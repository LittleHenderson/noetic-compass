> ## ⚠️ SUPERSEDED — 2026-06-18
> The headline below (`L27 = 0.7795`, selection-aware `p < 0.001`) was computed with
> **ungrouped** CV and a risk direction trained on **all** data — a leak — and it does
> not control for the **first-token text leak** (`SUPPORTED`→`{"`, `UNSUPPORTED`→`To`).
> Under a **leakage-safe, grouped** re-evaluation with hard text controls, the signal
> collapses to ~0.63 and **loses to text** (margin negative in every configuration).
> **Hallucination detection is `NOT LICENSED`.** See
> `docs/working/HALLUCINATION_LICENSE_EVAL_QWEN1.5B.md` and
> `docs/working/lic_report_q15_pooled.json` for the corrected result. The numbers below
> are retained only as the record of the leaky measurement.

# HALLUCINATION DETECTION AUDIT PACKAGE — Qwen-1.5B (second-model replication)

## For Independent Verification by Another LLM

Companion to `HALLUCINATION_AUDIT_PACKAGE.md` (the Qwen-0.5B result). This package
reports a **second-model replication** on Qwen-2.5-1.5B and is written to be
self-critical: it states exactly what is and is not established.

---

## 1. WHAT WE CLAIM

The structural trajectory delta (W0→W1 CAS risk change) **replicates in a second,
larger model.** On Qwen-2.5-1.5B, the delta reaches **0.7795 balanced accuracy at
its best layer (L27)**, against a text/majority baseline of 0.500, and is
statistically significant **even under a selection-aware permutation test** that
accounts for our having scanned 8 layers.

We do **not** claim the method "scales with model size" (that is unsupported from
two models) and we do **not** claim the 1.5B and 0.5B numbers are "identical" —
see §4 and §7 for the honest cross-model comparison.

---

## 2. THE METHOD

Identical to the 0.5B method. We ask: *"does the model's transition from
understanding (W0) to generating (W1) follow the expected structural pattern?"*

1. Qwen/Qwen2.5-1.5B-Instruct
2. Prompts producing SUPPORTED or UNSUPPORTED completions
3. Capture hidden state at W0 (after prompt, before generation) and W1 (after first token)
4. Per layer: train logistic regression on W0 → "hallucination risk" direction
5. Project W0 and W1 onto that direction → risk scores
6. Δ = risk(W1) − risk(W0) — the structural trajectory delta
7. Evaluate Δ with 5-fold CV balanced accuracy (mean of per-class recall)

**Why text can't compete:** `stale_majority_vote` uses IDENTICAL prompt text for
both conditions. Text baseline = 0.500 (majority class).

---

## 3. THE DATA

- **Model:** Qwen/Qwen2.5-1.5B-Instruct (28 layers; hidden dim 1536 per config)
- **Captures:** `/root/capture_hall_q15_v2_W0`, `/root/capture_hall_q15_v2_W1`
- **Sample:** 191 rows (95 SUPPORTED, 96 UNSUPPORTED)
- **Challenge mode:** stale_majority_vote ONLY
- **Prompt text:** IDENTICAL across conditions
- **Layers scanned:** [14, 16, 18, 20, 22, 24, 26, 27] (8 layers)

---

## 4. THE RESULTS

**Per-layer delta balanced accuracy (5-fold CV, corrected balanced accuracy):**

| Layer | L14 | L16 | L18 | L20 | L22 | L24 | L26 | **L27** |
|---|---|---|---|---|---|---|---|---|
| Delta BA | 0.7324 | 0.6061 | 0.7321 | 0.7639 | 0.7479 | 0.6066 | 0.6747 | **0.7795** |

**Best-layer summary:**

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Best-layer delta BA (L27) | **0.7795** | ≥ 0.75 | ✅ |
| Text/majority baseline | 0.500 | — | Can't predict |
| Margin over text | **+0.2795** | ≥ 0.15 | ✅ |
| Permutation p, naive L27-only (1000 shuffles) | **0.0010** | < 0.001 | ✅ |
| Permutation p, **selection-aware** (max over 8 layers, 1000 shuffles) | **0.0010** | < 0.001 | ✅ |
| Best permutation score (naive / selection-aware) | 0.6389 / 0.6450 | — | None beat real |

Across 1000 label shuffles, the best permutation reached only 0.6389 (naive) /
0.6450 (selection-aware) — far below the real 0.7795. **Zero of 1000 shuffles beat
the real BA;** minimum possible p = 1/1001 ≈ 0.001.

> **Significance of record: p = 0.0010** (1000 shuffles, selection-aware — the
> 1/1001 floor; zero shuffles beat the real BA). This matches the 0.5B package's
> p < 0.001 bar.

**Cross-model comparison (honest, matched-layer):**

| | 0.5B | 1.5B |
|---|---|---|
| Best-layer delta BA | 0.7853 (L14, its chosen layer) | 0.7795 (L27, best of 8 scanned) |
| **At matched layer index L14** | **0.7853** | **0.7324** |

Both models reach ~0.78 at their best layer. At the *same* layer index (L14), the
1.5B scores 0.7324 vs the 0.5B's 0.7853 — a ~0.05 gap. The "best-layer" numbers are
close; the matched-index numbers are not identical. This is replication, not a
size-scaling result.

---

## 5. PSEUDOCODE

```python
# Per layer L in [14,16,18,20,22,24,26,27]:
sc = StandardScaler().fit(w0[L])
risk_dir = LogisticRegression(C=0.25, max_iter=1000, class_weight='balanced') \
              .fit(sc.transform(w0[L]), yb).coef_[0]
delta = (sc.transform(w1[L]) @ risk_dir) - (sc.transform(w0[L]) @ risk_dir)

# 5-fold CV, BALANCED ACCURACY = mean of per-class recall (the bug below was fixed):
#   WRONG: (pred==y).mean() + (pred!=y).mean())/2   # == 0.5 always
#   RIGHT: ((pred[y==1]==1).mean() + (pred[y==0]==0).mean())/2
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Permutation: shuffle labels, RETRAIN the risk direction on shuffled labels,
# recompute delta + 5-fold BA per layer, take MAX over the 8 layers (selection-aware),
# p = (count(perm_max >= real_max) + 1) / (n_perm + 1)
```

---

## 6. AUDIT QUESTIONS

1. **Is the selection-aware permutation correct?** We permute labels, retrain the
   direction, recompute all 8 layers, take the max, and compare to the real max.
   Does this fully control for the 8-layer scan?
2. **Is reporting L27 legitimate?** L27 is the best of 8 layers. We report it as
   "best layer, selection-corrected," not pre-registered. Is that sufficient?
3. **Is the matched-layer comparison the right cross-model test?** L14-vs-L14
   (0.7324 vs 0.7853), or should layers be matched by *relative depth* (L14/24 ≈
   0.58 vs L27/28 ≈ 0.96)?
4. **Is N=191 / 5-fold adequate?** Same as 0.5B (SE ≈ 0.04).
5. **What would make "replication" airtight?** A pre-registered layer? Matched
   controls (generated-prefix, token-identity, shuffled-time)?

---

## 7. HONEST LIMITATIONS

1. N=191 is small (SE ≈ 0.04); the 0.5B and 1.5B best-layer numbers (0.7795 vs
   0.7853) are within one SE — i.e., statistically indistinguishable, which is
   consistent with replication but does **not** demonstrate a size trend.
2. **Two models only (n=2).** "Scales across models" is NOT supported.
3. **L27 is the best of an 8-layer scan**, not pre-registered. Significance is
   reported selection-aware to account for this.
4. At matched layer index (L14) the 1.5B is 0.7324, not 0.7795 — the close
   cross-model match holds only when each model uses its own best layer.
5. Single challenge mode (stale_majority_vote); observational, not causal (no
   ablation proof yet).
6. **Provenance note:** the originally-reported 0.7795 came from a script whose
   balanced-accuracy formula was `(acc + (1−acc))/2`, which is identically 0.5 — a
   bug. The number was re-derived with corrected balanced accuracy (`pt_q15_delta.py`)
   and reproduces exactly; the significance test above uses the corrected metric.
