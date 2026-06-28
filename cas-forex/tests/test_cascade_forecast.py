"""Tests for the Cascade Confidence-and-Break layer (cas_forex/cascade_forecast.py).

These tests enforce both the functional spec (monotone confidence, breakdown
threshold logic, involution flip, open-cause collapse) AND the anti-leakage /
honesty invariants (no future price reads, no directional output, surprise
fields never read).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cas_forex.cascade_forecast import (
    BREAKDOWN_PENALTY,
    INVOLUTION,
    NO_EDGE_DISCLAIMER,
    OPEN_CAUSE_COLLAPSE,
    CascadeForecast,
    breakdown_step_for,
    per_step_certainty,
    project_cascade,
)
from cas_forex.regime_sim import REGIMES, generate_regime_candles
from cas_forex.schemas.macro import (
    MacroEventState,
    MacroEventType,
    MacroImpact,
)
from cas_forex.verifier.macro_gate import StaticMacroCalendarProvider

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

# A known HIGH-impact seed event: the January 2026 NFP at 2026-01-09 13:30 UTC.
NFP_JAN_2026 = datetime(2026, 1, 9, 13, 30, tzinfo=UTC)
# A known MEDIUM-impact seed event: the central-bank speech at 2026-06-24 16:00 UTC.
CB_SPEECH_2026 = datetime(2026, 6, 24, 16, 0, tzinfo=UTC)


def _trend_up_closes(bars: int = 200, seed: int = 7):
    candles = generate_regime_candles("trend_up", symbol="EUR/USD", bars=bars, seed=seed)
    return [c["close"] for c in candles]


def _quiet_anchor():
    """An anchor in a window with no HIGH-impact seed event for a short horizon.

    2026-02-20 is well after the Feb NFP/CPI cluster and before the Mar events,
    so a short H1 horizon spans no HIGH event.
    """
    return datetime(2026, 2, 20, 9, 0, tzinfo=UTC)


def _monotone_non_increasing(curve, tol: float = 1e-12) -> bool:
    return all(curve[i + 1] <= curve[i] + tol for i in range(len(curve) - 1))


# ---------------------------------------------------------------------------
# Confidence curve properties
# ---------------------------------------------------------------------------


def test_confidence_is_monotone_decreasing():
    closes = _trend_up_closes()
    for beta in (0.0, 0.2, 0.5, 1.0, 3.0):
        fc = project_cascade(
            closes, horizon=20, beta=beta, start_regime="trend_up",
            anchor_time=_quiet_anchor(),
        )
        curve = fc.confidence_curve
        assert _monotone_non_increasing(curve), f"not monotone for beta={beta}: {curve}"
        # conf at step 1 is c_step <= 1; conf_base[0] is defined as 1.0 implicitly.
        assert curve[0] <= 1.0 + 1e-12


def test_higher_beta_decays_faster():
    closes = _trend_up_closes()
    # No breakdown within horizon (small betas) and no event -> pure decay.
    k = 10
    conf = {}
    for beta in (0.0, 0.2, 1.0):
        fc = project_cascade(
            closes, horizon=20, beta=beta, start_regime="trend_up",
            anchor_time=_quiet_anchor(),
            # keep runaway away so betas 0.2/1.0 don't break within k=10
            runaway_threshold=1000.0,
        )
        conf[beta] = fc.confidence_curve[k - 1]
    assert conf[1.0] < conf[0.2] < conf[0.0]


def test_per_step_certainty_in_open_unit_interval():
    prev = None
    for beta in (0.0, 0.1, 0.5, 1.0, 5.0):
        c = per_step_certainty(beta)
        assert 0.0 < c < 1.0
        if prev is not None:
            assert c < prev, "per-step certainty must strictly decrease in beta"
        prev = c


def test_per_step_certainty_rejects_negative_beta():
    with pytest.raises(ValueError):
        per_step_certainty(-0.1)


# ---------------------------------------------------------------------------
# Breakdown threshold logic + involution flip
# ---------------------------------------------------------------------------


def test_breakdown_step_threshold_logic():
    # G_k = beta * k; threshold 1.0.
    assert breakdown_step_for(0.25, horizon=20, threshold=1.0) == 4  # G_4 = 1.0
    # beta 0.1, horizon 5 -> G_5 = 0.5 < 1.0 -> no breakdown in horizon.
    assert breakdown_step_for(0.1, horizon=5, threshold=1.0) is None
    # beta 0 -> never.
    assert breakdown_step_for(0.0, horizon=50, threshold=1.0) is None


def test_breakdown_step_threshold_reflected_in_forecast():
    closes = _trend_up_closes()
    fc = project_cascade(
        closes, horizon=20, beta=0.25, start_regime="trend_up",
        anchor_time=_quiet_anchor(), runaway_threshold=1.0,
    )
    assert fc.breakdown_step == 4
    for s in fc.steps:
        assert s.breakdown_flag == (s.step >= 4)

    fc2 = project_cascade(
        closes, horizon=5, beta=0.1, start_regime="trend_up",
        anchor_time=_quiet_anchor(), runaway_threshold=1.0,
    )
    assert fc2.breakdown_step is None
    assert not any(s.breakdown_flag for s in fc2.steps)


def test_breakdown_flips_regime_to_involution():
    closes = _trend_up_closes()
    # trend_up -> trend_down after breakdown.
    fc = project_cascade(
        closes, horizon=10, beta=0.5, start_regime="trend_up",
        anchor_time=_quiet_anchor(), runaway_threshold=1.0,
    )
    b = fc.breakdown_step  # ceil(1.0/0.5) = 2
    assert b == 2
    for s in fc.steps:
        if s.step < b:
            assert s.projected_regime == "trend_up"
        else:
            assert s.projected_regime == "trend_down"

    # high_vol -> low_vol.
    fc_hv = project_cascade(
        closes, horizon=10, beta=0.5, start_regime="high_vol",
        anchor_time=_quiet_anchor(), runaway_threshold=1.0,
    )
    assert fc_hv.steps[-1].projected_regime == "low_vol"

    # range is self-paired: stays 'range' but still flags breakdown.
    fc_rng = project_cascade(
        closes, horizon=10, beta=0.5, start_regime="range",
        anchor_time=_quiet_anchor(), runaway_threshold=1.0,
    )
    assert all(s.projected_regime == "range" for s in fc_rng.steps)
    assert any(s.breakdown_flag for s in fc_rng.steps)


def test_breakdown_lowers_confidence():
    closes = _trend_up_closes()
    beta = 0.5
    with_break = project_cascade(
        closes, horizon=10, beta=beta, start_regime="trend_up",
        anchor_time=_quiet_anchor(), runaway_threshold=1.0,
        breakdown_penalty=0.5,
    )
    no_break = project_cascade(
        closes, horizon=10, beta=beta, start_regime="trend_up",
        anchor_time=_quiet_anchor(), runaway_threshold=1000.0,  # never breaks
    )
    b = with_break.breakdown_step
    # At and after the breakdown step, confidence is strictly below the
    # no-breakdown baseline (penalty < 1).
    for s_b, s_n in zip(with_break.steps, no_break.steps):
        if s_b.step >= b:
            assert s_b.confidence < s_n.confidence
    assert _monotone_non_increasing(with_break.confidence_curve)


# ---------------------------------------------------------------------------
# Open-cause (macro) wiring
# ---------------------------------------------------------------------------


def test_open_cause_flag_set_when_event_in_horizon():
    closes = _trend_up_closes()
    # Anchor 5 hours before the Jan NFP, H1 bars => event lands at step 5.
    anchor = NFP_JAN_2026 - timedelta(hours=5)
    fc = project_cascade(
        closes, horizon=12, beta=0.0, start_regime="trend_up",
        anchor_time=anchor, timeframe="H1",
    )
    assert fc.open_cause_step == 5
    for s in fc.steps:
        assert s.open_cause_flag == (s.step >= 5)
    # The matched event is recorded in evidence.
    assert fc.evidence["matched_events"], "expected a matched event"
    first = fc.evidence["matched_events"][0]
    assert first["step"] == 5
    assert first["event_type"] == "NFP"
    assert first["event_id"].startswith("2026-nfp")
    # And stamped on the step record.
    assert fc.steps[4].matched_event_id == first["event_id"]


def test_open_cause_collapses_confidence():
    closes = _trend_up_closes()
    anchor = NFP_JAN_2026 - timedelta(hours=5)
    with_event = project_cascade(
        closes, horizon=12, beta=0.2, start_regime="trend_up",
        anchor_time=anchor, timeframe="H1", runaway_threshold=1000.0,
    )
    # Same params but a quiet anchor with no in-horizon HIGH event.
    no_event = project_cascade(
        closes, horizon=12, beta=0.2, start_regime="trend_up",
        anchor_time=_quiet_anchor(), timeframe="H1", runaway_threshold=1000.0,
    )
    o = with_event.open_cause_step
    assert o == 5
    # At the open-cause step the confidence is collapsed by ~OPEN_CAUSE_COLLAPSE.
    ratio = with_event.confidence_curve[o - 1] / no_event.confidence_curve[o - 1]
    assert ratio < OPEN_CAUSE_COLLAPSE * 1.5  # roughly the collapse factor
    assert _monotone_non_increasing(with_event.confidence_curve)


def test_no_event_in_horizon_no_flag():
    closes = _trend_up_closes()
    fc = project_cascade(
        closes, horizon=4, beta=0.0, start_regime="trend_up",
        anchor_time=_quiet_anchor(), timeframe="H1",
    )
    assert fc.open_cause_step is None
    assert not any(s.open_cause_flag for s in fc.steps)
    assert fc.evidence["matched_events"] == []


def test_low_impact_event_does_not_collapse_by_default():
    closes = _trend_up_closes()
    # Anchor so the MEDIUM central-bank speech lands inside an H1 horizon.
    anchor = CB_SPEECH_2026 - timedelta(hours=3)
    # Default min_impact=HIGH -> the MEDIUM event is NOT flagged.
    fc_high = project_cascade(
        closes, horizon=6, beta=0.0, start_regime="trend_up",
        anchor_time=anchor, timeframe="H1", min_impact=MacroImpact.HIGH,
    )
    assert fc_high.open_cause_step is None
    assert not any(s.open_cause_flag for s in fc_high.steps)

    # min_impact=MEDIUM -> it IS flagged.
    fc_med = project_cascade(
        closes, horizon=6, beta=0.0, start_regime="trend_up",
        anchor_time=anchor, timeframe="H1", min_impact=MacroImpact.MEDIUM,
    )
    assert fc_med.open_cause_step == 3
    assert any(e["event_type"] == "CENTRAL_BANK_SPEECH" for e in fc_med.evidence["matched_events"])


# ---------------------------------------------------------------------------
# ANTI-LEAKAGE invariants
# ---------------------------------------------------------------------------


def test_confidence_independent_of_future_prices():
    """Appending arbitrary future bars must not move any confidence value,
    the breakdown step, the open-cause step, or the projected-regime list."""
    closes = _trend_up_closes()
    t = 150
    prefix = closes[:t]
    up = prefix + [prefix[-1] * 1.5] * 50
    down = prefix + [prefix[-1] * 0.5] * 50

    kwargs = dict(
        horizon=15, beta=0.4, start_regime="trend_up",
        anchor_time=NFP_JAN_2026 - timedelta(hours=5), timeframe="H1",
    )
    base = project_cascade(prefix, **kwargs)
    fc_up = project_cascade(up, **kwargs)
    fc_down = project_cascade(down, **kwargs)

    assert base.confidence_curve == fc_up.confidence_curve == fc_down.confidence_curve
    assert base.breakdown_step == fc_up.breakdown_step == fc_down.breakdown_step
    assert base.open_cause_step == fc_up.open_cause_step == fc_down.open_cause_step
    regimes_base = [s.projected_regime for s in base.steps]
    regimes_up = [s.projected_regime for s in fc_up.steps]
    regimes_down = [s.projected_regime for s in fc_down.steps]
    assert regimes_base == regimes_up == regimes_down


def test_breakdown_step_invariant_to_future_price_shape():
    """The breakdown flip is triggered only by the deterministic gain threshold,
    never by observing a realized reversal: scaling/reordering future closes
    must not move breakdown_step."""
    closes = _trend_up_closes()
    t = 150
    prefix = closes[:t]
    reordered = prefix + sorted([prefix[-1] * 0.7] * 25 + [prefix[-1] * 1.3] * 25)
    kwargs = dict(horizon=15, beta=0.3, start_regime="trend_up", anchor_time=_quiet_anchor())
    a = project_cascade(prefix, **kwargs)
    b = project_cascade(reordered, **kwargs)
    assert a.breakdown_step == b.breakdown_step


def test_no_directional_output():
    """No LONG/SHORT/direction/entry/target leaks into the public output."""
    closes = _trend_up_closes()
    fc = project_cascade(
        closes, horizon=10, beta=0.5, start_regime="trend_up",
        anchor_time=_quiet_anchor(),
    )
    out = fc.to_dict()
    # The disclaimer is ALLOWED to name LONG/SHORT in order to disavow them;
    # exclude it from the leakage scan and check every other field.
    out_no_disclaimer = {k: v for k, v in out.items() if k != "disclaimer"}
    blob = repr(out_no_disclaimer).upper()
    for forbidden in ("LONG", "SHORT", "DIRECTION", "ENTRY_PRICE", "TAKE_PROFIT",
                      "STOP_LOSS", "BUY", "SELL"):
        assert forbidden not in blob, f"directional token leaked: {forbidden}"
    # Keys of the per-step dicts are exactly the non-directional set.
    for d in fc.as_dicts():
        assert set(d.keys()) == {
            "step", "projected_regime", "confidence", "breakdown_flag", "open_cause_flag"
        }
    # Module exposes no Direction enum / directional names.
    import cas_forex.cascade_forecast as mod
    public = [n for n in dir(mod) if not n.startswith("_")]
    for n in public:
        up = n.upper()
        assert "DIRECTION" not in up
        assert up not in ("LONG", "SHORT", "BUY", "SELL")


def test_surprise_fields_never_read():
    """Setting actual/expected/shock_active to absurd values must leave the
    forecast byte-identical to the same calendar with those fields cleared --
    proving only scheduled timing/type/impact are read."""
    anchor = NFP_JAN_2026 - timedelta(hours=5)
    closes = _trend_up_closes()

    base_event = dict(
        event_id="2026-nfp-test",
        event_type=MacroEventType.NFP,
        currency="USD",
        scheduled_at_utc=NFP_JAN_2026,
        impact=MacroImpact.HIGH,
        shock_threshold=0.1,
    )
    poisoned = MacroEventState(**base_event, actual=999999.0, expected=-999999.0)
    # poisoned.shock_active is True (|surprise| >> threshold); must be ignored.
    assert poisoned.shock_active is True
    clean = MacroEventState(**base_event)
    assert clean.shock_active is False

    cal_poison = StaticMacroCalendarProvider(events=[poisoned])
    cal_clean = StaticMacroCalendarProvider(events=[clean])

    kwargs = dict(
        horizon=12, beta=0.3, start_regime="trend_up",
        anchor_time=anchor, timeframe="H1",
    )
    fc_poison = project_cascade(closes, calendar=cal_poison, **kwargs)
    fc_clean = project_cascade(closes, calendar=cal_clean, **kwargs)

    assert fc_poison.confidence_curve == fc_clean.confidence_curve
    assert fc_poison.breakdown_step == fc_clean.breakdown_step
    assert fc_poison.open_cause_step == fc_clean.open_cause_step
    assert fc_poison.as_dicts() == fc_clean.as_dicts()


def test_step_time_mapping():
    closes = _trend_up_closes()
    anchor = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    fc_h1 = project_cascade(
        closes, horizon=4, beta=0.0, start_regime="trend_up",
        anchor_time=anchor, timeframe="H1",
    )
    for s in fc_h1.steps:
        assert s.step_time == anchor + timedelta(hours=s.step)

    fc_m15 = project_cascade(
        closes, horizon=4, beta=0.0, start_regime="trend_up",
        anchor_time=anchor, timeframe="M15",
    )
    for s in fc_m15.steps:
        assert s.step_time == anchor + timedelta(minutes=15 * s.step)


# ---------------------------------------------------------------------------
# Output shape + validation + misc
# ---------------------------------------------------------------------------


def test_as_dicts_shape():
    closes = _trend_up_closes()
    fc = project_cascade(
        closes, horizon=8, beta=0.3, start_regime="trend_up",
        anchor_time=_quiet_anchor(),
    )
    dicts = fc.as_dicts()
    assert len(dicts) == 8
    for d in dicts:
        assert set(d.keys()) == {
            "step", "projected_regime", "confidence", "breakdown_flag", "open_cause_flag"
        }


def test_to_dict_is_json_safe():
    import json
    closes = _trend_up_closes()
    fc = project_cascade(
        closes, horizon=6, beta=0.3, start_regime="trend_up",
        anchor_time=NFP_JAN_2026 - timedelta(hours=2), timeframe="H1",
    )
    # Should serialize without error.
    s = json.dumps(fc.to_dict())
    assert NO_EDGE_DISCLAIMER in fc.to_dict()["disclaimer"]
    assert isinstance(s, str)


def test_invalid_inputs():
    closes = _trend_up_closes()
    with pytest.raises(ValueError):
        project_cascade(closes, horizon=0, beta=0.5, start_regime="trend_up")
    with pytest.raises(ValueError):
        project_cascade(closes, horizon=10, beta=-0.1, start_regime="trend_up")
    with pytest.raises(ValueError):
        project_cascade(closes, horizon=10, beta=0.5, start_regime="not_a_regime")


def test_beta_zero_pure_persistence():
    import math
    closes = _trend_up_closes()
    lam = 0.03
    fc = project_cascade(
        closes, horizon=10, beta=0.0, start_regime="trend_up",
        anchor_time=_quiet_anchor(), lam=lam,
    )
    assert fc.breakdown_step is None
    assert all(s.projected_regime == "trend_up" for s in fc.steps)
    # confidence == exp(-lam*k) (no event, no breakdown).
    for s in fc.steps:
        assert math.isclose(s.confidence, math.exp(-lam * s.step), rel_tol=1e-9)
    assert _monotone_non_increasing(fc.confidence_curve)


def test_involution_map_matches_regimes():
    # Every REGIME has an involution image, and the image is also a REGIME.
    for r in REGIMES:
        assert r in INVOLUTION
        assert INVOLUTION[r] in REGIMES
    # Directional/vol pairs are true involutions (apply twice -> identity).
    for r in ("trend_up", "trend_down", "high_vol", "low_vol"):
        assert INVOLUTION[INVOLUTION[r]] == r


def test_detect_regime_used_when_start_regime_omitted():
    # Smoke: omitting start_regime detects from price and yields a valid regime.
    closes = _trend_up_closes()
    fc = project_cascade(closes, horizon=5, beta=0.2, anchor_time=_quiet_anchor())
    assert fc.start_regime in REGIMES
