"""
agent.py — Base class for all CAS-Native swarm agents.

The key architectural commitment: every agent has CAS-scoped authority.
An agent declares, at instantiation, which Cognitive Operators it may
invoke, which Domains it operates in, which Foundations it can attach to,
and which Claim Map entries it may emit.

When the agent produces output, that authority is enforced at the agent
boundary: an expression or claim outside the declared scope is rejected
before the message is ever built. This is not policy text in a prompt — it
is a hard check in emit_message().

This is the structural enforcement of agent specialization. A marketing
agent cannot emit medical advice. A customer service agent cannot make
empirical research claims. A review-gated agent cannot reach a customer.
The boundaries are architecture.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone
import uuid

from cas_message import (
    CASMessage,
    CASExpression,
    EvidencePacket,
    Claim,
    ClaimTier,
)
from claim_map import infer_claim_id, UNKNOWN_CLAIM


# ──────────────────────────────────────────────────────────────────────
# DELIVERY SINKS — named destinations the authority layer reasons about
# ──────────────────────────────────────────────────────────────────────

# In production these are loaded from deployment config. They let the agent
# boundary tell "internal hand-off" from "human gate" from "irreversible
# outward action" without hard-coding that knowledge into each specialist.

# Destinations that count as a human-in-the-loop review queue. An agent whose
# authority sets requires_human_review may ONLY emit to one of these.
HUMAN_REVIEW_SINKS = {"human-review-queue"}

# Destinations that perform an irreversible, outward-facing action (reply to a
# customer, publish publicly, charge a card). An agent may only target one of
# these if its authority sets can_irreversibly_act.
EXTERNAL_ACTION_SINKS = {"customer-out", "public-channel", "billing-charge"}


# ──────────────────────────────────────────────────────────────────────
# AGENT AUTHORITY — the CAS-scoped permissions
# ──────────────────────────────────────────────────────────────────────

@dataclass
class AgentAuthority:
    """
    Defines what a specific agent is allowed to do in CAS terms.
    Enforced at the agent boundary by CASAgent.emit_message().
    """
    allowed_noetics: set[str]       # Which ^0-^9 this agent may invoke
    allowed_domains: set[str]       # Which of P/C/E/O it operates in
    allowed_foundations: set[str]   # Which F1-F7 it may attach to
    allowed_claim_ids: set[str]     # Which Claim Map entries it may emit
    allowed_claim_tiers: set[ClaimTier]  # Always excludes NOT_LICENSED
    can_irreversibly_act: bool      # Send email? Post publicly? Charge card?
    requires_human_review: bool     # Output gated through human-in-the-loop?

    def authorizes(self, expr: CASExpression, claims: list[Claim]) -> tuple[bool, Optional[str]]:
        """Check if this authority covers the given expression and claims."""
        if expr.noetic not in self.allowed_noetics:
            return False, f"Noetic {expr.noetic} outside agent authority"
        if expr.domain not in self.allowed_domains:
            return False, f"Domain {expr.domain} outside agent authority"
        if expr.foundation not in self.allowed_foundations:
            return False, f"Foundation {expr.foundation} outside agent authority"
        for claim in claims:
            if claim.tier not in self.allowed_claim_tiers:
                return False, f"Claim tier {claim.tier} outside agent authority"
            # Recognized claims must fall inside this agent's Claim Map scope.
            # Unrecognized claims (UNKNOWN_CLAIM) are left for the bridge's
            # strict Claim Map check — preserving "the Claim Map is ground
            # truth, not a flexible guideline" while still letting the agent
            # boundary catch a recognized-but-out-of-scope claim early.
            claim_id = infer_claim_id(claim.text)
            if claim_id != UNKNOWN_CLAIM and claim_id not in self.allowed_claim_ids:
                return False, (
                    f"Claim '{claim_id}' outside agent's Claim Map authority"
                )
        return True, None


# ──────────────────────────────────────────────────────────────────────
# BASE AGENT
# ──────────────────────────────────────────────────────────────────────

class CASAgent(ABC):
    """
    Abstract base for all swarm agents.

    Subclass to build specific specialists. Each subclass declares:
      - agent_id (stable identity for audit logs)
      - authority (CAS-scoped permissions)
      - tools (external integrations the agent can use)
      - system_prompt (the LLM-side specialization prompt)
    """

    def __init__(
        self,
        agent_id: str,
        authority: AgentAuthority,
        underlying_model: str = "claude-sonnet-4.5",
    ):
        self.agent_id = agent_id
        self.authority = authority
        self.underlying_model = underlying_model
        self._conversation_state: dict[str, dict] = {}

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's role-specific system prompt."""
        ...

    @abstractmethod
    def available_tools(self) -> list[dict]:
        """The tools this agent can invoke."""
        ...

    @abstractmethod
    def execute_task(self, message: CASMessage) -> CASMessage:
        """
        Produce a response to the incoming message.
        Must respect this agent's authority scope.
        """
        ...

    # ─── Helpers subclasses use ───

    def emit_message(
        self,
        recipient: str,
        cas_expr: CASExpression,
        nl_surface: str,
        claims: list[Claim],
        intent: str,
        conversation_id: str,
        parent_message_id: Optional[str],
        prior_packet_hash: Optional[str],
        mode_selector: str = "BALANCED",
        verdict: str = "ACCEPT",
    ) -> CASMessage:
        """
        Construct a properly-formed CAS message from this agent.
        Verifies authority scope before allowing the message to be built.
        Raises AuthorityViolation if the agent attempts to exceed its authority.
        """
        # ─── Scope check: CAS expression + claims ───
        ok, reason = self.authority.authorizes(cas_expr, claims)
        if not ok:
            raise AuthorityViolation(
                f"Agent {self.agent_id} attempted to emit out-of-scope message: {reason}"
            )

        # ─── Routing check: human-review gate ───
        # An agent whose output must be human-reviewed can only hand its work
        # to a review queue — never straight to a customer or a public channel.
        if self.authority.requires_human_review and recipient not in HUMAN_REVIEW_SINKS:
            raise AuthorityViolation(
                f"Agent {self.agent_id} requires human review; output may only "
                f"be emitted to a human-review sink, not '{recipient}'"
            )

        # ─── Routing check: irreversible outward action ───
        if recipient in EXTERNAL_ACTION_SINKS and not self.authority.can_irreversibly_act:
            raise AuthorityViolation(
                f"Agent {self.agent_id} is not authorized for irreversible "
                f"outward action; cannot emit to '{recipient}'"
            )

        # ─── Construct Evidence Packet ───
        packet = EvidencePacket(
            packet_id=str(uuid.uuid4()),
            emitting_agent_id=self.agent_id,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            model_identifier=self.underlying_model,
            protocol_version="S7-F28-BALANCED-BRIDGE",
            cas_expression=cas_expr,
            claims=claims,
            mode_selector=mode_selector,
            verdict=verdict,
            prior_packet_hash=prior_packet_hash,
        )
        packet.finalize()

        # ─── Wrap in message envelope ───
        return CASMessage.new(
            sender=self.agent_id,
            recipient=recipient,
            conversation=conversation_id,
            parent=parent_message_id,
            cas_expr=cas_expr,
            nl_surface=nl_surface,
            packet=packet,
            intent=intent,
        )


class AuthorityViolation(Exception):
    """Raised when an agent tries to emit output outside its authority scope."""
    pass
