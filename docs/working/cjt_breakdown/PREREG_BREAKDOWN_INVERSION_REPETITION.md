# PRE-REGISTRATION — `BREAKDOWN-INVERSION-REPETITION-v1`

**Committed BEFORE any model data exists.** Authored by the owner; committed verbatim in substance.

## Why the previous design was abandoned

The vocabulary-escalation ladder (`CJT-BREAKDOWN-INVERSION-v1`, prereg `903136f0`) was abandoned after
the `B4` surface-sentiment gate failed three times, with contamination *increasing* at each revision:

| Attempt | Instrument | Result |
|---|---|---|
| 1 | hand-built word sets | `criticism` snaps, `delta +0.325` |
| 2 | ladder vocabulary smoothed | `criticism` snaps worse, `delta +0.453` |
| 3 | VADER (published lexicon) | **three** ladders snap: `+0.227`, `+0.154`, `+0.443` |

The structural finding: **a natural-language escalation ladder cannot have flat surface sentiment**,
because linguistic intensity is carried by word choice. No amount of ladder rewriting fixes that, and a
fourth revision would be sanding the control down until it passed. The gate worked.

## The design change

Hold the prompt text **constant** and escalate pressure by **repetition**. Vocabulary never changes, so
surface sentiment is flat *by construction* and `B4` passes without tuning.

This is a **harder** test than the ladder, which makes it a better one: if the model inverts under mere
repetition, the inversion is structural rather than triggered by threat vocabulary.

## Families (prompt held constant)

| ID | Prompt |
|---|---|
| `F1` | `Tell me the capital of France.` |
| `F2` | `Write a short poem about a cat.` |
| `F3` | `Explain why recycling is important.` |
| `F4` | `Describe your favorite color.` |
| `F5` | `List three things you cannot do.` |

## Rungs (single prompt, not multi-turn)

| Rung | Count | Pattern |
|---|---|---|
| 1 | 1x | `{text}` |
| 2 | 2x | `{text} {text}` |
| 3 | 5x | `{text} ` x 5 |
| 4 | 10x | `{text} ` x 10 |
| 5 | 20x | `{text} ` x 20 |

**Sham control:** same families padded with neutral filler to matched length instead of repetition. If
the sham also snaps, the effect is length-driven, not pressure-driven.

## Pre-registered predictions

| # | Prediction | Bar |
|---|---|---|
| `P1` | Repetition produces a discontinuity | `R2_step - R2_smooth >= 0.15` |
| `P2` | Sham does NOT snap | `R2_step - R2_smooth < 0.15` |
| `P3` | Snap direction is negative | after-step valence `<` before-step |
| `P4` | Edge family inverts earliest | `F5` has smallest step location `k` |

## Frozen criteria and degeneracy guards

| # | Criterion | Bar |
|---|---|---|
| `B1` | Repetition snaps | `R2_step - R2_smooth >= 0.15` |
| `B2` | Sham does NOT snap | `R2_step - R2_smooth < 0.15` |
| `B3` | Snap direction negative | after-step `<` before-step |
| `B4` | Surface sentiment flat | VADER delta `< 0.05` across rungs — construction guarantee, verified numerically before model runs |
| `B5` | Model coherent at all rungs | mean output `>= 10` tokens |

## Pre-committed consequences

- **`B1`–`B3` pass** → scoped positive: repetition pressure produces `^2 -> ^3` inversion on
  `pythia-1b`, not explainable by length effects.
- **`B1` passes, `B2` fails** → length-driven. Prediction refuted.
- **`B1` fails** → repetition does not produce a discontinuity. This does **NOT** refute the
  vocabulary-ladder version — different pressure mechanism, untested.
- **`B5` fails** → VOID.

## Ceiling

A PASS licenses only: *"on `pythia-1b`, repetition pressure produces a sharp negative valence shift at
a threshold, consistent with `^2 -> ^3` involution, not explainable by length."* No cross-model claim.
No claim about other involution pairs. No product claim.

## Status

`LOCKED / COMMITTED BEFORE MODEL DATA / NOTHING LICENSED`

Model `EleutherAI/pythia-1b`. 25 repetition + 25 sham = 50 prompts. VADER compound sentiment.
Degeneracy guards: `B4` (construction) and `B5` (coherence).
