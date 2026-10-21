# TEST RECORD — HELM-R1 wave 7, the CHAT WAVE, v3 (FIX FIRST round 2), v4 (reader repair, section 9), v5 (FIX FIRST round 3, section 10), v6 (machine-neutral pin test + the host-exact suite rule, section 11), v7 (the reseal on the reader-gap cut, section 12, on PR #436), v8 (the reseal on the reader v7.1 fix, section 13) and v9 (the reseal on the reader v7.2 fix after job c55, section 14; builder, laptop, 0 USD; practice data only)

Nothing here is a result. Every number comes from the builder's PRACTICE inputs (RB-W1T's practice draw v2 and wave 6's
published practice conversation pool, both excluded from the exam by id and by text; the same draw for v1, v2 and v3).
No exam exists: the owner has not signed the proposed line `CHAT WAVE at 1 USD`, no approval record was written, and no
custodian seal was run. The builder never opened any exam folder or any `KEYS_*` file. Earlier records are kept as
`v1_void_TEST_RECORD_R1W7.md` and `v2_void_TEST_RECORD_R1W7.md`. Machine copies: `TEST_COUNTS_R1W7.json`
(`aa8160df...`), `dry_run/run5_v3_from_seal/DRY_RUN_SUMMARY.json` (`3e171a32...`) and `R1_W7_READING_DRY.json`
(`798f56f2...`), `build/CUT_CHECK_W7.json` (`f8b8b24b...`).

## 1. What changed between v2 and v3 (amendment A-R1W7-3 in the package's PREREGISTRATION_R1W7.md)

- **HELM under test:** commit `dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6` (branch `claude/helm-r1w7-chat-wave-packet-20261020`,
  PR #416, 2 commits on `974fe36c`). Of the 161 cut files exactly four differ from v2: `helm_end_to_end_loop.py`,
  `helm_chat.py`, `helm_wide_turn.py`, `test_helm_wide_alongside.py` (+4 tests, class F). Fixes: no tool engine on a
  kitchen sentence (whole-word keywords, the chat's software trigger knows the wide brain's ingredient names); the wide
  reader claims wave 3b's question forms and strips "Hi again." / "Hello there!"; an "X or Y" line binds X; "but we've
  run out of X" is a reader question (`ABSENT_STATED`). `helm_brain_canonical.py` byte-identical to base `d4488f2a`
  (`24df53c9...`). `build/CUT_CHECK_W7.json`: 161 of 161 equal to `git show dfc7158d`, 0 extra.
- **Package:** pins and labels (commit, version v3; FROZEN `0f1157e9...`; README, RUN_LIMITS, stage note) and one reported
  row, D-W7-19 (tool-engine turns per chat unit; must be 0; reported, not a gate). No mark, threshold, arm, word, band,
  exam size, instrument row or hard gate changed.
- **v1** (zip `5107b9c6...`) and **v2** (zip `7e7fa066...`) are VOID_SUPERSEDED: never launched, no exam drawn; kept with
  `v1_void_` / `v2_void_` prefixes (zip, freeze, test counts, test record, zip sha).

## 2. Sealed package v3

- Zip `HELM_R1_W7_20261020_SOURCE_R1W7.zip` sha256 **`5063baba8be9ba807e7905d5f86732cb1a535ff5a533e67c79f5cbe16edbc6a9`**
  (941,565 bytes; 194 members + the freeze; resealed byte-identical).
- `PACKAGE_FREEZE.json` **`2366e85d7a3b73fa0c6cefb94715aa7ba9cfeb6f3b384c4c0ad88d5ed0165da2`** (the runner's
  `--expected-freeze-sha256` once the owner signs); `PREREGISTRATION_R1W7.md` `abf125a4...` (= precode `efe94ed6...`
  verbatim + A-R1W7-1 + A-R1W7-2 + A-R1W7-3); `contract/HELM_CUT_R1W7.json` `6708c9e9...`.
- Neighbours unchanged: wave 1 v3 `8c55c413...`, wave 3 v3 `bd06f324...`, wave 3b `a6d9dbc7...`, wave 6 v3 `da1ec4d2...`,
  RB-W1T v3 `04eef886...`; all re-verified sealed; nothing written to the repo.

## 3. Tests (from the sealed v3 extract, every process `python -X utf8 -B -I`)

| Suite | Result |
|---|---|
| wave-7 suites (`tests_r1w7/run_tests.py`: unit + kit, incl. the two runner-refusal tests) | **Ran 31, OK** (56.9 s) |
| HELM's own 8 unittest files on a scratch copy of `helm_now/` | **Ran 201, OK** (skipped=1; 4.3 s); sealed `helm_now/` unchanged after |
| members re-hashed against the freeze | 194 of 194, 0 bad |
| receiver check on the practice draw | `all_pass: true` |

## 4. Practice dry run v1 -> v2 -> v3 (`dry_run/run1_from_seal`, `run3_v2_from_seal`, `run5_v3_from_seal`; each pre-seal run has identical totals)

Same practice inputs every time; 14 units one at a time (v3: 59.4 s; largest unit 7.5 s; peak process memory 31-51
MiB); every unit exit 0; 0 crashes; 0 `SystemExit`; 0 network attempts; 0 receipt problems; no file changed under
`helm_now/`; every session log under its scratch; replay and diagnostic projections equal; recorder transparent 6 of 6
(v3: byte-identical even before the wall-clock strip). Reader: `INSTRUMENT_ERROR` / `INCONCLUSIVE` as designed for a
practice mock (I0, I1, I6, I7, I9, I10; HG5 only for want of host sandbox hashes).

| Practice number (CHAT_ON unless said) | v1 `974fe36c` | v2 `1b0c6d62` | v3 `dfc7158d` |
|---|---|---|---|
| X7_REAL RIGHT / WRONG / asks / not scored | 90 / 0 / 23 / 15 | 103 / 0 / 10 / 15 | 103 / 0 / 10 / 15 |
| X7_REAL fully learned of 106 (K1 bar 96) | 97 | 102 | 102 |
| X7_REAL lessons learned / wrong / not learned (670) | 578 / 0 / 92 | 594 / 0 / 76 | 594 / 0 / 76 |
| X7_REAL unexplained asks (K4) | 8 | 0 | 0 |
| X7_REAL RIGHT_AND_PLAIN (P) | 35 | 103 | 103 |
| X7_REAL question turns not routed to the loop | 10 | 0 | 0 |
| X7_REAL CHAT_OFF / LOOP_ON / ALWAYS_ASK RIGHT | 0 / 100 / 0 | 0 / 100 / 0 | 0 / 100 / 0 |
| X7_REAL NH-CHAT lost / gained vs LOOP_ON | 13 / 3 | 0 / 3 | 0 / 3 |
| X7_REAL stock recorded but reply "outside what I know" | 110 of 110 | 0 of 115 | 0 of 115 |
| X7_CONV RIGHT / WRONG / UNDETERMINED / RIGHT_AND_PLAIN | 36 / 1 / 27 / 34 | 38 / 1 / 25 / 38 | 43 / 0 / 21 / 43 |
| X7_CONV CHAT_OFF RIGHT; LOOP_ON RIGHT / WRONG | 28; 36 / 1 | 28; 36 / 1 | 28; 41 / 0 |
| X7_CONV NH-CHAT lost / gained vs LOOP_ON | 2 / 2 | 0 / 2 | 0 / 2 |
| X7_NOISE RIGHT / WRONG / RIGHT_AND_PLAIN; items lost to noise | 36 / 1 / 34; 0 | 38 / 1 / 38; 0 | 43 / 0 / 43; 0 |
| X7_NOISE misrouted scored turns (N) / misrouted noise / noise CAS | 10 / 0 / 0 | 5 / 0 / 0 | 0 / 0 / 0 |
| X7_NOISE CHAT_OFF RIGHT / RIGHT_AND_PLAIN | 28 / 28 | 28 / 28 | 28 / 28 |
| tool-engine turns in chat units (D-W7-19) | not recorded | 4 | 0 |
| CHAT_ON - CHAT_OFF RIGHT: REAL / CONV / NOISE | +90 / +8 / +8 | +103 / +10 / +10 | +103 / +15 / +15 |
| marks met on practice | K1 | K1, K4, P, NH-CHAT | **all six** |
| word had the instruments held | HARMED | HARMED (N, K3) | EARNED_KEEP |

### v3 observations (facts; nothing tuned; a practice draw the builder has seen decides nothing)

- X7_CONV's 21 items not RIGHT are all UNDETERMINED: the 18 faces dialogues (S1, S2, S6, S7: the wide path asks for the
  stock it was just given, in the chat and in LOOP_ON alike), 2 of 4 R4 witness-in-English items (`CV23`, `CV25`), and
  the R7 item `CV31` (its stock sentence is not held at the question). `CV22` (WRONG in v1, v2) now learns "one soup
  needs 1 cup of dry bean" and is RIGHT.
- The limiting name of an "X or Y" line is said with the note in it: "Or chicken bouillon runs out first" (`CV18`);
  scored RIGHT by the K-R head.
- X7_REAL: 10 recipes asked as `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` (not fully learned, so explained), 2
  `UNDETERMINED_CLARIFY`, 1 `CLARIFY_NOT_CCE`; 25 of 128 not RIGHT in CHAT_ON, 15 of them UNDETERMINED keys (not scored).
- The chat answers 3 REAL items RIGHT that LOOP_ON (wave 3's triad-wrapped loop build) asks on, in every version
  (`RW:pg:38193@134740`, `RW:pg:42450@482967`, `RW:pg:65061@548598`); not investigated.

## 5. Deviations (all in the package's amendments; D-W7-1..5 are the precode's)

D-W7-6 LOOP_ON = wave 6's `FULL+WIDE_NOASK`. D-W7-7 "quotes the yield" = an exact number. D-W7-8 HG2 on REAL and CONV.
D-W7-9 K4 strict; an unrouted question is an ask. D-W7-10 `new_session` no-op in a chat arm. D-W7-11 isolated python.
D-W7-12 the 161-file cut. D-W7-13 the chat's tool engine roots at `helm_now/`; tree hash per unit. D-W7-14
`NOT_ROUTED_TO_LOOP` rows. D-W7-15 recorder fixture. D-W7-16 owner line proposed. D-W7-17 I12 strips wall-clock fields
(v2). D-W7-18 the loop's tool turns recorded (v2). **New in v3:** D-W7-19 tool-engine turns per chat unit reported, 0
required on practice (reported row, not a gate).

## 6. Forecast after v3 practice (not read by any program)

`CHAT_WAVE_EARNED_KEEP` about 0.45 (every mark holds on the practice draw; a fresh draw can hold a lesson form read
wrongly (K3), a question form not claimed (N), or a yield said in a form the quoting rule does not read (P));
`CHAT_WAVE_HARMED` about 0.2; `CHAT_WAVE_NO_GAIN` about 0.15; `INCONCLUSIVE` about 0.2.

## 7. Still wrong in HELM that this build shows (for the owner to read; not tuned here)

1. Faces stated in a dialogue (S1, S2, S6, S7; 18 of 64 items by construction) are UNDETERMINED in the chat and in the
   loop driven directly: the wide path does not read the face clause and asks for stock it already has. No mark
   suffers (LOOP_ON loses them too), but a quarter of every X7_CONV draw is unanswered.
2. The R7 "next session" dialogue `CV31` loses its stock at the question; `CV30` does not.
3. Two R4 witness-in-English items (`CV23`, `CV25`: "Yesterday we made 1 X from ..., and the Y ran out first.") are not
   admitted as lessons.
4. The "X or Y" limiting name is spoken as "Or chicken bouillon" (`CV18`): right by the key, odd to a person.

## 8. What failed while building v3

Nothing new: the stale-freeze kit test failed before the reseal (expected) and passes from the seal; every suite and the
dry run passed first time on the v3 cut.

## 9. v4 row (A-R1W7-4, the HG5 reader repair reseal; 2026-10-20, laptop, 0 USD, practice data only; the v3 state of this file is kept as `v3_TEST_RECORD_R1W7.md`)

Why v4 exists: v3 ran as job c51 and the frozen reader said `FAILURE` / `INCONCLUSIVE` because HG5 demanded `helm_now_files_changed`
from every unit and the recorder unit never wrote it (the fixture gave it the field by hand), plus the stage plan's empty `pythonpath`
killed attempt 1. The owner ordered: "want the chat test rerun with the reader repaired". Built in `build_v4\` from a fresh extract of
the v3 zip (`build_v4\extract_v3\`, never edited); every edit is an exact once-only replacement (`build_v4\build\patch_v4_*.py`,
logs `PATCH_V4_LOG*.json`); `READER_FIX_DIFF_V4.md` holds the whole diff (`r1w7/merge_r1w7.py` 9 changed lines, `r1w7/chat_harness.py`
22, `tests_r1w7/fixture_run.py`, `test_units_w7.py`, `test_kit_w7.py`, `r1w7/custody_w7.py`, `r1w7/common_w7.py`, `kit/STAGE_R1W7.json`,
`kit/run_r1w7.py` comment, `RUN_LIMITS_R1W7.json`; new `kit/stage_check_w7.py`). Amendment A-R1W7-4 = section 16 of the package's
`PREREGISTRATION_R1W7.md` (`8b0ef140...`).

| Item | v4 |
|---|---|
| Zip | `HELM_R1_W7_20261020_SOURCE_R1W7_v4.zip` sha256 **`8602b1bc98b543e4551e766d9db540d22d6dbc690b788dbbce5c91e4b6c7b712`** (950,613 bytes; 195 members + the freeze; resealed byte-identical) |
| `PACKAGE_FREEZE.json` | **`948cf6913963f5fe06ab87b46e2ebcf03c3f541433877e04bda666d6e429f072`**; `FROZEN_R1W7.json` `5d032bb7...` (`FROZEN_R1W7_v4.json` beside the zip) |
| HELM under test | commit `dfc7158d`, unchanged: `helm_now/` 162 files (161 cut + `SOURCE_CUT.json`) byte-identical to v3's freeze (`HELM_NOW_IDENTITY_V4.json`); `build_v4\CUT_CHECK_W7_v4.json` 161 of 161 equal to `git show dfc7158d`, 0 extra; byte copies `kit/plan_check.py` `84257a23...` and `kit/job_supervisor.py` `3b2337ca...` unchanged |
| Tests from the sealed extract (`TEST_COUNTS_R1W7_v4.json` `0c4f565a...`) | wave-7 suites **Ran 34, OK** (80.1 s; v3 had 31: +2 HG5 tests, +1 stage-check test); HELM's 8 unittest files on a scratch copy **Ran 201, OK** (skipped 1; 6.1 s); 195 / 195 members re-hashed; `helm_now/` unchanged by the suites. Before the seal the only failing test was the stale-freeze runner test (expected; passes from the seal). |
| The three HG5 tests | clean fixture: HG5 **true**, 14 of 14 units carry `[]`, missing list empty; plant `HG5c` (recorder unit lacks the field, the c51 shape): HG5 **false**, names `W7_RECORDER_EQUALITY`, 13 with the list; plant `HG5d` (recorder unit lists `helm_chat.py`): HG5 **false**. Also: the real recorder unit on practice turns writes `helm_now_files_changed == []`. |
| v3 practice data read by the v4 reader (`build_v4\reread_v3_practice\R1_W7_READING_V3DATA_V4READER.json` `5f90b063...`; a copy of `dry_run\run5_v3_from_seal`, never edited) | HG5 **false**, as expected: `units_missing_helm_now_files_changed` = `["W7_RECORDER_EQUALITY"]`, 13 of 14 with the list (the v3 recorder unit never wrote it); the two host rows (wave-1 hash pair, helm_cut row) are absent on the practice mock as well |
| Practice run from the v4 seal (`dry_run\run6_v4_from_seal`, 14 units one process at a time, 83.6 s, 14 of 14 exit 0, peaks 31.5-51.1 MiB; `DRY_RUN_SUMMARY.json` `01e02012...`, `R1_W7_READING_DRY.json` `4aaf5665...`) | verdict `INSTRUMENT_ERROR` / `INCONCLUSIVE` as designed for a practice mock (I0, I1, I6, I7, I9, I10 false); every mark met; **every number equals the v3 practice reading** (0 differing keys in `DRY_RUN_SUMMARY.json` outside timing and hashes). HG5 unit rows: 14 of 14 carry `[]`, missing list empty, `helm_now_files_changed` `{}`. As run, HG5 still reads false on practice because the laptop dry-run tool supplies neither the wave-1 folder hash pair nor the helm_cut instrument row (the host runner supplies them on AWS; v3's practice read the same two rows false). |
| The same run6 read again with those two host rows supplied (`reread_v4.py`; units untouched; `R1_W7_READING_DRY_WITH_HOST_ROWS.json` `3e8be09e...`; `PRACTICE_READINGS_V4.json` `a17cd941...`) | **HG5 holds: true**; `failing_gates` `[]`; wave-1 folder equals its sealed freeze after the run (110 of 110 members, 0 extra; tree sha `3a4987af...`); `canonical_brain_equals_base` true; marks and every reported row identical to the as-run reading. The verdict stays `INSTRUMENT_ERROR` (practice mock), as it must. |
| Exclusions (`contract/EXCLUDE_R1W7_PRIOR_USED.json` `19e972af...`) | block `X7_c51`: `X7_c51_real` 128 + `X7_c51_conv` 64 (ids from `x7_custody\X7_SEALED_20261021T024717Z.json` only); 16 lists, 1,466 distinct ids (v3: 14 lists, 1,277); every list now applies to BOTH pools; the 3 flagged REAL ids (`pg:65501@21017`, `pg:6912@731078` in `x6_conv`; `pg:49958@479072` in `x6v3_conv`) recorded in the block |
| Seed bands / owner line | REAL 2,000,000,001-2,001,000,000; CONV 2,002,000,001-2,003,000,000; NOISE 2,004,000,001-2,005,000,000; used table 1-1,999,000,000; line to sign **`CHAT WAVE 2 at 1 USD`** (20 UTF-8 bytes); seed = sha256(line + ":" + v4 zip sha256) |
| Stage plan | `kit/STAGE_R1W7.json` `pythonpath` = `["HELM_R1_W7_20261020"]` (= c51 attempt 2's job plan, D-OP-C51-1); `kit/stage_check_w7.py` PASS on the sealed stage, FAIL on `[]` and on a non-folder; the supervisor's own `validate_plan` passes the sealed stage and raises `PLAN_INVALID:r1w7_host_run:pythonpath` on `[]` (kit test) |
| Status | SEALED, **NOT LAUNCHED**; no exam drawn; no approval record; c51's record stands; v3 `VOID_SUPERSEDED_BY_V4` (`v3_VOID_SUPERSEDED_BY_V4.md`) |

What failed while building v4: nothing beyond the expected stale-freeze test before the seal. One honest limit: the laptop
dry-run tool cannot make HG5 read true by itself (two host-only rows); the reread with those rows supplied is the practice
proof that every HG5 row can now hold, and the sealed test suite is the proof that the gate still catches a missing list.

## 10. v5 row (A-R1W7-5, FIX FIRST round 3 on c52's one unexplained ask; 2026-10-20, laptop, 0 USD, practice data only)

Why v5 exists: v4 ran as job c52 and the frozen reader said `PASS` / `CHAT_WAVE_NO_GAIN`: every hard gate held, K4 HONEST was
missed by exactly one unexplained ask, the same in LOOP_ON. The owner ordered a "third chat round". The item was found by program
in the unit outputs (`K4_ITEM_DIAGNOSIS.md` beside the zip; id only, never the text): a batch or stock sentence carrying an amount
of a condition (a temperature) after an ingredient line; the wide reader cut the sentence there and bound the piece as an
ingredient, so the brain waited for a batch where that "ingredient" ran out and asked. Fixed in HELM as one general rule
(`helm_wide_turn.condition_fragment`; PR #425, commit `f45a8570`; test class G 3 of 3 fail on `1d2b390f`, 3 of 3 pass). v5 =
v4 with `helm_now/` recut at the fix, block `X7v4_c52` excluded, fresh bands and a new line; reader, recorder, fixture, marks,
thresholds, arms and words unchanged. Built in `build_v5\` from a fresh extract of v4 (`build_v5\extract_v4\`, never edited);
every package edit is an exact once-only replacement (`build_v5\build\patch_v5.py`, log `PATCH_V5_LOG.json`, 31 edits);
amendment A-R1W7-5 = section 17 of the package's `PREREGISTRATION_R1W7.md`.

| Item | v5 |
|---|---|
| Zip | `HELM_R1_W7_20261020_SOURCE_R1W7_v5.zip` sha256 **`4b54a077e4b2963301451c6eb78836a32d9797460cd8143d3cf2f9efdc1a7cf8`** (980,035 bytes; 198 members + the freeze; resealed byte-identical) |
| `PACKAGE_FREEZE.json` | **`8cc543d2102951c79e897f478bc31781e87c511d0a24be54cbf92611ce2bbfd1`**; `FROZEN_R1W7.json` `f71ab86a...` (`FROZEN_R1W7_v5.json` beside the zip) |
| HELM under test | commit `f45a85706a9d8b9177e4b7279453d1538c12045d` (PR #425 to the thread, 1 commit on `1d2b390f`): `helm_now/` 164 cut files + `SOURCE_CUT.json` (`CUT_CHECK_W7_v5.json` 164 of 164 equal to `git show`, 0 extra; cut `7465b615...`); +3 files vs v4 by the contract's own rule (`helm_cas_address.py`, imported by the loop since `9916d7da`, switch default OFF; `test_helm_cas_address.py`; `test_helm_units_note.py`); `helm_brain_canonical.py` = base `24df53c9...`; byte copies `kit/plan_check.py` `84257a23...` and `kit/job_supervisor.py` `3b2337ca...` unchanged |
| Tests from the sealed extract (`TEST_COUNTS_R1W7_v5.json` `d6dda0da...`) | wave-7 suites **Ran 34, OK** (66.1 s; pre-seal Ran 34 OK with 2 skipped); HELM's 8 unittest files on a scratch copy **Ran 204, OK** (skipped 1; 4.6 s; v4 201: +3 class G tests); the host's 10-file list (`kit/run_r1w7.py` `HELM_TESTS`, now + `test_helm_cas_address`, `test_helm_units_note`) on the same scratch copy **Ran 236, OK** (skipped 1); 198 / 198 members re-hashed; `helm_now/` unchanged by the suites |
| Practice run from the v5 seal (`dry_run\run7_v5_from_seal`, 14 units one process at a time, 65.5 s, 14 of 14 exit 0, largest unit 8.3 s, peaks 31.6-60.8 MiB; `DRY_RUN_SUMMARY.json` `61445386...`, `R1_W7_READING_DRY.json` `a2985266...`) | verdict `INSTRUMENT_ERROR` / `INCONCLUSIVE` as designed for a practice mock (I0, I1, I6, I7, I9, I10 false); every mark met (`marks_missed` `[]`); HG5 unit rows 14 of 14 carry `[]`, missing list empty |
| The same run7 read again with the two host rows supplied (`reread_v5.py`; units untouched; `R1_W7_READING_DRY_WITH_HOST_ROWS.json` `75b529ba...`; `PRACTICE_READINGS_V5.json` `2c1c5bbf...`) | **HG5 holds: true**; `failing_gates` `[]`; wave-1 folder equals its sealed freeze after the run (110 of 110 members, 0 extra); `canonical_brain_equals_base` true; marks and every reported row identical to the as-run reading |
| Practice numbers v5 (run7) beside v4 (run6) | **0 differing keys** across marks, mark parts, totals, noise and stock rows (`v5_minus_v4_practice_differences` `[]`): the practice draw holds no condition-shaped line, so the fix changes nothing there. CHAT_ON REAL: RIGHT 103 / WRONG 0 / ASKS 10 / NOT_SCORED 15, RIGHT_AND_PLAIN 103, fully learned 102 of 106 (bar 96), lessons LEARNED 594 / NOT_LEARNED 76, unexplained asks 0 (strict 0), unrouted 0, commitments on undetermined 12; LOOP_ON REAL 100 / 0 / 13 / 15, learned 99, unexplained 0; CHAT_OFF REAL 0 / 0 / 113 / 15, NOT_LEARNED 670, unrouted 10; CONV CHAT_ON 43 / 0 / 21 undetermined (LOOP_ON 41 / 23; CHAT_OFF 28 / 36, misrouted 10, unrouted 7); NOISE CHAT_ON 43 / 0 / 21, 128 noise turns, 0 misrouted (CHAT_OFF 28, misrouted 10); K1 102 of 106 ✓, K3 0/0/0/0 ✓, K4 0 ✓, NH-CHAT lost 0 REAL (103 vs 100, gained 3) and 0 CONV (43 vs 41, gained 2) ✓, P 0 not plain ✓, N lost 0 ✓; stock turns CHAT_ON STOCK_RECORDED 115, UNKNOWN_INGREDIENT 9, NO_INGREDIENT_NAMED 2, NO_STOCK_FRAME 1, INVENTORY_RECORDED 1 — every number equal to v4's run6 |
| Exclusions (`contract/EXCLUDE_R1W7_PRIOR_USED.json` `4c9dcf84...`) | block `X7v4_c52`: `X7v4_c52_real` 128 + `X7v4_c52_conv` 64 (ids from `x7v4_custody\X7_SEALED_20261021T050521Z.json` only; 0 overlap with any older list); 18 lists, 1,658 distinct ids (v4: 16 lists, 1,466); every list applies to BOTH pools |
| Seed bands / owner line | REAL 2,006,000,001-2,007,000,000; CONV 2,008,000,001-2,009,000,000; NOISE 2,010,000,001-2,011,000,000; used table 1-2,005,000,000 (1,996-1,999 M stays reserved for the continuity packet); line to sign **`CHAT WAVE 3 at 1 USD`** (20 UTF-8 bytes); seed = sha256(line + ":" + v5 zip sha256) |
| Status | SEALED, **NOT LAUNCHED**; no exam drawn; no approval record; c52's record stands; v4 `VOID_SUPERSEDED_BY_V5` (`v4_VOID_SUPERSEDED_BY_V5.md`) |

What failed while building v5: nothing in the package. Two decisions recorded: (1) the cut is 164 files, not 161, because the
contract's own rule ("+ every helm_*.py / test_helm_*.py at the commit") picks up the three files that entered the thread after
v4's cut, and the loop imports one of them; (2) the wide reader's version string was left as is because `test_helm_cas_address`
pins the OFF-path trace bytes (the rule itself is documented in the reader's header). One limit kept as a negative in the
diagnosis: the same stock sentence with plain unit words and the temperature in the middle is claimed first by the licensed
English reader's stock-frame rule and is not recorded; that is the licensed reader's own rule, not the c52 cause, unchanged.

## 11. v6 row (A-R1W7-6, the machine-neutral pin test and the host-exact suite rule after c53's instrument failure; 2026-10-21, laptop, 0 USD, practice data only)

Why v6 exists: v5 ran as job c53 and the frozen reader said `INSTRUMENT_ERROR` / `INCONCLUSIVE`: all 10 hard gates and all six
marks true as facts (K4 0: the round-3 fix held on fresh data), but instrument row I6 (`suites_ok`) false because one HELM unit test
failed on the Linux host (`test_helm_cas_address.C_LoopStamps.test_off_is_byte_identical_to_the_pre_change_code`: OFF records
`6bf323ad…` vs the stored laptop value `56f356ea…`). The owner ordered a "Fourth chat round". The cause was proven on the laptop by
program (`PIN_TEST_DIAGNOSIS.md` beside the zip): the only machine-bound value in the hashed records is the absolute path of the
wave-1 brain folder (`brain_dir` in two brain trace rows; two turn receipts hash over those rows); reporting the host's path on the
laptop reproduces `6bf323ad…` exactly, on base `159c7d2b` too. Fixed in HELM's tests by a second builder (PR #429, commit
`ad4fde73`; a first pass `3dae274f` / PR #428 was found insufficient by this builder's diff and superseded): records are hashed
through `helm_test_pins.canon` (the `brain_dir` and `receipt_hash` leaves stripped, absolute paths neutralised), new pin `312ddfd6…`,
and `test_helm_pin_hygiene.py` (9 tests) guards the class. v6 = v5 with `helm_now/` recut at `ad4fde73`, the host's HELM list grown
to 11 names, block `X7v5_c53` excluded, fresh bands and a new line; reader, recorder, fixture, marks, thresholds, arms and words
unchanged. Built in `build_v6\` from a fresh extract of v5 (`build_v6\extract_v5\`, never edited); every package edit is an exact
once-only replacement (`build_v6\build\patch_v6.py`, log `PATCH_V6_LOG.json`, 32 edits); amendment A-R1W7-6 = section 18 of the
package's `PREREGISTRATION_R1W7.md`.

**Rule since v6 (A-R1W7-6 item 6):** the seal step runs EXACTLY the host's HELM suite list (`kit/run_r1w7.py` `HELM_TESTS`, the
script the stage plan runs) with the host's command form, from a fresh extract of the sealed zip, and records the names, the
command and the `Ran` / `OK` line in `TEST_COUNTS_R1W7_v6.json` under `host_exact_suite_list`; the seal tool refuses unless the
sealed list equals its own typed copy and the stage plan's `argv[0]` is `kit/run_r1w7.py`. (v5's seal record ran an 8-file scratch
list, Ran 204, while the host ran 10 files, Ran 236; the v5 host failure was the one test above.)

| Item | v6 |
|---|---|
| Zip | `HELM_R1_W7_20261020_SOURCE_R1W7_v6.zip` sha256 **`387577deac79d8b395e1e3245cd3bb1bdddb20b0b21b86f1078e7a0cd20442f8`** (991,928 bytes; 200 members + the freeze; resealed byte-identical) |
| `PACKAGE_FREEZE.json` | **`3c7a9f3d6b18f6a70c83ac2447db045ff3bafccc6ce99de39a454c45225d1933`**; `FROZEN_R1W7.json` `b69d8034…` (`FROZEN_R1W7_v6.json` beside the zip) |
| HELM under test | commit `ad4fde734257cfd5e94ff1b54b8891df9d2e3003` (branch `claude/helm-pin-hygiene-2-20261021`, PR #429 to the thread, 1 commit on thread head `5f07c5d7`; the hash is unchanged by a merge): `helm_now/` **166 cut files** + `SOURCE_CUT.json` (`CUT_CHECK_W7_v6.json` 166 of 166 equal to `git show`, 0 extra; cut `2f16f424…`); +2 files vs v5 by the rule, which now names `helm_test_pins.py` explicitly (`helm_test_pins.py`, `test_helm_pin_hygiene.py`); `test_helm_cas_address.py` changed; every other file equal to v5's cut; `helm_brain_canonical.py` = base `24df53c9…`; `helm_wide_turn.py` byte-identical to the round-3 fix; byte copies `kit/plan_check.py` `84257a23…` and `kit/job_supervisor.py` `3b2337ca…` unchanged |
| Tests from the sealed extract (`TEST_COUNTS_R1W7_v6.json` `6313bdc7…`) | wave-7 suites **Ran 34, OK** (68.6 s; pre-seal from the package folder Ran 34 with one failure once, then Ran 34 OK on re-run, see below); **the host's exact list, 11 names, one process, the host's command form on a scratch copy of the sealed `helm_now/`: `Ran 245 tests in 5.558s`, `OK (skipped=1)`** (the one skip: `test_licensed_files_untouched`, "base commit not reachable in this checkout", as on c53; the pin test `... ok`); list equals the sealed kit's `HELM_TESTS`, stage plan `argv[0]` = `kit/run_r1w7.py`; 200 of 200 members re-hashed; `helm_now/` unchanged by the suites |
| Suites on the laptop at `ad4fde73` (one process each) | brain_wide 54, cas_address 17, end_to_end_loop 18, english_in 37, english_in_stock_frame 17, faces_in 16, pin_hygiene 9, triad 15, units_note 15, voice 22, wide_alongside 25 (= 245) all OK; pytest-style agentic_planner 8, chat_nuance 8, memory 4 passed |
| Practice run from the v6 seal (`dry_run\run8_v6_from_seal`, 14 units one process at a time, 68.4 s, 14 of 14 exit 0, largest unit 8.3 s, peaks 31.4-60.6 MiB; `DRY_RUN_SUMMARY.json` `0c1f435c…`, `R1_W7_READING_DRY.json` `640ecce7…`) | verdict `INSTRUMENT_ERROR` / `INCONCLUSIVE` as designed for a practice mock (I0, I1, I6, I7, I9, I10 false); every mark met (`marks_missed` `[]`); HG5 unit rows 14 of 14 carry `[]`, missing list empty |
| The same run8 read again with the two host rows supplied (`reread_v6.py`; units untouched; `R1_W7_READING_DRY_WITH_HOST_ROWS.json` `2af24a12…`; `PRACTICE_READINGS_V6.json` `2ff64702…`) | **HG5 holds: true**; `failing_gates` `[]`; wave-1 folder equals its sealed freeze after the run (110 of 110 members, 0 extra); `canonical_brain_equals_base` true; marks and every reported row identical to the as-run reading |
| Practice numbers v6 (run8) beside v5 (run7) | **0 differing keys** across marks, mark parts, totals, noise and stock rows (`v6_minus_v5_practice_differences` `[]`), as v5 beside v4. CHAT_ON REAL: RIGHT 103 / WRONG 0 / ASKS 10 / NOT_SCORED 15, RIGHT_AND_PLAIN 103, fully learned 102 of 106 (bar 96), lessons LEARNED 594 / NOT_LEARNED 76, unexplained asks 0 (strict 0), unrouted 0, commitments on undetermined 12; LOOP_ON REAL 100 / 0 / 13 / 15, learned 99, unexplained 0; CHAT_OFF REAL 0 / 0 / 113 / 15, NOT_LEARNED 670, unrouted 10; CONV CHAT_ON 43 / 0 / 21 undetermined (LOOP_ON 41 / 23; CHAT_OFF 28 / 36, misrouted 10, unrouted 7); NOISE CHAT_ON 43 / 0 / 21, 128 noise turns, 0 misrouted (CHAT_OFF 28, misrouted 10); K1 102 of 106 ✓, K3 0/0/0/0 ✓, K4 0 ✓, NH-CHAT lost 0 REAL (103 vs 100, gained 3) and 0 CONV (43 vs 41, gained 2) ✓, P 0 not plain ✓, N lost 0 ✓; stock turns CHAT_ON STOCK_RECORDED 115, UNKNOWN_INGREDIENT 9, NO_INGREDIENT_NAMED 2, NO_STOCK_FRAME 1, INVENTORY_RECORDED 1 — every number equal to v5's run7 |
| Exclusions (`contract/EXCLUDE_R1W7_PRIOR_USED.json` `7dc74c4c…`) | block `X7v5_c53`: `X7v5_c53_real` 128 + `X7v5_c53_conv` 64 (ids from `x7v5_custody\X7_SEALED_20261021T060622Z.json` keys `real_drawn_frame_ids_sorted` / `conv_pool_ids_sorted` only; 0 overlap with any older list); 20 lists, 1,850 distinct ids (v5: 18 lists, 1,658); every list applies to BOTH pools |
| Seed bands / owner line | REAL 2,012,000,001-2,013,000,000; CONV 2,014,000,001-2,015,000,000; NOISE 2,016,000,001-2,017,000,000; used table 1-2,011,000,000 (1,996-1,999 M stays reserved for the continuity packet); line to sign **`CHAT WAVE 4 at 1 USD`** (20 UTF-8 bytes); seed = sha256(line + ":" + v6 zip sha256) |
| Status | SEALED, **NOT LAUNCHED**; no exam drawn; no approval record; c53's record stands; v5 `VOID_SUPERSEDED_BY_V6` (`v5_VOID_SUPERSEDED_BY_V6.md`); PR #429 open at the seal (the cut's hash does not change when it is merged) |

What failed while building v6 (negatives kept): (1) the pre-seal wave-7 suite run from the package folder failed once,
`tests_r1w7.test_kit_w7.KitTests.test_runner_refuses_a_key_file_in_the_carrier` (Ran 34, failures=1); the same suite re-run from
the package folder passed (Ran 34, OK) and passed from the sealed extract (Ran 34, OK); the failure did not reproduce and its cause
is not known — recorded, not explained. (2) The builder's own first fix of the pin test (`62d559a8`, PR #427: the pin keyed by brain
folder) was withdrawn by the coordinator's order in favour of PR #428 / #429; PR #427 closed. (3) The peer's first pass `3dae274f`
was found insufficient by this builder's diff (6 leaves still machine-bound; host-path hash `d2e5fb18…`) and superseded by
`ad4fde73`. (4) The amendment text was first spliced into `patch_v6.py` through a shell here-string, which turned backtick-letter
pairs into control bytes; the patch tool's own guard caught it, the package copy was restored from the extract, and the amendment
now lives in a plain file the tool reads (`build\AMENDMENT_A_R1W7_6_BODY.md`); every shell-derived file was scanned for control
bytes (0 left). Decisions recorded: the cut rule names `helm_test_pins.py` explicitly although the `helm_*.py` rule already catches
it (the coordinator asked for it by name); the three pytest-style files stay carried but outside `HELM_TESTS`, as before.

## 13. v8 row (A-R1W7-9, the reseal on the reader v7.1 fix after v7's own practice reading; 2026-10-21, laptop, 0 USD, practice data only)

Section 12 (the v7 row: the reseal on the reader-gap cut with amendments A-R1W7-7 and A-R1W7-8) is on open PR #436
(`claude/helm-r1w7-v7-reseal-20261021`), not on the thread branch when this row was written; its facts are summarised in the
first paragraph below so this file reads on its own.

Why v8 exists: v7 (zip `42c044a9…`, freeze `ce74ccff…`, HELM cut `47440415`, 167 files, the host's list 12 names `Ran 271, OK
(skipped=1)`, A-R1W7-7 applied, block `X7v6_c54`, bands 2,024 / 2,026 / 2,028 M, line `CHAT WAVE 5 at 1 USD`) was sealed and is
VOID FOR LAUNCH: its own practice run from the seal (run9) read mark K3 SAFE false — X7_CONV `CHAT_ON` 59 right / **4 WRONG** / 1
undetermined, X7_NOISE `CHAT_ON` 59 / 4 / 1, X7_CONV `LOOP_ON` 57 / 2 / 5 (v6's run8: 43 / 0 / 21 and 41 / 0 / 23). The four wrong
were the `S1_WISDOM_STATED` items CV32, CV33, CV34, CV37: the clause named the held ingredient by a longer phrase ("the sifted
flour" for a held "flour") or a hyphenated form ("corn-starch" for "corn starch"), the v7 face reader read `FACE_UNREAD` or
`NONE`, and the question answered from the recorded stock as if the clause were unsaid. The fix is reader v7.1 (SPEC 7.113, PR #437,
merged on the thread; head `b10da2cd` after PR #438, a hub-only change): `helm_faces_in.py` v2.1 (longer-phrase name slot resolved
to the held name; hyphen / space variants; two held names → `FACE_WHICH_INGREDIENT`), `helm_wide_turn.py` reader `RB-W1 v7.1` (an
unread clause withdraws the named ingredient's stock on both paths, so the question asks), `test_helm_reader_gap.py` 28 tests,
OFF-path pin `2c8ba0196921e42ab654cd850032ee5da0e5687b60b809e6cbfa337ea6a01a55`. v8 = v7 with exactly two changes: (1) `helm_now/`
recut at `b10da2cd`; (2) amendment A-R1W7-9 (fresh bands and the labels). Everything else is v7's: the 12-name host list, A-R1W7-7 as
applied (same hook, same keys), block `X7v6_c54` as the last exclusion block (no exam drawn since c54), the same owner line (never
bound to v7), reader (`merge_r1w7 v2`), recorder, fixture, marks, thresholds, arms and status words. Built in `build_v8\` from a
fresh extract of v7 (`build_v8\extract_v7\`, never edited); every package edit is an exact once-only replacement
(`build_v8\build\patch_v8.py`, 24 edits, log `PATCH_V8_LOG.json` `d3c0494f…`); A-R1W7-9 = section 21 of the package's
`PREREGISTRATION_R1W7.md` (`AMENDMENT_A_R1W7_9.md` `bad784c5…`).

| Item | v8 |
|---|---|
| Zip | `HELM_R1_W7_20261020_SOURCE_R1W7_v8.zip` sha256 **`e88b125e3079f0fa79045fec888d4e862a5a742cf82010de6872bdc621f865c7`** (1,016,343 bytes; 203 members + the freeze; sealed twice, byte-identical) |
| `PACKAGE_FREEZE.json` | **`50e03e17f7f004b796a464d23cb84935238a413ec67c8ceccdbfa2f3746851fc`**; `FROZEN_R1W7.json` `4369a86587da2b08b26bcadc15ff436a41e6c46c93244b6c059f436f39735529` (`FROZEN_R1W7_v8.json` beside the zip; 14 units) |
| HELM under test | commit `b10da2cd2c78317f5983fa8460ac137c8034556b` (thread head: PR #437 the reader v7.1 fix, then PR #438): `helm_now/` **167 cut files** + `SOURCE_CUT.json` (`CUT_CHECK_W7_v8.json` `e8e25cca…`: 167 of 167 equal to `git show`, 0 extra, contract = source cut); the same 167 names as v7; four files changed: `helm_wide_turn.py` `47994f77…` (reader `RB-W1 v7.1`, the string "v7.1" present 3 times), `helm_faces_in.py` `642451f2…` (v2.1), `test_helm_cas_address.py` `1c330d70…` (`PINNED_OFF_SHA256 = "2c8ba019…"`), `test_helm_reader_gap.py` `cd523303…` (28 `def test_`); `helm_brain_canonical.py` = base `d4488f2a` `24df53c9…` (`canonical_base_equal` true) |
| Ask rule check (`check_ask_prefix_v8.py`, `ASK_PREFIX_CHECK_v8.json` `8ab5556c…`) | the reader's files `score_w7.py` `01fef927…` and `merge_r1w7.py` `3dcb07fa…` byte-identical to v7; every wide status the v8 cut can emit (9: `CLARIFY_WIDE_DISH_NAME_NOT_BOUND`, `_FACE_NEGATED`, `_FACE_NOT_HELD`, `_FACE_REFUSED`, `_FACE_UNKNOWN`, `_FACE_UNREAD`, `_FACE_WHICH_INGREDIENT`, `_INGREDIENT_PURPOSE_ABSENT`, `_PURPOSE_ABSENT`) counts as an ask under RB-W1T's `is_asking` prefix rule; v7.1 added 0 and removed 0 statuses against the v7 cut (`FACE_WHICH_INGREDIENT` was already named in v7; v7.1 makes it reachable); the four non-ask controls stay non-asks |
| Amendment A-R1W7-7 (kept) | `r1w7/custody_w7.py` `fb042b1b…` (identical to v7: the same one import and one hook), `multi_qty_w7.py`, `test_multi_qty_w7.py` carried; the practice draw by the sealed v8 extract (`dry_run\practice_inputs_v8`): 6 of 128 items tagged one line each (`PRACTICE_KEYS_V6_VS_V8.json` `82afee49…`: representable 120 → 114; the same six ids as v7), every other key field equal to v6's, and all 15 practice files byte-identical to v7's `practice_inputs_v7` |
| Exclusions | `contract/EXCLUDE_R1W7_PRIOR_USED.json` `174d0d4d…`, byte-identical to v7 (block `X7v6_c54` the last block; 22 lists, 2,042 distinct ids); no exam was drawn since job c54 |
| Seed bands / owner line | REAL 2,030,000,001-2,031,000,000; CONV 2,032,000,001-2,033,000,000; NOISE 2,034,000,001-2,035,000,000; used table 1-2,029,000,000 (v7's 2,024-2,029 M reserved by the void seal and never drawn; 1,996-1,999 M for the continuity packet and 2,018-2,022 M for the talk packet inside it); line **`CHAT WAVE 5 at 1 USD`** (20 bytes, unchanged from A-R1W7-8, never bound to v7); seed text `sha256(line + ":" + <v8 zip sha256>)` |
| Tests from the sealed extract (`TEST_COUNTS_R1W7_v8.json` `b8d6cf65…`) | 203 of 203 members re-hashed equal; wave-7 suites **Ran 41, OK** (59.5 s; 34 + the amendment's 7); **the host's exact list, 12 names, one process, the host's command form on a scratch copy of the sealed `helm_now/`: `Ran 273 tests in 5.357s`, `OK (skipped=1)`** (v7: 271; the two new tests are the v7.1 cases; the one skip is the base-commit test, as on c54); the OFF pin line `test_off_is_byte_identical_to_the_pre_change_code ... ok`; the sealed `helm_now/` unchanged by the suites |
| Practice run from the v8 seal (`dry_run\run10_v8_from_seal`; inputs `dry_run\practice_inputs_v8`, byte-identical to v7's; 14 units one process at a time; `DRY_RUN_SUMMARY.json` `86a1f6ce…`) | 62.7 s, 14 of 14 exit 0, largest unit 7.547 s, peaks 30.9-60.2 MiB; the dry-run tool's own reading says `INSTRUMENT_ERROR` / `INCONCLUSIVE` on the six practice-mock instrument rows (I0, I1, I6, I7, I9, I10) as designed, with HG5 failing only for the two host rows the tool does not write |
| The same run10 read again with the two host rows supplied (`reread_v8.py`; units untouched; `R1_W7_READING_DRY_WITH_HOST_ROWS.json` `a79150dc…`; `PRACTICE_READINGS_V8.json` `05145247…`) | **HG5 holds: true**; `failing_gates` `[]`; **`marks_missed` `[]` — all six marks true** (K1 98 of 100 fully learned, bar 90; K3 conv_wrong 0, noise_wrong 0, real wrong 0; K4 0 unexplained asks; NH-CHAT lost 0; N 63 / 63 right-and-plain, lost 0, 0 misrouted; P 0 not plain); wave-1 folder equals its sealed freeze after the run (110 of 110); the host rows change no mark and no reported row |
| Practice numbers v8 (run10) beside v7 (run9) and v6 (run8): **32 differing keys against run9, all with one cause (the reader v7.1 fix: inputs, keys and reader files byte-identical); 43 against run8** | X7_CONV `CHAT_ON` **63 right / 0 WRONG / 1 undetermined** (run9 59 / 4 / 1; run8 43 / 0 / 21); `CHAT_ON_REPLAY` and `CHAT_DIAG` the same; `LOOP_ON` 59 / 0 / 5 (57 / 2 / 5; 41 / 0 / 23); `CHAT_OFF` 28 / 0 / 36 in all three; X7_NOISE `CHAT_ON` 63 / 0 / 1 (59 / 4 / 1; 43 / 0 / 21), `CHAT_OFF` 28 / 0 / 36; CHAT_ON minus CHAT_OFF on dialogues +35 right (run9 +31, run8 +15); X7_REAL unchanged from run9 in every arm: `CHAT_ON` RIGHT 103 / WRONG 0 / ASKS 10 / NOT_SCORED 15, 98 of 100 fully learned, 0 unexplained asks; `LOOP_ON` 100 / 0 / 13, 95 of 100 |
| WRONG per dialogue family (`CONV_PER_ITEM_FROZEN_RUN10_VS_RUN9_VS_RUN8.json` `59f85d7d…`, the frozen scorer's own per-item verdicts) | **0 in every family** (R1 14 items, R2 4, R3 4, R4 4, R5 4, R7 2, S1 6, S2 6, S3 6, S4 4, S5 4, S6 2, S7 4) on X7_CONV `CHAT_ON`, `CHAT_ON_REPLAY`, `CHAT_DIAG`, `LOOP_ON` and X7_NOISE `CHAT_ON`; moved run9 → run10: CV32, CV33, CV34, CV37 WRONG → RIGHT on the chat arms and NOISE (4 each), CV34 and CV37 WRONG → RIGHT on `LOOP_ON` (2); no item moved the other way; the one `CHAT_ON` undetermined is CV31 (`R7_NEXT_SESSION`, `UNDETERMINED_CLARIFY`, unchanged since run9); the five `LOOP_ON` undetermined are CV04, CV30, CV31, CV32, CV33 (the loop driven directly still asks on CV32 and CV33, `UNDETERMINED_CLARIFY`, unchanged since run9; the chat answers them right) |
| The CV34 limiting-line mapping (`CV34_LIMITING_LINE_MAPPING_V8.json` `b45473d1…`, by program through the frozen scorer's own functions) | the key names the limiting line by the head **`cracker-crumbs`** (index 1 of `suet`, `cracker-crumbs`, `sugar`, `eggs`, `milk`; yield `1/4`); HELM names it **`cracker crumb`** (singular, a space); RB-W1T's `line_of` maps HELM's name by rule 1, the brain's own admitted lesson records (HELM's record for line 1 says ingredient `cracker crumb`), so the line is 1 = the key's; rule 2 alone (the plural fold of the last word, `crumb` against `cracker-crumb`) would give no hit; value `1/4` = key `1/4`; **the frozen scorer counted it RIGHT** on `CHAT_ON`, `LOOP_ON` and NOISE `CHAT_ON` |
| Status | SEALED, **NOT LAUNCHED**; no exam drawn; no approval record; c54's record stands; v7 `VOID_SUPERSEDED_BY_V8` (`v7_VOID_SUPERSEDED_BY_V8.md`); no practice WRONG remains, so no STOP and no `FLAG_FOR_HUMAN_REVIEW` from this seal; reader v7.1 `ENGINEERED-NOT-VALIDATED` until a sealed draw |

What was decided while building v8 (recorded): (1) the practice draw was made again by the sealed v8 extract's own custody tool
rather than reusing v7's folder, and then shown byte-identical to it, so run10's one cause is the cut; (2) A-R1W7-7 was checked
present in the fresh v7 extract and not re-applied (the apply tool refuses a second application); (3) the exclusion list was not
touched because no exam was drawn after c54; (4) the owner's line was kept as `CHAT WAVE 5 at 1 USD` because A-R1W7-8 proposed it
and no approval record bound it to v7; (5) v7's bands were put into the used table as reserved rather than reused; (6) the ask-rule
check was widened to list every wide status from the source of both cuts by regular expression, instead of a typed list of seven.
Nothing failed while building v8.

## 14. v9 row (A-R1W7-10, the reseal on the reader v7.2 fix after job c55 read CHAT_WAVE_HARMED; 2026-10-21, laptop, 0 USD, practice data only)

Section 12 (the v7 row) is on PR #436, not on the thread branch when this row was written (as section 13 says); section 13 is
the v8 row. This row reads on its own.

Why v9 exists: v8 (zip `e88b125e…`, freeze `50e03e17…`, HELM cut `b10da2cd`, 167 files, the host's list 12 names `Ran 273, OK
(skipped=1)`, A-R1W7-7 applied, block `X7v6_c54`, bands 2,030 / 2,032 / 2,034 M, line `CHAT WAVE 5 at 1 USD`) was sealed, signed,
drawn (X7v8, `x7v8_custody\X7_SEALED_20261021T170704Z.json`) and run once as job c55 (SPEC 7.116): verdict `PASS` (every instrument
row and hard gate true), status word **`CHAT_WAVE_HARMED`** — X7_CONV `CHAT_ON` 62 right / **2 WRONG** / 0 undetermined, X7_NOISE
`CHAT_ON` 62 / 2 / 0, `LOOP_ON` 59 / 2 / 3, and **1 wrong lesson** on a real recipe (real answers 93 of 94 right, 0 wrong; K4 HONEST
true at last, 0 unexplained asks; K1 92 of 94). The per-item replay by program (SPEC 7.116 "Mechanism", 7.117; no exam text read back)
found two mechanisms: (1) a face-shaped clause about an ingredient the brain did not hold under that name (one a plural/spelling form
the matcher did not reach, one sharing nothing with a held name) was read `NONE`, the stock stayed, and the question answered the raw
yield; (2) a measure phrase after a separator ("a dash of X") was folded into the line before it as a note, so X's running-out landed on
that line's ingredient and a wrong amount was learned. The fix is reader v7.2 (SPEC 7.117, PR #447, merged = thread head `55cda1e2`):
`helm_faces_in.py` v2.2 (an unheld subject in a face-shaped clause asks, `FACE_UNKNOWN_INGREDIENT` / `FACE_UNKNOWN_PRODUCT`; `-oes` /
`-ves` / `-o` / `-f` / `-fe` forms), `helm_wide_turn.py` reader `RB-W1 v7.2` (the wide question holds its answer under `wide_face_block`
until the stock is restated; a measure phrase after a separator is its own line; a ran-out phrase resolves through a line's own words
only), `test_helm_reader_gap.py` 35 tests (7 new, 5 failing on v7.1), `test_helm_brain_wide.py` one exact-shape test gains the `own`
key, OFF-path pin `79e4914a561851d2cd19d04902f38e869787e36db0e984302bbbc6c434fa698c`. v9 = v8 with exactly three changes: (1)
`helm_now/` recut at `55cda1e2`; (2) block `X7v8_c55` on the exclusion list; (3) amendment A-R1W7-10 (fresh bands, the new line, the
labels). Everything else is v8's: the 12-name host list, A-R1W7-7 as applied (same hook, same keys), reader (`merge_r1w7 v2`), recorder,
fixture, marks, thresholds, arms and status words. Built in `build_v9\` from a fresh extract of v8 (`build_v9\extract_v8\`, never
edited); every package edit is an exact once-only replacement (`build_v9\build\patch_v9.py`, 30 edits, log `PATCH_V9_LOG.json`
`b372c53e…`); A-R1W7-10 = section 22 of the package's `PREREGISTRATION_R1W7.md` (`AMENDMENT_A_R1W7_10.md` `6c605d30…`).

| Item | v9 |
|---|---|
| Zip | `HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip` sha256 **`ad3fb98cd3254963263929747791d151949c2f50923672e4bcbf3fc14490942c`** (1,022,659 bytes; 203 members + the freeze; sealed twice, byte-identical) |
| `PACKAGE_FREEZE.json` | **`ce9495fafd5507d1c2b1dbc0c6b00df4305034393720ef21528af1f210581355`**; `FROZEN_R1W7.json` `30ed56d08394639b0c55bea60d32688f087696bc3eb659ce69b4fb18728a9dd4` (`FROZEN_R1W7_v9.json` beside the zip; 14 units) |
| HELM under test | commit `55cda1e21f7e6ea0048fe2faf7e90f23e4ec9525` (thread head: PR #447 the reader v7.2 fix): `helm_now/` **167 cut files** + `SOURCE_CUT.json` (`CUT_CHECK_W7_v9.json` `efccfe62…`: 167 of 167 equal to `git show`, 0 extra, contract = source cut); the same 167 names as v8; five files changed: `helm_wide_turn.py` `c9e8a078…` (reader `RB-W1 v7.2`, the string "v7.2" present 7 times), `helm_faces_in.py` `2f7d4b57…` (v2.2), `test_helm_brain_wide.py` `8ad4a0ba…`, `test_helm_cas_address.py` `06889a63…` (`PINNED_OFF_SHA256 = "79e4914a…"`), `test_helm_reader_gap.py` `3eed47af…` (35 `def test_`); `helm_brain_canonical.py` = base `d4488f2a` `24df53c9…` (`canonical_base_equal` true) |
| Ask rule check (`check_ask_prefix_v9.py`, `ASK_PREFIX_CHECK_v9.json` `9b7795c8…`) | the reader's files `score_w7.py` `01fef927…` and `merge_r1w7.py` `3dcb07fa…` byte-identical to v8; every wide status the v9 cut can emit, read from the source of both cuts by regular expression (the forms widened for v7.2's `code = "…" if … else "…"`): **11** (v8's 9 + `CLARIFY_WIDE_FACE_UNKNOWN_INGREDIENT` + `CLARIFY_WIDE_FACE_UNKNOWN_PRODUCT`), every one begins `CLARIFY` and counts as an ask under RB-W1T's `is_asking`; v7.2 removed 0; the four non-ask controls stay non-asks |
| Amendment A-R1W7-7 (kept) | `r1w7/custody_w7.py` carries the same one import and one hook (the file changes only in `REAL_EXCLUDE_LISTS`, the two new names); the practice draw by the sealed v9 extract (`dry_run\practice_inputs_v9`): 6 of 128 items tagged one line each (`PRACTICE_KEYS_V6_VS_V9.json` `82afee49…`, identical to v8's: representable 120 → 114, the same six ids), and all 15 practice files byte-identical to v8's `practice_inputs_v8` |
| Exclusions | `contract/EXCLUDE_R1W7_PRIOR_USED.json` `1435f485…` (v8: `174d0d4d…`): new block `X7v8_c55` = `X7v8_c55_real` (128) + `X7v8_c55_conv` (64), read by program from the custodian's seal record (ids only; never an input or key file), 0 overlap with every older list; 24 lists, 2,234 distinct ids (v8: 22 lists, 2,042) |
| Seed bands / owner line | REAL 2,036,000,001-2,037,000,000; CONV 2,038,000,001-2,039,000,000; NOISE 2,040,000,001-2,041,000,000; used table 1-2,035,000,000 (v8's 2,030-2,035 M spent by c55; v7's 2,024-2,029 M reserved by the void v7 seal; 1,996-1,999 M and 2,018-2,022 M reserved inside it); line to sign **`CHAT WAVE 6 at 1 USD`** (20 bytes; proposed by A-R1W7-10; the owner's own typed word decides); seed text `sha256(line + ":" + <v9 zip sha256>)` |
| Tests from the sealed extract (`TEST_COUNTS_R1W7_v9.json` `d9c33d6f…`) | 203 of 203 members re-hashed equal; wave-7 suites **Ran 41, OK** (63.5 s); **the host's exact list, 12 names, one process, the host's command form on a scratch copy of the sealed `helm_now/`: `Ran 280 tests in 5.254s`, `OK (skipped=1)`** (v8 seal and c55 host: 273; the seven new tests are v7.2's; the one skip is the base-commit test, as on c55); the OFF pin line `test_off_is_byte_identical_to_the_pre_change_code ... ok`; the sealed `helm_now/` unchanged by the suites |
| Practice run from the v9 seal (`dry_run\run11_v9_from_seal`; inputs `dry_run\practice_inputs_v9`, byte-identical to v8's; 14 units one process at a time) | 60.0 s, 14 of 14 exit 0, largest unit 7.597 s, peaks 30.8-60.1 MiB; the dry-run tool's own reading says `INSTRUMENT_ERROR` / `INCONCLUSIVE` on the six practice-mock instrument rows (I0, I1, I6, I7, I9, I10) as designed, with HG5 failing only for the two host rows the tool does not write |
| The same run11 read again with the two host rows supplied (`reread_v9.py`; units untouched; `PRACTICE_READINGS_V9.json` `041dc851…`) | **HG5 holds: true**; `failing_gates` `[]`; **`marks_missed` `[]` — all six marks true** (K1 98 of 100 fully learned, bar 90; K3 conv_wrong 0, noise_wrong 0, real wrong answers 0, wrong lessons 0; K4 0 unexplained asks; NH-CHAT lost 0; N 63 / 63 right-and-plain, lost 0, 0 misrouted; P 0 not plain); wave-1 folder equals its sealed freeze after the run (110 of 110); the host rows change no mark and no reported row |
| Practice numbers v9 (run11) beside v8 (run10) and v7 (run9): **0 differing keys against run10** (inputs, keys and reader files byte-identical; the v7.2 fix touches shapes the practice dialogues never show); 32 against run9, every one the reader v7.1 fix already listed in `PRACTICE_READINGS_V8.json` | X7_CONV `CHAT_ON` **63 right / 0 WRONG / 1 undetermined** (run10 63 / 0 / 1; run9 59 / 4 / 1); `CHAT_ON_REPLAY` and `CHAT_DIAG` the same; `LOOP_ON` 59 / 0 / 5 (59 / 0 / 5; 57 / 2 / 5); `CHAT_OFF` 28 / 0 / 36 in all three; X7_NOISE `CHAT_ON` 63 / 0 / 1 (63 / 0 / 1; 59 / 4 / 1), `CHAT_OFF` 28 / 0 / 36; CHAT_ON minus CHAT_OFF on dialogues +35 right; X7_REAL every arm equal to run10: `CHAT_ON` RIGHT 103 / WRONG 0 / ASKS 10 / NOT_SCORED 15, 98 of 100 fully learned, 0 unexplained asks, 0 wrong lessons; `LOOP_ON` 100 / 0 / 13, 95 of 100 |
| WRONG per dialogue family (`CONV_PER_ITEM_FROZEN_RUN11_VS_RUN10_VS_RUN9.json` `6cb838dd…`, the frozen scorer's own per-item verdicts) | **0 in every family** (R1 14 items, R2 4, R3 4, R4 4, R5 4, R7 2, S1 6, S2 6, S3 6, S4 4, S5 4, S6 2, S7 4) on X7_CONV `CHAT_ON`, `CHAT_ON_REPLAY`, `CHAT_DIAG`, `LOOP_ON` and X7_NOISE `CHAT_ON`; no item moved between run10 and run11 on any arm; the one chat undetermined is CV31 (`R7_NEXT_SESSION`); the five `LOOP_ON` undetermined are the same five as run10 (R1 1, R7 2, S1 2: the loop driven directly still asks on CV32 and CV33 where the chat answers right) |
| Status | SEALED, **NOT LAUNCHED**; no exam drawn; no approval record; c55's record stands; v8 `VOID_SUPERSEDED_BY_V9` (`v8_VOID_SUPERSEDED_BY_V9.md`); no practice WRONG remains, so no STOP and no `FLAG_FOR_HUMAN_REVIEW` from this seal; reader v7.2 `ENGINEERED-NOT-VALIDATED` until a sealed draw |

What was decided while building v9 (recorded): (1) the practice draw was made again by the sealed v9 extract's own custody tool
and shown byte-identical to v8's, so run11's only possible cause of change was the cut, and it changed nothing; (2) A-R1W7-7 was
checked present in the fresh v8 extract and not re-applied; (3) the exclusion block was added from the custodian's seal record only
(ids), with a 0-overlap refusal built into the adder; (4) the line `CHAT WAVE 6 at 1 USD` was written in as proposed by §7.117 —
nothing here approves it; (5) v8's bands were put into the used table as spent (c55 drew them); (6) the ask-rule check's regular
expressions were widened to read v7.2's conditional code assignment, and both cuts were read with the same widened forms; (7)
section 13 of this file is v8's row, so this row is section 14. Nothing failed while building v9; the practice numbers did not move,
which is expected, since c55's two wrong items were shapes the practice dialogues do not contain, and is also why a fresh sealed
draw can still miss a mark on a shape no practice run has shown.
