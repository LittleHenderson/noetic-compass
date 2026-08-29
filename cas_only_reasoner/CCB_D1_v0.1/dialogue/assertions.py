"""CCB-D1: the SESSION ASSERTION STORE.

What the user told the machine this session - kept SEPARATE from the
verified knowledge store, never silently merged. Records are
append-only; lifecycle changes (SUPERSEDED / RETRACTED / CONTESTED)
keep the record in the audit history. Erasing a retracted record
would make the machine forget that it forgot.

Truth status uses the CAS-Sem vocabulary: a user assertion enters as
GIVEN (stated by a source, not independently verified). source_class
answers "who said this?"; truth_status answers "how well established
is it?" - different questions, never conflated.

ONLY the TransactionCoordinator (intents.py) may mutate this store.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Dict, List, Optional

LIFECYCLE = ("ACTIVE", "SUPERSEDED", "RETRACTED", "CONTESTED")

# CAS-Sem truth vocabulary (CAS_SEM_v0.1/cassem/truth.py) - reused,
# never duplicated
TRUTH_STATUSES = ("GIVEN", "ASSUMED", "DERIVED", "OBSERVED",
                  "VERIFIED", "CONTRADICTED")

SOURCE_CLASSES = ("USER_ASSERTED",)


class AssertionStoreError(Exception):
    pass


def record_digest(record: Dict) -> str:
    payload = {k: v for k, v in record.items() if k != "record_digest"}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str)
        .encode("utf-8")).hexdigest()[:16]


class SessionAssertionStore:
    """Append-only, session-scoped, deterministic (sequence ids and
    logical ticks - no wall clock, so replay reproduces every id)."""

    def __init__(self, session_id: str = "session") -> None:
        self.session_id = session_id
        self.records: List[Dict] = []
        self._seq = 0

    # -- reads ---------------------------------------------------------
    def next_id(self) -> str:
        return f"a{self._seq + 1}"

    def get(self, assertion_id: str) -> Optional[Dict]:
        for record in self.records:
            if record["assertion_id"] == assertion_id:
                return record
        return None

    def active(self) -> List[Dict]:
        return [r for r in self.records
                if r["lifecycle_status"] == "ACTIVE"]

    def contested(self) -> List[Dict]:
        return [r for r in self.records
                if r["lifecycle_status"] == "CONTESTED"]

    def to_json(self) -> List[Dict]:
        return copy.deepcopy(self.records)

    # -- mutations: COORDINATOR-ONLY entry points ----------------------
    def _append_committed(self, record: Dict) -> Dict:
        """Called by the TransactionCoordinator alone. The record
        arrives fully built; the append is the atomic commit point."""
        if record["assertion_id"] != self.next_id():
            raise AssertionStoreError(
                f"non-sequential assertion id "
                f"{record['assertion_id']!r} (expected "
                f"{self.next_id()!r})")
        self.records.append(record)
        self._seq += 1
        return record

    def _set_lifecycle(self, assertion_id: str, status: str,
                       reason: str, turn_id: str) -> Dict:
        """Called by the TransactionCoordinator alone."""
        record = self.get(assertion_id)
        if record is None:
            raise AssertionStoreError(
                f"no assertion {assertion_id!r}")
        if status not in LIFECYCLE:
            raise AssertionStoreError(f"unknown lifecycle {status!r}")
        if record["lifecycle_status"] == "RETRACTED":
            raise AssertionStoreError(
                f"{assertion_id} is RETRACTED - retracted records "
                f"are immutable audit history")
        record["lifecycle_status"] = status
        record.setdefault("lifecycle_history", []).append(
            {"status": status, "reason": reason, "turn_id": turn_id})
        record["record_digest"] = record_digest(record)
        return record
