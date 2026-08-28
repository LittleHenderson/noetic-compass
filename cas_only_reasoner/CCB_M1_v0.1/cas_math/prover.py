"""The strategy generator: bounded deterministic search.

CAS governs the search - the prover explores rule applications in a
deterministic breadth-first order. It never decides validity: every
proof it returns must still pass the checker.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Tuple

from .expr import canonical, equal
from .rules import all_foci, apply_rule


def search(premise, target, rule_ids: List[str],
           max_depth: int = 4) -> Optional[List[Dict]]:
    """BFS over rule applications; first path reaching the target wins."""
    target_canon = canonical(target)
    start_sig = tuple(sorted(
        (m, str(c)) for m, c in canonical(premise).items()))
    queue = deque([(premise, [], start_sig)])
    seen = {start_sig}
    while queue:
        expr, path, sig = queue.popleft()
        if len(path) >= max_depth:
            continue
        for rule_id in sorted(rule_ids):
            for focus in sorted(all_foci(expr)):
                try:
                    nxt = apply_rule(rule_id, expr, focus)
                except Exception:
                    continue
                step = {"rule": rule_id, "focus": list(focus), "to": _to_json(nxt)}
                if equal(nxt, target):
                    return path + [step]
                nxt_sig = tuple(sorted(
                    (m, str(c)) for m, c in canonical(nxt).items()))
                if nxt_sig not in seen:
                    seen.add(nxt_sig)
                    queue.append((nxt, path + [step], nxt_sig))
    return None


def _to_json(expr) -> Dict:
    from .expr import to_json
    return to_json(expr)
