# Approval requested: one $4 saved-model diagnostic

The AWS connection is implemented and committed. This request asks permission
for one diagnostic run. It does not report a completed GPU measurement.

Reply: **Approve the $4 diagnostic.**

No launch or reservation will occur before that explicit approval is recorded.

## Exact job and limits

- Job: `cas-meta2-20260906133828-cff56f29`
- Request SHA-256: `745b45d437e0b17adacc71f6f945a47f8cf6767c1209f637cbadc9a2380a8cbf`
- Dedicated launch source commit: `39d0ed9b65683504d9335963bf57c7ac6ef1d78f`
- Frozen diagnostic worker commit: `13f424981d7434b1a92815d1ad5759d543bbd3be`
- Account: `807562639912`; region: `us-west-2`; subnet: `subnet-0eb3ca4bf5ca98f24`.
- One `g7.2xlarge`, one NVIDIA RTX PRO 4500 GPU. No T4.
- Requested lifetime: at most 3,600 seconds, including setup and collection.
  Worker: at most 1,800 seconds. No automatic retries or deadline extensions.
- Independent cloud termination at 3,480 seconds; guest shutdown fallback at
  3,400 seconds. The earlier cutoff controls each guest stage.
- No training, native-runtime execution, B/R construction check, or later
  curriculum execution. No neural work on the laptop.
- The old V7 experiment is not invoked. Only its byte-pinned ownership and
  cleanup helpers are reused.

The parent validates the source, input archives, job identity and canonical
budget reservation. It confirms the independent shutdown schedule before it
gives the worker permission. Failed setup and worker stages retain output and
exit receipts; incomplete results stay marked incomplete. Cleanup checks job
ownership before acting.

## What it measures

The panel contains **120 distinct tasks**, repeated across four saved checkpoints:
24 training probes (8 at each depth 1/2/3) and 96 validation tasks (32 per depth).
These are previously used development tasks, not a new held-out generalization
test. This produces 480 task/checkpoint rows.

Each checkpoint has 2,272 reference decision opportunities. Of these, 360 are
grammar-forced RUN-input choices and 1,912 have multiple grammatical choices.
Multiple legal choices do not by themselves prove meaningful output differences.

The run compares choices after a supplied correct beginning with choices after
the model generates its own beginning. It keeps those results separate by
checkpoint, task partition, depth and decision role. It reports child selection,
CALL-input binding, observation binding, other RUN inputs, and returns, with
accuracy and coverage together. Missing, changed or ambiguous contexts remain
visible. Raw and grammar-restricted choices stay separate. Assisted accuracy is
not autonomous task success.

During execution, the worker must check saved-model loading, generation agreement
with recorded development output, numerical settings, output coverage and
unchanged weights. Failure of a required check is a failure result, not permission
to substitute another checkpoint, train, or silently extend the job.

## Bound source and inputs

The audit directory is:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/child_call_v8_launch_connection_001`

The exact runnable request is `launch_request.json`. `FINAL_RECEIPT.json` lists
absolute input addresses, source identities, test receipts and evidence hashes.

| Input | SHA-256 |
|---|---|
| Frozen source ZIP | `c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1` |
| Development ZIP | `1874508d0baad7d6620001505c39f184b3cb091c59de4e96197f309beee0a042` |
| Development manifest | `b4d7970ca59c07342942584e4752ad8c129c3125e25ecc241e3d76c9ddd1c629` |
| Prefix source manifest | `10f3283e5dcb3045dac2131e021d3ca383c35ae8b34c9e439e7fc82ff58cdd9c` |
| CAS initial checkpoint | `ad8c80bf3d3ed7111e118957066ac3f0ec0509681fa2aa00e44d1592403b43fd` |
| CAS selected checkpoint, epoch 200 | `bf709539d8a462fe73909553659ad046305e75428a15d80e83124bc28ee84b46` |
| Generic initial checkpoint | `20669d0470a583ab172bbb06451c0b6bcbbf190ea10b3e725e7a73c5c046b051` |
| Generic selected checkpoint, epoch 180 | `53e2acdd4635d843210a7aa0a5b194e395f57c0b7f71ca59b1a64dbeae4ca532` |

## Cost and current evidence

Read-only AWS checks on 2026-09-06 found the requested instance at **$2.52/hour**.
They found enough unused quota and an offered instance type in the chosen zone.
The exact API requests, responses and price records are in `readiness_001`.
The current canonical ledger is revision 11: $400 campaign cap, $78 reserved,
**$322 unreserved**. No new reservation has been made.

Known pre-tax resource cost under the declared limits is approximately $2.57.
Compute plus the full $1 allowance for setup-related storage, network and
collection costs is **$3.52**. The proposed reservation is **$4.00**.
If approved and successfully reserved, unreserved campaign capacity becomes $318.
The parent rechecks prices, resources and ledger state before spending.

This is a bounded job plan, not an AWS-enforced account spending cap. Taxes,
support allocation and abnormal provider shutdown delays are not proven by the
price query. Volume, transfer, request and retention limits are in the exact
request. GPU allocation and create permissions remain launch-time checks.

Local preparation evidence:

- **80 launch-connection tests passed**, including failed-preflight receipts,
  reservation/snapshot failure handling, approval refusals, shutdown-before-worker
  permission, bounded collection and parent-to-worker identity checks.
- **79 preparation tests passed**, covering archive input checks and the separate
  child-call scaffold.
- The unchanged frozen ZIP reproduced **313 tests and 5 subtests, zero skips**,
  with all declared development and historical regression inputs.
  This was a pure source test, not a wheel installation or CUDA run.

These tests used fake provider/process boundaries where required. They do not
prove the first real installation, CUDA inference or cloud cleanup will succeed.
Earlier incomplete clean-package attempts remain in the evidence; they are not
represented as successful complete reproduction.

## Remaining gate and separate work

The remaining required decision is your explicit approval of this $4 job.
No provider blocker was observed by the recorded read-only checks, but capacity,
create permissions, installation and CUDA execution have not been exercised.

The B/R candidate-pair preparation is separate. Its pure scaffold enumerates
180 choice tuples and six matched B/R pairs. It does not yet establish usable
native alternatives or task-dependent numerical differences. Its protocol starts
the two comparisons from copies of the same valid saved state. That later check
and any training require their own declared scope and budget; neither starts
automatically after this diagnostic.
