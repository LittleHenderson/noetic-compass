# Amendment A-R1W7-4 (copied verbatim from section 16 of the sealed v4 PREREGISTRATION_R1W7.md)

## 16. Amendment A-R1W7-4 (v4, written BEFORE the v4 reseal; owner order 2026-10-20 "want the chat test rerun with the reader repaired"; 2026-10-20)

**Why.** The v3 package (zip `5063baba8be9ba807e7905d5f86732cb1a535ff5a533e67c79f5cbe16edbc6a9`, freeze `2366e85d…`,
HELM cut `dfc7158d`) ran on the host as job c51 (`RUN_RESULT_R1W7_C51.md`; reading `R1_W7_READING.json` sha256
`8f2f76468fef11e4d755083d2581578e04466e0d028a92848c8019ad945a5d4d`). The frozen reader said verdict `FAILURE`, word
`INCONCLUSIVE`: every instrument row true, all six marks true, 9 of 10 hard gates true, **HG5 (sandbox) false**. HG5 read
false because of a defect in the v3 reader and the v3 recorder unit's record, not because of HELM and not because of any
sandbox breach: HG5's row `helm_now_files_changed` demands a list from every one of the 14 units; the recorder-equality
unit (`W7_RECORDER_EQUALITY`) never wrote the field (`chat_harness.run_recorder_equality` built its record without it;
only the chat and loop units hashed `helm_now/` before and after), so the reader saw `None`, and `None == []` is false. The
v3 fixture (`tests_r1w7/fixture_run.py`) gave its synthetic recorder unit `"helm_now_files_changed": []` by hand, so every
planted-failure test of HG5 passed while the real gate could never hold; the v3 practice reading also read HG5 false, hidden
under `INSTRUMENT_ERROR` on the practice mock. A second plumbing defect: `kit/STAGE_R1W7.json` carried `"pythonpath": []`,
which the run-proven supervisor refuses (`PLAN_INVALID:r1w7_host_run:pythonpath`; c51 attempt 1 died before any stage);
the v3 kit test even asserted the empty list; the operator fixed it in the job plan only (D-OP-C51-1, attempt 2). Line 4
of this document forbids re-reading c51's data with a repaired reader; the c51 word stands. The owner ordered the rerun.
**v3 is `VOID_SUPERSEDED_BY_V4`** for any further run (its c51 record stands as written; nothing from c51 is licensed).

**What changed in this package (v4). Exactly these, nothing else.**

1. **The recorder unit writes `helm_now_files_changed`** (belt). `chat_harness.run_recorder_equality` hashes `helm_now/`
   before and after exactly as the chat and loop units do (`common_w7.tree_listing`) and writes the sorted list of
   changed paths. Its record is now built by one function, `chat_harness.recorder_doc`, which the real unit and the test
   fixture both call, so the fixture carries the field only because the real code writes it.
2. **The reader names and refuses a missing list** (braces). `merge_r1w7.hard_gates` HG5 now lists
   `units_missing_helm_now_files_changed` (every unit whose record has no list), `units_with_the_list` and `units_planned`
   (14), and HG5 holds only if that missing list is empty AND every list is empty AND the wave-1 tree hash is unchanged
   AND `helm_brain_canonical.py` equals its base AND every chat unit's session log sits under its scratch. A unit that
   does not write the list is still a failure, so no unit can dodge the gate. Reader string
   `r1w7.merge_r1w7 v2 (2026-10-20, A-R1W7-4: ...)`. The exact diff is in `READER_FIX_DIFF_V4.md` beside the zip.
3. **Three HG5 tests** (`tests_r1w7/test_units_w7.py`): on the clean fixture all 14 units carry `[]` and HG5 reads **true**
   (`units_with_the_list` 14 of 14); plant `HG5c` (the recorder unit lacks the field, the c51 shape) reads HG5 **false**
   and names `W7_RECORDER_EQUALITY`; plant `HG5d` (the recorder unit lists `helm_chat.py` as changed) reads HG5 **false**.
   The real recorder unit's test asserts `helm_now_files_changed == []` on practice turns.
4. **The stage plan:** `kit/STAGE_R1W7.json` `pythonpath` = `["HELM_R1_W7_20261020"]`, exactly what c51 attempt 2 ran
   (D-OP-C51-1; `run_c51_r1w7_20261020/payload_c51/execution/job_plan.json`). Every process is `python -X utf8 -B -I`, so
   `-I` ignores the PYTHONPATH the supervisor exports; the entry matters only to the supervisor's own plan rule. New
   `kit/stage_check_w7.py` (not a byte copy) runs the run-proven `plan_check` and refuses an empty `pythonpath` or an
   entry that is not a folder under the source root; `kit/plan_check.py` and `kit/job_supervisor.py` stay byte copies
   (`84257a23…`, `3b2337ca…`). The kit test runs the supervisor's own `validate_plan` on the sealed stage (passes) and on
   the stage with an empty list (`PLAN_INVALID:r1w7_host_run:pythonpath`).
5. **Exclusions:** `contract/EXCLUDE_R1W7_PRIOR_USED.json` gains block `X7_c51` = lists `X7_c51_real` (X7's 128 REAL ids)
   and `X7_c51_conv` (X7's 64 CONV pool ids), read by program from the custodian's seal record
   `x7_custody/X7_SEALED_20261021T024717Z.json` (ids only; no input, key or exam file opened; file sha256 in `sources`).
   **From v4 every list applies to BOTH pools** (`custody_w7.REAL_EXCLUDE_LISTS` = all 16 lists; `CONV_EXTRA_LISTS` = `()`).
   Reason: c51's custodian flagged 3 of X7's 128 REAL ids that also sat in X6's / X6v3's CONV lists (`pg:65501@21017`,
   `pg:6912@731078` in `x6_conv`; `pg:49958@479072` in `x6v3_conv`): no violation of the v3 contract (sections 4.1-4.2
   applied those lists to the conversation pool only), but a recipe seen in any earlier exam or pool should never be
   drawn again in either pool. Distinct excluded ids over all 16 lists: 1,466 (v3: 1,277 over 14). The practice pool rule
   (`practice_real_exclusions`, `practice_conv_exclusions`) is unchanged, so the builder's practice draw is the same as v1-v3.
6. **Seed bands** (section 10 superseded): REAL 2,000,000,001-2,001,000,000; CONV 2,002,000,001-2,003,000,000; NOISE
   2,004,000,001-2,005,000,000 (each 1,000,000 wide; all below INT32_MAX 2,147,483,647). Used table 1-1,999,000,000 as one
   range (wave 6 v3 up to 1,989,000,000; v3 / c51's bands 1,990,000,001-1,995,000,000 are spent by the X7 draw; the
   continuity packet proposes 1,996,000,001-1,999,000,000, reserved here so the two never collide); gap 1,000,000; slot
   stepping and STOP as before. v4 needs fresh bands because the seed rule's used table must cover every band a sealed
   exam was drawn from, and X7 was drawn from v3's bands.
7. **The owner's line** (section 8 superseded): **`CHAT WAVE 2 at 1 USD`** (20 UTF-8 bytes; the v3 line `CHAT WAVE at 1 USD`
   (18 bytes) was consumed by c51's approval record `f28543bc…` and must never bind a second zip). Seed text
   `H = sha256(UTF-8("CHAT WAVE 2 at 1 USD" + ":" + <v4 zip sha256, 64 lower-case hex>))`, no trailing newline; the exam seed
   is derived from the owner's line and the v4 zip, so nothing is drawn until the owner writes that line. Cap 1.00 USD;
   one attempt + one plumbing retry; expected about 0.02 USD.
8. Labels: `PACKAGE_VERSION` = `v4`; `RUN_LIMITS_R1W7.json` `package_version`; the stage note; README; FROZEN re-derived
   from the constants (the kit test checks they agree).

**Unchanged (checked by the tests and the freeze):** HELM under test, commit `dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6`
(`helm_now/` byte-identical to v3: every one of the 161 cut files + `SOURCE_CUT.json` hashes to v3's freeze;
`helm_brain_canonical.py` = base `d4488f2a` `24df53c9…`); every mark, threshold, arm, status word, exam size, instrument
row, the other nine hard gates and HG5's other four rows; the noise sentences; the five neighbours by freeze; the practice
pools; the scoring functions; the units and their commands (the recorder unit's command line is the same; only its record
gained one field).

**What this amendment does not do.** It does not re-read c51. It does not launch. It does not draw an exam. It licenses
nothing. The v4 forecast is the v3 forecast (section 15): on c51's exam every mark held as a fact; a fresh draw can still
miss one.
