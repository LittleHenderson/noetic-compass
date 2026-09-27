"""Q1-Claude reversible compiler lease (helm_quantum/compiler/).

Imports are limited to helm_quantum.contracts, helm_quantum.admission,
helm_quantum.wire and fixtures/public. This package never imports
helm_quantum.classical, helm_quantum.verifier, helm_quantum.vendor or any
evaluator receipt, and nothing here reads a list of solved program IDs.

A compiled artifact is a description of a circuit. It is not a proposal, a
receipt, a verification, an execution grant or a HELM/CAS mapping.
"""
from .ir import Circuit, Gate
from .reversible import DataRegister, LIBRARY, PRIMITIVES, instruction_gates, inverse_instruction_gates
from .predicate import CompiledPredicate, PredicateSpec, RegisterLayout, compile_predicate
from .boundary import CompilerBinding, UnsupportedCapability, compile_problem, compiler_source_digest
from .resources import ResourceBoundExceeded, ResourceModel, SimulationBudget, admit_simulation, estimate_resources
from .search import SearchOutcome, bounded_search

__all__ = [
    "Circuit", "Gate", "DataRegister", "LIBRARY", "PRIMITIVES", "instruction_gates",
    "inverse_instruction_gates", "CompiledPredicate", "PredicateSpec", "RegisterLayout",
    "compile_predicate", "CompilerBinding", "UnsupportedCapability", "compile_problem",
    "compiler_source_digest", "ResourceBoundExceeded", "ResourceModel", "SimulationBudget",
    "admit_simulation", "estimate_resources", "SearchOutcome", "bounded_search",
]
