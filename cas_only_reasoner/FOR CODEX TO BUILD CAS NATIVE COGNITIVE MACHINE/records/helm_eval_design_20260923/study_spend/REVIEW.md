# Review of `bb942461` (study-spend gate and T4 route reader): findings and dispositions

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Builder: Claude (temporary builder). Reviewer: a Claude reviewer sub-agent.
Reviewer verdict on `bb942461`: **CHANGES_REQUIRED**. It got the admission gate to admit wrongly in 4 ways, and got
the route reader to accept results that did not come from the launched machine, with exit 0. It found the reader
correctly refused a mismatched `identity.json` and a watch record from another job, and found no way to get exit 0
without `ROUTE_ACCEPTED`.

This record is the builder's own. It is **not** an independent acceptance: the fixes below still need Codex's review.

## Summary

| # | Severity | Finding (short) | Disposition |
|---|---|---|---|
| 1 | MAJOR | One receipt can be claimed by two slots; nothing ties a slot to the job it launched | **FIXED** (limits stated below) |
| 2 | MAJOR | An AWS capacity refusal counts as a started training job for the $30 stop | **FIXED** |
| 3 | MAJOR | The owner's numbers and the slot list come from a file the runner edits | **FIXED** |
| 4 | MAJOR | A rejected or INVALID receipt counts at its cap even when it recorded more | **FIXED** |
| 5 | MAJOR | The route reader never checks the results came from the launched machine | **FIXED** (limit stated below) |
| 6 | MINOR | The reader never checks the launch record against the reviewed bundle and commit | **FIXED** |
| 7 | MINOR | Docs allow a cheaper machine; code rejects it | **FIXED** |
| 8 | MINOR | `--admit` leaves no record and does not set RUNNING | **FIXED** |
| 9 | MINOR | Training slots list no preconditions | **FIXED** |
| 10 | NOTE | Other AWS jobs in the design folder are not in the slot list | **FLAGGED** (open question 1) |
| 11 | NOTE | Spend versus bookings: which count the $60 applies to | **FLAGGED** (open question 2) |
| 12 | NOTE | Which job is "the third seed" | **FLAGGED** (open question 3) |
| 13 | NOTE | (a) S1 rule acceptance; (b) Windows paths; (c) JSON lists crash the reader; (d) 12-month retention | (a) **FLAGGED** (open question 4); (b), (c) **FIXED**; (d) **STATED** (open question 5) |

## The findings, as the reviewer gave them, and what was done

### 1. MAJOR — one receipt can be claimed by two slots (`study_spend.py`)

**Reviewer.** The gate never checked that a receipt, job id or instance id was used by only one slot. The expected
identity was written after the job ended, so nothing tied a slot to the job it launched. Scenario: mark M1 DONE with
an exact copy of S2's receipt spec. M1 was ACCEPTED at $3.29 and counted as a started training job; `--admit M2`
then exited 0 (spent $8.73, total $48.71).

**Done.**
- Every identity a RUNNING, DONE or INVALID slot claims is collected: receipt sha256 and path, job id, instance id,
  provider record sha256 and path, launch and watch record sha256 and path, and the job and instance ids inside the
  receipt files themselves. If two slots share one, **both** receipts are rejected (`RECEIPT_SHARED:...`), both count
  at least their cap, and every admission is refused (`RECEIPT_SHARED`). The report exits 1.
- `--admit` now records, before launch, what the slot will carry: the source commit (`--source`), the bundle sha256
  for watched slots (`--bundle`), and the model seed and arm for training slots (frozen per slot:
  M1 20260917 UNCHANGED, M2 20260917 REPAIRED, M3 20260918 REPAIRED, M4 20260919 REPAIRED, M5 20260918 UNCHANGED,
  M6 20260919 UNCHANGED). At DONE the receipt must show the admitted source (and bundle), the slot's seed
  (`authority.worker_config.design.model_seed`), and a launch time **after** the admission time (the time inside the
  job id, or the launch record's `launched_utc`). A DONE slot with no admission record is rejected.
- One source per arm: all admissions of one arm must use one source commit, and the two arms may never share one
  (`ARM_SOURCE_CONFLICT`). The receipt has no "arm" field, so the arm is bound through the source commit.

**Limit, stated honestly.** The job id and instance id do not exist until the launcher runs, so they cannot be
recorded at admission. The binding is: admitted source (and bundle) and seed, launch after admission, and no identity
shared with any other slot. A receipt forged with a fresh job id, a fresh instance id and the right source and seed
would still need to sit at a pinned git commit with a matching sha256; this program cannot detect such a forgery on
its own.

**Tests.** `test_a_copied_training_receipt_is_refused_for_both_slots` (the reviewer's exact scenario: M1 and S2
REJECTED, `--admit M2` exit 1), `test_copied_watched_records_are_refused_for_both_slots`,
`test_a_done_receipt_must_match_its_admission` (no admission, launch before admission, wrong seed, wrong source,
wrong bundle, watched launch before admission, and the accepted case), `test_one_source_per_training_arm`,
`test_admitted_job_end_to_end`.

### 2. MAJOR — a capacity refusal counts as a started training job (`study_spend.py`)

**Reviewer.** With M1-M3 DONE as capacity refusals ($1.60 each) and two retry seeds at $9.98 each, spent was $30.20
and `--admit R3` exited 0 with "5 of 3 training jobs started". Without the refusals counted, the same state gives
OWNER_STOP_TRIGGERED.

**Done.** A training job counts as **started** only when it is RUNNING, or DONE with an **accepted**
`pointer_finished` receipt. A capacity refusal, a rejected receipt and an INVALID slot never count.

**Tests.** `test_capacity_refusals_never_count_as_started` (the reviewer's exact scenario: spent $30.20, started
R1 and R2 only, `--admit R3` refused with OWNER_STOP_TRIGGERED "2 of 3", not over the ceiling at $58.52),
`test_rejected_or_invalid_training_never_counts_as_started`.

### 3. MAJOR — the owner's numbers and the slot list come from an editable file (`study_spend.py`)

**Reviewer.** Ceiling, stop amount, stop count, allowance, slot set, caps and flags all came from
`STUDY_SLOTS.json`. Changing the ceiling to "90.00" admitted P1b; deleting the DONE S1 row admitted P1b at $58.48;
flag and stop-number changes were accepted silently.

**Done.**
- `$60.00`, `$30.00`, `3` and `$0.10` are hard-coded. The file must carry the same values or the program exits 2
  (`FROZEN_CONSTANT_CHANGED`).
- The slot definitions are frozen by a digest in the code (`FROZEN_DEFINITIONS_SHA256`
  `82e809500f14ad8988b3b45ad6a7265f0601a5791f13cb8ea5a4608771456764`). It covers the whole file except, for slots
  other than S1, S2 and P1a, the four mutable fields `status`, `receipt`, `invalid_reason` and `admission`. S1, S2
  and P1a (done before the gate existed) are frozen whole. Any other change exits 2 (`SLOT_DEFINITIONS_CHANGED`) until
  a reviewed code change re-freezes the digest. This is stricter than "match HEAD", because a committed edit is caught
  too.
- Forward-only moves are checked against **every committed version** of the file (not only HEAD): a committed RUNNING
  row keeps its admission; a committed DONE row keeps its receipt and admission and may only become INVALID; a
  committed INVALID row never changes; no such row may disappear (`HISTORY_VIOLATION`, exit 2).
- `--admit` is refused while `STUDY_SLOTS.json` or `study_spend.py` differs from HEAD (`UNCOMMITTED_CHANGES`). So every
  DONE receipt is in git history before the next machine starts, and the gate only runs committed code.

**Limit.** A history rewrite (force-push) is outside this check. Before a DONE row is committed its pins can still be
edited; that is deliberate (the runner fixes wrong pins before committing), and the admission refusal above means it
must be committed before anything else is admitted.

**Tests.** `test_frozen_constants_and_definitions_cannot_change` (ceiling 90.00, stop $40.00, stop number 4,
allowance $0.05, S1 deleted, M4 mandatory false, M4 stop flag false, E1 cap changed, P1a pin changed, M1 seed changed:
each exit 2), `test_history_is_forward_only`, `test_admission_needs_committed_slots_and_program`.

### 4. MAJOR — "rejected counts at its full cap" is not an upper bound (`study_spend.py`)

**Reviewer.** P1b DONE with a 240-minute deadline and a watcher cost of $3.0719 was REJECTED and counted at its
$2.00 cap, below the recorded $3.07. Marking it INVALID kept $2.00 and let `--admit P2` pass (spent $9.89, total
$59.53). A too-high elapsed or price in a training receipt behaved the same way.

**Done.** A rejected DONE receipt, and any INVALID slot with a receipt, now counts **the larger of** the cap and every
cost figure the receipt shows: the recorded cost plus allowances, the cost recomputed from its timestamps, and the cost
at its own deadline or instance-seconds limit, each at the highest price or rate the receipt or the basis shows. The
figure is kept after INVALID. A receipt file whose hash does not match is still read for these figures (it can only
raise the count, never lower it). New: elapsed seconds above the basis are a rejection (`ELAPSED_OVER_BASIS`).

In addition, a readable receipt that shows an **unconfirmed cleanup** (a machine or disk may still exist, or a
capacity-refusal claim that failed its proof) refuses every admission, even after INVALID
(`CLEANUP_UNCONFIRMED_STOP_AND_REPORT`): the money then has no upper bound, so the runner must stop and report to the
owner. No mechanism clears this; that is an owner decision.

**What this does and does not change.** In the reviewer's P1b scenario the slot now counts **$3.18** (not $2.00), and
spent is $8.62 (not $7.44). With that correct count, `--admit P2` totals $58.26 and is admitted: the fix makes the
money right; it does not by itself stop the study after a cost-basis breach. The reviewer offered "or treat any basis
breach as a stop"; only unconfirmed cleanup is a stop here. Whether every basis breach should stop the study is left
to Codex or the owner.

**Tests.** `test_watched_basis_breach_counts_the_recorded_cost_even_after_invalid` (the reviewer's P1b scenario:
$3.18 DONE and INVALID, spent $8.62), `test_training_basis_breach_counts_the_recorded_elapsed_even_after_invalid`
(20,000 s: $15.58 DONE and INVALID), `test_unconfirmed_cleanup_blocks_admission_even_after_invalid`.

### 5. MAJOR — the route reader never checks the results came from the launched machine (`read_results.py`)

**Reviewer.** Every machine check (identity.json, the env.txt bundle line, wheel hashes, "bundle.tar.gz: OK") is the
same for any run of the same bundle, and the reader ignored the watch record's download facts. A watch record saying
MACHINE_ENDED_WITHOUT_RESULTS (or CLIENT_DEADLINE_TERMINATED), job_status null, files_downloaded 0 still gave
ROUTE_ACCEPTED, exit 0; so did "JOB START 2026-09-01T00:00:00Z". Realistic path: `watch.py` never clears `results/`
and ignores download errors, so a re-run whose download fails leaves the old run's results.

**Done.** Route acceptance now also requires:
- the watch outcome is exactly `RESULTS_RECEIVED`;
- `files_downloaded` is an integer above 0;
- the watch `job_status` equals `results/STATUS`;
- job.log has exactly one `JOB START <utc>` line, and that time lies between the launch record's `launched_utc` and
  the watch record's `watch_ended_utc` (the real job: 05:55:04Z inside 05:53:38Z to 06:28:42Z);
- if `env.txt` has an `instance_id=` line (from IMDSv2), it equals the launched instance. A template without that line
  is accepted only if it is the finished job's own template (`dc05f4af...`, which predates the line); the reading then
  says `NOT_WRITTEN` and that the binding rests on the time window and the watch record.

**Limit.** For the finished job, the binding is the time window plus the watch record, not the machine's own instance
id: its template did not write one, and the template is not changed (its sha256 is recorded in the launch record). Any
later template must write `instance_id=` or the reader refuses. `watch.py` itself is unchanged (it still does not
clear `results/` or fail on a download error); the reader now catches both consequences.

**Tests.** `test_watch_outcome_other_than_results_received_is_refused`, `test_watch_job_status_must_equal_results_status`,
`test_watch_must_have_downloaded_files`, `test_job_start_must_lie_inside_this_launch` (2026-09-01, 1 s before launch,
1 s after watch end, an impossible date, missing, repeated), `test_old_results_left_in_the_folder_by_a_later_launch_are_refused`,
`test_machine_instance_id_line_binds_to_the_launched_instance`. Each ends in ROUTE_NOT_ACCEPTED with exit 3.

### 6. MINOR — the reader never checks the launch record against the reviewed pair

**Done.** The reviewed bundle sha256 (`2410f269a46d0a8024c7709976557aa1734b7e577cc6cfdb9e9909c53393bd36`) and source
commit (`e05889eec0f800a9a17b0c39a8d8d37f544b43bf`) are pinned in the reader (from the reviewed dry run, admitted by
review `fb6bc4dd`), with `--expect-bundle` / `--expect-source` to override. The launch record must equal them, and
`dry_run_record.json`, when present, must agree. Tests: `test_a_self_consistent_but_unreviewed_launch_is_refused` (the
reviewer's `'d'*64` case), `test_dry_run_record_must_agree_when_present`, `test_main_strict_exit_codes_pins_and_no_write`.

### 7. MINOR — docs allow a cheaper machine; code rejects it

**Done.** A watched basis now lists its allowed machines, each with its own price; the cap check uses the dearest; a
receipt must use a listed machine at **that machine's** price. P1b and E1 list g4dn.2xlarge $0.752 and g4dn.xlarge
$0.526 (from `larger_question_t4_job/launch.py` PRICES). P2 lists only c7i.2xlarge $0.357; its "or cheaper" wording is
removed, because no cheaper price is on record. Test: `test_a_cheaper_listed_machine_is_checked_at_its_own_price`.

### 8. MINOR — `--admit` leaves no record and does not set RUNNING

**Done.** On ADMIT, `--admit` writes the slot as RUNNING with its admission record in one atomic write (checked:
the file did not change during the decision; the definitions digest is unchanged afterwards). A second `--admit`
is then refused (`ONE_MACHINE_AT_A_TIME`, and `UNCOMMITTED_CHANGES` until committed). An optional slot that ran
without `--admit` is still invisible to the gate; that cannot be prevented from inside a file. Test:
`test_admit_pass_case_writes_running_and_its_record`.

### 9. MINOR — training slots list no preconditions

**Done.** M1-M6 now list preconditions (the reviewed source for the arm; M1 admitted first for M2-M4; P1b passed; E1
built and reviewed; fallback B chosen by the owner for M5-M6), marked as from the plan text and this review, for Codex
or the owner to confirm. A slot with no list prints `NOT ASSESSED ...` instead of `[]`. The money gate still does not
check them. Test: `test_missing_preconditions_print_not_assessed`.

### 10-13. NOTES

- **10, 11, 12** are recorded as open questions 1-3 in `STUDY_SLOTS.json` (printed with every decision) and in
  `PREREQUISITE_SLOTS.md`. The builder does not decide them. For 10, the five watcher figures were re-read from their
  own `watch_record.json` files and match the reviewer's total of $1.9180.
- **13(a)** The S1 capacity-refusal rule is now labelled `CLAUDE_PROPOSED` in its printed override and is open
  question 4. It stays load-bearing: without it plan C is $67.14 and does not fit.
- **13(b)** Receipt paths are rejected if they contain a drive letter, a backslash, `..` or a leading `/`, and the
  resolved path must stay inside the design folder. Test: `test_receipt_paths_outside_the_design_folder_rejected`.
- **13(c)** The reader names any JSON file that is not a JSON object instead of crashing: a result file makes the job
  verdict RESULT_INTEGRITY_FAILED (exit 1); the launch, watch or dry-run record makes the route not accepted (exit 3).
  It still writes `RESULTS_READING.json`. Test: `test_json_lists_fail_by_name_without_crashing`.
- **13(d)** The 12-month limit is written next to the allowance in `STUDY_SLOTS.json` and is open question 5.

## Checks run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `python -B test_study_spend.py` | 40 passed, 0 failed |
| `python -B test_read_results.py` | 29 passed, 0 failed |
| `python -B study_spend.py` (real slots, report mode) | exit 0; spent upper bound $5.44; plan C $57.08, headroom $2.92; fallback B +$23.32 does not fit; no rejected or shared receipt; no unconfirmed cleanup; the history check passed against the committed `bb942461` version |
| `python -B read_results.py` (the finished job `i-09e14d4afd0e0ebfa`) | exit 0; script verdict and job verdict INTEGRATION_CHECKS_PASS; ROUTE_ACCEPTED; JOB START 05:55:04Z inside the window; instance id NOT_WRITTEN (template `dc05f4af`) |
| Real `--admit` | **Not run.** It now writes the slot as RUNNING, which would announce a launch |

The finished job's `results/`, `launch_record.json`, `watch_record.json` and `dry_run_record.json` are unchanged.
Only its reading, `RESULTS_READING.json`, was rewritten by the new reader. The meta1 ledger was not read or written.
