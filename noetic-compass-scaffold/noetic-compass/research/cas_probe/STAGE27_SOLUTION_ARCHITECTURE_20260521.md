# Stage 27 Solution Architecture From Noetic Topos and TKS v7.4

**Status:** `SOLUTION_ARCHITECTURE_READY`

## Purpose

This memo consolidates a four-agent read-only review of the Noetic Topos
submission, the TKS v7.4 master text, and the CAS Harness Stage 7-26 record.
The goal is to explain the recurring failure modes and define the next
solutions before new GPU work.

## Core Diagnosis

The recent failures are not one failure. They are failures of local,
single-channel assumptions:

| Failed assumption | Evidence | Corrected interpretation |
|---|---|---|
| A single hidden-state direction should steer free text. | Stage 7 output alignment and late-layer additive tests were null. | The probe learns `eta`, a readout/embedding map. Generation needs `epsilon`, a realization map. |
| Static output embeddings should expose fine CAS token signatures. | Stage 24B passed broad unrelated controls but failed hard local partner contrasts. | Static `W_U` projection sees broad vocabulary regions, not fine local CAS distinctions. |
| A standard SAE should find sparse causal CAS features. | Stage 25 reconstructed 98.3% variance but had 2303 active features per row and causal removal was null. | CAS signal is dense within a residual layer; a vanilla sparse basis is the wrong decomposition. |
| One global verification threshold should transfer cross-architecture. | Stage 19B held high accepted accuracy on OLMo/Qwen but missed the 80% coverage floor. | Architecture-specific pullbacks need calibrated mode profiles. |
| Free-form visible generation should reveal likelihood shifts. | Stage 18 visible text was null despite strong CPL2 likelihood evidence. | Greedy/free prose is a lossy surface channel. Use constrained or forced-choice realization. |

The positive result that changes the roadmap is Stage 26:

- `PASS_BOUNDED_COMPONENT_ATTRIBUTION`
- 78 components captured across 4368 rows.
- Top components concentrated in attention heads: `L5H3`, `L5H5`, `L5H0`,
  `L5H10`, `L1H6`, `L5H6`.
- Targeted ablation dropped Foundation accuracy from `0.7832` to `0.1855`.
- Matched same-kind/layer ablation p-value: `0.0323`.

Stage 26 says the signal is not sparse-neuron-like, but it is not shapeless.
It localizes as a jointly covering component family.

## Formal Anchors

| Anchor | Engineering consequence |
|---|---|
| Noetic coverage: jointly surjective covers, ACBE descent covers, and RPM counit covers. | Stop requiring one token, one feature, or one neuron to carry CAS. Test covering families of heads, MLP blocks, features, readouts, and traces. |
| ACBE pullback stability. | Treat each architecture/readout stack as a pullback of the CAS fixture. Calibrate per architecture instead of forcing one threshold. |
| RPM section-retraction: `epsilon_X after eta_X = id_X`. | Use `hidden readout -> readable realization -> likelihood/constrained output`; do not treat hidden-state surgery as the canonical realization path. |
| Sheaf condition and Grothendieck topology. | Treat probes, layers, judges, traces, and controls as local sections. Accept only when they glue; otherwise emit conflicted, suppressed, or undetermined. |
| Subobject classifier/internal intuitionistic logic. | Product states should be non-Boolean: accepted, caveated, conflicted, suppressed, structurally unsupported, undetermined. |
| 40-state open simplex and Fisher-Rao geometry. | Compare soft CAS distributions across models in probability-simplex space, not only raw logits or hard labels. |

## TKS v7.4 Design Rule

TKS v7.4 points to this loop:

```text
read structure -> validate/factor it -> realize it into surface form -> gate the result
```

It does not point to:

```text
find hidden thing -> push hidden thing -> expect free prose to obey
```

That distinction explains the nulls. The model can contain CAS-readable
structure without exposing a clean free-text steering column.

## Recommended Roadmap

### Stage 27A - Component Path-Patching and Component Atlas

**Priority:** first.

**Why:** It directly follows the Stage 26 pass and tests necessity plus
sufficiency, not only destructive ablation.

**Design:**

- Use Stage 26 top components as the candidate cover.
- Ablate top heads individually, cumulatively, and by class.
- Patch clean component contributions into corrupted/counterfactual forwards.
- Measure whether patching restores the Stage 7 Foundation readout.
- Emit a per-class component atlas: which components disrupt which Foundation
  classes.

**Files likely to create:**

- `stage27_component_path_patching_spec.py`
- `run_stage27_component_path_patching.py`
- `STAGE27_COMPONENT_PATH_PATCHING_20260521.md`
- `stage27_component_path_patching_20260521.json`
- `tests/test_stage27_component_path_patching.py`

**Gates:**

- Split-half top-component stability.
- Matched same-kind/layer ablation p < 0.05.
- Patch restoration recovers at least 50% of lost readout accuracy.
- Per-class disruption remains concentrated, not uniform global damage.

**Claim if pass:**

CAS Harness identifies a bounded component path for the Pythia-160M Stage 7
Foundation readout, with necessity and sufficiency evidence at the head/MLP
block level.

**Forbidden claims:**

Exact neurons, complete circuits, raw CAS-symbol understanding, internal CAS
compiler, free-form generation control, or cross-model component generality.

### Stage 27B - Component-Guided Contrast Sonar

**Priority:** second.

**Why:** Stage 24B static sonar failed hard local contrasts because `W_U` is too
blunt. Stage 26 gives causal components; use intervention deltas instead of
static top-token projection.

**Design:**

- Compute baseline token/logit signatures.
- Ablate or patch Stage 26 components.
- Measure token/logit deltas for target vs hard-partner contrasts.
- Score whether hard-partner margins become positive under component-localized
  intervention.

**Files likely to create:**

- `stage27_component_guided_sonar_spec.py`
- `run_stage27_component_guided_contrast_sonar.py`
- `STAGE27_COMPONENT_GUIDED_SONAR_20260521.md`
- `stage27_component_guided_sonar_20260521.json`
- `tests/test_stage27_component_guided_sonar.py`

**Gates:**

- Hard-partner margin flips positive.
- p < 0.05 versus matched component controls.
- Readable token stability under bootstrap.
- Broad-axis metrics do not regress.

**Claim if pass:**

CAS token signatures become more discriminative when measured through
component-localized intervention deltas than through static unembedding
projection.

### Stage 27C - Verification Calibration Registry

**Priority:** product-track parallel.

**Why:** Stage 19B did not fail in precision; it failed in cross-architecture
coverage. Stage 19C already introduced modes. The product needs a versioned
calibration registry.

**Design:**

- Store per-model calibration profiles keyed by model family, fixture,
  readout stack, layer profile, and threshold policy.
- Include HIGH_PRECISION, BALANCED, and MAX_COVERAGE_TRIAGE.
- Evidence Packets should store the calibration hash used for each decision.

**Files likely to create/modify:**

- `verification_calibration_registry.schema.json`
- `run_stage27_verification_calibration_registry.py`
- `run_stage19c_verification_mode_selector.py`
- `run_stage19CDE_cross_arch_extension_mode_selector.py`
- `evidence_packet.py`

**Gates:**

- No gold labels used at runtime.
- Bootstrap confidence intervals for accepted accuracy, coverage, and silent
  error.
- Held-out calibration split.
- BALANCED recovers >=80% coverage where possible while preserving bounded
  silent-error policy.

**Claim if pass:**

CAS Harness supports calibrated operating modes for tested architectures and
fixtures. It does not prove universal threshold transfer.

### Stage 28 - Causal Sparse Dictionary, Not Vanilla SAE

**Priority:** after Stage 27A.

**Why:** Stage 25 closed the vanilla residual SAE route as insufficient. A retry
only makes sense if it changes the method.

**Design:**

- Train a sparse dictionary over Stage 26 component contributions, not raw
  residual activations alone.
- Use top-k or L0-style sparsity with a real active-feature target.
- Add supervised CAS contrastive losses for Domain, Noetic, and 40-Element
  factors.
- Require causal removal and patch sufficiency.

**Gates:**

- <=50 active features per row.
- Alignment p < 0.05.
- Class specificity p < 0.05.
- Targeted feature removal drops probe accuracy more than random p < 0.05.
- Patch sufficiency passes.

**Claim if pass:**

Sparse feature candidates are causally relevant to the trained CAS readout.
Still not exact neurons or complete circuits.

### Controlled Visible Realization

**Priority:** lower than Stage 27A/27B/27C.

**Why:** Stage 18 showed open free-form generation is a lossy channel. Visible
text should be tested only in controlled-choice or constrained decoding.

**Design:**

- Replace free prose with forced-choice target/partner continuations.
- Use readable `epsilon` prefixes and typed CAS traces.
- Score target-vs-partner visible choice and judge alignment.

**Gate:**

- Target wins >=65%.
- Wilcoxon p < 0.05.
- Target-partner margin >=0.10.
- Judge accuracy >=0.65.

**Claim if pass:**

Controlled visible realization works under constrained conditions. Free-form
steering remains unlicensed.

## What Not To Do Next

- Do not rerun static `W_U` sonar as if it were untested.
- Do not rerun vanilla residual SAE without changing dictionary/sparsity and
  causal gates.
- Do not chase open free-form generation until path-level interventions affect
  likelihood or constrained choices.
- Do not call Stage 26 exact-neuron discovery.
- Do not claim the host model runs a CAS compiler internally.

## Bottom Line

The mathematical and empirical answer is the same: CAS Harness should move from
single-feature hunting to covering-family attribution.

The next gate is Stage 27A. It asks whether the Stage 26 component family is
not only necessary under ablation, but sufficient under path patching. If it
passes, CAS Harness gains a stronger mechanistic rung: bounded component path
attribution. If it fails, the product still keeps the readout, verification,
evidence-packet, and likelihood-conditioning tiers, but component localization
stops at Stage 26.
