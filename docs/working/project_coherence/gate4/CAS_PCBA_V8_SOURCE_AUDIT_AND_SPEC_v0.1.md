# CAS PCBA v8 source audit and candidate specification v0.1

**Status:** `OPEN / RING 4 / NOT LICENSED / HELD`

## 1. Baseline and identification

The engineering baseline is the 743-page `CAS_PCBA_Engineer.pdf`, identified by
SHA-256
`294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274`.
Its latest internal changelog label predates the supplied 2026-07-26 build, so
this candidate uses `PCBA-ENG-20260726` plus the exact hash and does not invent a
public semantic version.

The book is an engineering reference. Its own disclaimer, the Phase 0 authority
matrix, and this candidate all deny safety certification and physical telemetry.

## 2. Adverse source findings

### 2.1 Grammar and implementation coverage

Appendix C's formal `board_block` admits only a small subset of the constructs
used by the five Appendix D/reference boards. Published boards additionally use
I/O, CJT, component, rail, dial, `use`, monitor, event, verification, and other
forms listed in prose but absent from the EBNF. Available research parsers and
linters cover reduced subsets and cannot establish full compiler conformance.

Pinpoint evidence: the book reserves the additional Part IV statement leaders
at PDF page 578 (book page 562), describes selected extra forms and calls missing
appendix forms errata at PDF pages 591-592 (book pages 575-576), but the
consolidated structural EBNF at PDF pages 598-599 (book pages 582-583) still
limits `circuit_item` to seven alternatives and a `board_block` body to only
`layer_decl` or `via_decl`. The five reference listings appear at PDF pages
606-608, 613-614, 618-619, 623-624, and 628-632. The machine-readable
`PCBA_CCDL_CONSTRUCT_COVERAGE_v0.1.json` records four direct syntax
counterexamples and one bounded listing for which no direct syntax
counterexample was established. The corpus-level conformance claim therefore
fails without overstating the result for every individual board.

Candidate rule: the v0.1 implementation declares only its programmatic Python
model. It does not claim to parse the complete CCDL book language. Any later
grammar must publish an exact construct-coverage matrix, reject unsupported
forms, and round-trip every admitted board canonically.

### 2.2 CSB counterexample

The CSB red stage is clamped at `sat=0.1`, while the downstream fuse threshold is
`0.9`; under the stated clamp semantics, the fuse cannot trip. The same listing
uses non-finite `beta=infinity`, despite finite grammar/validator rules.
Saturation is a plateau, not a latch, and the book does not define a fail-closed
state machine showing that an open fuse preserves rather than suppresses the
refusal path.

Candidate rule: the unmodified CSB parameters are a known-fault fixture. Any
repair is a separately versioned design and needs threshold reachability, finite
parameters, latch state transitions, fuse truth tables, deterministic traces,
and independent safety review.

Pinpoint evidence: the Chapter 18 listing gives the red-stage and fuse values at
PDF page 342 (book page 326); Appendix D repeats them at PDF page 608 (book page
592). The Appendix D note at PDF page 610 (book page 594) says the infinite gain
is an idealization rejected by validators and directs the implementer to a large
finite value, while retaining the `sat=0.1` clamp. That note does not reconcile
the clamp with the `threshold=0.9` fuse.

### 2.3 Claim boundary

Claims of exact thought/transistor isomorphism, shared four-region identity,
overload-induced semantic involution, Fisher-Rao causal gain, certification,
regulatory sign-off, clinical use, and safety effectiveness remain hypotheses or
analogies. Historical AI-authored/self-hashed licensing receipts are not an
authenticated reviewer or legal authority.

## 3. Candidate type system

The programmatic v0.1 core keeps these types separate:

- `StateLiteral = Noetic x Domain x optional Drive x optional Register`;
- `NDCell = Noetic x Domain`;
- `SimplexAddress40`, a strictly positive normalized profile over 40 `NDCell`
  values, not a one-hot cell or TKS object element;
- port direction, signal kind, and unit;
- component kind and typed parameter contract;
- net endpoints and driver/consumer rules;
- test-point and calibration-profile references;
- deterministic trace event and child measurement identity; and
- research boundary and source provenance.

All decimal operations run under one immutable, versioned context created from
primitive constants for each operation; ambient caller precision is irrelevant
and the context identity enters reports and results. Finite carrier values use a
tagged exact type-plus-value identity, so integer `1`, Boolean `true`, and string
`"true"` are distinct throughout DRC, execution, traces, and adapters. Public
operations derive and recheck the fixed research boundary rather than trusting a
shared mutable object or a recomputable self-hash.

Projection from `StateLiteral` to `NDCell` is explicitly many-to-one and forgets
Drive/Register. It is not an isomorphism.

## 4. DRC contract

The candidate DRC uses one deterministic `PCBA8-*` diagnostic catalog. Errors
fail the board; warnings never become an implicit clean result. At minimum it
checks:

- unique nonblank component, port, net, and test-point identities;
- declared component kinds and exact parameter keys;
- port existence, direction, signal, and unit compatibility under a closed
  admissible signal-kind/unit table;
- required ports, driver count, unresolved names, and every unconnected input
  that lacks an executable default in the selected simulator profile;
- declared Cause/Bias/Effect state admissibility and bias-domain coherence;
- finite parameter values, threshold reachability through every cause/bias/gain/
  cutoff/clipping stage, and declared zero policies;
- feedback direction, per-realizable-cycle conservative gain bounds, explicit
  low-gain exceptions, and unsupported stateful or stochastic loops;
- safety-critical paths with test points and calibration references; and
- simulation/trace requirements for any executable claim.

## 5. Reference simulation

Reference simulation is deterministic and intentionally narrow. A supported
component must declare its transfer profile, units, clipping, statefulness, and
time semantics. Every run emits a canonical trace containing source identities,
input/output quantities, component events, diagnostics, test-point observations,
child measurement IDs, and final status. The result binds the exact DRC report,
engine/simulator profile, component catalog, decimal context, source baseline,
and implementation identities. Public measurement/result construction validates
digest form, unique IDs, child existence and acyclicity, tick/trace linkage, and
measurement-kind eligibility. Locally asserted calibration metadata is
structural/test-only and cannot create authenticated Evidence Packet eligibility.
Unsupported behavior fails closed.

Simulation validates the implementation against declared fixtures. It does not
establish that a cognitive or model system follows the simulated law.

## 6. Geometry and TKS v8 boundary

The mixed-simplex/Fisher-Rao baseline is preserved. Projector geometry is an
optional named research profile, not a replacement. Continuous simplex values,
analog/stateful components, and stochastic kernels are not encoded as finite
deterministic TKS arrows.

The binary64 Fisher-Rao implementation is a disclosed numerical pseudometric at
its resolution, not a proof that all distinct profiles are separated. Projector
profiles cap and version their tolerance, record validation residuals, and bind
the canonical matrix, basis/source, dimension, rank, and tolerance in one digest.

Only a certified finite deterministic component transition can be adapted to a
`FiniteArrow`; chains become `SemigroupoidPath`, and feedback powers require a
certified `Endomap`. The adapter returns an immutable certificate binding the
exact TKS kernel/profile, PCBA board/component/transition identities, tagged
carrier, semantic profile, and fixed boundary. Ambient module substitution is
rejected. The adapter carries no automatic CAS semantic theorem.

## 7. Explicitly open obligations

- Complete CCDL grammar and all five faithful board implementations.
- Stateful capacitor/PLL/memory/power semantics and time integration.
- Live calibration, uncertainty, environmental validity, and drift.
- Property/fuzz testing beyond the bounded known-fault suite.
- Independent systems, safety, regulatory, clinical, and formal review.
