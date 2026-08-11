"""Read-only binding between WASTE direction edges and realized paper outcomes.

Direction learning is not allowed to become adaptation authority merely because
the edge gate liked a setup. This report joins WASTE PASS-token direction cycles
to paper/demo dispatch attempts and closed MT5 paper/demo history, so future
adaptation can rely on realized outcomes instead of unclosed hypotheses.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.instruments import canonical_or_normalized_symbol
from cas_forex.jsonl_tail import read_jsonl_tail
from cas_forex.mt5_deal_history_ingest import (
    DEFAULT_OUTPUT_DIR as DEFAULT_MT5_DEAL_HISTORY_DIR,
    load_latest_mt5_deal_history_ingest_report,
)
from cas_forex.order_attempt_audit import DEFAULT_STATE_PATH as DEFAULT_ORDER_ATTEMPT_STATE_PATH
from cas_forex.time_utils import utc_now
from cas_forex.waste_cycle_audit import DEFAULT_AUDIT_PATH as DEFAULT_WASTE_AUDIT_PATH

REPORT_KIND = "cas_forex_waste_direction_outcome_binding"
STATUS_NO_CONFIRMED_EDGE = "WASTE_DIRECTION_OUTCOME_NO_CONFIRMED_EDGE"
STATUS_AWAITING_EXECUTION = "WASTE_DIRECTION_OUTCOME_AWAITING_PAPER_EXECUTION"
STATUS_AWAITING_CLOSED_HISTORY = "WASTE_DIRECTION_OUTCOME_AWAITING_CLOSED_HISTORY"
STATUS_COLLECTING = "WASTE_DIRECTION_OUTCOME_COLLECTING"
STATUS_READY = "WASTE_DIRECTION_OUTCOME_READY_FOR_PROMOTION_REVIEW"
DEFAULT_MIN_BOUND_OUTCOMES_FOR_PROMOTION = 5
LEARNING_RANKING_BASIS = (
    "after_cost_expectancy_r_then_per_1_lot_then_raw_expectancy_then_net_pnl"
)
REGIME_GROUPING_BASIS = (
    "symbol_x_timeframe_x_direction_x_profile_then_market_regime"
)

CLAIM_BOUNDARY = (
    "WASTE direction outcome binding is read-only PAPER/DEMO evidence joining. "
    "It can bind PASS-token direction cycles to paper/demo order attempts and "
    "closed MT5 paper/demo outcomes, but it does not place orders, close "
    "positions, create broker ACCEPT, create owner ACCEPT, authorize live "
    "trading, mint edge tokens, lower thresholds, deposit, withdraw, move "
    "bank/card money, automate payouts, or mark evidence LICENSED."
)


def build_waste_direction_outcome_binding(
    *,
    cycles: Iterable[Mapping[str, Any]] | None = None,
    attempts: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None,
    history_report: Mapping[str, Any] | None = None,
    audit_path: Path | str = DEFAULT_WASTE_AUDIT_PATH,
    order_attempt_state_path: Path | str = DEFAULT_ORDER_ATTEMPT_STATE_PATH,
    history_report_dir: Path | str = DEFAULT_MT5_DEAL_HISTORY_DIR,
    max_cycles: int = 250,
    min_bound_outcomes_for_promotion: int = DEFAULT_MIN_BOUND_OUTCOMES_FOR_PROMOTION,
) -> dict[str, Any]:
    """Bind confirmed WASTE direction samples to realized paper/demo outcomes."""

    cycle_rows = _cycle_rows(
        list(cycles) if cycles is not None else _load_cycles(audit_path, max_cycles=max_cycles)
    )
    confirmed_cycles = [row for row in cycle_rows if row.get("edge_confirmed")]
    attempt_rows = _attempt_rows(
        attempts if attempts is not None else _load_attempts(order_attempt_state_path)
    )
    history = dict(history_report) if history_report is not None else _latest_history(history_report_dir)
    history_rows = _history_rows(history)

    attempts_by_decision = _index_by(attempt_rows, "decision_ref")
    attempts_by_order = _index_by(attempt_rows, "order_id")
    history_by_ticket = _index_by(history_rows, "broker_ticket")

    bound_rows: list[dict[str, Any]] = []
    unbound_confirmed_rows: list[dict[str, Any]] = []
    executed_confirmed = 0
    for row in confirmed_cycles:
        attempt = _matching_attempt(row, attempts_by_decision, attempts_by_order)
        ticket = _broker_ticket(row, attempt)
        history_row = history_by_ticket.get(ticket) if ticket else None
        if attempt and bool(attempt.get("executed", False)):
            executed_confirmed += 1
        if attempt and history_row and _paper_demo_history(history_row):
            bound_rows.append(_bound_row(row, attempt, history_row))
        else:
            unbound_confirmed_rows.append(
                _unbound_row(row, attempt=attempt, broker_ticket=ticket, history_row=history_row)
            )

    bound_rows = _sort_outcome_rows(bound_rows)
    net_pnl = round(sum(_float(row.get("net_pnl"), 0.0) for row in bound_rows), 6)
    profitable = [row for row in bound_rows if _float(row.get("net_pnl"), 0.0) > 0.0]
    losing = [row for row in bound_rows if _float(row.get("net_pnl"), 0.0) < 0.0]
    flat = [row for row in bound_rows if _float(row.get("net_pnl"), 0.0) == 0.0]
    min_bound = max(1, int(min_bound_outcomes_for_promotion))
    group_stats = _outcome_group_stats(bound_rows, min_samples=min_bound)
    sample_ready_groups = [group for group in group_stats if group["sample_ready"]]
    risk_incomplete_sample_ready_groups = [
        group
        for group in sample_ready_groups
        if not bool(group.get("risk_normalized_evidence_complete", False))
    ]
    outcome_ready_groups = [
        group for group in group_stats if group["outcome_ready_for_promotion"]
    ]
    regime_attributed_bound_count = sum(
        1 for row in bound_rows if _regime_key(row.get("market_regime")) != "UNKNOWN"
    )
    recommended_growth_group = (
        _rank_growth_groups(outcome_ready_groups)[0] if outcome_ready_groups else None
    )
    max_group_count = max(
        (int(group.get("trades") or 0) for group in group_stats),
        default=0,
    )
    bound_outcomes_needed = max(0, min_bound - max_group_count)
    outcome_ready = bool(outcome_ready_groups)
    status = _status(
        confirmed_count=len(confirmed_cycles),
        executed_count=executed_confirmed,
        history_count=len(history_rows),
        bound_count=len(bound_rows),
        outcome_ready=outcome_ready,
    )

    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "read_only": True,
        "dry_run": True,
        "paper_only": True,
        "outcome_ready_for_promotion": outcome_ready,
        "min_bound_outcomes_for_promotion": min_bound,
        "grouping_basis": "symbol_x_timeframe_x_direction_x_profile",
        "regime_grouping_basis": REGIME_GROUPING_BASIS,
        "ranking_basis": LEARNING_RANKING_BASIS,
        "risk_normalized_ranking_required_for_promotion": True,
        "pooled_profit_cannot_promote_group": True,
        "pooled_profit_cannot_promote_across_regimes": True,
        "direction_rows": len(cycle_rows),
        "confirmed_direction_count": len(confirmed_cycles),
        "executed_confirmed_count": executed_confirmed,
        "closed_history_count": len(history_rows),
        "bound_outcome_count": len(bound_rows),
        "unbound_confirmed_count": len(unbound_confirmed_rows),
        "bound_outcomes_needed": bound_outcomes_needed,
        "sample_ready_group_count": len(sample_ready_groups),
        "risk_incomplete_sample_ready_group_count": len(
            risk_incomplete_sample_ready_groups
        ),
        "outcome_ready_group_count": len(outcome_ready_groups),
        "regime_attributed_bound_count": regime_attributed_bound_count,
        "unknown_regime_bound_count": len(bound_rows)
        - regime_attributed_bound_count,
        "group_stats": group_stats,
        "recommended_growth_group": recommended_growth_group,
        "profitable_bound_count": len(profitable),
        "losing_bound_count": len(losing),
        "flat_bound_count": len(flat),
        "net_paper_pnl": net_pnl,
        "avg_bound_pnl": round(net_pnl / len(bound_rows), 6) if bound_rows else 0.0,
        "direction_counts": dict(Counter(str(row.get("direction") or "UNKNOWN") for row in bound_rows)),
        "profile_counts": dict(Counter(str(row.get("profile") or "UNKNOWN") for row in bound_rows)),
        "regime_counts": dict(
            Counter(_regime_key(row.get("market_regime")) for row in bound_rows)
        ),
        "paper_demo_history_status": history.get("ingest_status"),
        "history_account_mode": history.get("account_mode"),
        "history_report_path": history.get("report_path"),
        "runtime_changed": False,
        "runtime_change_attempted": False,
        "would_apply_runtime_change": False,
        "would_lower_edge_threshold": False,
        "would_enable_live_trading": False,
        "would_raise_risk": False,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "money_moved": False,
        "bound_rows": bound_rows[-10:],
        "unbound_confirmed_rows": unbound_confirmed_rows[-10:],
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(
            status,
            len(bound_rows),
            bound_outcomes_needed,
            sample_ready_group_count=len(sample_ready_groups),
            outcome_ready_group_count=len(outcome_ready_groups),
            risk_incomplete_sample_ready_group_count=len(
                risk_incomplete_sample_ready_groups
            ),
        ),
    }


def _load_cycles(audit_path: Path | str, *, max_cycles: int) -> list[dict[str, Any]]:
    return read_jsonl_tail(audit_path, limit=max_cycles)


def _load_attempts(state_path: Path | str) -> list[dict[str, Any]]:
    path = Path(state_path)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    attempts = payload.get("attempts") if isinstance(payload, Mapping) else {}
    if not isinstance(attempts, Mapping):
        return []
    return [dict(row) for row in attempts.values() if isinstance(row, Mapping)]


def _latest_history(report_dir: Path | str) -> dict[str, Any]:
    try:
        return load_latest_mt5_deal_history_ingest_report(report_dir)
    except Exception as exc:
        return {
            "report_kind": "cas_forex_mt5_deal_history_ingest_report",
            "ingest_status": "UNAVAILABLE",
            "error": f"{type(exc).__name__}: {exc}",
            "history_records": [],
        }


def _cycle_rows(cycles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cycle in cycles:
        candidate = _mapping(cycle.get("candidate"))
        edge = _mapping(cycle.get("edge"))
        direction = _direction(candidate.get("direction"))
        decision_ref = str(candidate.get("decision_ref") or "")
        if direction not in {"LONG", "SHORT"} or not decision_ref:
            continue
        rows.append(
            {
                "cycle_id": cycle.get("cycle_id"),
                "generated_at": cycle.get("generated_at"),
                "decision": cycle.get("decision"),
                "symbol": candidate.get("symbol"),
                "timeframe": candidate.get("timeframe"),
                "direction": direction,
                "profile": _profile(candidate),
                "market_regime": candidate.get("regime")
                or _mapping(candidate.get("directional_hypothesis")).get("regime"),
                "market_regime_source": "waste_cycle_candidate",
                "decision_ref": decision_ref,
                "order_id": f"waste-{decision_ref}",
                "edge_status": edge.get("status"),
                "edge_confirmed": edge.get("status") == "PASS" and bool(edge.get("has_edge_token", False)),
                "measured_win_prob": edge.get("measured_win_prob"),
                "threshold": edge.get("threshold"),
                "execute_result": _mapping(cycle.get("execute_result")),
                "origin_source": "WASTE_CYCLE_AUDIT",
            }
        )
    return rows


def _learning_attempt_origin_rows(
    attempts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Project AI paper/demo executions into learning origins.

    Fresh live-candle candidates are dispatched directly as RouteIntent objects,
    so they do not necessarily have a legacy WASTE-cycle audit row. The finalized
    order-attempt record is still a durable, exact identity bridge from the AI
    decision reference to the broker position ticket.
    """

    rows: list[dict[str, Any]] = []
    for attempt in attempts:
        if not bool(attempt.get("executed")):
            continue
        mode = str(attempt.get("mode") or "").upper()
        if mode not in {"PAPER", "DEMO", "PAPER_FALLBACK"}:
            continue
        provenance = _mapping(attempt.get("execution_provenance"))
        initiator = _mapping(provenance.get("initiator"))
        strategy = _mapping(provenance.get("strategy"))
        order_shape = _mapping(provenance.get("order_shape"))
        proposed = _mapping(attempt.get("proposed_intent"))
        decision_ref = str(
            attempt.get("decision_ref")
            or order_shape.get("decision_ref")
            or ""
        ).strip()
        order_id = str(attempt.get("order_id") or order_shape.get("order_id") or "").strip()
        ai_action = str(strategy.get("ai_action") or initiator.get("ai_action") or "").strip()
        initiator_kind = str(initiator.get("kind") or "").upper()
        if not decision_ref or not order_id:
            continue
        if (
            initiator_kind != "AI_AUTOMATION"
            and not ai_action
            and not decision_ref.startswith("waste-dir-")
        ):
            continue
        direction = _direction(attempt.get("direction") or order_shape.get("direction"))
        if direction not in {"LONG", "SHORT"}:
            continue
        strategy_id = str(strategy.get("strategy_id") or "").strip() or None
        timeframe = proposed.get("timeframe") or strategy.get("timeframe")
        if not timeframe and strategy_id:
            suffix = strategy_id.rsplit("_", 1)[-1].upper()
            timeframe = suffix if suffix in {"M1", "M5", "M15", "M30", "H1", "H4", "D1"} else None
        edge = _mapping(proposed.get("edge_label") or proposed.get("edge"))
        rows.append(
            {
                "cycle_id": attempt.get("attempt_id") or order_id,
                "attempt_id": attempt.get("attempt_id"),
                "generated_at": attempt.get("created_at") or attempt.get("updated_at"),
                "decision": "EXECUTED_AI_ORDER_ATTEMPT",
                "symbol": attempt.get("symbol") or order_shape.get("symbol"),
                "timeframe": timeframe,
                "direction": direction,
                "profile": proposed.get("profile") or strategy_id,
                "strategy_id": strategy_id,
                "ai_action": ai_action or None,
                "market_regime": proposed.get("market_regime")
                or strategy.get("market_regime"),
                "market_regime_source": proposed.get("market_regime_source")
                or strategy.get("market_regime_source"),
                "decision_ref": decision_ref,
                "order_id": order_id,
                "edge_status": edge.get("status") or "EDGE_STATUS_NOT_ATTACHED_TO_ATTEMPT",
                "edge_confirmed": edge.get("status") == "PASS" and bool(edge.get("has_edge_token")),
                "measured_win_prob": edge.get("measured_win_prob"),
                "threshold": edge.get("threshold"),
                "execute_result": _mapping(attempt.get("result")),
                "origin_source": "ORDER_ATTEMPT_LEDGER",
            }
        )
    return rows


def _merge_learning_origin_rows(
    cycle_rows: Sequence[Mapping[str, Any]],
    attempt_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    merged = [dict(row) for row in cycle_rows]
    seen_decisions = {str(row.get("decision_ref") or "") for row in merged}
    seen_orders = {str(row.get("order_id") or "") for row in merged}
    for row in _learning_attempt_origin_rows(attempt_rows):
        decision_ref = str(row.get("decision_ref") or "")
        order_id = str(row.get("order_id") or "")
        if decision_ref in seen_decisions or order_id in seen_orders:
            continue
        merged.append(row)
        seen_decisions.add(decision_ref)
        seen_orders.add(order_id)
    return merged


def _attempt_rows(raw: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    values = raw.values() if isinstance(raw, Mapping) else raw
    return [dict(row) for row in values if isinstance(row, Mapping)]


def _history_rows(history_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = history_report.get("history_records") if isinstance(history_report.get("history_records"), list) else []
    return [dict(row) for row in rows if isinstance(row, Mapping) and _paper_demo_history(row)]


def _matching_attempt(
    cycle: Mapping[str, Any],
    attempts_by_decision: Mapping[str, Mapping[str, Any]],
    attempts_by_order: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    decision_ref = str(cycle.get("decision_ref") or "")
    order_id = str(cycle.get("order_id") or "")
    attempt = attempts_by_decision.get(decision_ref) or attempts_by_order.get(order_id)
    return dict(attempt) if isinstance(attempt, Mapping) else None


def _bound_row(cycle: Mapping[str, Any], attempt: Mapping[str, Any], history: Mapping[str, Any]) -> dict[str, Any]:
    net_pnl = _float(history.get("profit"), 0.0)
    proposed = _mapping(attempt.get("proposed_intent"))
    provenance = _mapping(attempt.get("execution_provenance"))
    order_shape = _mapping(provenance.get("order_shape"))
    lot_size = _first_positive(
        history.get("volume"),
        history.get("lot_size"),
        attempt.get("volume"),
        attempt.get("lots"),
        proposed.get("lots"),
        proposed.get("volume"),
        order_shape.get("volume"),
    )
    admission_risk = _admission_risk_evidence(
        attempt,
        history=history,
        lot_size=lot_size,
    )
    admission_stop_risk_usd = admission_risk.get("admission_stop_risk_usd")
    return {
        "binding_id": stable_ledger_id(
            "waste-direction-outcome",
            cycle.get("cycle_id"),
            cycle.get("decision_ref"),
            history.get("broker_ticket") or history.get("ticket"),
            net_pnl,
        ),
        "cycle_id": cycle.get("cycle_id"),
        "decision_ref": cycle.get("decision_ref"),
        "order_id": attempt.get("order_id") or cycle.get("order_id"),
        "broker_ticket": history.get("broker_ticket") or history.get("ticket"),
        "symbol": cycle.get("symbol") or history.get("symbol"),
        "timeframe": cycle.get("timeframe"),
        "direction": cycle.get("direction"),
        "history_direction": _direction(history.get("direction")),
        "direction_matches_history": _direction(history.get("direction")) in {None, cycle.get("direction")},
        "profile": cycle.get("profile"),
        "strategy_id": cycle.get("strategy_id"),
        "ai_action": cycle.get("ai_action"),
        "market_regime": cycle.get("market_regime"),
        "market_regime_source": cycle.get("market_regime_source"),
        "origin_source": cycle.get("origin_source"),
        "attempt_id": attempt.get("attempt_id") or cycle.get("attempt_id"),
        "edge_status": cycle.get("edge_status"),
        "attempt_status": attempt.get("status"),
        "attempt_mode": attempt.get("mode"),
        "history_broker_mode": history.get("broker_mode"),
        "lot_size": lot_size,
        "net_pnl": net_pnl,
        "net_pnl_per_1_lot_usd": (
            round(net_pnl / lot_size, 6) if lot_size is not None else None
        ),
        **admission_risk,
        "realized_after_cost_r_multiple": (
            round(net_pnl / float(admission_stop_risk_usd), 6)
            if admission_stop_risk_usd is not None
            and float(admission_stop_risk_usd) > 0.0
            else None
        ),
        "gross_profit": _float(history.get("gross_profit"), 0.0),
        "commission": _float(history.get("commission"), 0.0),
        "swap": _float(history.get("swap"), 0.0),
        "close_reason": history.get("close_reason"),
        "open_time": history.get("open_time"),
        "close_time": history.get("close_time"),
        "paper_demo_only": True,
    }


def _admission_risk_evidence(
    attempt: Mapping[str, Any],
    *,
    history: Mapping[str, Any] | None = None,
    lot_size: float | None,
) -> dict[str, Any]:
    """Rebuild planned stop risk from broker contract geometry when possible.

    Older attempt rows may contain a stored risk estimate produced before the
    MT5 tick-value/tick-size conversion was corrected. Immutable entry, stop,
    volume, and broker contract fields let learning recover the comparable
    admission risk without rewriting the original receipt.
    """

    result = _mapping(attempt.get("result"))
    estimate = _mapping(attempt.get("pre_trade_estimate"))
    if not estimate:
        estimate = _mapping(result.get("pre_trade_estimate"))
    proposed = _mapping(attempt.get("proposed_intent"))
    order = _mapping(attempt.get("order"))
    outcome = _mapping(attempt.get("outcome"))
    provenance = _mapping(attempt.get("execution_provenance"))
    order_shape = _mapping(provenance.get("order_shape"))
    constraints = _mapping(estimate.get("broker_contract_constraints"))
    broker_history = _mapping(history)

    lots = _first_positive(
        lot_size,
        estimate.get("lots"),
        attempt.get("volume"),
        proposed.get("lots"),
        order.get("volume"),
        order_shape.get("volume"),
    )
    entry = _first_positive(
        estimate.get("entry_price"),
        outcome.get("filled_price"),
        proposed.get("entry_price"),
        order.get("price"),
        order_shape.get("price"),
    )
    stop = _first_positive(
        estimate.get("stop_loss"),
        proposed.get("stop_loss"),
        order.get("stop_loss"),
        order.get("sl"),
        order_shape.get("stop_loss"),
    )
    tick_size = _first_positive(constraints.get("tick_size"))
    tick_value_loss = _first_positive(
        constraints.get("tick_value_loss"),
        constraints.get("tick_value"),
    )
    recomputed = None
    if (
        lots is not None
        and entry is not None
        and stop is not None
        and tick_size is not None
        and tick_value_loss is not None
    ):
        distance = abs(float(entry) - float(stop))
        if distance > 0.0:
            recomputed = round(
                (distance / float(tick_size))
                * float(tick_value_loss)
                * float(lots),
                6,
            )

    exact_stop_fill = _exact_mt5_stop_fill_risk(
        broker_history,
        intended_stop=stop,
        lots=lots,
    )
    exact_stop_fill_risk = exact_stop_fill.get("risk_usd")

    stored = _first_positive(estimate.get("risk_at_stop_usd"))
    broker_unit = _first_positive(estimate.get("broker_unit_value_per_lot_usd"))
    source_text = " ".join(
        str(value or "")
        for value in (
            estimate.get("unit_value_source"),
            estimate.get("risk_source"),
        )
    ).lower()
    stored_is_broker_valued = broker_unit is not None or "broker.trade_tick_value" in source_text

    trusted_candidates: list[tuple[float, str]] = []
    if recomputed is not None and recomputed > 0.0:
        trusted_candidates.append((recomputed, "RECOMPUTED_BROKER_TICK_CONTRACT"))
    if exact_stop_fill_risk is not None and exact_stop_fill_risk > 0.0:
        trusted_candidates.append(
            (exact_stop_fill_risk, "RECONSTRUCTED_EXACT_MT5_STOP_LOSS_FILL")
        )
    if stored is not None and stored_is_broker_valued:
        trusted_candidates.append((stored, "STORED_BROKER_VALUED_ESTIMATE"))
    admission_stop_risk_usd = (
        max(value for value, _source in trusted_candidates)
        if trusted_candidates
        else None
    )
    selected_sources = [
        source
        for value, source in trusted_candidates
        if admission_stop_risk_usd is not None and value == admission_stop_risk_usd
    ]
    exact_stop_fill_selected = (
        "RECONSTRUCTED_EXACT_MT5_STOP_LOSS_FILL" in selected_sources
    )
    legacy_missing_risk_repaired = bool(
        exact_stop_fill_selected
        and recomputed is None
        and not stored_is_broker_valued
    )
    ratio = (
        round(float(stored) / float(recomputed), 6)
        if stored is not None and recomputed is not None and recomputed > 0.0
        else None
    )
    mismatch = bool(ratio is not None and abs(float(ratio) - 1.0) > 0.05)
    return {
        "admission_stop_risk_usd": (
            round(float(admission_stop_risk_usd), 6)
            if admission_stop_risk_usd is not None
            else None
        ),
        "admission_risk_source": "+".join(selected_sources) or None,
        "admission_risk_evidence_complete": admission_stop_risk_usd is not None,
        "risk_recomputed_from_broker_contract": recomputed is not None,
        "recomputed_broker_stop_risk_usd": recomputed,
        "exact_mt5_stop_fill_observed": bool(
            exact_stop_fill.get("evidence_complete", False)
        ),
        "risk_reconstructed_from_exact_mt5_stop_fill": exact_stop_fill_selected,
        "legacy_missing_admission_risk_repaired_from_exact_mt5_stop_fill": (
            legacy_missing_risk_repaired
        ),
        "reconstructed_exact_mt5_stop_risk_usd": exact_stop_fill_risk,
        "exact_mt5_stop_fill_evidence": exact_stop_fill,
        "stored_pre_trade_risk_usd": stored,
        "stored_pre_trade_risk_was_broker_valued": stored_is_broker_valued,
        "stored_pre_trade_risk_ratio_to_recomputed": ratio,
        "stored_pre_trade_risk_mismatch_detected": mismatch,
        "admission_risk_contract": {
            "entry_price": entry,
            "stop_loss": stop,
            "lot_size": lots,
            "tick_size": tick_size,
            "tick_value_loss": tick_value_loss,
        },
    }


def _exact_mt5_stop_fill_risk(
    history: Mapping[str, Any],
    *,
    intended_stop: float | None,
    lots: float | None,
) -> dict[str, Any]:
    """Recover admission risk only from an exact broker-side MT5 stop fill."""

    broker_mode = str(history.get("broker_mode") or "").strip().upper()
    close_reason = str(
        history.get("close_reason") or history.get("comment") or ""
    ).strip()
    reason_upper = close_reason.upper()
    broker_open = _first_positive(
        history.get("open_price"),
        history.get("entry_price"),
    )
    broker_close = _first_positive(history.get("close_price"))
    stop = _first_positive(intended_stop)
    volume = _first_positive(lots)
    try:
        gross_profit = float(history.get("gross_profit"))
    except (TypeError, ValueError):
        gross_profit = 0.0
    direction = _direction(history.get("direction"))
    stop_reason = (
        "[SL" in reason_upper
        or "STOP_LOSS" in reason_upper
        or "STOP LOSS" in reason_upper
    )
    close_matches_stop = bool(
        broker_close is not None
        and stop is not None
        and _same_price(broker_close, stop)
    )
    direction_geometry_valid = bool(
        broker_open is not None
        and stop is not None
        and (
            (direction == "LONG" and stop < broker_open)
            or (direction == "SHORT" and stop > broker_open)
        )
    )
    evidence_complete = bool(
        "MT5" in broker_mode
        and stop_reason
        and close_matches_stop
        and direction_geometry_valid
        and volume is not None
        and gross_profit < 0.0
    )
    risk_usd = round(abs(gross_profit), 6) if evidence_complete else None
    implied_cash_value_per_price_per_lot = None
    if evidence_complete and broker_open is not None and stop is not None and volume:
        distance = abs(float(broker_open) - float(stop))
        if distance > 0.0:
            implied_cash_value_per_price_per_lot = round(
                float(risk_usd) / distance / float(volume),
                6,
            )
    return {
        "evidence_complete": evidence_complete,
        "broker_mode": broker_mode or None,
        "broker_open_price": broker_open,
        "broker_close_price": broker_close,
        "intended_stop_loss": stop,
        "executed_lots": volume,
        "gross_profit_usd": round(gross_profit, 6),
        "close_reason": close_reason or None,
        "stop_reason_confirmed": stop_reason,
        "close_matches_intended_stop": close_matches_stop,
        "direction_geometry_valid": direction_geometry_valid,
        "implied_cash_value_per_price_per_lot": (
            implied_cash_value_per_price_per_lot
        ),
        "risk_usd": risk_usd,
    }


def _same_price(left: float, right: float) -> bool:
    tolerance = max(1e-8, abs(float(right)) * 1e-10)
    return abs(float(left) - float(right)) <= tolerance


def _unbound_row(
    cycle: Mapping[str, Any],
    *,
    attempt: Mapping[str, Any] | None,
    broker_ticket: str | None,
    history_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not attempt:
        missing = "paper_order_attempt"
    elif not bool(attempt.get("executed", False)):
        missing = "executed_paper_attempt"
    elif not broker_ticket:
        missing = "broker_ticket"
    elif not history_row:
        missing = "closed_mt5_paper_history"
    else:
        missing = "paper_demo_closed_history"
    return {
        "cycle_id": cycle.get("cycle_id"),
        "decision_ref": cycle.get("decision_ref"),
        "order_id": cycle.get("order_id"),
        "symbol": cycle.get("symbol"),
        "timeframe": cycle.get("timeframe"),
        "direction": cycle.get("direction"),
        "profile": cycle.get("profile"),
        "edge_status": cycle.get("edge_status"),
        "attempt_status": attempt.get("status") if attempt else None,
        "attempt_executed": bool(attempt.get("executed", False)) if attempt else False,
        "broker_ticket": broker_ticket,
        "missing": missing,
    }


def _index_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if value:
            index[value] = dict(row)
    return index


def _broker_ticket(cycle: Mapping[str, Any], attempt: Mapping[str, Any] | None) -> str | None:
    candidates: list[Any] = []
    if attempt:
        outcome = _mapping(attempt.get("outcome"))
        result = _mapping(attempt.get("result"))
        candidates.extend(
            (
                outcome.get("broker_ticket"),
                result.get("broker_ticket"),
                result.get("ticket"),
            )
        )
    execute = _mapping(cycle.get("execute_result"))
    outcome = _mapping(execute.get("outcome"))
    candidates.extend((execute.get("broker_ticket"), execute.get("ticket"), outcome.get("broker_ticket")))
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return None


def _paper_demo_history(row: Mapping[str, Any]) -> bool:
    mode = str(row.get("broker_mode") or "").upper()
    return bool(row.get("broker_ticket") or row.get("ticket")) and ("PAPER" in mode or "DEMO" in mode) and "LIVE" not in mode


def _profile(candidate: Mapping[str, Any]) -> str | None:
    hypothesis = _mapping(candidate.get("directional_hypothesis"))
    meta = _mapping(candidate.get("market_state_meta"))
    cas_map = _mapping(meta.get("cas_feature_map"))
    value = hypothesis.get("profile") or cas_map.get("selected_profile")
    return str(value) if value else None


def _status(
    *,
    confirmed_count: int,
    executed_count: int,
    history_count: int,
    bound_count: int,
    outcome_ready: bool,
) -> str:
    if confirmed_count <= 0:
        return STATUS_NO_CONFIRMED_EDGE
    if executed_count <= 0:
        return STATUS_AWAITING_EXECUTION
    if history_count <= 0 or bound_count <= 0:
        return STATUS_AWAITING_CLOSED_HISTORY
    if outcome_ready:
        return STATUS_READY
    return STATUS_COLLECTING


def _next_action(
    status: str,
    bound_count: int,
    needed: int,
    *,
    sample_ready_group_count: int = 0,
    outcome_ready_group_count: int = 0,
    risk_incomplete_sample_ready_group_count: int = 0,
) -> str:
    if status == STATUS_NO_CONFIRMED_EDGE:
        return "Let WASTE keep running in PAPER until a LONG/SHORT setup earns a PASS edge token."
    if status == STATUS_AWAITING_EXECUTION:
        return "A PASS-token direction exists, but no matching paper/demo execution attempt is finalized yet."
    if status == STATUS_AWAITING_CLOSED_HISTORY:
        return "Run MT5 paper/demo deal-history ingest after the matched paper position closes."
    if status == STATUS_READY:
        return (
            "An exact symbol x timeframe x direction x profile group has enough "
            "after-cost profitable outcomes for review; all live gates remain separate."
        )
    if sample_ready_group_count > 0 and outcome_ready_group_count <= 0:
        if risk_incomplete_sample_ready_group_count > 0:
            return (
                "At least one exact behavior group has enough samples, but its "
                "broker-valued admission stop-risk evidence is incomplete. It may "
                "inform bounded PAPER exploration, but cannot be promoted or justify "
                "pressing size until comparable after-cost R evidence is complete."
            )
        return (
            "At least one exact behavior group has enough samples, but none has "
            "positive after-cost expectancy and net P&L. Do not promote a high "
            "win-rate or pooled-profit proxy; collect materially differentiated outcomes."
        )
    return (
        f"Collect {needed} more bound closed paper/demo outcome(s) inside one exact "
        f"symbol x timeframe x direction x profile group; {bound_count} total are bound."
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _direction(value: Any) -> str | None:
    text = str(value or "").upper()
    if text in {"LONG", "BUY"}:
        return "LONG"
    if text in {"SHORT", "SELL"}:
        return "SHORT"
    return None


def _symbol_key(value: Any) -> str:
    return canonical_or_normalized_symbol(value)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return round(float(default), 6)


def _first_positive(*values: Any) -> float | None:
    for value in values:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0.0:
            return round(parsed, 8)
    return None


LEARNING_REPORT_KIND = "cas_forex_waste_learning_outcomes"

LEARNING_CLAIM_BOUNDARY = (
    "WASTE learning outcomes is read-only PAPER/DEMO analysis binding EVERY "
    "closed paper trade (edge-passing or not) to its originating direction so the "
    "AI can learn from realized wins and losses. It does not place orders, close "
    "positions, create owner/broker ACCEPT, authorize live trading, mint edge "
    "tokens, or move money. Realized paper stats never auto-promote to real money "
    "— that path still requires a PASS edge token and the owner's live gates."
)


def _learning_agg(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    values = [_float(row.get("net_pnl"), 0.0) for row in rows]
    winning_values = [value for value in values if value > 0.0]
    losing_values = [value for value in values if value < 0.0]
    wins = len(winning_values)
    losses = len(losing_values)
    flat = n - wins - losses
    net = round(sum(values), 4)
    gross_profit = round(sum(winning_values), 4)
    gross_loss = round(sum(losing_values), 4)
    if gross_loss < 0.0:
        profit_factor = round(gross_profit / abs(gross_loss), 4)
        profit_factor_state = "FINITE"
    elif gross_profit > 0.0:
        profit_factor = None
        profit_factor_state = "NO_LOSSES"
    else:
        profit_factor = None
        profit_factor_state = "NO_GROSS_PROFIT"
    expectancy = round(net / n, 4) if n else 0.0
    normalized_values = [
        float(value)
        for value in (row.get("net_pnl_per_1_lot_usd") for row in rows)
        if value is not None
    ]
    normalized_expectancy = (
        round(sum(normalized_values) / len(normalized_values), 4)
        if normalized_values
        else None
    )
    risk_normalized_values = [
        float(value)
        for value in (row.get("realized_after_cost_r_multiple") for row in rows)
        if value is not None
    ]
    risk_normalized_expectancy = (
        round(sum(risk_normalized_values) / len(risk_normalized_values), 6)
        if risk_normalized_values
        else None
    )
    known_admission_risks = [
        float(value)
        for value in (row.get("admission_stop_risk_usd") for row in rows)
        if value is not None and float(value) > 0.0
    ]
    total_admission_risk = round(sum(known_admission_risks), 6)
    known_lots = [
        float(value)
        for value in (row.get("lot_size") for row in rows)
        if value is not None and float(value) > 0.0
    ]
    exact_stop_fill_rows = [
        row
        for row in rows
        if bool(row.get("risk_reconstructed_from_exact_mt5_stop_fill"))
    ]
    exact_stop_fill_tickets = sorted(
        {
            str(row.get("broker_ticket"))
            for row in exact_stop_fill_rows
            if row.get("broker_ticket") not in (None, "")
        }
    )
    legacy_exact_stop_repair_rows = [
        row
        for row in rows
        if bool(
            row.get(
                "legacy_missing_admission_risk_repaired_from_exact_mt5_stop_fill"
            )
        )
    ]
    legacy_exact_stop_repair_tickets = sorted(
        {
            str(row.get("broker_ticket"))
            for row in legacy_exact_stop_repair_rows
            if row.get("broker_ticket") not in (None, "")
        }
    )
    return {
        "trades": n,
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "win_rate": round(wins / n, 3) if n else 0.0,
        "net_pnl": net,
        "avg_pnl": expectancy,
        "after_cost_expectancy": expectancy,
        "after_cost_expectancy_r": risk_normalized_expectancy,
        "risk_normalized_trade_count": len(risk_normalized_values),
        "risk_normalized_evidence_complete": (
            len(risk_normalized_values) == n and n > 0
        ),
        "total_admission_stop_risk_usd": total_admission_risk,
        "net_pnl_per_dollar_admission_risk": (
            round(net / total_admission_risk, 6)
            if total_admission_risk > 0.0
            else None
        ),
        "stored_pre_trade_risk_mismatch_count": sum(
            1 for row in rows if bool(row.get("stored_pre_trade_risk_mismatch_detected"))
        ),
        "exact_mt5_stop_fill_risk_reconstruction_count": len(exact_stop_fill_rows),
        "exact_mt5_stop_fill_risk_reconstruction_tickets": exact_stop_fill_tickets,
        "legacy_exact_mt5_stop_fill_risk_repair_count": len(
            legacy_exact_stop_repair_rows
        ),
        "legacy_exact_mt5_stop_fill_risk_repair_tickets": (
            legacy_exact_stop_repair_tickets
        ),
        "after_cost_expectancy_per_1_lot_usd": normalized_expectancy,
        "lot_normalized_trade_count": len(normalized_values),
        "lot_normalized_evidence_complete": len(normalized_values) == n and n > 0,
        "total_executed_lots": round(sum(known_lots), 8),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "profit_factor_state": profit_factor_state,
        "average_win": round(gross_profit / wins, 4) if wins else 0.0,
        "average_loss": round(gross_loss / losses, 4) if losses else 0.0,
    }


def _aggregate_growth_positive(aggregate: Mapping[str, Any]) -> bool:
    risk_expectancy = aggregate.get("after_cost_expectancy_r")
    risk_complete = bool(
        aggregate.get("risk_normalized_evidence_complete", False)
    )
    normalized = aggregate.get("after_cost_expectancy_per_1_lot_usd")
    return bool(
        int(aggregate.get("trades") or 0) > 0
        and float(aggregate.get("net_pnl") or 0.0) > 0.0
        and float(aggregate.get("after_cost_expectancy") or 0.0) > 0.0
        and risk_complete
        and risk_expectancy is not None
        and float(risk_expectancy) > 0.0
        and (normalized is None or float(normalized) > 0.0)
    )


def _group_growth_robustness(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Measure whether one unusually good outcome carries the whole edge claim."""

    ordered = _sort_outcome_rows(rows)
    if not ordered:
        return {
            "largest_positive_outcome_pnl": None,
            "largest_positive_outcome_r": None,
            "largest_win_share_of_gross_profit": None,
            "leave_one_best_out_trades": 0,
            "leave_one_best_out_net_pnl": 0.0,
            "leave_one_best_out_after_cost_expectancy": 0.0,
            "leave_one_best_out_after_cost_expectancy_r": None,
            "leave_one_best_out_after_cost_expectancy_per_1_lot_usd": None,
            "leave_one_best_out_growth_positive_after_costs": False,
            "leave_one_best_out_removed_broker_ticket": None,
            "recent_window_trade_count": 0,
            "recent_window_net_pnl": 0.0,
            "recent_window_after_cost_expectancy_r": None,
            "recent_consecutive_losses": 0,
        }

    def best_outcome_key(row: Mapping[str, Any]) -> tuple[int, float, float]:
        risk_value = row.get("realized_after_cost_r_multiple")
        if risk_value is not None:
            return (2, _float(risk_value, 0.0), _float(row.get("net_pnl"), 0.0))
        normalized_value = row.get("net_pnl_per_1_lot_usd")
        if normalized_value is not None:
            return (
                1,
                _float(normalized_value, 0.0),
                _float(row.get("net_pnl"), 0.0),
            )
        net_value = _float(row.get("net_pnl"), 0.0)
        return (0, net_value, net_value)

    best_index = max(range(len(ordered)), key=lambda index: best_outcome_key(ordered[index]))
    removed = ordered[best_index]
    remainder = ordered[:best_index] + ordered[best_index + 1 :]
    remainder_aggregate = _learning_agg(remainder)
    recent = ordered[-min(5, len(ordered)) :]
    recent_aggregate = _learning_agg(recent)
    consecutive_losses = 0
    for row in reversed(ordered):
        if _float(row.get("net_pnl"), 0.0) >= 0.0:
            break
        consecutive_losses += 1

    positive_pnl = [
        _float(row.get("net_pnl"), 0.0)
        for row in ordered
        if _float(row.get("net_pnl"), 0.0) > 0.0
    ]
    positive_r = [
        _float(row.get("realized_after_cost_r_multiple"), 0.0)
        for row in ordered
        if row.get("realized_after_cost_r_multiple") is not None
        and _float(row.get("realized_after_cost_r_multiple"), 0.0) > 0.0
    ]
    gross_profit = sum(positive_pnl)
    largest_win = max(positive_pnl) if positive_pnl else None
    return {
        "largest_positive_outcome_pnl": (
            round(largest_win, 4) if largest_win is not None else None
        ),
        "largest_positive_outcome_r": (
            round(max(positive_r), 6) if positive_r else None
        ),
        "largest_win_share_of_gross_profit": (
            round(largest_win / gross_profit, 6)
            if largest_win is not None and gross_profit > 0.0
            else None
        ),
        "leave_one_best_out_trades": int(remainder_aggregate.get("trades") or 0),
        "leave_one_best_out_net_pnl": remainder_aggregate.get("net_pnl"),
        "leave_one_best_out_after_cost_expectancy": remainder_aggregate.get(
            "after_cost_expectancy"
        ),
        "leave_one_best_out_after_cost_expectancy_r": remainder_aggregate.get(
            "after_cost_expectancy_r"
        ),
        "leave_one_best_out_after_cost_expectancy_per_1_lot_usd": (
            remainder_aggregate.get("after_cost_expectancy_per_1_lot_usd")
        ),
        "leave_one_best_out_growth_positive_after_costs": (
            _aggregate_growth_positive(remainder_aggregate)
        ),
        "leave_one_best_out_removed_broker_ticket": removed.get("broker_ticket"),
        "recent_window_trade_count": int(recent_aggregate.get("trades") or 0),
        "recent_window_net_pnl": recent_aggregate.get("net_pnl"),
        "recent_window_after_cost_expectancy_r": recent_aggregate.get(
            "after_cost_expectancy_r"
        ),
        "recent_consecutive_losses": consecutive_losses,
    }


def _outcome_group_stats(
    rows: Sequence[Mapping[str, Any]],
    *,
    min_samples: int,
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for raw in rows:
        row = dict(raw)
        key = (
            _symbol_key(row.get("symbol")),
            str(row.get("timeframe") or "UNKNOWN").strip().upper(),
            _direction(row.get("direction")) or "UNKNOWN",
            str(row.get("profile") or row.get("strategy_id") or "UNKNOWN").strip(),
        )
        groups.setdefault(key, []).append(row)
    threshold = max(1, int(min_samples))
    stats: list[dict[str, Any]] = []
    for (symbol, timeframe, direction, profile), group_rows in groups.items():
        ordered = _sort_outcome_rows(group_rows)
        observed_symbols = sorted(
            {
                str(row.get("symbol") or "").strip()
                for row in ordered
                if str(row.get("symbol") or "").strip()
            }
        )
        aggregate = _learning_agg(ordered)
        robustness = _group_growth_robustness(ordered)
        regime_breakdown = _regime_group_breakdown(
            ordered,
            min_samples=threshold,
        )
        known_regime_trade_count = sum(
            int(row.get("trades") or 0)
            for row in regime_breakdown
            if bool(row.get("known_market_regime"))
        )
        regime_outcome_ready = any(
            bool(row.get("outcome_ready_for_promotion"))
            for row in regime_breakdown
        )
        sample_ready = aggregate["trades"] >= threshold
        risk_expectancy = aggregate.get("after_cost_expectancy_r")
        risk_evidence_complete = bool(
            aggregate.get("risk_normalized_evidence_complete", False)
        )
        risk_normalized_growth_positive = bool(
            risk_evidence_complete
            and risk_expectancy is not None
            and float(risk_expectancy) > 0.0
        )
        normalized_expectancy = aggregate.get("after_cost_expectancy_per_1_lot_usd")
        normalized_growth_positive = (
            normalized_expectancy is None or float(normalized_expectancy) > 0.0
        )
        growth_positive = (
            aggregate["net_pnl"] > 0.0
            and aggregate["after_cost_expectancy"] > 0.0
            and risk_normalized_growth_positive
            and normalized_growth_positive
        )
        robust_growth_positive = bool(
            growth_positive
            and robustness.get("leave_one_best_out_growth_positive_after_costs")
        )
        if robust_growth_positive:
            outlier_dependency_status = "ROBUST_POSITIVE_AFTER_BEST_OUTCOME_REMOVAL"
        elif growth_positive:
            outlier_dependency_status = "POSITIVE_DEPENDS_ON_SINGLE_BEST_OUTCOME"
        else:
            outlier_dependency_status = "GROUP_NOT_POSITIVE_AFTER_COSTS"
        stats.append(
            {
                "symbol": symbol,
                "observed_symbols": observed_symbols,
                "timeframe": timeframe,
                "direction": direction,
                "profile": profile,
                **aggregate,
                **robustness,
                "min_samples": threshold,
                "sample_ready": sample_ready,
                "growth_positive_after_costs": growth_positive,
                "growth_robust_to_single_best_outcome": robust_growth_positive,
                "outlier_dependency_status": outlier_dependency_status,
                "regime_grouping_basis": REGIME_GROUPING_BASIS,
                "regime_breakdown": regime_breakdown,
                "regime_count": len(regime_breakdown),
                "known_regime_trade_count": known_regime_trade_count,
                "unknown_regime_trade_count": int(aggregate["trades"])
                - known_regime_trade_count,
                "regime_attribution_complete": (
                    int(aggregate["trades"]) > 0
                    and known_regime_trade_count == int(aggregate["trades"])
                ),
                "regime_outcome_ready_for_promotion": regime_outcome_ready,
                "press_size_supported_by_robust_outcomes": (
                    sample_ready and robust_growth_positive and regime_outcome_ready
                ),
                "growth_positive_after_costs_per_risk_dollar": (
                    risk_normalized_growth_positive
                ),
                "promotion_blocked_by_incomplete_admission_risk": (
                    sample_ready and not risk_evidence_complete
                ),
                "growth_positive_after_costs_per_lot_when_available": (
                    normalized_growth_positive
                ),
                "outcome_ready_for_promotion": (
                    sample_ready and robust_growth_positive and regime_outcome_ready
                ),
                "last_close_time": ordered[-1].get("close_time") if ordered else None,
            }
        )
    return sorted(
        stats,
        key=lambda group: (
            str(group.get("symbol") or ""),
            str(group.get("timeframe") or ""),
            str(group.get("direction") or ""),
            str(group.get("profile") or ""),
        ),
    )


def _regime_group_breakdown(
    rows: Sequence[Mapping[str, Any]],
    *,
    min_samples: int,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for raw in rows:
        row = dict(raw)
        groups.setdefault(_regime_key(row.get("market_regime")), []).append(row)

    threshold = max(1, int(min_samples))
    result: list[dict[str, Any]] = []
    for market_regime, regime_rows in groups.items():
        ordered = _sort_outcome_rows(regime_rows)
        aggregate = _learning_agg(ordered)
        robustness = _group_growth_robustness(ordered)
        sample_ready = int(aggregate.get("trades") or 0) >= threshold
        growth_positive = _aggregate_growth_positive(aggregate)
        robust_growth_positive = bool(
            growth_positive
            and robustness.get("leave_one_best_out_growth_positive_after_costs")
        )
        known_regime = market_regime != "UNKNOWN"
        result.append(
            {
                "market_regime": market_regime,
                "known_market_regime": known_regime,
                **aggregate,
                **robustness,
                "min_samples": threshold,
                "sample_ready": sample_ready,
                "growth_positive_after_costs": growth_positive,
                "growth_robust_to_single_best_outcome": robust_growth_positive,
                "press_size_supported_by_robust_outcomes": bool(
                    known_regime and sample_ready and robust_growth_positive
                ),
                "outcome_ready_for_promotion": bool(
                    known_regime and sample_ready and robust_growth_positive
                ),
                "last_close_time": ordered[-1].get("close_time") if ordered else None,
            }
        )
    return sorted(result, key=lambda row: str(row.get("market_regime") or ""))


def _regime_key(value: Any) -> str:
    token = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    return token or "UNKNOWN"


def _profit_factor_sort_value(group: Mapping[str, Any]) -> float:
    value = group.get("profit_factor")
    if value is not None:
        return _float(value, 0.0)
    return 1_000_000.0 if str(group.get("profit_factor_state")) == "NO_LOSSES" else 0.0


def _rank_growth_groups(groups: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(group)
        for group in sorted(
            groups,
            key=lambda group: (
                -int(bool(group.get("risk_normalized_evidence_complete", False))),
                -_risk_expectancy_sort_value(group),
                -_normalized_expectancy_sort_value(group),
                -_float(group.get("after_cost_expectancy"), 0.0),
                -_float(group.get("net_pnl"), 0.0),
                -_profit_factor_sort_value(group),
                -int(group.get("trades") or 0),
                -_float(group.get("win_rate"), 0.0),
                str(group.get("symbol") or ""),
                str(group.get("timeframe") or ""),
                str(group.get("direction") or ""),
                str(group.get("profile") or ""),
            ),
        )
    ]


def _rank_weak_groups(groups: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(group)
        for group in sorted(
            groups,
            key=lambda group: (
                -int(bool(group.get("risk_normalized_evidence_complete", False))),
                _risk_expectancy_sort_value(group),
                _normalized_expectancy_sort_value(group),
                _float(group.get("after_cost_expectancy"), 0.0),
                _float(group.get("net_pnl"), 0.0),
                _profit_factor_sort_value(group),
                _float(group.get("win_rate"), 0.0),
                -int(group.get("trades") or 0),
                str(group.get("symbol") or ""),
                str(group.get("timeframe") or ""),
                str(group.get("direction") or ""),
                str(group.get("profile") or ""),
            ),
        )
    ]


def _normalized_expectancy_sort_value(group: Mapping[str, Any]) -> float:
    value = group.get("after_cost_expectancy_per_1_lot_usd")
    if value is None:
        return _float(group.get("after_cost_expectancy"), 0.0)
    return _float(value, 0.0)


def _risk_expectancy_sort_value(group: Mapping[str, Any]) -> float:
    value = group.get("after_cost_expectancy_r")
    if value is None:
        return 0.0
    return _float(value, 0.0)


def _sort_outcome_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted((dict(row) for row in rows), key=_outcome_time_key)


def _outcome_time_key(row: Mapping[str, Any]) -> tuple[float, str, str]:
    raw = row.get("close_time") or row.get("closed_at") or row.get("open_time") or ""
    text = str(raw or "").strip()
    timestamp = 0.0
    if text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            timestamp = parsed.astimezone(timezone.utc).timestamp()
        except (TypeError, ValueError, OverflowError):
            timestamp = 0.0
    return (
        timestamp,
        str(row.get("broker_ticket") or row.get("ticket") or ""),
        str(row.get("decision_ref") or row.get("binding_id") or ""),
    )


def _merged_learning_history(history_report_dir: Path | str) -> dict[str, Any]:
    """Broker-verified MT5 history + simulated paper outcomes, merged by ticket
    with the REAL record winning. Learning-only: the promotion-grade binding
    never reads the simulated ledger."""
    real = _latest_history(history_report_dir)
    real_rows = real.get("history_records") if isinstance(real.get("history_records"), list) else []
    merged: dict[str, dict[str, Any]] = {}
    try:
        from cas_forex.paper_outcome_sim import load_paper_outcome_history

        sim = load_paper_outcome_history()
        for row in sim.get("history_records", []) or []:
            if isinstance(row, Mapping):
                ticket = str(row.get("broker_ticket") or "")
                if ticket:
                    merged[ticket] = dict(row)
        sim_status = sim.get("ingest_status")
    except Exception:
        sim_status = "UNAVAILABLE"
    for row in real_rows:
        if isinstance(row, Mapping):
            ticket = str(row.get("broker_ticket") or row.get("ticket") or "")
            if ticket:
                merged[ticket] = dict(row)  # broker-verified wins over simulated
    return {
        "ingest_status": f"{real.get('ingest_status')}+{sim_status}",
        "history_records": list(merged.values()),
    }


def build_waste_learning_outcomes(
    *,
    cycles: Iterable[Mapping[str, Any]] | None = None,
    attempts: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None,
    history_report: Mapping[str, Any] | None = None,
    audit_path: Path | str = DEFAULT_WASTE_AUDIT_PATH,
    order_attempt_state_path: Path | str = DEFAULT_ORDER_ATTEMPT_STATE_PATH,
    history_report_dir: Path | str = DEFAULT_MT5_DEAL_HISTORY_DIR,
    max_cycles: int = 500,
    min_samples_per_group: int = 4,
) -> dict[str, Any]:
    """Bind EVERY closed paper/demo trade (learning trades included, not just
    PASS-token edges) to its originating direction and aggregate realized wins/
    losses per symbol x direction x profile — the owner's "learn from mistakes"
    ledger. This is what the AI operator reads to see what is actually working
    on paper vs what keeps losing, so it can tune the fenced dials accordingly.
    Read-only PAPER/DEMO; never promotes to real money on its own."""

    attempt_rows = _attempt_rows(
        attempts if attempts is not None else _load_attempts(order_attempt_state_path)
    )
    cycle_rows = _merge_learning_origin_rows(
        _cycle_rows(
            list(cycles) if cycles is not None else _load_cycles(audit_path, max_cycles=max_cycles)
        ),
        attempt_rows,
    )
    history = (
        dict(history_report)
        if history_report is not None
        else _merged_learning_history(history_report_dir)
    )
    history_rows = _history_rows(history)

    attempts_by_decision = _index_by(attempt_rows, "decision_ref")
    attempts_by_order = _index_by(attempt_rows, "order_id")
    history_by_ticket = _index_by(history_rows, "broker_ticket")

    bound: list[dict[str, Any]] = []
    for row in cycle_rows:  # ALL LONG/SHORT cycles, edge-passing or not
        attempt = _matching_attempt(row, attempts_by_decision, attempts_by_order)
        ticket = _broker_ticket(row, attempt)
        history_row = history_by_ticket.get(ticket) if ticket else None
        if attempt and history_row and _paper_demo_history(history_row):
            bound.append(_bound_row(row, attempt, history_row))

    overall = _learning_agg(bound)

    sample_threshold = max(1, int(min_samples_per_group))
    bound = _sort_outcome_rows(bound)
    group_stats = _outcome_group_stats(bound, min_samples=sample_threshold)
    sized = [g for g in group_stats if g["trades"] >= sample_threshold]
    worst = _rank_weak_groups(sized)[:5]
    best = _rank_growth_groups(sized)[:5]

    overall_sample_ready = overall["trades"] >= sample_threshold
    group_learning_ready = bool(sized)
    regime_attributed_trade_count = sum(
        1 for row in bound if _regime_key(row.get("market_regime")) != "UNKNOWN"
    )
    # Tuning is grouped by symbol x direction x profile. A total of four
    # unrelated one-off outcomes is not four samples of any behavior.
    learning_ready = group_learning_ready
    return {
        "report_kind": LEARNING_REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "read_only": True,
        "paper_only": True,
        "learning_ready": learning_ready,
        "group_learning_ready": group_learning_ready,
        "overall_sample_ready": overall_sample_ready,
        "learning_ready_group_count": len(sized),
        "min_samples_per_group": sample_threshold,
        "grouping_basis": "symbol_x_timeframe_x_direction_x_profile",
        "regime_grouping_basis": REGIME_GROUPING_BASIS,
        "ranking_basis": LEARNING_RANKING_BASIS,
        "risk_normalized_ranking_required_for_promotion": True,
        "win_rate_is_supporting_metric_only": True,
        "pooled_profit_cannot_promote_across_regimes": True,
        "bound_trade_count": overall["trades"],
        "closed_history_count": len(history_rows),
        "overall": overall,
        "direction_counts": dict(Counter(str(r.get("direction") or "UNKNOWN") for r in bound)),
        "symbol_counts": dict(Counter(str(r.get("symbol") or "UNKNOWN") for r in bound)),
        "regime_counts": dict(
            Counter(_regime_key(row.get("market_regime")) for row in bound)
        ),
        "regime_source_counts": dict(
            Counter(
                str(row.get("market_regime_source") or "UNKNOWN_SOURCE")
                for row in bound
            )
        ),
        "regime_attributed_trade_count": regime_attributed_trade_count,
        "unknown_regime_trade_count": int(overall["trades"])
        - regime_attributed_trade_count,
        "worst_groups": worst,
        "best_groups": best,
        "group_count": len(group_stats),
        "group_stats": group_stats,
        "paper_demo_history_status": history.get("ingest_status"),
        "runtime_changed": False,
        "broker_touched": False,
        "money_moved": False,
        "edge_token_minted": False,
        "owner_accept_created": False,
        "sample_bound_rows": bound[-8:],
        "claim_boundary": LEARNING_CLAIM_BOUNDARY,
        "next_action": (
            f"{overall['trades']} paper outcomes bound "
            f"({overall['wins']}W/{overall['losses']}L, net {overall['net_pnl']}). "
            "The AI operator reads this to tune the fenced dials; real-money "
            "promotion still requires a PASS edge token + owner live gates."
            if learning_ready
            else (
                f"{overall['trades']} paper outcomes are bound overall, but no symbol x timeframe x direction x profile "
                f"group has the required {sample_threshold} outcomes yet. Keep collecting differentiated "
                "broker-linked outcomes; do not describe per-group learning as ready."
                if overall_sample_ready
                else "Not enough closed paper trades bound yet to learn per-group patterns."
            )
        ),
    }


__all__ = [
    "DEFAULT_MIN_BOUND_OUTCOMES_FOR_PROMOTION",
    "LEARNING_REPORT_KIND",
    "REPORT_KIND",
    "STATUS_AWAITING_CLOSED_HISTORY",
    "STATUS_AWAITING_EXECUTION",
    "STATUS_COLLECTING",
    "STATUS_NO_CONFIRMED_EDGE",
    "STATUS_READY",
    "build_waste_direction_outcome_binding",
    "build_waste_learning_outcomes",
]
