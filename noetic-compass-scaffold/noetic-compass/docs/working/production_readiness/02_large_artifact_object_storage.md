# 02 — Large Artifact Object Storage

**Workstream:** 02 of 9 · **Status:** design + gap blueprint (not implemented) · **Date:** Jun 1, 2026
**Owner seam:** the durable, content-addressed substrate where captured artifacts physically land.

> Scope boundary up front: this workstream provides the **general durable object store**.
> WORM/Object-Lock/retention/legal-hold is **workstream 07** layered *on top* of this store, not
> in it. This document defines the clean seam between the two (see §5, §6). When in doubt: 02 can
> overwrite/delete and stores anything addressably; 07 is the policy layer that forbids it for
> retained artifacts.

---

## 1. Current state (what already exists)

The Harness already content-addresses and durably persists **small** evidence artifacts. The
machinery is real and trustworthy — it is the *large-tensor* and *generalized-object* cases that
are missing.

### 1.1 Content-addressing is already implemented (not aspirational)

`api/services/cas_harness_evidence_anchor.py` is the canonical reference implementation of
content-addressing + integrity-on-read in this codebase. It is **not** generic S3 boilerplate; it
already does the exact things this workstream must generalize:

- **sha256 over canonical JSON** as the content identity:
  `_sha256_json(value)` → `hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()`,
  where `_canonical_json` is `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`
  (`cas_harness_evidence_anchor.py:454-459`). The same canonicalization appears in
  `cas_harness_merged_evidence_packets.py:443-448` and `cas_harness_fleet_executor.py:679,747-752`.
- **Hash embedded in the S3 object key** — content-addressed layout already:
  `key = f"{prefix}/{_safe(trace_id)}/{entry_hash}.json"` (`cas_harness_evidence_anchor.py:163-164`).
- **PUT with an end-to-end integrity check**: when Object Lock is configured the writer attaches
  `ContentMD5 = base64(md5(body))` so S3 rejects a corrupted body
  (`cas_harness_evidence_anchor.py:200`), and sets `Metadata` carrying `hash-log-entry-sha256` and
  `packet-without-hashes-sha256` (`:184-188`).
- **Integrity-on-read (re-hash the bytes you read back)** — the behavior §4 requires of *every*
  artifact: `_verify_s3_anchor` calls `get_object`, reads `body`, and recomputes
  `actual_manifest_hash = hashlib.sha256(body).hexdigest()`; if it `!= expected_manifest_hash` the
  verify returns `match=False` with note *"S3 anchor object hash does not match packet
  manifest_sha256"* (`cas_harness_evidence_anchor.py:277-294`). It then re-parses the body and
  confirms the manifest commits back to the packet hash + hash-log entry (`:296-326`).
- **Object-Lock verification already lives here** (this is the 07 seam): after the content match,
  `_verify_s3_anchor` issues `head_object` and checks `ObjectLockMode` == expected and
  `ObjectLockRetainUntilDate` is in the future (`cas_harness_evidence_anchor.py:328-361`).
  `_object_lock_config()` validates `GOVERNANCE|COMPLIANCE` + positive retention days
  (`:403-425`). **02 owns the PUT/GET/re-hash; 07 owns this lock/retention overlay.**
- **Honest mode ladder**: `disabled` → recorded `status="disabled"` (no anchor); `local` →
  same-host file, *never* claims WORM; `s3` → only path that can be re-read and called retained
  (`cas_harness_evidence_anchor.py:39-55`, module docstring of `cas_harness_static_evidence_anchor.py:10-25`).

### 1.2 The local packet store (durable, same-host, JSON-only)

`api/services/cas_harness_merged_evidence_packets.py` is the actual artifact store today:

- Backing: a process-global `dict` cache `_MERGED_FLEET_PACKETS: dict[str, dict]`
  (`:22`) in front of same-host JSON files under
  `tempdir/noetic-compass/cas_harness_evidence_packets[/<subdir>]/packets/<safe_trace_id>.json`
  (`_packet_store_dir`/`_packet_path` `:455-470`), overridable via
  `CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR`.
- **Atomic write** already done correctly: write to `*.json.tmp`, then `tmp_path.replace(path)`
  (`_write_packet_to_store` `:477-482`).
- **Append-only hash-log** with a chained `previous_entry_sha256`/`entry_sha256` ledger
  (`_append_hash_log_entry` `:496-518`, chain re-validation `_load_hash_log_entry` `:533-551`).
- **Namespacing hook** via `evidence_store_namespace(subdir)` contextvar (`:31-43`) — already used
  to physically isolate static reference packets. This is the natural attach point for
  **tenant partitioning (06)** (see §6).

### 1.3 What the store must hold (gate 8 capture scope)

`api/services/cas_harness_data_governance.py:53-58` enumerates the four captured signal classes
that physically land in this store:

| Signal class | Typical size | Storage implication |
|---|---|---|
| `model_input_output` | small (text/tokens) | JSON today is fine |
| `pooled_hidden_state_activations` | **large** (float tensors, can be MB–GB) | **the gap** — JSON-in-a-dict cannot hold these |
| `cas_axis_readout` | small (label/axis/confidence) | JSON today is fine |
| `audit_verdict` | small | JSON today is fine |

The harvest corpus (`cas_harness_harvest.py`) already persists I/O + readout + verdict as JSONL and
captures pooled activations only as a *reference*, not the bytes. `RETENTION_MODEL =
"write_once_read_many"` (`cas_harness_data_governance.py:61`) is the contract the store must be able
to support (07 enforces it).

---

## 2. Gap to production

1. **No large-binary path.** Every persisted artifact today is a JSON `Mapping` hashed *whole*
   (`_fragment_payload_sha256` json-dumps the entire payload — `cas_harness_fleet_executor.py:747-752`).
   Pooled hidden-state activations are float tensors that do not belong in canonical JSON: encoding
   them as JSON numbers is lossy (float repr), enormous (3–10× blowup), and un-streamable. There is
   **no** binary blob path, **no** serialization format decision, and **no** multipart/streaming
   upload.
2. **In-memory dict is not durable at scale.** `_MERGED_FLEET_PACKETS` and `_WORKERS`/`_FLEET_RUNS`
   are process-global dicts; they vanish on restart and do not span the fleet. (Per project memory,
   *"pod can disappear"* — the activation bytes are the irreplaceable harvest.)
3. **No dedup.** Re-submitting an identical artifact rewrites it; there is no
   "content hash already present → skip upload" short-circuit. At fleet scale (many shards, retried
   jobs) this is real waste and a correctness smell (two keys for one content).
4. **No descriptor/index.** There is a hash-log chain but no queryable index answering *"which
   artifacts belong to audit X / worker W / shard S, what are their hashes, sizes, provenance,
   tier?"* The fragment ref (`cas-fragment://…/sha256:<digest>` — `build_evidence_fragment_ref`
   `:652-680`) is the only join key and it is per-receipt, not per-artifact.
5. **No lifecycle/tiering.** Everything is one flat hot tier. Large activation tensors are written
   once and rarely re-read (cold), but cost the same as hot packet JSON.
6. **No size accounting.** Nothing measures bytes-stored per audit/tenant — which **billing (08)**
   needs to meter and **compliance (09)** needs for retention reporting.

---

## 3. Phased plan (each phase has an explicit kill/validate gate)

### Phase A — `ArtifactStore` Protocol + content-addressed in-memory stub
Define the seam (the `ArtifactStore` Protocol + `ArtifactDescriptor` of §5) and ship a clearly
labeled in-memory stub that content-addresses by sha256 and dedups. No real infra. (Delivered with
this doc: `api/services/production/artifact_store.py`.)
- **Validate:** put → stat → get round-trips bytes; key == `sha256:<digest>`; integrity-on-read
  re-hashes and a tampered blob raises; identical content dedups to one entry. (`test_production_artifact_store.py`.)
- **Kill:** if the Protocol cannot express the existing anchor's put/verify shape without leaking
  S3 specifics, redesign before any backend work.

### Phase B — Serialization format + descriptor schema lock
Choose and freeze the tensor serialization format (see §7 open question — recommend **safetensors**)
and the `ArtifactStore.schema_version`. Implement `serialize_activation` / `deserialize_activation`
with the content hash computed over the **serialized bytes** (not the in-memory object), so the hash
is reproducible and matches what integrity-on-read recomputes.
- **Validate:** round-trip a known activation tensor → bytes → tensor is bit-exact; the byte hash is
  stable across processes and OSes; descriptor records `media_type`, `serialization`, `size_bytes`,
  `sha256`.
- **Kill:** if the chosen format is not deterministic byte-for-byte across the fleet's Python/lib
  versions, the content hash is meaningless — fall back to raw little-endian `npy` with an explicit
  dtype/shape header before proceeding.

### Phase C — Real object backend (S3/GCS) with multipart + integrity-on-read
Implement `S3ArtifactStore` reusing the anchor's exact patterns: content-addressed key
`<prefix>/<tenant>/<sha256>` , `ContentMD5` on single-part PUT, **multipart upload** for blobs over
a threshold (default 8 MiB part size), and `get`/`verify` that re-read and re-hash the bytes
(generalizing `_verify_s3_anchor`). `put` is a content-addressed no-op when `stat` shows the key
already exists with the same size (dedup).
- **Validate:** a >100 MiB synthetic activation uploads via multipart, `stat` reports the right
  size, `get` streams it back and `verify` re-hash matches; killing the process mid-run loses no
  committed object; a corrupted part fails the PUT (S3 part-ETag/MD5 mismatch).
- **Kill:** if multipart part-ETags cannot be reconciled to a whole-object content hash cheaply,
  store the canonical `sha256` in object **metadata** (as the anchor already does with
  `Metadata["packet-without-hashes-sha256"]`) and treat the metadata hash as authoritative for
  integrity-on-read — do not block the phase on S3's composite ETag.

### Phase D — Index/catalog + lifecycle/tiering
Persist `ArtifactDescriptor`s in a queryable catalog keyed by `(audit_id, worker_id, shard_id,
sha256)`; expose `list_for_audit`. Add a `tier` field (`hot|cold`) and a lifecycle policy: large
`pooled_hidden_state_activations` default to cold (S3 IA / Glacier-class) after N days; small
packets/readouts stay hot. Emit `bytes_stored` per audit/tenant for **08**.
- **Validate:** `list_for_audit(audit_id)` returns every artifact with hash+size+tier; a cold-tier
  artifact is still `get`-able (slower) and still passes integrity-on-read; `bytes_stored` totals
  match the sum of descriptor sizes.
- **Kill:** if tiering breaks integrity-on-read or 07's Object-Lock retention (e.g. lifecycle
  transition silently drops a retained object), disable auto-tiering for any artifact under 07
  retention and tier only non-retained artifacts.

> Sequencing: A and B can land together (pure-Python, no infra). C is the first phase that needs
> real cloud + credentials. D layers on C. **07/06/08 integrations attach at the seams A defines**,
> so they are not blocked on C/D landing.

---

## 4. Honesty constraints (non-negotiable)

- **Never serve an artifact whose hash doesn't match its key.** `get(key)` MUST re-hash the bytes
  it read and raise (not return) on mismatch — mirroring `_verify_s3_anchor`'s
  `actual_manifest_hash != expected_manifest_hash` → `match=False`
  (`cas_harness_evidence_anchor.py:287-294`). A silent corrupted read is the storage analog of a
  fabricated verdict.
- **The key *is* the hash.** Content identity = sha256 over the serialized bytes. A caller cannot
  choose an arbitrary key; `put(bytes)` returns `sha256:<digest>`. This makes every artifact
  self-verifying and walks it back to its origin (the §6 traceability spine).
- **Hash provenance over the bytes actually stored.** The hash is computed over the *serialized
  bytes* the store writes, not over the in-memory object, so the number a reader recomputes is the
  number the writer committed. (Matches the anchor hashing the JSON body it PUTs.)
- **A stub is a stub.** Per `production/__init__.py:9-12`, the in-memory `ArtifactStore` MUST NOT
  emit any `*_VERIFIED`/`*_WORM_COMMITTED` status. It can prove *content integrity* (re-hash) — that
  is honest — but it must never imply *durability* or *WORM retention* it does not provide. Those
  flips belong to the real S3 backend (durability) and to 07 (WORM).
- **Declared vs verified, at the storage tier.** `put` returning a key is a *declaration* that bytes
  were accepted. `verify(key)` (re-read + re-hash, and for the real backend a HEAD) is the only
  *verified* statement. The API tier may declare an artifact reference; only the
  fleet/worker-adjacent store may assert it verified — consistent with the gate-series split
  (`00_index.md:24-34`).
- **Dedup must be content-true.** Two puts collapse to one key **only** when the bytes (hence the
  hash) are identical. Never dedup on a logical name.

---

## 5. Interfaces / seams

Concrete Protocol + descriptor (the shippable scaffold is
`api/services/production/artifact_store.py`). Method shapes mirror the anchor's existing
put/verify so a real S3 backend is a drop-in.

```python
ArtifactMediaType = Literal[
    "model_input_output",            # gate-8 signal classes (cas_harness_data_governance.py:53-58)
    "pooled_hidden_state_activations",
    "cas_axis_readout",
    "audit_verdict",
    "evidence_packet",
    "merged_evidence_packet",
]
ArtifactSerialization = Literal["json", "safetensors", "npz", "raw"]
ArtifactTier = Literal["hot", "cold"]

@dataclass(frozen=True)
class ArtifactDescriptor:
    sha256: str                  # content identity == the key digest
    media_type: ArtifactMediaType
    serialization: ArtifactSerialization
    size_bytes: int
    # provenance — every object walks back to its origin (§6 spine)
    audit_id: str | None
    worker_id: str | None
    shard_id: str | None
    trace_id: str | None
    tenant_id: str | None        # 06 partition key; None == single-tenant/default
    created_at: str
    schema_version: str          # e.g. "cas_harness_artifact_descriptor.v1"
    tier: ArtifactTier = "hot"

class ArtifactStore(Protocol):
    def put(self, data: bytes, *, media_type, audit_id=None, worker_id=None,
            shard_id=None, trace_id=None, tenant_id=None,
            serialization="raw") -> ArtifactDescriptor: ...
        # Content-addressed: key = f"sha256:{sha256(data)}". Idempotent — identical
        # bytes dedup to one entry. Returns the descriptor (carrying the key).

    def put_stream(self, chunks: Iterable[bytes], *, media_type, **prov) -> ArtifactDescriptor: ...
        # Multipart/streaming path for large tensors; hashes incrementally while uploading.

    def get(self, key: str) -> bytes: ...
        # Integrity-on-read: re-hash bytes; raise ArtifactIntegrityError on mismatch. Never serve a bad object.

    def get_stream(self, key: str) -> Iterator[bytes]: ...

    def stat(self, key: str) -> ArtifactDescriptor | None: ...   # None if absent (enables dedup short-circuit)

    def verify(self, key: str) -> ArtifactVerifyResult: ...
        # Re-read + re-hash (real backend also HEADs). Shape mirrors the anchor's
        # {"artifact","expected","actual","match","notes"} check.

    def list_for_audit(self, audit_id: str) -> list[ArtifactDescriptor]: ...  # Phase D catalog
```

**Seam to the existing fleet path.** A worker today submits
`evidence_packet_fragment_payload` (a small JSON Mapping) and a `cas-fragment://…/sha256:<digest>`
ref. With this store, the **large** `pooled_hidden_state_activations` move out of that JSON payload
into the `ArtifactStore` as a separate blob; the fragment payload then carries only the artifact
**key** (`sha256:<digest>`) + `ArtifactDescriptor` metadata. `build_evidence_fragment_ref`
(`cas_harness_fleet_executor.py:652-680`) stays the receipt-integrity join; the `ArtifactStore`
key is the durable-bytes pointer it references. Clean separation: ref = "this receipt happened",
artifact key = "these bytes are durably stored and self-verifying".

**Seam to WORM (07).** `ArtifactStore` provides plain durable PUT/GET/verify. 07 wraps the real
S3 backend's PUT with `ObjectLockMode`/`ObjectLockRetainUntilDate` (already prototyped at
`cas_harness_evidence_anchor.py:190-200`) and the HEAD-based retention verify (`:328-361`). The
store exposes a `supports_object_lock`/`put` hook 07 can decorate; **02 never sets retention
itself**.

---

## 6. Cross-references

- **01 (worker-side verification)** *produces what 02 stores.* When 01 turns
  `ACTIVATION_CAPTURE_DECLARED` → `…_VERIFIED` via real activation capture + deterministic hashing,
  those verified activation tensors are exactly the large blobs that land here. 01's deterministic
  hash should **be** the `ArtifactDescriptor.sha256` (one hash, computed once, over the serialized
  bytes) — no double-hashing.
- **07 (production WORM writes)** *wraps 02.* 07 adds Object-Lock/retention/legal-hold on top of the
  real S3 backend; the lock-verify code already lives in the anchor (`:328-361`). 02 keeps the seam
  clean by never asserting WORM and exposing a put-hook 07 decorates. `RETENTION_MODEL =
  "write_once_read_many"` (`cas_harness_data_governance.py:61`) is 07's promise; 02 is the medium.
- **06 (tenant isolation)** *partitions 02.* The `tenant_id` descriptor field is the partition key;
  the existing `evidence_store_namespace(subdir)` contextvar
  (`cas_harness_merged_evidence_packets.py:31-43`) is the local-store precedent, and the S3 key
  layout `<prefix>/<tenant>/<sha256>` carries it in the real backend. Per-tenant keys/quotas attach
  here.
- **08 (billing/accounts)** *meters bytes stored by 02.* The `size_bytes` descriptor field and the
  Phase-D `bytes_stored` per-audit/tenant rollup are 08's storage-cost signal (`COST_METERED`
  consumes it). Dedup directly affects the metered number, so the dedup rule (§4) must be auditable.
- **05 (observability)** consumes per-put/get/verify timing + bytes counters this store emits.
- **09 (compliance)** governs the retention/redaction-vs-write-once tension; because dedup means one
  blob may back many audits, a redaction request (09) cannot blindly delete a deduped object — 09 +
  06 must resolve reference-counting before any delete. Flagged in §7.

---

## 7. Open questions

1. **Serialization format for activation tensors — the single most important decision.**
   Recommend **safetensors**: zero-copy, deterministic byte layout (good for content hashing),
   explicit dtype/shape, no pickle/code-exec risk. Alternatives: `.npz` (numpy-native, but zip
   member ordering can perturb bytes → unstable hash) or raw little-endian `.npy` + explicit header
   (simplest deterministic fallback). **Decision needed before Phase B.** Whatever is chosen must be
   byte-for-byte deterministic across the fleet's Python/numpy/torch versions or the content hash is
   meaningless (Phase B kill gate).
2. **Whole-object content hash vs S3 composite multipart ETag.** S3 multipart ETags are not a plain
   sha256 of the object. Plan: store the canonical sha256 in object **metadata** (the anchor already
   does this — `Metadata["packet-without-hashes-sha256"]`, `:184-188`) and treat that as
   authoritative for integrity-on-read, rather than trying to reconstruct a hash from part ETags.
   Confirm this is acceptable to 07's retention-verify.
3. **Dedup reference-counting vs redaction (09 tension).** If one deduped blob backs N audits, who
   may delete it, and how is WORM retention (07) reconciled with a 09 redaction request? Needs a
   refcount/owner model before any `delete` exists. (Default stance: deduped + retained artifacts are
   undeletable until all retentions expire.)
4. **Hash-log integration.** Should every large-artifact PUT also append to the existing append-only
   hash-log (`cas_harness_merged_evidence_packets.py:496-518`), or does the per-object content
   address + descriptor catalog suffice? Leaning: catalog + content-address for blobs; reserve the
   chained hash-log for *packets* (its current role), to avoid a multi-GB-per-row ledger.
5. **Tiering trigger.** Time-based (cold after N days) vs access-based (cold after no reads) vs
   size+type (activations always cold, packets always hot)? Interacts with 07 retention and 08 cost.
6. **Streaming hash + early-abort.** For `put_stream`, do we hash incrementally and only commit the
   final key after the full stream verifies, or commit parts then finalize? Affects how a failed
   large upload is cleaned up without leaving orphaned parts (08 would otherwise meter dead bytes).
