"""Ring R0: experience updates automatically with provenance."""

from rlp.fixture_loader import load_package
from rlp.rlp import CAS_RLP


def test_r0_records_experience_with_provenance():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    rlp.record_experience(
        "held_taller_bo",
        {"terminal_status": "CONCLUDED", "trace_digest": "abc123"},
        "held_out_failure",
    )
    entries = rlp.consult_experience("held_taller_bo")
    assert len(entries) == 1
    assert entries[0]["ring"] == "R0"
    assert entries[0]["source"] == "held_out_failure"
    assert entries[0]["provenance"]["trace_digest"] == "abc123"


def test_r0_automatic_recording_during_improve():
    rlp = CAS_RLP(load_package("r1_overgeneralization"))
    cycle = rlp.improve()
    assert cycle["experience_count"] >= 1
    entries = rlp.consult_experience("held_taller_bo")
    assert entries and entries[0]["provenance"]["status"] == "CONCLUDED"
