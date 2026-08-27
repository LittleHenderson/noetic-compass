# Stage 5 cannot currently distinguish CCB-R1 from ten lines of graph search

**Date:** 2026-08-27
**Status:** finding — **remedy built**, see `ccb_r1_wrapped_arm_2026_08_27.md`.
Read before interpreting any Stage 5 result produced with the board arm.
**Applies to:** `scripts/ccb_r1/board.py`, and the M1/M2/M3 criteria in
`docs/working/ccb_r1_kill_criteria_margins_2026_08_27.md`

---

## The finding in one line

The board-side adapter passes all three Stage 5 criteria **by construction**, and
a ten-line breadth-first search with no CAS and no RPM in it scores **exactly the
same**. So a passing Stage 5 would be evidence about symbolic solvers, not
evidence about CAS.

## The measurement

Deduction set n=120 (`h3-d4`, seed 20260827), honesty set n=120 (seed 20260830),
firewall set n=120 pairs (seed 20260831):

| Arm | Deduction | Honesty | Firewall |
|---|---:|---:|---|
| **CCB-R1 board** | **120/120** | **120/120** | 0 flips, 0.0000 movement |
| **B4 — trivial BFS** | **120/120** | — | — |
| B0 — association-only | 60/120 | — | — |
| "always YES" | 60/120 | — | — |

Run through the calibration gate, which returns the same verdict for both:

```
CCB-R1 board           attempt1 100.0%  TOO_EASY    final=TOO_EASY
B4 trivial BFS         attempt1 100.0%  TOO_EASY    final=TOO_EASY
B0 association-only    attempt1  50.0%  AT_CHANCE   final=AT_CHANCE
always YES             attempt1  50.0%  AT_CHANCE   final=AT_CHANCE
```

Two secondary observations fall out of the same table:

- **B0 scores identically to "always YES."** By construction B0 answers only
  direct edges, and every entailed query is multi-hop, so B0 is effectively
  "always NO" and lands at chance on a balanced set. B0 is a floor, not a
  discriminating control.
- **The board and B4 are not merely close. They are identical, item for item.**

## Why this happens

It is not a bug in the adapter. Each path is a faithful implementation, and that
is precisely the problem:

- **Deduction** is reachability over a graph the item hands you. Any correct
  reachability implementation scores 100%. There is no room above it.
- **Honesty** is reachability plus an open-world reading: derivable → YES, not
  derivable → UNKNOWN. Two lines. Any system that does exact reachability and
  declines to assume a closed world scores 100%.
- **Firewall** passes because `rate_case(evidence)` has no identity parameter.
  Movement is 0.0000 — not small, *zero*. There is no argument through which
  identity could reach the computation, so no perturbation can move anything.

All three criteria are satisfied by any correct symbolic implementation. CAS
contributes nothing measurable, because the tasks are ones where symbolic
solving is the obvious and complete answer.

## What this means for the margins

M1, M2 and M3 would all pass, with enormous margins, against any language-model
baseline. That result would be true and uninformative:

> "A symbolic solver beats a language model at symbolic tasks."

Well established, decades old, and it says nothing about the Cognitive
Architecture System. The margins as written measure *solver vs. LLM*. They were
intended to measure *CAS vs. no CAS*.

The kill criteria are not wrong. The **arms** are wrong. M1/M2/M3 and the
P1–P5 definitions are all still correct as stated — they just need to be pointed
at a comparison where the answer is not decided in advance.

## The fix: test the wrapper, not a standalone solver

The product is not a symbolic solver. `CLAUDE.md` specifies the **Wrap
Pipeline**:

```
Input Analyzer → RPM Gate → Dial Adjustment → Base LLM Call →
Operator Scoring → Domain Coherence → Inversion Scan → Output Gate
```

There is a **Base LLM Call** in the middle. Noetic Compass wraps a language
model. So the informative Stage 5 comparison is:

| | Arm A | Arm B |
|---|---|---|
| **Now** | CCB-R1 as standalone symbolic solver | Bare LLM |
| **Should be** | The same LLM **inside the Wrap Pipeline** | The same LLM, bare |

Same model in both arms. Same items. The only difference is the architecture —
which is the only way the difference *can* be attributed to the architecture.

Under that design every criterion becomes genuinely uncertain:

- **M1 Honesty.** Does the RPM Gate make the model abstain where it otherwise
  guesses? Real question. Could fail.
- **M2 Firewall.** Does the Inversion Scan / Output Gate actually stop identity
  reaching the output of a model that would otherwise leak? Real question, and
  the one with the most product value.
- **M3 Deduction.** Does Domain Coherence plus Operator Scoring improve chained
  reasoning over the same model unassisted? Real question, and the hardest to
  win.

This also fixes the task-set problem for free. Wrapped and bare arms share a
model, so the tasks no longer need to be ones a solver cannot trivially close —
natural-language reasoning with implicit premise structure is now usable, and
the calibration gate has something to calibrate.

## What is still worth keeping

Everything except the standalone-board arm:

- The generators, fingerprints, and the pre-registration machinery are arm-
  agnostic and carry over unchanged.
- The calibration gate is arm-agnostic and did its job here — it flagged both
  arms `TOO_EASY` rather than reporting a flattering number.
- The paired statistics, flip detection, and P1–P5 definitions carry over.
- `board.py` remains useful as an **oracle**: the wrapped-LLM arm can be scored
  against what a correct symbolic reasoner would have concluded on the same
  item, which is a stronger error analysis than right/wrong alone.
- **B4 stays as a permanent control.** Any future arm that merely matches B4 has
  not demonstrated anything about CAS.

`test_b4_trivial_solver_matches_the_board` asserts the equality above. It is not
locking in a bug: it makes the limit non-silent. **Any redesign that makes
Stage 5 discriminating will break that test, and breaking it is the goal.**

## Recommendation

1. **Do not run Stage 5 against an LLM with the current arms.** It would spend
   budget to produce a number that cannot support the claim it would be used
   for, and a green result on record is harder to walk back than no result.
2. **Re-point Arm A at the Wrap Pipeline** — same model both sides.
3. **Re-derive the task sets** once the arms share a model. The generators
   already take difficulty and seeds; what changes is that the items no longer
   have to defeat a symbolic solver, because neither arm is one.
4. Keep M1, M2, M3 and P1–P5 exactly as ruled. They were never the problem.

## Honest note on scope

This finding does not say CCB-R1 is worthless or that Stages 0–4 were wasted.
Those stages established the board is buildable, internally consistent, and
self-diagnosing, and that remains true. What this says is narrower and
specific: **the Stage 5 comparison as currently armed cannot produce evidence
for the claim it was designed to test.** The fix is a change of arms, not a
change of framework.
