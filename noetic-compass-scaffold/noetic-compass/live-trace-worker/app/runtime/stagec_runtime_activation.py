"""Fail-closed, process-local Stage C row model-call capability gate.

This module is deliberately independent of ``cas_harness_v2`` and of the
Stage C capture implementation.  It accepts only plain immutable values, and
it has no built-in backend capable of authenticating an activation.  A future
worker deployment must install one exact backend type in the private registry
and bind an exact backend instance during process construction.

Even a successfully authenticated permit is only a local one-call chokepoint.
It is not scientific evidence, product authority, Evidence Packet authority,
licensing, disclosure approval, or proof that any execution occurred.  The
fixed project boundary remains Gate 5 ``OPEN / KEEP_OPEN``, Stage C
``DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED``, and
``NOT LICENSED / HELD / NOT FROZEN``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
import secrets
import threading
from typing import Any


STAGEC_RUNTIME_ACTIVATION_SCHEMA = (
    "cas_harness.stagec.worker_runtime_activation_envelope.v1"
)
STAGEC_RUNTIME_LEDGER_OBSERVATION_SCHEMA = (
    "cas_harness.stagec.worker_runtime_activation_ledger_observation.v1"
)
STAGEC_RUNTIME_TERMINAL_OBSERVATION_SCHEMA = (
    "cas_harness.stagec.worker_runtime_activation_terminal_observation.v1"
)
STAGEC_RUNTIME_AMBIGUOUS_TERMINAL_OBSERVATION_SCHEMA = (
    "cas_harness.stagec.worker_runtime_activation_ambiguous_terminal_observation.v1"
)
STAGEC_RUNTIME_PURPOSE = "ONE_EXACT_STAGEC_ROW_MODEL_CALL"
STAGEC_RUNTIME_CAPABILITY_STATUS = (
    "PROCESS_LOCAL_ONE_USE_MODEL_CALL_CHOKEPOINT_ONLY"
)
STAGEC_RUNTIME_AUTHORITY_BOUNDARY = (
    "NO_SCIENTIFIC_PRODUCT_EVIDENCE_PACKET_LICENSE_OR_DISCLOSURE_AUTHORITY"
)
GATE5_STATUS = "OPEN / KEEP_OPEN"
STAGEC_DESIGN_STATUS = "DESIGN_ONLY"
STAGEC_AUTHORIZATION_STATUS = "UNAUTHORIZED"
STAGEC_EXECUTION_STATUS = "NOT_STARTED"
LICENSE_STATUS = "NOT LICENSED"
GOVERNANCE_STATUS = "HELD"
FREEZE_STATUS = "NOT FROZEN"

REQUEST_MEDIA_TYPE = "application/vnd.cas-harness.stagec-capture-request+json"
AUTHORIZATION_PROJECTION_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-authorization-projection+json"
)

STAGEC_CAPTURE_ARTIFACT_ID_FIELDS = (
    "capture_index",
    "model_config",
    "model_weights",
    "tokenizer_json",
    "tokenizer_config",
    "chat_template",
    "input_ids",
    "attention_mask",
    "target_vector",
    "wrong_layer_vector",
)

_MAX_ENVELOPE_BYTES = 65_536
_MAX_SIGNED_INT64 = (1 << 63) - 1
_STAGEC_ROW_COUNT = 480
_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_ARTIFACT_IDENTITY_KEYS = {
    "artifact_id",
    "sha256",
    "byte_length",
    "media_type",
}
_ENVELOPE_KEYS = {
    "schema_version",
    "purpose",
    "request_artifact_identity",
    "authorization_projection_artifact_identity",
    "capture_artifact_ids",
    "runtime_principal",
    "attempt",
    "model_identity",
    "runtime_authorization",
    "scope",
    "project_boundary",
}


class StageCRuntimeActivationErrorCode(str, Enum):
    """Closed worker-gate failure codes; backend text never becomes authority."""

    INVALID_INPUT = "STAGEC_RUNTIME_INVALID_INPUT"
    INVALID_ENVELOPE = "STAGEC_RUNTIME_INVALID_ENVELOPE"
    BACKEND_UNAVAILABLE = "STAGEC_RUNTIME_BACKEND_UNAVAILABLE"
    BACKEND_NOT_REGISTERED = "STAGEC_RUNTIME_BACKEND_NOT_REGISTERED"
    BACKEND_REJECTED = "STAGEC_RUNTIME_BACKEND_REJECTED"
    BACKEND_PROTOCOL_VIOLATION = "STAGEC_RUNTIME_BACKEND_PROTOCOL_VIOLATION"
    DUPLICATE_BACKEND_CLAIM = "STAGEC_RUNTIME_DUPLICATE_BACKEND_CLAIM"
    INVALID_PERMIT = "STAGEC_RUNTIME_INVALID_PERMIT"
    PERMIT_BINDING_MISMATCH = "STAGEC_RUNTIME_PERMIT_BINDING_MISMATCH"
    PERMIT_ALREADY_REDEEMED = "STAGEC_RUNTIME_PERMIT_ALREADY_REDEEMED"
    PERMIT_INVALIDATED = "STAGEC_RUNTIME_PERMIT_INVALIDATED"
    PERMIT_TERMINALIZATION_INDETERMINATE = (
        "STAGEC_RUNTIME_PERMIT_TERMINALIZATION_INDETERMINATE"
    )
    BACKEND_TERMINALIZATION_FAILED = (
        "STAGEC_RUNTIME_BACKEND_TERMINALIZATION_FAILED"
    )
    BACKEND_REDEEM_REAUTHENTICATION_FAILED = (
        "STAGEC_RUNTIME_BACKEND_REDEEM_REAUTHENTICATION_FAILED"
    )
    BACKEND_AMBIGUOUS_TERMINALIZATION_FAILED = (
        "STAGEC_RUNTIME_BACKEND_AMBIGUOUS_TERMINALIZATION_FAILED"
    )
    INVALID_INVALIDATION_DISPOSITION = (
        "STAGEC_RUNTIME_INVALID_INVALIDATION_DISPOSITION"
    )


class StageCRuntimeActivationError(RuntimeError):
    """A closed-code failure to establish or use a Stage C row permit."""

    __slots__ = ("code",)

    def __init__(self, code: StageCRuntimeActivationErrorCode) -> None:
        if type(code) is not StageCRuntimeActivationErrorCode:
            raise TypeError("Stage C runtime errors require an exact closed code")
        self.code = code.value
        super().__init__(code.value)


class StageCModelCallInvalidationDisposition(str, Enum):
    """Closed pre-model-call terminal dispositions for a claimed permit."""

    REJECTED = "INVALIDATED_REJECTED_PRE_MODEL_CALL"
    INDETERMINATE = "INVALIDATED_INDETERMINATE_PRE_MODEL_CALL"


class StageCRuntimeActivationAmbiguityReason(str, Enum):
    """Closed reasons requiring a control-owned durable row tombstone."""

    AUTHENTICATE_EXCEPTION = "AUTHENTICATE_EXCEPTION"
    BACKEND_ENVELOPE_MUTATION = "BACKEND_ENVELOPE_MUTATION"
    MALFORMED_LEDGER_OBSERVATION = "MALFORMED_LEDGER_OBSERVATION"
    DUPLICATE_RETURNED_CLAIM_ID = "DUPLICATE_RETURNED_CLAIM_ID"


_REDEEMED_TERMINAL_STATE = "CALL_STARTED"
_UNCLAIMED_STATE = "UNCLAIMED"
_CLAIMED_STATE = "AUTHENTICATED_AND_CLAIMED_FOR_ONE_MODEL_CALL"


def _fail(code: StageCRuntimeActivationErrorCode) -> None:
    raise StageCRuntimeActivationError(code)


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest().upper()


def _require_text(value: Any, *, identifier: bool = False) -> str:
    if type(value) is not str or not value or len(value) > 512:
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    if identifier and _IDENTIFIER_RE.fullmatch(value) is None:
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    return value


def _require_sha256(value: Any) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    return value


def _require_int(value: Any, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= _MAX_SIGNED_INT64:
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    return value


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.INVALID_INPUT
        ) from exc


def _artifact_identity(
    value: Any,
    *,
    expected_media_type: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _ARTIFACT_IDENTITY_KEYS:
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    artifact_id = _require_text(value["artifact_id"], identifier=True)
    digest = _require_sha256(value["sha256"])
    byte_length = _require_int(value["byte_length"], minimum=1)
    media_type = _require_text(value["media_type"])
    if media_type != expected_media_type:
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    return {
        "artifact_id": artifact_id,
        "sha256": digest,
        "byte_length": byte_length,
        "media_type": media_type,
    }


def _capture_artifact_ids(value: Any) -> dict[str, str]:
    if type(value) is tuple:
        if len(value) != len(STAGEC_CAPTURE_ARTIFACT_ID_FIELDS):
            _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
        source = dict(zip(STAGEC_CAPTURE_ARTIFACT_ID_FIELDS, value, strict=True))
    elif type(value) is dict:
        if set(value) != set(STAGEC_CAPTURE_ARTIFACT_ID_FIELDS):
            _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
        source = value
    else:
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    normalized = {
        name: _require_text(source[name], identifier=True)
        for name in STAGEC_CAPTURE_ARTIFACT_ID_FIELDS
    }
    if len(set(normalized.values())) != len(normalized):
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    return normalized


def _build_envelope_payload(
    *,
    request_artifact_identity: Any,
    authorization_projection_artifact_identity: Any,
    capture_artifact_ids: Any,
    tenant_id: Any,
    worker_id: Any,
    lease_generation: Any,
    attempt_subject_sha256: Any,
    case_id: Any,
    case_execution_ordinal: Any,
    model_id: Any,
    model_revision: Any,
    model_config_sha256: Any,
    weights_sha256: Any,
    tokenizer_json_sha256: Any,
    tokenizer_config_sha256: Any,
    chat_template_sha256: Any,
    capture_profile_sha256: Any,
    phase_activation_id: Any,
    ledger_generation: Any,
) -> dict[str, Any]:
    request = _artifact_identity(
        request_artifact_identity,
        expected_media_type=REQUEST_MEDIA_TYPE,
    )
    authorization = _artifact_identity(
        authorization_projection_artifact_identity,
        expected_media_type=AUTHORIZATION_PROJECTION_MEDIA_TYPE,
    )
    capture_ids = _capture_artifact_ids(capture_artifact_ids)
    prospective_ids = (
        request["artifact_id"],
        authorization["artifact_id"],
        *(capture_ids[name] for name in STAGEC_CAPTURE_ARTIFACT_ID_FIELDS),
    )
    if len(set(prospective_ids)) != len(prospective_ids):
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)

    tenant = _require_text(tenant_id, identifier=True)
    worker = _require_text(worker_id, identifier=True)
    lease = _require_int(lease_generation, minimum=1)
    subject = _require_sha256(attempt_subject_sha256)
    case = _require_text(case_id, identifier=True)
    ordinal = _require_int(case_execution_ordinal, minimum=1)
    if ordinal > _STAGEC_ROW_COUNT:
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    selected_model_id = _require_text(model_id)
    revision = _require_text(model_revision)
    if _REVISION_RE.fullmatch(revision) is None:
        _fail(StageCRuntimeActivationErrorCode.INVALID_INPUT)
    model_config = _require_sha256(model_config_sha256)
    weights = _require_sha256(weights_sha256)
    tokenizer_json = _require_sha256(tokenizer_json_sha256)
    tokenizer_config = _require_sha256(tokenizer_config_sha256)
    chat_template = _require_sha256(chat_template_sha256)
    capture_profile = _require_sha256(capture_profile_sha256)
    activation_id = _require_text(phase_activation_id, identifier=True)
    generation = _require_int(ledger_generation, minimum=1)

    return {
        "schema_version": STAGEC_RUNTIME_ACTIVATION_SCHEMA,
        "purpose": STAGEC_RUNTIME_PURPOSE,
        "request_artifact_identity": request,
        "authorization_projection_artifact_identity": authorization,
        "capture_artifact_ids": capture_ids,
        "runtime_principal": {
            "tenant_id": tenant,
            "worker_id": worker,
            "lease_generation": lease,
        },
        "attempt": {
            "attempt_subject_sha256": subject,
            "case_id": case,
            "case_execution_ordinal": ordinal,
        },
        "model_identity": {
            "model_id": selected_model_id,
            "model_revision": revision,
            "model_config_sha256": model_config,
            "weights_sha256": weights,
            "tokenizer_json_sha256": tokenizer_json,
            "tokenizer_config_sha256": tokenizer_config,
            "chat_template_sha256": chat_template,
            "capture_profile_sha256": capture_profile,
        },
        "runtime_authorization": {
            "phase_activation_id": activation_id,
            "ledger_generation": generation,
        },
        "scope": {
            "row_model_call_count": 1,
            "canary_count": 0,
            "pre_row_model_forward_count": 0,
            "corpus_access": "EXACT_BOUND_ROW_ONLY",
            "outcome_access_before_model_call": "FORBIDDEN",
        },
        "project_boundary": {
            "capability_status": STAGEC_RUNTIME_CAPABILITY_STATUS,
            "authority_boundary": STAGEC_RUNTIME_AUTHORITY_BOUNDARY,
            "gate5_status": GATE5_STATUS,
            "stagec_design_status": STAGEC_DESIGN_STATUS,
            "stagec_authorization_status": STAGEC_AUTHORIZATION_STATUS,
            "stagec_execution_status": STAGEC_EXECUTION_STATUS,
            "license_status": LICENSE_STATUS,
            "governance_status": GOVERNANCE_STATUS,
            "freeze_status": FREEZE_STATUS,
        },
    }


def _strict_json_object(raw_bytes: Any) -> dict[str, Any]:
    if (
        type(raw_bytes) is not bytes
        or not raw_bytes
        or len(raw_bytes) > _MAX_ENVELOPE_BYTES
    ):
        _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.INVALID_ENVELOPE
        ) from exc
    if text.startswith("\ufeff"):
        _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)

    def reject_constant(_value: str) -> None:
        _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)

    def exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
            result[key] = value
        return result

    try:
        value = json.loads(
            text,
            parse_constant=reject_constant,
            object_pairs_hook=exact_object,
        )
    except StageCRuntimeActivationError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.INVALID_ENVELOPE
        ) from exc
    if type(value) is not dict or _canonical_json_bytes(value) != raw_bytes:
        _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    return value


def _replay_envelope_payload(raw_bytes: Any) -> dict[str, Any]:
    value = _strict_json_object(raw_bytes)
    if set(value) != _ENVELOPE_KEYS:
        _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    try:
        rebuilt = _build_envelope_payload(
            request_artifact_identity=value["request_artifact_identity"],
            authorization_projection_artifact_identity=value[
                "authorization_projection_artifact_identity"
            ],
            capture_artifact_ids=value["capture_artifact_ids"],
            tenant_id=value["runtime_principal"]["tenant_id"],
            worker_id=value["runtime_principal"]["worker_id"],
            lease_generation=value["runtime_principal"]["lease_generation"],
            attempt_subject_sha256=value["attempt"]["attempt_subject_sha256"],
            case_id=value["attempt"]["case_id"],
            case_execution_ordinal=value["attempt"]["case_execution_ordinal"],
            model_id=value["model_identity"]["model_id"],
            model_revision=value["model_identity"]["model_revision"],
            model_config_sha256=value["model_identity"]["model_config_sha256"],
            weights_sha256=value["model_identity"]["weights_sha256"],
            tokenizer_json_sha256=value["model_identity"][
                "tokenizer_json_sha256"
            ],
            tokenizer_config_sha256=value["model_identity"][
                "tokenizer_config_sha256"
            ],
            chat_template_sha256=value["model_identity"][
                "chat_template_sha256"
            ],
            capture_profile_sha256=value["model_identity"][
                "capture_profile_sha256"
            ],
            phase_activation_id=value["runtime_authorization"][
                "phase_activation_id"
            ],
            ledger_generation=value["runtime_authorization"]["ledger_generation"],
        )
    except (KeyError, TypeError, StageCRuntimeActivationError) as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.INVALID_ENVELOPE
        ) from exc
    if value != rebuilt:
        _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    return value


@dataclass(frozen=True, slots=True)
class StageCRuntimeActivationEnvelope:
    """Canonical immutable bytes presented to the registered trust backend."""

    raw_bytes: bytes
    sha256: str

    def __post_init__(self) -> None:
        try:
            _replay_envelope_payload(self.raw_bytes)
            digest = _sha256_bytes(self.raw_bytes)
        except StageCRuntimeActivationError as exc:
            raise StageCRuntimeActivationError(
                StageCRuntimeActivationErrorCode.INVALID_ENVELOPE
            ) from exc
        if type(self.sha256) is not str or self.sha256 != digest:
            _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)


def build_stagec_runtime_activation_envelope(
    *,
    request_artifact_identity: dict[str, Any],
    authorization_projection_artifact_identity: dict[str, Any],
    capture_artifact_ids: tuple[str, ...] | dict[str, str],
    tenant_id: str,
    worker_id: str,
    lease_generation: int,
    attempt_subject_sha256: str,
    case_id: str,
    case_execution_ordinal: int,
    model_id: str,
    model_revision: str,
    model_config_sha256: str,
    weights_sha256: str,
    tokenizer_json_sha256: str,
    tokenizer_config_sha256: str,
    chat_template_sha256: str,
    capture_profile_sha256: str,
    phase_activation_id: str,
    ledger_generation: int,
) -> StageCRuntimeActivationEnvelope:
    """Build exact bytes without consulting a clock, provider, or trust root."""

    payload = _build_envelope_payload(
        request_artifact_identity=request_artifact_identity,
        authorization_projection_artifact_identity=(
            authorization_projection_artifact_identity
        ),
        capture_artifact_ids=capture_artifact_ids,
        tenant_id=tenant_id,
        worker_id=worker_id,
        lease_generation=lease_generation,
        attempt_subject_sha256=attempt_subject_sha256,
        case_id=case_id,
        case_execution_ordinal=case_execution_ordinal,
        model_id=model_id,
        model_revision=model_revision,
        model_config_sha256=model_config_sha256,
        weights_sha256=weights_sha256,
        tokenizer_json_sha256=tokenizer_json_sha256,
        tokenizer_config_sha256=tokenizer_config_sha256,
        chat_template_sha256=chat_template_sha256,
        capture_profile_sha256=capture_profile_sha256,
        phase_activation_id=phase_activation_id,
        ledger_generation=ledger_generation,
    )
    raw_bytes = _canonical_json_bytes(payload)
    return StageCRuntimeActivationEnvelope(
        raw_bytes=raw_bytes,
        sha256=_sha256_bytes(raw_bytes),
    )


def replay_stagec_runtime_activation_envelope(
    envelope: Any,
) -> dict[str, Any]:
    """Reconstruct and return a detached payload after exact byte replay."""

    if type(envelope) is not StageCRuntimeActivationEnvelope:
        _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    payload = _replay_envelope_payload(envelope.raw_bytes)
    if envelope.sha256 != _sha256_bytes(envelope.raw_bytes):
        _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    # A strict JSON round trip returns a detached tree, not internal authority.
    return json.loads(envelope.raw_bytes.decode("utf-8", errors="strict"))


@dataclass(frozen=True, slots=True)
class StageCRuntimeActivationLedgerObservation:
    """Exact claimed ledger observation returned only by a trusted backend."""

    schema_version: str
    envelope_sha256: str
    logical_row_claim_sha256: str
    claim_operation_id: str
    backend_claim_id: str
    ledger_observation_sha256: str
    phase_activation_id: str
    case_id: str
    case_execution_ordinal: int
    ledger_generation: int
    prior_claim_state: str
    claim_state: str
    claimed_now: bool

    def __post_init__(self) -> None:
        if self.schema_version != STAGEC_RUNTIME_LEDGER_OBSERVATION_SCHEMA:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        _require_sha256(self.envelope_sha256)
        _require_sha256(self.logical_row_claim_sha256)
        _require_sha256(self.claim_operation_id)
        _require_text(self.backend_claim_id, identifier=True)
        _require_sha256(self.ledger_observation_sha256)
        _require_text(self.phase_activation_id, identifier=True)
        _require_text(self.case_id, identifier=True)
        _require_int(self.case_execution_ordinal, minimum=1)
        if self.case_execution_ordinal > _STAGEC_ROW_COUNT:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        _require_int(self.ledger_generation, minimum=1)
        if (
            type(self.prior_claim_state) is not str
            or self.prior_claim_state != _UNCLAIMED_STATE
        ):
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        if type(self.claim_state) is not str or self.claim_state != _CLAIMED_STATE:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        if type(self.claimed_now) is not bool or self.claimed_now is not True:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)


@dataclass(frozen=True, slots=True)
class StageCRuntimeActivationTerminalObservation:
    """Exact durable terminalization acknowledgement from the same backend."""

    schema_version: str
    envelope_sha256: str
    backend_claim_id: str
    ledger_observation_sha256: str
    fresh_trust_observation_sha256: str
    terminal_observation_sha256: str
    phase_activation_id: str
    ledger_generation: int
    terminal_state: str

    def __post_init__(self) -> None:
        if self.schema_version != STAGEC_RUNTIME_TERMINAL_OBSERVATION_SCHEMA:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        _require_sha256(self.envelope_sha256)
        _require_text(self.backend_claim_id, identifier=True)
        _require_sha256(self.ledger_observation_sha256)
        _require_sha256(self.fresh_trust_observation_sha256)
        _require_sha256(self.terminal_observation_sha256)
        _require_text(self.phase_activation_id, identifier=True)
        _require_int(self.ledger_generation, minimum=1)
        allowed = {
            _REDEEMED_TERMINAL_STATE,
            StageCModelCallInvalidationDisposition.REJECTED.value,
            StageCModelCallInvalidationDisposition.INDETERMINATE.value,
        }
        if type(self.terminal_state) is not str or self.terminal_state not in allowed:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)


@dataclass(frozen=True, slots=True)
class StageCRuntimeActivationAmbiguousTerminalObservation:
    """Durable tombstone receipt for an unusable backend claim result."""

    schema_version: str
    envelope_sha256: str
    logical_row_claim_sha256: str
    claim_operation_id: str
    terminal_observation_sha256: str
    tenant_id: str
    phase_activation_id: str
    attempt_subject_sha256: str
    case_id: str
    case_execution_ordinal: int
    prior_ledger_generation: int
    ledger_generation: int
    ambiguity_reason: str
    terminal_state: str
    tombstoned_now: bool

    def __post_init__(self) -> None:
        if (
            self.schema_version
            != STAGEC_RUNTIME_AMBIGUOUS_TERMINAL_OBSERVATION_SCHEMA
        ):
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        _require_sha256(self.envelope_sha256)
        _require_sha256(self.logical_row_claim_sha256)
        _require_sha256(self.claim_operation_id)
        _require_sha256(self.terminal_observation_sha256)
        _require_text(self.tenant_id, identifier=True)
        _require_text(self.phase_activation_id, identifier=True)
        _require_sha256(self.attempt_subject_sha256)
        _require_text(self.case_id, identifier=True)
        _require_int(self.case_execution_ordinal, minimum=1)
        if self.case_execution_ordinal > _STAGEC_ROW_COUNT:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        _require_int(self.prior_ledger_generation, minimum=1)
        _require_int(self.ledger_generation, minimum=1)
        if self.ledger_generation <= self.prior_ledger_generation:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        if (
            type(self.ambiguity_reason) is not str
            or self.ambiguity_reason
            not in {
                reason.value for reason in StageCRuntimeActivationAmbiguityReason
            }
        ):
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        if (
            type(self.terminal_state) is not str
            or self.terminal_state
            != StageCModelCallInvalidationDisposition.INDETERMINATE.value
        ):
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        if type(self.tombstoned_now) is not bool or self.tombstoned_now is not True:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)


class StageCModelCallPermit:
    """Opaque, process-sealed capability; direct construction is disabled."""

    __slots__ = ("__nonce", "__process_seal", "__weakref__")

    def __new__(cls, *_args: Any, **_kwargs: Any) -> StageCModelCallPermit:
        raise TypeError("StageCModelCallPermit cannot be constructed directly")

    def __init_subclass__(cls, **_kwargs: Any) -> None:
        raise TypeError("StageCModelCallPermit cannot be subclassed")

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("StageCModelCallPermit is immutable")

    def __getattribute__(self, name: str) -> Any:
        if name in {
            "_StageCModelCallPermit__nonce",
            "_StageCModelCallPermit__process_seal",
        }:
            raise AttributeError("StageCModelCallPermit is opaque")
        return object.__getattribute__(self, name)

    def __repr__(self) -> str:
        return "<StageCModelCallPermit opaque process-local capability>"

    def __copy__(self) -> None:
        raise TypeError("StageCModelCallPermit cannot be copied")

    def __deepcopy__(self, _memo: Any) -> None:
        raise TypeError("StageCModelCallPermit cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("StageCModelCallPermit cannot be serialized")

    def __reduce_ex__(self, _protocol: int) -> None:
        raise TypeError("StageCModelCallPermit cannot be serialized")


class _UnavailableStageCRuntimeTrustBackend:
    """Literal no-backend sentinel.  Its methods must never be consulted."""

    __slots__ = ()


_UNAVAILABLE_TRUST_BACKEND = _UnavailableStageCRuntimeTrustBackend()

# There is intentionally no public registration API and no positive backend.
# Deployment assembly may replace these private values with a reviewed exact
# backend type/instance.  Tests monkeypatch them to exercise the closed seam.
_REGISTERED_WORKER_TRUST_BACKEND_TYPES: tuple[type[object], ...] = ()
_WORKER_TRUST_BACKEND: object = _UNAVAILABLE_TRUST_BACKEND

_PROCESS_SEAL = object()
_CLAIM_NAMESPACE_SHA256 = secrets.token_hex(32).upper()
_PERMIT_LOCK = threading.RLock()


@dataclass(slots=True)
class _PermitRecord:
    permit: StageCModelCallPermit
    nonce: object
    envelope: StageCRuntimeActivationEnvelope
    backend: object
    backend_type: type[object]
    observation: StageCRuntimeActivationLedgerObservation
    envelope_seal: tuple[bytes, str]
    observation_seal: tuple[Any, ...]
    state: str
    terminal_observation: StageCRuntimeActivationTerminalObservation | None


_PERMIT_RECORDS: dict[int, _PermitRecord] = {}
_BACKEND_CLAIMS: set[tuple[type[object], str]] = set()
_ENVELOPE_CLAIMS: set[tuple[str, bytes]] = set()
_LOGICAL_ROW_CLAIMS: set[tuple[str, str, str]] = set()
_ATTEMPT_SUBJECT_CLAIMS: set[tuple[str, str]] = set()
_AMBIGUOUS_TERMINALS: dict[
    tuple[str, str, str],
    StageCRuntimeActivationAmbiguousTerminalObservation,
] = {}


_LEDGER_OBSERVATION_FIELDS = (
    "schema_version",
    "envelope_sha256",
    "logical_row_claim_sha256",
    "claim_operation_id",
    "backend_claim_id",
    "ledger_observation_sha256",
    "phase_activation_id",
    "case_id",
    "case_execution_ordinal",
    "ledger_generation",
    "prior_claim_state",
    "claim_state",
    "claimed_now",
)
_TERMINAL_OBSERVATION_FIELDS = (
    "schema_version",
    "envelope_sha256",
    "backend_claim_id",
    "ledger_observation_sha256",
    "fresh_trust_observation_sha256",
    "terminal_observation_sha256",
    "phase_activation_id",
    "ledger_generation",
    "terminal_state",
)
_AMBIGUOUS_TERMINAL_OBSERVATION_FIELDS = (
    "schema_version",
    "envelope_sha256",
    "logical_row_claim_sha256",
    "claim_operation_id",
    "terminal_observation_sha256",
    "tenant_id",
    "phase_activation_id",
    "attempt_subject_sha256",
    "case_id",
    "case_execution_ordinal",
    "prior_ledger_generation",
    "ledger_generation",
    "ambiguity_reason",
    "terminal_state",
    "tombstoned_now",
)


def _snapshot_envelope(
    envelope: Any,
) -> StageCRuntimeActivationEnvelope:
    """Detach exact envelope values and reject any torn snapshot."""

    if type(envelope) is not StageCRuntimeActivationEnvelope:
        _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    try:
        raw_bytes = envelope.raw_bytes
        digest = envelope.sha256
        snapshot = StageCRuntimeActivationEnvelope(
            raw_bytes=raw_bytes,
            sha256=digest,
        )
        replay_stagec_runtime_activation_envelope(snapshot)
        if (
            type(envelope.raw_bytes) is not bytes
            or type(envelope.sha256) is not str
            or envelope.raw_bytes != raw_bytes
            or envelope.sha256 != digest
        ):
            _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    except StageCRuntimeActivationError:
        raise
    except Exception as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.INVALID_ENVELOPE
        ) from exc
    return snapshot


def _logical_row_claim_key(
    payload: dict[str, Any],
) -> tuple[str, str, str]:
    try:
        principal = payload["runtime_principal"]
        authorization = payload["runtime_authorization"]
        attempt = payload["attempt"]
        key = (
            principal["tenant_id"],
            authorization["phase_activation_id"],
            attempt["attempt_subject_sha256"],
        )
        if (
            type(key[0]) is not str
            or type(key[1]) is not str
            or type(key[2]) is not str
        ):
            _fail(StageCRuntimeActivationErrorCode.INVALID_ENVELOPE)
    except StageCRuntimeActivationError:
        raise
    except Exception as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.INVALID_ENVELOPE
        ) from exc
    return key


def _logical_row_claim_sha256(payload: dict[str, Any]) -> str:
    tenant_id, phase_activation_id, attempt_subject_sha256 = (
        _logical_row_claim_key(payload)
    )
    return _sha256_bytes(
        _canonical_json_bytes(
            {
                "attempt_subject_sha256": attempt_subject_sha256,
                "phase_activation_id": phase_activation_id,
                "tenant_id": tenant_id,
            }
        )
    )


def _attempt_subject_claim_key(payload: dict[str, Any]) -> tuple[str, str]:
    tenant_id, _phase_activation_id, attempt_subject_sha256 = (
        _logical_row_claim_key(payload)
    )
    return tenant_id, attempt_subject_sha256


def _claim_operation_id(
    envelope: StageCRuntimeActivationEnvelope,
    payload: dict[str, Any],
) -> str:
    return _sha256_bytes(
        _canonical_json_bytes(
            {
                "claim_namespace_sha256": _CLAIM_NAMESPACE_SHA256,
                "domain": "cas_harness.stagec.worker_runtime_claim_operation.v1",
                "envelope_sha256": envelope.sha256,
                "logical_row_claim_sha256": _logical_row_claim_sha256(payload),
            }
        )
    )


def _ledger_observation_values(observation: Any) -> tuple[Any, ...]:
    try:
        return tuple(
            object.__getattribute__(observation, name)
            for name in _LEDGER_OBSERVATION_FIELDS
        )
    except Exception as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc


def _snapshot_ledger_observation(
    observation: Any,
) -> StageCRuntimeActivationLedgerObservation:
    """Retain no backend-owned carrier, even when frozen APIs are bypassed."""

    if type(observation) is not StageCRuntimeActivationLedgerObservation:
        _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    try:
        values = _ledger_observation_values(observation)
        snapshot = StageCRuntimeActivationLedgerObservation(
            **dict(zip(_LEDGER_OBSERVATION_FIELDS, values, strict=True))
        )
        if _ledger_observation_values(observation) != values:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    except StageCRuntimeActivationError as exc:
        if exc.code == StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION.value:
            raise
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc
    except Exception as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc
    return snapshot


def _terminal_observation_values(terminal: Any) -> tuple[Any, ...]:
    try:
        return tuple(
            object.__getattribute__(terminal, name)
            for name in _TERMINAL_OBSERVATION_FIELDS
        )
    except Exception as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc


def _snapshot_terminal_observation(
    terminal: Any,
) -> StageCRuntimeActivationTerminalObservation:
    if type(terminal) is not StageCRuntimeActivationTerminalObservation:
        _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    try:
        values = _terminal_observation_values(terminal)
        snapshot = StageCRuntimeActivationTerminalObservation(
            **dict(zip(_TERMINAL_OBSERVATION_FIELDS, values, strict=True))
        )
        if _terminal_observation_values(terminal) != values:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    except StageCRuntimeActivationError as exc:
        if exc.code == StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION.value:
            raise
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc
    except Exception as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc
    return snapshot


def _ambiguous_terminal_observation_values(
    terminal: Any,
) -> tuple[Any, ...]:
    try:
        return tuple(
            object.__getattribute__(terminal, name)
            for name in _AMBIGUOUS_TERMINAL_OBSERVATION_FIELDS
        )
    except Exception as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc


def _snapshot_ambiguous_terminal_observation(
    terminal: Any,
) -> StageCRuntimeActivationAmbiguousTerminalObservation:
    if type(terminal) is not StageCRuntimeActivationAmbiguousTerminalObservation:
        _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    try:
        values = _ambiguous_terminal_observation_values(terminal)
        snapshot = StageCRuntimeActivationAmbiguousTerminalObservation(
            **dict(
                zip(
                    _AMBIGUOUS_TERMINAL_OBSERVATION_FIELDS,
                    values,
                    strict=True,
                )
            )
        )
        if _ambiguous_terminal_observation_values(terminal) != values:
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    except StageCRuntimeActivationError as exc:
        if exc.code == StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION.value:
            raise
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc
    except Exception as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc
    return snapshot


def _sealed_record_inputs(
    record: _PermitRecord,
) -> tuple[StageCRuntimeActivationEnvelope, StageCRuntimeActivationLedgerObservation]:
    """Rebuild private call carriers and prove the retained seals are intact."""

    try:
        if (
            type(record.envelope_seal) is not tuple
            or len(record.envelope_seal) != 2
            or type(record.observation_seal) is not tuple
            or len(record.observation_seal) != len(_LEDGER_OBSERVATION_FIELDS)
            or type(record.envelope) is not StageCRuntimeActivationEnvelope
            or type(record.observation) is not StageCRuntimeActivationLedgerObservation
        ):
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        raw_bytes, digest = record.envelope_seal
        sealed_envelope = StageCRuntimeActivationEnvelope(
            raw_bytes=raw_bytes,
            sha256=digest,
        )
        sealed_payload = replay_stagec_runtime_activation_envelope(sealed_envelope)
        sealed_observation = StageCRuntimeActivationLedgerObservation(
            **dict(
                zip(
                    _LEDGER_OBSERVATION_FIELDS,
                    record.observation_seal,
                    strict=True,
                )
            )
        )
        if (
            record.envelope.raw_bytes != raw_bytes
            or record.envelope.sha256 != digest
            or _ledger_observation_values(record.observation)
            != record.observation_seal
            or sealed_observation.envelope_sha256 != digest
            or sealed_observation.logical_row_claim_sha256
            != _logical_row_claim_sha256(sealed_payload)
        ):
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    except StageCRuntimeActivationError:
        raise
    except Exception as exc:
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc
    # Return fresh carriers.  The backend can never receive either retained
    # object or the immutable seal tuple stored on the permit record.
    return (
        _snapshot_envelope(sealed_envelope),
        _snapshot_ledger_observation(sealed_observation),
    )


def _selected_backend() -> tuple[object, type[object]]:
    backend = _WORKER_TRUST_BACKEND
    backend_type = type(backend)
    if backend is _UNAVAILABLE_TRUST_BACKEND:
        _fail(StageCRuntimeActivationErrorCode.BACKEND_UNAVAILABLE)
    allowed = _REGISTERED_WORKER_TRUST_BACKEND_TYPES
    if (
        type(allowed) is not tuple
        or not allowed
        or any(type(item) is not type for item in allowed)
        or len(set(allowed)) != len(allowed)
        or not any(backend_type is item for item in allowed)
    ):
        _fail(StageCRuntimeActivationErrorCode.BACKEND_NOT_REGISTERED)
    return backend, backend_type


def _backend_method(backend_type: type[object], name: str) -> Any:
    method = backend_type.__dict__.get(name)
    if not callable(method):
        _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    return method


def _terminalize_ambiguous_claim_locked(
    *,
    backend: object,
    backend_type: type[object],
    envelope: StageCRuntimeActivationEnvelope,
    payload: dict[str, Any],
    claim_operation_id: str,
    reason: StageCRuntimeActivationAmbiguityReason,
) -> None:
    """Durably tombstone a possibly claimed row without backend output IDs.

    The exact backend contract may CAS only ``UNCLAIMED`` or a claim carrying
    this control-owned ``claim_operation_id`` to ``INDETERMINATE``.  It must
    never terminalize a claim won by another process operation.
    """

    failure_code = (
        StageCRuntimeActivationErrorCode.BACKEND_AMBIGUOUS_TERMINALIZATION_FAILED
    )
    try:
        if type(reason) is not StageCRuntimeActivationAmbiguityReason:
            _fail(failure_code)
        logical_row_key = _logical_row_claim_key(payload)
        tenant_id, phase_activation_id, attempt_subject_sha256 = logical_row_key
        row_digest = _logical_row_claim_sha256(payload)
        attempt = payload["attempt"]
        prior_generation = payload["runtime_authorization"]["ledger_generation"]
        allowed = _REGISTERED_WORKER_TRUST_BACKEND_TYPES
        if (
            type(backend) is not backend_type
            or type(allowed) is not tuple
            or not allowed
            or any(type(item) is not type for item in allowed)
            or not any(backend_type is item for item in allowed)
        ):
            _fail(failure_code)
        terminalize = _backend_method(
            backend_type,
            "terminalize_ambiguous_stagec_runtime_activation_claim",
        )
        terminal = terminalize(
            backend,
            envelope_sha256=envelope.sha256,
            logical_row_claim_key=logical_row_key,
            logical_row_claim_sha256=row_digest,
            claim_operation_id=claim_operation_id,
            tenant_id=tenant_id,
            phase_activation_id=phase_activation_id,
            attempt_subject_sha256=attempt_subject_sha256,
            case_id=attempt["case_id"],
            case_execution_ordinal=attempt["case_execution_ordinal"],
            prior_ledger_generation=prior_generation,
            ambiguity_reason=reason.value,
            terminal_state=(
                StageCModelCallInvalidationDisposition.INDETERMINATE.value
            ),
        )
        terminal = _snapshot_ambiguous_terminal_observation(terminal)
        if (
            terminal.envelope_sha256 != envelope.sha256
            or terminal.logical_row_claim_sha256 != row_digest
            or terminal.claim_operation_id != claim_operation_id
            or terminal.tenant_id != tenant_id
            or terminal.phase_activation_id != phase_activation_id
            or terminal.attempt_subject_sha256 != attempt_subject_sha256
            or terminal.case_id != attempt["case_id"]
            or terminal.case_execution_ordinal
            != attempt["case_execution_ordinal"]
            or terminal.prior_ledger_generation < prior_generation
            or terminal.ledger_generation <= terminal.prior_ledger_generation
            or terminal.ambiguity_reason != reason.value
            or terminal.terminal_state
            != StageCModelCallInvalidationDisposition.INDETERMINATE.value
            or terminal.tombstoned_now is not True
            or logical_row_key in _AMBIGUOUS_TERMINALS
        ):
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    except BaseException as exc:
        raise StageCRuntimeActivationError(failure_code) from exc
    _AMBIGUOUS_TERMINALS[logical_row_key] = terminal


def _validate_ledger_observation(
    observation: Any,
    *,
    envelope: StageCRuntimeActivationEnvelope,
    claim_operation_id: str,
) -> StageCRuntimeActivationLedgerObservation:
    try:
        exact_observation = _snapshot_ledger_observation(observation)
        payload = replay_stagec_runtime_activation_envelope(envelope)
        if (
            exact_observation.envelope_sha256 != envelope.sha256
            or exact_observation.logical_row_claim_sha256
            != _logical_row_claim_sha256(payload)
            or exact_observation.claim_operation_id != claim_operation_id
            or exact_observation.phase_activation_id
            != payload["runtime_authorization"]["phase_activation_id"]
            or exact_observation.case_id != payload["attempt"]["case_id"]
            or exact_observation.case_execution_ordinal
            != payload["attempt"]["case_execution_ordinal"]
            or exact_observation.ledger_generation
            != payload["runtime_authorization"]["ledger_generation"]
        ):
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    except StageCRuntimeActivationError as exc:
        if exc.code == StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION.value:
            raise
        raise StageCRuntimeActivationError(
            StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
        ) from exc
    return exact_observation


def _new_permit_locked(
    *,
    envelope: StageCRuntimeActivationEnvelope,
    backend: object,
    backend_type: type[object],
    observation: StageCRuntimeActivationLedgerObservation,
) -> StageCModelCallPermit:
    claim_key = (backend_type, observation.backend_claim_id)
    if claim_key in _BACKEND_CLAIMS:
        _fail(StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM)
    # Never retain caller/backend-owned frozen dataclasses.  ``object.__setattr__``
    # can bypass their public immutability, so reconstruct both carriers and
    # seal their exact scalar values for every later terminalization.
    exact_envelope = _snapshot_envelope(envelope)
    exact_observation = _snapshot_ledger_observation(observation)
    if exact_observation.envelope_sha256 != exact_envelope.sha256:
        _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    nonce = object()
    permit = object.__new__(StageCModelCallPermit)
    object.__setattr__(permit, "_StageCModelCallPermit__nonce", nonce)
    object.__setattr__(permit, "_StageCModelCallPermit__process_seal", _PROCESS_SEAL)
    record = _PermitRecord(
        permit=permit,
        nonce=nonce,
        envelope=exact_envelope,
        backend=backend,
        backend_type=backend_type,
        observation=exact_observation,
        envelope_seal=(exact_envelope.raw_bytes, exact_envelope.sha256),
        observation_seal=_ledger_observation_values(exact_observation),
        state="ACTIVE_UNREDEEMED",
        terminal_observation=None,
    )
    _PERMIT_RECORDS[id(permit)] = record
    _BACKEND_CLAIMS.add(claim_key)
    return permit


def acquire_stagec_model_call_permit(
    *,
    runtime_activation_envelope: StageCRuntimeActivationEnvelope,
) -> StageCModelCallPermit:
    """Authenticate and claim one exact row permit using module-owned trust."""

    exact_envelope = _snapshot_envelope(runtime_activation_envelope)
    exact_payload = replay_stagec_runtime_activation_envelope(exact_envelope)
    logical_row_key = _logical_row_claim_key(exact_payload)
    attempt_subject_key = _attempt_subject_claim_key(exact_payload)
    claim_operation_id = _claim_operation_id(exact_envelope, exact_payload)
    backend, backend_type = _selected_backend()
    authenticate = _backend_method(
        backend_type,
        "authenticate_and_claim_stagec_runtime_activation",
    )
    with _PERMIT_LOCK:
        envelope_key = (exact_envelope.sha256, exact_envelope.raw_bytes)
        if (
            envelope_key in _ENVELOPE_CLAIMS
            or logical_row_key in _LOGICAL_ROW_CLAIMS
            or attempt_subject_key in _ATTEMPT_SUBJECT_CLAIMS
        ):
            _fail(StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM)
        # Reserve before external dispatch and never release.  Once a backend
        # claim might have happened, any rejection, exception, or malformed
        # acknowledgement is ambiguous and cannot become a retry oracle.
        _ENVELOPE_CLAIMS.add(envelope_key)
        _LOGICAL_ROW_CLAIMS.add(logical_row_key)
        _ATTEMPT_SUBJECT_CLAIMS.add(attempt_subject_key)
        backend_envelope = _snapshot_envelope(exact_envelope)
        try:
            observation = authenticate(
                backend,
                envelope=backend_envelope,
                claim_operation_id=claim_operation_id,
            )
        except StageCRuntimeActivationError as exc:
            _terminalize_ambiguous_claim_locked(
                backend=backend,
                backend_type=backend_type,
                envelope=exact_envelope,
                payload=exact_payload,
                claim_operation_id=claim_operation_id,
                reason=(
                    StageCRuntimeActivationAmbiguityReason.AUTHENTICATE_EXCEPTION
                ),
            )
            raise StageCRuntimeActivationError(
                StageCRuntimeActivationErrorCode.BACKEND_REJECTED
            ) from exc
        except BaseException as exc:
            _terminalize_ambiguous_claim_locked(
                backend=backend,
                backend_type=backend_type,
                envelope=exact_envelope,
                payload=exact_payload,
                claim_operation_id=claim_operation_id,
                reason=(
                    StageCRuntimeActivationAmbiguityReason.AUTHENTICATE_EXCEPTION
                ),
            )
            raise StageCRuntimeActivationError(
                StageCRuntimeActivationErrorCode.BACKEND_REJECTED
            ) from exc
        try:
            checked_backend_envelope = _snapshot_envelope(backend_envelope)
        except StageCRuntimeActivationError as exc:
            _terminalize_ambiguous_claim_locked(
                backend=backend,
                backend_type=backend_type,
                envelope=exact_envelope,
                payload=exact_payload,
                claim_operation_id=claim_operation_id,
                reason=(
                    StageCRuntimeActivationAmbiguityReason.BACKEND_ENVELOPE_MUTATION
                ),
            )
            raise StageCRuntimeActivationError(
                StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION
            ) from exc
        if (
            checked_backend_envelope.raw_bytes != exact_envelope.raw_bytes
            or checked_backend_envelope.sha256 != exact_envelope.sha256
        ):
            _terminalize_ambiguous_claim_locked(
                backend=backend,
                backend_type=backend_type,
                envelope=exact_envelope,
                payload=exact_payload,
                claim_operation_id=claim_operation_id,
                reason=(
                    StageCRuntimeActivationAmbiguityReason.BACKEND_ENVELOPE_MUTATION
                ),
            )
            _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
        try:
            observation = _validate_ledger_observation(
                observation,
                envelope=exact_envelope,
                claim_operation_id=claim_operation_id,
            )
        except BaseException:
            _terminalize_ambiguous_claim_locked(
                backend=backend,
                backend_type=backend_type,
                envelope=exact_envelope,
                payload=exact_payload,
                claim_operation_id=claim_operation_id,
                reason=(
                    StageCRuntimeActivationAmbiguityReason.MALFORMED_LEDGER_OBSERVATION
                ),
            )
            raise
        try:
            return _new_permit_locked(
                envelope=exact_envelope,
                backend=backend,
                backend_type=backend_type,
                observation=observation,
            )
        except StageCRuntimeActivationError as exc:
            reason = (
                StageCRuntimeActivationAmbiguityReason.DUPLICATE_RETURNED_CLAIM_ID
                if exc.code
                == StageCRuntimeActivationErrorCode.DUPLICATE_BACKEND_CLAIM.value
                else StageCRuntimeActivationAmbiguityReason.MALFORMED_LEDGER_OBSERVATION
            )
            _terminalize_ambiguous_claim_locked(
                backend=backend,
                backend_type=backend_type,
                envelope=exact_envelope,
                payload=exact_payload,
                claim_operation_id=claim_operation_id,
                reason=reason,
            )
            raise


def _permit_record_locked(permit: Any) -> _PermitRecord:
    if type(permit) is not StageCModelCallPermit:
        _fail(StageCRuntimeActivationErrorCode.INVALID_PERMIT)
    record = _PERMIT_RECORDS.get(id(permit))
    if record is None or record.permit is not permit:
        _fail(StageCRuntimeActivationErrorCode.INVALID_PERMIT)
    try:
        nonce = object.__getattribute__(
            permit,
            "_StageCModelCallPermit__nonce",
        )
        process_seal = object.__getattribute__(
            permit,
            "_StageCModelCallPermit__process_seal",
        )
    except AttributeError:
        _fail(StageCRuntimeActivationErrorCode.INVALID_PERMIT)
    if nonce is not record.nonce or process_seal is not _PROCESS_SEAL:
        # A bypass mutation irreversibly poisons and durably terminalizes the
        # locally registered permit before its integrity failure escapes.
        _terminalize_locked(
            record,
            terminal_state=(
                StageCModelCallInvalidationDisposition.INDETERMINATE.value
            ),
        )
        _fail(StageCRuntimeActivationErrorCode.INVALID_PERMIT)
    if record.state == _REDEEMED_TERMINAL_STATE:
        _fail(StageCRuntimeActivationErrorCode.PERMIT_ALREADY_REDEEMED)
    if record.state in {
        StageCModelCallInvalidationDisposition.REJECTED.value,
        StageCModelCallInvalidationDisposition.INDETERMINATE.value,
    }:
        _fail(StageCRuntimeActivationErrorCode.PERMIT_INVALIDATED)
    if record.state != "ACTIVE_UNREDEEMED":
        _fail(
            StageCRuntimeActivationErrorCode.PERMIT_TERMINALIZATION_INDETERMINATE
        )
    return record


def _matches_envelope_locked(
    record: _PermitRecord,
    candidate: Any,
) -> bool:
    if type(candidate) is not StageCRuntimeActivationEnvelope:
        return False
    try:
        replay_stagec_runtime_activation_envelope(candidate)
    except StageCRuntimeActivationError:
        return False
    return (
        candidate.sha256 == record.envelope.sha256
        and candidate.raw_bytes == record.envelope.raw_bytes
    )


def _validate_terminal_observation(
    terminal: Any,
    *,
    record: _PermitRecord,
    terminal_state: str,
) -> StageCRuntimeActivationTerminalObservation:
    terminal = _snapshot_terminal_observation(terminal)
    observed = record.observation
    if (
        terminal.envelope_sha256 != record.envelope.sha256
        or terminal.backend_claim_id != observed.backend_claim_id
        or terminal.ledger_observation_sha256
        != observed.ledger_observation_sha256
        or (
            terminal_state == _REDEEMED_TERMINAL_STATE
            and terminal.fresh_trust_observation_sha256
            == observed.ledger_observation_sha256
        )
        or terminal.phase_activation_id != observed.phase_activation_id
        or terminal.ledger_generation <= observed.ledger_generation
        or terminal.terminal_state != terminal_state
    ):
        _fail(StageCRuntimeActivationErrorCode.BACKEND_PROTOCOL_VIOLATION)
    return terminal


def _terminalize_locked(record: _PermitRecord, *, terminal_state: str) -> None:
    record.state = "TERMINALIZING"
    is_redemption = terminal_state == _REDEEMED_TERMINAL_STATE
    failure_code = (
        StageCRuntimeActivationErrorCode.BACKEND_REDEEM_REAUTHENTICATION_FAILED
        if is_redemption
        else StageCRuntimeActivationErrorCode.BACKEND_TERMINALIZATION_FAILED
    )
    try:
        backend_envelope, backend_observation = _sealed_record_inputs(record)
        allowed = _REGISTERED_WORKER_TRUST_BACKEND_TYPES
        if (
            type(record.backend) is not record.backend_type
            or type(allowed) is not tuple
            or not allowed
            or any(type(item) is not type for item in allowed)
            or not any(record.backend_type is item for item in allowed)
        ):
            _fail(failure_code)
        terminalize = _backend_method(
            record.backend_type,
            (
                "reauthenticate_and_redeem_stagec_runtime_activation_claim"
                if is_redemption
                else "terminalize_stagec_runtime_activation_claim"
            ),
        )
        terminal = terminalize(
            record.backend,
            envelope=backend_envelope,
            observation=backend_observation,
            terminal_state=terminal_state,
        )
        # A backend method receives only disposable clones.  Recheck both
        # retained seals after it returns before accepting any acknowledgement.
        _sealed_record_inputs(record)
        terminal = _validate_terminal_observation(
            terminal,
            record=record,
            terminal_state=terminal_state,
        )
        _sealed_record_inputs(record)
    except Exception as exc:
        record.state = "TERMINALIZATION_INDETERMINATE"
        raise StageCRuntimeActivationError(failure_code) from exc
    record.terminal_observation = terminal
    record.state = terminal_state


def _require_matching_active_record_locked(
    permit: Any,
    envelope: Any,
) -> _PermitRecord:
    record = _permit_record_locked(permit)
    if not _matches_envelope_locked(record, envelope):
        # Exact binding drift is a rejected pre-call claim, not a retry oracle.
        _terminalize_locked(
            record,
            terminal_state=StageCModelCallInvalidationDisposition.REJECTED.value,
        )
        _fail(StageCRuntimeActivationErrorCode.PERMIT_BINDING_MISMATCH)
    return record


def validate_stagec_model_call_permit(
    *,
    permit: StageCModelCallPermit,
    runtime_activation_envelope: StageCRuntimeActivationEnvelope,
) -> None:
    """Validate exact entry binding without redeeming a valid permit."""

    with _PERMIT_LOCK:
        _require_matching_active_record_locked(
            permit,
            runtime_activation_envelope,
        )


def redeem_stagec_model_call_permit(
    *,
    permit: StageCModelCallPermit,
    runtime_activation_envelope: StageCRuntimeActivationEnvelope,
) -> None:
    """Freshly authenticate and durably CAS to ``CALL_STARTED``.

    The exact registered backend method is required to reobserve trusted time
    and the authorization window, storage object version/checksum/retention,
    the worker lease, revocation state, and durable ledger generation.  It must
    perform a one-winner compare-and-swap to ``CALL_STARTED`` and return an
    exact acknowledgement with a fresh trust-observation digest.  Acquisition
    alone is never sufficient.  Any missing, stale, revoked, drifted, replayed,
    or indeterminate response burns the local permit without a model call.
    """

    with _PERMIT_LOCK:
        record = _require_matching_active_record_locked(
            permit,
            runtime_activation_envelope,
        )
        _terminalize_locked(record, terminal_state=_REDEEMED_TERMINAL_STATE)


def invalidate_stagec_model_call_permit(
    *,
    permit: StageCModelCallPermit,
    runtime_activation_envelope: StageCRuntimeActivationEnvelope,
    disposition: StageCModelCallInvalidationDisposition = (
        StageCModelCallInvalidationDisposition.INDETERMINATE
    ),
) -> None:
    """Terminalize a claimed permit after any pre-model-call capture failure."""

    if type(disposition) is not StageCModelCallInvalidationDisposition:
        _fail(
            StageCRuntimeActivationErrorCode.INVALID_INVALIDATION_DISPOSITION
        )
    with _PERMIT_LOCK:
        record = _require_matching_active_record_locked(
            permit,
            runtime_activation_envelope,
        )
        _terminalize_locked(record, terminal_state=disposition.value)


__all__ = [
    "AUTHORIZATION_PROJECTION_MEDIA_TYPE",
    "FREEZE_STATUS",
    "GATE5_STATUS",
    "GOVERNANCE_STATUS",
    "LICENSE_STATUS",
    "REQUEST_MEDIA_TYPE",
    "STAGEC_AUTHORIZATION_STATUS",
    "STAGEC_CAPTURE_ARTIFACT_ID_FIELDS",
    "STAGEC_DESIGN_STATUS",
    "STAGEC_EXECUTION_STATUS",
    "STAGEC_RUNTIME_ACTIVATION_SCHEMA",
    "STAGEC_RUNTIME_AMBIGUOUS_TERMINAL_OBSERVATION_SCHEMA",
    "STAGEC_RUNTIME_AUTHORITY_BOUNDARY",
    "STAGEC_RUNTIME_CAPABILITY_STATUS",
    "STAGEC_RUNTIME_LEDGER_OBSERVATION_SCHEMA",
    "STAGEC_RUNTIME_PURPOSE",
    "STAGEC_RUNTIME_TERMINAL_OBSERVATION_SCHEMA",
    "StageCModelCallInvalidationDisposition",
    "StageCModelCallPermit",
    "StageCRuntimeActivationAmbiguityReason",
    "StageCRuntimeActivationAmbiguousTerminalObservation",
    "StageCRuntimeActivationEnvelope",
    "StageCRuntimeActivationError",
    "StageCRuntimeActivationErrorCode",
    "StageCRuntimeActivationLedgerObservation",
    "StageCRuntimeActivationTerminalObservation",
    "acquire_stagec_model_call_permit",
    "build_stagec_runtime_activation_envelope",
    "invalidate_stagec_model_call_permit",
    "redeem_stagec_model_call_permit",
    "replay_stagec_runtime_activation_envelope",
    "validate_stagec_model_call_permit",
]
