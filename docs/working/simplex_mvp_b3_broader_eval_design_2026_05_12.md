# Simplex MVP B3 — Broader Eval Design (READY for build)

**Date locked:** 2026-05-12
**Status:** Design locked by user; code/build not yet started. Awaiting authorization for SDG generation + eval runner build.
**Scope:** Test whether staged B3 generalizes STAGE_VAR identifier recovery + zero non-rpm leakage on **fresh records** the model has not been trained against.

## Single claim under test

> **Does staged B3 generalize STAGE_VAR identifier recovery on fresh rpm_chain records while avoiding STAGE_VAR leakage on non-rpm records?**

Scope deliberately narrow: this is the property B3 validated on 11 canaries (rpm_chain identifier fidelity + zero leakage). Broader claims (fractal slot routing, OOD leakage, memory compression, multi-turn) are scoped OUT of this eval. They get earned by passing this one first.

## Composition — 24-pack

| Subset | N | Purpose |
|---|---|---|
| rpm_chain identifier suite | **15** | Statistical signal on canonical identifier recovery |
| Non-rpm leakage negatives | **9** | Slot head must NOT fire STAGE_VAR on inputs without stage_vars |
| **Total** | **24** | |

### rpm_chain subset (N=15) — composition specifics

- **Source:** fresh-generated via the existing SDG seed enumerator + EN templating. No samples drawn from `v1_mix_nlgen_train.jsonl` — exact-text overlap check before promoting to the eval pack.
- **Identifier prefix variety:** cover A (≥2 records), D (≥4 records, varied Dn), W (≥4 records, varied Wn), P (≥3 records, varied Pn). Plus at least 2 records mixing prefixes within a single chain.
- **Digit-length variety:** mix of 3-digit, 4-digit, and 5-digit identifier digit-bodies (e.g., `stageA0_4_049` vs `stageA0_4_0049` vs `stageA0_4_00499`). This stresses whether the slot gate releases STAGE_VAR cleanly on different identifier lengths.
- **Chain length:** **mostly 2-stage** (10 records) + **a few 3-stage** (3 records) + **2 records 4-stage**. The 3-4 stage records test slot sustainment across longer identifier-bearing spans.
- **Canonical identifier total:** 15 records × ~2 identifiers per record (some with 3-4 from longer chains) ≈ **30-40 canonical identifiers** for recovery measurement.

### Non-rpm leakage negatives (N=9) — composition specifics

- **Source:** fresh-generated via the existing category-specific SDG enumerators. Same no-training-overlap check.
- **Categories (2-3 each, total 9):**
  - `state_literal` × 2
  - `binary_composition` × 1
  - `recipe` × 2
  - `meta_logic` × 1
  - `cross_register_omega` × 1
  - `fractal_sequence` × 2 (no fractal-specific eval — just confirming slot head doesn't fire STAGE_VAR on fractal inputs)
- **OOD scoped OUT.** Adversarial OOD leakage is a separate suite. This eval gates on in-distribution non-rpm only.

### Fractals — scoped OUT

B3 validated STAGE_VAR (slot id 2). FRACTAL_K_LITERAL (slot id 7) is a separate slot type whose hard-routing behavior has never been tested. Mixing it into the first broader B3 eval would muddy the claim. Fractal hard-routing becomes its own Path D iteration after this eval passes.

## Locked pass criteria

Apply ALL seven at the end of the eval run; pass = all hold.

1. **rpm_chain canonical identifier exact-match recovery ≥ 50%** (first bar) / **≥ 70%** (strong pass). Measured as: across all 30-40 canonical identifiers in target texts, what fraction appear verbatim in the hard_full generated text at the correct position?
2. **hard_full must improve identifier recovery over full.** Both modes can be damage-detector-clean, but the canonical-recovery metric on hard_full must strictly exceed that on full. (Same Gate 4 measurement-instrument lesson from B3: use canonical recovery, not damage_severity.)
3. **Non-rpm `emission_route_counts.copy` = 0** on every non-rpm record. Single non-zero copy on a non-rpm record = falsify.
4. **Non-rpm sustained STAGE_VAR runs = 0**. Specifically: no non-rpm record may have any STAGE_VAR slot-id run of length ≥ 3 in its `slot_type_trace`.
5. **No trivial outputs.** Every record must satisfy `n_tokens_generated ≥ 50` AND `text_len ≥ 100`. Closes the Candidate-A "empty output gaming the detector" loophole.
6. **No catastrophic loops or truncations.** No `repeated_phrase_loop` with `count ≥ 5` and non-function-word phrase. No `truncation.found` flagged on more than 2/24 records (some 128-token tail truncation is expected from max_new_tokens cap).
7. **B3 must not regress pack-level severity vs B2-style LM+slot output.** Measured by running the same 24-pack through B2's `ckpt_final.pt` in `full` decode mode, compute its pack-level `mean_severity`, and require B3's hard_full pack `mean_severity ≤ B2_baseline + 0.10` tolerance. (B2 didn't have copy active, so its outputs lack canonical identifiers — but its prose stability is the floor B3 must hold.)

**Falsify any → broader eval fails.** No anti-tuning retry. Surface for direction on what the failure says about the staged recipe.

## Build plan (sequence of work)

### Step 1 — SDG generation (laptop, ~1-3 hr, $0)

Build `cas-synthetic/scripts/build_broader_b3_eval_pack.py`:
- Reuse existing Path D Wave 1B seed enumerator for CAS expression generation.
- Reuse existing Path D Wave 2 EN templating (sample from non-training paraphrase templates).
- Generate 15 rpm_chain records meeting the variety requirements above.
- Generate 9 non-rpm records (2-3 per category as specified).
- For each generated record, check against `v1_mix_nlgen_train.jsonl`:
  - No exact target_text match.
  - No exact cas_expression match.
  - Records that overlap get regenerated until clean.
- Output: `cas-synthetic/data/eval/broader_b3_eval_pack_2026_05_12.jsonl` (24 records).

### Step 2 — Eval runner (laptop, ~30 min, $0)

Build `cas-native/evaluation/broader_b3_eval_runner.py`:
- Loads `ckpt_final.pt` (B3) and `ckpt_final.pt` (B2 — for criterion 7 baseline).
- Loads `broader_b3_eval_pack_2026_05_12.jsonl`.
- Runs three pipelines on each model:
  - `decode_canary_pack` with `hard_typed_emission=True, copy_confidence_threshold=0.5` → per-record slot_type_trace, emission_route_counts, generated_text, damage_signatures.
  - `decode_canary_pack` with `hard_typed_emission=False` → for the full-vs-hard_full canonical-recovery comparison.
  - `teacher_forced_canary_pack` → per-record `canonical_stage_vars_in_target` and `_in_argmax` counts.
- Computes the seven locked criteria and surfaces pass/fail per criterion.
- Saves: `broader_b3_eval_report.json` (pack-level + per-record) + `broader_b3_eval_findings.md` (human-readable verdict).

### Step 3 — Pod run (~5-10 min wall-clock, ~$0.10 spot)

Push the eval pack + runner to pod, run against B3 ckpt + B2 ckpt, pull results. Postmortem-class workload — no training, just decode + TF eval on 24 records.

### Step 4 — Gate read

Apply the seven locked criteria. Single yes/no verdict. If pass → broader eval validates → next-step direction discussion. If fail → surface what falsified, no retune.

## Cost projection

| Step | Wall-clock | Spot |
|---|---|---|
| SDG generation | 1-3 hr laptop | $0 |
| Eval runner build | ~30 min laptop | $0 |
| Pod run | ~10 min | ~$0.10 |
| **Broader eval total** | **~4 hr** | **~$0.10** |

Cumulative since simplex MVP started: would reach ~$2.86 of $60.

## What this design does NOT do

- Does NOT launch any pod work or any SDG generation before user authorization.
- Does NOT promote B3 to production. v0-rc1 stays canonical.
- Does NOT scope in fractal hard routing, OOD leakage, memory compression, multi-turn, or scale. Each is a separate eval that follows passing this one.
- Does NOT modify B1/B2/B3 checkpoints. They're frozen artifacts being evaluated, not trained further.

## Companion files

- `docs/working/simplex_mvp_candidate_b3_findings_2026_05_12.md` — the 11-canary result this broader eval extends.
- `docs/working/simplex_mvp_staged_training_canonical_recipe_2026_05_12.md` — the recipe being evaluated.
- `docs/future/cas_self_training_recursive_gated_successor_2026_05_12.md` — the long-horizon target gated on this eval passing.
- `cas-synthetic/scripts/build_path_d_v1_mix.py` — existing SDG infrastructure to extend.
