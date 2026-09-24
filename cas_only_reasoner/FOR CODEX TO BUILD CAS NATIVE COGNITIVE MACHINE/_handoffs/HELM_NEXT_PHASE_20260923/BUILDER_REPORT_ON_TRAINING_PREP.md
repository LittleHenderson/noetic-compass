# Builder report: preparing switch-ON training (2026-09-23)

Written by the temporary Claude builder. Label: `CLAUDE_BUILT_CLAUDE_CHECKED` once reviewed and checked. Until
then this work is **built and statically checked only**.

- Nothing was run with torch. The launcher was not imported, and neither the launcher nor the writer was run.
- No package was built and no admission file was created.
- Parent commit: `1230a9ff` (coordinator log). Source parent: `ceab6c49`.
- `pointer_learner.py` is byte-identical to `ceab6c49` (`git diff --quiet` passes).

## Deliverable 1: the ablation table now owns the analogy head

File: `cncm/typed_pointer_worker.py` (`.gitattributes`: `text eol=lf`).

**The problem.** With the switch ON, the container has 53 state-dict keys. The ablation table owned only 48 of them.
`_ablation_components` (now line 1384) refused with
`POINTER_ABLATION_COVERAGE:analogy_head.0.weight:covered=48:of=53`. The ablations would then report FAILED.

**The fix.**
- `"analogy_head."` is appended to the existing `heads` row (now line 193).
- A 5-line comment above the row (lines 187-191) says why, and says the `heads` number is no longer like-for-like
  with Helm 2.0.
- The four components and their names are unchanged, so `ABLATION_PHASES` is unchanged:
  `ablation_baseline`, `ablation_core_block`, `ablation_round_mix`, `ablation_heads`, `ablation_query_and_readout`.
  The evidence contract's artifact names therefore do not move.
- The worker file is an input-inventory row, so the **inputs hash moves**. The design hash does not.

**Byte comparison vs `ceab6c49`:**
- Two changes only: 5 lines inserted (new 187-191), and 1 line replaced (old 188 → new 193).
- The other 1,890 of 1,891 lines are equal, byte for byte.
- LF only; no CR byte in the file.

| | `ceab6c49` | New |
|---|---|---|
| raw sha256 | `6d859630ef45bcc4ef969f1d7232e3e68270cc208da431dd25cddfbfadda34e2` | `712579b0b5a869e10e95b21644fe8157b9e4007036bbfa28aa62114bc491047c` |
| bytes / lines | 124,382 / 1,891 | 124,957 / 1,896 |

**Coverage, measured.** I loaded the edited file's own `ABLATION_COMPONENTS` and `_ablation_components` with `ast`
(no project import, no torch) and ran them on the committed inventory's key lists
(`records/helm_integrated_repairs_20260923/analogy_tensor_inventory.json`: 53 ON keys, 48 OFF keys).

| Table | Switch | Result |
|---|---|---|
| new | ON | 53 of 53 covered, each exactly once. `heads` owns 38, including the 5 `analogy_head.*` keys |
| new | OFF | 48 of 48 covered, each exactly once. `heads` owns 33. `dead_prefixes = ["heads:analogy_head."]`, recorded as evidence and not refused |
| old (`ceab6c49`) | ON | refused: `POINTER_ABLATION_COVERAGE:analogy_head.0.weight:covered=48:of=53` |
| old (`ceab6c49`) | OFF | accepted |

- The reset path covers the analogy head. `_reset_component` maps names through `pointer_learner._registered_names`,
  which is built from `named_parameters()` and so includes `analogy_head.*`.
- **Not like-for-like with Helm 2.0.** The `heads` ablation now also resets the analogy head to its initial
  weights. Helm 2.0's container had no analogy head, so this one ablation number cannot be compared directly with
  Helm 2.0's. The other three can, as far as the reset set goes: `core_block`, `round_mix` and `query_and_readout`
  own the same keys as before.
- No test or record pins the table's contents. `git grep` found no other use outside Markdown and frozen copies.

## Deliverable 2: the admission writer for the ON study

File: `records/typed_pointer_001/admission_analogy_on_001/prepare_on_study.py`.
- 346 lines, LF only, ASCII, longest line 117.
- sha256 `660ac6f5655e3dee90bf3d623c669a60d866f879beb210f8a28ceb7e6661dd5e`.
- `py_compile` passes. An `ast` check confirms every `launch.*`, `launch.shared.*`, `launch.lifecycle.*`,
  `launch.run_evidence.*`, `contract.*` and `pointer_learner.*` name it uses is defined in those modules.

### What it does

- **Two modes.** `--source-sha <40 hex>` plus exactly one of `--dry-run` or `--write`. There is an optional
  `--owner-question "<verbatim>"`, because the question the owner answered was not given to me. Without it the
  record says so.
- **Checks before anything is written.** Any failure stops with `ANALOGY_ON_ADMISSION_STOPPED:<reason>`:
  - The source sha is `HEAD`.
  - The tree is clean, except for the one package folder `package_<sha8>/`.
  - No reduced schedule is set.
  - `_build_container`'s switch default is `True`.
  - The worker's `heads` ablation row contains `analogy_head.`.
  - The seeds are `20260917, 20260918, 20260919`.
  - `launch.BOUNDS` still says `training True, jobs 1, automatic_retries 0, reservation_usd "15.00",
    instance_type "g7.2xlarge", region "us-west-2"`.
  - 3 × $15.00 = $45.00.
  - The owner's words still match their pinned sha256 values.
- **Write targets.** It writes only `admission_analogy_on_001/<seed>/{owner,request,authority}.json` and
  `admission_analogy_on_001/study.json`, with mode `'xb'` (never overwrite). It refuses if any of them, any seed
  folder, or any `records/typed_pointer_001/receipt_analogy_on_<seed>` already exists.
- **Job ids** follow the launcher's form, `cas-meta2-tpntr-<UTC 14-digit stamp>-<sha8>-m-<seed>`, checked against
  `launch.JOB_PATTERN`.
- **The package.** Nothing is built here. The package is read from the path `prepare_study.py` used,
  `research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_<sha8>/`, and verified:
  - the receipt's schema, status and source;
  - the archive's sha256 and length;
  - the receipt's `archive` path is this file, and the launcher's own `_locate_archive` finds it;
  - the manifest's sha256;
  - the manifest's inputs hash equals `launch.frozen_inputs_hash(sha)`;
  - its frozen bounds equal `launch.BOUNDS`;
  - its pre-declared evidence contract is the registered 10-pass one;
  - the packaged worker has no `CNCM_POINTER_REDUCED_SCHEDULE` line.
- **The owner record** (`owner.json`) quotes, verbatim:
  - `owner_instruction_raw`: "3. YOU HAVE THE GO AHEAD FOR THE SWITCH ON MODEL" (sha256 `a8c84d3c...`);
  - `owner_message_full_raw`: "4. KEEP IT (G6E.XLARGE) 3. YOU HAVE THE GO AHEAD FOR THE SWITCH ON MODEL 2. GO WITH
    YOUR RECOMMENDATION 6 AND 7 NODE 1. FOR RESCORER PICK WHICH EVER ONE MAKES FOR A BETTER MODEL" (177
    characters, sha256 `f3a62b2e...`).
  - It also records: answered 2026-09-23; item 3; `bounds = launch.BOUNDS`; `label CLAUDE_BUILT_CLAUDE_CHECKED`;
    `runner: Claude coordinator (temporary takeover)`; `transcribed_by_agent: true`; `is_owner_signature: false`.
- **The request and authority records** have exactly the field sets `validate_request` and `validate_authority`
  require, built the way `prepare_study.py` builds them.
  - It adds one check: the config's own `inputs_sha256` must equal the launcher's. That is the divergence
    `inputs_hash_cross_check` exists for.
- **`study.json`** records:
  - schema `cncm.typed-pointer-analogy-on-study-admission/0.1`, status `FROZEN_BEFORE_FIRST_RUN`, the label and
    the runner;
  - the claim-bearing statement: "The worker marks a full 10-pass run claim_bearing=true as a historical-protocol
    flag (cncm/typed_pointer_worker.py, schedule_plan). This is NOT a design-v0.2 claim.";
  - the package identity, the owner's words, and the budget basis;
  - for each job: the pins, the receipt folder, and the exact `launch_argv`;
  - the package command;
  - a note that `execute_study.py` does not apply. It requires the five 2026-09-19 decisions.

### How each file is validated (with the launcher's own functions)

- **Before writing, in both modes** (when the package exists):
  - `launch.validate_request(request)`;
  - `launch.validate_authority(authority)`, with the registered 10-pass evidence contract, because these are full runs;
  - `launch.validate_owner(path, authority)`. That function reads a path, so the owner bytes go into a temporary
    folder outside the repository, which is deleted at once.
- **After `--write`:** every file is read back and compared to the intended bytes. Then all three validators run
  again on the bytes on disk, with the owner record read from its final path.
- **Dry run without the package:** it prints the records with `PENDING_PACKAGE` in the three identity fields and
  says `validated_with_launcher_functions: false`.
- **The job stamp is taken at run time.** So `--write` makes different job names and hashes from any earlier dry run.

### The sequence for the coordinator (nothing here has been run)

1. **Use a full, non-sparse checkout of the reviewed commit** (call it `S`). It must include this worker fix and
   this writer, and be clean.
   - Put it under `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE
     MACHINE/_worktrees/<name>/` (see answer (a)).
   - Build the package, write the admission and launch the jobs **all from that one checkout**. The receipt and
     archive paths are absolute, and `_locate_archive` follows them.
2. **Build the package.** From the CNCM folder of that checkout, with no `--reduced-schedule`:
   `python -B "research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py" --package
   "<CNCM>/research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_<S8>" --source-sha <S>`
   - This is what `prepare_study.py`'s `launch.build_pointer_package(...)` call does.
   - It needs `HEAD == S`, because `build_pointer_package` reads the inventory from `HEAD`.
3. `python -B "records/typed_pointer_001/admission_analogy_on_001/prepare_on_study.py" --source-sha <S> --dry-run`
4. The same command with `--write`, and `--owner-question "..."` if you have the question.
5. **Commit** the package folder and the ten admission files, with explicit paths.
6. **Launch each job:** `python -B "research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py"` followed by that
   job's `launch_argv` from `study.json`. That is the same call `execute_study.py` makes.

### Points I flag for the coordinator (not decided by the builder)

- **Budget.** The owner's quoted words approve the switch-ON model and name no dollar amount. The $45.00 total
  (3 × the launcher's pinned $15.00) comes from your brief. The records say this in `budget_basis`.
- **Item 4.** "4. KEEP IT (G6E.XLARGE)" is recorded verbatim and not interpreted. The training instance is the
  launcher's `g7.2xlarge`.
- **No rehearsal.** `prepare_study.py` also extracted the package and ran a Windows refusal rehearsal. This writer
  does not, because the brief limits its writes to the admission files.

## Answers

### (a) Can the launcher run from `D:/tksCAS-worktrees/helm-builder` with an absolute `--ledger-path`?

**No.** It must run from a checkout nested under the main CNCM folder on `C:`, for example under its `_worktrees/`.

- `aws/typed_matched_launch.py:18-21`: `WORKSPACE_HOME` is the **outermost** ancestor folder named
  `FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE`.
- `aws/typed_matched_launch.py:48-50`:
  `CANONICAL_LEDGER = WORKSPACE_HOME / "_worktrees/meta1/.../records/budget/campaign_ledger.json"`.
- `aws/typed_matched_launch.py:130-134`: `validate_ledger_path` requires the resolved path to **equal**
  `CANONICAL_LEDGER.resolve()` **and** to be a file. Otherwise it refuses with `TYPED_CANONICAL_META1_LEDGER_REQUIRED`.
- `aws/typed_pointer_launch.py`: `CANONICAL_LEDGER` is `matched.CANONICAL_LEDGER` (252). `validate_ledger_path`
  delegates to it (495-497). `main` validates `--ledger-path` (946), and `execute` requires the provider's ledger
  to match (893).
- **The two locations, computed** with the same expression (pure path arithmetic; no file opened):
  - from `D:/tksCAS-worktrees/helm-builder/...` the canonical path is
    `D:\tksCAS-worktrees\helm-builder\cas_only_reasoner\FOR CODEX ...\_worktrees\meta1\...\campaign_ledger.json`,
    which does not exist;
  - from `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX .../_worktrees/<x>/...` it is
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX ...\_worktrees\meta1\...\campaign_ledger.json`.
- So from `D:`, an absolute `--ledger-path` to the `C:` ledger fails the equality test, and the `D:` path fails the
  file test.
- A directory junction would probably satisfy the check, but I did not test it and do not recommend it.
- I did not check that the `C:` ledger exists (it is another worktree's file).

### (b) Would the launcher's working-tree inventory check refuse a sparse checkout?

**Not for being sparse, but it refuses whenever an inventory file is missing, and every checkout of
`helm-builder` so far is missing some.**

- `aws/typed_pointer_launch.py:303-366` (`_committed_rows`) takes its row list from
  `contract.input_inventory(PROJECT)`, which reads the **working tree**, then checks each row against the commit.
- `pointer_contract.py:422-433` → `matched_contract.py:173-178` → `worker_contract.py:135-156`:
  - it globs every `*.py` under `cncm/` and `research/CAS_META_2_COMPOSITION/cas_meta2`
    (`SOURCE_PACKAGE_MISSING:<prefix>` if none);
  - it requires every pinned material file and wheel to exist (`INPUT_MEMBER_BOUND:<name>`).
- `pointer_contract.py:408-419` (`_checkpoint_rows`) also requires the 18 practice checkpoints on disk
  (`MATERIAL_PATH:<name>`).
- A checkout therefore needs all of:
  - `cncm/`, and `research/` (for `cas_meta2`, `aws` and the wheel folder
    `research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/`);
  - `records/typed_course_001/checks_002/public_course.json`;
  - `records/typed_interface_001/checks_002/training_tokenizer.json`;
  - `records/typed_matched_001/development_001/compact_development.json`;
  - the 18 files under `records/typed_practice_001/receipt_<seed>/checkpoints/`.
- **Two more refusals:**
  - An **untracked** `.py` file under `cncm/` or `cas_meta2/` becomes an extra row that the commit lacks, so it is
    refused with `POINTER_INVENTORY_BLOB_MISSING`.
  - `pointer_contract.make_config` → `load_material` also reads the course files.
- **This worktree today.** Before this task it lacked `cncm/`, so the first refusal would have been
  `SOURCE_PACKAGE_MISSING:cncm`. With `cncm/` added, the first refusal would be
  `INPUT_MEMBER_BOUND:records/typed_course_001/checks_002/public_course.json`. Answer (a) rules it out anyway.

### (c) The reduced-schedule smoke path Helm 2.0 used, and whether it can include ablations

**The mechanism.**
- The worker reads `CNCM_POINTER_REDUCED_SCHEDULE` (`cncm/typed_pointer_worker.py:202`; keys at 203).
- Only the launcher sets it: `typed_pointer_launch.py --reduced-schedule '<literal>'` →
  `configure_reduced_schedule()` (176-201) → one line inserted into the generated bootstrap (508-525).
- The package must be built with the opt-in unset (919-922).
- The smoke needs its own admission: an authority bound to the **smoke** evidence contract, frozen by a
  `prepare_smoke.py`-style script. This writer does not produce that.

**Helm 2.0's literal** (`records/typed_pointer_001/admission_smoke_001/smoke.json`, source `9b84b35c`):
`{"ablations":false,"evaluations":[0,1],"interference":false,"passes":1,"phase_a":["initial","pass_01","final"],"phase_b":false,"reloads":true,"replays":true,"retention":false,"updates":8}`
- 40 artifact names, 43 required evidence entries.
- Estimated 1,369 instance seconds, $0.96.
- **Its ablations were off.**

**Can it include ablations? Yes, by reading.**
- `"ablations"` is one of the ten accepted keys.
- `_plan` (249) puts no condition on it.
- A 1-pass, 8-update plan still has `initial.pt` and `final.pt`, which the ablations restore.
- The held-back panel (`ctx["held_packets"]`, 628) does not depend on the plan.
- The literal would be the same as above with `"ablations":true`.

**Would it catch the ablation gap?** Yes, in two places, by reading and not tested:
- **In the worker.** With the old table, the coverage check runs before the baseline evaluation (1489).
  `ablations.json` then carries `status FAILED` and the `POINTER_ABLATION_COVERAGE:...:covered=48:of=53` detail.
  The worker still reports success, because ablations are report-only (`_degraded_checks`, 1568). It lists
  `degraded_checks: ["ablations"]` and drops the ablation files from its own required list (`_effective_required`, 1543).
- **In the launcher.** The smoke's pre-declared contract is built from the same plan, so it lists the 10
  `ablation_*` files. They are missing, so the result is `INCOMPLETE`, `completed_deliverable` is false, and
  `main()` returns 1.
- **With the fixed table**, the same smoke would exercise all four resets on the ON container.

**Cost of adding ablations.** Helm 2.0's full runs measured `ablations_seconds` of 172.355, 171.508 and 170.547 on
the same held-back panel. So adding ablations to a smoke should add about 3 minutes of worker time. That is an
estimate from those measurements.

### (d) Laptop-side memory and time while the launcher polls

**Time (measured on Helm 2.0).**
- The lifecycle `elapsed_seconds` per job were 10,494.563, 10,529.071 and 10,471.830 (about 2.9 h). The
  launcher process stays alive and polls for the whole job.
- The wait budget is `INSTANCE_SECONDS_MAX` 14,400 s (line 54). The poll interval is 5 s (750).
- Up to 500 transient provider errors are retried (242). That includes `RequestTimeTooSkewed` and
  `RequestExpired` after a laptop sleep (235-236).
- If the process dies, the guest watchdog powers the instance off at 14,100 s (53).
- **Three sequential jobs take about 8.8 h.**
- The ON model adds 29,121 parameters, and its analogy head runs only on analogy questions, so worker time should
  be close to Helm 2.0's 9,852-9,932 s. That is an assumption, not a measurement.
- The worker's `OWNER_PROJECTION_THRESHOLD_SECONDS` is 11,000 (line 205). It is a reported spend check on
  projected instance seconds (used at 1629), not a stop. Helm 2.0's whole lifecycle took about 10,500 s, so a
  slower ON run leaves little room under that reading.

**Disk.** Each Helm 2.0 receipt collected 616 files, 153,407,505 bytes.

**Memory: NOT MEASURED.** What the process holds:
- `validate_authority` runs at least three times at start (lines 944, 890, 821). Each one calls
  `make_config` → `load_material`, which parses the course (`public_course.json` 4,165,195 bytes, development
  685,549, tokenizer 447,140).
- `frozen_inputs_hash` reads about 26 MB of inventory blobs through `git show`, cached per commit.
- Polling itself is one AWS describe call every 5 s.

I expect the start-up validation to be the peak and polling to be light, but I have no number. Suggestion: record
the process's peak memory on the first job.

**A consequence of (a).** The ledger rule ties the launcher to this laptop's `C:` path layout. So the launcher
cannot simply be moved to an AWS machine without the canonical ledger.

## What I could not verify locally

- **Not run:** the writer (both modes), `launch.validate_*` on real records, `make_config` and the package build.
  All need a full checkout and I ran none of them.
- **By reading only:** the smoke, the CUDA side, the collection size for an ON run, and the laptop's memory
  during a launch.
- **Measured only statically:** the worker fix, by running the file's own coverage function on the committed key
  lists. It has not been exercised in a real ablation run.

## EXPOSURE: what I opened outside my working copy

- **No file outside `D:/tksCAS-worktrees/helm-builder` was opened in this task.**
- **Read from this repository's git objects** (outside the sparse checkout) with `git show` / `git ls-tree`:
  - `records/typed_pointer_001/prepare_study.py`, `execute_study.py` and `prepare_smoke.py` (the smoke-schedule
    part);
  - `admission_smoke_001/smoke.json`;
  - the Helm 2.0 receipts `receipt_2026091{7,8,9}`: `worker_report.json` and `phase_timings.json` (selected
    fields), and `result.json`, `provider_0001.json`, `provider_0027.json` and `reduced_schedule.json` (seed
    20260918 only);
  - the file listings of `records/typed_pointer_001/`, `admission_001/` and
    `research/CAS_META_2_COMPOSITION/records/typed_pointer_001/`;
  - the sizes of the three course files, the wheels and the Python sources.
  - Nothing sealed, HSET or `hset1a` was read. One receipt file path contains the word "seal"
    (`receipt_helm2_gradfail_20260917/.../failed_seal.json`). It appeared in a name listing only and was not opened.
- **Worktree configuration changed:** the sparse-checkout list now also holds `cncm/` and
  `records/typed_pointer_001/admission_analogy_on_001/`.
  - My first attempt was mangled by Git Bash path conversion. I reset the list with `git sparse-checkout set
    --no-cone`: the original eight patterns plus these two.
- **Not opened:** `D:/tksCAS-archive/`, any `*SEALED*` file, other worktrees (including the meta1 ledger), S3, and
  session transcripts.
