"""One-command, fail-closed handoff from Risen login to CAS live preflight.

This module performs only readiness and recovery operations. It never places an
order, mints an edge authorization, accepts broker terms, or moves money.
"""

from __future__ import annotations

from typing import Any, Mapping

from cas_forex.auto_halt import clear_auto_halt, is_auto_halt_active
from cas_forex.broker_reality import build_broker_reality_review
from cas_forex.broker_truth_monitor import monitor_status, run_broker_truth_check
from cas_forex.broker_truth_recovery_packet import build_broker_truth_recovery_packet
from cas_forex.live_order_dry_run_review import build_live_order_dry_run_review
from cas_forex.live_recovery import (
    LiveRecoveryError,
    accept_live_recovery_review,
    build_live_recovery_report,
)
from cas_forex.runtime_gates import build_runtime_gates_report
from cas_forex.time_utils import utc_now
from cas_forex.waste_background_worker import start_broker_truth_monitor_worker


REPORT_KIND = "cas_forex_risen_live_handoff"
STATUS_PROBE_FAILED = "RISEN_LIVE_HANDOFF_PROBE_FAILED"
STATUS_WAITING_ACCOUNT = "RISEN_LIVE_HANDOFF_WAITING_FOR_CONFIGURED_ACCOUNT"
STATUS_RECONCILIATION_BLOCKED = "RISEN_LIVE_HANDOFF_RECONCILIATION_BLOCKED"
STATUS_RECOVERY_BLOCKED = "RISEN_LIVE_HANDOFF_RECOVERY_BLOCKED"
STATUS_OWNER_GATES_OPEN = "RISEN_LIVE_HANDOFF_OWNER_GATES_OPEN"
STATUS_READY_FOR_PREFLIGHT = "RISEN_LIVE_HANDOFF_READY_FOR_ACTION_TIME_PREFLIGHT"

CLAIM_BOUNDARY = (
    "Risen live handoff verifies the configured MT5 identity, records fresh "
    "broker truth, starts the read-only broker monitor, and applies the owner's "
    "standing recovery instruction only after clean reconciliation evidence. "
    "It never places or modifies an order, creates an edge PASS, accepts broker "
    "terms, funds an account, or moves money."
)


def run_risen_live_handoff(
    *,
    interval_seconds: int = 120,
    start_monitor: bool = True,
    apply_recovery: bool = True,
) -> dict[str, Any]:
    """Advance the live handoff as far as current broker evidence permits."""

    generated_at = utc_now().isoformat()
    try:
        broker_truth = run_broker_truth_check(write_state=True, write_report=True)
    except Exception as exc:
        return _packet(
            generated_at=generated_at,
            status=STATUS_PROBE_FAILED,
            exact_live_account=False,
            broker_truth={},
            detail=f"Fresh MT5 broker-truth probe failed: {type(exc).__name__}: {exc}",
            next_actions=["Complete the Risen MT5 login, then run the handoff again."],
        )

    exact_live_account = _exact_live_account_visible(broker_truth)
    if not exact_live_account:
        actual = _account_label(
            broker_truth.get("mt5_account"),
            broker_truth.get("mt5_account_server"),
        )
        expected = _account_label(
            broker_truth.get("mt5_expected_account"),
            broker_truth.get("mt5_expected_server"),
        )
        return _packet(
            generated_at=generated_at,
            status=STATUS_WAITING_ACCOUNT,
            exact_live_account=False,
            broker_truth=broker_truth,
            detail=f"Connected MT5 identity {actual} does not prove configured live identity {expected}.",
            next_actions=[
                f"Complete the MT5 login for {expected}.",
                "Do not start broker-truth monitoring against the stale or wrong account.",
            ],
        )

    monitor_worker: dict[str, Any] = {}
    if start_monitor:
        try:
            monitor_worker = dict(
                start_broker_truth_monitor_worker(interval_seconds=int(interval_seconds))
            )
        except Exception as exc:
            monitor_worker = {
                "running": False,
                "status": "START_FAILED",
                "last_error": f"{type(exc).__name__}: {exc}",
            }

    state = dict(monitor_status())
    state["latest_report"] = broker_truth
    recovery_packet = build_broker_truth_recovery_packet(monitor_state=state)
    broker_truth_clear = bool(
        recovery_packet.get("broker_truth_clear_for_live_recovery", False)
    )

    recovery_actions: list[dict[str, Any]] = []
    if apply_recovery and broker_truth_clear:
        if is_auto_halt_active():
            cleared = clear_auto_halt(
                confirm_clear=True,
                reason="OWNER_REQUESTED_RISEN_LIVE_HANDOFF_AFTER_FRESH_RECONCILIATION",
            )
            recovery_actions.append(
                {
                    "action": "auto_halt_clear",
                    "applied": not bool(cleared.get("active", True)),
                    "cleared_at": cleared.get("cleared_at"),
                }
            )

        review = build_live_recovery_report(broker_truth_report=broker_truth)
        if bool(review.get("requires_recovery_review")) and bool(
            review.get("evidence_ready_for_owner_accept")
        ):
            try:
                accepted = accept_live_recovery_review(
                    confirm_owner_accept=True,
                    notes=(
                        "Applied under the owner's standing goal instruction to clear "
                        "recovery after fresh exact-account broker truth."
                    ),
                    broker_truth_report=broker_truth,
                )
                recovery_actions.append(
                    {
                        "action": "live_recovery_accept",
                        "applied": bool(accepted.get("recovery_clear_for_live")),
                        "accepted_fingerprint": accepted.get("accepted_fingerprint"),
                    }
                )
            except LiveRecoveryError as exc:
                recovery_actions.append(
                    {
                        "action": "live_recovery_accept",
                        "applied": False,
                        "error": str(exc),
                    }
                )

    recovery = build_live_recovery_report(broker_truth_report=broker_truth)
    broker_review = build_broker_reality_review()
    dry_run_review = build_live_order_dry_run_review(
        broker_truth_report=broker_truth,
    )
    runtime = build_runtime_gates_report().to_dict()

    recovery_clear = bool(recovery.get("recovery_clear_for_live", False))
    broker_review_clear = str(broker_review.get("review_status") or "") == "ACCEPT"
    dry_run_clear = bool(dry_run_review.get("dry_run_review_clear_for_live", False))
    runtime_live = _runtime_live_authorized(runtime)

    next_actions: list[str] = []
    if not broker_truth_clear:
        status = STATUS_RECONCILIATION_BLOCKED
        next_actions.append(str(recovery_packet.get("next_action") or "Resolve broker-truth reconciliation blockers."))
    elif not recovery_clear:
        status = STATUS_RECOVERY_BLOCKED
        next_actions.append(str(recovery.get("next_action") or "Complete live recovery review."))
    elif not (broker_review_clear and dry_run_clear and runtime_live):
        status = STATUS_OWNER_GATES_OPEN
        if not broker_review_clear:
            next_actions.append(str(broker_review.get("next_action") or "Complete broker reality review."))
        if not dry_run_clear:
            next_actions.append(str(dry_run_review.get("next_action") or "Produce and review a fresh live-order dry run."))
        if not runtime_live:
            next_actions.append("Resolve the remaining runtime live-trading gate requirements.")
    else:
        status = STATUS_READY_FOR_PREFLIGHT
        next_actions.append(
            "Generate a fresh edge-bound candidate and run the normal action-time live preflight."
        )

    return _packet(
        generated_at=generated_at,
        status=status,
        exact_live_account=True,
        broker_truth=broker_truth,
        detail=(
            "Configured Risen live account identity is proven. The handoff advanced "
            "only through gates supported by current evidence."
        ),
        next_actions=next_actions,
        monitor_worker=monitor_worker,
        recovery_packet=recovery_packet,
        recovery=recovery,
        recovery_actions=recovery_actions,
        broker_review=broker_review,
        dry_run_review=dry_run_review,
        runtime_gates=runtime,
    )


def _exact_live_account_visible(report: Mapping[str, Any]) -> bool:
    return bool(report.get("mt5_connected")) and report.get("mt5_is_demo") is False and (
        report.get("mt5_account_identity_matches_config") is True
    )


def _runtime_live_authorized(report: Mapping[str, Any]) -> bool:
    decisions = report.get("decisions") if isinstance(report.get("decisions"), Mapping) else {}
    live = decisions.get("live_trading") if isinstance(decisions.get("live_trading"), Mapping) else {}
    return bool(live.get("authorized", False))


def _account_label(login: Any, server: Any) -> str:
    return f"{login or 'unknown'} / {server or 'unknown'}"


def _packet(
    *,
    generated_at: str,
    status: str,
    exact_live_account: bool,
    broker_truth: Mapping[str, Any],
    detail: str,
    next_actions: list[str],
    monitor_worker: Mapping[str, Any] | None = None,
    recovery_packet: Mapping[str, Any] | None = None,
    recovery: Mapping[str, Any] | None = None,
    recovery_actions: list[dict[str, Any]] | None = None,
    broker_review: Mapping[str, Any] | None = None,
    dry_run_review: Mapping[str, Any] | None = None,
    runtime_gates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "report_kind": REPORT_KIND,
        "generated_at": generated_at,
        "status": status,
        "exact_live_account": exact_live_account,
        "broker_truth": dict(broker_truth),
        "monitor_worker": dict(monitor_worker or {}),
        "broker_truth_recovery": dict(recovery_packet or {}),
        "live_recovery": dict(recovery or {}),
        "recovery_actions": list(recovery_actions or []),
        "broker_review": dict(broker_review or {}),
        "dry_run_review": dict(dry_run_review or {}),
        "runtime_gates": dict(runtime_gates or {}),
        "broker_touched": False,
        "order_attempted": False,
        "edge_pass_created": False,
        "money_moved": False,
        "detail": detail,
        "next_actions": [action for action in next_actions if str(action or "").strip()],
        "claim_boundary": CLAIM_BOUNDARY,
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "REPORT_KIND",
    "STATUS_OWNER_GATES_OPEN",
    "STATUS_PROBE_FAILED",
    "STATUS_READY_FOR_PREFLIGHT",
    "STATUS_RECONCILIATION_BLOCKED",
    "STATUS_RECOVERY_BLOCKED",
    "STATUS_WAITING_ACCOUNT",
    "run_risen_live_handoff",
]
