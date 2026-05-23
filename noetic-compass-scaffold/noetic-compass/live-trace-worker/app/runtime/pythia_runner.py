"""Pythia-160M runner — stub at milestone 1.

This module will house the actual model forward pass + token streaming. At
milestone 2 we copy/curate the probe code from experiment/cas-probe-pythia
and wire it here.

Today it exposes the same async-generator interface the event_stream depends
on, so milestone-2 swaps a single import without touching event_stream.py.
"""

from __future__ import annotations

from typing import AsyncIterator

from ..schemas.requests import CreateSessionRequest


async def run_pythia(req: CreateSessionRequest) -> AsyncIterator[dict]:
    """Real-model token stream — not implemented at milestone 1.

    Milestone 2: load Pythia-160M, run forward with the requested probes
    attached, yield one dict per emitted token containing:
      - token_index
      - token
      - top_activated_neurons
      - mode7_attribution
      - confidence (softmax margin, normalised)
    """
    raise NotImplementedError(
        "Real Pythia runner lands in milestone 2 — use the fake event_stream "
        "for now (set LIVE_TRACE_USE_FAKE=1 or rely on the milestone-1 default)."
    )
    # Keep the type checker happy — this is unreachable.
    if False:
        yield {}
