# HELM_R1_W5_20261019 — HELM-R1 wave 5, the EYE_PAIRING wave

Status: **NOT LAUNCHED.** Nothing scored. No claim. Standard library only; no torch; no GPU. Claim ceiling
`SYNTHETIC_ONLY`. Preregistration: `../PREREGISTRATION_R1W5.md` (pre-code copy and its sha256 beside it).

## 1. What this package is

Wave 3's idle drive loop (`DRIVE_LOOP`) read `NEUTRAL`: its pairing of the 7 desires (Foundations F1-F7) with the 7
faculties was a seeded random permutation that never learned. RB-I3 (spec sheet 7.74) showed, in a stand-alone
synthetic world with builder-fixed seeds, that a Unity Eye which counts verified tries per (desire, faculty) pair and
whispers its best pairing earns its keep. Wave 5 puts that Eye into the wave-3b brain as ONE new switch, `EYE_PAIRING`,
and scores it on a custodian-sealed exam whose seeds come from the owner's sign line:

- **X5_PAIR**: RB-I3's own 7-kind world (vendored byte-identical), where each kind is bound to a real brain job that
  needs one brain part (cascade, cube store, English reader, triad) or none.
- **X5_E64 / X5_F64**: fresh English-64 and Faces-64 (wave 3b's families and sizes) for the no-harm mark.
- **Reproduction**: FULL on the spent X3 files must equal c38's FULL records ("same brain").

## 2. What it imports, never copies

| Neighbour | zip sha256 | freeze sha256 | Used for |
|---|---|---|---|
| wave 3b `HELM_R1_W3B_20261019` | `a4f82556...` | `a6d9dbc7...` | the English-64 / Faces-64 generator, format check, text rule and FULL arm runner |
| wave 3 v3 `HELM_R1_W3_20261019` | `152bca2a...` | `bd06f324...` | `live_w3.run_item`, the cascade and its mechanisms, the drive-loop geometry, the pair rule, HELM's `helm/` |
| wave 2 `HELM_R1_W2_20261018` | `21ad185d...` | `c8f82a6d...` | the work pool `pool_w2` |
| wave 1 v3 `HELM_R1_W1_20261015` | `31f97d67...` | `8c55c413...` | the licensed recipe brain and its read-back receipt |

`vendor/rb_i3/` is RB-I3's code (byte-identical, `SOURCE_MANIFEST.json` `9ecfb7e7...`); `vendor/u1b_unity_eye/` is
U1b's 14-line `ConcertLedger`, the Eye's whisper channel (deviation D-W5-4). Every neighbour is checked against its
freeze before anything is imported from it (`r1w5/common_w5.setup_paths`).

## 3. Files

- `r1w5/drive_x5.py` — the idle drive loop: FULL (wave 3's rule), EYE_PAIRING and its controls, the cut, the Q6 guard,
  the Q5 decline.
- `r1w5/jobs_x5.py` — the seven brain jobs, the verifier, the independent re-checker, the job map.
- `r1w5/live_w5.py` — English-64 / Faces-64 with the drive loop hooked into the live loop (a subclass; no HELM edit).
- `r1w5/seed_rule_x5.py`, `r1w5/custody_x5.py` (the blind build), `r1w5/gen_x5pair.py`, `r1w5/check_x5_format.py`,
  `r1w5/seal_x5.py`, `x5_contract/` — the custodian's tools and contract.
- `r1w5/switches_w5.py`, `r1w5/pool_w5.py`, `r1w5/summary_w5.py`, `tests_r1w5/test_run_w5.py`, `kit/` — the host run.
- `r1w5/merge_r1w5.py` — the frozen reader (laptop).
- `FROZEN_R1W5.json`, `RUN_LIMITS_R1W5.json`, `SOURCE_CUT.json`, `PACKAGE_FREEZE.json`.

## 4. The run, in order (coordinator)

1. Owner signs the line in `OWNER_SIGN_REQUEST_R1W5.md`. Approval record (schema `helm.r1w5.approval/1`):
   `owner_line_verbatim`, `owner_line_sha256`, `package_zip_sha256`, `package_freeze_sha256`, cap, attempts,
   `superseded_by: null`.
2. X5 by a separate custodian (`x5_contract/`), laptop, 0 USD.
3. Host: sources `r1w5` (this zip), `r1w3b`, `r1w3`, `r1w2`, `w1` (the four neighbour zips), `x5` (X5 carrier, top
   folder `x5`), `x3spent` (carrier of `ENGLISH64_X3.json` and `FACES64_X3.json`, top folder `x3spent`). Stage exactly
   `kit/STAGE_R1W5.json` with `--expected-freeze-sha256` = this package's freeze. Before launch:
   `python -B kit/plan_check.py <job_plan.json> kit/run_r1w5.py` must print PASS.
4. Reading (laptop, from an extracted copy of the sealed zip):
   `python -B -m r1w5.merge_r1w5 --merge-input MERGE_INPUT_R1W5.json --out R1_W5_READING.json`.

MERGE_INPUT_R1W5.json keys (each path with `<key>_sha256`): `host_reading` (`r1w5_out/R1_W5_HOST.json`), `pins`
(`X5_PINS.json`, with `X5_SEAL_RECORD.json` beside it), `x5_worlds` (`X5PAIR_WORLDS.json`, the pinned one),
`run_record`, `supervisor_receipt`, `sources_manifest`, `approval_record`, `c37_reading` (`R1_W3_READING.json`,
`1cc7dba8...`), `c38_host` (`R1_W3B_HOST.json`, `5f479f61...`); plus `package_zip_sha256`, `package_freeze_sha256`,
`w3b_dir`, `w3_dir`, `w2_dir`, `w1_dir`.

## 5. Reading the result

`HARD_GATES_PASS` with one of `EYE_PAIRING_EARNED_KEEP`, `EYE_PAIRING_HARMED`, `LEARNING_DID_NOT_EARN_KEEP`,
`INCONCLUSIVE`. `FAILURE`: a hard gate broke (named); word `INCONCLUSIVE`. `INSTRUMENT_ERROR`: the measuring went
wrong; nothing about the brain is read. A stage exit code is never the verdict.
