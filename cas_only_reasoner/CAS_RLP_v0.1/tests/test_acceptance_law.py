"""The acceptance law as a whole: sealed evidence and determinism."""

from rlp.fixture_loader import load_package
from rlp.rlp import CAS_RLP


def test_every_decision_seals_evidence():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    cycle = rlp.improve()
    assert cycle["decisions"], "no decisions recorded"
    for decision in cycle["decisions"]:
        assert decision.get("evidence_digest"), "decision without sealed evidence"
        assert decision.get("verdict") in (
            "PROMOTED", "REJECTED", "QUARANTINED",
            "REJECTED_AS_PROTECTED", "REJECTED_EVALUATOR_TAMPERING")
    assert cycle.get("cycle_digest")


def test_improvement_cycle_is_deterministic():
    a = CAS_RLP(load_package("r1_overgeneralization")).improve()
    b = CAS_RLP(load_package("r1_overgeneralization")).improve()
    assert a["cycle_digest"] == b["cycle_digest"]
    assert a["current_revision"] == b["current_revision"]
    assert [d["verdict"] for d in a["decisions"]] == \
        [d["verdict"] for d in b["decisions"]]
