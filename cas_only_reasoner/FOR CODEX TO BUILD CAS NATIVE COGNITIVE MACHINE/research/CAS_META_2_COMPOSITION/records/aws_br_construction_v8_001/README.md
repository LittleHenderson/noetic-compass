# B/R diagnostic: executed on AWS, evidence checked

Status: `BR_COMPONENT_EXECUTED`; parent exit 0; `POST_RUN_CLEANUP_CONFIRMED`.

This is a completed component experiment, not a training result. A shared A → B → C → R sequence succeeded. Two independently restored stores then ran C once each, one using B's committed input and the other using R's. The recorded before-states matched. C's numerical output changed, but both outputs decoded `L2` and passed the unchanged fixed expectation. Neither choice is demonstrated to be wrong for this test.

## What happened

- Six actual accepted native ticks: four shared prelude ticks, then one C tick per branch. Each branch contains the same four earlier traces plus its own fifth trace; this is not ten separate executions.
- Each tick used 72 internal policy units: 288 in the shared prelude, 72 per branch, 432 total. Each branch started with the same fresh 8192-unit allowance and one-tick limit.
- All four saved and independently replayed before-state checks passed. These are four checks of one construction, not four independent experiments.
- Each output contains eight values, shape `[1, 2, 4]`. The maximum absolute difference was `5.323855634742358e-05`. Both decoded `L2`, `DECOMPOSITION_SIGNAL`, `^6`.
- Worker wall time was `42.52156505799999` seconds. AWS identity recorded Python 3.12.3, torch 2.11.0+cu128, CUDA 12.8, and NVIDIA RTX PRO 4500 Blackwell Server Edition on `g7.2xlarge`. No T4 or local neural execution was used.
- No weights were trained. The accepted model, executor, fixed expectation and protected source identities were preserved. Source and reservation postchecks passed.

The intervention changes the complete selected reference: payload, decoded content, producer, provenance and age. It does not isolate a tensor-only causal effect. B was published at tick 2 (age 3 at comparison); R at tick 4 (age 1).

The worker constructs a standalone component call, with no outer executor created. Its recorded claim that no caller is active is supported by this construction path, not proved merely by equal database hashes or equal dictionaries. This experiment does not demonstrate restoring an active caller stack or its remaining budget.

## Bound evidence

Job: `cas-meta2-20260906150012-7c9f6d00`  
AWS account/region: `807562639912` / `us-west-2`  
Instance: `i-05ba34f47185eb934`

| Identity | SHA / SHA-256 |
| --- | --- |
| Worker source commit | `d047540a635ecccdd2cfd4d96ee3b43da59f7ce7` |
| Parent source commit | `433089fcad368de96e27f93a8f77c375500f677a` |
| Launch registration commit | `f6429729c396152479168296ed364fde8926d28e` |
| Accepted baseline commit | `0917267b1354e5d036263eaa6ba9a7197eafb776` |
| Source ZIP | `1b13fbeb96465e2122b1709b87c99cdd06860f78a2bc4bbbfa4874e96ef7658a` |
| Source root manifest | `7d5fdf331e74638b5cd1ecf9fca2c4a5ae3610aa562014decc5c03e4ca29944f` |
| Downloaded result ZIP | `3cd1806649e0cd357d37391b805c64f928f0b5615aea524f8d84332f77aa735a` |
| Read-only AWS cleanup observation | `f9e9593d63da6efa319a372a0e494abd3a4ed2891910421915626effeaad3921` |

The research package root for the recorded commands is:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION
```

Paths below are relative to that root:

- `records/aws_br_construction_v8_001/FINAL_RECEIPT.json`: final binding of result, commands, raw files, cleanup and budget evidence.
- `records/aws_br_construction_v8_001/execution_001/cloud_artifacts.zip`: complete 1,502,016-byte result archive, 50 members (49 indexed files and the collection receipt), no omitted files. Includes native database bytes, per-arm results, before-state records, construction receipt, environment identity and raw worker/install logs. The local replay hashes database bytes but never opens a database.
- `records/aws_br_construction_v8_001/execution_001/launch_receipt.json`: final provider lifecycle and cleanup receipt.
- `records/aws_br_construction_v8_001/execution_001/post_run_provider_read.json`: separate read-only provider confirmation after parent exit.
- `records/aws_br_construction_v8_001/registration_001/`: exact request, standing authority registration, capture script, process identities and raw parent stdout/stderr. The completion receipt records the full actual parent command and exit 0. The capture has a one-run marker: do not rerun it or reuse this job ID.
- `records/aws_br_construction_v8_001/analysis_001/`: offline evidence replay, including all 49 indexed file checks and all 630 source archive member checks. Its saved launch receipt was observed before cleanup finished; it is historical evidence and is not the final cleanup receipt.
- `records/aws_br_construction_v8_001/independent_review_001/REVIEW.md`: separate JSON/text review, including exact shared trace histories, model/source identities and numerical contrast. It did not re-execute native code.
- `records/child_call_v8_construction_001/source_001/`: packaged worker source, published wheels, dependency lock and identities. All 316 protected baseline files were checked.
- `records/child_call_v8_construction_001/checks_004/`: 327 passing local pure/simulated tests, exit 0.
- `records/child_call_v8_construction_001/br_clean/checks_002/`: 203 passing tests from a fresh extraction of the exact source ZIP; all 630 files checked before and after. No neural execution on the laptop.

Offline replay command (from that package root, choose a fresh output directory):

```powershell
& 'C:/Python314/python.exe' -B records/aws_br_construction_v8_001/analyze_result.py --output records/aws_br_construction_v8_001/analysis_002
```

This checks existing recorded evidence. It does not launch AWS, open native databases, load tensors or retrain a model. The separately committed clean-package checker and its exact reproduction command are documented in `records/child_call_v8_construction_001/README.md`.

## Cleanup and budget

The parent confirmed termination at `2026-09-06T15:11:21.277375+00:00`, zero job-tagged volumes, and removal of the job's security group, two roles, instance profile and shutdown schedule. A later independent read confirmed those states. Inputs were deleted only after the result archive was downloaded and checked. Three result objects remain under a seven-day lifecycle rule; the bucket itself is retained. This is not a claim that every AWS object was deleted.

The interval from launch attempt (`2026-09-06T15:02:36.524095+00:00`) to termination confirmation was 524.753280 seconds. At the verified hourly rate of $2.52, that interval gives an EC2 compute estimate of **$0.367327296**, not an invoice or a total including storage, requests or network charges.

Canonical campaign ledger revision 13 retains this job's **$4 reservation**. The $400 campaign has **$86 reserved and $314 unreserved**. Reservations are not actual spending, and unreserved capacity is not a target to spend. No automatic refund was made. The committed standing-authority record identifies existing user authorization; it is not a newly invented human approval.

## What remains unproved

No task-conditioned input-selection skill, full-program continuation, task correctness, new learning, generalization or CAS-specific advantage is established here. Both alternatives pass the same fixed `L2` check. Before training on this construction, the curriculum must specify a public task condition and use the unchanged whole-task verifier to distinguish a correct choice from a wrong one. This result does not authorize changing the accepted verifier to manufacture that distinction.

Earlier held-out CAS composition **0/72**, familiar-program **24/24**, and the completed saved-prefix diagnostic remain separate evidence. Accepted core, META-0 and META-1 audits are not reopened.
