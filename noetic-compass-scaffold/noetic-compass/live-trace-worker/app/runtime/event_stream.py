"""Event stream — milestone 1 emits a fake but schema-valid trace.

Per the locked plan: prove the interface end-to-end first. Real Pythia
forward lands in milestone 2 (pythia_runner.run_pythia).

The fake stream:
  1. Emits ModelManifest (so the UI knows what model it would have hit).
  2. Emits NeuronCoversEvent (so the Blindspots overlay has something to
     paint).
  3. Tokenises the prompt very crudely (whitespace split), then emits a
     TokenEvent per token with deterministic-looking activations + Mode 7
     arcs derived from a seeded RNG so demos are reproducible.
  4. Emits CompleteEvent.
"""

from __future__ import annotations

import asyncio
import random
from typing import AsyncIterator

from ..schemas.events import (
    CompleteEvent,
    LiveTraceEvent,
    ManifestEvent,
    Mode7Edge,
    NeuronActivation,
    NeuronCoversEvent,
    TokenEvent,
)
from ..schemas.requests import CreateSessionRequest
from .model_loader import get_manifest
from .probe_runner import resolve_probes


# Cover sets — same shape the offline trace uses for the F1 (Unity) drive's
# four-register footprint. UI paints these via the Blindspots overlay.
F1_COVER_DEMO: dict[str, list[str]] = {
    "F1A": ["L3N142", "L3N518", "L5N91", "L7N2204"],
    "F1T": ["L4N336", "L6N1011", "L9N2782"],
    "F1f": ["L5N1492", "L8N87", "L11N305"],
    "F1E": ["L2N640", "L6N1872", "L10N2415"],
}


def _fake_neurons(rng: random.Random, n_layers: int) -> list[NeuronActivation]:
    """Top-k activated neurons for a token — k random hits across layers."""
    out: list[NeuronActivation] = []
    for _ in range(8):
        layer = rng.randint(0, n_layers - 1)
        index = rng.randint(0, 3071)
        activation = rng.uniform(0.30, 0.95)
        out.append(NeuronActivation(layer=layer, index=index, activation=activation))
    return out


def _fake_mode7(rng: random.Random, current: int) -> list[Mode7Edge]:
    """Mode 7 attribution — current token points back to up to 3 earlier ones."""
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


def _tokenise(prompt: str) -> list[str]:
    """Whitespace tokeniser — milestone-1 stand-in for the real BPE.

    Real tokenisation arrives with milestone 2 when the actual tokenizer
    is loaded by model_loader. For schema validation + UI rendering this
    is sufficient (UI just gets strings).
    """
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
    """Emit a fake-but-schema-valid trace for the given request.

    Milestone 2 swaps the per-token block here for a real pythia_runner call;
    everything else (manifest, covers, completion) stays.
    """
    manifest = get_manifest(req.model_id)
    yield ManifestEvent(manifest=manifest)

    _ = resolve_probes(req.probes)  # Reserved for milestone 2.

    yield NeuronCoversEvent(per_class_neuron_covers=F1_COVER_DEMO)

    seed = req.seed if req.seed is not None else 1234
    rng = random.Random(seed)
    tokens = _tokenise(req.prompt)
    max_new = min(req.max_new_tokens, 24)
    for i in range(max_new):
        # Cycle through the prompt's own tokens — milestone-1 stand-in. The
        # real runner will produce continuations from Pythia.
        tok = tokens[i % len(tokens)]
        yield TokenEvent(
            token_index=i,
            token=tok,
            top_activated_neurons=_fake_neurons(rng, manifest.model_arch.n_layers),
            mode7_attribution=_fake_mode7(rng, i),
            confidence=round(rng.uniform(0.55, 0.95), 3),
        )
        # Small wait keeps SSE clients from getting one giant flush.
        await asyncio.sleep(0.04)

    yield CompleteEvent(total_tokens=max_new)
