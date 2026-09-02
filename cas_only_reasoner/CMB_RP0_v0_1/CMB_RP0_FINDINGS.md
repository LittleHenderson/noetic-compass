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

---

## 13. The diagnostic worth keeping — ambiguity vs structure

*Recorded at the independent auditor's instruction: RGM-0.2 and CMB-RP0 measured the same
verifier against two different attacks and got opposite answers. Read them together or neither
means much.*

| | RGM-0.2 (admission) | CMB-RP0 (replay selection) |
|---|---|---|
| the attack | **one adaptive forgery**, built to sit above the bar and inside the margin (`0.9375`) | **132 cheap forgeries**, lev-1 mutations of real memories |
| what defeats it | **consistency** — the top cluster must agree with itself | **graph degree** — a one-item forgery has fewer edges |
| the verifier | near-miss authorized `119 → 0`, `358` true memories kept | ingests `5.67`; a degree count ingests `4.41` |
| verdict | **earns itself** | **adds nothing** |

**The two-tier verifier detects semantic contradiction. It does not detect structural anomaly.**

Where an attacker must make a forgery *agree* with the thing it impersonates, the verifier wins,
and it wins by mechanism rather than by threshold: a forgery that agreed would not be a forgery.
That is the property RGM-0.2 measured and the auditor confirmed by re-execution.

Where forgeries are cheap and numerous, they stop being ambiguous and start being *conspicuous* —
they sit in the graph differently from the memories they copy. Nothing in the verifier looks at
that, so it is beaten by a filter that counts edges and reads nothing else.

**The design consequence, stated plainly:** these are complementary defences, not competing
ones. A memory system facing both attacks needs the verifier for the adaptive case and a
structural check for the bulk case, and **neither substitutes for the other**. Nothing here
licenses building that; it is what the two measurements jointly imply, and it would need its own
preregistration and its own owner authorization.

**Why this was findable at all:** the structural weakness was visible only because the
mechanism-free competitor was registered *before* the run. `DEGREE_FILTER` exists because A2.5
disclosed a residual degree gap I could not remove, and the standing rule says a win by
mechanism M is uninterpretable until it beats the cheapest method without M. Without that arm,
CMB-RP0 would have reported the verifier beating `RANDOM` and `NO_REPLAY` and looked like a
modest success.

---

## 14. Independent audit — GLM, 2026-09-02: **PASS. The lane may close on this.**

Report: `tksCAS_audit_workspace/REFERENCE/AUDITS/CMB_RP0_GLM_AUDIT.md`, trail item 39.
Audit spend `$0`. GLM did not build CMB-RP0, so the independence requirement is satisfied.

**Verified live, not read:** the `$0.2039` spend inside the frozen `$0.40` cap, `PYTHONHASHSEED=0`
pinned on the instance, and **both code mirrors byte-identical** — GLM re-checked the hashes
itself rather than trusting the launcher's own mirror guard.

The auditor's summary of the safety result: *"The registered requirement was a poison-admission
gap > 1.0; measured −0.33. FAIL, emitted by the deterministic program, not prose."*

On the pre-flight catch: *"A5 was real and load-bearing… Without it, the bench would have printed
'balanced replay is immune to poisoning' — a false safety headline in the exact class the audit
program exists to catch."*

### The three findings

| # | finding | disposition |
|---|---|---|
| 1 | `make_audit_package.py` still emitted the **pre-launch** package (*"$0 spent, no result"*) after the run completed. | **FIXED.** The generator now detects a receipt and emits a close-out section: status words, failed conditions, content hash, device provenance, instance id, cost against ceiling, and termination proof. `AUDIT_PACKAGE.md` regenerated. |
| 2 | The 9-world power limitation stands; utility-side comparisons remain noise-limited. | **Agreed, already registered** (A3.5, before the run) and stated in §7. The ties with `RANDOM` and `DEGREE_FILTER` are absence of power, never equivalence. |
| 3 | *"The diagnostic worth keeping: the two-tier verifier blocks **ambiguity** but not **structure**. Both are now measured. Record them together."* | **RECORDED**, as §13 above and cross-referenced from `RGM02_FINDINGS.md` §10, so neither result can be read without the other. |

### Auditor's bottom line, preserved

> *"$0.2039, one claim-bearing run, falsifier as registered, every guard fired before or during
> it. This is what an honest negative looks like — close the lane on it."*

---

## 15. Lane status

```
CMB-RP0                  CLOSED on an audited negative
result                   TWO_TIER_GATE_EARNS_NOTHING / CMB_REPLAY_BEATS_NO_REPLAY_ONLY
promotion                NOT_PROMOTABLE  (6 of 8)
independent audit        GLM -- PASS
total spend              $0.2039
claims promoted          NONE
negatives deleted        NONE
```

Per the owner's standing `No automatic second repair`, **no successor round is started.** The
verifier keeps its RGM-0.2 result — where it earns itself — and gains a measured boundary: it is
a detector of semantic contradiction, not of structural anomaly.

---

## 16. QUALIFICATION 2026-09-02 — the `DEGREE_FILTER` headline is naming-specific

Found by the CMB-RP1 design attack, re-verified by me. Full record:
`cas_only_reasoner/CMB_RP1_v0_1/DESIGN_REVIEW_OUTCOME.md`.

### What STANDS

`TWO_TIER_GATE_EARNS_NOTHING`. The two-tier gap `−0.33`, positive in 3 of 9 worlds. The three
capability losses at **0 of 9** worlds at the permutation floor. `NOT_PROMOTABLE`, 6 of 8.
GLM's `PASS`. **No measured value changes.**

### What needs a note

§3 reports that `DEGREE_FILTER` — graph degree only — ingested `4.41` forgeries against the
verifier's `5.67`, and §13 builds on that to say the verifier "does not detect structural
anomaly".

**The link rule breaks `traj_sim` ties by ascending `memory_id`.** Ties are pervasive, because
only 13 similarity values are attainable. An id that sorts early is chosen as a neighbour by more
memories, so it ends up with *higher* degree.

Same world, same trajectories, same semantics — **only the id prefix changed:**

| forgery id prefix | forgery degree | real degree | separability |
|---|---|---|---|
| `poison_` *(what this bench used)* | 4.90 | 6.55 | 0.6811 |
| `zzzF` | 4.90 | 6.55 | 0.6811 |
| `m9F` | 4.90 | 6.55 | 0.6811 |
| **`aaaF`** | **7.03** | **6.48** | **0.5049** |

**An early-sorting prefix erases the signal and inverts the sign.**

**Corrected reading:** on this corpus, with forgeries named `poison_*`, a degree count excluded
more forgeries than the verifier. That is **corpus- and naming-specific**, not a general property
of one-item forgeries. The A2.4/A2.5 disclosure said the residual degree gap was *"a property of
the attack, not a bug"* — it is now measured to be **partly a property of the naming convention**,
which is worse than disclosed and is recorded here as such.

**This does not rescue the mechanism.** `CMB_AUTHORIZED` was still dominated by `CMB_RETRIEVED`
on both axes, and still lost to `SEMANTIC_DIVERSE`, `CLASS_BALANCED` and `CLASS_BALANCED_POOL` in
0 of 9 worlds. The qualification narrows one competitor's claim; it does not change the verdict.
