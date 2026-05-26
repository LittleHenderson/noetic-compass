"""Open-weight CAS Harness scale planner.

The planner is intentionally not a verdict runner. It turns a declared
open-weight model size into an auditable deployment plan: one orchestrator,
many probe workers, contiguous layer assignments, and explicit evidence
requirements. It does not offer black-box/output-only audit mode.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil
from typing import Literal


Precision = Literal["fp16", "bf16", "int8", "int4"]
AuditDepth = Literal["FULL_INTERNAL", "LAYER_SAMPLE"]
ScaleTier = Literal[
    "single_worker_open_weight",
    "small_distributed_open_weight",
    "distributed_open_weight",
    "enterprise_distributed_open_weight",
]


_BYTES_PER_PARAM: dict[Precision, float] = {
    "fp16": 2.0,
    "bf16": 2.0,
    "int8": 1.0,
    "int4": 0.5,
}


@dataclass(frozen=True)
class ScalePlanRequest:
    model_id: str
    parameter_count_b: float
    num_layers: int | None = None
    precision: Precision = "bf16"
    available_gpu_memory_gb: int | None = None
    audit_depth: AuditDepth = "FULL_INTERNAL"


@dataclass(frozen=True)
class WorkerAssignment:
    worker_id: str
    layer_start: int
    layer_end: int
    shard_id: str
    assigned_methods: tuple[str, ...]
    expected_outputs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["assigned_methods"] = list(self.assigned_methods)
        payload["expected_outputs"] = list(self.expected_outputs)
        return payload


@dataclass(frozen=True)
class MemoryEstimate:
    precision: Precision
    total_weight_memory_gb: float
    activation_overhead_gb: float
    estimated_total_runtime_gb: float
    estimated_memory_per_worker_gb: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ScalePlan:
    model_id: str
    weight_access: Literal["open_weight"]
    parameter_count_b: float
    num_layers: int
    scale_tier: ScaleTier
    recommended_worker_count: int
    orchestration_pattern: str
    worker_assignments: tuple[WorkerAssignment, ...]
    memory_estimate: MemoryEstimate
    expected_capability: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "weight_access": self.weight_access,
            "parameter_count_b": self.parameter_count_b,
            "num_layers": self.num_layers,
            "scale_tier": self.scale_tier,
            "recommended_worker_count": self.recommended_worker_count,
            "orchestration_pattern": self.orchestration_pattern,
            "worker_assignments": [assignment.to_dict() for assignment in self.worker_assignments],
            "memory_estimate": self.memory_estimate.to_dict(),
            "expected_capability": list(self.expected_capability),
            "evidence_requirements": list(self.evidence_requirements),
            "limitations": list(self.limitations),
        }


def build_scale_plan(request: ScalePlanRequest) -> ScalePlan:
    """Build an open-weight distributed CAS Harness plan.

    The plan is layer/shard based. It deliberately avoids the misleading
    "one harness per 1B parameters" framing because a transformer's practical
    audit boundary is layers, blocks, tensor shards, devices, and worker jobs.
    """

    _validate_request(request)
    num_layers = request.num_layers or _estimated_layers(request.parameter_count_b)
    scale_tier = _scale_tier(request.parameter_count_b)
    worker_count = _recommended_worker_count(
        parameter_count_b=request.parameter_count_b,
        num_layers=num_layers,
        scale_tier=scale_tier,
        memory_estimate=_memory_estimate(
            parameter_count_b=request.parameter_count_b,
            precision=request.precision,
            worker_count=1,
        ),
        available_gpu_memory_gb=request.available_gpu_memory_gb,
    )
    memory = _memory_estimate(
        parameter_count_b=request.parameter_count_b,
        precision=request.precision,
        worker_count=worker_count,
    )

    return ScalePlan(
        model_id=request.model_id,
        weight_access="open_weight",
        parameter_count_b=round(request.parameter_count_b, 3),
        num_layers=num_layers,
        scale_tier=scale_tier,
        recommended_worker_count=worker_count,
        orchestration_pattern=(
            "CAS Orchestrator + distributed Probe Workers assigned by contiguous "
            "layer ranges and model shards; one merged Evidence Packet and one verdict."
        ),
        worker_assignments=_assign_layers(
            num_layers=num_layers,
            worker_count=worker_count,
            audit_depth=request.audit_depth,
        ),
        memory_estimate=memory,
        expected_capability=_expected_capability(scale_tier, request.audit_depth),
        evidence_requirements=(
            "open model weights or customer-hosted activation hooks",
            "model identity plus weight/tokenizer hashes",
            "per-worker layer-range manifest",
            "hidden-state capture for selected CAS probe axes",
            "targeted ablation/intervention result where the architecture permits it",
            "matched random/wrong-drive control runs",
            "orchestrator merge record binding worker evidence into one Evidence Packet",
        ),
        limitations=_limitations(scale_tier, request.audit_depth),
    )


def _validate_request(request: ScalePlanRequest) -> None:
    if not request.model_id.strip():
        raise ValueError("model_id is required")
    if request.parameter_count_b <= 0:
        raise ValueError("parameter_count_b must be positive")
    if request.parameter_count_b > 300:
        raise ValueError("enterprise planner currently supports open-weight models up to 300B parameters")
    if request.num_layers is not None and request.num_layers <= 0:
        raise ValueError("num_layers must be positive when provided")
    if request.precision not in _BYTES_PER_PARAM:
        raise ValueError("precision must be one of fp16, bf16, int8, int4")
    if request.audit_depth not in {"FULL_INTERNAL", "LAYER_SAMPLE"}:
        raise ValueError("CAS Harness beta supports open-weight internal audit modes only")
    if request.available_gpu_memory_gb is not None and request.available_gpu_memory_gb <= 0:
        raise ValueError("available_gpu_memory_gb must be positive when provided")


def _scale_tier(parameter_count_b: float) -> ScaleTier:
    if parameter_count_b <= 1:
        return "single_worker_open_weight"
    if parameter_count_b <= 20:
        return "small_distributed_open_weight"
    if parameter_count_b <= 70:
        return "distributed_open_weight"
    return "enterprise_distributed_open_weight"


def _estimated_layers(parameter_count_b: float) -> int:
    if parameter_count_b <= 1:
        return 12
    if parameter_count_b <= 20:
        return 40
    if parameter_count_b <= 70:
        return 80
    if parameter_count_b <= 150:
        return 120
    return 160


def _recommended_worker_count(
    *,
    parameter_count_b: float,
    num_layers: int,
    scale_tier: ScaleTier,
    memory_estimate: MemoryEstimate,
    available_gpu_memory_gb: int | None,
) -> int:
    layer_floor = {
        "single_worker_open_weight": 1,
        "small_distributed_open_weight": max(2, ceil(num_layers / 20)),
        "distributed_open_weight": max(4, ceil(num_layers / 14)),
        "enterprise_distributed_open_weight": max(8, ceil(num_layers / 10)),
    }[scale_tier]

    size_floor = max(1, ceil(parameter_count_b / 12))
    memory_floor = 1
    if available_gpu_memory_gb:
        usable_gb = max(1.0, available_gpu_memory_gb * 0.62)
        memory_floor = ceil(memory_estimate.estimated_total_runtime_gb / usable_gb)

    return min(64, max(layer_floor, size_floor, memory_floor))


def _memory_estimate(
    *,
    parameter_count_b: float,
    precision: Precision,
    worker_count: int,
) -> MemoryEstimate:
    total_weight_gb = parameter_count_b * _BYTES_PER_PARAM[precision]
    activation_overhead_gb = total_weight_gb * 0.18
    total_runtime_gb = total_weight_gb + activation_overhead_gb
    per_worker = total_runtime_gb / max(worker_count, 1)
    return MemoryEstimate(
        precision=precision,
        total_weight_memory_gb=round(total_weight_gb, 2),
        activation_overhead_gb=round(activation_overhead_gb, 2),
        estimated_total_runtime_gb=round(total_runtime_gb, 2),
        estimated_memory_per_worker_gb=round(per_worker, 2),
    )


def _assign_layers(
    *,
    num_layers: int,
    worker_count: int,
    audit_depth: AuditDepth,
) -> tuple[WorkerAssignment, ...]:
    assignment_count = min(worker_count, num_layers)
    methods = (
        "foundation_probe",
        "inversion_scan",
        "blindspot_detection",
        "verification_stack",
    )
    if audit_depth == "FULL_INTERNAL":
        methods = methods + ("targeted_ablation", "matched_controls")

    assignments: list[WorkerAssignment] = []
    cursor = 0
    base = num_layers // assignment_count
    remainder = num_layers % assignment_count
    for index in range(assignment_count):
        width = base + (1 if index < remainder else 0)
        start = cursor
        end = cursor + width - 1
        assignments.append(
            WorkerAssignment(
                worker_id=f"probe-worker-{index + 1:02d}",
                layer_start=start,
                layer_end=end,
                shard_id=f"layers-{start:03d}-{end:03d}",
                assigned_methods=methods,
                expected_outputs=(
                    "layer_activation_summary",
                    "cas_axis_readout",
                    "blindspot_overlay",
                    "worker_evidence_manifest",
                ),
            )
        )
        cursor = end + 1
    return tuple(assignments)


def _expected_capability(scale_tier: ScaleTier, audit_depth: AuditDepth) -> tuple[str, ...]:
    base = [
        "open-weight model identity verification",
        "hidden-state CAS probe readout by layer range",
        "blindspot and inversion proxy attribution by assigned worker slice",
        "single orchestrated Evidence Packet across all workers",
        "one final ACCEPT / SUPPRESS / FLAG FOR HUMAN REVIEW verdict gate",
    ]
    if audit_depth == "FULL_INTERNAL":
        base.extend(
            [
                "targeted ablation or intervention where hooks are available",
                "matched random/wrong-drive controls per worker slice",
            ]
        )
    if scale_tier == "enterprise_distributed_open_weight":
        base.append("enterprise scheduling across many GPUs or customer-hosted shards")
    return tuple(base)


def _limitations(scale_tier: ScaleTier, audit_depth: AuditDepth) -> tuple[str, ...]:
    limitations = [
        "requires open weights, activation hooks, or customer-hosted internal telemetry",
        "does not support black-box/API-only model audits in this product lane",
        "worker counts are planning estimates until the target hardware profile is known",
        "one CAS Harness per 1B parameters is not the architecture; layer/shard workers are",
    ]
    if audit_depth == "LAYER_SAMPLE":
        limitations.append("layer-sample mode reduces cost but cannot claim full-layer coverage")
    if scale_tier == "enterprise_distributed_open_weight":
        limitations.append("70B-300B audits require enterprise GPU scheduling and an orchestrator merge step")
    return tuple(limitations)
