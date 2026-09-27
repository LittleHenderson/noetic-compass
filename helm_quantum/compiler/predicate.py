"""Length-L semantic predicate compiled from instruction semantics and the public target.

For every public input x the circuit prepares the data register in |x>, executes
the program selected by the selection register (each slot's instruction is
chosen by two-qubit controls on that slot's opcode), records whether the data
register equals the public target output in one flag qubit, then uncomputes the
program and the preparation. After all inputs a multi-controlled Z on the flags
phase-marks selection states whose program satisfies every input. The flag block
is then run in reverse so every data/flag qubit returns to |0>; the selection
register is preserved (only its phase changes).

Nothing here enumerates or stores which programs succeed.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..wire import ContractError, require
from .ir import Circuit, Gate
from .reversible import BY_CODE, LIBRARY, DataRegister, instruction_gates, semantics_digest
from .sim import execute_basis

DECODING_ORDER = "instruction-left-to-right;two-bit-op-msb-first"
DOMAIN = (0, 1, 2, 3)
MAX_PROGRAM_LENGTH = 4  # 2L + 6 qubits; L = 4 gives 14 qubits, still a small dense state


class UnsupportedCapability(ContractError):
    """A requested problem feature this compiler does not implement. Precise, not silent."""


@dataclass(frozen=True)
class PredicateSpec:
    instruction_library: tuple
    domain: tuple
    program_length: int
    target_outputs: tuple
    decoding_order: str

    def __post_init__(self):
        if type(self.instruction_library) is not tuple or self.instruction_library != LIBRARY:
            raise UnsupportedCapability(
                f"UNSUPPORTED_INSTRUCTION_LIBRARY: supported {LIBRARY}, got {self.instruction_library!r}")
        if type(self.domain) is not tuple or self.domain != DOMAIN:
            raise UnsupportedCapability(f"UNSUPPORTED_DOMAIN: supported {DOMAIN}, got {self.domain!r}")
        if type(self.program_length) is not int or not 1 <= self.program_length <= MAX_PROGRAM_LENGTH:
            raise UnsupportedCapability(
                f"UNSUPPORTED_PROGRAM_LENGTH: supported 1..{MAX_PROGRAM_LENGTH}, got {self.program_length!r}")
        if (type(self.target_outputs) is not tuple or len(self.target_outputs) != len(DOMAIN)
                or any(type(y) is not int or y not in DOMAIN for y in self.target_outputs)):
            raise UnsupportedCapability(
                f"UNSUPPORTED_TARGET: need one value in {DOMAIN} per input, got {self.target_outputs!r}")
        if self.decoding_order != DECODING_ORDER:
            raise UnsupportedCapability(
                f"UNSUPPORTED_DECODING_ORDER: supported {DECODING_ORDER!r}, got {self.decoding_order!r}")


@dataclass(frozen=True)
class RegisterLayout:
    """Pinned qubit allocation. Selection qubits 2k (opcode MSB) and 2k+1 (opcode LSB) hold slot k."""
    program_length: int
    selection: tuple
    data: DataRegister
    flags: tuple
    total: int

    @classmethod
    def for_length(cls, length: int) -> "RegisterLayout":
        require(type(length) is int and 1 <= length <= MAX_PROGRAM_LENGTH, "unsupported length")
        selection = tuple(range(2 * length))
        data = DataRegister(2 * length, 2 * length + 1)
        flags = tuple(range(2 * length + 2, 2 * length + 2 + len(DOMAIN)))
        return cls(length, selection, data, flags, 2 * length + 2 + len(DOMAIN))

    def slot(self, k: int) -> tuple:
        return (self.selection[2 * k], self.selection[2 * k + 1])

    def encode_program(self, program) -> int:
        require(type(program) is tuple and len(program) == self.program_length, "program length mismatch")
        index = 0
        for k, op in enumerate(program):
            require(type(op) is int and 0 <= op <= 3, "opcode outside 0..3")
            msb, lsb = self.slot(k)
            if op & 2:
                index |= 1 << msb
            if op & 1:
                index |= 1 << lsb
        return index

    def decode_bits(self, bits) -> tuple:
        """bits[i] is the measured value of selection qubit i (selection order)."""
        require(len(bits) == len(self.selection), "selection width mismatch")
        return tuple(2 * bits[2 * k] + bits[2 * k + 1] for k in range(self.program_length))

    def decode_index(self, index: int) -> tuple:
        return self.decode_bits(tuple((index >> q) & 1 for q in self.selection))

    def workspace(self) -> tuple:
        return (self.data.lsb, self.data.msb) + self.flags

    def allocation(self) -> dict:
        return {"selection_qubits": list(self.selection), "selection_count": len(self.selection),
                "slot_to_qubits": {str(k): {"opcode_msb": self.slot(k)[0], "opcode_lsb": self.slot(k)[1]}
                                   for k in range(self.program_length)},
                "data_lsb": self.data.lsb, "data_msb": self.data.msb, "data_count": 2,
                "check_flags": list(self.flags), "check_flag_count": len(self.flags),
                "decomposition_ancillas": 0,
                "decomposition_note": "multi-controlled gates are single abstract gates here; "
                                      "a device-level decomposition would add ancillas or depth",
                "total_qubits": self.total, "index_convention": "qubit i is bit i of the basis index"}


def controlled_program_gates(layout: RegisterLayout) -> list:
    """Execute the selected instruction of each slot, in order, controlled on that slot's opcode."""
    gates = []
    for k in range(layout.program_length):
        msb, lsb = layout.slot(k)
        for code in range(4):
            positive = tuple(q for q, bit in ((msb, code >> 1), (lsb, code & 1)) if bit)
            negated = tuple(q for q, bit in ((msb, code >> 1), (lsb, code & 1)) if not bit)
            gates.extend(instruction_gates(BY_CODE[code].name, layout.data, positive, negated))
    return gates


@dataclass(frozen=True)
class CompiledPredicate:
    spec: PredicateSpec
    layout: RegisterLayout
    circuit: Circuit
    semantics_digest: str

    @property
    def circuit_digest(self) -> str:
        return self.circuit.digest()

    def marks(self, program) -> bool:
        """Classical execution of the compiled circuit on one basis program (the compiler's own
        semantics, not an evaluator). Also asserts the workspace is restored."""
        index = self.layout.encode_program(program)
        final, sign = execute_basis(self.circuit, index)
        require(final == index, "compiled predicate did not restore its workspace")
        return sign == -1


def compile_predicate(spec: PredicateSpec) -> CompiledPredicate:
    require(type(spec) is PredicateSpec, "PredicateSpec required")
    layout = RegisterLayout.for_length(spec.program_length)
    flag_block = Circuit(layout.total)
    execution = controlled_program_gates(layout)
    for xi, x in enumerate(spec.domain):
        prepare = [Gate("X", q, label=f"prepare x={x}") for q, bit in layout.data.value_bits(x) if bit]
        flag_block.extend(prepare)
        flag_block.extend(execution)
        positive, negated = layout.data.positive_negated(spec.target_outputs[xi])
        flag_block.append(Gate("X", layout.flags[xi], positive, negated,
                               f"check f({x}) == {spec.target_outputs[xi]}"))
        flag_block.extend(g.inverse() for g in reversed(execution))
        flag_block.extend(g.inverse() for g in reversed(prepare))
    circuit = Circuit(layout.total)
    circuit.extend(flag_block.gates)
    circuit.append(Gate("Z", layout.flags[-1], tuple(layout.flags[:-1]), (), "phase-mark all inputs"))
    circuit.extend(flag_block.inverse().gates)
    return CompiledPredicate(spec, layout, circuit, semantics_digest())
