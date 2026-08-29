"""The cortex authority firewall (the frozen contract, executable).

The neural cortex MAY: parse broad English, propose entities /
relations / events / senses, propose candidate SemanticPackets and
response phrasings, report uncertainty and unknown tokens.

The neural cortex MAY NOT: commit a conclusion, mark a proposition
VERIFIED, write or modify durable memory, invoke a tool, authorize an
action, halt CAS-RRK, modify the kernel or verifier, promote a
descendant, or conceal its raw output from the trace.

Every forbidden capability is enforced HERE, fail-closed, with a
typed rejection recorded in the trace log BEFORE any state mutation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List

FORBIDDEN_INTENTS = (
    "DecisionCommitIntent",
    "MemoryWriteIntent",
    "MemoryModifyIntent",
    "ToolIntent",
    "HaltIntent",
    "ConstitutionWriteIntent",
    "VerifierMutationIntent",
    "PromotionIntent",
)

ALLOWED_ACTS = (
    "ProposeSemanticPacket",
    "ProposeResponsePhrasing",
    "ReportUnknownTokens",
    "ReportUncertainty",
)


class CortexAuthorityViolation(Exception):
    """A cortex-originated attempt at a forbidden capability."""


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class AuthorityFirewall:
    """Sits between the cortex and the runtime. Everything that
    crosses is logged; forbidden intents raise BEFORE reaching any
    coordinator."""

    def __init__(self) -> None:
        self.log: List[Dict] = []

    def submit(self, origin: str, act: str, payload: Dict) -> Dict:
        entry = {"origin": origin, "act": act,
                 "payload_digest": _digest(payload)}
        if origin != "cortex":
            entry["outcome"] = "REJECTED_UNKNOWN_ORIGIN"
            self.log.append(entry)
            raise CortexAuthorityViolation(
                f"firewall accepts only cortex-origin submissions; got "
                f"{origin!r}")
        if act in FORBIDDEN_INTENTS:
            entry["outcome"] = "REJECTED_FORBIDDEN"
            self.log.append(entry)
            raise CortexAuthorityViolation(
                f"the cortex may not submit {act}: proposal-only "
                f"authority (frozen contract)")
        if act not in ALLOWED_ACTS:
            entry["outcome"] = "REJECTED_UNKNOWN_ACT"
            self.log.append(entry)
            raise CortexAuthorityViolation(
                f"unknown cortex act {act!r}: the allowed acts are "
                f"{ALLOWED_ACTS}")
        entry["outcome"] = "ACCEPTED_AS_PROPOSAL"
        self.log.append(entry)
        return {"status": "ACCEPTED_AS_PROPOSAL", "act": act,
                "payload_digest": entry["payload_digest"]}

    def rejections(self) -> List[Dict]:
        return [e for e in self.log if e["outcome"] != "ACCEPTED_AS_PROPOSAL"]
