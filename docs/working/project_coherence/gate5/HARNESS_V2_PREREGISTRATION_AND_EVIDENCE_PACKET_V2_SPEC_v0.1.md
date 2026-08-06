# CAS Harness v2 preregistration and Evidence Packet v2 control kernel

Status: `DRAFT / OPEN / NOT_STARTED / RESEARCH ONLY / NOT FROZEN`

Admission and claim boundary: `RING 4 / NOT LICENSED / HELD`

This document specifies the isolated control kernel in
`src/cas_harness_v2`. It does not close Gate 5, execute an experiment, add a
live-worker route, authenticate a worker, change a product verdict, license a
claim, authorize disclosure, or establish production readiness.
It creates no live-execution, scientific, canon, product, license, or disclosure
authority.

## 1. Normative executable schemas

The closed, versioned schemas are enforced by exact-key Python loaders. The
loaders are normative because JSON Schema alone cannot verify raw-byte hashes,
claim-ledger membership, amendment-chain continuity, evidence bytes, or
cross-document identities.

| Artifact | Exact schema value | Loader |
|---|---|---|
| Per-claim preregistration | `cas_harness_v2.preregistration.v1` | `load_preregistration` |
| Preregistration amendment | `cas_harness_v2.preregistration_amendment.v1` | `load_amendment` or `PreregistrationChain.append_amendment` |
| Evidence Packet v2 | `cas_harness_v2.evidence_packet.v2` | `load_evidence_packet` |

The JSON profile rejects duplicate object keys, UTF-8 BOMs, invalid UTF-8,
non-finite values, JSON floating-point numbers, integers above 2,048 bits,
unpaired Unicode surrogates, NUL characters, excessive size/depth/node count,
unknown fields, missing fields, Boolean-as-integer substitutions, non-string
mapping keys, key-coercion collisions, and non-normalized machine identifiers.
Decimal measurements and thresholds are finite decimal strings.

Every successfully loaded artifact snapshots its exact input bytes and records
their SHA-256 and byte length. Loaded payloads are recursively immutable.

## 2. Per-claim preregistration

A preregistration binds one exact claim-ledger record to one frozen experimental
design. The claim binding contains:

- the exact raw-byte identity of `CLAIM_LEDGER_v0.1.json`;
- one `claim_id` and its exact `claim_text`;
- the canonical hash of the selected claim record; and
- the preregistration artifact's own detached raw-byte hash and byte length.

The design requires explicit:

- primary and null hypotheses, estimand, and direction;
- measurement identifiers, units, operational definitions, and measurement
  kinds;
- confirmatory and held-out-replication splits, source hashes, allocation
  rules, grouping keys, group floors, exact target groups, exact enrolled and
  analyzed row targets, and maximum disjoint missing/excluded rows;
- a fixed-sample plan with `FIXED_SAMPLE` stopping, interim outcome access
  `FORBIDDEN`, disjoint exhaustive row-accounting semantics, explicit
  exclusion and missing-data rules, fail-closed `SCIENTIFICALLY_INELIGIBLE`
  deviation effect, and an exact power-analysis artifact identity;
- threshold identifiers, operators, decimal values, units, and decision
  effects, with threshold units equal to their registered measurement units;
- matched-taxonomy, wrong-layer, and clean-null controls, with additional
  control types available only when preregistered;
- falsifiers and their consequences;
- uncertainty method, confidence level, multiplicity rule, permutations,
  seeds, and grouping unit;
- model, exact lowercase 40-character model revision, weights, tokenizer, code
  commit, clean-worktree, source, analysis, dependency, runtime, exact lowercase
  `sha256:<64-hex>` container digest, and hardware identities; and
- exact permitted and forbidden wording with a private-research claim ceiling.

The governance block is invariant and load-bearing:

```text
admission_ring       = 4
product_claim_status = NOT LICENSED
disclosure_status    = HELD
public_release       = false
product_route        = false
license_decision     = NONE
```

Any other value is rejected. No self-hash field is accepted.

## 3. Append-only amendments and outcome access

Amendments bind the base preregistration hash and the immediately preceding
amendment hash. Identifiers and timestamps must advance monotonically. Artifact
identifiers are append-only and may not collide with earlier identities. Every
public amendment load freshly replays the exact base and every predecessor
carrier. Predecessor replay is iterative, rejects cycles and skipped links, and
is capped at 128 total amendment links. Together with the 2,000,000-byte strict
JSON document ceiling, this caps retained amendment bytes at 256,000,000 and
bounds replay work; the amendment chain is a governance log, not an execution
event stream.

Only three pre-outcome amendment classes exist:

1. `ADMINISTRATIVE_CLARIFICATION` adds a non-operative note.
2. `EXECUTION_IDENTITY_ADDITION` adds exact artifact identities without
   replacing a frozen identity.
3. `EXECUTION_WINDOW` records a prospective execution window.

There is no amendment field for hypotheses, units, splits, thresholds,
controls, falsifiers, uncertainty, wording, or governance. Unknown fields are
rejected. An amendment declaring prior outcome access is rejected. The
process-local chain seals permanently when `record_outcome_access` records an
exact receipt identity and the pre-outcome chain digest; no later amendment can
be appended or injected without invalidating the seal. An `EXECUTION_WINDOW`
is unique and packet execution must occur inside it. Outcome access records the
declared execution-completion timestamp, cannot precede it, and the packet must
carry that exact sealed completion timestamp; therefore no in-protocol interim
outcome access is permitted. The event itself is a canonical exact-byte carrier
with SHA-256 and byte length, and is freshly replayed against the current
pre-outcome chain before any public read; field-only bypass mutation cannot be
rehashed into a matching packet. Public chain-state getters replay integrity
before returning state.

This is a deterministic sequence guard, not a durable authority. A later Gate 5
integration must place the chain and outcome-access event under an independently
authenticated append-only or WORM control. Reconstructing a fresh in-memory
chain is not evidence that no one previously accessed outcomes.

## 4. Evidence Packet v2

An Evidence Packet binds the exact claim, preregistration, protected design,
sealed amendment chain, raw outcomes, execution manifest, reported metrics,
controls, falsifiers, split results, uncertainty report, result summary, and
all available audit/review artifacts.

Packet artifact identifiers must be unique and disjoint from preregistration
artifact identifiers. Distinct identifiers may not reuse one SHA-256/byte-length
identity to simulate independent artifacts. When audit, replication, or claim
review records are present, the executor, auditor, replication team, and claim
reviewer identities must be pairwise distinct after Unicode NFKC normalization,
case folding, and trimming. A reported numerical-audit match cannot coexist
with discrepancies, and a mismatch must identify at least one discrepancy.
Packet creation must follow both execution completion and recorded outcome
access. Execution must start after the last preregistration amendment and fall
inside a registered execution window when one exists. Packet carrier fields are
freshly reconstructed from exact raw bytes before verification.

Every packet reports per split: groups, enrolled rows, analyzed rows, missing
rows, and excluded rows. Missing and excluded categories are disjoint and the
loader requires exact arithmetic:

```text
enrolled_rows = analyzed_rows + missing_rows + excluded_rows
```

Incoherent arithmetic is structurally rejected. Coherent underpowered runs,
target-count deviations, and missing/excluded maxima violations remain loadable
negative evidence; the computed preregistered-criteria axis fails and scientific
eligibility is `INELIGIBLE` rather than erasing the run.

The packet deliberately carries observations and artifact identities, not
caller-selected authoritative status fields. `verify_evidence_packet` computes
separate axes:

| Axis | Current isolated-kernel meanings |
|---|---|
| Structural completeness | `COMPLETE` only when every preregistration, chain, and packet artifact reference matches snapshotted bytes; otherwise `INCOMPLETE`. |
| Authenticated execution | `UNAVAILABLE` or `PRESENT_UNAUTHENTICATED`; this kernel has no trust root and no `AUTHENTICATED` path. |
| Preregistered criteria | `REPORTED_CRITERIA_MET` or `REPORTED_CRITERIA_NOT_MET`, computed from exact decimal thresholds, controls, falsifiers, and split floors. This assesses reported values, not their truth. |
| Scientific eligibility | `INELIGIBLE` when reported frozen criteria fail; otherwise `NOT_ESTABLISHED` until authenticated execution, independent audit, replication, claim review, and external scientific review exist. Underpowered and failed runs remain loadable negative evidence rather than being erased. |
| Independent numerical audit | `UNAVAILABLE`, `REPORTED_MATCH_UNAUTHENTICATED`, or `REPORTED_MISMATCH`. |
| Replication | `UNAVAILABLE` or a reported `AGREES`/`MIXED`/`DISAGREES` state marked unauthenticated. |
| Claim-language review | `UNAVAILABLE` or a reported `APPROVED`/`REJECTED` state marked unauthenticated. Approved wording must byte-for-text match a preregistered allowed string. |
| Product, license, disclosure | Always `RING 4 / NOT LICENSED / HELD / NONE`; public and product routes are always false. |

The packet's SHA-256 is an integrity identity only. It is never a signature,
reviewer identity, authorization, license, disclosure approval, WORM receipt,
scientific conclusion, or product verdict.

Authentication, audit, replication, claim-review, and external-review blockers
are reported independently of whether the frozen numerical criteria pass or
fail; a negative result cannot hide missing provenance or review.

## 5. Evidence Packet v1 boundary

Evidence Packet v1 lacks mandatory v2 facts, including a prospective per-claim
preregistration, protected-design identity, amendment/outcome-access history,
registered splits and thresholds, separated execution authentication,
independent numerical audit, replication, claim-language review, and fixed
governance state.

`reject_automatic_v1_upgrade` and `load_evidence_packet` therefore reject all
four repository-known labels (`evidence_packet.v1`,
`cas_harness_evidence_packet_v1`, `cas_harness_evidence_packet.v1`, and
`cas_harness_stage9_40e_evidence_packet.v1`) with
`AmbiguousV1UpgradeError`. A v1 packet may be cited as a separately hashed
historical source artifact in a newly authored v2 record, but missing facts may
not be inferred or backfilled as if they were prospective.

## 6. Historical design lessons retained

The control model preserves the lessons of the historical v3/v4
preregistrations:

- a successor design never edits a frozen predecessor;
- counts or outcomes already observed must be disclosed;
- prompt, group, layer, surface, taxonomy, and null controls are distinct;
- group-aware splits and uncertainty cannot be reconstructed after unblinding;
- a failed honesty control invalidates or downgrades the instrument rather than
  being absorbed into a favorable result; and
- revised thresholds belong to a new preregistration, never an amendment to the
  result-bearing design.

## 7. Verification and remaining boundaries

Authoritative manifest build and Gate 5 verifier commands, from the repository
root:

```powershell
python -I -B scripts\build_project_coherence_gate5_manifest.py
python -I -B scripts\verify_project_coherence_gate5.py
```

The manifest build is appropriate only after an intended admitted-surface
change. A local focused regression may be run separately with
`python -E -P -B -X dev -m pytest -q -p no:cacheprovider
tests\cas_harness_v2`; it bypasses the same-process receipt control and is not
the authoritative Gate 5 verifier or a locked, attested execution environment.

The suite covers missing and extra fields, duplicate JSON keys, raw-input
mutation, frozen payload mutation, wrong claim and artifact hashes, forged
governance/status fields, threshold/control/falsifier/split failures,
non-monotone or broken amendment chains, amendments after outcome access, and
v1 upgrade ambiguity. Independent adversarial cases additionally cover forged
dataclass carriers, post-seal injection, predecessor cycles, skipped links,
the exact 128-link chain bound, execution-window evasion, fixed-sample plan
deletions and forged rules, invalid target/max values, exact power-analysis
identity, row-accounting contradictions, preserved sample deviations, interim
outcome access, exact completion binding, bypass-mutated outcome-event replay,
retained-byte registry mutation, audit contradictions, normalized cross-role
aliases, and all four repository-known v1 labels.

Current focused validation: `150 passed, 99 subtests passed` under Python 3.14
with site startup and bytecode generation disabled. It comprises 94 active
kernel tests, 30 strict worker-protocol tests, four historical-recovery tests,
and 22 Gate 5 verifier red-team tests. Its same-process executed-node digest is
`6BF70F5569C4BCA5B7D896382A099FC966E9C0622B3A3694BE0B330B66048756`.
This ephemeral local receipt is checked inside the verifier but is not retained
under trusted time or WORM authority. It proves repository-local controls only;
it is not live execution, independent reproduction, scientific evidence, or
product authority.

The companion 364-test worker and 78-test API/launcher/fleet/state suites are
`LOCAL_UNATTESTED_HOST_REGRESSION` observations. One pytest process binds each
suite's duplicate-free collected/started/finished node IDs and exact
setup/call/teardown outcomes. The child starts with `-I -S -B`, imports only
locally locked pytest/plugin code before prepending exact repository roots, and
uses a fresh bytecode-cache prefix. The local runner lock binds three
interpreter files, 508 exact files owned by seven runner distributions, and
three disabled `.pth` files. Pytest and explicit plugin origins must match the
per-file lock before import; the lock is hashed and parsed from one stable byte
buffer. The surviving-module endpoint inventory maps cache paths to source and
does not prove exact executed bytecode or capture transient/unloaded/dynamic
imports, unresolved/deleted origins, native-loader dependencies, or child
processes. The standard library, distribution files absent from upstream
`RECORD`, complete test/native/descendant closure, kernel/filesystem trust, and
independent attestation remain outside the lock.

The time-indexed v0.2 container receipt records BuildKit SPDX/SLSA and Docker
Scout facts as `SELF_REPORTED_LOCAL_OBSERVATION_ONLY`; at issuance, its raw
payloads were not retained. A later additive receipt now retains ten exact OCI,
BuildKit, SPDX, SLSA, and current Scout 1.21 payloads. The current direct scan is
`COMPLETED_WITH_FINDINGS`: six records are vendor-confirmed vulnerable or
fix-deferred and one `dpkg` record remains a scanner/vendor conflict. The SARIF
does not embed the candidate invocation, scanner database/process transcripts
are absent, and linked Ubuntu vendor pages were not snapshotted. No independent
trust root or complete tool-execution replay exists. One CPU-only,
non-scientific engineering preflight
loaded the exact Pythia artifacts and ran the offline canary. It was not an
authorized or admitted experiment and created no GPU run, Evidence Packet, or
scientific result; experimental execution remains `NOT_STARTED` and
`G5-ENGINEERING-003` remains `OPEN_SECURITY`.

The broad active LF rules in `.gitattributes` are followed by later `-text`
exceptions for `api/services/cas_harness_pythia160m_*.py`,
`api/services/cas_harness_research_intervention_worker.py`,
`tests/test_cas_harness_pythia160m_*.py`, and
`tests/test_cas_harness_research_intervention_worker.py`. Those specific
exceptions preserve the already-LF historical worker source blobs as original
Git bytes while Gate 5's direct-or-transitive hash closure continues to bind
them.

Still open outside this isolated kernel:

- durable append-only storage and trusted outcome-access ordering;
- materialized, non-caller-selected trust roots and signature verification;
- trusted time, nonce/replay control, one-use run consumption, and protection
  against selective reporting across multiple packets;
- live-worker and executor/auditor protocol mapping;
- hermetic execution and environment attestation, including complete
  standard-library/test/native/descendant closure, an immutable read-only
  snapshot, privileged/metadata-preserving ABA protection, hosted/auxiliary
  loader alias hardening, and independent reproduction; the repository-local
  same-process, hardlink, reparse, descriptor, and ordinary replacement
  controls do not close `G5-ENGINEERING-002`;
- independent numerical implementation and authenticated reviewer identity;
- real person, affiliation, and organizational independence beyond normalized
  declared identity strings;
- cross-packet artifact identity and semantic/media-type equivalence when
  byte-different artifacts are relabeled or cloned;
- authorized held-out replication;
- external peer review and claim-language sign-off;
- downstream enforcement that `PacketAssessment` is evidence data and never an
  authority, authorization, or capability token;
- Gate 5 control matrix, manifest, verifier, and gate decision; and
- every production, licensing, compliance, disclosure, and public-route gate.

Until those separately authorized obligations close, Gate 5 remains `OPEN /
NOT_STARTED / RING 4 / NOT LICENSED / HELD / NOT FROZEN` with no live,
scientific, canon, product, license, or disclosure authority.
