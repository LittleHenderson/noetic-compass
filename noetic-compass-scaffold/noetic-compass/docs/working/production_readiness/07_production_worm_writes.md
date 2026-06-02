# 07 — Production WORM Writes

**Workstream:** the real immutable write that honestly flips `DATA_CAPTURE_WORM_COMMITTED`.
**Sits on:** 02 (object storage — where the bytes land; Object Lock is a property of that bucket).
**Consumes:** 01 (worker-side verification — the evidence that gets committed).
**Governed by:** 09 (compliance — retention vs redaction tension, legal hold, residency).
**Partitioned by:** 06 (tenant isolation — per-tenant buckets/prefixes/keys).
**Status:** design + gap blueprint. A real Object-Lock path already exists for the static anchor; the gap is generalizing it to every fleet run and wiring the receipt to the gate-8 `capture_committed` flag.

---

## 1. Current state

### 1.1 What already exists — a real Object-Lock write IS implemented

The honesty ethos for this workstream is *already substantially honored* in one path. The
codebase is not starting from a stub; it has a working S3 Object Lock write + re-read verify.

- **`api/services/cas_harness_evidence_anchor.py`** — the load-bearing module.
  - `anchor_hash_log_entry(...)` (line 23) dispatches on `CAS_HARNESS_EVIDENCE_ANCHOR_MODE`
    (`disabled` / `local` / `s3`). With the var unset it returns `{"status": "disabled", ...}` —
    **honest default: nothing is claimed when nothing is configured.**
  - `_anchor_s3(manifest)` (line 154) does the **real immutable write**. It reads
    `_object_lock_config()` (line 403), and when `CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE`
    ∈ {`GOVERNANCE`, `COMPLIANCE`} and `..._RETENTION_DAYS` ≥ 1, it sets `ObjectLockMode`,
    `ObjectLockRetainUntilDate = now + retention_days`, and `ContentMD5` on the `put_object`
    call (lines 196–201). It returns a receipt carrying `anchor_uri` (`s3://bucket/key`),
    `etag`, `object_lock_mode`, `object_lock_retain_until`, `retention_days`.
  - `_verify_s3_anchor(packet, anchor)` (line 248) does the **real re-read proof**: `get_object`,
    sha256 the bytes, confirm the manifest commits to this packet's hash + hash-log entry, then
    `head_object` and assert `ObjectLockMode` matches AND `_retain_until_is_future(...)` (line 434)
    is true. Only then does it emit notes containing `"object lock"` and `"retention is active"`
    (lines 362–370).

- **`api/services/cas_harness_static_evidence_anchor.py`** — proves the path end-to-end for a
  *static* packet (the GPT-NeoX-20B Stage 9 40E reference).
  `summarize_static_anchor_worm_status(...)` (line 160) returns `worm_retained = True` ONLY when
  `anchor.status == "anchored"` AND `anchor.mode == "s3"` AND `verify.overall == "all_match"` AND
  the external-anchor check matched AND the re-read notes contain all of
  `_WORM_RETENTION_NOTE_TERMS = ("object was re-read", "object lock", "retention is active")`
  (lines 138–142, 187–193). Anything weaker (disabled / local / partial verify) is honestly
  `worm_retained = False`.

- **`api/services/cas_harness_merged_evidence_packets.py`** — `write_merged_fleet_evidence_packet(...)`
  (line 112) assembles a fleet packet, appends an append-only hash-log entry, persists, then calls
  `anchor_hash_log_entry(...)` (lines 196–203) to attach an `external_anchor`. So the **fleet write
  path already invokes the anchor** — but it does not yet require the anchor to be a real S3
  Object-Lock write, nor surface a WORM receipt into gate-8.

- **`api/services/cas_harness_verdict_runner.py`** — `packet_proof_is_worm_retained(proof_chips)`
  (line 150) is the consumer-facing gate. It returns `True` only when the `packet_proof` chip
  status is `"verified"` and its `detail` contains all of
  `WORM_PACKET_DETAIL_TERMS = ("worm retained", "object lock", "retention is active")` (line 27).
  `run_evidence_gated_verdict(...)` blocks any ACCEPT/SUPPRESS that lacks this (lines 127–138).
  `cas_harness_fleet_verifier.py` enforces the same at the fleet level (line 82).

### 1.2 Why `capture_committed` is hard-wired `False` at the API tier — and stays that way

`api/services/cas_harness_data_governance.py` is the gate-8 contract:

- `DataCaptureStatus` (line 42) is one of `DATA_CAPTURE_WORM_COMMITTED` /
  `DATA_CAPTURE_ACKNOWLEDGED` / `DATA_CAPTURE_NOT_ACKNOWLEDGED`.
- `DataCaptureSummary.capture_committed` (line 80) is documented as *always* `False` at this tier.
- `summarize_data_capture(...)` (line 118) can only ever return `DATA_CAPTURE_ACKNOWLEDGED` or
  `DATA_CAPTURE_NOT_ACKNOWLEDGED`; it hard-codes `capture_committed=False` (line 143) and never
  constructs `DATA_CAPTURE_WORM_COMMITTED`.
- `api/routes/cas_harness_audit.py:834` (`DataCaptureSummaryResponse`) lists
  `DATA_CAPTURE_WORM_COMMITTED` in the Literal but the API tier never produces it.

This is **correct and must be preserved.** The API tier runs *before any model executes* — at
`/distributed-audits` creation time, no bytes have been captured, so claiming a WORM commit there
would be a fabricated production status. The committed status is a **promise the fleet keeps after
the workers run**: it is honest only when a real Object-Lock write has happened and been re-read.
This mirrors every other gate's declared-vs-verified split (`*_VERIFIED`, `*_METERED`).

**Bottom line on current state:** the cryptographic + Object-Lock machinery exists and is honest.
What is missing is (a) making the *fleet* path require a real Object-Lock write (not just attempt an
anchor that may be `disabled`/`local`), (b) a typed `WormStore` seam that decouples the write from
boto3 inline code, and (c) the wiring that turns a verified lock receipt into the single licensed
producer of `DATA_CAPTURE_WORM_COMMITTED` / `capture_committed=True`.

---

## 2. Gap to production

The delta from "works for the static reference packet, behind env vars" to "every fleet run
honestly flips `DATA_CAPTURE_WORM_COMMITTED` at scale, per tenant, durably":

| # | Gap | Today | Production target |
|---|-----|-------|-------------------|
| G1 | **Captured signal ≠ anchor manifest.** The S3 write today persists the *hash-log manifest* (a commitment to the packet), not the captured-signal payload classes (`CAPTURED_SIGNAL_CLASSES`: I/O, pooled activations, CAS readout, verdict). | Anchor commits to a packet hash; the large activation bytes land via 02 separately. | A WORM commit must cover the *evidence packet that references the content-addressed signal artifacts* (02 owns the bytes; 07 locks the packet + manifests that bind them). The commit object's `content_hash` must chain to the 01 verification evidence and the 02 artifact digests. |
| G2 | **Fleet path tolerates non-WORM anchors.** `write_merged_fleet_evidence_packet` calls `anchor_hash_log_entry` but does not *require* `mode == s3` with Object Lock; a `disabled`/`local` anchor still produces a packet (correctly NOT worm-retained, but no production guarantee). | Anchor is best-effort. | A production fleet run MUST anchor with `s3` + Object Lock, re-read, and fail closed (FLAG_FOR_HUMAN_REVIEW) if the lock receipt is absent. No silent degradation to `local`. |
| G3 | **No bucket-precondition assertion.** Code sets `ObjectLockMode` on `put_object`, but if the bucket was created **without** Object Lock enabled, S3 rejects the call at write time — there is no *preflight* that asserts the bucket is Object-Lock-enabled and IAM denies delete. | Relies on the write erroring. | A startup/first-write **preflight** that verifies `GetObjectLockConfiguration` returns `Enabled`, the configured retention mode matches, and an IAM simulation confirms `DeleteObjectVersion`/`PutObjectRetention`-bypass are denied. Surface the result as an operational readiness chip. |
| G4 | **`capture_committed` is never flipped — even fleet-side.** `DataCaptureSummary` has no constructor path to `DATA_CAPTURE_WORM_COMMITTED`. The verdict runner checks WORM retention for ACCEPT, but the *gate-8 data-capture receipt* is not updated post-commit. | Stuck at `ACKNOWLEDGED`. | A fleet-side `WormCommitResult` → `DataCaptureSummary(status=DATA_CAPTURE_WORM_COMMITTED, capture_committed=True, ...)` constructor, callable ONLY with a verified `LockReceipt`. This is the literal line that keeps the promise. |
| G5 | **Legal hold is absent.** Retention period is supported; an independent `PutObjectLegalHold` capability is not. 09 needs legal hold to freeze evidence beyond/independent of the retention clock. | No legal-hold surface. | `LegalHold.apply/release` on the `WormStore`, plus the commit receipt reporting legal-hold state. |
| G6 | **Per-tenant partitioning not enforced at the WORM layer.** Prefix is a single global env var (`CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX`). | One global prefix. | 06 owns the tenant→bucket/prefix map; 07 must take a `tenant_id` and resolve a tenant-scoped bucket/prefix + per-tenant KMS key, never cross-writing. |
| G7 | **No durable receipt ledger.** Receipts live only inside the packet's `hashes.external_anchor`. | In-packet only. | A queryable commit ledger (object_url, version_id, retain_until, content_hash, tenant, run/audit id, evidence digest) for audit trails (09) and idempotent re-commit detection. |
| G8 | **boto3 inline, untyped, untestable seam.** The S3 calls are inline in `_anchor_s3`/`_verify_s3_anchor`. | Hard to stub/inject. | A `WormStore` Protocol (§5) with a real S3 implementation and an explicit in-memory stub that **cannot** emit the committed status. |

---

## 3. Phased plan (each phase has an explicit kill/validate gate)

> Guiding rule: **no phase ships a code path that can emit `DATA_CAPTURE_WORM_COMMITTED` until the
> phase that proves a locked object cannot be deleted/overwritten has passed.**

### Phase 0 — Seam extraction (no behavior change)
Define the `WormStore` Protocol, `LockReceipt`, `RetentionPolicy`, `LegalHold`, `WormCommitResult`
dataclasses (§5) in `api/services/production/worm_writes.py`. Ship a clearly-labeled
`InMemoryStubWormStore` returning a *fake* receipt with `version_id="stub-..."` and a
`worm_committed=False` flag.
- **Validate gate:** a unit test imports the module with no AWS creds, calls the stub, and asserts
  the stub's commit helper returns `DATA_CAPTURE_ACKNOWLEDGED` (never `*_WORM_COMMITTED`), and that
  `LockReceipt.is_verifiable()` is `False` for the stub receipt.
- **Kill gate:** if the Protocol cannot express the existing `cas_harness_evidence_anchor.py`
  receipt shape without losing a field, stop and reconcile the shape first (do not fork the receipt).

### Phase 1 — Bucket preflight (real infra assertion)
Implement `assert_worm_bucket_ready(bucket, expected_mode)` calling `GetObjectLockConfiguration` +
an IAM `simulate_principal_policy` for `s3:DeleteObjectVersion` / `s3:PutObjectRetention` (bypass)
+ `s3:PutBucketObjectLockConfiguration`.
- **Validate gate (the decisive test):** against a real test bucket created **with** Object Lock
  enabled in COMPLIANCE mode + a short retention, perform `put_object` with retention, then assert
  that `delete_object(VersionId=...)` **raises `AccessDenied`/`InvalidRequest`** and `put_object`
  with the same key (overwrite of the locked version) **fails**. *A passing delete/overwrite here is
  a hard FAIL of the whole workstream.*
- **Kill gate:** if COMPLIANCE-mode delete is *not* refused (e.g., bucket misconfigured, root bypass
  possible), production WORM is not real — block all `*_WORM_COMMITTED` emission and escalate to 09.

### Phase 2 — Real `S3ObjectLockWormStore` + fail-closed fleet wiring
Port `_anchor_s3`/`_verify_s3_anchor` into the `WormStore` implementation behind the Protocol; make
`write_merged_fleet_evidence_packet` (and the static anchorer) call it. Make the fleet path **fail
closed**: production runs require `mode == s3` + Object Lock or the packet stays NOT worm-retained
and the verdict stays FLAG_FOR_HUMAN_REVIEW.
- **Validate gate:** the existing `test_cas_harness_static_evidence_anchor.py` invariants still hold
  (disabled/local ⇒ not retained); a new integration test against a real Object-Lock bucket gets a
  receipt whose `verify_anchor` re-read returns the three WORM terms.
- **Kill gate:** if any non-S3 mode can produce a packet that `packet_proof_is_worm_retained`
  accepts, revert — the gate has been holed.

### Phase 3 — Flip the gate-8 status (keep the promise)
Add the constructor that turns a **verified** `WormCommitResult` into
`DataCaptureSummary(status=DATA_CAPTURE_WORM_COMMITTED, capture_committed=True, ...)`. Wire it into
the fleet completion path (NOT the API tier). The API tier's `summarize_data_capture` is untouched
and still returns `ACKNOWLEDGED`.
- **Validate gate:** a test proves (a) the API-tier summary is still `ACKNOWLEDGED`/`False`, and
  (b) the fleet-side constructor refuses to emit the committed status when handed a stub/unverified
  receipt (raises or returns `ACKNOWLEDGED`).
- **Kill gate:** if any code path can reach the committed-status constructor without a re-read-verified
  receipt, stop — that is fabricated production.

### Phase 4 — Legal hold + per-tenant + receipt ledger
Add `LegalHold.apply/release`, take `tenant_id` and resolve 06's tenant→bucket/prefix/KMS map, and
persist receipts to a durable commit ledger.
- **Validate gate:** apply a legal hold, let retention expire, assert the object still cannot be
  deleted; assert tenant A's commit lands only under tenant A's bucket/prefix; assert a re-commit of
  the same evidence digest is detected idempotently from the ledger.
- **Kill gate:** any cross-tenant write, or a legal-held object becoming deletable, blocks rollout.

---

## 4. Honesty constraints — the exact precondition list

`DATA_CAPTURE_WORM_COMMITTED` (and `capture_committed = True`) may be produced **only when ALL of the
following are simultaneously true**, verified against real infrastructure, for the specific evidence
object of the specific run/tenant:

1. **Bucket Object Lock enabled.** `GetObjectLockConfiguration(Bucket)` returns
   `ObjectLockEnabled == "Enabled"`. (A bucket without this rejects retention writes; we assert it
   proactively, not by relying on the write to error.)
2. **Retention mode + period set on the object.** The written object version carries
   `ObjectLockMode ∈ {GOVERNANCE, COMPLIANCE}` and `ObjectLockRetainUntilDate` strictly in the
   future. (`_object_lock_config()` already validates the env inputs; the *object* must carry them.)
3. **Legal-hold capability present.** The store exposes `PutObjectLegalHold`/`GetObjectLegalHold`
   (`LegalHold.apply/release/status`); a production run records the legal-hold state in the receipt.
4. **IAM denies destruction.** A policy simulation confirms the run/fleet principal is **denied**
   `s3:DeleteObjectVersion` and `s3:PutObjectRetention` (retention-shortening / bypass) and
   `s3:BypassGovernanceRetention`. In COMPLIANCE mode, *no* principal (including root) can shorten or
   delete before `retain_until`.
5. **Write returned a verifiable lock receipt.** The `put_object` returned a `LockReceipt` with
   `object_url`, `version_id`, `retain_until`, `mode`, `content_hash`, AND a **re-read**
   (`get_object` + `head_object`) confirmed: bytes hash == `content_hash`, `ObjectLockMode` matches,
   `retain_until` is future. (This is exactly `_verify_s3_anchor`'s contract; the receipt must carry
   `is_verifiable() == True` only after that re-read.)
6. **Provenance chains back.** The committed object's `content_hash` binds to the 01 verification
   evidence and the 02 artifact digests for this run — *show your work*: the receipt walks back to the
   run + evidence that produced it.

**Stub rule (non-negotiable):** the in-memory `InMemoryStubWormStore` returns a receipt with
`is_verifiable() == False` and **never** lets the gate-8 constructor emit `DATA_CAPTURE_WORM_COMMITTED`.
A stub backend yields at most `DATA_CAPTURE_ACKNOWLEDGED`. There is no flag, env var, or test hook
that makes a stub claim commitment.

---

## 5. Interfaces / seams

Proposed home: `api/services/production/worm_writes.py` (import-isolated, per the subpackage's
honesty rule). Real Python signatures:

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

ObjectLockMode = Literal["GOVERNANCE", "COMPLIANCE"]


@dataclass(frozen=True)
class RetentionPolicy:
    """How long, and under which lock mode, a committed object is immutable."""
    mode: ObjectLockMode
    retention_days: int  # must be >= 1

    def retain_until(self, *, now: datetime) -> datetime: ...


@dataclass(frozen=True)
class LockReceipt:
    """Proof returned by a real immutable write. The ONLY license for the committed status.

    `is_verifiable()` is True ONLY after a re-read (get_object + head_object) has confirmed the
    bytes hash, the Object Lock mode, and a future retain_until — mirroring _verify_s3_anchor.
    A stub receipt always returns False.
    """
    object_url: str           # e.g. "s3://tenant-bucket/prefix/<entry_sha256>.json"
    version_id: str           # S3 object version; "stub-..." for the stub
    retain_until: datetime    # future instant the object is locked until
    mode: ObjectLockMode
    content_hash: str         # sha256 of the committed bytes; chains to 01/02 evidence
    legal_hold: bool = False
    reread_verified: bool = False

    def is_verifiable(self) -> bool:
        return self.reread_verified and self.version_id != "" and not self.version_id.startswith("stub-")


@dataclass(frozen=True)
class WormCommitResult:
    """Outcome of an attempted immutable commit."""
    status: Literal["DATA_CAPTURE_WORM_COMMITTED", "DATA_CAPTURE_ACKNOWLEDGED"]
    receipt: LockReceipt | None
    reason: str | None = None  # populated when status is ACKNOWLEDGED (no real commit)


@runtime_checkable
class LegalHold(Protocol):
    def apply(self, *, object_url: str, version_id: str) -> bool: ...
    def release(self, *, object_url: str, version_id: str) -> bool: ...
    def status(self, *, object_url: str, version_id: str) -> bool: ...


@runtime_checkable
class WormStore(Protocol):
    """The immutable-write seam. Real impl = S3 Object Lock; stub = in-memory, never committed."""

    def assert_ready(self, *, expected: RetentionPolicy) -> None:
        """Raise unless the backing bucket has Object Lock enabled and IAM denies delete/bypass."""

    def put_immutable(
        self, *, key: str, body: bytes, content_hash: str, policy: RetentionPolicy,
    ) -> LockReceipt:
        """Write WORM bytes and RE-READ to produce a verifiable LockReceipt. Real backends only."""

    def legal_hold(self) -> LegalHold | None: ...
```

### How a real receipt — and only a real receipt — licenses the committed status

The single bridge into gate-8 lives next to the contract; it is the *only* constructor of the
committed status, and it refuses anything but a verified receipt:

```python
from api.services.cas_harness_data_governance import (
    DataCaptureSummary, CAPTURED_SIGNAL_CLASSES, RETENTION_MODEL, REUSE_PURPOSE,
    data_capture_requirement_notice,
)

def data_capture_committed_summary(result: WormCommitResult) -> DataCaptureSummary:
    """Fleet-side ONLY. Emits DATA_CAPTURE_WORM_COMMITTED iff a verified LockReceipt exists.

    Never called at the API tier. A stub/unverified receipt yields DATA_CAPTURE_ACKNOWLEDGED,
    capture_committed=False — identical to where summarize_data_capture() already lands.
    """
    receipt = result.receipt
    committed = (
        result.status == "DATA_CAPTURE_WORM_COMMITTED"
        and receipt is not None
        and receipt.is_verifiable()
    )
    return DataCaptureSummary(
        status="DATA_CAPTURE_WORM_COMMITTED" if committed else "DATA_CAPTURE_ACKNOWLEDGED",
        acknowledged=True,
        capture_committed=committed,  # the line that keeps the promise
        captured_signal_classes=CAPTURED_SIGNAL_CLASSES,
        retention_model=RETENTION_MODEL,
        reuse_purpose=REUSE_PURPOSE,
        notice=data_capture_requirement_notice(),
        reasons=() if committed else (result.reason or "no verified Object-Lock receipt",),
    )
```

Note the symmetry with the existing `packet_proof_is_worm_retained` (verdict_runner.py:150): the
verdict side already gates ACCEPT on the WORM terms; this constructor gates the *data-capture
receipt* on a verified `LockReceipt`. Both refuse to fabricate.

---

## 6. Cross-references

- **02 — Large artifact object storage (sits on).** 02 owns where the captured bytes physically land
  (content-addressed activations/readouts/packets, multipart, lifecycle). **Object Lock is a property
  of that bucket**, so 07's `assert_ready` precondition (§4.1) is satisfied by 02 provisioning the
  bucket *with* Object Lock enabled. 07 locks the evidence packet + manifests that *reference* 02's
  artifact digests; it does not re-store the bytes. The `content_hash` in `LockReceipt` chains to
  02's content addresses.
- **01 — Worker-side verification (consumes).** 01 turns `*_DECLARED` → `*_VERIFIED` and produces the
  proof chips / verification block that the Evidence Packet carries. 07 commits *that verified
  evidence*; the `packet_proof` chip (verdict_runner.py) is exactly the bridge — its `detail` is what
  must contain the WORM terms after 07's re-read. 07 must never commit unverified (01-incomplete)
  evidence as if it were final.
- **09 — Compliance (governed by).** 09 owns the consent → capture → retention chain that gate-8
  opens, and the **retention-vs-redaction tension**: WORM is *write-once*, so once committed the
  signal cannot be selectively deleted (`RETENTION_MODEL = "write_once_read_many"`). Legal hold
  (§5 `LegalHold`) is the 09-owned override that freezes evidence independent of the retention clock.
  The COMPLIANCE-vs-GOVERNANCE mode choice (§7) is a joint 07/09 decision.
- **06 — Tenant isolation (partitioned by).** 06 owns the tenant→bucket/prefix/KMS-key map. 07's
  `put_immutable(key=...)` must resolve a *tenant-scoped* bucket + prefix from 06 and never cross-write;
  the commit ledger (§3 Phase 4) is partitioned per tenant for 09's per-tenant audit trail.

---

## 7. Open questions (genuinely unresolved)

1. **COMPLIANCE vs GOVERNANCE lock mode (joint with 09).** COMPLIANCE mode means *no one* — not even
   the account root — can delete or shorten retention before `retain_until`. That is the strongest
   honesty guarantee and the most defensible "immutable" claim, but it is operationally unforgiving:
   a mis-keyed write or a wrong retention period is **permanently** un-fixable for the retention
   window, and it collides head-on with any GDPR/CCPA erasure obligation 09 must honor. GOVERNANCE
   mode allows a privileged principal (`s3:BypassGovernanceRetention`) to delete — softer, but then
   "WORM" is only as strong as the IAM boundary. **Decision needed:** which mode is the default, and
   is it per-tenant configurable? Gate-8's notice currently promises capture "cannot be selectively
   deleted" — that wording only holds literally under COMPLIANCE.
2. **Default retention period.** `..._RETENTION_DAYS` has no default (Object Lock is opt-in today).
   For the CAS-Native training-corpus reuse purpose, the natural answer is "indefinite," but S3
   Object Lock retention is a finite future date that must be re-applied/extended, and an
   over-long COMPLIANCE retention is an irreversible storage-cost + compliance commitment. **Decision
   needed:** a concrete default (e.g., 3650 days?) and a re-application policy for "indefinite."
3. **Redaction-vs-write-once tension (owned jointly with 09).** If a customer invokes a right-to-erasure
   over signal already COMPLIANCE-locked, the bytes literally cannot be deleted until retention
   expires. Options — (a) crypto-shredding (delete the per-tenant KMS key so the locked ciphertext is
   unrecoverable, satisfying erasure without deleting the object); (b) consent-gating capture so
   erasable data never enters WORM; (c) accept the conflict and disclose it. **Decision needed:** is
   crypto-shredding (06's per-tenant key + key deletion) the sanctioned reconciliation, and does
   legal hold ever override an erasure request?
4. **What exactly is the committed object?** The current S3 write commits the *hash-log manifest*
   (a commitment to the packet), not the packet payload or the activation bytes. **Decision needed:**
   does WORM lock (a) the manifest only (cheap, commits-by-hash, bytes live in 02 with lifecycle), or
   (b) the full Evidence Packet, or (c) the captured-signal artifacts themselves? This determines
   storage cost, the meaning of `content_hash`, and how erasure (Q3) is even possible.
5. **Idempotency / re-commit semantics.** If a fleet run is retried (04 queue/resume), the same
   evidence digest may be re-committed. With Object Lock, a second write to the same key creates a
   new locked version rather than overwriting. **Decision needed:** is the key content-addressed
   (`<entry_sha256>.json`, so a re-commit is a no-op-by-identity) and does the ledger dedupe, or do
   we tolerate multiple locked versions per evidence digest?
