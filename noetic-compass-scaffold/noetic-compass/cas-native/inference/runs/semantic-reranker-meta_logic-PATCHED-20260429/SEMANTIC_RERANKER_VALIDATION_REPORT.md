# Semantic Reranker Validation

## Headline

- Exact top-1: 17 / 30 (56.7%)
- Ground truth top-1: 17 / 30
- Ground truth top-5: 22 / 30
- Mean ground-truth rank: 4.9655172413793105
- Compiler-valid outputs: 30 / 30

## Interpretation

The semantic reranker improved exact candidate selection under the current evaluation.

## Training

- Train pairs: 45868
- Eligible records: 11467
- Epochs: 10
- Batch size: 512
- Wall clock seconds: 1143.3

## Epoch Metrics

- epoch 1: loss=0.3838, pairwise_accuracy=0.772
- epoch 2: loss=0.2834, pairwise_accuracy=0.821
- epoch 3: loss=0.2638, pairwise_accuracy=0.832
- epoch 4: loss=0.2529, pairwise_accuracy=0.844
- epoch 5: loss=0.2399, pairwise_accuracy=0.857
- epoch 6: loss=0.2151, pairwise_accuracy=0.873
- epoch 7: loss=0.1901, pairwise_accuracy=0.887
- epoch 8: loss=0.1805, pairwise_accuracy=0.892
- epoch 9: loss=0.1715, pairwise_accuracy=0.897
- epoch 10: loss=0.1632, pairwise_accuracy=0.904

## By Bucket

- v74_baseline: exact=4/5, top5=4/5, mean_rank=1.0
- v75_register: exact=5/5, top5=5/5, mean_rank=1.0
- v77_rule_four: exact=4/5, top5=5/5, mean_rank=1.2
- v77_omega: exact=3/5, top5=5/5, mean_rank=2.0
- v76_production: exact=0/5, top5=0/5, mean_rank=12.2
- meta_logic: exact=1/5, top5=3/5, mean_rank=11.6
