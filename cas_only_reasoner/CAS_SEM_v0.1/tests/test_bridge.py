"""The lift bridge: kernel-style propositions become DERIVED claims."""

from cassem.bridge import lift
from cassem.coherence import CoherenceChecker
from conftest import good_story


def test_lift_produces_derived_claims_that_reprove():
    claims = lift(
        [{"pred": "property", "args": ["dog_1", "brown"]}],
        ["r_prop"],
    )
    assert claims[0]["truth"] == "DERIVED"
    assert claims[0]["derivation"]["conclusion"] == {
        "pred": "property", "args": ["dog_1", "brown"]}

    doc = good_story()
    doc["claims"] = claims + doc["claims"]
    checker = CoherenceChecker(doc)
    assert all(v.law != "derivation_validity" for v in checker.check())
