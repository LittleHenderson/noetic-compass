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

## Verification of d89721b4ddef5a3e8da1641b6e6f133c155aef6a

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Verifier: a fresh Claude verifier sub-agent. It did not build the fixes. This is
**not** Codex's review and **not** owner acceptance.

**Verdict: CHANGES_REQUIRED.**

In short: four of the five MAJOR findings are fixed. MAJOR 4 is fixed only for the reviewer's exact case. Leave one
field of a receipt spec empty, or pin a receipt with a stale hash, and the gate stops reading that receipt. It then
counts only the cap and skips the cleanup check. Mark the slot INVALID and the gate admits the next machine. In one
probe it admits at $57.08. Its own correct figure for the same state is $61.00, over the $60.00 ceiling, and a machine
may still be running.

### What was run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `python -B test_study_spend.py` | 40 passed, 0 failed |
| `python -B test_read_results.py` | 29 passed, 0 failed |
| `python -B study_spend.py --no-write` (real slots) | exit 0; spent upper bound $5.44; plan C $57.08; headroom $2.92; fallback B +$23.32 does not fit; nothing rejected, shared or unconfirmed |
| State regenerated into a scratch file | byte-identical to the committed `STUDY_SPEND_STATE.json` |
| `python -B read_results.py --no-write` (finished job `i-09e14d4afd0e0ebfa`) | exit 0; script verdict and job verdict INTEGRATION_CHECKS_PASS; ROUTE_ACCEPTED; JOB START 2026-09-24T05:55:04Z inside [05:53:38Z, 06:28:42Z] |
| Reading regenerated into a scratch file | byte-identical to the committed `RESULTS_READING.json` |
| Finished job's records | `results/`, `launch_record.json`, `watch_record.json` (17 tracked files): git diff since `b0fd06ff` is empty |
| Probes P1-P7 | a scratch script built on the builder's own test helpers (`World`, `FakeGit`); results below; not committed |
| Real `--admit` | **not run** (it writes the slot RUNNING) |

### The five MAJOR findings

| # | Finding | Verdict | Evidence |
|---|---|---|---|
| 1 | One receipt claimed by two slots | **FIXED** (residual MINOR A) | The reviewer's exact copy case: M1 and S2 both REJECTED, `--admit M2` exit 1 (test). Sharing is checked on receipt sha256 and path, job id, instance id, provider / launch / watch record sha256 and path, and the ids read from the files. At DONE the seed, the admitted source (and bundle) and "launch after admission" are checked. |
| 2 | A capacity refusal counts as a started training job | **FIXED** (NOTE C) | Started = RUNNING, or DONE with an ACCEPTED `pointer_finished` receipt (lines 849-851). The reviewer's case: started R1, R2 only; `--admit R3` exit 1, OWNER_STOP_TRIGGERED "2 of 3". |
| 3 | The owner's numbers and the slot list come from an editable file | **FIXED** | $60.00, $30.00, 3 and $0.10 are in the code. The definitions digest `82e80950...` matches the real file. Ceiling 90.00, S1 deleted, M4 flags, E1 cap, a seed change: each exit 2 (test). Forward-only moves are checked against every committed version. `--admit` is refused while the slots file or the program differs from HEAD. |
| 4 | A breached receipt is undercounted after INVALID | **NOT FULLY FIXED**: new MAJOR B | The reviewer's case now counts $3.18 (test). Neighbouring paths still fail open (probes P1-P4). |
| 5 | The reader never binds results to the launched machine | **FIXED** (residual MINOR D) | Watch outcome RESULTS_RECEIVED, files_downloaded > 0, watch job_status equal to `results/STATUS`, exactly one JOB START inside the launch window, and the `instance_id=` line when written. Each has a failing test that ends in exit 3. |

### Remaining findings

**B. MAJOR: the MAJOR 4 fix stops at an incomplete spec or a stale pin** (`study_spend.py` lines 568-582, 598-607,
689-706).

What happens:
- `validate_pointer` and `validate_watched` return at `RECEIPT_SPEC_INCOMPLETE` before they read the receipt. So
  there are no cost figures and no cleanup check.
- `cleanup_unconfirmed` is computed only from a receipt that passed its hash check. The lenient read of a stale receipt
  feeds the cost figures only.
- The default is "cleanup confirmed". An INVALID slot does not block. So the gate reopens.

Probes (each on the builder's own synthetic `World`):
- **P1.** P1b ran 240 min with a watcher cost of $3.0719. `expected.bundle_sha256` left empty. Marked INVALID. Counted
  $2.00, not $3.18. `--admit P2` exit 0, ADMIT.
- **P2.** P1b's watch record says `terminated_confirmed: false`, `final_state: running`. Same empty field. INVALID. No
  cleanup flag. `--admit P2` exit 0, ADMIT.
- **P3.** The same unconfirmed cleanup with a complete spec, but a stale watch-record pin. INVALID. No cleanup flag.
  `--admit P2` exit 0, ADMIT.
- **P4.** M1 ran 20,000 s. Its cleanup says `complete: false`, `compute_identity_uncertain: true`, instance
  `UNKNOWN`. `expected.instance_id` left empty, which is the natural entry when the identity is uncertain. INVALID.
  Counted $11.66. No cleanup flag. `--admit P1b` exit 0, ADMIT, total $57.08.
- **P5 (control).** P4 with a complete spec: counted $15.58; `--admit P1b` exit 1 with
  `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` and `OVER_CEILING:$61.00 > $60.00`.

Why it matters: P4 is the very case the fix exists for. The identity is uncertain, a machine may still exist, and the
money is over the ceiling. One empty field turns the refusal into ADMIT. A committed DONE receipt is frozen by the
history rule, so a spec committed incomplete can never be corrected. INVALID is then the only way on, and INVALID
reopens admission.

Fix: do the lenient read (cost figures, ids, cleanup) before any spec-completeness return, from whatever commit and
path the spec gives. Compute cleanup from the lenient document too. Fail closed: when a REJECTED or INVALID slot names
a receipt that cannot be read, or that does not positively show confirmed termination (and is not a proven capacity
refusal), mark its cleanup UNCONFIRMED. Add P1-P4 as negative tests.

**A. MINOR: a hand-written admission record is accepted** (`study_spend.py` lines 474-498). `bind_admission` checks
only the slot name, the time, the source, the bundle, the seed and the arm. It does not check that `--admit` wrote the
record, or that the RUNNING row was ever committed. Probe **P6**: M1 DONE with a hand-written admission dated
2000-01-01 and no `--admit` run: ACCEPTED, counted $8.94. So "launch after admission" is only as strong as the runner's
care. Fix: at DONE, require that a committed version of `STUDY_SLOTS.json` shows the slot RUNNING with the identical
admission record.

**C. NOTE: a training job that launched and then failed counts as started.** Probe **P7**: M1-M3 each launched and
failed after 60 s (status `AWS_CANDIDATE_FAILED`, cleanup confirmed). All three count as started; spent $10.33; the
$30.00 stop is then off for the rest of the study. This follows the stated rule. "Which job is the third seed" is
already open question 3. Codex or the owner should rule on whether a failed seed counts.

**D. MINOR: the reader's template exemption covers every future launch** (`read_results.py` lines 54 and 137-139). The
exemption is keyed on template sha256 `dc05f4af...`. That is also the CURRENT `job.sh.template` (sha256 checked; it
writes no `instance_id=` line). So any later launch from this folder is exempt, not only `i-09e14d4afd0e0ebfa`. The
dispositions above say "any later template must write `instance_id=`", but no later template exists. The time window
and the watch record still catch stale results, so this is not a wrongful accept today. Fix: key the exemption to the
instance id `i-09e14d4afd0e0ebfa` as well as the template, or change the template (a job-code change that needs its
own review) before the next launch.

### Claim states

- **Real (measured here):** the two test runs, the real report, the real reading, both byte-identical regenerations,
  probes P1-P7.
- **Open:** Codex's review of these fixes; open questions 1-5 in `STUDY_SLOTS.json` (FLAG_FOR_HUMAN_REVIEW).
- **Not licensed:** any statement that the gate is ready to admit the next machine. It should not be used for a real
  `--admit` until finding B is fixed and re-verified.

### Exposure

Read: the two programs, their tests, `STUDY_SLOTS.json`, this file, the T4 job's `watch.py`, `launch_record.json`,
`watch_record.json`, the summary's key names, and the S2 receipt at `1ddf6a1e` (field names only). Wrote: this section
only (the probe script and regenerated copies live in the verifier's scratch folder). No AWS call, no torch, no model,
no `*_eval.jsonl`, no sealed file, no `D:/tksCAS-archive/`, no S3, no meta1 ledger, no transcript.

## Round 2

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Builder: Claude (temporary builder). This answers the verification of `d89721b4`
above (verifier commit `e4fbff40`). It is the builder's own record. It is **not** an independent acceptance: these
fixes still need a fresh verifier and Codex's review.

Names: the task that ordered this round calls the findings MAJOR-A, MINOR-B, MINOR-C and NOTE-D. The verification
above calls the same findings B, A, D and C.

| Round-2 name | Verification's name | Finding (short) | Disposition |
|---|---|---|---|
| MAJOR-A | B | An empty spec field or a stale pin stops the receipt read; INVALID then reopens admission | **FIXED** (limits below) |
| MINOR-B | A | A hand-written admission record is accepted | **FIXED** (limit below) |
| MINOR-C | D | The reader's template exemption covers every future launch | **FIXED** (job code not changed; see below) |
| NOTE-D | C | Does a training job that launched and then failed count as "started"? | **OPEN** (not decided; behaviour unchanged) |

### MAJOR-A: read the receipt first; fail closed on cleanup (`study_spend.py`)

**The problem, in plain words.** Leave one field of a receipt spec empty, or pin a stale hash, and the gate stopped
reading the receipt. It then counted only the cap and never looked at the cleanup. Mark the slot INVALID and the gate
admitted the next machine, even when a machine might still be running.

**Done.**
- **Read first.** `validate_pointer` and `validate_watched` now read the receipt **before** any spec-completeness or
  pin check. They read from whatever commit and path the spec gives. The lenient copy (hash not checked) supplies the
  cost figures and the ids. It can only raise the count, never lower it. The count is the larger of the cap and every
  cost figure found.
- **Confirmed means verified.** A cleanup counts as confirmed only when records whose sha256 matches the pin show
  **this slot's own machine** gone:
  - training: cleanup complete; identity certain; the one launched instance `CONFIRMED_TERMINATED`; nothing pending;
    no failure; compute cleanup `COMPLETE`;
  - watched: terminated confirmed; final state terminated or gone; no volume left; the same instance and launch time
    in the launch record and the watch record;
  - any id the spec does give must agree; a receipt identity that another slot also claims never confirms.
- **The one exception** is a proven capacity refusal under the existing S1 rule: the receipt and its last provider
  record match their pins, every S1-rule check passes, and the receipt is the job the spec names.
- **Fail closed.** A `DONE` or `INVALID` slot, or a `RUNNING` slot past its lifetime, without a confirmed cleanup or
  a proven refusal is `CLEANUP UNCONFIRMED`. That refuses every admission (`CLEANUP_UNCONFIRMED_STOP_AND_REPORT`). The
  row says why: "no readable receipt", "also claimed by another slot", or "does not positively show ...".
  - "Past its lifetime" means: admission time + the basis's instance seconds (training, 14,400 s) or client deadline
    (watched, 130 min for P1b and E1) has passed, or the admission time cannot be read.
  - A `RUNNING` slot whose receipt spec is already filled is now read too, for its figures, ids and cleanup.
- **Hardening found on the way.** The lenient read never passes an option-like commit string (such as
  `--output=x`) to `git show`.

**The probes, after the fix** (each is now a test on the builder's synthetic `World`):

| Probe | Before (verification) | After |
|---|---|---|
| P1: P1b ran 240 min, watcher $3.0719, `expected.bundle_sha256` empty, INVALID | counted $2.00; `--admit P2` exit 0 | counted **$3.18**; cleanup confirmed (the watch record shows it); `--admit P2` decides exactly as its complete-spec twin: ADMIT, total $58.26 |
| P2: as P1, but the watcher saw `terminated_confirmed: false`, `final_state: running` | no cleanup flag; `--admit P2` exit 0 | counted $3.18; **UNCONFIRMED**; `--admit P2` **exit 1** `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b` |
| P3: as P2 with a complete spec, but a stale watch-record pin | no cleanup flag; exit 0 | counted $3.18; **UNCONFIRMED**; **exit 1**. Also exit 1 when the stale file was rewritten to say "terminated" after its pin was taken |
| P4: M1 ran 20,000 s, cleanup `complete: false`, `compute_identity_uncertain: true`, instance `UNKNOWN`, `expected.instance_id` empty, INVALID | counted $11.66; `--admit P1b` exit 0 at $57.08 | counted **$15.58**; **UNCONFIRMED**; `--admit P1b` **exit 1** with `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` and `OVER_CEILING:$61.00 > $60.00` |
| P5 (positive control): P4 with a complete spec | $15.58; exit 1, the same two reasons | unchanged: $15.58; exit 1, the same two reasons |

About P1. The count is now right. P1b's own watch record, with a matching hash, shows the machine terminated with no
volume left. So its cleanup is confirmed, and the admission is the same as for the complete spec. The round-1
disposition stands: a basis breach with a confirmed cleanup is counted at what it recorded; it is not by itself a
stop. Whether every basis breach should stop the study is still open for Codex or the owner.

**Tests** (`test_study_spend.py`): `test_round2_p1_an_empty_spec_field_no_longer_undercounts`,
`test_round2_p2_unconfirmed_cleanup_with_an_empty_spec_field_blocks`,
`test_round2_p3_unconfirmed_cleanup_with_a_stale_pin_blocks`, `test_round2_p4_empty_instance_id_is_counted_and_blocks`,
`test_round2_p5_positive_control_complete_spec`, `test_round2_no_readable_receipt_is_unconfirmed` (INVALID naming no
receipt; a pinned receipt missing from git; an option-like commit, with a spy showing `git` is never called),
`test_round2_a_proven_capacity_refusal_is_not_unconfirmed` (proven: not flagged, even when rejected for a wrong
source; a later provider call or a stale pin: flagged), `test_round2_running_past_its_lifetime_is_unconfirmed` (M1 at
3 h 00 min: not flagged; at 4 h 00 min 01 s: flagged and the report exits 1; P1b at 3 h against a 130-min deadline:
flagged).

**Limits, stated honestly.**
1. The training launcher's receipt has **no volume list**. For training jobs, "no retained volume" rests on the
   launcher's own "complete" cleanup and the terminated instance. The gate does not check the disk itself.
2. An id the spec leaves empty is not guessed. In P1 the confirmation rests on the verified records agreeing with
   each other and with the ids the spec does give.
3. A stale pin never confirms. So a slot whose committed pin is wrong stays `UNCONFIRMED` for good, even if the
   machine is in fact gone. That is a stop-and-report to the owner, by design.
4. **An `INVALID` slot that names no receipt now blocks every admission.** There is no "cancelled, never launched"
   path. A slot that never ran should stay `PLANNED` (a mandatory one keeps its cap reserved). Whether a cancellation
   rule is wanted is a new open question (7) below.
5. "Past its lifetime" counts from the admission time, not the launch time. A launch made later than the admission
   makes the flag early, never late. While a slot is `RUNNING` every admission is refused anyway; the flag adds the
   stop-and-report reason and makes the report exit 1.
6. Behaviour change before commit: a `DONE` row whose pins are stale now also shows `UNCONFIRMED`. Fixing the pins
   before the commit (allowed, as before) clears it.

### MINOR-B: a DONE admission must have been committed as RUNNING (`study_spend.py`)

**Done.** At `DONE`, the slot's admission record must appear, **identical**, in a committed version of
`STUDY_SLOTS.json` that shows the slot `RUNNING`. Otherwise the receipt is rejected
(`ADMISSION_NOT_IN_A_COMMITTED_RUNNING_ROW`). A rejected slot is never "started", and every admission is refused until
it is marked `INVALID`. The pre-gate rows S1, S2 and P1a are exempt, as before. Every committed version is searched,
not only HEAD.

**Test.** `test_round2_p6_a_hand_written_admission_is_refused`: M1 `DONE` with an admission dated
2000-01-01, `--admit` never run: **REJECTED** (was ACCEPTED at $8.94), not started, `--admit M2` exit 1
`DONE_RECEIPT_REJECTED:M1`. Control: the same record, committed as `RUNNING`: ACCEPTED. A committed `RUNNING` record
that differs from the `DONE` one: exit 2 `HISTORY_VIOLATION: M1 was RUNNING`. The test world now writes the committed
`RUNNING` version that `--admit` plus "commit and push" would leave; its fake git lists history newest first, like
`git log`. `test_admitted_job_end_to_end` now commits the real `--admit` output and uses no synthetic version.

**Limit.** A `RUNNING` row typed by hand **and committed** is still accepted. The gate cannot tell who wrote a
committed line. A history rewrite (force-push) is outside the check, as before.

### MINOR-C: the reader's exemption is the one finished job only (`read_results.py`)

**Done.** The exemption is now keyed to **both** the template sha256 `dc05f4afd885d135...` **and** the instance id
`i-09e14d4afd0e0ebfa` (`EXEMPT_WITHOUT_INSTANCE_LINE`). Any other launch whose `env.txt` has no `instance_id=` line is
refused: `ROUTE_NOT_ACCEPTED`, `MACHINE_INSTANCE_ID_MISSING`, exit 3. The reading's text for the finished job is
unchanged, so `RESULTS_READING.json` is byte-identical.

**Not changed, on purpose.** `job.sh.template` and `watch.py` are unchanged: a job-code change needs its own review.
**The next launch from `larger_question_t4_job/` needs a template that writes `instance_id=`.** Today's template still
has sha256 `dc05f4af` (checked by a test) and writes no such line. So a new launch with it would be refused at the
reader. This is written in that folder's `README.md` and in `PREREQUISITE_SLOTS.md`.

**Tests** (`test_read_results.py`): `test_instance_line_exemption_is_only_the_finished_job` (the finished job:
accepted, exit 0; the same template on a new instance: exit 3; the same instance with another template: exit 3),
`test_the_current_template_is_not_exempt_on_a_new_launch` (hashes today's `job.sh.template`, finds `dc05f4af`, and
shows a new launch with it is refused, exit 3).

### NOTE-D: not decided

A training job that launched and then failed counts as "started" for the owner's $30.00 stop (verification probe P7:
M1-M3 each fail after 60 s; all three count; spent $10.33; the stop is then off). The behaviour is unchanged. It is
listed as open question 6 in `PREREQUISITE_SLOTS.md` and below. It is not yet in `STUDY_SLOTS.json`: that file's
open-question list is inside the frozen definitions digest, so adding it needs a re-freeze in a reviewed change.

### Checks run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `python -B test_study_spend.py` | **49 passed, 0 failed** (40 before + 9 new) |
| `python -B test_read_results.py` | **31 passed, 0 failed** (29 before + 2 new; the old in-test exemption case moved into them) |
| Mutation check (scratch script, not committed): switch each fix off, rerun the 9 new study-spend tests | no fail-closed cleanup: 7 fail; any admission accepted: P6 fails; no lenient cost figures: P1-P5 fail |
| `python -B study_spend.py --no-write` (real slots, report mode) | **exit 0; spent upper bound $5.44; plan C $57.08; headroom $2.92**; fallback B +$23.32 does not fit; nothing rejected, shared or unconfirmed |
| Real state regenerated into a scratch file | **byte-identical** to the committed `STUDY_SPEND_STATE.json` (sha256 `6c515c246408e1cb...`) |
| `read_results.py --no-write` (finished job `i-09e14d4afd0e0ebfa`) | **exit 0; ROUTE_ACCEPTED**; script and job verdict INTEGRATION_CHECKS_PASS; JOB START 2026-09-24T05:55:04Z inside [05:53:38Z, 06:28:42Z]; instance id NOT_WRITTEN (exempt: template `dc05f4af` and this instance) |
| Real reading regenerated in memory | **byte-identical** to the committed `RESULTS_READING.json` |
| Finished job's `results/`, `launch_record.json`, `watch_record.json`; `STUDY_SLOTS.json`; `job.sh.template`; `watch.py` | `git diff` empty |
| Real `--admit` | **not run** (it writes the slot RUNNING) |

No real figure changed. The real slots file has no slot that the new rules touch: S1, S2 and P1a are accepted pre-gate
rows (S1 is a proven refusal; S2 and P1a have verified, confirmed cleanups), and nothing is `RUNNING` or `INVALID`.

### Claim states

- **Real (measured here):** the two test runs, the mutation check, the real report, the real reading, both
  byte-identical regenerations.
- **Open:** a fresh verifier and Codex's review of round 2; open questions 1-5 in `STUDY_SLOTS.json`; questions 6 and 7
  below (FLAG_FOR_HUMAN_REVIEW).
- **Not licensed:** any statement that the gate is ready for a real `--admit`, until round 2 is verified.

### Open questions (not decided by the builder)

6. Does a training job that launched and then failed count as "started" for the $30.00 stop? (NOTE-D.)
7. Should a slot that was never admitted and never launched have a way to be cancelled? Today, marking it `INVALID`
   stops the study (fail closed); leaving it `PLANNED` keeps its cap reserved.

### Exposure

Read: this file; `study_spend.py`, `test_study_spend.py`, `STUDY_SLOTS.json` (slot ids, statuses, receipt specs,
open questions), `PREREQUISITE_SLOTS.md`; `read_results.py`, `test_read_results.py`, `README.md`; the finished job's
`launch_record.json` (instance id, template sha256, launch time only); the sha256 of `job.sh.template` and a grep of it
for `instance_id`; the S2 receipt at `1ddf6a1e` (top-level field names, its `cleanup` section and its `stages` only); the head of
`CHANGELOG.md` and the commit lists of this branch. The real reader read `results/` through the program; only its
verdict fields were printed. Wrote: `study_spend.py`, `test_study_spend.py`, `PREREQUISITE_SLOTS.md`, this section,
`read_results.py`, `test_read_results.py`, `README.md` (of the T4 job); scratch files only in the session scratch
folder. Not written: `STUDY_SLOTS.json`, `STUDY_SPEND_STATE.json`, `RESULTS_READING.json`, `job.sh.template`,
`watch.py`, `CHANGELOG.md` (the coordinator batches it). No AWS call, no torch, no model, no `*_eval.jsonl`, no sealed
file, no `D:/tksCAS-archive/`, no salt, no S3, no meta1 ledger, no transcript.

## Verification of 269d13c8d62bdccdba147e825edf7560bcf07383

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Verifier: a fresh Claude verifier sub-agent. It did not build the round-2 fixes.
This is **not** Codex's review and **not** owner acceptance.

**Verdict: CHANGES_REQUIRED.**

In short: round 2 fixes probes P1-P6 as ordered, and the reader fix (MINOR-C) holds. But the gate can still reopen
after INVALID on evidence about the wrong machine. "Cleanup confirmed" today means "a hash-verified receipt shows *a*
machine gone". It does not check that the machine is *this slot's*. At DONE the gate itself proves that such a receipt
is another launch (launched days before the admission) and rejects it. Mark the slot INVALID, and the same receipt
now counts as proof that this slot's machine is gone. `--admit` then exits 0.

### What was run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `git pull --ff-only` | already up to date; tip `269d13c8` |
| `python -B test_study_spend.py` | 49 passed, 0 failed |
| `python -B test_read_results.py` | 31 passed, 0 failed |
| Real report (`main([])`, state written to a scratch file) | exit 0; spent upper bound $5.44; plan C $57.08; headroom $2.92; fallback B +$23.32 does not fit; nothing rejected, shared or unconfirmed; no training job started |
| State regenerated | byte-identical to the committed `STUDY_SPEND_STATE.json` (sha256 `6c515c246408e1cb...`) |
| Real reader on `i-09e14d4afd0e0ebfa` (in memory, no write) | exit 0; ROUTE_ACCEPTED; script and job verdict INTEGRATION_CHECKS_PASS; JOB START 2026-09-24T05:55:04Z inside [05:53:38Z, 06:28:42Z]; instance id NOT_WRITTEN (the exempt pair) |
| Reading regenerated | byte-identical to the committed `RESULTS_READING.json` |
| Finished job's files | working tree vs `b0fd06ff` over `results/`, `launch_record.json`, `watch_record.json`, `dry_run_record.json`, `job.sh.template`, `watch.py`: no difference. `STUDY_SLOTS.json`, `STUDY_SPEND_STATE.json`, `RESULTS_READING.json`: unchanged since `e4fbff40`. `job.sh.template` sha256 is still `dc05f4af...` and contains no `instance_id` text |
| Probes | a scratch script on the builder's own `World` / `FakeGit` and the reader test's `job()` builder; temporary folders only; not committed |
| Real `--admit` | **not run** (it writes the slot RUNNING) |

### Probes P1-P7, rebuilt from this file

| Probe | Result now | Verdict |
|---|---|---|
| P1 | P1b INVALID counted **$3.18** (was $2.00). Cleanup confirmed by P1b's own hash-verified watch record. Spent $8.62. `--admit P2` exit 0 ADMIT, total $58.26 | FIXED as ordered. The count is right; a basis breach with a confirmed cleanup is not a stop (still open) |
| P2 | $3.18; UNCONFIRMED; `--admit P2` exit 1 `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b` | FIXED |
| P3 | stale watch-record pin: $3.18; UNCONFIRMED; exit 1, same reason | FIXED |
| P4 | M1 counted **$15.58** (was $11.66); UNCONFIRMED; spent $21.02; `--admit P1b` exit 1 with `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` and `OVER_CEILING:$61.00 > $60.00` | FIXED |
| P5 (control) | $15.58; exit 1; the same two reasons | matches P4 |
| P6 | admission typed by hand (2000-01-01), never committed RUNNING: REJECTED `ADMISSION_NOT_IN_A_COMMITTED_RUNNING_ROW`; not started; `--admit M2` exit 1 `DONE_RECEIPT_REJECTED:M1` | FIXED as ordered (residual: NOTE F) |
| P7 | M1-M3 each launched and failed after 60 s: started M1, M2, M3; spent $10.33 | unchanged, as ordered (NOTE-D stays open) |

### New findings

**E. MAJOR: after INVALID, another job's clean receipt "confirms" this slot's cleanup** (`study_spend.py`:
`pointer_cleanup_confirmed` lines 585-598, `watched_cleanup_confirmed` 728-739, `proven_refusal` line 643,
`cleanup_gap` 879-888).

What happens:
- The cleanup check asks one question: do hash-verified records show a machine gone? It compares only the ids the
  spec gives. It never asks: is this the launch this slot's admission allowed?
- `bind_admission` does ask that (launch after admission, seed, source, bundle). But it runs only at DONE, and all it
  can do is mark the receipt REJECTED. Marking the slot INVALID then drops the question.
- So the round-2 escape route is still open through a different door: a wrong receipt path, then INVALID.

Probes (synthetic `World`; M1 or P1b admitted at 09:00 and committed RUNNING; its own machine is never shown gone):
- **N1a.** M1 INVALID. The spec names another job's clean training receipt (launched 2026-09-17, claimed by no slot).
  `expected.job` and `expected.instance_id` empty. Counted $11.66. Cleanup "confirmed". `--admit M2` **exit 0 ADMIT**,
  total $57.08.
- **N1b.** The same, with that other job's own ids filled in. **Exit 0 ADMIT**, $57.08. The same row as DONE is
  REJECTED with `LAUNCH_NOT_AFTER_ADMISSION:2026-09-17 12:00:00+00:00 vs admitted 2026-09-24T09:00:00Z`. So the gate
  knows the receipt is not this launch, and after INVALID it still takes it as cleanup evidence.
- **N2a / N2b.** P1b INVALID naming an older job's launch and watch records (launched 2026-09-20), ids empty or
  theirs. Counted $2.00. `--admit P2` **exit 0 ADMIT**, $57.08. As DONE: `BUNDLE_NOT_THE_ADMITTED_BUNDLE`,
  `LAUNCH_NOT_AFTER_ADMISSION`.
- **N3.** M1 INVALID naming an older job's capacity refusal (not S1's). It passes as a "proven refusal". `--admit M2`
  **exit 0 ADMIT**, $57.08. As DONE: `LAUNCH_NOT_AFTER_ADMISSION`.
- **Control.** M1 INVALID naming its own receipt, which says the identity is uncertain: UNCONFIRMED, exit 1.

Why it matters: such receipts already sit in the repository. The design folder holds five pairs of watched records
that no slot claims (`analogy_repair_t4_job/` and its `attempt1/`, `aws_probe_job/`, `hset1a_aws_job/` and its
`attempt1_` files). `typed_pointer_001/` holds 18 older receipt folders. One wrong path on an INVALID row (the row
the runner writes after trouble) admits the next machine while this slot's machine may still exist. That machine's
cost is then counted at the cap only.

Fix. For every slot other than S1, S2 and P1a, a cleanup counts as confirmed, and a refusal as proven, only when the
verified receipt is this slot's admitted launch:
- the slot has an admission record, and a committed version showed the slot RUNNING with that identical record (the
  MINOR-B check, applied to INVALID rows as well as DONE rows);
- the launch time the verified receipt itself shows is at or after `admitted_utc` (training: the time inside the
  receipt's own `job`; watched: `launched_utc` in both records). A stronger option: also before `admitted_utc` plus
  the slot's lifetime;
- training: the receipt's `model_seed` is the slot's seed;
- otherwise UNCONFIRMED, with a reason such as "the receipt is not this slot's launch".

A wrong source or bundle can stay a rejection reason only; the machine may still be this slot's. Add N1a, N1b, N2a,
N2b and N3 as negative tests. P1 and the two proven-refusal tests stay as positive controls (their launches come after
the admission).

**F. NOTE: the admission record need not be one `--admit` wrote** (residual of MINOR-B; the builder states this
limit). Probe **N4**: a bare record (slot, time 2000-01-01, source, seed, arm; no `gate`, `program_sha256` or
`slots_sha256_before`) committed as RUNNING: ACCEPTED, counted as started. The fix that was ordered is met. A cheap
tightening for Codex: require the fields `--admit` writes; `slots_sha256_before` must equal the committed version just
before the first RUNNING one; `program_sha256` must equal a committed `study_spend.py`. That is still forgeable, but a
careless hand edit would fail.

**G. NOTE: the next T4 launch must not reuse `larger_question_t4_job/`.** P1a's pins are the working-tree files
`larger_question_t4_job/launch_record.json` and `watch_record.json`. `launch.py` refuses while `launch_record.json`
exists. Moving it aside (as `analogy_repair_t4_job/attempt1/` did) changes P1a's pinned files. Probe **N5**: P1a
REJECTED and UNCONFIRMED; every admission refused (fail closed, not a wrongful admit). P1a cannot be marked INVALID:
exit 2 `SLOT_DEFINITIONS_CHANGED`, because the row is frozen whole. The study would stop until a reviewed code change.
The T4 folder's README now speaks of "the next launch from this folder"; it should say the next launch goes to a new
folder.

### MINOR-C (the reader): verified fixed

| Probe | Result |
|---|---|
| C1: template `dc05f4af` + `i-09e14d4afd0e0ebfa`, no line | exit 0 ROUTE_ACCEPTED (the one exempt job) |
| C2: same template, new instance, no line | exit 3 `MACHINE_INSTANCE_ID_MISSING` |
| C3: other template, the exempt instance, no line | exit 3 `MACHINE_INSTANCE_ID_MISSING` |
| C4: new instance, empty `instance_id=` line | exit 3 `MACHINE_INSTANCE_ID_NOT_LAUNCHED_INSTANCE` (the empty id) |
| C5: new instance, `instance_id =i-new` (space before `=`) | exit 3 `MACHINE_INSTANCE_ID_MISSING` |
| C6: new instance, two lines (its own and another) | exit 3 `MACHINE_INSTANCE_ID_NOT_LAUNCHED_INSTANCE` |
| C7: the exempt pair, a line naming another instance | exit 3 `MACHINE_INSTANCE_ID_NOT_LAUNCHED_INSTANCE` |
| C8: new instance, template field missing | exit 3 `MACHINE_INSTANCE_ID_MISSING` |
| C9 (control): new instance with its own line | exit 0 ROUTE_ACCEPTED |

`job.sh.template` and `watch.py` are unchanged, as ordered. The next launch needs a template that writes
`instance_id=`; that is recorded in the T4 README and in `PREREQUISITE_SLOTS.md`.

### NOTE-D: still open, behaviour unchanged

P7 gives the same result as before (M1-M3 started; spent $10.33; the $30.00 stop is then off). It is open question 6.
Not decided here.

### Claim states

- **Real (measured here):** both test runs; the real report and its byte-identical state; the real reading and its
  byte-identical regeneration; the file diffs; probes P1-P7, N1a-N5, C1-C9.
- **Open:** Codex's review; open questions 1-7; NOTE-D; notes F and G (FLAG_FOR_HUMAN_REVIEW).
- **Not licensed:** any statement that the gate is ready for a real `--admit`, until finding E is fixed and
  re-verified.

### Exposure

Read: this file; `study_spend.py`; `test_study_spend.py` (helpers and the round-2 tests); `STUDY_SLOTS.json` (ids,
statuses, caps, flags, receipt specs, `what`); `read_results.py`; `test_read_results.py` (helpers, test names); the
round-2 diff of the T4 `README.md`; a grep of `launch.py` and `watch.py` for record file names; git name lists of
`typed_pointer_001/` and of the design folder's record files. The S2 receipt at `1ddf6a1e`: a walk that printed field
names containing time or cost words. **That walk also printed the receipt's embedded `ledger_before` /
`ledger_after` snapshot fields and some of their values.** The meta1 ledger file itself was not opened, nothing was
written to it, and those values are not repeated here. The owner or Codex should know that this receipt carries a
copy of ledger data. Wrote: this section only. The probe script and the regenerated copies live in the verifier's
scratch folder. The untracked `aws_probe_job/dry_run_machine_script.sh` in this working copy is not the verifier's
and was left alone. No AWS call, no torch, no model, no `*_eval.jsonl`, no sealed file, no `D:/tksCAS-archive/`, no
salt, no S3, no transcript.

## Round 3

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Builder: Claude (temporary builder). This answers the verification of `269d13c8`
above (verifier commit `2b8a086f`). It is the builder's own record. It is **not** an independent acceptance: these
fixes still need a fresh verifier and Codex's review.

| Name | Finding (short) | Disposition |
|---|---|---|
| MAJOR-E | After `INVALID`, another job's clean receipt "confirms" this slot's cleanup or passes as a proven refusal | **FIXED** (limits below) |
| NOTE-F | The admission record need not be one `--admit` wrote | **FIXED** (the cheap tightening; limit below) |
| NOTE-G | The next T4 launch must not reuse `larger_question_t4_job/` | **FIXED** (documents only; no job code changed) |
| NOTE-D | Does a training job that launched and then failed count as "started"? | **OPEN** (not decided; behaviour unchanged) |
| Question 7 | Cancelling a slot that was never admitted or launched | **OPEN** (not decided; behaviour unchanged) |

### MAJOR-E: the verified receipt must be this slot's own launch (`study_spend.py`)

**The problem, in plain words.** Round 2 asked one question before it trusted a cleanup: "do hash-verified records
show *a* machine gone?" It never asked "is that machine *this slot's*?" So a row marked `INVALID` could name another
job's clean receipt, and the gate would admit the next machine while this slot's own machine might still be running.

**Done.** For every slot except S1, S2 and P1a (done before the gate existed), a cleanup now counts as confirmed, and
a capacity refusal as proven, only when the verified receipt is **this slot's admitted launch**. This holds whatever
the slot's status: `DONE`, `INVALID`, or `RUNNING` past its lifetime. Three conditions, all required:

1. **A real admission.** The slot's admission record appears, identical, in a committed version of
   `STUDY_SLOTS.json` that shows the slot `RUNNING`. Round 2 checked this only for `DONE` rows; it now applies to
   `INVALID` rows too. The record must also pass NOTE-F (below).
2. **Launched inside this admission's window.** The launch time the verified receipt **itself** shows is at or after
   `admitted_utc` and before `admitted_utc` + the slot's lifetime. For training receipts this is the time in the
   receipt's own `job` id (not the spec's `expected.job`, which N1a left empty). For watched jobs it is `launched_utc`,
   which must be the same in both records. Lifetime: 14,400 s for training slots; the client deadline (130 min) for
   P1b and E1.
3. **Training slots: the right seed and source.** The receipt's own model seed
   (`authority.worker_config.design.model_seed`) equals the slot's seed. The receipt's own source
   (`authority.source_sha`) equals the admitted source. The receipt has no arm field; the arm is bound through the
   source, as before (one source per arm, never shared across arms).

If any condition fails, the cleanup is `UNCONFIRMED` with the reason "the verified receipt is not this slot's admitted
launch: ...", and every admission is refused (stop and report to the owner).

At `DONE`, the window's upper end is now also a rejection reason (`LAUNCH_AFTER_THE_ADMISSION_LIFETIME`), next to the
existing `LAUNCH_NOT_AFTER_ADMISSION`. So a receipt is never ACCEPTED as this slot's launch while the cleanup check
says it is not.

**The probes, after the fix** (each is now a test on the builder's synthetic `World`; admission 2026-09-24T09:00:00Z,
committed `RUNNING`; this slot's own machine is never shown gone):

| Probe | Before (the verification) | After |
|---|---|---|
| N1a: M1 `INVALID` names a clean training receipt of another job (launched 2026-09-17), ids empty | counted $11.66; cleanup "confirmed"; `--admit M2` **exit 0 ADMIT**, total $57.08 | counted $11.66; **UNCONFIRMED** (`LAUNCHED_BEFORE_ADMISSION:2026-09-17T12:00:00Z < admitted 2026-09-24T09:00:00Z`); `--admit M2` **exit 1** `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` |
| N1b: as N1a, with that job's own ids filled in | exit 0 ADMIT, $57.08 | the same: **UNCONFIRMED**; **exit 1**. As `DONE`: REJECTED `LAUNCH_NOT_AFTER_ADMISSION` (as before) and now also UNCONFIRMED |
| N2a: P1b `INVALID` names an older job's launch and watch records (launched 2026-09-20), ids empty | counted $2.00; `--admit P2` **exit 0 ADMIT**, $57.08 | counted $2.00; **UNCONFIRMED** (`LAUNCHED_BEFORE_ADMISSION:2026-09-20T10:00:00Z ...`); `--admit P2` **exit 1** `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b` |
| N2b: as N2a, with that job's own ids | exit 0 ADMIT, $57.08 | **UNCONFIRMED**; **exit 1**. As `DONE`: REJECTED `BUNDLE_NOT_THE_ADMITTED_BUNDLE` and `LAUNCH_NOT_AFTER_ADMISSION` |
| N3: M1 `INVALID` names an older job's capacity refusal (not S1's) | passed as a proven refusal; exit 0 ADMIT, $57.08 | counted $11.66; **UNCONFIRMED** (`LAUNCHED_BEFORE_ADMISSION`); **exit 1**. As `DONE`: REJECTED `LAUNCH_NOT_AFTER_ADMISSION` |

**Positive controls kept.** P1 (`test_round2_p1_...`): P1b's own breached receipt, `INVALID`, still confirmed; `--admit
P2` still ADMIT at $58.26. The proven refusal (`test_round2_a_proven_capacity_refusal_is_not_unconfirmed`): M1's own
refusal, `INVALID`, is still proven. A new "rejected but proven" control replaces the old one (a refusal rejected for
`INSTANCE_TYPE_MISMATCH` is still proven). `test_admitted_job_end_to_end`: a record written by the real `--admit`,
committed, then the slot's own receipt: ACCEPTED and confirmed.

**New tests** (`test_study_spend.py`, 8): `test_round3_n1a_...`, `test_round3_n1b_...`, `test_round3_n2a_n2b_...`,
`test_round3_n3_...`; `test_round3_launch_window_seed_and_source_bind_the_cleanup` (launch at 09:00:00 and 12:59:59:
confirmed and `--admit M2` exit 0; at 13:00:00: UNCONFIRMED `LAUNCHED_AFTER_THE_ADMISSION_LIFETIME`, and as `DONE`
REJECTED `LAUNCH_AFTER_THE_ADMISSION_LIFETIME`; at 08:59:59: UNCONFIRMED; seed 20260918 inside the window:
UNCONFIRMED `SEED_NOT_THE_SLOT_SEED`; the other arm's source with M1's seed, inside the window: UNCONFIRMED
`SOURCE_NOT_THE_ADMITTED_SOURCE`; a job id with no time: UNCONFIRMED `RECEIPT_SHOWS_NO_LAUNCH_TIME`; P1b launched
11:09:59: confirmed; 11:10:00: UNCONFIRMED); `test_round3_an_invalid_rows_admission_must_be_committed_running` (the
slot's own clean receipt, `INVALID`: committed `RUNNING` gives confirmed and `--admit M2` exit 0; never committed gives
UNCONFIRMED and exit 1, where round 2 gave exit 0; no record at all gives UNCONFIRMED); `test_round3_n4_...` and
`test_round3_admission_record_positive_controls` (NOTE-F, below).

**Existing tests changed, and why.**
- The test world's default training job time moved from "10 + slot position" o'clock (M1 at 15:00) to 09:10 + slot
  position minutes (M1 at 09:15). The old default put every synthetic launch after its 4-hour window, which round 3
  correctly refuses. No assertion about money changed.
- `test_round2_a_proven_capacity_refusal_is_not_unconfirmed`: its sub-case "admitted source `999...`, receipt source
  the slot's real one" was a positive control ("rejected, but the refusal is proven"). Under condition 3 the receipt
  shows a source other than the admitted one, so it is now **UNCONFIRMED**. The test now asserts that. A new
  sub-case (rejected for `INSTANCE_TYPE_MISMATCH`, refusal proven) keeps the "rejected but proven" positive control.
  This is the one place where the ordered fix ("arm/source where the receipt shows them") and the verifier's note ("a
  wrong source or bundle can stay a rejection reason only") disagree. The builder followed the ordered fix. It is
  open question 8.
- `test_round2_p6_a_hand_written_admission_is_refused`: its control ("the same 2000-01-01 record, committed:
  ACCEPTED") is now REJECTED `LAUNCH_AFTER_THE_ADMISSION_LIFETIME`: a launch in 2026 is not inside a 4-hour window
  that opened in 2000. The control now uses a record the gate would write (09:00, committed): ACCEPTED. The committed
  2000-01-01 record is kept as a negative case.
- `test_admitted_job_end_to_end`: the world now commits the slots file **before** `--admit`, as the real gate
  requires, so the record's `slots_sha256_before` has a committed version to match.

**Limits, stated honestly.**
1. **The job id's time is the time the job was prepared**, not the time the machine started. `prepare_study.py` and
   `prepare_smoke.py` stamp it with `datetime.now(timezone.utc)`. So the runner must admit first, then prepare the
   job, then launch, all inside the slot's lifetime. A job prepared before its admission (for example, all seeds
   prepared at once, as `prepare_study.py` did for its study) is rejected at `DONE` (true since round 1) and, from
   round 3, its cleanup is `UNCONFIRMED` after `INVALID`: the study stops. This is written in
   `PREREQUISITE_SLOTS.md`, step 2.
2. **Watched slots bind time only.** For P1b, P2 and E1 the cleanup binding is conditions 1 and 2. A wrong source or
   bundle on a watched receipt stays a rejection reason only (as the verifier suggested). The ordered condition 3
   names training slots only.
3. **A receipt of another job that was launched inside this slot's window, with this slot's seed and source, still
   confirms.** The gate cannot tell it from this slot's own launch. The shared-identity check still refuses it if
   any other slot claims it.
4. **A slot launched from the wrong source commit now stops the study for good** (stop and report), even when its
   machine is shown gone. See open question 8.

### NOTE-F: the admission record must be one `--admit` wrote (`study_spend.py`)

**Done.** The same check is used at `DONE` (a failure is a rejection reason) and for the cleanup (a failure makes the
cleanup `UNCONFIRMED`, condition 1 above). The record must:
- carry `gate` equal to `study_spend.py --admit` (`ADMISSION_NOT_WRITTEN_BY_THE_GATE` otherwise);
- carry `program_sha256`, and it must be the sha256 of some committed `study_spend.py`
  (`ADMISSION_PROGRAM_NOT_A_COMMITTED_STUDY_SPEND` otherwise). Any committed version counts, not only the newest;
- carry `slots_sha256_before`, and it must be the sha256 of the committed `STUDY_SLOTS.json` version just before
  the **first** committed version that shows the slot `RUNNING` with this record
  (`ADMISSION_SLOTS_SHA256_BEFORE_MISSING` or `ADMISSION_SLOTS_BEFORE_NOT_THE_COMMITTED_VERSION_BEFORE_RUNNING`).

The committed programs are read only when a judged slot carries an admission record. Today none does, so the real
report reads no extra git objects.

**N4, after the fix.** The verifier's bare record (slot, time 2000-01-01, source, seed, arm; no `gate`,
`program_sha256` or `slots_sha256_before`), committed as `RUNNING`: was ACCEPTED and counted as started. Now
**REJECTED** (`LAUNCH_AFTER_THE_ADMISSION_LIFETIME`, `ADMISSION_NOT_WRITTEN_BY_THE_GATE`,
`ADMISSION_PROGRAM_NOT_A_COMMITTED_STUDY_SPEND`, `ADMISSION_SLOTS_SHA256_BEFORE_MISSING`), counted $11.66, **not
started**, cleanup UNCONFIRMED; `--admit M2` **exit 1** (`DONE_RECEIPT_REJECTED:M1`,
`CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1`).

**Tests.** `test_round3_n4_a_bare_admission_record_is_refused`: the verifier's exact N4; the same bare record dated
09:00 (inside the window), refused by NOTE-F alone with all three reasons; each field wrong on its own (gate "typed
by hand", program `000...`, slots-before `000...`), as `DONE` (REJECTED) and as `INVALID` (UNCONFIRMED).
`test_round3_admission_record_positive_controls`: a record naming an **older** committed program is ACCEPTED; a
`RUNNING` row committed twice is ACCEPTED (the comparison uses the version before the **first** one).

**Limit.** This is still forgeable: a careful hand edit that copies these three values and is committed passes. A
careless one fails. It is compared with committed bytes: on this checkout `STUDY_SLOTS.json` and `study_spend.py` are
`eol=lf`, and their working-copy sha256 equals the committed blob today (checked). A merge that interleaves commits
of the slots file could make "the version just before" differ from the one `--admit` started from; that fails
closed (a false refusal), never open.

### NOTE-G: the next T4 launch goes to a new folder (documents)

**Done.** `larger_question_t4_job/README.md` now says: the next T4 launch goes to a **new** folder, never this one.
P1a's pinned `launch_record.json` and `watch_record.json` (and `results/`) are never moved, renamed, edited or
overwritten. It gives the reason (`launch.py` refuses while `launch_record.json` exists, line 441; moving it aside
rejects P1a, makes its cleanup `UNCONFIRMED` and stops every admission; P1a's row is frozen whole, so it cannot be
marked `INVALID`) and repeats that the new folder's template must write `instance_id=`. `PREREQUISITE_SLOTS.md` says
the same. No job code (`launch.py`, `job.sh.template`, `watch.py`) was changed.

### NOTE-D and question 7: still open

Not decided. Behaviour unchanged. Both are listed in `PREREQUISITE_SLOTS.md` (questions 6 and 7), with the new
question 8.

### Mutation check (scratch script, not committed)

Each new binding was switched off, one at a time, in a temporary copy of `study_spend.py`. The 8 round-3 tests and
four existing tests this round changed or keeps as controls (`test_round2_a_proven_capacity_refusal_...`,
`test_round2_p6_...`, `test_round2_p1_...`, `test_admitted_job_end_to_end`) were run against each copy.

| Switched off | New tests that fail |
|---|---|
| nothing (the program as written) | none |
| condition 1 in the cleanup (committed RUNNING + NOTE-F record not required) | `..._an_invalid_rows_admission_must_be_committed_running`, `..._n4_...` |
| condition 2, lower end of the window | `..._n1a_...`, `..._n1b_...`, `..._n2a_n2b_...`, `..._n3_...`, `..._launch_window_...` |
| condition 2, upper end (cleanup) | `..._launch_window_...` |
| window upper end at `DONE` (rejection) | `..._launch_window_...`, `test_round2_p6_...` |
| condition 3, seed | `..._launch_window_...` |
| condition 3, source | `..._launch_window_...`, `test_round2_a_proven_capacity_refusal_...` |
| the whole binding (`not_this_launch` always empty) | 6 tests (N1a, N1b, N2a/N2b, N3, window, proven refusal) |
| NOTE-F `gate` | `..._n4_...` |
| NOTE-F `program_sha256` | `..._n4_...` |
| NOTE-F `slots_sha256_before` not compared | `..._n4_...` |
| `slots_sha256_before` compared with the NEWEST `RUNNING` version | `..._admission_record_positive_controls` |
| BEFORE: the committed `2b8a086f` program (plus the constant's name only) | 9 tests, including every N probe |

### Checks run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `git pull --ff-only` | already up to date; tip `2b8a086f` |
| `python -B test_study_spend.py` | **57 passed, 0 failed** (49 before + 8 new) |
| `python -B test_read_results.py` | **31 passed, 0 failed** (unchanged) |
| Mutation check | the table above |
| Real report (`main([])`, state written to a scratch file) | **exit 0; spent upper bound $5.44; plan C $57.08; headroom $2.92**; remaining mandatory caps $51.64; fallback B +$23.32 does not fit; nothing rejected, shared or unconfirmed; no training job started |
| Real state regenerated | **byte-identical** to the committed `STUDY_SPEND_STATE.json` (sha256 `6c515c246408e1cb...`) |
| Real reader on `i-09e14d4afd0e0ebfa` (`--no-write`, and in memory) | **exit 0; ROUTE_ACCEPTED**; script and job verdict INTEGRATION_CHECKS_PASS |
| Real reading regenerated in memory | **byte-identical** to the committed `RESULTS_READING.json` |
| Finished job's files (`results/`, `launch_record.json`, `watch_record.json`, `dry_run_record.json`, `job.sh.template`, `watch.py`, `launch.py`, `RESULTS_READING.json`); `STUDY_SLOTS.json`; `STUDY_SPEND_STATE.json` | `git diff` empty |
| Real `--admit` | **not run** (it writes the slot RUNNING) |

**No real figure changed.** The real slots file has only S1, S2 and P1a as `DONE` (all three exempt, as pre-gate
rows) and nothing `RUNNING` or `INVALID`. So no real row meets the new checks.

### Claim states

- **Real (measured here):** both test runs; the mutation check; the real report and its byte-identical state; the
  real reading and its byte-identical regeneration; the file diffs; the probe outputs above.
- **Open:** a fresh verifier and Codex's review of round 3; open questions 1-5 in `STUDY_SLOTS.json`; questions 6, 7
  and 8 (FLAG_FOR_HUMAN_REVIEW).
- **Not licensed:** any statement that the gate is ready for a real `--admit`, until round 3 is verified.

### Open questions (not decided by the builder)

6. (NOTE-D) Does a training job that launched and then failed count as "started" for the $30.00 stop?
7. Should a slot that was never admitted and never launched have a way to be cancelled?
8. Should a wrong source commit on a training receipt stop the study (round 3, as ordered), or stay a rejection
   reason only (the verifier's suggestion)? With the binding, a slot launched from the wrong commit ends
   `UNCONFIRMED` for good, even when its machine is shown gone.

### Exposure

Read: this file; `study_spend.py`; `test_study_spend.py`; `STUDY_SLOTS.json` (slot ids, statuses, caps, kinds,
training seeds and arms, receipt specs with their paths, pins and expected ids, open questions); `PREREQUISITE_SLOTS.md`;
`larger_question_t4_job/README.md`; `read_results.py` lines 283-298; grep hits for `launch_record` / `watch_record` in
`launch.py` and `watch.py`; grep hits for `tpntr` in `.py` files under `cas_only_reasoner/` (job-id formats and
comments); `typed_pointer_001/prepare_study.py` lines 95-115 and the `stamp =` lines of `prepare_smoke.py`; the
`route_acceptance` field and top-level key names of `RESULTS_READING.json`; `git config` and `git check-attr` for line
endings. The real report and the real reader read their receipts and `results/` through the programs; only summary
lines and verdict fields were printed. **No receipt file was opened directly**, so no `ledger_before` /
`ledger_after` field was read or printed. Wrote: `study_spend.py`, `test_study_spend.py`, `PREREQUISITE_SLOTS.md`,
this section, `larger_question_t4_job/README.md`; scratch files only in the session scratch folder (the mutation
script and a regenerated state copy). Not written: `STUDY_SLOTS.json`, `STUDY_SPEND_STATE.json`,
`RESULTS_READING.json`, any job code, `CHANGELOG.md` (the coordinator batches it). The untracked
`aws_probe_job/dry_run_machine_script.sh` is not the builder's and was left alone. No AWS call, no torch, no model, no
`*_eval.jsonl`, no sealed file, no `D:/tksCAS-archive/`, no salt, no S3, no meta1 ledger, no transcript.

## Verification of d2098474d2802538c843afe3118bfd33ecf2399f

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Verifier: a fresh Claude verifier sub-agent. It did not build the round-3 fixes.
This is **not** Codex's review and **not** owner acceptance.

**Verdict: CHANGES_REQUIRED.**

In short: round 3 does what was ordered. N1a, N1b, N2a, N2b, N3 and N4 now refuse. P1-P7 and the positive controls
behave as recorded. The real figures did not change. But the gate ties a receipt to the slot's admission **window**,
not to one **launch**. One admission can cover several launch attempts, and the row names only one receipt. The gate
never reads the others. So after a retry (the pattern this study already used: S1, then S2) the gate drops the first
attempt's cost, and it admits the next machine while the first attempt's machine may still exist. Probes N6a-N6d
reproduce this with exit 0 ADMIT.

### What was run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `git pull --ff-only` | already up to date; tip `d2098474` |
| `python -B test_study_spend.py` | 57 passed, 0 failed |
| `python -B test_read_results.py` | 31 passed, 0 failed |
| Real report (`main([])`, state written to a scratch file) | exit 0; spent upper bound $5.44; plan C $57.08; headroom $2.92; remaining mandatory caps $51.64; fallback B +$23.32 does not fit; nothing rejected, shared or unconfirmed; no training job started |
| State regenerated | byte-identical to the committed `STUDY_SPEND_STATE.json` (sha256 `6c515c246408e1cb...`) |
| Real reader on `i-09e14d4afd0e0ebfa` (in memory, no write) | exit 0; ROUTE_ACCEPTED; script and job verdict INTEGRATION_CHECKS_PASS |
| Reading regenerated | byte-identical to the committed `RESULTS_READING.json` |
| Finished job's files | working tree vs `b0fd06ff` over `results/`, `launch_record.json`, `watch_record.json`, `dry_run_record.json`, `job.sh.template`, `watch.py`, `launch.py`: no difference. `d2098474` does not touch `STUDY_SLOTS.json`, `STUDY_SPEND_STATE.json` or `RESULTS_READING.json`. `job.sh.template` sha256 is still `dc05f4af...` with no `instance_id` text. P1a's pins `82b91aeb...` and `6c2447e1...` match the files and the README |
| Line endings (NOTE-F compares committed bytes) | the committed `.gitattributes` of the Codex folder sets `*.json` and `*.py` to `eol=lf`; the working copy of both files equals the HEAD blob. So the NOTE-F hash checks hold on any checkout, including one with `core.autocrlf=true` |
| Probes | a scratch script on the builder's `World` / `FakeGit`; temporary folders; not committed. Probe N8 used one tiny real git repository in the scratch folder |
| Real `--admit` | **not run** (it writes the slot RUNNING) |

### Probes rebuilt (the round-3 probes written again from the World's primitives, not by calling the builder's tests)

| Probe | Result now | Verdict |
|---|---|---|
| P1 | P1b INVALID, bundle field empty: counted $3.18; cleanup confirmed by its own records (launched 10:00, inside [09:00, 11:10)); spent $8.62; `--admit P2` exit 0 ADMIT, $58.26 | as recorded (positive control) |
| P2 | $3.18; UNCONFIRMED; exit 1 `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b` | holds |
| P3 | stale watch pin, rewritten to say "terminated" after pinning: $3.18; UNCONFIRMED; exit 1 | holds |
| P4 | M1 $15.58; UNCONFIRMED; spent $21.02; `--admit P1b` exit 1 with `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` and `OVER_CEILING:$61.00 > $60.00` | holds |
| P5 | the same as P4 | holds |
| P6 | 2000-01-01 record, never committed RUNNING: REJECTED (now also `LAUNCH_AFTER_THE_ADMISSION_LIFETIME` and the three NOTE-F reasons); not started; UNCONFIRMED; `--admit M2` exit 1 | holds |
| P7 | M1-M3 each launched and failed after 60 s: started M1, M2, M3; spent $10.33 | unchanged (NOTE-D open) |
| N1a | M1 INVALID names another job's clean receipt (2026-09-17), ids empty: $11.66; UNCONFIRMED `LAUNCHED_BEFORE_ADMISSION`; `--admit M2` exit 1 | FIXED |
| N1b | the same, that job's ids filled: exit 1. As DONE: REJECTED `LAUNCH_NOT_AFTER_ADMISSION` and UNCONFIRMED | FIXED |
| N2a / N2b | P1b INVALID names an older job's watched records (2026-09-20): $2.00; UNCONFIRMED; `--admit P2` exit 1 | FIXED |
| N3 | M1 INVALID names an older capacity refusal: UNCONFIRMED; exit 1. As DONE: REJECTED | FIXED |
| N4 | bare record (2000-01-01; no gate, program or slots-before) committed RUNNING: REJECTED with `LAUNCH_AFTER_THE_ADMISSION_LIFETIME` and the three NOTE-F reasons; not started; `--admit M2` exit 1 | FIXED |
| N5 | P1a's pinned files moved to `job/attempt1/`: P1a REJECTED, UNCONFIRMED ("no readable receipt"); `--admit P1b` exit 1; marking P1a INVALID: exit 2 `SLOT_DEFINITIONS_CHANGED` | fails closed, as recorded; NOTE-G's text now forbids the move |
| Controls | M1's own clean receipt, INVALID: confirmed, `--admit M2` exit 0 ($57.08). M1's own capacity refusal, INVALID: proven, exit 0 ($57.08) | hold |
| Reuse R1 | M2 (admitted 12:00) INVALID names M1's unnamed attempt-1 refusal: UNCONFIRMED (`LAUNCHED_BEFORE_ADMISSION`, `SOURCE_NOT_THE_ADMITTED_SOURCE`); exit 1 | holds |
| Reuse R2 | M2 INVALID names M1's accepted receipt: `RECEIPT_SHARED`, both UNCONFIRMED; exit 1 | holds |

### New findings

**H. MAJOR: one admission can cover several launch attempts, but a row names one receipt, and the gate never
reads the others** (`not_this_launch` lines 614-644, `cleanup_gap` 974-990, `account` 993-1078; the procedure in
`PREREQUISITE_SLOTS.md` step 2).

What happens:
- `--admit` opens a window: the admission time up to the admission time plus the slot's lifetime (training 14,400 s;
  watched 130 min).
- Round 3 takes a receipt as "this slot's launch" when the launch time it shows lies in that window (and, for a
  training slot, its seed and source are right). Any number of jobs can pass that test.
- The row holds one receipt spec. The gate reads only that receipt: for the count, for the cleanup, and for the
  shared-identity check.
- The docs say "admit first, then prepare the job, then launch, all inside the slot's lifetime". They do not say
  "one launch per admission". They do not say a failed attempt must be written down.
- So after a retry, the gate's answer depends on which attempt the runner writes down.

Probes (synthetic `World`; M1 or P1b admitted at 09:00 and committed RUNNING; every receipt hash-verified):
- **N6a.** M1 attempt 1 (prepared 09:05) is an AWS capacity refusal. Its receipt is moved aside to
  `r/m1_attempt1/`, as S1's was to `..._attempt1/`. Attempt 2 (09:15) finishes clean, and the row names it. M1 is
  ACCEPTED at $8.94; spent $14.38; `--admit M2` **exit 0 ADMIT**, total $54.36. The refusal is not counted. This same
  gate counts a named refusal at **$1.60**. No mistake by the runner is needed.
- **N6b.** Attempt 1 launched a machine. It ran 600 s. Its cleanup and the machine's identity are uncertain.
  Attempt 2 is clean and is named. ACCEPTED $8.94; no cleanup flag; `--admit M2` **exit 0**, $54.36. With attempt 1
  named alone, the gate says UNCONFIRMED and exit 1.
- **N6c.** P1b attempt 1 (launched 09:05): the watcher saw it still running. Its records are moved to
  `p1b/attempt1/` (`launch.py` refuses while `launch_record.json` exists, so a retry in the same folder must move
  them; `analogy_repair_t4_job/attempt1/` did this). Attempt 2 (09:45) is clean and named. ACCEPTED $0.55;
  `--admit P2` **exit 0**, $55.63.
- **N6d.** The row names attempt 1, a proven capacity refusal (09:05). Attempt 2 (09:15) ran 20,000 s with an
  uncertain identity and is not named. ACCEPTED $1.60; not started; spent $7.04; `--admit M2` **exit 0**, $47.02.
  Named, attempt 2 is probe P4: $15.58, UNCONFIRMED, `OVER_CEILING:$61.00 > $60.00`.

Why MAJOR and not the stated limit 3:
- Limit 3 speaks of "a receipt of another job ... launched inside this slot's window". The usual source of such a
  receipt is not a stranger. It is this slot's own retry.
- Retries are the norm in this study. S1 (capacity refusal, job time 02:12:44) and S2 (finished, 03:35:50) are
  1 h 23 min apart, inside one 4-hour window. `analogy_repair_t4_job` and `hset1a_aws_job` each ran an attempt 1
  and an attempt 2. `typed_pointer_001/` has receipt folders named `..._orphaned_...`, `..._preflight_refused_...`
  and `..._gradfail_...` (names read only; the folders were not opened).
- N6a breaks the "spent upper bound" by the gate's own $1.60 per extra attempt, with the runner following the docs.
  Round 1 rated a $1.07 undercount MAJOR (finding 4). Plan C's headroom is $2.92, so two retries exceed it.
- N6b-N6d admit the next machine while a machine may still exist. That is the case round 3 was ordered to close.

Fix (a suggestion; Codex or the owner decides the design):
1. Docs: one admission covers **one** launch attempt. Commit every attempt's receipt, including a capacity refusal
   and a failed launch. Never prepare or launch a second job under one admission unless the row names every attempt.
2. Code, one of:
   - a. let the row list every attempt under its admission. Count each one (a proven refusal at its bound; anything
     else at the larger of the cap and its figures). Bind each to the window, seed and source. Require a confirmed
     cleanup or a proven refusal for each.
   - b. look for attempts the row does not name, and fail closed. Training: any committed receipt whose own job id
     carries this slot's seed and this admission's source prefix (the job id holds both) and a time in the window.
     Watched: any `launch_record.json` in the design folder whose `launched_utc` lies in the window. Any unnamed one
     makes the cleanup UNCONFIRMED ("another launch attempt of this admission is not named").
   - Detection only sees receipts that exist in git or on disk. Rule 1 covers the rest.
3. Tests: N6a (attempt 1 is counted, or the row is refused), N6b, N6c and N6d (exit 1) as negative tests. The
   single-attempt tests stay as positive controls.
4. Where a retry goes is not decided: no retry slot exists, and the slot definitions are frozen. New open question 9.

**I. MINOR: the history is one branch's default `git log`; a merge can hide a committed RUNNING or DONE row**
(`GitReader.history`, lines 375-380).

- `git log --format=%H -- STUDY_SLOTS.json` uses git's default history simplification. If a merge keeps one side's
  slots file exactly, the other side's commits of that file drop out of the list.
- **Probe N8** (a tiny real repository in the scratch folder). Main has M1 PLANNED. Branch `side` commits M1
  RUNNING, then M1 DONE. Then `git merge -s ours side` on main. Default log: 1 version (PLANNED). `GitReader.history`
  returned that 1 version, and `check_history` **passed** with M1 PLANNED again. So `--admit M1` would be judged as if
  M1 never ran. With `git log --full-history`: 4 versions, and `check_history` exits 2
  (`HISTORY_VIOLATION: M1 was DONE ... now PLANNED`).
- The same root: the gate reads only the local checkout. Two checkouts, or one that was not pulled, each see their
  own file, and each can admit. The second RUNNING row's push then fails or conflicts. A conflict resolved to "ours"
  is N8.
- Fix: read history with `--full-history`; make `--admit` refuse unless HEAD equals the fetched remote tip of the
  study's branch; in the docs, `git pull --ff-only` before `--admit`, and launch only after the RUNNING row's push
  succeeds.
- Why MINOR: it needs two runners, or a stale checkout plus a merge that discards one side. A force-push was already
  stated to be outside the check; this is a second way to the same place.

**J. NOTE: a careful hand-written admission record still passes** (the NOTE-F limit the builder states,
reconfirmed). Probe N7: the World writes every admission record by hand, with `gate`, `program_sha256` and
`slots_sha256_before` filled, and commits it RUNNING. ACCEPTED; `--admit M2` exit 0, $54.36. As stated. No change
asked.

**K. NOTE: watched slots bind time only, so a stray watched launch inside the window confirms** (the builder's
limit 2, reconfirmed). Probe R3: E1 admitted 10:30 with bundle `d...`; its INVALID row names a watched job launched
at 10:40 with bundle `c...` (a launch the gate never admitted). Cleanup confirmed; `--admit P2` exit 0, $55.63. The
bundle and source are known at `--admit` and shown in the launch record. Binding them for watched slots would match
what round 3 does for training sources. Codex or the owner should decide both together (with open question 8).

### Still open (not decided here)

NOTE-D (open question 6), question 7 and question 8 stay open, as the builder left them. New: **9. Where does a
retry of a slot go** after a capacity refusal or a failed launch? (No retry slot exists; the definitions are frozen.)

### Claim states

- **Real (measured here):** both test runs; the real report and its byte-identical state; the real reading and its
  byte-identical regeneration; the file diffs; probes P1-P7, N1a-N5, R1-R3, N6a-N6d, N7, N8.
- **Open:** Codex's review; open questions 1-9; findings H and I; notes J and K (FLAG_FOR_HUMAN_REVIEW for the
  design choices).
- **Not licensed:** any statement that the gate is ready for a real `--admit`, until finding H is fixed and
  re-verified.

### Exposure

Read: this file; `study_spend.py`; `test_study_spend.py`; `STUDY_SLOTS.json` (slot ids, statuses, caps, bases,
training seeds and arms, receipt specs including S1's and S2's job ids); `PREREQUISITE_SLOTS.md` (lines 20-179 and the
round-3 diff); the round-3 diff of `larger_question_t4_job/README.md`; `read_results.py` lines 283-300; the Codex
folder's `.gitattributes` (first 10 lines) and the git config for line endings; the folder listing of
`typed_pointer_001/` (names only). P1a's `launch_record.json` and `watch_record.json` were read as bytes and hashed
only; nothing from them was printed. The real report read its receipts through the program, and only summary lines
were printed. The real reader ran in memory; only its top-level key names, `route_acceptance`, the two verdicts and
`instance_id` were printed. **No receipt file was opened directly**, so no `ledger_before` / `ledger_after` field was
read or printed. Wrote: this section only. The probe script, the regenerated state and the N8 repository live in the
verifier's scratch folder. The untracked `aws_probe_job/dry_run_machine_script.sh` is not the verifier's and was left
alone. No AWS call, no torch, no model, no `*_eval.jsonl`, no sealed file, no `D:/tksCAS-archive/`, no salt, no S3,
no meta1 ledger, no transcript.

## Round 4

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Builder: Claude (temporary builder). This answers the verification of `d2098474`
above (verifier commit `3c51785f`). It is the builder's own record. It is **not** an independent acceptance: these
fixes still need a fresh verifier and Codex's review.

| Name | Finding (short) | Disposition |
|---|---|---|
| MAJOR-H (a) | A row names one receipt, but one admission can cover several launch attempts | **FIXED**: a row lists every attempt; each is counted and checked |
| MAJOR-H (b) | The gate never looks for attempts the row does not name | **FIXED**: unlisted attempts fail closed (limits below) |
| MINOR N8 (the verification's I) | History read with git's default simplification; `--admit` can run on a stale checkout | **FIXED** |
| NOTE J (probe N7) | A careful hand-written admission record still passes | **UNCHANGED**, as ordered; the limit stays stated |
| NOTE K (probe R3) | Watched slots bind by launch time only | **OPEN**, now written into question 8 |
| Questions 6, 7, 8 | As before | **OPEN**; new question 9 |

### MAJOR-H (a): the row lists every launch attempt (`study_spend.py`)

**The problem, in plain words.** One admission opens a time window. More than one launch can happen inside it: AWS
refuses a machine, and the runner launches again (S1 then S2 did exactly this). The row named one receipt. The gate
read only that one. So the first attempt's cost was dropped, and the first attempt's machine was never checked.

**Done.**
- A row may carry `attempts`: every launch attempt under its admission, in launch order. Each entry is a receipt spec
  of the same form as `receipt`. It is a mutable field (`MUTABLE` now has `attempts`), so it is **not** in the frozen
  definitions digest. The digest is unchanged: `82e809500f14ad8988b3b45ad6a7265f0601a5791f13cb8ea5a4608771456764`.
- Without `attempts`, a row has one attempt, its `receipt`. S1, S2 and P1a are frozen whole and keep this form. Their
  output is unchanged byte for byte.
- **Each attempt is judged on its own**, by the same code as a single receipt: pins, identity, its own admission
  binding (launched inside the window; a training attempt's own seed and source), and its cleanup (confirmed, or a
  proven capacity refusal). One attempt that fails makes the slot `UNCONFIRMED`, which refuses every admission.
- **The count is the sum over attempts.** `DONE` accepted: the sum of the bounds (a proven refusal at its bound, like
  S1). `DONE` rejected or `INVALID`: for each attempt, the larger of the cap and every cost figure it shows, summed.
  `RUNNING`: the full cap for the attempt in progress, plus every earlier listed attempt.
- **One receipt, one attempt.** An identity claimed by two listed attempts, of one slot or of two, is shared: both are
  rejected and every admission is refused.
- **At `DONE`, `receipt` must be the last listed attempt** (`RECEIPT_NOT_THE_LAST_LISTED_ATTEMPT` otherwise).
- **History.** A committed `attempts` list only grows at its end. No listed attempt may be removed, changed or
  reordered. An `INVALID` row's list never changes. A `PLANNED` row may not carry one; a malformed list is exit 2.

**The positive test the coordinator asked for.**
`test_round4_two_attempts_refusal_then_clean_run_are_both_counted_and_admitted`: M1 admitted 09:00; attempt 1 at 09:05
is an AWS capacity refusal; attempt 2 at 09:15 finishes clean; both listed. M1 is ACCEPTED at **$10.54** ($1.60 +
$8.94). Spent $15.98. No cleanup flag. M1 counts as a started training job. `--admit M2` **exit 0 ADMIT**, total
**$55.96** ($15.98 + $11.66 + $28.32 other mandatory caps).

### MAJOR-H (b): look for attempts the row does not list, and fail closed (`study_spend.py`)

**Done.** For every `DONE`, `INVALID` or overdue `RUNNING` slot, the program searches for launch attempts its row
does not list. A finding, or a search that cannot run (`SCAN_FAILED`), makes the slot's cleanup `UNCONFIRMED`. The
folders searched, stated plainly:

- **Training slots.** Files named `result.json`, `*_result.json` or `provider_NNNN.json`, at any depth, under
  `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001/` (the constant
  `TRAINING_RECEIPT_HOME`, the training launcher's receipt home) **and** under the folder that holds each listed
  attempt's receipt folder. They are read at HEAD, at every commit a listed attempt is pinned to, and in the working
  tree (files git reports untracked or modified). Only the job id is taken from each file (`job`, `authority.job`,
  `request.job`). An unlisted attempt: a job id that carries this slot's seed and the admitted source's first
  8 characters, prepared inside the admission window, that no listed attempt of this slot and no other slot claims.
- **Watched slots.** Files whose names end in `launch_record.json` or `watch_record.json`, anywhere under the design
  folder `helm_eval_design_20260923/`, on disk and at HEAD. Only the instance id and `launched_utc` are taken. An
  unlisted attempt: a record that no listed attempt and no other slot claims (by path or instance id), launched inside
  the window, or with no readable launch time and inside the slot's own job folder.
  - This is **wider** than "the slot's job folder" in the order, on purpose. `launch.py` refuses while a
    `launch_record.json` exists, and NOTE-G sends the next launch to a new folder. So a retry often lands in a
    different folder. The mutation check below shows the narrower search misses it (probe N6c, second folder).
  - A record another slot claims is that slot's. This matters in normal use: P2 may be admitted inside P1b's 130-min
    window, so P2's launch lies in P1b's window (test `test_round4_a_launch_another_slot_claims_is_not_this_slots`).

**S1, S2 and P1a: which it is.** They are **not** exempt. They have no admission window, so the program checks them
without one, on every run: S1 and S2 against every job id with their own seed and their own source prefix, at any
time; P1a against every watched record under `larger_question_t4_job/`. On the real data this search finds nothing
unlisted. **S1, S2 and P1a are the complete set of attempts of their jobs.** The evidence:

- The program's search (real, this round, read-only): in `typed_pointer_001/` at HEAD and at `1ddf6a1e` it saw
  19 job ids and no scan failure. The only seed-20260917 typed-pointer jobs prepared on 2026-09-24 are S1's
  `cas-meta2-tpntr-20260924021244-70490111-m-20260917` and S2's `cas-meta2-tpntr-20260924033550-3df31d96-m-20260917`.
  Each matches only its own slot's criteria. `larger_question_t4_job/` holds only P1a's `launch_record.json` and
  `watch_record.json` (`i-09e14d4afd0e0ebfa`, launched 2026-09-24T05:53:38Z), on disk and at HEAD.
- Git history over **all** refs (file names only): the only `result.json` files ever added under `typed_pointer_001/`
  for this smoke are attempt 1 (added in `5715fda0`, renamed with unchanged bytes to `..._attempt1/` in `3df31d96`)
  and attempt 2 (added in `1ddf6a1e`). The T4 folder's launch and watch records were each added once (`fae817fe`,
  `b0fd06ff`) and never replaced. The nearest other watched launch in the design folder is `analogy_repair_t4_job`
  at 2026-09-24T00:22:13Z, 5 h 31 min before P1a, in another folder.

**The probes, after the fix** (each is now a test on the builder's synthetic `World`; admission 09:00, committed
`RUNNING`):

| Probe | Before (the verification) | After |
|---|---|---|
| N6a: M1 attempt 1 (09:05) a capacity refusal, moved to `r/m1_attempt1/`; attempt 2 (09:15) clean and named alone | ACCEPTED $8.94; spent $14.38; `--admit M2` **exit 0 ADMIT**, $54.36 | still ACCEPTED at $8.94, but **UNCONFIRMED** (`UNLISTED_TRAINING_ATTEMPT:cas-meta2-tpntr-20260924090500-44444444-m-20260917`); `--admit M2` **exit 1** `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` |
| N6b: attempt 1 ran 600 s, cleanup and identity unconfirmed; attempt 2 clean, named alone | ACCEPTED $8.94; **exit 0**, $54.36 | **UNCONFIRMED** (unlisted attempt 1); **exit 1**. Listed honestly: REJECTED (`attempt 1: CLEANUP_INCOMPLETE_OR_IDENTITY_UNCERTAIN`) and UNCONFIRMED by attempt 1's own cleanup; exit 1 |
| N6c: P1b attempt 1 (09:05) still running per its watcher; records moved aside; attempt 2 (09:45) clean, named | ACCEPTED $0.55; `--admit P2` **exit 0**, $55.63 | **UNCONFIRMED** (`UNLISTED_WATCHED_LAUNCH`); **exit 1**. The same when attempt 1 sits in `p1b/attempt1/`, in a new folder `p1b_try1/`, or only at HEAD (deleted from disk). Listed honestly: REJECTED and UNCONFIRMED by attempt 1's own record |
| N6d: the row names attempt 1, a proven refusal (09:05); attempt 2 (09:15) ran 20,000 s, identity lost, unnamed | ACCEPTED $1.60; spent $7.04; **exit 0**, $47.02 | still ACCEPTED at $1.60, but **UNCONFIRMED** (unlisted attempt 2); **exit 1** |

**Other new tests** (`test_study_spend.py`):
- `test_round4_attempt_rules`: receipt not the last attempt: REJECTED. Another job's older receipt listed as
  attempt 1: REJECTED `attempt 1: LAUNCH_NOT_AFTER_ADMISSION`, and UNCONFIRMED. One attempt listed twice:
  `RECEIPT_SHARED` by `M1#1,M1#2`, exit 1. `INVALID` with a refusal and a clean run: $23.32. `RUNNING` with a listed
  refusal: $13.26 ($11.66 + $1.60). Attempts on a `PLANNED` row, an empty list, a wrong kind: exit 2.
- `test_round4_committed_attempts_only_grow`: append: allowed. Remove, reorder, change: exit 2 `HISTORY_VIOLATION`.
- `test_round4_the_scan_reads_head_the_pins_and_the_working_tree`: an attempt only in the working tree; one only at
  HEAD under the receipt home: both found. Control: M1's seed and source, prepared a week earlier: not a finding. A
  search that fails: UNCONFIRMED, exit 1.
- `test_round4_a_launch_another_slot_claims_is_not_this_slots`: P2 launched inside P1b's window, and two test slots
  with one seed and one source: no finding; `--admit M1` exit 0.
- `test_round4_pre_gate_rows_are_checked_for_other_attempts`: a third smoke job with S2's seed and source: S2
  UNCONFIRMED. Another seed: no finding. A foreign launch record in P1a's job folder: P1a UNCONFIRMED. P1a's own copy,
  and a record in another folder: no finding.

**Test world change.** S1's and S2's job ids in the synthetic world now use the launcher's format
(`cas-meta2-tpntr-<time>-<source prefix>-m-<seed>`), because the pre-gate search reads seed and source from them. The
world also pins every listed attempt, whatever the row's status. No assertion about money changed.

### MINOR N8: full history, and `--admit` only at the fetched remote tip (`study_spend.py`)

**Done.**
- `GitReader.history` now runs `git log --full-history`. The verifier's probe, rebuilt as a test on a tiny real git
  repository (`test_round4_n8_full_history_sees_a_merged_side_branch`): main has M1 `PLANNED`; branch `side` commits
  M1 `RUNNING`, then `DONE`; `git merge -s ours side`. Plain `git log`: 1 version. The gate's history includes the
  `RUNNING` and `DONE` versions, and `check_history` raises `HISTORY_VIOLATION: M1 was ...`.
- `--admit` now runs `git fetch <remote> <branch>` for the current branch's upstream. It refuses unless HEAD equals
  the fetched tip (`NOT_AT_THE_FETCHED_REMOTE_TIP`, exit 1). No upstream, a detached HEAD, or a fetch that fails (or
  takes over 120 s) refuses too. The decision prints the result as `remote_tip`. Report mode never fetches.
  Test `test_round4_n8_admit_only_at_the_fetched_remote_tip` (a local bare "remote", no network): at the tip: yes. A
  local commit not pushed: refused. Another clone pushes: refused until `git pull --ff-only`. The remote gone:
  `FETCH_FAILED`. Detached: refused. Through the gate: exit 1, and the slot stays `PLANNED`.
- Docs (`PREREQUISITE_SLOTS.md`): `git pull --ff-only` before `--admit`; launch only after the `RUNNING` row's push
  succeeds.

### NOTES J and K: not changed

- **J (N7).** A careful hand-written admission record, committed as `RUNNING`, still passes. The round-3 limit stays
  stated as it was.
- **K (R3).** Watched slots still bind a receipt to the admission by launch time only. It is now written into open
  question 8, to be decided with it.

### Mutation check (scratch script, not committed)

Each fix was switched off, one at a time, in a temporary copy of `study_spend.py`. The whole test file ran each time.

| Switched off | Tests that fail (of 69) |
|---|---|
| nothing (the program as written) | none |
| (a) the `attempts` list ignored | 4: `attempt_rules`, `n6b`, `n6c`, `two_attempts_...` |
| (a) the "receipt is the last attempt" rule | `attempt_rules` |
| (a) `RUNNING` without its earlier attempts | `attempt_rules` |
| (a) committed attempts may shrink or change | `committed_attempts_only_grow` |
| (b) the whole search | 6: `n6a`, `n6b`, `n6c`, `n6d`, `pre_gate_rows_...`, `the_scan_reads_...` |
| (b) the pre-gate rows not searched | `pre_gate_rows_...` |
| (b) the training window not applied | `the_scan_reads_...` |
| (b) other slots' claims not excluded | `a_launch_another_slot_claims_...` (this test was added in this round, after the first mutation pass showed that no test caught this switch) |
| (b) watched: only the slot's job folder | `n6c` |
| (b) the working tree not searched | `the_scan_reads_...` |
| (b) HEAD not searched (training) | `the_scan_reads_...` |
| (b) a failed search passes | `the_scan_reads_...` |
| N8: no `--full-history` | `n8_full_history_...` |
| N8: the remote tip ignored | `n8_admit_only_at_...` |
| BEFORE: the committed `3c51785f` program | 11 (every round-4 test except the claims control) |

### Checks run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `git pull --ff-only` | already up to date; tip `3c51785f` |
| `python -B test_study_spend.py` | **69 passed, 0 failed** (57 before + 12 new) |
| `python -B test_read_results.py` | **31 passed, 0 failed** (unchanged) |
| Mutation check | the table above |
| Real report (`main([])`, state written to a scratch file) | **exit 0; spent upper bound $5.44; plan C $57.08; headroom $2.92**; remaining mandatory caps $51.64; fallback B +$23.32 does not fit; nothing rejected, shared or unconfirmed; no training job started. 1.2 s, including the new search |
| Real state regenerated | **byte-identical** to the committed `STUDY_SPEND_STATE.json` (sha256 `6c515c246408e1cb...`) |
| Real reader on `i-09e14d4afd0e0ebfa` (in memory, no write) | **exit 0; ROUTE_ACCEPTED**; script and job verdict INTEGRATION_CHECKS_PASS |
| Real reading regenerated in memory | **byte-identical** to the committed `RESULTS_READING.json` |
| Real search for S1, S2, P1a (read-only) | the job ids and records listed above; no scan failure |
| Real `--admit` | **not run** (it writes the slot `RUNNING`, and now also fetches) |

### Limits, stated honestly

1. **The search sees git and the working tree only.** A receipt that exists only on another branch, at a commit no
   listed attempt pins, is not seen; nor is a deleted one. The docs now require: commit every attempt's receipt;
   never delete one or move it out of the searched folders; list every attempt. A later attempt's pinned commit
   normally contains the earlier attempts' receipts, when they are committed in order on one branch.
2. **Only the launcher's job-id format is matched** (`...-<14-digit time>-<8 hex>-m-<seed>`). A training job
   prepared before its admission is outside the window, so it is not a finding (if listed, it fails the binding, as
   in round 3).
3. **A watched record with no readable launch time** is a finding only inside the slot's own job folder.
4. **Fail closed can stop the study on a job that is not the slot's.** A watched job outside the study (open
   question 1) launched anywhere in the design folder inside a slot's window makes that slot `UNCONFIRMED`. That is a
   stop and report, not a wrongful admit.
5. **`INVALID` counts every listed attempt at the larger of the cap and its figures**, a proven refusal too. This is
   the existing `INVALID` rule applied per attempt. It is pessimistic (a refusal plus a clean run, `INVALID`: $23.32).
6. **Every report now reads the receipt folders.** On the real data: `typed_pointer_001/` at HEAD and at `1ddf6a1e`
   (at `1ddf6a1e`: 551 matching files, 19,600,495 bytes), plus the design folder's 12 watched records on disk and at
   HEAD. The receipts are parsed as JSON; only the job id is used. Their embedded `ledger_before` / `ledger_after`
   fields are never used or printed.
7. **`--admit` now needs the network**, to fetch the upstream. Offline, it refuses. It checks the current branch's
   configured upstream, so the runner must run it on the study's branch.
8. **The saved state's `rules.admission` text** does not name the new remote-tip condition. It was left as it was, so
   the committed `STUDY_SPEND_STATE.json` stays byte-identical. The `--admit` decision prints the condition.

### Claim states

- **Real (measured here):** both test runs; the mutation check; the real report and its byte-identical state; the
  real reading and its byte-identical regeneration; the real search for S1, S2, P1a; the git history listings.
- **Open:** a fresh verifier and Codex's review of round 4; open questions 1-5 in `STUDY_SLOTS.json`; questions 6-9
  (FLAG_FOR_HUMAN_REVIEW).
- **Not licensed:** any statement that the gate is ready for a real `--admit`, until round 4 is verified.

### Open questions (not decided by the builder)

6. (NOTE-D) Does a training job that launched and then failed count as "started" for the $30.00 stop?
7. Should a slot that was never admitted and never launched have a way to be cancelled?
8. Should a wrong source commit on a training receipt stop the study, or stay a rejection reason only? To decide with
   it: should watched slots bind the admitted bundle and source, not only the launch time (NOTE K, probe R3)?
9. Where does a retry go after its admission window has closed? No retry slot exists, and the definitions are frozen.

### Exposure

Read: this file; `study_spend.py`; `test_study_spend.py`; `PREREQUISITE_SLOTS.md`; `STUDY_SLOTS.json` (slot ids,
statuses, receipt specs, row keys); `read_results.py` lines 280-300; git name and size listings of
`typed_pointer_001/` at HEAD, `1ddf6a1e` and `origin/claude/helm-on-launch-20260924` (fetched, read-only); git history
of file names over all refs for `typed_pointer_001/` and `larger_question_t4_job/`. A scratch script printed, for each
`result.json` in `typed_pointer_001/` at `1ddf6a1e`, **only** its job id, the first 8 characters of its source, its
model seed and its status. The design folder's launch records: only instance id and `launched_utc` were printed. The
real reader ran in memory; only its top-level key names, `route_acceptance` and the two verdicts were printed. The
receipts were parsed by programs (the scratch script and the gate); their `ledger_before` / `ledger_after` fields were
not printed or inspected. Wrote: `study_spend.py`, `test_study_spend.py`, `PREREQUISITE_SLOTS.md`, this section.
Scratch only (the session scratch folder): the job-id script, the mutation script and its temporary copies, a
regenerated state, and a small git repository used to check upstream and fetch behaviour. Not written:
`STUDY_SLOTS.json`, `STUDY_SPEND_STATE.json`, `RESULTS_READING.json`, any job code, `CHANGELOG.md` (the coordinator
batches it). The untracked `aws_probe_job/dry_run_machine_script.sh` is not the builder's and was left alone. No AWS
call, no torch, no model, no `*_eval.jsonl`, no sealed file, no `D:/tksCAS-archive/`, no salt, no S3, no meta1
ledger, no transcript.

## Verification of 4e292912a1efe0a85312574a69291a1af5af5427

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Verifier: a fresh Claude verifier sub-agent. It did not build the round-4 fixes.
This is **not** Codex's review and **not** owner acceptance.

**Verdict: APPROVE_ADMISSION_GATE** (with two MINOR findings and two NOTEs, below).

In short: round 4 does what was ordered. N6a-N6d now refuse. The two-attempt positive case is admitted, with both
attempts counted. N8 is closed. The real figures did not change. I found three more ways to hide a launch attempt
from the new search (MINOR L). Each one needs the runner to leave an attempt out of the row, and
`PREREQUISITE_SLOTS.md` forbids that. When the same attempts are listed, as the document says, the gate refuses in
every case. I also found that a retry prepared the way the real S1 -> S2 retry was prepared stops the study for good
(MINOR M). That fails closed: no money is at risk. But the documented retry path does not work as written.

### What was run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `git pull --ff-only` | already up to date; tip `4e292912` |
| `python -B test_study_spend.py` (run once) | 69 passed, 0 failed (about 7 s) |
| `python -B test_read_results.py` (run once) | 31 passed, 0 failed |
| Real report (`main([])`, state written to a scratch file) | exit 0; spent upper bound $5.44; plan C $57.08; headroom $2.92; remaining mandatory caps $51.64; fallback B +$23.32 does not fit; nothing rejected, shared or unconfirmed; no training job started; 1.0 s |
| State regenerated | byte-identical to the committed `STUDY_SPEND_STATE.json` (sha256 `6c515c246408e1cb...`) |
| Real reader on `i-09e14d4afd0e0ebfa` (in memory, and `main(["--no-write"])`) | exit 0; ROUTE_ACCEPTED; script verdict and job verdict INTEGRATION_CHECKS_PASS |
| Reading regenerated | byte-identical to the committed `RESULTS_READING.json` |
| Finished job's files | `results/`, `launch_record.json`, `watch_record.json`, `dry_run_record.json`, `job.sh.template`, `watch.py`, `launch.py`: no difference from `b0fd06ff`. Round 4 does not touch the job folder, `STUDY_SLOTS.json` or `STUDY_SPEND_STATE.json` |
| Remote-tip check on this real checkout (`GitReader().at_remote_tip()` only; no `--admit`) | True: HEAD `4e292912` equals the fetched tip. This checkout's own `origin/research/helm-integration-20260923` ref is stale (`b0fd06ff`): the configured fetch refspec lists only three other branches. The gate reads `FETCH_HEAD`, so the stale ref does not fool it |
| Probes | a scratch script built from the World's primitives (`pointer`, `refusal`, `provider`, `LAUNCH`, `WATCH`, the spec builders, `admission`, `invalid`, `build`), not from the round-4 helpers or tests; temporary folders, deleted afterwards; N8 in tiny real git repositories |
| Real `--admit` | **not run** |

### S1, S2, P1a: the complete set of attempts of their jobs

The search was re-run on the real data, read-only. From each file it keeps only the job id, or the instance id and
the launch time. It found **nothing unlisted** for S1, S2 or P1a, and no scan failure.
- `typed_pointer_001/` at HEAD and at `1ddf6a1e`: 19 job ids. The only ones prepared on or after 2026-09-23 are S1's
  `cas-meta2-tpntr-20260924021244-70490111-m-20260917` and S2's `cas-meta2-tpntr-20260924033550-3df31d96-m-20260917`.
- The design folder: 12 launch and watch records, each seen on disk and at HEAD. `larger_question_t4_job/` holds
  only P1a's two records (`i-09e14d4afd0e0ebfa`, launched 2026-09-24T05:53:38Z).
- Git history (file names only) since 2026-09-23, on all 18 remote branches whose name contains `helm` (this one
  included; tips read with `git ls-remote`; tips missing locally were fetched) and on `master`: the only typed-pointer
  `result.json` files added are S1's (`5715fda0`, moved unchanged to `..._attempt1/` in `3df31d96`) and S2's
  (`1ddf6a1e`). P1a's two records were each added once (`fae817fe`, `b0fd06ff`). No other branch added a launch
  record in the design folder outside the three older job folders.

So **S1, S2 and P1a are the complete set of attempts of their jobs**. They are scanned, not exempt.

### Probes rebuilt

| Probe | Result now | Verdict |
|---|---|---|
| N6a | refusal 09:05 unlisted, clean run 09:15 named: M1 ACCEPTED $8.94 but UNCONFIRMED (`UNLISTED_TRAINING_ATTEMPT`); `--admit M2` exit 1 | FIXED |
| Two attempts listed (the ordered positive test) | refusal then clean run: ACCEPTED **$10.54** ($1.60 + $8.94); spent $15.98; no cleanup flag; `--admit M2` exit 0 ADMIT, total **$55.96** | as ordered |
| N6b | a 600-s attempt with its identity lost, unlisted: UNCONFIRMED; exit 1. Listed: REJECTED and UNCONFIRMED; exit 1 | FIXED |
| N6c | watched attempt still running, records in `p1b/attempt1/`, or in a new folder `p1b_try1/`: UNCONFIRMED (`UNLISTED_WATCHED_LAUNCH`); `--admit P2` exit 1 | FIXED |
| N6d | named refusal, unlisted 20,000-s attempt: ACCEPTED $1.60 but UNCONFIRMED; exit 1 | FIXED |
| N8 | after `merge -s ours`: plain `git log` sees 1 version, the gate's history 4; `check_history` raises `HISTORY_VIOLATION: M1 was DONE`. Remote tip: at the tip, True; after another clone pushes, `HEAD_IS_NOT_THE_REMOTE_TIP`; after `pull --ff-only`, True; remote gone, `FETCH_FAILED` | FIXED |
| N1a | INVALID naming another job's clean receipt: $11.66; UNCONFIRMED (`LAUNCHED_BEFORE_ADMISSION`); exit 1 | holds |
| N3 | INVALID naming an older capacity refusal: UNCONFIRMED; exit 1 | holds |
| N4 | bare record committed RUNNING: REJECTED (the window and the NOTE-F reasons); not started; exit 1 | holds |
| P4 | 20,000 s, identity lost, instance id empty, INVALID: $15.58; spent $21.02; `--admit P1b` exit 1 with `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` and `OVER_CEILING:$61.00 > $60.00` | holds |
| P6 | hand-written admission, never committed RUNNING: REJECTED (`ADMISSION_NOT_IN_A_COMMITTED_RUNNING_ROW`); exit 1 (`DONE_RECEIPT_REJECTED:M1`) | holds |

### New findings

**L. MINOR: the search for unlisted attempts misses three shapes of retry** (`unlisted_attempts`, lines 1258-1310).
The search is the safety net for an attempt the row leaves out. Each probe below leaves one out.

- **X2. A training retry prepared from a new source commit.** M1 is admitted at 09:00 with source `4444...`.
  Attempt 1 (09:05) is a capacity refusal, and the row names it. Attempt 2 (09:15) was prepared from `5555...`. It
  ran 20,000 s, and its machine's identity is lost. The row does not list it. The search looks only for the admitted
  source's first 8 characters, so it misses attempt 2. M1 is ACCEPTED at $1.60, with no cleanup flag. `--admit M2`
  gives **exit 0 ADMIT**, total $47.02. This is N6d with a new source.
  - Why this shape matters: the real retry had it. S2's source `3df31d96` is the commit that moved S1's receipt
    aside. The prepare scripts take the source from `git rev-parse HEAD`. So committing attempt 1's receipt in the
    preparing checkout changes the next attempt's source.
- **X3. The same prepared job launched twice.** Attempt 1 (job J) ran and lost its identity. Attempt 2 (the same
  job J) finished clean, and the row names it. The search skips every job id the row lists, so it skips J
  everywhere. `--admit M2` gives **exit 0**, total $54.36.
- **X1. A watched attempt committed at HEAD, then its folder reused.** P1b attempt 1 (09:05, still running) was
  committed in `p1b/`, then deleted from disk. Attempt 2 (09:45, clean) was launched into the same `p1b/`. The search
  skips any record whose path the row lists, so it skips attempt 1's copy at HEAD. `--admit P2` gives **exit 0**,
  total $55.63. Control: the same attempt 1 at HEAD under another path is found (exit 1).

Why MINOR, not MAJOR: each probe needs the runner to leave an attempt out of `attempts`. `PREREQUISITE_SLOTS.md`
says "Every attempt is listed in the row". Listed honestly, all three refuse (probes X2h, X3h, X1h):
- X2: `SOURCE_NOT_THE_ADMITTED_SOURCE`, UNCONFIRMED;
- X3: `RECEIPT_SHARED` on the job id (the "one receipt, one attempt" rule);
- X1: a pin mismatch, plus `RECEIPT_SHARED` on the instance id.
So a careful runner who follows the document cannot reach a wrongful ADMIT this way.

Fix (a suggestion; Codex decides):
- Training: match the seed and the window with **any** source prefix. A job another slot claims stays that slot's.
  (A job of the next slot inside this window is then flagged only until that slot's row names it.)
- Training: count a job id as listed only together with the listed receipt's own identity (its path or sha256),
  not the id alone.
- Watched: skip a scanned record only when its sha256 equals a listed pin, or its instance id is listed. Never skip
  it by path alone.
- Add X1-X3 as negative tests.

**M. MINOR: the documented retry stops the study for good when it is prepared the way the real retry was**
(`PREREQUISITE_SLOTS.md`, "Launch attempts and retries"; it fails closed).
- The runner action: commit attempt 1's receipt, as the document requires, in the checkout that prepares jobs. Then
  prepare the retry in that checkout. (`prepare_study.py` refuses a dirty tree, so the receipt must be committed or
  moved first.) The commit moves HEAD, and today's prepare scripts take the source from HEAD.
- Probe X2h: a refusal (admitted source) and a clean run (new source), both listed. M1 is REJECTED (`attempt 2:
  SOURCE_NOT_THE_ADMITTED_SOURCE`), counted $23.32, UNCONFIRMED. `--admit M2` gives exit 1. Both attempts are clean,
  yet the study stops, and nothing clears it.
- The round-4 positive test uses one source for both attempts. The real S1 -> S2 retry did not.
- No money is at risk: the gate refuses. But "a retry inside a live admission is allowed" holds only when the retry
  is prepared from a checkout that still sits at the admitted source commit. The document does not say so.
- Fix: say it in the document (prepare every attempt from the admitted source commit; commit receipts where they do
  not move that checkout's HEAD). Or decide it together with open question 8.

**N. NOTE: an attempt that made no machine, and is not an AWS capacity refusal, stops the study for good.** Probe
X5: a launcher preflight refusal (status `PREFLIGHT_REFUSED`, no launch) listed as attempt 1, then a clean run:
REJECTED, UNCONFIRMED, exit 1. Such receipts exist in the training receipt home
(`typed_pointer_001/receipt_20260917_preflight_refused_af0970cf/`; folder name only). Only a proven capacity refusal (the S1 rule) or a
confirmed termination can clear an attempt. This fails closed. Whether a proof that no AWS call was made should also
clear an attempt is for Codex or the owner.

**O. NOTE: `--admit` checks the current branch's upstream, not a named study branch.** The document says to run it on
the study's branch. Today only `research/helm-integration-20260923` carries `study_spend/` (checked on the local refs
`origin/claude/helm-on-launch-20260924` and `origin/master`). A copy of the slots file on another branch would have
its own tip. No change asked.

**Unchanged, as ordered.** NOTE J (a careful hand-written admission record passes) and NOTE K (watched slots bind by
launch time only; `validate_watched` passes no source or bundle to `not_this_launch`) stand as the builder states.
Open questions 6-9 stay open.

### Claim states

- **Real (measured here):** both test runs; the real report and its byte-identical state; the real reading and its
  byte-identical regeneration; the real attempt search for S1, S2, P1a; the file-name history on the branches named
  above; the file diffs; the remote-tip check on this checkout; probes N1a, N3, N4, N6a-N6d, the two-attempt positive
  case, N8, P4, P6, X1, X1h, X2, X2h, X3, X3h, X5.
- **Open:** Codex's review of rounds 1-4; open questions 1-9; findings L and M; notes N and O (FLAG_FOR_HUMAN_REVIEW
  for the design choices).
- **Verdict scope:** APPROVE_ADMISSION_GATE is this verifier's reading only. It is not Codex's review and not owner
  acceptance. It says nothing about the technical readiness of any slot; the gate does not check that.

### Exposure

Read: this file; `study_spend.py` (all of it); `test_study_spend.py` (helpers, the round-4 tests, the test list);
`PREREQUISITE_SLOTS.md` (the round-4 diff); `STUDY_SLOTS.json` (slot ids, statuses, caps, kinds, training seeds and
arms, receipt specs); `read_results.py` lines 283-300; `typed_pointer_001/prepare_smoke.py` lines 395-420 and
495-560, and a grep of it for `receipt`, `source_sha` and `rev-parse`; `typed_pointer_001/prepare_study.py` lines
80-130; the folder names of `typed_pointer_001/` and its `.gitignore`; a grep for `tpntr` in `.py` files; file-name
history for `typed_pointer_001/*result.json` and the design folder's launch records on the branches named above; the
fetch refspec, the upstream setting and `git ls-remote` branch names. The real report, the real reader and the real
attempt search read receipts and `results/` only through the programs. Printed were only summary lines, the route
and job verdicts, job ids with their file places, and each watched record's path, instance id and launch time. **No
receipt file was opened directly**, and no `ledger_before` / `ledger_after` field was read or printed. Network (git
only, read-only): `git pull --ff-only`; `git fetch origin` (it refreshed the three remote-tracking refs its refspec
lists); fetches of remote branch tips missing locally (`codex/helm-controlled-prelaunch-20260924`, `master`) into
`FETCH_HEAD`; `git ls-remote`; the
gate's own fetch inside `at_remote_tip()`. Wrote: this section only. Scratch (the session scratch folder): the probe
script and a regenerated state copy. The probes' temporary folders and the N8 repositories were deleted. The
untracked `aws_probe_job/dry_run_machine_script.sh` is not the verifier's and was left alone. No AWS call, no torch,
no model, no `*_eval.jsonl`, no sealed file, no `D:/tksCAS-archive/`, no salt, no S3, no meta1 ledger, no transcript,
no real `--admit`.

## v2 (Codex Q1-Q9)

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Builder: Claude (temporary builder). This implements the Codex decisions, read in
full at `c3a128ee` on `codex/helm-controlled-prelaunch-20260924`: `POLICY_DECISIONS_20260924.md` ("Spending decisions:
Q1-Q9", R3-F, "Envelope consequences") and `SPEND_STATIC_REVIEW_20260924.md` (findings 1 and 2). It is the builder's
own record, **not** an independent acceptance: Codex reviews these bounded changes next.

In plain words: the gate now allows exactly one machine launch per admission; a retry gets its own row and its own
admission. An admission is good for five minutes and one use, and a last check runs just before the launch. The search
for hidden launch attempts no longer trusts a job id, a source prefix or a file path alone. Every admission binds the
source, bundle, worker and checker, and a mismatch stops the study while the machine is still checked and paid for. A
job that broke a limit stops the study for good. Every main training run that started a machine counts toward the
owner's $30 stop. A never-used slot can be cancelled. The S1 rule is accepted. The earlier $1.9180 of preparation
spend is now counted, so plan C is **$59.00 with $1.00 to spare, and not final**.

### The prospectively reviewed schema revision (0.3 to 0.4)

Codex Q9 says: if the frozen schema cannot express one-attempt-per-admission and retry rows, retries are forbidden until
a prospectively reviewed schema revision exists. This is that revision, for review. It is implementation preparation;
no statistical rule changed.

| | Before (0.3) | After (0.4) |
|---|---|---|
| Slots schema | `claude.helm-repair-controlled-1.study-slots/0.3` | `.../0.4` |
| Frozen definitions digest | `82e809500f14ad8988b3b45ad6a7265f0601a5791f13cb8ea5a4608771456764` | `a9fed7896aab374c6c2ce994dfe697999e37c960366107a1532b7d66b1760ecb` |
| S1, S2, P1a rows | frozen whole | **byte-identical** (checked by the revision script) |
| Every row's status, receipt, admission, attempts | as committed | **unchanged** (checked) |
| P1b, P2, E1 rows; every cap, basis, seed, arm, flag; the $60 / $30 / $0.10 constants | as committed | unchanged |
| M1-M6 `preconditions_outside_money_gate` and note | the builder's list | **Codex's Q5 list** (below) |
| New rows | none | **PRIOR** (frozen whole; R9) |
| New list | none | `attempt_rows: []` (append-only state, outside the digest; R1) |
| `open_questions_for_owner_or_codex`, `owner_stop.rule` and `.counting`, `about` | open questions 1-5 | rewritten as decided or open, with the Codex source |
| New statuses | none | `CANCELLED_NOT_LAUNCHED` (R7), `CLOSED_NO_LAUNCH` (R1, R5) |

The committed history check still passes against every earlier 0.3 version.

### Disposition

| Rule | What was decided | Done | Test |
|---|---|---|---|
| R1 (Q9 + finding 1) | one admission = one RunInstances attempt; a retry is a new attempt row with its own cap reserved and its own fresh admission; an expired unused admission is closed with proof of no launch and reissued, never rewritten as PLANNED | `attempt_rows` (id `<slot>.<n>`, the slot's frozen definition); a second attempt under one admission is a latched breach; a row may be appended only after the previous attempt is settled; `CLOSED_NO_LAUNCH`; RUNNING to PLANNED is `HISTORY_VIOLATION` | `test_v2_r1_one_admission_one_attempt_a_retry_needs_its_own_row_and_admission` |
| R2 (R3-F) | recompute under a single-writer lock immediately before each attempt; valid 5 min, single use; expiry, another attempt, a changed input or a lost lock needs a fresh check; the record binds inventory hash, gate version, cap, remaining reserve, cumulative bound, main starts, launch identity | `ADMISSION.lock`; the admission record's binding fields; `--launch-check`; the receipt's launch time must lie in the 300-s validity | `test_v2_r2_an_admission_is_recomputed_under_a_lock_valid_300_s_and_single_use` |
| R3 (finding 2 / L, Q8) | any source prefix; listed only by path AND sha256; watched skipped only by a pinned sha256 or a listed instance id; reconcile HEAD and disk | the search rewritten; X1, X2, X3 | `test_v2_r3_x1_...`, `test_v2_r3_x2_...`, `test_v2_r3_x3_...` |
| R4 (Q8) | bind source, bundle, worker, checker for watched and training; wrong source: result INVALID, admissions blocked, cleanup still inspected, true cost counted | `IDENTITY_FIELDS`; `IDENTITY_NOT_THE_ADMITTED` rejects at DONE; `WRONG_IDENTITY_BLOCKS_THE_STUDY`; the source left the "not this launch" test | `test_v2_r4_source_bundle_worker_checker_are_bound_and_a_mismatch_blocks_but_cleanup_is_inspected` |
| R5 (Q4) | a limit breach blocks all further admissions, latched, even after cleanup; a prelaunch tool failure with proof of no instance does not | `LIMIT_BREACH_LATCHED`; `CLOSED_NO_LAUNCH` with an optional pinned `pointer_prelaunch_failure` receipt | `test_v2_r5_a_limit_breach_latches_the_study_but_a_prelaunch_failure_with_no_instance_does_not` |
| R6 (Q3/Q6) | count every main attempt that started an instance, failed or repeated, no reset; a proven refusal does not count; an uncertain start blocks; the $30 stop before every admission while fewer than 3 have started, latched; smoke and prerequisites never count, their costs do | the started rule; `MAIN_START_UNCERTAIN` | `test_v2_r6_every_started_main_attempt_counts_and_the_stop_stays_latched` |
| R7 (Q7) | `CANCELLED_NOT_LAUNCHED`, append-only, with evidence; releases optional reserve only; a cancelled mandatory row makes the comparison incomplete and blocks main admissions | as decided; the mandatory cap stays reserved | `test_v2_r7_cancelled_not_launched` |
| R8 (Q1) | the S1 accounting rule is accepted, conditional on its pinned provider failure evidence; record which evidence resolves the launcher's flag | the override now says ACCEPTED and names the evidence in `override_resolved_by` | `test_v2_r8_the_s1_rule_is_accepted_and_names_its_provider_evidence` |
| R9 (envelope) | include the earlier $1.9180 as DONE rows or one conservative row, pending the owner; print plan C's bound and headroom; do not call $57.08 final | one row, PRIOR ($1.92); `plan_C_is_final: false` and why | `test_v2_r9_the_prior_spend_row_and_plan_c_bound` |
| Q5 | M1-M6 preconditions are Codex's list, declared, checked by the technical admission, not the money gate | the lists and note replaced | `test_v2_q5_main_preconditions_are_the_codex_list_printed_and_not_checked_by_the_money_gate` |

### R1: one admission, one attempt; retries are attempt rows

- A row that lists more than one attempt under one admission is now a **latched breach**
  (`MORE_THAN_ONE_ATTEMPT_UNDER_ONE_ADMISSION`). The round-4 positive test (a refusal then a clean run, both listed) is
  still counted at **$10.54**, but `--admit M2` now gives **exit 1** `LIMIT_BREACH_LATCHED:M1` (round 4 admitted it at
  $55.96). The `attempts` field stays only so such a violation is counted and visible.
- A retry is `{"id": "M1.2", "slot": "M1", "attempt": 2, ...}` in `attempt_rows`. The program expands it into a row with
  M1's frozen cap, basis, seed, arm and flags, so every existing check applies to it. Test: M1's attempt 1 was a
  capacity refusal ($1.60); M1.2 is reserved while PLANNED (reserve **$51.64**); `--admit M1.2` gives **exit 0**,
  total **$58.68** ($7.04 + $11.66 + $39.98), and the arithmetic names "the replacement cap of attempt 2 of M1".
- An attempt row before the previous attempt is settled, or with the wrong number: exit 2. Removing a committed attempt
  row: exit 2 (append-only). A retry while an earlier attempt's cleanup is unconfirmed: exit 1.
- An unused admission closed as `CLOSED_NO_LAUNCH` with no launch in its window: $0.00, no cleanup flag, and
  `--admit M1.2` exit 0. With a launch found in its window: $11.66 and `UNCONFIRMED`. RUNNING rewritten as PLANNED:
  exit 2 `HISTORY_VIOLATION: M1 was RUNNING ... never rewritten as PLANNED`.

### R2: the five-minute, single-use admission under a lock

- `--admit` takes `ADMISSION.lock` (created exclusively beside the slots file), recomputes the whole account, and on
  ADMIT keeps the lock (state `ADMITTED`); on a refusal or an error it releases the lock it took. A lock held by an
  open admission, or by another gate process, refuses (`LOCK_HELD`). A lock left by an admission whose row is settled
  is released by the next `--admit`.
- The record binds: `valid_until_utc` = admission + 300 s; `inventory_sha256` (one hash over the gate version, the
  program, the canonical pre-admission slots document and the whole recomputed account); `gate_version`, `cap_usd`,
  `remaining_mandatory_reserve_usd`, `cumulative_upper_bound_usd`, `main_starts`, `lock_nonce`, and the launch
  identity (source, bundle, worker, checker; seed and arm for training). A record without these fields is refused
  (`ADMISSION_RECORD_MISSING_BINDING`).
- `--launch-check` recomputes the pre-admission state (the row put back as it was before `--admit` wrote it) and
  compares its inventory hash. Test on P1b admitted at 12:00:00: at 12:04:59 `LAUNCH_ONCE` (exit 0), and the lock
  becomes `LAUNCH_CHECKED`; a second check `ADMISSION_ALREADY_USED`; at 12:05:00 `ADMISSION_EXPIRED`; lock deleted
  `LOCK_LOST`; P1a's watch record changed after the admission `INPUT_CHANGED`. A second `--admit` while the lock is
  held: `LOCK_HELD:P1b`, and the lock stays.
- The receipt binding stays, with the 300-s window: a P1b launch at 09:05:00 on a 09:00:00 admission is
  `LAUNCHED_AFTER_THE_ADMISSION_VALIDITY` and `UNCONFIRMED`. The search for unlisted attempts still uses the lifetime
  window, so a launch after the validity is still found.

### R3: the unlisted-attempt search (finding L; the verifier's X1, X2, X3)

| Probe | Round 4 (the verifier) | Now |
|---|---|---|
| X2: retry prepared from a new source (5555...), ran 20,000 s, identity lost, unlisted; the row names a refusal | ACCEPTED $1.60; `--admit M2` **exit 0**, $47.02 | `UNLISTED_TRAINING_ATTEMPT:cas-meta2-tpntr-20260924091500-55555555-m-20260917`; **exit 1** `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` |
| X3: the same job J launched twice; attempt 1 lost its identity; attempt 2 named | **exit 0**, $54.36 | attempt 1's `r/m1_attempt1/result.json` is found (not listed by path and sha256); **exit 1** |
| X1: P1b attempt 1 committed at HEAD in `p1b/`, deleted from disk; attempt 2 in the same `p1b/`, named | **exit 0**, $55.63 | `UNLISTED_WATCHED_LAUNCH:p1b/launch_record.json instance i-p1b-0901 launched 2026-09-24T09:01:00Z (HEAD)`; **exit 1** |

"Listed" now means: the listed receipt by its own path and pinned sha256, and the sibling records (`provider_NNNN.json`,
`*_result.json`) in the listed receipt's folder at the listed commit, by their own path and sha256. The siblings are
needed: every training receipt folder holds many provider records that carry the same job id (S2's folder holds 26).
S1 and S2 keep their own-source search with no window (they have no admission); on the real data the search still finds
nothing unlisted.

### R4: identity binding

- `--admit` requires `--source`, `--bundle`, `--worker`, `--checker` for every slot. The receipt must show the same
  values at `IDENTITY_FIELDS` (training: `authority.source_sha`, `authority.archive_sha256`, `authority.worker_sha256`,
  `authority.checker_sha256`; watched: `identity.source_commit`, `bundle.sha256`, `identity.worker_sha256`,
  `identity.checker_sha256`).
- A mismatch or a missing value: `IDENTITY_NOT_THE_ADMITTED` (rejected at DONE) and `WRONG_IDENTITY_BLOCKS_THE_STUDY`
  (every admission refused). The cleanup check still inspects the actual machine: M1 with another worker, INVALID, has
  no cleanup flag, is counted $11.66 and still counts as a main start. This reverses the round-3 choice that made a wrong
  source `UNCONFIRMED` forever (open question 8, decided).
- Watched rows now bind source and bundle too, not only the launch time (NOTE K, decided).

### R5: limit breaches latch

- The round-2 probe P1 (P1b ran 240 min, watcher $3.0719, cleanup confirmed, INVALID) is still counted $3.18, but
  `--admit P2`, `M1` and `E1` now each give **exit 1** `LIMIT_BREACH_LATCHED:P1b` (round 1-4 admitted P2 at $58.26). A
  training job past 14,400 s with its cleanup confirmed latches too (`ELAPSED_OVER_BASIS`).
- A `CLOSED_NO_LAUNCH` row whose pinned prelaunch-failure receipt shows no launch, no instance, and no `run_instances`
  provider record in its folder: $0.00, no latch, no cleanup flag, not a main start; `--admit M2` exit 0. With a
  `run_instances` record in that folder: not proven, $11.66, `UNCONFIRMED`.
- The "update limit" (optimizer updates) is **not** checked: no receipt field for the observed update count is read.

### R6: main starts and the $30 stop

- M1 with a rejected receipt (another schema) and M2 INVALID after a failed job, both with a launched instance: both
  count (round 4 counted neither). A refusal that is not proven (a later provider call): `MAIN_START_UNCERTAIN:M3`,
  exit 1.
- M1 and M2 at 14,400 s ($23.32) + S1, S2, P1a ($5.44) + a $2.00 prior row = **$30.76** with 2 starts: `--admit M3`,
  `P1b`, `E1` all `OWNER_STOP_TRIGGERED`; after M2 moves to INVALID and a retry row M2.2 is appended, `M2.2` and `M3` are
  still refused.
- Latching rests on this: the stop is decided with nothing RUNNING, and settled rows only move forward (DONE to INVALID
  never lowers a count; a cancelled or new PLANNED row adds $0; the start count never falls). A report taken while a job
  is RUNNING counts that job at its full cap and may show the stop; nothing can be admitted then anyway.

### R7, R8, R9, Q5

- **R7.** Cancelling optional M5: $0.00, it leaves fallback B, `--admit M1` exit 0. Cancelling mandatory M4: reserve
  still **$51.64**, `COMPARISON_INCOMPLETE:M4` refuses `--admit M1`, while `--admit E1` (the partial-study readout) gives
  exit 0. A cancelled row with an admission: exit 2. A committed RUNNING row made CANCELLED: exit 2. No evidence: exit 2.
- **R8.** S1's pins now read "ACCEPTED (Codex Q1, POLICY_DECISIONS_20260924.md at c3a128ee) conditional on the pinned
  provider failure evidence", and `override_resolved_by` names `provider_0025.json` (sha256
  `d866fbf594c76b09e591dbd96c6df0ecc712386d54d37e34ef21ca4be2da2b33`, `run_instances`, `FAILED`,
  `InsufficientInstanceCapacity`), that it is the last provider record at `1ddf6a1e`, the receipt's outcome (zero client
  retries) and its cleanup. A changed provider record voids the rule and S1 becomes `UNCONFIRMED`.
- **R9.** PRIOR: analogy_repair_t4_job $0.5596 + $0.67, aws_probe_job $0.4834, hset1a_aws_job $0.0223 + $0.1827 =
  $1.9180, rounded up to **$1.92**. No $0.10 allowance is added (Codex's arithmetic); with it, plan C would be $59.50.
  Frozen whole; not validated by this program; its cleanup not re-checked here; scope pending the owner.
- **Q5.** M1-M6 now list Codex's common conditions (P2's feasibility / exposure receipt, corrected mechanism
  validation, eighteen checkpoint checks, both-arm route acceptance, the frozen source / data / starting values / worker
  / checker / environment, reader AWS acceptance, complete all-services reserves, the current single-use technical and
  spending admissions). M2-M4 need M1's completed VALID reproduction verdict, not "M1 was admitted first". M5 and M6 need
  the valid-mismatch predicate, reviewed B admissions and funding within $60, not an owner approval token. The note says
  they are checked by the technical admission, not the money gate, and that a status label proves nothing without its
  receipts.

### Existing tests whose expectations changed (because a decided rule changed them)

- The test world's job times and watched launches moved inside the 300-s validity (09:01:SS; 09:02:00). No money figure
  changed.
- `test_round4_two_attempts_...` (renamed `..._under_one_admission_are_counted_and_now_latch_the_study`): exit 1, R1.
- `test_round2_p1_...`: the same decision as its twin, now exit 1 `LIMIT_BREACH_LATCHED:P1b`, R5.
- `test_round2_a_proven_capacity_refusal_...` (wrong source) and `test_round3_launch_window_...` (the other arm's
  source): cleanup confirmed, wrong identity blocks, R4.
- `test_rejected_or_invalid_training_never_counts_as_started`: **removed**; its rule is the one Codex Q3/Q6 reversed
  (replaced by `test_v2_r6_...`).
- Needles renamed: `LAUNCH_AFTER_THE_ADMISSION_LIFETIME` to `..._VALIDITY`; `SOURCE_NOT_THE_ADMITTED_SOURCE` and
  `BUNDLE_NOT_THE_ADMITTED_BUNDLE` to `IDENTITY_NOT_THE_ADMITTED:<field>`. The S1 override test reads "ACCEPTED".

### Mutation check (scratch script, not committed)

Each rule was switched off, one at a time, in a temporary copy of `study_spend.py`; the eleven rule tests ran each time.

| Switched off | Rule tests that fail |
|---|---|
| nothing (as written) | none |
| R1: a second attempt under one admission not a breach | r1 |
| R1: attempt rows not reserved | r1 |
| R1: attempt row allowed before the previous attempt settles | r1 |
| R2: validity back to 14,400 s | r2 |
| R2: single use off / inventory check off / expiry check off / lock never held | r2 (each) |
| R3: admitted source prefix only | x2 |
| R3: a listed job id skipped everywhere | x3 |
| R3: watched records skipped by path | x1 |
| R4: identity not checked / a wrong identity does not block | r4 (each) |
| R5: money and time breaches both off | r5 (run by hand: the script's first rewrite of this switch did not apply; with only the money half off, the time codes still catch both test cases) |
| R5: a closure ignores a RunInstances record | r5 |
| R6: only accepted receipts count as started | r4, r6 |
| R6: an uncertain start does not block | r6 |
| R7: a cancelled mandatory row does not block / its cap released | r7 (each) |
| R8: the rule still CLAUDE_PROPOSED | r8 |
| R9: the prior row counted at zero | r6, r9 |

### Checks run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `git pull --ff-only` | already up to date; tip `a98221dd` |
| `python -B test_study_spend.py` (final run, once) | **80 passed, 0 failed** (69 before: 1 removed, 12 added) |
| `python -B test_read_results.py` (once) | **31 passed, 0 failed** (unchanged file) |
| Mutation check | the table above |
| Real report (`main([])`, state written to a scratch file, then installed as `STUDY_SPEND_STATE.json`) | **exit 0; spent upper bound $7.36** (S1 $1.60, S2 $3.29, P1a $0.55, PRIOR $1.92); remaining mandatory caps **$51.64**; **plan C $59.00, headroom $1.00, `plan_C_is_final: false`**; $59.50 with the prior allowance; fallback B +$23.32 does not fit (M5 would total $70.66); nothing rejected, shared, unconfirmed, latched or uncertain; no main start; sensitivity S1 $69.06, S2 $67.37, P1a $61.45; about 2 s |
| Real `--admit` / `--launch-check` | **not run** |

### Limits, stated honestly

1. **Today's launchers do not write `worker_sha256` or `checker_sha256`.** Every receipt from them fails R4. Each
   launcher used for P1b, P2, E1 and M1-M4 must add both fields where `IDENTITY_FIELDS` reads them, or the gate stops
   the study. The same holds for a job prepared from HEAD instead of the admitted source (finding M; Codex Q9: the
   scripts must accept the admitted source).
2. **A training receipt shows no launch time,** only the time its job id was prepared. So the runner must admit, commit
   and push, prepare, run `--launch-check`, and launch, all inside 300 s. Codex R3-A puts preparation before admission;
   that order needs the training launcher to record its RunInstances time first. Open.
3. **`--launch-check` is a runner step.** The gate cannot prove a launcher called it; the receipt's launch time inside
   the validity is the evidence it can bind afterwards. Wiring it into the launchers is open.
4. **The lock is a file in one checkout.** Across machines, the fetched-remote-tip check and the push race are the
   single-writer guard (round 4).
5. **`CLOSED_NO_LAUNCH` proof is the program's search** of the admission window (git and the working tree), plus an
   optional pinned prelaunch-failure receipt. It is not a provider query.
6. **S1 and S2 keep their own-source search**, because they have no admission window; their completeness rests on the
   round-4 verifier's full history search.
7. **PRIOR is declared, not validated**, and its jobs' cleanup is not re-checked here.
8. **Not changed here:** P1b's price (Codex: g7, not T4), E1's real scope, retention beyond 12 months, the canonical
   campaign cap, the technical admission itself.

### Claim states

- **Real (measured here):** the test runs; the mutation check; the real report and its numbers; the schema revision's
  byte checks on S1, S2, P1a and every row's mutable state.
- **Open:** Codex's review of v2; the launcher and runner items in limits 1-3 (open item 10 in `STUDY_SLOTS.json`);
  open question 1 (PRIOR's scope) and 5 (retention).
- **Not licensed:** any statement that the gate is ready for a real `--admit`, before Codex's review and before the
  launchers write the bound hashes.

### Exposure

Read: Codex `POLICY_DECISIONS_20260924.md` and `SPEND_STATIC_REVIEW_20260924.md` at `c3a128ee` (fetched read-only);
this file (rounds 4 and the round-4 verification); `study_spend.py`; `test_study_spend.py`; `PREREQUISITE_SLOTS.md`;
`STUDY_SLOTS.json`. A scratch script printed only the **key names** (not values) of S2's `result.json` at `1ddf6a1e`
(its `ledger_before` / `ledger_after` keys were skipped, never printed or inspected) and of P1a's
`launch_record.json`; the file names in S2's receipt folder; and the key names, operation and state of three of S2's
provider records. `grep` over `typed_pointer_launch.py` for launch-time fields. The real report read receipts only
through the program; it printed summary lines only. Wrote: `study_spend.py`, `test_study_spend.py`, `STUDY_SLOTS.json`
(the 0.4 revision, by a script that asserted S1/S2/P1a and every mutable field unchanged), `STUDY_SPEND_STATE.json`
(program output, not hand-edited), `PREREQUISITE_SLOTS.md`, this section. Scratch only (the session scratch folder):
the revision script, the edit scripts, the mutation scripts and their temporary copies, the scratch state. Not written:
`CHANGELOG.md` (the coordinator batches it), any job code or launcher. The untracked
`aws_probe_job/dry_run_machine_script.sh` is not the builder's and was left alone. No AWS call, no torch, no model, no
`*_eval.jsonl`, no sealed file, no `D:/tksCAS-archive/`, no salt, no S3, no meta1 ledger, no transcript, no real
`--admit`.

## Conformance check of d5c8184a5e293316e12eb1506520a8f8649af362

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Checker: Claude, a fresh checker (not the builder), 2026-09-24. Scope: conformance
of `d5c8184a` to rules R1-R9 and the Q5 list only, as decided by Codex at `c3a128ee` (`POLICY_DECISIONS_20260924.md`
"Spending decisions: Q1-Q9", R3-F, "Envelope consequences"; `SPEND_STATIC_REVIEW_20260924.md` findings 1 and 2, both
read in full). For each rule I built my own synthetic cases: at least one the rule must refuse and one it must allow.
No search for new attack classes beyond the rules.

**Verdict: CHANGES_REQUIRED, rule R3.** Every other rule and the Q5 list conform.

In plain words: the gate does what the decided rules say, with one exception. The search for hidden launch attempts
still skips a hidden attempt when its receipt is stored inside the folder of the receipt the row does list. R3 says a
file counts as listed only by the listed receipt's own path AND sha256 (its fingerprint). This file has neither, and it
carries a different job id. The gate then admits the next job. It must refuse.

### What was run (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `git pull --ff-only` | already up to date; HEAD `d5c8184a` = fetched remote tip |
| `python -B test_study_spend.py` (once) | **80 passed, 0 failed** |
| Real read-only report (`python -B study_spend.py --no-write`) | **exit 0**; spent upper bound **$7.36** (S1 $1.60, S2 $3.29, P1a $0.55, PRIOR $1.92); remaining mandatory caps **$51.64**; plan C **$59.00**, headroom **$1.00**, `plan_C_is_final: false`; fallback B +$23.32 does not fit; nothing rejected, shared, unconfirmed, latched, wrong-identity or uncertain; no main start; money-gate previews ADMIT for P1b, P2, M1-M4, E1 and REFUSE `OVER_CEILING:$70.66` for M5, M6 |
| Schema revision byte check (old `a98221dd` against new `d5c8184a` `STUDY_SLOTS.json`) | schema `0.3` to `0.4`; the S1-S2-P1a text span is byte-identical (4,126 bytes, same sha256 in both); P1b, P2, E1 identical; M1-M6 differ only in `preconditions_outside_money_gate` and `preconditions_note`; PRIOR added; `attempt_rows: []`; no status changed |
| My synthetic cases (scratch script, temporary folders, the test file's fake git; not committed) | **32 cases: 30 right decisions, 2 wrong (both R3)** |

### Rule by rule

| Rule | Must refuse (my case, decision) | Must allow (my case, decision) | Conforms |
|---|---|---|---|
| R1 | M1 lists two finished attempts under one admission; `--admit P1b`: exit 1 `LIMIT_BREACH_LATCHED:M1`. Retry row M4.2 while the closed M4 admission has a launch in its window: exit 1 `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M4`. A `CLOSED_NO_LAUNCH` row edited back to PLANNED: exit 2 `HISTORY_VIOLATION` | M3 attempt 1 a proven capacity refusal; retry row M3.2 `--admit`: exit 0, $7.04 + $11.66 "replacement cap of attempt 2 of M3" + $39.98 = $58.68 | yes |
| R2 | After P1b's admission: a new launch record appears on disk, then `--launch-check`: exit 1 `INPUT_CHANGED`. The program file changed: `PROGRAM_CHANGED`. A second launch check 10 s after the first: `ADMISSION_ALREADY_USED`. `--admit` while another process holds the lock in state DECIDING: `LOCK_HELD`, lock left in place | `--launch-check` 30 s after the admission: exit 0 `LAUNCH_ONCE`; the record carries `inventory_sha256`, `gate_version`, `cap_usd` 2.00, `remaining_mandatory_reserve_usd` 49.64, `cumulative_upper_bound_usd` 5.44, `main_starts` 0, source/bundle/worker/checker, `valid_until_utc` = admission + 300 s, `lock_nonce` | yes |
| R3 | **See the finding below: two cases give exit 0 where the rule must refuse.** These refuse correctly: an unlisted attempt with another source prefix at HEAD only under the receipt home (exit 1); a watched record at the listed path at HEAD with another sha256 and instance id (exit 1). The builder's X1, X2, X3 tests pass | M1's listed receipt with three of its own provider records (same job id) in its folder: `--admit M2` exit 0 | **no** |
| R4 | M1 training receipt with another bundle (`archive_sha256`), INVALID: exit 1 `WRONG_IDENTITY_BLOCKS_THE_STUDY:M1`, and its cleanup is still confirmed, it is counted $11.66 and counted as a main start. P1b watched receipt with another checker: exit 1, rejected and blocking | P1b with all four admitted hashes: `--admit P2` exit 0; `--admit P2` without `--checker`: exit 2 | yes |
| R5 | P2 ran on a 200 GB disk (basis 100 GB), terminated, INVALID: `--admit M1` exit 1 `LIMIT_BREACH_LATCHED:P2` (`DISK_OVER_BASIS`) with cleanup confirmed. P1b's watcher recorded $2.50 on a $2.00 cap: `LIMIT_BREACH_LATCHED:P1b` (`MONEY_OVER_CAP:$2.60`) | M3 `CLOSED_NO_LAUNCH` with a pinned prelaunch-failure receipt and no RunInstances call: $0.00, no latch, `--admit P1b` exit 0 | yes (update limit: NOTE 1) |
| R6 | M1 launched then failed (INVALID) and its repeat M1.2 finished; with a $5.00 prior row the spend is $31.04; starts = `M1, M1.2`; `--admit M2`: exit 1 `OWNER_STOP_TRIGGERED` | M1, M2, M3 all started, spend $40.42: `--admit M4` exit 0, total $57.08, owner stop "not triggered" (3 of 3 started; the $60 ceiling still applies) | yes |
| R7 | Mandatory M2 cancelled: `--admit M3` exit 1 `COMPARISON_INCOMPLETE:M2`, reserve still $51.64. A cancelled mandatory retry row M1.2: `--admit M2` exit 1 `COMPARISON_INCOMPLETE:M1.2` | Optional M5 cancelled: it leaves fallback B, reserve unchanged $51.64, `--admit M2` exit 0 | yes |
| R8 | S1's folder shows a later provider call (`provider_0026.json`): the rule fails, S1 `UNCONFIRMED`, `--admit P1b` exit 1 | S1 counted $1.60; the override reads ACCEPTED (Codex Q1) and `override_resolved_by` names `provider_0025.json` and its pin; the real report shows S1 $1.60 | yes |
| R9 | A temporary copy of the real slots file with PRIOR removed, or with a PRIOR item set to $0.00: `SLOT_DEFINITIONS_CHANGED` (exit 2 path) | The real file: PRIOR $1.92 (items sum $1.9180), the frozen digest holds; the real report prints plan C $59.00 and headroom $1.00, not final | yes |
| Q5 | Not a money-gate refusal by design: the list is declared and belongs to the separate technical admission (not built) | The real M1-M6 lists hold every Codex Q5 item; M2-M4 need M1's completed VALID reproduction verdict (the bare "M1 was admitted first" item is gone); M5/M6 need the valid-mismatch predicate, reviewed B admissions and funding within $60, "not a new owner approval token"; the note says both gates run and a status label proves nothing without its receipts. `--admit M1` on money alone prints the list | yes |

### Finding (CHANGES_REQUIRED): R3, a hidden attempt inside the listed receipt's folder counts as listed

- **Case 1.** M1 admitted 09:00. Attempt 1 (job `...-20260924090100-44444444-m-20260917`) ran 600 s and lost its
  instance identity; its receipt is at `r/m1/attempt1/result.json`. Attempt 2 (job `...-20260924090300-...`) finished
  clean at `r/m1/result.json`, and the row lists only attempt 2. `--admit M2`: **exit 0** (no cleanup flag on M1). The
  rule requires a refusal: this file is not the listed receipt's path, not its sha256, and not even its job id.
- **Case 2.** The same, with attempt 1's receipt renamed `r/m1/attempt1_result.json` beside the listed receipt:
  **exit 0**. Must refuse.
- **Control.** The same attempt one folder over (`r/m1_attempt1/result.json`) is found: M1 `UNCONFIRMED`, exit 1.
- **Why.** The search does find the hidden job id. But `listed_files` (`study_spend.py:1500-1517`) counts as listed
  EVERY training-named file under the listed receipt's folder at the listed commit, by its own path and sha256. The
  folder listing is recursive (`tree_files` uses `git ls-tree -r`, line 628), and no check compares the file's job id
  with the listed receipt's job id. `unlisted_attempts` then drops the hit (`(path, digest) in own`, lines 1575-1576).
  My probe printed `counted as listed: ['r/m1/attempt1/result.json', 'r/m1/result.json']`.
- **Smallest fix that meets the rule.** Count a sibling as listed only when (a) it is a `provider_NNNN.json` directly in
  the listed receipt's folder (not in a subfolder), and (b) every job id it carries equals the job id of the listed
  receipt as read from its pinned, hash-verified copy. Never count any other `result.json` or `*_result.json` as
  listed unless it is the listed receipt itself (path AND sha256). S2's 26 provider records still pass (they carry S2's
  own job id). Add cases 1 and 2 as negative tests.

### Notes (not the reason for the verdict)

1. **R5 "update" limit.** The latch fires for every limit this gate admits (money cap, instance seconds, deadline,
   disk, machine) and for a second attempt under one admission. No update (optimizer-step) limit is admitted or read,
   as the builder's own record says. It is empty in this gate, not wrong; Codex to say whether the technical
   admission owns it.
2. **A closed mandatory admission with no retry row frees its reserve.** Outside the literal rule text; recorded for
   Codex, not required. With a $4.00 prior row, `--admit P1b` is refused at $61.08. After M1's unused admission is
   closed `CLOSED_NO_LAUNCH` (no M1.2 appended yet), `--admit P1b` is admitted at $49.42: M1's $11.66 is no longer
   reserved, and the comparison is not marked incomplete. The $60 ceiling itself still holds on every admission.

### Claim states

- **Real (measured here):** the 80/0 test run; the real report's numbers; the byte check of the schema revision; the
  32 synthetic decisions (30 right, 2 wrong, both R3).
- **Open:** the R3 fix and its two negative tests; Codex's review of v2; NOTES 1-2.
- **Not licensed:** any real `--admit`; any claim that the unlisted-attempt search is fail-closed before the R3 fix.

### Exposure

Read: `POLICY_DECISIONS_20260924.md` and `SPEND_STATIC_REVIEW_20260924.md` at `c3a128ee` (`git show`, read-only);
`study_spend.py`, `test_study_spend.py`, this file's v2 section, `STUDY_SLOTS.json` at `a98221dd` and `d5c8184a`
(through a script that printed row ids, statuses, changed key names, the PRIOR row, `owner_stop`, and the M1/M2/M5
precondition lists). The real report read receipts only through the program and printed its summary lines only; no
receipt was opened directly, and no `ledger_before` / `ledger_after` field was printed or inspected. Ran: the test file
once; the real report once with `--no-write` (no state file written, no lock taken, no fetch); a scratch script of
synthetic cases (temporary folders, fake git; it read the real `STUDY_SLOTS.json` only to check Q5 and R9, never wrote
it). Wrote: this section only. Scratch only (session scratch folder, not committed): the case script and this
section's draft; two temporary copies of the slots file, deleted. The untracked
`aws_probe_job/dry_run_machine_script.sh` is not mine and was left alone. No AWS call, no torch, no model, no
`*_eval.jsonl`, no sealed file, no `D:/tksCAS-archive/`, no salt, no S3, no meta1 ledger, no transcript, no real
`--admit`, no `--launch-check` on the real slots file.

## Builder fix of the R3 finding (conformance check of d5c8184a)

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Builder: Claude, the temporary builder, 2026-09-24. Scope: the one MAJOR finding
(R3) of the conformance check above. The two NOTES are not rule non-conformances; they go to the after-run backlog
below. `STUDY_SLOTS.json` is unchanged (no schema change, frozen digest unchanged); `STUDY_SPEND_STATE.json` changes
only its `gate_version` line.

**What was wrong, in plain words.** The search for hidden launch attempts treated every result-named file anywhere
inside the listed receipt's folder as "listed" (already accounted for), whatever job it belonged to. So a hidden
attempt's receipt stored in that folder, or in a subfolder of it, was never found, and the gate admitted the next job.

**What changed (`study_spend.py`, `listed_files`; gate version now `v2.1`).** A file counts as listed only when it is
the listed receipt itself (its path AND pinned sha256). Beside it, in its folder at the listed commit, and only when
that commit's copy of the receipt has the pinned sha256 and exactly one job id, two kinds of file also count:

- (a) a `provider_NNNN.json` directly in that folder (not a subfolder) whose job ids are exactly the receipt's job id
  (the checker's suggested fix);
- (b) a file whose sha256 equals the worker-result pin the receipt itself carries (`collected.result_sha256`).

Every other `result.json` or `*_result.json` never counts, and a job id alone never makes a file listed.

**Why (b), a deviation from the checker's suggested fix.** I first built the suggested fix exactly (only (a)). The
tests passed, but the real read-only report then gave **exit 1**: S2 `UNCONFIRMED`, every money-gate preview
`REFUSE CLEANUP_UNCONFIRMED_STOP_AND_REPORT:S2`. The search found S2's own job id
(`cas-meta2-tpntr-20260924033550-3df31d96-m-20260917`) in two more files in S2's folder at `1ddf6a1e`:
`curriculum_result.json` and `collected/results/result.json`. The checker's note "S2's 26 provider records still
pass" was right about the 26 provider records, but these two files are not provider records. What they are (checked
by a script that printed booleans only): S2's receipt at `1ddf6a1e` has the pinned sha256, and both files' sha256
equals the `collected.result_sha256` that receipt pins. They are byte-identical copies of S2's own worker result.
The launcher writes both into every receipt folder (`graph_training_curriculum_launch.py`, `_collect_declared`:
`curriculum_result.json`; `collected/` tree). So with (a) alone, every future M1-M4 row would also block the study
because of its own output. Rule (b) keeps R3's substance: such a file is listed by a sha256 that the pinned receipt
itself pins, never by its job id. A hidden attempt's launcher receipt has other bytes, so it is still found (tested,
including one with the SAME job id in a subfolder). **Open for the next checker / Codex:** accept or reject (b).

### Results (laptop, pure Python, one at a time; no AWS call, no torch, no model)

| Check | Result |
|---|---|
| `python -B test_study_spend.py` | **81 passed, 0 failed** (80 before, plus the new test) |
| New test `test_v2_r3_a_hidden_attempt_inside_the_listed_receipts_folder_is_found` run against the old program `d5c8184a` | **fails**, as it must (the old program counted the hidden attempt as listed) |
| Checker's case 1: hidden attempt at `r/m1/attempt1/result.json`, `--admit M2` | was exit 0; now **exit 1** `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` |
| Checker's case 2: hidden attempt at `r/m1/attempt1_result.json`, `--admit M2` | was exit 0; now **exit 1** `CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1` |
| Checker's control: `r/m1_attempt1/result.json`, `--admit M2` | **exit 1** (unchanged, correct) |
| Also in the test: a provider-named file beside the receipt with attempt 1's job id; attempt 1 with the SAME job id as the listed receipt in `r/m1/attempt1/`; a worker-result copy with one byte changed | each **found**, `--admit M2` exit 1 |
| Controls in the test: 3 provider records with the listed job id beside the receipt, plus the two worker-result copies the receipt pins | not findings; `--admit M2` **exit 0** ADMIT, total $54.36 |
| Real read-only report (`python -B study_spend.py --no-write`), with (a) only | exit 1, S2 `UNCONFIRMED` (see above; not committed) |
| Real read-only report, final program | **exit 0**; spent upper bound **$7.36**; plan C **$59.00**; headroom **$1.00**; `plan_C_is_final: false`; nothing rejected, unconfirmed, latched or uncertain; previews ADMIT for P1b, P2, M1-M4, E1; M5, M6 REFUSE `OVER_CEILING:$70.66 > $60.00` (same as the checker's run of `d5c8184a`) |

### After-run backlog (NOTES from the conformance check; not fixed here, not rule non-conformances)

1. **R5 "update" limit (NOTE 1).** No update (optimizer-step) limit is admitted or read by this gate. The latch fires
   for every limit it does admit (money cap, instance seconds, deadline, disk, machine) and for a second attempt under
   one admission. Codex to decide: does the technical admission own the update limit, or should this gate bind an
   admitted update limit and read an observed update count?
2. **A closed mandatory admission with no retry row frees its reserve (NOTE 2).** Outside the literal rule text. With
   M1's unused admission closed `CLOSED_NO_LAUNCH` and no M1.2 appended yet, M1's $11.66 is no longer reserved and the
   comparison is not marked incomplete. The $60 ceiling still holds on every admission. Optional, for Codex: keep a
   mandatory slot's cap reserved while its latest attempt is `CLOSED_NO_LAUNCH` (or a proven refusal) and no later
   attempt row exists.

### Claim states

- **Real (measured here):** 81/0 tests; the new test fails on `d5c8184a`; the named case decisions above; the real
  report's numbers; the four booleans about S2's two worker-result copies.
- **Open:** a fresh conformance check of this fix; Codex's ruling on rule (b); NOTES 1-2 (backlog).
- **Not licensed:** any real `--admit`; any claim that the gate is final before that check.

### Exposure

Read: `REVIEW.md` (the conformance check section), `study_spend.py`, `test_study_spend.py`, `PREREQUISITE_SLOTS.md`
(R3 bullet); the receipt paths, kinds and commits in `STUDY_SLOTS.json` (a script printed those only); the file names
in S2's receipt folder at `1ddf6a1e` (`git ls-tree`, names only); the launcher's `_collect_declared` code
(`research/CAS_META_2_COMPOSITION/aws/graph_training_curriculum_launch.py`, lines 1060-1125, code only). One script
read S2's receipt, `curriculum_result.json` and `collected/results/result.json` at `1ddf6a1e` and printed only
booleans (pin match, sha256 equality with `collected.result_sha256`) and the file name tail of `collected.result`; no
`ledger_before` / `ledger_after` field was printed or inspected, and `collected/reservation/ledger_snapshot.json` was
not opened. One script printed S2's cleanup line from the real account (job id and paths only). Ran: the test file
three times (after each change) and the new test alone once; the real report three times with `--no-write` (no state file written, no lock, no
fetch) and once in plain report mode, which rewrote `STUDY_SPEND_STATE.json` (only its `gate_version` line changed; no
lock, no fetch); the checker's named cases in a scratch script (temporary folders, fake git); the new test once against a
scratch copy of the `d5c8184a` program. Wrote: `study_spend.py`, `test_study_spend.py`, `PREREQUISITE_SLOTS.md` (R3
bullet), `STUDY_SPEND_STATE.json` (by the program), this section. Scratch only (session scratch folder, not committed): the case script, the report outputs,
the old-program copy. The untracked `aws_probe_job/dry_run_machine_script.sh` is not mine and was left alone. No AWS
call, no torch, no model, no `*_eval.jsonl`, no sealed file, no `D:/tksCAS-archive/`, no salt, no S3, no meta1
ledger, no transcript, no real `--admit`, no `--launch-check` on the real slots file.
