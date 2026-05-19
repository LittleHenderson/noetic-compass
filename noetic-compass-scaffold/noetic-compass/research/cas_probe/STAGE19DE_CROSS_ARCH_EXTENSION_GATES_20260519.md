# Stage 19D / 19E Cross-Architecture Extension Gates

**Date:** 2026-05-19

**Branch:** `experiment/cas-probe-pythia`

**Status:** `PRE_REGISTERED_NOT_RUN`

**Authorization:** user authorized cross-architecture extension to two
additional families after the Stage 19C `MODE_SELECTOR_READY` verdict on
OLMo-1B and Qwen2.5-1.5B.

## Revision Note

This gate is committed BEFORE any Stage 19D / 19E pod run, BEFORE
`run_stage19BDE_cross_arch_extension_verification_stack.py` or
`run_stage19CDE_cross_arch_extension_mode_selector.py` is launched, and
BEFORE any artifact in this extension family is produced. Pre-registration
discipline applies (per Stage 19A's lesson).

## Purpose

Stage 19D / 19E extends the Stage 19C Mode Selector (`HIGH_PRECISION`,
`BALANCED`, `MAX_COVERAGE_TRIAGE`) to two further model families. The
methodology is the locked Stage 15 → 16 → 8 → 19B → 19C lineage with only
the model, tokenizer, and layer-scan range swapped. No new methodology is
introduced.

## Scope

Authorized:

- Model 19D: `microsoft/phi-2` (MIT, Microsoft, 2.7B parameters,
  Phi-2 decoder architecture).
- Model 19E: `TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T`
  (Apache 2.0, TinyLlama academic group, 1.1B parameters, Llama-style
  decoder architecture).
- Dataset: frozen Stage 7 original-TKS 28-Foundation fixture,
  `stage7_foundation_pilot_20260517.jsonl`. NO new fixture is built.
- Activation capture: focus-token, final-token, and mean-token readouts for
  the pre-registered layer-scan range below.
- Probe family: same sklearn `StandardScaler` + `LogisticRegression(lbfgs,
  class_weight="balanced")` used in Stages 8, 14, 15, 16.
- Primary CPL2 assay: same η→ε likelihood bridge used in Stages 8 / 14 / 15
  / 16, with the same 112-row same-register Drive-cycle pack (16 rows per
  Drive).
- Verification Stack: same selected-layer ensemble + Drive/Register factor
  recomposition + non-oracle trace stability as Stage 19B.
- Mode Selector: same `HIGH_PRECISION` / `BALANCED` / `MAX_COVERAGE_TRIAGE`
  source-component packaging as Stage 19C, with the SAME per-mode
  pre-registered targets.

Not authorized in this stage:

- Llama-3.x family (license skip per authorization).
- Phi-3-mini-4k-instruct (>5 GB per-model cap).
- Gemma-2B (gated, terms-of-use friction).
- 7B or larger models (separate scale-up direction).
- Stage 12 / 13 formula-family reruns on Phi-2 or TinyLlama.
- Hidden-state steering claims.
- Raw CAS-symbol understanding claims.
- Open-ended visible generation-control claims.
- New fixtures, new probes-other-than-Foundation, or new CPL2 conditions.

Hard cap: 4 GPU-hours aggregate on A6000 (2 per model). If projected
wall-clock exceeds 90 minutes on either model after model download starts,
stop and surface before continuing. Mode Selector calibration is CPU-only
post-processing of the Stage 19BDE JSON; it does not count against the GPU
budget.

## Locked Inputs

Shared fixture:

- `stage7_foundation_pilot_20260517.jsonl`

Model activation artifacts (produced by pod run):

| Model key | Activation file | Manifest |
|---|---|---|
| `phi2` | `stage19D_phi2_activations_20260519.npz` | `stage19D_phi2_activations_manifest_20260519.json` |
| `tinyllama` | `stage19E_tinyllama_activations_20260519.npz` | `stage19E_tinyllama_activations_manifest_20260519.json` |

The large activation binaries remain git-ignored. Manifests and SHA-256
values remain the provenance record.

## Layer Scan Ranges

| Model | Total layers | Pre-registered scan range |
|---|---:|---|
| Phi-2 | 32 | `12-28` (17 positions, depth fraction 0.375-0.875) |
| TinyLlama-1.1B | 22 | `8-20` (13 positions, depth fraction 0.36-0.91) |

Layer selection rule (same as Stages 15, 16):

1. Train a 28-way Foundation probe on each candidate layer using the
   frozen train split.
2. Select the layer with highest validation 28-way Foundation accuracy.
3. If validation accuracy ties within `0.001`, choose the
   lower-lacunarity layer.
4. Report test accuracy only after the layer is selected.

No test-set-driven layer choice is allowed.

## Per-Stage Pass Criteria

### Stage 19D / 19E Activation Capture

PASS:

- All target layer positions present in `.npz`.
- SHA-256 recorded in manifest.
- No missing samples.
- `n_records` equals fixture row count.

FAIL: any of the above; surface before continuing.

### Stage 19D / 19E Foundation Probe Training

Embedded in `probe_stage19D_phi2_cpl2.py` /
`probe_stage19E_tinyllama_cpl2.py`. The probe-training half of the script
trains 28-Foundation probes on each layer in the scan range.

PASS:

- Selected-layer validation accuracy at least `0.700`.
- Selected-layer test accuracy at least `0.600`.
- Test lacunarity at most `0.10`.

NULL: any of the above missed. CPL2 still runs but the result has reduced
weight.

### Stage 19D / 19E CPL2 η→ε Bridge

Same `probe_readable` vs `partner_readable` vs `none` design as
Stages 8 / 14 / 15 / 16. Status taxonomy: PASS_CLEAN / GREY / NULL.

`PASS_CLEAN` (all must hold):

- `probe_readable_delta_vs_none > +0.15`
- paired Wilcoxon `p < 0.05`
- `probe_readable_minus_partner_readable_margin > +0.30`
- positive-share `> 60 / 112`

`NULL` (any one is enough):

- `probe_readable_delta_vs_none < +0.05`
- `probe_readable_minus_partner_readable_margin < +0.10`
- positive-share `< 50 / 112`

`GREY`: between PASS_CLEAN and NULL.

Frozen CPL2 references for comparison:

| Model | Delta vs none | Margin over partner | Positive cases |
|---|---:|---:|---:|
| Pythia-160M | `+0.2828` | `+0.6829` | `81 / 112` |
| Pythia-1B | `+0.5542` | `+1.2460` | `90 / 112` |
| Pythia-2.8B | `+0.5832` | `+1.3363` | `92 / 112` |
| OLMo-1B | `+0.6037` | `+1.3047` | `87 / 112` |
| Qwen2.5-1.5B | `+0.7960` | `+1.6253` | `83 / 112` |

Phi-2 and TinyLlama are not expected to match Qwen2.5-1.5B; they only need
to clear the defensible CPL2 floor above.

### Stage 19BD / 19BE Verification Stack (per model)

Use the same product-safety thresholds as Stages 19A / 19B.

| Tier | Accepted Foundation accuracy | Coverage | Silent error rate | Meaning |
|---|---:|---:|---:|---|
| `PASS_STRONG` | `>= 0.970` | `>= 0.850` | `<= 0.030` | Stack transfers at high precision without suppressing too much. |
| `PASS_BOUNDED` | `>= 0.960` | `>= 0.800` | `<= 0.040` | Stack transfers as a high-precision verifier but misses the strong tier. |
| `DIAGNOSTIC_ONLY` | any | `< 0.800` | any | Stack is mainly a flagger on this model. |
| `NULL` | `< best single selected Foundation accuracy` | any | any | Stack does not improve usable quality over the best single Foundation readout. |
| `GREY` | otherwise | otherwise | otherwise | Mixed result requiring audit before claim use. |

Combined Stage 19BDE overall status:

- `PASS_STRONG_CROSS_ARCH`: both models reach `PASS_STRONG`.
- `PASS_BOUNDED_CROSS_ARCH`: both models reach `PASS_STRONG` or
  `PASS_BOUNDED`.
- `MIXED`: one model passes, one does not.
- `NULL`: neither model passes.

### Stage 19CDE Mode Selector

Per-mode pre-registered targets are EXACTLY the Stage 19C targets:

| Mode | Source component | Accepted accuracy min | Coverage min | Silent error rate max |
|---|---|---:|---:|---:|
| `HIGH_PRECISION` | `stack` | `0.98` | — | `0.02` |
| `BALANCED` | `factor_consistent` | `0.94` | `0.80` | `0.06` |
| `MAX_COVERAGE_TRIAGE` | `ensemble_only` | `0.88` | `0.88` | — |

Per-mode cross-architecture status:

- `MODE_SUPPORTED_CROSS_ARCH`: BOTH Phi-2 and TinyLlama meet the mode's
  pre-registered targets.
- `MODE_PARTIAL`: at least one model meets the target.
- `MODE_NOT_SUPPORTED`: neither model meets the target.

Per-model verdict (each model evaluated independently against the same
targets):

- `MEETS_TARGET`: model crosses the per-mode threshold under that mode's
  source component.
- `MISSES_TARGET`: otherwise.

Combined cross-architecture extension verdict (a Stage 19DE-aggregate label
for the synthesizer to use, not emitted by the runner directly):

- `EXTENSION_FULLY_SUPPORTED`: all three modes are
  `MODE_SUPPORTED_CROSS_ARCH`. Stage 19C extension claim can be widened to
  include Phi-2 and TinyLlama on equal footing with OLMo and Qwen.
- `EXTENSION_PARTIAL`: one or two of three modes are
  `MODE_SUPPORTED_CROSS_ARCH`. Synthesizer documents which modes extend
  and which require further work.
- `EXTENSION_NOT_SUPPORTED`: zero of three modes are
  `MODE_SUPPORTED_CROSS_ARCH`. Stage 19DE result is a `DIAGNOSTIC_ONLY`
  data point; OLMo/Qwen Stage 19C result is unchanged.

Reserved-language discipline: runner emits `MODE_SELECTOR_READY` overall and
per-mode `MODE_SUPPORTED_CROSS_ARCH` / `MODE_PARTIAL` / `MODE_NOT_SUPPORTED`
exactly. PASS_CLEAN / GREY / NULL / DIAGNOSTIC_ONLY appear in upstream
stages (CPL2, Verification Stack) on per-mode claim boundaries only.

## Sequence Dependency

Stages must run in order. Each stage depends on the previous artifact:

1. `capture_stage19D_phi2_activations.py` produces `.npz` + manifest.
2. `probe_stage19D_phi2_cpl2.py` reads the `.npz`, trains probes, runs
   CPL2; emits probe + CPL2 + summary report.
3. `capture_stage19E_tinyllama_activations.py` produces `.npz` + manifest.
4. `probe_stage19E_tinyllama_cpl2.py` reads the `.npz`, trains probes,
   runs CPL2; emits probe + CPL2 + summary report.
5. `run_stage19BDE_cross_arch_extension_verification_stack.py` reads both
   `.npz` files and emits the combined Verification Stack JSON + MD.
6. `run_stage19CDE_cross_arch_extension_mode_selector.py` reads the
   Stage 19BDE JSON and emits the Mode Selector JSON + MD.

Steps 1-4 can be parallelized across pod processes. Step 5 depends on both
`.npz` files. Step 6 depends on step 5. Do not parallelize 5 and 6.

## Required Artifacts

Commit before run:

- `STAGE19DE_CROSS_ARCH_EXTENSION_GATES_20260519.md` (this document).
- `STAGE19DE_MODEL_SELECTION_RATIONALE_20260519.md`.
- All scripts in this scaffolding pass (capture, probe+CPL2, Verification
  Stack, Mode Selector — 6 scripts total).

Commit after run:

- Activation manifests (both models) — JSON only, NOT `.npz` binaries.
- Probe report JSON + MD (both models).
- CPL2 report JSON + MD (both models).
- Summary MD (both models).
- Stage 19BDE Verification Stack JSON + MD.
- Stage 19CDE Mode Selector JSON + MD.
- README Stage 19D / 19E / 19BDE / 19CDE entries.
- Claude audit handoff in `docs/working/agent_exchange/inbox_claude.md`.

Do not commit:

- `stage19D_phi2_activations_20260519.npz` (binary, git-ignored).
- `stage19E_tinyllama_activations_20260519.npz` (binary, git-ignored).

## Audit Questions

1. Were gates committed before the run?
2. Was layer choice made by validation before test reporting on both
   models?
3. Do Phi-2 and TinyLlama each pass, fail, or land grey under the exact
   CPL2 thresholds above?
4. Are raw-symbol controls null or unexpectedly active on either model?
5. Does the Mode Selector report match Stage 19C per-mode pre-registered
   targets exactly, with no quiet relaxation of the
   `accepted_accuracy_min` / `silent_error_rate_max` / `coverage_min`
   thresholds?
6. Does wording keep Stage 19D / 19E as readable-prefix likelihood
   conditioning, not hidden-neuron steering or raw-symbol understanding?
7. Does the combined extension verdict
   (`EXTENSION_FULLY_SUPPORTED` / `EXTENSION_PARTIAL` /
   `EXTENSION_NOT_SUPPORTED`) follow correctly from the per-mode
   `MODE_SUPPORTED_CROSS_ARCH` counts?
