# Launch brief: HELM-R1 wave 3 (R1W3) (written 2026-10-19, Pacific)

**NOT LAUNCHED. No ledger hold placed.** The builder does not launch. Order of events after the owner signs:

1. **Owner signs** the exact line in `OWNER_SIGN_REQUEST_R1W3.md` (it carries `26b0ef7e`). The coordinator writes
   `OWNER_APPROVAL_R1W3_<utc>.json` (schema `helm.r1w3.approval/1`): `owner_line_verbatim`, `owner_line_sha256` (sha256
   of its exact UTF-8 bytes; the reader's I10 compares it with the X2 seed source), `package_zip_sha256`
   `26b0ef7ed25c8431334d98ddf3a566704b105e53feab15103494cea9893f7bf3`, `package_freeze_sha256`
   `a72063f5223b04f01a428dfa55bfeb3fb9f45bec847286c41a5160f5761da1f3`, cap, attempts, `superseded_by: null`. Any reseal
   after signing is a new package and needs a new sign line (I9).
2. **Ledger hold** (coordinator): the signed cap against `Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json`
   (read 2026-10-19: 111.11 of 200.00 used, 88.89 unreserved).
3. **X2** (a separate custodian session, `HELM_R1_W3_20261019/x2_contract/X2_CUSTODIAN_CONTRACT.md` and
   `SEED_RULE_X2.md`): `r1w3/seed_rule_x2.py` on the owner's line (must print `overlap_check: PASS`); the five carried
   parts by X1's generator path with X2's numbers (Gate B worlds by GB3's torch `world()` in one blind AWS helper job,
   cap 0.50 USD inside the wave cap, the c35a pattern); the four new parts by the sealed generators; the receiver's
   check `python -B -m r1w3.check_x2_format <X2> --w1-dir <w1> --extra-text-file <X1 ENGLISH16_X1.json>` prints
   `all_pass: true` BEFORE the seal; `X2_PINS.json` (hashes only) to the coordinator.
4. **The scored host run** (coordinator, the claude_jobkit precedent of c35):
   - Sources (each an archive pinned by sha256 in `sources_manifest.json`):
     `r1w3` = `HELM_R1_W3_20261019_SOURCE_R1W3_v2.zip` `26b0ef7e...`;
     `r1w2` = `HELM_R1_W2_20261018_SOURCE_R1W2.zip` `21ad185d885a11c4ee498e31e106c71ca608dc9edea1b201a283347086d58dc5`;
     `w1` = `HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip` `31f97d67122b45860cdff2b03481655fa502ff359f10b70a181904972ddbb3c9`;
     `gb3zip` = `claude_jobkit\rb1g2kit\GB3_ZIP_CARRIER_V1.zip` `efc041578d36d5592cb38d1b215a6f2d7a71005dbebf802b233913ab64263f59`;
     `x2` = a carrier of the X2 folder (top folder `x2`), pinned by its own sha256.
   - Stage: exactly `HELM_R1_W3_20261019/kit/STAGE_R1W3.json` (`r1_w3_host_run`), with `--expected-freeze-sha256
     a72063f5...`; supervisor = the package's `kit/job_supervisor.py` (wave 2's, byte for byte); required outputs
     `r1w3_out/R1_W3_HOST.json` and its `.sha256`. Before launch: `python -B kit/plan_check.py <job_plan.json>
     kit/run_r1w3.py` must print PASS.
   - Host: one `m6i.xlarge`, us-west-2, `ami-0dddfa1ffa6b87af7`, 2-CPU slice, 14 GiB; `R1W3_WORKERS=2`; deadline 5,400 s;
     window 120 minutes (work cut-off 111); no automatic retry (`RUN_LIMITS_R1W3.json`).
   - Expected: about 15-25 minutes of host, about 0.06-0.07 USD (c35's rate) or 0.12-0.19 (conservative); at most 0.92.
   - **Attempts: one scored + at most one plumbing retry** (only if no unit of the scored pool started; same zip, same
     X2 pins).
5. **Depth (laptop, $0):** from an extracted copy of the sealed zip: `python -B -m r1w3.d34_x2 drive --w2-dir <wave-2
   package> --x2-dir <X2> --runs <r1_wave3>\d34_x2\runs --freeze-sha256 a72063f5...` then `... merge --w2-dir <...> --runs
   <same>`. 20 parts, each <= 300 s and <= 300 MiB, start only with >= 300 MB free RAM. If the laptop cannot host
   them: report the blocker; no fallback; the reading waits.
6. **Cleanup and backup:** terminate host and volumes, release the slot, remove temporary role/profile/bucket,
   independent cleanup check within an hour; back up to `D:\tksCAS-archive\` with three sha256 confirmations; ledger
   closeout.
7. **The reading (laptop):** `MERGE_INPUT_R1W3.json` (README_R1W3.md section 4), then `python -B -m r1w3.merge_r1w3
   --merge-input MERGE_INPUT_R1W3.json --out R1_W3_READING.json` from an extracted copy of the sealed zip. Record the
   verdict, the 13 words, the DECOUPLING word and the pair words in the spec sheet with the reading's sha256.

**Reading the result.** PASS: every instrument row and hard gate held; each word stands. FAILURE: a gate broke (named);
no word licensed. INSTRUMENT_ERROR: the measuring went wrong; nothing about the brain is read. A stage exit code is
never the verdict.
