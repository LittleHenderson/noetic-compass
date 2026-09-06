# Preserved learning measurements and structural coverage

This is analysis of old metadata, not a new model evaluation. The original
training run's audit packet was incomplete. No checkpoint was loaded or changed.
The script checks the pinned input archive and all five reconstructed dataset
hashes, then recomputes depth/procedure counts with the frozen IR validator.

Selected CAS epoch 60 had 97.6758% teacher-forced token accuracy but only 43/96
freely generated program-and-binding matches on development tasks:

| Recorded call depth | CAS joint matches | Generic joint matches |
| --- | ---: | ---: |
| 1 | 31/32 | 32/32 |
| 2 | 8/32 | 18/32 |
| 3 | 4/32 | 19/32 |

These matches did not execute native task outcomes. They are not proof of
correct answers, general reasoning or CAS advantage. Generic used 183,892
parameters and CAS 183,852; both completed 11,520 optimizer steps. These facts
alone do not establish that either architecture was optimally trained.

The data coverage is also relevant:

- Training: 3,072 tasks, equally split across depths 1, 2 and 3; 1,099 use four procedures.
- Development: 96 tasks, equally split across those depths; 32 use four procedures,
  and only 14 combine depth three with four procedures.
- Already-exposed test: 72 tasks, all four procedures; 48 at depth three and
  24 at depth four. These are 24 matched triplets, not 72 independent graphs.

The evidence supports targeting complete nested-program generation and measuring
structural difficulty explicitly. It does not prove that this coverage difference,
the decoder, the loss, or model capacity caused the failures.

Next decision: use the unchanged-checkpoint decoder comparison to separate
decoding effects from the remaining learned-program weakness. For a subsequent
fresh learning run, include adequate four-procedure/depth-three development
coverage and report an explicitly separate deeper-call generalization test.
Do not quietly train on the old test set, relabel exposed examples as fresh,
or claim a deeper-generalization test remained unseen after using it for tuning.
The accepted executor, evaluator and baseline weights stay unchanged.
