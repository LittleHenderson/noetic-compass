# Launch brief: HELM-R1 wave 3b (R1W3B), the roomier exam (written 2026-10-19, Pacific)

**NOT LAUNCHED. No ledger hold placed.** The builder does not launch. Order of events after the owner signs:

1. **Owner signs** the exact line in `OWNER_SIGN_REQUEST_R1W3B.md` (it carries `a4f82556`). The coordinator writes
   `OWNER_APPROVAL_R1W3B_<utc>.json` (schema `helm.r1w3b.approval/1`): `owner_line_verbatim`, `owner_line_sha256`
   (sha256 of its exact UTF-8 bytes; the reader's I10 compares it with the X3 seed source), `package_zip_sha256`
   `a4f82556bf0fc26de5635a7c81ec8f5053951d4c64a3906c8e5dd474e3814d26`, `package_freeze_sha256`
   `a6d9dbc78d3f720941c5a358be9a4d514617f8de226811c55938f807833dfbba`, cap, attempts, `superseded_by: null`. Any reseal
   after signing is a new package and needs a new sign line (I9).
2. **Ledger hold** (coordinator): the signed cap against `Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json`
   (read 2026-10-19 after c37: 88.81 of 200.00 unreserved).
3. **X3** (a separate custodian session, `HELM_R1_W3B_20261019/x3_contract/X3_CUSTODIAN_CONTRACT.md` and
   `SEED_RULE_X3.md`), laptop, 0 USD: `r1w3b.seed_rule_x3` on the owner's line with the six pinned derivations (must
   print `overlap_check: PASS`); `r1w3b.gen64` for E64 and F64; the receiver's check `r1w3b.check_x3_format` with the
   three pinned extra text files must print `all_pass: true` BEFORE the seal; `X3_PINS.json` (hashes only) to the
   coordinator.
4. **The scored host run** (coordinator, the claude_jobkit precedent of c35 / c37):
   - Sources (each an archive pinned by sha256 in `sources_manifest.json`):
     `r1w3b` = `HELM_R1_W3B_20261019_SOURCE_R1W3B.zip` `a4f82556...`;
     `r1w3` = `HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip` `152bca2a3c869212642f96514e7d485413727bf92cf67e9aff1774cefa532362`;
     `r1w2` = `HELM_R1_W2_20261018_SOURCE_R1W2.zip` `21ad185d885a11c4ee498e31e106c71ca608dc9edea1b201a283347086d58dc5`;
     `w1` = `HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip` `31f97d67122b45860cdff2b03481655fa502ff359f10b70a181904972ddbb3c9`;
     `x3` = a carrier of the X3 folder (top folder `x3`); `x2lang` = a carrier (top folder `x2lang`) of
     `ENGLISH16_X2.json` `205054b2...` and `FACES16_X2.json` `69202c0b...` from `r1_wave3\x2_custody\exam\`, shipped
     by path and checked by sha256 only (never opened by the operator or the builder).
   - Stage: exactly `HELM_R1_W3B_20261019/kit/STAGE_R1W3B.json` (`r1_w3b_host_run`), with `--expected-freeze-sha256
     a6d9dbc7...`; supervisor = the package's `kit/job_supervisor.py` (wave 2's, byte for byte); required outputs
     `r1w3b_out/R1_W3B_HOST.json` and its `.sha256`. Before launch: `python -B kit/plan_check.py <job_plan.json>
     kit/run_r1w3b.py` must print PASS.
   - Host: one `m6i.xlarge`, us-west-2, `ami-0dddfa1ffa6b87af7`, 2-CPU slice, 14 GiB; `R1W3B_WORKERS=2`; runner
     deadline 2,400 s; no automatic retry (`RUN_LIMITS_R1W3B.json`).
   - Expected: about 6-8 minutes of host, about 0.02-0.03 USD at list (0.05-0.06 conservative); at most about 0.35.
   - **Attempts: one scored + at most one plumbing retry** (only if no unit of the scored pool started; same zip,
     same X3 pins).
5. **Cleanup and backup:** terminate host and volumes, release the slot, remove temporary role/profile/bucket,
   independent cleanup check within an hour; back up to `D:\tksCAS-archive\` with three sha256 confirmations; ledger
   closeout.
6. **The reading (laptop):** `MERGE_INPUT_R1W3B.json` (`README_R1W3B.md` section 4), then `python -B -m
   r1w3b.merge_r1w3b --merge-input MERGE_INPUT_R1W3B.json --out R1_W3B_READING.json` from an extracted copy of the
   sealed zip, with `w3_dir`, `w2_dir`, `w1_dir` pointing at the sealed neighbour packages and `c37_reading` /
   `c37_host` at `r1_wave3\run_c37_r1w3_20261019\`. Record the verdict and the four pair words in the spec sheet with
   the reading's sha256.

**Reading the result.** PASS: every instrument row and hard gate held; each pair word stands. FAILURE: a gate broke
(named); no word licensed. INSTRUMENT_ERROR: the measuring went wrong; nothing about the brain is read. A stage exit
code is never the verdict.
