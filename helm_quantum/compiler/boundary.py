"""Narrow boundary from Codex's admitted QuantumProblem to a compiled predicate.

Reads only public problem fields (instruction library, domain, program length,
public target outputs, decoding order, family, prerequisites). Never reads a
goal name to special-case a target, never mutates the problem or its admission,
and returns bindings (source / problem / circuit digests) that carry no
execution authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ..contracts import QuantumProblem
from ..wire import Record, require
from .predicate import CompiledPredicate, PredicateSpec, UnsupportedCapability, compile_predicate
from .resources import SimulationBudget, estimate_resources
from .search import SCHEDULE, diffusion

SUPPORTED_FAMILY = "synthetic-mod4-instruction-synthesis"
ARTIFACT_FORMAT = "helm-q1-compiler-artifact/1"
COMPILER_DIR = Path(__file__).resolve().parent


def compiler_source_digest() -> str:
    """SHA256 over {relative path: sha256} of every .py file in helm_quantum/compiler/."""
    files = sorted(p for p in COMPILER_DIR.glob("*.py"))
    table = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    return hashlib.sha256(json.dumps(table, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class CompilerBinding(Record):
    schema: str
    problem_digest: str
    source_digest: str
    compiler_source_digest: str
    semantics_digest: str
    circuit_digest: str
    family: str
    program_length: int
    total_qubits: int
    gate_count: int
    execution_authority: str
    origin: str


def compile_problem(problem: QuantumProblem) -> tuple:
    require(type(problem) is QuantumProblem, "typed QuantumProblem required")
    problem.assert_current()
    if problem.family != SUPPORTED_FAMILY:
        raise UnsupportedCapability(f"UNSUPPORTED_FAMILY: supported {SUPPORTED_FAMILY!r}, got {problem.family!r}")
    if problem.prerequisites:
        raise UnsupportedCapability("UNSUPPORTED_PREREQUISITES: no RPM prerequisite export is admitted")
    if problem.max_program_length != problem.program_length:
        raise UnsupportedCapability("UNSUPPORTED_VARIABLE_LENGTH: only fixed-length programs compile")
    spec = PredicateSpec(instruction_library=problem.instruction_library, domain=problem.domain,
                         program_length=problem.program_length, target_outputs=problem.target_outputs,
                         decoding_order=problem.decoding_order)
    pred = compile_predicate(spec)
    problem.assert_current()
    binding = CompilerBinding(
        schema="helm-q1-compiler-binding/1", problem_digest=problem.problem_digest,
        source_digest=problem.source_digest, compiler_source_digest=compiler_source_digest(),
        semantics_digest=pred.semantics_digest, circuit_digest=pred.circuit_digest,
        family=problem.family, program_length=problem.program_length,
        total_qubits=pred.layout.total, gate_count=len(pred.circuit),
        execution_authority="NONE", origin="compiler-artifact-not-a-proposal")
    return pred, binding


def compile(problem: QuantumProblem) -> tuple:  # noqa: A001 - name fixed by P2_COMPILER_BOUNDARY.md
    """Entry point named in coordination/codex/P2_COMPILER_BOUNDARY.md.

    Same behaviour as compile_problem: returns (CompiledPredicate, CompilerBinding).
    """
    return compile_problem(problem)


def artifact(pred: CompiledPredicate, binding: CompilerBinding,
             budget: SimulationBudget | None = None) -> dict:
    """Serialized compiler artifact: a plain JSON-able description of the circuit.

    Format ARTIFACT_FORMAT. It describes a circuit and its finite resource model;
    it is not a proposal, a receipt, a verification or an execution grant.
    """
    require(type(pred) is CompiledPredicate and type(binding) is CompilerBinding, "typed inputs required")
    require(binding.circuit_digest == pred.circuit_digest, "binding does not describe this circuit")
    budget = SimulationBudget() if budget is None else budget
    model = estimate_resources(pred, budget)
    layout = pred.layout
    return {
        "format": ARTIFACT_FORMAT,
        "binding": binding.to_dict(),
        "register_layout": layout.allocation(),
        "instruction_order": "slot 0 executes first; slot k is selected by qubits 2k (opcode MSB) and 2k+1 (opcode LSB)",
        "decoding_order": pred.spec.decoding_order,
        "measurement": "measure selection qubits 0..2L-1 only; workspace qubits are restored to |0> by the circuit",
        "gate_model": "abstract gates X, Z, H with positive and negated controls; qubit i is bit i of the basis index",
        "circuit": pred.circuit.to_dict(),
        "circuit_digest": pred.circuit_digest,
        "structure": {
            "per_input_block": ["prepare data = x", "execute selected program under opcode controls",
                                "flip flag_i iff data equals target_i", "inverse of execute",
                                "inverse of prepare"],
            "mark": "multi-controlled Z over all flags (phase -1 iff every input matches)",
            "cleanup": "exact inverse of the whole flag block; data and flags return to |0>; "
                       "selection preserved up to the marking phase",
        },
        "schedule": dict(SCHEDULE),
        "diffusion_gates": len(diffusion(pred)),
        "resource_model": model.to_dict(),
        "execution_authority": "NONE",
    }
