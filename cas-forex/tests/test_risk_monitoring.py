"""Pure tests for `cas_forex.risk_monitoring`.

These tests pin the observational contract: the snapshot reports the shape
of risk; it NEVER recommends an action. The forbidden-phrase list is
parametrised below — every additional advisory phrase the team wants to
keep out of operator surfaces should be added there.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cas_forex.risk_monitoring import (
    FORBIDDEN_ADVISORY_PHRASES,
    PortfolioRiskSnapshot,
    SymbolRiskExposure,
    compose_portfolio_risk_snapshot,
    snapshot_to_payload,
)


_FIXED_NOW = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)


def _live(positions):
    return {"open_positions": list(positions)}


def _acct(*, balance=None, equity=None, margin=None, free_margin=None):
    return {
        "balance": balance,
        "equity": equity,
        "margin": margin,
        "free_margin": free_margin,
    }


def test_empty_inputs_produce_zero_snapshot_with_explanatory_summary():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=None, account_snapshot=None, now=_FIXED_NOW
    )
    assert isinstance(snap, PortfolioRiskSnapshot)
    assert snap.open_position_count == 0
    assert snap.total_floating_pnl == 0.0
    assert snap.total_exposure_lots == 0.0
    assert snap.by_symbol == ()
    assert snap.largest_symbol_exposure is None
    assert snap.concentration_pct == 0.0
    assert snap.account_balance is None
    assert snap.margin_utilization_pct is None
    assert "no open positions" in snap.plain_english_summary.lower()
    assert snap.diagnostic_hints == ()


def test_single_position_eurusd_buy_one_lot_aggregates_correctly():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=_live([
            {"symbol": "EURUSD", "direction": "BUY", "lots": 0.1, "floating_pnl": 5.0}
        ]),
        account_snapshot=None,
        now=_FIXED_NOW,
    )
    assert snap.open_position_count == 1
    assert len(snap.by_symbol) == 1
    only = snap.by_symbol[0]
    assert only.symbol == "EURUSD"
    assert only.direction == "BUY"
    assert only.open_position_count == 1
    assert only.total_lots == pytest.approx(0.1)
    assert snap.total_exposure_lots == pytest.approx(0.1)
    assert snap.largest_floating_pnl_gain == pytest.approx(5.0)
    assert snap.largest_floating_pnl_loss == 0.0


def test_two_positions_same_symbol_same_direction_aggregate():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=_live([
            {"symbol": "EURUSD", "direction": "BUY", "lots": 0.5, "floating_pnl": 10.0},
            {"symbol": "EURUSD", "direction": "BUY", "lots": 0.3, "floating_pnl": -2.0},
        ]),
        account_snapshot=None,
        now=_FIXED_NOW,
    )
    assert len(snap.by_symbol) == 1
    eur = snap.by_symbol[0]
    assert eur.direction == "BUY"
    assert eur.open_position_count == 2
    assert eur.total_lots == pytest.approx(0.8)
    assert eur.total_floating_pnl == pytest.approx(8.0)
    assert eur.largest_position_lots == pytest.approx(0.5)


def test_two_positions_same_symbol_opposite_direction_yields_mixed():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=_live([
            {"symbol": "USDJPY", "direction": "BUY", "lots": 0.4, "floating_pnl": 1.0},
            {"symbol": "USDJPY", "direction": "SELL", "lots": 0.2, "floating_pnl": -3.0},
        ]),
        account_snapshot=None,
        now=_FIXED_NOW,
    )
    assert len(snap.by_symbol) == 1
    only = snap.by_symbol[0]
    assert only.direction == "MIXED"
    assert only.open_position_count == 2


def test_multiple_symbols_sorted_by_total_lots_descending():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=_live([
            {"symbol": "EURUSD", "direction": "BUY", "lots": 0.2, "floating_pnl": 0.0},
            {"symbol": "GBPUSD", "direction": "BUY", "lots": 1.5, "floating_pnl": 0.0},
            {"symbol": "USDJPY", "direction": "SELL", "lots": 0.7, "floating_pnl": 0.0},
        ]),
        account_snapshot=None,
        now=_FIXED_NOW,
    )
    symbols = [s.symbol for s in snap.by_symbol]
    assert symbols == ["GBPUSD", "USDJPY", "EURUSD"]


def test_largest_symbol_exposure_is_correctly_identified():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=_live([
            {"symbol": "EURUSD", "direction": "BUY", "lots": 0.2, "floating_pnl": 0.0},
            {"symbol": "GBPUSD", "direction": "BUY", "lots": 1.5, "floating_pnl": 0.0},
        ]),
        account_snapshot=None,
        now=_FIXED_NOW,
    )
    assert snap.largest_symbol_exposure is not None
    assert snap.largest_symbol_exposure.symbol == "GBPUSD"
    assert snap.largest_symbol_exposure.total_lots == pytest.approx(1.5)


def test_concentration_pct_is_correct_for_60_40_split():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=_live([
            {"symbol": "EURUSD", "direction": "BUY", "lots": 60.0, "floating_pnl": 0.0},
            {"symbol": "GBPUSD", "direction": "BUY", "lots": 40.0, "floating_pnl": 0.0},
        ]),
        account_snapshot=None,
        now=_FIXED_NOW,
    )
    assert snap.total_exposure_lots == pytest.approx(100.0)
    assert snap.concentration_pct == pytest.approx(60.0)


def test_margin_utilization_pct_is_correct_for_equity_10000_free_4000():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=None,
        account_snapshot=_acct(equity=10000.0, free_margin=4000.0, margin=6000.0, balance=10000.0),
        now=_FIXED_NOW,
    )
    # (1 - 4000/10000) * 100 = 60
    assert snap.margin_utilization_pct == pytest.approx(60.0)
    assert snap.account_equity == pytest.approx(10000.0)
    assert snap.account_free_margin == pytest.approx(4000.0)


def test_margin_utilization_pct_is_none_when_free_margin_missing():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=None,
        account_snapshot=_acct(equity=10000.0, free_margin=None, margin=None, balance=10000.0),
        now=_FIXED_NOW,
    )
    assert snap.margin_utilization_pct is None


def test_concentration_above_60_hint_fires_when_one_symbol_dominates():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=_live([
            {"symbol": "EURUSD", "direction": "BUY", "lots": 80.0, "floating_pnl": 0.0},
            {"symbol": "GBPUSD", "direction": "BUY", "lots": 20.0, "floating_pnl": 0.0},
        ]),
        account_snapshot=None,
        now=_FIXED_NOW,
    )
    hints_joined = " | ".join(snap.diagnostic_hints)
    assert "Concentration above 60% in EURUSD." in hints_joined


def test_margin_utilization_above_50_hint_fires():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=None,
        account_snapshot=_acct(equity=10000.0, free_margin=2000.0, margin=8000.0, balance=10000.0),
        now=_FIXED_NOW,
    )
    assert any("Margin utilization above 50%." == h for h in snap.diagnostic_hints)


def test_all_positions_on_one_symbol_hint_fires_when_only_one_symbol_multiple_positions():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=_live([
            {"symbol": "EURUSD", "direction": "BUY", "lots": 0.2, "floating_pnl": 0.0},
            {"symbol": "EURUSD", "direction": "BUY", "lots": 0.3, "floating_pnl": 0.0},
        ]),
        account_snapshot=None,
        now=_FIXED_NOW,
    )
    assert any("All positions on one symbol." == h for h in snap.diagnostic_hints)


@pytest.mark.parametrize("forbidden", FORBIDDEN_ADVISORY_PHRASES)
def test_summary_and_hints_never_contain_advisory_phrases(forbidden):
    """The summary + hints must never recommend an action — across multiple
    risk shapes (empty / concentrated / margin-stressed / loss-heavy)."""
    fixtures = [
        compose_portfolio_risk_snapshot(
            live_telemetry=None, account_snapshot=None, now=_FIXED_NOW
        ),
        compose_portfolio_risk_snapshot(
            live_telemetry=_live([
                {"symbol": "EURUSD", "direction": "BUY", "lots": 95.0, "floating_pnl": -500.0},
                {"symbol": "GBPUSD", "direction": "BUY", "lots": 5.0, "floating_pnl": -10.0},
            ]),
            account_snapshot=_acct(equity=10000.0, free_margin=500.0, margin=9500.0, balance=10000.0),
            now=_FIXED_NOW,
        ),
        compose_portfolio_risk_snapshot(
            live_telemetry=_live([
                {"symbol": "EURUSD", "direction": "BUY", "lots": 0.1, "floating_pnl": 1500.0},
            ]),
            account_snapshot=_acct(equity=20000.0, free_margin=19500.0, margin=500.0, balance=20000.0),
            now=_FIXED_NOW,
        ),
    ]
    for snap in fixtures:
        haystack = (snap.plain_english_summary + " " + " ".join(snap.diagnostic_hints)).lower()
        assert forbidden not in haystack, (
            f"Forbidden advisory phrase {forbidden!r} found in operator surface: "
            f"summary={snap.plain_english_summary!r} hints={snap.diagnostic_hints!r}"
        )


def test_snapshot_to_payload_is_json_friendly_and_round_trips():
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=_live([
            {"symbol": "EURUSD", "direction": "BUY", "lots": 0.1, "floating_pnl": 5.0},
        ]),
        account_snapshot=_acct(equity=10000.0, free_margin=4000.0, margin=6000.0, balance=10000.0),
        now=_FIXED_NOW,
    )
    payload = snapshot_to_payload(snap)
    assert isinstance(payload["by_symbol"], list)
    assert isinstance(payload["diagnostic_hints"], list)
    assert payload["largest_symbol_exposure"]["symbol"] == "EURUSD"
    # JSON-serialisable
    import json
    assert json.loads(json.dumps(payload))["open_position_count"] == 1


def test_mt5_verifier_shape_account_extraction():
    """The route's default loader passes a raw verifier report through to
    ``account_snapshot``. Confirm the extractor walks probe.receipt.account_snapshot."""
    verifier_report = {
        "probe": {
            "receipt": {
                "account_snapshot": {
                    "balance": 99999.87,
                    "equity": 99999.87,
                    "margin": 0.0,
                    "margin_free": 99999.87,
                }
            }
        }
    }
    snap = compose_portfolio_risk_snapshot(
        live_telemetry=None,
        account_snapshot=verifier_report,
        now=_FIXED_NOW,
    )
    assert snap.account_balance == pytest.approx(99999.87)
    assert snap.account_equity == pytest.approx(99999.87)
    assert snap.account_free_margin == pytest.approx(99999.87)


def test_symbol_risk_exposure_is_frozen_dataclass():
    exp = SymbolRiskExposure(
        symbol="EURUSD",
        direction="BUY",
        open_position_count=1,
        total_lots=0.1,
        total_floating_pnl=0.0,
        largest_position_lots=0.1,
    )
    with pytest.raises(Exception):
        exp.symbol = "GBPUSD"  # type: ignore[misc]
