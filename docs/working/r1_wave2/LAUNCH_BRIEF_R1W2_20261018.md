# Launch brief: HELM-R1 wave 2 (R1W2), one part switched off at a time (written 2026-10-18, Pacific)

**NOT LAUNCHED. No ledger hold placed.** The builder does not launch. Order of events after the owner signs:

1. **Owner signs** the exact line in `OWNER_SIGN_REQUEST_R1W2.md` (it carries this package's `21ad185d`). The coordinator
   writes `OWNER_APPROVAL_R1W2_<utc>.json` (schema `helm.r1w2.approval/1`): the owner's line verbatim and the sha256 of
   its exact bytes, `package_zip_sha256` `21ad185d885a11c4ee498e31e106c71ca608dc9edea1b201a283347086d58dc5`, `package_freeze_sha256` `c8f82a6d652ae6f910021e9d1c19ad7e67bcf29bdacc0613b8eb469d84b29224`, cap, attempts,
   `superseded_by: null`. The reader's row I9 checks every field. **Any reseal after signing is a new package and needs
   a new sign line** (the wave-1 gap "approval bound v1, v3 ran" cannot recur: I9 fails on it).
2. **Ledger hold** (coordinator): the signed cap, against `Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json`
   (read 2026-10-18: 110.35 of 200.00 used, 89.65 free).
3. **X1** (a separate custodian session, `HELM_R1_W2_20261018/x1_contract/X1_CUSTODIAN_CONTRACT.md`): seeds from the
   sha256 of the owner's sign-line bytes; one AWS `m6i.xlarge` job, cap 0.50 USD inside the wave cap; the receiver's
   check (`r1w2/check_x1_format.py`) must print `all_pass: true` BEFORE the seal; hands over `X1_PINS.json` (hashes
   only). The coordinator re-hashes every X1 file against the pins; nobody converts a file.
4. **The scored host run** (coordinator, the claude_jobkit precedent of c21 / c34-g):
   - Sources (each an archive pinned by sha256 in the controller's `sources_manifest.json`):
     `r1w2` = `HELM_R1_W2_20261018_SOURCE_R1W2.zip` `21ad185d885a11c4ee498e31e106c71ca608dc9edea1b201a283347086d58dc5`;
     `w1` = `HELM_R1_W1_20261015_V3_SOURCE_R1W1.zip` `31f97d67122b45860cdff2b03481655fa502ff359f10b70a181904972ddbb3c9`
     (the archive c34-g shipped, unchanged);
     `gb3zip` = the GB3 carrier `claude_jobkit\rb1g2kit\GB3_ZIP_CARRIER_V1.zip` `efc041578d36d5592cb38d1b215a6f2d7a71005dbebf802b233913ab64263f59`
     (holds `ff4de172...`);
     `x0` = `claude_jobkit\r1w1kit\R1W1_FRESH_CARRIER_V1.zip` `3e3d86672274fa157317b08525cb504faa40b12447a4b1411aa62f0363d93e2c`
     (X0's GB/TB files, exposure control only);
     `x1` = a carrier of the X1 folder (built after step 3, pinned by its own sha256).
   - Stage: exactly `HELM_R1_W2_20261018/kit/STAGE_R1W2.json` (one `command` stage `r1_w2_host_run`), with
     `--expected-freeze-sha256 c8f82a6d652ae6f910021e9d1c19ad7e67bcf29bdacc0613b8eb469d84b29224`; supervisor = the package's `kit/job_supervisor.py` (the c34-g
     supervisor plus the required-outputs fix); `required_outputs` = `r1w2_out/R1_W2_HOST.json`,
     `r1w2_out/R1_W2_HOST.json.sha256`. Before launch run `python -B kit/plan_check.py <job_plan.json> kit/run_r1w2.py`
     on the built plan: it must print PASS.
   - Host: one `m6i.xlarge`, us-west-2, the c21 image `ami-0dddfa1ffa6b87af7` (Python 3.12.3, torch 2.9.1), 2-CPU
     slice, 14 GiB; `R1W2_WORKERS=2`; command deadline 5,400 s; host window 120 minutes (work cut-off 111); no
     automatic retry. `RUN_LIMITS_R1W2.json`.
   - Expected: about 15-25 minutes of command, 30-45 minutes of host, about 0.25-0.35 USD (conservative rate); at most
     0.92 USD at the window.
   - **Attempts: one scored + at most one plumbing retry.** The retry is allowed only if no unit of the scored pool
     started (refused before package code ran, or the host never reached test 02); same zip, same X1 pins. Anything
     else is a finding of the one attempt.
5. **The depth families (laptop, $0):** from an extracted copy of the sealed zip,
   `python -B -m r1w2.d34_x1 drive --x1-dir <X1 folder> --runs <r1_wave2>\d34_x1\runs --freeze-sha256 c8f82a6d652ae6f910021e9d1c19ad7e67bcf29bdacc0613b8eb469d84b29224`
   then `... merge --runs <same>`. 20 parts, each at most 300 s and 300 MiB, start only with at least 300 MB free RAM,
   one at a time. If the laptop cannot host them: report the blocker; do not fall back; the reading waits.
6. **Cleanup and backup:** terminate the host and volumes, release the slot, remove the temporary role/profile/bucket,
   independent cleanup check within an hour; back up the deliverable to `D:\tksCAS-archive\` with three sha256
   confirmations; ledger closeout with the charge.
7. **The reading (laptop):** `MERGE_INPUT_R1W2.json` (README_R1W2.md section 5), then
   `python -B -m r1w2.merge_r1w2 --merge-input MERGE_INPUT_R1W2.json --out R1_W2_READING.json` from an extracted copy
   of the sealed zip. Record the verdict and the eight words in the spec sheet with the reading's sha256.

**Reading the result.** `PASS`: every instrument row and hard gate held; each switch word stands. `FAILURE`: a part
broke a rule (named); no word licensed. `INSTRUMENT_ERROR`: the measuring went wrong; nothing about the brain is read.
A stage exit code is never the verdict.

**Deliverables to retrieve:** the whole `r1w2_out/` folder, `RUN_RECORD.json`, `unittest.log`, `unittest_w1.log`,
the supervisor receipt and progress, the job record; laptop: the depth `runs/` folder and `D34_READING.json`.
