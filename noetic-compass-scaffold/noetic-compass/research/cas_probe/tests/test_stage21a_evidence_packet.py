from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


evidence_packet = _load_module("evidence_packet", ROOT / "evidence_packet.py")
exporter = _load_module(
    "run_stage21a_evidence_packet_exporter",
    ROOT / "run_stage21a_evidence_packet_exporter.py",
)


def test_build_packets_exports_four_canonical_readiness_cases():
    packets = exporter.build_packets()
    by_action = {
        packet["generation_readiness"]["generation_readiness"]: packet
        for packet in packets
    }

    assert set(by_action) == {"allow", "caveat", "suppress", "constrain"}
    assert by_action["allow"]["verification"]["accepted"] is True
    assert by_action["caveat"]["verification"]["confidence_tier"] == "medium"
    assert by_action["suppress"]["verification"]["mode"] == "BALANCED"
    assert by_action["constrain"]["verification"]["mode"] == "MAX_COVERAGE_TRIAGE"


def test_packets_validate_and_carry_required_product_sections():
    packets = exporter.build_packets()

    for packet in packets:
        assert evidence_packet.validate_evidence_packet(packet) is True
        assert packet["provenance"]["code_commit"]
        assert packet["provenance"]["fixture_sha256"]
        assert packet["provenance"]["activation_sha256"]
        assert "generation_readiness" in packet["claim_badges"]
        assert packet["caveats"]
        assert "exact_sentence_forcing_in_free_form_decoding" in packet["rejected_claims"]


def test_rejected_balanced_packet_cannot_be_allow():
    packet = next(
        packet
        for packet in exporter.build_packets()
        if packet["verification"]["accepted"] is False and packet["verification"]["mode"] == "BALANCED"
    )
    packet["generation_readiness"]["generation_readiness"] = "allow"

    with pytest.raises(evidence_packet.EvidencePacketValidationError, match="must suppress"):
        evidence_packet.validate_evidence_packet(packet)


def test_rejected_triage_packet_must_constrain():
    packet = next(
        packet
        for packet in exporter.build_packets()
        if packet["verification"]["accepted"] is False
        and packet["verification"]["mode"] == "MAX_COVERAGE_TRIAGE"
    )
    packet["generation_readiness"]["generation_readiness"] = "suppress"

    with pytest.raises(evidence_packet.EvidencePacketValidationError, match="must constrain"):
        evidence_packet.validate_evidence_packet(packet)


def test_medium_accepted_packet_must_caveat():
    packet = next(
        packet
        for packet in exporter.build_packets()
        if packet["verification"]["accepted"] is True
        and packet["verification"]["confidence_tier"] == "medium"
    )
    packet["generation_readiness"]["generation_readiness"] = "allow"

    with pytest.raises(evidence_packet.EvidencePacketValidationError, match="must caveat"):
        evidence_packet.validate_evidence_packet(packet)


def test_markdown_renderer_includes_readiness_and_rejected_claims():
    packet = exporter.build_packets()[0]

    rendered = evidence_packet.render_evidence_packet_markdown(packet)

    assert packet["trace_id"] in rendered
    assert "Generation Readiness" in rendered
    assert "Rejected Claims" in rendered
    assert packet["generation_readiness"]["generation_readiness"] in rendered


def test_stage21a_summary_json_is_schema_consistent_if_present():
    summary_path = ROOT / "stage21a_evidence_packet_export_20260519.json"
    if not summary_path.exists():
        pytest.skip("summary artifact not generated yet")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["status"] == "EVIDENCE_PACKET_EXPORT_READY"
    assert summary["packet_schema_version"] == evidence_packet.SCHEMA_VERSION
    assert summary["packet_count"] == 4
