
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
