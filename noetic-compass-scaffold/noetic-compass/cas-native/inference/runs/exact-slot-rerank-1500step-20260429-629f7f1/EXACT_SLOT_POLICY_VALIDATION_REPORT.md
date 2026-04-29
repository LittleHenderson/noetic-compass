# Exact Slot-Policy Rerank Validation

Run: `exact-slot-rerank-1500step-20260429-629f7f1`
Code commit: `629f7f1`
Checkpoint: `v2-first-full-20260428-220635/checkpoints/final.pt`
Dataset: `level2_full_10k.jsonl`
Mode: `--decode-mode rerank --candidate-source hybrid --family-filter prompt`

## Summary

Exact/ordered slot policies improved the two concrete failures from the prior slot-aware run without regressing compiler validity, structural validity, family match, or slot match.

| Metric | Previous Slot Run | Exact-Policy Run |
| --- | ---: | ---: |
| Samples | 30 | 30 |
| Whole compiler-valid | 30/30 | 30/30 |
| Structured CAS-valid | 30/30 | 30/30 |
| Prompt-family match | 30/30 | 30/30 |
| Required Omega-name anchors | 5/5 | 5/5 |
| Slot-match where applicable | 12/12 | 12/12 |
| Slot-policy match where applicable | n/a | 2/2 |
| Exact ground-truth match | 1/30 | 3/30 |
| Meta-logic exact match | 0/5 | 2/5 |

## Targeted Fixes Verified

The previous slot-aware run was containment-correct but not exact:

```text
Product prompt:
before: Product(Domains, Foundations)
after:  Product(Foundations, Domains)

NoeticCluster prompt:
before: NoeticCluster{^4, ^3, ^1, ^8, ^7}
after:  NoeticCluster{^8, ^3}
```

Both are now policy-correct:

- `Product(Foundations, Domains)` uses ordered carrier matching.
- `NoeticCluster over noetics 8, 3` uses exact Noetic member matching.

## Bucket Results

| Bucket | Structured | Family Match | Slot Match | Policy Match | Exact | Unique Outputs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v74_baseline | 5/5 | 5/5 | n/a | n/a | 0/5 | 3/5 |
| v75_register | 5/5 | 5/5 | n/a | n/a | 0/5 | 4/5 |
| v77_rule_four | 5/5 | 5/5 | n/a | n/a | 0/5 | 1/5 |
| v77_omega | 5/5 | 5/5 | 5/5 | n/a | 1/5 | 4/5 |
| v76_production | 5/5 | 5/5 | 4/4 | n/a | 0/5 | 4/5 |
| meta_logic | 5/5 | 5/5 | 3/3 | 2/2 | 2/5 | 5/5 |

## Interpretation

The decoder is now operating in a clearer layered way:

1. Compiler-valid candidate bank guarantees legal CAS.
2. Family filter picks the expression shape.
3. Slot filter preserves explicit typed content.
4. Exact/ordered policy filter handles closed-set and ordered constructs.
5. Model reranking chooses within that narrower candidate set.

This is a meaningful product-facing step: when users ask for `Product(Foundations, Domains)` or a `NoeticCluster` over named noetics, the system now respects the literal structure instead of returning a merely related expression.

## Remaining Gap

Exact-match is still low outside prompts with explicit symbolic anchors. That is expected because many prompts are prose-only, e.g. "a doctor facing an unfamiliar diagnosis," and do not expose explicit Noetic/Domain/Drive/Register slots. The current filter cannot infer those deep semantic labels without a stronger natural-language semantic parser or supervised classifier.

The next useful engineering layer is not another syntax filter. It is one of:

- Add supervised NL-to-slot classifiers for Noetic, Domain, Drive/Foundation, Register, and recipe target.
- Add prompt templates that expose symbolic hints during evaluation.
- Add a contrastive reranker trained to prefer the dataset ground truth over near-miss candidates.

## Verification

Local:

```text
python -m py_compile constrained_sampling.py generate_samples.py test_constrained_sampling.py
python -m pytest test_constrained_sampling.py test_tokenizer.py -q
19 passed, 4 skipped
```

Pod:

```text
python cas-native/inference/generate_samples.py \
  --dataset /root/workspace/cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl \
  --checkpoint /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v2-first-full-20260428-220635/checkpoints/final.pt \
  --out-dir /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/inference/runs/exact-slot-rerank-1500step-20260429-629f7f1 \
  --decode-mode rerank \
  --candidate-source hybrid \
  --family-filter prompt \
  --rerank-max-candidates 2000 \
  --rerank-batch-size 64 \
  --samples-per-bucket 5
```

