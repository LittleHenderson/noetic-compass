# Stage 4A v0.2 — Findings (2026-05-14)

**Run dir on pod:** `/workspace/tksCAS/stage4a_v02_20260514T200413Z`
**Eval dir on pod:** `/workspace/tksCAS/stage4a_eval_v02_20260514T201152Z`
**Checkpoint ID:** `30019a89-f75a-42f1-816b-f29f2df7fe4b`
**Corpus:** `cas-synthetic/data/stage4/track1_v02_merged_2026_05_14.jsonl` (sha256 `513dd106…`), 5,608 records (5,244 Wave 2.5 + 364 Stage 4B clean-train, natural ratio 93.5/6.5)
**AUTHORIZED entry:** 2026-05-14T19:45Z, ratified at user "go" 19:55Z (Codex 728be8c)

## Headline

**Run completed cleanly. Model did NOT promote.** 5 of 8 mechanical gates pass; 3 fail (normalized recovery still below 0.10 floor, unique_output_ratio regressed, mode_collapse_ratio regressed). **But the direction is right — recovery moved from 0 → 0.7% with first non-zero specifically in the category that received the most Stage 4B records (state_literal at 3.2% exact).**

## v0.1 → v0.2 deltas

| Metric | v0.1 | v0.2 | Δ |
|---|---|---|---|
| TF per-token accuracy | 0.773 | **0.776** | +0.3 pp |
| Free-decode validity rate | 0.927 | **0.932** | +0.5 pp |
| Exact recovery rate | 0.000 | **0.007** | **+0.7 pp (first non-zero)** |
| Normalized recovery rate | 0.000 | **0.007** | +0.7 pp (still < 0.10 floor) |
| Unique output ratio | 0.229 | **0.139** | **−9.0 pp (regressed)** |
| Mode collapse ratio | 0.111 | **0.189** | **+7.8 pp (regressed)** |
| Top mode count | 29 / 262 | 53 / 280 | top mode now dominates 19% |
| Per-bucket validity ≥ 0.25 buckets | 9/10 | **8/10** | meta_logic dipped slightly |
| Load mismatch | 0/0 | 0/0 | same |
| Final loss_lm | 0.91 | 0.95 | similar |

## Promotion gates against v0.2 AUTHORIZED entry

| Gate | Floor | v0.2 | Status |
|---|---|---|---|
| TF per-token accuracy | ≥ 0.20 | 0.776 | ✅ 3.9× over |
| Free-decode CAS validity rate | ≥ 0.50 | 0.932 | ✅ 1.86× over |
| Normalized recovery rate | ≥ 0.10 | **0.007** | ❌ FAIL (but FIRST non-zero) |
| Per-bucket validity ≥ 0.25 in ≥ 7/10 | 7/10 | 8/10 | ✅ |
| **Unique output ratio** | **≥ 0.40** | **0.139** | ❌ FAIL (regressed from v0.1) |
| **Mode-collapse ratio** | **≤ 0.15** | **0.189** | ❌ FAIL (regressed from v0.1) |
| Load mismatch | 0/0 | 0/0 | ✅ |
| Human sample read | "model trying" | partial mode collapse | mixed |

**Promotion verdict:** REJECT. Three gates failed.

## Per-grammar-category breakdown — the key finding

| Category | n | TF acc | Validity | Exact | Norm | Stage 4B records in corpus |
|---|---|---|---|---|---|---|
| **state_literal** | 62 | 0.373 | 1.000 | **0.032** | **0.032** | **190 (52% of Stage 4B)** |
| binary_composition | 39 | 0.573 | 1.000 | 0.000 | 0.000 | 53 (15%) |
| cross_register_omega | 34 | 0.766 | 1.000 | 0.000 | 0.000 | 0 |
| diagram_export | 18 | 0.758 | 1.000 | 0.000 | 0.000 | 0 |
| fractal_sequence | 19 | 0.516 | 1.000 | 0.000 | 0.000 | 0 |
| inversion | 1 | 0.818 | 1.000 | 0.000 | 0.000 | 0 |
| let_binding | 23 | 0.875 | 1.000 | 0.000 | 0.000 | 9 (2.5%) |
| meta_logic_relation | 37 | 0.739 | 0.919 | 0.000 | 0.000 | 0 |
| recipe | 32 | 0.722 | 0.969 | 0.000 | 0.000 | 121 (33%) |
| rpm_chain | 15 | 0.933 | 0.000 | 0.000 | 0.000 | 0 |

**The clean signal: recovery emerged ONLY in `state_literal` (3.2% exact), which got the most Stage 4B records (190 of 364 = 52% of Stage 4B's contribution).** Recipe got 121 records and still 0% recovery — possibly because recipes have higher template-specificity (`Θ(Ω_X) = ...`) that's hard to match exactly even when shape is right.

## Diversity collapse — the cautionary signal

Top 5 modes account for **49.6% of all 280 outputs**:

| Count | Share | (mode template family) |
|---|---|---|
| 53 | 18.9% | top mode (the new "favorite template") |
| 27 | 9.6% | |
| 23 | 8.2% | |
| 21 | 7.5% | |
| 15 | 5.4% | |

The model concentrated harder on a few favorite templates compared to v0.1. Likely cause: with Stage 4B records reinforcing the same 4 categories Wave 2.5 dominates (state_literal + recipe + binary_composition + let_binding), the merged corpus made the "most common surface shape per category" even more common, so the model's per-category go-to template hardened.

Sample evidence from the 12 sample reads:
- Two different rpm_chain prompts → both generated identical `let stageA0_2_0277 = ^0^P; let stageD2_2_0277 = ^0^P_{F2}; ...` (same identifier "0277" in both)
- Two different fractal_sequence prompts → both generated `Phi<2:2:2:2>` (single favorite fractal)
- Diagram-export prompt asking for "struck a chord in operational, wisdom drive" → generated unrelated NoeticCluster

## What v0.2 confirms

1. **The diversity hypothesis is partly right.** Adding real-user prompt diversity DOES move recovery off zero — that's a meaningful directional result.
2. **Volume matters.** 6.5% Stage 4B share isn't enough. The category that got 52% of Stage 4B (state_literal) is the only one showing recovery. Other categories got 0 records from Stage 4B and remain at 0% recovery.
3. **More Stage 4B records is the cheapest next lever.** Generating 1000-2000 more clean records at the Stage 4B pipeline cost ($1.44 per 500) gets us to 15-25% mix share, which is what the original spec recommended.

## What v0.2 reveals as a NEW concern

1. **Diversity regressed.** The 7 → 19% mode-collapse jump means the model is MORE locked-in on specific templates than after v0.1. Throwing more data at a model that's already over-confident may need a different fix (e.g., entropy regularization, dropout on the LM head, temperature scheduling) on top of corpus expansion.
2. **rpm_chain still 0% validity at free-decode** despite 93% TF accuracy — the exposure-bias signature persists. Stage 4B has 0 rpm_chain records and won't help this directly.

## Likely next lever (Codex to call)

**Stage 4B v2 expansion + v0.3 retrain:**
1. Generate ~2000 more Stage 4B records targeting under-represented categories with category-targeted prompts (e.g., "Walk me through a step-by-step recipe for…" to elicit `Θ(Ω) = …`)
2. Mix at 75/25 Wave 2.5 / Stage 4B (or whatever the math gives with ~2400 Stage 4B records)
3. Retain all other v0.1 hparams

Cost: ~$5-7 more API spend (target ~1500-2500 new accepted records). No GPU spend until v0.3 launch.

Alternative levers Codex may prefer:
- **Architecture change** (entropy regularization, dropout tweaks) — addresses diversity collapse but doesn't fix the data-imbalance root cause
- **Targeted prompts for rpm_chain / fractal_sequence / cross_register_omega** — fixes per-category recovery directly
- **Stop, declare partial-win on state_literal**, and use the v0.2 checkpoint for state_literal-only inference

## Cost

| Phase | Wall-time | Cost |
|---|---|---|
| Pre-flight | 1 sec | ~$0.001 |
| Real training | 6.7 min | ~$0.09 |
| Eval | 51 sec | ~$0.01 |
| **Total v0.2** | **~7 min** | **~$0.10** |

Cumulative Stage 4 spend (Stage 4B pilot $1.44 + v0 $0.05 + v0.1 $0.09 + v0.2 $0.10): **~$1.68**.

## Artifacts

In repo:
- `docs/working/stage4a_v02_2026_05_14/eval_report.json` (full eval JSON)
- `docs/working/stage4a_v02_2026_05_14/samples.jsonl` (12 stratified samples)
- `docs/working/stage4a_v02_2026_05_14/samples_view.txt` (human-readable sample dump)
- `docs/working/stage4a_v02_2026_05_14/FINDINGS.md` (this doc)
- `cas-synthetic/data/stage4/track1_v02_merged_2026_05_14.jsonl` (merged corpus committed)

On pod:
- `/workspace/tksCAS/stage4a_v02_20260514T200413Z/` (checkpoint, manifest, train.log, events)
- `/workspace/tksCAS/stage4a_eval_v02_20260514T201152Z/` (eval JSON + samples)

Per the AUTHORIZED entry's "backup IF it promotes" rule: NOT backed up to `D:\tksCAS-archive\` (didn't promote). Available on pod for re-eval / inspection.
