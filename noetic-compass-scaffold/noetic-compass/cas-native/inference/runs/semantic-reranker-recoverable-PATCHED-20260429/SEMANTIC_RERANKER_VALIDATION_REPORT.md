# Semantic Reranker Validation

## Headline

- Exact top-1: 21 / 30 (70.0%)
- Ground truth top-1: 21 / 30
- Ground truth top-5: 26 / 30
- Mean ground-truth rank: 2.888888888888889
- Compiler-valid outputs: 30 / 30

## Interpretation

The semantic reranker improved exact candidate selection under the current evaluation.

## Training

- Train pairs: 47056
- Eligible records: 11764
- Epochs: 10
- Batch size: 512
- Wall clock seconds: 2841.0

## Epoch Metrics

- epoch 1: loss=0.4185, pairwise_accuracy=0.749
- epoch 2: loss=0.3078, pairwise_accuracy=0.817
- epoch 3: loss=0.2672, pairwise_accuracy=0.848
- epoch 4: loss=0.2321, pairwise_accuracy=0.871
- epoch 5: loss=0.2008, pairwise_accuracy=0.890
- epoch 6: loss=0.1766, pairwise_accuracy=0.900
- epoch 7: loss=0.1623, pairwise_accuracy=0.906
- epoch 8: loss=0.1512, pairwise_accuracy=0.912
- epoch 9: loss=0.1445, pairwise_accuracy=0.913
- epoch 10: loss=0.1367, pairwise_accuracy=0.917

## By Bucket

- v74_baseline: exact=4/5, top5=4/5, mean_rank=1.0
- v75_register: exact=5/5, top5=5/5, mean_rank=1.0
- v77_rule_four: exact=5/5, top5=5/5, mean_rank=1.0
- v77_omega: exact=3/5, top5=5/5, mean_rank=1.6
- v76_production: exact=2/5, top5=5/5, mean_rank=1.8
- meta_logic: exact=2/5, top5=2/5, mean_rank=15.666666666666666
