"""The world-knowledge teaching channel - the STRICTER fact protocol.

Facts are not grammar: a model-generated fact enters PROPOSED, never
VERIFIED. Verification happens against a TRUSTED SOURCE STORE the
teacher does not control. Changing facts (laws, officeholders,
prices, versions) must carry retrieval provenance and a validity
window - the teacher's frozen internal memory is not a source for
them. Contradictory sources yield CONTESTED, never a silent pick.
Every accepted fact lands in its TYPED destination.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional

KNOWLEDGE_LESSON_REQUIRED = ("lesson_id", "claim", "source",
                             "validity", "scope", "confidence",
                             "verification_method", "teacher_model",
                             "provenance")

DESTINATIONS = {
    "stable_fact": "semantic_memory",
    "current_fact": "source_linked_retrieval_record",
    "definition": "cas_sem_concept_record",
    "procedure": "procedural_memory",
    "personal_experience": "episodic_memory",
    "general_pattern": "recipe_or_schema",
    "hard_boundary": "constitutional_memory_SEPARATELY_AUTHORIZED",
}


class KnowledgeError(Exception):
    pass


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class TrustedSourceStore:
    """The verification corpus the TEACHER does not control. v0.1:
    an explicit dict of source_id -> list of attested claims."""

    def __init__(self, sources: Optional[Dict[str, List[str]]] = None):
        self.sources = dict(sources or {})

    def attest(self, claim: str) -> Dict:
        supporting = [sid for sid, claims in self.sources.items()
                      if claim in claims]
        contradicting = [sid for sid, claims in self.sources.items()
                         if ("NOT: " + claim) in claims]
        return {"supporting": supporting,
                "contradicting": contradicting}


class KnowledgeChannel:
    """The verifier channel for world-knowledge lessons - passed to
    ApprenticeshipBoard.teach as the frozen examiner."""

    def __init__(self, trusted: TrustedSourceStore) -> None:
        self.trusted = trusted
        self.records: List[Dict] = []

    def __call__(self, lesson: Dict) -> Dict:
        missing = [f for f in KNOWLEDGE_LESSON_REQUIRED
                   if f not in lesson]
        if missing:
            return {"verdict": "REJECTED_MALFORMED",
                    "evidence": f"missing fields: {missing}"}

        knowledge_type = lesson.get("knowledge_type", "stable_fact")
        if knowledge_type not in DESTINATIONS:
            return {"verdict": "REJECTED_UNKNOWN_TYPE",
                    "evidence": f"unknown knowledge type "
                                f"{knowledge_type!r}"}
        if knowledge_type == "hard_boundary":
            return {"verdict": "REJECTED_SEPARATE_AUTHORIZATION",
                    "evidence": "hard boundaries enter constitutional "
                                "memory only through separate "
                                "authorization, never a teaching "
                                "channel"}

        # CHANGING facts demand retrieval provenance + validity window
        if knowledge_type == "current_fact":
            validity = lesson.get("validity", {})
            if lesson.get("source_kind") != "current_retrieval":
                return {"verdict": "REJECTED_STALE_SOURCE",
                        "evidence": "a changing fact must come from "
                                    "current retrieval, never the "
                                    "teacher's frozen internal memory"}
            if not validity.get("window"):
                return {"verdict": "REJECTED_NO_VALIDITY_WINDOW",
                        "evidence": "changing facts require an "
                                    "explicit validity window"}

        attestation = self.trusted.attest(lesson["claim"])
        if attestation["contradicting"] and attestation["supporting"]:
            status, verdict = "CONTESTED", "STORED_CONTESTED"
        elif attestation["contradicting"]:
            status, verdict = "CONTRADICTED", "REJECTED_CONTRADICTED"
        elif attestation["supporting"]:
            status, verdict = "VERIFIED", "PROMOTED_VERIFIED"
        else:
            # no trusted source speaks: the fact stays PROPOSED - it
            # is never silently upgraded because a model said so
            status, verdict = "PROPOSED", "STORED_PROPOSED"

        record = {
            "claim": lesson["claim"],
            "knowledge_type": knowledge_type,
            "destination": DESTINATIONS[knowledge_type],
            "truth_status": status,
            "source": lesson["source"],
            "validity": lesson["validity"],
            "scope": lesson["scope"],
            "exceptions": lesson.get("exceptions", []),
            "teacher_confidence_informational_only":
                lesson.get("confidence"),
            "attestation": attestation,
            "provenance": lesson["provenance"],
        }
        record["record_digest"] = _digest(record)
        if verdict != "REJECTED_CONTRADICTED":
            self.records.append(record)
        return {"verdict": verdict, "evidence": attestation,
                "record": record}

    # ------------------------------------------------------------------
    def by_status(self, status: str) -> List[Dict]:
        return [r for r in self.records if r["truth_status"] == status]
