# Tenant Evidence Packet Object Storage

Status: source implementation `present`; public/paid readiness `OPEN`; hosted
multi-replica proof `unavailable`.

This change removes host-local packet bytes from the account-mode design. It
does not enable accounts or make a customer-production `ACCEPT` claim.

## Plain-English map

| Technical part | Everyday equivalent |
|---|---|
| S3 Object-Lock packet version | A sealed evidence envelope that cannot be replaced |
| StateStore packet index | The tenant-specific card catalog for those envelopes |
| Hash-log lease and CAS head | One numbered ticket controlling who adds the next ledger row |
| WORM receipt row | The signed filing receipt proving that ledger row reached a sealed envelope |
| Request tenant scope | The locked customer drawer selected by server identity |

## Source contract

`api/services/cas_harness_evidence_object_store.py` provides the shared
repository. Its invariants are:

1. Packet object keys are derived from SHA-256 tenant, namespace, and trace
   identities. Raw tenant identifiers are not placed in S3 keys.
2. S3 writes use `IfNoneMatch: *`, bucket versioning, `ContentMD5`, and explicit
   Object-Lock mode/retention. A write is accepted only after byte/hash,
   `VersionId`, lock mode, and future retention are re-read.
3. The tenant-partitioned `StateStore` keeps the immutable packet index. An
   existing trace can be retried with identical bytes, but different bytes
   raise an immutable conflict.
4. The tenant hash log uses a shared-store lease plus version-checked head.
   Each entry receives a separate WORM receipt only after its packet version is
   re-read and indexed. A crash after append but before packet filing makes the
   chain fail verification until an idempotent retry repairs the receipt.
5. Evidence reads use an async FastAPI dependency so the server-derived tenant
   scope remains active through the complete handler. A process-global packet
   cache is never used while tenant storage is active.
6. The old file/JSONL path remains the unchanged default for account-OFF demo
   and static-reference behavior. The shared repository is dark unless
   `NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED=true`.

## Required configuration

Hosted account mode now requires all of the following:

- `NC_ACCOUNTS_ENABLED=true`
- `NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED=true`
- shared Postgres `NC_DATABASE_URL`
- `CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET`
- `CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION` when the bucket is not in the SDK default region
- `CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE=GOVERNANCE` or `COMPLIANCE`
- positive `CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS`
- AWS credentials able to put/get/head the versioned objects

Startup verifies bucket Object Lock and versioning. Keep
`NC_ACCOUNTS_ENABLED=false` and
`NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED=false` until the deployment gates
below pass.

## Source verification

The focused source suite covers:

- trusted S3 conditional create, version, Object-Lock, and re-read receipt;
- missing bucket Object Lock fail-closed behavior;
- tenant isolation and immutable trace conflict;
- close/reopen restart recovery;
- two repository instances sharing the same StateStore/object backend;
- concurrent packet create and concurrent hash-log append;
- idempotent duplicate append;
- append-before-WORM crash detection and retry repair;
- real FastAPI account ownership dependency reading/verifying the shared packet;
- remote-byte tamper detection;
- unchanged legacy runners, routes, ownership, static anchor, fleet, and WORM tests.

These are source tests, not hosted infrastructure proof.

## Remaining production gates

- Merge/deploy the account hardening, Mode 7, and this stacked branch.
- Provision/verify the real Object-Lock bucket and least-privilege IAM. Bucket
  API readiness does not by itself prove an organization-level deny on delete
  or retention bypass; attach that policy evidence separately.
- Run an account-mode hosted audit that writes, restarts, and re-reads the exact
  packet through `/evidence/{trace_id}` and `/verify`.
- Run two API replicas against the same Postgres and S3 backends with concurrent
  audit completions, then prove one durable chain and tenant isolation after a
  replica termination.
- Prove the configured retention mode honestly. `GOVERNANCE` is not permanent
  or `COMPLIANCE` retention.
- Add operational alerts for failed/unreceipted append rows and an authorized,
  audited retry/reconciliation job.

Until those gates pass, paid/public account readiness remains `OPEN`, hosted
multi-replica proof remains `unavailable`, and this work does not mint
`ACCEPT`.
