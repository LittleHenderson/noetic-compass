# C60 lacunarity test — the theory measured on the real CTT-v2 language run (2026-10-23)

Status: **diagnostic only. Not claim-bearing.** Run on the laptop's RTX 4070, not on AWS, so under the standing
rule it can license nothing. It measures; it does not train. Every number below is `MEASURED` unless marked otherwise.

## 1. What was tested

The last language run before the owner lost access: **MOUTH TRAIN v2**, job `c60`, instance `i-099d373e0e5ab939f`.

| Item | Value |
|---|---|
| Deliverable | `pointer-saturation-deliverable.zip`, 125,162,203 bytes, sha256 `b1cfa3815b39669814437fba7609523e813f32e0da44f71a6dc9d4412246f54d` |
| Source | S3 `helm-primary-pointer-807562639912-20261001-v4/bridge-control-20260822/helm-pointer-saturation-20261001-v4/` (read-only: one list + three GETs; **no instance launched**) |
| Run status | `RAN`, host word `MOUTH_NO_GAIN`, all four models 6,000 steps |
| Checkpoints scored | A4-s1, A4-s2, A4-s3 (`final.pt`, 9,585,823 parameters each); `smoke/final.pt` (A5, early-state proxy) |
| Data scored | `mouth_dev.jsonl` 2,097 held-out rows; `mouth_train.jsonl` 11,530 rows |
| Method | target-token NLL under teacher forcing (no sampling, `torch.no_grad`), per row, PAD masked; gliding-box lacunarity at boxes 4/16/64 |
| Script | `test_c60_error_field.py` in this folder |

Why this run: the owner asked for the theory to be tried in the CTT-v2 language training specifically, and this is
the last such run. Its final training loss is **0.047318484634160995** — not at the floor (CTT-1 reached
`1.8003862351179123e-05`), so the regime is different and worth measuring.

## 2. Results

Held-out replies (`mouth_dev.jsonl`), teacher-forced NLL:

| Checkpoint | Rows | Mean token NLL | L(4) median | L(4) p90 | L(4) share ≤1.05 | L(16) median | L(16) share ≤1.05 |
|---|---|---|---|---|---|---|---|
| A4-s1 final | 1,200 | **1.815093** | **2.0641** | 5.5144 | 0.0125 | 1.0449 | 0.5118 |
| A4-s2 final | 800 | 1.444061 | 2.4473 | — | 0.0188 | 1.0568 | 0.4872 |
| A4-s3 final | 800 | 1.460707 | 2.4441 | — | 0.0188 | 1.0512 | 0.4968 |
| smoke (A5, early) | 800 | 5.198844 | 1.0655 | 1.1482 | 0.3726 | 1.0017 | 0.9952 |

Training rows, same checkpoint A4-s1 (300 rows): mean token NLL **0.06606**, **L(4) median 11.0194**
(p90 19.2494), **L(16) median 3.0018**, share ≤1.05 at box 4 = **0.0**.

Box 64 returned `None` on every row of every run: the replies are too short.

Reply lengths (tokens, from the payload vocabulary): dev median **19**, p90 **33**, max **60**; train median **20**,
p90 **33**, max **63**. Only 12.2% of dev rows reach 32 tokens.

## 3. What the measurement says

**3.1 The statistic is live in this regime.** On held-out rows the per-token error field is clustered at box 4
(median 2.06–2.45, where 1.0 is uniform). On training rows it is strongly clustered (median 11.02). The mouth does
not spread its error evenly across a reply; it gets most tokens right and misses particular ones.

**3.2 The design note's prediction is refuted, in the useful direction.** The note predicted the field becomes
*uniform* as training saturates. The measurement shows the opposite: the early checkpoint is high-loss and almost
perfectly uniform (L(4) 1.07), while the trained model's training rows are low-loss and strongly clustered
(L(4) 11.02). As the easy tokens saturate, the remaining error concentrates into fewer positions. That is what a
lacunarity statistic should do on a model that is still learning something, and it is the behaviour to expect in
underfit runs like this one. (Caveat: smoke and final differ in model size and training amount, so this is a
two-point comparison, not a trajectory — see 3.4.)

**3.3 The box set was wrong for this task.** Box 64 is undefined for English replies whose median length is 19
tokens. The mouth task needs boxes **{4, 8, 16}**, with 32 only on the long tail (12% of rows). The CTT-1 box set
`{4, 16, 64}` was chosen for 128-token CAS records and does not transfer.

**3.4 The trajectory cannot be read from this run.** Only `final.pt` (plus a smoke checkpoint) was saved. Whether
L rises, falls or plateaus along training is exactly the question R1 exists to answer, and this run cannot answer
it. The next run must save periodic checkpoints (every 1,000 steps is enough) or the question stays open at the
cost of another GPU job.

**3.5 The gap that dwarfs all of this is generalization.** Training rows: NLL 0.066. Held-out rows: NLL 1.44–1.82,
with the same three-seed consistency. That is a 22–28× gap on unseen phrasings, not a step-size gap. A global
learning-rate multiplier cannot close it; the per-block variant (R2) at least has a mechanism to try, because the
tone-tag and `[M]` rows are the newest and least-trained part of the embedding.

## 4. What changes in the design packet

1. **Prediction rewritten.** E1 now predicts that L(4) *rises* as training saturates on training batches (from ~1
   toward 3–11), and stays in the 2–3 band on held-out batches. A field that stays at 1.0 after training means the
   model is nowhere near saturation, not that it is done.
2. **Boxes for mouth-style work: {4, 8, 16}.** Box 64 stays only for CAS-record targets, where sequences reach 128.
3. **Checkpoint cadence becomes an experiment requirement**, not a convenience: every 1,000 steps, kept, hashed.
4. **The R4 prior stays negative for this run family.** It is now measured that the mouth run is not at the loss
   floor, so the schedule has something to act on; but the dominant gap is generalization, so the expected exam
   effect of a global multiplier is still ≈ 0. R2 is the variant worth a pilot here.

## 5. Claim status

| Statement | Status |
|---|---|
| NLL and lacunarity numbers in section 2 | `MEASURED` (this script, these checkpoints) |
| Field is clustered at box 4 and near-uniform at box 16 on held-out replies | `MEASURED` |
| Field is more clustered on training rows than on held-out rows | `MEASURED` |
| "Saturation raises clustering" as a general law | `PROPOSED` — two points, one model family |
| Any exam gain from the schedule | `NOT CLAIMED` — this test cannot produce one |
| Claim-bearing status | **NONE**: local GPU diagnostic, not an AWS run |

## 6. Reproduction

```
# artifacts (read-only; no instance launched)
aws s3 ls s3://helm-primary-pointer-807562639912-20261001-v4/bridge-control-20260822/helm-pointer-saturation-20261001-v4/
aws s3 cp <prefix>/pointer-saturation-deliverable.zip <local>/c60_deliverable.zip

# scoring (RTX 4070, ~30 s per checkpoint)
C:\Users\wakil\venvs\cas-gpu\Scripts\python.exe -X utf8 test_c60_error_field.py \
  --checkpoint <...>\runs\A4-s1\final.pt --config A4_9p6M \
  --payload <...>\HELM_MOUTH_TRAIN_V2_20261022 --rows 1200 --file mouth_dev.jsonl
```

## 7. What this does not do

- It does not retrain anything, and it does not test the schedule itself (no optimiser step was taken).
- It does not touch the frozen C60 package, the exam, the reader or the host word (`MOUTH_NO_GAIN` stands).
- It does not license a claim: the project rule is that claim-bearing neural runs happen on AWS, and this one ran
  on the laptop's GPU.
