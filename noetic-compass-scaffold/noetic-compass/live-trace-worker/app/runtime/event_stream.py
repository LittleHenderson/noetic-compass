"""Event stream — dispatches real vs fake based on whether weights are loaded.

M1: fake-only.
M2: real Pythia takes over WHENEVER ``get_loaded_model().is_real`` is True;
fake remains the fallback for demo mode (no torch, no GPU, or
LIVE_TRACE_DEMO_MODE=1).

Cockpit invariant: manifest.is_real_model in the FIRST event tells the UI
which mode it's looking at. The UI MUST surface this in its provenance
badge — "Live · actual weights" only when is_real_model = True.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import AsyncIterator

from ..schemas.events import (
    CompleteEvent,
    ErrorEvent,
    LiveTraceEvent,
    ManifestEvent,
    Mode7Edge,
    NeuronActivation,
    NeuronCoversEvent,
    TokenEvent,
)
from ..schemas.requests import CreateSessionRequest
from .cover_library import cover_members_for_drive
from .model_loader import get_loaded_model
from .probe_runner import resolve_probes

logger = logging.getLogger(__name__)


def _knobs(req: CreateSessionRequest) -> dict:
    raw = req.method_config.get("knobs", {}) if req.method_config else {}
    return raw if isinstance(raw, dict) else {}


def _selected_drive(req: CreateSessionRequest) -> str:
    knobs = _knobs(req)
    for method_id, key in (
        ("drive_local_eraser", "drive"),
        ("sparse_neuron_cover", "target_class"),
        ("blindspot_detection", "scope"),
    ):
        method_knobs = knobs.get(method_id, {})
        if isinstance(method_knobs, dict):
            val = method_knobs.get(key)
            if isinstance(val, str) and val.startswith("F"):
                return val
    return "F1"


def _cover_event(req: CreateSessionRequest) -> NeuronCoversEvent:
    probes = _requested_probes(req)
    if "blindspots_f1" not in probes:
        return NeuronCoversEvent(per_class_neuron_covers={})
    return NeuronCoversEvent(
        per_class_neuron_covers=cover_members_for_drive(_selected_drive(req)),
    )


def _requested_probes(req: CreateSessionRequest) -> set[str]:
    if req.method_config and "enabled_methods" in req.method_config and not req.probes:
        return set()
    return set(resolve_probes(req.probes))


def _enabled_methods(req: CreateSessionRequest) -> set[str]:
    raw = req.method_config.get("enabled_methods", []) if req.method_config else []
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw}


def _inversion_risk(
    req: CreateSessionRequest,
    confidence: float,
    activations: list[NeuronActivation],
) -> float | None:
    if "inversion_scan" not in _enabled_methods(req):
        return None
    threshold = 0.0
    method_knobs = _knobs(req).get("inversion_scan", {})
    if isinstance(method_knobs, dict):
        try:
            threshold = float(method_knobs.get("severity_threshold", 0.0))
        except (TypeError, ValueError):
            threshold = 0.0
    activation_pressure = min(max((abs(a.activation) for a in activations), default=0.0), 1.0)
    confidence_pressure = 1.0 - confidence
    risk = max(0.0, min(1.0, (activation_pressure * 0.6) + (confidence_pressure * 0.4)))
    return round(risk, 3) if risk >= threshold else 0.0


# ---------------------------------------------------------------------------
# Demo-mode (M1 carry-over) — fake-but-schema-valid trace.
# Kept here both for fallback and as a sanity-check baseline.
# ---------------------------------------------------------------------------


def _fake_neurons(rng: random.Random, n_layers: int) -> list[NeuronActivation]:
    out: list[NeuronActivation] = []
    for _ in range(8):
        layer = rng.randint(0, n_layers - 1)
        index = rng.randint(0, 3071)
        activation = rng.uniform(0.30, 0.95)
        out.append(NeuronActivation(layer=layer, index=index, activation=activation))
    return out


def _fake_mode7(rng: random.Random, current: int) -> list[Mode7Edge]:
    if current == 0:
        return [Mode7Edge(from_token_index=None, to_token_index=0, weight=1.0)]
    n_edges = min(current, 3)
    targets = rng.sample(range(current), n_edges)
    return [
        Mode7Edge(
            from_token_index=t,
            to_token_index=current,
            weight=round(rng.uniform(0.25, 0.95), 3),
        )
        for t in targets
    ]


def _tokenise_whitespace(prompt: str) -> list[str]:
    pieces: list[str] = []
    cursor = 0
    for raw in prompt.split():
        idx = prompt.find(raw, cursor)
        if idx > cursor:
            pieces.append(prompt[cursor:idx] + raw)
        else:
            pieces.append(raw)
        cursor = idx + len(raw)
    if not pieces:
        return [prompt]
    return pieces


async def stream_fake_trace(req: CreateSessionRequest) -> AsyncIterator[LiveTraceEvent]:
    """Demo-mode trace — schema-valid, deterministic under seed, no real model."""
    loaded = get_loaded_model()
    yield ManifestEvent(manifest=loaded.manifest)
    probes = _requested_probes(req)
    yield _cover_event(req)

    seed = req.seed if req.seed is not None else 1234
    rng = random.Random(seed)
    tokens = _tokenise_whitespace(req.prompt)
    max_new = min(req.max_new_tokens, 24)
    for i in range(max_new):
        tok = tokens[i % len(tokens)]
        fake_neurons = _fake_neurons(rng, loaded.manifest.model_arch.n_layers)
        fake_confidence = round(rng.uniform(0.55, 0.95), 3)
        yield TokenEvent(
            token_index=i,
            token=tok,
            top_activated_neurons=fake_neurons
            if "active_trace" in probes
            else [],
            mode7_attribution=_fake_mode7(rng, i)
            if "mode7_attribution" in probes
            else [],
            confidence=fake_confidence
            if "confidence_margin" in probes
            else None,
            inversion_risk=_inversion_risk(req, fake_confidence, fake_neurons),
        )
        await asyncio.sleep(0.04)
    yield CompleteEvent(total_tokens=max_new)


# ---------------------------------------------------------------------------
# Real Pythia trace — drives event_stream off pythia_runner.run_pythia.
# ---------------------------------------------------------------------------


async def stream_real_trace(req: CreateSessionRequest) -> AsyncIterator[LiveTraceEvent]:
    """Real-model trace using the loaded Pythia + probe hooks."""
    loaded = get_loaded_model()
    if not loaded.is_real:
        # Defensive: if someone routes here when weights aren't loaded,
        # emit an error event so the UI falls back cleanly.
        yield ErrorEvent(
            message="Real Pythia runner invoked but model is not loaded.",
            retryable=False,
        )
        return

    yield ManifestEvent(manifest=loaded.manifest)
    yield _cover_event(req)

    # Import locally so demo mode can import this module without torch.
    from .pythia_runner import run_pythia

    n_layers = loaded.manifest.model_arch.n_layers
    emitted = 0
    try:
        async for token_payload in run_pythia(req, loaded.model, loaded.tokenizer, n_layers):
            yield TokenEvent(**token_payload)
            emitted += 1
    except Exception as exc:  # pragma: no cover — generation-time failures
        logger.exception("stream_real_trace: pythia_runner raised")
        yield ErrorEvent(
            message=f"Live generation failed: {exc!r}. Fall back to REPLAY.",
            retryable=True,
        )
        return

    yield CompleteEvent(total_tokens=emitted)


# ---------------------------------------------------------------------------
# Public entry — picks real vs fake based on whether weights are loaded.
# ---------------------------------------------------------------------------


async def stream_trace(req: CreateSessionRequest) -> AsyncIterator[LiveTraceEvent]:
    """Dispatcher: real Pythia if loaded, fake otherwise.

    Routes / tests that want to force one mode can call stream_real_trace
    or stream_fake_trace directly.
    """
    loaded = get_loaded_model()
    if loaded.is_real:
        async for event in stream_real_trace(req):
            yield event
    else:
        async for event in stream_fake_trace(req):
            yield event
