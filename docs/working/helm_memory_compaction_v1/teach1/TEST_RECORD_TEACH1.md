# TEST RECORD — TEACH-1 build, FIX FIRST and seal (2026-10-21 PDT, laptop, 0 USD)

Facts from practice data only (rule-written practice turns, practice seed texts, never a sealed world). They decide
nothing. A practice reading is `INCONCLUSIVE` by instrument row I0 by construction; `practice_view` names the word the
marks would print if the seal rows held.

## Practice rounds (16 practice worlds unless stated; 7 arms; frozen reader `reader_t1 v1`)

| Round | HELM | Exam side | What the reader saw | Mark |
|---|---|---|---|---|
| 0 (4 worlds) | build v1 (`64e53842`) | first draft | every arm, even VERBATIM_ONLY: 4 right of 64 taught, **27 WRONG**; refresh asked 0 times; the practice line "Like I said, …" read as a mood, saved as a user fact and served as the answer to every question | 🟥 U1, U2 |
| 1 (4 worlds) | FIX FIRST 1 (`9f0c359a`, below) | route check, anchor words | U1 64 of 64, 0 wrong; HG-H8 false in RANDOM_REFRESH (the arm checked the wrong capsule: my bookkeeping, not HELM); SUMMARY_TEXT served old questions (the arm lacked the new rule) | 🟧 |
| 2 | `9f0c359a` | both arm defects fixed; "Hello there, good to be back." swapped (read as a mood) | all 12 hard gates hold except HG-TESTS (pytest hidden by isolated mode) | 🟨 |
| 3 | `9f0c359a` | pytest found; "station" dropped from the bus template (it is on the recipe-speak list) | every non-seal instrument row and all 12 hard gates hold; RANDOM_REFRESH asked 51 vs COMPACT_ON 27 | 🟨 |
| 4 | `9f0c359a` | RANDOM_REFRESH capped at COMPACT_ON's count (new row I15) | every non-seal row holds; all 12 gates hold; I15 equal in 16 of 16 | 🟩 instrument, 🟥 R4 |

### Round 4 in numbers (`PRACTICE_READING_ROUND4.json`)

| Arm | RIGHT taught | RIGHT squeezed | RIGHT refreshed | WRONG (all quizzes) | refresh asked |
|---|---|---|---|---|---|
| VERBATIM_ONLY | 256 | 256 | 256 | 0 | 0 |
| COMPACT_ON | 256 | 247 | 247 | 0 | 27 |
| REPLAY | 256 | 247 | 247 | 0 | 27 |
| SUMMARY_TEXT | 256 | 247 | 249 | 0 | 27 |
| NO_REFRESH | 256 | 247 | 244 | 0 | 0 |
| RANDOM_REFRESH | 256 | 247 | 242 | 0 | 27 |
| FIFO_DROP | 64 | 64 | 64 | 0 | 0 |

Each arm answered 16 worlds × 16 questions = 256 per quiz. FIFO_DROP's 64 are the 4 honest unknowns per world; it recalls
no taught fact once the budget binds.

| Mark | Practice value | Bar | Reads |
|---|---|---|---|
| U1 | 256 of 256 (avg 16.0) | ≥ 10 avg, 0 wrong | 🟩 |
| U2 | 0 wrong in every arm | 0 | 🟩 |
| R1 vs FIFO_DROP | +183 | ≥ +8 | 🟩 |
| R2 vs SUMMARY_TEXT | **−2** | ≥ +4 | 🟥 (the tie the pre-code forecast) |
| R3 vs RANDOM_REFRESH | +5 | ≥ +4 | 🟩 |
| R4 vs VERBATIM_ONLY | **9 lost** (0 on undamaged items) | ≤ 2; > 4 = harm | 🟥 by planted damage alone |
| R5 vs NO_REFRESH (reported) | +3 | ≥ +2 | 🟩 |
| F1 / F2 / F3 (reported) | 21 of 27 confirmed; 21 strengthened, 21 stayed; 1,115 filed, 630 of 630 lookups anchor-first | — | 🟩 |
| S1 recipe-speak | 512 of 512 teaching replies | ≤ 2 per 48 | 🟥 HELM's chat voice ("…recipe you'd like to work on", "verified data") |
| S2 / S3 | worst 2 per quiz / every unknown marked | — | 🟩 |
| S4 said back | 0 of 32 corrections | ≥ 90% | 🟥 HELM's chat voice |
| HG-H8 | 4,020 memory-served answers, every label right | all | 🟩 |

Practice word if the seal rows held: **`COMPACTION_HARMED`** (R4 > 4), then `COMPACTION_NO_GAIN` reasons R2, S1, S4.

## The owner's ruling on R4 and practice round 5 (A-TEACH1-2, sha256 `17fbd5fe…`)

Owner's words (2026-10-21, verbatim): "Score R4 on the undamaged notes only (my recommendation). The wrecked notes still test honesty, so a rebuilt note must never be called exact. They just don’t count as lost answers. This costs 0 USD and a quick reseal."

R4 is now scored on the 14 undamaged quiz items per world (224 in all); the 2 damaged items per world are judged by
HG-H8 and the other gates. Practice round 5 (16 practice worlds, reader v2, `PRACTICE_READING_ROUND5.json`): every
non-seal instrument row and all 12 hard gates hold (HG-H8 4,020 answers, every label right); **R4 0 lost** 🟩 (the
pre-code's all-items count, reported only: 9, all on damaged items); R1, R3 hold; R2 −2, S1, S4 missed. The word the
practice marks would print if the seal rows held: **`COMPACTION_NO_GAIN`** (was `COMPACTION_HARMED` under the old R4).
Package tests 20 of 20 (one new: a loss on a damaged item is not an R4 loss; a loss on an undamaged item is).

## FIX FIRST round 1 on HELM (commit `9f0c359a`, tests first)

`test_helm_memory_compact.py` + 6 tests: on build v1 `6 failed, 28 passed`; on the fix 34 passed (+5 in
`test_helm_memory.py`: 39). Every HELM suite with the switch OFF on the committed tree: **335 passed** (329 + 6).
From the sealed extract, the package's host list: unittest `Ran 280 tests, OK (skipped=1)`; pytest `47 passed`.
Rules: every-word match + newest first; memory questions are never memories; number words are never clues; a
strengthened rebuild is never EXACT; the chat passes the answer to a refresh question to the compactor.

## Package tests (`tests_teach1/`, 19 tests, planted faults)

The first run caught a reader defect: the invention check counted a never-named person as part of the key, so it could
not flag that name. Fixed (the key = the names the world's facts use); 19 of 19 OK.

## Seals

| Seal | zip sha256 | Fate |
|---|---|---|
| 1 | `83f14426…` | **VOID**: the from-seal test failed 1 of 19 (FROZEN_TEACH1.json held the builder's folder path, a machine-bound value); never used, nothing drawn |
| 2 | `bdcde5b9…` | **VOID**: the sealed amendment said 4,016 label-checked answers for round 4 (that was round 3; round 4 is 4,020); never used, nothing drawn |
| 3 | `e8831bfd…` | **VOID**: its seed bands 2,036 / 2,038 / 2,040 M were taken first by wave 7 v9 (PR #449, merged while this package was built); found when merging the thread head before the PR; never used, nothing drawn |
| 4 | `65e2a926…` | **SUPERSEDED** by the owner's ruling on R4 (A-TEACH1-2); never used, nothing drawn |
| 5 | **`811726c45bd3f31a3df1d565295d191382685f7e7681edfc567e70e22e17dc73`** | **SEALED, NOT RUN, NOT SCORED** (1,023,713 bytes, 195 members + freeze `1ddf5128…`, sealed twice byte-identical); bands 2,042 / 2,044 / 2,046 / 2,048 M; reader v2 (R4 on undamaged items) |

From a fresh extract of seal 5 (`TEST_COUNTS_TEACH1.json`): 195 of 195 members re-hashed equal; package tests OK; cut
check 173 files equal; HELM's suites exit 0; route check 0 bad; a 2-world practice pool 14 of 14 units exit 0;
`helm_now/` unchanged after.

## Cost

0 USD. Laptop only. Round 4 took 163 s for 112 units, one process at a time.
