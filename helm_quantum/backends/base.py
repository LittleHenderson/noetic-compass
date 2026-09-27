from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..contracts import QuantumProblem, QuantumProposal
from ..wire import Record


@dataclass(frozen=True)
class Capabilities(Record):
    backend: str
    execution_kind: str
    compile_available: bool
    submit_available: bool
    max_tasks: int
    max_shots: int


class Backend(Protocol):
    def capabilities(self) -> Capabilities: ...
    def compile(self, problem: QuantumProblem) -> object: ...
    def estimate(self, problem: QuantumProblem) -> dict: ...
    def submit(self, problem: QuantumProblem, authorization: object = None) -> str: ...
    def poll(self, job_id: str) -> dict: ...
    def cancel(self, job_id: str) -> dict: ...
    def decode(self, problem: QuantumProblem, result: object) -> tuple[QuantumProposal, ...]: ...
