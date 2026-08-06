from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import threading

import pytest

from api.services.cas_harness_v2_run_lifecycle import (
    AUTHORIZED,
    AUTHORIZATION_FINALIZATION_KIND,
    EVENT_KIND,
    EXPIRED,
    FAILURE,
    INDETERMINATE,
    LIFECYCLE_KIND,
    NONCE_RESERVATION_KIND,
    NONREPORTING_RECORDED,
    OUTCOME_ACCESSED,
    OUTCOME_ACCESS_RESERVATION_KIND,
    PACKET_RECORDED,
    REPORTING_DISPOSITION_RESERVATION_KIND,
    REJECTED,
    RUNNING,
    SUBJECT_RESERVATION_KIND,
    SUCCESS,
    ArtifactBinding,
    DurableProspectiveRunLifecycle,
    RunLifecycleConflict,
    RunLifecycleBuilderError,
    RunLifecycleExpired,
    RunLifecycleNotFound,
    RunLifecyclePersistenceError,
    RunLifecycleQuarantined,
    RunLifecycleValidationError,
)
from api.services.production.state_substrate import (
    InMemoryStateStore,
    LedgerRecord,
    StateStoreError,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore


NOW = datetime(2026, 8, 6, 16, 0, tzinfo=UTC)


def _artifact(name: str) -> ArtifactBinding:
    return ArtifactBinding.from_bytes(
        artifact_id=name,
        media_type="application/vnd.cas-harness.test+json",
        body=json.dumps({"artifact": name}, sort_keys=True).encode("utf-8"),
    )


def _authorization_request_digest(
    subject_id: str, *, variant: str = "canonical-v1"
) -> str:
    body = json.dumps(
        {
            "subject_id": subject_id,
            "variant": variant,
            "execution_mapping": "test-fixture-v1",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _service(store, *, nonce: bytes = b"R" * 32):
    return DurableProspectiveRunLifecycle(store, nonce_factory=lambda size: nonce)


def _issue(
    service: DurableProspectiveRunLifecycle,
    *,
    tenant_id: str = "tenant-a",
    subject_id: str = "worker-auth-001",
    authorization_request_sha256: str | None = None,
):
    request_digest = authorization_request_sha256 or _authorization_request_digest(
        subject_id
    )

    def build_authorization(run_nonce: str) -> ArtifactBinding:
        body = json.dumps(
            {"subject_id": subject_id, "run_nonce": run_nonce}, sort_keys=True
        ).encode("utf-8")
        return ArtifactBinding.from_bytes(
            artifact_id=f"{subject_id}-authorization",
            media_type="application/vnd.cas-harness.worker-authorization+json",
            body=body,
        )

    return service.issue_with_builder(
        tenant_id=tenant_id,
        subject_id=subject_id,
        authorized_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        authorization_request_sha256=request_digest,
        authorization_builder=build_authorization,
    )


def _consume(
    service: DurableProspectiveRunLifecycle,
    nonce: str,
    *,
    tenant_id: str = "tenant-a",
    subject_id: str = "worker-auth-001",
    operation_id: str = "consume-001",
    worker_id: str = "worker-001",
):
    return service.consume_authorization(
        tenant_id=tenant_id,
        subject_id=subject_id,
        run_nonce=nonce,
        operation_id=operation_id,
        worker_id=worker_id,
        consumption_artifact=_artifact(f"{operation_id}-consumption"),
        started_at=NOW + timedelta(minutes=1),
    )


def _advance_to_outcome_access(
    service: DurableProspectiveRunLifecycle,
    *,
    subject_id: str = "worker-auth-001",
) -> ArtifactBinding:
    issuance = _issue(service, subject_id=subject_id)
    assert issuance.run_nonce is not None
    _consume(service, issuance.run_nonce, subject_id=subject_id)
    terminal_artifact = _artifact(f"{subject_id}-terminal-success")
    service.record_terminal(
        tenant_id="tenant-a",
        subject_id=subject_id,
        operation_id=f"{subject_id}-terminal",
        terminal_status=SUCCESS,
        terminal_artifact=terminal_artifact,
        terminal_at=NOW + timedelta(minutes=2),
    )
    service.record_outcome_access(
        tenant_id="tenant-a",
        subject_id=subject_id,
        operation_id=f"{subject_id}-outcome",
        terminal_artifact=terminal_artifact,
        outcome_access_artifact=_artifact(f"{subject_id}-outcome-access"),
        accessed_at=NOW + timedelta(minutes=3),
    )
    return terminal_artifact


def _stored_payload_text(store, tenant_id: str) -> str:
    rows = []
    for kind in (
        LIFECYCLE_KIND,
        SUBJECT_RESERVATION_KIND,
        NONCE_RESERVATION_KIND,
        AUTHORIZATION_FINALIZATION_KIND,
        OUTCOME_ACCESS_RESERVATION_KIND,
        EVENT_KIND,
    ):
        rows.extend(dict(record.payload) for record in store.list(tenant_id, kind))
    return json.dumps(rows, sort_keys=True)


class _FailOnceLifecycleIndexUpdateStore(InMemoryStateStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_lifecycle_update = False

    def put(self, record: LedgerRecord, *, expected_version: int) -> LedgerRecord:
        if (
            self.fail_next_lifecycle_update
            and record.kind == LIFECYCLE_KIND
            and expected_version > 0
        ):
            self.fail_next_lifecycle_update = False
            raise StateStoreError("synthetic crash between event and index writes")
        return super().put(record, expected_version=expected_version)


def test_server_nonce_is_returned_once_and_only_digest_is_persisted() -> None:
    store = InMemoryStateStore()
    service = _service(store)

    first = _issue(service)
    expected_nonce = base64.urlsafe_b64encode(b"R" * 32).rstrip(b"=").decode()
    assert first.issued_now is True
    assert first.run_nonce == expected_nonce
    assert first.lifecycle.state == AUTHORIZED
    assert first.lifecycle.run_nonce_sha256 == hashlib.sha256(b"R" * 32).hexdigest()
    assert (
        first.lifecycle.authorization_request_sha256
        == _authorization_request_digest("worker-auth-001")
    )
    assert first.lifecycle.authority["criteria_status"] == "OPEN"
    assert first.lifecycle.authority["execution_authentication"] == "NOT_ESTABLISHED"
    assert first.lifecycle.authority["trusted_time"] == "NOT_ESTABLISHED"
    assert first.lifecycle.authority["worm_authority"] == "NOT_ESTABLISHED"
    assert first.lifecycle.authority["independent_authority"] == "NOT_ESTABLISHED"
    assert first.lifecycle.authority["license_status"] == "NOT LICENSED"
    assert first.lifecycle.authority["disclosure_status"] == "HELD"
    assert (
        first.lifecycle.backend_durability_profile["profile"]
        == "PROCESS_LOCAL_NON_DURABLE"
    )

    retry = _issue(service)
    assert retry.issued_now is False
    assert retry.run_nonce is None
    assert retry.lifecycle == first.lifecycle

    stored = _stored_payload_text(store, "tenant-a")
    assert expected_nonce not in stored
    assert '"run_nonce"' not in stored
    assert "lease_token" not in stored
    assert "raw_nonce" not in stored
    assert len(store.list("tenant-a", SUBJECT_RESERVATION_KIND)) == 1
    assert len(store.list("tenant-a", NONCE_RESERVATION_KIND)) == 1
    assert len(store.list("tenant-a", AUTHORIZATION_FINALIZATION_KIND)) == 1
    assert len(store.list("tenant-a", EVENT_KIND)) == 1
    assert all(
        row.version == 1
        for kind in (
            SUBJECT_RESERVATION_KIND,
            NONCE_RESERVATION_KIND,
            AUTHORIZATION_FINALIZATION_KIND,
            EVENT_KIND,
        )
        for row in store.list("tenant-a", kind)
    )

    report = service.reconcile(tenant_id="tenant-a")
    assert report.has_registered_runs is True
    assert report.structurally_valid is True
    assert report.all_runs_reporting_disposed is False
    assert report.state_counts == {AUTHORIZED: 1}
    assert report.criteria_status == "OPEN"
    assert report.license_status == "NOT LICENSED"
    assert report.disclosure_status == "HELD"
    store.close()


def test_subject_reservation_is_create_only_and_conflicting_retry_fails() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    _issue(service)

    with pytest.raises(RunLifecycleConflict, match="different authorization facts"):
        service.issue_with_builder(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            authorized_at=NOW,
            expires_at=NOW + timedelta(hours=2),
            authorization_request_sha256=_authorization_request_digest(
                "worker-auth-001"
            ),
            authorization_builder=lambda _nonce: _artifact(
                "different-authorization"
            ),
        )
    subject = store.list("tenant-a", SUBJECT_RESERVATION_KIND)
    assert len(subject) == 1
    assert subject[0].version == 1
    store.close()


def test_different_authorization_request_digest_cannot_alias_exact_retry() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    first = _issue(service)
    builder_called = False

    def conflicting_builder(_run_nonce: str) -> ArtifactBinding:
        nonlocal builder_called
        builder_called = True
        return _artifact("conflicting-authorization")

    with pytest.raises(RunLifecycleConflict, match="different authorization facts"):
        service.issue_with_builder(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            authorized_at=NOW,
            expires_at=NOW + timedelta(hours=1),
            authorization_request_sha256=_authorization_request_digest(
                "worker-auth-001", variant="different-execution-scope"
            ),
            authorization_builder=conflicting_builder,
        )
    assert builder_called is False
    assert service.get_lifecycle(
        tenant_id="tenant-a", subject_id="worker-auth-001"
    ) == first.lifecycle
    store.close()


def test_builder_failure_is_quarantined_without_reissuing_or_leaking_nonce() -> None:
    store = InMemoryStateStore()
    service = _service(store, nonce=b"Q" * 32)
    calls: list[str] = []

    def fail_builder(run_nonce: str) -> ArtifactBinding:
        calls.append(run_nonce)
        raise RuntimeError("synthetic strict-loader failure")

    with pytest.raises(RunLifecycleBuilderError, match="quarantined"):
        service.issue_with_builder(
            tenant_id="tenant-a",
            subject_id="quarantined-auth",
            authorized_at=NOW,
            expires_at=NOW + timedelta(hours=1),
            authorization_request_sha256=_authorization_request_digest(
                "quarantined-auth"
            ),
            authorization_builder=fail_builder,
        )
    assert len(calls) == 1
    raw_nonce = calls[0]
    assert len(store.list("tenant-a", SUBJECT_RESERVATION_KIND)) == 1
    assert len(store.list("tenant-a", NONCE_RESERVATION_KIND)) == 1
    assert not store.list("tenant-a", AUTHORIZATION_FINALIZATION_KIND)
    assert not store.list("tenant-a", LIFECYCLE_KIND)
    assert raw_nonce not in _stored_payload_text(store, "tenant-a")

    retry_called = False

    def retry_builder(_run_nonce: str) -> ArtifactBinding:
        nonlocal retry_called
        retry_called = True
        return _artifact("must-not-build")

    with pytest.raises(RunLifecycleQuarantined, match="unrecoverable"):
        service.issue_with_builder(
            tenant_id="tenant-a",
            subject_id="quarantined-auth",
            authorized_at=NOW,
            expires_at=NOW + timedelta(hours=1),
            authorization_request_sha256=_authorization_request_digest(
                "quarantined-auth"
            ),
            authorization_builder=retry_builder,
        )
    assert retry_called is False
    report = service.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is False
    assert {issue.code for issue in report.issues} >= {
        "ORPHAN_SUBJECT_RESERVATION",
        "ORPHAN_NONCE_RESERVATION",
    }
    store.close()


def test_success_path_hash_binds_every_artifact_and_exact_retries_converge() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    issuance = _issue(service)
    assert issuance.run_nonce is not None

    running = _consume(service, issuance.run_nonce)
    assert running.lifecycle.state == RUNNING
    assert running.idempotent_replay is False
    running_retry = _consume(service, issuance.run_nonce)
    assert running_retry.idempotent_replay is True
    assert running_retry.event_sha256 == running.event_sha256

    with pytest.raises(RunLifecycleConflict, match="different immutable facts"):
        service.consume_authorization(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            run_nonce=issuance.run_nonce,
            operation_id="consume-001",
            worker_id="different-worker",
            consumption_artifact=_artifact("different-consumption"),
            started_at=NOW + timedelta(minutes=1),
        )

    terminal_artifact = _artifact("terminal-success")
    terminal = service.record_terminal(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="terminal-001",
        terminal_status=SUCCESS,
        terminal_artifact=terminal_artifact,
        terminal_at=NOW + timedelta(minutes=2),
    )
    assert terminal.lifecycle.state == SUCCESS
    outcome_artifact = _artifact("outcome-access")
    reservation = service.reserve_outcome_access(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="outcome-001",
        requested_at=NOW + timedelta(minutes=3),
        terminal_artifact=terminal_artifact,
    )
    reservation_retry = service.reserve_outcome_access(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="outcome-001",
        requested_at=NOW + timedelta(minutes=3),
        terminal_artifact=terminal_artifact,
    )
    assert reservation_retry == reservation
    assert reservation.accessed_at == "2026-08-06T16:03:00.000000Z"
    assert reservation.clock_observation == {
        "observed_at": "2026-08-06T16:03:00.000000Z",
        "source": "DIRECT_REGISTRY_CALLER_TIME",
        "assurance": "CALLER_DECLARED_TIME_NOT_TRUSTED",
    }
    pending = service.reconcile(tenant_id="tenant-a")
    assert "PENDING_OUTCOME_ACCESS_FINALIZATION" in {
        issue.code for issue in pending.issues
    }
    with pytest.raises(RunLifecycleConflict, match="conflicts"):
        service.reserve_outcome_access(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="outcome-001",
            requested_at=NOW + timedelta(minutes=4),
            terminal_artifact=terminal_artifact,
        )
    outcome = service.finalize_outcome_access(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        reservation_id=reservation.reservation_id,
        outcome_access_artifact=outcome_artifact,
    )
    assert outcome.lifecycle.state == OUTCOME_ACCESSED
    packet_artifact = _artifact("evidence-packet-v2")
    reporting = service.reserve_reporting_disposition(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="packet-001",
        disposition="PACKET",
        reason_code=None,
        request_sha256="d" * 64,
        dependency_binding_sha256="e" * 64,
        planned_artifact=packet_artifact,
        observed_at=NOW + timedelta(minutes=4),
    )
    packet = service.record_packet(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="packet-001",
        packet_artifact=packet_artifact,
        recorded_at=NOW + timedelta(minutes=4),
        reporting_reservation_id=reporting.reservation_id,
    )
    assert packet.lifecycle.state == PACKET_RECORDED

    packet_retry = service.record_packet(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="packet-001",
        packet_artifact=packet_artifact,
        recorded_at=NOW + timedelta(minutes=4),
        reporting_reservation_id=reporting.reservation_id,
    )
    assert packet_retry.idempotent_replay is True
    assert packet_retry.event_sha256 == packet.event_sha256
    with pytest.raises(RunLifecycleConflict, match="durable reservation"):
        service.record_nonreporting(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="nonreporting-conflict",
            nonreporting_artifact=_artifact("nonreporting-conflict"),
            reason_code="PACKET_ALREADY_RECORDED",
            recorded_at=NOW + timedelta(minutes=5),
            reporting_reservation_id=reporting.reservation_id,
        )

    events = service.list_events(tenant_id="tenant-a", subject_id="worker-auth-001")
    assert len(events) == 5
    assert events[2]["details"]["terminal_artifact"] == terminal_artifact.as_dict()
    assert events[3]["details"]["outcome_access_artifact"] == outcome_artifact.as_dict()
    assert events[4]["details"]["packet_artifact"] == packet_artifact.as_dict()
    for index, event in enumerate(events):
        assert event["sequence"] == index
        assert len(event["event_sha256"]) == 64
        if index:
            assert event["previous_event_sha256"] == events[index - 1]["event_sha256"]

    report = service.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is True
    assert report.all_runs_reporting_disposed is True
    assert report.state_counts == {PACKET_RECORDED: 1}
    assert report.event_count == 5
    store.close()


def test_consume_idempotent_replay_still_requires_the_exact_nonce() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    issuance = _issue(service)
    assert issuance.run_nonce is not None
    _consume(service, issuance.run_nonce)
    wrong = base64.urlsafe_b64encode(b"W" * 32).rstrip(b"=").decode()

    with pytest.raises(RunLifecycleConflict, match="does not match"):
        _consume(service, wrong)
    assert service.get_lifecycle(
        tenant_id="tenant-a", subject_id="worker-auth-001"
    ).state == RUNNING
    assert len(
        service.list_events(
            tenant_id="tenant-a", subject_id="worker-auth-001"
        )
    ) == 2
    store.close()


def test_exact_retry_repairs_event_written_before_lifecycle_index() -> None:
    store = _FailOnceLifecycleIndexUpdateStore()
    service = _service(store)
    issuance = _issue(service)
    assert issuance.run_nonce is not None
    store.fail_next_lifecycle_update = True

    with pytest.raises(RunLifecyclePersistenceError, match="synthetic crash"):
        _consume(service, issuance.run_nonce)
    raw_lifecycle = store.get("tenant-a", LIFECYCLE_KIND, issuance.lifecycle.run_id)
    assert raw_lifecycle is not None
    assert raw_lifecycle.payload["current_state"] == AUTHORIZED
    assert len(store.list("tenant-a", EVENT_KIND)) == 2
    interrupted = service.reconcile(tenant_id="tenant-a")
    assert interrupted.structurally_valid is False
    assert "event/index divergence" in interrupted.issues[0].detail

    repaired_read = service.get_lifecycle(
        tenant_id="tenant-a", subject_id="worker-auth-001"
    )
    assert repaired_read is not None
    assert repaired_read.state == RUNNING
    assert repaired_read.event_count == 2

    repaired = _consume(service, issuance.run_nonce)
    assert repaired.idempotent_replay is True
    assert repaired.lifecycle.state == RUNNING
    assert repaired.lifecycle.event_count == 2
    assert service.reconcile(tenant_id="tenant-a").structurally_valid is True
    store.close()


def test_verified_read_refuses_invalid_pending_successor_without_indexing() -> None:
    store = _FailOnceLifecycleIndexUpdateStore()
    service = _service(store)
    issuance = _issue(service)
    assert issuance.run_nonce is not None
    store.fail_next_lifecycle_update = True

    with pytest.raises(RunLifecyclePersistenceError, match="synthetic crash"):
        _consume(service, issuance.run_nonce)
    pending = next(
        event
        for event in store.list("tenant-a", EVENT_KIND)
        if event.payload.get("sequence") == 1
    )
    tampered_payload = dict(pending.payload)
    tampered_payload["event_sha256"] = "0" * 64
    store.put(
        pending.with_payload(tampered_payload),
        expected_version=pending.version,
    )

    with pytest.raises(RunLifecyclePersistenceError, match="digest does not verify"):
        service.get_lifecycle(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
        )
    raw_lifecycle = store.get(
        "tenant-a",
        LIFECYCLE_KIND,
        issuance.lifecycle.run_id,
    )
    assert raw_lifecycle is not None
    assert raw_lifecycle.payload["current_state"] == AUTHORIZED
    assert raw_lifecycle.payload["event_count"] == 1
    store.close()


def test_verified_read_refuses_divergent_pending_successors_without_indexing() -> None:
    store = _FailOnceLifecycleIndexUpdateStore()
    service = _service(store)
    issuance = _issue(service)
    assert issuance.run_nonce is not None
    store.fail_next_lifecycle_update = True

    with pytest.raises(RunLifecyclePersistenceError, match="synthetic crash"):
        _consume(service, issuance.run_nonce)
    pending = next(
        event
        for event in store.list("tenant-a", EVENT_KIND)
        if event.payload.get("sequence") == 1
    )
    divergent_payload = dict(pending.payload)
    divergent_payload["sequence"] = 2
    store.put(
        LedgerRecord.new(
            tenant_id="tenant-a",
            kind=EVENT_KIND,
            record_id=f"{pending.record_id}-divergent",
            payload=divergent_payload,
            parent_ids=pending.parent_ids,
            source="adversarial-test",
            trace_id=pending.trace_id,
        ),
        expected_version=0,
    )

    with pytest.raises(
        RunLifecyclePersistenceError,
        match="pending event/index divergence",
    ):
        service.get_lifecycle(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
        )
    raw_lifecycle = store.get(
        "tenant-a",
        LIFECYCLE_KIND,
        issuance.lifecycle.run_id,
    )
    assert raw_lifecycle is not None
    assert raw_lifecycle.payload["current_state"] == AUTHORIZED
    assert raw_lifecycle.payload["event_count"] == 1
    store.close()


@pytest.mark.parametrize(
    ("terminal_status", "requires_running"),
    [
        (SUCCESS, True),
        (FAILURE, True),
        (INDETERMINATE, True),
        (REJECTED, False),
        (EXPIRED, False),
    ],
)
def test_every_terminal_disposition_can_be_exhaustively_nonreported(
    terminal_status: str,
    requires_running: bool,
) -> None:
    store = InMemoryStateStore()
    subject_id = f"auth-{terminal_status.lower()}"
    service = _service(store, nonce=terminal_status.encode().ljust(32, b"_"))
    issuance = _issue(service, subject_id=subject_id)
    assert issuance.run_nonce is not None
    if requires_running:
        _consume(service, issuance.run_nonce, subject_id=subject_id)

    terminal_artifact = _artifact(f"terminal-{terminal_status.lower()}")
    terminal_at = (
        NOW + timedelta(hours=1, minutes=1)
        if terminal_status == EXPIRED
        else NOW + timedelta(minutes=2)
    )
    terminal = service.record_terminal(
        tenant_id="tenant-a",
        subject_id=subject_id,
        operation_id=f"terminal-{terminal_status.lower()}",
        terminal_status=terminal_status,
        terminal_artifact=terminal_artifact,
        terminal_at=terminal_at,
    )
    assert terminal.lifecycle.state == terminal_status
    if terminal_status in {SUCCESS, FAILURE}:
        service.record_outcome_access(
            tenant_id="tenant-a",
            subject_id=subject_id,
            operation_id=f"outcome-{terminal_status.lower()}",
            terminal_artifact=terminal_artifact,
            outcome_access_artifact=_artifact(f"outcome-{terminal_status.lower()}"),
            accessed_at=NOW + timedelta(minutes=3),
        )
    else:
        with pytest.raises(
            RunLifecycleConflict,
            match="strict completed or failed execution receipt",
        ):
            service.record_outcome_access(
                tenant_id="tenant-a",
                subject_id=subject_id,
                operation_id=f"fabricated-outcome-{terminal_status.lower()}",
                terminal_artifact=terminal_artifact,
                outcome_access_artifact=_artifact(
                    f"fabricated-outcome-{terminal_status.lower()}"
                ),
                accessed_at=terminal_at + timedelta(minutes=1),
            )
    nonreporting_artifact = _artifact(f"nonreporting-{terminal_status.lower()}")
    nonreporting_at = terminal_at + timedelta(minutes=2)
    reporting = service.reserve_reporting_disposition(
        tenant_id="tenant-a",
        subject_id=subject_id,
        operation_id=f"nonreporting-{terminal_status.lower()}",
        disposition="NONREPORTING",
        reason_code=f"DECLARED_{terminal_status}",
        request_sha256="d" * 64,
        dependency_binding_sha256="e" * 64,
        planned_artifact=nonreporting_artifact,
        observed_at=nonreporting_at,
    )
    nonreporting = service.record_nonreporting(
        tenant_id="tenant-a",
        subject_id=subject_id,
        operation_id=f"nonreporting-{terminal_status.lower()}",
        nonreporting_artifact=nonreporting_artifact,
        reason_code=f"DECLARED_{terminal_status}",
        recorded_at=nonreporting_at,
        reporting_reservation_id=reporting.reservation_id,
    )
    assert nonreporting.lifecycle.state == NONREPORTING_RECORDED
    report = service.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is True
    assert report.all_runs_reporting_disposed is True
    assert report.state_counts == {NONREPORTING_RECORDED: 1}
    store.close()


def test_wrong_or_expired_nonce_never_consumes_authorization() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    issuance = _issue(service)
    assert issuance.run_nonce is not None
    wrong = base64.urlsafe_b64encode(b"W" * 32).rstrip(b"=").decode()

    with pytest.raises(RunLifecycleConflict, match="does not match"):
        _consume(service, wrong)
    with pytest.raises(RunLifecycleExpired):
        service.consume_authorization(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            run_nonce=issuance.run_nonce,
            operation_id="consume-expired",
            worker_id="worker-001",
            consumption_artifact=_artifact("expired-consumption"),
            started_at=NOW + timedelta(hours=1),
        )
    assert service.get_lifecycle(
        tenant_id="tenant-a", subject_id="worker-auth-001"
    ).state == AUTHORIZED
    expired = service.record_terminal(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="terminal-expired",
        terminal_status=EXPIRED,
        terminal_artifact=_artifact("expiry-decision"),
        terminal_at=NOW + timedelta(hours=1),
    )
    assert expired.lifecycle.state == EXPIRED
    store.close()


def test_tenant_scope_fails_closed_and_same_subject_id_is_independent() -> None:
    store = InMemoryStateStore()
    service_a = _service(store, nonce=b"A" * 32)
    issuance_a = _issue(service_a, tenant_id="tenant-a")
    assert issuance_a.run_nonce is not None

    assert service_a.get_lifecycle(
        tenant_id="tenant-b", subject_id="worker-auth-001"
    ) is None
    with pytest.raises(RunLifecycleNotFound, match="not found"):
        _consume(
            service_a,
            issuance_a.run_nonce,
            tenant_id="tenant-b",
        )
    report_b = service_a.reconcile(tenant_id="tenant-b")
    assert report_b.has_registered_runs is False
    assert report_b.lifecycle_count == 0
    assert report_b.event_count == 0
    assert report_b.issues == ()
    assert report_b.structurally_valid is True
    assert report_b.all_runs_reporting_disposed is False

    service_b = _service(store, nonce=b"B" * 32)
    issuance_b = _issue(service_b, tenant_id="tenant-b")
    assert issuance_b.run_nonce is not None
    assert issuance_b.lifecycle.run_id == issuance_a.lifecycle.run_id
    assert issuance_b.lifecycle.run_nonce_sha256 != issuance_a.lifecycle.run_nonce_sha256
    assert service_a.reconcile(tenant_id="tenant-a").lifecycle_count == 1
    assert service_b.reconcile(tenant_id="tenant-b").lifecycle_count == 1
    store.close()


def test_sqlite_restart_preserves_digest_chain_without_promoting_backend_claims(
    tmp_path: Path,
) -> None:
    path = tmp_path / "prospective-runs.db"
    first_store = SqliteStateStore(path)
    first_service = _service(first_store, nonce=b"S" * 32)
    issuance = _issue(first_service)
    assert issuance.run_nonce is not None
    assert (
        issuance.lifecycle.backend_durability_profile["profile"]
        == "SQLITE_SINGLE_HOST_DURABLE_NOT_REPLICATED"
    )
    assert (
        issuance.lifecycle.backend_durability_profile["host_loss_survival"]
        == "UNAVAILABLE"
    )
    assert (
        issuance.lifecycle.backend_durability_profile[
            "atomic_compare_and_swap_scope"
        ]
        == "SAME_HOST_SQLITE_DATABASE_FILE"
    )
    first_store.close()

    restarted_store = SqliteStateStore(path)
    restarted = _service(restarted_store, nonce=b"unused".ljust(32, b"_"))
    running = _consume(restarted, issuance.run_nonce)
    assert running.lifecycle.state == RUNNING
    restart_terminal_artifact = _artifact("failure-after-restart")
    restarted.record_terminal(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="terminal-after-restart",
        terminal_status=FAILURE,
        terminal_artifact=restart_terminal_artifact,
        terminal_at=NOW + timedelta(minutes=2),
    )
    restarted.record_outcome_access(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="outcome-after-restart",
        terminal_artifact=restart_terminal_artifact,
        outcome_access_artifact=_artifact("outcome-after-restart"),
        accessed_at=NOW + timedelta(minutes=3),
    )
    restart_nonreporting_artifact = _artifact("nonreporting-after-restart")
    reporting = restarted.reserve_reporting_disposition(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="nonreporting-after-restart",
        disposition="NONREPORTING",
        reason_code="DECLARED_FAILURE",
        request_sha256="d" * 64,
        dependency_binding_sha256="e" * 64,
        planned_artifact=restart_nonreporting_artifact,
        observed_at=NOW + timedelta(minutes=4),
    )
    restarted.record_nonreporting(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="nonreporting-after-restart",
        nonreporting_artifact=restart_nonreporting_artifact,
        reason_code="DECLARED_FAILURE",
        recorded_at=NOW + timedelta(minutes=4),
        reporting_reservation_id=reporting.reservation_id,
    )
    restarted_store.close()

    verifier_store = SqliteStateStore(path)
    verifier = _service(verifier_store, nonce=b"unused".ljust(32, b"_"))
    report = verifier.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is True
    assert report.all_runs_reporting_disposed is True
    assert report.state_counts == {NONREPORTING_RECORDED: 1}
    assert report.execution_authentication == "NOT_ESTABLISHED"
    assert report.trusted_time == "NOT_ESTABLISHED"
    assert report.worm_authority == "NOT_ESTABLISHED"
    assert report.independent_authority == "NOT_ESTABLISHED"
    assert report.license_status == "NOT LICENSED"
    verifier_store.close()


def test_concurrent_sqlite_consumption_has_one_winner_and_exact_retries_converge(
    tmp_path: Path,
) -> None:
    # One SQLite connection is also covered; the separate-connection case below
    # proves same-file arbitration without claiming multi-host authority.
    store = SqliteStateStore(tmp_path / "concurrent-runs.db")
    service = _service(store, nonce=b"C" * 32)
    issuance = _issue(service)
    assert issuance.run_nonce is not None
    barrier = threading.Barrier(8)

    def contend(index: int):
        barrier.wait()
        operation_id = f"consume-{index}"
        try:
            result = _consume(
                service,
                issuance.run_nonce,
                operation_id=operation_id,
                worker_id=f"worker-{index}",
            )
            return ("won", index, result)
        except RunLifecycleConflict as exc:
            return ("lost", index, str(exc))

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(contend, range(8)))
    winners = [outcome for outcome in outcomes if outcome[0] == "won"]
    losers = [outcome for outcome in outcomes if outcome[0] == "lost"]
    assert len(winners) == 1
    assert len(losers) == 7
    winner_index = winners[0][1]
    assert service.get_lifecycle(
        tenant_id="tenant-a", subject_id="worker-auth-001"
    ).state == RUNNING
    assert len(service.list_events(tenant_id="tenant-a", subject_id="worker-auth-001")) == 2

    def exact_retry(_index: int):
        return _consume(
            service,
            issuance.run_nonce,
            operation_id=f"consume-{winner_index}",
            worker_id=f"worker-{winner_index}",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        retries = list(pool.map(exact_retry, range(16)))
    assert all(result.idempotent_replay for result in retries)
    assert len({result.event_sha256 for result in retries}) == 1
    assert len(service.list_events(tenant_id="tenant-a", subject_id="worker-auth-001")) == 2
    store.close()


def test_reporting_reservation_blocks_alternate_action_and_exposes_pending_state() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    _advance_to_outcome_access(service)
    recorded_at = NOW + timedelta(minutes=4)
    reservation = service.reserve_reporting_disposition(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="packet-fixed-operation",
        disposition="PACKET",
        reason_code=None,
        request_sha256="1" * 64,
        dependency_binding_sha256="2" * 64,
        planned_artifact=_artifact("reserved-packet"),
        observed_at=recorded_at,
    )
    assert reservation.disposition == "PACKET"
    assert reservation.recorded_at == "2026-08-06T16:04:00.000000Z"
    assert reservation.clock_observation == {
        "observed_at": "2026-08-06T16:04:00.000000Z",
        "source": "DIRECT_REGISTRY_CALLER_TIME",
        "assurance": "CALLER_DECLARED_TIME_NOT_TRUSTED",
    }
    with pytest.raises(RunLifecycleConflict, match="different exact facts"):
        service.reserve_reporting_disposition(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="packet-fixed-operation",
            disposition="PACKET",
            reason_code=None,
            request_sha256="1" * 64,
            dependency_binding_sha256="2" * 64,
            planned_artifact=_artifact("different-planned-packet"),
            observed_at=recorded_at,
        )
    pending = service.reconcile(tenant_id="tenant-a")
    assert pending.reporting_disposition_reservation_count == 1
    assert pending.structurally_valid is False
    assert "PENDING_REPORTING_DISPOSITION_FINALIZATION" in {
        issue.code for issue in pending.issues
    }

    with pytest.raises(RunLifecycleConflict, match="different exact facts"):
        service.reserve_reporting_disposition(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="nonreporting-fixed-operation",
            disposition="NONREPORTING",
            reason_code="SUCCESS_NO_PACKET_RECORDED",
            request_sha256="3" * 64,
            dependency_binding_sha256="4" * 64,
            planned_artifact=_artifact("alternate-nonreporting"),
            observed_at=recorded_at + timedelta(seconds=1),
        )
    assert len(
        store.list("tenant-a", REPORTING_DISPOSITION_RESERVATION_KIND)
    ) == 1

    with pytest.raises(RunLifecycleConflict, match="durable reservation"):
        service.record_packet(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="packet-fixed-operation",
            packet_artifact=_artifact("different-unreserved-packet"),
            recorded_at=recorded_at,
            reporting_reservation_id=reservation.reservation_id,
        )
    assert service.get_lifecycle(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
    ).state == OUTCOME_ACCESSED

    mutation = service.record_packet(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="packet-fixed-operation",
        packet_artifact=_artifact("reserved-packet"),
        recorded_at=recorded_at,
        reporting_reservation_id=reservation.reservation_id,
    )
    assert mutation.lifecycle.state == PACKET_RECORDED
    report = service.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is True
    assert report.all_runs_reporting_disposed is True
    store.close()


def test_reporting_reservation_binds_nonreporting_reason_and_forbids_packet_reason() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    _advance_to_outcome_access(service)
    recorded_at = NOW + timedelta(minutes=4)

    with pytest.raises(
        RunLifecycleValidationError,
        match="PACKET reporting reservations must not declare a reason_code",
    ):
        service.reserve_reporting_disposition(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="invalid-packet-reason-operation",
            disposition="PACKET",
            reason_code="PACKET_DOES_NOT_HAVE_A_REASON",
            request_sha256="1" * 64,
            dependency_binding_sha256="2" * 64,
            planned_artifact=_artifact("invalid-packet-reason"),
            observed_at=recorded_at,
        )
    with pytest.raises(RunLifecycleValidationError, match="reason_code"):
        service.reserve_reporting_disposition(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="missing-nonreporting-reason-operation",
            disposition="NONREPORTING",
            reason_code=None,
            request_sha256="3" * 64,
            dependency_binding_sha256="4" * 64,
            planned_artifact=_artifact("missing-nonreporting-reason"),
            observed_at=recorded_at,
        )

    artifact = _artifact("reason-bound-nonreporting")
    reservation = service.reserve_reporting_disposition(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="reason-bound-nonreporting-operation",
        disposition="NONREPORTING",
        reason_code="SUCCESS_NO_PACKET_RECORDED",
        request_sha256="5" * 64,
        dependency_binding_sha256="6" * 64,
        planned_artifact=artifact,
        observed_at=recorded_at,
    )
    assert reservation.reason_code == "SUCCESS_NO_PACKET_RECORDED"

    with pytest.raises(RunLifecycleConflict, match="durable reservation"):
        service.record_nonreporting(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id=reservation.operation_id,
            nonreporting_artifact=artifact,
            reason_code="DIFFERENT_UNRESERVED_REASON",
            recorded_at=recorded_at,
            reporting_reservation_id=reservation.reservation_id,
        )
    assert service.get_lifecycle(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
    ).state == OUTCOME_ACCESSED

    service.record_nonreporting(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id=reservation.operation_id,
        nonreporting_artifact=artifact,
        reason_code="SUCCESS_NO_PACKET_RECORDED",
        recorded_at=recorded_at,
        reporting_reservation_id=reservation.reservation_id,
    )
    report = service.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is True
    assert report.all_runs_reporting_disposed is True
    store.close()


def test_route_owned_outcome_reservation_concurrent_clock_reads_converge(
    tmp_path: Path,
) -> None:
    store = SqliteStateStore(tmp_path / "outcome-reservation-race.db")
    service = _service(store, nonce=b"O" * 32)
    issuance = _issue(service)
    assert issuance.run_nonce is not None
    _consume(service, issuance.run_nonce)
    terminal = _artifact("outcome-race-terminal")
    service.record_terminal(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="outcome-race-terminal-operation",
        terminal_status=SUCCESS,
        terminal_artifact=terminal,
        terminal_at=NOW + timedelta(minutes=2),
    )
    barrier = threading.Barrier(8)

    def reserve(index: int):
        barrier.wait()
        return service.reserve_outcome_access(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="fixed-http-outcome-operation",
            requested_at=NOW + timedelta(minutes=3, microseconds=index),
            terminal_artifact=terminal,
            request_sha256="b" * 64,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        reservations = list(pool.map(reserve, range(8)))
    assert len({item.reservation_id for item in reservations}) == 1
    assert len({item.accessed_at for item in reservations}) == 1
    assert len(store.list("tenant-a", OUTCOME_ACCESS_RESERVATION_KIND)) == 1
    winner = reservations[0]
    service.finalize_outcome_access(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        reservation_id=winner.reservation_id,
        outcome_access_artifact=_artifact("outcome-race-access"),
    )
    assert service.reconcile(tenant_id="tenant-a").structurally_valid is True
    store.close()


def test_backward_clock_cannot_poison_outcome_or_reporting_reservation() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    issuance = _issue(service)
    assert issuance.run_nonce is not None
    _consume(service, issuance.run_nonce)
    terminal = _artifact("causality-terminal")
    service.record_terminal(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="causality-terminal-operation",
        terminal_status=SUCCESS,
        terminal_artifact=terminal,
        terminal_at=NOW + timedelta(minutes=2),
    )
    with pytest.raises(RunLifecycleConflict, match="cannot precede"):
        service.reserve_outcome_access(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="causality-outcome-operation",
            requested_at=NOW + timedelta(minutes=1),
            terminal_artifact=terminal,
            request_sha256="c" * 64,
        )
    assert not store.list("tenant-a", OUTCOME_ACCESS_RESERVATION_KIND)

    service.record_outcome_access(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="causality-outcome-operation",
        terminal_artifact=terminal,
        outcome_access_artifact=_artifact("causality-outcome"),
        accessed_at=NOW + timedelta(minutes=3),
        request_sha256="c" * 64,
    )
    with pytest.raises(RunLifecycleConflict, match="cannot precede"):
        service.reserve_reporting_disposition(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="causality-reporting-operation",
            disposition="PACKET",
            reason_code=None,
            request_sha256="d" * 64,
            dependency_binding_sha256="e" * 64,
            planned_artifact=_artifact("causality-packet"),
            observed_at=NOW + timedelta(minutes=2),
        )
    assert not store.list(
        "tenant-a",
        REPORTING_DISPOSITION_RESERVATION_KIND,
    )
    store.close()


def test_backward_clock_cannot_create_running_or_terminal_transition() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    issuance = _issue(service)
    assert issuance.run_nonce is not None

    with pytest.raises(RunLifecycleConflict, match="cannot precede"):
        service.consume_authorization(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            run_nonce=issuance.run_nonce,
            operation_id="backward-running-operation",
            worker_id="worker-001",
            consumption_artifact=_artifact("backward-running-consumption"),
            started_at=NOW - timedelta(microseconds=1),
        )
    authorized = service.get_lifecycle(
        tenant_id="tenant-a", subject_id="worker-auth-001"
    )
    assert authorized is not None
    assert authorized.state == AUTHORIZED
    assert authorized.event_count == 1
    assert len(store.list("tenant-a", EVENT_KIND)) == 1

    running = _consume(service, issuance.run_nonce)
    assert running.lifecycle.state == RUNNING
    with pytest.raises(RunLifecycleConflict, match="cannot precede"):
        service.record_terminal(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id="backward-terminal-operation",
            terminal_status=SUCCESS,
            terminal_artifact=_artifact("backward-terminal"),
            terminal_at=NOW,
        )
    still_running = service.get_lifecycle(
        tenant_id="tenant-a", subject_id="worker-auth-001"
    )
    assert still_running is not None
    assert still_running.state == RUNNING
    assert still_running.event_count == 2
    assert len(store.list("tenant-a", EVENT_KIND)) == 2
    assert service.reconcile(tenant_id="tenant-a").structurally_valid is True
    store.close()


def test_replay_rejects_rehashed_history_with_decreasing_event_time() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    issuance = _issue(service)
    assert issuance.run_nonce is not None
    _consume(service, issuance.run_nonce)

    running_event = next(
        event
        for event in store.list("tenant-a", EVENT_KIND)
        if event.payload.get("sequence") == 1
    )
    tampered = dict(running_event.payload)
    tampered["occurred_at"] = (
        NOW - timedelta(microseconds=1)
    ).isoformat(timespec="microseconds").replace("+00:00", "Z")
    tampered["operation_fingerprint_sha256"] = hashlib.sha256(
        json.dumps(
            {
                "event_type": tampered["event_type"],
                "occurred_at": tampered["occurred_at"],
                "details": tampered["details"],
                "state_after": tampered["state_after"],
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    without_hash = dict(tampered)
    without_hash.pop("event_sha256")
    tampered["event_sha256"] = hashlib.sha256(
        json.dumps(
            without_hash,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    store.put(
        running_event.with_payload(tampered),
        expected_version=running_event.version,
    )
    lifecycle = store.get("tenant-a", LIFECYCLE_KIND, issuance.lifecycle.run_id)
    assert lifecycle is not None
    lifecycle_payload = dict(lifecycle.payload)
    lifecycle_payload["head_event_sha256"] = tampered["event_sha256"]
    store.put(
        lifecycle.with_payload(lifecycle_payload),
        expected_version=lifecycle.version,
    )

    with pytest.raises(RunLifecyclePersistenceError, match="cannot precede"):
        service.list_events(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
        )
    report = service.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is False
    assert any("cannot precede" in issue.detail for issue in report.issues)
    store.close()


def test_concurrent_reporting_reservations_choose_one_action_and_exact_calls_converge(
    tmp_path: Path,
) -> None:
    store = SqliteStateStore(tmp_path / "reporting-race.db")
    service = _service(store, nonce=b"Y" * 32)
    _advance_to_outcome_access(service)
    barrier = threading.Barrier(8)

    def contend(index: int):
        disposition = "PACKET" if index % 2 == 0 else "NONREPORTING"
        operation_id = (
            "packet-fixed-operation"
            if disposition == "PACKET"
            else "nonreporting-fixed-operation"
        )
        request_sha256 = "5" * 64 if disposition == "PACKET" else "6" * 64
        dependency_sha256 = "7" * 64 if disposition == "PACKET" else "8" * 64
        barrier.wait()
        try:
            reserved = service.reserve_reporting_disposition(
                tenant_id="tenant-a",
                subject_id="worker-auth-001",
                operation_id=operation_id,
                disposition=disposition,
                reason_code=(
                    None
                    if disposition == "PACKET"
                    else "SUCCESS_NO_PACKET_RECORDED"
                ),
                request_sha256=request_sha256,
                dependency_binding_sha256=dependency_sha256,
                planned_artifact=_artifact(
                    "race-winning-packet"
                    if disposition == "PACKET"
                    else "race-winning-nonreporting"
                ),
                observed_at=NOW
                + timedelta(minutes=4, microseconds=index),
            )
            return ("reserved", disposition, reserved)
        except RunLifecycleConflict as exc:
            return ("conflict", disposition, str(exc))

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(contend, range(8)))
    winners = [row for row in outcomes if row[0] == "reserved"]
    losers = [row for row in outcomes if row[0] == "conflict"]
    assert len(winners) == 4
    assert len(losers) == 4
    winning_disposition = winners[0][1]
    assert {row[1] for row in winners} == {winning_disposition}
    assert len({row[2].recorded_at for row in winners}) == 1
    assert len(
        store.list("tenant-a", REPORTING_DISPOSITION_RESERVATION_KIND)
    ) == 1

    reservation = winners[0][2]
    recorded_at = datetime.fromisoformat(
        reservation.recorded_at.replace("Z", "+00:00")
    )
    if winning_disposition == "PACKET":
        service.record_packet(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id=reservation.operation_id,
            packet_artifact=_artifact("race-winning-packet"),
            recorded_at=recorded_at,
            reporting_reservation_id=reservation.reservation_id,
        )
    else:
        service.record_nonreporting(
            tenant_id="tenant-a",
            subject_id="worker-auth-001",
            operation_id=reservation.operation_id,
            nonreporting_artifact=_artifact("race-winning-nonreporting"),
            reason_code="SUCCESS_NO_PACKET_RECORDED",
            recorded_at=recorded_at,
            reporting_reservation_id=reservation.reservation_id,
        )
    assert service.reconcile(tenant_id="tenant-a").structurally_valid is True
    store.close()


def test_pending_reporting_reservation_survives_restart_and_exact_finalization(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reporting-restart.db"
    first_store = SqliteStateStore(path)
    first = _service(first_store, nonce=b"Z" * 32)
    _advance_to_outcome_access(first)
    reservation = first.reserve_reporting_disposition(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id="restart-nonreporting-operation",
        disposition="NONREPORTING",
        reason_code="SUCCESS_NO_PACKET_RECORDED",
        request_sha256="9" * 64,
        dependency_binding_sha256="a" * 64,
        planned_artifact=_artifact("restart-nonreporting"),
        observed_at=NOW + timedelta(minutes=4),
    )
    first_store.close()

    restarted_store = SqliteStateStore(path)
    restarted = _service(restarted_store, nonce=b"unused".ljust(32, b"_"))
    loaded = restarted.get_reporting_disposition_reservation(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
    )
    assert loaded == reservation
    pending = restarted.reconcile(tenant_id="tenant-a")
    assert pending.structurally_valid is False
    assert "PENDING_REPORTING_DISPOSITION_FINALIZATION" in {
        issue.code for issue in pending.issues
    }
    restarted.record_nonreporting(
        tenant_id="tenant-a",
        subject_id="worker-auth-001",
        operation_id=reservation.operation_id,
        nonreporting_artifact=_artifact("restart-nonreporting"),
        reason_code="SUCCESS_NO_PACKET_RECORDED",
        recorded_at=datetime.fromisoformat(
            reservation.recorded_at.replace("Z", "+00:00")
        ),
        reporting_reservation_id=reservation.reservation_id,
    )
    restarted_store.close()

    verifier_store = SqliteStateStore(path)
    verifier = _service(verifier_store, nonce=b"unused".ljust(32, b"_"))
    report = verifier.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is True
    assert report.state_counts == {NONREPORTING_RECORDED: 1}
    verifier_store.close()


def test_two_sqlite_connections_have_one_authorization_consumer(
    tmp_path: Path,
) -> None:
    path = tmp_path / "two-connection-runs.db"
    first_store = SqliteStateStore(path)
    second_store = SqliteStateStore(path)
    first = _service(first_store, nonce=b"D" * 32)
    second = _service(second_store, nonce=b"unused".ljust(32, b"_"))
    issuance = _issue(first)
    assert issuance.run_nonce is not None
    barrier = threading.Barrier(2)

    def contend(index: int):
        barrier.wait()
        service = first if index == 0 else second
        try:
            result = _consume(
                service,
                issuance.run_nonce,
                operation_id=f"two-connection-consume-{index}",
                worker_id=f"two-connection-worker-{index}",
            )
            return ("won", index, result)
        except RunLifecycleConflict as exc:
            return ("lost", index, str(exc))

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(contend, range(2)))
    winners = [outcome for outcome in outcomes if outcome[0] == "won"]
    losers = [outcome for outcome in outcomes if outcome[0] == "lost"]
    assert len(winners) == 1
    assert len(losers) == 1
    winner_index = winners[0][1]

    retry_service = second if winner_index == 0 else first
    retry = _consume(
        retry_service,
        issuance.run_nonce,
        operation_id=f"two-connection-consume-{winner_index}",
        worker_id=f"two-connection-worker-{winner_index}",
    )
    assert retry.idempotent_replay is True
    report = first.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is True
    assert report.state_counts == {RUNNING: 1}
    assert report.backend_durability_profile[
        "atomic_compare_and_swap_scope"
    ] == "SAME_HOST_SQLITE_DATABASE_FILE"
    first_store.close()
    second_store.close()


def test_reconciliation_detects_external_event_tamper_and_orphan_reservation() -> None:
    store = InMemoryStateStore()
    service = _service(store)
    _issue(service)
    event = store.list("tenant-a", EVENT_KIND)[0]
    tampered_payload = dict(event.payload)
    tampered_payload["event_type"] = "MUTATED_OUTSIDE_LIFECYCLE_SERVICE"
    store.put(event.with_payload(tampered_payload), expected_version=event.version)
    store.put(
        LedgerRecord.new(
            tenant_id="tenant-a",
            kind=SUBJECT_RESERVATION_KIND,
            record_id="orphan-subject",
            payload={
                "schema": "cas_harness_v2.run_subject_reservation.v1",
                "run_id": "missing-run",
            },
            source="adversarial-test",
        ),
        expected_version=0,
    )

    report = service.reconcile(tenant_id="tenant-a")
    assert report.structurally_valid is False
    codes = {issue.code for issue in report.issues}
    assert "LIFECYCLE_INTEGRITY_FAILURE" in codes
    assert "ORPHAN_SUBJECT_RESERVATION" in codes
    assert report.issue_count >= 2
    store.close()
