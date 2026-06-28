"""LIVE method configuration contract.

The Atlas method panel exposes more research controls than the milestone-1
worker can execute. This module is the worker-side authority for which method
configs are allowed to affect a LIVE run and which ones must be rejected instead
of being accepted as decorative payload.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RuntimeSupportStatus = Literal["wired_runtime_effect", "payload_only", "unsupported"]

WIRED_LIVE_METHODS: frozenset[str] = frozenset(
    {
        "foundation_probe",
        "rpm_gate_check",
        "blindspot_detection",
        "verification_stack",
    }
)

PAYLOAD_ONLY_METHODS: frozenset[str] = frozenset(
    {
        "evidence_packet",
        "spatial_evidence_layer",
    }
)

UNSUPPORTED_LIVE_METHODS: frozenset[str] = frozenset(
    {
        "inversion_scan",
        "sparse_neuron_cover",
        "drive_local_eraser",
    }
)

ALL_LIVE_METHODS: frozenset[str] = (
    WIRED_LIVE_METHODS | PAYLOAD_ONLY_METHODS | UNSUPPORTED_LIVE_METHODS
)

METHOD_EFFECTS: dict[str, str] = {
    "foundation_probe": "layer_range restricts activation layers; top_k controls emitted top_activated_neurons count",
    "rpm_gate_check": "strictness_threshold changes pass/fail; emit_attention controls attention_summary emission",
    "blindspot_detection": "scope/drive/layer_range control emitted neuron cover classes and coordinates",
    "verification_stack": "mode changes token verdict thresholds",
    "evidence_packet": "accepted only by artifact/export code, not by the live worker runtime",
    "spatial_evidence_layer": "accepted only by visual grounding artifact code, not by the live worker runtime",
    "inversion_scan": "no live worker inversion scanner is wired yet",
    "sparse_neuron_cover": "no live worker causal cover discovery is wired yet",
    "drive_local_eraser": "live steering is disabled until a safe runtime implementation exists",
}


class LiveMethodConfig(BaseModel):
    """A single method entry from the Atlas LIVE request."""

    enabled: bool = True
    knobs: dict[str, Any] = Field(default_factory=dict)


class MethodRuntimeStatus(BaseModel):
    """Explicit runtime support report emitted by the worker."""

    method_id: str
    enabled: bool
    status: RuntimeSupportStatus
    effect: str


def live_support_status(method_id: str) -> RuntimeSupportStatus | None:
    if method_id in WIRED_LIVE_METHODS:
        return "wired_runtime_effect"
    if method_id in PAYLOAD_ONLY_METHODS:
        return "payload_only"
    if method_id in UNSUPPORTED_LIVE_METHODS:
        return "unsupported"
    return None


def enabled_live_method_ids(
    method_configs: dict[str, LiveMethodConfig],
) -> set[str]:
    return {method_id for method_id, config in method_configs.items() if config.enabled}


def validate_live_method_configs(
    method_configs: dict[str, LiveMethodConfig],
) -> None:
    """Reject unknown or non-runtime methods when they are enabled for LIVE."""

    unknown = sorted(set(method_configs) - ALL_LIVE_METHODS)
    if unknown:
        raise ValueError(f"Unknown LIVE method(s): {', '.join(unknown)}")

    unavailable = [
        method_id
        for method_id in sorted(enabled_live_method_ids(method_configs))
        if live_support_status(method_id) != "wired_runtime_effect"
    ]
    if unavailable:
        details = [
            f"{method_id}={live_support_status(method_id)}"
            for method_id in unavailable
        ]
        raise ValueError(
            "Unsupported LIVE method(s): "
            + ", ".join(details)
            + ". Disable them or run them through their non-live artifact pipeline."
        )


def method_runtime_statuses(
    method_configs: dict[str, LiveMethodConfig],
) -> list[MethodRuntimeStatus]:
    """Classify every known method and mark which ones this request enabled."""

    enabled_ids = enabled_live_method_ids(method_configs) if method_configs else set(WIRED_LIVE_METHODS)
    out: list[MethodRuntimeStatus] = []
    for method_id in sorted(ALL_LIVE_METHODS):
        status = live_support_status(method_id)
        if status is None:
            continue
        out.append(
            MethodRuntimeStatus(
                method_id=method_id,
                enabled=method_id in enabled_ids,
                status=status,
                effect=METHOD_EFFECTS[method_id],
            )
        )
    return out
