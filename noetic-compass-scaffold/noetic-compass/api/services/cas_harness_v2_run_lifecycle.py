"""Dark, research-only prospective run lifecycle for CAS Harness v2.

This module provides a tenant-scoped, prospective registry for one-use run
authorizations.  It deliberately stops short of a production authority:

* lifecycle events are create-only StateStore records joined by SHA-256 hashes;
* a mutable, version-checked index points at the current hash-chain head;
* run nonces are generated with a server-side CSPRNG and only their digest is
  persisted;
* optimistic concurrency makes ``AUTHORIZED -> RUNNING`` a one-winner change
  only within the atomic-CAS scope actually supplied by the backing StateStore;
* reconciliation enumerates lifecycle, reservation, and event records so partial
  writes and non-reporting remain visible.

The StateStore interface is not WORM storage, a trusted clock, execution
authentication, or an independent evidence authority.  SQLite can honestly
provide same-host restart durability, but not replication or host-loss survival.
Those limitations are preserved in every record and result.  Nothing here grants
scientific validity, a product licence, publication, or disclosure authority.
The integration gate therefore remains OPEN.
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import json
import secrets
from typing import Any

from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    StateStoreError,
    VersionConflict,
)


LIFECYCLE_SCHEMA = "cas_harness_v2.prospective_run_lifecycle.v1"
EVENT_SCHEMA = "cas_harness_v2.prospective_run_event.v1"
SUBJECT_RESERVATION_SCHEMA = "cas_harness_v2.run_subject_reservation.v1"
NONCE_RESERVATION_SCHEMA = "cas_harness_v2.run_nonce_reservation.v1"
AUTHORIZATION_FINALIZATION_SCHEMA = "cas_harness_v2.authorization_finalization.v1"
OUTCOME_ACCESS_RESERVATION_SCHEMA = "cas_harness_v2.outcome_access_reservation.v1"

LIFECYCLE_KIND = "cas_harness_v2_prospective_run_lifecycle"
EVENT_KIND = "cas_harness_v2_prospective_run_event"
SUBJECT_RESERVATION_KIND = "cas_harness_v2_run_subject_reservation"
NONCE_RESERVATION_KIND = "cas_harness_v2_run_nonce_reservation"
AUTHORIZATION_FINALIZATION_KIND = "cas_harness_v2_authorization_finalization"
OUTCOME_ACCESS_RESERVATION_KIND = "cas_harness_v2_outcome_access_reservation"

AUTHORIZED = "AUTHORIZED"
RUNNING = "RUNNING"
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"
INDETERMINATE = "INDETERMINATE"
REJECTED = "REJECTED"
EXPIRED = "EXPIRED"
OUTCOME_ACCESSED = "OUTCOME_ACCESSED"
PACKET_RECORDED = "PACKET_RECORDED"
NONREPORTING_RECORDED = "NONREPORTING_RECORDED"

TERMINAL_STATES = frozenset(
    {SUCCESS, FAILURE, INDETERMINATE, REJECTED, EXPIRED}
)
REPORTING_DISPOSITIONS = frozenset({PACKET_RECORDED, NONREPORTING_RECORDED})

_GENESIS_PREVIOUS_SHA256 = "0" * 64
_MAX_TEXT_LENGTH = 1024


class RunLifecycleError(RuntimeError):
    """Base error for the research-only prospective lifecycle."""


class RunLifecycleValidationError(RunLifecycleError):
    """A caller supplied a malformed identifier, timestamp, nonce, or binding."""


class RunLifecycleConflict(RunLifecycleError):
    """Stored immutable facts or the current monotone state conflict with a call."""


class RunLifecycleNotFound(RunLifecycleError):
    """No lifecycle is visible in the caller's tenant scope."""


class RunLifecycleExpired(RunLifecycleConflict):
    """An authorization was not consumed before its declared expiry."""


class RunLifecyclePersistenceError(RunLifecycleError):
    """StateStore persistence failed or returned an internally inconsistent row."""


class RunLifecycleBuilderError(RunLifecycleError):
    """The injected strict authorization builder failed after nonce reservation."""


class RunLifecycleQuarantined(RunLifecycleConflict):
    """A reserved nonce cannot be recovered to finish an interrupted build."""


@dataclass(frozen=True, slots=True)
class ArtifactBinding:
    """Exact identity and digest of bytes stored by a separate artifact system."""

    artifact_id: str
    media_type: str
    sha256: str
    byte_length: int

    def __post_init__(self) -> None:
        _required_text(self.artifact_id, "ArtifactBinding.artifact_id")
        _required_text(self.media_type, "ArtifactBinding.media_type")
        _required_lower_sha256(self.sha256, "ArtifactBinding.sha256")
        if type(self.byte_length) is not int or self.byte_length < 0:
            raise RunLifecycleValidationError(
                "ArtifactBinding.byte_length must be an exact non-negative integer."
            )

    @classmethod
    def from_bytes(
        cls,
        *,
        artifact_id: str,
        media_type: str,
        body: bytes,
    ) -> "ArtifactBinding":
        if type(body) is not bytes:
            raise RunLifecycleValidationError("ArtifactBinding body must be exact bytes.")
        return cls(
            artifact_id=artifact_id,
            media_type=media_type,
            sha256=hashlib.sha256(body).hexdigest(),
            byte_length=len(body),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "media_type": self.media_type,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
        }


@dataclass(frozen=True, slots=True)
class RunLifecycleSnapshot:
    """Current registry projection; it is not an execution or evidence verdict."""

    tenant_id: str
    run_id: str
    subject_id: str
    authorization_request_sha256: str
    state: str
    event_count: int
    head_event_sha256: str
    run_nonce_sha256: str
    authorized_at: str
    expires_at: str
    record_version: int
    backend_durability_profile: Mapping[str, str]
    authority: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class RunNonceIssuance:
    """Issuance result. ``run_nonce`` is present only for the winning first call."""

    lifecycle: RunLifecycleSnapshot
    run_nonce: str | None
    issued_now: bool
    criteria_status: str = "OPEN"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


@dataclass(frozen=True, slots=True)
class RunLifecycleMutation:
    lifecycle: RunLifecycleSnapshot
    event_sha256: str
    idempotent_replay: bool
    criteria_status: str = "OPEN"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


@dataclass(frozen=True, slots=True)
class OutcomeAccessReservation:
    tenant_id: str
    run_id: str
    subject_id: str
    reservation_id: str
    operation_id: str
    accessed_at: str
    terminal_state: str
    terminal_event_sha256: str
    terminal_artifact: Mapping[str, object]
    backend_durability_profile: Mapping[str, str]
    authority: Mapping[str, str]
    criteria_status: str = "OPEN"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


@dataclass(frozen=True, slots=True)
class ReconciliationIssue:
    code: str
    record_id: str
    detail: str


@dataclass(frozen=True, slots=True)
class RunLifecycleReconciliation:
    tenant_id: str
    has_registered_runs: bool
    lifecycle_count: int
    subject_reservation_count: int
    nonce_reservation_count: int
    authorization_finalization_count: int
    outcome_access_reservation_count: int
    event_count: int
    state_counts: Mapping[str, int]
    issue_count: int
    issues: tuple[ReconciliationIssue, ...]
    structurally_valid: bool
    all_runs_reporting_disposed: bool
    registry_sha256: str
    backend_durability_profile: Mapping[str, str]
    criteria_status: str = "OPEN"
    execution_authentication: str = "NOT_ESTABLISHED"
    trusted_time: str = "NOT_ESTABLISHED"
    worm_authority: str = "NOT_ESTABLISHED"
    independent_authority: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


class DurableProspectiveRunLifecycle:
    """StateStore-backed monotone lifecycle with create-only hash-chain events.

    ``nonce_factory`` is injectable solely for deterministic tests.  Production
    callers should retain the default ``secrets.token_bytes`` implementation.
    """

    def __init__(
        self,
        store: StateStore,
        *,
        nonce_factory: Callable[[int], bytes] = secrets.token_bytes,
    ) -> None:
        if store is None:
            raise RunLifecycleValidationError("A StateStore is required.")
        if not callable(nonce_factory):
            raise RunLifecycleValidationError("nonce_factory must be callable.")
        self._store = store
        self._nonce_factory = nonce_factory
        self._backend_profile = _backend_durability_profile(store)

    @property
    def backend_durability_profile(self) -> Mapping[str, str]:
        return dict(self._backend_profile)

    def issue_with_builder(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        authorized_at: datetime,
        expires_at: datetime,
        authorization_request_sha256: str,
        authorization_builder: Callable[[str], ArtifactBinding],
    ) -> RunNonceIssuance:
        """Reserve a nonce, build nonce-bearing authorization bytes, then release.

        ``authorization_request_sha256`` must be a caller-computed canonical digest
        over every pre-nonce authorization fact (including the preregistration
        chain, authorization identity, execution mapping, and issue/expiry times).
        The registry can enforce equality of that digest but cannot attest that the
        caller derived it honestly.  The injected builder receives the raw nonce
        only after create-only subject and nonce-digest reservations exist.  It
        must return the exact immutable artifact binding for the strict
        authorization bytes that embed that nonce.
        A builder failure leaves an unrecoverable pending reservation visible to
        reconciliation; a retry cannot recover or reissue its raw secret.
        """

        tenant_id = _required_text(tenant_id, "tenant_id")
        subject_id = _required_text(subject_id, "subject_id")
        if not callable(authorization_builder):
            raise RunLifecycleValidationError(
                "authorization_builder must be callable."
            )
        authorized_iso = _utc_iso(authorized_at, "authorized_at")
        expires_iso = _utc_iso(expires_at, "expires_at")
        authorization_request_sha256 = _required_lower_sha256(
            authorization_request_sha256, "authorization_request_sha256"
        )
        if _parse_utc(expires_iso) <= _parse_utc(authorized_iso):
            raise RunLifecycleValidationError("expires_at must follow authorized_at.")

        run_id = _run_id(subject_id)
        subject_record_id = _subject_record_id(subject_id)
        request_sha256 = _sha256_json(
            {
                "subject_id": subject_id,
                "authorized_at": authorized_iso,
                "expires_at": expires_iso,
                "authorization_request_sha256": authorization_request_sha256,
            }
        )
        existing = self._store.get(
            tenant_id, SUBJECT_RESERVATION_KIND, subject_record_id
        )
        if existing is not None:
            self._assert_subject_request(existing, request_sha256=request_sha256)
            finalization = self._authorization_finalization_for_subject(
                tenant_id, existing
            )
            if finalization is None:
                raise RunLifecycleQuarantined(
                    "nonce was reserved but authorization finalization is absent; "
                    "the raw nonce is intentionally unrecoverable"
                )
            lifecycle = self._complete_initialization(
                tenant_id, existing, finalization
            )
            return RunNonceIssuance(
                lifecycle=lifecycle,
                run_nonce=None,
                issued_now=False,
            )

        raw_nonce_bytes = self._fresh_unreserved_nonce(tenant_id)
        raw_nonce = _encode_nonce(raw_nonce_bytes)
        nonce_sha256 = hashlib.sha256(raw_nonce_bytes).hexdigest()
        issuance_id = "h2issue_" + secrets.token_hex(16)
        authority = _authority()
        subject_payload = {
            "schema": SUBJECT_RESERVATION_SCHEMA,
            "reservation": "CREATE_ONLY_PENDING_AUTHORIZATION",
            "run_id": run_id,
            "subject_id": subject_id,
            "request_sha256": request_sha256,
            "authorization_request_sha256": authorization_request_sha256,
            "run_nonce_sha256": nonce_sha256,
            "issuance_id": issuance_id,
            "authorized_at": authorized_iso,
            "expires_at": expires_iso,
            "backend_durability_profile": dict(self._backend_profile),
            "authority": authority,
        }
        subject_record = LedgerRecord.new(
            tenant_id=tenant_id,
            kind=SUBJECT_RESERVATION_KIND,
            record_id=subject_record_id,
            payload=subject_payload,
            source="cas_harness_v2_run_lifecycle.issue_with_builder",
            trace_id=run_id,
            now=authorized_at.astimezone(UTC),
        )
        try:
            stored_subject = self._store.put(subject_record, expected_version=0)
        except VersionConflict:
            stored_subject = self._store.get(
                tenant_id, SUBJECT_RESERVATION_KIND, subject_record_id
            )
            if stored_subject is None:
                raise RunLifecyclePersistenceError(
                    "subject reservation conflicted but is not tenant-visible"
                )
            self._assert_subject_request(
                stored_subject, request_sha256=request_sha256
            )
            finalization = self._authorization_finalization_for_subject(
                tenant_id, stored_subject
            )
            if finalization is None:
                raise RunLifecycleQuarantined(
                    "another invocation reserved the subject; its raw nonce is "
                    "not available to this invocation"
                )
            lifecycle = self._complete_initialization(
                tenant_id, stored_subject, finalization
            )
            return RunNonceIssuance(
                lifecycle=lifecycle,
                run_nonce=None,
                issued_now=False,
            )

        nonce_payload = {
            "schema": NONCE_RESERVATION_SCHEMA,
            "reservation": "CREATE_ONLY_DIGEST_ONLY_PENDING_AUTHORIZATION",
            "run_id": run_id,
            "subject_id": subject_id,
            "request_sha256": request_sha256,
            "authorization_request_sha256": authorization_request_sha256,
            "run_nonce_sha256": nonce_sha256,
            "issuance_id": issuance_id,
            "authorized_at": authorized_iso,
            "expires_at": expires_iso,
            "backend_durability_profile": dict(self._backend_profile),
            "authority": authority,
        }
        self._create_exact(
            LedgerRecord.new(
                tenant_id=tenant_id,
                kind=NONCE_RESERVATION_KIND,
                record_id=_nonce_record_id(nonce_sha256),
                payload=nonce_payload,
                parent_ids=(stored_subject.record_id,),
                source="cas_harness_v2_run_lifecycle.issue_with_builder",
                trace_id=run_id,
            )
        )
        try:
            authorization_artifact = authorization_builder(raw_nonce)
        except Exception as exc:
            raise RunLifecycleBuilderError(
                "authorization builder failed after nonce reservation; lifecycle "
                "is quarantined and the raw nonce was not released"
            ) from exc
        if not isinstance(authorization_artifact, ArtifactBinding):
            raise RunLifecycleBuilderError(
                "authorization builder must return an ArtifactBinding; lifecycle "
                "is quarantined and the raw nonce was not released"
            )
        finalization_payload = {
            "schema": AUTHORIZATION_FINALIZATION_SCHEMA,
            "record_profile": "CREATE_ONLY_AUTHORIZATION_BINDING",
            "run_id": run_id,
            "subject_id": subject_id,
            "request_sha256": request_sha256,
            "authorization_request_sha256": authorization_request_sha256,
            "run_nonce_sha256": nonce_sha256,
            "issuance_id": issuance_id,
            "authorized_at": authorized_iso,
            "expires_at": expires_iso,
            "authorization_artifact": authorization_artifact.as_dict(),
            "builder_assurance": "INJECTED_CALLABLE_PROVENANCE_NOT_ATTESTED",
            "backend_durability_profile": dict(self._backend_profile),
            "authority": authority,
        }
        finalization = self._create_exact(
            LedgerRecord.new(
                tenant_id=tenant_id,
                kind=AUTHORIZATION_FINALIZATION_KIND,
                record_id=_authorization_finalization_record_id(run_id),
                payload=finalization_payload,
                parent_ids=(stored_subject.record_id, _nonce_record_id(nonce_sha256)),
                source="cas_harness_v2_run_lifecycle.authorization_finalization",
                trace_id=run_id,
            )
        )
        lifecycle = self._complete_initialization(
            tenant_id, stored_subject, finalization
        )
        # Release occurs only after exact finalization, genesis, and lifecycle
        # index records were written and re-read through StateStore.
        return RunNonceIssuance(
            lifecycle=lifecycle,
            run_nonce=raw_nonce,
            issued_now=True,
        )

    def issue_authorization(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        authorized_at: datetime,
        expires_at: datetime,
        authorization_request_sha256: str,
        authorization_builder: Callable[[str], ArtifactBinding],
    ) -> RunNonceIssuance:
        """Compatibility name for :meth:`issue_with_builder`; no prebuilt bytes."""

        return self.issue_with_builder(
            tenant_id=tenant_id,
            subject_id=subject_id,
            authorized_at=authorized_at,
            expires_at=expires_at,
            authorization_request_sha256=authorization_request_sha256,
            authorization_builder=authorization_builder,
        )

    def consume_authorization(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        run_nonce: str,
        operation_id: str,
        worker_id: str,
        consumption_artifact: ArtifactBinding,
        started_at: datetime,
        lease_fence: Mapping[str, Any] | None = None,
        clock_observation: Mapping[str, Any] | None = None,
    ) -> RunLifecycleMutation:
        """Atomically move one exact authorization from AUTHORIZED to RUNNING."""

        nonce_bytes = _decode_nonce(run_nonce)
        details = {
            "worker_id": _required_text(worker_id, "worker_id"),
            "consumption_artifact": _artifact_dict(
                consumption_artifact, "consumption_artifact"
            ),
        }
        if (lease_fence is None) != (clock_observation is None):
            raise RunLifecycleValidationError(
                "lease_fence and clock_observation must be supplied together"
            )
        if lease_fence is not None and clock_observation is not None:
            details["lease_fence"] = _lease_fence_dict(lease_fence)
            details["clock_observation"] = _clock_observation_dict(
                clock_observation
            )
        occurred_at = _utc_iso(started_at, "started_at")
        if clock_observation is not None and details["clock_observation"][
            "observed_at"
        ] != occurred_at:
            raise RunLifecycleValidationError(
                "clock_observation must match the RUNNING event time"
            )

        def validate(record: LedgerRecord) -> None:
            payload = record.payload
            observed = hashlib.sha256(nonce_bytes).hexdigest()
            expected = _payload_text(payload, "run_nonce_sha256")
            if not hmac.compare_digest(observed, expected):
                raise RunLifecycleConflict("run nonce does not match this authorization")
            if _parse_utc(occurred_at) >= _parse_utc(
                _payload_text(payload, "expires_at")
            ):
                raise RunLifecycleExpired(
                    "authorization expiry was reached before consumption"
                )

        return self._append_transition(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation_id,
            event_type=RUNNING,
            occurred_at=occurred_at,
            details=details,
            allowed_from=frozenset({AUTHORIZED}),
            state_after=RUNNING,
            precondition=validate,
        )

    def record_terminal(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        operation_id: str,
        terminal_status: str,
        terminal_artifact: ArtifactBinding,
        terminal_at: datetime,
        lease_fence: Mapping[str, Any] | None = None,
        clock_observation: Mapping[str, Any] | None = None,
        disposition_reason_code: str | None = None,
    ) -> RunLifecycleMutation:
        """Record success or an adverse terminal disposition with exact bytes."""

        if terminal_status not in TERMINAL_STATES:
            raise RunLifecycleValidationError(
                f"terminal_status must be one of {sorted(TERMINAL_STATES)!r}."
            )
        allowed = (
            frozenset({AUTHORIZED})
            if terminal_status in {REJECTED, EXPIRED}
            else frozenset({RUNNING})
        )
        if lease_fence is not None and clock_observation is None:
            raise RunLifecycleValidationError(
                "a terminal lease_fence requires a clock_observation"
            )
        details: dict[str, Any] = {
            "terminal_status": terminal_status,
            "terminal_artifact": _artifact_dict(
                terminal_artifact, "terminal_artifact"
            ),
        }
        if clock_observation is not None:
            details["clock_observation"] = _clock_observation_dict(
                clock_observation
            )
        if lease_fence is not None:
            details["lease_fence"] = _lease_fence_dict(lease_fence)
        if disposition_reason_code is not None:
            if terminal_status not in {INDETERMINATE, REJECTED, EXPIRED}:
                raise RunLifecycleValidationError(
                    "disposition_reason_code is available only for server dispositions"
                )
            details["disposition_reason_code"] = _required_text(
                disposition_reason_code, "disposition_reason_code"
            )
        occurred_at = _utc_iso(terminal_at, "terminal_at")
        if clock_observation is not None and details["clock_observation"][
            "observed_at"
        ] != occurred_at:
            raise RunLifecycleValidationError(
                "clock_observation must match the terminal event time"
            )

        def validate(record: LedgerRecord) -> None:
            expiry = _parse_utc(_payload_text(record.payload, "expires_at"))
            observed = _parse_utc(occurred_at)
            if terminal_status == EXPIRED and observed < expiry:
                raise RunLifecycleConflict(
                    "EXPIRED cannot be recorded before authorization expiry"
                )
            if terminal_status == REJECTED and observed >= expiry:
                raise RunLifecycleConflict(
                    "REJECTED cannot replace EXPIRED after authorization expiry"
                )

        return self._append_transition(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation_id,
            event_type="TERMINAL_RECORDED",
            occurred_at=occurred_at,
            details=details,
            allowed_from=allowed,
            state_after=terminal_status,
            precondition=validate,
        )

    def reserve_outcome_access(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        operation_id: str,
        requested_at: datetime,
        terminal_artifact: ArtifactBinding,
    ) -> OutcomeAccessReservation:
        """Fix outcome-access time and terminal binding before chain mutation."""

        tenant_id = _required_text(tenant_id, "tenant_id")
        subject_id = _required_text(subject_id, "subject_id")
        operation_id = _required_text(operation_id, "operation_id")
        accessed_at = _utc_iso(requested_at, "requested_at")
        terminal_binding = _artifact_dict(terminal_artifact, "terminal_artifact")
        run_id = _run_id(subject_id)
        reservation_id = _outcome_access_reservation_id(run_id)
        existing = self._store.get(
            tenant_id, OUTCOME_ACCESS_RESERVATION_KIND, reservation_id
        )
        if existing is not None:
            expected_fingerprint = _sha256_json(
                {
                    "run_id": run_id,
                    "subject_id": subject_id,
                    "operation_id": operation_id,
                    "accessed_at": accessed_at,
                    "terminal_artifact": terminal_binding,
                }
            )
            if existing.payload.get("request_fingerprint_sha256") != expected_fingerprint:
                raise RunLifecycleConflict(
                    "outcome-access reservation operation conflicts with stored facts"
                )
            return _outcome_reservation_snapshot(existing)

        lifecycle = self._require_lifecycle(tenant_id, subject_id)
        terminal_state = _payload_text(lifecycle.payload, "current_state")
        if terminal_state not in {SUCCESS, FAILURE}:
            raise RunLifecycleConflict(
                "outcome access requires a strict completed or failed execution receipt"
            )
        terminal_sequence = _payload_int(
            lifecycle.payload, "event_count", minimum=1
        ) - 1
        terminal_event = self._store.get(
            tenant_id, EVENT_KIND, _event_record_id(run_id, terminal_sequence)
        )
        if terminal_event is None:
            raise RunLifecyclePersistenceError("terminal event is missing")
        terminal_details = terminal_event.payload.get("details")
        if not isinstance(terminal_details, Mapping):
            raise RunLifecyclePersistenceError("terminal event details are invalid")
        if terminal_details.get("terminal_artifact") != terminal_binding:
            raise RunLifecycleConflict(
                "terminal artifact does not match the current terminal event"
            )
        terminal_event_sha256 = _payload_text(
            terminal_event.payload, "event_sha256"
        )
        request_fingerprint = _sha256_json(
            {
                "run_id": run_id,
                "subject_id": subject_id,
                "operation_id": operation_id,
                "accessed_at": accessed_at,
                "terminal_artifact": terminal_binding,
            }
        )
        payload = {
            "schema": OUTCOME_ACCESS_RESERVATION_SCHEMA,
            "reservation": "CREATE_ONLY_PENDING_OUTCOME_ACCESS_FINALIZATION",
            "run_id": run_id,
            "subject_id": subject_id,
            "reservation_id": reservation_id,
            "operation_id": operation_id,
            "request_fingerprint_sha256": request_fingerprint,
            "accessed_at": accessed_at,
            "time_assurance": "CALLER_OR_PROCESS_TIME_NOT_TRUSTED",
            "terminal_state": terminal_state,
            "terminal_event_sha256": terminal_event_sha256,
            "terminal_artifact": terminal_binding,
            "backend_durability_profile": _json_copy(
                lifecycle.payload.get("backend_durability_profile")
            ),
            "authority": _authority(),
        }
        stored = self._create_exact(
            LedgerRecord.new(
                tenant_id=tenant_id,
                kind=OUTCOME_ACCESS_RESERVATION_KIND,
                record_id=reservation_id,
                payload=payload,
                parent_ids=(run_id, terminal_event.record_id),
                source="cas_harness_v2_run_lifecycle.outcome_access_reservation",
                trace_id=run_id,
            )
        )
        return _outcome_reservation_snapshot(stored)

    def finalize_outcome_access(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        reservation_id: str,
        outcome_access_artifact: ArtifactBinding,
    ) -> RunLifecycleMutation:
        tenant_id = _required_text(tenant_id, "tenant_id")
        subject_id = _required_text(subject_id, "subject_id")
        reservation_id = _required_text(reservation_id, "reservation_id")
        record = self._store.get(
            tenant_id, OUTCOME_ACCESS_RESERVATION_KIND, reservation_id
        )
        if record is None:
            raise RunLifecycleNotFound("outcome-access reservation not found")
        reservation = _outcome_reservation_snapshot(record)
        if reservation.subject_id != subject_id or reservation.run_id != _run_id(
            subject_id
        ):
            raise RunLifecycleConflict(
                "outcome-access reservation subject binding conflicts"
            )
        return self._append_transition(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=reservation.operation_id,
            event_type=OUTCOME_ACCESSED,
            occurred_at=reservation.accessed_at,
            details={
                "outcome_access_reservation_id": reservation.reservation_id,
                "terminal_event_sha256": reservation.terminal_event_sha256,
                "terminal_artifact": dict(reservation.terminal_artifact),
                "outcome_access_artifact": _artifact_dict(
                    outcome_access_artifact, "outcome_access_artifact"
                )
            },
            allowed_from=frozenset({SUCCESS, FAILURE}),
            state_after=OUTCOME_ACCESSED,
        )

    def record_outcome_access(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        operation_id: str,
        terminal_artifact: ArtifactBinding,
        outcome_access_artifact: ArtifactBinding,
        accessed_at: datetime,
    ) -> RunLifecycleMutation:
        """Convenience wrapper that still persists reservation before finalization."""

        reservation = self.reserve_outcome_access(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation_id,
            requested_at=accessed_at,
            terminal_artifact=terminal_artifact,
        )
        return self.finalize_outcome_access(
            tenant_id=tenant_id,
            subject_id=subject_id,
            reservation_id=reservation.reservation_id,
            outcome_access_artifact=outcome_access_artifact,
        )

    def record_packet(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        operation_id: str,
        packet_artifact: ArtifactBinding,
        recorded_at: datetime,
    ) -> RunLifecycleMutation:
        return self._append_transition(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation_id,
            event_type=PACKET_RECORDED,
            occurred_at=_utc_iso(recorded_at, "recorded_at"),
            details={
                "packet_artifact": _artifact_dict(packet_artifact, "packet_artifact")
            },
            allowed_from=frozenset({OUTCOME_ACCESSED}),
            state_after=PACKET_RECORDED,
        )

    def record_nonreporting(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        operation_id: str,
        nonreporting_artifact: ArtifactBinding,
        reason_code: str,
        recorded_at: datetime,
    ) -> RunLifecycleMutation:
        return self._append_transition(
            tenant_id=tenant_id,
            subject_id=subject_id,
            operation_id=operation_id,
            event_type=NONREPORTING_RECORDED,
            occurred_at=_utc_iso(recorded_at, "recorded_at"),
            details={
                "reason_code": _required_text(reason_code, "reason_code"),
                "nonreporting_artifact": _artifact_dict(
                    nonreporting_artifact, "nonreporting_artifact"
                ),
            },
            allowed_from=frozenset(
                {OUTCOME_ACCESSED, INDETERMINATE, REJECTED, EXPIRED}
            ),
            state_after=NONREPORTING_RECORDED,
        )

    def get_lifecycle(
        self, *, tenant_id: str, subject_id: str
    ) -> RunLifecycleSnapshot | None:
        tenant_id = _required_text(tenant_id, "tenant_id")
        subject_id = _required_text(subject_id, "subject_id")
        record = self._store.get(tenant_id, LIFECYCLE_KIND, _run_id(subject_id))
        if record is None:
            return None
        return _snapshot(record)

    def list_events(
        self, *, tenant_id: str, subject_id: str
    ) -> tuple[Mapping[str, Any], ...]:
        tenant_id = _required_text(tenant_id, "tenant_id")
        subject_id = _required_text(subject_id, "subject_id")
        record = self._require_lifecycle(tenant_id, subject_id)
        count = _payload_int(record.payload, "event_count", minimum=1)
        events: list[Mapping[str, Any]] = []
        for sequence in range(count):
            event = self._store.get(
                tenant_id, EVENT_KIND, _event_record_id(record.record_id, sequence)
            )
            if event is None:
                raise RunLifecyclePersistenceError(
                    f"indexed event {sequence} is missing for {record.record_id}"
                )
            events.append(dict(event.payload))
        return tuple(events)

    def reconcile(self, *, tenant_id: str) -> RunLifecycleReconciliation:
        """Exhaustively reconcile all tenant-visible lifecycle registry records."""

        tenant_id = _required_text(tenant_id, "tenant_id")
        lifecycles = self._store.list(tenant_id, LIFECYCLE_KIND)
        subjects = self._store.list(tenant_id, SUBJECT_RESERVATION_KIND)
        nonces = self._store.list(tenant_id, NONCE_RESERVATION_KIND)
        finalizations = self._store.list(
            tenant_id, AUTHORIZATION_FINALIZATION_KIND
        )
        outcome_reservations = self._store.list(
            tenant_id, OUTCOME_ACCESS_RESERVATION_KIND
        )
        events = self._store.list(tenant_id, EVENT_KIND)
        issues: list[ReconciliationIssue] = []
        state_counts: dict[str, int] = {}

        lifecycle_by_id = {record.record_id: record for record in lifecycles}
        subject_by_id = {record.record_id: record for record in subjects}
        nonce_by_id = {record.record_id: record for record in nonces}
        finalization_by_id = {
            record.record_id: record for record in finalizations
        }
        outcome_reservation_by_id = {
            record.record_id: record for record in outcome_reservations
        }
        events_by_run: dict[str, list[LedgerRecord]] = {}
        for event in events:
            run_id = event.payload.get("run_id")
            if not isinstance(run_id, str):
                issues.append(
                    ReconciliationIssue(
                        "EVENT_RUN_ID_INVALID",
                        event.record_id,
                        "event has no exact string run_id",
                    )
                )
                continue
            events_by_run.setdefault(run_id, []).append(event)

        referenced_subjects: set[str] = set()
        referenced_nonces: set[str] = set()
        referenced_finalizations: set[str] = set()
        finalized_outcome_reservations: set[str] = set()
        for lifecycle in lifecycles:
            try:
                self._verify_lifecycle(
                    lifecycle,
                    subject_by_id=subject_by_id,
                    nonce_by_id=nonce_by_id,
                    finalization_by_id=finalization_by_id,
                    outcome_reservation_by_id=outcome_reservation_by_id,
                    event_records=events_by_run.get(lifecycle.record_id, []),
                )
            except RunLifecycleError as exc:
                issues.append(
                    ReconciliationIssue(
                        "LIFECYCLE_INTEGRITY_FAILURE",
                        lifecycle.record_id,
                        str(exc),
                    )
                )
            state = lifecycle.payload.get("current_state")
            state_key = state if isinstance(state, str) else "INVALID_STATE"
            state_counts[state_key] = state_counts.get(state_key, 0) + 1
            subject_id = lifecycle.payload.get("subject_id")
            nonce_sha = lifecycle.payload.get("run_nonce_sha256")
            if isinstance(subject_id, str):
                referenced_subjects.add(_subject_record_id(subject_id))
            if isinstance(nonce_sha, str) and _is_lower_sha256(nonce_sha):
                referenced_nonces.add(_nonce_record_id(nonce_sha))
            finalization_id = lifecycle.payload.get(
                "authorization_finalization_record_id"
            )
            if isinstance(finalization_id, str):
                referenced_finalizations.add(finalization_id)
            for event in events_by_run.get(lifecycle.record_id, []):
                if event.payload.get("event_type") != OUTCOME_ACCESSED:
                    continue
                details = event.payload.get("details")
                if isinstance(details, Mapping):
                    reservation_id = details.get("outcome_access_reservation_id")
                    if isinstance(reservation_id, str):
                        finalized_outcome_reservations.add(reservation_id)

        for subject in subjects:
            run_id = subject.payload.get("run_id")
            if subject.record_id not in referenced_subjects or run_id not in lifecycle_by_id:
                issues.append(
                    ReconciliationIssue(
                        "ORPHAN_SUBJECT_RESERVATION",
                        subject.record_id,
                        "create-only subject reservation has no lifecycle index",
                    )
                )
        for nonce in nonces:
            run_id = nonce.payload.get("run_id")
            if nonce.record_id not in referenced_nonces or run_id not in lifecycle_by_id:
                issues.append(
                    ReconciliationIssue(
                        "ORPHAN_NONCE_RESERVATION",
                        nonce.record_id,
                        "create-only nonce reservation has no lifecycle index",
                    )
                )
        for finalization in finalizations:
            run_id = finalization.payload.get("run_id")
            if (
                finalization.record_id not in referenced_finalizations
                or run_id not in lifecycle_by_id
            ):
                issues.append(
                    ReconciliationIssue(
                        "ORPHAN_AUTHORIZATION_FINALIZATION",
                        finalization.record_id,
                        "create-only authorization finalization has no lifecycle index",
                    )
                )
        for reservation in outcome_reservations:
            run_id = reservation.payload.get("run_id")
            if run_id not in lifecycle_by_id:
                issues.append(
                    ReconciliationIssue(
                        "ORPHAN_OUTCOME_ACCESS_RESERVATION",
                        reservation.record_id,
                        "outcome-access reservation has no lifecycle index",
                    )
                )
            elif reservation.record_id not in finalized_outcome_reservations:
                issues.append(
                    ReconciliationIssue(
                        "PENDING_OUTCOME_ACCESS_FINALIZATION",
                        reservation.record_id,
                        "reserved accessed_at has no OUTCOME_ACCESSED event",
                    )
                )
        for run_id, run_events in events_by_run.items():
            if run_id not in lifecycle_by_id:
                for event in run_events:
                    issues.append(
                        ReconciliationIssue(
                            "ORPHAN_EVENT",
                            event.record_id,
                            "create-only event has no lifecycle index",
                        )
                    )

        registry_rows = [
            {
                "kind": record.kind,
                "record_id": record.record_id,
                "version": record.version,
                "payload": dict(record.payload),
            }
            for record in (
                *lifecycles,
                *subjects,
                *nonces,
                *finalizations,
                *outcome_reservations,
                *events,
            )
        ]
        registry_rows.sort(key=lambda row: (str(row["kind"]), str(row["record_id"])))
        registry_sha256 = _sha256_json(registry_rows)
        issues.sort(key=lambda issue: (issue.code, issue.record_id, issue.detail))
        has_registered_runs = bool(lifecycles)
        all_disposed = has_registered_runs and all(
            record.payload.get("current_state") in REPORTING_DISPOSITIONS
            for record in lifecycles
        )
        return RunLifecycleReconciliation(
            tenant_id=tenant_id,
            has_registered_runs=has_registered_runs,
            lifecycle_count=len(lifecycles),
            subject_reservation_count=len(subjects),
            nonce_reservation_count=len(nonces),
            authorization_finalization_count=len(finalizations),
            outcome_access_reservation_count=len(outcome_reservations),
            event_count=len(events),
            state_counts=dict(sorted(state_counts.items())),
            issue_count=len(issues),
            issues=tuple(issues),
            structurally_valid=not issues,
            all_runs_reporting_disposed=all_disposed,
            registry_sha256=registry_sha256,
            backend_durability_profile=dict(self._backend_profile),
        )

    # ------------------------------------------------------------------
    # Persistence and integrity helpers

    def _fresh_unreserved_nonce(self, tenant_id: str) -> bytes:
        for _attempt in range(16):
            candidate = self._nonce_factory(32)
            if type(candidate) is not bytes or len(candidate) != 32:
                raise RunLifecycleValidationError(
                    "nonce_factory must return exactly 32 bytes."
                )
            digest = hashlib.sha256(candidate).hexdigest()
            if self._store.get(
                tenant_id, NONCE_RESERVATION_KIND, _nonce_record_id(digest)
            ) is None:
                return candidate
        raise RunLifecycleConflict(
            "nonce_factory produced an already-reserved digest 16 times"
        )

    def _assert_subject_request(
        self, record: LedgerRecord, *, request_sha256: str
    ) -> None:
        if record.payload.get("schema") != SUBJECT_RESERVATION_SCHEMA:
            raise RunLifecycleConflict("subject reservation schema conflicts")
        observed = _payload_text(record.payload, "request_sha256")
        if not hmac.compare_digest(observed, request_sha256):
            raise RunLifecycleConflict(
                "subject is already reserved for different authorization facts"
            )

    def _authorization_finalization_for_subject(
        self, tenant_id: str, subject_record: LedgerRecord
    ) -> LedgerRecord | None:
        run_id = _payload_text(subject_record.payload, "run_id")
        return self._store.get(
            tenant_id,
            AUTHORIZATION_FINALIZATION_KIND,
            _authorization_finalization_record_id(run_id),
        )

    def _complete_initialization(
        self,
        tenant_id: str,
        subject_record: LedgerRecord,
        finalization_record: LedgerRecord,
    ) -> RunLifecycleSnapshot:
        payload = subject_record.payload
        finalization = finalization_record.payload
        run_id = _payload_text(payload, "run_id")
        subject_id = _payload_text(payload, "subject_id")
        nonce_sha256 = _payload_text(payload, "run_nonce_sha256")
        _required_lower_sha256(nonce_sha256, "subject.run_nonce_sha256")
        if finalization.get("schema") != AUTHORIZATION_FINALIZATION_SCHEMA:
            raise RunLifecyclePersistenceError(
                "authorization finalization schema is invalid"
            )
        for field in (
            "run_id",
            "subject_id",
            "request_sha256",
            "authorization_request_sha256",
            "run_nonce_sha256",
            "issuance_id",
            "authorized_at",
            "expires_at",
        ):
            if finalization.get(field) != payload.get(field):
                raise RunLifecyclePersistenceError(
                    f"authorization finalization {field} binding conflicts"
                )
        artifact = finalization.get("authorization_artifact")
        if not isinstance(artifact, Mapping):
            raise RunLifecyclePersistenceError(
                "authorization finalization artifact binding is invalid"
            )
        authorized_iso = _payload_text(payload, "authorized_at")
        expires_iso = _payload_text(payload, "expires_at")
        details = {
            "authorization_artifact": _json_copy(artifact),
            "authorization_finalization_record_id": finalization_record.record_id,
            "authorization_request_sha256": _payload_text(
                payload, "authorization_request_sha256"
            ),
            "run_nonce_sha256": nonce_sha256,
            "run_nonce_profile": "SERVER_CSPRNG_256_BIT_RAW_RETURNED_ONCE",
            "expires_at": expires_iso,
        }
        event_payload = _build_event_payload(
            run_id=run_id,
            subject_id=subject_id,
            sequence=0,
            event_type=AUTHORIZED,
            state_before=None,
            state_after=AUTHORIZED,
            operation_id=_payload_text(payload, "issuance_id"),
            occurred_at=authorized_iso,
            details=details,
            previous_event_sha256=_GENESIS_PREVIOUS_SHA256,
            authority=_json_copy(payload.get("authority")),
            backend_profile=_json_copy(payload.get("backend_durability_profile")),
        )
        event_sha256 = _payload_text(event_payload, "event_sha256")
        self._create_exact(
            LedgerRecord.new(
                tenant_id=tenant_id,
                kind=EVENT_KIND,
                record_id=_event_record_id(run_id, 0),
                payload=event_payload,
                parent_ids=(
                    subject_record.record_id,
                    _nonce_record_id(nonce_sha256),
                    finalization_record.record_id,
                ),
                source="cas_harness_v2_run_lifecycle.event",
                trace_id=run_id,
            )
        )
        lifecycle_payload = {
            "schema": LIFECYCLE_SCHEMA,
            "registry_profile": "DARK_RESEARCH_ONLY_PROSPECTIVE",
            "append_only_profile": (
                "STATESTORE_CREATE_ONLY_EVENTS_HASH_CHAINED_NO_EXTERNAL_WORM"
            ),
            "run_id": run_id,
            "subject_id": subject_id,
            "request_sha256": _payload_text(payload, "request_sha256"),
            "authorization_request_sha256": _payload_text(
                payload, "authorization_request_sha256"
            ),
            "run_nonce_sha256": nonce_sha256,
            "authorization_finalization_record_id": finalization_record.record_id,
            "authorization_artifact": _json_copy(artifact),
            "authorized_at": authorized_iso,
            "expires_at": expires_iso,
            "current_state": AUTHORIZED,
            "event_count": 1,
            "genesis_event_sha256": event_sha256,
            "head_event_sha256": event_sha256,
            "backend_durability_profile": _json_copy(
                payload.get("backend_durability_profile")
            ),
            "authority": _json_copy(payload.get("authority")),
        }
        lifecycle = self._create_exact(
            LedgerRecord.new(
                tenant_id=tenant_id,
                kind=LIFECYCLE_KIND,
                record_id=run_id,
                payload=lifecycle_payload,
                parent_ids=(
                    subject_record.record_id,
                    _nonce_record_id(nonce_sha256),
                    finalization_record.record_id,
                ),
                source="cas_harness_v2_run_lifecycle.index",
                trace_id=run_id,
            )
        )
        return _snapshot(lifecycle)

    def _create_exact(self, candidate: LedgerRecord) -> LedgerRecord:
        try:
            return self._store.put(candidate, expected_version=0)
        except VersionConflict:
            existing = self._store.get(
                candidate.tenant_id, candidate.kind, candidate.record_id
            )
            if existing is None:
                raise RunLifecyclePersistenceError(
                    f"{candidate.kind}/{candidate.record_id} conflicted but is absent"
                )
            if (
                _canonical_bytes(existing.payload)
                != _canonical_bytes(candidate.payload)
                or existing.parent_ids != candidate.parent_ids
                or existing.source != candidate.source
                or existing.trace_id != candidate.trace_id
            ):
                raise RunLifecycleConflict(
                    f"create-only record {candidate.kind}/{candidate.record_id} conflicts"
                )
            return existing
        except StateStoreError as exc:
            raise RunLifecyclePersistenceError(str(exc)) from exc

    def _verify_event_record(
        self,
        lifecycle: LedgerRecord,
        event: LedgerRecord,
        *,
        expected_sequence: int,
    ) -> str:
        """Verify one stored event before it is trusted for replay or recovery."""

        payload = event.payload
        run_id = lifecycle.record_id
        subject_id = _payload_text(lifecycle.payload, "subject_id")
        if event.record_id != _event_record_id(run_id, expected_sequence):
            raise RunLifecyclePersistenceError("event record id is not canonical")
        if payload.get("schema") != EVENT_SCHEMA:
            raise RunLifecyclePersistenceError("event schema is invalid")
        if payload.get("record_profile") != "CREATE_ONLY_HASH_CHAIN_EVENT":
            raise RunLifecyclePersistenceError("event record profile is invalid")
        if payload.get("run_id") != run_id:
            raise RunLifecyclePersistenceError("event run binding conflicts")
        if payload.get("subject_id") != subject_id:
            raise RunLifecyclePersistenceError("event subject binding conflicts")
        if _payload_int(payload, "sequence", minimum=0) != expected_sequence:
            raise RunLifecyclePersistenceError("event sequence binding conflicts")
        if payload.get("time_assurance") != "CALLER_OR_PROCESS_TIME_NOT_TRUSTED":
            raise RunLifecyclePersistenceError("event time assurance changed")
        if payload.get("authority") != _authority():
            raise RunLifecyclePersistenceError("event authority boundary changed")
        if payload.get("backend_durability_profile") != lifecycle.payload.get(
            "backend_durability_profile"
        ):
            raise RunLifecyclePersistenceError(
                "event backend durability profile conflicts"
            )
        if expected_sequence == 0:
            expected_parents = (
                _subject_record_id(subject_id),
                _nonce_record_id(
                    _payload_text(lifecycle.payload, "run_nonce_sha256")
                ),
                _payload_text(
                    lifecycle.payload, "authorization_finalization_record_id"
                ),
            )
        else:
            expected_parents = (run_id,)
        if (
            event.parent_ids != expected_parents
            or event.source != "cas_harness_v2_run_lifecycle.event"
            or event.trace_id != run_id
        ):
            raise RunLifecyclePersistenceError("event traceability envelope conflicts")
        details = payload.get("details")
        if not isinstance(details, Mapping):
            raise RunLifecyclePersistenceError("event details are invalid")
        observed_fingerprint = _payload_text(
            payload, "operation_fingerprint_sha256"
        )
        expected_fingerprint = _operation_fingerprint(
            event_type=_payload_text(payload, "event_type"),
            occurred_at=_payload_text(payload, "occurred_at"),
            details=details,
            state_after=_payload_text(payload, "state_after"),
        )
        if not hmac.compare_digest(observed_fingerprint, expected_fingerprint):
            raise RunLifecyclePersistenceError(
                "event operation fingerprint does not verify"
            )
        event_without_hash = dict(payload)
        observed_hash = event_without_hash.pop("event_sha256", None)
        expected_hash = hashlib.sha256(_canonical_bytes(event_without_hash)).hexdigest()
        if not isinstance(observed_hash, str) or not hmac.compare_digest(
            observed_hash, expected_hash
        ):
            raise RunLifecyclePersistenceError("event digest does not verify")
        return observed_hash

    def _repair_pending_transition_index(
        self, lifecycle: LedgerRecord
    ) -> LedgerRecord:
        """Finish a valid event-first/index-second write interrupted before CAS."""

        sequence = _payload_int(lifecycle.payload, "event_count", minimum=1)
        pending = self._store.get(
            lifecycle.tenant_id,
            EVENT_KIND,
            _event_record_id(lifecycle.record_id, sequence),
        )
        if pending is None:
            return lifecycle
        event_sha256 = self._verify_event_record(
            lifecycle, pending, expected_sequence=sequence
        )
        payload = pending.payload
        current_state = _payload_text(lifecycle.payload, "current_state")
        state_before = _payload_text(payload, "state_before")
        state_after = _payload_text(payload, "state_after")
        event_type = _payload_text(payload, "event_type")
        if state_before != current_state:
            raise RunLifecyclePersistenceError(
                "pending event state does not follow the lifecycle index"
            )
        if payload.get("previous_event_sha256") != lifecycle.payload.get(
            "head_event_sha256"
        ):
            raise RunLifecyclePersistenceError(
                "pending event predecessor does not match the lifecycle head"
            )
        _assert_valid_transition(
            event_type=event_type,
            state_before=state_before,
            state_after=state_after,
        )
        updated_payload = dict(lifecycle.payload)
        updated_payload.update(
            {
                "current_state": state_after,
                "event_count": sequence + 1,
                "head_event_sha256": event_sha256,
            }
        )
        try:
            return self._store.put(
                lifecycle.with_payload(updated_payload),
                expected_version=lifecycle.version,
            )
        except VersionConflict:
            latest = self._require_lifecycle(
                lifecycle.tenant_id,
                _payload_text(lifecycle.payload, "subject_id"),
            )
            if _payload_int(latest.payload, "event_count", minimum=1) <= sequence:
                raise RunLifecycleConflict(
                    "concurrent lifecycle update did not index the pending event"
                )
            self._verify_event_record(
                latest, pending, expected_sequence=sequence
            )
            return latest
        except StateStoreError as exc:
            raise RunLifecyclePersistenceError(str(exc)) from exc

    def _append_transition(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        operation_id: str,
        event_type: str,
        occurred_at: str,
        details: Mapping[str, Any],
        allowed_from: frozenset[str],
        state_after: str,
        precondition: Callable[[LedgerRecord], None] | None = None,
    ) -> RunLifecycleMutation:
        tenant_id = _required_text(tenant_id, "tenant_id")
        subject_id = _required_text(subject_id, "subject_id")
        operation_id = _required_text(operation_id, "operation_id")
        details_copy = _json_copy(details)
        fingerprint = _operation_fingerprint(
            event_type=event_type,
            occurred_at=occurred_at,
            details=details_copy,
            state_after=state_after,
        )
        record = self._require_lifecycle(tenant_id, subject_id)
        # Authentication/expiry preconditions apply to every invocation, including
        # an exact replay of an already indexed operation.
        if precondition is not None:
            precondition(record)
        record = self._repair_pending_transition_index(record)
        prior = self._find_operation_event(
            tenant_id=tenant_id,
            run_id=record.record_id,
            operation_id=operation_id,
        )
        if prior is not None:
            self._assert_operation_fingerprint(prior, fingerprint)
            prior_sequence = _payload_int(prior.payload, "sequence", minimum=0)
            if prior_sequence >= _payload_int(
                record.payload, "event_count", minimum=1
            ):
                raise RunLifecyclePersistenceError(
                    "operation event exists but is not indexed by the lifecycle"
                )
            self._verify_event_record(
                record, prior, expected_sequence=prior_sequence
            )
            return RunLifecycleMutation(
                lifecycle=_snapshot(record),
                event_sha256=_payload_text(prior.payload, "event_sha256"),
                idempotent_replay=True,
            )
        current_state = _payload_text(record.payload, "current_state")
        if current_state not in allowed_from:
            raise RunLifecycleConflict(
                f"cannot append {event_type} from lifecycle state {current_state}"
            )
        sequence = _payload_int(record.payload, "event_count", minimum=1)
        previous_sha256 = _payload_text(record.payload, "head_event_sha256")
        event_payload = _build_event_payload(
            run_id=record.record_id,
            subject_id=subject_id,
            sequence=sequence,
            event_type=event_type,
            state_before=current_state,
            state_after=state_after,
            operation_id=operation_id,
            occurred_at=occurred_at,
            details=details_copy,
            previous_event_sha256=previous_sha256,
            authority=_authority(),
            backend_profile=record.payload.get("backend_durability_profile"),
        )
        event = self._create_exact(
            LedgerRecord.new(
                tenant_id=tenant_id,
                kind=EVENT_KIND,
                record_id=_event_record_id(record.record_id, sequence),
                payload=event_payload,
                parent_ids=(record.record_id,),
                source="cas_harness_v2_run_lifecycle.event",
                trace_id=record.record_id,
            )
        )
        updated_payload = dict(record.payload)
        updated_payload.update(
            {
                "current_state": state_after,
                "event_count": sequence + 1,
                "head_event_sha256": event_payload["event_sha256"],
            }
        )
        try:
            updated = self._store.put(
                record.with_payload(updated_payload), expected_version=record.version
            )
        except VersionConflict:
            latest = self._require_lifecycle(tenant_id, subject_id)
            latest = self._repair_pending_transition_index(latest)
            existing = self._find_operation_event(
                tenant_id=tenant_id,
                run_id=record.record_id,
                operation_id=operation_id,
            )
            if existing is not None:
                self._assert_operation_fingerprint(existing, fingerprint)
                existing_sequence = _payload_int(
                    existing.payload, "sequence", minimum=0
                )
                self._verify_event_record(
                    latest, existing, expected_sequence=existing_sequence
                )
                if _payload_int(latest.payload, "event_count", minimum=1) > sequence:
                    return RunLifecycleMutation(
                        lifecycle=_snapshot(latest),
                        event_sha256=_payload_text(existing.payload, "event_sha256"),
                        idempotent_replay=True,
                    )
            raise RunLifecycleConflict(
                "concurrent lifecycle transition won before this index update"
            )
        except StateStoreError as exc:
            raise RunLifecyclePersistenceError(str(exc)) from exc
        return RunLifecycleMutation(
            lifecycle=_snapshot(updated),
            event_sha256=_payload_text(event.payload, "event_sha256"),
            idempotent_replay=False,
        )

    def _require_lifecycle(self, tenant_id: str, subject_id: str) -> LedgerRecord:
        record = self._store.get(tenant_id, LIFECYCLE_KIND, _run_id(subject_id))
        if record is None:
            # Deliberately indistinguishable from a record in another tenant.
            raise RunLifecycleNotFound("prospective run lifecycle not found")
        if record.payload.get("subject_id") != subject_id:
            raise RunLifecyclePersistenceError("lifecycle subject binding conflicts")
        return record

    def _find_operation_event(
        self, *, tenant_id: str, run_id: str, operation_id: str
    ) -> LedgerRecord | None:
        matches = [
            event
            for event in self._store.list(tenant_id, EVENT_KIND)
            if event.payload.get("run_id") == run_id
            and event.payload.get("operation_id") == operation_id
        ]
        if len(matches) > 1:
            raise RunLifecyclePersistenceError(
                f"operation_id {operation_id!r} appears in multiple events"
            )
        return matches[0] if matches else None

    @staticmethod
    def _assert_operation_fingerprint(
        event: LedgerRecord, expected_fingerprint: str
    ) -> None:
        observed = _payload_text(event.payload, "operation_fingerprint_sha256")
        details = event.payload.get("details")
        if not isinstance(details, Mapping):
            raise RunLifecyclePersistenceError("event details are invalid")
        recomputed = _operation_fingerprint(
            event_type=_payload_text(event.payload, "event_type"),
            occurred_at=_payload_text(event.payload, "occurred_at"),
            details=details,
            state_after=_payload_text(event.payload, "state_after"),
        )
        if not hmac.compare_digest(observed, recomputed):
            raise RunLifecyclePersistenceError(
                "stored operation fingerprint does not verify"
            )
        if not hmac.compare_digest(observed, expected_fingerprint):
            raise RunLifecycleConflict(
                "operation_id was already used with different immutable facts"
            )

    def _verify_lifecycle(
        self,
        lifecycle: LedgerRecord,
        *,
        subject_by_id: Mapping[str, LedgerRecord],
        nonce_by_id: Mapping[str, LedgerRecord],
        finalization_by_id: Mapping[str, LedgerRecord],
        outcome_reservation_by_id: Mapping[str, LedgerRecord],
        event_records: list[LedgerRecord],
    ) -> None:
        payload = lifecycle.payload
        if payload.get("schema") != LIFECYCLE_SCHEMA:
            raise RunLifecyclePersistenceError("lifecycle schema is invalid")
        if payload.get("authority") != _authority():
            raise RunLifecyclePersistenceError("lifecycle authority boundary changed")
        subject_id = _payload_text(payload, "subject_id")
        if lifecycle.record_id != _run_id(subject_id):
            raise RunLifecyclePersistenceError("lifecycle id/subject binding conflicts")
        nonce_sha = _payload_text(payload, "run_nonce_sha256")
        _required_lower_sha256(nonce_sha, "lifecycle.run_nonce_sha256")
        subject = subject_by_id.get(_subject_record_id(subject_id))
        nonce = nonce_by_id.get(_nonce_record_id(nonce_sha))
        if subject is None:
            raise RunLifecyclePersistenceError("subject reservation is missing")
        if nonce is None:
            raise RunLifecyclePersistenceError("nonce reservation is missing")
        for reservation, label in ((subject, "subject"), (nonce, "nonce")):
            if reservation.payload.get("run_id") != lifecycle.record_id:
                raise RunLifecyclePersistenceError(
                    f"{label} reservation run binding conflicts"
                )
            if reservation.payload.get("run_nonce_sha256") != nonce_sha:
                raise RunLifecyclePersistenceError(
                    f"{label} reservation nonce digest conflicts"
                )
            if reservation.payload.get("authority") != _authority():
                raise RunLifecyclePersistenceError(
                    f"{label} reservation authority boundary changed"
                )
        if subject.payload.get("request_sha256") != payload.get("request_sha256"):
            raise RunLifecyclePersistenceError("request digest binding conflicts")
        finalization_id = _payload_text(
            payload, "authorization_finalization_record_id"
        )
        finalization = finalization_by_id.get(finalization_id)
        if finalization is None:
            raise RunLifecyclePersistenceError(
                "authorization finalization is missing"
            )
        if finalization.record_id != _authorization_finalization_record_id(
            lifecycle.record_id
        ):
            raise RunLifecyclePersistenceError(
                "authorization finalization id is not canonical"
            )
        if finalization.payload.get("schema") != AUTHORIZATION_FINALIZATION_SCHEMA:
            raise RunLifecyclePersistenceError(
                "authorization finalization schema is invalid"
            )
        for field in (
            "run_id",
            "subject_id",
            "request_sha256",
            "authorization_request_sha256",
            "run_nonce_sha256",
            "authorized_at",
            "expires_at",
        ):
            expected = (
                lifecycle.record_id if field == "run_id" else payload.get(field)
            )
            if finalization.payload.get(field) != expected:
                raise RunLifecyclePersistenceError(
                    f"authorization finalization {field} binding conflicts"
                )
        if finalization.payload.get("authorization_artifact") != payload.get(
            "authorization_artifact"
        ):
            raise RunLifecyclePersistenceError(
                "authorization artifact binding conflicts"
            )
        if finalization.payload.get("authority") != _authority():
            raise RunLifecyclePersistenceError(
                "authorization finalization authority boundary changed"
            )

        event_count = _payload_int(payload, "event_count", minimum=1)
        events_by_sequence: dict[int, LedgerRecord] = {}
        for event in event_records:
            sequence = _payload_int(event.payload, "sequence", minimum=0)
            if sequence in events_by_sequence:
                raise RunLifecyclePersistenceError("duplicate event sequence")
            events_by_sequence[sequence] = event
        expected_sequences = set(range(event_count))
        observed_sequences = set(events_by_sequence)
        if observed_sequences != expected_sequences:
            missing = sorted(expected_sequences - observed_sequences)
            unindexed = sorted(observed_sequences - expected_sequences)
            raise RunLifecyclePersistenceError(
                f"event/index divergence; missing={missing}, unindexed={unindexed}"
            )

        previous = _GENESIS_PREVIOUS_SHA256
        prior_state: str | None = None
        operation_ids: set[str] = set()
        for sequence in range(event_count):
            event = events_by_sequence[sequence]
            event_payload = event.payload
            if event.record_id != _event_record_id(lifecycle.record_id, sequence):
                raise RunLifecyclePersistenceError("event record id is not canonical")
            if event_payload.get("schema") != EVENT_SCHEMA:
                raise RunLifecyclePersistenceError("event schema is invalid")
            if event_payload.get("run_id") != lifecycle.record_id:
                raise RunLifecyclePersistenceError("event run binding conflicts")
            if event_payload.get("subject_id") != subject_id:
                raise RunLifecyclePersistenceError("event subject binding conflicts")
            if event_payload.get("authority") != _authority():
                raise RunLifecyclePersistenceError("event authority boundary changed")
            if event_payload.get("previous_event_sha256") != previous:
                raise RunLifecyclePersistenceError("event hash-chain predecessor conflicts")
            event_without_hash = dict(event_payload)
            observed_hash = event_without_hash.pop("event_sha256", None)
            expected_hash = hashlib.sha256(
                _canonical_bytes(event_without_hash)
            ).hexdigest()
            if observed_hash != expected_hash:
                raise RunLifecyclePersistenceError("event digest does not verify")
            operation_id = _payload_text(event_payload, "operation_id")
            if operation_id in operation_ids:
                raise RunLifecyclePersistenceError("operation_id was reused")
            operation_ids.add(operation_id)
            state_before = event_payload.get("state_before")
            state_after = _payload_text(event_payload, "state_after")
            event_type = _payload_text(event_payload, "event_type")
            if event_type == OUTCOME_ACCESSED:
                details = event_payload.get("details")
                if not isinstance(details, Mapping):
                    raise RunLifecyclePersistenceError(
                        "outcome-access event details are invalid"
                    )
                reservation_id = _payload_text(
                    details, "outcome_access_reservation_id"
                )
                reservation = outcome_reservation_by_id.get(reservation_id)
                if reservation is None:
                    raise RunLifecyclePersistenceError(
                        "outcome-access reservation is missing"
                    )
                reservation_payload = reservation.payload
                if (
                    reservation_payload.get("schema")
                    != OUTCOME_ACCESS_RESERVATION_SCHEMA
                    or reservation_payload.get("run_id") != lifecycle.record_id
                    or reservation_payload.get("subject_id") != subject_id
                    or reservation_payload.get("operation_id") != operation_id
                    or reservation_payload.get("accessed_at")
                    != event_payload.get("occurred_at")
                    or reservation_payload.get("terminal_event_sha256")
                    != details.get("terminal_event_sha256")
                    or reservation_payload.get("terminal_artifact")
                    != details.get("terminal_artifact")
                    or reservation_payload.get("authority") != _authority()
                ):
                    raise RunLifecyclePersistenceError(
                        "outcome-access reservation/event binding conflicts"
                    )
            if sequence == 0:
                if (
                    event_type != AUTHORIZED
                    or state_before is not None
                    or state_after != AUTHORIZED
                ):
                    raise RunLifecyclePersistenceError(
                        "genesis event is not an AUTHORIZED transition"
                    )
                genesis_details = event_payload.get("details")
                if (
                    not isinstance(genesis_details, Mapping)
                    or genesis_details.get("authorization_artifact")
                    != finalization.payload.get("authorization_artifact")
                    or genesis_details.get("authorization_finalization_record_id")
                    != finalization.record_id
                    or genesis_details.get("authorization_request_sha256")
                    != payload.get("authorization_request_sha256")
                    or genesis_details.get("run_nonce_sha256") != nonce_sha
                    or genesis_details.get("expires_at") != payload.get("expires_at")
                ):
                    raise RunLifecyclePersistenceError(
                        "genesis authorization bindings conflict"
                    )
                if payload.get("genesis_event_sha256") != expected_hash:
                    raise RunLifecyclePersistenceError(
                        "lifecycle genesis digest conflicts"
                    )
            else:
                if state_before != prior_state:
                    raise RunLifecyclePersistenceError("event state chain conflicts")
                _assert_valid_transition(
                    event_type=event_type,
                    state_before=_required_text(state_before, "event.state_before"),
                    state_after=state_after,
                )
            previous = expected_hash
            prior_state = state_after
        if payload.get("head_event_sha256") != previous:
            raise RunLifecyclePersistenceError("lifecycle head digest conflicts")
        if payload.get("current_state") != prior_state:
            raise RunLifecyclePersistenceError("lifecycle current state conflicts")


def _authority() -> dict[str, str]:
    return {
        "criteria_status": "OPEN",
        "execution_authentication": "NOT_ESTABLISHED",
        "trusted_time": "NOT_ESTABLISHED",
        "worm_authority": "NOT_ESTABLISHED",
        "independent_authority": "NOT_ESTABLISHED",
        "scientific_status": "NOT_ESTABLISHED",
        "product_status": "NOT_ESTABLISHED",
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
    }


def _backend_durability_profile(store: StateStore) -> dict[str, str]:
    module = type(store).__module__
    name = type(store).__name__
    if name == "InMemoryStateStore" and module.endswith(".memory_store"):
        return {
            "profile": "PROCESS_LOCAL_NON_DURABLE",
            "atomic_compare_and_swap_scope": "SINGLE_STORE_INSTANCE_ONLY",
            "same_host_restart": "UNAVAILABLE",
            "multi_host": "UNAVAILABLE",
            "host_loss_survival": "UNAVAILABLE",
            "independent_attestation": "NOT_ESTABLISHED",
        }
    if name == "SqliteStateStore" and module.endswith(".sqlite_store"):
        return {
            "profile": "SQLITE_SINGLE_HOST_DURABLE_NOT_REPLICATED",
            "atomic_compare_and_swap_scope": "SAME_HOST_SQLITE_DATABASE_FILE",
            "same_host_restart": "PRESENT_BY_BACKEND_CONTRACT",
            "multi_host": "UNAVAILABLE",
            "host_loss_survival": "UNAVAILABLE",
            "independent_attestation": "NOT_ESTABLISHED",
        }
    return {
        "profile": "STATESTORE_INTERFACE_ONLY_DURABILITY_NOT_ESTABLISHED",
        "atomic_compare_and_swap_scope": "NOT_ESTABLISHED",
        "same_host_restart": "NOT_ESTABLISHED",
        "multi_host": "NOT_ESTABLISHED",
        "host_loss_survival": "NOT_ESTABLISHED",
        "independent_attestation": "NOT_ESTABLISHED",
    }


def _build_event_payload(
    *,
    run_id: str,
    subject_id: str,
    sequence: int,
    event_type: str,
    state_before: str | None,
    state_after: str,
    operation_id: str,
    occurred_at: str,
    details: Mapping[str, Any],
    previous_event_sha256: str,
    authority: Mapping[str, str],
    backend_profile: object,
) -> dict[str, Any]:
    details_copy = _json_copy(details)
    fingerprint = _operation_fingerprint(
        event_type=event_type,
        occurred_at=occurred_at,
        details=details_copy,
        state_after=state_after,
    )
    body: dict[str, Any] = {
        "schema": EVENT_SCHEMA,
        "record_profile": "CREATE_ONLY_HASH_CHAIN_EVENT",
        "run_id": run_id,
        "subject_id": subject_id,
        "sequence": sequence,
        "event_type": event_type,
        "state_before": state_before,
        "state_after": state_after,
        "operation_id": operation_id,
        "operation_fingerprint_sha256": fingerprint,
        "occurred_at": occurred_at,
        "time_assurance": "CALLER_OR_PROCESS_TIME_NOT_TRUSTED",
        "details": details_copy,
        "previous_event_sha256": previous_event_sha256,
        "backend_durability_profile": _json_copy(backend_profile),
        "authority": _json_copy(authority),
    }
    body["event_sha256"] = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    return body


def _operation_fingerprint(
    *,
    event_type: str,
    occurred_at: str,
    details: Mapping[str, Any],
    state_after: str,
) -> str:
    return _sha256_json(
        {
            "event_type": event_type,
            "occurred_at": occurred_at,
            "details": _json_copy(details),
            "state_after": state_after,
        }
    )


def _assert_valid_transition(
    *, event_type: str, state_before: str, state_after: str
) -> None:
    valid = False
    if event_type == RUNNING:
        valid = state_before == AUTHORIZED and state_after == RUNNING
    elif event_type == "TERMINAL_RECORDED":
        valid = state_after in TERMINAL_STATES and (
            (state_before == RUNNING and state_after not in {REJECTED, EXPIRED})
            or (state_before == AUTHORIZED and state_after in {REJECTED, EXPIRED})
        )
    elif event_type == OUTCOME_ACCESSED:
        valid = state_before in TERMINAL_STATES and state_after == OUTCOME_ACCESSED
    elif event_type == PACKET_RECORDED:
        valid = state_before == OUTCOME_ACCESSED and state_after == event_type
    elif event_type == NONREPORTING_RECORDED:
        valid = (
            state_before
            in {OUTCOME_ACCESSED, INDETERMINATE, REJECTED, EXPIRED}
            and state_after == event_type
        )
    if not valid:
        raise RunLifecyclePersistenceError(
            f"invalid lifecycle transition {state_before}->{state_after} ({event_type})"
        )


def _snapshot(record: LedgerRecord) -> RunLifecycleSnapshot:
    payload = record.payload
    if payload.get("schema") != LIFECYCLE_SCHEMA:
        raise RunLifecyclePersistenceError("lifecycle schema is invalid")
    profile = payload.get("backend_durability_profile")
    authority = payload.get("authority")
    if not isinstance(profile, Mapping) or not isinstance(authority, Mapping):
        raise RunLifecyclePersistenceError("lifecycle assurance maps are invalid")
    return RunLifecycleSnapshot(
        tenant_id=record.tenant_id,
        run_id=record.record_id,
        subject_id=_payload_text(payload, "subject_id"),
        authorization_request_sha256=_required_lower_sha256(
            payload.get("authorization_request_sha256"),
            "lifecycle.authorization_request_sha256",
        ),
        state=_payload_text(payload, "current_state"),
        event_count=_payload_int(payload, "event_count", minimum=1),
        head_event_sha256=_payload_text(payload, "head_event_sha256"),
        run_nonce_sha256=_payload_text(payload, "run_nonce_sha256"),
        authorized_at=_payload_text(payload, "authorized_at"),
        expires_at=_payload_text(payload, "expires_at"),
        record_version=record.version,
        backend_durability_profile=_json_copy(profile),
        authority=_json_copy(authority),
    )


def _outcome_reservation_snapshot(record: LedgerRecord) -> OutcomeAccessReservation:
    payload = record.payload
    if payload.get("schema") != OUTCOME_ACCESS_RESERVATION_SCHEMA:
        raise RunLifecyclePersistenceError(
            "outcome-access reservation schema is invalid"
        )
    terminal_artifact = payload.get("terminal_artifact")
    profile = payload.get("backend_durability_profile")
    authority = payload.get("authority")
    if (
        not isinstance(terminal_artifact, Mapping)
        or not isinstance(profile, Mapping)
        or not isinstance(authority, Mapping)
    ):
        raise RunLifecyclePersistenceError(
            "outcome-access reservation bindings are invalid"
        )
    return OutcomeAccessReservation(
        tenant_id=record.tenant_id,
        run_id=_payload_text(payload, "run_id"),
        subject_id=_payload_text(payload, "subject_id"),
        reservation_id=record.record_id,
        operation_id=_payload_text(payload, "operation_id"),
        accessed_at=_payload_text(payload, "accessed_at"),
        terminal_state=_payload_text(payload, "terminal_state"),
        terminal_event_sha256=_payload_text(payload, "terminal_event_sha256"),
        terminal_artifact=_json_copy(terminal_artifact),
        backend_durability_profile=_json_copy(profile),
        authority=_json_copy(authority),
    )


def _artifact_dict(value: ArtifactBinding, field: str) -> dict[str, object]:
    if not isinstance(value, ArtifactBinding):
        raise RunLifecycleValidationError(f"{field} must be an ArtifactBinding.")
    return value.as_dict()


def _lease_fence_dict(value: Mapping[str, Any]) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != {
        "job_id",
        "lease_generation_id",
        "lease_token_sha256",
        "lease_expires_at",
        "state_authority",
        "trusted_time",
    }:
        raise RunLifecycleValidationError(
            "lease_fence must contain only the redacted active-lease fields"
        )
    trusted_time = _required_text(value.get("trusted_time"), "lease_fence.trusted_time")
    if trusted_time != "NOT_ESTABLISHED":
        raise RunLifecycleValidationError(
            "lease_fence cannot claim trusted time"
        )
    expires_at = _canonical_caller_timestamp(
        value.get("lease_expires_at"), "lease_fence.lease_expires_at"
    )
    state_authority = _required_text(
        value.get("state_authority"), "lease_fence.state_authority"
    )
    if state_authority != "PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE":
        raise RunLifecycleValidationError(
            "lease_fence exceeds the bounded process-local authority"
        )
    return {
        "job_id": _required_text(value.get("job_id"), "lease_fence.job_id"),
        "lease_generation_id": _required_text(
            value.get("lease_generation_id"), "lease_fence.lease_generation_id"
        ),
        "lease_token_sha256": _required_lower_sha256(
            value.get("lease_token_sha256"), "lease_fence.lease_token_sha256"
        ),
        "lease_expires_at": expires_at,
        "state_authority": state_authority,
        "trusted_time": trusted_time,
    }


def _clock_observation_dict(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {
        "observed_at",
        "source",
        "assurance",
    }:
        raise RunLifecycleValidationError(
            "clock_observation must contain the exact untrusted clock fields"
        )
    assurance = _required_text(
        value.get("assurance"), "clock_observation.assurance"
    )
    if assurance != "PROCESS_OR_INJECTED_CLOCK_NOT_TRUSTED":
        raise RunLifecycleValidationError(
            "clock_observation cannot claim trusted time"
        )
    return {
        "observed_at": _canonical_caller_timestamp(
            value.get("observed_at"), "clock_observation.observed_at"
        ),
        "source": _required_text(value.get("source"), "clock_observation.source"),
        "assurance": assurance,
    }


def _canonical_caller_timestamp(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise RunLifecycleValidationError(f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RunLifecycleValidationError(f"{field} is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise RunLifecycleValidationError(f"{field} must be timezone-aware")
    return _utc_iso(parsed, field)


def _run_id(subject_id: str) -> str:
    return "h2run_" + hashlib.sha256(subject_id.encode("utf-8")).hexdigest()


def _subject_record_id(subject_id: str) -> str:
    return "h2subject_" + hashlib.sha256(subject_id.encode("utf-8")).hexdigest()


def _nonce_record_id(nonce_sha256: str) -> str:
    return "h2nonce_" + nonce_sha256


def _authorization_finalization_record_id(run_id: str) -> str:
    return "h2authfinal_" + run_id.removeprefix("h2run_")


def _outcome_access_reservation_id(run_id: str) -> str:
    # Exactly one prospective access time may be reserved for a run.  A changed
    # operation id or timestamp addresses this same create-only record and fails
    # as a conflict instead of leaving competing access reservations.
    return "h2outcome_" + run_id.removeprefix("h2run_")


def _event_record_id(run_id: str, sequence: int) -> str:
    return f"h2event_{run_id.removeprefix('h2run_')}_{sequence:08d}"


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RunLifecycleValidationError(f"{field} must be a non-empty exact string.")
    if len(value) > _MAX_TEXT_LENGTH or any(ord(char) < 32 for char in value):
        raise RunLifecycleValidationError(f"{field} contains invalid text.")
    return value


def _required_lower_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not _is_lower_sha256(value):
        raise RunLifecycleValidationError(
            f"{field} must be a lowercase 64-character SHA-256 hex digest."
        )
    return value


def _is_lower_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _payload_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise RunLifecyclePersistenceError(f"stored {field} must be an exact string")
    return value


def _payload_int(payload: Mapping[str, object], field: str, *, minimum: int) -> int:
    value = payload.get(field)
    if type(value) is not int or value < minimum:
        raise RunLifecyclePersistenceError(
            f"stored {field} must be an exact integer >= {minimum}"
        )
    return value


def _utc_iso(value: datetime, field: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise RunLifecycleValidationError(f"{field} must be timezone-aware.")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RunLifecyclePersistenceError("stored timestamp is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise RunLifecyclePersistenceError("stored timestamp is not timezone-aware")
    return parsed.astimezone(UTC)


def _encode_nonce(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_nonce(value: str) -> bytes:
    if not isinstance(value, str) or len(value) != 43:
        raise RunLifecycleValidationError(
            "run_nonce must be canonical unpadded base64url for exactly 32 bytes."
        )
    try:
        decoded = base64.urlsafe_b64decode(value + "=")
    except (ValueError, TypeError) as exc:
        raise RunLifecycleValidationError("run_nonce is not valid base64url.") from exc
    if len(decoded) != 32 or _encode_nonce(decoded) != value:
        raise RunLifecycleValidationError(
            "run_nonce must be canonical unpadded base64url for exactly 32 bytes."
        )
    return decoded


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RunLifecycleValidationError(
            "lifecycle facts must be canonical JSON values"
        ) from exc


def _json_copy(value: object) -> Any:
    return json.loads(_canonical_bytes(value).decode("utf-8"))


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


__all__ = [
    "ArtifactBinding",
    "DurableProspectiveRunLifecycle",
    "RunLifecycleConflict",
    "RunLifecycleBuilderError",
    "RunLifecycleError",
    "RunLifecycleExpired",
    "RunLifecycleMutation",
    "OutcomeAccessReservation",
    "RunLifecycleNotFound",
    "RunLifecyclePersistenceError",
    "RunLifecycleQuarantined",
    "RunLifecycleReconciliation",
    "RunLifecycleSnapshot",
    "RunLifecycleValidationError",
    "RunNonceIssuance",
    "ReconciliationIssue",
    "AUTHORIZED",
    "RUNNING",
    "SUCCESS",
    "FAILURE",
    "INDETERMINATE",
    "REJECTED",
    "EXPIRED",
    "OUTCOME_ACCESSED",
    "PACKET_RECORDED",
    "NONREPORTING_RECORDED",
    "TERMINAL_STATES",
    "REPORTING_DISPOSITIONS",
    "LIFECYCLE_KIND",
    "EVENT_KIND",
    "SUBJECT_RESERVATION_KIND",
    "NONCE_RESERVATION_KIND",
    "AUTHORIZATION_FINALIZATION_KIND",
    "OUTCOME_ACCESS_RESERVATION_KIND",
]
