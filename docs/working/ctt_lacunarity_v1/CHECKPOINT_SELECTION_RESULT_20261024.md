# Checkpoint-selection result — 3 seeds, dev-selected, held-out half (2026-10-24)

Status: **diagnostic, not claim-bearing** (local scoring of an authorised AWS training run). Numbers `REAL`.
Preregistration: `PREREGISTRATION_CHECKPOINT_SELECTION_20261023.md`, amended by
`PREREGISTRATION_CHECKPOINT_SELECTION_ADDENDUM_20261024.md` (the sealed exam has no gold text, so a fixed
even/odd split of dev replaced it; the addendum was written before any split result was computed).

## 1. What ran

Three seeds, model A4, the frozen mouth training for 6,000 steps on one g5.xlarge, order seed `3855894630296892324`
(the c60 order). Checkpoints at 1,000, 2,000, 3,000, 4,000, 5,000 and 6,000. All three finished with exit 0:

| Seed | Steps | Seconds | `final.pt` sha256 |
|---|---|---|---|
| A4-s1 | 6,000 | 1,257.1 | `ee5163d6fcac5896d2a02107a66c4825df913768fddaf1e45d2053bfc2fe7fab` |
| A4-s2 | 6,000 | 1,221.1 | `32f0b7001b1cfa9731b456c3bc5559287f0386c3087241044f57255bf7efaece` |
| A4-s3 | 6,000 | 1,222.3 | `bd7bebe8b23e6d901e90bd942eb53cc307318e1fb17ba45ffe47df49cce25555` |

Selection set: even rows of `mouth_dev.jsonl` (1,049). Report set: odd rows (1,048). No row is in both.

## 2. Selection (even half, 1,049 rows, mean token NLL)

| Checkpoint | A4-s1 | A4-s2 | A4-s3 |
|---|---|---|---|
| step 1,000 | **1.125884** | **1.035182** | **1.034138** |
| step 2,000 | 1.275916 | 1.190588 | 1.170136 |
| step 3,000 | 1.428419 | 1.326103 | 1.321158 |
| step 4,000 | 1.530410 | 1.442286 | 1.436232 |
| step 5,000 | 1.577702 | 1.492245 | 1.473372 |
| final (6,000) | 1.593455 | 1.506173 | 1.485200 |

All three seeds select **step 1,000**. There is no seed where any later checkpoint is better.

## 3. Report (odd half, 1,048 rows) and the decision

| Seed | FINAL | SELECTED (step 1,000) | Delta (selected − final) | Paired 95% CI | Median paired delta |
|---|---|---|---|---|---|
| A4-s1 | 1.603289 | **1.111825** | **−0.491463** | [0.448315, 0.535091] | 0.265747 |
| A4-s2 | 1.469737 | **1.018073** | **−0.451663** | [0.413322, 0.491463] | 0.265255 |
| A4-s3 | 1.466799 | **1.009736** | **−0.457062** | [0.417672, 0.497106] | 0.267639 |

(CI and median are for the paired difference final − selected, so positive means the final checkpoint is worse.)

Preregistered rule: selected must beat final by at least 0.05 NLL in at least 2 of 3 seeds.

**Decision: SELECTION HELPS — 3 of 3 seeds pass, each by about 0.45–0.49 NLL, roughly nine to ten times the
threshold.** The oracle check agrees: the best of the six checkpoints on the report half is step 1,000 for all three
seeds, so nothing later recovers.

## 4. What this means, and what it does not

**It means** the frozen "train 6,000 steps and score the final checkpoint" rule returns the worst of the six
checkpoints on this held-out distribution, in every seed, by a wide margin. Stopping at 1,000 steps would have used
**about one sixth of the training compute** and produced the better model on this measure.

**It does not mean** the mouth's real exam improves. NLL on held-out replies is not the mouth's exam: that exam scores
*generated* replies through a guard, a round-trip check and AI raters. A model that is better in likelihood may still
be worse in generation, or the early model may be more repetitive. The honest next test is to generate replies from
the 1,000-step and 6,000-step checkpoints on the real exam material and score them with the frozen mouth rules.

**It also does not generalise yet.** The report half is the same dev distribution as the selection half, not a sealed
exam from a different frame. The result is strong on this distribution and silent about others.

## 5. Claim status

| Statement | Status |
|---|---|
| Step 1,000 beats final on the held-out half in all three seeds: −0.491463, −0.451663, −0.457062 | `REAL` |
| The preregistered decision rule passes 3 of 3 | `REAL` |
| The final-checkpoint rule is the wrong rule for this run family | `PROPOSED` — holds on this distribution; needs the generation-level exam to license |
| Early stopping would cut compute to about 1/6 | `REAL` arithmetic for this run |
| Any improvement on the mouth's real exam or on CTT-1's ears | `NOT CLAIMED` |
| Claim-bearing status | **NONE** — local scoring, not an AWS claim run |

## 6. Cost

Run 2 on AWS: about **1.2 USD** (three seeds, ~61 minutes of g5.xlarge plus boot and upload). Total for both
checkpoint runs: about **2.4 USD**, as the owner approved. Scoring was local and free.
