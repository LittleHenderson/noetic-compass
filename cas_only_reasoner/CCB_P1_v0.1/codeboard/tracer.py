"""CCB-P1: the TRACER - line-by-line state capture, and the
PCBA-style walk-down: reproduce -> inspect states -> LAST GOOD state
-> FIRST BAD state.

The diagnosis compares the buggy run's variable trace against a
REFERENCE run (the examiner's known-good implementation, or the
student's own promoted procedure) on the same failing input: the
first step where a SHARED variable departs from the reference is the
first bad state - the programming TP1/TP2/TP3 probe."""

from __future__ import annotations

import sys
from typing import Dict, List, Optional

from .sandbox import (SAFE_BUILTINS, STUDENT_FILE, static_gate)


def trace_run(code: str, function_name: str, args: List,
              max_events: int = 4000,
              step_budget: int = 200_000) -> Dict:
    """Execute in the FULL sandbox discipline (audit finding: the
    tracer was a weaker sandbox than run()). The static gate refuses
    forbidden effects; the STEP BUDGET fires on every student-file
    line in ANY frame; the recursion limit is managed and restored.
    Snapshots are recorded only inside the target function."""
    gate = static_gate(code)
    if gate:
        return {"status": "REFUSED", "defects": gate, "events": []}
    events: List[Dict] = []
    state = {"overflow": False, "budget": step_budget}

    def snapshot(frame):
        out = {}
        for key, value in frame.f_locals.items():
            if key.startswith("_") or callable(value):
                continue
            out[key] = repr(value)
        return out

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != STUDENT_FILE:
            return None
        if event == "line":
            # the STEP BUDGET counts every student line in EVERY frame
            # (audit finding: a helper's runaway loop escaped the
            # per-target-function scoping and hung the tracer)
            state["budget"] -= 1
            if state["budget"] <= 0:
                raise TimeoutError("step budget exceeded")
        # snapshots (for the walk-down) only inside the TARGET
        # function - the module frame holds the function OBJECT whose
        # repr carries a memory address (false, nondeterministic
        # divergence)
        if frame.f_code.co_name != function_name:
            return tracer
        if event == "line":
            if len(events) >= max_events:
                state["overflow"] = True
                raise TimeoutError("trace budget exceeded")
            events.append({"line": frame.f_lineno,
                           "locals": snapshot(frame)})
        elif event == "return":
            events.append({"line": frame.f_lineno,
                           "locals": snapshot(frame),
                           "returned": repr(arg)})
        return tracer

    import copy as _copy
    namespace: Dict = {"__builtins__": dict(SAFE_BUILTINS)}
    old_limit = sys.getrecursionlimit()
    try:
        compiled = compile(code, STUDENT_FILE, "exec")
        sys.setrecursionlimit(2000)
        sys.settrace(tracer)
        try:
            exec(compiled, namespace)  # noqa: S102
            fn = namespace.get(function_name)
            if not callable(fn):
                return {"status": "ERROR",
                        "error": f"{function_name!r} not defined",
                        "events": events}
            value = fn(*_copy.deepcopy(args))
        finally:
            sys.settrace(None)
            sys.setrecursionlimit(old_limit)
    except TimeoutError:
        return {"status": "TRACE_BUDGET", "events": events}
    except RecursionError:
        return {"status": "RUNTIME_ERROR",
                "error": "recursion limit exceeded", "events": events}
    except Exception as exc:
        return {"status": "RUNTIME_ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "events": events}
    return {"status": "OK", "value": value, "events": events}


def first_divergence(buggy_events: List[Dict],
                     reference_events: List[Dict]) -> Optional[Dict]:
    """The walk-down verdict: the first traced step at which a
    variable PRESENT IN BOTH runs disagrees. Returns the last good
    step, the first bad step, the variable, and both values."""
    steps = min(len(buggy_events), len(reference_events))
    last_good = None
    for index in range(steps):
        buggy = buggy_events[index]
        reference = reference_events[index]
        shared = (set(buggy["locals"]) & set(reference["locals"]))
        differing = sorted(
            name for name in shared
            if buggy["locals"][name] != reference["locals"][name])
        if differing:
            variable = differing[0]
            return {
                "first_bad_step": index,
                "line": buggy["line"],
                "variable": variable,
                "got": buggy["locals"][variable],
                "reference": reference["locals"][variable],
                "last_good_step": last_good,
            }
        if buggy["line"] != reference["line"]:
            # CONTROL-FLOW divergence: same variables, different
            # path - this IS the first bad state (walk-down
            # completeness fix: locals alone missed it)
            return {"first_bad_step": index,
                    "line": buggy["line"],
                    "variable": None,
                    "detail": f"control flow diverges: buggy takes "
                              f"line {buggy['line']}, reference "
                              f"takes line {reference['line']}",
                    "last_good_step": last_good}
        if buggy.get("returned") != reference.get("returned"):
            # RETURN-VALUE divergence with identical locals/path
            return {"first_bad_step": index,
                    "line": buggy["line"],
                    "variable": "return value",
                    "got": buggy.get("returned"),
                    "reference": reference.get("returned"),
                    "last_good_step": last_good}
        last_good = index
    if len(buggy_events) != len(reference_events):
        return {"first_bad_step": steps,
                "line": (buggy_events[steps - 1]["line"]
                         if buggy_events else None),
                "variable": None,
                "detail": "control flow diverges: the runs have "
                          "different lengths after identical "
                          "prefixes",
                "last_good_step": last_good}
    return None
