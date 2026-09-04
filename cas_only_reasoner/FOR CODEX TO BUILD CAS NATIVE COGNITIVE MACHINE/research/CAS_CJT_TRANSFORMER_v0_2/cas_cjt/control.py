"""The audited Bias-to-neural-control materialization boundary."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor

from casformer import CASControl

from .artifacts import StoredArtifact, decode_tensor
from .checkpoint import encode_module_checkpoint
from .contracts import canonical_digest
from .memory import retrieve_memory
from .network import NeuralCJTNetwork
from .network_coordinator import NetworkStateEnvelope
from .readiness import DWPProfile
from .routing import (
    CASOhmRouter,
    CASOhmRoutingResult,
    ComputePolicy,
    NativeComputeInputs,
    PostExecutionObservation,
    RouteInputs,
    allocate_global_charge_tensor,
    global_memory_read_limit,
    realized_flow_tensors,
)
from .state import tensor_ref_from_mapping
from .types import BiasState, CausePacket, OperatingRegion


class ControlBindingError(ValueError):
    """Cause, Bias, checkpoint, or control data failed an exact binding check."""


@dataclass(frozen=True, slots=True)
class RouteSettings:
    """Exact authored controls; floating tensors are derived from these units."""

    drive_units: int = 2_000_000
    resistance_capability_units: int = 250_000
    resistance_context_units: int = 250_000
    resistance_resource_units: int = 250_000
    resistance_memory_units: int = 250_000
    unit_scale: int = 1_000_000
    causal: bool = False
    topology_open: bool = True
    permission_open: bool = True
    budget_open: bool = True
    force_breakdown: bool = False

    def validate(self) -> None:
        for name in (
            "drive_units",
            "resistance_capability_units",
            "resistance_context_units",
            "resistance_resource_units",
            "resistance_memory_units",
            "unit_scale",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ControlBindingError(f"{name} must be a nonnegative integer")
        if self.unit_scale <= 0:
            raise ControlBindingError("unit_scale must be positive")
        if self.drive_units > 0 and self.total_resistance_units <= 0:
            raise ControlBindingError("positive Drive requires positive total resistance")

    @property
    def total_resistance_units(self) -> int:
        return (
            self.resistance_capability_units
            + self.resistance_context_units
            + self.resistance_resource_units
            + self.resistance_memory_units
        )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "drive_units": self.drive_units,
            "resistance_capability_units": self.resistance_capability_units,
            "resistance_context_units": self.resistance_context_units,
            "resistance_resource_units": self.resistance_resource_units,
            "resistance_memory_units": self.resistance_memory_units,
            "unit_scale": self.unit_scale,
            "causal": self.causal,
            "topology_open": self.topology_open,
            "permission_open": self.permission_open,
            "budget_open": self.budget_open,
            "force_breakdown": self.force_breakdown,
        }


@dataclass(frozen=True)
class MaterializedControl:
    cause_tensor: Tensor
    bias_tensor: Tensor
    bias: BiasState
    control: CASControl
    routing: CASOhmRoutingResult
    observation: PostExecutionObservation
    current_microunits: Tensor
    total_current_microunits: Tensor
    flow_allocation_ppm: Tensor
    conducting_query_mask: Tensor
    memory_reads: tuple[Mapping[str, Any], ...]
    binding_manifest: Mapping[str, Any]
    binding_digest: str


class _ArtifactStore:
    def load_artifact(self, artifact_id: str) -> StoredArtifact: ...

    def has_artifact(self, artifact_id: str, sha256_digest: str | None = None) -> bool: ...


def _region_multiplier_ppm(region: OperatingRegion) -> int:
    return {
        OperatingRegion.UNASSESSED: 1_000_000,
        OperatingRegion.CUTOFF: 1_000_000,
        OperatingRegion.ACTIVE: 1_000_000,
        OperatingRegion.SATURATION: 500_000,
        OperatingRegion.BREAKDOWN: 0,
        OperatingRegion.NON_OHMIC: 0,
        OperatingRegion.UNSTABLE: 0,
    }[region]


def _resolve_artifact(
    store: _ArtifactStore,
    artifact_id: str,
    digest: str,
    supplied: Sequence[StoredArtifact],
) -> StoredArtifact:
    matches = [item for item in supplied if item.artifact_id == artifact_id]
    if len(matches) > 1:
        raise ControlBindingError("duplicate supplied artifact identity")
    if matches:
        artifact = matches[0]
    else:
        artifact = store.load_artifact(artifact_id)
    if artifact.sha256 != digest:
        raise ControlBindingError("artifact digest does not match its bound reference")
    artifact.verify()
    return artifact


class BiasControlMaterializer:
    """Build all neural controls from one durable network head and typed Cause."""

    def __init__(self, network: NeuralCJTNetwork, store: _ArtifactStore) -> None:
        self.network = network
        self.store = store

    def materialize(
        self,
        *,
        state: NetworkStateEnvelope,
        cause: CausePacket,
        cjt_id: str,
        settings: RouteSettings,
        supplied_artifacts: Sequence[StoredArtifact] = (),
    ) -> MaterializedControl:
        settings.validate()
        if not state.digest_valid:
            raise ControlBindingError("network state digest is invalid")
        try:
            bias = state.by_cjt_id[cjt_id]
        except KeyError as exc:
            raise ControlBindingError("requested CJT is not in the durable network state") from exc
        if self.network.spec(cjt_id).operation_id != bias.stable.registered_operation_id:
            raise ControlBindingError("neural node operation does not match its Bias")
        if cause.content_ref is None:
            raise ControlBindingError("runtime Causes require an artifact-backed dense input")
        cause_artifact = _resolve_artifact(
            self.store,
            cause.content_ref.artifact_id,
            cause.content_ref.sha256,
            supplied_artifacts,
        )
        x = decode_tensor(cause.content_ref, cause_artifact)
        if x.ndim != 3 or x.shape[-1] != self.network.config.d_model:
            raise ControlBindingError("Cause tensor does not match the network model width")
        if not x.is_floating_point() or not bool(torch.isfinite(x).all().item()):
            raise ControlBindingError("Cause tensor must be finite floating point")
        current_checkpoint = encode_module_checkpoint(self.network)
        if current_checkpoint.model_digest != state.model_digest:
            raise ControlBindingError("in-memory model does not match the durable checkpoint head")
        if bias.theta.model_digest != state.model_digest:
            raise ControlBindingError("Bias Theta does not match the global checkpoint head")
        live_beta_by_head = tuple(
            int(item)
            for item in torch.round(
                self.network.node(cjt_id).engine.cjt_gate.beta.detach().to(
                    device="cpu", dtype=torch.float64
                )
                * 1_000_000
            )
            .to(dtype=torch.int64)
            .tolist()
        )
        if not live_beta_by_head or any(
            item != bias.theta.beta_microunits for item in live_beta_by_head
        ):
            raise ControlBindingError(
                "live neural beta does not match the value declared by Bias Theta"
            )

        if bias.memory.recurrent_state_ref is None:
            bias_tensor = torch.zeros_like(x)
            recurrent_ref = None
        else:
            recurrent_ref = bias.memory.recurrent_state_ref
            recurrent_artifact = _resolve_artifact(
                self.store,
                recurrent_ref.artifact_id,
                recurrent_ref.sha256,
                supplied_artifacts,
            )
            bias_tensor = decode_tensor(recurrent_ref, recurrent_artifact).to(
                device=x.device, dtype=x.dtype
            )
            if bias_tensor.shape != x.shape:
                raise ControlBindingError("persistent recurrent Bias shape does not match Cause")

        batch, sequence, width = x.shape
        heads = self.network.config.num_heads
        semantic = torch.matmul(x, x.transpose(-2, -1)) / math.sqrt(width)
        semantic = semantic.unsqueeze(1).expand(batch, heads, sequence, sequence).contiguous()
        shape = semantic.shape

        def float_units(value: int) -> Tensor:
            return torch.full(
                shape,
                value / settings.unit_scale,
                dtype=x.dtype,
                device=x.device,
            )

        def mask(value: bool) -> Tensor:
            return torch.full(shape, value, dtype=torch.bool, device=x.device)

        topology = mask(settings.topology_open)
        if settings.causal:
            topology = topology & torch.ones(
                (sequence, sequence), dtype=torch.bool, device=x.device
            ).tril().view(1, 1, sequence, sequence)
        permission_open = (
            settings.permission_open
            and "execute" in bias.governance.hard_permissions
            and not bias.governance.quarantined
        )
        permission = mask(permission_open)
        budget = mask(settings.budget_open and bias.governance.compute_ceiling_units > 0)
        quarantine = mask(bias.governance.quarantined)
        readiness = DWPProfile.from_state(bias.rpm.readiness, semantic)
        prior_ppm = 0 if settings.force_breakdown else _region_multiplier_ppm(
            bias.operating.region
        )
        prior = float_units(prior_ppm)
        native = NativeComputeInputs(
            drive_units=torch.full(
                shape, settings.drive_units, dtype=torch.int64, device=x.device
            ),
            resistance_units=torch.full(
                shape,
                settings.total_resistance_units,
                dtype=torch.int64,
                device=x.device,
            ),
            canonical_route_ids=tuple(f"key-{index:04d}" for index in range(sequence)),
            flow_scale_units=settings.unit_scale,
        )
        router = CASOhmRouter(
            ComputePolicy(
                max_routes=bias.governance.compute_ceiling_units,
                max_reasoning_steps=bias.governance.compute_ceiling_units,
                max_branches=min(4, bias.governance.compute_ceiling_units),
                max_memory_reads=min(4, bias.governance.compute_ceiling_units),
                max_diagnostic_probes=min(4, bias.governance.compute_ceiling_units),
            )
        )
        routing = router.route(
            RouteInputs(
                semantic_scores=semantic,
                drive=float_units(settings.drive_units),
                resistance_capability=float_units(settings.resistance_capability_units),
                resistance_context=float_units(settings.resistance_context_units),
                resistance_resource=float_units(settings.resistance_resource_units),
                resistance_memory=float_units(settings.resistance_memory_units),
                prior_region_multiplier=prior,
                topology_mask=topology,
                permission_mask=permission,
                quarantine_mask=quarantine,
                budget_mask=budget,
                readiness=readiness,
                native_compute=native,
                reference_drive=self.network.config.reference_drive,
                reference_resistance=self.network.config.reference_resistance,
                minimum_total_resistance=self.network.config.minimum_total_resistance,
            )
        )

        (
            current_microunits,
            total_current_microunits,
            flow_allocation_ppm,
            conducting_query_mask,
        ) = realized_flow_tensors(
            routing.current,
            routing.effective_mask,
            native.canonical_route_ids,
        )

        # Memory remains a candidate input.  Resolve only the number of reads
        # admitted by the predeclared plan, verify each immutable record, and
        # blend artifact-backed contributions into the Bias input.  It cannot
        # grant routing, truth, publication, or write authority.
        memory_reads: tuple[Mapping[str, Any], ...] = ()
        memory_capacity = torch.where(
            conducting_query_mask.to(device=routing.compute_plan.memory_read_quanta.device),
            routing.compute_plan.memory_read_quanta,
            torch.zeros_like(routing.compute_plan.memory_read_quanta),
        )
        memory_budget = global_memory_read_limit(
            tuple(int(item) for item in memory_capacity.reshape(-1).tolist()),
            tuple(
                bool(item)
                for item in conducting_query_mask.reshape(-1).tolist()
            ),
            global_ceiling=bias.governance.compute_ceiling_units,
        )
        if (
            cause.memory_refs
            and memory_budget > 0
            and "read_memory" in bias.governance.hard_permissions
        ):
            memory_reads = retrieve_memory(
                self.store,
                cause.memory_refs,
                permitted_ids=cause.memory_refs,
                max_reads=memory_budget,
            )
        contribution_tensors: list[Tensor] = []
        for record in memory_reads:
            raw_reference = record.get("content_ref")
            if raw_reference is None:
                continue
            reference = tensor_ref_from_mapping(raw_reference)
            memory_artifact = _resolve_artifact(
                self.store,
                reference.artifact_id,
                reference.sha256,
                supplied_artifacts,
            )
            contribution = decode_tensor(reference, memory_artifact).to(
                device=x.device, dtype=x.dtype
            )
            if contribution.shape != x.shape or not bool(
                torch.isfinite(contribution).all().item()
            ):
                raise ControlBindingError(
                    "memory contribution must be finite and match the Cause tensor"
                )
            confidence = int(record["confidence_ppm"])
            contribution_tensors.append(contribution * (confidence / 1_000_000))
        if contribution_tensors:
            bias_tensor = bias_tensor + torch.stack(contribution_tensors).mean(dim=0)
        registration = self.network.node(cjt_id).operations.registration(
            bias.stable.registered_operation_id
        )
        relation_ids = torch.full(
            shape,
            registration.relation_index,
            dtype=torch.long,
            device=x.device,
        )
        breakdown = torch.full(
            (batch, heads, sequence),
            settings.force_breakdown,
            dtype=torch.bool,
            device=x.device,
        )
        # v0.1 named the fourth soft component R_policy.  Here that legacy
        # numeric slot carries R_memory; policy remains the exact permission
        # mask.  The sum therefore matches the v0.2 routing law.
        control = CASControl(
            drive=float_units(settings.drive_units),
            resistance_capability=float_units(settings.resistance_capability_units),
            resistance_policy=float_units(settings.resistance_memory_units),
            resistance_context=float_units(settings.resistance_context_units),
            resistance_resource=float_units(settings.resistance_resource_units),
            readiness=readiness.effective_readiness,
            region_multiplier=prior,
            topology_mask=routing.effective_mask,
            permission_mask=routing.effective_mask,
            relation_ids=relation_ids,
            bias=bias_tensor,
            breakdown_mask=breakdown,
            profile_id=bias.rpm.readiness.profile_id,
            provenance="BIAS_CONTROL_MATERIALIZER/0.2",
            drive_provenance=f"cause:{cause.cause_id}",
            resistance_provenance=f"bias:{bias.state_digest}",
            control_tick=cause.tick,
            feedback_source_tick=(
                bias.operating.last_tick if 0 <= bias.operating.last_tick < cause.tick else None
            ),
        )
        route_used = routing.effective_mask.sum(dim=-1, dtype=torch.int64)
        zero = torch.zeros_like(route_used)
        conducting = conducting_query_mask.to(device=route_used.device)
        observation = PostExecutionObservation(
            routes_executed=route_used,
            reasoning_steps_used=torch.where(
                conducting, torch.ones_like(route_used), zero
            ),
            branches_opened=zero,
            memory_reads_used=allocate_global_charge_tensor(
                routing.compute_plan.memory_read_quanta,
                conducting,
                len(memory_reads),
            ),
            diagnostic_probes_used=zero,
        )
        observation.validate_against(routing.compute_plan)
        manifest = {
            "schema_version": "cas.neural-cjt.control-binding/0.2",
            "cause_id": cause.cause_id,
            "cause_artifact_id": cause.content_ref.artifact_id,
            "cause_artifact_digest": cause.content_ref.sha256,
            "bias_id": bias.bias_id,
            "bias_version": bias.version,
            "bias_digest": bias.state_digest,
            "recurrent_bias_artifact_id": (
                None if recurrent_ref is None else recurrent_ref.artifact_id
            ),
            "recurrent_bias_digest": None if recurrent_ref is None else recurrent_ref.sha256,
            "model_digest": state.model_digest,
            "declared_beta_microunits": bias.theta.beta_microunits,
            "live_beta_by_head_microunits": list(live_beta_by_head),
            "readiness_profile_id": bias.rpm.readiness.profile_id,
            "operating_region": bias.operating.region.value,
            "governance_permissions": list(bias.governance.hard_permissions),
            "route_settings": settings.to_dict(),
            "native_compute": native.to_authoritative_dict(),
            "compute_policy": router.compute_policy.to_authoritative_dict(),
            "hard_masks": {
                "topology_mask": topology.detach().to(device="cpu").tolist(),
                "permission_mask": permission.detach().to(device="cpu").tolist(),
                "quarantine_mask": quarantine.detach().to(device="cpu").tolist(),
                "budget_mask": budget.detach().to(device="cpu").tolist(),
                "readiness_hard_mask": readiness.hard_mask.detach()
                .to(device="cpu")
                .tolist(),
            },
            "compute_plan": routing.compute_plan.to_authoritative_dict(),
            "memory_read_requests": list(cause.memory_refs),
            "memory_reads": [dict(item) for item in memory_reads],
        }
        return MaterializedControl(
            cause_tensor=x,
            bias_tensor=bias_tensor,
            bias=bias,
            control=control,
            routing=routing,
            observation=observation,
            current_microunits=current_microunits,
            total_current_microunits=total_current_microunits,
            flow_allocation_ppm=flow_allocation_ppm,
            conducting_query_mask=conducting_query_mask,
            memory_reads=memory_reads,
            binding_manifest=manifest,
            binding_digest=canonical_digest(manifest),
        )


__all__ = [
    "BiasControlMaterializer",
    "ControlBindingError",
    "MaterializedControl",
    "RouteSettings",
]
