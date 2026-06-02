"""Tests for the design-stage content-addressed ArtifactStore stub (workstream 02).

Import-isolated: imports ONLY from ``api.services.production.artifact_store``. Exercises the
honesty-critical behaviors from the blueprint — content-addressing, integrity-on-read that
*raises* on tampering, content-true dedup, streaming, and the descriptor provenance/metering
fields — none of which touch the live app.
"""

from __future__ import annotations

import hashlib

import pytest

from api.services.production.artifact_store import (
    ArtifactDescriptor,
    ArtifactIntegrityError,
    ArtifactStore,
    ArtifactVerifyResult,
    InMemoryArtifactStore,
    content_key,
)


def _store() -> InMemoryArtifactStore:
    return InMemoryArtifactStore()


def test_stub_satisfies_artifact_store_protocol():
    assert isinstance(_store(), ArtifactStore)


def test_put_returns_content_addressed_key():
    store = _store()
    data = b"pooled-activation-bytes"
    descriptor = store.put(data, media_type="pooled_hidden_state_activations")

    assert isinstance(descriptor, ArtifactDescriptor)
    assert descriptor.sha256 == hashlib.sha256(data).hexdigest()
    assert descriptor.key == content_key(data)
    assert descriptor.key == f"sha256:{descriptor.sha256}"
    assert descriptor.size_bytes == len(data)


def test_get_round_trips_bytes():
    store = _store()
    data = b"\x00\x01\x02 raw tensor block \xfe\xff"
    descriptor = store.put(data, media_type="pooled_hidden_state_activations", serialization="raw")

    assert store.get(descriptor.key) == data


def test_get_integrity_on_read_raises_on_tamper():
    store = _store()
    data = b"trustworthy artifact"
    descriptor = store.put(data, media_type="evidence_packet")

    # Simulate at-rest corruption: mutate the stored bytes behind the content key.
    store._blobs[descriptor.key] = b"tampered artifact"

    # Never serve an artifact whose hash does not match its key — it raises, not returns.
    with pytest.raises(ArtifactIntegrityError):
        store.get(descriptor.key)


def test_verify_reports_match_and_mismatch():
    store = _store()
    descriptor = store.put(b"verifiable", media_type="audit_verdict")

    ok = store.verify(descriptor.key)
    assert isinstance(ok, ArtifactVerifyResult)
    assert ok.match is True
    assert ok.expected == ok.actual == descriptor.sha256

    store._blobs[descriptor.key] = b"corrupted"
    bad = store.verify(descriptor.key)
    assert bad.match is False
    assert bad.actual == hashlib.sha256(b"corrupted").hexdigest()
    assert bad.expected == descriptor.sha256


def test_verify_missing_artifact_is_not_a_match():
    result = _store().verify("sha256:deadbeef")
    assert result.match is False
    assert result.actual is None
    assert "not found" in result.notes


def test_identical_content_dedups_to_one_entry():
    store = _store()
    data = b"identical bytes from two shards"
    first = store.put(data, media_type="pooled_hidden_state_activations", audit_id="audit-1", worker_id="w-1")
    second = store.put(data, media_type="pooled_hidden_state_activations", audit_id="audit-1", worker_id="w-2")

    # Same bytes -> same key -> one stored blob; first writer's provenance wins.
    assert first.key == second.key
    assert second.worker_id == "w-1"
    assert len(store._blobs) == 1


def test_distinct_content_does_not_dedup():
    store = _store()
    a = store.put(b"alpha", media_type="cas_axis_readout")
    b = store.put(b"beta", media_type="cas_axis_readout")

    assert a.key != b.key
    assert len(store._blobs) == 2


def test_stat_returns_descriptor_or_none():
    store = _store()
    descriptor = store.put(b"present", media_type="evidence_packet")

    assert store.stat(descriptor.key) == descriptor
    assert store.stat("sha256:absent") is None


def test_put_stream_matches_single_put_key():
    store = _store()
    whole = b"chunk-one|chunk-two|chunk-three"
    chunks = [b"chunk-one|", b"chunk-two|", b"chunk-three"]

    streamed = store.put_stream(iter(chunks), media_type="pooled_hidden_state_activations")
    assert streamed.key == content_key(whole)
    assert store.get(streamed.key) == whole


def test_get_stream_yields_full_object():
    store = _store()
    data = b"x" * (8 * 1024 * 1024 + 17)  # spans more than one 8 MiB chunk
    descriptor = store.put(data, media_type="pooled_hidden_state_activations")

    reassembled = b"".join(store.get_stream(descriptor.key))
    assert reassembled == data


def test_descriptor_carries_provenance_and_tenant():
    store = _store()
    descriptor = store.put(
        b"tenant-scoped activation",
        media_type="pooled_hidden_state_activations",
        serialization="safetensors",
        audit_id="audit-9",
        worker_id="worker-3",
        shard_id="shard-A",
        trace_id="trace-xyz",
        tenant_id="tenant-acme",
    )
    payload = descriptor.to_dict()

    assert payload["audit_id"] == "audit-9"
    assert payload["worker_id"] == "worker-3"
    assert payload["shard_id"] == "shard-A"
    assert payload["trace_id"] == "trace-xyz"
    assert payload["tenant_id"] == "tenant-acme"
    assert payload["serialization"] == "safetensors"
    assert payload["schema_version"] == "cas_harness_artifact_descriptor.v1"
    assert payload["tier"] == "hot"


def test_list_and_bytes_for_audit_support_metering():
    store = _store()
    store.put(b"a-bytes", media_type="pooled_hidden_state_activations", audit_id="audit-1")
    store.put(b"bb-bytes", media_type="cas_axis_readout", audit_id="audit-1")
    store.put(b"other-audit", media_type="audit_verdict", audit_id="audit-2")

    audit1 = store.list_for_audit("audit-1")
    assert len(audit1) == 2
    assert store.bytes_stored_for_audit("audit-1") == len(b"a-bytes") + len(b"bb-bytes")
    assert store.bytes_stored_for_audit("audit-2") == len(b"other-audit")


def test_set_tier_moves_artifact_to_cold():
    store = _store()
    descriptor = store.put(b"cold-candidate", media_type="pooled_hidden_state_activations")
    assert descriptor.tier == "hot"

    updated = store.set_tier(descriptor.key, "cold")
    assert updated.tier == "cold"
    # Tiering must not break integrity-on-read.
    assert store.get(descriptor.key) == b"cold-candidate"


def test_put_rejects_non_bytes():
    with pytest.raises(Exception):
        _store().put("not bytes", media_type="evidence_packet")  # type: ignore[arg-type]
