"""Standalone distributed probe-worker protocol schemas.

These models are scaffolding for future open-weight CAS probe workers. They
are intentionally not imported by the live worker routes yet.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ModelScale = Literal["20B", "70B", "100B", "300B"]
WeightAccessMode = Literal["open_weight"]
WorkerStatus = Literal[
    "queued",
    "assigned",
    "running",
    "completed",
    "failed",
    "cancelled",
]
MergeStatus = Literal["pending", "partial", "complete", "failed"]


class DistributedProtocolModel(BaseModel):
    """Base contract for future distributed worker protocol payloads."""

    model_config = ConfigDict(extra="forbid")


class WorkerCapability(DistributedProtocolModel):
    """Advertised worker capacity for open-weight probe execution."""

    worker_id: str = Field(..., min_length=1)
    weight_access: WeightAccessMode = Field(
        default="open_weight",
        description="Only open-weight internal probe execution is supported.",
    )
    supported_model_scales: list[ModelScale] = Field(..., min_length=1)
    supported_methods: list[str] = Field(..., min_length=1)
    supported_outputs: list[str] = Field(..., min_length=1)
    max_layers_per_assignment: int | None = Field(default=None, ge=1)
    max_shards: int | None = Field(default=None, ge=1)
    available_vram_gb: float | None = Field(default=None, ge=0.0)


class ProbeWorkerAssignment(DistributedProtocolModel):
    """Layer-range and shard based work unit for one probe worker."""

    assignment_id: str = Field(..., min_length=1)
    worker_id: str | None = Field(default=None, min_length=1)
    model_id: str = Field(..., min_length=1)
    model_scale: ModelScale
    weight_access: WeightAccessMode = Field(
        default="open_weight",
        description="Black-box output-only execution is not part of this protocol.",
    )
    model_weight_ref: str | None = Field(
        default=None,
        min_length=1,
        description="Optional URI, artifact id, or local reference for model weights.",
    )
    model_weight_hash: str | None = Field(
        default=None,
        min_length=1,
        description="Optional immutable hash for the exact model weights.",
    )
    layer_start: int = Field(..., ge=0, description="Inclusive first layer index.")
    layer_end: int = Field(..., ge=0, description="Inclusive final layer index.")
    shard_id: str = Field(..., min_length=1)
    assigned_methods: list[str] = Field(..., min_length=1)
    expected_outputs: list[str] = Field(..., min_length=1)
    worker_status: WorkerStatus = "queued"

    @model_validator(mode="after")
    def _validate_layer_range(self) -> "ProbeWorkerAssignment":
        if self.layer_end < self.layer_start:
            raise ValueError("layer_end must be greater than or equal to layer_start")
        return self


class DistributedAuditPlan(DistributedProtocolModel):
    """Orchestrator plan for distributed open-weight CAS probing."""

    plan_id: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)
    model_scale: ModelScale
    weight_access: WeightAccessMode = "open_weight"
    model_weight_ref: str | None = Field(default=None, min_length=1)
    model_weight_hash: str | None = Field(default=None, min_length=1)
    total_layers: int = Field(..., ge=1)
    merge_strategy: Literal["contiguous_layer_shards"] = "contiguous_layer_shards"
    expected_outputs: list[str] = Field(..., min_length=1)
    assignments: list[ProbeWorkerAssignment] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate_assignments(self) -> "DistributedAuditPlan":
        seen_assignment_ids: set[str] = set()
        expected_layer_start = 0

        for assignment in sorted(
            self.assignments,
            key=lambda item: (item.layer_start, item.layer_end, item.shard_id),
        ):
            if assignment.assignment_id in seen_assignment_ids:
                raise ValueError(f"duplicate assignment_id: {assignment.assignment_id}")
            seen_assignment_ids.add(assignment.assignment_id)

            if assignment.model_id != self.model_id:
                raise ValueError("assignment model_id must match plan model_id")
            if assignment.model_scale != self.model_scale:
                raise ValueError("assignment model_scale must match plan model_scale")
            if assignment.layer_start != expected_layer_start:
                raise ValueError(
                    "assignments must cover layers contiguously from 0 to total_layers - 1"
                )
            if assignment.layer_end >= self.total_layers:
                raise ValueError("assignment layer_end must be less than total_layers")

            if (
                self.model_weight_ref is not None
                and assignment.model_weight_ref is not None
                and assignment.model_weight_ref != self.model_weight_ref
            ):
                raise ValueError("assignment model_weight_ref must match plan model_weight_ref")
            if (
                self.model_weight_hash is not None
                and assignment.model_weight_hash is not None
                and assignment.model_weight_hash != self.model_weight_hash
            ):
                raise ValueError(
                    "assignment model_weight_hash must match plan model_weight_hash"
                )

            unknown_outputs = set(assignment.expected_outputs) - set(self.expected_outputs)
            if unknown_outputs:
                raise ValueError(
                    "assignment expected_outputs must be declared by the plan: "
                    + ", ".join(sorted(unknown_outputs))
                )

            expected_layer_start = assignment.layer_end + 1

        if expected_layer_start != self.total_layers:
            raise ValueError(
                "assignments must cover layers contiguously from 0 to total_layers - 1"
            )
        return self


class WorkerEvidenceSummary(DistributedProtocolModel):
    """Evidence packet summary emitted by a worker for merger intake."""

    plan_id: str = Field(..., min_length=1)
    assignment_id: str = Field(..., min_length=1)
    worker_id: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)
    model_scale: ModelScale
    weight_access: WeightAccessMode = "open_weight"
    model_weight_ref: str | None = Field(default=None, min_length=1)
    model_weight_hash: str | None = Field(default=None, min_length=1)
    layer_start: int = Field(..., ge=0)
    layer_end: int = Field(..., ge=0)
    shard_id: str = Field(..., min_length=1)
    assigned_methods: list[str] = Field(..., min_length=1)
    expected_outputs: list[str] = Field(..., min_length=1)
    produced_outputs: list[str] = Field(default_factory=list)
    missing_outputs: list[str] = Field(default_factory=list)
    worker_status: WorkerStatus
    evidence_packet_ref: str | None = Field(default=None, min_length=1)
    error_message: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_layer_range(self) -> "WorkerEvidenceSummary":
        if self.layer_end < self.layer_start:
            raise ValueError("layer_end must be greater than or equal to layer_start")
        return self


class OrchestratorMergeSummary(DistributedProtocolModel):
    """Orchestrator view of merged distributed evidence packets."""

    plan_id: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)
    model_scale: ModelScale
    weight_access: WeightAccessMode = "open_weight"
    model_weight_ref: str | None = Field(default=None, min_length=1)
    model_weight_hash: str | None = Field(default=None, min_length=1)
    total_layers: int = Field(..., ge=1)
    merge_status: MergeStatus
    expected_outputs: list[str] = Field(..., min_length=1)
    merged_shards: list[str] = Field(default_factory=list)
    worker_summaries: list[WorkerEvidenceSummary] = Field(default_factory=list)
    missing_layers: list[int] = Field(default_factory=list)
    missing_outputs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_complete_merge(self) -> "OrchestratorMergeSummary":
        for summary in self.worker_summaries:
            if summary.model_id != self.model_id:
                raise ValueError("worker summary model_id must match merge model_id")
            if summary.model_scale != self.model_scale:
                raise ValueError("worker summary model_scale must match merge model_scale")
            if summary.layer_end >= self.total_layers:
                raise ValueError("worker summary layer_end must be less than total_layers")

        if self.merge_status != "complete":
            return self

        expected_layer_start = 0
        for summary in sorted(
            self.worker_summaries,
            key=lambda item: (item.layer_start, item.layer_end, item.shard_id),
        ):
            if summary.worker_status != "completed":
                raise ValueError("complete merge requires completed worker summaries")
            if summary.layer_start != expected_layer_start:
                raise ValueError(
                    "complete merge requires contiguous worker summaries from layer 0"
                )
            expected_layer_start = summary.layer_end + 1

        if expected_layer_start != self.total_layers:
            raise ValueError(
                "complete merge requires contiguous worker summaries through total_layers"
            )
        return self

