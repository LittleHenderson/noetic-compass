# CCB-R1 — Cognitive Reasoning Processing Board

## The CAS Reasoning Processing Unit (CAS-RPU) — Board Specification

**Status:** Architectural specification. The runtime half of this board
exists and passes its conformance suite (CAS-RR v0.1, see
CAS_RR_V0_1_SPEC.md); the board below is the schematic architecture that
integrates the five reference CCBs into one reasoning processor.
**Date:** 2026-08-28.
**Grounding:** SOURCE_GROUNDING_NOTES.md.

**One-sentence purpose.** CCB-R1 is the motherboard that makes the CAS
organs reason together: the CMB remembers, the CDAB compares, the COB
clocks, the CPMB supplies Drive in order, the CSB governs — and CCB-R1
executes the loop that turns those organs into a reasoner.

---

## 1. The Board / Runtime Distinction

The missing hinge in the prior CAS artifacts was not another component.
It was the separation of two questions:

    The board specifies WHAT IS CONNECTED.
    The runtime specifies WHAT FIRES NEXT.

CAS PCBA Engineer already supplies the component library and the board
discipline; Appendix C states plainly that CCDL is a declarative netlist
language with "no execution model, no clock, and no state-transition
semantics" (11 of 39 leaders have full semantics, 11 partial, 17 none —
almost exactly the stateful/temporal family plus the verification
sub-language). CCB-R1 is therefore delivered as TWO artifacts:

1. This board spec — the topology.
2. CAS-RR v0.1 (cas-rr/) — the operational semantics that give the
   topology a pulse. Every module below maps to an executable class.

---

## 2. The Complete Board

                          A_root / Prime Desire
                                    |
                      7 FOUNDATION GOAL ENGINES
                                    |
                     28 SUB-FOUNDATION CHANNELS
                                    |
                       FOUNDATION-DRIVE ADAPTER
                                    |
    Problem -> Encoder -> Filters -> ^8 Hypothesis CJT Bank
                                    |
                            CMB memory recall
                                    |
                           ^6 Decomposition Bank
                                    |
                            ^9 Inference Bank
                                    |
                       CDAB Candidate Comparators
                                    |
                        28-Lane Goal Evaluation
                                    |
                         RPM D -> W -> P Scan
                           |                |
                      sufficient       first block
                           |                |
                           |          recursive subgoal
                           |                |
                           +------ re-measure -----+
                                    |
                         Principle and Logic Gates
                                    |
                           Schmitt Commit Stage
                                    |
                                Output MUX
                                    |
                       P -> C -> E -> O Sequencer
                                    |
                           Decision / Action / Reply
                                    |
                    CMB write + filtered O -> P feedback
                                    |
                                next cycle

Two half-diagrams from the sources become one spine here:

    CJT cascade  = thinking forward (Quantification Guide p. 13)
    RPM recursion = repairing what prevents forward movement (p. 15)

---

## 3. Board Modules

| Module | CAS components | Processing job | Executable (CAS-RR v0.1) |
| --- | --- | --- | --- |
| Foundation Engine Bank | 7 target controllers, 28 world-channel biases | decides what matters and in which context | foundations.FoundationEngineBank |
| Foundation-to-Drive Adapter | transformers, MUX, resistive dividers | converts goals into local Drive requirements | ontology.DRIVE_ADAPTER |
| Input Front End | transducer, ADC, filters | converts input into typed CAS states | runtime.Problem (encoder boundary) |
| Hypothesis Generator | parallel ^8 CJTs, DEMUX | surfaces interpretations and plans | candidates.CandidateGenerator |
| Reasoning ALU | ^6 and ^9 CJT cascades | decomposes premises, lands conclusions | reasoning.ReasoningStage |
| Candidate Comparator | CDAB, matched CJTs | extracts meaningful differences under shared bias | compare.CDAB / Tournament |
| RPM Planner | D/W/P gates, recursive goal stack | finds missing Desire, Wisdom, or Power | rpm.RPMController |
| Memory System | CMB capacitors, refresh, lacuna flags | holds facts, episodes, principles | memory.CMB |
| Commit Controller | comparator, Schmitt trigger, MUX | stable decisions without flip-flopping | commit.CommitmentController |
| Action Governor | diodes, sequencer, CSB, DAC | no action before P, C, E stabilize | domains.DomainDescent |
| Learning Controller | RC low-pass feedback, CMB write | weak, filtered outcome feedback | learning.LearningController |
| Power and Health | CPMB, seven Drive rails, budgets | keeps reasoning supplied and inside limits | runtime.Constitution + budgets |

The five reference boards keep their roles: CMB (memory), CDAB
(comparison), COB (clock and rhythm — the tick), CPMB (Drive regulation
and sequencing — the boot order), CSB (governing boundaries — the
principled constraints gate). CCB-R1 is their executive integration
layer.

---

## 4. Illustrative Netlist (CCDL-flavored; not yet a compiler artifact)

    board cognitive_reasoning_processor_v0 {
        input:  cas_problem;
        output: cas_decision;

        use cognitive_memory_board;
        use cognitive_differential_amplifier;
        use cognitive_power_management_board;
        use cognitive_safety_board;

        // Bias and memory substrate (Law 1: typed, explicit, probeable)
        node memory_bias:  ^5^C_{F2}|A;
        node charter_bias: ^5^P_{F7}|T;
        node goal_bias:    ^5^E_{F5}|A;

        // Reasoning spine
        node interpretation: ^8^C_{F2}|A;
        node decomposition:  ^6^E_{F6}|A;
        node conclusion:     ^9^C_{F2}|A;
        node action:         ^9^O_{F5}|E;

        cjt intake:
            CJT< cas_problem | memory_bias => interpretation >
            [beta=1.5, cutoff=0.2, sat=0.95, region=active];

        // Honest evaluation: unity gain is the truth firewall (Law 2)
        cjt analyze:
            CJT< interpretation | charter_bias => decomposition >
            [beta=1.0, region=active];

        cjt infer:
            CJT< decomposition | goal_bias => conclusion >
            [beta=1.0, region=active];

        // Diodes make the direction structural (Law 4)
        diode d_pc: Diode< ^P -> ^C >;
        diode d_ce: Diode< ^C -> ^E >;
        diode d_eo: Diode< ^E -> ^O >;

        // Slow, filtered learning - never instant self-rewriting
        feedback learn:
            action -> memory_bias
            [beta=0.05, tau=5];

        // Every silent failure gets a test point (Law 5)
        probe tp_interpretation: interpretation;
        probe tp_decomposition:  decomposition;
        probe tp_conclusion:     conclusion;
        probe tp_action:         action;
    }

The Foundation and RPM declarations require the CCDL extensions noted in
the runtime spec (Ch. 4-5): a foundation_ref production and explicit
semantics for clock, mutation, recursion, and halting. The netlist above
is illustrative; the executable semantics live in cas-rr/.

---

## 5. Drive Rails and Power (CPMB)

Seven Drive rails (F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5
Agency, F6 Structure, F7 Purpose) supply the local stages. The power
sequencer enforces P -> C -> E -> O and holds O low until P, C, and E
report power-good — "no action without principle," the board's core
safety property (book Ch. 14, Ch. 22).

Attention is the Ohm-shaped consistency check, and nothing more
(runtime spec Ch. 14):

    I_pred = V_drive / R_total,
    R_total = R_capability + R_policy + R_context + R_resource

Design quantities, not literal electricity, and never a truth source.

---

## 6. The Reasoning Integrity Spine

The board's most important property:

    Ambition may choose the question. It must not choose the answer.

The Foundation engines may select problems, query memories, request
candidate plans, set budgets, and decide which outcomes matter. They may
NOT inflate evidence so the machine proves what it already wants.

| Stage | Gain | Why |
| --- | --- | --- |
| ^8 candidate generation | 1.5 moderate | too little is tunnel vision, too much is a fireworks factory |
| ^6 decomposition | 1.0 unity | the truth firewall: "Unity is honesty" (book Ch. 11) |
| ^9 inference | 1.0 unity | the truth firewall |
| commitment | 2.0 bounded | commit without reopening settled conclusions |
| learning | 0.05 slow | one outcome cannot rewrite the machine |

The five load-bearing laws, all executable in CAS-RR v0.1:

1. **There is no bias-free CJT.** Bias is mandatory, typed, versioned,
   probeable, and shared where comparisons require fairness.
2. **Association is not deduction.** ^8 generates or surfaces; ^6 + ^9
   reasons and concludes.
3. **Gain is not truth.** Evaluation runs at unity gain; a constitution
   that says otherwise is rejected at boot.
4. **Action cannot authorize its own principle.** O -> P direct edges
   are blocked by diodes; only the low-gain learning channel passes.
5. **Parent totals never replace child probes.** Every candidate's
   probes are retained in the provenance packet (Guide p. 14).

---

## 7. Halting

The reasoning oscillator cannot become rumination. Every episode
terminates in exactly one typed state:

    CONCLUDED | NEEDS_INFORMATION | NEEDS_CAPABILITY |
    CONFLICT_UNRESOLVED | INADMISSIBLE | RESOURCE_EXHAUSTED |
    LOOP_LIMIT_REACHED

NEEDS_INFORMATION is a successful result: the machine correctly
discovered that the available state does not justify a conclusion.

---

## 8. Test Points and Evidence

Every module exposes test points; every CJT carries a probe (cause,
bias, beta, output, region, tick). At halt the machine emits a Reasoning
Provenance Packet: problem, goal, memories with sources and lacunae,
candidates, decompositions, inferences with proof paths, comparisons,
RPM stack history, commitment gates, domain power state, learning
disposition, output. "Show your work, or don't ship it" (book Ch. 25).

---

## 9. Development Status

| Gate | Deliverable | Status |
| --- | --- | --- |
| 0 | Ontology freeze (A_root, TF/DF split, 28 channels, adapter) | DONE (ontology.py) |
| 1 | CCDL extension + full runtime semantics | SPECIFIED (runtime spec Ch. 4-5); grammar untouched |
| 2 | Deterministic CAS simulator | DONE (cas-rr/, 25 tests green) |
| 3 | CCB-R1 integration + halt gates | DELIVERED IN SOFTWARE FORM (this spec + runtime) |
| 4 | Ablation and fault tests | PARTIAL (fault tasks, budget tests; full ablation suite open) |
| 5 | Encoders / external environment | OPEN |
| 6 | Neural instrumentation (CAS-Ohm) | OPEN — see paper restrictions, runtime spec Ch. 14 |

The board and the runtime together answer the founding question the way
the sources demand: CAS is no longer governing an intelligence. In
CAS-RR v0.1, CAS is where the reasoning happens — CJT by CJT, with every
conclusion carrying its cause, its bias, and its proof.
