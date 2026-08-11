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

from datetime import datetime
import os
from typing import Any, Mapping, Optional

from cas_forex import risk_monitoring
from cas_forex.pre_execution_risk_gate import (
    RiskCapConfig,
    RiskGateDecision,
    evaluate_proposed_intent,
)
from cas_forex.time_utils import utc_now


class ExecutionBlocked(Exception):
    """Raised when the pre-execution risk gate rejects a proposed intent.

    The full ``RiskGateDecision`` (which cap fired, the would-be metric, the
    plain-English reason) is attached as ``.decision`` for logging / UI.
    """

    def __init__(self, decision: RiskGateDecision) -> None:
        self.decision = decision
        super().__init__(decision.plain_english_reason)


class LiveDispatchBlocked(PermissionError):
    """Raised when a real dispatch fails a specific live-readiness sub-gate."""

    def __init__(self, *, stage: str, detail: str, report: Mapping[str, Any]) -> None:
        self.stage = str(stage or "live_gate")
        self.detail = str(detail or "")
        self.report = dict(report or {})
        super().__init__(self.detail or f"Live dispatch blocked at {self.stage}")


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        base = config
    else:
        from cas_forex.config import config as default_config

        base = default_config
    try:
        from cas_forex.live_enable_control import apply_live_enable_overrides

        return apply_live_enable_overrides(base)
    except Exception:  # pragma: no cover - guard remains conservative below
        return base


def _ai_dial(name: str) -> Optional[float]:
    """Read one AI-operator risk dial from the control authority. Best-effort:
    any failure (no authority, unknown lever) returns None so callers fall back
    to the owner/static value."""
    try:
        from cas_forex.ai_control_authority import get_authority

        value = get_authority().control.get(name)
        return None if value is None else float(value)
    except Exception:
        return None


def _config_float(config: Any, *names: str) -> Optional[float]:
    for name in names:
        try:
            value = getattr(config, name)
        except Exception:
            continue
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def caps_from_config(
    config: Any = None,
    *,
    owner_overrides: Optional[Mapping[str, Any]] = None,
) -> RiskCapConfig:
    """Map the effective risk caps onto the gate's ``RiskCapConfig``.

    Precedence per dimension (owner directive 2026-07-03 — the risk cap is in
    the AI's hands, the owner keeps the override):

      1. EXPLICIT owner runtime override (``risk_control``, may be None =
         unlimited) — the owner drives; always wins when set.
      2. The AI operator's dial (``max_concurrent_trades``,
         ``max_positions_per_symbol``, ``max_total_exposure_lots`` on the
         owner-fenced control surface) — so what the operator sets is what the
         chokepoint ENFORCES.
      3. Static config — the pre-dial fallback.

      - max_total_exposure_lots          <- override | AI dial | config
      - max_open_position_count          <- override | AI dial | config
      - max_positions_per_symbol         <- AI dial (capped by open-count cap),
                                            else the open-count cap
      - max_compound_units               <- owner-fenced AI dial; reserved
                                            slots apply only after exact scale-in
                                            authorization is verified
      - max_margin_utilization_pct       <- config.max_margin_utilization_pct
                                            or compatible config alias
      - max_risk_per_trade_pct           <- owner-fenced AI
                                            max_risk_pct_per_trade dial, then
                                            config.max_risk_per_trade_pct
      - max_drawdown_pct_from_equity_peak <- risk_control.max_drawdown_pct
      - max_floating_loss_usd            <- risk_control.max_loss_cap_usd
    """
    config = _resolve_config(config)
    from cas_forex.risk_control import (
        explicit_override_keys,
        resolve_risk_control,
        resolve_risk_control_snapshot,
    )

    if owner_overrides is None:
        rc = resolve_risk_control(config)
        owner_set = explicit_override_keys()
    else:
        rc = resolve_risk_control_snapshot(config, owner_overrides)
        owner_set = frozenset(owner_overrides)

    max_open = rc.max_concurrent_trades
    if "max_concurrent_trades" not in owner_set:
        dial = _ai_dial("max_concurrent_trades")
        if dial is not None:
            max_open = int(dial)

    per_symbol: Optional[int] = max_open
    dial = _ai_dial("max_positions_per_symbol")
    if dial is not None:
        per_symbol = int(dial) if max_open is None else min(int(dial), int(max_open))

    total_lots = rc.max_total_exposure_lots
    if "max_total_exposure_lots" not in owner_set:
        dial = _ai_dial("max_total_exposure_lots")
        if dial is not None:
            total_lots = float(dial)

    max_margin_utilization = _config_float(
        config,
        "max_margin_utilization_pct",
        "broker_max_margin_utilization_pct",
        "max_margin_use_pct",
        "max_margin_used_pct",
    )
    max_risk_per_trade = _ai_dial("max_risk_pct_per_trade")
    if max_risk_per_trade is None:
        max_risk_per_trade = _config_float(
            config,
            "max_risk_per_trade_pct",
            "risk_per_trade_pct",
        )
    max_compound_units = _ai_dial("max_compound_units")
    try:
        max_compound_units = max(0, int(max_compound_units or 0))
    except (TypeError, ValueError):
        max_compound_units = 0

    return RiskCapConfig(
        max_total_exposure_lots=total_lots,
        max_concentration_pct=None,
        max_margin_utilization_pct=max_margin_utilization,
        max_positions_per_symbol=per_symbol,
        max_open_position_count=max_open,
        max_drawdown_pct_from_equity_peak=rc.max_drawdown_pct,
        max_floating_loss_usd=rc.max_loss_cap_usd,
        max_risk_per_trade_pct=max_risk_per_trade,
        max_compound_units=max_compound_units,
    )


def build_snapshot_payload(
    *,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    config: Any = None,
) -> dict[str, Any]:
    """Compose the portfolio snapshot payload the gate consumes. Safe with
    all-``None`` inputs (collapses to an empty, zero-exposure portfolio).

    Self-hydration (2026-07-03): when the caller supplies NO telemetry, count
    the simulator's still-open PAPER attempts as the portfolio. Without this,
    the open-position caps compared every dispatch against an EMPTY portfolio
    and never fired — which is how 150+ paper positions piled up unchecked.
    Skipped under pytest (tests inject their own telemetry) and best-effort in
    production: any failure falls back to the empty portfolio as before."""
    paper_runtime = config is None or not bool(getattr(config, "live_mode", False))
    if paper_runtime and not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            from cas_forex.paper_outcome_sim import open_paper_positions

            rows = open_paper_positions()
            if rows:
                prepared = dict(live_telemetry or {})
                explicit = _explicit_position_rows(live_telemetry)
                durable = [
                    _tag_position_risk_source(row, "SimulatedBrokerBridge")
                    for row in rows
                    if isinstance(row, Mapping)
                ]
                merged = _merge_position_rows(explicit, durable)
                prepared["open_positions"] = merged
                prepared["paper_position_hydration"] = {
                    "status": "DURABLE_SIMULATOR_POSITIONS_MERGED",
                    "durable_simulator_position_count": len(durable),
                    "combined_open_position_count": len(merged),
                    "source": "paper_outcome_sim.open_paper_positions",
                }
                live_telemetry = prepared
        except Exception:
            pass
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
    compound_slot_authorized: bool = False,
) -> RiskGateDecision:
    """Run the pre-execution risk gate for ``proposed_intent``. Never raises;
    returns a ``RiskGateDecision`` (``.accepted`` True/False)."""
    if caps is None:
        caps = caps_from_config(config)
    payload = build_snapshot_payload(
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        config=config,
    )
    return evaluate_proposed_intent(
        proposed_intent=proposed_intent,
        portfolio_snapshot=payload,
        caps=caps,
        equity_peak=equity_peak,
        compound_slot_authorized=compound_slot_authorized,
    )


def guard(proposed_intent: Mapping[str, Any], **kwargs: Any) -> RiskGateDecision:
    """Evaluate the gate and RAISE ``ExecutionBlocked`` unless it accepts.

    Accepts the same keyword arguments as :func:`evaluate`.
    """
    decision = evaluate(proposed_intent, **kwargs)
    if not decision.accepted:
        raise ExecutionBlocked(decision)
    return decision


def require_daily_realized_loss_ready(
    *,
    bridge: Any,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Block new exposure after the owner-fenced daily realized-loss cap.

    This runs independently of the model and the ordinary portfolio gate. An
    active cap also fails closed when reconciled broker daily P&L is unavailable.
    Existing-position management uses a separate path and remains available.
    """

    from cas_forex.daily_loss_guard import evaluate_bridge_daily_realized_loss

    report = evaluate_bridge_daily_realized_loss(
        bridge,
        config=config,
        positions=_explicit_position_rows(live_telemetry),
        account_snapshot=account_snapshot,
    )
    if not bool(report.get("block_new_exposure")):
        return report

    cap = report.get("cap_usd")
    realized = report.get("realized_today_usd")
    decision = RiskGateDecision(
        accepted=False,
        decision="REJECT",
        blocking_caps=("daily_loss_cap_usd",),
        proposed_intent_summary="NEW EXPOSURE",
        plain_english_reason=str(
            report.get("detail")
            or "New exposure blocked by the configured daily realized-loss cap."
        ),
        evaluated_at_iso=utc_now().isoformat(),
        cap_snapshot={"daily_loss_cap_usd": cap},
        portfolio_snapshot_summary={
            "daily_realized_loss_gate": report,
            "realized_today_usd": realized,
        },
    )
    raise ExecutionBlocked(decision)


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


def _fresh_broker_truth_ready_for_live() -> bool:
    from cas_forex.broker_truth_monitor import broker_truth_monitor_ready_for_live

    return bool(broker_truth_monitor_ready_for_live())


def _require_fresh_broker_truth_for_real_dispatch() -> None:
    """Require fresh broker-truth reconciliation at the order chokepoint.

    ``runtime_gates.require_authorized("live_trading")`` already includes this
    readiness signal, but this direct check keeps the invariant local to the
    dispatch path: if a future caller stubs or bypasses the broader runtime
    gate in tests or glue code, a real broker bridge still cannot be touched
    without current broker truth.
    """
    try:
        ready = _fresh_broker_truth_ready_for_live()
    except Exception as exc:
        raise PermissionError(
            "fresh broker truth required before real dispatch; broker truth "
            "monitor status is unreadable"
        ) from exc
    if not ready:
        raise PermissionError(
            "fresh broker truth required before real dispatch; latest broker "
            "truth monitor report is missing, stale, unreconciled, demo-only, "
            "or blocked. Run broker truth monitoring/checks and resolve any "
            "mismatch before retrying."
        )


def require_trade_management_action_ready(
    action: Mapping[str, Any],
    *,
    config: Any = None,
    bridge: Any = None,
) -> dict[str, Any]:
    """Review a risk-reducing open-position management action before broker call.

    Management actions such as moving a stop toward breakeven or closing part of
    an existing position do not create new market exposure, so they do not need
    an edge PASS. A real broker bridge still needs the live-trading runtime gate
    and fresh broker truth at action time before any broker method can be called.
    """

    method = str(action.get("broker_method") or "")
    if method not in {"modify_position", "close_position"}:
        raise PermissionError(
            "unsupported trade-management broker method; expected modify_position or close_position"
        )
    ticket = action.get("broker_ticket")
    try:
        ticket_number = int(str(ticket))
    except (TypeError, ValueError):
        ticket_number = 0
    if ticket_number <= 0:
        raise PermissionError("trade-management action requires a broker ticket")
    risk_effect = str(action.get("risk_effect") or "")
    checks = _validate_trade_management_risk_reduction(action, method=method)
    is_real = _is_live_execution(config) or (bridge is not None and _bridge_executes_real(bridge))
    if is_real:
        from cas_forex import runtime_gates

        runtime_gates.require_authorized("live_trading", config)
        _require_fresh_broker_truth_for_real_dispatch()
    return {
        "report_kind": "cas_forex_trade_management_execution_guard",
        "status": "ACCEPT",
        "broker_method": method,
        "broker_ticket": ticket_number,
        "risk_effect": risk_effect,
        "risk_reduction_checks": checks,
        "is_real_broker_action": bool(is_real),
        "edge_pass_required": False,
        "fresh_broker_truth_required": bool(is_real),
        "live_trading_gate_required": bool(is_real),
        "claim_boundary": (
            "Trade-management guard review covers risk-reducing actions on "
            "existing positions. It does not create edge authorization, open "
            "new exposure, move money, or bypass broker bridge permissions."
        ),
    }


def _validate_trade_management_risk_reduction(
    action: Mapping[str, Any],
    *,
    method: str,
) -> list[dict[str, Any]]:
    """Prove a management payload reduces exposure before a broker call."""

    risk_effect = str(action.get("risk_effect") or "")
    if method == "modify_position":
        if risk_effect not in {
            "emergency_protective_stop",
            "principal_lock",
            "risk_reducing_trail",
            "bounded_profit_target",
            "profit_extension_after_principal_lock",
        }:
            raise PermissionError(
                "modify-position management requires an explicit protective-stop or take-profit policy effect"
            )
        side = str(action.get("side") or "").upper()
        current = _management_positive_float(action.get("current_price"), "current_price")
        new_stop = _management_positive_float(action.get("stop_loss"), "stop_loss")
        if side not in {"LONG", "BUY", "SHORT", "SELL"}:
            raise PermissionError("trade-management action requires LONG/BUY or SHORT/SELL side")
        previous_stop = _management_optional_float(action.get("previous_stop_loss"))
        previous_tp = _management_optional_float(action.get("previous_take_profit"))
        requested_tp = _management_optional_float(action.get("take_profit"))
        tolerance = max(
            abs(current),
            abs(previous_stop or 0.0),
            abs(new_stop),
            abs(previous_tp or 0.0),
            abs(requested_tp or 0.0),
            1.0,
        ) * 1e-10

        if risk_effect == "emergency_protective_stop":
            if previous_stop is not None and previous_stop > 0:
                raise PermissionError(
                    "emergency protective-stop policy is only valid when no positive broker stop exists"
                )
            if side in {"LONG", "BUY"} and new_stop >= current - tolerance:
                raise PermissionError("LONG emergency stop must remain below current exit price")
            if side in {"SHORT", "SELL"} and new_stop <= current + tolerance:
                raise PermissionError("SHORT emergency stop must remain above current exit price")
            if previous_tp is not None and previous_tp > 0:
                if requested_tp is None or abs(previous_tp - requested_tp) > tolerance:
                    raise PermissionError(
                        "emergency stop action cannot silently change or remove take profit"
                    )
            return [
                {"check": "risk_effect", "status": "PASSED", "value": risk_effect},
                {
                    "check": "missing_stop_bounded_without_crossing_market",
                    "status": "PASSED",
                    "side": side,
                    "new_stop_loss": new_stop,
                    "current_price": current,
                },
                {"check": "take_profit_unchanged", "status": "PASSED"},
            ]

        if risk_effect in {
            "bounded_profit_target",
            "profit_extension_after_principal_lock",
        }:
            entry = _management_positive_float(action.get("open_price"), "open_price")
            if previous_stop is None or previous_stop <= 0:
                raise PermissionError("take-profit management requires an existing positive stop")
            if abs(previous_stop - new_stop) > tolerance:
                raise PermissionError("take-profit management cannot silently change the stop")
            new_tp = _management_positive_float(requested_tp, "take_profit")
            if side in {"LONG", "BUY"}:
                if new_tp <= current + tolerance or new_tp <= entry + tolerance:
                    raise PermissionError(
                        "LONG take profit must remain above current exit price and entry"
                    )
            else:
                if new_tp >= current - tolerance or new_tp >= entry - tolerance:
                    raise PermissionError(
                        "SHORT take profit must remain below current exit price and entry"
                    )
            if risk_effect == "bounded_profit_target":
                if previous_tp is not None and previous_tp > 0:
                    raise PermissionError(
                        "bounded-profit-target policy is only valid when no positive take profit exists"
                    )
            else:
                if previous_tp is None or previous_tp <= 0:
                    raise PermissionError(
                        "take-profit extension requires an existing positive target"
                    )
                if side in {"LONG", "BUY"}:
                    improves_reward = new_tp > previous_tp + tolerance
                    principal_protected = previous_stop >= entry - tolerance
                else:
                    improves_reward = new_tp < previous_tp - tolerance
                    principal_protected = previous_stop <= entry + tolerance
                if not improves_reward:
                    raise PermissionError("take-profit extension must improve reward geometry")
                if not principal_protected:
                    raise PermissionError(
                        "take-profit extension requires a stop at or beyond breakeven"
                    )
            return [
                {"check": "risk_effect", "status": "PASSED", "value": risk_effect},
                {"check": "stop_unchanged", "status": "PASSED", "stop_loss": new_stop},
                {
                    "check": "take_profit_geometry",
                    "status": "PASSED",
                    "side": side,
                    "previous_take_profit": previous_tp,
                    "new_take_profit": new_tp,
                    "current_price": current,
                },
            ]

        previous_stop = _management_positive_float(previous_stop, "previous_stop_loss")
        tolerance = max(abs(current), abs(previous_stop), abs(new_stop), 1.0) * 1e-10
        if side in {"LONG", "BUY"}:
            if new_stop <= previous_stop + tolerance:
                raise PermissionError("LONG management stop must tighten above the previous stop")
            if new_stop >= current - tolerance:
                raise PermissionError("LONG management stop must remain below current exit price")
        elif side in {"SHORT", "SELL"}:
            if new_stop >= previous_stop - tolerance:
                raise PermissionError("SHORT management stop must tighten below the previous stop")
            if new_stop <= current + tolerance:
                raise PermissionError("SHORT management stop must remain above current exit price")
        if previous_tp is not None and requested_tp is not None:
            tp_tolerance = max(abs(previous_tp), abs(requested_tp), 1.0) * 1e-10
            if abs(previous_tp - requested_tp) > tp_tolerance:
                raise PermissionError(
                    "stop-management action cannot silently change take profit; use an explicit take-profit policy path"
                )
        return [
            {"check": "risk_effect", "status": "PASSED", "value": risk_effect},
            {
                "check": "stop_tightens_without_crossing_market",
                "status": "PASSED",
                "side": side,
                "previous_stop_loss": previous_stop,
                "new_stop_loss": new_stop,
                "current_price": current,
            },
            {"check": "take_profit_unchanged", "status": "PASSED"},
        ]

    if risk_effect not in {
        "exposure_reducing_partial_close",
        "exposure_reducing_close",
        "exposure_reducing_full_close",
    }:
        raise PermissionError("close-position management requires exposure-reducing evidence")
    original = _management_positive_float(action.get("original_volume"), "original_volume")
    volume = _management_optional_float(action.get("volume"))
    if volume is None:
        if risk_effect != "exposure_reducing_full_close":
            raise PermissionError("partial close requires a positive close volume")
    elif volume <= 0 or volume > original + 1e-9:
        raise PermissionError("close volume must be positive and no greater than the open volume")
    return [
        {"check": "risk_effect", "status": "PASSED", "value": risk_effect},
        {
            "check": "close_volume_reduces_exposure",
            "status": "PASSED",
            "original_volume": original,
            "close_volume": volume,
        },
    ]


def _management_positive_float(value: Any, label: str) -> float:
    parsed = _management_optional_float(value)
    if parsed is None or parsed <= 0:
        raise PermissionError(f"trade-management action requires positive {label}")
    return parsed


def _management_optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PermissionError("trade-management numeric evidence is invalid") from exc


_LIVE_RUNTIME_STAGE_MAP = {
    "auto-halt circuit breaker is CLEAR": "auto_halt",
    "continuous broker-truth monitor is fresh and live-connected": "broker_truth",
    "live crash/disconnect recovery review is CLEAR": "live_recovery",
    "owner ACCEPTED latest passing live-order dry run against fresh broker truth": "live_order_dry_run_review",
    "small-controlled live pilot is ACCEPT and has remaining capacity": "live_pilot",
}

_LIVE_STAGE_ORDER = (
    "live_gate",
    "auto_halt",
    "broker_truth",
    "mt5_terminal_permissions",
    "live_recovery",
    "live_order_dry_run_review",
    "live_risk_snapshot",
    "live_pilot",
)

_LIVE_STAGE_LABELS = {
    "live_gate": "Live gate",
    "auto_halt": "Auto-halt",
    "broker_truth": "Broker truth",
    "mt5_terminal_permissions": "MT5 terminal permissions",
    "live_recovery": "Live recovery",
    "live_order_dry_run_review": "Live dry run review",
    "live_risk_snapshot": "Live risk snapshot",
    "live_pilot": "Live pilot",
}


def _latest_broker_truth_snapshot() -> Mapping[str, Any]:
    try:
        from cas_forex.broker_truth_monitor import load_latest_broker_truth_monitor_report

        report = load_latest_broker_truth_monitor_report()
        return report if isinstance(report, Mapping) else {}
    except Exception:
        return {}


def _action_time_broker_truth_snapshot() -> Mapping[str, Any]:
    """Refresh broker truth at dispatch time; fall back to the latest saved
    report only when the refresh itself is unreadable."""
    latest = dict(_latest_broker_truth_snapshot() or {})
    try:
        from cas_forex.broker_truth_monitor import run_broker_truth_check

        report = run_broker_truth_check(write_state=True, write_report=True)
        if isinstance(report, Mapping):
            payload = dict(report)
            payload["action_time_refresh_performed"] = True
            payload["action_time_refresh_error"] = None
            return payload
    except Exception as exc:
        latest["action_time_refresh_performed"] = True
        latest["action_time_refresh_error"] = f"{type(exc).__name__}: {exc}"
        return latest
    latest["action_time_refresh_performed"] = True
    latest["action_time_refresh_error"] = "action-time broker truth refresh returned no usable report"
    return latest


def _latest_mt5_permission_snapshot() -> Mapping[str, Any]:
    try:
        from cas_forex.mt5_live import get_mt5_permission_snapshot

        report = get_mt5_permission_snapshot(force=True)
        return report if isinstance(report, Mapping) else {}
    except Exception:
        return {}


def _latest_mt5_live_risk_snapshot() -> Mapping[str, Any]:
    try:
        from cas_forex.mt5_live import get_mt5_account_snapshot

        report = get_mt5_account_snapshot(force=True)
        return report if isinstance(report, Mapping) else {}
    except Exception:
        return {}


def _live_recovery_snapshot() -> Mapping[str, Any]:
    try:
        from cas_forex.live_recovery import build_live_recovery_report

        report = build_live_recovery_report()
        return report if isinstance(report, Mapping) else {}
    except Exception:
        return {}


def _live_order_dry_run_review_snapshot() -> Mapping[str, Any]:
    try:
        from cas_forex.live_order_dry_run_review import build_live_order_dry_run_review

        report = build_live_order_dry_run_review()
        return report if isinstance(report, Mapping) else {}
    except Exception:
        return {}


def _live_pilot_snapshot() -> Mapping[str, Any]:
    try:
        from cas_forex.live_pilot import build_live_pilot_policy

        report = build_live_pilot_policy()
        return report if isinstance(report, Mapping) else {}
    except Exception:
        return {}


def _compact_broker_truth_snapshot(report: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(report or {})
    return {
        "generated_at": data.get("generated_at"),
        "monitor_status": data.get("monitor_status"),
        "overall_status": data.get("overall_status"),
        "mt5_connected": data.get("mt5_connected"),
        "mt5_is_demo": data.get("mt5_is_demo"),
        "mt5_account": data.get("mt5_account"),
        "mt5_account_server": data.get("mt5_account_server"),
        "mt5_expected_account": data.get("mt5_expected_account"),
        "mt5_expected_server": data.get("mt5_expected_server"),
        "mt5_account_identity_matches_config": data.get("mt5_account_identity_matches_config"),
        "mt5_open_position_count": data.get("mt5_open_position_count"),
        "terminal_unmatched_open_position_count": data.get("terminal_unmatched_open_position_count"),
        "terminal_unattributed_open_position_count": data.get("terminal_unattributed_open_position_count"),
        "terminal_memory_gap_open_position_count": data.get("terminal_memory_gap_open_position_count"),
        "cas_memory_only_open_position_count": data.get("cas_memory_only_open_position_count"),
        "cas_receipt_pending_open_position_count": data.get("cas_receipt_pending_open_position_count"),
        "terminal_unmatched_history_count": data.get("terminal_unmatched_history_count"),
        "terminal_unattributed_history_count": data.get("terminal_unattributed_history_count"),
        "terminal_attributed_history_memory_gap_count": data.get("terminal_attributed_history_memory_gap_count"),
        "terminal_pending_receipt_count": data.get("terminal_pending_receipt_count"),
        "terminal_receipt_mismatch_count": data.get("terminal_receipt_mismatch_count"),
        "terminal_unmatched_open_position_preview": list(data.get("terminal_unmatched_open_position_preview") or [])[:3],
        "terminal_unmatched_history_preview": list(data.get("terminal_unmatched_history_preview") or [])[:3],
        "fresh_for_live_seconds": data.get("fresh_for_live_seconds"),
        "action_time_refresh_performed": data.get("action_time_refresh_performed"),
        "action_time_refresh_error": data.get("action_time_refresh_error"),
        "next_action": data.get("next_action"),
    }


def _compact_mt5_permission_snapshot(report: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(report or {})
    account = data.get("account") if isinstance(data.get("account"), Mapping) else {}
    permission_state = data.get("permission_state") if isinstance(data.get("permission_state"), Mapping) else {}
    return {
        "connected": data.get("connected"),
        "cached": data.get("cached"),
        "is_demo": data.get("is_demo"),
        "account": {
            "login": account.get("login"),
            "server": account.get("server"),
            "currency": account.get("currency"),
        },
        "permission_state": {
            "status": permission_state.get("status"),
            "permission_label": permission_state.get("permission_label"),
            "can_submit_order_send": permission_state.get("can_submit_order_send"),
            "blockers": list(permission_state.get("blockers") or []),
            "plain_english": permission_state.get("plain_english"),
        },
        "detail": data.get("detail"),
        "error": data.get("error"),
    }


def _compact_live_recovery_snapshot(report: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(report or {})
    return {
        "generated_at": data.get("generated_at"),
        "recovery_status": data.get("recovery_status"),
        "owner_recovery_status": data.get("owner_recovery_status"),
        "recovery_clear_for_live": data.get("recovery_clear_for_live"),
        "requires_recovery_review": data.get("requires_recovery_review"),
        "evidence_ready_for_owner_accept": data.get("evidence_ready_for_owner_accept"),
        "current_fingerprint": data.get("current_fingerprint"),
        "missing_requirements": list(data.get("missing_requirements") or []),
        "next_action": data.get("next_action"),
    }


def _compact_live_order_dry_run_review_snapshot(report: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(report or {})
    latest = data.get("latest_dry_run_summary") if isinstance(data.get("latest_dry_run_summary"), Mapping) else {}
    return {
        "generated_at": data.get("generated_at"),
        "review_status": data.get("review_status"),
        "owner_review_status": data.get("owner_review_status"),
        "dry_run_review_clear_for_live": data.get("dry_run_review_clear_for_live"),
        "evidence_ready_for_owner_accept": data.get("evidence_ready_for_owner_accept"),
        "missing_requirements": list(data.get("missing_requirements") or []),
        "latest_dry_run_summary": {
            "present": latest.get("present"),
            "status": latest.get("status"),
            "order_id": latest.get("order_id"),
            "decision_ref": latest.get("decision_ref"),
            "generated_at": latest.get("generated_at"),
            "broker_touched": latest.get("broker_touched"),
            "would_reach_broker_if_executed": latest.get("would_reach_broker_if_executed"),
        },
        "next_action": data.get("next_action"),
    }


def _compact_live_pilot_snapshot(report: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(report or {})
    return {
        "owner_pilot_status": data.get("owner_pilot_status"),
        "ready_for_next_live_order": data.get("ready_for_next_live_order"),
        "pilot_capacity_remaining": data.get("pilot_capacity_remaining"),
        "live_trade_count": data.get("live_trade_count"),
        "allowed_symbols": list(data.get("allowed_symbols") or []),
        "sizing_mode": data.get("sizing_mode"),
        "continuous_authority": data.get("continuous_authority"),
        "max_trade_risk_pct_equity": data.get("max_trade_risk_pct_equity"),
        "max_trade_lots": data.get("max_trade_lots"),
        "max_open_live_lots": data.get("max_open_live_lots"),
        "missing_requirements": list(data.get("missing_requirements") or []),
        "next_action": data.get("next_action"),
    }


def _live_stage_record(
    stage: str,
    *,
    blocked: bool,
    detail: str,
    missing_requirements: list[str] | None = None,
    evidence: Mapping[str, Any] | None = None,
    evidence_snapshot: Mapping[str, Any] | None = None,
    next_action: str = "",
) -> dict[str, Any]:
    return {
        "stage": str(stage),
        "label": _LIVE_STAGE_LABELS.get(str(stage), str(stage)),
        "status": "BLOCKED" if blocked else "PASSED",
        "detail": str(detail or ""),
        "missing_requirements": list(missing_requirements or []),
        "evidence": dict(evidence or {}),
        "evidence_snapshot": dict(evidence_snapshot or {}),
        "next_action": str(next_action or ""),
    }


def _runtime_live_stage_missing(config: Any = None) -> tuple[dict[str, list[str]], dict[str, Any]]:
    from cas_forex import runtime_gates

    decision = runtime_gates.evaluate_live_trading(config)
    stage_missing = {stage: [] for stage in _LIVE_STAGE_ORDER}
    for requirement in decision.missing_requirements:
        stage = _LIVE_RUNTIME_STAGE_MAP.get(str(requirement), "live_gate")
        stage_missing.setdefault(stage, []).append(str(requirement))
    return stage_missing, decision.to_dict()


def _broker_truth_stage_report(
    runtime_missing: list[str],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    compact_snapshot = _compact_broker_truth_snapshot(snapshot)
    refresh_error = str(snapshot.get("action_time_refresh_error") or "").strip()
    if refresh_error:
        return _live_stage_record(
            "broker_truth",
            blocked=True,
            detail=(
                "Fresh broker truth is required before real dispatch, but the action-time "
                f"broker-truth refresh failed: {refresh_error}"
            ),
            missing_requirements=runtime_missing or ["continuous broker-truth monitor is fresh and live-connected"],
            evidence={"fresh_ready_for_live": False, "action_time_refresh_error": refresh_error},
            evidence_snapshot=compact_snapshot,
            next_action="Repair the broker-truth monitor refresh path, then rerun the live dispatch.",
        )
    ready_from_snapshot = _broker_truth_snapshot_ready_for_live(snapshot)
    next_action = str(snapshot.get("next_action") or "").strip()
    if ready_from_snapshot is not None:
        if ready_from_snapshot and not runtime_missing:
            return _live_stage_record(
                "broker_truth",
                blocked=False,
                detail="Action-time broker-truth refresh is fresh, live-connected, and reconciled for dispatch.",
                evidence={"fresh_ready_for_live": True, "readiness_source": "action_time_snapshot"},
                evidence_snapshot=compact_snapshot,
            )
        return _live_stage_record(
            "broker_truth",
            blocked=True,
            detail=(
                "Fresh broker truth is required before real dispatch; the action-time broker-truth report is not ready for live use."
            ),
            missing_requirements=runtime_missing or ["continuous broker-truth monitor is fresh and live-connected"],
            evidence={"fresh_ready_for_live": False, "readiness_source": "action_time_snapshot"},
            evidence_snapshot=compact_snapshot,
            next_action=next_action or "Run broker truth monitoring/checks and resolve any mismatch before retrying.",
        )
    try:
        ready = _fresh_broker_truth_ready_for_live()
        if ready and not runtime_missing:
            return _live_stage_record(
                "broker_truth",
                blocked=False,
                detail="Fresh broker-truth monitoring is visible for live dispatch.",
                evidence={"fresh_ready_for_live": True, "readiness_source": "cached_monitor_status"},
                evidence_snapshot=compact_snapshot,
            )
        return _live_stage_record(
            "broker_truth",
            blocked=True,
            detail=(
                "Fresh broker truth is required before real dispatch; the latest broker-truth monitor report is missing, stale, unreconciled, demo-only, or blocked."
            ),
            missing_requirements=runtime_missing,
            evidence={"fresh_ready_for_live": False, "readiness_source": "cached_monitor_status"},
            evidence_snapshot=compact_snapshot,
            next_action=next_action or "Run broker truth monitoring/checks and resolve any mismatch before retrying.",
        )
    except Exception as exc:
        return _live_stage_record(
            "broker_truth",
            blocked=True,
            detail="Fresh broker truth is required before real dispatch, but broker truth status is unreadable.",
            missing_requirements=runtime_missing or ["continuous broker-truth monitor is fresh and live-connected"],
            evidence={"read_error": str(exc)},
            evidence_snapshot=compact_snapshot,
            next_action="Restore broker-truth monitor visibility, then rerun the live dispatch.",
        )


def _broker_truth_snapshot_ready_for_live(snapshot: Mapping[str, Any]) -> bool | None:
    if not isinstance(snapshot, Mapping):
        return None
    generated = snapshot.get("generated_at")
    if not generated:
        return None
    try:
        generated_dt = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        age_seconds = (utc_now() - generated_dt).total_seconds()
    except Exception:
        return False
    if str(snapshot.get("overall_status") or "").upper() == "RECONCILIATION_FAILED":
        return False
    if not bool(snapshot.get("mt5_connected")) or snapshot.get("mt5_is_demo") is not False:
        return False
    if snapshot.get("mt5_account_identity_matches_config") is not True:
        return False
    try:
        fresh_limit = int(snapshot.get("fresh_for_live_seconds") or 180)
    except (TypeError, ValueError):
        fresh_limit = 180
    return 0 <= age_seconds <= fresh_limit


def _bridge_uses_mt5_terminal(bridge: Any, config: Any = None) -> bool:
    cfg = _resolve_config(config)
    bridge_name = getattr(getattr(bridge, "__class__", type(bridge)), "__name__", "")
    bridge_module = getattr(getattr(bridge, "__class__", type(bridge)), "__module__", "")
    if "mt5" in str(bridge_name).lower() or "mt5" in str(bridge_module).lower():
        return True
    if getattr(cfg, "prefer_mt5", False):
        return True
    if getattr(cfg, "mt5_login", 0) and getattr(cfg, "mt5_server", ""):
        return True
    return False


def _mt5_terminal_stage_report(
    *,
    config: Any = None,
    bridge: Any = None,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    if not _bridge_uses_mt5_terminal(bridge, config):
        return _live_stage_record(
            "mt5_terminal_permissions",
            blocked=False,
            detail="This live dispatch is not using an MT5 terminal-backed bridge, so no MT5 action-time permission check is required.",
            evidence={"mt5_terminal_check_required": False},
        )

    compact_snapshot = _compact_mt5_permission_snapshot(snapshot)
    permission_state = snapshot.get("permission_state") if isinstance(snapshot.get("permission_state"), Mapping) else {}
    account = snapshot.get("account") if isinstance(snapshot.get("account"), Mapping) else {}
    cfg = _resolve_config(config)

    missing: list[str] = []
    detail_parts: list[str] = []

    if snapshot.get("connected") is not True:
        missing.append("mt5_terminal_connected")
        detail_parts.append(str(snapshot.get("detail") or snapshot.get("error") or "MT5 terminal is not connected."))

    if snapshot.get("is_demo") is not False:
        missing.append("mt5_terminal_is_not_demo")
        detail_parts.append("The connected MT5 terminal is demo/read-only for live dispatch and must point at the intended real account.")

    if permission_state.get("can_submit_order_send") is not True:
        missing.append("mt5_order_send_ready_at_terminal")
        blockers = [str(item) for item in (permission_state.get("blockers") or []) if item]
        detail_parts.append(
            str(permission_state.get("plain_english") or "; ".join(blockers) or "MT5 terminal order_send is not ready.")
        )

    expected_login = getattr(cfg, "mt5_login", 0)
    actual_login = account.get("login")
    if expected_login and actual_login != expected_login:
        missing.append("mt5_terminal_login_matches_config")
        detail_parts.append(
            f"Connected MT5 account login {actual_login!s} does not match configured mt5_login {expected_login!s}."
        )

    expected_server = str(getattr(cfg, "mt5_server", "") or "").strip()
    actual_server = str(account.get("server") or "").strip()
    if expected_server and actual_server.lower() != expected_server.lower():
        missing.append("mt5_terminal_server_matches_config")
        detail_parts.append(
            f"Connected MT5 server {actual_server or 'unknown'} does not match configured mt5_server {expected_server}."
        )

    if missing:
        return _live_stage_record(
            "mt5_terminal_permissions",
            blocked=True,
            detail=" ".join(part for part in detail_parts if part).strip()
            or "Action-time MT5 terminal/account check failed before real dispatch.",
            missing_requirements=missing,
            evidence={
                "connected": snapshot.get("connected"),
                "is_demo": snapshot.get("is_demo"),
                "can_submit_order_send": permission_state.get("can_submit_order_send"),
                "expected_login": expected_login or None,
                "actual_login": actual_login,
                "expected_server": expected_server or None,
                "actual_server": actual_server or None,
            },
            evidence_snapshot=compact_snapshot,
            next_action=(
                "Open/log into the intended MT5 live terminal, enable Algo Trading, "
                "confirm the connected login/server match the configured live account, "
                "then retry the live dispatch."
            ),
        )
    return _live_stage_record(
        "mt5_terminal_permissions",
        blocked=False,
        detail="Action-time MT5 terminal/account check passed for the intended real account.",
        evidence={
            "connected": True,
            "is_demo": False,
            "can_submit_order_send": True,
            "expected_login": expected_login or None,
            "actual_login": actual_login,
            "expected_server": expected_server or None,
            "actual_server": actual_server or None,
        },
        evidence_snapshot=compact_snapshot,
    )


_ACCOUNT_FIELD_GROUPS: tuple[tuple[str, ...], ...] = (
    ("balance", "account_balance"),
    ("equity", "account_equity"),
    ("margin", "account_margin"),
    ("free_margin", "margin_free", "account_free_margin"),
)


def _has_float(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> bool:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            continue
    return False


def _account_candidates(
    account_snapshot: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        candidates.append(value)
        for key in ("account_snapshot", "account"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                candidates.append(nested)
        probe = value.get("probe")
        if isinstance(probe, Mapping):
            receipt = probe.get("receipt")
            if isinstance(receipt, Mapping):
                nested = receipt.get("account_snapshot")
                if isinstance(nested, Mapping):
                    candidates.append(nested)

    add(account_snapshot)
    add(live_telemetry)
    return candidates


def _complete_account_snapshot(
    account_snapshot: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    for candidate in _account_candidates(account_snapshot, live_telemetry):
        if all(_has_float(candidate, group) for group in _ACCOUNT_FIELD_GROUPS):
            return candidate
    return None


def _has_explicit_position_snapshot(live_telemetry: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(live_telemetry, Mapping):
        return False
    if "open_positions" in live_telemetry:
        return isinstance(live_telemetry.get("open_positions"), list)
    if "positions" in live_telemetry:
        return isinstance(live_telemetry.get("positions"), list)
    return False


def _explicit_position_rows(
    live_telemetry: Optional[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(live_telemetry, Mapping):
        return []
    for key in ("open_positions", "positions"):
        value = live_telemetry.get(key)
        if isinstance(value, list):
            return [dict(row) for row in value if isinstance(row, Mapping)]
    return []


def _tag_position_risk_source(
    row: Mapping[str, Any],
    source: str,
) -> dict[str, Any]:
    tagged = dict(row)
    tagged.setdefault("position_risk_source", str(source))
    return tagged


def _merge_position_rows(
    existing: list[dict[str, Any]],
    additional: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for row in [*existing, *additional]:
        if any(_same_position_identity(row, prior) for prior in merged):
            continue
        merged.append(dict(row))
    return merged


def _same_position_identity(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_ticket = str(left.get("broker_ticket") or left.get("ticket") or "").strip()
    right_ticket = str(right.get("broker_ticket") or right.get("ticket") or "").strip()
    left_source = str(left.get("position_risk_source") or "").strip()
    right_source = str(right.get("position_risk_source") or "").strip()
    if left_ticket and right_ticket and left_ticket == right_ticket:
        # Distinct brokers can legitimately issue the same numeric ticket.
        return not (left_source and right_source and left_source != right_source)
    if left_ticket or right_ticket:
        return False
    keys = ("symbol", "direction", "side", "volume", "lots", "open_price", "entry_price")
    return all(str(left.get(key) or "") == str(right.get(key) or "") for key in keys)


def _live_telemetry_is_marked_stale(live_telemetry: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(live_telemetry, Mapping):
        return False
    freshness = live_telemetry.get("data_freshness")
    if not isinstance(freshness, Mapping):
        return False
    return freshness.get("stale") is True


def _flat_account_value(mapping: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _normalize_mt5_risk_account(snapshot: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    account = snapshot.get("account") if isinstance(snapshot.get("account"), Mapping) else {}
    balance = _flat_account_value(account, "balance", "balance_usd")
    equity = _flat_account_value(account, "equity", "equity_usd")
    margin = _flat_account_value(account, "margin", "margin_used_usd")
    free_margin = _flat_account_value(account, "free_margin", "margin_free", "free_margin_usd")
    if balance is None or equity is None or margin is None or free_margin is None:
        return None
    return {
        "balance": balance,
        "equity": equity,
        "margin": margin,
        "free_margin": free_margin,
        "leverage": account.get("leverage"),
        "login": account.get("login"),
        "server": account.get("server"),
        "currency": account.get("currency"),
    }


def _action_time_live_risk_inputs(
    *,
    config: Any = None,
    bridge: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
) -> tuple[Optional[Mapping[str, Any]], Optional[Mapping[str, Any]]]:
    """Hydrate a missing/stale live risk snapshot from a fresh MT5 read.

    This only upgrades incomplete or stale caller inputs. Healthy explicit
    snapshots are preserved as-is.
    """
    needs_positions = not _has_explicit_position_snapshot(live_telemetry)
    needs_account = _complete_account_snapshot(account_snapshot, live_telemetry) is None
    telemetry_stale = _live_telemetry_is_marked_stale(live_telemetry)
    if not (needs_positions or needs_account or telemetry_stale):
        return live_telemetry, account_snapshot
    if not _bridge_uses_mt5_terminal(bridge, config):
        return live_telemetry, account_snapshot

    snapshot = _latest_mt5_live_risk_snapshot()
    if not isinstance(snapshot, Mapping) or snapshot.get("connected") is not True:
        return live_telemetry, account_snapshot

    positions = snapshot.get("positions") if isinstance(snapshot.get("positions"), list) else []
    normalized_account = _normalize_mt5_risk_account(snapshot)
    if not positions and normalized_account is None:
        return live_telemetry, account_snapshot

    prepared_live = dict(live_telemetry or {})
    prepared_live["open_positions"] = list(positions)
    freshness = (
        dict(prepared_live.get("data_freshness"))
        if isinstance(prepared_live.get("data_freshness"), Mapping)
        else {}
    )
    freshness.update(
        {
            "source": "mt5_action_time_snapshot",
            "stale": False,
            "last_update_iso": utc_now().isoformat(),
        }
    )
    prepared_live["data_freshness"] = freshness
    if normalized_account is not None:
        prepared_live["account_snapshot"] = normalized_account
        prepared_live["account"] = normalized_account
        return prepared_live, normalized_account
    return prepared_live, account_snapshot


def _action_time_paper_risk_telemetry(
    *,
    bridge: Any,
    live_telemetry: Optional[Mapping[str, Any]] = None,
) -> Optional[Mapping[str, Any]]:
    """Attach current primary paper-broker positions before the risk gate.

    An MT5 demo bridge is not a real-money bridge, so it does not enter the
    live-readiness hydrator. Without this paper-specific refresh, new demo
    orders could be checked against simulator positions only and ignore MT5
    demo exposure already on the account.
    """

    getter = getattr(bridge, "get_open_positions", None)
    if not callable(getter):
        return live_telemetry
    try:
        raw_positions = list(getter() or [])
    except Exception as exc:
        raise RuntimeError(
            "Paper broker position refresh failed before dispatch: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    bridge_source = type(bridge).__name__
    broker_positions = [
        _tag_position_risk_source(row, bridge_source)
        for row in raw_positions
        if isinstance(row, Mapping)
    ]
    prepared = dict(live_telemetry or {})
    prepared["open_positions"] = _merge_position_rows(
        _explicit_position_rows(live_telemetry),
        broker_positions,
    )
    prepared["paper_broker_position_hydration"] = {
        "status": "PRIMARY_PAPER_BROKER_POSITIONS_ATTACHED",
        "bridge_class": bridge_source,
        "primary_broker_position_count": len(broker_positions),
    }
    return prepared


def _action_time_paper_risk_account_snapshot(
    *,
    bridge: Any,
    account_snapshot: Optional[Mapping[str, Any]] = None,
) -> Optional[Mapping[str, Any]]:
    """Refresh paper/demo balance and equity before enforcing money caps."""

    getter = getattr(bridge, "get_account_info", None)
    if not callable(getter):
        return account_snapshot
    try:
        raw_account = getter() or {}
    except Exception as exc:
        raise RuntimeError(
            "Paper broker account refresh failed before dispatch: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(raw_account, Mapping):
        return account_snapshot
    prepared = dict(raw_account)
    if isinstance(account_snapshot, Mapping):
        prepared.update(dict(account_snapshot))
    if prepared.get("free_margin") is not None:
        prepared["margin_free"] = prepared.get("free_margin")
    elif prepared.get("margin_free") is not None:
        prepared["free_margin"] = prepared.get("margin_free")
    prepared["risk_snapshot_source"] = f"{type(bridge).__name__}.get_account_info"
    return prepared


def _require_real_risk_snapshot(
    *,
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
) -> Mapping[str, Any]:
    missing: list[str] = []
    if not _has_explicit_position_snapshot(live_telemetry):
        missing.append("live_telemetry.open_positions")
    if _live_telemetry_is_marked_stale(live_telemetry):
        missing.append("non_stale_live_telemetry")

    complete_account = _complete_account_snapshot(account_snapshot, live_telemetry)
    if complete_account is None:
        missing.append("account_snapshot.balance/equity/margin/free_margin")

    if missing:
        raise PermissionError(
            "fresh live risk snapshot required before real dispatch; missing: "
            + ", ".join(missing)
        )
    return complete_account


def _live_risk_snapshot_stage_report(
    *,
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
) -> tuple[dict[str, Any], Optional[Mapping[str, Any]]]:
    missing: list[str] = []
    if not _has_explicit_position_snapshot(live_telemetry):
        missing.append("live_telemetry.open_positions")
    if _live_telemetry_is_marked_stale(live_telemetry):
        missing.append("non_stale_live_telemetry")
    complete_account = _complete_account_snapshot(account_snapshot, live_telemetry)
    freshness = live_telemetry.get("data_freshness") if isinstance(live_telemetry, Mapping) else {}
    evidence_snapshot = {
        "source": freshness.get("source") if isinstance(freshness, Mapping) else None,
        "stale": freshness.get("stale") if isinstance(freshness, Mapping) else None,
        "last_update_iso": freshness.get("last_update_iso") if isinstance(freshness, Mapping) else None,
        "open_position_count": (
            len(live_telemetry.get("open_positions") or [])
            if isinstance(live_telemetry, Mapping) and isinstance(live_telemetry.get("open_positions"), list)
            else None
        ),
        "complete_account_snapshot": complete_account is not None,
    }
    if complete_account is None:
        missing.append("account_snapshot.balance/equity/margin/free_margin")
    if missing:
        return (
            _live_stage_record(
                "live_risk_snapshot",
                blocked=True,
                detail="Fresh live risk telemetry is required before real dispatch.",
                missing_requirements=missing,
                evidence={
                    "has_positions_snapshot": _has_explicit_position_snapshot(live_telemetry),
                    "telemetry_stale": _live_telemetry_is_marked_stale(live_telemetry),
                    "complete_account_snapshot": complete_account is not None,
                },
                evidence_snapshot=evidence_snapshot,
                next_action="Attach non-stale live positions plus complete balance/equity/margin/free-margin telemetry before retrying.",
            ),
            None,
        )
    return (
        _live_stage_record(
            "live_risk_snapshot",
            blocked=False,
            detail="Live positions and complete account margin telemetry are present.",
            evidence={
                "has_positions_snapshot": True,
                "telemetry_stale": False,
                "complete_account_snapshot": True,
            },
            evidence_snapshot=evidence_snapshot,
        ),
        complete_account,
    )


def _live_pilot_stage_report(
    proposed_intent: Mapping[str, Any],
    *,
    live_telemetry: Optional[Mapping[str, Any]],
    runtime_missing: list[str],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    from cas_forex import live_pilot

    compact_snapshot = _compact_live_pilot_snapshot(snapshot)
    try:
        policy = live_pilot.require_live_pilot_intent(
            proposed_intent,
            live_telemetry=live_telemetry,
        )
        return _live_stage_record(
            "live_pilot",
            blocked=False,
            detail="Live authority ACCEPT is current and this order stays inside the risk-denominated envelope.",
            evidence={
                "owner_pilot_status": (policy or {}).get("owner_pilot_status"),
                "ready_for_next_live_order": (policy or {}).get("ready_for_next_live_order"),
            },
            evidence_snapshot=compact_snapshot,
        )
    except Exception as exc:
        return _live_stage_record(
            "live_pilot",
            blocked=True,
            detail=str(exc),
            missing_requirements=runtime_missing,
            evidence_snapshot=compact_snapshot,
            next_action="Review the risk-denominated live authority and attach fresh stop-risk, margin, and portfolio evidence.",
        )


def build_live_dispatch_gate_report(
    proposed_intent: Mapping[str, Any],
    *,
    config: Any = None,
    bridge: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
) -> tuple[dict[str, Any], Optional[Mapping[str, Any]]]:
    stage_missing, live_decision = _runtime_live_stage_missing(config)
    broker_truth_snapshot = _action_time_broker_truth_snapshot()
    if _broker_truth_snapshot_ready_for_live(broker_truth_snapshot) and not str(
        broker_truth_snapshot.get("action_time_refresh_error") or ""
    ).strip():
        stage_missing["broker_truth"] = []
    mt5_permission_snapshot = _latest_mt5_permission_snapshot()
    live_recovery_snapshot = _live_recovery_snapshot()
    live_order_dry_run_review_snapshot = _live_order_dry_run_review_snapshot()
    live_pilot_snapshot = _live_pilot_snapshot()

    checks: list[dict[str, Any]] = []
    for stage in ("live_gate", "auto_halt", "live_recovery", "live_order_dry_run_review"):
        missing = list(stage_missing.get(stage) or [])
        detail_by_stage = {
            "live_gate": "Owner live authority, credentials, broker selection, and acknowledgments are current.",
            "auto_halt": "Auto-halt is clear for live dispatch.",
            "live_recovery": "Crash/disconnect recovery review is clear for live dispatch.",
            "live_order_dry_run_review": "Owner ACCEPTED the latest passing live-order dry run against fresh broker truth.",
        }
        evidence_snapshot: Mapping[str, Any] | None = None
        if stage == "live_recovery":
            evidence_snapshot = _compact_live_recovery_snapshot(live_recovery_snapshot)
        elif stage == "live_order_dry_run_review":
            evidence_snapshot = _compact_live_order_dry_run_review_snapshot(live_order_dry_run_review_snapshot)
        checks.append(
            _live_stage_record(
                stage,
                blocked=bool(missing),
                detail=("; ".join(missing) if missing else detail_by_stage[stage]),
                missing_requirements=missing,
                evidence_snapshot=evidence_snapshot,
                next_action="" if not missing else str(live_decision.get("next_action") or ""),
            )
        )

    broker_truth_stage = _broker_truth_stage_report(
        list(stage_missing.get("broker_truth") or []),
        broker_truth_snapshot,
    )
    checks.append(broker_truth_stage)
    checks.append(
        _mt5_terminal_stage_report(
            config=config,
            bridge=bridge,
            snapshot=mt5_permission_snapshot,
        )
    )

    live_risk_stage, prepared_account_snapshot = _live_risk_snapshot_stage_report(
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
    )
    checks.append(live_risk_stage)

    checks.append(
        _live_pilot_stage_report(
            proposed_intent,
            live_telemetry=live_telemetry,
            runtime_missing=list(stage_missing.get("live_pilot") or []),
            snapshot=live_pilot_snapshot,
        )
    )

    blocking_stage = next((check["stage"] for check in checks if check["status"] == "BLOCKED"), None)
    overall_status = "BLOCKED" if blocking_stage else "PASSED"
    blocking_detail = next((check["detail"] for check in checks if check["stage"] == blocking_stage), "")
    next_action = next((check["next_action"] for check in checks if check["stage"] == blocking_stage), "")
    return (
        {
            "report_kind": "cas_forex_live_dispatch_gate_report",
            "overall_status": overall_status,
            "blocking_stage": blocking_stage,
            "blocking_detail": blocking_detail,
            "next_action": next_action,
            "checks": checks,
            "live_trading_decision": live_decision,
            "evidence_snapshots": {
                "broker_truth": _compact_broker_truth_snapshot(broker_truth_snapshot),
                "mt5_terminal_permissions": _compact_mt5_permission_snapshot(mt5_permission_snapshot),
                "live_recovery": _compact_live_recovery_snapshot(live_recovery_snapshot),
                "live_order_dry_run_review": _compact_live_order_dry_run_review_snapshot(
                    live_order_dry_run_review_snapshot
                ),
                "live_risk_snapshot": dict((live_risk_stage or {}).get("evidence_snapshot") or {}),
                "live_pilot": _compact_live_pilot_snapshot(live_pilot_snapshot),
            },
        },
        prepared_account_snapshot,
    )


def require_live_dispatch_ready(
    proposed_intent: Mapping[str, Any],
    *,
    config: Any = None,
    bridge: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
) -> Mapping[str, Any]:
    report, prepared_account_snapshot = build_live_dispatch_gate_report(
        proposed_intent,
        config=config,
        bridge=bridge,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
    )
    if report.get("blocking_stage"):
        raise LiveDispatchBlocked(
            stage=str(report.get("blocking_stage") or "live_gate"),
            detail=str(report.get("blocking_detail") or "Live dispatch gate blocked."),
            report=report,
        )
    return prepared_account_snapshot or {}


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


_REAL_DISPATCH_PREFLIGHT_NEXT_ACTIONS = {
    "dispatch_preflight": (
        "Restore the order-dispatch evidence helpers before attempting another real order."
    ),
    "market_availability": (
        "Attach explicit market/session/symbol tradability evidence and retry only while the symbol is open and trade-enabled."
    ),
    "macro_blackout": (
        "Wait for the macro/news blackout to clear or intentionally disable that gate before retrying."
    ),
    "execution_quality": (
        "Refresh quote/slippage evidence or tighten broker controls until spread and slippage are back inside owner tolerance."
    ),
    "order_constraints": (
        "Adjust symbol mapping, lot size, or protective-order geometry so the request fits the broker symbol contract, lot step, and minimum stop distance."
    ),
}


def _build_real_dispatch_preflight_report(
    *,
    order: Any,
    proposed_intent: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
    bridge: Any = None,
    config: Any = None,
) -> dict[str, Any]:
    try:
        from cas_forex.order_dispatch import (
            _execution_quality_report,
            _macro_blackout_report,
            _market_availability_report,
            _order_constraints_report,
        )
    except Exception as exc:
        detail = (
            "Real dispatch preflight is unavailable because the shared dispatch "
            f"evidence helpers failed to load: {type(exc).__name__}: {exc}"
        )
        return {
            "report_kind": "cas_forex_real_dispatch_preflight_report",
            "overall_status": "BLOCKED",
            "blocking_stage": "dispatch_preflight",
            "blocking_detail": detail,
            "next_action": _REAL_DISPATCH_PREFLIGHT_NEXT_ACTIONS["dispatch_preflight"],
            "checks": [],
            "market_availability": {},
            "macro_blackout": {},
            "execution_quality": {},
            "order_constraints": {},
        }

    market_availability = _market_availability_report(
        order=order,
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        config=config,
    )
    macro_blackout = _macro_blackout_report(
        order=order,
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        config=config,
    )
    execution_quality = _execution_quality_report(
        order=order,
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        config=config,
    )
    order_constraints = _order_constraints_report(
        order=order,
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        bridge=bridge,
        config=config,
    )

    stage_reports = (
        ("market_availability", market_availability),
        ("macro_blackout", macro_blackout),
        ("execution_quality", execution_quality),
        ("order_constraints", order_constraints),
    )

    checks: list[dict[str, Any]] = []
    blocking_stage = None
    blocking_detail = ""
    next_action = ""
    for stage, stage_report in stage_reports:
        blocked = bool(stage_report.get("block"))
        blockers = list(stage_report.get("blockers") or [])
        if not blockers and isinstance(stage_report.get("checks"), list):
            blockers = [
                str(item.get("detail") or item.get("check") or "")
                for item in stage_report.get("checks", [])
                if str(item.get("status") or "").upper() == "BLOCKED"
            ]
        detail = str(stage_report.get("detail") or "")
        checks.append(
            {
                "stage": stage,
                "status": "BLOCKED" if blocked else str(stage_report.get("status") or "UNKNOWN"),
                "detail": detail,
                "blockers": blockers,
                "next_action": (
                    _REAL_DISPATCH_PREFLIGHT_NEXT_ACTIONS.get(stage, "") if blocked else ""
                ),
            }
        )
        if blocking_stage is None and blocked:
            blocking_stage = stage
            blocking_detail = detail or f"Real dispatch blocked at {stage}."
            next_action = _REAL_DISPATCH_PREFLIGHT_NEXT_ACTIONS.get(stage, "")

    return {
        "report_kind": "cas_forex_real_dispatch_preflight_report",
        "overall_status": "BLOCKED" if blocking_stage else "PASSED",
        "blocking_stage": blocking_stage,
        "blocking_detail": blocking_detail,
        "next_action": next_action,
        "checks": checks,
        "market_availability": market_availability,
        "macro_blackout": macro_blackout,
        "execution_quality": execution_quality,
        "order_constraints": order_constraints,
    }


def _require_real_dispatch_preflight(
    *,
    order: Any,
    proposed_intent: Optional[Mapping[str, Any]],
    live_telemetry: Optional[Mapping[str, Any]],
    account_snapshot: Optional[Mapping[str, Any]],
    bridge: Any = None,
    config: Any = None,
) -> Mapping[str, Any]:
    report = _build_real_dispatch_preflight_report(
        order=order,
        proposed_intent=proposed_intent,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        bridge=bridge,
        config=config,
    )
    if report.get("blocking_stage"):
        raise LiveDispatchBlocked(
            stage=str(report.get("blocking_stage") or "dispatch_preflight"),
            detail=str(report.get("blocking_detail") or "Real dispatch preflight blocked."),
            report=report,
        )
    return report


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

      1. Require a fresh matching EDGE PASS token, or for a winning scale-in an
         exact one-shot AI Operator edge authorization, for every real-money
         dispatch and every registered decision_ref. Missing authorization is the earliest
         hard stop, so a live order never gets to look "almost ready" without
         valid edge authorization.
      2. If this dispatch would touch a real broker -- either the app is in live
         mode OR the bridge reports it will place a real order
         (``will_execute_real_order``) -- re-assert the owner live-trading gate
         plus action-time live readiness.
      3. Require fresh broker truth at the real-order chokepoint, even if a
         future caller changes the broader live gate.
      4. Require explicit live account/position risk telemetry for real dispatch.
      5. Enforce the owner-accepted small-live-pilot envelope.
      6. Enforce the configured daily realized-loss cap over reconciled broker
         history. This blocks new entries/scale-ins, not risk-reducing position
         management.
      7. Run the pre-execution risk gate over the proposed intent -- raises
         ``ExecutionBlocked`` on any cap breach.
      8. Only then call ``bridge.execute_order(order)`` (real bridges) -- falling
         back to ``bridge.place_order`` for test fakes -- and return its result.

    ``proposed_intent`` overrides the symbol/direction/lots inferred from
    ``order`` if supplied.
    """
    intent = dict(proposed_intent) if proposed_intent else _intent_from_order(order)

    is_real = _is_live_execution(config) or _bridge_executes_real(bridge)

    # Fail-closed EDGE gate -- the WASTE loop's TEST step, enforced at the dispatch
    # chokepoint so it can never be skipped. A real-money dispatch, and any order
    # the loop registered for its decision_ref, MUST carry a fresh, matching PASS
    # from ``edge_gate`` (a measured win-prob >= the owner threshold that beat the
    # null). No PASS => ``EdgeNotAuthorized`` and the bridge is never touched.
    # Legacy paper dispatch (no registration, not live) is unaffected.
    from cas_forex import edge_authorization, operator_scale_in_authorization

    decision_ref = getattr(order, "decision_ref", None)
    operator_scale_in_required = operator_scale_in_authorization.is_required(decision_ref)
    compound_slot_authorized = False
    edge_required = (
        is_real
        or edge_authorization.is_required(decision_ref)
        or operator_scale_in_required
    )
    if edge_required:
        if operator_scale_in_required:
            operator_scale_in_authorization.require(
                order,
                proposed_intent=intent,
                bridge=bridge,
                config=config,
            )
            compound_slot_authorized = True
        else:
            edge_authorization.require(
                order,
                is_real=is_real,
                config=config,
                bridge=bridge,
                volume=intent.get("lots", getattr(order, "volume", None)),
                order_type=getattr(order, "order_type", None),
                price=getattr(order, "price", None),
                strategy_id=intent.get("strategy_id"),
                proposed_intent=intent,
            )

    risk_live_telemetry = live_telemetry
    risk_account_snapshot = account_snapshot
    if is_real:
        risk_live_telemetry, risk_account_snapshot = _action_time_live_risk_inputs(
            config=config,
            bridge=bridge,
            live_telemetry=live_telemetry,
            account_snapshot=account_snapshot,
        )
        risk_account_snapshot = require_live_dispatch_ready(
            intent,
            config=config,
            bridge=bridge,
            live_telemetry=risk_live_telemetry,
            account_snapshot=risk_account_snapshot,
        )
        _require_real_dispatch_preflight(
            order=order,
            proposed_intent=intent,
            live_telemetry=risk_live_telemetry,
            account_snapshot=risk_account_snapshot,
            bridge=bridge,
            config=config,
        )
    else:
        risk_live_telemetry = _action_time_paper_risk_telemetry(
            bridge=bridge,
            live_telemetry=risk_live_telemetry,
        )
        risk_account_snapshot = _action_time_paper_risk_account_snapshot(
            bridge=bridge,
            account_snapshot=risk_account_snapshot,
        )

    require_daily_realized_loss_ready(
        bridge=bridge,
        config=config,
        live_telemetry=risk_live_telemetry,
        account_snapshot=risk_account_snapshot,
    )
    guard(
        intent,
        config=config,
        live_telemetry=risk_live_telemetry,
        account_snapshot=risk_account_snapshot,
        equity_peak=equity_peak,
        compound_slot_authorized=compound_slot_authorized,
    )
    order_reference_setter = getattr(bridge, "set_order_reference_price", None)
    if callable(order_reference_setter):
        try:
            order_reference_price = float(intent.get("entry_price") or 0.0)
        except (TypeError, ValueError):
            order_reference_price = 0.0
        if order_reference_price > 0:
            order_reference_setter(str(getattr(order, "order_id", "")), order_reference_price)
    # The real broker bridges (MT5Bridge / SimulatedBrokerBridge / MT4EABridge)
    # expose ``execute_order``; only test fakes define ``place_order``. Prefer
    # the real method and fall back so both work through this one chokepoint.
    dispatch = getattr(bridge, "execute_order", None) or getattr(bridge, "place_order", None)
    if not callable(dispatch):
        raise TypeError(
            "broker bridge exposes neither execute_order nor place_order; "
            "cannot dispatch order"
        )
    if edge_required:
        if operator_scale_in_required:
            operator_scale_in_authorization.consume(
                order,
                proposed_intent=intent,
                bridge=bridge,
                config=config,
            )
        else:
            edge_authorization.consume(
                order,
                is_real=is_real,
                config=config,
                bridge=bridge,
                volume=intent.get("lots", getattr(order, "volume", None)),
                order_type=getattr(order, "order_type", None),
                price=getattr(order, "price", None),
                strategy_id=intent.get("strategy_id"),
                proposed_intent=intent,
            )
    return dispatch(order)
