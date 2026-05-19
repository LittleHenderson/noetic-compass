# Stage 16 Qwen2.5-1.5B Cross-Architecture Gates

**Status:** pre-registered before any Stage 16 Qwen2.5-1.5B run.

**Branch:** `experiment/cas-probe-pythia`

**Authorization:** user authorized a second cross-architecture replication after the Stage 15 OLMo-1B pass.

## Scope

Stage 16 tests whether the eta-to-epsilon CAS Harness bridge transfers to a third model family.

Authorized:

- Model: `Qwen/Qwen2.5-1.5B`.
- Dataset: frozen Stage 7 original-TKS 28-Foundation fixture, `stage7_foundation_pilot_20260517.jsonl`.
- Activation capture: focus-token, final-token, and mean-token readouts for Qwen2.5-1.5B layer positions `8` through `28`.
- Probe: same sklearn `StandardScaler` + `LogisticRegression(lbfgs, class_weight="balanced")` readout family used in Stages 8, 14, and 15.
- Primary assay: CPL2 likelihood bridge using probe-predicted readable realization prefixes.

Not authorized in this stage:

- Qwen 7B or larger.
- OLMo-7B.
- Llama-family models.
- Mistral-family models.
- Stage 12/13 formula-family reruns on Qwen.
- Hidden-state steering claims.
- Raw CAS-symbol understanding claims.
- Open-ended visible generation-control claims.

Hard cap: 2 GPU-hours on A6000. If projected wall-clock exceeds 90 minutes after model download starts, stop and surface before continuing.

## Frozen References

Prior CPL2 line:

| Model | Delta vs none | Margin over partner | Positive cases |
|---|---:|---:|---:|
| Pythia-160M | `+0.2828` | `+0.6829` | `81/112` |
| Pythia-1B | `+0.5542` | `+1.2460` | `90/112` |
| Pythia-2.8B | `+0.5832` | `+1.3363` | `92/112` |
| OLMo-1B | `+0.6037` | `+1.3047` | `87/112` |

Stage 16 is not expected to match OLMo-1B exactly. It only needs to pass the same defensible CPL2 floor to establish a third-family replication.

## Layer Selection

Capture Qwen2.5-1.5B hidden states for layer positions `8-28`.

Layer selection rule:

1. Train a 28-way Foundation probe on each candidate layer using the frozen train split.
2. Select the layer with highest validation 28-way Foundation accuracy.
3. If validation accuracy ties within `0.001`, choose the lower-lacunarity layer.
4. Report test accuracy only after the layer is selected.

No test-set-driven layer choice is allowed.

## Primary CPL2 Gate

Run CPL2 on the same 112-row same-register Drive-cycle test pack shape used in Stages 8, 14, and 15: `16` rows per Drive.

Conditions:

- `none`
- `gold_readable`
- `probe_readable`
- `partner_readable`
- `gold_raw`
- `probe_raw`
- `partner_raw`

Load-bearing condition: `probe_readable`.

Primary statistics:

- Probe-readable mean likelihood margin delta vs no-prefix.
- Probe-readable mean margin minus partner-readable mean margin.
- Positive-share for probe-readable per-row deltas vs no-prefix.
- Paired Wilcoxon signed-rank test on per-row probe-readable deltas vs no-prefix.

### PASS_CLEAN

All must pass:

- `probe_readable_delta_vs_none > +0.15`
- paired Wilcoxon `p < 0.05`
- `probe_readable_minus_partner_readable_margin > +0.30`
- positive-share `> 60/112`

Interpretation:

> The eta-to-epsilon readable-prefix bridge transfers to Qwen2.5-1.5B at defensible strength.

### NULL

Any one of these is enough for NULL:

- `probe_readable_delta_vs_none < +0.05`
- `probe_readable_minus_partner_readable_margin < +0.10`
- positive-share `< 50/112`

Interpretation:

> The Pythia/OLMo result remains valid, but this run does not establish transfer to Qwen2.5-1.5B.

### GREY

Anything between PASS_CLEAN and NULL.

Interpretation:

> The result is underpowered or borderline. Do not update third-family replication claims without a larger pre-registered pack.

## Required Artifacts

Commit:

- `STAGE16_QWEN15B_GATES_20260519.md`
- `capture_stage16_qwen15b_activations.py`
- `probe_stage16_qwen15b_cpl2.py`
- Qwen2.5-1.5B activation manifest JSON
- Qwen2.5-1.5B probe report JSON + markdown
- Qwen2.5-1.5B CPL2 report JSON + markdown
- `STAGE16_QWEN15B_SUMMARY_20260519.md`
- `STAGE16_CLAIMS_MATRIX_20260519.md`
- README Stage 16 entry
- Claude audit handoff in `docs/working/agent_exchange/inbox_claude.md`

Do not commit:

- Full Stage 16 activation `.npz` binary.

## Audit Questions

1. Were gates committed before the run?
2. Was layer choice made by validation before test reporting?
3. Does Qwen2.5-1.5B pass, fail, or land grey under the exact CPL2 thresholds above?
4. Are raw-symbol controls null or unexpectedly active?
5. Does wording keep Stage 16 as readable-prefix likelihood conditioning, not hidden-neuron steering or raw-symbol understanding?
