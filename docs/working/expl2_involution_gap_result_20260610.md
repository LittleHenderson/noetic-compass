# Exploratory Experiment #2 — Involution-Pair (CO-2/CO-3) signal for injection compliance vs refusal

**Date:** 2026-06-10  ·  **Status: EXPLORATORY** (not a registered-method validation; see caveats). The round table's recommended fast falsifier.

## Setup
- Data: the 280 v1 captured responses (240 INJECTED benign-mischief + 40 CLEAN), output text only.
- Scorer: 6 Claude (sonnet) sub-agents, **blind to arm**, each rating a response 0–10 on the 10 Noetic operators per the canonical definitions. (Exploratory scorer — see caveat 1.)
- Metric: the SHIPPED involution pairs `(CO-2,CO-3),(CO-5,CO-6),(CO-8,CO-9)` (`api/similarity/cosine.py:65`, `api/pipeline/forecast.py:_involution_gap`). max-gap = max(|s2−s3|, |s5−s6|, |s8−s9|); signed Positive−Negative = s2 − s3.
- v1 verified labels (COMPLIED 160 / REFUSED 24 / IGNORED 55 / CLEAN 40) joined by trace_id for the by-label cut.
- Stats: dependency-free tie-corrected Mann–Whitney (one-sided), AUC, rank-biserial.

## Results
**Test 1 — DETECT (injected vs clean), involution max-gap magnitude: NULL.**
median gap inj 3.0 vs clean 3.0; AUC 0.549; one-sided p 0.16; 4-point-gap rate inj 0.49 / clean 0.33.
→ The gap *magnitude* does NOT separate injected from clean. (Consistent with the 2026-06-09 spike lesson: magnitude is an off-task/novelty signal, not injection-specific.)

**Test 2 — signed CO-2 − CO-3 (Positive − Negative) by behavioral label:**

| label | n | mean(s2−s3) | median |
|---|---|---|---|
| COMPLIED | 160 | +1.22 | 0.00 |
| REFUSED | 24 | **−6.12** | **−7.00** |
| IGNORED | 55 | +2.42 | +2.00 |
| CLEAN | 40 | +1.07 | 0.00 |

**COMPLIED vs REFUSED on signed (s2−s3): AUC 0.956, rank-biserial 0.912, one-sided p 7.3e-14.**
→ The signed involution pair sharply separates refusal from compliance: REFUSED responses are strongly CO-3-dominant (aversion), everything else is mildly CO-2-leaning. This is the SIGNED-direction discrimination the crude raw-hidden readout could NOT do (it fired for both hijack and refusal).

## What this does and does NOT show (honesty ceiling)
1. **Circularity confound (the big one).** The scorer reads the response TEXT, and a refusal text literally says "I can't / I won't" → the scorer rates CO-3 (aversion/declining) high. The labels (COMPLIED/REFUSED) also came from judges reading the same text. So Test 2 is substantially *two text-readings agreeing that refusal text expresses aversion* — and CO-3 IS "aversion" by definition. The AUC 0.956 is therefore close to **tautological for a text scorer**; it confirms the CAS Positive/Negative involution axis is the **semantically correct coordinate** for the comply/refuse distinction, but it is NOT evidence of an internal or predictive detector.
2. **Not injection detection.** Test 1 (the actual detect-injection test) was null. Test 2 separates comply vs refuse *given* an injected response — useful as a structured readout, not as "we detect the injection."
3. **Claude-as-scorer** (same-family), single scorer, exploratory; v1 benign-mischief payloads only.
4. Must NOT be rounded up to "CAS detects/blocks prompt injection." Permitted claim: *the CAS Positive↔Negative involution pair is the right structured axis for the compliance-vs-refusal distinction, and a text-level operator scoring recovers that split cleanly.*

## Why it still matters
It validates the round table's mechanism-#2 *axis choice*: the comply/refuse distinction lives on the CO-2↔CO-3 involution pair, as a clean signed signal — a traceable, interpretable readout (unlike the crude magnitude trajectory). The genuinely novel, non-circular claim — can the SAME signed axis be read from the model's INTERNAL state (a probe), and does it PREDICT the branch — is the rigorous next step (pod-based, non-Claude scorer and/or internal readout, matched same-prompt design).

**Artifacts:** scores `op_scores_expl2_chunk*.jsonl`, result `expl2_involution_gap_result.json`, archived to `D:\tksCAS-archive\expl2_involution_gap_20260610\`.
