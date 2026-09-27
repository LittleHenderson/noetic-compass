"""Routing decisions only; never an authorization to dispatch or retain."""
from dataclasses import dataclass

from .contracts import QuantumProblem
from .wire import Record


@dataclass(frozen=True)
class Eligibility(Record):
    mode: str
    quantum_dispatch_allowed: bool
    authoritative_write_allowed: bool
    retention_allowed: bool
    disposition: str


def assess(problem: QuantumProblem) -> Eligibility:
    problem.assert_current()
    disposition = {"disabled": "BASELINE_ONLY", "shadow": "COMPARE_ONLY",
                   "research": "CANDIDATES_ONLY_NO_HOST_BRIDGE"}[problem.mode]
    return Eligibility(problem.mode, False, False, False, disposition)
