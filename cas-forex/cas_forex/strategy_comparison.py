"""Observational ranking + diffing primitives for strategy candidates.

This module unifies three disjoint strategy sources — Forex Fury replay
candidates, ``strategy_leads.json`` research leads, and the strategy-dev
queue work items — into a single ``StrategyComparisonRecord`` shape, then
ranks them by a weighted composite score and produces field-level diffs.

CRITICAL framing: every report and diff produced here is **observational**.
Plain-English text describes what the evidence shows and what is missing.
It never says "you should pick X", "X is a better trade", "go with Y", or
any advisory phrasing — the operator owns every decision. The forbidden
phrase set is enforced by ``tests/test_strategy_comparison.py``.

Pure functions only. No disk I/O, no network. ``rank_strategies`` is
deterministic when ``now`` is pinned.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RankingMetric:
    name: str
    value: float
    rank: Optional[int]


@dataclass(frozen=True)
class StrategyComparisonRecord:
    strategy_id: str
    source: str
    symbol: Optional[str]
    timeframe: Optional[str]
    family: Optional[str]
    profit_factor: Optional[float]
    equity_drawdown_pct: Optional[float]
    walk_forward_grade: Optional[str]
    total_trades: Optional[int]
    history_quality: Optional[str]
    metrics: tuple[RankingMetric, ...] = field(default_factory=tuple)
    composite_score: float = 0.0
    composite_rank: Optional[int] = None
    imported_at_iso: Optional[str] = None


@dataclass(frozen=True)
class StrategyRankingReport:
    generated_at_iso: str
    record_count: int
    records: tuple[StrategyComparisonRecord, ...]
    plain_english_summary: str
    diagnostic_hints: tuple[str, ...]


@dataclass(frozen=True)
class StrategyDiff:
    strategy_id_a: str
    strategy_id_b: str
    symbol_match: bool
    timeframe_match: bool
    family_match: bool
    field_diffs: tuple[Mapping[str, Any], ...]
    plain_english_diff: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


DEFAULT_WEIGHTS: Mapping[str, float] = {
    "profit_factor": 0.35,
    "equity_drawdown_inv": 0.30,
    "walk_forward_grade": 0.20,
    "recency": 0.10,
    "total_trades_log": 0.05,
}

# Walk-forward grade mapping. None / unknown grades map to 0.0.
WALK_FORWARD_GRADE_MAP: Mapping[str, float] = {
    "WALK_FORWARD_LEAD": 1.0,
    "LEAD": 1.0,
    "WATCH": 0.5,
    "REJECT": 0.0,
    "NOT_PROMOTED": 0.0,
}

# Profit-factor cap for normalization: PF >= PF_CAP normalizes to 1.0.
PF_CAP = 5.0

# Equity drawdown ceiling: DD >= DD_CEIL normalizes to 0.0 (worst).
DD_CEIL_PCT = 50.0

# Total trades log normalization ceiling: log1p(N) >= log1p(TRADES_CEIL) → 1.0.
TRADES_CEIL = 1000.0

# Recency: ages older than this in days → 0.0.
RECENCY_HORIZON_DAYS = 30.0


# ---------------------------------------------------------------------------
# Helpers — coercion
# ---------------------------------------------------------------------------


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    return str(value)


def _first(seq: Any) -> Optional[str]:
    """Return first non-empty string in a sequence; tolerant to bad inputs."""
    if isinstance(seq, str):
        return seq or None
    if isinstance(seq, (list, tuple)):
        for item in seq:
            text = _as_str(item)
            if text:
                return text
    return None


def _pick(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = _as_str(value)
    if not text:
        return None
    # Strip trailing Z so fromisoformat tolerates it.
    candidate = text.replace("Z", "+00:00") if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        # Try a date-only fallback.
        try:
            dt = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_fury_candidate(candidate: Mapping[str, Any], default_imported_at: Optional[str]) -> Optional[StrategyComparisonRecord]:
    sid = _as_str(_pick(candidate, "candidate_id", "id"))
    if not sid:
        return None
    evidence = candidate.get("evidence") if isinstance(candidate.get("evidence"), Mapping) else {}
    symbol = _as_str(_pick(candidate, "cas_symbol", "raw_symbol", "symbol"))
    timeframe = _as_str(_pick(candidate, "timeframe"))
    if not timeframe:
        job = candidate.get("replay_job") if isinstance(candidate.get("replay_job"), Mapping) else {}
        timeframe = _first(job.get("timeframes")) if job else None
    family = _as_str(_pick(candidate, "family"))
    pf = _as_float(_pick(evidence, "profit_factor"))
    dd = _as_float(_pick(evidence, "equity_drawdown_relative_pct", "equity_drawdown_pct"))
    trades = _as_int(_pick(evidence, "total_trades"))
    history_quality = _as_str(_pick(evidence, "history_quality"))
    walk_grade = _as_str(_pick(candidate, "walk_forward_grade"))
    imported_at = _as_str(_pick(candidate, "imported_at_iso", "created_at_iso", "created_at")) or default_imported_at
    return StrategyComparisonRecord(
        strategy_id=sid,
        source="forex_fury_candidate",
        symbol=symbol,
        timeframe=timeframe,
        family=family,
        profit_factor=pf,
        equity_drawdown_pct=dd,
        walk_forward_grade=walk_grade,
        total_trades=trades,
        history_quality=history_quality,
        imported_at_iso=imported_at,
    )


def _normalize_strategy_lead(lead: Mapping[str, Any], default_imported_at: Optional[str]) -> Optional[StrategyComparisonRecord]:
    sid = _as_str(_pick(lead, "lead_id", "strategy_lead_id", "id"))
    if not sid:
        return None
    family = _as_str(_pick(lead, "family"))
    condition_fit = lead.get("condition_fit") if isinstance(lead.get("condition_fit"), Mapping) else {}
    timeframe = _first(condition_fit.get("preferred_timeframes")) if condition_fit else None
    symbol = _first(_pick(lead, "symbols_promoted_for_next_tests", "symbols_watchlist", "symbols"))
    pf = _as_float(_pick(lead, "profit_factor"))
    dd = _as_float(_pick(lead, "equity_drawdown_pct", "max_drawdown_pct"))
    trades = _as_int(_pick(lead, "total_trades"))
    history_quality = _as_str(_pick(lead, "history_quality"))
    walk_grade = _as_str(_pick(lead, "walk_forward_grade"))
    imported_at = _as_str(_pick(lead, "imported_at_iso", "created_at_iso", "updated_at")) or default_imported_at
    return StrategyComparisonRecord(
        strategy_id=sid,
        source="strategy_lead",
        symbol=symbol,
        timeframe=timeframe,
        family=family,
        profit_factor=pf,
        equity_drawdown_pct=dd,
        walk_forward_grade=walk_grade,
        total_trades=trades,
        history_quality=history_quality,
        imported_at_iso=imported_at,
    )


def _normalize_dev_queue_item(item: Mapping[str, Any], default_imported_at: Optional[str]) -> Optional[StrategyComparisonRecord]:
    sid = _as_str(_pick(item, "work_item_id", "item_id", "strategy_id", "id"))
    if not sid:
        return None
    family = _first(_pick(item, "families")) or _as_str(_pick(item, "family"))
    symbol = _first(_pick(item, "symbols"))
    timeframe = _first(_pick(item, "timeframes"))
    evidence = item.get("evidence") if isinstance(item.get("evidence"), Mapping) else {}
    pf = _as_float(_pick(item, "profit_factor")) or _as_float(_pick(evidence, "profit_factor"))
    dd = _as_float(_pick(item, "equity_drawdown_pct", "max_drawdown_pct")) or _as_float(
        _pick(evidence, "equity_drawdown_relative_pct", "equity_drawdown_pct")
    )
    trades = _as_int(_pick(item, "total_trades")) or _as_int(_pick(evidence, "total_trades"))
    history_quality = _as_str(_pick(item, "history_quality")) or _as_str(_pick(evidence, "history_quality"))
    walk_grade = _as_str(_pick(item, "walk_forward_grade"))
    imported_at = _as_str(_pick(item, "imported_at_iso", "created_at_iso", "created_at")) or default_imported_at
    return StrategyComparisonRecord(
        strategy_id=sid,
        source="strategy_dev_queue",
        symbol=symbol,
        timeframe=timeframe,
        family=family,
        profit_factor=pf,
        equity_drawdown_pct=dd,
        walk_forward_grade=walk_grade,
        total_trades=trades,
        history_quality=history_quality,
        imported_at_iso=imported_at,
    )


def normalize_records(
    *,
    fury_candidates: Optional[Sequence[Mapping[str, Any]]] = None,
    strategy_leads: Optional[Sequence[Mapping[str, Any]]] = None,
    strategy_dev_queue_items: Optional[Sequence[Mapping[str, Any]]] = None,
    fury_imported_at: Optional[str] = None,
    leads_imported_at: Optional[str] = None,
    dev_queue_imported_at: Optional[str] = None,
) -> tuple[StrategyComparisonRecord, ...]:
    """Normalize records from three sources into a unified shape.

    Each source has its own field naming. Missing fields become ``None``.
    Records without an identifiable id are silently dropped.
    """

    out: list[StrategyComparisonRecord] = []
    for cand in fury_candidates or ():
        if not isinstance(cand, Mapping):
            continue
        rec = _normalize_fury_candidate(cand, fury_imported_at)
        if rec is not None:
            out.append(rec)
    for lead in strategy_leads or ():
        if not isinstance(lead, Mapping):
            continue
        rec = _normalize_strategy_lead(lead, leads_imported_at)
        if rec is not None:
            out.append(rec)
    for item in strategy_dev_queue_items or ():
        if not isinstance(item, Mapping):
            continue
        rec = _normalize_dev_queue_item(item, dev_queue_imported_at)
        if rec is not None:
            out.append(rec)
    return tuple(out)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def _norm_profit_factor(pf: Optional[float]) -> Optional[float]:
    if pf is None:
        return None
    if pf <= 0:
        return 0.0
    return min(pf / PF_CAP, 1.0)


def _norm_equity_drawdown_inv(dd: Optional[float]) -> Optional[float]:
    if dd is None:
        return None
    if dd <= 0:
        return 1.0
    if dd >= DD_CEIL_PCT:
        return 0.0
    return 1.0 - (dd / DD_CEIL_PCT)


def _norm_walk_forward(grade: Optional[str]) -> Optional[float]:
    if grade is None:
        return None
    key = grade.upper().strip()
    if key in WALK_FORWARD_GRADE_MAP:
        return WALK_FORWARD_GRADE_MAP[key]
    return 0.0


def _norm_recency(imported_at_iso: Optional[str], now: datetime) -> Optional[float]:
    dt = _parse_iso(imported_at_iso)
    if dt is None:
        return None
    age_days = (now - dt).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    if age_days >= RECENCY_HORIZON_DAYS:
        return 0.0
    return 1.0 - (age_days / RECENCY_HORIZON_DAYS)


def _norm_total_trades_log(trades: Optional[int]) -> Optional[float]:
    if trades is None:
        return None
    if trades <= 0:
        return 0.0
    return min(math.log1p(trades) / math.log1p(TRADES_CEIL), 1.0)


_METRIC_NORMALIZERS = {
    "profit_factor": lambda r, now: _norm_profit_factor(r.profit_factor),
    "equity_drawdown_inv": lambda r, now: _norm_equity_drawdown_inv(r.equity_drawdown_pct),
    "walk_forward_grade": lambda r, now: _norm_walk_forward(r.walk_forward_grade),
    "recency": lambda r, now: _norm_recency(r.imported_at_iso, now),
    "total_trades_log": lambda r, now: _norm_total_trades_log(r.total_trades),
}


def _per_metric_ranks(values: list[Optional[float]]) -> list[Optional[int]]:
    """Dense rank: 1 = highest value; None for None inputs.

    Ties get the same rank.
    """
    indexed = [(i, v) for i, v in enumerate(values) if v is not None]
    indexed.sort(key=lambda iv: iv[1], reverse=True)
    ranks: list[Optional[int]] = [None] * len(values)
    last_value: Optional[float] = None
    rank_counter = 0
    next_rank = 1
    for original_idx, value in indexed:
        if last_value is None or value != last_value:
            rank_counter = next_rank
            last_value = value
        ranks[original_idx] = rank_counter
        next_rank += 1
    return ranks


def _diagnostic_hints(records: Sequence[StrategyComparisonRecord]) -> tuple[str, ...]:
    hints: list[str] = []
    n = len(records)
    if n == 0:
        return tuple()
    missing_pf = sum(1 for r in records if r.profit_factor is None)
    missing_dd = sum(1 for r in records if r.equity_drawdown_pct is None)
    missing_grade = sum(1 for r in records if r.walk_forward_grade is None)
    missing_recency = sum(1 for r in records if r.imported_at_iso is None)
    if missing_pf:
        hints.append(f"{missing_pf} of {n} records lack profit-factor data — composite may be biased.")
    if missing_dd:
        hints.append(f"{missing_dd} of {n} records lack drawdown data — composite may be biased.")
    if missing_grade:
        hints.append(f"{missing_grade} of {n} records lack walk-forward grade — composite may be biased.")
    if missing_recency:
        hints.append(f"{missing_recency} of {n} records lack timestamp data — recency score defaulted.")
    all_none = sum(
        1
        for r in records
        if r.profit_factor is None
        and r.equity_drawdown_pct is None
        and r.walk_forward_grade is None
        and r.total_trades is None
        and r.imported_at_iso is None
    )
    if all_none:
        hints.append(f"{all_none} of {n} records have no scored fields and are unranked.")
    return tuple(hints)


def _plain_english_summary(records: Sequence[StrategyComparisonRecord]) -> str:
    if not records:
        return "No strategy records were normalized. The ranking report is empty."
    by_source: dict[str, int] = {}
    for r in records:
        by_source[r.source] = by_source.get(r.source, 0) + 1
    parts = [f"{count} {name}" for name, count in sorted(by_source.items())]
    sources_text = ", ".join(parts)
    return (
        f"Normalized {len(records)} strategy records ({sources_text}). "
        "Records are ordered by a weighted composite of profit factor, drawdown, "
        "walk-forward grade, recency, and trade count. The composite is observational "
        "evidence only; final selection is the operator's call."
    )


def rank_strategies(
    records: Sequence[StrategyComparisonRecord],
    *,
    weights: Optional[Mapping[str, float]] = None,
    now: Optional[datetime] = None,
) -> StrategyRankingReport:
    """Compute per-metric ranks + composite score for the given records."""

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    used_weights = dict(DEFAULT_WEIGHTS)
    if weights:
        for key, val in weights.items():
            used_weights[key] = float(val)
    weight_sum = sum(v for v in used_weights.values() if v > 0)

    # Compute per-metric normalized values for each record.
    metric_names = list(used_weights.keys())
    normalized_per_metric: dict[str, list[Optional[float]]] = {
        name: [] for name in metric_names
    }
    for rec in records:
        for name in metric_names:
            fn = _METRIC_NORMALIZERS.get(name)
            val = fn(rec, now) if fn is not None else None
            normalized_per_metric[name].append(val)

    # Per-metric ranks across the record list.
    ranks_per_metric: dict[str, list[Optional[int]]] = {
        name: _per_metric_ranks(values) for name, values in normalized_per_metric.items()
    }

    # Build StrategyComparisonRecord copies with metrics + composite filled.
    scored: list[tuple[StrategyComparisonRecord, float, bool]] = []
    for idx, rec in enumerate(records):
        metrics: list[RankingMetric] = []
        raw_composite = 0.0
        any_metric = False
        for name in metric_names:
            value = normalized_per_metric[name][idx]
            rank = ranks_per_metric[name][idx]
            if value is None:
                metrics.append(RankingMetric(name=name, value=0.0, rank=None))
                continue
            any_metric = True
            metrics.append(RankingMetric(name=name, value=float(value), rank=rank))
            weight = used_weights.get(name, 0.0)
            if weight > 0:
                raw_composite += value * weight
        composite_score = 0.0
        if any_metric and weight_sum > 0:
            composite_score = (raw_composite / weight_sum) * 100.0
            composite_score = max(0.0, min(composite_score, 100.0))
        new_rec = StrategyComparisonRecord(
            strategy_id=rec.strategy_id,
            source=rec.source,
            symbol=rec.symbol,
            timeframe=rec.timeframe,
            family=rec.family,
            profit_factor=rec.profit_factor,
            equity_drawdown_pct=rec.equity_drawdown_pct,
            walk_forward_grade=rec.walk_forward_grade,
            total_trades=rec.total_trades,
            history_quality=rec.history_quality,
            metrics=tuple(metrics),
            composite_score=round(composite_score, 6) if any_metric else 0.0,
            composite_rank=None,
            imported_at_iso=rec.imported_at_iso,
        )
        scored.append((new_rec, composite_score if any_metric else 0.0, any_metric))

    # Sort: any_metric=True first, then by composite desc, then stable by strategy_id.
    scored.sort(
        key=lambda triple: (
            0 if triple[2] else 1,
            -triple[1],
            triple[0].strategy_id,
        )
    )

    # Assign composite_rank: dense rank by composite_score for any_metric rows;
    # all-None rows get None.
    final_records: list[StrategyComparisonRecord] = []
    last_score: Optional[float] = None
    current_rank = 0
    next_rank = 1
    for rec, score, any_metric in scored:
        if not any_metric:
            final_records.append(rec)
            continue
        if last_score is None or score != last_score:
            current_rank = next_rank
            last_score = score
        ranked_rec = StrategyComparisonRecord(
            strategy_id=rec.strategy_id,
            source=rec.source,
            symbol=rec.symbol,
            timeframe=rec.timeframe,
            family=rec.family,
            profit_factor=rec.profit_factor,
            equity_drawdown_pct=rec.equity_drawdown_pct,
            walk_forward_grade=rec.walk_forward_grade,
            total_trades=rec.total_trades,
            history_quality=rec.history_quality,
            metrics=rec.metrics,
            composite_score=rec.composite_score,
            composite_rank=current_rank,
            imported_at_iso=rec.imported_at_iso,
        )
        final_records.append(ranked_rec)
        next_rank += 1

    summary = _plain_english_summary(final_records)
    hints = _diagnostic_hints(final_records)
    return StrategyRankingReport(
        generated_at_iso=now.isoformat(),
        record_count=len(final_records),
        records=tuple(final_records),
        plain_english_summary=summary,
        diagnostic_hints=hints,
    )


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


_DIFF_FIELDS = (
    "source",
    "symbol",
    "timeframe",
    "family",
    "profit_factor",
    "equity_drawdown_pct",
    "walk_forward_grade",
    "total_trades",
    "history_quality",
)


def _format_value(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, float):
        if math.isnan(value):
            return "missing"
        return f"{value:.4g}"
    return str(value)


def _plain_english_diff(
    a: StrategyComparisonRecord,
    b: StrategyComparisonRecord,
    field_diffs: Sequence[Mapping[str, Any]],
) -> str:
    if not field_diffs:
        return (
            f"Records {a.strategy_id} and {b.strategy_id} match on every compared "
            "field. No observational differences to report."
        )
    diff_field_names = [str(d["field"]) for d in field_diffs]
    field_text = ", ".join(diff_field_names)
    # Specific observational sentence on profit_factor / drawdown when present.
    extras: list[str] = []
    if a.profit_factor is not None and b.profit_factor is not None and a.profit_factor != b.profit_factor:
        extras.append(
            f"Profit factor reads {_format_value(a.profit_factor)} for {a.strategy_id} versus "
            f"{_format_value(b.profit_factor)} for {b.strategy_id}."
        )
    if (
        a.equity_drawdown_pct is not None
        and b.equity_drawdown_pct is not None
        and a.equity_drawdown_pct != b.equity_drawdown_pct
    ):
        extras.append(
            f"Equity drawdown reads {_format_value(a.equity_drawdown_pct)}% for {a.strategy_id} "
            f"versus {_format_value(b.equity_drawdown_pct)}% for {b.strategy_id}."
        )
    head = (
        f"Records {a.strategy_id} and {b.strategy_id} differ on {len(field_diffs)} field(s): "
        f"{field_text}."
    )
    tail = " ".join(extras)
    closer = "The operator owns interpretation; this diff is observational evidence only."
    return f"{head} {tail} {closer}".strip()


def diff_strategies(
    record_a: StrategyComparisonRecord,
    record_b: StrategyComparisonRecord,
) -> StrategyDiff:
    """Compare two normalized records and emit field-level + plain-English diffs."""

    field_diffs: list[Mapping[str, Any]] = []
    for fld in _DIFF_FIELDS:
        a_value = getattr(record_a, fld)
        b_value = getattr(record_b, fld)
        if a_value != b_value:
            field_diffs.append(
                {
                    "field": fld,
                    "a_value": a_value,
                    "b_value": b_value,
                }
            )
    symbol_match = record_a.symbol == record_b.symbol and record_a.symbol is not None
    timeframe_match = record_a.timeframe == record_b.timeframe and record_a.timeframe is not None
    family_match = record_a.family == record_b.family and record_a.family is not None
    plain = _plain_english_diff(record_a, record_b, field_diffs)
    return StrategyDiff(
        strategy_id_a=record_a.strategy_id,
        strategy_id_b=record_b.strategy_id,
        symbol_match=symbol_match,
        timeframe_match=timeframe_match,
        family_match=family_match,
        field_diffs=tuple(field_diffs),
        plain_english_diff=plain,
    )


__all__ = [
    "DEFAULT_WEIGHTS",
    "RankingMetric",
    "StrategyComparisonRecord",
    "StrategyDiff",
    "StrategyRankingReport",
    "diff_strategies",
    "normalize_records",
    "rank_strategies",
]
