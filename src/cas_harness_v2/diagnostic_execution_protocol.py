"""Strict, additive Diagnostic Stage C child-execution carriers.

This module is deliberately separate from every v1 worker, Study, and Stage C
carrier.  It validates canonical bytes and exact prospective associations only.
It does not authenticate a worker, execute a model, provide durable one-use,
trusted time, WORM retention, a scientific conclusion, a product route, a
license, or disclosure authority.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any

from ._strict_json import (
    canonical_json_bytes,
    canonical_sha256,
    freeze_json,
    load_json_object,
    sha256_bytes,
    thaw_json,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_bool,
    expect_enum,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
)
from .diagnostic_preregistration import (
    DIAGNOSTIC_CALIBRATION,
    DIAGNOSTIC_ONLY,
    DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE,
    DiagnosticPreregistrationArtifact,
    DiagnosticPreregistrationChain,
)
from .diagnostic_study_protocol import (
    DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE,
    DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE,
    STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    DiagnosticStudyPlanArtifact,
    DiagnosticStudyRequestArtifact,
    StageCCaptureRequestArtifact,
    load_diagnostic_study_plan,
    load_diagnostic_study_request,
    load_stagec_capture_request,
)


DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_SCHEMA = (
    "cas_harness_v2.diagnostic_stagec_execution_contract.v2"
)
DIAGNOSTIC_CHILD_EXECUTION_BINDING_SCHEMA = (
    "cas_harness_v2.diagnostic_child_execution_binding.v2"
)
DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA = (
    "cas_harness_v2.diagnostic_worker_authorization.v2"
)
DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA = (
    "cas_harness_v2.diagnostic_child_terminal_receipt.v2"
)

DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-stagec-execution-contract-v2+json"
)
DIAGNOSTIC_CHILD_EXECUTION_BINDING_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-child-execution-binding-v2+json"
)
DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-worker-authorization-v2+json"
)
DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-child-terminal-receipt-v2+json"
)

DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA = (
    "cas_harness_v2.diagnostic_stagec_archive_admission.v2"
)
DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-stagec-archive-admission-v2+json"
)
DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA = (
    "cas_harness_v2.diagnostic_stagec_child_output.v2"
)
DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-stagec-child-output-v2+json"
)

DIAGNOSTIC_TERMINAL_STATUSES = (
    "COMPLETED",
    "FAILED",
    "INDETERMINATE",
    "REJECTED",
    "EXPIRED",
)
DIAGNOSTIC_INVOCATION_CERTAINTIES = (
    "EXACTLY_ZERO",
    "EXACTLY_ONE",
    "INDETERMINATE_ZERO_OR_ONE",
)

_RUN_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_ARCHIVE_MANIFEST_ID_RE = re.compile(r"^stagec-local-archive-[0-9a-f]{64}$")

_AUTHORITY = {
    "scope": "STRUCTURE_ONLY",
    "execution_authority": "NOT_GRANTED_BY_CARRIER",
    "authentication": "NOT_PROVIDED",
    "durable_one_use": "EXTERNAL_REQUIRED_NOT_PROVIDED",
    "trusted_time": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "evidence_packet_v2": "FORBIDDEN",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "claim_promotion": "FORBIDDEN",
    "license": "NOT_GRANTED",
    "product": "NOT_AUTHORIZED",
    "disclosure": "HELD",
}

_CONTRACT_BOUNDARY = {
    "state_scope": "PROCESS_LOCAL_EXACT_BYTE_REPLAY",
    "identity_semantic": "PROSPECTIVE_REFERENCES_AND_FIXED_CAPTURE_LITERALS_ONLY",
    "model_file_rehash_at_execution": "NOT_ATTESTED",
    "runtime_authentication": "NOT_PROVIDED",
    "execution": "NOT_PERFORMED",
}

_BINDING_BOUNDARY = {
    "state_scope": "PROCESS_LOCAL_EXACT_BYTE_REPLAY",
    "position": "AFTER_STUDY_REQUEST_BEFORE_EXECUTION",
    "attempt_scope": "ONE_CASE_ONE_ATTEMPT",
    "retry": "FORBIDDEN",
    "replacement": "FORBIDDEN",
    "archive_admission": "FACTORY_ORIGIN_REQUIRED_FOR_COMPLETED_TERMINAL",
    "v1_capture_plan_binding": "V1_CAPTURE_PLAN_ID_ONLY",
    "execution": "NOT_PERFORMED",
}

_AUTHORIZATION_BOUNDARY = {
    "state_scope": "PROCESS_LOCAL_EXACT_BYTE_REPLAY",
    "carrier_semantic": "PROSPECTIVE_DIAGNOSTIC_CHILD_AUTHORIZATION_ENVELOPE",
    "execution_authority": "NOT_GRANTED_BY_CARRIER",
    "durable_consumption": "EXTERNAL_REQUIRED_NOT_PROVIDED",
    "retry": "FORBIDDEN",
    "replacement": "FORBIDDEN",
    "execution": "NOT_PERFORMED",
}

_TERMINAL_BOUNDARY = {
    "state_scope": "PROCESS_LOCAL_EXACT_BYTE_REPLAY",
    "execution_context": "COPIED_CANONIC_BYTES_UNCHANGED_FROM_BINDING_AND_AUTHORIZATION",
    "completed_archive_admission": "FACTORY_ORIGIN_MUST_BE_VALIDATED_EXTERNALLY",
    "partial_artifacts": "QUARANTINED_NEGATIVE_EVIDENCE_ONLY",
    "retry_count": 0,
    "retry": "FORBIDDEN",
    "replacement": "FORBIDDEN",
    "aggregate_outcome_access": "SEPARATE_COORDINATOR_REQUIRED",
}

_ARCHIVE_ADMISSION_DOCUMENT_BOUNDARY = {
    "serialized_replay": "STRUCTURAL_BINDING_ONLY",
    "factory_origin": "EXTERNAL_REQUIRED_NOT_PROVIDED_BY_SERIALIZED_BYTES",
    "local_archive_replay": "EXTERNAL_REQUIRED_NOT_PROVIDED_BY_SERIALIZED_BYTES",
    "execution_authority": "NOT_GRANTED",
}

_CHILD_OUTPUT_DOCUMENT_BOUNDARY = {
    "serialized_replay": "STRUCTURAL_BINDING_ONLY",
    "live_archive_admission": "EXTERNAL_REQUIRED_NOT_PROVIDED_BY_SERIALIZED_BYTES",
    "scientific_assessment": "NOT_PERFORMED",
    "execution_authority": "NOT_GRANTED",
}

_RETRY_POLICY = {
    "maximum_attempts": 1,
    "attempt_ordinal": 1,
    "retry_count": 0,
    "retry": "FORBIDDEN",
    "replacement": "FORBIDDEN",
    "durable_enforcement": "EXTERNAL_REQUIRED_NOT_PROVIDED",
}

_STAGEC_MODEL = {
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "tokenizer_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
    "model_weights_sha256": "FDF756FA7FCBE7404D5C60E26BFF1A0C8B8AA1F72CED49E7DD0210FE288FB7FE",
    "model_weights_byte_length": 988097824,
    "model_config_sha256": "18E18AFCACCAFADE98DAF13A54092927904649E1DD4EBA8299AB717D5D94FF45",
    "model_config_byte_length": 659,
    "tokenizer_json_sha256": "C0382117EA329CDF097041132F6D735924B697924D6F6FC3945713E96CE87539",
    "tokenizer_json_byte_length": 7031645,
    "tokenizer_config_sha256": "5B5D4F65D0ACD3B2D56A35B56D374A36CBC1C8FA5CF3B3FEBBBFABF22F359583",
    "tokenizer_config_byte_length": 7305,
}

_STAGEC_CAPTURE = {
    "capture_request_schema": "cas_harness.stagec.capture_request.v1",
    "capture_request_media_type": STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    "authorization_projection_schema": "cas_harness.stagec.authorization_projection.v1",
    "authorization_projection_media_type": "application/vnd.cas-harness.stagec-authorization-projection+json",
    "capture_index_schema": "cas_harness.stagec.capture_index.v1",
    "capture_index_media_type": "application/vnd.cas-harness.stagec-capture-index+json",
    "raw_array_media_type": "application/vnd.cas-harness.ndarray.raw",
    "target_layer": 18,
    "target_module_path": "model.layers[18].mlp.down_proj",
    "wrong_layer": 0,
    "wrong_layer_module_path": "model.layers[0].mlp.down_proj",
    "vector_width": 4864,
    "maximum_sequence_length": 32768,
    "direct_capture_model_call_count": 1,
    "direct_generate_api_call_count": 0,
}

_ARCHIVE_MEMBER_ROLES = (
    "request_artifact",
    "authorization_projection_artifact",
    "capture_index_artifact",
    "input_ids",
    "attention_mask",
    "target_vector",
    "wrong_layer_vector",
)

_ARTIFACT_ID_KEYS = {
    "authorization",
    "authorization_projection",
    "capture_index",
    "input_ids",
    "attention_mask",
    "target_vector",
    "wrong_layer_vector",
    "archive_admission",
    "child_output",
    "terminal_receipt",
}


@dataclass(frozen=True, slots=True)
class DiagnosticStageCExecutionContractArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    contract_id: str
    created_at: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.contract_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticChildExecutionBindingArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    binding_id: str
    created_at: str
    study_id: str
    case_id: str
    case_execution_ordinal: int
    attempt_ordinal: int
    run_nonce_b64url: str
    execution_context_sha256: str
    execution_context_byte_length: int
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.binding_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_CHILD_EXECUTION_BINDING_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticWorkerAuthorizationV2Artifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    authorization_id: str
    issued_at: str
    not_before: str
    expires_at: str
    study_id: str
    case_id: str
    case_execution_ordinal: int
    attempt_ordinal: int
    run_nonce_b64url: str
    execution_context_sha256: str
    execution_context_byte_length: int
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.authorization_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DiagnosticChildTerminalReceiptV2Artifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    receipt_id: str
    terminal_status: str
    invocation_certainty: str
    terminal_at: str
    worker_started_at: str | None
    execution_context_sha256: str
    execution_context_byte_length: int
    produced_artifact_refs: tuple[ArtifactRef, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.receipt_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE,
        )

    @property
    def authorization_sha256(self) -> str | None:
        value = self.payload["authorization"]
        return None if value is None else value["sha256"]

    @property
    def outcome_artifact_refs(self) -> tuple[ArtifactRef, ...]:
        return self.produced_artifact_refs


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _canonical_object(
    raw: bytes | bytearray | memoryview,
    path: str,
) -> tuple[bytes, dict[str, Any]]:
    snapshot, value = load_json_object(raw)
    if snapshot != canonical_json_bytes(value):
        raise SchemaValidationError(f"{path} must use exact canonical JSON bytes")
    return snapshot, value


def _base_ref(base: DiagnosticPreregistrationArtifact) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=base.preregistration_id,
        sha256=base.sha256,
        byte_length=base.byte_length,
        media_type=DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE,
    )


def _require_chain(
    chain: DiagnosticPreregistrationChain,
    *,
    require_pre_outcome: bool,
) -> DiagnosticPreregistrationArtifact:
    if type(chain) is not DiagnosticPreregistrationChain:
        raise SchemaValidationError("chain must be an exact DiagnosticPreregistrationChain")
    chain.assert_integrity()
    if require_pre_outcome and chain.outcome_access is not None:
        raise SchemaValidationError("diagnostic execution carriers require a pre-outcome chain")
    return chain.base


def _replay_plan(
    plan: DiagnosticStudyPlanArtifact,
    *,
    chain: DiagnosticPreregistrationChain,
) -> DiagnosticStudyPlanArtifact:
    if type(plan) is not DiagnosticStudyPlanArtifact:
        raise SchemaValidationError("plan must be an exact DiagnosticStudyPlanArtifact")
    replayed = load_diagnostic_study_plan(
        plan.raw_bytes,
        chain=chain,
        inventory=plan.inventory,
    )
    if replayed != plan:
        raise SchemaValidationError("diagnostic Study plan differs from fresh exact-byte replay")
    return replayed


def _replay_study_request(
    request: DiagnosticStudyRequestArtifact,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
) -> DiagnosticStudyRequestArtifact:
    if type(request) is not DiagnosticStudyRequestArtifact:
        raise SchemaValidationError("study_request must be an exact DiagnosticStudyRequestArtifact")
    replayed = load_diagnostic_study_request(
        request.raw_bytes,
        chain=chain,
        plan=plan,
    )
    if replayed != request:
        raise SchemaValidationError("diagnostic Study request differs from fresh exact-byte replay")
    return replayed


def _capture_request_for_case(
    plan: DiagnosticStudyPlanArtifact,
    case_id: str,
) -> StageCCaptureRequestArtifact:
    matches = tuple(
        request
        for request in plan.inventory.capture_requests
        if request.case_id == case_id
    )
    if len(matches) != 1:
        raise SchemaValidationError("case_id must resolve exactly one Stage C capture request")
    request = matches[0]
    replayed = load_stagec_capture_request(request.artifact_ref, request.raw_bytes)
    if replayed != request:
        raise SchemaValidationError("Stage C capture request differs from fresh exact-byte replay")
    return replayed


def _require_context_copy(
    value: Any,
    *,
    expected: Mapping[str, Any],
    expected_sha256: str,
    expected_byte_length: int,
    path: str,
) -> None:
    obj = expect_object(value, path)
    context_bytes = canonical_json_bytes(obj)
    if (
        obj != thaw_json(expected)
        or sha256_bytes(context_bytes) != expected_sha256
        or len(context_bytes) != expected_byte_length
    ):
        raise SchemaValidationError(f"{path} is not the unchanged canonical execution context")


def _require_absolute_archive_root(value: Any) -> str:
    result = expect_string(value, "archive_root", maximum=4096)
    if result != result.strip() or "\x00" in result or "\\" in result:
        raise SchemaValidationError("archive_root must be a normalized absolute path")
    if not (result.startswith("/") or _WINDOWS_ABSOLUTE_PATH_RE.match(result)):
        raise SchemaValidationError("archive_root must be an absolute path")
    if result.endswith("/"):
        raise SchemaValidationError("archive_root must not retain a trailing separator")
    normalized = result
    if normalized in {"", "/"} or re.fullmatch(r"[A-Za-z]:", normalized):
        raise SchemaValidationError("archive_root cannot be a filesystem root")
    parts = normalized.split("/")
    for index, part in enumerate(parts):
        if part in {"", ".", ".."} and not (index == 0 and part == ""):
            raise SchemaValidationError("archive_root contains a noncanonical path component")
        if part.endswith((".", " ")):
            raise SchemaValidationError(
                "archive_root components cannot end with a dot or space"
            )
        if ":" in part and not (
            index == 0 and re.fullmatch(r"[A-Za-z]:", part) is not None
        ):
            raise SchemaValidationError(
                "archive_root contains a colon outside the Windows drive prefix"
            )
    return result


def _nonce_value(value: bytes | bytearray | memoryview) -> tuple[str, str]:
    if type(value) not in (bytes, bytearray, memoryview):
        raise SchemaValidationError("run_nonce must be exact bytes-like input")
    snapshot = bytes(value)
    if len(snapshot) != 32:
        raise SchemaValidationError("run_nonce must contain exactly 32 bytes")
    encoded = base64.urlsafe_b64encode(snapshot).decode("ascii").rstrip("=")
    return encoded, sha256_bytes(snapshot)


def _validate_nonce_binding(value: Any, path: str) -> tuple[str, str]:
    obj = expect_object(value, path)
    expect_keys(
        obj,
        required={"value_b64url", "sha256", "profile", "structural_assurance"},
        path=path,
    )
    encoded = expect_string(obj["value_b64url"], f"{path}.value_b64url", maximum=43)
    if not _RUN_NONCE_RE.fullmatch(encoded):
        raise SchemaValidationError(f"{path}.value_b64url must be unpadded base64url")
    try:
        decoded = base64.b64decode(encoded + "=", altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise SchemaValidationError(f"{path}.value_b64url is invalid") from exc
    if len(decoded) != 32 or base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != encoded:
        raise SchemaValidationError(f"{path}.value_b64url must canonically encode 32 bytes")
    digest = expect_sha256(obj["sha256"], f"{path}.sha256")
    if digest != sha256_bytes(decoded):
        raise SchemaValidationError(f"{path}.sha256 does not bind the nonce bytes")
    if obj["profile"] != "CALLER_DECLARED_CSPRNG_256_BIT":
        raise SchemaValidationError(f"{path}.profile drifted")
    if obj["structural_assurance"] != "LENGTH_ENCODING_AND_DIGEST_ONLY":
        raise SchemaValidationError(f"{path}.structural_assurance drifted")
    return encoded, digest


def _unique_ref_closure(
    references: Sequence[ArtifactRef],
    path: str,
) -> tuple[ArtifactRef, ...]:
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], str] = {}
    ordered: list[ArtifactRef] = []
    for index, reference in enumerate(references):
        if type(reference) is not ArtifactRef:
            raise SchemaValidationError(f"{path}[{index}] must be an exact ArtifactRef")
        prior = by_id.get(reference.artifact_id)
        if prior is not None:
            if prior != reference:
                raise SchemaValidationError(f"{path} reuses one artifact_id for different bytes")
            continue
        identity = (reference.sha256, reference.byte_length)
        prior_id = by_content.get(identity)
        if prior_id is not None and prior_id != reference.artifact_id:
            raise SchemaValidationError(
                f"{path} clones one exact content identity under different artifact IDs"
            )
        by_id[reference.artifact_id] = reference
        by_content[identity] = reference.artifact_id
        ordered.append(reference)
    return tuple(ordered)


def _contract_value(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    contract_id: str,
    created_at: str,
) -> tuple[dict[str, Any], tuple[ArtifactRef, ...]]:
    base = _require_chain(chain, require_pre_outcome=True)
    replayed_plan = _replay_plan(plan, chain=chain)
    contract_id = expect_machine_id(contract_id, "contract_id")
    created_at = expect_timestamp(created_at, "created_at")
    if _time(created_at) <= _time(replayed_plan.created_at):
        raise SchemaValidationError("execution contract must follow the exact Study plan")
    if _time(created_at) >= _time(replayed_plan.execution_window_start):
        raise SchemaValidationError("execution contract must be frozen before the execution window")
    refs = _unique_ref_closure(
        (replayed_plan.artifact_ref, *replayed_plan.artifact_refs),
        "execution_contract.refs",
    )
    if contract_id in {item.artifact_id for item in refs}:
        raise SchemaValidationError("contract_id collides with a plan predecessor")
    value = {
        "schema_version": DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "created_at": created_at,
        "diagnostic_study_plan": _artifact_ref_value(replayed_plan.artifact_ref),
        "diagnostic_preregistration_binding": thaw_json(
            replayed_plan.payload["diagnostic_preregistration_binding"]
        ),
        "execution_identity_artifacts": [
            _artifact_ref_value(reference)
            for reference in replayed_plan.execution_identity_artifacts
        ],
        "model_contract": dict(_STAGEC_MODEL),
        "runtime_contract": {
            "identity_binding": "EXACT_ORDERED_PLAN_EXECUTION_IDENTITY_ARTIFACTS",
            "worker_profile": "STAGEC_QWEN_W0_SINGLE_PREFILL",
            "model_loader": "EXACT_SINGLETON_LOADER_CARRIER_REQUIRED",
            "network_during_execution": "NOT_ATTESTED",
            "device_and_dtype": "LOADER_BOUND_RUNTIME_OBSERVATION_REQUIRED",
        },
        "capture_contract": dict(_STAGEC_CAPTURE),
        "boundary": dict(_CONTRACT_BOUNDARY),
        "authority": dict(_AUTHORITY),
        "governance": thaw_json(base.payload["governance"]),
    }
    return value, refs


def load_diagnostic_stagec_execution_contract(
    raw: bytes | bytearray | memoryview,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
) -> DiagnosticStageCExecutionContractArtifact:
    """Strict-load one fixed Stage C model/runtime/capture contract."""

    snapshot, obj = _canonical_object(raw, "diagnostic Stage C execution contract")
    expect_keys(
        obj,
        required={
            "schema_version",
            "contract_id",
            "created_at",
            "diagnostic_study_plan",
            "diagnostic_preregistration_binding",
            "execution_identity_artifacts",
            "model_contract",
            "runtime_contract",
            "capture_contract",
            "boundary",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_SCHEMA:
        raise SchemaValidationError("diagnostic Stage C execution-contract schema drifted")
    contract_id = expect_machine_id(obj["contract_id"], "$.contract_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    expected, refs = _contract_value(
        chain=chain,
        plan=plan,
        contract_id=contract_id,
        created_at=created_at,
    )
    if obj != expected:
        raise SchemaValidationError(
            "diagnostic Stage C execution contract does not exactly replay its plan and fixed literals"
        )
    return DiagnosticStageCExecutionContractArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        contract_id=contract_id,
        created_at=created_at,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def build_diagnostic_stagec_execution_contract(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    contract_id: str,
    created_at: str,
) -> DiagnosticStageCExecutionContractArtifact:
    value, _ = _contract_value(
        chain=chain,
        plan=plan,
        contract_id=contract_id,
        created_at=created_at,
    )
    return load_diagnostic_stagec_execution_contract(
        canonical_json_bytes(value),
        chain=chain,
        plan=plan,
    )


def _replay_contract(
    contract: DiagnosticStageCExecutionContractArtifact,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
) -> DiagnosticStageCExecutionContractArtifact:
    if type(contract) is not DiagnosticStageCExecutionContractArtifact:
        raise SchemaValidationError(
            "execution_contract must be an exact DiagnosticStageCExecutionContractArtifact"
        )
    replayed = load_diagnostic_stagec_execution_contract(
        contract.raw_bytes,
        chain=chain,
        plan=plan,
    )
    if replayed != contract:
        raise SchemaValidationError("execution contract differs from fresh exact-byte replay")
    return replayed


def _artifact_ids(value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != _ARTIFACT_ID_KEYS:
        raise SchemaValidationError(
            f"artifact_ids must contain exactly {sorted(_ARTIFACT_ID_KEYS)!r}"
        )
    result = {
        key: expect_machine_id(item, f"artifact_ids.{key}")
        for key, item in value.items()
    }
    if len(set(result.values())) != len(result):
        raise SchemaValidationError("artifact_ids must be globally unique")
    return result


def _authorization_projection_ref(
    *,
    artifact_id: str,
    plan: DiagnosticStudyPlanArtifact,
    capture_request: StageCCaptureRequestArtifact,
) -> ArtifactRef:
    raw = canonical_json_bytes(
        {
            "schema_version": "cas_harness.stagec.authorization_projection.v1",
            "scope": "STRUCTURE_ONLY",
            "authority_status": "NON_AUTHORITY / DOES_NOT_AUTHORIZE_MODEL_EXECUTION",
            "request_sha256": capture_request.sha256,
            "plan_id": plan.plan_id,
            "study_id": capture_request.study_id,
            "case_id": capture_request.case_id,
            "invocation_id": capture_request.invocation_id,
        }
    )
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=_STAGEC_CAPTURE["authorization_projection_media_type"],
    )


def _binding_value(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding_id: str,
    created_at: str,
    run_nonce_b64url: str,
    run_nonce_sha256: str,
    assigned_worker_id: str,
    archive_root: str,
    artifact_ids: Mapping[str, str],
) -> tuple[
    dict[str, Any],
    Mapping[str, Any],
    str,
    int,
    tuple[ArtifactRef, ...],
    int,
]:
    base = _require_chain(chain, require_pre_outcome=True)
    replayed_plan = _replay_plan(plan, chain=chain)
    replayed_request = _replay_study_request(
        study_request,
        chain=chain,
        plan=replayed_plan,
    )
    replayed_contract = _replay_contract(
        execution_contract,
        chain=chain,
        plan=replayed_plan,
    )
    capture_request = _capture_request_for_case(replayed_plan, replayed_request.case_id)
    if replayed_request.capture_request != capture_request.artifact_ref:
        raise SchemaValidationError("Study request binds a different Stage C capture request")
    matches = tuple(
        case for case in replayed_plan.cases if case.case_id == replayed_request.case_id
    )
    if len(matches) != 1:
        raise SchemaValidationError("Study request case is not unique in the plan")
    case = matches[0]
    if case.execution_ordinal != replayed_request.execution_ordinal:
        raise SchemaValidationError("Study request execution ordinal drifted from the plan")

    binding_id = expect_machine_id(binding_id, "binding_id")
    created_at = expect_timestamp(created_at, "created_at")
    if _time(created_at) <= max(
        _time(replayed_request.created_at),
        _time(replayed_contract.created_at),
    ):
        raise SchemaValidationError("child execution binding must follow request and contract")
    if _time(created_at) >= _time(replayed_plan.execution_window_start):
        raise SchemaValidationError("child execution binding must precede execution window")
    assigned_worker_id = expect_machine_id(assigned_worker_id, "assigned_worker_id")
    archive_root = _require_absolute_archive_root(archive_root)
    ids = _artifact_ids(artifact_ids)
    _validate_nonce_binding(
        {
            "value_b64url": run_nonce_b64url,
            "sha256": run_nonce_sha256,
            "profile": "CALLER_DECLARED_CSPRNG_256_BIT",
            "structural_assurance": "LENGTH_ENCODING_AND_DIGEST_ONLY",
        },
        "run_nonce",
    )

    refs = _unique_ref_closure(
        (
            replayed_contract.artifact_ref,
            replayed_plan.artifact_ref,
            replayed_request.artifact_ref,
            capture_request.artifact_ref,
            *replayed_plan.artifact_refs,
        ),
        "child_binding.refs",
    )
    reserved_ids = {
        binding_id,
        *ids.values(),
    }
    if len(reserved_ids) != len(ids) + 1:
        raise SchemaValidationError("binding_id collides with a prospective child artifact")
    collisions = reserved_ids.intersection(item.artifact_id for item in refs)
    if collisions:
        raise SchemaValidationError(
            f"prospective child artifact IDs collide with predecessors: {sorted(collisions)!r}"
        )

    auth_projection = _authorization_projection_ref(
        artifact_id=ids["authorization_projection"],
        plan=replayed_plan,
        capture_request=capture_request,
    )
    expected_member_ids = {
        "request_artifact": capture_request.artifact_ref.artifact_id,
        "authorization_projection_artifact": ids["authorization_projection"],
        "capture_index_artifact": ids["capture_index"],
        "input_ids": ids["input_ids"],
        "attention_mask": ids["attention_mask"],
        "target_vector": ids["target_vector"],
        "wrong_layer_vector": ids["wrong_layer_vector"],
    }
    case_binding = {
        "study_id": replayed_plan.study_id,
        "case_id": case.case_id,
        "case_execution_ordinal": case.execution_ordinal,
        "split_id": case.split_id,
        "base_intent_group_id": case.base_intent_group_id,
        "frozen_variant": case.frozen_variant,
        "frozen_label": case.frozen_label,
        "invocation_id": case.invocation_id,
    }
    attempt_subject_sha256 = canonical_sha256(
        {
            "domain": "cas_harness_v2.diagnostic_child_attempt_subject.v2",
            "pre_outcome_chain_sha256": replayed_plan.pre_outcome_chain_sha256,
            "study_plan": _artifact_ref_value(replayed_plan.artifact_ref),
            "study_request": _artifact_ref_value(replayed_request.artifact_ref),
            "case_execution_ordinal": case.execution_ordinal,
        }
    )
    context = {
        "diagnostic_preregistration_binding": thaw_json(
            replayed_plan.payload["diagnostic_preregistration_binding"]
        ),
        "study_binding": {
            "diagnostic_study_plan": _artifact_ref_value(replayed_plan.artifact_ref),
            "diagnostic_study_request": _artifact_ref_value(replayed_request.artifact_ref),
            "stagec_capture_request": _artifact_ref_value(capture_request.artifact_ref),
        },
        "case_binding": case_binding,
        "execution_contract": _artifact_ref_value(replayed_contract.artifact_ref),
        "execution_identity_artifacts": [
            _artifact_ref_value(reference)
            for reference in replayed_plan.execution_identity_artifacts
        ],
        "model_runtime_capture_contract": {
            "model_contract": thaw_json(replayed_contract.payload["model_contract"]),
            "runtime_contract": thaw_json(replayed_contract.payload["runtime_contract"]),
            "capture_contract": thaw_json(replayed_contract.payload["capture_contract"]),
        },
        "attempt_binding": {
            "attempt_subject_sha256": attempt_subject_sha256,
            "run_nonce": {
                "value_b64url": run_nonce_b64url,
                "sha256": run_nonce_sha256,
                "profile": "CALLER_DECLARED_CSPRNG_256_BIT",
                "structural_assurance": "LENGTH_ENCODING_AND_DIGEST_ONLY",
            },
            "retry_policy": dict(_RETRY_POLICY),
        },
        "worker_assignment": {
            "assigned_worker_id": assigned_worker_id,
            "assignment_semantic": "PROSPECTIVE_STRUCTURAL_BINDING_ONLY",
        },
        "execution_window": thaw_json(replayed_plan.payload["execution_window"]),
        "artifact_expectations": {
            "authorization": {
                "artifact_id": ids["authorization"],
                "schema_version": DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
                "media_type": DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
            },
            "capture": {
                "authorization_projection": _artifact_ref_value(auth_projection),
                "capture_index": {
                    "artifact_id": ids["capture_index"],
                    "schema_version": _STAGEC_CAPTURE["capture_index_schema"],
                    "media_type": _STAGEC_CAPTURE["capture_index_media_type"],
                },
                "raw_arrays": {
                    "input_ids": {"artifact_id": ids["input_ids"], "dtype": "<i8", "role": "input_ids"},
                    "attention_mask": {"artifact_id": ids["attention_mask"], "dtype": "<i8", "role": "attention_mask"},
                    "target_vector": {"artifact_id": ids["target_vector"], "dtype": "<f4", "role": "target_final_token_activation", "layer_index": 18, "module_path": _STAGEC_CAPTURE["target_module_path"]},
                    "wrong_layer_vector": {"artifact_id": ids["wrong_layer_vector"], "dtype": "<f4", "role": "wrong_layer_final_token_activation", "layer_index": 0, "module_path": _STAGEC_CAPTURE["wrong_layer_module_path"]},
                },
            },
            "archive": {
                "schema_version": "cas_harness.stagec.local_capture_archive.v1",
                "media_type": "application/vnd.cas-harness.stagec-local-capture-archive+json",
                "manifest_name": "stagec-local-capture-archive.v1.json",
                "manifest_id_derivation": "stagec-local-archive- + lowercase_sha256(canonical_capture_index_ref_payload)",
                "content_path_derivation": "objects/sha256/<first-2-lowercase-digest>/<remaining-62>",
                "absolute_root": archive_root,
                "ordered_member_roles": list(_ARCHIVE_MEMBER_ROLES),
                "expected_member_artifact_ids": expected_member_ids,
                "admission": {
                    "artifact_id": ids["archive_admission"],
                    "schema_version": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
                    "media_type": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
                    "admission_domain": "FACTORY_ONLY_FRESH_WORKER_LOCAL_ARCHIVE_REPLAY_V2",
                },
            },
            "output": {
                "artifact_id": ids["child_output"],
                "output_name": "diagnostic_stagec_child_output",
                "schema_version": DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
                "media_type": DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE,
            },
            "terminal_receipt": {
                "artifact_id": ids["terminal_receipt"],
                "schema_version": DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA,
                "media_type": DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE,
            },
        },
    }
    context_bytes = canonical_json_bytes(context)
    context_sha256 = sha256_bytes(context_bytes)
    value = {
        "schema_version": DIAGNOSTIC_CHILD_EXECUTION_BINDING_SCHEMA,
        "binding_id": binding_id,
        "created_at": created_at,
        "execution_context": context,
        "execution_context_sha256": context_sha256,
        "execution_context_byte_length": len(context_bytes),
        "boundary": dict(_BINDING_BOUNDARY),
        "authority": dict(_AUTHORITY),
        "governance": thaw_json(base.payload["governance"]),
    }
    return value, freeze_json(context), context_sha256, len(context_bytes), refs, case.execution_ordinal


def load_diagnostic_child_execution_binding(
    raw: bytes | bytearray | memoryview,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
) -> DiagnosticChildExecutionBindingArtifact:
    snapshot, obj = _canonical_object(raw, "diagnostic child execution binding")
    expect_keys(
        obj,
        required={
            "schema_version",
            "binding_id",
            "created_at",
            "execution_context",
            "execution_context_sha256",
            "execution_context_byte_length",
            "boundary",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_CHILD_EXECUTION_BINDING_SCHEMA:
        raise SchemaValidationError("diagnostic child execution-binding schema drifted")
    binding_id = expect_machine_id(obj["binding_id"], "$.binding_id")
    created_at = expect_timestamp(obj["created_at"], "$.created_at")
    context = expect_object(obj["execution_context"], "$.execution_context")
    attempt = expect_object(context.get("attempt_binding"), "$.execution_context.attempt_binding")
    nonce, nonce_sha = _validate_nonce_binding(
        attempt.get("run_nonce"),
        "$.execution_context.attempt_binding.run_nonce",
    )
    worker = expect_object(context.get("worker_assignment"), "$.execution_context.worker_assignment")
    expectations = expect_object(context.get("artifact_expectations"), "$.execution_context.artifact_expectations")
    archive = expect_object(expectations.get("archive"), "$.execution_context.artifact_expectations.archive")
    capture = expect_object(expectations.get("capture"), "$.execution_context.artifact_expectations.capture")
    arrays = expect_object(capture.get("raw_arrays"), "$.execution_context.artifact_expectations.capture.raw_arrays")
    ids = {
        "authorization": expect_object(expectations.get("authorization"), "$.execution_context.artifact_expectations.authorization")["artifact_id"],
        "authorization_projection": expect_object(capture.get("authorization_projection"), "$.execution_context.artifact_expectations.capture.authorization_projection")["artifact_id"],
        "capture_index": expect_object(capture.get("capture_index"), "$.execution_context.artifact_expectations.capture.capture_index")["artifact_id"],
        "input_ids": expect_object(arrays.get("input_ids"), "$.execution_context.artifact_expectations.capture.raw_arrays.input_ids")["artifact_id"],
        "attention_mask": expect_object(arrays.get("attention_mask"), "$.execution_context.artifact_expectations.capture.raw_arrays.attention_mask")["artifact_id"],
        "target_vector": expect_object(arrays.get("target_vector"), "$.execution_context.artifact_expectations.capture.raw_arrays.target_vector")["artifact_id"],
        "wrong_layer_vector": expect_object(arrays.get("wrong_layer_vector"), "$.execution_context.artifact_expectations.capture.raw_arrays.wrong_layer_vector")["artifact_id"],
        "archive_admission": expect_object(archive.get("admission"), "$.execution_context.artifact_expectations.archive.admission")["artifact_id"],
        "child_output": expect_object(expectations.get("output"), "$.execution_context.artifact_expectations.output")["artifact_id"],
        "terminal_receipt": expect_object(expectations.get("terminal_receipt"), "$.execution_context.artifact_expectations.terminal_receipt")["artifact_id"],
    }
    expected, frozen_context, context_sha, context_length, refs, ordinal = _binding_value(
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
        binding_id=binding_id,
        created_at=created_at,
        run_nonce_b64url=nonce,
        run_nonce_sha256=nonce_sha,
        assigned_worker_id=worker.get("assigned_worker_id"),
        archive_root=archive.get("absolute_root"),
        artifact_ids=ids,
    )
    if obj != expected:
        raise SchemaValidationError("diagnostic child binding does not exactly replay all inputs")
    return DiagnosticChildExecutionBindingArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        binding_id=binding_id,
        created_at=created_at,
        study_id=study_request.study_id,
        case_id=study_request.case_id,
        case_execution_ordinal=ordinal,
        attempt_ordinal=1,
        run_nonce_b64url=nonce,
        execution_context_sha256=context_sha,
        execution_context_byte_length=context_length,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def build_diagnostic_child_execution_binding(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding_id: str,
    created_at: str,
    run_nonce: bytes | bytearray | memoryview,
    assigned_worker_id: str,
    archive_root: str,
    artifact_ids: Mapping[str, str],
) -> DiagnosticChildExecutionBindingArtifact:
    nonce, nonce_sha = _nonce_value(run_nonce)
    value, _, _, _, _, _ = _binding_value(
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
        binding_id=binding_id,
        created_at=created_at,
        run_nonce_b64url=nonce,
        run_nonce_sha256=nonce_sha,
        assigned_worker_id=assigned_worker_id,
        archive_root=archive_root,
        artifact_ids=artifact_ids,
    )
    return load_diagnostic_child_execution_binding(
        canonical_json_bytes(value),
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
    )


def _replay_binding(
    binding: DiagnosticChildExecutionBindingArtifact,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
) -> DiagnosticChildExecutionBindingArtifact:
    if type(binding) is not DiagnosticChildExecutionBindingArtifact:
        raise SchemaValidationError(
            "binding must be an exact DiagnosticChildExecutionBindingArtifact"
        )
    replayed = load_diagnostic_child_execution_binding(
        binding.raw_bytes,
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
    )
    if replayed != binding:
        raise SchemaValidationError("child binding differs from fresh exact-byte replay")
    return replayed


def _authorization_value(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    issued_at: str,
    expires_at: str,
) -> tuple[dict[str, Any], str, tuple[ArtifactRef, ...]]:
    base = _require_chain(chain, require_pre_outcome=True)
    replayed_plan = _replay_plan(plan, chain=chain)
    replayed_binding = _replay_binding(
        binding,
        chain=chain,
        plan=replayed_plan,
        study_request=study_request,
        execution_contract=execution_contract,
    )
    expectations = replayed_binding.payload["execution_context"]["artifact_expectations"]
    authorization_id = expect_machine_id(
        expectations["authorization"]["artifact_id"],
        "execution_context.artifact_expectations.authorization.artifact_id",
    )
    issued_at = expect_timestamp(issued_at, "issued_at")
    expires_at = expect_timestamp(expires_at, "expires_at")
    not_before = replayed_plan.execution_window_start
    if _time(issued_at) <= _time(replayed_binding.created_at):
        raise SchemaValidationError("authorization issuance must follow the child binding")
    if _time(issued_at) >= _time(expires_at):
        raise SchemaValidationError("authorization expiry must follow issuance")
    if _time(expires_at) > _time(replayed_plan.execution_window_end):
        raise SchemaValidationError("authorization cannot extend beyond the Study execution window")
    if _time(expires_at) <= _time(not_before):
        raise SchemaValidationError("authorization must cover some part of the execution window")
    context = replayed_binding.payload["execution_context"]
    value = {
        "schema_version": DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
        "authorization_id": authorization_id,
        "issued_at": issued_at,
        "not_before": not_before,
        "expires_at": expires_at,
        "child_execution_binding": _artifact_ref_value(replayed_binding.artifact_ref),
        "execution_context": thaw_json(context),
        "execution_context_sha256": replayed_binding.execution_context_sha256,
        "execution_context_byte_length": replayed_binding.execution_context_byte_length,
        "boundary": dict(_AUTHORIZATION_BOUNDARY),
        "authority": dict(_AUTHORITY),
        "governance": thaw_json(base.payload["governance"]),
    }
    refs = _unique_ref_closure(
        (replayed_binding.artifact_ref, *replayed_binding.artifact_refs),
        "diagnostic_authorization.refs",
    )
    if authorization_id in {item.artifact_id for item in refs}:
        raise SchemaValidationError("authorization_id collides with a predecessor")
    return value, authorization_id, refs


def load_diagnostic_worker_authorization_v2(
    raw: bytes | bytearray | memoryview,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
) -> DiagnosticWorkerAuthorizationV2Artifact:
    """Strict-load the distinct non-authoritative diagnostic v2 envelope."""

    snapshot, obj = _canonical_object(raw, "diagnostic worker authorization v2")
    expect_keys(
        obj,
        required={
            "schema_version",
            "authorization_id",
            "issued_at",
            "not_before",
            "expires_at",
            "child_execution_binding",
            "execution_context",
            "execution_context_sha256",
            "execution_context_byte_length",
            "boundary",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA:
        raise SchemaValidationError("diagnostic worker authorization-v2 schema drifted")
    authorization_id = expect_machine_id(obj["authorization_id"], "$.authorization_id")
    issued_at = expect_timestamp(obj["issued_at"], "$.issued_at")
    not_before = expect_timestamp(obj["not_before"], "$.not_before")
    expires_at = expect_timestamp(obj["expires_at"], "$.expires_at")
    expected, expected_id, refs = _authorization_value(
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
        binding=binding,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    if authorization_id != expected_id or not_before != plan.execution_window_start:
        raise SchemaValidationError("diagnostic authorization identity/window drifted")
    if obj != expected:
        raise SchemaValidationError("diagnostic authorization does not exactly replay its child binding")
    supplied_binding = parse_artifact_ref(
        obj["child_execution_binding"], "$.child_execution_binding"
    )
    if supplied_binding != binding.artifact_ref or not supplied_binding.verify_bytes(binding.raw_bytes):
        raise SchemaValidationError("authorization does not bind exact child-binding bytes")
    context_sha = expect_sha256(
        obj["execution_context_sha256"], "$.execution_context_sha256"
    )
    context_length = expect_int(
        obj["execution_context_byte_length"],
        "$.execution_context_byte_length",
        minimum=1,
    )
    _require_context_copy(
        obj["execution_context"],
        expected=binding.payload["execution_context"],
        expected_sha256=context_sha,
        expected_byte_length=context_length,
        path="$.execution_context",
    )
    if (
        context_sha != binding.execution_context_sha256
        or context_length != binding.execution_context_byte_length
    ):
        raise SchemaValidationError("authorization context identity differs from binding")
    nonce, _ = _validate_nonce_binding(
        obj["execution_context"]["attempt_binding"]["run_nonce"],
        "$.execution_context.attempt_binding.run_nonce",
    )
    return DiagnosticWorkerAuthorizationV2Artifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        authorization_id=authorization_id,
        issued_at=issued_at,
        not_before=not_before,
        expires_at=expires_at,
        study_id=binding.study_id,
        case_id=binding.case_id,
        case_execution_ordinal=binding.case_execution_ordinal,
        attempt_ordinal=1,
        run_nonce_b64url=nonce,
        execution_context_sha256=context_sha,
        execution_context_byte_length=context_length,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def build_diagnostic_worker_authorization_v2(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    issued_at: str,
    expires_at: str,
) -> DiagnosticWorkerAuthorizationV2Artifact:
    value, _, _ = _authorization_value(
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
        binding=binding,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    return load_diagnostic_worker_authorization_v2(
        canonical_json_bytes(value),
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
        binding=binding,
    )


def _replay_authorization(
    authorization: DiagnosticWorkerAuthorizationV2Artifact,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
) -> DiagnosticWorkerAuthorizationV2Artifact:
    if type(authorization) is not DiagnosticWorkerAuthorizationV2Artifact:
        raise SchemaValidationError(
            "authorization must be an exact DiagnosticWorkerAuthorizationV2Artifact"
        )
    replayed = load_diagnostic_worker_authorization_v2(
        authorization.raw_bytes,
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
        binding=binding,
    )
    if replayed != authorization:
        raise SchemaValidationError("authorization differs from fresh exact-byte replay")
    return replayed


def _terminal_error(
    value: Any,
    *,
    required: bool,
    status: str,
    phase: str,
) -> dict[str, Any] | None:
    if value is None:
        if required:
            raise SchemaValidationError("adverse terminal status requires an error object")
        return None
    if not required:
        raise SchemaValidationError("COMPLETED terminal status requires error=null")
    obj = expect_object(value, "terminal.error")
    expect_keys(
        obj,
        required={"code", "category", "message", "retryable"},
        path="terminal.error",
    )
    expect_machine_id(obj["code"], "terminal.error.code")
    category = expect_enum(
        obj["category"],
        {
            "INPUT_REJECTED",
            "AUTHORIZATION_REJECTED",
            "EXECUTION_FAILED",
            "RESOURCE_EXHAUSTED",
            "ARCHIVE_FAILED",
            "OUTPUT_FAILED",
            "INTERNAL_ERROR",
            "EXECUTION_INDETERMINATE",
            "AUTHORIZATION_EXPIRED",
        },
        "terminal.error.category",
    )
    expect_string(obj["message"], "terminal.error.message", maximum=4000)
    if expect_bool(obj["retryable"], "terminal.error.retryable"):
        raise SchemaValidationError("diagnostic child errors are never retryable")
    allowed = {
        "REJECTED": {"INPUT_REJECTED", "AUTHORIZATION_REJECTED"},
        "EXPIRED": {"AUTHORIZATION_EXPIRED"},
        "INDETERMINATE": {"EXECUTION_INDETERMINATE"},
        "FAILED": {
            "PRE_MODEL": {"EXECUTION_FAILED", "RESOURCE_EXHAUSTED", "INTERNAL_ERROR"},
            "CAPTURE": {"EXECUTION_FAILED", "RESOURCE_EXHAUSTED", "INTERNAL_ERROR"},
            "ARCHIVE": {"ARCHIVE_FAILED", "RESOURCE_EXHAUSTED", "INTERNAL_ERROR"},
            "OUTPUT": {"OUTPUT_FAILED", "RESOURCE_EXHAUSTED", "INTERNAL_ERROR"},
        }.get(phase, set()),
        "COMPLETED": set(),
    }[status]
    if category not in allowed:
        raise SchemaValidationError("terminal error category disagrees with status/phase")
    return dict(obj)


def _validate_produced_documents(
    rows: tuple[tuple[str, ArtifactRef, bytes], ...],
    *,
    authorization: DiagnosticWorkerAuthorizationV2Artifact,
) -> tuple[ArtifactRef, ...]:
    """Validate the two serialized documents without fabricating live origin."""

    by_role = {role: (reference, raw) for role, reference, raw in rows}
    context = authorization.payload["execution_context"]
    case_binding = thaw_json(context["case_binding"])
    governance = thaw_json(authorization.payload["governance"])
    archive_expectation = context["artifact_expectations"]["archive"]
    archive_row = by_role.get("archive_admission")
    if archive_row is not None:
        admission_ref, admission_raw = archive_row
        _snapshot, admission = _canonical_object(
            admission_raw, "diagnostic Stage C archive-admission document"
        )
        expect_keys(
            admission,
            required={
                "schema_version",
                "admission_id",
                "authorization",
                "execution_context_sha256",
                "case_binding",
                "archive_expectation_sha256",
                "archive_manifest",
                "observation",
                "boundary",
                "authority",
                "governance",
            },
            path="$archive_admission",
        )
        manifest_ref = parse_artifact_ref(
            admission["archive_manifest"], "$archive_admission.archive_manifest"
        )
        expected_admission = {
            "schema_version": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
            "admission_id": admission_ref.artifact_id,
            "authorization": _artifact_ref_value(authorization.artifact_ref),
            "execution_context_sha256": authorization.execution_context_sha256,
            "case_binding": case_binding,
            "archive_expectation_sha256": canonical_sha256(archive_expectation),
            "archive_manifest": _artifact_ref_value(manifest_ref),
            "observation": "SERIALIZED_BINDING_ONLY_FACTORY_ORIGIN_EXTERNAL_REQUIRED",
            "boundary": dict(_ARCHIVE_ADMISSION_DOCUMENT_BOUNDARY),
            "authority": dict(_AUTHORITY),
            "governance": governance,
        }
        if (
            admission != expected_admission
            or manifest_ref.media_type != archive_expectation["media_type"]
            or _ARCHIVE_MANIFEST_ID_RE.fullmatch(manifest_ref.artifact_id) is None
        ):
            raise SchemaValidationError(
                "archive-admission document does not exactly bind authorization/context/manifest"
            )

    output_row = by_role.get("child_output")
    if output_row is not None:
        output_ref, output_raw = output_row
        if archive_row is None:
            raise SchemaValidationError("child output cannot exist without archive admission")
        admission_ref, _ = archive_row
        _snapshot, output = _canonical_object(
            output_raw, "diagnostic Stage C child-output document"
        )
        expect_keys(
            output,
            required={
                "schema_version",
                "output_id",
                "authorization",
                "execution_context_sha256",
                "case_binding",
                "archive_admission",
                "output_role",
                "boundary",
                "authority",
                "governance",
            },
            path="$child_output",
        )
        expected_output = {
            "schema_version": DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
            "output_id": output_ref.artifact_id,
            "authorization": _artifact_ref_value(authorization.artifact_ref),
            "execution_context_sha256": authorization.execution_context_sha256,
            "case_binding": case_binding,
            "archive_admission": _artifact_ref_value(admission_ref),
            "output_role": "DIAGNOSTIC_STAGEC_CHILD_OUTPUT",
            "boundary": dict(_CHILD_OUTPUT_DOCUMENT_BOUNDARY),
            "authority": dict(_AUTHORITY),
            "governance": governance,
        }
        if output != expected_output:
            raise SchemaValidationError(
                "child-output document does not exactly bind authorization/context/admission"
            )
    return () if archive_row is None else (manifest_ref,)


def _produced_artifacts(
    value: Mapping[str, tuple[ArtifactRef, bytes]] | None,
    *,
    authorization: DiagnosticWorkerAuthorizationV2Artifact,
) -> tuple[tuple[tuple[str, ArtifactRef, bytes], ...], tuple[ArtifactRef, ...]]:
    if value is None:
        return (), ()
    if not isinstance(value, Mapping):
        raise SchemaValidationError("produced_artifacts must be a mapping or null")
    unexpected = set(value) - {"archive_admission", "child_output"}
    if unexpected:
        raise SchemaValidationError(f"unknown produced artifact roles: {sorted(unexpected)!r}")
    expectations = authorization.payload["execution_context"]["artifact_expectations"]
    expected = {
        "archive_admission": expectations["archive"]["admission"],
        "child_output": expectations["output"],
    }
    rows: list[tuple[str, ArtifactRef, bytes]] = []
    for role in ("archive_admission", "child_output"):
        if role not in value:
            continue
        pair = value[role]
        if type(pair) is not tuple or len(pair) != 2:
            raise SchemaValidationError(f"produced_artifacts.{role} must be (ArtifactRef, bytes)")
        reference, raw = pair
        if type(reference) is not ArtifactRef or type(raw) is not bytes:
            raise SchemaValidationError(f"produced_artifacts.{role} has invalid exact types")
        if (
            reference.artifact_id != expected[role]["artifact_id"]
            or reference.media_type != expected[role]["media_type"]
            or not reference.verify_bytes(raw)
        ):
            raise SchemaValidationError(f"produced_artifacts.{role} differs from expectation/bytes")
        rows.append((role, reference, raw))
    result = tuple(rows)
    dependent_refs = _validate_produced_documents(result, authorization=authorization)
    return result, dependent_refs


def _validate_terminal_branch(
    *,
    status: str,
    phase: str,
    certainty: str,
    worker_started_at: str | None,
    terminal_at: str,
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None,
    binding: DiagnosticChildExecutionBindingArtifact,
    plan: DiagnosticStudyPlanArtifact,
    produced_roles: tuple[str, ...],
) -> None:
    expect_enum(status, set(DIAGNOSTIC_TERMINAL_STATUSES), "terminal_status")
    expect_enum(certainty, set(DIAGNOSTIC_INVOCATION_CERTAINTIES), "invocation_certainty")
    if authorization is None:
        if not (
            status == "REJECTED"
            and phase == "PRE_AUTHORIZATION"
            and certainty == "EXACTLY_ZERO"
            and worker_started_at is None
            and not produced_roles
            and _time(binding.created_at) < _time(terminal_at)
            and _time(terminal_at) <= _time(plan.execution_window_end)
        ):
            raise SchemaValidationError(
                "authorization=null is allowed only for deterministic preauthorization REJECTED"
            )
        return

    allowed_phase = {
        "COMPLETED": {"COMPLETE"},
        "FAILED": {"PRE_MODEL", "CAPTURE", "ARCHIVE", "OUTPUT"},
        "INDETERMINATE": {"DISPATCH_OR_EXECUTION"},
        "REJECTED": {"PRE_ADMISSION"},
        "EXPIRED": {"AUTHORIZATION_EXPIRED"},
    }[status]
    expect_enum(phase, allowed_phase, "terminal_phase")
    terminal_time = _time(terminal_at)
    issued = _time(authorization.issued_at)
    not_before = _time(authorization.not_before)
    expires = _time(authorization.expires_at)
    if status in {"COMPLETED", "FAILED", "INDETERMINATE"}:
        if worker_started_at is None:
            raise SchemaValidationError(f"{status} requires worker_started_at")
        started = _time(expect_timestamp(worker_started_at, "worker_started_at"))
        if started < max(issued, not_before) or started >= expires:
            raise SchemaValidationError("worker start lies outside authorization/window")
        if terminal_time < started:
            raise SchemaValidationError("terminal_at precedes worker_started_at")
        if status != "INDETERMINATE" and terminal_time > expires:
            raise SchemaValidationError("definitive terminal lies beyond authorization expiry")
    elif worker_started_at is not None:
        raise SchemaValidationError(f"{status} requires worker_started_at=null")

    if status == "COMPLETED":
        if certainty != "EXACTLY_ONE" or produced_roles != ("archive_admission", "child_output"):
            raise SchemaValidationError("COMPLETED requires exactly one invocation and both outputs")
    elif status == "FAILED":
        expected_certainty = "EXACTLY_ZERO" if phase == "PRE_MODEL" else "EXACTLY_ONE"
        if certainty != expected_certainty:
            raise SchemaValidationError("FAILED phase and invocation certainty disagree")
        allowed_outputs = {
            "PRE_MODEL": (),
            "CAPTURE": (),
            "ARCHIVE": (),
            "OUTPUT": ("archive_admission",),
        }[phase]
        if produced_roles != allowed_outputs:
            raise SchemaValidationError("FAILED phase exposes an invalid produced-artifact set")
    elif status == "INDETERMINATE":
        if certainty != "INDETERMINATE_ZERO_OR_ONE":
            raise SchemaValidationError("INDETERMINATE requires unknown zero-or-one certainty")
        if produced_roles not in (
            (),
            ("archive_admission",),
            ("archive_admission", "child_output"),
        ):
            raise SchemaValidationError(
                "INDETERMINATE produced artifacts must form a dependency-valid prefix"
            )
    elif status == "REJECTED":
        if certainty != "EXACTLY_ZERO" or produced_roles or not (issued <= terminal_time < expires):
            raise SchemaValidationError("REJECTED must be pre-send, output-free, and pre-expiry")
    elif status == "EXPIRED":
        if certainty != "EXACTLY_ZERO" or produced_roles or terminal_time < expires:
            raise SchemaValidationError("EXPIRED must be unconsumed, output-free, and at/after expiry")


def _terminal_value(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None,
    terminal_at: str,
    terminal_status: str,
    terminal_phase: str,
    invocation_certainty: str,
    worker_started_at: str | None,
    produced_artifacts: Mapping[str, tuple[ArtifactRef, bytes]] | None,
    error: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], tuple[ArtifactRef, ...], tuple[ArtifactRef, ...]]:
    base = _require_chain(chain, require_pre_outcome=True)
    replayed_binding = _replay_binding(
        binding,
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
    )
    replayed_authorization = (
        None
        if authorization is None
        else _replay_authorization(
            authorization,
            chain=chain,
            plan=plan,
            study_request=study_request,
            execution_contract=execution_contract,
            binding=replayed_binding,
        )
    )
    terminal_at = expect_timestamp(terminal_at, "terminal_at")
    if worker_started_at is not None:
        worker_started_at = expect_timestamp(worker_started_at, "worker_started_at")
    if replayed_authorization is None:
        if produced_artifacts not in (None, {}):
            raise SchemaValidationError("preauthorization rejection cannot bind produced artifacts")
        rows: tuple[tuple[str, ArtifactRef, bytes], ...] = ()
        produced_dependency_refs: tuple[ArtifactRef, ...] = ()
        context = replayed_binding.payload["execution_context"]
        context_sha256 = replayed_binding.execution_context_sha256
        context_byte_length = replayed_binding.execution_context_byte_length
    else:
        rows, produced_dependency_refs = _produced_artifacts(
            produced_artifacts,
            authorization=replayed_authorization,
        )
        context = replayed_authorization.payload["execution_context"]
        context_sha256 = replayed_authorization.execution_context_sha256
        context_byte_length = replayed_authorization.execution_context_byte_length
    roles = tuple(row[0] for row in rows)
    _validate_terminal_branch(
        status=terminal_status,
        phase=terminal_phase,
        certainty=invocation_certainty,
        worker_started_at=worker_started_at,
        terminal_at=terminal_at,
        authorization=replayed_authorization,
        binding=replayed_binding,
        plan=plan,
        produced_roles=roles,
    )
    validated_error = _terminal_error(
        error,
        required=terminal_status != "COMPLETED",
        status=terminal_status,
        phase=terminal_phase,
    )
    receipt_id = expect_machine_id(
        context["artifact_expectations"]["terminal_receipt"]["artifact_id"],
        "terminal_receipt.artifact_id",
    )
    all_roles = ("archive_admission", "child_output")
    missing = tuple(role for role in all_roles if role not in roles)
    quarantined = () if terminal_status == "COMPLETED" else roles
    lifecycle_state = terminal_status
    authorization_disposition = (
        "NOT_CREATED_PREAUTHORIZATION_REJECTION"
        if replayed_authorization is None
        else (
            "CREATED_NOT_CONSUMED_TERMINAL"
            if terminal_status in {"REJECTED", "EXPIRED"}
            else "CREATED_CONSUMED_TERMINAL"
        )
    )
    nonce_disposition = (
        "RESERVED_UNCONSUMED_TERMINALLY_RETIRED"
        if replayed_authorization is None
        else (
            "ISSUED_UNCONSUMED_TERMINALLY_RETIRED"
            if terminal_status in {"REJECTED", "EXPIRED"}
            else "CONSUMED_SINGLE_ATTEMPT_TERMINAL"
        )
    )
    model_invocation_request_count: int | str = {
        "EXACTLY_ZERO": 0,
        "EXACTLY_ONE": 1,
        "INDETERMINATE_ZERO_OR_ONE": "INDETERMINATE_ZERO_OR_ONE",
    }[invocation_certainty]
    row_disposition = (
        "DIAGNOSTIC_CHILD_COMPLETE_AGGREGATE_ONLY"
        if terminal_status == "COMPLETED"
        else "DIAGNOSTIC_CHILD_NEGATIVE_EVIDENCE_QUARANTINED_NO_REPLACEMENT"
    )
    value = {
        "schema_version": DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA,
        "receipt_id": receipt_id,
        "terminal_at": terminal_at,
        "authorization": (
            None
            if replayed_authorization is None
            else _artifact_ref_value(replayed_authorization.artifact_ref)
        ),
        "child_execution_binding": _artifact_ref_value(replayed_binding.artifact_ref),
        "execution_context": thaw_json(context),
        "execution_context_sha256": context_sha256,
        "execution_context_byte_length": context_byte_length,
        "terminal": {
            "status": terminal_status,
            "lifecycle_terminal_state": lifecycle_state,
            "phase": terminal_phase,
            "invocation_certainty": invocation_certainty,
            "model_invocation_request_count": model_invocation_request_count,
            "authorization_disposition": authorization_disposition,
            "nonce_disposition": nonce_disposition,
            "worker_started_at": worker_started_at,
            "produced_artifacts": [
                {"role": role, "artifact": _artifact_ref_value(reference)}
                for role, reference, _raw in rows
            ],
            "archive_manifest": (
                None
                if not produced_dependency_refs
                else _artifact_ref_value(produced_dependency_refs[0])
            ),
            "missing_artifact_roles": list(missing),
            "quarantined_artifact_roles": list(quarantined),
            "error": validated_error,
            "retry_count": 0,
            "retryable": False,
            "replacement": "FORBIDDEN",
            "row_disposition": row_disposition,
            "packet_v2": "FORBIDDEN",
        },
        "boundary": dict(_TERMINAL_BOUNDARY),
        "authority": dict(_AUTHORITY),
        "governance": thaw_json(base.payload["governance"]),
    }
    refs = _unique_ref_closure(
        (
            *((replayed_authorization.artifact_ref,) if replayed_authorization else ()),
            replayed_binding.artifact_ref,
            *(
                replayed_authorization.artifact_refs
                if replayed_authorization is not None
                else replayed_binding.artifact_refs
            ),
            *(row[1] for row in rows),
            *produced_dependency_refs,
        ),
        "diagnostic_terminal.refs",
    )
    if receipt_id in {item.artifact_id for item in refs}:
        raise SchemaValidationError("terminal receipt_id collides with a bound artifact")
    return value, tuple(row[1] for row in rows), refs


def load_diagnostic_child_terminal_receipt_v2(
    raw: bytes | bytearray | memoryview,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None,
    produced_artifact_bodies: Mapping[str, bytes] | None = None,
) -> DiagnosticChildTerminalReceiptV2Artifact:
    """Strict-load one of the five closed terminal branches.

    Bodies for every listed produced artifact are mandatory.  This loader
    verifies their exact refs, but factory provenance for archive admission is
    an external worker-side obligation and is never inferred from these bytes.
    """

    snapshot, obj = _canonical_object(raw, "diagnostic child terminal receipt v2")
    expect_keys(
        obj,
        required={
            "schema_version",
            "receipt_id",
            "terminal_at",
            "authorization",
            "child_execution_binding",
            "execution_context",
            "execution_context_sha256",
            "execution_context_byte_length",
            "terminal",
            "boundary",
            "authority",
            "governance",
        },
        path="$",
    )
    if obj["schema_version"] != DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA:
        raise SchemaValidationError("diagnostic child terminal-v2 schema drifted")
    receipt_id = expect_machine_id(obj["receipt_id"], "$.receipt_id")
    terminal_at = expect_timestamp(obj["terminal_at"], "$.terminal_at")
    terminal = expect_object(obj["terminal"], "$.terminal")
    expect_keys(
        terminal,
        required={
            "status",
            "lifecycle_terminal_state",
            "phase",
            "invocation_certainty",
            "model_invocation_request_count",
            "authorization_disposition",
            "nonce_disposition",
            "worker_started_at",
            "produced_artifacts",
            "archive_manifest",
            "missing_artifact_roles",
            "quarantined_artifact_roles",
            "error",
            "retry_count",
            "retryable",
            "replacement",
            "row_disposition",
            "packet_v2",
        },
        path="$.terminal",
    )
    status = expect_enum(
        terminal["status"], set(DIAGNOSTIC_TERMINAL_STATUSES), "$.terminal.status"
    )
    certainty = expect_enum(
        terminal["invocation_certainty"],
        set(DIAGNOSTIC_INVOCATION_CERTAINTIES),
        "$.terminal.invocation_certainty",
    )
    phase = expect_string(terminal["phase"], "$.terminal.phase", maximum=64)
    worker_started_at = terminal["worker_started_at"]
    if worker_started_at is not None:
        worker_started_at = expect_timestamp(
            worker_started_at, "$.terminal.worker_started_at"
        )
    body_map = {} if produced_artifact_bodies is None else dict(produced_artifact_bodies)
    rows = expect_list(
        terminal["produced_artifacts"],
        "$.terminal.produced_artifacts",
        nonempty=False,
    )
    produced: dict[str, tuple[ArtifactRef, bytes]] = {}
    for index, row in enumerate(rows):
        path = f"$.terminal.produced_artifacts[{index}]"
        item = expect_object(row, path)
        expect_keys(item, required={"role", "artifact"}, path=path)
        role = expect_enum(
            item["role"], {"archive_admission", "child_output"}, f"{path}.role"
        )
        if role in produced:
            raise SchemaValidationError("terminal produced-artifact role is duplicated")
        reference = parse_artifact_ref(item["artifact"], f"{path}.artifact")
        raw_body = body_map.get(role)
        if type(raw_body) is not bytes:
            raise SchemaValidationError(f"exact produced body is required for role {role}")
        produced[role] = (reference, raw_body)
    if set(body_map) != set(produced):
        raise SchemaValidationError("produced_artifact_bodies must exactly match listed roles")
    expected, produced_refs, refs = _terminal_value(
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
        binding=binding,
        authorization=authorization,
        terminal_at=terminal_at,
        terminal_status=status,
        terminal_phase=phase,
        invocation_certainty=certainty,
        worker_started_at=worker_started_at,
        produced_artifacts=produced,
        error=terminal["error"],
    )
    if obj != expected:
        raise SchemaValidationError("terminal receipt does not exactly replay authorization/observations")
    binding_ref = parse_artifact_ref(
        obj["child_execution_binding"], "$.child_execution_binding"
    )
    if authorization is None:
        if obj["authorization"] is not None:
            raise SchemaValidationError(
                "preauthorization terminal must serialize authorization=null"
            )
        context_source = binding
    else:
        auth_ref = parse_artifact_ref(obj["authorization"], "$.authorization")
        if (
            auth_ref != authorization.artifact_ref
            or not auth_ref.verify_bytes(authorization.raw_bytes)
        ):
            raise SchemaValidationError("terminal does not bind exact authorization bytes")
        context_source = authorization
    if binding_ref != binding.artifact_ref or not binding_ref.verify_bytes(binding.raw_bytes):
        raise SchemaValidationError("terminal does not bind exact child-binding bytes")
    context_sha = expect_sha256(
        obj["execution_context_sha256"], "$.execution_context_sha256"
    )
    context_length = expect_int(
        obj["execution_context_byte_length"],
        "$.execution_context_byte_length",
        minimum=1,
    )
    _require_context_copy(
        obj["execution_context"],
        expected=context_source.payload["execution_context"],
        expected_sha256=context_sha,
        expected_byte_length=context_length,
        path="$.execution_context",
    )
    if context_sha != binding.execution_context_sha256 or (
        authorization is not None
        and context_sha != authorization.execution_context_sha256
    ) or context_length != binding.execution_context_byte_length or (
        authorization is not None
        and context_length != authorization.execution_context_byte_length
    ):
        raise SchemaValidationError("terminal context identity differs from binding/authorization")
    return DiagnosticChildTerminalReceiptV2Artifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        receipt_id=receipt_id,
        terminal_status=status,
        invocation_certainty=certainty,
        terminal_at=terminal_at,
        worker_started_at=worker_started_at,
        execution_context_sha256=context_sha,
        execution_context_byte_length=context_length,
        produced_artifact_refs=produced_refs,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def build_diagnostic_child_terminal_receipt_v2(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None,
    terminal_at: str,
    terminal_status: str,
    terminal_phase: str,
    invocation_certainty: str,
    worker_started_at: str | None,
    produced_artifacts: Mapping[str, tuple[ArtifactRef, bytes]] | None,
    error: Mapping[str, Any] | None,
) -> DiagnosticChildTerminalReceiptV2Artifact:
    value, _, _ = _terminal_value(
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
        binding=binding,
        authorization=authorization,
        terminal_at=terminal_at,
        terminal_status=terminal_status,
        terminal_phase=terminal_phase,
        invocation_certainty=invocation_certainty,
        worker_started_at=worker_started_at,
        produced_artifacts=produced_artifacts,
        error=error,
    )
    bodies = {
        role: pair[1]
        for role, pair in ({} if produced_artifacts is None else produced_artifacts).items()
    }
    return load_diagnostic_child_terminal_receipt_v2(
        canonical_json_bytes(value),
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=execution_contract,
        binding=binding,
        authorization=authorization,
        produced_artifact_bodies=bodies,
    )


def replay_diagnostic_execution_family(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None,
    terminal_receipt: DiagnosticChildTerminalReceiptV2Artifact,
    produced_artifact_bodies: Mapping[str, bytes] | None = None,
) -> tuple[
    DiagnosticStageCExecutionContractArtifact,
    DiagnosticChildExecutionBindingArtifact,
    DiagnosticWorkerAuthorizationV2Artifact | None,
    DiagnosticChildTerminalReceiptV2Artifact,
]:
    """Freshly replay the complete acyclic exact-byte family."""

    contract = _replay_contract(execution_contract, chain=chain, plan=plan)
    child = _replay_binding(
        binding,
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=contract,
    )
    auth = (
        None
        if authorization is None
        else _replay_authorization(
            authorization,
            chain=chain,
            plan=plan,
            study_request=study_request,
            execution_contract=contract,
            binding=child,
        )
    )
    if type(terminal_receipt) is not DiagnosticChildTerminalReceiptV2Artifact:
        raise SchemaValidationError(
            "terminal_receipt must be an exact DiagnosticChildTerminalReceiptV2Artifact"
        )
    terminal = load_diagnostic_child_terminal_receipt_v2(
        terminal_receipt.raw_bytes,
        chain=chain,
        plan=plan,
        study_request=study_request,
        execution_contract=contract,
        binding=child,
        authorization=auth,
        produced_artifact_bodies=produced_artifact_bodies,
    )
    if terminal != terminal_receipt:
        raise SchemaValidationError("terminal receipt differs from fresh exact-byte replay")
    return contract, child, auth, terminal


def validate_diagnostic_execution_batch_uniqueness(
    *,
    bindings: Sequence[DiagnosticChildExecutionBindingArtifact],
    authorizations: Sequence[DiagnosticWorkerAuthorizationV2Artifact | None],
    terminal_receipts: Sequence[DiagnosticChildTerminalReceiptV2Artifact],
) -> None:
    """Reject cross-child reuse; dependency replay remains a coordinator duty.

    This helper checks exact carrier self-integrity and batch-level uniqueness.
    A coordinator must first call :func:`replay_diagnostic_execution_family`
    for every row with its exact chain, plan, request, and produced bodies.
    """

    if not (
        type(bindings) in (tuple, list)
        and type(authorizations) in (tuple, list)
        and type(terminal_receipts) in (tuple, list)
        and len(bindings) == len(authorizations) == len(terminal_receipts)
        and len(bindings) > 0
    ):
        raise SchemaValidationError("diagnostic batch carrier sequences must be nonempty/equal")
    identifiers: set[str] = set()
    control_content_identities: set[tuple[str, int]] = set()
    nonces: set[str] = set()
    subjects: set[str] = set()
    case_ordinals: set[tuple[str, int]] = set()
    for index, (binding, authorization, terminal) in enumerate(
        zip(bindings, authorizations, terminal_receipts, strict=True)
    ):
        if type(binding) is not DiagnosticChildExecutionBindingArtifact or (
            authorization is not None
            and type(authorization) is not DiagnosticWorkerAuthorizationV2Artifact
        ) or type(terminal) is not DiagnosticChildTerminalReceiptV2Artifact:
            raise SchemaValidationError(f"diagnostic batch row {index} has a forged carrier type")

        binding_snapshot, binding_obj = _canonical_object(
            binding.raw_bytes, f"batch[{index}].binding"
        )
        terminal_snapshot, terminal_obj = _canonical_object(
            terminal.raw_bytes, f"batch[{index}].terminal"
        )
        for name, carrier, snapshot, obj in (
            ("binding", binding, binding_snapshot, binding_obj),
            ("terminal", terminal, terminal_snapshot, terminal_obj),
        ):
            if (
                sha256_bytes(snapshot) != carrier.sha256
                or len(snapshot) != carrier.byte_length
                or obj != thaw_json(carrier.payload)
            ):
                raise SchemaValidationError(
                    f"diagnostic batch row {index} {name} fails self-integrity"
                )
        authorization_obj: dict[str, Any] | None = None
        if authorization is not None:
            snapshot, authorization_obj = _canonical_object(
                authorization.raw_bytes, f"batch[{index}].authorization"
            )
            if (
                sha256_bytes(snapshot) != authorization.sha256
                or len(snapshot) != authorization.byte_length
                or authorization_obj != thaw_json(authorization.payload)
            ):
                raise SchemaValidationError(
                    f"diagnostic batch row {index} authorization fails self-integrity"
                )

        context = binding.payload["execution_context"]
        context_bytes = canonical_json_bytes(context)
        case = context["case_binding"]
        attempt = context["attempt_binding"]
        if (
            sha256_bytes(context_bytes) != binding.execution_context_sha256
            or len(context_bytes) != binding.execution_context_byte_length
            or binding.binding_id != binding_obj["binding_id"]
            or binding.created_at != binding_obj["created_at"]
            or binding.study_id != case["study_id"]
            or binding.case_id != case["case_id"]
            or binding.case_execution_ordinal != case["case_execution_ordinal"]
            or binding.attempt_ordinal != attempt["retry_policy"]["attempt_ordinal"]
            or binding.run_nonce_b64url != attempt["run_nonce"]["value_b64url"]
            or binding.execution_context_sha256 != terminal.execution_context_sha256
            or binding.execution_context_byte_length
            != terminal.execution_context_byte_length
        ):
            raise SchemaValidationError(
                f"diagnostic batch row {index} binding projection/context drifted"
            )

        terminal_value = terminal.payload["terminal"]
        serialized_produced: list[tuple[str, ArtifactRef]] = []
        for produced_index, produced_row in enumerate(
            terminal_value["produced_artifacts"]
        ):
            role = produced_row["role"]
            reference = parse_artifact_ref(
                thaw_json(produced_row["artifact"]),
                f"batch[{index}].terminal.produced_artifacts[{produced_index}]",
            )
            serialized_produced.append((role, reference))
        produced_roles = tuple(role for role, _reference in serialized_produced)
        if produced_roles not in (
            (),
            ("archive_admission",),
            ("archive_admission", "child_output"),
        ) or terminal.produced_artifact_refs != tuple(
            reference for _role, reference in serialized_produced
        ):
            raise SchemaValidationError(
                "diagnostic batch terminal produced-artifact projection drifted"
            )

        archive_manifest_value = terminal_value["archive_manifest"]
        archive_manifest_ref = (
            None
            if archive_manifest_value is None
            else parse_artifact_ref(
                thaw_json(archive_manifest_value),
                f"batch[{index}].terminal.archive_manifest",
            )
        )
        archive_media = context["artifact_expectations"]["archive"]["media_type"]
        if ("archive_admission" in produced_roles) != (archive_manifest_ref is not None):
            raise SchemaValidationError(
                "diagnostic batch terminal archive-manifest projection drifted"
            )
        if archive_manifest_ref is not None and (
            archive_manifest_ref.media_type != archive_media
            or _ARCHIVE_MANIFEST_ID_RE.fullmatch(
                archive_manifest_ref.artifact_id
            )
            is None
        ):
            raise SchemaValidationError(
                "diagnostic batch terminal archive-manifest identity drifted"
            )

        terminal_binding_ref = parse_artifact_ref(
            thaw_json(terminal.payload["child_execution_binding"]),
            f"batch[{index}].terminal.child_execution_binding",
        )
        if terminal_binding_ref != binding.artifact_ref:
            raise SchemaValidationError(
                "diagnostic batch terminal child-binding projection drifted"
            )
        if (
            terminal.receipt_id != terminal_obj["receipt_id"]
            or terminal.terminal_at != terminal_obj["terminal_at"]
            or terminal.terminal_status != terminal_value["status"]
            or terminal_value["lifecycle_terminal_state"] != terminal.terminal_status
            or terminal.invocation_certainty
            != terminal_value["invocation_certainty"]
            or terminal.worker_started_at != terminal_value["worker_started_at"]
            or terminal.execution_context_sha256
            != terminal_obj["execution_context_sha256"]
            or terminal.execution_context_byte_length
            != terminal_obj["execution_context_byte_length"]
        ):
            raise SchemaValidationError(
                "diagnostic batch terminal dataclass projection drifted"
            )
        expect_enum(
            terminal.terminal_status,
            set(DIAGNOSTIC_TERMINAL_STATUSES),
            f"batch[{index}].terminal_status",
        )
        expect_enum(
            terminal.invocation_certainty,
            set(DIAGNOSTIC_INVOCATION_CERTAINTIES),
            f"batch[{index}].invocation_certainty",
        )
        allowed_phases = {
            "COMPLETED": {"COMPLETE"},
            "FAILED": {"PRE_MODEL", "CAPTURE", "ARCHIVE", "OUTPUT"},
            "INDETERMINATE": {"DISPATCH_OR_EXECUTION"},
            "REJECTED": (
                {"PRE_AUTHORIZATION"}
                if authorization is None
                else {"PRE_ADMISSION"}
            ),
            "EXPIRED": {"AUTHORIZATION_EXPIRED"},
        }[terminal.terminal_status]
        expected_invocation_count: int | str = {
            "EXACTLY_ZERO": 0,
            "EXACTLY_ONE": 1,
            "INDETERMINATE_ZERO_OR_ONE": "INDETERMINATE_ZERO_OR_ONE",
        }[terminal.invocation_certainty]
        if (
            terminal_value["phase"] not in allowed_phases
            or terminal_value["model_invocation_request_count"]
            != expected_invocation_count
        ):
            raise SchemaValidationError(
                "diagnostic batch terminal phase/invocation projection drifted"
            )

        if authorization is None:
            if (
                terminal.terminal_status != "REJECTED"
                or terminal.authorization_sha256 is not None
                or terminal.payload["authorization"] is not None
            ):
                raise SchemaValidationError(
                    "authorization=null batch row must be a preauthorization REJECTED terminal"
                )
        else:
            assert authorization_obj is not None
            authorization_context = authorization.payload["execution_context"]
            authorization_context_bytes = canonical_json_bytes(authorization_context)
            authorization_binding_ref = parse_artifact_ref(
                thaw_json(authorization.payload["child_execution_binding"]),
                f"batch[{index}].authorization.child_execution_binding",
            )
            terminal_authorization_ref = parse_artifact_ref(
                thaw_json(terminal.payload["authorization"]),
                f"batch[{index}].terminal.authorization",
            )
            if (
                binding.execution_context_sha256
                != authorization.execution_context_sha256
                or binding.execution_context_byte_length
                != authorization.execution_context_byte_length
                or authorization_context != context
                or sha256_bytes(authorization_context_bytes)
                != authorization.execution_context_sha256
                or len(authorization_context_bytes)
                != authorization.execution_context_byte_length
                or binding.run_nonce_b64url != authorization.run_nonce_b64url
                or authorization.run_nonce_b64url
                != authorization_context["attempt_binding"]["run_nonce"]["value_b64url"]
                or authorization.authorization_id
                != authorization_obj["authorization_id"]
                or authorization.issued_at != authorization_obj["issued_at"]
                or authorization.not_before != authorization_obj["not_before"]
                or authorization.expires_at != authorization_obj["expires_at"]
                or authorization.study_id != case["study_id"]
                or authorization.case_id != case["case_id"]
                or authorization.case_execution_ordinal
                != case["case_execution_ordinal"]
                or authorization.attempt_ordinal
                != attempt["retry_policy"]["attempt_ordinal"]
                or authorization_binding_ref != binding.artifact_ref
                or terminal_authorization_ref != authorization.artifact_ref
                or terminal.authorization_sha256 != authorization.sha256
            ):
                raise SchemaValidationError("diagnostic batch row authorization/context drifted")
            expected_authorization_refs = _unique_ref_closure(
                (binding.artifact_ref, *binding.artifact_refs),
                f"batch[{index}].authorization.artifact_refs",
            )
            if authorization.artifact_refs != expected_authorization_refs:
                raise SchemaValidationError(
                    "diagnostic batch authorization artifact-ref projection drifted"
                )

        upstream_refs = (
            (binding.artifact_ref, *binding.artifact_refs)
            if authorization is None
            else (authorization.artifact_ref, *authorization.artifact_refs)
        )
        expected_terminal_refs = _unique_ref_closure(
            (
                *upstream_refs,
                *(reference for _role, reference in serialized_produced),
                *((archive_manifest_ref,) if archive_manifest_ref is not None else ()),
            ),
            f"batch[{index}].terminal.artifact_refs",
        )
        if terminal.artifact_refs != expected_terminal_refs:
            raise SchemaValidationError(
                "diagnostic batch terminal artifact-ref projection drifted"
            )

        study_binding = context["study_binding"]
        study_request_ref = parse_artifact_ref(
            thaw_json(study_binding["diagnostic_study_request"]),
            f"batch[{index}].study_request",
        )
        capture_request_ref = parse_artifact_ref(
            thaw_json(study_binding["stagec_capture_request"]),
            f"batch[{index}].capture_request",
        )
        expectations = context["artifact_expectations"]
        capture = expectations["capture"]
        arrays = capture["raw_arrays"]
        expected_ids = {
            "authorization": expectations["authorization"]["artifact_id"],
            "authorization_projection": capture["authorization_projection"]["artifact_id"],
            "capture_index": capture["capture_index"]["artifact_id"],
            "input_ids": arrays["input_ids"]["artifact_id"],
            "attention_mask": arrays["attention_mask"]["artifact_id"],
            "target_vector": arrays["target_vector"]["artifact_id"],
            "wrong_layer_vector": arrays["wrong_layer_vector"]["artifact_id"],
            "archive_admission": expectations["archive"]["admission"]["artifact_id"],
            "child_output": expectations["output"]["artifact_id"],
            "terminal_receipt": expectations["terminal_receipt"]["artifact_id"],
        }
        if binding.binding_id != binding.payload["binding_id"]:
            raise SchemaValidationError("diagnostic batch binding_id field drifted")
        if terminal.receipt_id != expected_ids["terminal_receipt"]:
            raise SchemaValidationError("diagnostic batch terminal receipt ID drifted")
        if authorization is not None and (
            authorization.authorization_id != expected_ids["authorization"]
            or authorization.payload["authorization_id"] != authorization.authorization_id
        ):
            raise SchemaValidationError("diagnostic batch authorization ID drifted")

        produced_by_role = dict(serialized_produced)
        admission_ref = produced_by_role.get("archive_admission")
        output_ref = produced_by_role.get("child_output")
        if admission_ref is not None and (
            admission_ref.artifact_id != expected_ids["archive_admission"]
            or admission_ref.media_type
            != DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE
        ):
            raise SchemaValidationError("diagnostic batch archive-admission ID drifted")
        if output_ref is not None and (
            output_ref.artifact_id != expected_ids["child_output"]
            or output_ref.media_type != DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE
        ):
            raise SchemaValidationError("diagnostic batch child-output ID drifted")
        manifest_refs = (
            () if archive_manifest_ref is None else (archive_manifest_ref,)
        )

        row_identifiers = [
            study_request_ref.artifact_id,
            capture_request_ref.artifact_id,
            case["case_id"],
            case["invocation_id"],
            binding.binding_id,
            *expected_ids.values(),
            *(reference.artifact_id for reference in manifest_refs),
        ]
        if len(row_identifiers) != len(set(row_identifiers)):
            raise SchemaValidationError("diagnostic batch row reuses a child-owned identifier")
        if identifiers.intersection(row_identifiers):
            raise SchemaValidationError("diagnostic batch reuses a child-owned identifier")
        identifiers.update(row_identifiers)

        control_refs = [
            study_request_ref,
            capture_request_ref,
            parse_artifact_ref(
                thaw_json(capture["authorization_projection"]),
                f"batch[{index}].authorization_projection",
            ),
            binding.artifact_ref,
            terminal.artifact_ref,
            *(reference for reference in (admission_ref, output_ref) if reference is not None),
            *manifest_refs,
        ]
        if authorization is not None:
            control_refs.append(authorization.artifact_ref)
        row_content_identities = {
            (reference.sha256, reference.byte_length) for reference in control_refs
        }
        if len(row_content_identities) != len(control_refs):
            raise SchemaValidationError(
                "diagnostic batch row clones control bytes under different identifiers"
            )
        if control_content_identities.intersection(row_content_identities):
            raise SchemaValidationError(
                "diagnostic batch clones control bytes under different child identifiers"
            )
        control_content_identities.update(row_content_identities)

        if binding.run_nonce_b64url in nonces:
            raise SchemaValidationError("diagnostic batch reuses an attempt nonce")
        nonces.add(binding.run_nonce_b64url)
        subject = binding.payload["execution_context"]["attempt_binding"][
            "attempt_subject_sha256"
        ]
        if subject in subjects:
            raise SchemaValidationError("diagnostic batch reuses an attempt subject")
        subjects.add(subject)
        case_key = (binding.case_id, binding.case_execution_ordinal)
        if case_key in case_ordinals:
            raise SchemaValidationError("diagnostic batch repeats a case/ordinal")
        case_ordinals.add(case_key)


__all__ = [
    "DIAGNOSTIC_CHILD_EXECUTION_BINDING_MEDIA_TYPE",
    "DIAGNOSTIC_CHILD_EXECUTION_BINDING_SCHEMA",
    "DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE",
    "DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA",
    "DIAGNOSTIC_INVOCATION_CERTAINTIES",
    "DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE",
    "DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA",
    "DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE",
    "DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA",
    "DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_MEDIA_TYPE",
    "DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_SCHEMA",
    "DIAGNOSTIC_TERMINAL_STATUSES",
    "DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE",
    "DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA",
    "DiagnosticChildExecutionBindingArtifact",
    "DiagnosticChildTerminalReceiptV2Artifact",
    "DiagnosticStageCExecutionContractArtifact",
    "DiagnosticWorkerAuthorizationV2Artifact",
    "build_diagnostic_child_execution_binding",
    "build_diagnostic_child_terminal_receipt_v2",
    "build_diagnostic_stagec_execution_contract",
    "build_diagnostic_worker_authorization_v2",
    "load_diagnostic_child_execution_binding",
    "load_diagnostic_child_terminal_receipt_v2",
    "load_diagnostic_stagec_execution_contract",
    "load_diagnostic_worker_authorization_v2",
    "replay_diagnostic_execution_family",
    "validate_diagnostic_execution_batch_uniqueness",
]
