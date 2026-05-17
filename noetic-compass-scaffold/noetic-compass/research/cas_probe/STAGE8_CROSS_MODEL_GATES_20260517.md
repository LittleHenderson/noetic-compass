# Stage 8 Cross-Model Gates: Pythia-1B CPL2 Replication

**Status:** pre-registered before any Stage 8 experiment run.

**Branch:** `experiment/cas-probe-pythia`

**Authorization:** `AUTHORIZED: yes` in
`docs/working/agent_exchange/decisions.md` at `2026-05-17T22:00Z`.

## Scope

This Stage 8 run tests whether the Stage 7 eta-to-epsilon CAS Harness bridge
replicates from Pythia-160M to Pythia-1B.

Authorized:

- Model: `EleutherAI/pythia-1b` only.
- Dataset: existing Stage 7 original-TKS 28-Foundation fixture
  `stage7_foundation_pilot_20260517.jsonl`.
- Activation capture: focus-token, final-token, and mean-token readouts for
  Pythia-1B layers 6 through 13.
- Probe: same sklearn `StandardScaler` + `LogisticRegression(lbfgs,
  class_weight="balanced")` readout family used in Stage 7.
- Primary assay: CPL2 likelihood bridge using probe-predicted readable
  realization prefixes.
- Optional sweetener: CPL3/CPL4 visible-text checks, exploratory only.

Not authorized:

- Pythia-1.4B, 2.8B, 6.9B, 12B, or any other larger Pythia.
- Cross-architecture runs such as Llama, OLMo, or Qwen.
- Glass House memo refresh before Stage 8 verdict and audit.
- Any threshold edits after this file is committed.

Hard cap: 2 GPU-hours on A6000. If wall-clock run time is projected to exceed
90 minutes, stop and surface before continuing.

## Frozen Baseline

Pythia-160M CPL2 result:

- Probe-readable delta vs none: `+0.2828`.
- Probe-readable minus partner-readable margin: `+0.6829`.
- Positive cases: `81/112`.
- Status: `PROBE_PREDICTED_CAS_PREFIX_CONDITIONS_PYTHIA`.

Stage 8 thresholds are intentionally about half-strength relative to the
Pythia-160M effect. A weaker effect may be scientifically interesting, but it
is not enough for a cross-scale product claim.

## Layer Selection

Capture Pythia-1B hidden states for layers 6 through 13. For each candidate
layer, train the 28-way Foundation probe on the frozen train split and score
on the frozen validation split.

Layer selection rule:

1. Choose the layer with highest validation 28-way Foundation accuracy.
2. If validation accuracy ties within `0.001`, choose the lower-lacunarity
   layer.
3. Test accuracy is reported only after the layer is selected.

No test-set-driven layer choice is allowed.

## Primary CPL2 Gate

Run CPL2 on the same 112-row same-register Drive-cycle test pack shape used
in Stage 7: `16` rows per Drive, conditions:

- `none`
- `gold_readable`
- `probe_readable`
- `partner_readable`
- `gold_raw`
- `probe_raw`
- `partner_raw`

The load-bearing condition is `probe_readable`.

Primary statistics:

- Probe-readable mean likelihood margin delta vs no-prefix.
- Probe-readable mean margin minus partner-readable mean margin.
- Positive-share for probe-readable per-row deltas vs no-prefix.
- Paired Wilcoxon signed-rank test on per-row probe-readable deltas vs
  no-prefix.

Use paired statistics. Do not substitute unpaired aggregate empirical-p for
the primary gate.

### PASS_CLEAN

All must pass:

- `probe_readable_delta_vs_none > +0.15`
- paired Wilcoxon `p < 0.05`
- `probe_readable_minus_partner_readable_margin > +0.30`
- positive-share `> 60/112`

Interpretation:

> The eta-to-epsilon readable-prefix bridge transfers from Pythia-160M to
> Pythia-1B at defensible strength.

### NULL

Any one of these is enough for NULL:

- `probe_readable_delta_vs_none < +0.05`
- `probe_readable_minus_partner_readable_margin < +0.10`
- positive-share `< 50/112`

Interpretation:

> The Pythia-160M result remains valid, but the cross-scale bridge is not
> established on Pythia-1B.

### GREY

Anything between PASS_CLEAN and NULL.

Interpretation:

> The result is underpowered or borderline. Do not refresh strategy claims.
> Rerun only with a pre-registered larger pack of at least `240` prompts.

## Optional CPL3/CPL4 Gate

Optional visible-text checks are exploratory. They must not change the CPL2
verdict.

PASS_CLEAN visible-text sweetener:

- Probe-readable beats wrong-partner by at least `+0.25` on the visible-text
  margin, matching the Stage 7.CPL3 floor.

If CPL3/CPL4 pass but CPL2 fails, do not call Stage 8 a bridge replication.
If CPL2 passes but CPL3/CPL4 fail, Stage 8 is still a likelihood-bridge pass,
not an open-ended generation-control pass.

## Required Artifacts

Commit:

- `capture_stage8_pythia1b_activations.py`
- `probe_stage8_pythia1b_cpl2.py`
- `STAGE8_CROSS_MODEL_GATES_20260517.md`
- Pythia-1B activation manifest JSON
- Pythia-1B probe report JSON + markdown summary
- Pythia-1B CPL2 report JSON + markdown summary
- Optional CPL3/CPL4 reports if run
- `STAGE8_PYTHIA1B_SUMMARY_20260517.md`
- README Stage 8 row
- `STAGE8_CLAIMS_MATRIX_20260517.md`
- Claude audit handoff in `docs/working/agent_exchange/inbox_claude.md`

Do not commit:

- Full Stage 8 activation `.npz` binary. It is expected to be too large for
  GitHub. Commit the manifest and SHA-256 instead.

## Audit Questions

1. Was layer choice locked by validation score before test reporting?
2. Was lacunarity computed on the selected Pythia-1B representation and
   compared against Stage 7's `0.021` reference?
3. Does paired Wilcoxon pass the pre-registered CPL2 gate?
4. Is the result PASS_CLEAN, NULL, or GREY under the exact thresholds above?
5. Does wording avoid hidden-neuron steering, raw CAS-symbol understanding, and
   open-ended generation-control claims unless separately proven?
