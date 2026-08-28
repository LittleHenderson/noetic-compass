"""A counterexample immediately invalidates a universal conjecture."""

from cas_math.counterexample import find_counterexample

SUM_EQ_PRODUCT = {
    "relation": "equal",
    "left": {"kind": "add", "terms": [
        {"kind": "var", "name": "x"}, {"kind": "var", "name": "y"}]},
    "right": {"kind": "mul", "factors": [
        {"kind": "var", "name": "x"}, {"kind": "var", "name": "y"}]},
    "vars": ["x", "y"],
}

SQUARE_GT = {
    "relation": "greater_than",
    "left": {"kind": "pow", "exp": 2, "base": {"kind": "var", "name": "x"}},
    "right": {"kind": "var", "name": "x"},
    "vars": ["x"],
}

TRUE_IDENTITY = {
    "relation": "equal",
    "left": {"kind": "pow", "exp": 2, "base": {"kind": "add", "terms": [
        {"kind": "var", "name": "a"}, {"kind": "var", "name": "b"}]}},
    "right": {"kind": "add", "terms": [
        {"kind": "pow", "exp": 2, "base": {"kind": "var", "name": "a"}},
        {"kind": "mul", "factors": [{"kind": "num", "q": "2"},
                                    {"kind": "var", "name": "a"},
                                    {"kind": "var", "name": "b"}]},
        {"kind": "pow", "exp": 2, "base": {"kind": "var", "name": "b"}}]},
    "vars": ["a", "b"],
}


def test_counterexample_for_sum_eq_product():
    result = find_counterexample(SUM_EQ_PRODUCT)
    assert result["found"] is True
    assert result["point"] == {"x": "1", "y": "1"}
    assert result["left_value"] == "2" and result["right_value"] == "1"


def test_boundary_counterexample_for_square_gt():
    result = find_counterexample(SQUARE_GT)
    assert result["found"] is True
    assert result["point"] == {"x": "1"}


def test_no_counterexample_for_true_identity():
    result = find_counterexample(TRUE_IDENTITY)
    assert result["found"] is False
