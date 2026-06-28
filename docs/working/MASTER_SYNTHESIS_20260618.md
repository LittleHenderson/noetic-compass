# Noetic Compass — Master Synthesis: CJT, PCBA, Detection Architecture & Hidden-State Feasibility

**Date:** 2026-06-18
**Version:** 1.0
**Status:** ACTIVE

---

## SESSION ARTIFACTS

| Artifact | Path | Purpose |
|---|---|---|
| CJT+PCBA Blueprint | `docs/working/CJT_PCBA_IMPLEMENTATION_BLUEPRINT.md` | Full CJT: compiler, analytical, safety, visualization, multi-agent, PCBA map |
| PCBA Engineer Book Plan | `book/CAS_PCBA_Engineer_BOOK_PLAN.md` | 26-chapter book: beginner to production CCB |
| Chapter 1 (written) | `book/CAS_PCBA_Engineer/Chapter_01_Why_Build_Cognitive_Circuits.md` | "The Prompt-and-Pray Problem" |
| Detection Architecture | `docs/working/CAS_DETECTION_ARCHITECTURE_20260618.md` | 7 detection primitives from v7.4 + Noetic Topos + PCBA |
| Hallucination Post-Mortem | `docs/working/outcome_native_hallucination_trajectory_break_postmortem_20260618.md` | Challenge-mode leak analysis |
| Evaluator patch | `evaluate_timing_trajectory_break.py` | W0-static claim, W4/W16 args |
| Pod run script | `run_qwen15_hallucination_v3.sh` | Full 5-stage experiment pipeline |

---

## DOES IT WORK ON HIDDEN STATES?

The 7 detection primitives require mapping LLM hidden states to CAS state coordinates. The bridge is a **CAS-probe** — a linear classifier that extracts Noetic/Domain/Drive/Register from hidden states.

**What EXISTS:**
- Stage9 40-Element probe (Noetic x Domain): **95.6% accuracy** on 8,320 GPT-NeoX-20B vectors
- Foundation-28 probe (Drive x Register): **86.9% accuracy** (NPZ recovery pending)
- CAS-Native V2 backbone checkpoint on disk

**What's MISSING:**
- Probes trained on GPT-NeoX, not Qwen — cross-model transfer unknown
- No unified 40-dim probe combining all 4 CAS axes
- Trajectory-break evaluator uses raw hidden states, not CAS-probed features

## THE PATH TO FIRST LICENSED CLAIM

**Target: Admissibility Violation (#1)** — each operator CO-k has Dk lookup table. Illegal transition = (source, target) not in Dk.

Steps:
1. Train 40-Element CAS probe on Qwen-2.5-1.5B hidden states
2. Extract Noetic + Domain from W0 hidden states
3. Load Dk tables from `cas-engine/src/ontology/`
4. Verify each state transition: (state_t, state_{t+1}) in Dk?
5. Gate: probe accuracy > 90%. Admissibility check is DETERMINISTIC (no BA vs text baseline needed)

**Estimated: 2-4 weeks to first licensed claim.**

## LICENSE STATE

```
CAS Harness: claims_licensed=0, claims_not_licensed=6
CAS Forex (PCBA): 3 claims LICENSED (component syntax, compiler safety, injection prevention)
```

Claim hierarchy: DETECTION → CAUSAL PROOF → PREVENTION → REMOVAL → REVERSAL
