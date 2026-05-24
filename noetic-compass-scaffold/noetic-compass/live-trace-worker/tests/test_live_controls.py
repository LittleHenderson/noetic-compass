from __future__ import annotations

import asyncio

from app.runtime.event_stream import stream_fake_trace
from app.schemas.events import NeuronCoversEvent, TokenEvent
from app.schemas.requests import CreateSessionRequest


def _drain(req: CreateSessionRequest):
    async def _run():
        return [event async for event in stream_fake_trace(req)]

    return asyncio.run(_run())


def test_explicit_empty_live_controls_emit_no_probe_payloads():
    req = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        probes=[],
        method_config={"enabled_methods": [], "knobs": {}},
    )
    events = _drain(req)
    cover = next(event for event in events if isinstance(event, NeuronCoversEvent))
    token = next(event for event in events if isinstance(event, TokenEvent))
    assert cover.per_class_neuron_covers == {}
    assert token.top_activated_neurons == []
    assert token.mode7_attribution == []
    assert token.confidence is None
    assert token.inversion_risk is None


def test_live_controls_enable_only_selected_probe_payloads():
    req = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        probes=["blindspots_f1", "confidence_margin"],
        method_config={
            "enabled_methods": ["blindspot_detection", "verification_stack"],
            "knobs": {"blindspot_detection": {"scope": "F1"}},
        },
    )
    events = _drain(req)
    cover = next(event for event in events if isinstance(event, NeuronCoversEvent))
    token = next(event for event in events if isinstance(event, TokenEvent))
    assert "F1A" in cover.per_class_neuron_covers
    assert token.top_activated_neurons == []
    assert token.mode7_attribution == []
    assert token.confidence is not None
    assert token.inversion_risk is None


def test_live_controls_known_but_uncalibrated_blindspot_scope_emits_no_covers():
    """The alpha live worker accepts the method envelope, but covers are F1-only."""
    req = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        probes=["blindspots_f1"],
        method_config={
            "enabled_methods": ["blindspot_detection"],
            "knobs": {"blindspot_detection": {"scope": "F2"}},
        },
    )
    events = _drain(req)
    cover = next(event for event in events if isinstance(event, NeuronCoversEvent))
    assert cover.per_class_neuron_covers == {}


def test_inversion_scan_emits_explicit_risk_side_channel():
    req = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        probes=["active_trace", "confidence_margin"],
        method_config={
            "enabled_methods": ["inversion_scan"],
            "knobs": {"inversion_scan": {"severity_threshold": 0.0}},
        },
    )
    events = _drain(req)
    token = next(event for event in events if isinstance(event, TokenEvent))
    assert token.inversion_risk is not None
    assert 0.0 <= token.inversion_risk <= 1.0
