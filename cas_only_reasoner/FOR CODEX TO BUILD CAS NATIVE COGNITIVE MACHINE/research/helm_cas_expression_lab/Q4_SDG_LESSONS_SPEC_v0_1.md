# Q4-SDG-1 lessons v0.1: sizes, mixture and practice budget

**Status: PROPOSED.** This is for the coordinator and the owner to accept, change or refuse. It is not a
decision. Nothing here has run on AWS. No model has trained on these lessons. Label: `CLAUDE_BUILT_CLAUDE_CHECKED`.

Code: `q4_sdg_curriculum.py` (lessons) and `q4_error_panel.py` (diagnostic). Specification: the owner's directive
`Q4_SDG_AND_TARGETED_FEEDBACK_DIRECTIVE_20260923.md`, sections 3 to 8.

## 1. Identity

| Item | Value |
|---|---|
| Schema | `helm-cas-expression-lab.q4-sdg-lessons/0.1` (D rounds: `...q4-sdg-lessons-d/0.1`) |
| Output folder | `data/q4_sdg_v0_1/` (the build refuses a folder that is not empty) |
| Pin file | `Q4_SDG_DATA_PINS.json` (new; `Q3_DATA_PINS.json` is never edited) |
| Main seed (train + dev) | `20260941` |
| Feedback panel seed | `20260951` |
| Error-panel selection seed | `20260971` (in `q4_error_panel.py`) |
| D-round seeds (proposed) | `20260980 + r` for round `r = 1, 2, ...` |
| Seeds never used | `20260921` to `20260925` (Q3). `20260921` is reused only to rebuild the original run's start |
| Record id | first 24 hex of sha256 of `'<schema>:<seed>:<lesson>:<split>:<index>'` |

## 2. What every row is

- One canonical text: `^n^D`, then optional `_{Fk}`, then optional `|R`; branches always bracketed, `+` or `×`.
  A domain is always written. A register is only ever the tail `|R`.
- The pinned compiler (LF sha256 `61ed5a45...`) must accept the text and give exactly the intended tree.
- Shapes allowed: the single state, or one of the 16 Q3 G-train bare shapes (all depth 3 or less).
- Shapes forbidden: the 9 Q3 G-dev bare shapes, and any depth of 4 or more (this excludes every G eval shape).
- The learner file holds only `record_id`, `lesson_family`, `mode`, `observation`. Targets live in `sealed_*` files.

## 3. Proposed pool (`--size 4096`)

The size is the TRAIN pool in rows. Dev and feedback are each 1/16 of it. Numbers are quotas; whole groups
(pairs, sets) can overshoot a quota by one group.

| Lesson | Subfamily | Train | Dev | Feedback | What it teaches |
|---|---|---:|---:|---:|---|
| A | single | 512 | 32 | 32 | one state, all four fields |
| A | one_field_pair | 512 | 32 | 32 | pairs that differ in one field only |
| B | swap_pair | 512 | 32 | 32 | `(a o b)` versus `(b o a)` |
| B | op_pair | 512 | 32 | 32 | `(a + b)` versus `(a × b)` |
| C | grouping | 614 | 38 | 38 | same leaves and operators, different brackets |
| C | operator_only | 410 | 26 | 26 | one operator changed |
| C | leaf_only | 410 | 26 | 26 | one leaf changed |
| C | mixed_allowed_shapes | 614 | 38 | 38 | all 16 allowed shapes, equal share each |
| | **Total** | **4096** | **256** | **256** | |

- Family A may use at most 1,200 of the 1,600 possible single states in all splits. The rest is kept for
  family D. At size 4096 family A uses 1,152.
- The build logs, per split: shape counts, depth counts, operator counts, the A field-value counts, and
  every refused candidate with its reason.
- A small local build (size 256, not the AWS build) gave depths 0/1/2/3 = 64/66/65/62 rows in train.

## 4. Proposed mixture rule, declared before any result

**For the first comparison (A versus B): no curriculum order.**
- Condition B presents its train pool in one seeded shuffle, family-mixed. The mixture is the pool itself:
  A 25%, B 25%, C 50% of rows.
- Condition A presents the Q3 G train pool (2,048 rows) in the original way: `random.Random(seed).shuffle`.
- Order effects are tested later, separately: the same corpus in shuffled order versus curriculum order.

**A later curriculum-order variant (declared now; run only if chosen).**
- Stage 1: depth 0-1. Stage 2: adds depth 2. Stage 3: all depths.
- Promotion: grammar-masked token accuracy of 0.90 or more on a fixed 256-row probe of the current stage's
  train rows, or a fixed update cap per stage, whichever comes first.
- Retention: at least 20% of presentations come from earlier stages.
- Controlled exposure: at least 10% of presentations come from the next stage.

**Family D (mistake-driven) is not part of the first A-versus-B comparison.**
- If it is used later, it is its own arm.
- Triggers come only from train rows or the feedback split.
- Each trigger makes 6 target rows plus 2 controls (branch mistakes), or 6 target/control pairs (operator or
  field mistakes).
- D rows would be capped at 20% of later presentations.

## 5. Proposed practice budget (A versus B)

What we know:
- The original run made 128 single-example updates. Each of 128 rows was seen once.
- Earlier review jobs: 2,000 updates over 256 rows gave no exact reconstruction. Repeated practice
  memorised 8 rows.

Proposal:
- **Equal budgets.** Each arm gets 16,384 single-example updates. That is 4 passes over B's 4,096 rows, and
  8 passes over A's 2,048 rows.
- **Same settings.** Same code path, AdamW, learning rate 0.001, clip 1.0, the same starting tensors (seed
  20260921), and the same limits.
- **Record per arm:** updates, presentations, distinct rows seen, source bytes, target tokens, wall time, and
  GPU peak memory.
- **Equal updates are not equal compute.** B's rows are shorter on average, because it has single states and
  depth-1 pairs, so B sees fewer target tokens. Proposal: report tokens. Decide before launch whether to add a
  token-matched B arm.
- **A larger budget (65,536 updates)** only if it is declared before any 16,384 result is seen.
- **Money:** the owner has not named a ceiling for training. None is assumed here.

## 6. Proposed evaluation panels (fixed before results)

1. **Teaching fit:** 64 rows from each arm's own consumed training rows (declared seed).
2. **New content, familiar structure:** the package dev split (256 rows), for both arms. Single states are
   reported apart, because they are new to arm A.
3. **New structure:** Q3 G dev (256 rows, the 9 held-out shapes). The old 16 rows are flagged as inspected
   many times.
4. **Deeper:** Q3 G eval (depths 4-5) is protected. It is used once, only with owner approval, and only for an
   arm registered in advance.

- **Metrics:** exact full tree first. Then structure, ordered leaves, per-field errors, the first wrong
  decision, length and depth, output diversity, and correct-prefix versus free generation.
- **No model selection:** the checkpoint at the end of the declared budget is the one evaluated. There is no
  early stopping on dev.

## 7. Open for the owner or coordinator

- Accept, change or refuse the size (4096), the mixture, the budget (16,384 updates) and the panels.
- Decide on the token-matched B arm.
- Name a dollar ceiling for the A-versus-B training job.
- Decide on build engine parity. The local build used the Rust `cas_engine` (`rust+python`). The AWS build may
  use the Python engine. Proposal: build on AWS with `--expect-engine` set to the engine recorded here, or accept
  the AWS engine and pin that build.
