# CONSTRAINT_LAYER_RESULT — +6.6194 points overall, +12.4861 on the many-decision half, and the one-decision half is untouched

> **Superseded in part, 2026-09-18 — ranking bug.** The committed `_apply_cardinality` ranked by the PRESENT score alone, against its own docstring ("PRESENT minus ABSENT"). With the margin: `parts` 257/318 -> 277/318, `edge_account` 0/420 -> 18/420. Fixed as `_margin_rank` with a regression test; re-measured in `constraint_layer_corrected.txt`; see `AUDIT_ROUNDS_32_33_RESULT.md` §3 and §5. The `edge_account` "cannot create evidence" reading below rested on the bug. By the owner's ruling of 2026-09-18 this layer's gains are rule-layer gains, reported separately from learned gains.

**Round 37. The declared-constraint layer is built as tested code, and measured end to end.**
**$0.00. Pure standard library plus the project's pure modules. No torch, no GPU, no model, no
training, no new run.**

Code: `cncm/answer_constraints.py` (new, additive, off by default).
Tests: `tests/test_answer_constraints.py` (16 new).
Measurement: `records/encoder_capacity_001/measure_constraint_layer.py`, `constraint_layer.txt`.

---

## 1. What was built

`slots.score_decisions` has two branches: an independent per-slot `max`, and a joint candidate MAP for
`correspondence` alone. Every other kind is decided slot by slot with no knowledge of what the packet
says a legal answer looks like — **and the packet says it, per kind, and nothing reads it.**

`cncm/answer_constraints.py` reads it. Three rules, each with its own measurement behind it:

1. **Self-links and self-parts are ABSENT.** Across 216,576 world declarations and 649,728 declared
   edges there are **zero** self-links. Structural: true of the task, not of a run.
2. **Declared cardinality.** `focus["contains"]` is in the packet, so the PRESENT count is known;
   likewise the declared out-edge count of the supplied `whole`; likewise
   `PRIMARY_AUTHORED_LABELS_FIRST_THREE` for a `context` participant set.
3. **One-world identity.** `FOCUS_WORLD_DECLARATION_IDENTITY` — a `definition` answer is one world's
   declaration triple and a `context` answer is one world's setting plus participants. Enumerate the
   bank, score each world's implied answer, take the argmax.

**It is additive and off by default.** It does not modify `slots.score_decisions`, the encoder, the
readout, or the block. Importing it changes no existing behaviour, and it is not wired into any run.
16 tests, all passing.

## 2. The measurement — every question, every kind, six runs

```
           kind     q  unconstrained  constrained      lift  selections changed
        analogy   420      16.1905%    16.1905%  +0.0000%            0.0000%
        context   420       0.0000%     4.0476%  +4.0476%           97.8571%
 correspondence   528      94.5076%    94.5076%  +0.0000%            0.0000%
     definition   420       0.0000%    10.2381% +10.2381%           97.6190%
   edge_account   420       0.0000%     0.0000%  +0.0000%           97.8571%
          parts   318      29.2453%    80.8176% +51.5723%           71.0692%
          reach   642      76.4798%    76.4798%  +0.0000%            0.0000%
       role_set   216      10.1852%    10.1852%  +0.0000%            0.0000%
   ONE DECISION  1590      66.5409%    66.5409%  +0.0000%
 MANY DECISIONS  1794       6.4103%    18.8963% +12.4861%
            ALL  3384      34.6631%    41.2825%  +6.6194%
```

Per run, exact counts:

| run | ALL, unconstrained | ALL, constrained | lift |
|---|---|---|---|
| 20260917_a | 193 of 564 | **222** | +29 |
| 20260917_m | 192 of 564 | **221** | +29 |
| 20260918_a | 200 of 564 | **249** | **+49** |
| 20260918_m | 203 of 564 | **245** | +42 |
| 20260919_a | 196 of 564 | **231** | +35 |
| 20260919_m | 189 of 564 | **229** | +40 |

**Mean +37.3 questions per run, 195.5/564 = 34.6631% → 232.9/564 = 41.2825%. Six for six, every run
improves.**

## 3. The property that makes this different from every previous attempt

**The one-decision half is unchanged: +0.0000%.** `selections changed` is **0.0000%** for `analogy`,
`correspondence`, `reach` and `role_set` — the layer does not touch a single one of their decisions.

**So there is no trade-off.** Round 30's fitted readout raised the many-decision half by 7–11 points
and cost the one-decision half **44.1510** points; net, a loss. This raises the many-decision half by
**12.4861** and costs the other half **exactly nothing**.

**And it needs no new baseline.** The model, encoder, readout and block are all untouched, so a run
using this is comparable to every existing run except in the decision contract's digest. It is the one
option on round 36's list that does not require re-baselining — which is why it was taken.

## 4. `parts` improves on the sum of its parts, and `edge_account` does not move

**`parts` reaches 80.8176%**, against 74.2138% for the cardinality rule alone (round 33) and 31.7610%
for the self-part rule alone (round 35). Round 35 explicitly said the **combination** was unmeasured
and refused to add the two figures. **This is that combination measured: 29.2453% → 80.8176%,
+51.5723 points, and it beats both rules applied separately.** `parts` is now the strongest
many-decision kind in the machine, behind only `correspondence` and `reach`.

**`edge_account` does not move: 0.0000% → 0.0000%**, even with self-links *and* cardinality applied,
and even though 97.8571% of its selections are changed. That is consistent with round 33 and with the
honest metric from the audit: its per-slot reading is **54.6353% balanced**, barely above a coin flip,
and **a constraint can reorder evidence but not create it.** The layer's own rules are sound there —
they simply have nothing to work with.

## 5. A bug the real data caught, and the fixture fix that follows

The first end-to-end run raised `KeyError: 'alias'`. **The packet's world nodes carry `ref`, `kind` and
`label` — not `alias`.** Aliases live in the plan's alias table
(`slots.compile_slots(packet)["aliases"]`). The unit tests had passed because my own fixture put
`alias` on the packet's nodes, which real packets never do.

Both were fixed: the module now reads the alias table, and **the fixture is deliberately faithful** —
its world nodes carry no `alias`, and its alias table is positional, matching reality. The corrected
fixture is the reason the bug would now be caught, and that is the same discipline the round-34 audit
imposed.

**It is the fourth time in four rounds that running against real artifacts found something a
hand-built fixture hid.**

## 6. Claim status

- **REAL, measured, truth-free:** §2's table and §3's arithmetic. Both arms read the **recorded** score
  table; no target enters either decoder. Correctness is admissible-**set** membership, because
  `analogy` and `correspondence` admit 6–9 and 1–6 answers per question.
- **REAL:** the 16 tests, and that the layer is additive — `selections changed` is 0.0000% on every
  kind it does not constrain.
- **WITHDRAWN:** round 34's **+36.83 per run** projection. Pieces added on paper overlap; the measured
  combination is **+37.3 questions per run** from the module, but the per-kind attribution differs —
  `parts` gains more (+51.5723 rather than +44.9686) and `edge_account` gains nothing.
- **NOT LICENSED:** that a run realises +6.6194 points. The layer ran **offline against recorded
  scores**. To count, it must be wired into the run's decision step, which changes the decision
  contract and its digest, and that is an owner decision this record does not take.
- **FLAG_FOR_HUMAN_REVIEW:** the wiring. Everything else on round 36's list required re-baselining;
  this does not, and it is built and tested. **Wiring it into `score_decisions`, or running a new arm
  with it selected, is the next decision — and it is yours.**
