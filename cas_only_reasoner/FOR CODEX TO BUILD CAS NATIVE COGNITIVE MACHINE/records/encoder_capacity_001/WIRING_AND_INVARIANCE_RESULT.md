# WIRING_AND_INVARIANCE — the layer's gain is world-invariant, exposure is not the explanation, and the wiring is far cheaper than I said

**Round 40. Two open items closed, one recorded defect fixed, and a correction to my own rounds 36–37.**
**$0.00. Pure standard library plus the project's pure modules. No torch, no GPU, no model, no
training, no new run.**

Scripts: `measure_exposure_vs_structure.py` (sections 4–5, re-run), `measure_wiring_impact.py`,
`diagnose_section4.py`. Outputs: `exposure_vs_structure.txt`, `wiring_impact.txt`.

---

## 1. The recorded defect is fixed, and what it was

Round 39 recorded a failed measurement rather than a number: section 4 reported `records` 269 and 295
with `obs` 0 **and the failure counters 0 too**, which meant the inner loop incremented nothing.
`diagnose_section4.py` reproduced the per-record logic on a single record and got **6 observations**,
so **the per-record logic was sound and the fault was in the counter handling.**

The section is rewritten with plain integer counters — the formulation `diagnose_section4.py` verified
— and the world partition is now **fixed** (worlds sorted by id, split at the median) instead of
`hash(world) % 2`, which is **salted per process** and so was not the same partition twice. **The
lesson is the round-34 audit's, used again: when a harness reports nothing, suspect the harness.**

## 2. The constraint layer's gain is world-invariant — round 37's claim, now tested

| half | records | observations | unconstrained | **constrained** | gain |
|---|---|---|---|---|---|
| 0 | 282 | 1692 | 33.8061% | **40.3664%** | **+6.5603%** |
| 1 | 282 | 1692 | 35.5201% | **42.1986%** | **+6.6785%** |

**The gain is +6.5603% on one half of the worlds and +6.6785% on the other — a difference of 0.1182
points.** The two halves' baselines are likewise close (33.8061% against 35.5201%), so the partition is
balanced.

**So the layer's benefit does not depend on which worlds are in front of it.** That is what round 37
claimed when it said the layer is carried by the packet rather than by memorised worlds, and it was
**asserted and untested** until now. **It is tested and confirmed.**

## 3. Exposure is not the explanation — the overall correlation was a kind confound

The overall exposure/correctness Spearman correlation was **+0.1451**, recorded in round 39 as weak and
confounded. Computed **within each kind**:

| kind | questions | Spearman(exposure, correct) | exposure range |
|---|---|---|---|
| `analogy` | 70 | **+0.2619** | 1..3 |
| `context` | 70 | undefined | 1..3 |
| `correspondence` | 88 | **+0.0036** | 1..14 |
| `definition` | 70 | undefined | 1..3 |
| `edge_account` | 70 | undefined | 1..3 |
| `parts` | 53 | **−0.2719** | 1..14 |
| `reach` | 107 | **−0.1930** | 1..17 |
| `role_set` | 36 | +0.1179 | 2..3 |

**Within kind the correlation is near zero or negative.** `correspondence` +0.0036 over an exposure
range of 1 to 14; `parts` **−0.2719** and `reach` **−0.1930**, both negative over the widest ranges.
Only `analogy` is meaningfully positive, and its range is 1..3 questions.

**The `+0.1451` was a kind confound and nothing else.** Exposure does not carry accuracy; more
presentations do not make a question more likely to be answered correctly. **The exposure question is
closed.**

*The three undefined cells are kinds whose correctness has zero variance within kind — `context`,
`definition` and `edge_account` are 0.00% throughout — so a rank correlation has no denominator. That
is expected, not a defect.*

## 4. The wiring is far cheaper than rounds 36 and 37 said — measured, and I was wrong

Rounds 36 and 37 described wiring the constraint layer as "changes the decision contract and its
digest", which reads as expensive. **Whether it is expensive is a question about code, so it was
answered rather than assumed.** The same 564 packets were compiled twice — once with the registered
`slots.DECISION_CONTRACT` and once with a contract amended to describe a constraint layer — and every
slot's encoder input compared:

```
kinds covered                        8  ['analogy','context','correspondence','definition',
                                        'edge_account','parts','reach','role_set']
packets compared                     564
slots compared                       2598

plan_digest changed, packets            564 of 564
slot_id set changed, packets              0 of 564
encoder query spec changed, slots         0 of 2598
encoder query BYTES changed, slots        0 of 2598
```

**The encoder's entire input is unchanged.** `binding._query_spec` reads kind, field, group, scope,
coordinates and symbols — never the contract — so every encoded vector, every score, and every
recorded prediction's `scores` are identical. **What changes is `plan_digest` and the decisions.**

**So wiring the layer does not invalidate the model, the encoder, the readout or the block, and it
requires no new baseline for any of them.** My earlier phrasing was true and misleading, and this
measurement does not support it. **Corrected here.**

*Caveat, stated because it is a property of the current code and not a guarantee:* `binding.compile_packet`
does not read `slots.DECISION_CONTRACT` today, which is what makes the encoder input invariant. That
would need re-checking if packet compilation changed.

## 5. Where the decision now stands

| | |
|---|---|
| **cost of wiring** | `plan_digest` changes for all 564 packets; the decisions change. **Nothing else.** |
| **benefit** | **+6.6194 points pooled** (34.6631% → 41.2825%), **+12.4861** on the many-decision half, **+0.0000** on the one-decision half |
| **robustness** | the gain is world-invariant (§2) and cannot be an exposure artefact (§3) |
| **what stays comparable** | the model, the encoder, the readout, the block, and every recorded `scores` |
| **what does not** | `plan_digest`, `slot_plan_digest` in each prediction, and the decisions themselves |

**The decision is unchanged — it is still the owner's, because it changes what the run's decoder does —
but it is now a decision with a measured cost of one digest and a measured benefit of 6.6194 points.**

## 6. Claim status

- **REAL:** §2's table and the +6.5603% / +6.6785% invariance, from the recorded six-run score table.
- **REAL:** §3's within-kind correlations, from the frozen course and the recorded scores.
- **REAL:** §4's comparison — 564 packets, 2,598 slots, zero changes to the encoder's input.
- **CORRECTED:** rounds 36 and 37's implication that wiring is expensive. It changes `plan_digest` and
  the decisions, and nothing else.
- **WITHDRAWN in round 39 and restored as tested here:** round 37's world-invariance claim. It was
  asserted, then untestable when the harness failed, and is now measured.
- **CLOSED:** the exposure question. The overall +0.1451 is a kind confound; within kind the
  correlation is near zero or negative.
- **NOT LICENSED:** that a run realises +6.6194 points. Every measurement in this record ran **offline
  against recorded scores**. §4 shows the wiring is cheap; it does not show the numbers a run would
  produce, because a run would also re-learn the block under a changed `plan_digest`.
