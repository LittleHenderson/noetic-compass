# Simplex Δ°₃₉ Rebuild — Plan Doc

**Date:** 2026-05-11
**Status:** PLAN DRAFT. Awaiting user sign-off. NO implementation, NO GPU spend, NO model code changes until plan is approved.
**Triggered by:** v1e exhaustion (Phase C killed by 24-pack regression 2026-05-11).

This doc maps the 5 questions the user asked me to answer:

1. What v0 proved
2. What v1d/v1e failed
3. Which failure modes simplex is supposed to solve
4. What minimum viable simplex checkpoint would look like
5. How CABS/geodesic memory plugs in later

It does NOT prescribe implementation steps. After user sign-off, a
follow-up design doc + 6-agent R&D recon (mirroring the v1e Phase 1B
6-agent pattern) would translate this plan into a buildable spec.

## 1. What v0 proved

**v0-rc1** (v1c VALIDTOK 5ep + 5 scaffolds, 18/24 acceptable+, tagged
`255b2a7`, archived at `D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\`).
What the empirical record shows v0 CAN do:

- **State literals** rendering correctly with domain + drive + register
  (records 1-2 green; record 3 was wrong but its target was unusual
  phrasing).
- **Binary composition** with `+` and `->` operators (records 4, 6
  green; 5 yellow on operator mis-rendering).
- **Cross-register Omega** integration prose (records 7-9 mostly
  green, two- and three-mode fusion described).
- **Invalid-CAS error explanation** rendering (records 22, 23, 24
  green — explains what's wrong about the source).
- **Identifier copy via cas_prefix attention** on shorter sources (Ω
  names, register letters, domain letters survive into the rendered
  prose in non-fractal records).
- **Postprocessor scaffold composition**: identifier_repair +
  rpm_repair + meta_logic_repair + generation_cleanup +
  fractal_repair work together to refine outputs.
- **Coherent connective-tissue prose** in all 24 records. The model
  speaks fluent English with CAS-aware vocabulary.

v0's strengths are: short-shape rendering + invalid-CAS explanation +
2-3 noetic-class compositions + coherent prose.

## 2. What v1d / v1e failed

### v1d failed (2026-05-09 to 2026-05-10)

- **Cleaner corpus + targeted regen + 2-epoch retrain** could not fix
  records 13/14/15 (long fractal sequences). v1d audit dropped
  acceptable+ from 18/24 → 15/24.
- More data and longer training are not the lever.

### v1e Phase 1B / β2 failed (2026-05-10 to 2026-05-11)

- **Phrase-trie constrained decoder + leaf-exit boundary + first-n
  comparator + EOS bias + length cap**: decode-time levers hit
  slot-commit 35/35 (mechanism works) but full_seq_match plateaued
  at 0/35. Trailing prose contains noetic indicators the verifier
  can't distinguish from sentence-closing prose.
- Best decode-side outcome: G_baseline (lever 3 + first_n_mode)
  reached first-n 33/35 with Record-14 prose preserved — but this
  required ACCEPTING that "extra trailing noetics are tolerable",
  which user explicitly rejected ("A fractal sequence is ordered
  and bounded. Extra trailing noetics are extra states.")

### v1e Phase C failed (2026-05-11)

- **4 aux heads + 1-epoch fine-tune from v1c**: 24-pack regressed
  18/24 → 12/24. Specific damages:
  - 5 truncations in long-output categories (H_stop did the opposite
    of intended — model now runs out of token budget instead of
    stopping cleanly).
  - Stage-variable copying broken in rpm_chain (model stalls on a
    single identifier, fails to advance through let-bindings).
  - Token-level corruption ("ABeing", "stageD3_3_0233333" with extra
    digits).
- Aux losses fired correctly per task, curriculum worked, LM loss
  stable — but the model regressed. Telemetry-clean training does not
  imply eval-clean model.

### The structural finding that emerged from the failures

**The v0 checkpoint's prose distribution is the binding constraint.**
Closing prose like "...and finally muscle memory took over" emits ^7
(muscle memory). Trailing prose is structurally identical to
sentence-closing prose. Decode-side suppression breaks closing prose;
training-side aux supervision perturbs the prose distribution itself,
damaging non-fractal records.

Both routes — masking outputs and adding training signal — confirm
that v0's prose distribution is the bottleneck. **The fix has to be
in the representation, not in the output filter or the head heads.**

## 3. Which failure modes simplex is supposed to solve

The architecture R&D synthesis (`project_simplex_redesign_revisit_after_v0.md`)
named simplex Δ°₃₉ + Fisher-Rao metric as the principled architecture.
Failure modes simplex addresses, mapped to the v1d/v1e evidence:

### 3.1 Cardinality + ordering is a representation problem, not a decode-time problem

**v1e evidence:** decode-time levers can land the right slot phrases
in source order (35/35 slot-commit), but the surrounding prose still
emits arbitrary noetic indicators. The MODEL doesn't internally know
"K slots, then stop."

**Simplex response:** Δ°₃₉ is the open probability simplex over the
40 cognitive states (10 Noetics × 4 Domains). The model's cognitive
state at each generation step IS A POINT on Δ°₃₉. Trajectory
geometry (geodesics, Fisher-Rao distance) lets the model represent
sequence cardinality + position as a GEOMETRIC property of the
trajectory through state space, not as something to be supervised
externally.

### 3.2 Trailing prose noetic contamination

**v1e evidence:** the model emits ^7 in "and finally muscle memory
took over" without intending it as a fractal slot. The prose
distribution is "noetic-dense" — every connective uses Noetic
vocabulary because the corpus was generated that way.

**Simplex response:** the simplex parameterization makes the model's
NOETIC CHOICE explicit as a state vector at each step. The decoder
samples on the simplex, not in English vocab space. Surface prose
is rendered from the simplex state by a small typed-fiber projection.
"What noetic is active" and "what prose surface is emitted" become
independently controllable.

### 3.3 Identifier copy via attention is fragile

**v1e evidence:** Phase C's aux-head training perturbed
cas_prefix→identifier-copy attention, breaking stage-variable
copying in rpm_chain. The current model treats identifiers as
arbitrary token sequences; gradient noise displaces them easily.

**Simplex response:** identifier copying is a TYPED operation on
typed fibers (per `project_path_c_base_manifold_typed_fibers_correction_2026_05_07`).
Stage variables, Ω names, coefficients, register letters become
named slots in the model's representation, not arbitrary token
sequences. Aux gradients can't break what's typed-constrained.

### 3.4 Drive head ambiguity

**v1c+scaffolds evidence:** drives are sometimes rendered correctly
(F2 wisdom, F3 vitality), sometimes lost. The R&D synthesis identified
this as a simplex-redesign target: drives should be 7-D intensity
vectors, not categorical slots.

**Simplex response:** explicit 7-D drive vector in the model state.
F1-F7 are co-present at different intensities, not mutually
exclusive. Drives are a typed fiber over the base simplex.

### 3.5 Per-token traceability

**Current state:** trace is engineered via probes (Mode 7 attribution),
not structural. `feedback_traceability_is_the_whole_purpose` says
this is load-bearing.

**Simplex response:** every token's generation point is a Δ°₃₉
coordinate. The trace IS the trajectory through state space, no
external probe needed. Traceability becomes a geometric property,
not engineered.

## 4. Minimum viable simplex checkpoint

A buildable target that proves the architecture works WITHOUT trying
to solve everything. Mapped to what we can ship in ~6-8 eng-weeks
(rather than the full 10-14 weeks of the synthesis estimate).

### 4.1 Core architectural pieces (must-have)

| Component | What it does | Approx eng-weeks |
|---|---|---|
| **Δ°₃₉ encoder** | Map source CAS expression → simplex sequence in `R^40` with strict `p_k > 0` constraint. The encoder's "pooled hidden state" becomes "trajectory representative" on the simplex. | 2 |
| **Fisher-Rao geodesic loss** | Loss term that measures the trajectory's distance from the target trajectory in Fisher-Rao metric, not just per-token cross-entropy. Encourages the model to take the right path through state space, not just hit the right tokens. | 1.5 |
| **Typed fiber decoder** | Decoder is NOT a free LM; it's a typed-fiber projection from Δ°₃₉ coordinates to surface prose. Identifiers (Ω, stage vars, coefficients) flow through typed slots; prose connective tissue flows through a small free-form path. | 2 |
| **Compiler-validated generation** | Every generated CAS expression must compile. Generation that produces invalid CAS is rejected and retried via Fisher-Rao trajectory adjustment. | 1 |

Total: ~6.5 eng-weeks for the core.

### 4.2 What the MVP DOES NOT have (deferred to v1+)

- **CABS / geodesic memory layer** — deferred until simplex base is
  proven on shorter records. (See §5.)
- **Full 7-D drive parameterization** — start with categorical drives
  matching v0, expand to 7-D intensity vectors in v1.1.
- **Topos reasoner / intuitionistic 3-valued logic** — the Phase 4
  scope in CLAUDE.md is post-MVP.
- **Cognitive Fractal X.Y.Z engine** — the simplex MVP handles
  fractals as ordinary sequences via Fisher-Rao trajectory; the
  Fractal X.Y.Z generative engine is a v1.1+ enrichment.

### 4.3 Promotion gate for MVP simplex

Direct comparison to v0-rc1's 18/24 baseline:

- **Equal or better on the 24-pack** — at minimum 18/24 acceptable+.
- **Full seq_match on Phase 1B fractal suite** ≥ 20/35 (the gate v1e
  couldn't hit).
- **NO truncations** on long-output categories. The simplex's typed
  fiber decoder must respect output-length bounds inherently.
- **Stage-variable copying clean** — same byte equality to v0 on
  rpm_chain identifier slots, ideally better on per-stage content.
- **v0-canary baseline holds** when MVP simplex is used with
  decoder-off mode (= v0 backbone path preserved through the
  architectural change).

If the MVP simplex hits these targets, the architecture is proven and
v1.1 (drives + Fractal X.Y.Z + topos reasoner) is funded. If it
misses, the simplex thesis itself is in question — at that point the
decision is to either redesign simplex or pivot to a different
architectural axis (more involved, e.g., a different state-space
geometry).

### 4.4 What this MVP can't decide

- Whether the simplex's typed-fiber decoder produces FLUENT prose.
  Risk: the geometric constraint over-constrains prose generation,
  giving stilted output (the same failure mode β2 produced from the
  EOS bias side, but via the architecture path).
- Whether CABS retrieval can plug in cleanly. The MVP doesn't load
  CABS, so this is unanswered.
- Whether the simplex generalizes beyond fractals — the v0 24-pack
  has 8 categories; simplex MVP must handle all 8, not just
  fractals.

Each unknown becomes a v1.1 design question after MVP ships.

## 5. How CABS / geodesic memory plugs in later

CABS (Cognitive Architecture Belief Substrate) was scoped in
`project_cabs_gravity_v2_thesis_2026_05_09.md` BEFORE v1e was attempted.
The thesis was held until v1 hygiene + truncation/routing fixes
landed — which they did via v0-rc1.

The plug-in point with simplex:

**Simplex provides the GEOMETRY.** Every model state is a point on
Δ°₃₉, every trajectory is a path through state space, distances are
Fisher-Rao.

**CABS provides the MEMORY.** A retrieval layer that finds belief
states from a stored corpus by geodesic distance on the same Δ°₃₉.
"Idea gravity" = belief mass weighted by Fisher-Rao distance to the
current state.

Together: when the model is at simplex coordinate $p$ at step $t$,
CABS retrieves the nearest stored belief states $\{b_1, b_2, ...\}$ by
geodesic distance and feeds them as context into the typed-fiber
decoder. Memory continuity emerges as gravitational attraction
toward stored beliefs.

**Sequencing:**

1. Simplex MVP ships, validates on 24-pack + fractal suite.
2. CABS retrieval layer is added as a v1.1 enrichment (~3-4 eng-weeks
   per the prior thesis estimate).
3. The combination ("simplex base + CABS memory") becomes the v1.1
   release candidate.

**Not part of MVP.** CABS retrieval design depends on the simplex
encoder's actual state-space geometry. Designing CABS before the
simplex base is proven would be premature optimization — and would
risk the same "build everything at once and find out it doesn't
work" failure mode that the v1e Phase C aux-heads stack hit.

## 6. What I'm NOT proposing

To stay disciplined against the v1e anti-recidivism guardrails
(`project_v1e_killswitch_tripped_simplex_pivot_2026_05_11`):

- **NOT** a fine-tune of v1c with simplex heads. The simplex MVP
  trains from scratch on a new architecture, not as a continuation
  of v1c. v1c is preserved as v0 — untouched.
- **NOT** a multi-head v1c-resumed run. C proved that fine-tuning
  v1c destabilizes it.
- **NOT** another decode-time lever stack on the v0 checkpoint.
  Phase 1B/β2 saturated those.
- **NOT** an aux-supervision approach to teach v0 cardinality/stop.
  Phase C proved that aux gradients perturb the LM head.
- **NOT** more SDG / cleaner corpus / one-more-epoch attempts. v1d
  proved data is not the lever.

The simplex rebuild is a NEW architecture trained from scratch on
the same corpus, with the typed geometry constraint built in. It
is NOT v1e iteration.

## 7. What I need from user before proceeding

Three sign-off questions:

1. **Does the simplex MVP scope (§4.1: encoder + Fisher-Rao loss +
   typed fiber decoder + compiler-validated generation, ~6.5
   eng-weeks) match your appetite?** Or do you want a tighter MVP
   (e.g., drop compiler-validated generation, just shipping
   trajectory + decoder)?

2. **Does the deferred list (§4.2: CABS, 7-D drives, topos reasoner,
   Fractal X.Y.Z) match your sequencing?** Or do you want any of
   these in the MVP?

3. **Is the promotion gate (§4.3: ≥18/24 acceptable+, ≥20/35
   fractal full seq_match, no truncations, identifier copy clean,
   v0-canary holds in fallback mode) correct?** Or do you want
   stricter / looser thresholds?

After your sign-off, I would:

a. Run a **6-agent R&D recon** (Wave-1 specialists × 4 architectural
   pieces + Wave-2 critics × 2) to produce concrete build specs for
   the four MVP components. Same pattern as the v1e Phase 1B
   6-agent R&D team that worked well.
b. Write a Stage-by-stage execution plan with explicit user-gates
   for: CPU smoke, RunPod first epoch, MVP eval, promotion gate.
c. Surface that plan for your sign-off before any code change.

Total elapsed before any code change: ~2 days of plan work.
Total elapsed before any GPU spend: ~3 eng-weeks of implementation
(encoder + decoder + losses) + 1 eng-week of CPU smoke.

## 8. Where this fits in durable project memory

This plan is the SECOND major architecture pivot in the project's
recent history:

- **2026-04-30**: NL-front-door pivot (CAS-CLM frozen backbone →
  CAS-Native NL encoder + structured heads). Captured in
  `project_cas_transformer_modality_mismatch_pivot.md` +
  `project_cas_transformer_nl_front_door_architecture.md`.
- **2026-05-11 (today)**: Simplex Δ°₃₉ rebuild pivot (cheap-paths
  exhausted via v1d/v1e → architectural change required). This doc.

Each pivot has been EVIDENCE-DRIVEN. The first pivot came from CAS
Transformer's modality mismatch (~100× underperformance vs hash
features). The second pivot comes from v1d/v1e exhausting all cheap
levers on the v0 prose distribution.

This is project memory the simplex implementation should inherit:
**we don't pivot until we have evidence the current architecture is
the binding constraint, and we don't iterate at the cheap level
once that evidence is in.**
