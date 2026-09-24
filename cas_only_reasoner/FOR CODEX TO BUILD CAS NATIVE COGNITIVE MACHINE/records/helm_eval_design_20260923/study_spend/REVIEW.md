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
