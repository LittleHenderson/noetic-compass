"""CCB-P1: the SANDBOX - the only place student/teacher code runs.

The security law, enforced in ORDER:
  1. A STATIC gate refuses forbidden effects BEFORE any execution:
     imports, file access, exec/eval, network, dunder reach-through,
     introspection builtins. 'Unsandboxed file write: rejects before
     execution' is a permanent battery row.
  2. Execution happens with a WHITELISTED builtin set and a hard
     step budget (a line-counting trace) - runaway loops die typed.
  3. Every run is wrapped in a typed SANDBOX_EXECUTE ToolIntent
     (the CCB-T1 discipline applied board-locally): code digest,
     arguments, budget, and outcome are all on the record.

Deterministic: pure Python, no clock, no randomness, arguments
deep-copied so a run cannot leak state into the next.
"""

from __future__ import annotations

import ast
import builtins as _builtins
import copy
import hashlib
import json
import sys
from typing import Dict, List, Optional

STEP_BUDGET_DEFAULT = 200_000
_MAX_INT_LITERAL = 1_000_000

_SAFE_BUILTIN_NAMES = (
    "len", "range", "abs", "min", "max", "sum", "sorted",
    "enumerate", "zip", "map", "filter", "reversed", "isinstance",
    "int", "str", "bool", "float", "list", "dict", "set", "tuple",
    "round", "divmod", "all", "any", "repr",
    "ValueError", "TypeError", "IndexError", "KeyError",
    "ZeroDivisionError", "ArithmeticError", "Exception",
    "StopIteration", "RecursionError", "True", "False", "None",
)
SAFE_BUILTINS = {name: getattr(_builtins, name)
                 for name in _SAFE_BUILTIN_NAMES
                 if hasattr(_builtins, name)}

FORBIDDEN_NAMES = {
    "open", "exec", "eval", "__import__", "compile", "globals",
    "locals", "vars", "getattr", "setattr", "delattr", "input",
    "print", "breakpoint", "exit", "quit", "help", "type", "super",
    "object", "memoryview", "bytearray", "classmethod",
    "staticmethod", "property", "os", "sys", "socket", "subprocess",
    "pathlib", "shutil", "requests", "urllib", "http",
}

STUDENT_FILE = "<student>"


class SandboxRefusal(Exception):
    """Typed pre-execution refusal - the code never ran."""


def code_digest(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


def static_gate(code: str) -> List[str]:
    """Typed defects; ANY defect means the code never executes."""
    defects: List[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"PARSE_ERROR: {exc.msg} (line {exc.lineno})"]
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            defects.append("FORBIDDEN_EFFECT: import is not "
                           "permitted in the sandbox (line "
                           f"{node.lineno})")
        elif isinstance(node, ast.Name) \
                and node.id in FORBIDDEN_NAMES:
            defects.append(f"FORBIDDEN_EFFECT: {node.id!r} is "
                           f"blocked (line {node.lineno})")
        elif isinstance(node, ast.Name) and node.id.startswith("__"):
            # __builtins__, __import__ etc. reached as bare names
            defects.append(f"FORBIDDEN_EFFECT: dunder name "
                           f"{node.id!r} is blocked (line "
                           f"{node.lineno})")
        elif isinstance(node, ast.Attribute):
            # ATTRIBUTE ACCESS IS BLOCKED ENTIRELY (audit finding: a
            # generator's non-underscore gi_frame / f_back /
            # f_builtins walked to the real __import__; str.format
            # traversed __class__ hidden in a string literal). The
            # taught pure functions use NO attribute access at all, so
            # the whole class of frame/introspection/format escapes
            # dies here. This is the crown-jewel security fix.
            defects.append(f"FORBIDDEN_EFFECT: attribute access "
                           f"{node.attr!r} is not permitted in the "
                           f"sandbox (line {node.lineno})")
        elif isinstance(node, ast.Constant) \
                and isinstance(node.value, str) \
                and node.value.startswith("__") \
                and node.value.endswith("__"):
            # a dunder name hidden in a string LITERAL (reached later
            # by subscript, format, or getattr-equivalent)
            defects.append(f"FORBIDDEN_EFFECT: dunder string literal "
                           f"{node.value!r} is blocked (line "
                           f"{node.lineno})")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            defects.append("FORBIDDEN_EFFECT: global/nonlocal "
                           f"state reach (line {node.lineno})")
        elif isinstance(node, (ast.Yield, ast.YieldFrom,
                               ast.Lambda)):
            # generators/lambdas are the frame-capture primitives of
            # the escape and are not needed by the taught functions
            defects.append("FORBIDDEN_EFFECT: yield/lambda is not "
                           f"permitted in the sandbox (line "
                           f"{node.lineno})")
        elif isinstance(node, ast.Constant) \
                and isinstance(node.value, int) \
                and not isinstance(node.value, bool) \
                and abs(node.value) > _MAX_INT_LITERAL:
            # a memory/CPU bomb needs a big literal count/exponent -
            # 5,000,000 in [0]*5000000, 10**8 in 2**(10**8) (audit
            # finding: the step budget counts lines, not work).
            # OS-level memory/CPU isolation is a documented residual
            # limit for a fully in-process sandbox; this cap kills the
            # single-line bombs the exam corpus and taught functions
            # never need.
            defects.append(f"FORBIDDEN_EFFECT: integer literal "
                           f"{node.value} exceeds the sandbox cap "
                           f"{_MAX_INT_LITERAL} (line {node.lineno})")
        elif isinstance(node, ast.BinOp) \
                and isinstance(node.op, ast.Pow):
            # exponentiation is a compute bomb primitive and is not
            # needed by the taught functions (the math board owns
            # powers) - blocked
            defects.append("FORBIDDEN_EFFECT: '**' is not permitted "
                           f"in the sandbox (line {node.lineno})")
    return defects


def make_execute_intent(code: str, function_name: str, args: List,
                        step_budget: int) -> Dict:
    """The typed ToolIntent wrapping every sandbox run."""
    return {"intent_type": "SANDBOX_EXECUTE",
            "code_digest": code_digest(code),
            "function_name": function_name,
            "args": copy.deepcopy(args),
            "step_budget": step_budget,
            "effects_allowed": []}


def validate_execute_intent(intent: Dict) -> List[str]:
    defects = []
    if intent.get("intent_type") != "SANDBOX_EXECUTE":
        defects.append("wrong intent_type")
    if intent.get("effects_allowed"):
        defects.append("no effects may be allowed - the sandbox "
                       "grants none (network/file access is refused "
                       "unless a HUMAN authorization enters the "
                       "intent, and none exists in v0.1)")
    for field in ("verified", "promote", "examiner", "tests"):
        if field in intent:
            defects.append(f"forbidden authority field {field!r}")
    return defects


class _StepBudget:
    def __init__(self, budget: int) -> None:
        self.remaining = budget

    def trace(self, frame, event, arg):
        if frame.f_code.co_filename != STUDENT_FILE:
            return None
        if event == "line":
            self.remaining -= 1
            if self.remaining <= 0:
                raise TimeoutError("step budget exceeded")
        return self.trace


def run(code: str, function_name: str, args: List,
        step_budget: int = STEP_BUDGET_DEFAULT) -> Dict:
    """One sandboxed call. Returns a typed outcome; never raises."""
    intent = make_execute_intent(code, function_name, args,
                                 step_budget)
    defects = validate_execute_intent(intent)
    if defects:
        return {"status": "INTENT_REFUSED", "defects": defects,
                "intent": intent}
    gate = static_gate(code)
    if gate:
        return {"status": ("PARSE_ERROR" if gate[0].startswith(
                    "PARSE_ERROR") else "FORBIDDEN_EFFECT"),
                "defects": gate, "intent": intent,
                "executed": False}
    namespace: Dict = {"__builtins__": dict(SAFE_BUILTINS)}
    budget = _StepBudget(step_budget)
    old_limit = sys.getrecursionlimit()
    try:
        compiled = compile(code, STUDENT_FILE, "exec")
        sys.setrecursionlimit(2000)
        sys.settrace(budget.trace)
        try:
            exec(compiled, namespace)  # noqa: S102 - the sandbox
            fn = namespace.get(function_name)
            if not callable(fn):
                return {"status": "RUNTIME_ERROR", "intent": intent,
                        "error": f"function {function_name!r} not "
                                 f"defined"}
            value = fn(*copy.deepcopy(args))
        finally:
            sys.settrace(None)
            sys.setrecursionlimit(old_limit)
    except TimeoutError:
        return {"status": "STEP_BUDGET_EXCEEDED", "intent": intent,
                "error": f"exceeded {step_budget} steps"}
    except RecursionError:
        return {"status": "RUNTIME_ERROR", "intent": intent,
                "error": "recursion limit exceeded"}
    except Exception as exc:
        return {"status": "RUNTIME_ERROR", "intent": intent,
                "error": f"{type(exc).__name__}: {exc}"}
    try:
        json.dumps(value)
    except TypeError:
        return {"status": "RUNTIME_ERROR", "intent": intent,
                "error": "return value is not plain data"}
    return {"status": "OK", "value": value, "intent": intent,
            "steps_used": step_budget - budget.remaining}
