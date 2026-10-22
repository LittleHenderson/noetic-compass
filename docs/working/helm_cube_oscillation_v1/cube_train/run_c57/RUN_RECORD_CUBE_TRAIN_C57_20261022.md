# CUBE TRAIN run c57 — record (2026-10-22)

Owner's words: "Yes: launch the CUBE TRAIN run on AWS now (one g5.xlarge, cap 3 USD), read the result, and record it."

## What ran

- Job `helm-claude-cubetrain-20261022-c57`, attempt 1 of 1 (no retry used). One `g5.xlarge` (NVIDIA A10G), us-west-2, instance `i-0a93a50584129d0e4`, launched 2026-10-22 10:55:29 UTC, terminated 12:03:52 UTC.
- Payload: the sealed zip `706e1fa6f3ce77ae4fee7a21cbb05b820c87f8a01c5df237858f81545eb2e899` (117,555,288 bytes). The host checked it (I1 true) before running.
- Host runner `run_cube.py`, exit 0, 3,879 s. Order seed 2840735047235775460 = sha256("CUBE TRAIN at 3 USD:" + zip sha) mod 2^63.
- Steps: package tests; 20-step GPU smoke with audited decoding (0 audit violations); 6,000 steps each for A4-s1, A4-s2, A4-s3 (9,585,566 parameters each) and the small twin A5-s1, fine-tuned from their pinned c45 weights; audited decoding of DEV (2,000 SDG + 357 AI-written rows); keep-old check (c45 serve on 2,000 kept CAS validation rows, start weights vs final weights) for the three voting copies.

## The reading (frozen reader `cube_task/read.py`, recomputed by hand on the laptop)

Status word: **`TRAIN_READY`**. Labels: `SYNTHETIC_ONLY`, `LLM_WRITTEN_STRATUM`, `CTT_RETRAINED_V1`.

Instrument (all true): I1 zip sha256, I2 audits clean (11 audit files, 0 violations), I3 trained with no NaN, I5/I6 package tests, I6 DEV floors, I7 cost estimate under cap.

Vote = unanimous answer of A4-s1, A4-s2, A4-s3 (A5-s1 is reported, never votes).

| Gate | Frozen limit | Count | Holds |
|---|---|---|---|
| G-INVENT | 0 invented words in any copy | 0 in all four copies | yes |
| G-CONFIDENT-WRONG, SDG | ≤ 0.01 | 0 / 2,000 = 0 | yes |
| G-CONFIDENT-WRONG, AI-written | ≤ 0.02 | 5 / 357 = 0.0140 | yes |
| G-CONFIDENT-WRONG, traps (both strata) | ≤ 0.01 | 1 / 307 = 0.0033 | yes |
| G-EXERCISED, SDG | ≥ 0.40 | 1,967 / 1,967 = 1.0000 | yes |
| G-EXERCISED, AI-written | ≥ 0.25 | 271 / 295 = 0.9186 | yes |
| G-KEEP-OLD | drop ≤ 0.02 | A4-s1 0.9785 → 0.9785; A4-s2 0.9795 → 0.9790; A4-s3 0.9770 → 0.9775 | yes |

Vote on the AI-written DEV: 331 right, 5 wrong, 21 NONE (copies disagreed, so no answer; HELM would ask), of 357.

Per copy on the AI-written DEV (right / wrong / no answer, of 357): A4-s1 339 / 17 / 1; A4-s2 341 / 15 / 1; A4-s3 342 / 13 / 2; A5-s1 321 / 35 / 1. On the SDG DEV every copy is 2,000 / 0 / 0.

## What this does and does not say

- It says: by the frozen reader, the retrained CTT copies may be pinned into the TEACH-2 package as the cube proposer. Nothing more.
- It does not say HELM reads people. The DEV rows are machine-made (SDG) or AI-written; the ceiling is `SYNTHETIC_ONLY` + `LLM_WRITTEN_STRATUM`. The claim-bearing test is the CUBE EXAM (TEACH-2) on its own sealed package.
- Negatives and limits, kept:
  - SDG 2,000 of 2,000 is the same generator as the training rows: it shows fit to that generator, not reading of new sentence shapes.
  - Any one A4 copy alone would fail the AI-written confident-wrong limit (13 to 17 wrong of 357 = 3.6% to 4.8%, limit 2%). Only the three-copy agreement rule brings it to 5 of 357 (1.40%), close to the limit.
  - The small twin A5-s1 is clearly weaker on AI-written lines: 35 wrong of 357 (9.8%).
  - 21 of 357 AI-written lines got no answer (the copies disagreed).
  - Each AI-written training row was seen about 100 times, each SDG row about 23 times (A-CUBE-TRAIN-5).

## Weights (re-hashed on the laptop; all MATCH the reading)

- A4-s1 `c39eafb6db92845a463a0c6bc711c73d45ddcb482b5e5eaffad466f337d7a69a`
- A4-s2 `3bfbf1f064e4dd96980bfa971cbd089706a4b99cfdaba0b84324f4a4b3a883ee`
- A4-s3 `6418ef1e27ffd18df9f571e9f5410af1afae6843d9d56cbcb01d31ccf947564b`
- A5-s1 `07a54adcdb58cfb746f35e0d4350a9bde536eb72f97d6b29451960313fca4bc1`

The weight files are not in git (size). They are in the deliverable zip `aws-c57-a1-deliverable.zip` sha256 `887c2803b735b16c5f7a35f4717cd2aec5256280b174843732ba6df385bda3b2` (124,952,688 bytes), checked against the machine's recorded sha after download; all 41 files of `SHA256SUMS.txt` verify. Unpacked at `Documents/Codex/2026-10-22/cube_train/c57_result/`. Backup: `D:/tksCAS-archive/cube_train_c57_run_20261022/` (33 files, source = destination, tree digest `78d2394afddd28a8597c6a8c104502d7c505f1f05ff5dbcd384beb156ba8b01b`).

## Cost and cleanup

- Charge 1.26 USD (list price for 4,440 s of host time: g5.xlarge 1.006 USD/h + 60 GB gp3 + public IPv4, rounded up to the cent); cautious figure 1.36 USD shown, not charged. The hold of 3.00 USD was released against it. Ledger 113.34 → 116.34 (hold) → 114.60 of 200 USD; 85.40 USD unreserved. Addendum `BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_CUBETRAIN_C57_20261022T121021Z.json` sha256 `4d6bf9ded141e5865b0fe9e229ee0880c8be11ecc61bfcffaac55b611b61798d`. The AWS bill itself is not yet posted.
- Cleanup verified three ways (files in this folder): the controller's record (`PRESERVED_AND_PREFIX_PURGE_VERIFIED`: instance terminated, root volume DELETED, prefix purged and verified empty, 0 multipart uploads); an independent read-only check (`VERIFIED`); a direct read-only look (no live project instance, no job volume, empty prefix, no delete markers, no multipart uploads). Cleanup proof sha256 `fa0403546f24ae4a4135c0428f1ae0b864ef325bc981d78d39c74ee08cb56291`.

## Operational notes

- One `CONTROL_ERROR` at launch + 0.07 s (`InvalidInstanceID.NotFound`): AWS's usual short delay before a new instance is visible. The controller's loop caught it and the next poll saw the instance running. No effect.
- The worker's once-a-minute progress ticker kept the phase name it started with (`BOOT`), so progress lines alternated BOOT / the real phase. Cosmetic; the run log carries the true steps. Fix in the next worker: read the phase from a file rather than a variable copied into the ticker.

## Next

Pin the A4-s1..s3 weights (and A5-s1 as reported-only) into the TEACH-2 package, seal it, then the CUBE EXAM at 1 USD on the owner's word.
