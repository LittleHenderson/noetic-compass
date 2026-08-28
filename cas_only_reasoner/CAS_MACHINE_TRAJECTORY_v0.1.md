# CAS Complete Machine Trajectory Plan v0.1

**Source:** owner directive, 2026-08-28 (mid-session, verbatim substance
kept; a STATUS LEDGER against the working lane is appended at the end).
**Status:** MASTER BUILD PLAN for the CNCM. Companion to
`HYBRID_MACHINE_DOCTRINE.md` (which governs the language-cortex and
reference-band reporting posture).

---

## The central project

Build a complete cognitive machine whose language, reasoning, memory,
planning, verification, explanation, and improvement systems work as
one inspectable architecture. Two foundational layers sit beneath the
seven organs:

    CAS-Sem     gives the machine precise content to think about
    CAS-RRK     makes every component execute, retain state, branch,
                recurse, commit, learn, trace, and stop

The complete stack:

    Language Cortex             knows and communicates
            |
    CAS-Sem                     represents meaning
            |
    Reasoning Processor         thinks
            |-- Memory System   remembers
            |-- RPM Executive   plans
            |-- Verifier        checks
            |
    Commitment and Action
            |
    Trace Fabric                explains the real execution
            |
    Evolution Protocol          improves tested descendants

Everything executes on the CAS-RRK protected backplane. Everything is
validated and lowered by the CAS Compiler. The source's central
engineering law remains in force throughout: a Cognitive Circuit Board
does what its schematic, parameters, and test report establish, no
more and no less.

## The critical path (dependency order, not slogan order)

    1.  Authority and ontology freeze
    2.  Kernel IR and compiler boundary
    3.  Runtime kernel and trace
    4.  Semantic content representation
    5.  Native reasoning processor
    6.  Memory, RPM, and verification
    7.  Language and conversation
    8.  Governed learning
    9.  Controlled self-evolution
    10. Scaling and qualification

Three rules govern this order:
- Trace begins on day one, not after the machine is finished.
- Verification begins before broad language generation, because fluent
  error is still error.
- Evolution comes last, because a system must be able to test and
  restore itself before it is permitted to redesign itself.

## Phase 0 - Freeze the constitutional ground

Artifacts: AUTHORITY_MANIFEST.yaml, CAS_CORE_ONTOLOGY,
FOUNDATION_DRIVE_ADAPTER, COMPILER_RUNTIME_BOUNDARY, CAS_KERNEL_IR,
NON_GOALS, CONFORMANCE_PLAN. Frozen decisions: canonical Noetics
^0-^9; Domains P/C/E/O; Registers T/A/f/E; Drives F1-F7; TKS
Foundations separately typed from CAS Drives; 28 Sub-Foundations as
separately typed goal/consequence channels; one canonical Prime Desire
root; D/W/P as prerequisite states, not aliases; CAS-Ohm as
instrumentation only. The ^8-vs-^6/^9 distinction (associative
triggering vs decomposition-then-conclusion deduction) is frozen
before any reasoning instruction set. Exit gate: one typed definition
per core term, recorded disposition per source conflict, explicit
compiler/runtime boundary, stable Kernel IR schema, frozen golden
fixtures.

## Phase 1 - White-box execution spine (CAS-RRK v0.1)

Kernel subsystems: logical clock/scheduler, authoritative state store,
branch manager, RPM call stack, commitment controller, governed
write-back, typed halting. Protected authority rule: no subsystem
mutates authoritative state directly - typed intents only, one
transaction coordinator validates/applies/traces. Native trace per
tick (pre-state hash, enabled/scheduled components, inputs, biases,
branch and goal identity, proposed/authorized/rejected intents,
committed mutations, post-state hash, terminal status). Demos: one
CJT; three-stage cascade; cutoff/active/saturation/fault; identical
repeated trace; rejected unauthorized mutation. Domain flow P->C->E->O
with governed feedback. Exit gate: trace completeness 100%,
deterministic replay 100%, zero untraced mutations, zero unauthorized
writes accepted, zero state-hash divergence. Target: CAS-G2 / E4.

## Phase 2 - Precise thoughts (CAS-Sem v0.1)

Semantic types: Entity, Predicate, Relation, Event, Property,
Proposition, Rule, Variable, Binding, Assumption, Query,
Contradiction, ProofStep, EvidenceStatus, Provenance. Minimum
reasoning instruction set: RECALL, FORK, ASSOCIATE, DECOMPOSE,
INFER_MODUS_PONENS, INFER_TRANSITIVE, SUBSTITUTE,
DETECT_CONTRADICTION, COMPARE, COMMIT_BRANCH, HALT. Pipeline:
problem -> ^8 candidate generation -> parallel branches -> ^6
decomposition -> rule application -> ^9 candidate conclusion -> CDAB
comparison -> commit or continue. Demos: modus ponens, transitivity,
contradiction, missing information (NEEDS_INFORMATION, not a decorated
guess), multi-candidate (one contradicted, one dominated, one
admissible). Exit gate: no conclusion without a derivation path; every
proof step names premises and rule; a contradicted branch cannot
commit; a discarded branch cannot touch durable state; missing
evidence produces a typed unknown. Target: CAS-G4 / E4.

## Phase 3 - Memory, planning, verification (one wave)

3A Memory: five classes (working, episodic, semantic, procedural,
constitutional); each record carries content, type, provenance,
confidence, verification status, creation time, last use, revision
history, source links, decay/refresh policy; the machine distinguishes
never-learned / learned-but-forgotten / recalled-provisionally /
verified / contradicted / superseded. 3B RPM executive: goal -> desire
sufficient? -> wisdom sufficient? -> power sufficient? -> proceed or
create subgoal; frames carry goal_id, parent_goal_id,
blocked_prerequisite, local workspace and branches, return_address,
resume_stage, completion and failure conditions. 3C Trusted verifier,
independent of candidate generation: propositional logic, exact
integer/rational arithmetic, linear equations, proof-step validation,
schema validation, trace validation (later: symbolic algebra, code
execution, theorem proving, citation verification, tool-result
validation); verdicts VALID / INVALID / UNSUPPORTED / INCOMPLETE /
COUNTEREXAMPLE_FOUND; it may not grade its own generation under
altered rules. Exit gate: a prior verified memory changes a later
derivation with the trace naming which memory; an RPM child returns to
the correct parent stage; an invalid proof is rejected; missing
knowledge is distinguished from failed capability; nested RPM depth
bounded and cycle-checked. Target: CAS-G6 / E5.

## Phase 4 - Language cortex and chatbot

Open-weight model as a REPLACEABLE language cortex (see
HYBRID_MACHINE_DOCTRINE.md governance note 2: Route B requires owner
ratification against the standing no-foreign-models rule). The cortex
may parse, paraphrase, propose senses, generate candidate
interpretations, retrieve latent knowledge, render responses. It may
NOT commit conclusions, self-verify, write durable memory, alter the
constitution, authorize actions, or halt the kernel. Boards: CCB-L1
(English acquisition), CCB-D1 (dialogue control). The decisive
SEVER-THE-CORTEX test: English->CAS-Sem->CAS-RRK vs direct
CAS-Sem->CAS-RRK must yield structurally equivalent reasoning - if
removing the language model removes the reasoning, the language model
is still the real brain. Exit gate: round-trip preserves meaning;
ambiguity creates clarification subgoals; language output cannot
bypass commitment; direct semantic and English input converge; every
response links to a real trace; conversation memory carries
provenance. Target: CAS-G6 + CONV-4/5 / E4-E5.

## Phase 5 - Governed learning

Rings: R0 experience (automatic with provenance), R1 skill (held-out
testing required), R2 architecture (sandboxed descendant required),
R3 kernel/constitution (no autonomous promotion). Loop: attempt ->
observe -> compare prediction and outcome -> locate first failing
stage -> identify the missing knowledge or procedure -> create an RPM
learning goal -> study/practice/ask -> test on unseen examples ->
store only if improvement generalizes. Demos: English word teaching
with delayed cross-context tests; mathematics rule with counterexample
revision and held-out solve; dialogue pronoun correction persisting
across turns. Exit gate: immediate retention, delayed retention,
structural transfer, protected regression clean, provenance on every
durable update, rollback of incorrect learning. Target: CAS-G8 / E5.

## Phase 6 - Self-improvement without self-corruption (CAS-RLP)

Loop: run tasks -> inspect traces -> find the recurring first-failure
stage -> propose candidate repairs -> sandbox descendants -> compile
and validate -> public/protected/held-out suites -> compare with
parent -> promote/quarantine/reject -> preserve rollback and lineage.
Immutable evaluation boundary: the system proposing an improvement may
not alter the proof checker, protected benchmark, authority manifest,
transaction coordinator, trace verifier, promotion threshold, or
rollback mechanism. Demo: inject a repeatable fault; localize the
first bad stage; three candidate repairs; sandbox each; reject one
unauthorized; reject one that damages another skill; promote the one
that passes the protected suite; restore the parent and replay the
original failure; reapply and confirm. Exit gate: no live
self-editing, no evaluator contamination, parented promotions, sealed
evidence packets, TESTED rollback, unsafe mutations fail before
execution. Target: CAS-G9 / E5.

## Phase 7 - CAS Foundry (grows alongside the engine)

Foundry A circuit editor (after Phase 0): state editor, CJT builder,
component library, typed wires, CCDL import/export, DRC, five
reference-board templates (CSB, COB, CDAB, CMB, CPMB). Foundry B
simulation and trace (after Phase 1): run/pause/step/rewind, test
points, state timeline, operating-region animation, fault injection,
deterministic replay. Foundry C motherboard and Mind composer (after
Phase 3): board nesting, backplane, memory/goal/proof buses, P/C/E/O
layer view, Mind Passport, capability manifest. Foundry D chat with
this Mind (after Phase 4): conversation pane, live semantic parse,
branch tree, RPM stack, memory recall, commitment decision, trace
explanation. Foundry E learning and evolution lab (after Phases 5-6):
episodes, skill curves, candidate patches, descendant versions,
before/after comparison, promotion and rollback, lineage. Foundry F
qualification bench: CRQS assigns D0-D10, CAS-G0-G10, Capability
Vector, E0-E6, A0-A5, CONV level.

## Phase 8 - Scale toward historical capability bands

Milestone A (GPT-1 band): small cortex + CAS-Sem + CAS-G3/G4 + basic
CMB + logic/arithmetic verifier + simple dialogue. Milestone B (GPT-2
band): stronger cortex, broader retrieval, persistent episodic memory,
multi-turn dialogue, branching, correction retention, longer
generation. Milestone C (GPT-3-like practical usefulness): few-shot
induction, deep RPM recursion, procedural learning, tools, math and
code verifiers, long-horizon plans, broad retrieval. These are
benchmark targets, not promises of equivalence; the report stays
multidimensional (language band / CAS-G / CONV / memory /
verification / traceability) per crqs/rmb.py.

## The seven decisive experiments

    Language cortex knows      remove retrieval or weights ->
                               the expected knowledge loss appears
    Reasoning processor thinks direct CAS-Sem input solves without an
                               LLM producing the answer
    Memory remembers           one verified episode specifically
                               changes a later derivation
    RPM plans                  suspend parent, solve child, resume at
                               the exact return point
    Verifier checks            an attractive invalid proof is rejected
    Trace explains             full replay reproduces every committed
                               transition
    Evolution improves         a descendant wins held-out tests while
                               an unsafe or regressive one is rejected

The architecture is proven when removing one organ produces the
specific failure that organ was claimed to prevent.

## Where CAS-Ohm belongs

After deterministic runtime semantics. May investigate local response
profiles, calibrated intervention effects, operating regions, gain
composition, branch redundancy, instrumented drift. Must NOT decide
truth, proof validity, commitment, intelligence, or authorization.
Trajectory: deterministic design semantics -> software simulation ->
registered calibration profile -> instrumented experiment -> held-out
validation -> independent replication. The measure/diagnose/tune/
re-test loop applies, with tuning stopped once the stage is active,
aligned, within tolerance, and producing the intended effect.

## The complete v1 machine - the 20-step integrated episode

English question -> candidate semantic interpretations -> dialogue
context resolution -> active goal established -> CMB recall ->
candidate branches -> ^6 decomposition -> ^9 inference -> verifier
rejects one invalid branch -> RPM detects a missing prerequisite and
creates a child learning goal -> the child acquires it -> RPM resumes
the parent at the saved stage -> CDAB comparison under one shared bias
-> commitment -> English rendering -> sealed trace and evidence packet
-> the user corrects one detail -> stored with provenance -> a later
held-out task shows the correction was learned -> the evolution system
notices a repeated inefficiency, proposes a descendant, tests it, and
promotes or rolls back.

When one machine completes that episode without an external model
secretly supplying the reasoning, the seven systems are one Mind.

## Immediate work order

1. Master trajectory + authority manifest. 2. Freeze CAS-KIR,
MachineState, Intent, BranchFrame, RPMFrame, SemanticPacket,
TraceEvent schemas. 3. Read-only Codex audit of compiler/VM/testbench.
4. Deterministic Python CAS-RRK reference kernel. 5. Trace viewer +
Foundry canvas in parallel. 6. CAS-Sem + first formal reasoning
fixtures. 7. Memory + RPM + trusted verifier. 8. Hybrid language
cortex + dialogue board. 9. Governed learning. 10. Sandboxed evolution
only after every earlier gate passes. Codex receives one phase at a
time, with frozen schemas, explicit acceptance tests, and a
prohibition against inventing missing semantics.

---

# STATUS LEDGER (this lane, as of commit 0363b69a, 2026-08-28)

Recorded so no agent re-derives or re-runs closed work. Statuses use
the standing vocabulary; every claim has an artifact path.

- **Phase 0 - CLOSED.** AUTHORITY_MANIFEST.yaml, NON_GOALS.md,
  CONFORMANCE_PLAN, CAS_KERNEL_IR, COMPILER_RUNTIME_BOUNDARY, frozen
  golden fixtures: `CAS_RRK_v0.1/` (spec/, schemas/, golden/).
  Canonical core frozen: ^0-^9, P/C/E/O, F1-F7, T/A/f/E, A_root,
  CAS-Ohm excluded from runtime authority (`spec sheet.txt`).
- **Phase 1 - CLOSED.** CAS-RRK v0.1: typed intents, sole-writer
  transaction coordinator, state/decision commit split, branch
  isolation, RPM stack, sealed traces, deterministic replay; 34 tests
  incl. the 16-row conformance table (`CAS_RRK_v0.1/`). Exit-gate
  metrics in `CRQS_v0.1/fixtures/manifest_cncm.json` (trace
  completeness 1.0, replay 1.0, violations all 0).
- **Phase 2 - CLOSED.** CAS-Sem v0.1: 19 tests (`CAS_SEM_v0.1/`);
  kernel evidence statuses + modus ponens / transitive /
  contradiction / missing-information golden fixtures in the kernel;
  NEEDS_INFORMATION typed, never a decorated guess.
- **Phase 3 - SUBSTANTIALLY CLOSED.** Memory classes, provenance,
  lacunae (CAS-Sem + kernel CMB structures); RPM recursion with
  parent resumption (`rpm_recursion` fixture, D6 stable); exact
  arithmetic + proof checker as sole validity authority + bounded
  search + counterexamples (`CCB_M1_v0.1/`, 27 tests). OPEN within
  phase: the five-class memory taxonomy and decay/refresh policies
  are partial; linear-equation checker not built.
- **Phase 4 - PARTIALLY CLOSED.** CCB-L1 v0.1 (18 tests): strict
  encoder/decoder peripheral, typed located parse errors, word
  acquisition under the acceptance law, kernel grounding. The
  sever-the-cortex principle holds BY CONSTRUCTION today (all
  reasoning demos run on direct CAS-Sem input; no LLM anywhere in the
  loop). OPEN: CCB-D1 dialogue board; the neural cortex itself -
  BLOCKED on the Route B owner decision (HYBRID_MACHINE_DOCTRINE.md
  governance note 2).
- **Phase 5 - CLOSED at v0.1 scale.** CAS-G8 earned and independently
  re-audited NOT REFUTED: correction retention, cross-process delayed
  retention, structural transfer via the machine's own recall loop,
  protected regression, causal ablation (`CAS_RLP_v0.1/tests/
  test_g8_suite.py`, 9 tests). Recorded bounds on the spec sheet.
- **Phase 6 - CLOSED at v0.1 scale.** CAS-G9 earned: self-diagnosis
  from sealed evidence, sandboxed exploration, procedure SYNTHESIS
  from the machine's own evidence, six-check acceptance-law promotion,
  judge digest-checked untouched, EXACT parent replay after rollback,
  causal ablation, stable-D9 double run (`CAS_RLP_v0.1/rlp/
  self_improvement.py`, `tests/test_g9_suite.py`, 9 tests).
  Adversarial re-verification of this phase: OPEN (queued).
- **Phase 7 - PARTIAL.** Foundry-B/E-equivalent exists as the
  ten-pane glass-brain workbench (`CAS_WORKBENCH_v0.1/`, 13 tests,
  self-contained glass_brain.html). Foundry F exists as CRQS
  (`CRQS_v0.1/`, 33 tests). OPEN: circuit editor (A), motherboard
  composer (C), chat pane (D); workbench does not yet project CCB-T1,
  the OHM panel, or the G8/G9 evolution rounds.
- **Phase 8 - MACHINERY REAL, BENCHMARK NOT RUN.** Reference-band
  reporting implemented and audit-hardened (`CRQS_v0.1/crqs/rmb.py`);
  the CNCM's RMB honestly reads NOT RUN until a real head-to-head
  under the nine identical conditions exists.
- **Seven decisive experiments:** "reasoning thinks" (all demos are
  direct CAS-Sem, no LLM), "memory remembers" (memory-dependent D5),
  "RPM plans" (rpm_recursion D6), "verifier checks" (CCB-M1 mistake
  cycle; CCB-T1 CONTRA_TOOL_RESULT), "trace explains" (deterministic
  replay suites), "evolution improves" (G8/G9 ablations) - REAL at
  v0.1 scale. "Language cortex knows" - OPEN (no cortex yet).
- **Current qualification:** CAS-G9 / E5 / A0 - the design ceiling.
  CAS-G10 requires long_term_goals + self_model machinery (new
  boards), the multi-domain long-horizon suite, and E6 (independent
  replication) to lift the evidence ceiling.
