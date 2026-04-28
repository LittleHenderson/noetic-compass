# Level 2 Synthetic Dataset

Documentation for the CAS-Native v2 first-training-run baseline dataset.

## Dataset Version

- **Identifier**: Level 2 v1
- **Commit**: `74e5350` (parent: `c61a3fe`)
- **Generated**: 2026-04-28
- **Dataset file**: `cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl` (6.92 MB, 10,000 examples)
- **Validator metrics**: `cas-synthetic/data/level2_scaffold/level2_full_10k_metrics.json`
- **Sidecar metrics**: `cas-synthetic/data/level2_scaffold/level2_full_10k_sidecar_metrics.json`
- **Replay command**: `python cas-synthetic/scripts/compute_sidecar_metrics.py cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl`

The dataset paths sit under `level2_scaffold/` per `cas-synthetic/.gitignore` policy (`!data/level2_scaffold/.gitkeep` keeps the dir tracked while gitignoring its contents). The committed dataset and metrics are tracked via `git add -f` overrides in commit `74e5350`.

## Generator Commit Chain

Day 2 sprint produced the dataset through six generator commits and two infrastructure commits:

| Commit | Layer | Description |
|---|---|---|
| `e8cd9dd` | generators | 4-bucket notation fix (v75/v77_rule_four register order; v77_omega Unicode `× Ω_*`; v76_production `Θ Ω_ →` + real state literals) |
| `c054c9b` | generators | meta_logic operand randomization (parametrized templates with 12 typed slot kinds across 7 axes) |
| `ede9e22` | generators | v77_omega diversity expansion (registry 2→8 entries, drive-arity-aware drive sampling, register-subset sampling) |
| `b9d5a28` | generators | v77_rule_four diversification (full 10-Noetic / 4-Domain / 7-Drive / variable register subsets, mixed `+` co-presence and `×=Ω_*` shapes) |
| `cbd9bab` | generators | v75_register diversification (paired co-presence `+` primary diversifier + 5 single-state form variants) |
| `c61a3fe` | generators | v75_register weight recalibration (small noetic-only/drive-only pools sampled at-or-near pool size) |
| `40e11d2` | registry | omega_registry expanded to 12 admitted Ω entries spanning Noetics 0-9 |
| `ec09594` / `edc09fa` | validator | post-generation validator + Windows cp1252 stdout UTF-8 fix |
| **`74e5350`** | **dataset** | **10K dataset commit + sidecar metrics + replayable compute script** |

## Bucket Structure

The Level 2 mix controller produces six buckets at the recalibrated **20/25/15/20/10/10** ratios (corrected from the original directive draft of 25/22/13/18/8/14, which conflated v7.6 production with v7.7 Rule 4 as a single bucket).

| Bucket | Allocation | n=10000 | What it teaches | Example expression |
|---|---|---|---|---|
| `v74_baseline` | 20% | 2000 | CAS notation foundation: bare state literals over the 10×4×7=280 unique `^N^D_{Fk}` combinatoric space | `^6^E_{F1}` |
| `v75_register` | 25% | 2500 | Register-tagged states with paired co-presence and single-state form variants | `^6^E_{F1}\|f + ^6^P_{F2}\|E` |
| `v77_rule_four` | 15% | 1500 | Rule 4 admissibility patterns (compliant `+` co-presence and `×=Ω_*` named-emergent forms) plus deliberate violations (~18% of bucket) for negative training | Compliant: `(^4^E_{F7}\|T × ^4^E_{F7}\|f) = ^4^E\|Ω_attunement` · Violation: `^2^C_{F3}\|E × ^2^C_{F3}\|f × ^2^C_{F3}\|A` (no emergent — Rule 4 violation by design) |
| `v77_omega` | 20% | 2000 | Cross-register integration with named emergents drawn from the 12-entry omega_registry | `(^8^C_{F7}\|A × ^8^C_{F5}\|f × ^8^C_{F2}\|T) = ^8^C\|Ω_invocation` |
| `v76_production` | 10% | 1000 | Production semantics with weighted multi-Noetic prerequisites, Gaussian coefficient noise, and optional Λ-prefixed leakage products | `Θ(Ω_pattern_entrainment_learning) = 0.48*^1^C_{F1}\|A + 1.96*^7^C_{F7}\|A + 0.99*^5^C_{F1}\|f → Ω_pattern_entrainment_learning + 0.15*Λ·Ω_evaluative_drift` |
| `meta_logic` | 10% | 1000 | Typed set theory over CAS objects (Pullback as finite meet, CoverOf, PartitionOf, set ops `∪ ∩ ∖`, membership/subset/superset, cardinality, Coordinate, Product) | `Pullback(NoeticCluster{^3, ^6, ^7}, NoeticCluster{^3, ^5})` · `StateCluster{^7^O} ∪ StateCluster{^7^E, ^9^C}` |

### v75_register internal sampling weights

Within v75_register's 2500-example allocation, six form families are sampled with these weights (recalibrated in `c61a3fe` to avoid small-pool saturation):

- 30% — compound `^N^D_{Fk}|R` (1120-form pool)
- 55% — paired co-presence `S₁ + S₂` over distinct states (~1.25M-pair pool, primary diversifier)
- 6% — compound-no-drive `^N^D|R` (160-form pool)
- 2% — Noetic-only `^N|R` (40-form pool)
- 2% — Drive-only `F_k|R` (28-form pool)
- 5% — independent-register `^N^D_{Fk|R_d}|R_n` (4480-form pool, edge case)

Scope distinction enforced: v75 paired co-presence uses **distinct states** (different Noetic OR Domain OR Drive). Same-Noetic cross-register stays in v77_rule_four / v77_omega per Rule 4 / Clarification 10.

## Validation Methodology

- Every example's `cas_expression` was piped through `api/notation/compiler.py::compile_expression` before inclusion.
- Per-bucket pass rates are checkpointed in `level2_full_10k_metrics.json`.
- Dataset-level halt-and-report criterion: any non-rule_four bucket dropping below 100% pass rate.
- v77_rule_four deliberate violations are labeled `is_valid=false, distance_to_valid > 0` and round-trip as the supervised-loss signal for the constraint-learning objective.
- **0 retries, 0 fallbacks** were observed during 10K generation. The retry-with-fallback instrumentation (`self.compile_retries`, `self.compile_fallbacks` on each generator) reported clean across the full run.

## Coverage Characteristics

### Axis coverage (all complete)

- **Noetics**: `^0` through `^9` — all 10 present
- **Domains**: P, C, E, O — all 4 present
- **Drives**: F1 through F7 — all 7 present
- **Registers**: T, A, f, E — all 4 present
- **Foundations**: Foundation_1 through Foundation_7 — all 7 present (concentrated in `meta_logic` bucket via `CoverOf` / `PartitionOf` constructors)

### Per-bucket dupe redundancy

| Bucket | Redundancy | Notes |
|---|---|---|
| v76_production | 0.00% | Gaussian coefficient noise on every emission — every example unique |
| v77_rule_four | 2.13% | Phase 2.5 diversification (down from 38.5% baseline) |
| v77_omega | 11.90% | Phase 2.5 registry expansion + drive/register randomization |
| v75_register | 12.32% | Phase 2.6 paired co-presence + form variants (down from 19.96%) |
| meta_logic | 15.30% | Parametrized templates; small-cardinality constructs (e.g. `^N ∈ Noetics`) saturate inherently |
| v74_baseline | 32.80% | Structurally bounded — 280 unique combos × 7.1 saturation at n=2000 (intentionally untouched; bare state-literal repetition is benign for vocabulary learning) |

**Total dataset duplicates: 1480 extra copies (14.8% of dataset)**, distributed primarily in v74_baseline. v77_rule_four — the constraint-learning bucket where duplicates would bias the model toward memorization — is at 2.13%.

### Compilation pass rate

- **Overall: 97.27%** (9727 / 10000)
- **Per-bucket**: v74_baseline 100%, v75_register 100%, v76_production 100%, v77_omega 100%, meta_logic 100%, v77_rule_four 81.8% (273 deliberate violations)

### Cross-bucket Noetic Jaccard

All bucket pairs: Jaccard similarity = 1.0. Every bucket spans all 10 Noetics; specialization is in form-shape, not Noetic identity.

## Schema

Each line in `level2_full_10k.jsonl` is a single JSON object with this structure:

```json
{
  "prompt": "A data scientist seeing a suspicious pattern in the logs must act with a clear register.",
  "response": "A data scientist seeing a suspicious pattern in the logs gravitates toward what speaks to them, at the level of action, with a felt sense of meaning and direction.",
  "cas_expression": "^2^O_{F3}|T",
  "scores": {
    "operator_scores": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "domain_scores": [0.0, 0.0, 0.0, 1.0]
  },
  "register_labels": [
    {"position": 0, "register": "T"}
  ],
  "_meta": {
    "bucket": "v75_register",
    "is_valid": true,
    "violation_type": null,
    "distance_to_valid": 0.0
  }
}
```

### Field reference

| Field | Type | Meaning |
|---|---|---|
| `prompt` | string | Natural-language input that motivates the CAS expression. Generated via per-bucket prompt templates with slot interpolation. |
| `response` | string | Natural-language explanation that mirrors what the CAS expression encodes. The model learns to map prompt+response context to the CAS expression. |
| `cas_expression` | string | The compiler-validated CAS expression. **The primary supervised target.** |
| `scores.operator_scores` | array[10] of float | One-hot indicator over the 10 Noetics (`^0` through `^9`) extracted from the expression. |
| `scores.domain_scores` | array[4] of float | One-hot indicator over the 4 Domains (P, C, E, O) extracted from the expression. |
| `register_labels` | array of `{position: int, register: string}` | Per-operand register annotations. Empty for v74_baseline (register-free). |
| `_meta.bucket` | string | Source bucket: `v74_baseline`, `v75_register`, `v77_rule_four`, `v77_omega`, `v76_production`, `meta_logic`. |
| `_meta.is_valid` | bool | True for compiler-valid examples. False for v77_rule_four deliberate violations. |
| `_meta.violation_type` | string \| null | Violation taxonomy label (e.g. `same_noetic_cross_no_emergent`) when `is_valid=false`. |
| `_meta.distance_to_valid` | float | Numeric distance from the violation to the nearest valid form. 0.0 for valid examples. |

Some buckets carry additional fields (e.g. v77_omega adds `omega_labels`, v76_production adds `production_target`). See `cas-synthetic/generator/base.py::GeneratedExample.to_dict` for the full per-bucket schema.

## Reproducibility

| Element | Value |
|---|---|
| Random seed | 42 (passed via `--seed 42` to `generate_level2`) |
| Generator config | `cas-synthetic/mix_controller/level2_mix.py::Level2MixConfig` defaults |
| Mix ratios | 20/25/15/20/10/10 across (v74_baseline, v75_register, v77_rule_four, v77_omega, v76_production, meta_logic) |
| Wall-clock generation | ~3.08 seconds (template-only mode, no LLM provider invoked) |
| Wall-clock validation | ~9 seconds for 10K examples |
| Python | 3.12+ recommended (compiler module uses dataclass features) |
| Key dependencies | `pyyaml` (templates), no external network calls |

### Replay generation

```bash
cd C:/Users/wakil/OneDrive/Desktop/tksCAS
python -m cas_synthetic.scripts.generate_level2 --n 10000 --seed 42 \
    --output cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl
```

### Replay validation

```bash
python cas-synthetic/scripts/validate_level2_dataset.py \
    cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl
```

### Replay sidecar metrics

```bash
python cas-synthetic/scripts/compute_sidecar_metrics.py \
    cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl
```

## Known Limitations

- **v74_baseline 32.80% redundancy is structural.** The bucket emits bare `^N^D_{Fk}` over 10×4×7=280 unique combos; at n=2000 birthday-paradox produces ~700 collisions regardless of generator quality. Repetition of bare state literals is benign for vocabulary acquisition; it does not bias the model toward memorization of constraints.
- **`meta_logic` bucket conservative on natural-language trigger discipline.** Idea Atlas captures with set-theoretic prose now produce typed meta-logic via `notation_synthesizer.py`, but the trigger vocabulary requires explicit set-reference language. Vague prose falls through to v7.4-v7.7 emission.
- **ASCII keyword aliases not universally admitted.** Only `union`, `intersect`, `setminus`/`difference`/`diff`, `in`, and `subseteq` have ASCII aliases in the compiler grammar. `∅`, `∉`, `⊂`, `⊃`, `⊇` require Unicode forms — the dataset emits Unicode for these throughout.
- **`NoeticSet`/`StateSet` exemplars** depend on `cas-native/model/meta_logic_constructs.py::CONSTRUCT_SPECS` enumeration. The constructs are present in compiler grammar AND in CONSTRUCT_SPECS as of commit `ce8dee4`, but symbolic test collection in no-torch environments is blocked because `cas_native.model.__init__` eagerly imports torch.nn. Optional follow-up: decouple symbolic-only construct imports from the neural stack.
- **No conversational layer (Level 3) yet.** Level 2 is sentence-pair training data (single prompt → single response → single CAS expression). Multi-turn conversational training is deferred to Level 3.

## Intended Use

| Tier | Purpose |
|---|---|
| Primary | First CAS-Native v2 training run baseline (this dataset replaces all earlier Level 1 / pre-meta-logic Level 2 candidates) |
| Secondary | Regression testing for compiler grammar changes — every example is a known-valid (or known-invalid-with-rationale) compile target |
| Tertiary | Reference dataset for Paper 1 (Categorical Hutchinson Theory) reproducibility section — the generator chain is fully traceable through the eight commits listed above |

## Top tokens (frequency across the dataset)

### Top-5 state literals

| Literal | Count |
|---|---|
| `^3^P` | 1193 |
| `^5^P` | 1090 |
| `^2^C` | 1051 |
| `^6^O` | 984 |
| `^1^C` | 948 |

### Top-5 named emergents

| Ω name | Count |
|---|---|
| `Ω_invocation` | 238 |
| `Ω_clarity` | 234 |
| `Ω_witness` | 234 |
| `Ω_refusal` | 233 |
| `Ω_genesis` | 230 |

Even spread across the 12 admitted registry entries — no single Ω dominates.
