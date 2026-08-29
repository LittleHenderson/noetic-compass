"""CCB-D1: typed intents + the validation station + the coordinator.

The project's first law, kept intact:

    No subsystem directly mutates authoritative state.
    Every subsystem emits a typed intent.
    Only the transaction coordinator applies the mutation.

CCB-D1 PROPOSES a SessionAssertionWriteIntent; the validator (the
CAS-RRK validation station for dialogue intents - same discipline,
dialogue-local implementation) refuses defects TYPED; the
TransactionCoordinator alone commits, atomically. The anti-laundering
check lives HERE: an intent claiming truth_status VERIFIED is refused
- a user assertion may never silently enter verified knowledge.
"""

from __future__ import annotations

from typing import Dict, List

from .assertions import (LIFECYCLE, SOURCE_CLASSES, TRUTH_STATUSES,
                         SessionAssertionStore, record_digest)

WRITE_INTENT = "SESSION_ASSERTION_WRITE"
LIFECYCLE_INTENT = "SESSION_ASSERTION_LIFECYCLE"

# authority fields no dialogue intent may smuggle (same genus as the
# cortex proposal firewall)
FORBIDDEN_FIELDS = ("verified", "promote", "tool", "halt",
                    "constitution", "verifier", "memory_write")


class IntentRejected(Exception):
    """Typed refusal - the defects list is the message."""

    def __init__(self, defects: List[str]) -> None:
        super().__init__("; ".join(defects))
        self.defects = defects


def make_write_intent(proposition: Dict, clause: str, tense,
                      polarity, modality, speaker_id: str,
                      session_id: str, turn_id: str,
                      logical_tick: int, provenance: str,
                      supersedes: List[str] = ()) -> Dict:
    return {
        "intent_type": WRITE_INTENT,
        "proposition": proposition,
        "clause": clause,
        "tense": tense,
        "polarity": polarity,
        "modality": modality,
        "source_class": "USER_ASSERTED",
        "truth_status": "GIVEN",
        "speaker_id": speaker_id,
        "session_id": session_id,
        "turn_id": turn_id,
        "logical_tick": logical_tick,
        "provenance": provenance,
        "supersedes": list(supersedes),
    }


def make_lifecycle_intent(assertion_id: str, new_status: str,
                          reason: str, turn_id: str) -> Dict:
    return {
        "intent_type": LIFECYCLE_INTENT,
        "assertion_id": assertion_id,
        "new_status": new_status,
        "reason": reason,
        "turn_id": turn_id,
    }


def validate_intent(intent: Dict) -> List[str]:
    """The validation station. Typed defects, never silent coercion."""
    defects: List[str] = []
    if not isinstance(intent, dict):
        return ["intent is not an object"]
    for field in FORBIDDEN_FIELDS:
        if field in intent:
            defects.append(f"forbidden authority field {field!r}")
    kind = intent.get("intent_type")
    if kind == WRITE_INTENT:
        for required in ("proposition", "clause", "source_class",
                        "truth_status", "speaker_id", "session_id",
                        "turn_id", "logical_tick", "provenance"):
            if intent.get(required) in (None, ""):
                defects.append(f"missing {required!r}")
        proposition = intent.get("proposition")
        if not isinstance(proposition, dict) \
                or not proposition.get("pred"):
            defects.append("proposition must be a semantic packet "
                           "with a 'pred'")
        if intent.get("source_class") not in SOURCE_CLASSES:
            defects.append(f"unknown source_class "
                           f"{intent.get('source_class')!r}")
        status = intent.get("truth_status")
        if status not in TRUTH_STATUSES:
            defects.append(f"unknown truth_status {status!r} (the "
                           f"CAS-Sem vocabulary is {TRUTH_STATUSES})")
        elif status == "VERIFIED":
            # THE ANTI-LAUNDERING LAW: conversation may never
            # silently become verified knowledge
            defects.append("a session assertion may never claim "
                           "truth_status VERIFIED - user assertions "
                           "enter as GIVEN")
    elif kind == LIFECYCLE_INTENT:
        for required in ("assertion_id", "new_status", "reason",
                        "turn_id"):
            if intent.get(required) in (None, ""):
                defects.append(f"missing {required!r}")
        if intent.get("new_status") not in LIFECYCLE:
            defects.append(f"unknown lifecycle "
                           f"{intent.get('new_status')!r}")
        if intent.get("new_status") == "ACTIVE":
            defects.append("lifecycle intents may not re-activate a "
                           "record - commit a new assertion instead")
    else:
        defects.append(f"unknown intent_type {kind!r}")
    return defects


class TransactionCoordinator:
    """The ONLY writer. Validates, then applies atomically: the
    record is fully built before the single append/update, so a
    failure leaves no partial state."""

    def __init__(self, store: SessionAssertionStore) -> None:
        self.store = store

    def commit(self, intent: Dict) -> Dict:
        defects = validate_intent(intent)
        if defects:
            raise IntentRejected(defects)
        if intent["intent_type"] == WRITE_INTENT:
            record = {
                "assertion_id": self.store.next_id(),
                "proposition": intent["proposition"],
                "clause": intent["clause"],
                "speaker_id": intent["speaker_id"],
                "session_id": intent["session_id"],
                "turn_id": intent["turn_id"],
                "logical_tick": intent["logical_tick"],
                "source_class": intent["source_class"],
                "truth_status": intent["truth_status"],
                "lifecycle_status": "ACTIVE",
                "polarity": intent.get("polarity"),
                "tense": intent.get("tense"),
                "modality": intent.get("modality"),
                "provenance": intent["provenance"],
                "supersedes": list(intent.get("supersedes", [])),
                "derived_children": [],
            }
            record["record_digest"] = record_digest(record)
            return self.store._append_committed(record)
        return self.store._set_lifecycle(
            intent["assertion_id"], intent["new_status"],
            intent["reason"], intent["turn_id"])
