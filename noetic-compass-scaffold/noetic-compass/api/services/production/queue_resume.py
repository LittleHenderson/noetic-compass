"""Queue / resume — import-isolated design-stage scaffold (workstream 04).

This module defines the *seam* for a durable job queue with idempotent leasing,
checkpoint/resume, dead-letter, and retry/backoff, plus a clearly-labeled
**in-memory stub** that the test-suite and the design blueprint can build against.

Nothing here is wired into the live FastAPI app or the fleet executor
(`api/services/cas_harness_fleet_executor.py`). It exists so the blueprint in
``docs/working/production_readiness/04_queue_and_resume.md`` has a concrete,
type-checked interface, and so the lease/ack/nack/checkpoint/dead-letter
semantics can be exercised without a real broker.

HONESTY RULE (see ``api/services/production/__init__.py`` and
``docs/working/production_readiness/00_index.md``):

    A stub is a stub. ``InMemoryQueueStub`` lives in one process's memory and
    vanishes on restart. It MUST NEVER report a job/checkpoint as durable,
    committed, replicated, or persisted, and MUST NEVER emit a
    ``*_VERIFIED`` / ``*_METERED`` / ``*_WORM_COMMITTED`` status. Its
    ``delivery_guarantee`` is hard-coded to ``"none_process_local"``. The flip
    to ``"at_least_once"`` + ``durably_committed=True`` is only honest from a
    real broker backend (Phase C of the blueprint), never from this stub.

The stub deliberately mirrors the *real* lease/receipt discipline already proven
in the fleet executor (single-holder token-validated lease, time-boxed
visibility, replay-protected ack) so a real ``DurableQueue`` backend is a drop-in
replacement for the executor's in-process ``_FLEET_RUNS``-backed leasing — not a
new contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol, Sequence
from uuid import uuid4


JobStatus = Literal["queued", "leased", "completed", "failed", "dead_letter"]

# A backend may only ever advertise one of these. The stub is pinned to
# "none_process_local"; "at_least_once" is reserved for a real durable broker.
# "exactly_once" is intentionally NOT a member: exactly-once *delivery* is not an
# honest claim over an unreliable fleet (see blueprint §4/§7). The honest target
# is at-least-once delivery + idempotent merge = exactly-once *effect*.
DeliveryGuarantee = Literal["none_process_local", "at_least_once"]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class QueueResumeError(ValueError):
    """Raised when a queue transition would overstate delivery/durability."""


@dataclass(frozen=True)
class QueueJob:
    """A unit of distributed-audit work to be leased to exactly one worker at a time.

    ``job_id`` mirrors the fleet executor's deterministic id
    (``_job_id_for(audit, worker, shard)`` -> ``fleet-job-<sha256[:16]>``), so a
    real backend keys on the same identity the executor already uses.
    """

    job_id: str
    run_id: str
    shard_id: str
    payload_ref: str
    assigned_worker_id: str | None = None  # None => any compatible worker (03 work-stealing)
    not_before: str | None = None          # backoff gate; not leasable until this instant
    attempt: int = 0
    max_attempts: int = 5
    status: JobStatus = "queued"


@dataclass(frozen=True)
class Lease:
    lease_id: str
    job_id: str
    worker_id: str
    deadline: str   # ISO-8601 visibility deadline
    attempt: int


@dataclass(frozen=True)
class Checkpoint:
    run_id: str
    shard_id: str
    cursor: int                       # monotonic progress marker (e.g. last completed layer)
    partial_result_ref: str | None    # 02 ArtifactStore key (sha256:<digest>); None if cursor-only
    created_at: str = field(default_factory=_utc_now_iso)
    schema_version: str = "cas_harness_checkpoint.v1"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 900.0
    jitter_seconds: float = 0.0

    def next_not_before(self, *, attempt: int, now_iso: str) -> str:
        """Exponential backoff gate for the *next* attempt. Pure over (attempt, now).

        ``attempt`` is the attempt that just failed (1-based). The delay is
        ``base * 2**(attempt-1)`` clamped to ``max_backoff_seconds``. Jitter, if
        configured, is deterministic-free here (the stub keeps it 0 for testable
        behavior; a real backend may add bounded randomness to de-synchronize the
        fleet).
        """

        exponent = max(attempt - 1, 0)
        delay = self.base_backoff_seconds * (2 ** exponent)
        delay = min(delay, self.max_backoff_seconds)
        delay = max(delay + self.jitter_seconds, 0.0)
        return (_parse_utc(now_iso) + timedelta(seconds=delay)).isoformat()


@dataclass(frozen=True)
class DeadLetterPolicy:
    """When a job goes straight to the DLQ regardless of remaining attempts.

    The default non-retryable substrings mirror ``FleetExecutorStateError``
    messages a retry can never fix (wrong model, unsupported method —
    ``cas_harness_fleet_executor.py`` ``_assert_worker_can_run_job``): retrying a
    structurally-incompatible worker just burns accelerator-hours.
    """

    non_retryable_error_substrings: tuple[str, ...] = (
        "model_id does not match",
        "does not support assigned methods",
    )

    def should_dead_letter(
        self, *, attempt: int, max_attempts: int, error_message: str | None
    ) -> bool:
        if error_message:
            lowered = error_message.lower()
            for needle in self.non_retryable_error_substrings:
                if needle.lower() in lowered:
                    return True
        return attempt >= max_attempts


@dataclass(frozen=True)
class DeadLetterRecord:
    job_id: str
    run_id: str
    shard_id: str
    final_attempt: int
    error_history: tuple[str, ...]
    dead_lettered_at: str = field(default_factory=_utc_now_iso)


class DurableQueue(Protocol):
    """The seam a real durable broker must implement.

    A real backend (Postgres ``FOR UPDATE SKIP LOCKED`` / SQS / Redis Streams)
    drops in here; the in-process executor's leasing delegates to this Protocol.
    """

    @property
    def delivery_guarantee(self) -> DeliveryGuarantee: ...

    def enqueue(self, job: QueueJob) -> str: ...

    def lease(self, *, run_id: str, worker_id: str, lease_seconds: int = 900) -> Lease | None: ...

    def ack(self, *, lease_id: str, idempotency_key: str) -> bool: ...

    def nack(
        self,
        *,
        lease_id: str,
        error_message: str,
        retry: RetryPolicy,
        dlq: DeadLetterPolicy,
    ) -> JobStatus: ...

    def extend_lease(self, *, lease_id: str, lease_seconds: int = 900) -> Lease | None: ...

    def reap_expired(self, *, now_iso: str | None = None) -> Sequence[str]: ...

    def checkpoint(self, ckpt: Checkpoint) -> bool: ...

    def latest_checkpoint(self, *, run_id: str, shard_id: str) -> Checkpoint | None: ...

    def list_dead_letters(self, *, run_id: str) -> Sequence[DeadLetterRecord]: ...

    def requeue_dead_letter(self, *, job_id: str) -> bool: ...


@dataclass
class _LeaseState:
    lease_id: str
    worker_id: str
    deadline: str
    attempt: int


class InMemoryQueueStub:
    """NON-DURABLE in-memory stub. NOT a production queue.

    Re-implements the fleet executor's lease/ack/expire semantics behind
    :class:`DurableQueue` so the contract is exercisable without a broker. It is
    honest about exactly one thing it can prove in-process — single-holder
    leasing with token validation, time-boxed visibility, process-local replay
    protection, monotonic checkpoints, backoff, and dead-lettering — and honest
    about what it CANNOT provide: durability, cross-process/replica safety, or
    any committed/verified status.

    ``delivery_guarantee`` is hard-coded to ``"none_process_local"``. This stub
    MUST NEVER be swapped in where a caller would read its status as a durable or
    verified guarantee.
    """

    #: Stable, machine-checkable marker so callers/tests can assert this is a stub
    #: and never mistake it for a real durable backend.
    is_durable: bool = False
    backend_kind: str = "in_memory_stub"

    def __init__(self) -> None:
        self._jobs: dict[str, QueueJob] = {}
        self._leases: dict[str, _LeaseState] = {}      # job_id -> active lease
        self._lease_index: dict[str, str] = {}         # lease_id -> job_id
        self._acked_keys: set[str] = set()             # process-local replay protection
        self._ack_by_lease: dict[str, str] = {}        # lease_id -> idempotency_key (idempotent re-ack)
        self._checkpoints: dict[tuple[str, str], Checkpoint] = {}
        self._dead_letters: dict[str, DeadLetterRecord] = {}
        self._error_history: dict[str, list[str]] = {}

    # -- honesty surface ---------------------------------------------------

    @property
    def delivery_guarantee(self) -> DeliveryGuarantee:
        # Hard-coded. A stub in one process's memory cannot honestly promise
        # at-least-once across restarts/replicas.
        return "none_process_local"

    def status_note(self) -> dict[str, object]:
        """Honest self-description. Never claims durability/commit/verification."""

        return {
            "backend_kind": self.backend_kind,
            "is_durable": self.is_durable,
            "delivery_guarantee": self.delivery_guarantee,
            "durably_committed": False,
            "replicated": False,
            "cross_process_safe": False,
            "note": (
                "In-memory stub. State is process-local and lost on restart. "
                "Not a production queue; never reports committed/verified/durable."
            ),
        }

    # -- queue operations --------------------------------------------------

    def enqueue(self, job: QueueJob) -> str:
        if not job.job_id.strip():
            raise QueueResumeError("job_id is required.")
        if not job.run_id.strip():
            raise QueueResumeError("run_id is required.")
        # Idempotent on job_id: re-enqueue of an existing id is a no-op.
        self._jobs.setdefault(job.job_id, job)
        self._error_history.setdefault(job.job_id, [])
        return job.job_id

    def lease(self, *, run_id: str, worker_id: str, lease_seconds: int = 900) -> Lease | None:
        if lease_seconds <= 0:
            raise QueueResumeError("lease_seconds must be positive.")
        if not worker_id.strip():
            raise QueueResumeError("worker_id is required.")
        self.reap_expired()
        now = datetime.now(UTC)
        candidates = [
            job
            for job in self._jobs.values()
            if job.run_id == run_id
            and job.status in {"queued", "failed"}
            and job.job_id not in self._leases
            and (job.assigned_worker_id in (None, worker_id))
            and job.attempt < job.max_attempts
            and self._not_before_ok(job, now)
        ]
        if not candidates:
            return None
        # Oldest-first by job_id for deterministic, starvation-free selection in
        # the stub. (A real backend orders by enqueue time / priority.)
        job = sorted(candidates, key=lambda j: j.job_id)[0]
        attempt = job.attempt + 1
        lease_id = uuid4().hex
        deadline = (now + timedelta(seconds=lease_seconds)).isoformat()
        self._jobs[job.job_id] = replace(job, status="leased", attempt=attempt)
        self._leases[job.job_id] = _LeaseState(
            lease_id=lease_id, worker_id=worker_id, deadline=deadline, attempt=attempt
        )
        self._lease_index[lease_id] = job.job_id
        return Lease(
            lease_id=lease_id,
            job_id=job.job_id,
            worker_id=worker_id,
            deadline=deadline,
            attempt=attempt,
        )

    def ack(self, *, lease_id: str, idempotency_key: str) -> bool:
        if not idempotency_key.strip():
            raise QueueResumeError("idempotency_key is required (the content-addressed fragment ref).")
        # Idempotent re-ack of the SAME lease is a no-op (returns False = already done),
        # never an error.
        if lease_id in self._ack_by_lease:
            return False
        job_id = self._lease_index.get(lease_id)
        if job_id is None:
            # Lease expired/reclaimed or never existed. Honest: cannot ack.
            raise QueueResumeError("ack requires an active lease.")
        # Durable analog of the executor's _FRAGMENT_REFS replay check — but
        # process-local here; a real backend persists this index.
        if idempotency_key in self._acked_keys:
            # A different lease already committed this exact result. Drop the
            # duplicate (at-least-once delivery, exactly-once effect).
            self._finalize_acked(lease_id, job_id, idempotency_key, first=False)
            return False
        self._finalize_acked(lease_id, job_id, idempotency_key, first=True)
        return True

    def _finalize_acked(self, lease_id: str, job_id: str, idempotency_key: str, *, first: bool) -> None:
        self._acked_keys.add(idempotency_key)
        self._ack_by_lease[lease_id] = idempotency_key
        job = self._jobs.get(job_id)
        if job is not None:
            self._jobs[job_id] = replace(job, status="completed")
        self._leases.pop(job_id, None)

    def nack(
        self,
        *,
        lease_id: str,
        error_message: str,
        retry: RetryPolicy,
        dlq: DeadLetterPolicy,
    ) -> JobStatus:
        if not error_message.strip():
            raise QueueResumeError("nack requires a non-empty error_message.")
        job_id = self._lease_index.get(lease_id)
        if job_id is None:
            raise QueueResumeError("nack requires an active lease.")
        job = self._jobs[job_id]
        history = self._error_history.setdefault(job_id, [])
        history.append(error_message.strip())
        self._leases.pop(job_id, None)
        self._lease_index.pop(lease_id, None)

        if dlq.should_dead_letter(
            attempt=job.attempt, max_attempts=job.max_attempts, error_message=error_message
        ):
            self._jobs[job_id] = replace(job, status="dead_letter")
            self._dead_letters[job_id] = DeadLetterRecord(
                job_id=job_id,
                run_id=job.run_id,
                shard_id=job.shard_id,
                final_attempt=job.attempt,
                error_history=tuple(history),
            )
            return "dead_letter"

        not_before = retry.next_not_before(attempt=job.attempt, now_iso=_utc_now_iso())
        self._jobs[job_id] = replace(job, status="failed", not_before=not_before)
        return "failed"

    def extend_lease(self, *, lease_id: str, lease_seconds: int = 900) -> Lease | None:
        if lease_seconds <= 0:
            raise QueueResumeError("lease_seconds must be positive.")
        job_id = self._lease_index.get(lease_id)
        if job_id is None:
            return None
        lease = self._leases.get(job_id)
        if lease is None or lease.lease_id != lease_id:
            return None
        # If already past deadline, the reaper owns it — do not silently revive.
        if _parse_utc(lease.deadline) < datetime.now(UTC):
            return None
        new_deadline = (datetime.now(UTC) + timedelta(seconds=lease_seconds)).isoformat()
        lease.deadline = new_deadline
        return Lease(
            lease_id=lease.lease_id,
            job_id=job_id,
            worker_id=lease.worker_id,
            deadline=new_deadline,
            attempt=lease.attempt,
        )

    def reap_expired(self, *, now_iso: str | None = None) -> Sequence[str]:
        now = _parse_utc(now_iso) if now_iso else datetime.now(UTC)
        reclaimed: list[str] = []
        for job_id, lease in list(self._leases.items()):
            if _parse_utc(lease.deadline) < now:
                self._leases.pop(job_id, None)
                self._lease_index.pop(lease.lease_id, None)
                job = self._jobs.get(job_id)
                if job is not None and job.status == "leased":
                    # Keep attempt count (this attempt was spent); make re-leasable.
                    self._jobs[job_id] = replace(job, status="queued")
                    reclaimed.append(job_id)
        return reclaimed

    def checkpoint(self, ckpt: Checkpoint) -> bool:
        key = (ckpt.run_id, ckpt.shard_id)
        existing = self._checkpoints.get(key)
        # Monotonic: no rewind. A cursor at or behind the stored one is refused.
        if existing is not None and ckpt.cursor <= existing.cursor:
            return False
        self._checkpoints[key] = ckpt
        return True

    def latest_checkpoint(self, *, run_id: str, shard_id: str) -> Checkpoint | None:
        return self._checkpoints.get((run_id, shard_id))

    def list_dead_letters(self, *, run_id: str) -> Sequence[DeadLetterRecord]:
        return [rec for rec in self._dead_letters.values() if rec.run_id == run_id]

    def requeue_dead_letter(self, *, job_id: str) -> bool:
        rec = self._dead_letters.pop(job_id, None)
        if rec is None:
            return False
        job = self._jobs.get(job_id)
        if job is None:
            return False
        # Operator action: reset attempts and clear the backoff gate.
        self._jobs[job_id] = replace(job, status="queued", attempt=0, not_before=None)
        return True

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _not_before_ok(job: QueueJob, now: datetime) -> bool:
        if job.not_before is None:
            return True
        return _parse_utc(job.not_before) <= now


# Static guarantee: the stub must never accidentally advertise durability.
assert InMemoryQueueStub.is_durable is False
