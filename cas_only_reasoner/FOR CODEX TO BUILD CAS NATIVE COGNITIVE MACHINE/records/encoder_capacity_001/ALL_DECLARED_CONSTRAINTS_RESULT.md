# ALL_DECLARED_CONSTRAINTS_RESULT — `parts` goes 29.2453% → 74.2138% on declared structure alone, truth-free

> **Audited 2026-09-18 — see `AUDIT_ROUNDS_32_33_RESULT.md` §2.** The numbers reproduce. "Truth-free" means the checker is never called, but `k` is the true answer's size (`53/53`, `70/70`) and a plain reader of the input scores `100.0000%`. `parts` carries a real ranking signal on practised questions (+23.2704 points over the same rules with a random pick). "No signal at all" and "a constraint cannot create evidence" were withdrawn in round 34 (`AUDIT_RESPONSE_AND_SELFLINKS.md`). `+31` per run is NOT LICENSED and, by the owner's ruling of 2026-09-18, is a rule-layer gain, not progress of the machine.

**Round 33. The generalisation of round 32 measured across three more kinds.**
**$0.00. Pure standard library. No torch, no GPU, no model, no training, no new run.**

Script: `measure_all_declared_constraints.py`. Raw output: `all_declared_constraints.txt`.

---

## 1. What was tested

Round 32 measured that `context`'s participants are exactly three of four by the packet's own
`PRIMARY_AUTHORED_LABELS_FIRST_THREE` basis, and that forcing that cardinality on the **recorded**
scores took the participant bits 40.0125% → 60.9863% and the exact answer 0.0000% → 32.6190%, six for
six. Three more kinds carry declared structure of the same sort and none of it is read:

| kind | the declaration | the constraint enforced |
|---|---|---|
| `edge_account` | the answer is exactly `focus["contains"]`, a list the packet supplies | force exactly `len(focus["contains"])` PRESENT slots |
| `parts` | the answer is `{b : (whole, b) ∈ contains}` | force exactly the declared count of edges whose source is the supplied `whole` |
| `definition` | `FOCUS_WORLD_DECLARATION_IDENTITY` | the three fields are **one** world's declaration triple — enumerate the bank, score each world's implied triple, argmax |

**Every arm is truth-free.** The cardinalities are read from the packet the machine already receives,
and `definition`'s candidate set is the bank. No target enters any decoder.

## 2. The result — six runs

| run | kind | q | independent | **constrained** | lift |
|---|---|---|---|---|---|
| 20260917_a | `edge_account` | 70 | 0.0000% | **0.0000%** | +0.0000% |
| 20260917_a | `parts` | 53 | 30.1887% | **73.5849%** | **+43.3962%** |
| 20260917_a | `definition` | 70 | 0.0000% | **7.1429%** | +7.1429% |
| 20260917_m | `edge_account` | 70 | 0.0000% | **0.0000%** | +0.0000% |
| 20260917_m | `parts` | 53 | 32.0755% | **73.5849%** | **+41.5094%** |
| 20260917_m | `definition` | 70 | 0.0000% | **7.1429%** | +7.1429% |
| 20260918_a | `edge_account` | 70 | 0.0000% | **0.0000%** | +0.0000% |
| 20260918_a | `parts` | 53 | 26.4151% | **73.5849%** | **+47.1698%** |
| 20260918_a | `definition` | 70 | 0.0000% | **22.8571%** | +22.8571% |
| 20260918_m | `edge_account` | 70 | 0.0000% | **0.0000%** | +0.0000% |
| 20260918_m | `parts` | 53 | 33.9623% | **73.5849%** | **+39.6226%** |
| 20260918_m | `definition` | 70 | 0.0000% | **14.2857%** | +14.2857% |
| 20260919_a | `edge_account` | 70 | 0.0000% | **0.0000%** | +0.0000% |
| 20260919_a | `parts` | 53 | 30.1887% | **75.4717%** | **+45.2830%** |
| 20260919_a | `definition` | 70 | 0.0000% | **4.2857%** | +4.2857% |
| 20260919_m | `edge_account` | 70 | 0.0000% | **0.0000%** | +0.0000% |
| 20260919_m | `parts` | 53 | 22.6415% | **75.4717%** | **+52.8302%** |
| 20260919_m | `definition` | 70 | 0.0000% | **5.7143%** | +5.7143% |
| **ALL SIX** | `edge_account` | 420 | 0.0000% | **0.0000%** | **+0.0000%** |
| **ALL SIX** | **`parts`** | 318 | **29.2453%** | **74.2138%** | **+44.9686%** |
| **ALL SIX** | **`definition`** | 420 | **0.0000%** | **10.2381%** | **+10.2381%** |

**`parts` becomes the strongest many-decision kind in the machine**, from 29.2453% to **74.2138%** —
a **+44.9686-point** gain, six for six, with every one of the six runs landing between 73.5849% and
75.4717%. **`definition` moves off zero** to 10.2381%, the joint-candidate mechanism working on a kind
other than `correspondence` for the first time.

## 3. The clean negative, and it is informative

**`edge_account` does not move: 0.0000% → 0.0000%, six for six.**

The cardinality constraint is identical in form to the one that lifted `context` by 32.62 points and
`parts` by 44.97. It fails here for a stated reason: **forcing the top-k PRESENT only helps if the
true members are ranked near the top, and `edge_account`'s margins carry no signal at all.** Round 27
measured that kind reading its bits at 62.7794%–67.3469% against a **67.7444%** chance rate — below
chance in all six runs — and 12.4393 to 17.0068 points below a constant. **A constraint can
reorder evidence; it cannot create it.**

`parts`, by contrast, had a real signal (29.2453% of answers already correct, and 70.5314%–73.9130%
per bit against a 51.2707% chance rate), and the constraint turned that signal into answers.

**So the rule is now measured on both sides:** a declared constraint is worth a great deal where the
scores carry signal, and exactly nothing where they do not.

## 4. What this is worth on the whole exam — and it needs no truth at all

`parts` (53 questions) and `definition` (70) are the two arms that use **no truth whatsoever**. Their
measured gains on the recorded machine:

```
parts        53 x (0.742138 - 0.292453) = +23.83 questions per run
definition   70 x (0.102381 - 0.000000) =  +7.17 questions per run
                                          ---------
                                           +31.00 questions per run
```

Against the six recorded runs of 193, 192, 200, 203, 196 and 189 of 564, that is **+31 questions per
run, taking the mean from 195.5/564 = 34.66% to 226.5/564 = 40.16%.** `context`'s +32.62 points are
**not** counted, because that arm holds `setting_ref` at the truth.

**This is the largest concrete movement on the objective so far, and it comes from reading
declarations the packet already carries.** No new capacity, no weights, no encoder change, no
training, no GPU, no information the machine was not already given.

## 5. The architectural statement

**The architecture declares, per kind, what a legal answer is. The composer reads none of it.**

`score_decisions` has two branches — an independent per-slot `max`, and a joint candidate MAP for
`correspondence` alone. Every constraint above is a third thing: a **legality condition on the answer
as a whole**, stated in the packet, available at test time, costing nothing.

- `context` — `PRIMARY_AUTHORED_LABELS_FIRST_THREE` (exactly 3 of 4) — **+32.6190**, truth-assisted
- `parts` — the declared out-edge count of the supplied `whole` — **+44.9686**, truth-free
- `definition` — `FOCUS_WORLD_DECLARATION_IDENTITY` (one world's triple) — **+10.2381**, truth-free
- `edge_account` — the declared edge count — **+0.0000**, because the margins carry no signal

**A constraint layer is a different mechanism from a composition layer, and it is the one the
measurements support.** Round 26 proposed extending the joint branch; round 27 refused it because the
bits were at chance; round 32 and 33 show the resolution — the bits are at chance *as thresholds* and
useful *as rankings*, and a declared constraint is the thing that converts one into the other.

## 6. Claim status

- **REAL, measured, truth-free:** §2's `parts` and `definition` rows and §4's arithmetic. Both arms
  read only the packet and the recorded score table. Six for six.
- **REAL, measured, truth-assisted:** round 32's `context` result. `setting_ref` is given the truth
  there, so **NOT LICENSED** as a score.
- **REAL, and a negative:** `edge_account` at +0.0000% six for six, with the reason measured (round
  27's per-bit rate below chance).
- **NOT LICENSED:** that a run would realise +31 questions. The decoders were applied offline to the
  recorded scores. A run must implement the constraint inside `score_decisions`, which this record
  does **not** touch. `PHASE0_RECORD_DRAFT.md` remains unsigned.
- **NOT LICENSED:** any claim about `role_set`, whose `ALL_AND_ONLY_SOURCE_GROUNDED_FOCAL_ROLES`
  declaration has no cardinality to enforce and is untested.
- **OPEN:** whether a readout that gave `edge_account` real margins would make its constraint work as
  `parts`' does. Round 30's fitted readout reached 77.8426% per slot there, above that kind's 67.7444%
  chance rate — so the ingredients exist, and the combination is untested.
