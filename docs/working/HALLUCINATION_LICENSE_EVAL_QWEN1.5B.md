# Hallucination Detection — License-Gate Evaluation (Qwen-1.5B)

**Date:** 2026-06-18
**Verdict:** `NOT LICENSED` (decisive — the hidden-state signal does not beat text under any leakage-safe configuration tested)
**Reproduce:** `lic_eval.py` piped to the pod (`/root/capture_hall_q15_v2_W0`, `_W1`); machine report `docs/working/lic_report_q15_pooled.json`.

---

## What was tested

The claim under audit: the **W0→W1 hidden-state risk delta** detects hallucination
(`SUPPORTED` vs `UNSUPPORTED`) from internal state, *better than the visible text can*.
The license bar (the user's gate): hidden balanced accuracy (BA) ≥ 0.75 **and** a
**margin ≥ 0.15 over every text control** (prompt word/char, generated-prefix
word/char, token identity, layer-0, length, topic, domain, retrieval metadata),
with **grouped CV** (prompt groups never split), a **residual** proof (works after
text is removed), a **held-out-topic** proof, and a **1000-shuffle selection-aware**
permutation `p < 0.001`.

Everything below is **leakage-safe**: GroupKFold by exact-prompt group, and the
risk direction is trained **inside each train fold only** (the earlier 0.78–0.88
numbers trained it on all data — a leak).

## Data (matched exact-prompt set, Qwen2.5-1.5B)

- 61 matched exact-prompt groups (same prompt produced both labels), 588 rows,
  205 `UNSUPPORTED` / 383 `SUPPORTED`, 5 topics. (Data gate satisfiable.)
- **W0 within-group deviation = exactly 0.0** — at the pre-answer window the hidden
  state is *identical* within a same-prompt group, so text/W0 carry zero within-group
  signal. The only within-group signal appears at **W1 (after the 1st generated token)**.

## Results — text beats hidden in every configuration

| Configuration | Hidden delta BA | Best text control | **Margin** | Gate |
|---|---|---|---|---|
| Pooled, all modes (61 groups) | 0.634 (L26) | 0.711 — genprefix/token-identity | **−0.077** | FAIL |
| mv-only (cleanest matched design) | 0.807 (L12) | 0.832 — first token (genprefix-char) | **−0.025** | FAIL |
| Shared-first-token (token held constant) | 0.640 (L26) | 0.678 — prompt text | **−0.039** | FAIL |

Pooled-set full gate panel (from `lic_report_q15_pooled.json`):

| Gate | Value | Pass |
|---|---|---|
| Enough data | 61 groups / 205 unsupported | ✅ |
| Accuracy floor (≥0.75) | hidden BA 0.634 | ❌ |
| Margin over text (≥0.15) | −0.077 | ❌ |
| Residual (delta after removing text/prefix/meta) | 0.480 (chance) | ❌ |
| Held-out topic (mean BA) | 0.573 | ❌ |
| **LICENSED** | — | **False** |

The **residual = 0.48** is the cleanest single fact: once text/prefix/metadata
information is regressed out of the delta, it predicts at chance. The delta carried
nothing beyond text.

## Root cause (why it cannot license with this data)

1. **W0 (pre-answer) is identical within a same-prompt group** → zero within-group
   signal by construction. A pre-answer detector has nothing to read.
2. **W1's signal is the first emitted token**, and that token *is* the leak: across
   matched groups, `SUPPORTED` starts mostly with `{"` and `UNSUPPORTED` with `To`.
   So `token_identity` / `genprefix` controls reach 0.71–0.83 — at or above the
   hidden state.
3. **Even holding the first token constant** (shared-token subset), the hidden state
   (0.64) loses to the **prompt** (0.68) under grouped CV — residual prompt/mode
   structure leaks.

In short: in this matched-sampling design the label is a *downstream consequence of
which completion was sampled*; it is not encoded in any pre-text-reveal hidden state
the captures contain. The hidden state never adds information beyond the visible text.

## What the earlier numbers were

The previously reported `L27 = 0.7795` (and `W16 ≈ 0.888`) were **leakage**:
ungrouped CV + a direction trained on all data + a cherry-picked layer/window + the
first-token text leak. Under leakage-safe grouped CV with hard controls the signal
collapses to ~0.63 and **loses to text**. `docs/working/HALLUCINATION_AUDIT_PACKAGE_QWEN1.5B.md`
is corrected/superseded accordingly.

## What would legitimately license it (requires NEW data)

A **teacher-forced identical-prefix capture**: force *both* conditions to emit a
byte-identical answer prefix (same template **and** same first token), and capture
the hidden state at the position **right before the answer-value token**, with the
value's groundedness as the label. That neutralizes every text control (prompt,
prefix, token all identical) and isolates whether the hidden state encodes
groundedness *before the value is revealed*. If hidden BA ≥ 0.75 with margin ≥ 0.15
there, the claim licenses honestly. That capture does not exist yet and cannot be
fabricated; it is the required next experiment.
