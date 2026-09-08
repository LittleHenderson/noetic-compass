# Seven-stage teaching integration v2

Status: runnable candidate training and blind-binding evaluation code; NOT TRAINED.
This dated follow-on preserves PROTOCOL.md, material_001 and the exported v1
renderer. It is a separate teaching experiment, not a v9 retry or a change to
accepted weights. Source and evidence commits are recorded in INTEGRATION_RESULT.md.

## Actual teaching, not just labels

The student still receives seven connected views of one input-binding relation:
name/function, context, analogy, explicit mapping, guided decomposition,
recomposition and reinforcement. The full worked example is now a separately
arranged demonstration. Its answer is public; the practice answer is a training
target, not part of the student's input. This prevents systematic answer copying
from the v1 solved practice text. The original v1 material is retained unchanged.
Copying the v2 demonstration solves 88/256 training cases; the best fixed answer
remapping solves 97/256. These are curriculum checks, not learned results.

The complete actual lesson is in lesson_v2_002/LESSON.md, with exact JSON inputs,
teacher-only targets and source receipts. Its demonstration is BIND0; its practice
target is BIND1. Guided ^6 is text about decomposition here, not native ^6 execution.
All seven stages supervise the same binding decision. The model is not yet trained
to answer the prose questions or give explanations; those prompts supply context
for binding supervision. Mistakes produce a training loss. This runner does not
yet generate a new personalized explanation from each mistake.

## Four candidates and exposure

Arms: cas.aligned, cas.ordinary, generic.aligned, generic.ordinary. Each gets 256
training families, the same seeded family order, batch size 32, and 7 presentations
per block. Within each model family, initial candidate bytes must match. The CAS
and generic model parameter match uses the existing META2 policy builder. Neither
accepted model nor executor is changed.

Each learner receives at least 1,024 complete fully guided blocks, including 4 for
every family, before readiness is eligible. Aligned blocks are connected cycles;
ordinary blocks are repeated ordinary presentations. Three consecutive unassisted
development checks at 90% or above permit hints instead of full demonstrations;
another three permit removal of the hint; another three support readiness. All64
development cases must be checked each time. This is readiness, not mastery.

The declared full allocation is 4,096 blocks/learner: 16 passes, 896 optimizer steps
per arm, 3,584 total updates, and 28,672 stage examples per arm. Every arm continues
to the same full allocation even if readiness comes early. A deadline can interrupt
this allocation; the report then records the actual delivered prefix as incomplete.
Equal examples and updates do not imply equal token, time or attention compute.
Per-step CUDA token and timing receipts report those differences separately.
Teacher preparation effort is shared source work; it is not assigned a fabricated
per-arm human-time measurement.

## Persistence and scope

Each attempted update gets an append-only intent and result record. Checkpoint
transactions bind weights, optimizer state, ordered stage/cycle counts, cursor,
development observations and the selected checkpoint. The runner saves at epoch
boundaries and at a graceful deadline. Restart verifies the checkpoint chain and
replays its bound event history before restoring candidate state. An uncommitted
crash tail is rejected; it is not silently erased, counted as saved, or retried.
This is tested with synthetic learners; actual CUDA restart behavior remains open.

The CUDA adapter uses the existing candidate embeddings, encoder, decoder, token
head and binding pointer. Only admitted candidate requires_grad parameters may
change. Nonzero/changed names and model-state hashes must be retained from actual
updates. Batch-level gradient delivery is not evidence that every example caused
the update, that the encoder learned the intended concept, or that mastery exists.

## Package and execution commands

Run pure build/check commands from CAS_META_2_COMPOSITION using Python 3.12 with
pytest installed. Use fresh output names. Nothing in these commands launches AWS.

```text
python -I -B tools/check_teaching_cycle.py records/teaching_cycle_001/checks_NEW
python -I -B tools/build_teaching_bundle.py --source-sha SOURCE_FREEZE_SHA --output records/teaching_cycle_001/bundle_NEW
```

The second command reads committed Git blobs, builds training.zip, checks all 17
members, extracts a fresh copy, and imports its worker modules in a fresh isolated
process. The worker bundle contains 256 training cases and 64 development cases,
the pinned reference wheel, and the required worker code. It contains no teacher
generator, construction seed, private targets, final public data or scoring code.

On the separately prepared AWS worker only, install torch 2.11.0 from the cu128
index and the bundle's exact casformer_reference 0.1.0 wheel with --no-deps. Preserve
pip's installation reports and installed distributions. The CLI requires isolated
Linux Python 3.11/3.12, torch 2.11.0+cu128, CUDA 12.8, one visible RTX PRO 4500, matching
instance/account/region observations, bundle pins and installed reference bytes.
Neither a flag nor guest metadata alone proves AWS execution; retain the parent's
independent EC2 identity and lifetime receipts.

```sh
export CAS_META2_RUN_TEACHING_CYCLE=1
python -I -B /opt/cas-teaching/bundle/cas_meta2/teaching_cycle/worker.py train \
  --bundle /opt/cas-teaching/bundle --manifest-sha256 MANIFEST_SHA256 \
  --output /opt/cas-teaching/train001 --run-id NEW_JOB_ID \
  --expected-instance-id INSTANCE_ID --worker-seconds 4800
```

Those identifiers are placeholders supplied by the new launcher, not fake provider
receipts. A graceful continuation uses the same run ID and source, a fresh output
directory, and --resume-summary plus --resume-summary-sha256. It restores the
existing campaign root. This command does not authorize or reserve a second job.

After the full training allocation and development checkpoint selection are sealed,
the parent may release public final inputs. Their export reads no private targets:

```text
python -I -B tools/score_teaching_cycle.py export-public --material-root records/teaching_cycle_001/material_001 --material-sha256 MATERIAL_RECEIPT_SHA256 --output FINAL_PUBLIC_JSON
```

Run a NEW process for prediction, passing the exact raw hashes of the training
summary and public JSON. No gold answers enter this process:

```sh
python -I -B /opt/cas-teaching/bundle/cas_meta2/teaching_cycle/worker.py predict \
  --bundle /opt/cas-teaching/bundle --manifest-sha256 MANIFEST_SHA256 \
  --output /opt/cas-teaching/predict001 --run-id NEW_JOB_ID \
  --expected-instance-id INSTANCE_ID --worker-seconds 300 \
  --campaign-summary /opt/cas-teaching/train001/campaign_summary.json \
  --campaign-summary-sha256 CAMPAIGN_SHA256 \
  --public-sets FINAL_PUBLIC_JSON --public-sets-sha256 PUBLIC_SHA256
```

The worker restores initial and development-selected checkpoints, writes 24 blind
prediction files (4 arms x 2 checkpoints x 3 splits), then seals their hashes. It
rejects incomplete allocations, unselected checkpoints, changed model state during
prediction and expired deadlines. Final scores never return to the training loop.

Use the teacher-only scorer after collecting the actual checkpoint journals and
sealed predictions. It checks packet/source/material/checkpoint identities before
opening private targets. Full CLI options are available with:

```text
python -I -B tools/score_teaching_cycle.py score --help
```

## What each result means

Training 256; development 64; final fresh 64, context 64, names 64. Fresh means new
numeric instances with familiar task forms. Context and names test unseen
combinations of familiar words. None tests unfamiliar nested program combinations.

The scorer reports per-arm before/after binding correctness with denominators,
first binding errors, and the applicable rule control on the same public cases.
Calculated selected float32 bytes are 32 bytes: eight float32 values for shape (1, 2, 4).
They are NOT observed native-call bytes. Binding accuracy, actual native argument
bytes, native A's output and complete native task correctness are separate measures.
Native A can produce an uninformative constant output even for the wrong binding.

The next appropriate phases remain explicit:

1. Actual AWS training, sealed evaluation, and independent process restart/retest.
   Run predict twice from the same selected checkpoints in separately receipted
   processes; compare predictions and identities before claiming persistence.
2. Native execution with the accepted runtime in its separate authenticated
   package. Verify the 32 selected bytes at the actual call boundary, then score A
   independently. No native runtime is added to this training worker.
3. Retention after a declared intervening learning task, using a new candidate
   copy and a development-only task set. Repeat unchanged binding probes before
   and after and compare with a no-intervening-learning control. Restart alone
   does not test forgetting. That learning task and budget are not silently added
   to the initial four-arm allocation.

## Bounded launch proposal — not a launch

Proposed new reservation ceiling: $8.00, within the existing $400 campaign cap.
The inspected canonical ledger remains revision 17, $102 reserved, $298 unreserved.
These are reservations, not invoices. The failed v9 $4 is not refunded or reused.

Proposed resource scope: one g7.2xlarge in us-west-2, one RTX PRO 4500, no T4,
at most 7,200 instance seconds; 4,800 training-worker seconds and two 300-second
prediction windows share that instance lifetime. Python setup, collection and
cleanup must fit the remaining time. Ceiling: $2.52/hour for compute, not a fresh
price quote; live pricing must be at or below this before reservation. Two hours
at that ceiling is $5.04, leaving $2.96 reserved for storage, requests, public IP and
transfer. Require a checked cost worksheet before launch; do not assume this
buffer covers an unbounded transfer or retained resource.

75 GiB encrypted gp3, delete on termination, no inbound rules, outbound HTTPS,
unique job identity, no automatic workload retry. Cloud termination schedule must
be read back before releasing the worker; a guest deadline is additional protection.
Retain source, installation reports, raw outputs, candidate checkpoints, journals
and predictions locally and rehash them before deleting their cloud copies.
Four bounded journals plus event logs can reach 2.25 GiB; use a new outer artifact
cap of 2.5 GiB, not the old v9 32MiB trainer-output cap. Time and bytes must be bounded
across the whole job, not independently reset for each process. Failed collection
must retain bounded cloud evidence with 7-day expiry rather than claim collection.

Open launch dependency: a new teaching-specific parent/guest launch profile must
connect these commands, public-data release, total deadlines and the larger artifact
bounds to the corrected transport. The old v9 resource plan/authority is intentionally
not accepted by this worker. IAM/profile, schedule, collection and cleanup fixes
have simulated tests; live provider behavior, capacity and environment remain
unproved. Do not label the package launch-ready until that integration passes.

This proposal is not a reservation and makes no AWS calls. It promises a bounded
attempt, not completion within the limit or successful learning. If teaching is
incomplete, retain actual exposure and report incomplete rather than a verdict
against the method. Preserve familiar 24/24 and prior held-out composition CAS 0/72
unchanged. No new learning, CAS advantage, language, general reasoning or completed
CNCM claim is made by this implementation.
