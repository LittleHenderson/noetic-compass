"""Independent, exact-binding verification for candidate Neural CJT Effects.

The verifier is deliberately not a ``torch.nn.Module`` and has no persistence
or commit handle.  It checks immutable typed inputs and emits a receipt.  An
operating region is reported on a separate axis from semantic correctness.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from .contracts import canonical_digest, canonical_json, verify_declared_digest
from .types import (
    BiasState,
    CandidateEffect,
    CausePacket,
    OntologyStatus,
    OperatingRegion,
    OperationContract,
    SemanticOutcome,
    VerifierDisposition,
    VerifierReceipt,
)


class VerificationError(ValueError):
    """A verifier call was malformed rather than semantically unsuccessful."""


@dataclass(frozen=True, slots=True)
class SemanticEvidence:
    """Independent exact-content evidence for one candidate Effect.

    ``expected_content=None`` means that no semantic target is available.  It
    produces ``UNASSESSED`` and can never produce ``ACCEPT``.  Authoritative
    JSON floats are rejected by canonical serialization.
    """

    evidence_id: str
    source_id: str
    port_id: str
    expected_content: Mapping[str, Any] | None
    opposite_content: Mapping[str, Any] | None = None
    provenance: tuple[str, ...] = ()
    _expected_json: str | None = field(init=False, repr=False)
    _opposite_json: str | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for name in ("evidence_id", "source_id", "port_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise VerificationError(f"{name} must be a nonempty trimmed string")
        provenance = tuple(self.provenance)
        if any(not isinstance(item, str) or not item for item in provenance):
            raise VerificationError("provenance must contain nonempty strings")
        object.__setattr__(self, "provenance", provenance)
        expected_json = (
            None if self.expected_content is None else canonical_json(self.expected_content)
        )
        opposite_json = (
            None if self.opposite_content is None else canonical_json(self.opposite_content)
        )
        if expected_json is not None and opposite_json == expected_json:
            raise VerificationError("opposite_content cannot equal expected_content")
        object.__setattr__(self, "_expected_json", expected_json)
        object.__setattr__(self, "_opposite_json", opposite_json)

    @property
    def expected_json(self) -> str | None:
        return self._expected_json

    @property
    def opposite_json(self) -> str | None:
        return self._opposite_json


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Two-axis result: physical/operating state plus semantic receipt."""

    operating_region: OperatingRegion
    receipt: VerifierReceipt

    @property
    def semantic_outcome(self) -> SemanticOutcome:
        return self.receipt.semantic_outcome


class IndependentVerifier:
    """Stateless exact-content verifier with no write or publication method."""

    def __init__(
        self,
        verifier_id: str,
        *,
        verifier_version: int = 1,
        policy_id: str = "cas.neural-cjt.exact-semantic-verifier/0.2",
    ) -> None:
        if not isinstance(verifier_id, str) or not verifier_id:
            raise VerificationError("verifier_id must be a nonempty string")
        if (
            not isinstance(verifier_version, int)
            or isinstance(verifier_version, bool)
            or verifier_version < 1
        ):
            raise VerificationError("verifier_version must be an integer >= 1")
        if not isinstance(policy_id, str) or not policy_id:
            raise VerificationError("policy_id must be a nonempty string")
        self.verifier_id = verifier_id
        self.verifier_version = verifier_version
        self.policy_id = policy_id

    @property
    def configuration_digest(self) -> str:
        return canonical_digest(
            {
                "verifier_id": self.verifier_id,
                "verifier_version": self.verifier_version,
                "policy_id": self.policy_id,
            }
        )

    def _binding_failures(
        self,
        cause: CausePacket,
        candidate: CandidateEffect,
        bias: BiasState,
        contract: OperationContract,
        evidence: SemanticEvidence | None,
    ) -> list[str]:
        failures: list[str] = []

        def require(condition: bool, reason: str) -> None:
            if not condition:
                failures.append(reason)

        require(candidate.producer_cjt_id != self.verifier_id, "SELF_VERIFICATION_PROHIBITED")
        if evidence is not None:
            require(
                evidence.source_id != candidate.producer_cjt_id,
                "EVIDENCE_NOT_INDEPENDENT",
            )
            require(
                evidence.port_id in contract.permitted_evidence_ports,
                "EVIDENCE_PORT_NOT_PERMITTED",
            )
        require(candidate.tick == cause.tick, "TICK_MISMATCH")
        require(candidate.parent_cause_id == cause.cause_id, "CAUSE_BINDING_MISMATCH")
        require(candidate.producer_cjt_id == bias.cjt_id, "CJT_BINDING_MISMATCH")
        require(candidate.operation_id == contract.operation_id, "OPERATION_BINDING_MISMATCH")
        require(
            candidate.operation_contract_id == contract.contract_id,
            "OPERATION_CONTRACT_ID_MISMATCH",
        )
        require(
            candidate.operation_contract_digest == contract.contract_digest,
            "OPERATION_CONTRACT_DIGEST_MISMATCH",
        )
        require(candidate.bias_id == bias.bias_id, "BIAS_ID_MISMATCH")
        require(candidate.bias_version == bias.version, "BIAS_VERSION_MISMATCH")
        require(candidate.bias_digest == bias.state_digest, "BIAS_DIGEST_MISMATCH")
        require(candidate.model_digest == bias.theta.model_digest, "MODEL_DIGEST_MISMATCH")
        require(
            bias.stable.registered_operation_id == candidate.operation_id,
            "BIAS_OPERATION_MISMATCH",
        )
        require(cause.cause_kind in contract.accepted_cause_kinds, "CAUSE_KIND_NOT_ACCEPTED")
        require(
            cause.schema_version in contract.accepted_schema_versions,
            "CAUSE_SCHEMA_NOT_ACCEPTED",
        )
        require(
            bias.rpm.readiness.profile_id == contract.readiness_profile_id,
            "READINESS_PROFILE_MISMATCH",
        )
        require(contract.verifier_id == self.verifier_id, "VERIFIER_ID_MISMATCH")
        require(
            contract.verifier_version == self.verifier_version,
            "VERIFIER_VERSION_MISMATCH",
        )
        require(
            contract.verifier_digest == self.configuration_digest,
            "VERIFIER_DIGEST_MISMATCH",
        )
        require(
            verify_declared_digest(contract, "contract_digest"),
            "OPERATION_CONTRACT_CORRUPT",
        )
        require(verify_declared_digest(bias, "state_digest"), "BIAS_STATE_CORRUPT")
        require(
            verify_declared_digest(candidate, "candidate_digest"),
            "CANDIDATE_EFFECT_CORRUPT",
        )
        require(not bias.governance.quarantined, "BIAS_QUARANTINED")
        return sorted(set(failures))

    def _receipt(
        self,
        *,
        cause: CausePacket,
        candidate: CandidateEffect,
        bias: BiasState,
        contract: OperationContract,
        outcome: SemanticOutcome,
        disposition: VerifierDisposition,
        reason_codes: tuple[str, ...],
        evidence_refs: tuple[str, ...],
        repair_required: bool,
    ) -> VerifierReceipt:
        identity_digest = canonical_digest(
            {
                "tick": candidate.tick,
                "verifier_id": self.verifier_id,
                "verifier_version": self.verifier_version,
                "verifier_digest": self.configuration_digest,
                "cause_id": cause.cause_id,
                "candidate_effect_id": candidate.candidate_effect_id,
                "candidate_effect_digest": candidate.candidate_digest,
                "bias_digest": bias.state_digest,
                "contract_digest": contract.contract_digest,
                "outcome": outcome.value,
                "disposition": disposition.value,
                "reason_codes": list(reason_codes),
                "evidence_refs": list(evidence_refs),
            }
        )
        draft = VerifierReceipt(
            receipt_id=f"verifier-receipt-{identity_digest}",
            tick=candidate.tick,
            verifier_id=self.verifier_id,
            verifier_version=self.verifier_version,
            verifier_digest=self.configuration_digest,
            independent=True,
            cause_id=cause.cause_id,
            candidate_effect_id=candidate.candidate_effect_id,
            candidate_effect_digest=candidate.candidate_digest,
            bias_id=bias.bias_id,
            bias_version=bias.version,
            bias_digest=bias.state_digest,
            operation_contract_id=contract.contract_id,
            operation_contract_digest=contract.contract_digest,
            model_digest=candidate.model_digest,
            semantic_outcome=outcome,
            disposition=disposition,
            reason_codes=reason_codes,
            evidence_refs=evidence_refs,
            repair_required=repair_required,
            receipt_digest="0" * 64,
        )
        return replace(
            draft,
            receipt_digest=canonical_digest(draft, omit_keys=("receipt_digest",)),
        )

    def evaluate(
        self,
        cause: CausePacket,
        candidate: CandidateEffect,
        operation_contract: OperationContract,
        evidence: SemanticEvidence | None,
        *,
        bias: BiasState,
        operating_region: OperatingRegion = OperatingRegion.UNASSESSED,
    ) -> VerificationResult:
        """Evaluate one immutable candidate and return a fully bound receipt."""

        if not isinstance(cause, CausePacket):
            raise VerificationError("cause must be a CausePacket")
        if not isinstance(candidate, CandidateEffect):
            raise VerificationError("candidate must be a CandidateEffect")
        if not isinstance(operation_contract, OperationContract):
            raise VerificationError("operation_contract must be an OperationContract")
        if evidence is not None and not isinstance(evidence, SemanticEvidence):
            raise VerificationError("evidence must be SemanticEvidence or None")
        if not isinstance(bias, BiasState):
            raise VerificationError("bias must be a BiasState")
        try:
            region = OperatingRegion(operating_region)
        except (TypeError, ValueError) as error:
            raise VerificationError("operating_region is invalid") from error

        evidence_refs = () if evidence is None else (evidence.evidence_id, *evidence.provenance)
        failures = self._binding_failures(
            cause, candidate, bias, operation_contract, evidence
        )
        if failures:
            receipt = self._receipt(
                cause=cause,
                candidate=candidate,
                bias=bias,
                contract=operation_contract,
                outcome=SemanticOutcome.UNASSESSED,
                disposition=VerifierDisposition.QUARANTINE,
                reason_codes=tuple(failures),
                evidence_refs=evidence_refs,
                repair_required=False,
            )
            return VerificationResult(region, receipt)

        # Numerical health and semantic correctness are separate dimensions.
        # A semantically matching tensor is still not publishable when no
        # route conducted or when the junction is in breakdown.
        if region is OperatingRegion.CUTOFF:
            outcome = SemanticOutcome.UNASSESSED
            disposition = VerifierDisposition.ABSTAIN
            reasons = ("ZERO_FLOW",)
            repair_required = False
        elif region is OperatingRegion.BREAKDOWN:
            outcome = SemanticOutcome.UNKNOWN
            disposition = VerifierDisposition.QUARANTINE
            reasons = ("BREAKDOWN_REGION",)
            repair_required = False
        elif operation_contract.ontology_status is not OntologyStatus.CANONICAL_ADMITTED:
            outcome = SemanticOutcome.UNKNOWN
            disposition = VerifierDisposition.ABSTAIN
            reasons = ("EXPERIMENTAL_OPERATION_NOT_AUTHORITY_ADMITTED",)
            repair_required = False
        elif evidence is None or evidence.expected_json is None:
            outcome = SemanticOutcome.UNASSESSED
            disposition = VerifierDisposition.ABSTAIN
            reasons = ("SEMANTIC_EVIDENCE_MISSING",)
            repair_required = False
        else:
            actual_json = canonical_json(candidate.content)
            if actual_json == evidence.expected_json:
                outcome = SemanticOutcome.INTENDED
                disposition = VerifierDisposition.ACCEPT
                reasons = ("EXACT_SEMANTIC_MATCH",)
                repair_required = False
            elif evidence.opposite_json is not None and actual_json == evidence.opposite_json:
                outcome = SemanticOutcome.OPPOSITE
                disposition = VerifierDisposition.REPAIR
                reasons = ("EXACT_OPPOSITE_MATCH",)
                repair_required = True
            else:
                outcome = SemanticOutcome.OFF_AXIS
                disposition = VerifierDisposition.REPAIR
                reasons = ("SEMANTIC_OFF_AXIS",)
                repair_required = True

        receipt = self._receipt(
            cause=cause,
            candidate=candidate,
            bias=bias,
            contract=operation_contract,
            outcome=outcome,
            disposition=disposition,
            reason_codes=reasons,
            evidence_refs=evidence_refs,
            repair_required=repair_required,
        )
        return VerificationResult(region, receipt)


IndependentEffectVerifier = IndependentVerifier


__all__ = [
    "IndependentEffectVerifier",
    "IndependentVerifier",
    "SemanticEvidence",
    "VerificationError",
    "VerificationResult",
]
