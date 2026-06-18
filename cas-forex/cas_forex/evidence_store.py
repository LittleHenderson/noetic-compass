"""Append-only local evidence store for CAS Forex packets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from cas_forex.schemas.evidence import EvidenceReceipt, ForexEvidencePacket


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

        state = self._read_state()
        previous = state.get("head_hash")
        event_seq = int(state.get("record_count", 0))
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
        records = self._records()
        previous: Optional[str] = None
        for expected_seq, record in enumerate(records):
            record_hash = record.get("record_hash")
            payload = dict(record)
            payload.pop("record_hash", None)
            if record.get("event_seq") != expected_seq:
                return False
            if record.get("previous_record_hash") != previous:
                return False
            if self._sha256(payload) != record_hash:
                return False
            packet_data = record.get("packet")
            if not isinstance(packet_data, dict):
                return False
            packet = ForexEvidencePacket.model_validate(packet_data)
            if packet.packet_hash_sha256 != record.get("packet_hash"):
                return False
            if not packet.verify_hash():
                return False
            previous = record_hash

        state = self._read_state()
        if not records:
            return state.get("record_count", 0) in (0, None)
        return (
            int(state.get("record_count", -1)) == len(records)
            and state.get("head_hash") == previous
        )

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
