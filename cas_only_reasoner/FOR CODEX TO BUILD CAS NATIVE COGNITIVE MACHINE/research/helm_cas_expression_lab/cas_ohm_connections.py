"""Prepared CAS-Ohm connections, without runtime, sensor, or learning claims.

PCBA uses one checked resistor's exact R literal and caller-declared units.
Synthetic observations and compiler-calculated reference targets are separate.
RPA emits a separate read-only projection. It is NOT an AtlasNode/snapshot or
cncm.cas-ohm-stage/0.1: those require context, evidence and runtime bindings
that a calculation cannot supply. No totals or parent/child flows are inferred.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

VERSION = "cas.ohm.connections/0.1"
MAX_EXPRESSION_BYTES = 16384
MAX_PROJECTION_NODES = 512
MAX_PROJECTION_DEPTH = 32
MAX_PROJECTION_BYTES = 2 * 1024 * 1024
MAX_REPORT_BYTES = 512 * 1024
_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}\Z")
_CALLS = frozenset(("ohm_scale", "ohm_drive", "ohm_attention", "ohm_constraint",
                    "ohm_flow", "ohm_required_drive", "ohm_effective_constraint"))
_OPERATIONS = {"attention_flow": "attention_flow", "required_drive": "required_drive",
               "effective_constraint": "effective_constraint"}
_COMPILER = Path(__file__).resolve().parents[4] / "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py"
_CACHE = None


class OhmConnectionError(ValueError):
    def __init__(self, code, message, details=None):
        self.code, self.details = code, details
        super().__init__(f"{code}: {message}")


def _require(condition, code, message):
    if not condition:
        raise OhmConnectionError(code, message)


def _fields(value, names, label):
    _require(type(value) is dict and set(value) == set(names), "OHM_CONNECTION_FIELDS", f"{label} requires exactly {sorted(names)}")


def _identifier(value, label):
    _require(type(value) is str and _ID.fullmatch(value) is not None,
             "OHM_CONNECTION_ID", f"{label} is not a bounded RPA-compatible identifier")


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _bounded_json(value, maximum):
    # Inspect container structure before recursive JSON encoding. Cycles,
    # pathological depth and arbitrary Python objects never reach the encoder.
    stack, active, count, text_size = [(value, 0, False)], set(), 0, 0
    while stack:
        item, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(item))
            continue
        count += 1
        _require(count <= 100000 and depth <= 64, "OHM_CONNECTION_LIMIT", "JSON structure exceeds its node/depth budget")
        if type(item) in (dict, list):
            _require(len(item) <= 100000, "OHM_CONNECTION_LIMIT", "JSON container exceeds its budget")
            _require(id(item) not in active, "OHM_CONNECTION_CYCLE", "Cyclic input container")
            active.add(id(item))
            stack.append((item, depth, True))
            if type(item) is dict:
                _require(all(type(key) is str for key in item), "OHM_CONNECTION_REPORT", "JSON object keys must be text")
                text_size += sum(len(key) for key in item)
                _require(text_size <= maximum, "OHM_CONNECTION_LIMIT", "JSON keys/text exceed their aggregate budget")
                children = list(item.values())
            else:
                children = item
            _require(len(children) <= 100000, "OHM_CONNECTION_LIMIT", "JSON container exceeds its budget")
            stack.extend((child, depth + 1, False) for child in children)
        else:
            _require(type(item) in (str, bool, int, float, type(None)), "OHM_CONNECTION_REPORT", "Input must contain only JSON values")
            if type(item) is str:
                text_size += len(item)
                _require(text_size <= maximum, "OHM_CONNECTION_LIMIT", "JSON keys/text exceed their aggregate budget")
            if type(item) is int:
                _require(item.bit_length() <= 4096, "OHM_CONNECTION_LIMIT", "JSON integer exceeds its budget")
    try:
        body = _json(value)
    except (ValueError, UnicodeError) as error:
        raise OhmConnectionError("OHM_CONNECTION_REPORT", "Invalid JSON value") from error
    _require(len(body) <= maximum, "OHM_CONNECTION_LIMIT", "JSON payload exceeds its byte budget")
    return body


def _source_bytes(path, maximum):
    try:
        with path.open("rb") as stream:
            raw = stream.read(maximum + 1)
    except OSError as error:
        raise OhmConnectionError("OHM_CONNECTION_SOURCE", f"Missing local source: {path}") from error
    _require(len(raw) <= maximum, "OHM_CONNECTION_LIMIT", "Implementation source exceeds its byte budget")
    return raw.replace(b"\r\n", b"\n")


def _source_binding():
    return {name: hashlib.sha256(_source_bytes(_COMPILER.with_name(name), limit)).hexdigest()
            for name, limit in (("compiler.py", 1024 * 1024), ("cas_ohm.py", 128 * 1024))}


def _helper_binding(helper, binding):
    _require(getattr(helper, "__cas_ohm_source_sha256_lf__", None) == binding["cas_ohm.py"],
             "OHM_CONNECTION_SOURCE", "Loaded helper bytes do not match the source receipt")
    _require(getattr(helper, "__cas_ohm_loaded_path__", None) == str(_COMPILER.with_name("cas_ohm.py")),
             "OHM_CONNECTION_SOURCE", "Loaded helper is from a different checkout")


def _runtime():
    """Load only this checkout, with identity bound to the consumed source bytes."""
    global _CACHE
    before = _source_binding()
    if _CACHE is not None and _CACHE[0] == before:
        _helper_binding(_CACHE[2], before)
        return _CACHE[1], _CACHE[2], dict(before)
    raw = _source_bytes(_COMPILER, 1024 * 1024)
    _require(hashlib.sha256(raw).hexdigest() == before["compiler.py"], "OHM_CONNECTION_SOURCE", "Compiler changed during loading")
    name = "_cas_ohm_connections_" + _digest({"path": str(_COMPILER), **before})
    spec = importlib.util.spec_from_file_location(name, _COMPILER)
    compiler = importlib.util.module_from_spec(spec)
    sys.modules[name] = compiler
    try:
        exec(compile(raw, str(_COMPILER), "exec"), compiler.__dict__)
        _require(callable(getattr(compiler, "_load_cas_ohm", None)), "OHM_CONNECTION_SOURCE", "This compiler has no CAS-Ohm integration")
        helper = compiler._load_cas_ohm()
        _helper_binding(helper, before)
        _require(_source_binding() == before, "OHM_CONNECTION_SOURCE", "Compiler/helper changed during loading")
    except Exception:
        sys.modules.pop(name, None)
        raise
    if _CACHE is not None:
        sys.modules.pop(_CACHE[1].__name__, None)
    _CACHE = (before, compiler, helper)
    return compiler, helper, dict(before)


def _unchanged(binding):
    _require(_source_binding() == binding, "OHM_CONNECTION_SOURCE", "Compiler/helper changed during calculation")


def _scale(helper, declaration):
    _fields(declaration, ("id", "drive_unit", "attention_unit"), "scale declaration")
    return helper.make_scale(**declaration)


def _quantity(helper, kind, declaration):
    _fields(declaration, ("value", "scale", "origin", "reference"), f"{kind} declaration")
    return helper.make_quantity(kind, declaration["value"], _scale(helper, declaration["scale"]),
                                declaration["origin"], declaration["reference"])


def pcba_resistor_flow(source, resistor_name, drive_declaration, resistance_declaration):
    """Calculate one resistor's I=V/R; never infer units, wiring, or total R.

    drive_declaration: value, scale{id,drive_unit,attention_unit}, origin,
    reference. resistance_declaration has scale, origin, reference ONLY: the
    numeric R is obtained from the checked component, never from a caller override.
    The board must pass the PCBA checker's stated static subset.
    """
    from pcba_check import check_pcba_document

    _identifier(resistor_name, "resistor name")
    _fields(resistance_declaration, ("scale", "origin", "reference"), "resistance declaration")
    report = check_pcba_document(source)
    if report["parse_status"] != "PASS" or report["structural_status"] != "PASS" or report["valid"] is not True:
        raise OhmConnectionError("OHM_PCBA_UNVERIFIED", "Board did not pass the declared static subset", report)
    component = report["netlist"]["components"].get(resistor_name)
    _require(component is not None and component["complete"] is True and component["kind"] == "resistor",
             "OHM_PCBA_RESISTOR", "Select an existing, supported Resistor declaration")
    literal = component["parameter_literals"]["R"]
    _, helper, binding = _runtime()
    drive = _quantity(helper, "drive", drive_declaration)
    resistance = _quantity(helper, "constraint", {**resistance_declaration, "value": literal})
    quantity = helper.attention_flow(drive, resistance).to_dict()
    _unchanged(binding)
    return {
        "schema": "cas.pcba.ohm-resistor-flow/0.1", "status": "CALCULATED_DECLARED_SINGLE_RESISTOR",
        "board_source_sha256": report["document"]["source_sha256"], "resistor_name": resistor_name,
        "resistance_literal": literal, "resistor_terminal": component["terminals"]["state"],
        "quantity_report": quantity, "implementation_sha256_lf": binding,
        "pcba_check": {key: report[key] for key in ("parse_status", "structural_status", "scope", "sources", "diagnostics")},
        "topology_status": "NO_SERIES_PARALLEL_OR_TOTAL_INFERENCE",
        "integration_status": "PREPARATORY_NOT_RUNTIME_CONNECTED", "measurement_status": "NO_MEASUREMENT_PERFORMED",
        "helm_status": "NOT_TRAINED", "control_status": "NOT_CONNECTED",
    }


def _demo_ast(compiler, expression):
    _require(type(expression) is str, "OHM_DEMO_SOURCE", "Expression must be text")
    try:
        body = expression.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise OhmConnectionError("OHM_DEMO_SOURCE", "Expression must be valid UTF-8") from error
    _require(0 < len(body) <= MAX_EXPRESSION_BYTES, "OHM_CONNECTION_LIMIT", "Demo expression exceeds its byte budget")
    try:
        tokens = compiler.lex(expression)
        _require(len(tokens) <= 4096, "OHM_CONNECTION_LIMIT", "Demo token budget exceeded")
        ast = compiler.Parser(tokens).parse()
    except (compiler.CompilerError, RecursionError) as error:
        raise OhmConnectionError("OHM_DEMO_SOURCE", f"Cannot parse bounded demo expression: {error}") from error
    # This adapter accepts only one nested named calculation, never imports,
    # user functions, operators, programs, or incidental compiler capabilities.
    _require(type(ast) is compiler.CallExpr and ast.callee in
             ("ohm_flow", "ohm_required_drive", "ohm_effective_constraint"),
             "OHM_DEMO_SUBSET", "Demo requires one named CAS-Ohm calculation expression")
    stack = [(ast, 1)]
    while stack:
        node, depth = stack.pop()
        _require(depth <= 32, "OHM_CONNECTION_LIMIT", "Demo call nesting exceeds 32")
        if type(node) is compiler.CallExpr:
            _require(node.callee in _CALLS, "OHM_DEMO_SUBSET", "Only CAS-Ohm named calls are allowed")
            stack.extend((arg, depth + 1) for arg in node.args)
        else:
            _require(type(node) in (compiler.StringLiteral, compiler.NumberLiteral), "OHM_DEMO_SUBSET", "Only literal arguments and CAS-Ohm calls are allowed")


def make_synthetic_demo(expression, reference_id):
    """Return separate input/target records from an actual compiler calculation.

    This small DEMO fixture is not a Q3 dataset/split or a learned prediction.
    Its target is obtained from compile_expression, never from a learner. Input
    IDs include expression, reference and consumed compiler/helper source hashes.
    """
    _identifier(reference_id, "demo reference")
    compiler, helper, binding = _runtime()
    _demo_ast(compiler, expression)
    artifact = compiler.compile_expression(expression)
    _require(artifact.valid, "OHM_DEMO_COMPILER", f"Compiler rejected the demo: {artifact.error}")
    _require(type(artifact.result) is helper.OhmQuantity and artifact.result.origin == "calculated",
             "OHM_DEMO_RESULT", "Compiler did not return a calculated CAS-Ohm quantity")
    result = artifact.result.to_dict()
    _unchanged(binding)
    observation = {"schema": "cas.ohm.demo-observation/0.1", "expression": expression,
                   "reference_id": reference_id, "implementation_sha256_lf": binding,
                   "fixture_status": "DEMO_NOT_A_TRAIN_DEV_EVAL_SPLIT"}
    observation["record_id"] = "ohm-demo-input-" + _digest(observation)
    target = {"schema": "cas.ohm.demo-target/0.1", "observation_id": observation["record_id"],
              "quantity_report": result, "implementation_sha256_lf": binding,
              "status": "REFERENCE_CALCULATED_NOT_LEARNED"}
    target["record_id"] = "ohm-demo-target-" + _digest(target)
    return {"schema": "cas.ohm.demo-pair/0.1", "observation": observation, "target": target,
            "generation_status": "REFERENCE_CALCULATED_NOT_LEARNED", "training_status": "NOT_RUN"}


def _restore_report(helper, record, depth=1, budget=None):
    """Replay the declared formula lineage, not a sensor or provenance claim."""
    if budget is None:
        budget = [0]
    budget[0] += 1
    _require(depth <= 16 and budget[0] <= 256, "OHM_CONNECTION_LIMIT", "Quantity lineage budget exceeded")
    _require(type(record) is dict and record.get("kind") == "cas_ohm_quantity", "OHM_CONNECTION_REPORT", "Expected a complete CAS-Ohm quantity report")
    _require(type(record.get("quantity")) is str and record["quantity"] in ("drive", "attention", "constraint"),
             "OHM_CONNECTION_REPORT", "Unknown quantity kind")
    origin = record.get("origin")
    if origin == "calculated":
        operation, inputs = record.get("operation"), record.get("inputs")
        _require(type(operation) is str and operation in _OPERATIONS and type(inputs) is list and len(inputs) == 2,
                 "OHM_CONNECTION_REPORT", "Calculation requires a known operation and two input reports")
        left, right = (_restore_report(helper, child, depth + 1, budget) for child in inputs)
        quantity = getattr(helper, _OPERATIONS[operation])(left, right)
    else:
        descriptor = record.get("scale")
        _require(type(descriptor) is dict, "OHM_CONNECTION_REPORT", "Quantity scale is missing")
        scale = helper.make_scale(descriptor.get("id"), descriptor.get("drive_unit"), descriptor.get("attention_unit"))
        literal, representation = record.get("input_literal"), record.get("numeric_representation")
        _require(type(literal) is str and len(literal) <= 1235, "OHM_CONNECTION_REPORT", "Quantity input literal is invalid")
        if representation == "integer":
            _require(re.fullmatch(r"-?[0-9]+", literal) is not None, "OHM_CONNECTION_REPORT", "Integer literal is invalid")
            value = int(Decimal(literal))  # bounded decimal conversion ignores ambient int string policy
        elif representation == "binary_float_via_shortest_decimal":
            try:
                value = float(literal)
            except ValueError as error:
                raise OhmConnectionError("OHM_CONNECTION_REPORT", "Float literal is invalid") from error
        elif representation == "exact_decimal_text":
            value = literal
        else:
            raise OhmConnectionError("OHM_CONNECTION_REPORT", "Unknown numeric input representation")
        quantity = helper.make_quantity(record.get("quantity"), value, scale, origin, record.get("reference"))
    # Canonical serialized equality is type sensitive: True cannot impersonate 1.
    _require(_json(quantity.to_dict()) == _json(record), "OHM_CONNECTION_REPORT", "Quantity report differs from its replayed formula/scale/provenance")
    return quantity


def project_cas_rpa(rows):
    """Retain explicitly supplied parent/child calculations in a read-only view.

    Each row has exactly node_id, parent_id (None for a root), quantity_report.
    IDs follow cncm.rpa_model's bounded identifier form. This separate schema
    supplies no AtlasContext, observation time, semantic status, or authority.
    Formula replay checks arithmetic consistency only; references remain unverified.
    """
    _require(type(rows) is list and 0 < len(rows) <= MAX_PROJECTION_NODES,
             "OHM_CONNECTION_LIMIT", "Projection needs 1..512 explicit node rows")
    _bounded_json(rows, MAX_PROJECTION_BYTES)
    _, helper, binding = _runtime()
    by_id = {}
    for row in rows:
        _fields(row, ("node_id", "parent_id", "quantity_report"), "projection row")
        node_id, parent = row["node_id"], row["parent_id"]
        _identifier(node_id, "node")
        if parent is not None:
            _identifier(parent, "parent")
        _require(node_id not in by_id, "OHM_RPA_DUPLICATE", f"Duplicate node: {node_id}")
        _bounded_json(row["quantity_report"], MAX_REPORT_BYTES)
        quantity = _restore_report(helper, row["quantity_report"])
        _require(quantity.origin == "calculated", "OHM_CONNECTION_REPORT", "Projection nodes require calculated reports, not bare declarations")
        by_id[node_id] = {"node_id": node_id, "parent_id": parent, "quantity_report": quantity.to_dict(), "children": []}
    for node_id, row in by_id.items():
        parent = row["parent_id"]
        if parent is not None:
            _require(parent in by_id, "OHM_RPA_PARENT", f"Missing parent: {parent}")
            by_id[parent]["children"].append(node_id)
        seen, current = set(), node_id
        while current is not None:
            _require(current not in seen, "OHM_RPA_CYCLE", "Parent links contain a cycle")
            seen.add(current)
            _require(len(seen) <= MAX_PROJECTION_DEPTH, "OHM_CONNECTION_LIMIT", "Projection parent depth exceeds 32")
            _require(current in by_id, "OHM_RPA_PARENT", f"Missing parent: {current}")
            current = by_id[current]["parent_id"]
    for row in by_id.values():
        row["children"].sort()
    _unchanged(binding)
    body = {"schema": "cas.rpa.ohm-projection/0.1", "status": "PREPARATORY_NOT_INTEGRATED",
            "nodes": [by_id[name] for name in sorted(by_id)],
            "roots": sorted(name for name, row in by_id.items() if row["parent_id"] is None),
            "parent_child_binding": "CALLER_DECLARED_UNVERIFIED", "aggregation_status": "NONE_NO_TOTAL_INFERRED",
            "formula_status": "REPLAYED_CALCULATION_ONLY", "provenance_status": "CALLER_REFERENCES_UNVERIFIED",
            "measurement_status": "NO_MEASUREMENT_PERFORMED", "runtime_status": "NOT_CONNECTED",
            "semantic_outcome": "NOT_ASSESSED", "authority": "NONE", "implementation_sha256_lf": binding}
    return {**body, "projection_sha256": _digest(body)}
