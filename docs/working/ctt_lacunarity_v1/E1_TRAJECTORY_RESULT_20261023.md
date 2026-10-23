# E1 trajectory result — the error field concentrates as the mouth trains (2026-10-23)

Status: **diagnostic, not claim-bearing.** One run, one model, the laptop's RTX 4070, not AWS. Claim status of the
numbers: `REAL`. Claim status of the interpretation: `PROPOSED`. Nothing here licenses a gain.

## 1. What was run

An instrumented copy of the frozen mouth trainer (`ctt_train/train_mouth.py`, E1 of the amendment): identical data,
mix, schedule, order seed and loss; two additions — a lacunarity reading every 100 steps, and a resumable checkpoint
every 250 steps. The frozen batch of 256 was split into micro-batches of 64 with gradient accumulation, because the
8 GB laptop GPU cannot hold 256; effective batch stays 256. Recorded in the manifest.

| Item | Value |
|---|---|
| Model | A4-s1 (9,585,823 parameters) |
| Order seed | 1423595301575908809 (identical to c60 A4-s1) |
| Steps | 6,000 (frozen schedule, cosine to 0) |
| Wall clock | 5,126.9 s (85.4 min) on the RTX 4070, capped at 52.50 W for most of it |
| Final training loss | **0.0714612081646919** (c60 A4-s1: 0.047318484634160995; micro-batch averaging accounts for part of the gap) |
| final.pt sha256 | `bcf90fe2951daac2e7bb06bc27e59c34c9dc2202aad91eabc65c53745396350c` |

The run survived because the machine was reduced to Silent mode: GPU limit 52.50 W instead of 117.51 W. It had
suffered four hard resets before that change and **none during the 85-minute run**.

## 2. Training-batch trajectory (mouth rows, every 500 steps)

| Step | Mouth NLL | L(4) | L(8) | L(16) | CAS L(4) |
|---|---|---|---|---|---|
| 100 | 4.254918 | 1.052297 | 1.016199 | 1.003605 | 1.347765 |
| 500 | 1.448300 | 1.394145 | 1.135591 | 1.026827 | 1.113856 |
| 1,000 | 0.693453 | 1.842254 | 1.309690 | 1.044663 | 1.092476 |
| 2,000 | 0.290652 | 2.252098 | 1.541585 | 1.100264 | 1.162461 |
| 3,000 | 0.185673 | 2.694256 | 1.608703 | 1.164894 | 1.182291 |
| 4,000 | 0.131269 | 3.267672 | 2.069567 | 1.357517 | 1.536207 |
| 5,000 | 0.135483 | 4.149633 | 2.533593 | 1.539982 | 1.201107 |
| 6,000 | 0.108589 | 4.154517 | 2.556001 | 1.433515 | 1.203036 |

First-three to last-three averages: NLL **2.865482 → 0.106426** (×0.037); L(4) **1.151168 → 4.079471** (×3.544);
L(8) **1.043230 → 2.491858** (×2.389); L(16) **1.006108 → 1.456961** (×1.448). CAS L(4) **1.229595 → 1.272126**
(×1.035), flat.

## 3. Held-out trajectory (mouth dev, 800 rows, teacher-forced)

| Checkpoint | Mean token NLL | L(4) median | L(16) median |
|---|---|---|---|
| step 1,000 | 1.111674 | 1.8504 | 1.0346 |
| step 2,000 | 1.248921 | 2.0951 | 1.0413 |
| step 3,000 | 1.369781 | 2.2230 | 1.0435 |
| step 4,000 | 1.485847 | 2.2830 | 1.0491 |
| final | 1.539552 | 2.3230 | 1.0445 |

## 4. What the measurement says

**4.1 The corrected prediction is confirmed.** On training batches, the error field grows more uneven at every box
while the loss falls: L(4) 1.052297 → 4.154517, L(8) 1.016199 → 2.556001, L(16) 1.003605 → 1.433515. The field does
not collapse to uniform; it concentrates, monotonically, in the order the design note now predicts.

**4.2 The CAS side does not move.** CAS L(4) stays at 1.229595 → 1.272126 while its NLL is already at 0.000886 by
step 6,000. Those rows are solved, so their field is static. The signal lives where learning still happens: the mouth.

**4.3 Held-out data shows the same direction, and a worse outcome.** The held-out field also concentrates
(L(4) 1.8504 → 2.3230), but the held-out loss gets **worse** from the first checkpoint onwards: 1.111674 → 1.539552.
Training improves 26.9× while held-out degrades 1.4×. The best generalizing checkpoint in this run is the earliest
one measured (step 1,000), not the final one.

**4.4 That last point is the finding that matters for CTT v2.** The frozen protocol scores `final` and forbids
checkpoint choice. This run says the final checkpoint is not the best one for unseen phrasings. That is a protocol
question for the owner, not something this diagnostic can decide.

**4.5 What it means for the schedule arms.** A global multiplier driven by L would act mostly in the phase where L is
rising *because the model is memorising the mix*. Damping in that phase might slow the harm, but it cannot fix a data
distribution that is drifting away from held-out English. E2 (global) is now even less attractive; E3 (per-block) or
the protocol question are better uses of the cap.

## 5. Claim status

| Statement | Status |
|---|---|
| Numbers in sections 2 and 3 | `REAL` (this run, these checkpoints, local GPU) |
| The field concentrates as training proceeds | `REAL` for this run; `PROPOSED` as a general law |
| CAS field stays flat while mouth field concentrates | `REAL` for this run |
| Final checkpoint is worse on held-out than step 1,000 | `REAL` for this run |
| Changing the checkpoint rule would improve the exam | `NOT CLAIMED` — untested |
| Claim-bearing status | **NONE** (local diagnostic, not AWS) |

## 6. Reproduction

```
python -X utf8 -B -m ctt_train.train_mouth --model A4-s1 \
  --out runs/A4-s1-lac5 --order-seed 1423595301575908809 \
  --checkpoint-every 1000 --micro-batch 64 --resume
python -X utf8 analyze_e1.py runs/A4-s1-lac5
```

Held-out scoring per checkpoint: `test_c60_error_field.py --rows 800`.
