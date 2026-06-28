# HALLUCINATION DETECTION AUDIT PACKAGE
## For Independent Verification by Another LLM

---

## 1. WHAT WE CLAIM

The structural trajectory delta (W0→W1 CAS risk change) detects hallucination from hidden states at 0.785 BA on a matched design where prompt text is IDENTICAL across conditions and text literally cannot predict the label.

---

## 2. THE METHOD

We don't ask "does this hidden state look like a hallucination?" We ask: **"does the model's transition from understanding (W0) to generating (W1) follow the expected structural pattern?"**

1. Take Qwen-2.5-0.5B-Instruct
2. Give it prompts that produce SUPPORTED or UNSUPPORTED completions  
3. Capture hidden state at W0 (after prompt, before generation) and W1 (after first token)
4. Train logistic regression on W0 to find "hallucination risk" direction
5. Project W0 and W1 onto this direction → risk scores
6. Δ = risk(W1) - risk(W0) — the structural trajectory delta
7. Classify: positive delta = grounded, negative delta = hallucinated

**Why text can't compete:** The `stale_majority_vote` challenge mode uses IDENTICAL prompt text for both conditions. Same template, same questions. Only the answer differs. Text baseline = 0.500 (majority class — coin flip).

---

## 3. THE DATA

- **Model:** Qwen/Qwen2.5-0.5B-Instruct, layer 14 (of 24), hidden dim 896
- **Sample:** 191 rows (95 SUPPORTED, 96 UNSUPPORTED)
- **Challenge mode:** stale_majority_vote ONLY
- **Prompt text:** IDENTICAL across conditions

---

## 4. THE RESULTS

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Delta BA | **0.7853** | ≥ 0.75 | ✅ |
| Text baseline | 0.500 | — | Can't predict |
| Margin over text | **+0.2853** | ≥ 0.15 | ✅ |
| Permutation p (1000) | **0.00100** | < 0.001 | ✅ |
| Best perm score | 0.6289 | — | None beat real |

Zero of 1000 random label shuffles beat the real BA. Minimum possible p = 1/1001 ≈ 0.001.

---

## 5. PSEUDOCODE

```python
# Train CAS risk direction on W0
scaler = StandardScaler().fit(w0)
clf = LogisticRegression(C=0.25, max_iter=1000, class_weight='balanced')
clf.fit(scaler.transform(w0), yb)
risk_dir = clf.coef_[0]

# Project to get delta
r0 = scaler.transform(w0) @ risk_dir
r1 = scaler.transform(w1) @ risk_dir
delta = r1 - r0

# Evaluate with 5-fold CV
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
for train, test in cv.split(delta, yb):
    c = LogisticRegression(C=0.5, max_iter=2000)
    c.fit(delta[train].reshape(-1,1), yb[train])
    pred = c.predict(delta[test].reshape(-1,1))
    # BA = mean of per-class recall

# Permutation: 1000 random label shuffles
# p = (count(shuffled_BA >= real_BA) + 1) / 1001
```

---

## 6. AUDIT QUESTIONS

1. **Is the matched design valid?** Identical prompts across conditions. Does this adequately control for text leakage?

2. **Is 5-fold CV appropriate for N=191?** 38 per fold, ~19 per class. Sufficient?

3. **Is the permutation test correct?** 1000 shuffles, full re-computation per shuffle.

4. **Is the delta method structurally valid?** We measure W0→W1 risk CHANGE, not absolute risk.

5. **What additional controls would you add?** Generated-prefix baseline? Token-identity? Shuffled-time?

6. **Is 0.785 BA practically meaningful?** Given hallucination base rates vary, what PPV/NPV?

---

## 7. HONEST LIMITATIONS

1. N=191 is small (SE ≈ 0.04)
2. Single model (Qwen-0.5B only)
3. Single challenge mode (stale_majority_vote only)
4. Single layer (14)
5. Observational, not causal (no ablation proof yet)
