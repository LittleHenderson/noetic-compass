"""Explicitly unavailable quantum backend with unconditional submission refusal."""
from .base import Capabilities
from ..contracts import QuantumProblem
from ..wire import ContractError


class OfflineBackend:
    def capabilities(self) -> Capabilities:
        return Capabilities("offline-only", "NO_QUANTUM_EXECUTION", False, False, 0, 0)

    def compile(self, problem: QuantumProblem) -> object:
        problem.assert_current()
        raise ContractError("COMPILER_NOT_INTEGRATED: awaiting Q1-Claude's reviewed source")

    def estimate(self, problem: QuantumProblem) -> dict:
        problem.assert_current()
        return {"status": "UNAVAILABLE_COMPILER_RESOURCE_ESTIMATE", "quote": None,
                "qubits": None, "gates": None, "authorized_cloud_budget_usd": "0.00",
                "submission_allowed": False}

    def submit(self, problem: QuantumProblem, authorization: object = None) -> str:
        raise ContractError("SUBMISSION_REFUSED: no trusted execution grant; zero task budget")

    def poll(self, job_id: str) -> dict:
        raise ContractError("UNKNOWN_JOB: this backend cannot create a job")

    def cancel(self, job_id: str) -> dict:
        raise ContractError("UNKNOWN_JOB: no provider cancellation was performed")

    def decode(self, problem: QuantumProblem, result: object) -> tuple:
        problem.assert_current()
        raise ContractError("UNADMITTED_RESULT: no quantum result source exists")
