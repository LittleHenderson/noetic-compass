"""Deployment authority levels: capability is not permission."""

from __future__ import annotations

from typing import Dict, List

LEVELS: List[Dict] = [
    {"level": "A0", "meaning": "design and simulation only"},
    {"level": "A1", "meaning": "shadow mode: observes but cannot affect output"},
    {"level": "A2", "meaning": "advises or flags for a human"},
    {"level": "A3", "meaning": "executes only after human approval"},
    {"level": "A4", "meaning": "bounded autonomous action within explicit permissions"},
    {"level": "A5", "meaning": "broader autonomous operation with continuous supervision and rollback"},
]


def validate(level: str) -> bool:
    return any(item["level"] == level for item in LEVELS)
