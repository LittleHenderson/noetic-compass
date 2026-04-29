# Family-Reranked Decoding Validation

Run: `family-rerank-1500step-20260429-7e3a479`
Code commit: `7e3a479`
Checkpoint: `v2-first-full-20260428-220635/checkpoints/final.pt`
Dataset: `level2_full_10k.jsonl`
Mode: `--decode-mode rerank --candidate-source hybrid --family-filter prompt`

## Summary

Prompt-family filtering solved the next layer above pure syntax. The model is still not selecting exact ground-truth expressions, but the decoder now reliably selects the requested structural family before scoring candidates.

| Metric | Result |
| --- | ---: |
| Samples | 30 |
| Whole compiler-valid | 30/30 |
| Structured CAS-valid | 30/30 |
| Prompt-family match | 30/30 |
| Required Omega-name anchors | 5/5 |
| Exact ground-truth match | 1/30 |

## Bucket Results

| Bucket | Structured | Family Match | Exact | Unique Outputs |
| --- | ---: | ---: | ---: | ---: |
| v74_baseline | 5/5 | 5/5 | 0/5 | 3/5 |
| v75_register | 5/5 | 5/5 | 0/5 | 4/5 |
| v77_rule_four | 5/5 | 5/5 | 0/5 | 1/5 |
| v77_omega | 5/5 | 5/5 | 1/5 | 4/5 |
| v76_production | 5/5 | 5/5 | 0/5 | 4/5 |
| meta_logic | 5/5 | 5/5 | 0/5 | 5/5 |

## What Changed

The prior reranker scored a broad compiler-valid candidate bank. That made every output syntactically legal, but it still collapsed toward generic high-probability candidates. The family filter now narrows the candidate bank using prompt-inferred structural families before model scoring.

Examples:

- `Omega_clarity arises` filters to Omega-integration candidates containing `Ω_clarity`.
- `typed coordinate` filters to coordinate candidates.
- `combine under ∪` filters to union candidates, not all StateCluster operations.
- `cover SubFoundations` filters to `CoverOf(...)`.

Two code fixes were made during validation:

- `Coordinate{...}` is now counted as structured meta-logic.
- `discovering` no longer falsely triggers the `cover` family.

## Interpretation

This is a real decoder improvement, not a full semantic solution. The pipeline now guarantees:

- legal CAS syntax,
- structured CAS shape,
- requested expression family,
- exact Omega target where the prompt names one.

The remaining failure is slot-level semantic selection. For example, a prompt may ask for a clear-register state and the decoder now picks a register expression, but it does not reliably choose the same Noetic, Domain, Drive, Register, or cluster members as the dataset ground truth.

## Next Engineering Move

Do not spend more GPU time on this exact checkpoint before improving semantic constraints. The next useful patch is a slot-aware prompt filter:

- infer requested Omega name, Noetic IDs, Domain names, Drive/Foundation IDs, Register names, and carrier names from the prompt;
- apply those as hard or soft candidate filters before reranking;
- add a separate slot-match metric alongside exact-match.

That moves evaluation from "right family" to "right family plus right typed components," which is the missing level between compiler-valid decoding and conversational CAS-Native behavior.

## Verification

Local:

```text
python -m py_compile constrained_sampling.py generate_samples.py test_constrained_sampling.py
python -m pytest test_constrained_sampling.py test_tokenizer.py -q
13 passed, 4 skipped
```

Pod:

```text
python cas-native/inference/generate_samples.py \
  --dataset /root/workspace/cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl \
  --checkpoint /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v2-first-full-20260428-220635/checkpoints/final.pt \
  --out-dir /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/inference/runs/family-rerank-1500step-20260429-7e3a479 \
  --decode-mode rerank \
  --candidate-source hybrid \
  --family-filter prompt \
  --rerank-max-candidates 2000 \
  --rerank-batch-size 64 \
  --samples-per-bucket 5
```

