# V7 training learning curves — action selection only

Training finished, but the full experiment did not. These scores measure whether the freely generated program and input binding both exactly match the checked target. They are not native task correctness scores, proof of CAS advantage, or a neural rerun.

The source receipt recounts saved validation/probe actions and replays the existing validation-only checkpoint selection. Checkpoint bytes were already checked there; this report only reads that pinned JSON receipt.

## Data and test limits

<!-- table:dataset -->
| Split | Tasks | Depth 1 | Depth 2 | Depth 3 | Depth 4 |
| --- | --- | --- | --- | --- | --- |
| train | 896 | 128 | 384 | 384 | 0 |
| validation | 96 | 32 | 32 | 32 | 0 |
| test | 72 | 0 | 0 | 48 | 24 |
<!-- endtable:dataset -->

The training split includes the exact original 256 records, used only for training. Validation has 32 examples at each measured depth. The training probe has 8 examples per depth and is part of development, not a test result.

The separate test combines fresh instances with unseen program combinations. It does not isolate those two changes into separate experiments. Its 72 variants are 24 related triplets, not 72 independent program structures. There is no depth-2 test group; depth-2 validation is present. No test or native outcome score is included in this report, and no task graphs were recomputed.

## Before, selected, and final

Initial means before training. Selected means the final validation-selected checkpoint. Final means the last training epoch; it need not be the selected checkpoint. Ratios below are exact counts, not rounded percentages.

<!-- table:snapshot -->
| Family | Stage | Epoch | Val d1 | Val d2 | Val d3 | Probe d1 | Probe d2 | Probe d3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cas | initial | 0 | 0/32 | 0/32 | 0/32 | 0/8 | 0/8 | 0/8 |
| cas | selected | 200 | 26/32 | 0/32 | 0/32 | 8/8 | 6/8 | 8/8 |
| cas | final | 200 | 26/32 | 0/32 | 0/32 | 8/8 | 6/8 | 8/8 |
| generic | initial | 0 | 0/32 | 0/32 | 0/32 | 0/8 | 0/8 | 0/8 |
| generic | selected | 180 | 26/32 | 0/32 | 0/32 | 8/8 | 8/8 | 8/8 |
| generic | final | 200 | 22/32 | 0/32 | 0/32 | 8/8 | 8/8 | 8/8 |
<!-- endtable:snapshot -->

<!-- table:checkpoints -->
| Family | Stage | Epoch | Optimizer steps | Bytes | Recorded filename | SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| cas | initial | 0 | 0 | 1117577 | cas_initial_epoch_0000.pt | ad8c80bf3d3ed7111e118957066ac3f0ec0509681fa2aa00e44d1592403b43fd |
| cas | selected | 200 | 11200 | 2666977 | cas_selected_epoch_0200.pt | bf709539d8a462fe73909553659ad046305e75428a15d80e83124bc28ee84b46 |
| cas | final | 200 | 11200 | 2666977 | cas_final_epoch_0200.pt | bf709539d8a462fe73909553659ad046305e75428a15d80e83124bc28ee84b46 |
| generic | initial | 0 | 0 | 1104425 | generic_initial_epoch_0000.pt | 20669d0470a583ab172bbb06451c0b6bcbbf190ea10b3e725e7a73c5c046b051 |
| generic | selected | 180 | 10080 | 2626593 | generic_selected_epoch_0180.pt | 53e2acdd4635d843210a7aa0a5b194e395f57c0b7f71ca59b1a64dbeae4ca532 |
| generic | final | 200 | 11200 | 2626593 | generic_final_epoch_0200.pt | 6e2f330d42b93f55102243b7597624a126f12dbbbd89f6ceffd3445b53748061 |
<!-- endtable:checkpoints -->

The checkpoint CSV also preserves the exact recorded remote file addresses. Those are historical AWS paths, not claims that the terminated worker is still available.

## Every measured depth curve

All 22 measured epochs per family are shown: epoch 0, epoch 1, and every tenth epoch through 200. The receipt has no generation measurement for intervening epochs; none was filled in. “Selected then” preserves the recorded best-so-far flag. “Final choice” marks only the checkpoint retained after the complete training run. Every validation ratio uses 32 cases; every probe ratio uses 8.

### Depth 1

<!-- table:depth_1 -->
| Epoch | CAS validation | CAS probe | CAS selected then | CAS final choice | Generic validation | Generic probe | Generic selected then | Generic final choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0/32 | 0/8 | false | false | 0/32 | 0/8 | false | false |
| 1 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 10 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 20 | 6/32 | 2/8 | true | false | 6/32 | 3/8 | true | false |
| 30 | 11/32 | 5/8 | true | false | 14/32 | 6/8 | true | false |
| 40 | 16/32 | 7/8 | true | false | 18/32 | 8/8 | true | false |
| 50 | 20/32 | 8/8 | true | false | 14/32 | 6/8 | false | false |
| 60 | 18/32 | 8/8 | false | false | 13/32 | 7/8 | false | false |
| 70 | 14/32 | 8/8 | false | false | 19/32 | 8/8 | true | false |
| 80 | 17/32 | 8/8 | false | false | 12/32 | 6/8 | false | false |
| 90 | 22/32 | 8/8 | true | false | 13/32 | 7/8 | false | false |
| 100 | 13/32 | 6/8 | false | false | 15/32 | 7/8 | false | false |
| 110 | 22/32 | 8/8 | true | false | 20/32 | 8/8 | true | false |
| 120 | 19/32 | 8/8 | false | false | 24/32 | 8/8 | true | false |
| 130 | 23/32 | 8/8 | true | false | 22/32 | 8/8 | false | false |
| 140 | 22/32 | 8/8 | false | false | 19/32 | 8/8 | false | false |
| 150 | 21/32 | 8/8 | false | false | 23/32 | 8/8 | false | false |
| 160 | 25/32 | 8/8 | true | false | 22/32 | 8/8 | false | false |
| 170 | 18/32 | 7/8 | false | false | 25/32 | 8/8 | true | false |
| 180 | 25/32 | 8/8 | true | false | 26/32 | 8/8 | true | true |
| 190 | 25/32 | 8/8 | false | false | 24/32 | 8/8 | false | false |
| 200 | 26/32 | 8/8 | true | true | 22/32 | 8/8 | false | false |
<!-- endtable:depth_1 -->

### Depth 2

<!-- table:depth_2 -->
| Epoch | CAS validation | CAS probe | CAS selected then | CAS final choice | Generic validation | Generic probe | Generic selected then | Generic final choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0/32 | 0/8 | false | false | 0/32 | 0/8 | false | false |
| 1 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 10 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 20 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 30 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 40 | 0/32 | 1/8 | true | false | 0/32 | 1/8 | true | false |
| 50 | 0/32 | 3/8 | true | false | 0/32 | 3/8 | false | false |
| 60 | 0/32 | 3/8 | false | false | 0/32 | 2/8 | false | false |
| 70 | 0/32 | 4/8 | false | false | 0/32 | 2/8 | true | false |
| 80 | 0/32 | 3/8 | false | false | 0/32 | 3/8 | false | false |
| 90 | 0/32 | 7/8 | true | false | 0/32 | 4/8 | false | false |
| 100 | 0/32 | 6/8 | false | false | 0/32 | 6/8 | false | false |
| 110 | 0/32 | 8/8 | true | false | 0/32 | 8/8 | true | false |
| 120 | 0/32 | 6/8 | false | false | 0/32 | 6/8 | true | false |
| 130 | 0/32 | 8/8 | true | false | 0/32 | 6/8 | false | false |
| 140 | 0/32 | 8/8 | false | false | 0/32 | 6/8 | false | false |
| 150 | 0/32 | 4/8 | false | false | 0/32 | 8/8 | false | false |
| 160 | 0/32 | 8/8 | true | false | 0/32 | 7/8 | false | false |
| 170 | 0/32 | 2/8 | false | false | 0/32 | 8/8 | true | false |
| 180 | 0/32 | 8/8 | true | false | 0/32 | 8/8 | true | true |
| 190 | 0/32 | 8/8 | false | false | 0/32 | 6/8 | false | false |
| 200 | 0/32 | 6/8 | true | true | 0/32 | 8/8 | false | false |
<!-- endtable:depth_2 -->

### Depth 3

<!-- table:depth_3 -->
| Epoch | CAS validation | CAS probe | CAS selected then | CAS final choice | Generic validation | Generic probe | Generic selected then | Generic final choice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0/32 | 0/8 | false | false | 0/32 | 0/8 | false | false |
| 1 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 10 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 20 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 30 | 0/32 | 0/8 | true | false | 0/32 | 0/8 | true | false |
| 40 | 0/32 | 1/8 | true | false | 0/32 | 2/8 | true | false |
| 50 | 0/32 | 3/8 | true | false | 0/32 | 4/8 | false | false |
| 60 | 0/32 | 0/8 | false | false | 0/32 | 5/8 | false | false |
| 70 | 0/32 | 5/8 | false | false | 0/32 | 3/8 | true | false |
| 80 | 0/32 | 5/8 | false | false | 0/32 | 6/8 | false | false |
| 90 | 0/32 | 7/8 | true | false | 0/32 | 5/8 | false | false |
| 100 | 0/32 | 3/8 | false | false | 0/32 | 5/8 | false | false |
| 110 | 0/32 | 7/8 | true | false | 0/32 | 7/8 | true | false |
| 120 | 0/32 | 8/8 | false | false | 0/32 | 6/8 | true | false |
| 130 | 0/32 | 7/8 | true | false | 0/32 | 7/8 | false | false |
| 140 | 0/32 | 7/8 | false | false | 0/32 | 8/8 | false | false |
| 150 | 0/32 | 3/8 | false | false | 0/32 | 8/8 | false | false |
| 160 | 0/32 | 8/8 | true | false | 0/32 | 8/8 | false | false |
| 170 | 0/32 | 5/8 | false | false | 0/32 | 8/8 | true | false |
| 180 | 0/32 | 8/8 | true | false | 0/32 | 8/8 | true | true |
| 190 | 0/32 | 8/8 | false | false | 0/32 | 8/8 | false | false |
| 200 | 0/32 | 8/8 | true | true | 0/32 | 8/8 | false | false |
<!-- endtable:depth_3 -->

## Evidence boundary and source

> Saved actions and validation selection independently recounted; checkpoint bytes checked but no tensors loaded. No complete-task score or independent neural arithmetic claim.

> Recorded validation/probe actions recounted and selection replayed; checkpoint bytes bound. Not independent neural/logit/gradient replay or native task correctness.

Training-recount receipt SHA-256: `452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76`.

Source commit: `42f9164754312f12850d9b8789c062fa7fb8069f`. Source archive: `f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9`.

Collected packet: `f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799`. Job: `cas-meta2-20260906094002-39762c47`.

The CSV retains joint correctness plus its separate program, binding, and valid-program counts. A valid program alone is not a correct program or a correct task answer.
