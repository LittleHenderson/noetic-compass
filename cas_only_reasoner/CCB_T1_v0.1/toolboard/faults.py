"""The fault and adversarial suite for tool use (the G7 gate).

Each fault must surface typed, with no partial state and no fabricated
continuation.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .intent import execute
from .tools import (AmbiguousToolNeed, ContraToolResult, Tool,
                    ToolBudgetExhausted, ToolFailure, ToolPermissionDenied,
                    ToolRegistry, ToolUnknown, default_registry)


def injected_failure_case() -> Dict:
    """A tool that raises; the failure must be typed with no partial state."""
    registry = ToolRegistry()

    def broken(need, facts):
        raise RuntimeError("injected tool failure")

    registry.register(Tool("broken_tool", "sum", permission=0, cost=1.0,
                           handler=broken))
    intent = {"tool": "broken_tool", "need": {"pred": "sum"},
              "provenance": {"committed_outcome": True, "sealed_trace": True,
                             "branch_id": None}}
    return {"registry": registry, "intent": intent}


def permission_case() -> Dict:
    """Authority 0 cannot run a permission-1 tool."""
    registry = default_registry()
    registry.tools["calculator"].permission = 1
    intent = {"tool": "calculator", "need": {"pred": "sum"},
              "provenance": {"committed_outcome": True, "sealed_trace": True,
                             "branch_id": None}}
    return {"registry": registry, "intent": intent, "authority": 0}


def budget_case() -> Dict:
    """The tool costs more than the remaining budget."""
    registry = default_registry()
    intent = {"tool": "calculator", "need": {"pred": "sum"},
              "provenance": {"committed_outcome": True, "sealed_trace": True,
                             "branch_id": None}}
    return {"registry": registry, "intent": intent, "budget": 0.5}


def branch_case() -> Dict:
    """A branch-level tool request is rejected by provenance rules."""
    registry = default_registry()
    intent = {"tool": "calculator", "need": {"pred": "sum"},
              "provenance": {"committed_outcome": False, "sealed_trace": True,
                             "branch_id": "branch_02"}}
    return {"registry": registry, "intent": intent}


def hostile_result_case() -> Dict:
    """A tool result contradicting a known fact must be flagged."""
    registry = default_registry()
    facts = [{"pred": "sum", "args": ["x", "y", "17/12"], "value": "17/12"}]

    def hostile(need, facts_):
        return {"add_facts": [{"pred": "sum", "args": ["x", "y", "3/4"],
                               "value": "3/4"}]}

    registry.register(Tool("hostile_tool", "sum", permission=0, cost=1.0,
                           handler=hostile))
    intent = {"tool": "hostile_tool", "need": {"pred": "sum"},
              "provenance": {"committed_outcome": True, "sealed_trace": True,
                             "branch_id": None}}
    return {"registry": registry, "intent": intent, "facts": facts}
