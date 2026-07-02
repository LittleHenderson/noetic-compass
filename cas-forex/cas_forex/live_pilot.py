"""Small-controlled live-money pilot gate for CAS Forex.

The final product is real-money capable, but the first live phase must be tiny,
owner-confirmed, and evidence-producing before any scaling. This module records
that pilot envelope and enforces it at the dispatch chokepoint.

It does not place trades, create broker ACCEPT, move money, or graduate the
system to scaled live trading by itself.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = REPO_ROOT / "runtime" / "live-pilot-policy.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "live-pilot-audit.jsonl"

REPORT_KIND = "cas_forex_small_controlled_live_pilot"
STATUS_OPEN = "OPEN"
STATUS_ACCEPT = "ACCEPT"

DEFAULT_MAX_TRADE_LOTS = 0.01
DEFAULT_MAX_OPEN_LIVE_LOTS = 0.02
DEFAULT_MAX_LIVE_TRADE_COUNT = 3
DEFAULT_MAX_DAILY_LOSS_USD = 25.0
DEFAULT_MAX_TOTAL_LOSS_USD = 50.0
DEFAULT_MAX_PILOT_DAYS = 5

HARD_MAX_TRADE_LOTS = 0.05
HARD_MAX_OPEN_LIVE_LOTS = 0.20
HARD_MAX_LIVE_TRADE_COUNT = 10
HARD_MAX_DAILY_LOSS_USD = 250.0
HARD_MAX_TOTAL_LOSS_USD = 500.0
HARD_MAX_PILOT_DAYS = 30

REQUIRED_CHECKS = (
    "owner_understands_real_money_risk",
    "owner_confirms_small_amounts_only",
    "owner_confirms_no_scaling_without_review",
    "owner_confirms_emergency_stop_ready",
)

NUMERIC_FIELDS = (
    "max_trade_lots",
    "max_open_live_lots",
    "max_live_trade_count",
    "max_daily_loss_usd",
    "max_total_loss_usd",
    "max_pilot_days",
)

CLAIM_BOUNDARY = (
    "Small-controlled live pilot is an owner-recorded live-money envelope for "
    "the first real trades only. It caps lots, trade count, loss limits, symbols, "
    "and duration before scaling. It does not prove profitability, place orders, "
    "move bank/card funds, automate payouts, or authorize live trading by itself."
)


class LivePilotError(PermissionError):
    """Raised when the live pilot policy cannot be accepted or an intent is outside it."""


def build_live_pilot_policy(
    *,
    policy_path: Path | str | None = None,
) -> dict[str, Any]:
    stored = _load_policy(policy_path)
    return _finalize_policy(stored if stored else _empty_policy())


def update_live_pilot_policy(
    patch: Mapping[str, Any],
    *,
    confirm_owner_accept: bool = False,
    policy_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    policy = dict(build_live_pilot_policy(policy_path=policy_path))
    checks = dict(policy.get("checks") or {})
    for key in REQUIRED_CHECKS:
        if key in patch:
            checks[key] = bool(patch[key])
    policy["checks"] = checks

    for key in NUMERIC_FIELDS:
        if key in patch:
            policy[key] = patch.get(key)
    if "allowed_symbols" in patch:
        policy["allowed_symbols"] = _clean_symbols(patch.get("allowed_symbols"))
    if "notes" in patch:
        policy["notes"] = str(patch.get("notes") or "").strip()

    policy["updated_at"] = utc_now().isoformat()
    if confirm_owner_accept:
        _assert_accept_ready(policy)
        policy["owner_pilot_status"] = STATUS_ACCEPT
        policy["owner_accepted_at"] = utc_now().isoformat()
    else:
        policy["owner_pilot_status"] = STATUS_OPEN
        policy["owner_accepted_at"] = None

    finalized = _finalize_policy(policy)
    _write_json(finalized, _policy_path(policy_path))
    _append_audit(
        {
            "action": "live_pilot_update",
            "timestamp": utc_now().isoformat(),
            "confirm_owner_accept": confirm_owner_accept,
            "owner_pilot_status": finalized["owner_pilot_status"],
            "ready_for_next_live_order": finalized["ready_for_next_live_order"],
            "missing_requirements": finalized["missing_requirements"],
        },
        _audit_path(audit_path),
    )
    return finalized


def reset_live_pilot_policy(
    *,
    policy_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    policy = _finalize_policy(_empty_policy())
    _write_json(policy, _policy_path(policy_path))
    _append_audit(
        {
            "action": "live_pilot_reset",
            "timestamp": utc_now().isoformat(),
            "owner_pilot_status": policy["owner_pilot_status"],
        },
        _audit_path(audit_path),
    )
    return policy


def is_live_pilot_available_for_live(*, policy_path: Path | str | None = None) -> bool:
    policy = build_live_pilot_policy(policy_path=policy_path)
    return bool(policy.get("ready_for_next_live_order", False))


def require_live_pilot_intent(
    proposed_intent: Mapping[str, Any],
    *,
    policy_path: Path | str | None = None,
    live_telemetry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Raise unless a real-money intent stays inside the accepted pilot envelope."""
    policy = build_live_pilot_policy(policy_path=policy_path)
    problems = _intent_problems(policy, proposed_intent, live_telemetry=live_telemetry)
    if problems:
        raise LivePilotError("Live pilot blocks order: " + "; ".join(problems))
    return policy


def record_live_pilot_dispatch(
    *,
    order_id: str,
    symbol: str,
    lots: float,
    outcome_status: str,
    policy_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    """Record one real-broker dispatch attempt against the pilot capacity."""
    policy = dict(build_live_pilot_policy(policy_path=policy_path))
    count = int(policy.get("live_trade_count", 0) or 0) + 1
    policy["live_trade_count"] = count
    policy["last_live_order_at"] = utc_now().isoformat()
    policy["last_live_order"] = {
        "order_id": str(order_id),
        "symbol": str(symbol),
        "lots": float(lots),
        "outcome_status": str(outcome_status),
    }
    finalized = _finalize_policy(policy)
    _write_json(finalized, _policy_path(policy_path))
    _append_audit(
        {
            "action": "live_pilot_dispatch_recorded",
            "timestamp": utc_now().isoformat(),
            "order_id": str(order_id),
            "symbol": str(symbol),
            "lots": float(lots),
            "outcome_status": str(outcome_status),
            "live_trade_count": finalized["live_trade_count"],
            "ready_for_next_live_order": finalized["ready_for_next_live_order"],
        },
        _audit_path(audit_path),
    )
    return finalized


def _empty_policy() -> dict[str, Any]:
    return {
        "report_kind": REPORT_KIND,
        "owner_pilot_status": STATUS_OPEN,
        "owner_accepted_at": None,
        "updated_at": None,
        "allowed_symbols": [],
        "max_trade_lots": DEFAULT_MAX_TRADE_LOTS,
        "max_open_live_lots": DEFAULT_MAX_OPEN_LIVE_LOTS,
        "max_live_trade_count": DEFAULT_MAX_LIVE_TRADE_COUNT,
        "max_daily_loss_usd": DEFAULT_MAX_DAILY_LOSS_USD,
        "max_total_loss_usd": DEFAULT_MAX_TOTAL_LOSS_USD,
        "max_pilot_days": DEFAULT_MAX_PILOT_DAYS,
        "live_trade_count": 0,
        "last_live_order_at": None,
        "last_live_order": None,
        "notes": "",
        "checks": {key: False for key in REQUIRED_CHECKS},
    }


def _finalize_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(policy)
    data["report_kind"] = REPORT_KIND
    data["allowed_symbols"] = _clean_symbols(data.get("allowed_symbols"))
    data["checks"] = {key: bool((data.get("checks") or {}).get(key, False)) for key in REQUIRED_CHECKS}
    data["max_trade_lots"] = _float(data.get("max_trade_lots"), DEFAULT_MAX_TRADE_LOTS)
    data["max_open_live_lots"] = _float(data.get("max_open_live_lots"), DEFAULT_MAX_OPEN_LIVE_LOTS)
    data["max_live_trade_count"] = _int(data.get("max_live_trade_count"), DEFAULT_MAX_LIVE_TRADE_COUNT)
    data["max_daily_loss_usd"] = _float(data.get("max_daily_loss_usd"), DEFAULT_MAX_DAILY_LOSS_USD)
    data["max_total_loss_usd"] = _float(data.get("max_total_loss_usd"), DEFAULT_MAX_TOTAL_LOSS_USD)
    data["max_pilot_days"] = _int(data.get("max_pilot_days"), DEFAULT_MAX_PILOT_DAYS)
    data["live_trade_count"] = max(0, _int(data.get("live_trade_count"), 0))

    config_missing = _config_missing(data)
    raw_status = str(data.get("owner_pilot_status") or STATUS_OPEN)
    status = STATUS_ACCEPT if raw_status == STATUS_ACCEPT and not config_missing else STATUS_OPEN
    capacity_remaining = max(0, int(data["max_live_trade_count"]) - int(data["live_trade_count"]))
    capacity_missing = ["pilot live trade count reached"] if status == STATUS_ACCEPT and capacity_remaining <= 0 else []
    data["owner_pilot_status"] = status
    data["accepted_for_live_start"] = status == STATUS_ACCEPT
    data["pilot_capacity_remaining"] = capacity_remaining
    data["ready_for_next_live_order"] = status == STATUS_ACCEPT and capacity_remaining > 0
    data["missing_requirements"] = config_missing + capacity_missing
    data["claim_boundary"] = CLAIM_BOUNDARY
    data["next_action"] = (
        "Live pilot is owner ACCEPT and has capacity for the next small live order."
        if data["ready_for_next_live_order"]
        else (
            "Pilot capacity is exhausted; review broker-confirmed pilot outcomes before resetting or scaling."
            if capacity_missing
            else "Set small live limits, allowed symbols, required owner checks, then owner-confirm ACCEPT."
        )
    )
    return data


def _assert_accept_ready(policy: Mapping[str, Any]) -> None:
    finalized = _finalize_policy({**dict(policy), "owner_pilot_status": STATUS_ACCEPT})
    missing = [item for item in finalized.get("missing_requirements", []) if item != "pilot live trade count reached"]
    if missing:
        raise LivePilotError("Cannot ACCEPT live pilot policy; missing: " + "; ".join(missing))


def _config_missing(policy: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    checks = policy.get("checks") or {}
    for key in REQUIRED_CHECKS:
        if not bool(checks.get(key, False)):
            missing.append(key)
    if not _clean_symbols(policy.get("allowed_symbols")):
        missing.append("allowed_symbols")

    max_trade = _float(policy.get("max_trade_lots"), 0.0)
    max_open = _float(policy.get("max_open_live_lots"), 0.0)
    max_count = _int(policy.get("max_live_trade_count"), 0)
    max_daily_loss = _float(policy.get("max_daily_loss_usd"), 0.0)
    max_total_loss = _float(policy.get("max_total_loss_usd"), 0.0)
    max_days = _int(policy.get("max_pilot_days"), 0)

    if max_trade <= 0 or max_trade > HARD_MAX_TRADE_LOTS:
        missing.append(f"max_trade_lots must be >0 and <= {HARD_MAX_TRADE_LOTS}")
    if max_open < max_trade or max_open > HARD_MAX_OPEN_LIVE_LOTS:
        missing.append(f"max_open_live_lots must be >= max_trade_lots and <= {HARD_MAX_OPEN_LIVE_LOTS}")
    if max_count < 1 or max_count > HARD_MAX_LIVE_TRADE_COUNT:
        missing.append(f"max_live_trade_count must be 1..{HARD_MAX_LIVE_TRADE_COUNT}")
    if max_daily_loss <= 0 or max_daily_loss > HARD_MAX_DAILY_LOSS_USD:
        missing.append(f"max_daily_loss_usd must be >0 and <= {HARD_MAX_DAILY_LOSS_USD}")
    if max_total_loss < max_daily_loss or max_total_loss > HARD_MAX_TOTAL_LOSS_USD:
        missing.append(f"max_total_loss_usd must be >= max_daily_loss_usd and <= {HARD_MAX_TOTAL_LOSS_USD}")
    if max_days < 1 or max_days > HARD_MAX_PILOT_DAYS:
        missing.append(f"max_pilot_days must be 1..{HARD_MAX_PILOT_DAYS}")
    return missing


def _intent_problems(
    policy: Mapping[str, Any],
    proposed_intent: Mapping[str, Any],
    *,
    live_telemetry: Mapping[str, Any] | None,
) -> list[str]:
    problems = list(policy.get("missing_requirements") or [])
    if not bool(policy.get("ready_for_next_live_order", False)):
        problems.append("live pilot is not ready for the next live order")
    symbol = str(proposed_intent.get("symbol") or "").strip().upper()
    allowed = {item.upper() for item in _clean_symbols(policy.get("allowed_symbols"))}
    if symbol not in allowed:
        problems.append(f"{symbol or 'symbol'} outside live pilot allowed_symbols")
    lots = _float(proposed_intent.get("lots", proposed_intent.get("volume")), 0.0)
    if lots <= 0:
        problems.append("lots must be positive")
    if lots > float(policy.get("max_trade_lots") or 0.0):
        problems.append(f"lots {lots:.4f} exceeds pilot max_trade_lots {float(policy.get('max_trade_lots') or 0.0):.4f}")
    open_lots = _open_live_lots(live_telemetry)
    if open_lots + lots > float(policy.get("max_open_live_lots") or 0.0):
        problems.append(
            f"open lots plus order {open_lots + lots:.4f} exceeds pilot max_open_live_lots "
            f"{float(policy.get('max_open_live_lots') or 0.0):.4f}"
        )
    expected_loss = proposed_intent.get("expected_loss_usd")
    if expected_loss is not None and _float(expected_loss, 0.0) > float(policy.get("max_daily_loss_usd") or 0.0):
        problems.append("expected_loss_usd exceeds pilot max_daily_loss_usd")
    return list(dict.fromkeys(problems))


def _open_live_lots(live_telemetry: Mapping[str, Any] | None) -> float:
    if not isinstance(live_telemetry, Mapping):
        return 0.0
    positions = live_telemetry.get("positions") or live_telemetry.get("open_positions") or []
    total = 0.0
    if not isinstance(positions, list):
        return 0.0
    for pos in positions:
        if not isinstance(pos, Mapping):
            continue
        total += _float(pos.get("lots", pos.get("volume")), 0.0)
    return max(0.0, total)


def _load_policy(path: Path | str | None) -> dict[str, Any] | None:
    target = _policy_path(path)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)


def _append_audit(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True, default=str) + "\n")


def _policy_path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else Path(DEFAULT_POLICY_PATH)


def _audit_path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else Path(DEFAULT_AUDIT_PATH)


def _clean_symbols(value: Any) -> list[str]:
    if isinstance(value, str):
        items = value.replace(",", "\n").splitlines()
    elif isinstance(value, list):
        items = value
    else:
        items = []
    cleaned = []
    for item in items:
        text = str(item).strip().upper()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)
