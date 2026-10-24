# CAS-LAB-011 — Operator-gated steering: fresh preregistration (2026-10-24)

Status: **preregistered before the run.** This is a **new hypothesis**, not a rerun of CAS-LAB-007. The earlier test
failed at 1.25×; that failure is kept and is not reinterpreted here. What changed is the hypothesis itself: from "a
structural label beats distance" to the narrower "**operator type** is the label that carries steering-relevant
information, and Noetic cell identity does not".

## 1. What the prior results say (all kept, unchanged)

- CAS-LAB-007 bar: best label-guided selector must reach 1.25× unguided. D3 (same-operator) reached **1.2283×** on
  A4-s1 — **failed**, 0.0217 short.
- Same run, A4-s1: D1 0.179647 (0.3933 of oracle), D2 same-cell 0.072766 (0.4050×), D3 0.220641 (0.4831×),
  D4 0.159371 (0.8871×), D5 random 0.018013 (0.1002×).
- Dose 0.20 safety replicated 3 of 3; the efficiency bar failed on A4-s3.

## 2. The hypothesis under test

**H:** a neighbourhood restricted to rows with the same operator (`×` vs `→`) captures a larger fraction of the
oracle gain than an unguided memory-distance neighbourhood, and this holds across seeds.

## 3. Design (frozen)

- Seeds: **A4-s1, A4-s2, A4-s3**, checkpoint step 1,000 each.
- Rows: `notation_new100` (600), split by source parity — discovery even, confirmation odd — as in every earlier run.
- Selectors: D1 (unguided) and D3 (same-operator only). D2 and D5 are reported for context but do not enter the
  decision.
- k = 10 for both. Same oracle directions, same scoring (teacher-forced NLL gain on confirmation rows).

## 4. Decision rule (frozen now)

**Primary:** D3/D1 ≥ **1.15** in **at least 2 of 3 seeds**.

**Secondary, reported not decisive:** whether D3 reaches 1.25 in any seed; the per-seed gain values; whether D3 > D1
in all three seeds.

Why 1.15 and not 1.25: the 1.2283 figure is a single-seed point estimate, and requiring a point estimate to replicate
exactly is the classic overfit trap. 1.15 is a *deliberately weaker* bar than the one that already failed, and that is
stated plainly so the record shows the weakening. If D3/D1 lands between 1.00 and 1.15, the hypothesis is **not
supported**; it is not "nearly supported".

## 5. What each outcome changes

- **Pass:** operator-gated neighbourhoods are a measured selection rule across three seeds, and the next question
  becomes whether they survive the reply guard at a safe dose.
- **Fail:** the 1.2283× was a single-seed fluctuation; the label carries no reliable information, and the steering
  route closes for good with that recorded.
- **Pass but only barely (1.15–1.20):** recorded as pass with the margin stated; no escalation to a control rule
  without the guard test.

## 6. Cost and host

AWS g5.xlarge, one instance, three seeds × (600 oracle backprops + 300 scoring rows). Expected under 15 minutes,
well inside the remaining cap (about **13.9 USD** of the 15.00 USD).

## 7. Honesty notes

- The weaker bar is declared before the data, not chosen after.
- No additional selectors may be added after seeing results.
- The failure of CAS-LAB-007 remains the record of the first attempt; this document does not delete it.
