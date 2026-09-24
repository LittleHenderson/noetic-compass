# AWS job: historical gates + rescorer 0.4 (readout plan item 7)

Label: `CLAUDE_BUILT_CLAUDE_CHECKED`. Status: **built, dry-run tested, NOT LAUNCHED.** Custody:
`EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT`.

## What it is, in plain words

One rented CPU computer on AWS runs two existing programs. Nothing is trained. No model runs. No torch is installed.

- **The frozen grader** (`records/typed_pointer_001/evaluate_gates.py`, LF sha256 `d3e0ea97...`). It prints the
  historical gate reading: H1 (`G_LEARN_population`) and H2 (`G_LEARN_all_kinds`). It loads the frozen course. That
  ran the laptop out of memory, so it runs only on AWS.
- **The trusted rescorer 0.4 revision 1** (`records/typed_pointer_001/trusted_rescore.py`, LF sha256 `c3d6bdd0...`,
  delta review `0d6bc2fd` APPROVE). It re-checks every raw prediction and re-derives the label. It has never run on AWS.

There are two modes. Each mode gets its own launch record, so each is one launch.

| Mode | Study | Must show |
|---|---|---|
| 1 | Helm 2.0 only: `admission_001/study.json`, from commit `0d6bc2fd` | The grader reproduces the committed `admission_001/gate_reading.json` exactly: canonical sha256 `52877c16...`, label `NO_TRANSFER_TO_NEW_WORLDS`, H1 11/1, 12/0, 7/1. The rescorer passes its builder report's R1.7 steps 3-6 on the Helm 2.0 study: step 3 exit 4, step 4 exit 4, step 6 anchor exit 0 then `RESCORE_OK` exit 0, step 5 (its three test files, slow tests on) exit 0. |
| 2 | The repaired (switch-ON) study `admission_analogy_on_001/seeds/study.json` (sha256 `c0d65ce8...`) | **Refused unless an ITEM2_PASS record is given** (prereg A5.3). Then: the grader's label, printed as a historical-rule reading of the ON arm (diagnostic only; no transfer claim, no promotion), and a trusted rescore that agrees with it (`RESCORE_OK`). Nothing is placed beside Helm 2.0 (A5.5). |

"Reproduce exactly" means this. The grader prints its reading with indentation. The job re-writes it in the
committed form (sorted keys, no spaces, one newline). The sha256 of that must equal the committed file's sha256. The
reading has no file paths in it, so the Linux paths cannot change it.

## Limits

| Limit | Value |
|---|---|
| Machine | ONE `c7i.2xlarge` (8 vCPU, 16 GiB), `us-west-2`, on-demand, $0.357/hour, CPU only. It uses no GPU quota. |
| Tools | uv `0.12.17` from its versioned installer, Python `3.14.7`, pytest `9.1.1`: the set T01 measured on this machine type. The machine stops if the uv or Python version differs. |
| Disk | 20 GB gp3, deleted with the machine. Mode 1 unpacks six copies of the bundle (about 2.5 GB). |
| In-machine timer | 80 minutes. The operating system powers off at 83 minutes. The machine is destroyed on shutdown. |
| Client deadline | 90 minutes after launch. `watch.py` terminates the machine and retries until AWS confirms. |
| Worst case | (0.357 + 0.005 public address + 20 x 0.08 / 730 disk) = $0.36419 per hour; x 90/60 hours = **$0.5463**. |
| Cap | **$0.60 per launch**, plus the **$0.10 allowance** in the ledger = $0.70. `launch.py` refuses if the worst case is above the cap. |
| Expected | Mode 1 about 45-60 minutes (T01's slow tests alone took 41 minutes), about $0.27-$0.36. Mode 2 about 20-35 minutes. |
| Retries | None. One launch attempt, one zone, no relaunch. `launch_record_mode<N>.json` refuses a second launch. |
| Machine id | The machine reads its own instance id through IMDSv2 and writes `instance_id=<id>` into `env.txt`. It stops if it cannot. `read_results.py` requires that id to equal the launched one. |
| Credentials on the machine | None. Presigned links only: one download (the bundle) and two uploads (progress log, results). Links last 4 hours. |
| Left behind on AWS | Only the S3 objects under `helm-integration/gates-job-mode<N>-<stamp>/` in the existing private bucket. No key pair, role, Elastic IP or snapshot. |

## The bundle (built from git objects, never from working files)

`launch.py` reads every file straight from git objects at the source commit, one blob at a time, and streams a
deterministic `tar.gz` into a new folder outside every git tree. It never holds the bundle in memory.

Measured by the laptop dry run (mode 1, 2026-09-24): **619 files, 418.7 MB raw, 122.6 MB compressed, bundle sha256
`fac13b9f529baab76fe1420228629fe6540148632ff55fd75af9160ad6967bbf`**. It took about 20 seconds.

What is in it (an allowlist):
- code: every `.py` under `cncm/` and `research/CAS_META_2_COMPOSITION/cas_meta2/`;
- pinned data: the public course, the training tokenizer, the compact development file, the two development
  reference files, the practice and matched start records `initial_checkpoint.json` (I3), and the practice grader;
- `records/typed_pointer_001/`: its top-level `.py` and `.json` files (the grader, the rescorer, its three tests,
  studies, anchors, readings), `history/trusted_rescore_0_3.py`, both admissions' `gate_reading.json`, `admission_001/study.json`,
  and T01's `aws_rescore_job/results/*.json` (the rescorer's tests compare against them);
- Helm 2.0 receipts `receipt_2026091{7,8,9}`: `result.json`, `artifact_manifest.json` and the whole
  `collected/results/artifacts/` folder (the grader reads it; it holds the five weight files per seed);
- Helm 1.0 receipts `receipt_helm1_certified_2026091{7,8,9}`: `artifact_manifest.json`, the four label files and the
  five weight files each. Only the rescorer's tests read these.
- `claude/machine_gates.py` (this job's program) and `anchors.json` (sha256 of every file).

Pins checked on every build (LF sha256): the grader `d3e0ea97...`, the rescorer `c3d6bdd0...`, its three test files,
the course, the tokenizer, the development file, the study, and the committed reading `52877c16...`. A mismatch refuses.

## Custody

- The allowlist above, plus a second filter on every bundle name. It refuses any name containing `sealed`,
  `_eval.jsonl`, `salt`, `private_target`, `protected`, `transcript`, `hset` or `tkscas-archive`, anything under
  `records/helm_eval_design_20260923/`, any `__pycache__`, and any `..` path.
- Nothing comes from `D:/tksCAS-archive/`, S3 or a salt. No HSET material, no protected examination, no transcript.
- Everything in the bundle is public course material, code, receipts and weights already committed in git.

## What runs on the machine

0. Instance id (IMDSv2) into `env.txt`. Tools. Bundle download and sha256 check. Every file against `anchors.json`
   (a changed, missing or unlisted file stops the job).
1. **Mode 1**, four stages at once, each in its own copy of the bundle:
   - gates: `machine_gates.py gates` makes a Linux-path copy of the study (only each `receipt_dir` changes; the
     folder name is kept), runs the grader unchanged, writes `gate_reading_fresh.json` and
     `GATES_READING_SUMMARY.json`, and reads `GATES_REPRODUCED` or `GATES_NOT_REPRODUCED` with reasons;
   - rescorer R1.7 steps 3 and 4 (historical-compatibility mode);
   - rescorer R1.7 step 6 (trusted mode): a new schema-0.4 anchor `trust_anchor_helm2_experimental_v0_4.json`, then a
     full rescore against `admission_001/gate_reading.json`;
   - rescorer R1.7 step 5: `test_trusted_rescore.py`, `test_historical_compatibility.py` and
     `test_historical_rescore_rule.py`, one process each, `HELM_RUN_SLOW_TESTS=1`.
   **Mode 2**: the grader on the repaired study, then a trusted anchor and a rescore against that fresh reading.
2. `machine_gates.py decide` writes `GATES_JOB_RESULT.json`. `STATUS` is `done` only when every expected exit code
   and output holds. Mode 1 reports two separate readings: the gates verdict and `RESCORER_0_4_AWS_ACCEPTED` /
   `RESCORER_0_4_NOT_ACCEPTED`. A failed expectation is a FAILURE with its name.
3. `memory.log` records memory use every 30 seconds. Peak memory for these programs has never been measured.

## Mode 2: the ITEM2 record it needs

`--item2-pass PATH` must be a file committed in this repository and unchanged. It must be the output of the ITEM2
reader for probe v0.3 (`readout/probe-v03/item2_reader.py`, schema `claude.item2-reading/0.3`, as drafted on
2026-09-24), with:
- `outcome` = `ITEM2_PASS`;
- `historical_gate_on_repaired_arm` = `MAY_RUN_FROZEN_EVALUATE_GATES` (the reader's own decision);
- `entries`: the 18 A5.1 checkpoints (3 seeds x `pass_01.pt`, `evidence/main_checkpoint_0294/0588/0882/1176.pt`,
  `final.pt`), each once, `verdict` = `PRESENT_GRAPH_AND_DOMAIN`, `problems` = `[]`, and a `checkpoint_sha256`.
The launcher then checks each `checkpoint_sha256` against the checkpoint file in the receipts it will read. A record
for other checkpoints is refused. The check runs FIRST, before any receipt is read. Without the record the answer is
`G_LEARN_ON_NOT_READ`.

`--receipts-commit SHA` must be ONE commit that holds the repaired study and all three repaired receipts (a merge
commit, if each receipt was committed on its own branch). A `gate_reading.json` already committed beside the study
is refused: the repaired arm is read once.

## Before launch (the coordinator)

1. Fetch this branch. Run `python -B launch.py --mode 1 --dry-run` from a clean checkout. The bundle sha256 should be
   `fac13b9f...` (it depends only on commit `0d6bc2fd` and the job files, not on later commits to this branch).
2. Check the money rule: measured spend S + $0.60 cap + $0.10 must be at most $60.00, and the R19 rule (S <= $30.00
   before R19; no paid job between R18 and R19).
3. Decide whether a CPU machine may run while training runs (plan call (b)). This job uses no GPU quota.
4. Launch: `python -B launch.py --mode 1`, then `python -B watch.py --mode 1`, then `python -B read_results.py --mode 1`
   (writes `RESULTS_READING_mode1.json`; exit 0 only for `JOB_ACCEPTED`).
5. Record source, purpose, instance, time and cost limits and cleanup (owner AWS rule). Commit the records.

## Open questions (not decided by the builder)

1. Mode 2's ITEM2 check follows a DRAFT reader (uncommitted when this was built). If its output shape changes, change
   `validate_item2_record` in one commit.
2. Mode 2 needs one commit with all three repaired receipts. The plan says each receipt is committed on its own branch.
   Who makes the merge commit?
3. Mode 2 reads the ON receipts with the tree at the receipts commit, and takes only `trusted_rescore.py` from
   `0d6bc2fd`. Is that the right combination?
4. A5.3 also asks for the 5 analogy questions next to the zero-learning rule LB18's answers, and the 11/18, 16/18 and
   18/18 floors. The job prints the per-checkpoint analogy counts and the grader's own zero-learning union (11 of 18)
   only. The LB18 comparison is not built.
5. Rescorer NOTE 7 (a rescore with `--no-frozen-reading` can still give `RESCORE_OK`) is not used here: every rescore in
   this job compares with a grader reading.
