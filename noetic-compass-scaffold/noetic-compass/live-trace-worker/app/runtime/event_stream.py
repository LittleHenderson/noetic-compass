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
from .model_loader import get_loaded_model
from .probe_runner import resolve_probes

logger = logging.getLogger(__name__)


# Cover sets used in BOTH demo and real modes — the F1 (Unity) drive's
# four-register footprint. v0.1 ships hardcoded covers; live-derivation
# of covers is a v0.2 follow-up (needs the harness probe pipeline).
F1_COVER_DEMO: dict[str, list[str]] = {
    "F1A": ["L3N142", "L3N518", "L5N91", "L7N2204"],
    "F1T": ["L4N336", "L6N1011", "L9N2782"],
    "F1f": ["L5N1492", "L8N87", "L11N305"],
    "F1E": ["L2N640", "L6N1872", "L10N2415"],
}


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
    _ = resolve_probes(req.probes)
    yield NeuronCoversEvent(per_class_neuron_covers=F1_COVER_DEMO)

    seed = req.seed if req.seed is not None else 1234
    rng = random.Random(seed)
    tokens = _tokenise_whitespace(req.prompt)
    max_new = min(req.max_new_tokens, 24)
    for i in range(max_new):
        tok = tokens[i % len(tokens)]
        yield TokenEvent(
            token_index=i,
            token=tok,
            top_activated_neurons=_fake_neurons(rng, loaded.manifest.model_arch.n_layers),
            mode7_attribution=_fake_mode7(rng, i),
            confidence=round(rng.uniform(0.55, 0.95), 3),
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
    yield NeuronCoversEvent(per_class_neuron_covers=F1_COVER_DEMO)

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
