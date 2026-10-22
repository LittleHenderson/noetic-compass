# HELM-R1 wave 3 (R1W3): one part off, two earned parts off, on HELM's own exams

Synthetic worlds only. Claim ceiling `SYNTHETIC_ONLY`. Rules frozen in `FROZEN_R1W3.json` (design:
`docs/working/r1_wave3/DESIGN_R1W3.md` on the thread branch, sha256 in `r1w3/common_w3.py`). One scored attempt plus at
most one plumbing retry. Only `r1w3/merge_r1w3.py` writes a verdict or a word.

## 1. What runs where

| Where | What | Torch? |
|---|---|---|
| AWS, one `m6i.xlarge`, 2-CPU slice, the c21 image | `kit/run_r1w3.py` (the one supervisor stage): wave 1's 128 carried tests, wave 2's unit tests, then `tests_r1w3` (units, kit, host). The host test regenerates X2's Gate B worlds with GB3's `world()` (one subprocess), then runs the carried units (wave 2's own `pool_w2.build_units` on E1, E2, X2 Gate B / Task B / CCE) and the 43 new units (`r1w3/pool_w3.py`), two at a time | only the world regeneration |
| Laptop, LOCAL_CPU_ONCE | the X2 depth families: `python -B -m r1w3.d34_x2 drive ...` (wave 2's adapter, wave 1's code, 20 parts) | no |
| Laptop | the reader: `python -B -m r1w3.merge_r1w3 --merge-input MERGE_INPUT_R1W3.json --out R1_W3_READING.json` | no |

## 2. Layout

- `r1w3/` `common_w3` (hashes, pins, bands, margins), `switches_w3` (13 switches, arms, exercise table, 16 pairs /
  18 pair runs, NOT_IN_WAVE), `live_w3` (English-16 v3 and Faces-16 through the live loop, with the CUBE_STORE,
  ENGLISH_IN, VOICE and TRIAD adapters), `cascade_w3` (the Cascade exam: the decoupling-stop rule, the fuse, the eye,
  the atlas returns, the cube ledger, the triad), `drive_w3` (DRIVE_LOOP RB-I2 and the idle exam), `gb_pair` (the Gate
  B pair arm), `pool_w3`, `summary_w3`, `merge_r1w3` (the frozen reader), `d34_x2`, `check_x2_format` (the receiver's
  check), `seed_rule_x2` (the X2 band rule), generators `gen_live`, `gen_cascade` (and `drive_w3 make`).
- `tests_r1w3/` `test_units_w3` (33), `test_kit_r1w3` (5), `test_run_r1w3` (4, AWS only); `fixtures/` the builder's
  E16 / F16 / Cascade / Idle FIXTURES (plumbing only, never scored).
- `kit/` `run_r1w3.py`, `STAGE_R1W3.json`, `plan_check.py` and `job_supervisor.py` (wave 2's, byte for byte).
- `helm/` HELM's live sources cut with `git show` from the thread branch (`helm/SOURCE_CUT.json`), plus
  `docs/working/noetic_council/{the_loop_v3, repair_performer, cube_store, faculties_v2, language_v3, return_address}`.
- `x2_contract/` `X2_CUSTODIAN_CONTRACT.md` and `SEED_RULE_X2.md`.
- NOT inside, shipped beside by hash: the wave-2 zip (`21ad185d...`), the wave-1 v3 zip (`31f97d67...`), the GB3 zip
  (`ff4de172...`), X2 (by its pins).

## 3. The host command

`kit/run_r1w3.py --package . --w1-package <w1> --w2-package <w2> --gb3-zip <zip> --x2-dir <x2> --scratch <dir>
--output <empty dir> --expected-freeze-sha256 <the approved PACKAGE_FREEZE sha256>`. It refuses, before any package
code runs, on any mismatch of this package, the wave-2 package, the wave-1 package, the GB3 zip, an X2 host file, or
under 5 GiB free disk. It keeps every `.json .md .log .sha256` file at `<stage out>/r1w3_out/`, where the plan
declares `R1_W3_HOST.json` and its sidecar.

## 4. The reading (laptop)

`MERGE_INPUT_R1W3.json`: host_reading, depth_reading, pins, run_record, supervisor_receipt, sources_manifest,
approval_record (each with its sha256), package_zip_sha256, package_freeze_sha256, w1_dir, w2_dir. Verdict PASS /
FAILURE / INSTRUMENT_ERROR; one word per switch; the DECOUPLING word; one word per read pair. Words licensed only with
PASS.
