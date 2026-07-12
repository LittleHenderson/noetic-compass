from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from api.services.cas_harness_audit_sessions import (
    AuditRunInProgress,
    AuditSessionPersistenceUnavailable,
    attach_runner_evidence,
    claim_run_attempt,
    configure_audit_session_store,
    create_session,
    get_session,
    list_sessions,
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
