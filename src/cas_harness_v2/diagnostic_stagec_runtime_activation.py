"""Fail-closed live control plane for Stage C runtime activation.

This module deliberately creates no serialized authority carrier and ships no
positive production backend.  It joins an exact, prospectively admitted Stage
C prerequisite bundle to the exact plan, execution contract, phase roster,
and live provider/issuer observations.  The resulting process-local objects
are control-plane interlocks only.  They do not alter the authority literals
on any existing artifact and they do not authorize a worker or a model call.

The v1 Stage C authorization fixes ``canary_count`` to zero.  Consequently a
startup forward canary is forbidden: one newly consumed phase nonce moves the
control plane directly to ``ROWS_ENABLED`` and only exact roster rows may then
compete for one durable dispatch claim apiece.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
import secrets
import threading
from typing import Any

from ._strict_json import canonical_sha256, sha256_bytes
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_int,
    expect_machine_id,
    expect_sha256,
    expect_string,
    expect_timestamp,
)
from .diagnostic_execution_protocol import (
    DiagnosticChildExecutionBindingArtifact,
    DiagnosticWorkerAuthorizationV2Artifact,
    load_diagnostic_child_execution_binding,
    load_diagnostic_stagec_execution_contract,
    load_diagnostic_worker_authorization_v2,
)
from .diagnostic_lifecycle import (
    DiagnosticSharedPlanReplayContext,
    build_diagnostic_shared_plan_replay_context,
    derive_diagnostic_attempt_subject_sha256,
)
from .diagnostic_phase_coordinator import (
    DiagnosticPhaseCoordinator,
    DiagnosticPhaseRegistrationArtifact,
    load_diagnostic_phase_registration,
    load_diagnostic_phase_store_binding,
)
from .diagnostic_preregistration import (
    DiagnosticPreregistrationChain,
    load_diagnostic_preregistration,
)
from .diagnostic_prompt_context_inventory import StageCPromptContextReplayBundle
from .diagnostic_stagec_prerequisite_admission import (
    StageCPrerequisiteFactoryContext,
    require_stagec_prerequisite_admission_in_preregistration,
)
from .diagnostic_stagec_prerequisite_external_intake import (
    StageCExternalPrerequisiteBinding,
    load_stagec_external_prerequisite_binding,
)
from .diagnostic_study_protocol import (
    DIAGNOSTIC_CASE_COUNT,
    DiagnosticStudyRequestArtifact,
    load_diagnostic_split_inventory,
    load_diagnostic_study_plan,
    load_diagnostic_study_request,
    load_stagec_capture_request,
)


STAGEC_RUNTIME_GATE_5_STATUS = "OPEN / KEEP_OPEN"
STAGEC_RUNTIME_STAGE_C_STATUS = "DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED"
STAGEC_RUNTIME_PROJECT_STATUS = "NOT LICENSED / HELD / NOT FROZEN"
STAGEC_RUNTIME_CONTROL_BOUNDARY = (
    "PROCESS_LOCAL_CONTROL_INTERLOCK_NOT_WORKER_OR_MODEL_CALL_AUTHORITY"
)
STAGEC_RUNTIME_SERIALIZED_AUTHORITY = "NONE"
STAGEC_RUNTIME_STARTUP_CANARY = "FORBIDDEN_AUTHORIZATION_CANARY_COUNT_ZERO"
STAGEC_RUNTIME_PREPARED = "PREPARED"
STAGEC_RUNTIME_ROWS_ENABLED = "ROWS_ENABLED"
STAGEC_RUNTIME_ACTIVATION_INDETERMINATE = "ACTIVATION_INDETERMINATE"
STAGEC_RUNTIME_PERMIT_UNREDEEMED = "UNREDEEMED"
STAGEC_RUNTIME_PERMIT_REDEEMED = "REDEEMED"
STAGEC_RUNTIME_PERMIT_INVALIDATED = "INVALIDATED"
STAGEC_RUNTIME_PERMIT_INDETERMINATE = "INDETERMINATE"

STAGEC_RUNTIME_INVALIDATION_REASONS = (
    "AMBIGUOUS_DURABLE_CLAIM_RESULT",
    "LOCAL_LIFECYCLE_CAS_FAILED",
    "POST_CLAIM_PRE_DISPATCH_FAILURE",
    "WORKER_BINDING_RECHECK_FAILED",
    "DISPATCH_PATH_UNAVAILABLE",
)
_INVALIDATION_REASON_SET = frozenset(STAGEC_RUNTIME_INVALIDATION_REASONS)

STAGEC_RUNTIME_ACTIVATION_ERROR_CODES = (
    "PREPARATION_INVALID",
    "EXTERNAL_BINDING_REPLAY_FAILED",
    "PREREGISTRATION_ADMISSION_FAILED",
    "SHARED_PLAN_REPLAY_FAILED",
    "PHASE_REGISTRATION_REPLAY_FAILED",
    "ROSTER_INVALID",
    "MODEL_CAPTURE_TARGET_INVALID",
    "TARGET_BINDING_MISMATCH",
    "BACKEND_UNAVAILABLE",
    "BACKEND_NOT_TRUSTED",
    "BACKEND_OPERATION_FAILED",
    "PHASE_ALREADY_ACTIVATED",
    "PHASE_ACTIVATION_INDETERMINATE",
    "PHASE_OBSERVATION_INVALID",
    "PHASE_BINDING_MISMATCH",
    "PHASE_TRUSTED_TIME_OUTSIDE_WINDOW",
    "PHASE_STORAGE_RETENTION_INSUFFICIENT",
    "PHASE_NONCE_NOT_NEWLY_CONSUMED",
    "PHASE_NOT_ROWS_ENABLED",
    "STARTUP_CANARY_FORBIDDEN",
    "ATTEMPT_BINDING_INVALID",
    "ATTEMPT_OUTSIDE_ROSTER",
    "ATTEMPT_ALREADY_CLAIMED",
    "ATTEMPT_CLAIM_INDETERMINATE",
    "CLAIM_OBSERVATION_INVALID",
    "CLAIM_BINDING_MISMATCH",
    "CLAIM_NOT_NEWLY_WON",
    "AMBIGUOUS_CLAIM_TERMINAL_OBSERVATION_INVALID",
    "AMBIGUOUS_CLAIM_TERMINAL_BINDING_MISMATCH",
    "AMBIGUOUS_CLAIM_TERMINALIZATION_FAILED",
    "WORKER_LEASE_INVALID",
    "PERMIT_INVALID",
    "PERMIT_BINDING_MISMATCH",
    "PERMIT_ALREADY_REDEEMED",
    "PERMIT_INVALIDATED",
    "PERMIT_INDETERMINATE",
    "INVALIDATION_REASON_INVALID",
    "INVALIDATION_OBSERVATION_INVALID",
    "INVALIDATION_BINDING_MISMATCH",
    "CLAIM_INVALIDATION_FAILED",
)
_ERROR_CODE_SET = frozenset(STAGEC_RUNTIME_ACTIVATION_ERROR_CODES)


class StageCRuntimeActivationError(RuntimeError):
    """One fail-closed runtime-activation error with a closed reason code."""

    __slots__ = ("error_code",)

    def __init__(self, error_code: str, message: str) -> None:
        if error_code not in _ERROR_CODE_SET:
            raise ValueError("runtime activation error code is outside the closed set")
        super().__init__(f"{error_code}: {message}")
        self.error_code = error_code


def _fail(error_code: str, message: str) -> None:
    raise StageCRuntimeActivationError(error_code, message)


def _time(value: str, field: str) -> datetime:
    try:
        timestamp = expect_timestamp(value, field)
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRuntimeActivationError(
            "PHASE_OBSERVATION_INVALID", f"{field} is not an exact UTC timestamp"
        ) from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or parsed.astimezone(timezone.utc).utcoffset() != timezone.utc.utcoffset(None)
    ):
        _fail("PHASE_OBSERVATION_INVALID", f"{field} is not timezone-aware UTC")
    return parsed


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _require_exact_ref(reference: Any, field: str) -> ArtifactRef:
    if type(reference) is not ArtifactRef:
        _fail("PHASE_OBSERVATION_INVALID", f"{field} must be an exact ArtifactRef")
    return reference


def _same_ref(left: ArtifactRef, right: ArtifactRef) -> bool:
    return type(left) is ArtifactRef and type(right) is ArtifactRef and left == right


def _machine(value: Any, field: str, *, claim: bool = False) -> str:
    try:
        return expect_machine_id(value, field)
    except (SchemaValidationError, TypeError, ValueError) as exc:
        code = "CLAIM_OBSERVATION_INVALID" if claim else "PHASE_OBSERVATION_INVALID"
        raise StageCRuntimeActivationError(code, f"{field} is invalid") from exc


def _sha(value: Any, field: str, *, claim: bool = False) -> str:
    try:
        return expect_sha256(value, field)
    except (SchemaValidationError, TypeError, ValueError) as exc:
        code = "CLAIM_OBSERVATION_INVALID" if claim else "PHASE_OBSERVATION_INVALID"
        raise StageCRuntimeActivationError(code, f"{field} is invalid") from exc


def _positive_int(value: Any, field: str, *, claim: bool = False) -> int:
    try:
        return expect_int(value, field, minimum=1)
    except (SchemaValidationError, TypeError, ValueError) as exc:
        code = "CLAIM_OBSERVATION_INVALID" if claim else "PHASE_OBSERVATION_INVALID"
        raise StageCRuntimeActivationError(code, f"{field} is invalid") from exc


@dataclass(frozen=True, slots=True, init=False, eq=False)
class StageCRuntimeModelCaptureTarget:
    model_identity_sha256: str
    capture_profile_sha256: str
    model_contract_sha256: str
    runtime_contract_sha256: str
    capture_contract_sha256: str
    target_sha256: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCRuntimeModelCaptureTarget is factory-only; use "
            "build_stagec_runtime_model_capture_target"
        )


@dataclass(frozen=True, slots=True, init=False, eq=False)
class StageCRuntimePreparation:
    external_binding: StageCExternalPrerequisiteBinding
    prerequisite_context: StageCPrerequisiteFactoryContext
    shared_plan_context: DiagnosticSharedPlanReplayContext
    phase_registration: DiagnosticPhaseRegistrationArtifact
    model_capture_target: StageCRuntimeModelCaptureTarget
    tenant_id: str
    roster_closure_sha256: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCRuntimePreparation is factory-only; use "
            "prepare_stagec_runtime_activation"
        )

    @property
    def control_state(self) -> str:
        return stagec_runtime_preparation_state(self)


@dataclass(frozen=True, slots=True, init=False, eq=False)
class StageCRuntimePhaseActivation:
    preparation: StageCRuntimePreparation
    observation: "StageCRuntimePhaseActivationObservation"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCRuntimePhaseActivation is backend-issued; use "
            "activate_stagec_runtime_phase"
        )

    @property
    def control_state(self) -> str:
        return stagec_runtime_phase_state(self)


@dataclass(frozen=True, slots=True, init=False, eq=False)
class StageCRuntimeDispatchPermit:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "StageCRuntimeDispatchPermit is claim-only; use "
            "ActivatedDiagnosticPhaseCoordinator.consume_attempt"
        )

    @property
    def control_state(self) -> str:
        return stagec_runtime_dispatch_permit_state(self)


@dataclass(frozen=True, slots=True)
class StageCRuntimeStorageObservation:
    authenticated_tenant_id: str
    authenticated_worker_id: str
    provider_id: str
    object_key: str
    object_version_id: str
    checksum_sha256: str
    byte_length: int
    retention_until: str
    trusted_time: str
    observation_generation: int


@dataclass(frozen=True, slots=True)
class StageCRuntimeIssuerAuthorizationObservation:
    authenticated_tenant_id: str
    authenticated_worker_id: str
    issuer_id: str
    authorization_id: str
    prospective_subject_sha256: str
    target_binding_sha256: str
    window_start: str
    window_end: str
    nonce_b64url: str
    nonce_state_before: str
    nonce_state_after: str
    nonce_consumed_now: bool
    ledger_generation: int
    phase_id: str
    phase_subject_sha256: str
    plan_sha256: str
    execution_contract_sha256: str
    admission_sha256: str


@dataclass(frozen=True, slots=True)
class StageCRuntimePhaseActivationObservation:
    storage: StageCRuntimeStorageObservation
    authorization: StageCRuntimeIssuerAuthorizationObservation
    registration_sha256: str
    roster_closure_sha256: str
    model_capture_target_sha256: str
    control_state: str


@dataclass(frozen=True, slots=True)
class StageCRuntimeWorkerLeaseObservation:
    lease_id: str
    authenticated_tenant_id: str
    authenticated_worker_id: str
    provider_id: str
    phase_id: str
    phase_subject_sha256: str
    issued_at: str
    not_before: str
    expires_at: str
    lease_generation: int
    state: str


@dataclass(frozen=True, slots=True)
class StageCRuntimeAttemptClaimObservation:
    storage: StageCRuntimeStorageObservation
    authorization: StageCRuntimeIssuerAuthorizationObservation
    worker_lease: StageCRuntimeWorkerLeaseObservation
    claim_id: str
    claim_operation_id: str
    claim_generation: int
    claim_state: str
    claimed_now: bool
    execution_ordinal: int
    study_request_sha256: str
    attempt_subject_sha256: str
    child_binding_sha256: str
    worker_authorization_sha256: str
    registration_sha256: str
    roster_closure_sha256: str
    model_capture_target_sha256: str


@dataclass(frozen=True, slots=True)
class StageCRuntimeAmbiguousClaimTerminalObservation:
    """Receipt for terminalizing a claim whose backend result was unusable.

    The receipt intentionally contains no backend-returned claim identifier.
    It is bound only to the control-owned operation identity and the sealed
    logical row, so malformed claim output can never steer terminalization.
    """

    claim_operation_id: str
    claim_state: str
    terminalized_now: bool
    execution_ordinal: int
    attempt_subject_sha256: str
    authenticated_tenant_id: str
    authenticated_worker_id: str
    phase_id: str
    phase_subject_sha256: str
    registration_sha256: str
    roster_closure_sha256: str
    model_capture_target_sha256: str
    invalidation_reason: str
    prior_ledger_generation: int
    ledger_generation: int


@dataclass(frozen=True, slots=True)
class StageCRuntimeAttemptInvalidationObservation:
    claim_id: str
    claim_generation: int
    claim_state: str
    invalidated_now: bool
    execution_ordinal: int
    attempt_subject_sha256: str
    authenticated_tenant_id: str
    authenticated_worker_id: str
    phase_id: str
    phase_subject_sha256: str
    invalidation_reason: str
    ledger_generation: int


@dataclass(frozen=True, slots=True)
class StageCRuntimePhaseActivationExpectation:
    tenant_id: str
    authenticated_worker_id: str
    phase_id: str
    phase_subject_sha256: str
    registration_ref: ArtifactRef
    roster_closure_sha256: str
    plan_ref: ArtifactRef
    execution_contract_ref: ArtifactRef
    admission_ref: ArtifactRef
    external_binding_report_ref: ArtifactRef
    target_binding_sha256: str
    prospective_subject_sha256: str
    authorization_id: str
    authorization_window_start: str
    authorization_window_end: str
    authorization_nonce_b64url: str
    corpus_ref: ArtifactRef
    storage_receipt_ref: ArtifactRef
    storage_object_version_id: str
    storage_checksum_sha256: str
    storage_byte_length: int
    storage_retention_until: str
    model_capture_target_sha256: str
    startup_canary_policy: str


@dataclass(frozen=True, slots=True)
class StageCRuntimeAttemptClaimExpectation:
    tenant_id: str
    phase_id: str
    phase_subject_sha256: str
    registration_ref: ArtifactRef
    roster_closure_sha256: str
    plan_ref: ArtifactRef
    execution_contract_ref: ArtifactRef
    admission_ref: ArtifactRef
    target_binding_sha256: str
    prospective_subject_sha256: str
    stagec_authorization_id: str
    stagec_authorization_window_start: str
    stagec_authorization_window_end: str
    stagec_authorization_nonce_b64url: str
    activation_provider_id: str
    activation_storage_object_key: str
    activation_storage_object_version_id: str
    activation_storage_checksum_sha256: str
    activation_storage_byte_length: int
    activation_storage_retention_until: str
    activation_storage_trusted_time: str
    activation_storage_observation_generation: int
    activation_issuer_id: str
    activation_ledger_generation: int
    execution_ordinal: int
    study_request_ref: ArtifactRef
    attempt_subject_sha256: str
    child_binding_ref: ArtifactRef
    worker_authorization_ref: ArtifactRef
    assigned_worker_id: str
    diagnostic_not_before: str
    diagnostic_expires_at: str
    run_nonce_b64url: str
    model_capture_target_sha256: str
    claim_operation_id: str


@dataclass(frozen=True, slots=True)
class StageCRuntimeAttemptInvalidationExpectation:
    tenant_id: str
    phase_id: str
    phase_subject_sha256: str
    execution_ordinal: int
    attempt_subject_sha256: str
    assigned_worker_id: str
    claim_id: str
    claim_generation: int
    invalidation_reason: str
    registration_sha256: str
    roster_closure_sha256: str
    model_capture_target_sha256: str


_BACKEND_EXPECTATION_TYPES = frozenset(
    {
        StageCRuntimePhaseActivationExpectation,
        StageCRuntimeAttemptClaimExpectation,
        StageCRuntimeAttemptInvalidationExpectation,
    }
)


def _backend_expectation_values(expectation: Any) -> tuple[Any, ...]:
    exact_type = type(expectation)
    if exact_type not in _BACKEND_EXPECTATION_TYPES:
        raise TypeError("backend expectation has an unrecognized exact type")
    return tuple(
        _ref_scalars(value) if type(value) is ArtifactRef else value
        for value in (getattr(expectation, item.name) for item in fields(exact_type))
    )


def _disposable_backend_expectation(expectation: Any) -> Any:
    """Deep-copy refs so a backend can never retain the private expectation."""

    exact_type = type(expectation)
    if exact_type not in _BACKEND_EXPECTATION_TYPES:
        raise TypeError("backend expectation has an unrecognized exact type")
    return exact_type(
        **{
            item.name: (
                _copy_ref(value) if type(value) is ArtifactRef else value
            )
            for item in fields(exact_type)
            for value in (getattr(expectation, item.name),)
        }
    )


def _require_disposable_expectation_unchanged(
    disposable: Any,
    before: tuple[Any, ...],
    *,
    error_code: str,
) -> None:
    try:
        unchanged = _backend_expectation_values(disposable) == before
    except Exception as exc:
        raise StageCRuntimeActivationError(
            error_code,
            "backend-mutated disposable expectation lost its exact closed shape",
        ) from exc
    if not unchanged:
        _fail(error_code, "backend mutated its disposable expectation")


@dataclass(frozen=True, slots=True)
class ActivatedDiagnosticAttemptConsumption:
    """One successful local CAS paired with its still-unredeemed control permit."""

    mutation: Any
    dispatch_permit: StageCRuntimeDispatchPermit
    control_boundary: str = STAGEC_RUNTIME_CONTROL_BOUNDARY


class StageCRuntimeActivationBackend:
    """Interface for an externally authenticated durable atomic backend.

    Defining this interface does not register a backend.  Exact backend types
    must additionally be admitted in the private build-time allowlist.
    """

    __slots__ = ()

    def activate_phase(
        self, expectation: StageCRuntimePhaseActivationExpectation
    ) -> StageCRuntimePhaseActivationObservation:
        raise NotImplementedError

    def claim_attempt(
        self, expectation: StageCRuntimeAttemptClaimExpectation
    ) -> StageCRuntimeAttemptClaimObservation:
        raise NotImplementedError

    def invalidate_attempt_claim(
        self, expectation: StageCRuntimeAttemptInvalidationExpectation
    ) -> StageCRuntimeAttemptInvalidationObservation:
        raise NotImplementedError

    def terminalize_ambiguous_attempt_claim(
        self,
        expectation: StageCRuntimeAttemptClaimExpectation,
        *,
        claim_operation_id: str,
        invalidation_reason: str,
    ) -> StageCRuntimeAmbiguousClaimTerminalObservation:
        """Atomically terminalize UNCLAIMED/this-operation CLAIMED to INDETERMINATE."""

        raise NotImplementedError


class UnavailableStageCRuntimeActivationBackend(StageCRuntimeActivationBackend):
    """The only built-in backend; it can never produce a positive result."""

    __slots__ = ()

    def activate_phase(self, expectation: StageCRuntimePhaseActivationExpectation):
        _fail("BACKEND_UNAVAILABLE", "no trusted runtime activation backend is installed")

    def claim_attempt(self, expectation: StageCRuntimeAttemptClaimExpectation):
        _fail("BACKEND_UNAVAILABLE", "no trusted runtime activation backend is installed")

    def invalidate_attempt_claim(
        self, expectation: StageCRuntimeAttemptInvalidationExpectation
    ):
        _fail("BACKEND_UNAVAILABLE", "no trusted runtime activation backend is installed")

    def terminalize_ambiguous_attempt_claim(
        self,
        expectation: StageCRuntimeAttemptClaimExpectation,
        *,
        claim_operation_id: str,
        invalidation_reason: str,
    ):
        del expectation, claim_operation_id, invalidation_reason
        _fail("BACKEND_UNAVAILABLE", "no trusted runtime activation backend is installed")


# Intentionally empty.  Production integration must review and install exact
# backend types in code; callers cannot register a backend at runtime.  Focused
# tests may monkeypatch this private immutable value with one deterministic
# backend type.
_TRUSTED_BACKEND_TYPES: frozenset[type[StageCRuntimeActivationBackend]] = frozenset()

# Production composition is restricted to the exact coordinator implementation.
# Focused wiring tests may replace this private immutable value with a fake type;
# there is no public runtime registration surface.
_ACTIVATED_COORDINATOR_TYPES: frozenset[type[Any]] = frozenset(
    {DiagnosticPhaseCoordinator}
)


@dataclass(slots=True)
class _TargetSeal:
    target: StageCRuntimeModelCaptureTarget
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _PhaseBindingSnapshot:
    """Detached authority inputs used to build the live phase expectation."""

    tenant_id: str
    phase_id: str
    phase_subject_sha256: str
    registration_ref: ArtifactRef
    roster_closure_sha256: str
    plan_ref: ArtifactRef
    execution_contract_ref: ArtifactRef
    admission_ref: ArtifactRef
    external_binding_report_ref: ArtifactRef
    target_binding_sha256: str
    prospective_subject_sha256: str
    authorization_id: str
    authorization_window_start: str
    authorization_window_end: str
    authorization_nonce_b64url: str
    corpus_ref: ArtifactRef
    storage_receipt_ref: ArtifactRef
    storage_object_version_id: str
    storage_checksum_sha256: str
    storage_byte_length: int
    storage_retention_until: str
    model_capture_target_sha256: str


@dataclass(frozen=True, slots=True)
class _ActivationBackendSnapshot:
    """Private scalar copy of the authenticated phase result used by row claims."""

    provider_id: str
    storage_object_key: str
    storage_object_version_id: str
    storage_checksum_sha256: str
    storage_byte_length: int
    storage_retention_until: str
    storage_trusted_time: str
    storage_observation_generation: int
    issuer_id: str
    ledger_generation: int


@dataclass(frozen=True, slots=True)
class _ClaimBackendSnapshot:
    claim_id: str
    claim_generation: int


@dataclass(slots=True)
class _PreparationSeal:
    preparation: StageCRuntimePreparation
    external_binding: StageCExternalPrerequisiteBinding
    prerequisite_context: StageCPrerequisiteFactoryContext
    shared_plan_context: DiagnosticSharedPlanReplayContext
    phase_registration: DiagnosticPhaseRegistrationArtifact
    private_shared_plan_context: DiagnosticSharedPlanReplayContext
    private_phase_registration: DiagnosticPhaseRegistrationArtifact
    model_capture_target: StageCRuntimeModelCaptureTarget
    phase_binding: _PhaseBindingSnapshot
    public_values: tuple[Any, ...]
    tenant_id: str
    roster_closure_sha256: str
    control_state: str
    lock: threading.RLock


@dataclass(slots=True)
class _ActivationSeal:
    activation: StageCRuntimePhaseActivation
    preparation_seal: _PreparationSeal
    backend: StageCRuntimeActivationBackend
    phase_expectation: StageCRuntimePhaseActivationExpectation
    observation: StageCRuntimePhaseActivationObservation
    observation_values: tuple[Any, ...]
    backend_snapshot: _ActivationBackendSnapshot
    claim_namespace_sha256: str
    control_state: str
    attempt_states: dict[str, str]
    lock: threading.RLock


@dataclass(slots=True)
class _PermitSeal:
    permit: StageCRuntimeDispatchPermit
    activation_seal: _ActivationSeal
    expectation: StageCRuntimeAttemptClaimExpectation
    observation: StageCRuntimeAttemptClaimObservation
    observation_values: tuple[Any, ...]
    backend_snapshot: _ClaimBackendSnapshot
    study_request: DiagnosticStudyRequestArtifact
    child_binding: DiagnosticChildExecutionBindingArtifact
    worker_authorization: DiagnosticWorkerAuthorizationV2Artifact
    model_capture_target: StageCRuntimeModelCaptureTarget
    control_state: str


_SEALS_LOCK = threading.RLock()
_TARGET_SEALS: dict[int, _TargetSeal] = {}
_PREPARATION_SEALS: dict[int, _PreparationSeal] = {}
_ACTIVATION_SEALS: dict[int, _ActivationSeal] = {}
_PERMIT_SEALS: dict[int, _PermitSeal] = {}
_DETACHED_MECHANICS_LOCK = threading.RLock()
_DETACHED_MECHANICS_CACHE: dict[
    str,
    tuple[DiagnosticSharedPlanReplayContext, DiagnosticPhaseRegistrationArtifact],
] = {}


def _target_values(target: StageCRuntimeModelCaptureTarget) -> tuple[str, ...]:
    return (
        target.model_identity_sha256,
        target.capture_profile_sha256,
        target.model_contract_sha256,
        target.runtime_contract_sha256,
        target.capture_contract_sha256,
        target.target_sha256,
    )


def _require_target(target: Any) -> _TargetSeal:
    if type(target) is not StageCRuntimeModelCaptureTarget:
        _fail("MODEL_CAPTURE_TARGET_INVALID", "model/capture target has the wrong exact type")
    with _SEALS_LOCK:
        seal = _TARGET_SEALS.get(id(target))
    if (
        seal is None
        or seal.target is not target
        or _target_values(target) != seal.values
        or canonical_sha256(
            {
                "domain": "cas_harness_v2.stagec_runtime_model_capture_target.v1",
                "model_identity_sha256": target.model_identity_sha256,
                "capture_profile_sha256": target.capture_profile_sha256,
                "model_contract_sha256": target.model_contract_sha256,
                "runtime_contract_sha256": target.runtime_contract_sha256,
                "capture_contract_sha256": target.capture_contract_sha256,
            }
        )
        != target.target_sha256
    ):
        _fail("MODEL_CAPTURE_TARGET_INVALID", "model/capture target is not factory-sealed")
    return seal


def build_stagec_runtime_model_capture_target(
    *,
    prerequisite_context: StageCPrerequisiteFactoryContext,
    shared_plan_context: DiagnosticSharedPlanReplayContext,
) -> StageCRuntimeModelCaptureTarget:
    """Bind exact model/runtime/capture contracts without creating authority."""

    try:
        if type(prerequisite_context) is not StageCPrerequisiteFactoryContext:
            raise TypeError("prerequisite context has the wrong exact type")
        if type(shared_plan_context) is not DiagnosticSharedPlanReplayContext:
            raise TypeError("shared plan context has the wrong exact type")
        fresh = build_diagnostic_shared_plan_replay_context(
            chain=shared_plan_context.chain,
            plan=shared_plan_context.plan,
            execution_contract=shared_plan_context.execution_contract,
        )
        value = {
            "domain": "cas_harness_v2.stagec_runtime_model_capture_target.v1",
            "model_identity_sha256": expect_sha256(
                prerequisite_context.model_identity_sha256,
                "prerequisite_context.model_identity_sha256",
            ),
            "capture_profile_sha256": expect_sha256(
                prerequisite_context.capture_profile_sha256,
                "prerequisite_context.capture_profile_sha256",
            ),
            "model_contract_sha256": canonical_sha256(
                fresh.execution_contract.payload["model_contract"]
            ),
            "runtime_contract_sha256": canonical_sha256(
                fresh.execution_contract.payload["runtime_contract"]
            ),
            "capture_contract_sha256": canonical_sha256(
                fresh.execution_contract.payload["capture_contract"]
            ),
        }
        digest = canonical_sha256(value)
    except (AttributeError, KeyError, SchemaValidationError, TypeError, ValueError) as exc:
        _fail("MODEL_CAPTURE_TARGET_INVALID", "model/capture target replay failed closed")
    target = object.__new__(StageCRuntimeModelCaptureTarget)
    for field, item in value.items():
        if field != "domain":
            object.__setattr__(target, field, item)
    object.__setattr__(target, "target_sha256", digest)
    with _SEALS_LOCK:
        _TARGET_SEALS[id(target)] = _TargetSeal(target, _target_values(target))
    return target


def _roster_closure(registration: DiagnosticPhaseRegistrationArtifact) -> str:
    return canonical_sha256(
        {
            "domain": "cas_harness_v2.stagec_runtime_exact_phase_roster.v1",
            "phase_id": registration.phase_id,
            "phase_subject_sha256": registration.phase_subject_sha256,
            "ordered_rows": [
                {
                    "execution_ordinal": index,
                    "study_request": _ref_value(request.artifact_ref),
                    "attempt_subject_sha256": registration.ordered_subjects[index - 1],
                }
                for index, request in enumerate(registration.study_requests, start=1)
            ],
        }
    )


def _ref_scalars(reference: ArtifactRef) -> tuple[Any, ...]:
    return (
        reference.artifact_id,
        reference.sha256,
        reference.byte_length,
        reference.media_type,
    )


def _copy_ref(reference: ArtifactRef) -> ArtifactRef:
    if type(reference) is not ArtifactRef:
        _fail("PREPARATION_INVALID", "detached authority reference is not exact")
    return ArtifactRef(
        artifact_id=reference.artifact_id,
        sha256=reference.sha256,
        byte_length=reference.byte_length,
        media_type=reference.media_type,
    )


def _raw_carrier_values(carrier: Any) -> tuple[Any, ...]:
    raw = carrier.raw_bytes
    if type(raw) is not bytes:
        _fail("PREPARATION_INVALID", "authority carrier raw bytes are not exact bytes")
    reference = carrier.artifact_ref
    if type(reference) is not ArtifactRef or not reference.verify_bytes(raw):
        _fail("PREPARATION_INVALID", "authority carrier bytes/ref identity drifted")
    return (
        type(carrier),
        sha256_bytes(raw),
        len(raw),
        _ref_scalars(reference),
    )


def _preparation_public_values(preparation: StageCRuntimePreparation) -> tuple[Any, ...]:
    """Mechanical value seal for every publicly reachable authority carrier."""

    binding = preparation.external_binding
    snapshot = binding.snapshot
    context = preparation.prerequisite_context
    shared = preparation.shared_plan_context
    registration = preparation.phase_registration
    storage = snapshot.trusted_storage
    authorization = snapshot.authorization
    return (
        binding,
        binding.snapshot,
        binding.intake,
        binding.admission,
        sha256_bytes(binding.report_raw_bytes),
        binding.report_sha256,
        _ref_scalars(binding.report_artifact_ref),
        _raw_carrier_values(binding.intake),
        _raw_carrier_values(binding.admission),
        binding.admission.target_binding_sha256,
        sha256_bytes(snapshot.manifest_raw_bytes),
        _ref_scalars(snapshot.manifest_artifact_ref),
        tuple(
            (
                row.role,
                row.relative_path,
                _ref_scalars(row.artifact_ref),
                sha256_bytes(row.raw_bytes),
                len(row.raw_bytes),
            )
            for row in snapshot.roles
        ),
        _raw_carrier_values(snapshot.detector_drc),
        _raw_carrier_values(snapshot.corpus),
        _raw_carrier_values(storage),
        storage.object_version_id,
        storage.retention_until,
        _raw_carrier_values(authorization),
        authorization.authorization_id,
        authorization.target_binding_sha256,
        authorization.prospective_subject_sha256,
        authorization.window_start,
        authorization.window_end,
        authorization.nonce_b64url,
        canonical_sha256(authorization.payload["scope"]),
        context,
        _raw_carrier_values(context.split_inventory),
        tuple(
            _raw_carrier_values(row)
            for row in context.split_inventory.capture_requests
        ),
        _raw_carrier_values(context.prompt_inventory),
        context.model_identity_sha256,
        context.capture_profile_sha256,
        context.target_binding_sha256,
        canonical_sha256(context.target_binding),
        shared,
        shared.chain.pre_outcome_chain_sha256,
        _raw_carrier_values(shared.plan),
        _raw_carrier_values(shared.execution_contract),
        shared.kernel_sha256,
        canonical_sha256(shared.execution_contract.payload["model_contract"]),
        canonical_sha256(shared.execution_contract.payload["runtime_contract"]),
        canonical_sha256(shared.execution_contract.payload["capture_contract"]),
        registration,
        _raw_carrier_values(registration),
        registration.phase_id,
        registration.phase_subject_sha256,
        registration.tenant_id,
        tuple(registration.ordered_subjects),
        tuple(_raw_carrier_values(row) for row in registration.study_requests),
        _raw_carrier_values(registration.store_binding),
        preparation.model_capture_target,
        _target_values(preparation.model_capture_target),
        preparation.tenant_id,
        preparation.roster_closure_sha256,
    )


def _detached_shared_plan_and_registration(
    shared: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
) -> tuple[DiagnosticSharedPlanReplayContext, DiagnosticPhaseRegistrationArtifact]:
    """Reconstruct private mechanics solely from exact copied carrier bytes."""

    base_raw = bytes(shared.chain.base.raw_bytes)
    amendment_raws = tuple(bytes(item.raw_bytes) for item in shared.chain.amendments)
    plan_raw = bytes(shared.plan.raw_bytes)
    contract_raw = bytes(shared.execution_contract.raw_bytes)
    inventory_raw = bytes(shared.plan.inventory.raw_bytes)
    capture_rows = tuple(
        (_copy_ref(item.artifact_ref), bytes(item.raw_bytes))
        for item in shared.plan.inventory.capture_requests
    )
    registration_raw = bytes(registration.raw_bytes)
    request_raws = tuple(bytes(item.raw_bytes) for item in registration.study_requests)
    store_binding_raw = bytes(registration.store_binding.raw_bytes)
    cache_key = canonical_sha256(
        {
            "domain": "cas_harness_v2.stagec_runtime_detached_mechanics.v1",
            "base": sha256_bytes(base_raw),
            "amendments": [sha256_bytes(raw) for raw in amendment_raws],
            "plan": sha256_bytes(plan_raw),
            "execution_contract": sha256_bytes(contract_raw),
            "inventory": sha256_bytes(inventory_raw),
            "capture_rows": [
                {
                    "artifact_ref": _ref_value(reference),
                    "raw_sha256": sha256_bytes(raw),
                }
                for reference, raw in capture_rows
            ],
            "registration": sha256_bytes(registration_raw),
            "study_requests": [sha256_bytes(raw) for raw in request_raws],
            "store_binding": sha256_bytes(store_binding_raw),
        }
    )
    with _DETACHED_MECHANICS_LOCK:
        cached = _DETACHED_MECHANICS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    private_chain = DiagnosticPreregistrationChain(
        load_diagnostic_preregistration(base_raw)
    )
    for amendment_raw in amendment_raws:
        private_chain.append_amendment(amendment_raw)
    private_captures = tuple(
        load_stagec_capture_request(reference, raw)
        for reference, raw in capture_rows
    )
    private_inventory = load_diagnostic_split_inventory(
        inventory_raw,
        capture_requests=private_captures,
    )
    private_plan = load_diagnostic_study_plan(
        plan_raw,
        chain=private_chain,
        inventory=private_inventory,
    )
    private_contract = load_diagnostic_stagec_execution_contract(
        contract_raw,
        chain=private_chain,
        plan=private_plan,
    )
    private_shared = build_diagnostic_shared_plan_replay_context(
        chain=private_chain,
        plan=private_plan,
        execution_contract=private_contract,
    )
    private_requests = tuple(
        load_diagnostic_study_request(
            raw,
            chain=private_chain,
            plan=private_plan,
        )
        for raw in request_raws
    )
    private_store_binding = load_diagnostic_phase_store_binding(store_binding_raw)
    private_registration = load_diagnostic_phase_registration(
        registration_raw,
        shared_plan_context=private_shared,
        study_requests=private_requests,
        store_binding=private_store_binding,
    )
    built = (private_shared, private_registration)
    with _DETACHED_MECHANICS_LOCK:
        retained = _DETACHED_MECHANICS_CACHE.setdefault(cache_key, built)
    return retained


def _phase_binding_snapshot(
    *,
    binding: StageCExternalPrerequisiteBinding,
    shared: DiagnosticSharedPlanReplayContext,
    registration: DiagnosticPhaseRegistrationArtifact,
    target: StageCRuntimeModelCaptureTarget,
    tenant_id: str,
    roster_closure_sha256: str,
) -> _PhaseBindingSnapshot:
    storage = binding.snapshot.trusted_storage
    corpus = binding.snapshot.corpus
    authorization = binding.snapshot.authorization
    return _PhaseBindingSnapshot(
        tenant_id=tenant_id,
        phase_id=registration.phase_id,
        phase_subject_sha256=registration.phase_subject_sha256,
        registration_ref=_copy_ref(registration.artifact_ref),
        roster_closure_sha256=roster_closure_sha256,
        plan_ref=_copy_ref(shared.plan.artifact_ref),
        execution_contract_ref=_copy_ref(shared.execution_contract.artifact_ref),
        admission_ref=_copy_ref(binding.admission.artifact_ref),
        external_binding_report_ref=_copy_ref(binding.report_artifact_ref),
        target_binding_sha256=binding.admission.target_binding_sha256,
        prospective_subject_sha256=authorization.prospective_subject_sha256,
        authorization_id=authorization.authorization_id,
        authorization_window_start=authorization.window_start,
        authorization_window_end=authorization.window_end,
        authorization_nonce_b64url=authorization.nonce_b64url,
        corpus_ref=_copy_ref(corpus.artifact_ref),
        storage_receipt_ref=_copy_ref(storage.artifact_ref),
        storage_object_version_id=storage.object_version_id,
        storage_checksum_sha256=corpus.sha256,
        storage_byte_length=corpus.byte_length,
        storage_retention_until=storage.retention_until,
        model_capture_target_sha256=target.target_sha256,
    )


def prepare_stagec_runtime_activation(
    *,
    external_binding: StageCExternalPrerequisiteBinding,
    prerequisite_context: StageCPrerequisiteFactoryContext,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...],
    shared_plan_context: DiagnosticSharedPlanReplayContext,
    phase_registration: DiagnosticPhaseRegistrationArtifact,
    model_capture_target: StageCRuntimeModelCaptureTarget,
    tenant_id: str,
) -> StageCRuntimePreparation:
    """Fresh-replay and process-seal every pre-window activation dependency."""

    try:
        if type(external_binding) is not StageCExternalPrerequisiteBinding:
            _fail("PREPARATION_INVALID", "external binding has the wrong exact type")
        if type(prerequisite_context) is not StageCPrerequisiteFactoryContext:
            _fail("PREPARATION_INVALID", "prerequisite context has the wrong exact type")
        if type(replay_bundles) is not tuple:
            _fail("PREPARATION_INVALID", "replay_bundles must be an exact tuple")
        target_seal = _require_target(model_capture_target)
        del target_seal
        try:
            fresh_binding = load_stagec_external_prerequisite_binding(
                external_binding.snapshot,
                context=prerequisite_context,
                replay_bundles=replay_bundles,
                intake_bytes=external_binding.intake.raw_bytes,
                admission_bytes=external_binding.admission.raw_bytes,
            )
        except Exception as exc:
            raise StageCRuntimeActivationError(
                "EXTERNAL_BINDING_REPLAY_FAILED",
                "external prerequisite binding did not fresh-replay",
            ) from exc
        try:
            admitted = require_stagec_prerequisite_admission_in_preregistration(
                prerequisite_context, shared_plan_context.chain
            )
        except Exception as exc:
            raise StageCRuntimeActivationError(
                "PREREGISTRATION_ADMISSION_FAILED",
                "exact shared preregistration chain did not retain the admission",
            ) from exc
        if (
            admitted.artifact_ref != fresh_binding.admission.artifact_ref
            or admitted.raw_bytes != fresh_binding.admission.raw_bytes
        ):
            _fail(
                "TARGET_BINDING_MISMATCH",
                "fresh external admission differs from the shared-chain admission",
            )
        try:
            fresh_shared = build_diagnostic_shared_plan_replay_context(
                chain=shared_plan_context.chain,
                plan=shared_plan_context.plan,
                execution_contract=shared_plan_context.execution_contract,
            )
        except Exception as exc:
            raise StageCRuntimeActivationError(
                "SHARED_PLAN_REPLAY_FAILED", "shared plan/contract replay failed"
            ) from exc
        try:
            fresh_registration = load_diagnostic_phase_registration(
                phase_registration.raw_bytes,
                shared_plan_context=fresh_shared,
                study_requests=phase_registration.study_requests,
                store_binding=phase_registration.store_binding,
            )
        except Exception as exc:
            raise StageCRuntimeActivationError(
                "PHASE_REGISTRATION_REPLAY_FAILED",
                "phase registration did not replay against the exact shared plan",
            ) from exc
        tenant = expect_machine_id(tenant_id, "tenant_id")
        if tenant != fresh_registration.tenant_id:
            _fail("TARGET_BINDING_MISMATCH", "tenant differs from phase registration")
        if (
            fresh_shared.plan.inventory.artifact_ref
            != prerequisite_context.split_inventory.artifact_ref
            or fresh_binding.admission.target_binding_sha256
            != prerequisite_context.target_binding_sha256
            or fresh_binding.snapshot.authorization.target_binding_sha256
            != prerequisite_context.target_binding_sha256
            or fresh_binding.snapshot.authorization.window_start
            != fresh_shared.plan.execution_window_start
            or fresh_binding.snapshot.authorization.window_end
            != fresh_shared.plan.execution_window_end
        ):
            _fail(
                "TARGET_BINDING_MISMATCH",
                "prerequisite, split, plan, or execution window identity drifted",
            )
        if (
            model_capture_target.model_identity_sha256
            != prerequisite_context.model_identity_sha256
            or model_capture_target.capture_profile_sha256
            != prerequisite_context.capture_profile_sha256
            or model_capture_target.model_contract_sha256
            != canonical_sha256(fresh_shared.execution_contract.payload["model_contract"])
            or model_capture_target.runtime_contract_sha256
            != canonical_sha256(fresh_shared.execution_contract.payload["runtime_contract"])
            or model_capture_target.capture_contract_sha256
            != canonical_sha256(fresh_shared.execution_contract.payload["capture_contract"])
        ):
            _fail(
                "MODEL_CAPTURE_TARGET_INVALID",
                "model/runtime/capture target differs from the exact shared contracts",
            )
        scope = fresh_binding.snapshot.authorization.payload["scope"]
        if (
            scope.get("total_attempt_count") != DIAGNOSTIC_CASE_COUNT
            or scope.get("attempts_per_case") != 1
            or scope.get("canary_count") != 0
            or scope.get("retry_count") != 0
            or scope.get("replacement_count") != 0
        ):
            _fail("STARTUP_CANARY_FORBIDDEN", "authorization scope is not exact v1 zero-canary")
        if (
            len(fresh_registration.ordered_subjects) != DIAGNOSTIC_CASE_COUNT
            or len(fresh_registration.study_requests) != DIAGNOSTIC_CASE_COUNT
            or len(set(fresh_registration.ordered_subjects)) != DIAGNOSTIC_CASE_COUNT
            or tuple(request.execution_ordinal for request in fresh_registration.study_requests)
            != tuple(range(1, DIAGNOSTIC_CASE_COUNT + 1))
        ):
            _fail("ROSTER_INVALID", "phase roster is not the exact unique 480-row order")
        roster_sha = _roster_closure(fresh_registration)
        try:
            private_shared, private_registration = (
                _detached_shared_plan_and_registration(
                    fresh_shared,
                    fresh_registration,
                )
            )
        except Exception as exc:
            raise StageCRuntimeActivationError(
                "SHARED_PLAN_REPLAY_FAILED",
                "detached private shared-plan mechanics did not exact-replay",
            ) from exc
        if (
            private_registration.artifact_ref != fresh_registration.artifact_ref
            or private_registration.ordered_subjects
            != fresh_registration.ordered_subjects
            or _roster_closure(private_registration) != roster_sha
        ):
            _fail(
                "PHASE_REGISTRATION_REPLAY_FAILED",
                "detached private phase roster differs from the public replay",
            )
        phase_binding = _phase_binding_snapshot(
            binding=fresh_binding,
            shared=private_shared,
            registration=private_registration,
            target=model_capture_target,
            tenant_id=tenant,
            roster_closure_sha256=roster_sha,
        )
    except StageCRuntimeActivationError:
        raise
    except (AttributeError, KeyError, SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRuntimeActivationError(
            "PREPARATION_INVALID", "runtime preparation validation failed closed"
        ) from exc

    preparation = object.__new__(StageCRuntimePreparation)
    object.__setattr__(preparation, "external_binding", fresh_binding)
    object.__setattr__(preparation, "prerequisite_context", prerequisite_context)
    object.__setattr__(preparation, "shared_plan_context", fresh_shared)
    object.__setattr__(preparation, "phase_registration", fresh_registration)
    object.__setattr__(preparation, "model_capture_target", model_capture_target)
    object.__setattr__(preparation, "tenant_id", tenant)
    object.__setattr__(preparation, "roster_closure_sha256", roster_sha)
    try:
        public_values = _preparation_public_values(preparation)
    except Exception as exc:
        raise StageCRuntimeActivationError(
            "PREPARATION_INVALID",
            "public preparation carrier value sealing failed closed",
        ) from exc
    seal = _PreparationSeal(
        preparation=preparation,
        external_binding=fresh_binding,
        prerequisite_context=prerequisite_context,
        shared_plan_context=fresh_shared,
        phase_registration=fresh_registration,
        private_shared_plan_context=private_shared,
        private_phase_registration=private_registration,
        model_capture_target=model_capture_target,
        phase_binding=phase_binding,
        public_values=public_values,
        tenant_id=tenant,
        roster_closure_sha256=roster_sha,
        control_state=STAGEC_RUNTIME_PREPARED,
        lock=threading.RLock(),
    )
    with _SEALS_LOCK:
        _PREPARATION_SEALS[id(preparation)] = seal
    return preparation


def _require_preparation(preparation: Any) -> _PreparationSeal:
    if type(preparation) is not StageCRuntimePreparation:
        _fail("PREPARATION_INVALID", "preparation has the wrong exact type")
    with _SEALS_LOCK:
        seal = _PREPARATION_SEALS.get(id(preparation))
    try:
        observed_public_values = _preparation_public_values(preparation)
    except Exception as exc:
        raise StageCRuntimeActivationError(
            "PREPARATION_INVALID",
            "public preparation carriers no longer reconstruct",
        ) from exc
    if (
        seal is None
        or seal.preparation is not preparation
        or preparation.external_binding is not seal.external_binding
        or preparation.prerequisite_context is not seal.prerequisite_context
        or preparation.shared_plan_context is not seal.shared_plan_context
        or preparation.phase_registration is not seal.phase_registration
        or preparation.model_capture_target is not seal.model_capture_target
        or preparation.tenant_id != seal.tenant_id
        or preparation.roster_closure_sha256 != seal.roster_closure_sha256
        or observed_public_values != seal.public_values
        or _roster_closure(seal.private_phase_registration)
        != seal.roster_closure_sha256
    ):
        _fail("PREPARATION_INVALID", "preparation is not the unchanged process-sealed object")
    _require_target(seal.model_capture_target)
    return seal


def stagec_runtime_preparation_state(preparation: StageCRuntimePreparation) -> str:
    seal = _require_preparation(preparation)
    with seal.lock:
        return seal.control_state


def _validate_backend(backend: Any) -> StageCRuntimeActivationBackend:
    if type(backend) is UnavailableStageCRuntimeActivationBackend:
        _fail("BACKEND_UNAVAILABLE", "no trusted runtime activation backend is installed")
    trusted = _TRUSTED_BACKEND_TYPES
    if type(trusted) is not frozenset or any(
        type(item) is not type or not issubclass(item, StageCRuntimeActivationBackend)
        for item in trusted
    ):
        _fail("BACKEND_NOT_TRUSTED", "trusted backend type allowlist is malformed")
    if type(backend) not in trusted:
        _fail("BACKEND_NOT_TRUSTED", "backend exact type is not installed")
    return backend


def _phase_expectation(
    seal: _PreparationSeal, authenticated_worker_id: str
) -> StageCRuntimePhaseActivationExpectation:
    binding = seal.phase_binding
    return StageCRuntimePhaseActivationExpectation(
        tenant_id=binding.tenant_id,
        authenticated_worker_id=authenticated_worker_id,
        phase_id=binding.phase_id,
        phase_subject_sha256=binding.phase_subject_sha256,
        registration_ref=binding.registration_ref,
        roster_closure_sha256=binding.roster_closure_sha256,
        plan_ref=binding.plan_ref,
        execution_contract_ref=binding.execution_contract_ref,
        admission_ref=binding.admission_ref,
        external_binding_report_ref=binding.external_binding_report_ref,
        target_binding_sha256=binding.target_binding_sha256,
        prospective_subject_sha256=binding.prospective_subject_sha256,
        authorization_id=binding.authorization_id,
        authorization_window_start=binding.authorization_window_start,
        authorization_window_end=binding.authorization_window_end,
        authorization_nonce_b64url=binding.authorization_nonce_b64url,
        corpus_ref=binding.corpus_ref,
        storage_receipt_ref=binding.storage_receipt_ref,
        storage_object_version_id=binding.storage_object_version_id,
        storage_checksum_sha256=binding.storage_checksum_sha256,
        storage_byte_length=binding.storage_byte_length,
        storage_retention_until=binding.storage_retention_until,
        model_capture_target_sha256=binding.model_capture_target_sha256,
        startup_canary_policy=STAGEC_RUNTIME_STARTUP_CANARY,
    )


def _storage_values(observation: StageCRuntimeStorageObservation) -> tuple[Any, ...]:
    return (
        observation.authenticated_tenant_id,
        observation.authenticated_worker_id,
        observation.provider_id,
        observation.object_key,
        observation.object_version_id,
        observation.checksum_sha256,
        observation.byte_length,
        observation.retention_until,
        observation.trusted_time,
        observation.observation_generation,
    )


def _issuer_values(
    observation: StageCRuntimeIssuerAuthorizationObservation,
) -> tuple[Any, ...]:
    return (
        observation.authenticated_tenant_id,
        observation.authenticated_worker_id,
        observation.issuer_id,
        observation.authorization_id,
        observation.prospective_subject_sha256,
        observation.target_binding_sha256,
        observation.window_start,
        observation.window_end,
        observation.nonce_b64url,
        observation.nonce_state_before,
        observation.nonce_state_after,
        observation.nonce_consumed_now,
        observation.ledger_generation,
        observation.phase_id,
        observation.phase_subject_sha256,
        observation.plan_sha256,
        observation.execution_contract_sha256,
        observation.admission_sha256,
    )


def _phase_observation_values(
    observation: StageCRuntimePhaseActivationObservation,
) -> tuple[Any, ...]:
    return (
        observation.storage,
        _storage_values(observation.storage),
        observation.authorization,
        _issuer_values(observation.authorization),
        observation.registration_sha256,
        observation.roster_closure_sha256,
        observation.model_capture_target_sha256,
        observation.control_state,
    )


def _detach_storage_observation(
    observation: Any,
    *,
    claim: bool,
) -> StageCRuntimeStorageObservation:
    code = "CLAIM_OBSERVATION_INVALID" if claim else "PHASE_OBSERVATION_INVALID"
    if type(observation) is not StageCRuntimeStorageObservation:
        _fail(code, "storage observation has the wrong exact immutable type")
    before = _storage_values(observation)
    detached = StageCRuntimeStorageObservation(*before)
    if _storage_values(observation) != before:
        _fail(code, "storage observation changed while being detached")
    return detached


def _detach_issuer_observation(
    observation: Any,
    *,
    claim: bool,
) -> StageCRuntimeIssuerAuthorizationObservation:
    code = "CLAIM_OBSERVATION_INVALID" if claim else "PHASE_OBSERVATION_INVALID"
    if type(observation) is not StageCRuntimeIssuerAuthorizationObservation:
        _fail(code, "issuer observation has the wrong exact immutable type")
    before = _issuer_values(observation)
    detached = StageCRuntimeIssuerAuthorizationObservation(*before)
    if _issuer_values(observation) != before:
        _fail(code, "issuer observation changed while being detached")
    return detached


def _detach_phase_observation(
    observation: Any,
) -> StageCRuntimePhaseActivationObservation:
    if type(observation) is not StageCRuntimePhaseActivationObservation:
        _fail("PHASE_OBSERVATION_INVALID", "phase observation has the wrong exact type")
    before = (
        _storage_values(observation.storage),
        _issuer_values(observation.authorization),
        observation.registration_sha256,
        observation.roster_closure_sha256,
        observation.model_capture_target_sha256,
        observation.control_state,
    )
    detached = StageCRuntimePhaseActivationObservation(
        storage=_detach_storage_observation(observation.storage, claim=False),
        authorization=_detach_issuer_observation(
            observation.authorization,
            claim=False,
        ),
        registration_sha256=before[2],
        roster_closure_sha256=before[3],
        model_capture_target_sha256=before[4],
        control_state=before[5],
    )
    after = (
        _storage_values(observation.storage),
        _issuer_values(observation.authorization),
        observation.registration_sha256,
        observation.roster_closure_sha256,
        observation.model_capture_target_sha256,
        observation.control_state,
    )
    if after != before:
        _fail("PHASE_OBSERVATION_INVALID", "phase observation changed while being detached")
    return detached


def _validate_storage(
    storage: Any,
    *,
    tenant_id: str,
    worker_id: str,
    expected_version: str,
    expected_checksum: str,
    expected_length: int,
    expected_retention: str,
    window_start: str,
    window_end: str,
    claim: bool,
) -> None:
    code = "CLAIM_OBSERVATION_INVALID" if claim else "PHASE_OBSERVATION_INVALID"
    if type(storage) is not StageCRuntimeStorageObservation:
        _fail(code, "storage observation has the wrong exact immutable type")
    _machine(storage.authenticated_tenant_id, "storage.authenticated_tenant_id", claim=claim)
    _machine(storage.authenticated_worker_id, "storage.authenticated_worker_id", claim=claim)
    _machine(storage.provider_id, "storage.provider_id", claim=claim)
    try:
        expect_string(storage.object_key, "storage.object_key", maximum=1024)
    except (SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRuntimeActivationError(code, "storage object key is invalid") from exc
    _machine(storage.object_version_id, "storage.object_version_id", claim=claim)
    _sha(storage.checksum_sha256, "storage.checksum_sha256", claim=claim)
    length = _positive_int(storage.byte_length, "storage.byte_length", claim=claim)
    _positive_int(storage.observation_generation, "storage.observation_generation", claim=claim)
    now = _time(storage.trusted_time, "storage.trusted_time")
    start = _time(window_start, "authorization.window_start")
    end = _time(window_end, "authorization.window_end")
    retention = _time(storage.retention_until, "storage.retention_until")
    if not (start <= now < end):
        _fail(
            "PHASE_TRUSTED_TIME_OUTSIDE_WINDOW" if not claim else "CLAIM_BINDING_MISMATCH",
            "backend trusted time is outside the half-open authorization window",
        )
    if retention <= end:
        _fail(
            "PHASE_STORAGE_RETENTION_INSUFFICIENT" if not claim else "CLAIM_BINDING_MISMATCH",
            "live storage retention does not extend beyond authorization",
        )
    if (
        storage.authenticated_tenant_id != tenant_id
        or storage.authenticated_worker_id != worker_id
        or storage.object_version_id != expected_version
        or storage.checksum_sha256 != expected_checksum
        or length != expected_length
        or storage.retention_until != expected_retention
    ):
        _fail(
            "CLAIM_BINDING_MISMATCH" if claim else "PHASE_BINDING_MISMATCH",
            "live storage observation differs from exact expected bindings",
        )


def _validate_issuer(
    authorization: Any,
    *,
    expectation: StageCRuntimePhaseActivationExpectation,
    tenant_id: str,
    worker_id: str,
    claim: bool,
    expected_issuer_id: str | None = None,
    minimum_generation: int = 1,
) -> None:
    code = "CLAIM_OBSERVATION_INVALID" if claim else "PHASE_OBSERVATION_INVALID"
    if type(authorization) is not StageCRuntimeIssuerAuthorizationObservation:
        _fail(code, "issuer observation has the wrong exact immutable type")
    for field, value in (
        ("authenticated_tenant_id", authorization.authenticated_tenant_id),
        ("authenticated_worker_id", authorization.authenticated_worker_id),
        ("issuer_id", authorization.issuer_id),
        ("authorization_id", authorization.authorization_id),
        ("phase_id", authorization.phase_id),
    ):
        _machine(value, f"authorization.{field}", claim=claim)
    for field, value in (
        ("prospective_subject_sha256", authorization.prospective_subject_sha256),
        ("target_binding_sha256", authorization.target_binding_sha256),
        ("phase_subject_sha256", authorization.phase_subject_sha256),
        ("plan_sha256", authorization.plan_sha256),
        ("execution_contract_sha256", authorization.execution_contract_sha256),
        ("admission_sha256", authorization.admission_sha256),
    ):
        _sha(value, f"authorization.{field}", claim=claim)
    generation = _positive_int(
        authorization.ledger_generation, "authorization.ledger_generation", claim=claim
    )
    if (
        authorization.authenticated_tenant_id != tenant_id
        or authorization.authenticated_worker_id != worker_id
        or authorization.authorization_id != expectation.authorization_id
        or authorization.prospective_subject_sha256
        != expectation.prospective_subject_sha256
        or authorization.target_binding_sha256 != expectation.target_binding_sha256
        or authorization.window_start != expectation.authorization_window_start
        or authorization.window_end != expectation.authorization_window_end
        or authorization.nonce_b64url != expectation.authorization_nonce_b64url
        or authorization.nonce_state_before != ("CONSUMED" if claim else "UNCONSUMED")
        or authorization.nonce_state_after != "CONSUMED"
        or type(authorization.nonce_consumed_now) is not bool
        or authorization.nonce_consumed_now is not (not claim)
        or (claim and generation <= minimum_generation)
        or (not claim and generation < minimum_generation)
        or authorization.phase_id != expectation.phase_id
        or authorization.phase_subject_sha256 != expectation.phase_subject_sha256
        or authorization.plan_sha256 != expectation.plan_ref.sha256
        or authorization.execution_contract_sha256
        != expectation.execution_contract_ref.sha256
        or authorization.admission_sha256 != expectation.admission_ref.sha256
        or (expected_issuer_id is not None and authorization.issuer_id != expected_issuer_id)
    ):
        _fail(
            "CLAIM_BINDING_MISMATCH" if claim else "PHASE_BINDING_MISMATCH",
            "live issuer observation differs from exact expected bindings",
        )


def _validate_phase_observation(
    observation: Any,
    expectation: StageCRuntimePhaseActivationExpectation,
) -> StageCRuntimePhaseActivationObservation:
    if type(observation) is not StageCRuntimePhaseActivationObservation:
        _fail("PHASE_OBSERVATION_INVALID", "phase observation has the wrong exact type")
    if observation.authorization.nonce_consumed_now is not True:
        _fail("PHASE_NONCE_NOT_NEWLY_CONSUMED", "phase nonce was not newly consumed")
    _validate_storage(
        observation.storage,
        tenant_id=expectation.tenant_id,
        worker_id=expectation.authenticated_worker_id,
        expected_version=expectation.storage_object_version_id,
        expected_checksum=expectation.storage_checksum_sha256,
        expected_length=expectation.storage_byte_length,
        expected_retention=expectation.storage_retention_until,
        window_start=expectation.authorization_window_start,
        window_end=expectation.authorization_window_end,
        claim=False,
    )
    _validate_issuer(
        observation.authorization,
        expectation=expectation,
        tenant_id=expectation.tenant_id,
        worker_id=expectation.authenticated_worker_id,
        claim=False,
    )
    if (
        observation.registration_sha256 != expectation.registration_ref.sha256
        or observation.roster_closure_sha256 != expectation.roster_closure_sha256
        or observation.model_capture_target_sha256
        != expectation.model_capture_target_sha256
        or observation.control_state != STAGEC_RUNTIME_ROWS_ENABLED
    ):
        _fail("PHASE_BINDING_MISMATCH", "phase observation target or roster drifted")
    if observation.storage.provider_id == "" or observation.authorization.issuer_id == "":
        _fail("PHASE_OBSERVATION_INVALID", "provider and issuer identities are required")
    return observation


def activate_stagec_runtime_phase(
    preparation: StageCRuntimePreparation,
    *,
    backend: StageCRuntimeActivationBackend,
    authenticated_worker_id: str,
) -> StageCRuntimePhaseActivation:
    """Atomically consume one live phase nonce and enable exact roster rows."""

    # These two checks are intentionally before any local activation-state
    # mutation.  The exact unavailable backend and arbitrary objects therefore
    # cannot consume a nonce or alter preparation state.
    trusted_backend = _validate_backend(backend)
    seal = _require_preparation(preparation)
    try:
        worker = expect_machine_id(authenticated_worker_id, "authenticated_worker_id")
    except (SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRuntimeActivationError(
            "PHASE_OBSERVATION_INVALID", "authenticated worker identity is invalid"
        ) from exc
    with seal.lock:
        # Re-run the full public-carrier value seal under the same local lock
        # used to reserve activation.  The backend expectation below is built
        # exclusively from the detached private snapshot, so a concurrent
        # low-level dataclass mutation can only make a later check reject.
        if _require_preparation(preparation) is not seal:
            _fail("PREPARATION_INVALID", "preparation seal identity changed")
        if seal.control_state == STAGEC_RUNTIME_ACTIVATION_INDETERMINATE:
            _fail("PHASE_ACTIVATION_INDETERMINATE", "activation cannot be retried")
        if seal.control_state != STAGEC_RUNTIME_PREPARED:
            _fail("PHASE_ALREADY_ACTIVATED", "preparation already attempted activation")
        expectation = _phase_expectation(seal, worker)
        # Reserve this exact process-local attempt before crossing the backend
        # boundary.  Any ambiguous return terminalizes it and forbids retry.
        seal.control_state = "ACTIVATION_IN_PROGRESS"
        try:
            backend_expectation = _disposable_backend_expectation(expectation)
            backend_expectation_values = _backend_expectation_values(
                backend_expectation
            )
            returned_observation = trusted_backend.activate_phase(
                backend_expectation
            )
            _require_disposable_expectation_unchanged(
                backend_expectation,
                backend_expectation_values,
                error_code="PHASE_OBSERVATION_INVALID",
            )
            observation = _detach_phase_observation(
                returned_observation
            )
            observation = _validate_phase_observation(observation, expectation)
            activation = object.__new__(StageCRuntimePhaseActivation)
            object.__setattr__(activation, "preparation", preparation)
            object.__setattr__(activation, "observation", observation)
            backend_snapshot = _ActivationBackendSnapshot(
                provider_id=observation.storage.provider_id,
                storage_object_key=observation.storage.object_key,
                storage_object_version_id=observation.storage.object_version_id,
                storage_checksum_sha256=observation.storage.checksum_sha256,
                storage_byte_length=observation.storage.byte_length,
                storage_retention_until=observation.storage.retention_until,
                storage_trusted_time=observation.storage.trusted_time,
                storage_observation_generation=(
                    observation.storage.observation_generation
                ),
                issuer_id=observation.authorization.issuer_id,
                ledger_generation=observation.authorization.ledger_generation,
            )
            activation_seal = _ActivationSeal(
                activation=activation,
                preparation_seal=seal,
                backend=trusted_backend,
                phase_expectation=expectation,
                observation=observation,
                observation_values=_phase_observation_values(observation),
                backend_snapshot=backend_snapshot,
                # Private per-process entropy prevents a losing process from
                # terminalizing another process's newly won row claim.  Only
                # the bound digest is disclosed to the backend.
                claim_namespace_sha256=secrets.token_hex(32).upper(),
                control_state=STAGEC_RUNTIME_ROWS_ENABLED,
                attempt_states={},
                lock=threading.RLock(),
            )
            with _SEALS_LOCK:
                _ACTIVATION_SEALS[id(activation)] = activation_seal
        except BaseException as exc:
            seal.control_state = STAGEC_RUNTIME_ACTIVATION_INDETERMINATE
            if isinstance(exc, StageCRuntimeActivationError):
                raise
            if not isinstance(exc, Exception):
                raise
            raise StageCRuntimeActivationError(
                "BACKEND_OPERATION_FAILED", "phase backend call failed closed"
            ) from exc
        seal.control_state = STAGEC_RUNTIME_ROWS_ENABLED
        return activation


def _require_activation(activation: Any) -> _ActivationSeal:
    if type(activation) is not StageCRuntimePhaseActivation:
        _fail("PHASE_NOT_ROWS_ENABLED", "activation has the wrong exact type")
    with _SEALS_LOCK:
        seal = _ACTIVATION_SEALS.get(id(activation))
    try:
        invalid = (
            seal is None
            or seal.activation is not activation
            or activation.preparation is not seal.preparation_seal.preparation
            or activation.observation is not seal.observation
            or _phase_observation_values(activation.observation)
            != seal.observation_values
        )
    except Exception as exc:
        raise StageCRuntimeActivationError(
            "PHASE_NOT_ROWS_ENABLED",
            "activation observation no longer has an exact closed shape",
        ) from exc
    if invalid:
        _fail("PHASE_NOT_ROWS_ENABLED", "activation is not the unchanged backend result")
    _require_preparation(seal.preparation_seal.preparation)
    return seal


def stagec_runtime_phase_state(activation: StageCRuntimePhaseActivation) -> str:
    seal = _require_activation(activation)
    with seal.lock:
        return seal.control_state


def _replay_attempt_inputs(
    seal: _ActivationSeal,
    *,
    execution_ordinal: Any,
    study_request: Any,
    attempt_subject_sha256: Any,
    child_binding: Any,
    worker_authorization: Any,
    model_capture_target: Any,
) -> tuple[
    int,
    DiagnosticStudyRequestArtifact,
    str,
    DiagnosticChildExecutionBindingArtifact,
    DiagnosticWorkerAuthorizationV2Artifact,
    str,
]:
    prep = seal.preparation_seal
    private_shared = prep.private_shared_plan_context
    private_registration = prep.private_phase_registration
    if type(execution_ordinal) is not int or isinstance(execution_ordinal, bool):
        _fail("ATTEMPT_BINDING_INVALID", "execution ordinal must be an exact integer")
    ordinal = execution_ordinal
    if ordinal < 1 or ordinal > DIAGNOSTIC_CASE_COUNT:
        _fail("ATTEMPT_OUTSIDE_ROSTER", "execution ordinal is outside the 480-row roster")
    if type(study_request) is not DiagnosticStudyRequestArtifact:
        _fail("ATTEMPT_BINDING_INVALID", "study request has the wrong exact type")
    expected_request = private_registration.study_requests[ordinal - 1]
    try:
        request_raw = bytes(study_request.raw_bytes)
        request_ref = _ref_scalars(study_request.artifact_ref)
    except Exception as exc:
        raise StageCRuntimeActivationError(
            "ATTEMPT_BINDING_INVALID", "study request carrier could not be snapshotted"
        ) from exc
    if (
        request_raw != expected_request.raw_bytes
        or request_ref != _ref_scalars(expected_request.artifact_ref)
    ):
        _fail("ATTEMPT_BINDING_INVALID", "study request differs from the exact roster row")
    try:
        fresh_request = load_diagnostic_study_request(
            request_raw,
            chain=private_shared.chain,
            plan=private_shared.plan,
        )
        if fresh_request != study_request:
            raise ValueError("study request projection differs from exact bytes")
    except Exception as exc:
        raise StageCRuntimeActivationError(
            "ATTEMPT_BINDING_INVALID", "study request exact replay failed"
        ) from exc
    try:
        subject = expect_sha256(attempt_subject_sha256, "attempt_subject_sha256")
    except (SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRuntimeActivationError(
            "ATTEMPT_BINDING_INVALID", "attempt subject is not an exact SHA-256"
        ) from exc
    expected_subject = private_registration.ordered_subjects[ordinal - 1]
    derived = derive_diagnostic_attempt_subject_sha256(
        plan=private_shared.plan, study_request=fresh_request
    )
    if subject != expected_subject or subject != derived:
        _fail("ATTEMPT_OUTSIDE_ROSTER", "attempt subject differs from exact roster row")
    if type(child_binding) is not DiagnosticChildExecutionBindingArtifact:
        _fail("ATTEMPT_BINDING_INVALID", "child binding has the wrong exact type")
    if type(worker_authorization) is not DiagnosticWorkerAuthorizationV2Artifact:
        _fail("ATTEMPT_BINDING_INVALID", "worker authorization has the wrong exact type")
    if model_capture_target is not prep.model_capture_target:
        _fail("PERMIT_BINDING_MISMATCH", "model/capture target object was substituted")
    _require_target(model_capture_target)
    try:
        binding_raw = bytes(child_binding.raw_bytes)
        authorization_raw = bytes(worker_authorization.raw_bytes)
        fresh_binding = load_diagnostic_child_execution_binding(
            binding_raw,
            chain=private_shared.chain,
            plan=private_shared.plan,
            study_request=fresh_request,
            execution_contract=private_shared.execution_contract,
        )
        fresh_authorization = load_diagnostic_worker_authorization_v2(
            authorization_raw,
            chain=private_shared.chain,
            plan=private_shared.plan,
            study_request=fresh_request,
            execution_contract=private_shared.execution_contract,
            binding=fresh_binding,
        )
    except Exception as exc:
        raise StageCRuntimeActivationError(
            "ATTEMPT_BINDING_INVALID", "child binding/authorization exact replay failed"
        ) from exc
    if (
        binding_raw != fresh_binding.raw_bytes
        or authorization_raw != fresh_authorization.raw_bytes
        or fresh_binding != child_binding
        or fresh_authorization != worker_authorization
    ):
        _fail("ATTEMPT_BINDING_INVALID", "attempt dataclass differs from exact replay")
    worker = fresh_binding.payload["execution_context"]["worker_assignment"][
        "assigned_worker_id"
    ]
    try:
        worker = expect_machine_id(worker, "assigned_worker_id")
    except SchemaValidationError as exc:
        raise StageCRuntimeActivationError(
            "ATTEMPT_BINDING_INVALID", "assigned worker identity is invalid"
        ) from exc
    if (
        fresh_binding.case_execution_ordinal != ordinal
        or fresh_authorization.case_execution_ordinal != ordinal
        or fresh_binding.attempt_ordinal != 1
        or fresh_authorization.attempt_ordinal != 1
        or fresh_binding.payload["execution_context"]["attempt_binding"][
            "attempt_subject_sha256"
        ]
        != subject
        or fresh_authorization.payload["authority"]["execution_authority"]
        != "NOT_GRANTED_BY_CARRIER"
    ):
        _fail("ATTEMPT_BINDING_INVALID", "attempt ordinal/authority projection drifted")
    return (
        ordinal,
        fresh_request,
        subject,
        fresh_binding,
        fresh_authorization,
        worker,
    )


def _claim_expectation(
    seal: _ActivationSeal,
    *,
    ordinal: int,
    request: DiagnosticStudyRequestArtifact,
    subject: str,
    binding: DiagnosticChildExecutionBindingArtifact,
    authorization: DiagnosticWorkerAuthorizationV2Artifact,
    worker: str,
) -> StageCRuntimeAttemptClaimExpectation:
    prep = seal.preparation_seal
    phase = seal.phase_expectation
    backend = seal.backend_snapshot
    claim_operation_id = canonical_sha256(
        {
            "domain": "cas_harness_v2.stagec_runtime_claim_operation.v1",
            "process_namespace_sha256": seal.claim_namespace_sha256,
            "tenant_id": phase.tenant_id,
            "phase_id": phase.phase_id,
            "phase_subject_sha256": phase.phase_subject_sha256,
            "registration_ref": _ref_value(phase.registration_ref),
            "roster_closure_sha256": phase.roster_closure_sha256,
            "plan_ref": _ref_value(phase.plan_ref),
            "execution_contract_ref": _ref_value(phase.execution_contract_ref),
            "admission_ref": _ref_value(phase.admission_ref),
            "target_binding_sha256": phase.target_binding_sha256,
            "prospective_subject_sha256": phase.prospective_subject_sha256,
            "stagec_authorization_id": phase.authorization_id,
            "stagec_authorization_window_start": phase.authorization_window_start,
            "stagec_authorization_window_end": phase.authorization_window_end,
            "stagec_authorization_nonce_b64url": phase.authorization_nonce_b64url,
            "activation_provider_id": backend.provider_id,
            "activation_storage_object_key": backend.storage_object_key,
            "activation_storage_object_version_id": backend.storage_object_version_id,
            "activation_storage_checksum_sha256": backend.storage_checksum_sha256,
            "activation_storage_byte_length": backend.storage_byte_length,
            "activation_storage_retention_until": backend.storage_retention_until,
            "activation_storage_trusted_time": backend.storage_trusted_time,
            "activation_storage_observation_generation": (
                backend.storage_observation_generation
            ),
            "activation_issuer_id": backend.issuer_id,
            "activation_ledger_generation": backend.ledger_generation,
            "execution_ordinal": ordinal,
            "study_request_ref": _ref_value(request.artifact_ref),
            "attempt_subject_sha256": subject,
            "child_binding_ref": _ref_value(binding.artifact_ref),
            "worker_authorization_ref": _ref_value(authorization.artifact_ref),
            "assigned_worker_id": worker,
            "diagnostic_not_before": authorization.not_before,
            "diagnostic_expires_at": authorization.expires_at,
            "run_nonce_b64url": authorization.run_nonce_b64url,
            "model_capture_target_sha256": phase.model_capture_target_sha256,
        }
    )
    return StageCRuntimeAttemptClaimExpectation(
        tenant_id=phase.tenant_id,
        phase_id=phase.phase_id,
        phase_subject_sha256=phase.phase_subject_sha256,
        registration_ref=phase.registration_ref,
        roster_closure_sha256=phase.roster_closure_sha256,
        plan_ref=phase.plan_ref,
        execution_contract_ref=phase.execution_contract_ref,
        admission_ref=phase.admission_ref,
        target_binding_sha256=phase.target_binding_sha256,
        prospective_subject_sha256=phase.prospective_subject_sha256,
        stagec_authorization_id=phase.authorization_id,
        stagec_authorization_window_start=phase.authorization_window_start,
        stagec_authorization_window_end=phase.authorization_window_end,
        stagec_authorization_nonce_b64url=phase.authorization_nonce_b64url,
        activation_provider_id=backend.provider_id,
        activation_storage_object_key=backend.storage_object_key,
        activation_storage_object_version_id=backend.storage_object_version_id,
        activation_storage_checksum_sha256=backend.storage_checksum_sha256,
        activation_storage_byte_length=backend.storage_byte_length,
        activation_storage_retention_until=backend.storage_retention_until,
        activation_storage_trusted_time=backend.storage_trusted_time,
        activation_storage_observation_generation=backend.storage_observation_generation,
        activation_issuer_id=backend.issuer_id,
        activation_ledger_generation=backend.ledger_generation,
        execution_ordinal=ordinal,
        study_request_ref=request.artifact_ref,
        attempt_subject_sha256=subject,
        child_binding_ref=binding.artifact_ref,
        worker_authorization_ref=authorization.artifact_ref,
        assigned_worker_id=worker,
        diagnostic_not_before=authorization.not_before,
        diagnostic_expires_at=authorization.expires_at,
        run_nonce_b64url=authorization.run_nonce_b64url,
        model_capture_target_sha256=phase.model_capture_target_sha256,
        claim_operation_id=claim_operation_id,
    )


def _lease_values(lease: StageCRuntimeWorkerLeaseObservation) -> tuple[Any, ...]:
    return (
        lease.lease_id,
        lease.authenticated_tenant_id,
        lease.authenticated_worker_id,
        lease.provider_id,
        lease.phase_id,
        lease.phase_subject_sha256,
        lease.issued_at,
        lease.not_before,
        lease.expires_at,
        lease.lease_generation,
        lease.state,
    )


def _claim_observation_values(
    observation: StageCRuntimeAttemptClaimObservation,
) -> tuple[Any, ...]:
    return (
        observation.storage,
        _storage_values(observation.storage),
        observation.authorization,
        _issuer_values(observation.authorization),
        observation.worker_lease,
        _lease_values(observation.worker_lease),
        observation.claim_id,
        observation.claim_operation_id,
        observation.claim_generation,
        observation.claim_state,
        observation.claimed_now,
        observation.execution_ordinal,
        observation.study_request_sha256,
        observation.attempt_subject_sha256,
        observation.child_binding_sha256,
        observation.worker_authorization_sha256,
        observation.registration_sha256,
        observation.roster_closure_sha256,
        observation.model_capture_target_sha256,
    )


def _detach_worker_lease_observation(
    observation: Any,
) -> StageCRuntimeWorkerLeaseObservation:
    if type(observation) is not StageCRuntimeWorkerLeaseObservation:
        _fail("WORKER_LEASE_INVALID", "worker lease has the wrong exact immutable type")
    before = _lease_values(observation)
    detached = StageCRuntimeWorkerLeaseObservation(*before)
    if _lease_values(observation) != before:
        _fail("WORKER_LEASE_INVALID", "worker lease changed while being detached")
    return detached


def _detach_claim_observation(
    observation: Any,
) -> StageCRuntimeAttemptClaimObservation:
    if type(observation) is not StageCRuntimeAttemptClaimObservation:
        _fail("CLAIM_OBSERVATION_INVALID", "claim observation has the wrong exact type")
    before = (
        _storage_values(observation.storage),
        _issuer_values(observation.authorization),
        _lease_values(observation.worker_lease),
        observation.claim_id,
        observation.claim_operation_id,
        observation.claim_generation,
        observation.claim_state,
        observation.claimed_now,
        observation.execution_ordinal,
        observation.study_request_sha256,
        observation.attempt_subject_sha256,
        observation.child_binding_sha256,
        observation.worker_authorization_sha256,
        observation.registration_sha256,
        observation.roster_closure_sha256,
        observation.model_capture_target_sha256,
    )
    detached = StageCRuntimeAttemptClaimObservation(
        storage=_detach_storage_observation(observation.storage, claim=True),
        authorization=_detach_issuer_observation(observation.authorization, claim=True),
        worker_lease=_detach_worker_lease_observation(observation.worker_lease),
        claim_id=before[3],
        claim_operation_id=before[4],
        claim_generation=before[5],
        claim_state=before[6],
        claimed_now=before[7],
        execution_ordinal=before[8],
        study_request_sha256=before[9],
        attempt_subject_sha256=before[10],
        child_binding_sha256=before[11],
        worker_authorization_sha256=before[12],
        registration_sha256=before[13],
        roster_closure_sha256=before[14],
        model_capture_target_sha256=before[15],
    )
    after = (
        _storage_values(observation.storage),
        _issuer_values(observation.authorization),
        _lease_values(observation.worker_lease),
        observation.claim_id,
        observation.claim_operation_id,
        observation.claim_generation,
        observation.claim_state,
        observation.claimed_now,
        observation.execution_ordinal,
        observation.study_request_sha256,
        observation.attempt_subject_sha256,
        observation.child_binding_sha256,
        observation.worker_authorization_sha256,
        observation.registration_sha256,
        observation.roster_closure_sha256,
        observation.model_capture_target_sha256,
    )
    if after != before:
        _fail("CLAIM_OBSERVATION_INVALID", "claim observation changed while being detached")
    return detached


def _phase_from_claim_expectation(
    expectation: StageCRuntimeAttemptClaimExpectation,
) -> StageCRuntimePhaseActivationExpectation:
    return StageCRuntimePhaseActivationExpectation(
        tenant_id=expectation.tenant_id,
        authenticated_worker_id=expectation.assigned_worker_id,
        phase_id=expectation.phase_id,
        phase_subject_sha256=expectation.phase_subject_sha256,
        registration_ref=expectation.registration_ref,
        roster_closure_sha256=expectation.roster_closure_sha256,
        plan_ref=expectation.plan_ref,
        execution_contract_ref=expectation.execution_contract_ref,
        admission_ref=expectation.admission_ref,
        external_binding_report_ref=expectation.admission_ref,
        target_binding_sha256=expectation.target_binding_sha256,
        prospective_subject_sha256=expectation.prospective_subject_sha256,
        authorization_id=expectation.stagec_authorization_id,
        authorization_window_start=expectation.stagec_authorization_window_start,
        authorization_window_end=expectation.stagec_authorization_window_end,
        authorization_nonce_b64url=expectation.stagec_authorization_nonce_b64url,
        corpus_ref=expectation.admission_ref,
        storage_receipt_ref=expectation.admission_ref,
        storage_object_version_id=expectation.activation_storage_object_version_id,
        storage_checksum_sha256=expectation.activation_storage_checksum_sha256,
        storage_byte_length=expectation.activation_storage_byte_length,
        storage_retention_until=expectation.activation_storage_retention_until,
        model_capture_target_sha256=expectation.model_capture_target_sha256,
        startup_canary_policy=STAGEC_RUNTIME_STARTUP_CANARY,
    )


def _validate_worker_lease(
    lease: Any,
    expectation: StageCRuntimeAttemptClaimExpectation,
    trusted_now: datetime,
) -> None:
    if type(lease) is not StageCRuntimeWorkerLeaseObservation:
        _fail("WORKER_LEASE_INVALID", "worker lease has the wrong exact immutable type")
    for field, value in (
        ("lease_id", lease.lease_id),
        ("authenticated_tenant_id", lease.authenticated_tenant_id),
        ("authenticated_worker_id", lease.authenticated_worker_id),
        ("provider_id", lease.provider_id),
        ("phase_id", lease.phase_id),
    ):
        _machine(value, f"worker_lease.{field}", claim=True)
    _sha(lease.phase_subject_sha256, "worker_lease.phase_subject_sha256", claim=True)
    _positive_int(lease.lease_generation, "worker_lease.lease_generation", claim=True)
    issued = _time(lease.issued_at, "worker_lease.issued_at")
    not_before = _time(lease.not_before, "worker_lease.not_before")
    expires = _time(lease.expires_at, "worker_lease.expires_at")
    diagnostic_expiry = _time(expectation.diagnostic_expires_at, "diagnostic.expires_at")
    if (
        lease.authenticated_tenant_id != expectation.tenant_id
        or lease.authenticated_worker_id != expectation.assigned_worker_id
        or lease.provider_id != expectation.activation_provider_id
        or lease.phase_id != expectation.phase_id
        or lease.phase_subject_sha256 != expectation.phase_subject_sha256
        or lease.state != "ACTIVE"
        or not (issued <= trusted_now and not_before <= trusted_now < expires)
        or expires > diagnostic_expiry
    ):
        _fail("WORKER_LEASE_INVALID", "worker lease identity or half-open window drifted")


def _validate_claim_observation(
    observation: Any,
    expectation: StageCRuntimeAttemptClaimExpectation,
) -> StageCRuntimeAttemptClaimObservation:
    if type(observation) is not StageCRuntimeAttemptClaimObservation:
        _fail("CLAIM_OBSERVATION_INVALID", "claim observation has the wrong exact type")
    _validate_storage(
        observation.storage,
        tenant_id=expectation.tenant_id,
        worker_id=expectation.assigned_worker_id,
        expected_version=expectation.activation_storage_object_version_id,
        expected_checksum=expectation.activation_storage_checksum_sha256,
        expected_length=expectation.activation_storage_byte_length,
        expected_retention=expectation.activation_storage_retention_until,
        window_start=expectation.stagec_authorization_window_start,
        window_end=expectation.stagec_authorization_window_end,
        claim=True,
    )
    if (
        observation.storage.provider_id != expectation.activation_provider_id
        or observation.storage.object_key != expectation.activation_storage_object_key
        or observation.storage.observation_generation
        <= expectation.activation_storage_observation_generation
        or _time(observation.storage.trusted_time, "claim.storage.trusted_time")
        < _time(
            expectation.activation_storage_trusted_time,
            "activation.storage.trusted_time",
        )
    ):
        _fail(
            "CLAIM_BINDING_MISMATCH",
            "provider storage object/generation/time drifted after activation",
        )
    phase_expectation = _phase_from_claim_expectation(expectation)
    _validate_issuer(
        observation.authorization,
        expectation=phase_expectation,
        tenant_id=expectation.tenant_id,
        worker_id=expectation.assigned_worker_id,
        claim=True,
        expected_issuer_id=expectation.activation_issuer_id,
        minimum_generation=expectation.activation_ledger_generation,
    )
    now = _time(observation.storage.trusted_time, "claim.storage.trusted_time")
    diagnostic_start = _time(expectation.diagnostic_not_before, "diagnostic.not_before")
    diagnostic_end = _time(expectation.diagnostic_expires_at, "diagnostic.expires_at")
    if not (diagnostic_start <= now < diagnostic_end):
        _fail("CLAIM_BINDING_MISMATCH", "claim trusted time is outside child authorization")
    _validate_worker_lease(observation.worker_lease, expectation, now)
    _machine(observation.claim_id, "claim.claim_id", claim=True)
    _sha(observation.claim_operation_id, "claim.claim_operation_id", claim=True)
    _positive_int(observation.claim_generation, "claim.claim_generation", claim=True)
    for field, value in (
        ("study_request_sha256", observation.study_request_sha256),
        ("attempt_subject_sha256", observation.attempt_subject_sha256),
        ("child_binding_sha256", observation.child_binding_sha256),
        ("worker_authorization_sha256", observation.worker_authorization_sha256),
        ("registration_sha256", observation.registration_sha256),
        ("roster_closure_sha256", observation.roster_closure_sha256),
        ("model_capture_target_sha256", observation.model_capture_target_sha256),
    ):
        _sha(value, f"claim.{field}", claim=True)
    if (
        type(observation.claimed_now) is not bool
        or not observation.claimed_now
        or observation.claim_state != "CLAIMED"
    ):
        _fail("CLAIM_NOT_NEWLY_WON", "durable attempt claim was not newly won")
    if (
        type(observation.execution_ordinal) is not int
        or isinstance(observation.execution_ordinal, bool)
        or observation.execution_ordinal != expectation.execution_ordinal
        or observation.study_request_sha256 != expectation.study_request_ref.sha256
        or observation.claim_operation_id != expectation.claim_operation_id
        or observation.attempt_subject_sha256 != expectation.attempt_subject_sha256
        or observation.child_binding_sha256 != expectation.child_binding_ref.sha256
        or observation.worker_authorization_sha256
        != expectation.worker_authorization_ref.sha256
        or observation.registration_sha256 != expectation.registration_ref.sha256
        or observation.roster_closure_sha256 != expectation.roster_closure_sha256
        or observation.model_capture_target_sha256
        != expectation.model_capture_target_sha256
    ):
        _fail("CLAIM_BINDING_MISMATCH", "durable claim differs from exact attempt bindings")
    return observation


def _validate_ambiguous_claim_terminal_observation(
    observation: Any,
    expectation: StageCRuntimeAttemptClaimExpectation,
) -> StageCRuntimeAmbiguousClaimTerminalObservation:
    if type(observation) is not StageCRuntimeAmbiguousClaimTerminalObservation:
        _fail(
            "AMBIGUOUS_CLAIM_TERMINAL_OBSERVATION_INVALID",
            "ambiguous-claim terminal receipt has the wrong exact immutable type",
        )
    try:
        expect_sha256(observation.claim_operation_id, "claim_operation_id")
        expect_sha256(observation.attempt_subject_sha256, "attempt_subject_sha256")
        expect_sha256(observation.phase_subject_sha256, "phase_subject_sha256")
        expect_sha256(observation.registration_sha256, "registration_sha256")
        expect_sha256(observation.roster_closure_sha256, "roster_closure_sha256")
        expect_sha256(
            observation.model_capture_target_sha256,
            "model_capture_target_sha256",
        )
        expect_machine_id(
            observation.authenticated_tenant_id, "authenticated_tenant_id"
        )
        expect_machine_id(
            observation.authenticated_worker_id, "authenticated_worker_id"
        )
        expect_machine_id(observation.phase_id, "phase_id")
        expect_int(
            observation.prior_ledger_generation,
            "prior_ledger_generation",
            minimum=1,
        )
        expect_int(observation.ledger_generation, "ledger_generation", minimum=1)
    except (SchemaValidationError, TypeError, ValueError) as exc:
        raise StageCRuntimeActivationError(
            "AMBIGUOUS_CLAIM_TERMINAL_OBSERVATION_INVALID",
            "ambiguous-claim terminal receipt contains invalid fields",
        ) from exc
    if (
        type(observation.terminalized_now) is not bool
        or not observation.terminalized_now
        or observation.claim_state != STAGEC_RUNTIME_PERMIT_INDETERMINATE
    ):
        _fail(
            "AMBIGUOUS_CLAIM_TERMINALIZATION_FAILED",
            "backend did not newly terminalize the ambiguous logical row",
        )
    if (
        observation.claim_operation_id != expectation.claim_operation_id
        or type(observation.execution_ordinal) is not int
        or isinstance(observation.execution_ordinal, bool)
        or observation.execution_ordinal != expectation.execution_ordinal
        or observation.attempt_subject_sha256 != expectation.attempt_subject_sha256
        or observation.authenticated_tenant_id != expectation.tenant_id
        or observation.authenticated_worker_id != expectation.assigned_worker_id
        or observation.phase_id != expectation.phase_id
        or observation.phase_subject_sha256 != expectation.phase_subject_sha256
        or observation.registration_sha256 != expectation.registration_ref.sha256
        or observation.roster_closure_sha256 != expectation.roster_closure_sha256
        or observation.model_capture_target_sha256
        != expectation.model_capture_target_sha256
        or observation.invalidation_reason != "AMBIGUOUS_DURABLE_CLAIM_RESULT"
        or observation.prior_ledger_generation
        < expectation.activation_ledger_generation
        or observation.ledger_generation <= observation.prior_ledger_generation
    ):
        _fail(
            "AMBIGUOUS_CLAIM_TERMINAL_BINDING_MISMATCH",
            "ambiguous-claim terminal receipt differs from the sealed operation",
        )
    return observation


def _ambiguous_terminal_observation_values(
    observation: StageCRuntimeAmbiguousClaimTerminalObservation,
) -> tuple[Any, ...]:
    return tuple(
        getattr(observation, item.name)
        for item in fields(StageCRuntimeAmbiguousClaimTerminalObservation)
    )


def _detach_ambiguous_terminal_observation(
    observation: Any,
) -> StageCRuntimeAmbiguousClaimTerminalObservation:
    if type(observation) is not StageCRuntimeAmbiguousClaimTerminalObservation:
        _fail(
            "AMBIGUOUS_CLAIM_TERMINAL_OBSERVATION_INVALID",
            "ambiguous-claim terminal receipt has the wrong exact type",
        )
    before = _ambiguous_terminal_observation_values(observation)
    detached = StageCRuntimeAmbiguousClaimTerminalObservation(*before)
    if _ambiguous_terminal_observation_values(observation) != before:
        _fail(
            "AMBIGUOUS_CLAIM_TERMINAL_OBSERVATION_INVALID",
            "ambiguous-claim terminal receipt changed while being detached",
        )
    return detached


def _terminalize_ambiguous_claim_result(
    seal: _ActivationSeal,
    expectation: StageCRuntimeAttemptClaimExpectation,
) -> StageCRuntimeAmbiguousClaimTerminalObservation:
    """Terminalize by sealed logical operation, never by untrusted claim output."""

    try:
        backend_expectation = _disposable_backend_expectation(expectation)
        backend_expectation_values = _backend_expectation_values(
            backend_expectation
        )
        observation = seal.backend.terminalize_ambiguous_attempt_claim(
            backend_expectation,
            claim_operation_id=expectation.claim_operation_id,
            invalidation_reason="AMBIGUOUS_DURABLE_CLAIM_RESULT",
        )
        _require_disposable_expectation_unchanged(
            backend_expectation,
            backend_expectation_values,
            error_code="AMBIGUOUS_CLAIM_TERMINAL_OBSERVATION_INVALID",
        )
        observation = _detach_ambiguous_terminal_observation(observation)
    except BaseException as exc:
        raise StageCRuntimeActivationError(
            "AMBIGUOUS_CLAIM_TERMINALIZATION_FAILED",
            "ambiguous durable claim could not be terminalized and cannot be retried",
        ) from exc
    return _validate_ambiguous_claim_terminal_observation(observation, expectation)


def _claim_stagec_runtime_attempt(
    activation: StageCRuntimePhaseActivation,
    *,
    execution_ordinal: int,
    study_request: DiagnosticStudyRequestArtifact,
    attempt_subject_sha256: str,
    child_binding: DiagnosticChildExecutionBindingArtifact,
    worker_authorization: DiagnosticWorkerAuthorizationV2Artifact,
    model_capture_target: StageCRuntimeModelCaptureTarget,
) -> StageCRuntimeDispatchPermit:
    """Return a permit only to a newly winning durable exact-row claim."""

    seal = _require_activation(activation)
    with seal.lock:
        # Replay, detached expectation construction, and backend crossing share
        # one lock interval.  Rechecking here closes the public-observation
        # TOCTOU between the outer lookup and the durable CAS.
        if _require_activation(activation) is not seal:
            _fail("PHASE_NOT_ROWS_ENABLED", "activation seal identity changed")
        if seal.control_state != STAGEC_RUNTIME_ROWS_ENABLED:
            _fail("PHASE_NOT_ROWS_ENABLED", "phase does not permit row claims")
        (
            ordinal,
            request,
            subject,
            binding,
            authorization,
            worker,
        ) = _replay_attempt_inputs(
            seal,
            execution_ordinal=execution_ordinal,
            study_request=study_request,
            attempt_subject_sha256=attempt_subject_sha256,
            child_binding=child_binding,
            worker_authorization=worker_authorization,
            model_capture_target=model_capture_target,
        )
        expectation = _claim_expectation(
            seal,
            ordinal=ordinal,
            request=request,
            subject=subject,
            binding=binding,
            authorization=authorization,
            worker=worker,
        )
        prior = seal.attempt_states.get(subject)
        if prior == STAGEC_RUNTIME_PERMIT_INDETERMINATE:
            _fail("ATTEMPT_CLAIM_INDETERMINATE", "attempt claim cannot be retried")
        if prior is not None:
            _fail("ATTEMPT_ALREADY_CLAIMED", "attempt already has a local claim result")
        seal.attempt_states[subject] = "CLAIM_IN_PROGRESS"
        try:
            backend_expectation = _disposable_backend_expectation(expectation)
            backend_expectation_values = _backend_expectation_values(
                backend_expectation
            )
            returned_observation = seal.backend.claim_attempt(backend_expectation)
            _require_disposable_expectation_unchanged(
                backend_expectation,
                backend_expectation_values,
                error_code="CLAIM_OBSERVATION_INVALID",
            )
            observation = _detach_claim_observation(
                returned_observation
            )
            observation = _validate_claim_observation(observation, expectation)
            permit = object.__new__(StageCRuntimeDispatchPermit)
            permit_seal = _PermitSeal(
                permit=permit,
                activation_seal=seal,
                expectation=expectation,
                observation=observation,
                observation_values=_claim_observation_values(observation),
                backend_snapshot=_ClaimBackendSnapshot(
                    claim_id=observation.claim_id,
                    claim_generation=observation.claim_generation,
                ),
                # Retain caller object identities only for substitution
                # rejection; backend mechanics used detached exact replays.
                study_request=study_request,
                child_binding=child_binding,
                worker_authorization=worker_authorization,
                model_capture_target=model_capture_target,
                control_state=STAGEC_RUNTIME_PERMIT_UNREDEEMED,
            )
            seal.attempt_states[subject] = STAGEC_RUNTIME_PERMIT_UNREDEEMED
            with _SEALS_LOCK:
                _PERMIT_SEALS[id(permit)] = permit_seal
        except BaseException as claim_error:
            # The backend may have won the durable CAS before failing to
            # return a usable receipt.  Burn locally first, then terminalize
            # the sealed logical operation without consulting any returned
            # claim ID or generation.  Neither path is retryable.
            seal.attempt_states[subject] = STAGEC_RUNTIME_PERMIT_INDETERMINATE
            _terminalize_ambiguous_claim_result(seal, expectation)
            if isinstance(claim_error, StageCRuntimeActivationError):
                raise claim_error
            if not isinstance(claim_error, Exception):
                raise claim_error
            raise StageCRuntimeActivationError(
                "BACKEND_OPERATION_FAILED", "attempt-claim backend call failed closed"
            ) from claim_error
        return permit


def _require_permit(permit: Any) -> _PermitSeal:
    if type(permit) is not StageCRuntimeDispatchPermit:
        _fail("PERMIT_INVALID", "dispatch permit has the wrong exact type")
    with _SEALS_LOCK:
        seal = _PERMIT_SEALS.get(id(permit))
    if seal is None or seal.permit is not permit:
        _fail("PERMIT_INVALID", "dispatch permit is not the unchanged process-sealed object")
    activation_seal = seal.activation_seal
    with activation_seal.lock:
        try:
            if _claim_observation_values(seal.observation) != seal.observation_values:
                _fail("PERMIT_INVALID", "sealed claim observation value drifted")
            _require_activation(activation_seal.activation)
        except Exception as integrity_error:
            if seal.control_state == STAGEC_RUNTIME_PERMIT_UNREDEEMED:
                try:
                    _invalidate_permit_from_seal(
                        seal,
                        invalidation_reason="WORKER_BINDING_RECHECK_FAILED",
                    )
                except StageCRuntimeActivationError as invalidation_error:
                    raise StageCRuntimeActivationError(
                        "CLAIM_INVALIDATION_FAILED",
                        "post-claim carrier drift could not be durably terminalized",
                    ) from invalidation_error
            if isinstance(integrity_error, StageCRuntimeActivationError):
                raise integrity_error
            raise StageCRuntimeActivationError(
                "PERMIT_INVALID",
                "post-claim carrier integrity read failed closed",
            ) from integrity_error
    return seal


def stagec_runtime_dispatch_permit_state(permit: StageCRuntimeDispatchPermit) -> str:
    seal = _require_permit(permit)
    with seal.activation_seal.lock:
        return seal.control_state


def _require_permit_bindings(
    permit_seal: _PermitSeal,
    *,
    activation: Any,
    execution_ordinal: Any,
    study_request: Any,
    attempt_subject_sha256: Any,
    child_binding: Any,
    worker_authorization: Any,
    model_capture_target: Any,
) -> None:
    expectation = permit_seal.expectation
    if (
        activation is not permit_seal.activation_seal.activation
        or execution_ordinal != expectation.execution_ordinal
        or study_request is not permit_seal.study_request
        or attempt_subject_sha256 != expectation.attempt_subject_sha256
        or child_binding is not permit_seal.child_binding
        or worker_authorization is not permit_seal.worker_authorization
        or model_capture_target is not permit_seal.model_capture_target
    ):
        _fail("PERMIT_BINDING_MISMATCH", "permit use substituted an exact claim binding")
    # Re-run all structural loaders before the atomic local state transition.
    replayed = _replay_attempt_inputs(
        permit_seal.activation_seal,
        execution_ordinal=execution_ordinal,
        study_request=study_request,
        attempt_subject_sha256=attempt_subject_sha256,
        child_binding=child_binding,
        worker_authorization=worker_authorization,
        model_capture_target=model_capture_target,
    )
    if (
        replayed[0] != expectation.execution_ordinal
        or replayed[2] != expectation.attempt_subject_sha256
        or replayed[5] != expectation.assigned_worker_id
    ):
        _fail("PERMIT_BINDING_MISMATCH", "permit binding replay drifted")


def redeem_stagec_runtime_dispatch_permit(
    permit: StageCRuntimeDispatchPermit,
    *,
    activation: StageCRuntimePhaseActivation,
    execution_ordinal: int,
    study_request: DiagnosticStudyRequestArtifact,
    attempt_subject_sha256: str,
    child_binding: DiagnosticChildExecutionBindingArtifact,
    worker_authorization: DiagnosticWorkerAuthorizationV2Artifact,
    model_capture_target: StageCRuntimeModelCaptureTarget,
) -> None:
    """Atomically burn one exact permit; return no execution authority object."""

    seal = _require_permit(permit)
    activation_seal = seal.activation_seal
    with activation_seal.lock:
        if _require_permit(permit) is not seal:
            _fail("PERMIT_INVALID", "permit seal identity changed before redemption")
        if seal.control_state == STAGEC_RUNTIME_PERMIT_REDEEMED:
            _fail("PERMIT_ALREADY_REDEEMED", "dispatch permit was already burned")
        if seal.control_state == STAGEC_RUNTIME_PERMIT_INVALIDATED:
            _fail("PERMIT_INVALIDATED", "dispatch permit was invalidated before dispatch")
        if seal.control_state == STAGEC_RUNTIME_PERMIT_INDETERMINATE:
            _fail("PERMIT_INDETERMINATE", "dispatch permit is permanently indeterminate")
        try:
            _require_permit_bindings(
                seal,
                activation=activation,
                execution_ordinal=execution_ordinal,
                study_request=study_request,
                attempt_subject_sha256=attempt_subject_sha256,
                child_binding=child_binding,
                worker_authorization=worker_authorization,
                model_capture_target=model_capture_target,
            )
            if activation_seal.control_state != STAGEC_RUNTIME_ROWS_ENABLED:
                _fail("PHASE_NOT_ROWS_ENABLED", "phase stopped permitting row dispatch")
        except StageCRuntimeActivationError as use_error:
            try:
                _invalidate_permit_from_seal(
                    seal, invalidation_reason="WORKER_BINDING_RECHECK_FAILED"
                )
            except StageCRuntimeActivationError as invalidation_error:
                raise StageCRuntimeActivationError(
                    "CLAIM_INVALIDATION_FAILED",
                    "invalid permit use and durable invalidation is indeterminate",
                ) from invalidation_error
            raise use_error
        seal.control_state = STAGEC_RUNTIME_PERMIT_REDEEMED
        activation_seal.attempt_states[expectation_subject := seal.expectation.attempt_subject_sha256] = (
            STAGEC_RUNTIME_PERMIT_REDEEMED
        )
        del expectation_subject
    return None


def _invalidation_values(
    observation: StageCRuntimeAttemptInvalidationObservation,
) -> tuple[Any, ...]:
    return (
        observation.claim_id,
        observation.claim_generation,
        observation.claim_state,
        observation.invalidated_now,
        observation.execution_ordinal,
        observation.attempt_subject_sha256,
        observation.authenticated_tenant_id,
        observation.authenticated_worker_id,
        observation.phase_id,
        observation.phase_subject_sha256,
        observation.invalidation_reason,
        observation.ledger_generation,
    )


def _detach_invalidation_observation(
    observation: Any,
) -> StageCRuntimeAttemptInvalidationObservation:
    if type(observation) is not StageCRuntimeAttemptInvalidationObservation:
        _fail(
            "INVALIDATION_OBSERVATION_INVALID",
            "invalidation receipt has the wrong exact immutable type",
        )
    before = _invalidation_values(observation)
    detached = StageCRuntimeAttemptInvalidationObservation(*before)
    if _invalidation_values(observation) != before:
        _fail(
            "INVALIDATION_OBSERVATION_INVALID",
            "invalidation receipt changed while being detached",
        )
    return detached


def _validate_invalidation_observation(
    observation: Any,
    expectation: StageCRuntimeAttemptInvalidationExpectation,
) -> StageCRuntimeAttemptInvalidationObservation:
    if type(observation) is not StageCRuntimeAttemptInvalidationObservation:
        _fail(
            "INVALIDATION_OBSERVATION_INVALID",
            "invalidation observation has the wrong exact type",
        )
    for field, value in (
        ("claim_id", observation.claim_id),
        ("authenticated_tenant_id", observation.authenticated_tenant_id),
        ("authenticated_worker_id", observation.authenticated_worker_id),
        ("phase_id", observation.phase_id),
    ):
        _machine(value, f"invalidation.{field}", claim=True)
    _sha(
        observation.attempt_subject_sha256,
        "invalidation.attempt_subject_sha256",
        claim=True,
    )
    _sha(
        observation.phase_subject_sha256,
        "invalidation.phase_subject_sha256",
        claim=True,
    )
    _positive_int(observation.claim_generation, "invalidation.claim_generation", claim=True)
    _positive_int(observation.ledger_generation, "invalidation.ledger_generation", claim=True)
    if (
        type(observation.invalidated_now) is not bool
        or not observation.invalidated_now
        or observation.claim_state != "INDETERMINATE"
    ):
        _fail("CLAIM_INVALIDATION_FAILED", "backend did not newly terminalize the claim")
    if (
        observation.claim_id != expectation.claim_id
        or observation.claim_generation != expectation.claim_generation
        or type(observation.execution_ordinal) is not int
        or isinstance(observation.execution_ordinal, bool)
        or observation.execution_ordinal != expectation.execution_ordinal
        or observation.attempt_subject_sha256 != expectation.attempt_subject_sha256
        or observation.authenticated_tenant_id != expectation.tenant_id
        or observation.authenticated_worker_id != expectation.assigned_worker_id
        or observation.phase_id != expectation.phase_id
        or observation.phase_subject_sha256 != expectation.phase_subject_sha256
        or observation.invalidation_reason != expectation.invalidation_reason
        or observation.ledger_generation <= expectation.claim_generation
    ):
        _fail(
            "INVALIDATION_BINDING_MISMATCH",
            "backend invalidation differs from the exact won claim",
        )
    return observation


def _invalidate_permit_from_seal(
    seal: _PermitSeal,
    *,
    invalidation_reason: str,
) -> StageCRuntimeAttemptInvalidationObservation:
    """Terminalize using only the original sealed claim, never caller substitutions."""

    if (
        type(invalidation_reason) is not str
        or invalidation_reason not in _INVALIDATION_REASON_SET
    ):
        _fail("INVALIDATION_REASON_INVALID", "invalidation reason is outside the closed set")
    activation_seal = seal.activation_seal
    if seal.control_state == STAGEC_RUNTIME_PERMIT_REDEEMED:
        _fail("PERMIT_ALREADY_REDEEMED", "a redeemed permit cannot be invalidated")
    if seal.control_state == STAGEC_RUNTIME_PERMIT_INVALIDATED:
        _fail("PERMIT_INVALIDATED", "claim was already invalidated")
    if seal.control_state == STAGEC_RUNTIME_PERMIT_INDETERMINATE:
        _fail("PERMIT_INDETERMINATE", "claim invalidation cannot be retried")
    expectation = StageCRuntimeAttemptInvalidationExpectation(
        tenant_id=seal.expectation.tenant_id,
        phase_id=seal.expectation.phase_id,
        phase_subject_sha256=seal.expectation.phase_subject_sha256,
        execution_ordinal=seal.expectation.execution_ordinal,
        attempt_subject_sha256=seal.expectation.attempt_subject_sha256,
        assigned_worker_id=seal.expectation.assigned_worker_id,
        claim_id=seal.backend_snapshot.claim_id,
        claim_generation=seal.backend_snapshot.claim_generation,
        invalidation_reason=invalidation_reason,
        registration_sha256=seal.expectation.registration_ref.sha256,
        roster_closure_sha256=seal.expectation.roster_closure_sha256,
        model_capture_target_sha256=seal.expectation.model_capture_target_sha256,
    )
    # Burn locally before crossing the backend boundary.  A lost or malformed
    # response can never be followed by dispatch or retry.
    seal.control_state = STAGEC_RUNTIME_PERMIT_INDETERMINATE
    activation_seal.attempt_states[seal.expectation.attempt_subject_sha256] = (
        STAGEC_RUNTIME_PERMIT_INDETERMINATE
    )
    try:
        backend_expectation = _disposable_backend_expectation(expectation)
        backend_expectation_values = _backend_expectation_values(
            backend_expectation
        )
        observation = activation_seal.backend.invalidate_attempt_claim(
            backend_expectation
        )
        _require_disposable_expectation_unchanged(
            backend_expectation,
            backend_expectation_values,
            error_code="INVALIDATION_OBSERVATION_INVALID",
        )
        observation = _detach_invalidation_observation(observation)
        observation = _validate_invalidation_observation(observation, expectation)
    except StageCRuntimeActivationError:
        raise
    except Exception as exc:
        raise StageCRuntimeActivationError(
            "CLAIM_INVALIDATION_FAILED",
            "claim invalidation backend call is indeterminate and cannot be retried",
        ) from exc
    seal.control_state = STAGEC_RUNTIME_PERMIT_INVALIDATED
    activation_seal.attempt_states[seal.expectation.attempt_subject_sha256] = (
        STAGEC_RUNTIME_PERMIT_INVALIDATED
    )
    _invalidation_values(observation)
    return observation


def invalidate_stagec_runtime_attempt_claim(
    permit: StageCRuntimeDispatchPermit,
    *,
    activation: StageCRuntimePhaseActivation,
    execution_ordinal: int,
    study_request: DiagnosticStudyRequestArtifact,
    attempt_subject_sha256: str,
    child_binding: DiagnosticChildExecutionBindingArtifact,
    worker_authorization: DiagnosticWorkerAuthorizationV2Artifact,
    model_capture_target: StageCRuntimeModelCaptureTarget,
    invalidation_reason: str,
) -> StageCRuntimeAttemptInvalidationObservation:
    """Durably terminalize a won claim before any dispatch, with no retry."""

    if type(invalidation_reason) is not str or invalidation_reason not in _INVALIDATION_REASON_SET:
        _fail("INVALIDATION_REASON_INVALID", "invalidation reason is outside the closed set")
    seal = _require_permit(permit)
    activation_seal = seal.activation_seal
    with activation_seal.lock:
        if _require_permit(permit) is not seal:
            _fail("PERMIT_INVALID", "permit seal identity changed before terminalization")
        if seal.control_state == STAGEC_RUNTIME_PERMIT_REDEEMED:
            _fail("PERMIT_ALREADY_REDEEMED", "a redeemed permit cannot be invalidated")
        if seal.control_state == STAGEC_RUNTIME_PERMIT_INVALIDATED:
            _fail("PERMIT_INVALIDATED", "claim was already invalidated")
        if seal.control_state == STAGEC_RUNTIME_PERMIT_INDETERMINATE:
            _fail("PERMIT_INDETERMINATE", "claim invalidation cannot be retried")
        try:
            _require_permit_bindings(
                seal,
                activation=activation,
                execution_ordinal=execution_ordinal,
                study_request=study_request,
                attempt_subject_sha256=attempt_subject_sha256,
                child_binding=child_binding,
                worker_authorization=worker_authorization,
                model_capture_target=model_capture_target,
            )
        except StageCRuntimeActivationError as use_error:
            try:
                _invalidate_permit_from_seal(
                    seal, invalidation_reason="WORKER_BINDING_RECHECK_FAILED"
                )
            except StageCRuntimeActivationError as invalidation_error:
                raise StageCRuntimeActivationError(
                    "CLAIM_INVALIDATION_FAILED",
                    "invalid terminalization use and durable invalidation is indeterminate",
                ) from invalidation_error
            raise use_error
        return _invalidate_permit_from_seal(
            seal, invalidation_reason=invalidation_reason
        )


def mark_stagec_runtime_attempt_indeterminate(
    permit: StageCRuntimeDispatchPermit,
    **kwargs: Any,
) -> StageCRuntimeAttemptInvalidationObservation:
    """Named alias for the fail-closed durable invalidation operation."""

    return invalidate_stagec_runtime_attempt_claim(permit, **kwargs)


class ActivatedDiagnosticPhaseCoordinator:
    """Compose the structural coordinator with the live activation interlock.

    ``issue_attempt`` is released only while the exact bound phase activation
    remains ``ROWS_ENABLED``.  ``consume_attempt`` first wins the durable live
    row claim, then delegates the existing local lifecycle compare-and-swap,
    and releases a dispatch permit only when that local mutation reports
    ``transitioned_now is True``.  Every post-claim failure is sent to the
    durable backend as terminal ``INDETERMINATE`` before the error escapes.

    Preauthorization rejection remains available with only the process-sealed
    preparation because it performs no authorized dispatch.
    """

    __slots__ = (
        "__coordinator",
        "__preparation",
        "__activation",
        "__issuances",
        "__consume_states",
        "__lock",
    )

    def __init__(
        self,
        *,
        coordinator: Any,
        preparation: StageCRuntimePreparation,
        activation: StageCRuntimePhaseActivation | None = None,
    ) -> None:
        trusted_types = _ACTIVATED_COORDINATOR_TYPES
        if type(trusted_types) is not frozenset or any(type(item) is not type for item in trusted_types):
            _fail("PREPARATION_INVALID", "coordinator type allowlist is malformed")
        if type(coordinator) not in trusted_types:
            _fail("PREPARATION_INVALID", "coordinator exact type is not installed")
        prep_seal = _require_preparation(preparation)
        try:
            registration = coordinator.registration
        except Exception as exc:
            raise StageCRuntimeActivationError(
                "PREPARATION_INVALID", "coordinator exposes no exact registration"
            ) from exc
        if (
            type(registration) is not DiagnosticPhaseRegistrationArtifact
            or registration != prep_seal.phase_registration
            or registration.raw_bytes != prep_seal.phase_registration.raw_bytes
            or registration.artifact_ref != prep_seal.phase_registration.artifact_ref
        ):
            _fail(
                "TARGET_BINDING_MISMATCH",
                "coordinator registration differs from the prepared exact phase",
            )
        if activation is not None:
            activation_seal = _require_activation(activation)
            if activation_seal.preparation_seal is not prep_seal:
                _fail(
                    "TARGET_BINDING_MISMATCH",
                    "activation and coordinator preparation differ",
                )
        self.__coordinator = coordinator
        self.__preparation = preparation
        self.__activation = activation
        self.__issuances: dict[
            str,
            tuple[
                int,
                DiagnosticStudyRequestArtifact,
                DiagnosticChildExecutionBindingArtifact,
                DiagnosticWorkerAuthorizationV2Artifact,
            ],
        ] = {}
        self.__consume_states: dict[str, str] = {}
        self.__lock = threading.RLock()

    @property
    def registration(self) -> DiagnosticPhaseRegistrationArtifact:
        return self.__coordinator.registration

    @property
    def activation(self) -> StageCRuntimePhaseActivation | None:
        return self.__activation

    def __require_active(self) -> StageCRuntimePhaseActivation:
        activation = self.__activation
        if activation is None:
            _fail("PHASE_NOT_ROWS_ENABLED", "coordinator has no phase activation")
        seal = _require_activation(activation)
        prep = _require_preparation(self.__preparation)
        if (
            seal.preparation_seal is not prep
            or seal.control_state != STAGEC_RUNTIME_ROWS_ENABLED
            or self.__coordinator.registration != prep.phase_registration
            or self.__coordinator.registration.artifact_ref
            != prep.phase_registration.artifact_ref
        ):
            _fail(
                "PHASE_NOT_ROWS_ENABLED",
                "coordinator no longer matches an active exact phase",
            )
        return activation

    def issue_attempt(self, *, execution_ordinal: int, **kwargs: Any) -> Any:
        with self.__lock:
            self.__require_active()
            issuance = self.__coordinator.issue_attempt(
                execution_ordinal=execution_ordinal, **kwargs
            )
            prep = _require_preparation(self.__preparation)
            if (
                type(execution_ordinal) is not int
                or isinstance(execution_ordinal, bool)
                or not 1 <= execution_ordinal <= DIAGNOSTIC_CASE_COUNT
            ):
                _fail("ATTEMPT_OUTSIDE_ROSTER", "issued ordinal is outside the roster")
            request = self.__coordinator.registration.study_requests[
                execution_ordinal - 1
            ]
            subject = prep.phase_registration.ordered_subjects[execution_ordinal - 1]
            binding = getattr(issuance, "binding", None)
            authorization = getattr(issuance, "authorization", None)
            snapshot = getattr(issuance, "snapshot", None)
            if (
                type(binding) is not DiagnosticChildExecutionBindingArtifact
                or type(authorization) is not DiagnosticWorkerAuthorizationV2Artifact
                or getattr(snapshot, "attempt_subject_sha256", None) != subject
                or getattr(snapshot, "case_execution_ordinal", None) != execution_ordinal
                or getattr(snapshot, "tenant_id", None) != prep.tenant_id
            ):
                _fail(
                    "ATTEMPT_BINDING_INVALID",
                    "coordinator issuance did not return the exact roster row",
                )
            retained = self.__issuances.get(subject)
            exact = (execution_ordinal, request, binding, authorization)
            if retained is None:
                self.__issuances[subject] = exact
            elif (
                retained[0] != execution_ordinal
                or retained[1] is not request
                or retained[2] is not binding
                or retained[3] is not authorization
            ):
                _fail(
                    "ATTEMPT_BINDING_INVALID",
                    "duplicate issuance returned substituted carrier objects",
                )
            return issuance

    def reject_preauthorization(
        self, *, execution_ordinal: int, **kwargs: Any
    ) -> Any:
        with self.__lock:
            _require_preparation(self.__preparation)
            return self.__coordinator.reject_preauthorization(
                execution_ordinal=execution_ordinal, **kwargs
            )

    def consume_attempt(
        self,
        *,
        execution_ordinal: int,
        study_request: DiagnosticStudyRequestArtifact,
        attempt_subject_sha256: str,
        child_binding: DiagnosticChildExecutionBindingArtifact,
        worker_authorization: DiagnosticWorkerAuthorizationV2Artifact,
        model_capture_target: StageCRuntimeModelCaptureTarget,
        run_nonce_b64url: str,
        worker_started_at: str,
        operation_id: str,
    ) -> ActivatedDiagnosticAttemptConsumption:
        with self.__lock:
            activation = self.__require_active()
            retained = self.__issuances.get(attempt_subject_sha256)
            if (
                retained is None
                or retained[0] != execution_ordinal
                or retained[1] is not study_request
                or retained[2] is not child_binding
                or retained[3] is not worker_authorization
                or run_nonce_b64url != worker_authorization.run_nonce_b64url
            ):
                _fail(
                    "ATTEMPT_BINDING_INVALID",
                    "consume inputs are not the exact wrapper-observed issuance",
                )
            if attempt_subject_sha256 in self.__consume_states:
                _fail(
                    "ATTEMPT_ALREADY_CLAIMED",
                    "wrapper already obtained a durable claim for this attempt",
                )
            permit = _claim_stagec_runtime_attempt(
                activation,
                execution_ordinal=execution_ordinal,
                study_request=study_request,
                attempt_subject_sha256=attempt_subject_sha256,
                child_binding=child_binding,
                worker_authorization=worker_authorization,
                model_capture_target=model_capture_target,
            )
            self.__consume_states[attempt_subject_sha256] = "DURABLY_CLAIMED"
            invalidation_kwargs = {
                "activation": activation,
                "execution_ordinal": execution_ordinal,
                "study_request": study_request,
                "attempt_subject_sha256": attempt_subject_sha256,
                "child_binding": child_binding,
                "worker_authorization": worker_authorization,
                "model_capture_target": model_capture_target,
                "invalidation_reason": "LOCAL_LIFECYCLE_CAS_FAILED",
            }
            try:
                mutation = self.__coordinator.consume_attempt(
                    attempt_subject_sha256=attempt_subject_sha256,
                    run_nonce_b64url=run_nonce_b64url,
                    worker_started_at=worker_started_at,
                    operation_id=operation_id,
                )
                if (
                    getattr(mutation, "transitioned_now", None) is not True
                    or getattr(mutation, "binding", None) != child_binding
                    or getattr(mutation, "authorization", None) != worker_authorization
                    or getattr(getattr(mutation, "snapshot", None), "attempt_subject_sha256", None)
                    != attempt_subject_sha256
                    or getattr(getattr(mutation, "snapshot", None), "case_execution_ordinal", None)
                    != execution_ordinal
                    or getattr(getattr(mutation, "snapshot", None), "tenant_id", None)
                    != self.__preparation.tenant_id
                ):
                    raise StageCRuntimeActivationError(
                        "ATTEMPT_BINDING_INVALID",
                        "local lifecycle CAS did not newly transition the exact row",
                    )
                consumption = ActivatedDiagnosticAttemptConsumption(
                    mutation=mutation,
                    dispatch_permit=permit,
                )
            except BaseException as local_error:
                try:
                    invalidate_stagec_runtime_attempt_claim(
                        permit, **invalidation_kwargs
                    )
                except BaseException as invalidation_error:
                    raise StageCRuntimeActivationError(
                        "CLAIM_INVALIDATION_FAILED",
                        "local CAS failed and durable claim invalidation is indeterminate",
                    ) from invalidation_error
                raise local_error
            return consumption


def require_stagec_runtime_startup_canary(*args: Any, **kwargs: Any) -> None:
    """Explicitly reject warm-load/model-forward canaries under v1 scope."""

    del args, kwargs
    _fail("STARTUP_CANARY_FORBIDDEN", STAGEC_RUNTIME_STARTUP_CANARY)


__all__ = [
    "STAGEC_RUNTIME_ACTIVATION_ERROR_CODES",
    "STAGEC_RUNTIME_ACTIVATION_INDETERMINATE",
    "STAGEC_RUNTIME_CONTROL_BOUNDARY",
    "STAGEC_RUNTIME_GATE_5_STATUS",
    "STAGEC_RUNTIME_INVALIDATION_REASONS",
    "STAGEC_RUNTIME_PERMIT_INDETERMINATE",
    "STAGEC_RUNTIME_PERMIT_INVALIDATED",
    "STAGEC_RUNTIME_PERMIT_REDEEMED",
    "STAGEC_RUNTIME_PERMIT_UNREDEEMED",
    "STAGEC_RUNTIME_PREPARED",
    "STAGEC_RUNTIME_PROJECT_STATUS",
    "STAGEC_RUNTIME_ROWS_ENABLED",
    "STAGEC_RUNTIME_SERIALIZED_AUTHORITY",
    "STAGEC_RUNTIME_STAGE_C_STATUS",
    "STAGEC_RUNTIME_STARTUP_CANARY",
    "StageCRuntimeActivationBackend",
    "StageCRuntimeActivationError",
    "ActivatedDiagnosticAttemptConsumption",
    "ActivatedDiagnosticPhaseCoordinator",
    "StageCRuntimeAmbiguousClaimTerminalObservation",
    "StageCRuntimeAttemptClaimExpectation",
    "StageCRuntimeAttemptClaimObservation",
    "StageCRuntimeAttemptInvalidationExpectation",
    "StageCRuntimeAttemptInvalidationObservation",
    "StageCRuntimeDispatchPermit",
    "StageCRuntimeIssuerAuthorizationObservation",
    "StageCRuntimeModelCaptureTarget",
    "StageCRuntimePhaseActivation",
    "StageCRuntimePhaseActivationExpectation",
    "StageCRuntimePhaseActivationObservation",
    "StageCRuntimePreparation",
    "StageCRuntimeStorageObservation",
    "StageCRuntimeWorkerLeaseObservation",
    "UnavailableStageCRuntimeActivationBackend",
    "activate_stagec_runtime_phase",
    "build_stagec_runtime_model_capture_target",
    "invalidate_stagec_runtime_attempt_claim",
    "mark_stagec_runtime_attempt_indeterminate",
    "prepare_stagec_runtime_activation",
    "redeem_stagec_runtime_dispatch_permit",
    "require_stagec_runtime_startup_canary",
    "stagec_runtime_dispatch_permit_state",
    "stagec_runtime_phase_state",
    "stagec_runtime_preparation_state",
]
