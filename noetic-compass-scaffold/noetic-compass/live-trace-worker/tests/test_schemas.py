"""Schema-level checks — these are the contract the API + UI rely on."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    CompleteEvent,
    CoverConfidence,
    CoverRowEvidence,
    CreateSessionRequest,
    MethodRuntimeStatusEvent,
    ManifestEvent,
    Mode7Edge,
    NeuronActivation,
    NeuronCoversEvent,
    TokenEvent,
)
from app.schemas.methods import LiveMethodConfig, method_runtime_statuses
from app.runtime.model_loader import PYTHIA_160M_MANIFEST as MANIFEST


def test_manifest_event_round_trip():
    e = ManifestEvent(manifest=MANIFEST)
    j = e.model_dump_json()
    e2 = ManifestEvent.model_validate_json(j)
    assert e2.manifest.model_id == "EleutherAI/pythia-160m"
    assert e2.manifest.is_real_model is False  # m1 invariant


def test_token_event_accepts_optional_confidence():
    TokenEvent(token_index=0, token="hi")  # no activations or confidence is fine
    TokenEvent(
        token_index=1,
        token=" world",
        top_activated_neurons=[NeuronActivation(layer=0, index=0, activation=0.5)],
        mode7_attribution=[Mode7Edge(from_token_index=0, to_token_index=1, weight=0.5)],
        confidence=0.8,
    )


def test_token_event_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        TokenEvent(token_index=0, token="x", confidence=1.5)


def test_mode7_weight_must_be_in_unit_interval():
    with pytest.raises(ValidationError):
        Mode7Edge(from_token_index=0, to_token_index=1, weight=1.5)


def test_complete_event_min():
    e = CompleteEvent(total_tokens=0)
    assert e.type == "complete"


def test_neuron_covers_event_default_empty():
    e = NeuronCoversEvent()
    assert e.per_class_neuron_covers == {}
    assert e.cover_evidence == {}


def test_neuron_covers_event_accepts_cover_evidence():
    confidence = CoverConfidence(
        status="real",
        score=0.72,
        label="medium",
        provenance={"formula": "targeted_drop / clean_margin"},
    )
    evidence = CoverRowEvidence(
        target="F1A",
        candidate_layers=[1, 5],
        neuron_cover=["L5N2648"],
        clean_margin=10.0,
        targeted_drop=7.2,
        confidence=confidence,
    )
    e = NeuronCoversEvent(
        per_class_neuron_covers={"F1A": ["L5N2648"]},
        cover_evidence={"F1A": evidence},
    )
    assert e.cover_evidence["F1A"].confidence.score == 0.72


def test_unavailable_cover_confidence_requires_reason():
    with pytest.raises(ValidationError):
        CoverConfidence(status="unavailable")


def test_create_session_request_defaults():
    r = CreateSessionRequest(prompt="hi")
    assert r.model_id == "EleutherAI/pythia-160m"
    assert r.max_new_tokens == 24
    assert r.temperature == 0.0
    assert r.seed is None
    assert r.probes == []
    assert r.method_configs == {}


def test_create_session_request_validates_prompt_length():
    with pytest.raises(ValidationError):
        CreateSessionRequest(prompt="")


def test_create_session_request_rejects_unsupported_live_method():
    with pytest.raises(ValidationError) as exc:
        CreateSessionRequest(
            prompt="hi",
            method_configs={
                "drive_local_eraser": {
                    "enabled": True,
                    "knobs": {"drive": "F1", "gain": 1.0},
                }
            },
        )
    assert "drive_local_eraser=unsupported" in str(exc.value)


def test_method_runtime_status_event_round_trip():
    event = MethodRuntimeStatusEvent(
        methods=[
            {
                "method_id": "evidence_packet",
                "enabled": False,
                "status": "payload_only",
                "effect": "artifact only",
            }
        ]
    )
    body = event.model_dump()
    assert body["type"] == "method_runtime_status"
    assert body["methods"][0]["status"] == "payload_only"


def test_method_runtime_statuses_do_not_enable_non_runtime_methods():
    statuses = {
        status.method_id: status
        for status in method_runtime_statuses(
            {
                "foundation_probe": LiveMethodConfig(enabled=True),
                "evidence_packet": LiveMethodConfig(
                    enabled=False,
                    knobs={"export_format": "JSON"},
                ),
                "drive_local_eraser": LiveMethodConfig(
                    enabled=False,
                    knobs={"drive": "F1", "gain": 1.0},
                ),
            }
        )
    }

    assert statuses["foundation_probe"].enabled is True
    assert statuses["foundation_probe"].status == "wired_runtime_effect"
    assert statuses["evidence_packet"].enabled is False
    assert statuses["evidence_packet"].status == "payload_only"
    assert "not by the live worker runtime" in statuses["evidence_packet"].effect
    assert statuses["drive_local_eraser"].enabled is False
    assert statuses["drive_local_eraser"].status == "unsupported"
