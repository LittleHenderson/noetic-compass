# CAS PCBA 8: Adaptive Cognitive Circuit Engineering

**Artifact status:** `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`

**Publication track:** Project Coherence charter Paper 6

**Draft version:** `v0.1`, source-bound to repository commit
`a1cd990109e7561dfd03949bf0e1653461c7ae44`

**Authorship:** `OPEN / NO AUTHORSHIP OR SUBMISSION DECISION RECORDED`

**Review:** `INTERNAL CROSS-REVIEW OPEN / EXTERNAL SPECIALIST REVIEW OPEN`

**Submission state:** `NOT READY FOR SUBMISSION`

## Abstract

CAS PCBA 8 is a typed, provenance-bearing research architecture for describing
and checking circuit-shaped cognitive-system models. The word *circuit* names an
engineering organization of typed components, ports, nets, state annotations,
calibration references, and deterministic traces. It does not assert a physical
electrical implementation or identify model quantities with voltage, current,
resistance, charge, or flux. This paper presents a source-bound delta over the
existing Gate 4 candidate rather than a replacement specification. The delta
organizes the candidate's implemented contracts into a publishable engineering
argument: semantic identities remain typed; board structure is canonicalized;
design-rule checks reject incompatible signal/unit pairs, unresolved ports,
unsafe feedback declarations, missing calibrated probes, and unreachable fuse
thresholds; supported simulations emit deterministic provenance-rich traces;
and only certified finite, deterministic, stateless transitions can cross the
TKS v8 adapter boundary.

The evidence is deliberately bounded. At the bound commit, an integrated Gate 4
receipt records 54 hash-bound artifacts and three green focused suites: 61 CAS
Core v8 tests, 82 CAS PCBA v8 tests, and 65 CAS-Ohm v1 tests. The combined
focused run comprises 208 test methods and 272 parameterized subtests. Those
receipts establish tested software behavior only. They do not establish a
complete CCDL language, empirical cognitive validity, physical materiality,
live calibration, safety effectiveness, regulatory or clinical suitability,
product readiness, canon admission, claim licensing, public-disclosure
authority, or peer review. Two adverse findings remain central: the published
formal EBNF does not cover the five-board reference corpus, with four direct
counterexamples; and the published CSB parameters clamp a stage at `0.1` before
a fuse threshold of `0.9`, making the stated crossing unreachable under the
declared clamp semantics. CAS PCBA 8 therefore treats the source CSB as a
known-fault fixture rather than evidence of a safety mechanism.

## 1. Research question and contribution boundary

The engineering question is not whether cognition *is* electronics. It is:

> Can a circuit-shaped modeling language make cognitive-system hypotheses more
> explicit, type-safe, replayable, and falsifiable without converting an
> analogy into a physical, causal, safety, or product claim?

The current candidate supports a qualified affirmative answer at the software
contract level. Its contributions are:

1. a typed board model separating semantic state, geometry, signal kind, unit,
   component contract, calibration metadata, and evidence provenance;
2. a deterministic design-rule checker (DRC) with fail-closed diagnostics;
3. a narrow trace-emitting reference simulator for declared deterministic
   component profiles;
4. a source- and profile-bound adapter from certified finite component tables to
   the TKS v8 finite reference kernel;
5. a source audit that preserves, rather than repairs silently, the incomplete
   CCDL grammar and the CSB threshold contradiction; and
6. an evidence discipline that distinguishes green software tests from
   experiments, measurement validation, safety evidence, and authority.

This paper introduces no successor canon and no new empirical result. It does
not modify the Gate 4 specifications, registries, or manifests. Every assertion
below is classified in
`WAVE1_ENGINEERING_CLAIM_ASSERTION_MATRIX_v0.1.json` and linked to exact evidence
in `WAVE1_ENGINEERING_EVIDENCE_MAP_v0.1.json`.

## 2. Versioned source basis

The immediate engineering baseline is the 743-page owner-supplied CAS PCBA
Engineer build, source ID `SRC-PCBA-ENGINEER-20260726`, SHA-256
`294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274`.
Its internal changelog label predates the supplied build. This paper therefore
uses the source ID and exact hash and does not invent a public semantic version.

The executable delta is bounded by the following repository sources:

| Boundary artifact | SHA-256 | Role |
|---|---|---|
| `CAS_CORE_V8_CANDIDATE_SPEC_v0.1.md` | `5FE6F91D005C7268D32C3943C2851138B30E2492C7D73877A04B30685CFCA1FC` | Semantic identity, evidence, and research-boundary kernel |
| `CAS_PCBA_V8_SOURCE_AUDIT_AND_SPEC_v0.1.md` | `19707B9213040A3B55DB51132C30B90A6004D15A611EC759906335F2E41450F0` | Normative Gate 4 engineering candidate |
| `PCBA_CCDL_CONSTRUCT_COVERAGE_v0.1.json` | `5BB797EC37CF289B4CBE8DF1256F07425C3DA13AA8CF2DA03E47DFCE1CB46808` | Grammar/corpus adverse evidence |
| `GATE4_REVIEW_MATRIX_v0.1.json` | `44DD99A847DA742C3EBEBC06D64452A6868421EE12129E789D1CC790DAE41B74` | Implemented/open decision ledger |
| `GATE4_ARTIFACT_MANIFEST_v0.1.json` | `49102F9BCBAA2345804F5EE3CA708FD6A84E83F8CF5ABB51E6612893A090D57B` | Exact artifacts and test-suite identities |
| TKS v8 core formal specification | `F740BA05AB7ADB2DCDF55E271016D127E45073B015497DE8982D44A49F0EA2C4` | Downstream finite-arrow boundary |
| Noetic Topos 2.0 specification | `156A5D8C5320F36E81E3B46473BA8A038B35672DCD28839A404D96A3DB1A763A` | Downstream ambient/resolved evidence boundary |

The Gate 5 preregistration specification is read-only downstream context. It
does not supply an experiment to this paper. At the bound commit it states that
Gate 5 is `OPEN / NOT_STARTED / Ring 4 / NOT LICENSED / HELD / NOT FROZEN` and
that no live, scientific, canon, product, license, or disclosure authority has
been created.

## 3. What “circuit” means here

CAS PCBA uses circuit engineering as a disciplined modeling grammar. It treats a
candidate cognitive pathway as a directed, typed network whose elements must
declare interfaces, allowed values, transfer behavior, statefulness, time
semantics, calibration references, and evidence limits. The abstraction can be
useful even when its subject is software or a model rather than hardware.

Three separations are load-bearing:

- **Model versus world:** a simulated transfer rule is behavior of the declared
  software profile, not evidence that a cognitive or physical system obeys it.
- **Design value versus measurement:** a locally supplied parameter or
  calibration label remains structural metadata until authenticated measurement
  evidence and uncertainty are supplied.
- **Analogy versus identity:** names borrowed from circuits do not make CAS
  quantities SI electrical quantities. Physical voltage, current, resistance,
  charge, flux, and power are outside the candidate unless a separately typed,
  instrumented physical profile is proposed and validated.

The literature supports this discipline at the level of method, not CAS
validity. VHDL demonstrates the engineering value of machine- and human-readable
formal hardware descriptions [E1]. Statecharts demonstrate the need to make
state, hierarchy, concurrency, and communication semantics explicit [E2].
Simulation verification and operational validation are distinct activities
[E8]. None of those sources validates the CAS ontology or its cognitive
interpretation.

## 4. Typed semantic and board model

### 4.1 Semantic identity

CAS Core v8 represents a semantic reference structurally as

```text
(namespace, local_id, version, source_id, definition_sha256).
```

TKS Foundations, TKS Worlds, CAS Drives, CAS Domains, CAS Registers, CAS States,
and Noetic Topos objects remain distinct namespaces. Historical or positional
relationships are typed as translations, alignments, or hypotheses; they are
not silently promoted to identities. This prevents a board adapter from making
a semantic theorem simply because two objects share a label or position.

### 4.2 State and geometry types

The PCBA candidate distinguishes:

```text
StateLiteral = Noetic × Domain × optional Drive × optional Register
NDCell       = Noetic × Domain
```

Projection from `StateLiteral` to `NDCell` forgets Drive and Register and is
therefore generally many-to-one. A `MixedSimplexAddress` is a strictly positive,
normalized profile over the 40 canonical `NDCell` values. It is neither a
one-hot state nor an element of the finite TKS kernel.

The mixed-simplex geometry retains a named Fisher-Rao profile. Information
geometry supplies the mathematical setting for probability-simplex metrics
[E10], but does not identify a learned model state with a CAS state. Projector
geometry is a separate optional profile with its own matrix, rank, basis/source,
tolerance, and validation residuals. The registered projector Gram-kernel result
does not establish latent cognitive capacity; the stronger CAS capacity transfer
retains a proof gap.

Formal Mathematics Paper 3 at commit
`3c8491db6f5559cf090909d9de0efa03d924f53f` (source-draft SHA-256
`679E1119CB084D9A429F6FCC26374B18FF1FB6252D7374631975B4FF56BAEFC4`)
is the sole mathematical authority for the projector theorem statements. The
engineering records are read-only dependency summaries. In particular, the
normalized Gram kernel requires common rank `d > 0`, and the CAS capacity
transfer remains `PROOF_GAP / IN_REVIEW / Ring 4` without the required isometry
and adjoint-intertwining certificate.

### 4.3 Board structure

A board contains immutable, identity-bearing records for:

- components and declared component kinds;
- typed ports, direction, signal kind, and unit;
- typed parameters and finite-state annotations;
- nets and endpoints;
- test points and calibration references;
- declared feedback loops;
- source and research-boundary metadata; and
- deterministic identity material.

Board identity includes the complete canonical structure. Exact value identity
is tagged so Boolean `true`, integer `1`, and string `"true"` cannot collide.
Arithmetic uses one immutable decimal context created from primitive constants;
the caller's ambient precision does not change declared results. IEEE 754 is a
useful external reference for explicit arithmetic formats and operation control
[E4], but the candidate's decimal profile remains its own software contract.

## 5. Design-rule checking

The DRC computes one deterministic diagnostic report. Errors fail a board;
warnings cannot become an implicit clean result. Its current checks cover the
following classes.

### 5.1 Structural integrity

The checker requires unique nonblank identities for components, ports, nets,
test points, calibrations, and feedback declarations. Component kinds and exact
parameter keys come from a closed catalog. Missing or unknown semantics fail
closed.

### 5.2 Typed connectivity

Every endpoint must resolve to a declared owner and port. Every net requires
exactly one typed driver. Driver and load signal kinds and units must agree under
a closed signal/unit table. Required inputs must connect or have an executable
default in the selected simulator profile. Unsupported signal/unit pairs,
multiple drivers, missing loads, and multiply connected ports receive distinct
diagnostics.

### 5.3 Calibration and probe integrity

Executable test points require versioned calibration references. The DRC checks
profile-digest shape, instrument and protocol identity fields, uncertainty,
measurement kind, and net-unit compatibility. A locally constructed calibration
record cannot make itself Evidence Packet eligible. Safety-marked paths require
explicitly marked probes, but the presence of a probe does not establish safety.

### 5.4 Feedback analysis

The checker builds a directed component graph, finds strongly connected
components, and evaluates declared cycles conservatively. The graph-algorithm
family is classical [E3]. The candidate additionally requires an exact feedback
declaration, a declared unit delay, an existing dimensionless calibration, and a
sub-unity gain bound for each realizable enumerated cycle. Unsupported or
resource-bounded analysis yields an unresolved-safety diagnostic rather than a
pass. Stateful, stochastic, and richer sequential semantics remain open.

### 5.5 Threshold reachability

For supported activation paths, the checker propagates conservative upper
bounds through causes, bias/gain stages, clipping, and cutoffs. A safety-critical
fuse whose threshold exceeds the resolved upstream bound receives
`UNREACHABLE_SAFETY_THRESHOLD`. An unresolved bound is not treated as reachable.

This check exposes the source CSB contradiction: an upstream saturation clamp of
`0.1` cannot cross a downstream threshold of `0.9` under the stated clamp
semantics. The candidate retains the unmodified parameters as a known-fault
fixture. A repaired board would be a new version requiring finite parameters,
explicit latch transitions, fuse truth tables, deterministic traces, hazard
analysis, and independent safety review.

## 6. Narrow deterministic simulation

Simulation is admitted only for supported component profiles with declared
ports, transfer rules, clipping, statefulness, and time semantics. The current
profile is intentionally narrow. It topologically orders the non-delay graph,
uses declared unit-delay behavior to break admitted feedback, and emits a
canonical trace.

Each result binds:

- board and component identities;
- DRC report identity;
- component catalog and decimal-context identities;
- simulator profile and source baseline;
- typed input samples and outputs;
- component events and tick linkage;
- test-point observations;
- measurement IDs, parent/child derivations, and calibration references; and
- the fixed Ring-4 research boundary.

Measurement/result construction rechecks child existence, derivation acyclicity,
tick linkage, units, measurement kinds, output/net agreement, and digest form.
This resembles the entity/activity/derivation separation in W3C PROV [E5], but
the current record format is a CAS-specific candidate, not a claim of PROV-O
conformance.

The correct interpretation of a green fixture is:

> The software performed the declared typed transition and produced the
> declared trace for the exact fixture under the exact profile.

It is not:

> The fixture proves a cognitive mechanism, a causal relation, a physical
> circuit law, a safe refusal mechanism, or a product capability.

## 7. TKS v8 and Noetic Topos 2 boundaries

Only a certified total, finite, deterministic, stateless, non-stochastic
component transition may be adapted to the TKS v8 `FiniteArrow` kernel. A typed
sequence can become a `SemigroupoidPath`; only an endomap has powers. The
adapter certificate binds the exact TKS kernel bytes, board, component,
transition table, tagged carrier, semantic profile, and research boundary.
Ambient module substitution is rejected.

This adapter proves, at most, type-correct representation in the finite
reference kernel. It does not prove that a PCBA component is a canonical TKS
operator or that its engineering labels have CAS semantic validity.

Continuous simplex profiles, local response curves, instrumented observations,
stateful devices, stochastic kernels, and memristive history variables remain
outside that finite deterministic arrow. They require distinct types and
comparison maps rather than coercion.

Noetic Topos 2 supplies an ambient-versus-resolved evidence distinction. Raw or
partially resolved records may be treated as external evidence associated with
the ambient construction, but a marked cover does not make a measurement true.
Restriction, gluing, calibration compatibility, and product-site comparison
remain separate obligations.

## 8. Source-audit results

### 8.1 CCDL grammar coverage

The consolidated EBNF admits only seven `circuit_item` alternatives and only
`layer_decl` or `via_decl` in a `board_block`. The published five-board corpus
uses additional forms. The exact audit records:

- four direct syntactic counterexamples;
- one bounded listing for which no direct syntax counterexample was established;
- no complete parser or semantic-conformance result; and
- a corpus-level conclusion that the formal EBNF does not cover the published
  five-board corpus.

Therefore the v0.1 implementation exposes a typed Python object model only. It
does not claim complete CCDL parsing. A successor grammar must publish exact
construct coverage, reject unsupported forms, and round-trip every admitted
board canonically.

### 8.2 CSB known-fault board

The source listing combines `sat=0.1`, a downstream fuse threshold of `0.9`, and
an infinite gain despite finite grammar/validator rules. No fail-closed latch
state machine is supplied. The DRC detects the reachability contradiction in a
bounded fixture. This is valuable negative evidence about the source and a
regression guard for the checker; it is not a validation of the board's safety
function.

### 8.3 Claim quarantine

The following remain hypotheses or prohibited product inferences:

- exact thought/transistor isomorphism;
- physical electrical identity for CAS quantities;
- semantic correctness from a response-region label;
- causal gain or hidden-cause identification from simulation or residuals;
- safety effectiveness, certification, regulatory compliance, or clinical use;
- complete compiler conformance;
- production readiness; and
- disclosure or license authority from a self-hash or generated receipt.

## 9. Bounded software evidence

The Gate 4 artifact manifest binds 54 files. Its suite identities are:

| Suite | Test methods | Test-ID SHA-256 |
|---|---:|---|
| CAS Core v8 | 61 | `E2AF5014DE28DD0702211EF32A2757B99B869A13FAFBB0B8D1B18A50A9F8FEF5` |
| CAS PCBA v8 | 82 | `D5F776C5F15758CD390470B5A542CCA110784DC5EBB9807B6BE41B2C80453470` |
| CAS-Ohm v1 | 65 | `2E81A685961286D944894A22EB93345B97211B4433B6C71EAF628D84CD8EB1EF` |

The integrated 2026-08-04 receipt reports all 208 exact test IDs passing, 272
combined parameterized subtests, 11 claim records all Ring 4 and `NOT LICENSED`,
53 review criteria with 20 open, four direct EBNF counterexamples, eight
CAS-Ohm source conflicts, and an integrated Gate 1 pass.

These numbers are historical, source-bound software receipts from the exact
Gate 4 manifest. They are not new experiments in this publication lane. The
repository-wide collector was not clean at the bound receipt: it reported four
pre-existing package/path namespace collisions after 1,200 collected items.
The focused suites therefore cannot support a repository-wide verification
claim.

## 10. Discussion

The strongest current result is architectural rather than empirical: a circuit
metaphor becomes safer and more useful when every analogy is forced through a
typed interface and every executable claim is bound to a profile, source,
calibration record, and trace. The framework makes several categories of error
observable earlier:

- scale and unit substitution;
- ambiguous semantic crosswalks;
- incomplete grammar claims;
- multiple-driver and unresolved-port defects;
- threshold paths that cannot activate;
- feedback loops without explicit delay or conservative gain evidence;
- fabricated or disconnected measurement lineage; and
- software receipts misrepresented as scientific or authority-bearing evidence.

That is a legitimate engineering contribution if its boundary remains clear.
Verification asks whether the software implements its declared candidate model;
validation asks whether that model is adequate for an intended external use
[E8]. The current work offers meaningful verification evidence and source
counterexamples. Operational validation is open.

## 11. Threats to validity and open obligations

### Construct validity

No experiment establishes that the selected CAS types correspond to cognitive
mechanisms or latent model structure. The circuit organization may help design
and audit hypotheses without being an ontology of cognition.

### Internal validity

The DRC and simulator have bounded regression suites, not a formal proof of all
paths. Property-based/random generation [E9], fuzz testing, independent
implementations, and a separately sourced mutation-testing campaign remain
open. E9 is not authority for mutation testing. The full CCDL parser does not
exist.

### External validity

There is no live calibrated model, physical board, instrument chain, held-out
replication, or multi-model evaluation in the admitted evidence. Cross-model and
cross-context generalization are open.

### Numerical validity

The fixed decimal profile controls candidate arithmetic, while the disclosed
binary64 Fisher-Rao implementation is a numerical pseudometric at its resolution.
Independent numerical audit and tolerance analysis remain open.

### Causal validity

Graph connectivity, gain composition, prediction, and residual localization do
not establish causation. Causal claims require an explicit causal model,
identification assumptions, and interventions [E11]. No such claim is admitted.

### Safety and governance

The CSB contradiction prevents a safety-effectiveness inference. Hazard analysis,
independent safety engineering, regulatory and clinical review, authenticated
claim authority, canon admission, disclosure approval, and product acceptance
are all open.

## 12. Dependency-ordered research program

The next defensible steps are:

1. specify a complete versioned CCDL grammar and a golden five-board corpus;
2. implement canonical parse/serialize round trips and fail-closed unsupported
   syntax;
3. define separate capacitor, PLL, memory, power, feedback, stochastic, and
   memristive state/time profiles;
4. create a property-based/random-generation campaign over DRC and simulation
   invariants [E9], and separately specify and source any mutation-testing
   campaign;
5. independently reproduce the exact source and test bundle in a hermetic
   toolchain;
6. preregister calibration and held-out validation through the Gate 5 control
   kernel, without promoting Gate 5 status;
7. require executor/auditor numerical agreement, falsifiers, negative outcomes,
   and independent replication;
8. complete internal cross-review against stable hashes; and
9. commission external formal, systems, experimental, safety, and claim-language
   review before any submission or use claim.

## 13. Conclusion

CAS PCBA 8 is presently viable as a private, Ring-4 adaptive-circuit engineering
research candidate. Its value is not that it proves cognition is electrical.
Its value is that it turns informal pathway diagrams into typed, inspectable,
versioned software objects and preserves negative evidence when the source or a
design cannot satisfy its own contract. The current code and tests support that
bounded engineering statement. Complete language conformance, stateful dynamics,
live calibration, empirical validity, physical materiality, safety, clinical or
regulatory use, product readiness, canon admission, licensing, disclosure, and
peer review remain explicitly open.

## References

Identifiers `[E1]`–`[E15]` resolve to complete metadata and exact URLs/DOIs in
`WAVE1_ENGINEERING_CITATION_LEDGER_v0.1.json`.

- [E1] IEEE Std 1076-2019, *VHDL Language Reference Manual*.
- [E2] D. Harel, “Statecharts: A Visual Formalism for Complex Systems,” 1987.
- [E3] R. Tarjan, “Depth-First Search and Linear Graph Algorithms,” 1972.
- [E4] IEEE Std 754-2019, *Floating-Point Arithmetic*.
- [E5] W3C, *PROV-O: The PROV Ontology*, 2013.
- [E8] R. G. Sargent, “Verification and Validation of Simulation Models,” 2013.
- [E9] K. Claessen and J. Hughes, “QuickCheck,” 2000.
- [E10] S.-i. Amari, *Information Geometry and Its Applications*, 2016.
- [E11] J. Pearl, *Causality*, second edition, 2009.

## Publication boundary

This draft is an internal research artifact. It is not a released specification,
peer-reviewed paper, Evidence Packet, safety case, regulatory submission,
clinical document, product claim, license decision, canon amendment, or public
disclosure authorization.
