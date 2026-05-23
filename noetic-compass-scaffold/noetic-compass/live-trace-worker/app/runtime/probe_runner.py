"""Probe runner — stub at milestone 1.

At milestone 2 this module owns the forward-hook registration: residual
stream taps, MLP post-activation taps, attention pattern dumps, logit
capture. Each probe is a context manager that returns the captured tensors
to the pythia_runner per-token.

For now it just exposes a placeholder so the schema imports resolve.
"""

from __future__ import annotations

from typing import Literal

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
