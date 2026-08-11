"""Process-pool worker for the evidence-store race test.

Lives OUTSIDE the test module on purpose: ProcessPoolExecutor pickles functions
by qualified module name, and pytest names a collected test module differently
depending on how much of the suite was collected ("test_evidence_store_integrity"
standalone vs "tests.test_evidence_store_integrity" in a full run). Workers
could import the former but not the latter, so the race test passed alone and
failed in the full suite. This module's name is stable either way - conftest
puts tests/ on sys.path, and spawn propagates sys.path to workers.
"""

from __future__ import annotations

from pathlib import Path

from cas_forex.evidence_store import EvidenceStore
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus


def make_packet(i: int) -> ForexEvidencePacket:
    packet = ForexEvidencePacket(
        packet_id=f"packet-{i}",
        trace_id=f"trace-{i}",
        status=PacketStatus.SUPPRESSED,
        notes=[f"integrity-test-{i}"],
    )
    packet.finalize()
    return packet


def append_worker(args: tuple[str, int, int]) -> int:
    path, start, n = args
    store = EvidenceStore(Path(path), run_id="race")
    for i in range(start, start + n):
        store.append(make_packet(i))
    return n
