# CAS Harness — Public Production Readiness Program

**Status:** design + gap blueprints, produced in parallel. Not yet implemented.
**Date opened:** Jun 1, 2026

## Why this program exists

The 8-gate **honesty gate series** is complete: a distributed CAS Harness audit run is
*refused* (HTTP 422) unless every precondition is honestly acknowledged —

1. risk acknowledgment · 2. open-weight access (universal) · 3. compute feasibility ·
4. cost acknowledgment · 5. provenance manifest · 6. architecture adapter ·
7. probe compatibility · 8. data-capture acknowledgment (universal)

— and the system **never claims `*_VERIFIED` / `*_METERED` / `*_WORM_COMMITTED` at the API
tier**; only the fleet/worker side verifies, meters, and commits. That closed a major
**product/honesty** gate.

It is **not** the same as **public production readiness**. The honest tri-states the gate
series defines (e.g. `DATA_CAPTURE_WORM_COMMITTED`, `COST_METERED`, `MODEL_ACCESS_VERIFIED`)
are *promises the fleet must actually keep*. Making those promises real — at scale, for many
tenants, durably, observably, billably, and compliantly — is the work below.

## The honesty ethos (governs every workstream)

- **Declared vs verified is sacred.** A status may only be produced where the real thing
  actually happened. The API tier declares/acknowledges; the fleet/worker verifies, meters,
  commits.
- **Show your work, or don't ship it.** Traceability is the spine: every object/decision walks
  back to its origin.
- **No fabricated production.** Where real infra is required (S3 Object Lock, a payment
  provider, a durable queue, an OTLP backend), define the interface, ship a clearly-labeled
  stub for tests, and document exactly what flips the honest status to true in production.

## The nine workstreams

| # | Workstream | One-line scope | Doc |
|---|---|---|---|
| 01 | Worker-side verification upgrades | Turn `*_DECLARED` → `*_VERIFIED`: real activation capture, deterministic hashing, attestation, tamper-evidence | `01_worker_side_verification.md` |
| 02 | Large artifact object storage | Where captured activations/readouts/packets physically land: content-addressed, multipart, lifecycle | `02_large_artifact_object_storage.md` |
| 03 | Fleet execution at scale | Scheduler, autoscaling, shard placement, backpressure, liveness beyond the 512-worker fan-out cap | `03_fleet_execution_at_scale.md` |
| 04 | Queue / resume | Durable job queue, idempotent leasing, checkpoint/resume of partial runs, dead-letter/retry | `04_queue_and_resume.md` |
| 05 | Observability | Structured logs, metrics, traces, per-stage timing, SLOs, run dashboards, traceability surfaces | `05_observability.md` |
| 06 | Tenant isolation | Multi-tenancy boundaries, per-tenant data partitioning + keys + quotas, noisy-neighbor isolation | `06_tenant_isolation.md` |
| 07 | Production WORM writes | The real immutable write that flips `DATA_CAPTURE_WORM_COMMITTED`: Object Lock, retention, legal hold | `07_production_worm_writes.md` |
| 08 | Billing / accounts | Accounts, real accelerator-hour metering (`COST_METERED`), usage → invoicing, quotas | `08_billing_and_accounts.md` |
| 09 | Compliance | Consent records, retention/redaction vs write-once tension, residency, audit trails, certifications | `09_compliance.md` |

## Dependency sketch

- **07 (WORM)** sits on **02 (object storage)** and consumes **01 (verification)** evidence.
- **08 (billing)** consumes **05 (observability)** metering and **03 (fleet)** consumption signal.
- **06 (tenant isolation)** is a cross-cut: 02/07 partition data by tenant; 03/04 schedule by tenant; 08 bills per tenant; 09 audits per tenant.
- **04 (queue/resume)** underpins **03 (fleet at scale)**.
- **09 (compliance)** governs the consent → capture → WORM retention chain that gate 8 (`cas_harness_data_governance.py`) opens.
