"""Scale planning for CAS Harness open-weight model audits."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from math import ceil
from typing import Any, Mapping


class TargetMode(str, Enum):
    """Supported CAS Harness audit depths for open-weight models."""

    FULL_INTERNAL = "FULL_INTERNAL"
    LAYER_SAMPLE = "LAYER_SAMPLE"


class ScaleTier(str, Enum):
    """Operational model-size tiers for open-weight CAS Harness audits."""

    SINGLE_WORKER = "single_worker"
    SMALL_DISTRIBUTED_OPTIONAL = "small_distributed_optional"
    DISTRIBUTED = "distributed"
    ENTERPRISE_DISTRIBUTED = "enterprise_distributed"


@dataclass(frozen=True)
class ScalePlannerRequest:
    model_id: str
    parameter_count_b: float
    num_layers: int | None = None
    precision: str = "bf16"
    quantization: str | None = None
    available_gpu_memory_gb: float | None = None
    target_mode: TargetMode | str = TargetMode.FULL_INTERNAL


@dataclass(frozen=True)
class WorkerAssignment:
    worker_id: str
    shard_id: int
    shard_count: int
    layer_start: int
    layer_end: int
    assigned_layers: int
    role: str
    target_mode: str


@dataclass(frozen=True)
class MemoryEstimate:
    precision: str
    quantization: str | None
    bytes_per_parameter: float
    total_weight_memory_gb: float
    activation_workspace_gb: float
    coordination_overhead_gb: float
    safety_buffer_gb: float
    total_estimated_memory_gb: float
    estimated_memory_per_worker_gb: float
    available_gpu_memory_gb: float | None
    fits_available_gpu_memory: bool | None


@dataclass(frozen=True)
class EnterpriseAuditPlan:
    model_id: str
    parameter_count_b: float
    num_layers: int
    layer_count_source: str
    target_mode: str
    scale_tier: str
    recommended_worker_count: int
    worker_assignments: tuple[WorkerAssignment, ...]
    memory_estimate: MemoryEstimate
    expected_capability: dict[str, str]
    limitations: tuple[str, ...]
    evidence_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready representation for route integration."""

        return {
            "model_id": self.model_id,
            "parameter_count_b": self.parameter_count_b,
            "num_layers": self.num_layers,
            "layer_count_source": self.layer_count_source,
            "target_mode": self.target_mode,
            "scale_tier": self.scale_tier,
            "recommended_worker_count": self.recommended_worker_count,
            "worker_assignments": [asdict(assignment) for assignment in self.worker_assignments],
            "memory_estimate": asdict(self.memory_estimate),
            "expected_capability": dict(self.expected_capability),
            "limitations": list(self.limitations),
            "evidence_requirements": list(self.evidence_requirements),
        }


PRECISION_BYTES: dict[str, tuple[str, float]] = {
    "fp32": ("fp32", 4.0),
    "float32": ("fp32", 4.0),
    "bf16": ("bf16", 2.0),
    "bfloat16": ("bf16", 2.0),
    "fp16": ("fp16", 2.0),
    "float16": ("fp16", 2.0),
    "fp8": ("fp8", 1.0),
}

QUANTIZATION_BYTES: dict[str, tuple[str, float]] = {
    "int8": ("int8", 1.0),
    "8bit": ("int8", 1.0),
    "8-bit": ("int8", 1.0),
    "int4": ("int4", 0.5),
    "4bit": ("int4", 0.5),
    "4-bit": ("int4", 0.5),
    "nf4": ("nf4", 0.5),
    "gptq-int4": ("gptq-int4", 0.5),
    "awq-int4": ("awq-int4", 0.5),
    "int2": ("int2", 0.25),
    "2bit": ("int2", 0.25),
    "2-bit": ("int2", 0.25),
}

DISALLOWED_AUDIT_MODES = {
    "BLACK_BOX",
    "BLACKBOX",
    "OUTPUT_ONLY",
    "OUTPUTONLY",
    "API_ONLY",
    "REMOTE_API",
    "PROMPT_ONLY",
}


def build_cas_harness_scale_plan(
    request: ScalePlannerRequest | Mapping[str, Any],
) -> EnterpriseAuditPlan:
    """Build an enterprise execution plan for an open-weight model audit."""

    normalized = _normalize_request(request)
    scale_tier = _scale_tier_for(normalized.parameter_count_b)
    layer_count, layer_count_source = _resolve_layer_count(
        normalized.parameter_count_b,
        normalized.num_layers,
    )
    precision, quantization, bytes_per_parameter = _resolve_storage_format(
        normalized.precision,
        normalized.quantization,
    )

    worker_count = _initial_worker_count(
        parameter_count_b=normalized.parameter_count_b,
        num_layers=layer_count,
        scale_tier=scale_tier,
        target_mode=normalized.target_mode,
    )
    worker_count = _adjust_workers_for_memory(
        parameter_count_b=normalized.parameter_count_b,
        bytes_per_parameter=bytes_per_parameter,
        worker_count=worker_count,
        max_workers=layer_count,
        available_gpu_memory_gb=normalized.available_gpu_memory_gb,
        target_mode=normalized.target_mode,
        quantization=quantization,
    )

    assignments = _build_worker_assignments(
        num_layers=layer_count,
        worker_count=worker_count,
        target_mode=normalized.target_mode,
    )
    memory_estimate = _build_memory_estimate(
        parameter_count_b=normalized.parameter_count_b,
        precision=precision,
        quantization=quantization,
        bytes_per_parameter=bytes_per_parameter,
        worker_count=worker_count,
        available_gpu_memory_gb=normalized.available_gpu_memory_gb,
        target_mode=normalized.target_mode,
    )

    limitations = _build_limitations(
        layer_count_source=layer_count_source,
        memory_estimate=memory_estimate,
        target_mode=normalized.target_mode,
    )

    return EnterpriseAuditPlan(
        model_id=normalized.model_id,
        parameter_count_b=normalized.parameter_count_b,
        num_layers=layer_count,
        layer_count_source=layer_count_source,
        target_mode=normalized.target_mode.value,
        scale_tier=scale_tier.value,
        recommended_worker_count=worker_count,
        worker_assignments=assignments,
        memory_estimate=memory_estimate,
        expected_capability=_build_expected_capability(
            num_layers=layer_count,
            worker_count=worker_count,
            target_mode=normalized.target_mode,
            scale_tier=scale_tier,
        ),
        limitations=limitations,
        evidence_requirements=_build_evidence_requirements(normalized.target_mode),
    )


def plan_cas_harness_scale(
    request: ScalePlannerRequest | Mapping[str, Any],
) -> EnterpriseAuditPlan:
    """Backward-compatible alias for callers that prefer a shorter name."""

    return build_cas_harness_scale_plan(request)


def _normalize_request(request: ScalePlannerRequest | Mapping[str, Any]) -> ScalePlannerRequest:
    if isinstance(request, ScalePlannerRequest):
        return ScalePlannerRequest(
            model_id=_validate_model_id(request.model_id),
            parameter_count_b=_validate_parameter_count(request.parameter_count_b),
            num_layers=_validate_optional_positive_int(request.num_layers, "num_layers"),
            precision=request.precision,
            quantization=request.quantization,
            available_gpu_memory_gb=_validate_optional_positive_float(
                request.available_gpu_memory_gb,
                "available_gpu_memory_gb",
            ),
            target_mode=_normalize_target_mode(request.target_mode),
        )

    if not isinstance(request, Mapping):
        raise TypeError("request must be a ScalePlannerRequest or mapping")

    _reject_disallowed_access_modes(request)
    return ScalePlannerRequest(
        model_id=_validate_model_id(request.get("model_id")),
        parameter_count_b=_validate_parameter_count(request.get("parameter_count_b")),
        num_layers=_validate_optional_positive_int(request.get("num_layers"), "num_layers"),
        precision=str(request.get("precision", "bf16")),
        quantization=_normalize_optional_string(request.get("quantization")),
        available_gpu_memory_gb=_validate_optional_positive_float(
            request.get("available_gpu_memory_gb"),
            "available_gpu_memory_gb",
        ),
        target_mode=_normalize_target_mode(request.get("target_mode", TargetMode.FULL_INTERNAL)),
    )


def _reject_disallowed_access_modes(request: Mapping[str, Any]) -> None:
    for key in ("target_mode", "audit_mode", "access_mode", "mode"):
        if key not in request:
            continue
        normalized = _canonical_mode_name(request[key])
        if normalized in DISALLOWED_AUDIT_MODES:
            raise ValueError("CAS Harness scale planning requires open-weight internal model access.")


def _normalize_target_mode(value: TargetMode | str | None) -> TargetMode:
    if isinstance(value, TargetMode):
        return value

    normalized = _canonical_mode_name(value or TargetMode.FULL_INTERNAL.value)
    if normalized in DISALLOWED_AUDIT_MODES:
        raise ValueError("CAS Harness scale planning requires open-weight internal model access.")

    aliases = {
        "FULL": TargetMode.FULL_INTERNAL,
        "FULL_INTERNAL": TargetMode.FULL_INTERNAL,
        "INTERNAL": TargetMode.FULL_INTERNAL,
        "LAYER_SAMPLE": TargetMode.LAYER_SAMPLE,
        "LAYER_SAMPLING": TargetMode.LAYER_SAMPLE,
        "SAMPLE": TargetMode.LAYER_SAMPLE,
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported target_mode: {value!r}") from exc


def _canonical_mode_name(value: Any) -> str:
    return str(value).strip().upper().replace("-", "_").replace(" ", "_")


def _validate_model_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("model_id is required")
    return value.strip()


def _validate_parameter_count(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError("parameter_count_b must be a positive number")
    try:
        parameter_count_b = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("parameter_count_b must be a positive number") from exc

    if parameter_count_b <= 0:
        raise ValueError("parameter_count_b must be a positive number")
    if parameter_count_b > 300:
        raise ValueError("CAS Harness open-weight scale planning supports models up to 300B parameters.")
    return parameter_count_b


def _validate_optional_positive_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive integer")
    try:
        as_int = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive integer") from exc
    if as_int <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return as_int


def _validate_optional_positive_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive number")
    try:
        as_float = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive number") from exc
    if as_float <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return as_float


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized or normalized.lower() in {"none", "null", "false"}:
        return None
    return normalized


def _scale_tier_for(parameter_count_b: float) -> ScaleTier:
    if parameter_count_b <= 1:
        return ScaleTier.SINGLE_WORKER
    if parameter_count_b <= 20:
        return ScaleTier.SMALL_DISTRIBUTED_OPTIONAL
    if parameter_count_b < 70:
        return ScaleTier.DISTRIBUTED
    return ScaleTier.ENTERPRISE_DISTRIBUTED


def _resolve_layer_count(parameter_count_b: float, num_layers: int | None) -> tuple[int, str]:
    if num_layers is not None:
        return num_layers, "provided"
    return _estimate_layer_count(parameter_count_b), "estimated"


def _estimate_layer_count(parameter_count_b: float) -> int:
    """Estimate transformer block count from common open-weight scaling bands."""

    if parameter_count_b <= 1:
        return 24
    if parameter_count_b <= 20:
        return max(24, round(24 + ((parameter_count_b - 1) * (24 / 19))))
    if parameter_count_b < 70:
        return round(48 + ((parameter_count_b - 20) * (32 / 50)))
    return round(80 + ((parameter_count_b - 70) * (80 / 230)))


def _resolve_storage_format(precision: str, quantization: str | None) -> tuple[str, str | None, float]:
    precision_key = precision.strip().lower()
    if precision_key not in PRECISION_BYTES:
        supported = ", ".join(sorted(PRECISION_BYTES))
        raise ValueError(f"Unsupported precision {precision!r}; supported values: {supported}")

    normalized_precision, precision_bytes = PRECISION_BYTES[precision_key]
    if quantization is None:
        return normalized_precision, None, precision_bytes

    quant_key = quantization.strip().lower()
    if quant_key not in QUANTIZATION_BYTES:
        supported = ", ".join(sorted(QUANTIZATION_BYTES))
        raise ValueError(f"Unsupported quantization {quantization!r}; supported values: {supported}")
    normalized_quantization, quantization_bytes = QUANTIZATION_BYTES[quant_key]
    return normalized_precision, normalized_quantization, quantization_bytes


def _initial_worker_count(
    *,
    parameter_count_b: float,
    num_layers: int,
    scale_tier: ScaleTier,
    target_mode: TargetMode,
) -> int:
    if scale_tier is ScaleTier.SINGLE_WORKER:
        return 1

    if scale_tier is ScaleTier.SMALL_DISTRIBUTED_OPTIONAL:
        target_layers_per_worker = 32 if target_mode is TargetMode.FULL_INTERNAL else 48
        floor = 2 if target_mode is TargetMode.FULL_INTERNAL else 1
        return min(num_layers, max(floor, ceil(num_layers / target_layers_per_worker)))

    if scale_tier is ScaleTier.DISTRIBUTED:
        target_layers_per_worker = 16 if target_mode is TargetMode.FULL_INTERNAL else 32
        floor = 4 if target_mode is TargetMode.FULL_INTERNAL else 2
        return min(num_layers, max(floor, ceil(num_layers / target_layers_per_worker)))

    target_layers_per_worker = 8 if target_mode is TargetMode.FULL_INTERNAL else 16
    if parameter_count_b <= 100:
        floor = 8 if target_mode is TargetMode.FULL_INTERNAL else 4
    elif parameter_count_b <= 200:
        floor = 12 if target_mode is TargetMode.FULL_INTERNAL else 6
    else:
        floor = 16 if target_mode is TargetMode.FULL_INTERNAL else 8
    return min(num_layers, max(floor, ceil(num_layers / target_layers_per_worker)))


def _adjust_workers_for_memory(
    *,
    parameter_count_b: float,
    bytes_per_parameter: float,
    worker_count: int,
    max_workers: int,
    available_gpu_memory_gb: float | None,
    target_mode: TargetMode,
    quantization: str | None,
) -> int:
    if available_gpu_memory_gb is None:
        return worker_count

    adjusted = worker_count
    while adjusted < max_workers:
        memory = _build_memory_estimate(
            parameter_count_b=parameter_count_b,
            precision="bf16",
            quantization=quantization,
            bytes_per_parameter=bytes_per_parameter,
            worker_count=adjusted,
            available_gpu_memory_gb=available_gpu_memory_gb,
            target_mode=target_mode,
        )
        if memory.estimated_memory_per_worker_gb <= available_gpu_memory_gb:
            return adjusted
        adjusted += 1
    return adjusted


def _build_worker_assignments(
    *,
    num_layers: int,
    worker_count: int,
    target_mode: TargetMode,
) -> tuple[WorkerAssignment, ...]:
    base_layers = num_layers // worker_count
    remainder = num_layers % worker_count
    role = (
        "full_internal_layer_shard"
        if target_mode is TargetMode.FULL_INTERNAL
        else "layer_sample_responsibility_shard"
    )
    assignments: list[WorkerAssignment] = []
    start = 1
    for index in range(worker_count):
        assigned_layers = base_layers + (1 if index < remainder else 0)
        end = start + assigned_layers - 1
        assignments.append(
            WorkerAssignment(
                worker_id=f"worker-{index + 1:02d}",
                shard_id=index + 1,
                shard_count=worker_count,
                layer_start=start,
                layer_end=end,
                assigned_layers=assigned_layers,
                role=role,
                target_mode=target_mode.value,
            )
        )
        start = end + 1
    return tuple(assignments)


def _build_memory_estimate(
    *,
    parameter_count_b: float,
    precision: str,
    quantization: str | None,
    bytes_per_parameter: float,
    worker_count: int,
    available_gpu_memory_gb: float | None,
    target_mode: TargetMode,
) -> MemoryEstimate:
    runtime_multiplier = 1.15 if quantization else 1.0
    sample_multiplier = 0.55 if target_mode is TargetMode.LAYER_SAMPLE else 1.0
    total_weight_memory_gb = parameter_count_b * bytes_per_parameter * runtime_multiplier
    activation_workspace_gb = max(2.0, parameter_count_b * 0.08 * sample_multiplier)
    coordination_overhead_gb = max(1.0, total_weight_memory_gb * 0.04)
    per_worker_before_buffer = (
        (total_weight_memory_gb / worker_count)
        + (activation_workspace_gb / worker_count)
        + max(0.75, coordination_overhead_gb / worker_count)
    )
    safety_buffer_gb = max(1.0, per_worker_before_buffer * 0.10)
    estimated_memory_per_worker_gb = per_worker_before_buffer + safety_buffer_gb
    total_estimated_memory_gb = (
        total_weight_memory_gb
        + activation_workspace_gb
        + coordination_overhead_gb
        + (safety_buffer_gb * worker_count)
    )
    fits = (
        None
        if available_gpu_memory_gb is None
        else estimated_memory_per_worker_gb <= available_gpu_memory_gb
    )

    return MemoryEstimate(
        precision=precision,
        quantization=quantization,
        bytes_per_parameter=bytes_per_parameter,
        total_weight_memory_gb=round(total_weight_memory_gb, 2),
        activation_workspace_gb=round(activation_workspace_gb, 2),
        coordination_overhead_gb=round(coordination_overhead_gb, 2),
        safety_buffer_gb=round(safety_buffer_gb, 2),
        total_estimated_memory_gb=round(total_estimated_memory_gb, 2),
        estimated_memory_per_worker_gb=round(estimated_memory_per_worker_gb, 2),
        available_gpu_memory_gb=available_gpu_memory_gb,
        fits_available_gpu_memory=fits,
    )


def _build_expected_capability(
    *,
    num_layers: int,
    worker_count: int,
    target_mode: TargetMode,
    scale_tier: ScaleTier,
) -> dict[str, str]:
    if target_mode is TargetMode.FULL_INTERNAL:
        coverage = f"All {num_layers} transformer layers assigned across {worker_count} worker(s)."
        depth = "Weight, residual-stream, activation, and layer-local CAS probe capture."
    else:
        coverage = (
            f"{num_layers} transformer layers partitioned into sampling responsibilities "
            f"across {worker_count} worker(s)."
        )
        depth = "Representative internal layer probes with explicit sampled-layer manifests."

    return {
        "audit_surface": "Open-weight internal model artifacts and layer activations.",
        "coverage": coverage,
        "analysis_depth": depth,
        "scale_posture": scale_tier.value,
    }


def _build_limitations(
    *,
    layer_count_source: str,
    memory_estimate: MemoryEstimate,
    target_mode: TargetMode,
) -> tuple[str, ...]:
    limitations: list[str] = [
        "Memory estimates are planning values; final placement must be verified on the target runtime.",
        "Worker ranges assume a transformer-style ordered layer stack and may need remapping for mixture-of-experts or adapter-heavy architectures.",
    ]
    if layer_count_source == "estimated":
        limitations.append("Layer count was estimated from parameter scale and should be replaced with model config metadata before execution.")
    if memory_estimate.fits_available_gpu_memory is False:
        limitations.append("Available GPU memory is below the estimated per-worker footprint; use more layer shards, lower precision, or larger devices.")
    if target_mode is TargetMode.LAYER_SAMPLE:
        limitations.append("Layer-sample mode reduces coverage and requires a sampled-layer manifest for reproducibility.")
    return tuple(limitations)


def _build_evidence_requirements(target_mode: TargetMode) -> tuple[str, ...]:
    requirements = [
        "Model provenance record identifying the exact open weights, revision, and license.",
        "Weight shard manifest with tensor names, precision metadata, and checksums.",
        "Layer index map from embeddings through final block and output head.",
        "CAS Harness configuration, probe set, seeds, worker logs, and replay manifest.",
        "Activation or residual-stream capture records for each assigned layer range.",
        "Hardware and runtime manifest covering GPU type, memory, driver, framework versions, and quantization loader.",
    ]
    if target_mode is TargetMode.LAYER_SAMPLE:
        requirements.append("Sample selection manifest documenting the selected layers and rationale.")
    return tuple(requirements)


__all__ = [
    "EnterpriseAuditPlan",
    "MemoryEstimate",
    "ScalePlannerRequest",
    "ScaleTier",
    "TargetMode",
    "WorkerAssignment",
    "build_cas_harness_scale_plan",
    "plan_cas_harness_scale",
]
