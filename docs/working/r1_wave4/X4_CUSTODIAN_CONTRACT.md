# X4 — the fresh exam of HELM-R1 wave 4 (the X3-SELF planted-fault exam + English-64 + Faces-64): what the custodian session must build and seal

Written 2026-10-19 by the wave-4 builder. **The builder never sees X4.** A separate custodian session builds it with the
sealed tools, checks it with the receiver's own checker, seals it, and hands over **hashes only** (`X4_PINS.json`).
Every step below is a command; the custodian makes no choice that is not written here.

## 1. When, where, money

- Only **after** the owner signs the R1W4 line (`OWNER_SIGN_REQUEST_R1W4.md`). Its exact bytes are X4's seed source.
- The coordinator first writes the approval record `R1W4_APPROVAL_RECORD.json` (schema `helm.r1w4.approval/1`):
  `owner_line_verbatim`, `owner_line_sha256` (sha256 of the line's UTF-8 bytes, no trailing newline),
  `package_zip_sha256`, `package_freeze_sha256`, `cap_usd`, `attempts`, `superseded_by: null`.
- Pure Python on the laptop: one process at a time, at least 300 MB free RAM, 0 USD, sockets blocked. No torch, no AWS.
- Use extracted copies of the SEALED wave-4 zip (this package), the sealed wave-3b zip (`a4f82556...`) and the sealed
  wave-3 v3 zip (`152bca2a...`). Run every command from the wave-4 package folder with `python -B`.

## 2. The four slots (file names fixed)

| Slot | File | Made by |
|---|---|---|
| `ENGLISH64_ITEMS` | `ENGLISH64_X4.json` | wave 3b's sealed generator `r1w3b.gen64` (`build`), the E64 seed |
| `FACES64_ITEMS` | `FACES64_X4.json` | the same, the F64 seed |
| `SELF_WORLDS` | `SELF_X4.json` | `r1w4.gen_self`, the SELF seed (152 worlds: 88 planted faults, 64 clean copies) |
| `X4_SEAL_RECORD` | `X4_SEAL_RECORD.json` | `r1w4.custody_x4 seal` |

## 3. The steps (each prints verdicts and hashes only)

Let `C` = a new empty custody folder (for example `Documents\Codex\2026-10-19\r1_wave4\x4_custody`), `W3B` / `W3` the
extracted wave-3b / wave-3 folders, `X0` = `Documents\Codex\2026-10-15\r1_x0_custodian\HELM_R1_X0_FRESH_W1_20261015`,
and `D` = the seven `--derivation NAME=path` arguments of `SEED_RULE_X4.md` section 3.

1. **Band preflight (before the owner's line is used):**
   `python -B -m r1w4.custody_x4 preflight --custody C --x0-pkg X0 --w3b-dir W3B D` → must print `overlap_check: PASS`.
2. **Derive the seeds from the owner's line:**
   `python -B -m r1w4.custody_x4 derive --custody C --x0-pkg X0 --w3b-dir W3B D --approval-record <R1W4_APPROVAL_RECORD.json>`
   → refuses unless the record's line hashes to its own `owner_line_sha256`; must print `overlap_check: PASS`.
3. **Generate twice:** `python -B -m r1w4.custody_x4 generate --custody C --w3-dir W3 --w3b-dir W3B` → writes
   `work/gen_a/` and `work/gen_b/`; must print `regenerated_byte_identical: true`.
4. **Receiver's check:** `python -B -m r1w4.custody_x4 check --custody C --w3-dir W3 --w3b-dir W3B` with five
   `--extra-text-file` arguments: X1 `ENGLISH16_X1.json`, X2 `ENGLISH16_X2.json`, X2 `FACES16_X2.json`, X3
   `ENGLISH64_X3.json`, X3 `FACES64_X3.json` (each pinned by sha256 in the checker; under `Documents\Codex\`:
   `2026-10-18\r1_wave2\x1_custody\exam\ENGLISH16_X1.json` `87f1db78...`,
   `2026-10-19\r1_wave3\x2_custody\exam\ENGLISH16_X2.json` `205054b2...`, `...\FACES16_X2.json` `69202c0b...`,
   `2026-10-19\r1_wave3b\x3_custody\exam\ENGLISH64_X3.json` `a5a4286a...`, `...\FACES64_X3.json` `8c1ff66a...`).
   The checker reads them only as the overlap rule needs. Must print `all_pass: true`.
   **Text step rule:** if a file reports text-rule hits, re-run step 2 with `--start-slot PART=<chosen slot + 1>`, then
   steps 3 and 4; append `{part, from_slot, to_slot, hits}` to `work/TEXT_STEPS.json`. Nothing else may change.
5. **Seal:** `python -B -m r1w4.custody_x4 seal --custody C --w3-dir W3 --w3b-dir W3B --approval-record <...>` →
   writes `exam/` (the three exam files, `X4_SEAL_RECORD.json`, `X4_PINS.json`, `MANIFEST_X4.json`, `X4_SEALED.flag`).

## 4. The rule for every session that touches X4

- The custodian may copy, hash and compare the exam files. **Nobody** opens, prints, parses, summarises or logs them,
  and **no arm is run on X4 before the host run**. The X3-SELF file names which record each world plants a fault in:
  if the builder saw it, the scan could be tuned to it.
- The builder gets `X4_PINS.json` and its sha256 only.
- The coordinator ships, by hash, an `x4` carrier (top folder `x4`: the three exam files, `X4_PINS.json`,
  `X4_SEAL_RECORD.json`) and a `spent` carrier (top folder `spent`: the seven spent files listed in
  `r1w4/common_w4.py SPENT_FILES`, copied byte for byte from `r1_wave3\x2_custody\exam\` and
  `r1_wave3b\x3_custody\exam\`). Re-hash every file before the launch and refuse on any mismatch.
