# Stage 19B Cross-Architecture Foundation Verification Stack Gates

Date: 2026-05-19

Branch: `experiment/cas-probe-pythia`

Status: `PRE_REGISTERED_NOT_RUN_V2`

## Revision Note

The first Stage 19B runner was pre-registered and launched, but produced no
report artifact after more than 100 minutes of CPU time. That no-result run was
terminated. This v2 gate is committed before any successful Stage 19B result and
tightens the compute scope without changing the product question.

## Purpose

Stage 19B tests whether the runtime-safe CAS Verification Stack from Stage 19A
transfers to the Stage 15/16 Foundation fixtures on non-Pythia architectures:

- `allenai/OLMo-1B-hf`
- `Qwen/Qwen2.5-1.5B`

This is a verification-stack replication. It is not a new hidden-state capture,
not a new CPL2 bridge test, and not a visible-text generation test.

## Locked Inputs

Shared fixture:

- `stage7_foundation_pilot_20260517.jsonl`

Model activation artifacts:

| Model key | Activation file | Manifest |
|---|---|---|
| `olmo1b` | `stage15_olmo1b_activations_20260519.npz` | `stage15_olmo1b_activations_manifest_20260519.json` |
| `qwen15b` | `stage16_qwen15b_activations_20260519.npz` | `stage16_qwen15b_activations_manifest_20260519.json` |

The large activation binaries remain git-ignored. Manifests and SHA-256 values
remain the provenance record.

## Runtime Components

Gold labels may be used only after the fact for scoring. They must not drive
runtime acceptance.

### 1. Multi-Readout Foundation Ensemble

Train a 28-way Foundation readout for each stored layer and readout position:

- `focus_token`
- `final_token`
- `mean_over_seq_len`

For each readout position, select the layer by validation accuracy only. Break
ties by validation macro-F1, then by earlier stored layer position. Test labels
must not select layers.

At runtime, accept a 28-way Foundation ensemble candidate only when at least two
of the three selected readouts agree. If all three disagree, suppress as
`foundation_ensemble_all_disagree`.

### 2. Drive/Register Factor Decomposition

Independently train:

- a 7-way Drive readout (`F1` through `F7`)
- a 4-way Register readout (`T`, `A`, `f`, `E`)

Drive/Register are consistency checks, not fresh layer-discovery claims in this
run. To avoid a second and third full all-layer scan, train each Drive/Register
readout at the Foundation-selected layer for the same readout position. This
anchors factor consistency to the exact hidden-state depth used by the 28-way
Foundation vote.

At runtime:

1. Require Drive majority agreement across the three selected readouts.
2. Require Register majority agreement across the three selected readouts.
3. Recompose the factor result as `F{drive}{register}`.
4. Require recomposed Foundation to equal the 28-way Foundation ensemble result.

If factor recomposition disagrees with the 28-way result, suppress as
`factor_conflicted`. No post-hoc confidence margin is allowed in this run.

Register is used only as an internal consistency signal. Stage 7.2 already
showed Register is text-explained, so Stage 19B must not present Register as a
fresh beyond-text claim.

### 3. Non-Oracle Trace Stability

For the 28-way Foundation task, compute per-readout trace states over every
stored layer:

- `stable`: majority label covers at least 70% of stored layers and the longest
  same-label run is at least 5 layers.
- `uncertain`: at least half of layers are low-confidence (`max p < 0.45`) or
  high-entropy (`entropy > 0.70 * max_entropy`).
- `conflicted`: at least 5 label switches or no majority over half the layers.
- `drifting`: neither stable nor conflicted, but label changes over depth.

Accept high confidence only when the Foundation ensemble candidate matches the
`focus_token` stable trace label.

Accept medium confidence only when at least two Foundation readout traces are
stable and agree with the Foundation ensemble candidate, with no
`uncertain`/`conflicted` Foundation trace.

Suppress all other cases as a trace-instability reason.

## Metrics

Report per model and aggregate:

- selected layers for Foundation, Drive, Register by readout position
- factor-layer selection mode (`foundation_selected_layer`)
- best single selected Foundation accuracy
- ensemble-only accepted accuracy and coverage
- factor-consistent accepted accuracy and coverage
- final stack accepted accuracy and coverage
- silent error rate over accepted examples
- suppressed rate and suppression reasons
- accepted Drive and Register accuracy for accepted examples

## Pass Tiers

Use the same product-safety thresholds as Stage 19A.

| Tier | Accepted Foundation accuracy | Coverage | Silent error rate | Meaning |
|---|---:|---:|---:|---|
| `PASS_STRONG` | `>= 0.970` | `>= 0.850` | `<= 0.030` | Stack transfers at high precision without suppressing too much. |
| `PASS_BOUNDED` | `>= 0.960` | `>= 0.800` | `<= 0.040` | Stack transfers as a high-precision verifier but misses the strong tier. |
| `DIAGNOSTIC_ONLY` | any | `< 0.800` | any | Stack is mainly a flagger on this model. |
| `NULL` | `< best single selected Foundation accuracy` | any | any | Stack does not improve usable quality over the best single Foundation readout. |
| `GREY` | otherwise | otherwise | otherwise | Mixed result requiring audit before claim use. |

Overall Stage 19B status:

- `PASS_STRONG_CROSS_ARCH`: OLMo and Qwen both reach `PASS_STRONG`.
- `PASS_BOUNDED_CROSS_ARCH`: both models reach either `PASS_STRONG` or
  `PASS_BOUNDED`.
- `MIXED`: one model passes and one does not.
- `NULL`: neither model passes.

## Boundaries

Allowed claim after pass:

> On the locked OLMo and Qwen Foundation fixtures, the runtime-safe CAS
> Verification Stack accepted X% of examples at Y% accuracy and suppressed
> conflicted cases with explicit reasons, using only non-oracle runtime signals.

Disallowed claims:

- CAS has 100% accuracy.
- CAS identifies exact neurons or exact weights that caused the answer.
- Register readout is beyond-text evidence in this run.
- Generation steering or visible-text control is proven by Stage 19B.
