"""Mode 7 Network Tracer / Mechanistic Interpretability surface.

Public API for inspecting why a CAS-Native structured prediction was produced.
See ``docs/working/mode_7_network_tracer_spec_2026_05_04.md`` for the full spec.

The package re-exports its public surface lazily to avoid import-time work
during test collection (some tests run before the ``cas_native`` package alias
is set up by the parent conftest). Consumers can use either::

    from cas_native.trace import trace_prediction, render_trace_markdown

or the explicit submodule path::

    from cas_native.trace.mechanistic import trace_prediction
"""

from __future__ import annotations

__all__ = [
    "MechanisticTrace",
    "SCHEMA_VERSION",
    "render_trace_json",
    "render_trace_markdown",
    "trace_prediction",
    "ActivationCapture",
    "compute_with_hooks",
    "compute_capacity_allocation",
    "compute_per_token_attribution",
    "summarize_activations",
    "LiveTrace",
    "HeadInfo",
    "LayerActivation",
    "capture_live_trace",
    "GenerationTrace",
    "GenerationTraceCapture",
    "NearestNeighborIndex",
    "TokenStep",
    "capture_generation_trace",
    "live_cas_grounding_score",
    "trace_to_dict",
]


def __getattr__(name: str):  # PEP 562 lazy attribute access
    if name in {
        "MechanisticTrace",
        "SCHEMA_VERSION",
        "render_trace_json",
        "render_trace_markdown",
        "trace_prediction",
    }:
        from cas_native.trace import mechanistic  # noqa: WPS433

        return getattr(mechanistic, name)
    if name in {"ActivationCapture", "compute_with_hooks"}:
        from cas_native.trace import activations  # noqa: WPS433

        return getattr(activations, name)
    if name in {"compute_capacity_allocation", "compute_per_token_attribution"}:
        from cas_native.trace import attribution  # noqa: WPS433

        return getattr(attribution, name)
    if name == "summarize_activations":
        from cas_native.trace import network_summary  # noqa: WPS433

        return network_summary.summarize_activations
    if name in {"LiveTrace", "HeadInfo", "LayerActivation", "capture_live_trace"}:
        from cas_native.trace import live_capture  # noqa: WPS433

        return getattr(live_capture, name)
    if name in {
        "GenerationTrace",
        "GenerationTraceCapture",
        "NearestNeighborIndex",
        "TokenStep",
        "capture_generation_trace",
        "live_cas_grounding_score",
        "trace_to_dict",
    }:
        from cas_native.trace import generation_trace  # noqa: WPS433

        return getattr(generation_trace, name)
    raise AttributeError(f"module 'cas_native.trace' has no attribute {name!r}")
