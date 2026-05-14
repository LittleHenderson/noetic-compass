# Stage 4A v0 — Findings (2026-05-14)

**Run dir on pod:** `/workspace/tksCAS/stage4a_v0_20260514T163737Z`
**Eval dir on pod:** `/workspace/tksCAS/stage4a_eval_v0_20260514T164204Z`
**Checkpoint ID:** `33bdaead-f171-4b5b-9bd9-68aecb872f7b`
**Trained from corpus sha256:** `8ced4726bceae5176285a171d33ad6d9f3903c3047c240157fd51265ac3d2954`
**AUTHORIZED entry:** `docs/working/agent_exchange/decisions.md` 2026-05-14T15:00Z, ratified at user "go" 2026-05-14T15:15Z.

## Headline

**Run completed cleanly. Model did NOT promote.** Recovery gate failed (0% exact, 0% normalized), mechanical pass on TF accuracy + validity + load mismatch + 9/10 per-bucket validity. Sample reads show **mode collapse** onto a handful of high-frequency CAS templates regardless of input.

## Training summary

| Metric | Value |
|---|---|
| Wall-time (3 epochs) | ~3 min on A6000 |
| Global steps | 468 |
| Final loss_lm | 0.91 (start: 10.07, monotonic descent) |
| Final loss_structured | 0.0 (intentional — `cas_expression=""` in records) |
| β at end | 0.140 (curriculum was 0.1 → 1.0 over 10K steps; we covered only 4.7%) |
| n_train / n_val | 4,982 / 262 (95/5 deterministic_split, seed 42) |
| Load mismatch on eval | n_missing=0, n_unexpected=0 (strict load PASS) |

## Eval — gates against AUTHORIZED entry

| Gate | Floor | Actual | Status |
|---|---|---|---|
| TF per-token accuracy | ≥ 0.20 | **0.726** | ✅ 3.6× floor |
| Free-decode CAS validity rate | ≥ 0.50 | **0.905** | ✅ 1.8× floor |
| Normalized recovery rate | ≥ 0.10 | **0.000** | ❌ FAIL |
| Per-bucket validity ≥ 0.25 in ≥ 7/10 | 7/10 | **9/10** | ✅ |
| Load mismatch (n_missing, n_unexpected) | 0/0 | **0/0** | ✅ |
| Human sample read | "looks like a CAS-conditioned model trying to write CAS" | mode-collapse pattern | ❌ FAIL |

**Promotion verdict:** REJECT (two gates failed — recovery rate and human sample read).

## Per-grammar-category breakdown

| Category | n | TF acc | Validity | Exact | Norm |
|---|---|---|---|---|---|
| binary_composition | 38 | 0.577 | 1.000 | 0.000 | 0.000 |
| cross_register_omega | 33 | 0.640 | 1.000 | 0.000 | 0.000 |
| diagram_export | 14 | 0.740 | 1.000 | 0.000 | 0.000 |
| fractal_sequence | 28 | 0.492 | 1.000 | 0.000 | 0.000 |
| inversion | 4 | 0.711 | 1.000 | 0.000 | 0.000 |
| let_binding | 21 | 0.837 | 1.000 | 0.000 | 0.000 |
| meta_logic_relation | 37 | 0.684 | 0.946 | 0.000 | 0.000 |
| recipe | 27 | 0.683 | 0.778 | 0.000 | 0.000 |
| rpm_chain | 17 | 0.871 | **0.000** | 0.000 | 0.000 |
| state_literal | 43 | 0.307 | 1.000 | 0.000 | 0.000 |

**Notable:** `rpm_chain` has the highest TF accuracy (87%) but **0% validity** — clear exposure-bias signature. Model knows the rpm_chain shape under teacher-forcing but cannot self-feed without breaking the chain (typecheck errors like "domain descent violated" and "undefined variable" in samples 5/6).

## Per-surface-family breakdown

| Family | n | TF acc | Validity | Exact | Norm |
|---|---|---|---|---|---|
| caret_only | 194 | 0.683 | 0.959 | 0.000 | 0.000 |
| caret_stage | 18 | 0.868 | **0.056** | 0.000 | 0.000 |
| caret_export | 14 | 0.740 | 1.000 | 0.000 | 0.000 |
| phi_fractal | 28 | 0.492 | 1.000 | 0.000 | 0.000 |
| co_form | 6 | 0.667 | 1.000 | 0.000 | 0.000 |
| other | 2 | 0.600 | 1.000 | 0.000 | 0.000 |

Same exposure-bias pattern at the surface level: `caret_stage` (let-stage chains) gets 87% TF accuracy but 5.6% validity on free decode.

## Mode-collapse evidence (from 12 sample reads)

Same generated reply repeats across very different prompts:
- Samples 4, 7, 8, 9, 10 all produced variants of `let judgment_0277 = ^3^O` or just `^3^O` regardless of the input describing felt aversion, composition, set membership, or cardinality.
- Sample 2 (recipe gold) generated `(^3^O|A × ^3^O|T) = ^3^O|Ω_wisdom`.
- Sample 11 (fractal gold `Φ<9:5:7>`) generated `let judgment_027 = ^3^O`.
- Sample 12 (long fractal gold `Phi<5:2:6:7:1:0:5:6>`) generated `(^3^O|A × ^3^O|T) = ^3^O|Ω_wisdom` — same as sample 2 despite radically different prompt.

**Diagnosis:** the model learned a high-frequency-token distribution over the CAS surface vocabulary but did NOT learn to condition emission on the encoder's prompt representation. Free-decode is essentially prompt-independent.

## Likely causes

1. **β curriculum too slow for short run.** Trainer default `--beta-curriculum-steps 10000` ramped β from 0.1 → only 0.140 over 468 steps. The LM loss was scaled by an effective factor of ≤ 14% throughout training. Most gradient signal went to the structured head (which is 0.0 because `cas_expression=""`). The LM head barely got supervised.
2. **Small corpus + 3 epochs.** 4,982 train records × 3 epochs = ~15K example exposures. For an English→CAS mapping with this much surface variation, that's likely under-data.
3. **Templated input distribution.** Wave 2.5 prompts are deterministic-renderer output. The encoder may have collapsed onto a near-singular prompt embedding, making the decoder effectively unconditional.

## Recommended next levers (Codex to pick / sequence)

1. **Lever A — β curriculum fix.** Cut `--beta-curriculum-steps` from 10000 to 200 (or set `--beta-lm-start 1.0` directly). β at 1.0 throughout means LM loss matters from step 1. Cheapest fix; ~3 min retrain.
2. **Lever B — Longer training.** 5-10 epochs instead of 3. Independent of Lever A. ~10-15 min retrain.
3. **Lever C — Bigger LR.** 5e-4 or 1e-3 instead of 2e-4. Risky (may diverge) but warranted given how slowly loss is dropping in the 200-468 step range (1.04 → 0.91 over 268 steps).
4. **Stage 4B kickoff.** External prompt diversity per the 2026-05-14 refined data rule. Wave 2.5 prompts are too templated. HF/Kaggle questions → CAS SDG → SFE gate → mix at 70/30. This is a corpus-side fix and won't be done by an A6000 retrain alone.

Lever A + B combined likely sufficient to clear the 0.10 normalized recovery floor on a v0.1 retrain. Stage 4B is the structural fix for the templated-input problem and feeds Stage 4C.

## Recommendation to user

Retrain v0.1 with Lever A + B combined (`--beta-curriculum-steps 200 --epochs 6`), keeping all other locks intact. ~6-10 min runtime, $1.50 budget. Same evaluator + gates. If v0.1 still fails recovery, kick off Stage 4B (HF questions via SDG) in parallel.

## Run-side artifacts

On pod:
- `/workspace/tksCAS/stage4a_v0_20260514T163737Z/` (467 MB checkpoint + tokenizer + english_bpe + train.log + events + manifest)
- `/workspace/tksCAS/stage4a_eval_v0_20260514T164204Z/` (eval JSON + samples + view txt)

In repo:
- `docs/working/stage4a_v0_2026_05_14/eval_report.json`
- `docs/working/stage4a_v0_2026_05_14/samples.jsonl`
- `docs/working/stage4a_v0_2026_05_14/samples_view.txt`
- `docs/working/stage4a_v0_2026_05_14/FINDINGS.md` (this doc)

NOT backed up to `D:\tksCAS-archive\` per the AUTHORIZED entry's "backup IF it promotes" condition. Per memory `feedback_back_up_successful_runs_imperative.md`, a clean-training-run-but-failed-eval may still be worth archiving for reproducibility — user call.

## Costs

| Phase | Wall-time | Cost |
|---|---|---|
| Pre-flight | 1 sec | ~$0.001 |
| Real training | 3 min | ~$0.04 |
| Eval (262 records) | 49 sec | ~$0.01 |
| **Total** | **~4 min** | **~$0.05** |

Well under the $5 budget cap.
