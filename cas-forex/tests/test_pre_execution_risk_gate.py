"""Tests for the pre-execution risk gate primitive.

The gate is strictly OBSERVATIONAL: it APPROVES or REJECTS a proposed
RouteIntent based on whether the would-be portfolio metrics breach the
operator's configured caps. It must NEVER render trade-advisory
language. The forbidden-phrase list is pinned here.
"""

from __future__ import annotations

import pytest

from cas_forex.pre_execution_risk_gate import (
    DEFAULT_CAPS,
    FORBIDDEN_ADVISORY_PHRASES,
    RiskCapConfig,
    RiskGateDecision,
    decision_to_payload,
    evaluate_proposed_intent,
)


# ---------------------------------------------------------------------------
# Snapshot fixtures (these mirror the shape produced by
# `cas_forex.risk_monitoring.snapshot_to_payload`).
# ---------------------------------------------------------------------------

def _empty_snapshot() -> dict:
    return {
        "open_position_count": 0,
        "total_floating_pnl": 0.0,
        "total_exposure_lots": 0.0,
        "concentration_pct": 0.0,
        "by_symbol": [],
        "account_balance": 10_000.0,
        "account_equity": 10_000.0,
        "account_margin": 0.0,
        "account_free_margin": 10_000.0,
        "margin_utilization_pct": 0.0,
    }


def _populated_snapshot(
    *,
    total_lots: float = 1.0,
    eurusd_lots: float = 1.0,
    eurusd_count: int = 1,
    open_count: int = 1,
    equity: float = 10_000.0,
    free_margin: float = 9_000.0,
    margin_util: float = 10.0,
    floating_pnl: float = 0.0,
) -> dict:
    by_symbol = [
        {
            "symbol": "EURUSD",
            "direction": "BUY",
            "open_position_count": eurusd_count,
            "total_lots": eurusd_lots,
            "total_floating_pnl": floating_pnl,
            "largest_position_lots": eurusd_lots,
        }
    ]
    return {
        "open_position_count": open_count,
        "total_floating_pnl": floating_pnl,
        "total_exposure_lots": total_lots,
        "concentration_pct": round(
            (eurusd_lots / total_lots * 100.0) if total_lots > 0 else 0.0, 2
        ),
        "by_symbol": by_symbol,
        "account_balance": equity,
        "account_equity": equity,
        "account_margin": equity - free_margin,
        "account_free_margin": free_margin,
        "margin_utilization_pct": margin_util,
    }


_BASE_INTENT = {"symbol": "EURUSD", "direction": "BUY", "lots": 0.10}


# ---------------------------------------------------------------------------
# 1. PASS when all caps are None.
# ---------------------------------------------------------------------------

def test_pass_when_all_caps_none() -> None:
    caps = RiskCapConfig(
        max_total_exposure_lots=None,
        max_concentration_pct=None,
        max_margin_utilization_pct=None,
        max_positions_per_symbol=None,
        max_open_position_count=None,
        max_drawdown_pct_from_equity_peak=None,
        max_floating_loss_usd=None,
    )
    decision = evaluate_proposed_intent(
        proposed_intent=_BASE_INTENT,
        portfolio_snapshot=_populated_snapshot(
            total_lots=999.0, eurusd_lots=999.0, eurusd_count=99, open_count=99
        ),
        caps=caps,
    )
    assert decision.accepted is True
    assert decision.decision == "PASS"
    assert decision.blocking_caps == ()
    assert "Within configured caps" in decision.plain_english_reason


# ---------------------------------------------------------------------------
# 2. PASS when proposed intent fits within all caps.
# ---------------------------------------------------------------------------

def test_pass_when_intent_fits_default_caps() -> None:
    # Diversified existing book: 0.5 EUR + 0.5 GBP.
    snapshot = {
        "open_position_count": 2,
        "total_floating_pnl": 0.0,
        "total_exposure_lots": 1.0,
        "concentration_pct": 50.0,
        "by_symbol": [
            {
                "symbol": "EURUSD",
                "direction": "BUY",
                "open_position_count": 1,
                "total_lots": 0.5,
                "total_floating_pnl": 0.0,
                "largest_position_lots": 0.5,
            },
            {
                "symbol": "GBPUSD",
                "direction": "BUY",
                "open_position_count": 1,
                "total_lots": 0.5,
                "total_floating_pnl": 0.0,
                "largest_position_lots": 0.5,
            },
        ],
        "account_balance": 10_000.0,
        "account_equity": 10_000.0,
        "account_margin": 1_000.0,
        "account_free_margin": 9_000.0,
        "margin_utilization_pct": 10.0,
    }
    decision = evaluate_proposed_intent(
        proposed_intent={"symbol": "USDJPY", "direction": "BUY", "lots": 0.10},
        portfolio_snapshot=snapshot,
        caps=DEFAULT_CAPS,
    )
    assert decision.accepted is True
    assert decision.decision == "PASS"
    assert decision.blocking_caps == ()
    assert decision.proposed_intent_summary == "BUY USDJPY 0.10 lots"


# ---------------------------------------------------------------------------
# 3. REJECT on total exposure.
# ---------------------------------------------------------------------------

def test_reject_on_total_exposure_cap() -> None:
    snapshot = _populated_snapshot(
        total_lots=9.95, eurusd_lots=9.95, eurusd_count=1, open_count=1
    )
    decision = evaluate_proposed_intent(
        proposed_intent={"symbol": "GBPUSD", "direction": "BUY", "lots": 1.0},
        portfolio_snapshot=snapshot,
        caps=DEFAULT_CAPS,
    )
    assert decision.accepted is False
    assert decision.decision == "REJECT"
    assert "max_total_exposure_lots" in decision.blocking_caps


# ---------------------------------------------------------------------------
# 4. REJECT on concentration; would-be concentration computed correctly.
# ---------------------------------------------------------------------------

def test_reject_on_concentration_cap_with_correct_calc() -> None:
    # Existing: 1.0 lot on EURUSD. Total exposure 2.0 (1 EUR + 1 other).
    snapshot = {
        "open_position_count": 2,
        "total_floating_pnl": 0.0,
        "total_exposure_lots": 2.0,
        "concentration_pct": 50.0,
        "by_symbol": [
            {
                "symbol": "EURUSD",
                "direction": "BUY",
                "open_position_count": 1,
                "total_lots": 1.0,
                "total_floating_pnl": 0.0,
                "largest_position_lots": 1.0,
            },
            {
                "symbol": "GBPUSD",
                "direction": "BUY",
                "open_position_count": 1,
                "total_lots": 1.0,
                "total_floating_pnl": 0.0,
                "largest_position_lots": 1.0,
            },
        ],
        "account_balance": 10_000.0,
        "account_equity": 10_000.0,
        "account_margin": 1_000.0,
        "account_free_margin": 9_000.0,
        "margin_utilization_pct": 10.0,
    }
    # Add 5.0 lots EURUSD -> EURUSD would be 6/7 = 85.7%, cap 70%.
    caps = RiskCapConfig(
        max_total_exposure_lots=None,
        max_concentration_pct=70.0,
        max_margin_utilization_pct=None,
        max_positions_per_symbol=None,
        max_open_position_count=None,
        max_drawdown_pct_from_equity_peak=None,
        max_floating_loss_usd=None,
    )
    decision = evaluate_proposed_intent(
        proposed_intent={"symbol": "EURUSD", "direction": "BUY", "lots": 5.0},
        portfolio_snapshot=snapshot,
        caps=caps,
    )
    assert decision.accepted is False
    assert "max_concentration_pct" in decision.blocking_caps
    # 6 / 7 ~ 86%; reason must mention the would-be number.
    assert "86%" in decision.plain_english_reason or "85" in decision.plain_english_reason


# ---------------------------------------------------------------------------
# 5. REJECT on margin utilization (uses snapshot's util).
# ---------------------------------------------------------------------------

def test_reject_on_margin_utilization_cap() -> None:
    snapshot = _populated_snapshot(
        total_lots=1.0,
        eurusd_lots=1.0,
        eurusd_count=1,
        open_count=1,
        equity=10_000.0,
        free_margin=2_000.0,
        margin_util=80.0,
    )
    caps = RiskCapConfig(
        max_total_exposure_lots=None,
        max_concentration_pct=None,
        max_margin_utilization_pct=70.0,
        max_positions_per_symbol=None,
        max_open_position_count=None,
        max_drawdown_pct_from_equity_peak=None,
        max_floating_loss_usd=None,
    )
    decision = evaluate_proposed_intent(
        proposed_intent=_BASE_INTENT,
        portfolio_snapshot=snapshot,
        caps=caps,
    )
    assert decision.accepted is False
    assert "max_margin_utilization_pct" in decision.blocking_caps


# ---------------------------------------------------------------------------
# 6. REJECT on positions-per-symbol.
# ---------------------------------------------------------------------------

def test_reject_on_positions_per_symbol_cap() -> None:
    snapshot = _populated_snapshot(
        total_lots=5.0, eurusd_lots=5.0, eurusd_count=5, open_count=5
    )
    caps = RiskCapConfig(
        max_total_exposure_lots=None,
        max_concentration_pct=None,
        max_margin_utilization_pct=None,
        max_positions_per_symbol=5,
        max_open_position_count=None,
        max_drawdown_pct_from_equity_peak=None,
        max_floating_loss_usd=None,
    )
    decision = evaluate_proposed_intent(
        proposed_intent=_BASE_INTENT,  # EURUSD; would become 6th position
        portfolio_snapshot=snapshot,
        caps=caps,
    )
    assert decision.accepted is False
    assert "max_positions_per_symbol" in decision.blocking_caps


# ---------------------------------------------------------------------------
# 7. REJECT on open-position-count.
# ---------------------------------------------------------------------------

def test_reject_on_open_position_count_cap() -> None:
    snapshot = _populated_snapshot(
        total_lots=5.0, eurusd_lots=5.0, eurusd_count=5, open_count=20
    )
    caps = RiskCapConfig(
        max_total_exposure_lots=None,
        max_concentration_pct=None,
        max_margin_utilization_pct=None,
        max_positions_per_symbol=None,
        max_open_position_count=20,
        max_drawdown_pct_from_equity_peak=None,
        max_floating_loss_usd=None,
    )
    decision = evaluate_proposed_intent(
        proposed_intent={"symbol": "GBPUSD", "direction": "BUY", "lots": 0.1},
        portfolio_snapshot=snapshot,
        caps=caps,
    )
    assert decision.accepted is False
    assert "max_open_position_count" in decision.blocking_caps


# ---------------------------------------------------------------------------
# 8. REJECT on drawdown vs equity_peak.
# ---------------------------------------------------------------------------

def test_reject_on_drawdown_cap() -> None:
    # equity 8_000, peak 10_000 -> 20% drawdown, cap 15%.
    snapshot = _populated_snapshot(
        total_lots=1.0,
        eurusd_lots=1.0,
        eurusd_count=1,
        open_count=1,
        equity=8_000.0,
        free_margin=7_000.0,
        margin_util=12.5,
    )
    caps = RiskCapConfig(
        max_total_exposure_lots=None,
        max_concentration_pct=None,
        max_margin_utilization_pct=None,
        max_positions_per_symbol=None,
        max_open_position_count=None,
        max_drawdown_pct_from_equity_peak=15.0,
        max_floating_loss_usd=None,
    )
    decision = evaluate_proposed_intent(
        proposed_intent=_BASE_INTENT,
        portfolio_snapshot=snapshot,
        caps=caps,
        equity_peak=10_000.0,
    )
    assert decision.accepted is False
    assert "max_drawdown_pct_from_equity_peak" in decision.blocking_caps


# ---------------------------------------------------------------------------
# 9. REJECT lists multiple blocking caps.
# ---------------------------------------------------------------------------

def test_reject_lists_multiple_blocking_caps() -> None:
    snapshot = _populated_snapshot(
        total_lots=9.5,
        eurusd_lots=9.5,
        eurusd_count=5,
        open_count=20,
        equity=8_000.0,
        free_margin=2_000.0,
        margin_util=75.0,
    )
    caps = DEFAULT_CAPS  # all engaged
    decision = evaluate_proposed_intent(
        proposed_intent={"symbol": "EURUSD", "direction": "BUY", "lots": 1.0},
        portfolio_snapshot=snapshot,
        caps=caps,
        equity_peak=10_000.0,
    )
    assert decision.accepted is False
    # At least two of these should fire: total_exposure, concentration,
    # margin_utilization, positions_per_symbol, open_position_count,
    # drawdown.
    assert len(decision.blocking_caps) >= 2


# ---------------------------------------------------------------------------
# 10. Direction: opposing direction still counted toward exposure.
# ---------------------------------------------------------------------------

def test_opposing_direction_still_counts_toward_exposure() -> None:
    # Existing BUY 9.5 lot EURUSD. Propose a SELL 1.0 lot EURUSD.
    # If direction-netted, total would be 8.5; if abs-summed, 10.5.
    # The gate must use abs-summed (matches risk_monitoring).
    snapshot = _populated_snapshot(
        total_lots=9.5, eurusd_lots=9.5, eurusd_count=1, open_count=1
    )
    caps = RiskCapConfig(
        max_total_exposure_lots=10.0,
        max_concentration_pct=None,
        max_margin_utilization_pct=None,
        max_positions_per_symbol=None,
        max_open_position_count=None,
        max_drawdown_pct_from_equity_peak=None,
        max_floating_loss_usd=None,
    )
    decision = evaluate_proposed_intent(
        proposed_intent={"symbol": "EURUSD", "direction": "SELL", "lots": 1.0},
        portfolio_snapshot=snapshot,
        caps=caps,
    )
    assert decision.accepted is False
    assert "max_total_exposure_lots" in decision.blocking_caps


# ---------------------------------------------------------------------------
# 11. Missing fields -> REJECT with clear reason.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "intent,missing_token",
    [
        ({"direction": "BUY", "lots": 0.1}, "symbol"),
        ({"symbol": "EURUSD", "lots": 0.1}, "direction"),
        ({"symbol": "EURUSD", "direction": "BUY"}, "lots"),
        ({}, "symbol"),
    ],
)
def test_missing_fields_reject_with_reason(intent: dict, missing_token: str) -> None:
    decision = evaluate_proposed_intent(
        proposed_intent=intent,
        portfolio_snapshot=_empty_snapshot(),
        caps=DEFAULT_CAPS,
    )
    assert decision.accepted is False
    assert decision.decision == "REJECT"
    assert "missing required field" in decision.plain_english_reason
    assert missing_token in decision.plain_english_reason
    assert "missing_required_fields" in decision.blocking_caps


# ---------------------------------------------------------------------------
# 12. plain_english_reason never contains any of the 10 forbidden phrases.
# ---------------------------------------------------------------------------

_SAMPLE_FIXTURES = [
    # 1. PASS, diversified portfolio adding a small new symbol
    (
        {"symbol": "USDJPY", "direction": "BUY", "lots": 0.1},
        {
            "open_position_count": 2,
            "total_floating_pnl": 0.0,
            "total_exposure_lots": 2.0,
            "concentration_pct": 50.0,
            "by_symbol": [
                {
                    "symbol": "EURUSD",
                    "direction": "BUY",
                    "open_position_count": 1,
                    "total_lots": 1.0,
                    "total_floating_pnl": 0.0,
                    "largest_position_lots": 1.0,
                },
                {
                    "symbol": "GBPUSD",
                    "direction": "BUY",
                    "open_position_count": 1,
                    "total_lots": 1.0,
                    "total_floating_pnl": 0.0,
                    "largest_position_lots": 1.0,
                },
            ],
            "account_balance": 10_000.0,
            "account_equity": 10_000.0,
            "account_margin": 1_000.0,
            "account_free_margin": 9_000.0,
            "margin_utilization_pct": 10.0,
        },
        DEFAULT_CAPS,
        None,
    ),
    # 2. PASS, fresh portfolio (empty snapshot -> adding 1 symbol = 100%
    # concentration which would breach DEFAULT_CAPS; use a relaxed caps
    # set to keep this a real PASS branch).
    (
        {"symbol": "GBPUSD", "direction": "SELL", "lots": 0.25},
        _empty_snapshot(),
        RiskCapConfig(
            max_total_exposure_lots=10.0,
            max_concentration_pct=None,
            max_margin_utilization_pct=70.0,
            max_positions_per_symbol=5,
            max_open_position_count=20,
            max_drawdown_pct_from_equity_peak=15.0,
            max_floating_loss_usd=None,
        ),
        None,
    ),
    # 3. REJECT, total exposure
    (
        {"symbol": "GBPUSD", "direction": "BUY", "lots": 5.0},
        _populated_snapshot(
            total_lots=9.5, eurusd_lots=9.5, eurusd_count=1, open_count=1
        ),
        DEFAULT_CAPS,
        None,
    ),
    # 4. REJECT, drawdown
    (
        {"symbol": "EURUSD", "direction": "BUY", "lots": 0.1},
        _populated_snapshot(
            total_lots=1.0,
            eurusd_lots=1.0,
            eurusd_count=1,
            open_count=1,
            equity=7_500.0,
            free_margin=6_000.0,
            margin_util=20.0,
        ),
        DEFAULT_CAPS,
        10_000.0,
    ),
    # 5. REJECT, missing fields
    (
        {"direction": "BUY", "lots": 0.1},
        _empty_snapshot(),
        DEFAULT_CAPS,
        None,
    ),
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_ADVISORY_PHRASES)
def test_plain_english_reason_never_contains_forbidden_phrase(forbidden: str) -> None:
    saw_pass = False
    saw_reject = False
    for intent, snapshot, caps, peak in _SAMPLE_FIXTURES:
        decision = evaluate_proposed_intent(
            proposed_intent=intent,
            portfolio_snapshot=snapshot,
            caps=caps,
            equity_peak=peak,
        )
        text = decision.plain_english_reason.lower()
        assert forbidden.lower() not in text, (
            f"forbidden phrase {forbidden!r} appeared in: {decision.plain_english_reason!r}"
        )
        if decision.accepted:
            saw_pass = True
        else:
            saw_reject = True
    assert saw_pass, "fixture set must include at least one PASS branch"
    assert saw_reject, "fixture set must include at least one REJECT branch"


# Confirm the canonical list has exactly the 10 required phrases the
# task spec pins.
def test_forbidden_phrase_list_pins_canonical_ten() -> None:
    expected = {
        "you should sell",
        "consider closing",
        "scale back",
        "exit position",
        "take profit",
        "cut your losses",
        "buy more",
        "add to position",
        "is a good entry",
        "we recommend",
    }
    assert set(FORBIDDEN_ADVISORY_PHRASES) == expected
    assert len(FORBIDDEN_ADVISORY_PHRASES) == 10


# ---------------------------------------------------------------------------
# 13. DEFAULT_CAPS sanity check.
# ---------------------------------------------------------------------------

def test_default_caps_are_reasonable() -> None:
    assert DEFAULT_CAPS.max_total_exposure_lots == 10.0
    assert DEFAULT_CAPS.max_concentration_pct == 70.0
    assert DEFAULT_CAPS.max_margin_utilization_pct == 70.0
    assert DEFAULT_CAPS.max_positions_per_symbol == 5
    assert DEFAULT_CAPS.max_open_position_count == 20
    assert DEFAULT_CAPS.max_drawdown_pct_from_equity_peak == 15.0
    # max_floating_loss_usd is intentionally None by default.
    assert DEFAULT_CAPS.max_floating_loss_usd is None
    # All numeric caps are strictly positive.
    for value in (
        DEFAULT_CAPS.max_total_exposure_lots,
        DEFAULT_CAPS.max_concentration_pct,
        DEFAULT_CAPS.max_margin_utilization_pct,
        DEFAULT_CAPS.max_positions_per_symbol,
        DEFAULT_CAPS.max_open_position_count,
        DEFAULT_CAPS.max_drawdown_pct_from_equity_peak,
    ):
        assert value is not None and value > 0


# ---------------------------------------------------------------------------
# Extras: payload + intent summary formatting.
# ---------------------------------------------------------------------------

def test_decision_payload_round_trip() -> None:
    caps = RiskCapConfig(
        max_total_exposure_lots=10.0,
        max_concentration_pct=None,
        max_margin_utilization_pct=70.0,
        max_positions_per_symbol=5,
        max_open_position_count=20,
        max_drawdown_pct_from_equity_peak=15.0,
        max_floating_loss_usd=None,
    )
    decision = evaluate_proposed_intent(
        proposed_intent=_BASE_INTENT,
        portfolio_snapshot=_empty_snapshot(),
        caps=caps,
    )
    payload = decision_to_payload(decision)
    assert payload["accepted"] is True
    assert payload["decision"] == "PASS"
    assert isinstance(payload["blocking_caps"], list)
    assert payload["proposed_intent_summary"] == "BUY EURUSD 0.10 lots"


def test_proposed_intent_summary_format() -> None:
    # We only care about the summary string formatting here; reject vs
    # pass is irrelevant for this assertion.
    decision = evaluate_proposed_intent(
        proposed_intent={"symbol": "usdjpy", "direction": "sell", "lots": 0.5},
        portfolio_snapshot=_empty_snapshot(),
        caps=DEFAULT_CAPS,
    )
    assert decision.proposed_intent_summary == "SELL USDJPY 0.50 lots"
