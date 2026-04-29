# Ground-Truth Rerank Diagnostic

Run: `rank-diagnostic-1500step-20260429-f38becf`
Code commit: `f38becf`
Checkpoint: `v2-first-full-20260428-220635/checkpoints/final.pt`
Dataset: `level2_full_10k.jsonl`
Mode: `--decode-mode rerank --candidate-source hybrid --family-filter prompt`

## Summary

This run answers the next architectural question: is exact-match low because the correct expression is missing from the candidate bank, or because the model is scoring the correct candidate too low?

Answer: mostly scoring. The correct candidate is usually present and scoreable, but the current LM-likelihood reranker ranks it far below generic high-probability candidates.

| Metric | Result |
| --- | ---: |
| Samples | 30 |
| Ground truth in base candidate bank | 29/30 |
| Ground truth survived prompt filters | 26/30 |
| Ground truth scoreable | 26/30 |
| Ground truth top-1 | 3/30 |
| Ground truth top-5 | 3/30 |
| Exact match | 3/30 |
| Mean ground-truth rank when scoreable | 390.5 |
| Median ground-truth rank when scoreable | 191 |
| Mean ground-truth rank percentile | 0.488 |

## Bucket Results

| Bucket | GT In Base | GT Filtered | GT Top-1 | GT Top-5 | Mean GT Rank |
| --- | ---: | ---: | ---: | ---: | ---: |
| v74_baseline | 5/5 | 4/5 | 0/5 | 0/5 | 482.0 |
| v75_register | 5/5 | 5/5 | 0/5 | 0/5 | 760.2 |
| v77_rule_four | 4/5 | 4/5 | 0/5 | 0/5 | 582.3 |
| v77_omega | 5/5 | 5/5 | 1/5 | 1/5 | 64.6 |
| v76_production | 5/5 | 3/5 | 0/5 | 0/5 | 543.3 |
| meta_logic | 5/5 | 5/5 | 2/5 | 2/5 | 28.6 |

## Interpretation

The earlier exact/ordered slot policies fixed prompt-literal cases. This diagnostic shows the remaining problem is learned semantic preference, not syntax:

- The candidate bank is broad enough for most ground truths.
- The filters only remove 4 of 30 ground truths; 3 of those are explainable by prompt-slot mismatch or candidate-bank grammar scope.
- For the 26 scoreable ground truths, the model usually ranks the correct answer hundreds of places down.
- The only top-5 cases are already exact matches.

That means more hand-written filters will have diminishing returns. The next useful component is a semantic reranker trained to prefer the dataset target over near-miss compiler-valid candidates.

## Filter Misses

Four examples did not survive to the scored candidate set:

- v74 baseline single-state expression was removed by the family filter because the prompt admits multiple v74 forms and the selected candidate family narrowed differently.
- v77 Rule 4 expression was absent from the base bank; the candidate bank does not currently enumerate that exact bare integration form.
- Two v76 production ground truths were filtered out by explicit domain-slot constraints because the prompt asked for cognitive/evaluative/operational or principled/cognitive/operational domains, while the dataset target used mostly principled ingredients.

Those are useful, but they are not the dominant failure mode.

## Next Engineering Move

Build a contrastive semantic reranker:

1. For each training example, build the same filtered candidate bank used here.
2. Score the ground truth as the positive candidate.
3. Sample hard negatives from the current top-ranked wrong candidates.
4. Train a lightweight prompt-candidate scorer with pairwise or cross-entropy loss.
5. Replace or augment LM-likelihood reranking with semantic-reranker score.

Success metric for the next validation:

- Ground-truth top-5 should rise materially before exact-match rises.
- Then exact-match should rise after top-1 improves.

This is the right order: first recover the target into the top candidate set, then optimize exact top-1.

## Verification

Local:

```text
python -m py_compile generate_samples.py test_constrained_sampling.py
python -m pytest test_constrained_sampling.py test_tokenizer.py -q
19 passed, 5 skipped
```

Pod:

```text
python cas-native/inference/generate_samples.py \
  --dataset /root/workspace/cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl \
  --checkpoint /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v2-first-full-20260428-220635/checkpoints/final.pt \
  --out-dir /root/workspace/noetic-compass-scaffold/noetic-compass/cas-native/inference/runs/rank-diagnostic-1500step-20260429-f38becf \
  --decode-mode rerank \
  --candidate-source hybrid \
  --family-filter prompt \
  --rerank-max-candidates 2000 \
  --rerank-batch-size 64 \
  --samples-per-bucket 5
```

