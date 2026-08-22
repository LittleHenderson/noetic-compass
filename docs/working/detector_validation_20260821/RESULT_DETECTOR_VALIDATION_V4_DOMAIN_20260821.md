# RESULT v4 — Domain-4 probe on real activations — the d=4 granularity rung — 2026-08-21

**The deep-dive's #1 action, executed. First rung of the 40/10/4 granularity ladder that T4 (Fisher-information interlacing) needs.** Same attested engine, real `pythia-160m`, local CPU, `$0`, no pod. Raw: `detector_validation_v4_domain_results.json` (sha256 `25b060f7…`). Script: `detector_validation_v4_domain.py`.

## What ran

A **4-way** nearest-centroid classifier over the canonical CAS **Domains** — P Principled (ought/values), C Cognitive (fact/reason), E Evaluative (judgment), O Operational (procedure). 8 content topics × 4 Domains = **32 real forward passes**; parallel framings of the same subject per topic. Train on **6** topics, test on **2 unseen** topics (cross-topic). Chance = **0.25**.

## Result — the Domain axis is linearly decodable and generalizes

**Verdict: `DOMAIN4_DECODABLE_CROSS_TOPIC`.** At the best layer, held-out 4-way accuracy is **1.000** vs 0.25 chance; the label-shuffle control sits at exact chance.

| layer | real (4-way) | label-shuffle | random-subspace |
|---:|---:|---:|---:|
| 0 | 0.750 | 0.250 | 0.250 |
| 2 | **1.000** | 0.250 | 0.250 |
| 4 | 1.000 | 0.250 | 0.000 |
| 6 | 1.000 | 0.250 | 0.500 |
| 7 | 1.000 | 0.250 | 0.250 |
| 10 | 1.000 | 0.250 | 0.250 |

**Predictions (all held):** P1 acc ≥ 0.50 (got 1.000); P2 beats random subspace by ≥ 0.15 (1.000 vs 0.250); P3 shuffle ≤ 0.45 (0.250, exact chance).

**The label-shuffle control is 0.250 — exact 4-way chance — at almost every layer.** Destroy the labels and the classifier reads nothing. That is the load-bearing null.

## Honest caveats — recorded, not buried

1. **The random-subspace control is noisy** (0.0–0.875 across layers) because the held-out set is small (8 items); at layer 9 a random 4-dim subspace happens to hit 0.875. So — as in every prior run — the **shuffle** (clean 0.250) is the informative null, not the random subspace. The best layer (2) has the random subspace at chance, so its gap is clean.
2. **Framing-cue confound.** The Domain framings carry lexical signatures (*ought/should* → P; *first…then* → O; superlatives → E; plain declaratives → C). Cross-topic controls for content but not for these framing markers, so part of the signal is Domain **framing**, not a deeper domain representation. A framing-matched control would separate them. Same honesty note as the `^8`/`^9` axis.
3. `n=8` held-out, 4-way, one tiny model — research-grade, not a significance claim, not a customer ACCEPT.

## Why this matters — it starts the ladder T4 needs

The deep-dive concluded T4 (the falsifiable interlacing screen) is blocked because the harness had only **one effective granularity** (two 2-way axes). This adds the **d=4 Domain rung** as a real, validated granularity. With the Operator-10 (d=10) rung still to build, the ladder needed to compute Fisher-information interlacing between granularities is now **one rung of three** in place — measured on real weights, not asserted.

## Claim states

- **Real:** 32 forward passes on real weights through the attested engine; the 4-way classifier; both controls; every number.
- **Accepted:** none — research-grade.
- **Open:** the framing-cue confound; the Operator-10 rung (needed to complete the ladder); the d=40 Element rung; larger sets for significance.
- **Not licensed:** any product sentence citing these numbers.

**No pod. No GPU. `$0`.** Three CAS levels now validated on real activations: `^2`/`^3`, `^8`/`^9`, and the 4-Domain axis.
