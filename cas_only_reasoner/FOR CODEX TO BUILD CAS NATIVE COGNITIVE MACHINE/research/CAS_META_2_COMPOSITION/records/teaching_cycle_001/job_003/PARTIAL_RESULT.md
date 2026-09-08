# Teaching job 003: saved partial training, not a final learning result

The worker stopped normally at its bounded deadline, saved its progress and
exited 0. The GPU instance was independently observed terminated. The full
training allocation is unfinished, so no final prediction questions were
released and no final test score is available.

Job: `cas-meta2-teaching-20260908052915-8b5df59c`.
Instance: `i-0272a6d80f3b5ad75`, account `807562639912`, region `us-west-2`.
Frozen worker commit: `c8c0e558cf30cd5fe06c2bf3d475697e97698a3e`.
Transport commit: `f0befae3956086eaf8d7115919f2d05349ec4b97`.
Inspection tools at commit: `fc1171d57209a64e89bc985eb2ac1c5e2ebbd7b5`.

## Time and shutdown

The recorded worker wall time is **4773.4186613 seconds** (79 minutes,
33.419 seconds). Its `--worker-seconds 4770` soft deadline is checked between
updates; saving and returning can exceed that value. It remained below the
4800-second outer training timeout. The latest CAS-aligned checkpoint records
`graceful_deadline`. The process exit receipt reports exit 0, no failure and
zero automatic retries; the retained stderr log is empty.

The original supervisor finished with `TEACHING_CYCLE_BLOCKED`, because its
cleanup observation timed out before it confirmed termination. That immutable
receipt is retained, not rewritten as a success. A separate read-only EC2 call
at `2026-09-08T07:00:07.089572+00:00` observed the instance **terminated**, with
reason `Client.InstanceInitiatedShutdown`, request ID
`a52d3e33-74fe-4835-ad88-04952766a82e`. This compact direct-call output is in the
task transcript, not a claimed retained full raw API response.

Remaining job-resource cleanup is being checked separately. Empty instance
block-device mappings alone are not proof of volume deletion. The original
cleanup kept the schedule and IAM resources while compute state was unknown.
The dedicated bucket's four result objects remain under its seven-day lifecycle
policy; that policy is not an exact deletion-time guarantee.

## Actual work saved

All four candidates completed seven whole passes through the training set.
CAS aligned also completed 19 updates of the eighth pass. The frozen allocation
is 16 passes per candidate, 896 updates each, 3584 updates total.

| Candidate | Updates / 896 | Complete aligned cycles | Complete ordinary blocks | Stage examples | Remaining updates |
|---|---:|---:|---:|---:|---:|
| CAS aligned | 411 | 1856 | 0 | 13152 | 485 |
| CAS ordinary | 392 | 0 | 1792 | 12544 | 504 |
| Generic aligned | 392 | 1792 | 0 | 12544 | 504 |
| Generic ordinary | 392 | 0 | 1792 | 12544 | 504 |

Total: **1587 / 3584 updates**, **50784 stage examples**, **1997 updates
remaining**. Ordinary blocks are not counted as aligned teaching cycles.
All candidates remained under full guidance. Parameter changes and update
counts do not establish successful learning.

The fixed material contains 256 training families, 64 development tasks, and
64 tasks in each of three final test splits (`test_fresh`, `test_context`,
`test_names`). This experiment concerns selecting the matching input, not
unfamiliar nested-program composition or complete native task execution.

## Development results: preserve the CAS negative

These are worker-recorded development results from the hash-bound archive.
They are not independently rerun model predictions and not final held-out
scores. There is **no untrained development measurement** in this job. The
first three passes record zero attempted development tasks, not zero correct.

| Candidate | Pass 4 | Pass 5 | Pass 6 | Pass 7 | Best development |
|---|---:|---:|---:|---:|---:|
| CAS aligned | 21/64 | 21/64 | 21/64 | 21/64 | 21/64, pass 4 |
| CAS ordinary | 21/64 | 20/64 | 21/64 | 21/64 | 21/64, pass 4 |
| Generic aligned | 21/64 | 24/64 | 49/64 | 42/64 | 49/64, pass 6 |
| Generic ordinary | 21/64 | 27/64 | 32/64 | 46/64 | 46/64, pass 7 |

At these equal completed passes, CAS is behind the matched generic models.
CAS aligned selected slot 1 for every development task at pass 4, and slot 2
for every task at passes 5 and 6; at pass 7 it selected slot 2 on 55/64 tasks.
CAS ordinary selected slot 2 on all 64 tasks at pass 7. This is evidence of
mostly single-slot selection, not useful task-dependent input binding yet.
It does not identify the causal neural defect or prove that further training
cannot help. The extra 19 CAS-aligned updates have no later development score.

No rule or untrained final comparison was executed by this partial run. Do not
substitute old selection or composition results for missing results here.
The earlier familiar-program 24/24 and held-out CAS composition 0/72 remain
separate evidence, unchanged by this experiment.

## Timing and continuation limits

| Candidate | Recorded update interval total | Mean per update |
|---|---:|---:|
| CAS aligned | 1201.3089621369988 s | 2.9229 s |
| CAS ordinary | 1139.9394916009974 s | 2.9080 s |
| Generic aligned | 1107.0523783749968 s | 2.8241 s |
| Generic ordinary | 1108.9527819860043 s | 2.8290 s |

Update intervals total 4557.2536141 seconds, 95.47% of worker wall time;
216.1650472 seconds is outside them. These synchronized intervals include
state snapshots, GPU-to-host byte copies, hashes, parameter checks, encoding,
forward/backward computation, updates and receipt construction. They are not
pure GPU-kernel time. The records do not show which internal cost dominates.

Extrapolating each candidate's mean suggests about 5732 seconds for remaining
updates, or roughly 6004 seconds with proportional outside-step overhead.
This is an estimate, not a completion promise. Restore/setup work is unmeasured,
and later guidance changes could change runtime. Another 4770-second training
slice would probably not finish. The frozen worker itself caps a call at 6000
seconds; the current cloud transport caps training at 4800 seconds.

A continuation must retain the existing allocation, source, model/optimizer
state, original logical run ID, and original campaign path
`/opt/cas-teaching/job/train/campaign`. The current AWS transport does not yet
ship prior journals or distinguish a new cloud job from this logical run ID.
No continuation, new reservation or new GPU launch is performed by this report.

## Evidence and local checks

The original result ZIP is retained: 69240408 bytes, SHA256
`73a1e22bdf011380527d78fd72f2a343bfffa1d302eedffc57b0f5417aa361e9`.

- Parent `launch/result.json`: SHA256
  `c12347f65d38dc883221b9f9ddb48099574c851acc858d6d6444a0eaa2295b76`.
- Completion marker `launch/partial_collected/complete.json`: SHA256
  `72e855be29eef920df8cf4089b6f81347a9b709a952e7f6d9aff44208e7d97a7`.
- Extracted `train/campaign_summary.json`: SHA256
  `26b23bb5f23ca875375797db155e8520b947bf0b4eada71e596a9ec7493e195f`.
- `evaluation_001/evaluation.json`: SHA256
  `0574d29371108ef8ef0a08c8af79216e638deabeffd3b6f5a323e6c57d953f18`.
  Status `PARTIAL_EXPOSURE_ONLY`; the evaluator did not open private targets.

The collected evaluator verified the pins and extracted the archive safely.
The separate read-only continuation inspection exited 0 and returned
`STRUCTURALLY_RESUMABLE_GPU_RESTORE_UNTESTED`. All four candidates passed the
unchanged pure resume checks. Their checkpoint transaction chains and event
hashes agree; there are no uncommitted tails or incomplete checkpoint staging
directories. Extracted bytes matched the original ZIP before and after the
inspection. It did not load model tensors or run CUDA. This is not proof that
restoring a real model and optimizer on another GPU succeeds.

Inspection receipt `continuation_inspection_001.json`: SHA256
`a47ced1ca072041306f8e4a47f2efb03ec97d5690659b14ab19cd0e19141ef6d`.

Latest recorded checkpoint file hashes (not model-state digests):

| Candidate | Transaction | File SHA256 |
|---|---:|---|
| CAS aligned | 9 | `72def8dec60ac22c4eac037ab41333a486649a5bf3a50e1c3ce8ff8480a1c13c` |
| CAS ordinary | 8 | `96bf14997494ff7e2a35ac9a40bb77d1f4403e7e0c7887a861d0cd6b2ff87da3` |
| Generic aligned | 8 | `8e06d1853eb5587c3f067aff6aaaed49ea39154f08d6357321c4a25ddcbe30a3` |
| Generic ordinary | 8 | `7c08443722ba010c9e2efcd4c26a780bfb44fa1c900473de63c75cfe8815990f` |

The accepted weights/executor were not edited. Native execution, retention
after intervening learning, final task correctness, successful GPU restart,
CAS-specific advantage and completion of the full CAS/CNCM goal remain unproved.

Budget ledger remains revision 19: $118 reserved, $282 unreserved, inclusive
$400 cap. This job's reservation stays $8; these are not actual AWS invoices
and no reservation is automatically refunded. At the retained $2.52/hour quote,
launch-to-observed-termination gives a conservative compute-only estimate of
about $3.72, excluding storage, networking and other charges. The actual bill
is not available in this record.
