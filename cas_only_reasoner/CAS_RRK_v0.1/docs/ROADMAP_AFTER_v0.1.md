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
3. CCB-L1: DONE v0.1 (cas_only_reasoner/CCB_L1_v0.1, 18 tests):
   strict encoder/decoder peripheral - English in at the edges, the
   unchanged kernel reasons, English out. Round-trip meaning,
   paraphrase convergence, pronoun reference, located typed parse
   errors ("I did not understand 'flurpy' at word 4"), word
   acquisition under the acceptance law (candidate senses, contrast
   against grounding facts, promotion, versioned corrections), novel
   composition, ablation, kernel grounding with verdict decoding
   (CONCLUDED -> "yes, the cat is gray.", NEEDS_INFORMATION ->
   "i do not know..."). No LLM anywhere.
4. CAS-Sem: DONE v0.1 (cas_only_reasoner/CAS_SEM_v0.1, 19 tests):
   the semantic content and binding layer - typed entities, role
   schemas, references with binding, transitive time consistency,
   nine truth statuses with discipline, provenance completeness, and
   the six coherence laws, with DERIVED claims re-proven through the
   unchanged proof kernel; Semantic CMB queries and typed lacunae.
5. Procedural learning: DONE (cas_only_reasoner/CAS_RLP_v0.1,
   rlp/procedural.py + rlp/strategies.py, 10 new tests): repair
   strategies promoted under the acceptance law - s_gt_first repairs
   the training fault AND a held-out fault case of the same class in
   ONE sandbox evaluation each (PROMOTED, versioned, provenance
   prior_proof); s_lt_first exhausts the budget (REJECTED);
   unbudgeted default behavior intact; rollback preserved.
6. Encoders/decoders as peripherals; neural instrumentation and
   CAS-Ohm experiments last, under the paper's own restrictions.
7. The cognitive workbench interface (charter section 3): goal map,
   live board, branch tree, RPM stack, trace timeline - the glass
   brain over the now-complete organ stack. NEXT artifact.

## Standing rules from the charter

- Math first as the rigorous learning domain: "Math can show that it
  actually learned to reason."
- The machine may become more capable; it may not redefine "better" so
  that every new version passes.
- A machine-generated proof is not valid until the trusted checker
  accepts it.
