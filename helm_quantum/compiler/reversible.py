"""Reversible two-bit primitives ID, INC, DEC and NOT2 with explicit bit ordering.

Data register: two qubits, `lsb` (value 1) and `msb` (value 2); x = lsb + 2*msb.
Each primitive is a permutation of {0, 1, 2, 3} realised with X and controlled-X
only, so its inverse is the reversed gate list. Controls handed in are added to
every gate, which yields a controlled instruction: when the control pattern is
not met the data register is untouched.

Realisations (derived from the public arithmetic, not from any solution list):
  ID   : x            -> no gates
  INC  : (x + 1) % 4  -> msb ^= lsb ; lsb ^= 1          (carry first, then flip)
  DEC  : (x + 3) % 4  -> lsb ^= 1 ; msb ^= lsb          (exact inverse of INC)
  NOT2 : 3 - x        -> lsb ^= 1 ; msb ^= 1            (bitwise complement)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ..wire import require
from .ir import Gate


@dataclass(frozen=True)
class DataRegister:
    lsb: int
    msb: int

    def __post_init__(self):
        require(type(self.lsb) is int and type(self.msb) is int and self.lsb >= 0 and self.msb >= 0
                and self.lsb != self.msb, "data register needs two distinct qubits")

    def value_bits(self, x: int) -> tuple:
        require(type(x) is int and 0 <= x <= 3, "two-bit value required")
        return ((self.lsb, x & 1), (self.msb, (x >> 1) & 1))

    def positive_negated(self, x: int) -> tuple:
        bits = self.value_bits(x)
        return (tuple(q for q, b in bits if b), tuple(q for q, b in bits if not b))


@dataclass(frozen=True)
class Primitive:
    code: int
    name: str
    arithmetic: str
    inverse_name: str


PRIMITIVES = (
    Primitive(0, "ID", "x", "ID"),
    Primitive(1, "INC", "(x + 1) % 4", "DEC"),
    Primitive(2, "DEC", "(x + 3) % 4", "INC"),
    Primitive(3, "NOT2", "3 - x", "NOT2"),
)
BY_NAME = {p.name: p for p in PRIMITIVES}
BY_CODE = {p.code: p for p in PRIMITIVES}
LIBRARY = tuple(p.name for p in PRIMITIVES)


def instruction_gates(name: str, data: DataRegister, controls=(), negated=()) -> tuple:
    require(name in BY_NAME, f"UNSUPPORTED_INSTRUCTION: {name!r}")
    require(type(data) is DataRegister, "DataRegister required")
    c = tuple(controls)
    n = tuple(negated)
    if name == "ID":
        return ()
    if name == "INC":
        return (Gate("X", data.msb, c + (data.lsb,), n, "INC carry"),
                Gate("X", data.lsb, c, n, "INC flip"))
    if name == "DEC":
        return (Gate("X", data.lsb, c, n, "DEC flip"),
                Gate("X", data.msb, c + (data.lsb,), n, "DEC borrow"))
    return (Gate("X", data.lsb, c, n, "NOT2 lsb"),
            Gate("X", data.msb, c, n, "NOT2 msb"))


def inverse_instruction_gates(name: str, data: DataRegister, controls=(), negated=()) -> tuple:
    return tuple(gate.inverse() for gate in reversed(instruction_gates(name, data, controls, negated)))


def semantics_digest() -> str:
    """Digest of the instruction table and its gate realisation on a canonical register."""
    reg = DataRegister(0, 1)
    table = [{"code": p.code, "name": p.name, "arithmetic": p.arithmetic, "inverse": p.inverse_name,
              "gates": [g.to_dict() for g in instruction_gates(p.name, reg)]} for p in PRIMITIVES]
    text = json.dumps({"bit_order": "x = lsb + 2*msb", "table": table}, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()
