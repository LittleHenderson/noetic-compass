# CAS PROBE SESSION — June 18, 2026

**Status:** Pipeline complete. CAS directions extracted. Hallucination detection at 0.832 BA.
**License state:** claims_licensed=0, claims_not_licensed=6

---

## PIPELINE BUILT

Official TKS Definitions → Fixture (816 scenarios) → Qwen-0.5B Capture (24 layers, 33MB NPZ) → Probe Training → CAS Direction Extraction (Cohen d=0.89) → Hallucination Detection (CAS-probe features: 0.832 BA)

---

## KEY RESULTS

### Official Definitions
- 40E from "Majik and the True Kabbalah" (A1-D10)
- 28F from Tootra elaborated (1a-7d)
- Stored: `docs/working/tks_owner_locked_definitions_20260603.json`

### Probe Accuracy (Qwen-0.5B)
- Noetic nearest-centroid L8: 73.2% (maj=41.2%)
- Noetic logistic L8: 98.8% — BUT text baseline = 100% (definition-keyword leak)
- CAS directions from natural-language prompts: Cohen d=0.89, W0 BA=0.67

### Hallucination Detection
- CAS-probe features L14: 0.832 BA (+24pp over raw 896-dim)
- CAS-probe features L8: 0.754 BA (crosses 0.75 threshold)
- Signal strongest at W0 (pre-generation)

---

## THREE DETECTION TARGETS

| Target | Status |
|---|---|
| Prompt Injection | PATH EXISTS — CAS probe + Dk admissibility + d_FR bias comparator |
| Hallucination | PARTIALLY PROVEN — 0.832 BA, needs permutation test + held-out validation |
| Causal Proof | INFRASTRUCTURE EXISTS — ablation probes + CAS direction measurement |

---

## NEXT STEPS

1. Permutation test on L8 CAS-probe (0.754 BA) → if p<0.001, licensable
2. Contrastive probe training for generalization
3. Scale to Qwen-2.5-1.5B
4. Wire Dk admissibility lookup → first structural detection claim
