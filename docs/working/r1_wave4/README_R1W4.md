# HELM_R1_W4_20261019 — HELM-R1 wave 4, the EYE_SCAN wave

Status: **NOT LAUNCHED.** Nothing scored. No claim. Standard library only; no torch.

## 1. What this package is

Wave 4 runs the SAME brain with the SAME switches as wave 3b (c38) and adds ONE switch, `EYE_SCAN`: U3-T1's read-only
self-scan by the Unity Eye (a Mind scan and a Body scan; report AND whisper; the Eye never writes), ported onto the
live English path. The new thing tested is the WHISPER RECEIVER on the real presentation path
(`r1w4/eye_live.py WhisperReceiver`): between the loop's result (`ExamLoop3.process_turn`) and the speaker
(`helm_chat._speak`); a held reply is spoken by `helm_voice._say_plain`. Exams: the fresh, custodian-sealed X4
(English-64, Faces-64 and the X3-SELF planted-fault exam of TEST_PLAN_U3), the carried exams on spent / exposed data
(Gate B, Task B, CCE, Cascade, Idle), and FULL on the spent X3 files (same brain as c38).

## 2. What it imports, never copies

| Neighbour | zip sha256 | freeze sha256 | Used for |
|---|---|---|---|
| wave 3b `HELM_R1_W3B_20261019` | `a4f82556...` | `a6d9dbc7...` | the 64-item generator and format check, the text rule, the reproduction command |
| wave 3 v3 `HELM_R1_W3_20261019` | `152bca2a...` | `bd06f324...` | HELM's live loop (`helm/`), `live_w3` (build_loop, scoring), the families (`gen_live.W`), the pair rule, Cascade / Idle units |
| wave 2 `HELM_R1_W2_20261018` | `21ad185d...` | `c8f82a6d...` | the work pool (Unit, dispatch), the Gate B / Task B / CCE unit commands |
| wave 1 v3 `HELM_R1_W1_20261015` | `31f97d67...` | `8c55c413...` | the licensed recipe brain |

U3-T1 (`Documents\Codex\2026-10-19\u3_t1\`) is not a sealed zip: its rules are COPIED into `r1w4/eye_live.py` and
`r1w4/voice_live.py`, each citing its source file's sha256 (`common_w4.PROVENANCE`).

## 3. Files

- `r1w4/eye_live.py` — the Eye on the live path (snapshot, Mind and Body scans, SELF_REPORT, gate, receiver).
- `r1w4/voice_live.py` — the plain-English self-report and its honesty check.
- `r1w4/session_w4.py` — one session (an item or a world) with the Eye, the planter and the checklist; the arm runner.
- `r1w4/planter_w4.py` — the five planted body faults of X3-SELF.
- `r1w4/gen_self.py`, `r1w4/formats_w4.py` — the X3-SELF generator and the X4 formats / text rule.
- `r1w4/seed_rule_x4.py`, `r1w4/check_x4_format.py`, `r1w4/custody_x4.py`, `x4_contract/` — the custodian's tools and contract.
- `r1w4/eye_sidecar.py` — EYE_SCAN at the unit boundaries of the carried exams.
- `r1w4/switches_w4.py`, `r1w4/pool_w4.py`, `r1w4/summary_w4.py`, `tests_r1w4/test_run_w4.py`, `kit/` — the host run.
- `r1w4/merge_r1w4.py` — the frozen reader (laptop).
- `FROZEN_R1W4.json`, `RUN_LIMITS_R1W4.json`, `SOURCE_CUT.json`, `PACKAGE_FREEZE.json`.

## 4. The run, in order (coordinator)

1. Owner signs the line in `OWNER_SIGN_REQUEST_R1W4.md`. Approval record `R1W4_APPROVAL_RECORD.json` (schema
   `helm.r1w4.approval/1`): `owner_line_verbatim`, `owner_line_sha256`, `package_zip_sha256`, `package_freeze_sha256`,
   `cap_usd`, `attempts`, `superseded_by: null`.
2. X4 by a separate custodian (`x4_contract/X4_CUSTODIAN_CONTRACT.md`), laptop, 0 USD.
3. Host: sources `r1w4` (this zip), `r1w3b`, `r1w3`, `r1w2`, `w1` (the four neighbour zips), `x4` (the X4 carrier, top
   folder `x4`), `spent` (the spent carrier, top folder `spent`). Stage exactly `kit/STAGE_R1W4.json` with
   `--expected-freeze-sha256` = this package's freeze. Before launch: `python -B kit/plan_check.py <job_plan.json>
   kit/run_r1w4.py` must print PASS.
4. Reading (laptop, from an extracted copy of the sealed zip):
   `python -B -m r1w4.merge_r1w4 --merge-input MERGE_INPUT_R1W4.json --out R1_W4_READING.json`.

MERGE_INPUT_R1W4.json keys (each path with `<key>_sha256`): `host_reading` (`r1w4_out/R1_W4_HOST.json`), `pins`
(`X4_PINS.json`, with `X4_SEAL_RECORD.json` beside it), `run_record`, `supervisor_receipt`, `sources_manifest`,
`approval_record`, `c38_reading` (`384f3038...`), `c38_host` (`5f479f61...`), `c37_reading` (`1cc7dba8...`), `c37_host`
(`e2bf6d4c...`); plus `package_zip_sha256`, `package_freeze_sha256`, `w3b_dir`, `w3_dir`, `w2_dir`, `w1_dir`.

## 5. Reading the result

Test verdict: PASS / FAILURE (a hard gate broke, named) / INSTRUMENT_ERROR (the measuring went wrong; nothing about the
brain is read). Then exactly one EYE_SCAN word: `EYE_SCAN_EARNED_KEEP`, `EYE_SCAN_HARMED`, `EYE_SCAN_NO_EFFECT` or
`INCONCLUSIVE`. A positive word stays `ENGINEERED-NOT-VALIDATED` within `SYNTHETIC_ONLY`. A stage exit code is never
the verdict.

Known limit, stated now: the receiver holds back the PRESENTATION, not the loop's own work. On a held SUCCESS_EVALUATED
turn the loop has already written its yield record (in every arm alike, before the receiver runs).
