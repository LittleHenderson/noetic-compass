# Launch brief: HELM-R1 X-REAL v2 (written 2026-10-19, Pacific; v1 c275daed VOID_SUPERSEDED_BY_V2)

**NOT LAUNCHED. No ledger hold placed.** The builder does not launch. Order of events (the owner has pre-approved; see step 1):

1. **Owner approval: already given** (pre-approval, 2026-10-19, verbatim in `OWNER_APPROVALS_20261018.md`: "I PRE-APPROVE
   BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.").
   `APPROVAL_RECORD_XREAL.md` binds that line to this package (`a9b4c954...`, freeze `67b48541...`), cap 1.00 USD, one
   attempt + one plumbing retry. Any reseal is a new package and needs a new owner word.
2. **Ledger hold** (coordinator): the signed cap against `Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json`
   (read after c40: 111.29 of 200.00 used, 88.71 unreserved).
3. **Custody** (a separate custodian session, laptop, 0 USD, no network): exactly
   `HELM_XREAL_20261019/xr_contract/XREAL_CUSTODIAN_CONTRACT.md` — frames rebuilt from the pinned sources, seeds from
   the owner's line + ":" + this zip's full sha256 (A-XR-18; `overlap_check: PASS` first), blind hash-rank sample, keys A and B, the receiver's checker
   (`all_pass: true`, two-key agreement >= 90%), seal, and the host carrier `xr` (INPUTS + PINS only; the key file and
   the sample record never leave the laptop). Hashes only to the coordinator. The builder never sees the exam.
4. **The scored host run** (coordinator, the claude_jobkit precedent of c37-c40):
   - Sources (each an archive pinned by sha256 in `sources_manifest.json`): `xreal` =
     `HELM_XREAL_20261019_SOURCE_XREAL.zip` `a9b4c954...`; `r1w4` = `HELM_R1_W4_20261019_SOURCE_R1W4.zip`
     `4bd0d740a70852c8d59091494ad88c69ac472f3a0f207a33fc44789b8e3df14c`; `r1w3b` = `a4f82556...`; `r1w3` = `152bca2a...`;
     `r1w2` = `21ad185d...`; `w1` = `31f97d67...`; `xr` = a carrier of the custodian's `xr` folder (top folder `xr`);
     `x5spent` = a carrier (top folder `x5spent`) of `ENGLISH64_X5.json` `1eb17c91...` and `FACES64_X5.json` `2c7cac21...`
     from `r1_wave5\x5_custody\exam\`, shipped by path and checked by sha256 only (never opened by the operator or
     the builder). No source corpus goes to AWS.
   - Stage: exactly `HELM_XREAL_20261019/kit/STAGE_XREAL.json` (`xreal_host_run`), with `--expected-freeze-sha256
     67b48541...`; supervisor = the package's `kit/job_supervisor.py` (wave 4's, byte for byte, `3b2337ca...`); required
     outputs `xreal_out/XREAL_HOST.json` and its `.sha256`. Before launch: `python -B kit/plan_check.py <job_plan.json>
     kit/run_xreal.py` must print PASS (it does on the stage file).
   - Host: one `m6i.xlarge`, us-west-2, `ami-0dddfa1ffa6b87af7`, 2-CPU slice, 14 GiB; `XREAL_WORKERS=2`; runner deadline
     2,400 s; no automatic retry (`RUN_LIMITS_XREAL.json`).
   - Expected: about 8-12 minutes of host, about 0.03-0.05 USD at list (0.07-0.10 cautious); at most about 0.35.
   - **Attempts: one scored + at most one plumbing retry** (only if no unit of the scored pool started; same zip, same
     pins).
5. **Cleanup and backup:** terminate host and volumes, release the slot, remove temporary role/profile/bucket,
   independent cleanup check within an hour and a direct read-only look; back up to `D:\tksCAS-archive\` with three
   sha256 confirmations; ledger closeout. Record per job: source, purpose, instance, time and cost limits, cleanup.
6. **The reading (laptop):** `MERGE_INPUT_XREAL.json` (`README_XREAL.md`), then from an extracted copy of the sealed zip
   `python -B -I -X utf8 xr_contract/xrun.py <PKG> xreal.merge_xreal --merge-input MERGE_INPUT_XREAL.json --out
   XREAL_READING.json`, with `c40_full_dir` = `r1_wave5\run_c40_r1w5_20261019\deliverable_unpacked\runs\helm-claude-r1w5-20261019-c40\results\r1_w5_host_run\out\r1w5_out`.
   Record the verdict, the part words, the F kind words, the census and the reading's sha256 in the spec sheet.

**Reading the result.** `INSTRUMENT_ERROR`: nothing about HELM is read. `FAILURE`: a hard gate failed. `PASS`: each part
word decides what may move, only to `NAMED_CORPORA_ONLY` (PREREGISTRATION section 11). Negative words are findings,
recorded and never deleted. A stage exit code is never the verdict.
