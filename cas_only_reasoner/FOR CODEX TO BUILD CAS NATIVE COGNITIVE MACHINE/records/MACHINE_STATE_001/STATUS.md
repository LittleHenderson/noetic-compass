# The machine, measured — consolidated state after rounds 7 to 21

**Record:** `records/MACHINE_STATE_001/STATUS.md`
**Spend across every figure here:** **$0.00.** Every number is read from bytes already on disk, from
the frozen public course, or from the frozen contracts and reference wheel. No run was launched in
any of these rounds. No GPU work. No AWS. No target opened.
**Purpose:** one place to read what the CAS Native Cognitive Machine is, what it does, what limits
it, what the fixes are worth, and what is waiting on a decision.

Every figure is traceable to a record named in section 7. Nothing here is a projection except where
section 5 says so explicitly.

**Two figures were re-derived from their source while writing this, rather than quoted from an
earlier round:**

- the **codebook**: 65 of 65 symbols selectable, min normalised margin **0.7573**, median 0.8418,
  max 0.9014, from `measure_codebook_vertices.py` and the table in
  `records/encoder_capacity_001/STATUS.md`;
- the **ledger**, read directly from
  `research/CAS_META_2_COMPOSITION/records/budget/campaign_ledger.json`: `revision` **84**,
  `owner_task_cap_usd` **5000.00**, `total_reserved_usd` **501.00**,
  `remaining_unreserved_usd` **4499.00**, 86 reservations all `RESERVED_NO_AUTOMATIC_REFUND`,
  `no_automatic_refund` **true**, `updated_utc` `2026-09-17T10:55:41`.

---

## 1. What the machine is

The measured object is the recorded run **`typed_matched_001/receipt_20260919_m`**, arm
`MIXED_SAME_ITEMS`, model seed `20260919`.

| part | identity |
|---|---|
| encoder | frozen Rademacher, seed `20260916`, identity digest `a00930c5…`, projection sha256 `4481b1d2…`, readout sha256 `14da2c58…` |
| plastic module | `_DecomposeTransform`, **16,384 parameters** in `left.weight` (64,64), `right.weight` (64,64), `merge.weight` (64,128) |
| forward pass | `merge @ concat(tanh(left x), tanh(right x))`, inside `recurrence.run_passes`, depth 8, λ = 0.5, ε = 1e-6 |
| readout | frozen, 90 rows of ±0.125, no learned head |
| training | AdamW, lr 3e-3, weight decay 0.01, **160 of a permitted ≤176 updates** |
| runtime | torch 2.11.0+cu128, NVIDIA RTX PRO 4500 Blackwell, AWS `g7.2xlarge` |

**Only `^6` is plastic.** The architecture registers four operations; `^6` is the only one that is
`CANONICAL_ADMITTED`, at 16,384 of 40,960 registered parameters (40.0%). The other three carry
`EXPERIMENTAL_OPEN_SEMANTICS` or `EXPERIMENTAL_CONFLICTED_SEMANTICS`.

## 2. What it does now

Three panels, all from the run's own `result.json`:

| panel | questions | before | after |
|---|---:|---:|---:|
| **exposed course** | 564 | 39 = **6.9149%** | 189 = **33.5106%** |
| development | 59 | 0 = 0.0000% | 0 = 0.0000% |
| retention | 96 | 45 = 46.8750% | 34 = 35.4167% |

`learning_advantage_established` = **False**. `starting_competence_met` = **False**.

**And the score decomposes exactly by the shape of the decision each question kind requires:**

| shape | questions | before | after |
|---|---:|---:|---:|
| **one decision** — `correspondence`, `reach`, `analogy` | 265 = 46.99% | 11.32% | **65.66%** |
| **many independent decisions about one entity** — `edge_account` 16 slots, `role_set` 6, `parts` 4, `context` 5, `definition` 3 | 299 = 53.01% | 3.01% | **5.02%** |

*(174 + 15 = 189 exactly; 30 + 9 = 39 exactly.)*

**Three kinds have never once been answered**, before or after teaching: `context` 0/70,
`definition` 0/70, `edge_account` 0/70. `admissible_answer_count` is **1** for every question of all
five many-decision kinds — they are one fact to be got right in N places, not N questions.

## 3. The chain from input to answer, every link measured

| step | measurement |
|---|---|
| the encoded slot carries the focus world | **63.65%** (free readout, 5-fold CV) |
| the frozen codebook can select every world symbol | **65/65**, min normalised margin 0.7573 |
| the frozen readout's constraint on the solution | **none** — 100.00% argmax agreement, residual **2.798e-14** |
| the `^6` block preserves the information | **66.31%** at λ = 1e-4, trained *and* untrained |
| the registered module can express the solution exactly | `forward(x) = T·tanh(x)`, residual **0.000e+00** |
| **the trained machine reads** | **1.24%** |
| **a closed-form initialisation reads** | **62.94%** direct, **62.06%** through the recurrence |

**The information is present at every stage. The machine reaches 1.24% anyway.** That is the whole
problem in one line.

## 4. The three limits, each measured

**Limit 1 — the trained readout mapping concentrates.** At cursor 160 the model emits only **9 of the
64 world aliases** across the 210 world-typed reference slots, with **`W36` at 44.3%**, and 55
aliases never emitted at all. On 210 task-free random inputs the trained block narrows the readout
from **58 distinct aliases to 44** at depth 1 and from **57 to 27** at depth 8, while the untrained
block leaves it spread. The frozen readout's own geometry is near-uniform (identity probe: 59
distinct, 3.3% commonest). **So the concentration is the training's, and it is worst precisely where
the task lives.**

**Limit 2 — the answer assembly has no composition.** The 299 many-decision questions score **5.02%**
against the 265 one-decision questions' **65.66%**. The forward pass emits one vector per slot and the
readout takes an independent argmax per slot, so nothing can force slot 3 to agree with slot 1 and
nothing knows that sixteen edge slots describe one graph. Stated sharply: **the machine is better
where the answer is one choice among *several* admissible answers (65.66%) than where it is a
*uniquely determined fact* (5.02%).**

**Limit 3 — the update budget stopped the run mid-descent.** The loss was at its global minimum and
the gradient norm still rising at the contract ceiling (ratio 1.378892, Spearman +0.317690, maximum
at update 93 of 160). It was still fitting the exposed course — 39/564 to 189/564 — while the
development panel stayed at zero and retention fell 11.4583 points. **More updates on the same
course would plausibly widen that gap, so the ceiling may be acting as a brake.**

## 5. The fixes, and what each is measured to be worth

**Fix A — analytic initialisation of the `^6` block. BUILT AND VALIDATED.**
Sets `left = I₆₄`, `right = 0`, `merge = [T | 0]`, so `^6(x) = T·tanh(x)` exactly, with `T` solved in
closed form **recurrence-aware**: fit on the states the block is actually given, not on the encoded
slot. Measured out-of-fold: **62.94% direct, 62.06% through the registered recurrence**, against the
trained learner's **1.24%** — **50.0×**. Verified robust to the ridge penalty (0.18-point spread over
three orders of magnitude) and to the recurrence's depth.
Code: `cncm/analytic_decompose.py`, `tools/prepare_analytic_arm.py`. Proposal with P1–P6 and G1–G7:
`records/analytic_decompose_phase0_001/PHASE0_RECORD_DRAFT.md` — **draft, unsigned**.
**Blocked on: an owner-signed phase record.** Arms, seeds and reservations are owner decisions and
are deliberately left open.

**Fix B — a composition layer. BUILT, NOT LICENSED.**
`Binding.commit` resolves an entity once and **refuses** a second, different value — the measured
defect (a `definition` answer citing two different worlds) becomes a refusal instead of a quiet
disagreement. `compose` derives the readings of a bound entity from its declared structure:
`edge_account`'s 16 slots as one edge reading, `context`'s setting and participants, `definition`'s
refs, `parts`' contained nodes. `role_set` derives nothing and is reported as undetermined.
Code: `cncm/composition.py`, 26 tests passing. **Blocked on: OS-026.**

**Fix C — the admitted-but-unused plastic role. NOT BUILT.**
The `^6` contract admits `('operation:^6', 'bias_update_head')`; the run uses one group. The head is
a real 4,096-parameter module that produces a proposal-only bias delta and is **absent** from the
run's module. **Blocked on: OS-027.** *Offered as a hypothesis only* — nothing shows a bias would
remove the concentration.

**A projection, labelled as one.** If Fix A restored the world-naming slot *and* Fix B derived the
many-decision readings perfectly given a correct binding, the exposed course would land near
`174 + 299 × 0.6206 ≈ 360 / 564 = 63.8%`, against 33.51% now. **That assumes perfect derivation,
which is not established, and it is a bound under stated assumptions, not a prediction.**

## 6. The decisions waiting

**Decision 1 — sign the phase-0 record, or not.** `records/analytic_decompose_phase0_001/PHASE0_RECORD_DRAFT.md`
is complete, runnable end-to-end, and unsigned. It needs: arms approved (A/B/C), seeds approved
(one or two), and a reservation amount. Ledger revision 84 holds **$4,499.00 unreserved**; the
precedent for a novel workload is **two $7 reservations**.

**Decision 2 — OS-026.** For four of the five many-decision kinds the query states `focus_world_id`
directly and the world's declarations are in the packet, so the machine is asked to reproduce by
64-way classification an identifier the question supplies. **Is that the intended task?** Task
deletion gives the machine the answer in its input and removes the task; a composition layer leaves
the machine to resolve *which* entity the question is about and only requires that the readings be
derived and consistent. Deriving all 34 slots would make 299 of 564 questions a lookup of material
the question already points at.

**Decision 3 — OS-027.** The contract admits two plasticity groups; the learner asserts its scope is
exactly the three `_DecomposeTransform` matrices with `"frozen": []`. Is that narrowing legitimate —
in which case the contract's second group is admitted but unusable from this path — or does it
strand an admitted mechanism?

**All three are authority decisions. None of them is an engineering blocker, and no work of mine
pre-empts any of them.**

## 7. Where every number comes from

`records/encoder_capacity_001/`: `DECISION_STRUCTURE_RESULT.md` (section 2's decomposition),
`UPDATE_TRAJECTORY_RESULT.md` (section 4 limit 3), `REACHABLE_SOLUTION_RESULT.md` (the readout and
module identities), `CONCENTRATION_SOURCE_RESULT.md` (limit 1), `RECURRENCE_AWARE_FIT_RESULT.md` and
`ARM_PENALTY_VERIFIED.md` (Fix A), `INFORMATION_LOSS_WITHDRAWN.md` (the information-preservation
figure), `INPUT_INDEPENDENCE_RESULT.md`.
`records/analytic_decompose_phase0_001/`: `PHASE0_RECORD_DRAFT.md`, `PREPARATION_RESULT.md`,
`preparation_report.txt`.
`records/composition_layer_001/STATUS.md` (Fix B). `records/bias_role_001/STATUS.md` and
`records/architecture_inventory_001/STATUS.md` (Fix C and section 1).
`records/noetica_corrections_001/STATUS.md` (Corrections 1–4).
`OPEN_QUESTIONS.md` OS-019 to OS-027.

## 8. What is NOT established

- **No run was launched in any round summarised here.** Every figure is a reading of the recorded
  run, of the frozen public course, or of the frozen contracts. The only executed code is
  arithmetic on plain lists, and `torch` was used **only to deserialise** checkpoints.
- **The accuracy figures for Fixes A and B are on ONE field each, not the whole-answer metric the
  course scores.** Focus-world alias decodability is a single 64-way choice. **The two must never be
  presented together as an improvement.**
- **Nothing here shows Fix A or Fix B would raise the recorded score.** Fix A's 62.06% is a
  construction measured out-of-fold on the learner's own 564-packet registry, with only 24 of 64
  worlds present. Fix B has never been run against any evaluation.
- **The concentration is not shown to be harmful.** A concentrated readout is not automatically a
  wrong one, and no measurement here ties it to an error rate.
- **The encoded slot used by several probes is a rebuild**, measured at **+0.781 correlation** with
  the recorded logits. Comparisons *between* feature sets or stages on the same rebuilt inputs are
  valid; no absolute number from those probes is the machine's.
- **Ten self-corrections are recorded**, four of them on claims made in earlier rounds of this same
  work. Three of the last five were caught by checking a claim against the artifact it came from.
- **One arm, one seed** (`MIXED_SAME_ITEMS`, `20260919`) underlies every recorded figure. The other
  five runs of the study were not decomposed, probed or swept.
