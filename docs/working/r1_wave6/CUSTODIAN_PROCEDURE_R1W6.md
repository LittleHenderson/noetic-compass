# CUSTODIAN PROCEDURE — HELM-R1 wave 6 v3 exam (the K4 re-run; laptop, 0 USD, no network)

You are the custodian: a separate session from the builder. You make a FRESH sealed exam for the v3 package from the
public frames and the sealed generators. You never show an item, a key, a seed or a multiplier to the builder or the
operator; you hand over hashes, counts and id lists only. The program still names its files `*_X6.json` (the file
names are frozen code); this draw is called **X6v3** in every record. The first X6 (manifest `4d81abff…`, job c48) is
SPENT: never open it, never re-use it.

## Seed source (amendment A-R1W6-2; PREREGISTRATION_R1W6.md sections 10 and 17)

The owner pre-approved ONE re-run after the K4 fix with the verbatim line `FIX K4 at 1 USD` (15 UTF-8 bytes; recorded
in `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, heading "Owner words (2026-10-19 night, verbatim)", bullet
"FIX K4 at 1 USD"). The seed source is

    H = sha256( UTF-8 bytes of  "FIX K4 at 1 USD" + ":" + <full sha256 of the sealed v3 zip, 64 lower-case hex> )

no trailing newline. Every exam seed comes from H by `r1w6/seed_rule_w6.py`. **v3 bands** (above everything used or
reserved: X6 1,954-1,963 M; CTT-2R 1,964-1,969 M; USE-1's reservation 1,972-1,977 M):
E64 1,980,000,001-1,981,000,000; F64 1,982,000,001-1,983,000,000; REAL 1,984,000,001-1,985,000,000; CONV
1,986,000,001-1,987,000,000; PAIRW 1,988,000,001-1,989,000,000; used table 1-1,979,000,000 whole; drive-loop world
seeds from H by life name. You do not compute any of it by hand. `APPROVAL_RECORD_R1W6.json` v3 (beside the zip) holds
the line, its byte length and sha256, and the zip and freeze sha256; the seal refuses any other zip or line.

**Exclusions (by program, nothing to do by hand):** X-REAL's 128, c46's 128, c47's 128, RB-W1T's two practice draws,
wave 6's practice pools, and the spent X6's 128 REAL + 64 CONV + 64 PAIRW ids (`contract/EXCLUDE_R1W6_X6_USED.json`,
ids only). The E64 / F64 text rule forbids the texts of the ELEVEN spent language files below.

## Steps

1. Check the zip: `sha256(HELM_R1_W6_20261019_SOURCE_R1W6.zip)` equals `package_zip_sha256` in the v3
   `APPROVAL_RECORD_R1W6.json`. Extract it to a NEW folder, e.g. `Documents\Codex\2026-10-19\r1_wave6\x6v3_custody\pkg\`.
   Extract the seven neighbour zips (sha256 in `r1w6/common_w6.py` NEIGHBOURS; unchanged from v2) beside it in
   `x6v3_custody\deps\` so the package finds them (`..\deps\<top folder>`), or set `R1W6_<W1|W2|W3|W3B|W4|W5|RBW1T>_DIR`.
2. Check the frames: `x_real\frames\FRAME_R_PG.jsonl` sha256 `c983e065...`, `FRAME_R_WB.jsonl` `6a0d7cc1...` (the seal
   checks them again).
3. One python process at a time (check that no python.exe running worker.py exists; wait, never kill), at least 300 MB
   free RAM. With the extracted package folder as working directory and PYTHONPATH set to it, run:

       python -X utf8 -B -m r1w6.custody_w6 seal --frames-dir <...\x_real\frames>
              --approval <...\APPROVAL_RECORD_R1W6.json> --zip <...\HELM_R1_W6_20261019_SOURCE_R1W6.zip>
              --out-dir <...\x6v3_custody\out>
              --extra-text-file <...\2026-10-18\r1_wave2\x1_custody\exam\ENGLISH16_X1.json>
              --extra-text-file <...\2026-10-19\r1_wave3\x2_custody\exam\ENGLISH16_X2.json>
              --extra-text-file <...\2026-10-19\r1_wave3\x2_custody\exam\FACES16_X2.json>
              --extra-text-file <...\2026-10-19\r1_wave3b\x3_custody\exam\ENGLISH64_X3.json>
              --extra-text-file <...\2026-10-19\r1_wave3b\x3_custody\exam\FACES64_X3.json>
              --extra-text-file <...\2026-10-19\r1_wave4\x4_custody\exam\ENGLISH64_X4.json>
              --extra-text-file <...\2026-10-19\r1_wave4\x4_custody\exam\FACES64_X4.json>
              --extra-text-file <...\2026-10-19\r1_wave5\x5_custody\exam\ENGLISH64_X5.json>
              --extra-text-file <...\2026-10-19\r1_wave5\x5_custody\exam\FACES64_X5.json>
              --extra-text-file <...\2026-10-19\r1_wave6\x6_custody\exam\ENGLISH64_X6.json>
              --extra-text-file <...\2026-10-19\r1_wave6\x6_custody\exam\FACES64_X6.json>

   (The last two are the SPENT X6 language files, sha256 `c5d496fc…` and `fd26f63e…`; pass them by path only, never
   open them.) It prints hashes and counts only. It must print `"all_pass": true` (the receiver's checker re-derives
   the seeds, re-makes every file from the frames and the sealed generators and compares byte for byte, and checks the
   exclusions incl. X6, the pools, the carrier and the pins). Never run `practice` for the exam.
4. `out\exam\` (keys, samples, pools, derivation and copies of the inputs) stays on the laptop. The builder and the
   operator never open it. The host carrier is `out\carrier\x6\` (the six input files + `X6_PINS.json` ONLY); zip it
   with top folder `x6` as `X6V3_CARRIER_V1.zip` and record its sha256. The spent-X5 carrier for the host is the
   existing `X5SPENT_CARRIER_V1.zip` (`653372b4...`; top folder `x5spent`).
5. Write a handoff `X6V3_SEALED_<UTC>.json` beside `out\`: the MANIFEST sha256, the carrier zip sha256, the receiver
   check sha256 and `all_pass`, the package zip sha256, the counts, a by-program check that the new REAL / CONV / PAIRW
   id lists share 0 ids with `contract/EXCLUDE_R1W6_X6_USED.json`, and the sorted id lists the manifest holds (ids
   only, so the next wave can exclude them). No item text, key, seed or multiplier.

## What you must not do

- Do not open any other exam folder (the spent X6 folder included) except to pass the eleven spent language files to
  the program by path.
- Do not change any frame, exclusion list, quota, multiplier, pool rule, generator or seed rule. If anything refuses,
  stop and report the refusal.
- Do not run the exam through HELM.
