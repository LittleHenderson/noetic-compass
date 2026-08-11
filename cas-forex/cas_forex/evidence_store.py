"""Append-only local evidence store for CAS Forex packets."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from cas_forex.schemas.evidence import EvidenceReceipt, ForexEvidencePacket

if os.name == "nt":
    import msvcrt
else:  # pragma: no cover - POSIX fallback for CI portability
    import fcntl


@contextmanager
def _append_lock(lock_path: Path) -> Iterator[None]:
    """Cross-process mutual exclusion for appends.

    The 2026-07 chain break (seq 11 linking to a predecessor hash absent from
    the file) came from unlocked read-derive-append across two processes/API
    restarts. One lock file per store; held only for the append critical
    section.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+b")
    try:
        if os.name == "nt":
            # LK_LOCK gives up with OSError after ~10s of contention. An
            # evidence append on a loaded machine must WAIT, not crash - a
            # crashed append under contention is exactly the failure mode that
            # broke the chain in July. Retry indefinitely; the critical section
            # is milliseconds, so real deadlock here would mean a hung process
            # holding the lock, which surfaces as an operational alarm either way.
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    continue
        else:  # pragma: no cover
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


class EvidenceStore:
    """Tamper-evident JSONL store for local Evidence Packets.

    This is not WORM storage. It is a local hash chain with a sidecar state
    checkpoint so content tamper and tail deletion can be detected.
    """

    def __init__(self, path: str | Path = "forex_evidence.jsonl", run_id: str = "default"):
        self.path = Path(path)
        self.state_path = self.path.with_suffix(self.path.suffix + ".state")
        self.run_id = run_id

    def append(self, packet: ForexEvidencePacket, source: str = "runtime") -> EvidenceReceipt:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if packet.packet_hash_sha256 is None:
            packet.finalize()

        with _append_lock(self.path.with_suffix(self.path.suffix + ".lock")):
            # The FILE is the chain; derive the link from its actual tail. The
            # old code trusted the sidecar state for previous/event_seq, so any
            # state/file divergence (crash between the two writes, concurrent
            # process) made the next record chain onto a ghost predecessor -
            # the July seq-11 break. The sidecar remains only as a
            # tail-deletion tripwire, checked by verify_chain.
            tail = self._records()
            if tail and tail[-1].get("record_hash") == "invalid-json":
                raise ValueError(
                    f"refusing to append to {self.path}: existing store has invalid JSON"
                )
            previous = tail[-1].get("record_hash") if tail else None
            event_seq = len(tail)
            payload = packet.model_dump(mode="json")
            record = {
                "run_id": self.run_id,
                "source": source,
                "trace_id": packet.trace_id,
                "packet_id": packet.packet_id,
                "event_seq": event_seq,
                "packet_hash": packet.packet_hash_sha256,
                "previous_record_hash": previous,
                "packet": payload,
            }
            record_hash = self._sha256(record)
            record["record_hash"] = record_hash

            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, sort_keys=True) + "\n")
                f.flush()

            self._write_state({"record_count": event_seq + 1, "head_hash": record_hash})
        return EvidenceReceipt(
            packet_id=packet.packet_id,
            trace_id=packet.trace_id,
            run_id=self.run_id,
            event_seq=event_seq,
            packet_hash=packet.packet_hash_sha256 or "",
            record_hash=record_hash,
            previous_record_hash=previous,
            store_uri=str(self.path),
        )

    def verify_chain(self) -> bool:
        return bool(self.verify_chain_report()["verified"])

    def verify_chain_report(self) -> Dict[str, Any]:
        """Verify the chain and say WHERE and WHY it fails.

        A bare False taught nobody anything: the July break sat undiagnosed for
        weeks as "Evidence chain did not verify." The report names the first
        breaking record, the reason class, and the length of the verified
        prefix, so a defect is a locatable event rather than a mood.
        """
        records = self._records()

        def failure(seq: int, reason: str, detail: str) -> Dict[str, Any]:
            return {
                "verified": False,
                "record_count": len(records),
                "verified_prefix_records": seq,
                "break_event_seq": seq,
                "break_reason": reason,
                "break_detail": detail,
            }

        previous: Optional[str] = None
        for expected_seq, record in enumerate(records):
            record_hash = record.get("record_hash")
            payload = dict(record)
            payload.pop("record_hash", None)
            if record_hash == "invalid-json":
                return failure(expected_seq, "invalid_json", "A line in the store is not valid JSON.")
            if record.get("event_seq") != expected_seq:
                return failure(
                    expected_seq,
                    "sequence_gap",
                    f"stored event_seq={record.get('event_seq')}, expected {expected_seq} - a record was inserted or removed.",
                )
            if record.get("previous_record_hash") != previous:
                return failure(
                    expected_seq,
                    "broken_link",
                    (
                        f"record links to predecessor {str(record.get('previous_record_hash'))[:16]}... "
                        f"but the actual predecessor hash is {str(previous)[:16]}... - "
                        "the predecessor was rewritten after this record was appended (concurrent-writer signature)."
                    ),
                )
            if self._sha256(payload) != record_hash:
                return failure(expected_seq, "record_tampered", "stored record_hash does not match the record's content.")
            packet_data = record.get("packet")
            if not isinstance(packet_data, dict):
                return failure(expected_seq, "packet_missing", "record carries no packet object.")
            packet = ForexEvidencePacket.model_validate(packet_data)
            if packet.packet_hash_sha256 != record.get("packet_hash"):
                return failure(expected_seq, "packet_hash_mismatch", "record's packet_hash disagrees with the embedded packet.")
            if not packet.verify_hash():
                return failure(expected_seq, "packet_tampered", "embedded packet content does not match its own hash.")
            previous = record_hash

        state = self._read_state()
        if not records:
            state_ok = state.get("record_count", 0) in (0, None)
            return {
                "verified": state_ok,
                "record_count": 0,
                "verified_prefix_records": 0,
                "break_event_seq": None,
                "break_reason": None if state_ok else "state_mismatch",
                "break_detail": None if state_ok else "state sidecar reports records for an empty store.",
            }
        if int(state.get("record_count", -1)) != len(records) or state.get("head_hash") != previous:
            return failure(
                len(records),
                "state_mismatch",
                (
                    f"state sidecar (count={state.get('record_count')}, head={str(state.get('head_hash'))[:16]}...) "
                    f"disagrees with the file (count={len(records)}, head={str(previous)[:16]}...) - "
                    "possible tail deletion."
                ),
            )
        return {
            "verified": True,
            "record_count": len(records),
            "verified_prefix_records": len(records),
            "break_event_seq": None,
            "break_reason": None,
            "break_detail": None,
        }

    def load_trace(self, trace_id: str) -> List[ForexEvidencePacket]:
        return [
            ForexEvidencePacket.model_validate(record["packet"])
            for record in self._records()
            if record.get("trace_id") == trace_id and isinstance(record.get("packet"), dict)
        ]

    @property
    def record_count(self) -> int:
        return len(self._records())

    def _records(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        records: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                return [{"record_hash": "invalid-json"}]
        return records

    def _read_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {"record_count": 0, "head_hash": None}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"record_count": -1, "head_hash": "invalid-state"}

    def _write_state(self, state: Dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _sha256(payload: Dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
