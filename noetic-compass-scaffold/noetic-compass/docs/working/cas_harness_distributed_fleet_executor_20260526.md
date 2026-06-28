# CAS Harness Distributed Fleet Executor

Date: 2026-05-26
Status: next implementation phase

## Purpose

The distributed fleet executor turns the current 20B/100B/300B scale plan into a real audit run. It is for open-weight or internal-access model audits where CAS Harness can inspect model weights, hidden states, activations, and worker-produced evidence. It is not a black-box prompt-only audit.

This phase must not fake a 300B run. A 300B audit is valid only when real Probe Workers are assigned, execute their shard/layer work, and return evidence receipts. Missing workers, missing receipts, failed workers, or missing required outputs must block `ACCEPT` and route the run to `FLAG_FOR_HUMAN_REVIEW` or pending state.

## Core Pieces

### Worker Registry

Each Probe Worker must register before it can receive work. The registry should track:

- `worker_id`
- GPU type and memory
- loaded model or model shard
- assigned layer range or tensor shard
- current status: `available`, `leased`, `running`, `completed`, `failed`, `stale`
- last heartbeat timestamp

The registry is the source of truth for whether enough real workers exist for the requested audit.

### Job Leasing

The orchestrator assigns work through leases, not static assumptions. A lease binds one worker to one audit shard for a limited time.

Required behavior:

- Only registered workers can receive leases.
- A lease expires if the worker stops heartbeating.
- Expired work returns to the queue.
- A worker cannot submit evidence for a job it was not leased.
- Dispatch is not proof. Dispatch only means the worker was assigned.

### Heartbeat

Workers must send regular heartbeats while loading weights and running probes. Heartbeats prove the worker is still alive and still owns the lease.

If a worker misses the heartbeat window:

- mark the worker `stale`
- invalidate or pause its lease
- keep the audit from completing
- require retry, replacement, or human review

### Worker Evidence Fragments

Each worker returns an Evidence Packet fragment for its assigned shard/layer range. A completed worker receipt must include:

- `evidence_packet_ref`
- model/shard identity
- layer or tensor-shard assignment
- probe readout outputs
- ablation/intervention outputs when required
- matched-control outputs when required
- blindspot/inversion outputs when required
- hashes for generated artifacts
- missing-output list, if any

A worker receipt without an Evidence Packet reference is not complete.

### Merged Evidence Packet

The orchestrator merges worker fragments into one run-level Evidence Packet. The merged packet should preserve:

- all worker IDs
- all shard/layer assignments
- all fragment hashes
- missing outputs
- failed workers
- merge timestamp
- model identity and audit configuration
- final verifier input bundle

The merge layer should make partial evidence obvious. It must not hide gaps.

### Verifier Gate

The merge step alone cannot emit `ACCEPT` or `SUPPRESS`. The final verdict requires a verifier decision over the merged Evidence Packet.

Allowed merge-only result:

- no verdict yet, or
- `FLAG_FOR_HUMAN_REVIEW` when evidence is incomplete, failed, or not verifier-ready

Only the verifier decision layer can emit:

- `ACCEPT`
- `SUPPRESS`
- `FLAG_FOR_HUMAN_REVIEW`

### 512 Worker Cap

The current hard cap is 512 workers per distributed audit. Requests above 512 must be rejected before dispatch.

This cap is intentional for the first fleet implementation:

- prevents runaway scheduling
- bounds API and UI state size
- keeps worker receipt merging tractable
- gives alpha operators a clear capacity limit

If a 300B audit needs more than 512 workers, the correct response is to reject or split the audit into multiple planned runs. The system must not silently pretend the run is covered.

## Operational Rule

Planner output is not an audit. Dispatch is not an audit. A real distributed CAS Harness audit requires assigned workers, live leases, heartbeats, evidence fragments, a merged Evidence Packet, and a verifier-gated decision.

The product claim should remain simple:

> CAS Harness can audit large open-weight or internally accessible models only when the model is actually available to the worker fleet and the fleet returns auditable evidence. No real workers, no receipts, no 300B claim.
