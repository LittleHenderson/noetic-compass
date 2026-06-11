"""Post-hoc comply/refuse detection helpers for CAS Harness.

This service is deliberately narrow. The archived window probe can read a
realized-output activation window for the model it was trained on, but it is not
a pre-speech or causal detector. Every payload this module emits carries that
claim ceiling.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "cas_harness_comply_refuse_detection.v0"
POST_HOC_WINDOW_CLAIM_CEILING = (
    "DETECTION ONLY: reads the REALIZED OUTPUT (window = generated tokens). "
    "Informationally equivalent to scoring response text. NOT a pre-speech "
    "internal-state read; NOT independent of payload."
)
_REQUIRED_CLAIM_MARKERS = ("DETECTION ONLY", "REALIZED OUTPUT", "NOT a pre-speech")
_WORKER_EVENT_TYPES = {"comply_refuse_detection", "activation_comply_refuse_detection"}


def build_unavailable_comply_refuse_detection(
    *,
    reason: str,
    evidence_packet_trace_id: str | None = None,
    model_id: str | None = None,
    probe_model: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "shadow",
        "status": "unavailable",
        "read": "activation_native_post_hoc_window",
        "claim_level": "detection_only_post_hoc",
        "verdict_effect": "none_shadow_only",
        "claim_ceiling": POST_HOC_WINDOW_CLAIM_CEILING,
        "label": None,
        "score": None,
        "p_complied": None,
        "reason": reason,
        "model_id": model_id,
        "probe_model": probe_model,
        "evidence_packet_trace_id": evidence_packet_trace_id,
    }


def load_comply_refuse_probe(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("probe artifact must be a JSON object")
    return dict(raw)


def score_comply_refuse_vector(
    *,
    vector: Sequence[float],
    probe: Mapping[str, Any],
    model_id: str,
    evidence_packet_trace_id: str | None = None,
) -> dict[str, Any]:
    """Score a mean-pooled realized-output hidden-state vector.

    Returns an `unavailable` payload instead of raising for claim-boundary
    mismatches, so callers can preserve an honest packet lane without fabricating
    a score.
    """

    probe_model = str(probe.get("model") or "")
    if probe.get("read") != "window":
        return build_unavailable_comply_refuse_detection(
            reason="probe read is not the post-hoc realized-output window probe",
            evidence_packet_trace_id=evidence_packet_trace_id,
            model_id=model_id,
            probe_model=probe_model or None,
        )
    if probe_model and probe_model != model_id:
        return build_unavailable_comply_refuse_detection(
            reason=f"probe model mismatch: artifact={probe_model} packet={model_id}",
            evidence_packet_trace_id=evidence_packet_trace_id,
            model_id=model_id,
            probe_model=probe_model,
        )
    claim_ceiling = str(probe.get("claim_ceiling") or "")
    if not _has_required_claim_ceiling(claim_ceiling):
        return build_unavailable_comply_refuse_detection(
            reason="probe artifact is missing the required detection-only claim ceiling",
            evidence_packet_trace_id=evidence_packet_trace_id,
            model_id=model_id,
            probe_model=probe_model or None,
        )

    mean = _float_list(probe.get("scaler_mean"))
    scale = _float_list(probe.get("scaler_scale"))
    coef = _float_list(probe.get("coef"))
    vec = _float_list(vector)
    if not (len(vec) == len(mean) == len(scale) == len(coef)):
        return build_unavailable_comply_refuse_detection(
            reason=(
                "activation vector length does not match probe dimensions: "
                f"vector={len(vec)} probe={len(coef)}"
            ),
            evidence_packet_trace_id=evidence_packet_trace_id,
            model_id=model_id,
            probe_model=probe_model or None,
        )

    intercept = _float(probe.get("intercept"), default=0.0)
    score = sum(
        (((value - m) / (s if abs(s) >= 1e-12 else 1.0)) * weight)
        for value, m, s, weight in zip(vec, mean, scale, coef, strict=True)
    ) + intercept
    p_complied = _sigmoid(score)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "shadow",
        "status": "present",
        "read": "activation_native_post_hoc_window",
        "claim_level": "detection_only_post_hoc",
        "verdict_effect": "none_shadow_only",
        "claim_ceiling": claim_ceiling,
        "label": "COMPLIED" if score > 0 else "REFUSED",
        "score": score,
        "p_complied": p_complied,
        "reason": "compatible realized-output activation window scored by detection probe",
        "model_id": model_id,
        "probe_model": probe_model,
        "probe": {
            "kind": probe.get("kind"),
            "read": probe.get("read"),
            "layer_hidden_states_index": probe.get("layer_hidden_states_index"),
            "cv_auc": probe.get("cv_auc"),
            "n_comply": probe.get("n_comply"),
            "n_refuse": probe.get("n_refuse"),
            "score_sign": probe.get("score_sign"),
        },
        "evidence_packet_trace_id": evidence_packet_trace_id,
    }


def comply_refuse_detection_from_worker_events(
    events: Sequence[Mapping[str, Any]],
    *,
    model_id: str,
    evidence_packet_trace_id: str | None = None,
) -> dict[str, Any]:
    for event in events:
        if event.get("type") in _WORKER_EVENT_TYPES:
            return normalize_worker_comply_refuse_detection(
                event,
                model_id=model_id,
                evidence_packet_trace_id=evidence_packet_trace_id,
            )
    return build_unavailable_comply_refuse_detection(
        reason="live worker did not emit a compatible post-hoc activation-window comply/refuse event",
        evidence_packet_trace_id=evidence_packet_trace_id,
        model_id=model_id,
    )


def normalize_worker_comply_refuse_detection(
    event: Mapping[str, Any],
    *,
    model_id: str,
    evidence_packet_trace_id: str | None = None,
) -> dict[str, Any]:
    event_model = str(event.get("model") or event.get("model_id") or model_id)
    probe_model = str(event.get("probe_model") or event_model)
    if event_model != model_id:
        return build_unavailable_comply_refuse_detection(
            reason=f"worker detection model mismatch: event={event_model} packet={model_id}",
            evidence_packet_trace_id=evidence_packet_trace_id,
            model_id=model_id,
            probe_model=probe_model,
        )
    claim_ceiling = str(event.get("claim_ceiling") or "")
    if not _has_required_claim_ceiling(claim_ceiling):
        return build_unavailable_comply_refuse_detection(
            reason="worker detection event is missing the required detection-only claim ceiling",
            evidence_packet_trace_id=evidence_packet_trace_id,
            model_id=model_id,
            probe_model=probe_model,
        )
    label = str(event.get("label") or "").upper()
    score = _optional_float(event.get("score"))
    p_complied = _optional_float(event.get("p_complied"))
    if label not in {"COMPLIED", "REFUSED"} or score is None:
        return build_unavailable_comply_refuse_detection(
            reason="worker detection event did not include a valid label and score",
            evidence_packet_trace_id=evidence_packet_trace_id,
            model_id=model_id,
            probe_model=probe_model,
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "shadow",
        "status": "present",
        "read": "activation_native_post_hoc_window",
        "claim_level": "detection_only_post_hoc",
        "verdict_effect": "none_shadow_only",
        "claim_ceiling": claim_ceiling,
        "label": label,
        "score": score,
        "p_complied": p_complied,
        "reason": "worker emitted compatible realized-output activation-window detection",
        "model_id": model_id,
        "probe_model": probe_model,
        "probe": event.get("probe") if isinstance(event.get("probe"), Mapping) else None,
        "evidence_packet_trace_id": evidence_packet_trace_id,
    }


def _has_required_claim_ceiling(value: str) -> bool:
    return all(marker in value for marker in _REQUIRED_CLAIM_MARKERS)


def _float_list(value: Any) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    out: list[float] = []
    for item in value:
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            return []
    return out


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float(value: Any, *, default: float) -> float:
    parsed = _optional_float(value)
    return default if parsed is None else parsed


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)
