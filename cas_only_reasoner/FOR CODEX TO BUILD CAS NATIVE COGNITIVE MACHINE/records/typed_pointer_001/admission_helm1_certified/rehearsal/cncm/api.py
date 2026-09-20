"""Stable host-facing API for the v0.1 reference implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .canonical import digest
from .engine import CognitiveMachine, RunResult
from .kernel import StateStore, StepResult, TraceFabric, TransactionCoordinator, boot_state
from .model import EpisodicRecord, Intent, MachineState, ProblemPacket
from .verification import VerificationReport, validate_problem, verify_bundle


@dataclass(frozen=True, slots=True)
class ReplayReport:
    matches: bool
    expected_trace_digest: str
    actual_trace_digest: str
    result: RunResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "cncm.replay/0.1",
            "matches": self.matches,
            "expected_trace_digest": self.expected_trace_digest,
            "actual_trace_digest": self.actual_trace_digest,
            "run_id": self.result.final_state.run_id,
        }


class KernelSession:
    """A step-capable session that keeps state ownership inside the kernel."""

    def __init__(
        self,
        problem: ProblemPacket | Mapping[str, Any],
        episodic_memory: Iterable[EpisodicRecord] = (),
    ) -> None:
        self.problem = problem if isinstance(problem, ProblemPacket) else ProblemPacket.from_dict(problem)
        initial = boot_state(self.problem, episodic_memory)
        self._store = StateStore(initial)
        self._trace = TraceFabric()
        self._coordinator = TransactionCoordinator(
            store=self._store,
            trace=self._trace,
            problem=self.problem,
        )

    @property
    def state(self) -> MachineState:
        return self._store.snapshot()

    @property
    def trace(self):
        return self._trace.events

    def step(
        self,
        intents: Iterable[Intent],
        *,
        enabled_components: Iterable[str],
        scheduled_components: Iterable[str],
    ) -> StepResult:
        return self._coordinator.execute(
            enabled_components=enabled_components,
            scheduled_components=scheduled_components,
            intents=intents,
        )


def boot(
    problem: ProblemPacket | Mapping[str, Any],
    episodic_memory: Iterable[EpisodicRecord] = (),
) -> MachineState:
    packet = problem if isinstance(problem, ProblemPacket) else ProblemPacket.from_dict(problem)
    return boot_state(packet, episodic_memory)


def run(
    problem: ProblemPacket | Mapping[str, Any],
    episodic_memory: Iterable[EpisodicRecord] = (),
) -> RunResult:
    return CognitiveMachine(episodic_memory).run(problem)


def replay(
    problem: ProblemPacket | Mapping[str, Any],
    expected_trace: Sequence[Mapping[str, Any]],
    episodic_memory: Iterable[EpisodicRecord] = (),
) -> ReplayReport:
    result = run(problem, episodic_memory)
    actual = [event.to_dict() for event in result.trace]
    expected = list(expected_trace)
    return ReplayReport(
        matches=actual == expected,
        expected_trace_digest=digest(expected),
        actual_trace_digest=digest(actual),
        result=result,
    )


def verify_evidence(bundle: Mapping[str, Any]) -> VerificationReport:
    return verify_bundle(bundle)

