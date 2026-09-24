# AWS job: HELM-LARGER-QUESTION-PATH-1 T4 checks (larger-question path, builder revision 2)

**Status: BUILT and dry-run only. NOT launched. NOT reviewed.** Label: `CLAUDE_BUILT_CLAUDE_CHECKED`.

## Authority (recorded, not invented)

- **Standing project approval, extended to Claude as runner** (owner, 2026-09-24, verbatim in
  `_handoffs/HELM_NEXT_PHASE_20260923/OWNER_STANDING_AUTHORIZATION_CLAUDE_20260924.md`, commit `ca68690b`). That
  record names "the larger-question T4 checks" as a prerequisite job that runs under this authority **once its own
  admission and review pass**.
- The owner's AWS order of 2026-09-23 ("use aws as there is only 354 mb of 16 gbs locally").
- `docs/OWNER_RUN_AUTHORIZATION_20260922.md`: every job names its source, task, resources, limits and results.
- **Execution admission: `NOT_READY`.** This folder has not been reviewed. The builder does not launch. The runner
  (the Claude coordinator) launches only after the review passes, and records that in the launch record.

## Limits

| Limit | Value |
|---|---|
| Machine | ONE `g4dn.2xlarge`: NVIDIA T4, 8 vCPU, 32 GiB, us-west-2, on-demand. It is the machine the T4 reference history (check a) was recorded on. `--instance-type g4dn.xlarge` (same T4, 4 vCPU, 16 GiB) is allowed |
| Price | $0.752/hour (`g4dn.xlarge`: $0.526/hour) |
| One GPU machine at a time | the launcher refuses if any GPU machine (g4dn, g4ad, g5, g5g, g6, g6e, gr6, p3, p3dn, p4d, p4de, p5, p5e, p5en) is pending, running or stopping. The GPU quota is 8 vCPU |
| Image | pinned `ami-07d69ce07bfe5628f` ("Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 24.04) 20260922"), the analogy T4 job's. **No substitute**: if it is gone, the launcher refuses (check a compares bits with that image's history) |
| Software | Python 3.14.7, torch 2.11.0 from the cu128 index (must report `2.11.0+cu128`), numpy 2.5.2, and both wheels installed with `--no-deps` from the bundle (sha256-pinned) |
| Environment | `CAS_META2_RUN_TEACHING_CYCLE=1`, `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2` (review V3), `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `PYTHONDONTWRITEBYTECODE=1` |
| Disk | 100 GB gp3, deleted with the machine |
| The script's own limit | 3,600 s wall. Its preflight (stage 1) refuses before any check if the projected total is over (exit 5) |
| In-machine timer | 120 minutes; the operating system powers off at 123 minutes; the machine is destroyed on shutdown |
| Client deadline | 130 minutes after launch. `watch.py` terminates the machine and waits for "terminated" |
| Worst case | (0.752 + 0.005 public address + 100 GB x 0.08 / 730 disk) = 0.767959 USD/hour; x 130/60 hours = **$1.6639**. For `g4dn.xlarge`: 0.541959 x 130/60 = $1.1742 |
| Ceiling | **$3.00** for this job. The launcher refuses unless the worst case is below it |
| Expected cost | ESTIMATE, not measured: about 50 to 65 minutes (setup 10 to 15, the script about 38 to 47 by the builder report's rough band, finish 2), so about $0.64 to $0.83 on `g4dn.2xlarge` |
| S3 | bucket `cas-harness-runpod-92754088`, prefix `helm-integration/larger-question-t4-<stamp>/`: the bundle (about 10 MB) and three uploads. Request and same-region transfer costs are cents or less. Objects are kept for the owner; Claude deletes no data |
| Credentials on the machine | **none**. Time-limited links only: one download (bundle) and three uploads (results, progress log, rows so far) |
| Work | forward passes only. No optimizer step, no checkpoint written, no training |
| Automatic retries | **none**. The launcher refuses if `launch_record.json` exists. The job runs the script once. Trying a second zone happens only when AWS refused to create the machine in the first |
| Cleanup evidence | `watch.py` confirms "terminated" and lists any volume still tagged with this job's name, in `watch_record.json` |

## What runs

- **Stage 0, smoke (job.sh).** torch is `2.11.0+cu128`, CUDA works on a T4; the two wheels import with their
  versions; the script's own `--list-inputs`, and every listed input present in the bundle with its bytes and sha256.
  Any failure stops the job by name (`SMOKE_FAILED` or `SMOKE_LIST_INPUTS_FAILED`).
- **Stage 1, the script's own timing preflight.** About 20 timed forward passes, inside the script's process, before
  any check. Over its 3,600 s projection: `PREFLIGHT_OVER_WALL_LIMIT`, exit 5, job status
  `STAGE1_PREFLIGHT_OVER_WALL_LIMIT`.
- **Stage 2, checks d, c, b, a**, same process. Every finished row is written at once to
  `larger_path_result.json.rows.jsonl`; the summary `larger_path_result.json` is written once.

## Source binding

- Code under test: `claude/helm-builder-continuation-20260923` at `e05889eec0f800a9a17b0c39a8d8d37f544b43bf`
  (builder revision 2). The launcher checks the commit is on the pushed branch (asks the remote for its tip).
- The bundle is built from git objects at that one commit. Its file list comes from the pinned script's own
  `--list-inputs`. The six checkpoints must equal the analogy T4 job's six.

## Budget question for the coordinator

- The standing record keeps a $60.00 ceiling for the main comparison. Whether this prerequisite job's spend counts
  toward it is not stated there. The coordinator decides; this file does not.
