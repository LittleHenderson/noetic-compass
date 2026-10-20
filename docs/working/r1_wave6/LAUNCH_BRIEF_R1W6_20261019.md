# LAUNCH BRIEF — HELM-R1 wave 6, the PAIR WAVE, v2 (for the custodian, the operator and the reader)

**Status: SEALED v2, NOT LAUNCHED.** Owner pre-approval `PAIR WAVE at 1 USD` (pinned 18 bytes; `APPROVAL_RECORD_R1W6.md`
/ `.json`, sha256 `5187cb7c…`). Cap **1.00 USD**, one scored attempt + one plumbing retry. No sign request. v1
(`f307bdbc…`) is VOID (never launched, no exam drawn); never ship it.

| Item | Value |
|---|---|
| Package zip | `HELM_R1_W6_20261019_SOURCE_R1W6.zip` sha256 `729623429832c5fa99141d96876434d9ebed7417055c87173e7a582b3677be0a` |
| Freeze | `83983cd4d70efe31d993822fca2f38392327a6f72b9066246af5cd17c014341a` (the runner's `--expected-freeze-sha256`) |
| HELM under test | inside the zip: `helm_now/` cut from `221cab70` (RB-W1 v4, PR #400) |
| Neighbour zips (beside, unchanged) | wave 1 v3 `31f97d67…`, wave 2 `21ad185d…`, wave 3 v3 `152bca2a…`, wave 3b `a4f82556…`, wave 4 `4bd0d740…`, wave 5 `b6598687…`, RB-W1T v3 `3a8ae37e…` (copies in `deps/`) |
| Seed source | sha256(UTF-8 of `PAIR WAVE at 1 USD` + ":" + the v2 zip sha256) — derived only by the custodian's sealed program |
| Host | one m6i.xlarge-class CPU host (2-CPU / 14 GiB slice), c21 image, us-west-2; no GPU; stage `kit/STAGE_R1W6.json` |
| Expected | about 0.03-0.10 USD; worst case about 0.70 with the plumbing retry |

1. **Custodian** (separate session, laptop): `CUSTODIAN_PROCEDURE_R1W6.md` with the v2 zip and `APPROVAL_RECORD_R1W6.json`;
   `r1w6.custody_w6 seal` must print `"all_pass": true`; ship `out\carrier\x6\` as `X6_CARRIER_V1.zip` (top folder `x6`).
2. **Operator** (AWS): sources `r1w6` = this zip, the seven neighbour zips, `x6` = the carrier, `x5spent` =
   `X5SPENT_CARRIER_V1.zip` (`653372b4…`). The runner refuses before any package code on any mismatch; then HELM's suites
   (scratch copy of the package's `helm_now/`), the wave-6 tests and the 77-unit pool. Outputs `r1w6_out/R1_W6_HOST.json`
   + sidecar and every unit file. Ledger hold, cleanup proof (three ways) and the job record are the operator's.
3. **Reader** (laptop, fresh extract of the v2 zip): `python -X utf8 -B -m r1w6.merge_r1w6 --merge-input
   MERGE_INPUT_R1W6.json --out R1_W6_READING.json` (host index + sha, `out_dir`, the custodian's exam and carrier
   folders, the approval record + sha, the zip, the frames, the nine spent language files, c40's host file,
   `practice_mock: false`).

**Builder's forecast after v2 practice (not read by any program):** `WIDE_WAVE_EARNED_KEEP` about 0.5; every mark held
on practice data, but a fresh draw may hold face or unit phrasings the guard does not cover.
