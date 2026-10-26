# Run sheet: Option B development test, pre-check jobs and GPU job b1

**Status: DRAFT. Nothing in this sheet has been run. No AWS call was made to write it. No money was spent.**

This sheet is the operator's step list. The operator is Claude Code. The owner decides; the operator only runs programs.

Label for both controllers: built by Claude, to be checked by a separate reviewer in one review round, never run before in this form.

This version holds the changes of review round 1. They are: more than one pre-check job is possible (Part A, step A9); the laptop must stay awake and must have free memory (Part B, step B10); the status word comes from the owner's table (step B17).

It also holds three amendments of 2026-10-05 (plan section 27):

- **Amendment A10.** A development test on made-up data is ordered before seal step 1. It is the new Part 0. It is the first job of this sheet.
- **Amendment A8.** Seal step 7 reads the receipt of the pre-check job (step A10 of Part A).
- **Amendment A5.** Each repair line has a window (step A9 and step B8). After seal step 7 no line is added to the seal file.

It also holds three small texts that came with amendment A13 (plan sections 27.3 and 27.4). No step of a job changed.

- Rules 8 and 9 below are new: the exit codes of the laptop tools, and when the final question writer may first run.
- Step 0.1 now names the command of the builder of the made-up package and the folder it writes to.
- The made-up package also holds the canonical sayings lines, because the role notes now print them (amendment A13).

Two kinds of name look alike in this sheet. "Amendment A5", "amendment A8" and "amendment A10" are operator decisions. "Step A5", "step A8" and "step A10" are steps of Part A. They are different things. This sheet always writes the word "amendment" or the word "step".

The order of the parts is the order of work: Part 0, then Part A, then Part B.

## Words used for every number

| Word | Meaning |
|---|---|
| REAL | Read or measured from a file on 2026-10-05. The file is named. |
| PROPOSED | A rule of this sheet or of the plan. Not a measurement. |
| EXPECTED | An estimate. Nobody has measured it. |
| NOT MEASURED | Nobody knows yet. |

## The jobs

| | Development test (Part 0) | Pre-check job (Part A) | GPU job b1 (Part B) |
|---|---|---|---|
| Job id | `cas-optionb-b1-devtest-d<N>`, N is 1 or 2 | `cas-optionb-b1-precheck-p<N>`, N from 1 to 4 | `cas-optionb-b1` |
| When | before seal step 1 | after seal step 6 (a rehearsal: after step 5) | after seal step 7 |
| Data | made-up only | the sealed package | the sealed package |
| Machine | one `m6i.xlarge`, CPU only | one `m6i.xlarge`, CPU only | one `g5.2xlarge`, one A10G GPU |
| Image | `ami-0dddfa1ffa6b87af7` | `ami-0dddfa1ffa6b87af7` | `ami-0dddfa1ffa6b87af7` |
| What runs | `runner_b1.py selftest --mode precheck`, once | `runner_b1.py selftest --mode precheck`, once | self-test, practice, gates, final calls, scoring |
| Model B weights on the host | no (six small tokenizer and config files only) | no (six small tokenizer and config files only) | yes (all seven pinned files) |
| Money cap | 0.50 USD for each job | 0.50 USD for each job | 5.00 USD |
| Hard time limit | 45 minutes for each job | 45 minutes for each job | 180 minutes |
| Attempts | 1 for each job id. At most 2 jobs in all (amendment A10). | 1 for each job id. At most 4 jobs in all (PROPOSED, plan section 19.1). | 1 |
| Controller folder | `C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_cas_optionb_devtest_d<N>/` | the same parent folder, `controller_cas_optionb_precheck_p<N>/` | `D:/tksCAS-runs/controller_cas_optionb_b1/` |
| Derived from | `controller_cas_probe_c02` (ran on 2026-10-04) | `controller_cas_probe_c02` (ran on 2026-10-04) | `D:/tksCAS-runs/controller_cas_small_op11_claude_c1/` (ran on 2026-10-04) |

The plan proposes 0.50 USD and 45 minutes for each pre-check job, and at most 4 such jobs. So all pre-check money stays at or under 2.00 USD (plan section 19.1). These numbers are PROPOSED. The operator confirms them before each launch.

The development test has the same cap and the same time limit. At most 2 such jobs, so all development-test money stays at or under 1.00 USD. Amendment A10 orders these numbers. They do not count toward the 4 pre-check jobs.

Every job uses the same storage slot. The slot is four fixed keys under one prefix in one bucket:

- bucket `helm-primary-pointer-807562639912-20261001-v4`
- prefix `bridge-control-20260822/helm-pointer-saturation-20261001-v4/`
- keys `input.zip`, `progress.json`, `transport-result.json`, `pointer-saturation-deliverable.zip`

Only one job may use the slot at a time. That is why every job posts a notice before and a release after.

## Rules that hold for every step

1. The laptop only edits, launches, watches and downloads. No model, no test and no project program runs on the laptop.
2. One attempt per job id. No retry of a job. No second host. A failed gate is a failure.
3. A new pre-check job under a new job id is not a retry. The plan says when one is allowed. Step A9 repeats that rule. The operator does not pick the case; the returned record does.
4. Never start a job while another job holds the slot. Read the bus first.
5. Never open, print or copy `~/.aws` or `~/.cas_llm_keys.env`. The programs read credentials by themselves.
6. Do not edit a program after its review. A changed byte needs a new review.
7. An outcome code comes only from a program. Repeat it exactly. Do not restate it in softer words.
8. **Exit codes of the laptop tools** (`FILE_FORMATS.md` section 0; PROPOSED). Every `tools/ob_*.py` program ends with one of four codes, and a code means the same thing in every tool:
   - `0`: done. The next step of the run order may start.
   - `1`: not finished. Something is still open. The printed text says what: run the same command again later, or run the step it names first.
   - `2`: not started, or stopped by a check or a refusal. The reason is printed.
   - `3`: done, and the result says: do not launch.

   Only code `0` lets the next step start. The printed status word is the record of what happened. Read it at every step. A run with `--max-calls 0` that leaves calls open ends with code `1`.
9. **The final question writer is not run early.** Do not run `tools/ob_write_questions.py --set final`, not even with `--max-calls 0`, before the practice set is fully done (plan section 11.1, "Practice first" in plan section 10). Its first run writes two files of the final set. From then on `tools/ob_seal.py` refuses a tool repair with `REPAIR_OUTSIDE_ITS_WINDOW`. A real run of the question writer does not give `--batch-size` (`FILE_FORMATS.md` section 4).

---

# Part 0. Development test on made-up data, before seal step 1

**Ordered by amendment A10** (operator decision, 2026-10-05; plan section 19.1). Review round 1 had left this test open. It is now the first job.

**Purpose.** To catch program faults before anything is sealed. The job programs have never run. A fault in a sealed constant, such as a wrong expected self-test code, can not be repaired after seal step 1.

**What it is not.** Its output is never evidence about roles. Its result is never written to a seal file. It is not one of the 4 pre-check jobs. It runs no model B.

**Authority.** The operator's decision of 2026-10-05, under the owner's approval record `CASALESCENCE_NOETICS_v0_1/OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json` (sha256 `d1c052f56b61a6f30a428d25b4530352d6cd6ddb489163734fe6ea6d23b24325`, REAL, hashed again on 2026-10-05). That record allows spending inside unreserved funds, with a stated cap and automatic shutdown on every job. The owner named no dollar figure in it. The cap of this test comes from the operator's decision.

**Limits.** One CPU-only job. At most two. Each: cap 0.50 USD, hard time limit 45 minutes, one attempt, the host shuts itself down. Work must end by minute 35. Forced stop at minute 40.

**The kit.** The same kit as Part A: `precheck_cpu/derive_precheck_job.py`, with `"kind": "DEVELOPMENT_TEST"`. The kit refuses a third development test. It refuses this kind once the real seal file exists.

**Status of every piece.** New. None has run. That holds for the kit, the supervisor and the made-up package. The builder of the package has run on the laptop only up to the step before it calls the two builders of this folder (step 0.1).

## 0.1 What must exist before the build

1. **No real seal file.** `optionb/SEAL_OPTIONB.jsonl` does not exist. REAL on 2026-10-05: it does not exist.
2. **The made-up package.** A folder of its own that holds `source.zip` and `SOURCE_ZIP_BUILD_RECEIPT.json`.
   - It is built by `optionb/dry/build_dev_package.py`. Follow its own usage text. REAL on 2026-10-05: the file is on disk. The command is:

     ```bash
     cd "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1"
     /c/Python314/python.exe -B optionb/dry/build_dev_package.py
     ```

   - It writes to the folder `optionb/dry/dev_package/`. The package is `optionb/dry/dev_package/package/source.zip`, with `SOURCE_ZIP_BUILD_RECEIPT.json` beside it. The folder `optionb/dry/dev_package/` must not exist before the build: a package is never overwritten. A second package, for test `d2`, is built with `--folder-name dev_package_2`.
   - It needs no service and no key. It calls no AWS service. It reads two real canon texts, read-only, and nothing else of the study: Part A of the labeling guide, and the table of the canonical sayings in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` (amendment A13).
   - REAL on 2026-10-05, after amendment A13: its steps 1, 2 and 4 ran clean on the laptop with `--stop-before-the-builders`. Its step 3, the two builders of this folder, has NOT run yet. The first full build is the first run of those two builders on a made-up study folder.
   - It runs the real laptop tools `tools/ob_*.py` on a made-up fixture. It lays the result out as a made-up study folder with its own made-up seal file. Then it runs the two builders of this folder. By hand they are:

     ```bash
     cd "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/optionb/controller_b1_draft"
     /c/Python314/python.exe -B build_source_zip_b1.py --study-root <made-up study folder> --out <new package folder> --guest worker_v02.py
     /c/Python314/python.exe -B build_contract_b1.py --study-root <made-up study folder> --out <new package folder> --stamp-only
     ```

   - The second command needs a **copy** of `worker_v02.py` in the new package folder. It stamps that copy and checks both size limits of the guest. It never touches the reviewed draft. It writes no contract: a contract needs seal step 7 of the real seal file.
   - The package holds made-up passages, made-up tasks, made-up notes and made-up keys. It never holds a real passage or a real question. The only real study text in it is the canon definition lines and, by amendment A13, the canonical sayings lines inside the made-up role notes. It also holds the job programs, the plan, the constants and the file formats as they stand that day (`FILE_FORMATS.md` section 20).
   - Build the package last. A file that changes after the build is not covered by the test.
3. **Check the build receipt** `SOURCE_ZIP_BUILD_RECEIPT.json` by eye:
   - `"made_up_study_root_never_for_a_seal_or_the_gpu_job": true`
   - `"last_seal_step_in_package": "6_PROGRAMS"`
   - `"members": 18`. That is the 16 package files of `FILE_FORMATS.md` section 14, the requirements file and `BUNDLE_MANIFEST.json`.
4. **The owner's approval record** is on disk with the sha256 above. The kit checks it.
5. **The cleanup record of the last job on the storage slot**, with status `VERIFIED`. Part D names it.

Note from the plan (`FILE_FORMATS.md` section 20; the kit does not check it): the made-up practice set needs at least 20 role-step tasks and at least 1 plain-fact task, or the self-test can not reach its expected codes.

## 0.2 Read the slot and the ledger again

1. Read the last lines of `D:/tksCAS-agent-bus/claude_to_codex.jsonl`. The last slot line must be a `SLOT RELEASED` line. REAL on 2026-10-05: the last line is `claude-0048`, `SLOT RELEASED` for `helm-claude-r8-matched-20261005-c05`, written at 2026-10-05T09:49:42Z.
2. Read `C:/Users/wakil/Documents/Codex/AWS_COMBINED_ALLOCATION_CURRENT.json`. Do not use an earlier reading.
   - REAL on 2026-10-05, read again for this part: `combined_allocation_usd` 87.36, `ceiling_usd` 100.0, `unreserved_usd` 12.64, `last_jobs` `["helm-claude-r8-matched-20261005-c05"]`, written at 2026-10-05T09:49:41Z. The file's sha256 was `37baa4707799bba88e48d07bd4bbe22ef84bf2bb994dd55640b589e5c224189f`.
   - The job needs 0.50 USD unreserved. If less is unreserved: no launch; report to the owner.
3. Copy `precheck_cpu/PRECHECK_CONFIG.template.json` to `precheck_cpu/PRECHECK_CONFIG.json`. Fill it:
   - `"attempt": 1` (for the second test: `2`)
   - `"kind": "DEVELOPMENT_TEST"`
   - `"source_zip"` and `"source_zip_sha256"`: the made-up package of step 0.1
   - the block `"previous"` and the number `"existing_allocation_usd"`: check them against what you just read. For test `d1` the template already names `helm-claude-r8-matched-20261005-c05`. For test `d2` the block names test `d1`.

## 0.3 Build the job folder

Both commands run on the laptop. They read and write a few MB. They call no AWS service and run no project code.

```bash
cd "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/optionb/controller_b1_draft/precheck_cpu"
/c/Python314/python.exe -B derive_precheck_job.py --check-text-only
/c/Python314/python.exe -B derive_precheck_job.py PRECHECK_CONFIG.json
```

- The first command writes nothing. It must print `TEXT_CHECK_PASS` and six job names: four pre-check jobs and two development tests.
- The second command creates `helm_operator_preparation/controller_cas_optionb_devtest_d<N>/`. It stops if that folder, the lease or the claim exists.
- It writes `PRECHECK_ADMISSION_VALUES.json` in the new folder. That file holds a draft of each record of step 0.4. For this kind the draft of `authority_record` is already the text of amendment A10. The file grants no authority.

What the build checks by itself for this kind: no real seal file exists; the attempt is 1 or 2, and test 1 was launched before test 2 is built; the kit's limits equal the plan's block `aws.development_test_job` (2 jobs, 0.50 USD, 45 minutes, not one of the 4); the owner's approval record has its pinned sha256; the previous job's cleanup record has status `VERIFIED` and the pinned hash; the previous job is the last job in the ledger; `PLAN_CONSTANTS.json` in the package equals the laptop copy, byte for byte; `tools/verdict.py` in the package has its pinned hash; the made-up seal copy ends with a program line; the six small model files equal the hashes in `PLAN_CONSTANTS.json`; `model.safetensors` is not in the payload.

If the build stops with `PACKAGE_PLAN_CONSTANTS_DIFFER_FROM_THE_LAPTOP_COPY`: the made-up package was built with other constants. Do not edit the kit. Build the package again with the real constants, or report.

## 0.4 One review round, then the four records

1. A separate reviewer reads the derived folder once. A BLOCKER or MAJOR finding holds the launch.
2. After the review accepts, write these records in this order. Take the values from `PRECHECK_ADMISSION_VALUES.json`, block `drafts_not_authority`.

| # | Record | Where | Fields the launcher reads (REAL, read in the base `aws_control.py`) |
|---|---|---|---|
| 1 | `INDEPENDENT_STATIC_REVIEW.json` | the job folder | `accepted` true; `source_pins_sha256` (the sha256 of `CONTROLLER_SOURCE_PINS.json`) |
| 2 | `CONTROLLER_REVIEW.json` | the job folder | `job`; `payload_sha256`; `approved_source_review` true; `tests_only_owner_approved` true; `source_pins_sha256`; `arm_b_source_freeze_sha256`; `arm_b_archive_sha256`; `archive_sha256`; `source_freeze_sha256`; `independent_review_receipt_sha256` (the sha256 of record 1 as finally written) |
| 3 | `ALLOCATION.json` | the job folder | `job`; `launch_authorized` true; `approved_for_single_launch` true; `tests_only_scope` true; `new_allocation_usd` 0.5; `maximum_all_services_usd` 0.5; `combined_existing_allocation_usd` (the ledger value of step 0.2); `combined_allocation_usd` (that value plus 0.50); `authority_record` (the text of amendment A10, taken from the draft); `owner_transfer_record` (one text that is not empty); `storage_reuse_adopted` true; `read_only_readiness_authorized` true; `source_archives.cas` with `path`, `archive_sha256`, `source_freeze_sha256` |
| 4 | `CAS_OPTIONB_DEVTEST_D<N>_TRANSPORT_LEASE.json` | the parent folder `helm_operator_preparation/` | `status` `EXCLUSIVELY_HELD`; `job`; `bucket`; `prefix`; the same `owner_transfer_record` as record 3; `no_other_launcher` true; `prior_cleanup_sha256`; `payload_sha256`; `arm_b_source_freeze_sha256`; `source_freeze_sha256` |

3. The field name `tests_only_owner_approved` comes from the base kit. Here it means: this spend is inside the owner's approval record named above. Add two plain fields to records 2 and 4 so that they say which approval is meant: `"owner_approval_record": "OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json"` and `"owner_approval_sha256": "d1c052f56b61a6f30a428d25b4530352d6cd6ddb489163734fe6ea6d23b24325"`. The probe's records carried the same two fields.
4. PROPOSED text for `owner_transfer_record`: `owner-direct-chat-claude-code-20261004 (OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json); amendment A10, operator decision of 2026-10-05`.
5. These must **not** exist before the launch: `CAS_OPTIONB_DEVTEST_D<N>_SINGLE_LAUNCH_CLAIM.json` in the parent folder (the launch creates it); `aws-cas-optionb-devtest-d<N>-control.json` and `aws-cas-optionb-devtest-d<N>-launch-intent.json` in the job folder.

## 0.5 Post the bus notice

Write one JSON file and post it with `claude_jobkit/post_bus.py <file>`. It adds one line to `D:/tksCAS-agent-bus/claude_to_codex.jsonl` and prints the new line id.

```json
{"type":"INFO",
 "subject":"SLOT NOTICE: job cas-optionb-b1-devtest-d<N> (Option B development test on made-up data, CPU only, self-test only) holds the shared four-key S3 prefix from now until its independent cleanup record is written; launch within minutes",
 "refs":{"branch":null,"commit":null,"files":["C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_cas_optionb_devtest_d<N>/","C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/CAS_OPTIONB_DEVTEST_D<N>_TRANSPORT_LEASE.json"]},
 "authority":"Operator decision of 2026-10-05 (amendment A10) under OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json. Grants nothing to anyone else.",
 "reply_to":"<id of the last SLOT RELEASED line; on 2026-10-05 that was claude-0048>",
 "body":"One m6i.xlarge CPU host from ami-0dddfa1ffa6b87af7, USD 0.50 all-services cap, 45 minute host limit, single attempt, no retry of this job id. Development test <N> of at most 2, before seal step 1. Made-up data only: made-up passages, tasks, notes and keys. One stage of interest: runner_b1.py selftest --mode precheck, tokenizer only. No model B weights on the host, no model call. The output is a program test. It is never evidence about roles and is never written to a seal file. Payload sha256 <...>. Previous slot user pinned: <previous job> (independent cleanup VERIFIED, <first 8 characters of its sha256>...). The release line will name controller_cas_optionb_devtest_d<N>/aws-cas-optionb-devtest-d<N>-independent-cleanup.json."}
```

## 0.6 Preflight, watchdog, launch

The working folder must be the job folder. Put the test number in place of `<N>`.

1. Read-only preflight (Git Bash). It writes `aws-cas-optionb-devtest-d<N>-preflight.json`. It also checks, on AWS, that the previous job's host has ended, that its disk is gone, and that the prefix is empty.

   ```bash
   cd "C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_cas_optionb_devtest_d<N>" && /c/Python314/python.exe -B aws_control.py preflight > preflight.stdout.log 2> preflight.stderr.log; echo "preflight exit=$?"
   ```

2. Start the watchdog, wait for `WATCHDOG_READY`, then start the launch (PowerShell). The watchdog needs a preflight record less than 300 seconds old. The launch needs a watchdog record less than 30 seconds old.

   ```powershell
   $n='<N>'
   $d="C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation\controller_cas_optionb_devtest_d$n"
   $job="cas-optionb-b1-devtest-d$n"
   $w=Start-Process -FilePath 'C:\Python314\python.exe' -ArgumentList '-B',"$d\aws_control.py",'watch' -WorkingDirectory $d -WindowStyle Hidden -RedirectStandardOutput "$d\watcher.stdout.log" -RedirectStandardError "$d\watcher.stderr.log" -PassThru
   @{pid=$w.Id; started_utc=[DateTime]::UtcNow.ToString('o'); job=$job} | ConvertTo-Json | Set-Content -Path "$d\watcher_process.json" -Encoding utf8
   $ok=$false
   for($i=0;$i -lt 60;$i++){ Start-Sleep -Seconds 1; if((Test-Path "$d\watcher.stdout.log") -and ((Get-Content "$d\watcher.stdout.log" -Raw) -match 'WATCHDOG_READY')){ $ok=$true; break }; if($w.HasExited){break} }
   "watcher pid=$($w.Id) ready=$ok exited=$($w.HasExited)"
   if($ok){
     $l=Start-Process -FilePath 'C:\Python314\python.exe' -ArgumentList '-B',"$d\aws_control.py",'launch' -WorkingDirectory $d -WindowStyle Hidden -RedirectStandardOutput "$d\launch.stdout.log" -RedirectStandardError "$d\launch.stderr.log" -PassThru
     @{pid=$l.Id; started_utc=[DateTime]::UtcNow.ToString('o'); job=$job} | ConvertTo-Json | Set-Content -Path "$d\launch_process.json" -Encoding utf8
     "launch pid=$($l.Id) started $([DateTime]::UtcNow.ToString('o'))"
   } else { Get-Content "$d\watcher.stderr.log" -Tail 30 }
   ```

The launch writes the claim file `CAS_OPTIONB_DEVTEST_D<N>_SINGLE_LAUNCH_CLAIM.json`. **From there this test is used.** It is never launched again.

## 0.7 What to watch

- `launch.stdout.log`: lines that start with `REMOTE_PROGRESS` show the stage names and their status.
- The four stage names, in order: `opt_pytorch_inventory`, `overlay_install`, `import_smoke`, `selftest`.
- EXPECTED time: the first three stages took about 200 seconds in probe c02 (REAL, 2026-10-04). The self-test time is NOT MEASURED. Its allowance is 900 seconds.
- The job ends by itself. Both control processes exit. Then `aws-cas-optionb-devtest-d<N>-cleanup.json` exists.

Do nothing by hand while it runs. Do not start anything a second time. Keep the laptop awake for these 45 minutes; the checklist of step B10 applies here too.

## 0.8 Independent cleanup check: at once, and within 30 minutes

Run it as soon as both control processes have exited and `aws-cas-optionb-devtest-d<N>-cleanup.json` exists (Git Bash). It only reads. It writes `aws-cas-optionb-devtest-d<N>-independent-cleanup.json`.

```bash
cd "C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_cas_optionb_devtest_d<N>" && /c/Python314/python.exe -B independent_cleanup.py > independent_cleanup.stdout.log 2> independent_cleanup.stderr.log; echo "exit=$?"
```

- **Time limit: at the latest 30 minutes after the cleanup file was written** (plan constants, `aws.cleanup_rule`). The check finds the ended host through AWS's own listing. AWS drops an ended host from that listing after about an hour. A late check on 2026-10-04 could not verify for that reason alone.
- Wanted: `"status": "VERIFIED"`, `"cleanup_verified": true`, `"instance_state": "terminated"`, an empty `prefix_versions_remaining`.
- This record is the one the next job's launch gate asks for. See Part D.
- If the status is not `VERIFIED`: stop. Do not launch any further job on the slot. Report it. The gate is not loosened.

## 0.9 Read the result

1. The result archive is `aws-cas-optionb-devtest-d<N>-deliverable.zip` in the job folder.
2. Inside it, read `runs/cas-optionb-b1-devtest-d<N>/results/supervisor_receipt.json`.
3. The receipt must say `"precheck_kind": "DEVELOPMENT_TEST"`. Its five values stand under `values_never_for_a_seal_file`. It has no block `seal_step_7_values`.
4. The self-test's own files are under `runs/cas-optionb-b1-devtest-d<N>/results/selftest/run_b1/`.

| `status` in the receipt | Meaning | What to do |
|---|---|---|
| `PRECHECK_COMPLETE_SELFTEST_PASS` | All five pass conditions hold. The self-test printed `SELFTEST_PASS` on the made-up package. | The development test passed. Seal step 1 may now be written (see the limit below). |
| `PRECHECK_COMPLETE_WITH_FINDINGS` | Evidence came back, but a condition failed. | Report the status, the stop code and the failed checks exactly. Fix the fault. Then the second test. |
| `STOPPED_NO_RETRY`, or no receipt | The supervisor or the host stopped. | Report it. Fix the fault. Then the second test. |

- **A test that did not pass.** Fixing is allowed, because nothing is sealed yet. A fix that changes a controller file of this folder needs a new review of that file (rule 6). Build a new made-up package into a new folder, and build test `d2` on it (steps 0.1 to 0.10). The folder, the archive and the receipt of test `d1` are kept.
- **Every test that was launched counts toward the 2**, whatever the reason it did not pass.
- **If the second test does not pass either:** nothing is sealed. No third test. Report to the owner.
- **Limit of a pass.** The test covers the files as they stood when its package was built. A file that changes after that is not covered by it. Seal step 1 is written only after a development test ended with `SELFTEST_PASS`. No program enforces this. The receipt carries its time, and the reviewer checks it against seal line 1.
- **Never** give the `selftest.json` or the receipt of a development test to seal step 7. The seal tool refuses it (step A10 of Part A).
- A pass here is a software result on made-up data. It says nothing about roles.

## 0.10 Ledger, release, archive

Do all three after every development test, pass or not. Do the ledger first: the next job's build reads `last_jobs` in the ledger pointer.

1. **Ledger.** Read the pointer again now. Write one budget addendum `BUDGET_RECONCILIATION_ADDENDUM_CAS_OPTIONB_DEVTEST_D<N>_<utc>.json` in `helm_operator_preparation/`. Then update the pointer by a delta on the value you just read.
   - Host seconds: from the host's launch time to the `utc` of the controller's cleanup file `aws-cas-optionb-devtest-d<N>-cleanup.json`. The launch time is the one AWS reports. If only the controller's own time is at hand, use `launch_utc` in `aws-cas-optionb-devtest-d<N>-launch-intent.json`; it is a little earlier, so the charge is not lower.
   - Rule (REAL, read in `claude_jobkit/closeout_job.py`): list-price use = `0.192 × hours + 100 × (0.08 / 730) × hours + 0.005 × hours`. Charge = the smaller of the cap and `ceil((1.5 × use + 0.05) × 100) / 100`. Here the cap is 0.50.
   - REAL example: the job of 2026-10-05 ran 897 seconds, use 0.051816 USD, charge 0.13 USD.
   - Fields of the addendum, as in the addendum of that job: `schema` `helm.aws-combined-allocation.reconciliation-addendum/1`, `utc`, `job`, `owner_authority` (`OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json`), `hold_placed_usd` 0.5, `release_rule`, `host_seconds`, `list_price_usage_usd`, `conservative_charge_usd`, `pointer_value_read_at_closeout_usd`, `job_build_time_existing_usd`, `combined_allocation_after_usd`, `update_mode` `DELTA_READ_MODIFY_WRITE`, `ceiling_usd`, `ceiling_changed` false.
   - The new pointer: add the charge to `combined_allocation_usd`; set `unreserved_usd` to the ceiling minus that; add the addendum's path to `reconciliation_records`; set `latest_record_sha256` to the addendum's sha256; set `"last_jobs": ["cas-optionb-b1-devtest-d<N>"]`. First add the old pointer as one line to `AWS_COMBINED_ALLOCATION_HISTORY.jsonl`. The ledger must not already carry this job.
   - `closeout_job.py` itself does not fit this folder unchanged. It expects a `JOB_CONFIG.json` and a hold of 1.00 USD. Write the addendum by the same rule.
   - PROPOSED, if the independent cleanup record is not `VERIFIED`: charge the whole cap, 0.50 USD. It stays on the ledger until the owner orders a release or the bill arrives. Report it.
   - The bill itself lags by about a day. Record it as pending.
2. **Bus.** Post one line with `claude_jobkit/post_bus.py`:

   ```json
   {"type":"DONE",
    "subject":"SLOT RELEASED: development test cas-optionb-b1-devtest-d<N> finished; <status in the receipt, exactly>; cleanup VERIFIED",
    "refs":{"branch":null,"commit":null,"files":["C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_cas_optionb_devtest_d<N>/aws-cas-optionb-devtest-d<N>-independent-cleanup.json","C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_cas_optionb_devtest_d<N>/aws-cas-optionb-devtest-d<N>-deliverable.zip"]},
    "authority":"work report; grants nothing",
    "reply_to":"<id of this job's SLOT NOTICE line>",
    "body":"The slot is free. Independent cleanup record status VERIFIED (sha256 <...>): instance <id> terminated, volume <id> absent, prefix has zero versions. RESULT (program strings; made-up data; a program test, never evidence about roles; never written to a seal file): supervisor status <...>; selftest_status <...>. Host time <seconds> s; conservative charge USD <...>; ledger pointer <before> -> <after> of 100 (delta)."}
   ```

   Post this line only when the independent cleanup record says `VERIFIED`. If it does not, post no release. Report instead.
3. **Archive.** Copy the whole job folder, the lease, the claim and the addendum to `D:/tksCAS-archive/casalescence_optionb_devtest_d<N>_<date>/`. Leave out `*.lock` files. Confirm each file three ways: hash of the source, hash of the copy, and for the archive the hash in `aws-cas-optionb-devtest-d<N>-download.json`. A test that did not pass is archived like one that passed.

---

# Part A. The pre-check job (decision D7)

**Purpose.** The GPU job has one attempt. The pre-check runs the runner's self-test on a cheap CPU machine first. The self-test loads no model. It needs only the tokenizer. It checks the scorer on its known examples, the gate program and the analysis program on five made-up answer sets, the padding plan, and the hash of every prompt. It also runs the three word-matching views of the analysis program; they need `tools/verdict.py` inside the package. A failure here stops the launch and is reported. It does not use the GPU attempt.

**It also prints two hashes.** One is the hash of the list of all prompt hashes. One is the hash of the padding plan. They go into the seal file as step `7_PRECHECK`. Gate 0 of the GPU job must print the same two hashes.

## A0. Three kinds of job the kit can build

The config file names the kind. The build compares it with the seal file. If they disagree, the build stops. So the seal file decides the kind, not the operator.

| `kind` | When | Job id | Counts toward the 4 jobs | Its result |
|---|---|---|---|---|
| `SEALED_PACKAGE` | after seal step `6_PROGRAMS`, or after the last line `6R_PROGRAMS_REPAIRED` | `cas-optionb-b1-precheck-p<N>` | yes | A pass gives the five values of seal step 7. |
| `REHEARSAL` | after seal step 5 and before seal step 6 | `cas-optionb-b1-precheck-p<N>` | yes | Never written to the real seal file. |
| `DEVELOPMENT_TEST` | before seal step 1, on made-up data | `cas-optionb-b1-devtest-d<N>`, N is 1 or 2 | no | Never written to a seal file. Never evidence about roles. |

- **Rehearsal (allowed, not required; plan section 19.1).** The job programs have never run. A rehearsal finds a program fault while seal step 6 is still open. Then the fault is fixed without a repair line. A data stop found in a rehearsal is as final as in a sealed pre-check.
- **Development test on made-up data (plan section 19.1; amendment A10).** It is ordered. It comes before seal step 1. Part 0 has its steps. It has its own limit of 2 jobs.
- All three kinds are new. None has run.

**How many jobs were launched.** Count the files `CAS_OPTIONB_PRECHECK_P<N>_SINGLE_LAUNCH_CLAIM.json` in `helm_operator_preparation/`. A launch leaves one behind. When 4 exist: no further pre-check job; report to the owner.

## A1. What must exist before the build

For kind `SEALED_PACKAGE`:

- Seal step `6_PROGRAMS` is written in `optionb/SEAL_OPTIONB.jsonl`.
- `source.zip` exists. It was built by `build_source_zip_b1.py` into a folder of its own. It is the same file, byte for byte, that will go into the GPU job's `input.zip`. Make the empty folder first; the script does not make it. The script has never been run.

  ```bash
  cd "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/optionb/controller_b1_draft"
  /c/Python314/python.exe -B build_source_zip_b1.py --out <new package folder> --guest worker_v02.py
  ```

- `source.zip` holds the 16 package files of `FILE_FORMATS.md` section 14, among them `tools/verdict.py`, and beside them `contracts/requirements.small-linux.txt` (sha256 `6d9ee033baf3acbcecfbf8feb735a807025c141cac8e6060e480154c2c1c15b7`, REAL, the file the probe installed from) and `BUNDLE_MANIFEST.json`. The build stops if one is missing, or if `tools/verdict.py` does not have the sha256 pinned in `PLAN_CONSTANTS.json`.
- The runner accepts the self-test command exactly as it is written in `precheck_cpu/precheck_supervisor.py`, constant `SELFTEST_ARGV`:
  `selftest --mode precheck --package-dir <folder> --model-dir <folder> --output-dir <folder>`.
  `FILE_FORMATS.md` does not fix the names of the three folder flags. If the runner uses other names, change `SELFTEST_ARGV` before the review. The build stops if a flag in `SELFTEST_ARGV` does not occur in `job/runner_b1.py`.

For kind `REHEARSAL`:

- Seal step 5 is written. Seal step 6 is not.
- Make a scratch copy of the seal file outside `optionb/`. Add one line to the copy: the line that `tools/ob_seal.py step 6 --dry-run` prints. That command writes nothing.
- Build the package from the scratch copy, into a folder of its own:
  `build_source_zip_b1.py --out <new rehearsal folder> --guest worker_v02.py --seal <scratch copy>`.
- The build stops unless the scratch copy is the real seal file plus exactly that one line.

For kind `DEVELOPMENT_TEST`: see Part 0, step 0.1. That job is not a pre-check job of this part.

## A2. Read the slot and the ledger again

1. Read the last lines of `D:/tksCAS-agent-bus/claude_to_codex.jsonl`. The last slot line must be a `SLOT RELEASED` line.
2. Read `C:/Users/wakil/Documents/Codex/AWS_COMBINED_ALLOCATION_CURRENT.json`.
   - REAL at 2026-10-05T09:49Z: `combined_allocation_usd` 87.36, `ceiling_usd` 100.0, `unreserved_usd` 12.64, `last_jobs` `["helm-claude-r8-matched-20261005-c05"]`.
   - Each pre-check job needs 0.50 USD unreserved.
3. Copy `precheck_cpu/PRECHECK_CONFIG.template.json` to `precheck_cpu/PRECHECK_CONFIG.json`. Fill `attempt`, `kind`, `source_zip` and `source_zip_sha256`. Check the block `previous` and the number `existing_allocation_usd` against what you just read.

- `attempt` is the lowest number from 1 to 4 that was never launched. The build stops if a lower number has no claim file, or if this number already has a folder, a lease or a claim.
- The block `previous` names the job that last used the slot. REAL on 2026-10-05: that job is `helm-claude-r8-matched-20261005-c05`. By the time of the first pre-check job the development test of Part 0 has run. So for the first pre-check job the block normally names the last development test. For a second pre-check job it is normally the pre-check job before it. See Part D.

## A3. Build the pre-check folder

Both commands run on the laptop. They read and write a few MB. They call no AWS service and run no project code.

```bash
cd "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/optionb/controller_b1_draft/precheck_cpu"
/c/Python314/python.exe -B derive_precheck_job.py --check-text-only
/c/Python314/python.exe -B derive_precheck_job.py PRECHECK_CONFIG.json
```

- The first command writes nothing. It proves that every text replacement still finds its exact count in the base files, for every job name the kit can give. An earlier form of it printed `TEXT_CHECK_PASS` on 2026-10-05 (REAL). The form of review round 1, and the form after amendment A10, have not been run. REAL for the new names: a separate counting script found the expected counts (1, 18, 4, 1, 1, 10, 6, 1) for the eight job names of review round 1. Amendment A10 took two of them away (`devtest-d3` and `devtest-d4`). The six names that are left are among the eight that were counted.
- The second command creates the folder `controller_cas_optionb_precheck_p<N>`. It stops if the folder exists. It has never been run.
- It writes `PRECHECK_ADMISSION_VALUES.json` in the new folder. That file holds the kind, the attempt number, the payload hash, the pins hash and a draft of each record of step A4. It grants no authority.

What the build checks by itself: the base files equal the reviewed bytes of probe c02; the previous job's cleanup record has status `VERIFIED` and the pinned hash; the previous job is the last job in the ledger; the kit's limits equal the plan's (4 pre-check jobs and 2 development tests, each 0.50 USD and 45 minutes); no tool-repair line stands outside its window in the real seal file (amendment A5); the six small model files equal the hashes in `PLAN_CONSTANTS.json`; `tools/verdict.py` in the package has its pinned hash; the kind in the config is the kind the seal file shows; a `SEALED_PACKAGE` holds the seal up to its last program line; `model.safetensors` is not in the payload; the payload is at most 64 MiB.

## A4. One review round, then the four records

1. A separate reviewer reads the derived folder once. A BLOCKER or MAJOR finding holds the launch.
2. After the review accepts, write these records in this order. Take the values from `PRECHECK_ADMISSION_VALUES.json`.
   1. `INDEPENDENT_STATIC_REVIEW.json` in the folder: `accepted` true, `source_pins_sha256`.
   2. `CONTROLLER_REVIEW.json` in the folder. It carries the sha256 of the file you wrote in step 1.
   3. `ALLOCATION.json` in the folder: `new_allocation_usd` 0.5, `maximum_all_services_usd` 0.5, `tests_only_scope` true, the two ledger numbers, `authority_record`, `owner_transfer_record`.
   4. The lease `CAS_OPTIONB_PRECHECK_P<N>_TRANSPORT_LEASE.json` in the parent folder `helm_operator_preparation/`: `status` `EXCLUSIVELY_HELD`, the same `owner_transfer_record`.
3. Do not create `CAS_OPTIONB_PRECHECK_P<N>_SINGLE_LAUNCH_CLAIM.json`. The launch creates it.

A second, third or fourth pre-check folder differs from the first in its names and hashes only. It still gets its own review record and its own four records.

Authority for this spend: `OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json` (sha256 `d1c052f56b61a6f30a428d25b4530352d6cd6ddb489163734fe6ea6d23b24325`, REAL). It allows spending inside unreserved funds with a stated cap and automatic shutdown. A `DEVELOPMENT_TEST` runs under the same record, by the operator's decision of 2026-10-05 (amendment A10); its records are in Part 0, step 0.4.

## A5. Post the bus notice

Write one JSON file and post it with `claude_jobkit/post_bus.py <file>`. It adds one line to `D:/tksCAS-agent-bus/claude_to_codex.jsonl`.

```json
{"type":"INFO",
 "subject":"SLOT NOTICE: job cas-optionb-b1-precheck-p<N> (Option B pre-check, CPU only, self-test only) holds the shared four-key S3 prefix from now until its independent cleanup record is written; launch within minutes",
 "refs":{"branch":null,"commit":null,"files":["C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_cas_optionb_precheck_p<N>/"]},
 "authority":"OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json. Grants nothing to anyone else.",
 "reply_to":"<id of the last SLOT RELEASED line>",
 "body":"One m6i.xlarge CPU host from ami-0dddfa1ffa6b87af7, USD 0.50 all-services cap, 45 minute host limit, single attempt, no retry of this job id. Pre-check job <N> of at most 4; kind <kind>. No model B weights on the host. One stage of interest: runner_b1.py selftest --mode precheck. Previous slot user pinned: <previous job> (independent cleanup VERIFIED, <first 8 characters of its sha256>...)."}
```

## A6. Preflight, watchdog, launch

The commands are the ones used for probe c02 on 2026-10-04, with the new folder name. The working folder must be the controller folder. Put the attempt number in place of `<N>` in the first line of each block.

1. Read-only preflight (Git Bash). It writes `aws-cas-optionb-precheck-p<N>-preflight.json`.

   ```bash
   cd "C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_cas_optionb_precheck_p<N>" && /c/Python314/python.exe -B aws_control.py preflight > preflight.stdout.log 2> preflight.stderr.log; echo "preflight exit=$?"
   ```

2. Start the watchdog, wait for `WATCHDOG_READY`, then start the launch (PowerShell). The watchdog needs a preflight record less than 300 seconds old. The launch needs a watchdog record less than 30 seconds old.

   ```powershell
   $n='<N>'
   $d="C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation\controller_cas_optionb_precheck_p$n"
   $job="cas-optionb-b1-precheck-p$n"
   $w=Start-Process -FilePath 'C:\Python314\python.exe' -ArgumentList '-B',"$d\aws_control.py",'watch' -WorkingDirectory $d -WindowStyle Hidden -RedirectStandardOutput "$d\watcher.stdout.log" -RedirectStandardError "$d\watcher.stderr.log" -PassThru
   @{pid=$w.Id; started_utc=[DateTime]::UtcNow.ToString('o'); job=$job} | ConvertTo-Json | Set-Content -Path "$d\watcher_process.json" -Encoding utf8
   $ok=$false
   for($i=0;$i -lt 60;$i++){ Start-Sleep -Seconds 1; if((Test-Path "$d\watcher.stdout.log") -and ((Get-Content "$d\watcher.stdout.log" -Raw) -match 'WATCHDOG_READY')){ $ok=$true; break }; if($w.HasExited){break} }
   "watcher pid=$($w.Id) ready=$ok exited=$($w.HasExited)"
   if($ok){
     $l=Start-Process -FilePath 'C:\Python314\python.exe' -ArgumentList '-B',"$d\aws_control.py",'launch' -WorkingDirectory $d -WindowStyle Hidden -RedirectStandardOutput "$d\launch.stdout.log" -RedirectStandardError "$d\launch.stderr.log" -PassThru
     @{pid=$l.Id; started_utc=[DateTime]::UtcNow.ToString('o'); job=$job} | ConvertTo-Json | Set-Content -Path "$d\launch_process.json" -Encoding utf8
     "launch pid=$($l.Id) started $([DateTime]::UtcNow.ToString('o'))"
   } else { Get-Content "$d\watcher.stderr.log" -Tail 30 }
   ```

For a `DEVELOPMENT_TEST` the folder is `controller_cas_optionb_devtest_d<N>`, the job id is `cas-optionb-b1-devtest-d<N>`, and the file names start with `aws-cas-optionb-devtest-d<N>-`. Part 0, step 0.6, has these commands with those names filled in.

## A7. What to watch

- `launch.stdout.log`: lines that start with `REMOTE_PROGRESS` show the stage names and their status.
- The four stage names, in order: `opt_pytorch_inventory`, `overlay_install`, `import_smoke`, `selftest`.
- EXPECTED time: the first three stages took about 200 seconds in probe c02 (REAL, 2026-10-04). The self-test time is NOT MEASURED. Its allowance is 900 seconds.
- The clock, in minutes after launch: work must end by 35, forced stop at 40, hard limit 45.
- The job ends by itself. Both control processes exit. Then `aws-cas-optionb-precheck-p<N>-cleanup.json` exists.

Do nothing by hand while it runs. Do not start anything a second time. Keep the laptop awake for these 45 minutes; the checklist of step B10 applies here too.

## A8. Independent cleanup check, at once

Run it as soon as both control processes have exited (Git Bash). It only reads. It writes `aws-cas-optionb-precheck-p<N>-independent-cleanup.json`.

```bash
cd "C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_cas_optionb_precheck_p<N>" && /c/Python314/python.exe -B independent_cleanup.py > independent_cleanup.stdout.log 2> independent_cleanup.stderr.log; echo "exit=$?"
```

- Wanted: `"status": "VERIFIED"`, `"cleanup_verified": true`, `"instance_state": "terminated"`, an empty `prefix_versions_remaining`.
- This record is the one the next job's launch gate asks for: the next pre-check job, or the GPU job. See step B4.
- If the status is not `VERIFIED`: stop. Do not launch any further job on the slot. Report it. The gate is not loosened.

## A9. Read the result. What may follow a pre-check that did not pass.

1. The result archive is `aws-cas-optionb-precheck-p<N>-deliverable.zip` in the controller folder.
2. Inside it, read `runs/cas-optionb-b1-precheck-p<N>/results/supervisor_receipt.json`.
3. The self-test's own files are under `runs/cas-optionb-b1-precheck-p<N>/results/selftest/run_b1/`: `selftest.json`, `padding_plan.json`, `prompt_hashes.jsonl` and the trial files.

| `status` in the receipt | Meaning | What to do |
|---|---|---|
| `PRECHECK_COMPLETE_SELFTEST_PASS` | All five pass conditions hold. The self-test printed `SELFTEST_PASS` in `precheck` mode. | Go to step A10 (kind `SEALED_PACKAGE` only). |
| `PRECHECK_COMPLETE_WITH_FINDINGS` | Evidence came back, but a condition failed. The stage row `selftest` shows `selftest_status`, for example `GATE_STOP_SELFTEST` or `GATE_STOP_PADDING`. | **Stop. No GPU launch.** Report the stop code and the failed checks exactly. Then find the case below. |
| `STOPPED_NO_RETRY`, or no receipt | The supervisor or the host stopped. | **Stop. No GPU launch.** Report it. Then find the case below. |

**A pre-check that does not pass is a failure of that job.** It is reported first. Its folder, its archive and its receipt are kept. That job id is never launched again. What may follow is fixed by plan section 19.1. It is PROPOSED there. The record decides the case, not the operator.

The receipt holds a block `after_a_failure_facts` with four plain facts: `selftest_started`, `selftest_json_present`, `selftest_status`, `check_package_matches_seal`. If there is no receipt at all, the self-test never started.

| Case (plan section 19.1) | How the record shows it | What may follow |
|---|---|---|
| The self-test never started | No receipt. Or `selftest_started` is false and `selftest_json_present` is false. Examples: the host or the network failed; the install stage failed; the stage row says `NOT_RUN_DEPENDENCIES_UNAVAILABLE`, `NOT_RUN_DEADLINE` or `SPAWN_FAILED`. | The same `source.zip`, with the same sha256, may be pre-checked again under the next job id. No seal line is added. |
| Package fault | `check_package_matches_seal` is false, and every sealed file on the laptop still has its sealed sha256 (`tools/ob_seal.py verify` exits 0). | `source.zip` is built again from the same sealed files, into a new folder, and pre-checked under the next job id. No seal line is added. |
| Data stop | `selftest_status` is `GATE_STOP_PADDING`. Or the fault sits in a file of seal steps 1 to 5: the constants, a prompt part, a key. | **Final. No launch.** No file of steps 1 to 5 is changed. A new attempt needs a new plan version. |
| Program fault | `selftest_started` is true, the self-test did not end with `SELFTEST_PASS`, and the fault sits in one of the five job files of seal step 6. | The repair rule below. At most **2** repairs. Then a new `source.zip` and the next pre-check job. |

- Every job that was launched counts toward the 4. A rehearsal counts too. A development test does not; it has its own limit of 2 (Part 0). When 4 are used: no launch; report to the owner.
- If the facts fit no case, or two cases: stop and report. Do not choose.

**The repair rule for a program fault** (plan section 11.1; `FILE_FORMATS.md` sections 15.2 and 15.3). This sheet only names the steps. `tools/ob_seal.py` enforces them.

**The window (amendment A5).** A line `6R_PROGRAMS_REPAIRED` is allowed only after a failed pre-check job of kind `SEALED_PACKAGE`, and only before seal step 7. So it comes before any call to model B. The kept receipt of the failed job must say `"precheck_kind": "SEALED_PACKAGE"` and a status other than `PRECHECK_COMPLETE_SELFTEST_PASS`. A rehearsal or a development test never opens this window. Outside the window the seal tool refuses with `REPAIR_OUTSIDE_ITS_WINDOW`. A fault in a job program after seal step 7 means: stop, report, a new reviewed plan version. A repair never changes the plan, the constants, a brief, a threshold, a key, a task or a note.

1. Only the five files of seal step 6 may change: `runner_b1.py`, `scorer_v0_1_1.py`, `gate_b1.py`, `analysis_b1.py`, `scorer_examples_v0_1_1.json`. No file of seal steps 1 to 5 changes. No expected category of the 40 known scorer examples changes.
2. The repair may only bring the code in line with the sealed plan. It changes no rule, no number and no wording.
3. The folder `optionb/repairs/6R1/` (then `6R2`) gets: `old/<file name>` for each changed file, `diff.txt`, `failed_precheck/supervisor_receipt.json` (a copy of the failed job's receipt), and `failed_precheck/selftest.json` if one came back.
4. A reviewer who did not write the change reads the diff against the sealed plan and writes `review.json`. It names the file that holds the fault and the evidence. Without the verdict `REPAIR_ALLOWED` nothing goes on.
5. `tools/ob_seal.py repair 6R1` adds one line `6R_PROGRAMS_REPAIRED` (the command is another builder's; REAL, read in its usage text on 2026-10-05). At most 2 such lines can exist.
6. Build a new `source.zip` into a **new** folder. The old `source.zip` is evidence; it is never deleted or overwritten. `build_source_zip_b1.py` refuses to overwrite one.
7. Build the next pre-check job on the new `source.zip` (steps A2 to A9).

In a **rehearsal** a program fault is simply fixed, because seal step 6 is not written yet. No repair line is needed. The rehearsal job still counts as one of the 4.

A fault in the pre-check kit itself (the controller, the worker script, the supervisor) is not a fault of the five job files. Fixing it changes reviewed bytes of the kit. It needs a new review of the kit, as rule 6 says. The package and the seal stay as they are.

**Tool repairs (amendment A5).** A line `TR_TOOLS_REPAIRED` is allowed only after seal step 1 and while no final question exists. So by the time of a pre-check job that window is closed. A fault in a laptop tool `tools/ob_*.py` that shows up now means: stop, report, a new reviewed plan version. The kit, the zip builder and the GPU launcher all refuse a seal file that holds a tool-repair line at or after the line `3C_FINAL_QUESTIONS_AND_KEYS`.

## A10. Seal step 7

Only after `PRECHECK_COMPLETE_SELFTEST_PASS` of a job of kind `SEALED_PACKAGE`.

The receipt holds the block `seal_step_7_values` with five values: `source_zip_sha256`, `selftest_status`, `prompt_list_sha256`, `padding_plan_sha256`, `selftest_json_sha256`.

A seal step is never written twice. A wrong step 7 can not be taken back. So check before you write.

**The seal tool reads the receipt (amendment A8; `FILE_FORMATS.md` section 15.1).** The command is `tools/ob_seal.py step 7 --receipt <supervisor_receipt.json> --selftest-json <selftest.json> --source-zip <source.zip>`. The tool belongs to another builder. It refuses step 7 unless all four hold:

- the receipt says `"precheck_kind": "SEALED_PACKAGE"`;
- the receipt says `"status": "PRECHECK_COMPLETE_SELFTEST_PASS"`;
- the receipt's block `seal_step_7_values` equals the five values the tool works out from the given `selftest.json` and `source.zip`;
- the member `SEAL_OPTIONB.jsonl` of the given `source.zip` is, byte for byte, the real seal file from its first line to its last program line.

So a rehearsal, or a development test on made-up data, can never be sealed as step 7. REAL, read in `precheck_cpu/precheck_supervisor.py`: the receipt of every job carries `precheck_kind` and `status`; only a job of kind `SEALED_PACKAGE` carries `seal_step_7_values`.

1. Take `selftest.json` and `supervisor_receipt.json` out of the archive, unchanged. Keep both.
2. The receipt must say `"precheck_kind": "SEALED_PACKAGE"` and must hold the block `seal_step_7_values`. If not: stop. This job is never sealed.
3. Check that the sha256 of that `selftest.json` equals `selftest_json_sha256` in the receipt. Check that the sha256 of the `source.zip` you built the job from equals `source_zip_sha256` in the receipt.
4. Run the step as a dry run first: the command above with `--dry-run` added. It runs every check, prints the line and writes nothing.
5. Check that the five values in the printed line equal the five values in the receipt. Only then run the same command without `--dry-run`.

- The receipt of a rehearsal or of a development test has no block `seal_step_7_values`. Its five values stand under `values_never_for_a_seal_file`. Never give the files of such a job to seal step 7. The seal tool refuses them. The GPU launcher checks the same thing again: it reads the receipt (step B2, `PRECHECK_RECEIPT.json`) and refuses a seal step 7 that does not come from a passed `SEALED_PACKAGE` job.
- After the line `7_PRECHECK` no line is added to the seal file (amendment A5). The GPU launcher refuses a seal file in which step 7 is not the last line.
- Seal step 7 also seals the owner's signed table of status words, `optionb/OUTCOME_STATUS_TABLE.json` (plan section 21, `FILE_FORMATS.md` section 19). The owner decides every word in it. Without that table there is no seal step 7 and no GPU launch. The GPU launcher checks the table against the seal again.

## A11. Release, ledger, archive

Do all three after every pre-check job, pass or not.

1. **Bus.** Post one line: `"type":"DONE"`, subject `SLOT RELEASED: pre-check cas-optionb-b1-precheck-p<N> finished; <receipt status>; cleanup VERIFIED`. Name the independent cleanup file and its sha256 in the body.
2. **Ledger.** Write one budget addendum and update the pointer by a delta on the value you read at that moment.
   - Rule (REAL, read in `claude_jobkit/closeout_job.py`): list-price use = `0.192 × hours + 100 × (0.08 / 730) × hours + 0.005 × hours`. Charge = the smaller of the cap and `ceil((1.5 × use + 0.05) × 100) / 100`. Here the cap is 0.50.
   - REAL example: probe c02 ran 330.3 seconds, use 0.01908 USD, charge 0.08 USD.
   - The new pointer must carry `"last_jobs": ["cas-optionb-b1-precheck-p<N>"]`. The next launch gate reads that field.
   - `closeout_job.py` itself does not fit this folder unchanged. It expects a `JOB_CONFIG.json` and a hold of 1.00 USD. Write the addendum by the same rule.
3. **Archive.** Copy the whole controller folder to `D:/tksCAS-archive/casalescence_optionb_precheck_p<N>_<date>/`. Confirm each file three ways: hash of the source, hash of the copy, and for the archive the hash in `aws-cas-optionb-precheck-p<N>-download.json`. A failed pre-check is archived like a passed one.

---

# Part B. GPU job b1

**Purpose.** The one GPU attempt of the Option B usefulness test. One outcome code comes back from a program.

**Limits (decision D8).** Cap 5.00 USD. Hard time limit 180 minutes. One attempt. No retry. At most 5,000 model calls. Result archive at most 100,000,000 bytes. The host shuts itself down.

**Clock, minutes after launch.** The clock starts when the launcher writes its single-attempt claim, before the upload.

| Point | Minute | Seconds |
|---|---:|---:|
| Setup must end | 30 | 1,800 |
| All model work stops | 135 | 8,100 |
| Forced shutdown | 175 | 10,500 |
| Hard limit | 180 | 10,800 |

EXPECTED cost: 0.9 to 2.0 USD for a full run; under 1 USD for a stop at a practice gate; 0.3 to 0.5 USD for a stop in setup. EXPECTED worst case by the price formula: about 4.72 USD for a host that runs the full 180 minutes. That figure uses the rates seen on 2026-10-04 (REAL: 1.212 USD per hour for the machine) and a fixed 1.00 USD allowance.

## B1. What must be true before anything else

- A pre-check job of kind `SEALED_PACKAGE` ended with `PRECHECK_COMPLETE_SELFTEST_PASS`. It ran on the `source.zip` that goes into this job, byte for byte.
- Seal step `7_PRECHECK` is written. It holds that pre-check's five values and the owner's signed table of status words.
- The launch floor is met: `optionb/removal_log.json` says `"launch_floor_met": true`.
- The owner has seen the real counts and said yes to this job. See B3.
- The one review round of the controller and the guest is done. No BLOCKER and no MAJOR is open.

## B2. Assemble the controller folder

Folder: `D:/tksCAS-runs/controller_cas_optionb_b1/`. It must be new. The old folder is not touched.

| File | Comes from |
|---|---|
| `controller_common.py`, `aws_control.py`, `watchdog.py` | this draft folder |
| `bounded_s3.py`, `independent_cleanup.py` | this draft folder; byte-identical to the old controller (sha256 `2582940278d720da833e3795d7678b4146046d4bb73deec1c76606f252fdee61` and `4d0b816c14fd65dd8773976a42e0872168da03f73960d810b0a1f286bc5c51e5`, REAL). The launcher refuses any other bytes. |
| `source.zip` | a copy of the `source.zip` the passed pre-check ran on. Check its sha256 against seal step 7. |
| `worker_v02.py` (the guest), `CONTRACT.json`, `input.zip` | the three builders in this draft folder: `build_contract_b1.py`, then `build_input_zip_b1.py` |
| `SOURCE_PINS.json` | written after the review: `{"job": "cas-optionb-b1", "files": [{"path": "...", "sha256": "..."}]}`. It must list at least the five controller programs, `worker_v02.py`, `CONTRACT.json` and `input.zip`. |
| `INDEPENDENT_REVIEW.json` | written after the review: `"job": "cas-optionb-b1"`, `"decision": "ACCEPT_SOURCE_PENDING_EXTERNAL_ADMISSION"`, `"source_pins_sha256"`. |
| `PRECHECK_RECEIPT.json` | `supervisor_receipt.json` of the pre-check job that passed, copied unchanged out of its result archive (step A10) |
| `PRIOR_INDEPENDENT_CLEANUP.json` | step B4 |
| `AUTHORITY_B1.json` | step B8 |

The guest carries four pins of `source.zip`. After a program repair there is a new `source.zip`. Then start again from the reviewed, unstamped draft of the guest and stamp it for the new `source.zip`. `build_contract_b1.py` refuses to restamp a guest that holds the pins of another `source.zip`. The stamped guest must differ from the reviewed draft in those four lines only.

Do not keep `__pycache__` folders. Always start Python with `-B`.

Before the review, the build-time text check must pass on the assembled folder. Its own usage line is `python -B text_check_b1.py --dir <controller folder>`. It reads files only.

The D: drive needs 24 GB free (REAL: the launcher checks this before the claim).

## B3. The owner's yes

The plan says the GPU job waits for one yes from the owner after the real counts are shown.

Write the owner's answer as a record in `CASALESCENCE_NOETICS_v0_1/`, in the same style as the other owner records. The launcher reads five fields:

- `"applies_to_job": "cas-optionb-b1"`
- `"decision": "GO"`
- `"owner_words_verbatim"`: the owner's own words, unchanged
- `"cap_usd": 5.0`
- `"hard_minutes": 180`

No such record: no launch. The operator does not write a yes on the owner's behalf.

## B4. The prior-cleanup record

The launch gate asks for a cleanup record of the job that most recently used the storage slot. The record must have status `VERIFIED` and the form the gate reads. Part D explains the form.

1. Find the last job on the slot: the last `SLOT` lines on the bus, and `last_jobs` in the ledger pointer. They must name the same job.
2. EXPECTED: that job is the last pre-check job, `cas-optionb-b1-precheck-p<N>`. Its record is the file from step A8.
3. Copy that file, unchanged, to `D:/tksCAS-runs/controller_cas_optionb_b1/PRIOR_INDEPENDENT_CLEANUP.json`.
4. If another job used the slot after the pre-check, use that job's record instead. If that job has no `VERIFIED` record in this form: **stop**. The launch is blocked. Report it. The gate is not loosened.

This gate runs before the single-attempt claim. A miss costs nothing.

## B5. Read the ledger again

Read `C:/Users/wakil/Documents/Codex/AWS_COMBINED_ALLOCATION_CURRENT.json` now. Do not use an earlier reading.

- `unreserved_usd` must be 5.00 or more.
- `last_jobs` must name the job of step B4.
- REAL at 2026-10-05T09:49Z: unreserved 12.64 USD. Every development test and every pre-check job changes it. EXPECTED after one development test and one pre-check job: about 12.4 USD. Arithmetic on that reading, if both development tests and all 4 pre-check jobs were charged their full cap: 12.64 − 1.00 − 2.00 = 9.64 USD.

The launcher compares the pointer file's hash with the hash in the authority record. If any job changes the ledger after your reading, the launch stops with `LEDGER_CHANGED_SINCE_THE_READING_READ_IT_AGAIN`. Then read again and fill again.

## B6. The lease

Write `C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/CAS_OPTIONB_B1_TRANSPORT_LEASE.json`:

```json
{"status": "ADMITTED_EXCLUSIVE",
 "job": "cas-optionb-b1",
 "execution_owner": "claude-code/claude-opus-5-5/session-d2ce92aa-19e8-4dac-8de6-1ffa8931b6b0",
 "bucket": "helm-primary-pointer-807562639912-20261001-v4",
 "prefix": "bridge-control-20260822/helm-pointer-saturation-20261001-v4/",
 "unique_local_output_prefix": "D:\\tksCAS-runs\\controller_cas_optionb_b1",
 "duplicate_launch_forbidden": true,
 "no_automatic_second_run": true,
 "utc": "<now>"}
```

`execution_owner` must equal the constant `OPERATOR` in `controller_common.py`. If a different session launches, that constant changes first, and the change is reviewed.

## B7. Readiness (read-only)

```bash
cd "D:/tksCAS-runs/controller_cas_optionb_b1" && /c/Python314/python.exe -B aws_control.py readiness > readiness.stdout.log 2> readiness.stderr.log; echo "readiness exit=$?"
```

- It launches nothing, uploads nothing and writes nothing to AWS. It calls no invoice service.
- It checks: the account identity; the prior-cleanup record; no live host of any job on the slot; the image, the network and the machine type; that the bucket is private, never versioned, with the seven-day expiry; that the prefix is empty; the live prices.
- It writes four local receipts: `READINESS_RECEIPT.json`, `PRIVATE_ROUTE_RECEIPT.json`, `STORAGE_NETWORK_LIVE_PRICES.json`, `FRESH_PRICE_RECEIPT.json`.
- Wanted: exit 0 and `"status": "READ_ONLY_READY"`. `projected_all_in_usd` must be at most 5.00.
- Exit 2 or `FAILED_NO_BYPASS`: stop and report the reason. Do not work around it.

The price receipt is valid for 60 minutes.

## B8. Fill the authority record

1. Print the hashes: `/c/Python314/python.exe -B aws_control.py hashes`. It calls no AWS service and writes nothing.
2. Copy `AUTHORITY_B1.template.json` to `AUTHORITY_B1.json` in the controller folder.
3. Fill every `<<FILL>>`: the owner's yes record, the ledger reading, the lease hash, the five receipt and review hashes, the prior job, `CONTRACT.json`, `input.zip`, and the seal block with the hash of `PRECHECK_RECEIPT.json`.
4. Set `"status": "ADMITTED"`.

The launcher checks every field against the files on disk. A wrong or empty field stops the launch before the claim.

What the launcher reads in the seal file (REAL, read in `controller_common.py`, function `seal_gate`):

- The nine steps stand in their order, each once. Repair lines may stand between them, each inside its window (amendment A5).
- A line `6R_PROGRAMS_REPAIRED` stands after step 6 and before step 7, at most twice. So the pre-check that passed is always later than the last program repair.
- A line `TR_TOOLS_REPAIRED` stands after line 1 and before the line `3C_FINAL_QUESTIONS_AND_KEYS`. One that stands elsewhere stops the launch with `SEAL_TOOL_REPAIR_LINE_OUTSIDE_ITS_WINDOW`.
- The line `7_PRECHECK` is the last line of the seal file. Any line after it stops the launch with `SEAL_MUST_END_WITH_ONE_PRECHECK`.
- Step 7 says `SELFTEST_PASS` and names the `source.zip` of this job.
- `PRECHECK_RECEIPT.json` shows a passed job of kind `SEALED_PACKAGE` with a job id `cas-optionb-b1-precheck-p1` to `-p4`, and its five values equal step 7. A rehearsal or a test on made-up data stops the launch with `SEALED_PRECHECK_IS_NOT_A_PASSED_JOB_ON_THE_SEALED_PACKAGE`.
- The owner's table `optionb/OUTCOME_STATUS_TABLE.json` is listed in step 7 and still has that sha256.
- The sealed plan constants agree with this controller. The launch floor is met.

## B9. Post the bus notice

```json
{"type":"INFO",
 "subject":"SLOT NOTICE: GPU job cas-optionb-b1 (Option B usefulness test, Claude operator) holds the shared four-key S3 prefix from now; latest possible cleanup <launch time + 180 minutes, Pacific>",
 "refs":{"branch":null,"commit":null,"files":["D:/tksCAS-runs/controller_cas_optionb_b1/"]},
 "authority":"OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json, OWNER_DIRECTION_POINTING_AND_OPTION_B_20261005.json and the owner's yes record for this job. Grants nothing to anyone else.",
 "reply_to":"<id of the last pre-check's SLOT RELEASED line>",
 "body":"One g5.2xlarge from ami-0dddfa1ffa6b87af7, USD 5.00 all-services cap, 180 minute hard limit, single attempt, no retry, host shuts itself down. Sealed package: source.zip sha256 <...>, input.zip sha256 <...>. Previous slot user pinned: <prior job> (independent cleanup VERIFIED, <first 8 characters>...)."}
```

## B10. Launch

### Before the launch: the laptop must stay awake, with free memory

Two laptop programs must stay alive and awake for the whole job: the launcher and the watchdog. That is up to 180 minutes, plus the cleanup check. This protects the **result**, not the money. The money is protected by the host's own shutdown at minute 175.

What happens otherwise (REAL, read in the code; never seen in a run of this controller):

- The launcher stops if the watchdog's heartbeat is 180 seconds old or older (`WATCH_HEARTBEAT_LOST`, `aws_control.py`). Its cleanup then ends the host at once. An unfinished upload is thrown away.
- The watchdog ends the host after twelve failed observations in a row (`watchdog.py`). A laptop without network for a few minutes can cause that.
- If the laptop sleeps, both programs stop. When it wakes, the heartbeat is old, and the launcher ends the host.
- If this happens in the final phase, final tasks are spent and no record comes back. The attempt is used.

Checklist. Every line must be true before the watchdog is started.

1. **Owner action: sleep and hibernate are off for the next 3.5 hours.** Closing the lid must not put the laptop to sleep. The laptop is on mains power. These are system settings. The operator does not change them. The operator asks the owner and waits for the answer.
2. **Free memory.** Close the heavy programs: the ChatGPT desktop app, Chrome, other editors. REAL on 2026-10-05: 598,933,504 bytes of 16,866,705,408 were free (measured with a separate small script; memory load 96 percent). The launcher refuses to start with less than 2,000,000,000 bytes free (PROPOSED number). It stops with `LOCAL_MEMORY_RESERVE` before the claim. That miss costs nothing. It writes the reading to `LOCAL_MEMORY_GATE.json` when the gate passes.
3. **No other agent work on this laptop during the window.** No build, no test, no second session that uses memory. The project notes record a shell that died from lack of memory on 2026-09-23.
4. **Network.** A steady connection. No planned router or VPN change in the window.
5. **Time.** Start only when the owner or the operator can run step B12 right after the job.

The memory gate is checked once, before the claim. It can not see what happens later. Lines 1 and 3 are the protection for the 180 minutes that follow.

### Start

Start the watchdog first. Then start the launcher within 15 minutes. These PowerShell lines are PROPOSED. They follow the form used for the earlier jobs. They have not been run in this form.

```powershell
$d='D:\tksCAS-runs\controller_cas_optionb_b1'
$w=Start-Process -FilePath 'C:\Python314\python.exe' -ArgumentList '-B',"$d\watchdog.py" -WorkingDirectory $d -WindowStyle Hidden -RedirectStandardOutput "$d\watch.stdout.log" -RedirectStandardError "$d\watch.stderr.log" -PassThru
$ok=$false
for($i=0;$i -lt 60;$i++){ Start-Sleep -Seconds 2; if(Test-Path "$d\WATCH.json"){ try{ if((Get-Content "$d\WATCH.json" -Raw | ConvertFrom-Json).status -eq 'READY'){ $ok=$true; break } }catch{} }; if($w.HasExited){break} }
"watch pid=$($w.Id) ready=$ok exited=$($w.HasExited)"
if($ok){
  $l=Start-Process -FilePath 'C:\Python314\python.exe' -ArgumentList '-B',"$d\aws_control.py",'launch' -WorkingDirectory $d -WindowStyle Hidden -RedirectStandardOutput "$d\launch.stdout.log" -RedirectStandardError "$d\launch.stderr.log" -PassThru
  @{watch_pid=$w.Id; launch_pid=$l.Id; started_utc=[DateTime]::UtcNow.ToString('o'); job='cas-optionb-b1'} | ConvertTo-Json | Set-Content -Path "$d\PROCESSES.json" -Encoding utf8
  "launch pid=$($l.Id)"
} else { Get-Content "$d\watch.stderr.log" -Tail 30 }
```

What the launcher does, in order:

1. It runs every authority check. A failure here costs nothing.
2. It checks the storage route and that no host of this slot is alive.
3. It checks the free disk space (24 GB) and the free memory (2,000,000,000 bytes). A failure here costs nothing.
4. It checks that the guest script and the signed links fit the 60,000 character limit of the command channel. A failure here costs nothing.
5. It writes `SINGLE_ATTEMPT_CLAIM.json`. **From here the attempt is used.**
6. It writes `LAUNCH_INTENT.json` and uploads `input.zip` (about 1.0 GB).
7. It starts the host and writes `CONTROL.json`.
8. It sends the guest script once, when the host answers.
9. It polls every 120 seconds until the result is downloaded or the host has ended.
10. It always ends with cleanup and writes `CLEANUP.json`.

## B11. What to watch

| File | What it tells you |
|---|---|
| `launch.stdout.log` | one line `ACTUAL_LAUNCH_CONFIRMED` with the instance id and the deadline |
| `launch.stderr.log` | the reason, if the launcher stopped before the claim (for example `LOCAL_MEMORY_RESERVE`) |
| `STATUS.json` | rewritten every 120 seconds: `dispatch`, `phase`, `setup_complete`, `downloaded` |
| `LATEST_PROGRESS.json` | the guest's last progress message: its stage and `setup_complete` |
| `WATCH.json` | the watchdog's heartbeat; `ARMED` while the host lives |
| `TRANSIENT_POLL_*.json` | a read-only poll failed once and was skipped; up to 15 in a row are tolerated |
| `CONTROL_FAILURE_*.json` | a control step failed; read `stage` and `message` |
| `REMOTE_TERMINAL.json` | the guest's final message |
| `DOWNLOAD.json` | the archive was downloaded and re-opened; its sha256 |
| `CLEANUP.json` | the job is over on the AWS side |

Points on the clock:

- **Minute 30.** The guest must have reported `setup_complete` true. If not, the launcher ends the host with `SETUP_CUTOFF`. In this job the guest sets that flag right after its Gate 0 self-test passes and before the first model call.
- **Minute 135.** The guest stops all model work.
- **Minute 175.** The host shuts itself down, whatever else happens. The watchdog also ends it.
- **Minute 180.** Hard limit.

EXPECTED: a full run ends between minute 45 and minute 105. A stop at a practice gate ends near minute 40.

While it runs: do nothing by hand. Do not start a second launcher. Do not stop the watchdog. Do not let the laptop sleep.

If the laptop sleeps or loses its network, the host still shuts itself down at minute 175. That limits the cost. It does not save the result. A sleep, a lost network or a dead control program can end the host early, and then the records of the run are lost and the attempt is used. See the list at the top of step B10.

## B12. Independent cleanup check: at once, and before minute 180

As soon as `CLEANUP.json` exists:

```bash
cd "D:/tksCAS-runs/controller_cas_optionb_b1" && /c/Python314/python.exe -B independent_cleanup.py > independent_cleanup.stdout.log 2> independent_cleanup.stderr.log; echo "exit=$?"
```

It only reads. It writes `INDEPENDENT_CLEANUP.json`.

**Two time limits. Both are REAL, read in the code. Nothing arms this check at launch; a person must run it.**

1. **Within 30 minutes after `CLEANUP.json`.** The check finds the ended host through AWS's own listing. AWS drops an ended host from that listing after about an hour. On the job of 2026-10-04 the check ran about 62 minutes after the end and wrote `NOT_VERIFIED_COMPLETE` for that reason alone.
2. **Before minute 180 after launch** (`termination_unix` in `LAUNCH_INTENT.json`). The check sets its own deadline to that time (`independent_cleanup.py` line 6). After it, every storage read is refused (`bounded_s3.py` lines 28 to 30 and line 111) and the script stops without a record.

So: run it at once. If the job ran to the forced shutdown, `CLEANUP.json` appears near minute 177 to 179, and only one to three minutes are left.

| `status` in `INDEPENDENT_CLEANUP.json` | Meaning |
|---|---|
| `VERIFIED_COMPLETE` | Host ended, no disk, no object, no open upload; the archive is on the laptop and complete. |
| `CLOUD_CLEANUP_VERIFIED_EVIDENCE_INCOMPLETE` | The AWS side is clean. The archive is missing or not complete. |
| `NOT_VERIFIED_COMPLETE` | Something is not shown clean. Read the fields. Do not start another job on the slot until it is clear. |

If the check was late and says `NOT_VERIFIED_COMPLETE` only because the host is no longer listed, write a supplementary read-only observation, as was done on 2026-10-04 (`SUPPLEMENTARY_CLEANUP_OBSERVATION.json` in the old folder). Say plainly that the independent check itself is not verified.

## B13. Read the result

1. `deliverable.zip` is the result archive. `DOWNLOAD.json` holds its sha256. `ARTIFACT_REOPEN_VERIFICATION.json` lists every member with its hash.
2. The outcome code is in the file `RESULT.json` of the runner's folder `run_b1` inside the archive, field `outcome_code`. The guest sets the exact path inside the archive; find it in the member list of `ARTIFACT_REOPEN_VERIFICATION.json`. Do not unpack or run anything else on the laptop; read that one file from the archive.
3. Report the code exactly as printed. A stop code is a stop. `INVALID_RUN` is not a finding about roles.
4. If there is no archive: report that. The attempt is used. A new attempt needs new cases and a newly reviewed version.

## B14. Post the bus release

One line, `"type":"DONE"`, subject `SLOT RELEASED: GPU job cas-optionb-b1 finished (<outcome or stop code, exactly>); independent cleanup <status>`. Name `INDEPENDENT_CLEANUP.json` and its sha256.

Tell the next slot user one more thing in the body: this controller's cleanup record has the old GPU-controller form, not the form with `"status": "VERIFIED"`. The next job's builder must read it as an external record of that form.

## B15. Budget addendum

Write one addendum `BUDGET_RECONCILIATION_ADDENDUM_CAS_OPTIONB_B1_<utc>.json` in `helm_operator_preparation/` and update the pointer by a delta on the value read at that moment. Set `"last_jobs": ["cas-optionb-b1"]`.

PROPOSED rule, the same shape as the earlier jobs:

- If `INDEPENDENT_CLEANUP.json` says `VERIFIED_COMPLETE`: the 5.00 USD hold is replaced by a conservative charge. List-price use = `1.212 × hours + 100 × (0.08 / 730) × hours + 0.005 × hours`, with the host hours taken from AWS's launch and end times. Charge = the smaller of 5.00 and `ceil((1.5 × use + 0.05) × 100) / 100`.
- If it says anything else: the whole 5.00 USD stays on the ledger until the owner orders a release or the bill arrives. That is what happened to the 8.00 USD hold of 2026-10-04.

The bill itself lags by about a day. Record it as pending.

## B16. Archive copy

Copy the whole controller folder, the lease and the addendum to `D:/tksCAS-archive/casalescence_optionb_b1_<date>/`. Leave out `*.lock` files. Confirm each file three ways: hash of the source, hash of the copy, and for `deliverable.zip` the hash in `DOWNLOAD.json`. Write an `ARCHIVE_MANIFEST_<utc>.json` with every path, size and hash.

Do this before any other work. Two earlier results were once found only on a retired machine.

## B17. Records in the repository

The result, pass, fail or stop, goes into `docs/CAS_HARNESS_SPEC_SHEET.md` and `CHANGELOG.md` in the same commit, with exact numbers and the artifact path. A negative result is never deleted. This run sheet does not do that step.

The status word of the spec sheet is not chosen after the result. A program prints it from the owner's table that seal step 7 sealed: `tools/ob_seal.py status-word --result <path of RESULT.json>`. If no result file came back: `tools/ob_seal.py status-word --no-result-file`. Quote the printed line. If it prints `NOT_IN_TABLE`, report that; nobody fills the word in by hand. That tool belongs to another builder; this sheet only names its command (`FILE_FORMATS.md` section 19.2).

---

# Part C. If something goes wrong

| What you see | Where in time | Money | What to do |
|---|---|---|---|
| The build of a development test stops with `ATTEMPT_MUST_BE_A_WHOLE_NUMBER_FROM_1_TO_2_FOR_THIS_KIND` | before any job | none | Both development tests are used, or the number is wrong. There is no third test. Report. |
| The build of a development test stops with `CONFIG_KIND_DIFFERS_FROM_WHAT_THE_SEAL_FILE_SHOWS` or `PACKAGE_SEAL_COPY_FITS_NEITHER_THE_SEAL_FILE_NOR_A_REHEARSAL` | before any job | none | The real seal file exists. A development test can only run before seal step 1. Report. |
| A development test does not pass | after the job | at most 0.50 USD | Report the status and the stop code exactly. Nothing is sealed, so the fault may be fixed. Then the second test on a new package (Part 0, step 0.9). |
| 2 development tests are used and none passed | after the second test | at most 1.00 USD in all | Nothing is sealed. No third test. Report to the owner. |
| The pre-check build stops with `REPLACE_COUNT ...` | before any job | none | A base file changed. Do not edit around it. Report. |
| A build stops with `SEAL_FILE_HOLDS_A_TOOL_REPAIR_LINE_OUTSIDE_ITS_WINDOW` or `TOOL_REPAIR_LINE_OUTSIDE_ITS_WINDOW_FILE_FORMATS_15_2` | before any job | none | The seal file holds a tool-repair line at or after the line 3C. Amendment A5 does not allow one there. Do not edit the seal file. Report. |
| The pre-check build stops with `CONFIG_KIND_DIFFERS_FROM_WHAT_THE_SEAL_FILE_SHOWS`, `A_LOWER_ATTEMPT_NUMBER_WAS_NEVER_LAUNCHED_USE_IT_FIRST` or `SEAL_STEP_7_IS_WRITTEN_NO_FURTHER_PRECHECK` | before any job | none | Correct the config, not the build. Report if the seal file is not as you expect. |
| Pre-check `preflight` fails | before the claim | none | Read `preflight.stderr.log` and `first_control_error.json`. Report. |
| A pre-check does not pass | after the job | at most 0.50 USD | No GPU launch. Report the status and the stop code exactly. Then step A9: the record names the case. |
| 4 pre-check jobs are used and none passed | after the fourth job | at most 2.00 USD in all | No launch. Report to the owner. |
| `readiness` exits 2 | before the claim | none | Read `READINESS_RECEIPT.json`, field `reason`. Report. |
| Launcher stops with `LOCAL_MEMORY_RESERVE ...` | before the claim | none | Free memory was under 2,000,000,000 bytes. Close programs. Start the watchdog and the launcher again. No attempt was used. |
| Launcher stops with a name such as `PRIOR_SERIAL_CLEANUP`, `LEDGER_CHANGED_...`, `FRESH_PRICE`, `PRECHECK_DID_NOT_PASS`, `SEAL_...`, `OWNER_STATUS_TABLE_...`, `LAUNCH_FLOOR_...`, `SSM_SIZE_BEFORE_STAGING` | before the claim | none | Fix the named record, not the gate. If the gate cannot be met, the launch is blocked. |
| `SINGLE_ATTEMPT_CLAIM.json` exists and the launcher stopped | after the claim | storage only, or host time | The attempt is used. Let cleanup finish. Run the independent check. No second launch. |
| `CONTROL_FAILURE_*.json` with `WATCH_HEARTBEAT_LOST` | after the claim | host time so far | The watchdog stalled, or the laptop slept. The launcher ended the host. The attempt is used. Report it. No second launch. |
| `SETUP_CUTOFF` | minute 30 | about 0.3 to 0.6 USD (EXPECTED) | The guest did not finish setup. Final tasks were not sent. The attempt is used. |
| `CLEANUP_BLOCKED_PARTS_RETAINED.json` | cleanup | storage until the 7-day expiry | The download failed and the uploaded parts were kept on purpose. Do not delete them. A reviewed step must complete them. |
| `CLEANUP_BLOCKED_UPLOADER_LIVE_OR_UNKNOWN.json` | cleanup | host time | The host is not shown ended. Run `aws_control.py cleanup` again. Report. |
| No `CLEANUP.json` at minute 180 | after the hard limit | host is down by itself at 175 | Run `aws_control.py cleanup`, then the independent check, then a read-only observation. |

Never do these: start a second launch of a job id; delete a claim file; edit a gate; rerun a failed stage; score anything on the laptop; delete or overwrite the `source.zip` or the folder of a failed pre-check.

---

# Part D. The last job on the storage slot, and the record the gate asks for

**Which job last used the slot (REAL, 2026-10-05).** `helm-claude-r8-matched-20261005-c05`. Two sources agree:

- the bus: line `claude-0047` (`SLOT NOTICE`, 2026-10-05T09:32:56Z) and line `claude-0048` (`SLOT RELEASED`, 2026-10-05T09:49:42Z) are the last slot lines in `D:/tksCAS-agent-bus/claude_to_codex.jsonl`;
- the ledger pointer: `"last_jobs": ["helm-claude-r8-matched-20261005-c05"]`, written at 2026-10-05T09:49:41Z.

**Does a VERIFIED record in the gate's form exist for it?** Yes (REAL).

- File: `C:/Users/wakil/Documents/Codex/2026-10-01/task-2/helm_operator_preparation/controller_claude_r8_c05/aws-claude-r8-c05-independent-cleanup.json`
- sha256 `298ed3dff67a9088bece7b727f2bd9ad8223584758fca35b7f18e540b7f8b094` (hashed on 2026-10-05; the same value is in `RUN_CLOSEOUT_CLAUDE_R8_C05.json`)
- `"schema": "pointer.saturation.independent-cleanup/1"`, `"status": "VERIFIED"`, `"cleanup_verified": true`, `"compute_cleanup_verified": true`, `"prefix_cleanup_verified": true`, `"instance_state": "terminated"`, `"active_own_job_instances": []`, `"prefix_versions_remaining": []`, written at 2026-10-05T09:48:21Z.

Those are exactly the fields the gate reads.

**The two record forms.** There are two controller families. Each has its own independent cleanup check.

| Family | Its check writes | Status words |
|---|---|---|
| The CPU job kit (`controller_cas_probe_c02`, `controller_claude_*`), also every pre-check job of Part A | `aws-<name>-independent-cleanup.json`, schema `pointer.saturation.independent-cleanup/1` | `VERIFIED` or `NOT_VERIFIED` |
| The GPU controller (`controller_cas_small_op11_claude_c1`), also job b1 | `INDEPENDENT_CLEANUP.json`, no schema field | `VERIFIED_COMPLETE`, `CLOUD_CLEANUP_VERIFIED_EVIDENCE_INCOMPLETE`, `NOT_VERIFIED_COMPLETE` |

The GPU launch gate asks for the first form. The GPU job of 2026-10-04 produced only the second form, and late, so its own record could not serve a later GPU launch. Jobs of the first family have run on the slot since then, and each left a `VERIFIED` record of the first form.

**How the operator produces such a record.** Run the CPU kit's `independent_cleanup.py` from inside that job's controller folder, with no argument, right after both control processes of that job have exited. It only reads: account identity, the host and its disks, and every version under the prefix. It writes the record beside itself. Step A8 is that command for a pre-check job. No tool makes this form for a job of the GPU family; for such a job only its own `INDEPENDENT_CLEANUP.json` and a supplementary read-only observation exist.

**What the launch gate of a job of the CPU kit asks of that record (REAL, read in the base `aws_control.py`, function `preflight`, and in `derive_precheck_job.py`).** This holds for every development test and every pre-check job.

- The file stands in the previous job's folder under `helm_operator_preparation/`, and its sha256 equals the pin the build wrote into the new controller.
- `account`, `region`, `bucket` and `prefix` are the slot's own. `job` is the previous job. `client_token` is that job id plus `-2b`.
- `status` is `VERIFIED`.
- `cleanup_verified`, `compute_cleanup_verified`, `local_preservation_verified` and `prefix_cleanup_verified` are all true.
- `instance` and `all_job_volumes` equal the ids the build pinned. There is exactly one disk.
- The ledger pointer names that job, and only that job, in `last_jobs`.
- At preflight and at launch the controller also asks AWS, read-only: no host of the previous job is alive, its disk is gone, and the prefix holds no object version.

The record of `helm-claude-r8-matched-20261005-c05` meets every point that can be read from files (REAL, read again on 2026-10-05): its `instance` is `i-01bc54291eba4267d`, its one disk is `vol-0d703bc10e7cd373d`, its `client_token` is `helm-claude-r8-matched-20261005-c05-2b`.

**What this means for the order of work.**

1. Today the last job is `helm-claude-r8-matched-20261005-c05`. Its `VERIFIED` record is the `previous` block of the first development test, `d1` (Part 0).
2. After each job of the CPU kit, that job is the last job on the slot. Its `VERIFIED` record (step 0.8 or step A8) is the `previous` block of the next build: the second development test if there is one, then the first pre-check job, then the next pre-check job if there is one.
3. The `VERIFIED` record of the last pre-check job is the prior-cleanup record of the GPU job (step B4).
4. If any other job uses the slot in between, its record takes that place. If it has none in this form, the next launch is blocked and reported.
