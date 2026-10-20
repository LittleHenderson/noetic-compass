# LAUNCH BRIEF — RB-W1T (sealed test of the wide recipe brain), for the operator

Status: **SEALED, NOT LAUNCHED.** The builder launched nothing, held nothing and spent nothing.

## 0. Before anything: read this finding

On the builder's published practice draw the wide brain gave **0 wrong answers**, but it fully learned only **54 of
106** answerable representable recipes (the mark needs 90%), and with the switch ON it **lost 55 of 64** English-64
items and **42 of 64** Faces-64 items (the mark allows 2). The reason is structural: RB-W1's switch sends every turn to
the wide reader, which has no store read, no absence, no faces. The builder's prediction for the sealed run is
`WIDE_BRAIN_HARMED` (about 0.85). The owner's pre-approval covers the run as sealed; whether to run it as sealed or to
first rebuild the switch (recipe turns only) is the owner's or coordinator's choice, not the builder's.

## 1. Approval

`APPROVAL_RECORD_RBW1T.json` (sha256 `97fb18ae...`): owner line `WIDE TEST at 1 USD` (18 bytes, sha256 `75904654...`),
zip `b50f4ca42178d4c43e43945267cc980aebd05a10f8e0d932d00e3eabd4495809`, freeze
`fadf08f6faf13ebcdb633b7894ebe515838465c52a90c51f6507f2371a28f8b1`, cap 1.00 USD, one attempt + one plumbing retry.

## 2. Custodian (laptop, 0 USD, a separate session)

`CUSTODIAN_PROCEDURE_RBW1T.md`. Output: `rbw1t_custody/` (exam stays on the laptop), carrier `RW_CARRIER_V1.zip` (top
folder `rw`: `INPUTS_RBW1T.json` + `RBW1T_PINS.json` only), a handoff with hashes and counts, `all_pass: true`.

## 3. Host job (one small CPU instance, us-west-2, the c21 image; no GPU, no torch)

| Source name | Archive | sha256 | Top folder |
|---|---|---|---|
| `rbw1t` | `HELM_RBW1T_20261019_SOURCE_RBW1T.zip` | `b50f4ca4...` | `HELM_RBW1T_20261019` |
| `r1w3` | `HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip` | `152bca2a...` | `HELM_R1_W3_20261019` |
| `r1w3b` | `HELM_R1_W3B_20261019_SOURCE_R1W3B.zip` | `a4f82556...` | `HELM_R1_W3B_20261019` |
| `w1` | `HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip` | `31f97d67...` | `HELM_R1_W1_20261015` |
| `rw` | the custodian's `RW_CARRIER_V1.zip` | from the handoff | `rw` |
| `x5spent` | X-REAL's `X5SPENT_CARRIER_V1.zip` (`claude_jobkit/xrealkit/`) | `653372b4...` | `x5spent` |

Stage exactly `kit/STAGE_RBW1T.json`; set `--expected-freeze-sha256` to `fadf08f6...` (full value above). Before
launch: `python -B kit/plan_check.py <job_plan.json> kit/run_rbw1t.py` must print PASS. The runner refuses before any
package code if a freeze, the carrier, or a spent file is wrong. Expected host time about 300-500 s; expected charge
about 0.01-0.03 USD; worst case about 0.70 USD for both tries; cap 1.00 USD. No automatic retry.

Record for the job: source (the six archives above), purpose (RB-W1T scored run), instance, launch / end times,
limits (cap 1.00 USD, stage limit 3,000 s, runner deadline 2,400 s), and cleanup (instance and volume terminated,
shared prefix purged, independent check within an hour, a direct read-only look).

## 4. Reading (laptop)

From a fresh extract of the sealed zip, PYTHONPATH = that folder:
`python -X utf8 -B -m rbw1t.merge_rbw1t --merge-input MERGE_INPUT_RBW1T.json --out RBW1T_READING.json`
(keys in `README_RBW1T.md` section "The run, in order"). Only the reader's verdict and status word are reported. The
operator never opens an exam file.

## 5. After

Back up the deliverable to `D:\tksCAS-archive\` with three sha256 confirmations; record the result in the spec sheet
(new §) and CHANGELOG with the exact numbers, negatives kept.
