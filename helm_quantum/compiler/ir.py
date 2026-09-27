"""Abstract reversible-circuit IR for the Q1 compiler lease.

Gate kinds: X (bit flip), Z (phase flip), H (Hadamard). X and Z may carry
positive controls (wire must read 1) and negated controls (wire must read 0).
This is an abstract gate model: a multi-controlled gate counts as ONE gate
here. Counts and depths from this module are abstract-gate figures, not
SDK-native or device-native measurements.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from ..wire import require

KINDS = ("X", "Z", "H")
MAX_IR_QUBITS = 24


@dataclass(frozen=True)
class Gate:
    kind: str
    target: int
    controls: tuple[int, ...] = ()
    negated: tuple[int, ...] = ()
    label: str = ""

    def __post_init__(self):
        require(self.kind in KINDS, f"unknown gate kind {self.kind!r}")
        require(type(self.target) is int and self.target >= 0, "invalid gate target")
        for name in ("controls", "negated"):
            value = getattr(self, name)
            require(type(value) is tuple and all(type(q) is int and q >= 0 for q in value),
                    f"invalid gate {name}")
        require(len(set(self.wires)) == len(self.wires), "gate wires must be distinct")
        require(self.kind != "H" or self.control_count == 0,
                "controlled H is not part of this gate model")
        require(type(self.label) is str, "gate label must be text")

    @property
    def wires(self) -> tuple[int, ...]:
        return (self.target,) + self.controls + self.negated

    @property
    def control_count(self) -> int:
        return len(self.controls) + len(self.negated)

    def inverse(self) -> "Gate":
        # X, Z and H are their own inverses; controls do not change that.
        return self

    def to_dict(self) -> dict:
        return {"kind": self.kind, "target": self.target, "controls": list(self.controls),
                "negated": list(self.negated), "label": self.label}


@dataclass
class Circuit:
    n_qubits: int
    gates: list = field(default_factory=list)

    def __post_init__(self):
        require(type(self.n_qubits) is int and 1 <= self.n_qubits <= MAX_IR_QUBITS,
                "unsupported qubit count for this IR")
        for gate in self.gates:
            self._check(gate)

    def _check(self, gate: Gate) -> None:
        require(type(gate) is Gate, "Gate required")
        require(max(gate.wires) < self.n_qubits, "gate wire outside circuit")

    def append(self, gate: Gate) -> "Circuit":
        self._check(gate)
        self.gates.append(gate)
        return self

    def extend(self, gates) -> "Circuit":
        for gate in gates:
            self.append(gate)
        return self

    def inverse(self) -> "Circuit":
        return Circuit(self.n_qubits, [gate.inverse() for gate in reversed(self.gates)])

    def __len__(self) -> int:
        return len(self.gates)

    def gate_counts(self) -> dict:
        counts: dict = {}
        for gate in self.gates:
            key = gate.kind if gate.control_count == 0 else f"C{gate.control_count}{gate.kind}"
            counts[key] = counts.get(key, 0) + 1
        return dict(sorted(counts.items()))

    def max_controls(self) -> int:
        return max((gate.control_count for gate in self.gates), default=0)

    def layered_depth(self) -> int:
        """ASAP layering of abstract gates on disjoint wires; an abstract bound only."""
        last = [0] * self.n_qubits
        depth = 0
        for gate in self.gates:
            layer = max(last[w] for w in gate.wires) + 1
            for w in gate.wires:
                last[w] = layer
            depth = max(depth, layer)
        return depth

    def to_dict(self) -> dict:
        return {"n_qubits": self.n_qubits, "gates": [gate.to_dict() for gate in self.gates]}

    def digest(self) -> str:
        text = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode()).hexdigest()
