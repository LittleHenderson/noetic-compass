# HELM & CAS Cognitive Architecture: Third-Party AI Audit Manual

This document provides a formal, reproducible verification guide for any independent third-party auditor, AI system, or human researcher evaluating HELM (Holistic Emergent Logic Model) and the CAS (Cognitive Architecture System) Recipe Brain.

---

## 1. Executive Summary & Audited Claims

| Claim ID | Formal Claim | Validation Standard | Evidence File |
| :--- | :--- | :--- | :--- |
| **CLM-01** | **Stoichiometric Parameter Efficiency**<br>A 5-parameter CAS substitution recipe outperforms a 223-parameter neural network on held-out substitution data. | Held-out rows right on Family `a_fresh` (512 challenge rows across 16 unseen recipes). | `benchmarks_and_results/MERGED.json`<br>`benchmarks_and_results/gpu_results/RUN_SUMMARY.json` |
| **CLM-02** | **Zero-Hallucination via RPM Gate**<br>When prerequisite inputs are missing, the system halts with code `G-ABSENT` (`UNDETERMINED`), producing 0 invented facts. | Gate evaluation across absent-ingredient panels; 64/64 absent rows quarantined. | `brains/helm_brain_22x40.py`<br>`brains/helm_brain_tks28.py` |
| **CLM-03** | **Deterministic Witness Solvability**<br>Parameters are solved uniquely from finite witness rows via exact 40-digit Gauss-Jordan linear algebra (no gradient descent, no random seeds). | Reconstruction error < 10^-35 on ground-truth parameters. | `verify_all.py`<br>`brains/helm_brain_22x40.py` |
| **CLM-04** | **Preservation of Clean Baseline Worlds**<br>The Hybrid Ledger Router never misroutes strict Leontief recipes to substitution or neural heads (0 false moves). | M3 and M8 milestone marks passing in `MERGED.json`. | `benchmarks_and_results/MERGED.json` |

---

## 2. Independent Step-by-Step Verification Protocol

To independently audit and reproduce all results without assistance:

### Step 1: Automated Verification Runner
Run the universal self-contained test script from the package root:
```bash
python verify_all.py
```
**Expected Output:**
- `helm_brain_22x40`: `PASS` (Reconstruction error < 10^-35)
- `helm_brain_tks28`: `PASS` (RPM Gates halt on absent foundations)
- `test_rboh1`: `PASS` (All 16 core substitution units pass)

### Step 2: Verifying the AWS GPU Head-to-Head Benchmark
Inspect `benchmarks_and_results/MERGED.json` (SHA-256 verified) and `benchmarks_and_results/gpu_results/RUN_SUMMARY.json`:
- **Core Recipe (`A1`)**: 12.50% (64 / 512 rows right)
- **AWS GPU Neural Network (`A7`, 223 parameters trained on NVIDIA Tesla T4)**: 60.74% (311 / 512 rows right)
- **CAS Substitution Recipe (`A2`, 5 parameters)**: **87.50% (448 / 512 rows right)**
- **Margin**: `A2` outperforms the GPU neural net by **+26.76 percentage points**.
- **Theoretical Limit**: The 64 missing rows were absent prerequisites correctly flagged by the RPM gate (448 / 448 valid rows solved = 100%).

---

## 3. Cryptographic Hashes & Integrity

All source files are bound by cryptographic SHA-256 digests. Inspect `core_engine/SOURCE_MANIFEST.json` and `core_engine/FROZEN.json` to verify that zero code files have drifted.
