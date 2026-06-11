# Output-side CAS audit — 40 Elements + 28 Foundations + the comply/refuse recipe Θ

**Date:** 2026-06-10  ·  **Status: EXPLORATORY (output-side, legitimate audit — reads the produced text, NOT activations, so the Path-B leakage trap does not apply).** Realizes the user's idea: convert the noetic readout into a CAS/TKS formula.

## What ran
12 blind Claude (sonnet) scorers rated the 280 v1 responses (240 injected + 40 clean) on the full **40 Cognitive States** (10 Noetics × 4 Domains P/C/E/O) + **28 Foundations** (7 Drives × 4 Domains), 0–10 each, from text only. Joined v1 verified labels (COMPLIED 160 / REFUSED 24). 6-fold stratified CV logistic (strong L2, balanced). npz/scores archived to `D:\tksCAS-archive\cas68_recipe_audit_20260610\`.

## AUC (comply vs refuse, output-side)
| feature set | AUC |
|---|---|
| signed polarity `E2−E3` (1-D, raw) | 0.966 |
| signed polarity `Σ*2 − Σ*3` (1-D, raw) | 0.971 |
| **40 Elements** | **1.000** |
| 28 Foundations only | 0.908 |
| Full 68-dim | 1.000 |

The richer encoding beats the original 10-Noetic ^2−^3 (0.956): the **domain-resolved** polarity is sharper (0.97), and the 40 Elements separate the two essentially perfectly. **Honesty:** AUC ≈ 1.0 here is the *expected* output-side ceiling — the LLM scorer recognizes refusal language and maps it to the Negative pole, so this confirms the CAS structure cleanly *captures* the distinction in the produced text; it is **not** a new capability and **not** an internal/real-time detector. The drives (28 Foundations) add nothing beyond the 40 Elements; the signal is in the Noetic×Domain structure.

## The recipe Θ (the real deliverable — a traceable CAS equation)
From the standardized logistic weights:

> **Θ(REFUSED) ≈ C3 + P3 + E3  (+ P5, C5, E5, O3)**
> The Negative pole (^3, aversion/objection) fired across the **Cognitive, Principled, and Evaluative** domains — the model objects on cognitive, principled, *and* felt-evaluative grounds — reinforced by accumulated stance (^5 Female) in those upper domains.

> **Θ(COMPLIED) ≈ O0 + O9 + O2 + O4  (+ O:F1, O:F3, P9)**
> Operational-domain activity dominates — the model just *produces the output* (O0 Idea, O9 landed Effect, O2 Positive/going-ahead, O4 intensity) with operational drives, and little upper-domain engagement.

**Interpretation, tied to CAS domain precedence (P ≻ C ≻ E ≻ O):** a **refusal engages the higher domains** — the "should I?" check fires Negative across Principled/Cognitive/Evaluative. A **compliance drops straight to Operational** — it executes without the upper-domain "no." That is a coherent, legible CAS account of hijack-vs-refusal, and it is *traceable*: every response can be rendered as `Θ = Σ aᵢ·(state) → {COMPLIED|REFUSED}`.

## Bottom line
- **Works (output-side):** the 40-Element/recipe audit cleanly separates hijack from refusal and, more importantly, yields a **traceable CAS formula** per response — the product's traceability spine, and exactly "the noetic as an equation."
- **Unchanged:** this is post-hoc (after the model answers), not a live internal interceptor; the internal detector remains unvalidated (Path B was leakage; matched-pair data still needed).

## Cross-family robustness — non-Claude (Mistral-7B) re-score
To check the recipe is not a Claude-scorer artifact, a **non-Claude** model (Mistral-7B-Instruct, on the pod) re-scored the 280 responses on the 10 key states (280/280, 0 unparsed). Result: **the core recipe direction REPLICATES; the magnitude and one term do not.**
- Mean scores by label (Mistral): REFUSED **P3 0.7 / C3 0.7** vs COMPLIED P3 0.3 / C3 0.2 — the **Principled + Cognitive Negative pole is elevated in refusals**, same direction as Claude. COMPLIED **O2 7.3 / O9 4.4** vs REFUSED O2 5.5 / O9 2.7 — **Operational activity elevated in compliance**, same direction.
- AUC is much weaker with the weaker scorer: signed polarity 0.701, 10-state logistic CV 0.757 (vs Claude ~1.0). And **E3 (Evaluative Negative) does NOT replicate** (Mistral sees no E3 elevation in refusals) — that term is scorer-dependent.
- **Verdict:** the **core structure (refusal = upper-domain Negative P3/C3; compliance = Operational O2/O9) is real and cross-family** — a much weaker, different-family model still recovers it (AUC 0.75), so it is **not** a Claude language artifact. The full strength (~1.0) and the E3 component are scorer-quality-dependent; for production replication use a stronger non-Claude scorer (the Gemini connector), not Mistral-7B. Mistral scores archived to `D:\tksCAS-archive\cas68_recipe_audit_20260610\mistral_recipe_scores.jsonl`.
