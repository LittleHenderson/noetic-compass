"""Evidence store: break-location reporting and concurrent-append safety.

Born from the July chain break: record 11 linked to a predecessor hash absent
from the file, because append derived its link from the sidecar state (which
had diverged from the file) with no cross-process lock. The suite's job here:
the verifier must NAME a break, and the race must be impossible to reintroduce.
"""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from cas_forex.evidence_store import EvidenceStore
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus


def _packet(i: int) -> ForexEvidencePacket:
    packet = ForexEvidencePacket(
        packet_id=f"packet-{i}",
        trace_id=f"trace-{i}",
        status=PacketStatus.SUPPRESSED,
        notes=[f"integrity-test-{i}"],
    )
    packet.finalize()
    return packet


def test_clean_chain_verifies_with_full_prefix(tmp_path):
    store = EvidenceStore(tmp_path / "chain.jsonl", run_id="t")
    for i in range(5):
        store.append(_packet(i))
    report = store.verify_chain_report()
    assert report["verified"] is True
    assert report["verified_prefix_records"] == report["record_count"] == 5
    assert report["break_event_seq"] is None


def test_broken_link_is_located_and_named(tmp_path):
    """Reproduce the July damage shape: rewrite a mid-chain record so its
    successor links to a ghost, and demand the verifier name record + reason."""
    store = EvidenceStore(tmp_path / "chain.jsonl", run_id="t")
    for i in range(6):
        store.append(_packet(i))
    path = tmp_path / "chain.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    # replace record 3 with a self-consistent but different record (new hash)
    replacement = dict(rows[3])
    replacement["packet"] = dict(replacement["packet"], notes=["REWRITTEN"])
    replacement.pop("record_hash")
    replacement["record_hash"] = EvidenceStore._sha256(replacement)
    rows[3] = replacement
    path.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n", encoding="utf-8")

    report = store.verify_chain_report()
    assert report["verified"] is False
    # record 3 itself may fail packet-hash checks, or record 4 fails the link -
    # either way the break must be located at 3 or 4 with a named reason.
    assert report["break_event_seq"] in (3, 4)
    assert report["break_reason"] in ("broken_link", "packet_hash_mismatch", "packet_tampered")
    assert report["verified_prefix_records"] == report["break_event_seq"]
    assert report["break_detail"]


def test_append_derives_chain_from_file_not_sidecar_state(tmp_path):
    """State/file divergence must not corrupt the chain: the file is the truth."""
    store = EvidenceStore(tmp_path / "chain.jsonl", run_id="t")
    for i in range(3):
        store.append(_packet(i))
    # sabotage the sidecar to simulate the pre-fix divergence
    state_path = tmp_path / "chain.jsonl.state"
    state_path.write_text(json.dumps({"record_count": 99, "head_hash": "ghost"}), encoding="utf-8")

    store.append(_packet(3))
    rows = [json.loads(l) for l in (tmp_path / "chain.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[3]["event_seq"] == 3, "seq must continue the FILE, not the corrupted state"
    assert rows[3]["previous_record_hash"] == rows[2]["record_hash"], (
        "link must point at the real file tail, never the sidecar's ghost head"
    )
    # append also repaired the sidecar checkpoint, so the chain verifies again
    assert store.verify_chain_report()["verified"] is True


def _append_worker(args: tuple[str, int, int]) -> int:
    path, start, n = args
    store = EvidenceStore(Path(path), run_id="race")
    for i in range(start, start + n):
        store.append(_packet(i))
    return n


def test_concurrent_processes_cannot_break_the_chain(tmp_path):
    """Four real processes appending simultaneously; the chain must verify."""
    path = str(tmp_path / "race.jsonl")
    jobs = [(path, base, 10) for base in (0, 100, 200, 300)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(_append_worker, jobs)) == 40

    store = EvidenceStore(Path(path), run_id="race")
    report = store.verify_chain_report()
    assert report["record_count"] == 40
    assert report["verified"] is True, report
