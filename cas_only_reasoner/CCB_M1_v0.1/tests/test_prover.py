"""CAS governs the search; the checker still decides."""

from cas_math.expr import from_json
from cas_math.prover import search


SQ = {"kind": "pow", "exp": 2, "base": {"kind": "add", "terms": [
    {"kind": "var", "name": "x"}, {"kind": "num", "q": "1"}]}}
X2_2X_1 = {"kind": "add", "terms": [
    {"kind": "pow", "exp": 2, "base": {"kind": "var", "name": "x"}},
    {"kind": "mul", "factors": [{"kind": "num", "q": "2"},
                                {"kind": "var", "name": "x"}]},
    {"kind": "num", "q": "1"}]}
X2_3X_1 = {"kind": "add", "terms": [
    {"kind": "pow", "exp": 2, "base": {"kind": "var", "name": "x"}},
    {"kind": "mul", "factors": [{"kind": "num", "q": "3"},
                                {"kind": "var", "name": "x"}]},
    {"kind": "num", "q": "1"}]}


def test_search_with_only_square_expand_uses_it():
    found = search(from_json(SQ), from_json(X2_2X_1), ["square_expand"])
    assert found is not None
    assert found[0]["rule"] == "square_expand"


def test_any_found_proof_is_checker_verified():
    from cas_math.checker import check
    found = search(from_json(SQ), from_json(X2_2X_1),
                   ["commute_add", "associate_add", "distribute",
                    "square_expand"])
    assert found is not None
    outcome = check(from_json(SQ), from_json(X2_2X_1), found)
    assert outcome.verdict == "VERIFIED"


def test_search_returns_none_when_unreachable():
    found = search(from_json(SQ), from_json(X2_3X_1),
                   ["commute_add", "associate_add", "distribute",
                    "square_expand", "square_sum"])
    assert found is None
