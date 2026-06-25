"""Unit tests for cas_forex.strategy_comparison.

Covers normalization from each of the 3 sources, ranking with default +
custom weights, composite_rank=None for all-None records, ties stable-sorted,
diff field-listing, and forbidden-phrase enforcement on all plain-English
text emitted by the module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cas_forex.strategy_comparison import (
    DEFAULT_WEIGHTS,
    StrategyComparisonRecord,
    diff_strategies,
    normalize_records,
    rank_strategies,
)


FORBIDDEN_PHRASES = [
    "you should pick",
    "pick a",
    "pick b",
    "is a better trade",
    "we recommend",
    "good choice",
    "is the winner",
    "go with",
    "should buy",
    "should sell",
]


def _fury_candidate(**overrides):
    base = {
        "candidate_id": "ff-replay-aud-cad-m5-swing-d7be2c38ca",
        "cas_symbol": "AUD/CAD",
        "raw_symbol": "AUDCAD",
        "family": "swing",
        "evidence": {
            "profit_factor": 3.2,
            "equity_drawdown_relative_pct": 5.0,
            "total_trades": 294,
            "history_quality": "98%",
        },
        "replay_job": {"timeframes": ["M5"]},
        "imported_at_iso": "2026-06-20T00:00:00+00:00",
        "walk_forward_grade": "WATCH",
    }
    base.update(overrides)
    return base


def _strategy_lead(**overrides):
    base = {
        "lead_id": "range_scalper_filtered_fx_d1",
        "family": "range_scalper",
        "symbols_promoted_for_next_tests": ["EUR/USD", "GBP/USD"],
        "condition_fit": {"preferred_timeframes": ["D1", "H1"]},
        "profit_factor": 1.8,
        "equity_drawdown_pct": 2.38,
        "walk_forward_grade": "WALK_FORWARD_LEAD",
        "total_trades": 120,
        "history_quality": "broker_grade",
        "imported_at_iso": "2026-06-22T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _dev_queue_item(**overrides):
    base = {
        "work_item_id": "strategy-dev-terminal-joinback-7c441e3221a2bdce",
        "families": ["forex_fury"],
        "symbols": ["EUR/USD"],
        "timeframes": ["H1"],
        "profit_factor": 2.5,
        "equity_drawdown_pct": 8.0,
        "walk_forward_grade": "WATCH",
        "total_trades": 60,
        "history_quality": "demo_grade",
        "created_at": "2026-06-24T10:29:00+00:00",
    }
    base.update(overrides)
    return base


NOW = datetime(2026, 6, 25, 0, 0, 0, tzinfo=timezone.utc)


def _all_text(report):
    chunks = [report.plain_english_summary]
    chunks.extend(report.diagnostic_hints)
    return " | ".join(chunks).lower()


def _assert_no_forbidden(text: str):
    lowered = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in lowered, f"forbidden phrase {phrase!r} found in: {text!r}"


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_normalize_fury_candidate_extracts_core_fields():
    records = normalize_records(fury_candidates=[_fury_candidate()])
    assert len(records) == 1
    rec = records[0]
    assert rec.strategy_id == "ff-replay-aud-cad-m5-swing-d7be2c38ca"
    assert rec.source == "forex_fury_candidate"
    assert rec.symbol == "AUD/CAD"
    assert rec.timeframe == "M5"
    assert rec.family == "swing"
    assert rec.profit_factor == 3.2
    assert rec.equity_drawdown_pct == 5.0
    assert rec.total_trades == 294
    assert rec.history_quality == "98%"
    assert rec.walk_forward_grade == "WATCH"


def test_normalize_strategy_lead_uses_condition_fit_timeframe_and_symbol_list():
    records = normalize_records(strategy_leads=[_strategy_lead()])
    assert len(records) == 1
    rec = records[0]
    assert rec.source == "strategy_lead"
    assert rec.symbol == "EUR/USD"
    assert rec.timeframe == "D1"
    assert rec.family == "range_scalper"
    assert rec.walk_forward_grade == "WALK_FORWARD_LEAD"


def test_normalize_dev_queue_item_picks_first_family_and_timeframe():
    records = normalize_records(strategy_dev_queue_items=[_dev_queue_item()])
    assert len(records) == 1
    rec = records[0]
    assert rec.source == "strategy_dev_queue"
    assert rec.family == "forex_fury"
    assert rec.timeframe == "H1"
    assert rec.symbol == "EUR/USD"


def test_normalize_drops_records_without_id_and_tolerates_non_mapping():
    records = normalize_records(
        fury_candidates=[{"evidence": {"profit_factor": 1.0}}, None, "garbage"],  # type: ignore[list-item]
        strategy_leads=[{"family": "x"}],
        strategy_dev_queue_items=[{}],
    )
    assert records == ()


def test_normalize_missing_fields_become_none():
    records = normalize_records(strategy_leads=[{"lead_id": "bare"}])
    assert len(records) == 1
    rec = records[0]
    assert rec.profit_factor is None
    assert rec.equity_drawdown_pct is None
    assert rec.walk_forward_grade is None
    assert rec.total_trades is None


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_rank_default_weights_orders_strong_record_first():
    strong = _strategy_lead(
        lead_id="strong",
        profit_factor=4.5,
        equity_drawdown_pct=2.0,
        walk_forward_grade="WALK_FORWARD_LEAD",
        total_trades=500,
        imported_at_iso=NOW.isoformat(),
    )
    weak = _strategy_lead(
        lead_id="weak",
        profit_factor=1.05,
        equity_drawdown_pct=40.0,
        walk_forward_grade="REJECT",
        total_trades=10,
        imported_at_iso=(NOW - timedelta(days=29)).isoformat(),
    )
    records = normalize_records(strategy_leads=[strong, weak])
    report = rank_strategies(records, now=NOW)
    assert report.record_count == 2
    assert report.records[0].strategy_id == "strong"
    assert report.records[0].composite_rank == 1
    assert report.records[1].composite_rank == 2
    assert report.records[0].composite_score > report.records[1].composite_score
    _assert_no_forbidden(_all_text(report))


def test_rank_custom_weights_can_invert_order_by_zeroing_pf():
    # Strong by PF only, weak everywhere else. With zero PF weight, the
    # ranking should flip to favor the other record.
    pf_strong = _strategy_lead(
        lead_id="pf_only",
        profit_factor=4.8,
        equity_drawdown_pct=40.0,
        walk_forward_grade="REJECT",
        total_trades=5,
        imported_at_iso=(NOW - timedelta(days=29)).isoformat(),
    )
    dd_strong = _strategy_lead(
        lead_id="dd_only",
        profit_factor=0.9,
        equity_drawdown_pct=1.0,
        walk_forward_grade="WALK_FORWARD_LEAD",
        total_trades=400,
        imported_at_iso=NOW.isoformat(),
    )
    records = normalize_records(strategy_leads=[pf_strong, dd_strong])
    custom = {
        "profit_factor": 0.0,
        "equity_drawdown_inv": 0.4,
        "walk_forward_grade": 0.4,
        "recency": 0.1,
        "total_trades_log": 0.1,
    }
    report = rank_strategies(records, weights=custom, now=NOW)
    assert report.records[0].strategy_id == "dd_only"


def test_rank_all_none_record_gets_none_rank_and_zero_score():
    bare = {"lead_id": "bare"}
    populated = _strategy_lead(lead_id="populated")
    records = normalize_records(strategy_leads=[bare, populated])
    report = rank_strategies(records, now=NOW)
    by_id = {r.strategy_id: r for r in report.records}
    assert by_id["bare"].composite_rank is None
    assert by_id["bare"].composite_score == 0.0
    assert by_id["populated"].composite_rank == 1
    # Diagnostic hint should mention unranked records.
    assert any("unranked" in hint for hint in report.diagnostic_hints)


def test_rank_ties_break_stably_by_strategy_id():
    a = _strategy_lead(lead_id="aaa")
    b = _strategy_lead(lead_id="bbb")  # identical metrics, just different id
    records = normalize_records(strategy_leads=[b, a])  # input order: bbb first
    report = rank_strategies(records, now=NOW)
    assert [r.strategy_id for r in report.records] == ["aaa", "bbb"]
    assert report.records[0].composite_score == report.records[1].composite_score
    # Ties share rank.
    assert report.records[0].composite_rank == report.records[1].composite_rank == 1


def test_rank_composite_score_clamped_0_to_100():
    rec = _strategy_lead(
        lead_id="extreme",
        profit_factor=99.0,
        equity_drawdown_pct=0.0,
        walk_forward_grade="WALK_FORWARD_LEAD",
        total_trades=10000,
        imported_at_iso=NOW.isoformat(),
    )
    records = normalize_records(strategy_leads=[rec])
    report = rank_strategies(records, now=NOW)
    assert 0.0 <= report.records[0].composite_score <= 100.0


def test_rank_diagnostic_hints_observational_only():
    bare = {"lead_id": "bare"}
    no_dd = _strategy_lead(lead_id="no_dd", equity_drawdown_pct=None)
    records = normalize_records(strategy_leads=[bare, no_dd])
    report = rank_strategies(records, now=NOW)
    text = _all_text(report)
    _assert_no_forbidden(text)


def test_default_weights_sum_to_one():
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


def test_rank_empty_records_returns_empty_report():
    report = rank_strategies((), now=NOW)
    assert report.record_count == 0
    assert report.records == ()
    _assert_no_forbidden(report.plain_english_summary)


def test_rank_metric_per_record_includes_all_default_metric_names():
    rec = _strategy_lead(lead_id="x")
    records = normalize_records(strategy_leads=[rec])
    report = rank_strategies(records, now=NOW)
    names = {m.name for m in report.records[0].metrics}
    assert names == set(DEFAULT_WEIGHTS.keys())


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


def test_diff_lists_each_differing_field():
    a = normalize_records(strategy_leads=[_strategy_lead(lead_id="a", profit_factor=2.0)])[0]
    b = normalize_records(
        strategy_leads=[
            _strategy_lead(
                lead_id="b",
                profit_factor=3.5,
                equity_drawdown_pct=10.0,
                family="meanrev",
            )
        ]
    )[0]
    diff = diff_strategies(a, b)
    fields = [d["field"] for d in diff.field_diffs]
    assert "profit_factor" in fields
    assert "equity_drawdown_pct" in fields
    assert "family" in fields
    assert diff.strategy_id_a == "a"
    assert diff.strategy_id_b == "b"
    _assert_no_forbidden(diff.plain_english_diff)


def test_diff_identical_records_emits_no_field_diffs():
    rec = normalize_records(strategy_leads=[_strategy_lead(lead_id="same")])[0]
    diff = diff_strategies(rec, rec)
    assert diff.field_diffs == ()
    assert "no observational differences" in diff.plain_english_diff.lower()
    _assert_no_forbidden(diff.plain_english_diff)


def test_diff_symbol_and_family_match_flags():
    a = normalize_records(
        strategy_leads=[
            _strategy_lead(
                lead_id="a",
                symbols_promoted_for_next_tests=["EUR/USD"],
                family="range_scalper",
            )
        ]
    )[0]
    b = normalize_records(
        strategy_leads=[
            _strategy_lead(
                lead_id="b",
                symbols_promoted_for_next_tests=["EUR/USD"],
                family="meanrev",
            )
        ]
    )[0]
    diff = diff_strategies(a, b)
    assert diff.symbol_match is True
    assert diff.family_match is False


def test_diff_none_symbol_does_not_count_as_match():
    a = StrategyComparisonRecord(
        strategy_id="a",
        source="strategy_lead",
        symbol=None,
        timeframe=None,
        family=None,
        profit_factor=None,
        equity_drawdown_pct=None,
        walk_forward_grade=None,
        total_trades=None,
        history_quality=None,
    )
    b = StrategyComparisonRecord(
        strategy_id="b",
        source="strategy_lead",
        symbol=None,
        timeframe=None,
        family=None,
        profit_factor=None,
        equity_drawdown_pct=None,
        walk_forward_grade=None,
        total_trades=None,
        history_quality=None,
    )
    diff = diff_strategies(a, b)
    assert diff.symbol_match is False
    assert diff.timeframe_match is False
    assert diff.family_match is False


# ---------------------------------------------------------------------------
# Forbidden phrases — parametrized across ranked + diff outputs
# ---------------------------------------------------------------------------


@pytest.fixture
def _populated_report():
    records = normalize_records(
        fury_candidates=[_fury_candidate()],
        strategy_leads=[_strategy_lead(), {"lead_id": "bare"}],
        strategy_dev_queue_items=[_dev_queue_item()],
    )
    return rank_strategies(records, now=NOW)


@pytest.fixture
def _populated_diff():
    a = normalize_records(strategy_leads=[_strategy_lead(lead_id="alpha")])[0]
    b = normalize_records(strategy_leads=[_strategy_lead(lead_id="bravo", profit_factor=4.5)])[0]
    return diff_strategies(a, b)


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_ranked_report_never_contains_forbidden_phrase(_populated_report, phrase):
    text = _all_text(_populated_report)
    assert phrase not in text, f"phrase {phrase!r} leaked into ranked text: {text!r}"


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_diff_text_never_contains_forbidden_phrase(_populated_diff, phrase):
    text = _populated_diff.plain_english_diff.lower()
    assert phrase not in text, f"phrase {phrase!r} leaked into diff text: {text!r}"
