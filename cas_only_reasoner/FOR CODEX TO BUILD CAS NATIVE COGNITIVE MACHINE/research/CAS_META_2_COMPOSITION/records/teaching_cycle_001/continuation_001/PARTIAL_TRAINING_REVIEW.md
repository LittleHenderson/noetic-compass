# Continuation 001: partial teaching result

Recorded 2026-09-08. **Training continued successfully from saved state, but this partial run does not show a clear CAS learning benefit or a finished learning experiment.** CAS remains substantially behind the matched generic candidates on the saved development checks.

The frozen allocation remains 16 epochs and 896 optimizer updates per candidate. This report does not shorten that allocation or change the teaching procedure.

## Scope and evidence boundary

The experiment teaches one input-binding decision: choose the correct observation slot for a requested tag. It uses a fixed child operation, `A`. These scores do not measure learned child selection, nested-program composition, native execution, or complete-task correctness.

The four candidates use the same 256 training cases, 64 development cases, seed 7, batch size 32, and planned 16-epoch allocation. “Aligned” means the seven-stage teaching cycle; “ordinary” is the matched ordinary-teaching condition. The two model families use the same causal decoder and observation-pointer design. The recorded parameter counts are 181,163 for CAS and 181,203 for generic; the 40-parameter difference is about 0.0221%.

All four candidates remained in full guidance. The accepted model and executor were not updated.

The formal evaluator completed with exit code 0 and returned `PARTIAL_EXPOSURE_ONLY`, not a final-score acceptance. It verified the pinned continuation records and 3,278 unchanged prior payload files. Actual CUDA restoration was worker-recorded and admitted by the parent; the evaluator did not repeat that restoration.

For this report, an additional read-only calculation checked the 64 permitted development targets against their requested tags and observation slots, then recounted correct answers from the saved prediction arrays. All 31 recorded checks from epochs 7–14 agreed: 1,984 saved predictions in total. Prior development rows matched the old summary unchanged. This calculation did not load a neural checkpoint, perform a new forward pass, or independently reproduce model predictions.

There is no untrained development measurement. Epochs 1–3 each recorded zero attempted development cases because the minimum teaching exposure had not been completed; they must not be presented as 0/64 accuracy. No final public release, final prediction seals, private final-target opening, final scores, native execution, or retention-after-intervening-learning result exists for this partial run. No applicable-rule model comparison was executed in this report; checking target consistency is not that comparison.

## Training progress

| Candidate | Restored updates | New updates in this slice | Total saved updates | Remaining to 896 |
|---|---:|---:|---:|---:|
| CAS aligned | 411 | 373 | 784 | 112 |
| CAS ordinary | 392 | 392 | 784 | 112 |
| Generic aligned | 392 | 392 | 784 | 112 |
| Generic ordinary | 392 | 382 | 774 | 122 |
| **Total** | **1,587** | **1,539** | **3,126** | **458** |

The first three candidates completed 14 epochs. Generic ordinary completed 13 epochs and 46 of the 56 updates in epoch 14; its saved cursor is `{"batch":6,"epoch":13,"stage":4}`, using the runner's zero-based cursor.

The continuation records 49,248 new stage-example presentations, for 100,032 cumulative stage-example presentations. These are repeated teaching presentations, not 100,032 unique tasks. The unique training set still contains 256 cases.

The training process exited 0 with `TEACHING_INCOMPLETE`. Its recorded worker wall time was `4775.023256590999` seconds, about 79 minutes 35 seconds, within the outer 4,800-second process limit. The process command requested a 4,770-second internal work allowance. Process exit 0 means the partial state was saved cleanly; it does not mean the 16-epoch allocation finished.

## Development curve: all recorded epochs 7–14

Each number is **correct bindings / attempted development cases** on the same 64-case set. Epoch 7 is the last completed check before this continuation. It is not an untrained baseline.

| Completed epoch | CAS aligned | CAS ordinary | Generic aligned | Generic ordinary |
|---|---:|---:|---:|---:|
| 7, before continuation | 21/64 | 21/64 | 42/64 | 46/64 |
| 8 | 21/64 | 21/64 | 42/64 | 41/64 |
| 9 | 20/64 | 20/64 | 45/64 | 47/64 |
| 10 | 24/64 | 21/64 | 41/64 | 46/64 |
| 11 | 23/64 | 21/64 | 45/64 | 40/64 |
| 12 | 17/64 | 20/64 | 42/64 | 43/64 |
| **13, latest common epoch** | **23/64** | **18/64** | **42/64** | **48/64** |
| 14 | 20/64 | 24/64 | 49/64 | No check recorded |

Generic ordinary has no epoch-14 prediction array or attempted-case denominator. Its epoch-13 score must not be relabeled as an epoch-14 result or filled in as 0/64.

The latest-common-epoch comparison is epoch 13, after 728 updates for each candidate:

| Candidate | Epoch 7 | Epoch 13 | Change in correct answers |
|---|---:|---:|---:|
| CAS aligned | 21/64 | 23/64 (35.94%) | +2 |
| CAS ordinary | 21/64 | 18/64 (28.13%) | -3 |
| Generic aligned | 42/64 | 42/64 (65.63%) | 0 |
| Generic ordinary | 46/64 | 48/64 (75.00%) | +2 |

These are descriptive results from one seed and a repeatedly used development set, not a statistical claim of generalization or a controlled CAS advantage. At epoch 13, aligned teaching is five answers ahead of ordinary teaching for CAS; at epoch 14 it is four answers behind. That reversal and the low CAS scores do not support a reliable teaching-cycle benefit for CAS.

The development target distribution is 22 cases for slot 0 and 21 each for slots 1 and 2. CAS scores remain close to these constant-slot counts. This comparison is descriptive; it is not proof of the internal cause of the plateau.

The earlier 24/24 familiar-program practice result and CAS 0/72 held-out composition result remain separate evidence. Neither is replaced or softened by this binding experiment.

## Checkpoint identities

Latest checkpoints are the states to resume from. Development-selected checkpoints are the best eligible saved states selected by the existing development-only procedure so far; they are not necessarily the latest states and are not final winners.

The following SHA-256 values are hashes of the actual `candidate.pt` files, checked without loading tensors. Each path is inside the retained extraction under `train/campaign/<candidate>/journal/txn-<number>/candidate.pt`.

| Candidate | Role | Transaction | File SHA-256 |
|---|---|---:|---|
| CAS aligned | Latest, after epoch 14 | 16 | `088054289ecfe1bca9b9156fdabc59ceecc7dde6f8c8d0a7a81bc7054b08b3d5` |
| CAS aligned | Development selected, epoch 10, 24/64 | 12 | `853720d54b29f0ff33efe5ea209cb07c908683a23c3eb122ab56f97612a3577f` |
| CAS ordinary | Latest and development selected, epoch 14, 24/64 | 15 | `413676bb08302aedcba3dd7097c7bc8b0cdc224c5e55ce19d198734cd21a58af` |
| Generic aligned | Latest, after epoch 14 | 15 | `dcf2faa105ad30d9ce3365f4f1aaa5d6d6914a5f306484370332e3f28e1f31f6` |
| Generic aligned | Development selected, epoch 6, 49/64 | 7 | `0d89ab29cfa0075949b82dcdc2e502a2fd312e14ec15ba8c12e9f471e54b2daf` |
| Generic ordinary | Latest, partway through epoch 14 | 15 | `6f790d894d3668c1bc03c6fcbf4713d111df57baf9ebe46c5f3deaf4c5c30f31` |
| Generic ordinary | Development selected, epoch 13, 48/64 | 14 | `3f86bfd971e7c7f06f7ad658b7f7a0cfca6a117151d48ec0a808988fba5c8c32` |

All eight latest/selected references were checked; CAS ordinary's two references identify the same file.

The curve's `checkpoint_sha256` field identifies model state, not the serialized checkpoint file. For the fair epoch-13 comparison, those state identities are:

| Candidate | Epoch-13 model-state SHA-256 |
|---|---|
| CAS aligned | `9b217787039561736584d01092214638ac7210a84c6afca375abdcca4f1d8d2d` |
| CAS ordinary | `4c6d9d8217de988f3d2b0f2f132579918649e010c78daa814dc478e4e8acefff` |
| Generic aligned | `682092e5000857b79c0536555daafaf0a7182223c3720af9d4411db0ab5b4857` |
| Generic ordinary | `9cd90aad267d5fd74cab0ce5758a11d3957f96828d76569ef5faaa6e1c89495a` |

## Bound source and records

- New cloud job: `cas-meta2-teaching-20260908080138-5518e287`.
- Original logical training run: `cas-meta2-teaching-20260908052915-8b5df59c`.
- Continuation transport source freeze: `a4b1af8519bd8def6e8cbb16f6d14ef72d99fa6b`.
- Frozen neural worker commit: `c8c0e558cf30cd5fe06c2bf3d475697e97698a3e`.
- Frozen worker source-map SHA-256: `60340b5865c674cc5558a27da6524928ec0db7042163b1ef031591ad7794555e`.
- Original worker ZIP SHA-256: `494f44d467a85e2edd54b568cf4b0822db6e25355003a8a6ae8c7d4c09dd8cec`.
- Worker manifest SHA-256: `975296defc543e234d4bd09fcf9e46a25dc42792e4cf6aed5ad35332de3167a9`.

Record paths in the following table are relative to this report's directory:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/continuation_001`

| Record | SHA-256 |
|---|---|
| `evaluation_001/evaluation.json` | `cd2d7cce4a3b75385d8f8348d6628b5edc43bcb18a10134f82f62567bc04ba05` |
| `evaluation_001/extracted/train_continued_001/campaign_summary.json` | `2cb6f5659a0377695b00e49f5a45d9edff6f87db6fe648927c4719d26a15d33b` |
| `launch/result.json`, original parent report | `ffb42912a72759a2c440571bcd929c397a8cc653b3d288d3a758221d52e4d86d` |
| `launch/partial_collected/complete.json` | `aac9bfe609b3c9d04c0ad83f8fb209bcf7da12f1c79529e02c39b4f162db7d84` |
| `launch/partial_collected/artifacts.zip`, 201,729,956 bytes | `43795d51cdc1fba4c70b0d7c0cd27f4beaedbb7dbfbf1c89dc358946f069cd38` |
| Raw restore receipt admitted by the parent | `c1f7adca5d7f8a22c7c6080a557eacb89e9061aedb3148a2010c1af87cc77ba6` |
| Original job003 summary, retained as `evaluation_001/extracted/train/campaign_summary.json` | `26b23bb5f23ca875375797db155e8520b947bf0b4eada71e596a9ec7493e195f` |

The retained result archive contains 6,468 members and expands to 259,519,669 bytes. The evaluator retained the original archive.

The permitted development file used for the additional score recount is:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/bundle_002/extracted/development.json`

Its raw file SHA-256 is `f12851d848f10b69abc8db73b380ec002972ba2dbc651acb2e08924fb34efd16`. The canonical development-case identity recorded by the worker is `45682abc65433707099691c3e849536c06a47c12604022ff97527922e886b667`; this differs from the raw file hash because it identifies canonical JSON content.

## Cleanup and next step

**Supplemental cleanup closed.** The original parent report remains unchanged: its termination observation window did not confirm shutdown. The first supplemental attempt stopped before mutations because the exact instance query returned no record. The second attempt verified absence with exact-ID, job-tag and client-token queries, checked the remaining resource ownership, removed the job's profile, two roles and inline policies, and security group, and verified the shutdown schedule was already absent. It did not request termination, delete volumes, modify S3 objects, or change the budget ledger.

`cleanup_recovery_002/result.json` has SHA-256 `4e49318d473776359a2c2097a180604e1d72e56aa1e4555569d7d6a3e06efc63` and status `CLEANUP_CLOSED_RESULTS_RETAINED`. Its compute state is `CONFIRMED_ABSENT_NOT_TERMINATION_RECEIPT`; this is not a newly observed termination event. All six result objects retained their observed identities under the existing seven-day lifecycle. The local result archive is also retained. The helper exited 0. The recorded counters advanced from control 347 / S3 532 to control 390 / S3 538; downloaded bytes stayed 201,761,654. All original reports, prior recovery records, frozen provider sources and the canonical ledger remained unchanged.

The separate cleanup helpers passed 40 and 83 fake-only tests respectively. Those tests concern cleanup behavior, not learning.

The next learning step is to preserve all four latest checkpoints and complete the original 458 remaining updates without changing the frozen comparison. Final public evaluation remains behind completion and checkpoint-selection checks. A separate read-only diagnostic may investigate the weak CAS binding behavior, but it must not modify the current comparison or turn a proposed explanation into an observed cause.

The full CAS/CNCM vision remains open. This partial result establishes additional recorded teaching work and a saved development curve; it does not establish language capability, general reasoning, CAS-specific advantage, native composition, production readiness, or completion of the machine.
