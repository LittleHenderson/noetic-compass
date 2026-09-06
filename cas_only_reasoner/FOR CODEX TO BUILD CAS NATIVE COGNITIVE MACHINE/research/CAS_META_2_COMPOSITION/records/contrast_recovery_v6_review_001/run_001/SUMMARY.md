# Recovered v6 evaluation — independently checked

The recovery evidence passed its independent offline review. The learning result is negative: CAS and the matched generic model each solved **0/72 before training and 0/72 after training**. The rule selector solved **72/72**. Valid execution traces are not correct task answers.

This is the recovered v6 experiment only. It does not replace the separate earlier result of CAS 0/72 versus generic 12/72. The original v6 campaign remains a failed run; this separate recovery reused its saved predictions without retraining, changing actions, or claiming a fresh test.

## Verified task scores

| Test group | Cases | CAS before → after | Generic before → after | Rule |
|---|---:|---:|---:|---:|
| All | 72 | 0 → 0 | 0 → 0 | 72 |
| Depth 3 | 48 | 0 → 0 | 0 → 0 | 48 |
| Depth 4 | 24 | 0 → 0 | 0 → 0 | 24 |
| Same-depth condition | 24 | 0 → 0 | 0 → 0 | 24 |
| Changed wording | 24 | 0 → 0 | 0 → 0 | 24 |
| Deeper calls | 24 | 0 → 0 | 0 → 0 | 24 |

These are overlapping views of the same 72 cases, not additional cases. Depth 3 combines the same-depth and changed-wording conditions. Depth 4 is the deeper-call condition. The cases are 24 related triplets, not 72 independent structures.

## What happened to the saved choices

| Selector | Rejected before execution | Complete executions, all wrong except rule | Failed after execution started | Correct tasks |
|---|---:|---:|---:|---:|
| CAS untrained | 72 | 0 | 0 | 0 |
| CAS trained | 47 | 20 | 5 | 0 |
| Generic untrained | 72 | 0 | 0 | 0 |
| Generic trained | 49 | 17 | 6 | 0 |
| Rule | 0 | 72 | 0 | 72 |

Training reduced rejections, but it did not improve task correctness. The 11 post-start failures are not pre-execution rejections. They retain the exact runtime error: `repair cannot open without a durable distinct ^6 round trip`. Their failure files and committed database records remain preserved.

For trained CAS, the frozen verifier found 20 correct input bindings, 47 incorrect bindings, and 5 unknown bindings. For trained generic, it found 16 correct bindings, 50 incorrect bindings, and 6 unknown bindings. Both had zero confirmed correct procedures or dependencies. Unknown fields remain unknown.

## Recorded mistakes and compute limits

All 20 complete wrong CAS runs and all 17 complete wrong generic runs have a recorded trajectory difference from the correct rule run. The first-difference categories are not exclusive:

| First recorded difference category | CAS trained | Generic trained |
|---|---:|---:|
| Wrong child called | 7 | 3 |
| Operation-kind difference | 6 | 4 |
| Input-binding difference | 4 | 9 |
| Early return | 3 | 1 |
| Wrong CJT selected | 1 | 1 |
| Output binding or value difference | 1 | 1 |

Literal named-site diagnostics are separate from task correctness. CAS matched 29/72 observation bindings, 252/1032 named input sites, and 20/216 named child sites. Generic matched 29/72, 258/1032, and 13/216 respectively. These exact-name comparisons can penalize equivalent renaming.

Three of five CAS failed prefixes and five of six generic failed prefixes contain a recorded RUN disagreement. The other three prefixes match the selected reference fields up to their last committed row; missing later rows do not prove an early return. A first recorded difference is not proof of the earliest causal neural error.

Post-start failures by zero-based case index:

- CAS: 9, 18, 32, 39, 53.
- Generic: 7, 32, 43, 46, 48, 52.

Committed work is a lower bound: CAS trained 303 native runs / 21,816 reserved policy units; generic trained 276 / 19,872; rule 816 / 58,752. Each failed tick's compute is unknown, so the two trained arms' compute totals are incomplete. The policy-unit figures are accounting units, not measured GPU FLOPs or a complete cost estimate.

## Checkpoints and evidence coverage

The original training receipt records 200 epochs and 8,000 optimizer steps for each family. The evaluated selected checkpoints were CAS epoch 180 / 7,200 steps and generic epoch 160 / 6,400 steps. All six initial/selected/final checkpoint files were checked as opaque bytes against that receipt; no checkpoint was loaded as a model.

- CAS selected: `5e15e4ce58677350ee295501e0a1b3fa102066b5c58de492aa04a8bc73c98477`.
- Generic selected: `09756cfe26b6bac50c28ecd7665149f69d410df5a9546cfd332d9b9ffeda654c`.

The checker verified all 2,435 packet members, 557 source files, 316 protected files, 72 references, 360 saved choices, and 192 main-evaluation databases. Across the full packet, including test evidence, 2,288 stored traces in 206 databases passed schema checks. The 194 complete trace exports contained 2,193 traces; partial failures do not acquire complete exports.

The two recovery GPU tests and the original four execution-contract GPU tests passed their bound process/identity checks. The recovery native process exited 0 in 2,221.573727747 seconds. The offline reviewer exited 0 in 720.3806504 seconds with empty stderr. It used no models, GPU, provider calls, task generation, or checkpoint selection.

This proves stored-record consistency and source-bound program replay within the stated checks. It does not independently rerun neural arithmetic or prove that any self-consistent output was produced by a GPU. No CAS-specific advantage, fresh-test result, accepted-learning promotion, or production-readiness claim follows.

## Exact receipt and input identities

[Independent review receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/contrast_recovery_v6_review_001/run_001/recovery_stored_review.json>)

SHA256: `5396e0ab263fa435eefd2b8925382ce802b7af7c8d1c4dae5702d51435349ac3`

Status: `RECOVERY_STORED_REVIEW_PASSED`; completed: true; no errors.

[Exact command and raw execution records](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/contrast_recovery_v6_review_001/execution_001/process_receipt.json>)

Process receipt SHA256: `b06af16e55472390100802875a7fbecb1faf9083898ebc7598cb4c69bf07fd88`.

- Job: `cas-meta2-20260906082659-383a339d`.
- Recovery packet: `4b5022d57c6d6f446463284dd79c7a9b3bf588754314b9110029a39827c6a57c`, 63,906,943 bytes.
- Recovery source: `cbf13795202094865744f7c0b5efa234451f9208`.
- Source archive: `54101904990bf3945dc1242e80982f05a47853a4fce56f2d9c88e9c9bb6f3bb7`.
- Runtime manifest: `897c6a72c7411676c4ad80ac9734b3dbe7a7ac169951f58d2ab2fd6d387ecb37`.
- Original failed packet: `db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def`.
- Failure-admission receipt: `d479c90f711d417f2f585b87a0b746e250db8db12029df1586a4fbabf3b82420`.

This summary is derived from that completed receipt. It does not change the receipt, checker, frozen source, packet, or prior findings.

