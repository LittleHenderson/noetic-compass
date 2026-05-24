"""Live alpha cover sets used by blindspot overlays and eraser hooks.

Cover sets answer "which neurons participate in this CAS class?". Each member
now also carries:

  * confidence — per-neuron probe score, in [0, 1] when available;
    ``None`` when no in-tree probe data backs the entry.
  * confidence_band — categorical bucket the UI shows (high/medium/low/
    unavailable); computed from the confidence value.
  * evidence_sources — which evidence streams agree (e.g. ``["probe",
    "ablation"]``).

Where DO real probe scores live? They DON'T live here yet. The closest
artifact in-tree is
``noetic-compass-scaffold/noetic-compass/research/cas_probe/cas_harness_public_evidence_manifest.json``
— but those are **aggregate panel claims** (78.6% Foundation probe, 3.57%
ablation chance, 98-99% verification stack accuracy at coverage). They do
NOT carry a per-neuron probe score for L3N142, L3N518, etc.

Until real per-neuron probes land, every member ships with
``confidence=None, confidence_band="unavailable", evidence_sources=[]``.
Per product spec, "unavailable" entries do NOT appear in the cockpit's
textual blindspot panel until probe data lands (the 3D red overlay
still draws — that's the spatial marker, not the interpretation).

When per-neuron probe scores DO land: emit them at this layer (e.g.
load ``research/cas_probe/per_neuron_probe_scores.json`` and merge by
label), feed the float into ``band_for_confidence`` from
``app.schemas.events``, and populate ``evidence_sources`` from whichever
runs agree. DO NOT INVENT confidence numbers — the "unavailable" band
exists for exactly this case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..schemas.events import NeuronCoverMember, band_for_confidence


F1_COVER: dict[str, list[str]] = {
    "F1A": ["L3N142", "L3N518", "L5N91", "L7N2204"],
    "F1T": ["L4N336", "L6N1011", "L9N2782"],
    "F1f": ["L5N1492", "L8N87", "L11N305"],
    "F1E": ["L2N640", "L6N1872", "L10N2415"],
}

COVER_LIBRARY: dict[str, dict[str, list[str]]] = {
    "F1": F1_COVER,
    # F2-F7 are NOT yet calibrated. The UI translates all 7 drives into
    # plain-English sentences, but no cover sets exist for them at the
    # worker level today. SUPPORTED_DRIVES (below) tells the UI exactly
    # which drives the worker will actually emit covers for, so the
    # cockpit can render an honest "F2-F7 calibration pending" header
    # rather than silently showing nothing.
}

# Source of truth for which drives have actual runtime cover data today.
# Kept separate from COVER_LIBRARY so a UI query can distinguish "we
# support this drive but there's no overlap in this trace" from "we
# don't support this drive yet at all." Add a drive ID to this tuple
# the same commit that adds its cover sets to COVER_LIBRARY — never
# advertise support that doesn't have data backing it.
SUPPORTED_DRIVES: tuple[str, ...] = ("F1",)

ALL_DRIVES: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")

_COORD_RE = re.compile(r"^L(\d+)N(\d+)$")


# --- Optional per-neuron probe-score registry ---------------------------
#
# When real probe scores land, populate this map either statically or via
# a loader (e.g. read research/cas_probe/per_neuron_probe_scores.json on
# worker startup). Until then it stays empty, and every cover member
# ships with confidence=None / band=unavailable.
#
# Schema:
#   { "L3N142": { "confidence": 0.84, "evidence_sources": ["probe",
#                                                          "ablation"] } }

_PROBE_SCORES: dict[str, dict[str, object]] = {}


@dataclass(frozen=True)
class CoverCoord:
    layer: int
    index: int


def cover_for_drive(drive: str) -> dict[str, list[str]]:
    """Return the raw string labels (legacy callers + eraser hooks).

    Kept separate from ``cover_members_for_drive`` so eraser intervention
    code that just wants L{layer}N{index} strings doesn't have to unpack
    typed records.
    """
    return COVER_LIBRARY.get(drive, {})


def _make_member(label: str) -> NeuronCoverMember:
    """Build a typed cover member, merging in probe scores when available.

    Falls back to confidence=None / band=unavailable when no per-neuron
    score exists for this label.
    """
    entry = _PROBE_SCORES.get(label)
    if entry is None:
        return NeuronCoverMember(
            label=label,
            confidence=None,
            confidence_band="unavailable",
            evidence_sources=[],
        )
    raw_conf = entry.get("confidence")
    confidence: float | None
    try:
        confidence = float(raw_conf) if raw_conf is not None else None
    except (TypeError, ValueError):
        confidence = None
    raw_sources = entry.get("evidence_sources", [])
    if isinstance(raw_sources, list):
        evidence_sources = [str(s) for s in raw_sources]
    else:
        evidence_sources = []
    return NeuronCoverMember(
        label=label,
        confidence=confidence,
        confidence_band=band_for_confidence(confidence),
        evidence_sources=evidence_sources,
    )


def cover_members_for_drive(drive: str) -> dict[str, list[NeuronCoverMember]]:
    """Return the calibrated cover classes as typed members.

    This is the shape the SSE ``neuron_covers`` event now emits. Each
    member carries label + confidence + band + evidence_sources.
    """
    raw = cover_for_drive(drive)
    return {
        cls: [_make_member(label) for label in labels]
        for cls, labels in raw.items()
    }


def coords_for_drive(drive: str) -> list[CoverCoord]:
    """Parse L{layer}N{index} labels into coordinates for runtime hooks."""
    out: list[CoverCoord] = []
    for labels in cover_for_drive(drive).values():
        for label in labels:
            match = _COORD_RE.match(label)
            if not match:
                continue
            out.append(CoverCoord(layer=int(match.group(1)), index=int(match.group(2))))
    return out
