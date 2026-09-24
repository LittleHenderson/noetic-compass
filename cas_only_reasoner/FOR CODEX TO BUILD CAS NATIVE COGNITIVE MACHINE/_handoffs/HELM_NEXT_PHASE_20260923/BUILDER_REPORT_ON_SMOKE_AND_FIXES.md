# Builder report: the switch-ON smoke writer, the fixed seed writer, and the runner (2026-09-23)

Written by the temporary Claude builder. It answers the fresh review of `2cd6aed9` (verdict CHANGES_REQUIRED).
Label: `CLAUDE_BUILT_CLAUDE_CHECKED` once reviewed. Until then this work is **built and statically checked only**.

- Nothing was run with torch. No writer, launcher or runner was run. No package was built. No AWS call was made.
- Parent commit: `31f6a037`. The worker fix of `2cd6aed9` is unchanged.
- No file under `cncm/`, `cas_meta2/` or `aws/` was added or edited. So the launcher's input inventory, and its
  `inputs_sha256`, do not move.

## In one paragraph

There are now three scripts and one shared module in `records/typed_pointer_001/admission_analogy_on_001/`.
`prepare_on_smoke.py` freezes the owner-approved short test run (the "smoke") with ablations ON. It builds its own
package, then reads the schedule line back out of the built zip. `prepare_on_study.py` freezes the three seed jobs.
It now quotes the owner's $60 budget answer, and it requires the item-1 pass. `run_on_study.py` runs the smoke and
then the three seeds, one at a time, and applies the owner's three stop rules. A static JSON declares the ON shapes
and the matched starts. Every admission file is written into a `.partial` folder first and renamed only after all
checks pass.

## D. Does launching need HEAD == the package's source commit? No.

**The answer.** The launch path never reads HEAD. It needs the files the launcher reads to be byte-identical to the
source commit. A later commit that adds only records is accepted.

**Where this comes from (`research/CAS_META_2_COMPOSITION/aws/`):**
- `typed_pointer_launch.py` `main` (905-955) and `execute` (887-902) call `validate_request`,
  `validate_authority`, `validate_owner`, `validate_ledger_path`, `_locate_archive` and the lifecycle. None of
  them reads HEAD.
- `validate_authority` (451-478) calls `frozen_inputs_hash(authority["source_sha"])` (471). That goes to
  `frozen_inputs(source_sha)` (369-379), then `_committed_rows` (303-366):
  - the row list comes from the **working tree** (`contract.input_inventory(PROJECT)`, 321);
  - each row's bytes come from `git show <source_sha>:<path>` (332-333);
  - they must match (357-364).
  - So the rule is "working-tree inventory == the source commit's bytes", not "HEAD == source".
- `frozen_inputs()` uses HEAD only when called with no argument (375). That happens only in the package build
  (`build_pointer_package`, 655; `package_data_files`, 630). So **building** needs HEAD == source. Launching does not.
- The lifecycle (`graph_training_candidate_launch.py` `execute`, 687-851) has no git call. It checks the owner
  record's bounds (714), finds and hashes the archive before the reservation (730-735), refuses a job name
  the ledger already holds (741), and needs a fresh receipt folder (742; `graph_training_curriculum_launch.py`
  `prepare_evidence`, 200-204).
- `_locate_archive` (`graph_training_candidate_launch.py` 913-929) searches every `receipt.json` under
  `research/CAS_META_2_COMPOSITION/records/` for the archive hash. Any package folder name there works, so
  `package_on_smoke_<sha8>` is found. The receipt stores an **absolute** archive path, so launch from the same
  checkout that built the package.
- The only other git calls in these modules are package builders: `typed_matched_launch.py:225`,
  `typed_practice_launch.py:204`, `graph_training_curriculum_launch.py:485-506`.

**Helm 2.0 did the same (timing evidence, not proof; the launcher records no HEAD):**
- Seeds: source `20208c92`. The freeze commit `3da10d84` adds only records (admission files, the package, the
  rehearsal copy); committed 2026-09-20 21:06:15 UTC. The first reservation (`receipt_20260917/reservation.json`)
  is 21:08:16 UTC, two minutes later.
- Smoke: source `9b84b35c`. The freeze commit `ccc4a30a` adds only the smoke records and package; committed
  02:57:27 UTC. The smoke's reservation is 02:58:41 UTC.

**The sequence to use (nothing here has been run):**
1. Make a FULL, non-sparse checkout of the reviewed commit `S` under
   `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/<name>/`.
   It must be clean. (That location is needed for the canonical ledger; see the earlier report, answer (a).)
2. Build the seed package with the launcher, from the CNCM folder:
   `python -B research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py --package "<CNCM>/research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_<S8>" --source-sha <S>`
3. Smoke writer: `python -B records/typed_pointer_001/admission_analogy_on_001/prepare_on_smoke.py --source-sha <S> --item1-reading <RESULTS_READING.json> --item1-reading-sha256 <hex> --dry-run`, then the same with `--write`.
   `--write` builds `package_on_smoke_<S8>` and writes `smoke/`.
4. Seed writer: `python -B records/typed_pointer_001/admission_analogy_on_001/prepare_on_study.py` with the same
   arguments, `--dry-run` then `--write`. It writes `seeds/`.
   - In this order, each writer sees the other's package and records that both carry the same `inputs_sha256`.
5. Commit together, by explicit path, as `S1`: `package_<S8>/`, `package_on_smoke_<S8>/`, `seeds/`, `smoke/`. Push.
6. `python -B records/typed_pointer_001/admission_analogy_on_001/run_on_study.py --dry-run`. It prints the plan and
   the sha256 of `smoke/smoke.json` and `seeds/study.json`.
7. `python -B .../run_on_study.py --execute --smoke-sha256 <hex> --study-sha256 <hex>`, from the same checkout.
8. Afterwards, commit the four receipt folders and `run_log.jsonl`. The runner does not commit.

## What changed, by review finding

| Finding | What was done |
|---|---|
| 1 BLOCKER: no ON smoke with ablations | New `prepare_on_smoke.py`. Literal exactly as briefed. Own package `package_on_smoke_<sha8>`, built in-process after `configure_reduced_schedule(literal)`. Line read back from the built `source.zip`. Seed 20260917. Receipt `receipt_analogy_on_smoke_20260917`. Authority bound to `smoke_evidence_contract()` |
| 2 MAJOR: false budget statement | Removed. Both writers quote the question, the answer "Up to $60 (Recommended)" and the option text, verbatim, checked against the committed owner record (`d6c9faa9`). $60.00 ceiling = smoke $15 + 3 × $15. One machine at a time. No automatic retries. The three stop rules, verbatim |
| 2 (owner record, lines 30-31) | Records carry source, seeds, starts, limits (`launch.BOUNDS`) and the ceiling. Migration record `MIGRATION_ON_SHAPES.json` |
| Item-1 order rule | `--item1-reading <path> --item1-reading-sha256 <hex>` required by both writers. Refused unless `item1_verdict == "OFF_PRESERVED_ON_T4"`. Path, sha256 and verdict recorded; a byte copy `item1_reading.json` is written beside the records |
| 3 MINOR: one HEAD for both | Each writer tolerates, untracked, only the two package folders and the two admission folders. Nothing else. Both packages must carry the same `inputs_sha256` |
| 4 MINOR: stop rules not enforced | New `run_on_study.py` |
| 5 NOTE: crash leaves partial files | All admission files go into `<folder>.partial/`, are read back and re-validated, then renamed. Any `.partial` folder stops every writer until a person looks at it. A half-built smoke package is refused (`PACKAGE_INCOMPLETE_INSPECT_BY_HAND`); a complete one is verified and reused |

**Output paths moved.** The seed admission files are now in `admission_analogy_on_001/seeds/` (was the folder
itself). The smoke's are in `admission_analogy_on_001/smoke/`. The study schema is now `...study-admission/0.2`.

## The smoke, as frozen by the writer (by reading; not run)

- Literal: `{"ablations":true,"evaluations":[0,1],"interference":false,"passes":1,"phase_a":["initial","pass_01","final"],"phase_b":false,"reloads":true,"replays":true,"retention":false,"updates":8}`
- It is the launcher's canonical form, so the argv text and the baked-in text are the same.
- Plan read back through the worker's own `schedule_plan()`: 1 pass, 8 updates, 5 ablation phases, not claim-bearing.
- 51 artifact names, so 54 required evidence entries. Helm 2.0's smoke had 40 and 43.
- The argv is recorded as a list. `--reduced-schedule` and the literal are two list items, so no shell quoting is
  involved when the runner launches it.
- The smoke's `owner_instruction_raw` is the budget answer "Up to $60 (Recommended)". The seed records keep item 3,
  "3. YOU HAVE THE GO AHEAD FOR THE SWITCH ON MODEL". Every record carries all the quotes.

## E. The runner's rules

- Order: smoke, 20260917, 20260918, 20260919. One launcher process at a time, by subprocess, with its recorded argv.
- **Delivered** means: exit code 0; `result.json` shows `completed_deliverable: true`, `cleanup.complete: true`,
  status `AWS_CANDIDATE_FINISHED`; and the worker report fits the job.
  - Smoke: `reduced_schedule.json` carries the literal; `claim_bearing: false`; `ablation_status` COMPLETE;
    `report_only_status` COMPLETE for `ablations` and `checkpoint_check_phase_a`.
  - Seed: no reduced schedule; `claim_bearing: true`; `degraded_checks` empty.
- If the smoke is not delivered, no seed starts. If a seed is not delivered, the next does not start.
- **The spend field.** The launcher writes **no actual-spend field**. The runner uses the nearest fields it does
  write, all in the receipt's `result.json`, and errs high:
  `elapsed_seconds / 3600 × max(preflight.observed_on_demand_hourly_usd) + reservation.reservation.plan.ancillary_reserved_usd`,
  rounded up to the cent.
  - On Helm 2.0's committed receipts this gives $2.97 (smoke), $8.83, $8.86 and $8.82 (seeds). Smoke plus two seeds:
    $20.66.
- The $30.00 test runs before **every** seed launch, so also before the third. Checking earlier can only stop sooner.
- No retry. A job whose receipt folder exists and is not logged as delivered is never relaunched.
- The log `run_log.jsonl` is append-only; each line carries the sha256 of the line before it. The runner refuses to
  start on any `stopped` event, any undelivered `job_finished`, a job started but not finished, a broken chain, or a
  half-written last line.
- On Ctrl-C the launcher is never killed from the runner. The runner waits for the launcher's own cleanup, logs the
  job, and starts nothing more.
- Before any launch: both record sha256s (required for `--execute`), every pinned file, the item-1 copy, the
  migration pin, $15.00 × 4 = $60.00, both archives, HEAD descends from the source with no change under `cncm/`,
  `cas_meta2/` or `aws/`, and the four frozen folders are committed and clean.
- There is no option that raises a limit or allows a retry.

## C. The ON shapes and the matched starts

File: `MIGRATION_ON_SHAPES.json` (static; both writers check its pin and re-derive its counts from the inventory).

- ON: 53 state-dict keys, 203,424 parameters. OFF: 48 keys, 174,303. Added: 5 keys, 29,121 parameters.
- The five `analogy_head` tensors: `0.weight` [64, 452] (28,928); `2.weight` [64]; `2.bias` [64]; `3.weight`
  [1, 64]; `3.bias` [1].
- Source: `records/helm_integrated_repairs_20260923/analogy_tensor_inventory.json`, sha256
  `21ae887a6c783bc6f20e17d672d33431f36b5e5032af45d15fafe3f1955c95e3`, 11,748 bytes.

**Helm 2.0 `initial.pt` identities** (the .pt files were not opened):

| Seed | Helm 2.0 job | sha256 (2,235,079 bytes) | git blob |
|---|---|---|---|
| 20260917 | `cas-meta2-tpntr-20260920210258-20208c92-m-20260917` | `59dd46877bd7bf97dbb4059975051cc6102b374d5c387d3a183884048b71b004` | `8b42f3ec` |
| 20260918 | `...-m-20260918` | `d3c6292f2c0d09e29952bfe353d47fff058741d42c0a8e8dbe7a80eaad8fd645` | `423085e9` |
| 20260919 | `...-m-20260919` | `93b84558c0123673eabcc462f68afe8ecb1537b598e297ee16f7a7458787ee9f` | `d90858ff` |

- Where stated: each receipt's `collected_inventory.json` and `artifact_manifest.json`. Both agree. Read at `31f6a037`.

**How the analogy head is initialised** (`pointer_learner.py` at `ceab6c49`; read, not run):
- It is built **last** (859-868), after all 48 other tensors.
- It is built inside `torch.random.fork_rng(devices=[])`. That saves the CPU random state and restores it after.
- Inside, the CPU generator is seeded with 20260923 (`ANALOGY_INIT_SEED`, line 166).
- `devices=[]` means the CUDA generator is not saved, reseeded or used.
- **So, by reading:** the 48 shared tensors get the same random draws as with the switch OFF. Later random draws
  are not moved either.
- Between Helm 2.0's source `20208c92` and `ceab6c49`, the container changed only by the appended head, two
  argument checks, read-only properties and comments. No shared tensor was reordered.

**Not verified (open).** The inventory's "all shared tensors identical" was measured on CPU, torch 2.5.1, at
`pointer_learner.py` from `60e382b0`, OFF versus ON. It was not measured against Helm 2.0's saved `initial.pt`, and
not on the g7.2xlarge. Prereg amendment A5.5 (`d7023288`) is the deciding check, on AWS, after training.

## Files (all in `records/typed_pointer_001/admission_analogy_on_001/` unless stated)

| File | Status | sha256 | Bytes / lines |
|---|---|---|---|
| `on_study_common.py` | new | `97d121c8c6798ae9751f1b7e197f88f658201f74669879eec0ebfa684b6f82f2` | 26,003 / 449 |
| `prepare_on_smoke.py` | new | `5ee86613094a18bb74134f94d5639cc640714dc24fe64cd92acdc9d78e00a360` | 25,950 / 367 |
| `prepare_on_study.py` | changed (was `660ac6f5...`) | `ba558820b616de29f6ed4fdc064d7b381babfb34fa5b409847f58008ca18707b` | 19,790 / 286 |
| `run_on_study.py` | new | `21fb3b9e8f07bfe277306312d441088d921e465cf3fa8df22939382c61fc2f5a` | 22,814 / 386 |
| `MIGRATION_ON_SHAPES.json` | new | `dbdcda9c7b64a83d9f2bb8ee260bc1450427d8e9b62d52ecb03490330e87c207` | 13,362 / 515 |
| `_handoffs/HELM_NEXT_PHASE_20260923/BUILDER_REPORT_ON_SMOKE_AND_FIXES.md` | new | (this file) | |

All are LF only and ASCII. `.gitattributes` gives `.py` and `.json` here `text eol=lf`.

## What I checked (static only)

- **Compiles** with warnings as errors (all four `.py`). **pyflakes 3.4.0:** clean.
- **Names:** an `ast` pass confirms every `launch.*`, `launch.shared.*`, `launch.lifecycle.*`,
  `launch.run_evidence.*`, `contract.*`, `pointer_learner.*`, `worker.*` and `common.*` name used is defined in
  that module. (One hit, `worker.decode` in the common module, is a local bytes variable, not the worker module.)
- **The smoke plan, measured.** I pulled the worker's own `_plan`, `schedule_plan` and `expected_artifact_names` out
  with `ast` (no import, no torch) and ran them on the literal: 51 names, 54 required, 5 ablation phases, not
  claim-bearing. The same code gives 40 for Helm 2.0's smoke literal and 99 for the full plan, matching the
  committed records (43 and 102 required).
- **27 pure-Python checks, all passed.** They imported only `on_study_common` and `run_on_study`, and wrote only in
  my scratch folder:
  - owner words found verbatim, once each, in the committed owner record `d6c9faa9` (blob `35bbb67e`);
  - migration record pin and counts;
  - item-1 reading: pass accepted; wrong verdict, wrong sha256, CR bytes and missing file refused;
  - `.partial` writing: renamed on success; existing target refused; a failed re-check leaves `.partial` and no
    target; an existing `.partial` refused;
  - untracked-path rule: only untracked files under the four declared folders pass; a `.partial` file, a modified
    tracked file and a new `cncm/*.py` are all refused;
  - shipped-bytes check (on a scratch zip of the current learner and worker sources): ON accepted; switch OFF
    refused; a `heads` row without `analogy_head.` refused;
  - runner, on Helm 2.0's committed receipt JSON: the three seeds read as delivered; Helm 2.0's smoke does NOT pass
    as an ON smoke (wrong literal, ablations SKIPPED); a non-zero exit and a missing receipt are not delivered;
  - run log: unfinished job, delivered job, stop, prior failure, tampered chain and half-written line all behave as
    described.

## What cannot be checked without the C: launch checkout (open)

- Neither writer has run, in either mode. The launcher's validators have not run on real records.
- The two package builds, `frozen_inputs_hash`, `make_config`, `_locate_archive` and the shipped-line read-back on a
  real smoke `source.zip`.
- The runner's `--dry-run` and `--execute` end to end, including its git checks on a real `S1`.
- The item-1 file. I have not seen `RESULTS_READING.json`. The writers assume a top-level `item1_verdict` key, as
  briefed.
- That the canonical ledger exists at the `C:` path.
- The matched start (A5.5, on AWS), the ON run's timing, and the laptop's memory while the launcher waits.

## Open questions and flags for the coordinator (not decided by the builder)

1. **Seed "delivered" is stricter than the owner's words.** It also needs an empty `degraded_checks`. Helm 2.0's
   three seeds met it. It can only stop the run sooner. Drop it if you disagree.
2. **The spend test runs before every seed**, not only before the third. Same money limit; it can only stop sooner.
3. **The spend figure is an estimate.** It is not a provider invoice. It includes the $1.48 ancillary allowance per
   job, so it errs high.
4. **The item-1 copy** (`item1_reading.json`) is a copy of a research-branch record, committed on this branch beside
   the admission records.
5. **`CHANGELOG.md` and the spec sheet were not edited.** The brief allowed new files plus `prepare_on_study.py`
   only, and neither file is in this sparse checkout. This is preparation, not a result. Please log it.
6. **The runner needs the records committed** (`S1`) even for `--dry-run`, because it checks they are clean.
7. **Commit after the run.** The four receipts and `run_log.jsonl` must be committed by hand.
8. **Laptop time.** From Helm 2.0's receipts, about 0.6 h for the smoke and about 2.9 h per seed, one after another.
   The launcher process must stay alive throughout.

## EXPOSURE: what I opened outside the worktree

- **One file under `C:/Users/wakil/.claude/projects/`:** `...\5e8709f4-3151-444f-939b-317c01bc3568\tool-results\blfn260nt.txt`.
  It is not a transcript. It is my own tool's saved output of `git show HEAD:.../records/typed_pointer_001/prepare_smoke.py`,
  saved there because it was long. I read it to see Helm 2.0's smoke writer. I disclose it because it is under
  that folder.
- **My scratch folder** `C:/Users/wakil/AppData/Local/Temp/claude/.../scratchpad/`: `make_migration.py`,
  `static_checks.py`, `owner_d6c9.md` (a `git show` copy of the owner record) and a temporary `checks_tmp/`
  (deleted at the end of the checks).
- **Git objects**, through `git show`, `git ls-tree`, `git rev-parse`, `git cat-file -s`, `git diff`, `git log`. The
  object store is physically at `C:/.../_worktrees/vision-next/.git` (this worktree's git common directory). Read:
  - the owner record at `d6c9faa9` and the prereg v0.2 at `d7023288` (sections A4.2 to A5.6);
  - Helm 2.0's `prepare_smoke.py`, `prepare_study.py` (outline), `execute_study.py`, `admission_smoke_001/smoke.json`;
  - from `receipt_2026091{7,8,9}` and `receipt_smoke_20260918`: `result.json`, `reservation.json`,
    `provider_0001.json` (17 only), `launch.json`, `reduced_schedule.json`,
    `collected/results/artifacts/worker_report.json`, `collected_inventory.json`, `artifact_manifest.json`;
    reservation times from `receipt_smoke_2026091{7,8,8b,9,9f}`;
  - `pointer_learner.py` at `20208c92`, `60e382b0`, `098a3bdc`, `ceab6c49` and older commits (digests and diffs);
  - file listings of `records/typed_pointer_001/` and one receipt; the file list of the freeze commits.
  - One repository-wide `git ls-files` was piped through `grep` for Helm 2.0 script names. I saw only the filtered
    lines.
- **Not opened:** `D:/tksCAS-archive/`, any `*SEALED*`/`*sealed*` file, any path containing `hset1a`, the
  `helm-integration` and `q4-sdg` working copies, S3/AWS, the meta1 ledger, any `.pt` file or package archive, and
  any Claude transcript.
- **Not changed:** the sparse-checkout list and all git configuration.
