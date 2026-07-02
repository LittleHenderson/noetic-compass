"""Read-only WASTE LONG/SHORT direction review packet.

The WASTE runner already decides LONG, SHORT, or NO_TRADE from real candle
state, CAS context, and owner controls. This module summarizes the latest
cycle's direction choice, opposite-side score, edge-gate result, and
take-profit box so live-money progression can see whether the direction is
actually confirmed or still blocked.
"""

from __future__ import annotations

from typing import Any, Mapping

from cas_forex.time_utils import utc_now

REPORT_KIND = "cas_forex_waste_direction_review_packet"
STATUS_CONFIRMED = "WASTE_DIRECTION_EDGE_CONFIRMED"
STATUS_BLOCKED = "WASTE_DIRECTION_EDGE_BLOCKED"
STATUS_NO_CANDIDATE = "WASTE_DIRECTION_NO_CANDIDATE"
STATUS_UNAVAILABLE = "WASTE_DIRECTION_REVIEW_UNAVAILABLE"

CLAIM_BOUNDARY = (
    "WASTE direction review is a read-only summary of the latest WASTE cycle's "
    "LONG/SHORT hypothesis, candidate, out-of-sample validation pairs, and edge "
    "gate result. It does not place orders, close positions, create broker "
    "ACCEPT, create owner ACCEPT, authorize live trading, mint edge tokens, "
    "deposit, withdraw, move bank/card money, automate payouts, or mark "
    "evidence LICENSED."
)


def build_waste_direction_review_packet(
    *,
    cycle_status: Mapping[str, Any] | None = None,
    latest_cycle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact direction quality packet from the latest WASTE cycle."""

    cycle = dict(latest_cycle) if latest_cycle is not None else _latest_cycle(cycle_status)
    if not cycle:
        return {
            "report_kind": REPORT_KIND,
            "generated_at": utc_now().isoformat(),
            "status": STATUS_UNAVAILABLE,
            "direction_edge_confirmed": False,
            "broker_touched": False,
            "live_order_attempted": False,
            "attempt_finalized": False,
            "edge_token_minted": False,
            "money_moved": False,
            "direction_summary": {},
            "profit_box": {},
            "edge_gate_summary": {},
            "cas_context": {},
            "blocker_count": 1,
            "blockers": [
                _blocker(
                    "latest_waste_cycle_present",
                    "directional_edge",
                    None,
                    "No durable WASTE cycle is available for direction review.",
                    "Start WASTE in PAPER or run a real-candle probe so CAS can review a current LONG/SHORT hypothesis.",
                )
            ],
            "claim_boundary": CLAIM_BOUNDARY,
            "next_action": "Start WASTE in PAPER or run a real-candle probe so CAS can review a current LONG/SHORT hypothesis.",
        }

    candidate = _mapping(cycle.get("candidate"))
    analysis = _mapping(cycle.get("analysis"))
    watch_state = _mapping(cycle.get("watch_state"))
    edge = _mapping(cycle.get("edge"))
    hypothesis = _mapping(candidate.get("directional_hypothesis")) or _mapping(analysis.get("hypothesis"))
    market_meta = _mapping(candidate.get("market_state_meta"))
    cas_map = _mapping(market_meta.get("cas_feature_map")) or _mapping(analysis.get("cas_feature_map")) or _mapping(watch_state.get("cas_feature_map"))
    tuning = (
        _mapping(market_meta.get("directional_hypothesis_tuning"))
        or _mapping(analysis.get("hypothesis_tuning"))
        or _mapping(watch_state.get("directional_hypothesis_tuning"))
    )

    direction = _direction(candidate, hypothesis)
    long_score = _float(hypothesis.get("long_score"))
    short_score = _float(hypothesis.get("short_score"))
    chosen_score = _chosen_score(direction, long_score, short_score)
    opposite_score = _opposite_score(direction, long_score, short_score)
    score_margin = (
        round(abs(float(chosen_score) - float(opposite_score)), 4)
        if chosen_score is not None and opposite_score is not None
        else None
    )
    edge_status = str(edge.get("status") or "")
    has_edge_token = bool(edge.get("has_edge_token", False))
    edge_pass = edge_status == "PASS" and has_edge_token
    broker_grade = bool(
        market_meta.get("broker_grade_market_truth", False)
        or watch_state.get("broker_grade_market_truth", False)
    )
    entry_pair_count = _int(candidate.get("entry_pair_count"), _int(watch_state.get("entry_pair_count"), 0))
    profit_box = _profit_box(candidate, direction)

    blockers: list[dict[str, Any]] = []
    _add_blocker(
        blockers,
        "waste_candidate_present",
        bool(candidate),
        None,
        "Latest WASTE cycle did not form a candidate.",
        "Let WASTE keep watching or run a real-candle probe until a candidate forms.",
    )
    _add_blocker(
        blockers,
        "direction_present",
        direction in {"LONG", "SHORT"},
        direction,
        "Latest WASTE candidate does not carry a LONG or SHORT direction.",
        "Review the WASTE analysis stage before any dry-run or pilot progression.",
    )
    _add_blocker(
        blockers,
        "broker_grade_market_truth_present",
        broker_grade,
        broker_grade,
        "Direction review requires broker-grade read-only candle truth.",
        "Reconnect/read MT5 broker candles and rerun WASTE or the real-candle probe.",
    )
    _add_blocker(
        blockers,
        "out_of_sample_pairs_present",
        entry_pair_count > 0,
        entry_pair_count,
        "Direction review requires out-of-sample validation pairs attached to the candidate.",
        "Run WASTE with enough broker candles so the edge gate has validation pairs.",
    )
    _add_blocker(
        blockers,
        "edge_gate_passed_for_direction",
        edge_pass,
        {
            "status": edge_status or None,
            "has_edge_token": has_edge_token,
            "reason": edge.get("reason"),
        },
        "The edge gate has not confirmed the chosen direction with a PASS token.",
        "Keep WASTE in PAPER/no-trade until the selected direction beats null, costs, and the threshold.",
    )
    _add_blocker(
        blockers,
        "directional_profit_box_valid",
        bool(profit_box.get("valid", False)),
        profit_box,
        "The candidate's stop-loss/take-profit box is not valid for its direction.",
        "Review candidate entry, stop, and take-profit before any dry-run or pilot progression.",
    )

    status = STATUS_CONFIRMED if not blockers else (STATUS_NO_CANDIDATE if not candidate else STATUS_BLOCKED)
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "direction_edge_confirmed": status == STATUS_CONFIRMED,
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "money_moved": False,
        "direction_summary": {
            "symbol": candidate.get("symbol") or hypothesis.get("symbol") or watch_state.get("symbol"),
            "timeframe": candidate.get("timeframe") or hypothesis.get("timeframe") or watch_state.get("timeframe"),
            "direction": direction,
            "opposite_direction": _opposite_direction(direction),
            "long_score": long_score,
            "short_score": short_score,
            "chosen_score": chosen_score,
            "opposite_score": opposite_score,
            "score_margin": score_margin,
            "confidence": _float(hypothesis.get("confidence")),
            "regime": candidate.get("regime") or hypothesis.get("regime"),
            "profile": hypothesis.get("profile") or watch_state.get("selected_directional_profile"),
            "decision_ref": candidate.get("decision_ref"),
            "entry_pair_count": entry_pair_count,
        },
        "profit_box": profit_box,
        "edge_gate_summary": {
            "status": edge_status or None,
            "measured_win_prob": _float(edge.get("measured_win_prob")),
            "threshold": _float(edge.get("threshold")),
            "null_p95": _float(edge.get("null_p95")),
            "has_edge_token": has_edge_token,
            "reason": edge.get("reason"),
        },
        "cas_context": {
            "broker_grade_market_truth": broker_grade,
            "entry_pair_count": entry_pair_count,
            "selected_profile": cas_map.get("selected_profile") or watch_state.get("selected_directional_profile"),
            "selected_rpm_action": cas_map.get("selected_rpm_action"),
            "selected_cjt_region": cas_map.get("selected_cjt_region"),
            "selected_is_lacuna": cas_map.get("selected_is_lacuna"),
            "cell_reliability": cas_map.get("cell_reliability"),
            "hypothesis_tuning_status": tuning.get("status"),
            "no_lookahead": bool(tuning.get("no_lookahead", False)),
            "validation_pairs_holdout": bool(tuning.get("validation_pairs_holdout", False)),
        },
        "blocker_count": len(blockers),
        "blockers": blockers,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(blockers),
    }


def _latest_cycle(cycle_status: Mapping[str, Any] | None) -> dict[str, Any]:
    if cycle_status is not None:
        latest = cycle_status.get("latest_cycle")
        return dict(latest) if isinstance(latest, Mapping) else {}
    try:
        from cas_forex.waste_cycle_audit import build_waste_cycle_audit_status

        latest = build_waste_cycle_audit_status().get("latest_cycle")
        return dict(latest) if isinstance(latest, Mapping) else {}
    except Exception:
        return {}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _direction(candidate: Mapping[str, Any], hypothesis: Mapping[str, Any]) -> str | None:
    value = candidate.get("direction") or hypothesis.get("direction") or hypothesis.get("action")
    text = str(value or "").upper()
    return text if text in {"LONG", "SHORT"} else None


def _opposite_direction(direction: str | None) -> str | None:
    if direction == "LONG":
        return "SHORT"
    if direction == "SHORT":
        return "LONG"
    return None


def _chosen_score(direction: str | None, long_score: float | None, short_score: float | None) -> float | None:
    if direction == "LONG":
        return long_score
    if direction == "SHORT":
        return short_score
    return None


def _opposite_score(direction: str | None, long_score: float | None, short_score: float | None) -> float | None:
    if direction == "LONG":
        return short_score
    if direction == "SHORT":
        return long_score
    return None


def _profit_box(candidate: Mapping[str, Any], direction: str | None) -> dict[str, Any]:
    entry = _float(candidate.get("entry"))
    stop = _float(candidate.get("stop_loss"))
    take_profit = _float(candidate.get("take_profit"))
    if entry is None or stop is None or take_profit is None or direction not in {"LONG", "SHORT"}:
        return {
            "valid": False,
            "entry": entry,
            "stop_loss": stop,
            "take_profit": take_profit,
            "risk_units": None,
            "reward_units": None,
            "reward_r": None,
        }
    if direction == "LONG":
        risk = entry - stop
        reward = take_profit - entry
        valid = stop < entry < take_profit
    else:
        risk = stop - entry
        reward = entry - take_profit
        valid = take_profit < entry < stop
    reward_r = round(reward / risk, 4) if risk > 0 else None
    return {
        "valid": bool(valid and risk > 0 and reward > 0),
        "entry": entry,
        "stop_loss": stop,
        "take_profit": take_profit,
        "risk_units": round(float(risk), 8) if risk > 0 else None,
        "reward_units": round(float(reward), 8) if reward > 0 else None,
        "reward_r": reward_r,
        "direction": direction,
    }


def _add_blocker(
    out: list[dict[str, Any]],
    blocker_id: str,
    clear: bool,
    value: Any,
    detail: str,
    next_action: str,
) -> None:
    if clear:
        return
    out.append(_blocker(blocker_id, "directional_edge", value, detail, next_action))


def _blocker(
    blocker_id: str,
    plane: str,
    value: Any,
    detail: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "blocker_id": blocker_id,
        "plane": plane,
        "clear": False,
        "value": value,
        "detail": detail,
        "next_action": next_action,
    }


def _next_action(blockers: list[Mapping[str, Any]]) -> str:
    if not blockers:
        return "WASTE direction is edge-confirmed; any live/pilot action still requires the normal owner, broker, risk, and recovery gates."
    first = blockers[0]
    return str(first.get("next_action") or "Resolve the listed WASTE direction blockers.")


def _float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


__all__ = [
    "REPORT_KIND",
    "STATUS_BLOCKED",
    "STATUS_CONFIRMED",
    "STATUS_NO_CANDIDATE",
    "STATUS_UNAVAILABLE",
    "build_waste_direction_review_packet",
]
