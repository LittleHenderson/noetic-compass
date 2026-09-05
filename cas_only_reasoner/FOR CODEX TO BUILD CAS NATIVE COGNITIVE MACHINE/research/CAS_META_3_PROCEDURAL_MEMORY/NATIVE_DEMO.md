# Separate AWS native procedural-memory demonstration

Status: implemented candidate with 364 passing pure integration tests in
`records/local_native_demo_002/receipt.json`. Not yet executed on AWS or
independently validated from a cloud packet. This document does not mark native
reuse passed.

The unchanged runtime must execute an independently specified A -> CALL(B) ->
CALL(B) parent. Both children consume the same earlier A Effect. The parent
must return the first B Effect identity, not the second equal-valued result.

## Execution and authority

`cas_meta3/native_demo.py` first runs a separate direct neural reference. Its
actual model, parameter bytes, topology, software, operation/decoder contracts,
and published schema establish compatibility. Package claims do not establish
that compatibility. A writer installs the package and exits. A fresh reader
retrieves it from the unchanged registry, checks permissions and compatibility,
links it, and executes it through the existing native runtime.

The reader also constructs a fresh native runtime to check compatibility. That
construction writes an initialized zero-tick database. It is not a no-write
operation. Package/schema/scope rejection checks happen before this probe and
before candidate execution; the earlier reference database already exists.

Five cloud rejection cases are required: unknown package digest, incompatible
software identity, denied child scope, denied parent scope, and unsupported
package schema. Altered package bytes are covered by earlier pure registry
tests, not claimed as a sixth cloud negative in this demo.

The native adapter writes only inside the exact new
`CAS_META_2_COMPOSITION/records/meta3_<job>` directory. Its source, old records,
accepted executor, verifiers and model weights remain unchanged. Demo logs,
registry and control receipts stay in this META3 package.

## Paid launch boundary

Freeze all source and tests before building the bundle. Build from committed
bytes with `tools/build_launch_bundle.py --output <new ZIP path>`. The builder
includes six source packages, unchanged published wheels and dependency lock,
and a manifest tied to the exact source commit. Prior run records are excluded.

`aws/launch.py` defaults to plan-only. Execution requires `--execute`, the exact
archive/hash/source SHA, `--approved-cap-usd 400.00`, profile, subnet, and a new
receipt directory. It reserves $7 in the one existing campaign ledger. It uses
one g7.2xlarge RTX PRO 4500 Blackwell, no automatic retry, a 7,200-second outer
limit, a 6,600-second compute ceiling and a maximum 1,200-second demo. The cloud
termination schedule must be confirmed before neural work begins. Four frozen
META1 GPU checks and four original META2 GPU checks run before the demo.

A local META3 execution lock prevents simultaneous launches through this
launcher on this checkout. It is not a cross-host or cross-version campaign
mutex. The live provider check also rejects an already active CAS job. Runs
must remain serial. Lost auxiliary-create responses require exact ownership
reconciliation; unconfirmed ownership is a cleanup issue, never permission to
delete an unrelated resource. Resource reservations are not AWS invoices.

## Two independent evidence checks

The packet preserves every file in `cloud_job/`, the exact native-job subtree
under `meta2_native/`, and any `meta1_runs/`. Complete byte inventories, raw
commands/logs, GPU test records, environment, and source bindings travel with
the archive. Partial output cannot count as a completed demonstration.

1. Run `tools/inspect_cloud_packet.py` with the externally expected packet
   digest, source SHA, job and source-bundle receipt, plus new extraction and
   inspection directories under META3 `records`. It checks archive safety,
   all bytes, source, installed wheel hashes, recorded GPU gates and both roots.
2. Pass its `semantic_audit_inputs` values to `tools/audit_native_demo.py`, plus
   a new `--output` directory. This read-only auditor checks the independently
   authored task, writer exit and fresh-reader records, registry/package/link,
   all five admissions, every stored trace against the published schema, all
   intermediate/final native results, and the exact first-B return identity.

Both tools refuse checkpoint/model loading. Neither is an independent provider
attestation. The launcher/provider receipts and live termination/cleanup check
must separately establish AWS execution and resource shutdown. Original
evidence stays unchanged; each audit writes only its own new receipt.

## Claim boundary

Storage and linking stay `UNQUALIFIED`, even if this fixed native demonstration
passes. It would establish one authored package surviving writer exit and
being reused by a fresh reader. It would not prove learned retrieval, skill
acquisition, qualification, model-version migration, suspended-caller restart,
new Noetic/Foundation meanings, pulsation, or the complete CASformer vision.
Those remain separate work toward the full objective.
