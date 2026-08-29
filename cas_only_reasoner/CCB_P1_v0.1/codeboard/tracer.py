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
              max_events: int = 4000) -> Dict:
    """Execute in the sandbox discipline while recording a per-line
    snapshot of local variables inside the student frame."""
    gate = static_gate(code)
    if gate:
        return {"status": "REFUSED", "defects": gate, "events": []}
    events: List[Dict] = []
    state = {"overflow": False}

    def snapshot(frame):
        out = {}
        for key, value in frame.f_locals.items():
            if key.startswith("_") or callable(value):
                continue
            out[key] = repr(value)
        return out

    def tracer(frame, event, arg):
        # only frames INSIDE the target function: the module-level
        # exec frame holds the function OBJECT, whose repr carries a
        # memory address - a false, nondeterministic divergence
        # (battery-found)
        if frame.f_code.co_filename != STUDENT_FILE                 or frame.f_code.co_name != function_name:
            return None
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
    try:
        compiled = compile(code, STUDENT_FILE, "exec")
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
    except TimeoutError:
        return {"status": "TRACE_BUDGET", "events": events}
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
