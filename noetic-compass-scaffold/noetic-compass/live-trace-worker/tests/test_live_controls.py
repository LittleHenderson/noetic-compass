from __future__ import annotations

import asyncio

from app.runtime.event_stream import stream_fake_trace
from app.runtime.pythia_runner import _eraser_intervention
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
        probes=["blindspot_covers", "confidence_margin"],
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


def test_live_controls_calibrated_f2_scope_emits_f2_covers():
    req = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        probes=["blindspot_covers"],
        method_config={
            "enabled_methods": ["blindspot_detection"],
            "knobs": {"blindspot_detection": {"scope": "F2"}},
        },
    )
    events = _drain(req)
    cover = next(event for event in events if isinstance(event, NeuronCoversEvent))
    assert set(cover.per_class_neuron_covers) == {"F2A", "F2T", "F2f", "F2E"}
    assert cover.per_class_neuron_covers["F2A"][0].confidence is not None


def test_live_controls_all_7_scope_emits_every_calibrated_drive():
    req = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        probes=["blindspot_covers"],
        method_config={
            "enabled_methods": ["blindspot_detection"],
            "knobs": {"blindspot_detection": {"scope": "all_7"}},
        },
    )
    events = _drain(req)
    cover = next(event for event in events if isinstance(event, NeuronCoversEvent))
    assert len(cover.per_class_neuron_covers) == 28
    assert "F1A" in cover.per_class_neuron_covers
    assert "F7E" in cover.per_class_neuron_covers


def test_drive_local_eraser_uses_selected_f5_runtime_cover():
    req = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        probes=["active_trace"],
        method_config={
            "enabled_methods": ["drive_local_eraser"],
            "knobs": {"drive_local_eraser": {"drive": "F5", "gain": 0.5}},
        },
    )
    intervention = _eraser_intervention(req)
    assert intervention is not None
    assert intervention.gain == 0.5
    assert intervention.coordinate_space == "mlp_intermediate_post_activation"
    assert intervention.execution_kind == "typed_test_fixture"
    assert intervention.source_kind == "typed_test_fixture"
    assert intervention.expected_coordinate_width == 3072
    assert intervention.expected_projected_output_width == 768
    assert (1, 142) in intervention.coords
    assert (5, 2346) in intervention.coords


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
