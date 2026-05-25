# CAS Harness M1 Evidence Packet Bridge

**Date:** 2026-05-25
**Scope:** Bridge plan from M1 audit sessions to Evidence Packet v1
**Status:** Implementation plan, not a signed/compliance claim

## Purpose

M1 makes CAS Harness audit sessions real enough to persist, refresh, and resume. The Evidence Packet bridge defines what each session must save so M2 can export a defensible packet without inventing proof after the fact.

Plain English:

> The audit session is the live work record. The Evidence Packet is the receipt.

The packet should never contain a stronger claim than the session actually earned. If a run used scaffolded evidence, missing trace data, fallback labels, or proxy metrics, the packet must say that directly.

## M1 To M2 Bridge Rule

M1 must persist enough structured evidence that M2 can export the same truth later.

Do not make M2 reconstruct critical facts from UI state, logs, browser memory, or screenshots. The packet exporter should read session records and assemble them.

## Fields An Audit Session Must Persist

### Session Header

Required before packet export:

- `audit_id`
- `created_at`
- `updated_at`
- `created_by_user_id` or service account reference
- `license_id` or invite/license proof reference
- `tenant_id` or customer/account boundary
- `status`
- `mode`: `BALANCED`, `HIGH_PRECISION`, or `MAX_COVERAGE_TRIAGE`
- `run_profile_version`
- `cas_harness_version`
- `api_version`

Why it matters:

The packet needs to prove which run produced the verdict and under which product mode.

### Model Record

Required before packet export:

- `model_id`
- `model_provider`
- `model_endpoint_kind`: hosted reference, customer API, uploaded model, RunPod worker, or other connector
- `model_weight_proof_status`
- `model_weight_proof_detail`
- `is_real_model`
- `fake_runtime_env`
- `model_loaded`
- `load_error`
- `adapter_name`
- `adapter_version`
- `adapter_support_level`: validated, exploratory, request_adapter, refused
- `model_config_hash` when available

Why it matters:

This prevents a replay, fixture, unavailable worker, or unvalidated connector from being described as a real completed model audit.

### Scenario And Input Record

Required before packet export:

- `scenario_id`
- `scenario_pack_id`
- `scenario_pack_version`
- `prompt_text` or redacted prompt reference
- `input_hash`
- `policy_profile_id`
- `policy_profile_version`
- `customer_policy_overrides`
- `expected_cas_axes` when supplied by the scenario pack

Why it matters:

The same model can pass one scenario and fail another. The packet must identify the actual test.

### Run Configuration

Required before packet export:

- enabled methods
- method knobs
- layer range
- target drive or drive scope
- threshold values
- max tokens
- random seed when used
- worker URL or worker identity reference
- timeout settings
- fallback policy

Why it matters:

If the side panel controls affect the worker, the session must persist exactly what was turned on and which values were used.

### Runtime Events

Required before packet export where available:

- manifest event
- token events
- word span events
- neuron cover events
- blindspot interpretation events
- verification telemetry
- complete event
- error event if failed

Each event needs:

- event type
- event sequence number
- event timestamp
- source component
- payload hash
- raw payload reference or stored payload

Why it matters:

The packet needs to show whether verdict evidence came from a real runtime stream, an offline trace, or no trace at all.

### Verdict Rows

Required before packet export:

- `item_id`
- `output_text` or redacted output reference
- `verdict`: `ACCEPT`, `SUPPRESS`, or `FLAG_FOR_HUMAN_REVIEW`
- `confidence`
- `confidence_band`
- `reason_summary`
- `policy_match`
- `behavioral_signal`
- `scenario_anchor`
- `trace_evidence_status`
- `confidence_basis`
- `reviewer_context`
- `review_required`
- `human_override_status`
- `human_override_reason`

Why it matters:

This is the operational result. The packet should be able to reproduce the table a user saw in the audit console.

### Evidence References

Required before packet export:

- `evidence_ref`
- `evidence_type`
- `source_trace_id`
- `source_token_indices`
- `source_word_span_id`
- `source_layer`
- `source_neuron_cover`
- `source_method`
- `metric_name`
- `metric_value`
- `metric_unit`
- `availability`: available, unavailable, not_collected, not_applicable, scaffold

Why it matters:

Evidence must be addressable. "The UI showed a red marker" is not enough.

### Export Metadata

Required for M2 export:

- packet schema version
- export timestamp
- exporter version
- included artifact list
- missing artifact list
- known limitations
- hash manifest
- signature status

Why it matters:

This separates a normal packet export from a signed/compliance-grade artifact.

## Live Atlas Evidence Vs Audit Verdict Evidence

These are related, but they are not the same thing.

### Live Atlas Evidence

Live Atlas evidence answers:

> What happened inside this supported run while the model processed tokens?

Examples:

- realmodel health proof
- token stream
- word spans
- token-level top neurons
- layer/neuron activity
- Mode 7 attention path
- blindspot cover overlap
- visual grounding primitives when available

Use it for:

- deep inspection
- debugging
- stakeholder demonstration
- explaining a verdict path when trace data exists

Do not use it alone to claim:

- the whole model is safe
- all model families are supported
- a blindspot is proven without calibrated scoring
- a compliance-grade packet exists

### Audit Verdict Evidence

Audit verdict evidence answers:

> Should this output be accepted, suppressed, or sent to human review under this audit policy?

Examples:

- scenario rule matched
- CAS readout score
- verification verdict
- confidence margin
- causal or control evidence reference
- model proof status
- reviewer override state

Use it for:

- product verdicts
- audit tables
- exported packets
- customer reporting
- allow/block/review workflow

### Bridge Rule

Atlas evidence can support an audit verdict only when the session stores a stable reference from verdict row to trace evidence.

Required linkage:

- verdict row has `trace_evidence_status`
- verdict row has one or more `evidence_ref` values
- each `evidence_ref` resolves to stored runtime event data or a packet artifact
- missing trace data is labeled `not_collected`, `unavailable`, or `scaffold`

## Six Provenance Chips To Packet Fields

### 1. Model Proof

Packet fields:

- `model_id`
- `model_provider`
- `model_weight_proof_status`
- `is_real_model`
- `fake_runtime_env`
- `model_loaded`
- `load_error`
- `adapter_support_level`

Plain English:

This proves what model was tested and whether it was really loaded.

### 2. CAS Readout

Packet fields:

- `cas_readout_method`
- `cas_readout_version`
- `cas_axes`
- `layer_range`
- `readout_score`
- `readout_confidence`
- `readout_availability`

Plain English:

This shows whether CAS could read the relevant internal signal.

### 3. Causal Proof

Packet fields:

- `intervention_method`
- `intervention_target`
- `intervention_strength`
- `pre_intervention_metric`
- `post_intervention_metric`
- `observed_shift`
- `causal_availability`

Plain English:

This shows whether changing the CAS-linked internal part changed model behavior.

### 4. Control Proof

Packet fields:

- `control_method`
- `control_target`
- `control_metric`
- `control_result`
- `matched_control_count`
- `control_availability`

Plain English:

This shows whether random or wrong-target changes failed to explain the result.

### 5. Output Proof

Packet fields:

- `output_text` or redacted reference
- `output_hash`
- `verdict`
- `confidence`
- `confidence_basis`
- `verification_margin`
- `accept_suppress_signal`

Plain English:

This connects the CAS evidence to the actual output routing decision.

### 6. Packet Proof

Packet fields:

- `packet_schema_version`
- `packet_hash`
- `manifest_hash`
- `signature_status`
- `exporter_version`
- `artifact_list`
- `limitations`

Plain English:

This proves the evidence was packaged consistently and shows whether it was signed.

## Minimum Evidence Packet v1 Shape

M2 packet export should include:

1. Packet header
2. Session header
3. Model record
4. Scenario and policy record
5. Run configuration
6. Verdict summary
7. Per-item verdict rows
8. Provenance chip details
9. Evidence references
10. Runtime event references where available
11. Missing or unavailable evidence list
12. Known limitations
13. Hash manifest
14. Signature status

## What Is Still Missing Before Signed Or Compliance-Grade Claims

Do not call the packet compliance-grade until these exist:

- stable packet schema version with migration policy
- durable session storage
- durable artifact storage
- hash manifest generated from actual exported artifacts
- signing key management
- signature verification endpoint or CLI
- tenant isolation review
- access control review
- retention and deletion policy
- secret redaction policy
- customer data handling review
- legal/IP review
- external reviewer checklist

Do not call blindspot interpretations calibrated until these exist:

- per-drive cover calibration beyond current supported runtime scope
- per-neuron or per-cover confidence source wired into the worker
- confidence calculation documented
- matched controls for confidence bands
- tests showing unavailable confidence cannot appear as a numeric score

Do not call arbitrary external model support complete until these exist:

- connector validation
- adapter registry
- model-family support levels
- model config discovery
- failure modes that are visible to users
- per-adapter test suite

## M1.1 Implementation Checkpoints

Goal: make audit sessions persist enough truth for packet export later.

Deliverables:

- Create audit session storage model.
- Persist model record fields.
- Persist scenario and policy fields.
- Persist run configuration.
- Persist status transitions.
- Persist verdict rows with null verdict/confidence until computed.
- Persist provenance chip placeholders with explicit availability states.
- Add API endpoints:
  - `POST /api/cas-harness/audit/session`
  - `GET /api/cas-harness/audit/session/{audit_id}`
  - `GET /api/cas-harness/audit/session/{audit_id}/status`
  - `GET /api/cas-harness/audit/session`

Exit criteria:

- A user can create a session, refresh the page, and see the same session state.
- Scaffolded evidence is stored as scaffolded, not silently treated as real.
- No packet export yet claims signing or compliance readiness.

## M1.2 Implementation Checkpoints

Goal: connect session rows to real evidence where available.

Deliverables:

- Add evidence reference table or JSON field.
- Store live worker realmode proof with the session.
- Store trace IDs when Atlas evidence exists.
- Store token/word/layer/neuron references where available.
- Store unavailable evidence states explicitly.
- Wire the Audit Console frontend to read persisted session status.
- Add a "View packet preview" screen that is clearly labeled preview.

Exit criteria:

- Every verdict row can explain which evidence exists and which evidence is missing.
- The UI can show "not collected" and "unavailable" without hiding the row.
- Atlas links only appear when a trace reference exists.

## M2 Implementation Checkpoints

Goal: export Evidence Packet v1 from persisted audit sessions.

Deliverables:

- Define packet schema v1.
- Implement JSON exporter.
- Implement Markdown report exporter.
- Implement manifest generator.
- Implement hash manifest.
- Add signature status field, even if unsigned at first.
- Add packet validation tests.
- Add export endpoint:
  - `GET /api/cas-harness/audit/session/{audit_id}/evidence-packet`

Exit criteria:

- Packet can be exported from stored session data.
- Packet marks missing and scaffolded evidence honestly.
- Packet has a stable schema version.
- Packet has a hash manifest.
- Packet does not claim legal/compliance-grade signature until signing is actually implemented.

## Investor-Safe Product Line

Use this:

> CAS Harness creates an audit session for a model output, assigns an operational verdict, records confidence and provenance, and exports an Evidence Packet showing what was tested, what evidence was available, and what still needs review.

Avoid this until M2 signing and review are complete:

> CAS Harness produces compliance-certified proof.

## Engineering Priority

Build in this order:

1. Persist sessions.
2. Persist evidence references.
3. Connect frontend to session state.
4. Add packet preview.
5. Add packet export.
6. Add hashing.
7. Add signing.

Reason:

The packet can only be as trustworthy as the session record underneath it.
