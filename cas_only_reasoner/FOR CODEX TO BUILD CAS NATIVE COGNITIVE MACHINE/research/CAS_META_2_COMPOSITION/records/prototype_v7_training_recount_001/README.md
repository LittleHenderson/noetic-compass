# V7 saved training recount — passed; evaluation remains incomplete

The unchanged, source-bound training checker independently recounted the saved
training records and validation-only checkpoint selection. It verified checkpoint
bytes without loading tensors. This is not a successful full experiment or an
independent replay of neural arithmetic.

Job: `cas-meta2-20260906094002-39762c47`.
Frozen source: `42f9164754312f12850d9b8789c062fa7fb8069f`.
Packet SHA256: `f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799`.
Recount receipt SHA256: `452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76`.

## Actual data and training

| Partition | Total | Depth 1 | Depth 2 | Depth 3 | Depth 4 |
|---|---:|---:|---:|---:|---:|
| Training | 896 | 128 | 384 | 384 | 0 |
| Validation | 96 | 32 | 32 | 32 | 0 |
| Test | 72 | 0 | 0 | 48 | 24 |

The unchanged original 256 records were verified as the exact training-only
append to the new 640 base. All 8,837 known program exclusions remain in force
for fresh base/validation/test data. Held-out bytes did not change during the
append. The training export contains only its declared public files, not the
private test targets. All 360 comparison choices were sealed before the recorded
private-target opening; the rule choices match the public parser.

Both candidates completed 200 epochs and 11,200 optimizer steps. The saved
training-step times are CAS 1,628.876326619009 seconds and generic 240.20945939201647
seconds. Whole training-stage work recorded 2,596.375743874 seconds. These are
recorded elapsed times, not FLOPs or independent timing measurements.

Recorded environment: NVIDIA RTX PRO 4500 Blackwell Server Edition, CUDA 12.8,
PyTorch 2.11.0+cu128, Python 3.12.3. Parameter counts are CAS 183,852 and
generic 183,892, a 40-parameter difference. Both receive the same curriculum,
optimizer-step count and permitted information. Similar size and equal steps
do not imply equal elapsed time.

## Validation-selected program-and-input matches

| Validation depth | CAS initial | CAS selected, epoch 200 | Generic initial | Generic selected, epoch 180 |
|---|---:|---:|---:|---:|
| 1 | 0/32 | 26/32 | 0/32 | 26/32 |
| 2 | 0/32 | 0/32 | 0/32 | 0/32 |
| 3 | 0/32 | 0/32 | 0/32 | 0/32 |
| All | 0/96 | 26/96 | 0/96 | 26/96 |

These are freely generated exact program-plus-binding matches, not native
task outcomes. The receipt contains the full per-depth validation and training
probe curves at every measured epoch, and independently repeats the unchanged
selection rule. The generic final checkpoint is not the selected checkpoint.

The new training probe at final epoch 200 scores CAS 22/24 and generic 24/24.
It is a sample from this run's training set, not the earlier separate v5
24/24 familiar-program experiment and not unseen-task evidence.

## Saved checkpoint identities

All paths below are within the byte-authenticated extraction's
`cloud_job/campaign/training` directory. Files remain unchanged.

| Family | Kind | Epoch / steps | Filename | SHA256 |
|---|---|---|---|---|
| CAS | Initial | 0 / 0 | cas_initial_epoch_0000.pt | ad8c80bf3d3ed7111e118957066ac3f0ec0509681fa2aa00e44d1592403b43fd |
| CAS | Selected | 200 / 11200 | cas_selected_epoch_0200.pt | bf709539d8a462fe73909553659ad046305e75428a15d80e83124bc28ee84b46 |
| CAS | Final | 200 / 11200 | cas_final_epoch_0200.pt | bf709539d8a462fe73909553659ad046305e75428a15d80e83124bc28ee84b46 |
| Generic | Initial | 0 / 0 | generic_initial_epoch_0000.pt | 20669d0470a583ab172bbb06451c0b6bcbbf190ea10b3e725e7a73c5c046b051 |
| Generic | Selected | 180 / 10080 | generic_selected_epoch_0180.pt | 53e2acdd4635d843210a7aa0a5b194e395f57c0b7f71ca59b1a64dbeae4ca532 |
| Generic | Final | 200 / 11200 | generic_final_epoch_0200.pt | 6e2f330d42b93f55102243b7597624a126f12dbbbd89f6ceffd3445b53748061 |

## Recount identity and boundary

`execute.py` captured the exact command, actual child PID 69408, raw stdout and
stderr, start/end times, exit 0 and 45.4674098-second duration in `execution_001`.
The executed `run.py` SHA256 is
`3615080f9bdf88cdce295cda8e1af5715fc9ca87c48feba0a4f919663b587f2b`.
No AWS call, model import, tensor load, training, scoring change or new launch
occurred in this local audit. All 603 source files and 316 protected files were
checked against the fixed source archive and Git before and after.

The full-success reviewer was not called. The evaluation process remains
return 1 after its 2,700-second native deadline. The separately checked partial
native outcomes must retain the unfinished generic case 45 and the unstarted
rule arm rather than assigning invented outcomes. No automatic promotion follows.
