"""Worker-local admission of one diagnostic-v2 Stage C capture archive.

The live carrier in this module is deliberately factory-only and process-local.
Its factory strictly validates exact canonical diagnostic-v2 authorization bytes,
freshly reloads and semantically replays all seven members of the existing local
Stage C archive, and binds the observation to the small serialized admission
document accepted by the canonical diagnostic terminal protocol.

The v1 archive does not carry a case execution ordinal.  This seam only
range-checks the ordinal declared by the exact authorization bytes; canonical
controller-side chain replay remains required to establish that declaration.

Neither the authorization envelope nor the serialized admission document grants
execution authority.  Successful admission is not authentication, durable
one-use enforcement, trusted time, WORM retention, an external anchor, capture
provenance, a model-file rehash, scientific validation, or a product claim.
The worker HTTP route and Docker wiring remain OPEN and are not implemented here.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import threading
from types import MappingProxyType
from typing import Any, Mapping
import weakref

from .stagec_archive import (
    LOCAL_ARCHIVE_AUTHORITY,
    MANIFEST_MEMBERSHIP_BOUNDARY,
    RELOCATABILITY_BOUNDARY,
    SOURCE_RETENTION_BOUNDARY,
    STAGEC_ARCHIVE_MEMBER_ROLES,
    STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME,
    STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE,
    STAGEC_LOCAL_ARCHIVE_SCHEMA,
    StageCArchivedCapture,
    StageCLocalArchiveReceipt,
    load_stagec_capture_archive,
)
from .stagec_capture import (
    AUTHORIZATION_MEDIA_TYPE,
    CAPTURE_INDEX_MEDIA_TYPE,
    RAW_ARRAY_MEDIA_TYPE,
    REQUEST_MEDIA_TYPE,
    ArtifactIdentity,
)


DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA = (
    "cas_harness_v2.diagnostic_worker_authorization.v2"
)
DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-worker-authorization-v2+json"
)
DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA = (
    "cas_harness_v2.diagnostic_stagec_archive_admission.v2"
)
DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-stagec-archive-admission-v2+json"
)
DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_DOMAIN = (
    "FACTORY_ONLY_FRESH_WORKER_LOCAL_ARCHIVE_REPLAY_V2"
)

DIAGNOSTIC_CHILD_EXECUTION_BINDING_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-child-execution-binding-v2+json"
)
DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-stagec-execution-contract-v2+json"
)
DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-study-plan+json"
)
DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-study-request+json"
)
DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA = (
    "cas_harness_v2.diagnostic_child_terminal_receipt.v2"
)
DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-child-terminal-receipt-v2+json"
)
DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA = (
    "cas_harness_v2.diagnostic_stagec_child_output.v2"
)
DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE = (
    "application/vnd.cas-harness.diagnostic-stagec-child-output-v2+json"
)

ARCHIVE_MANIFEST_ID_DERIVATION = (
    "stagec-local-archive- + lowercase_sha256(canonical_capture_index_ref_payload)"
)
ARCHIVE_CONTENT_PATH_DERIVATION = (
    "objects/sha256/<first-2-lowercase-digest>/<remaining-62>"
)
SERIALIZED_ADMISSION_OBSERVATION = (
    "SERIALIZED_BINDING_ONLY_FACTORY_ORIGIN_EXTERNAL_REQUIRED"
)
HTTP_DOCKER_INTEGRATION_STATUS = "OPEN_NOT_IMPLEMENTED"

AUTHORIZATION_AUTHORITY = MappingProxyType(
    {
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
)
AUTHORIZATION_BOUNDARY = MappingProxyType(
    {
        "state_scope": "PROCESS_LOCAL_EXACT_BYTE_REPLAY",
        "carrier_semantic": "PROSPECTIVE_DIAGNOSTIC_CHILD_AUTHORIZATION_ENVELOPE",
        "execution_authority": "NOT_GRANTED_BY_CARRIER",
        "durable_consumption": "EXTERNAL_REQUIRED_NOT_PROVIDED",
        "retry": "FORBIDDEN",
        "replacement": "FORBIDDEN",
        "execution": "NOT_PERFORMED",
    }
)
SERIALIZED_ADMISSION_BOUNDARY = MappingProxyType(
    {
        "serialized_replay": "STRUCTURAL_BINDING_ONLY",
        "factory_origin": "EXTERNAL_REQUIRED_NOT_PROVIDED_BY_SERIALIZED_BYTES",
        "local_archive_replay": "EXTERNAL_REQUIRED_NOT_PROVIDED_BY_SERIALIZED_BYTES",
        "execution_authority": "NOT_GRANTED",
    }
)
GOVERNANCE = MappingProxyType(
    {
        "admission_ring": 4,
        "product_claim_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "public_release": False,
        "product_route": False,
        "license_decision": "NONE",
    }
)
LOCAL_LIVE_ADMISSION_BOUNDARY = MappingProxyType(
    {
        "state_scope": "PROCESS_LOCAL_FACTORY_ONLY",
        "archive_replay": "FRESH_SEVEN_MEMBER_WORKER_LOCAL_RELOAD_AND_SEMANTIC_REPLAY",
        "expected_manifest_ref": "CALLER_SUPPLIED_FACTORY_RECEIPT_NOT_EXTERNAL_ANCHOR",
        "archive_authority": "LOCAL_SINGLE_HOST_ONLY",
        "membership_scope": MANIFEST_MEMBERSHIP_BOUNDARY,
        "relocatability": RELOCATABILITY_BOUNDARY,
        "source_retention": SOURCE_RETENTION_BOUNDARY,
        "capture_provenance": "NOT_ESTABLISHED",
        "model_file_rehash": "NOT_PERFORMED",
        "authentication": "NOT_PROVIDED",
        "durable_one_use": "NOT_PROVIDED",
        "trusted_time": "NOT_PROVIDED",
        "worm": "NOT_PROVIDED",
        "execution_authority": "NOT_GRANTED",
        "evidence_packet_v2": "FORBIDDEN",
        "scientific_conclusion": "NOT_ESTABLISHED",
        "license": "NOT_GRANTED",
        "product": "NOT_AUTHORIZED",
        "disclosure": "HELD",
        "v1_capture_plan_binding": "PLAN_ID_ONLY",
        "case_execution_ordinal": "AUTHORIZATION_DECLARED_RANGE_BOUND_NOT_ARCHIVE_DERIVED",
        "controller_replay": "CANONICAL_CONTROLLER_CHAIN_REPLAY_STILL_REQUIRED",
        "http_integration": HTTP_DOCKER_INTEGRATION_STATUS,
        "docker_integration": HTTP_DOCKER_INTEGRATION_STATUS,
    }
)

_RETRY_POLICY = {
    "maximum_attempts": 1,
    "attempt_ordinal": 1,
    "retry_count": 0,
    "retry": "FORBIDDEN",
    "replacement": "FORBIDDEN",
    "durable_enforcement": "EXTERNAL_REQUIRED_NOT_PROVIDED",
}
_RUNTIME_CONTRACT = {
    "identity_binding": "EXACT_ORDERED_PLAN_EXECUTION_IDENTITY_ARTIFACTS",
    "worker_profile": "STAGEC_QWEN_W0_SINGLE_PREFILL",
    "model_loader": "EXACT_SINGLETON_LOADER_CARRIER_REQUIRED",
    "network_during_execution": "NOT_ATTESTED",
    "device_and_dtype": "LOADER_BOUND_RUNTIME_OBSERVATION_REQUIRED",
}
_STAGEC_MODEL_CONTRACT = {
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
_STAGEC_CAPTURE_CONTRACT = {
    "capture_request_schema": "cas_harness.stagec.capture_request.v1",
    "capture_request_media_type": REQUEST_MEDIA_TYPE,
    "authorization_projection_schema": "cas_harness.stagec.authorization_projection.v1",
    "authorization_projection_media_type": AUTHORIZATION_MEDIA_TYPE,
    "capture_index_schema": "cas_harness.stagec.capture_index.v1",
    "capture_index_media_type": CAPTURE_INDEX_MEDIA_TYPE,
    "raw_array_media_type": RAW_ARRAY_MEDIA_TYPE,
    "target_layer": 18,
    "target_module_path": "model.layers[18].mlp.down_proj",
    "wrong_layer": 0,
    "wrong_layer_module_path": "model.layers[0].mlp.down_proj",
    "vector_width": 4864,
    "maximum_sequence_length": 32768,
    "direct_capture_model_call_count": 1,
    "direct_generate_api_call_count": 0,
}

_AUTHORIZATION_KEYS = {
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
}
_CONTEXT_KEYS = {
    "diagnostic_preregistration_binding",
    "study_binding",
    "case_binding",
    "execution_contract",
    "execution_identity_artifacts",
    "model_runtime_capture_contract",
    "attempt_binding",
    "worker_assignment",
    "execution_window",
    "artifact_expectations",
}
_CASE_KEYS = {
    "study_id",
    "case_id",
    "case_execution_ordinal",
    "split_id",
    "base_intent_group_id",
    "frozen_variant",
    "frozen_label",
    "invocation_id",
}
_ARCHIVE_EXPECTATION_KEYS = {
    "schema_version",
    "media_type",
    "manifest_name",
    "manifest_id_derivation",
    "content_path_derivation",
    "absolute_root",
    "ordered_member_roles",
    "expected_member_artifact_ids",
    "admission",
}
_ADMISSION_DOCUMENT_KEYS = {
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
}
_MACHINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_ARCHIVE_MANIFEST_ID_RE = re.compile(r"^stagec-local-archive-[0-9a-f]{64}$")


class DiagnosticStageCArchiveAdmissionError(RuntimeError):
    """The worker-local diagnostic archive-admission contract failed closed."""


def _fail(message: str) -> None:
    raise DiagnosticStageCArchiveAdmissionError(message)


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    if type(value) is list:
        return [_thaw_json(item) for item in value]
    if type(value) in (str, int, bool) or value is None:
        return value
    _fail(f"non-JSON value cannot be serialized: {type(value).__name__}")


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    if type(value) in (str, int, bool) or value is None:
        return value
    _fail(f"non-JSON value cannot be frozen: {type(value).__name__}")


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            _thaw_json(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise DiagnosticStageCArchiveAdmissionError(
            "value is not canonical strict JSON"
        ) from exc


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest().upper()


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"JSON object contains duplicate key {key!r}")
        result[key] = value
    return result


def _reject_float(_text: str) -> Any:
    _fail("JSON floating-point numbers are forbidden")


def _reject_constant(_text: str) -> Any:
    _fail("JSON non-finite constants are forbidden")


def _strict_json_object(raw_bytes: Any, *, field_name: str) -> dict[str, Any]:
    if type(raw_bytes) is not bytes:
        _fail(f"{field_name} must be exact immutable bytes")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise DiagnosticStageCArchiveAdmissionError(
            f"{field_name} is not strict UTF-8"
        ) from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except DiagnosticStageCArchiveAdmissionError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise DiagnosticStageCArchiveAdmissionError(
            f"{field_name} is not one strict JSON object"
        ) from exc
    if type(value) is not dict:
        _fail(f"{field_name} must decode to one exact JSON object")
    if _canonical_json_bytes(value) != raw_bytes:
        _fail(f"{field_name} bytes are not the exact canonical encoding")
    return value


def _exact_object(value: Any, keys: set[str], *, field_name: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{field_name} must be an exact JSON object")
    if set(value) != keys:
        _fail(f"{field_name} keys drifted")
    return value


def _text(value: Any, *, field_name: str, maximum: int = 20_000) -> str:
    if type(value) is not str or not value.strip() or len(value) > maximum:
        _fail(f"{field_name} must be a bounded nonblank exact string")
    return value


def _machine_id(value: Any, *, field_name: str) -> str:
    result = _text(value, field_name=field_name, maximum=128)
    if _MACHINE_ID_RE.fullmatch(result) is None:
        _fail(f"{field_name} must be an ASCII machine identifier")
    return result


def _digest(value: Any, *, field_name: str) -> str:
    result = _text(value, field_name=field_name, maximum=64)
    if _SHA256_RE.fullmatch(result) is None:
        _fail(f"{field_name} must be an uppercase SHA-256 digest")
    return result


def _integer(value: Any, *, field_name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > 2**31 - 1:
        _fail(f"{field_name} must be an exact bounded integer")
    return value


def _timestamp(value: Any, *, field_name: str) -> str:
    result = _text(value, field_name=field_name, maximum=32)
    if _TIMESTAMP_RE.fullmatch(result) is None:
        _fail(f"{field_name} must be an explicit UTC ISO-8601 timestamp")
    try:
        datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DiagnosticStageCArchiveAdmissionError(
            f"{field_name} is not a real timestamp"
        ) from exc
    return result


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _ref_from_payload(value: Any, *, field_name: str) -> ArtifactIdentity:
    obj = _exact_object(
        value,
        {"artifact_id", "sha256", "byte_length", "media_type"},
        field_name=field_name,
    )
    try:
        return ArtifactIdentity(
            artifact_id=_machine_id(obj["artifact_id"], field_name=f"{field_name}.artifact_id"),
            sha256=_digest(obj["sha256"], field_name=f"{field_name}.sha256"),
            byte_length=_integer(
                obj["byte_length"], field_name=f"{field_name}.byte_length", minimum=1
            ),
            media_type=_text(
                obj["media_type"], field_name=f"{field_name}.media_type", maximum=128
            ),
        )
    except Exception as exc:
        if isinstance(exc, DiagnosticStageCArchiveAdmissionError):
            raise
        raise DiagnosticStageCArchiveAdmissionError(
            f"{field_name} is not an exact artifact reference"
        ) from exc


def _ref_payload(reference: ArtifactIdentity) -> dict[str, Any]:
    if type(reference) is not ArtifactIdentity:
        _fail("artifact reference has the wrong exact type")
    return reference.to_payload()


def _fixed_mapping(value: Any, expected: Mapping[str, Any], *, field_name: str) -> None:
    obj = _exact_object(value, set(expected), field_name=field_name)
    if obj != dict(expected):
        _fail(f"{field_name} fixed literals drifted")


def _validate_governance(value: Any) -> dict[str, Any]:
    _fixed_mapping(value, GOVERNANCE, field_name="authorization.governance")
    return dict(value)


def _validate_nonce(value: Any) -> None:
    obj = _exact_object(
        value,
        {"value_b64url", "sha256", "profile", "structural_assurance"},
        field_name="execution_context.attempt_binding.run_nonce",
    )
    encoded = _text(
        obj["value_b64url"],
        field_name="execution_context.attempt_binding.run_nonce.value_b64url",
        maximum=43,
    )
    if _NONCE_RE.fullmatch(encoded) is None:
        _fail("run_nonce.value_b64url is not unpadded canonical base64url")
    try:
        decoded = base64.b64decode(encoded + "=", altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise DiagnosticStageCArchiveAdmissionError("run nonce is invalid") from exc
    if (
        len(decoded) != 32
        or base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != encoded
        or _digest(obj["sha256"], field_name="run_nonce.sha256")
        != _sha256_bytes(decoded)
        or obj["profile"] != "CALLER_DECLARED_CSPRNG_256_BIT"
        or obj["structural_assurance"] != "LENGTH_ENCODING_AND_DIGEST_ONLY"
    ):
        _fail("run nonce binding drifted")


def _validate_case_binding(value: Any) -> dict[str, Any]:
    case = _exact_object(value, _CASE_KEYS, field_name="execution_context.case_binding")
    for name in _CASE_KEYS - {"case_execution_ordinal"}:
        _machine_id(case[name], field_name=f"execution_context.case_binding.{name}")
    _integer(
        case["case_execution_ordinal"],
        field_name="execution_context.case_binding.case_execution_ordinal",
        minimum=1,
    )
    if case["frozen_variant"] != case["frozen_label"]:
        _fail("case frozen variant and label drifted")
    return dict(case)


def _validate_preregistration_binding(
    value: Any,
) -> tuple[ArtifactIdentity, tuple[ArtifactIdentity, ...]]:
    obj = _exact_object(
        value,
        {
            "base_artifact",
            "pre_outcome_chain_sha256",
            "protected_design_sha256",
            "study_phase",
            "claim_ceiling",
            "ordered_amendments",
        },
        field_name="execution_context.diagnostic_preregistration_binding",
    )
    base_ref = _ref_from_payload(
        obj["base_artifact"], field_name="preregistration.base_artifact"
    )
    _digest(obj["pre_outcome_chain_sha256"], field_name="preregistration.pre_outcome_chain_sha256")
    _digest(obj["protected_design_sha256"], field_name="preregistration.protected_design_sha256")
    if obj["study_phase"] != "DIAGNOSTIC_CALIBRATION" or obj["claim_ceiling"] != "DIAGNOSTIC_ONLY":
        _fail("diagnostic preregistration role/claim ceiling drifted")
    amendments = obj["ordered_amendments"]
    if type(amendments) is not list or not amendments:
        _fail("ordered amendments must be one nonempty exact JSON array")
    amendment_refs = tuple(
        _ref_from_payload(
            item, field_name=f"preregistration.ordered_amendments[{index}]"
        )
        for index, item in enumerate(amendments)
    )
    if len({reference.artifact_id for reference in amendment_refs}) != len(
        amendment_refs
    ):
        _fail("ordered amendment artifact IDs are not unique")
    return base_ref, amendment_refs


def _canonical_archive_root(value: Any, *, field_name: str) -> str:
    if isinstance(value, Path):
        result = value.as_posix()
    else:
        result = _text(value, field_name=field_name, maximum=4096)
    if result != result.strip() or "\x00" in result or "\\" in result:
        _fail(f"{field_name} must be a normalized absolute path")
    if not (
        result.startswith("/")
        or re.match(r"^[A-Za-z]:/", result) is not None
    ):
        _fail(f"{field_name} must be an absolute path")
    if result.endswith("/") or result in {"", "/"} or re.fullmatch(r"[A-Za-z]:", result):
        _fail(f"{field_name} cannot be a filesystem root or retain a trailing separator")
    parts = result.split("/")
    for index, part in enumerate(parts):
        if part in {"", ".", ".."} and not (index == 0 and part == ""):
            _fail(f"{field_name} contains a noncanonical path component")
        if part.endswith((".", " ")):
            _fail(f"{field_name} components cannot end with a dot or space")
        if ":" in part and not (
            index == 0 and re.fullmatch(r"[A-Za-z]:", part) is not None
        ):
            _fail(f"{field_name} contains a colon outside the Windows drive prefix")
    return result


def _validate_absolute_root(value: Any) -> str:
    return _canonical_archive_root(value, field_name="archive.absolute_root")


def _unique_logical_artifact_ids(entries: list[tuple[str, str]]) -> frozenset[str]:
    observed: dict[str, str] = {}
    for role, artifact_id in entries:
        prior = observed.get(artifact_id)
        if prior is not None:
            _fail(
                "distinct diagnostic artifact roles reuse one artifact ID: "
                f"{prior} and {role}"
            )
        observed[artifact_id] = role
    return frozenset(observed)


def _validate_artifact_expectations(value: Any, *, authorization_id: str) -> dict[str, Any]:
    expectations = _exact_object(
        value,
        {"authorization", "capture", "archive", "output", "terminal_receipt"},
        field_name="execution_context.artifact_expectations",
    )
    authorization = _exact_object(
        expectations["authorization"],
        {"artifact_id", "schema_version", "media_type"},
        field_name="artifact_expectations.authorization",
    )
    if authorization != {
        "artifact_id": authorization_id,
        "schema_version": DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
        "media_type": DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
    }:
        _fail("authorization artifact expectation drifted")

    capture = _exact_object(
        expectations["capture"],
        {"authorization_projection", "capture_index", "raw_arrays"},
        field_name="artifact_expectations.capture",
    )
    projection = _ref_from_payload(
        capture["authorization_projection"],
        field_name="artifact_expectations.capture.authorization_projection",
    )
    if projection.media_type != AUTHORIZATION_MEDIA_TYPE:
        _fail("authorization-projection expected media type drifted")
    index = _exact_object(
        capture["capture_index"],
        {"artifact_id", "schema_version", "media_type"},
        field_name="artifact_expectations.capture.capture_index",
    )
    _machine_id(index["artifact_id"], field_name="capture_index.artifact_id")
    if index["schema_version"] != _STAGEC_CAPTURE_CONTRACT["capture_index_schema"] or index["media_type"] != CAPTURE_INDEX_MEDIA_TYPE:
        _fail("capture-index expectation drifted")

    arrays = _exact_object(
        capture["raw_arrays"],
        {"input_ids", "attention_mask", "target_vector", "wrong_layer_vector"},
        field_name="artifact_expectations.capture.raw_arrays",
    )
    expected_arrays = {
        "input_ids": {"dtype": "<i8", "role": "input_ids"},
        "attention_mask": {"dtype": "<i8", "role": "attention_mask"},
        "target_vector": {
            "dtype": "<f4",
            "role": "target_final_token_activation",
            "layer_index": 18,
            "module_path": "model.layers[18].mlp.down_proj",
        },
        "wrong_layer_vector": {
            "dtype": "<f4",
            "role": "wrong_layer_final_token_activation",
            "layer_index": 0,
            "module_path": "model.layers[0].mlp.down_proj",
        },
    }
    for name, fixed in expected_arrays.items():
        item = _exact_object(
            arrays[name],
            {"artifact_id", *fixed},
            field_name=f"artifact_expectations.capture.raw_arrays.{name}",
        )
        _machine_id(item["artifact_id"], field_name=f"raw_arrays.{name}.artifact_id")
        if {key: item[key] for key in fixed} != fixed:
            _fail(f"raw-array expectation {name} drifted")

    archive = _exact_object(
        expectations["archive"],
        _ARCHIVE_EXPECTATION_KEYS,
        field_name="artifact_expectations.archive",
    )
    if (
        archive["schema_version"] != STAGEC_LOCAL_ARCHIVE_SCHEMA
        or archive["media_type"] != STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE
        or archive["manifest_name"] != STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME
        or archive["manifest_id_derivation"] != ARCHIVE_MANIFEST_ID_DERIVATION
        or archive["content_path_derivation"] != ARCHIVE_CONTENT_PATH_DERIVATION
    ):
        _fail("archive expectation fixed literals drifted")
    _validate_absolute_root(archive["absolute_root"])
    if type(archive["ordered_member_roles"]) is not list or tuple(archive["ordered_member_roles"]) != STAGEC_ARCHIVE_MEMBER_ROLES:
        _fail("archive ordered member roles drifted")
    member_ids = _exact_object(
        archive["expected_member_artifact_ids"],
        set(STAGEC_ARCHIVE_MEMBER_ROLES),
        field_name="archive.expected_member_artifact_ids",
    )
    for role, artifact_id in member_ids.items():
        _machine_id(artifact_id, field_name=f"archive.expected_member_artifact_ids.{role}")
    admission = _exact_object(
        archive["admission"],
        {"artifact_id", "schema_version", "media_type", "admission_domain"},
        field_name="archive.admission",
    )
    _machine_id(admission["artifact_id"], field_name="archive.admission.artifact_id")
    if admission != {
        "artifact_id": admission["artifact_id"],
        "schema_version": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
        "media_type": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
        "admission_domain": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_DOMAIN,
    }:
        _fail("archive admission expectation drifted")

    output = _exact_object(
        expectations["output"],
        {"artifact_id", "output_name", "schema_version", "media_type"},
        field_name="artifact_expectations.output",
    )
    _machine_id(output["artifact_id"], field_name="output.artifact_id")
    if output != {
        "artifact_id": output["artifact_id"],
        "output_name": "diagnostic_stagec_child_output",
        "schema_version": DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
        "media_type": DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE,
    }:
        _fail("diagnostic child-output expectation drifted")
    terminal = _exact_object(
        expectations["terminal_receipt"],
        {"artifact_id", "schema_version", "media_type"},
        field_name="artifact_expectations.terminal_receipt",
    )
    _machine_id(terminal["artifact_id"], field_name="terminal_receipt.artifact_id")
    if terminal != {
        "artifact_id": terminal["artifact_id"],
        "schema_version": DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA,
        "media_type": DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE,
    }:
        _fail("diagnostic terminal-receipt expectation drifted")

    prospective_ids = [
        authorization["artifact_id"],
        projection.artifact_id,
        index["artifact_id"],
        *(arrays[name]["artifact_id"] for name in arrays),
        admission["artifact_id"],
        output["artifact_id"],
        terminal["artifact_id"],
    ]
    if len(prospective_ids) != len(set(prospective_ids)):
        _fail("prospective diagnostic child artifact IDs are not globally unique")
    expected_nonrequest_members = {
        "authorization_projection_artifact": projection.artifact_id,
        "capture_index_artifact": index["artifact_id"],
        **{name: arrays[name]["artifact_id"] for name in arrays},
    }
    if any(
        member_ids[role] != artifact_id
        for role, artifact_id in expected_nonrequest_members.items()
    ):
        _fail("archive expected-member mapping is internally inconsistent")
    return dict(expectations)


@dataclass(frozen=True, slots=True)
class _ValidatedAuthorization:
    ref: ArtifactIdentity
    raw_bytes: bytes
    payload: Mapping[str, Any]
    context: Mapping[str, Any]
    case_binding: Mapping[str, Any]
    archive_expectation: Mapping[str, Any]
    bound_artifact_ids: frozenset[str]


def _validate_authorization(
    *, authorization_ref: ArtifactIdentity, authorization_bytes: bytes
) -> _ValidatedAuthorization:
    if type(authorization_ref) is not ArtifactIdentity:
        _fail("authorization_ref must be an exact ArtifactIdentity")
    if authorization_ref.media_type != DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE:
        _fail("authorization_ref media type drifted")
    if type(authorization_bytes) is not bytes:
        _fail("authorization_bytes must be exact immutable bytes")
    if (
        len(authorization_bytes) != authorization_ref.byte_length
        or _sha256_bytes(authorization_bytes) != authorization_ref.sha256
    ):
        _fail("authorization_ref does not bind exact authorization bytes")
    payload = _strict_json_object(
        authorization_bytes, field_name="diagnostic worker authorization v2"
    )
    _exact_object(payload, _AUTHORIZATION_KEYS, field_name="authorization")
    if payload["schema_version"] != DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA:
        _fail("diagnostic worker authorization schema drifted")
    authorization_id = _machine_id(
        payload["authorization_id"], field_name="authorization.authorization_id"
    )
    if authorization_id != authorization_ref.artifact_id:
        _fail("authorization ID differs from its exact reference")
    issued_at = _timestamp(payload["issued_at"], field_name="authorization.issued_at")
    not_before = _timestamp(payload["not_before"], field_name="authorization.not_before")
    expires_at = _timestamp(payload["expires_at"], field_name="authorization.expires_at")
    if _time(issued_at) >= _time(expires_at) or _time(not_before) >= _time(expires_at):
        _fail("authorization time ordering drifted")
    binding_ref = _ref_from_payload(
        payload["child_execution_binding"],
        field_name="authorization.child_execution_binding",
    )
    if binding_ref.media_type != DIAGNOSTIC_CHILD_EXECUTION_BINDING_MEDIA_TYPE:
        _fail("authorization child-binding media type drifted")
    _fixed_mapping(payload["boundary"], AUTHORIZATION_BOUNDARY, field_name="authorization.boundary")
    _fixed_mapping(payload["authority"], AUTHORIZATION_AUTHORITY, field_name="authorization.authority")
    governance = _validate_governance(payload["governance"])

    context = _exact_object(
        payload["execution_context"], _CONTEXT_KEYS, field_name="authorization.execution_context"
    )
    context_bytes = _canonical_json_bytes(context)
    context_sha = _digest(
        payload["execution_context_sha256"], field_name="authorization.execution_context_sha256"
    )
    context_length = _integer(
        payload["execution_context_byte_length"],
        field_name="authorization.execution_context_byte_length",
        minimum=1,
    )
    if context_sha != _sha256_bytes(context_bytes) or context_length != len(context_bytes):
        _fail("authorization execution-context digest/length drifted")

    base_ref, amendment_refs = _validate_preregistration_binding(
        context["diagnostic_preregistration_binding"]
    )
    study = _exact_object(
        context["study_binding"],
        {"diagnostic_study_plan", "diagnostic_study_request", "stagec_capture_request"},
        field_name="execution_context.study_binding",
    )
    plan_ref = _ref_from_payload(study["diagnostic_study_plan"], field_name="study_binding.diagnostic_study_plan")
    request_ref = _ref_from_payload(study["diagnostic_study_request"], field_name="study_binding.diagnostic_study_request")
    capture_request_ref = _ref_from_payload(study["stagec_capture_request"], field_name="study_binding.stagec_capture_request")
    if (
        plan_ref.media_type != DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE
        or request_ref.media_type != DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE
        or capture_request_ref.media_type != REQUEST_MEDIA_TYPE
    ):
        _fail("diagnostic study-binding media type drifted")
    case = _validate_case_binding(context["case_binding"])
    contract_ref = _ref_from_payload(context["execution_contract"], field_name="execution_context.execution_contract")
    if contract_ref.media_type != DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_MEDIA_TYPE:
        _fail("diagnostic execution-contract media type drifted")
    identities = context["execution_identity_artifacts"]
    if type(identities) is not list or not identities:
        _fail("execution identity artifacts must be one nonempty exact JSON array")
    identity_refs = [
        _ref_from_payload(item, field_name=f"execution_identity_artifacts[{index}]")
        for index, item in enumerate(identities)
    ]
    if len({item.artifact_id for item in identity_refs}) != len(identity_refs):
        _fail("execution identity artifact IDs are not unique")

    runtime = _exact_object(
        context["model_runtime_capture_contract"],
        {"model_contract", "runtime_contract", "capture_contract"},
        field_name="execution_context.model_runtime_capture_contract",
    )
    _fixed_mapping(runtime["model_contract"], _STAGEC_MODEL_CONTRACT, field_name="model_contract")
    _fixed_mapping(runtime["runtime_contract"], _RUNTIME_CONTRACT, field_name="runtime_contract")
    _fixed_mapping(runtime["capture_contract"], _STAGEC_CAPTURE_CONTRACT, field_name="capture_contract")

    attempt = _exact_object(
        context["attempt_binding"],
        {"attempt_subject_sha256", "run_nonce", "retry_policy"},
        field_name="execution_context.attempt_binding",
    )
    _digest(attempt["attempt_subject_sha256"], field_name="attempt_binding.attempt_subject_sha256")
    _validate_nonce(attempt["run_nonce"])
    _fixed_mapping(attempt["retry_policy"], _RETRY_POLICY, field_name="attempt_binding.retry_policy")
    worker = _exact_object(
        context["worker_assignment"],
        {"assigned_worker_id", "assignment_semantic"},
        field_name="execution_context.worker_assignment",
    )
    _machine_id(worker["assigned_worker_id"], field_name="worker_assignment.assigned_worker_id")
    if worker["assignment_semantic"] != "PROSPECTIVE_STRUCTURAL_BINDING_ONLY":
        _fail("worker assignment semantic drifted")
    window = _exact_object(
        context["execution_window"],
        {"amendment", "window_start", "window_end", "semantic", "trust"},
        field_name="execution_context.execution_window",
    )
    window_amendment_ref = _ref_from_payload(
        window["amendment"], field_name="execution_window.amendment"
    )
    window_start = _timestamp(window["window_start"], field_name="execution_window.window_start")
    window_end = _timestamp(window["window_end"], field_name="execution_window.window_end")
    if (
        _time(window_start) >= _time(window_end)
        or window["semantic"] != "DECLARED_UTC_TIMESTAMP_WINDOW_ONLY"
        or window["trust"] != "NOT_TRUSTED"
        or not_before != window_start
        or _time(expires_at) > _time(window_end)
    ):
        _fail("authorization execution-window binding drifted")
    preregistration_amendments = context["diagnostic_preregistration_binding"][
        "ordered_amendments"
    ]
    if window_amendment_ref.to_payload() not in preregistration_amendments:
        _fail("execution-window amendment is not in the ordered preregistration chain")
    expectations = _validate_artifact_expectations(
        context["artifact_expectations"], authorization_id=authorization_id
    )
    archive_expectation = expectations["archive"]
    if (
        archive_expectation["expected_member_artifact_ids"]["request_artifact"]
        != capture_request_ref.artifact_id
    ):
        _fail("archive request-member expectation differs from study capture request")

    logical_ids: list[tuple[str, str]] = [
        ("preregistration.base_artifact", base_ref.artifact_id),
        *(
            (f"preregistration.ordered_amendments[{index}]", reference.artifact_id)
            for index, reference in enumerate(amendment_refs)
        ),
        ("study_binding.diagnostic_study_plan", plan_ref.artifact_id),
        ("study_binding.diagnostic_study_request", request_ref.artifact_id),
        ("study_binding.stagec_capture_request", capture_request_ref.artifact_id),
        ("execution_contract", contract_ref.artifact_id),
        *(
            (f"execution_identity_artifacts[{index}]", reference.artifact_id)
            for index, reference in enumerate(identity_refs)
        ),
        ("child_execution_binding", binding_ref.artifact_id),
        ("artifact_expectations.authorization", expectations["authorization"]["artifact_id"]),
        (
            "artifact_expectations.capture.authorization_projection",
            expectations["capture"]["authorization_projection"]["artifact_id"],
        ),
        ("artifact_expectations.capture.capture_index", expectations["capture"]["capture_index"]["artifact_id"]),
        *(
            (f"artifact_expectations.capture.raw_arrays.{name}", item["artifact_id"])
            for name, item in expectations["capture"]["raw_arrays"].items()
        ),
        ("artifact_expectations.archive.admission", expectations["archive"]["admission"]["artifact_id"]),
        ("artifact_expectations.output", expectations["output"]["artifact_id"]),
        ("artifact_expectations.terminal_receipt", expectations["terminal_receipt"]["artifact_id"]),
    ]
    bound_artifact_ids = _unique_logical_artifact_ids(logical_ids)
    return _ValidatedAuthorization(
        ref=authorization_ref,
        raw_bytes=authorization_bytes,
        payload=_freeze_json(payload),
        context=_freeze_json(context),
        case_binding=_freeze_json(case),
        archive_expectation=_freeze_json(archive_expectation),
        bound_artifact_ids=bound_artifact_ids,
    )


@dataclass(frozen=True, slots=True, init=False)
class DiagnosticStageCArchiveAdmissionArtifact:
    """Strict serialized binding; its bytes never recreate factory origin."""

    raw_bytes: bytes
    ref: ArtifactIdentity
    payload: Mapping[str, Any]
    authorization_ref: ArtifactIdentity
    archive_manifest_ref: ArtifactIdentity
    execution_context_sha256: str
    archive_expectation_sha256: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        _fail("serialized archive-admission construction requires the strict loader")

    @property
    def artifact_ref(self) -> ArtifactIdentity:
        return self.ref

    def to_payload(self) -> dict[str, Any]:
        return _thaw_json(self.payload)


def load_diagnostic_stagec_archive_admission(
    raw_bytes: bytes,
    *,
    expected_artifact_ref: ArtifactIdentity,
    authorization_ref: ArtifactIdentity,
    authorization_bytes: bytes,
) -> DiagnosticStageCArchiveAdmissionArtifact:
    """Strict-load only the portable admission document, never a live admission."""

    authorization = _validate_authorization(
        authorization_ref=authorization_ref,
        authorization_bytes=authorization_bytes,
    )
    if type(expected_artifact_ref) is not ArtifactIdentity:
        _fail("expected_artifact_ref must be an exact ArtifactIdentity")
    if expected_artifact_ref.media_type != DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE:
        _fail("archive-admission expected media type drifted")
    if type(raw_bytes) is not bytes:
        _fail("archive-admission raw bytes must be exact immutable bytes")
    if (
        len(raw_bytes) != expected_artifact_ref.byte_length
        or _sha256_bytes(raw_bytes) != expected_artifact_ref.sha256
    ):
        _fail("archive-admission reference does not bind exact bytes")
    payload = _strict_json_object(raw_bytes, field_name="diagnostic Stage C archive admission")
    _exact_object(payload, _ADMISSION_DOCUMENT_KEYS, field_name="archive_admission")
    admission_expectation = authorization.archive_expectation["admission"]
    admission_id = _machine_id(payload["admission_id"], field_name="archive_admission.admission_id")
    if (
        payload["schema_version"] != DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA
        or admission_id != expected_artifact_ref.artifact_id
        or admission_id != admission_expectation["artifact_id"]
    ):
        _fail("archive-admission identity/schema drifted")
    manifest_ref = _ref_from_payload(
        payload["archive_manifest"], field_name="archive_admission.archive_manifest"
    )
    archive_expectation_sha = _sha256_bytes(
        _canonical_json_bytes(authorization.archive_expectation)
    )
    expected = {
        "schema_version": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
        "admission_id": admission_id,
        "authorization": _ref_payload(authorization.ref),
        "execution_context_sha256": authorization.payload["execution_context_sha256"],
        "case_binding": _thaw_json(authorization.case_binding),
        "archive_expectation_sha256": archive_expectation_sha,
        "archive_manifest": _ref_payload(manifest_ref),
        "observation": SERIALIZED_ADMISSION_OBSERVATION,
        "boundary": dict(SERIALIZED_ADMISSION_BOUNDARY),
        "authority": dict(AUTHORIZATION_AUTHORITY),
        "governance": dict(GOVERNANCE),
    }
    if payload != expected:
        _fail("archive-admission document does not exactly bind authorization/context/manifest")
    if (
        manifest_ref.media_type != authorization.archive_expectation["media_type"]
        or _ARCHIVE_MANIFEST_ID_RE.fullmatch(manifest_ref.artifact_id) is None
    ):
        _fail("archive-admission manifest reference drifted")
    artifact = object.__new__(DiagnosticStageCArchiveAdmissionArtifact)
    for name, value in (
        ("raw_bytes", raw_bytes),
        ("ref", expected_artifact_ref),
        ("payload", _freeze_json(payload)),
        ("authorization_ref", authorization.ref),
        ("archive_manifest_ref", manifest_ref),
        ("execution_context_sha256", authorization.payload["execution_context_sha256"]),
        ("archive_expectation_sha256", archive_expectation_sha),
    ):
        object.__setattr__(artifact, name, value)
    return artifact


def _archive_members(archive: StageCArchivedCapture) -> dict[str, Any]:
    return {
        "request_artifact": archive.request_artifact,
        "authorization_projection_artifact": archive.authorization_projection_artifact,
        "capture_index_artifact": archive.index_artifact,
        "input_ids": archive.input_ids,
        "attention_mask": archive.attention_mask,
        "target_vector": archive.target_vector,
        "wrong_layer_vector": archive.wrong_layer_vector,
    }


def _validate_archive_against_authorization(
    *,
    archive_receipt: StageCLocalArchiveReceipt,
    authorization: _ValidatedAuthorization,
) -> StageCArchivedCapture:
    if type(archive_receipt) is not StageCLocalArchiveReceipt:
        _fail("archive_receipt must be an exact StageCLocalArchiveReceipt")
    try:
        archive_receipt._validate()
        loaded = load_stagec_capture_archive(
            archive_receipt.root,
            expected_manifest_ref=archive_receipt.manifest_ref,
        )
        loaded._validate()
    except Exception as exc:
        if isinstance(exc, DiagnosticStageCArchiveAdmissionError):
            raise
        raise DiagnosticStageCArchiveAdmissionError(
            f"fresh worker-local Stage C archive replay failed: {type(exc).__name__}: {exc}"
        ) from exc
    if (
        loaded.root != archive_receipt.root
        or loaded.manifest_artifact.ref != archive_receipt.manifest_ref
        or {
            name: loaded.index.association[name]
            for name in archive_receipt.association
        }
        != dict(archive_receipt.association)
        or dict(loaded.authority) != dict(LOCAL_ARCHIVE_AUTHORITY)
    ):
        _fail("fresh archive replay differs from its exact local receipt")

    expectation = authorization.archive_expectation
    observed_root = _canonical_archive_root(
        loaded.root, field_name="fresh_archive.root"
    )
    expected_root = _canonical_archive_root(
        expectation["absolute_root"], field_name="archive.absolute_root"
    )
    if observed_root != expected_root:
        _fail("fresh archive root differs from authorization expectation")
    if tuple(expectation["ordered_member_roles"]) != STAGEC_ARCHIVE_MEMBER_ROLES:
        _fail("authorized archive member ordering drifted")
    if _ARCHIVE_MANIFEST_ID_RE.fullmatch(loaded.manifest_artifact.ref.artifact_id) is None:
        _fail("fresh archive manifest ID derivation drifted")

    members = _archive_members(loaded)
    if tuple(members) != STAGEC_ARCHIVE_MEMBER_ROLES:
        _fail("fresh archive does not expose exactly seven ordered member roles")
    actual_ids = [members[role].ref.artifact_id for role in STAGEC_ARCHIVE_MEMBER_ROLES]
    expected_ids = expectation["expected_member_artifact_ids"]
    if len(actual_ids) != len(set(actual_ids)):
        _fail("fresh archive member artifact IDs are not unique")
    for role, artifact_id in zip(STAGEC_ARCHIVE_MEMBER_ROLES, actual_ids):
        if artifact_id != expected_ids[role]:
            _fail(f"fresh archive member {role} differs from authorization expectation")
    # Content SHA equality is intentionally allowed across distinct roles/IDs.

    manifest_id = loaded.manifest_artifact.ref.artifact_id
    if manifest_id in authorization.bound_artifact_ids:
        _fail("fresh archive manifest ID collides with a bound diagnostic artifact")

    context = authorization.context
    study = context["study_binding"]
    case = context["case_binding"]
    association = loaded.index.association
    if loaded.request_artifact.ref.to_payload() != _thaw_json(study["stagec_capture_request"]):
        _fail("fresh archive request differs from diagnostic study binding")
    if loaded.authorization_projection_artifact.ref.to_payload() != _thaw_json(
        context["artifact_expectations"]["capture"]["authorization_projection"]
    ):
        _fail("fresh archive authorization projection differs from expectation")
    if association["plan_id"] != study["diagnostic_study_plan"]["artifact_id"]:
        _fail("v1 capture plan_id differs from diagnostic Study plan ID")
    # The v1 archive has no execution ordinal.  The authorization ordinal was
    # range-checked above, but canonical controller replay must establish it.
    for name in _CASE_KEYS - {"case_execution_ordinal"}:
        if association[name] != case[name]:
            _fail(f"fresh archive case association drifted at {name}")

    capture_expectation = context["artifact_expectations"]["capture"]
    if (
        loaded.index_artifact.ref.artifact_id != capture_expectation["capture_index"]["artifact_id"]
        or loaded.index_artifact.ref.media_type != capture_expectation["capture_index"]["media_type"]
        or loaded.index.payload["schema_version"] != capture_expectation["capture_index"]["schema_version"]
    ):
        _fail("fresh archive capture-index expectation drifted")
    arrays = capture_expectation["raw_arrays"]
    for role in ("input_ids", "attention_mask", "target_vector", "wrong_layer_vector"):
        ref = members[role].ref
        expected = arrays[role]
        if (
            ref.artifact_id != expected["artifact_id"]
            or ref.dtype != expected["dtype"]
            or ref.role != expected["role"]
            or ("layer_index" in expected and ref.layer_index != expected["layer_index"])
            or ("module_path" in expected and ref.module_path != expected["module_path"])
        ):
            _fail(f"fresh archive raw-array expectation drifted at {role}")
    return loaded


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class StageCLocalArchiveAdmission:
    """Factory-created live admission, usable only in this Python process."""

    archive_receipt: StageCLocalArchiveReceipt
    archive: StageCArchivedCapture
    artifact: DiagnosticStageCArchiveAdmissionArtifact
    authorization_ref: ArtifactIdentity
    authorization_bytes: bytes = field(repr=False)
    boundary: Mapping[str, str]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        _fail("live archive-admission construction requires the worker-local factory")

    def _validate(self) -> None:
        if type(self.archive_receipt) is not StageCLocalArchiveReceipt:
            _fail("live admission receipt has the wrong exact type")
        if type(self.archive) is not StageCArchivedCapture:
            _fail("live admission archive has the wrong exact type")
        if type(self.artifact) is not DiagnosticStageCArchiveAdmissionArtifact:
            _fail("live admission serialized artifact has the wrong exact type")
        if type(self.authorization_ref) is not ArtifactIdentity or type(self.authorization_bytes) is not bytes:
            _fail("live admission authorization binding has the wrong exact types")
        if self.artifact.authorization_ref != self.authorization_ref:
            _fail("live admission authorization reference drifted")
        if self.artifact.archive_manifest_ref != self.archive.manifest_artifact.ref:
            _fail("live admission archive manifest reference drifted")
        if dict(self.boundary) != dict(LOCAL_LIVE_ADMISSION_BOUNDARY):
            _fail("live admission boundary drifted")


_LIVE_REGISTRY_LOCK = threading.Lock()
_LIVE_REGISTRY: dict[
    int, tuple[weakref.ReferenceType[StageCLocalArchiveAdmission], str]
] = {}


def _live_seal(admission: StageCLocalArchiveAdmission) -> str:
    members = _archive_members(admission.archive)
    value = {
        "archive_receipt": admission.archive_receipt.to_payload(),
        "archive_manifest": admission.archive.manifest_artifact.ref.to_payload(),
        "archive_members": [
            {"role": role, "ref": members[role].ref.to_payload()}
            for role in STAGEC_ARCHIVE_MEMBER_ROLES
        ],
        "artifact": admission.artifact.ref.to_payload(),
        "artifact_raw_sha256": _sha256_bytes(admission.artifact.raw_bytes),
        "authorization": admission.authorization_ref.to_payload(),
        "authorization_raw_sha256": _sha256_bytes(admission.authorization_bytes),
        "boundary": dict(admission.boundary),
    }
    return _sha256_bytes(_canonical_json_bytes(value))


def _register_live(admission: StageCLocalArchiveAdmission) -> None:
    admission_id = id(admission)
    seal = _live_seal(admission)

    def discard(reference: weakref.ReferenceType[StageCLocalArchiveAdmission]) -> None:
        with _LIVE_REGISTRY_LOCK:
            current = _LIVE_REGISTRY.get(admission_id)
            if current is not None and current[0] is reference:
                _LIVE_REGISTRY.pop(admission_id, None)

    reference = weakref.ref(admission, discard)
    with _LIVE_REGISTRY_LOCK:
        _LIVE_REGISTRY[admission_id] = (reference, seal)


def _require_live(admission: Any) -> StageCLocalArchiveAdmission:
    if type(admission) is not StageCLocalArchiveAdmission:
        _fail("live replay requires an exact StageCLocalArchiveAdmission")
    admission._validate()
    with _LIVE_REGISTRY_LOCK:
        registered = _LIVE_REGISTRY.get(id(admission))
    if registered is None or registered[0]() is not admission:
        _fail("archive admission is not factory-created in this process")
    if registered[1] != _live_seal(admission):
        _fail("factory-created archive admission drifted after registration")
    return admission


def admit_diagnostic_stagec_archive(
    *,
    archive_receipt: StageCLocalArchiveReceipt,
    authorization_ref: ArtifactIdentity,
    authorization_bytes: bytes,
) -> StageCLocalArchiveAdmission:
    """Freshly replay one exact local archive and mint one live admission."""

    authorization = _validate_authorization(
        authorization_ref=authorization_ref,
        authorization_bytes=authorization_bytes,
    )
    loaded = _validate_archive_against_authorization(
        archive_receipt=archive_receipt,
        authorization=authorization,
    )
    admission_id = authorization.archive_expectation["admission"]["artifact_id"]
    value = {
        "schema_version": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
        "admission_id": admission_id,
        "authorization": authorization.ref.to_payload(),
        "execution_context_sha256": authorization.payload["execution_context_sha256"],
        "case_binding": _thaw_json(authorization.case_binding),
        "archive_expectation_sha256": _sha256_bytes(
            _canonical_json_bytes(authorization.archive_expectation)
        ),
        "archive_manifest": loaded.manifest_artifact.ref.to_payload(),
        "observation": SERIALIZED_ADMISSION_OBSERVATION,
        "boundary": dict(SERIALIZED_ADMISSION_BOUNDARY),
        "authority": dict(AUTHORIZATION_AUTHORITY),
        "governance": dict(GOVERNANCE),
    }
    raw = _canonical_json_bytes(value)
    artifact_ref = ArtifactIdentity(
        artifact_id=admission_id,
        sha256=_sha256_bytes(raw),
        byte_length=len(raw),
        media_type=DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
    )
    artifact = load_diagnostic_stagec_archive_admission(
        raw,
        expected_artifact_ref=artifact_ref,
        authorization_ref=authorization.ref,
        authorization_bytes=authorization.raw_bytes,
    )
    admission = object.__new__(StageCLocalArchiveAdmission)
    for name, item in (
        ("archive_receipt", archive_receipt),
        ("archive", loaded),
        ("artifact", artifact),
        ("authorization_ref", authorization.ref),
        ("authorization_bytes", authorization.raw_bytes),
        ("boundary", LOCAL_LIVE_ADMISSION_BOUNDARY),
    ):
        object.__setattr__(admission, name, item)
    admission._validate()
    _register_live(admission)
    return admission


def replay_stagec_local_archive_admission(
    admission: StageCLocalArchiveAdmission,
) -> StageCArchivedCapture:
    """Require live factory origin and freshly replay its seven-member archive."""

    live = _require_live(admission)
    authorization = _validate_authorization(
        authorization_ref=live.authorization_ref,
        authorization_bytes=live.authorization_bytes,
    )
    serialized = load_diagnostic_stagec_archive_admission(
        live.artifact.raw_bytes,
        expected_artifact_ref=live.artifact.ref,
        authorization_ref=live.authorization_ref,
        authorization_bytes=live.authorization_bytes,
    )
    if serialized != live.artifact:
        _fail("live admission differs from fresh serialized replay")
    loaded = _validate_archive_against_authorization(
        archive_receipt=live.archive_receipt,
        authorization=authorization,
    )
    if loaded.manifest_artifact.ref != serialized.archive_manifest_ref:
        _fail("fresh live replay differs from serialized manifest binding")
    return loaded


__all__ = [
    "AUTHORIZATION_AUTHORITY",
    "AUTHORIZATION_BOUNDARY",
    "DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_DOMAIN",
    "DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE",
    "DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA",
    "DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE",
    "DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA",
    "DiagnosticStageCArchiveAdmissionArtifact",
    "DiagnosticStageCArchiveAdmissionError",
    "GOVERNANCE",
    "HTTP_DOCKER_INTEGRATION_STATUS",
    "LOCAL_LIVE_ADMISSION_BOUNDARY",
    "SERIALIZED_ADMISSION_BOUNDARY",
    "StageCLocalArchiveAdmission",
    "admit_diagnostic_stagec_archive",
    "load_diagnostic_stagec_archive_admission",
    "replay_stagec_local_archive_admission",
]
