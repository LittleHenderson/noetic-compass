# CAS PCBA 8: Adaptive Cognitive Circuit Engineering with Typed, Fail-Closed Design Rules

**White paper, version 0.1 — 2026-08-07**

**Artifact status:** `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`

**Source basis:**
- Engineering baseline: `CAS_PCBA_Engineer.pdf`, 743 pp., source ID
  `SRC-PCBA-ENGINEER-20260726`, SHA-256
  `294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274`
- `CAS_PCBA_V8_SOURCE_AUDIT_AND_SPEC_v0.1.md` (SHA-256
  `19707B9213040A3B55DB51132C30B90A6004D15A611EC759906335F2E41450F0`)
- `PCBA_CCDL_CONSTRUCT_COVERAGE_v0.1.json` (SHA-256
  `5BB797EC37CF289B4CBE8DF1256F07425C3DA13AA8CF2DA03E47DFCE1CB46808`)
- Publication delta: `CAS_PCBA_8_ADAPTIVE_COGNITIVE_CIRCUIT_ENGINEERING_DRAFT_v0.1.md`
  (Project Coherence charter Paper 6, base commit
  `a1cd990109e7561dfd03949bf0e1653461c7ae44`)
- Implementation: `src/cas_pcba_v8/` (model, types, values, DRC, simulation,
  geometry, TKS adapter, diagnostics, integrity, fixtures)

**Authorship / review:** `OPEN / INTERNAL CROSS-REVIEW OPEN / EXTERNAL SPECIALIST REVIEW OPEN`

---

## Abstract

CAS PCBA 8 is a typed, provenance-bearing research architecture for describing
and checking circuit-shaped cognitive-system models. "Circuit" names an
engineering organization — typed components, ports, nets, state annotations,
calibration references, deterministic traces — and does not assert a physical
electrical implementation or identify model quantities with voltage, current,
or resistance. The research question is whether a circuit-shaped modeling
language can make cognitive-system hypotheses more explicit, type-safe,
replayable, and falsifiable *without* converting an analogy into a physical,
causal, safety, or product claim. The candidate supports a qualified
affirmative at the software-contract level: semantic identities remain typed;
board structure is canonicalized; a deterministic design-rule checker rejects
incompatible signal/unit pairs, unresolved ports, unsafe feedback
declarations, missing calibrated probes, and unreachable fuse thresholds;
supported simulations emit deterministic provenance-rich traces; and only
certified finite, deterministic, stateless transitions may cross the TKS v8
adapter boundary.

Two adverse source findings are preserved rather than silently repaired. The
published formal CCDL grammar does not cover the book's own five-board
reference corpus (four direct syntactic counterexamples). And the published
Cognitive Safety Board clamps a red stage at `sat = 0.1` upstream of a fuse
threshold of `0.9`, making the stated crossing unreachable under the declared
clamp semantics; the unmodified board is retained as a known-fault fixture. At
the bound Gate 4 receipt, 82 CAS PCBA v8 test methods pass within an
integrated 208-method three-suite run. These receipts establish tested
software behavior only — not language completeness, empirical cognitive
validity, physical materiality, safety effectiveness, or product readiness.

---

## 1. What "circuit" means here

CAS PCBA treats a candidate cognitive pathway as a directed, typed network
whose elements must declare interfaces, allowed values, transfer behavior,
statefulness, time semantics, calibration references, and evidence limits.
Three separations are load-bearing:

- **Model versus world.** A simulated transfer rule is behavior of the
  declared software profile, not evidence that a cognitive or physical system
  obeys it.
- **Design value versus measurement.** A locally supplied parameter or
  calibration label remains structural metadata until authenticated
  measurement evidence and uncertainty are supplied.
- **Analogy versus identity.** Borrowed circuit names do not make CAS
  quantities SI electrical quantities.

The engineering literature supports this discipline at the level of method,
not CAS validity: VHDL for machine-readable hardware description [E1],
Statecharts for explicit state/hierarchy/concurrency semantics [E2], and the
verification-versus-validation distinction for simulation models [E8].

## 2. Typed semantic and board model

### 2.1 State types

Building on the CAS Core 8 semantic-identity kernel, the candidate keeps
distinct:

```text
StateLiteral = Noetic × Domain × optional Drive × optional Register
NDCell       = Noetic × Domain
SimplexAddress40 = strictly positive normalized profile over the 40 NDCells
```

Projection `StateLiteral -> NDCell` forgets Drive and Register and is
explicitly many-to-one — not an isomorphism. A simplex address is neither a
one-hot cell nor an element of the finite TKS kernel. The mixed-simplex
geometry retains a named Fisher-Rao profile; the disclosed binary64
implementation is a numerical pseudometric at its resolution, not a proof that
all distinct profiles are separated. Projector geometry is a separate optional
research profile that caps and versions its tolerance, records validation
residuals, and binds matrix, basis/source, dimension, rank, and tolerance in
one digest.

### 2.2 Values and arithmetic

Finite carrier values use tagged exact type-plus-value identity, so integer
`1`, Boolean `true`, and string `"true"` are distinct throughout DRC,
execution, traces, and adapters. All decimal operations run under one
immutable, versioned context created from primitive constants; ambient caller
precision is irrelevant, and the context identity enters reports and results.

### 2.3 Board structure

A board contains immutable, identity-bearing records for components and kinds;
typed ports (direction, signal kind, unit); typed parameters and finite-state
annotations; nets and endpoints; test points and calibration references;
declared feedback loops; and source/research-boundary metadata. Board identity
includes the complete canonical structure.

## 3. The design-rule checker

The DRC computes one deterministic diagnostic report under a closed `PCBA8-*`
catalog. Errors fail the board; warnings never become an implicit clean
result. Checks cover five classes:

1. **Structural integrity** — unique nonblank identities; closed component
   kinds and exact parameter keys; missing or unknown semantics fail closed.
2. **Typed connectivity** — every endpoint resolves; exactly one typed driver
   per net; driver/load signal kinds and units agree under a closed
   admissibility table; required inputs connect or have an executable default
   in the selected simulator profile.
3. **Calibration and probe integrity** — executable test points require
   versioned calibration references with profile-digest shape, instrument and
   protocol identity, uncertainty, measurement kind, and net-unit
   compatibility; a locally constructed calibration record cannot make itself
   Evidence Packet eligible; safety-marked paths require marked probes, but a
   probe's presence does not establish safety.
4. **Feedback analysis** — a directed component graph with strongly connected
   components (classical algorithms [E3]); each realizable declared cycle
   needs an exact feedback declaration, declared unit delay, existing
   dimensionless calibration, and a conservative sub-unity gain bound;
   unsupported or resource-bounded analysis yields an unresolved-safety
   diagnostic, never a pass.
5. **Threshold reachability** — conservative upper bounds propagate through
   causes, bias/gain stages, clipping, and cutoffs; a safety-critical fuse
   whose threshold exceeds the resolved upstream bound receives
   `UNREACHABLE_SAFETY_THRESHOLD`; an unresolved bound is not treated as
   reachable.

## 4. Adverse source findings

### 4.1 CCDL grammar coverage

Appendix C's formal `board_block` admits only a small subset of the constructs
used by the five published Appendix D / reference boards, which additionally
use I/O, CJT, component, rail, dial, `use`, monitor, event, verification, and
other forms listed in prose but absent from the EBNF. Pinpoint evidence: the
book reserves additional Part IV statement leaders at PDF page 578, calls
missing appendix forms errata at PDF pages 591–592, yet the consolidated EBNF
at PDF pages 598–599 still limits `circuit_item` to seven alternatives and a
`board_block` body to `layer_decl` or `via_decl`. The machine-readable
coverage record documents four direct syntax counterexamples and one bounded
listing without an established counterexample; the corpus-level conformance
claim therefore fails without overstating the result for any individual board.

Candidate rule: v0.1 declares only its programmatic Python model and does not
claim to parse the complete CCDL book language. Any later grammar must publish
an exact construct-coverage matrix, reject unsupported forms, and round-trip
every admitted board canonically.

### 4.2 The CSB known-fault fixture

The Cognitive Safety Board listing clamps its red stage at `sat = 0.1` while
the downstream fuse threshold is `0.9`; under the stated clamp semantics the
fuse cannot trip. The same listing uses non-finite `beta = infinity` despite
finite grammar/validator rules, and the book defines no fail-closed latch
state machine showing that an open fuse preserves rather than suppresses the
refusal path. Evidence: red-stage and fuse values at PDF page 342, repeated at
PDF page 608; the Appendix D note at PDF page 610 replaces the infinite gain
with "a large finite value" but retains the clamp and does not reconcile it
with the threshold.

The unmodified parameters are retained as a known-fault fixture that the DRC
must flag. Any repair is a separately versioned design requiring threshold
reachability, finite parameters, latch state transitions, fuse truth tables,
deterministic traces, hazard analysis, and independent safety review. This is
valuable negative evidence about the source and a regression guard for the
checker — not a validation of the board's safety function.

### 4.3 Claim quarantine

The following remain hypotheses or prohibited product inferences: exact
thought/transistor isomorphism; shared four-region identity; overload-induced
semantic involution; Fisher-Rao causal gain; physical electrical identity for
CAS quantities; semantic correctness from a response-region label; safety
effectiveness, certification, regulatory or clinical use; complete compiler
conformance; production readiness; and disclosure or license authority from a
self-hash or generated receipt.

## 5. Narrow deterministic simulation

Simulation is admitted only for supported component profiles with declared
ports, transfer rules, clipping, statefulness, and time semantics. The current
profile topologically orders the non-delay graph, uses declared unit-delay
behavior to break admitted feedback, and emits a canonical trace binding board
and component identities, the exact DRC report, component catalog and
decimal-context identities, simulator profile and source baseline, typed
inputs/outputs, component events and tick linkage, test-point observations,
measurement IDs with parent/child derivations, and the fixed Ring-4 boundary.
Measurement construction rechecks child existence, derivation acyclicity, tick
linkage, units, measurement kinds, and digest form — a discipline that
resembles the entity/activity/derivation separation of W3C PROV [E5] without
claiming PROV-O conformance.

The correct reading of a green fixture is: *the software performed the
declared typed transition and produced the declared trace for the exact
fixture under the exact profile* — never that the fixture proves a cognitive
mechanism, causal relation, physical law, safe refusal, or product capability.

## 6. TKS v8 and Noetic Topos 2 boundaries

Only a certified total, finite, deterministic, stateless, non-stochastic
component transition may be adapted to a TKS v8 `FiniteArrow`. Chains become
`SemigroupoidPath` values; only an endomap has powers. The adapter certificate
binds the exact TKS kernel bytes, board, component, transition table, tagged
carrier, semantic profile, and research boundary; ambient module substitution
is rejected. The adapter proves at most type-correct representation in the
finite reference kernel — it carries no automatic CAS semantic theorem.
Continuous simplex profiles, response curves, instrumented observations,
stateful devices, stochastic kernels, and memristive history variables remain
outside the finite arrow and require distinct types and comparison maps.

From Noetic Topos 2.0 the candidate inherits the ambient-versus-resolved
evidence distinction: raw or partially resolved records may be treated as
external evidence associated with the ambient construction, but a marked cover
does not make a measurement true, and records do not enter resolved semantics
until restriction and gluing under one calibration profile are defined and
tested.

## 7. Bounded software evidence

At the bound commit, the integrated Gate 4 receipt records 54 hash-bound
artifacts and three green focused suites:

| Suite | Test methods | Test-ID SHA-256 |
|---|---:|---|
| CAS Core v8 | 61 | `E2AF5014DE28DD0702211EF32A2757B99B869A13FAFBB0B8D1B18A50A9F8FEF5` |
| CAS PCBA v8 | 82 | `D5F776C5F15758CD390470B5A542CCA110784DC5EBB9807B6BE41B2C80453470` |
| CAS-Ohm v1 | 65 | `2E81A685961286D944894A22EB93345B97211B4433B6C71EAF628D84CD8EB1EF` |

The combined run comprises 208 test methods and 272 parameterized subtests,
with 11 claim records all Ring 4 / `NOT LICENSED`, 53 review criteria (20
open), four direct EBNF counterexamples, and eight CAS-Ohm source conflicts.
The repository-wide collector was not clean at the bound receipt (four
pre-existing package/path namespace collisions after 1,200 collected items),
so the focused suites cannot support a repository-wide verification claim.

## 8. Threats to validity

- **Construct:** no experiment establishes that the selected CAS types
  correspond to cognitive mechanisms or latent model structure.
- **Internal:** bounded regression suites, not proofs of all paths;
  property-based and fuzz campaigns [E9], independent implementations, and a
  separately sourced mutation-testing campaign remain open; the full CCDL
  parser does not exist.
- **External:** no live calibrated model, physical board, instrument chain,
  held-out replication, or multi-model evaluation is in the admitted evidence.
- **Numerical:** independent audit of the decimal profile and the binary64
  Fisher-Rao pseudometric remains open.
- **Causal:** connectivity, gain composition, prediction, and residuals do not
  establish causation; causal claims require explicit models, identification
  assumptions, and interventions [E11]. None is admitted.
- **Safety and governance:** the CSB contradiction blocks any
  safety-effectiveness inference; hazard analysis, independent safety
  engineering, regulatory/clinical review, authenticated claim authority,
  canon admission, disclosure approval, and product acceptance are all open.

## 9. Dependency-ordered research program

1. Specify a complete versioned CCDL grammar and a golden five-board corpus.
2. Implement canonical parse/serialize round trips; fail closed on
   unsupported syntax.
3. Define separate capacitor, PLL, memory, power, feedback, stochastic, and
   memristive state/time profiles.
4. Run a property-based/random-generation campaign over DRC and simulation
   invariants [E9]; separately specify any mutation-testing campaign.
5. Reproduce the exact source and test bundle in a hermetic toolchain.
6. Preregister calibration and held-out validation through the Gate 5 control
   kernel without promoting Gate 5 status.
7. Require executor/auditor numerical agreement, falsifiers, negative
   outcomes, and independent replication.
8. Complete internal cross-review against stable hashes; then commission
   external formal, systems, experimental, safety, and claim-language review.

## 10. Conclusion

CAS PCBA 8's value is not that it proves cognition is electrical — it does not
and cannot at this stage. Its value is that it turns informal pathway diagrams
into typed, inspectable, versioned software objects and *preserves negative
evidence* when a source or design cannot satisfy its own contract: a grammar
that does not cover its own corpus, and a safety board whose fuse cannot trip,
are recorded as first-class findings with page-anchored evidence rather than
patched away. The strongest current result is architectural: every analogy is
forced through a typed interface, and every executable claim is bound to a
profile, source, calibration record, and trace.

## References

Identifiers `[E1]`–`[E15]` resolve to complete metadata in
`WAVE1_ENGINEERING_CITATION_LEDGER_v0.1.json`.

- [E1] IEEE Std 1076-2019, *VHDL Language Reference Manual*.
- [E2] D. Harel, "Statecharts: A Visual Formalism for Complex Systems," 1987.
- [E3] R. Tarjan, "Depth-First Search and Linear Graph Algorithms," 1972.
- [E4] IEEE Std 754-2019, *Floating-Point Arithmetic*.
- [E5] W3C, *PROV-O: The PROV Ontology*, 2013.
- [E8] R. G. Sargent, "Verification and Validation of Simulation Models," 2013.
- [E9] K. Claessen and J. Hughes, "QuickCheck," 2000.
- [E10] S.-i. Amari, *Information Geometry and Its Applications*, 2016.
- [E11] J. Pearl, *Causality*, 2nd ed., 2009.

---

**Publication boundary.** This white paper is an internal research artifact,
not a released specification, peer-reviewed paper, Evidence Packet, safety
case, regulatory submission, clinical document, product claim, license
decision, canon amendment, or public disclosure authorization. New matter
relative to USPTO provisional 64/037,173 requires its own filing or inclusion
in the utility conversion.
