"""Fixture-bound immutable contracts, validated on every supported constructor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar
from uuid import UUID

from .wire import ContractError, Record, canonical, digest, integer, require


@dataclass(frozen=True)
class ReturnAddress(Record):
    parent_ref: str
    snapshot_ref: str
    snapshot_digest: str
    branch_id: str
    caller_id: str
    caller_frame: str
    continuation: str
    checkpoint_digest: str | None

    def __post_init__(self):
        for name, value in self.to_dict().items():
            if name.endswith("digest"):
                if name == "checkpoint_digest" and value is None:
                    continue
                require(type(value) is str and len(value) == 64 and
                        all(c in "0123456789abcdef" for c in value), f"invalid {name}")
            else:
                require(type(value) is str and 0 < len(value) <= 256, f"invalid {name}")


@dataclass(frozen=True)
class ExecutionLimits(Record):
    max_programs: int
    max_transitions: int
    max_wall_ms: int
    max_memory_mib: int
    max_shots: int
    max_tasks: int
    max_cost_usd: str

    def __post_init__(self):
        for name, maximum in (("max_programs", 64), ("max_transitions", 1024),
                              ("max_wall_ms", 1000), ("max_memory_mib", 64)):
            integer(getattr(self, name), 1, maximum, name)
        integer(self.max_shots, 0, 0, "max_shots")
        integer(self.max_tasks, 0, 0, "max_tasks")
        require(self.max_cost_usd == "0.00", "zero spending only")


@dataclass(frozen=True, kw_only=True)
class QuantumProblem(Record):
    schema: str
    request_id: str
    source_digest: str
    compiler_digest: str | None
    operations_digest: str
    binding: ReturnAddress
    family: str
    domain: tuple[int, ...]
    instruction_library: tuple[str, ...]
    program_length: int
    max_program_length: int
    prerequisites: tuple[str, ...]
    goal: str
    target_outputs: tuple[int, ...]
    decoding_order: str
    limits: ExecutionLimits
    deadline_unix_ms: int
    mode: str
    verifier_digest: str
    _admission: object = field(repr=False, compare=False)

    _nested: ClassVar[dict] = {"binding": ReturnAddress, "limits": ExecutionLimits}
    _tuples: ClassVar[tuple] = ("domain", "instruction_library", "prerequisites", "target_outputs")

    def __post_init__(self):
        self.assert_current()

    def assert_current(self):
        from .admission import require_admission
        context = require_admission(self._admission)
        require(type(self.binding) is ReturnAddress and type(self.limits) is ExecutionLimits,
                "typed binding and limits required")
        for key in self._tuples:
            require(type(getattr(self, key)) is tuple, f"immutable {key} required")
        require(canonical(self) == canonical(context.problem_fields()),
                "problem differs from independently admitted offline fixture")

    @property
    def problem_digest(self) -> str:
        self.assert_current()
        return digest(self)


def _bound(record, schema: str):
    from .admission import require_admission
    context = require_admission(record._admission)
    require(type(record._problem) is QuantumProblem, "admitted problem required")
    record._problem.assert_current()
    require(record._problem._admission is context, "foreign admission")
    require(record.schema == schema, "unsupported schema")
    require(record.problem_digest == record._problem.problem_digest, "wrong problem digest")
    require(type(record.binding) is ReturnAddress and record.binding == record._problem.binding,
            "wrong return address")
    require(record.mode == record._problem.mode, "mode cannot change")


def validate_program(program: tuple[int, ...]) -> None:
    require(type(program) is tuple and len(program) == 3, "exactly three instructions required")
    for op in program:
        integer(op, 0, 3, "instruction")


@dataclass(frozen=True, kw_only=True)
class QuantumProposal(Record):
    schema: str
    problem_digest: str
    binding: ReturnAddress
    mode: str
    program: tuple[int, ...]
    origin: str
    _admission: object = field(repr=False, compare=False)
    _problem: QuantumProblem = field(repr=False, compare=False)
    _nested: ClassVar[dict] = {"binding": ReturnAddress}
    _tuples: ClassVar[tuple] = ("program",)

    def __post_init__(self):
        _bound(self, "helm-q1-proposal/1")
        validate_program(self.program)
        require(self.origin == "offline-classical", "unadmitted candidate origin")


@dataclass(frozen=True, kw_only=True)
class QuantumRunReceipt(Record):
    schema: str
    run_id: str
    problem_digest: str
    proposal_digest: str | None
    binding: ReturnAddress
    mode: str
    requested_backend: str
    actual_backend: str
    execution_kind: str
    device_properties_digest: str | None
    native_circuit_digest: str | None
    compilation_settings: tuple[str, ...]
    measurement_order: str
    shots: int
    observed_counts: tuple[str, ...]
    job_ids: tuple[str, ...]
    elapsed_ns: int
    candidates_checked: int
    quote_id: str | None
    estimated_charges_usd: str
    reconciled_charges_usd: str | None
    status: str
    _admission: object = field(repr=False, compare=False)
    _problem: QuantumProblem = field(repr=False, compare=False)
    _proposal: QuantumProposal | None = field(default=None, repr=False, compare=False)
    _nested: ClassVar[dict] = {"binding": ReturnAddress}
    _tuples: ClassVar[tuple] = ("compilation_settings", "observed_counts", "job_ids")

    def __post_init__(self):
        _bound(self, "helm-q1-receipt/1")
        require(type(self.run_id) is str, "run identity required")
        try:
            parsed_id = UUID(self.run_id)
        except ValueError as exc:
            raise ContractError("invalid run identity") from exc
        require(str(parsed_id) == self.run_id and parsed_id.version == 4, "invalid run identity")
        if self._proposal is None:
            require(self.proposal_digest is None, "candidate receipt requires a validated proposal")
        else:
            require(type(self._proposal) is QuantumProposal, "typed proposal required")
            self._proposal.__post_init__()
            require(self._proposal._problem is self._problem, "foreign receipt proposal")
            require(self.proposal_digest == digest(self._proposal), "receipt/proposal mismatch")
            integer(self.candidates_checked, 1, 64, "candidate-producing evaluation count")
        require(self.requested_backend == self.actual_backend == "offline-classical",
                "backend not admitted")
        require(self.execution_kind == "CLASSICAL_OFFLINE", "hardware/simulation not admitted")
        for name in ("device_properties_digest", "native_circuit_digest", "quote_id",
                     "reconciled_charges_usd"):
            require(getattr(self, name) is None, f"{name} must be unknown/not applicable")
        for name in self._tuples:
            require(type(getattr(self, name)) is tuple and not getattr(self, name),
                    f"no {name} in an offline classical receipt")
        require(self.measurement_order == "NOT_APPLICABLE", "no quantum measurement")
        integer(self.shots, 0, 0, "shots")
        integer(self.elapsed_ns, 0, 2**63 - 1, "elapsed_ns")
        integer(self.candidates_checked, 0, 64, "candidates_checked")
        require(self.estimated_charges_usd == "0.00", "zero provider cost only")
        require(self.status in ("COMPLETED", "BUDGET_EXHAUSTED"), "invalid receipt status")


@dataclass(frozen=True, kw_only=True)
class QuantumVerification(Record):
    schema: str
    problem_digest: str
    binding: ReturnAddress
    mode: str
    program: tuple[int, ...]
    verifier_digest: str
    outputs: tuple[int, ...]
    inputs_checked: int
    accepted: bool
    disposition: str
    retained: bool
    _admission: object = field(repr=False, compare=False)
    _problem: QuantumProblem = field(repr=False, compare=False)
    _nested: ClassVar[dict] = {"binding": ReturnAddress}
    _tuples: ClassVar[tuple] = ("program", "outputs")

    def __post_init__(self):
        from .verifier import direct_outputs
        _bound(self, "helm-q1-verification/1")
        validate_program(self.program)
        actual = direct_outputs(self.program)
        require(type(self.outputs) is tuple and canonical(self.outputs) == canonical(actual),
                "verifier outputs must be recomputed")
        require(self.verifier_digest == self._problem.verifier_digest, "foreign verifier")
        integer(self.inputs_checked, 4, 4, "inputs_checked")
        accepted = actual == self._problem.target_outputs
        require(type(self.accepted) is bool and self.accepted == accepted, "forged verdict")
        expected = ("REJECTED" if not accepted else {
            "disabled": "VERIFIED_OFFLINE_ONLY", "shadow": "VERIFIED_SHADOW_ONLY",
            "research": "VERIFIED_RESEARCH_CANDIDATE"}[self.mode])
        require(self.disposition == expected, "forged disposition")
        require(self.retained is False, "no host retention bridge admitted")
