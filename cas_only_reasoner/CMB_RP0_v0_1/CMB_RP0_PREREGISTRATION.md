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
