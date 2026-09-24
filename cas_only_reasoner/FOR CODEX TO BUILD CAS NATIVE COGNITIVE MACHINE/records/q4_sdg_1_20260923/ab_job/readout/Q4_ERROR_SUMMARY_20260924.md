# Q4-SDG-1 saved-error summary: where the A and B models go wrong (final checkpoint)

- **Label:** CLAUDE_BUILT_CLAUDE_CHECKED. Claude built this summary and Claude checked it. No independent person
  or model checked it.
- **Date:** 2026-09-24. **Cost:** $0. It ran on the laptop and used only the Python standard library. No model was
  loaded. Nothing was rerun. No torch. No AWS call.
- **Data:** the saved public records of the finished A-versus-B job, at its last checkpoint (after 32,768 training
  updates): `../results/ab/runs/*/checkpoint_32768.json`, `run_result.json` and `../results/ab/prep.json`.
- **Numbers file:** `Q4_ERROR_SUMMARY_20260924.json` (this folder). The program that made it is
  `summarize_q4_errors.py` (this folder). Every number below comes from that JSON file.
- **Status:** descriptive only. This summary decides nothing. It changes no label. It runs no statistical test.

## The verdict labels (quoted unchanged)

The frozen reader program gave these two answers. They stand exactly as written:

- `LESSONS_OVERALL_EFFECT_NOT_SHOWN`
- `ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE`

(Source: `../VERDICT_LAPTOP_REREAD.json`, fields `lessons_overall` and `architecture`. The per-panel lessons labels
are `LESSONS_EFFECT_NOT_SHOWN_SP1`, `LESSONS_EFFECT_NOT_SHOWN_SP2U` and `LESSONS_EFFECT_NOT_SHOWN_SP2ALL`.)

Where this summary shows arm A next to arm B, the numbers are plain sums over three seeds. They are not a lessons
result. The program's own paired tests found `NO_PAIRED_DIFFERENCE` on every pair.

## The short answer

1. **On familiar tree shapes (SP1), almost every miss is a field value, not the tree structure.** Field values
   (noetic, domain, drive, register) are the first wrong decision in 746 of 768 rows for arm A and 709 of 768 for
   arm B. Tree-branch mistakes are 8 (A) and 20 (B). Operator (+ or ×) mistakes are 10 (A) and 28 (B).
2. **The model gets the first leaf's noetic right. For every later leaf it gets the noetic about as often as a
   guess.** With the right answer fed in up to each step, the first leaf's noetic is right in 684 of 768 (A) and
   763 of 768 (B) cases. The noetic of the 2nd leaf is right in 98 of 768 (A) and 73 of 768 (B) cases. That is
   about the level of always guessing the most common noetic value (90 of 799, about 11.3%). This holds in all six
   runs (the highest single run is A_20260931, leaf 2 at 43/256). It holds on the model's own taught rows too. It
   did not improve at any saved checkpoint from 0 to 32,768 updates. In 4 of 6 runs, none of the 132 edits that
   change a later leaf's noetic in the input made the model's chance of the new value rise by 0.01 or more.
3. **On new, deeper tree shapes (SP2U, SP2ALL), structure is missing.** The targets are 3 levels deep. The model
   most often writes a tree 2 levels deep with fewer leaves. On SP2U the shape is wrong in 606 of 624 rows (A) and
   565 of 624 rows (B). The "first wrong decision" label hides part of this; see Finding 3.
4. **Length follows structure.** On SP1 the answer has the right length in 702 of 768 (A) and 721 of 768 (B) rows.
   On SP2U it is too short in 421 of 624 (A) and 297 of 624 (B) rows.
5. **One proposal** (not approved, not run): train the same model longer and watch the later-leaf noetic. See the
   last section before EXPOSURE.

## Words used here

- **Panel:** a fixed set of test rows. **SP1** = 256 rows with familiar tree shapes and new content.
  **SP2ALL** = 256 rows with 9 held-out tree shapes, each 3 levels deep. **SP2U** = the 208 SP2 rows that were never
  looked at before the run (SP2ALL minus 48 inspected rows). SP1 and SP2U are the two deciding panels; SP2ALL is
  reported.
- **Tree, leaf, field:** each answer is a small tree. A **leaf** is one CAS state. Each leaf has four **fields**:
  noetic (`^0`-`^9`), domain, drive, register. A **branch** point joins two parts with an **operator** (`+` or `×`).
- **Token order:** the model writes the tree top-down, left part first (prefix order). A leaf's four fields are
  written together: noetic, domain, drive, register.
- **Free answer:** what the model writes on its own, one token after another (the "generated tokens").
- **First wrong decision:** the first token where the free answer differs from the target, and what kind of choice
  it was. `WRONG_NOETIC` etc. = a field value. `LOST_BRANCH` = it wrote a leaf where a branch belonged (structure
  lost). `INVENTED_BRANCH` = it wrote a branch where a leaf belonged (structure added). `PLUS_FOR_TIMES` /
  `TIMES_FOR_PLUS` = wrong operator. `PREDICTION_ENDED` / `GRAMMAR_VIOLATION` = the answer stopped early or broke the
  grammar (these never happened).
- **Assisted accuracy:** the model is fed the correct answer up to each step and must choose only the next token
  (teacher forcing). The saved record keeps one right/wrong bit per step. Assisted accuracy counts those bits per
  field. It measures each choice on its own, without earlier mistakes getting in the way.

## Finding 1: what kind of choice goes wrong first

Counts per run. Each row adds up to the panel size (256 / 208 / 256). "Ended / grammar" was 0 everywhere.

### SP1 (256 rows per run)

| Run | Rows | Exact | Noetic | Domain | Drive | Register | Lost branch | Invented branch | + for × | × for + | Ended / grammar | Sum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_20260931 | 256 | 1 | 66 | 2 | 124 | 58 | 2 | 0 | 1 | 2 | 0 | 256 |
| A_20260932 | 256 | 2 | 130 | 1 | 67 | 50 | 2 | 0 | 3 | 1 | 0 | 256 |
| A_20260933 | 256 | 1 | 45 | 104 | 62 | 37 | 3 | 1 | 3 | 0 | 0 | 256 |
| B_20260931 | 256 | 4 | 177 | 2 | 23 | 19 | 4 | 6 | 10 | 11 | 0 | 256 |
| B_20260932 | 256 | 1 | 74 | 7 | 89 | 79 | 1 | 0 | 5 | 0 | 0 | 256 |
| B_20260933 | 256 | 6 | 184 | 10 | 32 | 13 | 4 | 5 | 1 | 1 | 0 | 256 |
| Arm A, 3 seeds | 768 | 4 | 241 | 107 | 253 | 145 | 7 | 1 | 7 | 3 | 0 | 768 |
| Arm B, 3 seeds | 768 | 11 | 435 | 19 | 144 | 111 | 9 | 11 | 16 | 12 | 0 | 768 |

### SP2U (208 rows per run)

| Run | Rows | Exact | Noetic | Domain | Drive | Register | Lost branch | Invented branch | + for × | × for + | Ended / grammar | Sum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_20260931 | 208 | 0 | 22 | 3 | 102 | 42 | 29 | 0 | 1 | 9 | 0 | 208 |
| A_20260932 | 208 | 0 | 105 | 1 | 29 | 22 | 25 | 20 | 4 | 2 | 0 | 208 |
| A_20260933 | 208 | 0 | 12 | 64 | 69 | 38 | 21 | 0 | 2 | 2 | 0 | 208 |
| B_20260931 | 208 | 0 | 48 | 2 | 17 | 20 | 66 | 34 | 10 | 11 | 0 | 208 |
| B_20260932 | 208 | 0 | 29 | 1 | 81 | 60 | 23 | 0 | 4 | 10 | 0 | 208 |
| B_20260933 | 208 | 0 | 20 | 1 | 17 | 11 | 0 | 126 | 24 | 9 | 0 | 208 |
| Arm A, 3 seeds | 624 | 0 | 139 | 68 | 200 | 102 | 75 | 20 | 7 | 13 | 0 | 624 |
| Arm B, 3 seeds | 624 | 0 | 97 | 4 | 115 | 91 | 89 | 160 | 38 | 30 | 0 | 624 |

### SP2ALL (256 rows per run)

| Run | Rows | Exact | Noetic | Domain | Drive | Register | Lost branch | Invented branch | + for × | × for + | Ended / grammar | Sum |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_20260931 | 256 | 0 | 29 | 4 | 126 | 49 | 35 | 0 | 2 | 11 | 0 | 256 |
| A_20260932 | 256 | 0 | 122 | 2 | 39 | 24 | 35 | 25 | 5 | 4 | 0 | 256 |
| A_20260933 | 256 | 0 | 18 | 81 | 80 | 44 | 27 | 0 | 3 | 3 | 0 | 256 |
| B_20260931 | 256 | 0 | 59 | 4 | 22 | 26 | 82 | 36 | 12 | 15 | 0 | 256 |
| B_20260932 | 256 | 0 | 33 | 2 | 102 | 75 | 27 | 0 | 5 | 12 | 0 | 256 |
| B_20260933 | 256 | 0 | 34 | 1 | 23 | 16 | 4 | 138 | 28 | 12 | 0 | 256 |
| Arm A, 3 seeds | 768 | 0 | 169 | 87 | 245 | 117 | 97 | 25 | 10 | 18 | 0 | 768 |
| Arm B, 3 seeds | 768 | 0 | 126 | 7 | 147 | 117 | 113 | 174 | 45 | 39 | 0 | 768 |

### Grouped, and where in the tree it happens

"Field" = the four field columns. "Branch" = lost + invented. "Operator" = + for × and × for +. The last three
columns place the first wrong decision by how many **whole leaves were already right** before it (exact rows have no
wrong decision, so these three columns add up to rows minus exact).

| Panel | Run | Exact | Field | Branch | Operator | Before leaf 1 was finished | After 1 whole leaf right | After 2 or more |
|---|---|---|---|---|---|---|---|---|
| SP1 | A_20260931 | 1 | 250 | 2 | 3 | 184 | 71 | 0 |
| SP1 | A_20260932 | 2 | 248 | 2 | 4 | 193 | 61 | 0 |
| SP1 | A_20260933 | 1 | 248 | 4 | 3 | 200 | 55 | 0 |
| SP1 | B_20260931 | 4 | 221 | 10 | 21 | 37 | 211 | 4 |
| SP1 | B_20260932 | 1 | 249 | 1 | 5 | 172 | 83 | 0 |
| SP1 | B_20260933 | 6 | 239 | 9 | 2 | 51 | 196 | 3 |
| SP1 | Arm A, 3 seeds | 4 | 746 | 8 | 10 | 577 | 187 | 0 |
| SP1 | Arm B, 3 seeds | 11 | 709 | 20 | 28 | 260 | 490 | 7 |
| SP2U | A_20260931 | 0 | 169 | 29 | 10 | 162 | 46 | 0 |
| SP2U | A_20260932 | 0 | 157 | 45 | 6 | 185 | 23 | 0 |
| SP2U | A_20260933 | 0 | 183 | 21 | 4 | 183 | 25 | 0 |
| SP2U | B_20260931 | 0 | 87 | 100 | 21 | 79 | 128 | 1 |
| SP2U | B_20260932 | 0 | 171 | 23 | 14 | 147 | 61 | 0 |
| SP2U | B_20260933 | 0 | 49 | 126 | 33 | 166 | 42 | 0 |
| SP2U | Arm A, 3 seeds | 0 | 509 | 95 | 20 | 530 | 94 | 0 |
| SP2U | Arm B, 3 seeds | 0 | 307 | 249 | 68 | 392 | 231 | 1 |
| SP2ALL | A_20260931 | 0 | 208 | 35 | 13 | 203 | 53 | 0 |
| SP2ALL | A_20260932 | 0 | 187 | 60 | 9 | 231 | 25 | 0 |
| SP2ALL | A_20260933 | 0 | 223 | 27 | 6 | 227 | 29 | 0 |
| SP2ALL | B_20260931 | 0 | 111 | 118 | 27 | 103 | 152 | 1 |
| SP2ALL | B_20260932 | 0 | 212 | 27 | 17 | 185 | 71 | 0 |
| SP2ALL | B_20260933 | 0 | 74 | 142 | 40 | 197 | 59 | 0 |
| SP2ALL | Arm A, 3 seeds | 0 | 618 | 122 | 28 | 661 | 107 | 0 |
| SP2ALL | Arm B, 3 seeds | 0 | 397 | 287 | 84 | 485 | 282 | 1 |

What this says in plain words:

- The models almost never get past the second leaf. At most 2 whole leaves were right before the first mistake,
  in every row of every run.
- On SP1, arm A's first mistake is usually inside leaf 1 (577 of 764 wrong rows). Arm A's leaf-1 drive and
  register are weak (see Finding 5). Arm B's first mistake usually comes after leaf 1 was fully right (490 of 757
  wrong rows), and arm B's most common first mistake is `WRONG_NOETIC` (435 of 768 rows).

## Finding 2: the first leaf's noetic is right; later leaves' noetic is near the guess level

### Assisted noetic accuracy by leaf (SP1, final checkpoint)

"Leaf 2" means the second leaf of the target tree in writing order. The guess level is the share of the most common
noetic value among the SP1 targets: 90 of 799, about 11.3% (`SP1_NOETIC_NULL` in `q4_ab_rules.py`).

| Run | Leaf 1 | Leaf 2 | Leaf 3 | Leaf 4 or later |
|---|---|---|---|---|
| A_20260931 | 248/256 (96.9%) | 43/256 (16.8%) | 21/161 (13.0%) | 16/126 (12.7%) |
| A_20260932 | 181/256 (70.7%) | 21/256 (8.2%) | 10/161 (6.2%) | 13/126 (10.3%) |
| A_20260933 | 255/256 (99.6%) | 34/256 (13.3%) | 13/161 (8.1%) | 16/126 (12.7%) |
| B_20260931 | 255/256 (99.6%) | 21/256 (8.2%) | 15/161 (9.3%) | 7/126 (5.6%) |
| B_20260932 | 256/256 (100.0%) | 25/256 (9.8%) | 18/161 (11.2%) | 14/126 (11.1%) |
| B_20260933 | 252/256 (98.4%) | 27/256 (10.5%) | 14/161 (8.7%) | 17/126 (13.5%) |

The same pattern shows on SP2U and SP2ALL. Arm totals: leaf 1 noetic is 493/624 (A) and 604/624 (B) on SP2U, and
603/768 (A) and 742/768 (B) on SP2ALL. Every later-leaf noetic cell on these two panels is between 9.4% and
12.8%. The other three fields do not fall off this way. For example, SP1 later-leaf register is 46.0% to 54.9%
(A) and 71.2% to 73.7% (B). Full per-field, per-leaf numbers are in the JSON (`assisted_accuracy_by_field_and_leaf`).

### It did not change during training

SP1 assisted noetic, first leaf vs all later leaves, at every saved checkpoint (from the JSON section
`context_reported_not_decisive`):

| Run | Update 0 (before training) | 2,048 | 8,192 | 16,384 | 32,768 |
|---|---|---|---|---|---|
| A_20260931 | 32/256 · 52/543 | 19/256 · 42/543 | 31/256 · 43/543 | 52/256 · 51/543 | 248/256 · 80/543 |
| A_20260932 | 18/256 · 57/543 | 27/256 · 60/543 | 21/256 · 37/543 | 27/256 · 52/543 | 181/256 · 44/543 |
| A_20260933 | 31/256 · 61/543 | 34/256 · 50/543 | 50/256 · 41/543 | 165/256 · 42/543 | 255/256 · 63/543 |
| B_20260931 | 32/256 · 52/543 | 20/256 · 56/543 | 26/256 · 53/543 | 223/256 · 43/543 | 255/256 · 43/543 |
| B_20260932 | 18/256 · 57/543 | 58/256 · 57/543 | 226/256 · 49/543 | 256/256 · 73/543 | 256/256 · 57/543 |
| B_20260933 | 31/256 · 61/543 | 15/256 · 57/543 | 24/256 · 58/543 | 239/256 · 43/543 | 252/256 · 58/543 |

(Each cell: first leaf · later leaves. The 128 and 512 checkpoints are in the JSON; there too the first leaf is
18-35 of 256 and the later leaves 41-70 of 543.)

The first-leaf noetic jumped from the guess level to nearly all right during training (between 2,048 and 32,768
updates, depending on the run; B_20260932 first, A_20260931 and A_20260932 last). The later-leaf noetic stayed
near the guess level from the untrained model to the end (543 × 90/799 ≈ 61 right by guessing; the final counts
are 43 to 80 of 543).

### It is the same on the model's own taught rows

Each run saved its first 64 teaching rows ("TEACH_FIT"; per run, never compared between arms). Assisted noetic at the
final checkpoint: first leaf 61/64, 50/64, 64/64, 64/64, 64/64, 63/64; later leaves 29/139, 23/143, 18/132, 11/115,
14/113, 17/116 (runs in the order A_20260931, A_20260932, A_20260933, B_20260931, B_20260932, B_20260933). So this is
not only a failure on new rows. The model has not learned the later-leaf noetic even on rows it was taught.

### Changing the later-leaf noetic in the input does not raise the new value

The job saved one-field edits: one field value in an SP1 input is changed, and the record keeps the model's chance
of the new value at that field's position, before and after. "Up" = the chance rose by at least 0.01 (the frozen
T2 step). Value edits only (presence edits left out, as in the frozen rule).

| Run | Noetic, leaf 1 | Noetic, later | Domain, leaf 1 | Domain, later | Drive, leaf 1 | Drive, later | Register, leaf 1 | Register, later |
|---|---|---|---|---|---|---|---|---|
| A_20260931 | 64 of 64 up | 73 of 132 up | 63 of 63 | 96 of 122 | 0 of 26 | 0 of 62 | 0 of 23 | 0 of 46 |
| A_20260932 | 64 of 64 up | 0 of 132 up | 63 of 63 | 106 of 122 | 23 of 26 | 26 of 62 | 0 of 23 | 3 of 46 |
| A_20260933 | 64 of 64 up | 46 of 132 up | 54 of 63 | 82 of 122 | 19 of 26 | 42 of 62 | 0 of 23 | 0 of 46 |
| B_20260931 | 64 of 64 up | 0 of 132 up | 63 of 63 | 122 of 122 | 26 of 26 | 52 of 62 | 22 of 23 | 25 of 46 |
| B_20260932 | 64 of 64 up | 0 of 132 up | 63 of 63 | 37 of 122 | 17 of 26 | 24 of 62 | 0 of 23 | 24 of 46 |
| B_20260933 | 64 of 64 up | 0 of 132 up | 63 of 63 | 97 of 122 | 26 of 26 | 60 of 62 | 23 of 23 | 39 of 46 |

In 4 of 6 runs, not one of the 132 later-leaf noetic edits raised the model's chance of the new value by 0.01 (the
"down" counts, in the JSON, are 0 or 1 of 132). The same models do react to later-leaf domain edits. In the other
2 runs (A_20260931, A_20260933) some later-leaf noetic edits move the chance up (73 and 46 of 132), but the
assisted later-leaf noetic is still near the guess level (80/543 and 63/543).

### A note on the input-use test (information only; changes no label)

The frozen input-use test T1 counts assisted noetic over all SP1 noetic slots. At the final checkpoint the program
counted 328, 225, 318, 298, 313, 310 of 799. The summary checked that these equal first-leaf plus later-leaf counts
(for example A_20260931: 248 + 80 = 328). So most of each T1 count comes from the first leaf. This is a description
of where the count comes from. It does not change `INPUT_USE_FULL` or any other label.

## Finding 3: on new, deeper shapes, structure is missing

Structure of the free answer compared with the target tree. Each row adds up to the panel size. "Not a tree" was 0
everywhere: every free answer was one complete tree followed by the end token.

| Panel | Run | Same shape | Fewer leaves (missing) | More leaves (extra) | Same leaf count, other shape | Not a tree | Sum | Leaves missing in total |
|---|---|---|---|---|---|---|---|---|
| SP1 | A_20260931 | 232 | 22 | 1 | 1 | 0 | 256 | 22 |
| SP1 | A_20260932 | 231 | 11 | 4 | 10 | 0 | 256 | 11 |
| SP1 | A_20260933 | 220 | 23 | 5 | 8 | 0 | 256 | 23 |
| SP1 | B_20260931 | 233 | 12 | 7 | 4 | 0 | 256 | 12 |
| SP1 | B_20260932 | 242 | 12 | 1 | 1 | 0 | 256 | 12 |
| SP1 | B_20260933 | 236 | 14 | 1 | 5 | 0 | 256 | 14 |
| SP1 | Arm A, 3 seeds | 683 | 56 | 10 | 19 | 0 | 768 | 56 |
| SP1 | Arm B, 3 seeds | 711 | 38 | 9 | 10 | 0 | 768 | 38 |
| SP2U | A_20260931 | 10 | 195 | 3 | 0 | 0 | 208 | 195 |
| SP2U | A_20260932 | 4 | 47 | 21 | 136 | 0 | 208 | 48 |
| SP2U | A_20260933 | 4 | 179 | 4 | 21 | 0 | 208 | 182 |
| SP2U | B_20260931 | 10 | 127 | 18 | 53 | 0 | 208 | 127 |
| SP2U | B_20260932 | 26 | 157 | 24 | 1 | 0 | 208 | 157 |
| SP2U | B_20260933 | 23 | 13 | 22 | 150 | 0 | 208 | 13 |
| SP2U | Arm A, 3 seeds | 18 | 421 | 28 | 157 | 0 | 624 | 425 |
| SP2U | Arm B, 3 seeds | 59 | 297 | 64 | 204 | 0 | 624 | 297 |
| SP2ALL | A_20260931 | 14 | 238 | 3 | 1 | 0 | 256 | 244 |
| SP2ALL | A_20260932 | 7 | 69 | 26 | 154 | 0 | 256 | 74 |
| SP2ALL | A_20260933 | 7 | 219 | 5 | 25 | 0 | 256 | 231 |
| SP2ALL | B_20260931 | 14 | 153 | 25 | 64 | 0 | 256 | 155 |
| SP2ALL | B_20260932 | 36 | 188 | 31 | 1 | 0 | 256 | 191 |
| SP2ALL | B_20260933 | 33 | 28 | 26 | 169 | 0 | 256 | 35 |
| SP2ALL | Arm A, 3 seeds | 28 | 526 | 34 | 180 | 0 | 768 | 549 |
| SP2ALL | Arm B, 3 seeds | 83 | 369 | 82 | 234 | 0 | 768 | 381 |

Tree depth, target → free answer (SP2U, all targets are depth 3):

| Run | → depth 1 | → depth 2 | → depth 3 | → depth 4 |
|---|---|---|---|---|
| A_20260931 | 0 | 194 | 13 | 1 |
| A_20260932 | 1 | 46 | 160 | 1 |
| A_20260933 | 0 | 168 | 40 | 0 |
| B_20260931 | 0 | 153 | 52 | 3 |
| B_20260932 | 0 | 152 | 56 | 0 |
| B_20260933 | 0 | 94 | 83 | 31 |
| Arm A, 3 seeds | 1 | 408 | 213 | 2 |
| Arm B, 3 seeds | 0 | 399 | 191 | 34 |

(SP1 and SP2ALL depth tables are in the JSON under `target_depth_to_generated_depth`.)

**Why the first-wrong label undercounts structure on SP2.** In writing order, leaf 1's four fields come before the
branch choice for the right-hand part of the tree. When a leaf-1 field is wrong, that field is counted as the first
wrong decision, and the later structure mistake is not counted there. The structure table counts every row. So on
SP2U the shape is wrong in 606 of 624 rows for arm A (624 − 18) and 565 of 624 for arm B (624 − 59), even though
only 95 (A) and 249 (B) rows have a branch mistake as the *first* wrong decision.

**Seeds differ a lot on SP2.** B_20260933 mostly adds structure: 126 `INVENTED_BRANCH` first mistakes on SP2U, and
31 answers 4 levels deep. B_20260931 mostly loses it: 66 `LOST_BRANCH`. A_20260932 keeps depth 3 in 160 of 208 rows
but with another shape (136 rows: same leaf count, other shape). A_20260931 and A_20260933 mostly drop to depth 2
(194 and 168 rows).

## Finding 4: length

Tokens counted with the end token on both sides.

| Panel | Run | Shorter | Same length | Longer | Mean length: free answer vs target |
|---|---|---|---|---|---|
| SP1 | Arm A, 3 seeds | 56 | 702 | 10 | 20.43 vs 20.85 (15,689 vs 16,011 tokens / 768) |
| SP1 | Arm B, 3 seeds | 38 | 721 | 9 | 20.58 vs 20.85 (15,808 vs 16,011 / 768) |
| SP2U | Arm A, 3 seeds | 421 | 175 | 28 | 25.88 vs 30.33 (16,148 vs 18,927 / 624) |
| SP2U | Arm B, 3 seeds | 297 | 263 | 64 | 27.76 vs 30.33 (17,324 vs 18,927 / 624) |
| SP2ALL | Arm A, 3 seeds | 526 | 208 | 34 | 26.74 vs 31.43 (20,533 vs 24,138 / 768) |
| SP2ALL | Arm B, 3 seeds | 369 | 317 | 82 | 28.76 vs 31.43 (22,087 vs 24,138 / 768) |

Per run (shorter / same / longer): SP1 A 22/233/1, 11/241/4, 23/228/5; B 12/237/7, 12/243/1, 14/241/1.
SP2U A 195/10/3, 47/140/21, 179/25/4; B 127/63/18, 157/27/24, 13/173/22. SP2ALL A 238/15/3, 69/161/26, 219/32/5;
B 153/78/25, 188/37/31, 28/202/26. Wrong length here is the same thing as wrong structure: a leaf is 5 tokens and a
branch is 2, so a missing leaf makes the answer shorter.

## Finding 5: assisted accuracy per field

Right choices / all choices, with the correct answer fed in up to each step. The summary re-derived these from the
per-row bits; for SP1 and SP2ALL they equal the saved `tf_by_slot` exactly (checked). SP2U has no saved total, so it
is computed from the bits of its 208 rows. "Rows all right" = rows where every assisted step was right.

| Panel | Run | Noetic | Domain | Drive | Register | Branch | Operator | End | Rows all right |
|---|---|---|---|---|---|---|---|---|---|
| SP1 | A_20260931 | 328/799 (41.1%) | 605/799 (75.7%) | 406/799 (50.8%) | 404/799 (50.6%) | 1317/1342 (98.1%) | 522/543 (96.1%) | 256/256 | 1 |
| SP1 | A_20260932 | 225/799 (28.2%) | 613/799 (76.7%) | 452/799 (56.6%) | 412/799 (51.6%) | 1316/1342 (98.1%) | 526/543 (96.9%) | 256/256 | 2 |
| SP1 | A_20260933 | 318/799 (39.8%) | 460/799 (57.6%) | 441/799 (55.2%) | 400/799 (50.1%) | 1302/1342 (97.0%) | 512/543 (94.3%) | 256/256 | 1 |
| SP1 | B_20260931 | 298/799 (37.3%) | 619/799 (77.5%) | 611/799 (76.5%) | 619/799 (77.5%) | 1310/1342 (97.6%) | 480/543 (88.4%) | 256/256 | 4 |
| SP1 | B_20260932 | 313/799 (39.2%) | 464/799 (58.1%) | 500/799 (62.6%) | 521/799 (65.2%) | 1317/1342 (98.1%) | 516/543 (95.0%) | 256/256 | 1 |
| SP1 | B_20260933 | 310/799 (38.8%) | 507/799 (63.5%) | 592/799 (74.1%) | 639/799 (80.0%) | 1314/1342 (97.9%) | 500/543 (92.1%) | 256/256 | 6 |
| SP1 | Arm A, 3 seeds | 871/2397 (36.3%) | 1678/2397 (70.0%) | 1299/2397 (54.2%) | 1216/2397 (50.7%) | 3935/4026 (97.7%) | 1560/1629 (95.8%) | 768/768 | 4 |
| SP1 | Arm B, 3 seeds | 921/2397 (38.4%) | 1590/2397 (66.3%) | 1703/2397 (71.0%) | 1779/2397 (74.2%) | 3941/4026 (97.9%) | 1496/1629 (91.8%) | 768/768 | 11 |
| SP2U | A_20260931 | 284/931 (30.5%) | 519/931 (55.7%) | 476/931 (51.1%) | 431/931 (46.3%) | 1457/1654 (88.1%) | 639/723 (88.4%) | 208/208 | 0 |
| SP2U | A_20260932 | 179/931 (19.2%) | 551/931 (59.2%) | 381/931 (40.9%) | 428/931 (46.0%) | 1331/1654 (80.5%) | 675/723 (93.4%) | 208/208 | 0 |
| SP2U | A_20260933 | 275/931 (29.5%) | 407/931 (43.7%) | 449/931 (48.2%) | 429/931 (46.1%) | 1408/1654 (85.1%) | 644/723 (89.1%) | 208/208 | 0 |
| SP2U | B_20260931 | 282/931 (30.3%) | 613/931 (65.8%) | 632/931 (67.9%) | 525/931 (56.4%) | 1376/1654 (83.2%) | 589/723 (81.5%) | 208/208 | 0 |
| SP2U | B_20260932 | 284/931 (30.5%) | 416/931 (44.7%) | 487/931 (52.3%) | 510/931 (54.8%) | 1373/1654 (83.0%) | 641/723 (88.7%) | 208/208 | 0 |
| SP2U | B_20260933 | 267/931 (28.7%) | 503/931 (54.0%) | 612/931 (65.7%) | 598/931 (64.2%) | 1298/1654 (78.5%) | 600/723 (83.0%) | 208/208 | 0 |
| SP2U | Arm A, 3 seeds | 738/2793 (26.4%) | 1477/2793 (52.9%) | 1306/2793 (46.8%) | 1288/2793 (46.1%) | 4196/4962 (84.6%) | 1958/2169 (90.3%) | 624/624 | 0 |
| SP2U | Arm B, 3 seeds | 833/2793 (29.8%) | 1532/2793 (54.9%) | 1731/2793 (62.0%) | 1633/2793 (58.5%) | 4047/4962 (81.6%) | 1830/2169 (84.4%) | 624/624 | 0 |
| SP2ALL | A_20260931 | 350/1186 (29.5%) | 645/1186 (54.4%) | 602/1186 (50.8%) | 552/1186 (46.5%) | 1860/2116 (87.9%) | 813/930 (87.4%) | 256/256 | 0 |
| SP2ALL | A_20260932 | 228/1186 (19.2%) | 687/1186 (57.9%) | 476/1186 (40.1%) | 542/1186 (45.7%) | 1717/2116 (81.1%) | 860/930 (92.5%) | 256/256 | 0 |
| SP2ALL | A_20260933 | 345/1186 (29.1%) | 504/1186 (42.5%) | 556/1186 (46.9%) | 549/1186 (46.3%) | 1802/2116 (85.2%) | 821/930 (88.3%) | 256/256 | 0 |
| SP2ALL | B_20260931 | 347/1186 (29.3%) | 760/1186 (64.1%) | 789/1186 (66.5%) | 652/1186 (55.0%) | 1770/2116 (83.6%) | 756/930 (81.3%) | 256/256 | 0 |
| SP2ALL | B_20260932 | 354/1186 (29.8%) | 530/1186 (44.7%) | 611/1186 (51.5%) | 646/1186 (54.5%) | 1773/2116 (83.8%) | 819/930 (88.1%) | 256/256 | 0 |
| SP2ALL | B_20260933 | 333/1186 (28.1%) | 635/1186 (53.5%) | 762/1186 (64.2%) | 752/1186 (63.4%) | 1686/2116 (79.7%) | 772/930 (83.0%) | 256/256 | 0 |
| SP2ALL | Arm A, 3 seeds | 923/3558 (25.9%) | 1836/3558 (51.6%) | 1634/3558 (45.9%) | 1643/3558 (46.2%) | 5379/6348 (84.7%) | 2494/2790 (89.4%) | 768/768 | 0 |
| SP2ALL | Arm B, 3 seeds | 1034/3558 (29.1%) | 1925/3558 (54.1%) | 2162/3558 (60.8%) | 2050/3558 (57.6%) | 5229/6348 (82.4%) | 2347/2790 (84.1%) | 768/768 | 0 |

(Percentages are rounded to one decimal place for reading; the exact counts are the fractions beside them.)

In plain words: with help, the models place branches almost perfectly on familiar shapes (about 98%) and less well
on the new deeper shapes (about 82% to 85%). Noetic is the weakest field everywhere, because every later leaf's
noetic is near the guess level (Finding 2).

## One proposal (PROPOSAL: not approved, not run, not costed)

This is Claude's proposal only. It is not a decision. It needs an owner-signed approval, a frozen threshold and its
own job-limits file before anything runs. Any run goes to AWS, never the laptop.

- **The error it targets:** the later-leaf noetic (Finding 2). It is the single largest, most regular error in the
  data: near the guess level in all six runs, on new and taught rows alike.
- **The repair:** train the same model longer. Keep everything else the same: the same arms, the same seeds, the
  same data, the same panels, the same edits and the same saved per-checkpoint records. For example 4 × 32,768 =
  131,072 single-example updates, with extra saved checkpoints in between.
- **Why this one first:**
  1. The training loss was still falling at the end of every run. Mean loss over three blocks of 4,096 updates,
     named by the update each block ends at (rounded to 4 decimals; full values in the JSON under
     `training_loss_mean_per_4096_updates`; each arm's loss is on its own teaching rows, so A and B losses must not
     be compared):

     | Run | Block ending 16,384 | Block ending 28,672 | Block ending 32,768 |
     |---|---|---|---|
     | A_20260931 | 0.9537 | 0.8031 | 0.7669 |
     | A_20260932 | 0.9016 | 0.7727 | 0.7069 |
     | A_20260933 | 0.8716 | 0.7581 | 0.7274 |
     | B_20260931 | 0.6120 | 0.4238 | 0.4034 |
     | B_20260932 | 0.7466 | 0.5727 | 0.5459 |
     | B_20260933 | 0.6178 | 0.4460 | 0.4190 |

  2. The first-leaf noetic also stayed at the guess level for a long time and then jumped late (for example
     A_20260931: 52/256 at 16,384, then 248/256 at 32,768). The later leaves may simply not have reached that point.
  3. It changes neither the model nor the data. So it does not touch
     `ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE`.
- **What to read out** (the threshold is for the owner-approved spec to freeze, not for this summary): SP1 assisted
  later-leaf noetic against the guess level 90/799; the later-leaf noetic value edits (how many of 132 move the new
  value up by at least 0.01); and the same on the taught rows.
- **What it does not target:** the missing structure on SP2 (Finding 3). That stays open.
- **If it fails:** if the later-leaf noetic stays near the guess level after longer training, that is information for
  the owner. This summary makes no second proposal.
- **Cost:** not estimated here. For scale only: the upper bound for the whole finished job was $0.3383 of $5.00
  (training machine $0.336 + data build $0.0023). That job ran 6 runs of 32,768 updates each, with the panel
  evaluation at every checkpoint.

## What this summary does not show

- It does not show that A and B differ. The program's pair tests found no paired difference, and the verdict is
  `LESSONS_OVERALL_EFFECT_NOT_SHOWN`. The arm totals here are sums, with no test.
- It does not show *why* the later-leaf noetic is not learned. It shows *where* and *how much*.
- It covers the final checkpoint only, except the context section (noetic by checkpoint, taught rows, edits, loss),
  which is reported and decides nothing.
- It does not cover the B package's own dev panel (B_DEV) or compare the teaching-fit rows between arms.
- It does not cover the fourth panel the directive named (longer or deeper than taught). That panel was never built;
  its only visible rows are the protected Q3 G examination.

## Checks (149 checks, all passed; listed in the JSON under `checks`)

- The two verdict labels read from `VERDICT_LAPTOP_REREAD.json` equal the expected strings exactly.
- Panel sizes from `prep.json`: SP1 256, SP2U 208, SP2ALL 256.
- Each run: `run_result.json` says `COMPLETE` with 32,768 updates; the checkpoint is 32,768; the frozen sha256
  (`5b03862a653902699921d668f11cb67c98689e6c80a5d89f76f78fbe962901cb`), arm and seed match.
- Each run and panel: the first-wrong kinds, the structure classes and the length classes each add up to the panel
  size; the exact count equals the EXACT first-wrong count, the saved panel count, and the verdict re-read's count.
- Each run and panel: the first-wrong label, re-derived from the free tokens and the target tokens with the same rule,
  equals the saved `fwd` label in every row (256/256, 208/208, 256/256 in all 18 cases).
- Each row: the slot kinds re-derived from the target tokens equal the saved `slot_kinds`; the target's shape, depth
  and leaf count equal `prep.json`; the assisted bits have one bit per target token.
- SP1 and SP2ALL: the assisted per-field totals re-derived from the bits equal the saved `tf_by_slot`.
- Each run: the final assisted noetic count (first leaf + later leaves) equals the program's T1 count.
- The program refuses to open any `*.pt`, `*_eval*`, `sealed*` or `salt*` file, or anything under the archive.
  Tested outside the 149 checks with five made-up paths (none of them exists): all five were refused before any read.
- Outside the 149 checks: a second run into a scratch file gave a byte-identical JSON (sha256
  `2eca6cafd2a036b687523a9fe3d05c130e78507c9cdaa48435c7e0ecc0789315`, the same as the committed file), and a run
  into the existing output was refused (create-only).

## How to reproduce

From this folder, with Python 3.14 and nothing else installed:

    python -B summarize_q4_errors.py --out <a new path>.json

It is create-only (it refuses an existing output). It prints `CHECKS_PASS: 149 checks, 0 failed`. The output
records the raw sha256 of every file it read (`inputs_sha256_raw_bytes`) and the LF sha256 of itself and of the two
lab modules it imports (`learner_q4_decoder.py` `1f8b1cef11fbf9961bfe98f344115f4ed4a096dbac2772c09aaf3549d16e4451`,
`q4_ab_rules.py` `807ebbef4f6e41f9b53a868a8c319cba657695d3ada65462189dd2f2588e7fa6`, the same pins as the job).

## EXPOSURE (everything outside my working copy that I opened or used)

- **Git:** `git pull --ff-only` of `claude/q4-sdg-feedback-20260923` (already up to date at `1d657408`); `git status`,
  `git log`, `git show --stat HEAD`, `git ls-files` (file names only), `git config core.autocrlf`,
  `git check-attr` (of `prep.json`), `git rev-parse`, `git fetch` of this branch (remote also at `1d657408`). Then
  the commit and push of these three files, by explicit path. Note: this worktree's git metadata lives in
  `_worktrees/vision-next/.git/worktrees/q4-sdg` (shown by `git rev-parse --git-dir`); git itself writes there on
  commit. I opened nothing in the `vision-next` working tree.
- **My own scratch folder**
  `C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/`:
  `try1.json` and `try2.json` (two trial outputs of the program before the final one) and `repro.json` (the
  reproduction run).
- **Memory query:** one PowerShell read of free memory (a number only).
- **Python and tools:** `python` 3.14 and its standard library; Git Bash (`grep`, `sed`, `ls`, `wc`, `file`,
  `timeout`, `mkdir`). No torch, numpy or boto3 import. No AWS call.
- **Context the harness gave me, not opened by me:** the user's `CLAUDE.md` files and memory index.
- **Inside the working copy, read:** in `records/q4_sdg_1_20260923/ab_job/`: `VERDICT_LAPTOP_REREAD.json`,
  `results/ab/job_result.json`, `results/ab/prep.json`, and for all six runs `run_result.json`, `run_manifest.json`,
  `updates.json` and all seven `checkpoint_*.json`; the folder listing of `error_panel_job/`. In
  `research/helm_cas_expression_lab/`: `q4_ab_rules.py` (lines 40-120, 379-386 and `grep` lines),
  `read_q4_ab_results.py` (lines 102-215, 270-310, 520-545), `q4_ab_train.py` (lines 1-60, 193-268),
  `q4_sdg_curriculum.py` (lines 155-170, 400-482 and `grep` lines), `learner_q4_decoder.py` (lines 17-81, 150-175),
  `learner_q4_neural.py` (lines 1-60 and `grep` lines), import lines only of `learner_q4_representation.py`,
  `q4_ab_prep.py` and `historical_compiler.py`, and `grep` lines of `Q4_SDG_AB_SPEC_v0_2.md`. In `_handoffs/`:
  `HELM_NEXT_PHASE_20260923/Q4_AB_BUILDER_REPORT_20260924.md` lines 925-960 (to copy this section's form).
- **Not touched:** any `*.pt` (the untracked model files beside the runs were never opened), `results.tar.gz`, any
  `*_eval.jsonl`, any `sealed*` file, salts, the Q3/Q4 protected examination, `D:/tksCAS-archive/`, S3 or any AWS
  service, the meta1 ledger and worktree, `helm-on-launch-20260924`, `helm-unchanged-repro-20260924`, `vision-next`,
  other worktrees, and Claude transcripts. No Python process was signalled.
