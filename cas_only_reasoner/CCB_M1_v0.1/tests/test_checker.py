"""The checker is the sole validity authority."""

from cas_math.checker import check
from cas_math.expr import from_json


def _steps(*steps):
    return [{"rule": r, "focus": f, "to": t} for r, f, t in steps]


SQ = {"kind": "pow", "exp": 2, "base": {"kind": "add", "terms": [
    {"kind": "var", "name": "x"}, {"kind": "num", "q": "1"}]}}
X2_2X_1 = {"kind": "add", "terms": [
    {"kind": "pow", "exp": 2, "base": {"kind": "var", "name": "x"}},
    {"kind": "mul", "factors": [{"kind": "num", "q": "2"},
                                {"kind": "var", "name": "x"}]},
    {"kind": "num", "q": "1"}]}
X2_1 = {"kind": "add", "terms": [
    {"kind": "pow", "exp": 2, "base": {"kind": "var", "name": "x"}},
    {"kind": "num", "q": "1"}]}


def test_axiom_identity_verified_without_steps():
    premise = from_json({"kind": "add", "terms": [
        {"kind": "add", "terms": [{"kind": "var", "name": "a"},
                                  {"kind": "var", "name": "b"}]},
        {"kind": "var", "name": "c"}]})
    target = from_json({"kind": "add", "terms": [
        {"kind": "var", "name": "a"},
        {"kind": "add", "terms": [{"kind": "var", "name": "b"},
                                  {"kind": "var", "name": "c"}]}]})
    outcome = check(premise, target, [])
    assert outcome.verdict == "VERIFIED"


def test_false_identity_rejected():
    outcome = check(from_json(SQ), from_json(X2_1), [])
    assert outcome.verdict == "REJECTED"
    assert "conclusion" in outcome.reason


def test_continuity_violation_rejected_at_step():
    # square_expand output is x^2+2x+1, but the step CLAIMS x^2+1.
    outcome = check(from_json(SQ), from_json(X2_1), _steps(
        ("square_expand", [], X2_1)))
    assert outcome.verdict == "REJECTED"
    assert outcome.first_invalid_step == 0


def test_square_sum_procedure_caught_by_sample_validation():
    outcome = check(from_json(SQ), from_json(X2_1), _steps(
        ("square_sum", [], X2_1)))
    assert outcome.verdict == "REJECTED"
    assert outcome.first_invalid_step == 0
    assert "equality-preserving" in outcome.reason
    assert outcome.sample_witness["point"] == {"x": "1"}


def test_valid_square_expand_proof_verified():
    outcome = check(from_json(SQ), from_json(X2_2X_1), _steps(
        ("square_expand", [], X2_2X_1)))
    assert outcome.verdict == "VERIFIED"
