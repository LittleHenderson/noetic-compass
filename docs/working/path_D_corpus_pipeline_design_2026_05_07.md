# Path D — Corpus Pipeline Design (sprint kickoff)

**Date:** 2026-05-07
**Status:** Design memo. Translates Path D §10 open questions into a deliverable graph with dependencies and an execution plan.

## 1. Frame

Path D specifies a compiler-fluency curriculum (six tasks) plus contrastive readout supervision over compiler-validated samples. To produce that corpus we need a generation pipeline that:

1. Enumerates compiler-valid base CAS objects across the full grammar.
2. Produces controlled variants of each base for contrastive supervision.
3. Generates invalid CAS in instructive ways (syntax errors, semantic admissibility failures, RPM violations) for the repair tasks.
4. Annotates every CAS object with natural-language paraphrase + compile trace.
5. Validates every sample against the compiler before it enters the corpus.
6. Aggregates everything into a training-ready JSONL with full provenance.
7. Uses an expanded tokenizer that covers the full grammar surface forms (closes the meta_logic 14-token vocab gap).

This memo specifies the pipeline as **eight deliverable buckets**, identifies their dependencies, and proposes a four-wave execution order.

## 2. Eight deliverables, with dependencies

| ID | Deliverable | Output | Depends on |
|---|---|---|---|
| **A** | Tokenizer expansion | `english_bpe_v2.json` with all CAS surface forms as single tokens | (none) |
| **B** | Seed CAS object enumerator | `seeds.jsonl` (~6K compiler-valid base objects spanning the full grammar) | (none) |
| **C** | Fiber/marginal variation transforms | `variants.jsonl` (contrastive variants per seed: drive intensity / register / operation context perturbations) | B |
| **D** | Invalid-CAS generator | `invalids.jsonl` (controlled mutations producing parse failures, admissibility failures, RPM violations) | B |
| **E** | NL annotation pipeline | `cas_to_english.jsonl` + `english_to_cas.jsonl` (Claude-generated paraphrases, compiler-validated) | A + B + C |
| **F** | Compile-trace generator | `compile_traces.jsonl` (parse tree, AST, admissibility verdict, RPM result, fractal canonical form) | B |
| **G** | Corpus aggregator | `path_d_corpus_v1.jsonl` (training-ready, six-task labeled, full provenance) | A–F |
| **H** | Corpus eval / sanity check | Coverage stats, compiler-validation rate, per-task slot distribution | G |

**Wave order:**

- **Wave 1 (parallel, foundational):** A (tokenizer), B (seed enumeration). Both independent; both unblock subsequent waves.
- **Wave 2 (parallel after Wave 1):** C (variation), D (invalid generation), F (compile-trace generation). Three independent tracks consuming B's output.
- **Wave 3:** E (NL annotation). Requires A + B + C; uses Claude API for paraphrases. This is the most expensive wave (API spend; budget needed).
- **Wave 4:** G (aggregator) → H (corpus eval).

## 3. Volume and budget targets

Per the v0 50K dialogue corpus baseline + the six compiler-fluency tasks + contrastive variation:

- Seed enumeration (B): ~6K base CAS objects (1K per task slot)
- Contrastive variants (C): ~3 variants per seed → 18K
- Invalid-CAS samples (D): ~6K
- Compile-trace targets (F): ~6K (one per seed)
- NL annotations (E): ~30K paraphrase pairs (CAS↔EN both directions; ~15K per direction)
- **Total corpus (G):** ~60K compiler-validated samples

**Budget for Wave 3 (NL annotation, Claude API):** estimate based on B-1 50K dialogue cost ($153.26) + adjustment for shorter outputs. Probably $80-150 for 30K paraphrase pairs at ~200 tokens average reply. Confirm before firing.

## 4. The seven-category coverage requirement

Per memory `feedback_cas_token_enum_must_include_metalogic_and_fractals.md`, every deliverable that enumerates CAS surface tokens MUST cover all seven categories:

1. State literals (`^N`, `^N^D`)
2. Drive subscripts (`F[1-7]`, `_{F_k}`)
3. Register tags (single `|T/A/f/E` + multi-register `|⟨...⟩`)
4. Operators (`+`, `×`, `→`, `∘`, `=`, `Ω`, named emergents)
5. Production recipes (`Θ` + coefficients + arrows)
6. Meta-logic constructors (`NoeticCluster`, `StateSet`, `RelationCluster`, `Tuple`, `Coordinate`, `Product`, `CoverOf`, `PartitionOf`, set ops `∪ ∩ ∖`, `let` bindings, `∈`, `⊆`)
7. Cognitive Fractal angle-bracket sequences `⟨k₁:k₂:⋯:kₙ⟩` + composition operators

Any deliverable producing fewer than seven categories is incomplete. Compiler at `api/notation/compiler.py` is authoritative; grep it when in doubt.

## 5. Compiler-in-the-loop validation

Every produced sample round-trips through `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`. Failed parses are rejected. Failed admissibility checks (RPM violations, register multiplicity violations, recipe stoichiometry violations) are either rejected (for "valid CAS" slots) or kept (for "invalid CAS" slots, with the failure mode tagged).

This is the load-bearing structural difference vs the v0 corpus, which had no compiler validation step. Path D corpus is compiler-validated by construction.

## 6. Contrastive readout structure (from Path D §7)

For each seed CAS object, generate a contrast set varying ONE fiber/marginal at a time while preserving the base:

- Same Δ°₃₉ state, different drive intensities → different replies, same anchor state
- Same state, different register activation → different surface styles, same content
- Same state, different operation context → different reasoning trajectories
- Invalid expression + compiler error → corrected expression (repair pair)

This is the data shape that defeats silhouette-without-content. The model must learn *what's load-bearing vs what's modulation* because the corpus shows the same base producing controlled variants.

## 7. Execution plan — start today

**Wave 1 launches now:**

- **Agent A (tokenizer expansion)**: extend the existing 293-token vocab with the meta_logic + Cognitive Fractal coverage gap + any other missing surface forms identified by grepping the compiler grammar. Produce `english_bpe_v2.json` and a tokenizer-load test showing the new tokens encode as single tokens.
- **Agent B (seed enumerator)**: enumerate compiler-valid base CAS objects across the full grammar. Combinatorial enumeration through grammar productions + curated manual seeds for complex cases. Output `seeds.jsonl` (~6K records, compiler-validated).

**Wave 2 unblocks after Wave 1 lands.** Wave 3 (NL annotation, Claude API) requires user budget approval.

**This memo is the binding spec for the sprint.** Any agent or sub-task that diverges from these eight deliverables and seven-category coverage either updates this memo first or flags the divergence in its report.

## 8. References

- Path D runbook: `docs/working/path_D_compiler_fluency_curriculum_2026_05_07.md`
- Path C architecture: `docs/working/path_C_non_transformer_simplex_encoder_decoder_design_2026_05_06.md`
- Compiler: `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`
- Existing tokenizer: `noetic-compass-scaffold/noetic-compass/cas-native/training/tokenizer.py` + `cas-synthetic/data/native_nl/english_bpe_50k_*.json`
- Memory: `feedback_cas_token_enum_must_include_metalogic_and_fractals.md` (7-category coverage rule)
- v0 audit failure record: `docs/working/path_B4_human_relevance_failure_2026_05_07.md`
