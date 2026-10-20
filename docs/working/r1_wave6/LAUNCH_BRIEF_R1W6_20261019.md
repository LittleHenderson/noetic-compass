# LAUNCH BRIEF — HELM-R1 wave 6, the PAIR WAVE (for the custodian, the operator and the reader)

**Status: SEALED, NOT LAUNCHED.** Owner pre-approval `PAIR WAVE at 1 USD` (pinned 18 bytes; `APPROVAL_RECORD_R1W6.md`
/ `.json`, sha256 `271ee619…`). Cap **1.00 USD**, one scored attempt + one plumbing retry. No sign request is needed.

| Item | Value |
|---|---|
| Package zip | `HELM_R1_W6_20261019_SOURCE_R1W6.zip` sha256 `f307bdbc51210b87d413b5adb834183f3404ce4da5ac6d37ce23873909d7c9e1` |
| Freeze | `1b8943c6f9b59a0cef4c179125c4c5cc4c45c6f3d4f55980591f139d4a95db6f` (pass to the runner as `--expected-freeze-sha256`) |
| Neighbour zips (ship beside, unchanged) | wave 1 v3 `31f97d67…`, wave 2 `21ad185d…`, wave 3 v3 `152bca2a…`, wave 3b `a4f82556…`, wave 4 `4bd0d740…`, wave 5 `b6598687…`, RB-W1T v3 `3a8ae37e…` (copies in `deps/`) |
| Seed source | sha256(UTF-8 of `PAIR WAVE at 1 USD` + ":" + the zip sha256 above) — derived only by the custodian's sealed program |
| Host | one m6i.xlarge-class CPU host (2-CPU / 14 GiB slice), c21 image, us-west-2; no GPU; stage `kit/STAGE_R1W6.json` (plan check PASS) |
| Expected | about 0.03-0.10 USD; worst case about 0.70 with the plumbing retry |

## Step 1 — custodian (separate session, laptop, 0 USD)
Follow `CUSTODIAN_PROCEDURE_R1W6.md`: extract the zip and the seven neighbours, run `r1w6.custody_w6 seal` with the
nine spent language files; it must print `"all_pass": true`. Zip `out\carrier\x6\` (six inputs + `X6_PINS.json`, no key
file) as `X6_CARRIER_V1.zip` (top folder `x6`). Hand over hashes and counts only (`X6_SEALED_<UTC>.json`).

## Step 2 — operator (AWS)
Sources: `r1w6` = this zip; `w1`, `r1w2`, `r1w3`, `r1w3b`, `r1w4`, `r1w5`, `rbw1t` = the neighbour zips; `x6` = the
custodian's carrier; `x5spent` = the existing `X5SPENT_CARRIER_V1.zip` (`653372b4…`). Stage `kit/STAGE_R1W6.json`,
`--expected-freeze-sha256 1b8943c6…`. The runner refuses before any package code if a freeze, a carrier file or a spent
file differs, or a key file is in the carrier. Then HELM's seven suites (scratch copy), the wave-6 tests, and the
77-unit pool (2 workers, deadline 2,400 s). Declared outputs `r1w6_out/R1_W6_HOST.json` + sidecar (the index) and every
unit file under `r1w6_out/W6_*/`. Ledger hold and cleanup proof are the operator's (three ways, as c46 / c47).
Record each cloud job's source, purpose, instance, limits and cleanup.

## Step 3 — reader (laptop)
From a fresh extract of the sealed zip: `python -X utf8 -B -m r1w6.merge_r1w6 --merge-input MERGE_INPUT_R1W6.json
--out R1_W6_READING.json`, where the merge input names: `host_index` (+ sha256 from the sidecar), `out_dir` (the
deliverable's `r1w6_out`), `x6_exam_dir` and `x6_carrier_dir` (the custodian's), `approval_record` (+ sha256
`271ee619…`), `zip`, `frames_dir` (`x_real\frames`), `extra_text_files` (the nine spent language files),
`c40_host` (`r1_wave5\run_c40_r1w5_20261019\R1_W5_HOST.json`), `practice_mock: false`. The reader re-runs the receiver's
check, opens every unit file by its sha256 one at a time, and writes the only status word.

## Builder's honest forecast (not read by any program)
On practice data the wave would read `WIDE_WAVE_HARMED`: the wide brain gave 23 wrong answers on the conversation part
(faces, absent purposes, a unit restated in another kind) where the licensed brain gave 0 (mark NH-CONV, D-W6-13).
Everything else held. If the coordinator prefers to fix those HELM gaps first (and the chat crash D-W6-11), this
packet should wait; a fix means a new HELM build and a reseal.
