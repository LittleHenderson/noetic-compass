"""Execution provenance snapshots for trade auditability."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from typing import Any, Optional

from cas_forex.time_utils import utc_now

PROVENANCE_REPORT_KIND = "cas_forex_execution_provenance"
PROVENANCE_SCHEMA_VERSION = "cas_forex_execution_provenance.v1"

_CONFIG_FIELDS = (
    "live_mode",
    "paper_trading",
    "selected_broker_id",
    "broker_name",
    "broker_platform",
    "broker_strictness",
    "prefer_mt5",
    "market_data_provider",
    "max_daily_drawdown_pct",
    "max_weekly_drawdown_pct",
    "max_position_lots",
    "max_open_positions",
    "max_total_exposure_lots",
    "max_risk_per_trade_pct",
    "max_correlated_exposure_lots",
    "max_slippage_points",
    "broker_max_spread_pips",
    "broker_max_slippage_pips",
    "broker_min_lot",
    "broker_max_lot",
    "broker_min_stop_distance_pips",
    "macro_blackout_enabled",
    "owner_enable_live_trading",
    "owner_enable_broker_accept",
    "live_trading_licensed",
    "mt5_treat_account_as_demo",
)

_MODEL_FIELDS = (
    "ai_operator_enabled",
    "ai_operator_primary_backend",
    "ai_operator_primary_model",
    "ai_operator_token_budget",
    "ai_operator_max_tokens",
    "ai_model_enabled",
    "ai_model_backend",
    "ai_model_name",
    "ai_model_control_plane",
    "ai_model_pcba_guard_enabled",
)


def build_execution_provenance(
    *,
    order: Any = None,
    proposed_intent: Optional[Mapping[str, Any]] = None,
    config: Any = None,
    bridge: Any = None,
    strategy_id: Optional[str] = None,
    ai_action: str = "DISPATCH",
    outcome: Any = None,
    source: str = "order_dispatch",
    dispatch_result: Any = None,
    mode: Optional[str] = None,
    audit: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Build a redacted, stable snapshot explaining what versions/config acted.

    The snapshot is evidence only. It does not authorize trading or alter any
    dispatch behavior.
    """
    cfg = _resolve_config(config)
    config_snapshot = _config_snapshot(cfg)
    model_snapshot = _model_snapshot(cfg)
    operator_decision = _operator_decision_snapshot(proposed_intent)
    sizing_snapshot = _operator_sizing_snapshot(proposed_intent)
    if operator_decision.get("model_ref"):
        model_snapshot.update(
            {
                "decision_model_ref": operator_decision.get("model_ref"),
                "decision_model_backend": operator_decision.get("model_backend"),
                "decision_provider": operator_decision.get("provider"),
                "decision_provider_label": operator_decision.get("provider_label"),
                "decision_prompt_version": operator_decision.get("prompt_version"),
                "decision_prompt_hash": operator_decision.get("decision_prompt_hash"),
                "decision_system_prompt_hash": operator_decision.get("system_prompt_hash"),
                "operator_event_hash": operator_decision.get("operator_event_hash"),
            }
        )
    market_snapshot = _market_snapshot(cfg, outcome=outcome)
    payload = {
        "report_kind": PROVENANCE_REPORT_KIND,
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "captured_at_iso": utc_now().isoformat(),
        "source": str(source or "order_dispatch"),
        "initiator": _initiator_snapshot(order, proposed_intent, source=source, ai_action=ai_action),
        "strategy": {
            "strategy_id": strategy_id or _intent_value(proposed_intent, "strategy_id"),
            "ai_action": str(ai_action or _intent_value(proposed_intent, "ai_action") or "DISPATCH"),
            "decision_ref": _attr(order, "decision_ref") or _intent_value(proposed_intent, "decision_ref"),
            "market_regime": _intent_value(proposed_intent, "market_regime"),
            "market_regime_source": _intent_value(
                proposed_intent, "market_regime_source"
            ),
            "order_comment": _attr(order, "comment"),
            "magic_number": _attr(order, "magic_number"),
            "strategy_version": "strategy_context.v2",
        },
        "model": model_snapshot,
        "operator_decision": operator_decision,
        "sizing": sizing_snapshot,
        "risk_engine": {
            "execution_guard_version": "execution_guard.v1",
            "pre_execution_risk_gate_version": "pre_execution_risk_gate.v1",
            "risk_control_version": "risk_control.v1",
            "runtime_gate_version": "runtime_gates.v1",
            "risk_cap_config_fields": {
                key: config_snapshot.get(key)
                for key in (
                    "max_open_positions",
                    "max_total_exposure_lots",
                    "max_daily_drawdown_pct",
                    "max_weekly_drawdown_pct",
                    "max_risk_per_trade_pct",
                    "max_slippage_points",
                    "broker_min_lot",
                    "broker_max_lot",
                )
                if key in config_snapshot
            },
        },
        "market_data": market_snapshot,
        "runtime_lane": _runtime_lane_snapshot(
            cfg,
            bridge=bridge,
            outcome=outcome,
            dispatch_result=dispatch_result,
            mode=mode,
        ),
        "dispatch_path": _dispatch_path_snapshot(dispatch_result, outcome=outcome),
        "attempt_audit": _audit_trace_snapshot(audit),
        "broker_bridge": {
            "bridge_name": bridge.__class__.__name__ if bridge is not None else "",
            "will_execute_real_order": _bridge_real_probe(bridge),
        },
        "order_shape": _order_shape(order, proposed_intent),
        "config_snapshot": config_snapshot,
        "config_hash": _hash_payload(config_snapshot),
        "claim_boundary": (
            "Execution provenance is read-only audit metadata. It records the "
            "model, strategy, risk, market-data, broker-symbol, and config "
            "context for this dispatch result; it does not authorize or place orders."
        ),
    }
    payload["version_trace"] = _version_trace_summary(payload)
    payload["provenance_hash"] = _hash_payload({k: v for k, v in payload.items() if k != "provenance_hash"})
    return payload


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


def _config_snapshot(config: Any) -> dict[str, Any]:
    return {
        field: _safe_json(getattr(config, field))
        for field in _CONFIG_FIELDS
        if hasattr(config, field)
    }


def _model_snapshot(config: Any) -> dict[str, Any]:
    snapshot = {
        field: _safe_json(getattr(config, field))
        for field in _MODEL_FIELDS
        if hasattr(config, field)
    }
    snapshot["assistant_model"] = os.environ.get("CAS_FOREX_ASSISTANT_MODEL", "claude-sonnet-4-6")
    prompt_text = ""
    try:
        from cas_forex import ai_operator

        prompt_text = str(getattr(ai_operator, "_OPERATOR_SYSTEM_PROMPT", "") or "")
    except Exception:
        prompt_text = ""
    snapshot["ai_operator_prompt_version"] = "ai_operator_system_prompt.v1"
    snapshot["ai_operator_prompt_hash"] = _hash_text(prompt_text) if prompt_text else None
    return snapshot


def _operator_decision_snapshot(
    proposed_intent: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "decision": _intent_value(proposed_intent, "operator_decision"),
        "conviction": _intent_value(proposed_intent, "operator_conviction"),
        "reason": _intent_value(proposed_intent, "operator_reason"),
        "provider": _intent_value(proposed_intent, "operator_provider"),
        "provider_label": _intent_value(proposed_intent, "operator_provider_label"),
        "model_ref": _intent_value(proposed_intent, "operator_model_ref"),
        "model_backend": _intent_value(proposed_intent, "operator_model_backend"),
        "prompt_version": _intent_value(proposed_intent, "operator_prompt_version"),
        "decision_prompt_hash": _intent_value(
            proposed_intent, "operator_decision_prompt_hash"
        ),
        "system_prompt_hash": _intent_value(
            proposed_intent, "operator_system_prompt_hash"
        ),
        "decision_context_hash": _intent_value(
            proposed_intent, "operator_decision_context_hash"
        ),
        "candidate_snapshot_hash": _intent_value(
            proposed_intent, "operator_candidate_snapshot_hash"
        ),
        "candidate_hash": _intent_value(proposed_intent, "operator_candidate_hash"),
        "action_ref": _intent_value(proposed_intent, "operator_action_ref"),
        "action_set_hash": _intent_value(proposed_intent, "operator_action_set_hash"),
        "operator_event_hash": _intent_value(proposed_intent, "operator_event_hash"),
        "growth_case": _intent_value(proposed_intent, "operator_growth_case"),
        "growth_evidence_state": _intent_value(proposed_intent, "growth_evidence_state"),
        "regime_identity_available": _intent_value(
            proposed_intent, "regime_identity_available"
        ),
        "regime_comparable_outcome_count": _intent_value(
            proposed_intent, "regime_comparable_outcome_count"
        ),
        "all_regimes_growth_evidence_state": _intent_value(
            proposed_intent, "all_regimes_growth_evidence_state"
        ),
    }


def _operator_sizing_snapshot(
    proposed_intent: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    offered = _safe_json(_intent_value(proposed_intent, "sizing_options_offered"))
    if not isinstance(offered, list):
        offered = []
    return {
        "sizing_ref": _intent_value(proposed_intent, "sizing_ref"),
        "label": _intent_value(proposed_intent, "sizing_label"),
        "selected_lots": _intent_value(proposed_intent, "lots"),
        "sizing_plan_hash": _intent_value(proposed_intent, "sizing_plan_hash"),
        "offered_options": offered[:5],
        "offered_option_count": _intent_value(
            proposed_intent, "sizing_option_count"
        ),
        "max_executable_lots": _intent_value(
            proposed_intent, "max_executable_lots"
        ),
        "limiting_source": _intent_value(
            proposed_intent, "sizing_limiting_source"
        ),
        "fallback_selection_policy": _intent_value(
            proposed_intent, "fallback_selection_policy"
        ),
        "selection_source": (
            "AI_OPERATOR_EXACT_OPTION"
            if _intent_value(proposed_intent, "sizing_ref")
            else "NOT_ATTACHED"
        ),
    }


def _market_snapshot(config: Any, *, outcome: Any = None) -> dict[str, Any]:
    outcome_payload = _safe_json(outcome) if outcome is not None else {}
    if not isinstance(outcome_payload, Mapping):
        outcome_payload = {}
    raw_request = outcome_payload.get("raw_request_snapshot") if isinstance(outcome_payload.get("raw_request_snapshot"), Mapping) else {}
    overrides = str(getattr(config, "mt5_symbol_overrides", "") or "")
    return {
        "market_data_provider": getattr(config, "market_data_provider", None),
        "mt5_symbol_overrides_configured": bool(overrides.strip()),
        "mt5_symbol_overrides_hash": _hash_text(overrides) if overrides.strip() else None,
        "broker_symbol": outcome_payload.get("broker_symbol") or raw_request.get("symbol"),
        "broker_symbol_resolution": outcome_payload.get("broker_symbol_resolution"),
        "raw_request_symbol": raw_request.get("symbol"),
        "broker_mode": outcome_payload.get("broker_mode"),
        "is_real_broker": outcome_payload.get("is_real_broker"),
        "is_demo_account": outcome_payload.get("is_demo_account"),
        "account_mode": _outcome_account_mode(outcome_payload),
        "live_money_broker": _outcome_account_mode(outcome_payload) == "LIVE",
        "terminal_name": outcome_payload.get("terminal_name"),
        "server": outcome_payload.get("server"),
    }


def _initiator_snapshot(
    order: Any,
    proposed_intent: Optional[Mapping[str, Any]],
    *,
    source: str,
    ai_action: str,
) -> dict[str, Any]:
    action = str(ai_action or _intent_value(proposed_intent, "ai_action") or "DISPATCH").strip().upper()
    comment = str(_attr(order, "comment") or "")
    manual = action in {"MANUAL", "OWNER_MANUAL", "OWNER_ORDER"} or "MANUAL" in comment.upper()
    return {
        "kind": "OWNER_MANUAL" if manual else "AI_AUTOMATION",
        "source": str(source or "order_dispatch"),
        "ai_action": action or "DISPATCH",
        "decision_ref": _attr(order, "decision_ref") or _intent_value(proposed_intent, "decision_ref"),
        "order_id": _attr(order, "order_id") or _intent_value(proposed_intent, "order_id"),
        "manual_order_journal_attached": bool(_intent_value(proposed_intent, "manual_order_journal")),
    }


def _runtime_lane_snapshot(
    config: Any,
    *,
    bridge: Any = None,
    outcome: Any = None,
    dispatch_result: Any = None,
    mode: Optional[str] = None,
) -> dict[str, Any]:
    configured_mode = str(mode or ("LIVE" if bool(getattr(config, "live_mode", False)) else "PAPER")).upper()
    bridge_real_capable = _bridge_real_probe(bridge)
    outcome_payload = _safe_json(outcome if outcome is not None else _attr(dispatch_result, "outcome"))
    if not isinstance(outcome_payload, Mapping):
        outcome_payload = {}
    real_broker_confirmed = outcome_payload.get("is_real_broker")
    demo_account_confirmed = outcome_payload.get("is_demo_account")
    account_mode = _outcome_account_mode(outcome_payload)
    return {
        "configured_mode": configured_mode,
        "effective_lane": _effective_lane(
            configured_mode=configured_mode,
            bridge_real_capable=bridge_real_capable,
            real_broker_confirmed=real_broker_confirmed,
            demo_account_confirmed=demo_account_confirmed,
        ),
        "bridge_name": bridge.__class__.__name__ if bridge is not None else "",
        "bridge_real_capable": bridge_real_capable,
        "real_broker_confirmed": real_broker_confirmed,
        "demo_account_confirmed": demo_account_confirmed,
        "account_mode": account_mode,
        "live_money_broker_confirmed": account_mode == "LIVE",
        "broker_mode": outcome_payload.get("broker_mode"),
        "paper_trading_enabled": getattr(config, "paper_trading", None),
    }


def _dispatch_path_snapshot(dispatch_result: Any, *, outcome: Any = None) -> dict[str, Any]:
    status = str(_attr(dispatch_result, "status") or "")
    dispatched_to_bridge = bool(_attr(dispatch_result, "dispatched_to_bridge"))
    executed = bool(_attr(dispatch_result, "executed"))
    reason = _attr(dispatch_result, "reason")
    live_gate_report = _mapping(_attr(dispatch_result, "live_gate_report"))
    outcome_payload = _safe_json(outcome if outcome is not None else _attr(dispatch_result, "outcome"))
    if not isinstance(outcome_payload, Mapping):
        outcome_payload = {}
    ledger_payload = _safe_json(_attr(dispatch_result, "ledger_event"))
    if not isinstance(ledger_payload, Mapping):
        ledger_payload = {}
    return {
        "final_status": status or "PENDING_RESULT",
        "final_reason": reason,
        "gate_outcome": _gate_outcome_for_status(status, executed=executed),
        "terminal_stage": _terminal_stage_for_status(
            status,
            dispatched_to_bridge=dispatched_to_bridge,
            live_gate_report=live_gate_report,
        ),
        "blocked_stage": _blocked_stage_for_status(status, live_gate_report=live_gate_report),
        "bridge_touch_state": _bridge_touch_state(
            status=status,
            dispatched_to_bridge=dispatched_to_bridge,
            outcome_present=bool(outcome_payload),
        ),
        "broker_status": outcome_payload.get("status"),
        "order_executed": executed,
        "real_broker": bool(outcome_payload.get("is_real_broker")),
        "external_broker_terminal": bool(outcome_payload.get("is_real_broker")),
        "is_demo_account": outcome_payload.get("is_demo_account"),
        "account_mode": _outcome_account_mode(outcome_payload),
        "live_money_broker": _outcome_account_mode(outcome_payload) == "LIVE",
        "external_money_movement": bool(ledger_payload.get("external_money_movement")),
    }


def _audit_trace_snapshot(audit: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    row = _mapping(audit)
    return {
        "attempt_id": row.get("attempt_id"),
        "status": row.get("status"),
        "result_finalized": row.get("result_finalized"),
        "source": row.get("source"),
        "bridge_name": row.get("bridge_name"),
        "mode": row.get("mode"),
    }


def _order_shape(order: Any, proposed_intent: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "order_id": _attr(order, "order_id") or _intent_value(proposed_intent, "order_id"),
        "decision_ref": _attr(order, "decision_ref") or _intent_value(proposed_intent, "decision_ref"),
        "symbol": _attr(order, "symbol") or _intent_value(proposed_intent, "symbol"),
        "direction": _direction_value(_attr(order, "direction")) or _intent_value(proposed_intent, "direction"),
        "volume": _attr(order, "volume") or _intent_value(proposed_intent, "lots"),
        "order_type": _direction_value(_attr(order, "order_type")),
        "price": _attr(order, "price"),
        "stop_loss": _attr(order, "stop_loss"),
        "take_profit": _attr(order, "take_profit"),
    }


def _version_trace_summary(provenance: Mapping[str, Any]) -> dict[str, Any]:
    initiator = _mapping(provenance.get("initiator"))
    strategy = _mapping(provenance.get("strategy"))
    model = _mapping(provenance.get("model"))
    operator_decision = _mapping(provenance.get("operator_decision"))
    sizing = _mapping(provenance.get("sizing"))
    risk = _mapping(provenance.get("risk_engine"))
    market = _mapping(provenance.get("market_data"))
    runtime_lane = _mapping(provenance.get("runtime_lane"))
    bridge = _mapping(provenance.get("broker_bridge"))

    strategy_ref = _first_nonempty(strategy.get("strategy_id"), strategy.get("decision_ref"))
    strategy_version = _first_nonempty(strategy.get("strategy_version"))
    model_ref = _first_nonempty(
        operator_decision.get("model_ref"),
        model.get("decision_model_ref"),
        model.get("ai_operator_primary_model"),
        model.get("ai_model_name"),
        model.get("assistant_model"),
    )
    prompt_version = _first_nonempty(
        operator_decision.get("prompt_version"),
        model.get("decision_prompt_version"),
        model.get("ai_operator_prompt_version"),
    )
    prompt_hash = _first_nonempty(
        operator_decision.get("decision_prompt_hash"),
        model.get("decision_prompt_hash"),
        operator_decision.get("system_prompt_hash"),
        model.get("ai_operator_prompt_hash"),
    )
    market_data_source = _first_nonempty(
        market.get("market_data_provider"),
        market.get("terminal_name"),
        market.get("server"),
        market.get("broker_mode"),
    )
    broker_symbol = _first_nonempty(market.get("broker_symbol"), market.get("raw_request_symbol"))
    config_hash = _first_nonempty(provenance.get("config_hash"))
    bridge_name = _first_nonempty(bridge.get("bridge_name"))

    risk_versions = {
        "execution_guard": _first_nonempty(risk.get("execution_guard_version")),
        "pre_execution_risk_gate": _first_nonempty(risk.get("pre_execution_risk_gate_version")),
        "risk_control": _first_nonempty(risk.get("risk_control_version")),
        "runtime_gates": _first_nonempty(risk.get("runtime_gate_version")),
    }

    gaps: list[str] = []
    if not strategy_ref:
        gaps.append("strategy_ref_not_attached")
    if not strategy_version:
        gaps.append("strategy_version_not_attached")
    if not model_ref:
        gaps.append("model_ref_not_attached")
    if not prompt_version:
        gaps.append("prompt_version_not_attached")
    if prompt_version and not prompt_hash:
        gaps.append("prompt_hash_not_attached")
    if not market_data_source:
        gaps.append("market_data_source_not_attached")
    if not config_hash:
        gaps.append("config_hash_not_attached")
    if not bridge_name:
        gaps.append("broker_bridge_not_attached")

    return {
        "trace_status": "COMPLETE" if not gaps else "PARTIAL",
        "trace_source": "execution_provenance",
        "strategy_ref": strategy_ref or "not_attached",
        "strategy_version": strategy_version or "not_attached",
        "ai_action": _first_nonempty(strategy.get("ai_action")) or "not_attached",
        "model_ref": model_ref or "not_attached",
        "model_provider": _first_nonempty(
            operator_decision.get("provider"), model.get("decision_provider")
        )
        or "not_attached",
        "prompt_version": prompt_version or "not_attached",
        "prompt_hash": prompt_hash or "not_attached",
        "operator_event_hash": _first_nonempty(
            operator_decision.get("operator_event_hash")
        )
        or "not_attached",
        "operator_candidate_hash": _first_nonempty(
            operator_decision.get("candidate_hash")
        )
        or "not_attached",
        "sizing_ref": _first_nonempty(sizing.get("sizing_ref")) or "not_attached",
        "sizing_plan_hash": _first_nonempty(sizing.get("sizing_plan_hash"))
        or "not_attached",
        "risk_engine_versions": risk_versions,
        "risk_engine_version": _first_nonempty(
            risk_versions.get("risk_control"),
            risk_versions.get("pre_execution_risk_gate"),
            risk_versions.get("execution_guard"),
        )
        or "not_attached",
        "dispatch_engine_version": "order_dispatch.v1",
        "market_data_source": market_data_source or "not_attached",
        "broker_symbol": broker_symbol or "not_attached",
        "broker_bridge": bridge_name or "not_attached",
        "runtime_lane": _first_nonempty(runtime_lane.get("effective_lane")) or "not_attached",
        "initiator_kind": _first_nonempty(initiator.get("kind")) or "not_attached",
        "config_hash": config_hash or "not_attached",
        "gaps": gaps,
    }


def _effective_lane(
    *,
    configured_mode: str,
    bridge_real_capable: bool | None,
    real_broker_confirmed: Any,
    demo_account_confirmed: Any,
) -> str:
    if real_broker_confirmed is True and demo_account_confirmed is True:
        return "MT5_DEMO_BROKER"
    if real_broker_confirmed is True and demo_account_confirmed is False:
        return "LIVE_REAL_BROKER"
    if real_broker_confirmed is True:
        return "BROKER_ACCOUNT_MODE_UNKNOWN"
    if configured_mode == "LIVE" and bridge_real_capable is True:
        return "LIVE_REAL_BROKER_ARMED"
    if configured_mode == "LIVE":
        return "LIVE_MODE_WITH_SIMULATED_BRIDGE"
    if bridge_real_capable is True:
        return "PAPER_MODE_WITH_REAL_CAPABLE_BRIDGE"
    return "PAPER_SIMULATED"


def _outcome_account_mode(outcome_payload: Mapping[str, Any]) -> str:
    if not bool(outcome_payload.get("is_real_broker")):
        return "SIMULATED"
    demo = outcome_payload.get("is_demo_account")
    if demo is True:
        return "DEMO"
    if demo is False:
        return "LIVE"
    return "UNKNOWN"


def _gate_outcome_for_status(status: str, *, executed: bool) -> str:
    token = str(status or "").upper()
    if not token:
        return "PENDING_RESULT"
    if executed or token in {"BROKER_EXECUTED", "BROKER_PARTIAL"}:
        return "EXECUTED"
    if token == "REJECTED_PRECHECK":
        return "REJECTED_PRECHECK"
    if token == "DUPLICATE_SUPPRESSED":
        return "BLOCKED_DUPLICATE"
    if token.startswith("BLOCKED_") or token == "OVERSEER_REJECTED":
        return "BLOCKED"
    if token == "DISPATCH_ERROR" or token.endswith("_ERROR"):
        return "ERROR"
    if token.startswith("BROKER_"):
        return "BROKER_RESPONSE"
    return "UNKNOWN"


def _terminal_stage_for_status(
    status: str,
    *,
    dispatched_to_bridge: bool,
    live_gate_report: Mapping[str, Any] | None = None,
) -> str:
    token = str(status or "").upper()
    if token == "BLOCKED_LIVE_GATE":
        live_stage = _first_nonempty(_mapping(live_gate_report).get("blocking_stage"))
        if live_stage:
            return live_stage
    mapping = {
        "REJECTED_PRECHECK": "precheck",
        "DUPLICATE_SUPPRESSED": "idempotency",
        "BLOCKED_MARKET": "market_availability",
        "BLOCKED_LIVE_GATE": "live_gate",
        "BLOCKED_EDGE_AUTHORIZATION": "edge_authorization",
        "BLOCKED_EXECUTION_QUALITY": "execution_quality",
        "BLOCKED_MACRO": "macro_blackout",
        "BLOCKED_ORDER_CONSTRAINTS": "order_constraints",
        "BLOCKED_RISK": "risk_engine",
        "OVERSEER_REJECTED": "risk_engine",
    }
    if token in mapping:
        return mapping[token]
    if token.startswith("BROKER_") or token == "DISPATCH_ERROR" or dispatched_to_bridge:
        return "broker_bridge"
    return "dispatch_loop"


def _blocked_stage_for_status(status: str, *, live_gate_report: Mapping[str, Any] | None = None) -> str | None:
    terminal_stage = _terminal_stage_for_status(
        status,
        dispatched_to_bridge=False,
        live_gate_report=live_gate_report,
    )
    outcome = _gate_outcome_for_status(status, executed=False)
    if outcome.startswith("BLOCKED") or outcome == "REJECTED_PRECHECK":
        return terminal_stage
    return None


def _bridge_touch_state(*, status: str, dispatched_to_bridge: bool, outcome_present: bool) -> str:
    if not dispatched_to_bridge:
        return "NOT_TOUCHED"
    if outcome_present:
        return "TOUCHED_CONFIRMED"
    if str(status or "").upper() == "DISPATCH_ERROR":
        return "TOUCH_UNKNOWN"
    return "TOUCHED_NO_OUTCOME"


def _bridge_real_probe(bridge: Any) -> bool | None:
    probe = getattr(bridge, "will_execute_real_order", None)
    if not callable(probe):
        return None
    try:
        return bool(probe())
    except Exception:
        return True


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_nonempty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _intent_value(intent: Optional[Mapping[str, Any]], key: str) -> Any:
    if not isinstance(intent, Mapping):
        return None
    return intent.get(key)


def _attr(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def _direction_value(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value))


def _safe_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe_json(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _safe_json(model_dump(mode="json"))
        except Exception:
            pass
    return str(value)


def _hash_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _hash_payload(payload: Any) -> str:
    blob = json.dumps(_safe_json(payload), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
