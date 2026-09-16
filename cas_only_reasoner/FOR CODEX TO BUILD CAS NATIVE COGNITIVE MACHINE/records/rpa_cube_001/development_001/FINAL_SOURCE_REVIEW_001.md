# Independent final cube bridge review

Reviewed adapter SHA-256:
`129bcf8876a1489841e97b3161ef9d5751bc08884e7915e70b661f5b3c4e3275`.

Status: one remaining source-integrity defect was reproduced. No production
source, tests directory, ledger, or compound record was changed by this review.
All additional work stayed in this scratch directory. Neural and provider
imports were denied; existing pure compiler/constants imports were allowed.
No learner construction, prediction, training, or provider call occurred.

## Required correction: compare reconstructed JSON without scalar coercion

`_revalidate_document` compares `wire == expected`. Python equality considers
`True == 1`, `False == 0`, and `0.0 == 0`. Consequently the trusted-source
reconstruction accepts wire values whose JSON type and canonical bytes differ.

Reproduced with the supplied six-cube bundle and its valid external receipt:

- Change catalog cube revision from integer `1` to boolean `true`.
  The loader accepts it. Paging returns a cube whose actual digest differs from
  its supplied `record_digest`.
- Change a catalog source-path index from integer `0` to float `0.0`.
  The loader accepts it. Paging then raises `TypeError: list indices must be
  integers or slices, not float`.
- Change source-receipt `authorship_authenticated` from `false` to `0`.
  The loader accepts the wrong JSON type.

Use canonical JSON equality (after bounded validation) or a strict recursive
comparison that distinguishes JSON scalar types. Retain the existing navigation
allowances for focus and hypothetical selection. Do not repair the incoming
catalog silently.

Evidence:

- `test_rpa_cube_final_review.py`: independent nine-test regression suite.
- `final_review_probe_001.txt`: initial five-test run, three failures.
- `final_review_probe_002.txt`: extended nine-test run, six passes and the same
  three failures; exact adapter hash verified unchanged before/after.
- `capture_final_review_effects.py` and `final_review_effects_001.json`: actual
  wrong-digest and paging-exception consequences, with the same source hash.

## Covered boundaries and honest claims

The source constructor retains original file bytes privately and verifies both
their file SHA-256 and canonical bundle digest. A whitespace-only byte change
keeps the canonical bundle identity but changes the file identity; retaining the
old expected file digest is refused.

The parser rejects duplicate decoded keys (including equivalent escaped names),
NaN, positive/negative Infinity, numeric overflow to infinity, invalid UTF-8,
and invalid source structures. Existing bounded validation and tests constrain
source, catalog, document, lesson, node, and expansion sizes.

A catalog cursor from a different source is refused even when its own
self-contained checksum is recomputed. Normal page rows cover the complete
six-cube catalog exactly once and match their source records and record digests.
The scalar-substitution defect above is the exception that must be fixed before
claiming exact reconstructed-wire integrity.

Compilation derives its teacher reference from the supplied complete authored
graph. The learner export uses the separate three-field allowlist. The reviewed
implementation refuses target-shaped source fields and lossy option/prompt
encoding. Prior independent nine-test results are retained in
`adversarial_probe_005.txt`; those covered namespace separation, source
corruption, unsupported partial views, wrong partial face inventory, target
metadata, and truncation.

## Trust limitations to retain in documentation

Source identity is relative to an externally supplied expected identity and
original bytes. The host supplies namespace, observation metadata and revision.
These are not authenticated author signatures or independently verified world
observations. A caller that changes both the source and its expected identities
has supplied a different source, not disproved a physical fact.

Cursor hashes are content bindings, not secret signatures or evidence that prior
pages were visited. Explicit offsets already permit random access. A valid,
self-resealed cursor to another permissible offset is not an authorization
bypass and does not establish complete inspection.

`check_teacher_target` checks agreement with the supplied sidecar and its
self-contained digests. It does not reconstruct an external source. The effects
probe shows that a fabricated answer with a recomputed sidecar digest returns
`agrees: true` when compared to that same fabricated answer. This is honest only
as a local agreement check; it must not be described as verifying untrusted
export provenance or a graph-derived answer. For untrusted lesson exports, first
reconstruct the lesson against externally pinned source bytes, or add a separate
source-bound verification operation.

Supplied encoder/checkpoint identities bind the cache context only. No actual
encoder, cache capability, learned competence, causal executor, or runtime
execution is established by this bridge or this review.

