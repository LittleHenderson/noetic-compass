# GRAPH6_CURRICULUM_002 — preregistration (varied relationship lessons vs repetition control)

Status: **PREPARED — NOT LAUNCHED.** No reservation, no owner authorization
record, no AWS call exists for this job. Preparation only until owner approval.

Owner directive this answers: *"Prepare `GRAPH6_CURRICULUM_002`: targeted
relationship teaching with an equal-budget repetition control. Preparation only;
no launch or reservation yet."* … *"Do not create another separately funded
diagnostic campaign, and do not move this specialist into child-call integration
yet."*

## 1. The measured problem (unchanged facts)

`GRAPH6_CONFIRMATION_001` attempt 002 (`FRESH_TRANSFER_NOT_CONFIRMED`, 0 of 3):

| Fact | Value |
| --- | --- |
| Familiar learning replicated | fit criterion met **3/3** (margins 0.4940, 0.5148, 0.5340); practice accuracy 9/30→23/30, 4/30→22/30, 9/30→23/30 |
| Fresh accuracy at 256-update-equivalent budget (64 updates) | 34/90, 36/90, 36/90 = 37.78 %, 40.00 %, 40.00 % |
| Weakest fresh operation | `LIST_PARTS` **6/30, 10/30, 7/30** (chance is 10/30) |
| Stronger fresh operations | `FIND_SHARED_PART` 14/30, 15/30, 15/30; `REACHED_VIA` 14/30, 11/30, 14/30 |

The question is **not** whether the module can learn; that replicated. It is
whether the relationship can be taught across enough changed examples to survive
a changed worksheet. The thresholds are **not** lowered.

## 2. Read-only error review (existing records only; no GPU, no new run)

Tool: `tools/graph6_curriculum_error_review.py` (deterministic, pure Python,
~35 s). Evidence: `CURRICULUM_002_ERROR_REVIEW.json`
(sha256 `e317c0c74b0dbad59b35aed9b29e09f50f5aa93096a8516de2d087e6115cbc04`) and
`CURRICULUM_002_ERROR_REVIEW.md`
(sha256 `b42bef20bd60352d68ec75021a218cc25250379e1771bebf1bb6f8d444706bd7`).
Headline numbers were re-derived independently and match exactly.

**`LIST_PARTS` wrong-answer classes (pooled over the three candidates, 90 cases per phase):**

| Phase | correct | missing_part | extra_part | mixed | wrong_whole | padding | other |
| --- | --- | --- | --- | --- | --- | --- | --- |
| before training | 18 | 36 | 15 | 3 | 18 | 0 | 0 |
| after training | 23 | 34 | 22 | 0 | 11 | 0 | 0 |

Independent re-derivation (pooled, both phases): missing_part **70**,
extra_part **37**, mixed **3**, wrong_whole **29**, padding **0**, other **0**;
wrong before **72**, after **67**; correct 18 → 23. **`missing_part` is the
largest wrong class in every cell**, and `extra_part` grows after training.

Other operations (pooled before → after): `FIND_SHARED_PART` correct **30 → 44**,
`wrong_part` 60 → 46, `chose_none` **0 → 0**; `REACHED_VIA` correct **25 → 39**,
`said_direct` **30 → 11**, `said_absent` 18 → 22, `said_via` 17 → 18.

Coverage facts that shaped the curriculum:

* The correct option was present exactly once in **361/361** wrong cases — the
  failures are choice failures, not missing answers.
* Teaching `REACHED_VIA` answers were direct 5 / via 1 / absent 4; the examined
  panel was a declared 10 / 10 / 10 split.
* Teaching `FIND_SHARED_PART` answered `none` in 3/10 cases; the examined panel in
  21/30 — yet the model chose `none` **0 of 60** wrong times before and **0 of
  46** after.
* **No lesson or panel case ever offered three options of equal length**
  (0/10 teaching, 0/30 panel for `LIST_PARTS`); 139 wrong choices split 69
  longest / 70 shortest.
* Ten panel text units fall back to byte tokens in 33/90 panel cases, and 10 node
  labels never appear in teaching.
* UNAVAILABLE in the records: practice-set predicted strings (so practice errors
  cannot be classified), per-option scores, optimizer state, trained weights,
  per-case timings.

## 3. A finding that changed the panel plan (corrected 2026-09-10)

The owner asked for an untouched final panel, and a first draft of this section
claimed the frozen generator could not supply one ("0 of 2,840 families"). Two
corrections, both now measured rather than asserted:

**(a) The finding is narrower than first stated.** Supply depends on the
exclusion scope, and the two scopes answer different questions:

| Scope | Families searched | every record unused | ≥1 selected case unused | all three selected cases unused |
| --- | --- | --- | --- | --- |
| teaching set only (seed `20260909`) | 2,831 | 409 | 2,664 | 751 |
| teaching set **and the examined panel** | 2,831 | **0** | 1,756 | 38 |

Eligible questions per operation in the untouched scope: `LIST_PARTS` **4**,
`FIND_SHARED_PART` **85**, `REACHED_VIA` **7**. The **distinct arrangements**
behind those eligible questions are only **3, 4 and 2** respectively — i.e. at
most the four teaching templates. So the frozen generator can supply **new
instances of familiar arrangements**, not previously unseen arrangements, and
`LIST_PARTS` is the binding constraint. That is the honest, narrowed finding.

**(b) The first replacement draft was not actually new.** Twelve proposed shapes
were checked with a label-invariant graph calculation and reduced to **two**
distinct directed connection patterns (shapes 1,3,4,6,8,9,10,11,12 shared one;
2,5,7 the other) — renaming objects is not novelty. The panel generator was
therefore rebuilt to **enumerate** arrangements and to prove distinctness.

### The final panel as now built

`final_panel.py` enumerates every contains-DAG inside the teaching difficulty
envelope, drops arrangements isomorphic to a teaching template or a curriculum
shape, keeps only those that support all three reach questions, and selects 30
**pairwise non-isomorphic** arrangements (pool: 92).

| Property | Final panel | Teaching material |
| --- | --- | --- |
| Distinct connection patterns | **30** (of a 92-pattern pool) | 4 |
| Idea nodes | 8 / 9 / 10 → 6 / 11 / 13 families | 8 / 9 / 10 |
| `contains` connectors | 6 / 7 / 8 → 15 / 10 / 5 | 6 / 7 / 8 / 9 |
| Direct parts of the asked whole | 2 / 3 → 20 / 10 | 2 / 3 |
| Maximum chain depth | 3 | 3 |
| Vocabulary | 34 labels, **0** outside the supported teaching words | 34 words |
| Reach labels | 10 direct / 10 via / 10 absent | 5 / 1 / 4 |

30 families, 90 cases, one question per operation, **0** id and **0** signature
overlap with the teaching dataset, the examined panel and the varied curriculum.
The examined panel's own content digest still reproduces exactly
(`d1076de3…`). Evidence: `CURRICULUM_002_CHECK.json`.

## 4. The two curricula (equal budget, same schedule)

| | Control | Varied |
| --- | --- | --- |
| Records | the existing 30 train+practice lessons, unchanged | 30 new records (10 per operation) |
| Variation | none | consistent renaming (8 of 10 families use labels absent from teaching), harmless connection reordering (5 families), meaningful rewiring (4 families), nested wholes |
| `LIST_PARTS` | as-is | every lesson carries a missing-part option and a foreign-part option; 7 of 10 have all three options the same length; the correct list is never the unique longest or shortest |
| `FIND_SHARED_PART` | as-is | 4 of 10 offer `none`; 4 of 10 have `none` as the answer; 4 of 10 have equal-length options |
| `REACHED_VIA` | as-is | answers 4 direct / 3 via / 3 absent |
| Schedule | balanced round-robin over operations, position-major | **identical** schedule shape |
| Exposure at 256 updates | 256 deliveries, 30 distinct records, 85/86/85 per operation, 8–9 deliveries per record | **identical counts**, reported |

## 5. Design (pre-registered before execution)

| Item | Value |
| --- | --- |
| Conditions | `control`, `varied` (CAS framing only — not a CAS-vs-generic contest) |
| Paired seeds | `20260913`, `20260914`, `20260915`; both learners of a pair share the same initialization, verified by equal initial checkpoint identity |
| Learners | 6 (3 seeds × 2 conditions), separate copies and separate optimizer states |
| Checkpoints measured | **64** and **256** updates per learner |
| Total updates | **1,536** |
| Final panel | untouched, 30 **pairwise non-isomorphic** arrangements / 90 cases, reach 10/10/10, teaching vocabulary only |
| Wall ceiling | 900 s per learner (declared), 3,600 s worker, 7,200 s instance (2 h) |
| Sealing | predictions produced from an answer-free input view, correctness computed in a second pass; the record states explicitly that this does not prove event ordering |
| Reporting | every learner and both checkpoints, including regressions; per-operation breakdown; exposures; containment; checkpoint identities |

## 6. Checkpoint persistence (the concrete fix the owner asked for)

Every learner writes **real checkpoint files**, not digests:
initial (`step000`), `step064`, `step256` — 18 files — each containing the model
`state_dict`, the **optimizer state**, the encoder projection and tokenizer
vocabulary, the step, the condition, the learner seed, the record ids, and the
torch version. Each file is **reloaded into a fresh module inside the job** and
verified twice: parameter identity and re-prediction of the panel. The launcher
then **downloads every artifact from S3 and re-verifies its sha256 and byte count
before cleanup deletes the bucket**; a missing, short, or altered artifact fails
the job closed.

## 7. Pre-registered decision rules (fixed now, not after seeing results)

Per seed, on the untouched panel, all comparisons paired over the same 90 cases:

* **P1 — curriculum advantage at equal budget (primary):** `varied@256 −
  control@256 ≥ +0.10` accuracy **and** the family-clustered 95 % bootstrap lower
  bound `> 0`.
* **P2 — absolute level (primary):** `varied@256 ≥ 0.50`.
* **P3 — repetition effect (secondary, always reported, never gating):**
  `control@256 − control@64 ≥ +0.10` with interval lower bound `> 0`;
  and `varied@256 − varied@64` for contrast.
* **Verdict:** `VARIED_CURRICULUM_BETTER` iff **≥ 2 of 3 seeds** satisfy P1
  **and ≥ 2 of 3** satisfy P2; otherwise `VARIED_CURRICULUM_NOT_ESTABLISHED`.
* **Uncertainty:** family-clustered percentile bootstrap, 10,000 resamples, seed
  `20260926`, 30 clusters × 3 cases, plus exact McNemar on discordant cases.
* No threshold is lowered, no seed is dropped, no checkpoint is selected using
  final-panel results.

## 8. Budget (one request)

| Item | Value |
| --- | --- |
| Instance | 1 × `g7.2xlarge` (RTX PRO 4500), no T4 fallback |
| Reservation | **`$7.00`** = 2 h × `$2.52` + `$1.48` ancillary, rounded up |
| Ledger after | revision 47 → 48: `$249.00` reserved / `$151.00` unreserved (cap `$400.00`) |
| Retries | zero; original errors preserved; verified cleanup; artifacts collected first |

## 9. What this experiment does NOT claim

No composition claim, no specialist claim, no two-framing comparison, and no
child-call integration (explicitly deferred by the owner). A
`VARIED_CURRICULUM_BETTER` verdict would mean: on an untouched 90-case panel,
varied relationship lessons beat repeating the existing lessons at equal budget
in at least two of three paired seeds and reached 50 % absolute accuracy in at
least two. A negative result is equally reportable and would say the hypothesis
"more varied practice separates the relationship from the surface" is not
supported at this budget.
