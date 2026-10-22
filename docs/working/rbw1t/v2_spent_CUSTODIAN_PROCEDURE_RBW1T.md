# CUSTODIAN PROCEDURE — RB-W1T exam (laptop, 0 USD, no network)

You are the custodian: a separate session from the builder. You make the sealed exam from the public frames. You never
show an item, a key or a multiplier to the builder or the operator; you hand over hashes and counts only.

## Seed source (frozen before the seal)

The owner pre-approved this test with the verbatim line `WIDE TEST at 1 USD` (recorded in
`Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, heading "Owner pre-approval (2026-10-19, verbatim)").
The seed source is:

    H = sha256( UTF-8 bytes of  "WIDE TEST at 1 USD" + ":" + <full sha256 of the sealed zip, 64 lower-case hex> )

no trailing newline. k = int(H[0:16], 16); first slot = k mod 1,000,000; seed = 1,950,000,001 + slot (band RW
1,950,000,001-1,951,000,000), stepped only by the used-table rule; `overlap_check` must say PASS. The program does this
(`rbw1t/seed_rule_rbw1t.py`); you do not compute it by hand. `APPROVAL_RECORD_RBW1T.json` (beside the zip) holds the
line, its UTF-8 byte length and sha256, and the zip and freeze sha256; the seal refuses any other zip or line.

## Steps

1. Check the zip: `sha256(HELM_RBW1T_20261019_SOURCE_RBW1T.zip)` equals `package_zip_sha256` in
   `APPROVAL_RECORD_RBW1T.json`. Extract it to a NEW folder (for example `Documents\Codex\2026-10-19\rbw1t\rbw1t_custody\pkg\`).
2. Check the public frames: `x_real\frames\FRAME_R_PG.jsonl` sha256 `c983e065...` and `FRAME_R_WB.jsonl` `6a0d7cc1...`
   (the seal checks them again).
3. Run, with the extracted package folder as working directory and PYTHONPATH set to it (one python process at a time,
   at least 300 MB free RAM; measured peak about 150 MB, about 2 s):

       python -X utf8 -B -m rbw1t.custody_rbw1t seal --frames-dir <...\x_real\frames>
              --approval <...\APPROVAL_RECORD_RBW1T.json> --zip <...\HELM_RBW1T_20261019_SOURCE_RBW1T.zip>
              --out-dir <...\rbw1t_custody>

   It prints only hashes and counts. It must print `"all_pass": true` (the receiver's checker re-derives the seed, the
   draw, the fresh amounts, the turns and the keys from the frames and compares them with what it wrote).
   Never pass `--practice-mock` (that is the builder's dry run; the reader refuses it).
4. The exam folder `rbw1t_custody/exam/` (INPUTS, KEYS, SAMPLE_RECORD, SEED_DERIVATION) stays on the laptop. The builder
   and the operator never open it. The host carrier is `rbw1t_custody/carrier/rw/` (INPUTS_RBW1T.json + RBW1T_PINS.json
   ONLY); zip it with top folder `rw` as `RW_CARRIER_V1.zip` and record its sha256.
5. Write a handoff `RBW1T_SEALED_<UTC>.json` beside `rbw1t_custody/`: the MANIFEST sha256, the carrier zip sha256, the
   receiver-check sha256 and `all_pass`, the package zip sha256, the counts (items per cell, shortfall, skips, answer /
   undetermined keys, representable). No item, key or multiplier.

## What you must not do

- Do not open `x_real\xr_custody\exam\` or `cas_token_transformer\ctt_custody\` (other exams).
- Do not change any frame, exclusion list, quota, multiplier or rule. If anything refuses, stop and report the refusal.
- Do not run the exam through HELM.
