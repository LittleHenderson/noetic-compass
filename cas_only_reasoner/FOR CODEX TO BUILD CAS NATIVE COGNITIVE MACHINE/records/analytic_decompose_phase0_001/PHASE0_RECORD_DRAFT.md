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
| G1 passes, G3 passes | The optimisation gap was the blocker for this field. The architecture change is worth carrying into the registered curriculum. |
| G1 passes, G3 fails | The initialisation helps and the registered training destroys it. That is a finding about the loss and the update ceiling, and it is the more interesting of the two. |
| G1 fails, G2 passes | The construction is exact and still does not help. The conjunctive-metric defect is then the leading explanation, and the next work is the objective, not the initialisation. |
| G2 fails | The construction is not measuring what it claims. Stop and re-derive before spending again. |

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
