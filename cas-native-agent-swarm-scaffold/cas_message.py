"""
cas_message.py — Inter-agent message format for the CAS-Native swarm.

This is the load-bearing piece that distinguishes a CAS-Native swarm from
generic multi-agent systems. Inter-agent messages are not JSON-wrapped
natural language. They are CAS expressions with Evidence Packets attached.

Every message that crosses an agent boundary in the swarm must:
  1. Carry a CAS expression that validates against the compiler
  2. Include an Evidence Packet documenting the cognitive trace
  3. Tag every claim to its evidence tier (LICENSED, FRAMEWORK_PREDICTED, NOT_LICENSED)
  4. Be cryptographically signed by the emitting agent
  5. Include a hash-chain pointer to the prior message in the conversation

If a message fails any of these checks at the bridge layer, it is rejected
before the receiving agent sees it. Drift between agents is structurally
prevented, not behaviorally hoped for.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Literal
import hashlib
import json
import uuid


# ──────────────────────────────────────────────────────────────────────
# CLAIM TIERS — the reserved-language discipline at message level
# ──────────────────────────────────────────────────────────────────────

ClaimTier = Literal[
    "LICENSED",            # Empirically validated under named protocol
    "FRAMEWORK_PREDICTED", # Predicted by CAS but not yet empirically closed
    "NOT_LICENSED",        # Speculative — must NEVER appear in agent outputs
]


# ──────────────────────────────────────────────────────────────────────
# CAS EXPRESSION — the structured content of an inter-agent message
# ──────────────────────────────────────────────────────────────────────

@dataclass
class CASExpression:
    """
    A CAS expression that has been validated by the compiler.

    Notation reference (canonical CAS v7.7 grammar):
      ^n^D_{Fk}|R
        n  = Noetic Operator (^0-^9)  [a.k.a. Cognitive Operator]
        D  = Domain (P/C/E/O)         [Principled/Cognitive/Evaluative/Operational]
        Fk = Foundation drive (F1-F7) [a.k.a. Core Drive]
        R  = Register (T/A/f/E)       [Transcendent/Analytical/Affective/Embodied]
    """
    noetic: str               # e.g. "^4" — which Cognitive Operator
    domain: str               # P/C/E/O
    foundation: str           # F1-F7
    register: str             # T/A/f/E
    canonical_form: str       # The full string form, e.g. "^4^C_{F2}|A"
    semantic_payload: dict    # Structured content the operator carries
    validated: bool = False   # Compiler validation status
    validator_version: str = "compiler_v7.7"

    def to_dict(self) -> dict:
        return asdict(self)


# ──────────────────────────────────────────────────────────────────────
# CLAIM — a single assertion the agent is making, with evidence tier
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Claim:
    """
    A claim made by an agent. Every claim carries its evidence tier inline.

    The compiler rejects any agent output containing a claim at NOT_LICENSED
    tier. This is the structural enforcement of reserved-language discipline.
    """
    text: str
    tier: ClaimTier
    evidence_protocol: Optional[str] = None  # e.g. "S7-F28-BALANCED-BRIDGE"
    statistical_threshold: Optional[str] = None  # e.g. "p < 1e-11"
    bounds: Optional[list[str]] = None  # What this claim does NOT cover


# ──────────────────────────────────────────────────────────────────────
# EVIDENCE PACKET — per-message audit trail
# ──────────────────────────────────────────────────────────────────────

@dataclass
class EvidencePacket:
    """
    The audit trail emitted with every inter-agent message.
    Bit-identically reproducible. Cryptographically chained.
    WORM-anchored when the swarm runs in production audit mode.
    """
    packet_id: str
    emitting_agent_id: str
    timestamp_utc: str
    model_identifier: str           # Which underlying LLM produced this
    protocol_version: str           # Which η→ε protocol was used
    cas_expression: CASExpression
    claims: list[Claim]
    mode_selector: str              # HIGH_PRECISION | BALANCED | MAX_COVERAGE_TRIAGE
    verdict: str                    # ACCEPT | FLAG_FOR_HUMAN_REVIEW | SUPPRESS
    prior_packet_hash: Optional[str]  # Chain-of-custody linkage
    self_hash: str = ""             # Computed on finalize

    def compute_hash(self) -> str:
        """Bit-identical hash of this packet's content."""
        # Deterministic serialization for hashing
        content = {
            "packet_id": self.packet_id,
            "emitting_agent_id": self.emitting_agent_id,
            "timestamp_utc": self.timestamp_utc,
            "model_identifier": self.model_identifier,
            "protocol_version": self.protocol_version,
            "cas_expression": asdict(self.cas_expression),
            "claims": [asdict(c) for c in self.claims],
            "mode_selector": self.mode_selector,
            "verdict": self.verdict,
            "prior_packet_hash": self.prior_packet_hash,
        }
        canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def finalize(self) -> EvidencePacket:
        """Compute and attach the self-hash. Call before sending."""
        self.self_hash = self.compute_hash()
        return self


# ──────────────────────────────────────────────────────────────────────
# CAS MESSAGE — the inter-agent envelope
# ──────────────────────────────────────────────────────────────────────

@dataclass
class CASMessage:
    """
    The full message that crosses an agent boundary.

    Generic multi-agent systems pass JSON. CAS-Native passes this structure.
    The compiler validates this at the bridge layer before delivery.
    """
    message_id: str
    sender_agent_id: str
    recipient_agent_id: str
    conversation_id: str       # All messages in one task share this
    parent_message_id: Optional[str]
    cas_expression: CASExpression
    natural_language_surface: str  # The realized ε surface text
    evidence_packet: EvidencePacket
    intent_summary: str

    @staticmethod
    def new(
        sender: str,
        recipient: str,
        conversation: str,
        parent: Optional[str],
        cas_expr: CASExpression,
        nl_surface: str,
        packet: EvidencePacket,
        intent: str,
    ) -> CASMessage:
        return CASMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=sender,
            recipient_agent_id=recipient,
            conversation_id=conversation,
            parent_message_id=parent,
            cas_expression=cas_expr,
            natural_language_surface=nl_surface,
            evidence_packet=packet,
            intent_summary=intent,
        )
