"""CCB-P1: MINIMAL REPAIR - bounded, deterministic single-edit
program repair.

Candidate patches are SINGLE AST-node edits (a constant nudged by
one, a comparison relaxed or tightened, an arithmetic operator
swapped) - minimality is by construction: one node changes, nothing
else. Every candidate must pass the FULL battery the caller supplies
(public + negative + boundary + protected); the first fully-passing
candidate in deterministic order is the repair. A patch that merely
fixes the reproducing case is not accepted - that is the
compiling-bug-in-a-clean-shirt trap."""

from __future__ import annotations

import ast
import copy
from typing import Callable, Dict, List, Optional, Tuple

_CMP_SWAPS = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE,
              ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
_BIN_SWAPS = {ast.Add: ast.Sub, ast.Sub: ast.Add,
              ast.Mult: ast.Add, ast.FloorDiv: ast.Mod}


def _iter_nodes(tree: ast.AST) -> List[Tuple[int, ast.AST]]:
    return list(enumerate(ast.walk(tree)))


def candidate_patches(code: str,
                      focus_line: Optional[int] = None) -> List[str]:
    """Every single-edit variant, deterministic order. When the
    walk-down named a line, patches at that line come FIRST."""
    tree = ast.parse(code)
    patches: List[Tuple[int, str]] = []

    def emit(mutated: ast.AST, line: int) -> None:
        try:
            text = ast.unparse(ast.fix_missing_locations(mutated))
        except Exception:
            return
        if text != code and text not in [p for _, p in patches]:
            patches.append((line, text))

    nodes = _iter_nodes(tree)
    for index, node in nodes:
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Constant) \
                and isinstance(node.value, int) \
                and not isinstance(node.value, bool):
            for delta in (1, -1):
                mutated = copy.deepcopy(tree)
                target = list(ast.walk(mutated))[index]
                target.value = node.value + delta
                emit(mutated, line)
        elif isinstance(node, ast.Compare) and len(node.ops) == 1 \
                and type(node.ops[0]) in _CMP_SWAPS:
            mutated = copy.deepcopy(tree)
            target = list(ast.walk(mutated))[index]
            target.ops = [_CMP_SWAPS[type(node.ops[0])]()]
            emit(mutated, line)
        elif isinstance(node, ast.BinOp) \
                and type(node.op) in _BIN_SWAPS:
            mutated = copy.deepcopy(tree)
            target = list(ast.walk(mutated))[index]
            target.op = _BIN_SWAPS[type(node.op)]()
            emit(mutated, line)
        elif isinstance(node, ast.AugAssign) \
                and type(node.op) in _BIN_SWAPS:
            mutated = copy.deepcopy(tree)
            target = list(ast.walk(mutated))[index]
            target.op = _BIN_SWAPS[type(node.op)]()
            emit(mutated, line)
    if focus_line is not None:
        patches.sort(key=lambda item: (item[0] != focus_line,))
    return [text for _, text in patches]


def repair(code: str, battery: Callable[[str], Tuple[bool, Dict]],
           focus_line: Optional[int] = None,
           max_candidates: int = 200) -> Optional[Dict]:
    """The first single-edit patch that passes the WHOLE battery.
    Returns {'patched_code', 'candidates_tried'} or None."""
    tried = 0
    for candidate in candidate_patches(code, focus_line):
        if tried >= max_candidates:
            break
        tried += 1
        passed, _detail = battery(candidate)
        if passed:
            return {"patched_code": candidate,
                    "candidates_tried": tried}
    return None


def diff_lines(before: str, after: str) -> List[int]:
    """The 1-indexed lines that changed - the locality receipt."""
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    changed = []
    for index in range(max(len(before_lines), len(after_lines))):
        a = before_lines[index] if index < len(before_lines) else None
        b = after_lines[index] if index < len(after_lines) else None
        if a != b:
            changed.append(index + 1)
    return changed
