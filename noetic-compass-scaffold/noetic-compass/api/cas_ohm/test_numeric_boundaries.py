"""Fabricated numeric regression cases; no observations, model or training.

Each parameter instance is one pytest case, not an independent requirement.
The receipt runner executes these identical bytes against pinned old and new
modules, and keeps each result in a separate, newly dated record.
"""
import importlib.util
import math
import os
import sys
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

SOURCE = Path(os.environ.get("CAS_OHM_TEST_SOURCE", Path(__file__).with_name("quantifiers.py")))
spec = importlib.util.spec_from_file_location("numeric_boundary_subject", SOURCE)
q = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = q
spec.loader.exec_module(q)

BAD = [float("nan"), float("inf"), -float("inf"), 10 ** 400,
       Decimal("1e400"), Decimal("sNaN"), None]
BAD_IDS = ["nan", "positive_infinity", "negative_infinity", "integer_conversion_overflow",
           "decimal_conversion_overflow", "signaling_nan", "missing"]


@pytest.mark.parametrize("bad", BAD, ids=BAD_IDS)
@pytest.mark.parametrize("argument", ["drive", "resistance"])
def test_prediction_refuses_invalid_numbers(bad, argument):
    with pytest.raises(ValueError):
        q.i_pred(bad, 2) if argument == "drive" else q.i_pred(8, bad)


@pytest.mark.parametrize("operation", ["total", "capability", "bound", "score", "known_resistance", "hidden_drive"])
@pytest.mark.parametrize("bad", BAD, ids=BAD_IDS)
def test_other_float_boundaries_refuse_invalid_numbers(operation, bad):
    operations = {
        "total": lambda: q.r_total(1, bad, 1, 1),
        "capability": lambda: q.r_cap(bad, 1, 5),
        "bound": lambda: q.r_cap(5, 1, bad),
        "score": lambda: q.Score(bad),
        "known_resistance": lambda: q.r_hidden(8, 2, bad),
        "hidden_drive": lambda: q.r_hidden(bad, 2, 2),
    }
    with pytest.raises(ValueError):
        operations[operation]()


@pytest.mark.parametrize("field", ["observed", "predicted", "tolerance"])
@pytest.mark.parametrize("bad", BAD, ids=BAD_IDS)
def test_residual_cannot_emit_a_sign_from_invalid_numbers(field, bad):
    kwargs = {"i_obs": 100, "i_pred_value": 0, "tolerance": 0.1}
    kwargs[{"observed": "i_obs", "predicted": "i_pred_value", "tolerance": "tolerance"}[field]] = bad
    with pytest.raises(ValueError):
        q.delta_current(**kwargs)


@pytest.mark.parametrize("operation", ["prediction", "residual", "total"])
def test_finite_operation_overflow_is_rejected(operation):
    operations = {
        "prediction": lambda: q.i_pred(1e308, 1e-308),
        "residual": lambda: q.delta_current(1e308, -1e308),
        "total": lambda: q.r_total(1e308, 1e308, 1, 1),
    }
    with pytest.raises(ValueError):
        operations[operation]()


@pytest.mark.parametrize("operation", ["residual", "hidden", "maturity", "trend"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.1, Decimal("1e-400")],
                         ids=["nan", "infinite", "negative", "underflow"])
def test_thresholds_must_be_finite_nonnegative_and_representable(operation, bad):
    operations = {
        "residual": lambda: q.delta_current(100, 0, tolerance=bad),
        "hidden": lambda: q.r_hidden(8, 0, 2, zero_compat_eps=bad),
        "maturity": lambda: q.maturity_q4(2, minimum_effect=bad),
        "trend": lambda: q.admissible_trend(2, 4, axis="fixture", earlier_interval=(1, 2),
                                          later_interval=(3, 4), minimum_effect=bad),
    }
    with pytest.raises(ValueError):
        operations[operation]()


@pytest.mark.parametrize("bad", BAD, ids=BAD_IDS)
@pytest.mark.parametrize("interval", [None, (1, 3)], ids=["point", "interval"])
def test_unusable_observations_are_censored(bad, interval):
    result = q.r_hidden(8, bad, 2, i_obs_interval=interval)
    assert isinstance(result, q.CensoredResult)
    assert result.censored and result.reason and not result.identifies_mechanism
    assert not hasattr(result, "magnitude")


@pytest.mark.parametrize("point,interval", [
    (0, (1, 2)), (2, (3, 1)), (4, (1, 2)), (2, (1,)), (2, (1, 2, 3)),
    (2, (Decimal("1e400"), Decimal("2e400"))), (2, {"lo": 1, "hi": 3}),
])
def test_invalid_observation_interval_never_admits_ratio(point, interval):
    result = q.r_hidden(8, point, 2, i_obs_interval=interval)
    assert isinstance(result, q.CensoredResult)
    assert result.reason


def test_hidden_finite_input_overflow_is_censored():
    result = q.r_hidden(1e308, 0.1, 2)
    assert isinstance(result, q.CensoredResult)
    assert "finite" in result.reason


def test_independently_observed_zero_preserves_difference_but_censors_ratio():
    residual = q.delta_current(0, 2)
    assert residual.value == -2 and residual.sign is q.SignReading.UNDERSHOOT
    assert residual.identifies_mechanism is False
    assert residual.method_identity == "CAS-OHM-V1-NONIDENTIFYING-RESIDUAL"
    assert isinstance(q.r_hidden(8, 0, 4), q.CensoredResult)


def test_negative_resistance_delta_remains_signed_and_nonidentifying():
    result = q.r_hidden(2, 2, 4)
    assert result.magnitude == result.resistance_delta == -3
    assert result.role is q.ResistanceRole.APPARENT_SAME_SAMPLE
    assert result.identifies_mechanism is False


def test_valid_tiny_positive_interval_does_not_use_point_epsilon():
    result = q.r_hidden(8, 1e-12, 2, i_obs_interval=(0.5e-12, 1.5e-12))
    assert isinstance(result, q.RHidden)
    assert result.r_apparent == 8e12


@pytest.mark.parametrize("field", ["current", "previous", "minimum_effect"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, Decimal("sNaN"), None],
                         ids=["nan", "infinite", "negative", "signaling_nan", "missing"])
def test_maturity_requires_valid_declared_numbers(field, bad):
    if field == "previous" and bad is None:
        assert q.maturity_q4(2, prev_i_q=None).trend is None
        return  # the documented absence of a previous reading remains allowed
    kwargs = {"i_q": 2, "prev_i_q": 1, "minimum_effect": 0}
    kwargs[{"current": "i_q", "previous": "prev_i_q", "minimum_effect": "minimum_effect"}[field]] = bad
    with pytest.raises(ValueError):
        q.maturity_q4(**kwargs)


def test_maturity_saved_value_replays_its_original_band_with_low_decimal_precision():
    value = Decimal("2.49999999999999999999999999999999999999999999999999999")
    with localcontext() as context:
        context.prec = 2
        result = q.maturity_q4(value)
        assert result.band is q.Band.Q1
        assert Decimal(result.i_q_exact) == value
        assert q.maturity_q4(Decimal(result.i_q_exact)).band is q.Band.Q1


def test_exact_trend_does_not_collapse_distinct_decimal_inputs_to_float():
    D = Decimal
    with localcontext() as context:
        context.prec = 2
        result = q.admissible_trend(
            D("1.00000000000000000001"), D("1.00000000000000000004"), axis="fixture",
            earlier_interval=(D("1.00000000000000000000"), D("1.00000000000000000002")),
            later_interval=(D("1.00000000000000000003"), D("1.00000000000000000005")),
            minimum_effect=D("0.000000000000000000001"))
    assert result.verdict is q.TrendVerdict.RISING


@pytest.mark.parametrize("overrides", [
    {"earlier_interval": (3, 1)}, {"later_interval": (5, 3)},
    {"earlier_interval": (1,)}, {"later_interval": (3, 4, 5)},
    {"earlier_interval": (float("nan"), 2)}, {"earlier_point": float("nan")},
    {"axis": ""}, {"uncertainty_rule": "invented-rule"},
])
def test_trend_rejects_invalid_evidence_instead_of_emitting_a_verdict(overrides):
    kwargs = dict(earlier_point=2, later_point=4, axis="fixture", earlier_interval=(1, 2),
                  later_interval=(3, 4), minimum_effect=0.1)
    kwargs.update(overrides)
    with pytest.raises(q.InadmissibleTrendError):
        q.admissible_trend(**kwargs)


def test_import_does_not_change_caller_decimal_context():
    with localcontext() as context:
        context.prec = 3
        fresh_spec = importlib.util.spec_from_file_location("ohm_context_fixture", SOURCE)
        fresh = importlib.util.module_from_spec(fresh_spec)
        sys.modules[fresh_spec.name] = fresh
        fresh_spec.loader.exec_module(fresh)
        assert context.prec == 3
        assert fresh.maturity_q4(Decimal("2.499")).band is fresh.Band.Q1
        assert fresh.maturity_q4(Decimal("2.5")).band is fresh.Band.Q2


def test_decimal_conversion_underflow_is_not_silently_reported_as_zero_drive():
    with pytest.raises(ValueError):
        q.i_pred(Decimal("1e-400"), 2)


@pytest.mark.parametrize("operation", ["maturity", "trend"])
def test_exact_threshold_is_retained_alongside_legacy_float_display(operation):
    threshold = Decimal("0.1000000000000000000001")
    if operation == "maturity":
        result = q.maturity_q4(Decimal("2.1"), prev_i_q=2, minimum_effect=threshold)
        assert result.trend is q.Trend.STABLE
    else:
        result = q.admissible_trend(2, Decimal("2.1"), axis="fixture",
            earlier_interval=(Decimal("1.99"), Decimal("2.01")),
            later_interval=(Decimal("2.09"), Decimal("2.11")), minimum_effect=threshold)
        assert result.verdict is q.TrendVerdict.NO_TREND
    assert result.minimum_effect == 0.1  # legacy approximate display remains
    assert Decimal(result.minimum_effect_exact) == threshold


@pytest.mark.parametrize("bad", [Decimal("1e400"), Decimal("1e-400")], ids=["overflow", "underflow"])
def test_unrepresentable_threshold_is_rejected_before_rational_allocation(monkeypatch, bad):
    def fraction_must_not_run(value):
        raise AssertionError("rational allocation preceded finite float validation")
    monkeypatch.setattr(q, "Fraction", fraction_must_not_run, raising=False)
    with pytest.raises(ValueError):
        q.maturity_q4(2, minimum_effect=bad)
