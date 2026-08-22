# RESULT v5 — Operator-10 probe on real activations — the d=10 middle rung — 2026-08-21

**The generative roadmap's keystone build, executed. Partially completes the 40/10/4 granularity ladder that T4 (Fisher-information interlacing) needs.** Real `pythia-160m` through the attested engine, CPU, `$0`, no pod. Raw: `detector_validation_v5_operator10_results.json` (sha256 `48fe6766…`). Script: `detector_validation_v5_operator10.py`.

## What ran

A **10-way** nearest-centroid classifier over the canonical CAS Noetic operators `^0`..`^9`, stimuli anchored to the canonical colloquialism map (CLAUDE.md). 6 exemplars per operator = **60 real forward passes**; stratified 4-train / 2-test per operator; chance = **0.10**.

## Result — 7 of 10 operators linearly decodable (a real PARTIAL)

**Verdict: `OPERATOR10_PARTIAL_DECODABLE`.** Best layer 3: macro-accuracy **`0.550`** (vs 0.10 chance); label-shuffle control **`0.050`** (below 10-way chance) — clean null.

**Per-operator accuracy at the best layer (2 held-out each):**

| operator | acc | | operator | acc |
|---|---:|---|---|---:|
| `^0` Idea | **1.00** | | `^5` Female | 0.50 |
| `^1` Mind | **1.00** | | `^6` Male | **1.00** |
| `^2` Positive | 0.50 | | `^7` Rhythm | **0.00** |
| `^3` Negative | **0.00** | | `^8` Above/Cause | **0.00** |
| `^4` Vibration | 0.50 | | `^9` Below/Effect | **1.00** |

**Separated (≥0.5): 7/10** — `^0, ^1, ^2, ^4, ^5, ^6, ^9`.

## The load-bearing negative — 3 operators did NOT separate, with an interpretable confusion structure

- **`^8` Above/Cause → `^0` Idea (2/2).** The associative trigger ("that reminds me", "triggered a memory") collapses into the bare-concept operator. Both "evoke a concept to mind" — a defensible confusion, not random.
- **`^7` Rhythm → `^1` Mind, `^2` Positive.** Habit/conditioning scatters into awareness and attraction.
- **`^3` Negative → `^1` Mind, `^4` Vibration.** Aversion scatters into the awareness substrate and impression.

`^1` Mind (awareness) acts as a natural attractor for ambiguous items — expected, since Mind is the processing substrate the definitions build on. Note `^2`/`^3` and `^8`/`^9` each separate *perfectly as 2-way axes* (v1–v3), but in the harder 10-way field `^3` and `^8` lose their held-out items to neighbors — the 2-way signal is real but not strong enough to win a 10-way vote at n=2.

## Honest caveats — recorded, not buried

1. `n=2` held-out per operator (20 items, 10-way) — research-grade, not significance.
2. **Framing-cue confound (now the priority follow-up).** The operator stimuli carry lexical signatures ("break it down" → `^6`, "practice makes perfect" → `^7`). Part of the separation is operator **framing**, not a deep operator representation. The roadmap's BUILD-NOW item #3 (framing-matched controls) is the exact next step to separate framing from structure.
3. One tiny model; self-duals were predicted to under-separate — mixed (`^0`/`^1`/`^4` separated, `^7` did not).

## Why this matters — the ladder is now 2-of-3 rungs

The granularity ladder T4 needs, measured on real weights:
- **d=4 Domain rung** — validated (v4, perfect cross-topic).
- **d=10 Operator rung** — **PARTIAL (7/10 operators), built here.**
- **d=40 Element rung** — not yet built (research track, new matter, subject to the T3 obstruction).

Two of three rungs now exist as real-model measurements, not assertions. The d=10 rung being a *partial* is itself information: an honest interlacing screen would have to account for the 3 non-separating operators, not assume a clean 10-way basis.

## Claim states

- **Real:** 60 forward passes on real weights; the 10-way classifier; the shuffle null; the confusion matrix; every number.
- **Accepted:** none — research-grade.
- **Open:** framing-matched controls (priority); the 3 non-separating operators; the d=40 rung; larger n.
- **Not licensed:** any product sentence citing these numbers.

**No pod. No GPU. `$0`.** CAS levels now validated on real activations: `^2`/`^3`, `^8`/`^9`, the 4-Domain axis (d=4), and now the 10-Operator axis (d=10, 7/10 partial).
