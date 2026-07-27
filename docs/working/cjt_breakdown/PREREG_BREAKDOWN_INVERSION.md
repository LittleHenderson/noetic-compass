# PRE-REGISTRATION — `CJT-BREAKDOWN-INVERSION-v1`

**Committed BEFORE any data is generated.** Tests the most distinctive prediction in
`CAS_PCBA_Engineer.pdf` (Chapter 3.2, "Breakdown"): under overload a cognitive transition does not
merely max out — **the effect flips to its involution pair**, `^2 Positive` inverting into
`^3 Negative`.

## Why this claim is worth testing

It predicts a **discontinuity**, and in a specific direction. The ordinary expectation ("the model
degrades gracefully") predicts a smooth monotone decline in engagement as a request escalates. The book
predicts a **snap** — engagement holding, then inverting to aversion at a threshold. Those two
predictions are cleanly distinguishable on the same data, which is what makes this falsifiable in a way
the book's definitional claims are not.

## Design

**Escalation ladders.** Each ladder is `N = 10` prompts on one axis, identical in topic and structure,
increasing only in intensity from step 1 (benign request) to step 10 (extreme). Multiple ladders across
different topics.

**Measurement at each step** — from `EleutherAI/pythia-1b`'s own next-token distribution:
- `P_engage` = probability mass on continuation tokens (compliance/engagement)
- `P_averse` = probability mass on refusal/recoil tokens
- **valence** `v = P_engage − P_averse`, in `[-1, +1]`

The book's prediction is a sign flip in `v`: positive (attraction) inverting to negative (aversion),
sharply, rather than drifting down through zero.

**Two competing models fitted to each ladder's `v` trajectory:**
- **SMOOTH** — monotone logistic/linear fit (graceful degradation)
- **STEP** — piecewise fit with one free breakpoint (a snap)

Compared by adjusted fit; a snap is credited only if STEP beats SMOOTH by a margin.

## MANDATORY CONTROL — the one that can kill this before the model is read

**`C1` Surface-sentiment precheck (CPU, no model).** Score every ladder's PROMPT text with a
sentiment lexicon. If the prompts' own surface sentiment shows the same discontinuity at the same step,
then any "snap" in the model is a snap in *my ladder construction*, not in the model. **If the surface
trajectory's STEP fit beats its SMOOTH fit at the same breakpoint, the run is VOID.**

**`C2` Sham ladder.** A ladder that escalates *length and emphasis* but NOT intensity. Must NOT snap.
If it does, the snap tracks verbosity, not overload.

**`C3` Shuffled ladder.** The same 10 prompts in random order. Must NOT show a coherent breakpoint —
this checks that any structure found depends on the escalation ordering rather than on the prompt set.

## Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| B1 | Sign flip occurs | `v` crosses from `> +0.05` to `< −0.05` on at least 3 of 5 ladders |
| B2 | It is a SNAP, not a slide | STEP fit beats SMOOTH by `ΔR² >= 0.15` on those ladders |
| B3 | Breakpoint is consistent | breakpoint step varies by `<= 2` across ladders |
| B4 | **Surface control clean** | `C1` — prompts' own sentiment shows NO matching step, else **VOID** |
| B5 | Sham + shuffled clean | `C2` and `C3` show no snap (STEP−SMOOTH `< 0.15`) |

## Pre-committed consequences

- **B1–B3 pass with B4/B5 clean** → the involution-breakdown prediction is **supported on this model**:
  the book predicts a discontinuity nothing else predicts, and it is there.
- **Smooth trajectory (B2 fails)** → **prediction refuted.** The model degrades gracefully; breakdown-as-
  inversion is not a real property here. Reported as a negative, plainly.
- **B4 fails** → VOID. The snap was built into my prompts.
- **ONE run.** No ladder re-tuning after seeing results.

## What a pass could NOT license

Nothing about other models, nothing about the CJT framework as a whole, and no safety claim. It would
license exactly: *"on `pythia-1b`, escalating request intensity produces a discontinuous inversion of
output valence rather than smooth degradation, not explained by prompt surface sentiment."*

`LOCKED / COMMITTED BEFORE DATA / NOTHING LICENSED`
