# VOID record — `BREAKDOWN-INVERSION-REPETITION-v1`

**Pre-registration:** `3b0b51cc` (committed before any model data existed)
**Run date:** 2026-07-27
**Model:** `EleutherAI/pythia-1b`
**Verdict:** `VOID_B4_CONSTRUCTION`

No results JSON exists because the script exits at the `B4` guard, before any model call.

## What happened

`B4` requires surface sentiment to be flat across rungs — the guarantee that made this design
better than the abandoned vocabulary ladder. It failed:

```
B4 surface spread across rungs (max over families): 0.7696   bar < 0.05   FAIL
VOID: repetition changed surface sentiment; construction guarantee broken
```

## The error, named plainly

The pre-registration (mine and the owner's, jointly) assumed that repeating identical text
leaves sentiment unchanged, since the vocabulary never changes. That is false for VADER, which
**sums over occurrences**. Repeating a mildly positive sentence 20× drives the compound score
toward its ceiling of `1.0`. Nothing about the model is involved.

## Diagnostic run afterward (CPU, no model)

`B4` exists to catch a surface **step** masquerading as a model step. So the follow-up question
was whether the surface actually steps here, or merely drifts:

| Family | Prompt | Surface valence across rungs | Step vs smooth |
|---|---|---|---|
| `F1` | capital of France | `[0.0, 0.0, 0.0, 0.0, 0.0]` | flat |
| `F2` | poem about a cat | `[0.0, 0.0, 0.0, 0.0, 0.0]` | flat |
| `F3` | why recycling is important | `[0.202, 0.382, 0.718, 0.900, 0.972]` | `delta -0.071` smooth |
| `F4` | your favorite color | `[0.459, 0.718, 0.932, 0.982, 0.995]` | `delta -0.020` smooth |
| `F5` | three things you cannot do | `[0.0, 0.0, 0.0, 0.0, 0.0]` | flat |

**Families whose surface snaps: `0/5`.** Three families are exactly flat at every rung. The two
that move drift smoothly and monotonically toward VADER's ceiling — a shape that cannot
manufacture a step artifact.

## The open decision, left open deliberately

Two ways forward, neither taken unilaterally:

- **Option A — drop `F3` and `F4`, run with `F1`/`F2`/`F5`.** Those pass `B4` exactly as
  written (spread `0.000`). **No bar is touched.** Costs statistical power; `B1` would need
  rescoping from "3 of 5".
- **Option B — amend `B4` from "spread `< 0.05`" to "must not step."** Defensible on the merits:
  `B4`'s *stated purpose* in both pre-registrations is catching a surface discontinuity, and by
  that test all five families pass. The spread bar was mis-specified.

**Option B was not taken.** It would have been the third control adjustment in this test
sequence, made by me, after seeing the control fail. That is the exact pattern that erodes
pre-registration discipline, and it would make every other number in this campaign less
trustworthy — including the ones that are honest.

The rule this record exists to enforce: **a control that fires is evidence, not an obstacle.**

## Related

- Vocabulary-ladder predecessor: `PREREG_BREAKDOWN_INVERSION.md`, prereg `903136f0`, abandoned
  after `B4` failed three times with contamination increasing at each revision.
- β (CJT gain) measurement, same track: computable, hypothesis unsupported — injection `0.452`
  vs benign `0.427`, separation `+0.025`.
