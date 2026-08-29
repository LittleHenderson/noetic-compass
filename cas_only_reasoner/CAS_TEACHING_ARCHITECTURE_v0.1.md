# The CAS Teaching Architecture v0.1 — the Faculty, not the Oracle

**Source:** owner directive, 2026-08-28.
**Status:** ADOPTED. Extends `VERIFIED_COGNITIVE_APPRENTICESHIP_v0.1.md`
from language to everything. The crucial law:

    The teacher may propose knowledge and skill.
    The CNCM decides what becomes part of itself.

The bigger model is a FACULTY, not an oracle: it lectures,
demonstrates, invents exercises, attacks weak answers, proposes
repairs. CAS-SDG produces independent variations. The verifier
checks. CAS-RRK controls promotion. CMB stores what survives.

**Naming note:** the directive labels the teaching board "CCB-T1";
that identifier is already the Tool Board (`CCB_T1_v0.1/`). The
apprenticeship board is recorded as **CCB-A1** (Cognitive
Apprenticeship and Teaching Board, `CAS_APPRENTICE_v0.1/`).

## What the faculty can teach (fourteen domains)

1. **Languages** — lexical knowledge (multi-sense words, idioms,
   morphological families — "run" is four senses, never one fuzzy
   blob), grammar constructions, semantic roles, discourse and
   conversation; other human languages (Spanish, Mandarin, ASL
   structure...) each with own constructions but ONE CAS-Sem meaning
   layer — two sentences in different languages become the same
   internal proposition.
2. **World knowledge** — under the STRICTER fact protocol: every
   lesson carries claim, source, date/validity window, scope,
   exceptions, confidence, contradictory sources, verification
   method. Model-generated facts enter PROPOSED, never VERIFIED.
   Stable facts verify against trusted documents; CHANGING facts
   (laws, officeholders, prices, versions) must come from current
   retrieval, never the teacher's frozen memory. Typed destinations:
   stable fact → semantic memory; current fact → source-linked
   retrieval record; definition → CAS-Sem concept; procedure →
   procedural memory; experience → episodic; pattern → recipe/schema;
   hard boundary → constitutional memory, separately authorized.
3. **Reasoning strategies** — decomposition, hidden assumptions,
   cause vs correlation, competing hypotheses, counterexample search,
   analogy, constraints, backtracking, missing-information detection.
   The student extracts problem type, strategy, why it fit,
   intermediate states, failure points, alternatives, failure
   conditions — never just the teacher's final answer. The ^8
   association vs ^6→^9 deduction boundary stays enforced.
4. **Mathematics** — content AND habits (invariants, small cases,
   symmetry, counterexamples, representation changes, auxiliary
   variables, reduction to known theorems). The teacher never decides
   proof validity: teacher proposes → CCB-M1 compiles → exact checker
   tests → SDG varies → held-out transfer → procedural memory. A
   brilliant proposed proof can still contain one invalid step; the
   trusted checker holds the red pen.
5. **Programming** — syntax through architecture, plus HOW TO
   DIAGNOSE: reproduce, reduce, locate the first incorrect state,
   compete hypotheses, instrument, patch one thing, regress. Learned
   procedures carry contracts, pre/postconditions, failure modes,
   tests, complexity, security assumptions.
6. **Tool use** — when appropriate, inputs, output schema, common
   errors, permissions, result verification, when NOT to trust. The
   reusable procedure: recognize need → ToolIntent → permission →
   execute → validate → provenance → resume parent.
7. **Research methods** — literature search through claim boundaries.
   The teacher must NOT generate hypothesis, test, and grading
   standard from one hidden template and call it discovery — the D10
   audit exposed exactly that trap. Proper form: Teacher A proposes,
   Teacher B attacks, SDG produces controls, an independent verifier
   evaluates, EXTERNAL review determines novelty.
8. **Memory formation** — HOW to remember: summarization, event
   extraction, chunking, causal linking, cue creation, importance
   ranking, schema induction, consolidation, forgetting policies,
   reconstruction with the six evidence labels. Feeds CAS-GEM.
9. **Metacognition** — perhaps the most important: know / inferred /
   assumed / uncertain / need-a-clue / lack-knowledge / two-readings
   / memory-conflicts-source / depends-on-unverified-premise.
   Calibration, uncertainty decomposition, abstention. The student
   learns the METHOD of uncertainty, never the teacher's swagger.
10. **Social and conversational intelligence** — structural
    procedures (recognize frustration, acknowledge the actual
    concern, one precise clarification, match depth to user), not
    simulated feelings. Bad examples diagnosed, not just good ones
    imitated.
11. **Creativity** — methods, not outputs: map distant structures,
    preserve useful isomorphism, reject non-transfers, generate
    candidates. CAS-GEM supplies capsules; results labeled IMAGINED.
12. **Board design** — the teacher may propose components, CCDL
    schematics, test points, fault suites; the proposed board still
    must compile, pass DRC, simulate, survive fault injection, pass
    held-out tests, preserve authority invariants. The teacher
    designs; the foundry certifies nothing without receipts.
13. **Self-diagnosis and self-improvement** — trace inspection,
    first-failing-stage, value vs topology faults, repair hypotheses,
    descendant comparison, rollback. The teacher never gains
    promotion authority.
14. **Multimodal perception** — labels and explanations, but text
    alone cannot ground "red" or "behind": grounding needs images,
    audio, simulation, sensors, action and consequence.

## The five transfer channels (the key architectural insight)

    1 Explicit symbolic lessons   → CAS-Sem, procedural memory, CCDL
    2 Demonstration + induction   → recipes, strategy boards
    3 Neural distillation         → small REPLACEABLE neural subboards
                                    (proposal generators under CAS
                                    authority, always)
    4 Retrieval-linked knowledge  → source-linked memory + indexes
    5 Synthetic experience        → SDG curricula, protected fixtures,
                                    episodic records

## CCB-A1: the Cognitive Apprenticeship and Teaching Board

Pipeline: teacher proposal → lesson parser → prerequisite check →
SDG expansion → positives → minimal pairs → counterexamples →
held-out transfer → regression → provisional promotion → delayed
retention → durable promotion or rollback. Every lesson seals a
TeachingEpisode (identity, proposed content, examples, verification
method, accepted scope, exceptions, pre/post capability, provenance,
version, rollback pointer).

## The seven teacher roles — a faculty committee

Lecturer, Demonstrator, Socratic tutor, Curriculum designer,
Adversary, Critic, Research mentor. The same model should not fill
all seven for one lesson: one proposes, another criticizes, SDG
mutates, a frozen verifier grades, CAS-RRK promotes.

## Teaching metrics (new CNCM metrics)

    learning gain        dP_cap = P_after - P_before
    resistance reduction dR_cap = R_before - R_after
    transfer rate        held-out successes / held-out tasks
    teaching efficiency  dP_cap / teacher-compute cost
    retention            capability after delay / immediately after
    teacher dependence   teacher-assisted tasks / total tasks

The best teacher is not the prettiest explainer: it is the one whose
lessons become durable native capability at the lowest cost and
lowest false-lesson rate. CAS-Ohm profiles every lesson before/after
(P_cap up, R_cap down, active region, correct effect, held-out
transfer, no protected regression).

## Never autonomously teachable (suggestions only, no promotion)

The authority contract; the sole-writer state rule; the proof
checker; the trace verifier; protected benchmarks; constitutional
values; deployment permissions; rollback machinery; the definition of
improvement. A model can explain why a constitution might change. It
cannot vote itself the power to change it.

## The teaching order

    1 language structure          (expands access to everything)
    2 exact reasoning domains     (clean verification)
    3 coding and tool use         (practical capability)
    4 source-grounded knowledge   (citations + provenance)
    5 research and metacognition
    6 conversation, creativity, social pragmatics
    7 board design and self-improvement

## The deeper endgame

Teacher supplies answers → lessons → strategies → only hard examples
→ becomes a critic → occasional consultant → for mastered domains,
the CNCM teaches itself. The most important transfer is none of the
content: it is HOW TO DETECT WHAT IT DOES NOT KNOW, formulate the
missing prerequisite, construct a curriculum, test whether learning
occurred, and preserve only the improvements that generalize. Once
that procedure is native, every larger model becomes a potential
professor rather than a permanent prosthetic brain.
