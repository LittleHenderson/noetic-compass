from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from api.services.cas_harness_audit_sessions import (
    AuditRunInProgress,
    AuditRunReconciliationRequired,
    AuditSessionPersistenceUnavailable,
    attach_runner_evidence,
    checkpoint_provider_completed,
    checkpoint_provider_evidence_persisted,
    claim_provider_run,
    claim_run_attempt,
    configure_audit_session_store,
    create_session,
    finalize_provider_run,
    get_session,
    list_sessions,
    mark_provider_request_started,
    reset_audit_sessions_for_tests,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore


PAYLOAD = {
    "model_id": "EleutherAI/pythia-160m",
    "audit_mode": "BALANCED",
    "prompt": "Audit this response.",
    "selected_modules": ["active_trace"],
}


@pytest.fixture(autouse=True)
def _reset_store_pointer():
    reset_audit_sessions_for_tests()
    yield
    reset_audit_sessions_for_tests()


def test_scoped_session_survives_sqlite_reopen(tmp_path) -> None:
    path = tmp_path / "audit-sessions.db"
    first = SqliteStateStore(path)
    configure_audit_session_store(first)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")
    first.close()

    second = SqliteStateStore(path)
    configure_audit_session_store(second)
    recovered = get_session(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert recovered is not None
    assert recovered.audit_id == created.audit_id
    assert recovered.prompt_text == "Audit this response."
    second.close()


def test_scoped_session_is_invisible_across_tenant_and_account(tmp_path) -> None:
    backend = SqliteStateStore(tmp_path / "isolation.db")
    configure_audit_session_store(backend)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")

    assert get_session(created.audit_id, tenant_id="tenant-b", account_id="acct-a") is None
    assert get_session(created.audit_id, tenant_id="tenant-a", account_id="acct-b") is None
    assert list_sessions(tenant_id="tenant-b", account_id="acct-a") == []
    assert list_sessions(tenant_id="tenant-a", account_id="acct-b") == []
    backend.close()


def test_mutation_persists_across_store_reconfiguration(tmp_path) -> None:
    path = tmp_path / "mutation.db"
    first = SqliteStateStore(path)
    configure_audit_session_store(first)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")
    attempt = claim_run_attempt(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    attached = attach_runner_evidence(
        created.audit_id,
        evidence_packet_trace_id="trace-1",
        proof_chips=[],
        message="attached",
        tenant_id="tenant-a",
        account_id="acct-a",
        run_attempt_id=attempt,
    )
    assert attached is not None and attached.status == "EVIDENCE_READY"
    first.close()

    second = SqliteStateStore(path)
    configure_audit_session_store(second)
    recovered = get_session(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert recovered is not None
    assert recovered.evidence_packet_trace_id == "trace-1"
    assert recovered.run_state is None
    second.close()


def test_missing_durable_store_fails_closed_but_dark_mode_stays_in_memory() -> None:
    with pytest.raises(AuditSessionPersistenceUnavailable):
        create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")

    dark = create_session(PAYLOAD, owner_sub="anonymous")
    assert get_session(dark.audit_id, owner_sub="anonymous") is not None


def test_two_claimers_get_one_fenced_attempt(tmp_path) -> None:
    backend = SqliteStateStore(tmp_path / "claim.db")
    configure_audit_session_store(backend)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")

    def claim():
        try:
            return claim_run_attempt(
                created.audit_id, tenant_id="tenant-a", account_id="acct-a"
            )
        except AuditRunInProgress:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _value: claim(), range(2)))
    assert results.count("blocked") == 1
    assert len([value for value in results if value != "blocked"]) == 1
    backend.close()


def test_expired_lease_can_be_reclaimed_and_stale_completion_is_rejected(tmp_path) -> None:
    backend = SqliteStateStore(tmp_path / "fence.db")
    configure_audit_session_store(backend)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")
    stale_attempt = claim_run_attempt(
        created.audit_id,
        tenant_id="tenant-a",
        account_id="acct-a",
        lease_seconds=-1,
    )
    current_attempt = claim_run_attempt(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert current_attempt != stale_attempt

    with pytest.raises(AuditRunInProgress):
        attach_runner_evidence(
            created.audit_id,
            evidence_packet_trace_id="trace-stale",
            proof_chips=[],
            message="stale",
            tenant_id="tenant-a",
            account_id="acct-a",
            run_attempt_id=stale_attempt,
        )
    current = attach_runner_evidence(
        created.audit_id,
        evidence_packet_trace_id="trace-current",
        proof_chips=[],
        message="current",
        tenant_id="tenant-a",
        account_id="acct-a",
        run_attempt_id=current_attempt,
    )
    assert current is not None
    assert current.evidence_packet_trace_id == "trace-current"
    backend.close()


def _expire_provider_lease(backend: SqliteStateStore, audit_id: str) -> None:
    ledger = backend.get("tenant-a", "cas_audit_session", audit_id)
    assert ledger is not None
    payload = dict(ledger.payload)
    payload["run_lease_until"] = "2000-01-01T00:00:00+00:00"
    backend.put(ledger.with_payload(payload), expected_version=ledger.version)


def test_claimed_provider_run_restarts_with_same_durable_idempotency_key(tmp_path) -> None:
    path = tmp_path / "provider-claimed-restart.db"
    first = SqliteStateStore(path)
    configure_audit_session_store(first)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")
    original = claim_provider_run(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert original is not None and original.phase == "CLAIMED"
    _expire_provider_lease(first, created.audit_id)
    first.close()

    second = SqliteStateStore(path)
    configure_audit_session_store(second)
    reclaimed = claim_provider_run(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert reclaimed is not None and reclaimed.phase == "CLAIMED"
    assert reclaimed.run_attempt_id != original.run_attempt_id
    assert reclaimed.provider_idempotency_key == original.provider_idempotency_key
    second.close()


def test_request_started_crash_becomes_durable_orphan_and_never_reclaims(tmp_path) -> None:
    path = tmp_path / "provider-request-started.db"
    first = SqliteStateStore(path)
    configure_audit_session_store(first)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")
    claim = claim_provider_run(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert claim is not None
    started = mark_provider_request_started(
        created.audit_id,
        tenant_id="tenant-a",
        account_id="acct-a",
        run_attempt_id=claim.run_attempt_id,
    )
    assert started is not None and started.phase == "REQUEST_STARTED"
    _expire_provider_lease(first, created.audit_id)
    first.close()

    second = SqliteStateStore(path)
    configure_audit_session_store(second)
    with pytest.raises(AuditRunReconciliationRequired, match="repeat external spend"):
        claim_provider_run(
            created.audit_id, tenant_id="tenant-a", account_id="acct-a"
        )
    orphaned = get_session(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert orphaned is not None
    assert orphaned.provider_run_phase == "ORPHANED"
    assert orphaned.provider_idempotency_key == claim.provider_idempotency_key
    assert orphaned.provider_result_checkpoint is None
    with pytest.raises(AuditRunReconciliationRequired):
        claim_provider_run(
            created.audit_id, tenant_id="tenant-a", account_id="acct-a"
        )
    second.close()


def test_expired_prejournal_inflight_attempt_is_quarantined_on_upgrade(tmp_path) -> None:
    backend = SqliteStateStore(tmp_path / "legacy-provider-upgrade.db")
    configure_audit_session_store(backend)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")
    legacy_attempt = claim_run_attempt(
        created.audit_id,
        tenant_id="tenant-a",
        account_id="acct-a",
        lease_seconds=-1,
    )
    assert legacy_attempt is not None

    with pytest.raises(AuditRunReconciliationRequired, match="legacy in-flight"):
        claim_provider_run(
            created.audit_id, tenant_id="tenant-a", account_id="acct-a"
        )
    record = get_session(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert record is not None
    assert record.provider_run_phase == "ORPHANED"
    assert record.provider_idempotency_key is None
    backend.close()


def test_provider_completed_restart_resumes_to_finalized_without_new_operation(tmp_path) -> None:
    path = tmp_path / "provider-completed-restart.db"
    first = SqliteStateStore(path)
    configure_audit_session_store(first)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")
    claim = claim_provider_run(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert claim is not None
    mark_provider_request_started(
        created.audit_id,
        tenant_id="tenant-a",
        account_id="acct-a",
        run_attempt_id=claim.run_attempt_id,
    )
    checkpoint = {
        "schema_version": "cas_harness_provider_result_checkpoint.v1",
        "runner": "live_worker",
        "trace_id": "trace-provider-restart",
        "evidence_packet": {"trace_id": "trace-provider-restart"},
        "proof_chips": [],
        "verifier_decision": None,
        "message": "checkpointed",
        "audit_scope": None,
    }
    completed = checkpoint_provider_completed(
        created.audit_id,
        tenant_id="tenant-a",
        account_id="acct-a",
        run_attempt_id=claim.run_attempt_id,
        result_checkpoint=checkpoint,
        trace_id="trace-provider-restart",
    )
    assert completed is not None and completed.phase == "PROVIDER_COMPLETED"
    _expire_provider_lease(first, created.audit_id)
    first.close()

    second = SqliteStateStore(path)
    configure_audit_session_store(second)
    resumed = claim_provider_run(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert resumed is not None and resumed.phase == "PROVIDER_COMPLETED"
    assert resumed.provider_idempotency_key == claim.provider_idempotency_key
    assert resumed.result_checkpoint == checkpoint
    checkpoint_provider_evidence_persisted(
        created.audit_id,
        tenant_id="tenant-a",
        account_id="acct-a",
        run_attempt_id=resumed.run_attempt_id,
        trace_id="trace-provider-restart",
    )
    attached = attach_runner_evidence(
        created.audit_id,
        evidence_packet_trace_id="trace-provider-restart",
        proof_chips=[],
        message="attached after restart",
        tenant_id="tenant-a",
        account_id="acct-a",
        run_attempt_id=resumed.run_attempt_id,
    )
    assert attached is not None
    second.close()

    # Crash after the evidence/session attachment but before FINALIZED. The
    # durable attempt id and EVIDENCE_PERSISTED phase are sufficient to finish
    # locally; no provider operation is reopened.
    third = SqliteStateStore(path)
    configure_audit_session_store(third)
    finalized = finalize_provider_run(
        created.audit_id,
        tenant_id="tenant-a",
        account_id="acct-a",
        run_attempt_id=resumed.run_attempt_id,
        trace_id="trace-provider-restart",
    )
    assert finalized is not None
    assert finalized.provider_run_phase == "FINALIZED"
    assert finalized.provider_result_checkpoint is None
    third.close()


def test_two_provider_claimers_allow_one_replica_only(tmp_path) -> None:
    backend = SqliteStateStore(tmp_path / "provider-concurrency.db")
    configure_audit_session_store(backend)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")

    def claim():
        try:
            result = claim_provider_run(
                created.audit_id, tenant_id="tenant-a", account_id="acct-a"
            )
            return result.provider_idempotency_key if result is not None else "missing"
        except AuditRunInProgress:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _value: claim(), range(2)))
    assert results.count("blocked") == 1
    keys = [value for value in results if value != "blocked"]
    assert len(keys) == 1 and keys[0].startswith("cas-run-")
    backend.close()


def test_provider_phase_order_fails_closed(tmp_path) -> None:
    backend = SqliteStateStore(tmp_path / "provider-order.db")
    configure_audit_session_store(backend)
    created = create_session(PAYLOAD, tenant_id="tenant-a", account_id="acct-a")
    claim = claim_provider_run(
        created.audit_id, tenant_id="tenant-a", account_id="acct-a"
    )
    assert claim is not None
    with pytest.raises(AuditRunInProgress, match="evidence cannot be persisted"):
        checkpoint_provider_evidence_persisted(
            created.audit_id,
            tenant_id="tenant-a",
            account_id="acct-a",
            run_attempt_id=claim.run_attempt_id,
            trace_id="out-of-order",
        )
    backend.close()
