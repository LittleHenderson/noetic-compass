# LAUNCH BRIEF — RB-W1T v2 (sealed test of the wide recipe brain), for the operator

Status: **SEALED v2, NOT LAUNCHED.** The builder launched nothing, held nothing and spent nothing. v1 (`b50f4ca4…`) is
VOID_SUPERSEDED_BY_V2 (never launched, no seed drawn).

## 0. What changed in v2 (coordinator decision "FIX FIRST")

RB-W1 v2 (PR #389, `045548b6`): the WIDE switch now extends the licensed path (licensed first; the wide brain only
where the licensed one cannot bind), and the wide reader's practice failure classes were fixed. On the builder's
published practice draw: WIDE 98 right, 0 wrong, fully learned 99 of 106 (bar 96); switch ON lost 0 of 64 on both
practice English-64 and Faces-64 (records identical to OFF). Builder prediction: `WIDE_BRAIN_EARNED_KEEP` about 0.35.

## 1. Approval

`APPROVAL_RECORD_RBW1T.json` (sha256 `3a223136c0b6ec58a3a607ade490ad6c8b11fadb60a658a5b26c10422d754a40`): owner line
`WIDE TEST at 1 USD` (18 bytes, sha256 `75904654…`), zip `7c04a40855b81c6bfc5c1a44fc4486e112fcc4bf16bc37b1e84d7b457c6b009e`,
freeze `b22690ced5a257ec964160103a28c03cea1d5730a0d006fb22c758a1be3d5ed9`, cap 1.00 USD, one attempt + one plumbing retry.

## 2. Custodian (laptop, 0 USD, a separate session)

`CUSTODIAN_PROCEDURE_RBW1T.md`. Output: `rbw1t_custody/` (exam stays on the laptop), carrier `RW_CARRIER_V1.zip` (top
folder `rw`: `INPUTS_RBW1T.json` + `RBW1T_PINS.json` only), a handoff with hashes and counts, `all_pass: true`.

## 3. Host job (one small CPU instance, us-west-2, the c21 image; no GPU, no torch)

| Source name | Archive | sha256 | Top folder |
|---|---|---|---|
| `rbw1t` | `HELM_RBW1T_20261019_SOURCE_RBW1T.zip` (v2) | `7c04a408…` | `HELM_RBW1T_20261019` |
| `r1w3` | `HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip` | `152bca2a…` | `HELM_R1_W3_20261019` |
| `r1w3b` | `HELM_R1_W3B_20261019_SOURCE_R1W3B.zip` | `a4f82556…` | `HELM_R1_W3B_20261019` |
| `w1` | `HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip` | `31f97d67…` | `HELM_R1_W1_20261015` |
| `rw` | the custodian's `RW_CARRIER_V1.zip` | from the handoff | `rw` |
| `x5spent` | X-REAL's `X5SPENT_CARRIER_V1.zip` (`claude_jobkit/xrealkit/`) | `653372b4e1eb03c190a401445bff6315f4b6465a48062628fbf832b0d714c69b` | `x5spent` |

Stage exactly `kit/STAGE_RBW1T.json`; set `--expected-freeze-sha256` to the v2 freeze above. Before launch:
`python -B kit/plan_check.py <job_plan.json> kit/run_rbw1t.py` must print PASS. The runner refuses before any package
code if a freeze, the carrier or a spent file is wrong. Expected host time about 300-500 s; expected charge about
0.01-0.03 USD; worst case about 0.70 USD for both tries; cap 1.00 USD. No automatic retry.

Record for the job: source (the six archives above), purpose (RB-W1T scored run), instance, launch / end times, limits
(cap 1.00 USD, stage limit 3,000 s, runner deadline 2,400 s), and cleanup (instance and volume terminated, shared prefix
purged, independent check within an hour, a direct read-only look).

## 4. Reading (laptop)

From a fresh extract of the sealed zip, PYTHONPATH = that folder:
`python -X utf8 -B -m rbw1t.merge_rbw1t --merge-input MERGE_INPUT_RBW1T.json --out RBW1T_READING.json`
(keys in `README_RBW1T.md`). Only the reader's verdict and status word are reported. The operator never opens an exam
file.

## 5. After

Back up the deliverable to `D:\tksCAS-archive\` with three sha256 confirmations; record the result in the spec sheet
(new §) and CHANGELOG with the exact numbers, negatives kept.
