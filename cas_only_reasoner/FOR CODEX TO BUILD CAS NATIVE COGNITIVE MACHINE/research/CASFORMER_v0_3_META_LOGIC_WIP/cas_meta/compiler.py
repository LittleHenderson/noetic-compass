"""Strict, bounded compiler for the first CAS-META procedure experiment.

This module admits only the existing ^6 operation.  It does not execute neural
work, grant verifier authority, or interpret Foundation/Noetic aliases.  CALL
instructions remain CALL instructions; only explicit SEQUENCE nodes flatten.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any


VERSION = "cas-meta/0.1"
MAX_SOURCE_BYTES = 1_048_576
MAX_PROCEDURES = 128
MAX_AST_NODES = 4096
MAX_AST_DEPTH = 64
MAX_STEPS_PER_PROCEDURE = 1024
MAX_ALLOWANCE = 1_000_000
_INPUT_TYPES = frozenset(("IDEA", "EFFECT", "RPM_SUBGOAL"))
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}\Z")


class MetaCompileError(ValueError):
    """A stable error code and the source location that failed admission."""

    def __init__(self, code: str, path: str = "") -> None:
        self.code = code
        self.path = path
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class Step:
    kind: str
    path: str
    cjt: str = ""
    operation: str = ""
    expected: str = ""
    opposite: str | None = None
    repair: str | None = None
    resume_expected: str | None = None
    procedure: str = ""
    allowance: int = 0


@dataclass(frozen=True, slots=True)
class Procedure:
    name: str
    input_type: str
    output_type: str
    allowed_cjts: tuple[str, ...]
    steps: tuple[Step, ...]


@dataclass(frozen=True, slots=True)
class Program:
    version: str
    digest: str
    entry: str
    procedures: tuple[Procedure, ...]
    source_json: str

    @property
    def by_name(self) -> dict[str, Procedure]:
        """Return a fresh index, without a mutable object inside the program."""
        return {procedure.name: procedure for procedure in self.procedures}


def _fail(code: str, path: str = "") -> None:
    raise MetaCompileError(code, path)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _nonfinite(_: str) -> None:
    _fail("NONFINITE_NUMBER")


def _check_json_tree(value: Any) -> None:
    """Bound dict input too, including cycles and non-JSON Python values."""
    active: set[int] = set()
    stack = [(value, 0, False)]
    nodes = 0
    while stack:
        node, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(node))
            continue
        nodes += 1
        if nodes > MAX_AST_NODES * 16:
            _fail("SOURCE_NODE_LIMIT")
        # A sequence adds both an object and a list to the JSON nesting.
        if depth > MAX_AST_DEPTH * 2 + 8:
            _fail("SOURCE_DEPTH_LIMIT")
        if type(node) in (dict, list):
            if len(node) > MAX_AST_NODES * 16:
                _fail("SOURCE_NODE_LIMIT")
            if id(node) in active:
                _fail("CYCLIC_SOURCE")
            active.add(id(node))
            stack.append((node, depth, True))
            if type(node) is dict:
                if any(type(key) is not str for key in node):
                    _fail("NON_STRING_JSON_KEY")
                children = list(node.values())
            else:
                children = node
            stack.extend((child, depth + 1, False) for child in reversed(children))
        elif type(node) is float:
            if not math.isfinite(node):
                _fail("NONFINITE_NUMBER")
        elif node is not None and type(node) not in (str, int, bool):
            _fail("NON_JSON_VALUE")
        if type(node) is str and len(node) > MAX_SOURCE_BYTES:
            _fail("SOURCE_SIZE_LIMIT")


def _source(source: str | dict[str, Any]) -> tuple[dict[str, Any], str]:
    if type(source) is str:
        try:
            if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
                _fail("SOURCE_SIZE_LIMIT")
            value = json.loads(
                source, object_pairs_hook=_unique_object, parse_constant=_nonfinite
            )
        except MetaCompileError:
            raise
        except UnicodeEncodeError as error:
            raise MetaCompileError("INVALID_UNICODE") from error
        except (ValueError, RecursionError) as error:
            raise MetaCompileError("INVALID_JSON") from error
    elif type(source) is dict:
        value = source
    else:
        _fail("INVALID_SOURCE_TYPE")
    if type(value) is not dict:
        _fail("INVALID_PROGRAM")
    _check_json_tree(value)
    try:
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        )
        if len(canonical.encode("utf-8")) > MAX_SOURCE_BYTES:
            _fail("SOURCE_SIZE_LIMIT")
        # Detach dict input from its owner before constructing immutable values.
        detached = json.loads(canonical)
    except UnicodeEncodeError as error:
        raise MetaCompileError("INVALID_UNICODE") from error
    except (ValueError, RecursionError) as error:
        if isinstance(error, MetaCompileError):
            raise
        raise MetaCompileError("INVALID_JSON_VALUE") from error
    return detached, canonical


def _object(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("EXPECTED_OBJECT", path)
    return value


def _keys(value: dict[str, Any], required: set[str], optional: set[str], path: str) -> None:
    if set(value) - required - optional:
        _fail("UNKNOWN_FIELD", path)
    if required - set(value):
        _fail("MISSING_FIELD", path)


def _name(value: Any, path: str) -> str:
    if type(value) is not str or not _NAME.fullmatch(value):
        _fail("INVALID_NAME", path)
    return value


def _symbol(value: Any, path: str) -> str:
    if (
        type(value) is not str or not value or len(value) > 256
        or value.strip() != value or any(ord(char) < 32 for char in value)
    ):
        _fail("INVALID_SYMBOL", path)
    return value


def _steps(body: Any, path: str, count: list[int], depth: int = 1) -> tuple[Step, ...]:
    if depth > MAX_AST_DEPTH:
        _fail("AST_DEPTH_LIMIT", path)
    count[0] += 1
    if count[0] > MAX_AST_NODES:
        _fail("AST_NODE_LIMIT", path)
    node = _object(body, path)
    kind = node.get("kind")
    if type(kind) is not str:
        _fail("INVALID_KIND", path)
    if kind == "sequence":
        _keys(node, {"kind", "steps"}, set(), path)
        if type(node["steps"]) is not list:
            _fail("EXPECTED_STEP_LIST", path)
        if not node["steps"]:
            _fail("EMPTY_SEQUENCE", path)
        if len(node["steps"]) > MAX_STEPS_PER_PROCEDURE:
            _fail("STEP_LIMIT", path)
        result: list[Step] = []
        for index, child in enumerate(node["steps"]):
            result.extend(_steps(child, f"{path}.steps[{index}]", count, depth + 1))
            if len(result) > MAX_STEPS_PER_PROCEDURE:
                _fail("STEP_LIMIT", path)
        return tuple(result)
    if kind == "run":
        _keys(node, {"kind", "cjt", "operation", "expected"},
              {"opposite", "repair", "resume_expected"}, path)
        cjt = _name(node["cjt"], path + ".cjt")
        if type(node["operation"]) is not str or node["operation"] != "^6":
            _fail("OPERATION_NOT_ADMITTED", path + ".operation")
        expected = _symbol(node["expected"], path + ".expected")
        if ("repair" in node) != ("resume_expected" in node):
            _fail("REPAIR_RESUME_PAIR_REQUIRED", path)
        opposite = _symbol(node["opposite"], path + ".opposite") if "opposite" in node else None
        repair = _name(node["repair"], path + ".repair") if "repair" in node else None
        resume = _symbol(node["resume_expected"], path + ".resume_expected") if "resume_expected" in node else None
        return (Step("run", path, cjt, "^6", expected, opposite, repair, resume),)
    if kind == "call":
        _keys(node, {"kind", "procedure", "allowance"}, set(), path)
        procedure = _name(node["procedure"], path + ".procedure")
        allowance = node["allowance"]
        if type(allowance) is not int or not 1 <= allowance <= MAX_ALLOWANCE:
            _fail("INVALID_ALLOWANCE", path + ".allowance")
        return (Step("call", path, procedure=procedure, allowance=allowance),)
    _fail("UNSUPPORTED_KIND", path)


def _check_graph(procedures: dict[str, Procedure]) -> None:
    edges: dict[str, set[str]] = {}
    for name, procedure in procedures.items():
        current_type = procedure.input_type
        scope = set(procedure.allowed_cjts)
        edges[name] = set()
        for step in procedure.steps:
            if step.kind == "run":
                if step.cjt not in scope:
                    _fail("CJT_SCOPE_VIOLATION", step.path)
                current_type = "EFFECT"
                child_name = step.repair
            else:
                child_name = step.procedure
            if child_name is not None:
                if child_name not in procedures:
                    _fail("UNKNOWN_PROCEDURE", step.path)
                child = procedures[child_name]
                edges[name].add(child_name)
                if not set(child.allowed_cjts) <= scope:
                    _fail("CHILD_SCOPE_ESCALATION", step.path)
                wanted = "RPM_SUBGOAL" if step.kind == "run" else current_type
                if child.input_type != wanted:
                    _fail("TYPE_MISMATCH", step.path)
                if step.kind == "call":
                    current_type = child.output_type
        if current_type != procedure.output_type:
            _fail("OUTPUT_TYPE_MISMATCH", f"procedures.{name}")

    # Check every declared procedure, not just those reachable from entry.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            _fail("CALL_CYCLE", f"procedures.{name}")
        if name in visited:
            return
        visiting.add(name)
        for child in sorted(edges[name]):
            visit(child)
        visiting.remove(name)
        visited.add(name)

    for name in sorted(procedures):
        visit(name)


def compile_program(source: str | dict[str, Any]) -> Program:
    """Compile strict JSON to immutable instructions without executing them.

    A Program is a data value, not an admission token.  Executors must compile
    source_json again and verify the complete value before using a supplied
    Program; manually constructing these public dataclasses grants nothing.
    """
    value, canonical = _source(source)
    _keys(value, {"version", "entry", "procedures"}, set(), "program")
    if type(value["version"]) is not str or value["version"] != VERSION:
        _fail("UNSUPPORTED_VERSION", "version")
    entry = _name(value["entry"], "entry")
    definitions = _object(value["procedures"], "procedures")
    if not 1 <= len(definitions) <= MAX_PROCEDURES:
        _fail("PROCEDURE_LIMIT", "procedures")
    procedures: dict[str, Procedure] = {}
    count = [0]
    for name, definition in sorted(definitions.items()):
        _name(name, "procedures")
        path = f"procedures.{name}"
        definition = _object(definition, path)
        _keys(definition, {"input_type", "output_type", "allowed_cjts", "body"}, set(), path)
        input_type = definition["input_type"]
        if type(input_type) is not str or input_type not in _INPUT_TYPES:
            _fail("INVALID_INPUT_TYPE", path)
        if type(definition["output_type"]) is not str or definition["output_type"] != "EFFECT":
            _fail("INVALID_OUTPUT_TYPE", path)
        allowed = definition["allowed_cjts"]
        if type(allowed) is not list or not 1 <= len(allowed) <= MAX_PROCEDURES:
            _fail("INVALID_CJT_SCOPE", path)
        allowed = [_name(cjt, path + ".allowed_cjts") for cjt in allowed]
        if len(set(allowed)) != len(allowed):
            _fail("DUPLICATE_CJT_SCOPE", path)
        steps = _steps(definition["body"], path + ".body", count)
        procedures[name] = Procedure(name, input_type, "EFFECT", tuple(allowed), steps)
    if entry not in procedures:
        _fail("UNKNOWN_ENTRY", "entry")
    _check_graph(procedures)
    return Program(
        VERSION, hashlib.sha256(canonical.encode("utf-8")).hexdigest(), entry,
        tuple(procedures.values()), canonical,
    )
