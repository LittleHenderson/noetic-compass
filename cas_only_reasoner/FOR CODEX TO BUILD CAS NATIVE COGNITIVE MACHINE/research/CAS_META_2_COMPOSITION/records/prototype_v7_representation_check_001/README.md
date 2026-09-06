# V7 saved-target representation check

All 1,064 saved targets can be represented and completed by the actual frozen codec and grammar. This rules out several interface mistakes for this packet. It does not show that either model learned to choose those targets.

This is a post-run, read-only diagnosis of existing data. It does not generate tasks, load checkpoints, create tensors, run the executor, contact AWS, or change the learning results. The checker uses the private test targets only after the completed run and its pinned byte audit.

## Rebuild

Use PowerShell from the exact package directory below. The output directory must be new; use `run_002` for the next reproduction.

```powershell
Set-Location -LiteralPath 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION'
python -B records/prototype_v7_representation_check_001/check.py --output records/prototype_v7_representation_check_001/run_002
```

The executed command was the same command with `run_001`. It exited 0. `run_output.txt` preserves its complete raw output. `run_001/receipt.json` records the command, Python identity, exact source/input hashes, counts, start/end times, and boundaries. Its SHA256 is `1b8829268149b0dc334525718932951414db320e2986a7d7027e54776147f0f7`.

## Checked result

| Saved split | Tasks | Maximum encoded input / limit | Maximum target tokens / limit | Complete gold grammar paths |
|---|---:|---:|---:|---:|
| Training | 896 | 469 / 1024 | 111 / 256 | 896 |
| Validation | 96 | 449 / 1024 | 107 / 256 | 96 |
| Private test | 72 | 469 / 1024 | 115 / 256 | 72 |

The check covered 98,296 target-token transitions. Every target passes codec serialization and decoding, then the actual `grammar_v3` prefix transitions and final action decoding. All public text round-trips exactly. Every copy span agrees with the frozen encoded text. Every required procedure, variable, and CJT spelling occurs in its problem's copy spans. No validation/test target token is absent from positive training targets. Source and input hashes were unchanged at the end.

The result rules out unsupported target names, missing required copy spellings, silent input/target truncation, and gold-program rejection caused by the canonical declaration order. It does **not** rule out a model emitting the wrong prefix or using its length budget on incorrect extra declarations.

Text losslessness is not numeric tensor losslessness. This check does not measure float32 precision, neural logits, gradients, weight updates, native answers, or the cause of the observed learning failure. No model package was imported.

## Source observations, not causal findings

- `cas_meta2/contrast_v7/train.py:131` uses the same `policy_v3` encoder, targets and predictor; training pairs each public input with its target at lines 248-258. `policy.py:96` implements the expected one-token teacher-forcing shift. No source-level off-by-one target mismatch was found.
- `policy_v3.py:228` explicitly imports `grammar_v3`, not the separately prepared `grammar_viability_v4`. The original grammar can permit a prefix choice that later has no legal completion (`grammar_v3.py:98` and `grammar_v3.py:119`). The existing viability helper documents two narrow examples. Attribution to actual rejected token paths belongs to the separate token-path diagnosis; this record does not claim that replacing the grammar would produce correct programs.
- `selection_v2.py:21` scores the exact serialized program, including names and scope-list order. It is not an equivalence-aware execution score. The saved native negatives remain separate and are not overturned by this observation.

## Identity and limits

Frozen source: `42f9164754312f12850d9b8789c062fa7fb8069f`.

Job: `cas-meta2-20260906094002-39762c47`.

Original packet SHA256: `f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799`.

The checker first verifies the exact partial-native receipt `bc700054e18dad6de9e2516f441adccdfac0a9ace25a39fd0fce6a0879d37f4f`, extraction receipt `9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98`, and training recount `452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76`. Their published source/input pins are checked before imports or task reads, and checked again afterward. Fifteen relevant source files are hashed; only six pure package modules are imported. The large packet is not extracted or fully re-audited again.

No original data, checkpoint, source, ledger, or historical conclusion is changed. Target reachability is not a learning result, and this record does not promote the partial campaign to completion.
