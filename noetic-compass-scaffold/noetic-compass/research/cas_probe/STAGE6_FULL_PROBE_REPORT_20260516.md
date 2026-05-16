# Stage 6.4 - Full Role-Bound Noetic Probe Evaluation

**Status:** PASS on the locked discriminative gate. This is not yet causal
evidence.

## Plain-English Result

The Stage 6 question was:

> If the same sentence contains two possible CAS meanings, can an open model's
> hidden state at the focused `A` or `B` token tell which noetic role is being
> selected, better than plain text baselines?

On the locked 3,000-row Stage 6 fixture, the answer is yes.

The validation-selected activation probe reached `73.9%` test accuracy. The
best validation-selected text baseline reached `46.4%` test accuracy. The lift
is `+27.5 percentage points`, and the paired McNemar test is extremely strong
(`p = 8.14e-50`).

This is the first Stage 6 result that cleanly clears the "above text baseline"
gate.

## Command

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\evaluate_stage6_role_bound_full.py --input stage6_role_bound_full_20260516.jsonl --activations stage6_role_bound_full_activations_20260516.npz --out-report stage6_role_bound_full_probe_report_20260516.json
```

## Locked Inputs

Dataset:

```text
stage6_role_bound_full_20260516.jsonl
```

Dataset SHA-256:

```text
450086d137396cd9906f8458ab37ead041ead1842fbfa866d47326befd155710
```

Activation artifact:

```text
stage6_role_bound_full_activations_20260516.npz
```

Activation SHA-256:

```text
6641e28519eefeadc66d053c4996075d640401f6f650ef14b80435ccd57206f2
```

The activation binary is local-only because it is `217,947,380` bytes, above
GitHub's 100 MB per-file limit. The manifest and report are committed.

## Split

| Split | Rows |
|---|---:|
| Train | 1,200 |
| Val | 400 |
| Test | 1,400 |

Each split is class-balanced across all ten noetics.

## Baselines

Language baselines:

| Baseline | Val Acc | Test Acc | Test Macro-F1 |
|---|---:|---:|---:|
| Majority | 0.100 | 0.100 | 0.018 |
| Stratified dummy | 0.073 | 0.098 | 0.098 |
| Count vector word 1-2 | 0.500 | 0.439 | 0.353 |
| TF-IDF word 1-2 | 0.500 | 0.470 | 0.314 |
| **TF-IDF char 3-5** | **0.502** | **0.464** | **0.445** |

The headline text baseline is selected by validation accuracy, so the
comparison baseline is `tfidf_char_3_5`.

Metadata baselines:

| Baseline | Val Acc | Test Acc | Test Macro-F1 |
|---|---:|---:|---:|
| Focus only | 0.100 | 0.100 | 0.018 |
| Family + focus | 0.100 | 0.100 | 0.018 |
| Pair + focus | 0.500 | 0.500 | 0.367 |
| Surface + pair + family + focus | 0.500 | 0.500 | 0.333 |

`pair_focus` reaching 0.500 is expected: the pair narrows the answer to two
candidate noetics. It still does not identify which role in the sentence is
semantically correct.

## Activation Headline

The headline is validation-selected, not post-hoc test-selected:

| Field | Value |
|---|---|
| Readout | `focus_token` |
| Layer | 5 |
| Val accuracy | 0.9925 |
| Test accuracy | 0.7393 |
| Test macro-F1 | 0.7409 |

The focus-token readout has the strongest validation result. Some later layers
have higher locked-test accuracy after the fact (`focus_token` layer 8 reaches
0.779), but they are not the headline because they were not validation-selected.

## Gate Check

Predeclared gate:

- activation test accuracy - best text test accuracy >= 5 percentage points
- McNemar exact binomial p < 0.05
- focus-only metadata baseline <= 0.15

Result:

| Gate | Result |
|---|---:|
| Test lift over best text | +0.275 |
| McNemar p vs best text | 8.14e-50 |
| Focus-only metadata test acc | 0.100 |
| Verdict | `ROLE_BOUND_PROBE_RELIABLY_ABOVE_TEXT_BASELINE` |

Paired contingency vs `tfidf_char_3_5`:

| Case | Count |
|---|---:|
| Both correct | 489 |
| Activation only correct | 546 |
| Text only correct | 161 |
| Both wrong | 204 |
| Discordant total | 707 |

## What This Means

This supports the reserved claim:

> On the locked Stage 6 role-bound fixture, Pythia-160M hidden states at the
> focus token recover the intended noetic role substantially better than plain
> text and metadata baselines.

That is a meaningful black-box result because the signal is not merely in the
final answer text. It is recoverable from an internal hidden state of an open
model.

## What This Does Not Mean Yet

This does **not** prove:

- Pythia has native CAS reasoning.
- CAS has solved the black box problem.
- The detected direction causes the model's answer.
- Glass House AI is ready as a product.

It is discriminative evidence: a probe can read the role-bound noetic label
from internal activations. The next needed evidence is causal: change or remove
the detected signal and test whether behavior changes in the predicted way.

## Next Step

Stage 6.5 should run a causal follow-up:

1. Train the focus-token layer-5 probe from the locked train split.
2. Remove or reduce the probe-readable noetic subspace on held-out test rows.
3. Compare against random orthogonal removals.
4. Measure whether the role-bound prediction and/or generated continuation
   changes in a noetic-consistent direction.

If that passes, the wording can move from:

> "CAS can read a role-bound internal signal."

to:

> "CAS can read and test a role-bound internal signal that appears to matter."
