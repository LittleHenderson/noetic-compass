"""Fixture and golden loading for the conformance suite."""

from __future__ import annotations

import json
import os
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FIXTURE_NAMES = [
    "modux_ponens",
    "transitive_reasoning",
    "contradiction",
    "missing_information",
    "candidate_planning",
    "rpm_recursion",
]


def load_problem(name: str) -> Dict:
    path = os.path.join(ROOT, "fixtures", name, "problem.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_golden(name: str) -> Dict:
    path = os.path.join(ROOT, "golden", "expected", f"{name}.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def digest_path(name: str) -> str:
    return os.path.join(ROOT, "golden", "expected_traces", f"{name}.digest")


def load_digest(name: str) -> str:
    with open(digest_path(name), "r", encoding="utf-8") as fh:
        return fh.read().strip()


def freeze_trace_digests(packets: Dict[str, Dict]) -> None:
    """Freeze each fixture's trace digest into golden/expected_traces/.

    Run once after behavior stabilizes; afterwards the conformance suite
    requires identical digests, so any behavioral drift is caught.
    """
    out_dir = os.path.join(ROOT, "golden", "expected_traces")
    os.makedirs(out_dir, exist_ok=True)
    for name, packet in packets.items():
        with open(digest_path(name), "w", encoding="utf-8") as fh:
            fh.write(packet["trace_digest"])
