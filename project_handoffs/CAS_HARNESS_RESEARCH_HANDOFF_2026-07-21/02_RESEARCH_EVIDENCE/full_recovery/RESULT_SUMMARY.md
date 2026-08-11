# TKS definition-anchor diagnostic: exact result summary

Status: **NOT_LICENSED_DIAGNOSTIC_ONLY**. This was a completed zero-shot definition-anchor diagnostic on exactly `EleutherAI/pythia-160m` revision `50f5173d932e8e61f858120bcb800b97af589f46`. It is not an `ACCEPT` verdict and does not establish semantic-probe validity, prompt-injection detection, output control, cross-architecture universality, 300B execution, or production readiness.

## Sole preregistered primary result

The frozen primary endpoint was Foundation-28 full-class accuracy on the Stage7 test split, using attention-masked mean-token pooling at layer 1. Layer 1 was selected on Stage7 validation only, using D3 and A124 together.

- D3 owner-original definitions: `0.09906462585034014` accuracy (`9.9065%`).
- A124 operational rewrites: `0.09481292517006802` accuracy (`9.4813%`).
- D3 minus A124: `0.0042517006802721136`, or `+0.4252` percentage points.
- Paired cluster-bootstrap 95% CI: `[-0.001275510204081634, 0.010204081632653059]`, or `[-0.1276, +1.0204]` percentage points.

The interval includes zero. This run therefore does not establish a reliable D3 advantage over A124 on the sole primary endpoint. Both point accuracies exceed the 28-way chance level of `0.03571428571428571`, but that fact alone does not validate the definitions semantically.

## Prespecified changed-8 and unchanged-20 analyses

These analyses are secondary sensitivity/negative-control results, not the primary endpoint and not causal estimates.

- Changed 8 classes: D3 `0.03720238095238095`; A124 `0.05654761904761905`; delta `-0.019345238095238096` (`-1.9345` pp); paired cluster-bootstrap 95% CI `[-0.03474798480191032, -0.0058997050147492625]`.
- Unchanged 20 classes: D3 `0.12380952380952381`; A124 `0.11011904761904762`; delta `+0.013690476190476197` (`+1.3690` pp); paired cluster-bootstrap 95% CI `[0.008367701838559087, 0.019093649042066937]`.

The opposite directions matter. Changing eight anchors also moves 28-way decision boundaries for examples whose true classes were not rewritten, so the unchanged-20 result cannot be interpreted as a localized semantic benefit. The changed-8 result does not support the proposition that D3 was uniformly better than A124 for the definitions that actually changed.

## Character TF-IDF surface baseline

On the same Stage7 test full-28 task, the character 3-5-gram TF-IDF baseline scored:

- D3: `0.1054421768707483` (`10.5442%`).
- A124: `0.0824829931972789` (`8.2483%`).
- D3 minus A124: `0.0229591836734694` (`+2.2959` pp).
- Compact CAS comparator: `0.13180272108843538` (`13.1803%`).

The surface baseline's D3-A124 separation is larger than the hidden-state primary separation. That makes lexical/style alignment a live competing explanation; the hidden-state result cannot be presented as uniquely semantic.

## Source-bias boundary

The Stage7 bank was generated from the original TKS Foundation glosses used by D3. The Foundation-28 sensitivity bank was generated with the same DRIVES/REGISTERS vocabulary used by the compact comparator. Neither bank is an independently authored neutral holdout, and Stage7 pairs share broader paraphrase-family and scenario-generator dependencies. Pair-clustered bootstrap intervals do not remove that family-level dependence. These data can measure source-language alignment, but they cannot establish universal semantic transfer.

## Next decisive experiment

Preregister and freeze an independently authored neutral holdout that is not generated from D3, A124, or the compact vocabulary. Match D3 and A124 for length and surface style; preserve a validation-only shared layer-selection rule and a separately untouched paired test set; include surface baselines, a genuine permutation-null distribution, and multiple fixed seeds. Run that experiment first on this exact model revision, then repeat the unchanged frozen protocol on separately qualified architecture adapters. Only those new results can test whether the signal survives source wording and architecture changes.

Evidence recovery itself was verified off-pod: 33 recovered entries matched the pod bundle manifest, with inventory SHA-256 `b44e4457de6763bc41a27aa1b746cbaba19a753f788f472b2fe4ef9546624a93`. The 109,414,103-byte raw NPZ has SHA-256 `454a4f017d56ed393e50d7e88d29486b3379e96ae930a1123698c6275298ead6` and was reopened off-pod with `allow_pickle=False`. Independent object-store durability remains **OPEN**.
