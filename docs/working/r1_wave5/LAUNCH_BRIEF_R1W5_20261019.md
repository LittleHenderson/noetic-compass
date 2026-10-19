# Launch brief: HELM-R1 wave 5 (R1W5), the EYE_PAIRING wave (written 2026-10-19, Pacific)

**NOT LAUNCHED. No ledger hold placed.** The builder does not launch. Order of events after the owner signs:

1. **Owner signs** the exact line in `OWNER_SIGN_REQUEST_R1W5.md` (it carries `b6598687` and the cap). If the owner
   changes Q5, Q6 or Q9 first, the builder reseals and a new line is written; the old line is void. The coordinator
   writes `OWNER_APPROVAL_R1W5_<utc>.json` (schema `helm.r1w5.approval/1`): `owner_line_verbatim`,
   `owner_line_sha256` (sha256 of its exact UTF-8 bytes; the reader's I9 recomputes it and I10 compares it with the
   X5 seed source), `package_zip_sha256` `b6598687190bc9e41f52695144eeeac5428913ab804f8bec64841093ea825d6c`,
   `package_freeze_sha256` `a325ea13b8851f9d8ed928dd73c2c3892315fa534fc876a146c6eb975bdc0334`, cap, attempts,
   `superseded_by: null`. Any reseal after signing is a new package and needs a new sign line (I9).
2. **Ledger hold** (coordinator): the signed cap against `Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json`
   (read after c38: 111.22 of 200.00 used, 88.78 unreserved).
3. **X5** (a separate custodian session, `HELM_R1_W5_20261019/x5_contract/X5_CUSTODIAN_CONTRACT.md` and
   `SEED_RULE_X5.md`), laptop, 0 USD: `r1w5.seed_rule_x5` on the owner's line with the seven pinned derivations (must
   print `overlap_check: PASS`); `r1w3b.gen64` for E64 and F64 with the derived seeds; `r1w5.gen_x5pair make` for the
   11 lives; the receiver's check `r1w5.check_x5_format` with the five pinned spent files must print `all_pass: true`
   BEFORE the seal (expect a text step about one time in six for English-64, D-W5-9); `r1w5.seal_x5` writes
   `X5_SEAL_RECORD.json` and `X5_PINS.json`; hashes only to the coordinator. The builder never sees X5.
4. **The scored host run** (coordinator, the claude_jobkit precedent of c37 / c38):
   - Sources (each an archive pinned by sha256 in `sources_manifest.json`):
     `r1w5` = `HELM_R1_W5_20261019_SOURCE_R1W5.zip` `b6598687...`;
     `r1w3b` = `HELM_R1_W3B_20261019_SOURCE_R1W3B.zip` `a4f82556bf0fc26de5635a7c81ec8f5053951d4c64a3906c8e5dd474e3814d26`;
     `r1w3` = `HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip` `152bca2a3c869212642f96514e7d485413727bf92cf67e9aff1774cefa532362`;
     `r1w2` = `HELM_R1_W2_20261018_SOURCE_R1W2.zip` `21ad185d885a11c4ee498e31e106c71ca608dc9edea1b201a283347086d58dc5`;
     `w1` = `HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip` `31f97d67122b45860cdff2b03481655fa502ff359f10b70a181904972ddbb3c9`;
     `x5` = a carrier of the X5 folder (top folder `x5`); `x3spent` = a carrier (top folder `x3spent`) of
     `ENGLISH64_X3.json` `a5a4286a...` and `FACES64_X3.json` `8c1ff66a...` from `r1_wave3b\x3_custody\exam\`, shipped
     by path and checked by sha256 only (never opened by the operator or the builder).
   - Stage: exactly `HELM_R1_W5_20261019/kit/STAGE_R1W5.json` (`r1_w5_host_run`), with `--expected-freeze-sha256
     a325ea13...`; supervisor = the package's `kit/job_supervisor.py` (wave 2's, byte for byte); required outputs
     `r1w5_out/R1_W5_HOST.json` and its `.sha256`. Before launch: `python -B kit/plan_check.py <job_plan.json>
     kit/run_r1w5.py` must print PASS.
   - Host: one `m6i.xlarge`, us-west-2, `ami-0dddfa1ffa6b87af7`, 2-CPU slice, 14 GiB; `R1W5_WORKERS=2`; runner
     deadline 2,400 s; no automatic retry (`RUN_LIMITS_R1W5.json`).
   - Expected: about 8-12 minutes of host, about 0.03-0.04 USD at list (0.07-0.09 conservative); at most about 0.35.
   - **Attempts: one scored + at most one plumbing retry** (only if no unit of the scored pool started; same zip,
     same X5 pins).
5. **Cleanup and backup:** terminate host and volumes, release the slot, remove temporary role/profile/bucket,
   independent cleanup check within an hour; back up to `D:\tksCAS-archive\` with three sha256 confirmations; ledger
   closeout.
6. **The reading (laptop):** `MERGE_INPUT_R1W5.json` (`README_R1W5.md` section 4), then `python -B -m
   r1w5.merge_r1w5 --merge-input MERGE_INPUT_R1W5.json --out R1_W5_READING.json` from an extracted copy of the
   sealed zip, with `w3b_dir`, `w3_dir`, `w2_dir`, `w1_dir` pointing at the sealed neighbour packages, `c37_reading`
   at `r1_wave3\run_c37_r1w3_20261019\R1_W3_READING.json`, `c38_host` at
   `r1_wave3b\run_c38_r1w3b_20261019\R1_W3B_HOST.json`, and `x5_worlds` at the pinned `X5PAIR_WORLDS.json`. Record
   the test verdict, the status word, the four pair words and the reported rows in the spec sheet with the reading's
   sha256.

**Reading the result.** `HARD_GATES_PASS` + `EYE_PAIRING_EARNED_KEEP`: the word is licensed within `SYNTHETIC_ONLY`;
claim status `ENGINEERED-NOT-VALIDATED` (the world was built so pairing matters). `EYE_PAIRING_HARMED`,
`LEARNING_DID_NOT_EARN_KEEP` or `INCONCLUSIVE`: a finding, recorded and never deleted. `FAILURE` / `INSTRUMENT_ERROR`:
nothing about the brain is read. A stage exit code is never the verdict.
