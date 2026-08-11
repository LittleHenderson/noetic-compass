"""Edge-authorization registry — the fail-closed lock between the WASTE loop's
TEST gate and the broker.

An order may reach a broker bridge through ``execution_guard.guarded_place_order``
ONLY if a fresh PASS from the edge gate (``edge_gate``) has been registered for the
order's ``decision_ref`` AND the order's geometry still matches what was tested.

This closes the architecture audit's fail-closed hole: the requirement rides on the
order's ``decision_ref`` + this registry, NOT an opt-in call-site kwarg that every
existing caller would silently skip. Two rules at the chokepoint:

  * REAL-MONEY (live) dispatch ALWAYS requires a registered, fresh, matching PASS —
    no PASS => the bridge is never touched.
  * Any order whose ``decision_ref`` the WASTE loop registered (``is_required``) is
    likewise gated. The loop registers its PASS immediately before it builds the
    order, so it is structurally incapable of dispatching without a tested edge.

Legacy paper paths that never went through the loop and are not live are unaffected
(they carry no registration and are not real-money), so this does not retro-break the
existing paper-proof dispatch — it only governs real money and the autonomous loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Dict, Optional

from cas_forex.edge_gate import CandidateSetup, EdgeTestDecision, _now_iso, verify_token
from cas_forex.execution_provenance import _config_snapshot, _hash_payload


class EdgeNotAuthorized(PermissionError):
    """Raised at the dispatch chokepoint when an order lacks a fresh, matching edge PASS."""


@dataclass(frozen=True)
class _Authorization:
    token: str
    setup: CandidateSetup
    evaluated_at: str
    max_age_seconds: float
    binding: "_AuthorizationBinding"


@dataclass(frozen=True)
class _AuthorizationBinding:
    mode: Optional[str] = None
    config_hash: Optional[str] = None
    broker_account_ref: Optional[str] = None
    max_volume: Optional[float] = None
    order_type: Optional[str] = None
    price: Optional[float] = None
    strategy_id: Optional[str] = None


# decision_ref -> the PASS authorization minted for it. Populated ONLY by the edge
# gate's PASS via ``authorize``; consulted by ``guarded_place_order`` via
# ``require`` / ``consume``.
_REGISTRY: Dict[str, _Authorization] = {}

# decision_refs that had a PASS and already spent it. This preserves the
# "registered loop decisions are gated" invariant after consumption: a replay of
# the same decision_ref must fail instead of falling through as legacy paper.
_CONSUMED: Dict[str, str] = {}


def authorize(
    decision_ref: str,
    decision: EdgeTestDecision,
    setup: CandidateSetup,
    *,
    max_age_seconds: float = 120.0,
    config: Any = None,
    bridge: Any = None,
    is_real: Optional[bool] = None,
    volume: Any = None,
    order_type: Any = None,
    price: Any = None,
    strategy_id: Any = None,
    proposed_intent: Any = None,
) -> None:
    """Register a PASS so an order with this ``decision_ref`` may dispatch.

    Only a genuine PASS (status == 'PASS' AND a non-empty ``edge_token``) can be
    registered — you cannot authorize a NO_TRADE/underpowered verdict.
    """
    if not decision_ref:
        raise ValueError("decision_ref is required to authorize an edge")
    if decision.status != "PASS" or not decision.edge_token:
        raise EdgeNotAuthorized(
            f"cannot authorize a non-PASS edge (status={decision.status!r})"
        )
    _REGISTRY[str(decision_ref)] = _Authorization(
        token=str(decision.edge_token),
        setup=setup,
        evaluated_at=str(decision.evaluated_at),
        max_age_seconds=float(max_age_seconds),
        binding=_binding_for_context(
            config=config,
            bridge=bridge,
            is_real=is_real,
            volume=volume,
            order_type=order_type,
            price=price,
            strategy_id=strategy_id,
            proposed_intent=proposed_intent,
        ),
    )
    _CONSUMED.pop(str(decision_ref), None)


def is_required(decision_ref: Optional[str]) -> bool:
    """True iff this decision_ref has a registered edge authorization."""
    return bool(decision_ref) and (
        str(decision_ref) in _REGISTRY or str(decision_ref) in _CONSUMED
    )


def clear(decision_ref: str) -> None:
    """Drop one authorization (call after a successful one-shot dispatch)."""
    _REGISTRY.pop(str(decision_ref), None)


def reset() -> None:
    """Clear the whole registry (tests / shutdown)."""
    _REGISTRY.clear()
    _CONSUMED.clear()


def _norm_dir(d: Any) -> str:
    s = getattr(d, "name", None) or getattr(d, "value", None) or d
    s = str(s).strip().upper()
    if s in {"LONG", "BUY"}:
        return "LONG"
    if s in {"SHORT", "SELL"}:
        return "SHORT"
    return s


def _close(a: Any, b: Any) -> bool:
    try:
        a_f, b_f = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return abs(a_f - b_f) <= 1e-6 + 1e-9 * max(abs(a_f), abs(b_f))


def _mapping_value(payload: Any, key: str) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(key)
    return None


def _norm_order_type(value: Any) -> Optional[str]:
    raw = getattr(value, "name", None) or getattr(value, "value", None) or value
    token = str(raw or "").strip().upper()
    return token or None


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        base = config
    else:
        from cas_forex.config import config as default_config

        base = default_config
    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        return apply_live_enable_overrides(base)
    except Exception:
        return base


def _config_hash(config: Any = None) -> Optional[str]:
    cfg = _resolve_config(config)
    snapshot = _config_snapshot(cfg)
    if not snapshot:
        return None
    return _hash_payload(snapshot)


def _bridge_account_ref(bridge: Any) -> Optional[str]:
    if bridge is None:
        return None
    for attr in ("account_id_hash", "account_hash", "broker_account_ref"):
        value = getattr(bridge, attr, None)
        if value:
            return str(value)
    probe = getattr(bridge, "_account_id_hash", None)
    if callable(probe):
        try:
            value = probe()
        except Exception:
            value = None
        if value:
            return str(value)
    login = getattr(bridge, "login", None)
    server = getattr(bridge, "server", None)
    if login or server:
        return _hash_payload({"login": login, "server": server})[:16]
    return None


def _config_account_ref(config: Any = None) -> Optional[str]:
    cfg = _resolve_config(config)
    login = getattr(cfg, "mt5_login", None)
    server = getattr(cfg, "mt5_server", None)
    if login or server:
        return _hash_payload({"login": login, "server": server})[:16]
    return None


def _current_mode(*, is_real: Optional[bool], config: Any = None, bridge: Any = None) -> Optional[str]:
    if is_real is not None:
        return "LIVE" if bool(is_real) else "PAPER"
    if bridge is not None:
        probe = getattr(bridge, "will_execute_real_order", None)
        if callable(probe):
            try:
                return "LIVE" if bool(probe()) else "PAPER"
            except Exception:
                return "LIVE"
    if config is None:
        return None
    return "LIVE" if bool(getattr(_resolve_config(config), "live_mode", False)) else "PAPER"


def _as_positive_float(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _binding_for_context(
    *,
    config: Any = None,
    bridge: Any = None,
    is_real: Optional[bool] = None,
    volume: Any = None,
    order_type: Any = None,
    price: Any = None,
    strategy_id: Any = None,
    proposed_intent: Any = None,
) -> _AuthorizationBinding:
    return _AuthorizationBinding(
        mode=_current_mode(is_real=is_real, config=config, bridge=bridge),
        config_hash=_config_hash(config),
        broker_account_ref=_bridge_account_ref(bridge) or _config_account_ref(config),
        max_volume=_as_positive_float(volume),
        order_type=_norm_order_type(order_type if order_type is not None else _mapping_value(proposed_intent, "order_type")),
        price=_as_float(price if price is not None else _mapping_value(proposed_intent, "price")),
        strategy_id=(
            str(strategy_id).strip()
            if strategy_id is not None and str(strategy_id).strip()
            else (
                str(_mapping_value(proposed_intent, "strategy_id")).strip()
                if _mapping_value(proposed_intent, "strategy_id") not in (None, "")
                else None
            )
        ),
    )


def require(
    order: Any,
    *,
    is_real: bool,
    now_iso: Optional[str] = None,
    config: Any = None,
    bridge: Any = None,
    volume: Any = None,
    order_type: Any = None,
    price: Any = None,
    strategy_id: Any = None,
    proposed_intent: Any = None,
) -> None:
    """Fail-closed gate: raise ``EdgeNotAuthorized`` unless a fresh, matching edge
    PASS is registered for this order's ``decision_ref``.

    Three independent checks, all must hold:
      1. an authorization exists for the order's decision_ref;
      2. its token is still authentic AND unexpired (delegated to
         ``edge_gate.verify_token``, which binds to the exact tested geometry+time);
      3. the ORDER's stable geometry (symbol, direction, stop-loss, take-profit)
         matches the authorized setup — no swapping the trade after the PASS.
    """
    now = now_iso or _now_iso()
    decision_ref = getattr(order, "decision_ref", None)
    record = _REGISTRY.get(str(decision_ref)) if decision_ref else None
    if record is None:
        if decision_ref and str(decision_ref) in _CONSUMED:
            raise EdgeNotAuthorized(
                f"edge authorization for decision_ref={decision_ref!r} was already consumed; "
                "re-test required before another dispatch"
            )
        raise EdgeNotAuthorized(
            f"no edge authorization for decision_ref={decision_ref!r}: the TEST gate must "
            f"PASS and register before dispatch ({'live' if is_real else 'loop'} order refused)"
        )
    if not verify_token(
        record.token, record.setup, record.evaluated_at,
        now_iso=now, max_age_seconds=record.max_age_seconds,
    ):
        raise EdgeNotAuthorized(
            f"edge token for decision_ref={decision_ref!r} is invalid or stale — re-test required"
        )
    s = record.setup
    if (
        str(getattr(order, "symbol", "")) != str(s.symbol)
        or _norm_dir(getattr(order, "direction", "")) != _norm_dir(s.direction)
        or not _close(getattr(order, "stop_loss", float("nan")), s.stop_loss)
        or not _close(getattr(order, "take_profit", float("nan")), s.take_profit)
    ):
        raise EdgeNotAuthorized(
            f"order geometry diverges from the authorized edge for decision_ref={decision_ref!r}"
        )
    binding = record.binding
    current_order_type = _norm_order_type(
        order_type
        if order_type is not None
        else getattr(order, "order_type", None) or _mapping_value(proposed_intent, "order_type")
    )
    current_price = _as_float(
        price
        if price is not None
        else getattr(order, "price", None) if getattr(order, "price", None) is not None else _mapping_value(proposed_intent, "price")
    )
    current_strategy_id = (
        str(strategy_id).strip()
        if strategy_id is not None and str(strategy_id).strip()
        else (
            str(_mapping_value(proposed_intent, "strategy_id")).strip()
            if _mapping_value(proposed_intent, "strategy_id") not in (None, "")
            else None
        )
    )
    if binding.order_type is not None:
        if current_order_type is None:
            raise EdgeNotAuthorized(
                f"edge authorization for decision_ref={decision_ref!r} is bound to order type "
                f"{binding.order_type}, but current order type is unavailable"
            )
        if current_order_type != binding.order_type:
            raise EdgeNotAuthorized(
                f"edge authorization order type mismatch for decision_ref={decision_ref!r}: "
                f"authorized for {binding.order_type}, current order is {current_order_type}"
            )
    if binding.price is not None:
        if current_price is None:
            raise EdgeNotAuthorized(
                f"edge authorization for decision_ref={decision_ref!r} is bound to price "
                f"{binding.price:g}, but current order price is unavailable"
            )
        if not _close(current_price, binding.price):
            raise EdgeNotAuthorized(
                f"edge authorization price mismatch for decision_ref={decision_ref!r}: "
                f"authorized for {binding.price:g}, current order is {current_price:g}"
            )
    if binding.strategy_id is not None:
        if current_strategy_id is None:
            raise EdgeNotAuthorized(
                f"edge authorization for decision_ref={decision_ref!r} is bound to strategy "
                f"{binding.strategy_id}, but current strategy is unavailable"
            )
        if current_strategy_id != binding.strategy_id:
            raise EdgeNotAuthorized(
                f"edge authorization strategy mismatch for decision_ref={decision_ref!r}: "
                f"authorized for {binding.strategy_id}, current strategy is {current_strategy_id}"
            )
    if is_real:
        current = _binding_for_context(
            config=config,
            bridge=bridge,
            is_real=is_real,
            volume=volume if volume is not None else getattr(order, "volume", None),
            order_type=current_order_type,
            price=current_price,
            strategy_id=current_strategy_id,
            proposed_intent=proposed_intent,
        )
        if binding.mode is not None:
            if current.mode is None:
                raise EdgeNotAuthorized(
                    f"edge authorization for decision_ref={decision_ref!r} is bound to mode "
                    f"{binding.mode}, but current dispatch mode is unavailable"
                )
            if current.mode != binding.mode:
                raise EdgeNotAuthorized(
                    f"edge authorization mode mismatch for decision_ref={decision_ref!r}: "
                    f"authorized for {binding.mode}, current dispatch is {current.mode}"
                )
        if binding.config_hash is not None:
            if current.config_hash is None:
                raise EdgeNotAuthorized(
                    f"edge authorization for decision_ref={decision_ref!r} is bound to an "
                    "effective config snapshot, but current config is unavailable"
                )
            if current.config_hash != binding.config_hash:
                raise EdgeNotAuthorized(
                    f"edge authorization config snapshot changed for decision_ref={decision_ref!r}; "
                    "re-test required before dispatch"
                )
        if binding.broker_account_ref is not None:
            if current.broker_account_ref is None:
                raise EdgeNotAuthorized(
                    f"edge authorization for decision_ref={decision_ref!r} is bound to a broker "
                    "account, but current account identity is unavailable"
                )
            if current.broker_account_ref != binding.broker_account_ref:
                raise EdgeNotAuthorized(
                    f"edge authorization broker account mismatch for decision_ref={decision_ref!r}; "
                    "re-test required before dispatch"
                )
        if binding.max_volume is not None:
            if current.max_volume is None:
                raise EdgeNotAuthorized(
                    f"edge authorization for decision_ref={decision_ref!r} is bound to a maximum "
                    "volume, but current order size is unavailable"
                )
            if current.max_volume > binding.max_volume and not _close(current.max_volume, binding.max_volume):
                raise EdgeNotAuthorized(
                    f"edge authorization volume exceeded for decision_ref={decision_ref!r}: "
                    f"{current.max_volume:g} lots requested, {binding.max_volume:g} authorized"
                )


def consume(
    order: Any,
    *,
    is_real: bool,
    now_iso: Optional[str] = None,
    config: Any = None,
    bridge: Any = None,
    volume: Any = None,
    order_type: Any = None,
    price: Any = None,
    strategy_id: Any = None,
    proposed_intent: Any = None,
) -> None:
    """One-shot version of :func:`require`.

    This verifies the same fresh, matching PASS and then spends it. Call this at
    the final dispatch chokepoint, immediately before touching the broker bridge.
    A fresh PASS for the same ``decision_ref`` can re-authorize later, but a raw
    replay of the old order cannot reuse the spent token.
    """
    require(
        order,
        is_real=is_real,
        now_iso=now_iso,
        config=config,
        bridge=bridge,
        volume=volume,
        order_type=order_type,
        price=price,
        strategy_id=strategy_id,
        proposed_intent=proposed_intent,
    )
    decision_ref = getattr(order, "decision_ref", None)
    if decision_ref:
        record = _REGISTRY.pop(str(decision_ref), None)
        if record is not None:
            _CONSUMED[str(decision_ref)] = record.evaluated_at
