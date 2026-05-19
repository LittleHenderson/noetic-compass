# Stage 14 Pythia-2.8B Scale Gates

**Status:** pre-registered before any Stage 14 Pythia-2.8B run.

**Branch:** `experiment/cas-probe-pythia`

**Authorization:** user authorized this run on 2026-05-18 with: "ok try it and then we'll try it on a different architecture."

## Scope

Stage 14 tests whether the Stage 8 eta-to-epsilon CAS Harness bridge transfers from Pythia-1B to Pythia-2.8B.

Authorized:

- Model: `EleutherAI/pythia-2.8b` only.
- Dataset: frozen Stage 7 original-TKS 28-Foundation fixture, `stage7_foundation_pilot_20260517.jsonl`.
- Activation capture: focus-token, final-token, and mean-token readouts for Pythia-2.8B layer positions 12 through 27.
- Probe: same sklearn `StandardScaler` + `LogisticRegression(lbfgs, class_weight="balanced")` readout family used in Stage 8.
- Primary assay: CPL2 likelihood bridge using probe-predicted readable realization prefixes.

Not authorized in this stage:

- Pythia-6.9B or Pythia-12B.
- Cross-architecture models such as OLMo, Llama, or Qwen.
- Stage 12/13 formula-family reruns on Pythia-2.8B.
- Hidden-state steering claims.
- Raw CAS-symbol understanding claims.
- Open-ended visible generation-control claims.

Hard cap: 2 GPU-hours on A6000. If projected wall-clock exceeds 90 minutes after model download starts, stop and surface before continuing.

## Frozen References

Pythia-160M CPL2:

- Probe-readable delta vs none: `+0.2828`.
- Probe-readable minus partner-readable margin: `+0.6829`.
- Positive cases: `81/112`.

Pythia-1B CPL2:

- Probe-readable delta vs none: `+0.5542`.
- Probe-readable minus partner-readable margin: `+1.2460`.
- Positive cases: `90/112`.
- Status: `PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES`.

Stage 14 is a scale-replication test, not a new method.

## Layer Selection

Capture Pythia-2.8B hidden states for layer positions `12-27`. This window is scaled up from the Pythia-1B candidate window and spans mid-to-late layers of the deeper model.

Layer selection rule:

1. Train a 28-way Foundation probe on each candidate layer using the frozen train split.
2. Select the layer with highest validation 28-way Foundation accuracy.
3. If validation accuracy ties within `0.001`, choose the lower-lacunarity layer.
4. Report test accuracy only after the layer is selected.

No test-set-driven layer choice is allowed.

## Primary CPL2 Gate

Run CPL2 on the same 112-row same-register Drive-cycle test pack shape used in Stage 8: `16` rows per Drive.

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

> The eta-to-epsilon readable-prefix bridge transfers to Pythia-2.8B at defensible strength.

### NULL

Any one of these is enough for NULL:

- `probe_readable_delta_vs_none < +0.05`
- `probe_readable_minus_partner_readable_margin < +0.10`
- positive-share `< 50/112`

Interpretation:

> The Pythia-160M and Pythia-1B results remain valid, but this run does not establish transfer to Pythia-2.8B.

### GREY

Anything between PASS_CLEAN and NULL.

Interpretation:

> The result is underpowered or borderline. Do not update cross-scale claims without a larger pre-registered pack.

## Required Artifacts

Commit:

- `STAGE14_PYTHIA28B_GATES_20260518.md`
- `capture_stage14_pythia28b_activations.py`
- `probe_stage14_pythia28b_cpl2.py`
- Pythia-2.8B activation manifest JSON
- Pythia-2.8B probe report JSON + markdown
- Pythia-2.8B CPL2 report JSON + markdown
- `STAGE14_PYTHIA28B_SUMMARY_20260518.md`
- `STAGE14_CLAIMS_MATRIX_20260518.md`
- README Stage 14 entry
- Claude audit handoff in `docs/working/agent_exchange/inbox_claude.md`

Do not commit:

- Full Stage 14 activation `.npz` binary.

## Audit Questions

1. Were gates committed before the run?
2. Was layer choice made by validation before test reporting?
3. Does Pythia-2.8B pass, fail, or land grey under the exact CPL2 thresholds above?
4. Does the effect strengthen, weaken, or stay similar relative to Pythia-1B?
5. Does the wording keep Stage 14 as readable-prefix likelihood conditioning, not hidden-neuron steering or raw-symbol understanding?
