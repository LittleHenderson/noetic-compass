# PARAMETER_JOBS_CTT — every parameter block of the CAS-token translator and its job

Capacity Rules v0.1: more parameters only when each has a job. Counts are exact, by formula
(`helm_cas_translator/param_count.py`), with the vocabulary of 8,349 tokens = 8 specials + 341 CAS-side tokens +
8,000 English word-pieces. The GPU host asserts torch's own count equals these numbers before training
(`model.assert_parameter_count`); a mismatch stops the run.

## A4_9p6M — 9,585,566 parameters

Shape: width 256, 4 encoder + 4 decoder layers, 4 heads, feed-forward 1024.

| Block | Parameters | Its job |
|---|---:|---|
| shared embedding, tied input/output (vocab x d) | 2,137,344 | one vector per English piece and per CAS token; CAS states are factored (^n, ^D, Fk, \|R), so the 40 states cost 14 vectors |
| output bias (vocab) | 8,349 | base rate of each output token before the context is read |
| encoder: 4 layers (self-attention + feed-forward + 2 layer norms) | 3,159,040 | read the English, the slot tags and the dialogue records |
| encoder final layer norm | 512 | scale the encoder's output |
| decoder: 4 layers (self-attention + cross-attention + feed-forward + 3 layer norms) | 4,213,760 | write the CAS record one token at a time, looking back at the sentence |
| decoder final layer norm | 512 | scale the decoder's output |
| copy (pointer) head: bilinear copy attention (d x d) | 65,536 | point at a slot tag of the user's own sentence instead of inventing a number or a name |
| copy gate (2d + 1) | 513 | decide, per output step, between writing a CAS token and pointing at a slot |
| positions | 0 | fixed sinusoids; no parameters, so no input-length table to run out of (gate H-LEN) |
| **Total** | **9,585,566** | |

## A5_2p5M — 2,482,718 parameters

Shape: width 128, 3 encoder + 3 decoder layers, 4 heads, feed-forward 512.

| Block | Parameters | Its job |
|---|---:|---|
| shared embedding, tied input/output (vocab x d) | 1,068,672 | one vector per English piece and per CAS token; CAS states are factored (^n, ^D, Fk, \|R), so the 40 states cost 14 vectors |
| output bias (vocab) | 8,349 | base rate of each output token before the context is read |
| encoder: 3 layers (self-attention + feed-forward + 2 layer norms) | 594,816 | read the English, the slot tags and the dialogue records |
| encoder final layer norm | 256 | scale the encoder's output |
| decoder: 3 layers (self-attention + cross-attention + feed-forward + 3 layer norms) | 793,728 | write the CAS record one token at a time, looking back at the sentence |
| decoder final layer norm | 256 | scale the decoder's output |
| copy (pointer) head: bilinear copy attention (d x d) | 16,384 | point at a slot tag of the user's own sentence instead of inventing a number or a name |
| copy gate (2d + 1) | 257 | decide, per output step, between writing a CAS token and pointing at a slot |
| positions | 0 | fixed sinusoids; no parameters, so no input-length table to run out of (gate H-LEN) |
| **Total** | **2,482,718** | |

## When to grow (Capacity Rules applied to a learned part)

Only if the model UNDER-fits: it misses its own training rows (`WEIGHTS_MANIFEST.json` → `train_fit_exact`). If it
fits training and fails held-out English, that is not a capacity failure, and more parameters would make it worse.
The 2.5 M twin (arm A5) is the size check. No size change is made inside this test (anti-tuning rule).

## Deviation from the design's twin shape (recorded in PREREGISTRATION_CTT.md section 16)

The design named the twin "about 2.5 M: width 192, 3 + 3 layers". With the shared 8,349-token table that shape
comes to 4,764,382 parameters, not 2.5 M (embedding 1,603,008 alone). The owner accepted the SIZE ("9.6 M with a
2.5 M twin"), so the size is kept and the width is 128 (3 + 3 layers, feed-forward 512): 2,482,718 parameters.
