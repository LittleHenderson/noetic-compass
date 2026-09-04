# CCB-T1 Cognitive Apprenticeship and Teaching Board v0.1

Status: `EXPERIMENTAL / NOT KERNEL INTEGRATED`

CCB-T1 is a contract-first design for domain-neutral teaching episodes. It lets external teachers propose knowledge, procedures, strategies, curricula, critiques, and candidate repairs while independently custodied examinations determine what evidence supports the proposal.

The controlling law is:

> The teacher may propose knowledge and skill. The CNCM decides what may become part of itself.

In CNCM-RRK `0.1.0`, no CCB-T1 board, teacher adapter, procedural-promotion path, semantic-promotion path, constitutional-promotion path, tool-learning executor, neural-distillation installer, or durable apprenticeship store is kernel integrated. The isolated `cncm/cognitive_apprenticeship.py` laboratory exercises a bounded subset of these contracts without entering `MachineState`. CAS-RRK does not currently promote these lessons, and current episodic-write authority must not be repurposed for them. Every lifecycle value in this package describes an experimental artifact or recommendation only.

## 1. Purpose

CCB-T1 defines a common teaching envelope for:

- language and dialogue;
- source-grounded world knowledge;
- reasoning strategies;
- mathematics and proof methods;
- software engineering and debugging;
- tool-use procedures;
- research methods;
- memory organization and retrieval methods;
- metacognition and epistemic discipline;
- social and conversational procedures;
- creativity and explicitly labeled imagination;
- board-design proposals;
- self-diagnosis and repair proposals;
- multimodal perception and grounding curricula.

The package separates a lesson proposal from its examinations, qualification evidence, metrics, lineage, and any future promotion authority. A teacher is a faculty member, not an oracle or state writer.

## 2. Non-authority boundary

CCB-T1 artifacts are data. They do not:

- assert empirical truth or proof validity;
- select a reasoning winner or committed result;
- authorize a tool, network call, subprocess, file operation, message, device, payment, or deployment;
- write semantic, procedural, episodic, neural, constitutional, or runtime state;
- issue a CNCM intent, capability, permission, or halt;
- modify source, schemas, protected fixtures, verifiers, rollback machinery, or the authority manifest;
- convert a teacher's confidence or consistency into acceptance evidence;
- identify a CAS-Ohm observation as the cause of success or failure.

All teacher outputs are proposal-only. A current host may store artifacts as ordinary files only when explicitly invoked by the user; that host I/O is not cognitive authority or kernel integration.

Any live promotion mechanism requires a new versioned authority contract, manifest, issuer/capability mapping, intent schema, coordinator validation, negative tests, replay tests, migration rule, rollback rule, and independently demonstrated qualification.

## 3. Normative artifacts

This experimental package adds four closed JSON contracts:

- `schemas/teaching_episode.schema.json` — one domain-neutral lesson proposal and evidence plan;
- `schemas/teacher_role_assignment.schema.json` — one proposal-only faculty assignment with protected-exam exclusions;
- `schemas/apprenticeship_qualification_receipt.schema.json` — one provisional or durable qualification recommendation;
- `schemas/apprenticeship_lineage.schema.json` — append-only episode versions, recommendations, rollback ancestry, and exact apprenticeship metrics.

Language lessons may specialize a teaching episode by referencing:

- `https://cas.local/schemas/language_lesson_packet.schema.json`;
- `https://cas.local/schemas/grammar_construction.schema.json`;
- `https://cas.local/schemas/semantic_frame.schema.json`;
- `https://cas.local/schemas/language_qualification_receipt.schema.json`.

CCB-T1 does not duplicate or weaken those CCB-L1 requirements. When a specialized contract is named, both the CCB-T1 envelope and the specialized artifact must validate.

All CCB-T1 objects use closed property sets, lowercase SHA-256 digests, namespaced enums, and IDs matching `^[A-Za-z_][A-Za-z0-9_.:-]*$`. Floating-point values are not admitted. Ratios use an integer numerator, positive integer denominator, and integer basis points from `0` through `10000`. CAS-Ohm-derived quantities use exact decimal strings and explicit units.

Every artifact fixes:

```text
package_maturity = EXPERIMENTAL
kernel_integration_status = NOT_KERNEL_INTEGRATED
runtime_effect = NONE
```

## 4. Domain typing

Each `TeachingEpisode` declares exactly one primary domain:

| Domain value | Typical content | Minimum verifier class |
|---|---|---|
| `CCB_T1_DOMAIN_LANGUAGE` | lexicon, grammar, reference, realization | semantic-frame and contrast verifier |
| `CCB_T1_DOMAIN_WORLD_KNOWLEDGE` | stable or current source-grounded claims | source corroboration with validity window |
| `CCB_T1_DOMAIN_REASONING_STRATEGY` | decomposition, search, counterexample, backtracking | held-out task and trace comparer |
| `CCB_T1_DOMAIN_MATHEMATICS` | exact operations, proof methods, theorem use | exact checker or proof verifier |
| `CCB_T1_DOMAIN_SOFTWARE_ENGINEERING` | code, algorithms, tests, debugging | isolated executable/property-test harness |
| `CCB_T1_DOMAIN_TOOL_USE` | recognition, typed intent proposal, result checks | permission simulator and output-schema verifier |
| `CCB_T1_DOMAIN_RESEARCH_METHOD` | hypotheses, controls, measurement, replication | registered-design and independent evidence review |
| `CCB_T1_DOMAIN_MEMORY_ORGANIZATION` | encoding, cues, consolidation, reconstruction labels | retrieval/retention verifier with provenance checks |
| `CCB_T1_DOMAIN_METACOGNITION` | uncertainty, assumptions, clarification, abstention | calibration and error-detection fixtures |
| `CCB_T1_DOMAIN_SOCIAL_CONVERSATION` | tone, repair, audience adaptation | anchored dialogue fixtures and required constraints |
| `CCB_T1_DOMAIN_CREATIVITY` | analogy, counterfactuals, recombination | novelty-independent constraint and labeling checks |
| `CCB_T1_DOMAIN_BOARD_DESIGN` | board/component/topology proposals | compiler, DRC, simulator, fault, authority-invariant suite |
| `CCB_T1_DOMAIN_SELF_DIAGNOSIS` | trace inspection and repair hypotheses | protected descendants and first-fault verification |
| `CCB_T1_DOMAIN_MULTIMODAL_PERCEPTION` | visual, audio, spatial, and sensory grounding | held-out grounded samples from the declared modality |

A verifier class constrains the evidence method; it does not itself confer proof or truth authority. High-stakes or temporally changing world knowledge requires current source-linked retrieval and an explicit validity window. Teacher-memory-only facts cannot qualify as verified current facts.

## 5. Transfer channels and destinations

Every episode declares one transfer channel and one destination. The schema enforces this matrix:

| Channel | Admitted destination classes |
|---|---|
| `CCB_T1_CHANNEL_EXPLICIT_SYMBOLIC` | semantic concept candidate, procedural recipe candidate, language construction candidate, CCDL board candidate, protected-review-only |
| `CCB_T1_CHANNEL_DEMONSTRATION_PROCEDURAL_INDUCTION` | procedural recipe candidate, strategy-board candidate, dialogue-procedure candidate, protected-review-only |
| `CCB_T1_CHANNEL_NEURAL_DISTILLATION` | replaceable neural proposal-subboard candidate, protected-review-only |
| `CCB_T1_CHANNEL_RETRIEVAL_LINKED_KNOWLEDGE` | source-linked retrieval-record candidate, protected-review-only |
| `CCB_T1_CHANNEL_SYNTHETIC_EXPERIENCE` | CAS-SDG curriculum candidate, episodic-training-record candidate, protected-review-only |

The word `candidate` is essential. A destination names the type of artifact a future authorized system could consider; it does not authorize a write. Neural destinations remain replaceable proposal generators under the same closed authority boundary.

## 6. Teacher roles

The exact teacher roles are:

- `CCB_T1_ROLE_LECTURER`;
- `CCB_T1_ROLE_DEMONSTRATOR`;
- `CCB_T1_ROLE_SOCRATIC_TUTOR`;
- `CCB_T1_ROLE_CURRICULUM_DESIGNER`;
- `CCB_T1_ROLE_ADVERSARY`;
- `CCB_T1_ROLE_CRITIC`;
- `CCB_T1_ROLE_RESEARCH_MENTOR`.

A `TeacherRoleAssignment` binds teacher, provider, model, revision, adapter, domain, channel, destination, assigned roles, faculty-separation group, and proposal duties. No teacher role includes examiner, custodian, verifier, grader, promoter, state writer, permission grantor, or rollback executor.

The same teacher may hold several proposal roles only when those assignments are visible in the faculty manifest. It may never generate or view protected cases before sealing, configure or modify the frozen verifier, grade its own lesson, select protected seeds, authorize promotion, or mutate the learned artifact.

## 7. Protected non-autonomous categories

The following exact categories may receive explanations, critiques, or candidate amendments but may not undergo autonomous promotion:

- `CCB_T1_PROTECTED_AUTHORITY_CONTRACT`;
- `CCB_T1_PROTECTED_SOLE_WRITER_RULE`;
- `CCB_T1_PROTECTED_PROOF_CHECKER`;
- `CCB_T1_PROTECTED_TRACE_VERIFIER`;
- `CCB_T1_PROTECTED_BENCHMARKS`;
- `CCB_T1_PROTECTED_CONSTITUTIONAL_VALUES`;
- `CCB_T1_PROTECTED_DEPLOYMENT_PERMISSIONS`;
- `CCB_T1_PROTECTED_ROLLBACK_MACHINERY`;
- `CCB_T1_PROTECTED_DEFINITION_OF_IMPROVEMENT`.

An episode that names any protected category must use `CCB_T1_DEST_PROTECTED_REVIEW_ONLY`, must set `autonomous_promotion_allowed: false`, and must identify a separately governed review route. No CCB-T1 receipt can convert that route into an authorization.

## 8. TeachingEpisode contract

A `TeachingEpisode` binds:

- episode, lesson, version, and optional parent/rollback identities;
- one domain, transfer channel, and destination;
- teacher-role assignments and optional specialized-contract references;
- typed proposed content, claimed scope, known exceptions, and validity window;
- explicit prerequisites with expected evidence and unresolved status;
- development examples, contrasts, negative cases, and counterexamples;
- protected held-out, frozen regression, deterministic replay, and delayed-retention plans;
- independent custodians, manifests, seed partitions, and frozen verifier digests;
- pre-learning observation references and proposed post-learning measurement plan;
- full provenance and a proposal-only authority boundary.

Proposed content types are closed: claim, definition, procedure, reasoning strategy, proof method, tool contract, research method, memory method, dialogue procedure, creative method, board design, repair pattern, neural-training objective, or perception-grounding curriculum.

World-knowledge claims additionally require source references, a temporal classification, verification method, scope, exceptions, and a validity window. Tool lessons describe how to propose a typed action and verify returned data; they do not grant permission or execute the tool. Creative products must retain an explicit `IMAGINED` or `HYPOTHETICAL` evidence label rather than being stored as remembered or verified facts.

## 9. Prerequisite law

Every episode contains at least one prerequisite record. A record declares its type, evidence required, resolution status, and resolver class. An unmet prerequisite blocks qualification and is not silently replaced by a teacher assertion.

The experimental package may describe a proposed child lesson for the first unmet prerequisite. It does not authorize RPM to create, execute, return, or promote that child. Current RPM semantics remain unchanged.

Before a provisional recommendation, every required prerequisite must have a bound passing evidence receipt or an explicitly admitted `NOT_APPLICABLE` rule from a frozen domain profile. A teacher cannot waive a prerequisite it proposed.

## 10. Examination custody

Every episode and qualification receipt binds four distinct evidence partitions:

1. development evidence under `CCB_T1_DEVELOPMENT_CUSTODIAN`;
2. protected held-out transfer under `CCB_T1_PROTECTED_HELD_OUT_CUSTODIAN`;
3. frozen regression evidence under `CCB_T1_FROZEN_REGRESSION_CUSTODIAN`;
4. delayed retention evidence under `CCB_T1_DELAYED_RETENTION_CUSTODIAN`.

A fifth role, `CCB_T1_FROZEN_VERIFIER_CUSTODIAN`, owns the sealed verifier configuration. The schema requires declarations that teacher identities are excluded, development and protected seeds are disjoint, protected cases remain withheld until sealing, the verifier freezes before protected execution, and custody is separated.

JSON Schema cannot prove organizational independence, cross-array seed disjointness, clock order, or identity inequality. A qualification runner must recompute those conditions before issuing a receipt. Assertions without recomputation are insufficient.

For research, constitutional, board-design, self-improvement, high-stakes, or mutable-world-knowledge lessons, a human-authored or independently sourced anchor is mandatory. One teacher producing both a lesson and stylistically different tests is not independent evidence.

## 11. Namespaced lifecycle

CCB-T1 reserves these exact artifact states:

```text
CCB_T1_EPISODE_PROPOSED
CCB_T1_EPISODE_SCHEMA_VALID
CCB_T1_EPISODE_PREREQUISITES_SATISFIED
CCB_T1_EPISODE_DEVELOPMENT_EVIDENCE_PASS
CCB_T1_EPISODE_PROTECTED_HELD_OUT_PASS
CCB_T1_EPISODE_REGRESSION_PASS
CCB_T1_EPISODE_PROVISIONAL_PROMOTION_RECOMMENDED
CCB_T1_EPISODE_DELAYED_RETENTION_PASS
CCB_T1_EPISODE_DURABLE_PROMOTION_RECOMMENDED
CCB_T1_EPISODE_QUARANTINED
CCB_T1_EPISODE_SUPERSEDED
CCB_T1_EPISODE_ROLLBACK_RECOMMENDED
```

Generic values such as `ACTIVE`, `VERIFIED`, or `PROMOTED` are prohibited because they collide with existing runtime concepts and overstate authority. A recommendation is not a mutation, installation, memory write, proof, or commitment.

## 12. Qualification law

A provisional qualification recommendation requires:

```text
schema_valid
AND domain_channel_destination_valid
AND teacher_role_assignments_valid
AND protected_category_policy_valid
AND prerequisites_satisfied
AND development_evidence_pass
AND protected_held_out_pass
AND frozen_regression_pass
AND deterministic_replay_pass
AND provenance_complete
AND custody_verified
AND retention_plan_sealed
AND critical_failure_count = 0
```

A durable qualification recommendation additionally requires:

```text
delayed_retention_pass
AND lineage_complete
AND qualified_rollback_ancestor_available
```

Each evidence partition has a nonzero case count, immutable manifest digest, seed-partition digest, expected-output digest, custodian, execution state, and exact counts. A pass cannot hide a failed critical case behind an aggregate score.

Critical failures include invalid proof steps, source/validity-window failure, permission bypass, unsafe tool output acceptance, security or authority regression, protected-fixture exposure, teacher grading, replay mismatch, fabricated provenance, imagined-to-verified relabeling, ungrounded multimodal claims, and unauthorized effects.

## 13. Exact metrics and lineage

`ApprenticeshipLineage` is append-only and binds every version, parent, qualification receipt, recommendation, supersession, quarantine, and rollback target. A rollback target must be a qualified ancestor with matching artifact and evidence digests.

Each metrics snapshot records integer or exact-string quantities only:

- pre/post capability in signed micro-units;
- learning gain in signed micro-units;
- pre/post capability resistance in nonnegative micro-units;
- resistance reduction in signed micro-units;
- held-out transfer numerator, denominator, and basis points;
- retention numerator, denominator, and basis points;
- teacher-assisted and total task counts with dependence basis points;
- teacher compute cost in integer quanta;
- teaching-efficiency numerator and positive denominator;
- critical regression and unauthorized-commit counts.

The runner must recompute every derived value. Basis points are not floating estimates, and zero denominators are invalid. These are experimental CCB-T1 metrics, not current source-defined CAS quantities.

CAS-Ohm stage records may be referenced for before/after observation. They remain `OBSERVATION_ONLY`: CAS-Ohm does not decide correctness, causality, qualification, destination, curriculum priority, or promotion. Behavioral evidence establishes whether the effect is correct; attention measurements only describe the measured path.

## 14. Specialization rules

- Language uses the existing CCB-L1 apprenticeship contracts and semantic-frame comparison.
- Mathematics requires an exact checker or proof verifier; teacher agreement never proves a step.
- Software lessons execute only in an isolated qualification harness and must include regression, security, and resource assumptions.
- Tool-use lessons test permission refusal and output validation; they never authorize live effects.
- Retrieval-linked world knowledge binds source, retrieval time, validity window, and contradiction handling.
- Neural distillation produces a replaceable proposal subboard candidate with held-out data and frozen controls; weights receive no authority.
- Board design and repair remain protected-review-only and require compiler/DRC/simulation/fault/authority-invariant evidence before even a recommendation.
- Multimodal grounding requires modality-linked evidence; text labels alone do not ground sensory concepts.

## 15. Required negative tests before integration

An implementation claiming this contract must reject:

- an unknown domain, channel, destination, content type, role, lifecycle state, verifier class, or protected category;
- an inadmissible channel/destination pairing;
- a protected category routed anywhere except protected review;
- missing or unresolved prerequisites presented as satisfied;
- absent development, protected held-out, regression, replay, or retention plans;
- zero-case partitions marked passing;
- floating confidence, metrics, cost, probability, or ratio values;
- overlapping development/protected seeds;
- teacher custody, early protected-case visibility, verifier modification, self-grading, or promotion authority;
- provisional recommendation without a sealed retention plan;
- durable recommendation without delayed-retention evidence and a qualified rollback ancestor;
- aggregate success with any critical failure;
- a CAS-Ohm observation used as correctness, causality, or promotion authority;
- current facts without source-linked retrieval time and validity window;
- tool lessons that grant permission or execute an effect;
- constitutional, authority, verifier, benchmark, deployment, rollback, or improvement-definition lessons marked autonomously promotable;
- any artifact that emits a CNCM intent or claims a kernel, memory, source, or runtime mutation.

## 16. Integration rule

CCB-T1 is an experimental contract with an isolated host-side reference laboratory. Its artifacts may be authored, validated, and exercised by that laboratory and its browser bridge. They must not be wired into the current CNCM kernel, installed as native memory, treated as kernel-learned capability, or described as CAS-RRK-controlled promotion until a separately authorized implementation and current qualification evidence exist.
