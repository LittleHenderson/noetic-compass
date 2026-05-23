"""Live alpha cover sets used by blindspot overlays and eraser hooks."""

from __future__ import annotations

import re
from dataclasses import dataclass


F1_COVER: dict[str, list[str]] = {
    "F1A": ["L3N142", "L3N518", "L5N91", "L7N2204"],
    "F1T": ["L4N336", "L6N1011", "L9N2782"],
    "F1f": ["L5N1492", "L8N87", "L11N305"],
    "F1E": ["L2N640", "L6N1872", "L10N2415"],
}

COVER_LIBRARY: dict[str, dict[str, list[str]]] = {
    "F1": F1_COVER,
}

_COORD_RE = re.compile(r"^L(\d+)N(\d+)$")


@dataclass(frozen=True)
class CoverCoord:
    layer: int
    index: int


def cover_for_drive(drive: str) -> dict[str, list[str]]:
    """Return the calibrated cover classes for a live-supported drive."""
    return COVER_LIBRARY.get(drive, {})


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
