# GPT-NeoX-20B TKS40 Guarded Balanced-Logistic Result - 2026-05-27

## Status

This is a **packet-ready 40-Element readout report**, not a full CAS Harness
ACCEPT/SUPPRESS verdict.

The guarded evaluator was run on RunPod against the balanced source-derived
TKS40 activation dataset:

- Dataset:
  `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_tks40_400_layers_0_43.npz`
- Metadata:
  `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_tks40_400_layers_0_43.metadata.json`
- Report:
  `docs/working/gpt_neox_20b_tks40_balanced_logistic_eval_guarded_20260527.json`
- Archive:
  `D:\tksCAS-archive\gpt_neox_20b_tks40_balanced_logistic_guarded_20260527\`
- Report SHA256:
  `89911A513AE9F74DB66A2623BABF9BC78EE7407D40455C127B6DFB74FF23A0AD`

## Method

The evaluator used the original closure readout family:

- `StandardScaler`
- `LogisticRegression(class_weight="balanced", solver="lbfgs")`
- group-aware split by stripped base prompt
- majority, shuffled-label, and text-hash controls
- strict `--require-balanced-40e` guard

## Guard Result

The strict 40E guard passed:

- Status: `packet_ready_evaluation_completed`
- Packet ready: `true`
- Populated cells: `40 / 40`
- Minimum samples per cell: `10`
- Missing cells: `0`
- Sparse cells: `0`

## Headline Numbers

| Metric | Value |
| --- | ---: |
| Best layer | `1` |
| Hidden readout accuracy | `97.50%` |
| Hidden readout macro-F1 | `97.81%` |
| Majority baseline | `3.75%` |
| Shuffled-label mean | `1.75%` |
| Shuffled-label max | `3.75%` |
| Text-hash baseline | `100.00%` |
| Pythia-160M comparator | `89.80%` |

## Interpretation

This is a strong source-surface/readout result for the balanced TKS40 axis on
real GPT-NeoX-20B hidden states. The hidden-state readout is far above majority
and shuffled-label controls and above the Pythia-160M 40-Element readout
comparator.

The text-hash baseline is also `100.00%`. That means the current source-derived
TKS40 prompt library is text-separable. This is not a failure by itself because
the TKS definitions are the approved English surface of the axis, but it limits
the claim:

- Allowed claim: real 20B hidden states carry a very strong, balanced TKS40
  readout signal under the original balanced-logistic method.
- Not allowed from this report alone: CAS beats text-only baselines on TKS40.
- Not allowed from this report alone: a production ACCEPT/SUPPRESS verdict.

A follow-up diagnostic confirmed this with an interpretable text-only
classifier: `CountVectorizer(1-2 grams) +
LogisticRegression(class_weight="balanced")` also reached `100.00%` heldout
accuracy with `0` train/test group overlap. The diagnostic report is:
`docs/working/tks40_text_baseline_diagnostic_20260527.json`.

## Next

To promote TKS40 into a fuller Evidence Packet, merge this readout report with:

1. the existing TKS40 activation-cover ablation report,
2. matched random and wrong-cover controls,
3. an output-effect or eta-to-epsilon bridge layer for TKS40,
4. a conservative verifier decision that remains `FLAG_FOR_HUMAN_REVIEW` unless
   the Stage 19/20/21 product verifier is attached.

For a future TKS40 headline claim, first build a hardened `tks40_balanced_v1`
scenario library where compact class glosses are not repeated directly and the
pre-registered text-baseline ceiling is `<= 60%`.

Follow-up: the original Pythia-era Stage 9 40E fixture was regenerated from
commit `be9b4a3` and passed the modern diagnostic at `49.24%` text-only
accuracy. The blocked text-baseline issue is therefore specific to the new
compact-gloss TKS40 v0 library, not to the original Stage 9 fixture design.
