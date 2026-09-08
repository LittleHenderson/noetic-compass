# Teaching v2: AWS transport and independent result reading

This is the new teaching job, not a retry of frozen condition-skill v9. It uses
the unchanged `bundle_002` worker, seven-stage material, four candidate arms,
and development-only checkpoint selection. Accepted models and native executors
are unchanged. Integration tests use fake processes and clients; they are not
neural teaching results.

The source directory for the commands below is:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION`

## One bounded job

The new request records the existing inclusive $400 campaign authority, exact
source and data identities, and a fresh $8 reservation. It never reuses v9's
authority or resets the ledger. Reservation is not an AWS invoice.

One `g7.2xlarge`, one RTX PRO 4500, account `807562639912`, `us-west-2`. No T4.
The parent has one shared 7,200-second deadline. Setup, a training worker capped
at 4,800 seconds, two prediction processes capped at 300 seconds each, and
collection fit inside it. The subprocess supervisor leaves a short margin for
the worker to save its checkpoint before the process limit. An independently
configured termination schedule is read back before the worker permit is sent.
A guest shutdown timer adds a second protection; neither is a promise that AWS
can never experience a service delay or failure.

The artifact limit is 2.5 GiB across the job. Transfers stream without loading
the archive into RAM. S3 request attempts include failed calls and polls:
1,024 parent + 896 guest + 128 bootstrap = 2,048. Cloud results keep a seven-day
expiration policy; that is not a claim of physical deletion exactly at hour 168.
The cost worksheet conservatively prices three decimal GB for a full month.

The fresh read-only pricing receipt in `live_preflight_001/receipt.json` observed
$2.52 per instance hour and a conservative worksheet of $6.417097142857142857142857143,
including $1 of additional allowance, below the $8 ceiling. It found the expected
GPU and no conflicting CAS/G instances. Refresh these mutable facts before
launch. Offering, quota, configuration and IAM readback do not guarantee capacity
or successful in-guest CUDA execution.

## Run and retain evidence

Use Python 3.12 for pure local checks. No local neural, NumPy or SQLite work:

```text
python -I -B tools/check_teaching_launch.py records/teaching_cycle_001/transport_checks_NEW
```

Use the AWS-enabled Python installation for the explicit read-only preflight:

```text
python -B aws/teaching_cycle_preflight.py --output records/teaching_cycle_001/live_preflight_NEW
```

After committing the tested source, create an inert request from its actual Git
blobs, the current canonical ledger, successful fresh pricing and existing owner
approval. This exports only the public final inputs, not private targets:

```text
python -I -B tools/prepare_teaching_launch.py --output records/teaching_cycle_001/job_NEW --pricing-receipt records/teaching_cycle_001/live_preflight_NEW/receipt.json
```

That command returns the preparation receipt and its raw SHA256. Run exactly
that job through the separately gated command, supplying that returned digest:

```text
python -B tools/run_teaching_launch.py --execute --preparation records/teaching_cycle_001/job_NEW/receipt.json --preparation-sha256 RETURNED_SHA256 --receipt-dir records/teaching_cycle_001/job_NEW/launch
```

Without `--execute`, the command reports `NOT_LAUNCHED` and makes no provider call.
The launcher rechecks source/data/authority bytes, the whole budget history and
fresh provider state. Any source or ledger change requires a fresh preparation,
not an edit to an already bound request. No workload or reservation retry occurs.

## What the guest receives

Before training: the 17-file training bundle, pinned bootstrap/configuration and
schedule-bound permit. The bundle contains 256 training cases and 64 development
cases. Private final answers and the teacher scorer never enter the guest bucket.

After training exits and the parent validates its allocation and selected
checkpoints: the parent releases three public sets of 64 cases. Two fresh child
processes load the same initial and selected checkpoints and each produce 24
sealed prediction files. The training process is already dead at public release.

During training, an optional progress receipt reports the first saved CUDA
optimizer event. The parent checks it at most once per minute and preserves its
exact bytes. `WORKER_REPORTED_FIRST_CUDA_UPDATE` means the worker reported an
update; it is not independent proof of GPU execution, learning or mastery.
Missing progress telemetry does not change the final result checks.

The job bucket allows only its own named input reads and result writes. Its
bucket-list permission permits missing-object polls to return 404 rather than 403;
it gives no access to another bucket. This follows the documented
[S3 HeadObject permission behavior](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html).

Partial teaching preserves available checkpoints, optimizer state and exposure
records. It receives no final public data and is reported `TEACHING_INCOMPLETE`,
not failure of the teaching method. A refused/no-effects launch does not clean
up resources belonging to an existing job with the same name.

## Read the result independently

After collection, use the saved parent `result.json`, original `artifacts.zip`
and raw `complete.json`, supplying independently retained raw digests:

```text
python -I -B tools/evaluate_teaching_launch.py --parent-result PARENT_RESULT --parent-sha256 PARENT_SHA --archive ARCHIVE --archive-sha256 ARCHIVE_SHA --complete-marker COMPLETE_JSON --complete-sha256 COMPLETE_SHA --material-root records/teaching_cycle_001/material_001 --output records/teaching_cycle_001/evaluation_NEW
```

This checks archive paths, hashes and limits, keeps the original ZIP, admits
both prediction packets, and compares their predictions, public inputs and
checkpoint identities before private targets are opened. The frozen scorer
then reports before/after binding correctness with attempted-task denominators
for each arm and split. A process ID alone is not restart proof.

The fresh, context and name splits do not test unseen nested programs. Binding
correctness is separate from actual native call bytes and native A correctness.
Native execution and retention after intervening learning remain later phases.
The familiar 24/24 and earlier held-out CAS 0/72 results remain separate evidence.
No new learning, mastery, CAS advantage, language, general reasoning or complete
CNCM claim follows from transport tests or valid trace hashes.
