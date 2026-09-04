"""Proposal-only boundary between Neural CJT v0.2 and a future CNCM revision.

This module deliberately does not import the current :mod:`cncm` package.  It
can only turn an already committed, store-backed ``PublishedEffect`` into an
inert candidate envelope.  The envelope grants no current CNCM authority and
has no method for state mutation, proof creation, commitment, action, or halt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from .contracts import canonical_digest, canonical_json, verify_declared_digest
from .types import PublishedEffect


BRIDGE_SCHEMA_VERSION = "cas.neural-cjt.cncm-candidate-envelope/0.2"
BRIDGE_ADAPTER_ID = "cas.neural-cjt.proposal-only-cncm-boundary/0.2"
AUTHORITY_STATUS = "INERT_PROPOSAL_ONLY_NOT_ADMITTED_BY_CURRENT_CNCM"
FUTURE_REVISION_STATUS = "REQUIRED_BUT_UNASSIGNED"

PERMITTED_USES = (
    "DISPLAY_AS_NONAUTHORITATIVE_CANDIDATE",
    "REVIEW_BY_A_FUTURE_EXPLICIT_AUTHORITY_REVISION",
)

PROHIBITED_AUTHORITIES = (
    "CURRENT_CNCM_STATE_WRITE",
    "CURRENT_CNCM_PROOF_CREATION",
    "CURRENT_CNCM_INTENT_CREATION",
    "CURRENT_CNCM_COMMITMENT",
    "CURRENT_CNCM_MEMORY_WRITE",
    "CURRENT_CNCM_EXTERNAL_ACTION",
    "CURRENT_CNCM_HALT",
)


class CNCMBridgeError(ValueError):
    """A value failed the proposal-only boundary contract."""


class CommittedEffectEvidenceStore(Protocol):
    """Read-only evidence surface required by the bridge."""

    def immutable_document(self, table: str, record_id: str) -> dict[str, Any]: ...

    def receipt_by_id(self, receipt_id: str) -> dict[str, Any]: ...


def _nonempty(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CNCMBridgeError(f"{name} must be a nonempty trimmed string")
    return value


def _freeze_json(value: Any, *, path: str) -> Any:
    """Deep-freeze one no-float JSON value."""

    if isinstance(value, float):
        raise CNCMBridgeError(f"{path} contains a float")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str) or not key:
                raise CNCMBridgeError(f"{path} contains an invalid object key")
            result[key] = _freeze_json(value[key], path=f"{path}.{key}")
        return MappingProxyType(result)
    if isinstance(value, (tuple, list)):
        return tuple(
            _freeze_json(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise CNCMBridgeError(f"{path} contains unsupported type {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in sorted(value.items())}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _document(
    store: CommittedEffectEvidenceStore,
    table: str,
    record_id: str,
) -> dict[str, Any]:
    reader = getattr(store, "immutable_document", None)
    if not callable(reader):
        raise CNCMBridgeError("store lacks the required read-only document interface")
    try:
        value = reader(table, record_id)
    except Exception as exc:  # fail closed across persistence implementations
        raise CNCMBridgeError(f"{table} evidence is absent or unreadable") from exc
    if not isinstance(value, Mapping):
        raise CNCMBridgeError(f"{table} evidence is not an object")
    return dict(value)


def _commit_receipt(
    store: CommittedEffectEvidenceStore,
    receipt_id: str,
) -> dict[str, Any]:
    reader = getattr(store, "receipt_by_id", None)
    if not callable(reader):
        raise CNCMBridgeError("store lacks the required read-only receipt interface")
    try:
        value = reader(receipt_id)
    except Exception as exc:  # fail closed across persistence implementations
        raise CNCMBridgeError("commit receipt evidence is absent or unreadable") from exc
    if not isinstance(value, Mapping):
        raise CNCMBridgeError("commit receipt evidence is not an object")
    return dict(value)


def _require_contract(
    value: Mapping[str, Any],
    *,
    contract_type: str,
    schema_version: str,
    digest_field: str,
    label: str,
) -> None:
    if value.get("contract_type") != contract_type:
        raise CNCMBridgeError(f"{label} has the wrong contract type")
    if value.get("schema_version") != schema_version:
        raise CNCMBridgeError(f"{label} has the wrong schema version")
    if not verify_declared_digest(value, digest_field):
        raise CNCMBridgeError(f"{label} digest is invalid")


@dataclass(frozen=True, slots=True, kw_only=True)
class InertCNCMCandidateEnvelope:
    """A future-facing candidate with explicit zero current CNCM authority."""

    envelope_id: str
    adapter_id: str
    source_published_effect_id: str
    source_publication_digest: str
    source_candidate_effect_id: str
    source_candidate_digest: str
    source_verifier_receipt_id: str
    source_verifier_receipt_digest: str
    source_commit_receipt_id: str
    source_commit_receipt_digest: str
    producer_cjt_id: str
    source_tick: int
    operation_id: str
    operation_contract_id: str
    operation_contract_digest: str
    source_bias_digest: str
    source_model_digest: str
    candidate_payload: Mapping[str, Any]
    candidate_payload_ref: Mapping[str, Any] | None
    source_provenance: tuple[str, ...]
    envelope_digest: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "envelope_id",
            "adapter_id",
            "source_published_effect_id",
            "source_publication_digest",
            "source_candidate_effect_id",
            "source_candidate_digest",
            "source_verifier_receipt_id",
            "source_verifier_receipt_digest",
            "source_commit_receipt_id",
            "source_commit_receipt_digest",
            "producer_cjt_id",
            "operation_id",
            "operation_contract_id",
            "operation_contract_digest",
            "source_bias_digest",
            "source_model_digest",
        ):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        if (
            not isinstance(self.source_tick, int)
            or isinstance(self.source_tick, bool)
            or self.source_tick < 0
        ):
            raise CNCMBridgeError("source_tick must be a nonnegative integer")
        object.__setattr__(
            self,
            "candidate_payload",
            _freeze_json(self.candidate_payload, path="candidate_payload"),
        )
        if self.candidate_payload_ref is not None:
            object.__setattr__(
                self,
                "candidate_payload_ref",
                _freeze_json(
                    self.candidate_payload_ref,
                    path="candidate_payload_ref",
                ),
            )
        provenance = tuple(self.source_provenance)
        if not provenance or any(not isinstance(item, str) or not item for item in provenance):
            raise CNCMBridgeError("source_provenance must contain nonempty strings")
        object.__setattr__(self, "source_provenance", provenance)
        object.__setattr__(self, "envelope_digest", canonical_digest(self._body()))

    def _body(self) -> dict[str, Any]:
        return {
            "contract_type": "FUTURE_CNCM_CANDIDATE_ENVELOPE",
            "schema_version": BRIDGE_SCHEMA_VERSION,
            "envelope_id": self.envelope_id,
            "adapter_id": self.adapter_id,
            "authority_status": AUTHORITY_STATUS,
            "authoritative": False,
            "current_cncm_admitted": False,
            "future_authority_revision": FUTURE_REVISION_STATUS,
            "permitted_uses": list(PERMITTED_USES),
            "prohibited_authorities": list(PROHIBITED_AUTHORITIES),
            "source_published_effect_id": self.source_published_effect_id,
            "source_publication_digest": self.source_publication_digest,
            "source_candidate_effect_id": self.source_candidate_effect_id,
            "source_candidate_digest": self.source_candidate_digest,
            "source_verifier_receipt_id": self.source_verifier_receipt_id,
            "source_verifier_receipt_digest": self.source_verifier_receipt_digest,
            "source_commit_receipt_id": self.source_commit_receipt_id,
            "source_commit_receipt_digest": self.source_commit_receipt_digest,
            "producer_cjt_id": self.producer_cjt_id,
            "source_tick": self.source_tick,
            "operation_id": self.operation_id,
            "operation_contract_id": self.operation_contract_id,
            "operation_contract_digest": self.operation_contract_digest,
            "source_bias_digest": self.source_bias_digest,
            "source_model_digest": self.source_model_digest,
            "candidate_payload": _thaw_json(self.candidate_payload),
            "candidate_payload_ref": (
                None
                if self.candidate_payload_ref is None
                else _thaw_json(self.candidate_payload_ref)
            ),
            "source_provenance": list(self.source_provenance),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "envelope_digest": self.envelope_digest}


class ProposalOnlyCNCMBridge:
    """Validate a complete evidence chain and emit only an inert envelope."""

    def __init__(self, adapter_id: str = BRIDGE_ADAPTER_ID) -> None:
        self.adapter_id = _nonempty("adapter_id", adapter_id)

    def translate_optional(
        self,
        published_effect: PublishedEffect | None,
        *,
        store: CommittedEffectEvidenceStore | None = None,
    ) -> InertCNCMCandidateEnvelope | None:
        """Return no proposal when the neural core is absent."""

        if published_effect is None:
            return None
        if store is None:
            raise CNCMBridgeError("a retained evidence store is required")
        return self.translate(published_effect, store=store)

    def translate(
        self,
        published_effect: PublishedEffect,
        *,
        store: CommittedEffectEvidenceStore,
    ) -> InertCNCMCandidateEnvelope:
        """Translate one retained publication without granting CNCM authority."""

        if not isinstance(published_effect, PublishedEffect):
            raise CNCMBridgeError("only a typed PublishedEffect can cross this boundary")
        effect_wire = published_effect.to_dict()
        if published_effect.authoritative is not True or not verify_declared_digest(
            published_effect,
            "publication_digest",
        ):
            raise CNCMBridgeError("PublishedEffect is unsealed or forged")

        retained_effect = _document(
            store,
            "published_effects",
            published_effect.published_effect_id,
        )
        _require_contract(
            retained_effect,
            contract_type=PublishedEffect.CONTRACT_TYPE,
            schema_version=PublishedEffect.SCHEMA_VERSION,
            digest_field="publication_digest",
            label="retained PublishedEffect",
        )
        if canonical_json(retained_effect) != canonical_json(effect_wire):
            raise CNCMBridgeError("PublishedEffect does not match the retained publication")

        candidate = _document(
            store,
            "candidate_effects",
            published_effect.candidate_effect_id,
        )
        _require_contract(
            candidate,
            contract_type="CANDIDATE_EFFECT",
            schema_version="cas.neural-cjt.candidate-effect/0.2",
            digest_field="candidate_digest",
            label="candidate Effect",
        )
        verifier = _document(
            store,
            "verifier_receipts",
            published_effect.verifier_receipt_id,
        )
        _require_contract(
            verifier,
            contract_type="VERIFIER_RECEIPT",
            schema_version="cas.neural-cjt.verifier-receipt/0.2",
            digest_field="receipt_digest",
            label="verifier receipt",
        )
        commit = _commit_receipt(store, published_effect.commit_receipt_id)
        _require_contract(
            commit,
            contract_type="COMMIT_RECEIPT",
            schema_version="cas.neural-cjt.commit-receipt/0.2",
            digest_field="receipt_digest",
            label="commit receipt",
        )

        candidate_expected = {
            "candidate_effect_id": published_effect.candidate_effect_id,
            "producer_cjt_id": published_effect.producer_cjt_id,
            "tick": published_effect.tick,
            "authoritative": False,
        }
        if any(candidate.get(key) != value for key, value in candidate_expected.items()):
            raise CNCMBridgeError("candidate Effect does not bind the publication")
        if canonical_json(candidate.get("content")) != canonical_json(published_effect.content):
            raise CNCMBridgeError("candidate and published semantic content differ")
        published_ref = (
            None
            if published_effect.content_ref is None
            else published_effect.content_ref.to_dict()
        )
        if canonical_json(candidate.get("content_ref")) != canonical_json(published_ref):
            raise CNCMBridgeError("candidate and published tensor references differ")

        verifier_expected = {
            "receipt_id": published_effect.verifier_receipt_id,
            "candidate_effect_id": published_effect.candidate_effect_id,
            "candidate_effect_digest": candidate.get("candidate_digest"),
            "bias_id": candidate.get("bias_id"),
            "bias_version": candidate.get("bias_version"),
            "bias_digest": candidate.get("bias_digest"),
            "operation_contract_id": candidate.get("operation_contract_id"),
            "operation_contract_digest": candidate.get("operation_contract_digest"),
            "model_digest": candidate.get("model_digest"),
            "semantic_outcome": "INTENDED",
            "disposition": "ACCEPT",
            "independent": True,
            "repair_required": False,
        }
        if any(verifier.get(key) != value for key, value in verifier_expected.items()):
            raise CNCMBridgeError("verifier receipt does not authorize this publication")

        if (
            commit.get("receipt_id") != published_effect.commit_receipt_id
            or commit.get("authorized") is not True
            or commit.get("disposition") != "COMMITTED"
            or list(commit.get("published_effect_ids", [])).count(
                published_effect.published_effect_id
            )
            != 1
        ):
            raise CNCMBridgeError("commit receipt does not publish this Effect")

        identity = {
            "adapter_id": self.adapter_id,
            "publication_digest": published_effect.publication_digest,
            "candidate_digest": candidate["candidate_digest"],
            "verifier_receipt_digest": verifier["receipt_digest"],
            "commit_receipt_digest": commit["receipt_digest"],
        }
        envelope_id = f"future-cncm-candidate-{canonical_digest(identity)[:24]}"
        envelope = InertCNCMCandidateEnvelope(
            envelope_id=envelope_id,
            adapter_id=self.adapter_id,
            source_published_effect_id=published_effect.published_effect_id,
            source_publication_digest=published_effect.publication_digest,
            source_candidate_effect_id=published_effect.candidate_effect_id,
            source_candidate_digest=str(candidate["candidate_digest"]),
            source_verifier_receipt_id=published_effect.verifier_receipt_id,
            source_verifier_receipt_digest=str(verifier["receipt_digest"]),
            source_commit_receipt_id=published_effect.commit_receipt_id,
            source_commit_receipt_digest=str(commit["receipt_digest"]),
            producer_cjt_id=published_effect.producer_cjt_id,
            source_tick=published_effect.tick,
            operation_id=str(candidate["operation_id"]),
            operation_contract_id=str(candidate["operation_contract_id"]),
            operation_contract_digest=str(candidate["operation_contract_digest"]),
            source_bias_digest=str(candidate["bias_digest"]),
            source_model_digest=str(candidate["model_digest"]),
            candidate_payload=published_effect.content,
            candidate_payload_ref=published_ref,
            source_provenance=published_effect.provenance,
        )
        # Canonical round-trip is a final no-float and digest sanity check.
        json.loads(canonical_json(envelope.to_dict()))
        if envelope.envelope_digest != canonical_digest(
            envelope.to_dict(), omit_keys=("envelope_digest",)
        ):
            raise CNCMBridgeError("new inert envelope failed its digest check")
        return envelope


__all__ = [
    "AUTHORITY_STATUS",
    "BRIDGE_ADAPTER_ID",
    "BRIDGE_SCHEMA_VERSION",
    "FUTURE_REVISION_STATUS",
    "PERMITTED_USES",
    "PROHIBITED_AUTHORITIES",
    "CNCMBridgeError",
    "CommittedEffectEvidenceStore",
    "InertCNCMCandidateEnvelope",
    "ProposalOnlyCNCMBridge",
]
