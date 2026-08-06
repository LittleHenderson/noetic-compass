# Project Coherence Wave 2 Engineering Adversarial Review

**Status:** DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD

**Public disclosure authorized:** No

**Canon effect:** None

**Product-claim effect:** None

**Review verdict:** CONDITIONAL PASS AFTER 2 PUBLICATION BLOCKERS AND 4 STRENGTHENING CHANGES

## 1. Review binding

This review is bound to the Wave 1 engineering package at commit
c8635270ca6ba7c65504b4fda43cb42a89623015, based on parent
a1cd990109e7561dfd03949bf0e1653461c7ae44.

The reviewed non-self-hashing Wave 1 manifest is:

- path: docs/working/project_coherence/publication/wave1/engineering/WAVE1_ENGINEERING_ARTIFACT_MANIFEST_v0.1.json
- SHA-256: D1EE9BD0EB865FDC5522031375748BEE51DC8774531737F015EE0FF554D0E97B
- bytes: 5,251
- listed artifacts: 7

The governing formal dependency is Paper 3 in the Formal Mathematics lane:

- commit: 3c8491db6f5559cf090909d9de0efa03d924f53f
- path: docs/working/project_coherence/publication/wave1/formal_math/PAPER_3_NOETIC_PROJECTION_GEOMETRY_AND_STATE_CAPACITY_DELTA_v0.1.md
- SHA-256: 679E1119CB084D9A429F6FCC26374B18FF1FB6252D7374631975B4FF56BAEFC4
- bytes: 17,908

Paper 3 is reviewed here only as a cross-lane mathematical dependency. This
review does not edit or supersede either frozen Wave 1 lane.

## 2. Scope and method

The audit covered:

1. all 31 entries in the Wave 1 engineering claim/assertion matrix;
2. all 15 external references and their stated uses;
3. all seven manifest-listed engineering artifacts;
4. the bound CAS Core, CAS PCBA v8, and CAS-Ohm v1 source and test
   collections;
5. the four external PCBA/CAS-Ohm source bindings;
6. the eight recorded CAS-Ohm source conflicts;
7. the projector theorem transfer against Formal Mathematics Paper 3;
8. mathematical, engineering, type, interface, and counterexample boundaries;
9. every physical, empirical, causal, safety, clinical, regulatory, product,
   canon, license, and disclosure prohibition.

This was a source-bound adversarial review, not an experiment, external
specialist review, public release decision, or product acceptance exercise.

## 3. Verification result

The package has strong byte and test integrity within its declared boundary.

- All 7 Wave 1 package artifact hashes and byte counts matched.
- All 19 control-artifact hashes matched.
- All 43 source/test member hashes matched across six declared collections.
- All six collection aggregate hashes matched.
- All four external source bindings matched the recorded authority hashes.
- The unchanged Gate 4 runner passed in 121.1 seconds.
- Gate 4 exercised 208 test methods and 272 parameterized subtests:
  61 CAS Core methods, 82 CAS PCBA methods, and 65 CAS-Ohm methods.
- The runner reconfirmed 54 bound Gate 4 artifacts, 11 Ring 4 / NOT LICENSED
  claims, 53 criteria with 20 still open, four direct grammar counterexamples
  across the five-board corpus, all eight CAS-Ohm source conflicts, and the
  Gate 1 dependency.

The result does not close Gate 4 or Gate 5. The correct state remains
DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD / NOT FROZEN.

## 4. Claim review result

All 31 claim entries were reviewed individually:

- 26 are accepted within their existing bounded, open, negative, or
  not-licensed wording;
- 3 are accepted subject to wording-strengthening changes;
- 1 requires a mathematical correction before integrated publication;
- 1 remains correctly open but requires an exact cross-lane dependency binding
  before integrated publication.

No software test or source inspection justified widening a claim. No negative,
open, or prohibited inference may be promoted by the integrated editor.

## 5. Publication blockers

### B-ENG-001 — add the missing positive-rank hypothesis

The engineering claim entry THM-PROJECTOR-GRAM-KERNEL says “common
finite-rank orthogonal projectors.” Its normalized overlap divides by the
common rank. Rank zero is therefore not admissible: for zero projectors the
expression is tr(0)/0, which is undefined.

The governing theorem ledger and Formal Mathematics Paper 3 correctly require
common rank d > 0. The integrated claim statement must include that
hypothesis. This is a precise publication correction; it does not invalidate
the positive-rank result.

### B-ENG-002 — establish one theorem authority and bind it exactly

The engineering package repeats the projector Gram-kernel and capacity-transfer
identifiers as dependency summaries. The formal lane contains the governing
proofs, full hypotheses, and the decisive weakened-hypothesis counterexample.
Because the lanes were produced in parallel, the engineering evidence map does
not bind the exact Paper 3 commit and file digest.

Before integration:

1. Paper 3 must be designated the sole mathematical authority for both theorem
   identifiers;
2. the engineering entries must be explicitly read-only dependency records;
3. the integrated registry/evidence map must bind Paper 3 commit
   3c8491db6f5559cf090909d9de0efa03d924f53f and SHA-256
   679E1119CB084D9A429F6FCC26374B18FF1FB6252D7374631975B4FF56BAEFC4;
4. no engineering summary may omit or weaken Paper 3 hypotheses.

The capacity transfer remains PROOF_GAP / IN_REVIEW / Ring 4 for CAS. No
CAS-specific isometry/intertwining certificate has been supplied.

## 6. Required strengthening changes

### S-ENG-001 — distinguish exact pre-clipping Q4 input from clipped display

The implementation classifies the exact pre-clipping value
10 * raw / full_scale, which can exceed 10. The displayed Q10 value is
clipped at 10 while overload is retained separately. Therefore the exact
classifier domain is nonnegative and Q4 is [7.5, infinity), not merely
[7.5, 10]. Alternatively, prose may explicitly say that the shown bins
describe the clipped display while classification uses the pre-clipping
identity. Boundary classifications are tested and remain unchanged.

### S-ENG-002 — correct the SI-unit ontology sentence

CAS-Ohm UnitKind contains ALPHA, ACTIVATION, Q10, Q100,
ALPHA_PER_ACTIVATION, DIMENSIONLESS, and FRACTION. It does not contain physical
SI quantities. Replace the sentence saying the current ontology includes “any
separately declared physical SI quantity” with: physical SI quantities are
outside this ontology and would require a separate explicitly typed,
instrumented physical profile.

The broader nonphysical boundary is otherwise maintained. The generic PCBA
Unit vocabulary does include VOLT; that fact permits typed generic board
data and does not license interpreting CAS quantities as physical telemetry.

### S-ENG-003 — qualify “nonstale” as replay-time-current

Calibration validity is evaluated against a caller-supplied replay_as_of.
The candidate has no admitted trusted current-time authority and
authenticated_current is always false. Wherever “active,” “current,” or
“nonstale” could imply live freshness, say “replay-time-current, not
authenticated-current.”

### S-ENG-004 — narrow the QuickCheck citation

Reference E9 supports property-oriented randomized test generation. It does not
support the separate request for a mutation-testing campaign. Cite E9 only for
property-based/random generation, avoid relying on it for mutation testing,
and either add an appropriate primary mutation-testing source or leave that
method uncited as an open engineering obligation. Do not overstate shrinking
beyond what the cited source directly establishes.

## 7. Cross-lane and boundary findings

### Projector geometry

The engineering package correctly treats projector geometry as optional and
type-distinct from the canonical mixed-simplex Fisher-Rao profile. Paper 3
retains the simplex baseline, proves the positive-rank Gram-kernel result, and
requires a specific isometry plus adjoint intertwining identity for capacity
transfer. The counterexample with D = d = 1, two orthogonal code vectors,
and both projectors equal to the identity shows that the transfer is false if
the intertwining premise is omitted.

### PCBA versus CAS-Ohm

The distinction is preserved:

- CAS PCBA v8 is a typed modeling grammar, board representation, deterministic
  DRC, narrow simulator, and certified finite adapter.
- CAS-Ohm v1 is a nonphysical, profile-specific response/calibration model.
- No rule coerces PCBA board parameters into live CAS-Ohm measurements.
- A PCBA vocabulary member named VOLT is not evidence that any CAS quantity
  is physical voltage.

### Electrical metaphor boundary

The drafts consistently prohibit interpreting drive, activation, effective
resistance, gain, charge, flux, or power metaphors as physical electrical
telemetry. The physical-telemetry claim is explicitly contradicted and not
licensed. References to electrical circuit and memristor theory are analogical
or methodological only.

### Memristive status

The bound source and tests contain no memristor, hysteresis, charge-state, or
flux-state implementation. The paper’s history-state equations are provisional
and nonphysical. There is no device, material, calibrated state law, hysteresis
result, or physical mapping. MEM-OPEN-001 is correctly open and
not implemented.

### PCBA known limits

The formal CCDL grammar fails the published corpus via four direct syntax
counterexamples across five boards. The CSB fixture retains an unreachable
threshold because the red-stage clamp is 0.1 and the downstream fuse threshold
is 0.9; the source also retains non-finite gain and incomplete latch/fail-closed
semantics. Stateful, stochastic, adaptive, memory, richer feedback, and
memristive semantics remain open.

### CAS-Ohm inferential limits

The local response relation is profile-specific. Same-sample
r = alpha / activation is circular and cannot be used as a predictor.
Series, parallel, gain composition, redundancy, and residual diagnostics are
structural research operations only. Residual sign does not identify a hidden
cause. All five empirical claims lack preregistration, Evidence Packets, and
held-out results, so they remain open and not licensed.

## 8. Final disposition

The Wave 1 engineering package is viable for continued internal integration.
Its strongest feature is disciplined claim quarantine: software evidence is
not promoted into empirical, causal, physical, safety, clinical, regulatory,
product, or canonical truth.

Integrated publication is blocked until B-ENG-001 and B-ENG-002 are resolved.
S-ENG-001 through S-ENG-004 are required strengthening changes before editorial
freeze. All remaining experiments, external validation, independent review,
product acceptance, canon migration, licensing, and disclosure decisions stay
OPEN.
