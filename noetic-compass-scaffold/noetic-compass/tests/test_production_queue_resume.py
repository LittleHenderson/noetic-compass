"""Contract tests for the workstream-04 queue/resume scaffold.

These exercise the in-memory stub's lease/ack/nack/checkpoint/dead-letter
semantics AND the honesty invariant: the stub never claims durability or a
committed/verified status. The stub deliberately mirrors the fleet executor's
single-holder, token-validated, time-boxed lease discipline
(``api/services/cas_harness_fleet_executor.py``) so a real ``DurableQueue``
backend is a drop-in.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from api.services.production.queue_resume import (
    Checkpoint,
    DeadLetterPolicy,
    DeliveryGuarantee,
    InMemoryQueueStub,
    Lease,
    QueueJob,
    QueueResumeError,
    RetryPolicy,
)


def _job(job_id: str = "fleet-job-0000000000000001", *, run_id: str = "cas-dist-abc",
         shard_id: str = "layers-000-007", worker: str | None = "probe-worker-01",
         max_attempts: int = 3) -> QueueJob:
    return QueueJob(
        job_id=job_id,
        run_id=run_id,
        shard_id=shard_id,
        payload_ref=f"assignment://{run_id}/{shard_id}",
        assigned_worker_id=worker,
        max_attempts=max_attempts,
    )


def _queue() -> InMemoryQueueStub:
    return InMemoryQueueStub()


# --- honesty invariants ----------------------------------------------------

def test_stub_never_claims_durability_or_commit():
    q = _queue()
    assert q.is_durable is False
    assert q.backend_kind == "in_memory_stub"
    assert q.delivery_guarantee == "none_process_local"

    note = q.status_note()
    assert note["is_durable"] is False
    assert note["durably_committed"] is False
    assert note["replicated"] is False
    assert note["cross_process_safe"] is False
    assert note["delivery_guarantee"] == "none_process_local"


def test_delivery_guarantee_is_never_exactly_once():
    # The literal type forbids it; assert the runtime value is honest too.
    allowed: set[DeliveryGuarantee] = {"none_process_local", "at_least_once"}
    assert _queue().delivery_guarantee in allowed
    assert _queue().delivery_guarantee != "at_least_once"  # a stub cannot promise even this


# --- enqueue / lease single-holder ----------------------------------------

def test_enqueue_is_idempotent_on_job_id():
    q = _queue()
    assert q.enqueue(_job()) == "fleet-job-0000000000000001"
    # Re-enqueue is a no-op; does not reset or duplicate.
    assert q.enqueue(_job()) == "fleet-job-0000000000000001"
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease is not None
    # Only one job existed -> nothing else leasable.
    assert q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01") is None


def test_lease_grants_single_holder_and_increments_attempt():
    q = _queue()
    q.enqueue(_job())
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert isinstance(lease, Lease)
    assert lease.job_id == "fleet-job-0000000000000001"
    assert lease.attempt == 1
    assert lease.deadline
    # A second worker cannot steal a leased job.
    assert q.lease(run_id="cas-dist-abc", worker_id="probe-worker-02") is None


def test_pinned_job_is_not_leasable_by_other_worker():
    q = _queue()
    q.enqueue(_job(worker="probe-worker-07"))
    # Wrong worker for a pinned job.
    assert q.lease(run_id="cas-dist-abc", worker_id="probe-worker-99") is None
    # Correct worker can lease.
    assert q.lease(run_id="cas-dist-abc", worker_id="probe-worker-07") is not None


def test_unpinned_job_is_leasable_by_any_worker():
    q = _queue()
    q.enqueue(_job(worker=None))
    lease = q.lease(run_id="cas-dist-abc", worker_id="any-worker-42")
    assert lease is not None
    assert lease.worker_id == "any-worker-42"


# --- ack idempotency + durable-style replay drop ---------------------------

def test_ack_completes_job_and_is_idempotent():
    q = _queue()
    q.enqueue(_job())
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease is not None
    key = "cas-fragment://cas-dist-abc/job/worker/shard/sha256:deadbeef"
    assert q.ack(lease_id=lease.lease_id, idempotency_key=key) is True
    # Re-ack of the same lease is a NO-OP (False), never an error.
    assert q.ack(lease_id=lease.lease_id, idempotency_key=key) is False
    # Completed job is not re-leasable.
    assert q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01") is None


def test_duplicate_idempotency_key_on_active_lease_is_dropped():
    # Models at-least-once delivery + idempotent merge = exactly-once effect:
    # the SAME content-addressed result (identical bytes -> identical fragment
    # ref) arrives on two distinct, currently-valid leases. The first ack commits
    # it; the second is dropped (False) instead of double-counting the result.
    # Two jobs whose work deduplicates to identical content share one key.
    q = _queue()
    q.enqueue(_job(job_id="fleet-job-aaaaaaaaaaaaaaa1"))
    q.enqueue(_job(job_id="fleet-job-bbbbbbbbbbbbbbb2"))
    key = "cas-fragment://cas-dist-abc/shard/worker/sha256:cafef00d"

    lease_a = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    lease_b = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease_a is not None and lease_b is not None
    assert lease_a.lease_id != lease_b.lease_id

    # First commit of the content key succeeds.
    assert q.ack(lease_id=lease_a.lease_id, idempotency_key=key) is True
    # Second distinct, active lease presents the SAME committed content -> dropped.
    assert q.ack(lease_id=lease_b.lease_id, idempotency_key=key) is False
    assert key in q._acked_keys


def test_ack_without_active_lease_raises():
    q = _queue()
    with pytest.raises(QueueResumeError, match="active lease"):
        q.ack(lease_id="does-not-exist", idempotency_key="cas-fragment://x/sha256:1")


def test_ack_requires_nonempty_idempotency_key():
    q = _queue()
    q.enqueue(_job())
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease is not None
    with pytest.raises(QueueResumeError, match="idempotency_key is required"):
        q.ack(lease_id=lease.lease_id, idempotency_key="   ")


# --- nack: backoff retry vs dead-letter ------------------------------------

def test_nack_retryable_sets_backoff_and_requeues():
    q = _queue()
    q.enqueue(_job(max_attempts=3))
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease is not None
    status = q.nack(
        lease_id=lease.lease_id,
        error_message="transient CUDA OOM",
        retry=RetryPolicy(base_backoff_seconds=2.0),
        dlq=DeadLetterPolicy(),
    )
    assert status == "failed"
    # Backoff gate is in the future -> not immediately leasable.
    assert q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01") is None
    # Clear the gate to prove it becomes leasable again with attempt preserved.
    q._jobs[lease.job_id] = replace(q._jobs[lease.job_id], not_before=None)
    released = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert released is not None
    assert released.attempt == 2  # attempt 1 was spent on the failed try


def test_nack_dead_letters_after_max_attempts():
    q = _queue()
    q.enqueue(_job(max_attempts=2))
    retry = RetryPolicy(base_backoff_seconds=0.0, jitter_seconds=0.0)
    dlq = DeadLetterPolicy()

    # Attempt 1
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease is not None and lease.attempt == 1
    assert q.nack(lease_id=lease.lease_id, error_message="boom 1", retry=retry, dlq=dlq) == "failed"

    # Attempt 2 -> reaches max_attempts -> dead-letter
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease is not None and lease.attempt == 2
    assert q.nack(lease_id=lease.lease_id, error_message="boom 2", retry=retry, dlq=dlq) == "dead_letter"

    dead = q.list_dead_letters(run_id="cas-dist-abc")
    assert len(dead) == 1
    assert dead[0].job_id == "fleet-job-0000000000000001"
    assert dead[0].error_history == ("boom 1", "boom 2")  # full "show your work" trail
    # Dead-lettered job is not leasable.
    assert q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01") is None


def test_nack_non_retryable_dead_letters_immediately():
    q = _queue()
    q.enqueue(_job(max_attempts=9))
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease is not None
    status = q.nack(
        lease_id=lease.lease_id,
        error_message="Worker probe-worker-01 model_id does not match the distributed audit model.",
        retry=RetryPolicy(),
        dlq=DeadLetterPolicy(),
    )
    # A wrong-model error can never be fixed by retrying -> straight to DLQ even
    # though attempt (1) < max_attempts (9).
    assert status == "dead_letter"
    assert len(q.list_dead_letters(run_id="cas-dist-abc")) == 1


def test_requeue_dead_letter_resets_attempts():
    q = _queue()
    q.enqueue(_job(max_attempts=1))
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease is not None
    q.nack(
        lease_id=lease.lease_id,
        error_message="boom",
        retry=RetryPolicy(base_backoff_seconds=0.0),
        dlq=DeadLetterPolicy(),
    )
    assert len(q.list_dead_letters(run_id="cas-dist-abc")) == 1

    assert q.requeue_dead_letter(job_id="fleet-job-0000000000000001") is True
    assert q.list_dead_letters(run_id="cas-dist-abc") == []
    # Leasable again with a fresh attempt count.
    released = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert released is not None
    assert released.attempt == 1
    # Requeue of an unknown job is a no-op False.
    assert q.requeue_dead_letter(job_id="nope") is False


# --- visibility timeout reaper + lease extension ---------------------------

def test_reaper_reclaims_expired_lease_keeping_attempt():
    q = _queue()
    q.enqueue(_job(max_attempts=3))
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert lease is not None
    # Force the visibility deadline into the past.
    q._leases[lease.job_id].deadline = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    reclaimed = q.reap_expired()
    assert list(reclaimed) == [lease.job_id]
    # Re-leasable; attempt was spent so the next lease is attempt 2.
    released = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01")
    assert released is not None
    assert released.attempt == 2


def test_extend_lease_pushes_deadline_and_blocks_after_expiry():
    q = _queue()
    q.enqueue(_job())
    lease = q.lease(run_id="cas-dist-abc", worker_id="probe-worker-01", lease_seconds=10)
    assert lease is not None
    extended = q.extend_lease(lease_id=lease.lease_id, lease_seconds=900)
    assert extended is not None
    assert datetime.fromisoformat(extended.deadline) > datetime.fromisoformat(lease.deadline)

    # Once expired, extend refuses (the reaper owns it).
    q._leases[lease.job_id].deadline = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    assert q.extend_lease(lease_id=lease.lease_id, lease_seconds=900) is None


# --- checkpoint monotonicity ----------------------------------------------

def test_checkpoint_is_monotonic_no_rewind():
    q = _queue()
    assert q.latest_checkpoint(run_id="cas-dist-abc", shard_id="layers-000-007") is None
    assert q.checkpoint(Checkpoint(
        run_id="cas-dist-abc", shard_id="layers-000-007", cursor=10,
        partial_result_ref="sha256:aaa",
    )) is True
    # Advancing cursor accepted.
    assert q.checkpoint(Checkpoint(
        run_id="cas-dist-abc", shard_id="layers-000-007", cursor=42,
        partial_result_ref="sha256:bbb",
    )) is True
    # Equal or behind is refused (no rewind).
    assert q.checkpoint(Checkpoint(
        run_id="cas-dist-abc", shard_id="layers-000-007", cursor=42,
        partial_result_ref="sha256:ccc",
    )) is False
    assert q.checkpoint(Checkpoint(
        run_id="cas-dist-abc", shard_id="layers-000-007", cursor=5,
        partial_result_ref="sha256:ddd",
    )) is False

    latest = q.latest_checkpoint(run_id="cas-dist-abc", shard_id="layers-000-007")
    assert latest is not None
    assert latest.cursor == 42
    assert latest.partial_result_ref == "sha256:bbb"


def test_retry_policy_backoff_is_exponential_and_clamped():
    policy = RetryPolicy(base_backoff_seconds=2.0, max_backoff_seconds=60.0, jitter_seconds=0.0)
    now = datetime(2026, 6, 1, tzinfo=UTC).isoformat()

    def delay(attempt: int) -> float:
        nb = policy.next_not_before(attempt=attempt, now_iso=now)
        return (datetime.fromisoformat(nb) - datetime.fromisoformat(now)).total_seconds()

    assert delay(1) == 2.0    # base * 2**0
    assert delay(2) == 4.0    # base * 2**1
    assert delay(3) == 8.0
    assert delay(10) == 60.0  # clamped to max_backoff_seconds
