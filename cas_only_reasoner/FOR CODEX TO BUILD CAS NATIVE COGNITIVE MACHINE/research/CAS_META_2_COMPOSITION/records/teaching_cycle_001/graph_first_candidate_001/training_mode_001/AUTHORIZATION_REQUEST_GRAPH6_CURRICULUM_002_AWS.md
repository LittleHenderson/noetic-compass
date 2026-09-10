# GRAPH6_CURRICULUM_002 — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** One combined job, one package, one total
budget. Nothing has been reserved, registered, or launched. The specialist is
**not** moved into child-call integration.

## What this job tests

Your hypothesis, tested rather than assumed: *the learner needs more varied
practice that separates the relationship from familiar names, layouts and answer
patterns.* One job runs **control** (repeat the existing lessons) against
**varied** (the new relationship lessons) at equal budget, with the same
architecture, the same frozen encoder, the same CAS framing, and matched starting
weights within each seed.

## Informed by the read-only error review (existing records only)

`tools/graph6_curriculum_error_review.py` → `CURRICULUM_002_ERROR_REVIEW.json`
(sha256 `e317c0c74b0dbad59b35aed9b29e09f50f5aa93096a8516de2d087e6115cbc04`).
Headline numbers re-derived independently and matching:

* Pooled `LIST_PARTS` wrongs **72 before → 67 after**; `missing_part` **36→34**
  (largest class in every cell), `extra_part` **15→22**, `mixed` 3→0,
  `wrong_whole` 18→11, padding 0.
* `FIND_SHARED_PART` correct **30→44**, but `chose_none` **0→0** while `none` is
  the answer in 21/30 panel cases.
* `REACHED_VIA` correct **25→39**; `said_direct` **30→11**.
* Correct option present **361/361** wrong cases; **no** lesson or panel case ever
  had three equal-length `LIST_PARTS` options; 139 wrong choices split 69
  longest / 70 shortest.
* UNAVAILABLE: practice predicted strings (no practice error can be classified),
  per-option scores, optimizer state, trained weights, per-case timings.

## What the varied curriculum does (identity `f3e56f29…`)

30 records, 10 per operation, same schedule shape as the control:
every `LIST_PARTS` lesson carries a missing-part **and** a foreign-part option,
**7 of 10** have all three options the same length, and the correct list is never
the unique longest or shortest; `FIND_SHARED_PART` **4/10** offer `none` and
**4/10** answer `none` with equal-length options; `REACHED_VIA` answers
**4 direct / 3 via / 3 absent**; 8 of 10 families use labels absent from teaching;
5 families reorder connections; 4 families rewire a connection. Answer contract,
^6 module, encoder, parameter scope and scoring semantics are unchanged.

## One finding you must approve knowingly: the untouched panel was rebuilt (twice)

**Correction first.** A first draft of this panel proposed twelve "new shapes";
checked with a label-invariant graph calculation they reduced to **two** distinct
directed connection patterns (shapes 1,3,4,6,8,9,10,11,12 shared one; 2,5,7 the
other). Renaming objects is not novelty. The generator was rebuilt to
**enumerate** arrangements and to prove distinctness.

**The supply finding, narrowed.** How much the FROZEN generator supplies depends
on the exclusion scope:

| Scope | Families searched | every record unused | ≥1 selected case unused | all three selected cases unused |
| --- | --- | --- | --- | --- |
| teaching set only | 2,831 | 409 | 2,664 | 751 |
| teaching set **and the examined panel** | 2,831 | **0** | 1,756 | 38 |

Eligible questions per operation in the untouched scope: `LIST_PARTS` **4**,
`FIND_SHARED_PART` **85**, `REACHED_VIA` **7** — but the distinct **arrangements**
behind them are only **3, 4 and 2**. So the frozen generator offers new
*instances* of familiar arrangements, not previously unseen ones, and
`LIST_PARTS` is the binding constraint. Both questions you distinguished are
therefore answered explicitly: new instances are available; unseen arrangements
are not.

**The panel now used.** `final_panel.py` enumerates every contains-DAG inside the
teaching difficulty envelope, drops arrangements isomorphic to a teaching
template or a curriculum shape, keeps only those supporting all three reach
questions, and selects **30 pairwise non-isomorphic arrangements** from a
92-arrangement pool.

| Property | Final panel | Teaching material |
| --- | --- | --- |
| Distinct connection patterns | **30** | 4 |
| Idea nodes | 8 / 9 / 10 → 6 / 11 / 13 families | 8 / 9 / 10 |
| `contains` connectors | 6 / 7 / 8 → 15 / 10 / 5 | 6 / 7 / 8 / 9 |
| Direct parts of the asked whole | 2 / 3 → 20 / 10 | 2 / 3 |
| Max chain depth | 3 | 3 |
| Vocabulary | 34 labels, **0** outside the teaching words | 34 words |
| Reach labels | 10 / 10 / 10 | 5 / 1 / 4 |

90 cases, one question per operation, **0** id and **0** signature overlap with
the teaching dataset, the examined panel and the varied curriculum. The examined
panel's content digest still reproduces exactly (`d1076de3…`). No unfamiliar
vocabulary and no deeper reasoning requirement was added to escape the filter.
Same panel for both conditions.

**Interpretation limit:** these limits show the panel is built *within the
documented teaching envelope*; they do **not** prove equal difficulty. New
arrangements may challenge the learner differently — acceptable here because
both curricula face the same panel.

## A second shortcut found and closed (owner review)

The first draft of the curriculum offered `none` in exactly four
`FIND_SHARED_PART` lessons and had `none` **correct in all four**, which permits
"choose none whenever it appears". A pure check of the generated records
confirmed exactly that (offered 4/10, correct 4/4, incorrect 0/4). The builder
now offers `none` as an **incorrect distractor in three lessons where a real
shared part exists**: `none` appears in 7 lessons, is the answer in 4 and a
distractor in 3, so the shortcut scores 4 of 7. Three choices, correct targets,
record count, module and training allowance are unchanged.

## Design and budget (one request)

| Item | Value |
| --- | --- |
| Conditions | control, varied (3 paired seeds `20260913/14/15`, matched initial weights, separate optimizer states) |
| Learners | 6; checkpoints measured at **64** and **256** updates each |
| Total updates | **1,536** |
| Final panel | untouched, 30 families / 90 cases, reach 10/10/10 |
| Wall ceiling | 900 s per learner, 3,600 s worker, 7,200 s instance (2 h) |
| Reservation | one new **`$7.00`** (2 h × `$2.52` + `$1.48` ancillary, rounded up) |
| Ledger after | revision 47 → 48: `$249.00` reserved / `$151.00` unreserved (cap `$400.00`) |
| Retries | zero; original errors preserved; verified cleanup |

## Pre-registered decision rules (fixed now)

* **P1 (primary):** per seed, `varied@256 − control@256 ≥ +0.10` **and**
  family-clustered 95 % bootstrap lower bound `> 0`.
* **P2 (primary):** per seed, `varied@256 ≥ 0.50` absolute.
* **P3 (secondary, reported, never gating):** `control@256 − control@64` and
  `varied@256 − varied@64`.
* **Verdict:** `VARIED_CURRICULUM_BETTER` iff ≥ 2 of 3 seeds satisfy P1 **and**
  ≥ 2 satisfy P2; else `VARIED_CURRICULUM_NOT_ESTABLISHED`. Thresholds are **not**
  lowered; every learner and checkpoint is reported, including regressions.
* Uncertainty: family-clustered percentile bootstrap (10,000 resamples, seed
  `20260926`, 30 clusters × 3 cases) plus exact McNemar.

## Checkpoint delivery (the concrete fix)

Each learner writes **real files** — initial, `step064`, `step256` (18 files) —
containing model `state_dict`, **optimizer state**, encoder projection and
tokenizer vocabulary, step, condition, seed, record ids, torch version. Every
file is **reloaded into a fresh module in-job** and verified by parameter
identity and re-prediction; the launcher **downloads every artifact and
re-verifies sha256 and byte count before cleanup deletes the bucket**, failing
closed on any mismatch.

## Exact package (built; NOT launched)

| Field | Value |
| --- | --- |
| source_sha | `f8b958ab40481a146a3d515b439cc861028e90de` |
| archive_sha256 | `c61c125efac2846520e585619b32f63a9ccbcd1da06bd0d847a052fa932e91cb` |
| archive_bytes | 407819 |
| manifest_sha256 | `f4c60db2af16e7284cd9e3e135eb497ff8dd6ecabc66a2e1f1fbddab029b9cab` |
| member_count | 37 |
| package | `training_mode_001/graph6_curriculum_package_001/` |
| launch request | `training_mode_001/graph6_curriculum_launch_001/launch_request.json` (sha256 `02616ce58cbd1bf1761f0e618ae96374498bf0bee15be2f405c64ce9a3fcaca3`, `launch_authorized: false`) |
| proposed job | `cas-meta2-graph6curr-20260910050000-f8b958ab` |
| launcher | `aws/graph_training_curriculum_launch.py` at commit `f8b958ab` |
| preregistration | `GRAPH6_CURRICULUM_002.md`; evidence `CURRICULUM_002_CHECK.json` (sha256 `bae701cf29710c62b5bef36579e1f5aaaf2d3f1722aee4268d0dc2442bedfe41`) |

Packaged worker byte-checked against `render_worker()`; manifest carries
`launch_enabled:false`, pair seeds, conditions, checkpoints, 1,536 steps, panel
seed `20260930`. 241 graph tests pass. Plan output verified inert
(`PLAN_ONLY_NOT_EXECUTED`, 0 provider calls, no reservation).

## What I need from you

**GO / NO-GO** for this single job (one new owner-signed record + one new `$7.00`
reservation), and confirmation that building the untouched final panel from a
**new shape bank** is acceptable — that is the only way to honour "untouched"
with this generator, and it makes the test stricter (unseen topologies), not
easier. On GO I mint the owner record binding these exact identities, register,
and execute — nothing before.
