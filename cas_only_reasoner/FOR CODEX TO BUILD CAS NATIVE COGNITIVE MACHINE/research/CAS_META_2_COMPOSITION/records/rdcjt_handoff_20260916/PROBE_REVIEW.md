# Independent contrast-probe review — 2026-09-16

Reviewed `cas_meta2/graph_teaching/contrast_probe.py` and `tests/test_graph_training_contrast_probe.py` after the prompt-rendering, cache-identity, option-order, semantic-renaming, length-permutation, evaluation-mode, and parameter-identity repairs. No additional blocking implementation defect was found for the current whole-part records. This is an automated software review, not a neural result or human approval.

The 15 pure probe tests passed with `C:\Python314\python.exe -B -m pytest -p no:cacheprovider tests/test_graph_training_contrast_probe.py -q` in 0.18 seconds. Tests use fake learners; they do not load checkpoints, import torch, train, or call a provider.

## Independent tokenizer check

Used the actual pure-Python `LosslessPublicTokenizer` class from `cas_meta2/features_v2.py`. Fitted it with `LosslessPublicTokenizer.fit_train([adapter.public_records(r, 'cas')['public'] for r in trainer.training_records(20260909)], max_length=1024)`.

For each of two sets—30 records from `trainer.training_records(20260909)` and 30 records from `curriculum.varied_records()`—constructed and validated all available variants with `validate_probe_cases(build_probe_cases(records, all_record_ids, maximum=len(records)))`, using the default contrast seed `20260927`. Every non-null variant was passed through `public_probe_input(original_record, variant)` and then `tokenizer.encode_public(task['public'])`. The check measured `len(encoded['ids'])` and recorded any exception.

| Set | Original maximum | Renamed maximum | Reordered maximum | Rewired maximum | Encoding failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training, 30 records | 386 | 786 | 386 | 371 | 0 |
| Varied, 30 records | 691 | 832 | 691 | 632 | 0 |

All checked variants fit the 1024-token bound. This validates the public-input construction and tokenizer capacity for these records and seed only. It does not validate retained-checkpoint restoration, tensor execution, prediction quality, or other data/label choices.

## Interpretation limits

- Renamed labels also change tokenization. A prediction change alone does not isolate a neural reasoning mechanism.
- Rewiring changes the candidate options as well as the graph. It is not an intervention holding the entire answer interface constant.
- The list-length probe reports option-order sensitivity and chosen lengths. It does not prove that length caused a semantic error.
- Real parameter preservation remains unmeasured until the retained checkpoint is restored and the probe runs on the authorized GPU path. Fake-learner tests are software evidence only.

The structural-supply audit contained pre-fix findings during this review. A separate agent is updating its historical labeling; this review does not certify that later document change.
