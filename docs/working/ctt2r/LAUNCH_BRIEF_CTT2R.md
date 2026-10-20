# Launch brief — CTT-2R (for the coordinator / launch controller). NOT LAUNCHED.

## What runs, in one paragraph
No training. One AWS GPU host (`g5.xlarge`, us-west-2; fallback `g4dn.xlarge`) loads the six c45 translator models
exactly as c45 left them (sha256 pinned), makes two never-trained controls from recorded seeds, and runs HELM's reader
v1.1 first on every sealed Part R / Part K turn. Where the reader would ask, eight translator processes (three main
copies, twin, shuffled control, three untrained controls) and three copy-closest neighbours each propose a reading;
CTT's frozen checker checks each one; the host records the ACCEPT-2 votes (all three copies identical, or ask) and the
logs (margin, agreement, alignment). Then the six spent wave exams run OFF, OFF-without-the-translator-folder and ON
with the three-copy hook. No answer key is on the host. The frozen reader runs later on the laptop.

## Package and records
- Zip `HELM_CTT2R_20261019_SOURCE_CTT2R.zip` sha256 **`d97a16d6683b41037b51d028bcc4776be86ae1db66b117bd2af0126bab6159b6`**
  (181,203 bytes, 35 members; inner `PACKAGE_FREEZE.json` `7cccf18e…`; outside `PACKAGE_FREEZE_CTT2R.json` `26367200…`).
- Preregistration: pre-code `23c0ae7c…`; final (with amendment A-2R-1) `26843f32…`.
- Tests from a fresh extract of the zip: 56 run, 0 failures, 0 errors, 0 skipped on the laptop, 8 s, 269 MB peak
  (`TEST_COUNTS_CTT2R.json`, log `TEST_LOG_FROM_ZIP_CTT2R.log`).
- Approval: `APPROVAL_RECORD_CTT2R.json` / `.md`, written by program (`ctt2r.approval_2r`): the owner's pinned bytes
  `CTT RULE TEST at 1.50 USD` (25 bytes, `0ed58283…`) cut from `OWNER_APPROVALS_20261018.md` + the zip above; cap
  1.50 USD; one attempt + one plumbing retry; seed source `c0230aa3…`. (Its field `package_freeze_sha256` is the
  sha256 of the outside file `PACKAGE_FREEZE_CTT2R.json`.)

## Preconditions (all must hold; the runner refuses otherwise)
1. The approval record above exists.
2. **The custodian has run `contract/CUSTODIAN_PROCEDURE_CTT2R.md`.** Step 3 (the Part R census) comes FIRST and
   costs nothing. The builder's practice census (amendment A-2R-1) predicts **R1 well below 24**, so the census will
   most likely print `NOT_EXERCISED` and STOP. Then the coordinator chooses: (a) widen the frame (new design, new
   package, new owner word; nothing launches), or (b) Part K only on this package (overall word `INCONCLUSIVE` by
   rule 1, with the Part K line reported beside it). Do not launch before that choice is recorded.
3. The new LLM pool is written by the custodian (Gemini free tier + DeepSeek, under 0.50 USD, not AWS), drawn,
   checked (`all_pass: true`) and sealed; the carrier holds only the inputs file(s) + `SEAL_RECORD_CTT2R.json`.
4. Payload, staged as `kit/STAGE_CTT2R.json` says (byte copies, every pin checked before upload):
   - `zips/ctt2r.zip` = the zip above; `zips/ctt.zip` = `HELM_CTT_20261019_SOURCE_CTT.zip` `f280633d…`;
     `zips/r1w5.zip` `b6598687…`, `zips/r1w3b.zip` `a4f82556…`, `zips/r1w3.zip` `152bca2a…`
     (`HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip`), `zips/w1.zip` `31f97d67…` (`HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip`).
   - `carriers/spent/`: ENGLISH64/FACES64 `_X3` `_X4` `_X5` and R1_W3B/R1_W4/R1_W5_HOST.json (the c45 payload's
     `carriers/spent/` members; pins in `ctt2r/common_2r.py`).
   - `carriers/weights/` from `Documents\Codex\2026-10-19\cas_token_transformer\run_c45_ctt1_20261020\a1_unpacked\
     c45_out\ctt_out\`: `runs/<seed>/final.pt` and `WEIGHTS_MANIFEST.json` for A4-s1 `db53775b…`, A4-s2 `16aebd0d…`,
     A4-s3 `76abf019…`, A5-s1 `525898b8…`, C1-s1 `e7028fe7…`, C2-s1 `d293039b…` (laid out as `<seed>/final.pt`),
     `data/vocab.json` `825b417a…`, `data/train.jsonl` `d92a070b…`, `data/DATA_MANIFEST_CTT.json` `513d9580…`,
     `NOHARM_OFF.json` `9b7cec6d…`. The same files are inside the archived c45 deliverable `3a1a7142…`
     (`D:\tksCAS-archive\ctt1_c45_20261020\`), re-hashed equal on 2026-10-19.
   - `carriers/exam/` = the custodian's carrier; `APPROVAL_RECORD_CTT2R.json`.
5. Image: an AWS Deep Learning AMI with PyTorch 2.x + CUDA; `HELM_CTT2R_AWS=1`; command in `kit/STAGE_CTT2R.json`;
   `--expected-zip-sha256` = the zip above; `--deadline-epoch` = launch + 90 min.

## Limits (`RUN_LIMITS_CTT2R.json`)
Cap 1.50 USD across both attempts; instance life 2 h (self-terminate); job wall 90 min; preflight 10 min; one
attempt + one plumbing retry (only if no part was scored). Expected 20–35 host minutes, about 0.35–0.60 USD
(cautious 0.80). A ledger hold before launch; closed after.

## First run of the neural code
`ctt2r_translator/serve2r.py` and `init_c2.py` have never run (no torch on the laptop). Stage 2 (preflight) runs a
GPU smoke of `serve2r.py` on A4-s1 (parameter count asserted, audit judged). If preflight or the C2 inits fail,
nothing was scored: that is plumbing; read `PREFLIGHT_CTT2R.json` and the stage logs before the retry.

## After the run
1. Download the output folder; verify every file against `RUN_RECORD_CTT2R.json` and the draft merge input.
2. Custodian: `ctt2r.seal_2r confirm` → `SEAL_CONFIRM_CTT2R.json`.
3. Fill `MERGE_INPUT_CTT2R.json` from `MERGE_INPUT_CTT2R.draft.json` + the laptop files (keys, seal record, seal
   confirm, approval record, derivation; each with its sha256), then on the laptop:
   `python -B -I -X utf8 contract/xrun.py <PKG> ctt2r.merge_2r --merge-input MERGE_INPUT_CTT2R.json --ctt-dir <CTT> --overlay <overlay> --out CTT2R_READING.json`.
4. Record per job (source, purpose, instance, start/stop UTC and Pacific, limits, actual cost, three-way cleanup
   proof, ledger), back up to `D:\tksCAS-archive\` with three sha256 passes, and add the spec-sheet row in the same
   commit as the result (negatives kept).
