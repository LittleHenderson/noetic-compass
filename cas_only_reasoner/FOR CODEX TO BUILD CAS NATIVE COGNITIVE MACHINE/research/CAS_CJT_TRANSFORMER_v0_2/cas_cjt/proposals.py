"""Typed proposal factories shared by inference and learning ticks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

from torch import Tensor

from .artifacts import StoredArtifact, encode_tensor
from .contracts import canonical_digest
from .state import ZERO_DIGEST, content_id, tensor_ref_from_mapping
from .types import (
    AuthorityCapability,
    BiasState,
    CandidateEffect,
    CausePacket,
    OperationContract,
    PhaseRecord,
    StateUpdateIntent,
    TickPhase,
    VerifierReceipt,
)


class ProposalError(ValueError):
    """A neural proposal could not be frozen into an authoritative envelope."""


def freeze_candidate_effect(
    *,
    cause: CausePacket,
    bias: BiasState,
    contract: OperationContract,
    effect_tensor: Tensor,
    semantic_content: Mapping[str, Any],
    uncertainty_ppm: int = 0,
    decoder_digest: str | None = None,
    control_binding_digest: str | None = None,
) -> tuple[CandidateEffect, StoredArtifact]:
    """Store neural values by reference and bind a non-authoritative Effect."""

    reference_mapping, artifact = encode_tensor(effect_tensor, kind="candidate-effect")
    reference = tensor_ref_from_mapping(reference_mapping)
    identity = {
        "tick": cause.tick,
        "parent_cause_id": cause.cause_id,
        "producer_cjt_id": bias.cjt_id,
        "operation_contract_digest": contract.contract_digest,
        "bias_digest": bias.state_digest,
        "model_digest": bias.theta.model_digest,
        "content": dict(semantic_content),
        "content_ref": reference.to_dict(),
    }
    candidate = CandidateEffect(
        candidate_effect_id=content_id("candidate-effect", identity),
        tick=cause.tick,
        parent_cause_id=cause.cause_id,
        producer_cjt_id=bias.cjt_id,
        operation_id=contract.operation_id,
        operation_contract_id=contract.contract_id,
        operation_contract_digest=contract.contract_digest,
        bias_id=bias.bias_id,
        bias_version=bias.version,
        bias_digest=bias.state_digest,
        model_digest=bias.theta.model_digest,
        content=semantic_content,
        content_ref=reference,
        uncertainty_ppm=uncertainty_ppm,
        provenance=(
            f"cause:{cause.cause_id}",
            f"bias:{bias.state_digest}",
            f"model:{bias.theta.model_digest}",
            *(() if decoder_digest is None else (f"decoder:{decoder_digest}",)),
            *(
                ()
                if control_binding_digest is None
                else (f"control-binding:{control_binding_digest}",)
            ),
        ),
        candidate_digest=ZERO_DIGEST,
    )
    candidate = replace(
        candidate,
        candidate_digest=canonical_digest(
            candidate.to_dict(), omit_keys=("candidate_digest",)
        ),
    )
    return candidate, artifact


def make_state_update_intent(
    *,
    bias: BiasState,
    tick: int,
    receipt: VerifierReceipt,
    target_path: str,
    replacement: Mapping[str, Any],
    issuer_id: str,
    reason_codes: Sequence[str],
) -> StateUpdateIntent:
    """Bind one proposed Bias path replacement to one verifier receipt."""

    identity = {
        "tick": tick,
        "bias_digest": bias.state_digest,
        "receipt_id": receipt.receipt_id,
        "target_path": target_path,
        "replacement": dict(replacement),
        "issuer_id": issuer_id,
    }
    intent = StateUpdateIntent(
        intent_id=content_id("intent-state", identity),
        tick=tick,
        issuer_id=issuer_id,
        authority_capability=AuthorityCapability.PROPOSE_STATE_UPDATE.value,
        target_bias_id=bias.bias_id,
        expected_bias_version=bias.version,
        expected_bias_digest=bias.state_digest,
        target_path=target_path,
        replacement=replacement,
        verifier_receipt_id=receipt.receipt_id,
        reason_codes=tuple(reason_codes),
        intent_digest=ZERO_DIGEST,
    )
    return replace(
        intent,
        intent_digest=canonical_digest(intent.to_dict(), omit_keys=("intent_digest",)),
    )


def state_update_intents_for_successor(
    before: BiasState,
    after: BiasState,
    *,
    tick: int,
    receipt: VerifierReceipt,
    issuer_id: str,
) -> tuple[StateUpdateIntent, ...]:
    """Describe exactly the mutable root paths changed in a successor Bias."""

    if (
        after.bias_id != before.bias_id
        or after.cjt_id != before.cjt_id
        or after.version != before.version + 1
        or after.previous_digest != before.state_digest
    ):
        raise ProposalError("Bias successor does not bind its predecessor")
    before_wire = before.to_dict()
    after_wire = after.to_dict()
    if before_wire["stable"] != after_wire["stable"]:
        raise ProposalError("stable Bias substrate cannot be proposed as mutable")
    if before_wire["governance"] != after_wire["governance"]:
        raise ProposalError("neural code cannot propose its own governance change")
    intents: list[StateUpdateIntent] = []
    for root in ("memory", "rpm", "operating", "theta"):
        if before_wire[root] == after_wire[root]:
            continue
        intents.append(
            make_state_update_intent(
                bias=before,
                tick=tick,
                receipt=receipt,
                target_path=f"/{root}",
                replacement=after_wire[root],
                issuer_id=issuer_id,
                reason_codes=(f"PROPOSE_{root.upper()}_SUCCESSOR",),
            )
        )
    if not intents:
        raise ProposalError("successor Bias contains no proposed mutable change")
    return tuple(intents)


def phase_records(
    *,
    tick: int,
    phase_payloads: Mapping[TickPhase | str, Mapping[str, Any]],
) -> tuple[PhaseRecord, ...]:
    """Freeze exactly one record for every mandatory phase in exact order."""

    result: list[PhaseRecord] = []
    for phase in TickPhase:
        raw = phase_payloads.get(phase, phase_payloads.get(phase.value, {}))
        inputs = raw.get("inputs", {})
        outputs = raw.get("outputs", {})
        diagnostics = raw.get("diagnostics", {})
        compute_units = raw.get("compute_units", 0)
        if not isinstance(inputs, Mapping) or not isinstance(outputs, Mapping) or not isinstance(
            diagnostics, Mapping
        ):
            raise ProposalError(f"{phase.value} phase sections must be mappings")
        result.append(
            PhaseRecord(
                phase=phase,
                tick=tick,
                inputs=inputs,
                outputs=outputs,
                diagnostics=diagnostics,
                compute_units=compute_units,
            )
        )
    return tuple(result)


__all__ = [
    "ProposalError",
    "freeze_candidate_effect",
    "make_state_update_intent",
    "phase_records",
    "state_update_intents_for_successor",
]
