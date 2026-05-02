# Structured-Token 20-Epoch GPU Run

**Run:** `structured-token-20epoch-gpu-20260502-001907`  
**Commit basis:** `2366628`  
**Hardware:** RunPod RTX A6000, 49 GB  
**Mode:** `StructuredTokenEmbedding + StructuredPredictionHead`  
**Training set:** `level3_recoverable_full.jsonl`, filtered to 17,974 non-overlapping records  
**Held-out eval:** `level3_recoverable_eval_1000.jsonl`  

## Headline

The structured-token substrate decisively beat the honest leak-fixed hash baseline.

| Metric | Hash baseline | Structured-token run | Delta |
|---|---:|---:|---:|
| All-heads exact | 487 / 1000 | 853 / 1000 | +366 |
| All-heads exact rate | 48.7% | 85.3% | +36.6pp |

This is the first strong empirical result for the CAS-native tokenizer path: a 290-entry structured-token vocabulary with CAS-axis side channels beats deterministic hash features by a wide margin on the same held-out 1K eval.

## Per-Bucket Result

| Bucket | n | Exact | Rate |
|---|---:|---:|---:|
| v74_baseline | 194 | 194 | 100.0% |
| v75_register | 262 | 217 | 82.8% |
| v76_production | 104 | 72 | 69.2% |
| v77_rule_four | 106 | 46 | 43.4% |
| v77_omega | 218 | 218 | 100.0% |
| meta_logic | 116 | 106 | 91.4% |

`v77_rule_four` is the only major laggard. Its failures are concentrated in `expression_family` and `transition_kind`, while noetic/domain/drive/register axes are essentially solved.

## Per-Head Accuracy

| Head | Accuracy |
|---|---:|
| turn_type | 100.0% |
| authority | 100.0% |
| has_omega | 100.0% |
| has_meta_logic | 100.0% |
| meta_relations | 100.0% |
| domain | 99.2% |
| registers | 98.2% |
| drive | 97.4% |
| noetic | 96.7% |
| register_mode | 96.6% |
| transition_kind | 94.3% |
| expression_family | 94.1% |

## Trajectory

The run crossed the hash baseline at epoch 4 and kept improving:

| Epoch | Exact | Rate | Delta vs Hash |
|---:|---:|---:|---:|
| 0 | 183 | 18.3% | -30.4pp |
| 1 | 410 | 41.0% | -7.7pp |
| 2 | 461 | 46.1% | -2.6pp |
| 3 | 478 | 47.8% | -0.9pp |
| 4 | 512 | 51.2% | +2.5pp |
| 5 | 559 | 55.9% | +7.2pp |
| 6 | 625 | 62.5% | +13.8pp |
| 7 | 690 | 69.0% | +20.3pp |
| 8 | 705 | 70.5% | +21.8pp |
| 9 | 743 | 74.3% | +25.6pp |
| 10 | 795 | 79.5% | +30.8pp |
| 14 | 809 | 80.9% | +32.2pp |
| 17 | 841 | 84.1% | +35.4pp |
| 19 | 853 | 85.3% | +36.6pp |

## Implementation Notes

- The original launch exposed a CPU-bound startup issue: the runner re-tokenized prompts repeatedly and the adapter loaded the seed lexicon per record.
- `2366628` fixed this by caching train/eval token sequences once, loading the lexicon once per corpus pass, and emitting progress logs every 1,000 records during startup.
- GPU utilization remained low (~12-14%) because batch tensor construction is still Python-heavy. The result is strong enough that the next engineering optimization is a prebuilt tensor dataset, not more proof-of-concept plumbing.

## Artifacts

Committed:

- `manifest.json`
- `samples.jsonl`
- `structured_token_vocab.json`
- `launch.log`
- `STRUCTURED_TOKEN_RUN_REPORT.md`

Local only / off-VCS:

- `best_structured_token_model.pt` (tiny checkpoint, retained locally for debugging but ignored by `.gitignore`)

## Next

1. Add a prebuilt tensor-cache dataset for structured-token batches to raise GPU utilization and reduce wall-clock.
2. Diagnose `v77_rule_four` family/transition-kind confusion.
3. Expand lexicon/tagger coverage only after the tensor-cache runner confirms the current 85.3% result is reproducible.
