# LAUNCH BRIEF — HELM-R1 wave 7, the CHAT WAVE (for the owner, the custodian, the operator and the reader)

**Status: SEALED v3, NOT APPROVED, NOT LAUNCHED.** No approval record exists. The owner's line to sign, proposed by the
coordinator: **`CHAT WAVE at 1 USD`** (18 UTF-8 bytes, the inner text without quote marks). Cap 1.00 USD; one scored attempt +
one plumbing retry. Expected 0.02–0.10 USD (c48 and c50 cost 0.02 each on the same kind of host).

| Item | Value |
|---|---|
| Package zip | `HELM_R1_W7_20261020_SOURCE_R1W7.zip` sha256 `5063baba8be9ba807e7905d5f86732cb1a535ff5a533e67c79f5cbe16edbc6a9` (941,565 bytes) |
| Freeze | `2366e85d7a3b73fa0c6cefb94715aa7ba9cfeb6f3b384c4c0ad88d5ed0165da2` (the runner's `--expected-freeze-sha256`) |
| HELM under test | inside the zip: `helm_now/` cut from commit `dfc7158d` (PR #416, FIX FIRST rounds 1 and 2 on thread head `974fe36c`) |
| Neighbour zips (beside, unchanged) | wave 1 v3 `31f97d67…`, wave 3 v3 `152bca2a…`, wave 3b `a4f82556…`, wave 6 v3 `f1b64a5e…`, RB-W1T v3 `3a8ae37e…` (copies in `Documents\Codex\2026-10-19\r1_wave6\deps\` and `..\r1_wave6\HELM_R1_W6_20261019_SOURCE_R1W6.zip`) |
| Seed source | sha256(UTF-8 of `CHAT WAVE at 1 USD` + ":" + the zip sha256); part seeds derived only by the custodian's sealed program, bands REAL 1,990 M / CONV 1,992 M / NOISE 1,994 M |
| Exam | a FRESH custodian draw "X7": `INPUTS_REAL_X7.json`, `INPUTS_CONV_X7.json`, `INPUTS_NOISE_X7.json`, `X7_PINS.json` in a carrier `X7_CARRIER_V1.zip` (top folder `x7`, no key file) |
| Host | one m6i.xlarge-class CPU host (2-CPU / 14 GiB slice), c21 image, us-west-2; no GPU; stage `kit/STAGE_R1W7.json`; runner deadline 2,400 s |

1. **Owner:** signs the line (the words themselves, in the chat). The coordinator records them verbatim in
   `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md` with the Pacific time.
2. **Approval record by program** (coordinator): `python -X utf8 -B -I <extract>\HELM_R1_W7_20261020\r1w7\approval_w7.py record ...`
   from a one-line file holding the owner's exact words and the zip; it binds the zip and freeze sha256 and writes
   `APPROVAL_RECORD_R1W7.json` / `.md`.
3. **Custodian** (a separate session, laptop, 0 USD): `CUSTODIAN_PROCEDURE_R1W7.md`; `custody_w7 seal` must print `"all_pass": true`;
   ships `X7_CARRIER_V1.zip` and a handoff `X7_SEALED_<UTC>.json` (hashes, counts, id lists only).
4. **Operator** (AWS, job c51): `make_c51_kit.py` with the values file, then `build_payload_c51.py`, the ledger hold (1.00 USD),
   the transport lease, `aws_control_c51.py preflight 1`, `launch 1` + `watch 1`, download, cleanup proof three ways
   (controller, independent read-only check, direct read-only look), closeout against the measured list price.
5. **Reader** (laptop, fresh extract of the zip, the five neighbours beside it):
   `python -X utf8 -B -I HELM_R1_W7_20261020\r1w7\merge_r1w7.py --merge-input MERGE_INPUT_R1W7.json --out R1_W7_READING.json`.
6. **Record:** `RUN_RESULT_R1W7_C51.md`, spec sheet §7.101 in the same commit, CHANGELOG, hub, backup to `D:\tksCAS-archive\` with three
   hash passes. Negatives kept whatever the word.

**Builder's forecast after v3 practice (not read by any program):** `CHAT_WAVE_EARNED_KEEP` about 0.45; `CHAT_WAVE_HARMED` about 0.2;
`CHAT_WAVE_NO_GAIN` about 0.15; `INCONCLUSIVE` about 0.2.
