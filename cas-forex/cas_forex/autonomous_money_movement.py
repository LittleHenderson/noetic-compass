"""AI Operator initiated autonomous money-movement cycle.

The first production policy is a verified-profit sweep. The owner arms the
standing policy once; each Operator tick may then dispatch only the incremental
unswept entitlement through the durable provider chokepoint without per-transfer
confirmation.
"""

from __future__ import annotations

from datetime import datetime
import math
from typing import Any, Mapping, Optional

from cas_forex.money_movement import MovementEngine
from cas_forex.money_movement_dispatch import reconcile_pending_money_movements
from cas_forex.payout_recovery import PayoutAttemptStore, default_payout_attempt_store
from cas_forex.time_utils import utc_now
from cas_forex.verified_profit_sweep import (
    ProfitSweepAuditLog,
    ProfitSweepPolicyStore,
    ProfitSweepSettings,
    build_sweep_preview,
    request_verified_profit_sweep,
)


REPORT_KIND = "cas_forex_autonomous_money_movement_cycle"

CLAIM_BOUNDARY = (
    "The AI Operator may autonomously initiate a configured verified-profit "
    "sweep after the owner arms the policy. It dispatches only incremental, "
    "broker-confirmed live winnings through the provider chokepoint. Fresh live "
    "broker truth, recovery clearance, allowlist, event/daily caps, anomaly "
    "checks, one-use idempotency, receipt, ledger, event-hash, and kill-switch "
    "gates remain mandatory; no per-transfer human confirmation is required "
    "inside that delegated envelope."
)


def run_autonomous_verified_profit_sweep_cycle(
    *,
    trigger: str = "AI_OPERATOR_TICK",
    account_ledger: Mapping[str, Any] | None = None,
    settings: ProfitSweepSettings | None = None,
    config: Any = None,
    engine: MovementEngine | None = None,
    attempt_store: PayoutAttemptStore | None = None,
    audit: ProfitSweepAuditLog | None = None,
    broker_truth_report: Mapping[str, Any] | None = None,
    live_recovery_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = _resolve_config(config)
    settings = (settings or ProfitSweepPolicyStore().load()).normalized()
    attempt_store = attempt_store or default_payout_attempt_store()
    audit = audit or ProfitSweepAuditLog()
    engine = engine or MovementEngine.from_config(cfg)
    base = {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "trigger": str(trigger or "AI_OPERATOR_TICK"),
        "autonomous_enabled": settings.autonomous_enabled,
        "policy_id": settings.policy_id,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    if not settings.autonomous_enabled:
        return {
            **base,
            "status": "AUTONOMY_NOT_ARMED",
            "provider_touched": False,
            "detail": "Owner has not armed autonomous verified-profit sweeping.",
        }

    provider_reconciliation = reconcile_pending_money_movements(
        engine=engine,
        attempt_store=attempt_store,
        config=cfg,
    )
    recovery = attempt_store.build_status()
    if recovery.get("has_pending_recovery"):
        return {
            **base,
            "status": "PAYOUT_RECOVERY_REQUIRED",
            "provider_touched": False,
            "payout_recovery": recovery,
            "provider_reconciliation": provider_reconciliation,
            "detail": (
                "An earlier movement is pending or uncertain. Reconcile provider/bank "
                "evidence before any autonomous movement."
            ),
        }

    truth = dict(broker_truth_report or _refresh_broker_truth())
    truth_ready, truth_detail = _fresh_live_broker_truth(
        truth,
        max_age_seconds=int(
            getattr(cfg, "movement_broker_truth_max_age_seconds", 180) or 180
        ),
    )
    if not truth_ready:
        return {
            **base,
            "status": "BROKER_TRUTH_BLOCKED",
            "provider_touched": False,
            "broker_truth": _compact_broker_truth(truth),
            "detail": truth_detail,
        }

    if live_recovery_report is None:
        from cas_forex.live_recovery import build_live_recovery_report

        live_recovery_report = build_live_recovery_report(
            broker_truth_report=truth,
        )
    live_recovery = dict(live_recovery_report)
    if not bool(live_recovery.get("recovery_clear_for_live", False)):
        return {
            **base,
            "status": "LIVE_RECOVERY_BLOCKED",
            "provider_touched": False,
            "broker_truth": _compact_broker_truth(truth),
            "live_recovery": live_recovery,
            "detail": (
                "Live recovery is not clear; autonomous money movement did not contact "
                "the provider."
            ),
        }

    if account_ledger is None:
        from api.data import verified_profit_account_ledger

        account_ledger = verified_profit_account_ledger()
    already_swept = attempt_store.settled_total_usd(
        purpose="verified_profit_sweep",
        policy_id=settings.policy_id,
    )
    preview = build_sweep_preview(
        account_ledger,
        settings,
        config=cfg,
        already_swept_usd=already_swept,
    )
    if preview.status != "READY":
        record = audit.append(
            "AUTONOMOUS_SWEEP_IDLE_OR_BLOCKED",
            {
                "trigger": base["trigger"],
                "broker_truth": _compact_broker_truth(truth),
                "preview": preview.to_dict(),
            },
        )
        return {
            **base,
            "status": "IDLE" if preview.sweep_amount_usd <= 0 else "BLOCKED",
            "provider_touched": False,
            "broker_truth": _compact_broker_truth(truth),
            "preview": preview.to_dict(),
            "audit": record,
            "detail": preview.reason,
        }

    funds_ready, funds_detail, funds_evidence = _outflow_funds_check(
        preview.sweep_amount_usd,
        truth,
    )
    if not funds_ready:
        record = audit.append(
            "AUTONOMOUS_SWEEP_BROKER_FUNDS_BLOCKED",
            {
                "trigger": base["trigger"],
                "broker_truth": _compact_broker_truth(truth),
                "preview": preview.to_dict(),
                "funds_check": funds_evidence,
            },
        )
        return {
            **base,
            "status": "BROKER_FUNDS_BLOCKED",
            "provider_touched": False,
            "broker_truth": _compact_broker_truth(truth),
            "preview": preview.to_dict(),
            "funds_check": funds_evidence,
            "audit": record,
            "detail": funds_detail,
        }

    result = request_verified_profit_sweep(
        account_ledger,
        settings,
        confirm=False,
        autonomous=True,
        destination_id=settings.destination_id,
        engine=engine,
        audit=audit,
        config=cfg,
        attempt_store=attempt_store,
        live_recovery_report=live_recovery,
        broker_truth_report=truth,
        preview=preview,
    )
    dispatch = result.get("money_movement_dispatch") or {}
    return {
        **base,
        "status": result.get("status"),
        "provider_touched": bool(dispatch.get("provider_touched", False)),
        "broker_truth": _compact_broker_truth(truth),
        "live_recovery": live_recovery,
        "preview": preview.to_dict(),
        "result": result,
        "detail": result.get("detail") or preview.reason,
    }


def autonomous_money_movement_status(
    *,
    settings: ProfitSweepSettings | None = None,
    attempt_store: PayoutAttemptStore | None = None,
    config: Any = None,
) -> dict[str, Any]:
    settings = (settings or ProfitSweepPolicyStore().load()).normalized()
    recovery = (attempt_store or default_payout_attempt_store()).build_status()
    from cas_forex.payment_providers import describe_payment_provider_runtime

    provider_runtime = describe_payment_provider_runtime(_resolve_config(config)).to_dict()
    return {
        "report_kind": "cas_forex_autonomous_money_movement_status",
        "generated_at": utc_now().isoformat(),
        "autonomous_enabled": settings.autonomous_enabled,
        "policy_id": settings.policy_id,
        "destination_configured": bool(settings.destination_id),
        "payout_recovery": recovery,
        "provider_runtime": provider_runtime,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": (
            "The Operator may initiate an in-envelope verified-profit sweep on its next tick."
            if settings.autonomous_enabled and not recovery.get("has_pending_recovery")
            else recovery.get("next_action")
            if recovery.get("has_pending_recovery")
            else "Arm autonomous_enabled in the verified-profit sweep policy."
        ),
    }


def _refresh_broker_truth() -> Mapping[str, Any]:
    from cas_forex.broker_truth_monitor import run_broker_truth_check

    return run_broker_truth_check(write_report=False, write_state=True)


def _fresh_live_broker_truth(
    report: Mapping[str, Any],
    *,
    max_age_seconds: int,
) -> tuple[bool, str]:
    if not report:
        return False, "No fresh broker-truth report is available."
    if not bool(report.get("mt5_connected", False)):
        return False, "MT5 is not connected; fresh live broker truth is unavailable."
    if report.get("mt5_is_demo") is not False:
        return False, "Connected MT5 account is demo/paper, not a live-money account."
    if report.get("mt5_account_identity_matches_config") is not True:
        return False, "Connected MT5 login/server does not match the configured owner-approved account."
    if str(report.get("overall_status") or "").upper() == "RECONCILIATION_FAILED":
        return False, "Broker-truth reconciliation failed."
    money_fields = {
        "balance_usd": report.get("mt5_balance_usd"),
        "equity_usd": report.get("mt5_equity_usd"),
        "free_margin_usd": report.get("mt5_free_margin_usd"),
    }
    for label, value in money_fields.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False, f"Fresh broker truth is missing {label}."
        if not math.isfinite(numeric):
            return False, f"Fresh broker truth has invalid {label}."
    generated = report.get("generated_at")
    try:
        generated_at = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        age = (utc_now() - generated_at).total_seconds()
    except Exception:
        return False, "Broker-truth timestamp is missing or invalid."
    if age < 0 or age > max(1, int(max_age_seconds)):
        return False, f"Broker truth is stale ({age:.1f}s old)."
    return True, "Fresh connected live MT5 broker truth is present."


def _outflow_funds_check(
    amount_usd: float,
    report: Mapping[str, Any],
) -> tuple[bool, str, dict[str, Any]]:
    amount = float(amount_usd)
    balance = float(report.get("mt5_balance_usd") or 0.0)
    equity = float(report.get("mt5_equity_usd") or 0.0)
    free_margin = float(report.get("mt5_free_margin_usd") or 0.0)
    available = max(0.0, min(balance, equity, free_margin))
    passed = amount > 0 and amount <= available
    evidence = {
        "check_id": "broker_outflow_funds_available",
        "passed": passed,
        "requested_amount_usd": round(amount, 2),
        "balance_usd": round(balance, 2),
        "equity_usd": round(equity, 2),
        "free_margin_usd": round(free_margin, 2),
        "available_outflow_ceiling_usd": round(available, 2),
        "projected_balance_usd": round(balance - amount, 2),
        "projected_equity_usd": round(equity - amount, 2),
        "projected_free_margin_usd": round(free_margin - amount, 2),
    }
    if passed:
        return True, "Broker balance, equity, and free margin cover the autonomous outflow.", evidence
    return (
        False,
        "Autonomous payout exceeds fresh broker balance, equity, or free margin; provider dispatch was not attempted.",
        evidence,
    )


def _compact_broker_truth(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": report.get("generated_at"),
        "monitor_status": report.get("monitor_status"),
        "overall_status": report.get("overall_status"),
        "mt5_connected": bool(report.get("mt5_connected", False)),
        "mt5_is_demo": report.get("mt5_is_demo"),
        "mt5_account": report.get("mt5_account"),
        "mt5_account_currency": report.get("mt5_account_currency"),
        "mt5_balance_usd": report.get("mt5_balance_usd"),
        "mt5_equity_usd": report.get("mt5_equity_usd"),
        "mt5_margin_used_usd": report.get("mt5_margin_used_usd"),
        "mt5_free_margin_usd": report.get("mt5_free_margin_usd"),
        "mt5_open_positions": report.get(
            "mt5_open_positions",
            report.get("mt5_open_position_count"),
        ),
    }


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config
