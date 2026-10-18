# HELM & CAS Complete Distribution Package

This standalone package contains the complete HELM brain, the 22x40 and TKS-28 architectures, the verified core engine, the AWS GPU benchmark results, and the publication-grade PDF book.

---

## Directory Structure
- `brains/`: Contains `helm_brain_22x40.py` (22 ingredients x 40 parameters) and `helm_brain_tks28.py` (the 28 Foundations of TKS).
- `core_engine/`: The official `rb_oh1` engine, routing logic, 40-digit Decimal solver, and unit tests.
- `benchmarks_and_results/`: The official `MERGED.json` report and AWS GPU run logs.
- `docs/`: Contains `CAS_HELM_TRANSPARENCY_AND_RECIPE_BRAIN_FOUNDATIONS.pdf` (8-chapter book).
- `verify_all.py`: Single-command verification runner (standard Python 3.10+ stdlib).
- `AUDIT_MANUAL.md`: Complete audit guide for third-party evaluators.

---

## Quickstart: How to Run
From the root of this folder, execute:
```bash
python verify_all.py
```
Zero external packages required.
