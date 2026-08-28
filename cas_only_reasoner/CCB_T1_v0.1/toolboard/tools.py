"""The tool registry: deterministic in-process tools.

Each tool declares its capability, permission level, and budget cost.
The exact calculator reuses CCB-M1's rational arithmetic - 1/3 stays
1/3, even inside a tool call.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, List, Optional

_CAS_ONLY = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_CCB_M1 = os.path.join(_CAS_ONLY, "CCB_M1_v0.1")
if _CCB_M1 not in sys.path:
    sys.path.insert(0, _CCB_M1)

from cas_math.exact import compare, parse_q, q_str  # noqa: E402


class ToolError(Exception):
    pass


class ToolUnknown(ToolError):
    pass


class AmbiguousToolNeed(ToolError):
    pass


class ToolPermissionDenied(ToolError):
    pass


class ToolProvenanceViolation(ToolError):
    """The intent's provenance breaks the contract: uncommitted outcome,
    unsealed trace, or a candidate branch trying to call a tool."""
    pass


class ToolBudgetExhausted(ToolError):
    pass


class ToolFailure(ToolError):
    pass


class ContraToolResult(ToolError):
    pass


def _calculator(need: Dict, facts: List[Dict]) -> Dict:
    """Compute the exact sum of two values referenced by a need like
    sum(?X, ?Y, ?S) where value(?X, n) facts exist."""
    x = need.get("args", [None, None])[0]
    y = need.get("args", [None, None])[1]
    values: Dict[str, str] = {}
    for fact in facts:
        if fact.get("pred") == "value" and len(fact.get("args", [])) == 2:
            values[fact["args"][0]] = fact["args"][1]
    if x not in values or y not in values:
        raise ToolFailure(f"calculator: missing value facts for {x}, {y}")
    total = parse_q(values[x]) + parse_q(values[y])
    result_fact = {"pred": "sum", "args": [x, y, q_str(total)]}
    # Tool contract: the exact sum AND its exact comparison against the
    # unit threshold 1, SYMMETRICALLY - gt, eq, or lt, whichever is true.
    # Never only the goal-friendly direction: the caller's goal must not
    # shape which facts the tool reports.
    relation = compare(total, parse_q("1"))
    comparison_fact = {"pred": relation, "args": [q_str(total), "1"]}
    return {
        "add_facts": [result_fact, comparison_fact],
        "note": f"exact sum of {values[x]} and {values[y]} is {q_str(total)}"
                f" ({relation} 1)",
    }


def _knowledge_query(need: Dict, facts: List[Dict]) -> Dict:
    """Return the facts matching a knowledge need (pred, args pattern)."""
    pred = need.get("pred")
    matched = [f for f in facts
               if f.get("pred") == pred and
               all(a == b or str(a).startswith("?") or str(b).startswith("?")
                   for a, b in zip(f.get("args", []),
                                   need.get("args", [])))]
    if not matched:
        raise ToolFailure(f"knowledge_query: no facts for {need}")
    return {"add_facts": matched, "note": f"queried {len(matched)} fact(s)"}


class Tool:
    def __init__(self, name: str, capability: str, permission: int,
                 cost: float, handler: Callable) -> None:
        self.name = name
        self.capability = capability
        self.permission = permission
        self.cost = cost
        self.handler = handler

    def call(self, need: Dict, facts: List[Dict]) -> Dict:
        return self.handler(need, facts)


class ToolRegistry:
    def __init__(self) -> None:
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def match(self, need: Dict) -> List[Tool]:
        """Tools whose capability matches the need's predicate."""
        return [t for t in self.tools.values()
                if t.capability == need.get("pred")]


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(Tool("calculator", "sum", permission=0, cost=1.0,
                           handler=_calculator))
    registry.register(Tool("knowledge_query", "has", permission=0,
                           cost=0.5, handler=_knowledge_query))
    return registry
