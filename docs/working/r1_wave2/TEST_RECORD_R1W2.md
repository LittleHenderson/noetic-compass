# TEST_RECORD_R1W2 - what was tested on the laptop before the seal (2026-10-18, Pacific)

Laptop MSI, Windows 11, Python 3.14.0. Pure Python only, one process at a time (the laptop-RAM rule). No AWS, no
spend, no torch. Torch parts: NOT_RUN_HERE (GB3's `world()` regeneration of X1's Gate B worlds, host only).

## 1. Every suite, run from the EXTRACTED SEALED ZIP (`build/test_from_seal.py`)

| Suite | Result | Exit | Wall |
|---|---|---|---|
| `cube_store/test_all.py` | 19 of 19 cases passed (ALL PASS) | exit 0 | 0.23 s |
| `helm.test_helm_chat_nuance (pytest)` | pytest 5 passed | exit 0 | 1.13 s |
| `helm.test_helm_end_to_end_loop` | Ran 18; OK | exit 0 | 0.81 s |
| `helm.test_helm_english_in` | Ran 31; OK | exit 0 | 0.65 s |
| `helm.test_helm_triad` | Ran 15; OK | exit 0 | 0.54 s |
| `helm.test_helm_voice` | Ran 22; OK | exit 0 | 0.86 s |
| `language_v3.test_lexicon_v2` | Ran 19; OK | exit 0 | 0.52 s |
| `language_v3.test_lm_t1` | Ran 26; OK | exit 0 | 0.66 s |
| `language_v3.test_lm_t1b` | Ran 11; OK | exit 0 | 0.29 s |
| `language_v3.test_lm_t1c` | Ran 5; OK | exit 0 | 0.2 s |
| `language_v3.test_lm_t1v3` | Ran 26; OK | exit 0 | 0.86 s |
| `r1w2.test_kit_r1w2` | Ran 9; OK | exit 0 | 0.43 s |
| `r1w2.test_run_r1w2 (AWS only)` | Ran 4; OK (skipped=4) | exit 0 | 0.24 s |
| `r1w2.test_units_r1w2` | Ran 25; OK | exit 0 | 3.9 s |
| `repair_performer/test_all.py` | 16 of 16 cases passed (ALL PASS) | exit 0 | 1.6 s |
| `the_loop_v3/test_all.py` | 35 of 35 cases passed (ALL PASS) | exit 0 | 0.68 s |
| `wave1 carried (v3 folder)` | Ran 128; OK | exit 0 | 71.5 s |

**Totals: 410 passed, 4 skipped (the AWS-only host tests, by their guard), 0 failed** (wave 2 34 + HELM live modules 91
+ language_v3 87 + council scripts 70 + wave 1 carried 128).

**One failure found and fixed before the final seal.** The first seal (zip `c6db9556ae584f21322080d5c4e4aa356cc5d3c3fdf98aee0f1783cc2ba3bddb`,
freeze `db952957...`) failed `test_helm_end_to_end_loop.TestValveRule.test_13_written_rule`: the test checks that the old
valve weights file is kept beside the loop as history, and the cut had left `tks_meta_valve_weights_v0_4.json` out.
The cut now includes it (git blob, never loaded), the package was resealed, and every suite above was rerun from the
NEW sealed zip. The first seal was never signed or shipped; it is void. Only the hash in the sign request is the
package.

## 2. The c34-g supervisor fix (inside section 1's kit suite; listed here because the owner's order names it)

| Test | What it proves |
|---|---|
| `test_c34g_fixtures_are_the_real_bytes` | the fixtures are c34-g's own plan `b66adf88…`, runner `53fb28e5…` and supervisor receipt `b561d67b…` (stage FAIL with exit code 0, both outputs "missing") |
| `test_plan_check_names_the_c34g_defect` | `kit/plan_check.py` on c34-g's plan + runner: FAIL, naming "not under the runner's kept folder 'r1w1_out'/" and ".sha256 suffix not kept" |
| `test_plan_check_passes_the_wave2_pair` | `kit/STAGE_R1W2.json` + `kit/run_r1w2.py`: PASS (kept folder `r1w2_out`, `.sha256` kept) |
| `test_check_required_outputs_finds_nested_and_names_misplaced` | the supervisor finds nested outputs with their sha256, and names `r1w2_out/R1_W2_HOST.json` when a plan declares it at the root |
| `test_supervisor_run_stage_passes_the_wave2_declaration` | the supervisor's own `run_stage` on a real command stage that writes like the runner: PASS, no missing outputs, both found |
| `test_supervisor_run_stage_reproduces_c34g_with_the_old_declaration` | the same stage with c34-g's kind of declaration: exit 0 yet FAIL, and the misplaced file is named: c34-g reproduced, then fixed |
| `test_runner_keeps_the_sidecar` | the runner copies `.sha256` sidecars (c34-g's filter dropped them) |
| `test_wave2_stage_is_a_valid_plan_stage` | `kit/STAGE_R1W2.json` passes the supervisor's own `validate_plan`; its runner path exists |
| `test_launch_window_and_runner_constants` | window 6,660 s; the wave-1 host test (T reruns) is not repeated |

Correction found while measuring (recorded in spec sheet §7.63, §7.47 not edited): c34-g's runner DID write
`R1_W1_HOST.json.sha256` (its `RUN_RECORD.json` lists it under `r1w1_output_files` and `not_copied`); the copy filter
`('.json', '.md', '.log')` left it behind.

## 3. The receiver's check (what X1 must pass before its seal)

`r1w2/check_x1_format.py` (runs wave 1's own `r1/check_fresh_format.py` plus the English-16 check), and the unit tests
`TestReceiverCheck` (laptop only): on X0's ORIGINAL custodian files it reports FAIL for exactly
`CCE_PLANTED_W1.json`, `D34_FRESH_TaskB_d3.json`, `D34_FRESH_TaskB_d4.json` (the §7.46 finding, reproduced); on the
coordinator's converted copies it reports `all_pass: true`. Record: `X0_RECHECK_20261018.json`.

## 4. The depth adapter (laptop stage of E3)

`python -B -m r1w2.d34_x1 part --part D00 ...` (wave 1's own depth code, its identity part, exposed data):
COMPLETED in 35.13 s, 10 / 10 code tests, `identity_D00.ok: true` (LSR_TODAY 16 / 16 and A1_RF 16 / 16 state hashes
equal rb_c4's), and wave 1's `merge_d34.py` ran unchanged on the wave-2 runs folder. `preflight`: wave 1's d34
`SOURCE_MANIFEST.json` (`59f1be24…`) re-hashed, 197 of 197 files match.

## 5. English-16 on the builder's FIXTURE (plumbing only, never scored)

16 builder-written items (`tests_r1w2/fixtures/E16_FIXTURE.json`), through the packaged live loop with the canonical
brain loaded from the wave-1 v3 folder: FULL 16 RIGHT / 0 WRONG / 0 UNDETERMINED, PLAIN 16, FACT_KEPT 9 of 9;
-TRIAD identical structure; -ENGLISH_IN 5 RIGHT / 0 WRONG / 11 UNDETERMINED; -VOICE identical structure, PLAIN 7 (the
old adapter text says "receipt" and shows the checked-form example); FULL replay identical record for record. These
numbers are about the harness, not about HELM: the fixture was written by the builder, who can see the reader's
shapes. The scored items come from the custodian.

## 6. Pins, sidecar, reader on nothing

`load_pins` refuses wave 1's schema, a missing slot, a missing owner seed source and an unknown slot; the sidecar is
`<sha256>  <name>\n`; the reader on empty inputs says `INSTRUMENT_ERROR` with no word licensed (missing data is never a
pass).

## 7. Laptop DRY RUN of the whole host pool on EXPOSED data (`build/dry_run_r1w2.py`)

One unit at a time on the laptop; E1 (c21's sealed worlds) and E2 (RB2c's worlds) exactly as the host will run them; 'E3' = X0 (exposed since c34-g; the coordinator's contract-format copies); E4 = the builder's fixture; depth = the D00-only dry reading; I5 a labelled fixture (no torch).

- Units: 68 planned, 68 exit 0, not ok []; 391.9 s wall in all (the slowest units are the two A1_RM Task B teaches).
- FULL on E1 reproduces c23 RB-det (wave 1's I3a, all 8 parts): True; FULL on E2 reproduces c26 RB-det on every draw (I3b every_draw_equal): True, draws equal 20 of 20, medians 16 / 16: True.
- FULL on 'E3' (X0) reproduces c34-g's A1 Task B labels on every draw: True; Gate B new-world labels equal c34-g's: True.
- Hard gates that do not need X1 or the depth panel: H3 replay {'E1_GB_C21': True, 'E2_TB_C25': True, 'E3_GB_X1': True, 'E3_TB_X1': True, 'E4_ENGLISH16': True, 'depth': False}; H4 restart {'E1_GB_C21': True, 'E2_TB_C25': True, 'E3_GB_X1': True, 'E3_TB_X1': True}; H8 {'triad_at_peak_is_identity': True, 'voice_never_changes_the_answer': True}.
- The reader's verdict on this dry input: `INSTRUMENT_ERROR` (as designed: exposed 'fresh' exam, no X1 pins, no depth panel, no approval record); no word licensed. Words it would print on these EXPOSED and FIXTURE inputs (NOT results, shown only to prove the reader runs end to end): {'CCE_SKIN': 'NEUTRAL', 'ENGLISH_IN': 'EARNED_KEEP', 'LACUNA_CADENCE': 'EARNED_KEEP', 'RECIPE_MATH': 'EARNED_KEEP', 'RESTART_FALLBACK': 'INCOMPLETE', 'RPM_GATE': 'INCOMPLETE', 'TRIAD': 'NOT_EXERCISED', 'VOICE': 'EARNED_KEEP'}.
- Reading sha256 (dry): `0d706ef5b653e9f5efd9e84b607af9f7fa48ee35a035b05c2b4208e6380d3a08`.

## 8. What was NOT run here

- The host test `tests_r1w2/test_run_r1w2.py` (4 tests): AWS only, SKIPPED here by its guard (as designed).
- Torch: the X1 Gate B regeneration (I5). NOT_RUN_HERE.
- The 19 depth parts D01-D19: they need X1's depth files.
- Anything on X1: it does not exist yet.
