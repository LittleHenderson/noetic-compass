# Stage 4A v0.1 — Findings (2026-05-14)

**Run dir on pod:** `/workspace/tksCAS/stage4a_v01_20260514T170228Z`
**Eval dir on pod:** `/workspace/tksCAS/stage4a_eval_v01_20260514T171317Z`
**Checkpoint ID:** `3c7e9021-b2d7-41fe-a135-d83594afe8aa`
**Trained from corpus sha256:** `8ced4726bceae5176285a171d33ad6d9f3903c3047c240157fd51265ac3d2954` (same as v0)
**AUTHORIZED entry:** `decisions.md` 2026-05-14T17:00Z, ratified at user "go" 2026-05-14T17:10Z

**Operational note:** SSH disconnect during training due to user-side power outage. Training was launched via `nohup` and detached from the SSH session, so it ran to completion uninterrupted. RunPod side fully unaffected.

## Headline

**Lever A + B combined (β curriculum 200, epochs 6) worked partially.** Mode collapse substantially reduced (top mode 11% vs v0's much higher concentration), unique-output count tripled, TF accuracy + validity both improved. **But the recovery gate still fails at 0%** and unique-output ratio (22.9%) falls below the 0.40 floor. **Model still does NOT promote.**

## v0 → v0.1 deltas

| Metric | v0 | v0.1 | Δ |
|---|---|---|---|
| TF per-token accuracy | 0.726 | **0.773** | +4.7 pp |
| Free-decode validity rate | 0.905 | **0.927** | +2.2 pp |
| Exact recovery | 0.000 | 0.000 | — |
| Normalized recovery | 0.000 | 0.000 | — |
| Top mode count | (not measured) | 29 / 262 | new metric |
| **Mode collapse ratio** | (visibly high in samples) | **0.111** | new metric |
| **Unique output ratio** | (visibly ~0.15) | **0.229** | new metric |
| Per-bucket validity ≥ 0.25 buckets | 9/10 | 9/10 | — |
| rpm_chain TF | 0.871 | 0.929 | +5.8 pp |
| rpm_chain validity | 0.000 | 0.000 | — (exposure bias persists) |
| Final loss_lm | ~0.91 | ~0.6-0.7 | improved |

## Promotion gates against v0.1 AUTHORIZED entry

| Gate | Floor | v0.1 | Status |
|---|---|---|---|
| TF per-token accuracy | ≥ 0.20 | 0.773 | ✅ 3.9× over |
| Free-decode validity rate | ≥ 0.50 | 0.927 | ✅ 1.85× over |
| Normalized recovery rate | ≥ 0.10 | **0.000** | ❌ FAIL |
| Per-bucket validity ≥ 0.25 in ≥ 7/10 | 7/10 | **9/10** | ✅ |
| **Unique output ratio** | **≥ 0.40** | **0.229** | ❌ FAIL |
| **Mode-collapse ratio** | **≤ 0.15** | **0.111** | ✅ |
| Load mismatch | 0/0 | 0/0 | ✅ |
| Human sample read | "model trying to write CAS" | category-aware shape selection, no input mapping | mixed |

**Promotion verdict:** REJECT. Recovery still 0%, unique-output ratio 0.229 < 0.40 floor.

## Top 5 modes (29 + 18 + 14 + 14 + 11 = 86 / 262 = 33% of records collapse to top 5)

| Count | Share | Normalized text |
|---|---|---|
| 29 | 11.1% | `(^4^C|A×^4^C|f)=^4^C|Ω_self` |
| 18 | 6.9% | `Θ(Ω_translation_22)=1*^5^O+1*^3^O→Ω_translation_22+0.1*Λ·Ω_translation_side` |
| 14 | 5.3% | `^5^C_{F1}|A` |
| 14 | 5.3% | `Φ⟨6:6⟩` |
| 11 | 4.2% | `letstageA0_3_0266=...` (truncated rpm_chain skeleton) |

Each top mode is a different surface family (cross_register_omega, recipe, state_literal, fractal, rpm_chain) — meaning the model has converged to **one "favorite template" per category** instead of v0's single template across all categories.

## What v0.1 learned vs v0

**v0.1 gain:** category-conditional shape selection. The encoder now distinguishes "this English is asking for a recipe" vs "asking for an rpm_chain" vs "asking for a fractal" and emits the matching shape. From samples:

- Sample 1 (gold = cluster of 3 Noetics): v0.1 emits a cluster of 4 Noetics, gold-adjacent. v0 emitted any random shape.
- Sample 2 (gold = recipe `Theta(Omega_decision)`): v0.1 emits `Theta(Omega_translation)`, same shape different specifics. v0 emitted a cross-register omega.
- Sample 5/6 (gold = rpm_chain): v0.1 emits a properly-formatted rpm_chain skeleton with correct `stageA0/D/W/P` slots — only fails at the final stage-reference token where it gets the identifier name wrong, leading to "undefined variable" or "domain descent violated" compile errors.

**v0.1 still missing:** input-content mapping. The model knows "recipe shape" but not "this recipe for that prompt." Free-decode picks one of ~60 plausible templates per surface family, not the specific gold CAS for the specific English prompt.

## Diagnosis

Codex's pre-stated trigger fires: **"If v0.1 still collapses, then Stage 4B external-question SDG becomes the next justified move."**

The β curriculum was correctly diagnosed as a real limiter — Lever A clearly lifted the LM head signal and let the model learn category-shape mapping that v0 couldn't. But Lever A+B cannot fix what v0.1's residual reveals: **the Wave 2.5 input distribution is too templated for input-content mapping to emerge**. Prompts have shape `"Let X name a foundational thought, Y name…"` or `"A Noetic in domain D, driven by Drive…"` — the encoder ends up modeling input *category* (which template), not input *content* (which specific identifiers).

The Wave 2.5 generator emits English by walking pre-defined sentence templates over the source CAS. The English carries enough info to identify the CATEGORY, but not enough natural language signal to push the encoder to learn fine-grained content mapping. External diversity (HF/Kaggle questions phrased many ways) is the structural fix.

## Recommended next step

**Stage 4B kickoff.** Pull questions from a license-clean external Q&A source (OASST1 Apache 2.0 or Natural Questions short), run the existing path_d SDG pipeline to generate CAS answers, SFE-filter, then mix at 70/30 with Wave 2.5 for v0.2 retrain.

Out of scope for this entry — needs its own AUTHORIZED entry.

## Cost

| Phase | Wall-time | Cost |
|---|---|---|
| Pre-flight | 1 sec | ~$0.001 |
| Real training | 6.2 min | ~$0.08 |
| Eval | 47 sec | ~$0.01 |
| **Total** | **~7 min** | **~$0.09** |

Cumulative Stage 4A spend (v0 + v0.1): ~$0.14. Well under $5 cap.

## Run artifacts

On pod:
- `/workspace/tksCAS/stage4a_v01_20260514T170228Z/` (467 MB checkpoint + tokenizer + bpe + train.log + events + manifest)
- `/workspace/tksCAS/stage4a_eval_v01_20260514T171317Z/` (eval report + samples)

In repo:
- `docs/working/stage4a_v01_2026_05_14/eval_report.json`
- `docs/working/stage4a_v01_2026_05_14/samples.jsonl`
- `docs/working/stage4a_v01_2026_05_14/samples_view.txt`
- `docs/working/stage4a_v01_2026_05_14/FINDINGS.md` (this doc)

Not backed up to `D:\tksCAS-archive\` per the "backup IF it promotes" rule. Same caveat as v0 findings.
