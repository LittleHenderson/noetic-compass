# LAUNCH BRIEF — HELM-R1 wave 6, the PAIR WAVE, v3 = the K4 re-run (for the custodian, the operator and the reader)

**Status: SEALED v3, NOT LAUNCHED.** Owner pre-approval `FIX K4 at 1 USD` (pinned 15 bytes; `APPROVAL_RECORD_R1W6.md`
/ `.json` v3, json sha256 `4054cfd682bdda66ad1e1fb1d640d9afb56a50c42fa43089730e00d4aeded8c4`). Cap **1.00 USD**, one
scored attempt + one plumbing retry. No sign request. Amendment A-R1W6-2 (PREREGISTRATION_R1W6.md section 17).
v1 `f307bdbc…` VOID; **v2 `72962342…` VOID_SPENT (scored by c48; never ship it again)**; **X6 SPENT (never ship its
carrier `6de3d782…` again)**.

| Item | Value |
|---|---|
| Package zip | `HELM_R1_W6_20261019_SOURCE_R1W6.zip` sha256 `f1b64a5edf0df2b152c867f328c71b3df8640a759836108079590e7959c31b47` (939,259 bytes) |
| Freeze | `da1ec4d2e144a8921d27231e99ff277de0e915b61e2de205cc94646a4723c8a8` (the runner's `--expected-freeze-sha256`) |
| HELM under test | inside the zip: `helm_now/` cut from thread head `fdf68e0c` (PR #406, reader v5) |
| Neighbour zips (beside, unchanged from v2) | wave 1 v3 `31f97d67…`, wave 2 `21ad185d…`, wave 3 v3 `152bca2a…`, wave 3b `a4f82556…`, wave 4 `4bd0d740…`, wave 5 `b6598687…`, RB-W1T v3 `3a8ae37e…` (copies in `deps/`) |
| Seed source | sha256(UTF-8 of `FIX K4 at 1 USD` + ":" + the v3 zip sha256) = `430df5a9…` (approval record); part seeds derived only by the custodian's sealed program, bands 1,980-1,989 M |
| Exam | a FRESH custodian draw "X6v3" (file names still `*_X6.json`), excluding the spent X6 by id and text |
| Host | one m6i.xlarge-class CPU host (2-CPU / 14 GiB slice), c21 image, us-west-2; no GPU; stage `kit/STAGE_R1W6.json` (unchanged) |
| Expected | about 0.02-0.10 USD (c48 cost 0.02); worst case about 0.70 with the plumbing retry |

1. **Custodian** (separate session, laptop): `CUSTODIAN_PROCEDURE_R1W6.md` (v3) with the v3 zip and the v3
   `APPROVAL_RECORD_R1W6.json`; output folder `x6v3_custody\`; ELEVEN spent language files (X1-X5's nine + the spent
   X6 `ENGLISH64_X6.json` `c5d496fc…` and `FACES64_X6.json` `fd26f63e…`, by path only); `r1w6.custody_w6 seal` must
   print `"all_pass": true`; ship `out\carrier\x6\` as `X6V3_CARRIER_V1.zip` (top folder `x6`).
2. **Operator** (AWS): sources `r1w6` = the v3 zip, the seven neighbour zips, `x6` = the NEW `X6V3_CARRIER_V1.zip`,
   `x5spent` = `X5SPENT_CARRIER_V1.zip` (`653372b4…`). The runner refuses before any package code on any mismatch.
   Ledger hold, cleanup proof (three ways) and the job record are the operator's. Lesson from c48: extract the seven
   neighbour zips beside the reader's fresh extract BEFORE the first reader call.
3. **Reader** (laptop, fresh extract of the v3 zip, neighbours beside it): `python -X utf8 -B -m r1w6.merge_r1w6
   --merge-input MERGE_INPUT_R1W6.json --out R1_W6_READING.json` (host index + sha, `out_dir`, the custodian's X6v3
   exam and carrier folders, the v3 approval record + sha, the v3 zip, the frames, the ELEVEN spent language files,
   c40's host file, `practice_mock: false`).

**Builder's forecast after v3 practice (not read by any program):** `WIDE_WAVE_EARNED_KEEP` about 0.55;
`WIDE_WAVE_NO_GAIN` about 0.2 (a fresh draw may hold another reader form that makes an unexplained ask);
`WIDE_WAVE_HARMED` about 0.1; `INCONCLUSIVE` about 0.15. Known cost: reader v5 asks on relative-amount forms it cannot
hold (one practice recipe, "same quantity of milk"), which lowers K1 margin but never adds a wrong answer.
