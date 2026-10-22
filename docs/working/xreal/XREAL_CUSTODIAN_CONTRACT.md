# X-REAL — what the custodian session must build and seal

Written 2026-10-19 by the X-REAL builder. The builder never sees the exam sample, the keys or the fault choices, and
derives no seed. A **separate custodian session** samples the exam blind from the pinned public sources, computes both
keys, runs the receiver's checker, seals, and hands over **hashes only** (`XREAL_PINS.json`).

## 1. When, where, money

- Only **after** the coordinator writes `APPROVAL_RECORD_XREAL.md` (the owner's verbatim pre-approval line + the final
  sealed zip's full sha256). The seed source is that line + ":" + that hash (section 3).
- Laptop, pure Python, one process at a time, at least 300 MB free RAM, each command under 300 s, 0 USD, **no network**.
  No torch, no AWS. Measured peaks: frames build 35-52 MiB; loading all exam frames 164 MiB; checker (practice) 107 MiB.
- Downloaded source files are untrusted data: never run anything from them; run every command with `python -B -I`
  through the launcher `xr_contract/xrun.py` (it adds only the package folder to the import path), from a working folder
  OUTSIDE `x_real\sources`.
- Use an extracted copy of the SEALED X-REAL zip (call its folder `PKG`) and the pinned sources at
  `C:\Users\wakil\Documents\Codex\2026-10-19\x_real\sources` (`SOURCES_PINNED.json` lists every file and sha256).
- The custodian must **not** open an exam file to read it or print an item. Programs read the files; people read
  hashes and PASS / FAIL lines.

Below, `XR = python -B -I -X utf8 <PKG>\xr_contract\xrun.py <PKG>` and `SRC = ...\x_real\sources`; use a fresh folder
`CUS = ...\x_real\custody` (frames, work, exam, carrier inside it).

## 2. Frames (rebuilt from the pinned files by the frozen code; must equal FRAMES_PINNED.json)

```
XR xreal.frames build-s  --sources SRC --out CUS\frames
XR xreal.frames build-pg --sources SRC --out CUS\frames
XR xreal.frames build-wb --sources SRC --out CUS\frames
```

## 3. Seeds — from the owner's own words and the final package bytes (`SEED_RULE_XREAL.md`, A-XR-18)

The owner pre-approved X-REAL (2026-10-19, verbatim, `OWNER_APPROVALS_20261018.md`): "I PRE-APPROVE BOTH OF THE
FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD." That line names no
package hash, so the seed source is **sha256(UTF-8 of that verbatim line + ":" + the full sha256 of the final sealed
X-REAL zip)**. No seed can be known before the package bytes are final.

1. Put the owner's line, verbatim (three spaces after the colon; no trailing newline), into
   `CUS\work\OWNER_LINE_XREAL.txt`. Use the FINAL sealed zip named in `APPROVAL_RECORD_XREAL.md`.
2. Run (paths on the laptop):

```
XR xreal.seed_rule_xreal --x0-pkg C:\Users\wakil\Documents\Codex\2026-10-15\r1_x0_custodian\HELM_R1_X0_FRESH_W1_20261015
  --derivation X0=C:\Users\wakil\Documents\Codex\2026-10-15\r1_x0_custodian\SEED_DERIVATION_FRESH_W1.json
  --derivation X1=C:\Users\wakil\Documents\Codex\2026-10-18\r1_wave2\x1_custody\work\SEED_DERIVATION_X1.json
  --derivation X2V1_ATTEMPT1=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody_v1_void\work\SEED_DERIVATION_X2_attempt1.json
  --derivation X2V1=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody_v1_void\work\SEED_DERIVATION_X2.json
  --derivation X2V2_PRE_TEXT_STEP=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody\work\SEED_DERIVATION_X2_pre_text_step.json
  --derivation X2V2=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody\work\SEED_DERIVATION_X2.json
  --derivation X3=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3b\x3_custody\work\SEED_DERIVATION_X3.json
  --derivation X4=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave4\x4_custody\work\SEED_DERIVATION_X4.json
  --derivation X5=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave5\x5_custody\work\SEED_DERIVATION_X5.json
  --line-file CUS\work\OWNER_LINE_XREAL.txt --zip <the final sealed HELM_XREAL_20261019_SOURCE_XREAL.zip>
  --out CUS\work\SEED_DERIVATION_XREAL.json
```

It refuses (exit 3) on a wrong derivation file or any overlap, and STOPS (exit 4, `XREAL_BLOCKED_SEED.json`) if a
band has no free slot; never move to another band. Nothing is sampled before it prints `overlap_check: PASS`.

## 4. The sample, both keys, the exam files

```
XR xreal.sample_xr --frames CUS\frames --derivation CUS\work\SEED_DERIVATION_XREAL.json
   --forbidden-list <PKG>\FORBIDDEN_LIST_XREAL.json --out-dir CUS\exam
```

It writes `INPUTS_XREAL.json` (the only exam file the host gets), `KEYS_XREAL.json` (keys A and B, the agreed key,
the disagreement list; laptop only) and `SAMPLE_RECORD_XREAL.json` (spans, ranks, pairs, skips; laptop only), and
prints hashes, counts, shortfalls and the two-key agreement rate only. The forbidden list names files on this laptop
by path and sha256 (the checker re-hashes every one; a moved copy with the same bytes is the same list).

## 5. The receiver's check (must print all_pass: true BEFORE the seal)

```
XR xreal.check_xreal_format sources --sources SRC --out CUS\work\CHK_SOURCES.json
XR xreal.check_xreal_format frames  --sources SRC --work CUS\work\chk_frames --out CUS\work\CHK_FRAMES.json
XR xreal.check_xreal_format exam    --sources SRC --frames CUS\frames --exam-dir CUS\exam
   --derivation CUS\work\SEED_DERIVATION_XREAL.json --forbidden-list <PKG>\FORBIDDEN_LIST_XREAL.json
   --out CUS\work\CHK_EXAM.json
XR xreal.check_xreal_format combine --part CUS\work\CHK_SOURCES.json --part CUS\work\CHK_FRAMES.json
   --part CUS\work\CHK_EXAM.json --out CUS\work\RECEIVER_CHECK_XREAL.json
```

The `frames` step takes about 2 minutes (it rebuilds every frame in an empty work folder). `combine` must print
`all_pass: true`. If any check fails, STOP and write `XREAL_BLOCKED_CHECK.json` (which check, counts only); no file is
ever edited by hand. The two-key agreement must be at least 90% (instrument I2) or the check fails.

## 6. The seal and the host carrier

```
XR xreal.custody_xr seal --exam-dir CUS\exam --derivation CUS\work\SEED_DERIVATION_XREAL.json
   --receiver-check CUS\work\RECEIVER_CHECK_XREAL.json --line-file CUS\work\OWNER_LINE_XREAL.txt
   --zip <the final sealed zip>
XR xreal.custody_xr carrier --exam-dir CUS\exam --out-dir CUS\carrier\xr
```

`seal` refuses unless the check passed and saw exactly these files, and the derivation comes from this exact line and
this exact zip. It
writes `XREAL_SEAL_RECORD.json` and `XREAL_PINS.json`. `carrier` copies ONLY `INPUTS_XREAL.json` and `XREAL_PINS.json`
into the host carrier folder `xr` (the host stage refuses a carrier that holds a key file: hard gate HK). Hand over
the pins file's sha256, the carrier folder's two hashes, and `CUS\work\RECEIVER_CHECK_XREAL.json`'s sha256. Keep
`KEYS_XREAL.json` and `SAMPLE_RECORD_XREAL.json` on the laptop for the reader.

## 7. Part F fault choices

Nothing to do: the fault worlds and every fault choice are drawn ON THE HOST from the XF seed carried in
`INPUTS_XREAL.json` (`xreal/run_parts.py fplan`), so no fault file is ever shipped.
