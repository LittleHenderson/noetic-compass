# Stage 15 OLMo-1B Cross-Architecture Gates

**Status:** pre-registered before any Stage 15 OLMo-1B run.

**Branch:** `experiment/cas-probe-pythia`

**Authorization:** user authorized OLMo after the Stage 14 Pythia-2.8B pass.

## Scope

Stage 15 tests whether the eta-to-epsilon CAS Harness bridge transfers outside the Pythia model family.

Authorized:

- Model: `allenai/OLMo-1B-hf`.
- Dataset: frozen Stage 7 original-TKS 28-Foundation fixture, `stage7_foundation_pilot_20260517.jsonl`.
- Activation capture: focus-token, final-token, and mean-token readouts for OLMo-1B layer positions 6 through 16.
- Probe: same sklearn `StandardScaler` + `LogisticRegression(lbfgs, class_weight="balanced")` readout family used in Stage 8 and Stage 14.
- Primary assay: CPL2 likelihood bridge using probe-predicted readable realization prefixes.

Not authorized in this stage:

- Larger OLMo models.
- Pythia-6.9B or Pythia-12B.
- Llama or Qwen.
- Stage 12/13 formula-family reruns on OLMo.
- Hidden-state steering claims.
- Raw CAS-symbol understanding claims.
- Open-ended visible generation-control claims.

Hard cap: 2 GPU-hours on A6000. If projected wall-clock exceeds 90 minutes after model download starts, stop and surface before continuing.

## Frozen References

Pythia-family CPL2 line:

| Model | Delta vs none | Margin over partner | Positive cases |
|---|---:|---:|---:|
| Pythia-160M | `+0.2828` | `+0.6829` | `81/112` |
| Pythia-1B | `+0.5542` | `+1.2460` | `90/112` |
| Pythia-2.8B | `+0.5832` | `+1.3363` | `92/112` |

Stage 15 is not expected to match Pythia-2.8B. It only needs to pass the same defensible CPL2 floor to establish cross-architecture transfer.

## Layer Selection

Capture OLMo-1B hidden states for layer positions `6-16`.

Layer selection rule:

1. Train a 28-way Foundation probe on each candidate layer using the frozen train split.
2. Select the layer with highest validation 28-way Foundation accuracy.
3. If validation accuracy ties within `0.001`, choose the lower-lacunarity layer.
4. Report test accuracy only after the layer is selected.

No test-set-driven layer choice is allowed.

## Primary CPL2 Gate

Run CPL2 on the same 112-row same-register Drive-cycle test pack shape used in Stage 8 and Stage 14: `16` rows per Drive.

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

> The eta-to-epsilon readable-prefix bridge transfers to OLMo-1B at defensible strength.

### NULL

Any one of these is enough for NULL:

- `probe_readable_delta_vs_none < +0.05`
- `probe_readable_minus_partner_readable_margin < +0.10`
- positive-share `< 50/112`

Interpretation:

> The Pythia-family result remains valid, but this run does not establish cross-architecture transfer to OLMo-1B.

### GREY

Anything between PASS_CLEAN and NULL.

Interpretation:

> The result is underpowered or borderline. Do not update cross-architecture claims without a larger pre-registered pack.

## Required Artifacts

Commit:

- `STAGE15_OLMO1B_GATES_20260519.md`
- `capture_stage15_olmo1b_activations.py`
- `probe_stage15_olmo1b_cpl2.py`
- OLMo-1B activation manifest JSON
- OLMo-1B probe report JSON + markdown
- OLMo-1B CPL2 report JSON + markdown
- `STAGE15_OLMO1B_SUMMARY_20260519.md`
- `STAGE15_CLAIMS_MATRIX_20260519.md`
- README Stage 15 entry
- Claude audit handoff in `docs/working/agent_exchange/inbox_claude.md`

Do not commit:

- Full Stage 15 activation `.npz` binary.

## Audit Questions

1. Were gates committed before the run?
2. Was layer choice made by validation before test reporting?
3. Does OLMo-1B pass, fail, or land grey under the exact CPL2 thresholds above?
4. Are raw-symbol controls null or unexpectedly active?
5. Does wording keep Stage 15 as readable-prefix likelihood conditioning, not hidden-neuron steering or raw-symbol understanding?
