# Semantic Reranker Validation

## Headline

- Exact top-1: 12 / 30 (40.0%)
- Ground truth top-1: 12 / 30
- Ground truth top-5: 24 / 30
- Mean ground-truth rank: 5.111111111111111
- Compiler-valid outputs: 30 / 30

## Interpretation

The semantic reranker improved exact candidate selection under the current evaluation.

Compared with the prior Level 2 semantic-reranker diagnostic, this is a structural improvement:

- Exact top-1 improved from 2 / 30 to 12 / 30.
- Ground-truth top-5 improved from 2 / 30 to 24 / 30.
- Mean ground-truth rank improved from 363.8 to 5.11.
- Pairwise training accuracy improved from 0.657 to 0.985.

The improvement came from the recoverable Level 3 prompt layer, not from a compiler change. The core lesson is that CAS-Native needs prompts that expose recoverable Noetic/Domain/Drive/Register/recipe slots when exact expression recovery is the target.

## Training

- Train pairs: 69360
- Eligible records: 17340
- Epochs: 10
- Batch size: 512
- Wall clock seconds: 1783.9

## Epoch Metrics

- epoch 1: loss=0.3605, pairwise_accuracy=0.803
- epoch 2: loss=0.1275, pairwise_accuracy=0.940
- epoch 3: loss=0.0846, pairwise_accuracy=0.961
- epoch 4: loss=0.0614, pairwise_accuracy=0.971
- epoch 5: loss=0.0494, pairwise_accuracy=0.975
- epoch 6: loss=0.0416, pairwise_accuracy=0.979
- epoch 7: loss=0.0375, pairwise_accuracy=0.981
- epoch 8: loss=0.0336, pairwise_accuracy=0.982
- epoch 9: loss=0.0297, pairwise_accuracy=0.984
- epoch 10: loss=0.0276, pairwise_accuracy=0.985

## By Bucket

- v74_baseline: exact=2/5, top5=4/5, mean_rank=2.5
- v75_register: exact=2/5, top5=5/5, mean_rank=2.2
- v77_rule_four: exact=4/5, top5=5/5, mean_rank=1.2
- v77_omega: exact=1/5, top5=4/5, mean_rank=5.0
- v76_production: exact=2/5, top5=4/5, mean_rank=3.2
- meta_logic: exact=1/5, top5=2/5, mean_rank=23.333333333333332
