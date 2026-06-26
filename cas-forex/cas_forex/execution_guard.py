"""Mandatory pre-dispatch execution guard for CAS FOREX.

This module finally WIRES IN the previously-unused ``pre_execution_risk_gate``
(audit finding #1: the gate existed but nothing called it). Every path that
would dispatch an order to a broker bridge should go through
``guarded_place_order`` -- or call ``guard`` directly first. The guard:

  1. builds a portfolio risk snapshot from optional live telemetry / account
     snapshot (``risk_monitoring.compose_portfolio_risk_snapshot``),
  2. derives risk caps from the app config (``caps_from_config``),
  3. evaluates the *proposed* intent against those caps
     (``pre_execution_risk_gate.evaluate_proposed_intent``), and
  4. for a real-money (live_mode) dispatch, re-asserts the owner live-trading
     authorization (``runtime_gates.require_authorized``) right at the dispatch
     chokepoint -- defense-in-depth for audit finding #2, so the live gate is
     enforced even if a bridge was constructed outside ``broker.get_bridge``.

It is purely a SAFETY layer. It can only ever BLOCK an order; it never creates,
sizes, routes, or places a trade on its own, and it enables no real-money
capability. The risk caps apply in paper mode too, so the same limits protect
demo dispatch.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from cas_forex import risk_monitoring
from cas_forex.pre_execution_risk_gate import (
    RiskCapConfig,
    RiskGateDecision,
    evaluate_proposed_intent,
)


class ExecutionBlocked(Exception):
    """Raised when the pre-execution risk gate rejects a proposed intent.

    The full ``RiskGateDecision`` (which cap fired, the would-be metric, the
    plain-English reason) is attached as ``.decision`` for logging / UI.
    """

    def __init__(self, decision: RiskGateDecision) -> None:
        self.decision = decision
        super().__init__(decision.plain_english_reason)


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def caps_from_config(config: Any = None) -> RiskCapConfig:
    """Map the app ForexConfig onto the gate's ``RiskCapConfig``.

    Only the dimensions the app config actually defines are capped; everything
    else stays ``None`` (no cap) rather than inventing limits the operator
    never set. Mapping:

      - max_total_exposure_lots          <- config.max_total_exposure_lots
      - max_open_position_count          <- config.max_open_positions
      - max_positions_per_symbol         <- config.max_open_positions
        (a single symbol can never need more than the whole-book position cap)
      - max_drawdown_pct_from_equity_peak <- config.max_weekly_drawdown_pct
    """
    config = _resolve_config(config)

    def _f(attr: str) -> Optional[float]:
        value = getattr(config, attr, None)
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    def _i(attr: str) -> Optional[int]:
        value = getattr(config, attr, None)
        try:
            return None if value is None else int(value)
        except (TypeError, ValueError):
            return None

    open_cap = _i("max_open_positions")
    return RiskCapConfig(
        max_total_exposure_lots=_f("max_total_exposure_lots"),
        max_concentration_pct=None,
        max_margin_utilization_pct=None,
        max_positions_per_symbol=open_cap,
        max_open_position_count=open_cap,
        max_drawdown_pct_from_equity_peak=_f("max_weekly_drawdown_pct"),
        max_floating_loss_usd=None,
    )


def build_snapshot_payload(
    *,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Compose the portfolio snapshot payload the gate consumes. Safe with
    all-``None`` inputs (collapses to an empty, zero-exposure portfolio)."""
    snapshot = risk_monitoring.compose_portfolio_risk_snapshot(
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
    )
    return risk_monitoring.snapshot_to_payload(snapshot)


def evaluate(
    proposed_intent: Mapping[str, Any],
    *,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    config: Any = None,
    caps: Optional[RiskCapConfig] = None,
    equity_peak: Optional[float] = None,
) -> RiskGateDecision:
    """Run the pre-execution risk gate for ``proposed_intent``. Never raises;
    returns a ``RiskGateDecision`` (``.accepted`` True/False)."""
    if caps is None:
        caps = caps_from_config(config)
    payload = build_snapshot_payload(
        live_telemetry=live_telemetry, account_snapshot=account_snapshot
    )
    return evaluate_proposed_intent(
        proposed_intent=proposed_intent,
        portfolio_snapshot=payload,
        caps=caps,
        equity_peak=equity_peak,
    )


def guard(proposed_intent: Mapping[str, Any], **kwargs: Any) -> RiskGateDecision:
    """Evaluate the gate and RAISE ``ExecutionBlocked`` unless it accepts.

    Accepts the same keyword arguments as :func:`evaluate`.
    """
    decision = evaluate(proposed_intent, **kwargs)
    if not decision.accepted:
        raise ExecutionBlocked(decision)
    return decision


def _is_live_execution(config: Any = None) -> bool:
    """A dispatch is real-money when the app is in live mode. This mirrors the
    condition ``broker._enforce_live_legal_gates`` uses, so the recheck fires
    on exactly the dispatches that touch real money (and never on paper)."""
    return bool(getattr(_resolve_config(config), "live_mode", False))


def _bridge_executes_real(bridge: Any) -> bool:
    """Whether the bridge itself would place a real order on this dispatch.

    ``config.live_mode`` is NOT sufficient: a connected real MT5 terminal fills
    orders based on connection state, not the live_mode flag, so an operator who
    left LIVE_MODE off but pointed the bridge at a connected live account would
    otherwise bypass the owner gate. We ask the bridge directly via
    ``will_execute_real_order``. If the probe raises, fail closed (assume real).
    """
    probe = getattr(bridge, "will_execute_real_order", None)
    if not callable(probe):
        return False
    try:
        return bool(probe())
    except Exception:  # pragma: no cover - defensive; fail closed
        return True


def _intent_from_order(order: Any) -> dict[str, Any]:
    """Best-effort extraction of symbol/direction/lots from a bridge order
    object (e.g. an MT5 order model). ``direction`` may be an enum with a
    ``.value`` or a plain string; ``lots`` may be ``volume`` or ``lots``."""
    direction = getattr(order, "direction", None)
    direction = getattr(direction, "value", direction)
    lots = getattr(order, "volume", None)
    if lots is None:
        lots = getattr(order, "lots", None)
    return {
        "symbol": getattr(order, "symbol", None),
        "direction": direction,
        "lots": lots,
    }


def guarded_place_order(
    bridge: Any,
    order: Any,
    *,
    proposed_intent: Optional[Mapping[str, Any]] = None,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
) -> Any:
    """The sanctioned way to dispatch an order to a broker bridge.

    Order of checks (fail-closed -- the bridge is only touched if all pass):

      1. If this dispatch would touch a real broker -- either the app is in live
         mode OR the bridge reports it will place a real order
         (``will_execute_real_order``) -- re-assert the owner live-trading gate
         via ``runtime_gates.require_authorized`` -- raises ``PermissionError``
         listing what is still missing.
      2. Run the pre-execution risk gate over the proposed intent -- raises
         ``ExecutionBlocked`` on any cap breach.
      3. Only then call ``bridge.execute_order(order)`` (real bridges) -- falling
         back to ``bridge.place_order`` for test fakes -- and return its result.

    ``proposed_intent`` overrides the symbol/direction/lots inferred from
    ``order`` if supplied.
    """
    intent = dict(proposed_intent) if proposed_intent else _intent_from_order(order)

    if _is_live_execution(config) or _bridge_executes_real(bridge):
        # Defense-in-depth: enforce the live-trading authorization at the
        # dispatch chokepoint, not only at bridge construction. This fires when
        # the app is in live mode OR when the bridge itself would place a real
        # order (e.g. a connected MT5 terminal) even with live_mode off.
        from cas_forex import runtime_gates

        runtime_gates.require_authorized("live_trading", config)

    guard(
        intent,
        config=config,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        equity_peak=equity_peak,
    )
    # The real broker bridges (MT5Bridge / SimulatedBrokerBridge / MT4EABridge)
    # expose ``execute_order``; only test fakes define ``place_order``. Prefer
    # the real method and fall back so both work through this one chokepoint.
    dispatch = getattr(bridge, "execute_order", None) or getattr(bridge, "place_order", None)
    if not callable(dispatch):
        raise TypeError(
            "broker bridge exposes neither execute_order nor place_order; "
            "cannot dispatch order"
        )
    return dispatch(order)
