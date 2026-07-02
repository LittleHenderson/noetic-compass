from __future__ import annotations

from cas_forex.ai_control_authority import AiControlAuthority
from cas_forex.directional_intelligence import (
    DIRECTIONAL_PROFILES,
    candidate_from_hypothesis,
    score_direction,
)


def _candles(start: float, step: float, n: int = 80):
    out = []
    price = start
    for _ in range(n):
        price += step
        out.append(
            {
                "open": price - step * 0.3,
                "high": price + abs(step) + 0.0004,
                "low": price - abs(step) - 0.0004,
                "close": price,
            }
        )
    return out


def test_score_direction_can_choose_long(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    h = score_direction(
        _candles(1.1000, 0.0008),
        symbol="EUR/USD",
        timeframe="M15",
        authority=auth,
    )
    assert h.action == "LONG"
    assert h.long_score > h.short_score
    assert h.confidence > 0
    assert h.profile == "blend"


def test_score_direction_can_choose_short(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    h = score_direction(
        _candles(1.2000, -0.0008),
        symbol="EUR/USD",
        timeframe="M15",
        authority=auth,
    )
    assert h.action == "SHORT"
    assert h.short_score > h.long_score


def test_score_direction_records_requested_profile(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    h = score_direction(
        _candles(1.1000, 0.0008),
        symbol="EUR/USD",
        timeframe="M15",
        authority=auth,
        profile="trend_follow",
    )

    assert h.profile == "trend_follow"
    assert h.profile in DIRECTIONAL_PROFILES
    assert h.to_dict()["profile"] == "trend_follow"
    assert h.reasons[0] == "profile=trend_follow"


def test_unknown_directional_profile_falls_back_to_blend(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    h = score_direction(
        _candles(1.1000, 0.0008),
        symbol="EUR/USD",
        timeframe="M15",
        authority=auth,
        profile="made_up_profile",
    )

    assert h.profile == "blend"


def test_owner_disabled_short_forces_no_trade(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    auth.owner_update(allow_short=False)
    h = score_direction(
        _candles(1.2000, -0.0008),
        symbol="EUR/USD",
        timeframe="M15",
        authority=auth,
    )
    assert h.action == "NO_TRADE"
    assert "owner disabled SHORT" in h.reasons[0]


def test_candidate_from_hypothesis_sets_directional_risk_box(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    candles = _candles(1.1000, 0.0008)
    h = score_direction(candles, symbol="EUR/USD", timeframe="M15", authority=auth)
    setup = candidate_from_hypothesis(h, candles)

    assert setup is not None
    assert setup.direction == "LONG"
    assert setup.stop_loss < setup.entry < setup.take_profit
    assert setup.signal_strength == h.confidence
    assert setup.decision_ref.startswith("waste-dir-")
    assert getattr(setup, "entry_pairs") == []


def test_insufficient_candles_are_no_trade(tmp_path):
    auth = AiControlAuthority(tmp_path / "authority.json")
    h = score_direction(
        _candles(1.1000, 0.0001, n=10),
        symbol="EUR/USD",
        authority=auth,
    )
    assert h.action == "NO_TRADE"
    assert "insufficient candles" in h.reasons[0]
