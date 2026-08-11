"""Owner-confirmed broker emergency exposure controls.

This module is intentionally narrow: it inspects MT5 exposure by default, and it
only mutates broker state when the owner explicitly confirms the action. The
actual MT5 order_send paths still run through the MT5 bridge's existing live
authorization and terminal-permission gates.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "broker-emergency-audit.jsonl"
REPORT_KIND = "cas_forex_broker_emergency_action"

BrokerEmergencyAction = Literal[
    "close_all_positions",
    "close_profitable_positions",
    "close_losing_positions",
    "cancel_pending_orders",
]

CLAIM_BOUNDARY = (
    "Broker emergency actions are owner-commanded broker-exposure controls. "
    "Dry runs only inspect exposure. Confirmed actions may submit MT5 order_send "
    "requests to close positions or cancel pending orders, and the MT5 bridge "
    "still enforces live-trading authorization and terminal permissions before "
    "touching broker state."
)


def build_mt5_bridge() -> Any:
    from cas_forex.broker.mt5_bridge import MT5Bridge

    bridge = MT5Bridge()
    bridge.connect()
    return bridge


def build_broker_emergency_status(*, bridge: Any | None = None) -> dict[str, Any]:
    bridge = bridge or build_mt5_bridge()
    positions = _open_positions(bridge)
    pending = _pending_orders(bridge)
    return {
        "report_kind": "cas_forex_broker_emergency_status",
        "status": "READY" if _is_connected(bridge) else "MT5_NOT_CONNECTED",
        "mt5_connected": _is_connected(bridge),
        "will_execute_real_order": _will_execute_real_order(bridge),
        "open_position_count": len(positions),
        "pending_order_count": len(pending),
        "open_positions": positions,
        "pending_orders": pending,
        "supported_actions": [
            "close_all_positions",
            "close_profitable_positions",
            "close_losing_positions",
            "cancel_pending_orders",
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run_broker_emergency_action(
    action: BrokerEmergencyAction,
    *,
    bridge: Any | None = None,
    confirm_owner_action: bool = False,
    dry_run: bool = True,
    reason: str = "OWNER_BROKER_EMERGENCY",
    audit_path: Path | str = DEFAULT_AUDIT_PATH,
) -> dict[str, Any]:
    bridge = bridge or build_mt5_bridge()
    connected = _is_connected(bridge)
    positions = _open_positions(bridge)
    pending = _pending_orders(bridge)
    selected_positions = _select_positions(action, positions)
    selected_pending = pending if action == "cancel_pending_orders" else []

    if not connected:
        payload = _base_payload(
            action,
            status="MT5_NOT_CONNECTED",
            bridge=bridge,
            positions=positions,
            pending=pending,
            selected_positions=selected_positions,
            selected_pending=selected_pending,
            reason=reason,
        )
        payload["next_action"] = "Open and log into MT5, then retry the dry-run before any confirmed emergency action."
        _append_audit(payload, audit_path)
        return payload

    if dry_run:
        payload = _base_payload(
            action,
            status="DRY_RUN",
            bridge=bridge,
            positions=positions,
            pending=pending,
            selected_positions=selected_positions,
            selected_pending=selected_pending,
            reason=reason,
        )
        payload["next_action"] = "Review selected exposure, then rerun with dry_run=false and confirm_owner_action=true if intended."
        _append_audit(payload, audit_path)
        return payload

    if not confirm_owner_action:
        payload = _base_payload(
            action,
            status="CONFIRM_REQUIRED",
            bridge=bridge,
            positions=positions,
            pending=pending,
            selected_positions=selected_positions,
            selected_pending=selected_pending,
            reason=reason,
        )
        payload["next_action"] = "Set confirm_owner_action=true to submit the broker emergency action."
        _append_audit(payload, audit_path)
        return payload

    if action == "cancel_pending_orders" and not hasattr(bridge, "cancel_pending_order"):
        payload = _base_payload(
            action,
            status="UNSUPPORTED",
            bridge=bridge,
            positions=positions,
            pending=pending,
            selected_positions=selected_positions,
            selected_pending=selected_pending,
            reason=reason,
        )
        payload["next_action"] = "Use MT5 terminal pending-order controls or add a bridge cancel_pending_order implementation."
        _append_audit(payload, audit_path)
        return payload

    close_results = []
    cancel_results = []
    if selected_positions:
        for position in selected_positions:
            ticket = int(position["ticket"])
            ok = bool(bridge.close_position(ticket))
            close_results.append({**position, "action_status": "CLOSED" if ok else "FAILED"})
    if selected_pending:
        for order in selected_pending:
            ticket = int(order["ticket"])
            ok = bool(bridge.cancel_pending_order(ticket))
            cancel_results.append({**order, "action_status": "CANCELLED" if ok else "FAILED"})

    failures = [
        row
        for row in [*close_results, *cancel_results]
        if row.get("action_status") in {"FAILED", "REJECTED"}
    ]
    payload = _base_payload(
        action,
        status="PARTIAL" if failures else "EXECUTED",
        bridge=bridge,
        positions=positions,
        pending=pending,
        selected_positions=selected_positions,
        selected_pending=selected_pending,
        reason=reason,
    )
    payload.update(
        {
            "broker_touched": bool(close_results or cancel_results),
            "broker_order_send_attempted": bool(close_results or cancel_results),
            "closed_positions": close_results,
            "cancelled_orders": cancel_results,
            "failed_count": len(failures),
            "next_action": "Refresh broker truth and account reconciliation after this emergency action.",
        }
    )
    _append_audit(payload, audit_path)
    return payload


def _base_payload(
    action: BrokerEmergencyAction,
    *,
    status: str,
    bridge: Any,
    positions: list[dict[str, Any]],
    pending: list[dict[str, Any]],
    selected_positions: list[dict[str, Any]],
    selected_pending: list[dict[str, Any]],
    reason: str,
) -> dict[str, Any]:
    payload = {
        "report_kind": REPORT_KIND,
        "action": action,
        "status": status,
        "generated_at_iso": utc_now().isoformat(),
        "reason": str(reason or "OWNER_BROKER_EMERGENCY")[:300],
        "mt5_connected": _is_connected(bridge),
        "will_execute_real_order": _will_execute_real_order(bridge),
        "open_position_count": len(positions),
        "pending_order_count": len(pending),
        "selected_position_count": len(selected_positions),
        "selected_pending_order_count": len(selected_pending),
        "selected_positions": selected_positions,
        "selected_pending_orders": selected_pending,
        "broker_touched": False,
        "broker_order_send_attempted": False,
        "external_money_movement": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["audit_id"] = _audit_id(payload)
    return payload


def _select_positions(action: BrokerEmergencyAction, positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if action == "close_all_positions":
        return positions
    if action == "close_profitable_positions":
        return [position for position in positions if float(position.get("profit") or 0.0) > 0.0]
    if action == "close_losing_positions":
        return [position for position in positions if float(position.get("profit") or 0.0) < 0.0]
    return []


def _open_positions(bridge: Any) -> list[dict[str, Any]]:
    if hasattr(bridge, "get_all_open_positions"):
        rows = bridge.get_all_open_positions()
    elif hasattr(bridge, "get_open_positions"):
        rows = bridge.get_open_positions()
    else:
        rows = []
    return [_position_row(row) for row in rows or [] if _ticket(row) is not None]


def _pending_orders(bridge: Any) -> list[dict[str, Any]]:
    if hasattr(bridge, "get_pending_orders"):
        rows = bridge.get_pending_orders()
    else:
        rows = []
    return [_order_row(row) for row in rows or [] if _ticket(row) is not None]


def _position_row(row: Any) -> dict[str, Any]:
    ticket = _ticket(row)
    return {
        "ticket": int(ticket) if ticket is not None else 0,
        "symbol": str(_value(row, "symbol") or ""),
        "type": str(_value(row, "type") or _value(row, "direction") or ""),
        "volume": _float(_value(row, "volume")),
        "open_price": _float(_value(row, "open_price") or _value(row, "price_open")),
        "current_price": _float(_value(row, "current_price") or _value(row, "price_current")),
        "profit": _float(_value(row, "profit")),
        "comment": str(_value(row, "comment") or ""),
    }


def _order_row(row: Any) -> dict[str, Any]:
    ticket = _ticket(row)
    return {
        "ticket": int(ticket) if ticket is not None else 0,
        "symbol": str(_value(row, "symbol") or ""),
        "type": str(_value(row, "type") or ""),
        "volume": _float(_value(row, "volume") or _value(row, "volume_current")),
        "price_open": _float(_value(row, "price_open") or _value(row, "price")),
        "comment": str(_value(row, "comment") or ""),
    }


def _ticket(row: Any) -> int | None:
    value = _value(row, "ticket") or _value(row, "order")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _value(row: Any, key: str) -> Any:
    if isinstance(row, Mapping):
        return row.get(key)
    return getattr(row, key, None)


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _is_connected(bridge: Any) -> bool:
    probe = getattr(bridge, "is_connected", None)
    if not callable(probe):
        return False
    try:
        return bool(probe())
    except Exception:
        return False


def _will_execute_real_order(bridge: Any) -> bool | None:
    probe = getattr(bridge, "will_execute_real_order", None)
    if not callable(probe):
        return None
    try:
        return bool(probe())
    except Exception:
        return True


def _append_audit(payload: Mapping[str, Any], audit_path: Path | str) -> None:
    path = Path(audit_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_safe_json(payload), sort_keys=True) + "\n")


def _audit_id(payload: Mapping[str, Any]) -> str:
    return "broker-emergency-" + hashlib.sha256(
        json.dumps(_safe_json(payload), sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


def _safe_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        return [_safe_json(item) for item in value]
    return str(value)
