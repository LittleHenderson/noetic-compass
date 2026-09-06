# Dedicated prefix-diagnostic launch connection

This is the current follow-up to the frozen saved-model diagnostic. It does not
replace that worker or its development bundle. No new training, native execution,
GPU instance, budget reservation, or model score has been produced by this work.

The requested launch is only the saved-checkpoint prefix diagnostic: 24 training
probes and 96 validation tasks, four checkpoints, 480 task/checkpoint rows over
120 distinct tasks. Each checkpoint has 2,272 reference decision opportunities:
360 forced RUN-input choices and 1,912 with multiple grammatical choices. Correct
prefix and self-generated prefix results remain separate by checkpoint, cohort,
depth and decision role. Missing or changed opportunities remain in the counts.

## What the connection does

`aws/launch_prefix_diagnostic_v8.py` is the dedicated parent. Its default path
builds an unpaid, source-bound approval request. The separate `--execute` path
requires a later explicit owner approval, verifies its exact request identity,
checks current resources/prices and the canonical ledger, then reserves at most
$4 before creating resources. It does not invoke the old V7 experiment.

`aws/prefix_remote_v8.py` stages the two existing archives, installs the pinned
environment and wheels, checks the AWS/CUDA identity, and invokes only
`cas_meta2.diagnostic_v8.gpu`. The diagnostic worker remains unchanged at
`13f424981d7434b1a92815d1ad5759d543bbd3be`.

One `g7.2xlarge` with one RTX PRO 4500 is allowed. The declared instance lifetime
is at most 3,600 seconds including setup and collection; the worker is at most
1,800 seconds. An independent cloud termination schedule is set earlier, with a
guest shutdown fallback. Every guest stage uses the earlier cutoff. A complete
worker window plus 240 seconds for collection must remain; it is not silently
shortened. There are no automatic job retries or deadline extensions.

Stage receipts retain command, time, exit code and stdout/stderr even when the
worker fails before creating its own result directory. Output-size and transfer
limits are explicit. A failed or shortened collection is marked partial, never
reported as completed measurement. Cleanup checks exact job ownership. These
controls are implemented and tested with fake providers/processes; their first
real AWS execution is still untested.

## Current cost and authorization boundary

The recorded read-only AWS checks found the current rate of $2.52/hour, unused
quota for one requested instance, an available matching AMI and subnet, and no
active tagged CAS job. An offered instance type and quota are not a promise of
allocation. Read permissions do not prove create permissions or live CUDA.

With the declared volume, IPv4, storage, transfer, request and time limits, known
pre-tax resources are estimated at $2.569243. Compute plus the full $1 ancillary
allowance is $3.52, below the proposed $4 reservation. This is not an invoice or
an AWS-enforced account spending cap. Prices and resource state must be checked
again during an authorized launch. Taxes and abnormal provider delays remain
explicit limits on the estimate.

No approval is inferred from the $400 campaign cap or the request to finish this
connection. The later approval record must bind the exact launch request and the
owner's actual message. No real launch approval artifact has been created here.
Synthetic approval fixtures exist only inside tests and do not authorize this job.

## Clean-source reproduction

The frozen source ZIP is
`c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1`.
The separate development ZIP is
`1874508d0baad7d6620001505c39f184b3cb091c59de4e96197f309beee0a042`.
Its four checkpoints and exact cohort ordering are bound by development manifest
`b4d7970ca59c07342942584e4752ad8c129c3125e25ecc241e3d76c9ddd1c629`.

`clean_package_003` reproduced **313 tests and 5 subtests, zero skips**, from the
unchanged ZIP source in a new directory. This is a pure source-package test, not
a wheel installation, model run or fully isolated operating environment. Its
receipt is
`453d255e66376b619f54ab1f0bcba42af169821a723bd15844ed7bfbbdce22a6`.

The complete test inputs are the source ZIP, the pinned original development
extraction and companion receipt, plus two previously opened historical packets
used by the frozen grammar regression tests. Those two extra test dependencies
are now explicitly pinned:

- `records/aws_full_002/cloud_artifacts.zip`: 62,269,330 bytes,
  `e22412583114e50cbf9e60d8b22864bfb4ca76e6ccecedee7a0f72976ec37ae0`.
- `records/aws_learning_v2_001/cloud_artifacts.zip`: 59,648,802 bytes,
  `0d1b13aa711685cc488bdfdb981d8682d3d1b02b8e67530a3742add44dd13e93`.

These historical packets are local regression-test inputs only. They are not
added to the model's diagnostic panel or uploaded for its GPU run. No new final
task is opened. This does not reopen the resolved META-3 line-ending finding.

Earlier attempts remain: `clean_package_001` failed before child creation because
Windows rejected a long working directory; `clean_package_002` had 311 passed,
2 skipped and 5 subtests because the two historical regression packets had not
been staged. Neither is represented as the complete 313-test reproduction.
The second receipt's old count parser records null; its raw stdout records the
actual counts. The final runner handles skips explicitly and requires zero.

The final receipt's `external_data_unchanged` means the extraction receipt and
the original/staged historical ZIPs remained unchanged. It is not an after-test
hash of every external development file; the frozen bundle checks their pinned
bytes while constructing test fixtures. Source bytes are checked before/after.

## Separate child-call preparation

The pure scaffold compiler and enumeration now run. One construction scaffold
with three observations yields 180 choice tuples, not 180 learning tasks. Of
these, 90 pass structural admission, 72 fail topology and 18 fail the accepted-
Effect return requirement. Six B/R pairs change only the child input. Full
catalogs and input scopes stay visible; no private answer prunes the choices.

This has not established native usability, meaningful numerical differences,
or public task information that makes the correct B/R choice vary. The equal-
state comparison protocol preserves the accepted restoration and repair rules.
Its required CUDA restoration adapter and task-conditioned curriculum remain
unbuilt/unexecuted. It is not part of this $4 diagnostic request. Later training
needs its own decision and budget; it will not start automatically.

## Runnable checks

Run from this exact directory:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION`

Use new output directories on rerun; the commands refuse existing destinations.

```powershell
python -B tools/verify_prefix_clean_package_v8.py --output records/child_call_v8_diagnostic_001/NEW_CLEAN_CHECK
python -B tools/check_child_call_preparation_v8.py records/child_call_v8_preparation_002/NEW_CHECK
python -B tools/check_prefix_launch_connection_v8.py records/child_call_v8_launch_connection_001/NEW_CHECK
python -B -m cas_meta2.child_scaffold_v8 --output records/child_call_v8_preparation_002/NEW_ENUMERATION
python -B -m aws.launch_prefix_diagnostic_v8 --help
```

Exact launch/source identities and the one pending approval request are recorded
separately in `APPROVAL_REQUEST.md`, `launch_request.json` and `FINAL_RECEIPT.json`.
No automatic merge, push, release promotion or claim of learned skill follows.
