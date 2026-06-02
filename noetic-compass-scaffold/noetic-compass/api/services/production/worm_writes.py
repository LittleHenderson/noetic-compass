"""Production WORM-write seam (design-stage, import-isolated) — workstream 07.

This module defines the *interface* for the real immutable write that honestly flips
``DATA_CAPTURE_WORM_COMMITTED`` (gate 8, ``api/services/cas_harness_data_governance.py``),
plus a clearly-labeled in-memory **stub** for tests.

Honesty rule (see ``docs/working/production_readiness/07_production_worm_writes.md`` and the
subpackage ``__init__``): a stub is a stub. The stub returns a *fake* receipt whose
``is_verifiable()`` is ``False``, and the gate-8 bridge here refuses to emit
``DATA_CAPTURE_WORM_COMMITTED`` for anything but a re-read-verified ``LockReceipt``. There is
no flag, env var, or test hook that lets a stub claim commitment.

Nothing here is wired into the live FastAPI app or the fleet executor. The real
``WormStore`` implementation will port the already-working S3 Object Lock write + re-read
verify from ``api/services/cas_harness_evidence_anchor.py`` (``_anchor_s3`` /
``_verify_s3_anchor``) behind the ``WormStore`` Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol, runtime_checkable

from api.services.cas_harness_data_governance import (
    CAPTURED_SIGNAL_CLASSES,
    REUSE_PURPOSE,
    RETENTION_MODEL,
    DataCaptureSummary,
    data_capture_requirement_notice,
)

ObjectLockMode = Literal["GOVERNANCE", "COMPLIANCE"]

_STUB_VERSION_PREFIX = "stub-"


@dataclass(frozen=True)
class RetentionPolicy:
    """How long, and under which lock mode, a committed object is immutable."""

    mode: ObjectLockMode
    retention_days: int

    def __post_init__(self) -> None:
        if self.mode not in ("GOVERNANCE", "COMPLIANCE"):
            raise ValueError("RetentionPolicy.mode must be GOVERNANCE or COMPLIANCE")
        if not isinstance(self.retention_days, int) or self.retention_days < 1:
            raise ValueError("RetentionPolicy.retention_days must be a positive integer")

    def retain_until(self, *, now: datetime | None = None) -> datetime:
        return (now or datetime.now(UTC)) + timedelta(days=self.retention_days)


@dataclass(frozen=True)
class LockReceipt:
    """Proof returned by a real immutable write. The ONLY license for the committed status.

    ``is_verifiable()`` is True only after a re-read (get_object + head_object) has confirmed
    the bytes hash, the Object Lock mode, and a future ``retain_until`` — mirroring
    ``_verify_s3_anchor`` in ``cas_harness_evidence_anchor.py``. A stub receipt always returns
    False because its ``version_id`` carries the stub prefix and ``reread_verified`` is False.
    """

    object_url: str
    version_id: str
    retain_until: datetime
    mode: ObjectLockMode
    content_hash: str
    legal_hold: bool = False
    reread_verified: bool = False

    def is_verifiable(self) -> bool:
        return (
            self.reread_verified
            and bool(self.version_id)
            and not self.version_id.startswith(_STUB_VERSION_PREFIX)
            and self.retain_until > datetime.now(UTC)
        )


@dataclass(frozen=True)
class WormCommitResult:
    """Outcome of an attempted immutable commit."""

    status: Literal["DATA_CAPTURE_WORM_COMMITTED", "DATA_CAPTURE_ACKNOWLEDGED"]
    receipt: LockReceipt | None
    reason: str | None = None


@runtime_checkable
class LegalHold(Protocol):
    def apply(self, *, object_url: str, version_id: str) -> bool: ...

    def release(self, *, object_url: str, version_id: str) -> bool: ...

    def status(self, *, object_url: str, version_id: str) -> bool: ...


@runtime_checkable
class WormStore(Protocol):
    """The immutable-write seam. Real impl = S3 Object Lock; stub = in-memory, never committed."""

    def assert_ready(self, *, expected: RetentionPolicy) -> None:
        """Raise unless the bucket has Object Lock enabled and IAM denies delete/bypass."""

    def put_immutable(
        self,
        *,
        key: str,
        body: bytes,
        content_hash: str,
        policy: RetentionPolicy,
    ) -> LockReceipt:
        """Write WORM bytes and RE-READ to produce a verifiable LockReceipt. Real backends only."""

    def legal_hold(self) -> LegalHold | None: ...


class StubWormStoreNotProductionError(RuntimeError):
    """Raised if anyone asks the in-memory stub to behave like real WORM infrastructure."""


class InMemoryStubWormStore:
    """A clearly-labeled, non-durable stub. Produces a FAKE, NON-VERIFIABLE receipt.

    This exists only so tests and the blueprint have a concrete seam to build against. It does
    NOT write to durable storage, does NOT enforce Object Lock, and its receipts can never
    license ``DATA_CAPTURE_WORM_COMMITTED``. Using it in a context that expects real WORM is a
    programming error, surfaced via ``assert_ready``.
    """

    is_stub = True

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def assert_ready(self, *, expected: RetentionPolicy) -> None:  # noqa: ARG002
        raise StubWormStoreNotProductionError(
            "InMemoryStubWormStore is not real WORM infrastructure: no bucket Object Lock, no "
            "IAM delete-deny, no durable retention. It cannot satisfy the production readiness "
            "preconditions and must never gate DATA_CAPTURE_WORM_COMMITTED."
        )

    def put_immutable(
        self,
        *,
        key: str,
        body: bytes,
        content_hash: str,
        policy: RetentionPolicy,
    ) -> LockReceipt:
        # Record the bytes in memory so tests can introspect, but mark the receipt UNVERIFIABLE:
        # a stub version_id + reread_verified=False guarantee is_verifiable() is False.
        self._objects[key] = body
        return LockReceipt(
            object_url=f"memory://stub-worm/{key}",
            version_id=f"{_STUB_VERSION_PREFIX}{content_hash[:16]}",
            retain_until=policy.retain_until(),
            mode=policy.mode,
            content_hash=content_hash,
            legal_hold=False,
            reread_verified=False,
        )

    def legal_hold(self) -> LegalHold | None:
        return None


def data_capture_committed_summary(result: WormCommitResult) -> DataCaptureSummary:
    """Bridge a WORM commit into the gate-8 receipt. Fleet-side ONLY; never the API tier.

    Emits ``DATA_CAPTURE_WORM_COMMITTED`` / ``capture_committed=True`` IFF the result carries a
    re-read-verified ``LockReceipt``. A stub or unverified receipt yields
    ``DATA_CAPTURE_ACKNOWLEDGED`` / ``capture_committed=False`` — exactly where the API-tier
    ``summarize_data_capture`` already lands, so the honest declared-vs-verified split holds.
    """

    receipt = result.receipt
    committed = (
        result.status == "DATA_CAPTURE_WORM_COMMITTED"
        and receipt is not None
        and receipt.is_verifiable()
    )
    reasons: tuple[str, ...] = ()
    if not committed:
        reasons = (
            result.reason
            or "no re-read-verified Object-Lock receipt; capture is acknowledged but not committed",
        )
    return DataCaptureSummary(
        status="DATA_CAPTURE_WORM_COMMITTED" if committed else "DATA_CAPTURE_ACKNOWLEDGED",
        acknowledged=True,
        capture_committed=committed,
        captured_signal_classes=CAPTURED_SIGNAL_CLASSES,
        retention_model=RETENTION_MODEL,
        reuse_purpose=REUSE_PURPOSE,
        notice=data_capture_requirement_notice(),
        reasons=reasons,
    )


def _verified_receipt_for_tests(receipt: LockReceipt) -> LockReceipt:
    """Test-only helper: a real backend produces this shape after a successful re-read.

    Kept here (rather than in the test) so the *shape* of a verifiable receipt has one
    authoritative definition. It only flips ``reread_verified`` and strips the stub prefix; it
    does NOT perform any real verification and must never be called by production code.
    """

    version_id = receipt.version_id
    if version_id.startswith(_STUB_VERSION_PREFIX):
        version_id = version_id[len(_STUB_VERSION_PREFIX) :] or "v-reread"
    return replace(receipt, version_id=version_id, reread_verified=True)
