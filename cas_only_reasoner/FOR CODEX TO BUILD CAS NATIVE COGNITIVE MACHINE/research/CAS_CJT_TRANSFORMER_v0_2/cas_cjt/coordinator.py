"""Trusted single-Bias compatibility harness for atomic persistence tests.

``AtomicCoordinator`` preserves the prototype's legacy effect, memory-record,
rollback, and all-or-nothing persistence exercises.  It does not retain enough
network context to authorize semantic state, model, or repair transitions, so
those proposal classes fail closed.  ``NetworkAtomicCoordinator`` is the sole
supported v0.2 semantic writer.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields as dataclass_fields
import hmac
from typing import Any, Iterable, Mapping, Sequence

from .artifacts import StoredArtifact
from .contracts import (
    assert_no_json_floats,
    canonical_digest,
    canonical_json,
    verify_declared_digest,
)
from .persistence import (
    ActiveHead,
    AtomicWriteSet,
    IdempotencyConflict,
    ModelVersionWrite,
    PersistenceError,
    SQLiteAtomicStore,
    StaleHeadError,
    StoredDocument,
)
from .state import make_cause
from .trace import MANDATORY_PHASES, SealedTrace, seal_trace, verify_trace_chain
from .types import (
    BiasState,
    CauseKind,
    CommitDisposition,
    CommitReceipt,
    PhaseRecord,
    PublishedEffect,
    TensorArtifactRef,
    TickPhase,
    TickTrace,
)


PROPOSE_STATE_UPDATE = "PROPOSE_STATE_UPDATE"
PROPOSE_MODEL_UPDATE = "PROPOSE_MODEL_UPDATE"
PROPOSE_MEMORY_WRITE = "PROPOSE_MEMORY_WRITE"
REQUEST_EFFECT_PUBLICATION = "REQUEST_EFFECT_PUBLICATION"


class CoordinatorError(RuntimeError):
    """A proposed batch cannot cross the authority boundary."""


class BatchRejected(CoordinatorError):
    """A complete batch was rejected without changing durable state."""

    def __init__(self, *reason_codes: str) -> None:
        normalized = tuple(dict.fromkeys(code for code in reason_codes if code))
        self.reason_codes = normalized or ("BATCH_REJECTED",)
        super().__init__("; ".join(self.reason_codes))


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitBatch:
    """One all-or-nothing transition proposed by the runtime."""

    batch_id: str
    tick: int
    base_snapshot_hash: str
    base_trace_digest: str | None
    cause: Any
    bias_before: Any
    bias_after: Any
    candidate_effects: tuple[Any, ...]
    verifier_receipts: tuple[Any, ...]
    state_intents: tuple[Any, ...]
    model_intents: tuple[Any, ...]
    memory_intents: tuple[Any, ...]
    repair_frames: tuple[Any, ...]
    phase_records: tuple[PhaseRecord, ...]
    runtime_id: str
    software_digest: str
    cjt_ids: tuple[str, ...]
    artifacts: tuple[StoredArtifact, ...] = ()
    model_version: ModelVersionWrite | None = None
    qualification_receipts: tuple[Any, ...] = ()
    memory_read_refs: tuple[str, ...] = ()
    compute_plan: Mapping[str, Any] = field(default_factory=dict)
    compute_observations: Mapping[str, Any] = field(default_factory=dict)
    sensitive_trace_fields: tuple[str, ...] = ()
    effect_publication_capability: str = REQUEST_EFFECT_PUBLICATION


@dataclass(frozen=True, slots=True, kw_only=True)
class RollbackRequest:
    """Request a new compensating commit that restores one receipt's pre-state."""

    batch_id: str
    tick: int
    rollback_of_receipt_id: str
    issuer_id: str
    authority_capability: str
    cause_id: str
    runtime_id: str
    software_digest: str
    cjt_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecoverySnapshot:
    head: ActiveHead
    state: dict[str, Any]
    traces: tuple[dict[str, Any], ...]


def _wire(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        result = dict(value)
    else:
        to_dict = getattr(value, "to_dict", None)
        if not callable(to_dict):
            raise BatchRejected(f"{label.upper()}_NOT_A_CONTRACT")
        result = to_dict()
        if not isinstance(result, Mapping):
            raise BatchRejected(f"{label.upper()}_NOT_A_CONTRACT")
        result = dict(result)
    try:
        assert_no_json_floats(result)
    except (TypeError, ValueError) as exc:
        raise BatchRejected(f"{label.upper()}_NOT_AUTHORITATIVE_JSON") from exc
    return result


def _text(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _require_digest(value: Mapping[str, Any], field_name: str, label: str) -> None:
    if not verify_declared_digest(value, field_name):
        raise BatchRejected(f"{label.upper()}_DIGEST_INVALID")


def _unique_by(
    values: Sequence[Any],
    field_name: str,
    *,
    label: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        mapped = _wire(value, label=label)
        identity = mapped.get(field_name)
        if not isinstance(identity, str) or not identity or identity in result:
            raise BatchRejected(f"{label.upper()}_IDENTITY_INVALID")
        result[identity] = mapped
    return result


def _json_clone(value: Mapping[str, Any]) -> dict[str, Any]:
    # canonical_json also makes this a no-float, detached JSON tree.
    import json

    return json.loads(canonical_json(value))


def _decode_pointer(path: str) -> tuple[str, ...]:
    if not isinstance(path, str) or not path.startswith("/"):
        raise BatchRejected("STATE_INTENT_PATH_INVALID")
    parts = path[1:].split("/")
    if not parts or any(part == "" for part in parts):
        raise BatchRejected("STATE_INTENT_PATH_INVALID")
    return tuple(part.replace("~1", "/").replace("~0", "~") for part in parts)


def _set_pointer(document: dict[str, Any], path: str, replacement: Any) -> None:
    parts = _decode_pointer(path)
    cursor: Any = document
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            raise BatchRejected("STATE_INTENT_PATH_MISSING")
        cursor = cursor[part]
    if not isinstance(cursor, dict) or parts[-1] not in cursor:
        raise BatchRejected("STATE_INTENT_PATH_MISSING")
    cursor[parts[-1]] = deepcopy(replacement)


def _artifact_references(value: Any) -> Iterable[tuple[str, str]]:
    if isinstance(value, Mapping):
        artifact_id = value.get("artifact_id")
        digest = value.get("sha256")
        if isinstance(artifact_id, str) and isinstance(digest, str):
            yield artifact_id, digest
        for item in value.values():
            yield from _artifact_references(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _artifact_references(item)


def _receipt_kwargs(payload: Mapping[str, Any]) -> dict[str, Any]:
    names = {item.name for item in dataclass_fields(CommitReceipt)}
    return {key: value for key, value in payload.items() if key in names}


class AtomicCoordinator:
    """Exercise trusted compatibility commits within a fail-closed scope."""

    def __init__(
        self,
        store: SQLiteAtomicStore,
        *,
        coordinator_id: str,
        authority_contract_id: str,
        operation_contract_digests: Mapping[str, str],
        trusted_runtime_id: str,
        trusted_software_digest: str,
        trusted_cjt_ids: Iterable[str],
        proposal_issuers: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        trusted_cjts = tuple(trusted_cjt_ids)
        if (
            not coordinator_id
            or not authority_contract_id
            or not trusted_runtime_id
            or not trusted_cjts
            or len(set(trusted_cjts)) != len(trusted_cjts)
        ):
            raise ValueError("coordinator and trusted identities must be nonempty")
        if (
            not isinstance(trusted_software_digest, str)
            or len(trusted_software_digest) != 64
            or any(character not in "0123456789abcdef" for character in trusted_software_digest)
        ):
            raise ValueError("trusted_software_digest must be lowercase SHA-256")
        self.store = store
        self.coordinator_id = coordinator_id
        self.authority_contract_id = authority_contract_id
        self.operation_contract_digests = dict(operation_contract_digests)
        self.trusted_runtime_id = trusted_runtime_id
        self.trusted_software_digest = trusted_software_digest
        self.trusted_cjt_ids = trusted_cjts
        self.proposal_issuers = {
            capability: frozenset(issuers)
            for capability, issuers in ({} if proposal_issuers is None else proposal_issuers).items()
        }

    def _request_payload(self, batch: CommitBatch) -> dict[str, Any]:
        artifacts = [artifact.public_descriptor() for artifact in batch.artifacts]
        model = None
        if batch.model_version is not None:
            model = {
                "model_digest": batch.model_version.model_digest,
                "parent_model_digest": batch.model_version.parent_model_digest,
                "artifact_id": batch.model_version.artifact_id,
                "payload": _wire(batch.model_version.payload, label="model version"),
            }
        return {
            "batch_id": batch.batch_id,
            "tick": batch.tick,
            "base_snapshot_hash": batch.base_snapshot_hash,
            "base_trace_digest": batch.base_trace_digest,
            "cause": _wire(batch.cause, label="cause"),
            "bias_before": _wire(batch.bias_before, label="bias before"),
            "bias_after": _wire(batch.bias_after, label="bias after"),
            "candidate_effects": [_wire(item, label="candidate effect") for item in batch.candidate_effects],
            "verifier_receipts": [_wire(item, label="verifier receipt") for item in batch.verifier_receipts],
            "state_intents": [_wire(item, label="state intent") for item in batch.state_intents],
            "model_intents": [_wire(item, label="model intent") for item in batch.model_intents],
            "memory_intents": [_wire(item, label="memory intent") for item in batch.memory_intents],
            "repair_frames": [_wire(item, label="repair frame") for item in batch.repair_frames],
            "phase_records": [_wire(item, label="phase record") for item in batch.phase_records],
            "runtime_id": batch.runtime_id,
            "software_digest": batch.software_digest,
            "cjt_ids": list(batch.cjt_ids),
            "artifacts": artifacts,
            "model_version": model,
            "qualification_receipts": [
                _wire(item, label="qualification receipt") for item in batch.qualification_receipts
            ],
            "memory_read_refs": list(batch.memory_read_refs),
            "compute_plan": batch.compute_plan,
            "compute_observations": batch.compute_observations,
            "sensitive_trace_fields": list(batch.sensitive_trace_fields),
            "effect_publication_capability": batch.effect_publication_capability,
        }
    def _request_digest(self, batch: CommitBatch) -> str:
        return canonical_digest(self._request_payload(batch))

    @staticmethod
    def _validate_compatibility_scope(batch: CommitBatch) -> None:
        """Reject proposal classes that need the network authority context."""

        if (
            batch.model_intents
            or batch.model_version is not None
            or batch.qualification_receipts
        ):
            raise BatchRejected("MODEL_UPDATE_REQUIRES_NETWORK_COORDINATOR")
        if batch.state_intents:
            raise BatchRejected("STATE_UPDATE_REQUIRES_NETWORK_COORDINATOR")
        if batch.repair_frames:
            raise BatchRejected("REPAIR_REQUIRES_NETWORK_COORDINATOR")

    def _issuer_authorized(
        self,
        *,
        capability: str,
        issuer_id: Any,
        batch: CommitBatch,
    ) -> bool:
        if not isinstance(issuer_id, str) or not issuer_id:
            return False
        configured = self.proposal_issuers.get(capability)
        if configured is not None:
            return issuer_id in configured
        if capability in {PROPOSE_STATE_UPDATE, PROPOSE_MEMORY_WRITE}:
            return issuer_id in batch.cjt_ids
        if capability == PROPOSE_MODEL_UPDATE:
            return issuer_id == "prototype-write-back-controller"
        return False

    def _idempotent_receipt(
        self, batch_id: str, request_digest: str
    ) -> CommitReceipt | None:
        retained = self.store.batch_record(batch_id)
        if retained is None:
            return None
        retained_digest, payload = retained
        if not hmac.compare_digest(retained_digest, request_digest):
            raise IdempotencyConflict("batch_id was already used for a different request")
        return CommitReceipt(**_receipt_kwargs(payload))

    def _validate_common(self, batch: CommitBatch) -> tuple[dict[str, Any], dict[str, Any], ActiveHead]:
        if not isinstance(batch.batch_id, str) or not batch.batch_id:
            raise BatchRejected("BATCH_ID_INVALID")
        if not isinstance(batch.tick, int) or isinstance(batch.tick, bool) or batch.tick < 1:
            raise BatchRejected("TICK_INVALID")
        if (
            batch.runtime_id != self.trusted_runtime_id
            or batch.software_digest != self.trusted_software_digest
            or batch.cjt_ids != self.trusted_cjt_ids
        ):
            raise BatchRejected("RUNTIME_IDENTITY_INVALID")
        before = _wire(batch.bias_before, label="bias before")
        after = _wire(batch.bias_after, label="bias after")
        _require_digest(before, "state_digest", "bias before")
        _require_digest(after, "state_digest", "bias after")
        head = self.store.head
        if (
            batch.base_snapshot_hash != before.get("state_digest")
            or head.state_digest != before.get("state_digest")
            or head.state_version != before.get("version")
            or head.trace_digest != batch.base_trace_digest
        ):
            raise StaleHeadError("batch is stale relative to the active head")
        if batch.tick != self.store.next_tick():
            raise BatchRejected("TICK_SEQUENCE_INVALID")
        if self.store.load_state() != before:
            raise BatchRejected("BIAS_BEFORE_NOT_DURABLE_HEAD")
        if (
            after.get("bias_id") != before.get("bias_id")
            or after.get("cjt_id") != before.get("cjt_id")
            or after.get("version") != head.state_version + 1
            or after.get("previous_digest") != head.state_digest
        ):
            raise BatchRejected("BIAS_SUCCESSOR_BINDING_INVALID")
        if after.get("stable") != before.get("stable"):
            raise BatchRejected("STABLE_SUBSTRATE_IS_IMMUTABLE")
        if after.get("governance") != before.get("governance"):
            raise BatchRejected("GOVERNANCE_IS_NOT_SELF_WRITABLE")
        for record in batch.phase_records:
            if not isinstance(record, PhaseRecord) or record.tick != batch.tick:
                raise BatchRejected("PHASE_RECORD_INVALID")
        if tuple(_text(record.phase) for record in batch.phase_records) != MANDATORY_PHASES:
            raise BatchRejected("PHASE_ORDER_INVALID")
        return before, after, head

    def _governance(self, before: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        governance = before.get("governance")
        theta = before.get("theta")
        if not isinstance(governance, Mapping) or not isinstance(theta, Mapping):
            raise BatchRejected("BIAS_AUTHORITY_METADATA_MISSING")
        governance = dict(governance)
        theta = dict(theta)
        if governance.get("quarantined") is True:
            raise BatchRejected("BIAS_QUARANTINED")
        return governance, theta

    def _validate_candidates(
        self,
        batch: CommitBatch,
        before: Mapping[str, Any],
        head: ActiveHead,
    ) -> tuple[
        dict[str, dict[str, Any]],
        dict[str, dict[str, Any]],
        dict[str, dict[str, Any]],
    ]:
        cause = _wire(batch.cause, label="cause")
        cause_id = cause.get("cause_id")
        if cause.get("tick") != batch.tick or not isinstance(cause_id, str):
            raise BatchRejected("CAUSE_BINDING_INVALID")
        candidates = _unique_by(
            batch.candidate_effects, "candidate_effect_id", label="candidate effect"
        )
        receipts = _unique_by(
            batch.verifier_receipts, "receipt_id", label="verifier receipt"
        )
        by_candidate: dict[str, dict[str, Any]] = {}
        for receipt in receipts.values():
            _require_digest(receipt, "receipt_digest", "verifier receipt")
            candidate_id = receipt.get("candidate_effect_id")
            if not isinstance(candidate_id, str) or candidate_id in by_candidate:
                raise BatchRejected("VERIFIER_RECEIPT_BINDING_INVALID")
            by_candidate[candidate_id] = receipt
        if set(candidates) != set(by_candidate):
            raise BatchRejected("EVERY_CANDIDATE_REQUIRES_ONE_VERIFIER_RECEIPT")
        model_digest = before.get("theta", {}).get("model_digest")
        for candidate_id, candidate in candidates.items():
            _require_digest(candidate, "candidate_digest", "candidate effect")
            receipt = by_candidate[candidate_id]
            registered_digest = self.operation_contract_digests.get(
                str(candidate.get("operation_contract_id"))
            )
            expected = {
                "tick": batch.tick,
                "parent_cause_id": cause_id,
                "bias_id": before.get("bias_id"),
                "bias_version": before.get("version"),
                "bias_digest": before.get("state_digest"),
                "model_digest": model_digest,
            }
            if any(candidate.get(key) != value for key, value in expected.items()):
                raise BatchRejected("CANDIDATE_HEAD_BINDING_INVALID")
            if candidate.get("authoritative") is not False:
                raise BatchRejected("CANDIDATE_CANNOT_BE_AUTHORITATIVE")
            if (
                registered_digest is None
                or candidate.get("operation_contract_digest") != registered_digest
            ):
                raise BatchRejected("OPERATION_CONTRACT_NOT_ADMITTED")
            receipt_expected = {
                "tick": batch.tick,
                "cause_id": cause_id,
                "candidate_effect_id": candidate_id,
                "candidate_effect_digest": candidate.get("candidate_digest"),
                "bias_id": before.get("bias_id"),
                "bias_version": before.get("version"),
                "bias_digest": before.get("state_digest"),
                "operation_contract_id": candidate.get("operation_contract_id"),
                "operation_contract_digest": registered_digest,
                "model_digest": model_digest,
                "independent": True,
            }
            if any(receipt.get(key) != value for key, value in receipt_expected.items()):
                raise BatchRejected("VERIFIER_RECEIPT_BINDING_INVALID")
            if receipt.get("verifier_id") == candidate.get("producer_cjt_id"):
                raise BatchRejected("SELF_VERIFICATION_FORBIDDEN")
        return candidates, receipts, by_candidate

    def _validate_state_intents(
        self,
        batch: CommitBatch,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
        by_candidate: Mapping[str, Mapping[str, Any]],
        receipts: Mapping[str, Mapping[str, Any]],
        governance: Mapping[str, Any],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        intents = _unique_by(batch.state_intents, "intent_id", label="state intent")
        if intents and self.coordinator_id not in governance.get("state_write_authorities", []):
            raise BatchRejected("COORDINATOR_HAS_NO_STATE_WRITE_GRANT")
        paths: list[tuple[str, ...]] = []
        projected = _json_clone(before)
        accepted: list[str] = []
        mapped_intents: list[dict[str, Any]] = []
        repair_receipt_ids = {
            str(frame.get("verifier_receipt_id"))
            for frame in (_wire(item, label="repair frame") for item in batch.repair_frames)
        }
        for intent_id, intent in intents.items():
            _require_digest(intent, "intent_digest", "state intent")
            if intent.get("authority_capability") != PROPOSE_STATE_UPDATE:
                raise BatchRejected("STATE_INTENT_CAPABILITY_INVALID")
            if not self._issuer_authorized(
                capability=PROPOSE_STATE_UPDATE,
                issuer_id=intent.get("issuer_id"),
                batch=batch,
            ):
                raise BatchRejected("STATE_INTENT_ISSUER_NOT_ADMITTED")
            if any(
                intent.get(key) != value
                for key, value in {
                    "tick": batch.tick,
                    "target_bias_id": before.get("bias_id"),
                    "expected_bias_version": before.get("version"),
                    "expected_bias_digest": before.get("state_digest"),
                }.items()
            ):
                raise BatchRejected("STATE_INTENT_HEAD_BINDING_INVALID")
            receipt = receipts.get(str(intent.get("verifier_receipt_id")))
            if receipt is None:
                raise BatchRejected("STATE_INTENT_RECEIPT_MISSING")
            path = _decode_pointer(str(intent.get("target_path")))
            if path[0] not in {"memory", "rpm", "operating", "theta"}:
                raise BatchRejected("STATE_INTENT_PROTECTED_PATH")
            if any(path[: len(other)] == other or other[: len(path)] == path for other in paths):
                raise BatchRejected("STATE_INTENT_PATHS_OVERLAP")
            paths.append(path)
            outcome = _text(receipt.get("semantic_outcome"))
            disposition = _text(receipt.get("disposition"))
            if disposition == "ACCEPT":
                if outcome != "INTENDED" or receipt.get("repair_required") is not False:
                    raise BatchRejected("ACCEPT_RECEIPT_NOT_INTENDED")
            elif disposition == "REPAIR":
                if path[0] not in {"rpm", "operating"} or receipt.get("receipt_id") not in repair_receipt_ids:
                    raise BatchRejected("REPAIR_INTENT_SCOPE_INVALID")
            elif path[0] != "operating":
                raise BatchRejected("NONACCEPT_INTENT_SCOPE_INVALID")
            _set_pointer(projected, str(intent["target_path"]), intent["replacement"])
            accepted.append(intent_id)
            mapped_intents.append(intent)
        projected["version"] = int(before["version"]) + 1
        projected["previous_digest"] = before["state_digest"]
        projected["state_digest"] = after["state_digest"]
        if projected != after:
            raise BatchRejected("BIAS_AFTER_DOES_NOT_EQUAL_INTENT_RESULT")
        return accepted, mapped_intents

    def _validate_memory_intents(
        self,
        batch: CommitBatch,
        before: Mapping[str, Any],
        receipts: Mapping[str, Mapping[str, Any]],
        governance: Mapping[str, Any],
    ) -> tuple[list[str], tuple[StoredDocument, ...], list[dict[str, Any]]]:
        intents = _unique_by(batch.memory_intents, "intent_id", label="memory intent")
        if intents and self.coordinator_id not in governance.get("memory_write_authorities", []):
            raise BatchRejected("COORDINATOR_HAS_NO_MEMORY_WRITE_GRANT")
        accepted: list[str] = []
        documents: list[StoredDocument] = []
        mapped: list[dict[str, Any]] = []
        record_ids: set[str] = set()
        for intent_id, intent in intents.items():
            _require_digest(intent, "intent_digest", "memory intent")
            if intent.get("authority_capability") != PROPOSE_MEMORY_WRITE:
                raise BatchRejected("MEMORY_INTENT_CAPABILITY_INVALID")
            if not self._issuer_authorized(
                capability=PROPOSE_MEMORY_WRITE,
                issuer_id=intent.get("issuer_id"),
                batch=batch,
            ):
                raise BatchRejected("MEMORY_INTENT_ISSUER_NOT_ADMITTED")
            if any(
                intent.get(key) != value
                for key, value in {
                    "tick": batch.tick,
                    "target_bias_id": before.get("bias_id"),
                    "expected_bias_version": before.get("version"),
                    "expected_bias_digest": before.get("state_digest"),
                }.items()
            ):
                raise BatchRejected("MEMORY_INTENT_HEAD_BINDING_INVALID")
            receipt = receipts.get(str(intent.get("verifier_receipt_id")))
            if receipt is None or _text(receipt.get("disposition")) != "ACCEPT" or _text(
                receipt.get("semantic_outcome")
            ) != "INTENDED":
                raise BatchRejected("MEMORY_INTENT_NOT_ACCEPTED")
            record_id = intent.get("memory_record_id")
            if not isinstance(record_id, str) or not record_id or record_id in record_ids:
                raise BatchRejected("MEMORY_RECORD_ID_INVALID")
            record_ids.add(record_id)
            accepted.append(intent_id)
            mapped.append(intent)
            memory_body = {
                "schema_version": "cas.neural-cjt.memory-record/0.2",
                "memory_record_id": record_id,
                "memory_kind": _text(intent["memory_kind"]),
                "content": intent["content"],
                "content_ref": intent.get("content_ref"),
                "confidence_ppm": intent["confidence_ppm"],
                "provenance": list(intent["provenance"]),
                "evidence_refs": list(intent["evidence_refs"]),
                "source_intent_id": intent_id,
                "verifier_receipt_id": intent["verifier_receipt_id"],
                "committed_by": self.coordinator_id,
            }
            memory_record = {
                **memory_body,
                "record_digest": canonical_digest(memory_body),
            }
            documents.append(StoredDocument(record_id, memory_record))
        return accepted, tuple(documents), mapped

    def _validate_qualification(
        self,
        intent: Mapping[str, Any],
        qualification: Mapping[str, Any],
        post_model_digest: str,
    ) -> None:
        digest_field = "receipt_digest" if "receipt_digest" in qualification else None
        if digest_field is None or not verify_declared_digest(qualification, digest_field):
            raise BatchRejected("QUALIFICATION_RECEIPT_DIGEST_INVALID")
        qualified_digest = qualification.get(
            "candidate_model_digest", qualification.get("model_digest")
        )
        disposition = _text(
            qualification.get("disposition", qualification.get("outcome"))
        )
        if (
            qualification.get("qualification_receipt_id", qualification.get("receipt_id"))
            != intent.get("qualification_receipt_id")
            or qualification.get("independent") is not True
            or qualified_digest != post_model_digest
            or disposition not in {"ACCEPT", "PASS", "QUALIFIED"}
            or qualification.get("qualified") is not True
            or qualification.get("target_improved") is not True
            or qualification.get("retention_passed") is not True
            or qualification.get("regression_passed") is not True
        ):
            raise BatchRejected("MODEL_UPDATE_NOT_INDEPENDENTLY_QUALIFIED")
        baseline_digest = qualification.get("baseline_model_digest")
        if baseline_digest is not None and baseline_digest != intent.get("expected_model_digest"):
            raise BatchRejected("QUALIFICATION_BASELINE_MODEL_MISMATCH")
        bound_verifier = qualification.get("verifier_receipt_id")
        if bound_verifier is not None and bound_verifier != intent.get("verifier_receipt_id"):
            raise BatchRejected("QUALIFICATION_VERIFIER_BINDING_INVALID")
        bound_groups = qualification.get("parameter_group_ids")
        if bound_groups is not None and set(bound_groups) != set(intent.get("parameter_group_ids", [])):
            raise BatchRejected("QUALIFICATION_PARAMETER_GROUP_BINDING_INVALID")

    def _validate_model_intents(
        self,
        batch: CommitBatch,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
        receipts: Mapping[str, Mapping[str, Any]],
        governance: Mapping[str, Any],
        theta: Mapping[str, Any],
    ) -> tuple[list[str], list[dict[str, Any]], str]:
        intents = _unique_by(batch.model_intents, "intent_id", label="model intent")
        if len(intents) > 1:
            raise BatchRejected("ONLY_ONE_MODEL_UPDATE_PER_COMMIT")
        pre_model_digest = theta.get("model_digest")
        post_theta = after.get("theta")
        if not isinstance(pre_model_digest, str) or not isinstance(post_theta, Mapping):
            raise BatchRejected("MODEL_HEAD_MISSING")
        post_model_digest = post_theta.get("model_digest")
        if not isinstance(post_model_digest, str):
            raise BatchRejected("POST_MODEL_DIGEST_MISSING")
        if not intents:
            if batch.model_version is not None or post_model_digest != pre_model_digest:
                raise BatchRejected("MODEL_CHANGED_WITHOUT_INTENT")
            return [], [], post_model_digest
        if self.coordinator_id not in governance.get("state_write_authorities", []):
            raise BatchRejected("COORDINATOR_HAS_NO_MODEL_WRITE_GRANT")
        if batch.model_version is None:
            raise BatchRejected("MODEL_VERSION_ARTIFACT_MISSING")
        qualifications: dict[str, dict[str, Any]] = {}
        for value in batch.qualification_receipts:
            qualification = _wire(value, label="qualification receipt")
            identity = qualification.get(
                "qualification_receipt_id", qualification.get("receipt_id")
            )
            if not isinstance(identity, str) or not identity or identity in qualifications:
                raise BatchRejected("QUALIFICATION_RECEIPT_IDENTITY_INVALID")
            qualifications[identity] = qualification
        intent_id, intent = next(iter(intents.items()))
        _require_digest(intent, "intent_digest", "model intent")
        if intent.get("authority_capability") != PROPOSE_MODEL_UPDATE:
            raise BatchRejected("MODEL_INTENT_CAPABILITY_INVALID")
        if not self._issuer_authorized(
            capability=PROPOSE_MODEL_UPDATE,
            issuer_id=intent.get("issuer_id"),
            batch=batch,
        ):
            raise BatchRejected("MODEL_INTENT_ISSUER_NOT_ADMITTED")
        receipt = receipts.get(str(intent.get("verifier_receipt_id")))
        if receipt is None or _text(receipt.get("disposition")) != "ACCEPT" or _text(
            receipt.get("semantic_outcome")
        ) != "INTENDED":
            raise BatchRejected("MODEL_INTENT_NOT_ACCEPTED")
        expected = {
            "tick": batch.tick,
            "model_id": theta.get("model_id"),
            "expected_model_version": theta.get("model_version"),
            "expected_model_digest": pre_model_digest,
        }
        if any(intent.get(key) != value for key, value in expected.items()):
            raise BatchRejected("MODEL_INTENT_HEAD_BINDING_INVALID")
        groups = set(intent.get("parameter_group_ids", []))
        if not groups or not groups.issubset(set(theta.get("parameter_group_ids", []))):
            raise BatchRejected("MODEL_PARAMETER_GROUP_NOT_ADMITTED")
        learning_permissions = set(governance.get("learning_permissions", []))
        if "learn" not in learning_permissions or not groups.issubset(learning_permissions):
            raise BatchRejected("BIAS_LEARNING_PERMISSION_DENIED")
        qualification = qualifications.get(str(intent.get("qualification_receipt_id")))
        if qualification is None:
            raise BatchRejected("QUALIFICATION_RECEIPT_MISSING")
        self._validate_qualification(intent, qualification, post_model_digest)
        artifact_ref = intent.get("candidate_artifact")
        if not isinstance(artifact_ref, Mapping):
            raise BatchRejected("MODEL_CANDIDATE_ARTIFACT_MISSING")
        if (
            artifact_ref.get("artifact_id") != batch.model_version.artifact_id
            or artifact_ref.get("sha256") != batch.model_version.model_digest
            or batch.model_version.model_digest != post_model_digest
            or batch.model_version.parent_model_digest != pre_model_digest
        ):
            raise BatchRejected("MODEL_VERSION_BINDING_INVALID")
        if post_theta.get("model_version") != int(theta.get("model_version", -1)) + 1:
            raise BatchRejected("MODEL_VERSION_NUMBER_INVALID")
        return [intent_id], [intent], post_model_digest

    def _validate_repairs(
        self,
        batch: CommitBatch,
        receipts: Mapping[str, Mapping[str, Any]],
        before: Mapping[str, Any],
    ) -> tuple[StoredDocument, ...]:
        frames = _unique_by(batch.repair_frames, "repair_id", label="repair frame")
        if frames:
            # The single-Bias compatibility coordinator does not retain the
            # trusted network topology needed to prove a viable t+1/t+2 repair
            # round trip.  Only NetworkAtomicCoordinator may authorize v0.2
            # RepairFrame openings.
            raise BatchRejected("REPAIR_REQUIRES_NETWORK_COORDINATOR")
        return ()

    def _verify_artifact_refs(self, values: Iterable[Any], artifacts: Sequence[StoredArtifact]) -> None:
        supplied = {artifact.artifact_id: artifact for artifact in artifacts}
        if len(supplied) != len(artifacts):
            raise BatchRejected("ARTIFACT_ID_DUPLICATE")
        for artifact in artifacts:
            artifact.verify()
        for value in values:
            for artifact_id, digest in _artifact_references(value):
                artifact = supplied.get(artifact_id)
                if artifact is not None:
                    if artifact.sha256 != digest:
                        raise BatchRejected("ARTIFACT_REFERENCE_DIGEST_MISMATCH")
                elif not self.store.has_artifact(artifact_id, digest):
                    raise BatchRejected("ARTIFACT_REFERENCE_NOT_RETAINED")

    def _published_effects(
        self,
        batch: CommitBatch,
        candidates: Mapping[str, Mapping[str, Any]],
        by_candidate: Mapping[str, Mapping[str, Any]],
        governance: Mapping[str, Any],
        commit_receipt_id: str,
    ) -> tuple[StoredDocument, ...]:
        accepted = [
            (candidate_id, candidate, by_candidate[candidate_id])
            for candidate_id, candidate in candidates.items()
            if _text(by_candidate[candidate_id].get("disposition")) == "ACCEPT"
            and _text(by_candidate[candidate_id].get("semantic_outcome")) == "INTENDED"
        ]
        if accepted:
            if batch.effect_publication_capability != REQUEST_EFFECT_PUBLICATION:
                raise BatchRejected("EFFECT_PUBLICATION_CAPABILITY_INVALID")
            if self.coordinator_id not in governance.get("effect_publication_authorities", []):
                raise BatchRejected("COORDINATOR_HAS_NO_EFFECT_PUBLICATION_GRANT")
        documents: list[StoredDocument] = []
        for candidate_id, candidate, receipt in accepted:
            provenance = tuple(
                dict.fromkeys(
                    [
                        *candidate.get("provenance", []),
                        str(receipt["receipt_id"]),
                        self.authority_contract_id,
                    ]
                )
            )
            core = {
                "contract_type": PublishedEffect.CONTRACT_TYPE,
                "schema_version": PublishedEffect.SCHEMA_VERSION,
                "published_effect_id": "pending",
                "candidate_effect_id": candidate_id,
                "tick": batch.tick,
                "producer_cjt_id": candidate["producer_cjt_id"],
                "content": candidate["content"],
                "content_ref": candidate.get("content_ref"),
                "verifier_receipt_id": receipt["receipt_id"],
                "commit_receipt_id": commit_receipt_id,
                "provenance": list(provenance),
                "authoritative": True,
            }
            identity = canonical_digest(core)
            core["published_effect_id"] = f"effect-{identity[:24]}"
            core["publication_digest"] = canonical_digest(core)
            typed_content_ref = core["content_ref"]
            if isinstance(typed_content_ref, Mapping):
                ref_fields = {item.name for item in dataclass_fields(TensorArtifactRef)}
                typed_content_ref = TensorArtifactRef(
                    **{key: value for key, value in typed_content_ref.items() if key in ref_fields}
                )
            effect = PublishedEffect(
                **{
                    key: typed_content_ref if key == "content_ref" else value
                    for key, value in core.items()
                    if key not in {"contract_type", "schema_version"}
                }
            )
            if not verify_declared_digest(effect, "publication_digest"):
                raise BatchRejected("PUBLISHED_EFFECT_DIGEST_INVALID")
            documents.append(StoredDocument(effect.published_effect_id, effect))
        return tuple(documents)

    def _make_trace(
        self,
        batch: CommitBatch,
        *,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
        pre_model_digest: str,
        post_model_digest: str,
        candidate_ids: Sequence[str],
        published_ids: Sequence[str],
        verifier_receipt_ids: Sequence[str],
        commit_receipt_id: str,
        accepted_intent_ids: Sequence[str],
        repair_ids: Sequence[str],
        rejected_intent_ids: Sequence[str] = (),
    ) -> SealedTrace:
        cause = _wire(batch.cause, label="cause")
        payload = {
            "tick": batch.tick,
            "runtime_id": batch.runtime_id,
            "software_digest": batch.software_digest,
            "cause_id": cause["cause_id"],
            "cjt_ids": list(batch.cjt_ids),
            "pre_state_digest": before["state_digest"],
            "post_state_digest": after["state_digest"],
            "pre_model_digest": pre_model_digest,
            "post_model_digest": post_model_digest,
            "phases": list(batch.phase_records),
            "candidate_effect_ids": list(candidate_ids),
            "published_effect_ids": list(published_ids),
            "verifier_receipt_ids": list(verifier_receipt_ids),
            "commit_receipt_id": commit_receipt_id,
            "memory_read_refs": list(batch.memory_read_refs),
            "memory_write_refs": [item.memory_record_id if hasattr(item, "memory_record_id") else _wire(item, label="memory intent")["memory_record_id"] for item in batch.memory_intents],
            "accepted_intent_ids": list(accepted_intent_ids),
            "rejected_intent_ids": list(rejected_intent_ids),
            "sealed": True,
        }
        sealed = seal_trace(
            payload,
            previous_trace_digest=batch.base_trace_digest,
            sensitive_fields=batch.sensitive_trace_fields,
        )
        # Reify the frozen public type as a second structural check.  Extra
        # diagnostic fields remain in SealedTrace but never grant authority.
        typed_fields = {item.name for item in dataclass_fields(TickTrace)}
        typed_payload = {key: value for key, value in sealed.payload.items() if key in typed_fields}
        typed_payload["phases"] = batch.phase_records
        trace = TickTrace(**typed_payload)
        if not verify_declared_digest(trace, "trace_digest"):
            raise BatchRejected("TRACE_DIGEST_INVALID")
        return sealed

    def _make_receipt(
        self,
        *,
        receipt_id: str,
        batch_id: str,
        tick: int,
        disposition: CommitDisposition,
        pre_state_digest: str,
        post_state_digest: str,
        pre_model_digest: str,
        post_model_digest: str,
        accepted_intent_ids: Sequence[str],
        published_effect_ids: Sequence[str],
        opened_repair_ids: Sequence[str],
        trace_id: str,
        reason_codes: Sequence[str],
        rollback_of_receipt_id: str | None = None,
    ) -> CommitReceipt:
        data: dict[str, Any] = {
            "receipt_id": receipt_id,
            "tick": tick,
            "batch_id": batch_id,
            "coordinator_id": self.coordinator_id,
            "authority_contract_id": self.authority_contract_id,
            "authorized": True,
            "disposition": disposition,
            "pre_state_digest": pre_state_digest,
            "post_state_digest": post_state_digest,
            "pre_model_digest": pre_model_digest,
            "post_model_digest": post_model_digest,
            "accepted_intent_ids": tuple(accepted_intent_ids),
            "rejected_intent_ids": (),
            "published_effect_ids": tuple(published_effect_ids),
            "opened_repair_ids": tuple(opened_repair_ids),
            "reason_codes": tuple(dict.fromkeys(reason_codes)),
            "atomic": True,
            "rollback_of_receipt_id": rollback_of_receipt_id,
            "persisted_snapshot_id": f"snapshot-{post_state_digest[:24]}",
            "trace_id": trace_id,
        }
        allowed = {item.name for item in dataclass_fields(CommitReceipt)}
        data = {key: value for key, value in data.items() if key in allowed}
        digest_payload = {
            "contract_type": CommitReceipt.CONTRACT_TYPE,
            "schema_version": CommitReceipt.SCHEMA_VERSION,
            **data,
        }
        data["receipt_digest"] = canonical_digest(digest_payload)
        receipt = CommitReceipt(**data)
        if not verify_declared_digest(receipt, "receipt_digest"):
            raise BatchRejected("COMMIT_RECEIPT_DIGEST_INVALID")
        return receipt

    def _commit_authoritative(
        self, batch: CommitBatch, *, fault_at: str | None = None
    ) -> CommitReceipt:
        """Commit all accepted writes/effects, or leave the store byte-logically unchanged."""

        request_digest = self._request_digest(batch)
        self._validate_compatibility_scope(batch)
        previous = self._idempotent_receipt(batch.batch_id, request_digest)
        if previous is not None:
            return previous
        before, after, head = self._validate_common(batch)
        governance, theta = self._governance(before)
        candidates, receipts, by_candidate = self._validate_candidates(batch, before, head)
        state_ids, state_values = self._validate_state_intents(
            batch, before, after, by_candidate, receipts, governance
        )
        memory_ids, memory_documents, memory_values = self._validate_memory_intents(
            batch, before, receipts, governance
        )
        model_ids, model_values, post_model_digest = self._validate_model_intents(
            batch, before, after, receipts, governance, theta
        )
        repair_documents = self._validate_repairs(batch, receipts, before)
        accepted_ids = [*state_ids, *memory_ids, *model_ids]
        receipt_id = f"commit-{request_digest[:24]}"
        effect_documents = self._published_effects(
            batch, candidates, by_candidate, governance, receipt_id
        )
        if not accepted_ids and not effect_documents and not repair_documents:
            raise BatchRejected("EMPTY_COMMIT_FORBIDDEN")
        self._verify_artifact_refs(
            [
                after,
                *candidates.values(),
                *state_values,
                *memory_values,
                *model_values,
                *[item.payload for item in repair_documents],
            ],
            batch.artifacts,
        )
        pre_model_digest = theta.get("model_digest")
        if head.model_digest != pre_model_digest:
            raise StaleHeadError("model digest is stale relative to the active head")
        published_ids = [item.record_id for item in effect_documents]
        repair_ids = [item.record_id for item in repair_documents]
        trace = self._make_trace(
            batch,
            before=before,
            after=after,
            pre_model_digest=pre_model_digest,
            post_model_digest=post_model_digest,
            candidate_ids=list(candidates),
            published_ids=published_ids,
            verifier_receipt_ids=list(receipts),
            commit_receipt_id=receipt_id,
            accepted_intent_ids=accepted_ids,
            rejected_intent_ids=(),
            repair_ids=repair_ids,
        )
        receipt = self._make_receipt(
            receipt_id=receipt_id,
            batch_id=batch.batch_id,
            tick=batch.tick,
            disposition=CommitDisposition.COMMITTED,
            pre_state_digest=before["state_digest"],
            post_state_digest=after["state_digest"],
            pre_model_digest=pre_model_digest,
            post_model_digest=post_model_digest,
            accepted_intent_ids=accepted_ids,
            published_effect_ids=published_ids,
            opened_repair_ids=repair_ids,
            trace_id=trace.trace_id,
            reason_codes=("AUTHORIZED_ATOMIC_COMMIT",),
        )
        request_payload = self._request_payload(batch)
        cause_payload = _wire(batch.cause, label="cause")
        qualification_documents: list[StoredDocument] = []
        for value in batch.qualification_receipts:
            payload = _wire(value, label="qualification receipt")
            identity = payload.get("qualification_receipt_id", payload.get("receipt_id"))
            if not isinstance(identity, str) or not identity:
                raise BatchRejected("QUALIFICATION_RECEIPT_IDENTITY_INVALID")
            qualification_documents.append(StoredDocument(identity, payload))
        write = AtomicWriteSet(
            batch_id=batch.batch_id,
            request_digest=request_digest,
            expected_state_digest=before["state_digest"],
            expected_state_version=before["version"],
            expected_trace_digest=batch.base_trace_digest,
            expected_model_digest=pre_model_digest,
            post_state_digest=after["state_digest"],
            post_state_version=after["version"],
            post_state=after,
            post_model_digest=post_model_digest,
            trace=trace,
            receipt_id=receipt.receipt_id,
            receipt=receipt,
            transition_batch=StoredDocument(batch.batch_id, request_payload),
            causes=(StoredDocument(str(cause_payload["cause_id"]), cause_payload),),
            candidate_effects=tuple(
                StoredDocument(identity, payload) for identity, payload in candidates.items()
            ),
            verifier_receipts=tuple(
                StoredDocument(identity, payload) for identity, payload in receipts.items()
            ),
            qualification_receipts=tuple(qualification_documents),
            state_intents=tuple(
                StoredDocument(str(payload["intent_id"]), payload) for payload in state_values
            ),
            model_intents=tuple(
                StoredDocument(str(payload["intent_id"]), payload) for payload in model_values
            ),
            memory_intents=tuple(
                StoredDocument(str(payload["intent_id"]), payload) for payload in memory_values
            ),
            artifacts=batch.artifacts,
            published_effects=effect_documents,
            memory_records=memory_documents,
            repair_frames=repair_documents,
            model_version=batch.model_version,
        )
        stored = self.store.commit(write, fault_at=fault_at)
        return CommitReceipt(**_receipt_kwargs(stored))

    def _record_rejection(
        self,
        batch: CommitBatch,
        *,
        request_payload: Mapping[str, Any],
        request_digest: str,
        reason_codes: Sequence[str],
    ) -> None:
        head = self.store.head
        rejected_intent_ids: list[str] = []
        for collection in (batch.state_intents, batch.model_intents, batch.memory_intents):
            for value in collection:
                try:
                    identity = _wire(value, label="rejected intent").get("intent_id")
                except BatchRejected:
                    identity = None
                if isinstance(identity, str) and identity:
                    rejected_intent_ids.append(identity)
        cause_payload = _wire(batch.cause, label="cause")
        audit_payload = {
            "tick": batch.tick,
            "runtime_id": batch.runtime_id,
            "software_digest": batch.software_digest,
            "cause_id": cause_payload.get("cause_id"),
            "cjt_ids": list(batch.cjt_ids),
            "pre_state_digest": head.state_digest,
            "post_state_digest": head.state_digest,
            "pre_state_version": head.state_version,
            "post_state_version": head.state_version,
            "pre_model_digest": head.model_digest,
            "post_model_digest": head.model_digest,
            "active_trace_digest": head.trace_digest,
            "active_commit_receipt_id": head.commit_receipt_id,
            "candidate_effect_ids": [
                mapped["candidate_effect_id"]
                for mapped in (
                    _wire(item, label="candidate effect") for item in batch.candidate_effects
                )
                if isinstance(mapped.get("candidate_effect_id"), str)
            ],
            "verifier_receipt_ids": [
                mapped["receipt_id"]
                for mapped in (
                    _wire(item, label="verifier receipt") for item in batch.verifier_receipts
                )
                if isinstance(mapped.get("receipt_id"), str)
            ],
            "accepted_intent_ids": [],
            "rejected_intent_ids": list(dict.fromkeys(rejected_intent_ids)),
            "published_effect_ids": [],
            "opened_repair_ids": [],
            "reason_codes": list(dict.fromkeys(reason_codes)),
            "atomic_rollback": True,
            "request": dict(request_payload),
        }
        self.store.record_rejection(
            batch_id=batch.batch_id,
            request_digest=request_digest,
            payload=audit_payload,
            sensitive_fields=batch.sensitive_trace_fields,
        )

    def commit(self, batch: CommitBatch, *, fault_at: str | None = None) -> CommitReceipt:
        """Commit a valid batch or append only a non-authoritative rejection audit."""

        request_payload = self._request_payload(batch)
        request_digest = canonical_digest(request_payload)
        try:
            return self._commit_authoritative(batch, fault_at=fault_at)
        except BatchRejected as exc:
            self._record_rejection(
                batch,
                request_payload=request_payload,
                request_digest=request_digest,
                reason_codes=exc.reason_codes,
            )
            raise
        except StaleHeadError:
            self._record_rejection(
                batch,
                request_payload=request_payload,
                request_digest=request_digest,
                reason_codes=("STALE_ACTIVE_HEAD",),
            )
            raise

    def _rollback_phases(
        self,
        request: RollbackRequest,
        *,
        cause_id: str,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
        pre_model_digest: str,
        post_model_digest: str,
        previous_trace_digest: str | None,
    ) -> tuple[PhaseRecord, ...]:
        """Emit a complete neutral-compute phase ledger for compensation."""

        empty: list[Any] = []
        phases = {
            "READ": (
                {"cause_id": cause_id, "state_digest": before["state_digest"], "model_digest": pre_model_digest},
                {"bias_ids": [before["bias_id"]], "bias_digests": [before["state_digest"]], "memory_read_refs": empty},
                {},
            ),
            "CANDIDATE": (
                {"candidate_operation_ids": empty},
                {"candidate_cjt_ids": empty, "operation_contract_ids": empty},
                {},
            ),
            "READINESS": (
                {"profile_ids": empty},
                {"desire": empty, "wisdom": empty, "power": empty, "hard_open": empty},
                {},
            ),
            "ROUTE": (
                {
                    "control_cjt_id": self.coordinator_id,
                    "topology_mask": empty,
                    "permission_mask": empty,
                    "quarantine_mask": empty,
                    "budget_mask": empty,
                    "readiness_hard_mask": empty,
                    "route_settings": {},
                    "native_compute": {},
                    "compute_policy": {"mode": "COMPENSATING_ROLLBACK", "rollback_of_receipt_id": request.rollback_of_receipt_id},
                    "control_binding_manifest": {},
                },
                {
                    "compute_plan": {},
                    "effective_path_mask": empty,
                    "conducting_query_mask": empty,
                    "current_microunits": empty,
                    "total_current_microunits": empty,
                    "flow_allocation_ppm": empty,
                },
                {},
            ),
            "EXECUTE": (
                {"scheduled_cjt_ids": empty, "operation_ids": empty},
                {"executed_cjt_ids": empty, "compute_units_used": 0},
                {},
            ),
            "OBSERVE": (
                {"executed_cjt_ids": empty},
                {"candidate_effect_ids": empty, "operating_regions": empty, "artifact_ids": empty, "compute_observations": {}},
                {"control_binding_digest": None, "declared_beta_microunits": empty, "live_beta_by_head_microunits": empty},
            ),
            "VERIFY": (
                {"candidate_effect_ids": empty, "evidence_ids": empty},
                {"verifier_receipt_ids": empty, "semantic_outcomes": empty, "dispositions": empty},
                {},
            ),
            "DIAGNOSE": (
                {"operating_regions": empty, "semantic_outcomes": empty},
                {"reason_codes": ["COMPENSATING_ROLLBACK", *request.reason_codes], "repair_required": False},
                {},
            ),
            "EMIT": (
                {"verifier_receipt_ids": empty},
                {"state_intent_ids": empty, "model_intent_ids": empty, "memory_intent_ids": empty, "repair_ids": empty, "repair_outcome_ids": empty, "publication_requested": False},
                {},
            ),
            "COMMIT": (
                {"pre_state_digest": before["state_digest"], "pre_model_digest": pre_model_digest},
                {"proposed_post_state_digest": after["state_digest"], "proposed_post_model_digest": post_model_digest},
                {},
            ),
            "TRACE": (
                {"previous_trace_digest": previous_trace_digest},
                {"seal_requested": True, "phase_count": len(MANDATORY_PHASES)},
                {},
            ),
        }
        return tuple(
            PhaseRecord(
                phase=TickPhase(name),
                tick=request.tick,
                inputs=phases[name][0],
                outputs=phases[name][1],
                diagnostics=phases[name][2],
                compute_units=0,
            )
            for name in MANDATORY_PHASES
        )

    def rollback(
        self, request: RollbackRequest, *, fault_at: str | None = None
    ) -> CommitReceipt:
        """Restore a retained pre-state through a new auditable commit."""

        if request.authority_capability != PROPOSE_STATE_UPDATE:
            raise BatchRejected("ROLLBACK_CAPABILITY_INVALID")
        request_payload = {
            "mode": "COMPENSATING_ROLLBACK",
            "batch_id": request.batch_id,
            "tick": request.tick,
            "rollback_of_receipt_id": request.rollback_of_receipt_id,
            "issuer_id": request.issuer_id,
            "authority_capability": request.authority_capability,
            "cause_id": request.cause_id,
            "runtime_id": request.runtime_id,
            "software_digest": request.software_digest,
            "cjt_ids": list(request.cjt_ids),
            "reason_codes": list(request.reason_codes),
        }
        request_digest = canonical_digest(request_payload)
        previous = self._idempotent_receipt(request.batch_id, request_digest)
        if previous is not None:
            return previous
        if (
            request.runtime_id != self.trusted_runtime_id
            or request.software_digest != self.trusted_software_digest
            or request.cjt_ids != self.trusted_cjt_ids
        ):
            raise BatchRejected("RUNTIME_IDENTITY_INVALID")
        if request.tick != self.store.next_tick():
            raise BatchRejected("TICK_SEQUENCE_INVALID")
        original = self.store.receipt_by_id(request.rollback_of_receipt_id)
        head = self.store.head
        current = self.store.load_state()
        governance, current_theta = self._governance(current)
        if self.coordinator_id not in governance.get("state_write_authorities", []):
            raise BatchRejected("COORDINATOR_HAS_NO_ROLLBACK_GRANT")
        if request.issuer_id not in governance.get("state_write_authorities", []):
            raise BatchRejected("ROLLBACK_ISSUER_NOT_AUTHORIZED")
        target_digest = original.get("pre_state_digest")
        target_model_digest = original.get("pre_model_digest")
        if not isinstance(target_digest, str) or not isinstance(target_model_digest, str):
            raise BatchRejected("ROLLBACK_TARGET_INVALID")
        if not self.store.is_state_ancestor(target_digest, head.state_digest):
            raise BatchRejected("ROLLBACK_TARGET_IS_NOT_ANCESTOR")
        _, _, target = self.store.state_record(target_digest)
        if target.get("stable") != current.get("stable") or target.get("governance") != current.get(
            "governance"
        ):
            raise BatchRejected("ROLLBACK_CANNOT_CHANGE_PROTECTED_BIAS")
        post = _json_clone(target)
        post["version"] = head.state_version + 1
        post["previous_digest"] = head.state_digest
        post.pop("state_digest", None)
        post_digest = canonical_digest(post)
        post["state_digest"] = post_digest
        receipt_id = f"commit-{request_digest[:24]}"
        rollback_cause = make_cause(
            tick=request.tick,
            cause_kind=CauseKind.PROPOSITION,
            content={
                "mode": "COMPENSATING_ROLLBACK",
                "rollback_of_receipt_id": request.rollback_of_receipt_id,
                "reason_codes": list(request.reason_codes),
            },
            goal_context={"kind": "COMPENSATING_ROLLBACK"},
            source="prototype:atomic-coordinator",
            provenance=(f"commit-receipt:{request.rollback_of_receipt_id}",),
            candidate_operation_ids=(),
        )
        if request.cause_id != rollback_cause.cause_id:
            raise BatchRejected("ROLLBACK_CAUSE_IDENTITY_INVALID")
        pre_model_digest = head.model_digest or current_theta["model_digest"]
        phases = self._rollback_phases(
            request,
            cause_id=rollback_cause.cause_id,
            before=current,
            after=post,
            pre_model_digest=pre_model_digest,
            post_model_digest=target_model_digest,
            previous_trace_digest=head.trace_digest,
        )
        pseudo_batch = CommitBatch(
            batch_id=request.batch_id,
            tick=request.tick,
            base_snapshot_hash=head.state_digest,
            base_trace_digest=head.trace_digest,
            cause=rollback_cause,
            bias_before=current,
            bias_after=post,
            candidate_effects=(),
            verifier_receipts=(),
            state_intents=(),
            model_intents=(),
            memory_intents=(),
            repair_frames=(),
            phase_records=phases,
            runtime_id=request.runtime_id,
            software_digest=request.software_digest,
            cjt_ids=request.cjt_ids,
        )
        trace = self._make_trace(
            pseudo_batch,
            before=current,
            after=post,
            pre_model_digest=pre_model_digest,
            post_model_digest=target_model_digest,
            candidate_ids=(),
            published_ids=(),
            verifier_receipt_ids=(),
            commit_receipt_id=receipt_id,
            accepted_intent_ids=(f"rollback:{request.rollback_of_receipt_id}",),
            rejected_intent_ids=(),
            repair_ids=(),
        )
        receipt = self._make_receipt(
            receipt_id=receipt_id,
            batch_id=request.batch_id,
            tick=request.tick,
            disposition=CommitDisposition.ROLLED_BACK,
            pre_state_digest=head.state_digest,
            post_state_digest=post_digest,
            pre_model_digest=pre_model_digest,
            post_model_digest=target_model_digest,
            accepted_intent_ids=(f"rollback:{request.rollback_of_receipt_id}",),
            published_effect_ids=(),
            opened_repair_ids=(),
            trace_id=trace.trace_id,
            reason_codes=("COMPENSATING_ROLLBACK", *request.reason_codes),
            rollback_of_receipt_id=request.rollback_of_receipt_id,
        )
        stored = self.store.commit(
            AtomicWriteSet(
                batch_id=request.batch_id,
                request_digest=request_digest,
                expected_state_digest=head.state_digest,
                expected_state_version=head.state_version,
                expected_trace_digest=head.trace_digest,
                expected_model_digest=head.model_digest,
                post_state_digest=post_digest,
                post_state_version=head.state_version + 1,
                post_state=post,
                post_model_digest=target_model_digest,
                trace=trace,
                receipt_id=receipt_id,
                receipt=receipt,
                transition_batch=StoredDocument(request.batch_id, request_payload),
                causes=(StoredDocument(rollback_cause.cause_id, rollback_cause),),
                rollback_of_receipt_id=request.rollback_of_receipt_id,
            ),
            fault_at=fault_at,
        )
        return CommitReceipt(**_receipt_kwargs(stored))

    def restore_and_verify(self) -> RecoverySnapshot:
        """Reopen-time check used before serving any authoritative state."""

        if not self.store.verify_integrity():
            raise PersistenceError("durable Neural CJT history failed restart verification")
        head = self.store.head
        state = self.store.load_state()
        if state.get("state_digest") != head.state_digest or state.get("version") != head.state_version:
            raise PersistenceError("active head does not match its retained Bias payload")
        traces = self.store.trace_events()
        if traces and not verify_trace_chain(traces):
            raise PersistenceError("durable trace chain failed restart verification")
        return RecoverySnapshot(head=head, state=state, traces=traces)


__all__ = [
    "PROPOSE_STATE_UPDATE",
    "PROPOSE_MODEL_UPDATE",
    "PROPOSE_MEMORY_WRITE",
    "REQUEST_EFFECT_PUBLICATION",
    "AtomicCoordinator",
    "BatchRejected",
    "CommitBatch",
    "CoordinatorError",
    "RecoverySnapshot",
    "RollbackRequest",
]
