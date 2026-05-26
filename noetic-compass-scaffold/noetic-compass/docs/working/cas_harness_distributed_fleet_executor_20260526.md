# CAS Harness Distributed Fleet Executor

Date: 2026-05-26
Scope: open-weight / internal-access CAS Harness audits for large models.

## Purpose

The scale planner answers: "How many Probe Workers do we need?"

The distributed audit control plane answers: "Which layer or tensor-shard job is each worker responsible for?"

The fleet executor answers: "Did real workers register, lease those jobs, stay alive, and return Evidence Packet fragments?"

No 20B/100B/300B run should move forward from a plan alone. A run moves forward only when assigned workers return receipts.

## Core Objects

### Worker Registry

Each Probe Worker registers:

- `worker_id`
- `model_id`
- `worker_url`
- `gpu_type`
- `capacity`
- `supported_methods`
- `last_heartbeat_at`

If a worker is not registered, it cannot lease a job.

### Job Lease

Each distributed audit assignment becomes a fleet job:

- `job_id`
- `audit_id`
- assigned worker
- layer range
- shard id
- assigned CAS methods
- expected outputs
- lease token
- lease expiry

The lease token prevents a different worker from submitting a receipt for a job it does not own.

### Heartbeat

Workers must heartbeat while running. Stale workers block verifier readiness. This prevents a dead worker from looking like a valid part of a 300B run.

### Evidence Fragment Receipt

A completed job must return an `evidence_packet_fragment_ref`.

Failed jobs may return zero outputs, but must return an `error_message`.

The receipt records:

- produced outputs
- missing outputs
- packet fragment reference
- failure message if failed

## Merge Gate

Fleet evidence can merge only after every assigned job has a completed receipt.

The merge gate blocks when:

- workers are not registered
- workers are stale
- jobs are not leased
- receipts are missing
- required outputs are missing
- a worker failed

When all fragments are present, the fleet executor marks the run `ready_for_verifier`. It still does not fabricate `ACCEPT`.

## Verifier Gate

The verifier decision layer is the only layer allowed to turn a merged Evidence Packet into:

- `ACCEPT`
- `SUPPRESS`
- `FLAG_FOR_HUMAN_REVIEW`

The fleet executor's job is to prove that the distributed evidence exists and is complete enough for verifier review.

## 512 Worker Cap

The planner supports up to 512 Probe Workers today.

For 300B models, the planner can create more workers than layers by splitting layers into tensor-shard jobs. Example: a 160-layer 300B model can request 300 workers, producing layer-level tensor-shard jobs instead of pretending one worker owns an impossible full-model audit.

Requests above 512 workers are intentionally rejected until the scheduler, storage, and monitoring plane are expanded.

## Non-Negotiable Boundary

This lane supports open-weight or internal-telemetry audits only.

It does not perform black-box API-only audits.

It does not claim a 300B audit happened unless real workers registered, leased jobs, returned Evidence Packet fragments, and passed the merge gate.
