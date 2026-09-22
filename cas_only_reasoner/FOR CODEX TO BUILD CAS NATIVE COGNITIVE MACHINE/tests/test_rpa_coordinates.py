"""Arithmetic tests on declared fixtures, never measured cognitive profiles.

Atlas PDF e1acd28bbdc91e5b33e1f29f2610e75b80960dc55b6907b1dc34311a3a6386ab,
pp. 6-7 and 21: row-major labels, reference centering, synthetic ^6/C fixture.
"""
from decimal import localcontext
from fractions import Fraction
import math
import random
import sys

import pytest

from cncm.model import ContractError
from cncm.rpa_coordinates import (
    CANONICAL_LABELS, CANONICAL_ORDER, COORDINATE_ABS_TOL,
    COORDINATE_LABELS, DENOMINATOR_LABEL, DOMAIN_MAJOR_LABELS,
    DOMAIN_MAJOR_ORDER, NUMERICAL_POLICY, ROUND_TRIP_ABS_TOL,
    ROUND_TRIP_REL_TOL, centered_coordinates, recover_profile,
    reorder_profile, validate_profile,
)


UNIFORM = ("1/40",) * 40
ATLAS_FIXTURE = tuple("61/100" if index == 25 else "1/100" for index in range(40))
RAMP = tuple(str(Fraction(index, 820)) for index in range(1, 41))


def center(profile, reference):
    return centered_coordinates(profile, reference, profile_order=CANONICAL_ORDER,
                                reference_order=CANONICAL_ORDER)


def recover(coordinates, reference):
    return recover_profile(coordinates, reference, reference_order=CANONICAL_ORDER,
                           output_order=CANONICAL_ORDER)


def changed(profile, index, value):
    return profile[:index] + (value,) + profile[index + 1:]


def assert_profile_close(actual, expected):
    assert len(actual) == 40
    assert all(math.isclose(got, float(Fraction(want)), rel_tol=ROUND_TRIP_REL_TOL,
                            abs_tol=ROUND_TRIP_ABS_TOL) for got, want in zip(actual, expected))
    assert math.isclose(math.fsum(actual), 1, rel_tol=0, abs_tol=2e-15)
    assert all(0 < value < 1 for value in actual)


def test_source_label_order_and_denominator_are_explicit():
    assert CANONICAL_ORDER == "^0..^9 x P,C,E,O; row-major"
    assert CANONICAL_LABELS == tuple(f"^{n}/{d}" for n in range(10) for d in "PCEO")
    assert CANONICAL_LABELS[25] == "^6/C"
    assert DENOMINATOR_LABEL == "^9/O"
    assert COORDINATE_LABELS == CANONICAL_LABELS[:39]
    assert DOMAIN_MAJOR_LABELS == tuple(f"^{n}/{d}" for d in "PCEO" for n in range(10))
    assert len(set(CANONICAL_LABELS)) == 40


def test_known_existing_domain_major_order_matches_state_labels():
    from cncm.noetica import COGNITIVE_STATES
    assert tuple(f"^{label[1:]}/{label[0]}" for label in COGNITIVE_STATES) == DOMAIN_MAJOR_LABELS


def test_reorder_preserves_each_labeled_value_and_exact_bytes():
    alternate = reorder_profile(RAMP, source_order=CANONICAL_ORDER, target_order=DOMAIN_MAJOR_ORDER)
    assert {label: value for label, value in zip(DOMAIN_MAJOR_LABELS, alternate)} == dict(zip(CANONICAL_LABELS, RAMP))
    assert reorder_profile(alternate, source_order=DOMAIN_MAJOR_ORDER, target_order=CANONICAL_ORDER) == RAMP
    assert RAMP == tuple(str(Fraction(index, 820)) for index in range(1, 41))


def test_pdf_synthetic_fixture_maps_noetic_six_cognitive_to_index_16_in_alternate():
    assert validate_profile(ATLAS_FIXTURE)[25] == Fraction(61, 100)
    alternate = reorder_profile(ATLAS_FIXTURE, source_order=CANONICAL_ORDER, target_order=DOMAIN_MAJOR_ORDER)
    assert alternate[16] == "61/100"
    assert all(value == "1/100" for index, value in enumerate(alternate) if index != 16)


@pytest.mark.parametrize("order", [None, [], {}, 0, True, "", "row-major", "PCEO", "|T,|A,|f,|E", "^0..^9 x T,A,f,E; row-major"])
def test_unknown_order_never_guessed_or_crosswalked(order):
    with pytest.raises(ContractError):
        reorder_profile(UNIFORM, source_order=order, target_order=CANONICAL_ORDER)
    with pytest.raises(ContractError):
        reorder_profile(UNIFORM, source_order=CANONICAL_ORDER, target_order=order)


def test_order_arguments_are_required():
    with pytest.raises(TypeError):
        reorder_profile(UNIFORM)
    with pytest.raises(TypeError):
        centered_coordinates(UNIFORM, UNIFORM)
    with pytest.raises(TypeError):
        recover_profile((0.0,) * 39, UNIFORM)


@pytest.mark.parametrize("profile", [None, [], list(UNIFORM), (), UNIFORM[:39], UNIFORM + ("1/40",),
    (0.025,) * 40, (Fraction(1, 40),) * 40, ("0.025",) * 40, ("2/80",) * 40,
    changed(UNIFORM, 0, "0"), changed(UNIFORM, 0, "-1/40"), changed(UNIFORM, 0, "1/0"),
    changed(UNIFORM, 0, "1/41"), changed(UNIFORM, 0, True), changed(UNIFORM, 0, "NaN"),
    changed(UNIFORM, 0, "inf"), changed(UNIFORM, 0, " 1/40"), changed(UNIFORM, 0, "01/40"),
    changed(UNIFORM, 0, "1/" + "9" * 40), changed(UNIFORM, 0, "1/" + str(2**128))])
def test_invalid_profile_is_refused_without_normalization_or_imputation(profile):
    with pytest.raises(ContractError):
        validate_profile(profile)
    with pytest.raises(ContractError):
        center(profile, UNIFORM)
    with pytest.raises(ContractError):
        center(UNIFORM, profile)
    with pytest.raises(ContractError):
        recover((0.0,) * 39, profile)


@pytest.mark.parametrize("profile", [UNIFORM, ATLAS_FIXTURE, RAMP])
def test_actual_reference_maps_exactly_to_zero_and_recovers_itself(profile):
    assert center(profile, profile) == (0.0,) * 39
    assert recover((0.0,) * 39, profile) == tuple(float(Fraction(value)) for value in profile)


def test_inverse_zero_is_nonuniform_when_actual_reference_is_nonuniform():
    result = recover((0.0,) * 39, ATLAS_FIXTURE)
    assert result[25] == .61
    assert result != (.025,) * 40


def test_pdf_fixture_has_only_declared_coordinate_displacement_from_uniform():
    z = center(ATLAS_FIXTURE, UNIFORM)
    assert z[25] == pytest.approx(math.log(61), abs=COORDINATE_ABS_TOL)
    assert all(value == 0.0 for index, value in enumerate(z) if index != 25)
    assert_profile_close(recover(z, UNIFORM), ATLAS_FIXTURE)


def test_each_coordinate_matches_the_printed_two_log_ratio_formula():
    p, ref = tuple(map(Fraction, RAMP)), tuple(map(Fraction, ATLAS_FIXTURE))
    expected = tuple(math.log(float(value / p[-1])) - math.log(float(baseline / ref[-1]))
                     for value, baseline in zip(p[:-1], ref[:-1]))
    assert center(RAMP, ATLAS_FIXTURE) == pytest.approx(expected, abs=COORDINATE_ABS_TOL)


def test_denominator_change_shifts_all_thirty_nine_coordinates():
    profile = ("1/100",) * 39 + ("61/100",)
    assert center(profile, UNIFORM) == pytest.approx((-math.log(61),) * 39, abs=COORDINATE_ABS_TOL)
    assert_profile_close(recover(center(profile, UNIFORM), UNIFORM), profile)


def test_reference_change_shifts_chart_without_changing_underlying_profile():
    p, old, new = ATLAS_FIXTURE, RAMP, UNIFORM
    before, after, shift = center(p, old), center(p, new), center(new, old)
    assert after == pytest.approx(tuple(value - delta for value, delta in zip(before, shift)), abs=COORDINATE_ABS_TOL)
    assert_profile_close(recover(before, old), p)
    assert_profile_close(recover(after, new), p)
    assert p == ATLAS_FIXTURE and old == RAMP and new == UNIFORM


@pytest.mark.parametrize("seed", range(20))
def test_nonuniform_profiles_round_trip_using_nonuniform_reference(seed):
    rng = random.Random(seed)
    weights = [rng.randrange(1, 10**9) for _ in range(40)]
    baseline = [rng.randrange(1, 10**9) for _ in range(40)]
    p = tuple(str(Fraction(value, sum(weights))) for value in weights)
    ref = tuple(str(Fraction(value, sum(baseline))) for value in baseline)
    assert_profile_close(recover(center(p, ref), ref), p)


def test_extreme_but_valid_exact_profile_round_trips_without_flooring():
    denominator = 2**120
    profile = (str(Fraction(1, denominator)),) + tuple(str(Fraction(denominator - 1, 39 * denominator)) for _ in range(39))
    assert_profile_close(recover(center(profile, RAMP), RAMP), profile)


def test_near_one_exact_ratio_does_not_disappear_before_logarithm():
    epsilon = Fraction(1, 2**120)
    p = changed(changed(UNIFORM, 0, str(Fraction(1, 40) + epsilon)), 1, str(Fraction(1, 40) - epsilon))
    z = center(p, UNIFORM)
    assert z[0] > 0 and z[1] < 0
    assert z[0] == pytest.approx(float(epsilon * 40), rel=1e-14, abs=0)


def test_mixed_input_orders_and_requested_inverse_output_order():
    p_alt = reorder_profile(ATLAS_FIXTURE, source_order=CANONICAL_ORDER, target_order=DOMAIN_MAJOR_ORDER)
    ref_alt = reorder_profile(RAMP, source_order=CANONICAL_ORDER, target_order=DOMAIN_MAJOR_ORDER)
    z = centered_coordinates(p_alt, RAMP, profile_order=DOMAIN_MAJOR_ORDER, reference_order=CANONICAL_ORDER)
    assert z == center(ATLAS_FIXTURE, RAMP)
    z_other = centered_coordinates(ATLAS_FIXTURE, ref_alt, profile_order=CANONICAL_ORDER, reference_order=DOMAIN_MAJOR_ORDER)
    assert z_other == z
    actual = recover_profile(z, ref_alt, reference_order=DOMAIN_MAJOR_ORDER, output_order=DOMAIN_MAJOR_ORDER)
    assert_profile_close(actual, p_alt)


@pytest.mark.parametrize("coordinates", [None, [], [0.0] * 39, (), (0.0,) * 38, (0.0,) * 40,
    (True,) * 39, ("0",) * 39, (Fraction(0),) * 39, (float("nan"),) * 39,
    (float("inf"),) * 39, (float("-inf"),) * 39, (1 << 1024,) * 39])
def test_bad_coordinates_fail_with_contract_error(coordinates):
    with pytest.raises(ContractError):
        recover(coordinates, RAMP)


@pytest.mark.parametrize("coordinates", [
    (1000.0,) + (0.0,) * 38,
    (-1000.0,) + (0.0,) * 38,
    (sys.float_info.max, -sys.float_info.max) + (0.0,) * 37,
    (-710.0,) + (0.0,) * 38,
    (40.0,) + (-40.0,) * 38,
])
def test_inverse_refuses_nonrepresentable_interior_instead_of_clipping(coordinates):
    with pytest.raises(ContractError):
        recover(coordinates, UNIFORM)


def test_log_sum_exp_can_recover_finite_profile_when_naive_exponentials_overflow():
    # exp(720) overflows before it can be multiplied by the tiny reference
    # components. Combined log weights retain a normal positive denominator.
    denominator = 2**120
    reference = (str(Fraction(1, denominator)),) * 39 + (str(Fraction(denominator - 39, denominator)),)
    with pytest.raises(OverflowError):
        math.exp(720)
    result = recover((720.0,) * 39, reference)
    assert all(math.isfinite(value) and value > 0 for value in result)
    assert sys.float_info.min < result[-1] < 1e-270
    assert math.fsum(result) == pytest.approx(1, abs=2e-15)


def test_decimal_context_does_not_change_coordinate_arithmetic():
    expected = center(ATLAS_FIXTURE, RAMP)
    with localcontext() as context:
        context.prec = 1
        context.Emin = -1
        context.Emax = 1
        assert center(ATLAS_FIXTURE, RAMP) == expected
        assert_profile_close(recover(expected, RAMP), ATLAS_FIXTURE)


def test_calculated_profile_is_not_silently_admitted_as_exact_input():
    with pytest.raises(ContractError):
        validate_profile(recover(center(ATLAS_FIXTURE, RAMP), RAMP))


def test_policy_declares_approximation_and_no_metric_or_measurement_claim():
    assert NUMERICAL_POLICY["denominator_label"] == "^9/O"
    assert NUMERICAL_POLICY["round_trip_relative_tolerance"] == ROUND_TRIP_REL_TOL
    assert NUMERICAL_POLICY["round_trip_absolute_tolerance"] == 0.0
    assert NUMERICAL_POLICY["minimum_inverse_component"] == sys.float_info.min
    assert NUMERICAL_POLICY["metric_status"] == "CHART_ONLY_NOT_FISHER_RAO_OR_TRANSITION_COST"
    assert NUMERICAL_POLICY["measurement_status"] == "NO_MEASUREMENT_PERFORMED"
