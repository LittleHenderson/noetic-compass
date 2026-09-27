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

SUPPORTED_FAMILY = "synthetic-mod4-instruction-synthesis"
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
