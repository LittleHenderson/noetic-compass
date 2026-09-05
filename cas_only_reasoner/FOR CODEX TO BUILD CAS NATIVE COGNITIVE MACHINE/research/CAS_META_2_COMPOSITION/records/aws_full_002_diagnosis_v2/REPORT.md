# Saved-run data diagnosis

The tokenizer loses test information. This alone is not a proven sufficient cause of failure.

| Split | Examples | Unknown / encoded token rows | Share |
|---|---:|---:|---:|
| train | 256 | 0 / 38870 | 0.00% |
| validation | 48 | 2043 / 6603 | 30.94% |
| test | 72 | 6982 / 15926 | 43.84% |

Unknown structural names affect 25 test cases; 22 contain at least two names mapped to the same unknown marker.
Test requires 109 calls inside child procedures, across 36 cases. Training has 0.
Test requires 154 output-token occurrences never present as positive training targets.

- cas_trained: 30 decoded programs; 0 exact target programs; depths {'2': 30}; 0 child calls.
- generic_trained: 35 decoded programs; 0 exact target programs; depths {'2': 35}; 0 child calls.

Frozen parser explicitly recognizes all three wording families; neural vocabulary is fitted only on family 0.

Equal complete pre-tensor feature-data groups: {"test": [], "train": [], "validation": []}. This does not prove distinct neural tensors.

Frozen source: `b5f1718e63a2b5cf72b4b606d513d0524b9226ac`. Inspected diagnostic inputs were unchanged before/after.

Post-evaluation diagnosis, not held-out tuning. Counts establish information loss and distribution shifts; they do not establish that any one change is sufficient to fix task accuracy. Pre-tensor JSON feature uniqueness does not guarantee distinct downstream neural tensors. No checkpoint/model/tensor execution, native execution, restart experiment, or stored-native semantic audit is performed.
