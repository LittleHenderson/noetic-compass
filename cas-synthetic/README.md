# CAS Synthetic Data Generator — Level 2 Scaffold

Generates training data for the CAS-Native v2 model across CAS versions 7.4 through 7.7.

## Architectural decision (Option 2 — fresh at repo root)

Inspected `noetic-compass-scaffold/noetic-compass/cas-native/data/` in Phase 1. That pipeline is working v7.4 (compiler-validated expressions, template and LLM English generation, round-trip hallucination verifier) but emits a pre-Level-2 schema: `{id, cas_expression, english_text, scores, compilation}`. It has no register annotation, no `Omega_*` awareness, no production semantics, no Rule 4 checks, and no mix controller. Extending it would have required rewriting most of it and diverging the existing v7.4 artifacts.

Chose Option 2: fresh `cas-synthetic/` at repo root implementing the authoritative Level 2 schema from `noetic-compass-scaffold/noetic-compass/cas-native/training/data_format.md` end-to-end. The old pipeline is preserved untouched as a historical v7.4 artifact; if the mix controller ever needs its rich template bank, a thin adapter can be added later.

## Directory layout

```
cas-synthetic/
  generator/        — v7.4, v7.5, v7.6, v7.7 generators (streaming, seedable)
  templates/        — YAML templates (structural correctness per version)
  llm_interface/    — Claude, OpenAI, Local paraphrase providers
  validation/       — schema / Rust / composite validators
  mix_controller/   — 30/25/15/20/10 weighted mixture controller
  scripts/          — generate, validate, inspect
  tests/            — 40+ pytest tests
  data/level2_scaffold/ — git-ignored output directory
```

## Mix ratios (Level 2, locked)

| Bucket | Fraction | Example at n=10,000 |
|---|---|---|
| v7.4 baseline (Noetic × Domain) | 30% | 3,000 |
| v7.5 register (single register per state) | 25% | 2,500 |
| v7.7 Rule 4 (compliant + 20% violations) | 15% | 1,500 |
| v7.7 Ω_* named emergent | 20% | 2,000 |
| v7.6 production semantics | 10% | 1,000 |

Within the v7.7 Rule 4 bucket, 20% of examples are deliberate `same_noetic_cross_no_emergent` violations labeled `is_valid=false, distance_to_valid > 0`. The remaining 80% are compliant — either `+` co-presence or `×` with a named emergent result drawn from `cas-native/config/omega_registry.yaml`.

## Running

Generate a 10K dataset:

```
python -m cas_synthetic.scripts.generate_level2 --n 10000 \
    --output cas-synthetic/data/level2_scaffold/level2_10k.jsonl \
    --seed 42
```

Inspect samples:

```
python -m cas_synthetic.scripts.inspect_sample cas-synthetic/data/level2_scaffold/level2_10k.jsonl --n 5 --bucket v77_omega
```

Validate an existing dataset:

```
python -m cas_synthetic.scripts.validate_dataset cas-synthetic/data/level2_scaffold/level2_10k.jsonl
```

## LLM provider configuration

Set one of these environment variables to enable paraphrase augmentation:

- `ANTHROPIC_API_KEY` — uses Claude (model: `claude-3-5-sonnet-latest`)
- `OPENAI_API_KEY` — uses OpenAI (model: `gpt-4o-mini`)
- `LOCAL_MODEL_ENDPOINT` — OpenAI-compatible local endpoint (llama-server, vLLM, TGI, ...)

When no keys are configured, the scaffold falls back to template-only generation. This is the default mode for the Level 2 smoke test.

## Tests

40+ tests across:

- `test_base.py` — abstract class interface
- `test_v74_generator.py`, `test_v75_generator.py`, `test_v77_rule_four_generator.py`, `test_v77_omega_generator.py`, `test_v76_production_generator.py` — per-version invariants
- `test_schema_validation.py` — data_format.md conformance
- `test_rust_validator.py` — integration with the vendored cas_engine 0.1.1 wheel
- `test_composite_validator.py` — semantic coherence
- `test_mix_controller.py` — ratio + RNG reproducibility + checkpoint/resume
- `test_level2_end_to_end.py` — 100-example sample end-to-end

Run with:

```
pytest cas-synthetic/tests/
```

## Extending Ω_*

Architecture is registry-based. To add a new `Omega_*` name:

1. Add a row to `cas-native/config/omega_registry.yaml` with a fresh `slot`.
2. Add a corresponding Appendix I entry in `FULL_MANUSCRIPT.md`.
3. Add scenario lines to `templates/v77_omega_templates.yaml` under `omega_scenarios[<name>]`.

No generator code change is required — `V77OmegaGenerator` reads the registry and parses the derivation string at runtime.

## Level 3 roadmap (deferred)

- External data cleaning (incident database integration, web-scraped scenario extraction)
- Larger-scale validation (10K-example Rust Rule 4 sweep, yield computation on every production example)
- Additional providers (Gemini, Cohere, DeepSeek)
- Multiprocessing-based parallel generation (Level 2 is sequential; hooks already in mix controller)
- Round-trip verification (feed generated text back through signal analyzer to catch LLM hallucination)
- Additional Ω_* as Appendix I admits them
- Mix ratio tuning from training telemetry (current ratios frozen for Level 2)

## Authoritative references

- Per-example schema: `noetic-compass-scaffold/noetic-compass/cas-native/training/data_format.md`
- Ω_* registry: `noetic-compass-scaffold/noetic-compass/cas-native/config/omega_registry.yaml`
- ADR chain: `docs/architecture/cas_native_v2_adrs.md`
- Foundational clarifications: `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` (Clarifications 1, 8, 9, 10)
- Rust engine wheel: `noetic-compass-scaffold/noetic-compass/cas-native/tests/_vendor/cas_engine/` (version 0.1.1)
