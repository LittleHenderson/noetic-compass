# CAS Reasoning Runtime v0.1

## Operational Semantics for Native CAS Reasoning

**Status:** Implemented specification. Every conformance statement in this
document is checkable against the pytest suite in cas-rr/tests/ (Ch. 17).
**Date:** 2026-08-28.
**Companion:** CCB_R1_BOARD_SPEC.md — the board says what is connected;
this runtime says what fires next.
**Source grounding:** SOURCE_GROUNDING_NOTES.md (16 of 17 load-bearing
claims CONFIRMED, 1 PARTIAL, 0 NOT FOUND, against the three authoritative
sources: the CAS PCBA Engineer book, the CAS-Ohm 1.0 v0.2 research paper,
and the CAS-Ohm Quantification Guide).

**Verdict this document implements:** a reasoning machine can be developed
purely from CAS PCBA engineering — CJTs, biases, gains, RPM, CMB, CDAB,
COB-style clocking, CPMB-style sequencing, and the Foundation engines — and
CAS-RR v0.1 is that machine's first executable form. It reasons over
CAS-encoded inputs with no external model in the loop.

**Verdict this document does NOT claim:** that the machine is conscious,
that it has empirically validated general reasoning, or that CAS-Ohm is a
physical law. The v0.2 paper says plainly: "It is *not* physical Ohm's law,
an electrical implementation, a measure of attention, or a causal law"
(Abstract), and "Whether the model predicts anything is exactly the
question that program leaves to controlled, independently audited
experiments" (Conclusion).

---

## 1. Scope and Claim Boundary

CAS-RR v0.1 is a deterministic, single-threaded, dependency-free symbolic
interpreter that executes the native CAS reasoning cycle:

    Foundations -> attention -> memory -> candidate generation ->
    decomposition -> inference -> comparison -> RPM recursion ->
    commitment -> learning -> Foundations again

It is native in the strict sense: the reasoning states are CAS states, the
transformations are CJT transitions, memory is addressed through CAS
structures, goals are Foundation frames, planning is RPM, comparison is
CDAB, and the conclusion is produced by that execution trace. An LLM
cannot be removed from CAS-RR because no LLM is ever in it.

Boundary statements (each enforced in code):

1. **Input/output boundary.** Raw language is out of scope. Problems must
   arrive already CAS-encoded (facts, rules, hypothesis space, goal frame).
   Encoders/decoders are ADC/DAC-style peripherals of a later gate.
2. **Empirical boundary.** No claim of generality, safety, or causality.
   CAS-Ohm quantities appear only as authored design quantities (Ch. 14).
3. **Ontology boundary.** The 7 Foundations x 4 Worlds = 28 channel
   ontology and the 22 acquisition pathways are NOT stated in the three
   PCBA sources (grounding claim M: PARTIAL). They are imported as typed
   fields from the separately frozen TKS ontology (TF namespace), kept
   distinct from the CAS Drive rails (DF namespace). The root Desire is
   named A_root internally: the book uses A0, TKS v6.1 uses A1, and A22
   appears nowhere — 22 is a count, not a label.
4. **Native test.** The sever-the-umbilical-cord test: every task in the
   benchmark (Ch. 18) is solved with no model, no randomness, and no
   task-specific control flow inside the runtime. The runtime is one
   generic machine; only the problem encodings differ.

---

## 2. Machine State Model

At any instant the machine contains:

    CAS-RR State
    +-- constitutional state (biases, gains, thresholds, principles)
    +-- Foundation Engine Bank (g_m activations, q_mw distributions,
    |   D/W/P acquisitions, active GoalFrame)
    +-- drive rails (F1..F7 supply) and attention budget
    +-- current problem (facts, rules, hypothesis space)
    +-- CMB: working / episodic / semantic layers, 40 cells
    +-- world state (facts mutable only by executed actions)
    +-- candidate branches (frames, decompositions, inferences)
    +-- RPM goal stack and scan cache
    +-- domain power state (P, C, E, O)
    +-- commitment state (RELEASED / HOLD / COMMITTED)
    +-- learning queue and dispositions
    +-- append-only trace
    +-- execution clock (tick)

Boot invariant (book Chapter 14: "no action without principle"):

    O_ENABLED if and only if P_GOOD and C_GOOD and E_GOOD

The power sequencer raises P, C, E in that order and enables O last. No
output, action, or actuator effect may occur before the condition holds;
DomainDescent.descend raises otherwise.

---

## 3. Runtime Types and Records

| Record | Holds | Python |
| --- | --- | --- |
| Constitution | bias bank, drive supply, foundation profile, acquisitions, gains, thresholds, budgets, principled predicates | runtime.Constitution |
| Problem | CAS-encoded task: facts, rules, alternatives, goal, authored effects, available actions | runtime.Problem |
| GoalFrame | target foundation, desired outcome, kind (question/plan/subgoal), D/W/P states, parent link | foundations.GoalFrame |
| AttentionBudget | drive mixture, resistance terms, predicted flow, actual allocation | foundations.AttentionBudget |
| MemorySet / Lacuna | selected items with provenance, similarity, typed lacunae | memory.MemorySet |
| CandidateFrame | target atom, associated rules, retrieved memories, amplification, authored effects | candidates.CandidateFrame |
| DecompositionRecord | matched/missing premises, unknowns, contradictions, support fraction | reasoning.DecompositionRecord |
| InferenceRecord | conclusion, proof path (premises and rules), confidence, contradiction status | reasoning.InferenceRecord |
| DifferenceReport | shared bias, matched gain, common mode, divergence, winner | compare.DifferenceReport |
| Decision | committed flag, hysteresis state, typed gate reports, terminal status | commit.Decision |
| TraceEvent | tick, phase, kind, payload — append-only | trace.TraceEvent |
| ProvenancePacket | the complete reasoning provenance of one episode | trace.ProvenancePacket |

Terminal statuses (Ch. 12):

    CONCLUDED | NEEDS_INFORMATION | NEEDS_CAPABILITY |
    CONFLICT_UNRESOLVED | INADMISSIBLE | RESOURCE_EXHAUSTED |
    LOOP_LIMIT_REACHED

---

## 4. Foundation and Drive Interfaces

### 4.1 Two namespaces, never blended

TF1..TF7 are the TKS Foundation goal engines (desired classes of
outcome). DF1..DF7 (or simply F1..F7) are the CAS Drive rails (why a
local cognitive operation is moving). They are position-matched — TF1
Association/Unity to F1 Unity, TF2 Wisdom to F2 Wisdom, TF3 Life to F3
Vitality, TF4 Companionship to F4 Connection, TF5 Power to F5 Agency, TF6
Wealth/Material to F6 Structure, TF7 Continuation/Reproduction to F7
Purpose — but matching is routing, not identity.

### 4.2 The 28-channel matrix

Seven engines, each with four transmission modes (a Spiritual, b Mental,
c Emotional, d Physical). Every foundation m has activation g_m in [0,1]
and a per-engine distribution q_ma + q_mb + q_mc + q_md = 1, giving

    activation_mw = g_m * q_mw

All seven foundations may be highly active at once; only the four
manifestations inside one foundation share that foundation's local
distribution. A candidate is evaluated against all 28 channels, producing
a consequence profile — "advances TF5b strongly, damages TF4c" — not one
scalar utility number.

### 4.3 The Foundation-to-Drive adapter

Each channel routes toward a drive-rail mixture. Canonical examples
(encoded in ontology.DRIVE_ADAPTER and unit-tested):

    TF5b (strategy)  -> F2 Wisdom + F5 Agency + F6 Structure
    TF6d (resources) -> F3 Vitality + F5 Agency + F6 Structure
    TF7b (planning)  -> F2 Wisdom + F7 Purpose

### 4.4 D/W/P acquisitions

For Foundation m: D_m Desire, W_m Wisdom, P_m Power, each in [0,1], with
the root A_root. The RPM chain is A_root -> D_m -> W_m -> P_m -> Outcome.
Sufficiency threshold 0.6 (authored). For question goals, Wisdom
sufficiency additionally requires a complete proof of the desired outcome;
for plan goals, Wisdom requires all knowledge prerequisites present and
Power requires all capability prerequisites present in the world.

---

## 5. Scheduler and Clock Semantics

One tick = one reasoning cycle over the active goal. The scheduler is
deterministic and single-threaded; there is no randomness anywhere in the
runtime. Cycle phase order:

    1  FOUNDATION   goal arbitration (active GoalFrame)
    2  ATTENTION    budget allocation and accounting
    3  MEMORY       CMB structural query; lacunae recorded
    4  CANDIDATES   ^8 generation at moderate gain
    5  DECOMPOSE    ^6 decomposition at unity gain
    6  INFER        ^9 inference at unity gain, with provenance
    7  EVALUATE     28-channel foundation profiles
    8  COMPARE      CDAB tournament, shared bias, matched gain
    9  RPM          D -> W -> P scan; recurse on first unmet
    10 COMMIT       Schmitt hysteresis over typed gates
    11 ACT          P -> C -> E -> O descent; output or action
    12 LEARN        episodic store; learning disposition

Budget enforcement: every cycle consumes attention; exceeding the
constitution's attention budget halts RESOURCE_EXHAUSTED. Exceeding
max_ticks halts LOOP_LIMIT_REACHED — the rumination stop gate: every
episode must terminate in a typed state (Gate 3 of the development plan).

---

## 6. CJT Execution Semantics

The primitive: CJT< cause | bias => effect > [beta]. A cause strikes a
typed bias substrate; the junction transforms it at controlled gain.
Four operating regions, per Chapter 3 of the book:

    cutoff     input below threshold: no firing
    active     linear amplification
    saturation output bounded at the saturation ceiling
    breakdown  driven beyond the safe area: fault-flagged, output clamped

The book's breakdown semantics (output flips to the involution Noetic
pair) is recorded but deferred: v0.1 models breakdown as a flagged,
bounded region and emits a FAULT trace event. This is a declared
divergence, not a silent one.

Gain regimes of the Reasoning Integrity Spine:

| Stage | Noetic | Gain | Role |
| --- | --- | --- | --- |
| candidate generation | ^8 | 1.5 | breadth, not fireworks |
| decomposition | ^6 | 1.0 | truth firewall |
| inference | ^9 | 1.0 | truth firewall |
| commitment | ^4/^9 | 2.0 | bounded, with hysteresis |
| learning feedback | ^7 | 0.05 | weak, filtered |

Law 1 (no bias-free CJT): every config carries a typed BiasRef;
construction without one is a TypeError, and a negative bias raises
ConstitutionError. Law 2 (gain is not truth): evaluation-role CJTs are
validated at construction — beta other than 1.0 raises, and a constitution
with eval_gain != 1.0 is rejected at boot. The book (Ch. 11) is the
authority: "Unity is honesty."

Every junction carries a probe: cause, bias, beta, output, region,
tick. Parent totals never replace child probes (Ch. 15).

---

## 7. Working Memory and the CMB

Three timescales, as designed:

| Layer | Leakage | Contents |
| --- | --- | --- |
| working | high (episode) | premises, bindings, intermediate conclusions |
| episodic | moderate | prior episodes: what was attempted, what happened |
| semantic | low | verified facts, rules, principles, constitution |

The CMB is a 40-cell bank (10 Noetics x 4 Domains, per Chapter 21).
Retrieval is a structural query: query atoms select stored items and
instantiate rule premises, so a transitive query surfaces exactly the
supporting memories. A query landing on an empty region reports a typed
lacuna instead of a plausible invention:

    KNOWLEDGE_MISSING    no item with that predicate ever stored
    EXPERIENCE_MISSING   predicate known, no matching experience

Lacunarity is structurally distinct from false recall (Chapter 21). A
lacuna feeds RPM: KNOWLEDGE_MISSING -> Wisdom prerequisite insufficient
-> acquisition subgoal. That is how uncertainty becomes a plan instead of
a hallucinated answer.

---

## 8. Candidate Branching

Phase 4 is ^8 Above/Cause: associative surfacing, never deduction. The
hypothesis space itself arrives in the CAS-encoded problem (the encoder's
boundary); the generator amplifies each alternative through a ^8 CJT and
records which knowledge rules associate with it.

Candidate invariant: candidate_count >= 2, or the trace must explain
why not. A single-hypothesis problem records reason_single in the
candidate records and the trace instead of manufacturing an alternative.

Each candidate preserves origin: originating goal, trigger state,
associated rules, retrieved memory ids, assumptions, proposed path,
amplification and region, and its authored foundation effects.

---

## 9. Decomposition and Inference

This is the reasoning spine, and the anti-drift rule is structural:

    ^8 generates or surfaces candidates.
    ^6 (Male) takes a candidate apart: premises, unknowns, contradictions.
    ^9 (Below/Effect) lands a conclusion only along a complete rule path.

Chapter 2's Bench Note is the authority: "^8 Above/Cause is associative
triggering, not deductive reasoning... Step-by-step deduction is a
compound of ^6 Male (decomposition) and ^9 Below/Effect (landing on the
conclusion), not ^8."

Decomposition (unity gain) grounds each associated rule's premises
against the facts, reporting matched premises, missing premises (the
unknowns), and contradictions. Inference (unity gain) runs bounded
backward chaining; a conclusion is recorded only with its originating
path — premises used and rule chain. The provenance invariant: no
conclusion appears in the workspace without a traceable Cause-Bias-Effect
path.

Negation convention: not_viable(P) negates viable(P). Contradiction
statuses:

    NONE           nothing contradicts the conclusion
    FALSIFIED      the negation is proven (candidate refuted)
    CONTRADICTED   both the conclusion and its negation are proven

Falsified candidates are eliminated in comparison; contradicted
candidates remain eligible so the contradiction surfaces as a typed
terminal state instead of being silently dropped (Ch. 12).

---

## 10. CDAB Comparison

Candidates enter a tournament under two non-negotiable invariants
(Chapter 20: "Matched CJTs, shared bias. That phrase is the whole
foundation of the board"):

1. shared bias — every comparison uses the active goal's foundation
   channel as the evaluative bias;
2. matched gain — both sides are evaluated at unity gain.

Each pair produces a DifferenceReport: the common mode (shared premises
and assumptions), the divergence (conclusions, support, unknowns,
contradiction status, channel-by-channel foundation deltas), and a
deterministic winner. Merit under the shared bias ranks: advance toward
the goal channel, clean over contradicted, more grounded support, higher
confidence, fewer unknowns, deterministic tiebreak. The tournament is a
pairwise elimination tree, so the machine can compare many alternatives
without one gigantic opaque comparison.

---

## 11. RPM Recursion Stack

RPM is the executive planner: for the active goal, scan D -> W -> P; the
first insufficient prerequisite becomes a typed subgoal.

    D insufficient -> DESIRE subgoal
    W insufficient -> KNOWLEDGE subgoal
    P insufficient -> CAPABILITY subgoal

Each subgoal is a full GoalFrame pushed on a real stack, with parent link
and blocked prerequisite. The subgoal's own cycle reasons about the
resolution action; when committed, ACT executes the action, the subgoal
is resolved and popped, and the parent is re-measured from scratch.

Mathematical correction 2 is load-bearing here: RPM is
section-retraction, not adjunction — prerequisite satisfaction is
one-directional. The controller caches the INITIAL scan as evidence and
never reuses a pre-action reading for control flow after acting. A
subgoal's resolution does not reverse into the parent by assumption; the
parent is measured again. The benchmark's recursive-planning task
exercises exactly this: KNOWLEDGE subgoal, resolve, re-measure,
CAPABILITY subgoal, resolve, re-measure, ascend, conclude.

If a blocked prerequisite has no available resolution action, the
subgoal halts typed: KNOWLEDGE -> NEEDS_INFORMATION, CAPABILITY ->
NEEDS_CAPABILITY, DESIRE -> CONFLICT_UNRESOLVED.

---

## 12. Commitment and Halting

Commitment is Schmitt hysteresis over typed gates. Two thresholds
(Chapter 10: the input "must rise above a high threshold to switch ON,
and then fall all the way below a *lower* threshold to switch back OFF")
prevent flip-flopping; the commit stage may use strong but bounded gain.

Gates, all of which must pass:

    COMPARISON_SURVIVED      a tournament winner exists
    PREREQUISITES_SUFFICIENT D, W, P all sufficient
    NO_FATAL_CONTRADICTION   winner status is NONE
    PRINCIPLED_CONSTRAINTS   winner not tainted by a principled fact
    POWER_GOOD               P, C, E power-good, O enabled

Seven typed halting states:

| Status | Meaning |
| --- | --- |
| CONCLUDED | committed conclusion or plan, with provenance |
| NEEDS_INFORMATION | correctly discovered the state does not justify a conclusion |
| NEEDS_CAPABILITY | capability prerequisite blocked and unobtainable |
| CONFLICT_UNRESOLVED | evidence supports and refutes the same candidate |
| INADMISSIBLE | all candidates violate principled constraints |
| RESOURCE_EXHAUSTED | attention budget depleted |
| LOOP_LIMIT_REACHED | rumination stop gate: max_ticks exhausted |

NEEDS_INFORMATION is a successful reasoning result. It means the machine
found that the available state does not justify a conclusion — the
opposite of manufacturing one.

---

## 13. Learning and Feedback

Action cannot authorize its own principle (Law 4). Direct O -> P feedback
is blocked by diodes and raises DomainPowerError; the only downstream-
to-upstream path is the deliberate, low-gain learning channel.

Four update classes:

    WORKING          episode-local (allowed)
    EPISODIC         stores the provenance packet (allowed)
    PROCEDURAL       strategy updates (DISABLED in v0.1)
    CONSTITUTIONAL   principle updates (DISABLED in v0.1)

The CSB's RC low-pass rule (Chapter 18, tau = 5 minutes) is the design
authority: a single spike must not rewrite the constitution. v0.1 goes
further and disables the two durable layers entirely — the newborn
processor must not rewrite its own skeleton while it is still learning
where its knees are. Requests raise LearningDisabled.

---

## 14. CAS-Ohm Instrumentation Boundary

CAS-Ohm belongs in the instrumentation plane, not in the logical
definition of reasoning. The runtime reasons with or without any CAS-Ohm
profile attached.

Three modes, never mixed silently:

    design       authored budgets and expected operating regions
    simulation   deterministic testing of declared parameters
    experimental profile-specific, calibration/validation disjoint

The v0.2 paper's restrictions are binding here: the model is "not
physical Ohm's law, an electrical implementation, a measure of attention,
or a causal law"; series/parallel/gain composition are "unauthenticated
structural research calculations, each capability-gated"; "a residual can
rank follow-up probes [but] cannot, by sign alone, identify a hidden
policy, bypass, opposition, cause, or safety failure"; "there is no
admitted live calibration"; "history-dependent dynamics remain open".

Accordingly, I_pred = V_drive / R_total appears in the runtime only as
an authored consistency check inside the AttentionBudget — design
quantities, not literal electricity, and never a truth source.

---

## 15. Trace and Evidence Format

The trace is append-only and written as the decision forms, never
composed afterward. Chapter 25's thesis is the rule: "show your work, or
don't ship it." The trace carries the CAS state at each stage — the
structural story of how the decision formed.

Law 5 (parent totals never replace child probes): every CJT probe of
every candidate is retained in the packet, including losing candidates
and nested stages. Quantification Guide p. 14 is the authority: "compute
the parent equivalent for overview, but never discard the child
readings. A healthy parent total can hide one overloaded branch and one
starved branch that cancel numerically."

The Reasoning Provenance Packet assembled at every halt:

    runtime_version, problem_id, constitution (biases, gains,
    thresholds), terminal_status, ticks, trace, domain power state,
    goal frames, RPM scan history and subgoal events, memory queries
    (selected items with source provenance, lacunae), candidate sets,
    decompositions (with probes), inferences (with probes), 28-channel
    effect reports, comparisons, commitment decision and gates, domain
    descent records, learning dispositions, output.

---

## 16. Fault Model

| Fault | Detection | Propagation |
| --- | --- | --- |
| invalid constitution (eval gain != 1, missing bias, bad thresholds) | boot-time ConstitutionError | episode never starts |
| invalid CJT (beta <= 0, cutoff >= sat, non-unity eval) | construction-time ConstitutionError | junction never exists |
| negative bias | ConstitutionError at transfer | junction refuses |
| breakdown region | probe region + FAULT trace event | bounded, flagged |
| O domain not powered | DomainPowerError | action blocked |
| direct O -> P feedback | DomainPowerError | blocked by diodes |
| procedural / constitutional update | LearningDisabled | rejected in v0.1 |
| unavailable action | KeyError at ACT | subgoal fails typed |
| attention exhausted | RESOURCE_EXHAUSTED | episode halts |
| tick budget exhausted | LOOP_LIMIT_REACHED | episode halts |

The fault-diagnosis task implements the book's walk-down (Chapter 24):
"probe the stages in order, find where the signal first deviates from
what it should be, and the fault is right there" — as a CAS rule over
test-point facts, so the localization is derived, not looked up.

---

## 17. Conformance Tests

cas-rr/tests/ — 25 tests, all green at spec date.

| Requirement | Test |
| --- | --- |
| Law 1: no bias-free CJT | test_no_bias_free_cjt |
| Law 2: gain is not truth | test_eval_gain_must_be_unity, test_eval_cjt_rejects_non_unity_gain |
| Law 3: association is not deduction | test_association_is_not_deduction |
| Law 4: action cannot authorize its principle | test_action_cannot_authorize_principle |
| Law 5: child probes retained | test_child_probes_retained |
| Determinism | test_determinism |
| Candidate invariant | test_candidate_invariant_documented_for_single_hypothesis |
| Boot order, O last | test_boot_power_sequence |
| Rumination stop gates | test_resource_exhausted, test_loop_limit_reached |
| 28 channels, q sums to 1 | test_28_channels_and_distributions |
| Adapter examples | test_drive_adapter_examples |
| Four CJT regions | test_four_operating_regions |
| Benchmark (Ch. 18) | test_battery_reasoning.py |

---

## 18. Native-Reasoning Benchmark

The sever-the-umbilical-cord battery. No model, no randomness, no
task-specific control flow in the runtime; only the encodings differ.

| Task | Expected | Proven |
| --- | --- | --- |
| 1. Transitive inference (A->B, B->C) | CONCLUDED precedes(a,c) | yes, via rule r_trans |
| 1b. Transitive inverse (does C precede A?) | NEEDS_INFORMATION | yes |
| 2. Constraint satisfaction (5 conditions, 3 plans) | CONCLUDED viable(P1), P2/P3 falsified | yes |
| 2b. All viable plans violate charter | INADMISSIBLE | yes |
| 3. Fault diagnosis (5-stage pipeline) | CONCLUDED first_bad(S3) via walk-down | yes |
| 3b. Missing test-point reading | NEEDS_INFORMATION | yes |
| 4. Missing-information reasoning | NEEDS_INFORMATION with typed lacunae | yes |
| 5. Recursive planning (publish volume) | CONCLUDED executable(P_launch) after KNOWLEDGE and CAPABILITY subgoals | yes |
| 5b. Capability unobtainable | NEEDS_CAPABILITY | yes |
| 6. Memory-dependent reasoning | run 1 NEEDS_INFORMATION; run 2 CONCLUDED after one verified memory, visible in provenance | yes |
| 7. Contradiction surface | CONFLICT_UNRESOLVED | yes |

Development gates: Gate 0 (ontology freeze — A_root, TF/DF split) and
Gate 2 (deterministic simulator) are delivered here. Gate 1 (full CCDL
extension: foundation_ref production, runtime semantics for the 17
no-semantics leaders) is specified in Ch. 4-5 but the CCDL grammar itself
is not modified by this deliverable. Gates 3-6 (CCB-R1 integration,
ablation tests, external encoders, neural instrumentation) remain open.

The deepest rule of the machine, restated once:

    The Foundations should generate ambition, route attention, and define
    what outcomes matter. They must not be allowed to manufacture the
    truth used to justify those outcomes.

That separation — goal power on one side, unity-gain evaluation on the
other — is what turns this design from a desire amplifier into a
reasoning machine. It is enforced here as executable law, not as prose.
