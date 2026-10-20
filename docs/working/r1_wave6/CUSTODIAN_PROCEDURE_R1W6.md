# CUSTODIAN PROCEDURE — HELM-R1 wave 6 exam X6 (laptop, 0 USD, no network)

You are the custodian: a separate session from the builder. You make the sealed exam X6 from the public frames and the
sealed generators. You never show an item, a key, a seed or a multiplier to the builder or the operator; you hand over
hashes and counts only.

## Seed source (frozen before the seal; PREREGISTRATION_R1W6.md section 10 and D-W6-8)

The owner pre-approved this wave with the verbatim line `PAIR WAVE at 1 USD` (18 UTF-8 bytes; recorded in
`Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, heading "Owner pre-approval + order (2026-10-19 night,
verbatim)"). The seed source is

    H = sha256( UTF-8 bytes of  "PAIR WAVE at 1 USD" + ":" + <full sha256 of the sealed zip, 64 lower-case hex> )

no trailing newline. Every exam seed comes from H by `r1w6/seed_rule_w6.py` (bands E64 1,954,000,001-1,955,000,000;
F64 1,956,000,001-1,957,000,000; REAL 1,958,000,001-1,959,000,000; CONV 1,960,000,001-1,961,000,000; PAIRW
1,962,000,001-1,963,000,000; used table 1-1,953,000,000 whole; drive-loop world seeds from H by life name). You do not
compute any of it by hand. `APPROVAL_RECORD_R1W6.json` (beside the zip) holds the line, its byte length and sha256, and
the zip and freeze sha256; the seal refuses any other zip or line.

## Steps

1. Check the zip: `sha256(HELM_R1_W6_20261019_SOURCE_R1W6.zip)` equals `package_zip_sha256` in
   `APPROVAL_RECORD_R1W6.json`. Extract it to a NEW folder, e.g. `Documents\Codex\2026-10-19\r1_wave6\x6_custody\pkg\`.
   Extract the seven neighbour zips (the same zips the builder's `deps\` copies came from; their sha256 are in
   `r1w6/common_w6.py` NEIGHBOURS) beside it in `x6_custody\deps\` so the package finds them (`..\deps\<top folder>`),
   or set `R1W6_<W1|W2|W3|W3B|W4|W5|RBW1T>_DIR` to them.
2. Check the frames: `x_real\frames\FRAME_R_PG.jsonl` sha256 `c983e065...`, `FRAME_R_WB.jsonl` `6a0d7cc1...` (the seal
   checks them again).
3. One python process at a time (check that no python.exe running worker.py exists; wait, never kill), at least 300 MB
   free RAM. With the extracted package folder as working directory and PYTHONPATH set to it, run:

       python -X utf8 -B -m r1w6.custody_w6 seal --frames-dir <...\x_real\frames>
              --approval <...\APPROVAL_RECORD_R1W6.json> --zip <...\HELM_R1_W6_20261019_SOURCE_R1W6.zip>
              --out-dir <...\x6_custody\out>
              --extra-text-file <...\2026-10-18\r1_wave2\x1_custody\exam\ENGLISH16_X1.json>
              --extra-text-file <...\2026-10-19\r1_wave3\x2_custody\exam\ENGLISH16_X2.json>
              --extra-text-file <...\2026-10-19\r1_wave3\x2_custody\exam\FACES16_X2.json>
              --extra-text-file <...\2026-10-19\r1_wave3b\x3_custody\exam\ENGLISH64_X3.json>
              --extra-text-file <...\2026-10-19\r1_wave3b\x3_custody\exam\FACES64_X3.json>
              --extra-text-file <...\2026-10-19\r1_wave4\x4_custody\exam\ENGLISH64_X4.json>
              --extra-text-file <...\2026-10-19\r1_wave4\x4_custody\exam\FACES64_X4.json>
              --extra-text-file <...\2026-10-19\r1_wave5\x5_custody\exam\ENGLISH64_X5.json>
              --extra-text-file <...\2026-10-19\r1_wave5\x5_custody\exam\FACES64_X5.json>

   It prints hashes and counts only. It must print `"all_pass": true` (the receiver's checker re-derives the seeds,
   re-makes every file from the frames and the sealed generators and compares byte for byte, and checks the exclusions,
   the pools, the carrier and the pins). Never run `practice` for the exam.
4. `out\exam\` (keys, samples, pools, derivation and copies of the inputs) stays on the laptop. The builder and the
   operator never open it. The host carrier is `out\carrier\x6\` (the six input files + `X6_PINS.json` ONLY); zip it
   with top folder `x6` as `X6_CARRIER_V1.zip` and record its sha256. The spent-X5 carrier for the host is the existing
   `X5SPENT_CARRIER_V1.zip` (`653372b4...`; top folder `x5spent`).
5. Write a handoff `X6_SEALED_<UTC>.json` beside `out\`: the MANIFEST sha256, the carrier zip sha256, the receiver
   check sha256 and `all_pass`, the package zip sha256, the counts, and the sorted id lists the manifest holds (REAL draw,
   CONV pool, PAIRW pool: ids only, so the next wave can exclude them). No item text, key, seed or multiplier.

## What you must not do

- Do not open any other exam folder except to pass the nine spent language files to the program by path.
- Do not change any frame, exclusion list, quota, multiplier, pool rule, generator or seed rule. If anything refuses,
  stop and report the refusal.
- Do not run the exam through HELM.
