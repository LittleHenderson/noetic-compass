"""Independent numeric checks; these tests do not claim native integration."""

from copy import deepcopy
from fractions import Fraction
import random

import pytest

from cncm.canonical import digest
from cncm.model import ContractError
from cncm.nested_model import Equation
from cncm.nested_verification import grounding_inputs, verify_equation_output


def rational(value):
    value = Fraction(value)
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def equation(**changes):
    values = {"variable": "x", "a": "3", "b": "5", "rhs_constant": "2",
              "rhs_terms": (("y", "4"),)}
    values.update(changes)
    return Equation(**values)


def test_grounding_and_current_output_check():
    problem = equation()
    inputs = grounding_inputs(problem, {"y": "6"})
    assert inputs == {"a": "3", "b": "5", "c": "26"}
    report = verify_equation_output(problem, {"y": "6"}, inputs, "7")
    assert report["status"] == "CHECKED"
    assert report["reason"] == "EXACT_SUBSTITUTION_VALID"
    assert report["report_digest"] == digest({k: v for k, v in report.items() if k != "report_digest"})


def test_constant_equation_and_negative_rationals():
    problem = equation(a="-2/3", b="5/7", rhs_constant="2/7", rhs_terms=())
    inputs = grounding_inputs(problem, {})
    assert inputs == {"a": "-2/3", "b": "5/7", "c": "2/7"}
    assert verify_equation_output(problem, {}, inputs, "9/14")["status"] == "CHECKED"


def test_four_dependencies_match_independent_fraction_oracle():
    rng = random.Random(20260916)
    for _ in range(96):
        names = ("d0", "d1", "d2", "d3")
        coefficients = {name: Fraction(rng.choice((-7, -2, 1, 3, 11)), rng.randint(1, 11)) for name in names}
        values = {name: Fraction(rng.randint(-30, 30), rng.randint(1, 13)) for name in names}
        constant = Fraction(rng.randint(-17, 17), rng.randint(1, 7))
        a, b = Fraction(rng.choice((-5, -1, 2, 7))), Fraction(rng.randint(-9, 9), 3)
        problem = equation(a=rational(a), b=rational(b), rhs_constant=rational(constant),
                           rhs_terms=tuple((name, rational(coefficients[name])) for name in names))
        supplied = {name: rational(values[name]) for name in names}
        expected_c = constant + sum((coefficients[name] * values[name] for name in names), Fraction(0))
        expected_x = (expected_c - b) / a  # Independent test oracle only.
        inputs = grounding_inputs(problem, supplied)
        assert inputs == {"a": rational(a), "b": rational(b), "c": rational(expected_c)}
        assert verify_equation_output(problem, supplied, inputs, rational(expected_x))["status"] == "CHECKED"
        assert verify_equation_output(problem, supplied, inputs, rational(expected_x + 1))["status"] == "REJECTED"


@pytest.mark.parametrize("inputs", [
    {"a": "4", "b": "5", "c": "26"},
    {"a": "3", "b": "6", "c": "26"},
    {"a": "3", "b": "5", "c": "29"},
])
def test_wrong_grounded_inputs_are_rejected(inputs):
    report = verify_equation_output(equation(), {"y": "6"}, inputs, "7")
    assert (report["status"], report["reason"]) == ("REJECTED", "GROUNDED_INPUT_MISMATCH")


def test_false_candidate_is_not_replaced_by_a_solved_answer():
    inputs = grounding_inputs(equation(), {"y": "6"})
    report = verify_equation_output(equation(), {"y": "6"}, inputs, "9")
    assert report["status"] == "REJECTED"
    assert report["reason"] == "EQUATION_SUBSTITUTION_MISMATCH"
    assert report["output"] == "9"
    assert "expected_output" not in report


@pytest.mark.parametrize("rhs", ["1", "2"])
def test_zero_leading_coefficient_never_establishes_a_unique_solution(rhs):
    problem = equation(a="0", b="1", rhs_constant=rhs, rhs_terms=())
    report = verify_equation_output(problem, {}, grounding_inputs(problem, {}), "37")
    assert (report["status"], report["reason"]) == ("REJECTED", "ZERO_LEADING_COEFFICIENT")


@pytest.mark.parametrize("values", [{}, {"y": "6", "z": "1"}, {"z": "6"}, [("y", "6")]])
def test_exact_dependency_key_contract(values):
    with pytest.raises(ContractError):
        grounding_inputs(equation(), values)


@pytest.mark.parametrize("value", [True, 6, 6.0, None, "", " 6", "6 ", "+6", "06", "-0", "6/1",
                                   "12/2", "0/2", "1/0", "1/-2", "1/02", "1/2/3", "1e3", "\u0661"])
def test_noncanonical_dependency_values_fail_closed(value):
    with pytest.raises(ContractError):
        grounding_inputs(equation(), {"y": value})


@pytest.mark.parametrize("values", [{"a": "3", "b": "5"},
                                     {"a": "3", "b": "5", "c": "26", "x": "7"},
                                     ["3", "5", "26"]])
def test_exact_grounded_input_fields(values):
    with pytest.raises(ContractError):
        verify_equation_output(equation(), {"y": "6"}, values, "7")


@pytest.mark.parametrize("value", ["7/1", "+7", "07", "-0", True, 7])
def test_output_requires_canonical_rational_text(value):
    with pytest.raises(ContractError):
        verify_equation_output(equation(), {"y": "6"}, {"a": "3", "b": "5", "c": "26"}, value)


def test_raw_equation_dictionary_is_not_an_authorized_typed_equation():
    with pytest.raises(ContractError, match="typed"):
        grounding_inputs(equation().to_dict(), {"y": "6"})


@pytest.mark.parametrize("value", [str(1 << 128), f"1/{1 << 128}", "9" * 10000])
def test_dependency_bit_and_text_limits(value):
    with pytest.raises(ContractError):
        grounding_inputs(equation(), {"y": value})


def test_128_bit_boundary_and_cross_cancellation():
    largest = (1 << 128) - 1
    problem = equation(a="1", b="0", rhs_constant="0", rhs_terms=(("y", str(largest)),))
    inputs = grounding_inputs(problem, {"y": f"1/{largest}"})
    assert inputs == {"a": "1", "b": "0", "c": "1"}
    assert verify_equation_output(problem, {"y": f"1/{largest}"}, inputs, "1")["status"] == "CHECKED"


def test_large_intermediate_can_cancel_before_final_128_bit_input():
    largest = (1 << 128) - 1
    problem = equation(a="1", b="0", rhs_constant="0", rhs_terms=(("u", str(largest)), ("v", str(-largest))))
    assert grounding_inputs(problem, {"u": "2", "v": "2"})["c"] == "0"


@pytest.mark.parametrize("coefficient,value", [("2", str((1 << 128) - 1)), (f"1/{(1 << 128)-1}", "1/2")])
def test_grounded_input_numerator_and_denominator_are_limited(coefficient, value):
    problem = equation(rhs_constant="0", rhs_terms=(("y", coefficient),))
    with pytest.raises(ContractError, match="grounded c"):
        grounding_inputs(problem, {"y": value})


def test_rhs_denominator_growth_is_refused_before_oversize_product():
    # Pairwise coprime Mersenne-prime denominators plus a power of two require
    # a >512-bit intermediate denominator before final c can be constructed.
    terms = (("u", f"1/{(1 << 127)-1}"), ("v", f"1/{(1 << 89)-1}"), ("w", f"1/{(1 << 31)-1}"))
    values = {"u": f"1/{(1 << 107)-1}", "v": f"1/{(1 << 61)-1}", "w": f"1/{(1 << 19)-1}"}
    problem = equation(rhs_constant=f"1/{1 << 127}", rhs_terms=terms)
    with pytest.raises(ContractError, match="intermediate"):
        grounding_inputs(problem, values)


@pytest.mark.parametrize("a,b,output", [("2", "0", str((1 << 512)-1)),
                                        ("1", "1", str((1 << 512)-1)),
                                        ("1", "-1", str(-((1 << 512)-1)))])
def test_output_substitution_growth_is_bounded(a, b, output):
    problem = equation(a=a, b=b, rhs_constant="0", rhs_terms=())
    with pytest.raises(ContractError, match="intermediate"):
        verify_equation_output(problem, {}, grounding_inputs(problem, {}), output)


def test_output_512_bit_boundary_is_admitted_but_513_is_not():
    problem = equation(a="1", b="0", rhs_constant="0", rhs_terms=())
    inputs = grounding_inputs(problem, {})
    assert verify_equation_output(problem, {}, inputs, str((1 << 512)-1))["status"] == "REJECTED"
    with pytest.raises(ContractError, match="bound"):
        verify_equation_output(problem, {}, inputs, str(1 << 512))


def test_reports_are_canonical_context_bound_copies():
    problem = equation(rhs_terms=(("u", "2"), ("v", "3")))
    values = {"v": "4", "u": "6"}
    inputs = grounding_inputs(problem, values)
    original = deepcopy((values, inputs))
    report = verify_equation_output(problem, values, inputs, "7")
    again = verify_equation_output(problem, dict(reversed(list(values.items()))), dict(reversed(list(inputs.items()))), "7")
    assert report == again
    assert (values, inputs) == original
    report["dependency_values"]["u"] = "999"
    report["inputs"]["c"] = "999"
    assert (values, inputs) == original
    changed = verify_equation_output(problem, {"u": "7", "v": "4"}, inputs, "7")
    assert changed["report_digest"] != again["report_digest"]
    assert changed["status"] == "REJECTED"
