# Phase-0 record — analytic initialisation of the registered `^6` block

**Status:** DRAFT. **NOT SIGNED. NOT AUTHORISED. NOT RUN.**
**Proposal:** `records/encoder_capacity_001/ARCHITECTURE_CHANGE_SPEC_v0.2_ANALYTIC_DECOMPOSE_INIT.md`
**Executable form:** `cncm/analytic_decompose.py`
**Evidence base:** `records/encoder_capacity_001/UPDATE_TRAJECTORY_RESULT.md`,
`records/encoder_capacity_001/REACHABLE_SOLUTION_RESULT.md`
**Record:** `records/analytic_decompose_phase0_001/`

An owner-signed copy of this record is required before any job is registered, reserved or
launched. Writing this file does not authorise anything. The signature block at the end is
empty on purpose.

---

## 1. The question, stated once

The `^6` decompose block has 16,384 plastic parameters in three registered matrices and a
registered ceiling of 176 update steps. Measured on the recorded run:

| | value |
|---|---:|
| representation — real encoded slot, free readout, 5-fold CV | 63.65% |
| codebook — world symbols selectable | 65/65, min normalised margin 0.7573 |
| frozen readout as a constraint | none; 100.00% argmax agreement, max &#124;RᵀR⁻ᵀ − I&#124; = 2.798e-14 |
| registered `^6` class `x ↦ T·tanh(x)`, 5-fold CV | 63.83% |
| the trained learner, frozen readout, 160 updates | **1.24%** |
| training objective at the stopping point | not converged; gradient norm still rising, 1.378892× |

**The question:** does placing the plastic block at the closed-form solution, instead of
asking 160 stochastic updates to find it, produce a materially better machine?

This is one question with one falsifier. It is not a programme.

## 2. What is being held fixed

Nothing changes except the initial values of three matrices. Frozen and unchanged:

- the frozen encoder and its identity digest;
- the frozen 90-row readout, including the 65 world-alias rows;
- the registered parameter names `left.weight`, `merge.weight`, `right.weight`;
- the registered parameter shapes `(64,64)`, `(64,128)`, `(64,64)`;
- the registered plasticity scope, `operation:^6` only;
- the registered update ceiling, `max_updates <= 176`;
- the loss, the curriculum, the tokenizer, and the worker contract.

No new parameter, no new module, no new contract field, no change to `PARAMETERS`. The
construction is verified exact in `cncm/analytic_decompose.py`:
`parameters_for_map(T)` gives `left = I₆₄`, `right = 0`, `merge = [T | 0]`, and
`identity_residual` returns **0.0**.

**The solve needs no GPU.** It is ridge normal equations in 64 dimensions. The GPU is needed
only to run the arms.

## 3. The three arms

| arm | initialisation | updates | what it isolates |
|---|---|---|---|
| **A** | analytic `T` | **0** | whether the initialisation alone carries the solution |
| **B** | analytic `T` | 160 (registered) | whether registered training preserves, improves or destroys it |
| **C** | analytic `T` from **shuffled labels** | 0 | what a wrong solve achieves |

Arm C is load-bearing. With zero updates the solve *is* the model, so a good arm-A number is
uninterpretable without knowing what a wrong solve scores. A unit test already asserts the
wrong solve scores at most 4 of 64 on separable data.

### 3.1 Material discipline — a hard precondition

`T` is fitted on packets drawn from the registry, **disjoint from every evaluation set**. The
curriculum-order semantics of each arm are preserved as registered. Fitting `T` on the packets
an arm will be scored on would be leakage and would make the entire result meaningless. This is
checked programmatically before the run and its receipt is part of the evidence.

## 4. Frozen predictions

Written before launch, sealed with the record. These are predictions, not hopes; a prediction
recorded afterwards is not a prediction.

**P1 — arm A beats the recorded pre-teaching baseline on the final held-out set.**
The recorded pre-teaching score is **6.5201%** (raw 21/177). Arm A is predicted to exceed it.
*Confidence: moderate.* The mechanism is that one field moves to a strong solution; whether
that propagates through a conjunctive metric is exactly what is uncertain.

**P2 — arm A does not reach 63.83% on the whole answer.**
63.83% is focus-world alias decodability, one 64-way field. The whole-answer score is exact
match over all eleven fields and is conjunctive, so it cannot exceed the weakest field. Arm A
is predicted to land well below 63.83%. **If arm A scores near 63.83% on the whole answer,
that is a contradiction of this spec's model of the task and must be investigated, not
celebrated.**

**P3 — arm C stays at chance.** Scored at or below the majority-class baseline of the
evaluation set. If arm C scores materially above chance, arm A's result is void.

**P4 — arm B does not fall below arm A by more than one question.** The registered 160 updates
are predicted to be roughly neutral on an already-solved field, and negative on the fields the
solve does not touch.

**P5 — RESTORED. Arm A moves the emitted-alias distribution, and the recorded distribution is
the measurable target.**

> **Justification restated after the ninth self-correction.** P5 was first withdrawn when
> `measure_world_consistency.py` appeared to show that identification was already solved; that
> measurement was an artifact of counting a *supplied* world identifier. It was then justified by
> a "collapse" mechanism that has since been **refuted** — the block grew, it did not collapse,
> and a pure-Python rebuild of the forward pass does not reproduce the recorded distribution
> (`records/encoder_capacity_001/COLLAPSE_CLAIM_WITHDRAWN.md`).
>
> **What P5 now rests on is only the recorded fact**, which is not in dispute: at cursor 160 the
> model emits **9 of the 64 world aliases** across the 210 world-typed reference slots, **`W36`
> accounts for 44.3%** of them, and the focus alias is ranked 6th or worse in **157** of the 210.
> The cause of that concentration is **open**, and P5 does not depend on it.

The clean measurement (`measure_joint_binding.py`) looks only at slots whose alphabet is the 64
world aliases — the slots where the world is genuinely decided. Over 210 such slots, across the
70 `context` and 70 `definition` questions:

| cursor | focus alias ranked #1 | #2–#5 | **#6 or worse** | distinct aliases emitted | output entropy |
|---|---:|---:|---:|---:|---:|
| 0 (before teaching) | 6 | 22 | **182** | 26 of 64 | 4.164 bits |
| 160 (after teaching) | 10 | 43 | **157** | **9 of 64** | **2.516 bits** |

Teaching made the distribution **more concentrated and not more accurate**: distinct aliases
26 → 9, entropy 4.164 → 2.516 bits, commonest emission 15.2% → 44.3%, focus alias at rank 1
2.86% → 4.76%.

> **P5: arm A emits more than 9 distinct world aliases across the 210 world-typed reference
> slots, reduces the commonest single alias below 44.3%, and ranks the focus alias first in more
> than 10 of 210 slots.**

Each is a direct reading of the recorded quantity the analytic solve was fitted to raise, each
is falsifiable in one direction, and none depends on the sealed target or on any mechanism.

**What a pass would and would not mean.** It would mean the analytic solve moves the block's
readout behaviour off a concentrated distribution. It would **not** mean a collapse was repaired,
because no collapse was established. The mechanism stays open either way.

**What P5 does not cover.** `edge_account` and `parts` fail for a separate measured reason — a
conjunction over independent binary decisions (`DECISION_STRUCTURE_RESULT.md`, and Defect B in
`TWO_DEFECTS_RESULT.md`, which stands) — and a strong P5 would say nothing about them. A reader
who sees the alias distribution repaired must not read it as progress on the questions those
kinds contribute.

**A binding fix is NOT part of this.** Jointly deciding the world across the slots that must agree
was measured and changes nothing — 10 of 140 questions either way, because in the recorded run
the two slots are not disagreeing: they emit the same wrong constant. Referential consistency is
not the missing piece. See `joint_binding.txt`.

**P6 — the recurrence-aware fit costs arm A under 2 points, where the naive fit cost 19.15.**

> **P6 superseded.** It first predicted the recurrence would cost arm A between 10 and 30 points,
> measured on the **naive** fit. That fit had an aiming error and the error is now fixed; see
> `records/encoder_capacity_001/RECURRENCE_AWARE_FIT_RESULT.md`.

The naive solve fits `T` so that `T·tanh(encoded)` reads well, but the run never evaluates the
block on the encoded slot — it evaluates it on `incoming`, the encoded slot **plus a scaled carry
of the block's own previous output**, eight times. Scored out-of-fold at each registered depth:

| depth | 0 | 1 | 2 | 4 | 8 |
|---|---:|---:|---:|---:|---:|
| naive fit | 63.83% | **63.83%** | 44.86% | 43.62% | **44.68%** |

Depth 1 equals depth 0 exactly, because at depth 1 the state is still zero and `incoming` is the
encoded slot. **The loss happens on pass 2** and the later passes neither recover nor worsen it.

Re-fitting on the states the block is actually given recovers it, and converges:

| round | depth 0 | depth 8 | fitted on |
|---:|---:|---:|---|
| 0 | 63.83% | 44.68% | encoded slots |
| 1 | 62.77% | 61.88% | recurrence states |
| 2 | **62.94%** | **62.06%** | recurrence states |

`tools/prepare_analytic_arm.py` now performs this refinement by default (`refinements=2`;
`--refinements 0` reproduces the naive fit).

> **P6, revised: through the registered depth-8 recurrence, arm A reads the focus world above the
> recorded baseline, and the recurrence-aware fit leaves a residual cost of under 2 points.**
> Preparation values: **62.94% direct, 62.06% through the recurrence** — a residual cost of
> **0.88 points**, against 19.15 for the naive fit, a recovery of **+17.38 points**.

A run showing a recurrence cost above 5 points means the refinement is not transferring to the
real forward pass and the tool must be revisited before the result is interpreted.

**The honest prediction is therefore 62.06% through the registered recurrence** — 50.0× the
trained learner's 1.24%, 39.7× chance, and 13.46× the strongest null.

**And the figures are not penalty artifacts.** The tenth self-correction found that a fixed ridge
penalty can turn a conditioning difference into an apparent capability difference, so the arm's
numbers were swept (`records/encoder_capacity_001/ARM_PENALTY_VERIFIED.md`). Over three orders of
magnitude of penalty the refined fit's depth-8 accuracy spans **0.18 points** (61.70% to 61.88%) and
the direct figure spans 0.89. The same sweep moves the *trained block's* decodability by **29.08
points**. **Arm A's features are well-conditioned where the trained block's are not**, which is a
second independent reading of the same asymmetry. With one refinement round instead of two the
depth-8 figure is 61.88%, within 0.18 points.

**G6 is unaffected and passes on both readings**: 24 distinct aliases with the commonest at 7.3%
(direct) or 6.9% (through the recurrence), against the recorded baseline of 9 distinct with
`W36` at 44.3%.

## 5. Hard gates

Evaluated by a deterministic program reading raw results, frozen thresholds, controls and
hard-gate results. Not by prose. A hard gate that fails is a **FAILURE**, never "PASS with
caveats".

| gate | condition | on failure |
|---|---|---|
| **G1** | arm A > 6.5201% on the final held-out set | FAIL. The initialisation does not help. Report and stop. |
| **G2** | arm C ≤ the evaluation set's majority-class baseline | FAIL. The construction measures something other than what it claims; arm A is void. |
| **G3** | arm B ≥ arm A − 1 question | FAIL is a finding about the training, and is reported as one rather than tuned away. |
| **G4** | every arm's encoder, readout and scope digests equal the registered ones | FAIL. The run is void regardless of scores. |
| **G5** | no fitting material appears in any evaluation set | FAIL. Leakage; the run is void. |
| **G6** | arm A emits strictly more than 9 distinct world aliases across the 210 world-typed reference slots, and the commonest single alias is below 44.3% of emissions | FAIL. The analytic solve does not move the recorded concentration. Report and stop rather than tuning. |
| **G7** | arm C leaves the emitted-alias distribution at or below the recorded baseline (≤ 9 distinct, ≥ 44.3% commonest) | FAIL. If the wrong solve also moves the distribution, the movement is not evidence about the solve. |

G6 and G7 are direct readings of a recorded quantity, on the identification slots only, and
neither depends on the sealed target. Baseline for both: **9 distinct aliases of 64, commonest
alias `W36` at 44.3% of 210 slots, focus alias ranked #1 in 10 of 210**, measured at cursor 160.
The cause of the concentration is open; these gates test whether the solve moves it, not why it
is there.

**Aggregate reporting requirement.** Because teaching moves the exposed course and the
development panel in opposite directions on this architecture, every arm must report all three
panels separately — exposed course, development, retention — and must not report a single
aggregate. The recorded evidence for that requirement is
`records/encoder_capacity_001/PANEL_MISREAD_CORRECTION.md` and the error it corrects.

**Per-kind reporting requirement.** Every arm must report all eight question kinds separately
and must report, per kind, the number of answers naming the focus world. The recorded evidence
is `records/encoder_capacity_001/TWO_DEFECTS_RESULT.md`: three kinds have never been answered,
two of them while naming the focus world in 100% of their answers, and an aggregate would hide
both the zeroes and the reason.

No automatic retries. A failure is retained as a result. Negative results are not deleted.

## 6. Cost, reservations and precedent

- **Two $7 reservations** for a novel workload, per the precedent that the first typed-course
  attempt timed out at 1,800 s. Ledger revision 84 holds **$4,499.00 unreserved**.
- Six jobs if each arm runs on each of two seeds; three if one seed. **The arm and seed count
  is an owner decision and is left open here rather than assumed.**
- AWS GPU only. Not the local RTX 4070, not CPU. `GPU_REQUIRED` fails closed.
- Three arms at 160 updates on a 16,384-parameter module is a small job; the wall-clock cost is
  dominated by package install and encoder construction, not by training.

## 7. What each outcome would mean

| outcome | reading |
|---|---|
| G1 passes, G3 passes | The optimisation gap was the blocker for the world-naming slot. Worth carrying into the registered curriculum — and worth exactly that much, not more. |
| G1 passes, G3 fails | The initialisation helps and the registered training destroys it. A finding about the loss and the update ceiling. |
| G1 fails, G2 passes | The construction is exact and still does not help. The blocked kinds are then confirmed to be blocked by composition and binding, not by identification, and the next work is `TWO_DEFECTS_RESULT.md`, not this proposal. |
| **Any outcome on P5** | **P5 is withdrawn.** It was falsified before the run by $0 measurement. A run that changes `context`, `definition` or `edge_account` would not confirm it, because the mechanism it named is not the mechanism that operates. |
| G2 fails | The construction is not measuring what it claims. Stop and re-derive before spending again. |

**What this run can and cannot decide.** It decides whether a closed-form initialisation of the
world-naming slot buys anything. It **cannot** decide anything about `definition`,
`edge_account` or `parts`, because the defects there are referential consistency and
conjunction-over-decisions, and this change touches neither. A reader who sees a single high
number from this run must not read it as progress on the 210 questions the machine has never
answered.

## 8. What this record does NOT claim or authorise

- **It authorises nothing.** The signature block is empty.
- **It is not a preregistration for a claim about the cognitive machine.** It is a
  preregistration for one initialisation change and its three arms.
- **It does not fix the conjunctive-metric defect.** `UPDATE_TRAJECTORY_RESULT.md` records that
  the loss is additive over eleven fields while the score is conjunctive over the whole answer.
  Analytic initialisation removes one cause of failure and not that one.
- **It does not claim 63.83% is a whole-answer number.** It is not, and presenting it as one
  would be the single most misleading thing this record could do.
- **It does not touch `max_updates`.** The 176 ceiling is a field of the registered learner
  contract, and changing it is a contract-and-authority decision outside this proposal.
- **No GPU work may be launched on the strength of this document.** A signed copy is required.

---

## Signature block

    Owner:        ______________________________________
    Date (UTC):   ______________________________________
    Arms approved:            [ ] three (A, B, C)    [ ] other: ____________
    Seeds approved:           [ ] one               [ ] two
    Reservation amount:       $ ____________
    Phase-0 record digest:    ______________________________________

    Signed means: the owner has read sections 4, 5 and 8, accepts the frozen predictions and
    hard gates as written, and authorises registration and reservation of the jobs named
    above and no others.
