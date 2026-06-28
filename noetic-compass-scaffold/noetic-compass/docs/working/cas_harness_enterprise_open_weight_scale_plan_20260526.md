# CAS Harness Enterprise Open-Weight Scale Plan - May 26, 2026

## Objective

Scale CAS Harness from a reference Atlas / Audit Console path into enterprise open-weight audit infrastructure. The target workflow is simple:

1. Customer selects or attaches a supported open-weight model.
2. CAS Harness runs instrumented probes, ablations, controls, and output checks.
3. Atlas Viewer shows the trace and verdict.
4. The run emits one final Evidence Packet.
5. Enterprise reviewer gets one verdict: `ACCEPT`, `SUPPRESS`, or `FLAG`.

The product does not need black-box coverage to be valuable. It needs strong open-weight coverage, credible internal evidence, reproducible packet export, and cost-controlled execution.

## Product Scope

In scope:

- Open-weight models with inspectable weights or supported runtime hooks.
- Hidden-state capture by layer, shard, token position, and run phase.
- Activation probes for CAS signals.
- Ablation and matched-control jobs to test causality rather than correlation alone.
- Output proof that connects internal evidence to emitted text, token, claim, or step.
- Evidence Packet generation with tamper-evident integrity metadata.
- Atlas Viewer as the UI for setup, trace inspection, verdict review, and packet export.

Out of scope for the current push:

- Closed black-box API models where internal activations are unavailable.
- Generic prompt firewall positioning.
- Universal model support.
- Claims of legal, safety, or regulatory certification.

## Target Scale Band

The enterprise architecture should be designed for 20B-300B open-weight models.

That band changes the system design:

- Single-process probe execution is not enough.
- Activation capture must be selective, streamed, compressed, and tiered by retention policy.
- Layer and shard parallelism are required.
- Cost estimates and abort thresholds must be visible before execution.
- Every partial, degraded, or failed run must still produce an interpretable packet status.

## Architecture

### Control Plane

CAS Orchestrator owns the audit run.

Responsibilities:

- Validate customer entitlement, model access, and supported architecture band.
- Resolve model metadata, tokenizer, layer map, shard map, and adapter version.
- Build the audit plan: probes, layer ranges, ablations, controls, output checks, budgets, and stop conditions.
- Dispatch work to Probe Workers by layer, shard, probe type, and run phase.
- Track run state: queued, running, completing, completed, failed, canceled, or degraded.
- Aggregate worker outputs into one verdict runner.
- Emit one final Evidence Packet.

### Data Plane

Probe Workers execute the heavy model-facing work.

Worker types:

- Hidden-state workers: capture selected activations and residual stream slices.
- Probe workers: run CAS signal probes over selected layers and token positions.
- Ablation workers: perform targeted neuron, feature, head, or channel interventions.
- Control workers: run matched controls to separate signal from artifact.
- Output-proof workers: align internal evidence with output tokens, claims, or steps.
- Packet workers: canonicalize artifacts, hash outputs, and assemble packet rows.

Partitioning strategy:

- By model shard where tensor parallelism or pipeline parallelism is already present.
- By layer band for probe sweeps.
- By intervention set for ablation/control batches.
- By token or claim span for output-proof alignment.

The orchestrator does not need every raw activation in memory. It needs normalized worker summaries, artifact references, confidence inputs, error states, and enough provenance to reconstruct the audit.

## Run Contract

Every enterprise audit run produces:

- One `trace_id`.
- One model subject record.
- One audit config.
- One artifact manifest.
- One verdict table.
- One confidence record.
- One Evidence Packet.
- One final run status.

Verdict semantics:

- `ACCEPT`: required evidence exists, confidence clears threshold, controls did not invalidate the signal, and provenance links resolve.
- `SUPPRESS`: validated failure condition or suppressing evidence class is present.
- `FLAG`: evidence is missing, low-confidence, degraded, unsupported, contradictory, or requires human review.

Release rule: unsupported, partial, stale, or low-confidence evidence cannot become `ACCEPT`.

## Evidence Packet

The Evidence Packet is the audit artifact, not a screenshot.

Minimum enterprise packet contents:

- Model subject: provider, model ID, version, parameter band, adapter, architecture status.
- Runtime metadata: hardware class, shard plan, quantization state if any, precision, tokenizer.
- Audit config: probe versions, layer ranges, thresholds, ablation plan, control plan, output-proof config.
- Verdict: `ACCEPT`, `SUPPRESS`, or `FLAG`.
- Confidence: numeric or banded score with calibration version.
- Reason codes and proof chips.
- Component scores and pass/fail outcomes.
- Artifact manifest with hashes and storage references.
- Errors, skipped probes, degraded-mode markers, and timeout reasons.
- Packet hash, append-only log reference, and optional Merkle or WORM anchor.

Atlas Viewer should display the packet, but the packet must remain useful without Atlas.

## 20B-300B Execution Pattern

1. Intake
   - User selects supported model or requests adapter review.
   - Orchestrator labels the model `Validated`, `Exploratory`, or `Refused`.
   - UI shows estimated time, cost, required artifacts, and max budget.

2. Plan
   - Orchestrator selects probe set and layer coverage.
   - For large models, default to tiered coverage: sentinel layers first, then targeted expansion.
   - Abort early if architecture, memory, or credential checks fail.

3. Capture
   - Workers capture hidden states and activations only where needed.
   - Raw tensors are short-lived unless the audit config explicitly requires retention.
   - Summaries and artifact hashes are retained in the packet path.

4. Intervene
   - Ablation workers test target features or circuits.
   - Control workers run matched negative controls.
   - Failed or missing controls degrade verdicts to `FLAG` unless a suppress rule applies.

5. Align
   - Output-proof workers connect internal evidence to output tokens, claims, or steps.
   - Atlas renders this as trace evidence, but the packet stores the authority.

6. Decide
   - Verdict runner combines evidence, thresholds, controls, and error states.
   - The output is one verdict table and one final packet.

## Enterprise Requirements

- Tenant isolation for credentials, prompts, artifacts, and packet access.
- Budget controls before heavy GPU jobs start.
- Queue visibility and cancellation.
- Reproducible adapter versions and method versions.
- Packet retention policy by customer tier.
- Tamper-evident packet log.
- Refusal path for unsupported architectures.
- Degraded-mode path that never hides missing evidence.
- API and UI semantic parity.

## AI2 Help Needed

- Compute credits for 20B-300B open-weight audit runs and stress tests.
- Model-hosting guidance for activation capture without runaway memory and storage cost.
- Systems architecture review for orchestrator, worker partitioning, artifact storage, and packet integrity.
- Enterprise design partners with real governance workflows and open-weight deployment needs.
- Go-to-market support: ICP, buyer, budget owner, procurement blockers, and proof threshold.

## Honest Limitations

- The current live path proves Evidence Packet-backed `ACCEPT` for the Atlas / Audit Console reference path; customer open-weight execution is next.
- 20B-300B support will require serious systems work, not just UI changes.
- Some model families will need custom adapters before they can be validated.
- CAS evidence is bounded by the configured probes, ablations, controls, thresholds, and captured runtime state.
- Evidence Packets prove the audit record and CAS verdict, not universal model safety.

## First Validation Sprint

Recommended AI2-backed sprint:

- Pick two open-weight model families and one size band each.
- Define three enterprise audit scenarios that require internal evidence, not just output scoring.
- Run CAS Orchestrator prototype with layer-banded Probe Workers.
- Emit one packet per run with explicit `ACCEPT`, `SUPPRESS`, or `FLAG`.
- Review packet quality with AI2 systems, interpretability, and enterprise stakeholders.
- Decide whether the architecture merits a larger 20B-300B buildout.
