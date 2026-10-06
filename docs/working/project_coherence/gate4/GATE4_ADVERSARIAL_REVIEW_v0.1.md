# Gate 4 adversarial review v0.1

**Status:** `DRAFT / OPEN / RING 4 / NOT LICENSED / HELD / NOT FROZEN`

## Decision

**KEEP GATE 4 OPEN.** The candidate packages are isolated research software.
Passing their bounded regression suites establishes only the behavior covered by
those suites against the hash-bound fixtures. It does not admit a semantic
canon, validate a cognitive or physical model, license a product claim,
establish safety or regulatory readiness, complete peer review, or authorize
public disclosure.

## Review method

The review used four deliberately separate evidence classes:

1. exact source identities and pinpoint source inspection;
2. implementation and fixture construction;
3. nominal regression suites; and
4. independent adversarial review using counterexamples not supplied by the
   implementer.

An implementation defect is recorded as repaired only when its counterexample
is retained as a regression test. A source conflict is never silently repaired
in the historical source; it is quarantined and assigned a candidate rule. A
self-hash is treated as an integrity check, never as reviewer, legal, or claim
authority.

## Source-level adverse evidence

### CAS PCBA

The exact 743-page engineering PDF was inspected at the grammar, reference-board,
CSB, and Fisher-Rao locations listed in
`CAS_PCBA_V8_SOURCE_AUDIT_AND_SPEC_v0.1.md`. The machine-readable coverage audit
records five reference boards. Four contain direct counterexamples to the
published formal EBNF; the bounded COB review established no direct syntax
counterexample. The defensible corpus-level result is therefore that the formal
EBNF does not cover the published five-board corpus, not that every individual
board was proved unparsable.

The CSB listing also clamps its red stage at `0.1` while giving the downstream
fuse a threshold of `0.9`. The source's later instruction to replace infinite
gain with a large finite value does not reconcile that reachability failure.
The unmodified listing is retained as a known-fault fixture, not promoted as a
safety mechanism.

### CAS-Ohm

The exact Guide PDF, operationalization addendum, PCBA Appendix I, and PCBA
engineering PDF were compared. Eight conflicts or under-specifications are
bound in `CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json`, including incompatible
numeric scales, incompatible full-scale methods, a missing dimensional bridge,
distinct gain definitions, ASOM mnemonic overload, unvalidated network rules,
causal overinterpretation of residuals, and under-specified Q4 precision.

The PDF pages were rendered and visually inspected. Appendix I was read from its
exact UTF-8 source. The addendum was inspected structurally by OOXML paragraph
and table position after both available rendering routes failed; this review
therefore makes no page-number assertion for that DOCX.

## CAS Core v8 audit chronology

The first implementation correctly separated namespaces, raw/LF byte identity,
registry snapshots, legacy compilation, typed finite-arrow composition, action
intent, and the Ring-4 boundary. Its nominal tests did not expose the following
adversarial failures:

- semantic rendered IDs omitted source/hash fields;
- the legacy compiler could observe ambient Python modules outside its declared
  dependency closure;
- a caller could publicly construct and re-hash a receipt whose nonclaim/action
  semantics were insufficiently typed;
- public registry constructors bypassed loader validation;
- registry schema bytes were not pinned;
- generic canonicalization collapsed enum/scalar and tuple/list distinctions;
  and
- unsafe Unicode control/format text was accepted into review-visible IDs.

The repair requirement is a content-addressed isolated compiler worker, a
type-injective canonical form, schema-bound validated registry snapshots,
structurally typed action/assessment/authorization records, complete semantic
IDs, and consistent unsafe-Unicode rejection. Even after bounded regression,
OS/toolchain hermeticity, Python/Rust conformance, semantic migration, and an
authenticated claim-authority trust root remain open.

A second independent review of the 47-test hardened candidate found four
additional invariant classes before admission:

- process-local sentinel objects were described as issuance provenance even
  though Python-local object identity is not authentication;
- directly constructed registry views could preserve an original raw identity
  while substituting parsed header, record, or schema content;
- the frozen compiler-policy comparison dispatched caller-defined equality; and
- Ring-4 boundary and semantic-identity checks dispatched caller-defined
  equality, allowing typed subclasses to misrepresent primitive fields.

These findings require replay-based structural verification, exact-type plus
primitive-field comparison, and raw-byte-backed registry reconstruction. They
do not create an authorization path: the independently reviewed decision API
continued to return `authorization_granted=false` and `allowed=false`. They do
invalidate any stronger claim that Python-local sentinels or parsed self-hashes
authenticate origin.

The second repair removed the sentinels and public policy override, added fresh
compiler replay at assessment and decision time, reconstructed registry views
from exact retained bytes, enforced exact-type/primitive comparisons, and added
bounded canonicalization and ASCII machine-identifier rules. Independent
confirmation closed the four findings across 56 tests and found one minor raw
error-type edge for integers beyond Python's conversion limit. The final repair
added an explicit 2,048-bit integer limit and normalized residual conversion
errors; the post-repair Core suite was 57 tests.

The first integrated Gate 4 replay then exposed an intermittent transport
failure: a fresh compiler worker exited with an empty response. A controlled
pre-fix stress run of 96 raw workers at concurrency 16 reproduced 95 canonical
successes and one `returncode=1` with zero stdout and stderr bytes. This proves a
startup/transport failure under launch pressure, not its Windows-internal root
cause. The repair does not retry. It serializes cooperating worker processes
through an advisory lock; profile-binds the lock path, 90-second acquisition
bound, 10-millisecond poll, and 10-millisecond post-release yield; and records
only exit code, stream byte counts, and stream hashes on failure. The advisory
lock makes no fairness claim.

A later combined replay still found nondeterministic dependency profiles. The
variable surface was the Windows `platform.uname()` probe: WMI success and its
fallback path can load different module graphs while returning the same runtime
labels. The corrected worker does not use WMI or subprocess probing. It derives
runtime labels from already-bound interpreter fields, `sys.platform`/POSIX
`os.uname`, and the profile-bound Windows architecture environment, and captures
them before compiler execution. Profile mismatch errors now expose only both
profile hashes and at most 32 keyed difference paths, hashing all environment
values and dependency paths. A 100-call, 20-caller stress run produced one
artifact digest, one 98-module dependency inventory, and one profile digest; the
ordinary frozen profile contains no `platform`, `_wmi`, or `subprocess` probe
module. The stable Core suite is 61 tests with 19 pytest subtests, and the three
focused packages pass together across 208 methods and 272 subtests. OS
sandboxing, host-native dependency closure, and authenticated authority remain
open.

## CAS PCBA v8 audit chronology

The first hardened implementation passed 43 nominal tests, but the independent
read-only audit produced nine P1 blocker classes:

1. ambient `Decimal` precision changed normalized values, projector admission,
   DRC decisions, simulation outputs, and result hashes;
2. caller-selected projector tolerance admitted `2I`, while projector identity
   omitted matrix, tolerance, and basis identity;
3. Python equality collapsed finite states such as integer `1` and Boolean
   `true`, and textual trace encoding collided Boolean `true` with string
   `"true"`;
4. DRC admitted semantically invalid signal/unit pairs and unconnected optional
   inputs that the simulator could not execute;
5. fuse reachability ignored transfer parameters, allowing a zero-gain path to
   pass a reachability check;
6. feedback analysis multiplied an entire strongly connected component instead
   of bounding each realizable cycle, allowing an amplifying branch to hide
   behind an attenuating branch;
7. a shared boundary object could be mutated after construction and then
   re-hashed, demonstrating that self-hashes are not authority;
8. public measurement/result constructors accepted fabricated IDs, nonexistent
   children, and derived-but-packet-eligible records, while calibration metadata
   was self-attested; and
9. the TKS adapter trusted an ambient import and returned a bare arrow without a
   PCBA certificate, kernel identity, or fixed boundary.

The same audit found P2 defects: the binary64 Fisher-Rao routine can act only as
a numerical pseudometric; safety probes ignored their `safety_critical` flag;
review-visible references admitted unsafe Unicode; identities omitted engine,
catalog, context, source, and DRC-report bindings; and fuse persistence scope was
not explicit.

The repair requirement is fixed and versioned arithmetic, complete identity
binding, exact tagged finite values, fail-closed DRC/runtime agreement, sound
safety-path and cycle analysis, constructor-level provenance validation,
immutable fixed boundaries, and a kernel-bound adapter certificate. Complete
CCDL parsing, faithful implementations of all reference boards, stateful and
stochastic semantics, live calibration, physical validity, safety review, and
regulatory review remain open regardless of the repair result.

The repair implemented those bounded requirements and expanded the focused
suite to 82 test methods with 195 passing subtests. A fresh independent
read-only confirmation reproduced every original Decimal, projector, finite
value, DRC/runtime, fuse, feedback, boundary, result-graph, packet, adapter,
safety-probe, Unicode, and provenance invariant with zero failures, errors, or
skips. It found no remaining ordinary correctness defect inside the declared
deterministic research profile. The complete CCDL, stateful/stochastic, live
measurement, safety, regulatory, and production boundaries remain open.

## CAS-Ohm v1 audit chronology

The first implementation passed 27 nominal tests, but adversarial review found
seven P1 blocker classes:

1. packet eligibility accepted unrelated or arbitrary evidence, unresolved
   parents, and unassessed records;
2. calibration identity omitted runtime, dtype, code, direction sign, corpus
   rights, seeds, grids, methods, rules, controls, and expiry, and failed to
   enforce the alpha domain;
3. same-sample apparent resistance could be reused as calibrated effective
   resistance;
4. residual diagnosis accepted design values, saturated states, intervals
   compatible with zero, and values without adequate uncertainty;
5. preclassification rounding could move a value across an exact Q4 boundary;
6. network capabilities could be self-attested; and
7. gain/network operations did not bind dimensions or topology.

P2 review additionally found non-injective generic canonicalization, unresolved
parent roles/order, and synthetic oracle classifications instead of derived
classifiers. The repair requirement is a fully bound calibration profile,
role-aware evidence resolution, separate apparent/calibrated/predictive
resistance types, active/nonstale uncertainty-aware residual rules, exact Q4
classification, externally verified capability grants, and unit/topology-bound
networks.

A second independent review of the 52-test hardened candidate found that its
cryptography established signature integrity but not independent authority: the
operation context still selected its own trust roots and replay time. The same
review found un-replayed `NETWORK_EQUIVALENT` roles, duplicate/cyclic network
paths, incomplete recursive freezing and evidence snapshots, missing authority
identity in derived outputs, mutable shared arithmetic context, classifications
not bound to exact sweep evidence, controls checked for presence rather than
profile relevance, undeclared packet fields, incomplete canonical tag/surrogate
handling, and public result constructors that did not always recompute their
claimed derivation.

The required correction separates structural research completeness from
authenticated Evidence Packet eligibility. Until an independently admitted
authority manifest and trusted current-time receipt exist, a locally configured
signature can support reproducible research calculations but cannot make a
packet authenticated, licensed, or product-eligible.

The second repair made locally configured authority and clock records explicitly
integrity/replay inputs only; made authenticated eligibility fail closed; replayed
network-equivalent, operating, and derived evidence; rejected duplicate and
cyclic network paths; recursively snapshotted registry evidence; bound complete
authority, attestation, runtime, dependency, code, and covariance identities;
closed packet fields; and hardened exact-type canonicalization. Independent
read-only confirmation reproduced all repaired invariants across 63 tests and
found one remaining host-dependent error path for integers beyond Python's
decimal-conversion limit. The final repair added the same explicit 2,048-bit
bound used by Core and normalized conversion failures. The stable CAS-Ohm suite
is 65 tests with 58 passing parameterized subtests. Structural completeness can
be true, but authenticated and overall eligibility remain false because external
authority and trusted current-time admission are intentionally unimplemented.

The five empirical CAS-Ohm hypotheses, held-out model experiments, uncertainty
and drift validation, inter-rater reliability, causal interpretation, and any
cross-model comparison remain explicitly open.

## Verification receipt

On 2026-08-04, `PYTHONDONTWRITEBYTECODE=1 python -B
scripts/verify_project_coherence_gate4.py` returned `PASS` from the stable,
manifest-bound candidate bytes. The integrated receipt records:

- 54 hash-bound Gate 4 artifacts;
- 61 CAS Core v8, 82 CAS PCBA v8, and 65 CAS-Ohm v1 unittest methods, for 208
  exact passing test IDs;
- 11 claim records, all Ring 4 / `NOT LICENSED`;
- 53 review criteria, 20 explicitly open;
- four direct EBNF counterexamples across five audited PCBA boards;
- eight retained CAS-Ohm source conflicts or under-specifications; and
- the integrated Gate 1 dependency chain `PASS`.

This is an identity, structure, bounded-software, and regression receipt only.
Gate 4 remains `OPEN / Ring 4 / NOT LICENSED / HELD / NOT FROZEN`; the receipt
does not establish canon acceptance, empirical validation, safety certification,
peer review, claim licensing, product readiness, or disclosure authority.

A combined focused pytest run of the three Gate 4 directories is green across
208 test methods and 272 parameterized subtests. It is not a repository-wide
receipt. Repository-wide collect-only reaches the PCBA suite but still reports
four pre-existing duplicate-package and source/test namespace collisions after
reporting 1,200 collected items. The integrated verifier therefore launches each
exact Gate 4 unittest directory in a fresh subprocess and binds both its exact
test-ID set and count. Repairing the global repository collector remains a
separate engineering obligation.

## Required open boundaries

The following remain open even if every bounded software test passes:

- semantic canon admission;
- migration and backward-compatibility acceptance;
- OS/toolchain hermeticity and Python/Rust conformance;
- authenticated claim authority;
- complete CCDL grammar and stateful PCBA semantics;
- live PCBA calibration, safety, and regulatory review;
- CAS-Ohm empirical and uncertainty/drift validation;
- independent specialist and peer review;
- CAS Harness v2 integration and causal experiments;
- product readiness; and
- public-disclosure authorization.
