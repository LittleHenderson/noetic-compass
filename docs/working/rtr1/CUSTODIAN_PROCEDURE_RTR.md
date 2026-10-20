# RTR-1 — what the custodian session must draw and seal

Written 2026-10-19 by the RTR-1 builder. The builder never sees the draw, the keys or the seed. A **separate custodian
session** draws the 128 sentences blind, computes both keys, runs the receiver's check, seals, and hands over
**hashes only**.

## 1. When, where, money

- Only **after** `APPROVAL_RECORD_RTR.md` / `.json` exist (the owner's verbatim line + the FINAL sealed zip's sha256).
- Laptop, pure Python, one process at a time (check for another `python.exe ... worker.py` and wait; never kill it),
  at least 300 MB free RAM, each command under 300 s, 0 USD, **no network**, no torch, no AWS.
- Use a fresh extract of the SEALED RTR-1 zip (`PKG`) and a fresh extract of the sealed X-REAL zip
  `HELM_XREAL_20261019_SOURCE_XREAL.zip` (`a9b4c954…`; call it `XPKG`). Never edit either.
- Never open an exam file to read it or print an item: programs read the files; people read hashes and PASS/FAIL.
- Below: `RT = python -B -I -X utf8 <PKG>\rtr_contract\xrun.py <PKG>`, `CUS = ...\2026-10-19\rtr1\rtr_custody`
  (fresh: `work\`, `exam\`, `carrier\` inside), `XR = ...\2026-10-19\x_real`, `CT = ...\2026-10-19\cas_token_transformer`,
  `C = C:\Users\wakil\Documents\Codex`.

## 2. The owner's line (by program, never typed)

```
RT rtr.seed_rule_rtr line --approvals C\2026-10-18\OWNER_APPROVALS_20261018.md --out CUS\work\OWNER_LINE_RTR.txt
```
It must print `"bytes": 68` and sha256 `b645e4f482e10e3caa1f6e497f304ebc13faf481ff1345b2099c3f1358bc60e4`
(the text after `verbatim): ` on the `## Owner order (2026-10-19, verbatim): "RE-TEST READER" …` line).

## 3. The seed (from the owner's line and the final package bytes)

```
RT rtr.seed_rule_rtr derive --xreal-dir XPKG\HELM_XREAL_20261019
  --x0-pkg C\2026-10-15\r1_x0_custodian\HELM_R1_X0_FRESH_W1_20261015
  --derivation X0=C\2026-10-15\r1_x0_custodian\SEED_DERIVATION_FRESH_W1.json
  --derivation X1=C\2026-10-18\r1_wave2\x1_custody\work\SEED_DERIVATION_X1.json
  --derivation X2V1_ATTEMPT1=C\2026-10-19\r1_wave3\x2_custody_v1_void\work\SEED_DERIVATION_X2_attempt1.json
  --derivation X2V1=C\2026-10-19\r1_wave3\x2_custody_v1_void\work\SEED_DERIVATION_X2.json
  --derivation X2V2_PRE_TEXT_STEP=C\2026-10-19\r1_wave3\x2_custody\work\SEED_DERIVATION_X2_pre_text_step.json
  --derivation X2V2=C\2026-10-19\r1_wave3\x2_custody\work\SEED_DERIVATION_X2.json
  --derivation X3=C\2026-10-19\r1_wave3b\x3_custody\work\SEED_DERIVATION_X3.json
  --derivation X4=C\2026-10-19\r1_wave4\x4_custody\work\SEED_DERIVATION_X4.json
  --derivation X5=C\2026-10-19\r1_wave5\x5_custody\work\SEED_DERIVATION_X5.json
  --line-file CUS\work\OWNER_LINE_RTR.txt --zip <the FINAL sealed HELM_RTR1_20261019_SOURCE_RTR1.zip>
  --out CUS\work\SEED_DERIVATION_RTR.json
```
Exit 3 = refused (wrong file or overlap); exit 4 = STOP (`RTR_BLOCKED_SEED.json`; never another band). Nothing is
drawn before it prints `"overlap_check": "PASS"`. Band RS 1,940,000,001–1,941,000,000.

## 4. The draw, both keys, the exam files

```
RT rtr.sample_rtr --xreal-dir XPKG\HELM_XREAL_20261019 --frame XR\frames\FRAME_S.jsonl
   --derivation CUS\work\SEED_DERIVATION_RTR.json
   --xreal-inputs XR\xr_custody\carrier\xr\INPUTS_XREAL.json
   --ctt-exam CT\ctt_custody\exam\E_MACHINE_S_CTT.json --ctt-seal-record CT\ctt_custody\exam\E_MACHINE_SEAL_RECORD.json
   --ctt-approval CT\APPROVAL_RECORD_CTT.json
   --forbidden-list XPKG\HELM_XREAL_20261019\FORBIDDEN_LIST_XREAL.json --out-dir CUS\exam
```
The program checks every pin itself: the frame `98c2fb8f…`; X-REAL's spent inputs `37312a31…` (128 Part S items); the
CTT exam's sha256 equals its seal record's `exam_sha256_raw`, and the seal record names the package in CTT's approval
record; X-REAL's forbidden list content `3aadc747…` (its files are on this laptop by path and sha256). If the CTT
primary exam is not sealed yet, STOP and tell the coordinator (no draw without it). It prints counts, the key kinds,
the two-key agreement, the skip reasons and `overlap_zero` only. A stratum with fewer than 32 free items = STOP.

## 5. The receiver's check (must print all_pass: true BEFORE the seal)

```
RT rtr.check_rtr --exam-dir CUS\exam --work CUS\work\chk_redraw <the same --xreal-dir --frame --derivation
   --xreal-inputs --ctt-exam --ctt-seal-record --ctt-approval --forbidden-list as step 4>
   --line-file CUS\work\OWNER_LINE_RTR.txt --zip <the final sealed zip> --out CUS\work\CHECK_RTR.json
```
It redraws into the empty `chk_redraw` folder and needs byte-equal files, agreement >= 90%, 0 overlap, 32 per stratum,
no key in the inputs, no float, the seed equal to the derivation's. If any check fails: STOP and write
`RTR_BLOCKED_CHECK.json` (which check, counts only). No file is ever edited by hand.

## 6. The seal and the host carriers

```
RT rtr.custody_rtr seal --exam-dir CUS\exam --derivation CUS\work\SEED_DERIVATION_RTR.json
   --receiver-check CUS\work\CHECK_RTR.json --line-file CUS\work\OWNER_LINE_RTR.txt --zip <the final sealed zip>
RT rtr.custody_rtr carrier --exam-dir CUS\exam --out-dir CUS\carrier\rt
RT rtr.custody_rtr spent --xreal-inputs XR\xr_custody\carrier\xr\INPUTS_XREAL.json --out-dir CUS\carrier\xrspent
```
`carrier` copies ONLY `INPUTS_RTR.json` + `RTR_PINS.json` (the host refuses a carrier holding a key file: gate HK).
Hand to the coordinator: `RTR_PINS.json`'s sha256, the two carrier folders' file hashes, `CHECK_RTR.json`'s sha256,
`SEED_DERIVATION_RTR.json`'s sha256, and the counts line from step 4. Keep `KEYS_RTR.json` and
`SAMPLE_RECORD_RTR.json` on the laptop for the reader.
