# Guest change list — `worker_v02.py` for Option B GPU job b1

**Status: built by Claude. Never run. Review round 1 is done; its fixes are in section 11. The amendments of 2026-10-05 are in section 12. Nothing here is a result.**

The guest is the one script that runs on the AWS host. It unpacks the package, builds the Python environment, starts the package's programs and sends the files back.

Review round 1 changed no byte of the guest. Its sizes and its sha256 were measured again after the fixes (REAL, 2026-10-05): 56,033 raw bytes, 22,124 packed bytes, sha256 `26eac561681c87fb57b7c43788530a7e12847246d056f4fb9fb3f176751c12d1`. The three build scripts beside it did change. Section 11 says how.

The amendments of 2026-10-05 changed no byte of the guest either. The same three numbers were measured again after them (REAL): they are unchanged. Section 12 says what changed beside the guest.

This list compares two files:

| | File | Bytes | sha256 |
|---|---|---:|---|
| Old | `D:/tksCAS-runs/controller_cas_small_op11_claude_c1/worker_v02.py` (ran on 2026-10-04) | 73,986 | `cb1f0493fc13d20ea9bf1d863e559662d8e9f5b0a671fabe440e40b4ef33a732` |
| New | `optionb/controller_b1_draft/worker_v02.py` (this draft, not yet stamped) | 56,033 | `26eac561681c87fb57b7c43788530a7e12847246d056f4fb9fb3f176751c12d1` |

The file name `worker_v02.py` and the service name `helm-op11-work` are kept. The design says a new name can break the launch after the single attempt is claimed.

## 1. Sizes

"Packed" means: gzip with `mtime=0`, then base64. That is exactly how `aws_control.py` packs the guest for the launch command (old file line 227, new controller draft line 230).

| Number | Limit | New guest | Kind |
|---|---:|---:|---|
| Raw bytes | 73,986 | **56,033** | REAL, measured 2026-10-05 |
| Packed bytes | 28,420 | **22,124** | REAL, measured 2026-10-05 with `/c/Python314/python.exe` (3.14.0) |
| Old guest packed, same tool | — | 28,420 | REAL; equals `SSM_SOURCE_BOUND.json`, so the tool measures as the launcher did |
| Raw bytes after the stamp (section 6) | 73,986 | about 56,040 | EXPECTED; trial stamps with made-up values, in memory only |
| Packed bytes after the stamp | 28,420 | 22,124 to 22,136 | EXPECTED; eight trial stamps |
| Room left for the packed signed links | — | 21,492 | REAL arithmetic: 60,000 − 16,384 − 22,124 |

Line ends are LF. The file is plain ASCII. It parses as Python (`ast.parse`). It was not executed.

## 2. What did not change

REAL counts from a line comparison (`difflib`, standard library):

- 925 of the 1,373 old lines are unchanged.
- 448 old lines were removed or replaced. 164 new lines were added.
- 29 functions are identical, compared by their parsed form: `canonical`, `cgroup_pids`, `check_time`, `cleanup_children`, `connection`, `download_input`, `extract_entry`, `fallback_archive`, `gpu_preflight`, `imds_instance`, `load_json`, `ordinary`, `progress`, `put_small`, `remaining`, `request_target`, `require`, `run_stage`, `runtime_preflight`, `safe_error`, `safe_relative`, `sha_file`, `terminal`, `transport_url`, `tree_files`, `upload_parts`, `verify_tree`, `write_json`, `zip_records`.
- `runtime_preflight` is among them. So the check of the contract's runtime block is exactly as sealed, including `numpy` `2.5.3`, and the nine pins of `contracts/requirements.small-linux.txt` (sha256 `6d9ee033baf3acbcecfbf8feb735a807025c141cac8e6060e480154c2c1c15b7`).
- All transport code is unchanged: the download, the 64 MiB parts, the 269 part links, the status uploads, the final message.
- All time reserves at the end are unchanged: file hashes must end 1,800 seconds before the forced shutdown, the archive 1,200 seconds before, the upload 600 seconds before.

## 3. Every changed line range

"Old" is the line range in the old file. "New" is the line range in the new file. A dash means the lines exist only on one side.

| # | Old | New | What changed | Why |
|---:|---|---|---|---|
| 1 | 1 | 1 | First line of the description. | It names job b1. |
| 2 | 3–8 | 3–11 | Rest of the description. | It says what this guest does: start the package's commands, read back one code. |
| 3 | — | 41 | New constant `OUT = WORK / 'run_b1'`. | The runner's one output folder, `work/run_b1/`. |
| 4 | 47–51 | 51–81 | Old pins removed: old source hash, old manifest hash, two review hashes, the owner delegation id. New: `SOURCE_ZIP_SHA`, `SOURCE_ZIP_BYTES`, `SOURCE_MEMBERS`, `SOURCE_SEAL` (placeholders until the stamp); `SOURCE_UNPACKED_CAP = 8_388_608`; `SOURCE_FILE_CAP = 400`; `MODEL_REVISION`; `MODEL_FILES = 7`; `MODEL_BYTES = 999_586_347`; the table `CLOCK`; the table `LIMITS`; the table `RUNNER`. | The design's list of constants. All numbers now sit in one place at the top, as plain values, so the build-time text check can read them without running the guest. |
| 5 | 53–54 | 83–84 | `MAX_WORK` was 16 GiB, now 80,000,000 bytes. `MAX_ARCHIVE` was 18,000,000,000, now 100,000,000. Both read from `LIMITS`. | The plan's archive cap is 100,000,000 bytes. The guest keeps 16 MiB of the archive for its file list, so the work folder cap must be below 83,222,784. |
| 6 | 101–104 | — | Function `digest` removed. | Only the removed pilot code used it. |
| 7 | 210–218 | — | Function `artifact` removed. | Only the removed pilot code used it. |
| 8 | 281–283 | 298–299 | The clock check reads the table `CLOCK`: 1800 / 8100 / 10500 / 10800 seconds. It was 1800 / 11400 / 14100 / 14400. | Design: clock. Same kind of check as before, one message per field. |
| 9 | 421 | 437 | `source.zip` caps: `SOURCE_UNPACKED_CAP` and `SOURCE_FILE_CAP`. They were 2 MiB and 100 files. | Design: raise the caps to 8 MiB and 400 files. |
| 10 | 430–431 | 446–447 | Contract schema name is `cas-optionb-b1-guest-contract/v1`. The contract's `clock_seconds` must equal `CLOCK`. | An old contract can not be taken by mistake. The contract, the guest and the controller must carry one clock. |
| 11 | 433–435 | 449–451 | The source pins are compared with the four stamped constants. The old numbers 192671 and 78 are gone. | Design: source hash, zip size and member count. |
| 12 | 437 | 453–454 | Model files: 7 files and 999,586,347 bytes. It was 17 files and 4,098,559,794 bytes. | Design. Model A is not in this job. |
| 13 | 445–449 | 462–466 | Snapshot roles: only `B`. Its folder name must be revision `7ae557604adf67be50417f59c2c2f167def9a775`. New: every model file must lie inside that folder. | Design: snapshots A and B become B only. |
| 14 | 451–455 | 468–474 | `limits` must equal the table `LIMITS` (5,000 model calls, 100,000,000 archive bytes, and the stage time limits). The flag `mechanical_stage_binding_authorized` is no longer asked for. Instead `external_authority.owner_record` must name one of the authority files. New: the block `precheck` must hold two 64-character hashes. | Design: limits block and archive cap. The old flag gave the guest leave to write stage permits; this guest writes none. The design allowed changing that check. The two hashes are the pre-check binding of decision D7. |
| 15 | 574 | 593 | `PYTHONPATH` for started programs is `work/source/job`. It was the pilot's `src` and `tests`. | The runner and its helper programs sit in `job/`. |
| 16 | 665, 667–715, 717–724 | 684, 686–688, 690–692 | `external_authority` now only hashes the authority files and writes two small records. The pilot's review receipts and permission lines are gone. It returns nothing. | The pilot's reviews do not belong to this job. The guest still never grants acceptance. |
| 17 | 727–771 | 695–697 | `make_admission` removed. New three-line helper `runner`: it builds one command line from the table `RUNNER`. | Pilot science stage removed. |
| 18 | 774–878 | 700–701 | `authored_stage`, `validate_identity_plan`, `validate_pipeline_plan`, `validate_observed_identity` removed. First lines of the new `execute_science`. | Pilot science stages removed. |
| 19 | 882–907 | 705–728 | New `execute_science`, first half: the self-test stage, the file-rule check, the setup clock check. The pilot's 28 tests and identity plans are gone. | Section 4 below. |
| 20 | 909 | 730–731 | The stage text after setup: `SETUP_VERIFIED_BEFORE_MODEL_CALLS`, or `SELFTEST_STOP_NO_MODEL_CALLS` after a self-test stop. | Section 7, reading 1. |
| 21 | 911–936 | 733–761 | New `execute_science`, second half: practice, gate, final, the model hash after the calls, the score stage. | Section 4 below. |
| 22 | 939–970 | 764–777 | `authored_outcome` replaced by `read_result`. | Section 4, item 4. |
| 23 | 999 | 806 | `excluded_model_bytes` is `MODEL_BYTES` (999,586,347). It was the old 4,098,559,794. | Design: the old number would have gone into the new evidence. |
| 24 | 1032 | 839 | The file list inside the archive has the schema name `cas-optionb-b1-required-evidence-inventory/v1`. | The old name carried the old job. The controller reads only the field `members`. |
| 25 | 1035–1036 | 842–845 | Same number as row 23. New field `model_after_calls_receipt`. | Row 23. The new receipt is named in the evidence. |
| 26 | 1071–1072 | 880–881 | The evidence counts as incomplete when a model stage was started and there is no `RESULT.json`. It was tied to a stage named `pipeline`. | Design, item 6. |
| 27 | 1080 | 889 | In `GUEST_RESULT.json`: the key `software_gate_is_not_scientific_qualification` is replaced by `guest_scored_nothing`. | There is no 28-test gate in this job. |
| 28 | 1198 | 1007 | The starting outcome has the reader's three keys. | Row 22. |
| 29 | 1215 | 1024 | `external_authority()` returns nothing now. | Row 16. |
| 30 | 1219 | 1028 | `execute_science()` takes no argument. | Row 16. |
| 31 | 1232 | 1041 | `read_result()` is called. | Row 22. |
| 32 | 1237–1238 | 1046 | If the reader itself fails, the outcome is the fixed text `RESULT_READER_FAILED` with the same three keys. | No copied content can reach the status upload. |
| 33 | 1279–1367 | — | `software_bootstrap` removed. | Pilot science stage (the 28 tests). |
| 34 | 1369–1373 | 1088–1089 | The start of the script no longer knows the argument `--software-bootstrap`. | Row 33. |

## 4. The six things the design asks of `execute_science`

1. **Setup flag.** New lines 728–732. After the self-test stage, and before the first model call, the guest checks the setup clock, sets `SETUP_COMPLETE = True` and forces a progress upload. The controller ends the host at minute 30 unless it has seen that flag.
2. **Deadlines.** New lines 740–742 and 760. The practice, gate and final stages get the work cutoff (minute 135, 8,100 seconds) as their deadline. The same time goes to the runner as `--deadline-unix`, as a whole number of seconds. The score stage must end by minute 140 (8,400 seconds). Its time limit is `score_time_limit_seconds` from `selftest.json`, if that is a whole number from 120 to 240; otherwise 240.
3. **Model hash before scoring.** New lines 746–755. After the last model stage and before the score stage, the unchanged `verify_tree` hashes all 7 model files and writes `work/controller/MODEL_AFTER_CALLS.json`. A failure is recorded and does not skip scoring. The score command gets the paths of this receipt and of `work/controller/MODEL_PRE.json`.
4. **Small result reader.** New lines 764–777. It returns three things only: `status`, `result_sha256`, `result_bytes`. `status` is `outcome_code` from `work/run_b1/RESULT.json` when that is 1 to 80 capital letters and underscores. Anything else becomes the fixed text `RESULT_UNREADABLE`. No file gives `NO_RESULT_FILE`. It never copies a table.
5. **File rules.** The runner is given one output folder, `work/run_b1/`, and the model's snapshot folder inside the payload. The guest does not make the output folder; the runner makes it, as in the pre-check job. New lines 717–723: after the self-test and before any model call, the guest checks that nothing new lies under `work/source/` or `work/external-authority/`, and that every file name under `work/run_b1/` uses only letters, digits, dot, dash and underscore. A break stops the job before a task is spent.
6. **Completeness.** New lines 880–881. See row 26.

**A gate stop is a normal end.** The guest starts all five commands, in the order `selftest`, `run-practice`, `gate`, `run-final`, `score`, every time. Each command exits with 0 after a stop; the stop is written into a file. The package's own commands skip their work after a stop (FILE_FORMATS.md section 16). The guest then hashes, scores, archives and uploads as usual. No failure record is written for a gate stop.

**A crash is different.** If `run-practice`, `gate` or `run-final` exits with an error or runs into its deadline, the guest starts no further model stage. It still hashes the model files and runs `score`. Then it records the failure (`MODEL_STAGE_FAILED_SCORE_STILL_RAN`) and archives and uploads everything.

## 5. What the guest starts

The table `RUNNER` (new lines 70–81) holds the five command lines. A part in curly brackets is filled in by `execute_science` (new lines 707–711).

| Stage name | Command line |
|---|---|
| `selftest` | `selftest --mode gate0 --package-dir <work/source> --model-dir <snapshot> --output-dir <work/run_b1> --expect-prompt-list-sha256 <hash> --expect-padding-plan-sha256 <hash>` |
| `run_practice` | `run-practice --package-dir <work/source> --model-dir <snapshot> --output-dir <work/run_b1> --deadline-unix <work cutoff>` |
| `gate` | `gate --package-dir <work/source> --output-dir <work/run_b1> --deadline-unix <work cutoff>` |
| `run_final` | `run-final --constants <work/source/PLAN_CONSTANTS.json> --prompts-dir <work/source/prompts> --model-dir <snapshot> --output-dir <work/run_b1> --deadline-unix <work cutoff>` |
| `score` | `score --package-dir <work/source> --output-dir <work/run_b1> --model-receipt-before <work/controller/MODEL_PRE.json> --model-receipt-after-calls <work/controller/MODEL_AFTER_CALLS.json>` |

Each is started as `<overlay python> -B work/source/job/runner_b1.py <command line>`.

- `--mode`, `--deadline-unix` and the two `--expect-…` names are fixed by FILE_FORMATS.md section 16.
- `--package-dir`, `--model-dir` and `--output-dir` are the names the pre-check job uses (`precheck_cpu/precheck_supervisor.py`, constant `SELFTEST_ARGV`). So the GPU job uses the spelling the pre-check has already run.
- `--constants`, `--prompts-dir`, `--model-receipt-before` and `--model-receipt-after-calls` are names FILE_FORMATS.md does not fix. They were taken from `optionb/job/runner_b1.py` as it stood on 2026-10-05 (70,307 bytes, sha256 `29197ad60a8443c17a3e9bf923dd734d5a1ff37fb7242613a1b4d6bb0879941e`). REAL: every fixed word of the five lines occurs in that file as a whole quoted word. The runner was read, not run. It may still change before seal step 6.
- Review round 1 changed the runner (another builder's file). REAL, counted again on 2026-10-05 on the runner as it then stood (70,753 bytes, sha256 `ca7e49d0b47f5d8f0bf52d248beb152e8a1f0ecad017e9e7ccb0366dd0474a30`): all 28 fixed words of the five lines still occur in it as whole quoted words. Other fixers were still at work on that file, so this count is for that moment only. Check X8 repeats it on the sealed package.
- `run-final` is not given the package folder and not given a key folder.
- Stage time limits: `selftest` 900 seconds, `gate` 300 seconds, `run_practice` and `run_final` up to the work cutoff. These are in `LIMITS` and in the contract.

`text_check_b1.py` (check X8) refuses the build unless every fixed word of these five lines occurs, as a whole quoted word, in `job/runner_b1.py` inside the sealed `source.zip`.

## 6. The stamp

Four constants can not be known before `source.zip` exists: its sha256, its size, its member count, and the sha256 of `BUNDLE_MANIFEST.json`. The draft holds placeholders. The two placeholder hashes are the sha256 of the texts `UNSTAMPED:SOURCE_ZIP_SHA` and `UNSTAMPED:SOURCE_SEAL`. With placeholders the guest refuses every package.

`build_contract_b1.py --stamp-only` (or `--stamp-guest`) replaces exactly those four lines (new lines 53–56). It refuses a guest that is already stamped with other values. It checks both size limits again before it writes. `text_check_b1.py` fails while a placeholder is left.

The reviewer should read the stamped file once more: it must differ from the reviewed draft in those four lines only.

After a program repair (a seal line `6R_PROGRAMS_REPAIRED`, plan section 11.1) there is a new `source.zip`, so the four pins change. The stamp tool does not restamp a stamped guest. Start again from the reviewed, unstamped draft and stamp it for the new `source.zip`. The result must again differ from the reviewed draft in those four lines only.

## 7. Readings chosen where the plan was silent

Each is reported to the operator as an open point.

1. **Setup flag after a self-test stop.** The design says the flag is set after the self-test passes. This guest also sets it when the self-test ends with a stop code (for example `GATE_STOP_PADDING`). Reason: the task rule that a gate stop must still be archived and uploaded. Without the flag the controller would end the host at minute 30, possibly in the middle of the upload. The stage text then reads `SELFTEST_STOP_NO_MODEL_CALLS`. If the self-test crashes, or `selftest.json` can not be read, the flag is not set and no model stage starts.
2. **Exact deadline.** The runner and the guest hold the same second for the work cutoff, as the design says. If the runner is still writing at that second, the guest ends it and records `STAGE_TIMEOUT`. Scoring still runs. The runner should therefore stop a few seconds early.
3. **Authority check.** The old flag check was changed, not kept (row 14).
4. **Early file-rule check** (section 4, item 5) is an addition. It costs no task. It can only stop the job before the first model call.
5. **Work folder cap of 80,000,000 bytes.** If the work folder grows past it, the running stage is ended and only the small controller folder is sent back. EXPECTED size at the ceiling of 4,552 calls: about 36 MB. REAL from the old job: everything outside the pilot's own output was under 3 MB.
6. **No pre-check mode.** The pre-check job has its own supervisor (`precheck_cpu/`). This guest serves the GPU job only.

## 8. What the guest needs from the other files

- **`CONTRACT.json`** (written by `build_contract_b1.py`): `schema`, `job`, `clock_seconds`, `source` (`zip_sha256`, `zip_bytes`, `manifest_sha256`, `members`), `model_cache` (`files`, `snapshots.B`), `runtime` (the sealed block, copied from the old contract), `limits`, `precheck` (`prompt_list_sha256`, `padding_plan_sha256`), `external_authority` (`files`, `owner_record`).
- **`input.zip`** (written by `build_input_zip_b1.py`): exactly `CONTRACT.json`, `source.zip`, `authority/<each authority file>`, `models/<each of the 7 model files>`.
- **`source.zip`** (written by `build_source_zip_b1.py`): the 16 package files of FILE_FORMATS.md section 14, among them `tools/verdict.py` since review round 1, plus `contracts/requirements.small-linux.txt` and `BUNDLE_MANIFEST.json`. That is 18 members.
- **The controller**: the clock 1800 / 8100 / 10500 / 10800, 269 part links of 64 MiB, the output key `pointer-saturation-deliverable.zip`, the unit name `helm-op11-work`, the launch line `/opt/pytorch/bin/python -B /opt/helm-op11-worker/worker_v02.py`. REAL on 2026-10-05: `text_check_b1.py` checks A2, A3 and X7 passed on the controller draft in this folder.

## 9. How to repeat the comparison

Small, standard library only, reads two files:

```
/c/Python314/python.exe -B -c "import difflib,sys;a=open(sys.argv[1],encoding='utf-8').read().splitlines();b=open(sys.argv[2],encoding='utf-8').read().splitlines();[print(t,i1+1,i2,j1+1,j2) for t,i1,i2,j1,j2 in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if t!='equal']" D:/tksCAS-runs/controller_cas_small_op11_claude_c1/worker_v02.py worker_v02.py
```

Each printed line is: kind, first old line, last old line, first new line, last new line.

## 10. What was not checked

- The guest was never executed. It was read, parsed and measured.
- The three builders were never executed. They were parsed only.
- `text_check_b1.py` was run once on this draft folder (REAL, 2026-10-05, before review round 1). It read files only. Its checks A1, A2, A3, E1, X1, X3 and X7 passed. Its other ten checks failed because `source.zip`, `CONTRACT.json` and `input.zip` do not exist yet. Those ten code paths have not run on real files.
- After review round 1 `text_check_b1.py`, `aws_control.py` and `controller_common.py` are other bytes, and `text_check_b1.py` was not run again. REAL instead: a separate counting script replayed the patterns of checks A2, A3 and X7 on the changed files, and all of them held.
- Whether the runner really accepts the five command lines was checked by words only (section 5). The runner has a switch `--check-args-only` that reads the arguments and does nothing else. Nobody has run it. The laptop may not run the runner.
- The pre-check job runs `selftest` in mode `precheck`. It does not run the guest and it does not run mode `gate0`, `run-practice`, `gate`, `run-final` or `score`. So the guest's own path, and four of the five commands, run for the first time in the GPU job.

## 11. Review round 1: what changed beside the guest

The guest itself did not change. Three files that build or check its package did. None of them was run. Each parses (`ast.parse`). Line numbers are those of the files after the fixes (REAL, compared with the first draft by `difflib`).

This section is the record of review round 1. Amendment A5 changed one rule of it afterwards: a tool-repair line can no longer follow step 7. Section 12 has that change.

**`build_source_zip_b1.py` (was 275 lines, now 321).**

| Lines | What changed | Why |
|---|---|---|
| 57, 70 to 72 | `tools/verdict.py` is in the list of package files. The list of "optional" files is gone. | The review found that three views the plan says are always printed need `content()` from `tools/verdict.py`, and the file was not in the package. It is now one of the 16 package files (FILE_FORMATS.md section 14). A seal that does not give it the package path `tools/verdict.py` stops the build. |
| 83 to 85, 176 to 189 | The two repair lines are known. Leave them out; what is left must be steps 1 to 6 in order, each once, then at most one step 7 line. A line `6R_PROGRAMS_REPAIRED` must stand after step 6 and before step 7, at most twice. | The review found no path after a failed pre-check. The plan now has one (sections 11.1 and 19.1). Before this change the build refused every seal file that held a repair line. |
| 198 to 199 | The seal copy in the package ends at step 6, or at the last line `6R_PROGRAMS_REPAIRED`. | FILE_FORMATS.md section 14. The same rule gives the same bytes every time, so the pre-check job and the GPU job share one package. |
| 201 to 220 | The hash in force: where two seal lines list one path, the later line counts. Only a repair line may give a path other bytes. A repair line may not move a file inside the package. | FILE_FORMATS.md section 15.2. After a repair the package holds the repaired file. |
| 155 to 157, 170 to 173, 190 to 197 | New option `--seal`. It names a scratch copy of the seal file for a rehearsal. The scratch copy must be the real seal file plus exactly one line, a step 6 line. | Plan section 19.1: a rehearsal after seal step 5 and before seal step 6. |
| 245, 305 to 308 | The bundle manifest names the real last step of the seal copy. The build receipt says which seal file was read, whether it is a rehearsal package, and how many repair lines are in the package. | So the record shows what kind of package it is. With no repair line the manifest has the same bytes as before. |

A new `source.zip` after a repair goes into a new folder. The script refuses to overwrite a `source.zip` with other bytes. The old one is evidence of the failed pre-check.

**`build_contract_b1.py` (was 370 lines, now 379).** Lines 168 to 179, in `precheck_binding`.

- After the line `7_PRECHECK` only lines `TR_TOOLS_REPAIRED` may follow. Before, step 7 had to be the last line.
- The seal copy in the package must end at the last program line of the seal file. A package built before a repair line is stale and gets no contract. Stop name: `PACKAGE_SEAL_COPY_DOES_NOT_END_AT_THE_LAST_PROGRAM_LINE`.
- Unchanged: the seal copy must be the start of the real seal file. So a rehearsal package never gets a GPU contract.

**`text_check_b1.py` (was 619 lines, now 635).**

| Lines | Check | What changed |
|---|---|---|
| 53 to 56 | | Three new constants: the program lines, the tool-repair line, the name `tools/verdict.py`. |
| 475 to 487 | X5 | The seal copy may end with step 6 or with a line `6R_PROGRAMS_REPAIRED`. No program line may follow it in the seal file. The package is compared with the hash in force. |
| 494 to 499 | X5 | `tools/verdict.py` must be in `source.zip` with the size and sha256 pinned in `PLAN_CONSTANTS.json`. |
| 506 to 510 | X6 | Step 7 must stand exactly once. After it only tool-repair lines may follow. |

**`build_input_zip_b1.py`:** not changed.

**Sizes of the guest after these fixes (REAL, measured 2026-10-05 with `/c/Python314/python.exe`, the same way as in section 1).**

| Number | Limit | Guest |
|---|---:|---:|
| Raw bytes | 73,986 | 56,033 |
| Packed bytes (gzip with `mtime=0`, then base64) | 28,420 | 22,124 |
| Room left for the packed signed links | — | 21,492 |

They equal the numbers of section 1, because no byte of the guest changed.

## 12. Amendments of 2026-10-05 (A5 and A10): what changed beside the guest

The guest itself did not change. The three files below did. None of them was run. Each parses (`ast.parse`, REAL). Line numbers in this section are those of the files after the amendments (REAL, found by text search). The line numbers in section 11 are those of the files as they stood after review round 1; in `build_source_zip_b1.py` and `text_check_b1.py` the later lines have moved down since.

**`build_source_zip_b1.py` (was 321 lines, now 338).**

| Lines | What changed | Why |
|---|---|---|
| 35 to 41 | Docstring: the development-test use of `--study-root`, and the window of a tool-repair line. | A10, A5 |
| 94 to 95, 200 to 204 | A tool-repair line must stand after line 1 and before the line `3C_FINAL_QUESTIONS_AND_KEYS`. Stop name: `TOOL_REPAIR_LINE_OUTSIDE_ITS_WINDOW_FILE_FORMATS_15_2`. | A5: a tool repair is allowed only while no final question exists. The seal tool can not write such a line later, so a seal file that holds one is refused. |
| 322 to 323 | The build receipt has one more field: `made_up_study_root_never_for_a_seal_or_the_gpu_job`. It is true when `--study-root` named another folder than the study folder. | A10: the development-test package is built from a made-up study folder. The record now says so. |

The option `--study-root` is not new. A development-test package needs no other change here: the script reads the made-up seal file of that folder and applies the same rules to it.

**`build_contract_b1.py` (379 lines, as before).** Lines 170 to 173, in `precheck_binding`.

- The line `7_PRECHECK` must be the last line of the seal file. Review round 1 had allowed tool-repair lines after it. Under A5 none can stand there.
- For a development-test package only the mode `--stamp-only` can run. It stamps a copy of the guest and checks the two size limits. It writes no contract: a contract needs seal step 7 of the real seal file.

**`text_check_b1.py` (was 635 lines, now 641).**

| Lines | Check | What changed |
|---|---|---|
| 56 to 57 | | One new constant: the line `3C_FINAL_QUESTIONS_AND_KEYS`. |
| 510 to 516 | X6 | Step 7 must stand exactly once, as the last line of the seal file. A tool-repair line must stand after line 1 and before the line 3C. |

**`build_input_zip_b1.py`:** not changed.

**Sizes of the guest after the amendments (REAL, measured 2026-10-05 with `/c/Python314/python.exe` 3.14.0, the same way as in section 1).**

| Number | Limit | Guest |
|---|---:|---:|
| Raw bytes | 73,986 | 56,033 |
| Packed bytes (gzip with `mtime=0`, then base64) | 28,420 | 22,124 |
| Room left for the packed signed links | — | 21,492 |

sha256 `26eac561681c87fb57b7c43788530a7e12847246d056f4fb9fb3f176751c12d1`. They equal the numbers of section 1, because no byte of the guest changed.
