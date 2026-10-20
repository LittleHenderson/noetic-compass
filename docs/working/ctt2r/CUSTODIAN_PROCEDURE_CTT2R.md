# CTT-2R — what the custodian session does (census, new LLM pool, blind draws, seal)

Written 2026-10-19 by the CTT-2R builder. The builder never sees the census rows, the pool, a draw, a key or a seed.
A **separate custodian session** does every step below and hands over **hashes and counts only**.

## 0. When, where, rules

- Only after `APPROVAL_RECORD_CTT2R.md` / `.json` exist (written by program from the owner's pinned bytes
  `CTT RULE TEST at 1.50 USD` and the FINAL sealed zip's sha256).
- Laptop, one Python process at a time (check for another `python.exe ... worker.py` and wait; never kill it), each
  command under 300 s and 300 MiB, no torch, 0 USD. Network ONLY in step 4, and only to the two writer APIs.
- Never open, print, parse or summarise an exam file, a pool row or a key by hand: programs read them; people read
  hashes, counts and PASS/FAIL. Never edit a file by hand.
- Names below: `PKG` = a fresh extract of the sealed `HELM_CTT2R_20261019_SOURCE_CTT2R.zip` (its folder
  `HELM_CTT2R_20261019`); `CTT` = a fresh extract of `HELM_CTT_20261019_SOURCE_CTT.zip` (`f280633d…`, folder
  `HELM_CTT_20261019`); `XPKG` = a fresh extract of `HELM_XREAL_20261019_SOURCE_XREAL.zip` (`a9b4c954…`);
  `W3` = `Documents\Codex\2026-10-19\r1_wave3\HELM_R1_W3_20261019` (wave-3 v3, freeze `bd06f324…`);
  `XR` = `Documents\Codex\2026-10-19\x_real`; `CT` = `Documents\Codex\2026-10-19\cas_token_transformer`;
  `CUS` = `Documents\Codex\2026-10-19\ctt2r_custody_only` (NEW, custodian-only; never shared with a builder or
  an operator; its path must contain "custod"); `RT` = `python -B -I -X utf8 PKG\contract\xrun.py PKG`.

## 1. The owner's line (by program)

```
RT ctt2r.seed_rule_2r line --approvals C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md --out CUS\work\OWNER_LINE_CTT2R.txt
```
Must print `"bytes": 25` and sha256 `0ed5828323f6fa100eb7287000ca454602ead9b1547bfc09d52862d5efa1a193`.

## 2. The reader v1.1 overlay

```
RT ctt2r.env_2r overlay --w3-dir W3 --out CUS\overlay
```
Must print `"ok": true`.

## 3. Part R census R0 (no seed needed; counts only) — FIRST, before anything else is drawn

```
RT ctt2r.census_r census --xreal-dir XPKG\HELM_XREAL_20261019 --frame XR\frames\FRAME_S.jsonl --overlay CUS\overlay
   --ctt-dir CTT\HELM_CTT_20261019 --forbidden-list XPKG\HELM_XREAL_20261019\FORBIDDEN_LIST_XREAL.json
   --xreal-inputs XR\xr_custody\carrier\xr\INPUTS_XREAL.json --ctt-exam CT\ctt_custody\carrier\emachine\E_MACHINE_S_CTT.json
   --rtr-inputs C:\Users\wakil\Documents\Codex\2026-10-19\rtr1\rtr_custody\carrier\rt\INPUTS_RTR.json
   --out CUS\work\CENSUS_R_CTT2R.json
```
- Exit 0 (`"part_r": "EXERCISABLE"`): go on.
- **Exit 5 (`"part_r": "NOT_EXERCISED"`, R1 below 24): STOP.** Send the coordinator the printed counts line and the
  census file's sha256. Wait for the coordinator's choice (PREREGISTRATION_CTT2R.md amendment A-2R-1 item 4):
  (a) widen the frame = new design, nothing more here; (b) Part K only = go on, skip step 6, and add
  `--part-r-not-exercised CUS\work\CENSUS_R_CTT2R.json` to steps 8 and 9.
- Exit 6 (over its 280 s budget): STOP; the census moves to a small AWS CPU host (operator; inside the 1.50 USD cap).
- Exit 3: a pin refused; STOP and report which.

## 4. Part K: the NEW LLM-written pool (custodian plays the writer-wrangler; pool stays in CUS)

```
RT ctt2r.writers_k plan  --custody-dir CUS\k_pool
RT ctt2r.writers_k call  --custody-dir CUS\k_pool --call G_S1        (then G_S2, G_S3, G_S4, G_D1, D_S1 ... D_S4, D_D1)
RT ctt2r.writers_k clean --custody-dir CUS\k_pool
```
- One call per process. A failed call is retried as a NEW attempt (`--attempt 2`, `3`); after 3 failures STOP and
  report. If Gemini's default model (`gemini-3.5-flash`) has no free quota, pass `--model-id <id>` (recorded in
  the request file) — a model change is recorded, never hidden. Keys come from `~/.cas_llm_keys.env`; never printed.
- `clean` prints counts only (units per writer and family, drop reasons). Keep `RAW\` (create-only).

## 5. The seed

```
RT ctt2r.seed_rule_2r derive --line-file CUS\work\OWNER_LINE_CTT2R.txt --zip <the FINAL sealed zip> --out CUS\work\SEED_DERIVATION_CTT2R.json
```
Must print `"overlap_check": "PASS"`. Exit 4 = STOP (`CTT2R_BLOCKED_SEED.json`), never another band.

## 6. Part R draw (skip if Part R is NOT_EXERCISED and the coordinator chose (b))

Run twice, into two EMPTY folders (the second is the receiver's redraw):
```
RT ctt2r.census_r draw <the step-3 arguments> --census CUS\work\CENSUS_R_CTT2R.json
   --derivation CUS\work\SEED_DERIVATION_CTT2R.json --out-dir CUS\exam
RT ctt2r.census_r draw <the same> --out-dir CUS\work\redraw
```

## 7. Part K draw

```
RT ctt2r.draw_k --custody-dir CUS\k_pool --c45-pool CT\llm_written\POOL_LLM_WRITTEN.jsonl
   --derivation CUS\work\SEED_DERIVATION_CTT2R.json --out-dir CUS\exam
RT ctt2r.draw_k <the same> --out-dir CUS\work\redraw
```
Exit 4 = a cell ran out (`CTT2R_BLOCKED_DRAW_K.json`): STOP and report; never fill from another cell.

## 8. The receiver's check (must print `"all_pass": true` BEFORE the seal)

```
RT ctt2r.seal_2r check --a CUS\exam --b CUS\work\redraw --derivation CUS\work\SEED_DERIVATION_CTT2R.json
   [--part-r-not-exercised CUS\work\CENSUS_R_CTT2R.json] --out CUS\work\RECEIVER_CHECK_CTT2R.json
```

## 9. Seal and carrier

```
RT ctt2r.seal_2r seal --exam-dir CUS\exam --derivation CUS\work\SEED_DERIVATION_CTT2R.json
   --receiver-check CUS\work\RECEIVER_CHECK_CTT2R.json --line-file CUS\work\OWNER_LINE_CTT2R.txt
   --zip <the FINAL sealed zip> [--part-r-not-exercised CUS\work\CENSUS_R_CTT2R.json]
RT ctt2r.seal_2r carrier --exam-dir CUS\exam --out-dir CUS\carrier\exam
```
The carrier holds only the inputs file(s) and `SEAL_RECORD_CTT2R.json`. Hand to the coordinator: the carrier's file
hashes, the seal record's sha256, the derivation's sha256, the census's sha256 and counts line, the pool summary's
sha256 and counts, the draw counts lines. Keys (`KEYS_*`), sample records, the pool and `RAW\` stay in CUS.

## 10. After the run

```
RT ctt2r.seal_2r confirm --exam-dir CUS\exam --out CUS\work\SEAL_CONFIRM_CTT2R.json
```
Then the coordinator fills `MERGE_INPUT_CTT2R.json` from the host's draft plus the laptop paths of `KEYS_K_CTT2R.json`
(and `KEYS_R_CTT2R.json`), `SEAL_RECORD_CTT2R.json`, `SEAL_CONFIRM_CTT2R.json`, `APPROVAL_RECORD_CTT2R.json`,
`SEED_DERIVATION_CTT2R.json` (each with its sha256), and runs the frozen reader:
```
RT ctt2r.merge_2r --merge-input MERGE_INPUT_CTT2R.json --ctt-dir CTT\HELM_CTT_20261019 --overlay CUS\overlay --out CTT2R_READING.json
```
