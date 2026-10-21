
## 20. Amendment A-R1W7-8 (v7, written BEFORE the v7 reseal; the fifth chat round on the reader-gap cut: four changes, nothing else; 2026-10-21)

**Why.** The v6 package (zip `387577deac79d8b395e1e3245cd3bb1bdddb20b0b21b86f1078e7a0cd20442f8`, freeze `3c7a9f3d…`,
HELM cut `ad4fde73`) ran on the host as job c54 (`RUN_RESULT_R1W7V6_C54.md`; reading `R1_W7_READING.json`; SPEC 7.108).
The frozen reader said verdict `PASS`, status word `CHAT_WAVE_NO_GAIN`: the first run of the four with a clean instrument end
to end (8 of 8 instrument rows, 10 of 10 hard gates, HELM's 11-file suite `Ran 245, OK (skipped=1)` on the host), 5 of 6
marks true, **K4 missed by 2 unexplained asks** on real recipes (the same 2 in the loop driven directly: the wide reader, not
the chat). The per-item diagnosis by program (SPEC 7.109; no exam text pasted) found both asks to be one book line holding
two amounts, which the frozen key keeps as one lesson and the wide reader reads as two; the owner said yes to the custodian's
MULTI_QTY rule (A-R1W7-7, section 19) and ordered the reader-gap designs D1–D5 built FIX FIRST (SPEC 7.111, PR #435, merged
as thread head `47440415`). Line 4 of this document forbids re-reading c54's data; the c54 word stands. **v6 is
`VOID_SUPERSEDED_BY_V7`** for any further run (its c54 record stands as written; its line `CHAT WAVE 4 at 1 USD` was
consumed by c54's approval record; its bands 2,012–2,017 M were spent by the X7v6 draw).

**What changed in this package (v7). Exactly these four, nothing else.**

1. **`helm_now/` recut at `4744041503ca6feb044afa05cbb380533de2fcfe`** (the thread head: PR #435 merged, the reader-gap
   build of SPEC 7.111) by the contract's rule (the v6 cut's 166 files + every `helm_*.py` / `test_helm_*.py` at the commit;
   `helm_test_pins.py` named explicitly as in v6; each by `git show`, never the working tree): **167 files** (v6: 166;
   + `test_helm_reader_gap.py`, 26 tests; `helm_wide_turn.py` → reader `RB-W1 v7 (2026-10-21)` `05dcc16e…`,
   `helm_faces_in.py` → v2 `c034bb66…`, `test_helm_wide_alongside.py` and `test_helm_cas_address.py` changed — the OFF-path
   pin is now `83f96a4a3e64256f0cae1c5567285463f442f92f1c4759e6b2c7bdd397502c35` over the same machine-neutral canon; every
   other file equal to v6's cut; `helm_brain_canonical.py` = base `d4488f2a` `24df53c9…`). `contract/HELM_CUT_R1W7.json`
   carries the commit and all 167 hashes. The wide reader's new ask statuses (`CLARIFY_WIDE_PURPOSE_ABSENT`,
   `CLARIFY_WIDE_INGREDIENT_PURPOSE_ABSENT`, `CLARIFY_WIDE_FACE_UNREAD` / `_NEGATED` / `_WHICH_INGREDIENT` / `_REFUSED` /
   `_UNKNOWN`) count as asks under RB-W1T's prefix rule (`keys_rbw1t.is_asking`: every status beginning `CLARIFY` is an
   ask), which the reader uses through wave 6's `score_real`; the reader's rules are not changed.
2. **The host's HELM self-check list** (`kit/run_r1w7.py` `HELM_TESTS`): the 11 names of v6 + `test_helm_reader_gap` =
   **12 names**, one process, the same command form as c54. The A-R1W7-6 rule is kept: the seal step runs exactly that
   list with that command form from a fresh extract and records it in `TEST_COUNTS_R1W7_v7.json` under
   `host_exact_suite_list`, refusing unless the sealed kit's list equals the tool's typed copy. The three pytest-style
   files stay carried but not run as unittest suites.
3. **Amendment A-R1W7-7 applied** (section 19): `r1w7/multi_qty_w7.py`, `tests_r1w7/test_multi_qty_w7.py` (7 tests, now
   part of the package's own suite run from the seal), one import and one hook in `custody_w7.make_all`; measured effect on
   the practice draw 6 of 128 items `NOT_SCORED` (section 19.5).
4. **Exclusions, bands, line.** `contract/EXCLUDE_R1W7_PRIOR_USED.json` gains block `X7v6_c54` = lists `X7v6_c54_real`
   (X7v6's 128 REAL ids) and `X7v6_c54_conv` (64 CONV pool ids), read by program from the custodian's seal record
   `x7v6_custody/X7_SEALED_20261021T140909Z.json` (keys `real_drawn_frame_ids_sorted` / `conv_pool_ids_sorted`; ids only; no
   input, key or exam file opened); 0 overlap with any older list; every list applies to BOTH pools (A-R1W7-4 rule kept):
   22 lists, 2,042 distinct ids. **Seed bands** (section 10 superseded again): REAL 2,024,000,001-2,025,000,000; CONV
   2,026,000,001-2,027,000,000; NOISE 2,028,000,001-2,029,000,000 (each 1,000,000 wide; below INT32_MAX 2,147,483,647). Used
   table 1-2,023,000,000 as one range (everything up to wave 7 v6 / c54's 2,012-2,017 M, spent by the X7v6 draw; the
   continuity packet's reserved 1,996-1,999 M and the talk packet's reserved 2,018-2,022 M inside it); gap 1,000,000; slot
   stepping and STOP as before. **The owner's line** (section 8 superseded again): **`CHAT WAVE 5 at 1 USD`** (20 UTF-8
   bytes; `CHAT WAVE at 1 USD` was consumed by c51's approval record, `CHAT WAVE 2 at 1 USD` by c52's, `CHAT WAVE 3 at 1 USD`
   by c53's, `CHAT WAVE 4 at 1 USD` by c54's; none may bind a second zip). Seed text
   `H = sha256(UTF-8("CHAT WAVE 5 at 1 USD" + ":" + <v7 zip sha256, 64 lower-case hex>))`, no trailing newline. Cap 1.00
   USD; one attempt + one plumbing retry; expected about 0.01-0.02 USD.

Labels: `PACKAGE_VERSION` = `v7`; `RUN_LIMITS_R1W7.json` `package_version` and the line in `cost_cap_status`; the stage note;
README; the custodian procedure; FROZEN re-derived from the constants (the kit test checks they agree); the tests that pin the
bands, the line, the blocked table, the cut size and the exclusion lists.

**Unchanged (checked by the tests and the freeze):** the v4 reader (`r1w7.merge_r1w7 v2`), the v4 recorder unit and fixture,
every mark, threshold, arm, status word, exam size, instrument row and hard gate; the noise sentences; the five neighbours by
freeze; the practice pools; the scoring functions; the units and their commands.

**What this amendment does not do.** It does not re-read c54. It does not launch. It does not draw an exam. It licenses
nothing. The reader-gap code is `ENGINEERED-NOT-VALIDATED` until a sealed draw; practice numbers under the new reader and
the new rule may move against v6's run8, and every move is reported as a finding in `PRACTICE_READINGS_V7.json`, never
smoothed. A fresh draw can still miss a mark on a shape no practice run has shown.
