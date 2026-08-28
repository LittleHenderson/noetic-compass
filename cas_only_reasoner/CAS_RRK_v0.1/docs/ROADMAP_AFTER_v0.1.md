# Roadmap After v0.1

Per the capability charter (cas_reasoner.txt) and the staged plan.

## Stage 2: shared CAS Kernel IR
Emit CAS-KIR from the Rust compiler pipeline; parse it in the kernel.

## Stage 3: differential execution
Python reference vs Rust implementation: identical authorized intents,
rejected intents, branch states, RPM transitions, terminal status,
final state hash, and trace digest.

## Stage 4 and later (in order)

1. CAS-RLP: DONE v0.1 (cas_only_reasoner/CAS_RLP_v0.1, 13 tests):
   fault diagnosis from sealed traces, candidate mutation, sandbox
   evaluation, promotion, rollback. Four rings gated: R0 automatic
   with provenance, R1 held-out promotion, R2 sandbox + regression,
   R3 refused; evaluator tampering rejected.
2. CCB-M1: DONE v0.1 (cas_only_reasoner/CCB_M1_v0.1, 27 tests):
   exact rational arithmetic (never floats), expression IR with exact
   canonical expansion, the trusted proof checker as sole validity
   authority (continuity, structural rules, sample validation of
   learned procedures, first-invalid-step walk-down), bounded proof
   search, counterexample generator, mistake recovery promoted under
   the acceptance law, versioned axioms, curriculum DAG.
3. Procedural learning: strategies and proof patterns behind the
   Gate-5 controls (RLP ring R1 extended to proof strategies).
4. CAS-Sem expansion: entities, relations, reference, time, truth,
   provenance - beyond propositions and rules.
5. CCB-L1: the English acquisition board (lexicon, grammar, grounding,
   dialogue, decoding) - strictly outside the reasoning loop.
   NEXT organ to build.
6. Encoders/decoders as peripherals; neural instrumentation and
   CAS-Ohm experiments last, under the paper's own restrictions.

## Standing rules from the charter

- Math first as the rigorous learning domain: "Math can show that it
  actually learned to reason."
- The machine may become more capable; it may not redefine "better" so
  that every new version passes.
- A machine-generated proof is not valid until the trusted checker
  accepts it.
