# §5.7.5 Full-Scale Retrain Results — V3 Numbers Fill-In Template

**Purpose.** Drop-in replacement for §5.7.5 in `paper_a_v2_section_5_7_diagloop_draft_2026_05_04.md`. When the K9_DiagLoop full v3 honest eval lands, fill in the numeric placeholders below, select the matching pre-committed interpretation case (Case A / B / C), and replace the placeholder section in the parent draft with the populated version.

**Source eval manifest.** `noetic-compass-scaffold/noetic-compass/cas-native/training/runs/K9_DiagLoop_full_v3_2026_05_04/manifest.json` (path will exist post-eval).

**Decision rule for case selection.** Read three numbers from the manifest:
1. `paraphrase_with_self_prior_rate` (aggregate)
2. lift = `paraphrase_with_self_prior_rate − paraphrase_text_only_rate`
3. `per_head.registers.consistency_under_self_prior`

Apply thresholds:
- Case A: paraphrase_with_self_prior ≥ 0.60 AND lift ≥ 0.20 AND registers ≥ 0.95
- Case B: 0.50 ≤ paraphrase_with_self_prior < 0.60 OR (lift in [0.15, 0.20) and not Case A)
- Case C: paraphrase_with_self_prior < 0.50 OR lift < 0.10

If multiple cases match, prefer the more conservative (C > B > A). If no case matches cleanly (e.g., paraphrase_with_self_prior in [0.50, 0.60) with lift > 0.20), fall back to Case B and add a note explaining the boundary.

---

### 5.7.5 Full-Scale Retrain Results

**Setup.** Training base: K=9 baseline checkpoint commit `3232f05`. Augmentation: K=8 paraphrase + K=3 diagram-loop. Training data: 16,570 canonical Level 3 recoverable records (post joint-key filter) expanded to ~198,840 training examples. Held-out evaluation: 1,000 records on `level3_recoverable_eval_1000_v77_relabeled.jsonl`. Epochs: 20. Total steps: ~31,080. Eval protocol: honest two-pass (§5.7.3). Pod: 104.255.9.187. Run identifier: `K9_DiagLoop_full_v3_2026_05_04`. Started 2026-05-04 18:19 UTC. Eval landed _____ UTC.

**Aggregate results.**

| Metric | Value |
|---|---:|
| Canonical text-only (pass 1) | _____% |
| Paraphrase text-only (no graph prior) | _____% |
| Paraphrase with self-prior (pass 2, honest) | **_____%** |
| Honest lever lift | **_____ pp** |

**Smoke v2 → full v3 delta.**

| Metric | Smoke v2 (5K, 5ep) | Full v3 (16.5K, 20ep) | Δ |
|---|---:|---:|---:|
| Canonical text-only | 47.9% | _____% | _____ pp |
| Paraphrase text-only | 26.6% | _____% | _____ pp |
| Paraphrase with self-prior | 45.4% | _____% | _____ pp |
| Honest lever lift | +18.8 pp | _____ pp | _____ pp |

**Per-head consistency under self-prior.**

| Head | Smoke v2 | Full v3 | Δ |
|---|---:|---:|---:|
| registers | 98.6% | _____% | _____ pp |
| noetic | 85.1% | _____% | _____ pp |
| domain | 81.0% | _____% | _____ pp |
| drive | 71.6% | _____% | _____ pp |

**Per-bucket all-heads-exact (paraphrase with self-prior).**

| Bucket | n | Smoke v2 | Full v3 | Δ |
|---|---:|---:|---:|---:|
| `v77_omega` | 267 | 75.7% | _____% | _____ pp |
| `v74_baseline` | 200 | 60.5% | _____% | _____ pp |
| `v77_rule_four` | 59 | 48.6% | _____% | _____ pp |
| `v75_register` | 264 | 25.8% | _____% | _____ pp |
| `v76_production` | 108 | 24.4% | _____% | _____ pp |
| `meta_logic` | 102 | 7.5% | _____% | _____ pp |

**Comparison to K=9 notation-only baseline at full scale.**

| Metric | K=9 notation-only (full scale) | K9_DiagLoop full v3 | Δ |
|---|---:|---:|---:|
| Canonical | 93.2% | _____% | _____ pp |
| Paraphrase text-only | 46.9% | _____% | _____ pp |
| Paraphrase with self-prior | n/a (no graph channel) | _____% | _____ |

---

#### Interpretation — select one case

##### Case A — strong validation (≥60% with-self-prior, ≥20 pp lift, registers ≥95%)

The full-scale result confirms the smoke v2 finding. The tri-channel architecture delivers a paraphrase-invariance lift that survives the transition from smoke scale to full scale and that scales monotonically with training data and training epochs. The graph channel is non-redundant signal beyond what a text-only model can recover at any scale we have tested. Per-bucket recovery on `v76_production` and `meta_logic` ____________ (fill in: did high-arity buckets recover with more data, or did the architectural canary persist?), suggesting that ____________ (encoder capacity is sufficient at full scale / encoder capacity remains the bottleneck even at full scale).

We recommend the diagloop architecture as the production architecture going forward, replacing K=9 notation-only as the deployment target. The follow-on research question is per-head channel routing: the per-head asymmetry observed at smoke (registers >> noetic ≈ domain > drive) ____________ (fill in: was preserved at full scale / was attenuated at full scale / inverted at full scale), and a per-head routing ablation is the natural next experiment.

##### Case B — solid validation (50-60%, 15-20 pp lift)

The full-scale result partially confirms the smoke v2 finding. The graph channel adds a real, statistically significant lift over text-only paraphrase recovery, but the lift is smaller than smoke suggested and does not unambiguously dominate the K=9 notation-only baseline on the joint metric. ____________ (fill in: a specific cost-benefit observation — e.g., the diagloop architecture matches the K=9 baseline canonical accuracy but lifts paraphrase invariance by X pp at the cost of Y pp on a different metric).

The architecture is a successful research probe but not a clear production-architecture commitment. We recommend continued lever exploration — bare-slot K beyond 9, self-conditioning at scale, grammar-guided sampling on the K=9 checkpoint — before architectural commitment, and we defer the production-architecture decision to a follow-up study with per-head channel routing controls. The §5.7.7 discussion frames this as the appropriate epistemic posture given the observed cost-benefit profile.

##### Case C — collapse (<50%, <10 pp lift)

The full-scale result does not confirm the smoke v2 finding. The paraphrase-with-self-prior accuracy at full scale is _____% (vs 45.4% at smoke), and the honest lever lift is _____ pp (vs +18.8 pp at smoke). The smoke v2 lift was a scale artifact: at full data and full epochs, the graph channel either does not survive training pressure or is dominated by capacity-stealing at the shared 64-dimensional bottleneck.

The signature finding is the divergence between smoke v2 and full v3 on the same architecture. Two non-exclusive mechanisms can produce this divergence. First, capacity-stealing: the graph fusion path competes with the text path for the 64-dimensional shared bottleneck, and at smoke scale the model has not yet reached the capacity limit, while at full scale the canonical-recovery feature path loses parameters to the graph-fusion feature path. Second, signal-shift: the K=3 diagram-loop augmentation ratio that was effective at 5K records and 5 epochs may dilute or compete with paraphrase signal at 16.5K records and 20 epochs, and a different ratio (or a curriculum schedule) may be required at full scale.

We deprecate the diagloop architecture as a primary lever and recommend the K=9 notation-only baseline plus Lever 3 — ____________ (fill in: self-conditioning at scale OR grammar-guided sampling on the K=9 checkpoint OR per-head channel routing on the K=9 backbone) — as the next experimental direction. The negative result is publishable as a methodological finding: a non-redundant signal at smoke scale does not guarantee a net-positive architecture at full scale, and capacity-stealing at the shared bottleneck is the load-bearing mechanism. The §5.7.7 discussion frames this finding alongside the per-head channel routing hypothesis as a follow-on architectural direction that addresses the diagnosis on its merits.

---

**Sub-section status when filled.** Once the table values are populated and one of Case A / B / C above is selected, this template replaces the placeholder §5.7.5 in `paper_a_v2_section_5_7_diagloop_draft_2026_05_04.md` verbatim. §5.7.6 and §5.7.7 in the parent draft are written to be valid under all three cases; verify that the discussion in §5.7.7 still reads correctly given the selected case, and edit only the case-specific extension sentences (per-head asymmetry preservation, per-bucket recovery interpretation).

**Filled-by.** _____ (agent or operator name)
**Filled-at.** _____ (UTC timestamp)
**Manifest path used.** _____ (full path to manifest.json)
**Case selected.** _____ (A / B / C, plus any boundary note)
