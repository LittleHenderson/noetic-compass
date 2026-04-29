# Semantic Reranker Validation

## Headline

- Exact top-1: 2 / 30 (6.7%)
- Ground truth top-1: 2 / 30
- Ground truth top-5: 2 / 30
- Mean ground-truth rank: 363.8076923076923
- Compiler-valid outputs: 30 / 30

## Interpretation

This run falsifies the lightweight semantic-reranker hypothesis for the current Level 2 prompt corpus. The model learned a weak preference signal (pairwise accuracy rose from 0.552 to 0.657), but exact target recovery stayed low because most held-out prompts do not expose the Noetic/Domain/Drive/Register slots needed to identify the hidden target expression.

Meta-logic performs best (2/5 exact; mean rank 15.2) because those prompts contain explicit structural language such as product, cluster, containment, or set operation. The v7.4-v7.7 buckets are mostly underdetermined natural-language scenarios, e.g. "a doctor facing an unfamiliar diagnosis" can plausibly map to many compiler-valid states. A scorer cannot recover an exact target that the prompt does not specify.

Engineering implication: the next move is not more reranker epochs. The data generator needs a recoverable prompt layer that verbalizes the CAS slots in natural language, or evaluation should treat multiple semantically valid candidates as acceptable rather than one hidden exact string.

## Training

- Train pairs: 33244
- Eligible records: 8311
- Epochs: 8
- Batch size: 512
- Wall clock seconds: 360.6

## Epoch Metrics

- epoch 1: loss=0.6641, pairwise_accuracy=0.552
- epoch 2: loss=0.5970, pairwise_accuracy=0.606
- epoch 3: loss=0.5860, pairwise_accuracy=0.617
- epoch 4: loss=0.5782, pairwise_accuracy=0.630
- epoch 5: loss=0.5719, pairwise_accuracy=0.636
- epoch 6: loss=0.5644, pairwise_accuracy=0.646
- epoch 7: loss=0.5573, pairwise_accuracy=0.653
- epoch 8: loss=0.5525, pairwise_accuracy=0.657

## By Bucket

- v74_baseline: exact=0/5, top5=0/5, mean_rank=616.75
- v75_register: exact=0/5, top5=0/5, mean_rank=668.8
- v77_rule_four: exact=0/5, top5=0/5, mean_rank=458.25
- v77_omega: exact=0/5, top5=0/5, mean_rank=91.0
- v76_production: exact=0/5, top5=0/5, mean_rank=428.0
- meta_logic: exact=2/5, top5=2/5, mean_rank=15.2
