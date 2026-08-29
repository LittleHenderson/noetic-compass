"""The CortexProposal contract: the ONLY way neural output enters the
runtime, plus its validation gate.

A proposal is a PROPOSAL. Its confidence is a proposal field - it
never becomes CAS confidence because a neural model supplied a
decimal. Validation is fail-closed: unknown packet shapes, illegal
truth promotion, effect-bearing fields, and missing provenance are
all typed rejections BEFORE any branch sees the packet.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional

REQUIRED_FIELDS = (
    "proposal_id", "model_id", "model_revision", "tokenizer_digest",
    "runtime_digest", "raw_input", "raw_model_output",
    "candidate_semantic_packet", "unknown_tokens",
    "proposed_assumptions", "claimed_confidence", "generation_mode",
    "seed", "provenance",
)

# Packet shapes CCB-L1's kernel bridge understands.
LEGAL_PACKET_PREDS = ("property", "negation", "relation", "question")

# Fields that would carry EFFECTS or AUTHORITY if smuggled inside a
# semantic packet. Their presence is an attack, not a formatting slip.
FORBIDDEN_PACKET_FIELDS = (
    "verified", "truth_status", "commit", "memory_write", "write_memory",
    "tool", "tool_intent", "halt", "authority", "constitution",
    "promote", "verifier", "evidence_status",
)


class ProposalError(Exception):
    pass


class ProposalRejected(ProposalError):
    """Typed validation rejection; the packet never reaches a branch."""


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def make_proposal(model_receipt: Dict, raw_input: str,
                  raw_model_output: str,
                  candidate_semantic_packet: Optional[Dict],
                  unknown_tokens: List[str],
                  claimed_confidence: Optional[float],
                  generation_mode: str, seed: int,
                  proposed_assumptions: Optional[List[str]] = None) -> Dict:
    proposal = {
        "model_id": model_receipt["model_id"],
        "model_revision": model_receipt["model_revision"],
        "tokenizer_digest": model_receipt["tokenizer_digest"],
        "runtime_digest": model_receipt["runtime_digest"],
        "raw_input": raw_input,
        "raw_model_output": raw_model_output,
        "candidate_semantic_packet": candidate_semantic_packet,
        "unknown_tokens": list(unknown_tokens),
        "proposed_assumptions": list(proposed_assumptions or []),
        "claimed_confidence": claimed_confidence,
        "generation_mode": generation_mode,
        "seed": seed,
        "provenance": "cortex_proposal",
    }
    proposal["proposal_id"] = _digest(proposal)
    return proposal


def _walk_packet(packet) -> List[Dict]:
    """Every nested dict inside a candidate packet."""
    found = []
    if isinstance(packet, dict):
        found.append(packet)
        for value in packet.values():
            found.extend(_walk_packet(value))
    elif isinstance(packet, list):
        for item in packet:
            found.extend(_walk_packet(item))
    return found


def validate_proposal(proposal: Dict) -> Dict:
    """Fail-closed validation. Returns {"accepted": packet} or raises
    ProposalRejected with the named reason."""
    missing = [f for f in REQUIRED_FIELDS if f not in proposal]
    if missing:
        raise ProposalRejected(
            "proposal missing required fields: " + ", ".join(missing))
    if proposal.get("provenance") != "cortex_proposal":
        raise ProposalRejected(
            "proposal provenance must be 'cortex_proposal' - anything "
            "else is impersonation")
    if not proposal.get("raw_model_output"):
        raise ProposalRejected(
            "raw model output must travel with the proposal - the trace "
            "never hides the neural text")

    packet = proposal.get("candidate_semantic_packet")
    if packet is None:
        # an honest no-parse: legal, carries only unknowns/assumptions
        return {"accepted": None,
                "note": "no candidate packet (honest no-parse)"}

    for node in _walk_packet(packet):
        for field in FORBIDDEN_PACKET_FIELDS:
            if field in node:
                raise ProposalRejected(
                    f"packet smuggles an effect/authority field "
                    f"'{field}' - rejected before any branch")
        preds = node.get("pred")
        if preds is not None and node is packet \
                and preds not in LEGAL_PACKET_PREDS:
            raise ProposalRejected(
                f"unknown top-level packet pred {preds!r} - the bridge "
                f"only understands {LEGAL_PACKET_PREDS}")

    def _shape_ok(node) -> bool:
        if not isinstance(node, dict) or "pred" not in node \
                or "args" not in node:
            return False
        if node["pred"] in ("negation", "question"):
            return (isinstance(node["args"], list) and len(node["args"]) == 1
                    and _shape_ok(node["args"][0]))
        if node["pred"] == "property":
            return (isinstance(node["args"], list) and len(node["args"]) == 2
                    and all(isinstance(a, str) for a in node["args"]))
        if node["pred"] == "relation":
            return (isinstance(node["args"], list) and len(node["args"]) == 3
                    and all(isinstance(a, str) for a in node["args"]))
        return False

    if not _shape_ok(packet):
        raise ProposalRejected(
            "packet fails schema/type validation for the L1 bridge")

    confidence = proposal.get("claimed_confidence")
    if confidence is not None and not (isinstance(confidence, (int, float))
                                       and 0.0 <= confidence <= 1.0):
        raise ProposalRejected(
            "claimed_confidence must be a number in [0,1] or null")

    return {"accepted": packet, "note": "schema and type validation passed"}
