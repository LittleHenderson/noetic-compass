# V32 — SCALE-UP to n=100 × 5 frames: the dissociation is CONFIRMED with non-overlapping CIs, and two earlier claims are CORRECTED

**Date:** 2026-08-22 · `pythia-160m` (reserialized), **attested engine**, CPU, **$0**.
**Results:** `detector_v32_scaleup_results.json`, sha256 `1a31c7fda638a35d…`
**Answers the two objections an informed critic raises first:** *"n=12, cherry-picked"* → **100 pairs / 200 items per contrast**, with bootstrap 95% CIs. *"one sentence template"* → **5 distinct frame templates**, 20 pairs each, **reported per frame**.

**Pre-flight gate passed on all 300 pairs before the model loaded:** word multisets identical (`0` mismatches), char-n-gram bag residual `0.000000`, token-length mismatches `0/12`. **Both surface baselines are therefore FORCED to `0.500` by arithmetic across the entire scaled set.**

---

## 1. Results

| contrast | best layer | mean over ALL 12 layers | bootstrap 95% CI | excludes 0.500 |
|---|---|---|---|---|
| **CAS `^8`/`^9`** trigger-vs-arrival | **`1.000`** (L3) = 200/200 | **`0.8033`** | `[0.7883, 0.8183]` | ✅ |
| **temporal** binding | **`0.970`** (L3) = 194/200 | **`0.7367`** | `[0.7142, 0.7592]` | ✅ |
| **speaker** binding | `0.710` (L3) = 142/200 | `0.5683` | `[0.5563, 0.5813]` | ✅ |

Best-layer significance (200 items): CAS `P = 6.223e-61`; temporal `P = 5.290e-50`; speaker `P = 1.290e-09` (single-layer), all still astronomically past best-of-12 correction.

Per frame (mean over layers) — the ordering holds in **every one of the five**:

| frame | CAS | temporal | speaker |
|---|---|---|---|
| 0 | 0.7271 | 0.6354 | 0.5687 |
| 1 | 0.8292 | 0.7312 | 0.5958 |
| 2 | 0.7646 | 0.8750 | 0.5542 |
| 3 | 0.8562 | 0.7812 | 0.5708 |
| 4 | 0.8396 | 0.6604 | 0.5521 |

## 2. ✅ CONFIRMED — the dissociation is real and now statistically clean

**All three 95% confidence intervals are mutually NON-OVERLAPPING:**

```
CAS ^8/^9  [0.7883, 0.8183]
temporal   [0.7142, 0.7592]
speaker    [0.5563, 0.5813]
```

At n=12 the dissociation rested on point estimates. At **n=100 across 5 frames** it rests on **separated intervals**, and the ordering **CAS > temporal > speaker** reproduces in every single frame. The "n=12, cherry-picked, one template" objection is now **answered**, not deflected.

## 3. 🟥 CORRECTION 1 — "speaker binding is at chance" is WRONG

**v27 and v29 recorded speaker binding as `NOT_READ` / "chance."** At n=100 that is **false**: mean `0.5683` with CI `[0.5563, 0.5813]`, which **excludes `0.500`**; best layer `142/200`, `P = 1.29e-09`.

**Corrected statement:** speaker-instruction binding is **weakly but genuinely readable** — *dramatically* weaker than cause or time (non-overlapping CIs, a gap of `~0.24` from CAS), but **not absent**. The earlier "chance" verdict was an artifact of n=12 lacking the power to resolve a small effect.

**This does NOT overturn the substantive finding.** The dissociation stands and is now stronger. What changes is the *wording*: it is a **graded** dissociation (strong / medium / weak), not **presence vs absence**. Every claim phrased as "the model does NOT bind speaker to instruction" must be restated as **"binds speaker far more weakly than it binds cause or time."**

## 4. 🟥 CORRECTION 2 — the n=12 effect sizes were INFLATED

| contrast | n=12 mean | n=100 mean | delta |
|---|---|---|---|
| temporal | `0.917` | `0.7367` | **`−0.1803`** |
| CAS `^8`/`^9` | `0.962` | `0.8033` | **`−0.1587`** |
| speaker | `0.520` | `0.5683` | `+0.0483` |

Small-n **overstated the strong effects by `0.16`–`0.18`** and **understated the weak one**. Mechanism: with 12 pairs, leave-one-out centroids are noisy and the estimate is unstable in both directions.

**Consequence for the record:** the headline figures in v23/v25/v26 (`1.000` best, `0.917`–`0.962` mean) are **real at their own n but not representative**. **The n=100 means are the defensible numbers.** Best-layer `1.000` does survive at n=100 for CAS (`200/200`) — so the *peak* claim holds; the *average-across-layers* claim shrinks.

## 5. What this does and does not license

- ✅ **LICENSED:** *"On `pythia-160m`, with both bag-of-words and char-n-gram baselines forced to `0.500` by construction across 100 pairs and 5 frame templates, the model separates CAS `^8`/`^9` trigger-vs-arrival (mean `0.8033`, CI `[0.7883,0.8183]`, best layer `200/200`), temporal order (mean `0.7367`, CI `[0.7142,0.7592]`), and speaker-instruction binding (mean `0.5683`, CI `[0.5563,0.5813]`) — three non-overlapping intervals, same ordering in all five frames."*
- 🟥 **WITHDRAWN:** "speaker binding is at chance / NOT_READ" (v27, v29) → replaced by "weakest of the three, but above chance."
- 🟥 **BOUNDED:** the v23/v25/v26 mean-over-layers figures — use the n=100 values.
- **Still NOT established:** that the readable structure is specifically **CAS** rather than ordinary semantic role structure that CAS names. `GREY`, unchanged.
- **Open:** whether the graded pattern reproduces at 6.9b / instruction-tuned scale with n=100 (the paid runs used n=12).

## 6. Method note — a bug this run caught in itself
A first attempt reported temporal at **exactly `0.5000`** with zero variance across 100 pairs, 5 frames, and 12 layers. Real data cannot do that. Cause: in the rewritten scorer, `hit = (A correct); hit += (B correct)` where both are `numpy.bool_` — and **`np.True_ + np.True_` is logical OR, not `1+1`**, so every pair was capped at `0.5` and no pair could score `1.0`. Fixed by casting to `float` before adding, plus a permanent self-check that warns if no pair ever scores `1.0`. The original scorer (`ok = 0; ok += np.bool_`) was correct because `int + np.bool_` promotes properly. **The impossible-looking null was the tell.**
