# Path D — Compiler-Fluency Curriculum (v1 training)

**Date:** 2026-05-07
**Status:** Active runbook for the v1 model retrain. Companion to Path C (architecture).

## 1. Frame

Path D specifies how the model is **trained** to be CAS-fluent. Path C specifies the **architecture** that supports it. They ship together for the v1 retrain — separate runbooks, single sprint.

This document captures the load-bearing framing (originally drafted as Path C §3.4 on 2026-05-07, lifted out into Path D when the four-step v1 plan locked) plus the corpus and curriculum design that follows from it.

**Slogan:** *Compiler = law. Model = fluent speaker. Together = traceable conversational reasoning.*

The model knows everything the compiler can SAY. The compiler decides whether what the model said is TRUE. That is how CAS-Native becomes genuinely native, not just CAS-conditioned.

## 2. The analogy

Claude/Codex do not BECOME the Python compiler. They learn enough Python that they can:

- read code
- write code
- explain code
- predict likely compiler errors
- fix invalid code
- use the compiler as feedback

CAS-Native should do the same with CAS notation. It should not replace the CAS compiler. It should become fluent in the compiler's language:

- read CAS
- write CAS
- explain CAS
- translate English → CAS
- translate CAS → English
- predict likely invalidity
- repair invalid CAS
- use compiler feedback

The right target is **not** "model that emits CAS-shaped tokens." It is **model that genuinely understands what CAS expressions mean, what makes them valid, and how to translate fluently in either direction**.

## 3. The long-term inference architecture

```
Human English
  → CAS-Native proposes CAS expression / intent
  → CAS compiler validates it
  → RPM / meta-logic checks admissibility
  → CAS-Native explains or responds in natural English
```

The model is the **bidirectional translator + hypothesis generator**. The compiler is the **parser + admissibility judge**. Together they produce traceable, auditable, conversationally natural CAS reasoning.

This pipeline is the load-bearing structure for traceability — every reply walks back through compiler validation, and the compiler verdict is what's surfaced in Mode 7 / Mode 3 trace.

## 4. What "fluent" means concretely

Eventually the model understands every construct the compiler validates:

- state expressions (`^n^D`, the 40 Cognitive States)
- domains (P/C/E/O)
- drives (F1–F7)
- registers (T/A/f/E and multi-register `|⟨…⟩`)
- operations (`+`, `×`, `→`, `∘`, `=`, `Ω`)
- fractal composition (Cognitive Fractal sequences `⟨k₁:k₂:⋯:kₙ⟩`)
- RPM (prerequisite chain admissibility)
- meta-logic (relations, proofs, set constructors `NoeticCluster`, `StateSet`, `RelationCluster`, `Tuple`, `Coordinate`, `Product`, `CoverOf`, `PartitionOf`)
- production semantics (recipes `Θ(Ω) = a·X₁ + b·X₂ → Ω`)
- register multiplicity (operator discipline: `+` vs `×` vs `|⟨…⟩`)
- invalid / underdefined forms (predicting failure before the compiler does)
- compiler errors and repairs (verbalizing what went wrong, proposing the nearest valid form)

The compiler at `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py` is the authoritative grammar. Any token surface form the compiler accepts must be representable by the model's vocab and producible by the model's heads.

## 5. Roles, not redundancy

| Role | Who plays it | Why |
|---|---|---|
| Law / judge | CAS compiler | Deterministic. Same expression → same verdict, every time. Not creative. |
| Fluent speaker / writer / explainer | CAS-Native model | Creative and conversational. Approximately compiler-aligned but not perfectly. Can hypothesize, paraphrase, translate in either direction, repair invalid forms. |

The strength is the **asymmetry**:

- Codex without rustc is a hallucinator.
- rustc without Codex is a parser, not a writing assistant.
- Both together is what makes the system work.

CAS-Native model + CAS compiler is the same pattern. The model can be creative *because* the compiler keeps it honest.

## 6. Six-task compiler-fluency curriculum

The next training track after conversational v0 is **not** "more dialogue corpus." It is a **compiler-fluency curriculum**. Six core training tasks:

| # | Task | Input | Target | Compiler role |
|---|---|---|---|---|
| 1 | CAS → English | CAS expression | natural-language paraphrase | validates expression before training; rejects invalid sources |
| 2 | English → CAS | natural-language description | compiler-valid CAS expression | accept-sample-only training; invalid generations rejected |
| 3 | Invalid CAS → explanation | malformed expression | natural-language description of why it's invalid | compiler emits the error; model learns to verbalize it |
| 4 | Invalid CAS → corrected CAS | malformed expression | nearest valid expression | compiler validates the correction |
| 5 | CAS operation → outcome | source state + operation | resulting state / admissibility verdict | compiler / engine runs the transition; model predicts |
| 6 | CAS expression → compiler trace | full expression | compile trace (parse tree, admissibility, RPM result, fractal canonical form) | compiler emits the trace; model learns to predict it |

These are **not random new tasks**. They are the bidirectional symbolic ↔ NL translation tasks that turn a "CAS-conditioned" model (one that emits CAS-shaped tokens because we trained it to) into a "CAS-native" model (one that genuinely understands what CAS expressions mean and what makes them valid).

## 7. Contrastive readout supervision (Path D's load-bearing data structure)

Beyond the six tasks above, Path D introduces a complementary data design that defeats the silhouette-without-content failure mode the v0 audit revealed.

Take one compiler-valid base CAS object. Generate multiple readouts that vary fibers/marginals while PRESERVING the base. Train the model on the contrastive set:

- Same Δ°₃₉ state, different drive intensities → different replies, same anchor state
- Same state, different register activation → different surface styles, same content
- Same state, different operation context → different reasoning trajectories
- Invalid expression + compiler error → corrected expression (repair)
- Same recipe, different ingredient ordering → equivalent expressions per CAS algebra

The model can't memorize a silhouette and hollow out content if the corpus shows the same base producing controlled variants — it MUST learn what's load-bearing vs what's modulation. The v0 corpus taught silhouettes without contrast (recipes appeared in only one form per scenario); contrastive readout supervision is the corpus design that makes preservation forced.

## 8. Five operational requirements

Five concrete things that must be true for CAS-Native to reach compiler-fluency:

1. **Vocab parity with grammar.** Every atom the compiler parses is a model token. (The meta_logic 53.6% failure mode in v0 was exactly this gap — 8 set-constructors + 6 operators absent from the 293-token vocab. Cheap fix, ~1.5 pod-hours.)

2. **Corpus parity with grammar.** For every construct in the grammar, the SDG corpus has natural-language examples that round-trip to that construct. Recipes, set constructors, `let` bindings, diagram exports, multi-register `|⟨…⟩`, fractal sequences, set ops (`∪ ∩ ∖`) — all need representation. The 7-category checklist in `feedback_cas_token_enum_must_include_metalogic_and_fractals.md` (memory) is the canonical list.

3. **Compiler-validated training.** Every training example, after generation, round-trips through the compiler. Samples that fail to parse or fail admissibility get rejected before they enter the corpus. Same as code-LLM compiler-rejection sampling.

4. **Constrained decoding.** At inference, mask logits the compiler would reject. Syntax-aware autocomplete pattern.

5. **Compiler-as-evaluator.** "Compile rate" is a first-class eval metric alongside loss / sample quality / round-trip K=9 / traceability. CAS-Native's HumanEval-equivalent. Already wired into `cas-native/evaluation/b4_failure_eval.py` via the compiler-preservation scorer at `cas-native/evaluation/compiler_preservation_scorer.py` (committed `dfc7269`).

## 9. Reframed v0 → Path C/D → Phase 4 progression

Under the Codex analogy:

- **v0 today** — covers a subset of the grammar (state literals + basic operators + register prediction). Analog: "Codex that knows Python expressions but not classes, decorators, or async/await." Useful, bounded.
- **Path C + Path D (v1 retrain)** — closes the grammar gap. Path C: simplex-native architecture (Δ°₃₉ base manifold + typed fibers + typed constraints). Path D: vocab parity + corpus parity + compiler-validated training across the full grammar + contrastive readout supervision. Analog: "Codex that covers the full Python language."
- **Phase 4+** — structural alignment via auxiliary losses + constrained decoding + extended compiler-fluency tasks. Analog: "Codex with linter integration in the loss + compile rate as a first-class eval metric."

## 10. Path D corpus design (next sprint)

The next concrete deliverable for Path D is a corpus generator that produces compiler-validated samples for the six tasks plus contrastive readout sets. Open questions to resolve in the corpus design sprint:

- How to source seed CAS objects: hand-curated initial set + compiler-driven enumeration through grammar productions vs LLM-generated then compiler-filtered.
- How to vary fibers/marginals systematically for contrastive readout: drive intensity perturbations, register reassignments, operation substitutions.
- How to generate invalid CAS that the compiler rejects in instructive ways (syntax errors vs semantic admissibility failures vs RPM violations).
- How to generate compile-trace targets at the right granularity for the model to learn (full AST? abbreviated trace? error-only trace?).
- Volume target: based on the v0 50K dialogue corpus, probably 100K–500K compiler-validated samples across the six tasks + contrastive readouts.
- Tokenizer expansion: the meta_logic 14-token vocab gap closes here; expand vocab and retrain tokenizer artifact before corpus generation begins.

These are scoped for the post-v1-eval-gate sprint. Until B-4 product-routing eval clears the gate (which requires v1 model retrain), Path D corpus design is the binding deliverable.

## 11. Relationship to Path C

| Aspect | Path C | Path D |
|---|---|---|
| Owns | Architecture | Curriculum + corpus |
| Geometry | Δ°₃₉ base manifold + typed fibers + typed constraints | (consumes the architecture) |
| Heads / losses | Cognitive State / Drive / Register / Operations / Meta-logic / RPM | (provides the supervision targets) |
| Vocab | (consumes the corpus) | Defines vocab parity requirements |
| Compiler integration | (consumes compiler verdicts via meta-logic and RPM) | Trains against compiler-validated samples; uses compiler as eval |
| Corpus | (consumes Path D corpus) | Owns corpus design + generation |
| Falsification gate | C1–C5 axis-by-axis prototype gates | Compile rate, structural preservation, contrastive consistency on the eval harness |

**They ship together as v1.** Path C without Path D produces a beautiful architecture trained on the wrong corpus (v0 reflective monologues — fails the audit again). Path D without Path C trains a flat-vocab model with no architectural pressure to preserve content (silhouette-without-content reproduces). Pairing is the correct unit.

## 12. References

- Path C runbook: `docs/working/path_C_non_transformer_simplex_encoder_decoder_design_2026_05_06.md`
- Audit failure record: `docs/working/path_B4_human_relevance_failure_2026_05_07.md`
- Compiler: `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`
- B-4 eval harness (uses compiler-preservation scorer + 7-dim user-facing): `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/b4_failure_eval.py`
- Compiler-preservation scorer (Path D's primary eval signal): `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/compiler_preservation_scorer.py`
- 7-category CAS token enumeration (vocab/regex coverage requirement): memory `feedback_cas_token_enum_must_include_metalogic_and_fractals.md`
- v1 locked plan: memory `project_v1_locked_plan_path_c_d_2026_05_07.md`
