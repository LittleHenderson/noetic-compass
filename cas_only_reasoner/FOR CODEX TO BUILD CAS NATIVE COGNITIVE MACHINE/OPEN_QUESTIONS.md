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

### OS-019 — Admissibility relations `D1` through `D9`

- Status: `OPEN-SEMANTICS`
- Scope: operators `^1` through `^9`
- Question: Which `(source, target)` pairs are valid for each operator? Correction 1 states the mechanism — each `CO-k` has an admissibility relation `Dk ⊆ I × I` — and freezes `D0 = {(I, I) : I ∈ I}`, the identity on the diagonal only. It states no pair for the other nine.
- v0.1 rule: `cncm/noetica.py` implements the guard and the registry, freezes `D0` (exactly 40 diagonal pairs over the 40 cognitive states), and marks the other nine `NOT_FROZEN` with an empty pair set. `is_admissible` **raises** `UnregisteredAdmissibility` for them rather than returning `False`, because an undecided relation is not an empty one and a guard that silently refuses everything is indistinguishable from one that works. `admissibility_status`, `frozen_operators` and `unresolved_operators` let a caller tell the two refusals apart deliberately. No pair is invented for any of the nine.

### OS-020 — Inversion axis thresholds, and stealth

- Status: `OPEN-SEMANTICS`
- Scope: axes `W`, `F`, `E`, `S`, and the state-vector reading of `N`; plus stealth
- Question: How much state-vector involution imbalance, domain-tier inversion, drive-pair divergence, entropy deficit, or cross-domain sub-drive variance constitutes an inversion? And what is "stealth", named in the NCCS weights as "7 axes + stealth + compound severity"?
- v0.1 rule: `cncm/inversions.py` measures every one of those quantities and supplies no limit for any of them. `frozen_limit` is `None` and `exceeds_frozen_limit` is `None` — not `False` — because "no limit exists" and "within the limit" are different answers. A caller applies its own threshold through `AxisMeasurement.exceeds(threshold)`. The compound axis is reachable only from a **frozen** limit, so no unfrozen reading can produce a compound finding. The module produces no NCCS component: the 15%-weighted inversion-resistance score would need thresholds that are not frozen, and `nccs_inversion_resistance` reads `NOT_PRODUCED`. Stealth is reported as `ABSENT_FROM_THE_INSTRUCTIONS`.
- Contrast: axis `N` on dials **is** judged, because the instructions freeze one limit there (an involution pair cannot diverge by more than 4 dial points), and axis `A` is judged at 0 because the chain `A0 → Dn → Wn → Pn` is frozen and one-directional.

### OS-021 — `P1` through `P7` name two different things

- Status: `OPEN-SEMANTICS`
- Scope: the 40-state listing and the 22-pathway listing
- Question: `P1`-`P7` each denote **both** a cognitive state (`P<noetic>`, from `P0-P9, C0-C9, E0-E9, O0-O9`) and a capability-pathway node (`P<purpose>`, from `A0 + D1-D7 + W1-W7 + P1-P7`). Which naming is authoritative in a context where both are in scope, and should one set be renamed or namespaced?
- v0.1 rule: The collision is real and is **not** resolved by inventing a rule. `cncm/noetica.py` names two label domains, `STATE_DOMAIN` and `PATHWAY_DOMAIN`, requires every function that takes a label to take its domain, and exposes `AMBIGUOUS_LABELS` (the seven) and `label_kinds(label)`. `realize` refuses a realization whose domain does not match, so a pathway realization can never be realized as a cognitive state just because the labels look alike.

### OS-022 — Is the `max_updates <= 176` ceiling an architectural constant?

- Status: `OPEN-ENGINEERING` / authority decision
- Scope: `cas_meta2/typed_teaching/learner.py`, `TYPED_LEARNER_LIMITS`
- Question: The registered learner contract admits `0 < max_updates <= 176`. Measured on the recorded run, the training objective had **not converged** when the run stopped at 160: the last update was the global minimum of the batch loss and the gradient norm was still climbing (ratio 1.378892, Spearman +0.317690, maximum at update 93 of 160). Is 176 a deliberate architectural constant, or a provisional bound that may be raised?
- **Why raising it is no longer the obvious first move.** The loss was still falling because the run was still fitting the **exposed** course: 39/564 = 6.9149% → 189/564 = 33.5106%, with `correspondence` going 0/88 → 82/88. Over the same 160 updates the **development** panel stayed at 0/59 and **retention fell** from 45/96 = 46.8750% to 34/96 = 35.4167%. On this evidence more updates on the same exposed course would plausibly widen the exposed-versus-transfer gap rather than close it, so the ceiling may be acting as a brake. One arm, one seed; offered as a reading, not a result. Evidence: `records/encoder_capacity_001/PANEL_MISREAD_CORRECTION.md`.
- v0.1 rule: Nothing raises it. It is treated as frozen, and no run that changes it may be launched without an owner-signed phase record.

### OS-025 — Two pre-teaching baselines for the same 59-question development panel

- Status: `OPEN-ENGINEERING` / measurement disagreement
- Question: The same 59-question development panel carries two different pre-teaching numbers in `typed_matched_001/receipt_20260919_m`: `summary.development_scores` at cursor 0 reads **0/59 = 0.0000%**, while the study's transfer baseline reads **21/177 "in each method before teaching"**, and 177 = 59 × 3, i.e. 7 per run. `development_boundary` names the same panel in both cases (`PUBLIC_DEVELOPMENT_TOPOLOGIES_NO_TRAINING_CORRECTIONS_NO_FINAL_PANEL`).
- Why it matters: the study's headline is that transfer degraded from 21/177 to 4/177 and 1/177. If the true pre-teaching development level is 0/59 rather than 7 per run, the headline's baseline is wrong and the degradation is measured from a different starting point.
- v0.1 rule: **Not reconciled.** Neither number is preferred and no third number is derived. Both are recorded and the disagreement is left open, because choosing the convenient one is how a disagreement becomes a false certainty.

### OS-023 — The loss is additive over fields while the score is conjunctive over the answer

- Status: `OPEN-SPECIFICATION` / measured defect
- Question: `_tensor_loss` averages a per-field loss over eleven fields; a scored question is correct only when the **whole** assembled answer matches the single admissible answer (`admissible_answer_count: 1`, rule `direct_contains_v1`). Measured consequence: over the 160 recorded updates, `correspondence` fell 79% and `reach` fell 52% in normalized terms while development accuracy moved from 0/59 to at most 1/59 and back to 0/59. Partial field improvement is structurally incapable of raising the score.
- Question, restated as a decision: should the objective be made conjunctive, should per-field progress be reported against the all-or-nothing metric, or is the current objective correct and the metric simply strict?
- v0.1 rule: Nothing changes. The mismatch is recorded as a measured defect with its evidence path and is not bundled into the analytic-initialisation proposal, which removes one cause of failure and not this one.

### OS-024 — Domain precedence semantics for inversion axis `W`

- Status: `OPEN-SEMANTICS`
- Question: The tier order `P ≻ C ≻ E ≻ O` is frozen. Does it mean that a state vector's mass must **decrease** from `P` toward `O`, and if so by how much before it is an inversion? `cncm/inversions.py` counts adjacent tier pairs where the lower tier carries strictly more mass than the tier above it, which makes equal tiers not an inversion, and reports the count with no threshold. Whether a count of 1 is a violation is undecided.

### OS-026 — Is deriving the readings of a bound entity the task, or the removal of the task?

- Status: `OPEN-SEMANTICS` / boundary decision
- Scope: the five kinds whose answer is one determined fact about one entity — `edge_account` (16 slots), `role_set` (6), `parts` (4), `context` (5), `definition` (3). 299 of 564 questions.
- Question: For four of those five kinds the query states `focus_world_id` directly and the world's declarations are in the packet. The machine is therefore being asked to **reproduce, by 64-way classification, an identifier the question supplies and the document declares.** Is that the intended task?
- Measured evidence: `records/encoder_capacity_001/DECISION_STRUCTURE_RESULT.md`. `admissible_answer_count` is **1** for every question of those kinds, in both arms at both cursors — they are one fact to be got right in N places, not N questions. The recorded score decomposes exactly by decision shape: **265 one-decision questions score 174/265 = 65.66%** after teaching, and **299 many-decision questions score 15/299 = 5.02%**. The machine is better where the answer is one choice among several admissible answers than where the answer is uniquely determined.
- The distinction that decides it (round 7 precedent): **task deletion** gives the machine the answer in its input and removes the task — pre-selecting the focus world's row into the encoding was withdrawn for exactly that. **A composition layer** leaves the machine to resolve *which* entity the question is about and only requires that the readings of that entity be derived and consistent.
- v0.1 rule: `cncm/composition.py` is implemented as a component with its own 26 tests, is **not licensed to run**, is **not wired into any run**, and changes no registered contract. Deriving all 34 slots would make 299 of 564 questions a lookup of material the question already points at. Whether that is the intended task, an unintended consequence of the course contract's slot plan, or something the frozen contract already settles, is an **owner decision**, and neither the component nor its record pre-empts it.

## Non-blocking engineering freezes

The v0.1 documents freeze single-thread scheduling, logical ticks, atomic state commits, stable ordering, branch isolation, authoritative-support filtering, exact terminal reconstruction, and canonical trace hashing. Changes to those choices require a new contract version, not an implementation-local interpretation.
