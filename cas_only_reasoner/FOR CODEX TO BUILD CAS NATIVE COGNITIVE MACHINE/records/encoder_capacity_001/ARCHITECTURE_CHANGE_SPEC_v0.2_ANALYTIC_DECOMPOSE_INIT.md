# Architecture change spec v0.2 — analytic initialisation of the registered `^6` block

**Status:** PROPOSED. Not implemented, not authorised, not run.
**Supersedes:** nothing. `ARCHITECTURE_CHANGE_SPEC_v0.1.md` in this record stands
**WITHDRAWN IN FULL** and is not revived by this document.
**Evidence base:** `REACHABLE_SOLUTION_RESULT.md` and `UPDATE_TRAJECTORY_RESULT.md` in this
record, both $0.00, both pure standard library, both grounded in already-recorded bytes.
**Requires:** an owner-signed phase-approval record before any GPU launch. Nothing in this
document authorises a run.

---

## 1. Why this spec exists, and why it is not v0.1

v0.1 was withdrawn because it proposed changing the encoder on the strength of a **synthetic
packet model** that turned out to be wrong, and because the parameters it wanted were
blocked by the registered learner contract. It argued from a model of the encoder rather than
from the encoder.

v0.2 argues from four measurements of the real system and proposes **no change to the
encoder, the codebook, the readout, the parameter list, the parameter shapes, the registered
scope, or the registered update ceiling.** It changes one thing: the values the plastic block
starts from.

The four measurements:

| what was measured | value | source |
|---|---|---|
| real encoded slot, free readout, 5-fold CV | 63.65% | `measure_real_slot_encoding.py`, reproduced in `measure_reachable_solution.py` |
| world symbols selectable from the frozen codebook | 65/65, min normalised margin 0.7573 | `measure_codebook_vertices.py` |
| frozen readout as a constraint | none — 100.00% argmax agreement, max &#124;RᵀR⁻ᵀ − I&#124; = 2.798e-14 | `measure_reachable_solution.py` |
| registered `^6` class `x ↦ T·tanh(x)`, 5-fold CV | 63.83% | `measure_reachable_solution.py` |
| the trained learner, frozen readout, 160 updates | 1.24% | `receipt_20260919_m` |
| training objective at the stopping point | not converged; gradient norm ratio 1.378892, Spearman +0.317690, last update the global minimum | `measure_update_trajectory.py` |

The gap between 63.83% (reachable) and 1.24% (reached) is an optimisation gap inside a
function class the registered module already contains.

---

## 2. The change

### 2.1 The construction

`cas_cjt.neural._DecomposeTransform` is the registered `^6` decompose module:

```python
self.left  = nn.Linear(64,  64, bias=False)   # left.weight   (64, 64)
self.right = nn.Linear(64,  64, bias=False)   # right.weight  (64, 64)
self.merge = nn.Linear(128, 64, bias=False)   # merge.weight  (64, 128)

def forward(self, value):
    parts = torch.cat((torch.tanh(self.left(value)),
                       torch.tanh(self.right(value))), dim=-1)
    return self.merge(parts)
```

Set

    left.weight  = I₆₄          # 64 x 64 identity
    right.weight = 0₆₄          # 64 x 64 zeros
    merge.weight = [ T | 0 ]    # 64 x 128; left half T, right half zeros

Then for every input `x`,

    ^6(x) = [T | 0] @ [ tanh(I x) ; tanh(0 x) ] = T @ tanh(x)

**exactly.** The right branch contributes `tanh(0) = 0` and contributes nothing to the
output, because the corresponding half of `merge.weight` is zero. This is an identity, not an
approximation.

### 2.2 Fitting `T`

Let `R` be the 64 × 64 matrix whose row `c` is the frozen readout row for world alias `Wc`,
and let `W` be the free-readout weight matrix (64 × 64, column `c` = the class-`c` weight
vector) obtained by ridge regression on the frozen features `φ = tanh(x)`.

    Tᵀ = W (Rᵀ)⁻¹

Then for every class `c`,

    r_c · (T φ) = (Tᵀ r_c) · φ = W_c · φ

so the frozen readout computes exactly the free-readout score vector. **Verified at 100.00%
argmax agreement on held-out rows.**

The invertibility of `Rᵀ` is not an assumption: it was measured, at max &#124;RᵀR⁻ᵀ − I&#124;
= 2.798e-14.

### 2.3 Where the solve runs

The solve is ridge normal equations in 64 dimensions — pure linear algebra, no torch, no
device, no gradient, no GPU. It runs in the worker before training and writes its result into
the three registered parameters. It adds no parameter, no module, no hook and no contract
field.

### 2.4 What the solve may and may not be fitted on

The initialisation material must be **disjoint from every evaluation set**, and the arm's
curriculum-order semantics must be preserved. Fitting `T` on the packets an arm will be
scored on would be leakage and would make the result meaningless. This is a hard
precondition, not a preference.

---

## 3. The run this spec proposes

Three arms, all with the registered frozen encoder and the registered frozen readout, all
inside the registered `^6` scope.

| arm | initialisation | updates | what it isolates |
|---|---|---|---|
| **A** | analytic (`left = I`, `right = 0`, `merge = [T \| 0]`) | **0** | whether the initialisation alone carries the solution |
| **B** | analytic | 160 (registered) | whether registered training preserves, improves or destroys it |
| **C** | analytic on **shuffled labels** | 0 | what a wrong solve achieves — the null for the construction itself |

Arm C is the control that matters most. Without it, a good number in arm A cannot be
distinguished from an initialisation that merely happens to sit in a helpful region.

Recorded baselines this would be compared against, all already on disk:

- pre-teaching score on the final held-out set: **6.5201%** (raw 21/177)
- after teaching, arm `ALT_COMPONENT_WHOLE`: **4/177**
- after teaching, arm `MIXED_SAME_ITEMS`: **1/177**
- the trained learner's frozen-readout focus decodability: **1.24%**

### 3.1 Hard gates, frozen before launch

1. **Arm A must beat the recorded pre-teaching score of 6.5201% on the final held-out set.**
   A hard gate that fails is a FAILURE, never "PASS with caveats".
2. **Arm C must stay at chance.** If the shuffled-label solve scores materially above chance,
   the construction is measuring something other than what it claims and arm A's result is
   void.
3. **Arm B must not fall below arm A.** If registered training destroys an analytic
   initialisation, that is a finding about the training, and it must be reported as one
   rather than tuned away.
4. **The predicted direction and magnitude must be written down and sealed before launch.**
   A prediction recorded afterwards is not a prediction.

### 3.2 Cost and authorisation

This is a claim-bearing neural run. It requires AWS GPU, not the local RTX 4070 and not CPU.
Budget two $7 reservations on the precedent that the first typed-course attempt timed out at
1,800 s. The ledger holds $4,499.00 unreserved at revision 84.

**No part of this run may be launched without an owner-signed phase-approval record, and
this document is not one.**

---

## 4. Honesty boundaries

- **63.83% is a single-field number.** It is focus-world alias decodability, one 64-way
  field. The learner's 1.24% and the arms' scores are whole-answer exact match over all
  eleven fields, which is conjunctive. **These are not like-for-like metrics.** If arm A
  scores far below 63.83% on the whole answer, that is expected and is not a refutation: a
  conjunctive metric over eleven fields cannot exceed the weakest field.
- **This spec does not claim the whole-answer score will rise to 63.83%.** It claims the
  initialisation places one field, the one the frozen codebook already resolves, at a
  solution the architecture can represent exactly — and that whether that propagates is an
  empirical question for the run.
- **The 63.83% was measured on the learner's own registry,** with only 24 of 64 worlds
  present. Held-out evaluation spanning all 64 worlds has not been run.
- **Nothing here shows stochastic gradient descent could find the solution.** The opposite:
  the companion record shows the objective had not converged at the ceiling.
- **The construction is exact but the class is linear in `φ`.** It cannot express anything a
  linear map on `tanh(x)` cannot. If the task needs more than that, this spec does not supply
  it.
- **A wrong `T` is not merely useless, it is a fixed wrong answer.** Arm C exists because the
  initialisation is not trained away by anything; 0 updates means the solve *is* the model.
- **The conjunctive-metric defect is not fixed by this spec.** `UPDATE_TRAJECTORY_RESULT.md`
  records that the loss is additive over eleven fields while the score is conjunctive over
  the whole answer, so improving a subset cannot move the score. Analytic initialisation
  removes one cause of failure; it does not remove that one. It is tracked separately and
  should not be conflated with this proposal.
