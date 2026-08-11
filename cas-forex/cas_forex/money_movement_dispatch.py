"""Durable provider-dispatch chokepoint for CAS Forex money movement.

Every real deposit, withdrawal, payout, or configured autonomous sweep should
enter here. The intent is reserved before provider contact, the same key is
sent to the provider, and an uncertain or in-flight outcome blocks blind retry.
"""

from __future__ import annotations

import json
import math
from typing import Any, Mapping, Optional

from cas_forex import runtime_gates
from cas_forex.account_ledger import money, stable_ledger_id
from cas_forex.money_movement import (
    STATUS_BLOCKED,
    STATUS_PENDING,
    STATUS_SETTLED,
    MovementEngine,
    MovementKind,
)
from cas_forex.payout_recovery import (
    STATUS_BLOCKED as ATTEMPT_BLOCKED,
    STATUS_FAILED as ATTEMPT_FAILED,
    STATUS_PENDING as ATTEMPT_PENDING,
    STATUS_RECOVERY_REQUIRED,
    STATUS_RESERVED,
    STATUS_SETTLED as ATTEMPT_SETTLED,
    PayoutAttemptStore,
    default_payout_attempt_store,
)


REPORT_KIND = "cas_forex_money_movement_dispatch"

_CAPABILITY_BY_KIND = {
    MovementKind.DEPOSIT: "auto_deposit",
    MovementKind.WITHDRAWAL: "bank_card_movement",
    MovementKind.PAYOUT: "payout_automation",
}

CLAIM_BOUNDARY = (
    "Money-movement dispatch is the provider-side chokepoint. It atomically "
    "reserves one intent before provider contact, sends the same idempotency key "
    "to the provider, and records receipt, ledger, event-hash, and balance-delta "
    "evidence. PENDING or uncertain outcomes require reconciliation and are not "
    "reported as settled."
)


def build_movement_idempotency_key(
    *,
    kind: MovementKind | str,
    amount_usd: float,
    source_id: str | None = None,
    destination_id: str | None = None,
    purpose: str,
    intent_fingerprint: str,
) -> str:
    normalized_kind = _movement_kind(kind)
    fingerprint = str(intent_fingerprint or "").strip()
    if not fingerprint:
        raise ValueError("intent_fingerprint is required for money-movement idempotency")
    material = {
        "kind": normalized_kind.value,
        "amount_usd": money(float(amount_usd)),
        "source_id": source_id or "",
        "destination_id": destination_id or "",
        "purpose": str(purpose or "unspecified"),
        "intent_fingerprint": fingerprint,
    }
    return stable_ledger_id(
        "money-movement-intent",
        json.dumps(material, sort_keys=True, default=str),
    )


def dispatch_money_movement(
    *,
    kind: MovementKind | str,
    amount_usd: float,
    idempotency_key: str,
    source_id: str | None = None,
    destination_id: str | None = None,
    strategy_id: str | None = None,
    purpose: str = "configured_money_movement",
    policy_id: str | None = None,
    authority_mode: str = "AUTONOMOUS",
    require_real_provider: bool = True,
    preview: Mapping[str, Any] | None = None,
    engine: MovementEngine | None = None,
    attempt_store: PayoutAttemptStore | None = None,
    config: Any = None,
    daily_cap_usd: float | None = None,
) -> dict[str, Any]:
    """Dispatch one configured movement with durable once-only semantics."""

    movement_kind = _movement_kind(kind)
    amount = float(amount_usd)
    key = str(idempotency_key or "").strip()
    if not key:
        raise ValueError("idempotency_key is required before provider dispatch")
    cfg = _resolve_config(config)
    engine = engine or MovementEngine.from_config(cfg)
    attempt_store = attempt_store or default_payout_attempt_store()
    capability = _CAPABILITY_BY_KIND[movement_kind]
    effective_daily_cap = _effective_daily_cap(
        daily_cap_usd,
        getattr(cfg, "movement_max_daily_usd", None),
    )
    checks = _preflight_checks(
        movement_kind,
        amount,
        source_id=source_id,
        destination_id=destination_id,
        capability=capability,
        require_real_provider=require_real_provider,
        provider_is_real=bool(getattr(engine.provider, "is_real", False)),
        attempt_store=attempt_store,
        idempotency_key=key,
        config=cfg,
    )
    if not checks["passed"]:
        reason = "; ".join(
            str(item["detail"])
            for item in checks["checks"]
            if not bool(item.get("passed"))
        ) or "money-movement preflight blocked"
        attempt = attempt_store.record_blocked(
            key,
            amount_usd=amount,
            kind=movement_kind.value,
            source_id=source_id,
            destination_id=destination_id,
            purpose=purpose,
            policy_id=policy_id,
            authority_mode=authority_mode,
            reason=reason,
            anomaly_checks=checks,
        )
        return _dispatch_result(
            status=STATUS_BLOCKED,
            detail=reason,
            movement=None,
            attempt=attempt,
            checks=checks,
            provider_touched=False,
        )

    attempt, can_call_provider = attempt_store.reserve(
        key,
        amount_usd=amount,
        destination_id=destination_id,
        preview=dict(preview or {}),
        kind=movement_kind.value,
        source_id=source_id,
        purpose=purpose,
        policy_id=policy_id,
        daily_cap_usd=effective_daily_cap,
        anomaly_checks=checks,
        authority_mode=authority_mode,
    )
    if not can_call_provider:
        attempt_status = str(attempt.get("status") or ATTEMPT_BLOCKED)
        if attempt_status == ATTEMPT_SETTLED:
            status = "ALREADY_RECORDED"
            detail = "This exact money-movement intent is already settled."
        elif attempt_status in {STATUS_RESERVED, ATTEMPT_PENDING, STATUS_RECOVERY_REQUIRED}:
            status = STATUS_RECOVERY_REQUIRED
            detail = (
                "This exact movement or another unresolved provider attempt requires "
                "provider/bank reconciliation before retry."
            )
        elif attempt_status == ATTEMPT_FAILED:
            status = "ALREADY_RECORDED"
            detail = "This exact failed intent is already recorded; create a new intent to retry."
        else:
            status = STATUS_BLOCKED
            detail = str(attempt.get("movement_reason") or "Money-movement reservation blocked.")
        return _dispatch_result(
            status=status,
            detail=detail,
            movement=attempt.get("movement") if attempt_status == ATTEMPT_SETTLED else None,
            attempt=attempt,
            checks=checks,
            provider_touched=False,
        )

    if movement_kind == MovementKind.DEPOSIT:
        movement = engine.deposit(
            amount,
            source_id=source_id,
            strategy_id=strategy_id,
            idempotency_key=key,
        )
    elif movement_kind == MovementKind.WITHDRAWAL:
        movement = engine.withdraw(
            amount,
            destination_id=destination_id,
            strategy_id=strategy_id,
            idempotency_key=key,
        )
    else:
        movement = engine.payout(
            amount,
            destination_id=destination_id,
            strategy_id=strategy_id,
            idempotency_key=key,
        )
    movement_payload = movement.to_dict()
    attempt = attempt_store.record_result(key, movement=movement_payload)
    attempt_status = str(attempt.get("status") or "")
    if attempt_status == STATUS_RECOVERY_REQUIRED:
        status = STATUS_RECOVERY_REQUIRED
    elif attempt_status == ATTEMPT_PENDING:
        status = STATUS_PENDING
    else:
        status = movement.status
    return _dispatch_result(
        status=status,
        detail=str(attempt.get("recovery_reason") or movement.reason),
        movement=movement_payload,
        attempt=attempt,
        checks=checks,
        provider_touched=bool(movement.provider_touched),
    )


def reconcile_pending_money_movements(
    *,
    engine: MovementEngine | None = None,
    attempt_store: PayoutAttemptStore | None = None,
    config: Any = None,
) -> dict[str, Any]:
    """Refresh provider truth for in-flight references without issuing a new transfer."""

    cfg = _resolve_config(config)
    engine = engine or MovementEngine.from_config(cfg)
    attempt_store = attempt_store or default_payout_attempt_store()
    recovery = attempt_store.build_status()
    results: list[dict[str, Any]] = []
    for attempt in recovery.get("pending_attempts") or []:
        attempt_status = str(attempt.get("status") or "")
        if attempt_status not in {
            ATTEMPT_PENDING,
            STATUS_RECOVERY_REQUIRED,
            STATUS_RESERVED,
        }:
            continue
        reference = str(attempt.get("provider_reference") or "").strip()
        key = str(attempt.get("idempotency_key") or "").strip()
        try:
            kind = _movement_kind(str(attempt.get("kind") or "payout"))
            if reference:
                receipt = engine.provider.reconcile(reference, kind=kind)
                lookup_mode = "provider_reference"
            else:
                lookup = getattr(engine.provider, "reconcile_idempotency_key", None)
                receipt = lookup(key, kind=kind) if callable(lookup) else None
                lookup_mode = "idempotency_key"
        except Exception as exc:
            results.append(
                {
                    "idempotency_key": key,
                    "status": "RECONCILIATION_ERROR",
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        if receipt is None:
            results.append(
                {
                    "idempotency_key": key,
                    "status": "RECONCILIATION_UNSUPPORTED",
                    "lookup_mode": lookup_mode,
                    "detail": (
                        "Configured provider returned no movement for the existing "
                        f"{lookup_mode}; no transfer was retried."
                    ),
                }
            )
            continue
        movement = engine.result_from_provider_receipt(
            str(attempt.get("kind") or "payout"),
            float(attempt.get("amount_usd") or receipt.amount_usd),
            receipt,
            strategy_id=str(attempt.get("purpose") or "money-movement-reconciliation"),
        ).to_dict()
        updated = attempt_store.record_result(
            key,
            movement=movement,
        )
        results.append(
            {
                "idempotency_key": key,
                "status": updated.get("status"),
                "lookup_mode": lookup_mode,
                "provider_status": updated.get("provider_status"),
                "provider_reference": updated.get("provider_reference"),
                "evidence_complete": updated.get("evidence_complete"),
            }
        )
    final_status = attempt_store.build_status()
    return {
        "report_kind": "cas_forex_money_movement_reconciliation",
        "attempted_count": len(results),
        "results": results,
        "pending_count": final_status.get("pending_count", 0),
        "has_pending_recovery": final_status.get("has_pending_recovery", False),
        "provider_queried": bool(results),
        "claim_boundary": (
            "Reconciliation reads an existing provider reference and never creates a "
            "new transfer. Only final provider truth can close a pending attempt."
        ),
    }


def _preflight_checks(
    kind: MovementKind,
    amount: float,
    *,
    source_id: str | None,
    destination_id: str | None,
    capability: str,
    require_real_provider: bool,
    provider_is_real: bool,
    attempt_store: PayoutAttemptStore,
    idempotency_key: str,
    config: Any,
) -> dict[str, Any]:
    gate = runtime_gates.evaluate_capability(capability, config)
    checks: list[dict[str, Any]] = []

    def add(check_id: str, passed: bool, detail: str, evidence: Any = None) -> None:
        checks.append(
            {
                "check_id": check_id,
                "passed": bool(passed),
                "detail": detail,
                "evidence": evidence,
            }
        )

    add(
        "amount_positive_finite",
        math.isfinite(amount) and amount > 0,
        "Movement amount is positive and finite."
        if math.isfinite(amount) and amount > 0
        else "Movement amount must be positive and finite.",
        amount,
    )
    add(
        "authority_gate",
        bool(gate.authorized),
        "Owner-delegated capability gate is authorized."
        if gate.authorized
        else f"{capability} is not authorized: {'; '.join(gate.missing_requirements)}",
        gate.to_dict(),
    )
    add(
        "real_provider",
        provider_is_real or not require_real_provider,
        "Configured provider is real-money capable."
        if provider_is_real
        else "A real provider is required; the runtime provider is simulated.",
        {"required": require_real_provider, "provider_is_real": provider_is_real},
    )
    event_cap = getattr(config, "movement_max_usd", None)
    add(
        "per_event_cap",
        event_cap is None or amount <= float(event_cap),
        "Amount is inside the owner per-event cap."
        if event_cap is None or amount <= float(event_cap)
        else f"Amount {money(amount):.2f} exceeds per-event cap {float(event_cap):.2f}.",
        event_cap,
    )
    if kind in {MovementKind.WITHDRAWAL, MovementKind.PAYOUT}:
        allowed = getattr(config, "payout_destination_id", None)
        allowlisted = bool(getattr(config, "payout_destination_allowlisted", False))
        requested = destination_id or allowed
        destination_ok = bool(allowed and allowlisted and requested == allowed)
        add(
            "destination_allowlist",
            destination_ok,
            "Destination matches the owner allowlist."
            if destination_ok
            else "Outflow destination is missing, unallowlisted, or does not match owner setup.",
            {"configured": allowed, "requested": requested, "allowlisted": allowlisted},
        )
    else:
        configured_source = getattr(config, "deposit_source_id", None)
        source_allowlisted = bool(getattr(config, "deposit_source_allowlisted", False))
        source_policy_configured = bool(configured_source or source_allowlisted)
        source_ok = (
            not source_policy_configured
            or bool(configured_source and source_allowlisted and source_id == configured_source)
        )
        add(
            "origin_account_approved",
            source_ok,
            "Deposit source is inside the configured origin policy."
            if source_ok
            else "Deposit source does not match the approved owner origin.",
            {
                "policy_configured": source_policy_configured,
                "configured": configured_source,
                "requested": source_id,
                "allowlisted": source_allowlisted,
            },
        )
    recovery = attempt_store.build_status()
    foreign_pending = [
        item
        for item in recovery.get("pending_attempts") or []
        if item.get("idempotency_key") != idempotency_key
    ]
    add(
        "prior_movement_recovery_clear",
        not foreign_pending,
        "No other unresolved provider movement is open."
        if not foreign_pending
        else "Another provider movement is unresolved; reconcile it before a new movement.",
        {"pending_count": len(foreign_pending)},
    )
    return {
        "report_kind": "cas_forex_money_movement_anomaly_checks",
        "passed": all(bool(item["passed"]) for item in checks),
        "checks": checks,
    }


def _dispatch_result(
    *,
    status: str,
    detail: str,
    movement: Mapping[str, Any] | None,
    attempt: Mapping[str, Any],
    checks: Mapping[str, Any],
    provider_touched: bool,
) -> dict[str, Any]:
    return {
        "report_kind": REPORT_KIND,
        "status": status,
        "detail": detail,
        "provider_touched": provider_touched,
        "movement": dict(movement) if isinstance(movement, Mapping) else None,
        "movement_attempt": dict(attempt),
        "payout_attempt": dict(attempt),
        "anomaly_checks": dict(checks),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _effective_daily_cap(*values: Any) -> Optional[float]:
    caps = [float(value) for value in values if value is not None and float(value) >= 0]
    return min(caps) if caps else None


def _movement_kind(value: MovementKind | str) -> MovementKind:
    if isinstance(value, MovementKind):
        return value
    normalized = str(value or "").strip().lower()
    try:
        return MovementKind(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported money-movement kind: {value}") from exc


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config
