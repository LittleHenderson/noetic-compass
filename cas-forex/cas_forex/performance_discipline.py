"""Performance-reporting discipline checks for strategy evidence.

The goal is to keep strategy/backtest surfaces professionally honest. This
module does not calculate a new edge and does not rank strategies. It inspects
the evidence already present and reports whether each record has the fields a
serious performance report should expose: costs, drawdown, sample size,
risk-adjusted metrics, out-of-sample/walk-forward status, Monte Carlo, and
paper/demo/live separation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


REPORT_KIND = "cas_forex_performance_discipline"
CLAIM_BOUNDARY = (
    "Performance discipline is a read-only evidence coverage report. It does "
    "not calculate a new edge, recommend a strategy, authorize trading, place "
    "orders, or imply that past paper, demo, live, or backtest performance will "
    "continue."
)


@dataclass(frozen=True)
class Requirement:
    key: str
    label: str
    aliases: tuple[str, ...]
    critical: bool = True


REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement(
        "net_return_after_costs",
        "Net Return After Costs",
        (
            "net_return_after_costs",
            "net_return_after_costs_pct",
            "net_return_pct",
            "net_pnl",
            "net_pnl_usd",
            "total_net_profit",
            "net_profit",
        ),
    ),
    Requirement(
        "cost_model",
        "Spread / Slippage / Commission / Swap",
        (
            "spread",
            "spread_pips",
            "spread_cost_usd",
            "edge_cost_pips",
            "slippage",
            "slippage_pips",
            "slippage_buffer_pips",
            "commission",
            "commission_usd",
            "swap",
            "swap_usd",
            "rollover",
            "rollover_usd",
        ),
    ),
    Requirement(
        "max_drawdown",
        "Max Drawdown",
        (
            "max_drawdown_pct",
            "equity_drawdown_pct",
            "equity_drawdown_relative_pct",
            "routed_max_drawdown_pct",
            "max_dd_pct",
        ),
    ),
    Requirement(
        "sample_size",
        "Sample Size",
        ("total_trades", "trade_count", "closed_trade_count", "sample_count", "n_trades"),
    ),
    Requirement(
        "win_loss_quality",
        "Win/Loss Quality",
        (
            "win_rate",
            "win_rate_pct",
            "profit_factor",
            "average_win",
            "avg_win",
            "average_loss",
            "avg_loss",
            "average_r_multiple",
            "expectancy",
            "expectancy_usd",
        ),
    ),
    Requirement(
        "risk_adjusted",
        "Risk-Adjusted Metrics",
        ("sharpe", "sharpe_ratio", "sortino", "sortino_ratio"),
        critical=False,
    ),
    Requirement(
        "worst_period",
        "Worst Day / Week / Month",
        (
            "worst_day",
            "worst_day_usd",
            "worst_week",
            "worst_week_usd",
            "worst_month",
            "worst_month_usd",
        ),
        critical=False,
    ),
    Requirement(
        "out_of_sample",
        "Out-Of-Sample / Walk-Forward",
        (
            "out_of_sample",
            "oos",
            "oos_result",
            "walk_forward",
            "walk_forward_grade",
            "walk_forward_result",
            "forward_window",
        ),
    ),
    Requirement(
        "monte_carlo",
        "Monte Carlo / Robustness",
        ("monte_carlo", "monte_carlo_drawdown", "robustness", "bootstrap", "permutation"),
        critical=False,
    ),
    Requirement(
        "mode_separation",
        "Paper / Demo / Live Separation",
        (
            "account_mode",
            "mode",
            "environment",
            "paper",
            "demo",
            "live",
            "source",
            "is_live",
            "is_demo",
        ),
    ),
)


def build_performance_discipline_report(
    *,
    fury_candidates: Sequence[Mapping[str, Any]] | None = None,
    strategy_leads: Sequence[Mapping[str, Any]] | None = None,
    strategy_dev_queue_items: Sequence[Mapping[str, Any]] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    rows = _source_rows(
        fury_candidates=fury_candidates,
        strategy_leads=strategy_leads,
        strategy_dev_queue_items=strategy_dev_queue_items,
    )
    if limit is not None:
        rows = rows[: max(0, int(limit))]
    record_reports = [_record_report(row) for row in rows]
    critical_rows = [row for row in record_reports if row["critical_missing_count"] > 0]
    coverage = _requirement_coverage(record_reports)
    return {
        "report_kind": REPORT_KIND,
        "status": "ATTENTION" if critical_rows or not record_reports else "OK",
        "record_count": len(record_reports),
        "attention_count": len(critical_rows),
        "requirements": [
            {
                "key": req.key,
                "label": req.label,
                "critical": req.critical,
                "aliases": list(req.aliases),
            }
            for req in REQUIREMENTS
        ],
        "coverage": coverage,
        "records": record_reports,
        "plain_english_summary": _summary(record_reports, critical_rows),
        "diagnostic_hints": _diagnostic_hints(record_reports),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _source_rows(
    *,
    fury_candidates: Sequence[Mapping[str, Any]] | None,
    strategy_leads: Sequence[Mapping[str, Any]] | None,
    strategy_dev_queue_items: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source, items in (
        ("forex_fury_candidate", fury_candidates),
        ("strategy_lead", strategy_leads),
        ("strategy_dev_queue", strategy_dev_queue_items),
    ):
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
            continue
        for item in items:
            if isinstance(item, Mapping):
                rows.append({"source": source, "payload": dict(item)})
    return rows


def _record_report(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
    source = str(row.get("source") or _pick(payload, "source") or "unknown")
    flat = {"source": source, **_flatten(payload)}
    strategy_id = _strategy_id(source, payload)
    mode = _mode_label(source, flat)
    checks = [_requirement_check(req, flat) for req in REQUIREMENTS]
    critical_missing = [
        check["key"]
        for check, req in zip(checks, REQUIREMENTS)
        if req.critical and check["status"] != "COVERED"
    ]
    covered_count = sum(1 for check in checks if check["status"] == "COVERED")
    coverage_pct = round((covered_count / len(REQUIREMENTS)) * 100.0, 1) if REQUIREMENTS else 0.0
    return {
        "strategy_id": strategy_id,
        "source": source,
        "mode_label": mode,
        "status": "ATTENTION" if critical_missing else "OK",
        "covered_count": covered_count,
        "requirement_count": len(REQUIREMENTS),
        "coverage_pct": coverage_pct,
        "critical_missing_count": len(critical_missing),
        "critical_missing": critical_missing,
        "checks": checks,
        "cost_model_present": _check_by_key(checks, "cost_model")["status"] == "COVERED",
        "out_of_sample_present": _check_by_key(checks, "out_of_sample")["status"] == "COVERED",
        "mode_separation_present": _check_by_key(checks, "mode_separation")["status"] == "COVERED",
    }


def _requirement_check(req: Requirement, flat: Mapping[str, Any]) -> dict[str, Any]:
    matched = [alias for alias in req.aliases if _has_value(flat.get(alias))]
    return {
        "key": req.key,
        "label": req.label,
        "status": "COVERED" if matched else "MISSING",
        "matched_fields": matched[:6],
        "critical": req.critical,
    }


def _requirement_coverage(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for req in REQUIREMENTS:
        covered = 0
        for record in records:
            check = _check_by_key(record.get("checks") or [], req.key)
            if check.get("status") == "COVERED":
                covered += 1
        pct = round((covered / len(records)) * 100.0, 1) if records else 0.0
        rows.append(
            {
                "key": req.key,
                "label": req.label,
                "critical": req.critical,
                "covered_count": covered,
                "record_count": len(records),
                "coverage_pct": pct,
                "status": "OK" if covered == len(records) and records else "ATTENTION",
            }
        )
    return rows


def _check_by_key(checks: Iterable[Any], key: str) -> Mapping[str, Any]:
    for check in checks:
        if isinstance(check, Mapping) and check.get("key") == key:
            return check
    return {}


def _summary(records: Sequence[Mapping[str, Any]], critical_rows: Sequence[Mapping[str, Any]]) -> str:
    if not records:
        return "No strategy performance records were loaded, so performance discipline cannot be assessed."
    if not critical_rows:
        return (
            f"{len(records)} strategy performance record(s) include the critical "
            "fields needed for cost-aware, mode-separated review."
        )
    return (
        f"{len(critical_rows)} of {len(records)} strategy performance record(s) "
        "are missing at least one critical performance-reporting field."
    )


def _diagnostic_hints(records: Sequence[Mapping[str, Any]]) -> list[str]:
    if not records:
        return ["Load strategy leads, replay candidates, or strategy-dev items before comparing performance discipline."]
    hints: list[str] = []
    for record in records[:8]:
        missing = record.get("critical_missing") if isinstance(record.get("critical_missing"), list) else []
        if missing:
            hints.append(
                f"{record.get('strategy_id')} missing critical fields: {', '.join(str(item) for item in missing)}."
            )
    if not hints:
        hints.append("All loaded records cover critical performance fields; optional robustness fields may still be incomplete.")
    return hints


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = _normalize_key(str(raw_key))
            full = f"{prefix}_{key}" if prefix else key
            out[full] = raw_value
            if key not in out:
                out[key] = raw_value
            if isinstance(raw_value, Mapping):
                out.update(_flatten(raw_value, full))
                for child_key, child_value in _flatten(raw_value).items():
                    out.setdefault(child_key, child_value)
    return out


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set, frozenset)):
        return bool(value)
    return True


def _strategy_id(source: str, payload: Mapping[str, Any]) -> str:
    for key in ("candidate_id", "lead_id", "strategy_lead_id", "work_item_id", "item_id", "strategy_id", "id"):
        value = _pick(payload, key)
        if _has_value(value):
            return str(value)
    return f"{source}:unknown"


def _mode_label(source: str, flat: Mapping[str, Any]) -> str:
    for key in ("account_mode", "mode", "environment"):
        value = str(flat.get(key) or "").strip().upper()
        if value in {"LIVE", "DEMO", "PAPER", "PAPER_DEMO", "BACKTEST", "RESEARCH"}:
            return value
    if any(bool(flat.get(key)) for key in ("is_live", "live")):
        return "LIVE"
    if any(bool(flat.get(key)) for key in ("is_demo", "demo")):
        return "DEMO"
    if "fury" in source or "lead" in source or "dev" in source:
        return "RESEARCH/BACKTEST"
    return "UNKNOWN"


def _pick(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None
