# Launch brief: RTR-1 "RE-TEST READER" (written 2026-10-19, Pacific)

**NOT LAUNCHED. No ledger hold placed.** The builder does not launch. Order of events:

1. **Owner approval: given** — owner order "RE-TEST READER" (0.03 USD), coordinator mapping cap 0.10 USD, one attempt +
   one plumbing retry. `APPROVAL_RECORD_RTR.md` / `.json` bind it to zip `e201feb6…` (freeze `6a622106…`).
2. **Ledger hold** (coordinator): 0.10 USD against `Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json`
   (read 2026-10-19 after c42: 111.33 of 200.00 used, 88.67 unreserved).
3. **Custody** (a separate custodian session, laptop, 0 USD, no network): exactly `CUSTODIAN_PROCEDURE_RTR.md`.
   Needs the CTT primary exam sealed (`ctt_custody\exam\E_MACHINE_S_CTT.json` + its seal record); if it is not, STOP.
   Hashes only to the coordinator. The builder never sees the draw.
4. **The host run** (coordinator, the claude_jobkit precedent of c41/c42):
   - Sources (each an archive pinned by sha256): `rtr` = `HELM_RTR1_20261019_SOURCE_RTR1.zip` `e201feb6e5fd4eaf1d9b9060ed100a9db6150257c2d0b64d230ad81c4042f7a8`;
     `xreal` = `HELM_XREAL_20261019_SOURCE_XREAL.zip` `a9b4c954…`; `r1w4` = `4bd0d740…`; `r1w3b` = `a4f82556…`;
     `r1w3` = `152bca2a…` (v3); `w1` = `31f97d67…` (v3); `rt` = a carrier of the custodian's `carrier\rt` folder (top
     folder `rt`: INPUTS_RTR.json + RTR_PINS.json only); `xrspent` = a carrier (top folder `xrspent`) of X-REAL's spent
     `INPUTS_XREAL.json` `37312a31…`, shipped by path and checked by sha256 only (never opened). No corpus goes to AWS.
     (Wave 2 is NOT needed.)
   - Stage: exactly `HELM_RTR1_20261019/kit/STAGE_RTR.json` (`rtr_host_run`) with `--expected-freeze-sha256
     6a622106aa1a57c23ec5ad03f8f687fd20653772413404cb9eda3b57aa956cf3`; supervisor = the package's
     `kit/job_supervisor.py` (`3b2337ca…`, X-REAL's = wave 4's); required outputs `rtr_out/RTR_HOST.json` and its
     `.sha256`. Before launch: `python -B kit/plan_check.py <job_plan.json> kit/run_rtr.py` must print PASS (it does on
     the stage file).
   - Host: one `t3.medium` (m6i.large if unavailable), us-west-2, `ami-0dddfa1ffa6b87af7`; one worker; runner deadline
     1,200 s; no automatic retry (`RUN_LIMITS_RTR.json`).
   - Expected: about 5-8 minutes of host, about 0.01 USD at list (0.02 cautious); at most about 0.04 per attempt.
   - **Attempts: one scored + at most one plumbing retry** (only if no unit of the pool started; same zip, same carriers).
5. **Cleanup and backup:** terminate host and volumes, release the slot, remove temporary role/profile/bucket,
   independent cleanup check within an hour and a direct read-only look; back up to `D:\tksCAS-archive\` with three
   sha256 confirmations; ledger closeout. Record: source, purpose, instance, time and cost limits, cleanup.
6. **The reading (laptop):** `MERGE_INPUT_RTR.json` (`README_RTR.md`), then from a fresh extract of the sealed zip
   `python -B -I -X utf8 rtr_contract/xrun.py <PKG> rtr.merge_rtr --merge-input MERGE_INPUT_RTR.json --out RTR_READING.json`,
   with `c42_xr_s_full` = c42's `XR_S_FULL.json` (`6a53606d…`). Record the verdict, the three words, the tallies and
   the reading's sha256 in the spec sheet.

**Reading the result.** `INSTRUMENT_ERROR`: nothing about the reader is read. `FAILURE`: a hard gate failed. `PASS`:
V11's word decides what may move (PREREGISTRATION section 8), only to `NAMED_CORPORA_ONLY`, and never anything about
English typed to HELM by people. Negative words are findings, recorded and never deleted.
