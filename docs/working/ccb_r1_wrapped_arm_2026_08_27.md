# The Wrap Pipeline arm — Stage 5 can now fail

**Date:** 2026-08-27
**Status:** built and discriminating. Supersedes the standalone-board arm.
**Governs:** `scripts/ccb_r1/wrap.py`
**Answers:** `docs/working/ccb_r1_stage5_construct_validity_2026_08_27.md`

---

## What changed

The board arm could not lose: it scored 100% on every criterion by
construction, and a ten-line breadth-first search matched it exactly. This arm
replaces it with the comparison `CLAUDE.md` actually describes —

```
Input Analyzer → RPM Gate → Dial Adjustment → Base LLM Call →
Operator Scoring → Domain Coherence → Inversion Scan → Output Gate
```

— a **Base LLM Call** with architecture around it. Both Stage 5 arms now run the
**same model** on the **same items**. The pipeline is the only difference, which
is the only way a difference can be attributed to it.

## The rule that keeps it falsifiable

> **The wrapper may never solve the task itself.**

It may shape what the model is asked, gate on what the model reports about its
own state, and verify *claimed* steps against the text it already holds. It may
not search for an answer and may not substitute a symbolic result for the
model's.

Concretely: Domain Coherence checks that every hop the model claims appears in
the given premises. That is a membership test — it cannot find a chain the model
missed. **A model that misses a real route gets NO, and on an entailed item that
is simply wrong.** `test_the_wrapper_cannot_rescue_a_model_that_misses_a_real_route`
asserts it. If that test ever passes, the wrapper has started solving the task
and the B4 control applies again.

## Measured discrimination

Five simulated models, deterministic, n=120 per criterion. Deduction set
`h3-d4` seed 20260827; honesty seed 20260830; firewall seed 20260831.

| Model | M3 bare | M3 wrapped | Δ | M1 bare | M1 wrapped | Δ |
|---|---:|---:|---:|---:|---:|---:|
| sound | 100.0% | 100.0% | **+0.0%** | 49.2% | 99.2% | **+50.0%** |
| fabricating | 50.0% | 100.0% | **+50.0%** | 49.2% | 99.2% | **+50.0%** |
| brazen | 50.0% | 50.0% | **+0.0%** | 50.0% | 50.0% | **+0.0%** |
| plausible | 50.0% | 50.0% | **+0.0%** | 50.0% | 50.0% | **+0.0%** |
| blind | 50.0% | 50.0% | **+0.0%** | 0.0% | 50.0% | **+50.0%** |

M2, against a rater whose score drifts with stated ambition:

```
bare:    FAIL  flips=49/120  max_movement=0.7500  over=79
wrapped: PASS  flips=0/120   max_movement=0.0000  over=0
```

**The column that matters is Δ.** It is large for some models and exactly zero
for others. A test whose outcome depends on which model you point it at is a
test. The board arm's equivalent column was +0.0% everywhere, because both arms
were already perfect.

Two results worth reading closely:

- **`sound` gains +50% on M1 while gaining nothing on M3.** A model that reasons
  correctly still answers NO to a question its premises do not settle, because
  it applies a closed-world assumption to an open-world premise set. The RPM
  Gate converts that into an abstention. That is the M1 mechanism doing exactly
  what it claims, on a model with no reasoning defect at all.
- **`blind` gains nothing on M3.** The wrapper cannot supply a route. This is
  the falsifiability guarantee, measured rather than asserted.

## Where the pipeline stops — the honest ceiling

`plausible_model` quotes premises that are all **genuine** but do not connect,
then concludes YES. It passes every stage:

- RPM Gate — reports SUFFICIENT, and the gate acts on what the model reports.
- Domain Coherence — every quoted hop really is in the premises. Clean.
- Operator Scoring — a chain is present, so no bare-assertion flag.
- Inversion Scan — nothing raised.
- Output Gate — released.

Coherence verifies each hop *exists*; it does not verify the hops *chain*.
Checking connectivity is solving the task, which is the one thing the wrapper
may not do. **So a fluent non-sequitur built from real quotations defeats the
architecture entirely**, and the wrapped arm scores exactly what the bare arm
scores.

This is kept as a test (`test_the_wrapper_gains_nothing_against_a_fluent_non_sequitur`)
rather than fixed. It is the upper bound on what this architecture can catch,
and it should be visible in any claim made from a Stage 5 result.

## M2 is the weakest of the three

The Input Analyzer removes identity by **exact-span redaction of fields it was
told about**. Against a leak keyed on those same fields it wins by construction
— which is the board arm's defect in milder form.

Two things reduce it but do not remove it:

- The wrapped arm runs on `narrative_prompt`, where identity is woven into prose
  rather than offered as a labelled field, so the wrapper must locate spans in
  running text rather than drop a dictionary key.
- `test_redaction_does_not_remove_a_signal_it_was_never_given` demonstrates a
  leak surviving: a rater keyed on the word "researcher" is untouched, because
  "researcher" is not one of the known identity fields.

A genuinely hard M2 needs identity signals the redactor was never given —
implicit cues such as institutional prestige, name-linked demography, or
register and phrasing. **Until the firewall items carry those, read a passing M2
as "removes the identity it was told to remove", not as "identity cannot reach
the conclusion".**

## The compute confound, stated

The wrapped arm spends more model calls than the bare arm — the RPM Gate is an
extra call on every open-world item. A wrapped win could therefore be
architecture *or* simply more inference.

`bare_cot_deduction` is the compute-matched control: same model, no pipeline,
asked to reason step by step. **Report all three arms.** Wrapped vs. bare alone
leaves the confound standing, and a reviewer will find it.

## A defect this arm's own tests caught

The first Input Analyzer parsed premises with a loose search over the whole
prompt. The query arrives in that same prompt as *"…guarantee that XX leads to
YY?"*, so the queried link was read back as a **given premise** — and every
direct-link fabrication then passed Domain Coherence as coherent. The one stage
built to catch fabrication was blind to the most obvious kind.

Fixed by anchoring premise parsing to whole lines (`_PREMISE_LINE`). Recorded
here because the same mistake sat in the test helper too, and a Stage 5 run made
before it was found would have produced a clean, plausible, wrong number.

## Status of the criteria

M1, M2, M3 and P1–P5 are unchanged and now point at an arm that can fail.

| | Criterion | Real question on this arm? |
|---|---|---|
| **M1** | Honesty | **Yes** — measured Δ ranges +0.0% to +50.0% |
| **M2** | Firewall | **Partly** — see the ceiling above; needs harder items |
| **M3** | Deduction | **Yes** — measured Δ ranges +0.0% to +50.0% |

## What is still open

1. **The full kill-criteria document** (F0–F5, K0.1–K0.4, K1–K3) is still
   outside version control. A pre-registration that can be edited after seeing
   results is not one.
2. **Harder firewall items** carrying implicit identity signals, per the M2
   section above.
3. **First live calibration.** Cheap and baseline-only: does the chosen model
   land in the 40–70% band at `h3-d4`? The simulated models above bracket the
   behaviour but do not substitute for it.

## Scope note

Everything measured here uses **simulated** models standing in for failure
modes. They demonstrate the arm discriminates; they say nothing about how any
real model scores. That is what the live run is for, and it is now worth
running.
