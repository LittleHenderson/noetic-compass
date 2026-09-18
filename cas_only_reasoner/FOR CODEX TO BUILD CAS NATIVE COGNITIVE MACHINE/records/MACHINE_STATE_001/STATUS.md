# The machine, measured — consolidated state after rounds 7 to 32

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

**And the decomposition holds in all six runs of the study**, not just this one
(`ALL_RUNS_RESULT.md`). Three seeds × two arms, worst-case gap **56.79 percentage points**, six of
six:

| | min | max | mean |
|---|---:|---:|---:|
| one-decision, after | 64.15% | 69.06% | **66.54%** |
| many-decision, one entity, after | 5.02% | 7.36% | **6.41%** |
| gap | **56.79 pp** | **63.37 pp** | **60.13 pp** |

**Three kinds have never once been answered.** `context` 0/70, `definition` 0/70 and
`edge_account` 0/70 — and they are **0.00% in every one of the six runs**, which is **1,260
individual question-attempts and not one correct answer**, across two arm conditions and three
independent model initialisations. `admissible_answer_count` is **1** for every question of all five
many-decision kinds — they are one fact to be got right in N places, not N questions.

**And the study's own contrast is small next to this.** The arm condition moves the one-decision half
by **under 1.2 points** on every matched seed pair, while the decision shape moves it by 57 to 63
points. **The decision shape is the dominant variable by a factor of about fifty.**

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

**Limit 1 — the trained readout mapping concentrates, and every run converges on the same alias.** At
cursor 160 the model emits only **9 to 11 of the 64 world aliases** across the 210 world-typed
reference slots, and **all six runs end with `W36` as the commonest** — shares **44.3% to 60.0%** —
from three independent initialisations under two curricula. On 210 task-free random inputs the
trained block narrows the readout in **every** run (53–57 distinct aliases to 27–32; 5.4–5.6 bits to
3.4–3.8), while the untrained block leaves it spread and the frozen readout's own geometry is
near-uniform (identity probe: 59 distinct, 3.3% commonest). **So the concentration is the training's
and it is general.**

**And `W36` is neither a training target nor a constant optimum.** The course presents **24** distinct
target aliases over 1,152 presentations, commonest `W15` at 5.8%, and **`W36` does not appear among
them at all**. The constant directions give `W20` (all-ones), `W37` (mean of all rows) and `W27`
(mean of target rows) — none is `W36`, against which it ranks 56th and 22nd respectively. **The
convergence is real, robust across six runs, and unexplained.**

**Limit 2 — the answer assembly has no composition.** The 299 many-decision questions score **5.02%**
against the 265 one-decision questions' **65.66%**. The forward pass emits one vector per slot and the
readout takes an independent argmax per slot, so nothing can force slot 3 to agree with slot 1 and
nothing knows that sixteen edge slots describe one graph. Stated sharply: **the machine is better
where the answer is one choice among *several* admissible answers (65.66%) than where it is a
*uniquely determined fact* (5.02%).**

> **Rounds 27–29 changed the diagnosis of this limit, and the change is adverse to the composition
> reading.** Per-bit measurement (`BITS_READ_RESULT.md`) grades each binary slot against a truth
> re-derived by the project's own checker, validated at **229/229 with zero disagreements in all six
> runs**. On the final cursor, per-bit accuracy against chance and against the best constant answer:
>
> | kind | per-bit | chance | best constant | vs constant | exact answers |
> |---|---|---|---|---|---|
> | `edge_account` | **62.7794% – 67.3469%** | **67.7444%** | **79.7862%** | **−12.4393 to −17.0068** | **0.0000%, all six runs** |
> | `parts` | 70.5314% – 73.9130% | 51.2707% | 57.9710% | **+12.56 to +15.94** | 22.6415% – 33.9623% |
> | `role_set` | 65.7407% – 70.8333% | 68.6728% | 80.5556% | **−9.72 to −14.81** | 8.3333% – 13.8889% |
> | `context` | 38.5768% – 41.5730% | 66.4184% | 78.6517% | **−37.08 to −40.07** | **0.0000%, all six runs** |
>
> **Three of the four kinds read their own bits at or below chance, and two of them would have done
> better by answering a constant.** `edge_account` is **below chance in all six runs** and
> never once got a 16-slot question's bits all right in 420 questions; `parts` reached 100% in 93 of
> 318. **So for three kinds there is nothing for a composer to compose** — which withdraws the
> round-26 reading of this limit, and with it the plan to extend the joint candidate branch beyond
> `correspondence`.
>
> **The `edge_account` row was corrected in round 32.** Through rounds 27–31 that kind's per-slot
> truth read a directed edge as undirected, doubling the apparent edge count. The published figures
> were 52.3810%–53.5471% per bit against a 51.8326% chance rate and a 59.5724% constant. The
> correction makes the machine look better in absolute terms and **worse against its baselines**:
> the deficit against a constant roughly doubles, from −6.03/−7.19 to **−12.4393/−17.0068**. The
> conclusion is unchanged and strengthened. Full account: `EDGE_DIRECTION_CORRECTION.md`.

**Limit 3 — the update budget stopped the run mid-descent.** The loss was at its global minimum and
the gradient norm still rising at the contract ceiling (ratio 1.378892, Spearman +0.317690, maximum
at update 93 of 160). It was still fitting the exposed course — 39/564 to 189/564 — while the
development panel stayed at zero and retention fell 11.4583 points. **More updates on the same
course would plausibly widen that gap, so the ceiling may be acting as a brake.**

**Limit 4 — the packet is invisible per slot before the block, and the block then destroys a signal
that is linearly present in its own input.** `encoder.py:212` is the whole slot encoding,
`normalize((packet + query)/√2)`, and `learner.py:153` reads it out linearly, so the packet's
contribution to a slot's decision is one constant per question. Measured on a pure-Python rebuild of
the frozen encoder that **reproduces both published sha256s exactly** (`projection 4481b1d2…fdd9`,
`readout 14da2c58…c667`):

| kind | before the block | chance | best constant | after the block | `before == name-alone` |
|---|---|---|---|---|---|
| `edge_account` | 51.6035% | 51.8326% | 59.5724% | 52.3810% – 53.5471% | **100.0000%** |
| `parts` | 47.8261% | 51.2707% | 57.9710% | 70.5314% – 73.9130% | 97.1014% |
| `context` | 49.0637% | 66.4184% | 78.6517% | 38.5768% – 41.5730% | **100.0000%** |
| `role_set` | 53.2407% | 68.6728% | 80.5556% | 65.7407% – 70.8333% | 94.4444% |

`before == name-alone` is the fraction of slots where the frozen readout's decision on
`normalize(packet + query)` is **identical** to its decision with the packet deleted. For
`edge_account` and `context` it is **100.0000%** — the packet changes nothing in 1,296 slots — and it
is identical in all six runs, as it must be: this is architecture, not training.

**But that is not the bottleneck.** For these kinds the answer is a function of the slot's own name
(the world alias is in every slot descriptor and each world's declarations are fixed across the whole
course), and the name carries it: a plain lookup keyed on it reads the bits at **96.4508%**
(`edge_account`) and **98.5926%** (`context`), and a linear probe of `encoded` reads `context` at
**96.3758%** where the block reads **40.8240%** — a **−55.55-point** loss that lands below the
78.6517% a constant earns. **So the block discards a linearly available signal, and that is the
larger and cheaper defect.** Source: `BINDING_VARIANTS_RESULT.md`.

**Limit 5 — per-bit headroom does not become answer-level headroom.** Turning the 96–98% per-bit
reading into whole answers was measured, not assumed: a memoriser fitted on four fifths of the
exposed course and scored on the held-out fifth gains **−6.7033 points** at the answer level
(26.2411% → 19.5378%), and `context` scores **0.0000%** on whole answers while reading its bits at
98.5926%. Whole-answer accuracy compounds over every field, and for `context` and `definition` the
binding constraint is the **alias-valued** field (`setting_ref`, `whole`, `kind_ref`, `function_ref`),
not the binary slots.

**Limit 6 — the architecture has ONE block and ONE readout, and the exam needs two different score
structures.** A **fitted** linear readout of `tanh(encoded)` — the exact construction
`decompose_from_free_readout` installs, `score_c = W[:,c]·tanh(x)` — scored through the project's own
`score_decisions` and `assemble_answer`, five folds by question. Harness validated: its
`frozen (recorded)` row reproduces the run's own exposed-course score at **33.5106%** and its
many-decision rate at **5.0167%**.

| family | q | recorded | fitted readout, correspondence in the fit | correspondence excluded |
|---|---|---|---|---|
| ONE DECISION | 265 | **65.6604%** | **21.5094%** | — |
| MANY DECISIONS | 299 | **5.0167%** | **12.0401%** | **16.0535%** |
| ALL | 564 | **33.5106%** | **16.4894%** | 18.6170% |

**This is the first change measured to lift the many-decision half (+7.0234 points, or +11.0368 with
`correspondence` excluded), and it is a net loss overall (−17.0213 points).** `definition` goes from
**0 of 70 to 18–31 of 70**; `parts` falls 7.55 points. Splitting the fit across both task families
costs the many-decision half 4.0 points, because `correspondence`'s 64-symbol vocabularies dominate a
single 90-class ridge fit.

**The binding constraint is that `T = R⁻¹Wᵀ` is a single 64×64 map.** One shared map cannot serve
both families: fit it for the many-decision kinds and the one-decision kinds lose 44.1510 points; fit
it for both and it is worse than the tuned machine on both halves. `correspondence`'s 93.18%–96.59%
depends on *relative* score structure that a one-hot ridge fit does not preserve.

**And the contract already admits two plasticity groups** — `('operation:^6', 'bias_update_head')`.
The run uses one; the `bias_update_head` is a real 4,096-parameter module absent from the run's
module (Fix C, OS-027); `/memory` appears as a `target_path` in the recorded `aws_saved_repair_v8_001`
lifecycle receipt. **Round 30 is the first evidence that the second group is not decorative.**

**Limit 7 — there is no composition defect left, and the whole deficit is one scalar per kind.**

> **Audited 2026-09-18 (`AUDIT_ROUNDS_32_33_RESULT.md` §1).** "No composition defect left" is NOT
> LICENSED: the measured exact rates rest on 1 to 3 correct questions (`1/70` has a 95% range of
> `0.04%`-`7.70%`), and the `edge_account` prediction with its real slot mix is `3.4289%`, not `1.82%`.
> The fitted readout here is a ridge fit on the frozen encoder, not the trained machine; its `77.8426%`
> is below always-ABSENT (`79.7862%`). "`setting_ref` is worth exactly +0.0000" holds for the fit
> only; the machine's own `setting_ref` is `0.0000%` (Limit 8).
Round 31/32 asked what each field of an answer is worth by giving that field the true symbol and
re-assembling through the project's own `assemble_answer`, and the answer is unambiguous:

| kind | field given the truth | accuracy |
|---|---|---|
| `edge_account` | `edge` | **100.0000%** |
| `role_set` | `role` | **100.0000%** |
| `parts` | `node` | **100.0000%** |
| `context` | `participant` | **75.7143%** (+71.4286) |
| `context` | `setting_ref` | 4.2857% (**+0.0000**) |

**Every single-field kind reaches 100% when its own field is correct.** The assembly is right, the
task is reachable, and exact-answer accuracy is simply **per-slot accuracy raised to the slot count**:

```
edge_account   0.778426^16                     =  3.43%   measured 1.4286%
role_set       0.694444^6                      = 11.22%   measured 8.3333%
context        0.528090^4 x 0.757143           =  5.89%   measured 4.2857%
```

**So the target is one measurable number per kind.** `edge_account` at 77.8426% per slot over 16 slots
yields 1.4% of answers; the same readout at 90% per slot yields 18.5%. And `definition` already reads
at **48.5714%**, the strongest many-decision kind.

> **Round 34 corrected the `context` reading that stood here.** It said "`context`'s deficit is
> entirely its four participant bits — `setting_ref` is worth **exactly +0.0000**". That was true only
> of the **analyst's fitted readout**, and it was misleading: an arm reports +0.0000 because that fit
> *already* reads `setting_ref` at 75.7143%, which then **caps `context` at 75.7143%** once the
> participants are fixed. It is not a field that costs nothing.
>
> On the **trained machine** the number is the opposite: `setting_ref` is right only **10.7143%** of
> the time against a 1.5625% chance rate for a 64-way choice. So `context` needs **both** fields
> repaired — two things, not one — and neither is done. Measured in round 34 by
> `measure_one_world_joint.py`; see `AUDIT_RESPONSE_AND_SELFLINKS.md` §5.
>
> **The per-kind rates above rest on 1 to 3 correct questions each** (1/70 has a 95% interval of
> 0.04%–7.70%), so they are **consistent with** pure compounding, not proof of it. Downgraded from
> "there is no composition defect left to explain", which the evidence does not support.

**Limit 8 — the composer ignores declared structure, and enforcing it is the first fix that works on

> **FLAG_FOR_HUMAN_REVIEW — audit 2026-09-18 (`AUDIT_ROUNDS_32_33_RESULT.md` §2.3).** The `context`
> lift below is no better than random: with the same count rule a random choice of three scores
> `163.5/420 = 38.9286%`, the machine's ranking `137/420 = 32.6190%` (AUC `0.466862`). The later
> `parts` result carries a real ranking signal (+23.2704 points on equal information, practised
> questions only). By the owner's ruling (section 6) these are rule-layer gains, not machine progress.
> The layer's ranking bug (PRESENT alone instead of the margin) is fixed; see section 6.
the trained machine's own scores.** `context` answers are the focus world's setting plus its
participants, and `answers.answer_space` declares `participants_basis =
PRIMARY_AUTHORED_LABELS_FIRST_THREE` — measured over all 420 `context` questions in six runs, the
truth cardinality is **exactly 3, every time**. So four participant slots are not four free bits; they
are a choice of which one node is absent. `score_decisions` never reads the declaration and takes an
independent `max` per slot.

Enforcing the declared cardinality on the **recorded** score table — force exactly three PRESENT by
the three highest `PRESENT − ABSENT` margins — with `setting_ref` held at the truth to isolate the
bits:

| run | bits, independent | bits, top-3 | exact, independent | exact, top-3 |
|---|---|---|---|---|
| 20260917_a | 39.7004% | **62.1723%** | 0.0000% | **37.1429%** |
| 20260917_m | 39.3258% | **63.2959%** | 0.0000% | **41.4286%** |
| 20260918_a | 38.5768% | **61.0487%** | 0.0000% | **32.8571%** |
| 20260918_m | 40.0749% | **61.0487%** | 0.0000% | **32.8571%** |
| 20260919_a | 41.5730% | **59.1760%** | 0.0000% | **25.7143%** |
| 20260919_m | 40.8240% | **59.1760%** | 0.0000% | **25.7143%** |
| **ALL SIX** | **40.0125%** | **60.9863%** | **0.0000%** | **32.6190%** |

**+20.9738 points per bit and 0.0000% → 32.6190% per answer, six for six.** The machine's threshold is
badly calibrated — 40.0125% per bit against a 78.6517% constant — but its **ranking** is well above
chance: ordered by margin, the truly-absent node lands outside the top three **60.9863%** of the time.
**A declared constraint converts an absolute-threshold problem into a ranking problem.**

**This is the first fix in this record that works on the trained machine's own scores** — round 30's
fitted readout was a substituted, hypothetical readout and cost more than it gained. It needs no new
information path, no capacity, no weights, no encoder change. **And it corrects round 27's refusal of
round 26:** there *is* something for the composer to do, not a joint likelihood but a declared
constraint. The bits were at chance *as thresholds* and are well above chance *as rankings*.

**The generalisation is architectural and untried.** Every kind carries declared structure in the
packet that nothing reads: `edge_account` (the focus world's `contains`, whose size is declared per
world), `parts` (direct targets of the supplied `whole`), `role_set`
(`ALL_AND_ONLY_SOURCE_GROUNDED_FOCAL_ROLES`), `definition` (`FOCUS_WORLD_DECLARATION_IDENTITY` — one
world's declaration, not three free choices). **The architecture already declares, per kind, what a
legal answer is. Nothing reads it.** Source: `DECLARED_CONSTRAINT_RESULT.md`.

**NOT LICENSED:** that a run would score 32.6190%. `setting_ref` is given the truth in that arm — the
machine's own `setting_ref` accuracy is 0.0000% on these questions — so **two things are needed, not
one**, and only one of them is measured.

**Round 33 generalised it to three more kinds, and two of them are truth-free.**

| kind | declaration enforced | independent | **constrained** | lift |
|---|---|---|---|---|
| **`parts`** | the declared out-edge count of the supplied `whole` | 29.2453% | **74.2138%** | **+44.9686%** |
| `definition` | `FOCUS_WORLD_DECLARATION_IDENTITY` — one world's triple, argmax over the bank | 0.0000% | **10.2381%** | **+10.2381%** |
| `edge_account` | the declared edge count of `focus["contains"]` | 0.0000% | **0.0000%** | **+0.0000%** |

Six runs each. `parts` lands between 73.5849% and 75.4717% in **all six**, and becomes the strongest
many-decision kind in the machine. **Neither arm uses any truth**: the cardinalities are read from the
packet the machine already receives and `definition`'s candidates are the bank.

```
parts        53 x (0.742138 - 0.292453) = +23.83 questions per run
definition   70 x (0.102381 - 0.000000) =  +7.17 questions per run
                                          +31.00 questions per run
```

**+31 questions per run against the six recorded 193/192/200/203/196/189 of 564 — the mean moves from
195.5/564 = 34.66% to 226.5/564 = 40.16%.** `context`'s +32.62 points are **not** counted, because
that arm holds `setting_ref` at the truth.

**`edge_account` is the clean negative, and it states the rule.** The constraint is identical in form
to the two that worked and it does nothing, because that kind's margins carry no signal — round 27
measured 62.7794%–67.3469% per bit against a **67.7444%** chance rate, below chance in all six
runs. **A constraint can reorder evidence; it cannot create it.** `parts` had a real signal
(51.2707% chance, 70.5314%–73.9130% per bit) and the constraint turned it into answers.

**So the architecture declares its own legality conditions per kind — `PRIMARY_AUTHORED_LABELS_FIRST_THREE`,
the declared edge counts, `FOCUS_WORLD_DECLARATION_IDENTITY`, `ALL_AND_ONLY_SOURCE_GROUNDED_FOCAL_ROLES`
— and `score_decisions` reads none of them.** A constraint layer is a **different mechanism** from a
composition layer, and it is the one the measurements support. Source:
`ALL_DECLARED_CONSTRAINTS_RESULT.md`. **NOT LICENSED:** that a run realises +31 questions — the
decoders were applied offline to the recorded scores, and `score_decisions` is untouched.

**Round 34 added a fourth declared constraint and the honest metric for edges.**

**Self-links are declared by absence.** Across the whole course — **216,576 world declarations,
649,728 declared edges — there are ZERO self-links.** The task never presents one. The recorded
machine calls **472 of 1,602 self-link slots PRESENT** (29.4632%), every one a false alarm by
construction. Forcing them ABSENT, truth-free, six runs:

| decoder | exact answers | per-slot |
|---|---|---|
| independent (the run's own rule) | 0.0000% (0 of 420) | 65.2251% |
| **self-links forced ABSENT** | **4.2857% (18 of 420)** | **72.8701%** |
| self-links ABSENT + declared cardinality | 4.2857% (18 of 420) | **74.3440%** |

**And the metric changed, on the strength of an independent audit. Per-slot accuracy is not a target
here:** after the direction fix only 20.2138% of edge slots are PRESENT, so always answering ABSENT
earns **79.7862%** for free. Measured properly, over 6,174 edge slots in six runs:

```
  edges FOUND       460 of 1248   36.8590%
  FALSE ALARMS     1359 of 4926   27.5883%
  balanced accuracy              54.6353%   (coin flip = 50%)
  plain per-slot   65.2251%      (always-ABSENT = 79.7862%)
```

**The machine's real edge-reading is 54.6353% balanced. Every edge figure in this record now uses that.**

**Round 34 also withdrew two round-33/34 overclaims.** "A constraint can reorder evidence; it cannot
create it" is **withdrawn**: `edge_account`'s cardinality constraint failed because it was the *wrong*
constraint, not because there was nothing to reorder — a different declared constraint moves the kind
off zero, and its balanced accuracy is above chance. The corrected rule is that **a declared
constraint helps in proportion to how little it asks of a weak reader.** And "there is no composition
defect left" is **withdrawn**, for the reasons given under Limit 7.

**Truth-free gains now measured, all six runs:**

| kind | mechanism | lift per run |
|---|---|---|
| `parts` | declared out-edge count of `whole` | **+23.83** of 53 |
| `definition` | `FOCUS_WORLD_DECLARATION_IDENTITY` | **+7.17** of 70 |
| `edge_account` | self-links are never PRESENT | **+3.00** of 70 |
| `context` | one-world joint decode | **+2.83** of 70 |
| | | **+36.83 per run of 564** |

mean **195.5/564 = 34.66% → 232.3/564 = 41.19%**. Source: `AUDIT_RESPONSE_AND_SELFLINKS.md`.

**Round 35 turned the audit's lucky find into a construction, and bounded it.** Scanning every
structural slot cell over all 64 worlds of the bank — keyed by kind, field, and node **positions within
their own world** — finds **exactly 8 cells whose symbol is the same in every world**:

```
  ('edge_account', 'edge', (0,0)) (1,1) (2,2) (3,3)   ->  ABSENT
  (       'parts', 'node', (0,0)) (1,1) (2,2) (3,3)   ->  ABSENT
  cells scanned: 36   constant: 8   mixed: 28
```

**Every constant is a self-link or a self-part, all ABSENT, and `context` has none at all** — its
participant cells are genuinely mixed across the worlds. **The class is bounded and now exhausted.**

| kind | q | independent | constants applied | hard-coded | lift |
|---|---|---|---|---|---|
| `edge_account` | 420 | 0.0000% | 1602 | **4.2857%** | **+4.2857%** |
| `parts` | 318 | 29.2453% | 318 | **31.7610%** | **+2.5157%** |
| `context` | 420 | 0.0000% | 0 | 0.0000% | **+0.0000%** |

`edge_account`'s +4.2857% **reproduces round 34's ad-hoc self-link result exactly**, from an
independently built measurement — an unplanned cross-check both pass. `parts`' +2.5157% is measured
against the **independent** baseline while its cardinality decoder already reaches 74.2138%: **the two
overlap, their combination is unmeasured, and they are not added.** The total stays **+36.83 per run**.
Source: `STRUCTURAL_CONSTANTS_RESULT.md`.

**Round 36 built the rectangular solve and closed a route.** `decompose_from_free_readout` requires
`nclass == core_width`, so it refuses the registered `[90, 64]` readout. The new
`decompose_from_free_readout_rectangular` takes `nclass > core_width` via
`T = (RᵀR)⁻¹RᵀWᵀ` and reports the residual. 13 new tests; 189 passing. **But it cannot realise every
`W`** — `R T` lands in the column space of `R`, so it realises the orthogonal projection only.

Measured on the real readout, five folds, 299 many-decision questions:

| | MANY DECISIONS |
|---|---|
| recorded (the run itself) | 5.0167% (15 of 299) |
| **direct free readout (idealised)** | **14.3813% (43 of 299)** |
| **through the registered `^6` block** | **4.0134% (12 of 299)** |

residual 0.1440–0.1851, **exact in 0 of 5 folds**; `definition` collapses 48.5714% → 8.5714%.

**Round 30's fitted-readout gain is an idealisation that cannot be installed.** The registered path
lands *below* the run's own score. **`Fix A` cannot improve the many-decision half by this route and
no GPU run should be spent trying.** The square requirement was never arbitrary: with `R` square,
`R·T = Wᵀ` is exactly satisfiable, which is why `Fix A`'s 62.94%/62.06% on focus identification is
real; with 90 rows and 64 columns only the projection is reachable, and there the gain dies.

**Three independent measurements now name the same component — the frozen readout.** Round 29 (packet
inert per slot), round 30 (the fit rides on the slot's *name*), round 36 (the name-derived fit cannot
be expressed through the readout either). Source: `RECTANGULAR_REALISATION_RESULT.md`.

**Round 37 built the constraint layer as tested code and measured it end to end.** Of the three
options below, the third needs no re-baselining — it touches only the decoder — so it was taken.
`cncm/answer_constraints.py` (new, additive, off by default; 16 tests, `2186 passed` overall) reads
the packet's declared legality conditions and corrects the decision table. It does **not** modify
`slots.score_decisions`, the encoder, the readout or the block.

Every question, every kind, **six runs, on the recorded scores**:

| kind | q | unconstrained | **constrained** | lift | selections changed |
|---|---|---|---|---|---|
| **`parts`** | 318 | 29.2453% | **80.8176%** | **+51.5723%** | 71.0692% |
| `definition` | 420 | 0.0000% | **10.2381%** | **+10.2381%** | 97.6190% |
| `context` | 420 | 0.0000% | **4.0476%** | **+4.0476%** | 97.8571% |
| `edge_account` | 420 | 0.0000% | **0.0000%** | **+0.0000%** | 97.8571% |
| correspondence / reach / analogy / role_set | 1806 | — | — | **+0.0000%** | **0.0000%** |
| **ONE DECISION** | 1590 | 66.5409% | 66.5409% | **+0.0000%** | |
| **MANY DECISIONS** | 1794 | 6.4103% | **18.8963%** | **+12.4861%** | |
| **ALL** | 3384 | **34.6631%** | **41.2825%** | **+6.6194%** | |

Per run: 193→222, 192→221, 200→249, 203→245, 196→231, 189→229 — **mean +37.3 of 564, six for six.**

**The property that makes this different from every previous attempt: the one-decision half is
unchanged at +0.0000%, and `selections changed` is 0.0000% for all four kinds the layer does not
constrain. There is no trade-off.** Round 30's fitted readout gained 7–11 points on one half and cost
44.1510 on the other. This gains **12.4861** and costs **nothing**.

`parts` reaches **80.8176%**, beating its cardinality rule (74.2138%) and its self-part rule
(31.7610%) applied separately — round 35 refused to add those figures because the combination was
unmeasured, and this is that combination. `edge_account` does not move, even with both rules applied
and 97.8571% of its selections changed: its balanced reading is 54.6353%, and a constraint can reorder
evidence but not create it. Source: `CONSTRAINT_LAYER_RESULT.md`.

**WITHDRAWN:** round 34's +36.83 per-run projection — pieces added on paper overlap, and the measured
per-kind attribution differs.

**FLAG_FOR_HUMAN_REVIEW — the wiring, and it is the only thing left.** Everything else on this list
required re-baselining; this does not. The layer ran **offline against recorded scores**. To count it
must be wired into the run's decision step, which changes the decision contract and its digest. That
is an owner decision, and this record does not take it.
**The open item is now sharp and singular. `parts`' constraint decoder reaches 74.2138% while
`context`'s best truth-free decoder reaches 4.0476% and `edge_account`'s reaches 4.2857%** — the same
gap round 27 measured, where `parts` reads its bits at 70.5314%–73.9130% against a 51.2707% chance rate
and the other two do not read at all. **The constraint layer is now as good as the readout underneath
it, and the readout is the binding constraint.**

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

**A projection, WITHDRAWN in round 27.** This record previously carried: if Fix A restored the
world-naming slot *and* Fix B derived the many-decision readings perfectly given a correct binding,
the exposed course would land near `174 + 299 × 0.6206 ≈ 360 / 564 = 63.8%`. **That is withdrawn.**
Round 27 measured three of the four binary kinds reading their own bits at or below chance and two of
them worse than a constant, so Fix B has nothing to derive; and round 29 measured that per-bit
recoverability does not convert into answer-level accuracy (Limit 5). **No route to 63.8% is
established, and none is proposed.**

**What rounds 27–29 put in its place — a location, not a projection.** Two defects, in order of size,
both measured: (i) the block discards a linear signal present in its own input, worst on `context`
(−55.55 points); (ii) the packet is inert per slot before the block, so any conjunction must be
synthesised by the recurrence, and it is synthesised for `parts` alone. **Neither has a tested fix.**
Two candidate fixes were tested and refused:
`BINDING_VARIANTS_RESULT.md` §2 refutes re-naming a pair-valued slot as a single token (**−2.03
points**, and `swapped` coordinates are byte-identical, so order is discarded), and the arity
hypothesis behind it is refuted by `context` sharing `parts`' arity and failing.

## 6. The decisions waiting

**RULED 2026-09-18 by the owner — what counts as progress.** Verbatim: **"IT MUST BE LEARNING LEARNING
AT THE NEURON LEVEL THE ARCHITECTURE SHOULD BE SERVING THIS PURPOSE. EVERYTHING SHOULD BE SERVING THIS
PURPOSE."** Applied: a gain from a hand-written rule over saved scores (the declared-constraint layer,
fitted readouts, closed-form weights at zero updates) is **not** progress of the machine. It is
reported separately and never added to a learned gain. The test of progress is what training changes
in the plastic weights, read on questions the machine was not taught (development panel) and on
retention. Source: `records/encoder_capacity_001/AUDIT_ROUNDS_32_33_RESULT.md` §0.

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
- **One arm, one seed underlies the probes, but not the central claim.** The decision-shape
  decomposition and the three never-answered kinds hold across **all six runs** of the study
  (`ALL_RUNS_RESULT.md`). The concentration measurements, the stage probes, the penalty sweeps and
  the arm-A preparation rest on `receipt_20260919_m` alone, because those need the checkpoints and
  the cached features, which exist only for that run.
