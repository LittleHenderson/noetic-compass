# CAS-META-1 bounded AWS pilot

This launcher is **plan-only by default**. A passing local contract test does not
prove that a cloud job ran. The owner approved a **$100 total task budget** on
2026-09-05. Approval is not evidence that a paid run has happened.

## Proposed limits

- One new On-Demand `g4dn.xlarge` in `us-west-2`; no retries or larger fallback.
- Each attempted job reserves **$2.00** from the approved **$100.00 total** before
  any cloud write. `records/aws_budget_ledger.json` uses an exclusive lock and
  an atomic update. Failed starts keep their reservation. There is no automatic
  refund or retry; 50 reservations exhaust the budget. A stale lock fails closed.
  Keep this one canonical ledger; copying the pilot does not create another budget.
- Maximum 60 minutes from launch; training gets at most 45 minutes and stops
  earlier to leave time for evidence upload. A boot-time shutdown timer, a
  confirmed cloud-side EventBridge Scheduler termination, and a client watchdog
  cover different failure modes. No training starts without the cloud permit.
- 75 GB encrypted gp3, `DeleteOnTermination=true`, no snapshots or reserved
  capacity. No inbound connections or public SSH. Egress is restricted to HTTPS;
  this is a port restriction, not a total network-byte quota or domain firewall.
- At most 1 GiB of job output, including its bounded bootstrap log. The dedicated
  S3 bucket expires all objects after seven days. The client downloads the result
  ZIP into a new directory inside this pilot and checks its SHA-256. Keep that
  local evidence durably before the seven days expire. An empty bucket may
  remain; bucket names themselves do not incur storage charges.

Current Oregon pricing was checked through the official AWS Price List API on
2026-09-05, with effective date 2026-09-01: `$0.526/hour` for the selected Linux
instance and `$0.08/GB-month` for gp3. One hour of compute and 75 GB storage is
about `$0.5343`, before IPv4, storage requests, transfer, retention, and taxes.
The launcher refuses a changed compute rate. **This is not an unconditional AWS
billing guarantee:** provider/control-plane failure can delay termination, and
billing reports are delayed. AWS Budgets is not the shutdown mechanism.

## Archive contract

The parent build creates one ZIP and separately records its full SHA-256 and
source commit. At its root, `launch_manifest.json` contains:

```json
{
  "schema_version": 1,
  "source_sha": "FULL_40_CHARACTER_PILOT_SOURCE_COMMIT",
  "baseline_sha": "0917267b1354e5d036263eaa6ba9a7197eafb776",
  "pilot_dir": "research/CAS_META_1_LEARNED_SELECTION",
  "data_dir": "research/CAS_META_1_LEARNED_SELECTION/data",
  "wheel_paths": ["wheels/first_frozen.whl", "wheels/second_frozen.whl"],
  "dependency_lock": "research/CAS_META_1_LEARNED_SELECTION/requirements-gpu.txt",
  "files_sha256": {"EVERY_NON_DIRECTORY_ENTRY_EXCEPT_THIS_MANIFEST": "SHA256"}
}
```

The manifest's complete member set and hashes are checked before any cloud
write. Paths must be relative POSIX paths; duplicates, symlinks, traversal,
unlisted files and expanded archives above 512 MiB are refused. Both frozen
wheels install with `--no-deps`; the accepted sources are never edited.

The GPU lock must be a separate Linux-compatible pinned dependency list. It
must not reference a CPU PyTorch build or override package sources. The launcher
installs `torch==2.11.0` from the official CUDA 12.8 index. It then requires exact
runtime version `2.11.0+cu128`, CUDA `12.8`, and exactly one available CUDA GPU.
The AMI must provide Python 3.11 or 3.12 and AWS CLI; missing prerequisites cause
refusal and termination, not local execution. The runtime, package freeze, pip
installation reports, source/archive identities, command, and result hashes are
retained in the cloud output. The running launcher and plan must also match their
archive hashes before any cloud write. This remote bootstrap remains unproven until run.

Before training, the job enables and runs the four GPU integration tests. It
requires a JUnit receipt with exactly four tests, zero failures, zero errors, and
zero skips. The training command then runs its separate nine TRAIN-only anchors.
GPU test evidence and training evidence are both packaged under the pilot's
`runs` directory. Python bytecode writes are disabled before importing the frozen
packages. Every stage consumes the same 60-minute cloud deadline.

## Commands

From this pilot directory, using a Python interpreter with `boto3` available for
the eventual launch:

```powershell
# No AWS reads or writes. Prints the proposed plan.
python aws/launch.py

# Read-only local ZIP validation, still no AWS actions.
python aws/launch.py --archive PATH_TO_ZIP --sha256 FULL_ZIP_SHA256 --source-sha FULL_SOURCE_SHA

# Owner approved $100 total; this attempted job reserves $2 from that total.
python aws/launch.py --execute --approved-cap-usd 100 --archive PATH_TO_ZIP --sha256 FULL_ZIP_SHA256 --source-sha FULL_SOURCE_SHA --subnet-id subnet-02deacfa16bdaa4f4 --receipt-dir NEW_ABSOLUTE_DIRECTORY_INSIDE_THIS_PILOT
```

The selected subnet must already provide internet routing for HTTPS downloads.
The shown subnet was read-only checked on 2026-09-05: `us-west-2b`, default VPC
`vpc-0df2f8cc1b9f23838`, with an active default route to an Internet Gateway.
The launcher creates no NAT gateway. It verifies the expected AWS account and
AMI, and creates a dedicated job bucket, two narrowly scoped roles, an instance
profile, and an outbound-only security group. It never starts, stops, or changes
an existing instance. The scheduled termination targets the newly created
instance and is additionally restricted by the unique job tag.

The remote command is:

```text
python -m cas_meta1.train --data DATA --output OUTPUT
```

Neural work is only remote. The client validates files, calls AWS, records
receipts, waits, and downloads evidence. It does not import PyTorch.

## Failure and cleanup

The launcher records IDs immediately after each creation. Its `finally` block
checks the new instance's job tag, requests termination, and waits for a provider
termination receipt. Only after confirmed termination does it remove its own
schedule, instance profile, roles, and security group. Failed cleanup is explicit
`CLEANUP_REQUIRES_ATTENTION`, never a claim that resources are gone. The scheduled
termination is retained if instance termination cannot be confirmed.
If the launch response is lost, the client searches for the exact unique job tag
and launch token. An empty or ambiguous response is **not** treated as proof that
no instance exists. It reports `TERMINATION_UNCONFIRMED` and retains supporting
resources until the instance's identity and termination can be confirmed.

S3 data uses the seven-day lifecycle even after failure, so logs are not erased
to make a failed job appear clean. No unrelated resources are cleaned up. The
local receipt identifies anything left behind. Early bootstrap failure may
produce only the bounded S3 bootstrap log rather than a training artifact ZIP.
If output exceeds the ceiling, the job uploads a bounded failure ZIP containing
log tails, small receipts and candidate checkpoints when they fit, plus a file
index digest and explicit omitted-file counts. Partial evidence never counts as
a successful job. Original source files and checkpoints are not deleted to fit.

The current readiness check is not a launch receipt: EC2 G/VT quota was eight
vCPUs, while SageMaker g4dn/g5 training quotas were zero. The old shared GPU role
and its old S3 prefix are deliberately not reused. The selected AMI is pinned
to Ubuntu 24.04 image `ami-0fbbd0facbc9e3cff` (20260821). Its live Oregon image
record declares a 75 GB `/dev/sda1` root and G4dn support. The
[exact AWS release notes](https://docs.aws.amazon.com/dlami/latest/devguide/aws-deep-learning-ami-gpubaseoss-ul2404-2026-08-24.html)
declare Python 3.12. The earlier unlaunched Ubuntu 22.04 image was replaced
because its documented Python 3.10 is too old for the frozen wheels.
Remote AWS CLI, virtual-environment setup and GPU compatibility still need the guarded run.

Sources: [AWS Price List](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html),
[Scheduler targets](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-targets-universal.html),
[EC2 shutdown behavior](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_ChangingInstanceInitiatedShutdownBehavior.html),
[AWS budget delays](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html),
[PyTorch 2.11 CUDA builds](https://pytorch.org/blog/pytorch-2-11-release-blog/).
