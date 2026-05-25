from __future__ import annotations

import json
from pathlib import Path

from api.services.cas_harness_evidence_bridge import (
    normalize_evidence_packet_for_audit,
    normalize_public_evidence_manifest_for_audit,
)


def _chips_by_id(result):
    return {chip.id: chip for chip in result.chips}


def _packet_fixture() -> dict:
    return {
        "schema_version": "evidence_packet.v1",
        "trace_id": "trace-123",
        "generated_at": "2026-05-25T00:00:00Z",
        "input": {"text": "Prompt"},
        "cas_expression": {
            "text": "^3^P|A",
            "compiler_valid": True,
            "grammar_category": "state_literal",
        },
        "output": {"text": "Model answer", "n_tokens": 12},
        "provenance": {
            "model_checkpoint_id": "EleutherAI/pythia-160m",
            "code_commit_sha": "abc123",
        },
        "hashes": {
            "weights_sha": "a" * 64,
            "tokenizer_hash": "b" * 64,
            "on_disk_paths": {"weights_path": "model.pt"},
        },
        "claim_levels": [
            {
                "claim": "CAS compiler accepted ^3^P|A.",
                "level": "cas_hard_trace",
                "support_status": "supported",
                "support_rationale": "Compiler-valid CAS expression.",
                "rationale": "compiler_valid=true",
            }
        ],
    }


def test_evidence_packet_normalizes_present_and_missing_proof_chips():
    result = normalize_evidence_packet_for_audit(_packet_fixture())
    chips = _chips_by_id(result)

    assert result.trace_id == "trace-123"
    assert result.evidence_packet_trace_id == "trace-123"
    assert [chip.id for chip in result.chips] == [
        "model_proof",
        "cas_readout",
        "causal_proof",
        "control_proof",
        "output_proof",
        "packet_proof",
    ]
    assert chips["model_proof"].status == "present"
    assert chips["cas_readout"].status == "present"
    assert chips["output_proof"].status == "present"
    assert chips["packet_proof"].status == "present"
    assert chips["causal_proof"].status == "missing"
    assert chips["control_proof"].status == "missing"


def test_hash_verification_upgrades_packet_and_model_only_when_all_match():
    result = normalize_evidence_packet_for_audit(
        _packet_fixture(),
        verify_hashes={"overall": "all_match", "checks": []},
    )
    chips = _chips_by_id(result)

    assert chips["packet_proof"].status == "verified"
    assert chips["model_proof"].status == "verified"
    assert chips["cas_readout"].status == "present"


def test_hash_verification_mismatch_marks_hash_backed_chips_failed():
    result = normalize_evidence_packet_for_audit(
        _packet_fixture(),
        verify_hashes={"overall": "partial_mismatch", "checks": []},
    )
    chips = _chips_by_id(result)

    assert chips["packet_proof"].status == "failed"
    assert chips["model_proof"].status == "failed"
    assert chips["output_proof"].status == "present"


def test_product_style_packet_fields_are_mapped_without_inventing_verdict():
    packet = {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": "stage21a-suppress-001",
        "model": {"model_key": "olmo1b", "name": "OLMo-1B"},
        "provenance": {"source_stage": "Stage 21A"},
        "readout": {"axis": "drive", "label": "F1", "confidence": 0.86},
        "ablation": {"status": "present", "effect": "targeted_drop"},
        "matched_controls": {"status": "present", "control": "random_same_rank"},
        "output": {"text": "Observed model output"},
    }

    result = normalize_evidence_packet_for_audit(packet)
    chips = _chips_by_id(result)
    payload = result.to_dict()

    assert chips["model_proof"].status == "present"
    assert chips["cas_readout"].status == "present"
    assert chips["causal_proof"].status == "present"
    assert chips["control_proof"].status == "present"
    assert chips["output_proof"].status == "present"
    assert chips["packet_proof"].status == "present"
    assert "verdict" not in payload
    assert "confidence" not in payload


def test_missing_trace_and_explicit_null_model_are_not_upgraded():
    packet = {
        "schema_version": "evidence_packet.v1",
        "trace_id": None,
        "provenance": {"model_checkpoint_id": "unknown"},
        "hashes": {"weights_sha": None, "on_disk_paths": {}},
        "output": {},
    }

    result = normalize_evidence_packet_for_audit(packet)
    chips = _chips_by_id(result)

    assert result.evidence_packet_trace_id is None
    assert chips["packet_proof"].status == "missing"
    assert chips["model_proof"].status == "unavailable"
    assert chips["output_proof"].status == "missing"


def test_claim_support_failure_maps_to_failed_not_present():
    packet = _packet_fixture()
    packet["claim_levels"] = [
        {
            "claim": "Ablation contradicted the claimed effect.",
            "level": "derived_trace",
            "support_status": "contradicted",
            "support_rationale": "Targeted removal did not change the readout.",
            "rationale": "ablation negative",
        }
    ]

    result = normalize_evidence_packet_for_audit(packet)
    chips = _chips_by_id(result)

    assert chips["causal_proof"].status == "failed"
    assert "did not change" in chips["causal_proof"].detail


def test_public_manifest_maps_claims_but_not_model_or_packet_proof():
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "research"
        / "cas_probe"
        / "cas_harness_public_evidence_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    result = normalize_public_evidence_manifest_for_audit(manifest)
    chips = _chips_by_id(result)

    assert result.source_schema == "cas_harness_public_evidence_manifest.v1"
    assert result.evidence_packet_trace_id is None
    assert chips["model_proof"].status == "unavailable"
    assert chips["cas_readout"].status == "present"
    assert chips["causal_proof"].status == "present"
    assert chips["control_proof"].status == "present"
    assert chips["output_proof"].status == "present"
    assert chips["packet_proof"].status == "unavailable"
    assert result.warnings
