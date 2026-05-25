# CAS Harness Audit Console Execution Plan

**Date:** 2026-05-25
**Owner:** Agent E documentation/product-copy scope
**Status:** Product-copy and execution plan draft for implementation alignment

## Product Definition

CAS Harness Audit Console is the licensed audit workflow where a user connects their model of choice, CAS evaluates model behavior, and the console returns an operational verdict - **ACCEPT**, **SUPPRESS**, or **FLAG FOR HUMAN REVIEW** - with confidence and five to six provenance-backed reasons.

Atlas is the deep inspection cockpit used when a run, verdict, or stakeholder question needs model-internal evidence. Atlas is not the whole product surface.

## User Flow

1. User signs in with a licensed account or time-limited trial key.
2. User creates an audit session and selects an intake mode:
   - Hosted/reference model already supported by CAS.
   - User-supplied external model endpoint.
   - Uploaded or registered model identifier that needs adapter validation.
3. User chooses a scenario pack, policy profile, and audit mode:
   - Fast triage for high-throughput routing.
   - Balanced audit for default production checks.
   - Deep inspection for Atlas-backed evidence review.
4. User runs the audit and watches session status:
   - Intake validation.
   - Scenario execution.
   - CAS scoring.
   - Provenance assembly.
   - Verdict generation.
5. Console returns one verdict per item or claim:
   - Verdict label.
   - Confidence.
   - Short explanation.
   - Provenance chips.
   - Evidence packet link.
   - Atlas deep-inspection link when available.
6. User acts on the result:
   - ACCEPT: allow output or approve claim.
   - SUPPRESS: block, redact, or withhold output.
   - FLAG FOR HUMAN REVIEW: send to reviewer queue with evidence.
7. User exports the evidence packet for internal audit, partner review, or compliance handoff.

## Main Screens

### 1. Audit Sessions

Purpose: show the operational queue of model audits.

Implementation-ready elements:
- Session list with status, model, scenario pack, policy profile, created time, owner, and current verdict counts.
- Primary actions: **New Audit**, **Open Session**, **Export Report**.
- Status labels: Draft, Validating, Running, Evidence Ready, Review Needed, Complete, Failed.
- Filters: model, verdict, policy profile, date range, confidence band, review owner.

### 2. New Audit

Purpose: configure the model, scenario pack, and audit policy before execution.

Implementation-ready elements:
- Model connector panel: provider, endpoint/model ID, credentials status, adapter status.
- Scenario pack picker: default CAS audit pack, customer pack, regression pack, benchmark pack.
- Policy profile picker: default safety policy, customer policy, strict suppression, review-first.
- Audit mode segmented control: Fast Triage, Balanced Audit, Deep Inspection.
- Run estimate: expected item count, expected latency, whether Atlas inspection is enabled.

### 3. Run Monitor

Purpose: make the audit understandable while it is running without claiming the system has finished analysis early.

Implementation-ready elements:
- Progress timeline: intake, execution, scoring, provenance, verdicts, export.
- Live counters: processed, accepted, suppressed, review flagged, failed.
- Current item drawer with prompt/output preview and provisional status.
- Clear language for partial state: "running", "provisional", "waiting for evidence", "not yet scored".

### 4. Verdict Review

Purpose: the core operator screen for deciding what leaves the system.

Implementation-ready elements:
- Table of audited items with verdict, confidence, provenance chips, model output preview, and reviewer state.
- Detail pane with reason summary, evidence rows, provenance chips, and action buttons.
- Actions: Accept Verdict, Override to Review, Override to Suppress, Add Reviewer Note, Open Atlas.
- Override copy must record that a human changed workflow routing; it must not imply CAS changed its score.

### 5. Evidence Packet

Purpose: package the defensible audit output.

Implementation-ready elements:
- Packet summary: session ID, model, scenario pack, policy profile, verdict distribution, generated time.
- Per-item evidence rows: verdict, confidence, reason, provenance chips, evidence references, reviewer notes.
- Hash/signature area when implemented.
- Export actions: JSON, Markdown, ZIP bundle.

### 6. Atlas Deep Inspection

Purpose: inspect the internal evidence path for selected items, not replace the audit console.

Implementation-ready elements:
- Entry points only from items that have trace/evidence available.
- Copy: "Open in Atlas" or "Inspect evidence path".
- Do not label Atlas as the primary verdict engine unless the backend actually uses it for that run.

### 7. Licensing and Usage

Purpose: expose account readiness without distracting from audit workflow.

Implementation-ready elements:
- License status, plan tier, allowed model slots, monthly runs, API usage, and billing contact.
- Credential health for external model providers.
- Adapter availability by model family.

## Verdict Vocabulary

Use exactly these product verdict labels in the audit console:

- **ACCEPT**: CAS found enough evidence under the active policy profile to allow the model output or claim to proceed.
- **SUPPRESS**: CAS found enough evidence under the active policy profile to block, redact, or withhold the model output or claim.
- **FLAG FOR HUMAN REVIEW**: CAS did not produce a sufficiently clear allow/block decision, or the policy profile requires human review for this item.

Implementation notes:
- Use confidence as a numeric or banded field adjacent to the verdict, not as a substitute verdict.
- Keep "review" separate from "failure"; a review flag is a workflow route.
- Avoid legacy terms like "constrain" in the audit-console verdict layer unless referring to older Atlas/verification documents.
- If Atlas-specific modules still emit ACCEPT / CONSTRAIN / SUPPRESS internally, map them into the console vocabulary before showing the operational verdict.

## Six Provenance Chips

Each verdict should show five to six chips. The target set is six:

1. **Policy Match** - which policy clause, scenario rule, or audit profile drove the verdict.
2. **Behavioral Signal** - the observable model behavior that CAS scored.
3. **Scenario Anchor** - the scenario, test item, or benchmark row used for the audit.
4. **Trace Evidence** - the Atlas or runtime trace reference when available; otherwise mark "not collected".
5. **Confidence Basis** - the scoring basis for the confidence value, such as agreement, margin, or calibration band.
6. **Reviewer Context** - prior reviewer note, override history, customer policy exception, or "none".

Chip behavior:
- Chips are compact labels in table view.
- Chip details expand in the item detail pane.
- Missing provenance must be explicit: "not collected", "not available", or "not applicable".
- Do not silently omit required provenance unless the UI is in a deliberately compact state.

## What Is Real Now vs Scaffolded

### Real Now

- Hosted Atlas Viewer alpha exists as a live cockpit experience.
- Mode 7-style trace playback and 3D/2D evidence surfaces exist in the Atlas viewer.
- Fixture-backed evidence and demo flows exist for showing the inspection concept.
- Login, API key, and license surfaces exist as product scaffolds in the app.
- Testing-method registry and visual method cards exist as product structure.
- Shared API and hosted viewer deployment exist for alpha demonstration.

### Scaffolded or Not Yet Real

- CAS Harness Audit Console as a full verdict workflow is not yet implemented as the primary product surface.
- External customer model intake is not yet a complete production workflow.
- Live CAS verdict generation against arbitrary customer models is not yet production-ready.
- Evidence Packet export is partially represented but not yet a complete signed bundle workflow.
- Atlas deep inspection is available for demonstration and reference traces, not yet every external run.
- Licensing/billing is not yet a complete metered commercial system.
- Multi-model adapters are planned and partially described, not broadly validated across all named model families.

## Non-Overclaiming Language

Use:
- "CAS evaluates model behavior under the selected audit profile."
- "The console returns an operational verdict with confidence and provenance."
- "Atlas provides deep inspection evidence when trace data is available."
- "This alpha demonstrates the intended audit workflow using scaffolded and fixture-backed evidence where marked."
- "External model intake is planned for staged rollout."
- "Evidence packets are designed to be exportable and eventually signed."

Avoid:
- "CAS proves a model is safe."
- "Atlas fully explains the model."
- "Works with any model."
- "Production-ready compliance evidence" before signed packet, policy, and legal review are complete.
- "Real-time live audit" for fixture-backed or replayed traces.
- "Autonomous final decision" when human review is part of the workflow.

Default disclaimer for demo surfaces:

> Alpha surface: some runs use reference traces or scaffolded evidence. Production language should distinguish live API results from replayed or fixture-backed demonstrations.

## Build Phases

### M0 - Scaffold

Goal: create the visible Audit Console shape without implying full backend completeness.

Deliverables:
- Audit Sessions screen with fixture-backed sessions.
- New Audit form with disabled or clearly labeled fields for unsupported intake modes.
- Verdict Review table using ACCEPT / SUPPRESS / FLAG FOR HUMAN REVIEW.
- Six provenance chips represented in UI data.
- Evidence Packet detail view with fixture-backed export placeholders.
- Atlas link from selected records where demo trace exists.
- Copy scrub for non-overclaiming language.

Exit criteria:
- Stakeholder can understand the product in five minutes.
- Every scaffolded state is labeled honestly.
- No code path claims arbitrary external model support.

### M1 - Real API / Session

Goal: move from static console to real session lifecycle.

Deliverables:
- Backend session create/list/get endpoints.
- Session state machine: Draft, Validating, Running, Evidence Ready, Review Needed, Complete, Failed.
- Persisted audit items and verdict rows.
- Real progress updates from API.
- Auth/license gate connected to session creation.

Exit criteria:
- A licensed user can create an audit session and retrieve its persisted results.
- Run state survives page refresh.
- Fixture data is isolated from real sessions.

### M2 - Evidence Packet

Goal: make the audit output portable and reviewable.

Deliverables:
- Evidence packet schema with session, model, policy, scenario, verdict, confidence, provenance, and reviewer fields.
- Markdown and JSON exports.
- ZIP bundle containing packet JSON, human-readable report, and manifest.
- Hash/signature design and first implementation if key management is available.

Exit criteria:
- Each verdict row can be traced to packet evidence.
- Packet clearly marks missing, unavailable, or scaffolded evidence.
- Export can be shared with a stakeholder without relying on the live UI.

### M3 - External Model Intake

Goal: let licensed users connect a non-reference model in a controlled way.

Deliverables:
- Provider/model connector form.
- Credential validation without exposing secrets.
- Model config discovery where supported.
- Adapter status labels: Validated, Exploratory, Request Adapter, Refused.
- Intake failure reasons that are useful to customers and support.

Exit criteria:
- Supported external models can enter a real audit session.
- Unsupported models are handled cleanly without pretending compatibility.
- Credential and customer data handling language is reviewed.

### M4 - Licensing / Billing

Goal: make commercial usage enforceable and visible.

Deliverables:
- Plan tiers, model slots, run caps, and usage counters.
- License key status and expiration handling.
- Billing provider integration or manual enterprise billing workflow.
- Account-level audit history and export limits.
- Admin controls for trials, suspensions, and enterprise overrides.

Exit criteria:
- Usage limits affect session creation and model intake.
- Customer-facing messaging explains limits without exposing internal billing implementation.
- Enterprise/manual billing path is documented.

### M5 - Multi-Model Adapters

Goal: expand model coverage after the audit workflow is stable.

Deliverables:
- Adapter framework for supported model families.
- Validation suite per model family.
- Adapter registry exposed to the UI.
- Per-adapter confidence and support-level language.
- Request-adapter flow connected to support or sales.

Exit criteria:
- Each listed adapter has a validation status and known limitations.
- UI never says "all models" unless intake and validation actually support that scope.
- New adapters can be added without rewriting audit-console workflow.

## Stakeholder Demo Script

### Setup

"This is the CAS Harness Audit Console. The user connects a model, chooses an audit profile, and CAS returns operational routing decisions: ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW. Atlas is available for deep inspection when we need to examine the evidence path behind a verdict."

### Step 1 - Open Audit Sessions

Show the session queue.

Talk track:
"The first screen is operational. It is not a research cockpit. It shows which model was audited, which policy profile was used, and how many outputs were accepted, suppressed, or routed to review."

### Step 2 - Create a New Audit

Open New Audit and point to model connector, scenario pack, policy profile, and audit mode.

Talk track:
"In production, a licensed user attaches their model of choice through a supported connector. In this alpha, any scaffolded connector is labeled. The important product shape is stable: model, scenario pack, policy, run mode."

### Step 3 - Run Monitor

Show the run status timeline.

Talk track:
"The console separates running state from completed evidence. We do not call a result final until scoring and provenance assembly are complete."

### Step 4 - Verdict Review

Open the verdict table.

Talk track:
"This is the core workflow. Each row gets a verdict, a confidence value, and provenance chips. ACCEPT means allow it. SUPPRESS means block or withhold it. FLAG FOR HUMAN REVIEW means CAS is routing it to a person under the active policy."

### Step 5 - Provenance Chips

Expand one item.

Talk track:
"The chips are the compact reason trail: policy match, behavioral signal, scenario anchor, trace evidence, confidence basis, and reviewer context. If evidence was not collected, the UI says that directly."

### Step 6 - Open Evidence Packet

Show the export-oriented detail.

Talk track:
"The Evidence Packet is the artifact customers can hand to internal reviewers, partners, or auditors. M2 turns this into signed JSON, markdown, and a ZIP bundle. Until signing is implemented, we should call it an exportable packet, not a compliance-certified artifact."

### Step 7 - Open Atlas

Open Atlas from a row that has trace evidence.

Talk track:
"Atlas is the deep inspection cockpit. It helps explain what happened inside a supported run. It is not the whole CAS Harness product and it is not required for every operational screen."

### Step 8 - Close with Roadmap

Talk track:
"The build sequence is M0 scaffold, M1 real API sessions, M2 Evidence Packet, M3 external model intake, M4 licensing and billing, and M5 multi-model adapters. That order keeps the product honest: first show the workflow, then make sessions real, then make the evidence portable, then broaden model coverage."

## Implementation Copy Rules

- Prefer "audit session" over "experiment" in customer-facing screens.
- Prefer "verdict" over "score" for the final operational result.
- Prefer "confidence" over "certainty".
- Prefer "provenance" or "evidence" over "proof".
- Label fixture-backed data as "demo", "reference", or "sample".
- Label unsupported model intake as "request adapter" instead of "failed".
- Keep Atlas copy subordinate: "open in Atlas", "inspect evidence path", "deep inspection".
