"""Bounded CCDL schematic checks. No circuit execution or Helm training.

PASS means only the declared static scope passed, not full-book validation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from fractions import Fraction
from functools import lru_cache
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

from pcba_reader import PcbaParseError, parse_pcba_document
from pcba_component_adapter import ComponentError, parse_component, source_files, AUTHORITY_SOURCE

SCHEMA = "cas.pcba.check/0.1"
COMPILER_SHA256_LF = "61ed5a45970459e49a6948282ce4060e7c3d3d3f7042078228bc97ff252b2527"
DOMAIN_ORDER = {"P": 0, "C": 1, "E": 2, "O": 3}
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)\Z")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
MAX_GRAPH_STEPS = 20000


@lru_cache(maxsize=1)
def _compiler():
    """Load the historical state checker; new arithmetic uses the active compiler."""
    path = Path(__file__).resolve().parent / "pinned_sources/compiler_pre_ohm_61ed5a45.py"
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != COMPILER_SHA256_LF:
        raise ValueError("CAS compiler source differs from the reviewed pin")
    name = "_pcba_state_compiler_" + COMPILER_SHA256_LF[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        exec(compile(raw, str(path), "exec"), module.__dict__)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _state(raw):
    compiler = _compiler()
    parser = compiler.Parser(compiler.lex(raw))
    state = parser.parse_state()
    parser.expect(compiler.TokenKind.EOF)
    if not state.domain_explicit:
        raise ValueError("a schematic state must have an explicit Domain")
    compiler._infer(state, [])
    return asdict(state)


def _report():
    return {
        "schema": SCHEMA, "parse_status": "FAIL", "structural_status": "NOT_RUN",
        "valid": False, "diagnostics": [], "document": None,
        "netlist": {"symbols": {}, "components": {}, "edges": [], "loops": []},
        "execution_status": "NOT_IMPLEMENTED", "helm_status": "NOT_TRAINED",
        "scope": "bounded schematic static checks; not full CCDL or runtime validation",
        "full_book_validation_status": "UNVERIFIED",
        "engine_admissibility_status": "NOT_RUN_OPERATOR_UNSPECIFIED",
        "sources": {"compiler_sha256_lf": COMPILER_SHA256_LF},
    }


class _Checker:
    def __init__(self, report):
        self.report = report
        self.netlist = report["netlist"]
        self.symbols = self.netlist["symbols"]
        self.components = self.netlist["components"]
        self.statements = []
        self.used = set()
        self.inline = {}
        self.passive_nets = set()

    def diagnostic(self, code, message, statement=None, severity="error"):
        loc = (statement or {}).get("location", {"line": 1, "column": 1})
        self.report["diagnostics"].append({
            "code": code, "severity": severity, "message": message,
            "line": loc["line"], "column": loc["column"],
        })

    def declare(self, name, kind, statement, **extra):
        if name in self.symbols:
            self.diagnostic("E-PCBA-DUPLICATE", f"Duplicate or conflicting name: {name}", statement)
            return False
        self.symbols[name] = {"kind": kind, "location": statement["location"], **extra}
        return True

    def collect(self, statements, layer=None):
        for statement in statements:
            kind, name = statement["kind"], statement.get("name")
            if kind == "layer":
                self.declare(name, kind, statement, domain=statement["domain"])
                self.collect(statement["statements"], statement["domain"])
                continue
            self.statements.append(statement)
            if kind in ("input", "output"):
                if not statement["names"]:
                    self.diagnostic("E-PCBA-IO", "Empty I/O declaration", statement)
                for io_name in statement["names"]:
                    self.declare(io_name, kind, statement, domain=None)
            elif kind == "node":
                state = self.parse_state(statement["state"], statement)
                if state and layer and state["domain"] != layer:
                    self.diagnostic("E-PCBA-LAYER", f"Node {name} Domain {state['domain']} does not match layer {layer}", statement)
                self.declare(name, kind, statement, state=state, domain=state["domain"] if state else None)
            elif name:
                self.declare(name, kind, statement, domain=None)

    def parse_state(self, raw, statement):
        try:
            return _state(raw)
        except (ValueError, RecursionError) as error:
            self.diagnostic("E-PCBA-STATE", f"Invalid complete state {raw!r}: {error}", statement)
        except (OSError, ImportError) as error:
            self.diagnostic("U-PCBA-COMPILER", f"State compiler unavailable: {error}", statement, "unverified")
        return None

    def resolve(self, raw, statement, role):
        raw = raw.strip()
        if raw in self.symbols:
            symbol = self.symbols[raw]
            self.used.add(raw)
            if symbol["kind"] not in ("node", "input", "output", "component"):
                self.diagnostic("E-PCBA-TERMINAL", f"{raw} is a {symbol['kind']}, not a terminal", statement)
                return None
            if symbol["domain"] is None:
                self.diagnostic("U-PCBA-TERMINAL", f"{raw} has no resolved state type or explicit component port", statement, "unverified")
            return {"id": "name:" + raw, "reference": raw, "domain": symbol["domain"], "state": symbol.get("state")}
        if raw in DOMAIN_ORDER or (raw.startswith("^") and raw[1:] in DOMAIN_ORDER):
            state, domain = None, raw.lstrip("^")
        elif IDENTIFIER.fullmatch(raw):
            self.diagnostic("E-PCBA-UNRESOLVED", f"Unresolved terminal: {raw}", statement)
            return None
        else:
            state = self.parse_state(raw, statement)
            if not state:
                return None
            domain = state["domain"]
        # Same state text never implicitly joins distinct named nets.
        key = f"inline:{statement['location']['line']}:{statement['location']['column']}:{role}"
        identity = json.dumps(state, sort_keys=True) if state else "domain:" + domain
        self.inline.setdefault(identity, []).append((key, statement))
        return {"id": key, "reference": raw, "domain": domain, "state": state}

    def descent(self, source, target, statement, feedback=False):
        if not source or not target or not source["domain"] or not target["domain"]:
            return
        if DOMAIN_ORDER[target["domain"]] < DOMAIN_ORDER[source["domain"]]:
            if feedback:
                self.diagnostic("U-PCBA-FEEDBACK-POLICY", "Explicit upward feedback preserved; the book does not define a complete low-gain acceptance policy", statement, "unverified")
            else:
                self.diagnostic("E-CJT-008", f"Upward Domain transition {source['domain']} -> {target['domain']} requires deliberate feedback", statement)

    def edge(self, source, target, gain, statement, role):
        if source and target:
            self.netlist["edges"].append({
                "id": len(self.netlist["edges"]), "source": source["id"],
                "target": target["id"], "gain_literal": gain, "kind": role,
                "location": statement["location"],
            })

    def component(self, statement):
        try:
            component = parse_component(statement["expression"])
        except ComponentError as error:
            self.diagnostic(error.code, str(error), statement)
            return
        name = statement["name"]
        self.components[name] = component
        for diagnostic in component.get("diagnostics", []):
            self.diagnostic(diagnostic["code"], diagnostic["message"], statement, diagnostic["severity"])
        prefix_type = {"cap": "capacitor"}.get(statement["prefix"], statement["prefix"])
        if prefix_type != "let" and prefix_type.lower() != component["type"].lower() and component["complete"]:
            self.diagnostic("E-DECL-002", f"Declaration {statement['prefix']} does not match {component['type']}", statement)
        if not component["complete"]:
            self.diagnostic("U-PCBA-COMPONENT", f"{component['type']} is preserved but unsupported", statement, "unverified")
            return
        terminals = {role: self.resolve(raw, statement, role) for role, raw in component["terminals"].items()}
        component["resolved_terminals"] = terminals
        if statement["prefix"] == "let":
            self.diagnostic("U-PCBA-MACRO", "Reusable component declaration preserved; macro instantiation is not implemented", statement, "unverified")
            return
        params = component["parameter_literals"]
        if component["type"].lower() == "cjt":
            cause, bias, effect = (terminals.get(role) for role in ("cause", "bias", "effect"))
            if cause and effect and cause["domain"] and effect["domain"]:
                if DOMAIN_ORDER[effect["domain"]] < DOMAIN_ORDER[cause["domain"]]:
                    self.diagnostic("U-PCBA-CJT-ADMISSIBILITY", "Upward CJT cause-to-effect connection needs an operator admissibility policy; the book's guard example permits one", statement, "unverified")
            if cause and bias and cause["domain"] and bias["domain"]:
                if DOMAIN_ORDER[bias["domain"]] > DOMAIN_ORDER[cause["domain"]]:
                    self.diagnostic("E-CJT-002", "Bias Domain is below cause Domain (Appendix C; Chapter 4's printed example conflicts with this rule)", statement)
            self.edge(cause, effect, params.get("beta"), statement, "cjt_cause")
            self.edge(bias, effect, params.get("gm"), statement, "cjt_bias")
        elif "source" in terminals and "target" in terminals:
            self.descent(terminals["source"], terminals["target"], statement)
            # Ratio alone is not a complete small-signal transfer model.
            self.edge(terminals["source"], terminals["target"], None, statement, component["type"])
        elif terminals.get("state"):
            # R/C/L declarations constrain a net, but no transfer equation was
            # supplied. They cannot disappear from a claim about loop gain.
            self.passive_nets.add(terminals["state"]["id"])

    def connection(self, statement):
        source = self.resolve(statement["source"], statement, "source")
        target = self.resolve(statement["target"], statement, "target")
        params = {}
        for key, value in statement.get("parameters", {}).items():
            normalized = {"β": "beta", "b": "beta"}.get(key, key)
            if normalized in params:
                self.diagnostic("E-PCBA-DUPLICATE-PARAMETER", f"Duplicate parameter {normalized}", statement)
            elif normalized not in ("beta", "tau"):
                self.diagnostic("U-PCBA-PARAMETER", f"Unsupported connection parameter {key}", statement, "unverified")
            elif len(value) > 512:
                self.diagnostic("E-PCBA-LIMIT", f"{key} exceeds the 512-character numeric limit", statement)
            elif not NUMBER.fullmatch(value) or not math.isfinite(float(value)) or Fraction(value) < 0:
                self.diagnostic("E-PCBA-PARAMETER", f"{key} must be a finite nonnegative decimal", statement)
            else:
                params[normalized] = value
        deliberate = statement["kind"] == "feedback" or (statement["kind"] == "via" and "beta" in params)
        self.descent(source, target, statement, feedback=deliberate)
        self.edge(source, target, params.get("beta"), statement, statement["kind"])

    def assertion_value(self, raw, statement):
        match = re.fullmatch(r"([A-Za-z_]\w*)\.(bias|beta|gm|rpi|rπ|sat|cutoff)", raw.strip())
        if match:
            name, attr = match.groups()
            component = self.components.get(name)
            if not component:
                self.diagnostic("E-PCBA-ASSERT", f"Unknown component in assertion: {name}", statement)
                return None
            if attr == "bias":
                terminal = component.get("resolved_terminals", {}).get("bias")
                if terminal:
                    if terminal["id"].startswith("inline:"):
                        self.diagnostic("U-PCBA-ASSERT", "Inline bias net identity is not established; use a named node for equality", statement, "unverified")
                        return None
                    return ("terminal", terminal["id"])
            else:
                aliases = {"rpi": "rπ"}
                value = component["parameter_literals"].get(aliases.get(attr, attr))
                if value is not None:
                    return ("number", Fraction(str(value)))
            self.diagnostic("U-PCBA-ASSERT", f"Unknown property {raw}", statement, "unverified")
            return None
        if len(raw) <= 512 and NUMBER.fullmatch(raw.strip()) and math.isfinite(float(raw)):
            return ("number", Fraction(raw))
        self.diagnostic("U-PCBA-ASSERT", f"Unsupported assertion operand: {raw}", statement, "unverified")
        return None

    def assertion(self, statement):
        if statement["operator"] != "==":
            self.diagnostic("U-PCBA-ASSERT", "Only equality of declared bias/parameter properties is implemented", statement, "unverified")
            return
        left = self.assertion_value(statement["left"], statement)
        right = self.assertion_value(statement["right"], statement)
        if left is not None and right is not None and left != right:
            self.diagnostic("E-PCBA-ASSERT", f"Static assertion failed: {statement['left']} == {statement['right']}", statement)

    def loops(self):
        """Bounded iterative simple-cycle search, retaining parallel edges."""
        outgoing = {}
        for edge in self.netlist["edges"]:
            outgoing.setdefault(edge["source"], []).append(edge)
        steps = 0
        cycle_nodes_seen = set()
        coupling_reported = False
        for start in sorted(outgoing):
            stack = [(start, frozenset((start,)), ())]
            while stack:
                node, visited, path = stack.pop()
                for edge in outgoing.get(node, []):
                    steps += 1
                    if steps > MAX_GRAPH_STEPS:
                        self.diagnostic("U-PCBA-GRAPH-LIMIT", "Loop search budget exceeded; remaining loops are unverified", severity="unverified")
                        return
                    target = edge["target"]
                    if target == start:
                        cycle = path + (edge,)
                        cycle_nodes = {part["source"] for part in cycle}
                        if cycle_nodes_seen.intersection(cycle_nodes) and not coupling_reported:
                            self.diagnostic("U-PCBA-COUPLED-LOOPS", "Loops share nodes; their combined transfer is not defined by individual path gains", edge, "unverified")
                            coupling_reported = True
                        cycle_nodes_seen.update(cycle_nodes)
                        gains = [part["gain_literal"] for part in cycle]
                        passive = any(part["source"] in self.passive_nets or part["target"] in self.passive_nets for part in cycle)
                        unknown = any(gain is None for gain in gains) or passive
                        product = None
                        if not unknown:
                            product = Fraction(1)
                            for gain in gains:
                                product *= Fraction(gain)
                                if max(product.numerator.bit_length(), product.denominator.bit_length()) > 65536:
                                    self.diagnostic("U-PCBA-GAIN-LIMIT", "Exact loop gain proof exceeds the numeric budget", edge, "unverified")
                                    unknown, product = True, None
                                    break
                        display_product = None
                        if product is not None:
                            display_product = str(product) if max(product.numerator.bit_length(), product.denominator.bit_length()) <= 1024 else ("EXACT_GE_1" if product >= 1 else "EXACT_LT_1")
                        self.netlist["loops"].append({
                            "edges": [part["id"] for part in cycle],
                            "gain_status": "UNKNOWN" if unknown else "KNOWN",
                            "gain_product": display_product,
                            "unmodelled_passive": passive,
                        })
                        if unknown:
                            self.diagnostic("U-PCBA-LOOP-GAIN", "Feedback loop contains an unknown transfer/gain or unmodelled passive; stability is unverified", edge, "unverified")
                        elif product >= 1:
                            self.diagnostic("E-CJT-005", f"Complete feedback loop gain {display_product} is >= 1", edge)
                    elif target not in visited and target > start:
                        stack.append((target, visited | {target}, path + (edge,)))

    def check(self, document):
        self.collect(document["statements"])
        if document["kind"] == "circuit":
            for kind in ("input", "output", "component"):
                if not any(s["kind"] == kind for s in self.statements):
                    self.diagnostic("E-PCBA-MINIMAL-CIRCUIT", f"Circuit requires a declared {kind}")
        for statement in self.statements:
            if statement["kind"] == "component":
                self.component(statement)
        for statement in self.statements:
            kind = statement["kind"]
            if kind in ("feedback", "via", "transition", "series"):
                self.connection(statement)
            elif kind == "probe":
                self.resolve(statement["target"], statement, "probe")
            elif kind == "assert":
                self.assertion(statement)
        for name, symbol in self.symbols.items():
            if symbol["kind"] in ("input", "output") and name not in self.used:
                self.diagnostic("W-PCBA-UNCONNECTED-IO", f"Declared {symbol['kind']} {name} is unconnected; no wiring was inferred", symbol, "warning")
        for identity, uses in self.inline.items():
            if len(uses) > 1:
                self.diagnostic("U-PCBA-INLINE-TOPOLOGY", "Repeated inline state/domain does not establish shared net identity; use named nodes for complete loop checking", uses[0][1], "unverified")
        self.loops()
        severities = {d["severity"] for d in self.report["diagnostics"]}
        self.report["structural_status"] = "FAIL" if "error" in severities else "UNVERIFIED" if "unverified" in severities else "PASS"
        self.report["valid"] = self.report["structural_status"] == "PASS"


def check_pcba_document(source):
    """Return JSON-safe separate parse, structural, execution and Helm results."""
    report = _report()
    try:
        report["document"] = parse_pcba_document(source)
    except PcbaParseError as error:
        report["parse_status"] = "UNSUPPORTED" if "UNSUPPORTED" in error.code else "FAIL"
        report["diagnostics"].append({
            "code": error.code, "severity": "error", "message": str(error),
            "line": error.line, "column": error.column,
        })
        return report
    report["parse_status"] = "PASS"
    report["sources"]["implementation_sha256_lf"] = {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in ("pcba_check.py", "pcba_reader.py", "pcba_component_adapter.py")
    }
    try:
        report["sources"]["component_frontends"] = source_files()
        report["sources"]["book_authority"] = AUTHORITY_SOURCE
    except ComponentError as error:
        report["diagnostics"].append({"code": error.code, "severity": "unverified", "message": str(error), "line": 1, "column": 1})
    _Checker(report).check(report["document"])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="UTF-8 circuit or board source")
    args = parser.parse_args(argv)
    try:
        with args.source.open("rb") as handle:
            raw = handle.read(65537)
        if len(raw) > 65536:
            raise ValueError("Source exceeds the 64 KiB limit")
        report = check_pcba_document(raw.decode("utf-8-sig"))
        report["input"] = {"path": str(args.source.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    except (OSError, UnicodeError, ValueError) as error:
        report = _report()
        report["diagnostics"].append({"code": "E-PCBA-INPUT", "severity": "error", "message": str(error), "line": 1, "column": 1})
    print(json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
