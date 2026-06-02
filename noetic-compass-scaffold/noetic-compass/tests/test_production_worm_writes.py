"""Honesty tests for the workstream-07 WORM-write seam.

Core invariant under test: a STUB WORM store can never license
``DATA_CAPTURE_WORM_COMMITTED``. Only a re-read-verified ``LockReceipt`` flips
``capture_committed`` to True. This mirrors the gate-8 contract in
``api/services/cas_harness_data_governance.py`` (capture_committed hard-wired False at the
API tier) and the verdict runner's WORM gate.
"""

from __future__ import annotations

import pytest

from api.services.production.worm_writes import (
    InMemoryStubWormStore,
    LockReceipt,
    RetentionPolicy,
    StubWormStoreNotProductionError,
    WormCommitResult,
    WormStore,
    _verified_receipt_for_tests,
    data_capture_committed_summary,
)


def _policy() -> RetentionPolicy:
    return RetentionPolicy(mode="COMPLIANCE", retention_days=3650)


def test_stub_conforms_to_protocol() -> None:
    assert isinstance(InMemoryStubWormStore(), WormStore)


def test_stub_receipt_is_not_verifiable() -> None:
    store = InMemoryStubWormStore()
    receipt = store.put_immutable(
        key="cas-harness/evidence/abc123.json",
        body=b'{"trace_id": "abc123"}',
        content_hash="abc123" + "0" * 58,
        policy=_policy(),
    )
    assert isinstance(receipt, LockReceipt)
    # The decisive honesty assertion: a stub receipt can never be verifiable.
    assert receipt.is_verifiable() is False
    assert receipt.version_id.startswith("stub-")


def test_stub_commit_never_emits_worm_committed() -> None:
    store = InMemoryStubWormStore()
    receipt = store.put_immutable(
        key="cas-harness/evidence/abc123.json",
        body=b"{}",
        content_hash="d" * 64,
        policy=_policy(),
    )
    # Even if a caller *claims* the committed status, an unverifiable receipt downgrades it.
    result = WormCommitResult(status="DATA_CAPTURE_WORM_COMMITTED", receipt=receipt)
    summary = data_capture_committed_summary(result)

    assert summary.status == "DATA_CAPTURE_ACKNOWLEDGED"
    assert summary.capture_committed is False
    assert summary.reasons  # carries an honest reason for the downgrade


def test_acknowledged_result_stays_acknowledged() -> None:
    summary = data_capture_committed_summary(
        WormCommitResult(status="DATA_CAPTURE_ACKNOWLEDGED", receipt=None, reason="stub backend")
    )
    assert summary.status == "DATA_CAPTURE_ACKNOWLEDGED"
    assert summary.capture_committed is False


def test_stub_assert_ready_refuses_to_pose_as_production() -> None:
    with pytest.raises(StubWormStoreNotProductionError):
        InMemoryStubWormStore().assert_ready(expected=_policy())


def test_only_a_verified_receipt_licenses_worm_committed() -> None:
    """The positive path: a re-read-verified receipt (as a real backend would return) flips it."""
    store = InMemoryStubWormStore()
    stub_receipt = store.put_immutable(
        key="cas-harness/evidence/run-7.json",
        body=b"{}",
        content_hash="e" * 64,
        policy=_policy(),
    )
    assert stub_receipt.is_verifiable() is False

    # Simulate what a real S3 Object-Lock backend returns AFTER a successful re-read verify.
    verified = _verified_receipt_for_tests(stub_receipt)
    assert verified.is_verifiable() is True

    summary = data_capture_committed_summary(
        WormCommitResult(status="DATA_CAPTURE_WORM_COMMITTED", receipt=verified)
    )
    assert summary.status == "DATA_CAPTURE_WORM_COMMITTED"
    assert summary.capture_committed is True
    assert summary.retention_model == "write_once_read_many"
    assert summary.reasons == ()


def test_retention_policy_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        RetentionPolicy(mode="COMPLIANCE", retention_days=0)
    with pytest.raises(ValueError):
        RetentionPolicy(mode="NOPE", retention_days=1)  # type: ignore[arg-type]
