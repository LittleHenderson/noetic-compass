"""Deterministic semantic decoding and independently bound oracle evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor

from .artifacts import StoredArtifact, canonical_json as artifact_canonical_json, decode_tensor
from .contracts import canonical_digest, canonical_json
from .types import CandidateEffect, CausePacket, OperationContract
from .verifier import SemanticEvidence


class SemanticDecodeError(ValueError):
    """A neural Effect or semantic evidence binding was malformed."""


@dataclass(frozen=True, slots=True)
class DecoderContract:
    decoder_id: str
    version: int
    operation_id: str
    effect_kind: str
    labels: tuple[str, ...]
    algorithm: str = "MEAN_LOGIT_ARGMAX_LOWEST_INDEX"
    zero_symbol: str = "NO_EFFECT"

    def __post_init__(self) -> None:
        if not self.decoder_id or self.version < 1 or not self.operation_id or not self.effect_kind:
            raise SemanticDecodeError("decoder identity/version is invalid")
        if not self.labels or len(set(self.labels)) != len(self.labels):
            raise SemanticDecodeError("decoder labels must be nonempty and unique")
        if any(not isinstance(item, str) or not item for item in self.labels):
            raise SemanticDecodeError("decoder labels must be nonempty strings")
        if not self.algorithm or not self.zero_symbol:
            raise SemanticDecodeError("decoder algorithm and zero symbol are required")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": "cas.neural-cjt.decoder-contract/0.2",
            "decoder_id": self.decoder_id,
            "version": self.version,
            "operation_id": self.operation_id,
            "effect_kind": self.effect_kind,
            "labels": list(self.labels),
            "algorithm": self.algorithm,
            "zero_symbol": self.zero_symbol,
        }
        return {**body, "decoder_digest": canonical_digest(body)}

    @property
    def decoder_digest(self) -> str:
        return str(self.to_dict()["decoder_digest"])


class DeterministicSemanticDecoder:
    """Map a neural Effect tensor to one typed symbol without caller content."""

    def __init__(self, contract: DecoderContract) -> None:
        self.contract = contract

    def decode(self, effect: Tensor) -> dict[str, str]:
        if not isinstance(effect, Tensor) or not effect.is_floating_point() or effect.ndim < 1:
            raise SemanticDecodeError("effect must be a floating-point Tensor")
        if not bool(torch.isfinite(effect).all().item()):
            raise SemanticDecodeError("effect must be finite")
        if effect.shape[-1] != len(self.contract.labels):
            raise SemanticDecodeError("effect width does not match decoder labels")
        detached = effect.detach().to(device="cpu")
        if bool((detached == 0).all().item()):
            symbol = self.contract.zero_symbol
        else:
            reduce_dims = tuple(range(detached.ndim - 1))
            logits = detached.mean(dim=reduce_dims) if reduce_dims else detached
            index = int(torch.argmax(logits).item())
            symbol = self.contract.labels[index]
        # The semantic payload stays small enough for an oracle to author
        # before execution.  Candidate.content_ref and decoder validation bind
        # this symbol to the exact tensor bytes.
        return {
            "operation_id": self.contract.operation_id,
            "effect_kind": self.contract.effect_kind,
            "symbol": symbol,
        }

    def decode_artifact(self, candidate: CandidateEffect, artifact: StoredArtifact) -> dict[str, str]:
        if candidate.content_ref is None:
            raise SemanticDecodeError("candidate Effect has no tensor artifact reference")
        tensor = decode_tensor(candidate.content_ref, artifact)
        return self.decode(tensor)

    def validate_candidate(self, candidate: CandidateEffect, artifact: StoredArtifact) -> bool:
        """Recompute semantic content from the exact referenced tensor bytes."""

        try:
            if candidate.content_ref is None:
                return False
            if (
                candidate.content_ref.artifact_id != artifact.artifact_id
                or candidate.content_ref.sha256 != artifact.sha256
            ):
                return False
            return canonical_json(candidate.content) == canonical_json(
                self.decode_artifact(candidate, artifact)
            ) and f"decoder:{self.contract.decoder_digest}" in candidate.provenance
        except (SemanticDecodeError, TypeError, ValueError):
            return False


def validate_operation_io(
    cause: CausePacket,
    candidate: CandidateEffect,
    contract: OperationContract,
) -> bool:
    """Enforce the registered Cause kind and operation-specific Effect shape."""

    try:
        content = dict(candidate.content)
        expected_kind = contract.effect_schema_id.rsplit(":", 1)[-1]
        return (
            cause.cause_kind in contract.accepted_cause_kinds
            and candidate.operation_id == contract.operation_id
            and set(content) == {"operation_id", "effect_kind", "symbol"}
            and content["operation_id"] == contract.operation_id
            and content["effect_kind"] == expected_kind
            and isinstance(content["symbol"], str)
            and bool(content["symbol"])
        )
    except (TypeError, ValueError):
        return False


def make_bound_evidence(
    *,
    evidence_id: str,
    source_id: str,
    port_id: str,
    operation_id: str,
    effect_kind: str,
    expected_symbol: str | None,
    opposite_symbol: str | None = None,
    provenance: Sequence[str] = (),
) -> tuple[SemanticEvidence, dict[str, Any]]:
    """Create an oracle record whose full content is replayable from trace."""

    expected = (
        None
        if expected_symbol is None
        else {
            "operation_id": operation_id,
            "effect_kind": effect_kind,
            "symbol": expected_symbol,
        }
    )
    opposite = (
        None
        if opposite_symbol is None
        else {
            "operation_id": operation_id,
            "effect_kind": effect_kind,
            "symbol": opposite_symbol,
        }
    )
    body = {
        "schema_version": "cas.neural-cjt.semantic-evidence/0.2",
        "evidence_id": evidence_id,
        "source_id": source_id,
        "port_id": port_id,
        "expected_content": expected,
        "opposite_content": opposite,
        "provenance": list(provenance),
    }
    digest = canonical_digest(body)
    bound_provenance = tuple(provenance) + (f"evidence-digest:{digest}",)
    descriptor = {**body, "provenance": list(bound_provenance), "evidence_digest": digest}
    evidence = SemanticEvidence(
        evidence_id=evidence_id,
        source_id=source_id,
        port_id=port_id,
        expected_content=expected,
        opposite_content=opposite,
        provenance=bound_provenance,
    )
    return evidence, descriptor


def verify_evidence_descriptor(descriptor: Mapping[str, Any]) -> bool:
    """Verify an oracle descriptor and its receipt-visible digest marker."""

    try:
        retained = descriptor["evidence_digest"]
        provenance = list(descriptor["provenance"])
        marker = f"evidence-digest:{retained}"
        if marker not in provenance:
            return False
        original_provenance = [item for item in provenance if item != marker]
        body = {
            "schema_version": descriptor["schema_version"],
            "evidence_id": descriptor["evidence_id"],
            "source_id": descriptor["source_id"],
            "port_id": descriptor["port_id"],
            "expected_content": descriptor["expected_content"],
            "opposite_content": descriptor["opposite_content"],
            "provenance": original_provenance,
        }
        return isinstance(retained, str) and retained == canonical_digest(body)
    except (KeyError, TypeError, ValueError):
        return False


__all__ = [
    "DecoderContract",
    "DeterministicSemanticDecoder",
    "SemanticDecodeError",
    "make_bound_evidence",
    "validate_operation_io",
    "verify_evidence_descriptor",
]
