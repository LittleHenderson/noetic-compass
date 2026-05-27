# TKS40 Text Baseline Diagnostic - 2026-05-27

## Status

The concern is confirmed. The current balanced TKS40 scenario library is too
lexically separable to support a "CAS hidden readout beats surface text" claim.

This does **not** invalidate the S7-F28 eta-to-epsilon bridge result or the
existing Evidence Packet path. It means the TKS40 readout packet must stay
guarded until the TKS40 eval set is hardened.

## Command

```powershell
python live-trace-worker\scripts\diagnose_tks40_text_baseline.py `
  --scenario live-trace-worker\scenarios\tks40_balanced_v0_20260526.json `
  --output docs\working\tks40_text_baseline_diagnostic_20260527.json `
  --top-k 12 `
  --samples-per-label 3
```

## Result

| Check | Result |
| --- | ---: |
| Scenarios | `400` |
| Classes | `40 / 40` |
| Samples per class | `10` |
| Train / test split | `320 / 80` |
| Unique prompt groups | `400` |
| Train/test group overlap | `0` |
| Text features | `1,072` |
| Text-only test accuracy | `100.00%` |
| Text-only macro-F1 | `100.00%` |

The split is clean: no train/test group overlap. The failure is therefore not
an obvious train/test duplication bug. The scenario text itself carries enough
class-specific wording for a text-only classifier to recover every heldout
label.

## What Leaked

The top predictive text features are source-gloss phrases that map cleanly to a
single TKS40 class. Examples:

- `^0|P`: `true self`, `unseen matter`, `soul-state`, `record`
- `^2|P`: `virtue`, `draws`, `highest aim`, `quiets`
- `^7|C`: `recurring thought`, `ego-state`, `frequency`
- `^9|P`: `exoteric`, `outer symbol`, `empty appearance`, `shell`

These are not fake labels. They are source-derived English. The problem is that
the eval set repeats compact class glosses directly, so text-only classification
becomes a lookup task.

## Claim Discipline

Allowed from the current TKS40 report:

- Real GPT-NeoX-20B hidden states carry a very strong balanced TKS40 signal.
- The balanced-logistic hidden readout reached `97.50%` on the current library.
- The result beats majority and shuffled-label controls.

Not allowed from the current TKS40 report:

- CAS beats text-only baselines on TKS40.
- TKS40 is closed as a full CAS Harness Evidence Packet.
- TKS40 proves universality by itself.

## Required Fix

Build `tks40_balanced_v1` before using TKS40 as a headline comparator:

1. Keep the original TKS A1-D10 definitions as the label source.
2. Stop injecting compact class glosses directly into every prompt.
3. Write concrete situations that instantiate the class without naming the
   defining phrase.
4. Add lexical distractors: include words from the wrong class inside denial,
   contrast, quotation, or irrelevant-context frames.
5. Group splits by semantic seed so paraphrases of the same case cannot cross
   train/test.
6. Increase volume to at least `25` examples per class for the next pass, and
   `50+` per class for the real headline set.
7. Pre-register a text-baseline ceiling: target `<= 60%` before claiming
   hidden-state readout beats surface text.

## Plain-English Explanation

The current TKS40 test is like giving a student a multiple-choice test where
each question contains the answer phrase. The student can score perfectly
without understanding the subject. The model's hidden states may still contain
real structure, but this eval set cannot prove that the hidden structure beats
surface wording.

The fix is not to abandon TKS definitions. The fix is to turn the definitions
into varied real situations, then prove a text-only classifier cannot solve the
task before checking whether hidden states can.

## Follow-Up: Original Fixtures

A follow-up diagnostic ran the same modern text-only check on the original
Pythia-era fixtures:

- Original Stage 9 40E: `49.24%` text-only accuracy, gate passed.
- Original Stage 7 Foundation-28: `54.08%` text-only accuracy, gate passed.

So the blocked result is specific to the new compact-gloss
`tks40_balanced_v0_20260526.json` library. The original role-bound
counterfactual fixture design remains a usable text-baseline adversary under
the modern diagnostic.

See:
`docs/working/original_stage7_stage9_text_baseline_diagnostics_20260527.md`.
