# Semantic Reranker Validation

## Headline

- Exact top-1: 19 / 30 (63.3%)
- Ground truth top-1: 19 / 30
- Ground truth top-5: 22 / 30
- Mean ground-truth rank: 6.758620689655173
- Compiler-valid outputs: 30 / 30

## Interpretation

The semantic reranker improved exact candidate selection under the current evaluation.

## Training

- Train pairs: 47192
- Eligible records: 11798
- Epochs: 10
- Batch size: 512
- Wall clock seconds: 1152.1

## Epoch Metrics

- epoch 1: loss=0.3825, pairwise_accuracy=0.775
- epoch 2: loss=0.2780, pairwise_accuracy=0.824
- epoch 3: loss=0.2596, pairwise_accuracy=0.836
- epoch 4: loss=0.2492, pairwise_accuracy=0.847
- epoch 5: loss=0.2329, pairwise_accuracy=0.860
- epoch 6: loss=0.2062, pairwise_accuracy=0.878
- epoch 7: loss=0.1894, pairwise_accuracy=0.889
- epoch 8: loss=0.1755, pairwise_accuracy=0.895
- epoch 9: loss=0.1675, pairwise_accuracy=0.902
- epoch 10: loss=0.1640, pairwise_accuracy=0.901

## By Bucket

- v74_baseline: exact=4/5, top5=4/5, mean_rank=1.0
- v75_register: exact=5/5, top5=5/5, mean_rank=1.0
- v77_rule_four: exact=5/5, top5=5/5, mean_rank=1.0
- v77_omega: exact=4/5, top5=5/5, mean_rank=1.6
- v76_production: exact=0/5, top5=0/5, mean_rank=18.8
- meta_logic: exact=1/5, top5=3/5, mean_rank=16.0
