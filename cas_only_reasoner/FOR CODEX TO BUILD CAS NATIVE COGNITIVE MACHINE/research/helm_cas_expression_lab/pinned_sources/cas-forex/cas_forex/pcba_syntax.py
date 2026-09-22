"""Research parser for PCBA-style CAS component syntax."""

from __future__ import annotations

import math
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

from cas_forex.schemas.pcba import PcbaComponentKind


class PcbaSyntaxError(ValueError):
    """Raised when a PCBA component expression is malformed."""


COMPONENT_ALIASES = {
    "resistor": PcbaComponentKind.RESISTOR,
    "capacitor": PcbaComponentKind.CAPACITOR,
    "inductor": PcbaComponentKind.INDUCTOR,
    "diode": PcbaComponentKind.DIODE,
    "transformer": PcbaComponentKind.TRANSFORMER,
    "opamp": PcbaComponentKind.OP_AMP,
    "op_amp": PcbaComponentKind.OP_AMP,
    "operationalamplifier": PcbaComponentKind.OP_AMP,
    "oscillator": PcbaComponentKind.OSCILLATOR,
    "logicgate": PcbaComponentKind.LOGIC_GATE,
    "logic_gate": PcbaComponentKind.LOGIC_GATE,
    "mux": PcbaComponentKind.MUX,
    "demux": PcbaComponentKind.DEMUX,
    "regulator": PcbaComponentKind.REGULATOR,
    "fuse": PcbaComponentKind.FUSE,
    "circuitbreaker": PcbaComponentKind.CIRCUIT_BREAKER,
    "circuit_breaker": PcbaComponentKind.CIRCUIT_BREAKER,
    "trace": PcbaComponentKind.TRACE,
    "via": PcbaComponentKind.VIA,
    "varactor": PcbaComponentKind.VARACTOR,
    "relay": PcbaComponentKind.RELAY,
    "schmitttrigger": PcbaComponentKind.SCHMITT_TRIGGER,
    "schmitt_trigger": PcbaComponentKind.SCHMITT_TRIGGER,
    "photodiode": PcbaComponentKind.PHOTODIODE,
    "crystaloscillator": PcbaComponentKind.CRYSTAL_OSCILLATOR,
    "crystal_oscillator": PcbaComponentKind.CRYSTAL_OSCILLATOR,
    "adc": PcbaComponentKind.ADC,
    "dac": PcbaComponentKind.DAC,
    "bridgerectifier": PcbaComponentKind.BRIDGE_RECTIFIER,
    "bridge_rectifier": PcbaComponentKind.BRIDGE_RECTIFIER,
}

_WRAPPER_RE = re.compile(r"^\s*(?:let\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*)?(?P<body>.+?)\s*;?\s*$")
_COMPONENT_RE = re.compile(r"^(?P<component>[A-Za-z_][A-Za-z0-9_]*)\s*<(?P<body>.*)>\s*$", re.DOTALL)


class PcbaComponentNode(BaseModel):
    name: Optional[str] = None
    kind: PcbaComponentKind
    component_name: str
    args: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_component(self):
        if not self.args and not self.params:
            raise ValueError("PCBA component body cannot be empty")
        _validate_params(self.kind, self.params)
        return self

    def to_expression(self) -> str:
        prefix = f"let {self.name} = " if self.name else ""
        parts = list(self.args)
        parts.extend(f"{key}={_format_value(value)}" for key, value in self.params.items())
        return f"{prefix}{self.component_name}< {', '.join(parts)} >;"


def parse_pcba_component_expression(expression: str) -> PcbaComponentNode:
    """Parse a PCBA component expression into a research IR node."""

    wrapper = _WRAPPER_RE.match(expression)
    if not wrapper:
        raise PcbaSyntaxError("Invalid PCBA expression wrapper")
    body_expr = wrapper.group("body").strip()
    match = _COMPONENT_RE.match(body_expr)
    if not match:
        raise PcbaSyntaxError("Expected Component< ... > syntax")

    component_name = match.group("component")
    kind = _component_kind(component_name)
    tokens = _split_top_level(match.group("body"))
    args: list[str] = []
    params: dict[str, Any] = {}
    for token in tokens:
        if not token:
            continue
        key, value = _split_param(token)
        if key is None:
            args.append(token.strip())
        else:
            params[key] = _parse_value(value)

    try:
        return PcbaComponentNode(
            name=wrapper.group("name"),
            kind=kind,
            component_name=component_name,
            args=args,
            params=params,
        )
    except ValueError as exc:
        raise PcbaSyntaxError(str(exc)) from exc


def roundtrip_pcba_component_expression(expression: str) -> PcbaComponentNode:
    first = parse_pcba_component_expression(expression)
    second = parse_pcba_component_expression(first.to_expression())
    if first != second:
        raise PcbaSyntaxError("PCBA roundtrip changed the IR")
    return second


def _component_kind(name: str) -> PcbaComponentKind:
    normalized = re.sub(r"[^A-Za-z0-9_]", "", name).lower()
    if normalized not in COMPONENT_ALIASES:
        raise PcbaSyntaxError(f"Unknown PCBA component '{name}'")
    return COMPONENT_ALIASES[normalized]


def _split_top_level(raw: str) -> list[str]:
    parts: list[str] = []
    start = 0
    angle_depth = 0
    square_depth = 0
    for index, char in enumerate(raw):
        if char == "<":
            angle_depth += 1
        elif char == ">" and (index == 0 or raw[index - 1] != "-"):
            angle_depth -= 1
            if angle_depth < 0:
                raise PcbaSyntaxError("Unbalanced angle bracket")
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth -= 1
            if square_depth < 0:
                raise PcbaSyntaxError("Unbalanced square bracket")
        elif char == "," and angle_depth == 0 and square_depth == 0:
            parts.append(raw[start:index].strip())
            start = index + 1
    if angle_depth != 0 or square_depth != 0:
        raise PcbaSyntaxError("Unbalanced PCBA component body")
    parts.append(raw[start:].strip())
    return parts


def _split_param(token: str) -> tuple[Optional[str], str]:
    match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", token, re.DOTALL)
    if not match:
        return None, token
    return match.group(1), match.group(2).strip()


def _parse_value(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_value(part) for part in _split_top_level(inner)]
    try:
        number = float(value)
    except ValueError:
        return value.strip()
    if not math.isfinite(number):
        raise PcbaSyntaxError(f"Invalid non-finite value '{value}'")
    return int(number) if number.is_integer() else number


def _validate_params(kind: PcbaComponentKind, params: dict[str, Any]) -> None:
    for key, value in params.items():
        if isinstance(value, (int, float)) and not math.isfinite(float(value)):
            raise PcbaSyntaxError(f"Invalid non-finite parameter '{key}'")
        if key in {"R", "C", "L", "open_loop_gain"} and isinstance(value, (int, float)) and value < 0:
            raise PcbaSyntaxError(f"Parameter '{key}' must be non-negative")
        if key in {"leakage", "threshold", "tolerance", "duty_cycle"}:
            if not isinstance(value, (int, float)) or value < 0 or value > 1:
                raise PcbaSyntaxError(f"Parameter '{key}' must be between 0 and 1")
        if key in {"ratio", "frequency"}:
            if not isinstance(value, (int, float)) or value <= 0:
                raise PcbaSyntaxError(f"Parameter '{key}' must be positive")

    if kind == PcbaComponentKind.LOGIC_GATE and params.get("gate"):
        allowed = {"AND", "OR", "NOT", "NAND", "NOR", "XOR"}
        if str(params["gate"]).upper() not in allowed:
            raise PcbaSyntaxError("Unsupported logic gate")


def _format_value(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
