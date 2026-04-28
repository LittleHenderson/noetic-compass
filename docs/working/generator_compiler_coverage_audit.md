# Generator vs Compiler Coverage Audit

Worker C scope: documentation under `docs/working/` and non-synthesizer tests under `noetic-compass-scaffold/noetic-compass/tests/`.

## Purpose

This audit defines the compiler surfaces that generated CAS examples must satisfy during the compiler/generator catch-up. It is intentionally a compatibility gate, not a generator implementation plan: generator unit tests should still own randomization, templates, labels, and bucket mix behavior.

## Status (Day 1 SDG Sprint Closure — 2026-04-27)

The Day 1 sprint closed two coverage gaps that were previously listed as residual:

- **Track A (`7951e56`)** extended `cas-native/data/expression_generator.py::TYPED_META_LOGIC_EXEMPLARS` from 15 to 32 exemplars covering Union (`∪`), Difference (`∖`), Empty set (`∅`), Not-member (`∉`), Strict subset (`⊂`), Superset (`⊃`), and SupersetEq (`⊇`). Each token class has valid + invalid + edge-case counterparts; surface tests and the coverage gate were extended in lockstep.
- **Track B (`8ed4f5b`)** added a meta-logic trigger vocabulary to `api/pipeline/notation_synthesizer.py`. Idea Atlas captures whose prose explicitly invokes set-theoretic vocabulary now produce typed meta-logic assertions; vague prose falls through unchanged to v7.4–v7.7 emission paths.

Both tracks are guarded by a runtime safety net: every emitted form is piped through `compile_expression` before being returned to the caller, so a misfiring trigger cannot propagate an invalid assertion.

## Post-Audit Follow-Up (2026-04-28)

Codex audit closed two Day 1 residuals locally:

- `cas-native/model/meta_logic_constructs.py::CONSTRUCT_SPECS` now enumerates the compiler-admitted typed Set family (`NoeticSet`, `StateSet`, `StateVariantSet`, `RelationSet`, `DriveSet`, `DomainSet`, `RegisterSet`, `FoundationSet`, `SubFoundationSet`) instead of leaving `NoeticSet`/`StateSet` as grammar-only support.
- `api/pipeline/notation_synthesizer.py` now normalizes common numeric natural-language carrier references before meta-logic emission, so prompts such as `the union of Foundations 1 and 7` and `Foundation 1 is in Foundations` emit compiler-valid meta-logic instead of falling through to v7.4.

Focused verification after the follow-up: `tests/test_notation_synthesizer.py` + `tests/test_generator_compiler_coverage_gate.py` = 187 passed / 3 xfailed; `cas-native/tests/test_expression_generator_surfaces.py` = 6 passed. `cas-native/tests/test_meta_logic_constructs.py` still cannot collect in this local environment because `cas_native.model.__init__` eagerly imports torch-dependent modules and `torch.nn` is unavailable; that is an environment/package-boundary issue, not a compiler/synthesizer failure.

## Day 2 Sprint Closure — Level 2 Dataset (2026-04-28)

The Day 2 sprint produced and committed the Level 2 v1 training dataset for the first CAS-Native v2 training run. Full dataset documentation lives at `cas-synthetic/data/README.md`; this section only records the audit-relevant outcome.

**Committed dataset**: `74e5350` — `cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl` (10,000 examples, 6.92 MB) plus paired metrics and replayable sidecar script. Mix ratios 20/25/15/20/10/10 across (v74_baseline, v75_register, v77_rule_four, v77_omega, v76_production, meta_logic). Compilation pass rate 97.27% overall — 100% on five non-rule_four buckets; v77_rule_four 81.8% with the remaining 18.2% being deliberate Rule 4 violations preserved as `is_valid=false` supervised-loss signal.

**Generator chain** (closes notation drift and diversifies all six buckets):

- `e8cd9dd` — 4-bucket notation fix (v75/v77_rule_four register order; v77_omega Unicode `× Ω_*`; v76_production `Θ Ω_ →` + real state literals)
- `c054c9b` — meta_logic operand randomization (parametrized templates with 12 typed slot kinds across 7 axes)
- `ede9e22` — v77_omega diversity expansion (registry 2→8, drive-arity-aware drive sampling)
- `b9d5a28` — v77_rule_four diversification (full 10-Noetic / 4-Domain / 7-Drive / variable register subsets)
- `cbd9bab` — v75_register diversification (paired co-presence `+` primary diversifier + 5 single-state form variants)
- `c61a3fe` — v75_register weight recalibration (small-pool saturation correction)

**Registry chain**: `ce8dee4` → `ede9e22` → `40e11d2` (12 admitted Ω entries spanning Noetics 0-9: Ω_presence, Ω_refusal, Ω_grounding, Ω_alignment, Ω_clarity, Ω_resolve, Ω_witness, Ω_attunement, Ω_genesis, Ω_cadence, Ω_invocation, Ω_landing).

**Validator chain**: `ec09594` (`validate_level2_dataset.py`) → `edc09fa` (Windows cp1252 stdout UTF-8 fix). Per-example compile-validation against `api.notation.compile_expression`; 0 retries and 0 fallbacks observed across 10K generation.

**Coverage at the dataset level**: all 10 Noetics, all 4 Domains, all 7 Drives, all 4 Registers, all 7 Foundations present. Cross-bucket Noetic Jaccard = 1.0 across all bucket pairs.

**Per-bucket dupe redundancy** at n=10000:

| Bucket | Redundancy | Disposition |
|---|---|---|
| v76_production | 0.00% | Per-example Gaussian coefficient noise eliminates duplicates |
| v77_rule_four | 2.13% | Phase 2.5 fix (down from 38.5% — load-bearing for constraint-learning quality) |
| v77_omega | 11.90% | Phase 2.5 registry expansion + drive/register randomization |
| v75_register | 12.32% | Phase 2.6 paired co-presence (down from 19.96%) |
| meta_logic | 15.30% | Parametrized templates; small-cardinality constructs saturate inherently |
| v74_baseline | 32.80% | Structurally bounded; bare state-literal repetition benign for vocabulary learning (intentionally not diversified) |

Total dataset duplicates: 1480 extra copies (14.8% of dataset).

## Remaining Follow-Ups (Deferred, Not Blocking)

- **ASCII keyword grammar parity** for `∅`, `∉`, `⊂`, `⊃`, `⊇` — would require lockstep parser changes in `api/notation/compiler.py` and `cas-engine/crates/casc-syntax/src/lib.rs`. Optional; generated fixtures use Unicode forms throughout.
- **Torch decoupling** for symbolic-only construct imports — `cas_native.model.__init__` eagerly imports torch.nn-dependent modules, blocking `cas-native/tests/test_meta_logic_constructs.py` collection in no-torch environments. Cleanest fix: split `cas-native/model/__init__.py` into a thin symbolic re-export layer and a separate `cas_native.neural` namespace for the torch-dependent stack.
- **Conversational layer (Level 3)** — multi-turn dialogue training data with retained CAS state across turns. Deferred to Month 3+; not in Level 2 scope.
- **Appendix I manuscript entries** for the 10 newly admitted Ω names (`Ω_grounding` through `Ω_landing`) — book/manuscript work parked for separate weekend session.
- **v74_baseline duplication** is acknowledged structural saturation (280 unique combos × 7.1× sampling at n=2000). Not a sprint target; if Level 3 needs lower vocabulary redundancy, the cleanest path is to reduce the bucket's allocation rather than diversify the parameter space.

The Level 2 v1 dataset is closed. See `cas-synthetic/data/README.md` for full dataset documentation including schema, reproducibility commands, top-token frequency tables, and intended-use tiers.

## Compiler-Accepted Surfaces Relevant to Generation

The public gate is `api.notation.compiler.compile_expression`. A generated `cas_expression` is compiler-compatible when it returns a valid artifact for valid examples, or a targeted invalid artifact for intentionally invalid training examples.

Relevant accepted surfaces:

- v7.4 baseline states: `^n^D_{Fk}`, `CO-n^D_{Fk}`, shorthand state refs such as `C2`, same-domain products, domain-descent relations, `RPM(Fk)`, `Phi<...>`, and multi-statement programs.
- v7.5 registers: register-neutral v7.4 expressions, state-level suffixes such as `^2^C_{F2}|A`, noetic-level suffixes such as `^2|T`, drive-level suffixes such as `F_2|A`, independent noetic/drive registers such as `^2|T^C_{F2|A}`, and valid register tokens `T`, `A`, `f`, `E`.
- v7.6 production semantics: `Theta(Omega_name) = coeff*primitive + ... -> Omega_name`, leakage products on the RHS, catalyst/inhibitor annotations before the arrow, state-vector literals, `Y_T`, `Y_A`, and `eta` yield queries. Recipe targets must be `Omega_*` tokens inside `Theta(...)` and on the RHS.
- v7.7 register multiplicity: register sets such as `^3^P|<A,f,T>` or Unicode angle equivalents, co-presence via `+`, explicit same-noetic emergent assignment via `(...) = ^n^D|Omega_name`, and Rule 4 rejection for bare same-noetic cross-register `*`.
- Meta-logic: canonical meta-sets (`Noetics`, `Domains`, `States`, `Registers`, `Foundations`, etc.), typed clusters (`NoeticCluster`, `StateCluster`, `StateVariantCluster`, `RelationCluster`), finite set operations (`∪ ∩ ∖`), `Pullback` as finite meet/intersection only, `Product`, `CoverOf`, `PartitionOf`, `Coordinate`, tuple forms, membership/subset/cardinality assertions (`∈ ∉ ⊂ ⊆ ⊃ ⊇`), and the empty-set element `∅`.
- Diagrams: every valid artifact may call `artifact.diagram()` and should expose graph nodes, edges, containers, and layout hints. Generation should not emit diagram-only syntax; diagrams are a projection of compiler-valid CAS.

## Coverage Matrix

| Surface | Generator bucket/source | Compiler status | QA gate |
| --- | --- | --- | --- |
| v7.4 single state `^n^D_{Fk}` | `v74_baseline` single-state branch | Accepted | Blocking compile case |
| v7.4 same-domain product | `v74_baseline` product branch | Accepted | Blocking compile case |
| v7.4 domain descent relation | `v74_baseline` relation branch | Accepted | Blocking compile case |
| v7.5 register suffix after full state | Desired register surface | Accepted | Blocking compile case |
| v7.5 independent noetic/drive registers | Expanded register surface | Accepted | Blocking compile case |
| v7.5 register before drive subscript, e.g. `^2^C|A_{F2}` | Legacy invalid shape generators must avoid | Not accepted | Strict xfail guardrail |
| v7.6 Omega recipe | Desired production surface | Accepted | Blocking compile case |
| v7.6 state-vector/yield query | Production support surface | Accepted | Blocking compile case |
| v7.6 bare production target, e.g. `Theta(goal)` | Legacy invalid shape generators must avoid | Not accepted | Strict xfail guardrail |
| v7.7 register set | Register multiplicity surface | Accepted | Blocking compile case |
| v7.7 same-noetic `+` co-presence | Rule 4 compliant generation | Accepted | Blocking compile case |
| v7.7 same-noetic `*` without emergent result | Intentional violation examples | Rejected with Rule 4 error | Blocking invalid guardrail |
| v7.7 same-noetic emergent assignment using `*` | Named emergent generation | Accepted | Blocking compile case |
| v7.7 same-noetic emergent assignment using `x` | Legacy invalid shape generators must avoid | Not accepted | Strict xfail guardrail |
| Meta-logic typed clusters | `v78_meta_logic` cluster families | Accepted | Blocking compile case |
| Meta-logic finite set operations (`∩`) | `v78_meta_logic` set-op families | Accepted with compiler tokens/aliases | Blocking compile case |
| Meta-logic Union (`∪`) — generator | `TYPED_META_LOGIC_EXEMPLARS` (Track A) | Accepted | ✅ Blocking compile case |
| Meta-logic Difference (`∖`) — generator | `TYPED_META_LOGIC_EXEMPLARS` (Track A) | Accepted | ✅ Blocking compile case |
| Meta-logic Empty set (`∅`) — generator | `TYPED_META_LOGIC_EXEMPLARS` (Track A) | Accepted (Unicode only) | ✅ Blocking compile case |
| Meta-logic Not-member (`∉`) — generator | `TYPED_META_LOGIC_EXEMPLARS` (Track A) | Accepted | ✅ Blocking compile case |
| Meta-logic Strict subset (`⊂`) — generator | `TYPED_META_LOGIC_EXEMPLARS` (Track A) | Accepted | ✅ Blocking compile case |
| Meta-logic Superset (`⊃`) — generator | `TYPED_META_LOGIC_EXEMPLARS` (Track A) | Accepted | ✅ Blocking compile case |
| Meta-logic SupersetEq (`⊇`) — generator | `TYPED_META_LOGIC_EXEMPLARS` (Track A) | Accepted | ✅ Blocking compile case |
| Meta-logic typed Set constructors | `TYPED_META_LOGIC_EXEMPLARS` + `CONSTRUCT_SPECS` | Accepted by compiler grammar and construct taxonomy | Blocking compile case |
| Synthesizer NL → Union / Intersection / Difference | `_try_meta_logic_emission` (Track B) | Accepted | Blocking emission test |
| Synthesizer NL → Member / NotMember | `_try_membership_emission` (Track B) | Accepted | Blocking emission test |
| Synthesizer NL → Subset / SubsetEq / Superset / SupersetEq | `_try_subset_emission` (Track B) | Accepted | Blocking emission test |
| Meta-logic covers/partitions/products | `v78_meta_logic` higher constructors | Accepted | Blocking compile case |
| Diagram projection | Any valid compiled representative | Accepted | Blocking diagram smoke case |

## Synthesizer NL Surface (newly covered, Track B)

`api/pipeline/notation_synthesizer.py` now emits typed meta-logic assertions when source prose explicitly invokes set-theoretic vocabulary. Trigger detection is split across three helper functions:

- `_detect_set_operation_vocabulary` — recognizes `Union`, `Intersection`, `Difference`.
- `_detect_membership_vocabulary` — recognizes `Member`, `NotMember`.
- `_detect_subset_vocabulary` — recognizes `Subset`, `SubsetEq`, `Superset`, `SupersetEq`.

That gives **9 trigger categories** total. Conservative trigger discipline applies: each detector requires explicit set-reference language *and* a recognized meta-set carrier. Common everyday senses (`labor union`, `street intersection`, `the difference between us`, `is in trouble`, `contains nuts`) are filtered out via explicit negative-fire lists (`_UNION_NEGATIVE_CONTEXTS`, `_INTERSECTION_NEGATIVE_CONTEXTS`, `_DIFFERENCE_NEGATIVE_CONTEXTS`, `_IS_IN_NEGATIVE_CONTEXTS`, `_CONTAINS_NEGATIVE_CONTEXTS`).

When a trigger fires, the synthesizer:

1. Resolves both operands via `_resolve_meta_set_operand` (canonical meta-set name → bare Domain/Drive/Foundation → `^N^D` state ref → `^N` Noetic ref → existing typed cluster).
2. Verifies carrier-type compatibility via `_carriers_compatible` (e.g. a Noetic ref cannot subset `States`).
3. Wraps bare singletons as singleton clusters where the assertion type requires it (`_wrap_singleton_for_set_op`).
4. Builds the final assertion via `_construct_meta_logic_assertion`.
5. Pipes the candidate string through `compile_expression` and only returns it if `valid` is True.

This compile-validation step is the runtime safety net: even if a misfiring trigger produces a candidate string, an invalid candidate is dropped silently and the existing v7.4–v7.7 emission paths run as before. False-fire cost is bounded.

## ASCII Keyword Discrepancy (vs Day 1 directive)

The original Day 1 directive named ASCII keyword aliases for the new token classes (`emptyset`, `notin`, `subset`, `supset`, `supseteq`). Empirical compilation against `api/notation/compiler.py` showed the Python compiler grammar admits ASCII aliases only for set operations:

| Symbol | Unicode | ASCII alias(es) admitted? |
| --- | --- | --- |
| Union | `∪` | ✅ `union` |
| Intersection | `∩` | ✅ `intersect` |
| Difference | `∖` | ✅ `setminus`, `difference`, `diff` |
| Empty set | `∅` | ❌ no admitted ASCII alias |
| Not-member | `∉` | ❌ no admitted ASCII alias |
| Strict subset | `⊂` | ❌ no admitted ASCII alias |
| Superset | `⊃` | ❌ no admitted ASCII alias |
| SupersetEq | `⊇` | ❌ no admitted ASCII alias |
| Member | `∈` | ✅ `in` |
| SubsetEq | `⊆` | ✅ `subseteq` |

Track A exemplars use Unicode forms exclusively for the five symbols without ASCII aliases. The directive's ASCII keyword list should not be trusted at face value by future authors; verify against the compiler grammar before assuming an alias exists.

## Edge-Case Substitutions (vs Day 1 directive)

Two directive-suggested edge cases failed compilation and were substituted in `TYPED_META_LOGIC_EXEMPLARS`:

- **`∅ ∪ Noetics = Noetics`** — the trailing `=` is parsed as v7.7 emergent-result syntax, which requires an emergent state token (e.g. `^n^D|Omega_name`) at the terminal. A bare meta-set on the RHS does not satisfy that. Substituted with bare `∅ ∪ Noetics`.
- **`^11 ∉ Noetics`** — `^11` is rejected at typecheck with `operator index must be 0-9` before the `∉` assertion is evaluated. Substituted with `^2^P ∉ Noetics` (a State ref that is correctly *not* a Noetic) and `^9 ∉ States` (a bare Noetic ref that is correctly *not* a State).

These substitutions preserve the negative-test intent (assertions that should *not* hold) while staying within the compiler's typecheck surface.

## QA Gate

Added `noetic-compass-scaffold/noetic-compass/tests/test_generator_compiler_coverage_gate.py`.

The gate has three roles:

- Blocking valid-surface cases: representative generated-style expressions across v7.4, v7.5, v7.6, v7.7, meta-logic (now including Union, Difference, ∅, ∉, ⊂, ⊃, ⊇), and diagrams must compile.
- Blocking invalid-surface guardrail: a deliberate Rule 4 violation must fail compilation, preserving supervised invalid-example semantics.
- Strict xfail guardrails: legacy generator-output shapes that are not compiler-compatible are recorded as expected failures. If the compiler intentionally begins accepting one of those forms, pytest reports XPASS so the audit can be updated and the row can graduate to blocking.

Synthesizer-side coverage is asserted in `tests/test_notation_synthesizer.py` (140 tests as of Track B), exercising both positive triggers (set-theoretic prose → typed assertion) and negative-fire cases (everyday vocabulary → fall-through to v7.4–v7.7 emission).

## Closed Carve-Out: Typed Set Constructors

The Day 1 audit listed NoeticSet and StateSet as residual gaps for the generator. Empirically:

- **The compiler grammar accepts** `NoeticSet{...}` and `StateSet{...}` (and the related variant `*Set` constructors) — `compile_expression` returns valid artifacts for those forms.
- **`cas-native/model/meta_logic_constructs.py::CONSTRUCT_SPECS` now enumerates** the typed Set family as first-class symbolic constructs.

Because the generator uses `CONSTRUCT_SPECS` as its source of truth for which constructs may be sampled, the correct fix was to extend `CONSTRUCT_SPECS` first, then add the exemplars and matching coverage-gate cases. That follow-up is complete locally for `NoeticSet`, `StateSet`, `StateVariantSet`, `RelationSet`, `DriveSet`, `DomainSet`, `RegisterSet`, `FoundationSet`, and `SubFoundationSet`.

## Remaining Gaps

- Current generators should continue emitting compiler-recognized order for v7.5 registers: `^n^D_{Fk}|R` or independently registered forms, not `^n^D|R_{Fk}`.
- Current generators should continue emitting v7.6 recipe targets as `Theta(Omega_name) ... -> Omega_name`, not bare `Theta(name) ... -> name`.
- Decide whether `state_<id>` recipe prerequisites are a stable accepted shorthand or should remain banned in favor of explicit state primitives such as `^n^D`.
- Current generators should continue avoiding `x` as a cross-register separator unless compiler support is deliberately added in a separate parser task.
- Keep meta-logic generator templates encoded and emitted in compiler-recognized token forms; ASCII aliases such as `union`, `intersect`, `setminus`, `subseteq`, and `in` are safer for generated fixtures when encoding is uncertain. There are NO admitted ASCII aliases for `∅`, `∉`, `⊂`, `⊃`, or `⊇`; generators must use the Unicode forms (or extend the grammar in a separate parser task).
- **CAS-Native symbolic tests in no-torch environments** — `cas_native.model.__init__` eagerly imports torch-dependent modules before symbolic-only modules can be collected. Optional follow-up: make symbolic construct imports available without importing the full neural stack, or install a complete torch environment for these tests.
- **ASCII keyword variants for `∅`, `∉`, `⊂`, `⊃`, `⊇`** — blocked on grammar extension. Optional follow-up: if generated fixtures need encoding-resilient ASCII forms for these symbols, add the aliases to the Python and Rust grammars in lockstep.
- Add fixture-based integration once generator output snapshots stabilize. The current gate uses representative static expressions plus direct generator tests to avoid overfitting to random output.
