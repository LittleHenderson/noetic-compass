# Condition-skill v9: real package and budget integration

This continues, rather than replaces, the other agent's work at
`b777584792ac6a5fede4c97ac072d4d1313fe8c9`. That commit and its publication
packet remain intact. Its 222 passing preparation tests remain a valid result
for their covered cases, not a measured learning result or an AWS launch.

## Confirmed integration findings

1. The launcher read `cap_usd`, `reserved_usd`, and `unreserved_usd`. The real
   campaign ledger uses `owner_task_cap_usd`, `total_reserved_usd`, and
   `remaining_unreserved_usd`. A guarded, read-only call to the old
   `read_ledger()` failed with `ValueError: LEDGER_FIELD:cap_usd` before any
   provider operation. The synthetic ledger in the old tests used the same
   incorrect short field names.
2. The package builder used `research/...` as a Git object key. This repository
   requires the prefix `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE
   MACHINE/`. Archive paths must still remain relative to the homebase, with
   sibling packages under `research/`.
3. The accepted baseline manifest contains 316 files, not a v0.1-only closure:
   28 v0.1, 103 v0.2, and 185 META-0 files. Both frozen wheels are required by
   the trainer. They must be packaged and installed, not replaced by source
   directories earlier on the Python import path.
4. The local worker wrapper accepted output/dataset locations incompatible
   with the real trainer and could lose its failure receipt when the trainer
   stopped before writing `result.json`. Its inherited/source `PYTHONPATH`
   also obscured proof that neural imports came from the installed wheels.

These findings concern preparation code. They do not reopen accepted core,
META-0, or META-1 audits, or establish defects in the frozen neural model.

## Budget correction

The launch reader now uses the existing canonical budget validator and strict
JSON decoder. It reads a snapshot without creating a lock or reservation.
Money is checked as exact decimal strings, not binary floating-point values.
The real spending transaction must still use the existing budget helper,
which takes its lock and rechecks the append-only history.

Tests now create their private ledgers using that real helper. No test reserves
against the canonical campaign ledger. A separate read-only test checks the
actual campaign ledger. A reservation receipt must match exactly one appended
entry, the job, source/archive identities, complete v9 resource/task plan,
the $4 amount, ledger identity, revision, balances, and prior state. A second
attempt for the same job is refused before provider callbacks.

The focused launch-plus-budget run passed 90 tests and 24 subtests. Neural,
provider and SQLite imports and socket/SQLite operations were blocked. This
is a preparation result, not AWS execution.

## Frozen learning scope stays unchanged

No edits to the trainer, data builder, dataset, checkpoint-selection rule,
adjudicator, or original protocol are part of this correction. The v9 task
remains two labelled integer conditions, not arbitrary nested composition.
The historical 256 practice records are not silently appended.

Dataset manifest:
`6b19020c4653aa535919f4af092020ad3650855bf7f58c6b550169af3d5468dd`.

Baseline manifest:
`476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0`.

The earlier held-out CAS result remains depth 3: `0/48`, depth 4: `0/24`,
total `0/72`. The `24/24` familiar-program result remains separate.
This correction establishes no new neural learning, native skill admission,
persistent Bias update, repair, caller return, or composition capability.

## Remaining real AWS connection

There is no paid run or new canonical reservation in this correction.
The verified campaign ledger remains revision 16, $98 reserved and $302
unreserved under the inclusive $400 cap. Ledger SHA-256:
`6cf5b0b2d337d1487d2c711f074c3b2b13bcbae8c5ede68ca5f5f13bf6d48f32`.

The real AWS connection must reuse the existing bounded lifecycle once. In
particular, `launch_child_qualification_v8._run_authorized()` already owns its
reservation. It must not be called behind the injectable v9 launcher's
`provider.reserve()` path, which would reserve twice. The injectable path and
its fake-provider tests do not prove real AWS operation.

Before launch, complete a source-bound outer worker/provider connection:

- Hash-bound source archive, transport request, authority, subnet and parent
  source identities; independent review and preflight.
- One reservation through the canonical helper and one registered instance;
  confirmed scheduled shutdown before publishing the execution permit.
- A clean environment with the exact two frozen wheels and pinned CUDA
  dependencies, independent AWS/GPU identity evidence, and an actual CUDA
  operation. No laptop neural work or T4.
- Exactly one candidate run, no automatic retry, bounded setup/training/output
  and collection, and evidence preserved on both success and failure.
- Provider termination/volume/input/role/schedule cleanup receipts, source and
  checkpoint hashes, and the unchanged adjudicator applied to actual results.

A source package built from the old `b7775847` tree is an integration test of
dependency resolution. It is not the final package: the actual package must
carry the corrected verifier and worker from the new committed source.

The full goal remains a persistent, programmable, continually learning CNCM.
An offline condition skill is one prerequisite to test; it is not substituted
for native admission, governed learning, return to the interrupted caller, or
unfamiliar nested composition.
