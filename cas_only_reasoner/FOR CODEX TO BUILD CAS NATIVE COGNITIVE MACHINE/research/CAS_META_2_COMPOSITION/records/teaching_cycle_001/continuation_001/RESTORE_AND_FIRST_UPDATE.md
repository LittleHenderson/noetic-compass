# AWS continuation: restore and first new update

Recorded 2026-09-08. This is a completed restore milestone and one new-update observation, not the finished teaching result. It supplements the source-frozen pre-launch report without rewriting it.

## Bound run

- New cloud job: `cas-meta2-teaching-20260908080138-5518e287`.
- Original logical run: `cas-meta2-teaching-20260908052915-8b5df59c`.
- EC2 instance: `i-0c89cf580dd58a803`, `g7.2xlarge`, account `807562639912`, `us-west-2`.
- Actual GPU reported by the restore process and first new update: `NVIDIA RTX PRO 4500 Blackwell Server Edition`.
- Continuation source freeze: `a4b1af8519bd8def6e8cbb16f6d14ef72d99fa6b`.
- Frozen neural worker: `c8c0e558cf30cd5fe06c2bf3d475697e97698a3e`; original source ZIP SHA-256 `494f44d467a85e2edd54b568cf4b0822db6e25355003a8a6ae8c7d4c09dd8cec`.
- Preparation receipt SHA-256: `f47e40ae3f72aca8b77824cce6dc2498e66261c7274a440a478573c2e3d656c3`.

The original job003 GPU was also an RTX PRO 4500 Blackwell. Reusing that model is not a newly measured hardware speedup. Neither the old timings nor this first update identifies which internal cost dominates.

## Actual restoration passed

The separate CUDA restore process exited 0 in `155.05006252200002` seconds, within its 180-second cap. Its status is `RESTORED_NO_TRAINING`, with `actual_restore = FOUR_ARMS_RESTORED`.

| Candidate | Restored optimizer updates | CUDA optimizer tensors checked |
|---|---:|---:|
| CAS aligned | 411 | 261 |
| CAS ordinary | 392 | 261 |
| Generic aligned | 392 | 165 |
| Generic ordinary | 392 | 165 |

For every candidate, actual restored model identity, optimizer values, training cursor, event count and pending-development state matched the saved package. Optimizer moment-buffer placement was checked. The prior 3,278 payload files, 97,150,484 bytes, stayed unchanged; their tree identity is `348466cba08c04e65f7f27461b46e849c4fc6f183eb9346350a08afa816fee91`.

The restore probe performed zero optimizer updates and no predictions. This is actual AWS/CUDA restoration evidence admitted by the parent, not another local fake test. It does not establish bitwise-identical future random state or retained task correctness after new learning.

## New training update observed after release

The parent admitted the restore receipt and uploaded the training release. It subsequently recorded `WORKER_REPORTED_FIRST_CUDA_UPDATE` at Unix time `1788855187.9728043` (2026-09-08 08:13:07.972804 UTC).

The observed arm was CAS aligned: **411 -> 412 cumulative optimizer updates**. The new event's before-model digest equals the restored CAS-aligned model digest, `7443a312c7d50a6830cb5c7d16c03851998559eba06f66d71868145748971c47`. Its after-model digest is `7c2e38d2ef57f31528607803ab24bf0456da05557ee118dc44ffb1a3f7d7d75b`.

That event records 32 examples, CUDA execution, loss `1.0477039813995361` and step-wall time `3.515044295999985` seconds. The measured interval includes snapshots, encoding, neural forward/backward, the optimizer update and receipt construction; it is not pure GPU-kernel time. One event is not a learning curve, a current total across arms, an independent checkpoint rerun or an accuracy improvement.

## Exact records

Paths below are relative to this report's directory. Raw receipt bytes remain unchanged.

| Record | SHA-256 |
|---|---|
| `launch/004_wait_restore_result.json` | `675b35278130e04000ef75a57108dc7d3daedd40137c0079a499aaa92964c346` |
| Raw restore receipt inside that result | `c1f7adca5d7f8a22c7c6080a557eacb89e9061aedb3148a2010c1af87cc77ba6` |
| Raw restore-ready record inside that result | `59eb4b418018bf17355d0277dc15e18be08c6907dea88dccf69f271d83633b98` |
| `launch/005_release_training_result.json` | `4f4ca9e03f1f5f97309ca0e03b3543e8eb8f820ac61bd44d91517330e07bea06` |
| Uploaded training-release bytes, recorded by the parent | `71a0a40208600163c905fffd5775544993d6186aff6c65e39d5152de7d6bd4db` |
| `launch/new_update.json` | `a592c1c0ca33356a1e814f14b1cebc3a32add23d45c2b7a9d34df17a5b312478` |
| Raw step-412 event inside that marker | `e3e53d9d31e111d0758a4af8cbeea7a066abf6b57c157498f2426affe198ac5f` |

## What remains open

The original four-way 16-epoch allocation is unchanged. This cloud slice still has a 4,800-second training ceiling and shared 7,200-second lifecycle deadline. At the old measured pace, another partial result is likely; this is not permission to shorten the allocation or restart from random weights.

There is no new development score or final held-out result in this milestone. Final public release, two fresh prediction processes, private scoring, archive validation and cleanup are later gates. The previous CAS 21/64 development plateau and earlier CAS 0/72 held-out composition result remain separate, unchanged negatives.

The ledger is revision 20: $126 reserved, $274 unreserved, within the inclusive $400 campaign cap. This continuation reserved $8. These are reservations, not the AWS invoice. No diagnostic job or second instance was launched as part of this observation.

The full CAS/CNCM vision remains incomplete. This milestone proves that saved teaching state can be restored on the new worker and followed by a reported new CUDA update; it is not a claim of general reasoning, language ability, CAS-specific advantage or the completed machine.
