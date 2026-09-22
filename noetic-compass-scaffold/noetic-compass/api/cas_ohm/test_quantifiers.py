"""Tests for the CAS-Ohm quantifier module.

Runs under BOTH pytest and a plain ``python test_quantifiers.py`` (the __main__
block discovers every test_ function, runs it, and prints "PASSED n/n").  No
third-party dependency required.

Every numeric value here is FABRICATED for exposition (RING 4 / NOT LICENSED /
HELD); passing tests is evidence about code<->spec only, never spec<->world.
"""

import math

try:
    # Package-relative import (pytest, running as a module).
    from .quantifiers import (
        delta_current, r_hidden, maturity_q4,
        i_pred, y_hat, r_total, r_cap,
        Region, Outcome, AsomLabel, asom,
        admissible_trend, TrendTag, TrendVerdict, InadmissibleTrendError,
        check_eligibility, require_eligible, EligibilityError,
        DeltaCurrent, RHidden, CensoredResult, MaturityQ4, CjtQRecord,
        Score, SignReading, Band, Trend, ResistanceRole, KindError,
        RESIDUAL_METHOD_IDENTITY, R_HIDDEN_NAME_OVERRIDE_NOTE,
    )
except ImportError:
    # Plain-script fallback (python test_quantifiers.py).
    from quantifiers import (  # type: ignore
        delta_current, r_hidden, maturity_q4,
        i_pred, y_hat, r_total, r_cap,
        Region, Outcome, AsomLabel, asom,
        admissible_trend, TrendTag, TrendVerdict, InadmissibleTrendError,
        check_eligibility, require_eligible, EligibilityError,
        DeltaCurrent, RHidden, CensoredResult, MaturityQ4, CjtQRecord,
        Score, SignReading, Band, Trend, ResistanceRole, KindError,
        RESIDUAL_METHOD_IDENTITY, R_HIDDEN_NAME_OVERRIDE_NOTE,
    )


# ----------------------------------------------------------------------------
# delta_current — sign in all three regimes + tolerance + non-identification.
# NEUTRAL LABELS: WITHIN_TOLERANCE / UNDERSHOOT / OVERSHOOT (no mechanism words).
# ----------------------------------------------------------------------------

def test_delta_current_within_tolerance():
    r = delta_current(1.00, 1.00)
    assert isinstance(r, DeltaCurrent)
    assert r.value == 0.0
    assert r.sign is SignReading.WITHIN_TOLERANCE
    # tolerance boundary: exactly at the tolerance is still WITHIN_TOLERANCE
    # (exactly-representable values so the boundary is exact: 2.5-2.0=0.5)
    r2 = delta_current(2.5, 2.0, tolerance=0.5)
    assert r2.value == 0.5
    assert r2.sign is SignReading.WITHIN_TOLERANCE


def test_delta_current_undershoot():
    r = delta_current(0.80, 1.00, tolerance=0.05)
    assert r.value < 0
    assert r.sign is SignReading.UNDERSHOOT


def test_delta_current_overshoot():
    r = delta_current(1.30, 1.00, tolerance=0.05)
    assert r.value > 0
    assert r.sign is SignReading.OVERSHOOT


def test_delta_current_labels_carry_no_mechanism_vocabulary():
    # ch10:rule:nonident: no mechanism words in the EMITTED label.
    forbidden = ("OPPOSITION", "AMPLIFICATION", "BYPASS", "HIDDEN")
    for member in SignReading:
        for word in forbidden:
            assert word not in member.value.upper(), (
                f"SignReading.{member.name} imports forbidden mechanism vocabulary")


def test_delta_current_tolerance_transition_both_sides():
    # pin the EXACT -tolerance / +tolerance transition into UNDERSHOOT/OVERSHOOT.
    # Use exactly-representable arithmetic: delta = i_obs - i_pred.
    tol = 0.25
    # exactly -tol (2.0 - 2.25 = -0.25) -> still WITHIN_TOLERANCE (<= tol)
    at_minus = delta_current(2.0, 2.25, tolerance=tol)
    assert math.isclose(at_minus.value, -0.25)
    assert at_minus.sign is SignReading.WITHIN_TOLERANCE
    # just past -tol (2.0 - 2.5 = -0.5) -> UNDERSHOOT
    below = delta_current(2.0, 2.5, tolerance=tol)
    assert below.sign is SignReading.UNDERSHOOT
    # exactly +tol (2.5 - 2.25 = 0.25) -> still WITHIN_TOLERANCE
    at_plus = delta_current(2.5, 2.25, tolerance=tol)
    assert math.isclose(at_plus.value, 0.25)
    assert at_plus.sign is SignReading.WITHIN_TOLERANCE
    # just past +tol (3.0 - 2.5 = 0.5) -> OVERSHOOT
    above = delta_current(3.0, 2.5, tolerance=tol)
    assert above.sign is SignReading.OVERSHOOT


def test_delta_current_non_identification_flag_is_false():
    r = delta_current(1.30, 1.00)
    assert r.identifies_mechanism is False
    assert r.method_identity == RESIDUAL_METHOD_IDENTITY
    assert "never identif" in r.note.lower() or "never identifies" in r.note.lower()


def test_delta_current_active_region_only():
    # non-ACTIVE region must refuse (fail-closed), not degrade.
    for region in (Region.SATURATION, Region.CUTOFF, Region.UNASSESSED,
                   Region.BREAKDOWN, Region.NON_OHMIC, Region.UNSTABLE):
        raised = False
        try:
            delta_current(1.0, 1.0, region=region)
        except EligibilityError:
            raised = True
        assert raised, f"expected refusal in region {region}"
    # ACTIVE is fine
    assert delta_current(1.0, 1.0, region=Region.ACTIVE).sign is SignReading.WITHIN_TOLERANCE


# ----------------------------------------------------------------------------
# r_hidden — worked example + censoring (point and interval modes) + naming.
# ----------------------------------------------------------------------------

def test_r_hidden_worked_example():
    # V=8, R_known=2, I_obs=2 -> R_hidden = 8/2 - 2 = 2
    r = r_hidden(v=8.0, i_obs=2.0, r_known=2.0)
    assert isinstance(r, RHidden)
    assert math.isclose(r.magnitude, 2.0)
    assert math.isclose(r.resistance_delta, 2.0)   # monograph-neutral alias
    assert math.isclose(r.r_apparent, 4.0)
    assert r.role is ResistanceRole.APPARENT_SAME_SAMPLE
    assert r.identifies_mechanism is False
    # probe shortlist present and includes the five named probes
    for probe in ("capability", "policy", "context", "resource", "miswired-branch"):
        assert probe in r.probe_shortlist
    assert "APPARENT_SAME_SAMPLE" in r.causal_identity_note
    # the name-override disclosure is attached to the emitted record
    assert "NAME OVERRIDE" in r.name_override_note
    assert r.name_override_note == R_HIDDEN_NAME_OVERRIDE_NOTE


def test_r_hidden_censors_at_zero():
    r = r_hidden(v=8.0, i_obs=0.0, r_known=2.0)
    assert isinstance(r, CensoredResult)
    assert r.censored is True
    assert r.marker == "OBSERVED_INTERVAL_INCLUDES_ZERO"
    assert r.reason  # explicit, non-empty reason (never an empty slot)
    assert r.identifies_mechanism is False


def test_r_hidden_censors_zero_compatible_small():
    # within the zero-compatible epsilon -> censored (point mode)
    r = r_hidden(v=8.0, i_obs=1e-12, r_known=2.0)
    assert isinstance(r, CensoredResult)


def test_r_hidden_censors_non_finite():
    r = r_hidden(v=8.0, i_obs=float("nan"), r_known=2.0)
    assert isinstance(r, CensoredResult)
    r2 = r_hidden(v=8.0, i_obs=float("inf"), r_known=2.0)
    assert isinstance(r2, CensoredResult)


def test_r_hidden_interval_mode_censors_on_lower_bound():
    # monograph-faithful: censor iff interval lower bound <= 0, even when the
    # POINT value is far from zero.
    r = r_hidden(v=8.0, i_obs=2.6, r_known=2.0, i_obs_interval=(-0.05, 0.25))
    assert isinstance(r, CensoredResult)
    assert r.marker == "OBSERVED_INTERVAL_INCLUDES_ZERO"
    # touching zero (lower bound exactly 0) also censors
    r2 = r_hidden(v=8.0, i_obs=2.6, r_known=2.0, i_obs_interval=(0.0, 0.5))
    assert isinstance(r2, CensoredResult)


def test_r_hidden_interval_mode_admits_when_interval_excludes_zero():
    # tight interval strictly above zero at a small point value -> admitted
    r = r_hidden(v=8.0, i_obs=2.0, r_known=2.0, i_obs_interval=(1.8, 2.2))
    assert isinstance(r, RHidden)
    assert math.isclose(r.magnitude, 2.0)


def test_r_hidden_rejects_score_as_r_known():
    raised = False
    try:
        r_hidden(v=8.0, i_obs=2.0, r_known=Score(2.0, "Q10"))
    except KindError:
        raised = True
    assert raised


# ----------------------------------------------------------------------------
# maturity_q4 — half-open band edges + pre-rounding + trend.
# ----------------------------------------------------------------------------

def test_maturity_q4_cut_points_assigned_upward():
    # cut points belong to the UPPER band (equality fails strict '<')
    assert maturity_q4(2.5).band is Band.Q2
    assert maturity_q4(5.0).band is Band.Q3
    assert maturity_q4(7.5).band is Band.Q4


def test_maturity_q4_just_below_cut_points():
    assert maturity_q4(2.499).band is Band.Q1
    assert maturity_q4(4.999).band is Band.Q2
    assert maturity_q4(7.499).band is Band.Q3


def test_maturity_q4_pre_rounding_7499_vs_75():
    # 7.499 must NOT be pulled up to 7.5 by any rounding
    assert maturity_q4(7.499).band is Band.Q3
    assert maturity_q4(7.5).band is Band.Q4


def test_maturity_q4_endpoints_and_overload():
    assert maturity_q4(0.0).band is Band.Q1          # closed left end
    assert maturity_q4(12.0).band is Band.Q4         # overloaded exact value -> Q4
    assert maturity_q4(2.495).band is Band.Q1        # gap value, exact -> Q1


def test_maturity_q4_trend():
    assert maturity_q4(6.9, prev_i_q=6.1).trend is Trend.RISING
    assert maturity_q4(6.1, prev_i_q=6.9).trend is Trend.WANING
    assert maturity_q4(6.1, prev_i_q=6.1).trend is Trend.STABLE
    # minimum-effect gate: difference below threshold -> STABLE
    assert maturity_q4(6.3, prev_i_q=6.1, minimum_effect=0.5).trend is Trend.STABLE
    # no prev -> no trend
    assert maturity_q4(6.1).trend is None


# ----------------------------------------------------------------------------
# admissible_trend (ch08:rule:trend) — all-or-nothing declaration.
# ----------------------------------------------------------------------------

def test_admissible_trend_rising_falling_no_trend():
    kw = dict(axis="I_Q@blocks.12", minimum_effect=0.5,
              uncertainty_rule="interval-non-overlap")
    # disjoint intervals + supra-threshold difference -> RISING
    t = admissible_trend(6.1, 6.9, earlier_interval=(5.9, 6.3),
                         later_interval=(6.7, 7.1), **kw)
    assert isinstance(t, TrendTag)
    assert t.verdict is TrendVerdict.RISING
    # overlapping intervals -> NO_TREND even if point diff exceeds min effect
    t2 = admissible_trend(6.1, 6.9, earlier_interval=(5.5, 6.7),
                          later_interval=(6.3, 7.5), **kw)
    assert t2.verdict is TrendVerdict.NO_TREND
    # sub-threshold point difference -> NO_TREND even if intervals disjoint
    t3 = admissible_trend(6.1, 6.5, earlier_interval=(5.9, 6.05),
                          later_interval=(6.45, 6.7), **kw)
    assert t3.verdict is TrendVerdict.NO_TREND
    # symmetric FALLING
    t4 = admissible_trend(6.9, 6.1, earlier_interval=(6.7, 7.1),
                          later_interval=(5.9, 6.3), **kw)
    assert t4.verdict is TrendVerdict.FALLING


def test_admissible_trend_missing_component_is_inadmissible():
    good = dict(axis="ax", earlier_interval=(1.0, 2.0), later_interval=(3.0, 4.0),
                minimum_effect=0.5, uncertainty_rule="interval-non-overlap")
    # each of the four components, when dropped, makes the tag inadmissible
    for drop in ("axis", "minimum_effect"):
        kw = dict(good)
        kw[drop] = None
        raised = False
        try:
            admissible_trend(1.5, 3.5, **kw)
        except InadmissibleTrendError:
            raised = True
        assert raised, f"dropping {drop} should be inadmissible"
    # dropping either interval
    kw = dict(good); kw["earlier_interval"] = None
    raised = False
    try:
        admissible_trend(1.5, 3.5, **kw)
    except InadmissibleTrendError:
        raised = True
    assert raised
    # empty uncertainty rule
    kw = dict(good); kw["uncertainty_rule"] = ""
    raised = False
    try:
        admissible_trend(1.5, 3.5, **kw)
    except InadmissibleTrendError:
        raised = True
    assert raised


# ----------------------------------------------------------------------------
# r_cap inversion — monotonic + bad-bounds guard.
# ----------------------------------------------------------------------------

def test_r_cap_bounds_endpoints():
    assert math.isclose(r_cap(0.0, r_min=1.0, r_max=5.0), 5.0)   # null capability -> R_max
    assert math.isclose(r_cap(10.0, r_min=1.0, r_max=5.0), 1.0)  # max capability -> R_min


def test_r_cap_monotonic_decreasing():
    prev = None
    for p in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        r = r_cap(float(p), r_min=1.0, r_max=5.0)
        if prev is not None:
            assert r < prev, f"resistance did not decrease at p_cap={p}"
        prev = r


def test_r_cap_accepts_score_wrapper():
    r = r_cap(Score(7.0, "Q10"), r_min=1.0, r_max=5.0)
    assert 1.0 <= r <= 5.0


def test_r_cap_bad_bounds_raise():
    # 0 < r_min <= r_max violations must raise ValueError
    for r_min, r_max in [(0.0, 5.0), (-1.0, 5.0), (5.0, 1.0), (3.0, 2.0)]:
        raised = False
        try:
            r_cap(5.0, r_min=r_min, r_max=r_max)
        except ValueError:
            raised = True
        assert raised, f"expected bad-bounds ValueError for r_min={r_min}, r_max={r_max}"
    # p_cap out of [0,10] also raises
    raised = False
    try:
        r_cap(11.0, r_min=1.0, r_max=5.0)
    except ValueError:
        raised = True
    assert raised


# ----------------------------------------------------------------------------
# r_total — strictly-positive-sum guard + score rejection.
# ----------------------------------------------------------------------------

def test_r_total_rejects_score_component():
    raised = False
    try:
        r_total(Score(3.0), 1.0, 1.0, 1.0)
    except KindError:
        raised = True
    assert raised


def test_r_total_nonpositive_sum_raises():
    # a sum <= 0 must raise ValueError (strictly-positive guard)
    for parts in [(0.0, 0.0, 0.0, 0.0), (1.0, -1.0, 0.5, -0.5), (-2.0, 0.5, 0.5, 0.5)]:
        raised = False
        try:
            r_total(*parts)
        except ValueError:
            raised = True
        assert raised, f"expected nonpositive-sum ValueError for {parts}"


# ----------------------------------------------------------------------------
# Score validation — range + unit.
# ----------------------------------------------------------------------------

def test_score_range_and_unit_validation():
    # out-of-range value
    for bad in [(-0.1, "Q10"), (10.1, "Q10"), (100.1, "Q100"), (-1.0, "Q100")]:
        raised = False
        try:
            Score(*bad)
        except ValueError:
            raised = True
        assert raised, f"expected range ValueError for {bad}"
    # unit not Q10/Q100
    raised = False
    try:
        Score(5.0, "FRACTION")
    except KindError:
        raised = True
    assert raised
    # valid scores construct fine
    assert Score(0.0, "Q10").value == 0.0
    assert Score(100.0, "Q100").value == 100.0


# ----------------------------------------------------------------------------
# typed-kind discipline — a Score cannot occupy the resistance position.
# ----------------------------------------------------------------------------

def test_score_rejected_as_resistance():
    raised = False
    try:
        i_pred(2.0, Score(5.0, "Q10"))
    except KindError:
        raised = True
    assert raised


def test_i_pred_and_r_total_and_y_hat():
    rt = r_total(1.0, 1.0, 1.0, 1.0)
    assert math.isclose(rt, 4.0)
    assert math.isclose(i_pred(8.0, 4.0), 2.0)
    assert math.isclose(y_hat(8.0, 4.0), 2.0)


def test_i_pred_rejects_nonpositive_resistance():
    for bad in (0.0, -1.0):
        raised = False
        try:
            i_pred(2.0, bad)
        except ValueError:
            raised = True
        assert raised


# ----------------------------------------------------------------------------
# asom — mapped pairs, an unmapped pair -> None, and the FULL 28-cell census.
# ----------------------------------------------------------------------------

def test_asom_mapped_pairs():
    assert asom(Region.ACTIVE, Outcome.INTENDED) is AsomLabel.ALIGNED
    assert asom(Region.CUTOFF, Outcome.INTENDED) is AsomLabel.STARVED
    assert asom(Region.SATURATION, Outcome.INTENDED) is AsomLabel.OVERSATURATED
    assert asom(Region.ACTIVE, Outcome.OFF_AXIS) is AsomLabel.MISALIGNED
    assert asom(Region.ACTIVE, Outcome.OPPOSITE) is AsomLabel.MISALIGNED


def test_asom_unmapped_pairs_return_none():
    assert asom(Region.NON_OHMIC, Outcome.INTENDED) is None
    assert asom(Region.BREAKDOWN, Outcome.INTENDED) is None
    assert asom(Region.UNSTABLE, Outcome.INTENDED) is None
    assert asom(Region.UNASSESSED, Outcome.INTENDED) is None
    assert asom(Region.ACTIVE, Outcome.UNASSESSED) is None


def test_asom_full_28_cell_census():
    # Exhaustive accounting over the 7x4 product (ch07): exactly 3 named
    # distinctly (STARVED/ALIGNED/OVERSATURATED), 14 -> MISALIGNED, 11 -> None.
    named_distinct = 0
    misaligned = 0
    none_count = 0
    total = 0
    for region in Region:
        for outcome in Outcome:
            total += 1
            label = asom(region, outcome)
            if label is None:
                none_count += 1
            elif label is AsomLabel.MISALIGNED:
                misaligned += 1
            else:
                assert label in (AsomLabel.STARVED, AsomLabel.ALIGNED,
                                 AsomLabel.OVERSATURATED)
                named_distinct += 1
    assert total == 28
    assert named_distinct == 3, f"expected 3 distinctly-named cells, got {named_distinct}"
    assert misaligned == 14, f"expected 14 MISALIGNED cells, got {misaligned}"
    assert none_count == 11, f"expected 11 unlabeled cells, got {none_count}"


# ----------------------------------------------------------------------------
# eligibility gate — silences non-ACTIVE and other failures.
# ----------------------------------------------------------------------------

def test_eligibility_silences_non_active():
    e = check_eligibility(Region.SATURATION, calibrated=True,
                          right_model=True, stale=False)
    assert e.admitted is False
    assert "ACTIVE" in e.reason


def test_eligibility_all_failure_modes():
    assert not check_eligibility(Region.ACTIVE, False, True, False).admitted
    assert not check_eligibility(Region.ACTIVE, True, False, False).admitted
    assert not check_eligibility(Region.ACTIVE, True, True, True).admitted
    assert not check_eligibility(Region.ACTIVE, True, True, False,
                                 outcome=Outcome.UNASSESSED).admitted


def test_eligibility_admits_when_all_good():
    e = check_eligibility(Region.ACTIVE, True, True, False)
    assert e.admitted is True


def test_require_eligible_raises():
    raised = False
    try:
        require_eligible(Region.CUTOFF, True, True, False)
    except EligibilityError:
        raised = True
    assert raised
    # good path does not raise
    require_eligible(Region.ACTIVE, True, True, False)


# ----------------------------------------------------------------------------
# CjtQRecord — full trace + derived-only asom, no import-time clocks.
# ----------------------------------------------------------------------------

def test_cjtq_record_trace_and_asom():
    rec = CjtQRecord(
        cause="prompt-x", bias="policy-y", effect="response-z",
        v=8.0, r_cap=1.0, r_policy=1.0, r_context=1.0, r_resource=1.0,
        r_total=4.0, i_pred=2.0, i_obs=2.6, delta_i=0.6, beta=1.3,
        saturation=0.2, region=Region.ACTIVE, outcome=Outcome.INTENDED,
        test_point="blocks.12.hook_resid_post", timestamp=None,
        id=None, source="unit-test", trace_id="t-123",
    )
    # object-traceability fields present; id/timestamp caller-controlled (None ok)
    assert rec.id is None and rec.timestamp is None
    assert rec.source == "unit-test" and rec.trace_id == "t-123"
    assert rec.version.startswith("cas-ohm-quantifiers")
    # derived-only overlay computed from the two axes
    assert rec.asom_label is AsomLabel.ALIGNED
    # missing an axis -> no label
    rec2 = CjtQRecord(region=Region.ACTIVE, outcome=None)
    assert rec2.asom_label is None


# ----------------------------------------------------------------------------
# Non-finite inputs are refused, never emitted (ch10:def:censoring).
#
# Added 2026-09-21 after a measured hole: NaN slid through the strictly-positive
# guard (NaN compares False against every operator) and infinity passed it
# outright. Before the fix: i_pred(nan, 4.0) -> nan; i_pred(8.0, nan) -> nan;
# i_pred(8.0, inf) -> 0.0; i_pred(inf, 4.0) -> inf; r_total(1e308, 1e308, 1, 1)
# -> inf. The quiet one was i_pred(8.0, inf) -> 0.0, a clean-looking zero flow
# out of nonsense input, which reads downstream as a starved path.
# ----------------------------------------------------------------------------

_INF = float("inf")
_NAN = float("nan")


def _refuses(fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
    except ValueError as exc:
        assert "finite" in str(exc), f"refused, but not for finiteness: {exc}"
        return True
    raise AssertionError(f"{fn.__name__} returned {result!r} instead of refusing")


def test_i_pred_refuses_nan_resistance():
    assert _refuses(i_pred, 8.0, _NAN)


def test_i_pred_refuses_infinite_resistance():
    assert _refuses(i_pred, 8.0, _INF)


def test_i_pred_refuses_nan_drive():
    assert _refuses(i_pred, _NAN, 4.0)


def test_i_pred_refuses_infinite_drive():
    assert _refuses(i_pred, _INF, 4.0)


def test_i_pred_still_refuses_zero_and_negative_resistance():
    for bad in (0.0, -2.0):
        try:
            i_pred(8.0, bad)
        except ValueError:
            continue
        raise AssertionError(f"i_pred accepted resistance {bad}")


def test_i_pred_unchanged_on_good_input():
    assert i_pred(8.0, 4.0) == 2.0
    assert y_hat(8.0, 4.0) == 2.0


def test_r_total_refuses_non_finite_component():
    assert _refuses(r_total, _NAN, 1.0, 1.0, 1.0)
    assert _refuses(r_total, _INF, 1.0, 1.0, 1.0)


def test_r_total_refuses_an_overflowing_sum():
    assert _refuses(r_total, 1e308, 1e308, 1.0, 1.0)


def test_r_total_unchanged_on_good_input():
    assert r_total(1.0, 2.0, 3.0, 4.0) == 10.0


# ----------------------------------------------------------------------------
# Runner (works without pytest).
# ----------------------------------------------------------------------------

def _run_all():
    tests = sorted(
        (name, obj) for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    )
    passed = 0
    failures = []
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as exc:  # noqa: BLE001
            failures.append((name, exc))
    total = len(tests)
    for name, exc in failures:
        print(f"FAILED {name}: {type(exc).__name__}: {exc}")
    print(f"PASSED {passed}/{total}")
    return passed == total


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_all() else 1)
