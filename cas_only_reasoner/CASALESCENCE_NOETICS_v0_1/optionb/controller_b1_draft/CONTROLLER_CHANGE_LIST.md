# Controller change list: Option B job b1 and its pre-check

**Status: DRAFT after review round 1 and after the amendments of 2026-10-05 (A5, A8, A10). Nothing here has been run. No AWS call was made.**

This file lists every changed line range against the two controllers these files come from, with the reason. "Old" means the old file. "New" means the file in this folder.

Line ranges were computed again on 2026-10-05, after the fixes of review round 1, by a small comparison script (REAL; standard library `difflib`). Line counts are counts of text lines. The first draft of this list gave each line count one too high; the ranges were right. After the amendments the ranges of `controller_common.py` (section 2) were computed again the same way (REAL). The other files of sections 3, 4 and 6 did not change in the amendments.

Checks done on the laptop after the fixes: every Python file parses (`ast.parse`); a parse-only check found no name that is read but never bound; the two JSON templates load. No program in this folder was executed. That holds for the build scripts and the text checks too. After the amendments: every Python file parses again, and the two JSON templates load (REAL).

Section 8 lists what review round 1 changed, in one place. Section 9 lists what the amendments changed, in one place.

## 1. Where the files come from

| File here | Old file | Old sha256 (REAL) | State |
|---|---|---|---|
| `bounded_s3.py` | `D:/tksCAS-runs/controller_cas_small_op11_claude_c1/bounded_s3.py` | `2582940278d720da833e3795d7678b4146046d4bb73deec1c76606f252fdee61` | **byte-identical** (sha256 of the copy is the same) |
| `independent_cleanup.py` | same folder | `4d0b816c14fd65dd8773976a42e0872168da03f73960d810b0a1f286bc5c51e5` | **byte-identical** (sha256 of the copy is the same) |
| `controller_common.py` | same folder | `8cc09ef99eae173917549d14aa3e9f8b8d6ef952d4e065219e28f4683877ccd5` | changed, section 2 |
| `aws_control.py` | same folder | `208da1f5079965c5e33904797d3cbec8dc291b4ba009b0f8b1575420df787784` | changed, section 3 |
| `watchdog.py` | same folder | `b5dde1c4e7811c851147d54dbde7e9acac4c89ec25d2cab1f265f49c7537acd9` | changed, section 4 |
| `precheck_cpu/precheck_supervisor.py` | `.../helm_operator_preparation/controller_cas_probe_c02/cas_probe_supervisor.py` | `fdc407229df3e275ef4fcb989299fb62fb34421e7a0209e4c16e5340af98bb83` | changed, section 6 |
| `precheck_cpu/derive_precheck_job.py` | new; modeled on `build_cas_probe_job.py` | | section 7 |

The old controller ran once, on 2026-10-04 (job `casalescence-small-v02-20261004-op11`). The probe ran once, on 2026-10-04 (job `cas-small-v02-software-probe-20261004-c02`).

The two byte-identical files were copied with a file copy, not retyped. The launcher refuses to start if either one has other bytes (`controller_common.py`, constant `IDENTICAL_SHA`). Both hashes were measured again after the fixes (REAL): they are unchanged.

Because `bounded_s3.py` is unchanged, three old names stay in the new job: the environment variable `OP11_CONTROL_DEADLINE_UNIX`, the local request ledger `op11-s3-ledger.json`, and its request budgets. Because the guest checks them, three more old names stay in `aws_control.py`: the folder `/opt/helm-op11-worker`, the service `helm-op11-work`, and the service `helm-op11-host-deadline`.

## 2. `controller_common.py` (old 94 lines, new 170 lines)

| Old lines | New lines | What changed | Why |
|---|---|---|---|
| 1 to 2 | 1 to 2 | Docstring. `re` added to the imports. | New job. `re` is used by the seal check. |
| 9 to 12 | 9 to 16 | `OPERATOR`, the owner record and `JOB` replaced. New: `CAS`, `LEDGER_POINTER`, `OWNER_APPROVAL` and `OWNER_DIRECTION` with their sha256. `JOB='cas-optionb-b1'`. | The old pins named the takeover instruction of the old job. The new job runs under the standing approval record and the Option B direction record. Both hashes are REAL, taken on 2026-10-05. |
| 18 to 19 | 22 to 34 | `SOURCE_SHA` and `MANIFEST_SHA` removed. New: `CAP_USD=5.00`, `HARD_MINUTES=180`, `MODEL_CALLS=5000`, `CLOCK_SECONDS=[1800,8100,10500,10800]`, `ARCHIVE_CAP_BYTES=100000000`, `INPUT_CAP_BYTES=1100000000`, `COST_BOUNDS`, `LEASE_NAME`, `IDENTICAL_SHA`, `REQUIRED_PINS`, `SEAL_STEPS`. Review round 1 added lines 32 to 34: `REPAIR_STEPS`, `MAX_PROGRAM_REPAIRS=2`, `STATUS_TABLE`. | The package hashes do not exist yet; they now come from the authority record and are checked against `CONTRACT.json` and the seal file. The limits are decision D8 and plan section 19. The three new names serve the seal check, section 2.2. |
| (insert after 42) | 58 to 116 | New helpers: `cents`, `pinned`, `ledger_gate`, `seal_gate`. | See 2.1 and 2.2. |
| 44 to 52 | 118 to 130 | Head of `authority()`. It reads `AUTHORITY_B1.json`. Removed: the handoff record, the previous-operator checks, the 8 USD transferred hold, 240 minutes. Added: schema and status, two owner records, the owner's yes record, the b1 scope numbers, the ledger gate, the byte-identity check, the new lease name. | "New authority record and pins for this job." The old checks belong to the old job. |
| 56 | 134 | The list of pinned records loses `scientific_acceptance_binding`. | That record was the old package's acceptance. Its place is taken by the seal check. |
| 58 to 60 | 136 to 142 | The prior-cleanup gate, the review check, the pins check. | See 2.3. |
| 62 to 71 | 144 to 146 | Price receipt: must name this job; cap 5.00, 180 minutes, `COST_BOUNDS`. The old lines 65 to 71 (acceptance binding, review receipts, protocol review) are removed. | Old-package records. |
| 73 to 75 | 148 to 151 | Input cap 1,100,000,000 bytes. Route receipt must name this job. Contract: job, manifest hash, `limits.model_calls` 5000, `limits.archive_bytes` 100000000. Then `seal_gate`. | b1 limits. |

Unchanged, byte for byte: old lines 3 to 8, 13 to 17, 20 to 43, 53 to 55, 57, 61, 72 and 76 to 94. That covers `require`, `sha`, `read`, `save`, `utc`, `clients`, the lease field check, `discover`, `scoped_volumes`, `no_live_conflict`, `terminate` and `preserve_error`.

### 2.1 `ledger_gate` (new lines 62 to 71)

Decision D8 says the ledger is read again before launch. The gate makes that a program rule.

- The authority record carries the reading and the sha256 of the pointer file.
- The gate hashes the pointer file again. A different hash stops the launch with `LEDGER_CHANGED_SINCE_THE_READING_READ_IT_AGAIN`.
- Unreserved funds must be at least 5.00 USD. The record must book one new hold of 5.00 USD.
- Money is compared in whole cents.

### 2.2 `seal_gate` (new lines 72 to 116)

It reads local files only. It follows `FILE_FORMATS.md` sections 11, 15 and 19.

- The seal file must have the hash in the authority record, unbroken line numbers and an unbroken hash chain.
- **Changed in review round 1 (new lines 79 and 82 to 86).** Repair lines are accepted, by the order rule of `FILE_FORMATS.md` 15.2. Leave the repair lines out; what is left must be the nine steps in order, each once. A line `6R_PROGRAMS_REPAIRED` must stand after step 6 and before step 7, at most twice. Before this change the gate refused every seal file that held a repair line, so a repaired package could never be launched.
- **Changed by amendment A5 (new lines 87 to 90).** Each repair line has a window. A line `TR_TOOLS_REPAIRED` must stand after line 1 and before the line `3C_FINAL_QUESTIONS_AND_KEYS`. Stop name: `SEAL_TOOL_REPAIR_LINE_OUTSIDE_ITS_WINDOW`. So nothing can follow the line `7_PRECHECK`: it must be the last line of the seal file. Stop name, as before: `SEAL_MUST_END_WITH_ONE_PRECHECK`. Review round 1 had allowed tool-repair lines after step 7. Under A5 the seal tool can not write one there, so a seal file that holds one is refused.
- The step 7 line must say `selftest_status` `SELFTEST_PASS`.
- The pre-check and the GPU job must have used the same `source.zip`: seal step 7, the authority record and `CONTRACT.json` must carry the same hash. Step 7 always stands after the last program repair, so this is the repaired package when there was a repair.
- **New in review round 1 (new lines 96 to 100).** The authority record names `PRECHECK_RECEIPT.json`: the supervisor receipt of the pre-check job, copied unchanged out of that job's result archive. It must show kind `SEALED_PACKAGE`, status `PRECHECK_COMPLETE_SELFTEST_PASS`, a job id `cas-optionb-b1-precheck-p1` to `-p4`, and the same five values as seal step 7. So a rehearsal or a test on made-up data can not stand in for the sealed pre-check. Stop name: `SEALED_PRECHECK_IS_NOT_A_PASSED_JOB_ON_THE_SEALED_PACKAGE`.
- The two hashes the guest hands to Gate 0 come from `CONTRACT.json`, block `precheck` (REAL, read in the guest draft `worker_v02.py` and in `build_contract_b1.py`). They must equal seal step 7. A contract with other values would stop the GPU job in its self-test and spend the attempt.
- **Review round 1 (new line 103 and 104).** Where two seal lines list one path, the later line counts. That is the "hash in force". The code already read the file that way; the comment now says so.
- **New in review round 1 (new lines 106 and 107).** The owner's table of status words, `optionb/OUTCOME_STATUS_TABLE.json`, must be listed in the step 7 line, and the file on the laptop must still have that sha256. Stop name: `OWNER_STATUS_TABLE_NOT_SEALED_IN_STEP_7_OR_CHANGED`. So the launch can not happen before the status words are fixed.
- The sealed `PLAN_CONSTANTS.json` must agree with this controller on cap, minutes, attempts, call cap, archive cap, image, machine type and the four clock numbers. A difference stops the launch with `CONTROLLER_AND_SEALED_PLAN_DISAGREE`.
- The sealed `removal_log.json` must say the launch floor is met, and its four counts must reach the floor numbers of the sealed plan.

This makes decision D7 and the launch floor conditions of the launch, checked by a program, before the single-attempt claim.

### 2.3 The prior-cleanup gate (new lines 136 to 139)

Old: the record had to name one job, fixed in the code at build time, with status `VERIFIED` and six more fields.

New: the same status and the same six fields, plus the schema, the bucket and the prefix. The job name comes from the authority record. It must not be this job. It must be the last job the shared ledger carries (`last_jobs`). So the record is for the most recent job on the slot, and an unclosed earlier job blocks the launch.

The gate is not loosened. It runs before the claim. If no such record exists the launch is blocked.

Also new: the review record must name this job, and `SOURCE_PINS.json` must list at least the five controller programs, the guest, `CONTRACT.json` and `input.zip`.

## 3. `aws_control.py` (old 355 lines, new 463 lines)

| Old lines | New lines | What changed | Why |
|---|---|---|---|
| 1 to 2 | 1 to 2 | Docstring. Review round 1: `ctypes` added to the imports. | New job. `ctypes` reads the free memory, section 3.2. |
| (insert after 7) | 8 to 21 | Review round 1, lines 8 to 18: `LOCAL_MEMORY_RESERVE_BYTES=2000000000` and `free_physical_memory()`. Then two comment lines and one check: `CLOCK_SECONDS==[1800,8100,10500,10800] and ARCHIVE_CAP_BYTES==100000000`. | Section 3.2. A mismatch between this file and `controller_common.py` stops the program at start, before any claim. |
| 42 | 56 | `0<total<=18000000000` becomes `0<total<=ARCHIVE_CAP_BYTES`. | Archive cap 100,000,000 bytes. |
| 102 | 116 | Expansion cap `18000000000` becomes `ARCHIVE_CAP_BYTES`. | Same. The guest stores the archive without compression, so unpacked size is not above archive size. |
| 139 | 153 | Output cap `18000000000` becomes `ARCHIVE_CAP_BYTES`. | Same. |
| 143 | 157 | Download cap `max_bytes=18000000000` becomes `ARCHIVE_CAP_BYTES`. | Same. |
| 229 | 243 to 246 | Review round 1, lines 243 to 245: the free-memory gate and its local record `LOCAL_MEMORY_GATE.json`. Line 246: signed-link life default `expires=14400` becomes `expires=10800`. | Section 3.2. "Link life scaled to 180 minutes." |
| 236 | 253 | Control deadline `started+14340` becomes `started+10740`. | "Control deadline scaled to 180 minutes." Same 60 second offset as before. |
| 237 | 254 | Intent clock: `started+11400`, `started+14100`, `started+14400` become `started+8100`, `started+10500`, `started+10800`. `started+1800` stays. | The b1 clock: 1800 / 8100 / 10500 / 10800. |
| 241 | 258 | Upload cap `max_bytes=4200000000` becomes `INPUT_CAP_BYTES`. | The input is about 1.0 GB. A cap of 1.1 GB keeps the storage cost bound true. |
| 282 | 299 | Host shutdown time `started+14100` becomes `started+10500`. | Forced shutdown at minute 175. |
| 292 | 309 | Printed deadline `started+14400` becomes `started+10800`. | Hard limit at minute 180. |
| 302 | 319 | In the bootstrap text, `started+14100` becomes `started+10500`. | Forced shutdown at minute 175. |
| 320 | 337 | Command time limit `started+14100` becomes `started+10500`. | Forced shutdown at minute 175. |
| (insert after 349) | 367 to 455 | New: `SUBNET`, `SECURITY_GROUP`, `readiness()`, `hashes()`. Review round 1, line 450: `hashes()` also prints the hash of `PRECHECK_RECEIPT.json` and of the owner's status table. | See 3.1. |
| 351 to 352 | 457 to 460 | `main()` accepts `readiness` and `hashes` beside `launch` and `cleanup`. | See 3.1. |

The clock numbers are plain numbers in the text, as in the old file. The build-time text check `text_check_b1.py` compares them with the guest. Its patterns for checks A2, A3 and X7 were replayed on this file, on `watchdog.py` and on `controller_common.py` after the fixes of review round 1, by a separate counting script (REAL, 2026-10-05): each of the four intent times is found once with the right number; every `started+N` is one of 1800, 8100, 10500, 10740, 10800; the link life is 10800; 269 upload links; the old archive cap is gone. `text_check_b1.py` itself was not run after the fixes.

Unchanged, byte for byte: everything else. That covers the three 30 minute waits (`started+1800`), the multipart upload handling, `private_preflight`, `reopen`, `retrieve`, `cleanup`, `read_watch`, `tolerate`, the launch order, the size check of the command channel (it still runs before the claim), the single-attempt claim, the host launch call, the bootstrap text apart from one number, the 269 upload links of 64 MiB, the polling loop and its 120 second sleep, the 24 GB free-disk rule, and the rule that the launcher stops when the watchdog's heartbeat is 180 seconds old.

### 3.1 `readiness()` and `hashes()`

No readiness script was assigned to this folder, and the launcher cannot start without a fresh price receipt and a route receipt. So the old `read_only_readiness_c1.py` and `read_only_storage_network_prices_v02.py` were folded into one read-only mode of `aws_control.py`.

- `readiness` makes read-only calls only. It starts no host, uploads nothing, writes nothing to AWS and calls no invoice service. It refuses to run once a claim or an intent exists.
- It uses its own plain clients, as the old script did. It does not touch the request ledger of the launch.
- Same checks as the old script: identity; prior job ended; no live host on the slot; image; network; machine shape; zone offering; nine storage reads; live prices.
- Changed against the old script: the prior job and its record are read from `PRIOR_INDEPENDENT_CLEANUP.json` and must match the ledger's last job; the prior host is looked up by filter, so an id that AWS no longer lists gives an empty answer and not an error; receipts hold plain facts, not raw AWS replies; the cost formula uses `COST_BOUNDS` (3 hours, 1.2 GB stored for 8 billable days, 0.2 GB sent out, 2,000 and 1,000 requests, 100 GiB disk, 1.00 USD allowance) and must come out at or under 5.00 USD.
- EXPECTED result of that formula at the rates seen on 2026-10-04: about 4.72 USD.
- `hashes` is laptop-only. It calls no AWS service and writes nothing. It prints the hashes and ledger numbers the authority record needs.

Both modes are new and have never run. Both act before the claim, so a fault in them costs no money.

### 3.2 The free-memory gate (review round 1; new lines 8 to 18 and 243 to 245)

The review found that the run sheet called a sleeping laptop harmless, and that nothing checked the laptop's memory before the single-attempt claim.

- Two laptop programs must stay alive for up to 180 minutes: the launcher and the watchdog. If the watchdog's heartbeat is 180 seconds old, the launcher stops and its cleanup ends the host. In the final phase that loses the records of a paid run.
- `free_physical_memory()` reads one number from Windows, with `ctypes` and the call `GlobalMemoryStatusEx`. It changes nothing.
- The gate stands beside the disk gate, before the claim. It needs 2,000,000,000 bytes of free physical memory. That number is PROPOSED by the review. It is not a measured need. A miss stops the launch with `LOCAL_MEMORY_RESERVE` and the two numbers. It costs nothing. When the gate passes, the reading is written to `LOCAL_MEMORY_GATE.json`.
- REAL, 2026-10-05: a separate small script with the same structure returned 598,933,504 free bytes of 16,866,705,408 (structure size 64 bytes, call result 1). So a launch on the laptop as it stood then would have been refused. The launcher itself was not run.
- The gate checks one moment. It can not keep the laptop awake. The run sheet, step B10, has the owner's checklist for that. The reviewed logic of the launch, the watchdog and the cleanup is unchanged.

## 4. `watchdog.py` (old 42 lines, new 44 lines)

| Old lines | New lines | What changed | Why |
|---|---|---|---|
| 1 | 1 | Docstring. | New job. |
| (insert after 3) | 4 to 5 | One comment line and one check: `CLOCK_SECONDS[2:]==[10500,10800]`. | A mismatch with `controller_common.py` stops the watchdog at start. |
| 13 | 15 | `+14400` and `+14100` become `+10800` and `+10500`. | Old line 13 required the 240 minute clock. |

Everything else is unchanged, byte for byte. Review round 1 changed nothing in this file.

## 5. What is new in behaviour, and has never run

1. The 180 minute clock in the launcher and the watchdog.
2. The whole new `authority()`: owner records, owner's yes record, ledger gate, seal gate (with repair lines, the pre-check receipt and the owner's status table), prior-cleanup gate with the ledger cross-check.
3. `readiness` and `hashes`.
4. The archive cap of 100,000,000 bytes and the input cap of 1,100,000,000 bytes.
5. The free-memory gate.

Items 2, 3 and 5 act before the single-attempt claim. A fault there blocks the launch and costs nothing. Items 1 and 4 act after the claim.

## 6. `precheck_cpu/precheck_supervisor.py` against `cas_probe_supervisor.py` (old 785 lines, new 850 lines)

| Old lines | New lines | What changed | Why |
|---|---|---|---|
| 1, 6, 8 to 11 | 1, 6, 8 to 22 | Docstring. Review round 1 added lines 16 to 22. | New purpose. |
| 29 to 31 | 40 to 53 | Job id and the two package hashes become fill-in values. Review round 1: the job id is now a fill-in value too (`@@JOB@@`), and `PRECHECK_KIND` is new (`@@PRECHECK_KIND@@`). New: `MAXIMUM_WORKLOAD_SECONDS=2100`, `MODEL_SNAPSHOT`, `SELFTEST_ARGV`, `SELFTEST_PASS`. | The package does not exist yet. Each pre-check job has its own job id. The work window is 35 minutes. The self-test command is one constant, so it can be matched to the runner before the review. |
| 43 to 45 | 65 to 68 | Stage 4 is `selftest`. Limits: 60, 600, 180, 900 seconds (old: 60, 900, 180, 135). | The window is shorter. The install took 24.5 seconds in the probe (REAL). The self-test time is NOT MEASURED. |
| 52 | 75 | The modules the last stage needs: `transformers`, `tokenizers`, `numpy`, `torch` (old: `sklearn` in place of `tokenizers`). | The self-test loads a tokenizer and runs the analysis program. |
| 660 to 662, 665, 667, 669 to 673, 675, 679 to 695, 698 to 699, 701, and one line added after 703 | 683 to 747 | The stage that ran the 28 package tests is replaced by the `selftest` stage. The lines that list and remove the stage's scratch folder are kept. Review round 1: the row gains `selftest_started` (lines 686 to 687 and 711 to 712). | See below. |
| 719 to 720 | 763 to 764 | The deadline check uses 2100 seconds (old 3000). | 35 minute work window. |
| 724 to 725 | 768 to 770 | Scope text of the receipt. Review round 1: the receipt carries `precheck_kind`. | New purpose. |
| (insert after 728) | 774 to 775 | Review round 1: the receipt carries the sha256 of `source.zip` also under the name `source_zip_sha256`. | `tools/ob_seal.py` reads that name when it records a failed pre-check in a repair line. |
| 755 | 802 | The fourth stage call. | Stage 4. |
| 762 | 809 | The fourth pass condition. | Stage 4. |
| 769 to 770 | 816 to 825 | The five values of seal step 7. Status words: `PRECHECK_COMPLETE_SELFTEST_PASS`, `PRECHECK_COMPLETE_WITH_FINDINGS`. Review round 1: the five values stand under `seal_step_7_values` only when the kind is `SEALED_PACKAGE`; otherwise under `values_never_for_a_seal_file`. | A rehearsal or a test on made-up data is never written to a seal file (plan section 19.1). |
| (insert after 774) | 830 to 839 | Review round 1: the block `after_a_failure_facts` with four plain facts. It is written in every case, also when the supervisor stopped. | Plan section 19.1: the record decides which case a failed pre-check is, not the operator. |

Stages 1 to 3 (image inventory, pinned install, import check) are unchanged, byte for byte. They are "the same pinned environment": the nine pins of `contracts/requirements.small-linux.txt`, installed from pypi.org as binary wheels, with the one path line that exposes the image's torch.

The `selftest` stage:

- refuses to run if `model.safetensors` is on the host;
- runs `runner_b1.py selftest --mode precheck` once, in the installed environment, with absolute folders for the package, the tokenizer files and the output;
- gives the runner a new output folder inside `results/`, so everything it writes is returned;
- reads `selftest.json`, and hashes `prompt_hashes.jsonl` and `padding_plan.json` itself;
- passes only if the command exits 0, the status is `SELFTEST_PASS`, the mode is `precheck`, and the two bound hashes equal the hashes of those two files.

A stop such as `GATE_STOP_SELFTEST` or `GATE_STOP_PADDING` makes the stage `FAIL`. The job still returns its evidence. The status is then `PRECHECK_COMPLETE_WITH_FINDINGS`, and the GPU job is not launched.

The four facts of `after_a_failure_facts`:

| Fact | Meaning |
|---|---|
| `selftest_started` | true once the runner process was really started |
| `selftest_json_present` | true if `selftest.json` could be read |
| `selftest_status` | the status in `selftest.json`, or null |
| `check_package_matches_seal` | the result of the self-test's check of that name: true, false, or null if it is not there |

The supervisor names no case. The run sheet, step A9, maps the facts to the four cases of plan section 19.1.

The four fill-in values each stand exactly once in the file (REAL, counted after the fixes): `@@JOB@@`, `@@PRECHECK_KIND@@`, `@@SOURCE_ARCHIVE_SHA256@@`, `@@BUNDLE_MANIFEST_SHA256@@`.

## 7. `precheck_cpu/derive_precheck_job.py`: what it changes in the probe controller

The script writes one pre-check controller folder from the probe's reviewed bytes. Every change is an exact-count text replacement. A count that is off stops the build.

The counts were proved against the real base files on 2026-10-05 by the first draft of this script (`--check-text-only`, REAL, `TEXT_CHECK_PASS`). The script was changed in review round 1 and has not been run since. REAL for the new names: a separate counting script applied the five name replacements to the real base files for all eight job names the script could give then. After amendment A10 it gives six of those eight (`d3` and `d4` are gone); no edit table changed. It found the expected counts each time: job line 1, file stem 18, payload name 4, lease 1, claim 1 in `aws_control.py`; job id 10 in `worker.sh`; file stem 6 and payload name 1 in `independent_cleanup.py`. No new name holds one of the stale words the script looks for.

### 7.1 Review round 1: one folder per pre-check job

The review found that the job id, the folder, the lease and the claim were fixed in the code. So a second pre-check job needed code edits and a new review. The plan now allows up to 4 pre-check jobs (section 19.1).

- The config file names two new things: `attempt` (1 to 4) and `kind`.
- `name_the_job()` sets six names from them. For attempt N of a pre-check job: job id `cas-optionb-b1-precheck-p<N>`, file stem `aws-cas-optionb-precheck-p<N>`, payload `cas-optionb-precheck-p<N>-payload.zip`, lease `CAS_OPTIONB_PRECHECK_P<N>_TRANSPORT_LEASE.json`, claim `CAS_OPTIONB_PRECHECK_P<N>_SINGLE_LAUNCH_CLAIM.json`, folder `controller_cas_optionb_precheck_p<N>`. A test on made-up data gets `devtest-d<N>` in place of `precheck-p<N>`.
- A number is used only when every lower number of its series has a claim file. A launch leaves its claim file behind. So the numbers count the launched jobs, and no number is used twice.
- The kit's limits must equal the plan's: 4 jobs, 0.50 USD, 45 minutes. A difference stops the build.
- The job id in the supervisor is filled in by the build, as the two package hashes are.
- The old fixed file stem had one more fault. A second pre-check job names the first one as its previous job, and the first job's cleanup file name began with the same stem. The count check "18" would then have failed. The suffix removes that.

### 7.2 Review round 1: the kind of job

| `kind` | How the build knows | Counts toward the 4 jobs |
|---|---|---|
| `SEALED_PACKAGE` | The seal copy inside `source.zip` is the start of the real seal file, and ends with its last program line (step 6, or the last line `6R_PROGRAMS_REPAIRED`). Step 7 is not written yet. | yes |
| `REHEARSAL` | The real seal file ends with step 5. The seal copy inside `source.zip` is the real seal file plus one line, a step 6 line. | yes |
| `DEVELOPMENT_TEST` | No real seal file exists yet (before seal step 1). | no; it has its own limit of 2 (amendment A10) |

The config must say the kind the files show. Otherwise the build stops with `CONFIG_KIND_DIFFERS_FROM_WHAT_THE_SEAL_FILE_SHOWS`. The kind goes into the supervisor and into its receipt.

Review round 1 left the test on made-up data open, and the script allowed `d1` to `d4`. Amendment A10 changed that; see 7.5.

### 7.3 Review round 1: `tools/verdict.py`

`tools/verdict.py` is now one of the package files that must be in `source.zip` (list `PROJECT_FILES`). Its sha256 must be the one pinned in `PLAN_CONSTANTS.json`. The same list goes into the host's own check of the package files. So the self-test runs the three word-matching views of the analysis program in the pre-check.

### 7.4 What the script does to the base files (unchanged in review round 1)

Copied unchanged: `bounded_s3.py` (probe family version, sha256 `c16fc985ccb409fdb2a1cba4c8b5ce3735fba0a0f50b1e455b0abe981d772c0c`) and `service_prices.py`.

Changed lines of the base files (old line numbers, REAL):

| Base file | Old lines changed | What changes |
|---|---|---|
| `aws_control.py` | 12, 13, 19, 26, 28, 30, 32 to 34, 84, 99 to 103, 112 to 113, 123, 145, 219, 224, 279, 343, 383, 390, 427, 431, 479, 487, 494, 506, 532, 538, 544, 550, 567, 576 | job id; previous job, its folder, its record name, its hash, its host and disk; file names; payload name; lease and claim names; the two package hashes; the two ledger numbers; the purpose text |
| `aws_control.py` | 18 | cap `1.00` becomes `0.50` |
| `aws_control.py` | 64 to 65 | policy check: host 60 becomes 45 minutes; window 3000 becomes 2100 seconds; cutoffs 50 and 55 become 35 and 40 minutes |
| `aws_control.py` | 277 | compute estimate for 60 minutes becomes 45 minutes (`rates[0]*0.75`) |
| `aws_control.py` | 500 to 501, 506 | force cutoff 55 becomes 40 minutes; work cutoff 50 becomes 35; hard deadline 60 becomes 45; window 3000 becomes 2100 |
| `aws_control.py` | 530, 532, 537 | least window at dispatch 2400 becomes 1500 seconds |
| `worker.sh` | 62, 265 to 266, 274, 293, 310, 318 to 319, 366, 371, 411 | job id and the two package hashes |
| `worker.sh` | 375 to 377, 379, 381 to 382 | window 3000 becomes 2100 seconds; least admitted window 2400 becomes 1500; comments to match |
| `worker.sh` | 413, 415 to 416, 420 | status words, stage names and the pass check of the last stage |
| `runtime_preflight.py` | 30, 58 to 59, 65 | job id; the list of package files that must exist; the manifest hash |
| `shared_entry.py` | 22 | supervisor file name |
| `independent_cleanup.py` (probe family) | 31, 37, 39 to 41, 97 to 98, 314 | job id, file names, payload name, manifest hash |

Policy file `COST_POLICY.json`: cap 0.5; host 45 minutes; window 2100 seconds; least admitted window 1500 seconds; cutoffs 35 and 40 minutes; stage limits; upper estimate 0.493285714286 USD (0.15 compute at the 0.20 USD per hour bound, 0.03 disk, 0.01 address, 0.15 transfer and requests, 0.003285714286 storage, 0.15 allowance). EXPECTED live estimate at the rates seen on 2026-10-05 for the last CPU job: about 0.365 USD.

Why 1500 seconds: the old rule admitted a dispatch only with 2400 of 3000 seconds left, that is 600 seconds after launch at the latest. The same 600 seconds give 1500 of 2100.

Payload: every member of `source.zip` under `sources/cas/`; the six small model B files under `models/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775/` (11,488,523 bytes, REAL sizes); three scripts under `execution/`; the inventory. `model.safetensors` is refused.

Not written by the script, on purpose: `ALLOCATION.json`, `CONTROLLER_REVIEW.json`, `INDEPENDENT_STATIC_REVIEW.json`, the lease and the claim. They grant authority.

New and never run: the build itself, the `selftest` stage, the 45 / 40 / 35 minute clock of the probe controller, the job names with a number, the three kinds.

### 7.5 Amendment A10: the development test is ordered

Line numbers are those of `derive_precheck_job.py` after the amendments (REAL, found by text search; the file has 696 lines).

| Lines | What changed | Why |
|---|---|---|
| 13 to 31 | Docstring: the development test is ordered; at most 2; who authorises it; the window of a tool-repair line. | A10 and A5. |
| 54 to 57 | `OWNER_APPROVAL` and `OWNER_APPROVAL_SHA`. | The record under which the operator orders the test. The sha256 is REAL, taken on 2026-10-05; it equals the pin in `controller_common.py`. |
| 80 to 83 | `DEV_JOBS_MAX = 2` and `SERIES_MAX`. | At most 2 development tests. The 4 pre-check jobs keep their own limit. |
| 101 to 105 | `name_the_job()`: the attempt number is 1 to 4 for a pre-check job, and 1 or 2 for a development test. | So a third development test can not be built. Before, `d3` and `d4` could be built. |
| 363 | `--check-text-only` walks 4 pre-check names and 2 development-test names: six names. | The same limit. |
| 451 to 460 | The kit's limits must also equal the plan's block `aws.development_test_job`: kind, 2 jobs, 0.50 USD, 45 minutes, not one of the 4. For this kind the owner's approval record must have its pinned sha256. | A difference between the kit and the plan stops the build. |
| 633 to 641, 675 | For this kind the draft of `authority_record` in `PRECHECK_ADMISSION_VALUES.json` is the text of amendment A10: operator decision, the approval record with its sha256, the limits. | The operator copies it into `ALLOCATION.json` after the review. The file still grants no authority. |
| 623, 644, 650 to 653, 659 | The receipts name the limit of the kind (`attempts_max_for_this_kind`); the note of the kind is new; `limits_in_the_plan` shows the plan block of the kind. | So the record says which limit applies. |

The cap and the time limit of a development test are the kit's own: 0.50 USD and 45 minutes. They were already the kit's numbers; no number changed.

Nothing in the kit enforces "seal step 1 only after a development test passed". The plan says so too (section 19.1).

### 7.6 Amendment A5: the window of a tool-repair line

| Lines | What changed | Why |
|---|---|---|
| 143 to 144 | Two names: the tool-repair line and the line `3C_FINAL_QUESTIONS_AND_KEYS`. | |
| 509 to 513 | The build stops if the real seal file holds a tool-repair line that does not stand after line 1 and before the line 3C. Stop name: `SEAL_FILE_HOLDS_A_TOOL_REPAIR_LINE_OUTSIDE_ITS_WINDOW`. | A5: a tool repair is allowed only while no final question exists. |
| 520 to 523 | Rehearsal: the real seal file must end with step 5. Before, tool-repair lines after step 5 were left aside. | Under A5 no tool-repair line can stand there. |

The window of the line `6R_PROGRAMS_REPAIRED` (after a failed pre-check job on the sealed package, before step 7) is enforced by `tools/ob_seal.py`, which reads the kept receipt. The kit only reads the place of the line: a package for kind `SEALED_PACKAGE` must end at the last program line, and no further pre-check is built once step 7 is written. That was so before.

### 7.7 Amendment A8: the receipt

No byte of `precheck_supervisor.py` changed. The receipt already carried what seal step 7 now reads (REAL, read in the file):

| What seal step 7 reads | Where the supervisor writes it |
|---|---|
| `precheck_kind` | line 768, in every receipt, from the first write on |
| `status` | lines 824 to 825 (`PRECHECK_COMPLETE_SELFTEST_PASS` or `PRECHECK_COMPLETE_WITH_FINDINGS`), line 828 (`STOPPED_NO_RETRY`) |
| `seal_step_7_values` with the five values `source_zip_sha256`, `selftest_status`, `prompt_list_sha256`, `padding_plan_sha256`, `selftest_json_sha256` | lines 818 to 823, only when the kind is `SEALED_PACKAGE`; otherwise the five stand under `values_never_for_a_seal_file` |

The same receipt serves the 6R window of amendment A5: it carries `precheck_kind`, `status`, `job` and `source_zip_sha256` (line 775).

## 8. Review round 1: every change in this folder, in one place

This table is the record of review round 1. Amendment A5 changed one point of it afterwards: a tool-repair line can no longer follow step 7. Section 9 has that change.

| File | What changed | Finding it answers |
|---|---|---|
| `controller_common.py` | `seal_gate` accepts repair lines by the order rule; it needs the receipt of a passed job on the sealed package; it needs the owner's status table sealed in step 7 | no path after a failed pre-check; rehearsal; status word fixed before the result |
| `aws_control.py` | free-memory gate before the claim; `hashes` prints two more hashes | the laptop can lose the result |
| `watchdog.py` | nothing | |
| `bounded_s3.py`, `independent_cleanup.py` | nothing; still byte-identical | |
| `worker_v02.py` (the guest) | nothing. REAL after the fixes: 56,033 raw bytes; 22,124 packed bytes; sha256 `26eac561681c87fb57b7c43788530a7e12847246d056f4fb9fb3f176751c12d1` | |
| `build_source_zip_b1.py` | `tools/verdict.py` is a required package file; repair lines and the hash in force; the seal copy ends at the last program line; `--seal` for a rehearsal | three views needed a file that was not in the package; no path after a failed pre-check |
| `build_contract_b1.py` | step 7 may be followed by tool-repair lines; the package must hold the seal up to its last program line | no path after a failed pre-check |
| `build_input_zip_b1.py` | nothing | |
| `text_check_b1.py` | check X5: hash in force, last program line, `tools/verdict.py` with its pinned sha256; check X6: tool-repair lines after step 7 | the same two |
| `precheck_cpu/derive_precheck_job.py` | sections 7.1 to 7.3 | fixed job id; rehearsal; `tools/verdict.py` |
| `precheck_cpu/precheck_supervisor.py` | section 6 | fixed job id; the record decides the case |
| `precheck_cpu/PRECHECK_CONFIG.template.json` | `attempt` and `kind` | fixed job id; rehearsal |
| `AUTHORITY_B1.template.json` | `seal.precheck_receipt`; two texts | rehearsal; more than one pre-check job |
| `RUN_SHEET_B1.md` | steps A0, A1, A9, A10, B2, B8, B10, B11, B17, Part C, Part D | no path after a failed pre-check; the laptop can lose the result; status word |

What these changes do not do:

- They do not run anything. Every new code path is unrun.
- They do not write the repair line, the status table or the status word. Those belong to `tools/ob_seal.py`, another builder's file.
- They do not keep the laptop awake. Sleep and power are system settings. The owner sets them (run sheet, step B10).

## 9. Amendments of 2026-10-05 (A5, A8, A10): every change in this folder, in one place

The operator decided twelve amendments after an outside review of the plan (plan section 27). Three of them touch this folder. Nothing was run. Every changed Python file parses (`ast.parse`, REAL). The changed window checks were copied as text into a separate small script and tried on seven made-up lists of seal steps (REAL): a tool-repair line before the line 3C was accepted; one at or after it was refused; a program-repair line between step 6 and step 7 was accepted.

| File | What changed | Amendment |
|---|---|---|
| `precheck_cpu/derive_precheck_job.py` | At most 2 development tests (`d1`, `d2`), with the kit's own cap and time (0.50 USD, 45 minutes). The kit's limits must equal the plan's new block `aws.development_test_job`. The owner's approval record is pinned for this kind, and the draft of `authority_record` is the A10 text. Sections 7.5 and 7.6. | A10, A5 |
| `precheck_cpu/PRECHECK_CONFIG.template.json` | The texts for `attempt`, `kind` and `previous`: a development test is ordered, 1 or 2; who authorises it; the first job on the slot is now test `d1`. | A10 |
| `precheck_cpu/precheck_supervisor.py` | nothing. The receipt already carries `precheck_kind`, `status` and the five values. Section 7.7. | A8 |
| `controller_common.py` | `seal_gate`: a tool-repair line must stand before the line 3C; step 7 must be the last line of the seal file. Section 2.2. | A5 |
| `build_source_zip_b1.py` | The build stops on a tool-repair line outside its window. The receipt says when the study root was a made-up one (`made_up_study_root_never_for_a_seal_or_the_gpu_job`). The docstring names the development-test use of `--study-root`. | A5, A10 |
| `build_contract_b1.py` | `precheck_binding`: step 7 must be the last line of the seal file. | A5 |
| `text_check_b1.py` | Check X6: step 7 must be the last line; a tool-repair line must stand before the line 3C. | A5 |
| `AUTHORITY_B1.template.json` | One text: after step 7 no line is added to the seal file. | A5 |
| `RUN_SHEET_B1.md` | New Part 0, the development test, with every operator step. Step A10: seal step 7 takes `--receipt`. Steps A9 and B8: the windows of the repair lines. Part C and Part D follow. | A10, A8, A5 |
| `aws_control.py`, `watchdog.py`, `build_input_zip_b1.py` | nothing | |
| `bounded_s3.py`, `independent_cleanup.py` | nothing; still byte-identical to the old controller (REAL, both sha256 measured again after the amendments) | |
| `worker_v02.py` (the guest) | nothing. REAL after the amendments: 56,033 raw bytes (limit 73,986); 22,124 packed bytes (limit 28,420); sha256 `26eac561681c87fb57b7c43788530a7e12847246d056f4fb9fb3f176751c12d1` | |

What these changes do not do:

- They do not run anything. Every new code path is unrun. The first run of the kit is the development test itself.
- They do not build the made-up package. That is `optionb/dry/build_dev_package.py`, another builder's file.
- They do not write a repair line or refuse one. That is `tools/ob_seal.py`. This folder only refuses to build or launch on a seal file that holds a repair line outside its window.
- They do not check that seal step 1 comes after a passed development test. No program does (plan section 19.1).
