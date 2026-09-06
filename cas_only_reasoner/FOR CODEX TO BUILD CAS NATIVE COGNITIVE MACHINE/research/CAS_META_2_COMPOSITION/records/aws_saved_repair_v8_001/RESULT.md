# Saved repair: negative result and revised diagnosis

The AWS attempt failed the frozen authored-label contract. It did not repair R,
advance the saved state, qualify the curriculum, or demonstrate new learning.
The negative result is complete, not a missing-packet inference.

## Actual result

- Job: `cas-meta2-20260906165606-cbc41523`.
- Source freeze: `e85d224842c50b2be202c8a15181df0526fa26cc`.
- Registration commit: `8af76a090e9f0659a0c84e26c731eb54c3aa285d`.
- Result archive: `execution_001/lifecycle/cloud_artifacts.zip`, 623,035 bytes,
  SHA256 `0189b4def99e9416fa432b0c678dab1f99f44a3a9d202de721f2ec0151dcf5f5`.
- Parent exit 1; final status `AWS_SAVED_NATIVE_REPAIR_FAILED`.
- C at tick 7: one attempt, zero returned calls, zero committed ticks, zero
  accepted ticks. Its observed proposal decoded to L0; the frozen target was L2.
- Exact exception: `RuntimeContractError: an open repair subgoal must verify ACCEPT before tick advancement`.
- R at tick 8 was not attempted. The original R repair remains open and suspended.
- 72 attempted policy units, zero committed policy units. These are declared
  native compute allowances, not measured FLOPs, dollars, or a completed call.
- 27 GPU module pre-hook entries, not 27 independent model calls.
- Original six traces, original database bytes, weights, decoder and source
  identities remained unchanged. The copied database also retained its original
  hash because the failed call committed nothing.
- All 39 packet files were verified, with complete coverage and no missing
  worker files. The separate local analyzer passed 23 evidence-consistency
  checks. Those checks establish the negative record, not repair success.

The read-only proposal hook saved 32 bytes even though the runtime refused the
call before commit. Raw payload SHA256:
`d3c0220d35f17ebfac3b788c09846a32f38bec636f0712caf14acb0f732ab4c9`.
Metadata-bound artifact SHA256:
`ac9278c10fb4716a58c0476e87790fcfd846742a140d7e1be6d55d0191d74981`.
Neither is a published Effect or commit receipt.

## What was missing

The absent repair continuation was real, but adding it was not sufficient.
This attempt reached the actual repair child, which then failed its fixed target.

There is also a more basic experimental boundary:

1. `cas_meta2/native.py:82` creates the original fixture and freezes its weights.
   `cas_meta/fixture.py:45` selects seed 7. `cas_cjt/runtime.py:346` constructs a
   seeded NeuralCJTNetwork and immediately checkpoints it, without training.
   This particular native network is not the separately trained program selector.
   Updating persistent recurrent Bias is not the same as training model weights.
2. `cas_meta2/native.py:26` assigns fixed per-node labels, including C=L2 and R=L1.
   `open_repair()` does not derive L2 from the failed problem. These are authored
   fixture expectations, not established universal meanings of those CJTs.
   The accepted reference itself deliberately authors different C expectations
   to exercise rejection and resumption. We must not train constant L2 output
   and describe that as learning to repair arbitrary problems.
3. `cas_cjt/control.py:178` materializes the referenced dense input; its later
   sections load recurrent Bias and numeric controls. `runtime.py:804` forwards
   those values. Goal text, repair reasons and RPM_SUBGOAL metadata are recorded
   and checked but are not encoded as a neural instruction in this path.

All three inspected source members match the actual registered source ZIP:

| Source member under research/ | SHA256 |
| --- | --- |
| CAS_META_2_COMPOSITION/cas_meta2/native.py | 16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512 |
| CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/fixture.py | 0038db2ed122e7d1ccb312771e0ea14388ee8564d3ffaa9a9f6c7316c6eb1735 |
| CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py | 5eda27339d0d216d5359116617c6dc8c9f99c376d6cfa6be386845b59ec00187 |

C3 used B2's accepted output with C Bias version 0. C5 used R4's accepted
output with C Bias version 1. C7 used R6's rejected proposal with C Bias version
2. Thus both dense input and recurrent state changed. Their separate numerical
contributions remain unmeasured. The receipt does not establish a need for
pulsation, more GPU capacity, a new Noetic meaning, or a Bias reset.

## Next work

Keep the accepted executor, verifier, weights, targets and historical evidence
unchanged. Do not repeat this paid repair attempt or widen its claims.

Prepare an explicit candidate learning contract with separate scores for:

- Choosing C versus C-to-R and binding the requested B/R source from the public
  task. The existing parser/compiler provides independent selection targets.
- Producing a task-correct child result. Before training native candidates,
  define input-dependent outcome targets independently of the seeded network,
  its argmax, and the node name. A constant-symbol predictor must not satisfy
  the intended learning claim.
- Executing repair and returning through the complete caller with its remaining
  budget intact. A native database copy alone does not establish caller return.

The present four-combination native qualification remains failed; R_CR is not
removed. A selector-only learning improvement must remain a selector result,
not complete-task success. Future candidate training and evaluation belong to
a separate source freeze and bounded AWS reservation, with validation-only
checkpoint selection and held-out outcome checking. No new paid job is started
by this report. Earlier CAS 0/72 held-out and 24/24 familiar-program results stay
separate and unchanged.

## Environment, cost and cleanup

Actual worker: AWS g7.2xlarge, NVIDIA RTX PRO 4500 Blackwell Server Edition,
Python 3.12.3, torch 2.11.0+cu128, CUDA 12.8. Worker wall time was 19.913827125
seconds; the failed C call took 0.123175177 seconds. Startup, installation and
shutdown are additional time. No local neural or SQLite execution occurred.

The separate provider check made 13 read-only getter calls and passed all 15
checks. The exact instance is terminated; its volumes, security group, worker
and timer roles, instance profile and schedule are absent. Uploaded input
objects were deleted after the result was downloaded and hash-verified. Their
local source package remains available. Three result objects remain with a
seven-day expiry rule. The metadata check did not re-download those objects.

The job reserved $4, not an invoice. Campaign ledger revision 16 records $98
reserved and $302 unreserved under the $400 cap. No automatic refund was made.
At the recorded $2.52/hour rate, launch to observed termination was about 552
seconds, roughly $0.39 of EC2 time. This estimate excludes ancillary charges
and is not the provider's final bill.

## Audit entry points

- `analysis_001/analysis.json` and `analysis_001/command_receipt.json`.
- `provider_check_001/receipt.json`.
- `registration_001/parent_process_completion.json` and raw parent outputs.
- `execution_001/launch_receipt.json` and its complete lifecycle records.
- `final_validation_receipt.json` binds these files and the campaign ledger.

Pure local result examination, using a fresh output directory:
`python -B records/aws_saved_repair_v8_001/analyze_result.py --output records/aws_saved_repair_v8_001/analysis_002`.
This reads JSON/ZIP bytes only, and blocks neural imports, SQLite and network.
It does not rerun the AWS job. Do not rerun the paid capture entrypoint.
