"""
bridge.py — The η→ε bridge as inter-agent communication protocol.

In a generic multi-agent system, Agent A's output becomes Agent B's input
directly. Drift, hallucination, and overclaim propagate through the swarm
unchecked.

In a CAS-Native swarm, every message passes through the bridge before
delivery. The bridge:

  1. Validates the CAS expression against the compiler (rejects malformed)
  2. Validates every claim against the Claim Map (rejects NOT_LICENSED tier
     and rejects any tag that disagrees with the Claim Map's classification)
  3. Verifies the Evidence Packet hash chain (rejects tampered packets)
  4. Verifies the protocol version is supported
  5. Delivers the validated message to the recipient

If any validation fails, the bridge rejects the message and emits a
verdict of SUPPRESS with the reason. The recipient agent never sees
the bad message.

The bridge is also the swarm's SECOND line of defense: even if an agent's
own authority check is bypassed or buggy, the bridge independently re-derives
each claim's tier from the Claim Map and catches reserved-language violations.

This is the structural defeat of inter-agent drift.
"""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass

from cas_message import (
    CASMessage,
    CASExpression,
    EvidencePacket,
    Claim,
)
from claim_map import infer_claim_id, tier_of


# ──────────────────────────────────────────────────────────────────────
# VALIDATION RESULTS
# ──────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    passed: bool
    reason: Optional[str] = None
    suppressed_claims: Optional[list[str]] = None


# ──────────────────────────────────────────────────────────────────────
# THE BRIDGE
# ──────────────────────────────────────────────────────────────────────

class CASBridge:
    """
    The inter-agent message validator. Every message goes through this.
    """

    def __init__(self, audit_log_writer=None):
        self.audit_log = audit_log_writer  # WORM-anchored sink in production
        self._last_packet_hash_by_conversation: dict[str, str] = {}

    def validate_and_deliver(
        self,
        message: CASMessage,
        delivery_callback,
    ) -> ValidationResult:
        """
        Run all validations. If they pass, deliver. If any fail,
        suppress the message and emit the failure to the audit log.
        """

        # ─── Validation 1: CAS expression must validate ───
        expr_result = self._validate_cas_expression(message.cas_expression)
        if not expr_result.passed:
            self._log_suppression(message, expr_result.reason)
            return expr_result

        # ─── Validation 2: claim map enforcement ───
        claim_result = self._validate_claims(message.evidence_packet.claims)
        if not claim_result.passed:
            self._log_suppression(message, claim_result.reason)
            return claim_result

        # ─── Validation 3: hash chain integrity ───
        chain_result = self._validate_hash_chain(message)
        if not chain_result.passed:
            self._log_suppression(message, chain_result.reason)
            return chain_result

        # ─── Validation 4: protocol version compatibility ───
        proto_result = self._validate_protocol_version(message.evidence_packet)
        if not proto_result.passed:
            self._log_suppression(message, proto_result.reason)
            return proto_result

        # All checks passed. Update chain pointer. Deliver.
        self._last_packet_hash_by_conversation[message.conversation_id] = (
            message.evidence_packet.self_hash
        )
        self._log_delivery(message)
        delivery_callback(message)
        return ValidationResult(passed=True)

    # ─── Validation helpers ───

    def _validate_cas_expression(self, expr: CASExpression) -> ValidationResult:
        """
        Verify the expression validates against the CAS compiler.
        In production this calls into the compiler service. In scaffold
        form we check the canonical form is well-formed and validated.
        """
        if not expr.validated:
            return ValidationResult(
                passed=False,
                reason="CAS expression not validated by compiler"
            )
        # Verify noetic, domain, foundation, register are in valid ranges
        if expr.noetic not in [f"^{i}" for i in range(10)]:
            return ValidationResult(
                passed=False,
                reason=f"Invalid noetic operator: {expr.noetic}"
            )
        if expr.domain not in ["P", "C", "E", "O"]:
            return ValidationResult(
                passed=False,
                reason=f"Invalid domain: {expr.domain}"
            )
        if expr.foundation not in [f"F{i}" for i in range(1, 8)]:
            return ValidationResult(
                passed=False,
                reason=f"Invalid foundation: {expr.foundation}"
            )
        if expr.register not in ["T", "A", "f", "E"]:
            return ValidationResult(
                passed=False,
                reason=f"Invalid register: {expr.register}"
            )
        return ValidationResult(passed=True)

    def _validate_claims(self, claims: list[Claim]) -> ValidationResult:
        """
        Enforce reserved-language discipline. For every claim, re-derive its
        canonical id from the Claim Map and require that the agent's tag agrees
        with the Claim Map's own classification:

          - An explicit NOT_LICENSED tag is never allowed in agent output.
          - A claim whose id is in the NOT_LICENSED set is suppressed no matter
            how it is tagged (this catches tier-mislabeling / laundering).
          - The tag must match the claim's actual tier. Unrecognized claims
            (not in the Claim Map at all) are rejected — the Claim Map is
            ground truth, not a flexible guideline.

        Checking every tier symmetrically (not just LICENSED) means a
        FRAMEWORK_PREDICTED claim with the wrong id is caught too.
        """
        suppressed = []
        for claim in claims:
            claim_id = infer_claim_id(claim.text)
            actual_tier = tier_of(claim_id)  # None if not in the Claim Map

            # 1. NOT_LICENSED claims cannot appear in agent output, period.
            if claim.tier == "NOT_LICENSED":
                suppressed.append(f"NOT_LICENSED claim attempted: {claim.text}")
                continue

            # 2. Structurally not-licensed but tagged otherwise = laundering.
            if actual_tier == "NOT_LICENSED":
                suppressed.append(
                    f"Claim '{claim.text}' is in NOT_LICENSED set but "
                    f"tagged as {claim.tier}"
                )
                continue

            # 3. The tag must match the Claim Map's classification.
            if actual_tier != claim.tier:
                suppressed.append(
                    f"Claim '{claim.text}' tagged {claim.tier} but Claim Map "
                    f"classifies it as {actual_tier or 'unrecognized'}"
                )
                continue

        if suppressed:
            return ValidationResult(
                passed=False,
                reason="Reserved-language discipline violation",
                suppressed_claims=suppressed,
            )
        return ValidationResult(passed=True)

    def _validate_hash_chain(self, message: CASMessage) -> ValidationResult:
        """
        Verify the Evidence Packet's hash chain is intact.
        """
        # Verify the self-hash matches the computed hash
        expected = message.evidence_packet.compute_hash()
        if message.evidence_packet.self_hash != expected:
            return ValidationResult(
                passed=False,
                reason="Evidence Packet hash mismatch — tampering or corruption"
            )

        # Verify the prior packet pointer is correct for this conversation
        prior_in_conversation = self._last_packet_hash_by_conversation.get(
            message.conversation_id
        )
        if prior_in_conversation is not None:
            if message.evidence_packet.prior_packet_hash != prior_in_conversation:
                return ValidationResult(
                    passed=False,
                    reason=(
                        "Prior packet hash mismatch — chain of custody broken"
                    )
                )
        return ValidationResult(passed=True)

    def _validate_protocol_version(
        self, packet: EvidencePacket
    ) -> ValidationResult:
        """
        Verify the protocol version is one this swarm supports.
        """
        SUPPORTED_PROTOCOLS = {
            "S7-F28-BALANCED-BRIDGE",
            "S7-F28-HIGH-PRECISION",
            "S7-F28-MAX-COVERAGE",
        }
        if packet.protocol_version not in SUPPORTED_PROTOCOLS:
            return ValidationResult(
                passed=False,
                reason=f"Unsupported protocol version: {packet.protocol_version}"
            )
        return ValidationResult(passed=True)

    # ─── Audit logging ───

    def _log_delivery(self, message: CASMessage) -> None:
        if self.audit_log:
            self.audit_log.write({
                "event": "DELIVERED",
                "message_id": message.message_id,
                "from_agent": message.sender_agent_id,
                "to_agent": message.recipient_agent_id,
                "packet_hash": message.evidence_packet.self_hash,
            })

    def _log_suppression(self, message: CASMessage, reason: str) -> None:
        if self.audit_log:
            self.audit_log.write({
                "event": "SUPPRESSED",
                "message_id": message.message_id,
                "from_agent": message.sender_agent_id,
                "to_agent": message.recipient_agent_id,
                "reason": reason,
            })
