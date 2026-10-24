# CAS Harness — steering, influence and control: consolidated inventory (2026-10-24)

Status: **inventory + mapping.** This gathers the scattered Harness work on steering/influence into one place, states
what each piece proves and does not prove, and says what it changes in the current cell-steering build.

## 1. Where the work actually lives (the disjointed set)

| Location | What it is | Status it carries |
|---|---|---|
| `docs/CAS_HARNESS_SPEC_SHEET.md` | the living master record: read / prove-cause / correct / record | `GREY` on CAS-specificity; **no `ACCEPT` anywhere**; surface-text steering "not yet closed" |
| `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/` | the Jacobian lens canary: exact-token lens, VJP/JVP conditioning, RFC3161-anchored receipts, 11 attempts | Attempt 11: **technical canary PASS**, Gate 1 `0.38` earned, `SHADOW / NONE / NOT_LICENSED` |
| same handoff, `GATE2_W0_FAIR_COMPARISON/` | injection detection from hidden states, 4 attempts, fair grouped CV, 4 surface controls | **4 FAILs at the pre-registered bar; family CLOSED** |
| same handoff, `04_PROTOCOL_AND_ANCHOR/ATTEMPT_08…/attempt8_conditioning_test.py` | the conditioning direction itself: `grad` of `logit(top1) − logit(top2)` w.r.t. a source-layer delta, verified by JVP | apparatus test, not an outcome test |
| same handoff, `ATTEMPT_09…/evidence/a9_vjp_conditioning.py`, `a9_metric_candidates.py` | VJP conditioning and candidate metrics, local JVP/VJP investigation | failed-closed attempts, kept as negatives |
| `cas-rr/cas_rr/` (`foundations.py`, `rpm.py`, `runtime.py`) | the Reasoning Processor: GoalFrame D/W/P states, prerequisite descent, `NEEDS_INFORMATION`, recipe with declared coefficients | implemented, bounded symbolic; **no neural coupling** |
| `noetic-compass-scaffold/…/cas-native/model/lacunarity_gate.py` | 40-slot `Var/Mean²` gate with a **learned** correction inside the model | implemented, unevaluated |

## 2. What the Harness actually established about steering

**Established (apparatus):**
- A conditioning direction can be computed as the gradient of a chosen logit functional with respect to a source-layer
  activation, applied at a named position and layer, and the analytic derivative check passes to `5e-4` relative error
  (Attempt 11: `1248/1248` autograd contract, producer + independent torch-free receiver).
- The whole run is anchored and re-derivable from raw artifacts (`RFC3161` verified).

**Not established (effect):**
- That such a direction *improves* task performance. Attempt 11 is a **technical canary**: it proves the machinery
  computes and records correctly, not that the perturbation helps. Its own status is `SHADOW / NONE / NOT_LICENSED`.
- That hidden-state structure beats surface structure: the W0 family tested exactly that and **failed four times** —
  real signal above chance (`0.6875`–`0.7375` balanced accuracy, permutation `p = 0.0005`) but not beyond the layer-0
  token-identity control (margins `+0.0375`, `+0.1125`, `+0.025`; only one CI excluded zero, and it did not replicate).
- That weight-level repair works: the repair chain the spec sheet records is **one axis, a numeric array, no model
  loaded, no efficacy claim**.

So: the Harness gives a **method** for bounded influence and a **discipline** for proving cause, not a demonstrated
repair.

## 3. What it changes in the current build

My `cell_steer.py` (previous round) used a mean-difference direction between rows with and without a cell. The Harness
work says three things about that:

1. **Replace the direction estimator with the gradient one.** The Harness conditions on a *functional* (a logit gap),
   not on a class mean. A gradient direction is the first-order optimal perturbation for a stated objective and can be
   checked analytically.
2. **Keep the matched random control and the grouped split.** Those are the Harness's own non-negotiables, and the W0
   failures show why: without the layer-0 token-identity control, a "signal" can be surface reading.
3. **Expect selectivity, not a general effect.** The W0 family's honest failure and my own 8-win/14-loss result point
   the same way: a direction that moves one functional will not improve everything, and the claim must be scoped to
   the cells and functional where it was measured.

## 4. Next build (adopting the Harness method)

`cell_steer_grad.py`, for the CTT model:

- **Functional:** the margin between the gold next token and its strongest competitor, at a named decoder position;
  alternatively the row's teacher-forced NLL (a scalar with a clean gradient).
- **Direction:** `−∇_mem (NLL)` at the last source position, computed by backprop through the decoder. This is an
  oracle direction (it uses the gold target), so it is an **upper bound**, not a deployable controller.
- **Deployable comparison:** the cell mean-difference direction from the previous round.
- **Control:** matched random direction, same norm, deterministic seed.
- **Check:** finite-difference the functional along the direction to confirm the sign matches the gradient (the
  Harness's JVP check, at our scale).
- **Report:** per cell, the oracle gain, the cell-direction gain, and the random gain, with a statement of how much of
  the oracle gain the deployable direction captures.

The point of the comparison is honest: it tells us whether a cell-level direction is a useful approximation of the
gradient direction, or whether cell steering is a placebo with a lucky tail.

## 5. Claim status

| Statement | Status |
|---|---|
| The Harness computes and verifies conditioning directions | `REAL` (Attempt 11, apparatus only) |
| The Harness demonstrates a steering effect on task performance | `NOT ESTABLISHED` |
| Hidden-state structure beats surface controls at the W0 bar | `FAILED` (4 attempts) |
| Our mean-difference cell direction helps 8 of 30 cells, hurts 14 | `REAL`, small samples, local |
| Gradient-conditioned steering on CTT | `NOT RUN` — next build |

## 6. First run of the Harness-style conditioning on CTT (2026-10-24)

`cell_steer_grad.py`, A4-s1 step 1,000, 30 cells, confirmation half only, intervention at the last source position,
matched norm. The analytic sign check passed (NLL 0.203282 → 0.203280 along the step).

| Direction | Mean change in held-out NLL (positive = improvement) | Best cell | Worst cell |
|---|---:|---|---|
| **Oracle gradient** (per row, uses the gold answer) | **+0.2200** | `^1^O` +0.3698 | `^2^E` +0.0987 |
| Cell mean-difference (deployable) | **−0.0008** | `^3^P` +0.0080 | `^4^C` −0.0151 |
| Matched random | **−0.0012** | `^5^C` +0.0106 | `^4^C` −0.0216 |

**The gap is the story.** A per-row gradient direction lowers held-out error on every one of the 30 cells, by
+0.0987 to +0.3698. The deployable cell direction captures essentially **none** of that at the same position — its
mean change is −0.0008, indistinguishable from the random control.

**Position caveat, stated plainly.** The previous round's `cell_steer.py` applied the cell direction at **every**
source position and reported gains up to 0.38 on 8 cells. This run applies it at the **last** position only. The
difference between those two runs is therefore the *position* of the intervention, not the direction. That earlier
result is not withdrawn, but it must be re-read as an all-position shift, and it has not yet been compared to the
oracle at the same setting.

**What this changes.** The Harness conditioning method works as an apparatus on our model: the gradient direction does
what first-order theory says it should. But a cell-level class direction is not a cheap substitute for it. Any claim
that "we can steer cell ^n" now has a concrete bar to clear: it must capture a stated fraction of the oracle gain at
the same position, not merely beat random by a hair.

Artifacts: `cs_aws/steer_grad_results.jsonl` (30 cells), `lacunarity_e1/cell_steer_grad.py`.
