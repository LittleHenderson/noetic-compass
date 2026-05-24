"""Prove that method-panel knobs measurably change worker output.

The fixture in ``conftest.py`` forces demo mode (``LIVE_TRACE_DEMO_MODE=1``),
which means ``stream_trace`` routes to ``stream_fake_trace``. The fake
stream is wired through the *same* ``knob_resolution.resolve_knobs``
helper the real ``pythia_runner`` uses; if a refactor ever loses the
plumbing between ``method_config`` and the runner, the same divergence
that broke the real path will also break here.

Each test:

  1. Builds two ``CreateSessionRequest`` payloads that differ ONLY in
     one knob.
  2. Drains the resulting event sequence under the same seed.
  3. Asserts the worker output diverges (different token-event
     contents) on a metric specific to that knob.
  4. Cross-checks the ``KnobResolutionEvent`` echo so the cockpit's
     Knob Diagnostic disclosure cannot mis-report what the worker
     used.

Tests intentionally use ``stream_fake_trace`` so they run without
torch. The real-model path is covered by the existing
``test_real_mode_dispatch.py`` (which now also asserts the
``knob_resolution`` event slot).
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.runtime.event_stream import stream_fake_trace
from app.schemas.events import (
    KnobResolutionEvent,
    NeuronCoversEvent,
    TokenEvent,
)
from app.schemas.requests import CreateSessionRequest


def _drain(req: CreateSessionRequest) -> list[Any]:
    async def _run() -> list[Any]:
        return [event async for event in stream_fake_trace(req)]

    return asyncio.run(_run())


def _token_events(events: list[Any]) -> list[TokenEvent]:
    return [e for e in events if isinstance(e, TokenEvent)]


def _knob_event(events: list[Any]) -> KnobResolutionEvent:
    return next(e for e in events if isinstance(e, KnobResolutionEvent))


def _cover_event(events: list[Any]) -> NeuronCoversEvent:
    return next(e for e in events if isinstance(e, NeuronCoversEvent))


# ---------------------------------------------------------------------------
# foundation_probe.top_k — controls how many neurons appear per token.
# ---------------------------------------------------------------------------


def test_foundation_top_k_changes_per_token_neuron_count():
    """top_k=4 must emit FEWER top_activated_neurons per token than top_k=8."""
    base = {
        "prompt": "hello world",
        "seed": 13,
        "max_new_tokens": 4,
        "probes": ["active_trace"],
    }

    req_low = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["foundation_probe"],
            "knobs": {"foundation_probe": {"top_k": 4}},
        },
    )
    req_high = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["foundation_probe"],
            "knobs": {"foundation_probe": {"top_k": 8}},
        },
    )

    low_tokens = _token_events(_drain(req_low))
    high_tokens = _token_events(_drain(req_high))

    assert low_tokens, "expected token events for low-k run"
    assert high_tokens, "expected token events for high-k run"

    low_counts = [len(t.top_activated_neurons) for t in low_tokens]
    high_counts = [len(t.top_activated_neurons) for t in high_tokens]

    assert all(c == 4 for c in low_counts), low_counts
    assert all(c == 8 for c in high_counts), high_counts
    assert low_counts != high_counts


def test_foundation_top_k_echoed_in_resolved_knobs():
    """Knob the cockpit sees in ``resolved_knobs`` matches what was sent."""
    req = CreateSessionRequest(
        prompt="hi",
        seed=1,
        max_new_tokens=1,
        probes=["active_trace"],
        method_config={
            "enabled_methods": ["foundation_probe"],
            "knobs": {"foundation_probe": {"top_k": 4}},
        },
    )
    knob_event = _knob_event(_drain(req))
    assert knob_event.resolved_knobs["foundation_probe"]["top_k"] == 4


# ---------------------------------------------------------------------------
# foundation_probe.layer_range — controls WHICH layers can contribute neurons.
# ---------------------------------------------------------------------------


def test_foundation_layer_range_constrains_returned_layers():
    """A [0,3] window restricts neuron layer ids to {0,1,2,3} only."""
    base = {
        "prompt": "alpha beta gamma delta",
        "seed": 7,
        "max_new_tokens": 6,
        "probes": ["active_trace"],
    }

    req_low = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["foundation_probe"],
            "knobs": {
                "foundation_probe": {"top_k": 8, "layer_range": [0, 3]},
            },
        },
    )
    req_high = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["foundation_probe"],
            "knobs": {
                "foundation_probe": {"top_k": 8, "layer_range": [6, 11]},
            },
        },
    )

    low_tokens = _token_events(_drain(req_low))
    high_tokens = _token_events(_drain(req_high))

    low_layers = {n.layer for tok in low_tokens for n in tok.top_activated_neurons}
    high_layers = {n.layer for tok in high_tokens for n in tok.top_activated_neurons}

    assert low_layers, low_layers
    assert high_layers, high_layers
    assert low_layers.issubset({0, 1, 2, 3}), low_layers
    assert high_layers.issubset({6, 7, 8, 9, 10, 11}), high_layers
    # Sets must not overlap — the two windows partition the layer axis.
    assert low_layers.isdisjoint(high_layers)


def test_foundation_layer_range_echo_expands_to_inclusive_list():
    """Cockpit echo carries the EXPANDED list of layers the worker used."""
    req = CreateSessionRequest(
        prompt="x",
        seed=1,
        max_new_tokens=1,
        probes=["active_trace"],
        method_config={
            "enabled_methods": ["foundation_probe"],
            "knobs": {
                "foundation_probe": {"top_k": 8, "layer_range": [2, 5]},
            },
        },
    )
    knob_event = _knob_event(_drain(req))
    assert knob_event.resolved_knobs["foundation_probe"]["layer_range"] == [
        2,
        3,
        4,
        5,
    ]


# ---------------------------------------------------------------------------
# rpm_gate_check.strictness_threshold — filters Mode 7 edges.
# ---------------------------------------------------------------------------


def test_rpm_strictness_threshold_drops_weak_mode7_edges():
    """A high threshold must remove edges that a low threshold kept."""
    base = {
        "prompt": "one two three four five",
        "seed": 21,
        "max_new_tokens": 6,
        "probes": ["mode7_attribution"],
    }

    req_lax = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["rpm_gate_check"],
            "knobs": {"rpm_gate_check": {"strictness_threshold": 0.0}},
        },
    )
    req_strict = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["rpm_gate_check"],
            "knobs": {"rpm_gate_check": {"strictness_threshold": 0.9}},
        },
    )

    lax_tokens = _token_events(_drain(req_lax))
    strict_tokens = _token_events(_drain(req_strict))

    lax_edges = sum(len(t.mode7_attribution) for t in lax_tokens)
    strict_edges = sum(len(t.mode7_attribution) for t in strict_tokens)

    # The lax run must carry STRICTLY MORE edges than the strict one.
    assert lax_edges > strict_edges, (lax_edges, strict_edges)

    # Every surviving strict edge must clear the 0.9 bar.
    for tok in strict_tokens:
        for edge in tok.mode7_attribution:
            assert edge.weight >= 0.9, edge


def test_rpm_strictness_threshold_echoed_and_clamped_into_unit_interval():
    """A 1.4 value clamps to 1.0 in the cockpit echo."""
    req = CreateSessionRequest(
        prompt="x",
        seed=1,
        max_new_tokens=1,
        probes=["mode7_attribution"],
        method_config={
            "enabled_methods": ["rpm_gate_check"],
            "knobs": {"rpm_gate_check": {"strictness_threshold": 1.4}},
        },
    )
    knob_event = _knob_event(_drain(req))
    assert knob_event.resolved_knobs["rpm_gate_check"]["strictness_threshold"] == 1.0


# ---------------------------------------------------------------------------
# blindspot_detection.drive — controls which cover set the cockpit overlay
# uses. ONLY F1 is calibrated in COVER_LIBRARY at v0.1; the test pivots
# F1-vs-non-library so the divergence is between "calibrated cover" and
# "no cover" (a deliberate decision documented in cover_library.py).
# ---------------------------------------------------------------------------


def test_blindspot_drive_f1_vs_uncalibrated_changes_cover_event():
    """F1 returns the calibrated cover; an uncalibrated drive returns empty.

    F2-F7 are intentionally absent from ``COVER_LIBRARY`` at v0.1.
    Documented behaviour: the cockpit's knob still echoes back, the
    blindspot overlay simply has nothing to paint. The cockpit's
    diagnostic disclosure surfaces ``cover_available: false`` so the
    user can see the worker resolved the knob but had no calibrated
    cover for it.
    """
    base = {
        "prompt": "hi",
        "seed": 1,
        "max_new_tokens": 1,
        "probes": ["blindspots_f1"],
    }

    f1_req = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["blindspot_detection"],
            "knobs": {"blindspot_detection": {"scope": "F1"}},
        },
    )
    f2_req = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["blindspot_detection"],
            "knobs": {"blindspot_detection": {"scope": "F2"}},
        },
    )

    f1_events = _drain(f1_req)
    f2_events = _drain(f2_req)

    f1_cover = _cover_event(f1_events).per_class_neuron_covers
    f2_cover = _cover_event(f2_events).per_class_neuron_covers

    assert "F1A" in f1_cover, f1_cover
    assert f2_cover == {}, f2_cover

    # Echo must report what the user asked for AND whether the cover
    # set was calibrated. ``cover_available`` is the diagnostic
    # disclosure's "✓/✗" signal.
    f1_knob = _knob_event(f1_events).resolved_knobs["blindspot_detection"]
    f2_knob = _knob_event(f2_events).resolved_knobs["blindspot_detection"]
    assert f1_knob == {"drive": "F1", "cover_available": True}
    assert f2_knob == {"drive": "F2", "cover_available": False}


# ---------------------------------------------------------------------------
# inversion_scan.severity_threshold — gates whether the runtime side-channel
# emits a non-zero risk value.
# ---------------------------------------------------------------------------


def test_inversion_severity_threshold_changes_risk_channel():
    """Above-threshold risk emits non-zero; max-threshold suppresses to 0.0."""
    base = {
        "prompt": "alpha beta",
        "seed": 5,
        "max_new_tokens": 3,
        "probes": ["active_trace", "confidence_margin"],
    }

    req_open = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["inversion_scan"],
            "knobs": {"inversion_scan": {"severity_threshold": 0.0}},
        },
    )
    req_strict = CreateSessionRequest(
        **base,
        method_config={
            "enabled_methods": ["inversion_scan"],
            "knobs": {"inversion_scan": {"severity_threshold": 1.0}},
        },
    )

    open_tokens = _token_events(_drain(req_open))
    strict_tokens = _token_events(_drain(req_strict))

    open_risks = [t.inversion_risk for t in open_tokens]
    strict_risks = [t.inversion_risk for t in strict_tokens]

    # Open threshold lets at least one positive risk reading through.
    assert any(r is not None and r > 0 for r in open_risks), open_risks
    # Strict threshold suppresses all of them to 0.0 (still not None,
    # because the method is enabled — distinguishes "filtered" from
    # "method off").
    assert all(r == 0.0 for r in strict_risks), strict_risks
    assert open_risks != strict_risks
