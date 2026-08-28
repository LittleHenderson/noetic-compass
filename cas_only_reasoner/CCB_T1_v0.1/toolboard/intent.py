"""ToolIntent: the only sanctioned request to execute a tool."""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional

from .tools import (AmbiguousToolNeed, ContraToolResult, Tool,
                    ToolBudgetExhausted, ToolError, ToolFailure,
                    ToolPermissionDenied, ToolProvenanceViolation,
                    ToolUnknown)


def _digest(obj: Dict) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def validate(intent: Dict, registry, authority: int,
             budget_remaining: float, known_facts: List[Dict]) -> List[str]:
    """Return rejection reasons; empty means valid."""
    reasons: List[str] = []
    provenance = intent.get("provenance", {})
    if not provenance.get("committed_outcome"):
        reasons.append("tool calls require a committed outcome")
    if not provenance.get("sealed_trace"):
        reasons.append("tool calls require a sealed trace")
    if provenance.get("branch_id") is not None:
        reasons.append("no candidate branch may call tools")
    tool = registry.tools.get(intent.get("tool", ""))
    if tool is None:
        reasons.append(f"unknown tool {intent.get('tool')}")
        return reasons
    if tool.permission > authority:
        reasons.append("TOOL_PERMISSION_DENIED")
    if tool.cost > budget_remaining:
        reasons.append("TOOL_BUDGET_EXHAUSTED")
    return reasons


def execute(intent: Dict, registry, authority: int,
            budget_remaining: float, known_facts: List[Dict]) -> Dict:
    """Validate then execute; typed failures, no partial state."""
    reasons = validate(intent, registry, authority, budget_remaining,
                       known_facts)
    if reasons:
        message = "; ".join(reasons)
        # Each rejection surfaces under its OWN type - a provenance
        # violation is never disguised as an unknown tool.
        if "TOOL_PERMISSION_DENIED" in reasons:
            raise ToolPermissionDenied(message)
        if "TOOL_BUDGET_EXHAUSTED" in reasons:
            raise ToolBudgetExhausted(message)
        if any("committed" in r or "sealed" in r or "branch" in r
               for r in reasons):
            raise ToolProvenanceViolation(message)
        raise ToolUnknown(message)
    tool = registry.tools[intent.get("tool", "")]
    need = intent.get("need", {})
    try:
        result = tool.call(need, known_facts)
    except ToolError:
        raise
    except Exception as exc:
        raise ToolFailure(f"tool {tool.name} failed: {exc}")
    # Contradiction check: a tool result must not contradict known
    # facts - same predicate, same inputs, but a DIFFERENT output.
    for fact in result.get("add_facts", []):
        fargs = fact.get("args", [])
        for known in known_facts:
            kargs = known.get("args", [])
            same_inputs = (known.get("pred") == fact.get("pred")
                           and len(kargs) >= 2 and len(fargs) >= 2
                           and kargs[:-1] == fargs[:-1])
            different_output = kargs != fargs
            if same_inputs and different_output:
                raise ContraToolResult(
                    f"tool result {fact} contradicts known fact {known}")
    record = {
        "tool": tool.name,
        "need": need,
        "result": result,
        "cost": tool.cost,
        "provenance": intent.get("provenance", {}),
    }
    record["digest"] = _digest(record)
    return record
