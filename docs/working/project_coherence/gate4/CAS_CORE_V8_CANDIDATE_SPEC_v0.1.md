# CAS Core v8 research candidate specification v0.1

**Status:** `OPEN / RING 4 / NOT LICENSED / HELD`

## 1. Scope

This candidate supplies a small, auditable compatibility and evidence kernel.
It is not a rewrite of CAS v7.7 and is not installed on a production route. Its
purpose is to make source identity, semantic namespace, compatibility profile,
registry integrity, action intent, and claim boundaries explicit enough to test.

## 2. Semantic identity

A semantic reference is structural data:

```text
(namespace, local_id, version, source_id, definition_sha256)
```

TKS Foundation, TKS World, CAS Drive, CAS Domain, CAS Register, CAS State, and
Noetic Topos object identities occupy different namespaces. A positional or
historical correspondence is represented as `TRANSLATION`, `ALIGNMENT`, or
`HYPOTHESIS`; it is never silently represented as `IDENTITY`.

Rendered identifiers must be injective. Delimiter-containing components cannot
create the same identifier as a different structural tuple.

## 3. Research boundary

Every candidate artifact carries a boundary. Ring 4 enforces all of:

- admission state `OPEN`;
- product state `NOT LICENSED`; and
- public disclosure `false`.

Contradictory combinations are invalid. A structural receipt or green test does
not alter this boundary.

## 4. Byte identity and canonical evidence

Raw bytes and the declared CRLF-to-LF comparison identity are recorded
separately. Lone CR, CRLF, and lone LF counts are not conflated. The evidence
encoding:

- is deterministic UTF-8 JSON with sorted string keys;
- rejects unordered containers, binary floats, NaN, and infinity;
- tags exact decimals so `Decimal("1.0")` cannot collide with the string
  `"1.0"`; and
- gives each public type one declared serialization route.

Canonicalization is bounded and cycle-aware. Review-visible machine identifiers
use declared normalized/ASCII profiles; unrestricted prose Unicode remains
separate. Equality-overriding subclasses are not admitted as identity-bearing
public values: exact types and primitive fields determine every boundary and
semantic identity check.

A self-digest detects accidental or malicious mutation after construction, but
is not a signature, reviewer identity, or authority grant.

## 5. Legacy compatibility profile

The only admitted legacy profile in v0.1 binds the exact active Python compiler
bytes listed in the Gate 4 README. It is explicitly `legacy_only` and produces
no CAS v8 semantic translation.

For deterministic closure, the profile:

- verifies the requested source hash;
- reads and hashes compiler bytes before execution;
- forces the Python-only engine profile and an exact frozen policy unless a
  separately hash-bound native engine profile is introduced;
- rejects `use` imports because no import-DAG manifest is yet admitted;
- executes the verified compiler bytes in a fresh `-I -S -B` worker with a
  sanitized environment rather than inheriting parent `sys.modules`;
- samples and binds the worker runtime before compiler code executes, deriving
  labels from interpreter fields, `sys.platform`/POSIX `os.uname`, and the
  profile-bound Windows architecture inputs without WMI or subprocess probing;
- serializes cooperating worker executions through a profile-bound advisory
  lock with a 90-second acquisition bound, 10-millisecond poll interval, and
  10-millisecond post-release scheduler yield, without retrying a failed worker
  or claiming lock fairness;
- records raw and LF compiler identities, interpreter and worker bytes, import
  search paths, loaded-module inventory, exact syntax/semantic/engine profiles,
  result digest, diagnostics, and research boundary; and
- requires fresh replay against the same source and compiler identity before a
  structural decision can pass.

This is Python-process isolation, not an operating-system sandbox. Host native
libraries and the operating system are not yet content-addressed, and every
receipt exposes both limitations as `false` capability fields. Worker transport
failure records include only exit code, stdout/stderr byte counts, and their
SHA-256 digests; an empty or malformed response fails closed and is never
retried. If two successful workers disagree on their dependency profiles, the
error records both profile hashes and at most 32 keyed difference paths;
environment values and dependency paths are represented only by hashes.

Legacy fractal digit sequences require an explicit caller-supplied catalog of
typed `FiniteArrow` values. Composition uses `SemigroupoidPath`; missing digits
or source/target mismatches fail closed. This bridge proves only type-correct
composition in the finite reference kernel, not the meaning of a legacy digit.

## 6. Registry integrity

The claim and theorem registries are exact-byte-backed snapshots validated
against the Project Coherence record contracts. Parsed headers, schemas, and
records are reconstructed from and rechecked against the retained raw ledger
and schema bytes; a direct constructor or dataclass copy cannot preserve an old
raw identity while substituting parsed content. The loader rejects duplicate
JSON keys, unknown root/record fields, wrong enums or shapes, invalid
identifiers, ambiguous versions, and missing required metadata. Loaded values
are recursively immutable, and each selected record has a deterministic digest
bound to the registry bytes.

`LICENSED` text inside a record is necessary metadata, not sufficient authority.
The v0.1 candidate has no authenticated reviewer or legal trust root and
therefore cannot authorize a claim-bearing action.

## 7. Runtime decision model

Action operation, target, and effect class are explicit enums. Nonclaim research
evidence may pass only a structural replay comparison when every exact
compatibility field and digest validates. A self-hash or Python-local sentinel
is not issuance provenance. Structural consistency is not authorization:
`authorization_granted` and the compatibility spelling `allowed` are always
false. Claim-bearing intent is denied in this candidate even if a locally
constructed ledger says `LICENSED`.

Future claim authorization requires a separately reviewed design that binds:

- an exact trusted registry/schema manifest;
- an authenticated authority/trust root;
- reviewer and admission receipts;
- Evidence Packet identities and verification status;
- claim ID and exact version; and
- the code, model, environment, semantic, and calibration identities of the
  requested operation.

## 8. Explicitly open obligations

- A hermetic subprocess/toolchain bundle is not yet established merely by
  Python-level isolation.
- Python/Rust conformance is not established; profiles remain separate.
- No v8 parser or full semantic migration is claimed.
- No claim-authority implementation is admitted.
- Independent software, formal-methods, semantics, and product-safety review is
  still required.
