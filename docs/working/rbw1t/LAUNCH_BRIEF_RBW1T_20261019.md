# LAUNCH BRIEF — RB-W1T v3 (second sealed test of the wide recipe brain), for the operator

Status: **SEALED v3, NOT LAUNCHED.** The builder launched nothing, held nothing and spent nothing. v2 (`7c04a408…`) is
SPENT_BY_C46 (scored once: `WIDE_LEARNING_DID_NOT_EARN_KEEP`; its brief is `v2_spent_LAUNCH_BRIEF_RBW1T_20261019.md`).
v1 (`b50f4ca4…`) is void.

## 0. What changed in v3 (amendment A-RBW1T-2, PREREGISTRATION_RBW1T.md section 19)

RB-W1 v3 (PR #392, merge `65b86282`): ingredient lines split only where a new amount begins, names taken from the
line's own words, the ran-out phrase found inside exactly one line, two amounts for one ingredient asked about, ties
answered, dish-name variants bound, a missing dish name asked once. It is the ONLY change to the HELM cut. On the
builder's published practice draw v2: WIDE 101 right, 0 wrong, fully learned 100 of 106 (bar 96); switch ON lost 0 of
64 on practice English-64 and Faces-64. The c46 exam's 128 recipes and the practice draw v2 are excluded from the v3
draw. Marks, arms and thresholds are unchanged. Builder prediction: `WIDE_BRAIN_EARNED_KEEP` about 0.35,
`WIDE_LEARNING_DID_NOT_EARN_KEEP` about 0.4.

## 1. Approval

`APPROVAL_RECORD_RBW1T.json` (v3; sha256 `954c7364efeedd61fc92e2869bdff2a5588b6aea0271bf9f99a88dac30e852ab`): owner line
`WIDE TEST 2 at 1 USD` (20 bytes, sha256 `fd82691eff719a757cca296740faf5e9baf02bc8582b6650193bddb9b0878b8b`), zip
`3a8ae37eb51c18414bfa83a71b9079dd7ec2282bec6ba3952d86ac0454f0e967`, freeze
`04eef88645acbd0c89de9e6e914d8faf2896939769e11f4d4c93f2dfc12e84f4`, cap 1.00 USD, one attempt + one plumbing retry.

## 2. Custodian (laptop, 0 USD, a separate session)

`CUSTODIAN_PROCEDURE_RBW1T.md` (v3). Output: `rbw1t_custody_v3/` (exam stays on the laptop; the spent
`rbw1t_custody/` is never touched), carrier `RW_CARRIER_V3.zip` (top folder `rw`: `INPUTS_RBW1T.json` +
`RBW1T_PINS.json` only), a handoff with hashes, counts and the drawn ids, `all_pass: true`.

## 3. Host job (one small CPU instance, us-west-2, the c21 image; no GPU, no torch)

| Source name | Archive | sha256 | Top folder |
|---|---|---|---|
| `rbw1t` | `HELM_RBW1T_20261019_SOURCE_RBW1T.zip` (v3) | `3a8ae37e…` | `HELM_RBW1T_20261019` |
| `r1w3` | `HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip` | `152bca2a…` | `HELM_R1_W3_20261019` |
| `r1w3b` | `HELM_R1_W3B_20261019_SOURCE_R1W3B.zip` | `a4f82556…` | `HELM_R1_W3B_20261019` |
| `w1` | `HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip` | `31f97d67…` | `HELM_R1_W1_20261015` |
| `rw` | the custodian's `RW_CARRIER_V3.zip` | from the v3 handoff | `rw` |
| `x5spent` | X-REAL's `X5SPENT_CARRIER_V1.zip` (`claude_jobkit/xrealkit/`) | `653372b4e1eb03c190a401445bff6315f4b6465a48062628fbf832b0d714c69b` | `x5spent` |

Stage exactly `kit/STAGE_RBW1T.json`; set `--expected-freeze-sha256` to the v3 freeze above. Before launch:
`python -B kit/plan_check.py <job_plan.json> kit/run_rbw1t.py` must print PASS. The runner refuses before any package
code if a freeze, the carrier or a spent file is wrong. c46 took 148.95 host seconds and 0.01 USD on one m6i.large;
expect the same; worst case about 0.70 USD for both tries; cap 1.00 USD. No automatic retry.

Record for the job: source (the six archives above), purpose (RB-W1T v3 scored run), instance, launch / end times,
limits (cap 1.00 USD, stage limit 3,000 s, runner deadline 2,400 s), and cleanup (instance and volume terminated,
prefix purged, independent check within an hour, a direct read-only look).

## 4. Reading (laptop)

From a fresh extract of the sealed v3 zip, PYTHONPATH = that folder:
`python -X utf8 -B -m rbw1t.merge_rbw1t --merge-input MERGE_INPUT_RBW1T.json --out RBW1T_READING.json`
(keys in `README_RBW1T.md`; `exam_dir` and `carrier_dir` point into `rbw1t_custody_v3/`). Only the reader's verdict
and status word are reported. The operator never opens an exam file.

## 5. After

Back up the deliverable to `D:\tksCAS-archive\` with three sha256 confirmations; record the result in the spec sheet
(new §) and CHANGELOG with the exact numbers, negatives kept.
