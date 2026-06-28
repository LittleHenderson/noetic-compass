from __future__ import annotations

import json

from app.runtime.cover_library import (
    build_cover_payload_from_snapshot,
    derive_cover_confidence,
    unsupported_cover_confidence,
)


def test_valid_cover_confidence_score_is_real_medium():
    confidence = derive_cover_confidence(
        {"targeted_drop": 7.2, "clean_margin": 10.0},
        {"source": "unit-test"},
    )

    assert confidence.status == "real"
    assert confidence.score == 0.72
    assert confidence.label == "medium"
    assert confidence.provenance["formula"] == "targeted_drop / clean_margin"
    assert confidence.provenance["source"] == "unit-test"


def test_zero_clean_margin_makes_confidence_unavailable():
    confidence = derive_cover_confidence({"targeted_drop": 1.0, "clean_margin": 0.0})

    assert confidence.status == "unavailable"
    assert confidence.score is None
    assert "clean_margin" in (confidence.reason or "")


def test_invalid_clean_margin_makes_confidence_unavailable():
    confidence = derive_cover_confidence({"targeted_drop": 1.0, "clean_margin": "bad"})

    assert confidence.status == "unavailable"
    assert confidence.score is None
    assert confidence.reason == "clean_margin must be a positive finite number"


def test_missing_targeted_drop_makes_confidence_unavailable():
    confidence = derive_cover_confidence({"clean_margin": 10.0})

    assert confidence.status == "unavailable"
    assert confidence.score is None
    assert confidence.reason == "targeted_drop missing from Stage 27F row evidence"


def test_confidence_above_calibrated_range_is_unavailable():
    confidence = derive_cover_confidence({"targeted_drop": 9.6, "clean_margin": 10.0})

    assert confidence.status == "unavailable"
    assert confidence.score is None
    assert "0.95" in (confidence.reason or "")
    assert confidence.provenance["raw_score"] == 0.96


def test_unsupported_drive_is_not_unavailable_score():
    confidence = unsupported_cover_confidence("F8A")

    assert confidence.status == "unsupported"
    assert confidence.score is None
    assert "unsupported" in (confidence.reason or "")


def test_cover_payload_propagates_evidence_provenance(tmp_path):
    snapshot = {
        "schema_version": "stage27f_targeted_mlp_neuron_covers.v1",
        "status": "STAGE27F_TARGETED_MLP_NEURON_COVERS_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH",
        "artifact_contract": {
            "status": "LOCAL_RECAPTURE_HASH_MISMATCH",
            "formal_gate_valid": False,
        },
        "candidate_layers_per_class": {"F1A": [1, 5]},
        "per_class_neuron_covers": {"F1A": ["L5N2648"]},
        "row_reports": [
            {
                "target": "F1A",
                "candidate_layers": [1, 5],
                "neuron_cover": ["L5N2648"],
                "clean_margin": 10.0,
                "targeted_drop": 7.2,
                "sample_id": "sample-1",
            }
        ],
    }
    snapshot_path = tmp_path / "stage27f.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    payload = build_cover_payload_from_snapshot(snapshot, source_path=snapshot_path)

    evidence = payload.cover_evidence["F1A"]
    assert evidence.confidence.status == "real"
    assert evidence.confidence.provenance["source_schema_version"] == (
        "stage27f_targeted_mlp_neuron_covers.v1"
    )
    assert evidence.confidence.provenance["artifact_status"] == (
        "LOCAL_RECAPTURE_HASH_MISMATCH"
    )
    assert evidence.confidence.provenance["sample_id"] == "sample-1"
