# Roadmap After v0.1

Per the capability charter (cas_reasoner.txt) and the staged plan.

## Stage 2: shared CAS Kernel IR
Emit CAS-KIR from the Rust compiler pipeline; parse it in the kernel.

## Stage 3: differential execution
Python reference vs Rust implementation: identical authorized intents,
rejected intents, branch states, RPM transitions, terminal status,
final state hash, and trace digest.

## Stage 4 and later (in order)

1. CAS-RLP: recursive learning protocol - fault diagnosis, candidate
   mutation, sandbox evaluation, promotion, rollback. Four rings:
   R0 experience (auto), R1 skill (test+promote), R2 architecture
   (sandbox descendants), R3 kernel/constitution (no autonomous
   promotion).
2. Procedural learning: strategies and proof patterns behind the
   Gate-5 controls.
3. CAS-Sem expansion: entities, relations, reference, time, truth,
   provenance - beyond propositions and rules.
4. CCB-L1: the English acquisition board (lexicon, grammar, grounding,
   dialogue, decoding) - strictly outside the reasoning loop.
5. CCB-M1: the mathematical learning and proof board - trusted
   arithmetic and proof checker, counterexample generator, curriculum.
6. Encoders/decoders as peripherals; neural instrumentation and
   CAS-Ohm experiments last, under the paper's own restrictions.

## Standing rules from the charter

- Math first as the rigorous learning domain: "Math can show that it
  actually learned to reason."
- The machine may become more capable; it may not redefine "better" so
  that every new version passes.
- A machine-generated proof is not valid until the trusted checker
  accepts it.
