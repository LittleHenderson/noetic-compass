# Launch brief: HELM-R1 wave 4 (R1W4), the EYE_SCAN wave (written 2026-10-19, Pacific)

**NOT LAUNCHED. No ledger hold placed.** The builder does not launch. Order of events after the owner signs:

1. **Owner signs** the exact line in `OWNER_SIGN_REQUEST_R1W4.md` (it carries `4bd0d740`). The coordinator writes
   `R1W4_APPROVAL_RECORD.json` (schema `helm.r1w4.approval/1`): `owner_line_verbatim`, `owner_line_sha256` (sha256 of
   its exact UTF-8 bytes, no trailing newline; the custodian's seed source and the reader's I10), `package_zip_sha256`
   `4bd0d740a70852c8d59091494ad88c69ac472f3a0f207a33fc44789b8e3df14c`, `package_freeze_sha256`
   `0d45017c98186d64c701a3a4a7b953fc1d1b87b94a940eb779b3397ae09bf6c7`, `cap_usd`, `attempts`, `superseded_by: null`.
   Any reseal after signing is a new package and needs a new sign line (I9).
2. **Ledger hold** (coordinator): the signed cap against `Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json`
   (read 2026-10-19 after c38: 111.22 of 200.00 used, 88.78 unreserved).
3. **X4** (a separate custodian session; `HELM_R1_W4_20261019/x4_contract/X4_CUSTODIAN_CONTRACT.md` and
   `SEED_RULE_X4.md`), laptop, 0 USD, five commands of `r1w4.custody_x4` (preflight, derive, generate, check, seal).
   The receiver's check must print `all_pass: true` BEFORE the seal. Only `X4_PINS.json` (hashes) reaches the
   builder. Nobody opens an X4 file; no arm runs on X4 before the host.
4. **The scored host run** (coordinator, the claude_jobkit precedent of c35 / c37 / c38):
   - Sources (each an archive pinned by sha256 in `sources_manifest.json`):
     `r1w4` = `HELM_R1_W4_20261019_SOURCE_R1W4.zip` `4bd0d740...`;
     `r1w3b` = `HELM_R1_W3B_20261019_SOURCE_R1W3B.zip` `a4f82556bf0fc26de5635a7c81ec8f5053951d4c64a3906c8e5dd474e3814d26`;
     `r1w3` = `HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip` `152bca2a3c869212642f96514e7d485413727bf92cf67e9aff1774cefa532362`;
     `r1w2` = `HELM_R1_W2_20261018_SOURCE_R1W2.zip` `21ad185d885a11c4ee498e31e106c71ca608dc9edea1b201a283347086d58dc5`;
     `w1` = `HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip` `31f97d67122b45860cdff2b03481655fa502ff359f10b70a181904972ddbb3c9`;
     `x4` = a carrier of the sealed X4 files (top folder `x4`: `ENGLISH64_X4.json`, `FACES64_X4.json`, `SELF_X4.json`,
     `X4_PINS.json`, `X4_SEAL_RECORD.json`); `spent` = a carrier (top folder `spent`) of the seven spent files, byte for
     byte: from `r1_wave3\x2_custody\exam\` `GB_FRESH_W1.json` `21706f4f...`, `TB_FRESH_W1.json` `4049fa49...`,
     `CCE_PLANTED_W1.json` `be0828ab...`, `CASCADE_X2.json` `d39f5b25...`, `IDLE_X2.json` `f883f8b0...`; from
     `r1_wave3b\x3_custody\exam\` `ENGLISH64_X3.json` `a5a4286a...`, `FACES64_X3.json` `8c1ff66a...`. Shipped by path,
     checked by sha256 only, never opened.
   - Stage: exactly `HELM_R1_W4_20261019/kit/STAGE_R1W4.json` (`r1_w4_host_run`), with `--expected-freeze-sha256
     0d45017c...`; supervisor = the package's `kit/job_supervisor.py` (wave 2's, byte for byte); required outputs
     `r1w4_out/R1_W4_HOST.json` and its `.sha256`. Before launch: `python -B kit/plan_check.py <job_plan.json>
     kit/run_r1w4.py` must print PASS.
   - Host: one `m6i.xlarge`, us-west-2, `ami-0dddfa1ffa6b87af7`, 2-CPU slice, 14 GiB; `R1W4_WORKERS=2`; runner
     deadline 2,400 s; no torch, no GPU, no helper job; no automatic retry (`RUN_LIMITS_R1W4.json`).
   - Expected: about 15-25 minutes of host (80 units; the laptop dry run's 56 units took 137.8 s of unit time, one at a
     time), about 0.05-0.08 USD at list (0.12-0.19 conservative); at most about 0.35-0.40 per attempt.
   - **Attempts: one scored + at most one plumbing retry** (only if no unit of the scored pool started; same zip,
     same X4 pins). **Cap $1.00 PROPOSED** (the owner's sign line sets it).
5. **Cleanup and backup:** terminate host and volumes, release the slot, remove temporary role/profile/bucket,
   independent cleanup check within an hour; back up to `D:\tksCAS-archive\` with three sha256 confirmations; ledger
   closeout. Record source, purpose, instance, time and cost limits, and cleanup (owner order 2026-09-23).
6. **The reading (laptop):** `MERGE_INPUT_R1W4.json` (`README_R1W4.md` section 4), then `python -B -m
   r1w4.merge_r1w4 --merge-input MERGE_INPUT_R1W4.json --out R1_W4_READING.json` from an extracted copy of the
   sealed zip, with `w3b_dir`, `w3_dir`, `w2_dir`, `w1_dir` at the sealed neighbour packages, `c38_reading` /
   `c38_host` at `r1_wave3b\run_c38_r1w3b_20261019\` and `c37_reading` / `c37_host` at
   `r1_wave3\run_c37_r1w3_20261019\`. The dry reader peaked at 139.5 MiB (laptop rule met). Record the verdict, the
   EYE_SCAN word and the pair words in the spec sheet with the reading's sha256.

**Reading the result.** Test verdict PASS / FAILURE (a gate broke, named) / INSTRUMENT_ERROR (the measuring went
wrong). Then ONE EYE_SCAN word: EYE_SCAN_EARNED_KEEP, EYE_SCAN_HARMED, EYE_SCAN_NO_EFFECT or INCONCLUSIVE. A positive
word stays ENGINEERED-NOT-VALIDATED within SYNTHETIC_ONLY. A stage exit code is never the verdict.
