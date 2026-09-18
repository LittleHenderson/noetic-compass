# BITS_READ_RESULT — the many-decision kinds are not mis-composed, they are unread

**Round 27. New measurement. Establishes a result that reframes the central finding of round 26.**
**$0.00. Pure Python, standard library plus the project's own pure modules. No torch, no GPU, no
model, no training, no new run.**

Script: `measure_bits_read.py`. Raw output: `bits_read.txt`.
Companion mechanism test (refuted): `measure_slot_evidence.py`, `slot_evidence.txt`.

> ## CORRECTION — round 32. Every `edge_account` number below is superseded.
>
> This record read a **directed** edge as **undirected**: it tested
> `tuple(sorted((source, target)))`, which conflates `(a,b)` with `(b,a)` and doubles the apparent
> edge count. Found in round 31 via an impossible reading (`edge_account` scored 0.0000% when given
> the answer), diagnosed by `probe_edge_reachability.py`, and fixed. Full account:
> `EDGE_DIRECTION_CORRECTION.md`.
>
> | `edge_account` | as published below | **corrected** |
> |---|---|---|
> | per-bit accuracy, six runs | 52.3810% – 53.5471% | **62.7794% – 67.3469%** |
> | truth PRESENT rate | 40.4276% | **20.2138%** |
> | chance | 51.8326% | **67.7444%** |
> | best constant | 59.5724% | **79.7862%** |
> | machine − best constant | −6.0253 to −7.1914 | **−12.4393 to −17.0068** |
> | exact answers | 0.0000%, all six | 0.0000%, all six (**unchanged**) |
>
> **The conclusion is unchanged in direction and stronger in degree.** The machine reads
> `edge_account` at 62.7794%–67.3469% where chance is 67.7444% — **below chance in four of six runs**
> — and 12.4393 to 17.0068 points below a constant answer. Every `parts`, `role_set`, `context` and
> `definition` figure in this record is unaffected. `bits_read.txt` on disk is the **corrected** run.
> The corrected `edge_account` histogram never reaches 0% or 100% in 420 questions either.

---

## 1. What was owed

Round 26 (`COMPOSITION_BRANCH_RESULT.md`) established that `slots.score_decisions` composes
**jointly for exactly one kind** — `correspondence` — and **per-slot independently for the other
seven**, and that the joint kind is the one that works:

| decision shape | kinds | questions | before | after |
|---|---|---|---|---|
| ONE DECISION | correspondence, reach, analogy | 265 | 11.32% | **65.66%** |
| MANY INDEPENDENT DECISIONS ABOUT ONE ENTITY | edge_account, role_set, parts, context, definition | 299 | 3.01% | **5.02%** |

held in all six runs, gap 56.79–63.37 points. That record named the one composition mechanism and
said, in its own words, that the joint branch had **not been shown to cause** the accuracy — no
ablation was run.

The natural reading was: the architecture composes jointly for the kind that works and
independently for the kinds that do not, therefore extend the joint mechanism.

**This record measures the premise of that reading, and refutes it.**

## 2. Why it was measurable at all

The answer to every many-decision question is a **field of the packet the learner can see**. For
`edge_account` the checker reads `focus["contains"]` (world's declared edge list, a top-level key
present in every world of `packet["source"]["worlds"]`) and the slots are exactly the directed
pairs of the focus's nodes. For `parts`, `role_set` and the `context` participants it is the same
shape: N binary slots whose PRESENT set **is** the answer.

So the true symbol of every binary slot follows from the derived answer through the same mapping
`slots.assemble_answer` uses, walked in the opposite direction — **with no private material**.

### The pipeline validated itself

The checker was re-run on the public snapshot for every question, and the resulting answer compared
to the answer the machine actually submitted. That comparison **must** reproduce the run's own
recorded `correct` flag:

```
receipt_20260917_a: pipeline validation agree=229 disagree=0  of 229 binary questions
receipt_20260917_m: pipeline validation agree=229 disagree=0  of 229 binary questions
receipt_20260918_a: pipeline validation agree=229 disagree=0  of 229 binary questions
receipt_20260918_m: pipeline validation agree=229 disagree=0  of 229 binary questions
receipt_20260919_a: pipeline validation agree=229 disagree=0  of 229 binary questions
receipt_20260919_m: pipeline validation agree=229 disagree=0  of 229 binary questions
```

**229 of 229, zero disagreements, six runs, six-for-six.** The derivation is the run's own checker.
Every number below is therefore read through the run's own semantics, not through a reimplementation.

## 3. The measurement

Final cursor, all six runs. `selected` and `argmax` are identical in **every row of every run** —
the binary slots are decoded by plain argmax, so this is a **readout** property, not a decoder
artifact.

`chance` = `p² + (1−p)²` for p = the truth PRESENT rate of that kind's slots. `always-A`/`always-P`
is what a decoder that always answered that symbol would have earned on the same slots. The last
column is the machine's per-bit accuracy minus the better of those two constants.

| run | kind | q | bits | selected | exact | chance | always-A | always-P | vs best const |
|---|---|---|---|---|---|---|---|---|---|
| 20260917_a | edge_account | 70 | 1029 | 53.2556% | 0.0000% | 51.8326% | 59.5724% | 40.4276% | **−6.3168%** |
| 20260917_a | parts | 53 | 207 | **73.9130%** | 30.1887% | 51.2707% | 42.0290% | 57.9710% | **+15.9420%** |
| 20260917_a | role_set | 36 | 216 | 65.7407% | 13.8889% | 68.6728% | 80.5556% | 19.4444% | **−14.8148%** |
| 20260917_a | context | 70 | 267 | 39.7004% | 0.0000% | 66.4184% | 21.3483% | 78.6517% | **−38.9513%** |
| 20260917_m | edge_account | 70 | 1029 | 53.4500% | 0.0000% | 51.8326% | 59.5724% | 40.4276% | **−6.1224%** |
| 20260917_m | parts | 53 | 207 | 73.4300% | 32.0755% | 51.2707% | 42.0290% | 57.9710% | **+15.4589%** |
| 20260917_m | role_set | 36 | 216 | 68.5185% | 13.8889% | 68.6728% | 80.5556% | 19.4444% | **−12.0370%** |
| 20260917_m | context | 70 | 267 | 39.3258% | 0.0000% | 66.4184% | 21.3483% | 78.6517% | **−39.3258%** |
| 20260918_a | edge_account | 70 | 1029 | 52.9640% | 0.0000% | 51.8326% | 59.5724% | 40.4276% | **−6.6084%** |
| 20260918_a | parts | 53 | 207 | 71.4976% | 26.4151% | 51.2707% | 42.0290% | 57.9710% | **+13.5266%** |
| 20260918_a | role_set | 36 | 216 | 68.0556% | 8.3333% | 68.6728% | 80.5556% | 19.4444% | **−12.5000%** |
| 20260918_a | context | 70 | 267 | 38.5768% | 0.0000% | 66.4184% | 21.3483% | 78.6517% | **−40.0749%** |
| 20260918_m | edge_account | 70 | 1029 | 52.8669% | 0.0000% | 51.8326% | 59.5724% | 40.4276% | **−6.7055%** |
| 20260918_m | parts | 53 | 207 | 73.9130% | 33.9623% | 51.2707% | 42.0290% | 57.9710% | **+15.9420%** |
| 20260918_m | role_set | 36 | 216 | 70.8333% | 8.3333% | 68.6728% | 80.5556% | 19.4444% | **−9.7222%** |
| 20260918_m | context | 70 | 267 | 40.0749% | 0.0000% | 66.4184% | 21.3483% | 78.6517% | **−38.5768%** |
| 20260919_a | edge_account | 70 | 1029 | 52.3810% | 0.0000% | 51.8326% | 59.5724% | 40.4276% | **−7.1914%** |
| 20260919_a | parts | 53 | 207 | 72.9469% | 30.1887% | 51.2707% | 42.0290% | 57.9710% | **+14.9758%** |
| 20260919_a | role_set | 36 | 216 | 68.0556% | 8.3333% | 68.6728% | 80.5556% | 19.4444% | **−12.5000%** |
| 20260919_a | context | 70 | 267 | 41.5730% | 0.0000% | 66.4184% | 21.3483% | 78.6517% | **−37.0787%** |
| 20260919_m | edge_account | 70 | 1029 | 53.5471% | 0.0000% | 51.8326% | 59.5724% | 40.4276% | **−6.0253%** |
| 20260919_m | parts | 53 | 207 | 70.5314% | 22.6415% | 51.2707% | 42.0290% | 57.9710% | **+12.5604%** |
| 20260919_m | role_set | 36 | 216 | 69.4444% | 8.3333% | 68.6728% | 80.5556% | 19.4444% | **−11.1111%** |
| 20260919_m | context | 70 | 267 | 40.8240% | 0.0000% | 66.4184% | 21.3483% | 78.6517% | **−37.8277%** |

### The same, as ranges across the six runs

| kind | selected | exact | vs chance | vs best constant |
|---|---|---|---|---|
| edge_account | 52.3810% – 53.5471% | **0.0000% in all six** | +0.55 to +1.71 | **−6.03 to −7.19** |
| parts | 70.5314% – 73.9130% | 22.6415% – 33.9623% | +19.26 to +22.64 | **+12.56 to +15.94** |
| role_set | 65.7407% – 70.8333% | 8.3333% – 13.8889% | **−2.93 to +2.16** | **−9.72 to −14.81** |
| context | 38.5768% – 41.5730% | **0.0000% in all six** | **−24.85 to −27.84** | **−37.08 to −40.07** |

### The bits-correct distribution, all 420/318/216/420 questions

Bucketed by the fraction of that question's own slots answered correctly.

```
edge_account   (420 questions, slot counts {9: 13, 16: 57})
    30% correct    20    4.76%
    40% correct   124   29.52%
    50% correct    54   12.86%
    60% correct   164   39.05%
    70% correct    45   10.71%
    80% correct    13    3.10%
   -- never 0%, never 90%, never 100%

parts   (318 questions, slot counts {3: 5, 4: 48})
     0% correct     2    0.63%
    20% correct    22    6.92%
    30% correct     4    1.26%
    50% correct    62   19.50%
    70% correct    16    5.03%
    80% correct   119   37.42%
   100% correct    93   29.25%     <-- all slots right, 93 times

role_set   (216 questions, 6 slots each)
    20% correct     2    0.93%
    30% correct     9    4.17%
    50% correct    52   24.07%
    70% correct    76   35.19%
    80% correct    55   25.46%
   100% correct    22   10.19%     <-- all six slots right, 22 times

context   (420 questions, slot counts {3: 13, 4: 57})
     0% correct   137   32.62%     <-- every single slot wrong
    20% correct    50   11.90%
    30% correct    13    3.10%
    50% correct    78   18.57%
    70% correct     4    0.95%
    80% correct   138   32.86%
   -- never 100%
```

**`edge_account` never once got a question's slots all right, in 420 questions**, and its accuracy
is pinned in a 30%–80% band with 68.57% of the mass at 40% or 60%. That is the signature of a
decoder emitting a rough half-right pattern regardless of the question, not of one reading and
occasionally succeeding. **`parts` reaches 100% in 93 of 318 questions; `role_set` reaches 100% in
22 of 216.** The difference is categorical, not a matter of degree.

**`context` is bimodal**: 137 questions at 0% and 138 at 80%, with almost nothing in between. A
third of the time the machine gets *every participant slot wrong* — the signature of emitting the
complement of the truth.

## 4. What this means

**Three of the four kinds carry essentially no per-bit information, and two of them are worse than
a constant answer.**

`edge_account` reads its edge bits at 53.5471% where chance is 51.83% — **+1.72 points**. This is
the kind that scored 0 correct in 70 questions in all six runs, 0 correct in 1,260 attempts across
the five many-decision kinds. It is not that the machine reads the bits and loses the answer in
composition. It reads almost none of them, and it would have done **better by asserting "no edges
at all"** on every question — by 6.03 points.

`context` is worse still: 40.8240% where always-ABSENT earns 78.6517%, a **37.83-point deficit**.
The machine systematically over-asserts PRESENT on a field that is three-quarters PRESENT-or-absent
by construction (`PRIMARY_AUTHORED_LABELS_FIRST_THREE`).

`role_set` reads at 69.4444% against a 68.67% chance rate — **+0.78 points, no signal** — and sits
11.11 points *below* always-ABSENT.

**`parts` is the exception, and it is the clue.** It reads at 70.5314%, +19.26 over chance and
+12.56 over the better constant. It is also the only one of the four with a non-zero exact-match
rate. Whatever `parts` does, it is doing something the other three are not.

## 5. The consequence for the architecture

**A composer cannot compose information the readout never carried.**

This is a decisive negative for the reading of round 26 that said "extend the joint branch to the
many-decision kinds". The joint branch helped `correspondence` because `correspondence`'s readout
**does** carry per-node information — `_candidate_scores` scores each enumerated bijection against
per-slot logits that discriminate among target node aliases, and the summed score picks the right
one 93.18%–96.59% of the time. The branch supplies a **constraint over an informative readout**.

For `edge_account` there is no such informative readout: at +1.72 points over chance there is
nothing to constrain. Enumerating candidates, scoring them jointly, snapping to an entity-consistent
completion — none of these can help, and the projection recorded in
`records/MACHINE_STATE_001/STATUS.md` (which put the machine at `174 + 299 × 0.6206 ≈ 360 / 564 =
63.8%`, there explicitly labelled as assuming perfect derivation) is not available by that route.

**The defect is upstream of composition, in whether the readout is addressed by the slot at all.**

### Where that points

`encoder.py` line 212 is the whole of the slot encoding:

```python
result = normalize((entry["vector"] + query) / math.sqrt(2.0))
```

One packet vector plus one slot vector, **added**. `learner._forward` line 153 then reads out
`readout_rows[indexes] @ vector`, which is **linear** in that sum. So for two slots s, t of one
question, sharing the packet term and the readout row r for a symbol:

```
logit(s, PRESENT) − logit(s, ABSENT) ∝ d·p + d·q(s)
logit(t, PRESENT) − logit(t, ABSENT) ∝ d·p + d·q(t)
```

with the same `d = readout[PRESENT] − readout[ABSENT]` and the same packet term `d·p` in both. A set
membership question asks for `f(pair, S)` — a **conjunction** of a slot and the focus world's
declared set. An additively bound representation read by a linear functional computes `g(pair) +
h(S)`: a sum, not a conjunction. `binding._query_spec` builds `q` out of

```
kind, field, group, scope_alias, coordinates, symbols
```

— the slot's name and its world's alias. No declaration content enters. Every fact about the focus
world's declared edge set arrives as **one constant per question**, added identically to all
sixteen slots.

The recurrence is nonlinear and can in principle synthesise the missing product. Depth 8 of a
16,384-parameter block trained from scratch evidently does not: the trained block lands at 53.5471%
against a 51.83% chance rate.

> **Round 29 corrected the consequence of this, without changing the measurement.** The packet *is*
> inert per slot — `measure_binding_ceiling.py` measures `before == name-alone` at **100.0000%** for
> `edge_account` and `context`, 97.1014% for `parts`, 94.4444% for `role_set`, identically in all six
> runs. But that does not make the binding the bottleneck, because for these kinds **the answer is a
> function of the slot's own name**: the world alias is in every slot descriptor, and a plain lookup
> keyed on it reads the bits at **96.4508%** (`edge_account`) and **98.5926%** (`context`) where the
> trained block reads them at 53.5471% and 40.8240%. So the larger loss is not that the block cannot
> synthesise the conjunction — it is that the block **destroys a linear signal present in its own
> input**: `context` sits at 96.3758% under a plain linear probe of `encoded` and 40.8240% after the
> block, a **−55.55-point** loss, landing below the 78.6517% a constant answer earns. See
> `BINDING_VARIANTS_RESULT.md` §3–§4. §5's three routes below are therefore **not** the leading
> candidate any more; the leading candidate is whatever the block does to its own input.

**This is the architectural diagnosis, and it is where the payoff is.** Three routes follow, none of
them taken here and none of them authorised by this record:

1. **Multiplicative binding in the encoder.** Replace `packet + query` with a binding that carries a
   product term — concatenate `[packet, query, packet ⊙ query]` and project, so the conjunction is
   expressible in one linear readout layer.
2. **Slot-conditioned readout.** Let the readout be addressed by the slot rather than by the symbol
   alone, so a slot can select which part of the packet vector to read.
3. **Engineered transparency (Fix A, already measured).** The analytic decomposition initialises the
   block to `T·tanh(x)`, inverting the readout and creating a read path by construction: 62.94%
   direct and 62.06% through the registered recurrence, out-of-fold, against 1.24% for the trained
   block — a 50.0× factor.

## 6. Claim status

- **REAL** (measured, arithmetic on recorded artifacts, no model): the per-bit accuracies, the
  chance and constant baselines, the exact-match rates, the 229/229 pipeline validation. Artifact:
  `bits_read.txt`, `measure_bits_read.py`.
- **REAL**: `selected` equals `argmax` on every binary slot in the measured cursor. Artifact: the
  `selected` and `argmax` columns agreeing to four decimal places in every row.
- **NOT LICENSED**: any claim that a composition change would raise the many-decision kinds. §5
  refutes the route.
- **WITHDRAWN, this round**: the hypothesis that the additive binding leaves *no* per-slot variation
  at all (`measure_slot_evidence.py`). Refuted — within-question margin spread is 36.1%–53.9% of the
  whole-kind spread, and `edge_account` never emits a constant. Variation exists; §3 shows it does
  not track the truth.
- **OPEN**: whether `parts` reads because of its single-coordinate slot, or because of structure in
  the course. **Answered in round 29 and the arity answer is no** — see `BINDING_VARIANTS_RESULT.md`
  §2. `context` participants carry one node ref per slot, the same arity as `parts`, and `context`
  fails at 40.8240% against a 78.6517% constant while `parts` succeeds at 70.5314% against a 57.9710%
  constant. Slot arity does not separate success from failure. What does separate them remains open.

## 7. What this does not say

- It does not say the machine is broken. `correspondence` at 93.18%–96.59% is real work.
- It does not say the encoder is informationless. It says the readout's per-slot discrimination does
  not track set membership for these fields — which is a statement about the *binding*, and about
  the trained block's failure to synthesise the product, not about the packet.
- It does not authorise a code change. §5's three routes are proposals; none is licensed by this
  record. The `PHASE0_RECORD_DRAFT.md` remains unsigned and authorises nothing.
