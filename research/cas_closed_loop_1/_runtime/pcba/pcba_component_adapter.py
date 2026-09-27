"""Strict, non-executing component boundary for the CCDL research reader.

Reuses the two existing syntax frontends, never their substring compiler
wrappers. Their exact source bytes are checked before use. Only enum class
definitions are taken from schemas; no cas_forex package or trading module is
imported. Appendix C supplies the added parameter rules. ``complete`` means
this adapter covers the component form, not that its circuit is valid or safe.
"""
from __future__ import annotations

import ast
import hashlib
import math
from pathlib import Path
import re
import sys
import threading
import types
from enum import Enum
from fractions import Fraction


SOURCE_ROOT = Path(__file__).resolve().parent / "pinned_sources" / "cas-forex" / "cas_forex"
ORIGINAL_SOURCE_ROOT = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex")
SOURCE_HASHES = {
    "pcba_syntax.py": "ca4728d4e03d1db2e627fb5eebea7370b6500309fcb04b64f15c4a5ed24ee7f1",
    "cjt_syntax.py": "ba05a2e889b638b2afef8ba67b5d1f3a9e62ac53c322f658281084129316f540",
    "schemas/pcba.py": "dfe920dfb22faf9a00438a9a76d92d5bd86336beb5d57ecb0aa40c7f829bce8d",
    "schemas/cjt.py": "c9cef41723e5cd6f8de3f3087faa430aa95cbf4c741fdbb11b659c9deab083b0",
}
AUTHORITY_SOURCE = {
    "path": str(Path(__file__).resolve().parent / "pinned_sources" / "pcba_book" / "Appendix_C_CCDL_Language_Reference.md"),
    "original_path": r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Appendix_C_CCDL_Language_Reference.md",
    "sha256": "452d64308f860b1c0e5b6c3f4d9c8a91760822baa9b9fcd1a6e12a4797983d8f",
    "sections": ["Passive Components", "One-Way and Threshold Components", "CJT Parameter Block Grammar"],
}
MAX_SOURCE_BYTES = 131072
MAX_EXPRESSION_CHARS = 16384
MAX_NESTING = 32
MAX_ARGUMENTS = 64
MAX_NUMBER_CHARS = 512
_LOCK = threading.RLock()
_FRONTENDS = None
_IDENT = r"[A-Za-z][A-Za-z0-9_]*"
_NUMBER = re.compile(r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)\Z")
_REGISTER = r"(?:[TAfE]|<[TAfE](?:,[TAfE])*>|⟨[TAfE](?:,[TAfE])*⟩)"
_STATE = re.compile(
    rf"\^[0-9](?:\|{_REGISTER}(?=\^[PCEO]))?(?:\^[PCEO])?"
    rf"(?:_\{{F_?[1-7](?:\|{_REGISTER})?\}})?(?:\|{_REGISTER})?\Z"
)
_RESERVED = set("circuit board input output node cjt feedback probe layer via let resistor cap capacitor inductor diode zener transformer opamp oscillator crystal varactor relay schmitt comparator integrator divider active_load mirror modulator pll tank filter diff mux demux gate xor xnor fuse reg led adc dac rectifier".split())
_BOOK_TYPES = set("CJT Resistor Capacitor Inductor Diode Zener Transformer OpAmp Oscillator CrystalOscillator Varactor Relay Schmitt SchmittTrigger Comparator Integrator LowPass HighPass LC PLL DutyCycle Differential Photodiode BridgeRectifier ADC DAC LED AND OR NOT NAND NOR XOR XNOR MUX DEMUX Regulator Fuse CircuitBreaker Phi".split())
_SUPPORTED = {"resistor", "capacitor", "inductor", "diode", "transformer"}
_CJT_ALIASES = {"β": "beta", "b": "beta", "saturation": "sat"}


class ComponentError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _verified_sources() -> dict[str, bytes]:
    result = {}
    for relative, expected in SOURCE_HASHES.items():
        path = SOURCE_ROOT / relative
        try:
            with path.open("rb") as stream:
                data = stream.read(MAX_SOURCE_BYTES + 1)
        except OSError as exc:
            raise ComponentError("E-COMP-SOURCE", f"Cannot read pinned frontend: {path}") from exc
        if len(data) > MAX_SOURCE_BYTES or hashlib.sha256(data).hexdigest() != expected:
            raise ComponentError("E-COMP-SOURCE", f"Pinned frontend bytes changed: {path}")
        result[relative] = data
    return result


def source_files() -> list[dict]:
    """Return verified read-only dependencies; no discovery or environment fallback."""
    sources = _verified_sources()
    return [
        {"path": str((SOURCE_ROOT / name).resolve()), "original_path": str(ORIGINAL_SOURCE_ROOT / name), "sha256": SOURCE_HASHES[name],
         "bytes": len(data), "use": "enum_class_only" if name.startswith("schemas/") else "syntax_parser_with_isolated_enum_import"}
        for name, data in sources.items()
    ]


def _load_frontends():
    global _FRONTENDS
    # Verify even when already loaded: an edited dependency must never be hidden
    # by a cached module. Executed code below is from these verified bytes.
    sources = _verified_sources()
    with _LOCK:
        if _FRONTENDS is not None:
            return _FRONTENDS
        loaded = []
        modules = []
        try:
            for stem, enum_name in (("pcba", "PcbaComponentKind"), ("cjt", "CjtRegion")):
                name = f"_helm_pcba_adapter_{SOURCE_HASHES[stem + '_syntax.py']}_{stem}"
                if name in sys.modules:
                    raise ComponentError("E-COMP-SOURCE", f"Private frontend namespace already occupied: {name}")
                module = types.ModuleType(name)
                module.__file__ = str(SOURCE_ROOT / (stem + "_syntax.py"))
                module.__dict__["Enum"] = Enum
                schema = ast.parse(sources[f"schemas/{stem}.py"], filename=str(SOURCE_ROOT / f"schemas/{stem}.py"))
                enum_nodes = [node for node in schema.body if isinstance(node, ast.ClassDef) and node.name == enum_name]
                if len(enum_nodes) != 1:
                    raise ComponentError("E-COMP-SOURCE", f"Expected one {enum_name} enum")
                sys.modules[name] = module
                loaded.append(name)
                exec(compile(ast.Module(body=enum_nodes, type_ignores=[]), module.__file__, "exec"), module.__dict__)
                tree = ast.parse(sources[stem + "_syntax.py"], filename=module.__file__)
                imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == f"cas_forex.schemas.{stem}"]
                if len(imports) != 1 or [item.name for item in imports[0].names] != [enum_name]:
                    raise ComponentError("E-COMP-SOURCE", "Unexpected frontend schema dependency")
                tree.body.remove(imports[0])
                exec(compile(tree, module.__file__, "exec"), module.__dict__)
                modules.append(module)
            _FRONTENDS = tuple(modules)
            return _FRONTENDS
        except ImportError as exc:
            for name in loaded:
                sys.modules.pop(name, None)
            raise ComponentError("E-COMP-DEPENDENCY", "Pinned syntax frontends require Pydantic 2") from exc
        except Exception:
            for name in loaded:
                sys.modules.pop(name, None)
            raise


def _scan(raw: str, *, outer: bool = False):
    """Split commas outside nested groups; arrows are never angle brackets."""
    pairs = {"<": ">", "[": "]", "(": ")", "{": "}", "⟨": "⟩"}
    stack = []
    start = 0
    pieces = []
    index = 0
    quoted = False
    while index < len(raw):
        char = raw[index]
        if char == '"':
            quoted = not quoted
        elif quoted:
            if char in "\r\n":
                raise ComponentError("E-COMP-SYNTAX", "A string cannot span lines")
        elif any(raw.startswith(arrow, index) for arrow in ("<->", "->", "=>", "<-")):
            index += 3 if raw.startswith("<->", index) else 2
            continue
        elif char in pairs:
            stack.append(pairs[char])
            if len(stack) > MAX_NESTING:
                raise ComponentError("E-COMP-LIMIT", "Component nesting limit exceeded")
        elif char in pairs.values():
            if not stack or stack.pop() != char:
                raise ComponentError("E-COMP-SYNTAX", "Unbalanced component delimiters")
            if outer and not stack:
                return index
        elif char == "," and not stack:
            pieces.append(raw[start:index].strip())
            start = index + 1
        index += 1
    if stack or quoted:
        raise ComponentError("E-COMP-SYNTAX", "Unclosed component delimiter or string")
    if outer:
        raise ComponentError("E-COMP-SYNTAX", "Missing component closing angle bracket")
    pieces.append(raw[start:].strip())
    if len(pieces) > MAX_ARGUMENTS:
        raise ComponentError("E-COMP-LIMIT", "Too many component arguments")
    if any(not item for item in pieces):
        raise ComponentError("E-COMP-SYNTAX", "Empty component argument")
    return pieces


def _parts(expression: str):
    if not isinstance(expression, str) or not expression.strip():
        raise ComponentError("E-COMP-SYNTAX", "Component expression must be nonempty text")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise ComponentError("E-COMP-LIMIT", "Component expression length limit exceeded")
    text = expression.strip()
    if text.endswith(";"):
        text = text[:-1].rstrip()
    if text.startswith("let "):
        alias = re.match(rf"let\s+({_IDENT})\s*=\s*", text)
        if not alias or alias[1] in _RESERVED or alias[1] in _BOOK_TYPES:
            raise ComponentError("E-COMP-SYNTAX", "Invalid component alias")
        text = text[alias.end():]
    head = re.match(rf"({_IDENT})(?:\(([^()]*)\))?\s*<", text)
    if not head:
        raise ComponentError("E-COMP-SYNTAX", "Expected Type<...> component expression")
    opening = head.end() - 1
    closing = opening + _scan(text[opening:], outer=True)
    tail = text[closing + 1:].strip()
    suffix = ""
    if tail:
        if not tail.startswith("[") or not tail.endswith("]"):
            raise ComponentError("E-COMP-SYNTAX", "Unexpected text after component")
        suffix = tail[1:-1]
        if not suffix.strip():
            raise ComponentError("E-COMP-SYNTAX", "Empty parameter block")
    return head[1], head[2] or "", text[opening + 1:closing], suffix


def _parameter_items(block: str, *, aliases: bool = False) -> list[tuple[str, str]]:
    if not block.strip():
        return []
    result = []
    for token in _scan(block):
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_]*|β|rπ)\s*=\s*(.+)", token, re.DOTALL)
        if not match:
            raise ComponentError("E-COMP-PARAM", f"Expected key=value parameter: {token}")
        key = _CJT_ALIASES.get(match[1], match[1]) if aliases else match[1]
        result.append((key, match[2].strip()))
    return result


def _unique(items: list[tuple[str, str]]) -> dict[str, str]:
    result = {}
    for key, value in items:
        if key in result:
            raise ComponentError("E-COMP-DUPLICATE", f"Duplicate parameter: {key}")
        result[key] = value
    return result


def _number(key: str, raw: str):
    if len(raw) > MAX_NUMBER_CHARS:
        raise ComponentError("E-COMP-LIMIT", f"Parameter {key} exceeds the 512-character decimal limit")
    if not _NUMBER.fullmatch(raw):
        raise ComponentError("E-COMP-PARAM", f"Parameter {key} requires a finite decimal number")
    number = float(raw)
    if not math.isfinite(number):
        raise ComponentError("E-COMP-PARAM", f"Parameter {key} requires a finite decimal number")
    return int(raw) if "." not in raw else number


def _reference(raw: str, *, domain: bool = False) -> str:
    text = raw.strip()
    if re.fullmatch(_IDENT, text) and text not in _RESERVED and text not in _BOOK_TYPES:
        return text
    if _STATE.fullmatch(text) or (domain and re.fullmatch(r"\^[PCEO]", text)):
        return text
    raise ComponentError("E-COMP-TERMINAL", f"Expected one complete {'domain or ' if domain else ''}state/reference: {text}")


def _cjt(frontend, prefix: str, body: str, suffix: str) -> dict:
    raw = _unique(_parameter_items(prefix, aliases=True) + _parameter_items(suffix, aliases=True))
    allowed = {"beta", "sat", "cutoff", "region", "gm", "rπ"}
    if set(raw) - allowed:
        raise ComponentError("E-COMP-PARAM", f"Unknown CJT parameter: {sorted(set(raw) - allowed)[0]}")
    literals = {"beta": "1.0", "sat": "0.95", "cutoff": "0.1", "region": "active", **raw}
    parameters = {"beta": 1.0, "sat": 0.95, "cutoff": 0.1, "region": "active"}
    parameters.update({key: value if key == "region" else _number(key, value) for key, value in raw.items()})
    if parameters["region"] not in {"active", "cutoff", "saturation", "breakdown"}:
        raise ComponentError("E-COMP-PARAM", "Invalid intended CJT region")
    exact = {key: Fraction(value) for key, value in literals.items() if key != "region"}
    if any(exact[key] < 0 for key in ("beta", "gm", "rπ") if key in exact):
        raise ComponentError("E-COMP-PARAM", "beta, gm and rπ must be nonnegative")
    if not 0 <= exact["cutoff"] < exact["sat"] <= 1:
        raise ComponentError("E-COMP-PARAM", "CJT requires 0 <= cutoff < sat <= 1")
    # gm/rπ are checked and preserved here; the older frontend has no fields
    # for them. Use original decimal strings, never its lossy :g serializer.
    old_params = ", ".join(f"{key}={raw.get(key, value)}" for key, value in parameters.items() if key not in {"gm", "rπ"})
    try:
        node = frontend.parse_cjt_expression(f"CJT< {body} > [{old_params}]".replace("\r", " ").replace("\n", " "))
    except ValueError as exc:
        raise ComponentError("E-COMP-SYNTAX", str(exc)) from exc
    terminals = {role: _reference(getattr(node, role)) for role in ("cause", "bias", "effect")}
    return {"type": "CJT", "kind": "cjt", "parameters": parameters, "parameter_literals": literals,
            "terminals": terminals, "complete": True, "diagnostics": []}


def parse_component(expression: str) -> dict:
    """Read one component; board name resolution and CAS checking are separate."""
    type_name, prefix, body, suffix = _parts(expression)
    pcba, cjt = _load_frontends()
    if type_name == "CJT":
        return _cjt(cjt, prefix, body, suffix)
    if prefix:
        raise ComponentError("E-COMP-SYNTAX", "Prefix parameters are supported only for CJT")
    enum = pcba.COMPONENT_ALIASES.get(type_name.lower())
    if enum is None and type_name not in _BOOK_TYPES:
        raise ComponentError("E-COMP-SYNTAX", f"Unknown component type: {type_name}")
    kind = enum.value if enum is not None else type_name.lower()
    tokens = _scan(body)
    args = []
    pairs = []
    for token in tokens:
        if re.match(r"(?:[A-Za-z][A-Za-z0-9_]*|β|rπ)\s*=", token):
            pairs.extend(_parameter_items(token))
        else:
            args.append(token)
    pairs.extend(_parameter_items(suffix))
    raw = _unique(pairs)
    if kind not in _SUPPORTED:
        # Preserve syntax we cannot check. Do not manufacture terminal roles or
        # claim the permissive older component parser validated a whole board.
        return {"type": type_name, "kind": kind, "parameters": raw, "parameter_literals": dict(raw), "terminals": {}, "raw_arguments": args,
                "complete": False, "diagnostics": [{"code": "UNSUPPORTED_COMPONENT", "severity": "warning", "message": f"{type_name} is preserved; component semantics are not checked."}]}
    if len(args) != 1:
        raise ComponentError("E-COMP-TERMINAL", f"{type_name} requires exactly one state or directed pair")
    required = {"resistor": "R", "capacitor": "C", "inductor": "L", "transformer": "ratio"}.get(kind)
    allowed = {required} if required else set()
    if kind == "capacitor":
        allowed.add("leakage")
    if set(raw) - allowed:
        raise ComponentError("E-COMP-PARAM", f"Unknown {type_name} parameter: {sorted(set(raw) - allowed)[0]}")
    if required and required not in raw:
        raise ComponentError("E-COMP-PARAM", f"Missing {type_name} parameter: {required}")
    parameters = {key: _number(key, value) for key, value in raw.items()}
    exact = {key: Fraction(value) for key, value in raw.items()}
    if any(value < 0 for value in exact.values()) or (kind == "transformer" and exact["ratio"] <= 0):
        raise ComponentError("E-COMP-PARAM", f"Invalid {type_name} parameter range")
    if "leakage" in exact and exact["leakage"] > 1:
        raise ComponentError("E-COMP-PARAM", "Capacitor leakage must be in [0,1]")
    if kind in {"diode", "transformer"}:
        pair = args[0].split("->")
        if len(pair) != 2:
            raise ComponentError("E-COMP-TERMINAL", f"{type_name} requires source -> target")
        terminals = {"source": _reference(pair[0], domain=True), "target": _reference(pair[1], domain=True)}
    else:
        terminals = {"state": _reference(args[0])}
    # The original splitter understands ASCII register-set brackets. Normalize
    # Unicode brackets for that parser only; preserve the actual terminal text
    # above. Ignore its float-mediated numeric values (large integers lose bits).
    old_terminal = args[0].replace("⟨", "<").replace("⟩", ">")
    legacy_raw = dict(raw)
    if kind == "transformer" and parameters["ratio"] == 0:
        # The exact positive ratio already passed above. The old frontend only
        # checks float>0 and cannot represent a subnormal-underflow decimal;
        # supply a positive representative solely for its redundant range guard.
        # All public values and downstream checks retain the original literal.
        legacy_raw["ratio"] = "1"
    old_args = [old_terminal] + [f"{key}={value}" for key, value in legacy_raw.items()]
    try:
        node = pcba.parse_pcba_component_expression(f"{type_name}< {', '.join(old_args)} >")
    except ValueError as exc:
        raise ComponentError("E-COMP-SYNTAX", str(exc)) from exc
    return {"type": type_name, "kind": node.kind.value, "parameters": parameters, "parameter_literals": dict(raw),
            "terminals": terminals, "complete": True, "diagnostics": []}
