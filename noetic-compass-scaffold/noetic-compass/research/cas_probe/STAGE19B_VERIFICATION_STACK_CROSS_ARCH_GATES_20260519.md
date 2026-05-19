# Stage 19B Verification Stack Cross-Architecture Gates

Date: 2026-05-19

Branch: `experiment/cas-probe-pythia`

Status: `PRE_REGISTERED_NOT_RUN`

## Purpose

Stage 19B tests whether the runtime-safe CAS Verification Stack from Stage 19A
transfers across architecture families. Stage 19A produced a `PASS_STRONG`
verdict on Pythia-160M against the Stage 12 formula-family fixture:

- accepted accuracy `0.9978`
- coverage `0.8760`
- silent error rate `0.0022`
- suppress rate `0.1240`

Stage 19B reruns the same methodology — selected-layer multi-readout ensemble
plus non-oracle trace stability — on OLMo-1B (Stage 15) and Qwen2.5-1.5B
(Stage 16) activation artifacts and asks whether the 99.78% / 12.4%
accept/suppress profile transfers to the OLMo and Qwen architecture families.

This is a verification-stack replication. It is not a new activation capture,
not a new CPL2 bridge test, and not a visible-text generation test.

## Methodology Reuse

The Stage 19B runners are near-clones of `run_stage19a_formula_verification_stack.py`,
swapping only the model/activation/fixture paths. Decision logic, status tiering,
and suppression-reason taxonomy are preserved exactly. Reserved language matches
Stage 19A:

- `accepted`, `suppressed`, `decision_tier`, `suppression_reasons`
- status names: `PASS_CLEAN`, `PASS_STRONG_WITH_PRECOMMIT_CAVEAT`, `NULL`, `GREY`

Runtime states are non-oracle. The runner does NOT introduce `stable_correct`
or `stable_wrong` oracle states. Gold labels are used only after the fact to
score accepted accuracy and silent errors.

## Locked Inputs

### Shared fixture

- `stage7_foundation_pilot_20260517.jsonl`
- Input sha256: `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250`
- Records: `4368`
- Labels: 28-Foundation (`F1T` ... `F7E`)

The Stage 15 and Stage 16 activation artifacts were both captured against
this fixture. The Stage 12 formula-family fixture does NOT transfer to OLMo
or Qwen because no formula-family activations exist for those models. The
Foundation fixture is the correct cross-architecture test fixture per architecture.

### Per-model activation artifacts

| Model key | Model source | Revision | Activation file | Manifest |
|---|---|---|---|---|
| `olmo1b` | `allenai/OLMo-1B-hf` | `aee7752d9c08ee4775e9b0091426d8410e8f6a89` | `stage15_olmo1b_activations_20260519.npz` | `stage15_olmo1b_activations_manifest_20260519.json` |
| `qwen15b` | `Qwen/Qwen2.5-1.5B` | `8faed761d45a263340a0528343f099c05c9a4323` | `stage16_qwen15b_activations_20260519.npz` | `stage16_qwen15b_activations_manifest_20260519.json` |

OLMo activation sha256: `b2fbf6661c4b3b9067bdc74edb27c587cee498bc9b6717ee4f74682d07a47e8b`.

Qwen activation sha256: `ccb79afe5a3215f0f6aac828c574a0d14cf8115ab769489ea4269c70ce43fe8e`.

Stored layer positions:

- OLMo: 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 (11 layers)
- Qwen: 8 through 28 inclusive (21 layers)

The large activation binaries remain git-ignored. Manifests and SHA-256 values
remain the provenance record.

### Run scripts

- `run_stage19b_olmo_verification_stack.py`
- `run_stage19b_qwen_verification_stack.py`

### Output JSON paths

- `stage19b_olmo_verification_stack_20260519.json`
- `stage19b_qwen_verification_stack_20260519.json`

### Output Markdown paths

- `STAGE19B_OLMO_VERIFICATION_STACK_20260519.md`
- `STAGE19B_QWEN_VERIFICATION_STACK_20260519.md`

### Random seed

The runner does not set a Python or numpy RNG seed directly; the underlying
`evaluate_stage7_factor_check._fit_readout` uses the scikit-learn default
RandomState behavior. Determinism for the runner is provided by the locked
activation artifact, the locked train/val/test split derived from sample IDs,
and the locked sklearn solver. Re-running the same script against the same
activation artifact reproduces the same JSON output by inspection. Stage 19A
already verified this property on Pythia (deterministic rerun under commit
`05ac687` matched the original numerically).

## Runtime Components

### 1. Multi-Readout Foundation Ensemble

Train a 28-way Foundation readout for each stored layer at each readout
position:

- `focus_token`
- `final_token`
- `mean_over_seq_len`

For each readout position, select the layer by validation accuracy only. Break
ties by validation macro-F1, then by earlier stored layer position. Test labels
must not select layers.

At runtime, accept a 28-way Foundation ensemble candidate only when at least
two of the three selected readouts agree. If all three disagree, suppress as
`ensemble_all_disagree`.

### 2. Non-Oracle Trace Stability

For the 28-way Foundation task, compute per-readout trace states over every
stored layer:

- `stable`: majority label covers at least 70% of stored layers and the longest
  same-label run is at least 5 layers.
- `uncertain`: at least half of layers are low-confidence (`max p < 0.45`) or
  high-entropy (`entropy > 0.70 * max_entropy`).
- `conflicted`: at least 5 label switches or no majority over half the layers.
- `drifting`: neither stable nor conflicted, but the label changes over depth.

Accept `high` decision_tier only when the Foundation ensemble candidate matches
the `focus_token` stable trace label.

Accept `medium` decision_tier only when at least two readout traces are stable
and agree with the ensemble candidate, with no `uncertain` or `conflicted`
readout trace.

Suppress all other cases with a `trace_unstable` reason composed of the
unstable readout names (matching Stage 19A taxonomy exactly).

## Pre-Registered Gate Thresholds

Per-model thresholds (apply independently to OLMo and Qwen runs):

| Outcome | Accepted accuracy | Silent error rate | Suppress rate | Meaning |
|---|---:|---:|---:|---|
| `PASS_CLEAN` | `>= 0.95` | `<= 0.05` | `<= 0.30` | Verification stack methodology transfers cleanly to this architecture. |
| `NULL` | `< 0.85` | any | any | Stack does not improve usable quality on this architecture. |
| `NULL` (baseline-floor) | `< best single selected readout` | any | any | Stack underperforms the strongest single readout — no value added. |
| `GREY` | anything between `0.85` and `0.95`, or PASS_CLEAN thresholds partially missed | otherwise | otherwise | Mixed result requiring audit before claim use. |

The runner emits `PASS_CLEAN`, `NULL`, or `GREY`. The Stage 19A precedent
`PASS_STRONG_WITH_PRECOMMIT_CAVEAT` is reserved for a synthesizer to apply
post-hoc only if the runner was launched before this gate document was
committed; the runner itself never emits that status.

## Combined Cross-Architecture Verdict

The combined Stage 19B verdict is computed from the two per-model verdicts:

- `PASS_CLEAN_CROSS_ARCH`: both OLMo and Qwen reach `PASS_CLEAN`.
- `MIXED`: exactly one model reaches `PASS_CLEAN`; the other is `GREY` or `NULL`.
- `NULL_CROSS_ARCH`: neither model reaches `PASS_CLEAN`.
- `GREY_CROSS_ARCH`: both models land in `GREY` (no `NULL`).

The synthesizer applies this verdict after both JSON reports are produced.

## Pre-Registration Discipline

- This gate document MUST be committed before either Stage 19B runner is
  launched. If launched first, the post-hoc status becomes
  `PASS_STRONG_WITH_PRECOMMIT_CAVEAT` for the affected model (mirrors the
  Stage 19A pre-commit caveat handling).
- The thresholds above are locked. No relaxation after looking at any data.
- The runners are committed alongside this gate document so the launch command
  is reproducible byte-for-byte.

## Boundaries

Allowed claim after a `PASS_CLEAN_CROSS_ARCH` result:

> On the locked Foundation fixture, the runtime-safe CAS Verification Stack
> methodology that produced 99.78% accepted accuracy and 12.4% suppression on
> Pythia-160M also produced PASS_CLEAN accept/suppress profiles on OLMo-1B and
> Qwen2.5-1.5B, using only non-oracle runtime signals. The 28-Foundation
> verification methodology transfers across three model families: Pythia, OLMo,
> and Qwen.

Disallowed claims regardless of result:

- CAS has 100% accuracy on any architecture.
- CAS identifies the exact neurons or weights that caused any answer.
- Generation steering or visible-text control is proven by Stage 19B.
- The Stage 19A Pythia formula-family numbers transfer to OLMo or Qwen at the
  same fixture — Stage 19B is on the Foundation fixture, not the formula
  fixture.

## Cost Cap

1 GPU-hour on A6000. Stage 19B reuses the existing activation artifacts and
runs the same probe-fit + Verification-Stack-decision logic. No new model
forward passes. No new training. The activation artifacts have already been
captured by Stages 15 and 16; this run is offline probe inference plus the
Stack decision loop.
