# Review: switch-ON smoke writer, fixed seed writer, runner, migration record (commit 0a8a81b3)

Fresh reviewer, 2026-09-23. Static review only. Nothing was run with torch. No writer, launcher or runner was run.
No package was built. No AWS call was made.

## Verdict: APPROVE_WITH_MINOR

- **No BLOCKER. No MAJOR.**
- My earlier BLOCKER (no smoke with ablations) is closed.
- My earlier MAJOR (the false budget statement) is closed.
- There are four MINOR findings. None of them lets money be spent above the $60.00 ceiling.
  - MINOR 1 and MINOR 2 concern how exactly the owner's stop rules are applied. The coordinator should decide on
    both before `--execute`.
  - MINOR 3 and MINOR 4 are hardening.
- Scope: the commit touches only `records/typed_pointer_001/admission_analogy_on_001/` (5 files) and 2 handoff
  files. No file under `cncm/`, `cas_meta2/` or `aws/` changed, so the launcher's input inventory does not move.
- File hashes match the builder's report: `on_study_common.py` `97d121c8...`, `prepare_on_smoke.py` `5ee86613...`,
  `prepare_on_study.py` `ba558820...`, `run_on_study.py` `21fb3b9e...`, `MIGRATION_ON_SHAPES.json` `dbdcda9c...`.
  All are LF only and ASCII, with `text eol=lf`.

## Findings, most severe first

### MINOR 1: a seed's "delivered" test is stricter than the owner's words and could stop a usable run

- **Where.** `run_on_study.py:262` (`report['degraded_checks'] == []`) and `:363` (stop reason `SEED_NOT_DELIVERED`).
- **What it does.** A seed counts as delivered only if all three report-only checks reached `COMPLETE`: phase A,
  phase B and the ablations. "Report-only" means the worker records these checks but does not fail the job on them.
- **Failure scenario.**
  - Seed 20260917 trains all 10 passes. Its checkpoints arrive, and the launcher reports `completed_deliverable: true`.
  - But phase B's probe step fails. Phase B is report-only, and the worker still reports success.
  - The runner logs `SEED_NOT_DELIVERED` and stops. Seeds 20260918 and 20260919 are never run.
  - Acceptance item 2 (prereg A5.1/A5.2) needs 18 checkpoints across all three seeds, so it can then never be read.
    The two remaining approved seeds are forfeited.
- **Why the risk is real, though small.**
  - The smoke literal switches phase B off, as briefed.
  - So seed 1 is the first run of phase B on the 53-key container.
  - Helm 2.0's three seeds all had empty `degraded_checks`.
- **The stop reason also misstates the fact.** The job WAS delivered in the launcher's sense.
- **Suggested fix.** Either:
  - keep the rule, but record it as a coordinator decision in the run records, and log a separate reason such as
    `SEED_DELIVERED_WITH_DEGRADED_CHECKS`; or
  - stop only on the owner's test (exit 0, `completed_deliverable`, cleanup complete, `claim_bearing: true`, no
    reduced schedule), and log degraded checks as a warning the coordinator reads before the next seed.
- For comparison: the frozen `evaluate_gates.py` (FIX 6 and the I3 phase-A rule) will refuse a degraded seed at
  reading time anyway. So the historical gate stays protected either way.

### MINOR 2: the spend estimate can under-count if the laptop sleeps during a job

- **Where.** `run_on_study.py:271-286` (`spend`) and `:350-354` (the $30.00 test).
- **The formula.** It uses `result.json` `elapsed_seconds` from the launcher, which is a `time.monotonic()` reading
  (`graph_training_candidate_launch.py`, `elapsed_seconds: time.monotonic() - started`).
- **The problem.** On Windows, the monotonic clock may not count time while the laptop is suspended. The EC2
  instance keeps running and billing while the laptop sleeps, up to the guest watchdog at 14,100 s.
- **Failure scenario.**
  - The laptop sleeps for 2 h during each of the first two seeds, which is plausible across about 8.8 h of runs.
  - Each seed's estimate is then about $5 low.
  - The true spend before seed 3 could pass $30.00 while the estimate shows about $20.66.
  - Seed 3 would then launch against the owner's third stop rule.
- **The money stays bounded.** Four reservations of $15.00 cap the total at $60.00, so the ceiling holds. Only the
  $30 stop can be missed.
- **Suggested fix (cheap).** The runner already logs a UTC wall-clock `utc` on `job_started` and `job_finished`
  (`:121`, `:357-361`). Use `max(elapsed_seconds, job_finished.utc - job_started.utc)` as the hours.
- **The rest of the estimate errs high, as claimed:**
  - the maximum observed on-demand rate;
  - plus the $1.48 ancillary allowance per job (EBS, S3 and transfer are far below this);
  - rounded up to the cent.
- **One more gap.** If a person ever resets the run log after a failure, the spend of the failed job is not in the
  $30 sum.

### MINOR 3: a free refusal before any reservation stops the whole study and needs log surgery

- **Where.** `run_on_study.py:359-364` (`outcome` after `launch_job`) and `:80-113` (`read_log` / `log_state`).
- **The problem.** Any non-zero exit is logged as a failed job:
  - `SMOKE_FAILED_NO_SEED_IS_LAUNCHED` for the smoke;
  - `SEED_NOT_DELIVERED` for a seed.
  That includes a launch that the launcher refused for free, before any reservation.
- **The log then blocks for good.** It is append-only. Every later start refuses with
  `RUN_LOG_SHOWS_A_PRIOR_FAILURE`, and there is no documented way to resume.
- **Failure scenarios (each costs $0):**
  - the runner is started with a Python that lacks `boto3` / `botocore`, so `lifecycle._clients` fails;
  - `LEDGER_CAP_CHANGED`;
  - `TYPED_CANONICAL_META1_LEDGER_REQUIRED`;
  - `POINTER_INVENTORY_WORKING_TREE_DIVERGED`.
  In each case no receipt folder is created and nothing was spent. But the owner's rule "if the test run fails, no
  seed is launched" is now recorded as having fired.
- **Suggested fix.**
  - In `--dry-run`, check that `sys.executable` can import `boto3` and `botocore`, and that
    `CANONICAL_LEDGER.is_file()`.
  - Record "exit non-zero and no receipt folder created" as `launch_refused_before_reservation`, with its own stop
    reason.
  - Document the restart procedure: who may start a new log, and the record that must accompany it.

### MINOR 4: the item-1 reading is trusted from any file whose hash is typed on the same command line

- **Where.** `on_study_common.py:274-295` (`read_item1`).
- **What it proves.** The path and the sha256 both come from the operator. So the hash check only proves the file
  did not change between hashing and running. It does not prove the file is the committed `RESULTS_READING.json`
  that `read_results.py` wrote.
- **Suggested fix.** Handle it the way the owner record is handled (`verify_owner_words`, `:200-225`):
  - pin the research-branch commit and path;
  - read the bytes with `git show <commit>:<path>`;
  - compare them to the supplied file.
- **Checked:** `read_results.py` at `research/helm-integration-20260923` (`30d35c0c`) writes the file with
  `newline="\n"` (line 113). Its top-level key is `item1_verdict`, and its pass value is exactly
  `OFF_PRESERVED_ON_T4` (lines 5-7 and 100-102). So the writers' key, value and no-CR rule all fit it.

### NOTES (no change required)

- **N1. Where to put the item-1 file.**
  - Supply it from OUTSIDE the launch checkout, for example a `git show` copy in a temp folder.
  - An untracked file inside the checkout's CNCM folder is not one of the four tolerated folders. So both writers
    would refuse with `COMMIT_FIRST_ONLY_THE_DECLARED_OUTPUTS_MAY_BE_UNTRACKED`.
- **N2. What the smoke does not exercise.** The smoke leaves phase B, retention and interference switched off, as
  briefed. Seed 20260917 is the first run of those paths on the ON container (see MINOR 1).
- **N3. OneDrive.** The final `os.rename(partial, final)` (`on_study_common.py:446`) can fail with
  `PermissionError` if OneDrive holds a handle on a file inside `.partial`. That fails safe: the `.partial` folder
  stays, and every writer refuses until a person looks.
- **N4. Ctrl-C.**
  - The lifecycle catches `BaseException` and runs cleanup in `finally`, so the runner's "wait, do not kill"
    handling is sound.
  - A second Ctrl-C during cleanup could still leave the instance to the guest watchdog.
- **N5. Stops are permanent.**
  - A delivered job that was followed by Ctrl-C ends in a permanent `stopped` event
    (`OPERATOR_INTERRUPT_AFTER`, `:366-367`).
  - A Ctrl-C that lands between `job_started` and `job_finished` leaves an unfinished job; later starts refuse.
  - Both fail safe. Both need the restart procedure asked for in MINOR 3.
- **N6. Files the writers need in the launch checkout.** Beyond the list in my review of `2cd6aed9`, they also
  read `records/helm_integrated_repairs_20260923/analogy_tensor_inventory.json` (`verify_migration`). A full
  checkout has it.

## Answers to the coordinator's six checks

### 1. The smoke: CLOSED

- **The literal.** `SMOKE_LITERAL` (`on_study_common.py:41-43`) is byte-for-byte the briefed literal.
  - It equals the launcher's canonical form: `json.dumps(sort_keys, separators=(",",":"))`, with the trailing
    newline stripped.
  - `prepare_on_smoke.py:111-114` enforces this and requires all ten keys.
- **The plan, recomputed by me.** I pulled the worker's own `_plan`, `schedule_plan` and `expected_artifact_names`
  out with `ast` (no torch) and ran them on the literal:
  - `claim_bearing` False;
  - every `INTENDED_PLAN` value matches;
  - 51 artifact names, including all 11 ablation files, so 54 required entries. The full plan has 99.
- **The package build, in order.**
  - `configure_reduced_schedule(SMOKE_LITERAL)` runs first (`:239-241`).
  - Only then does `ensure_package` build `package_on_smoke_<sha8>` with `launch.build_pointer_package`
    (`:169-186`, `:180-181`). It refuses unless the opt-in is set.
  - The line is read back from the BUILT `source.zip`:
    - the env-var and anchor counts are exactly 1;
    - the line sits right after the anchor;
    - the literal appears in the shipped line (`:139-166`);
    - `verify_package(..., smoke=True)` requires exactly one `CNCM_POINTER_REDUCED_SCHEDULE` in the shipped worker.
  - The seed package must carry none (`smoke=False`).
- **The binding.**
  - The authority's `evidence_contract_sha256` is the digest of `launch.smoke_evidence_contract()` (`:218`).
  - That contract is checked to equal `job_evidence_contract()` once the opt-in is set (`:243-244`), and to have 54
    required entries with `claim_bearing: false` (`:245-247`).
  - Validation runs with the launcher's own `validate_request`, `validate_authority(authority, smoke_contract)` and
    `validate_owner`, before writing (`:262-265`). They run again on the `.partial` bytes (`:339-344`).
- **The argv.** The recorded argv is `['--execute', '--reduced-schedule', <literal>, ...]` (`:273-278`). That is the
  one path by which `main()` selects the smoke contract (`typed_pointer_launch.py:919-926`, `:942-944`).
- **Folder names the launcher accepts.**
  - `_locate_archive` (`graph_training_candidate_launch.py:913-929`) searches every `receipt.json` under
    `research/CAS_META_2_COMPOSITION/records/`, so `package_on_smoke_<sha8>` is found.
  - `build_pointer_package` accepts any fresh folder under `ROOT/records` (`typed_pointer_launch.py:651-652`).
  - The receipt folder `records/typed_pointer_001/receipt_analogy_on_smoke_20260917` meets `prepare_evidence`: it
    must be fresh, its parent must exist, and no ancestor may be a link.
  - It also meets the owner-record job count (`receipts_root = records/typed_pointer_001`). The count is per owner
    record, and each job's owner record has its own hash.
  - Smoke and seed job names are checked against each other (`prepare_on_smoke.py:194-195`,
    `prepare_on_study.py:136`). The bucket name is exactly 63 characters.

### 2. The owner's budget words: CLOSED

- **The words.** I re-ran the check myself on the committed record (`d6c9faa9`, blob `35bbb67e`, no CR bytes).
  - After the writers' normalisation (line breaks and `> ` markers turned into spaces), each of these occurs exactly
    once: the question, the answer "Up to $60 (Recommended)", the option text, the full item message, and the three
    stop rules.
  - All five sha256 pins match.
- **The money.** `CEILING_USD '60.00'` = $15.00 smoke + 3 × $15.00, checked arithmetically against
  `launch.RESERVATION_USD` (`on_study_common.py:247-250`). The runner re-sums the four job reservations to $60.00
  (`run_on_study.py:192-194`).
- **The records.** Both records carry the stop rules, one machine at a time, and zero retries. The false sentence
  "the owner named no dollar amount" is gone; it survives only as a correction note in a docstring.
- **Item 1.** Both writers require `--item1-reading` plus its sha256, and refuse unless
  `item1_verdict == "OFF_PRESERVED_ON_T4"`.
  - The path, sha256 and verdict are recorded, and a byte copy is committed beside the records.
  - The runner re-checks both copies (`run_on_study.py:179-182`).
  - See MINOR 4 for a hardening.

### 3. Launching does not need HEAD == source: CONFIRMED

- **What the launch path reads.**
  - `validate_authority` (`typed_pointer_launch.py:451-478`) calls `frozen_inputs_hash(authority["source_sha"])` at
    `:471`.
  - That leads to `_committed_rows` (`:303-366`). The row list comes from the working tree (`:321`), each row's bytes
    come from `git show <source_sha>:<path>` (`:332-333`), and they must be equal (`:357-364`).
- **Where HEAD is used.** `frozen_inputs()` reads HEAD only with no argument (`:375`), and only the package build
  calls it that way (`:630`, `:655`).
- **No other HEAD reads.**
  - `main` and `execute` (`:887-955`) read no HEAD.
  - `pointer_contract.make_config` makes no git call and embeds no checkout path.
  - The lifecycle `execute` (`graph_training_candidate_launch.py:687-851`) makes no git call.
- **The planned sequence is satisfiable.** The sequence is: build the seed package at S, smoke writer, seed writer,
  commit as S1, launch from S1.
  - `tolerated_prefixes` (`on_study_common.py:157-165`) accepts untracked files only under both package folders and
    both admission folders.
  - So each writer accepts exactly the other's outputs and its own package.
  - Each refuses if its own admission folder exists, or if any `.partial` folder exists (`seeds/` does not prefix
    `seeds.partial/`).
  - Both writers check that the two packages carry the same `inputs_sha256`, whichever runs second.
- **The runner's side.**
  - It requires HEAD to descend from S, with no diff and no dirt under `cncm/`, `cas_meta2/` or `aws/`, and the four
    frozen folders committed and clean (`run_on_study.py:214-231`).
  - `run_log.jsonl` and the receipt folders are outside those four folders, so they do not trip its own check.

### 4. The runner: sound, with MINOR 1-3

- **No retry.**
  - A non-zero exit, or a receipt that is not delivered, stops the run.
  - A receipt folder without a logged delivery is never relaunched (`:347-348`).
  - There is no option that raises a limit.
- **The log.** It is append-only and hash-chained. The runner refuses after any `stopped` event, an undelivered
  `job_finished`, an unfinished job, a broken chain, or a half-written last line.
- **Could the stricter "delivered" wrongly stop a good run?** Yes. See MINOR 1.
- **Could the spend estimate under-count?** Yes, through laptop suspend or a log reset. See MINOR 2. Otherwise it
  errs high.
- **The fields it reads exist.** I checked every one against Helm 2.0's committed receipt `receipt_20260917` and the
  worker source:
  - `result.json`: `status` `AWS_CANDIDATE_FINISHED`, `elapsed_seconds`, `preflight.observed_on_demand_hourly_usd`
    `['2.5200000000']`, and `reservation.reservation.plan.ancillary_reserved_usd` `1.48`;
  - the worker report: `ablation_status`, `report_only_status` and `degraded_checks`
    (`cncm/typed_pointer_worker.py:1838-1845`).

### 5. `MIGRATION_ON_SHAPES.json`: CORRECT, and I re-derived it

- **Counts.** 53 keys and 203,424 parameters with the switch ON; 48 keys and 174,303 with it OFF.
- **The head.** The five `analogy_head` tensors, and the 48-row shared list, equal the inventory rows.
- **The inventory.** Its sha256 `21ae887a...` (11,748 bytes) matches the committed file.
- **Helm 2.0 starts.** For all three seeds I checked the `initial.pt` identity against the committed git blob:
  the blob id, the byte count 2,235,079 and the sha256 all match. I hashed the blob bytes with `git cat-file`; no
  checkpoint was loaded.
- **The recorded source hash.** `pointer_learner.py` at `60e382b0` hashes to `320024b4...`, as the record says.
- **The builder's reading of the head initialisation.** It matches the code and my earlier reviews:
  - the head is built last;
  - inside `fork_rng(devices=[])`, seeded 20260923;
  - its Linear layers draw on the CPU, then move to the device;
  - no CUDA generator is used.
- **The claimed diff.** Between `20208c92` and `ceab6c49`, the container differs only by:
  - the appended head;
  - the two argument checks;
  - the read-only properties and guards;
  - comments and the profile/schema strings.
  I checked this with `git diff`.
- **Status of the matched start.** It is correctly labelled an expectation, not a result. A5.5 on AWS decides it.

### 6. `.partial` write-then-rename: SOUND

- **How it writes.** `write_folder_atomically` (`on_study_common.py:418-449`):
  - refuses if the target or the `.partial` folder exists;
  - writes each file with `'xb'` plus `fsync`;
  - checks the exact file set and the bytes;
  - re-runs the launcher's validators on the `.partial` bytes;
  - renames once, then re-reads the bytes.
- **Crash before the rename.** The `.partial` folder stays, and `refuse_partials` stops every later writer run.
- **Crash after the rename.** The folder is complete.
- **A half-built smoke package** is refused (`PACKAGE_INCOMPLETE_INSPECT_BY_HAND`). A complete one is re-verified and
  reused.
- The only caveat is OneDrive (N3), and it fails safe.

## EXPOSURE (outside the worktree `D:/tksCAS-worktrees/helm-builder`)

- **No file outside the worktree was opened or written,** except this review file inside the worktree. I made no
  scratch files for this delta.
- **Git objects read, through the shared object store:**
  - `read_results.py` at `research/helm-integration-20260923` (`30d35c0c`), matching lines only;
  - the owner record blob at `d6c9faa9`;
  - Helm 2.0 `receipt_20260917`: `result.json`, `launch.json`, `provider_0001.json` and `provider_0027.json` at
    `31f6a037`;
  - the three Helm 2.0 `initial.pt` blobs, bytes hashed only;
  - `pointer_learner.py` at `60e382b0` (hash only) and the diff `20208c92..ceab6c49`;
  - five `.gitignore` files;
  - `ls-tree` listings;
  - one `git for-each-ref` listing.
- **Not opened:** `D:/tksCAS-archive/`, any `*SEALED*` or `*sealed*` file, any `hset1a` path, the helm-integration
  and q4-sdg working copies, the meta1 ledger, S3 or AWS, torch source, and any transcript.
