"""Strict data-only candidate IR for named unary CJT program composition.

This is not an authority token or a replacement for the accepted native runtime.
Structural admission neither executes a junction nor establishes task correctness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re


SCHEMA = "cas-meta2-program/0.1"
CJT_IDS = frozenset(("A", "B", "C", "R"))
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,31}\Z")


class IRValidationError(ValueError):
    def __init__(self, code, path=""):
        self.code, self.path = code, path
        super().__init__(f"{code}:{path}" if path else code)


@dataclass(frozen=True)
class Limits:
    max_source_bytes: int = 262144
    max_procedures: int = 32
    max_instructions: int = 256
    max_expanded_instructions: int = 512
    max_expanded_runs: int = 256
    max_call_depth: int = 16

    def __post_init__(self):
        caps = (1048576, 128, 4096, 8192, 4096, 32)
        for (name, value), cap in zip(asdict(self).items(), caps, strict=True):
            if type(value) is not int or not 1 <= value <= cap:
                raise IRValidationError("INVALID_LIMIT", name)


def _fail(code, path=""):
    raise IRValidationError(code, path)


def _keys(value, names, path):
    if type(value) is not dict:
        _fail("EXPECTED_OBJECT", path)
    if set(value) != set(names):
        _fail("UNEXPECTED_FIELDS", path)


def _name(value, path):
    if type(value) is not str or not _NAME.fullmatch(value):
        _fail("INVALID_NAME", path)
    return value


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _fail("DUPLICATE_JSON_KEY", key)
        value[key] = item
    return value


def _source(program, limits):
    if isinstance(program, bytes):
        try:
            program = program.decode("utf-8")
        except UnicodeDecodeError:
            _fail("INVALID_UTF8")
    if type(program) is str:
        if len(program.encode("utf-8")) > limits.max_source_bytes:
            _fail("SOURCE_SIZE_LIMIT")
        try:
            program = json.loads(program, object_pairs_hook=_pairs,
                                 parse_constant=lambda _: _fail("NONFINITE_VALUE"))
        except IRValidationError:
            raise
        except (ValueError, RecursionError):
            _fail("INVALID_JSON")
    if type(program) is not dict:
        _fail("EXPECTED_OBJECT", "program")
    # Reject cycles, subclasses, huge/deep containers and coercible Python data
    # before JSON serialization. Never use a JSON dump to silently turn tuples
    # or integer dictionary keys into admissible source.
    active, nodes = set(), 0
    stack = [(program, 0, False)]
    while stack:
        value, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(value))
            continue
        nodes += 1
        if nodes > 65536 or depth > 32:
            _fail("SOURCE_TREE_LIMIT")
        if type(value) in (dict, list):
            if id(value) in active:
                _fail("CYCLIC_SOURCE")
            if len(value) > 8192:
                _fail("SOURCE_TREE_LIMIT")
            active.add(id(value))
            stack.append((value, depth, True))
            if type(value) is dict and any(type(k) is not str for k in value):
                _fail("NON_STRING_KEY")
            children = value.values() if type(value) is dict else value
            stack.extend((child, depth + 1, False) for child in children)
        elif type(value) is not str:
            _fail("NON_STRING_SCALAR")
    try:
        encoded = json.dumps(program, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")
    except (ValueError, RecursionError, UnicodeError):
        _fail("INVALID_JSON")
    if len(encoded) > limits.max_source_bytes:
        _fail("SOURCE_SIZE_LIMIT")
    return json.loads(encoded), encoded


def _admit(program, limits=None):
    if limits is None:
        limits = Limits()
    if not isinstance(limits, Limits):
        _fail("INVALID_LIMITS")
    value, encoded = _source(program, limits)
    _keys(value, ("schema", "entry", "procedures"), "program")
    if value["schema"] != SCHEMA:
        _fail("UNSUPPORTED_SCHEMA", "schema")
    entry = _name(value["entry"], "entry")
    procedures = value["procedures"]
    if type(procedures) is not dict or not 1 <= len(procedures) <= limits.max_procedures:
        _fail("PROCEDURE_LIMIT", "procedures")
    if entry not in procedures:
        _fail("UNKNOWN_ENTRY", "entry")
    edges, instruction_count = {}, 0
    for name, proc in procedures.items():
        path = f"procedures.{_name(name, 'procedures')}"
        _keys(proc, ("input", "allowed_cjts", "steps", "return"), path)
        values = {_name(proc["input"], path + ".input")}
        scope = proc["allowed_cjts"]
        if (type(scope) is not list or not scope or
                any(type(cjt) is not str or cjt not in CJT_IDS for cjt in scope)):
            _fail("INVALID_CJT_SCOPE", path)
        if len(scope) != len(set(scope)):
            _fail("DUPLICATE_CJT_SCOPE", path)
        steps = proc["steps"]
        if type(steps) is not list or not steps:
            _fail("EMPTY_OR_INVALID_STEPS", path)
        instruction_count += len(steps)
        if instruction_count > limits.max_instructions:
            _fail("INSTRUCTION_LIMIT", path)
        edges[name] = []
        for index, step in enumerate(steps):
            location = f"{path}.steps[{index}]"
            if type(step) is not dict:
                _fail("EXPECTED_OBJECT", location)
            if step.get("kind") == "RUN":
                _keys(step, ("kind", "cjt_id", "input", "output"), location)
                if step["cjt_id"] not in scope:
                    _fail("CJT_SCOPE_DENIED", location)
            elif step.get("kind") == "CALL":
                _keys(step, ("kind", "procedure", "input", "output"), location)
                child = _name(step["procedure"], location + ".procedure")
                if child not in procedures:
                    _fail("UNKNOWN_PROCEDURE", location)
                edges[name].append(child)
            else:
                _fail("UNSUPPORTED_STEP", location)
            source = _name(step["input"], location + ".input")
            target = _name(step["output"], location + ".output")
            if source not in values:
                _fail("UNDECLARED_VALUE", location)
            if target in values:
                _fail("DUPLICATE_VALUE", location)
            values.add(target)
        if _name(proc["return"], path + ".return") not in values:
            _fail("UNDECLARED_RETURN", path)
    for name, children in edges.items():
        for child in children:
            if not set(procedures[child]["allowed_cjts"]) <= set(procedures[name]["allowed_cjts"]):
                _fail("CHILD_SCOPE_ESCALATION", f"procedures.{name}")
    visiting, costs = set(), {}

    def inspect(name):
        if name in visiting:
            _fail("CALL_CYCLE", f"procedures.{name}")
        if name in costs:
            return costs[name]
        visiting.add(name)
        count = len(procedures[name]["steps"])
        runs = sum(s["kind"] == "RUN" for s in procedures[name]["steps"])
        depth = 1
        for child in edges[name]:
            child_count, child_runs, child_depth = inspect(child)
            count += child_count
            runs += child_runs
            depth = max(depth, child_depth + 1)
            if count > limits.max_expanded_instructions:
                _fail("EXPANDED_INSTRUCTION_LIMIT", f"procedures.{name}")
            if runs > limits.max_expanded_runs:
                _fail("EXPANDED_RUN_LIMIT", f"procedures.{name}")
            if depth > limits.max_call_depth:
                _fail("CALL_DEPTH_LIMIT", f"procedures.{name}")
        if count > limits.max_expanded_instructions:
            _fail("EXPANDED_INSTRUCTION_LIMIT", f"procedures.{name}")
        if runs > limits.max_expanded_runs:
            _fail("EXPANDED_RUN_LIMIT", f"procedures.{name}")
        costs[name] = (count, runs, depth)
        visiting.remove(name)
        return costs[name]

    expanded, runs, depth = inspect(entry)
    if set(costs) != set(procedures):
        # Validate unreachable subgraphs too so a hidden cycle cannot be
        # mistaken for a harmless unused declaration.
        for name in procedures:
            inspect(name)
        _fail("UNREACHABLE_PROCEDURE")
    return value, {"procedure_count": len(procedures),
                   "instruction_count": instruction_count,
                   "expanded_instruction_count": expanded,
                   "expanded_run_count": runs, "max_call_depth": depth,
                   "program_sha256": hashlib.sha256(encoded).hexdigest()}


def validate_program(program, limits=None):
    """Validate structure, scope and budgets without any native computation."""
    return _admit(program, limits)[1]


def canonical_program(program):
    value, _ = _admit(program)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def expand_program(program):
    """Return a bounded event plan, never an executed trace or authority receipt.

    References name frame-local values. ENTER transports the caller's input into
    the child. RETURN transports a selected child value into its caller's named
    output. A structural address is not a globally unique execution/call ID.
    """
    value, _ = _admit(program)
    events = []

    def walk(name, frame, input_ref, output_ref, parent=None, call_address=None):
        proc = value["procedures"][name]
        prefix = frame + "/values/"
        events.append({"kind": "ENTER", "address": frame + "/enter", "frame_address": frame,
                       "parent_frame_address": parent, "call_address": call_address,
                       "procedure": name, "input_ref": input_ref,
                       "output_ref": prefix + proc["input"]})
        for index, step in enumerate(proc["steps"]):
            address = frame + f"/steps/{index}"
            if step["kind"] == "RUN":
                events.append({"kind": "RUN", "address": address, "frame_address": frame,
                               "procedure": name, "cjt_id": step["cjt_id"],
                               "input_ref": prefix + step["input"], "output_ref": prefix + step["output"]})
            else:
                walk(step["procedure"], address + "/call:" + step["procedure"],
                     prefix + step["input"], prefix + step["output"], frame, address)
        events.append({"kind": "RETURN", "address": frame + "/return", "frame_address": frame,
                       "parent_frame_address": parent, "procedure": name,
                       "input_ref": prefix + proc["return"], "output_ref": output_ref})

    walk(value["entry"], "entry:" + value["entry"], "$input", "$result")
    return events
