from __future__ import annotations

from api.services.cas_harness_comply_refuse_detection import (
    POST_HOC_WINDOW_CLAIM_CEILING,
    build_unavailable_comply_refuse_detection,
    comply_refuse_detection_from_worker_events,
    score_comply_refuse_vector,
)


def _probe(*, read: str = "window", model: str = "Qwen/Qwen2.5-1.5B-Instruct"):
    return {
        "kind": "comply_refuse_detection_probe",
        "read": read,
        "model": model,
        "layer_hidden_states_index": 14,
        "cv_auc": 1.0,
        "n_comply": 160,
        "n_refuse": 24,
        "score_sign": "+ => COMPLIED, - => REFUSED",
        "claim_ceiling": POST_HOC_WINDOW_CLAIM_CEILING,
        "scaler_mean": [0.0, 0.0],
        "scaler_scale": [1.0, 1.0],
        "coef": [1.0, -1.0],
        "intercept": 0.0,
    }


def test_comply_refuse_window_probe_scores_compatible_vector():
    payload = score_comply_refuse_vector(
        vector=[2.0, 0.0],
        probe=_probe(),
        model_id="Qwen/Qwen2.5-1.5B-Instruct",
        evidence_packet_trace_id="trace-1",
    )

    assert payload["schema_version"] == "cas_harness_comply_refuse_detection.v0"
    assert payload["status"] == "present"
    assert payload["label"] == "COMPLIED"
    assert payload["score"] == 2.0
    assert payload["p_complied"] > 0.5
    assert payload["verdict_effect"] == "none_shadow_only"
    assert "DETECTION ONLY" in payload["claim_ceiling"]
    assert "NOT a pre-speech" in payload["claim_ceiling"]
    assert payload["evidence_packet_trace_id"] == "trace-1"


def test_comply_refuse_probe_refuses_model_mismatch():
    payload = score_comply_refuse_vector(
        vector=[2.0, 0.0],
        probe=_probe(),
        model_id="EleutherAI/pythia-160m",
        evidence_packet_trace_id="trace-2",
    )

    assert payload["status"] == "unavailable"
    assert "model mismatch" in payload["reason"]
    assert payload["probe_model"] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert "NOT a pre-speech" in payload["claim_ceiling"]


def test_comply_refuse_prompt_probe_stays_diagnostic_only():
    payload = score_comply_refuse_vector(
        vector=[2.0, 0.0],
        probe=_probe(read="prompt"),
        model_id="Qwen/Qwen2.5-1.5B-Instruct",
        evidence_packet_trace_id="trace-3",
    )

    assert payload["status"] == "unavailable"
    assert "not the post-hoc" in payload["reason"]
    assert payload["label"] is None


def test_worker_detection_event_requires_claim_ceiling():
    payload = comply_refuse_detection_from_worker_events(
        [
            {
                "type": "comply_refuse_detection",
                "label": "COMPLIED",
                "score": 1.2,
                "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
            }
        ],
        model_id="Qwen/Qwen2.5-1.5B-Instruct",
        evidence_packet_trace_id="trace-4",
    )

    assert payload["status"] == "unavailable"
    assert "claim ceiling" in payload["reason"]


def test_worker_detection_event_normalizes_present_payload():
    payload = comply_refuse_detection_from_worker_events(
        [
            {
                "type": "comply_refuse_detection",
                "label": "REFUSED",
                "score": -1.2,
                "p_complied": 0.23,
                "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
                "probe_model": "Qwen/Qwen2.5-1.5B-Instruct",
                "claim_ceiling": POST_HOC_WINDOW_CLAIM_CEILING,
            }
        ],
        model_id="Qwen/Qwen2.5-1.5B-Instruct",
        evidence_packet_trace_id="trace-5",
    )

    assert payload["status"] == "present"
    assert payload["label"] == "REFUSED"
    assert payload["score"] == -1.2
    assert payload["claim_level"] == "detection_only_post_hoc"


def test_unavailable_payload_carries_detection_claim_ceiling():
    payload = build_unavailable_comply_refuse_detection(
        reason="no compatible activation window",
        evidence_packet_trace_id="trace-6",
        model_id="EleutherAI/pythia-160m",
    )

    assert payload["status"] == "unavailable"
    assert payload["model_id"] == "EleutherAI/pythia-160m"
    assert "DETECTION ONLY" in payload["claim_ceiling"]
    assert payload["verdict_effect"] == "none_shadow_only"
