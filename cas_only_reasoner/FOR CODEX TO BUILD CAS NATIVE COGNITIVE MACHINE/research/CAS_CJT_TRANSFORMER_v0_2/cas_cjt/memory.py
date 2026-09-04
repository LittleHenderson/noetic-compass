"""Proposal-only memory interface for Neural CJT Bias."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Protocol, Sequence

from .contracts import canonical_digest
from .state import ZERO_DIGEST, content_id
from .types import (
    AuthorityCapability,
    BiasState,
    CandidateEffect,
    CausePacket,
    MemoryKind,
    MemoryWriteIntent,
    TensorArtifactRef,
    VerifierDisposition,
    VerifierReceipt,
)


class MemoryError(ValueError):
    """A memory proposal or retrieval violated the local contract."""


class _DocumentStore(Protocol):
    def immutable_document(self, table: str, record_id: str) -> dict[str, Any]: ...


def propose_memory_write(
    *,
    tick: int,
    issuer_id: str,
    bias: BiasState,
    receipt: VerifierReceipt,
    cause: CausePacket,
    candidate: CandidateEffect,
) -> MemoryWriteIntent:
    """Create the one receipt-bound episodic projection admitted by v0.2."""

    if receipt.disposition is not VerifierDisposition.ACCEPT:
        raise MemoryError("memory writes require an accepted verifier receipt")
    if receipt.bias_id != bias.bias_id or receipt.bias_digest != bias.state_digest:
        raise MemoryError("memory receipt does not bind the active Bias")
    if (
        tick != cause.tick
        or tick != candidate.tick
        or tick != receipt.tick
        or issuer_id != candidate.producer_cjt_id
        or candidate.parent_cause_id != cause.cause_id
        or candidate.bias_id != bias.bias_id
        or candidate.bias_version != bias.version
        or candidate.bias_digest != bias.state_digest
        or receipt.cause_id != cause.cause_id
        or receipt.candidate_effect_id != candidate.candidate_effect_id
        or receipt.candidate_effect_digest != candidate.candidate_digest
        or not receipt.evidence_refs
    ):
        raise MemoryError("memory write inputs do not bind one accepted transition")
    authority = AuthorityCapability.PROPOSE_MEMORY_WRITE.value
    content = {
        "cause_id": cause.cause_id,
        "candidate_effect_id": candidate.candidate_effect_id,
        "semantic_content": dict(candidate.content),
    }
    content_ref = candidate.content_ref
    memory_kind = MemoryKind.EPISODIC
    confidence_ppm = 1_000_000
    provenance = (f"bias:{bias.state_digest}", f"verifier:{receipt.receipt_id}")
    evidence_refs = tuple(receipt.evidence_refs)
    identity = {
        "tick": tick,
        "issuer_id": issuer_id,
        "target_bias_id": bias.bias_id,
        "expected_bias_version": bias.version,
        "expected_bias_digest": bias.state_digest,
        "verifier_receipt_id": receipt.receipt_id,
        "memory_kind": memory_kind.value,
        "content": dict(content),
        "content_ref": None if content_ref is None else content_ref.to_dict(),
        "confidence_ppm": confidence_ppm,
        "provenance": list(provenance),
        "evidence_refs": list(evidence_refs),
    }
    record_id = content_id("memory", identity)
    intent = MemoryWriteIntent(
        intent_id=content_id("intent-memory", identity),
        tick=tick,
        issuer_id=issuer_id,
        authority_capability=authority,
        target_bias_id=bias.bias_id,
        expected_bias_version=bias.version,
        expected_bias_digest=bias.state_digest,
        memory_record_id=record_id,
        memory_kind=memory_kind,
        content=content,
        content_ref=content_ref,
        confidence_ppm=confidence_ppm,
        provenance=provenance,
        evidence_refs=evidence_refs,
        verifier_receipt_id=receipt.receipt_id,
        intent_digest=ZERO_DIGEST,
    )
    return replace(
        intent,
        intent_digest=canonical_digest(intent.to_dict(), omit_keys=("intent_digest",)),
    )


def memory_document(intent: MemoryWriteIntent, *, committed_by: str) -> dict[str, Any]:
    """Freeze the immutable record installed by an authorized coordinator."""

    body = {
        "schema_version": "cas.neural-cjt.memory-record/0.2",
        "memory_record_id": intent.memory_record_id,
        "memory_kind": intent.memory_kind.value,
        "content": dict(intent.content),
        "content_ref": None if intent.content_ref is None else intent.content_ref.to_dict(),
        "confidence_ppm": intent.confidence_ppm,
        "provenance": list(intent.provenance),
        "evidence_refs": list(intent.evidence_refs),
        "source_intent_id": intent.intent_id,
        "verifier_receipt_id": intent.verifier_receipt_id,
        "committed_by": committed_by,
    }
    return {**body, "record_digest": canonical_digest(body)}


def retrieve_memory(
    store: _DocumentStore,
    memory_record_ids: Sequence[str],
    *,
    permitted_ids: Sequence[str],
    max_reads: int,
) -> tuple[dict[str, Any], ...]:
    """Return deterministic candidate memory contributions under a hard ceiling."""

    if not isinstance(max_reads, int) or isinstance(max_reads, bool) or max_reads < 0:
        raise MemoryError("max_reads must be a nonnegative integer")
    allowed = set(permitted_ids)
    selected = [record_id for record_id in sorted(set(memory_record_ids)) if record_id in allowed]
    result: list[dict[str, Any]] = []
    for record_id in selected[:max_reads]:
        try:
            record = store.immutable_document("memory_records", record_id)
        except (LookupError, RuntimeError) as error:
            raise MemoryError(f"memory record {record_id} was not found") from error
        retained = record.get("record_digest")
        if not isinstance(retained, str) or retained != canonical_digest(
            record, omit_keys=("record_digest",)
        ):
            raise MemoryError(f"memory record {record_id} failed digest verification")
        result.append(
            {
                "memory_record_id": record_id,
                "memory_kind": record["memory_kind"],
                "content": record["content"],
                "content_ref": record["content_ref"],
                "confidence_ppm": record["confidence_ppm"],
                "provenance": record["provenance"],
                "candidate_only": True,
            }
        )
    return tuple(result)


__all__ = [
    "MemoryError",
    "memory_document",
    "propose_memory_write",
    "retrieve_memory",
]
