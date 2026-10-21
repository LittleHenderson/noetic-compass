# LM-T4c — LM-T4b run again with the CONT-3 run-code defect fixed (CREATED vs ATTEMPTED on the untaught twin's asking crossings)

Owner's order (verbatim, 2026-10-20): "Fix the CONT-3 run-code defect (CREATED vs ATTEMPTED), seal, and rerun LM-T4 on the
laptop at 0 USD as LM-T4c." Laptop (MSI), 0 USD, no network, no AWS. Written BEFORE any part ran (hashes of the seal
below); the result file `RUN_RESULT_LMT4C.md` is added after the run.

## Seal (recorded before running)

| Item | Value |
|---|---|
| Package zip | `LM_T4C_20261020_SOURCE.zip` |
| Zip sha256 | `ccece4ab2037a0d2de48c88cb8da64073c98f5e362bf3a8eb2b09c7d5d409807` (194,369 bytes, 32 members) |
| Built from | a fresh extract of LM-T4b's sealed zip `LM_T4B_20261020_SOURCE.zip` sha256 `f93ceba8601ccc579331d1a2c930ac44a857eeba87c3ff6591ac14e8e729efe2` (28 members) |
| `SOURCE_MANIFEST.json` (inside the package; the supervisor's and worker's drift check, 132 rows) sha256 | `94bcf5d14d173ec71f9da9e9f2386538b898a1ae4ef8d56ab57cebc7b5fa7f93` |
| Sign line (operator-composed from the owner's order, LM-T4's form; not an owner signature) | `APPROVE lm_t4, source 94bcf5d1, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.` |
| Reader of record `merge_t4b.py` sha256 (UNCHANGED from LM-T4b) | `382033ca52735f9b3a6dfedfd1316a716bc01360e8c794d8681328470a0d0db5` |
| `stations.py` sha256 before (LM-T4 = LM-T4b) -> after (the fix) | `64a2051bc17c200c570d7ea1f5428842a774ccb311d08cf7f9c4e0dc1c8fb8db` -> `f9109b9d916a893c2a0e487c65828138430e24d622c6ad02290db35e7537622d` |
| `test_lm_t4.py` sha256 before -> after (one test added) | `c3590dd0427dd0efb78d9121c4abba11a20a87c59abe39e1121951ba47532056` -> `b4eae8e710d4c3ee36841bdacf194d72367fd9ac105500e4a9ef2f66d91f3af8` |
| LM-T4 original sealed reader `merge_t4.sealed.py` sha256 (reference, byte-exact) | `37f4a0e09fe325ec80c4e0993431a9486c26fa29649cd83c21c56eb8b064e6b2` |
| LM-T4 manifest of record (run code source) | `3390ebbd335cbc7613ec058e6721efba89453733ff49804f8370abbcaf4ec5d3` |
| LM-T4b manifest of record | `01da263dba25cb0ac149a501491ce55303a9d8210617fba550c1bc52cd887c86` |
| Every member's sha256 | `PACKAGE_FREEZE.json` |

Only two members differ from LM-T4b's zip in content (`lm_t4/stations.py`, `lm_t4/test_lm_t4.py`); `SOURCE_MANIFEST.json`
is regenerated for this extract location (two hashes and the paths move); four record files are added
(`FROZEN_LMT4C.json`, `PREREGISTRATION_LMT4C.md`, `CONT3_DIAGNOSIS.md`, `CONT3_FIX_DIFF.md`). Checked by
`tools/build_package_t4c.py` (it refuses any other difference).

## Layout

- `package/` — what was zipped: `lm_t4/` (LM-T4b's files + the fix + the LM-T4c record files) and `rb_i1/` (the six
  rb_i1 files LM-T4 imports, unchanged). Every other import is read in place from its original folder and hash-verified
  before any part runs.
- `extract/` — the fresh extract of the zip that the parts actually run from (`extract/lm_t4/runs/` holds the parts);
  every member re-hashed against `PACKAGE_FREEZE.json` after extraction: PASS, 32 of 32.
- `old_code_test/` — LM-T4b's run code byte-identical with ONLY the new unit test added; used once to show the test fails
  on the old code (`TEST_OLD_CODE_OUTPUT.txt`). Never run as a part.
- `runs/` — the record copied from `extract/lm_t4/runs/` after the run: `LM_T4_MSI_P11..P18/`, `MERGED_MARKS_LMT4C.json`.
- `tools/` — the operator's scripts (`apply_cont3_fix.py`, `run_one_test.py`, `twin_asking_detail.py`,
  `build_package_t4c.py`, `run_parts_t4c.ps1`, `compare_to_lmt4.py`, `verify_hashes.py`). None of them is a source of results.
- `CONT3_DIAGNOSIS.md`, `CONT3_FIX_DIFF.md`, `PREREGISTRATION_LMT4C.md`, `FROZEN_LMT4C.json` (copies of the sealed ones),
  `PACKAGE_FREEZE.json`, `TEST_OLD_CODE_OUTPUT.txt`, `TEST_FIXED_CODE_OUTPUT.txt`, `TWIN_ASKING_DETAIL_OLD_CODE.txt`,
  `CONT3_stations.diff`, `CONT3_test.diff`, `DRIVER_LOG.txt`, `RUN_RESULT_LMT4C.md`, `COMPARISON_TO_LMT4B.txt`,
  `HASHES_PASS_1..3.txt`, `BACKUP_RECORD.md`.

## Decisions taken by the operator (none of them changes a rule, a mark or a threshold)

1. The fix keys on the brain's tag (`self.tag == "taught"`): the taught brain keeps `CREATED` (its questions are answered
   by teaching; 0 mismatches in LM-T4 and LM-T4b), the untaught twin gets `ATTEMPTED`. Writing `ATTEMPTED` for both brains
   would have moved the defect onto the taught brain (80 mismatches there instead).
2. One unit test was added to the package's own test file; the worker runs every test before a part, so each part now
   runs 13 tests instead of 12. The reader's gate H11 requires every test to pass, not a count of 12; the `tests` field in the
   reading will read 13 and is an expected non-number difference from LM-T4b.
3. LM-T4b's record files (`PREREGISTRATION_LMT4B.md`, `FROZEN_LMT4B.json`, `READER_FIX_DIFF.md`) stay in the package as
   they were in LM-T4b's zip (lineage of the reader).
4. The package keeps the folder name `lm_t4`; `merge_t4b.py` keeps its output name `runs/MERGED_MARKS.json`; the operator
   copies that file byte-for-byte to `runs/MERGED_MARKS_LMT4C.json` and hashes both. The on-disk hash is the hash of record.
5. The unchanged `supervisor.ps1` is called from the extract by `tools/run_parts_t4c.ps1` (LM-T4b's driver with only the run
   folder path changed).
