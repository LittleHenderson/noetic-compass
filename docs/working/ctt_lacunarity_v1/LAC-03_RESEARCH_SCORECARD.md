# LAC-03 — Research and engineering scorecard (CAS-LAC-001, Phase 1)

Status: living document. Statuses are not interchangeable. **No measure is a validated HELM control signal.**

| Measure | Math correct | Structural sensitivity | Diagnostic validity | Predictive value | Incremental value | Intervention value | Generality | Engineering |
|---|---|---|---|---|---|---|---|---|
| CAS state lacunarity `Var/Mean²` (10 or 40 cells) | YES (formula inspectable) | UNTESTED on synthetic controls | NOT EVALUATED as diagnostic | NO | UNTESTED | NO | UNKNOWN | Implemented twice (Rust + Python), no cross-test |
| CAS coverage metrics (`1−unique/10`, `1−active/4`, `1−active/7`, `1−mechanisms/4`) | YES | UNTESTED | NOT EVALUATED | NO | UNTESTED | NO | UNKNOWN | Implemented; two thresholds (0.2, 0.15) undocumented |
| 40-slot `LacunarityGate` | formula inspectable | N/A (learned controller) | NOT EVALUATED | N/A | N/A | NOT EVALUATED | UNKNOWN | Implemented inside the model; measurement and intervention entangled |
| 40-element `LacunarityHead` | N/A (learned predictor) | N/A | NOT EVALUATED | NOT EVALUATED | NOT EVALUATED | NO | UNKNOWN | Implemented, unvalidated |
| Gliding-box `L(b)` (token field) | YES (14 tests, hand checks) | YES on synthetic fields | YES, one run: field concentrates | NO (the uniform-collapse prediction failed) | UNTESTED vs exposure | NO | One model family | Implemented, tested |
| N-1 per-cell error lacunarity | YES | PARTIAL | YES, held out, one source | NO — overfit check failed after correction | UNTESTED | NO | 98 sources, one family | Implemented |
| N-2 exposure–error gap | formula defined | untested | NOT EVALUATED | NOT EVALUATED | untested | NO | — | Not implemented |
| R-1 recipe requirement dispersion | formula defined | untested | NOT EVALUATED | NOT EVALUATED | untested | NO | — | Not implemented |
| R-2 recipe fragility | formula defined | untested | NOT EVALUATED | NOT EVALUATED | untested | NO | — | Not implemented |
| P-1 unresolved-prerequisite dispersion | formula defined | untested | NOT EVALUATED | NOT EVALUATED | untested | NO | — | Not implemented |
| P-2 RPM chain fragility | formula defined | untested | NOT EVALUATED | NOT EVALUATED | untested | NO | — | Not implemented |

## Status definitions used

- **Proposed** — a formula exists, no code.
- **Implemented** — code runs; correctness not independently established.
- **Mathematically Verified** — hand-checked against its own definition on synthetic inputs.
- **Diagnostically Evaluated** — tested against known structural conditions on held-out data.
- **Predictively Validated** — predicts a failure beyond simpler baselines, replicated.
- **Intervention Validated** — using it selects a repair that improves held-out outcomes.
- **Replicated** — survives a second independent source or model family.

## Honest summary

- Three families are named in the directive; only the Noetic family has any evaluated measure, and that evaluation
  needed a correction that **reversed its verdict** (LAC-00 §4).
- The Recipe and RPM families are **proposals**, not implementations.
- No measure has demonstrated **incremental value** over exposure and loss.
- No measure has been tested in an **intervention**.
- The one strong, clean result in this program is the generation reversal (later checkpoint writes better replies in
  3 of 3 seeds), and it came from a **generation evaluation**, not from a lacunarity measure.
