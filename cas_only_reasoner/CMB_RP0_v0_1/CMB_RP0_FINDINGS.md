# CMB-RP0 — RESULT: `TWO_TIER_GATE_EARNS_NOTHING` / `CMB_REPLAY_BEATS_NO_REPLAY_ONLY`

**Run:** 9 registered worlds (700–708), AWS `g4dn.xlarge` Tesla T4, `1220.38 s` harness wall,
`23.2 min` instance, **`$0.2039`** against a frozen `$0.40` ceiling.
**Hash:** `f2fbfd0c97df96f7c8ad159a39841f9f15fc62c0558b4a78bc4508bab934022e`
**Receipt:** `CMB_RP0_RECEIPT.json` · raw `CMB_RP0_RAW.json` · console `console.log`
**Instance:** `i-06b51636eec07f6e3` · torch `2.6.0+cu124` · CUDA `12.4` · `PYTHONHASHSEED=0`
**Builder:** Claude. **Auditor:** unnamed — 🔒 owner. **I do not audit this.**

```
SAFETY        TWO_TIER_GATE_EARNS_NOTHING
CAPABILITY    CMB_REPLAY_BEATS_NO_REPLAY_ONLY
PROMOTION     NOT_PROMOTABLE  -- 6 of the owner's 8 conditions FAIL
```

---

## 1. The headline, in one sentence

**The authorization tier — the entire subject of this bench — is dominated by the retrieval
tier it sits on top of, and both are beaten on forgetting by farthest-point semantic coverage
and beaten on poisoning by a filter that counts graph edges.**

## 2. The safety result: the second tier does nothing

The bench exists to test one claim: that a memory may be *retrieved* (shown) more freely than
it is *authorized* (allowed to influence training), because a forgery in a training batch is
written into the weights and cannot be taken back.

Registered requirement: `CMB_RETRIEVED` minus `CMB_AUTHORIZED` poison ingestion **> 1.0**
forgeries, with `POISON_MARGIN = 1.0` fixed before any retention number was seen.

| world | AUTHORIZED | RETRIEVED | gap |
|---|---|---|---|
| 700 | 5.00 | 4.00 | **−1.00** |
| 701 | 4.00 | 4.00 | 0.00 |
| 702 | 5.00 | 2.00 | **−3.00** |
| 703 | 5.00 | 5.00 | 0.00 |
| 704 | 6.00 | 5.00 | **−1.00** |
| 705 | 3.00 | 6.00 | +3.00 |
| 706 | 8.00 | 9.00 | +1.00 |
| 707 | 6.00 | 7.00 | +1.00 |
| 708 | 9.00 | 6.00 | **−3.00** |
| **mean** | **5.67** | **5.33** | **−0.33** |

Positive in **3 of 9** worlds. Exceeds the required 1.0 in **1 of 9**. The sign is
**−1, 0, −3, 0, −1, +3, +1, +1, −3** — that is noise around zero, not a small effect.

**The authorization tier admitted slightly MORE forgeries than the retrieval floor it filters.**
The registered §11 falsifier — implemented as `TWO_TIER_GATE_EARNS_NOTHING` after the design
review found it had never been coded — fired exactly as designed.

## 3. A mechanism-free competitor is safer than the mechanism

Poison ingested, ranked. Lower is safer.

| arm | poison ingested | forgetting (clean) | what it uses |
|---|---|---|---|
| `NO_REPLAY` | 0.00 | 0.9928 | nothing — replays nothing, forgets everything |
| `CLASS_BALANCED` | 0.00 | 0.0417 | **privileged poison-free pool — NOT a safety result** (A5) |
| **`DEGREE_FILTER`** | **4.41** | 0.1841 | **graph degree only. No query, no semantics, no CAS.** |
| `CMB_RETRIEVED` | 5.33 | 0.1388 | the verifier's first tier |
| `CMB_AUTHORIZED` | 5.67 | 0.1518 | **the mechanism under test** |
| `RANDOM` | 7.00 | 0.1621 | uniform sample |
| `ID_ORDER` | 7.11 | 0.2176 | store order — zero information |
| `SEMANTIC_DIVERSE` | 7.33 | **0.0365** | farthest-point coverage |
| `SEMANTIC_TO_NEW` | 8.78 | 0.4945 | documented straw man |
| `CLASS_BALANCED_POOL` | **16.00** | 0.0429 | label-balanced over the real pool |

**`DEGREE_FILTER` keeps out more forgeries than the two-tier verifier.** It counts edges. It
never reads the query, the semantics, the trajectory, or anything CAS.

This settles the limit registered as **A2.8 before the run**, and it settles it against the
mechanism. The disclosure said this bench could not separate *"the verifier keeps forgeries out
of training"* from *"my forgeries happen to be low-degree."* It did not have to: the degree
statistic did the job **better**.

## 4. The capability result

`CMB_AUTHORIZED` vs each arm, paired permutation on 9 worlds, `N_PERM = 10000`:

| vs | delta | sd | worlds + | p | verdict |
|---|---|---|---|---|---|
| `NO_REPLAY` | **+0.8410** | 0.0889 | 9/9 | 0.0038 | **WIN** |
| `SEMANTIC_TO_NEW` | **+0.3427** | 0.1132 | 9/9 | 0.0038 | **WIN** (straw man) |
| `ID_ORDER` | **+0.0658** | 0.0737 | 7/9 | 0.0458 | **WIN** |
| `DEGREE_FILTER` | +0.0323 | 0.1151 | 6/9 | 0.4148 | tie — underpowered |
| `RANDOM` | +0.0102 | 0.0706 | 6/9 | 0.7056 | tie — underpowered |
| `CMB_RETRIEVED` | −0.0130 | 0.0786 | 5/9 | 0.8438 | tie |
| `CLASS_BALANCED_POOL` | **−0.1089** | 0.0885 | **0/9** | 0.0038 | **LOSS** |
| `CLASS_BALANCED` | **−0.1101** | 0.0852 | **0/9** | 0.0038 | **LOSS** |
| `SEMANTIC_DIVERSE` | **−0.1154** | 0.0847 | **0/9** | 0.0038 | **LOSS** |

The three losses are **0 of 9 worlds** at `p = 0.0038`, which is the **floor** of a two-sided
sign-flip test at n=9 (`2/2^9 = 0.0039`). They are as decisive as nine worlds can make them.

## 5. The mechanism is dominated by its own first tier

Treating (forgetting, poison) as a two-objective frontier:

```
DEGREE_FILTER      0.1841 forget,  4.41 poison    on the frontier
CMB_RETRIEVED      0.1388 forget,  5.33 poison    on the frontier
SEMANTIC_DIVERSE   0.0365 forget,  7.33 poison    on the frontier
CMB_AUTHORIZED     0.1518 forget,  5.67 poison    DOMINATED by CMB_RETRIEVED
```

`CMB_RETRIEVED` is better than `CMB_AUTHORIZED` on **both** axes. **The authorization tier is
not on the frontier, and the thing that beats it is the tier directly beneath it.**

## 6. The owner's promotion law

```
FAIL  admits_less_poison_than_RETRIEVED      gap -0.33, needs > 1.0
FAIL  beats_RANDOM                            +0.0102, p 0.7056
FAIL  beats_SEMANTIC_DIVERSE                  -0.1154, p 0.0038  (a LOSS)
FAIL  beats_CLASS_BALANCED                    -0.1101, p 0.0038  (a LOSS)
FAIL  beats_DEGREE_FILTER                     +0.0323, p 0.4148
FAIL  clears_uncertainty_law
PASS  preserves_old_task                      0.8482 of its own peak, floor 0.80
PASS  learns_new_task                         0.9999, floor 0.80
```

**`NOT_PROMOTABLE`**, six of eight. The two that pass say the learner works — it keeps the old
task and learns the new one. Nothing about them favours the CMB; every arm that replays
anything passes them.

## 7. What nine worlds could and could not settle

The owner's blocking objection was that `MARGIN = 0.02` sat five times below a between-world sd
of `~0.108`. Measured here, the sd is `0.0706–0.1151` — **the estimate was right.**

The answer is not "nine worlds was enough" or "nine worlds was not enough". It is both:

- **Enough for the effects that exist.** All three losses fired at the permutation floor, 0/9
  worlds. Nine worlds detected them with room to spare.
- **Not enough for the ties.** `RANDOM` (+0.0102) and `DEGREE_FILTER` (+0.0323) are inside the
  noise. Per **A3.5, registered before the run**, those are **ABSENCE OF POWER, not evidence of
  equivalence**, and must never be reported as the mechanism "matching" them.

The capability question the bench was underpowered for turned out not to matter, because the
mechanism **lost** the comparisons that decide the outcome rather than tying them.

## 8. What the controls revealed that the mechanism did not

A real capability/safety tension exists among the cheap methods, and the CMB is not on it:

- **`SEMANTIC_DIVERSE`** forgets least (`0.0365`) and takes middling poison (`7.33`).
- **`DEGREE_FILTER`** takes least poison (`4.41`) and forgets more (`0.1841`).
- **`CLASS_BALANCED_POOL`** — the fair label-balanced arm added hours before launch — is
  near-best on forgetting (`0.0429`) and **by far the worst on poisoning (`16.00`)**.

That last one is a finding in its own right: **label-balanced replay is excellent at preserving
old tasks and highly vulnerable to label-forgery**, because a forgery carrying a wrong label
looks to it exactly like a member of that class. Had I not added this arm, the bench would have
had no fair balanced safety comparison at all — and the privileged `CLASS_BALANCED 0.00` row
would have read as "balanced replay is immune to poisoning."

## 9. Preconditions, all passed before any arm was scored

```
forgetting_exists          True    NO_REPLAY forgets 0.9928  (gate: > 0.10)
replay_helps               True    CLASS_BALANCED 0.0417     (gate: < 0.9928 - MARGIN)
id_order_not_equivalent    True    ID_ORDER 0.2176 vs CLASS_BALANCED 0.0417,
                                   CMB_AUTHORIZED 0.1518
```

The third is the A3.1 shortcut guard. Before the repair, `ID_ORDER` reproduced the
class-balanced set at **32/32 overlap**. Here it is clearly separated from both, so the
shortcut is closed **in the registered worlds**, not only in the dev checks.

## 10. Disclosed limits — all registered before the run

- **This tests the CMB as a replay SELECTOR.** Topic is 100% recoverable from the semantic
  vector (`480/480`) and the trajectory carries no topic information (`17/480`, chance). **This
  result says NOTHING about CAS geometry as a feature.** (A1.1)
- **Forgetting here is class-incremental naming loss, not representational loss.** Masked
  accuracy is `0.986–0.999` for every arm including `NO_REPLAY` at `0.9984`. The correct phrase
  is *"restores accuracy on earlier classes"*, never *"prevents representational forgetting"*.
  (A3.10)
- **Class coverage largely drives the ranking** (rank correlation `−0.9017` on dev), and the
  two-tier verifier is not a coverage mechanism. `CMB_AUTHORIZED` covers 19.0 classes against
  `SEMANTIC_DIVERSE`'s 22.0. (A3.10)
- **`CLASS_BALANCED`'s `0.00` poison is a construction privilege, not a safety property.** (A5)
- **The GPU was a governance choice, not a speed necessity** — a ~4.8k-parameter MLP. Peak VRAM
  `19.7 MB`. GPU usage here is **not** evidence of scale.
- **Nine worlds**, not the ≥20 an earlier audit prescribed for a related bench.

## 11. What is licensed

> On 9 independent synthetic memory worlds, a two-tier admission verifier used as a **replay
> selector** did **not** reduce forgery ingestion relative to its own retrieval tier
> (`−0.33` forgeries, positive in 3 of 9 worlds against a required `+1.0`), and lost on
> forgetting to farthest-point semantic coverage, to class-balanced replay, and to
> label-balanced replay over the same pool, each in **0 of 9 worlds** at the permutation floor.
> A filter using **graph degree alone** ingested fewer forgeries (`4.41`) than the verifier
> (`5.67`).

**NOT licensed:** any claim that CAS geometry helps replay selection; any claim about CAS
geometry as a feature; any production-memory claim; any claim that the mechanism "matches"
`RANDOM` or `DEGREE_FILTER` — those are underpowered ties, not equivalence; any promotion
whatsoever. **`NOT_PROMOTABLE` stands, and the standing `No claim promotion` prohibition
applies until an independent auditor — not Claude, who built this — has passed the design.**

## 12. What this does not disturb

**RGM-0.2's `ADMISSION_SAFETY_REPAIRED` stands unchanged**, and GLM reproduced it
byte-identically. That result is about **admission** — near-miss forgeries reaching the tier
that may influence reasoning, `119 → 0`, with `358` true memories still authorized. This
result is about **replay selection**, a different job the same verifier was asked to do here
for the first time.

The honest reading: **the two-tier verifier is good at the thing it was built for and adds
nothing as a replay selector.** Those are compatible, and only the second was tested here.
