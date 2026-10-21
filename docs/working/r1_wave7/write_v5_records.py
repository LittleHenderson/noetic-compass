"""Builder tool (NOT sealed): the v4 void note (beside the v4 zip) and the v5 row of TEST_RECORD_R1W7.md (the repo copy is
the live file; a copy is written beside the v5 zip).

    python -X utf8 -B -I write_v5_records.py <r1_wave7 dir> <repo TEST_RECORD_R1W7.md>
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
TR = Path(sys.argv[2]).resolve()

VOID = """# v4 of the wave 7 CHAT WAVE package is VOID_SUPERSEDED_BY_V5 (2026-10-20)

- The v4 zip `HELM_R1_W7_20261020_SOURCE_R1W7_v4.zip` (sha256 `8602b1bc98b543e4551e766d9db540d22d6dbc690b788dbbce5c91e4b6c7b712`,
  freeze `948cf6913963f5fe06ab87b46e2ebcf03c3f541433877e04bda666d6e429f072`) stays exactly where it is: job c52's record
  (`run_c52_r1w7v4_20261020/RUN_RESULT_R1W7V4_C52.md`, reading `bcb2f372...`) points at it and that record stands as written
  (verdict `PASS`, word `CHAT_WAVE_NO_GAIN`, K4 missed by one unexplained ask, nothing licensed). Nothing here was deleted,
  moved or renamed.
- v4 must never be shipped, sealed by a custodian, or scored again: the owner's v4 line `CHAT WAVE 2 at 1 USD` was consumed by
  c52's approval record (`approval_v4/APPROVAL_RECORD_R1W7.json` `9e4058a9...`), v4's seed bands 2,000-2,005 M were spent by
  the X7v4 draw, and v4's HELM cut `dfc7158d` carries the wide-reader fault that produced the K4 miss (amendment A-R1W7-5).
- The package for the third round the owner ordered ("third chat round") is **v5**:
  `HELM_R1_W7_20261020_SOURCE_R1W7_v5.zip` sha256 `4b54a077e4b2963301451c6eb78836a32d9797460cd8143d3cf2f9efdc1a7cf8`,
  freeze `PACKAGE_FREEZE_R1W7_v5.json` `8cc543d2102951c79e897f478bc31781e87c511d0a24be54cbf92611ce2bbfd1`, built in
  `build_v5\\` from a fresh extract of v4 (`build_v5\\extract_v4\\`, never edited), HELM cut `f45a8570` (FIX FIRST round 3,
  PR #425). v5 is SEALED, NOT LAUNCHED; it waits for the owner's new line `CHAT WAVE 3 at 1 USD`.
"""

ROW = """
## 10. v5 row (A-R1W7-5, FIX FIRST round 3 on c52's one unexplained ask; 2026-10-20, laptop, 0 USD, practice data only)

Why v5 exists: v4 ran as job c52 and the frozen reader said `PASS` / `CHAT_WAVE_NO_GAIN`: every hard gate held, K4 HONEST was
missed by exactly one unexplained ask, the same in LOOP_ON. The owner ordered a "third chat round". The item was found by program
in the unit outputs (`K4_ITEM_DIAGNOSIS.md` beside the zip; id only, never the text): a batch or stock sentence carrying an amount
of a condition (a temperature) after an ingredient line; the wide reader cut the sentence there and bound the piece as an
ingredient, so the brain waited for a batch where that "ingredient" ran out and asked. Fixed in HELM as one general rule
(`helm_wide_turn.condition_fragment`; PR #425, commit `f45a8570`; test class G 3 of 3 fail on `1d2b390f`, 3 of 3 pass). v5 =
v4 with `helm_now/` recut at the fix, block `X7v4_c52` excluded, fresh bands and a new line; reader, recorder, fixture, marks,
thresholds, arms and words unchanged. Built in `build_v5\\` from a fresh extract of v4 (`build_v5\\extract_v4\\`, never edited);
every package edit is an exact once-only replacement (`build_v5\\build\\patch_v5.py`, log `PATCH_V5_LOG.json`, 31 edits);
amendment A-R1W7-5 = section 17 of the package's `PREREGISTRATION_R1W7.md`.

| Item | v5 |
|---|---|
| Zip | `HELM_R1_W7_20261020_SOURCE_R1W7_v5.zip` sha256 **`4b54a077e4b2963301451c6eb78836a32d9797460cd8143d3cf2f9efdc1a7cf8`** (980,035 bytes; 198 members + the freeze; resealed byte-identical) |
| `PACKAGE_FREEZE.json` | **`8cc543d2102951c79e897f478bc31781e87c511d0a24be54cbf92611ce2bbfd1`**; `FROZEN_R1W7.json` `f71ab86a...` (`FROZEN_R1W7_v5.json` beside the zip) |
| HELM under test | commit `f45a85706a9d8b9177e4b7279453d1538c12045d` (PR #425 to the thread, 1 commit on `1d2b390f`): `helm_now/` 164 cut files + `SOURCE_CUT.json` (`CUT_CHECK_W7_v5.json` 164 of 164 equal to `git show`, 0 extra; cut `7465b615...`); +3 files vs v4 by the contract's own rule (`helm_cas_address.py`, imported by the loop since `9916d7da`, switch default OFF; `test_helm_cas_address.py`; `test_helm_units_note.py`); `helm_brain_canonical.py` = base `24df53c9...`; byte copies `kit/plan_check.py` `84257a23...` and `kit/job_supervisor.py` `3b2337ca...` unchanged |
| Tests from the sealed extract (`TEST_COUNTS_R1W7_v5.json` `d6dda0da...`) | wave-7 suites **Ran 34, OK** (66.1 s; pre-seal Ran 34 OK with 2 skipped); HELM's 8 unittest files on a scratch copy **Ran 204, OK** (skipped 1; 4.6 s; v4 201: +3 class G tests); the host's 10-file list (`kit/run_r1w7.py` `HELM_TESTS`, now + `test_helm_cas_address`, `test_helm_units_note`) on the same scratch copy **Ran 236, OK** (skipped 1); 198 / 198 members re-hashed; `helm_now/` unchanged by the suites |
| Practice run from the v5 seal (`dry_run\\run7_v5_from_seal`, 14 units one process at a time, 65.5 s, 14 of 14 exit 0, largest unit 8.3 s, peaks 31.6-60.8 MiB; `DRY_RUN_SUMMARY.json` `61445386...`, `R1_W7_READING_DRY.json` `a2985266...`) | verdict `INSTRUMENT_ERROR` / `INCONCLUSIVE` as designed for a practice mock (I0, I1, I6, I7, I9, I10 false); every mark met (`marks_missed` `[]`); HG5 unit rows 14 of 14 carry `[]`, missing list empty |
| The same run7 read again with the two host rows supplied (`reread_v5.py`; units untouched; `R1_W7_READING_DRY_WITH_HOST_ROWS.json` `75b529ba...`; `PRACTICE_READINGS_V5.json` `2c1c5bbf...`) | **HG5 holds: true**; `failing_gates` `[]`; wave-1 folder equals its sealed freeze after the run (110 of 110 members, 0 extra); `canonical_brain_equals_base` true; marks and every reported row identical to the as-run reading |
| Practice numbers v5 (run7) beside v4 (run6) | **0 differing keys** across marks, mark parts, totals, noise and stock rows (`v5_minus_v4_practice_differences` `[]`): the practice draw holds no condition-shaped line, so the fix changes nothing there. CHAT_ON REAL: RIGHT 103 / WRONG 0 / ASKS 10 / NOT_SCORED 15, RIGHT_AND_PLAIN 103, fully learned 102 of 106 (bar 96), lessons LEARNED 594 / NOT_LEARNED 76, unexplained asks 0 (strict 0), unrouted 0, commitments on undetermined 12; LOOP_ON REAL 100 / 0 / 13 / 15, learned 99, unexplained 0; CHAT_OFF REAL 0 / 0 / 113 / 15, NOT_LEARNED 670, unrouted 10; CONV CHAT_ON 43 / 0 / 21 undetermined (LOOP_ON 41 / 23; CHAT_OFF 28 / 36, misrouted 10, unrouted 7); NOISE CHAT_ON 43 / 0 / 21, 128 noise turns, 0 misrouted (CHAT_OFF 28, misrouted 10); K1 102 of 106 ✓, K3 0/0/0/0 ✓, K4 0 ✓, NH-CHAT lost 0 REAL (103 vs 100, gained 3) and 0 CONV (43 vs 41, gained 2) ✓, P 0 not plain ✓, N lost 0 ✓; stock turns CHAT_ON STOCK_RECORDED 115, UNKNOWN_INGREDIENT 9, NO_INGREDIENT_NAMED 2, NO_STOCK_FRAME 1, INVENTORY_RECORDED 1 — every number equal to v4's run6 |
| Exclusions (`contract/EXCLUDE_R1W7_PRIOR_USED.json` `4c9dcf84...`) | block `X7v4_c52`: `X7v4_c52_real` 128 + `X7v4_c52_conv` 64 (ids from `x7v4_custody\\X7_SEALED_20261021T050521Z.json` only; 0 overlap with any older list); 18 lists, 1,658 distinct ids (v4: 16 lists, 1,466); every list applies to BOTH pools |
| Seed bands / owner line | REAL 2,006,000,001-2,007,000,000; CONV 2,008,000,001-2,009,000,000; NOISE 2,010,000,001-2,011,000,000; used table 1-2,005,000,000 (1,996-1,999 M stays reserved for the continuity packet); line to sign **`CHAT WAVE 3 at 1 USD`** (20 UTF-8 bytes); seed = sha256(line + ":" + v5 zip sha256) |
| Status | SEALED, **NOT LAUNCHED**; no exam drawn; no approval record; c52's record stands; v4 `VOID_SUPERSEDED_BY_V5` (`v4_VOID_SUPERSEDED_BY_V5.md`) |

What failed while building v5: nothing in the package. Two decisions recorded: (1) the cut is 164 files, not 161, because the
contract's own rule ("+ every helm_*.py / test_helm_*.py at the commit") picks up the three files that entered the thread after
v4's cut, and the loop imports one of them; (2) the wide reader's version string was left as is because `test_helm_cas_address`
pins the OFF-path trace bytes (the rule itself is documented in the reader's header). One limit kept as a negative in the
diagnosis: the same stock sentence with plain unit words and the temperature in the middle is claimed first by the licensed
English reader's stock-frame rule and is not recorded; that is the licensed reader's own rule, not the c52 cause, unchanged.
"""

(ROOT / "v4_VOID_SUPERSEDED_BY_V5.md").write_text(VOID, encoding="utf-8", newline="\n")
t = TR.read_text(encoding="utf-8")
if "## 10. v5 row" in t:
    raise SystemExit("already has the v5 row")
old = "# TEST RECORD — HELM-R1 wave 7, the CHAT WAVE, v3 (FIX FIRST round 2) and v4 (reader repair, section 9; builder, laptop, 0 USD; practice data only)"
if t.count(old) != 1:
    raise SystemExit("title not found")
t = t.replace(old, "# TEST RECORD — HELM-R1 wave 7, the CHAT WAVE, v3 (FIX FIRST round 2), v4 (reader repair, section 9) and v5 (FIX FIRST round 3, section 10; builder, laptop, 0 USD; practice data only)")
if not t.endswith("\n"):
    t += "\n"
TR.write_text(t + ROW, encoding="utf-8", newline="\n")
shutil.copyfile(TR, ROOT / "build_v5" / "TEST_RECORD_R1W7.md")
print("written")
