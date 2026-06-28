# CAS-SDG-Bench — Abstract, Discussion, and Significance
## Verified Draft (2026-05-24) — Updated: all numbers traced, no placeholders

**Verification:** All DiagLoop numbers verified against cas-native/training/runs/K9_DiagLoop_full_v2_honest/honest_eval_report.json. K=9 baseline from v2 outline §5.7; runlog not independently accessible. Gap stated honestly.

---

## ABSTRACT

CAS-SDG-Bench is a synthetic benchmark for structured cognitive recovery over CAS v7.7. Its headline contribution is a tri-channel ground truth framework — notation, diagram, and color — where cross-channel consistency rate serves as the primary diagnostic. Single-channel scoring cannot distinguish surface errors (Register flip) from structural errors (Noetic error); tri-channel evaluation disaggregates error types by modality.

Benchmark methodology layers bucket-stratified generation, property-test-enforced template disjointness, joint-key eval-overlap filtering, and compiler-backed relabel-with-provenance. Empirical validation yields a 6.4 pp hidden clean-eval uplift from contamination remediation and 95-98% canonical-wins asymmetry.

A sequence of results establishes Drive specialization as the limiting reagent. A K=9 paraphrase retrain recovered three of four content heads while Drive regressed. A self-conditioning smoke test produced a null Drive result (70.5% vs 70.7% baseline, -0.2 pp). The K9_DiagLoop full-scale tri-channel experiment achieves +17.63 pp paraphrase-with-self-prior lift, confirming non-redundant diagram-channel signal. However, canonical all-heads-exact drops to 63.0% (per-head: Drive 86.3%, Noetic 88.1%, Registers 93.5%, Domain 95.2%). The shared 64-dimensional bottleneck saturates — smoke-positive, full-scale-negative (outcome C). Cross-channel consistency as benchmark diagnostic is unaffected by the architectural result.

*Data note:* K=9 baseline (93.2% canonical / 46.9% paraphrase) from v2 outline §5.7; runlog not independently verified. All DiagLoop numbers verified against primary runlog artifact.

## DISCUSSION

### Contributions
CAS-SDG-Bench introduces a tri-channel ground truth framework with cross-channel consistency as primary diagnostic. The notation channel provides the canonical string target. The diagram channel (compiler-emitted typed graph) distinguishes structural error severity. The color channel (§4.4) provides paraphrase-insensitive encoding.

### Empirical Results
The K=9 paraphrase retrain established Drive as limiting reagent. Self-conditioning smoke (5K records, 5 epochs) was null for Drive (70.5% vs 70.7%, -0.2 pp). K9_DiagLoop tri-channel: +17.63 pp lift, canonical all-heads-exact 63.0%, capacity-stealing confirmed.

### What We Are NOT Claiming
We do not claim tri-channel outperforms notation-only. We do not claim a new architecture. We do not claim SOTA on public benchmarks. We claim the tri-channel methodology as benchmark contribution, independent of training results.

### Limitations
(a) Color channel specified but not empirically tested. (b) Single CAS-Native model family. (c) K=9 baseline runlog not independently verified. (d) Synthetic data only.

## SIGNIFICANCE
CAS-SDG-Bench addresses a structural blind spot: single-channel scoring cannot distinguish surface from structural errors. Tri-channel framework with cross-channel consistency enables error disaggregation. Contamination remediation exposes hidden leakage. Principled negative results motivate the methodology independently of architectural outcomes.
