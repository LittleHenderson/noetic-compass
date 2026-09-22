"""Research parser for CJT<> syntax.

This parser proves the proposed syntax can be represented safely as an IR
sidecar. It is intentionally disconnected from broker execution and the
production CAS compiler authority path.
"""

from __future__ import annotations

import math
import re
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from cas_forex.schemas.cjt import CjtRegion


class CjtSyntaxError(ValueError):
    """Raised when a CJT<> expression is malformed."""


_LET_RE = re.compile(r"^\s*(?:let\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*)?(?P<body>.+?)\s*;?\s*$")
_CJT_RE = re.compile(
    r"^CJT(?:\((?P<prefix_params>[^)]*)\))?\s*<(?P<body>.+)>\s*(?:\[(?P<bracket_params>[^\]]*)\])?$",
    re.DOTALL,
)
_BODY_RE = re.compile(r"^\s*(?P<cause>.+?)\s+\|\s+(?P<bias>.+?)\s*=>\s*(?P<effect>.+?)\s*$", re.DOTALL)


class CjtSyntaxNode(BaseModel):
    """Intermediate representation for one CJT expression."""

    name: Optional[str] = None
    cause: str
    bias: str
    effect: str
    beta: Optional[float] = Field(default=None, ge=0.0)
    saturation: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cutoff: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    region: CjtRegion = CjtRegion.UNKNOWN

    @model_validator(mode="after")
    def _validate_terminals(self):
        for attr in ("cause", "bias", "effect"):
            if not getattr(self, attr).strip():
                raise ValueError(f"CJT {attr} terminal is required")
        return self

    def to_expression(self) -> str:
        prefix = f"let {self.name} = " if self.name else ""
        params = []
        if self.beta is not None:
            params.append(f"beta={self.beta:g}")
        if self.saturation is not None:
            params.append(f"sat={self.saturation:g}")
        if self.cutoff is not None:
            params.append(f"cutoff={self.cutoff:g}")
        if self.region != CjtRegion.UNKNOWN:
            params.append(f"region={self.region.value}")
        suffix = f" [{', '.join(params)}]" if params else ""
        return f"{prefix}CJT< {self.cause} | {self.bias} => {self.effect} >{suffix};"


def parse_cjt_expression(expression: str) -> CjtSyntaxNode:
    """Parse one CJT<> expression into a safe IR node."""

    outer = _LET_RE.match(expression)
    if not outer:
        raise CjtSyntaxError("Invalid CJT expression wrapper")

    name = outer.group("name")
    body_expr = outer.group("body").strip()
    match = _CJT_RE.match(body_expr)
    if not match:
        raise CjtSyntaxError("Expected CJT< cause | bias => effect > syntax")

    body = match.group("body")
    body_match = _BODY_RE.match(body)
    if not body_match:
        raise CjtSyntaxError("Expected CJT body 'cause | bias => effect' with spaced bias separator")
    cause = body_match.group("cause")
    bias = body_match.group("bias")
    effect = body_match.group("effect")

    params = {}
    for block in (match.group("prefix_params"), match.group("bracket_params")):
        params.update(_parse_params(block or ""))

    try:
        return CjtSyntaxNode(
            name=name,
            cause=cause.strip(),
            bias=bias.strip(),
            effect=effect.strip(),
            beta=params.get("beta"),
            saturation=params.get("sat"),
            cutoff=params.get("cutoff"),
            region=params.get("region", CjtRegion.UNKNOWN),
        )
    except ValueError as exc:
        raise CjtSyntaxError(str(exc)) from exc


def roundtrip_cjt_expression(expression: str) -> CjtSyntaxNode:
    """Parse, serialize, and parse again to prove IR stability."""

    first = parse_cjt_expression(expression)
    second = parse_cjt_expression(first.to_expression())
    if second != first:
        raise CjtSyntaxError("CJT roundtrip changed the IR")
    return second


def _parse_params(raw: str) -> dict:
    params = {}
    if not raw.strip():
        return params
    for part in raw.split(","):
        if "=" not in part:
            raise CjtSyntaxError(f"Invalid CJT parameter '{part.strip()}'")
        key, value = [piece.strip() for piece in part.split("=", 1)]
        key = {"beta": "beta", "b": "beta", "sat": "sat", "saturation": "sat", "cutoff": "cutoff", "region": "region"}.get(key)
        if key is None:
            raise CjtSyntaxError(f"Unknown CJT parameter '{part.strip()}'")
        if key == "region":
            try:
                params[key] = CjtRegion(value)
            except ValueError as exc:
                raise CjtSyntaxError(f"Invalid CJT region '{value}'") from exc
        else:
            try:
                number = float(value)
            except ValueError as exc:
                raise CjtSyntaxError(f"Invalid numeric CJT parameter '{value}'") from exc
            if not math.isfinite(number):
                raise CjtSyntaxError(f"Invalid non-finite CJT parameter '{value}'")
            params[key] = number
    return params
