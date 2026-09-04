# CCB-L1 Grammar Apprenticeship v0.1

Status: `EXPERIMENTAL / NOT KERNEL INTEGRATED`

This document defines a contract-first package for teaching inspectable English constructions to CCB-L1. It defines proposal, qualification, lineage, and promotion-record artifacts. Its companion `cncm/language_apprenticeship.py` provides an isolated deterministic laboratory for compiling and qualifying bounded constructions in a local language store. It does not add a live teacher model, a kernel issuer, a CNCM intent, a durable memory-write path, or a kernel state transition.

The governing principle is:

> Foreign proposals are permitted. Foreign commitments are prohibited.

The current CNCM runtime does not perform durable lexical or grammatical learning. Registered vocabulary is data, dialogue-local correction is provisional, and the existing authority contract permits only episodic writes. Every lifecycle and promotion value below is therefore an experimental artifact-state vocabulary, not a claim that CNCM-RRK `0.1.0` can install it.

## 1. Purpose and boundary

The apprenticeship package is designed to let an external teacher propose a reusable language rule while CNCM-controlled, independently custodied evidence determines whether the proposal generalizes. A lesson must be representable as typed data, compile to a closed semantic transformation representation, survive protected tests, retain complete provenance, and remain reversible.

The package may describe:

- candidate lexical, morphological, grammatical, role, reference, discourse, and realization lessons;
- expected semantic frames and inspectable construction artifacts;
- development, protected, frozen-verifier, regression, ambiguity, replay, and delayed-retention evidence;
- provisional promotion, durable promotion, quarantine, supersession, and rollback recommendations in an offline experimental store.

The package may not:

- treat teacher prose, confidence, model weights, or repeated agreement as truth;
- let a teacher select, modify, view, or grade its protected examination cases;
- turn a lesson, qualification receipt, or promotion receipt into a kernel intent;
- write machine state, episodic memory, durable grammar, source, protected contracts, or the authority manifest;
- confer proof, meaning, commitment, permission, halt, action, or self-modification authority;
- claim kernel integration, native runtime coverage, or qualified English capability.

Any future live promotion path requires a separately versioned authority specification, manifest, intent schema, coordinator validation, negative tests, replay tests, and migration/rollback contract. Runtime configuration alone cannot create that authority.

## 2. CCB-L1 subboard family

CCB-L1 is partitioned by responsibility. The partitions are artifact scopes in this package; they are not installed scheduler or kernel components.

| Subboard | Scope | Required restraint |
|---|---|---|
| `CCB-L1-LEX` | lexemes, senses, categories, argument types, aliases | no autonomous sense selection or durable acquisition |
| `CCB-L1-MORPH` | inflection, derivation, tense, number, word formation | no unrestricted executable rewrite rules |
| `CCB-L1-GRAM` | reusable surface constructions and semantic transformation IR | no sentence-template memorization as a substitute for generalization |
| `CCB-L1-ROLE` | agent, patient, recipient, instrument, location, experiencer, stimulus, source, goal | no role binding from plausibility alone |
| `CCB-L1-REF` | pronouns, descriptions, identity candidates, anaphora | unresolved or ambiguous reference remains explicit |
| `CCB-L1-DISC` | topic, turn context, discourse links, unresolved context | no invented conversational history or intent |
| `CCB-L1-REALIZE` | admitted semantic frame to grammatical surface proposal | no semantic additions, omissions, or authority changes |

`CCB-L1-GRAM` is the immediate experimental target. A construction describes a reusable surface pattern, binds typed variables, and maps them through a closed transformation IR into a `SemanticFrame`. The transformation is data. It is not host code and cannot call tools, network services, subprocesses, or kernel APIs.

## 3. Normative artifact set

The following JSON Schemas are normative for this experimental package:

- `schemas/language_lesson_packet.schema.json` — one proposal-only teacher lesson;
- `schemas/grammar_construction.schema.json` — one versioned, inspectable construction candidate;
- `schemas/semantic_frame.schema.json` — language-independent expected meaning graph;
- `schemas/language_qualification_receipt.schema.json` — immutable result from one evidence channel and stage;
- `schemas/language_promotion_receipt.schema.json` — non-authoritative record of a requested experimental transition;
- `schemas/version_lineage.schema.json` — append-only construction/version ancestry and transition evidence.

Objects are closed with `additionalProperties: false`. IDs follow `^[A-Za-z_][A-Za-z0-9_.:-]*$`. Digests are lowercase SHA-256 hex. Arrays are ordered unless explicitly marked as sets. Exact ratios use bounded integer basis points from `0` through `10000`; floating-point confidence is prohibited.

Every artifact carries this package status:

```text
package_maturity = EXPERIMENTAL
kernel_integration_status = NOT_KERNEL_INTEGRATED
runtime_effect = NONE
```

## 4. Teacher lesson contract

A `LanguageLessonPacket` carries a teacher identity and immutable model/revision digests, the target subboard, prerequisites, a closed surface-pattern declaration, a semantic-transformation proposal, examples, expected semantic-frame references, claimed scope, bounded confidence in basis points, custody manifests, and provenance.

The teacher may propose:

- a surface pattern and typed variables;
- a semantic transformation artifact reference;
- positive examples, minimal pairs, counterexamples, ambiguity cases, and exceptions;
- prerequisite construction or lexicon IDs;
- a claimed scope and confidence from `0` to `10000` basis points.

The teacher confidence is metadata only. It cannot satisfy a gate, weight a protected test, break ambiguity, select a meaning, authorize promotion, or become an intent credential.

The packet's authority boundary fixes every authority flag to `false`, fixes `emits_cncm_intents` to `false`, and fixes `proposal_only` to `true`.

## 5. Construction and semantic representation

A `GrammarConstruction` is a versioned candidate containing:

1. a closed token/slot surface pattern;
2. typed variable bindings;
3. a reference to a closed semantic-transformation IR artifact and digest;
4. admitted features such as voice, tense, polarity, quantification, clause type, and sentence force;
5. scope restrictions and explicit exceptions;
6. lesson, qualification, and lineage provenance;
7. one namespaced lifecycle value.

Executable source strings are not admitted as semantic transformations. An implementation may compile a declared IR only after validating the IR version and operation vocabulary. Unknown operations fail closed.

A `SemanticFrame` contains no raw English and no proof assertion. It uses typed nodes and directed role edges. Role edges include `AGENT`, `PATIENT`, `RECIPIENT`, `INSTRUMENT`, `LOCATION`, `EXPERIENCER`, `STIMULUS`, `SOURCE`, `GOAL`, and structural relations needed for clauses, properties, reference, and discourse. Tense, aspect, voice, polarity, modality, sentence force, and quantifier scope are explicit.

For the passive construction, the active and passive examples must produce the same canonical semantic-frame digest while the role-reversed contrast must produce a different digest.

## 6. Namespaced lifecycle

These exact values are reserved for grammar apprenticeship artifacts. Generic values such as `PROPOSED`, `ACTIVE`, or `ROLLED_BACK` are not used because they collide with existing dialogue, branch, and machine statuses.

| Order | Exact artifact state | Required evidence before entry |
|---:|---|---|
| 1 | `CCB_L1_GRAM_PROPOSED` | typed lesson and candidate exist |
| 2 | `CCB_L1_GRAM_SCHEMA_VALID` | all schemas and closed vocabularies validate |
| 3 | `CCB_L1_GRAM_COMPILED` | candidate compiles to the declared closed IR |
| 4 | `CCB_L1_GRAM_POSITIVE_EXAMPLES_PASS` | every admitted positive case matches its expected frame |
| 5 | `CCB_L1_GRAM_CONTRAST_TESTS_PASS` | minimal pairs preserve required equality and inequality relations |
| 6 | `CCB_L1_GRAM_HELD_OUT_GENERALIZATION_PASS` | unseen protected combinations pass |
| 7 | `CCB_L1_GRAM_PRIOR_GRAMMAR_REGRESSION_PASS` | frozen prior-construction suite has no critical regression |
| 8 | `CCB_L1_GRAM_AMBIGUITY_BEHAVIOR_PASS` | ambiguity yields alternatives, clarification, or unsupported—not invented certainty |
| 9 | `CCB_L1_GRAM_PROMOTED_PROVISIONALLY` | all preceding receipts are present and replayable |
| 10 | `CCB_L1_GRAM_DELAYED_RETENTION_PASS` | delayed, independently run retention suite passes |
| 11 | `CCB_L1_GRAM_PROMOTED_DURABLY` | retention receipt and complete lineage are present |
| 12 | `CCB_L1_GRAM_ACTIVE` | selected by the experimental grammar-store view |
| — | `CCB_L1_GRAM_QUARANTINED` | evidence conflict, regression, custody failure, or unresolved anomaly |
| — | `CCB_L1_GRAM_SUPERSEDED` | a qualified descendant replaces this version |
| — | `CCB_L1_GRAM_ROLLED_BACK` | an accepted rollback receipt restores a qualified ancestor |

In this package, a promotion receipt records a requested transition only. It fixes `authorized_by_kernel`, `kernel_state_write_performed`, and `memory_write_performed` to `false`. Therefore, even the words "promoted durably" denote a target state in an offline experimental artifact store until a future authority version explicitly admits a live path.

## 7. Examination custody

Teacher/test separation is mandatory.

| Channel | Custodian role | Teacher access | Purpose |
|---|---|---|---|
| Development | `CAS_SDG_DEVELOPMENT_CUSTODIAN` | lesson and development outputs allowed | expand positives, contrasts, and adversarial development cases |
| Protected held-out | `PROTECTED_FIXTURE_CUSTODIAN` | manifest and cases withheld until evaluation is sealed | test novel combinations from a separately controlled seed set |
| Frozen verifier | `FROZEN_VERIFIER_CUSTODIAN` | no modification or grading control | deterministically compare actual and expected semantic frames |
| Delayed retention | `DELAYED_RETENTION_CUSTODIAN` | no case selection or grading control | detect brittle or transient success after a declared delay |

Every lesson declares separate development and protected manifest digests, separate seed lists, and the attestations:

```text
development_and_protected_seeds_disjoint = true
teacher_excluded_from_protected_custody = true
teacher_excluded_from_verifier_custody = true
verifier_frozen_before_protected_run = true
custody_separated = true
```

The schema can require these declarations but cannot prove organizational independence or compare every identity and seed across nested arrays. The qualification runner must enforce identity inequality, seed disjointness, frozen artifact digests, protected visibility, and timestamp/sequence rules before issuing a receipt.

For high-impact constructions, at least one protected semantic anchor must be independently human-authored, derived from a separately governed reference set, or corroborated by multiple teacher families. Repeated outputs from one teacher are not independent evidence.

## 8. Acceptance law

A provisional-promotion request is admissible only when all of the following are true:

```text
schema_valid
AND compiled
AND positive_examples_pass
AND contrast_tests_pass
AND held_out_generalization_pass
AND prior_grammar_regression_pass
AND ambiguity_behavior_pass
AND deterministic_replay_pass
AND provenance_complete
AND custody_verified
```

A durable-promotion request additionally requires:

```text
delayed_retention_pass
AND lineage_complete
AND rollback_target_available
```

No aggregate score may hide a critical failure. Role reversal, polarity reversal, quantifier collapse, invented reference, custody breach, replay mismatch, unauthorized effect, or lost provenance is a critical failure and forces rejection or quarantine. Zero test cases never constitutes a pass.

## 9. Qualification receipts

Each `LanguageQualificationReceipt` covers exactly one construction version, one lifecycle stage, and one evidence channel. It binds:

- the construction, lesson, IR, test-manifest, verifier, and expected-frame digests;
- the custodian role and protected visibility state;
- every case result and its expected/actual semantic-frame digest;
- integer pass/fail/ambiguous/unsupported counts;
- exact pass rate in basis points;
- deterministic replay result and replay digest;
- critical-failure codes;
- the fixed proposal-only authority boundary.

Qualification stages use exact namespaced values from the lifecycle table. Receipt results use `CCB_L1_QUAL_PASS`, `CCB_L1_QUAL_FAIL`, or `CCB_L1_QUAL_INCONCLUSIVE`.

The frozen verifier evaluates semantic equality, inequality, feature preservation, declared ambiguity behavior, and deterministic replay. It does not establish broad empirical truth, decide promotion, modify the construction, or identify a CAS-Ohm observation as a cause.

## 10. Promotion, quarantine, supersession, and rollback

A `LanguagePromotionReceipt` binds one action, exact from/to lifecycle states, qualification receipts, a complete gate summary, the construction and lineage digests, and an optional rollback target.

Its exact actions are:

- `CCB_L1_GRAM_REQUEST_PROVISIONAL_PROMOTION`;
- `CCB_L1_GRAM_REQUEST_DURABLE_PROMOTION`;
- `CCB_L1_GRAM_REQUEST_ACTIVATION`;
- `CCB_L1_GRAM_REQUEST_QUARANTINE`;
- `CCB_L1_GRAM_REQUEST_SUPERSESSION`;
- `CCB_L1_GRAM_REQUEST_ROLLBACK`;
- `CCB_L1_GRAM_REJECT_PROMOTION`.

The receipt's effect is always `CCB_L1_PROMOTION_RECORDED_ONLY`. It is not an authority token and cannot be submitted as a current CNCM intent.

`VersionLineage` is append-only. Every node binds its artifact digest, parents, source lesson, source promotion receipt, lifecycle state, and qualification receipts. Every transition binds the before/after versions and states, reason code, receipt, and evidence digest. An implementation must reject cycles, duplicate version IDs, missing parents, a rollback target that is not an ancestor, or an artifact digest mismatch.

## 11. Teacher operating modes

The architecture admits three proposal modes without changing authority:

- `CCB_L1_TEACHER_MODE`: proposes lesson packets during controlled offline learning;
- `CCB_L1_RUNTIME_CONSULTANT_MODE`: may propose candidate interpretations only after a native diagnostic reports unsupported coverage;
- `CCB_L1_SHADOW_MODE`: produces a comparison candidate that cannot affect the committed path.

The teacher never receives a promotion capability. Runtime consultation requires a future, separately versioned typed adapter. It is not present in this package.

## 12. CAS-Ohm observation boundary

CAS-Ohm may attach observation references to a lesson or qualification receipt. It may measure declared flow, residual, attention-routing, resistance, saturation, or alignment quantities under its own protocol.

CAS-Ohm may not:

- determine whether a construction is linguistically or semantically correct;
- assign a lifecycle state;
- authorize promotion, quarantine, supersession, rollback, or curriculum choice;
- identify a measured residual as the cause of failure;
- emit a CNCM intent or mutate language artifacts.

Semantic-frame and contrast evidence determines the observed behavioral fault. CAS-Ohm observations may rank probe neighborhoods or compare before/after measurements only. Every attached reference is explicitly `OBSERVATION_ONLY` and `causal_identification_authority: false`.

## 13. Response diagnostics are not terminal statuses

The following values are response-planning diagnostics only:

- `CCB_L1_DIAG_LANGUAGE_UNDERSTOOD_KNOWLEDGE_AVAILABLE`;
- `CCB_L1_DIAG_LANGUAGE_UNDERSTOOD_KNOWLEDGE_MISSING`;
- `CCB_L1_DIAG_UNKNOWN_CONSTRUCTION`;
- `CCB_L1_DIAG_AMBIGUOUS_PARSE`;
- `CCB_L1_DIAG_UNKNOWN_LEXEME`;
- `CCB_L1_DIAG_INSUFFICIENT_COVERAGE`.

They do not extend the kernel halt vocabulary. In particular, `LANGUAGE_UNDERSTOOD` and `KNOWLEDGE_MISSING` are not terminal statuses. A future adapter may use a diagnostic to construct an admitted `ResponsePlan`; CAS-RRK still halts only under the existing authority contract.

## 14. Metrics and retirement profiles

Coverage, fidelity, intervention, honesty, role-reversal discrimination, compositional generalization, and regression metrics must be reported as integer basis points with exact numerator and denominator. A zero denominator is invalid. Retirement thresholds are declared qualification targets, not evidence of achieved capability.

An example target-domain profile may declare:

```text
native_coverage_bps >= 9500
semantic_fidelity_bps >= 9800
role_reversal_discrimination_bps >= 9900
unknown_term_honesty_bps >= 9800
teacher_intervention_bps <= 500
critical_regressions = 0
unauthorized_teacher_commits = 0
```

No target is earned until its protected receipts, manifest digests, sample sizes, and replay evidence are present.

## 15. First qualification slice

The first executable slice should be narrow enough to falsify:

1. active/passive role equivalence;
2. active role-reversal inequality;
3. positive/negative polarity inequality;
4. unknown lexeme honesty;
5. ambiguity preservation;
6. deterministic replay;
7. prior controlled-English regression absence.

The slice should use unseen noun/verb substitutions and protected seed partitions. Questions, commands, coordination, conditionals, reference, discourse, and realization follow only after this slice produces independently custodied receipts.

## 16. Required negative tests before integration

Any implementation claiming conformance must reject at least:

- a lesson with an unregistered subboard, lesson type, IR version, or operation;
- any floating-point confidence or ratio;
- missing model, artifact, fixture, verifier, or lineage digests;
- teacher custody of protected cases or the frozen verifier;
- overlapping development/protected seeds;
- a protected manifest exposed before the verifier is frozen;
- a promotion request with a failed, inconclusive, missing, zero-case, or replay-mismatched gate;
- a durable-promotion request without delayed retention and a rollback ancestor;
- role, polarity, quantifier, or reference collapse hidden by an aggregate score;
- generic unnamespaced lifecycle values;
- CAS-Ohm used as semantic correctness or causal authority;
- `LANGUAGE_UNDERSTOOD` or `KNOWLEDGE_MISSING` used as a kernel halt status;
- any attempt to emit a kernel intent, write memory/state, modify source, or expand authority.

## 17. Integration rule

This package is a follow-on design contract only. Its artifacts may be created, inspected, validated, and tested in an isolated experimental harness. They must not be wired into the current runtime or described as native capability until the separately versioned authority and implementation work is complete and current evidence proves the claimed path.
