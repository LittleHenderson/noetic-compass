"""Dark orchestration for the prospective CAS Harness v2 worker lifecycle.

This module joins the repository-root strict research kernel, the prospective
run registry, immutable exact-byte wrappers, and the authenticated callback
bridge without promoting any of them into a production or scientific authority.

All kernel callables are injected.  Their provenance is therefore explicitly
unattested.  Application timestamps remain untrusted, callback authentication
does not authenticate model execution, Object-Lock receipts cover repository
wrappers rather than the inner bytes directly, and every result remains
``OPEN / NOT LICENSED / HELD``.
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import json
from typing import Any, Protocol

from api.services.cas_harness_evidence_object_store import (
    EvidenceObjectStoreError,
    EvidencePacketRepository,
    ImmutableEvidenceConflict,
)
from api.services.cas_harness_v2_run_lifecycle import (
    AUTHORIZED,
    EXPIRED,
    FAILURE,
    INDETERMINATE,
    NONREPORTING_RECORDED,
    OUTCOME_ACCESSED,
    PACKET_RECORDED,
    REJECTED,
    RUNNING,
    SUCCESS,
    ArtifactBinding,
)
from api.services.cas_harness_v2_worker_bridge import (
    ResearchOnlyHarnessV2WorkerBridge,
    ResearchWorkerBridgeBindingError,
    ResearchWorkerBridgeConflict,
    ResearchWorkerBridgeError,
    ResearchWorkerBridgePersistenceError,
    ResearchWorkerBridgeResult,
)


EXACT_WRAPPER_SCHEMA = "cas_harness_v2.lifecycle_exact_bytes.v1"
AUTHORIZATION_NAMESPACE = "research-only/harness-v2/lifecycle-authorization"
CONSUMPTION_NAMESPACE = "research-only/harness-v2/lifecycle-consumption"
TERMINAL_NAMESPACE = "research-only/harness-v2/lifecycle-terminal"
TERMINAL_DISPOSITION_NAMESPACE = (
    "research-only/harness-v2/lifecycle-terminal-disposition"
)
OUTPUT_NAMESPACE = "research-only/harness-v2/lifecycle-output"
OUTCOME_ACCESS_NAMESPACE = "research-only/harness-v2/lifecycle-outcome-access"
DEPENDENCY_NAMESPACE = "research-only/harness-v2/lifecycle-dependency"
EVIDENCE_PACKET_NAMESPACE = "research-only/harness-v2/lifecycle-evidence-packet"
NONREPORTING_NAMESPACE = "research-only/harness-v2/lifecycle-nonreporting"

AUTHORIZATION_MEDIA_TYPE = "application/vnd.cas-harness.worker-authorization+json"
TERMINAL_MEDIA_TYPE = "application/vnd.cas-harness.worker-terminal-receipt+json"
TERMINAL_DISPOSITION_MEDIA_TYPE = (
    "application/vnd.cas-harness.terminal-disposition+json"
)
OUTCOME_ACCESS_MEDIA_TYPE = "application/vnd.cas-harness.outcome-access+json"
EVIDENCE_PACKET_MEDIA_TYPE = "application/vnd.cas-harness.evidence-packet+json"
CONSUMPTION_MEDIA_TYPE = (
    "application/vnd.cas-harness.run-consumption-attempt+json"
)
NONREPORTING_MEDIA_TYPE = "application/vnd.cas-harness.nonreporting+json"

SERVER_TERMINAL_DISPOSITIONS = frozenset({INDETERMINATE, REJECTED, EXPIRED})
TERMINAL_DISPOSITION_REASON_CODES = {
    INDETERMINATE: frozenset(
        {"EXECUTION_COMPLETION_UNRESOLVED", "LEASE_LOST_DURING_RUNNING"}
    ),
    REJECTED: frozenset({"ACTION_REJECTED_BEFORE_CONSUMPTION"}),
    EXPIRED: frozenset({"AUTHORIZATION_EXPIRED_BEFORE_CONSUMPTION"}),
}
UNTRUSTED_CLOCK_ASSURANCE = "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED"


class AuthorizationCarrier(Protocol):
    raw_bytes: bytes
    sha256: str
    byte_length: int
    authorization_id: str
    issued_at: str
    expires_at: str
    run_nonce_b64url: str
    payload: Mapping[str, Any]


class TerminalCarrier(Protocol):
    raw_bytes: bytes
    sha256: str
    byte_length: int
    receipt_id: str
    terminal_status: str
    terminal_at: str
    authorization_sha256: str
    payload: Mapping[str, Any]
    outcome_artifact_refs: tuple[Any, ...]
    artifact_ref: Any


class EvidencePacketCarrier(Protocol):
    raw_bytes: bytes
    sha256: str
    byte_length: int
    packet_id: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[Any, ...]


class ActiveLeaseCarrier(Protocol):
    snapshot: Any
    lease_generation_id: str
    lease_token_sha256: str
    lease_expires_at: str
    state_authority: str
    trusted_time: str


class LifecycleClock(Protocol):
    def observe(self, *, operation: str) -> "LifecycleClockObservation": ...


@dataclass(frozen=True, slots=True)
class LifecycleClockObservation:
    """One application-clock reading that explicitly establishes no trusted time."""

    observed_at: datetime
    source: str
    assurance: str = UNTRUSTED_CLOCK_ASSURANCE

    def __post_init__(self) -> None:
        if not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None:
            raise LifecycleServiceBindingError(
                "Lifecycle clock observations must be timezone-aware."
            )
        _required_text(self.source, "clock source")
        if self.assurance != UNTRUSTED_CLOCK_ASSURANCE:
            raise LifecycleServiceBindingError(
                "Lifecycle clock cannot claim trusted time."
            )

    def as_dict(self) -> dict[str, str]:
        return {
            "observed_at": _registry_timestamp(self.observed_at),
            "source": self.source,
            "assurance": self.assurance,
        }


class ProcessUtcLifecycleClock:
    """Default process wall clock; useful for ordering, never a trusted-time receipt."""

    def observe(self, *, operation: str) -> LifecycleClockObservation:
        _required_text(operation, "clock operation")
        return LifecycleClockObservation(
            observed_at=datetime.now(UTC),
            source="PROCESS_UTC_WALL_CLOCK",
        )


class LifecyclePort(Protocol):
    def issue_with_builder(self, **kwargs: Any) -> Any: ...

    def consume_authorization(self, **kwargs: Any) -> Any: ...

    def record_terminal(self, **kwargs: Any) -> Any: ...

    def reserve_outcome_access(self, **kwargs: Any) -> Any: ...

    def finalize_outcome_access(self, **kwargs: Any) -> Any: ...

    def record_packet(self, **kwargs: Any) -> Any: ...

    def record_nonreporting(self, **kwargs: Any) -> Any: ...

    def get_lifecycle(self, **kwargs: Any) -> Any: ...

    def list_events(self, **kwargs: Any) -> tuple[Mapping[str, Any], ...]: ...

    def reconcile(self, **kwargs: Any) -> Any: ...


class LifecycleServiceError(RuntimeError):
    """Base failure for the dark lifecycle orchestrator."""


class LifecycleServiceBindingError(LifecycleServiceError):
    """Exact bytes, scope, state, or transitive artifact bindings disagree."""


class LifecycleServiceNotFound(LifecycleServiceBindingError):
    """A prospective authorization or retained artifact is unavailable."""


class LifecycleServiceConflict(LifecycleServiceBindingError):
    """An immutable lifecycle fact was already bound differently."""


class LifecycleServicePersistenceError(LifecycleServiceError):
    """Immutable storage, exact reload, or receipt verification failed."""


@dataclass(frozen=True, slots=True)
class ExactArtifactReceipt:
    """Wrapper receipt and separately identified inner exact bytes."""

    namespace: str
    trace_id: str
    purpose: str
    artifact_id: str
    media_type: str
    sha256: str
    byte_length: int
    wrapper_content_sha256: str
    wrapper_version_id: str
    raw_bytes: bytes
    wrapper_receipt_scope: str = "REPOSITORY_WRAPPER_NOT_INNER_BYTES"

    @property
    def lifecycle_binding(self) -> ArtifactBinding:
        return ArtifactBinding(
            artifact_id=self.artifact_id,
            media_type=self.media_type,
            sha256=self.sha256.lower(),
            byte_length=self.byte_length,
        )


@dataclass(frozen=True, slots=True)
class LifecycleIssueResult:
    lifecycle: Any
    authorization: AuthorizationCarrier
    authorization_storage: ExactArtifactReceipt
    run_nonce: str | None
    issued_now: bool
    loader_assurance: str = "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED"
    criteria_status: str = "OPEN"
    execution_authentication: str = "NOT_ESTABLISHED"
    trusted_time: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


@dataclass(frozen=True, slots=True)
class LifecycleTerminalResult:
    lifecycle: Any
    terminal: TerminalCarrier
    terminal_storage: ExactArtifactReceipt
    output_storage: tuple[ExactArtifactReceipt, ...]
    bridge_result: ResearchWorkerBridgeResult | None
    idempotent_replay: bool
    loader_assurance: str = "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED"
    criteria_status: str = "OPEN"
    execution_authentication: str = "NOT_ESTABLISHED"
    trusted_time: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


@dataclass(frozen=True, slots=True)
class LifecycleDispositionResult:
    lifecycle: Any
    terminal_status: str
    reason_code: str
    disposition_storage: ExactArtifactReceipt
    observed_at: str
    idempotent_replay: bool
    criteria_status: str = "OPEN"
    execution_authentication: str = "NOT_ESTABLISHED"
    trusted_time: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


@dataclass(frozen=True, slots=True)
class LifecycleOutcomeResult:
    lifecycle: Any
    outcome_access: Any
    outcome_storage: ExactArtifactReceipt
    accessed_at: str
    idempotent_replay: bool
    trusted_time: str = "NOT_ESTABLISHED"
    criteria_status: str = "OPEN"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


@dataclass(frozen=True, slots=True)
class LifecyclePacketResult:
    lifecycle: Any
    packet: EvidencePacketCarrier
    packet_storage: ExactArtifactReceipt
    assessment: Any
    dependency_storage: tuple[ExactArtifactReceipt, ...]
    idempotent_replay: bool
    loader_assurance: str = "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED"
    criteria_status: str = "OPEN"
    execution_authentication: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


@dataclass(frozen=True, slots=True)
class LifecycleReconciliationResult:
    lifecycle: Any
    registry_reconciliation: Any
    authorization_storage: ExactArtifactReceipt
    consumption_storage: ExactArtifactReceipt | None
    terminal_storage: ExactArtifactReceipt | None
    outcome_storage: ExactArtifactReceipt | None
    packet_storage: ExactArtifactReceipt | None
    nonreporting_storage: ExactArtifactReceipt | None
    state: str
    structurally_valid: bool
    criteria_status: str = "OPEN"
    execution_authentication: str = "NOT_ESTABLISHED"
    trusted_time: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


class DarkHarnessV2LifecycleService:
    """Coordinate a single prospective run through exact, conservative stages."""

    def __init__(
        self,
        *,
        repository: EvidencePacketRepository,
        lifecycle: LifecyclePort,
        bridge: ResearchOnlyHarnessV2WorkerBridge,
        build_authorization: Callable[..., AuthorizationCarrier],
        load_authorization: Callable[..., AuthorizationCarrier],
        replay_authorization_for_terminal: Callable[..., AuthorizationCarrier],
        load_terminal_receipt: Callable[..., TerminalCarrier],
        load_evidence_packet: Callable[..., EvidencePacketCarrier],
        verify_evidence_packet: Callable[..., Any],
        artifact_registry_factory: Callable[[Mapping[str, bytes]], Any],
        verify_authenticated_callback: Callable[[Any], Any],
        validate_active_lease: Callable[..., ActiveLeaseCarrier],
        clock: LifecycleClock | None = None,
    ) -> None:
        if repository is None or lifecycle is None or bridge is None:
            raise LifecycleServiceError(
                "Repository, lifecycle registry, and worker bridge are required."
            )
        callables = (
            build_authorization,
            load_authorization,
            replay_authorization_for_terminal,
            load_terminal_receipt,
            load_evidence_packet,
            verify_evidence_packet,
            artifact_registry_factory,
            verify_authenticated_callback,
            validate_active_lease,
        )
        if any(not callable(item) for item in callables):
            raise LifecycleServiceError("Every strict kernel/callback port must be injected.")
        self._repository = repository
        self._lifecycle = lifecycle
        self._bridge = bridge
        self._build_authorization = build_authorization
        self._load_authorization = load_authorization
        self._replay_authorization_for_terminal = replay_authorization_for_terminal
        self._load_terminal_receipt = load_terminal_receipt
        self._load_evidence_packet = load_evidence_packet
        self._verify_evidence_packet = verify_evidence_packet
        self._artifact_registry_factory = artifact_registry_factory
        self._verify_authenticated_callback = verify_authenticated_callback
        self._validate_active_lease = validate_active_lease
        self._clock = clock or ProcessUtcLifecycleClock()
        if not callable(getattr(self._clock, "observe", None)):
            raise LifecycleServiceError("Lifecycle clock must provide observe().")

    def issue_run(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
        authorization_id: str,
        authorized_at: datetime,
        expires_at: datetime,
        execution_mapping: Mapping[str, Any],
    ) -> LifecycleIssueResult:
        """Prospectively create and retain the nonce-bearing authorization."""

        scope = _scope_from_execution(
            tenant_id=tenant_id,
            account_id=account_id,
            execution_mapping=execution_mapping,
        )
        if subject_id != authorization_id or scope["job_id"] != subject_id:
            raise LifecycleServiceBindingError(
                "subject_id, authorization_id, and execution_mapping.job_id must match."
            )
        authorization_request_sha256 = _authorization_request_sha256(
            chain=chain,
            authorization_id=authorization_id,
            authorized_at=authorized_at,
            expires_at=expires_at,
            execution_mapping=execution_mapping,
        )
        captured: list[ExactArtifactReceipt] = []

        def materialize(run_nonce: str) -> ArtifactBinding:
            nonce_bytes = _decode_nonce(run_nonce)
            built = self._build_authorization(
                chain=chain,
                authorization_id=authorization_id,
                issued_at=_kernel_timestamp(authorized_at),
                expires_at=_kernel_timestamp(expires_at),
                execution_mapping=execution_mapping,
                run_nonce=nonce_bytes,
            )
            raw = _carrier_bytes(built, "built authorization")
            loaded = self._load_authorization(raw, chain=chain)
            _verify_carrier(
                loaded,
                raw,
                id_field="authorization_id",
                expected_id=authorization_id,
                label="worker authorization",
            )
            if not hmac.compare_digest(loaded.run_nonce_b64url, run_nonce):
                raise LifecycleServiceBindingError(
                    "Registry nonce does not match the strict authorization carrier."
                )
            _verify_execution_scope(loaded.payload, scope)
            stored = self._store_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="authorization",
                namespace=AUTHORIZATION_NAMESPACE,
                artifact_id=authorization_id,
                media_type=AUTHORIZATION_MEDIA_TYPE,
                raw=raw,
            )
            captured.append(stored)
            return stored.lifecycle_binding

        issuance = self._lifecycle.issue_with_builder(
            tenant_id=tenant_id,
            subject_id=subject_id,
            authorized_at=authorized_at,
            expires_at=expires_at,
            authorization_request_sha256=authorization_request_sha256,
            authorization_builder=materialize,
        )
        stored = (
            captured[0]
            if captured
            else self._load_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="authorization",
                namespace=AUTHORIZATION_NAMESPACE,
                artifact_id=authorization_id,
                expected_binding=_authorization_binding_from_events(
                    self._events(tenant_id, subject_id)
                ),
            )
        )
        authorization = self._load_authorization_for_chain(stored.raw_bytes, chain=chain)
        _verify_carrier(
            authorization,
            stored.raw_bytes,
            id_field="authorization_id",
            expected_id=authorization_id,
            label="reloaded worker authorization",
        )
        _verify_execution_scope(authorization.payload, scope)
        if issuance.run_nonce is not None and not hmac.compare_digest(
            issuance.run_nonce, authorization.run_nonce_b64url
        ):
            raise LifecycleServiceBindingError(
                "Released registry nonce differs from retained authorization bytes."
            )
        return LifecycleIssueResult(
            lifecycle=issuance.lifecycle,
            authorization=authorization,
            authorization_storage=stored,
            run_nonce=issuance.run_nonce,
            issued_now=issuance.issued_now,
        )

    def consume_run(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
        run_nonce: str,
        operation_id: str,
        worker_id: str,
        consumption_id: str,
        job_id: str,
        lease_token: str,
    ) -> Any:
        """Consume with a server-validated active lease; retain no raw lease token."""

        lifecycle = self._require_lifecycle(tenant_id, subject_id)
        authorization, scope, authorization_storage = self._reload_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=subject_id,
            chain=chain,
        )
        if not hmac.compare_digest(run_nonce, authorization.run_nonce_b64url):
            raise LifecycleServiceBindingError(
                "Supplied run nonce differs from the prospective authorization."
            )
        if worker_id != scope["worker_id"]:
            raise LifecycleServiceBindingError(
                "Consuming worker does not match the prospective execution mapping."
            )
        if job_id != scope["job_id"]:
            raise LifecycleServiceBindingError(
                "Consuming job does not match the prospective execution mapping."
            )
        if lifecycle.state not in {AUTHORIZED, RUNNING}:
            raise LifecycleServiceBindingError(
                "Consumption attempts require an AUTHORIZED or replayed RUNNING lifecycle."
            )

        operation = _required_text(operation_id, "operation_id")
        consumption = _required_text(consumption_id, "consumption_id")
        observation = self._observe_clock(operation="consume_run")
        lease_fence = self._active_lease_fence(
            scope=scope,
            job_id=job_id,
            worker_id=worker_id,
            lease_token=lease_token,
            observation=observation,
            authorization=authorization,
        )

        if lifecycle.state == RUNNING:
            running_event = _event(self._events(tenant_id, subject_id), RUNNING)
            if running_event is None or running_event.get("operation_id") != operation:
                raise LifecycleServiceConflict(
                    "RUNNING lifecycle accepts only the exact winning consumption replay."
                )
            details = running_event.get("details")
            if not isinstance(details, Mapping):
                raise LifecycleServicePersistenceError(
                    "RUNNING event details are unavailable."
                )
            recorded_fence = _lease_fence_from_event(running_event)
            if lease_fence != recorded_fence or details.get("worker_id") != worker_id:
                raise LifecycleServiceConflict(
                    "Active lease differs from the winning RUNNING lease fence."
                )
            binding = _binding_from_mapping(details.get("consumption_artifact"))
            if binding.artifact_id != consumption:
                raise LifecycleServiceConflict(
                    "RUNNING lifecycle accepts only the exact winning consumption replay."
                )
            stored = self._load_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="consumption",
                namespace=CONSUMPTION_NAMESPACE,
                artifact_id=binding.artifact_id,
                expected_binding=binding,
            )
            _validate_consumption_envelope(
                stored.raw_bytes,
                subject_id=subject_id,
                run_id=lifecycle.run_id,
                authorization_binding=authorization_storage.lifecycle_binding,
                running_event=running_event,
            )
            recorded_clock = _clock_observation_from_event(running_event)
            return self._lifecycle.consume_authorization(
                tenant_id=tenant_id,
                subject_id=subject_id,
                run_nonce=run_nonce,
                operation_id=operation,
                worker_id=worker_id,
                consumption_artifact=stored.lifecycle_binding,
                started_at=_parse_timestamp(str(running_event.get("occurred_at"))),
                lease_fence=recorded_fence,
                clock_observation=recorded_clock,
            )

        started_iso = observation.as_dict()["observed_at"]
        if _parse_timestamp(authorization.expires_at) <= observation.observed_at.astimezone(UTC):
            raise LifecycleServiceBindingError(
                "Authorization expiry was reached before the consumption attempt."
            )
        raw = _canonical_json_bytes(
            {
                "schema_version": "cas_harness_v2.run_consumption_attempt.v2",
                "consumption_id": consumption,
                "subject_id": subject_id,
                "run_id": lifecycle.run_id,
                "job_id": job_id,
                "worker_id": worker_id,
                "authorization_artifact": authorization_storage.lifecycle_binding.as_dict(),
                "lease_fence": lease_fence,
                "clock_observation": observation.as_dict(),
                "started_at": started_iso,
                "secret_retention": "DIGEST_ONLY_NO_RAW_RUN_LEASE_OR_CALLBACK_NONCES",
                "record_effect": "ATTEMPT_ONLY_NOT_PROOF_OF_EXECUTION",
                "authority": _authority(),
            }
        )
        stored = self._store_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="consumption",
            namespace=CONSUMPTION_NAMESPACE,
            artifact_id=consumption,
            media_type=CONSUMPTION_MEDIA_TYPE,
            raw=raw,
        )
        mutation = self._lifecycle.consume_authorization(
            tenant_id=tenant_id,
            subject_id=subject_id,
            run_nonce=run_nonce,
            operation_id=operation,
            worker_id=worker_id,
            consumption_artifact=stored.lifecycle_binding,
            started_at=observation.observed_at,
            lease_fence=lease_fence,
            clock_observation=observation.as_dict(),
        )
        if lifecycle.run_id != mutation.lifecycle.run_id:
            raise LifecycleServiceBindingError("Run identity changed during consumption.")
        return mutation

    def replay_run_authorization(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
    ) -> LifecycleIssueResult:
        """Reverify an already-issued authorization without mutating its run.

        Authorization issuance is a create/recovery operation and cannot be
        reused as a read once later lifecycle events have advanced the durable
        record.  This explicit replay port reloads the exact retained carrier
        against the current chain and scope while withholding the one-time run
        nonce and raw-release authority.
        """

        lifecycle = self._require_lifecycle(tenant_id, subject_id)
        authorization, _scope, stored = self._reload_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=subject_id,
            chain=chain,
        )
        return LifecycleIssueResult(
            lifecycle=lifecycle,
            authorization=authorization,
            authorization_storage=stored,
            run_nonce=None,
            issued_now=False,
        )

    def accept_terminal(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
        terminal_receipt_raw: bytes | bytearray | memoryview,
        output_bodies: Mapping[str, bytes | bytearray | memoryview],
        callback: Any,
        operation_id: str,
        job_id: str,
        lease_token: str,
        bound_intake_receipt: Any | None = None,
    ) -> LifecycleTerminalResult:
        """Accept a callback only for a consumed, prospectively stored run."""

        lifecycle = self._require_lifecycle(tenant_id, subject_id)
        authorization, scope, _authorization_storage = self._reload_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=subject_id,
            chain=chain,
        )
        if job_id != scope["job_id"]:
            raise LifecycleServiceBindingError(
                "Terminal job does not match the prospective execution mapping."
            )
        terminal_raw = _snapshot(terminal_receipt_raw, "terminal_receipt_raw")
        terminal = self._load_terminal_receipt(
            terminal_raw,
            authorization=authorization,
            chain=chain,
        )
        _verify_carrier(
            terminal,
            terminal_raw,
            id_field="receipt_id",
            expected_id=None,
            label="worker terminal receipt",
        )
        _verify_execution_scope(terminal.payload, scope)
        verified_callback = self._verify_authenticated_callback(callback)
        if verified_callback is not callback:
            raise LifecycleServiceBindingError(
                "Callback verifier did not return the exact authenticated carrier."
            )

        events = self._events(tenant_id, subject_id)
        running_event = _event(events, RUNNING)
        _verify_terminal_started_at(terminal, running_event)
        existing_terminal = _terminal_event(events)
        if existing_terminal is not None:
            existing_details = existing_terminal.get("details")
            if not isinstance(existing_details, Mapping):
                raise LifecycleServicePersistenceError(
                    "Terminal event details are unavailable."
                )
            terminal_status = existing_details.get("terminal_status")
            if terminal_status not in {SUCCESS, FAILURE}:
                raise LifecycleServiceConflict(
                    "A server terminal disposition cannot be replaced by a worker receipt."
                )
            recorded_fence = _lease_fence_from_event(existing_terminal)
            if (
                recorded_fence["job_id"] != job_id
                or not hmac.compare_digest(
                    recorded_fence["lease_token_sha256"],
                    _lease_token_sha256(lease_token),
                )
            ):
                raise LifecycleServiceConflict(
                    "Terminal replay does not match the previously accepted lease fence."
                )
            expected = _binding_from_mapping(
                existing_details["terminal_artifact"]
            )
            stored_terminal = self._load_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="terminal",
                namespace=TERMINAL_NAMESPACE,
                artifact_id=terminal.receipt_id,
                expected_binding=expected,
            )
            if stored_terminal.raw_bytes != terminal_raw:
                raise LifecycleServiceConflict(
                    "Run is already terminal with different exact receipt bytes."
                )
            outputs = self._require_retained_outputs(
                scope=scope,
                subject_id=subject_id,
                terminal=terminal,
                submitted=output_bodies,
            )
            try:
                bridge_result = self._bridge.persist_terminal_callback(
                    authorization_raw=authorization.raw_bytes,
                    terminal_receipt_raw=terminal_raw,
                    chain=chain,
                    callback=callback,
                    bound_intake_receipt=bound_intake_receipt,
                )
            except ResearchWorkerBridgePersistenceError as exc:
                raise LifecycleServicePersistenceError(str(exc)) from exc
            except ResearchWorkerBridgeConflict as exc:
                raise LifecycleServiceConflict(str(exc)) from exc
            except ResearchWorkerBridgeBindingError as exc:
                raise LifecycleServiceBindingError(str(exc)) from exc
            except ResearchWorkerBridgeError as exc:
                raise LifecycleServiceBindingError(str(exc)) from exc
            if (
                bridge_result.authorization_sha256 != authorization.sha256
                or bridge_result.receipt_sha256 != terminal.sha256
            ):
                raise LifecycleServiceBindingError(
                    "Worker bridge replay does not bind the retained terminal pair."
                )
            return LifecycleTerminalResult(
                lifecycle=self._require_lifecycle(tenant_id, subject_id),
                terminal=terminal,
                terminal_storage=stored_terminal,
                output_storage=outputs,
                bridge_result=bridge_result,
                idempotent_replay=True,
            )

        if lifecycle.state != RUNNING:
            raise LifecycleServiceBindingError(
                "Terminal acceptance requires a prospectively consumed RUNNING authorization."
            )
        if getattr(chain, "outcome_access", None) is not None:
            raise LifecycleServiceBindingError(
                "A first terminal callback cannot be accepted after outcome sealing."
            )
        observation = self._observe_clock(operation="accept_terminal")
        active_fence = self._active_lease_fence(
            scope=scope,
            job_id=job_id,
            worker_id=scope["worker_id"],
            lease_token=lease_token,
            observation=observation,
            authorization=authorization,
        )
        if running_event is None or active_fence != _lease_fence_from_event(
            running_event
        ):
            raise LifecycleServiceConflict(
                "Terminal lease differs from the lease fence that consumed the run."
            )
        outputs = self._ensure_terminal_outputs(
            scope=scope,
            subject_id=subject_id,
            terminal=terminal,
            submitted=output_bodies,
        )
        try:
            bridge_result = self._bridge.persist_terminal_callback(
                authorization_raw=authorization.raw_bytes,
                terminal_receipt_raw=terminal_raw,
                chain=chain,
                callback=callback,
                bound_intake_receipt=bound_intake_receipt,
            )
        except ResearchWorkerBridgePersistenceError as exc:
            raise LifecycleServicePersistenceError(str(exc)) from exc
        except ResearchWorkerBridgeConflict as exc:
            raise LifecycleServiceConflict(str(exc)) from exc
        except ResearchWorkerBridgeBindingError as exc:
            raise LifecycleServiceBindingError(str(exc)) from exc
        except ResearchWorkerBridgeError as exc:
            raise LifecycleServiceBindingError(str(exc)) from exc
        if (
            bridge_result.authorization_sha256 != authorization.sha256
            or bridge_result.receipt_sha256 != terminal.sha256
        ):
            raise LifecycleServiceBindingError(
                "Worker bridge result does not bind the strict terminal pair."
            )
        terminal_storage = self._store_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="terminal",
            namespace=TERMINAL_NAMESPACE,
            artifact_id=terminal.receipt_id,
            media_type=TERMINAL_MEDIA_TYPE,
            raw=terminal_raw,
        )
        state = SUCCESS if terminal.terminal_status == "COMPLETED" else FAILURE
        mutation = self._lifecycle.record_terminal(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation_id,
            terminal_status=state,
            terminal_artifact=terminal_storage.lifecycle_binding,
            terminal_at=observation.observed_at,
            lease_fence=active_fence,
            clock_observation=observation.as_dict(),
        )
        return LifecycleTerminalResult(
            lifecycle=mutation.lifecycle,
            terminal=terminal,
            terminal_storage=terminal_storage,
            output_storage=outputs,
            bridge_result=bridge_result,
            idempotent_replay=mutation.idempotent_replay,
        )

    def record_terminal_disposition(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
        operation_id: str,
        job_id: str,
        terminal_status: str,
        reason_code: str,
    ) -> LifecycleDispositionResult:
        """Build a control-plane terminal disposition without inventing an outcome."""

        if terminal_status not in SERVER_TERMINAL_DISPOSITIONS:
            raise LifecycleServiceBindingError(
                "Server dispositions are limited to INDETERMINATE, REJECTED, and EXPIRED."
            )
        allowed_reasons = TERMINAL_DISPOSITION_REASON_CODES[terminal_status]
        reason = _required_text(reason_code, "reason_code")
        if reason not in allowed_reasons:
            raise LifecycleServiceBindingError(
                f"reason_code is not allowed for {terminal_status}."
            )
        operation = _required_text(operation_id, "operation_id")
        lifecycle = self._require_lifecycle(tenant_id, subject_id)
        authorization, scope, authorization_storage = self._reload_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=subject_id,
            chain=chain,
        )
        if job_id != scope["job_id"]:
            raise LifecycleServiceBindingError(
                "Disposition job does not match the prospective execution mapping."
            )
        events = self._events(tenant_id, subject_id)
        existing_terminal = _terminal_event(events)
        disposition_id = _terminal_disposition_artifact_id(subject_id)
        if existing_terminal is not None:
            details = existing_terminal.get("details")
            if (
                not isinstance(details, Mapping)
                or existing_terminal.get("operation_id") != operation
                or details.get("terminal_status") != terminal_status
                or details.get("disposition_reason_code") != reason
            ):
                raise LifecycleServiceConflict(
                    "Run is already terminal with different immutable disposition facts."
                )
            binding = _binding_from_mapping(details.get("terminal_artifact"))
            if binding.artifact_id != disposition_id:
                raise LifecycleServicePersistenceError(
                    "Stored disposition artifact id is not deterministic."
                )
            stored = self._load_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="terminal-disposition",
                namespace=TERMINAL_DISPOSITION_NAMESPACE,
                artifact_id=disposition_id,
                expected_binding=binding,
            )
            _validate_terminal_disposition_envelope(
                stored.raw_bytes,
                subject_id=subject_id,
                run_id=lifecycle.run_id,
                job_id=job_id,
                authorization_binding=authorization_storage.lifecycle_binding,
                terminal_event=existing_terminal,
                running_event=_event(events, RUNNING),
            )
            return LifecycleDispositionResult(
                lifecycle=lifecycle,
                terminal_status=terminal_status,
                reason_code=reason,
                disposition_storage=stored,
                observed_at=str(existing_terminal.get("occurred_at")),
                idempotent_replay=True,
            )

        required_state = RUNNING if terminal_status == INDETERMINATE else AUTHORIZED
        if lifecycle.state != required_state:
            raise LifecycleServiceBindingError(
                f"{terminal_status} requires a {required_state} lifecycle."
            )
        observation = self._observe_clock(operation="record_terminal_disposition")
        if terminal_status == EXPIRED and observation.observed_at.astimezone(UTC) < _parse_timestamp(
            authorization.expires_at
        ):
            raise LifecycleServiceBindingError(
                "EXPIRED cannot be recorded before authorization expiry."
            )
        if terminal_status == REJECTED and observation.observed_at.astimezone(UTC) >= _parse_timestamp(
            authorization.expires_at
        ):
            raise LifecycleServiceBindingError(
                "REJECTED cannot replace EXPIRED after authorization expiry."
            )
        running_event = _event(events, RUNNING)
        lease_fence = (
            _lease_fence_from_event(running_event)
            if terminal_status == INDETERMINATE and running_event is not None
            else None
        )
        consumption_artifact = None
        if running_event is not None:
            details = running_event.get("details")
            if not isinstance(details, Mapping):
                raise LifecycleServicePersistenceError(
                    "RUNNING event details are unavailable for disposition."
                )
            consumption_artifact = _binding_from_mapping(
                details.get("consumption_artifact")
            ).as_dict()
        raw = _canonical_json_bytes(
            {
                "schema_version": "cas_harness_v2.terminal_disposition.v1",
                "disposition_id": disposition_id,
                "subject_id": subject_id,
                "run_id": lifecycle.run_id,
                "job_id": job_id,
                "terminal_status": terminal_status,
                "reason_code": reason,
                "state_before": lifecycle.state,
                "authorization_artifact": authorization_storage.lifecycle_binding.as_dict(),
                "consumption_artifact": consumption_artifact,
                "lease_fence": lease_fence,
                "clock_observation": observation.as_dict(),
                "outcome_access": "NOT_RECORDED",
                "reporting_effect": "NONREPORTING_REQUIRED_NO_OUTCOME_FABRICATED",
                "authority": _authority(),
            }
        )
        stored = self._store_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="terminal-disposition",
            namespace=TERMINAL_DISPOSITION_NAMESPACE,
            artifact_id=disposition_id,
            media_type=TERMINAL_DISPOSITION_MEDIA_TYPE,
            raw=raw,
        )
        mutation = self._lifecycle.record_terminal(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation,
            terminal_status=terminal_status,
            terminal_artifact=stored.lifecycle_binding,
            terminal_at=observation.observed_at,
            lease_fence=lease_fence,
            clock_observation=observation.as_dict(),
            disposition_reason_code=reason,
        )
        return LifecycleDispositionResult(
            lifecycle=mutation.lifecycle,
            terminal_status=terminal_status,
            reason_code=reason,
            disposition_storage=stored,
            observed_at=observation.as_dict()["observed_at"],
            idempotent_replay=mutation.idempotent_replay,
        )

    def retain_output(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
        output_name: str,
        artifact_id: str,
        media_type: str,
        output_raw: bytes | bytearray | memoryview,
        job_id: str,
        lease_token: str,
    ) -> ExactArtifactReceipt:
        """Retain one authorized output callback while the run is RUNNING."""

        lifecycle = self._require_lifecycle(tenant_id, subject_id)
        if lifecycle.state != RUNNING:
            raise LifecycleServiceBindingError(
                "Output retention is available only while the lifecycle is RUNNING."
            )
        authorization, scope, _ = self._reload_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=subject_id,
            chain=chain,
        )
        if job_id != scope["job_id"]:
            raise LifecycleServiceBindingError(
                "Output job does not match the prospective execution mapping."
            )
        observation = self._observe_clock(operation="retain_output")
        active_fence = self._active_lease_fence(
            scope=scope,
            job_id=job_id,
            worker_id=scope["worker_id"],
            lease_token=lease_token,
            observation=observation,
            authorization=authorization,
        )
        running_event = _event(self._events(tenant_id, subject_id), RUNNING)
        if running_event is None or active_fence != _lease_fence_from_event(
            running_event
        ):
            raise LifecycleServiceConflict(
                "Output lease differs from the lease fence that consumed the run."
            )
        name = _required_text(output_name, "output_name")
        expected_outputs = authorization.payload["execution_mapping"][
            "expected_outputs"
        ]
        if name not in expected_outputs:
            raise LifecycleServiceBindingError(
                "Output name is not present in the prospective expected_outputs list."
            )
        return self._store_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="output",
            namespace=OUTPUT_NAMESPACE,
            artifact_id=_required_text(artifact_id, "artifact_id"),
            media_type=_required_text(media_type, "media_type"),
            raw=_snapshot(output_raw, "output_raw"),
            binding_context={"output_name": name},
        )

    def seal_outcome(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
        operation_id: str,
        requested_accessed_at: datetime,
    ) -> LifecycleOutcomeResult:
        """Reserve one stable untrusted time, seal the chain, then finalize it."""

        authorization, scope, _ = self._reload_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=subject_id,
            chain=chain,
        )
        terminal_event = _terminal_event(self._events(tenant_id, subject_id))
        if terminal_event is None:
            raise LifecycleServiceBindingError("Outcome sealing requires a terminal run.")
        terminal_details = terminal_event.get("details")
        if (
            not isinstance(terminal_details, Mapping)
            or terminal_details.get("terminal_status") not in {SUCCESS, FAILURE}
        ):
            raise LifecycleServiceBindingError(
                "Server dispositions have no execution outcome to seal."
            )
        terminal_binding = _binding_from_mapping(
            terminal_details["terminal_artifact"]
        )
        terminal_storage = self._load_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="terminal",
            namespace=TERMINAL_NAMESPACE,
            artifact_id=terminal_binding.artifact_id,
            expected_binding=terminal_binding,
        )
        terminal = self._load_terminal_receipt(
            terminal_storage.raw_bytes,
            authorization=authorization,
            chain=chain,
        )
        reservation = self._lifecycle.reserve_outcome_access(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation_id,
            requested_at=requested_accessed_at,
            terminal_artifact=terminal_binding,
        )
        current = getattr(chain, "outcome_access", None)
        if current is None:
            outcome = chain.record_outcome_access(
                accessed_at=reservation.accessed_at,
                execution_completed_at=terminal.terminal_at,
                receipt=terminal.artifact_ref,
            )
        else:
            outcome = current
            if (
                outcome.accessed_at != reservation.accessed_at
                or outcome.execution_completed_at != terminal.terminal_at
                or outcome.receipt != terminal.artifact_ref
            ):
                raise LifecycleServiceConflict(
                    "Sealed outcome event differs from the durable reservation."
                )
        outcome_id = _outcome_artifact_id(subject_id)
        outcome_storage = self._store_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="outcome-access",
            namespace=OUTCOME_ACCESS_NAMESPACE,
            artifact_id=outcome_id,
            media_type=OUTCOME_ACCESS_MEDIA_TYPE,
            raw=_carrier_bytes(outcome, "outcome access event"),
        )
        mutation = self._lifecycle.finalize_outcome_access(
            tenant_id=tenant_id,
            subject_id=subject_id,
            reservation_id=reservation.reservation_id,
            outcome_access_artifact=outcome_storage.lifecycle_binding,
        )
        return LifecycleOutcomeResult(
            lifecycle=mutation.lifecycle,
            outcome_access=outcome,
            outcome_storage=outcome_storage,
            accessed_at=reservation.accessed_at,
            idempotent_replay=mutation.idempotent_replay,
        )

    def attach_evidence_packet(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
        operation_id: str,
        packet_raw: bytes | bytearray | memoryview,
        artifact_bodies: Mapping[str, bytes | bytearray | memoryview],
        recorded_at: datetime,
    ) -> LifecyclePacketResult:
        """Strict-load, retain every referenced body, verify, and attach Packet v2."""

        lifecycle = self._require_lifecycle(tenant_id, subject_id)
        if lifecycle.state not in {OUTCOME_ACCESSED, PACKET_RECORDED}:
            raise LifecycleServiceBindingError(
                "Evidence Packet attachment requires a sealed outcome."
            )
        authorization, scope, _ = self._reload_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=subject_id,
            chain=chain,
        )
        terminal_event = _terminal_event(self._events(tenant_id, subject_id))
        if terminal_event is None:
            raise LifecycleServiceBindingError("Evidence Packet has no terminal parent.")
        if terminal_event["details"].get("terminal_status") != SUCCESS:
            raise LifecycleServiceBindingError(
                "Failed/indeterminate runs require explicit nonreporting, not a fabricated Packet v2."
            )
        terminal_binding = _binding_from_mapping(
            terminal_event["details"]["terminal_artifact"]
        )
        terminal_storage = self._load_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="terminal",
            namespace=TERMINAL_NAMESPACE,
            artifact_id=terminal_binding.artifact_id,
            expected_binding=terminal_binding,
        )
        terminal = self._load_terminal_receipt(
            terminal_storage.raw_bytes,
            authorization=authorization,
            chain=chain,
        )
        raw = _snapshot(packet_raw, "packet_raw")
        packet = self._load_evidence_packet(raw, chain=chain)
        _verify_carrier(
            packet,
            raw,
            id_field="packet_id",
            expected_id=None,
            label="Evidence Packet v2",
        )
        if packet.payload["execution"]["run_id"] != lifecycle.run_id:
            raise LifecycleServiceBindingError(
                "Evidence Packet run_id does not match the prospective registry run."
            )
        packet_outcomes = tuple(
            _reference_tuple(item) for item in packet.payload["outcome_artifacts"]
        )
        terminal_outcomes = tuple(
            _reference_tuple(item) for item in terminal.outcome_artifact_refs
        )
        if packet_outcomes != terminal_outcomes:
            raise LifecycleServiceBindingError(
                "Evidence Packet outcome refs do not exactly match terminal outputs."
            )

        # Packet attachment is a two-phase operation.  First materialize and
        # verify the complete exact-byte inventory without writing anything;
        # only a fully valid inventory may cross the immutable-storage boundary.
        references = (*chain.artifact_refs, *packet.artifact_refs)
        inventory: dict[str, tuple[Any, ArtifactBinding]] = {}
        for reference in references:
            binding = _binding_from_reference(reference)
            existing = inventory.get(binding.artifact_id)
            if existing is not None:
                if existing[1] != binding:
                    raise LifecycleServiceBindingError(
                        f"Artifact reference {binding.artifact_id!r} is ambiguous."
                    )
                raise LifecycleServiceBindingError(
                    f"Artifact reference {binding.artifact_id!r} is duplicated."
                )
            inventory[binding.artifact_id] = (reference, binding)

        supplied = _snapshot_mapping(artifact_bodies, "artifact_bodies")
        if terminal.receipt_id in supplied:
            raise LifecycleServiceBindingError(
                "artifact_bodies must not replace the server-retained terminal receipt."
            )
        unexpected = set(supplied) - set(inventory)
        if unexpected:
            raise LifecycleServiceBindingError(
                f"Unreferenced artifact bodies were supplied: {sorted(unexpected)!r}."
            )

        terminal_inventory = inventory.get(terminal.receipt_id)
        if terminal_inventory is None:
            raise LifecycleServiceBindingError(
                "Evidence Packet dependency inventory omits the server-retained terminal receipt."
            )
        if terminal_storage.lifecycle_binding != terminal_inventory[1]:
            raise LifecycleServiceBindingError(
                "Server-retained terminal bytes do not match the Packet dependency ref."
            )

        output_names: dict[str, str] = {}
        seen_output_names: set[str] = set()
        for output_name, reference in _terminal_output_rows(terminal):
            if output_name in seen_output_names:
                raise LifecycleServiceBindingError(
                    f"Terminal output name {output_name!r} is duplicated."
                )
            if reference.artifact_id in output_names:
                raise LifecycleServiceBindingError(
                    f"Terminal output artifact {reference.artifact_id!r} is duplicated."
                )
            if reference.artifact_id not in inventory:
                raise LifecycleServiceBindingError(
                    f"Terminal output {reference.artifact_id!r} is absent from the Packet inventory."
                )
            if inventory[reference.artifact_id][1] != _binding_from_reference(reference):
                raise LifecycleServiceBindingError(
                    f"Terminal output {reference.artifact_id!r} is ambiguously referenced."
                )
            seen_output_names.add(output_name)
            output_names[reference.artifact_id] = output_name

        registry_bytes: dict[str, bytes] = {}
        dependency_plan: list[tuple[Any, ArtifactBinding, bytes]] = []
        for artifact_id, (reference, expected_binding) in inventory.items():
            if artifact_id == terminal.receipt_id:
                body = terminal_storage.raw_bytes
            elif artifact_id in output_names:
                output = self._load_exact(
                    scope=scope,
                    subject_id=subject_id,
                    purpose="output",
                    namespace=OUTPUT_NAMESPACE,
                    artifact_id=artifact_id,
                    expected_binding=expected_binding,
                    expected_context={"output_name": output_names[artifact_id]},
                )
                body = output.raw_bytes
                supplied_body = supplied.get(artifact_id)
                if supplied_body is not None and supplied_body != body:
                    raise LifecycleServiceConflict(
                        f"Packet supplied different bytes for retained output {artifact_id!r}."
                    )
            else:
                body = supplied.get(artifact_id)
                if body is None:
                    raise LifecycleServiceNotFound(
                        f"Referenced artifact body {artifact_id!r} is unavailable."
                    )
                observed_binding = ArtifactBinding.from_bytes(
                    artifact_id=artifact_id,
                    media_type=reference.media_type,
                    body=body,
                )
                if observed_binding != expected_binding:
                    raise LifecycleServiceBindingError(
                        f"Artifact body {artifact_id!r} does not match its exact ref."
                    )
                dependency_plan.append((reference, expected_binding, body))
            registry_bytes[artifact_id] = body

        artifact_registry = self._artifact_registry_factory(registry_bytes)
        assessment = self._verify_evidence_packet(
            packet,
            chain=chain,
            artifact_registry=artifact_registry,
        )
        if getattr(assessment, "structural_completeness", None) != "COMPLETE":
            raise LifecycleServiceBindingError(
                "Evidence Packet verifier did not establish structural completeness."
            )

        retained: list[ExactArtifactReceipt] = []
        for reference, expected_binding, body in dependency_plan:
            stored = self._store_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="dependency",
                namespace=DEPENDENCY_NAMESPACE,
                artifact_id=reference.artifact_id,
                media_type=reference.media_type,
                raw=body,
            )
            if stored.lifecycle_binding != expected_binding:
                raise LifecycleServiceBindingError(
                    f"Retained dependency {reference.artifact_id!r} does not match its ref."
                )
            retained.append(stored)
        packet_storage = self._store_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="evidence-packet",
            namespace=EVIDENCE_PACKET_NAMESPACE,
            artifact_id=packet.packet_id,
            media_type=EVIDENCE_PACKET_MEDIA_TYPE,
            raw=raw,
        )
        mutation = self._lifecycle.record_packet(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation_id,
            packet_artifact=packet_storage.lifecycle_binding,
            recorded_at=recorded_at,
        )
        return LifecyclePacketResult(
            lifecycle=mutation.lifecycle,
            packet=packet,
            packet_storage=packet_storage,
            assessment=assessment,
            dependency_storage=tuple(retained),
            idempotent_replay=mutation.idempotent_replay,
        )

    def record_nonreporting(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
        operation_id: str,
        reason_code: str,
        recorded_at: datetime,
    ) -> Any:
        """Attach an explicit negative/nonreporting envelope instead of Packet v2."""

        lifecycle = self._require_lifecycle(tenant_id, subject_id)
        if lifecycle.state not in {
            OUTCOME_ACCESSED,
            INDETERMINATE,
            REJECTED,
            EXPIRED,
            NONREPORTING_RECORDED,
        }:
            raise LifecycleServiceBindingError(
                "Nonreporting requires a sealed outcome or a no-outcome server disposition."
            )
        _authorization, scope, _ = self._reload_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=subject_id,
            chain=chain,
        )
        events = self._events(tenant_id, subject_id)
        terminal_event = _terminal_event(events)
        if terminal_event is None:
            raise LifecycleServiceBindingError(
                "Nonreporting envelope requires a terminal parent."
            )
        terminal_binding = _binding_from_mapping(
            terminal_event["details"]["terminal_artifact"]
        )
        terminal_status = terminal_event["details"]["terminal_status"]
        outcome_event = _event(events, OUTCOME_ACCESSED)
        direct_no_outcome = terminal_status in SERVER_TERMINAL_DISPOSITIONS
        if direct_no_outcome and outcome_event is not None:
            raise LifecycleServicePersistenceError(
                "Server disposition unexpectedly has an outcome-access event."
            )
        if not direct_no_outcome and outcome_event is None:
            raise LifecycleServiceBindingError(
                "Strict worker terminal nonreporting requires a sealed outcome."
            )
        reason = _required_text(reason_code, "reason_code")
        nonreporting_id = _nonreporting_artifact_id(subject_id)
        raw = _canonical_json_bytes(
            {
                "schema_version": "cas_harness_v2.nonreporting.v2",
                "nonreporting_id": nonreporting_id,
                "subject_id": subject_id,
                "run_id": lifecycle.run_id,
                "terminal_status": terminal_status,
                "terminal_artifact": terminal_binding.as_dict(),
                "reason_code": reason,
                "recorded_at": _registry_timestamp(recorded_at),
                "outcome_access": (
                    "NOT_RECORDED" if direct_no_outcome else "RECORDED"
                ),
                "preregistration_chain_closure": (
                    "NOT_ESTABLISHED_NO_OUTCOME_EVENT"
                    if direct_no_outcome
                    else "SEALED_OUTCOME_EVENT_RECORDED_NOT_SCIENTIFIC_AUTHORITY"
                ),
                "reporting_effect": "NO_EVIDENCE_PACKET_V2_FABRICATED",
                "authority": _authority(),
            }
        )
        stored = self._store_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="nonreporting",
            namespace=NONREPORTING_NAMESPACE,
            artifact_id=nonreporting_id,
            media_type=NONREPORTING_MEDIA_TYPE,
            raw=raw,
        )
        return self._lifecycle.record_nonreporting(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation_id,
            nonreporting_artifact=stored.lifecycle_binding,
            reason_code=reason,
            recorded_at=recorded_at,
        )

    def reconcile_run(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
    ) -> LifecycleReconciliationResult:
        """Replay the registry and every retained strict carrier for one run."""

        lifecycle = self._require_lifecycle(tenant_id, subject_id)
        registry_reconciliation = self._lifecycle.reconcile(tenant_id=tenant_id)
        authorization, scope, authorization_storage = self._reload_authorization(
            tenant_id=tenant_id,
            account_id=account_id,
            subject_id=subject_id,
            chain=chain,
        )
        events = self._events(tenant_id, subject_id)
        terminal_storage: ExactArtifactReceipt | None = None
        outcome_storage: ExactArtifactReceipt | None = None
        packet_storage: ExactArtifactReceipt | None = None
        consumption_storage: ExactArtifactReceipt | None = None
        nonreporting_storage: ExactArtifactReceipt | None = None
        running_event = _event(events, RUNNING)
        if running_event is not None:
            binding = _binding_from_mapping(
                running_event["details"]["consumption_artifact"]
            )
            consumption_storage = self._load_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="consumption",
                namespace=CONSUMPTION_NAMESPACE,
                artifact_id=binding.artifact_id,
                expected_binding=binding,
            )
            _validate_consumption_envelope(
                consumption_storage.raw_bytes,
                subject_id=subject_id,
                run_id=lifecycle.run_id,
                authorization_binding=authorization_storage.lifecycle_binding,
                running_event=running_event,
            )
        terminal_event = _terminal_event(events)
        terminal: TerminalCarrier | None = None
        if terminal_event is not None:
            terminal_details = terminal_event.get("details")
            if not isinstance(terminal_details, Mapping):
                raise LifecycleServicePersistenceError(
                    "Terminal event details are unavailable."
                )
            binding = _binding_from_mapping(
                terminal_details["terminal_artifact"]
            )
            if terminal_details.get("terminal_status") in SERVER_TERMINAL_DISPOSITIONS:
                terminal_storage = self._load_exact(
                    scope=scope,
                    subject_id=subject_id,
                    purpose="terminal-disposition",
                    namespace=TERMINAL_DISPOSITION_NAMESPACE,
                    artifact_id=binding.artifact_id,
                    expected_binding=binding,
                )
                _validate_terminal_disposition_envelope(
                    terminal_storage.raw_bytes,
                    subject_id=subject_id,
                    run_id=lifecycle.run_id,
                    job_id=scope["job_id"],
                    authorization_binding=authorization_storage.lifecycle_binding,
                    terminal_event=terminal_event,
                    running_event=running_event,
                )
            else:
                terminal_storage = self._load_exact(
                    scope=scope,
                    subject_id=subject_id,
                    purpose="terminal",
                    namespace=TERMINAL_NAMESPACE,
                    artifact_id=binding.artifact_id,
                    expected_binding=binding,
                )
                terminal = self._load_terminal_receipt(
                    terminal_storage.raw_bytes,
                    authorization=authorization,
                    chain=chain,
                )
                _verify_terminal_started_at(terminal, running_event)
                self._require_retained_outputs(
                    scope=scope,
                    subject_id=subject_id,
                    terminal=terminal,
                    submitted={},
                )
        outcome_event = _event(events, OUTCOME_ACCESSED)
        if outcome_event is not None:
            binding = _binding_from_mapping(
                outcome_event["details"]["outcome_access_artifact"]
            )
            outcome_storage = self._load_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="outcome-access",
                namespace=OUTCOME_ACCESS_NAMESPACE,
                artifact_id=binding.artifact_id,
                expected_binding=binding,
            )
            current = getattr(chain, "outcome_access", None)
            if current is None or _carrier_bytes(current, "outcome access event") != outcome_storage.raw_bytes:
                raise LifecycleServiceBindingError(
                    "Retained outcome-access bytes do not match the sealed chain."
                )
        packet_event = _event(events, PACKET_RECORDED)
        if packet_event is not None:
            if terminal is None:
                raise LifecycleServiceBindingError("Packet registry event has no terminal parent.")
            binding = _binding_from_mapping(packet_event["details"]["packet_artifact"])
            packet_storage = self._load_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="evidence-packet",
                namespace=EVIDENCE_PACKET_NAMESPACE,
                artifact_id=binding.artifact_id,
                expected_binding=binding,
            )
            packet = self._load_evidence_packet(packet_storage.raw_bytes, chain=chain)
            bodies: dict[str, bytes] = {}
            output_names = {
                reference.artifact_id: output_name
                for output_name, reference in _terminal_output_rows(terminal)
            }
            output_ids = set(output_names)
            for reference in (*chain.artifact_refs, *packet.artifact_refs):
                if reference.artifact_id == terminal.receipt_id:
                    if terminal_storage is None:
                        raise LifecycleServicePersistenceError(
                            "Packet reconciliation lost its terminal storage parent."
                        )
                    body = terminal_storage.raw_bytes
                else:
                    purpose = "output" if reference.artifact_id in output_ids else "dependency"
                    namespace = OUTPUT_NAMESPACE if purpose == "output" else DEPENDENCY_NAMESPACE
                    body = self._load_exact(
                        scope=scope,
                        subject_id=subject_id,
                        purpose=purpose,
                        namespace=namespace,
                        artifact_id=reference.artifact_id,
                        expected_binding=_binding_from_reference(reference),
                        expected_context=(
                            {"output_name": output_names[reference.artifact_id]}
                            if purpose == "output"
                            else None
                        ),
                    ).raw_bytes
                bodies[reference.artifact_id] = body
            assessment = self._verify_evidence_packet(
                packet,
                chain=chain,
                artifact_registry=self._artifact_registry_factory(bodies),
            )
            if getattr(assessment, "structural_completeness", None) != "COMPLETE":
                raise LifecycleServiceBindingError(
                    "Replayed packet is not structurally complete."
                )
        nonreporting_event = _event(events, NONREPORTING_RECORDED)
        if nonreporting_event is not None:
            if terminal_event is None:
                raise LifecycleServiceBindingError(
                    "Nonreporting registry event has no terminal parent."
                )
            binding = _binding_from_mapping(
                nonreporting_event["details"]["nonreporting_artifact"]
            )
            nonreporting_storage = self._load_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="nonreporting",
                namespace=NONREPORTING_NAMESPACE,
                artifact_id=binding.artifact_id,
                expected_binding=binding,
            )
            _validate_nonreporting_envelope(
                nonreporting_storage.raw_bytes,
                subject_id=subject_id,
                run_id=lifecycle.run_id,
                terminal_event=terminal_event,
                nonreporting_event=nonreporting_event,
                outcome_event=outcome_event,
            )
        return LifecycleReconciliationResult(
            lifecycle=lifecycle,
            registry_reconciliation=registry_reconciliation,
            authorization_storage=authorization_storage,
            consumption_storage=consumption_storage,
            terminal_storage=terminal_storage,
            outcome_storage=outcome_storage,
            packet_storage=packet_storage,
            nonreporting_storage=nonreporting_storage,
            state=lifecycle.state,
            structurally_valid=bool(
                getattr(registry_reconciliation, "structurally_valid", False)
            ),
        )

    def _reload_authorization(
        self,
        *,
        tenant_id: str,
        account_id: str,
        subject_id: str,
        chain: object,
    ) -> tuple[AuthorizationCarrier, dict[str, str], ExactArtifactReceipt]:
        events = self._events(tenant_id, subject_id)
        binding = _authorization_binding_from_events(events)
        provisional_scope = {
            "tenant_id": tenant_id,
            "account_id": account_id,
            "audit_id": "PENDING_STRICT_RELOAD",
            "fleet_id": "PENDING_STRICT_RELOAD",
            "job_id": "PENDING_STRICT_RELOAD",
            "worker_id": "PENDING_STRICT_RELOAD",
        }
        # Scope is stored inside the immutable wrapper, so first load it without
        # guessing worker-controlled execution values, then validate the strict
        # carrier against that server-side scope.
        stored = self._load_exact(
            scope=provisional_scope,
            subject_id=subject_id,
            purpose="authorization",
            namespace=AUTHORIZATION_NAMESPACE,
            artifact_id=binding.artifact_id,
            expected_binding=binding,
            allow_scope_discovery=True,
        )
        authorization = self._load_authorization_for_chain(stored.raw_bytes, chain=chain)
        scope = _scope_from_execution(
            tenant_id=tenant_id,
            account_id=account_id,
            execution_mapping=authorization.payload["execution_mapping"],
        )
        if (
            subject_id != scope["job_id"]
            or authorization.authorization_id != subject_id
        ):
            raise LifecycleServiceBindingError(
                "Reloaded subject_id, authorization_id, and job_id differ."
            )
        self._load_exact(
            scope=scope,
            subject_id=subject_id,
            purpose="authorization",
            namespace=AUTHORIZATION_NAMESPACE,
            artifact_id=binding.artifact_id,
            expected_binding=binding,
        )
        _verify_execution_scope(authorization.payload, scope)
        return authorization, scope, stored

    def _load_authorization_for_chain(
        self, raw: bytes, *, chain: object
    ) -> AuthorizationCarrier:
        """Use the public pre-outcome loader or the explicit sealed replay port."""

        if getattr(chain, "outcome_access", None) is None:
            return self._load_authorization(raw, chain=chain)
        return self._replay_authorization_for_terminal(raw, chain=chain)

    def _ensure_terminal_outputs(
        self,
        *,
        scope: Mapping[str, str],
        subject_id: str,
        terminal: TerminalCarrier,
        submitted: Mapping[str, bytes | bytearray | memoryview],
    ) -> tuple[ExactArtifactReceipt, ...]:
        bodies = _snapshot_mapping(submitted, "output_bodies")
        rows = _terminal_output_rows(terminal)
        expected_ids = {reference.artifact_id for _name, reference in rows}
        unexpected = set(bodies) - expected_ids
        if unexpected:
            raise LifecycleServiceBindingError(
                f"Unexpected output bodies were supplied: {sorted(unexpected)!r}."
            )
        stored: list[ExactArtifactReceipt] = []
        for output_name, reference in rows:
            try:
                item = self._load_exact(
                    scope=scope,
                    subject_id=subject_id,
                    purpose="output",
                    namespace=OUTPUT_NAMESPACE,
                    artifact_id=reference.artifact_id,
                    expected_binding=_binding_from_reference(reference),
                    expected_context={"output_name": output_name},
                )
            except LifecycleServiceNotFound:
                body = bodies.get(reference.artifact_id)
                if body is None:
                    raise LifecycleServiceNotFound(
                        f"Produced output {output_name!r} has no retained exact body."
                    )
                item = self._store_exact(
                    scope=scope,
                    subject_id=subject_id,
                    purpose="output",
                    namespace=OUTPUT_NAMESPACE,
                    artifact_id=reference.artifact_id,
                    media_type=reference.media_type,
                    raw=body,
                    binding_context={"output_name": output_name},
                )
            if item.lifecycle_binding != _binding_from_reference(reference):
                raise LifecycleServiceBindingError(
                    f"Output body {reference.artifact_id!r} does not verify its terminal ref."
                )
            supplied_body = bodies.get(reference.artifact_id)
            if supplied_body is not None and supplied_body != item.raw_bytes:
                raise LifecycleServiceConflict(
                    f"Submitted output {reference.artifact_id!r} differs from retained bytes."
                )
            stored.append(item)
        return tuple(stored)

    def _require_retained_outputs(
        self,
        *,
        scope: Mapping[str, str],
        subject_id: str,
        terminal: TerminalCarrier,
        submitted: Mapping[str, bytes | bytearray | memoryview],
    ) -> tuple[ExactArtifactReceipt, ...]:
        supplied = _snapshot_mapping(submitted, "output_bodies")
        rows = _terminal_output_rows(terminal)
        unexpected = set(supplied) - {
            reference.artifact_id for _name, reference in rows
        }
        if unexpected:
            raise LifecycleServiceBindingError(
                f"Unexpected output bodies were supplied: {sorted(unexpected)!r}."
            )
        stored: list[ExactArtifactReceipt] = []
        for output_name, reference in rows:
            item = self._load_exact(
                scope=scope,
                subject_id=subject_id,
                purpose="output",
                namespace=OUTPUT_NAMESPACE,
                artifact_id=reference.artifact_id,
                expected_binding=_binding_from_reference(reference),
                expected_context={"output_name": output_name},
            )
            if reference.artifact_id in supplied and supplied[reference.artifact_id] != item.raw_bytes:
                raise LifecycleServiceConflict(
                    f"Submitted output {reference.artifact_id!r} differs from retained bytes."
                )
            stored.append(item)
        return tuple(stored)

    def _store_exact(
        self,
        *,
        scope: Mapping[str, str],
        subject_id: str,
        purpose: str,
        namespace: str,
        artifact_id: str,
        media_type: str,
        raw: bytes,
        binding_context: Mapping[str, Any] | None = None,
    ) -> ExactArtifactReceipt:
        body = _snapshot(raw, f"{purpose} raw")
        context = dict(binding_context or {})
        trace_id = _trace_id(subject_id, purpose, artifact_id, context)
        inner_sha = hashlib.sha256(body).hexdigest().upper()
        wrapper = {
            "schema_version": EXACT_WRAPPER_SCHEMA,
            "trace_id": trace_id,
            "storage_profile": "EXACT_BYTES_BASE64_WRAPPER_NOT_INNER_ARTIFACT_RECEIPT",
            "purpose": purpose,
            "subject_id": subject_id,
            "scope": dict(scope),
            "binding_context": context,
            "inner_artifact": {
                "artifact_id": artifact_id,
                "media_type": media_type,
                "sha256": inner_sha,
                "byte_length": len(body),
                "raw_base64": base64.b64encode(body).decode("ascii"),
            },
            "authority": _authority(),
        }
        try:
            receipt = self._repository.put_packet(
                tenant_id=scope["tenant_id"],
                namespace=namespace,
                trace_id=trace_id,
                packet=wrapper,
                account_id=scope["account_id"],
            )
        except ImmutableEvidenceConflict as exc:
            raise LifecycleServiceConflict(
                f"{purpose} wrapper is already bound to different exact bytes."
            ) from exc
        except (EvidenceObjectStoreError, OSError, ValueError) as exc:
            raise LifecycleServicePersistenceError(
                f"{purpose} immutable wrapper write failed."
            ) from exc
        if not receipt.is_verifiable():
            raise LifecycleServicePersistenceError(
                f"{purpose} wrapper lacks a re-read-verifiable receipt."
            )
        loaded = self._load_exact(
            scope=scope,
            subject_id=subject_id,
            purpose=purpose,
            namespace=namespace,
                artifact_id=artifact_id,
                expected_binding=ArtifactBinding.from_bytes(
                artifact_id=artifact_id,
                media_type=media_type,
                    body=body,
                ),
                expected_context=binding_context,
        )
        if loaded.wrapper_version_id != receipt.version_id or loaded.raw_bytes != body:
            raise LifecycleServicePersistenceError(
                f"{purpose} exact wrapper receipt/reload diverged."
            )
        return loaded

    def _load_exact(
        self,
        *,
        scope: Mapping[str, str],
        subject_id: str,
        purpose: str,
        namespace: str,
        artifact_id: str,
        expected_binding: ArtifactBinding,
        expected_context: Mapping[str, Any] | None = None,
        allow_scope_discovery: bool = False,
    ) -> ExactArtifactReceipt:
        context = dict(expected_context or {})
        trace_id = _trace_id(subject_id, purpose, artifact_id, context)
        try:
            wrapper, wrapper_sha = self._repository.load_packet_with_content_sha256(
                tenant_id=scope["tenant_id"],
                namespace=namespace,
                trace_id=trace_id,
            )
            verification = self._repository.verify_packet(
                tenant_id=scope["tenant_id"], namespace=namespace, trace_id=trace_id
            )
        except FileNotFoundError as exc:
            raise LifecycleServiceNotFound(
                f"Retained {purpose} wrapper is unavailable."
            ) from exc
        except (EvidenceObjectStoreError, OSError, ValueError) as exc:
            raise LifecycleServicePersistenceError(
                f"Retained {purpose} wrapper could not be reloaded."
            ) from exc
        if verification.get("match") is not True:
            raise LifecycleServicePersistenceError(
                f"Retained {purpose} wrapper receipt did not reverify."
            )
        receipt = verification.get("object_lock_verification")
        if not isinstance(receipt, Mapping):
            raise LifecycleServicePersistenceError(
                f"Retained {purpose} wrapper has no structured receipt."
            )
        observed = receipt.get("observed")
        if not isinstance(observed, Mapping) or not isinstance(
            observed.get("get_version_id"), str
        ):
            raise LifecycleServicePersistenceError(
                f"Retained {purpose} wrapper version is unavailable."
            )
        if (
            wrapper.get("schema_version") != EXACT_WRAPPER_SCHEMA
            or wrapper.get("trace_id") != trace_id
            or wrapper.get("storage_profile")
            != "EXACT_BYTES_BASE64_WRAPPER_NOT_INNER_ARTIFACT_RECEIPT"
            or wrapper.get("purpose") != purpose
            or wrapper.get("subject_id") != subject_id
            or wrapper.get("authority") != _authority()
            or set(wrapper)
            != {
                "schema_version",
                "trace_id",
                "storage_profile",
                "purpose",
                "subject_id",
                "scope",
                "binding_context",
                "inner_artifact",
                "authority",
            }
        ):
            raise LifecycleServicePersistenceError(
                f"Retained {purpose} wrapper metadata changed."
            )
        stored_scope = wrapper.get("scope")
        if not isinstance(stored_scope, Mapping):
            raise LifecycleServicePersistenceError(
                f"Retained {purpose} wrapper scope is unavailable."
            )
        if set(stored_scope) != {
            "tenant_id",
            "account_id",
            "audit_id",
            "fleet_id",
            "job_id",
            "worker_id",
        }:
            raise LifecycleServicePersistenceError(
                f"Retained {purpose} wrapper scope shape changed."
            )
        stored_context = wrapper.get("binding_context")
        if not isinstance(stored_context, Mapping) or dict(stored_context) != dict(
            expected_context or {}
        ):
            raise LifecycleServiceBindingError(
                f"Retained {purpose} wrapper binding context differs."
            )
        if allow_scope_discovery:
            if (
                stored_scope.get("tenant_id") != scope["tenant_id"]
                or stored_scope.get("account_id") != scope["account_id"]
            ):
                raise LifecycleServiceBindingError(
                    f"Retained {purpose} wrapper tenant/account scope differs."
                )
        elif dict(stored_scope) != dict(scope):
            raise LifecycleServiceBindingError(
                f"Retained {purpose} wrapper scope differs from the current run."
            )
        node = wrapper.get("inner_artifact")
        if not isinstance(node, Mapping):
            raise LifecycleServicePersistenceError(
                f"Retained {purpose} inner artifact is unavailable."
            )
        if set(node) != {
            "artifact_id",
            "media_type",
            "sha256",
            "byte_length",
            "raw_base64",
        }:
            raise LifecycleServicePersistenceError(
                f"Retained {purpose} inner artifact shape changed."
            )
        raw = _decode_exact(node, purpose)
        sha = hashlib.sha256(raw).hexdigest().upper()
        if (
            node.get("artifact_id") != artifact_id
            or node.get("media_type") != expected_binding.media_type
            or sha.lower() != expected_binding.sha256
            or len(raw) != expected_binding.byte_length
        ):
            raise LifecycleServiceBindingError(
                f"Retained {purpose} inner artifact differs from its lifecycle binding."
            )
        return ExactArtifactReceipt(
            namespace=namespace,
            trace_id=trace_id,
            purpose=purpose,
            artifact_id=artifact_id,
            media_type=expected_binding.media_type,
            sha256=sha,
            byte_length=len(raw),
            wrapper_content_sha256=wrapper_sha,
            wrapper_version_id=str(observed["get_version_id"]),
            raw_bytes=raw,
        )

    def _events(self, tenant_id: str, subject_id: str) -> tuple[Mapping[str, Any], ...]:
        return self._lifecycle.list_events(tenant_id=tenant_id, subject_id=subject_id)

    def _observe_clock(self, *, operation: str) -> LifecycleClockObservation:
        try:
            observation = self._clock.observe(operation=operation)
        except LifecycleServiceError:
            raise
        except (TypeError, ValueError, RuntimeError) as exc:
            raise LifecycleServiceBindingError(
                "Untrusted lifecycle clock observation failed."
            ) from exc
        if not isinstance(observation, LifecycleClockObservation):
            raise LifecycleServiceBindingError(
                "Lifecycle clock returned an invalid observation carrier."
            )
        # Materialize the exact representation now so malformed injected clocks
        # fail before any repository or lifecycle write.
        observation.as_dict()
        return observation

    def _active_lease_fence(
        self,
        *,
        scope: Mapping[str, str],
        job_id: str,
        worker_id: str,
        lease_token: str,
        observation: LifecycleClockObservation,
        authorization: AuthorizationCarrier,
    ) -> dict[str, str]:
        secret = _required_text(lease_token, "lease_token")
        try:
            active = self._validate_active_lease(
                audit_id=scope["audit_id"],
                job_id=job_id,
                worker_id=worker_id,
                lease_token=secret,
                now=observation.observed_at,
            )
        except LifecycleServiceError:
            raise
        except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
            raise LifecycleServiceBindingError(
                "Active fleet lease validation failed."
            ) from exc
        try:
            snapshot_mapping = active.snapshot.execution_mapping()
            generation = _required_text(
                active.lease_generation_id, "active lease generation"
            )
            token_digest = _required_lower_sha256(
                active.lease_token_sha256, "active lease token digest"
            )
            expires_at = _registry_timestamp(
                _parse_timestamp(active.lease_expires_at)
            )
            state_authority = _required_text(
                active.state_authority, "active lease state authority"
            )
            trusted_time = _required_text(
                active.trusted_time, "active lease trusted-time status"
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise LifecycleServiceBindingError(
                "Active fleet lease result is malformed."
            ) from exc
        expected_mapping = authorization.payload.get("execution_mapping")
        if (
            not isinstance(snapshot_mapping, Mapping)
            or not isinstance(expected_mapping, Mapping)
            or _plain_json(snapshot_mapping) != _plain_json(expected_mapping)
        ):
            raise LifecycleServiceBindingError(
                "Active fleet lease snapshot differs from the prospective authorization."
            )
        if (
            trusted_time != "NOT_ESTABLISHED"
            or state_authority != "PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE"
        ):
            raise LifecycleServiceBindingError(
                "Active fleet lease result exceeds the bounded process-local authority."
            )
        if not hmac.compare_digest(token_digest, _lease_token_sha256(secret)):
            raise LifecycleServiceBindingError(
                "Active fleet lease digest does not bind the supplied secret."
            )
        if _parse_timestamp(expires_at) <= observation.observed_at.astimezone(UTC):
            raise LifecycleServiceBindingError("Active fleet lease has expired.")
        return {
            "job_id": job_id,
            "lease_generation_id": generation,
            "lease_token_sha256": token_digest,
            "lease_expires_at": expires_at,
            "state_authority": state_authority,
            "trusted_time": trusted_time,
        }

    def _require_lifecycle(self, tenant_id: str, subject_id: str) -> Any:
        lifecycle = self._lifecycle.get_lifecycle(
            tenant_id=tenant_id, subject_id=subject_id
        )
        if lifecycle is None:
            raise LifecycleServiceNotFound(
                "No prospective authorization exists for this tenant/subject."
            )
        return lifecycle


def _authorization_binding_from_events(
    events: tuple[Mapping[str, Any], ...]
) -> ArtifactBinding:
    event = _event(events, "AUTHORIZED")
    if event is None:
        raise LifecycleServiceNotFound("Prospective authorization event is unavailable.")
    return _binding_from_mapping(event["details"]["authorization_artifact"])


def _terminal_event(
    events: tuple[Mapping[str, Any], ...]
) -> Mapping[str, Any] | None:
    return _event(events, "TERMINAL_RECORDED")


def _event(
    events: tuple[Mapping[str, Any], ...], event_type: str
) -> Mapping[str, Any] | None:
    matches = [item for item in events if item.get("event_type") == event_type]
    if len(matches) > 1:
        raise LifecycleServicePersistenceError(
            f"Lifecycle contains multiple {event_type} events."
        )
    return matches[0] if matches else None


def _lease_fence_from_event(event: Mapping[str, Any]) -> dict[str, str]:
    details = event.get("details")
    value = details.get("lease_fence") if isinstance(details, Mapping) else None
    if not isinstance(value, Mapping) or set(value) != {
        "job_id",
        "lease_generation_id",
        "lease_token_sha256",
        "lease_expires_at",
        "state_authority",
        "trusted_time",
    }:
        raise LifecycleServicePersistenceError(
            "Lifecycle event has no exact redacted lease fence."
        )
    try:
        result = {
            "job_id": _required_text(value.get("job_id"), "lease fence job_id"),
            "lease_generation_id": _required_text(
                value.get("lease_generation_id"), "lease fence generation"
            ),
            "lease_token_sha256": _required_lower_sha256(
                value.get("lease_token_sha256"), "lease fence token digest"
            ),
            "lease_expires_at": _registry_timestamp(
                _parse_timestamp(value.get("lease_expires_at"))
            ),
            "state_authority": _required_text(
                value.get("state_authority"), "lease fence state authority"
            ),
            "trusted_time": _required_text(
                value.get("trusted_time"), "lease fence trusted-time status"
            ),
        }
    except LifecycleServiceBindingError as exc:
        raise LifecycleServicePersistenceError(
            "Lifecycle event lease fence is malformed."
        ) from exc
    if (
        result["trusted_time"] != "NOT_ESTABLISHED"
        or result["state_authority"] != "PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE"
        or dict(value) != result
    ):
        raise LifecycleServicePersistenceError(
            "Lifecycle event lease fence changed or claims trusted time."
        )
    return result


def _clock_observation_from_event(event: Mapping[str, Any]) -> dict[str, str]:
    details = event.get("details")
    value = details.get("clock_observation") if isinstance(details, Mapping) else None
    if not isinstance(value, Mapping) or set(value) != {
        "observed_at",
        "source",
        "assurance",
    }:
        raise LifecycleServicePersistenceError(
            "Lifecycle event has no exact untrusted clock observation."
        )
    try:
        result = {
            "observed_at": _registry_timestamp(
                _parse_timestamp(value.get("observed_at"))
            ),
            "source": _required_text(value.get("source"), "clock source"),
            "assurance": _required_text(
                value.get("assurance"), "clock assurance"
            ),
        }
    except LifecycleServiceBindingError as exc:
        raise LifecycleServicePersistenceError(
            "Lifecycle event clock observation is malformed."
        ) from exc
    if result["assurance"] != UNTRUSTED_CLOCK_ASSURANCE or dict(value) != result:
        raise LifecycleServicePersistenceError(
            "Lifecycle event clock observation changed or claims trusted time."
        )
    if result["observed_at"] != event.get("occurred_at"):
        raise LifecycleServicePersistenceError(
            "Lifecycle event clock observation differs from occurred_at."
        )
    return result


def _verify_terminal_started_at(
    terminal: TerminalCarrier,
    running_event: Mapping[str, Any] | None,
) -> None:
    if running_event is None:
        raise LifecycleServiceBindingError(
            "Strict worker terminal has no prospective RUNNING parent."
        )
    freshness = terminal.payload.get("freshness")
    worker_started_at = (
        freshness.get("worker_started_at") if isinstance(freshness, Mapping) else None
    )
    occurred_at = running_event.get("occurred_at")
    if not isinstance(worker_started_at, str) or not isinstance(occurred_at, str):
        raise LifecycleServiceBindingError(
            "Strict terminal worker start time is unavailable."
        )
    if _parse_timestamp(worker_started_at) != _parse_timestamp(occurred_at):
        raise LifecycleServiceBindingError(
            "Strict terminal worker_started_at differs from the RUNNING event time."
        )


def _lease_token_sha256(value: object) -> str:
    secret = _required_text(value, "lease_token")
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _binding_from_mapping(value: object) -> ArtifactBinding:
    if not isinstance(value, Mapping):
        raise LifecycleServicePersistenceError("Stored artifact binding is unavailable.")
    try:
        return ArtifactBinding(
            artifact_id=value["artifact_id"],
            media_type=value["media_type"],
            sha256=value["sha256"],
            byte_length=value["byte_length"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LifecycleServicePersistenceError(
            "Stored artifact binding is malformed."
        ) from exc


def _binding_from_reference(reference: Any) -> ArtifactBinding:
    return ArtifactBinding(
        artifact_id=reference.artifact_id,
        media_type=reference.media_type,
        sha256=reference.sha256.lower(),
        byte_length=reference.byte_length,
    )


def _terminal_output_rows(
    terminal: TerminalCarrier,
) -> tuple[tuple[str, Any], ...]:
    value = terminal.payload.get("terminal")
    if not isinstance(value, Mapping):
        raise LifecycleServiceBindingError("Terminal output block is unavailable.")
    rows = value.get("produced_outputs")
    if not isinstance(rows, (tuple, list)):
        raise LifecycleServiceBindingError("Terminal produced_outputs are unavailable.")
    references = terminal.outcome_artifact_refs
    if len(rows) != len(references):
        raise LifecycleServiceBindingError(
            "Terminal output rows differ from the strict carrier refs."
        )
    result: list[tuple[str, Any]] = []
    for index, (row, reference) in enumerate(zip(rows, references, strict=True)):
        if not isinstance(row, Mapping):
            raise LifecycleServiceBindingError(
                f"Terminal output row {index} is malformed."
            )
        output_name = _required_text(row.get("output_name"), "terminal output_name")
        artifact = row.get("artifact")
        if not isinstance(artifact, Mapping) or _reference_tuple(artifact) != _reference_tuple(
            reference
        ):
            raise LifecycleServiceBindingError(
                f"Terminal output row {index} does not bind its strict ref."
            )
        result.append((output_name, reference))
    return tuple(result)


def _reference_tuple(reference: Any) -> tuple[object, ...]:
    if isinstance(reference, Mapping):
        return (
            reference.get("artifact_id"),
            str(reference.get("sha256", "")).upper(),
            reference.get("byte_length"),
            reference.get("media_type"),
        )
    return (
        reference.artifact_id,
        str(reference.sha256).upper(),
        reference.byte_length,
        reference.media_type,
    )


def _reference_inventory(reference: Any) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "media_type": reference.media_type,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
    }


def _authorization_request_sha256(
    *,
    chain: object,
    authorization_id: str,
    authorized_at: datetime,
    expires_at: datetime,
    execution_mapping: Mapping[str, Any],
) -> str:
    if getattr(chain, "outcome_access", None) is not None:
        raise LifecycleServiceBindingError(
            "Prospective authorization cannot be issued after outcome access."
        )
    try:
        base = chain.base
        amendments = chain.amendments
        chain_sha256 = chain.chain_sha256
    except AttributeError as exc:
        raise LifecycleServiceBindingError(
            "Prospective issuance requires an exact preregistration chain."
        ) from exc
    inventory = {
        "base": {
            "artifact_id": base.preregistration_id,
            "media_type": "application/vnd.cas-harness.preregistration+json",
            "sha256": base.sha256,
            "byte_length": base.byte_length,
        },
        "base_bound_artifacts": [
            _reference_inventory(reference) for reference in base.artifact_refs
        ],
        "amendments": [
            {
                "artifact_id": amendment.amendment_id,
                "media_type": (
                    "application/vnd.cas-harness.preregistration-amendment+json"
                ),
                "sha256": amendment.sha256,
                "byte_length": amendment.byte_length,
                "bound_artifacts": [
                    _reference_inventory(reference)
                    for reference in amendment.artifact_refs
                ],
            }
            for amendment in amendments
        ],
        "pre_outcome_chain_sha256": chain_sha256,
    }
    body = {
        "schema_version": "cas_harness_v2.authorization_request_fingerprint.v1",
        "authorization_id": authorization_id,
        "issued_at": _kernel_timestamp(authorized_at),
        "expires_at": _kernel_timestamp(expires_at),
        "execution_mapping": _plain_json(execution_mapping),
        "preregistration_binding_inventory": inventory,
    }
    return hashlib.sha256(_canonical_json_bytes(body)).hexdigest()


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_plain_json(item) for item in value]
    return value


def _scope_from_execution(
    *,
    tenant_id: str,
    account_id: str,
    execution_mapping: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(execution_mapping, Mapping):
        raise LifecycleServiceBindingError("execution_mapping must be a mapping.")
    return {
        "tenant_id": _required_text(tenant_id, "tenant_id"),
        "account_id": _required_text(account_id, "account_id"),
        "audit_id": _required_text(execution_mapping.get("audit_id"), "audit_id"),
        "fleet_id": _required_text(execution_mapping.get("fleet_id"), "fleet_id"),
        "job_id": _required_text(execution_mapping.get("job_id"), "job_id"),
        "worker_id": _required_text(
            execution_mapping.get("assigned_worker_id"), "assigned_worker_id"
        ),
    }


def _verify_execution_scope(payload: Mapping[str, Any], scope: Mapping[str, str]) -> None:
    execution = payload.get("execution_mapping")
    if not isinstance(execution, Mapping):
        raise LifecycleServiceBindingError("Strict carrier execution_mapping is unavailable.")
    expected = {
        "audit_id": scope["audit_id"],
        "fleet_id": scope["fleet_id"],
        "job_id": scope["job_id"],
        "assigned_worker_id": scope["worker_id"],
    }
    for field, value in expected.items():
        actual = execution.get(field)
        if not isinstance(actual, str) or not hmac.compare_digest(actual, value):
            raise LifecycleServiceBindingError(
                f"Strict carrier {field} differs from server scope."
            )


def _verify_carrier(
    carrier: object,
    raw: bytes,
    *,
    id_field: str,
    expected_id: str | None,
    label: str,
) -> None:
    try:
        actual = bytes(getattr(carrier, "raw_bytes"))
        digest = getattr(carrier, "sha256")
        length = getattr(carrier, "byte_length")
        artifact_id = getattr(carrier, id_field)
        payload = getattr(carrier, "payload")
    except (AttributeError, TypeError) as exc:
        raise LifecycleServiceBindingError(
            f"Injected loader returned an invalid {label} carrier."
        ) from exc
    if (
        actual != raw
        or digest != hashlib.sha256(raw).hexdigest().upper()
        or length != len(raw)
        or not isinstance(artifact_id, str)
        or not artifact_id
        or not isinstance(payload, Mapping)
        or (expected_id is not None and artifact_id != expected_id)
    ):
        raise LifecycleServiceBindingError(
            f"Injected loader did not retain the exact {label} bytes."
        )


def _decode_exact(node: Mapping[str, Any], label: str) -> bytes:
    encoded = node.get("raw_base64")
    if not isinstance(encoded, str):
        raise LifecycleServicePersistenceError(f"{label} raw_base64 is unavailable.")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise LifecycleServicePersistenceError(f"{label} raw_base64 is invalid.") from exc
    digest = hashlib.sha256(raw).hexdigest().upper()
    if (
        node.get("sha256") != digest
        or node.get("byte_length") != len(raw)
        or not isinstance(node.get("media_type"), str)
    ):
        raise LifecycleServicePersistenceError(
            f"{label} exact-byte identity does not verify."
        )
    return raw


def _snapshot(value: bytes | bytearray | memoryview, label: str) -> bytes:
    if type(value) not in (bytes, bytearray, memoryview):
        raise LifecycleServiceBindingError(f"{label} must be bytes-like.")
    raw = bytes(value)
    if not raw:
        raise LifecycleServiceBindingError(f"{label} must not be empty.")
    return raw


def _snapshot_mapping(
    values: Mapping[str, bytes | bytearray | memoryview], label: str
) -> dict[str, bytes]:
    if not isinstance(values, Mapping):
        raise LifecycleServiceBindingError(f"{label} must be a mapping.")
    result: dict[str, bytes] = {}
    for key, value in values.items():
        result[_required_text(key, f"{label} key")] = _snapshot(
            value, f"{label}[{key!r}]"
        )
    return result


def _carrier_bytes(value: object, label: str) -> bytes:
    try:
        raw = getattr(value, "raw_bytes")
    except AttributeError as exc:
        raise LifecycleServiceBindingError(f"{label} has no exact bytes.") from exc
    return _snapshot(raw, f"{label}.raw_bytes")


def _trace_id(
    subject_id: str,
    purpose: str,
    artifact_id: str,
    binding_context: Mapping[str, Any],
) -> str:
    identity = (
        binding_context.get("output_name")
        if purpose == "output"
        else artifact_id
    )
    if not isinstance(identity, str) or not identity:
        raise LifecycleServiceBindingError(
            f"{purpose} wrapper has no deterministic trace identity."
        )
    digest = hashlib.sha256(
        f"{subject_id}\0{purpose}\0{identity}".encode("utf-8")
    ).hexdigest()
    return "h2exact_" + digest


def _outcome_artifact_id(subject_id: str) -> str:
    return "h2outcome_" + hashlib.sha256(subject_id.encode("utf-8")).hexdigest()


def _nonreporting_artifact_id(subject_id: str) -> str:
    return "h2nonreport_" + hashlib.sha256(subject_id.encode("utf-8")).hexdigest()


def _terminal_disposition_artifact_id(subject_id: str) -> str:
    return "h2disposition_" + hashlib.sha256(subject_id.encode("utf-8")).hexdigest()


def _decode_nonce(value: str) -> bytes:
    if not isinstance(value, str) or len(value) != 43:
        raise LifecycleServiceBindingError("Registry nonce is not canonical base64url.")
    try:
        raw = base64.urlsafe_b64decode(value + "=")
    except (TypeError, ValueError) as exc:
        raise LifecycleServiceBindingError("Registry nonce is not valid base64url.") from exc
    if (
        len(raw) != 32
        or base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != value
    ):
        raise LifecycleServiceBindingError("Registry nonce is not exactly 32 bytes.")
    return raw


def _kernel_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise LifecycleServiceBindingError("Lifecycle timestamps must be timezone-aware.")
    utc = value.astimezone(UTC)
    if utc.microsecond:
        return utc.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return utc.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise LifecycleServiceBindingError("Strict timestamp is invalid.") from exc
    if parsed.tzinfo is None:
        raise LifecycleServiceBindingError("Strict timestamp is not timezone-aware.")
    return parsed.astimezone(UTC)


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise LifecycleServiceBindingError(f"{label} must be a non-empty exact string.")
    if len(value) > 1024 or any(ord(char) < 32 for char in value):
        raise LifecycleServiceBindingError(f"{label} contains invalid text.")
    return value


def _required_lower_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise LifecycleServiceBindingError(
            f"{label} must be a lowercase 64-character SHA-256 digest."
        )
    return value


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise LifecycleServiceBindingError(
            "Nonreporting envelope facts are not canonical JSON values."
        ) from exc


def _registry_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise LifecycleServiceBindingError("Lifecycle timestamps must be timezone-aware.")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _strict_canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    duplicates: list[str] = []

    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("ascii"), object_pairs_hook=strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleServicePersistenceError(
            f"Retained {label} is not strict canonical JSON."
        ) from exc
    if (
        duplicates
        or not isinstance(value, dict)
        or _canonical_json_bytes(value) != raw
    ):
        raise LifecycleServicePersistenceError(
            f"Retained {label} is not one strict canonical object."
        )
    return value


def _validate_terminal_disposition_envelope(
    raw: bytes,
    *,
    subject_id: str,
    run_id: str,
    job_id: str,
    authorization_binding: ArtifactBinding,
    terminal_event: Mapping[str, Any],
    running_event: Mapping[str, Any] | None,
) -> None:
    value = _strict_canonical_object(raw, "terminal disposition")
    details = terminal_event.get("details")
    if not isinstance(details, Mapping):
        raise LifecycleServicePersistenceError(
            "Terminal disposition event details are unavailable."
        )
    terminal_status = details.get("terminal_status")
    if terminal_status not in SERVER_TERMINAL_DISPOSITIONS:
        raise LifecycleServicePersistenceError(
            "Terminal disposition event has a worker terminal state."
        )
    consumption_artifact = None
    lease_fence = None
    if running_event is not None:
        running_details = running_event.get("details")
        if not isinstance(running_details, Mapping):
            raise LifecycleServicePersistenceError(
                "RUNNING event details are unavailable for disposition replay."
            )
        consumption_artifact = _binding_from_mapping(
            running_details.get("consumption_artifact")
        ).as_dict()
        lease_fence = _lease_fence_from_event(running_event)
    expected = {
        "schema_version": "cas_harness_v2.terminal_disposition.v1",
        "disposition_id": _terminal_disposition_artifact_id(subject_id),
        "subject_id": subject_id,
        "run_id": run_id,
        "job_id": job_id,
        "terminal_status": terminal_status,
        "reason_code": details.get("disposition_reason_code"),
        "state_before": terminal_event.get("state_before"),
        "authorization_artifact": authorization_binding.as_dict(),
        "consumption_artifact": consumption_artifact,
        "lease_fence": lease_fence if terminal_status == INDETERMINATE else None,
        "clock_observation": _clock_observation_from_event(terminal_event),
        "outcome_access": "NOT_RECORDED",
        "reporting_effect": "NONREPORTING_REQUIRED_NO_OUTCOME_FABRICATED",
        "authority": _authority(),
    }
    if value != expected:
        raise LifecycleServicePersistenceError(
            "Retained terminal disposition differs from its lifecycle facts."
        )


def _validate_nonreporting_envelope(
    raw: bytes,
    *,
    subject_id: str,
    run_id: str,
    terminal_event: Mapping[str, Any],
    nonreporting_event: Mapping[str, Any],
    outcome_event: Mapping[str, Any] | None,
) -> None:
    duplicates: list[str] = []

    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("ascii"), object_pairs_hook=strict_object
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleServicePersistenceError(
            "Retained nonreporting envelope is not strict canonical JSON."
        ) from exc
    if duplicates or not isinstance(value, dict):
        raise LifecycleServicePersistenceError(
            "Retained nonreporting envelope contains duplicate fields or is not an object."
        )
    terminal_binding = _binding_from_mapping(
        terminal_event["details"]["terminal_artifact"]
    )
    terminal_status = terminal_event["details"].get("terminal_status")
    direct_no_outcome = terminal_status in SERVER_TERMINAL_DISPOSITIONS
    if direct_no_outcome == (outcome_event is not None):
        raise LifecycleServicePersistenceError(
            "Nonreporting outcome-access ancestry conflicts with terminal status."
        )
    reason = nonreporting_event["details"].get("reason_code")
    occurred_at = nonreporting_event.get("occurred_at")
    expected = {
        "schema_version": "cas_harness_v2.nonreporting.v2",
        "nonreporting_id": _nonreporting_artifact_id(subject_id),
        "subject_id": subject_id,
        "run_id": run_id,
        "terminal_status": terminal_status,
        "terminal_artifact": terminal_binding.as_dict(),
        "reason_code": reason,
        "recorded_at": occurred_at,
        "outcome_access": "NOT_RECORDED" if direct_no_outcome else "RECORDED",
        "preregistration_chain_closure": (
            "NOT_ESTABLISHED_NO_OUTCOME_EVENT"
            if direct_no_outcome
            else "SEALED_OUTCOME_EVENT_RECORDED_NOT_SCIENTIFIC_AUTHORITY"
        ),
        "reporting_effect": "NO_EVIDENCE_PACKET_V2_FABRICATED",
        "authority": _authority(),
    }
    if value != expected or _canonical_json_bytes(value) != raw:
        raise LifecycleServicePersistenceError(
            "Retained nonreporting envelope differs from its lifecycle facts."
        )


def _validate_consumption_envelope(
    raw: bytes,
    *,
    subject_id: str,
    run_id: str,
    authorization_binding: ArtifactBinding,
    running_event: Mapping[str, Any],
) -> None:
    duplicates: list[str] = []

    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("ascii"), object_pairs_hook=strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleServicePersistenceError(
            "Retained consumption envelope is not strict canonical JSON."
        ) from exc
    exact_keys = {
        "schema_version",
        "consumption_id",
        "subject_id",
        "run_id",
        "job_id",
        "worker_id",
        "authorization_artifact",
        "lease_fence",
        "clock_observation",
        "started_at",
        "secret_retention",
        "record_effect",
        "authority",
    }
    if (
        duplicates
        or not isinstance(value, dict)
        or set(value) != exact_keys
        or _canonical_json_bytes(value) != raw
    ):
        raise LifecycleServicePersistenceError(
            "Retained consumption envelope is not one strict canonical object."
        )
    details = running_event.get("details")
    if not isinstance(details, Mapping):
        raise LifecycleServicePersistenceError(
            "RUNNING event details are unavailable for consumption replay."
        )
    event_binding = _binding_from_mapping(details.get("consumption_artifact"))
    expected_static = {
        "schema_version": "cas_harness_v2.run_consumption_attempt.v2",
        "consumption_id": event_binding.artifact_id,
        "subject_id": subject_id,
        "run_id": run_id,
        "job_id": _lease_fence_from_event(running_event)["job_id"],
        "worker_id": details.get("worker_id"),
        "authorization_artifact": authorization_binding.as_dict(),
        "lease_fence": _lease_fence_from_event(running_event),
        "clock_observation": _clock_observation_from_event(running_event),
        "started_at": running_event.get("occurred_at"),
        "secret_retention": "DIGEST_ONLY_NO_RAW_RUN_LEASE_OR_CALLBACK_NONCES",
        "record_effect": "ATTEMPT_ONLY_NOT_PROOF_OF_EXECUTION",
        "authority": _authority(),
    }
    if any(value.get(key) != expected for key, expected in expected_static.items()):
        raise LifecycleServicePersistenceError(
            "Retained consumption envelope differs from lifecycle facts."
        )
    try:
        fence = _lease_fence_from_event(running_event)
        expires = _parse_timestamp(fence["lease_expires_at"])
        started = _parse_timestamp(value.get("started_at"))
    except LifecycleServiceBindingError as exc:
        raise LifecycleServicePersistenceError(
            "Retained consumption lease facts are malformed."
        ) from exc
    if expires <= started:
        raise LifecycleServicePersistenceError(
            "Retained consumption lease facts are not active and exact."
        )


def _authority() -> dict[str, str]:
    return {
        "adapter": "RESEARCH_ONLY_DARK",
        "loader_assurance": "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED",
        "wrapper_receipt_scope": "REPOSITORY_WRAPPER_NOT_INNER_BYTES",
        "execution_authentication": "NOT_ESTABLISHED",
        "trusted_time": "NOT_ESTABLISHED",
        "independent_authority": "NOT_ESTABLISHED",
        "scientific_status": "NOT_ESTABLISHED",
        "criteria_status": "OPEN",
        "product_status": "NOT_ESTABLISHED",
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
    }


__all__ = [
    "AUTHORIZATION_NAMESPACE",
    "CONSUMPTION_NAMESPACE",
    "DEPENDENCY_NAMESPACE",
    "EVIDENCE_PACKET_NAMESPACE",
    "EXACT_WRAPPER_SCHEMA",
    "NONREPORTING_NAMESPACE",
    "OUTCOME_ACCESS_NAMESPACE",
    "OUTPUT_NAMESPACE",
    "TERMINAL_NAMESPACE",
    "TERMINAL_DISPOSITION_NAMESPACE",
    "TERMINAL_DISPOSITION_REASON_CODES",
    "DarkHarnessV2LifecycleService",
    "ExactArtifactReceipt",
    "LifecycleClockObservation",
    "ProcessUtcLifecycleClock",
    "LifecycleDispositionResult",
    "LifecycleIssueResult",
    "LifecycleOutcomeResult",
    "LifecyclePacketResult",
    "LifecycleReconciliationResult",
    "LifecycleServiceBindingError",
    "LifecycleServiceConflict",
    "LifecycleServiceError",
    "LifecycleServiceNotFound",
    "LifecycleServicePersistenceError",
    "LifecycleTerminalResult",
]
