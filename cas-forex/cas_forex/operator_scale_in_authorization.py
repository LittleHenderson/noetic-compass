"""One-shot authorization for an AI Operator-selected winning scale-in.

This is the compound-order equivalent of edge_authorization: a model decision
binds one exact add order to one parent still net winning after reported costs,
configuration, and sizing plan. The authorization is consumed immediately
before the broker call and cannot be replayed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from cas_forex.execution_provenance import _config_snapshot, _hash_payload
from cas_forex.edge_authorization import EdgeNotAuthorized
from cas_forex.operator_account_context import (
    position_is_net_winning_after_reported_costs,
)
from cas_forex.time_utils import ensure_utc, utc_now


class OperatorScaleInNotAuthorized(EdgeNotAuthorized):
    """Raised when a compound add lacks a fresh exact Operator decision."""


@dataclass(frozen=True)
class _Authorization:
    decision_ref: str
    order_hash: str
    parent_ticket: str
    parent_snapshot_hash: str
    operator_event_hash: str
    sizing_plan_hash: str
    sizing_ref: str
    authorized_at: str
    max_age_seconds: float
    config_hash: str | None
    broker_account_ref: str | None


_REGISTRY: dict[str, _Authorization] = {}
_CONSUMED: dict[str, str] = {}


def authorize(
    order: Any,
    *,
    parent_position: Mapping[str, Any],
    operator_event_hash: str,
    sizing_plan_hash: str,
    sizing_ref: str,
    bridge: Any,
    config: Any = None,
    max_age_seconds: float = 90.0,
) -> dict[str, Any]:
    decision_ref = str(_field(order, "decision_ref") or "").strip()
    parent_ticket = str(
        parent_position.get("broker_ticket")
        or parent_position.get("ticket")
        or parent_position.get("position")
        or ""
    ).strip()
    if not decision_ref:
        raise ValueError("scale-in decision_ref is required")
    if decision_ref in _CONSUMED:
        raise OperatorScaleInNotAuthorized(
            f"Operator scale-in authorization for {decision_ref!r} was already consumed; "
            "a fresh parent snapshot and new scale-in unit decision are required"
        )
    if not parent_ticket:
        raise ValueError("scale-in parent broker ticket is required")
    if not str(operator_event_hash or "").strip():
        raise ValueError("scale-in Operator event hash is required")
    if not str(sizing_plan_hash or "").strip() or not str(sizing_ref or "").strip():
        raise ValueError("scale-in sizing plan hash and sizing_ref are required")
    if not _position_is_winning(parent_position):
        raise OperatorScaleInNotAuthorized(
            "Operator scale-in authorization requires a parent that is net winning after reported carry and costs"
        )
    record = _Authorization(
        decision_ref=decision_ref,
        order_hash=_order_hash(order),
        parent_ticket=parent_ticket,
        parent_snapshot_hash=_parent_hash(parent_position),
        operator_event_hash=str(operator_event_hash),
        sizing_plan_hash=str(sizing_plan_hash),
        sizing_ref=str(sizing_ref),
        authorized_at=utc_now().isoformat(),
        max_age_seconds=max(1.0, float(max_age_seconds)),
        config_hash=_config_hash(config),
        broker_account_ref=_bridge_account_ref(bridge),
    )
    _REGISTRY[decision_ref] = record
    return _payload(record, status="AUTHORIZED")


def is_required(decision_ref: Any) -> bool:
    key = str(decision_ref or "")
    return key in _REGISTRY or key in _CONSUMED


def require(
    order: Any,
    *,
    proposed_intent: Mapping[str, Any] | None,
    bridge: Any,
    config: Any = None,
) -> dict[str, Any]:
    decision_ref = str(_field(order, "decision_ref") or "")
    record = _REGISTRY.get(decision_ref)
    if record is None:
        if decision_ref in _CONSUMED:
            raise OperatorScaleInNotAuthorized(
                f"Operator scale-in authorization for {decision_ref!r} was already consumed"
            )
        raise OperatorScaleInNotAuthorized(
            f"no Operator scale-in authorization exists for {decision_ref!r}"
        )
    age = (ensure_utc(utc_now()) - ensure_utc(datetime.fromisoformat(record.authorized_at))).total_seconds()
    if age < 0 or age > record.max_age_seconds:
        raise OperatorScaleInNotAuthorized(
            f"Operator scale-in authorization is stale ({age:.1f}s > {record.max_age_seconds:.1f}s)"
        )
    if _order_hash(order) != record.order_hash:
        raise OperatorScaleInNotAuthorized("scale-in order geometry differs from the Operator selection")
    proposed = dict(proposed_intent or {})
    if str(proposed.get("parent_broker_ticket") or "") != record.parent_ticket:
        raise OperatorScaleInNotAuthorized("scale-in parent ticket differs from the Operator selection")
    if str(proposed.get("operator_event_hash") or "") != record.operator_event_hash:
        raise OperatorScaleInNotAuthorized("scale-in Operator event hash mismatch")
    if str(proposed.get("sizing_plan_hash") or "") != record.sizing_plan_hash:
        raise OperatorScaleInNotAuthorized("scale-in sizing plan changed after Operator selection")
    if str(proposed.get("sizing_ref") or "") != record.sizing_ref:
        raise OperatorScaleInNotAuthorized("scale-in sizing_ref changed after Operator selection")
    if record.config_hash is not None and _config_hash(config) != record.config_hash:
        raise OperatorScaleInNotAuthorized("effective configuration changed after scale-in selection")
    if record.broker_account_ref is not None and _bridge_account_ref(bridge) != record.broker_account_ref:
        raise OperatorScaleInNotAuthorized("broker account changed after scale-in selection")
    parent = _current_parent(bridge, record.parent_ticket)
    if parent is None:
        raise OperatorScaleInNotAuthorized("authorized net-winning parent position is no longer open")
    if not _position_is_winning(parent):
        raise OperatorScaleInNotAuthorized(
            "parent position is no longer net winning after reported carry and costs at dispatch time"
        )
    if _parent_hash(parent) != record.parent_snapshot_hash:
        raise OperatorScaleInNotAuthorized(
            "parent position volume or protective geometry changed after Operator selection"
        )
    return _payload(record, status="READY")


def consume(
    order: Any,
    *,
    proposed_intent: Mapping[str, Any] | None,
    bridge: Any,
    config: Any = None,
) -> dict[str, Any]:
    payload = require(
        order,
        proposed_intent=proposed_intent,
        bridge=bridge,
        config=config,
    )
    decision_ref = str(_field(order, "decision_ref") or "")
    record = _REGISTRY.pop(decision_ref, None)
    if record is not None:
        _CONSUMED[decision_ref] = record.authorized_at
    return {**payload, "status": "CONSUMED"}


def reset() -> None:
    _REGISTRY.clear()
    _CONSUMED.clear()


def _current_parent(bridge: Any, ticket: str) -> dict[str, Any] | None:
    for name in ("get_open_positions_all", "get_open_positions"):
        getter = getattr(bridge, name, None)
        if not callable(getter):
            continue
        try:
            rows = list(getter() or [])
        except Exception:
            continue
        for raw in rows:
            row = _mapping(raw)
            current_ticket = str(row.get("broker_ticket") or row.get("ticket") or row.get("position") or "")
            if current_ticket == str(ticket):
                return row
    return None


def _position_is_winning(position: Mapping[str, Any]) -> bool:
    return position_is_net_winning_after_reported_costs(position)


def _order_hash(order: Any) -> str:
    payload = {
        key: _field(order, key)
        for key in (
            "order_id",
            "decision_ref",
            "symbol",
            "order_type",
            "direction",
            "volume",
            "price",
            "stop_loss",
            "take_profit",
            "comment",
            "magic_number",
        )
    }
    payload["order_type"] = getattr(payload["order_type"], "value", payload["order_type"])
    payload["direction"] = _direction(payload["direction"])
    return _hash(payload)


def _parent_hash(position: Mapping[str, Any]) -> str:
    def value(*keys: str) -> Any:
        for key in keys:
            if key in position and position.get(key) is not None:
                return position.get(key)
        return None

    return _hash(
        {
            "ticket": value("broker_ticket", "ticket", "position"),
            "symbol": position.get("symbol"),
            "side": _direction(value("side", "direction", "type")),
            "volume": value("lot_size", "volume", "lots"),
            "open_price": value("open_price", "price_open"),
            "stop_loss": value("stop_loss", "sl"),
            "take_profit": value("take_profit", "tp"),
        }
    )


def _config_hash(config: Any) -> str | None:
    try:
        snapshot = _config_snapshot(config)
    except Exception:
        return None
    return _hash_payload(snapshot) if snapshot else None


def _bridge_account_ref(bridge: Any) -> str | None:
    getter = getattr(bridge, "get_account_info", None)
    raw: Any = None
    if callable(getter):
        try:
            raw = getter()
        except Exception:
            raw = None
    account = _mapping(raw)
    login = account.get("login") or getattr(bridge, "login", None)
    server = account.get("server") or getattr(bridge, "server", None)
    if login or server:
        return _hash({"login": login, "server": server})[:20]
    return type(bridge).__name__ if bridge is not None else None


def _payload(record: _Authorization, *, status: str) -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_operator_scale_in_authorization",
        "status": status,
        "decision_ref": record.decision_ref,
        "parent_ticket": record.parent_ticket,
        "parent_snapshot_hash": record.parent_snapshot_hash,
        "operator_event_hash": record.operator_event_hash,
        "sizing_plan_hash": record.sizing_plan_hash,
        "sizing_ref": record.sizing_ref,
        "authorized_at": record.authorized_at,
        "max_age_seconds": record.max_age_seconds,
        "one_shot": True,
    }


def _field(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, Mapping) else getattr(value, key, None)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    return {
        key: getattr(value, key)
        for key in (
            "broker_ticket",
            "ticket",
            "position",
            "symbol",
            "side",
            "direction",
            "type",
            "volume",
            "lots",
            "lot_size",
            "open_price",
            "price_open",
            "current_price",
            "price_current",
            "stop_loss",
            "sl",
            "take_profit",
            "tp",
            "floating_pnl_usd",
            "profit",
            "position_price_pnl_usd",
            "swap_usd",
            "swap",
            "commission_usd",
            "commission",
            "net_open_pnl_after_reported_costs_usd",
        )
        if hasattr(value, key)
    }


def _direction(value: Any) -> str:
    raw = getattr(value, "value", value)
    text = str(raw or "").upper()
    if text in {"BUY", "LONG", "0"}:
        return "LONG"
    if text in {"SELL", "SHORT", "1"}:
        return "SHORT"
    return text


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "OperatorScaleInNotAuthorized",
    "authorize",
    "consume",
    "is_required",
    "require",
    "reset",
]
