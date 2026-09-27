"""Finite resource model for simulating a compiled predicate. Estimates are labelled.

Nothing is simulated here. `admit_simulation` is the gate that every simulator
path must pass before allocating a state; it fails closed and never raises a
limit to fit an oversized circuit.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..wire import ContractError, Record, integer, require
from .predicate import CompiledPredicate
from .sim import BYTES_PER_AMPLITUDE, MAX_SIM_QUBITS

INTERPRETER_BASELINE_BYTES = 32 * 1024 * 1024   # assumed CPython + modules RSS, not measured here
ASSUMED_MS_PER_GATE_12_QUBITS = 2.0             # planning assumption; measured value goes in the return


class ResourceBoundExceeded(ContractError):
    pass


@dataclass(frozen=True)
class SimulationBudget(Record):
    max_oracle_calls: int = 64
    max_wall_ms: int = 120_000
    max_qubits: int = 16
    max_state_bytes: int = 16 * 1024 * 1024
    seed: int = 0

    def __post_init__(self):
        integer(self.max_oracle_calls, 1, 4096, "max_oracle_calls")
        integer(self.max_wall_ms, 1, 3_600_000, "max_wall_ms")
        integer(self.max_qubits, 1, MAX_SIM_QUBITS, "max_qubits")
        integer(self.max_state_bytes, 1, 2**31, "max_state_bytes")
        integer(self.seed, 0, 2**32 - 1, "seed")


@dataclass(frozen=True)
class ResourceModel(Record):
    schema: str
    representation: str
    register_allocation: dict
    total_qubits: int
    amplitudes: int
    state_bytes_estimate: int
    peak_memory_bytes_estimate: int
    oracle_gate_counts: dict
    oracle_gates: int
    oracle_max_controls: int
    diffusion_gates: int
    gates_per_iteration: int
    oracle_depth_serial_bound: int
    oracle_depth_layered_bound: int
    toffoli_estimate_per_oracle: int
    sdk_native_depth: str
    max_oracle_calls: int
    max_wall_ms: int
    runtime_ceiling_ms_estimate: int
    assumed_ms_per_gate: float
    measured_ms_per_gate: float | None
    stop_behavior: str
    within_budget: bool
    limiting_bounds: tuple


def _toffoli_estimate(counts: dict) -> int:
    """Barenco-style abstract count: a gate with k>=2 controls costs about 2k-3 Toffolis
    (dirty ancillas); k<=1 costs 0 Toffolis. Estimate only."""
    total = 0
    for key, n in counts.items():
        if key.startswith("C"):
            k = int(key[1:-1])
            if k >= 2:
                total += (2 * k - 3) * n
    return total


def estimate_resources(pred: CompiledPredicate, budget: SimulationBudget,
                       diffusion_gates: int | None = None) -> ResourceModel:
    require(type(pred) is CompiledPredicate and type(budget) is SimulationBudget, "typed inputs required")
    layout = pred.layout
    n = layout.total
    amplitudes = 1 << n
    state_bytes = amplitudes * BYTES_PER_AMPLITUDE
    peak = INTERPRETER_BASELINE_BYTES + 2 * state_bytes  # one live state plus one transient copy
    counts = pred.circuit.gate_counts()
    oracle_gates = len(pred.circuit)
    if diffusion_gates is None:
        diffusion_gates = 4 * len(layout.selection) + 1
    per_iteration = oracle_gates + diffusion_gates
    limiting = []
    if n > budget.max_qubits:
        limiting.append(f"total_qubits {n} > max_qubits {budget.max_qubits}")
    if n > MAX_SIM_QUBITS:
        limiting.append(f"total_qubits {n} > simulator ceiling {MAX_SIM_QUBITS}")
    if state_bytes > budget.max_state_bytes:
        limiting.append(f"state_bytes {state_bytes} > max_state_bytes {budget.max_state_bytes}")
    scale = amplitudes / 4096.0
    ms_per_gate = ASSUMED_MS_PER_GATE_12_QUBITS * scale
    runtime_ceiling = int(per_iteration * budget.max_oracle_calls * ms_per_gate) + 1
    return ResourceModel(
        schema="helm-q1-compiler-resource-model/1",
        representation="dense statevector; Python complex amplitudes in one list; "
                       "qubit i is bit i of the basis index (little-endian index bits)",
        register_allocation=layout.allocation(), total_qubits=n, amplitudes=amplitudes,
        state_bytes_estimate=state_bytes, peak_memory_bytes_estimate=peak,
        oracle_gate_counts=counts, oracle_gates=oracle_gates,
        oracle_max_controls=pred.circuit.max_controls(), diffusion_gates=diffusion_gates,
        gates_per_iteration=per_iteration, oracle_depth_serial_bound=oracle_gates,
        oracle_depth_layered_bound=pred.circuit.layered_depth(),
        toffoli_estimate_per_oracle=_toffoli_estimate(counts),
        sdk_native_depth="NOT_MEASURED: no SDK is installed or authorised; abstract gates only",
        max_oracle_calls=budget.max_oracle_calls, max_wall_ms=budget.max_wall_ms,
        runtime_ceiling_ms_estimate=runtime_ceiling, assumed_ms_per_gate=ms_per_gate,
        measured_ms_per_gate=None,
        stop_behavior="stop before the first oracle application that would exceed max_oracle_calls; "
                      "stop at the next round boundary once max_wall_ms has elapsed; no retry; "
                      "no limit is raised to fit the circuit",
        within_budget=not limiting, limiting_bounds=tuple(limiting))


def admit_simulation(pred: CompiledPredicate, budget: SimulationBudget) -> ResourceModel:
    model = estimate_resources(pred, budget)
    if not model.within_budget:
        raise ResourceBoundExceeded("SIMULATION_REFUSED: " + "; ".join(model.limiting_bounds))
    return model
