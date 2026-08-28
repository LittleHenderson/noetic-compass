"""Time points and the temporal consistency checker.

before/after assertions must not contradict, directly or through
transitivity. Violations are typed.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class TimeError(Exception):
    pass


class Timeline:
    def __init__(self) -> None:
        self.before: Dict[str, List[str]] = {}

    def assert_order(self, earlier: str, later: str) -> None:
        """Declare earlier before later; contradiction raises TimeError."""
        if earlier == later:
            raise TimeError(f"time point '{earlier}' cannot precede itself")
        if self._reachable(later, earlier):
            raise TimeError(
                f"contradiction: '{earlier}' before '{later}' conflicts "
                f"with a declared path from '{later}' to '{earlier}'")
        self.before.setdefault(earlier, []).append(later)

    def _reachable(self, start: str, target: str) -> bool:
        stack = [start]
        seen = set()
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(self.before.get(node, []))
        return False

    def ordered_after(self, point: str) -> List[str]:
        out: List[str] = []
        stack = list(self.before.get(point, []))
        seen = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            out.append(node)
            stack.extend(self.before.get(node, []))
        return sorted(out)

    def at_or_before(self, point: str) -> List[str]:
        """point and every time point that precedes it, transitively."""
        preceding: List[str] = []
        for node in list(self.before):
            if node != point and self._reachable(node, point):
                preceding.append(node)
        return sorted(set(preceding + [point]))
