"""Confirmed AI Operator Edge/Hedge management execution adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from cas_forex import order_dispatch
from cas_forex.ai_hedge_management import build_ai_hedge_management_handoff
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "ai-hedge-management-execution-audit.jsonl"
REPORT_KIND = "cas_forex_ai_hedge_management_execution"
CLAIM_BOUNDARY = (
    "AI Operator Edge/Hedge management execution is a confirmed broker-action "
    "adapter for existing positions. It rebuilds the handoff at action time, "
    "routes through order_dispatch.py and execution_guard.py, calls the configured "
    "broker bridge, then attempts terminal receipt reconciliation against open-position "
    "truth. It does not require per-action owner confirmation inside delegated "
    "authority, open new positions, move money, mint edge PASS, or bypass bridge "
    "live/terminal gates."
)
_ONE_SHOT_MANAGEMENT_INTENTS = {
    "close_partial",
    "close_full",
    "reduce",
    "move_stop_to_breakeven",
}
_TRUTH_REARMABLE_MANAGEMENT_INTENTS = {
    "set_stop_loss",
    "set_take_profit",
}
_TERMINAL_EFFECT_STATUSES = {
    "EXECUTED_RECONCILED",
    "EXECUTED_NOT_RECONCILED",
    "EXECUTED_RECONCILIATION_UNAVAILABLE",
}


def run_ai_hedge_management_action(
    *,
    action_id: str | None = None,
    dry_run: bool = True,
    confirm_owner_action: bool = False,
    reason: str = "AI_OPERATOR_EDGE_MANAGEMENT",
    bridge: Any | None = None,
    bridge_factory: Callable[[], Any] | None = None,
    audit_path: Path | str = DEFAULT_AUDIT_PATH,
    handoff: Mapping[str, Any] | None = None,
    config: Any = None,
    post_execution_refresh: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Dry-run or execute one current AI Edge/Hedge management draft."""

    fresh_handoff = dict(handoff or build_ai_hedge_management_handoff())
    actions = [
        dict(row)
        for row in (fresh_handoff.get("management_actions") or [])
        if isinstance(row, Mapping)
    ]
    selected = _select_action(actions, action_id)
    base = _base_payload(
        action_id=action_id,
        selected_action=selected,
        handoff=fresh_handoff,
        reason=reason,
    )
    if selected is None:
        payload = {
            **base,
            "status": "ACTION_NOT_FOUND" if action_id else "NO_ACTIONABLE_MANAGEMENT",
            "next_action": "Refresh AI Operator Edge/Hedge management handoff and choose a current action draft.",
        }
        _append_audit(payload, audit_path)
        return payload

    if str(fresh_handoff.get("status") or "") not in {
        "READY_FOR_GUARDED_EXECUTION",
        "READY_FOR_OWNER_REVIEW",
    }:
        payload = {
            **base,
            "status": "HANDOFF_NOT_READY",
            "next_action": "Resolve the current AI Edge/Hedge handoff blockers before executing management.",
        }
        _append_audit(payload, audit_path)
        return payload

    if dry_run:
        payload = {
            **base,
            "status": "DRY_RUN",
            "next_action": "Review the selected draft, then rerun with dry_run=false if guarded autonomous execution is intended.",
        }
        _append_audit(payload, audit_path)
        return payload

    resolved_bridge = bridge or _build_bridge(bridge_factory)
    if resolved_bridge is None:
        payload = {
            **base,
            "status": "NO_BRIDGE",
            "next_action": "Configure broker control or reconnect the terminal, then retry a dry run.",
        }
        _append_audit(payload, audit_path)
        return payload

    position_preflight = _management_position_preflight(resolved_bridge, selected)
    if position_preflight.get("status") == "ALREADY_APPLIED":
        applied_receipt = position_preflight.get("receipt") or {}
        payload = {
            **base,
            "status": "ALREADY_APPLIED_RECONCILED",
            "terminal_receipt": applied_receipt,
            "terminal_receipt_status": "RECONCILED",
            "bridge_status": _bridge_status(resolved_bridge),
            "next_action": (
                "No broker call was needed because fresh position truth already "
                "shows the requested management target."
            ),
        }
        _append_audit(payload, audit_path)
        return payload
    duplicate = _find_prior_management_effect(selected, audit_path)
    if duplicate is not None:
        payload = {
            **base,
            "status": "DUPLICATE_SUPPRESSED",
            "duplicate_of_audit_id": duplicate.get("audit_id"),
            "duplicate_of_status": duplicate.get("status"),
            "next_action": (
                "Refresh broker position truth. The same one-shot or exact-target "
                "management action already reached, or may have reached, the broker."
            ),
        }
        _append_audit(payload, audit_path)
        return payload

    if position_preflight.get("status") != "READY":
        payload = {
            **base,
            "status": "POSITION_TRUTH_BLOCKED",
            "position_truth_preflight": position_preflight,
            "bridge_status": _bridge_status(resolved_bridge),
            "next_action": (
                "Refresh the exact broker position and rebuild the management "
                "handoff before any broker method is called."
            ),
        }
        _append_audit(payload, audit_path)
        return payload

    dispatch_result = order_dispatch.dispatch_trade_management_action(
        selected,
        bridge=resolved_bridge,
        config=config,
    )
    guard_report = dispatch_result.get("execution_guard")
    if dispatch_result.get("status") == "EXECUTION_GUARD_BLOCKED":
        payload = {
            **base,
            "status": "EXECUTION_GUARD_BLOCKED",
            "execution_guard": guard_report,
            "order_dispatch": dispatch_result,
            "bridge_status": _bridge_status(resolved_bridge),
            "next_action": "Resolve the execution-guard blocker and refresh broker truth before retrying.",
        }
        _append_audit(payload, audit_path)
        return payload
    if dispatch_result.get("status") == "BRIDGE_ERROR":
        payload = {
            **base,
            "status": "BRIDGE_ERROR",
            "execution_guard": guard_report,
            "order_dispatch": dispatch_result,
            "bridge_status": _bridge_status(resolved_bridge),
            "broker_touched": True,
            "broker_method_called": True,
            "broker_result": dispatch_result.get("broker_result") or {},
            "next_action": "Inspect broker terminal state and account reconciliation before retrying.",
        }
        payload["post_execution_refresh"] = _run_post_execution_refresh(
            post_execution_refresh,
            payload,
            broker_state_may_have_changed=True,
        )
        payload["post_execution_refresh_status"] = payload["post_execution_refresh"].get("status")
        _append_audit(payload, audit_path)
        return payload

    result = dict(dispatch_result.get("broker_result") or {})

    receipt = (
        _reconcile_post_execution(resolved_bridge, selected, result)
        if result.get("accepted")
        else _receipt_not_requested("Broker rejected the management action before receipt reconciliation.")
    )
    status = _execution_status(result, receipt)
    refresh_report = (
        _run_post_execution_refresh(
            post_execution_refresh,
            {
                **base,
                "status": status,
                "selected_action": dict(selected),
                "broker_result": result,
                "terminal_receipt": receipt,
                "terminal_receipt_status": receipt.get("status"),
            },
            broker_state_may_have_changed=True,
        )
        if result.get("accepted")
        else _post_execution_refresh_not_requested(
            "Broker rejected the management action before account panels needed a post-execution refresh."
        )
    )
    payload = {
        **base,
        "status": status,
        "execution_guard": guard_report,
        "order_dispatch": dispatch_result,
        "bridge_status": _bridge_status(resolved_bridge),
        "broker_touched": True,
        "broker_method_called": True,
        "broker_result": result,
        "terminal_receipt": receipt,
        "terminal_receipt_status": receipt.get("status"),
        "post_execution_refresh": refresh_report,
        "post_execution_refresh_status": refresh_report.get("status"),
    }
    payload["next_action"] = _post_execution_next_action(result, receipt, refresh_report)
    _append_audit(payload, audit_path)
    return payload


def latest_ai_hedge_management_execution(
    audit_path: Path | str = DEFAULT_AUDIT_PATH,
) -> dict[str, Any]:
    path = Path(audit_path)
    if not path.exists():
        return {
            "report_kind": "cas_forex_ai_hedge_management_execution_latest",
            "status": "NO_AUDIT_YET",
            "broker_touched": False,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    latest = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            latest = json.loads(line)
        except json.JSONDecodeError:
            continue
    return {
        "report_kind": "cas_forex_ai_hedge_management_execution_latest",
        "status": (latest or {}).get("status") if latest else "NO_AUDIT_YET",
        "latest": latest or {},
        "broker_touched": bool((latest or {}).get("broker_touched")),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _build_bridge(bridge_factory: Callable[[], Any] | None) -> Any:
    if bridge_factory is not None:
        return bridge_factory()
    from cas_forex.broker_control import select_bridge

    return select_bridge()


def _select_action(actions: list[dict[str, Any]], action_id: str | None) -> dict[str, Any] | None:
    if action_id:
        for action in actions:
            if str(action.get("action_id") or "") == str(action_id):
                return action
        return None
    return actions[0] if actions else None


def _management_action_identity(action: Mapping[str, Any] | None) -> dict[str, str | None]:
    selected = action if isinstance(action, Mapping) else {}
    ticket = str(selected.get("broker_ticket") or "")
    intent = str(selected.get("intent") or "")
    exact_body = {
        "ticket": ticket,
        "intent": intent,
        "method": str(selected.get("broker_method") or ""),
        "volume": _optional_float(selected.get("volume")),
        "previous_stop_loss": _optional_float(selected.get("previous_stop_loss")),
        "stop_loss": _optional_float(selected.get("stop_loss")),
        "previous_take_profit": _optional_float(selected.get("previous_take_profit")),
        "take_profit": _optional_float(selected.get("take_profit")),
    }
    exact_key = hashlib.sha256(
        json.dumps(exact_body, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24]
    once_key = f"{ticket}:{intent}" if ticket and intent in _ONE_SHOT_MANAGEMENT_INTENTS else None
    return {
        "management_action_exact_key": exact_key,
        "management_action_once_key": once_key,
    }


def _find_prior_management_effect(
    action: Mapping[str, Any],
    audit_path: Path | str,
) -> dict[str, Any] | None:
    target = Path(audit_path)
    if not target.exists():
        return None
    identity = _management_action_identity(action)
    target_exact = identity.get("management_action_exact_key")
    target_once = identity.get("management_action_once_key")
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, Mapping):
            continue
        status = str(row.get("status") or "")
        if status not in _TERMINAL_EFFECT_STATUSES and status != "BRIDGE_ERROR":
            continue
        if (
            str(action.get("intent") or "") in _TRUTH_REARMABLE_MANAGEMENT_INTENTS
            and status == "EXECUTED_RECONCILED"
        ):
            continue
        prior_identity = {
            "management_action_exact_key": row.get("management_action_exact_key"),
            "management_action_once_key": row.get("management_action_once_key"),
        }
        if not prior_identity["management_action_exact_key"]:
            prior_identity = _management_action_identity(
                row.get("selected_action") if isinstance(row.get("selected_action"), Mapping) else {}
            )
        exact_match = bool(
            target_exact
            and prior_identity.get("management_action_exact_key") == target_exact
        )
        once_match = bool(
            target_once
            and prior_identity.get("management_action_once_key") == target_once
        )
        if exact_match or once_match:
            return dict(row)
    return None


def _base_payload(
    *,
    action_id: str | None,
    selected_action: Mapping[str, Any] | None,
    handoff: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    identity = _management_action_identity(selected_action)
    payload = {
        "report_kind": REPORT_KIND,
        "generated_at_iso": utc_now().isoformat(),
        "requested_action_id": action_id,
        "selected_action_id": (selected_action or {}).get("action_id"),
        "selected_action": dict(selected_action or {}),
        "handoff_status": handoff.get("status"),
        "handoff_movement_stream_id": handoff.get("movement_stream_id"),
        "handoff_price_source_status": handoff.get("price_source_status"),
        "reason": str(reason or "AI_OPERATOR_EDGE_MANAGEMENT")[:300],
        "dry_run_only": False,
        "per_action_owner_confirmation_required": False,
        "autonomous_execution_authority": "OWNER_DELEGATED_WITHIN_GATES",
        "broker_touched": False,
        "broker_method_called": False,
        "orders_placed": False,
        "money_moved": False,
        "external_money_movement": False,
        "claim_boundary": CLAIM_BOUNDARY,
        **identity,
    }
    payload["audit_id"] = _audit_id(payload)
    return payload


def _execution_status(result: Mapping[str, Any], receipt: Mapping[str, Any]) -> str:
    if not result.get("accepted"):
        return "REJECTED"
    receipt_status = str(receipt.get("status") or "")
    if receipt_status == "RECONCILED":
        return "EXECUTED_RECONCILED"
    if receipt_status == "NOT_RECONCILED":
        return "EXECUTED_NOT_RECONCILED"
    return "EXECUTED_RECONCILIATION_UNAVAILABLE"


def _management_position_preflight(
    bridge: Any,
    action: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a management draft to the bridge's current position state."""

    positions_result = _read_bridge_positions(bridge)
    if positions_result.get("status") != "POSITIONS_READ":
        return {
            "status": "BLOCKED",
            "reason": positions_result.get("reason") or "Bridge position truth is unavailable.",
            "positions_source": positions_result.get("source"),
        }
    ticket = int(action.get("broker_ticket"))
    positions = [
        row for row in (positions_result.get("positions") or []) if isinstance(row, Mapping)
    ]
    position = _position_by_ticket(positions, ticket)
    method = str(action.get("broker_method") or "")
    if position is None:
        expected_remaining = _optional_float(action.get("expected_remaining_volume"))
        if (
            method == "close_position"
            and expected_remaining is not None
            and _float_matches(expected_remaining, 0.0)
        ):
            return {
                "status": "ALREADY_APPLIED",
                "receipt": {
                    "status": "RECONCILED",
                    "method": method,
                    "ticket": ticket,
                    "expected_remaining_volume": 0.0,
                    "actual_remaining_volume": 0.0,
                    "positions_source": positions_result.get("source"),
                    "reason": "Fresh broker truth already shows the position fully closed.",
                },
            }
        return {
            "status": "BLOCKED",
            "reason": "The targeted broker ticket is not present in fresh open-position truth.",
            "ticket": ticket,
            "positions_source": positions_result.get("source"),
        }

    if method == "modify_position":
        expected_sl = _optional_float(action.get("stop_loss"))
        actual_sl = _position_float(position, "stop_loss", "sl")
        expected_tp = _optional_float(action.get("take_profit"))
        actual_tp = _position_float(position, "take_profit", "tp")
        sl_matches = _float_matches(actual_sl, expected_sl)
        tp_matches = expected_tp is None or _protection_value_matches(actual_tp, expected_tp)
        if sl_matches and tp_matches:
            return {
                "status": "ALREADY_APPLIED",
                "receipt": {
                    "status": "RECONCILED",
                    "method": method,
                    "ticket": ticket,
                    "expected_stop_loss": expected_sl,
                    "actual_stop_loss": actual_sl,
                    "expected_take_profit": expected_tp,
                    "actual_take_profit": actual_tp,
                    "positions_source": positions_result.get("source"),
                    "reason": "Fresh broker truth already contains the requested SL/TP target.",
                },
            }
        previous_sl = _optional_float(action.get("previous_stop_loss"))
        previous_tp = _optional_float(action.get("previous_take_profit"))
        if not _protection_value_matches(actual_sl, previous_sl):
            return {
                "status": "BLOCKED",
                "reason": "The broker stop changed after this management draft was built.",
                "method": method,
                "ticket": ticket,
                "expected_previous_stop_loss": previous_sl,
                "actual_stop_loss": actual_sl,
                "positions_source": positions_result.get("source"),
            }
        if not _protection_value_matches(actual_tp, previous_tp):
            return {
                "status": "BLOCKED",
                "reason": "The broker take profit changed after this management draft was built.",
                "method": method,
                "ticket": ticket,
                "expected_previous_take_profit": previous_tp,
                "actual_take_profit": actual_tp,
                "positions_source": positions_result.get("source"),
            }
        return {
            "status": "READY",
            "method": method,
            "ticket": ticket,
            "positions_source": positions_result.get("source"),
        }

    if method == "close_position":
        actual_volume = _position_float(position, "volume", "lots", "lot_size")
        expected_volume = _optional_float(action.get("original_volume"))
        if not _float_matches(actual_volume, expected_volume):
            return {
                "status": "BLOCKED",
                "reason": "The broker position volume changed after this close draft was built.",
                "method": method,
                "ticket": ticket,
                "expected_original_volume": expected_volume,
                "actual_volume": actual_volume,
                "positions_source": positions_result.get("source"),
            }
        return {
            "status": "READY",
            "method": method,
            "ticket": ticket,
            "positions_source": positions_result.get("source"),
        }

    return {
        "status": "BLOCKED",
        "reason": f"Unsupported management method {method}.",
        "ticket": ticket,
        "positions_source": positions_result.get("source"),
    }


def _reconcile_post_execution(
    bridge: Any,
    action: Mapping[str, Any],
    broker_result: Mapping[str, Any],
) -> dict[str, Any]:
    method = str(action.get("broker_method") or "")
    ticket = int(action.get("broker_ticket"))
    positions_result = _read_bridge_positions(bridge)
    if positions_result.get("status") != "POSITIONS_READ":
        return {
            "status": "RECONCILIATION_UNAVAILABLE",
            "reason": positions_result.get("reason"),
            "method": method,
            "ticket": ticket,
            "broker_result_status": broker_result.get("status"),
            "positions_source": positions_result.get("source"),
        }
    positions = [
        row for row in (positions_result.get("positions") or []) if isinstance(row, Mapping)
    ]
    position = _position_by_ticket(positions, ticket)
    if method == "modify_position":
        return _reconcile_modify(action, position, positions_result)
    if method == "close_position":
        return _reconcile_close(action, position, positions_result)
    return {
        "status": "RECONCILIATION_UNAVAILABLE",
        "reason": f"Unsupported management method {method}.",
        "method": method,
        "ticket": ticket,
        "positions_source": positions_result.get("source"),
    }


def _read_bridge_positions(bridge: Any) -> dict[str, Any]:
    for method in ("get_all_open_positions", "get_open_positions"):
        fn = getattr(bridge, method, None)
        if not callable(fn):
            continue
        try:
            rows = fn()
        except Exception as exc:
            return {
                "status": "POSITIONS_UNAVAILABLE",
                "source": method,
                "reason": f"{type(exc).__name__}: {exc}",
            }
        if rows is None:
            return {
                "status": "POSITIONS_UNAVAILABLE",
                "source": method,
                "reason": "Bridge returned no position collection.",
            }
        return {
            "status": "POSITIONS_READ",
            "source": method,
            "positions": [dict(row) if isinstance(row, Mapping) else _object_payload(row) for row in rows],
        }
    return {
        "status": "POSITIONS_UNAVAILABLE",
        "source": None,
        "reason": "Bridge exposes no get_all_open_positions or get_open_positions method.",
    }


def _reconcile_modify(
    action: Mapping[str, Any],
    position: Mapping[str, Any] | None,
    positions_result: Mapping[str, Any],
) -> dict[str, Any]:
    ticket = int(action.get("broker_ticket"))
    if position is None:
        return {
            "status": "NOT_RECONCILED",
            "method": "modify_position",
            "ticket": ticket,
            "reason": "Modified ticket is not present in the bridge open-position snapshot.",
            "positions_source": positions_result.get("source"),
        }
    actual_sl = _position_float(position, "stop_loss", "sl")
    expected_sl = _optional_float(action.get("stop_loss"))
    if actual_sl is None:
        return {
            "status": "RECONCILIATION_UNAVAILABLE",
            "method": "modify_position",
            "ticket": ticket,
            "reason": "Bridge position snapshot does not expose stop_loss/sl.",
            "actual_position": _compact_position(position),
            "positions_source": positions_result.get("source"),
        }
    tp_check = _tp_matches(action, position)
    sl_matches = _float_matches(actual_sl, expected_sl)
    if sl_matches and tp_check.get("matches"):
        return {
            "status": "RECONCILED",
            "method": "modify_position",
            "ticket": ticket,
            "expected_stop_loss": expected_sl,
            "actual_stop_loss": actual_sl,
            "expected_take_profit": tp_check.get("expected_take_profit"),
            "actual_take_profit": tp_check.get("actual_take_profit"),
            "actual_position": _compact_position(position),
            "positions_source": positions_result.get("source"),
        }
    return {
        "status": "NOT_RECONCILED",
        "method": "modify_position",
        "ticket": ticket,
        "expected_stop_loss": expected_sl,
        "actual_stop_loss": actual_sl,
        "expected_take_profit": tp_check.get("expected_take_profit"),
        "actual_take_profit": tp_check.get("actual_take_profit"),
        "reason": "Bridge accepted modify_position, but the open-position snapshot does not show the requested SL/TP.",
        "actual_position": _compact_position(position),
        "positions_source": positions_result.get("source"),
    }


def _reconcile_close(
    action: Mapping[str, Any],
    position: Mapping[str, Any] | None,
    positions_result: Mapping[str, Any],
) -> dict[str, Any]:
    ticket = int(action.get("broker_ticket"))
    expected_remaining = _optional_float(action.get("expected_remaining_volume"))
    close_volume = _optional_float(action.get("volume"))
    if position is None:
        if expected_remaining is None or _float_matches(expected_remaining, 0.0):
            return {
                "status": "RECONCILED",
                "method": "close_position",
                "ticket": ticket,
                "expected_remaining_volume": expected_remaining,
                "actual_remaining_volume": 0.0,
                "positions_source": positions_result.get("source"),
            }
        return {
            "status": "NOT_RECONCILED",
            "method": "close_position",
            "ticket": ticket,
            "close_volume": close_volume,
            "expected_remaining_volume": expected_remaining,
            "actual_remaining_volume": 0.0,
            "reason": "Partial-close draft expected the position to remain open, but the ticket is absent.",
            "positions_source": positions_result.get("source"),
        }
    actual_volume = _position_float(position, "volume", "lots", "lot_size")
    if actual_volume is None:
        return {
            "status": "RECONCILIATION_UNAVAILABLE",
            "method": "close_position",
            "ticket": ticket,
            "close_volume": close_volume,
            "reason": "Bridge position snapshot does not expose remaining volume.",
            "actual_position": _compact_position(position),
            "positions_source": positions_result.get("source"),
        }
    if expected_remaining is not None and _float_matches(actual_volume, expected_remaining):
        return {
            "status": "RECONCILED",
            "method": "close_position",
            "ticket": ticket,
            "close_volume": close_volume,
            "expected_remaining_volume": expected_remaining,
            "actual_remaining_volume": actual_volume,
            "actual_position": _compact_position(position),
            "positions_source": positions_result.get("source"),
        }
    if expected_remaining is None and actual_volume >= 0:
        return {
            "status": "RECONCILIATION_UNAVAILABLE",
            "method": "close_position",
            "ticket": ticket,
            "close_volume": close_volume,
            "actual_remaining_volume": actual_volume,
            "reason": "Position remains open, but the action did not provide an expected remaining volume.",
            "actual_position": _compact_position(position),
            "positions_source": positions_result.get("source"),
        }
    return {
        "status": "NOT_RECONCILED",
        "method": "close_position",
        "ticket": ticket,
        "close_volume": close_volume,
        "expected_remaining_volume": expected_remaining,
        "actual_remaining_volume": actual_volume,
        "reason": "Bridge accepted close_position, but remaining volume does not match the expected receipt state.",
        "actual_position": _compact_position(position),
        "positions_source": positions_result.get("source"),
    }


def _receipt_not_requested(reason: str) -> dict[str, Any]:
    return {
        "status": "NOT_REQUESTED",
        "reason": reason,
    }


def _run_post_execution_refresh(
    callback: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
    payload: Mapping[str, Any],
    *,
    broker_state_may_have_changed: bool,
) -> dict[str, Any]:
    if callback is None:
        return _post_execution_refresh_not_requested(
            "No API post-execution refresh callback was configured for this execution path.",
            broker_state_may_have_changed=broker_state_may_have_changed,
        )
    if not broker_state_may_have_changed:
        return _post_execution_refresh_not_requested(
            "Broker state was not touched, so no post-execution refresh was requested.",
            broker_state_may_have_changed=False,
        )
    try:
        report = callback(payload)
    except Exception as exc:  # pragma: no cover - defensive evidence wrapper.
        return {
            "status": "REFRESH_FAILED",
            "error_type": type(exc).__name__,
            "detail": str(exc),
            "broker_state_may_have_changed": True,
        }
    if isinstance(report, Mapping):
        out = dict(report)
        out.setdefault("status", "REFRESH_RAN")
        out.setdefault("broker_state_may_have_changed", True)
        return out
    return {
        "status": "REFRESH_UNAVAILABLE",
        "detail": f"Refresh callback returned {type(report).__name__}, not a mapping.",
        "broker_state_may_have_changed": True,
    }


def _post_execution_refresh_not_requested(
    reason: str,
    *,
    broker_state_may_have_changed: bool = False,
) -> dict[str, Any]:
    return {
        "status": "NOT_REQUESTED",
        "reason": reason,
        "broker_state_may_have_changed": bool(broker_state_may_have_changed),
    }


def _post_execution_next_action(
    broker_result: Mapping[str, Any],
    receipt: Mapping[str, Any],
    refresh_report: Mapping[str, Any],
) -> str:
    refresh_status = str(refresh_report.get("status") or "")
    refresh_ok = refresh_status in {"REFRESH_RAN", "REFRESH_PARTIAL"}
    refresh_failed = refresh_status in {"REFRESH_FAILED", "REFRESH_UNAVAILABLE"}
    if receipt.get("status") == "RECONCILED":
        if refresh_ok:
            return (
                "Receipt reconciled against current bridge position state and post-execution "
                "broker/account refresh ran; verify dashboard, live telemetry, and account reconciliation panels."
            )
        if refresh_failed:
            return (
                "Receipt reconciled against current bridge position state, but post-execution "
                "broker/account refresh failed. Manually refresh broker truth and account reconciliation before follow-up action."
            )
        return (
            "Receipt reconciled against current bridge position state; refresh the dashboard/account reconciliation "
            "to show the new state everywhere."
        )
    if broker_result.get("accepted"):
        if refresh_ok:
            return (
                "Bridge accepted the action, terminal receipt reconciliation is not proven, and post-execution "
                "broker/account refresh ran. Inspect broker truth/account reconciliation before any retry or follow-up action."
            )
        return (
            "Bridge accepted the action, but terminal receipt reconciliation is not proven. Inspect broker truth/account "
            "reconciliation before any retry or follow-up action."
        )
    return "Review the broker rejection, refresh broker truth, and retry only if the handoff remains current."


def _position_by_ticket(
    positions: list[Mapping[str, Any]],
    ticket: int,
) -> Mapping[str, Any] | None:
    for position in positions:
        for key in ("ticket", "broker_ticket", "position", "position_id"):
            value = position.get(key)
            try:
                if int(str(value)) == int(ticket):
                    return position
            except (TypeError, ValueError):
                continue
    return None


def _tp_matches(action: Mapping[str, Any], position: Mapping[str, Any]) -> dict[str, Any]:
    expected = _optional_float(action.get("take_profit"))
    if expected is None:
        return {
            "matches": True,
            "expected_take_profit": None,
            "actual_take_profit": _position_float(position, "take_profit", "tp"),
        }
    actual = _position_float(position, "take_profit", "tp")
    return {
        "matches": actual is not None and _float_matches(actual, expected),
        "expected_take_profit": expected,
        "actual_take_profit": actual,
    }


def _position_float(position: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = position.get(key)
        parsed = _optional_float(value)
        if parsed is not None:
            return parsed
    return None


def _float_matches(left: float | None, right: float | None, *, tolerance: float = 1e-6) -> bool:
    if left is None or right is None:
        return False
    return abs(float(left) - float(right)) <= tolerance


def _protection_value_matches(left: float | None, right: float | None) -> bool:
    normalized_left = None if left is None or left <= 0 else float(left)
    normalized_right = None if right is None or right <= 0 else float(right)
    if normalized_left is None or normalized_right is None:
        return normalized_left is None and normalized_right is None
    return _float_matches(normalized_left, normalized_right)


def _compact_position(position: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: position.get(key)
        for key in (
            "ticket",
            "broker_ticket",
            "position",
            "symbol",
            "type",
            "side",
            "volume",
            "lots",
            "lot_size",
            "open_price",
            "current_price",
            "stop_loss",
            "sl",
            "take_profit",
            "tp",
            "profit",
            "comment",
        )
        if key in position
    }


def _object_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    out: dict[str, Any] = {}
    for key in (
        "ticket",
        "position",
        "symbol",
        "type",
        "volume",
        "price_open",
        "price_current",
        "profit",
        "swap",
        "comment",
        "sl",
        "tp",
    ):
        if hasattr(value, key):
            out[key] = getattr(value, key)
    return out


def _bridge_status(bridge: Any) -> dict[str, Any]:
    return {
        "bridge_class": getattr(getattr(bridge, "__class__", type(bridge)), "__name__", ""),
        "connected": _safe_bool_call(bridge, "is_connected"),
        "will_execute_real_order": _safe_bool_call(bridge, "will_execute_real_order"),
    }


def _safe_bool_call(obj: Any, method: str) -> bool | None:
    fn = getattr(obj, method, None)
    if not callable(fn):
        return None
    try:
        return bool(fn())
    except Exception:
        return None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _append_audit(payload: Mapping[str, Any], audit_path: Path | str) -> None:
    path = Path(audit_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def _audit_id(payload: Mapping[str, Any]) -> str:
    body = json.dumps(
        {
            "report_kind": payload.get("report_kind"),
            "selected_action_id": payload.get("selected_action_id"),
            "generated_at_iso": payload.get("generated_at_iso"),
            "reason": payload.get("reason"),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
