# AWS job: HELM-ANALOGY-REPAIR-1 acceptance item 1 on a T4 (prereg amendments A3 and A4)

**Authority.**
- The owner's takeover instruction in chat, 2026-09-23: "Complete the required historical OFF-control and ON-effect
  checks", and "Follow my current AWS preference and the actual standing authorization, job limits and cleanup
  requirements. Do not ... treat this staffing change as expanded spending permission."
- The AWS order of 2026-09-23.
- The standing authorization `docs/OWNER_RUN_AUTHORIZATION_20260922.md`. It requires every job to name its source,
  task, resources, limits and results.
- **These limits are exactly the previous T4 job's.** Nothing is expanded.

**Runner.** The Claude coordinator, the only runner of this job. The read-only fix is built by a separate Claude
builder, so every outcome is labelled `CLAUDE_BUILT_CLAUDE_CHECKED`.

| Limit | Value |
|---|---|
| Machine | ONE `g4dn.2xlarge`: NVIDIA T4, 8 vCPU, 32 GiB, us-west-2, on-demand. The GPU quota is 8 vCPU, so the launcher refuses if any GPU machine is running |
| Price | $0.752/hour |
| Image | pinned `ami-07d69ce07bfe5628f` (the reference job's). If it is retired, the SSM "latest" base image is used and recorded as a SUBSTITUTE |
| Software | Python 3.14.7, torch 2.11.0 (cu128), numpy 2.5.2, pytest, and the two wheels by sha256: the reference environment |
| Disk | 100 GB gp3, deleted with the machine |
| In-machine timer | 150 minutes, then the operating system powers off at 153. The machine is destroyed on shutdown |
| Client deadline | 160 minutes after launch. `watch.py` terminates the machine and waits for "terminated" |
| Worst-case cost | 160/60 x (0.752 + 0.005 public address + 0.011 disk) = **$2.05**. **Ceiling $3.00** |
| Expected cost | about $0.60 to $0.70: roughly 50 to 55 minutes |
| Credentials on the machine | **none**. Presigned links only: one download and two uploads |
| Work | forward passes only, plus pytest of the switch tests. No optimizer, no checkpoint written, no training |
| Automatic retries | none. The launcher refuses to run twice (`launch_record.json`) |
| Cleanup evidence | the watcher confirms "terminated" and that no volume tagged with this job's name remains. S3 objects are kept for the owner; Claude deletes no data |

**What runs.** The stages are in prereg amendment A4.1:
- stage 0: switch tests, plus the frozen read-only check;
- stage 1: the unchanged-source control, 9 models;
- stage 2: repaired OFF, 9 models;
- stage 3: 3 OFF probes and 1 fresh-ON probe.

**The verdict.** `read_results.py` emits it by A4.3. The fresh-ON reading is `FRESH_ON_REPORT_ONLY`.

**Source binding.** The repaired commit R is passed explicitly, must be on
`claude/helm-builder-continuation-20260923`, and must differ from `20208c92` in existing bundled code only in
`pointer_learner.py`. The bundle is built from git objects. The six checkpoints must match the reference job's
sha256.
