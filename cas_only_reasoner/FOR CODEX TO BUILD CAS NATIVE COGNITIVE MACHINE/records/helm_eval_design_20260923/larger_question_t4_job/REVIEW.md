# Review: HELM-LARGER-QUESTION-PATH-1 T4 check job

**Verdict: APPROVE_FOR_LAUNCH.**

Label: `CLAUDE_BUILT_CLAUDE_CHECKED`. A fresh Claude reviewer wrote this on 2026-09-23 (US Pacific). The reviewer did
not build either part. Nothing was launched. Nothing ran with torch or on a GPU.

## What was reviewed

| Part | Where | Exact version |
|---|---|---|
| Code fixes ("Revision 2": V1 grader pins, V4 5-node ruling) | branch `claude/helm-builder-continuation-20260923` | commit `e05889eec0f800a9a17b0c39a8d8d37f544b43bf` |
| AWS job folder (8 files) | branch `research/helm-integration-20260923`, this folder | commit `bd81e5b5bdb9c999826465192b6423f52dfc4ff1` |

The approval covers these job-file blobs at `bd81e5b5` and nothing later:

| File | git blob |
|---|---|
| `launch.py` | `763858bcbd605da86b62ef4e8448fc5f27ae434b` |
| `job.sh.template` | `faf4a8aa181efd422f76fb2ce2d26913db68f017` |
| `watch.py` | `d47d48e0d95e465e3b5d7888d502530fb12842a0` |
| `read_results.py` | `4ba1fee549a1a4bb75aa45f2fe79eba450f0d771` |
| `JOB_LIMITS.md` | `70ef6434f222cdc3adf9c84286e267bd8beecff3` |
| `README.md` | `ac13042350e91b1c4f2b599a33e0cb9ac1a901d4` |

Why the verdict is APPROVE: no finding below changes what runs on the machine. None changes what the job can cost.
None changes the reading of any output the pinned script can actually write. The MINOR items are hardening. They
are not conditions hidden inside the approval.

## What I ran (each once)

| Command | Result |
|---|---|
| `python -B -m pytest -q -p no:cacheprovider eval_paths/tests/test_larger_question_path_static.py` (from `research/CAS_META_2_COMPOSITION` in the `e05889ee` working copy) | **37 passed in 72.64 s**. The working copy stayed clean |
| `python -B launch.py --dry-run` (this folder, HEAD `bd81e5b5`) | **exit 0**. Bundle **259 files, 10,230,760 bytes, sha256 `2410f269a46d0a8024c7709976557aa1734b7e577cc6cfdb9e9909c53393bd36`**. This is identical to the builder's bundle. Worst case **1.6639 USD**, ceiling 3.00. Image `ami-07d69ce07bfe5628f` is available |

The dry run rewrote `dry_run_record.json` and `dry_run_machine_script.sh`. I compared them with the committed copies.
Only two things differed: the time stamp inside the placeholder links, and `job_commit`. The builder's value is
`f9ee07aa`, because the builder ran the dry run before committing. Mine is `bd81e5b5`. The template sha256 matched
(`dc05f4af...`). I then copied the committed bytes back, so those two files are unchanged in git.

AWS and network calls made by the dry run: one `ec2.describe_images` (read-only), and one `git ls-remote origin`
(read-only). Nothing was uploaded. No link was made. Nothing was launched.

## Checks asked for, and what I found

1. **The bundle comes from git objects at the pinned commit.** Yes. `read_blobs` uses `git cat-file --batch` on
   `e05889ee:<path>`. `tree_py` uses `git ls-tree` at the same commit. No working file enters the bundle. The
   launcher checks that `e05889ee` is on the pushed branch. I confirmed with `git ls-remote` that both branch tips are
   pushed: the source branch at `e05889ee`, the job branch at `bd81e5b5`. The bundle is reproducible: my sha256
   equals the builder's.
2. **Every REQUIRED_INPUTS file is carried.** Yes, all 12, each checked for bytes and sha256 against the script's own
   `--list-inputs`. The six checkpoints are also checked against the analogy T4 job's `launch_record.json`, which is
   an independent record. Stage 0 on the machine checks all 12 again. So does the script's own `verify_inputs`.
3. **Every file a bundled tool reads beside itself is carried.** Yes, for today's code. See M2: the launcher's own
   check is narrower than its wording, so I checked by hand.
   - I built the script's static import closure myself (79 distinct files). I scanned every file for file reads,
     for `__file__`-relative paths, for dynamic imports, and for code that runs at import time.
   - Every file read on the run path is one of three kinds. (a) A `.py` file in the two shipped trees:
     `face_corpus.py`, `controller.py`, `lesson_contract.py`, the `course_plan.LEGACY_FILES`,
     `cncm/rpa_learning_match.py` and the like. I confirmed each exists at `e05889ee`. (b) The course, tokenizer
     and development file. `pointer_contract` reads these at import time through `CNCM = parents[4]`, the bundle
     root. All three are REQUIRED_INPUTS. (c) The fixture JSON, which is REQUIRED_INPUTS.
   - The two trees hold 5 non-`.py` files: two READMEs, `source_manifest.json` and two exclusion JSON files. No
     closure module reads any of them.
   - Only one dynamic load is reachable in principle: `pointer_contract._practice_gates`, which loads
     `records/typed_practice_001/evaluate_gates.py`. It is reached only through `relational_population`. Nothing on
     the run path calls that.
4. **Exactly torch 2.11.0+cu128, and the two wheels with `--no-deps`.** Yes. The job installs `torch==2.11.0` from the
   cu128 index. Stage 0 refuses unless `torch.__version__ == "2.11.0+cu128"`. It also refuses unless CUDA works and
   the GPU name contains "T4". Both wheels are installed `--no-deps` from the bundle, and their sha256 is pinned. numpy
   is pinned at `2.5.2` and Python at `3.14.7`. These are the same versions as the analogy T4 job, which ran to
   `done`. See N5 on `jsonschema`.
5. **Environment variables.** Yes. `CAS_META2_RUN_TEACHING_CYCLE=1`, `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`,
   `CUBLAS_WORKSPACE_CONFIG=:4096:8` and `PYTHONDONTWRITEBYTECODE=1` are exported before stage 0. The learner's guard
   needs only Linux plus that one variable (`gpu_adapter.execution_guard`). I checked that the learner path never
   calls `gpu_adapter._cuda`, the function that refuses a T4 (`T4_NOT_ADMITTED`). Only the workers' `main` paths call
   it, and the script does not run them.
6. **Kill switches and timers.** Yes, four layers.
   - (0) `shutdown -h +123` from the operating system.
   - (1) An in-machine timer. At 7,200 s it sends TERM to the job shell. 120 s later it runs `shutdown -h now`.
   - (2) An EXIT trap. It stops the child process, packs `out/`, uploads the results and shuts down.
   - (3) `watch.py`. It terminates the machine at 130 minutes and retries until AWS confirms.
   - The launcher sets shutdown behaviour = terminate. The disk is deleted on termination.
   - The child runs in the background under `wait`, so the TERM trap works during the checks.
   - The in-machine limits (120 and 123 minutes) sit inside the 130-minute client deadline. The watcher stays the
     outer bound.
7. **Smoke stage and preflight.** Yes. Stage 0 checks the torch build, the GPU, the wheels, and every listed input.
   Any failure stops the job by name. Stage 1 is the script's own timed preflight. It refuses with exit 5 before any
   check if the projected wall time is over 3,600 s. `job.sh` maps exit codes 0 to 5 exactly as the script defines
   them.
8. **Ceiling arithmetic.** Correct. The rate is 0.752 + 0.005 + 100 x 0.08 / 730 = 0.767959 USD/hour. Over 130/60
   hours that is 1.6639 USD, below the 3.00 ceiling. For `g4dn.xlarge` the rate is 0.541959, which gives 1.1742. The
   launcher refuses unless the worst case is below the ceiling.
9. **Refusal if a GPU machine is running.** Yes, on a real launch. It refuses if any listed GPU family is pending,
   running or stopping (see N1 on the list). It also refuses if `launch_record.json` exists, if the job files are not
   committed, if the default security group is open to an address range, or if the pinned image is gone.
10. **The watcher's termination and volume checks.** Yes. The file is the analogy job's proven watcher (that run
    ended `terminated`, no volume left), with small additions. It makes sure the machine is gone before it
    downloads. It extracts only plain files named `out/<simple name>`. It waits up to 10 minutes for "terminated".
    It lists any volume tagged with this job's name. It exits 6 if the machine is not confirmed gone. It never
    launches, retries or deletes. See N4.
11. **`read_results.py` emits a verdict only from the script's own outputs.** Yes. It never re-decides a check. It
    restates the script's verdict after these rules: smoke first, then incomplete, then an integrity check (rows
    file sha256, code under test, torch build, GPU). I drove it with 10 fake result folders in scratch. It gave
    PASS, RESULT_INTEGRITY_FAILED (tampered rows; no launch record; wrong GPU), SMOKE_FAILED, INCOMPLETE and FAIL as
    designed. See M1 for three cases where it is not fail-closed.
12. **Nothing sealed is bundled or read.** Yes. The launcher refuses any bundle path matching `sealed` or ending in
    `_eval.jsonl` (none matched). The bundle holds only the 12 inputs, the `*.py` of two source trees, five
    `eval_paths` files and `identity.json`. No `records/` path is bundled beyond the 12 inputs. The run path reads
    no sealed file. Check d calls `train_sealed_batch` only on the subclass, and the subclass refuses with
    `INFERENCE_ONLY` before it reads anything. The fixtures are public. The script says its recording scheme must
    never be used for sealed items.

### The code fixes (Revision 2)

- **V1 is fixed as asked.** `verify_grader_pins` checks the route's checker files. On both routes it also checks
  `answers.py`, `focal.py`, `source.py` and `course.py`, on every `grade` and `target` call. I confirmed that
  `checker.py` and `checker_v2.py` import exactly `answers`, `focal` and `source`. `course.validate_model_packet`
  calls only pinned modules (`source`, `answers`). A new test drifts each shared file on both routes and expects
  `SOURCE_DRIFT:<file>`.
- **V4 is recorded as the coordinator ruled.** At 5 nodes, `parts`, `edge_account` and `reach` are
  `DIAGNOSTIC_ONLY`. Each row carries the reason. Each row carries
  `claim_status_vocabulary = LOCAL_LABELS_NOT_THE_SPEC_SHEET_LEGEND`. A test checks that no claim word is a spec-sheet
  legend word.
- `t4_larger_question_checks.py` is unchanged from the reviewed revision 1. The launcher's pin check found no drift
  in the 12 protected files or in the five T4-reference files.

## Findings

| # | Severity | Finding |
|---|---|---|
| M1 | MINOR | `read_results.py` is not fail-closed on missing identity fields. Measured in scratch: a summary that says `INTEGRATION_CHECKS_PASS` but has no `inputs.eval_paths_lf_sha256`, or no `torch`/`device_name`, is restated as PASS (exit 0). A PASS with `STATUS` not `done` is also restated as PASS. The pinned script always writes these fields before any check runs, and PASS always means exit 0. So nothing it can write triggers this today. Fix: for a PASS, require all three fields present and equal, and require `CHECKS_EXIT_CODE` = 0 |
| M2 | MINOR | The launcher's sibling-read check covers only the five `eval_paths` files, and only the `HERE / "..."` form. The two whole trees are not scanned. The README says the launcher refuses when "a bundled tool reads a file beside itself" that is not bundled; that is wider than the code. My manual scan found no gap (check 3). Fix: correct the wording, or widen the scan to the import closure |
| M3 | MINOR | There is no mechanical admission gate. `launch.py` does not read a review verdict. It does not pin the expected bundle sha256. A later commit to `launch.py` or `job.sh.template` would pass the "job files committed" check without a new review. Runner practice: launch only from job-file blobs listed above. Check that the dry run prints bundle sha256 `2410f269...` and template sha256 `dc05f4af...`. Put this review's commit in the launch record |
| M4 | MINOR | The machine runs `curl https://astral.sh/uv/install.sh \| sh`, whose version is not pinned. The analogy job did the same and ran. This is a reproducibility and supply-chain point. The README already lists it as open question 4 |
| N1 | NOTE | The GPU-family list is not complete. It lacks, for example, `g3`, `g3s`, `g6f`, `gr6f`, `p2` and `p6-b200`. The 8-vCPU G/VT quota would still stop a second G machine at AWS, so this is not a cost risk |
| N2 | NOTE | Stage 0 does not import the project code. A failure at import time would show only in stage 1, as `SETUP_REFUSED`, after about 10 to 15 minutes of setup. The launcher's static import check and the analogy run's identical imports make this unlikely |
| N3 | NOTE | `read_results.py` does not compare `out/identity.json` with the launch record. Its verdict does not depend on `watch_record.json` (`terminated_confirmed`, volumes). The machine's `sha256sum -c` protects bundle integrity. The runner should read both records |
| N4 | NOTE | The volume check is one snapshot, taken right after "terminated". A volume still `deleting` would be listed even though it is not a leak. The exit code ignores the list. The analogy run listed none |
| N5 | NOTE | `jsonschema` is not installed, because the wheels go in with `--no-deps`. `cas_cjt` imports it only inside `_validator` (`cas_cjt/contracts.py:97`), which only contract validation uses. The analogy job ran the same wheel set without it and finished `done` |
| N6 | NOTE | The committed `dry_run_record.json` names `job_commit f9ee07aa`, because the dry run ran before the job commit. My dry run at `bd81e5b5` reproduced the same bundle and template |
| N7 | NOTE | Open coordinator questions stay open, and this review does not decide them. They are: whether this spend counts toward the $60 ceiling; which machine size to use (`g4dn.2xlarge` matches the reference history; `g4dn.xlarge` costs less). The worst case fits the $3.00 job ceiling either way |

## What this review does not establish

- **NOT RUN:** the four T4 checks, the preflight, and any GPU work. Whether check a reproduces the T4 reference
  digests is unknown until the job runs.
- **NOT LICENSED:** any statement about Helm's accuracy. This job checks plumbing only.
- **Not decided here:** the budget question and the machine size (N7). The launch itself is the runner's step,
  under the recorded standing authorization.

## EXPOSURE

- **Read (whole files):**
  - In this folder: all 8 files.
  - At `e05889ee`: `t4_larger_question_checks.py`, `larger_question_scope.py` and `larger_question_learner.py`.
  - The commit message and test diff of `e05889ee`.
  - `_handoffs/HELM_NEXT_PHASE_20260923/OWNER_STANDING_AUTHORIZATION_CLAUDE_20260924.md`.
- **Read in part:**
  - The V1-V5 notes of the verification record at `0cdd1a7b`.
  - Diffs of the analogy job's `job.sh.template` and `watch.py`, and its launch constants.
  - Four fields of its `watch_record.json`.
  - Chosen lines of `larger_question_fixtures.py` and of these `cas_meta2` modules: `source.py`, `input_frames.py`,
    `pointer_contract.py`, `pointer_learner.py`, `pointer_inputs.py`, `matched_contract.py`, `worker_contract.py`,
    `development.py`, `course.py`, `course_plan.py`, `gpu_adapter.py`, `cube_node.py`, and `typed_matched_worker.py`
    in `cncm`.
  - grep and AST scans (for file reads and imports) of the 79-file import closure.
  - The two wheels, copied from git objects to scratch: their import statements, their METADATA, and lines 86-106
    of `cas_cjt/contracts.py`.
- **Not opened:** any `*_eval.jsonl`; any file or folder named sealed; `D:/tksCAS-archive/`; any salt; the meta1
  ledger; Claude transcripts; the analogy job's `results/` and `attempt1/` folders. The harness saved one long tool
  output of mine (a listing of `launch.py`) under `C:/Users/wakil/.claude/projects/.../tool-results/`. I did not
  open that file.
- **Ran:** the torch-free tests once, and `launch.py --dry-run` once. No torch, no GPU, no training.
- **AWS:** one read-only `ec2.describe_images`. Also one read-only `git ls-remote`. No upload, no launch.
- **Scratch only:** small pure-Python scans, one at a time; a fake-folder drive of `read_results.py`.
- **Written to git:** this file only.
