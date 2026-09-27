"""Dense statevector simulator, standard library only.

Convention (pinned, tested): qubit i is bit i of the basis-state index, so the
index of a basis state is sum(bit_i << i). Amplitudes are Python complex
numbers in one list and gates act in place. Nothing here talks to a provider,
an SDK, an account or the network. A run here establishes simulator behavior
only.
"""
from __future__ import annotations

import math
import random

from ..wire import require
from .ir import Circuit, Gate

MAX_SIM_QUBITS = 20  # hard ceiling of this implementation: 2**20 amplitudes
BYTES_PER_AMPLITUDE = 40  # CPython complex object (32 B) plus one list slot (8 B)


def control_pattern(gate: Gate) -> tuple[int, int]:
    mask = 0
    value = 0
    for q in gate.controls:
        mask |= 1 << q
        value |= 1 << q
    for q in gate.negated:
        mask |= 1 << q
    return mask, value


class StateVector:
    __slots__ = ("n_qubits", "amps", "gates_applied")

    def __init__(self, n_qubits: int, index: int = 0):
        require(type(n_qubits) is int and 1 <= n_qubits <= MAX_SIM_QUBITS,
                "simulator qubit ceiling exceeded")
        size = 1 << n_qubits
        require(type(index) is int and 0 <= index < size, "invalid basis index")
        self.n_qubits = n_qubits
        self.amps = [0j] * size
        self.amps[index] = 1 + 0j
        self.gates_applied = 0

    @classmethod
    def from_amplitudes(cls, n_qubits: int, amps) -> "StateVector":
        state = cls(n_qubits)
        require(len(amps) == len(state.amps), "amplitude count mismatch")
        state.amps = [complex(a) for a in amps]
        require(abs(state.norm() - 1.0) < 1e-9, "state must be normalised")
        return state

    def copy(self) -> "StateVector":
        other = StateVector(self.n_qubits)
        other.amps = list(self.amps)
        other.gates_applied = self.gates_applied
        return other

    def apply(self, gate: Gate) -> None:
        require(max(gate.wires) < self.n_qubits, "gate wire outside state")
        t = 1 << gate.target
        mask, value = control_pattern(gate)
        amps = self.amps
        size = len(amps)
        if gate.kind == "X":
            for base in range(0, size, t << 1):
                for i in range(base, base + t):
                    if (i & mask) == value:
                        j = i | t
                        amps[i], amps[j] = amps[j], amps[i]
        elif gate.kind == "Z":
            for base in range(t, size, t << 1):
                for i in range(base, base + t):
                    if (i & mask) == value:
                        amps[i] = -amps[i]
        else:
            r = math.sqrt(0.5)
            for base in range(0, size, t << 1):
                for i in range(base, base + t):
                    j = i | t
                    a, b = amps[i], amps[j]
                    amps[i] = (a + b) * r
                    amps[j] = (a - b) * r
        self.gates_applied += 1

    def run(self, circuit: Circuit) -> "StateVector":
        require(circuit.n_qubits == self.n_qubits, "circuit/state width mismatch")
        for gate in circuit.gates:
            self.apply(gate)
        return self

    def norm(self) -> float:
        return math.sqrt(sum(abs(a) ** 2 for a in self.amps))

    def probabilities(self) -> list:
        return [abs(a) ** 2 for a in self.amps]

    def bits(self, index: int, qubits) -> tuple:
        return tuple((index >> q) & 1 for q in qubits)

    def marginal(self, qubits) -> dict:
        result: dict = {}
        for index, a in enumerate(self.amps):
            p = abs(a) ** 2
            if p:
                key = self.bits(index, qubits)
                result[key] = result.get(key, 0.0) + p
        return result

    def sample(self, rng: random.Random) -> int:
        """One measurement of every qubit; returns the basis index (no collapse kept)."""
        r = rng.random()
        acc = 0.0
        last = 0
        for index, a in enumerate(self.amps):
            p = abs(a) ** 2
            if p:
                last = index
                acc += p
                if r < acc:
                    return index
        return last

    def allclose(self, other: "StateVector", tol: float = 1e-9) -> bool:
        return (self.n_qubits == other.n_qubits and
                all(abs(a - b) <= tol for a, b in zip(self.amps, other.amps)))


def execute_basis(circuit: Circuit, index: int) -> tuple[int, int]:
    """Exact classical execution of a permutation-plus-phase circuit on one basis state.

    Returns (final index, sign) where sign is +1 or -1. Refuses H gates, which
    would leave the computational basis.
    """
    require(type(index) is int and 0 <= index < (1 << circuit.n_qubits), "invalid basis index")
    sign = 1
    for gate in circuit.gates:
        require(gate.kind != "H", "basis execution requires a permutation/phase circuit")
        mask, value = control_pattern(gate)
        if (index & mask) != value:
            continue
        t = 1 << gate.target
        if gate.kind == "X":
            index ^= t
        elif index & t:
            sign = -sign
    return index, sign
