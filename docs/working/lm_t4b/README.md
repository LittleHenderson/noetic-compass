# LM-T4b — LM-T4 rerun under a reader sealed before the run (digit-and-eye-rows fix)

Owner's order (verbatim, 2026-10-20): "the LM-T4 corrected reading. rerun under a sealed reader with the bug fix".
Laptop (MSI), 0 USD, no network, no AWS. Written BEFORE any part ran (hashes of the seal below); the result file
`RUN_RESULT_LMT4B.md` is added after the run.

## Seal (recorded before running)

| Item | Value |
|---|---|
| Package zip | `LM_T4B_20261020_SOURCE.zip` |
| Zip sha256 | `f93ceba8601ccc579331d1a2c930ac44a857eeba87c3ff6591ac14e8e729efe2` (159,805 bytes, 28 members) |
| `SOURCE_MANIFEST.json` (inside the package; the supervisor's and worker's drift check, 128 rows) sha256 | `01da263dba25cb0ac149a501491ce55303a9d8210617fba550c1bc52cd887c86` |
| Sign line (operator-composed from the owner's order, LM-T4's form; not an owner signature) | `APPROVE lm_t4, source 01da263d, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.` |
| Reader of record `merge_t4b.py` sha256 | `382033ca52735f9b3a6dfedfd1316a716bc01360e8c794d8681328470a0d0db5` |
| LM-T4 original sealed reader `merge_t4.sealed.py` sha256 (reference, byte-exact) | `37f4a0e09fe325ec80c4e0993431a9486c26fa29649cd83c21c56eb8b064e6b2` |
| LM-T4 manifest of record (run code source) | `3390ebbd335cbc7613ec058e6721efba89453733ff49804f8370abbcaf4ec5d3` |
| Every member's sha256 | `PACKAGE_FREEZE.json` |

## Layout

- `package/` — what was zipped: `lm_t4/` (LM-T4's own files copied unchanged + `merge_t4b.py`, `merge_t4.sealed.py`,
  `FROZEN_LMT4B.json`, `PREREGISTRATION_LMT4B.md`, `READER_FIX_DIFF.md`, `SOURCE_MANIFEST.json`) and `rb_i1/` (the six
  rb_i1 files LM-T4 imports, copied unchanged). Every other import is read in place from its original folder and
  hash-verified before any part runs.
- `extract/` — the fresh extract of the zip that the parts actually ran from (`extract/lm_t4/runs/` holds the parts).
- `runs/` — the record copied from `extract/lm_t4/runs/` after the run: `LM_T4_MSI_P11..P18/`, `MERGED_MARKS_LMT4B.json`.
- `tools/` — the operator's scripts (`make_reader.py`, `build_package.py`, `run_parts_t4b.ps1`, `compare_to_lmt4.py`,
  `verify_hashes.py`). None of them is a source of results.
- `PREREGISTRATION_LMT4B.md`, `FROZEN_LMT4B.json`, `READER_FIX_DIFF.md` (copies of the sealed ones), `PACKAGE_FREEZE.json`,
  `DRIVER_LOG.txt`, `RUN_RESULT_LMT4B.md`, `HASHES_PASS_1..3.txt`, `BACKUP_RECORD.md`.

## Decisions taken by the operator (none of them changes a rule, a mark or a threshold)

1. The package keeps the folder name `lm_t4` (the code imports itself as `lm_t4`), inside `package/` and `extract/`.
2. `merge_t4.py` is not shipped under that name: the original sealed reader ships as `merge_t4.sealed.py` (reference only,
   byte-exact) and `merge_t4b.py` is the only reader run. `merge_t4b.py` keeps its output name `runs/MERGED_MARKS.json`
   (so the reader differs from the sealed reader in nothing but the two fixes); the operator copies that file byte-for-byte
   to `runs/MERGED_MARKS_LMT4B.json` and hashes both.
3. `FROZEN.json` is copied as it is on disk today (LM-T4's freeze plus amendments A1-A3 appended after the seal; the
   amendments are a record, not a rule change). `FROZEN_LMT4B.json` carries it verbatim plus the one change.
4. `run_all_parts.ps1` is copied unchanged but not used (it hard-codes LM-T4's folder); `tools/run_parts_t4b.ps1` calls the
   unchanged `supervisor.ps1` from the extract, one part at a time, in `PLAN.json` order, and stops at the first part that
   does not complete.
5. The CONT-3 run-time defect (CREATED vs ATTEMPTED on the untaught twin's asking crossings) is NOT fixed: it is in the
   run code, outside the owner's order. CONT-3 reads whatever it reads.
6. The old corrected reading (LMT4-A3, `8606c5aa4ef45a6dccb4fc40337e3f967ff88f079a386424b6d9520a1c416bc8`) is a note
   and never counts; the old sealed reading (`7423922310b81ecad2e2d5238d1a9e5237d535d880df45188ef07a9b6993d378`) stays
   LM-T4's reading of record.
