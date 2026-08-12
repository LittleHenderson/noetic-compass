from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sqlite3
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TEST_DIR = Path(__file__).resolve().parent
for candidate in (SRC, TEST_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cas_harness_v2._strict_json import canonical_json_bytes  # noqa: E402
import cas_harness_v2.diagnostic_lifecycle as lifecycle_module  # noqa: E402
from cas_harness_v2.diagnostic_lifecycle import (  # noqa: E402
    AUTHORIZED,
    COMPLETED,
    EXPIRED,
    FAILED,
    INDETERMINATE,
    REJECTED,
    RUNNING,
    DiagnosticAttemptLifecycle,
    DiagnosticLifecycleConflict,
    DiagnosticLifecycleExpired,
    DiagnosticLifecycleIntegrityError,
    DiagnosticLifecycleNotFound,
    DiagnosticLifecyclePersistenceError,
    DiagnosticLifecycleReplayContext,
    DiagnosticLifecycleValidationError,
    DiagnosticSharedPlanReplayContext,
    InMemoryDiagnosticLifecycleStore,
    SqliteDiagnosticLifecycleStore,
    build_diagnostic_shared_plan_replay_context,
    derive_diagnostic_attempt_subject_sha256,
)
from test_diagnostic_execution_protocol import (  # noqa: E402
    ARTIFACT_IDS,
    error as terminal_error,
    fx as carrier_fixture,
)


TENANT = "tenant-diagnostic-lifecycle"
_SHARED = None


@pytest.fixture(scope="module")
def fx():
    return carrier_fixture.__wrapped__()


@pytest.fixture
def context(fx) -> DiagnosticLifecycleReplayContext:
    shared = shared_context(fx)
    return DiagnosticLifecycleReplayContext(
        shared_plan=shared,
        study_request=fx.request,
    )


def shared_context(fx):
    global _SHARED
    if _SHARED is None:
        _SHARED = build_diagnostic_shared_plan_replay_context(
            chain=fx.chain,
            plan=fx.plan,
            execution_contract=fx.contract,
        )
    return _SHARED


def registry(store=None, *, fault_hook=None) -> DiagnosticAttemptLifecycle:
    if store is None:
        store = InMemoryDiagnosticLifecycleStore(fault_hook=fault_hook)
    return DiagnosticAttemptLifecycle(
        store,
        nonce_factory=lambda count: bytes(range(count)),
    )


def issue(lifecycle: DiagnosticAttemptLifecycle, fx, *, tenant=TENANT, **changes):
    values = {
        "tenant_id": tenant,
        "chain": fx.chain,
        "plan": fx.plan,
        "study_request": fx.request,
        "execution_contract": fx.contract,
        "shared_plan_context": shared_context(fx),
        "binding_id": "diagnostic-child-binding-001",
        "binding_created_at": "2026-08-08T08:45:00Z",
        "assigned_worker_id": "diagnostic-worker-001",
        "archive_root": "C:/cas-harness/stagec/diag-child-001",
        "artifact_ids": ARTIFACT_IDS,
        "issued_at": "2026-08-08T08:50:00Z",
        "expires_at": "2026-08-08T11:00:00Z",
        "operation_id": "issue-attempt-001",
    }
    values.update(changes)
    return lifecycle.issue_attempt(**values)


def consume(lifecycle, issuance, context, **changes):
    values = {
        "tenant_id": issuance.snapshot.tenant_id,
        "attempt_subject_sha256": issuance.snapshot.attempt_subject_sha256,
        "context": context,
        "run_nonce_b64url": issuance.run_nonce_b64url,
        "worker_started_at": "2026-08-08T09:05:00Z",
        "operation_id": "consume-attempt-001",
    }
    values.update(changes)
    return lifecycle.consume_attempt(**values)


def complete(lifecycle, issuance, context, fx, **changes):
    values = {
        "tenant_id": issuance.snapshot.tenant_id,
        "attempt_subject_sha256": issuance.snapshot.attempt_subject_sha256,
        "context": context,
        "terminal_at": "2026-08-08T09:06:00Z",
        "terminal_status": COMPLETED,
        "terminal_phase": "COMPLETE",
        "invocation_certainty": "EXACTLY_ONE",
        "produced_artifacts": {
            "archive_admission": (fx.admission_ref, fx.admission_raw),
            "child_output": (fx.output_ref, fx.output_raw),
        },
        "error": None,
        "operation_id": "terminal-attempt-001",
    }
    values.update(changes)
    return lifecycle.build_and_record_terminal(**values)


def preauth_reject(lifecycle, fx, *, tenant=TENANT, **changes):
    values = {
        "tenant_id": tenant,
        "chain": fx.chain,
        "plan": fx.plan,
        "study_request": fx.request,
        "execution_contract": fx.contract,
        "shared_plan_context": shared_context(fx),
        "binding_id": "diagnostic-child-binding-001",
        "binding_created_at": "2026-08-08T08:45:00Z",
        "assigned_worker_id": "diagnostic-worker-001",
        "archive_root": "C:/cas-harness/stagec/diag-child-001",
        "artifact_ids": ARTIFACT_IDS,
        "terminal_at": "2026-08-08T08:49:00Z",
        "error": terminal_error("INPUT_REJECTED"),
        "operation_id": "preauth-reject-001",
    }
    values.update(changes)
    return lifecycle.reject_preauthorization(**values)


def test_issue_is_exact_create_only_and_nonce_is_released_once(fx, context):
    lifecycle = registry()
    first = issue(lifecycle, fx)
    replayed = issue(lifecycle, fx)

    assert first.issued_now is True
    assert first.run_nonce_b64url == fx.binding.run_nonce_b64url
    assert first.binding.raw_bytes == fx.binding.raw_bytes
    assert first.authorization.raw_bytes == fx.authorization.raw_bytes
    assert first.snapshot.state == AUTHORIZED
    assert first.snapshot.attempt_ordinal == 1
    assert first.snapshot.event_count == first.snapshot.record_version == 1
    assert replayed.issued_now is False
    assert replayed.run_nonce_b64url is None
    assert replayed.binding.raw_bytes == first.binding.raw_bytes
    replay = lifecycle.read_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=first.snapshot.attempt_subject_sha256,
        context=context,
    )
    assert replay.events[0].sha256 == replay.snapshot.head_event_sha256
    assert replay.events[0].state_before is None
    assert replay.events[0].state_after == AUTHORIZED
    assert replay.snapshot.authority["criteria_status"] == "OPEN"
    assert replay.snapshot.authority["product_claim_status"] == "NOT LICENSED"
    assert replay.snapshot.authority["disclosure_status"] == "HELD"
    assert replay.snapshot.authority["trusted_time"] == "NOT_PROVIDED"


def test_subject_digest_is_exact_and_attempt_fact_change_conflicts(fx):
    lifecycle = registry()
    first = issue(lifecycle, fx)
    expected = derive_diagnostic_attempt_subject_sha256(
        plan=fx.plan, study_request=fx.request
    )
    assert first.snapshot.attempt_subject_sha256 == expected
    assert first.binding.payload["execution_context"]["attempt_binding"][
        "attempt_subject_sha256"
    ] == expected
    with pytest.raises(DiagnosticLifecycleConflict):
        issue(lifecycle, fx, assigned_worker_id="diagnostic-worker-002")
    with pytest.raises(DiagnosticLifecycleConflict):
        issue(lifecycle, fx, operation_id="issue-attempt-changed")
    other_tenant = issue(lifecycle, fx, tenant="tenant-other-exact-request")
    assert (
        other_tenant.snapshot.issuance_request_sha256
        != first.snapshot.issuance_request_sha256
    )


def test_frozen_results_and_exact_public_replay_surface(fx, context):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    replay = lifecycle.read_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
        context=context,
    )
    with pytest.raises(FrozenInstanceError):
        replay.snapshot.state = RUNNING
    with pytest.raises(TypeError):
        replay.snapshot.authority["criteria_status"] = "CLOSED"
    with pytest.raises(TypeError):
        replay.produced_artifact_bodies["forged"] = b"x"
    assert replay.binding.raw_bytes == fx.binding.raw_bytes
    assert replay.authorization.raw_bytes == fx.authorization.raw_bytes
    assert replay.terminal_receipt is None
    assert replay.produced_artifact_bodies == {}


def test_consume_is_single_winner_idempotent_and_nonce_bound(fx, context):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    changed = consume(lifecycle, issued, context)
    replayed = consume(lifecycle, issued, context)
    assert changed.transitioned_now is True
    assert changed.snapshot.state == RUNNING
    assert replayed.transitioned_now is False
    assert replayed.event.sha256 == changed.event.sha256
    assert replayed.snapshot.event_count == 2
    with pytest.raises(DiagnosticLifecycleConflict):
        consume(
            lifecycle,
            issued,
            context,
            operation_id="consume-attempt-002",
        )


@pytest.mark.parametrize("bad_nonce", ["wrong", "nön-ascii"])
def test_consume_rejects_wrong_or_non_ascii_nonce(fx, context, bad_nonce):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    expected = (
        DiagnosticLifecycleValidationError
        if "ö" in bad_nonce
        else DiagnosticLifecycleConflict
    )
    with pytest.raises(expected):
        consume(lifecycle, issued, context, run_nonce_b64url=bad_nonce)
    assert lifecycle.read_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
        context=context,
    ).snapshot.state == AUTHORIZED


@pytest.mark.parametrize(
    ("started_at", "error_type"),
    [
        ("2026-08-08T08:49:59Z", DiagnosticLifecycleConflict),
        ("2026-08-08T11:00:00Z", DiagnosticLifecycleExpired),
        ("2026-08-08T11:00:01Z", DiagnosticLifecycleExpired),
    ],
)
def test_consume_enforces_half_open_authorization_window(
    fx, context, started_at, error_type
):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    with pytest.raises(error_type):
        consume(lifecycle, issued, context, worker_started_at=started_at)


def test_completed_terminal_retains_exact_outputs_and_forbids_second_terminal(
    fx, context
):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    consume(lifecycle, issued, context)
    terminal = complete(lifecycle, issued, context, fx)
    replayed = complete(lifecycle, issued, context, fx)
    assert terminal.transitioned_now is True
    assert terminal.snapshot.state == COMPLETED
    assert terminal.snapshot.event_count == 3
    assert replayed.transitioned_now is False
    replay = lifecycle.read_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
        context=context,
    )
    assert replay.terminal_receipt.raw_bytes == terminal.terminal_receipt.raw_bytes
    assert replay.produced_artifact_bodies == {
        "archive_admission": fx.admission_raw,
        "child_output": fx.output_raw,
    }
    assert [event.state_after for event in replay.events] == [
        AUTHORIZED,
        RUNNING,
        COMPLETED,
    ]
    assert all(event.payload["details"]["retry"] == "FORBIDDEN" for event in replay.events)
    assert all(
        event.payload["details"]["replacement"] == "FORBIDDEN"
        for event in replay.events
    )
    with pytest.raises(DiagnosticLifecycleConflict):
        lifecycle.terminalize_stranded_running(
            tenant_id=TENANT,
            attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
            context=context,
            observed_at="2026-08-08T09:07:00Z",
            operation_id="second-terminal-001",
        )


@pytest.mark.parametrize(
    ("status", "phase", "certainty", "category"),
    [
        (FAILED, "PRE_MODEL", "EXACTLY_ZERO", "EXECUTION_FAILED"),
        (INDETERMINATE, "DISPATCH_OR_EXECUTION", "INDETERMINATE_ZERO_OR_ONE", "EXECUTION_INDETERMINATE"),
    ],
)
def test_running_terminal_branches(fx, context, status, phase, certainty, category):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    consume(lifecycle, issued, context)
    result = lifecycle.build_and_record_terminal(
        tenant_id=TENANT,
        attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
        context=context,
        terminal_at="2026-08-08T09:06:00Z",
        terminal_status=status,
        terminal_phase=phase,
        invocation_certainty=certainty,
        produced_artifacts=None,
        error=terminal_error(category),
        operation_id="adverse-terminal-001",
    )
    assert result.snapshot.state == status
    assert result.terminal_receipt.terminal_status == status


def test_authorized_rejected_and_expired_terminal_branches(fx, context):
    rejected_lifecycle = registry()
    rejected = issue(rejected_lifecycle, fx)
    result = rejected_lifecycle.reject_authorized_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=rejected.snapshot.attempt_subject_sha256,
        context=context,
        terminal_at="2026-08-08T08:55:00Z",
        error=terminal_error("AUTHORIZATION_REJECTED"),
        operation_id="authorized-reject-001",
    )
    assert result.snapshot.state == REJECTED
    assert result.snapshot.worker_started_at is None

    expired_lifecycle = registry()
    expired = issue(expired_lifecycle, fx)
    result = expired_lifecycle.expire_authorized_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=expired.snapshot.attempt_subject_sha256,
        context=context,
        terminal_at="2026-08-08T11:00:00Z",
        error=terminal_error("AUTHORIZATION_EXPIRED"),
        operation_id="authorized-expire-001",
    )
    assert result.snapshot.state == EXPIRED
    assert result.snapshot.worker_started_at is None


def test_preauthorization_rejection_never_creates_or_releases_authorization(fx, context):
    lifecycle = registry()
    result = preauth_reject(lifecycle, fx)
    replayed = preauth_reject(lifecycle, fx)
    assert result.transitioned_now is True
    assert result.snapshot.state == REJECTED
    assert result.authorization is None
    assert result.terminal_receipt.authorization_sha256 is None
    assert result.snapshot.authorization_ref is None
    assert result.snapshot.worker_started_at is None
    assert replayed.transitioned_now is False
    assert replayed.authorization is None
    assert lifecycle.read_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=result.snapshot.attempt_subject_sha256,
        context=context,
    ).events[0].payload["details"]["model_invocation_request_count"] == 0
    with pytest.raises(DiagnosticLifecycleConflict):
        issue(lifecycle, fx)


def test_stranded_running_terminalizes_indeterminate_without_retry(fx, context):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    consume(lifecycle, issued, context)
    recovered = lifecycle.terminalize_stranded_running(
        tenant_id=TENANT,
        attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
        context=context,
        observed_at="2026-08-08T12:00:00Z",
        operation_id="stranded-recovery-001",
    )
    assert recovered.snapshot.state == INDETERMINATE
    assert recovered.terminal_receipt.invocation_certainty == "INDETERMINATE_ZERO_OR_ONE"
    with pytest.raises(DiagnosticLifecycleConflict):
        consume(
            lifecycle,
            issued,
            context,
            operation_id="retry-forbidden-001",
        )


def test_concurrent_issue_and_consume_each_have_exactly_one_winner(fx, context):
    lifecycle = registry()
    with ThreadPoolExecutor(max_workers=8) as pool:
        issued_rows = list(pool.map(lambda _: issue(lifecycle, fx), range(16)))
    assert sum(row.issued_now for row in issued_rows) == 1
    winner = next(row for row in issued_rows if row.issued_now)
    assert sum(row.run_nonce_b64url is not None for row in issued_rows) == 1

    def consume_once(_):
        return consume(lifecycle, winner, context)

    with ThreadPoolExecutor(max_workers=8) as pool:
        consumed_rows = list(pool.map(consume_once, range(16)))
    assert sum(row.transitioned_now for row in consumed_rows) == 1
    assert {row.event.sha256 for row in consumed_rows} == {
        consumed_rows[0].event.sha256
    }


@pytest.mark.parametrize("stage", ["memory.create.after_attempt", "memory.create.after_event"])
def test_memory_create_fault_rolls_back_all_rows(fx, stage):
    def fail(current):
        if current == stage:
            raise RuntimeError("simulated crash")

    store = InMemoryDiagnosticLifecycleStore(fault_hook=fail)
    lifecycle = registry(store)
    with pytest.raises(DiagnosticLifecyclePersistenceError):
        issue(lifecycle, fx)
    assert lifecycle.list_subjects(tenant_id=TENANT) == ()


def test_memory_cas_fault_rolls_back_attempt_and_event(fx, context):
    armed = {"value": False}

    def fail(stage):
        if armed["value"] and stage == "memory.cas.after_attempt":
            raise RuntimeError("simulated crash")

    store = InMemoryDiagnosticLifecycleStore(fault_hook=fail)
    lifecycle = registry(store)
    issued = issue(lifecycle, fx)
    armed["value"] = True
    with pytest.raises(DiagnosticLifecyclePersistenceError):
        consume(lifecycle, issued, context)
    replay = lifecycle.read_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
        context=context,
    )
    assert replay.snapshot.state == AUTHORIZED
    assert len(replay.events) == 1


def test_sqlite_reopen_preserves_exact_family_and_no_nonce_reissue(fx, context, tmp_path):
    path = tmp_path / "diagnostic-lifecycle.sqlite3"
    first_store = SqliteDiagnosticLifecycleStore(path)
    first = registry(first_store)
    issued = issue(first, fx)
    consume(first, issued, context)
    complete(first, issued, context, fx)
    first_store.close()

    second_store = SqliteDiagnosticLifecycleStore(path)
    second = registry(second_store)
    replay = second.read_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
        context=context,
    )
    replayed_issue = issue(second, fx)
    assert replay.snapshot.state == COMPLETED
    assert replay.snapshot.event_count == 3
    assert replay.binding.raw_bytes == fx.binding.raw_bytes
    assert replay.authorization.raw_bytes == fx.authorization.raw_bytes
    assert replay.produced_artifact_bodies["child_output"] == fx.output_raw
    assert replayed_issue.issued_now is False
    assert replayed_issue.run_nonce_b64url is None
    assert second.backend_durability_profile["profile"] == (
        "SQLITE_SINGLE_HOST_DURABLE_NOT_REPLICATED"
    )
    second_store.close()


@pytest.mark.parametrize("stage", ["sqlite.create.after_attempt", "sqlite.create.after_event"])
def test_sqlite_create_fault_rolls_back_transaction(fx, tmp_path, stage):
    def fail(current):
        if current == stage:
            raise RuntimeError("simulated crash")

    path = tmp_path / f"fault-{stage.rsplit('.', 1)[-1]}.sqlite3"
    store = SqliteDiagnosticLifecycleStore(path, fault_hook=fail)
    lifecycle = registry(store)
    with pytest.raises(DiagnosticLifecyclePersistenceError):
        issue(lifecycle, fx)
    assert lifecycle.list_subjects(tenant_id=TENANT) == ()
    store.close()
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM diagnostic_attempts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM diagnostic_attempt_events").fetchone()[0] == 0


def test_two_sqlite_connections_arbitrate_one_issuance(fx, tmp_path):
    path = tmp_path / "shared.sqlite3"
    left_store = SqliteDiagnosticLifecycleStore(path)
    right_store = SqliteDiagnosticLifecycleStore(path)
    left = registry(left_store)
    right = registry(right_store)
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(lambda lifecycle: issue(lifecycle, fx), (left, right)))
    assert sum(row.issued_now for row in rows) == 1
    assert sum(row.run_nonce_b64url is not None for row in rows) == 1
    left_store.close()
    right_store.close()


def test_tenant_scope_isolated_while_nonce_unique_inside_tenant(fx):
    lifecycle = registry()
    left = issue(lifecycle, fx, tenant="tenant-left")
    right = issue(lifecycle, fx, tenant="tenant-right")
    assert left.snapshot.attempt_subject_sha256 == right.snapshot.attempt_subject_sha256
    assert left.snapshot.tenant_id != right.snapshot.tenant_id
    assert left.run_nonce_b64url == right.run_nonce_b64url
    assert lifecycle.list_subjects(tenant_id="tenant-left") == (
        left.snapshot.attempt_subject_sha256,
    )


def test_reconciliation_reports_open_stranded_complete_and_context_extras(fx, context):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    subject = issued.snapshot.attempt_subject_sha256
    open_result = lifecycle.reconcile(tenant_id=TENANT, contexts={subject: context})
    assert open_result.integrity_clean is True
    assert open_result.all_terminal is False
    assert open_result.state_counts[AUTHORIZED] == 1
    assert open_result.issues[0].code == "AUTHORIZED_NOT_TERMINAL"

    consume(lifecycle, issued, context)
    running_result = lifecycle.reconcile(tenant_id=TENANT, contexts={subject: context})
    assert running_result.issues[0].code == "STRANDED_RUNNING"
    lifecycle.terminalize_stranded_running(
        tenant_id=TENANT,
        attempt_subject_sha256=subject,
        context=context,
        observed_at="2026-08-08T12:00:00Z",
        operation_id="reconcile-terminal-001",
    )
    final = lifecycle.reconcile(tenant_id=TENANT, contexts={subject: context})
    assert final.integrity_clean is True
    assert final.all_terminal is True
    assert final.attempt_count == 1
    assert final.event_count == 3
    assert final.issues == ()

    extra = "F" * 64
    extra_result = lifecycle.reconcile(
        tenant_id=TENANT, contexts={subject: context, extra: context}
    )
    assert extra_result.integrity_clean is False
    assert extra_result.issues[-1].code == "UNREGISTERED_CONTEXT"


def test_missing_context_and_missing_subject_are_explicit(fx, context):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    result = lifecycle.reconcile(tenant_id=TENANT, contexts={})
    assert result.integrity_clean is False
    assert result.all_terminal is False
    assert result.issues[0].code == "MISSING_REPLAY_CONTEXT"
    with pytest.raises(DiagnosticLifecycleNotFound):
        lifecycle.read_attempt(
            tenant_id=TENANT,
            attempt_subject_sha256="A" * 64,
            context=context,
        )
    assert issued.snapshot.attempt_subject_sha256 in lifecycle.list_subjects(
        tenant_id=TENANT
    )


def test_memory_event_byte_forgery_is_rejected(fx, context):
    store = InMemoryDiagnosticLifecycleStore()
    lifecycle = registry(store)
    issued = issue(lifecycle, fx)
    key = (TENANT, issued.snapshot.attempt_subject_sha256)
    event = store._events[key][0]
    forged_value = json.loads(event.raw_bytes)
    forged_value["details"]["retry"] = "ALLOWED"
    forged = replace(event, raw_bytes=canonical_json_bytes(forged_value))
    store._events[key] = (forged,)
    with pytest.raises(DiagnosticLifecycleIntegrityError):
        lifecycle.read_attempt(
            tenant_id=TENANT,
            attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
            context=context,
        )


def test_memory_event_chain_reorder_and_attempt_projection_forgery_are_rejected(
    fx, context
):
    store = InMemoryDiagnosticLifecycleStore()
    lifecycle = registry(store)
    issued = issue(lifecycle, fx)
    consume(lifecycle, issued, context)
    key = (TENANT, issued.snapshot.attempt_subject_sha256)
    original = store._events[key]
    original_attempt = store._attempts[key]
    store._events[key] = tuple(reversed(original))
    with pytest.raises(DiagnosticLifecycleIntegrityError):
        lifecycle.read_attempt(
            tenant_id=TENANT,
            attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
            context=context,
        )
    store._events[key] = original
    store._attempts[key] = replace(
        original_attempt, issuance_request_sha256="A" * 64
    )
    with pytest.raises(DiagnosticLifecycleIntegrityError):
        lifecycle.read_attempt(
            tenant_id=TENANT,
            attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
            context=context,
        )
    store._attempts[key] = replace(original_attempt, attempt_ordinal=2)
    with pytest.raises(DiagnosticLifecycleIntegrityError):
        lifecycle.read_attempt(
            tenant_id=TENANT,
            attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
            context=context,
        )


def test_sqlite_payload_forgery_is_rejected(fx, context, tmp_path):
    path = tmp_path / "forged.sqlite3"
    store = SqliteDiagnosticLifecycleStore(path)
    lifecycle = registry(store)
    issued = issue(lifecycle, fx)
    with sqlite3.connect(path) as conn:
        raw = conn.execute(
            "SELECT payload FROM diagnostic_attempts WHERE tenant_id = ?",
            (TENANT,),
        ).fetchone()[0]
        value = json.loads(raw)
        value["attempt_ordinal"] = 2
        conn.execute(
            "UPDATE diagnostic_attempts SET payload = ? WHERE tenant_id = ?",
            (canonical_json_bytes(value), TENANT),
        )
        conn.commit()
    with pytest.raises(
        (DiagnosticLifecycleIntegrityError, DiagnosticLifecyclePersistenceError)
    ):
        lifecycle.read_attempt(
            tenant_id=TENANT,
            attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
            context=context,
        )
    store.close()


def test_terminal_from_wrong_state_and_changed_operation_are_rejected(fx, context):
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    with pytest.raises(DiagnosticLifecycleValidationError):
        complete(lifecycle, issued, context, fx)
    consume(lifecycle, issued, context)
    complete(lifecycle, issued, context, fx)
    with pytest.raises(DiagnosticLifecycleConflict):
        complete(
            lifecycle,
            issued,
            context,
            fx,
            terminal_at="2026-08-08T09:07:00Z",
        )


def test_store_close_and_bad_inputs_fail_closed(fx, context):
    store = InMemoryDiagnosticLifecycleStore()
    lifecycle = registry(store)
    issued = issue(lifecycle, fx)
    with pytest.raises(DiagnosticLifecycleValidationError):
        lifecycle.consume_attempt(
            tenant_id=TENANT,
            attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
            context=context,
            run_nonce_b64url=issued.run_nonce_b64url,
            worker_started_at="not-a-time",
            operation_id="bad-time-001",
        )
    store.close()
    with pytest.raises(DiagnosticLifecyclePersistenceError):
        lifecycle.list_subjects(tenant_id=TENANT)


@pytest.mark.parametrize(
    "path",
    [":memory:", "file:diagnostic-lifecycle?mode=memory"],
)
def test_sqlite_memory_modes_cannot_claim_durable_profile(path):
    with pytest.raises(DiagnosticLifecycleValidationError):
        SqliteDiagnosticLifecycleStore(path)


def test_full_480_row_shared_plan_read_and_reconcile_have_bounded_cost(fx):
    # "Bounded cost" here is the exact 480-row workload and event cardinality.
    # Gate 5 carries NO PERFORMANCE AUTHORITY, so host wall-clock throughput is
    # benchmark evidence, not a correctness pass/fail condition.
    shared = shared_context(fx)
    store = InMemoryDiagnosticLifecycleStore()
    counter = {"value": 0}

    def unique_nonce(count):
        counter["value"] += 1
        return counter["value"].to_bytes(count, "big")

    lifecycle = DiagnosticAttemptLifecycle(store, nonce_factory=unique_nonce)
    tenant = "tenant-full-480-performance"
    contexts = {}
    subjects = []
    for case in shared.plan.cases:
        ordinal = case.execution_ordinal
        request = shared.build_study_request(
            case_id=case.case_id,
            created_at="2026-08-08T08:40:00Z",
        )
        row_context = DiagnosticLifecycleReplayContext(
            shared_plan=shared,
            study_request=request,
        )
        suffix = f"{ordinal:03d}"
        ids = {
            key: f"diag-{key.replace('_', '-')}-{suffix}"
            for key in ARTIFACT_IDS
        }
        result = lifecycle.reject_preauthorization(
            tenant_id=tenant,
            chain=shared.chain,
            plan=shared.plan,
            study_request=request,
            execution_contract=shared.execution_contract,
            shared_plan_context=shared,
            binding_id=f"diagnostic-child-binding-{suffix}",
            binding_created_at="2026-08-08T08:45:00Z",
            assigned_worker_id="diagnostic-worker-performance",
            archive_root=f"C:/cas-harness/stagec/diag-child-{suffix}",
            artifact_ids=ids,
            terminal_at="2026-08-08T08:49:00Z",
            error=terminal_error("INPUT_REJECTED"),
            operation_id=f"preauth-reject-{suffix}",
        )
        subject = result.snapshot.attempt_subject_sha256
        contexts[subject] = row_context
        subjects.append(subject)
    one = lifecycle.read_attempt(
        tenant_id=tenant,
        attempt_subject_sha256=subjects[0],
        context=contexts[subjects[0]],
    )
    rows = tuple(
        lifecycle.read_attempt(
            tenant_id=tenant,
            attempt_subject_sha256=subject,
            context=contexts[subject],
        )
        for subject in subjects
    )
    reconciled = lifecycle.reconcile(tenant_id=tenant, contexts=contexts)

    assert len(rows) == shared.case_count == 480
    assert one.snapshot.state == REJECTED
    assert reconciled.attempt_count == 480
    assert reconciled.event_count == 480
    assert reconciled.integrity_clean is True
    assert reconciled.all_terminal is True


def test_shared_plan_context_is_factory_only_process_sealed_and_map_bound(fx):
    shared = shared_context(fx)
    with pytest.raises(TypeError):
        DiagnosticSharedPlanReplayContext()
    with pytest.raises(TypeError):
        replace(shared, kernel_sha256="F" * 64)

    forged = object.__new__(DiagnosticSharedPlanReplayContext)
    for name in (
        "chain",
        "plan",
        "execution_contract",
        "kernel_sha256",
        "case_count",
        "planned_request_ids",
        "_case_by_id",
        "_capture_by_case_id",
        "_study_request_refs",
    ):
        object.__setattr__(forged, name, getattr(shared, name))
    with pytest.raises(DiagnosticLifecycleValidationError):
        forged.build_study_request(
            case_id=fx.request.case_id,
            created_at="2026-08-08T08:40:00Z",
        )

    original_kernel = shared.kernel_sha256
    object.__setattr__(shared, "kernel_sha256", "E" * 64)
    try:
        with pytest.raises(DiagnosticLifecycleValidationError):
            shared.replay_study_request(fx.request)
    finally:
        object.__setattr__(shared, "kernel_sha256", original_kernel)

    original_cases = shared._case_by_id
    object.__setattr__(shared, "_case_by_id", dict(original_cases))
    try:
        with pytest.raises(DiagnosticLifecycleValidationError):
            shared.replay_study_request(fx.request)
    finally:
        object.__setattr__(shared, "_case_by_id", original_cases)


def test_shared_plan_seal_rejects_post_factory_chain_mutation(fx):
    shared = shared_context(fx)
    slot = "_DiagnosticPreregistrationChain__amendments"
    original = getattr(shared.chain, slot)
    setattr(shared.chain, slot, (*original, object()))
    try:
        with pytest.raises(DiagnosticLifecycleValidationError):
            shared.replay_study_request(fx.request)
    finally:
        setattr(shared.chain, slot, original)


@pytest.mark.parametrize(
    ("target_name", "field_name", "forged_value"),
    [
        ("plan", "execution_window_start", "2026-08-08T10:00:00Z"),
        ("plan", "payload", {"forged": "plan-payload"}),
        ("execution_contract", "created_at", "2026-08-08T08:36:00Z"),
        ("execution_contract", "payload", {"forged": "contract-payload"}),
    ],
)
def test_shared_plan_seal_binds_plan_and_contract_projections(
    fx, target_name, field_name, forged_value
):
    shared = shared_context(fx)
    target = getattr(shared, target_name)
    original = getattr(target, field_name)
    object.__setattr__(target, field_name, forged_value)
    try:
        with pytest.raises(DiagnosticLifecycleValidationError):
            shared.replay_study_request(fx.request)
    finally:
        object.__setattr__(target, field_name, original)


def test_row_operations_do_not_recompute_plan_sized_ref_closures(
    fx, context, monkeypatch
):
    calls = []
    original = lifecycle_module._execution._unique_ref_closure

    def instrumented(references, path):
        snapshot = tuple(references)
        calls.append((path, len(snapshot)))
        return original(snapshot, path)

    monkeypatch.setattr(
        lifecycle_module._execution,
        "_unique_ref_closure",
        instrumented,
    )
    lifecycle = registry()
    issued = issue(lifecycle, fx)
    consume(lifecycle, issued, context)
    complete(lifecycle, issued, context, fx)
    lifecycle.read_attempt(
        tenant_id=TENANT,
        attempt_subject_sha256=issued.snapshot.attempt_subject_sha256,
        context=context,
    )
    assert calls == []
    source = lifecycle_module._shared_binding_value.__code__.co_names
    assert "artifact_refs" not in source


@pytest.mark.parametrize(
    ("column", "forged_value", "requested_tenant", "requested_subject"),
    [
        ("tenant_id", "tenant-forged", "tenant-forged", None),
        ("attempt_subject_sha256", "B" * 64, TENANT, "B" * 64),
        ("state", REJECTED, TENANT, None),
        ("version", 99, TENANT, None),
        ("run_nonce_sha256", "C" * 64, TENANT, None),
        ("authorization_sha256", "D" * 64, TENANT, None),
        ("terminal_sha256", "E" * 64, TENANT, None),
        ("head_event_sha256", "F" * 64, TENANT, None),
    ],
)
def test_sqlite_redundant_attempt_columns_are_exactly_payload_bound(
    fx,
    context,
    tmp_path,
    column,
    forged_value,
    requested_tenant,
    requested_subject,
):
    path = tmp_path / f"attempt-column-{column}.sqlite3"
    store = SqliteDiagnosticLifecycleStore(path)
    lifecycle = registry(store)
    issued = issue(lifecycle, fx)
    subject = issued.snapshot.attempt_subject_sha256
    with sqlite3.connect(path) as conn:
        conn.execute(
            f"UPDATE diagnostic_attempts SET {column} = ? WHERE tenant_id = ?",
            (forged_value, TENANT),
        )
        conn.commit()
    requested_subject = subject if requested_subject is None else requested_subject
    with pytest.raises(DiagnosticLifecyclePersistenceError):
        store.get_attempt(requested_tenant, requested_subject)
    store.close()


@pytest.mark.parametrize(
    ("column", "forged_value", "requested_tenant", "requested_subject"),
    [
        ("tenant_id", "event-tenant-forged", "event-tenant-forged", None),
        ("attempt_subject_sha256", "A" * 64, TENANT, "A" * 64),
        ("sequence", 99, TENANT, None),
        ("operation_id", "event-operation-forged", TENANT, None),
        ("event_sha256", "B" * 64, TENANT, None),
    ],
)
def test_sqlite_redundant_event_columns_are_exactly_payload_bound(
    fx,
    tmp_path,
    column,
    forged_value,
    requested_tenant,
    requested_subject,
):
    path = tmp_path / f"event-column-{column}.sqlite3"
    store = SqliteDiagnosticLifecycleStore(path)
    lifecycle = registry(store)
    issued = issue(lifecycle, fx)
    subject = issued.snapshot.attempt_subject_sha256
    with sqlite3.connect(path) as conn:
        conn.execute(
            f"UPDATE diagnostic_attempt_events SET {column} = ? WHERE tenant_id = ?",
            (forged_value, TENANT),
        )
        conn.commit()
    requested_subject = subject if requested_subject is None else requested_subject
    with pytest.raises(DiagnosticLifecyclePersistenceError):
        store.list_events(requested_tenant, requested_subject)
    store.close()


def test_sqlite_payload_scope_rewrite_disagrees_with_sql_key(fx, tmp_path):
    path = tmp_path / "payload-scope-rewrite.sqlite3"
    store = SqliteDiagnosticLifecycleStore(path)
    lifecycle = registry(store)
    issued = issue(lifecycle, fx)
    subject = issued.snapshot.attempt_subject_sha256
    with sqlite3.connect(path) as conn:
        raw = conn.execute(
            "SELECT payload FROM diagnostic_attempts WHERE tenant_id = ?",
            (TENANT,),
        ).fetchone()[0]
        value = json.loads(raw)
        value["tenant_id"] = "payload-tenant-forged"
        conn.execute(
            "UPDATE diagnostic_attempts SET payload = ? WHERE tenant_id = ?",
            (canonical_json_bytes(value), TENANT),
        )
        conn.commit()
    with pytest.raises(DiagnosticLifecyclePersistenceError):
        store.get_attempt(TENANT, subject)
    store.close()
