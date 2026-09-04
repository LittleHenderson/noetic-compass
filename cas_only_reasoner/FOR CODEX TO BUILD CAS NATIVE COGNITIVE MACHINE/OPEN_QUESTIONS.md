# CNCM-RRK v0.1 Open Questions

`OPEN-SEMANTICS` means an implementation must preserve the typed field or identifier but must not derive behavior from an invented meaning. A future decision becomes normative only through a versioned change to the authority manifest and affected contracts.

## Blocking ontology questions

### OS-001 — Seven TKS Foundation meanings

- Status: `OPEN-SEMANTICS`
- Scope: `TF1` through `TF7`
- Question: Which separately frozen ontology supplies their names, meanings, precedence, and goal-generation behavior?
- v0.1 rule: Identifiers may be carried as opaque goal references. They confer no truth, evidence, priority, or runtime authority.

### OS-002 — Twenty-eight TKS Sub-Foundation meanings

- Status: `OPEN-SEMANTICS`
- Scope: `TF1a` through `TF7d`
- Question: Which canonical definitions and World mappings are authoritative?
- v0.1 rule: The schema validates the identifier shape only. It does not assign consequences or weights.

### OS-003 — Foundation-to-Drive adapter

- Status: `OPEN-SEMANTICS`
- Question: How does a `TF*` goal request a mixture of CAS Drive rails `F1`-`F7`?
- v0.1 rule: Foundations and Drive rails remain separate namespaces. No default mapping exists.

### OS-004 — D/W/P sufficiency

- Status: `OPEN-SEMANTICS`
- Question: What makes Desire, Wisdom, or Power sufficient, who may assess it, and what evidence is required?
- v0.1 rule: No D/W/P field, assessment, calculation, or routing exists in the packet or runtime. RPM resolves caller-declared symbolic missing prerequisites only.

## Kernel semantic questions

### OS-005 — Remaining Noetic operations

- Status: `OPEN-SEMANTICS`
- Scope: `^0`-`^5` and `^7`
- v0.1 rule: They are valid canonical coordinates but are not executable operations.

### OS-006 — Register transfer behavior

- Status: `OPEN-SEMANTICS`
- Scope: registers `T`, `A`, `f`, and `E`
- v0.1 rule: The identifiers remain frozen in the authority manifest but have no packet, state, or executable IR field. No transfer, leakage, or persistence behavior is inferred.

### OS-007 — Domain stability criteria

- Status: `OPEN-SEMANTICS`
- Question: What substantive conditions establish `P_GOOD`, `C_GOOD`, and `E_GOOD`?
- v0.1 rule: Boot installs structural constants `P/C/E = GOOD` and `O = ENABLED`; no substantive domain test is implemented. These values are not moral, cognitive, or empirical certifications.

### OS-008 — Commitment hysteresis calibration

- Status: `OPEN-SEMANTICS`
- Question: Which non-arbitrary evidence quantity should drive `T_low` and `T_high`?
- v0.1 rule: Commitment is controlled by exact Boolean gates. A latch structure may be represented, but no activation-derived threshold may decide truth.

### OS-009 — Memory verification authority

- Status: `OPEN-SEMANTICS`
- Question: Which verifier may promote an episodic result to semantic or procedural authority?
- v0.1 rule: Episodic writes are allowed; online semantic and procedural promotion are prohibited.

### OS-010 — Full CCDL integration

- Status: `OPEN-SEMANTICS`
- Question: Which shared CAS Kernel IR and compiler version will later lower CCDL into this runtime?
- v0.1 rule: Only strict CAS-Sem problem packets and the admitted IR instruction set are in scope.

### OS-012 — Rule-source verification

- Status: `OPEN-ENGINEERING`
- Question: Which authenticated authority may admit a rule beyond structural validation and provenance strings?
- v0.1 rule: A structurally valid, provenance-bearing rule in the typed packet is executable. The runtime has no signer registry or separate verified-rule status.

### OS-013 — Self-contained warm replay

- Status: `OPEN-ENGINEERING`
- Question: How should a serialized receipt bind the exact initial episodic snapshot without duplicating or exposing an external store?
- v0.1 rule: In-memory `RunResult` retains that snapshot and replays from it; `RunResult.to_dict()` does not serialize it. `_from_trusted_snapshot` is a private same-process implementation boundary, not a security control or cryptographic proof that a snapshot belongs to a particular `RunResult`.

### OS-014 — Durable episodic import trust

- Status: `OPEN-ENGINEERING`
- Question: Which signature, trusted store, policy revision, and verifier authenticate an episode imported from persistence?
- v0.1 rule: Records created and recalled inside one persistent `CognitiveMachine` follow the kernel's write checks. Public nonempty memory injection is rejected. Private replay reinstalls the snapshot retained on the supplied `RunResult` as trusted host input; the underscore path does not authenticate an arbitrary caller-supplied record. `verified=True` is not a public import credential.

### OS-015 — Cognitive Board ontology and capability contract

- Status: `OPEN-SPECIFICATION`
- Scope: the CAS Foundry/Cognitive Board Studio/CADA proposal appended to `cas_reasoner.txt` at lines 8812-10029.
- Question: What are the canonical Board, node, edge, port, capability, execution, collaboration, registry, and publishing objects, and which operations may cross into the reasoning kernel?
- v0.1 rule: None of that web-workbench surface is implemented. Freeze a separate versioned Board Ontology and Capability Specification before code, and keep visual/editor state outside proof or mutation authority unless a later authority contract explicitly admits it.

### OS-016 — CAS Reasoning Qualification Standard

- Status: `OPEN-SPECIFICATION` / `PROPOSED-NOT-IMPLEMENTED`
- Scope: the CRQS v0.1 qualification-bench proposal appended to `cas_reasoner.txt` at lines 10031-11171, including Task Difficulty Grades `D0`-`D10`, native generations `CAS-G0`-`CAS-G10` and `CAS-GΩ`, Capability Vector (`CV`), evidence tiers `E0`-`E6`, deployment-authority levels `A0`-`A5`, Reference Model Benchmark (`RMB`), mandatory qualification gates, protected and held-out tests, causal ablations, failure localization, repair recommendations, and the qualification-bench workflow.
- Question: What versioned task/report schemas, operational metric definitions, calibration data, hard-floor precedence rules, cumulative-level rules, protected-suite controls, contamination checks, evaluator-independence guarantees, statistical acceptance criteria, and authority-policy bindings make each proposed result reproducible and auditable?
- Separation rule: capability describes demonstrated behavior; evidence maturity describes the support for that claim; deployment authority describes permitted action. None is evidence for or authority over another. A repair recommendation is advisory output, not permission to compile, patch, promote, or act.
- v0.1 rule: The runtime does not implement CRQS task manifests, scorers, graders, reports, benchmarks, repair semantics, or UI. The current schemas, fixtures, tests, traces, evidence packets, and goldens are engineering-conformance artifacts only. They are not a CRQS qualification suite, and this implementation has earned no `D`, `CAS-G`, `CV`, `E`, `A`, or `RMB` result.
- Required next contract: Freeze a separate **CAS Reasoning Qualification Standard v0.1 — Task Difficulty, Capability Generations, Evidence, and Repair Semantics** before implementing or claiming any grade. Its evaluator and protected fixtures must remain outside the mutation authority of any board being judged.

### OS-017 — CAS-Ohm native attention-plane integration

- Status: `ADOPTED-DESIGN-DIRECTION / OPEN-ENGINEERING / NOT-INTEGRATED`
- Scope: `spec/CAS_OHM_ATTENTION_INTEGRATION_PROTOCOL_v0.1.md` and `schemas/cas_ohm_stage_record.schema.json`.
- Question: Which exact quantity registry, native units, arithmetic validator, topology rules, fairness allocator, pre-schedule `AttentionAllocationPlan`, CJT/test-point identities, trace-sidecar hash verifier, and versioned KIR changes make native attention flow executable without creating truth, proof, meaning, validity, commitment, permission, memory-occurrence/write, state-mutation, halt, causal-identification, action, or self-modification authority?
- Current v0.1 rule: No CAS-Ohm quantity or stage record is present in authoritative state, intents, trace events, or evidence; the existing evidence flag only asserts `cas_ohm_runtime_authority = false`. The scheduler does not read CAS-Ohm. The contract-only stage record is a post-seal diagnostic observer, must emit no CNCM intent, and earns append-only status only after its payload/chain hashes and retention are independently verified. Removal or alteration of the observer must leave state, trace, proof, conclusion, commitment, RPM behavior, and episodic memory unchanged.
- Neural rule: A neural quantity requires a frozen profile, explicit `H_profile` bridge, uncertainty, controls, disjoint calibration/held-out splits, and retained negative outcomes. Same-sample resistance reconstruction is circular and prohibited.
- Admission rule: Native resource allocation may become normative only through a separate pre-schedule plan in a later authority/KIR version after deterministic budget conservation, fairness floors, ceilings, stable tie-breaking, starvation controls, neutral-profile equivalence, and hard-gate non-bypass tests pass. The post-seal stage record cannot be used as a scheduler command.

### OS-018 — CAS-GEM / CMB-R1 reconstructive memory

- Status: `ADOPTED-DESIGN-DIRECTION / OPEN-SPECIFICATION / NOT-IMPLEMENTED`
- Question: What exact `MemoryCapsule`, `CuePacket`, reconstruction-candidate, sentence-evidence, correction/reconsolidation, and `MemoryEvidencePacket` contracts support cue-based reconstruction while preserving exact anchors, unknown fields, provenance, and the rule that generated recollection never overwrites its source capsule?
- Current v0.1 rule: `EpisodicRecord` supports only same-process, exact semantic-key recall of a proof-bound committed conclusion. There is no similarity retrieval, embedding index, reconstructive generator, hot/warm/cold store, external authenticated import, or memory-candidate attention allocation.
- Compiler/SDG rule: The local compiler validates embedded CAS notation only. CAS-SDG may generate synthetic episodes, cues, candidates, perturbations, and ground truth, but generated records remain fixtures until independently compiler-checked and admitted by future capsule/evidence contracts.
- CAS-Ohm rule: A proposed retrieval current or candidate weight is a native work-allocation quantity, not probability that an event occurred. Anchor conflicts, policy blocks, evidence labels, and verifier results remain separate hard constraints.

## Non-blocking engineering freezes

The v0.1 documents freeze single-thread scheduling, logical ticks, atomic state commits, stable ordering, branch isolation, authoritative-support filtering, exact terminal reconstruction, and canonical trace hashing. Changes to those choices require a new contract version, not an implementation-local interpretation.
