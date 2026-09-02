# CMB-RP0 — Selective Replay and Catastrophic Forgetting · PREREGISTRATION v0.1 (FROZEN)

**Authorized by owner directive, 2026-09-02:** *"build item 5 and 6"*, unlocked because
RGM-0.2 returned `ADMISSION_SAFETY_REPAIRED`.
**Builder:** Claude. **Auditor:** a different model, named by the owner. I do not audit this.
**Parent:** `94a08bef` (RGM-0.2 result), branch `research/cmb-r1-rgm02-v1`.
**Status:** frozen before any held-out world is read.

```
item 5   selective replay selector
item 6   does CMB-selected replay reduce catastrophic forgetting better than
         random replay and semantic-only replay?
```

---

## 0. Conflict of interest, carried forward

I audited RGM-0/0.1, built RGM-0.2, and now build the bench that tests RGM-0.2's output. The
same two rules bind: every claim is quoted with the measurement that motivated it, and I emit
no status that rests on my own prior judgement. §0 of `RGM_02_PREREGISTRATION.md` applies here
unchanged.

## 1. Why replay is the case where admission safety actually matters

Retrieval is recoverable — a wrong memory shown to a user can be dismissed. **Replay is not.**
A forgery mixed into a training batch is written into the weights and cannot be un-learned by
noticing it later.

That is exactly the boundary items 1–2 drew:

```
RETRIEVED    may be SHOWN
AUTHORIZED   may influence REASONING or LEARNING   <- replay lives here
```

So this bench tests two things at once, and the second is the one nobody has measured:

1. **Capability** — does CMB-selected replay reduce forgetting more than random or
   semantic-only replay?
2. **Safety** — when forgeries are present, does the `AUTHORIZED` tier keep them out of the
   training set while semantic-only replay ingests them?

## 2. The learner and the task

Sequential classification over disjoint topic groups drawn from the CMB corpus.

```
features   semantic vector (SEM_DIM) ++ trajectory profile (10-dim operator histogram)
label      the memory's topic
tasks      T1, T2, T3 -- disjoint topic groups, trained IN SEQUENCE
model      small MLP, identical init per arm (same seed), identical optimiser and steps
```

Catastrophic forgetting needs a learner with enough capacity to overwrite. A linear model
barely forgets, so it would make every arm look equally good and prove nothing. **Neural
work, therefore AWS GPU** per the standing compute law; the local RTX 4070 is smoke/dev only
and records no measurement.

## 3. Replay arms

When training task `T_n`, each arm chooses `REPLAY_K` memories from tasks `T_1..T_{n-1}` to
mix into the batch. Everything else — init, optimiser, steps, batch size, `REPLAY_K` — is
identical across arms.

| Arm | Selection rule | Role |
|---|---|---|
| `NO_REPLAY` | nothing | lower bound |
| `RANDOM` | uniform from past memories | floor control |
| **`SEMANTIC_ONLY`** | top-K by semantic similarity to the new task | **MECHANISM-FREE BASELINE** |
| **`CMB_AUTHORIZED`** | top-K from RGM-0.2's `AUTHORIZED` tier | **the mechanism** |
| `CMB_RETRIEVED` | top-K from the `RETRIEVED` tier | ablation: does the AUTHORIZED gate matter? |
| `ORACLE_PAST_TASK` | true samples from the forgotten task | ceiling, **never a method** |

`CMB_AUTHORIZED` vs `SEMANTIC_ONLY` is the registered comparison. `CMB_AUTHORIZED` vs
`CMB_RETRIEVED` isolates the safety gate specifically.

## 4. The poisoning condition — the sharpest test in this bench

A second condition injects lev-1 **near-miss forgeries** into the corpus, using the identical
attack RGM-0.2 was measured against.

```
CLEAN      corpus as built
POISONED   + near-miss forgeries, 20 per attack, one shared provenance root
```

Registered measurements under `POISONED`:

```
poison_ingested          forgeries that entered the replay set
poison_rate              poison_ingested / REPLAY_K
retention_under_poison   how much accuracy survives when the replay set is contaminated
```

**This is the claim that would justify the whole two-tier design**, and it has never been
measured.

## 5. Registered predictions — written down BEFORE the run

Made from RGM-0.2's own numbers, so that a surprise is a surprise rather than a story fitted
afterwards.

1. **`CMB_AUTHORIZED` will roughly TIE `SEMANTIC_ONLY` on the CLEAN condition.** RGM-0.2
   measured plain semantic retrieval at 0.83–0.94 on three of five families, with the whole
   geometry stack adding only 0.03–0.15. Unless replay selection specifically needs
   composition or corroboration, there is no reason to expect a capability win.
2. **`CMB_AUTHORIZED` will BEAT `SEMANTIC_ONLY` decisively on the POISONED condition**, because
   `AUTHORIZED` excludes near-miss forgeries (measured: 0 authorised out of 119 admitted by
   RGM-0.1) and semantic similarity cannot tell a forgery from its original — a lev-1 forgery
   is *almost the same*, which is precisely what semantic similarity rewards.
3. **`CMB_RETRIEVED` will ingest poison at close to `SEMANTIC_ONLY`'s rate**, because forgeries
   do enter `RETRIEVED` (119/177/142 in RGM-0.2). If this fails to separate from
   `CMB_AUTHORIZED`, the two-tier design earns nothing here.

**If prediction 1 is wrong and CMB wins on clean data, that is a genuine surprise and must be
reported as one.**

## 6. Metrics

```
forgetting        acc(T1 | after T1) - acc(T1 | after T3)     lower is better
retention         acc(T1 | after T3) / acc(T1 | after T1)
final_avg_acc     mean accuracy over all tasks at the end
poison_ingested   forgeries in the replay set        POISONED condition only
poison_rate       poison_ingested / REPLAY_K
```

The world is the statistical unit. All arms are **paired**: identical worlds, identical task
splits, identical model init.

## 7. Status law

```
CMB_REPLAY_REDUCES_FORGETTING        CMB_AUTHORIZED beats SEMANTIC_ONLY and RANDOM on
                                     forgetting, on CLEAN, at MARGIN, in >=70% of worlds
CMB_REPLAY_TIES_SEMANTIC             beats RANDOM but ties SEMANTIC_ONLY  (the predicted outcome)
CMB_REPLAY_NO_BENEFIT                does not beat RANDOM
AUTHORIZATION_PREVENTS_POISONING     under POISONED, CMB_AUTHORIZED ingests materially less
                                     poison AND retains materially more than SEMANTIC_ONLY
AUTHORIZATION_NO_POISON_BENEFIT      it does not
STATUS_NOT_EMITTED                   a precondition or the mechanism-free gate failed
```

Capability and safety get **separate statuses**. A tie on capability with a win on safety is a
real and reportable result, not a failure — and on my own predictions it is the likely one.

```
MARGIN        = 0.02
WIN_FRACTION  = 0.70
REPLAY_K      = 32
```

## 8. Preconditions, checked before any spend

```
GATE_FORGETTING_EXISTS   NO_REPLAY must actually forget -- forgetting > 0.10 on CLEAN.
                         If the learner does not forget, no replay strategy can help and the
                         bench cannot answer its own question.
GATE_ORACLE_HELPS        ORACLE_PAST_TASK must beat NO_REPLAY. If replaying the true past does
                         not help, the instrument is broken.
GATE_MECHANISM_FREE      SEMANTIC_ONLY and RANDOM are both measured. No status is emitted
                         without them.
```

`GATE_FORGETTING_EXISTS` is the one that matters. A bench where nothing forgets would produce
five arms tied at zero and look like a clean null.

## 9. Compute

Neural work, so **AWS GPU**, fail closed on silent CPU fallback, local 4070 for smoke only.

```
HARD COST CEILING   $0.40
```

Raw results flushed to disk before receipt construction. `frozen_params` from an explicit
whitelist, never `dir()`.

## 10. Stop and audit

Stop after the deterministic report. Send to the owner's named third-party auditor. I built
RGM-0.2 and I built this; I do not audit either.

## 11. Falsifiers

- Nothing forgets → `STATUS_NOT_EMITTED`, the bench cannot answer its question.
- `ORACLE_PAST_TASK` does not beat `NO_REPLAY` → the instrument is broken.
- `CMB_AUTHORIZED` ≈ `CMB_RETRIEVED` on poison ingestion → the two-tier gate earns nothing in
  the one place it was designed to matter.
- `SEMANTIC_ONLY` matches `CMB_AUTHORIZED` even under poisoning → the entire admission
  apparatus is unnecessary for replay.

---

**Frozen. No held-out world has been read.**

---

# AMENDMENT A1 — measured before any build or spend. Supersedes §2, §3 and §5.

No held-out world has been read. Everything below was measured on dev worlds on the local
RTX 4070 (smoke/dev, records no measurement), and it changes the design in three ways.

## A1.1 The original task was BROKEN, in two independent ways

```
TOPIC from the SEMANTIC vector alone, nearest-centroid : 480/480 = 1.0000   (chance 0.0312)
TOPIC from the TRAJECTORY PROFILE alone               :  17/480 = 0.0354   (chance 0.0312)
```

1. **Topic is perfectly separable from the semantic vector**, so a model reaches ceiling
   immediately.
2. **The trajectory carries no topic information at all** — it is exactly at chance. So the
   CAS-specific part of the representation is irrelevant to this label by construction.

**Consequence for what this bench can claim:** it tests the CMB as a **replay SELECTOR**. It
does **not** test CAS geometry as a feature, and no result here may be read that way.

## A1.2 Forgetting is real — in fact total — and the arms ARE separable

Class-incremental over 3 disjoint topic groups, shared 32-way head, small MLP:

| strategy | forgetting | final accuracy | past classes covered |
|---|---|---|---|
| `NO_REPLAY` | **1.0000** | 0.3675 | — |
| `RANDOM` | **0.0964** | 0.8819 | 19 |
| `SEMANTIC → new task` | **0.6291** | 0.5769 | **4 of 22** |
| `ORACLE balanced` | **0.0509** | 0.9656 | 22 |

`GATE_FORGETTING_EXISTS` passes overwhelmingly, and `GATE_ORACLE_HELPS` passes. There is
genuine headroom between `NO_REPLAY` and the ceiling.

## A1.3 🟥 My registered mechanism-free baseline was a STRAW MAN. Corrected.

`SEMANTIC_ONLY` as specified — top-K by similarity **to the new task** — is **worse than
random** (0.6291 vs 0.0964). It covers only **4 of 22** past classes because it selects
near-duplicates of what is *already* being trained, which is precisely the material *least* at
risk of being forgotten.

Registering that as the baseline the mechanism must beat would have handed the mechanism a
free win. **The lesson from this project's own record is to register the STRONGEST
mechanism-free competitor, not a convenient one.** Revised arms:

| Arm | Selection rule | Role |
|---|---|---|
| `NO_REPLAY` | nothing | lower bound |
| **`RANDOM`** | uniform from past | **strong mechanism-free baseline (0.0964)** |
| **`SEMANTIC_DIVERSE`** | farthest-point coverage over past semantics | **strongest mechanism-free baseline** |
| `SEMANTIC_TO_NEW` | top-K similar to the new task | kept as a **documented straw man**, reported, never the bar |
| `CMB_AUTHORIZED` | RGM-0.2 `AUTHORIZED` tier | the mechanism |
| `CMB_RETRIEVED` | `RETRIEVED` tier | ablation: does the authorisation gate matter? |
| `ORACLE_BALANCED` | balanced coverage of past classes | ceiling, never a method |

## A1.4 Revised predictions — the headroom is NARROW and that is registered

**`RANDOM` already achieves 0.0964 against a ceiling of 0.0509.** Most of the available
benefit of replay is captured by picking uniformly at random.

1. **`CMB_AUTHORIZED` will struggle to beat `RANDOM`.** The entire band between the strong
   baseline and the ceiling is `0.0964 → 0.0509`, i.e. about **0.045** of forgetting. With
   `MARGIN = 0.02` the test is meaningful but tight, and a tie is the most likely capability
   outcome.
2. **Coverage, not similarity, is what replay needs.** Any arm that selects redundantly will
   lose. This predicts `SEMANTIC_TO_NEW` loses badly (measured: it does).
3. **The poisoning condition remains where a real difference is expected**, because it tests
   something no coverage heuristic addresses: keeping forgeries out of the training set.

**If `CMB_AUTHORIZED` beats `RANDOM` on clean data, that contradicts prediction 1 and is a
genuine surprise to be reported as one.**

## A1.5 Equal-volume rule — added

The `AUTHORIZED` tier **fails closed** and can be empty. An arm that replays fewer items is
not a better selector, it is a different experiment. So:

```
every arm replays EXACTLY REPLAY_K items, or the run records why it could not
if an arm supplies fewer than REPLAY_K, the shortfall is recorded as `underfilled`
an arm that is empty is reported as EQUIVALENT TO NO_REPLAY, never as a winner
```

`poison_ingested` must therefore be read alongside `underfilled` — **"kept poison out" and
"replayed nothing" are different results and are reported separately.**

---

# AMENDMENT A2 — construction validity (2026-09-02, before any measurement)

Written while building the harness, before any claim-bearing run. Every item below was found
by **measuring my own construction**, not by reasoning about it. Four of the five would have
produced an invalid result that still printed a clean status word.

## A2.1 — a forgery with missing fields is caught by bookkeeping, not by the mechanism

My first poison had `context = None`, `generic_profile = None`, and `links = []`, because I
built it after `assign_generic_geometry` and `_mk_memory` starts every memory with no links.

`coherence()` blends trajectory and context **only when both sides have a context**. So a
forgery with no context would have been scored on a different quantity from every real
memory. The verifier could then have excluded 100% of poison — and the win would have belonged
to a missing field, not to the two-tier rule.

**Fixed:** poison is built before geometry assignment, gets a real context vector (its
source's, plus noise), and real links. Checked: `0` poison items missing any field.

## A2.2 — the safety test was vacuous as first written

I defined the replay pool as `torch.cat(idx[:t])`, where `idx` is the training stream. The
training stream excludes poison. **So poison could never be replayed by any arm, and the
poisoning condition measured nothing at all.**

**Fixed:** the training stream and the replay pool are now separate. Training sees real
memories only. The pool is everything *stored* from earlier tasks, poison included — an item
sitting in memory, eligible for recall, that the model never legitimately learned. Checked:
`132 of 132` poison items reachable in the final pool, `0` in the training stream.

## A2.3 — a forgery is stored next to what it impersonates

Pool membership follows the topic the forgery **impersonates**, not the wrong label it
carries. Otherwise a forgery of a task-1 memory could sit in the task-2 pool, which is not
what an attack on a memory store looks like.

## A2.4 — degree gave the forgeries away, twice, in opposite directions

| construction | mean degree, poison | mean degree, real |
|---|---|---|
| forgery inherits its source's link set | **12.55** | 7.42 |
| forgery links out by the corpus rule only | **4.00** | 6.79 |
| whole graph rebuilt by the corpus rule | **4.89** | 6.67 |

First I made the forgeries **hubs**. Fixing that left them with no **incoming** edges — the
same giveaway, reversed. Both would have let a filter that counts edges do the verifier's job.

## A2.5 — the residual gap gets a competitor, not a patch

`4.89` against `6.67` does not go away. A forgery of one memory is close to that one memory,
so it earns fewer edges than a real memory sitting inside a cluster. **That is a property of
the attack, not a defect in the harness**, and it cannot be tuned out without faking the graph.

So it gets a competitor. **`DEGREE_FILTER`** is a new arm: keep the past items whose degree is
at or above the pool median, then sample at random. No query, no semantics, no CAS, no
verifier. It is added to the mechanism-free set and to the safety law:

> `AUTHORIZATION_PREVENTS_POISONING` now requires the verifier to ingest less poison than the
> best of `RANDOM`, `SEMANTIC_DIVERSE`, `SEMANTIC_TO_NEW`, **and `DEGREE_FILTER`**.

This follows the standing rule from CMB-P0: *a win by mechanism M is uninterpretable until it
beats the cheapest method without M.* There, three adversarial reviewers and a full held-out
run all missed a content leak that a one-line gate exposed. Here the cheapest competitor is
built in before the first measurement rather than after it.

## Arms, final

| arm | what it uses | role |
|---|---|---|
| `NO_REPLAY` | nothing | floor |
| `RANDOM` | uniform sample of the pool | strong mechanism-free baseline |
| `SEMANTIC_DIVERSE` | farthest-point coverage of the pool | strongest mechanism-free baseline |
| `SEMANTIC_TO_NEW` | nearest to the new task | documented straw man (A1.3), never the bar |
| `DEGREE_FILTER` | graph degree only | mechanism-free competitor on safety (A2.5) |
| `CMB_AUTHORIZED` | two-tier verifier, authorized tier | the thing under test |
| `CMB_RETRIEVED` | two-tier verifier, retrieved tier | isolates what the second tier adds |
| `ORACLE_BALANCED` | true labels | ceiling, never a method |

---

# AMENDMENT A2 (continued) — A2.6, A2.7, and a disclosed construct limit

## A2.6 — the verifier was right and my harness was wrong

First run of the finished harness: `CMB_AUTHORIZED` underfilled **64 of 64 slots**. The
authorized tier came back completely empty, so the arm was numerically identical to
`NO_REPLAY` (forgetting `0.9891` for both).

I expected the fail-closed behaviour disclosed in RGM-0.2 §6. **It was not that.** Counting
which condition fired gave: `0` absolute failures, `0` relative failures, `0` consistency
failures, mean authorized `1.0` per query, best coherence `1.0000` on every query.

The verifier was working perfectly. It was returning **the query's own source memory** — an
exact self-match — and I was then discarding that item for not being a past memory. I queried
the whole store with a new-task memory and got that new-task memory back.

**Fixed, and the fix is the more faithful construction:** at task `t` the memory store holds
tasks `0..t-1` and nothing else. The new task's items have not been stored yet. This is what a
continual-learning memory actually looks like, and it removes a hidden dependency where
propagation could reach new-task items that a downstream filter then removed.

This is the third time in this lane that I have diagnosed a mechanism failure that turned out
to be my own harness. Recorded for the auditor as a pattern, not a footnote.

## A2.7 — both the mechanism and the ceiling were being judged at starved settings

- One query per new-task topic supplied only **~19 of 32** replay slots, and the rest were
  padded by duplication. A selector judged at a setting that starves it proves nothing.
  Now: up to `QUERIES_PER = 8` examples per new-task topic, round-robin, stopping when the
  budget is full. Underfill is now `0` for every arm.
- `ORACLE_BALANCED` used a fixed per-class quota of `REPLAY_K // n_classes = 1`, filling only
  22 of 32 slots — and **`SEMANTIC_DIVERSE` beat it**. A ceiling that loses to a baseline is
  not a ceiling, and `oracle_helps` is a precondition gate. Now round-robin to a full budget.

## A2.8 — DISCLOSED CONSTRUCT LIMIT, stated before the run, not after

`DEGREE_FILTER` is strong on this corpus **because of the very gap A2.5 could not remove**.
A one-item forgery earns fewer edges than a real memory in a cluster, so a filter that counts
edges is well-suited to this particular attack.

**Therefore this bench cannot cleanly separate "the two-tier verifier keeps forgeries out of
training" from "the forgeries I built happen to be low-degree."** That is a limit of the
construction, and the correct response is to report it and keep the competitor in the safety
law — not to drop the competitor so the mechanism wins.

If the verifier beats `DEGREE_FILTER` the result is meaningful. If it does not, the honest
reading is that a graph statistic did the job, and the mechanism is not licensed here.

---

# AMENDMENT A3 — independent adversarial design review, NINE BLOCKING FIXES (2026-09-02)

A three-lens adversarial review (`will_it_forget`, `shortcut_and_fairness`, `stats_and_compute`;
7 agents) returned **BUILD WITH CHANGES / DO NOT LAUNCH**. I re-verified the decisive items
myself with the real code before accepting them. **All nine are real. All nine are fixed.**
None of them came from me.

## A3.1 — a ZERO-INFORMATION rule reproduced my registered ceiling EXACTLY

`build_corpus` sets `topic = i % 32` and `memory_id = "m%04d" % i`, and I used
`mids = sorted(memories)`. **Sorting the ids IS a class round-robin.** My own verification, pure
index arithmetic, no seeds involved:

```
CLEAN t=1   CLASS_BALANCED 11 classes | ID_ORDER 11 classes | set overlap 32/32
CLEAN t=2   CLASS_BALANCED 22 classes | ID_ORDER 22 classes | set overlap 32/32
```

"Take the 32 lowest-index past memories" — no query, no labels, no semantics, no graph, no CAS —
selected the **identical 32-item set** as the arm I had registered as *"ceiling, never a method"*.
The poison source draw and the CMB query draw took the lowest ids too, identically in every world.

**This is the FOURTH label-free shortcut in this bench family** (CMB-P0 C1, CMB-P0 A3.2 content
leak, CMB-P2 two-hop, now this). It is the same signature that closed the phase lane. I did not
find it; the review did.

**Fixed:** store order, poison source draw, CMB query draw and the task split are all drawn from
the world's own RNG; `CLASS_BALANCED` picks a **random** member of each class rather than the
first in order. Re-verified: overlap **2/32** and **0/32** against chance **1.9** and **0.9**.
`ID_ORDER` is registered as a **permanent arm**, and a new precondition
`id_order_not_equivalent` emits `STATUS_NOT_EMITTED` if it ever again reaches the class-balanced
arm or the mechanism.

**`ORACLE_BALANCED` is RENAMED `CLASS_BALANCED`.** It uses only labels already stored on the
memories, so it is a **deployable one-line method, not an oracle**, and the mechanism must beat it.

## A3.2 — the safety headline could fire on an ablation showing ZERO separation

`best_base` excluded `CMB_RETRIEVED`, and nothing checked the gap between the two tiers. The
review measured both tiers ingesting **identical** poison (2.75 vs 2.75; 3.67 vs 3.67) with
`AUTHORIZATION_PREVENTS_POISONING` still firing. Section 11 registers exactly this as a
falsifier and it was **implemented nowhere**.

The sentence that would have been carried forward — *"the authorization tier keeps forgeries out
of training"* — when the numbers actually said *"the retrieval floor did the work and the second
tier, the entire subject of this bench, added nothing."*

**Fixed:** `POISON_MARGIN = 1.0` forgeries, **registered before seeing any retention number**,
and a new executable status `TWO_TIER_GATE_EARNS_NOTHING` that fires first.

## A3.3 — the ceiling arm was the MOST POISONED arm, by construction

Poison sits in the pool by the topic it impersonates but carries a **wrong** label, so eleven
"classes" appeared whose only members were forgeries. Measured: `CLASS_BALANCED` ingested
**16 of 32** forgeries, more than any other arm — and my own dev run reproduced exactly 16.
**Fixed:** built from the true past training indices only. Re-verified: **0 of 32**.

## A3.4 — `RANDOM` drew the SAME 32 items in every world

`manual_seed(1000 * t + hash(arm) % 100000)` had **no world term**, and the pools are pure topic
arithmetic identical across worlds. So the strongest mechanism-free baseline got **one** draw
copied into all twelve worlds, and the win-fraction test would have treated twelve reuses of one
draw as twelve independent draws — precisely how a spurious 12/12 is manufactured.
**Fixed:** the world is in the seed, plus `N_DRAWS = 5` draws per stochastic arm. Re-verified:
draws differ across worlds, 5 of 5 distinct within a world.

## A3.5 — the margin was about five times below the noise

Between-world sd on the paired delta is `0.1077-0.1105`, with the sign flipping between worlds;
within-world seed sd is only `0.0066-0.0328`. **The variance is between worlds, not between
seeds.** `MARGIN = 0.02`; the win-fraction rule had a floor near `0.076` that more worlds cannot
lower; registered headroom (A1.4) is `0.045`.

**Fixed and DISCLOSED:** the test is now a paired permutation (`N_PERM = 10000`); win fraction is
descriptive only; per-world sd goes in the receipt; seeds cut to 2 because a third buys almost
nothing. **Registered up front: no affordable world count resolves the capability question, so a
tie there is ABSENCE OF POWER, not evidence of equivalence.** The claim rests on the safety half,
which is a count.

## A3.6 — the frozen status law and the executable status law DISAGREED

Section 7 said `NO_BENEFIT` = "does not beat RANDOM"; the code said "does not beat NO_REPLAY".
The two documents would emit **different words from the same result**, and the code's word would
have printed over a result where the mechanism loses to `RANDOM`, `SEMANTIC_DIVERSE` and
`DEGREE_FILTER`. Section 7 also named `SEMANTIC_ONLY`, an arm that no longer exists, and
`GATE_MECHANISM_FREE` appeared **zero** times in the harness.

**Fixed:** one law, the one the code executes. `CMB_REPLAY_TIES_SEMANTIC` renamed
`CMB_REPLAY_BEATS_NO_REPLAY_ONLY`. The capability status must beat **every** mechanism-free arm
measured, not a hand-picked pair. The `auth_empty` guard now covers capability as well as safety.

## A3.7 — the run was not reproducible and the receipt claimed it was

`hash(arm)` is randomised per process — three runs gave seeds `12308`, `27607`, `95831` — and
`PYTHONHASHSEED` appeared nowhere in the launcher's user-data. **Fixed:** fixed per-arm integers,
plus `PYTHONHASHSEED=0` exported in user-data and recorded in the receipt.

## A3.8 — GOVERNANCE: I raised the executable ceiling above the frozen one

Section 14 freezes `$0.40`. I had set `HARD_CAP_USD = 0.75` with an 80-minute watchdog worth
`$0.70`. Under the standing rule that approval must be **executable** rather than
prose-interpretable, the launcher's number is the real ceiling — so I had silently raised the
owner's cap by 88%. **That is my error and it is the one I like least.**
**Fixed:** `HARD_CAP_USD = 0.40`, `WATCHDOG_MIN = 45`, `IN_INSTANCE_HARD_MIN = 40`.

## A3.9 — twelve worlds shared ONE task split

`topics[i::3]` over sorted topics is the constant `(i mod 32) mod 3` in every world; the worlds
differed only in semantic centroids and trajectories. **Fixed:** drawn per world, re-verified to
differ across worlds.

## A3.10 — what forgetting here actually IS, disclosed before the run

`GATE_FORGETTING_EXISTS` passes by roughly ten times (four independent measurements: `1.0000`,
`0.9976`, `0.9897`, `0.9911`). But **task-masked forgetting is `0.0024`** — the representation is
not destroyed; the shared softmax stops naming classes it has not seen recently. This is a
legitimate class-incremental protocol, so it is a **disclosure, not a gate**.

Two consequences, both registered:

1. Section 2's justification is **falsified by measurement**. I wrote that a linear model
   "barely forgets, so every arm would look equally good". A linear model forgets `0.8885` and
   the arms stay separable. **That was my stated reason for needing a neural learner, and
   therefore for needing a GPU. Withdrawn.**
2. Across 24 arm-world cells, the rank correlation between **distinct past classes covered** and
   forgetting is **-0.9017**. Coverage sets the ranking almost entirely, and the two-tier
   verifier is not a coverage mechanism. `past_classes_covered` is now logged per arm per world,
   and the receipt states that the capability comparison largely measures **coverage**.

Claims must say *"restores accuracy on earlier classes"*, never *"prevents representational
forgetting"*.

## Recorded, NOT fixed here

`V2.is_correct` reads `.get("answer")` while `_mk_memory` writes `"answer_field"`, so it returns
`False` for a known-correct memory. **Neither RGM-0.2 nor CMB-RP0 calls it, so it is latent** —
and it lives in the module RGM-0.2's committed receipt was produced with. Changing that module
mid-bench is the auditor's call, not mine. Recorded here so it is not rediscovered as new.

## Status

Nine blocking items, nine fixes, four re-verified by my own measurement (A3.1, A3.3, A3.4,
A3.9). **Still NOT LAUNCHED.**

---

# A3 ADDENDUM — run constants, frozen (were absent from this document; B8)

```
worlds            700-708  (9), asserted disjoint from RGM-0.1 (0-19) and RGM-0.2 (500-511)
seeds             0, 1          per world
replay draws      5             per stochastic arm per world (RANDOM, DEGREE_FILTER)
tasks             3             topic-to-task split DRAWN PER WORLD
learner           42 -> 64 -> 32 MLP, shared 32-way softmax head, ~4.8k parameters
optimiser         Adam, lr 1e-3, batch 64, 300 steps per task
REPLAY_K          32            equal-volume rule; underfill recorded
QUERIES_PER       8             CMB query budget per new-task topic
POISON            6 per past topic, lev-1 trajectory, wrong label, real context and links
MARGIN            0.02          capability; paired permutation, N_PERM 10000
POISON_MARGIN     1.0           forgeries; registered BEFORE seeing retention
HARD COST CEILING $0.40         launcher: HARD_CAP_USD 0.40, in-instance 40 min, watchdog 45 min
```

Cost arithmetic, from measurement rather than estimate: `146.3 s` per world pair on the RTX 4070
(`64.4` CLEAN + `81.8` POISONED); `x1.4` for the T4 host's slower vCPU on Python-bound work =
`205 s` per world. Nine worlds = `35.7 min` billable including ~5 min boot and torch install =
**`$0.313`**, sitting `4.3 min` inside the in-instance timer. Ten worlds would leave `0.9 min`
of margin and twelve would exceed the frozen ceiling.

**Honest note on what the GPU is doing.** The learner is a ~4.8k-parameter MLP. The GPU performs
a fraction of a second of arithmetic across the entire run; the instance is rented for Python
interpreter overhead, not for compute. **GPU usage here is not evidence of scale**, and the
receipt says so. Whether this workload falls inside the GPU-first law at all is an owner
question, not mine — RGM-0.2's own receipt set the precedent in the other direction
(`"device": "cpu"`, `$0`, 428 s).

---

# AMENDMENT A4 — OWNER AUTHORIZED LAUNCH (2026-09-02), written BEFORE the run

Owner message: *"GLM IS AUDITING CMB-P0/P1/P2 and RGM-0.2. AND YES LAUNCH"*.

This resolves the conflict recorded in `OWNER_RULING_2026_09_02_PRELAUNCH.md` section 1 in
favour of the opening instruction. **The run is authorized.** Committed before launch so the
ordering is checkable in git rather than asserted.

## A4.1 — auditor assignments

```
CMB-P0 / CMB-P1 / CMB-P2 / RGM-0.2     GLM        <- NAMED, unblocked
CMB-RP0                                 UNNAMED    <- still owed
```

The owner's earlier ordering (*"After audit passes: ONE AWS GPU DEVELOPMENT RUN"*) is
superseded for the RUN only. It is **not** superseded for promotion. The standing prohibition
`No claim promotion` remains in force, so:

> **This is a DEVELOPMENT RUN. It produces raw measurements. No claim may be promoted from it
> until an independent auditor — not Claude, who built it — has passed the design.**

## A4.2 — the effect threshold at launch is PROVISIONAL, and why that is safe

`MARGIN = 0.02` is unchanged at launch and is **known to be roughly five times below the
between-world standard deviation** (`0.1077-0.1105`). The owner raised exactly this. The
calibration measuring a defensible threshold is still in flight on dev worlds.

Launching now does not bake in the wrong threshold, because **the status is a pure function of
the per-world measurements**, and those are saved: `CMB_RP0_RAW.json` is flushed after every
world and the full `clean` / `poisoned` arrays are embedded in the receipt. `summarize()` can
therefore be re-applied to the saved data at **`$0`**, with no GPU and no re-run.

**REGISTERED PROCEDURE, binding, so this cannot become post-hoc tuning:**

1. The threshold may be revised **at most once**.
2. The revision must be derived **only from dev worlds `750+`**. Registered worlds `700-708`
   may **never** inform the threshold.
3. The calibration method is fixed in advance: the null is the paired delta between **two
   independent draws of the same stochastic arm**, which is pure noise with the same variance
   structure as the real comparison; the candidate margin is the 95th percentile of that
   null's `|delta|`.
4. Any recomputed status must be reported **alongside** the launch-time status, with both
   margin values stated. Neither replaces the other silently.
5. If the revised threshold changes a status word, **both words are recorded** and the change
   is flagged for the auditor.

## A4.3 — what this run can and cannot settle

Registered in advance, so a null result is not later reinterpreted as a win:

- **CAN settle:** the safety half. Poison ingestion is a **count**, and the two-tier gap
  (`CMB_RETRIEVED` minus `CMB_AUTHORIZED`) is the measurement the whole bench exists for. A
  one-world dev signal already put that gap at `-1.0` — the authorized tier admitting **more**
  forgeries, not fewer — so `TWO_TIER_GATE_EARNS_NOTHING` is a live outcome.
- **CANNOT settle:** the capability half. Between-world sd `~0.108` against registered
  headroom `0.045` means nine worlds cannot resolve the forgetting comparison. **A capability
  tie is ABSENCE OF POWER, not evidence of equivalence**, and must never be reported as one.

## A4.4 — compute law, as ruled

```
No experimental workload on the owner's local CPU.
One remote AWS GPU.
All scalable learning tensors on CUDA.
Fail closed on silent numerical CPU fallback.
Remote CPU host: orchestration, file I/O, hashing, JSON, monitoring, shutdown only.
```

Enforced: `require_cuda()` raises `GPU_REQUIRED` and **no CPU fallback branch exists in the
harness**. The launcher additionally aborts before any harness work if CUDA is unavailable on
the instance. Binding cost stop is the in-instance timer at 40 min = **`$0.351`**, inside the
frozen `$0.40`.

---

# AMENDMENT A5 — the A3.3 repair handed one arm a SAFETY ORACLE (2026-09-02, pre-launch)

Found in the end-to-end pre-flight on dev worlds 750-751, before spending anything.

## What the pre-flight showed

```
arm                  poison ingested (dev worlds 750-751, POISONED)
CLASS_BALANCED                 0.00      <-- every other arm: 4.6 to 9.5
SEMANTIC_DIVERSE               9.50
RANDOM                         7.90
DEGREE_FILTER                  6.30
CMB_RETRIEVED                  6.50
CMB_AUTHORIZED                 6.00
```

**Zero is not a property of class-balanced replay. It is a privilege I handed the arm.**

## Why it happened

The A3.3 repair moved `CLASS_BALANCED` off the replay pool and onto the true past
**training stream**, to stop the "ceiling" arm ingesting 16 of 32 forgeries. The training
stream excludes forgeries by construction. So the repair silently gave that one arm a
**poison-free pool that no other arm gets** — a safety oracle.

A deployable label-balanced replay method cannot tell a forgery from a memory. It reads the
label stored on each item and balances. Forgeries carry a *wrong* label, so a real
label-balanced method **would** be fooled — which is exactly what the reviewer's original
`16/32` measurement was showing. That number was a **finding**, not a defect.

**The repair for A3.3 manufactured the next problem.** That is how three of the four earlier
shortcuts in this lane were born, and it is the specific failure mode the design review warned
to expect a fifth instance of.

## Scope of the damage, measured honestly

The **gating conditions were not corrupted**, and this is worth stating precisely rather than
overstating the error:

- The capability status compares arms on **CLEAN** worlds only, where there is no poison, and
  in CLEAN worlds the training stream and the replay pool are the **identical index set**. So
  the owner's `beats_CLASS_BALANCED` condition was always a fair comparison.
- `CLASS_BALANCED` was never in `MECHANISM_FREE`, so its zero never gated the safety status.

What *was* wrong is the **reporting**: the POISONED table carried a row reading
`CLASS_BALANCED 0.00 poison`, which an auditor would reasonably read as *"simple class-balanced
replay is immune to poisoning."* That is false, and it is false in the direction that makes the
mechanism look worse than a competitor it was never actually beaten by.

## The fix — two arms, because one cannot honestly play both roles

| arm | pool | role |
|---|---|---|
| `CLASS_BALANCED` | true past **training stream** (poison-free) | **capability** competitor only, per the owner's ruling. Its POISONED row is **not** a safety result. |
| `CLASS_BALANCED_POOL` | the **same replay pool as every other arm**, balanced on the label **stored** on each memory | the **fair safety competitor**. Forgeries carry a wrong label, are eligible, and it gets fooled — as a deployable method would. |

`CLASS_BALANCED_POOL` is added to `MECHANISM_FREE`, so it now gates **both** the safety status
and the builder's capability status. The owner's `REQUIRED_BEAT` is unchanged — it names
`CLASS_BALANCED`, and that comparison was and remains fair.

Cost: two extra training runs per world-condition, roughly 14 s per world.

## Registered consequence

The bench now answers the owner's question — *"can CMB select a small replay set that preserves
old learning better than simple balanced replay, while admitting fewer forged memories?"* —
against a label-balanced competitor that is **exposed to the same forgeries the mechanism is**.
Without this arm, the safety half had no fair balanced comparison at all.
