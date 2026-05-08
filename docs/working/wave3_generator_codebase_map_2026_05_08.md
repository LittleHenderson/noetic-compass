# Path D Wave 3 generator codebase map (2026-05-08)

Purpose: a mini-map of the existing Wave 3 generator code in this repo at the
moment the Wave 3 phase 1 corpus was frozen as `NEEDS_REWORK`, plus the new
Wave 3 v2 module added on 2026-05-08 to fix the four content-preservation
defects the audit caught.

## Inputs

- `cas-synthetic/data/path_d/seeds.jsonl` — 5,802 compiler-validated CAS
  expressions, one per line. Schema: `seed_id`, `task_slot`, `grammar_category`
  (one of `state_literal`, `binary_composition`, `cross_register_omega`,
  `recipe`, `meta_logic_relation`, `fractal_sequence`, `let_binding`,
  `diagram_export`, `rpm_chain`, `inversion`), `expression`, `axes` (noetics /
  domains / drives / registers / operators), and metadata.
- `cas-synthetic/data/path_d/invalids.jsonl` — 5,581 invalid CAS expressions
  paired with their `corrected_form` (the original seed) and a verbatim
  `compiler_error_message`. Schema includes `error_class` ∈ {parse,
  admissibility, rpm, recipe, meta_logic, fractal}.

Both inputs are produced by separate generators (`generate_path_d_seeds.py`,
`generate_path_d_invalids.py`); Wave 3 only consumes them.

## Wave 3 phase 1 — single generator file (unchanged by this PR)

`cas-synthetic/scripts/generate_path_d_wave3_smoke.py` — the only Wave 3
generator. ~1,484 lines. Produces records for all four task slots:

| Slot                      | Model                       | Prompt builder                        | Compiler-loop |
| ------------------------- | --------------------------- | ------------------------------------- | ------------- |
| `cas_to_english`          | claude-haiku-4-5-20251001   | `build_cas_to_english_prompt`         | n/a           |
| `english_to_cas`          | claude-sonnet-4-6           | `build_english_to_cas_prompt`         | up to 3 tries |
| `invalid_to_explanation`  | claude-sonnet-4-6           | `build_invalid_to_explanation_prompt` | n/a           |
| `invalid_to_corrected`    | claude-sonnet-4-6           | `build_invalid_to_corrected_prompt`   | n/a           |

The slot generators share:

- `_PLAIN_LANGUAGE_GUIDANCE` (anti-drift constants — chemistry / counts /
  intensities / level-talk).
- `_COLLOQUIALISM_GUIDANCE` (the 10-Noetic colloquialism map), used only in
  `cas_to_english` per `feedback_use_canonical_colloquialisms_as_operator_aliases`.
- `CostTracker` (USD cap), `AnthropicClient` (sync wrapper, exponential
  backoff), `SampleRecord` dataclass (the per-record JSONL schema), and the
  `run_smoke` round-robin pipeline.

The four content-preservation defects all live in the **prompt-builder**
functions, not in the pipeline scaffolding:

- `build_english_to_cas_prompt` calls `_derive_english_hint`, which embeds the
  source CAS as "reference target (for guidance only — do not paste verbatim,
  render afresh)". The model copies the reference target verbatim ~100% of the
  time.
- `build_invalid_to_corrected_prompt` shows the corrected form alongside the
  invalid one and asks the model to narrate the repair — but does not constrain
  the corrected form to be a minimal edit. When the underlying invalid /
  corrected_form pair has substantial divergence (RPM-class mutations, etc.),
  the narration confabulates "the fix replaces the whole construct" language
  the audit flagged as ~30% unrelated-correction.
- `build_cas_to_english_prompt` does not require numeric coefficient or named
  Ω-target reproduction in the English output (recipe slot drops them).
- `build_cas_to_english_prompt` does not warn the model that fractal `Φ⟨k:k:…⟩`
  k-values are operator indices (the model interprets them as counts).

Both `_PLAIN_LANGUAGE_GUIDANCE` and `_COLLOQUIALISM_GUIDANCE` are correct in
intent but were not enough on their own to guarantee content preservation.
Adding strict per-slot rules and per-slot validators is the v2 fix.

## Wave 3 phase 2 — new module (this PR)

`cas-synthetic/scripts/generate_path_d_wave3_v2.py` — the rewritten generator.
Self-contained. Re-implements the four prompt builders with the audit fixes,
adds five content-preservation validators, and supports an extra Wave 2.5
pre-generation step. Mirrors the phase-1 module's call shape so existing
infrastructure (`CostTracker`, `AnthropicClient`, the round-robin pipeline) is
reused conceptually but with new prompt logic.

Key functions in the v2 module:

- `build_cas_to_english_prompt_v2` — adds explicit coefficient-preservation
  and named-Ω-preservation rules in the recipe path; adds explicit
  k-as-operator-index rule in the fractal path. Returns the same
  `(system, user)` tuple shape as the phase-1 module.
- `build_english_to_cas_prompt_v2` — takes a pre-generated English description
  (read from the Wave 2.5 artifact) and produces a system+user prompt that
  contains ONLY the English description. The system message names the task;
  the user message gives the English plus a "reply with only the CAS
  expression" instruction. No reference target is embedded.
- `build_invalid_to_corrected_prompt_v2` — produces TWO prompts: a "produce
  the corrected expression" prompt and a "narrate the change" prompt. The
  corrected-expression prompt instructs the model to produce the smallest
  possible edit and includes a positive example (single-character fix) and a
  bad example (whole-expression rewrite). The narration prompt references
  the actual minimal change.
- `build_invalid_to_explanation_prompt_v2` — unchanged from phase 1 (the audit
  rated this slot clean; we keep it as-is and re-export it under the v2 name
  for module-symmetry).
- `validate_cas_to_english_recipe_preservation` — extracts numeric
  coefficients (regex `\d+(?:\.\d+)?\s*\*`) and named Ω targets from the
  source CAS, requires each to surface in the English output. Returns a
  `(passed: bool, missing_items: list[str])` tuple.
- `validate_cas_to_english_fractal_k_indices` — extracts k-indices from
  `Φ⟨…⟩` / `Phi<…>`, requires the corresponding operator name OR canonical
  colloquialism to appear in the English output. Operates on a per-k basis.
- `validate_anti_copy_english_to_cas` — tokenizes the prompt (system+user)
  and the generated CAS; rejects if the generated CAS is byte-equal to any
  contiguous substring of the prompt.
- `validate_invalid_to_corrected_jaccard` — tokenizes the invalid expression
  and the model-produced corrected expression, computes Jaccard, rejects if
  <0.6.
- `validate_invalid_to_corrected_compiles` — runs the model's corrected
  expression through the compiler.

Wave 2.5 pre-generation entrypoint:

- `generate_wave3_step2_5_english_descriptions` (also exported as a script
  `cas-synthetic/scripts/generate_wave3_step2_5_english_descriptions.py`) —
  iterates over a stratified sample of seed CAS expressions, calls the model
  with `build_cas_to_english_prompt_v2`, validates each output with the
  cas_to_english recipe + fractal validators, writes accepted records to
  `cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_<ts>.jsonl`.

## Per-record traceability fields (new)

Every record produced by the v2 module carries these fields in addition to
the phase-1 schema:

- `prompt_template_version` — string, e.g. `"wave3_v2_2026_05_08"` for the
  rewritten prompts.
- `validators_run` — list of validator names invoked on this record.
- `validators_passed` — list of validator names that returned True.
- `validators_failed_reasons` — dict mapping validator name → human-readable
  reason for the failure (omitted for accepted records).
- `seed_id` (already present as `source_id`) — preserved.
- `source_cas` — the source CAS expression, surfaced as a top-level field
  (was previously embedded inside the prompt only). Required by the audit
  pack so faithfulness review can run without dropping into the raw prompt.
- `generated_at` — UTC ISO8601 timestamp.

## Test coverage

`cas-synthetic/tests/test_path_d_wave3_v2.py` (new) — unit tests for each
validator, prompt builder, and the Wave 2.5 stub. Designed to run without
calling any API; uses hand-constructed example CAS expressions and
hand-constructed model outputs to exercise accept/reject paths.

`cas-synthetic/tests/test_path_d_wave3_smoke.py` (unchanged) — phase-1 tests
remain green; the v2 module imports / re-exports the phase-1 prompt builders
under their original names where the v2 builder is identical (only
`build_invalid_to_explanation_prompt`).

## What's NOT in the v2 module

- Anthropic API calls. The v2 module is a library + CLI; this PR's deliverable
  is the prompt rewrites + validators + dry-run smoke, not paid generation.
  The user runs paid generation as a separate decision after reviewing this
  work.
- The phase-1 file `generate_path_d_wave3_smoke.py` is left untouched. The
  audit corpus is locked, the phase-1 pipeline keeps working for any
  reproducibility check.
- A full content-preservation scorer for the post-hoc audit pipeline. The v2
  module's validators run at generation time and reject records inline; a
  separate scorer for already-accepted corpora is follow-on work.
