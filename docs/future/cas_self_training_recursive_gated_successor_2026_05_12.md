# CAS Self-Training — Recursive Gated Successor Architecture

**Status:** FUTURE EXPLORATION. Archived 2026-05-12 after Candidate B3 validated the staged-training transformer recipe end-to-end. **Do NOT implement until broader B3 eval (24-pack, rpm-heavy identifier suite, non-rpm leakage negatives, fractal suite) lands clean.**

**Provenance:** This document captures two analyses on whether/how a fully-developed CAS-Native model could train itself. The two analyses converge on the same conclusion via different framings; both are recorded verbatim so the architectural commitment is preserved with its reasoning intact.

---

## Why this is now a real question, not speculation

As of 2026-05-12, the architectural primitives that make CAS-style self-training possible all exist in shipped code:

- Compiler with admissibility relations (deterministic, non-learned ground-truth oracle).
- Δ°₃₉ open probability simplex with strict pk > 0.
- Fisher-Rao geodesic metric on the simplex.
- Typed slot head (9 classes) + hard typed-fiber emission.
- Object traceability (id + parent_ids + trace_id on every domain object).
- Seven-axis inversion scanner.
- Round-trip eval gate (EN ↔ CAS via compiler).

Candidate B3 (this commit cycle) demonstrated these primitives work together end-to-end on the canary pack:
- TF `canonical_recovery_rate` rose from 0.0 (every prior candidate) to 0.5.
- Both rpm_chain canaries reconstructed canonical stage_var identifiers via hard routing.
- Zero non-rpm leakage.

The pieces are there. The orchestration that turns them into a self-training loop hasn't been written. This document is the design target for when it is.

---

## Analysis 1 — The four architectural signals + four-phase loop

CAS-Native has unusually strong self-supervision signals because of the non-learned compiler. Standard LLM self-improvement (RLAIF, constitutional AI, RLHF bootstrapping) hits a wall: another LLM as judge is circular — the judge has the same blind spots as the trainee. CAS-Native breaks the circle.

### Four self-supervision signals (architectural)

1. **Compiler-validated correctness.** Did the output parse? Did the operator chain satisfy admissibility? Hard binary signal, no annotator needed.
2. **Round-trip preservation.** Generate EN → recover CAS → compare to source. Distance in Fisher-Rao geometry on the simplex is a continuous gradient signal. Standard models have no equivalent because their internal state has no grammar that can be round-tripped.
3. **Internal consistency.** Slot head predicted STAGE_VAR but the emitted token wasn't a stage_var — that's a mismatch you can compute without any external label. Simplex trajectory predicted P=0.8 but compiler-computed P from the actual output is 0.3 — same kind of self-check. The multi-head structure becomes a mutual-verification network.
4. **Inversion-scan compliance.** The seven-axis scanner flags structurally problematic outputs (involution imbalance, drive imbalance, etc.). Self-generated outputs that fail the scan become hard negatives for free.

### Four-phase loop

**Phase 1 — Round-trip self-supervision.** Model generates EN for a given CAS expression. Compiler tries to recover the CAS from the EN. Fisher-Rao distance between source and recovered CAS is the loss. No human annotator anywhere. The existing compiler-round-trip eval gate is the same machinery, repurposed as supervision instead of evaluation.

**Phase 2 — Curriculum self-generation.** Model proposes new CAS expressions subject to admissibility. Compiler accepts/rejects. Accepted expressions get rendered to EN. Round-trip verifies. Successful round-trips become next-cycle training data. The corpus self-expands within the admissible space — the admissibility relations bound the expansion, so the model can't drift into nonsense, only into more-of-the-same-correctness.

**Phase 3 — Dialectic refinement.** Two CAS instances with involution-pair priors dialogue on a problem. The third instance is the `(A × B) = Ω` integrator. The compiler arbitrates which instance got which step right. Disagreement between A and B identifies where the model's representation is bimodal — that's where training emphasis should land.

**Phase 4 — Inversion-scanner-driven hard negatives.** Generate broadly, run the seven-axis scan, failures become contrastive negatives. The inversion scanner defines what structurally bad outputs look like, so it can produce labelled negative training data without human input.

### The honest caveat

Pure self-training drifts. Even with compiler validation, the model can converge to whatever style the compiler accepts most easily — "compiler-pleasing minimalism": every output technically valid, all of them flat and dead. Full self-training needs *periodic* external grounding — human eval at intervals, or injection of fresh external dialogue every N cycles. Like a centrifuge: internal pressure does most of the work, but you have to spin out the silt occasionally or it accumulates.

The asymptote isn't "model trains itself forever." It's "model self-trains 95% of the time and a human reviews 5%."

### Why this isn't just RLAIF rebranded

RLAIF's reward signal is another model's preference (opinion). CAS-Native's reward signal is compiler validity + round-trip preservation + admissibility + inversion compliance (formal properties). You can't argue with a compiler; you can argue with an LLM judge. That asymmetry is why CAS-style self-training has a chance of avoiding the convergent-mediocrity failure mode that bedevils current RLAIF.

---

## Analysis 2 — The recursive gated successor architecture

The model should train **successor models**, not mutate its own live weights directly. A mature CAS-Native loop looks like seven stages:

### Stage 1 — Live model operates
Production model serves traffic:
- English → CAS
- CAS → English
- Memory compression into CAS
- Level 3 conversation
- Stakeholder explanations
- CABS/simplex reasoning

### Stage 2 — Every decision is traced
Every output carries:
- Simplex state trajectory
- Typed fiber route
- CAS expression
- Output text
- Confidence
- Repair logs
- Verifier results

### Stage 3 — Failures become training examples
Each failure flagged by the verifier produces:
- Bad output
- Expected CAS
- Corrected CAS
- Corrected English
- Why the old trace failed
- Which state / fiber decision caused the issue

### Stage 4 — Model proposes its own curriculum
The model itself names its weaknesses, in structural terms (not vague):
- "I'm weak at identifier copying."
- "I collapse STAGE_VAR under long rpm_chain."
- "I paraphrase away Ω too often."
- "I need 5,000 examples of this failure class."

This is uniquely possible in CAS because the model isn't producing vague text about its mistakes — it can point at specific noetic states, fiber routes, simplex trajectories, memory-compression losses, or fluent-but-structurally-false outputs.

### Stage 5 — A trainer builds a new checkpoint offline
**Not the production model editing itself live.** A candidate successor is trained from curated traces, in a separate process, on separate hardware. The live model continues serving.

### Stage 6 — External gates decide promotion
The candidate successor must pass all of:
- v0 canary
- 24-pack
- Fractal suite
- Memory compression suite
- Hidden-belief / eval-awareness probes
- Level 3 conversation suite
- No regression on known-good records

### Stage 7 — Only then does the successor replace the old model
Promotion is a discrete event with a versioned audit trail. The old model is archived, not deleted (so we can A/B compare or roll back).

### The slogan

> **The model observes itself, diagnoses itself, generates corrected CAS traces, builds a curriculum, trains a successor offline, and promotes only through hard external gates. That is self-training without self-delusion.**

### Why CAS is uniquely suited

The model isn't generating vague self-criticism. It can name:
- This noetic state was wrong.
- This fiber route was wrong.
- This simplex trajectory drifted.
- This memory compression lost a required component.
- This output was fluent but structurally false.

Each of these is a typed, structurally specific claim — recoverable from the trace, verifiable by the compiler, traceable to a concrete training-example proposal.

### The danger and the safety

**Danger: reward hacking.** The model learns to satisfy its own evaluator instead of becoming more correct.

**Safety: evaluator and promotion gates must stay external, versioned, and adversarial.** The model never grades its own promotion. It can propose curriculum, generate candidate corrections, train candidate successors — but the gate that decides which candidate goes to production is held outside the loop.

---

## Convergence of the two analyses

Both framings converge on the same operational architecture:

| Analysis 1 framing | Analysis 2 framing |
|---|---|
| Round-trip preservation as supervision | Stage 3 — failures-as-training-examples (with corrected CAS) |
| Curriculum self-generation within admissibility | Stage 4 — model proposes its own curriculum |
| Dialectic refinement with compiler arbitration | (Compatible — fits inside Stage 5's trainer logic) |
| Inversion-driven hard negatives | (Part of failure-classification in Stage 3) |
| Periodic external grounding ("centrifuge") | External + versioned + adversarial gates (Stages 6-7) |
| Successor model, not live-weight mutation | Explicit: "successor offline, not live editing" |

The strongest single insight, common to both: **the compiler is the asymmetric advantage**. Standard LLM self-improvement is bottlenecked by the circularity of LLM-judges-LLM. CAS has a non-learned deterministic compiler that can never drift away from the trainee, which is what makes recursive gated successor training defensible.

---

## Dependencies before any implementation

This is a real research direction, not vapor — but it does not start until the following are in place:

1. **Broader B3 eval lands clean** (24-pack, rpm-heavy identifier suite, non-rpm leakage negatives, fractal suite). The 11-canary result is necessary but not sufficient to claim production-ready.
2. **B1/B2/B3 staged recipe is locked as canonical.** (Companion doc: `simplex_mvp_staged_training_canonical_recipe_2026_05_12.md`.)
3. **The three-instance dialectic prototype exists** OR is explicitly designed-but-deferred. Stage 5 of the recursive loop can use single-model successor training; Stage 5 + dialectic is the strongest form.
4. **Decision: which six-property "best LM" weakness becomes the first self-training target.** Probably identifier/copy fidelity (property 4), since B3 hit 0.5 canonical recovery and the failure mode is structurally namable.
5. **External evaluator versioning policy.** Need a story for "evaluator V1 graded successor V42; what happens when evaluator V2 ships." Versioning + cross-version sanity checks.
6. **Compute budget commitment.** Recursive successor training is not free even in self-training mode (corpus generation + verifier runs + candidate training + gate passes). Order-of-magnitude estimate before commit.

## Companion files

- `docs/working/simplex_mvp_candidate_b3_findings_2026_05_12.md` — the validation evidence this design target is downstream of.
- `docs/working/simplex_mvp_staged_training_canonical_recipe_2026_05_12.md` — the recipe self-training would generate successors from.
- `docs/working/simplex_mvp_architecture_review_2026_05_11.md` — the A→C→B sequence that ended in B's validation.
- Memory: `feedback_cas_best_lm_six_properties.md` (what "better" means for successors), `feedback_traceability_is_the_whole_purpose.md` (why structural traces are the curriculum substrate), `project_three_instance_dialectic_proposal_2026_05_04.md` (Stage 5's natural form).
