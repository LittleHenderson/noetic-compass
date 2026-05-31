from __future__ import annotations

from typing import Any

import pytest

from api.services.cas_harness_merged_evidence_packets import (
    reset_merged_fleet_evidence_packets_for_tests,
)
from api.services.cas_harness_static_evidence_anchor import (
    anchor_static_evidence_packet,
    load_anchored_static_packet_payload,
    verify_anchored_static_packet,
)

_WORM_TERMS = ("worm retained", "object lock", "retention is active")


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", raising=False)
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", raising=False)
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", raising=False)
    reset_merged_fleet_evidence_packets_for_tests()
    yield
    reset_merged_fleet_evidence_packets_for_tests()


def _static_packet(trace_id: str = "static-validation-001") -> dict[str, Any]:
    return {
        "schema_version": "cas_harness_stage9_40e_evidence_packet.v1",
        "trace_id": trace_id,
        "verdict": "ACCEPT",
        "output": {"text": "scoped validation readout"},
        "verification": {"accepted": True},
    }


def _external_anchor_check(verify: dict[str, Any]) -> dict[str, Any]:
    for check in verify["checks"]:
        if check.get("artifact") == "merged_packet_external_anchor":
            return check
    raise AssertionError("verify response missing external anchor check")


def test_disabled_mode_anchors_but_is_not_worm_retained():
    anchored = anchor_static_evidence_packet(_static_packet())

    anchor = anchored["hashes"]["external_anchor"]
    assert anchor["status"] == "disabled"
    assert anchored["hashes"]["packet_without_hashes_sha256"]

    verify = verify_anchored_static_packet(anchored)
    assert verify["overall"] == "all_match"
    notes = (_external_anchor_check(verify).get("notes") or "").lower()
    assert not all(term in notes for term in _WORM_TERMS)


def test_local_mode_anchors_but_is_not_worm_retained(monkeypatch):
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "local")
    anchored = anchor_static_evidence_packet(_static_packet("static-validation-local"))

    anchor = anchored["hashes"]["external_anchor"]
    assert anchor["status"] == "anchored"
    assert anchor["mode"] == "local"

    verify = verify_anchored_static_packet(anchored)
    assert verify["overall"] == "all_match"
    notes = (_external_anchor_check(verify).get("notes") or "").lower()
    # Local anchoring is same-host, not WORM: it must never claim object-lock retention.
    assert "object lock" not in notes
    assert not all(term in notes for term in _WORM_TERMS)


def test_anchored_packet_round_trips_from_store():
    packet = _static_packet("static-validation-roundtrip")
    anchor_static_evidence_packet(packet)

    loaded = load_anchored_static_packet_payload("static-validation-roundtrip")
    assert loaded is not None
    assert loaded["trace_id"] == "static-validation-roundtrip"
    assert "external_anchor" in loaded["hashes"]


def test_unanchored_trace_returns_none():
    assert load_anchored_static_packet_payload("never-anchored-xyz") is None


def test_tampering_with_anchored_packet_breaks_verification():
    anchored = anchor_static_evidence_packet(_static_packet("static-validation-tamper"))
    anchored["output"]["text"] = "tampered readout"

    verify = verify_anchored_static_packet(anchored)
    assert verify["overall"] == "partial_mismatch"


def test_anchor_requires_trace_id():
    with pytest.raises(ValueError):
        anchor_static_evidence_packet({"schema_version": "x", "verdict": "ACCEPT"})
