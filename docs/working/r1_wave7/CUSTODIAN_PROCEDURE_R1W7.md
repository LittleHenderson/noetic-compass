# CUSTODIAN PROCEDURE — HELM-R1 wave 7 exam X7 (laptop, 0 USD, no network)

You are the custodian: a separate session from the builder. You make a FRESH sealed exam for the sealed package from the
public frames and the sealed generators. You never show an item, a key, a seed or a multiplier to the builder or the
operator; you hand over hashes, counts and id lists only. The builder never handles a carrier.

## Before you start: the owner's signature

The exam seeds come from the owner's signed line and the sealed zip. The line to sign is **`CHAT WAVE 4 at 1 USD`** (20 UTF-8
bytes, the inner text without quote marks; PREREGISTRATION_R1W7.md section 8 as superseded by amendment A-R1W7-6, section 18; the v3 line `CHAT WAVE at 1 USD` was consumed by job c51, the v4 line `CHAT WAVE 2 at 1 USD` by job c52 and the v5 line `CHAT WAVE 3 at 1 USD` by job c53; none may bind a second zip). Until the owner signs it, there is no
`APPROVAL_RECORD_R1W7.json` and nothing to seal. When the owner has signed, the approval record is written by program from a
one-line file holding the owner's exact words (`r1w7/approval_w7.py record ... --source "<where the words are recorded>"`);
it binds the zip and freeze sha256. The seal refuses any other zip or line.

## Seed source (PREREGISTRATION_R1W7.md section 10 as superseded by A-R1W7-6, section 18)

    H = sha256( UTF-8 bytes of  "CHAT WAVE 4 at 1 USD" + ":" + <full sha256 of the sealed v6 zip, 64 lower-case hex> )

no trailing newline. REAL k = int(H[0:16], 16), CONV k = int(H[16:32], 16), NOISE k = int(H[32:48], 16); slot = k mod
1,000,000; seed = band low + slot. Bands (v6): REAL 2,012,000,001-2,013,000,000; CONV 2,014,000,001-2,015,000,000; NOISE
2,016,000,001-2,017,000,000; used table 1-2,011,000,000 whole (v3's bands were spent by X7, v4's by X7v4, v5's by X7v5; 1,996-1,999 M stays
reserved for the continuity packet); gap 1,000,000; slot stepping and STOP as wave 6. You do not
compute any of it by hand: `r1w7/seed_rule_w7.py` does and writes every step to `exam/SEED_DERIVATION_X7.json`.

**Exclusions (by program, nothing to do by hand; `contract/EXCLUDE_R1W7_PRIOR_USED.json`, ids only):** X-REAL's 128, c46's 128,
c47's 128, X6's 128 REAL ids, X6v3's 128 REAL ids, both RB-W1T practice draws, wave 6's practice pools, wave 7's practice pool
(`practice/PRACTICE_POOLS_W7.json`), X6's and X6v3's CONV and PAIRW pools, (v4, block `X7_c51`) X7's 128 REAL ids and 64 CONV pool ids from job c51, (v5, block `X7v4_c52`) X7v4's 128 REAL ids and 64 CONV pool ids from job c52, and (v6, block `X7v5_c53`) X7v5's 128 REAL ids and 64 CONV pool ids from job c53.
From v4 EVERY list applies to BOTH pools (A-R1W7-4); the conversation pool also excludes this package's own REAL draw.

## Steps

1. Check the zip: `sha256(HELM_R1_W7_20261020_SOURCE_R1W7_v6.zip)` equals `package_zip_sha256` in `APPROVAL_RECORD_R1W7.json`
   (the v6 zip; the v3 zip `5063baba…`, the v4 zip `8602b1bc…` and the v5 zip `4b54a077…` are VOID_SUPERSEDED and the seal refuses them).
   Extract it to a NEW folder, e.g. `Documents\Codex\2026-10-20\r1_wave7\x7v6_custody\pkg\` (never over the c51 / c52 / c53 custody folders `x7_custody\`, `x7v4_custody\`, `x7v5_custody\`). Extract the five neighbour zips
   (sha256 in `r1w7/common_w7.py` NEIGHBOURS) beside it in `x7_custody\deps\` so the package finds them (`..\deps\<top folder>`),
   or set `R1W7_<W1|W3|W3B|W6|RBW1T>_DIR`.
2. Check the frames: `x_real\frames\FRAME_R_PG.jsonl` sha256 `c983e065...`, `FRAME_R_WB.jsonl` `6a0d7cc1...` (the seal checks
   them again).
3. One python process at a time (no other python.exe of HELM's running; wait, never kill), at least 300 MB free RAM. Run:

       python -X utf8 -B -I <pkg>\HELM_R1_W7_20261020\r1w7\custody_w7.py seal --frames-dir <...\x_real\frames>
              --approval <...\APPROVAL_RECORD_R1W7.json> --zip <...\HELM_R1_W7_20261020_SOURCE_R1W7.zip>
              --out-dir <...\x7_custody\out>

   It prints hashes and counts only. It must print `"all_pass": true` (the receiver's checker re-derives the seeds, re-makes
   every file from the frames and the sealed generators and compares byte for byte, and checks the exclusions, the pool, the
   carrier, the pins, the noise file's binding and its frozen sentences and positions). Never run `practice` for the exam.
   If `X7_BLOCKED_SEED.json` appears instead, STOP and report: the seed rule found no free slot.
4. `out\exam\` (keys, samples, pools, derivation and copies of the inputs) stays on the laptop. The builder and the operator
   never open it. The host carrier is `out\carrier\x7\` (`INPUTS_REAL_X7.json`, `INPUTS_CONV_X7.json`, `INPUTS_NOISE_X7.json`,
   `X7_PINS.json` ONLY); zip it with top folder `x7` as `X7_CARRIER_V1.zip` and record its sha256.
5. Write a handoff `X7_SEALED_<UTC>.json` beside `out\`: the MANIFEST sha256, the carrier zip sha256, the receiver check sha256
   and `all_pass`, the package zip sha256, the counts (X7_REAL 128 with its key counts: at least 16 representable and
   ANSWER-keyed, else say so; X7_CONV 64 with every family present; X7_NOISE 64 with 128 noise turns), a by-program check that
   the new REAL and CONV id lists share 0 ids with `contract/EXCLUDE_R1W7_PRIOR_USED.json`, and the sorted id lists the manifest
   holds (ids only, so the next wave can exclude them). No item text, key, seed or multiplier.

## What you must not do

- Do not open any other exam folder, and never any `KEYS_*` file.
- Do not change any frame, exclusion list, quota, multiplier, pool rule, generator, noise sentence or seed rule. If anything
  refuses, stop and report the refusal.
- Do not run the exam through HELM, and do not run the practice command on the exam's output folder.
