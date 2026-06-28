# CAS Harness M3 Real Verdict Runner Plan

Date: 2026-05-25
Owner: Agent B
Scope: design/research only. No shared API routes or frontend files edited.

## Executive Decision

M3 should wire the Audit Console to a real CAS Harness verdict runner, not to UI-only state and not to placeholder confidence. The runner should emit exactly one product verdict:

- `ACCEPT`
- `SUPPRESS`
- `FLAG_FOR_HUMAN_REVIEW`

The safe route is to promote the Stage 19 Verification Stack and Stage 20 Generation Readiness Gate into a production service layer, then attach Evidence Packet export. Do not create a new verdict heuristic from scratch.

Plain English:

> The model is accepted only when the calibrated CAS verifier sees enough agreement and stability. If the evidence is missing, conflicted, unsupported, or outside calibrated coverage, the system does not guess. It suppresses or flags for human review.

## Existing Code That Already Produces Real Accept/Suppress Behavior

### 1. Stage 19A Formula Verification Stack

Source inspected:

- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage19a_formula_verification_stack.py`
- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/stage19a_formula_verification_stack_rerun_20260519.json`

What it does:

- Uses selected layer readouts across `focus_token`, `final_token`, and `mean_over_seq_len`.
- Requires 2-of-3 ensemble agreement.
- Computes non-oracle trace states: `stable`, `drifting`, `uncertain`, `conflicted`.
- Accepts only high/medium stability cases.
- Suppresses ensemble disagreement, uncertainty, conflict, or unstable traces.
- Uses gold labels only after the decision to score accuracy.

Important metrics from the rerun report:

- Test rows: 4,200.
- Accepted rows: 3,679.
- Suppressed rows: 521.
- Coverage / accept rate: 87.60%.
- Accepted accuracy: 99.78%.
- Silent accepted error rate: 0.22%.
- Status: `PASS_STRONG_AUDIT_CLEAN`.

M3 implication:

This is the clearest existing production-shape verifier. Its acceptance logic is already runtime-safe because it does not need gold labels to decide whether to accept.

### 2. Stage 19B Cross-Architecture Foundation Verification Stack

Source inspected:

- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage19b_cross_arch_foundation_verification_stack.py`
- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/stage19b_cross_arch_foundation_verification_stack_20260519.json`

What it adds:

- Runs OLMo-1B and Qwen2.5-1.5B Foundation checks.
- Performs Foundation ensemble agreement.
- Separately reads Drive and Register factors.
- Recombines Drive x Register back into the Foundation label.
- Suppresses `factor_conflicted` rows instead of accepting an inconsistent CAS interpretation.
- Emits per-row diagnostics when `--emit-diagnostics` is enabled.

Important metrics:

- OLMo-1B accepted accuracy: 98.16%.
- OLMo-1B coverage: 71.73%.
- Qwen2.5-1.5B accepted accuracy: 99.49%.
- Qwen2.5-1.5B coverage: 74.57%.
- Both are high precision but diagnostic-only under strict product coverage thresholds.

M3 implication:

For cross-architecture models, the runner must expose coverage honestly. A row outside acceptance coverage should become `FLAG_FOR_HUMAN_REVIEW` or `SUPPRESS`, not a low-confidence `ACCEPT`.

### 3. Stage 19C Verification Mode Selector

Source inspected:

- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage19c_verification_mode_selector.py`

What it does:

- Packages Stage 19B into user-facing modes.
- `HIGH_PRECISION`: uses final Stack component. Highest precision, lower coverage.
- `BALANCED`: uses factor-consistent component. Default customer mode.
- `MAX_COVERAGE_TRIAGE`: uses ensemble-only component. Triage only, not a final high-confidence claim.

M3 implication:

The Audit Console's mode selector should choose verifier operating mode, not just UI copy. `MAX_COVERAGE_TRIAGE` should not silently produce license-grade `ACCEPT` decisions.

### 4. Stage 20 Generation Readiness Gate

Source inspected:

- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/cas-native/model/generation_readiness_gate.py`
- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage20b_generation_readiness_packets.py`

What it does:

- Reads Verification Stack status plus optional lacunarity, inversion, RPM, gap, and domain-confidence signals.
- Emits `allow`, `caveat`, `constrain`, or `suppress`.
- Is non-mutating: no hidden-state edits, no logit edits, no tensor throttle.
- Uses mode-aware thresholds.

M3 implication:

M3 should map Stage 20 policy to the three product verdicts:

- `allow` -> `ACCEPT` if all required provenance is present.
- `caveat` -> `FLAG_FOR_HUMAN_REVIEW`.
- `constrain` -> `FLAG_FOR_HUMAN_REVIEW` in triage mode, `SUPPRESS` in license-grade modes.
- `suppress` -> `SUPPRESS`.

### 5. Stage 21A Evidence Packet Export

Source inspected:

- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/evidence_packet.py`
- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage21a_evidence_packet_exporter.py`
- `noetic-compass-scaffold/noetic-compass/api/routes/evidence.py`

What it does:

- Defines `cas_harness_evidence_packet_v1`.
- Validates packet structure.
- Renders reviewer-readable Markdown.
- Includes model, provenance, readout, diagnostics, verification, generation readiness, controls, conditioning, caveats, rejected claims, and boundary.

M3 implication:

Every final M3 verdict should have an Evidence Packet. If packet creation fails, the runner should not return a customer-safe `ACCEPT`.

### 6. Stage 22.4 / 22.5 / 22.6 Diagnostic Attribution

Source inspected:

- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage22_4_instrumented_verifier_preflight.py`
- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/run_stage22_6_inversion_proxy_attribution.py`
- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/stage22_6_inversion_scanner.py`
- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/stage22_5_full_row_proxy_attribution_20260520.json`
- `origin/experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/stage22_6_inversion_proxy_attribution_20260520.json`

What it does:

- Stage 22.4 emits diagnostic rows for all OLMo/Qwen rows.
- Stage 22.5 reports:
  - total rows: 4,704
  - RPM proxy measurable rows: 4,142
  - lacunarity proxy measurable rows: 4,704
  - inversion numeric measured rows: 0
- Stage 22.6 reports:
  - numeric inversion proxy rows: 4,704 / 4,704
  - numeric inversion proxy rate: 1.000
  - OLMo inversion decisions: allow 1,035, constrain 713, suppress 604
  - Qwen inversion decisions: allow 940, constrain 590, suppress 822

M3 implication:

Inversion can be shown as numeric proxy attribution. It should not be described as a full semantic inversion theorem. If inversion says `suppress`, the final verdict cannot be `ACCEPT`.

## Current Audit Console Lifecycle To Wire Into

Source inspected:

- `origin/codex/cas-harness-audit-console:noetic-compass-scaffold/noetic-compass/api/routes/cas_harness_audit.py`
- `origin/codex/cas-harness-audit-console:noetic-compass-scaffold/noetic-compass/api/services/cas_harness_audit_sessions.py`
- `origin/codex/cas-harness-audit-console:noetic-compass-scaffold/noetic-compass/atlas-viewer/src/lib/casHarnessAudit.ts`
- `origin/codex/cas-harness-audit-console:noetic-compass-scaffold/noetic-compass/atlas-viewer/src/lib/casHarnessAuditApi.ts`
- `origin/codex/cas-harness-audit-console:noetic-compass-scaffold/noetic-compass/atlas-viewer/src/pages/AuditConsolePage.tsx`

Current behavior:

- Creates and stores an audit session.
- Validates the request shape.
- Stops at `SCAFFOLD_PENDING_RUNNER`.
- Returns no verdict and no confidence.
- Correctly labels model status as `NOT_CONNECTED_MOCK`.

M3 target behavior:

- `run_session()` calls a real runner service.
- The session reaches `COMPLETE` only after a real verdict and packet exist.
- If the runner cannot compute a real verdict, the session reaches `FAILED` or `FLAG_FOR_HUMAN_REVIEW`, with explicit reasons.

## Inputs A Real M3 Runner Needs

The runner needs more than a prompt. It needs the actual data the Verification Stack consumes.

### Required session inputs

- `audit_id`
- `audit_mode`: `HIGH_PRECISION`, `BALANCED`, or `MAX_COVERAGE_TRIAGE`
- `model_id`
- `scenario_text` or `prompt`
- `selected_modules`
- license/user context
- requested output limit / generation settings

### Required model proof inputs

- real model loaded flag
- fake/demo mode flag is false
- model manifest says real model
- model load error is null
- model revision or commit/hash when available
- tokenizer identity
- runtime worker identity
- capture timestamp

If this proof is missing, final verdict must not be `ACCEPT`.

### Required model-run inputs

- input prompt
- generated output or candidate output
- token ids and decoded token strings
- focus-token hidden states
- final-token hidden states
- mean-over-sequence hidden states
- per-layer hidden-state tensors or artifact references
- logits or token probabilities if output confidence is part of the packet
- optional attention patterns for Mode 7 evidence

### Required CAS probe-pack inputs

- supported model family / architecture
- probe-pack id and version
- selected layer config
- readout labels
- scaler/classifier/probe artifacts
- validation metrics for the probe pack
- baseline/control metrics
- ablation/intervention evidence backing the claim
- hash of every artifact used

If the model family has no calibrated probe pack, the runner should return `FLAG_FOR_HUMAN_REVIEW` with reason `unsupported_or_uncalibrated_model`, not `ACCEPT`.

### Required diagnostic inputs

- Foundation readout votes
- Drive readout votes
- Register readout votes
- trace states for readouts
- Drive/Register recomposition result
- RPM satisfaction
- lacunarity scores or proxy lacunarity
- inversion proxy scores
- suppression reasons if any gate rejects

## Minimal M3 Runner Interface

### Python service location

Recommended next file:

- `noetic-compass-scaffold/noetic-compass/api/services/cas_harness_verdict_runner.py`

Do not put the logic directly inside the FastAPI route. Keep the route thin and make the runner unit-testable.

### Request

```python
class CasHarnessVerdictRunRequest(BaseModel):
    audit_id: str
    audit_mode: Literal["HIGH_PRECISION", "BALANCED", "MAX_COVERAGE_TRIAGE"]
    model_id: str
    prompt: str
    selected_modules: list[str]
    license_context: dict[str, Any] = {}
    runtime_proof: RuntimeProof
    model_run: ModelRunArtifact
    probe_pack: ProbePackRef
```

Minimum nested fields:

```python
class RuntimeProof(BaseModel):
    is_real_model: bool
    model_loaded: bool
    manifest_is_real_model: bool
    fake_runtime_env: bool
    load_error: str | None
    worker_url_hash: str | None
    model_revision: str | None
```

```python
class ModelRunArtifact(BaseModel):
    input_text: str
    output_text: str
    token_ids: list[int]
    tokens: list[str]
    hidden_state_artifact_ref: str
    logits_artifact_ref: str | None = None
    attention_artifact_ref: str | None = None
```

```python
class ProbePackRef(BaseModel):
    probe_pack_id: str
    model_family: str
    supported_model_ids: list[str]
    selected_layers: dict[str, Any]
    validation_profile: dict[str, Any]
    artifact_hashes: dict[str, str]
```

### Response

```python
class CasHarnessVerdictRunResponse(BaseModel):
    audit_id: str
    status: Literal["COMPLETE", "FAILED"]
    verdict: Literal["ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"] | None
    confidence: float | None
    confidence_band: Literal["high", "medium", "low", "unavailable"]
    confidence_meaning: str
    reasons: list[str]
    verification_stack: dict[str, Any]
    generation_readiness: dict[str, Any]
    diagnostics: dict[str, Any]
    provenance_chips: list[dict[str, str]]
    evidence_packet_trace_id: str | None
    atlas_deep_link: str | None
    failure_code: str | None
```

## Confidence Meaning

Do not compute M3 confidence from one softmax margin and call it truth.

M3 confidence should mean:

> How strong this verdict is under the calibrated CAS verifier profile for this model/probe pack and this row's runtime agreement/stability evidence.

Confidence sources:

1. Probe-pack validation profile.
2. Current row ensemble agreement.
3. Current row trace stability.
4. Drive/Register factor consistency.
5. Runtime diagnostics: RPM, lacunarity, inversion.
6. Evidence Packet completion.

Initial numeric confidence rule:

- `ACCEPT` confidence must be capped by the selected verifier component's historical accepted accuracy for that model/probe pack.
- `ACCEPT` requires row-level agreement and stability.
- `FLAG_FOR_HUMAN_REVIEW` can carry confidence only as "risk/conflict confidence", not "safe-to-accept confidence".
- `SUPPRESS` confidence should explain how strongly the evidence supports blocking, not how likely the model is generally wrong.
- If the probe pack is missing or uncalibrated, confidence must be `None` and `confidence_band` must be `unavailable`.

## Verdict Mapping

### ACCEPT

Return `ACCEPT` only when all are true:

- model proof is verified real
- model/probe pack is calibrated for the target model family
- selected audit modules required for this mode completed
- Verification Stack accepts the row
- Stage 20 readiness action is `allow`
- no diagnostic gate returns `suppress`
- Evidence Packet was written and validates

### SUPPRESS

Return `SUPPRESS` when the runner has enough evidence that the output should not be trusted or shown:

- Verification Stack rejects in `HIGH_PRECISION` or `BALANCED`
- Stage 20 readiness action is `suppress`
- inversion proxy returns `suppress`
- RPM/factor recomposition hard-conflicts
- selected policy module requires blocking
- Evidence Packet identifies a hard failure that should block output

### FLAG_FOR_HUMAN_REVIEW

Return `FLAG_FOR_HUMAN_REVIEW` when evidence is real but not sufficient for safe acceptance:

- model/probe pack is unsupported or uncalibrated
- coverage is insufficient
- confidence tier is medium/low under a license-grade mode
- Stage 20 readiness action is `caveat`
- Stage 20 readiness action is `constrain` in triage mode
- required provenance is missing but no hard suppress reason exists
- runner receives partial diagnostics

Plain English:

> Flag is not failure. Flag means "CAS saw enough to know this needs a human, but not enough to safely accept or automatically suppress."

## Coverage Behavior

Coverage is a product feature, not an embarrassment.

The verifier should expose:

- `coverage_basis`: selected mode/source component
- `accepted_coverage`: historical coverage for the probe pack/mode
- `row_in_coverage`: true/false
- `coverage_reason`: why the row was inside or outside acceptance coverage

Rules:

- Rows outside calibrated coverage cannot be `ACCEPT`.
- In `HIGH_PRECISION`, low coverage is acceptable because suppression/review is preferred over silent error.
- In `BALANCED`, factor consistency restores throughput but should not hide lower precision.
- In `MAX_COVERAGE_TRIAGE`, outputs should normally be `FLAG_FOR_HUMAN_REVIEW`, not final `ACCEPT`, unless a later validated policy says otherwise.

## Failure Modes

The runner should return explicit failure codes. No silent fallback to fake verdicts.

Recommended failure codes:

- `runtime_not_real_model`
- `model_load_failed`
- `unsupported_model`
- `probe_pack_missing`
- `probe_pack_hash_mismatch`
- `hidden_state_capture_missing`
- `token_alignment_failed`
- `verification_stack_not_computable`
- `diagnostics_not_computable`
- `evidence_packet_write_failed`
- `evidence_packet_validation_failed`
- `license_not_authorized`
- `runner_timeout`

Handling:

- Infrastructure failures -> `status=FAILED`, `verdict=None`.
- Unsupported or uncalibrated model -> `status=COMPLETE`, `verdict=FLAG_FOR_HUMAN_REVIEW`, confidence unavailable.
- Hard CAS rejection -> `status=COMPLETE`, `verdict=SUPPRESS`.
- Full successful accepted result -> `status=COMPLETE`, `verdict=ACCEPT`.

## Provenance Fields Required In The Response

M3 should report the six proof chips the Audit Console already teaches users to expect:

1. `model_proof`
   - real model loaded, not fake/demo, revision captured.
2. `cas_readout`
   - readout votes, selected layers, labels, trace states.
3. `causal_proof`
   - ablation/intervention evidence from the calibrated probe pack, or unavailable if not present.
4. `control_proof`
   - matched controls / baselines from the calibrated probe pack, or unavailable if not present.
5. `output_proof`
   - actual output text, token ids, logits/hash, token alignment.
6. `packet_proof`
   - Evidence Packet id, hash, schema validation result.

Customer-safe `ACCEPT` requires all six to be present/verified or explicitly waived by a documented mode-specific policy. M3 should not waive them by default.

## Recommended Next Coding Slice

Build M3 in three small PRs:

### PR M3.1: Runner Contract And No-Fake Failure Path

Files to add/edit:

- Add `api/services/cas_harness_verdict_runner.py`.
- Add `tests/test_cas_harness_verdict_runner.py`.
- Edit `api/services/cas_harness_audit_sessions.py` from PR #76 branch to call the runner.
- Edit `api/routes/cas_harness_audit.py` only to widen response models if needed.

Behavior:

- If no real runtime/probe-pack inputs exist, return `FLAG_FOR_HUMAN_REVIEW` or `FAILED`, never fake `ACCEPT`.
- Preserve current M1 honesty.
- Add tests proving fake/demo runtime cannot produce `ACCEPT`.

### PR M3.2: Stage 19B Verifier Core Promotion

Files to add:

- `api/services/cas_harness_verification_stack.py`
- `api/services/cas_harness_probe_pack.py`

Behavior:

- Port the reusable parts of Stage 19B:
  - consensus voting
  - trace state classification
  - Drive/Register recomposition
  - suppression reason construction
  - selected mode source-component selection
- Do not import research scripts directly at request time.
- Use packaged probe-pack artifacts with hashes.

### PR M3.3: Evidence Packet Bridge

Files to add/edit:

- Promote `evidence_packet.py` schema helper into an API-safe module.
- Emit packet JSON/Markdown for every completed verdict.
- Return `evidence_packet_trace_id`.
- Add packet validation tests.

## Risks / Fool-Looking Failure Modes To Avoid

- Calling a placeholder "confidence" a real confidence score.
- Returning `ACCEPT` for a model with no calibrated probe pack.
- Treating Stage 22.6 inversion proxy as a full semantic inversion theorem.
- Treating `MAX_COVERAGE_TRIAGE` as final high-confidence acceptance.
- Hiding coverage by only showing accepted accuracy.
- Using gold labels at runtime.
- Claiming per-session causal proof when the ablation evidence only lives in the calibration pack.
- Reusing live worker fake-mode events as audit verdicts.

## Bottom Line

The real M3 path is not to invent a new verdict system. It is to productize the already-validated Stage 19/20/21 line:

1. Stage 19 Verification Stack decides whether the row is stable enough to trust.
2. Stage 20 Generation Readiness Gate converts that into policy.
3. Stage 21 Evidence Packet makes the decision auditable.
4. Stage 22 diagnostics add RPM, lacunarity, and inversion attribution.

That gives the Audit Console a real answer:

> ACCEPT when the calibrated verifier accepts with complete evidence. SUPPRESS when the calibrated verifier or diagnostics reject. FLAG_FOR_HUMAN_REVIEW when coverage or provenance is not enough.
