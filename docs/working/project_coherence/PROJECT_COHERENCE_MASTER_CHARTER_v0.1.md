# Project Coherence Master Charter v0.1

Document status: `DRAFT / OPEN / NOT FROZEN`

- Program: CAS/TKS Provable Systems Evolution
- Working codename: Project Coherence
- Planned coordinated release: Provable Systems Release 8.0 (`PSR-8`)
- Charter version: 0.1
- Charter date: 2026-08-04
- Repository baseline: Git commit `81b5c18b`
- Working branch: `codex/project-coherence-phase0`

## 1. Authority and purpose

This charter is the change-control constitution for a proposed, version-preserving evolution of TKS, the Noetic Topos, CAS Core, CAS PCBA, CAS-Ohm, and CAS Harness. It authorizes research organization and audit work. It does not release, validate, or silently replace any successor system.

The controlling rule is selective inheritance:

> No definition, theorem, model, implementation, experiment, or product claim enters PSR-8 merely because an earlier artifact called it canonical, because a proof looks plausible, or because a result appears in a research analysis.

The source baselines remain available byte-for-byte. Successor work must point back to them through versioned migration records.

This charter does not itself establish:

- an empirically validated theory of cognition;
- a production-ready CAS Harness capability;
- a physically electrical interpretation of CAS-Ohm or CAS PCBA;
- the correctness, novelty, authorship attribution, or peer-review status of the supplied *Ten Advances* manuscript;
- a public-release or patent-disclosure decision; or
- authorization to relabel an `OPEN`, `NOT LICENSED`, or `FLAG_FOR_HUMAN_REVIEW` item as closed, licensed, or accepted.

## 2. Freeze boundary

The following classes of source are frozen as historical or operational baselines. “Frozen” means preserved and cited by identity; it does not mean every claim inside the source is correct.

| Source ID | Baseline | Charter treatment |
|---|---|---|
| `SRC-SEMANTIC-AUTHORITY-REGISTRY-20260720` | Owner-signed TKS/CAS semantic source registry | Highest recorded semantic manifest. It binds precedence and run fields but leaves twelve conflicts unresolved and licenses no empirical claim. |
| `SRC-TKS74-MASTER-TEX` | TKS v7.4 master LaTeX source | Frozen broad source identity, subject to explicit correction overlays. |
| `SRC-TKS74-FULL-BEAUTIFUL-TEXT` | Registered TKS v7.4 integrated corrected-edition text | Frozen formal target-space authority, subject to correction overlays; not an empirical hidden-state map. |
| `SRC-TKS74-FULL-BEAUTIFUL-PDF` | Owner-supplied FULL_BEAUTIFUL PDF | Frozen 539-page rendering of the registered text, not a separate semantic authority. |
| `SRC-TKS74-REVIEW-CORRECTIONS` | TKS v7.4 review and corrections | Frozen correction/status overlay that outranks blanket inheritance language. |
| `SRC-TKS74-REFEREE` | TKS v7.4 referee-defensible edition | Frozen editorial overlay; not evidence of external acceptance or mechanical verification. |
| `SRC-TKS74-CORRECTED-CHAPTERS` | TKS v7.4 corrected chapters | Frozen field-specific correction overlay. |
| `SRC-TKS74-FULL-CORRECTED-UNREGISTERED` | Repository 596-page FULL_CORRECTED PDF | Context only. It differs materially from the registered FULL_BEAUTIFUL source and has not been admitted by the signed registry. |
| `SRC-NOETOPOS-CONSERVATIVE-TEX-REGISTERED` | Conservative Noetic Topos LaTeX source | Frozen formal baseline by hash. The source has no explicit version label; its claims remain conditional on its axioms. |
| `SRC-CAS77-NORMATIVE-REGISTERED` | Registered CAS foundational clarifications | Frozen normative CAS semantics for the ten canonical Noetics and admitted refinements. Byte-different repository copies remain separately identifiable. |
| `SRC-CAS77-ROLLOUT` | CAS v7.7 rollout plan | Frozen time-indexed implementation-status record; it explicitly shows that propagation is incomplete. |
| `SRC-TKS-OWNER-LOCK-20260603` | Owner-locked TKS definitions | Frozen source-bound definition record. |
| `SRC-TKS-F28-CROSSWALK` | TKS 28 Foundations translation key | Frozen named crosswalk; it is not an identity between TKS Foundations and CAS Core Drives. |
| `SRC-PCBA-ENGINEER-20260726` | Owner-supplied CAS PCBA Engineer build | Current engineering baseline by exact PDF hash. Its internal version label requires review because the latest changelog entry predates the supplied build. |
| `SRC-CAS-OHM-GUIDE-01` | CAS-Ohm Quantification Guide v0.1 | Working quantitative model, not validated telemetry. |
| `SRC-CAS-OHM-ADDENDUM-01` | CAS-Ohm Harness operationalization addendum v0.1 | Draft measurement proposal. Instrumented, behavioral, and scored fields remain distinct. |
| `SRC-CAS-OHM-PCBA-APP-I` | CAS PCBA Appendix I | Engineering calibration companion; design values remain distinct from measurements. |
| `SRC-HARNESS-16-HISTORICAL` | CAS Harness v1.6 reconciled spec sheet | Frozen historical claim snapshot only. It is not current production-readiness authority. |
| `SRC-HARNESS-PRODUCTION-TODO-LIVE` | Canonical CAS Harness Production TODO | Mutable, time-indexed source of truth for current product status, blockers, claim language, and next actions. |

The exact paths, hashes, status, and identity policies are recorded in `CANONICAL_SOURCE_AUTHORITY_MATRIX_v0.1.json`.

### 2.1 Corrected Harness boundary

The precursor plan described CAS Harness v1.6 as the “current evidence and product baseline.” That statement is now too old. Project Coherence preserves v1.6 as a historical snapshot, while current readiness and claim status remain governed by the canonical production TODO and current repository/provider evidence.

A mathematical research result cannot change product readiness on its own. A saved result is not a live feature. A green narrow test proves only its covered behavior.

### 2.2 Supplied primary manuscript under quarantine

The owner supplied the 249-page PDF *Ten Advances in Mathematics and Theoretical Computer Science*, SHA-256 `64B900D5FAE6FE22F2AE1B8E3B712D20055194A6C81CF343A2455E5898AC7DD6`. It is also available from an OpenAI-hosted public URL and describes itself as work obtained by an internal OpenAI model. It has no DOI, arXiv identifier, journal or conference venue, or named chapter authors in the reviewed artifact.

Accordingly:

- `SRC-TEN-ADVANCES-PRIMARY` is `present` and classified `UNTRUSTED_RESEARCH_INPUT`;
- each new result is labeled `MANUSCRIPT_CLAIM` unless and until its proof, novelty, and publication status are independently verified;
- every bespoke CAS/TKS transfer remains `OPEN`, `NOT LICENSED`, and in Ring 4;
- no such result may enter Ring 1 or Ring 2 merely because the manuscript supplies a proof;
- exact theorem names, constants, exponents, and hypotheses must be transcribed from the primary source rather than the earlier transfer summary; and
- standard mathematics that can be proved independently must be cited and classified independently rather than credited as a new result.

The first red-team audit has already found a material transfer error: the proposed projector-capacity result omitted the source proposition's load-bearing isometry/intertwining hypothesis. The normalized projector-overlap kernel remains a standard specialization; the capacity transfer remains a `PROOF_GAP`.

## 3. Source-authority order

When artifacts disagree, authority is resolved by the type of question being asked.

1. Semantic source precedence: `SRC-SEMANTIC-AUTHORITY-REGISTRY-20260720` and its approval receipt, subject to the registry's explicitly unresolved conflicts.
2. Canonical Noetic meaning: the registered field authorities and `SRC-CAS77-NORMATIVE-REGISTERED`.
3. Original TKS meaning: exact original TKS source, version, symbol, and definition hash, with registered correction overlays applied by field.
4. Conservative Noetic Topos theorem text: `SRC-NOETOPOS-CONSERVATIVE-TEX-REGISTERED`.
5. Current CAS Harness product status: `SRC-HARNESS-PRODUCTION-TODO-LIVE` plus current runtime, provider, CI, and deployment evidence.
6. PCBA engineering presentation: the owner-supplied current build and its source files.
7. CAS-Ohm quantitative proposals: the named guide, addendum, and PCBA appendix, each with its stated honesty boundary.
8. Research analyses and external transfers: hypothesis inputs only until source, proof, literature, and reduction review are complete.

No lower authority silently rewrites a higher authority. Where two authorities govern different semantic types, Project Coherence creates an explicit typed crosswalk rather than declaring an identity.

## 4. Canonical preservation rules

The following rules are binding on all PSR-8 work.

1. The ten Noetic names and definitions remain exact: Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, and Below/Effect.
2. TKS A-D Worlds are not silently renamed into CAS P/C/E/O Domains.
3. TKS 28 Foundations 1.0 remain distinct from CAS Core Drives.
4. A crosswalk is a named, typed transformation with a source, target, scope, loss statement, and version. It is not an identity unless an identity theorem is actually proved.
5. Original TKS definitions, native symbols, normalized indices, fixtures, generated data, and definition hashes remain versioned experimental subjects.
6. No compact CAS summary may silently replace an original TKS definition.
7. Earlier terminology remains available through an explicit compatibility profile.
8. Exact equality, isomorphism, equivalence, approximation, statistical similarity, analogy, and empirical correlation are different relations and must use different fields or symbols.
9. Every approximate relation names a metric or divergence, tolerance, composition rule, and evidence source.
10. Every theorem names its assumptions, object types, dependencies, proof artifact, and claim boundary.
11. Every empirical claim names its population, model and architecture scope, controls, falsifier, uncertainty, and time-indexed evidence.
12. Every product claim uses the exact current status vocabulary: `LICENSED`, `NOT LICENSED`, or `OPEN`, with `ACCEPT` and `FLAG_FOR_HUMAN_REVIEW` reserved for their existing decision contexts.
13. Unsupported customer verdicts, unsafe execution, corrupt evidence, and missing claim records fail closed.
14. Mathematical correctness does not imply empirical validity, and empirical validity does not imply product readiness.
15. Public disclosure requires a separate disclosure decision; this charter makes none.

## 5. Successor namespaces

The following are proposed development namespaces, not released versions.

| Workstream | Proposed namespace | Current status |
|---|---|---|
| Typed mathematical core | TKS v8.0 | `OPEN / RING 4 GATE 1 REFERENCE CANDIDATE` |
| Categorical and evidence logic | Noetic Topos 2.0 | `OPEN / RING 4 GATE 1 REFERENCE CANDIDATE` |
| CAS architecture | CAS Core v8.0-RC | `OPEN / RING 4 BOUNDED SOFTWARE CANDIDATE TESTED` |
| Circuit engineering | CAS PCBA v8.0 | `OPEN / RING 4 BOUNDED SOFTWARE CANDIDATE TESTED` |
| Quantification | CAS-Ohm v1.0 | `OPEN / RING 4 BOUNDED SOFTWARE CANDIDATE TESTED` |
| Interpretability and experimental platform | CAS Harness v2.0 | `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED` |
| Clinical engineering profile | CAS PCBA Clinical 1.0 | `OPEN / NOT STARTED` |
| Proof and claim control | CAS Evidence and Theorem Registry 1.0 | `DRAFT / OPEN` |

No successor namespace may be represented as released, production-ready, peer-reviewed, or canonically frozen while this charter remains `NOT FROZEN`.

## 6. Admission rings

### Ring 1 - canonical core

Admission requires precise typing, internal consistency, a complete proof or explicit axiom status, cross-system necessity, a migration record, and independent review. Canonical ontology is preserved here; it is not recreated here.

### Ring 2 - verified extension library

Admission requires a complete proof under explicit hypotheses, dependency closure, a reproducible proof artifact, novelty classification, and a statement of what the result does not prove. A standard theorem specialized to CAS remains a specialization, not a new theorem of mathematics.

### Ring 3 - experimental profile

Admission requires operational definitions, preregistration, matched controls, clean nulls, falsifiers, uncertainty, held-out replication, Evidence Packet emission, and claim-language review. A mathematically coherent model may remain here indefinitely if evidence is weak.

### Ring 4 - frontier research annex

This ring contains promising transfers, unavailable or unverified primary sources, open reductions, conjectural architectures, and proposed analogies. Ring 4 material is research direction, not inherited truth.

Promotion follows one direction only:

`Ring 4 -> Ring 3 -> Ring 2 -> Ring 1`

The Integration Board may skip a ring only when the omitted ring is inapplicable and the record explains why. No workstream promotes its own result.

## 7. Theorem and claim controls

### 7.1 Statement kind

Every registry item is exactly one primary kind:

- `AXIOM`
- `DEFINITION`
- `THEOREM`
- `PROPOSITION`
- `LEMMA`
- `COROLLARY`
- `CONJECTURE`
- `MODEL`
- `EMPIRICAL_HYPOTHESIS`
- `PRODUCT_CLAIM`

An item may link to other kinds, but it may not remain an unlabeled hybrid.

### 7.2 Migration disposition

After audit, every inherited item receives exactly one disposition:

- `INHERITED`
- `CLARIFIED`
- `CORRECTED`
- `CONDITIONAL`
- `DOWNGRADED`
- `DEPRECATED`
- `REFUTED`
- `REPLACED`

Before audit, the separate review state is `UNASSESSED` or `IN_REVIEW`; this prevents an unreviewed item from being mislabeled as inherited.

### 7.3 Proof status

Proof status is independent from migration disposition. Permitted initial values are:

- `NOT_APPLICABLE`
- `PROOF_REQUIRED`
- `PROOF_GAP`
- `INFORMAL_PROOF_PRESENT`
- `PROVED`
- `FORMALLY_VERIFIED`
- `STANDARD_RESULT_CITED`
- `COUNTEREXAMPLE_PRESENT`
- `INDEPENDENT_REPLICATION_REQUIRED`

### 7.4 Novelty status

Every mathematical record states one of:

- `STANDARD_RESULT`
- `STANDARD_SPECIALIZATION`
- `FRAMEWORK_COUPLING`
- `CANDIDATE_NEW_RESULT`
- `NOVELTY_UNASSESSED`

“New to TKS/CAS” is not “new to mathematics.”

### 7.5 Product-claim status

Product claims preserve current exact language:

- `LICENSED`
- `NOT LICENSED`
- `OPEN`

No theorem-record status may automatically mutate a product-claim status.

The machine-readable contracts are `THEOREM_RECORD.schema.json` and `CLAIM_RECORD.schema.json`.

## 8. Initial migration controls

The initial migration matrix is machine-readable in `INITIAL_MIGRATION_MATRIX_v0.1.json`. Its first priorities are:

1. distinguish the state-plus-failure RPM computation from the realization section-retraction;
2. distinguish typed paths from unrestricted digit strings;
3. distinguish exact inverse cancellation from approximate operator error;
4. audit finite-state claims only on an explicitly finite semantic domain;
5. correct deterministic Hilbert-space lift norms where maps are many-to-one;
6. retract or replace the false occupation trace, idempotent partial-isometry, and orthogonal-projector claims exposed by the two-state constant-map counterexample;
7. quarantine spectral/MVR tables until concrete maps and correct nonnormal analysis are supplied;
8. retain the hash-identified conservative Noetic Topos source unchanged while separately studying what its topology forgets;
9. record that ACBE and RPM clauses add no nonmaximal covers, and redesign any claimed distinct modalities rather than relying on trivial or identical generated topologies;
10. treat current subcanonicity as refuted by counterexample and use explicit sheafification or a changed site/coverage;
11. require global-distribution feasibility hypotheses rather than inferring probabilistic gluing from pairwise marginals;
12. keep deterministic maps, Markov kernels, classical channels, and unitary maps type-distinct;
13. keep CAS-Ohm design values, behavioral proxies, instrumented readings, and human/LLM scores type-distinct;
14. keep historical Harness claims separate from current product status and future Harness 2 experiments; and
15. reject the transferred projector-capacity theorem until the omitted isometry/intertwining hypothesis is supplied by a CAS-specific construction.

The initial matrix records review-state counts of 26 `IN_REVIEW`, 1 `UNASSESSED`, and 1 `REVIEWED`; its migration-disposition counts are 27 `UNASSESSED` and 1 `CLARIFIED`. No inherited or canonical promotion has occurred.

## 9. Workstreams and decision authority

Project Coherence uses seven research cells.

| Cell | Responsibility |
|---|---|
| Canon and Semantics | Ontology, exact terminology, source authority, compatibility, migrations. |
| Formal Mathematics | Proofs, counterexamples, theorem registry, novelty classification. |
| Category and Sheaf Theory | Site/topos audits, markings, modalities, gluing, subcanonicity. |
| Dynamics and Geometry | Markov kernels, projectors, Fisher/Wasserstein geometry, stability. |
| PCBA and Systems Engineering | Typed components, CCDL, DRC, calibration, simulation, traceability. |
| Harness Experimental Science | Preregistration, probes, interventions, controls, Evidence Packets. |
| Verification, Publication, and IP | Proof assistant, independent review, release packaging, disclosure boundary. |

### 9.1 Integration Board

The Integration Board owns promotion and release decisions. At minimum, a promotion record needs independent sign-off from:

- the source/semantics owner for definition fidelity;
- a mathematical reviewer for theorem-bearing material;
- an experimental or engineering reviewer for measured claims; and
- a product-claim reviewer when wording could affect customer or public claims.

Public disclosure and patent decisions additionally remain `FLAG_FOR_HUMAN_REVIEW` until the owner and qualified counsel decide them. This charter does not invent or substitute that sign-off.

## 10. Release gates

### Gate 0 - charter and canon control

Status: `OPEN`

Closes only when:

- the charter is reviewed and explicitly frozen;
- every top-level baseline has an identity policy and source authority;
- every initial canonical term has a source, version, semantic type, aliases, and migration policy;
- the open-vs-held boundary has human review;
- version and compatibility rules are accepted; and
- unresolved source gaps have an owner and closure action.

The bounded load-bearing term census is now technically complete: it records 49
groups, 712 members, 22 pinned sources, and 19 preserved conflicts. It does not
select canon. Current blockers include owner-reviewed registry amendments or
accepted exclusions for the final frozen interface, the signed registry's
unresolved semantic conflicts, owner acceptance of the manuscript quarantine
and closure path, PCBA internal version-label ambiguity, the CAS-Ohm scale/unit,
gain-profile, and ASOM-axis conflicts, the PCBA grammar and CSB safety-reference
contradictions, Integration Board acceptance, and outstanding disclosure review.
The earlier active-compiler
drift concern is technically resolved: the current CRLF checkout normalizes
exactly to the registry-bound LF Git blob, as recorded in
`gate0/COMPILER_IDENTITY_NORMALIZATION_RECEIPT_v0.1.json`.

### Gate 1 - theorem, axiom, and claim audit

Status: `OPEN / IN PROGRESS`

Closes only when every major statement in scope has a statement kind, proof status, migration disposition, dependencies, and claim boundary. A proof sketch is not a completed proof. The internal red team has begun this gate and found explicit counterexamples, but independent specialist review and the full theorem ledger remain open.

### Gate 2 - TKS v8 typed core

Status: `OPEN / CANDIDATE IMPLEMENTATION IN REVIEW`

Closes only when typed composition, exact/approximate separation, proof artifacts, a compatibility parser, and fail-closed legacy warnings are verified.

Current evidence includes a separate finite typed-function reference kernel,
bounded exhaustive tests, deterministic-lift corrections, denotational
shortlex normal forms, and a pinned partial Lean proof seed. The compatibility
parser, exact/approximate calculus, universal proof obligations, semantic
mapping from v7.4, independent review, and canon admission remain open.

### Gate 3 - Noetic Topos 2.0

Status: `OPEN / FINITE REFERENCE CANDIDATE IN REVIEW`

Closes only when the information loss of the conservative unmarked construction is stated precisely, the reduction of ACBE/RPM coverage is resolved, proposed markings/modalities are well typed, subcanonicity is resolved, a nontrivial finite model exists, and a backward comparison to the hash-identified conservative baseline is proved.

Current evidence includes a sixteen-context transverse-partition model,
distinct ambient ACBE/RPM witnesses, strict provenance-bearing cover records,
a two-parent join derivation, schema-valid theorem and obligation ledgers, and
bounded Lean context lemmas. An internal finite-context proof candidate now
establishes modality commutation up to natural isomorphism on `PSh(L,Set)`.
The resolved factor is explicitly only four independent channels;
observational/product-site provenance, the product-site modality lift,
backward comparison, richer cross-context semantics, full formal proof, and
independent review remain open.

### Gate 4 - CAS Core 8, CAS PCBA 8, and CAS-Ohm 1.0

Status: `OPEN / RING 4 BOUNDED SOFTWARE CANDIDATES TESTED`

Closes only when:

- CAS Core semantic identities and crosswalks are versioned and nonidentity relations cannot be silently promoted to identity;
- every compatibility execution binds the requested source, compiler bytes, engine/toolchain profile, complete dependency closure, typed result digest, and conservative research boundary;
- registries are immutable, exact-schema and hash bound, action intent defaults to deny, and no claim-bearing action can be authorized by a self-authored receipt or caller omission;
- Python and Rust/compiler profiles are either shown equivalent on a declared conformance surface or retained as explicitly different profiles;
- PCBA ports, directions, signals, units, nets, test points, component parameters, and admissibility rules are typed;
- the admitted CCDL grammar has an exact conformance matrix and unsupported board forms fail closed;
- calibration is versioned, child measurements survive aggregation, and every simulation emits a deterministic trace;
- known-fault boards include the unmodified CSB threshold contradiction and are diagnosed rather than silently repaired;
- invalid boards fail the DRC; and
- CAS-Ohm quantities keep constraint scores, normalized regions, calibrated effective resistance, physical units, gain profiles, response regions, and semantic outcomes type-distinct, with network operations capability-gated by profile evidence.

Current evidence includes three isolated, independently red-teamed bounded
software candidates: CAS Core has 61 focused tests, CAS PCBA has 82 focused
tests plus 195 parameterized subcases, and CAS-Ohm has 65 focused tests plus 58
parameterized subcases. The reviews forced replay-based Core assessment,
raw-byte-backed registries, fixed PCBA arithmetic and complete provenance,
sounder DRC cycle/safety analysis, and an Ohm separation between structural
research completeness and authenticated Evidence Packet eligibility.

The adverse source evidence remains controlling: the formal PCBA EBNF does not
cover the published five-board corpus (four direct counterexamples), the CSB
fuse threshold is unreachable under its own saturation value, and the CAS-Ohm
sources contain eight preserved conflicts or under-specifications across scales,
units, full-scale methods, gain, network rules, ASOM, residuals, and Q4. Exact
compiler/toolchain closure, Python/Rust conformance, full CCDL/stateful
semantics, live calibration, external authority, empirical validity, safety,
peer review, migration acceptance, canon admission, product readiness, and
disclosure approval remain open. The bounded tests repair software behavior;
they do not accept successor semantics or license claims.

### Gate 5 - CAS Harness 2 research modules

Status is split across independent axes:

| Axis | Current status |
|---|---|
| Document | `DRAFT / OPEN / NOT FROZEN` |
| Decision | `OPEN / KEEP_OPEN` |
| Engineering | `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED` |
| Experimental | `NOT_STARTED` |
| License / disclosure / canon | `NOT LICENSED / HELD / NOT FROZEN` |
| Live / product route | `unavailable / not authorized` |

The engineering status records bounded software-candidate testing only; it does not claim a joined or live run. Experimental conclusions remain unavailable while the experimental axis is `NOT_STARTED` and the live/product route is `unavailable / not authorized`.

Each module closes separately only after execution integrity, preregistration, clean nulls, matched-taxonomy and wrong-layer controls, executor-auditor numerical agreement, held-out replication, falsifiers, Evidence Packet emission, and claim-language review.

No Gate 5 result changes current production readiness without a separate current live-product gate.

## 11. First-year execution sequence

The dates below are planning windows, not evidence or completion claims.

### Days 1-30

- freeze or revise this charter;
- complete the source-authority and symbol registries;
- complete the open-vs-held human review;
- build the initial theorem and claim ledgers;
- write the v7.4 corrigendum outline;
- complete the chapter-by-chapter manuscript quarantine and independent proof/literature audit; and
- establish the repository skeleton and validation checks.

### Days 31-90

- build the TKS v8 typed-core candidate;
- separate the two RPM structures;
- implement exact and approximate calculi;
- implement finite transformation-semigroup semantics;
- type the deterministic/stochastic/channel layers;
- draft the Noetic Topos 2.0 design specification; and
- begin proof-assistant artifacts.

### Days 91-180

- build candidate PCBA 8 components and DRC rules;
- define CAS-Ohm 1.0 calibration profiles;
- simulate memristive and projector modules as experimental profiles;
- implement a finite sheaf-coherence engine;
- draft Evidence Packet v2; and
- preregister the first Harness 2 experiments.

### Months 6-9

- run authorized open-weight experiments;
- replicate across models and architectures;
- execute adversarial and taxonomy-matched controls;
- measure causal-abstraction defects;
- expand formal proof coverage; and
- obtain external mathematical review.

### Months 9-12

- prepare release candidates only for gates actually closed;
- publish corrigenda and narrow papers rather than one undifferentiated manual;
- separate public and confidential editions;
- conduct patent and disclosure review;
- produce a 1:1 plain-English companion; and
- decide whether any part of PSR-8 is ready to release.

A failed theorem or experiment is a versioned result, not a result to hide.

## 12. Publication architecture

Candidate papers remain separate so each claim set can survive specialist review:

1. Typed Noetic Dynamics and Finite Fractal Semantics.
2. The Marked and Modal Noetic Topos.
3. Noetic Projection Geometry and State Capacity.
4. Noetic Markov Sheaves for Contextual AI Assessment.
5. ACBE as Approximate Causal Abstraction.
6. CAS PCBA 8: Adaptive Cognitive Circuit Engineering.
7. CAS Harness 2: Evidence-Grounded Validation of Structured Latent Representations.

Titles are working titles. A paper may not be submitted until its theorem, evidence, authorship, disclosure, and citation records are complete.

## 13. Definition of done

PSR-8 is complete only when all applicable statements below are true:

- every canonical symbol has one typed meaning in its version;
- every crosswalk is explicit and versioned;
- every theorem is proved, explicitly conditional, or downgraded;
- every approximate relation has a metric and error budget;
- every core object has a tested reference implementation;
- every PCBA component has typed ports and test points;
- every quantitative board has a calibration profile;
- every Harness claim has an Evidence Packet and falsifier;
- every legacy document has a migration path;
- every public claim has disclosure review;
- independent reviewers can reproduce the proofs and experiments; and
- the plain-English guide maps 1:1 to the formal specification.

At v0.1, none of these completion statements is asserted globally.

## 14. Freeze procedure for this charter

This draft may be frozen only after:

1. source hashes and identities are independently rechecked;
2. the owner resolves the named source/version ambiguities;
3. mathematical red-team and primary-literature findings are incorporated;
4. the open-vs-held boundary receives human review;
5. the Integration Board composition and decision rule are accepted; and
6. the owner explicitly approves the resulting charter version.

Freezing the charter is a material program decision. It is not inferred from silence and is not performed by this draft.

## 15. Immediate next actions

1. Keep Gate 0 and Gate 1 open while completing the full theorem/definition
   census, migration surface, independent proof/novelty review, owner conflict
   decisions, and explicit charter/canon freeze procedure.
2. Preserve the Gate 4 candidate as private Ring-4 evidence; complete external
   formal, semantic, systems, empirical, safety, and claim-language review
   against its stable hashes.
3. Build the hermetic runtime/dependency bundle, Python/Rust conformance surface,
   complete CCDL grammar, stateful PCBA profiles, and materialized authority and
   calibration identities without promoting unsupported claims.
4. Build CAS Harness v2 research modules with preregistration, matched controls,
   clean nulls, falsifiers, independent numerical replay, and Evidence Packet v2
   structural/authentication separation.
5. Execute only authorized, budgeted, private held-out experiments; retain all
   failed or nonreplicated hypotheses in Ring 4 and `NOT LICENSED`.
6. Complete the theorem-and-claim registry links, reproducibility packages,
   proof artifacts, migration tools, specialist papers, formal specification,
   and matching plain-English companion.
7. Prepare separate private and disclosure-filtered release packages; keep the
   public package `HELD` until explicit owner and qualified-counsel approval.
8. Freeze or release any successor only through the charter's explicit human
   decision procedure; never infer acceptance from a software test or silence.
