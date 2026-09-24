# Environment lock for the unchanged arm - candidate, with its blockers

Label: CLAUDE_BUILT_CLAUDE_CHECKED. Not yet checked by Codex. Date: 2026-09-24.
Branch: `claude/helm-unchanged-reader-rev-20260924` (on top of reader revision 5, `55182f5f`).

## What this is

The environment lock is the list of machine and software facts a reproduction must match: Python, torch, CUDA,
cuDNN, the GPU, the driver, the kernel, the maths settings, and so on. Its format is `helm.reproduction-environment/1`
(Codex ruling R3-I). Every value must come from public historical records of the Helm 2.0 seed-17 run. A value that
those records cannot establish is written as the exact text `UNESTABLISHED_FROM_PUBLIC_HISTORICAL_RECORDS`. That text
is an explicit blocker: the reader treats it as `ENVIRONMENT_ADMISSION_UNVERIFIED`, which makes the evidence INVALID
(Codex ruling Q-G). Nothing here was taken from this laptop, and nothing was guessed.

Files (all in this folder):

- `ENVIRONMENT_LOCK_CANDIDATE.json` - the lock itself (sha256 `4059b88810d800f5f7356facba6fd463b3946d349b97a56e7055a65171356419`).
- `ENVIRONMENT_LOCK_SOURCES.json` - for every field: its value, why, and the exact commit, path and place of each
  source; for every blocker: why it is not established, any part that is, and any candidate value with its sources.
- `check_environment_lock.py` - re-reads every cited source from git and runs the reader's own validator.

The `status` field says `FROZEN` because that is the only status the schema accepts. "Candidate" means Codex has not
checked it yet and no eligibility record binds it yet. Every lock field is required-equal, driver and kernel included;
`diagnostic_only` is empty.

## Filled fields (16)

| Field | Value | Evidence class | Main source |
|---|---|---|---|
| image.provider | aws | RUN_RECORD | receipt_20260917 `preflight.json` (AmazonEC2), `launch.json` @ c8d5c430 |
| image.region | us-west-2 | RUN_RECORD | receipts 17/18/19 `preflight.json` @ c8d5c430, 27fd5698 |
| image.ami_id | ami-0fbbd0facbc9e3cff | RUN_RECORD | same three `preflight.json` |
| runtime.os | Linux | PACKAGE_CODE | `gpu_adapter.execution_guard` @ 20208c92 refuses non-Linux; run completed |
| runtime.machine | x86_64 | IMAGE_METADATA | AMI `describe_images` record `03_ami.json` @ 41ff8407 (Architecture x86_64) |
| accelerator.instance_type | g7.2xlarge | RUN_RECORD | three `preflight.json` |
| accelerator.gpu_model | NVIDIA RTX PRO 4500 Blackwell Server Edition | RUN_RECORD | three `worker_report.json` runtime |
| libraries.torch | 2.11.0+cu128 | RUN_RECORD | three `worker_report.json` runtime; worker refuses anything else |
| libraries.cuda_runtime | 12.8 | RUN_RECORD | three `worker_report.json` runtime |
| numerics.dtype | float32 | PACKAGE_CODE_WITH_PINNED_LIBRARY_DEFAULT | learner code @ 20208c92; archive scan; checkpoint `float32LE` |
| numerics.deterministic_algorithms | true | PACKAGE_CODE | `typed_pointer_worker._preflight` @ 20208c92 |
| numerics.matmul_allow_tf32 | false | PACKAGE_CODE | same |
| numerics.cudnn_allow_tf32 | false | PACKAGE_CODE | same |
| numerics.float32_matmul_precision | highest | PACKAGE_CODE_WITH_PINNED_LIBRARY_DEFAULT | archive never sets it; allow_tf32=False; torch 2.11.0 default |
| numerics.seeds | model 20260917, python 20260917, encoder 20260916, source 101 | RUN_RECORD | `worker_report.json` design, checkpoint init_args @ c8d5c430 |
| numerics.environment_variables | CUBLAS_WORKSPACE_CONFIG=:4096:8 | PACKAGE_CODE | worker preflight; run's `loaded_sources.json` has no thread/env-setting module |

## Blockers (8, exact)

| Field | Why it is not established | Candidate from ANOTHER job on the same AMI (not in the lock) |
|---|---|---|
| runtime.kernel | no Helm 2.0 record | 6.17.0-1020-aws (teaching job 003 pip report @ 4847bd9f) |
| runtime.python_implementation | no Helm 2.0 record | CPython (job 003 pip report) |
| runtime.python_version | no Helm 2.0 record; package allows 3.11 or 3.12 | 3.12.3 (job 003); python3.12 selected in graph6read and typed-course consoles |
| accelerator.compute_capability | never recorded by any job | none (vendor tables say 12.0; not a record, not offered) |
| accelerator.driver_version | no Helm 2.0 record | 595.91.07 (graph6read console @ 38b5ea96; typed-course console @ a0471107) |
| libraries.cudnn | torch installed without hashes; cuDNN never recorded | 9.19.0 (pip resolved nvidia-cudnn-cu12==9.19.0.56 from torch==2.11.0 in job 003 and typed-course) |
| libraries.packages | no installed-wheel list or third-party SHA-256 was recorded | none; only the 2 project wheels (with SHA-256) and 4 pinned versions are known |
| numerics.thread_counts | the run set no thread count; torch's machine default was never recorded | none |

## What this means

- Under reader revision 5, every source reads `ENVIRONMENT_ADMISSION_UNVERIFIED` on these 8 fields. So a strict
  option-C environment admission for the unchanged arm is INVALID as things stand. Codex ruling Q-G already says
  this is the correct outcome, and that exact state and panel comparisons may still be reported as conditional
  diagnostics.
- Five blockers could be filled mechanically if Codex rules that a record from another job on the same, unchanged
  AMI establishes the Helm 2.0 value (kernel, Python implementation, Python version, driver, cuDNN).
- Two blockers can never be filled from public history: `libraries.packages` and `numerics.thread_counts`. So the
  strict admission stays UNVERIFIED even after that ruling, unless Codex rules differently on what those two fields
  must hold for a historical run.

## Disclosed residuals (not blockers)

- R1: `environment_variables` holds the one maths-affecting variable the package sets. No record lists the rest of
  the process environment, so the absence of others (for example NVIDIA_TF32_OVERRIDE) is not recorded. Revision 5
  refuses a lock whose map lacks CUBLAS_WORKSPACE_CONFIG, so this field cannot be a blocker.
- R2 and R3: `float32_matmul_precision` and `dtype` rest on package code plus torch 2.11.0's documented default. If
  Codex does not accept that evidence class, they become blockers 9 and 10.

## Checks run (CLAUDE_BUILT_CLAUDE_CHECKED)

`python -B check_environment_lock.py` -> exit 0, `result: PASS`:

- 101 citations re-read from git; all 9 cited commits are ancestors of a pushed branch.
- Reader revision 4 (`fee4ebec`): its validator accepts the structure. Its only refusals are the 6 value-level ones
  the blockers cause. With the blockers replaced by well-typed placeholders it accepts the lock outright. Revision 4
  cannot tell the marker from a text value for `runtime.kernel` and `runtime.python_implementation`. Those two still
  fail closed when compared, and revision 5 names them explicitly.
- Reader revision 5 (`55182f5f`): its validator accepts the lock. It lists exactly the same 8 blockers. The Helm 2.0
  seed-17 recorded runtime matches every filled field it records.
- A separate scratch mutation run (not committed) made 12 deliberate errors, and the checker caught all 12. The errors
  included a changed value, a wrong citation, a guessed blocker, the driver moved to diagnostic, and an unpushed commit.
- The reader test suite was not run: no reader source changed. The folder's ASCII/LF rule holds for the new files
  (the checker tests it).

## EXPOSURE

- Read: public git objects only. These were the Helm 2.0 receipts (c8d5c430, 27fd5698), package source 20208c92,
  package receipt 3da10d84 and its archive, AMI record 41ff8407, teaching job 003 artifacts (4847bd9f), the graph6read
  receipt (9ca4a653, 38b5ea96), the typed-numeric receipt and console (a0471107), and Codex rulings dc02eb81.
- Found while searching `result.json` and `intent.json` of receipt_20260917 for runtime fields: those public receipts
  embed ledger copies. The search output showed a few plan fields from them (AMI id, torch version, another job's
  resource plan). None of those fields was used as a source.
- To check what "highest" means, I read the text of `torch/__init__.py` (torch 2.11.0) in the local venv. I did not
  import it or run torch. That file is not a source of the lock; the lock points to public PyTorch documentation.
- Not opened: any `*_eval.jsonl`, sealed files, D:/tksCAS-archive/, salts, S3, the meta1 ledger, protected
  examinations or transcripts. No AWS call and no torch run. No python process was signalled.
