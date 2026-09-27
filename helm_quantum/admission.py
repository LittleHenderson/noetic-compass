"""Trusted synthetic fixture admission. This is deliberately not a HELM adapter.

Only the local factory can admit an offline context. Payloads cannot mint one.
Python code with arbitrary access to this process is outside this boundary.
"""
from __future__ import annotations

import hashlib
import time
import weakref
from dataclasses import InitVar, dataclass
from pathlib import Path

from .contracts import ExecutionLimits, QuantumProblem, ReturnAddress
from .wire import digest, read_json, require

ROOT = Path(__file__).resolve().parents[1]
_TOKEN = object()
_LIVE = weakref.WeakSet()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, eq=False)
class OfflineAdmission:
    goal: str
    mode: str
    deadline_unix_ms: int
    source_digest: str
    operations_digest: str
    verifier_digest: str
    _token: InitVar[object]

    def __post_init__(self, _token):
        require(_token is _TOKEN, "caller cannot mint trusted admission")

    def problem_fields(self) -> dict:
        binding = ReturnAddress(
            parent_ref="offline-fixture:root", snapshot_ref="offline-fixture:mod4-v1",
            snapshot_digest=self.operations_digest, branch_id="offline-fixture:branch-0",
            caller_id="offline-fixture:caller-0", caller_frame="offline-fixture:frame-0",
            continuation="offline-fixture:return-0", checkpoint_digest=None)
        return dict(
            schema="helm-q1-problem/1", request_id=f"offline-fixture:{self.goal}:{self.mode}",
            source_digest=self.source_digest, compiler_digest=None,
            operations_digest=self.operations_digest, binding=binding,
            family="synthetic-mod4-instruction-synthesis", domain=(0, 1, 2, 3),
            instruction_library=("ID", "INC", "DEC", "NOT2"), program_length=3,
            max_program_length=3, prerequisites=(), goal=self.goal,
            target_outputs={"add2": (2, 3, 0, 1), "parity": (0, 1, 0, 1)}[self.goal],
            decoding_order="instruction-left-to-right;two-bit-op-msb-first",
            limits=ExecutionLimits(64, 1024, 1000, 64, 0, 0, "0.00"),
            deadline_unix_ms=self.deadline_unix_ms, mode=self.mode,
            verifier_digest=self.verifier_digest)

    def problem(self) -> QuantumProblem:
        return QuantumProblem(**self.problem_fields(), _admission=self)


def require_admission(context: object) -> OfflineAdmission:
    require(type(context) is OfflineAdmission and context in _LIVE,
            "independently admitted in-process offline state required")
    require(time.time_ns() // 1_000_000 < context.deadline_unix_ms, "admission expired")
    return context


def admit_offline_fixture(goal: str = "add2", mode: str = "disabled") -> OfflineAdmission:
    require(type(goal) is str and goal in ("add2", "parity"), "unknown fixture target")
    require(type(mode) is str and mode in ("disabled", "shadow", "research"), "unknown mode")
    policy = read_json((ROOT / "config/policy.json").read_text(encoding="utf-8"))
    from .vendor.q1_tools import validate_offline_policy
    validate_offline_policy(policy)
    paths = sorted(p for p in (ROOT / "helm_quantum").rglob("*.py")
                   if "compiler" not in p.relative_to(ROOT / "helm_quantum").parts)
    context = OfflineAdmission(
        goal, mode, time.time_ns() // 1_000_000 + 60_000,
        digest({p.relative_to(ROOT).as_posix(): file_digest(p) for p in paths}),
        file_digest(ROOT / "fixtures/public/q1-mod4.json"),
        file_digest(Path(__file__).with_name("verifier.py")), _TOKEN)
    _LIVE.add(context)
    return context
