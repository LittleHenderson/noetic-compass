# Causal Localization of Cognitive Structure in Open-Weight Language Models
## Full Manuscript — Updated 2026-05-24 (replaces outline draft)

**Authors:** Little Henderson et al. — Noetic Compass
**Target:** NeurIPS 2026, ICML 2026
**Data:** CAS Harness Spec Sheet v1.5, Stage 27F/G/H

---

## ABSTRACT

We report evidence that cognitive structure defined by the Cognitive Architecture System (CAS) — a formal framework of 10 Noetic operators, 4 Processing Domains, 7 Core Drives, and 4 Phenomenological Registers — is present and causally load-bearing inside open-weight language models that were never trained on CAS. Using linear probes on hidden-state activations, we detect CAS Foundation classes (28 categories: 7 Drives × 4 Registers) at 78.6% accuracy on Pythia-160M (+28.9 pp over text baseline, p ≈ 10^-95) and 82.4% on Pythia-1B. Subspace ablation collapses probe accuracy to exact chance (3.57% = 1/28). At finer granularity, sparse MLP-neuron covers — small subsets of intermediate neurons — produce bidirectional causal control of the probe readout at 112/112 tests passing (p < 10^-33) with bit-exact patch-back recovery. Cross-architecture replication on Qwen2.5-1.5B yields +0.90 mean lift, 56/56 unanimous (p = 1.4 × 10^-17). The finding supports the hypothesis that CAS describes representational universals.

---

## 1. INTRODUCTION

A central question in mechanistic interpretability is whether structure found inside language models is structure we put there — through training data, architecture, or measurement methodology — or structure that genuinely exists independent of our frameworks. This paper addresses that question for the CAS framework.

If CAS structure is detectable only in models trained on CAS-labeled data, CAS is an invention. If it is detectable in models never exposed to CAS, at accuracy reliably above baselines, with causal dependence at individual neuron level, and replicable across architectures — then CAS is a discovery.

We report five claims: (1) Detection at 78.6% on Pythia-160M, cross-scale to 82.4% on Pythia-1B. (2) Causal necessity via subspace ablation collapse to exact chance. (3) Neuron-level bidirectional control at 112/112, p < 10^-33. (4) Cross-architecture replication on Qwen2.5-1.5B. (5) Behavioral steering at drive-local granularity.

---

## 2. RELATED WORK

Our work intersects linear probing [1,2], mechanistic interpretability [3,4], sparse feature discovery [5,6,7], representation engineering [8], and latent knowledge elicitation [9,10]. Unlike prior probing, we validate causal necessity through three-condition bidirectional control (ablate/amplify/invert) with bit-exact patch-back. Unlike prior steering, our intervention is class-local and cross-architecture validated. Unlike prior feature discovery, neuron covers are discovered via targeted optimization, not unsupervised decomposition.

---

## 3. METHODOLOGY

**3.1 Probe Training.** Linear classifiers over layer 5 MLP activations. Target: 28 CAS Foundation classes (7 Drives × 4 Registers). Text and metadata baselines control for distribution confounds.

**3.2 Neuron-Cover Discovery (Stages 27E-F).** Greedy ablation within candidate layers selects 4–32 neurons per class. Disjoint train/eval splits prevent circularity. Model-native coordinates (L5N2648 = Layer 5, Neuron 2648).

**3.3 Causal Validation (Stages 27F-G).** Three conditions: ablation (zero out), amplification (2×), polarity flip (−1×). Matched random controls. Bit-exact patch-back. Sign test with exact binomial p-values.

**3.4 Cross-Architecture.** Pythia-160M → Pythia-1B (cross-scale) → Qwen2.5-1.5B (cross-architecture). OLMo-1B preregistered but incomplete.

**3.5 Behavioral Steering (Stage 27H).** Calibrated eraser-channel suppression. Likelihood shift measurement. Drive-local specificity.

---

## 4. RESULTS

**4.1 Detection.** Foundation probe: 78.6% (+28.9 pp, p ≈ 10^-95). Pythia-1B: 82.4%. 40-Element: 89.8% (+39.7 pp). Lacunarity 0.021 (38× cleaner than Noetics).

**4.2 Causal Necessity.** Subspace ablation: 78.6% → 3.57% (exact chance). Random same-rank: 0.000 disruption.

**4.3 Neuron-Cover Control.** Ablation: mean drop 3.46 vs -0.22 random. Amplification: +12.74 vs -0.22. Polarity flip: -25.31 vs -0.27. All 28/28 per condition (p = 3.73 × 10^-9). Combined 112/112 (p < 10^-33). Bit-exact recovery: max error 0.0.

**4.4 Cross-Architecture.** Readout: 3 families (Pythia, OLMo, Qwen). Steering: 2 families (Pythia, Qwen). Qwen steering: +0.90, 56/56 unanimous, p = 1.4 × 10^-17.

**4.5 Behavioral Steering.** Pythia-160M: +0.85 (181/245, p = 2.0 × 10^-14). Pythia-1B: +0.84 (54/56, p = 2.2 × 10^-14). Qwen: +0.90 (56/56, p = 1.4 × 10^-17). Weight-geometry: 2.83× random (p = 0.0099).

---

## 5. DISCUSSION

We measure linear decodability + causal dependence. We do NOT claim the model "understands" CAS. Limitations: (a) linear probes — lower bound only, (b) probe training circularity partially mitigated by cross-architecture replication, (c) Pythia training data unknown, mitigated by Qwen, (d) single pair-kind for covers, (e) OLMo steering gap, (f) evidence for universals, not proof.

---

## 6. CONCLUSION

CAS cognitive structure is present, causally load-bearing at two granularities, replicable across architectures, and steerable. These findings support representational universals — pending cross-taxonomy validation and OLMo steering.

---

## REFERENCES

[1] Alain & Bengio. Understanding intermediate layers using linear classifier probes. ICLR Workshop, 2017.
[2] Hewitt & Manning. A structural probe for finding syntax in word representations. NAACL, 2019.
[3] Nanda et al. Progress measures for grokking via mechanistic interpretability. ICLR, 2023.
[4] Conmy et al. Towards automated circuit discovery. NeurIPS, 2023.
[5] Marks et al. Sparse feature circuits. arXiv:2403.19647, 2024.
[6] Bricken et al. Towards monosemanticity. Transformer Circuits Thread, 2023.
[7] Templeton et al. Scaling monosemanticity. Transformer Circuits Thread, 2024.
[8] Zou et al. Representation engineering. arXiv:2310.01405, 2023.
[9] Belrose et al. Eliciting latent predictions. arXiv:2303.08112, 2023.
[10] Gurnee et al. Finding neurons in a haystack. TMLR, 2023.
