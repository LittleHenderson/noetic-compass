"""Probe runner — stub at milestone 1.

At milestone 2 this module owns the forward-hook registration: residual
stream taps, MLP post-activation taps, attention pattern dumps, logit
capture. Each probe is a context manager that returns the captured tensors
to the pythia_runner per-token.

For now it just exposes a placeholder so the schema imports resolve.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..schemas.methods import LiveMethodConfig, WIRED_LIVE_METHODS

ProbeName = Literal[
    "active_trace",
    "blindspots_f1",
    "mode7_attribution",
    "confidence_margin",
]


DEFAULT_PROBES: tuple[ProbeName, ...] = (
    "active_trace",
    "blindspots_f1",
    "mode7_attribution",
    "confidence_margin",
)


def resolve_probes(requested: list[ProbeName]) -> tuple[ProbeName, ...]:
    """Empty request = default pipeline. Explicit list = only those probes."""
    if not requested:
        return DEFAULT_PROBES
    # Preserve user order, dedupe.
    seen: set[ProbeName] = set()
    out: list[ProbeName] = []
    for p in requested:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return tuple(out)


FOUNDATION_AXES: tuple[str, ...] = ("Noetic", "Domain", "Drive", "Register")
DRIVE_IDS: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
VERIFICATION_MODES: tuple[str, ...] = (
    "BALANCED",
    "HIGH_PRECISION",
    "MAX_COVERAGE_TRIAGE",
)


@dataclass(frozen=True)
class RuntimeProbeConfig:
    """Resolved worker-side knobs that alter emitted runtime behavior."""

    active_methods: frozenset[str]
    foundation_axis: str
    foundation_layer_range: tuple[int, ...]
    foundation_top_k: int
    rpm_pathway_nodes: tuple[str, ...]
    rpm_strictness_threshold: float
    rpm_emit_attention: bool
    blindspot_scope: str
    blindspot_drive: str
    blindspot_layer_range: tuple[int, ...]
    verification_mode: str

    def is_active(self, method_id: str) -> bool:
        return method_id in self.active_methods


def _enabled_method_configs(
    method_configs: dict[str, LiveMethodConfig],
) -> dict[str, LiveMethodConfig]:
    if method_configs:
        return {
            method_id: config
            for method_id, config in method_configs.items()
            if config.enabled and method_id in WIRED_LIVE_METHODS
        }
    return {method_id: LiveMethodConfig() for method_id in WIRED_LIVE_METHODS}


def _float_knob(
    knobs: dict[str, object],
    key: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    raw = knobs.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = default
    return min(max(value, minimum), maximum)


def _int_knob(
    knobs: dict[str, object],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw = knobs.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return min(max(value, minimum), maximum)


def _bool_knob(knobs: dict[str, object], key: str, default: bool) -> bool:
    raw = knobs.get(key, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return bool(raw)


def _enum_knob(
    knobs: dict[str, object],
    key: str,
    default: str,
    allowed: tuple[str, ...],
) -> str:
    raw = str(knobs.get(key, default))
    return raw if raw in allowed else default


def _layer_range(
    knobs: dict[str, object],
    key: str,
    n_layers: int,
) -> tuple[int, ...]:
    raw = knobs.get(key, [])
    if raw is None or raw == []:
        return tuple(range(n_layers))
    if not isinstance(raw, list):
        raw = [raw]

    layers: set[int] = set()
    for item in raw:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= value < n_layers:
            layers.add(value)
    if not layers:
        return tuple(range(n_layers))
    return tuple(sorted(layers))


def resolve_runtime_config(
    method_configs: dict[str, LiveMethodConfig],
    *,
    n_layers: int,
) -> RuntimeProbeConfig:
    """Resolve UI method knobs into concrete runtime behavior.

    Empty method_configs preserves the milestone-1 default by enabling all
    worker-wired methods with defaults. Explicit configs are authoritative:
    disabled methods do not emit their corresponding runtime artifacts.
    """

    enabled = _enabled_method_configs(method_configs)
    active = frozenset(enabled)

    foundation = enabled.get("foundation_probe", LiveMethodConfig()).knobs
    rpm = enabled.get("rpm_gate_check", LiveMethodConfig()).knobs
    blindspot = enabled.get("blindspot_detection", LiveMethodConfig()).knobs
    verification = enabled.get("verification_stack", LiveMethodConfig()).knobs

    return RuntimeProbeConfig(
        active_methods=active,
        foundation_axis=_enum_knob(foundation, "axis", "Drive", FOUNDATION_AXES),
        foundation_layer_range=_layer_range(foundation, "layer_range", n_layers),
        foundation_top_k=_int_knob(
            foundation,
            "top_k",
            8,
            minimum=1,
            maximum=64,
        ),
        rpm_pathway_nodes=tuple(
            str(node)
            for node in rpm.get("pathway_nodes", ["A0", "D1", "W1", "P1"])
            if isinstance(rpm.get("pathway_nodes", []), list)
        )
        or ("A0", "D1", "W1", "P1"),
        rpm_strictness_threshold=_float_knob(
            rpm,
            "strictness_threshold",
            0.75,
            minimum=0.0,
            maximum=1.0,
        ),
        rpm_emit_attention=_bool_knob(rpm, "emit_attention", False),
        blindspot_scope=_enum_knob(
            blindspot,
            "scope",
            "all_7",
            ("one_drive", "all_7"),
        ),
        blindspot_drive=_enum_knob(blindspot, "drive", "F1", DRIVE_IDS),
        blindspot_layer_range=_layer_range(blindspot, "layer_range", n_layers),
        verification_mode=_enum_knob(
            verification,
            "mode",
            "BALANCED",
            VERIFICATION_MODES,
        ),
    )
