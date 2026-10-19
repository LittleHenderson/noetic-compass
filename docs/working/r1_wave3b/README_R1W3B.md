# HELM_R1_W3B_20261019 — HELM-R1 wave 3b, the roomier exam

Status: **NOT LAUNCHED.** Nothing scored. No claim. Standard library only; no torch.

## 1. What this package is

Wave 3 (job c37) read 16 pairs of parts. Four came back `CEILING_NOT_READABLE`: the 16-item English and Faces exams had
too little room to tell how two parts work together. Wave 3b runs the SAME brain with the SAME switches on two
roomier, harder exams, English-64 and Faces-64, and only the arms those four pairs need.

The four pairs: `CUBE_STORE x ENGLISH_IN` (English-64), `ENGLISH_IN x TRIAD` (Faces-64), `ENGLISH_IN x VOICE`
(English-64 and Faces-64), `TRIAD x VOICE` (Faces-64).

## 2. What it imports, never copies

| Neighbour | zip sha256 | freeze sha256 | Used for |
|---|---|---|---|
| wave 3 v3 `HELM_R1_W3_20261019` | `152bca2a...` | `bd06f324...` | the generator's families and pools, `live_w3.run_item`, `live_settings`, the pair rule, the text rule, HELM's live loop (`helm/`) |
| wave 2 `HELM_R1_W2_20261018` | `21ad185d...` | `c8f82a6d...` | the work pool `pool_w2` (Unit, dispatch, run_cmd) |
| wave 1 v3 `HELM_R1_W1_20261015` | `31f97d67...` | `8c55c413...` | the licensed recipe brain |

Each is checked against its freeze before anything is imported from it (`common_w3b.w3_import`, the runner, the host
test, the reader).

## 3. Files

- `r1w3b/gen64.py` — English-64 / Faces-64 generators (wave 3's family bodies + the difficulty ladder).
- `r1w3b/live64.py` — the 64-item format check; runs an arm through wave 3's `run_item`.
- `r1w3b/switches_w3b.py` — the arms (15) and the two reproduction units.
- `r1w3b/text_rule_w3b.py` — the text rule: A1 carried + T3b.
- `r1w3b/seed_rule_x3.py`, `r1w3b/check_x3_format.py`, `x3_contract/` — the custodian's tools and contract.
- `r1w3b/pool_w3b.py`, `r1w3b/summary_w3b.py`, `tests_r1w3b/test_run_w3b.py`, `kit/` — the host run.
- `r1w3b/merge_r1w3b.py` — the frozen reader (laptop).
- `FROZEN_R1W3B.json`, `RUN_LIMITS_R1W3B.json`, `PACKAGE_FREEZE.json`.

## 4. The run, in order (coordinator)

1. Owner signs the line in `OWNER_SIGN_REQUEST_R1W3B.md`. Approval record (schema `helm.r1w3b.approval/1`):
   `owner_line_verbatim`, `owner_line_sha256`, `package_zip_sha256`, `package_freeze_sha256`, cap, attempts,
   `superseded_by: null`.
2. X3 by a separate custodian (`x3_contract/`), laptop, 0 USD.
3. Host: sources `r1w3b` (this zip), `r1w3` (wave 3 v3 zip), `r1w2` (wave 2 zip), `w1` (wave 1 v3 zip), `x3` (X3
   carrier, top folder `x3`), `x2lang` (carrier of `ENGLISH16_X2.json` and `FACES16_X2.json`, top folder `x2lang`).
   Stage exactly `kit/STAGE_R1W3B.json` with `--expected-freeze-sha256` = this package's freeze. Before launch:
   `python -B kit/plan_check.py <job_plan.json> kit/run_r1w3b.py` must print PASS.
4. Reading (laptop, from an extracted copy of the sealed zip):
   `python -B -m r1w3b.merge_r1w3b --merge-input MERGE_INPUT_R1W3B.json --out R1_W3B_READING.json`.

MERGE_INPUT_R1W3B.json keys (each path with `<key>_sha256`): `host_reading` (`r1w3b_out/R1_W3B_HOST.json`), `pins`
(`X3_PINS.json`, with `X3_SEAL_RECORD.json` beside it), `run_record`, `supervisor_receipt`, `sources_manifest`,
`approval_record`, `c37_reading` (`R1_W3_READING.json`, `1cc7dba8...`), `c37_host` (`R1_W3_HOST.json`, `e2bf6d4c...`);
plus `package_zip_sha256`, `package_freeze_sha256`, `w3_dir`, `w2_dir`, `w1_dir`.

## 5. Reading the result

PASS: every instrument row and hard gate held; each pair word stands. FAILURE: a gate broke (named); no word
licensed. INSTRUMENT_ERROR: the measuring went wrong; nothing about the brain is read. A stage exit code is never the
verdict.
