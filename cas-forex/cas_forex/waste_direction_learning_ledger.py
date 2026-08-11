"""Read-only WASTE direction learning ledger.

This module summarizes the durable WASTE audit log so CAS can learn how LONG
and SHORT hypotheses are behaving over time. It does not change the strategy,
authorize trades, mint edge tokens, or move money. It gives the AI evidence it
can later use to adapt profile selection and compounding only after enough
confirmed direction evidence exists.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from cas_forex.jsonl_tail import read_jsonl_tail
from cas_forex.time_utils import utc_now
from cas_forex.waste_cycle_audit import DEFAULT_AUDIT_PATH

REPORT_KIND = "cas_forex_waste_direction_learning_ledger"
STATUS_ACTIVE = "WASTE_DIRECTION_LEARNING_ACTIVE"
STATUS_NO_EVIDENCE = "WASTE_DIRECTION_LEARNING_NO_EVIDENCE"

CLAIM_BOUNDARY = (
    "WASTE direction learning ledger is read-only analysis of prior WASTE cycle "
    "audit rows. It can summarize LONG/SHORT outcomes and profile evidence, but "
    "it does not place orders, close positions, create broker ACCEPT, create "
    "owner ACCEPT, authorize live trading, mint edge tokens, deposit, withdraw, "
    "move bank/card money, automate payouts, or mark evidence LICENSED."
)


def build_waste_direction_learning_ledger(
    *,
    cycles: Iterable[Mapping[str, Any]] | None = None,
    audit_path: Path | str = DEFAULT_AUDIT_PATH,
    max_cycles: int = 250,
    min_confirmed_for_adaptation: int = 5,
) -> dict[str, Any]:
    """Summarize historical WASTE direction outcomes without side effects."""

    raw_cycles = list(cycles) if cycles is not None else _load_cycles(audit_path, max_cycles=max_cycles)
    rows = [_cycle_row(cycle) for cycle in raw_cycles if isinstance(cycle, Mapping)]
    rows = [row for row in rows if row is not None]
    groups = _groups(rows)
    direction_counts = Counter(row["direction"] for row in rows if row.get("direction") in {"LONG", "SHORT"})
    status_counts = Counter(str(row.get("edge_status") or "NO_EDGE") for row in rows)
    confirmed = [row for row in rows if row.get("edge_confirmed")]
    blocked = [row for row in rows if row.get("direction") in {"LONG", "SHORT"} and not row.get("edge_confirmed")]
    profile_recommendation = _profile_recommendation(
        groups,
        min_confirmed_for_adaptation=min_confirmed_for_adaptation,
    )

    status = STATUS_ACTIVE if rows else STATUS_NO_EVIDENCE
    return {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "cycles_loaded": len(raw_cycles),
        "direction_rows": len(rows),
        "confirmed_direction_count": len(confirmed),
        "blocked_direction_count": len(blocked),
        "direction_counts": dict(direction_counts),
        "edge_status_counts": dict(status_counts),
        "groups": groups,
        "profile_recommendation": profile_recommendation,
        "learning_ready_for_adaptation": bool(profile_recommendation.get("ready_for_adaptation", False)),
        "broker_touched": False,
        "live_order_attempted": False,
        "attempt_finalized": False,
        "edge_token_minted": False,
        "money_moved": False,
        "sample_rows": rows[-10:],
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(rows, confirmed, profile_recommendation),
    }


def _load_cycles(audit_path: Path | str, *, max_cycles: int) -> list[dict[str, Any]]:
    return read_jsonl_tail(audit_path, limit=max_cycles)


def _cycle_row(cycle: Mapping[str, Any]) -> dict[str, Any] | None:
    candidate = _mapping(cycle.get("candidate"))
    analysis = _mapping(cycle.get("analysis"))
    watch_state = _mapping(cycle.get("watch_state"))
    edge = _mapping(cycle.get("edge"))
    hypothesis = _mapping(candidate.get("directional_hypothesis")) or _mapping(analysis.get("hypothesis"))
    meta = _mapping(candidate.get("market_state_meta"))
    cas_map = _mapping(meta.get("cas_feature_map")) or _mapping(analysis.get("cas_feature_map")) or _mapping(watch_state.get("cas_feature_map"))
    tuning = _mapping(meta.get("directional_hypothesis_tuning")) or _mapping(analysis.get("hypothesis_tuning")) or _mapping(watch_state.get("directional_hypothesis_tuning"))
    direction = _direction(candidate, hypothesis)
    if direction not in {"LONG", "SHORT"}:
        return None
    long_score = _float(hypothesis.get("long_score"))
    short_score = _float(hypothesis.get("short_score"))
    chosen_score = long_score if direction == "LONG" else short_score
    opposite_score = short_score if direction == "LONG" else long_score
    score_margin = (
        round(abs(float(chosen_score) - float(opposite_score)), 6)
        if chosen_score is not None and opposite_score is not None
        else None
    )
    edge_status = str(edge.get("status") or "NO_EDGE")
    edge_confirmed = edge_status == "PASS" and bool(edge.get("has_edge_token", False))
    profit_box = _profit_box(candidate, direction)
    return {
        "cycle_id": cycle.get("cycle_id"),
        "generated_at": cycle.get("generated_at"),
        "decision": cycle.get("decision"),
        "symbol": candidate.get("symbol") or hypothesis.get("symbol") or watch_state.get("symbol"),
        "timeframe": candidate.get("timeframe") or hypothesis.get("timeframe") or watch_state.get("timeframe"),
        "direction": direction,
        "opposite_direction": "SHORT" if direction == "LONG" else "LONG",
        "profile": hypothesis.get("profile") or cas_map.get("selected_profile") or watch_state.get("selected_directional_profile"),
        "regime": candidate.get("regime") or hypothesis.get("regime"),
        "chosen_score": chosen_score,
        "opposite_score": opposite_score,
        "score_margin": score_margin,
        "confidence": _float(hypothesis.get("confidence")),
        "entry_pair_count": _int(candidate.get("entry_pair_count"), _int(watch_state.get("entry_pair_count"), 0)),
        "edge_status": edge_status,
        "edge_confirmed": edge_confirmed,
        "measured_win_prob": _float(edge.get("measured_win_prob")),
        "threshold": _float(edge.get("threshold")),
        "null_p95": _float(edge.get("null_p95")),
        "edge_reason": edge.get("reason"),
        "reward_r": profit_box.get("reward_r"),
        "profit_box_valid": bool(profit_box.get("valid", False)),
        "broker_grade_market_truth": bool(meta.get("broker_grade_market_truth", False) or watch_state.get("broker_grade_market_truth", False)),
        "selected_rpm_action": cas_map.get("selected_rpm_action"),
        "selected_cjt_region": cas_map.get("selected_cjt_region"),
        "selected_is_lacuna": cas_map.get("selected_is_lacuna"),
        "cell_reliability": cas_map.get("cell_reliability"),
        "no_lookahead": bool(tuning.get("no_lookahead", False)),
        "validation_pairs_holdout": bool(tuning.get("validation_pairs_holdout", False)),
    }


def _groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("symbol") or "UNKNOWN"),
            str(row.get("timeframe") or "UNKNOWN"),
            str(row.get("profile") or "UNKNOWN"),
            str(row.get("direction") or "UNKNOWN"),
        )
        buckets.setdefault(key, []).append(row)
    groups: list[dict[str, Any]] = []
    for (symbol, timeframe, profile, direction), items in buckets.items():
        confirmed = [item for item in items if item.get("edge_confirmed")]
        groups.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "profile": profile,
                "direction": direction,
                "cycles": len(items),
                "confirmed_count": len(confirmed),
                "blocked_count": len(items) - len(confirmed),
                "confirmed_rate": round(len(confirmed) / len(items), 6) if items else 0.0,
                "avg_chosen_score": _avg(item.get("chosen_score") for item in items),
                "avg_opposite_score": _avg(item.get("opposite_score") for item in items),
                "avg_score_margin": _avg(item.get("score_margin") for item in items),
                "avg_measured_win_prob": _avg(item.get("measured_win_prob") for item in items),
                "avg_reward_r": _avg(item.get("reward_r") for item in items),
                "edge_status_counts": dict(Counter(str(item.get("edge_status") or "NO_EDGE") for item in items)),
                "last_seen_at": items[-1].get("generated_at"),
                "last_edge_status": items[-1].get("edge_status"),
                "last_edge_reason": items[-1].get("edge_reason"),
                "broker_grade_count": sum(1 for item in items if item.get("broker_grade_market_truth")),
                "holdout_count": sum(1 for item in items if item.get("validation_pairs_holdout")),
            }
        )
    return sorted(
        groups,
        key=lambda item: (
            -int(item["confirmed_count"]),
            -float(item["confirmed_rate"]),
            -int(item["cycles"]),
            str(item["symbol"]),
            str(item["direction"]),
        ),
    )


def _profile_recommendation(
    groups: list[dict[str, Any]],
    *,
    min_confirmed_for_adaptation: int,
) -> dict[str, Any]:
    confirmed_groups = [group for group in groups if int(group.get("confirmed_count", 0)) > 0]
    total_confirmed = sum(int(group.get("confirmed_count", 0)) for group in groups)
    if total_confirmed < int(min_confirmed_for_adaptation):
        dominant = groups[0] if groups else {}
        return {
            "status": "INSUFFICIENT_CONFIRMED_EDGE",
            "ready_for_adaptation": False,
            "min_confirmed_for_adaptation": int(min_confirmed_for_adaptation),
            "confirmed_direction_count": total_confirmed,
            "dominant_observed_group": dominant,
            "recommendation": (
                "Keep WASTE learning in PAPER until enough LONG/SHORT hypotheses earn PASS edge tokens."
            ),
        }
    best = sorted(
        confirmed_groups,
        key=lambda item: (
            -float(item.get("confirmed_rate", 0.0)),
            -int(item.get("confirmed_count", 0)),
            -float(item.get("avg_score_margin") or 0.0),
        ),
    )[0]
    return {
        "status": "PROFILE_DIRECTION_REVIEW_READY",
        "ready_for_adaptation": True,
        "min_confirmed_for_adaptation": int(min_confirmed_for_adaptation),
        "confirmed_direction_count": total_confirmed,
        "recommended_group": best,
        "recommendation": (
            "Review the recommended profile/direction as an input to WASTE profile selection; live execution still requires edge, broker, risk, recovery, and owner gates."
        ),
    }


def _next_action(
    rows: list[dict[str, Any]],
    confirmed: list[dict[str, Any]],
    recommendation: Mapping[str, Any],
) -> str:
    if not rows:
        return "Let WASTE run in PAPER or run a real-candle probe so the direction ledger can collect evidence."
    if not confirmed:
        return "Continue PAPER WASTE learning until at least one LONG/SHORT direction earns a PASS edge token."
    if not bool(recommendation.get("ready_for_adaptation", False)):
        return str(recommendation.get("recommendation") or "Collect more confirmed direction evidence before adapting WASTE.")
    return "Direction learning has enough confirmed evidence for owner/AI review; any adaptation must stay behind normal gates."


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _direction(candidate: Mapping[str, Any], hypothesis: Mapping[str, Any]) -> str | None:
    text = str(candidate.get("direction") or hypothesis.get("direction") or hypothesis.get("action") or "").upper()
    return text if text in {"LONG", "SHORT"} else None


def _profit_box(candidate: Mapping[str, Any], direction: str | None) -> dict[str, Any]:
    entry = _float(candidate.get("entry"))
    stop = _float(candidate.get("stop_loss"))
    take_profit = _float(candidate.get("take_profit"))
    if entry is None or stop is None or take_profit is None or direction not in {"LONG", "SHORT"}:
        return {"valid": False, "reward_r": None}
    if direction == "LONG":
        risk = entry - stop
        reward = take_profit - entry
        valid = stop < entry < take_profit
    else:
        risk = stop - entry
        reward = entry - take_profit
        valid = take_profit < entry < stop
    return {
        "valid": bool(valid and risk > 0 and reward > 0),
        "reward_r": round(float(reward / risk), 6) if risk > 0 and reward > 0 else None,
    }


def _avg(values: Iterable[Any]) -> float | None:
    nums = [float(value) for value in values if value is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 6)


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
    "STATUS_ACTIVE",
    "STATUS_NO_EVIDENCE",
    "build_waste_direction_learning_ledger",
]
