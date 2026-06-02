"""Content-addressed large-artifact object store — design-stage scaffold (workstream 02).

Import-isolated. NOTHING here is wired into the live FastAPI app, the fleet executor, or
the evidence-packet writers. It exists so the blueprint in
``docs/working/production_readiness/02_large_artifact_object_storage.md`` has a concrete
``ArtifactStore`` seam the team (and workstreams 06/07/08) can build against.

This module deliberately reuses the *exact* content-addressing + integrity-on-read pattern
already proven in ``api/services/cas_harness_evidence_anchor.py``:

* identity = ``sha256`` over the bytes actually stored (there: the canonical-JSON body that
  is PUT to S3; here: the serialized artifact bytes);
* the hash is embedded in the key (there: the S3 object key ``.../<entry_hash>.json``;
  here: ``sha256:<digest>``);
* **integrity-on-read**: bytes read back are re-hashed and compared to the expected digest,
  and a mismatch is surfaced as a failure — never served silently. ``_verify_s3_anchor``
  computes ``actual_manifest_hash = hashlib.sha256(body).hexdigest()`` and returns
  ``match=False`` on mismatch; this stub *raises* ``ArtifactIntegrityError`` instead, because
  a corrupted read is the storage analog of a fabricated verdict.

Honesty rule (mirrors ``api/services/production/__init__.py``): a stub is a stub. The
in-memory backend below proves *content integrity* (an honest, real property — it really
does re-hash) but it MUST NOT imply *durability* or *WORM retention* it does not provide.
It never emits a ``*_VERIFIED`` / ``*_WORM_COMMITTED`` status. Durability is the real S3
backend's job (workstream 02 Phase C); WORM/Object-Lock/retention is workstream 07 layered
on top — this store never sets retention itself.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import hashlib
from typing import Iterable, Iterator, Literal, Protocol, runtime_checkable


ARTIFACT_DESCRIPTOR_SCHEMA_VERSION = "cas_harness_artifact_descriptor.v1"

# The four captured-signal classes from gate 8
# (api/services/cas_harness_data_governance.py:53-58), plus the packet artifact types.
ArtifactMediaType = Literal[
    "model_input_output",
    "pooled_hidden_state_activations",
    "cas_axis_readout",
    "audit_verdict",
    "evidence_packet",
    "merged_evidence_packet",
]
ArtifactSerialization = Literal["json", "safetensors", "npz", "raw"]
ArtifactTier = Literal["hot", "cold"]


class ArtifactStoreError(ValueError):
    """Base error for the artifact store."""


class ArtifactIntegrityError(ArtifactStoreError):
    """Raised when bytes read back do not re-hash to their content-addressed key.

    The store must never *return* a corrupted object; it raises. This is the storage
    analog of refusing to fabricate a verdict.
    """


@dataclass(frozen=True)
class ArtifactDescriptor:
    """Self-describing provenance record for one stored artifact.

    ``sha256`` is the content identity: the key is ``f"sha256:{sha256}"``. Every other
    field walks the artifact back to its origin (the traceability spine) — which audit,
    worker, shard, trace, and tenant it belongs to, how it is serialized, how big it is.
    """

    sha256: str
    media_type: ArtifactMediaType
    serialization: ArtifactSerialization
    size_bytes: int
    audit_id: str | None = None
    worker_id: str | None = None
    shard_id: str | None = None
    trace_id: str | None = None
    tenant_id: str | None = None  # workstream 06 partition key; None == default/single-tenant
    created_at: str = ""
    schema_version: str = ARTIFACT_DESCRIPTOR_SCHEMA_VERSION
    tier: ArtifactTier = "hot"

    @property
    def key(self) -> str:
        """Content-addressed key. Identity == hash; callers cannot pick arbitrary keys."""
        return f"sha256:{self.sha256}"

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "sha256": self.sha256,
            "media_type": self.media_type,
            "serialization": self.serialization,
            "size_bytes": self.size_bytes,
            "audit_id": self.audit_id,
            "worker_id": self.worker_id,
            "shard_id": self.shard_id,
            "trace_id": self.trace_id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "tier": self.tier,
        }


@dataclass(frozen=True)
class ArtifactVerifyResult:
    """Integrity-on-read result. Shape mirrors the anchor's verify check
    (``cas_harness_evidence_anchor.py:389-396``): ``{artifact, expected, actual, match, notes}``.
    """

    artifact: str
    expected: str | None
    actual: str | None
    match: bool
    notes: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact": self.artifact,
            "expected": self.expected,
            "actual": self.actual,
            "match": self.match,
            "notes": self.notes,
        }


@runtime_checkable
class ArtifactStore(Protocol):
    """Durable, content-addressed large-object store seam.

    A real backend (S3/GCS, workstream 02 Phase C) is a drop-in for this Protocol; the
    method shapes intentionally mirror ``cas_harness_evidence_anchor``'s put/verify so the
    real implementation reuses ``ContentMD5`` single-part PUT, multipart upload, and the
    re-read-and-re-hash verify. Workstream 07 decorates ``put`` with Object-Lock/retention.
    """

    def put(
        self,
        data: bytes,
        *,
        media_type: ArtifactMediaType,
        serialization: ArtifactSerialization = "raw",
        audit_id: str | None = None,
        worker_id: str | None = None,
        shard_id: str | None = None,
        trace_id: str | None = None,
        tenant_id: str | None = None,
    ) -> ArtifactDescriptor: ...

    def put_stream(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: ArtifactMediaType,
        serialization: ArtifactSerialization = "raw",
        audit_id: str | None = None,
        worker_id: str | None = None,
        shard_id: str | None = None,
        trace_id: str | None = None,
        tenant_id: str | None = None,
    ) -> ArtifactDescriptor: ...

    def get(self, key: str) -> bytes: ...

    def get_stream(self, key: str) -> Iterator[bytes]: ...

    def stat(self, key: str) -> ArtifactDescriptor | None: ...

    def verify(self, key: str) -> ArtifactVerifyResult: ...

    def list_for_audit(self, audit_id: str) -> list[ArtifactDescriptor]: ...


def content_key(data: bytes) -> str:
    """Return the content-addressed key for ``data``: ``sha256:<hexdigest>``.

    Identity is computed over the bytes actually stored — the same discipline the anchor
    uses when it hashes the canonical-JSON body it PUTs.
    """
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


class InMemoryArtifactStore:
    """Labeled in-memory ``ArtifactStore`` stub — content-addressed + deduped.

    For tests and design only. It is honest about exactly one thing: content integrity
    (it really re-hashes on read). It provides NO durability and NO WORM; it never claims
    them. Backed by plain dicts that vanish on process exit — which is precisely why a real
    object backend is required for production (blueprint §2, §3 Phase C).
    """

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}
        self._descriptors: dict[str, ArtifactDescriptor] = {}

    # -- writes ------------------------------------------------------------------
    def put(
        self,
        data: bytes,
        *,
        media_type: ArtifactMediaType,
        serialization: ArtifactSerialization = "raw",
        audit_id: str | None = None,
        worker_id: str | None = None,
        shard_id: str | None = None,
        trace_id: str | None = None,
        tenant_id: str | None = None,
    ) -> ArtifactDescriptor:
        if not isinstance(data, (bytes, bytearray)):
            raise ArtifactStoreError("artifact data must be bytes")
        data = bytes(data)
        key = content_key(data)

        existing = self._descriptors.get(key)
        if existing is not None:
            # Content-true dedup: identical bytes -> one entry. Never dedup on a logical
            # name. (Blueprint §4.) The first writer's provenance is authoritative.
            return existing

        descriptor = ArtifactDescriptor(
            sha256=key.split(":", 1)[1],
            media_type=media_type,
            serialization=serialization,
            size_bytes=len(data),
            audit_id=audit_id,
            worker_id=worker_id,
            shard_id=shard_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._blobs[key] = data
        self._descriptors[key] = descriptor
        return descriptor

    def put_stream(
        self,
        chunks: Iterable[bytes],
        *,
        media_type: ArtifactMediaType,
        serialization: ArtifactSerialization = "raw",
        audit_id: str | None = None,
        worker_id: str | None = None,
        shard_id: str | None = None,
        trace_id: str | None = None,
        tenant_id: str | None = None,
    ) -> ArtifactDescriptor:
        # Stub buffers then delegates; the real multipart backend hashes incrementally and
        # only commits the final key once the whole stream verifies (blueprint §7 Q6).
        buffer = bytearray()
        for chunk in chunks:
            if not isinstance(chunk, (bytes, bytearray)):
                raise ArtifactStoreError("artifact stream chunks must be bytes")
            buffer.extend(chunk)
        return self.put(
            bytes(buffer),
            media_type=media_type,
            serialization=serialization,
            audit_id=audit_id,
            worker_id=worker_id,
            shard_id=shard_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
        )

    # -- reads (integrity-on-read) ----------------------------------------------
    def get(self, key: str) -> bytes:
        data = self._blobs.get(key)
        if data is None:
            raise KeyError(key)
        expected = key.split(":", 1)[1] if ":" in key else key
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            # Never serve an artifact whose hash does not match its key. (Blueprint §4.)
            raise ArtifactIntegrityError(
                f"artifact {key} failed integrity-on-read: stored bytes hash to {actual}"
            )
        return data

    def get_stream(self, key: str) -> Iterator[bytes]:
        # Verify-then-yield: re-hash up front so a corrupted object never streams out.
        data = self.get(key)
        chunk_size = 8 * 1024 * 1024  # 8 MiB, matching the real multipart part size
        for offset in range(0, len(data), chunk_size):
            yield data[offset : offset + chunk_size]

    def stat(self, key: str) -> ArtifactDescriptor | None:
        # None enables the put dedup short-circuit / "already present" check.
        return self._descriptors.get(key)

    def verify(self, key: str) -> ArtifactVerifyResult:
        descriptor = self._descriptors.get(key)
        data = self._blobs.get(key)
        expected = key.split(":", 1)[1] if ":" in key else key
        if descriptor is None or data is None:
            return ArtifactVerifyResult(
                artifact="artifact_object",
                expected=expected,
                actual=None,
                match=False,
                notes="artifact not found in store",
            )
        actual = hashlib.sha256(data).hexdigest()
        match = actual == expected
        return ArtifactVerifyResult(
            artifact="artifact_object",
            expected=expected,
            actual=actual,
            match=match,
            notes=(
                "stored bytes re-hash to the content-addressed key"
                if match
                else "stored bytes do not match the content-addressed key"
            ),
        )

    def list_for_audit(self, audit_id: str) -> list[ArtifactDescriptor]:
        return [d for d in self._descriptors.values() if d.audit_id == audit_id]

    # -- design-stage helpers (no production analog) -----------------------------
    def set_tier(self, key: str, tier: ArtifactTier) -> ArtifactDescriptor:
        """Stub-only tiering toggle (blueprint §3 Phase D). Real backend uses lifecycle rules."""
        descriptor = self._descriptors.get(key)
        if descriptor is None:
            raise KeyError(key)
        updated = replace(descriptor, tier=tier)
        self._descriptors[key] = updated
        return updated

    def bytes_stored_for_audit(self, audit_id: str) -> int:
        """Sum of stored bytes for one audit — the metering signal workstream 08 consumes.

        Reflects dedup: a blob shared across audits is counted under the audit whose
        provenance the descriptor carries, never double-counted.
        """
        return sum(d.size_bytes for d in self._descriptors.values() if d.audit_id == audit_id)
