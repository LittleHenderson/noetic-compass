"""Route A: the native symbolic CCB-L1 board (no foreign models).

Its 'training' is the seed lexicon and the hand-built grammar; its
competence boundary is typed - outside the fragment it refuses with a
located parse error, never a fabricated packet.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict

_CAS_ONLY = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_L1 = os.path.join(_CAS_ONLY, "CCB_L1_v0.1")
if _L1 not in sys.path:
    sys.path.insert(0, _L1)

from lang.grammar import ParseError  # noqa: E402
from lang.l1 import CCB_L1  # noqa: E402


def load_seed() -> Dict:
    path = os.path.join(_L1, "fixtures", "seed_lexicon.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class RouteA:
    name = "route_a_native_ccb_l1"
    description = ("CCB-L1 v0.1: hand-built lexicon + deterministic "
                   "grammar + unchanged kernel; no neural weights")

    def __init__(self) -> None:
        self.seed = load_seed()

    def _fresh(self) -> CCB_L1:
        # a fresh board per call: no cross-task discourse leakage
        return CCB_L1(self.seed)

    def parse(self, sentence: str) -> Dict:
        """Returns {"ok": packet} or {"refused": typed error}."""
        try:
            return {"ok": self._fresh().parse(sentence)}
        except ParseError as exc:
            return {"refused": {"error": "parse_error",
                                "word": exc.args[0],
                                "message": exc.message()}}

    def ask(self, sentence: str) -> Dict:
        """Returns {"ok": {status, answer}} or {"refused": ...}."""
        try:
            result = self._fresh().ask(sentence)
            return {"ok": {"status": result["kernel_status"],
                           "answer": result["answer"]}}
        except ParseError as exc:
            return {"refused": {"error": "parse_error",
                                "word": exc.args[0],
                                "message": exc.message()}}
