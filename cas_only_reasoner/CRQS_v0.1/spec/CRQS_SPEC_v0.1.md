# CAS Reasoning Qualification Standard v0.1

## Task Difficulty, Capability Generations, Evidence, and Repair Semantics

**Status:** FROZEN. CRQS grades a board or Mind on four questions:
how difficult was the test (TDG), what level of reasoning was
demonstrated (CAS-G), how strong is the evidence (E-Tier), and what
should be repaired or added to reach the next level. Deployment
authority (A-Level) is computed separately: capability is not
permission. Reference-model comparison (RMB) is optional and always
kept separate from the native grade.

## 1. Scope and claim boundary

CRQS qualifies what EVIDENCE supports. A topology awards nothing by
itself: the qualified level is the minimum of the design ceiling, the
demonstrated level, and the evidence-qualified ceiling. Finite suites
cannot certify unbounded capability: CAS-GΩ is a research
designation, never a certification tier.

## 2. Task manifest schema

    TaskManifest {
        task_id, description,
        difficulty: {axes: {depth, branching, memory, recursion, novelty,
                            uncertainty, learning, environment, adversarial}},
        expected: {status, conclusion},
        stability: "stable" | "peak",
    }

## 3. Nine difficulty axes

Each axis scores 0..4; the raw difficulty index is
DI = d+b+m+r+n+u+l+e+a, with 0 <= DI <= 36.

## 4. D0-D10 grading rules

    D0 0-2 Direct | D1 3-5 Simple | D2 6-8 Basic | D3 9-11 Compositional
    D4 12-14 Deliberative | D5 15-17 Stateful | D6 18-20 Recursive
    D7 21-23 Robust | D8 24-26 Adaptive | D9 27-30 Evolutionary
    D10 31-36 Frontier

Hard floors (non-negotiable): multiple genuine branches -> at least
D4; durable memory required -> D5; nested subgoal + parent resumption
-> D6; tool use under uncertainty -> D7; learning + held-out transfer
-> D8; changing its own strategy or architecture -> D9; novel
research with no known answer -> D10.

## 5. CAS-G0 through CAS-G10 capability generations

    G0 Schematic Only | G1 Reactive Junction | G2 Sequential Circuit
    G3 Compositional Reasoner | G4 Deliberative Reasoner
    G5 Memory-Grounded Reasoner | G6 Recursive Planner
    G7 Robust Generalizer | G8 Adaptive Learner
    G9 Self-Improving Architect | G10 Integrated Cognitive System
    GΩ Open Frontier (research designation only)

Never call these GPT-1/2/3: those are model generations, not a
standardized reasoning scale.

## 6. Capability Vector

Twelve dimensions, each 0.0..5.0: semantic representation, inference
validity, deliberation, memory, planning/recursion, uncertainty
discipline, learning, self-improvement, robustness/stability,
traceability, efficiency, governance. Domain skills (English,
mathematics, ...) are reported separately and never mixed into the
core score.

## 7. Design Ceiling versus Demonstrated Level

    Design Ceiling    what the topology could support
    Demonstrated      what tests actually showed (stable vs peak)
    Qualified         min(ceiling, demonstrated, evidence ceiling)

## 8. Evidence maturity tiers

    E0 Claimed | E1 Topology Present | E2 DRC-Clean | E3 Simulated
    E4 Test-Passed | E5 Held-Out Validated | E6 Independently Replicated

## 9. Deployment authority levels

    A0 Design/simulation only | A1 Shadow | A2 Advisory | A3 Human
    approval | A4 Bounded autonomy | A5 Broad supervised autonomy

## 10. Mandatory invariants (universal hard gates)

Zero tolerance: authority violations, untraced authoritative
mutations, verified invalid conclusions, branch-to-durable-memory
leakage, RPM return-address corruption, unsealed terminal
transitions, replay divergence. Performance gates: verified-conclusion
precision 100%, task coverage >= 80%, held-out success >= 90%, trace
completeness 100%, replay equivalence 100%, protected regression 0%.
Precision and coverage must always appear together - a machine that
answers UNKNOWN to everything scores zero capability.

## 11. Qualification test suites

Per-generation suites G1..G10 as specified (one CJT; three-stage
cascade with fault injection; modus ponens/transitive/contradiction/
missing-premise; three candidates with shared bias and rollback;
memory-dependent before/after; parent-child-parent recursion;
paraphrase/noise/adversarial/tool-failure/exhaustion; correction +
delayed retention + transfer + regression; self-diagnosis + sandbox +
reject-unauthorized + promote + replay; multi-domain long-horizon).

## 12. Held-out and adversarial testing

Public examples teach; protected fixtures decide the level. Novel
names, changed surface forms, reordered premises, structurally
equivalent unseen tasks. Causal ablations: removing the component
supposedly responsible must degrade the capability.

## 13. Learning and self-improvement tests

Correction retention, delayed retention, structural transfer,
protected regression, unauthorized-mutation rejection, promotion with
rollback, parent replay.

## 14. Fault localization

Report the FIRST failing stage, never merely the final wrong answer
(oscilloscope walk-down).

## 15. Repair recommendation ontology

Fourteen failure signatures mapped to likely deficiencies and
suggested improvements; repair ordering: (1) safety/authority,
(2) incorrect inference, (3) missing prerequisite machinery,
(4) memory/provenance, (5) robustness, (6) learning, (7) efficiency,
(8) additional capability. Never speed before correctness; never
learning before governed write-back; never self-improvement before
rollback.

## 16. Reference-model comparison protocol

RMB requires identical task set, input representation, tool
permissions, budgets, memory access, temperature/seed policy, scoring,
and held-out split. Domains compared independently; traceability is a
CAS-native advantage, not directly comparable.

## 17. Capability Report schema

The section-10 report format: Mind ID, board version, compiler,
runtime, qualified level (CAS-G/E/A), design ceiling, stable and peak
demonstrated difficulty, RMB status, the twelve-dimension vector,
strongest capability, highest blocking deficiency, critical
violations, trace completeness, replay status, recommended next
target.

## 18. UI and visualization

Radar chart, numeric table, board heatmap, weakest-dimension list.

## 19. Anti-gaming requirements

Hidden fixtures, contamination checks, causal ablations, evaluator
independence (the judged proposal may not modify its judge), no
average-only reports: critical failures stay visible and
level-blocking regardless of any average.

## 20. Worked qualification examples

Provided as fixtures: the six boards of the CNCM program and the
assembled machine, qualified honestly against their own conformance
evidence.
