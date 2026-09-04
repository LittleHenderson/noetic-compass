"""One atomic authority boundary for a network of Neural CJTs.

The durable state is one global envelope.  Individual CJTs can propose state,
memory, model, Effect, or repair changes, but no proposal is written alone.
The coordinator validates the complete network transition and hands exactly
one compare-and-swap write set to :class:`SQLiteAtomicStore`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields as dataclass_fields, replace
import hmac
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

from .artifacts import ArtifactError, StoredArtifact, decode_tensor
from .contracts import canonical_digest, canonical_json, verify_declared_digest
from .checkpoint import verify_checkpoint
from .coordinator import (
    PROPOSE_MEMORY_WRITE,
    PROPOSE_MODEL_UPDATE,
    PROPOSE_STATE_UPDATE,
    REQUEST_EFFECT_PUBLICATION,
    BatchRejected,
    _artifact_references,
    _decode_pointer,
    _json_clone,
    _receipt_kwargs,
    _require_digest,
    _text,
    _unique_by,
    _wire,
)
from .persistence import (
    ActiveHead,
    AtomicWriteSet,
    IdempotencyConflict,
    ModelVersionWrite,
    PersistenceError,
    SQLiteAtomicStore,
    StaleHeadError,
    StoredDocument,
)
from .phase_contract import PhaseContractError, validate_phase_contract
from .trace import MANDATORY_PHASES, SealedTrace, seal_trace, verify_trace_chain
from .semantic import validate_operation_io, verify_evidence_descriptor
from .learning import LearningError, LearningPolicy, validate_qualification_receipt
from .memory import memory_document
from .repair import open_repair, repair_frame_from_dict, repair_outcome_from_dict
from .routing import (
    RoutingError,
    allocate_global_charge,
    bounded_mean_flow_ppm,
    global_memory_read_limit,
    largest_remainder_flow_ppm,
)
from .state import (
    advance_bias,
    bias_from_dict,
    cause_from_committed_effect,
    content_id,
    make_cause,
    make_operation_contract,
    tensor_ref_from_mapping,
    verify_cause_identity,
)
from .types import (
    BiasState,
    CandidateEffect,
    CauseKind,
    CausePacket,
    CommitDisposition,
    CommitReceipt,
    MemoryWriteIntent,
    ModelUpdateIntent,
    OntologyStatus,
    OperatingRegion,
    OperationContract,
    PhaseRecord,
    PublishedEffect,
    RepairFrame,
    RepairOutcome,
    StateUpdateIntent,
    TensorArtifactRef,
    TickPhase,
    VerifierReceipt,
)
from .verifier import IndependentVerifier, SemanticEvidence


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_INT64_MAX = (1 << 63) - 1

CandidateArtifactValidator = Callable[[CandidateEffect, StoredArtifact], bool]


NetworkBatchRejected = BatchRejected


def _authoritative_array(
    value: Any,
    *,
    label: str,
    boolean: bool,
) -> tuple[tuple[int, ...], list[int | bool]]:
    """Validate and flatten a nonempty rectangular no-float array."""

    def visit(item: Any, path: str) -> tuple[tuple[int, ...], list[int | bool]]:
        if isinstance(item, (tuple, list)):
            if not item:
                raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
            children = [visit(child, f"{path}[{index}]") for index, child in enumerate(item)]
            shape = children[0][0]
            if any(child_shape != shape for child_shape, _ in children[1:]):
                raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
            return (len(item), *shape), [
                leaf for _, leaves in children for leaf in leaves
            ]
        if boolean:
            if not isinstance(item, bool):
                raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
        elif (
            not isinstance(item, int)
            or isinstance(item, bool)
            or item < 0
            or item > _INT64_MAX
        ):
            raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
        return (), [item]

    shape, leaves = visit(value, label)
    return shape, leaves


def _reshape_authoritative(values: Sequence[Any], shape: Sequence[int]) -> Any:
    if not shape:
        if len(values) != 1:
            raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
        return values[0]
    if len(shape) == 1:
        return list(values)
    stride = 1
    for size in shape[1:]:
        stride *= size
    return [
        _reshape_authoritative(values[index : index + stride], shape[1:])
        for index in range(0, len(values), stride)
    ]


def _sum_authoritative(value: Any, *, label: str) -> int:
    _, leaves = _authoritative_array(value, label=label, boolean=False)
    return sum(int(item) for item in leaves)


def _reject_floats(value: Any) -> None:
    """Reject floating-point evidence at the sole-writer boundary."""

    if isinstance(value, float):
        raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) or not key for key in value):
            raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
        for item in value.values():
            _reject_floats(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _reject_floats(item)


def _recompute_compute_plan(
    *,
    route_inputs: Mapping[str, Any],
    bias: BiasState,
) -> tuple[dict[str, Any], tuple[int, ...]]:
    """Recompute the proposal's exact integer plan without neural floats."""

    native = route_inputs.get("native_compute")
    policy = route_inputs.get("compute_policy")
    if not isinstance(native, Mapping) or not isinstance(policy, Mapping):
        raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
    _reject_floats(native)
    _reject_floats(policy)
    native_expected_keys = {
        "contract_type",
        "schema_version",
        "drive_units",
        "resistance_units",
        "canonical_route_ids",
        "flow_scale_units",
    }
    policy_expected_keys = {
        "contract_type",
        "schema_version",
        "policy_id",
        "flow_units_per_quantum",
        "max_routes",
        "max_reasoning_steps",
        "max_branches",
        "max_memory_reads",
        "max_diagnostic_probes",
    }
    if set(native) != native_expected_keys or set(policy) != policy_expected_keys:
        raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
    route_ids = native.get("canonical_route_ids")
    if (
        native.get("contract_type") != "NATIVE_COMPUTE_INPUTS"
        or native.get("schema_version")
        != "cas.neural-cjt.native-compute-inputs/0.2"
        or not isinstance(route_ids, (tuple, list))
        or not route_ids
        or any(not isinstance(item, str) or not item for item in route_ids)
        or len(set(route_ids)) != len(route_ids)
    ):
        raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
    flow_scale = native.get("flow_scale_units")
    if (
        not isinstance(flow_scale, int)
        or isinstance(flow_scale, bool)
        or flow_scale <= 0
        or flow_scale > _INT64_MAX
    ):
        raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")

    ceiling = bias.governance.compute_ceiling_units
    expected_policy = {
        "contract_type": "NATIVE_COMPUTE_POLICY",
        "schema_version": "cas.neural-cjt.native-compute-policy/0.2",
        "policy_id": "cas.cjt.compute/0.2",
        "flow_units_per_quantum": 1_000_000,
        "max_routes": ceiling,
        "max_reasoning_steps": ceiling,
        "max_branches": min(4, ceiling),
        "max_memory_reads": min(4, ceiling),
        "max_diagnostic_probes": min(4, ceiling),
    }
    try:
        policy_matches = canonical_json(policy) == canonical_json(expected_policy)
    except (TypeError, ValueError):
        policy_matches = False
    if not policy_matches:
        raise BatchRejected("COMPUTE_POLICY_NOT_BOUND_TO_BIAS")

    drive_shape, drive = _authoritative_array(
        native["drive_units"], label="drive_units", boolean=False
    )
    resistance_shape, resistance = _authoritative_array(
        native["resistance_units"], label="resistance_units", boolean=False
    )
    if (
        not drive_shape
        or drive_shape != resistance_shape
        or drive_shape[-1] != len(route_ids)
    ):
        raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
    masks: dict[str, list[int | bool]] = {}
    for name in (
        "topology_mask",
        "permission_mask",
        "quarantine_mask",
        "budget_mask",
        "readiness_hard_mask",
    ):
        shape, leaves = _authoritative_array(
            route_inputs.get(name), label=name, boolean=True
        )
        if shape != drive_shape:
            raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
        masks[name] = leaves

    admitted = [
        bool(topology)
        and bool(permission)
        and not bool(quarantine)
        and bool(budget)
        and bool(readiness)
        for topology, permission, quarantine, budget, readiness in zip(
            masks["topology_mask"],
            masks["permission_mask"],
            masks["quarantine_mask"],
            masks["budget_mask"],
            masks["readiness_hard_mask"],
            strict=True,
        )
    ]
    raw: list[int] = []
    for drive_value, resistance_value, is_admitted in zip(
        drive, resistance, admitted, strict=True
    ):
        typed_drive = int(drive_value)
        typed_resistance = int(resistance_value)
        if not is_admitted or typed_drive == 0:
            raw.append(0)
            continue
        if typed_resistance <= 0:
            raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
        flow = (flow_scale * typed_drive) // typed_resistance
        if flow > _INT64_MAX:
            raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
        raw.append(flow)

    width = drive_shape[-1]
    total_values: list[int] = []
    route_values: list[int] = []
    scheduled_values: list[bool] = []
    quantum_values: list[int] = []
    for offset in range(0, len(raw), width):
        row = raw[offset : offset + width]
        total = sum(row)
        if total > _INT64_MAX:
            raise BatchRejected("NATIVE_COMPUTE_EVIDENCE_INVALID")
        total_quanta = (
            0
            if total == 0
            else (total + expected_policy["flow_units_per_quantum"] - 1)
            // expected_policy["flow_units_per_quantum"]
        )
        positive = sum(value > 0 for value in row)
        route_count = min(total_quanta, positive, expected_policy["max_routes"])
        order = sorted(
            range(width), key=lambda index: (-row[index], route_ids[index])
        )
        chosen = set(index for index in order if row[index] > 0)
        chosen = set([index for index in order if index in chosen][:route_count])
        total_values.append(total)
        quantum_values.append(total_quanta)
        route_values.append(route_count)
        scheduled_values.extend(index in chosen for index in range(width))

    prefix_shape = drive_shape[:-1]

    def bounded(name: str) -> list[int]:
        cap = int(expected_policy[name])
        return [min(value, cap) for value in quantum_values]

    expected_plan = {
        "contract_type": "PREDECLARED_COMPUTE_PLAN",
        "schema_version": "cas.neural-cjt.predeclared-compute-plan/0.2",
        "policy_id": expected_policy["policy_id"],
        "canonical_route_ids": list(route_ids),
        "source_raw_flow_units": _reshape_authoritative(raw, drive_shape),
        "source_total_flow_units": _reshape_authoritative(
            total_values, prefix_shape
        ),
        "scheduled_route_mask": _reshape_authoritative(
            scheduled_values, drive_shape
        ),
        "route_quanta": _reshape_authoritative(route_values, prefix_shape),
        "reasoning_step_quanta": _reshape_authoritative(
            bounded("max_reasoning_steps"), prefix_shape
        ),
        "branch_quanta": _reshape_authoritative(
            bounded("max_branches"), prefix_shape
        ),
        "memory_read_quanta": _reshape_authoritative(
            bounded("max_memory_reads"), prefix_shape
        ),
        "diagnostic_probe_quanta": _reshape_authoritative(
            bounded("max_diagnostic_probes"), prefix_shape
        ),
    }
    return expected_plan, prefix_shape


def _validate_realized_flow(
    *,
    route_outputs: Mapping[str, Any],
    expected_plan: Mapping[str, Any],
    compute_shape: tuple[int, ...],
) -> dict[str, list[int | bool]]:
    """Recompute all integer realized-flow relationships without floats."""

    raw_shape, _ = _authoritative_array(
        expected_plan["source_raw_flow_units"],
        label="source_raw_flow_units",
        boolean=False,
    )
    effective_shape, effective = _authoritative_array(
        route_outputs.get("effective_path_mask"),
        label="effective_path_mask",
        boolean=True,
    )
    current_shape, current = _authoritative_array(
        route_outputs.get("current_microunits"),
        label="current_microunits",
        boolean=False,
    )
    total_shape, totals = _authoritative_array(
        route_outputs.get("total_current_microunits"),
        label="total_current_microunits",
        boolean=False,
    )
    conducting_shape, conducting = _authoritative_array(
        route_outputs.get("conducting_query_mask"),
        label="conducting_query_mask",
        boolean=True,
    )
    allocation_shape, allocation = _authoritative_array(
        route_outputs.get("flow_allocation_ppm"),
        label="flow_allocation_ppm",
        boolean=False,
    )
    if (
        effective_shape != raw_shape
        or current_shape != raw_shape
        or allocation_shape != raw_shape
        or total_shape != compute_shape
        or conducting_shape != compute_shape
    ):
        raise BatchRejected("REALIZED_FLOW_EVIDENCE_INVALID")
    _, scheduled = _authoritative_array(
        expected_plan["scheduled_route_mask"],
        label="scheduled_route_mask",
        boolean=True,
    )
    if any(
        bool(is_effective) != (int(units) > 0)
        or (bool(is_effective) and not bool(is_scheduled))
        for is_effective, units, is_scheduled in zip(
            effective, current, scheduled, strict=True
        )
    ):
        raise BatchRejected("REALIZED_FLOW_SUPPORT_INVALID")

    width = raw_shape[-1]
    route_ids = tuple(expected_plan["canonical_route_ids"])
    expected_totals: list[int] = []
    expected_allocations: list[int] = []
    for offset in range(0, len(current), width):
        row = [int(item) for item in current[offset : offset + width]]
        total = sum(row)
        if total > _INT64_MAX:
            raise BatchRejected("REALIZED_FLOW_EVIDENCE_INVALID")
        expected_totals.append(total)
        try:
            expected_allocations.extend(
                largest_remainder_flow_ppm(row, route_ids)
            )
        except RoutingError as error:
            raise BatchRejected("REALIZED_FLOW_EVIDENCE_INVALID") from error
    if (
        [int(item) for item in totals] != expected_totals
        or [bool(item) for item in conducting]
        != [item > 0 for item in expected_totals]
        or [int(item) for item in allocation] != expected_allocations
    ):
        raise BatchRejected("REALIZED_FLOW_TELEMETRY_MISMATCH")
    return {
        "effective_path_mask": effective,
        "current_microunits": current,
        "total_current_microunits": totals,
        "conducting_query_mask": conducting,
        "flow_allocation_ppm": allocation,
    }


def _validate_route_settings(
    *,
    route_inputs: Mapping[str, Any],
    bias: BiasState,
) -> dict[str, Any]:
    """Bind authored route settings to native controls and hard masks."""

    settings = route_inputs.get("route_settings")
    keys = {
        "drive_units",
        "resistance_capability_units",
        "resistance_context_units",
        "resistance_resource_units",
        "resistance_memory_units",
        "unit_scale",
        "causal",
        "topology_open",
        "permission_open",
        "budget_open",
        "force_breakdown",
    }
    if not isinstance(settings, Mapping) or set(settings) != keys:
        raise BatchRejected("ROUTE_SETTINGS_INVALID")
    integer_names = (
        "drive_units",
        "resistance_capability_units",
        "resistance_context_units",
        "resistance_resource_units",
        "resistance_memory_units",
        "unit_scale",
    )
    boolean_names = (
        "causal",
        "topology_open",
        "permission_open",
        "budget_open",
        "force_breakdown",
    )
    if any(
        not isinstance(settings[name], int)
        or isinstance(settings[name], bool)
        or settings[name] < 0
        or settings[name] > _INT64_MAX
        for name in integer_names
    ) or any(not isinstance(settings[name], bool) for name in boolean_names):
        raise BatchRejected("ROUTE_SETTINGS_INVALID")
    if settings["unit_scale"] <= 0:
        raise BatchRejected("ROUTE_SETTINGS_INVALID")
    resistance = sum(int(settings[name]) for name in integer_names[1:5])
    if resistance > _INT64_MAX or (
        settings["drive_units"] > 0 and resistance <= 0
    ):
        raise BatchRejected("ROUTE_SETTINGS_INVALID")
    native = route_inputs["native_compute"]
    drive_shape, drive = _authoritative_array(
        native["drive_units"], label="drive_units", boolean=False
    )
    resistance_shape, resistance_values = _authoritative_array(
        native["resistance_units"], label="resistance_units", boolean=False
    )
    if (
        drive_shape != resistance_shape
        or any(int(item) != settings["drive_units"] for item in drive)
        or any(int(item) != resistance for item in resistance_values)
        or native["flow_scale_units"] != settings["unit_scale"]
    ):
        raise BatchRejected("ROUTE_SETTINGS_NATIVE_BINDING_INVALID")

    width = drive_shape[-1]
    query_count = drive_shape[-2] if len(drive_shape) >= 2 else 1
    _, topology = _authoritative_array(
        route_inputs["topology_mask"], label="topology_mask", boolean=True
    )
    expected_topology = [
        bool(settings["topology_open"])
        and (
            not settings["causal"]
            or index % width <= (index // width) % query_count
        )
        for index in range(len(topology))
    ]
    _, permission = _authoritative_array(
        route_inputs["permission_mask"], label="permission_mask", boolean=True
    )
    expected_permission = bool(
        settings["permission_open"]
        and "execute" in bias.governance.hard_permissions
        and not bias.governance.quarantined
    )
    _, quarantine = _authoritative_array(
        route_inputs["quarantine_mask"], label="quarantine_mask", boolean=True
    )
    _, budget = _authoritative_array(
        route_inputs["budget_mask"], label="budget_mask", boolean=True
    )
    expected_budget = bool(
        settings["budget_open"] and bias.governance.compute_ceiling_units > 0
    )
    if (
        [bool(item) for item in topology] != expected_topology
        or any(bool(item) is not expected_permission for item in permission)
        or any(
            bool(item) is not bias.governance.quarantined
            for item in quarantine
        )
        or any(bool(item) is not expected_budget for item in budget)
    ):
        raise BatchRejected("ROUTE_SETTINGS_HARD_MASK_BINDING_INVALID")
    return dict(settings)


def _digest_text(name: str, value: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase SHA-256")


def _checkpoint_entries(
    reference: TensorArtifactRef,
    artifact: StoredArtifact,
) -> dict[str, tuple[str, tuple[int, ...], bytes]]:
    """Decode only frozen checkpoint geometry and exact parameter bytes."""

    if not verify_checkpoint(reference, artifact):
        raise BatchRejected("CHECKPOINT_ARTIFACT_INVALID")
    result: dict[str, tuple[str, tuple[int, ...], bytes]] = {}
    for entry in artifact.metadata["entries"]:
        name = str(entry["name"])
        offset = int(entry["offset"])
        length = int(entry["byte_length"])
        result[name] = (
            str(entry["dtype"]),
            tuple(int(item) for item in entry["shape"]),
            artifact.payload[offset : offset + length],
        )
    return result


@dataclass(frozen=True, slots=True, kw_only=True)
class NetworkStateEnvelope:
    """A deterministic global state head containing at least three CJTs."""

    state_version: int
    previous_state_digest: str | None
    model_id: str
    model_version: int
    model_digest: str
    model_artifact_ref: TensorArtifactRef
    biases: tuple[BiasState, ...]
    state_digest: str

    CONTRACT_TYPE = "NETWORK_STATE_ENVELOPE"
    SCHEMA_VERSION = "cas.neural-cjt.network-state-envelope/0.2"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.state_version, int)
            or isinstance(self.state_version, bool)
            or self.state_version < 0
        ):
            raise ValueError("state_version must be a nonnegative integer")
        if self.state_version == 0 and self.previous_state_digest is not None:
            raise ValueError("initial network state cannot have a parent")
        if self.state_version > 0:
            if self.previous_state_digest is None:
                raise ValueError("versioned network state requires its parent digest")
            _digest_text("previous_state_digest", self.previous_state_digest)
        if not isinstance(self.model_id, str) or not self.model_id:
            raise ValueError("model_id must be a nonempty string")
        if (
            not isinstance(self.model_version, int)
            or isinstance(self.model_version, bool)
            or self.model_version < 0
        ):
            raise ValueError("model_version must be a nonnegative integer")
        _digest_text("model_digest", self.model_digest)
        if (
            not isinstance(self.model_artifact_ref, TensorArtifactRef)
            or self.model_artifact_ref.sha256 != self.model_digest
        ):
            raise ValueError("model_artifact_ref must bind the global model digest")
        _digest_text("state_digest", self.state_digest)
        biases = tuple(self.biases)
        if len(biases) < 3 or not all(isinstance(item, BiasState) for item in biases):
            raise ValueError("a network state requires at least three typed BiasState records")
        keys = [(item.bias_id, item.cjt_id) for item in biases]
        if (
            len({item.bias_id for item in biases}) != len(biases)
            or len({item.cjt_id for item in biases}) != len(biases)
        ):
            raise ValueError("network Bias IDs and CJT IDs must each be unique")
        if keys != sorted(keys):
            raise ValueError("network Bias records must be in canonical identity order")
        for bias in biases:
            if not verify_declared_digest(bias, "state_digest"):
                raise ValueError(f"Bias digest is invalid: {bias.bias_id}")
            if (
                bias.theta.model_id != self.model_id
                or bias.theta.model_version != self.model_version
                or bias.theta.model_digest != self.model_digest
                or self.model_artifact_ref not in bias.theta.parameter_artifacts
            ):
                raise ValueError(
                    f"Bias {bias.bias_id} is not bound to the global model head"
                )
        object.__setattr__(self, "biases", biases)

    @property
    def digest_valid(self) -> bool:
        return verify_declared_digest(self.to_dict(), "state_digest")

    @property
    def by_bias_id(self) -> dict[str, BiasState]:
        return {item.bias_id: item for item in self.biases}

    @property
    def by_cjt_id(self) -> dict[str, BiasState]:
        return {item.cjt_id: item for item in self.biases}

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.CONTRACT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "state_version": self.state_version,
            "previous_state_digest": self.previous_state_digest,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "model_digest": self.model_digest,
            "model_artifact_ref": self.model_artifact_ref.to_dict(),
            "biases": [item.to_dict() for item in self.biases],
            "state_digest": self.state_digest,
        }

    @classmethod
    def create(
        cls,
        biases: Sequence[BiasState],
        *,
        model_id: str,
        model_version: int,
        model_digest: str,
        model_artifact_ref: TensorArtifactRef,
    ) -> "NetworkStateEnvelope":
        ordered = tuple(sorted(biases, key=lambda item: (item.bias_id, item.cjt_id)))
        draft = cls(
            state_version=0,
            previous_state_digest=None,
            model_id=model_id,
            model_version=model_version,
            model_digest=model_digest,
            model_artifact_ref=model_artifact_ref,
            biases=ordered,
            state_digest="0" * 64,
        )
        return replace(
            draft,
            state_digest=canonical_digest(draft.to_dict(), omit_keys=("state_digest",)),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NetworkStateEnvelope":
        """Strictly rebuild a persisted envelope and every nested Bias."""

        if not isinstance(value, Mapping):
            raise ValueError("network state must be a mapping")
        expected = {
            "contract_type",
            "schema_version",
            "state_version",
            "previous_state_digest",
            "model_id",
            "model_version",
            "model_digest",
            "model_artifact_ref",
            "biases",
            "state_digest",
        }
        if set(value) != expected:
            raise ValueError("network state fields do not match the frozen schema")
        if (
            value.get("contract_type") != cls.CONTRACT_TYPE
            or value.get("schema_version") != cls.SCHEMA_VERSION
            or not isinstance(value.get("biases"), list)
        ):
            raise ValueError("network state contract type or schema is invalid")
        try:
            result = cls(
                state_version=value["state_version"],
                previous_state_digest=value["previous_state_digest"],
                model_id=value["model_id"],
                model_version=value["model_version"],
                model_digest=value["model_digest"],
                model_artifact_ref=tensor_ref_from_mapping(
                    value["model_artifact_ref"]
                ),
                biases=tuple(bias_from_dict(item) for item in value["biases"]),
                state_digest=value["state_digest"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("persisted network state is malformed") from error
        if not result.digest_valid:
            raise ValueError("persisted network state digest is invalid")
        return result

    def successor(
        self,
        *,
        biases: Sequence[BiasState] | None = None,
        model_version: int | None = None,
        model_digest: str | None = None,
        model_artifact_ref: TensorArtifactRef | None = None,
    ) -> "NetworkStateEnvelope":
        ordered = tuple(
            sorted(
                self.biases if biases is None else biases,
                key=lambda item: (item.bias_id, item.cjt_id),
            )
        )
        draft = NetworkStateEnvelope(
            state_version=self.state_version + 1,
            previous_state_digest=self.state_digest,
            model_id=self.model_id,
            model_version=self.model_version if model_version is None else model_version,
            model_digest=self.model_digest if model_digest is None else model_digest,
            model_artifact_ref=(
                self.model_artifact_ref
                if model_artifact_ref is None
                else model_artifact_ref
            ),
            biases=ordered,
            state_digest="0" * 64,
        )
        return replace(
            draft,
            state_digest=canonical_digest(draft.to_dict(), omit_keys=("state_digest",)),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class NetworkCommitBatch:
    """One proposed transition spanning every affected CJT and global model."""

    batch_id: str
    tick: int
    base_trace_digest: str | None
    state_before: NetworkStateEnvelope
    state_after: NetworkStateEnvelope
    cause: CausePacket
    candidate_effects: tuple[CandidateEffect, ...]
    verifier_receipts: tuple[VerifierReceipt, ...]
    state_intents: tuple[StateUpdateIntent, ...]
    model_intents: tuple[ModelUpdateIntent, ...]
    memory_intents: tuple[MemoryWriteIntent, ...]
    repair_frames: tuple[RepairFrame, ...]
    phase_records: tuple[PhaseRecord, ...]
    runtime_id: str
    software_digest: str
    cjt_ids: tuple[str, ...]
    artifacts: tuple[StoredArtifact, ...] = ()
    repair_outcomes: tuple[RepairOutcome, ...] = ()
    model_version: ModelVersionWrite | None = None
    qualification_receipts: tuple[Any, ...] = ()
    semantic_evidence: tuple[Any, ...] = ()
    decoder_contract: Any | None = None
    memory_read_refs: tuple[str, ...] = ()
    compute_plan: Mapping[str, Any] = field(default_factory=dict)
    compute_observations: Mapping[str, Any] = field(default_factory=dict)
    sensitive_trace_fields: tuple[str, ...] = ()
    effect_publication_capability: str = REQUEST_EFFECT_PUBLICATION
    audit_only: bool = False
    audit_reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NetworkRecoverySnapshot:
    head: ActiveHead
    state: dict[str, Any]
    traces: tuple[dict[str, Any], ...]


class NetworkAtomicCoordinator:
    """Validate a complete multi-CJT batch, then perform one SQLite CAS."""

    def __init__(
        self,
        store: SQLiteAtomicStore,
        *,
        coordinator_id: str,
        authority_contract_id: str,
        runtime_id: str,
        software_digest: str,
        num_attention_heads: int,
        model_manifest_context: Mapping[str, Any],
        operation_contracts: Mapping[str, OperationContract],
        decoder_contracts: Mapping[str, Any],
        permitted_topology_edges: Sequence[tuple[str, str]] = (),
        trusted_evidence_sources: Sequence[str] = (),
        candidate_validator: CandidateArtifactValidator | None = None,
        parameter_scope_prefixes: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        if not isinstance(store, SQLiteAtomicStore):
            raise TypeError("store must be SQLiteAtomicStore")
        if not coordinator_id or not authority_contract_id or not runtime_id:
            raise ValueError(
                "coordinator, authority contract, and runtime IDs must be nonempty"
            )
        _digest_text("software digest", software_digest)
        if (
            not isinstance(num_attention_heads, int)
            or isinstance(num_attention_heads, bool)
            or num_attention_heads < 1
        ):
            raise ValueError("num_attention_heads must be a positive integer")
        try:
            manifest_context = _wire(
                model_manifest_context,
                label="model manifest context",
            )
        except Exception as error:
            raise ValueError("model manifest context must be serializable") from error
        if (
            set(manifest_context) != {"network", "config", "decoder_labels"}
            or not isinstance(manifest_context["network"], Mapping)
            or not isinstance(manifest_context["config"], Mapping)
            or not isinstance(manifest_context["decoder_labels"], list)
            or not manifest_context["decoder_labels"]
            or any(
                not isinstance(item, str) or not item
                for item in manifest_context["decoder_labels"]
            )
        ):
            raise ValueError("model manifest context fields are not exact")
        contracts_by_id: dict[str, OperationContract] = {}
        contracts_by_operation: dict[str, OperationContract] = {}
        for key, contract in operation_contracts.items():
            if (
                not isinstance(key, str)
                or not key
                or not isinstance(contract, OperationContract)
                or key != contract.contract_id
                or not verify_declared_digest(contract, "contract_digest")
            ):
                raise ValueError("operation contracts must be intact and keyed by contract_id")
            try:
                frozen_contract = make_operation_contract(contract.operation_id)
            except Exception as error:
                raise ValueError(
                    "operation contract operation is not frozen in runtime 0.2"
                ) from error
            if contract != frozen_contract:
                raise ValueError(
                    "operation contract does not equal the frozen runtime 0.2 contract"
                )
            if contract.operation_id in contracts_by_operation:
                raise ValueError("operation contract operation IDs must be unique")
            admitted_verifier = IndependentVerifier(
                contract.verifier_id,
                verifier_version=contract.verifier_version,
            )
            if admitted_verifier.configuration_digest != contract.verifier_digest:
                raise ValueError("operation contract verifier configuration is not admitted")
            contracts_by_id[key] = contract
            contracts_by_operation[contract.operation_id] = contract
        if not contracts_by_id:
            raise ValueError("at least one operation contract is required")
        admitted_decoders: dict[str, dict[str, Any]] = {}
        for cjt_id, value in decoder_contracts.items():
            try:
                decoder = _wire(value, label="decoder contract")
            except Exception as error:
                raise ValueError("decoder contracts must be serializable") from error
            if (
                not isinstance(cjt_id, str)
                or not cjt_id
                or not verify_declared_digest(decoder, "decoder_digest")
                or decoder.get("operation_id") not in contracts_by_operation
                or canonical_json(decoder.get("labels"))
                != canonical_json(manifest_context["decoder_labels"])
            ):
                raise ValueError("decoder contracts must be intact and keyed by CJT ID")
            admitted_decoders[cjt_id] = decoder
        if not admitted_decoders:
            raise ValueError("at least one decoder contract is required")
        topology_edges: set[tuple[str, str]] = set()
        for edge in permitted_topology_edges:
            if (
                not isinstance(edge, (tuple, list))
                or len(edge) != 2
                or any(not isinstance(item, str) or not item for item in edge)
            ):
                raise ValueError("topology edges must contain two nonempty CJT IDs")
            pair = (edge[0], edge[1])
            if pair in topology_edges:
                raise ValueError("topology edges must be unique")
            if any(endpoint not in admitted_decoders for endpoint in pair):
                raise ValueError("topology edges must use admitted CJT IDs")
            topology_edges.add(pair)
        self.store = store
        self.coordinator_id = coordinator_id
        self.authority_contract_id = authority_contract_id
        self.runtime_id = runtime_id
        self.software_digest = software_digest
        self.num_attention_heads = num_attention_heads
        self.model_manifest_context = manifest_context
        self.learning_policy = LearningPolicy()
        self.learning_policy.validate()
        self.operation_contracts = contracts_by_id
        self.operation_contracts_by_operation = contracts_by_operation
        self.decoder_contracts = admitted_decoders
        self.permitted_topology_edges = frozenset(topology_edges)
        self.trusted_evidence_sources = frozenset(trusted_evidence_sources)
        self.candidate_validator = candidate_validator
        self.parameter_scope_prefixes = {
            key: tuple(value)
            for key, value in (
                {} if parameter_scope_prefixes is None else parameter_scope_prefixes
            ).items()
        }
        if any(not isinstance(item, str) or not item for item in self.trusted_evidence_sources):
            raise ValueError("trusted evidence sources must be nonempty strings")
        if any(
            not key
            or not values
            or any(not isinstance(item, str) or not item for item in values)
            for key, values in self.parameter_scope_prefixes.items()
        ):
            raise ValueError("parameter scope prefixes must contain nonempty strings")

    def _contract_for_bias(self, bias: BiasState) -> OperationContract:
        contract = self.operation_contracts_by_operation.get(
            bias.stable.registered_operation_id
        )
        if contract is None:
            raise BatchRejected("BIAS_OPERATION_CONTRACT_NOT_ADMITTED")
        return contract

    def _viable_repair_cjts(
        self,
        state: NetworkStateEnvelope,
        suspended_cjt_id: str,
    ) -> tuple[str, ...]:
        """Return distinct, durably eligible canonical ^6 round trips."""

        source = state.by_cjt_id.get(suspended_cjt_id)
        if source is None or "cascade" not in source.governance.topology_permissions:
            return ()
        zero_multiplier_regions = {
            OperatingRegion.BREAKDOWN,
            OperatingRegion.NON_OHMIC,
            OperatingRegion.UNSTABLE,
        }
        viable: list[str] = []
        for candidate in state.biases:
            contract = self.operation_contracts_by_operation.get(
                candidate.stable.registered_operation_id
            )
            if (
                contract is None
                or candidate.cjt_id == suspended_cjt_id
                or contract.operation_id != "^6"
                or contract.ontology_status is not OntologyStatus.CANONICAL_ADMITTED
                or CauseKind.RPM_SUBGOAL not in contract.accepted_cause_kinds
                or "PROPOSE_EFFECT" not in contract.legal_actions
                or (suspended_cjt_id, candidate.cjt_id)
                not in self.permitted_topology_edges
                or (candidate.cjt_id, suspended_cjt_id)
                not in self.permitted_topology_edges
                or "cascade" not in candidate.governance.topology_permissions
                or "execute" not in candidate.governance.hard_permissions
                or "publish_effect" not in candidate.governance.hard_permissions
                or self.coordinator_id
                not in candidate.governance.effect_publication_authorities
                or candidate.governance.quarantined
                or not candidate.rpm.readiness.hard_open
                or candidate.operating.region in zero_multiplier_regions
            ):
                continue
            viable.append(candidate.cjt_id)
        return tuple(sorted(viable))

    def _validate_repair_reservation(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
    ) -> None:
        """Reserve global t+1 repair execution and t+2 exact resumption."""

        open_ids = [
            repair_id
            for bias in before.biases
            for repair_id in bias.rpm.open_repair_ids
        ]
        if len(open_ids) > 1:
            raise BatchRejected("MULTIPLE_GLOBAL_OPEN_REPAIRS_FORBIDDEN")
        if not open_ids:
            return
        try:
            frame = repair_frame_from_dict(
                self.store.immutable_document("repair_frames", open_ids[0])
            )
            suspended = before.by_bias_id[frame.suspended_bias_id]
            route = next(
                item for item in batch.phase_records if item.phase is TickPhase.ROUTE
            )
            control_cjt_id = str(route.inputs["control_cjt_id"])
        except Exception as error:
            raise BatchRejected("OPEN_REPAIR_RESERVATION_NOT_RECONSTRUCTIBLE") from error
        if (
            frame.status.value != "OPEN"
            or suspended.rpm.open_repair_ids != (frame.repair_id,)
            or suspended.rpm.suspended_parent_cause_id != frame.parent_cause_id
            or suspended.rpm.return_addresses != (frame.return_address,)
        ):
            raise BatchRejected("OPEN_REPAIR_STATE_CROSS_LINK_INVALID")
        viable = self._viable_repair_cjts(before, suspended.cjt_id)
        if batch.tick == frame.eligible_tick:
            if (
                batch.cause.cause_kind is not CauseKind.RPM_SUBGOAL
                or batch.cause.cause_id != frame.subgoal_cause_id
                or batch.cause.content.get("repair_id") != frame.repair_id
                or control_cjt_id not in viable
                or batch.model_intents
                or batch.model_version is not None
                or batch.state_after.model_digest != before.model_digest
                or batch.state_after.model_version != before.model_version
                or batch.state_after.by_bias_id[frame.suspended_bias_id] != suspended
            ):
                raise BatchRejected("REPAIR_SUBGOAL_TICK_RESERVATION_VIOLATED")
            return
        if batch.tick != frame.eligible_tick + 1:
            raise BatchRejected("OPEN_REPAIR_RESERVED_STAGE_MISSED")

        traces = self.store.trace_events()
        latest = traces[-1] if traces else None
        results: list[tuple[dict[str, Any], dict[str, Any]]] = []
        if isinstance(latest, Mapping) and latest.get("tick") == frame.eligible_tick:
            for effect_id in latest.get("published_effect_ids", []):
                try:
                    effect = self.store.immutable_document(
                        "published_effects", str(effect_id)
                    )
                    candidate = self.store.immutable_document(
                        "candidate_effects", str(effect["candidate_effect_id"])
                    )
                except Exception as error:
                    raise BatchRejected(
                        "REPAIR_RESULT_NOT_RECONSTRUCTIBLE"
                    ) from error
                if (
                    candidate.get("parent_cause_id") == frame.subgoal_cause_id
                    and candidate.get("tick") == frame.eligible_tick
                ):
                    results.append((effect, candidate))
        if len(results) != 1:
            raise BatchRejected("REPAIR_RESULT_CARDINALITY_INVALID")
        result_effect, result_candidate = results[0]
        try:
            parent_cause = self.store.immutable_document(
                "causes", frame.parent_cause_id
            )
            rebuilt = cause_from_committed_effect(
                self.store,
                str(result_effect["published_effect_id"]),
                tick=batch.tick,
                candidate_operation_ids=tuple(parent_cause["candidate_operation_ids"]),
                goal_context=parent_cause["goal_context"],
            )
        except Exception as error:
            raise BatchRejected("REPAIR_RESUME_CAUSE_NOT_RECONSTRUCTIBLE") from error
        if (
            batch.cause.cause_kind is not CauseKind.EFFECT
            or batch.cause != rebuilt
            or control_cjt_id != suspended.cjt_id
            or result_candidate.get("producer_cjt_id") not in viable
            or len(batch.repair_outcomes) != 1
            or batch.repair_outcomes[0].repair_id != frame.repair_id
        ):
            raise BatchRejected("REPAIR_RESUME_TICK_RESERVATION_VIOLATED")

    def _eligible_biases(
        self,
        cause: CausePacket,
        before: NetworkStateEnvelope,
    ) -> tuple[BiasState, ...]:
        """Derive proposal eligibility from durable Biases and trusted topology."""

        requested = set(cause.candidate_operation_ids)
        eligible = [
            bias
            for bias in before.biases
            if bias.stable.registered_operation_id in requested
        ]
        if cause.originating_cjt_id is None:
            eligible = [
                bias
                for bias in eligible
                if "local" in bias.governance.topology_permissions
            ]
        else:
            source = before.by_cjt_id.get(cause.originating_cjt_id)
            if (
                source is None
                or "cascade" not in source.governance.topology_permissions
            ):
                return ()
            eligible = [
                bias
                for bias in eligible
                if (cause.originating_cjt_id, bias.cjt_id)
                in self.permitted_topology_edges
                and "cascade" in bias.governance.topology_permissions
            ]
        return tuple(sorted(eligible, key=lambda item: item.cjt_id))

    @staticmethod
    def _candidate_identity_valid(candidate: Mapping[str, Any]) -> bool:
        identity = {
            "tick": candidate.get("tick"),
            "parent_cause_id": candidate.get("parent_cause_id"),
            "producer_cjt_id": candidate.get("producer_cjt_id"),
            "operation_contract_digest": candidate.get(
                "operation_contract_digest"
            ),
            "bias_digest": candidate.get("bias_digest"),
            "model_digest": candidate.get("model_digest"),
            "content": candidate.get("content"),
            "content_ref": candidate.get("content_ref"),
        }
        try:
            return candidate.get("candidate_effect_id") == content_id(
                "candidate-effect", identity
            )
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _receipt_identity_valid(receipt: Mapping[str, Any]) -> bool:
        try:
            identity_digest = canonical_digest(
                {
                    "tick": receipt.get("tick"),
                    "verifier_id": receipt.get("verifier_id"),
                    "verifier_version": receipt.get("verifier_version"),
                    "verifier_digest": receipt.get("verifier_digest"),
                    "cause_id": receipt.get("cause_id"),
                    "candidate_effect_id": receipt.get("candidate_effect_id"),
                    "candidate_effect_digest": receipt.get(
                        "candidate_effect_digest"
                    ),
                    "bias_digest": receipt.get("bias_digest"),
                    "contract_digest": receipt.get(
                        "operation_contract_digest"
                    ),
                    "outcome": _text(receipt.get("semantic_outcome")),
                    "disposition": _text(receipt.get("disposition")),
                    "reason_codes": list(receipt.get("reason_codes", ())),
                    "evidence_refs": list(receipt.get("evidence_refs", ())),
                }
            )
        except (TypeError, ValueError):
            return False
        return receipt.get("receipt_id") == f"verifier-receipt-{identity_digest}"

    def _validate_cause_provenance(
        self,
        cause: CausePacket,
        before: NetworkStateEnvelope,
    ) -> None:
        """Rebuild every authority-bearing Cause from retained evidence."""

        if cause.cause_kind is CauseKind.EFFECT:
            if cause.parent_effect_id is None or cause.originating_cjt_id is None:
                raise BatchRejected("EFFECT_CAUSE_PROVENANCE_INVALID")
            try:
                rebuilt = cause_from_committed_effect(
                    self.store,
                    cause.parent_effect_id,
                    tick=cause.tick,
                    candidate_operation_ids=cause.candidate_operation_ids,
                    goal_context=cause.goal_context,
                )
            except Exception as error:
                raise BatchRejected("EFFECT_CAUSE_PROVENANCE_INVALID") from error
            if rebuilt != cause:
                raise BatchRejected("EFFECT_CAUSE_PROVENANCE_INVALID")
            return

        if cause.cause_kind is CauseKind.RPM_SUBGOAL:
            repair_id = cause.content.get("repair_id")
            if (
                not isinstance(repair_id, str)
                or not repair_id
                or cause.parent_effect_id is not None
                or cause.originating_cjt_id is None
            ):
                raise BatchRejected("RPM_SUBGOAL_PROVENANCE_INVALID")
            try:
                frame = repair_frame_from_dict(
                    self.store.immutable_document("repair_frames", repair_id)
                )
                candidate = self.store.immutable_document(
                    "candidate_effects", frame.rejected_candidate_effect_id
                )
                receipt = self.store.immutable_document(
                    "verifier_receipts", frame.verifier_receipt_id
                )
                suspended = before.by_bias_id[frame.suspended_bias_id]
            except Exception as error:
                raise BatchRejected("RPM_SUBGOAL_PROVENANCE_INVALID") from error
            if (
                frame.status.value != "OPEN"
                or frame.subgoal_cause_id != cause.cause_id
                or frame.eligible_tick != cause.tick
                or frame.repair_id not in suspended.rpm.open_repair_ids
                or frame.parent_cause_id
                != suspended.rpm.suspended_parent_cause_id
                or candidate.get("candidate_effect_id")
                != frame.rejected_candidate_effect_id
                or candidate.get("parent_cause_id") != frame.parent_cause_id
                or candidate.get("bias_id") != frame.suspended_bias_id
                or candidate.get("bias_version") != frame.suspended_bias_version
                or candidate.get("producer_cjt_id") != suspended.cjt_id
                or receipt.get("receipt_id") != frame.verifier_receipt_id
                or receipt.get("candidate_effect_id")
                != frame.rejected_candidate_effect_id
                or receipt.get("candidate_effect_digest")
                != candidate.get("candidate_digest")
                or receipt.get("cause_id") != frame.parent_cause_id
                or _text(receipt.get("disposition")) != "REPAIR"
                or receipt.get("repair_required") is not True
                or not verify_declared_digest(candidate, "candidate_digest")
                or not self._candidate_identity_valid(candidate)
                or not verify_declared_digest(receipt, "receipt_digest")
            ):
                raise BatchRejected("RPM_SUBGOAL_PROVENANCE_INVALID")
            ref_value = candidate.get("content_ref")
            try:
                reference = (
                    None
                    if ref_value is None
                    else tensor_ref_from_mapping(ref_value)
                )
                rebuilt = make_cause(
                    tick=frame.eligible_tick,
                    cause_kind=CauseKind.RPM_SUBGOAL,
                    content={
                        "repair_id": frame.repair_id,
                        "blocked_axis": frame.prerequisite_axis.value,
                        "parent_cause_id": frame.parent_cause_id,
                        "rejected_candidate_effect_id": (
                            frame.rejected_candidate_effect_id
                        ),
                        "reason_codes": list(receipt["reason_codes"]),
                    },
                    goal_context={
                        "kind": "PREREQUISITE_REPAIR",
                        "return_address": frame.return_address,
                    },
                    source="prototype:rpm-controller",
                    provenance=(
                        f"verifier-receipt:{frame.verifier_receipt_id}",
                        f"suspended-bias:{candidate['bias_digest']}",
                    ),
                    candidate_operation_ids=("^6",),
                    originating_cjt_id=str(candidate["producer_cjt_id"]),
                    content_ref=reference,
                )
            except Exception as error:
                raise BatchRejected("RPM_SUBGOAL_PROVENANCE_INVALID") from error
            if rebuilt != cause:
                raise BatchRejected("RPM_SUBGOAL_PROVENANCE_INVALID")
            return

        if cause.originating_cjt_id is not None or cause.parent_effect_id is not None:
            raise BatchRejected("CAUSE_PROVENANCE_FIELDS_NOT_ADMITTED")

    def _request_payload(self, batch: NetworkCommitBatch) -> dict[str, Any]:
        model = None
        if batch.model_version is not None:
            model = {
                "model_digest": batch.model_version.model_digest,
                "parent_model_digest": batch.model_version.parent_model_digest,
                "artifact_id": batch.model_version.artifact_id,
                "payload": _wire(batch.model_version.payload, label="model version"),
            }
        return {
            "batch_id": batch.batch_id,
            "tick": batch.tick,
            "base_trace_digest": batch.base_trace_digest,
            "state_before": batch.state_before.to_dict(),
            "state_after": batch.state_after.to_dict(),
            "cause": batch.cause.to_dict(),
            "candidate_effects": [item.to_dict() for item in batch.candidate_effects],
            "verifier_receipts": [item.to_dict() for item in batch.verifier_receipts],
            "state_intents": [item.to_dict() for item in batch.state_intents],
            "model_intents": [item.to_dict() for item in batch.model_intents],
            "memory_intents": [item.to_dict() for item in batch.memory_intents],
            "repair_frames": [item.to_dict() for item in batch.repair_frames],
            "repair_outcomes": [item.to_dict() for item in batch.repair_outcomes],
            "phase_records": [item.to_dict() for item in batch.phase_records],
            "runtime_id": batch.runtime_id,
            "software_digest": batch.software_digest,
            "cjt_ids": list(batch.cjt_ids),
            "artifacts": [item.public_descriptor() for item in batch.artifacts],
            "model_version": model,
            "qualification_receipts": [
                _wire(item, label="qualification receipt")
                for item in batch.qualification_receipts
            ],
            "semantic_evidence": [
                _wire(item, label="semantic evidence")
                for item in batch.semantic_evidence
            ],
            "decoder_contract": None
            if batch.decoder_contract is None
            else _wire(batch.decoder_contract, label="decoder contract"),
            "memory_read_refs": list(batch.memory_read_refs),
            "compute_plan": dict(batch.compute_plan),
            "compute_observations": dict(batch.compute_observations),
            "sensitive_trace_fields": list(batch.sensitive_trace_fields),
            "effect_publication_capability": batch.effect_publication_capability,
            "audit_only": batch.audit_only,
            "audit_reason_codes": list(batch.audit_reason_codes),
        }

    def _request_digest(self, batch: NetworkCommitBatch) -> str:
        return canonical_digest(self._request_payload(batch))

    def _idempotent(
        self, batch_id: str, request_digest: str
    ) -> CommitReceipt | None:
        retained = self.store.batch_record(batch_id)
        if retained is None:
            return None
        retained_digest, payload = retained
        if not hmac.compare_digest(retained_digest, request_digest):
            raise IdempotencyConflict("batch_id was already used for a different request")
        return CommitReceipt(**_receipt_kwargs(payload))

    def _common(
        self, batch: NetworkCommitBatch
    ) -> tuple[NetworkStateEnvelope, NetworkStateEnvelope, ActiveHead]:
        if not isinstance(batch, NetworkCommitBatch):
            raise BatchRejected("NETWORK_BATCH_TYPE_INVALID")
        if not isinstance(batch.batch_id, str) or not batch.batch_id:
            raise BatchRejected("BATCH_ID_INVALID")
        if (
            not isinstance(batch.tick, int)
            or isinstance(batch.tick, bool)
            or batch.tick < 0
        ):
            raise BatchRejected("TICK_INVALID")
        durable_traces = self.store.trace_events()
        expected_tick = 1 if not durable_traces else int(durable_traces[-1]["tick"]) + 1
        if batch.tick != expected_tick:
            raise BatchRejected("GLOBAL_TICK_SEQUENCE_INVALID")
        before, after = batch.state_before, batch.state_after
        if not isinstance(before, NetworkStateEnvelope) or not before.digest_valid:
            raise BatchRejected("NETWORK_BEFORE_DIGEST_INVALID")
        if not isinstance(after, NetworkStateEnvelope) or not after.digest_valid:
            raise BatchRejected("NETWORK_AFTER_DIGEST_INVALID")
        head = self.store.head
        if (
            head.state_digest != before.state_digest
            or head.state_version != before.state_version
            or head.trace_digest != batch.base_trace_digest
            or head.model_digest != before.model_digest
        ):
            raise StaleHeadError("network batch is stale relative to the active head")
        if self.store.load_state() != before.to_dict():
            raise BatchRejected("NETWORK_BEFORE_NOT_DURABLE_HEAD")
        if (
            after.state_version != before.state_version + 1
            or after.previous_state_digest != before.state_digest
            or after.model_id != before.model_id
        ):
            raise BatchRejected("NETWORK_SUCCESSOR_BINDING_INVALID")
        if set(before.by_bias_id) != set(after.by_bias_id):
            raise BatchRejected("NETWORK_BIAS_SET_CHANGED")
        if not isinstance(batch.cause, CausePacket) or batch.cause.tick != batch.tick:
            raise BatchRejected("CAUSE_BINDING_INVALID")
        if not verify_cause_identity(batch.cause):
            raise BatchRejected("CAUSE_IDENTITY_INVALID")
        self._validate_cause_provenance(batch.cause, before)
        if (
            batch.runtime_id != self.runtime_id
            or batch.software_digest != self.software_digest
        ):
            raise BatchRejected("RUNTIME_IDENTITY_NOT_ADMITTED")
        for bias in before.biases:
            self._contract_for_bias(bias)
            for candidate_id in bias.memory.recent_candidate_effect_ids:
                try:
                    retained_candidate = self.store.immutable_document(
                        "candidate_effects", candidate_id
                    )
                except PersistenceError as error:
                    raise BatchRejected(
                        "BIAS_CANDIDATE_HISTORY_NOT_RETAINED"
                    ) from error
                if (
                    retained_candidate.get("candidate_effect_id") != candidate_id
                    or not verify_declared_digest(
                        retained_candidate, "candidate_digest"
                    )
                    or not self._candidate_identity_valid(retained_candidate)
                ):
                    raise BatchRejected("BIAS_CANDIDATE_HISTORY_INVALID")
            if len(bias.rpm.open_repair_ids) > 1:
                raise BatchRejected("MULTIPLE_OPEN_REPAIRS_FORBIDDEN")
            if bias.rpm.open_repair_ids:
                try:
                    frame = repair_frame_from_dict(
                        self.store.immutable_document(
                            "repair_frames", bias.rpm.open_repair_ids[0]
                        )
                    )
                except Exception as error:
                    raise BatchRejected("OPEN_REPAIR_STATE_NOT_RECONSTRUCTIBLE") from error
                if (
                    frame.status.value != "OPEN"
                    or frame.suspended_bias_id != bias.bias_id
                    or frame.parent_cause_id
                    != bias.rpm.suspended_parent_cause_id
                    or bias.rpm.return_addresses != (frame.return_address,)
                ):
                    raise BatchRejected("OPEN_REPAIR_STATE_CROSS_LINK_INVALID")
            elif (
                bias.rpm.suspended_parent_cause_id is not None
                or bias.rpm.return_addresses
            ):
                raise BatchRejected("CLOSED_REPAIR_STATE_NOT_CLEARED")
        expected_cjts = tuple(item.cjt_id for item in before.biases)
        if tuple(batch.cjt_ids) != expected_cjts:
            raise BatchRejected("NETWORK_CJT_SET_INVALID")
        if any(
            not isinstance(item, PhaseRecord) or item.tick != batch.tick
            for item in batch.phase_records
        ):
            raise BatchRejected("PHASE_RECORD_INVALID")
        try:
            validate_phase_contract(
                batch.phase_records,
                cause_id=batch.cause.cause_id,
                pre_state_digest=before.state_digest,
                pre_model_digest=before.model_digest,
            )
        except PhaseContractError as error:
            raise BatchRejected("PHASE_CONTRACT_INVALID") from error
        self._validate_repair_reservation(batch, before)
        self._validate_phase_bindings(batch, before, after)
        if not isinstance(batch.audit_only, bool):
            raise BatchRejected("AUDIT_MODE_INVALID")
        if batch.cause.cause_kind is CauseKind.RPM_SUBGOAL:
            dispositions = tuple(
                _text(item.disposition) for item in batch.verifier_receipts
            )
            if (
                batch.audit_only
                or len(batch.candidate_effects) != 1
                or len(batch.verifier_receipts) != 1
                or dispositions != ("ACCEPT",)
                or _text(batch.verifier_receipts[0].semantic_outcome)
                != "INTENDED"
                or batch.verifier_receipts[0].repair_required
            ):
                raise BatchRejected("RPM_SUBGOAL_MUST_ACCEPT_BEFORE_TICK_ADVANCE")
        if batch.audit_only:
            # These are known fail-closed verifier outcomes.  They may advance
            # only the audit/trace envelope; they never authorize a Bias,
            # model, memory, repair, or Effect write.
            allowed = {
                "ZERO_FLOW",
                "NOT_READY",
                "UNASSESSED",
                "BREAKDOWN_REGION",
                "BIAS_QUARANTINED",
                "SEMANTIC_EVIDENCE_MISSING",
                "EXPERIMENTAL_OPERATION_NOT_AUTHORITY_ADMITTED",
            }
            if (
                not batch.audit_reason_codes
                or not set(batch.audit_reason_codes).issubset(allowed)
                or after.model_digest != before.model_digest
                or after.model_version != before.model_version
            ):
                raise BatchRejected("AUDIT_TRANSITION_INVALID")
        for bias_id, old in before.by_bias_id.items():
            new = after.by_bias_id[bias_id]
            if len(new.rpm.open_repair_ids) > 1:
                raise BatchRejected("MULTIPLE_OPEN_REPAIRS_FORBIDDEN")
            if not new.rpm.open_repair_ids and (
                new.rpm.suspended_parent_cause_id is not None
                or new.rpm.return_addresses
            ):
                raise BatchRejected("CLOSED_REPAIR_STATE_NOT_CLEARED")
            if old.cjt_id != new.cjt_id:
                raise BatchRejected("CJT_IDENTITY_CHANGED")
            if old.stable != new.stable:
                raise BatchRejected("STABLE_SUBSTRATE_IS_IMMUTABLE")
            if old.governance != new.governance:
                raise BatchRejected("GOVERNANCE_IS_NOT_SELF_WRITABLE")
            if new == old:
                continue
            if (
                new.version != old.version + 1
                or new.previous_digest != old.state_digest
                or not verify_declared_digest(new, "state_digest")
            ):
                raise BatchRejected("BIAS_SUCCESSOR_BINDING_INVALID")
        if (
            sum(len(item.rpm.open_repair_ids) for item in before.biases) > 1
            or sum(len(item.rpm.open_repair_ids) for item in after.biases) > 1
        ):
            raise BatchRejected("MULTIPLE_GLOBAL_OPEN_REPAIRS_FORBIDDEN")
        return before, after, head

    def _durable_memory_projection(
        self, record_id: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load one exact durable record and its candidate-only projection."""

        required = {
            "schema_version",
            "memory_record_id",
            "memory_kind",
            "content",
            "content_ref",
            "confidence_ppm",
            "provenance",
            "evidence_refs",
            "source_intent_id",
            "verifier_receipt_id",
            "committed_by",
            "record_digest",
        }
        try:
            record = self.store.immutable_document("memory_records", record_id)
        except PersistenceError as error:
            raise BatchRejected("MEMORY_RECORD_NOT_RETAINED") from error
        if (
            set(record) != required
            or record.get("schema_version")
            != "cas.neural-cjt.memory-record/0.2"
            or record.get("memory_record_id") != record_id
            or not verify_declared_digest(record, "record_digest")
        ):
            raise BatchRejected("MEMORY_RECORD_IDENTITY_INVALID")
        projection = {
            "memory_record_id": record_id,
            "memory_kind": record["memory_kind"],
            "content": record["content"],
            "content_ref": record["content_ref"],
            "confidence_ppm": record["confidence_ppm"],
            "provenance": record["provenance"],
            "candidate_only": True,
        }
        return record, projection

    def _validate_phase_bindings(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
        after: NetworkStateEnvelope,
    ) -> None:
        """Bind the phase evidence to this exact network proposal."""

        phases = {record.phase: record for record in batch.phase_records}

        def equal(left: Any, right: Any) -> bool:
            try:
                return canonical_json(left) == canonical_json(right)
            except (TypeError, ValueError):
                return False

        def string_set(value: Any) -> set[str] | None:
            if not isinstance(value, (tuple, list)) or any(
                not isinstance(item, str) or not item for item in value
            ):
                return None
            return set(value)

        read = phases[TickPhase.READ]
        expected_bias_ids = [item.bias_id for item in before.biases]
        expected_bias_digests = [item.state_digest for item in before.biases]
        if (
            not equal(read.outputs["bias_ids"], expected_bias_ids)
            or not equal(read.outputs["bias_digests"], expected_bias_digests)
            or not equal(read.outputs["memory_read_refs"], batch.memory_read_refs)
        ):
            raise BatchRejected("READ_PHASE_NETWORK_BINDING_INVALID")

        candidate = phases[TickPhase.CANDIDATE]
        eligible_biases = self._eligible_biases(batch.cause, before)
        eligible_cjt_ids = tuple(item.cjt_id for item in eligible_biases)
        eligible_contract_ids = tuple(
            self._contract_for_bias(item).contract_id for item in eligible_biases
        )
        actual_candidate_cjts = {item.producer_cjt_id for item in batch.candidate_effects}
        actual_contract_ids = {
            item.operation_contract_id for item in batch.candidate_effects
        }
        if (
            not equal(
                candidate.inputs["candidate_operation_ids"],
                batch.cause.candidate_operation_ids,
            )
            or not equal(candidate.outputs["candidate_cjt_ids"], eligible_cjt_ids)
            or not equal(
                candidate.outputs["operation_contract_ids"],
                eligible_contract_ids,
            )
            or not actual_candidate_cjts.issubset(set(eligible_cjt_ids))
            or not actual_contract_ids.issubset(set(eligible_contract_ids))
            or (batch.candidate_effects and not eligible_cjt_ids)
        ):
            raise BatchRejected("CANDIDATE_PHASE_BINDING_INVALID")

        route = phases[TickPhase.ROUTE]
        control_cjt_id = route.inputs["control_cjt_id"]
        if (
            not isinstance(control_cjt_id, str)
            or control_cjt_id not in set(eligible_cjt_ids)
        ):
            raise BatchRejected("ROUTE_CONTROL_CJT_INVALID")
        control_bias = before.by_cjt_id[control_cjt_id]
        if batch.candidate_effects and any(
            item.producer_cjt_id != control_cjt_id
            for item in batch.candidate_effects
        ):
            raise BatchRejected("ROUTE_CONTROL_CJT_BINDING_INVALID")

        readiness = phases[TickPhase.READINESS]
        expected_readiness = control_bias.rpm.readiness
        if (
            not equal(
                readiness.inputs["profile_ids"],
                [expected_readiness.profile_id],
            )
            or not equal(readiness.outputs["desire"], expected_readiness.desire.to_dict())
            or not equal(readiness.outputs["wisdom"], expected_readiness.wisdom.to_dict())
            or not equal(readiness.outputs["power"], expected_readiness.power.to_dict())
            or readiness.outputs["hard_open"] is not expected_readiness.hard_open
        ):
            raise BatchRejected("READINESS_PHASE_NETWORK_BINDING_INVALID")

        if (
            not equal(route.outputs["compute_plan"], batch.compute_plan)
            or route.outputs["effective_path_mask"] is None
            or route.outputs["conducting_query_mask"] is None
            or route.outputs["current_microunits"] is None
            or route.outputs["total_current_microunits"] is None
            or route.outputs["flow_allocation_ppm"] is None
        ):
            raise BatchRejected("ROUTE_PHASE_BINDING_INVALID")
        _reject_floats(route.inputs)
        _reject_floats(route.outputs)
        route_settings = _validate_route_settings(
            route_inputs=route.inputs,
            bias=control_bias,
        )
        expected_plan, compute_shape = _recompute_compute_plan(
            route_inputs=route.inputs,
            bias=control_bias,
        )
        try:
            plan_matches = canonical_json(batch.compute_plan) == canonical_json(
                expected_plan
            )
        except (TypeError, ValueError):
            plan_matches = False
        if not plan_matches:
            raise BatchRejected("COMPUTE_PLAN_NOT_REPRODUCIBLE")
        realized = _validate_realized_flow(
            route_outputs=route.outputs,
            expected_plan=expected_plan,
            compute_shape=compute_shape,
        )
        if route_settings["force_breakdown"] and any(
            bool(item) for item in realized["conducting_query_mask"]
        ):
            raise BatchRejected("BREAKDOWN_REALIZED_FLOW_FORBIDDEN")
        binding_manifest = route.inputs.get("control_binding_manifest")
        manifest_keys = {
            "schema_version",
            "cause_id",
            "cause_artifact_id",
            "cause_artifact_digest",
            "bias_id",
            "bias_version",
            "bias_digest",
            "recurrent_bias_artifact_id",
            "recurrent_bias_digest",
            "model_digest",
            "declared_beta_microunits",
            "live_beta_by_head_microunits",
            "readiness_profile_id",
            "operating_region",
            "governance_permissions",
            "route_settings",
            "native_compute",
            "compute_policy",
            "hard_masks",
            "compute_plan",
            "memory_read_requests",
            "memory_reads",
        }
        cause_ref = batch.cause.content_ref
        recurrent_ref = control_bias.memory.recurrent_state_ref
        if not isinstance(binding_manifest, Mapping) or set(binding_manifest) != manifest_keys:
            raise BatchRejected("CONTROL_BINDING_MANIFEST_INVALID")
        live_beta = binding_manifest.get("live_beta_by_head_microunits")
        memory_reads = binding_manifest.get("memory_reads")
        try:
            expected_memory_reads = [
                self._durable_memory_projection(str(record_id))[1]
                for record_id in batch.memory_read_refs
            ]
            binding_matches = all(
                (
                    binding_manifest["schema_version"]
                    == "cas.neural-cjt.control-binding/0.2",
                    binding_manifest["cause_id"] == batch.cause.cause_id,
                    binding_manifest["cause_artifact_id"]
                    == (None if cause_ref is None else cause_ref.artifact_id),
                    binding_manifest["cause_artifact_digest"]
                    == (None if cause_ref is None else cause_ref.sha256),
                    binding_manifest["bias_id"] == control_bias.bias_id,
                    binding_manifest["bias_version"] == control_bias.version,
                    binding_manifest["bias_digest"] == control_bias.state_digest,
                    binding_manifest["recurrent_bias_artifact_id"]
                    == (
                        None
                        if recurrent_ref is None
                        else recurrent_ref.artifact_id
                    ),
                    binding_manifest["recurrent_bias_digest"]
                    == (None if recurrent_ref is None else recurrent_ref.sha256),
                    binding_manifest["model_digest"] == before.model_digest,
                    binding_manifest["declared_beta_microunits"]
                    == control_bias.theta.beta_microunits,
                    isinstance(live_beta, (tuple, list)),
                    len(live_beta) == self.num_attention_heads,
                    all(
                        item == control_bias.theta.beta_microunits
                        for item in live_beta
                    ),
                    binding_manifest["readiness_profile_id"]
                    == control_bias.rpm.readiness.profile_id,
                    binding_manifest["operating_region"]
                    == control_bias.operating.region.value,
                    canonical_json(binding_manifest["governance_permissions"])
                    == canonical_json(control_bias.governance.hard_permissions),
                    canonical_json(binding_manifest["route_settings"])
                    == canonical_json(route_settings),
                    canonical_json(binding_manifest["native_compute"])
                    == canonical_json(route.inputs["native_compute"]),
                    canonical_json(binding_manifest["compute_policy"])
                    == canonical_json(route.inputs["compute_policy"]),
                    canonical_json(binding_manifest["hard_masks"])
                    == canonical_json(
                        {
                            name: route.inputs[name]
                            for name in (
                                "topology_mask",
                                "permission_mask",
                                "quarantine_mask",
                                "budget_mask",
                                "readiness_hard_mask",
                            )
                        }
                    ),
                    canonical_json(binding_manifest["compute_plan"])
                    == canonical_json(expected_plan),
                    canonical_json(binding_manifest["memory_read_requests"])
                    == canonical_json(batch.cause.memory_refs),
                    canonical_json(memory_reads)
                    == canonical_json(expected_memory_reads),
                )
            )
        except (KeyError, TypeError, ValueError):
            binding_matches = False
        if not binding_matches:
            raise BatchRejected("CONTROL_BINDING_MANIFEST_INVALID")
        observe_diagnostics = phases[TickPhase.OBSERVE].diagnostics
        expected_diagnostic_keys = {
            "control_binding_digest",
            "declared_beta_microunits",
            "live_beta_by_head_microunits",
        }
        if (
            set(observe_diagnostics) != expected_diagnostic_keys
            or observe_diagnostics["control_binding_digest"]
            != canonical_digest(binding_manifest)
            or observe_diagnostics["declared_beta_microunits"]
            != control_bias.theta.beta_microunits
            or canonical_json(
                observe_diagnostics["live_beta_by_head_microunits"]
            )
            != canonical_json(live_beta)
        ):
            raise BatchRejected("OBSERVE_CONTROL_DIAGNOSTICS_INVALID")
        expected_control_binding = (
            f"control-binding:{observe_diagnostics['control_binding_digest']}"
        )
        for candidate_effect in batch.candidate_effects:
            control_bindings = [
                item
                for item in candidate_effect.provenance
                if item.startswith("control-binding:")
            ]
            if control_bindings != [expected_control_binding]:
                raise BatchRejected("CANDIDATE_CONTROL_BINDING_INVALID")
        _, readiness_mask = _authoritative_array(
            route.inputs["readiness_hard_mask"],
            label="readiness_hard_mask",
            boolean=True,
        )
        if any(bool(item) is not expected_readiness.hard_open for item in readiness_mask):
            raise BatchRejected("READINESS_ROUTE_MASK_INVALID")
        _, permission_mask = _authoritative_array(
            route.inputs["permission_mask"],
            label="permission_mask",
            boolean=True,
        )
        _, quarantine_mask = _authoritative_array(
            route.inputs["quarantine_mask"],
            label="quarantine_mask",
            boolean=True,
        )
        _, budget_mask = _authoritative_array(
            route.inputs["budget_mask"],
            label="budget_mask",
            boolean=True,
        )
        if any(permission_mask) and (
            "execute" not in control_bias.governance.hard_permissions
            or control_bias.governance.quarantined
        ):
            raise BatchRejected("EXECUTE_PERMISSION_MASK_INVALID")
        if any(
            bool(item) is not control_bias.governance.quarantined
            for item in quarantine_mask
        ):
            raise BatchRejected("QUARANTINE_ROUTE_MASK_INVALID")
        if any(budget_mask) and control_bias.governance.compute_ceiling_units <= 0:
            raise BatchRejected("BUDGET_ROUTE_MASK_INVALID")

        execute = phases[TickPhase.EXECUTE]
        scheduled = string_set(execute.inputs["scheduled_cjt_ids"])
        executed = string_set(execute.outputs["executed_cjt_ids"])
        operation_ids = string_set(execute.inputs["operation_ids"])
        used = execute.outputs["compute_units_used"]
        expected_operations = (control_bias.stable.registered_operation_id,)
        any_conducting = any(
            bool(item) for item in realized["conducting_query_mask"]
        )
        expected_execution = {control_cjt_id} if any_conducting else set()
        if (
            scheduled is None
            or executed is None
            or operation_ids is None
            or len(scheduled) != len(execute.inputs["scheduled_cjt_ids"])
            or len(executed) != len(execute.outputs["executed_cjt_ids"])
            or not equal(execute.inputs["operation_ids"], expected_operations)
            or scheduled != expected_execution
            or executed != expected_execution
            or not scheduled.issubset(set(eligible_cjt_ids))
            or not executed.issubset(set(eligible_cjt_ids))
            or not executed.issubset(scheduled)
            or not {item.operation_id for item in batch.candidate_effects}.issubset(
                operation_ids
            )
            or not isinstance(used, int)
            or isinstance(used, bool)
            or used < 0
            or execute.compute_units != used
        ):
            raise BatchRejected("EXECUTE_PHASE_BINDING_INVALID")
        if (
            "execute" not in control_bias.governance.hard_permissions
            or control_bias.governance.quarantined
        ) and (scheduled or executed):
            raise BatchRejected("EXECUTE_NOT_PERMITTED")

        observe = phases[TickPhase.OBSERVE]
        observed_ids = [item.candidate_effect_id for item in batch.candidate_effects]
        artifact_ids = [
            item.content_ref.artifact_id
            for item in batch.candidate_effects
            if item.content_ref is not None
        ]
        if (
            not equal(observe.inputs["executed_cjt_ids"], execute.outputs["executed_cjt_ids"])
            or not equal(observe.outputs["candidate_effect_ids"], observed_ids)
            or not equal(observe.outputs["artifact_ids"], artifact_ids)
            or not isinstance(observe.outputs["operating_regions"], (tuple, list))
            or len(observe.outputs["operating_regions"]) != len(observed_ids)
            or not equal(
                observe.outputs["compute_observations"],
                batch.compute_observations,
            )
        ):
            raise BatchRejected("OBSERVE_PHASE_BINDING_INVALID")
        if len(set(observed_ids)) != len(observed_ids):
            raise BatchRejected("OBSERVE_CANDIDATE_ID_DUPLICATE")
        try:
            region_by_candidate = {
                candidate_id: OperatingRegion(region)
                for candidate_id, region in zip(
                    observed_ids,
                    observe.outputs["operating_regions"],
                    strict=True,
                )
            }
        except (TypeError, ValueError) as error:
            raise BatchRejected("OPERATING_REGION_INVALID") from error
        observations = batch.compute_observations
        if not isinstance(observations, Mapping):
            raise BatchRejected("COMPUTE_OBSERVATION_INVALID")
        _reject_floats(observations)
        observation_to_ceiling = {
            "routes_executed": "route_quanta",
            "reasoning_steps_used": "reasoning_step_quanta",
            "branches_opened": "branch_quanta",
            "memory_reads_used": "memory_read_quanta",
            "diagnostic_probes_used": "diagnostic_probe_quanta",
        }
        if set(observations) != set(observation_to_ceiling):
            raise BatchRejected("COMPUTE_OBSERVATION_INVALID")
        flattened_observations: dict[str, list[int | bool]] = {}
        flattened_ceilings: dict[str, list[int | bool]] = {}
        for observation_name, ceiling_name in observation_to_ceiling.items():
            observation_shape, observation_values = _authoritative_array(
                observations[observation_name],
                label=observation_name,
                boolean=False,
            )
            ceiling_shape, ceiling_values = _authoritative_array(
                expected_plan[ceiling_name], label=ceiling_name, boolean=False
            )
            if observation_shape != compute_shape or ceiling_shape != compute_shape:
                raise BatchRejected("COMPUTE_OBSERVATION_INVALID")
            if any(
                int(observed) > int(ceiling)
                for observed, ceiling in zip(
                    observation_values, ceiling_values, strict=True
                )
            ):
                raise BatchRejected("COMPUTE_CEILING_EXCEEDED")
            flattened_observations[observation_name] = observation_values
            flattened_ceilings[ceiling_name] = ceiling_values
        width = len(expected_plan["canonical_route_ids"])
        effective = [bool(item) for item in realized["effective_path_mask"]]
        conducting = [
            bool(item) for item in realized["conducting_query_mask"]
        ]
        expected_routes = [
            sum(effective[offset : offset + width])
            for offset in range(0, len(effective), width)
        ]
        expected_reasoning = [1 if item else 0 for item in conducting]
        try:
            expected_memory_usage = list(
                allocate_global_charge(
                    [
                        int(item)
                        for item in flattened_ceilings["memory_read_quanta"]
                    ],
                    conducting,
                    len(batch.memory_read_refs),
                )
            )
            expected_branch_usage = list(
                allocate_global_charge(
                    [int(item) for item in flattened_ceilings["branch_quanta"]],
                    conducting,
                    len(batch.repair_frames),
                )
            )
        except RoutingError as error:
            raise BatchRejected("GLOBAL_COMPUTE_CHARGE_INVALID") from error
        exact_observations = {
            "routes_executed": expected_routes,
            "reasoning_steps_used": expected_reasoning,
            "branches_opened": expected_branch_usage,
            "memory_reads_used": expected_memory_usage,
            "diagnostic_probes_used": [0 for _ in conducting],
        }
        if any(
            [int(item) for item in flattened_observations[name]] != expected
            for name, expected in exact_observations.items()
        ):
            raise BatchRejected("COMPUTE_OBSERVATION_NOT_EXACT")
        reasoning_used = sum(
            int(item) for item in flattened_observations["reasoning_steps_used"]
        )
        if used != reasoning_used:
            raise BatchRejected("EXECUTE_COMPUTE_OBSERVATION_MISMATCH")
        regions = tuple(
            OperatingRegion(item).value
            for item in observe.outputs["operating_regions"]
        )
        for candidate_effect in batch.candidate_effects:
            region = region_by_candidate[candidate_effect.candidate_effect_id].value
            if (
                region in {"ACTIVE", "SATURATION"}
                and candidate_effect.producer_cjt_id not in executed
            ):
                raise BatchRejected("CONDUCTING_CANDIDATE_NOT_EXECUTED")
        if not any_conducting and (
            scheduled
            or executed
            or batch.memory_read_refs
            or any(
                int(item)
                for values in flattened_observations.values()
                for item in values
            )
        ):
            raise BatchRejected("ZERO_REALIZED_FLOW_USAGE_FORBIDDEN")

        verify = phases[TickPhase.VERIFY]
        evidence_ids = [
            _wire(item, label="semantic evidence")["evidence_id"]
            for item in batch.semantic_evidence
        ]
        if (
            not equal(verify.inputs["candidate_effect_ids"], observed_ids)
            or not equal(verify.inputs["evidence_ids"], evidence_ids)
            or not equal(
                verify.outputs["verifier_receipt_ids"],
                [item.receipt_id for item in batch.verifier_receipts],
            )
            or not equal(
                verify.outputs["semantic_outcomes"],
                [_text(item.semantic_outcome) for item in batch.verifier_receipts],
            )
            or not equal(
                verify.outputs["dispositions"],
                [_text(item.disposition) for item in batch.verifier_receipts],
            )
        ):
            raise BatchRejected("VERIFY_PHASE_BINDING_INVALID")

        # The operating region is part of the authoritative transition, even
        # though it is recorded by OBSERVE rather than duplicated in each
        # verifier receipt.  Bind it to the verifier outcome here so an ACCEPT
        # receipt cannot be replayed with a trace that claims zero flow or
        # breakdown.
        if set(region_by_candidate) != {
            item.candidate_effect_id for item in batch.verifier_receipts
        }:
            raise BatchRejected("OPERATING_REGION_RECEIPT_MISMATCH")
        for receipt in batch.verifier_receipts:
            region = region_by_candidate[receipt.candidate_effect_id].value
            disposition = _text(receipt.disposition)
            outcome = _text(receipt.semantic_outcome)
            reasons = tuple(receipt.reason_codes)
            if disposition == "ACCEPT" and region not in {"ACTIVE", "SATURATION"}:
                raise BatchRejected("OPERATING_REGION_RECEIPT_MISMATCH")
            if region == "CUTOFF" and (
                disposition != "ABSTAIN"
                or outcome != "UNASSESSED"
                or reasons != ("ZERO_FLOW",)
            ):
                raise BatchRejected("OPERATING_REGION_RECEIPT_MISMATCH")
            if region == "BREAKDOWN" and (
                disposition != "QUARANTINE"
                or outcome != "UNKNOWN"
                or reasons != ("BREAKDOWN_REGION",)
            ):
                raise BatchRejected("OPERATING_REGION_RECEIPT_MISMATCH")

        diagnose = phases[TickPhase.DIAGNOSE]
        expected_reason_codes = [
            reason
            for receipt in batch.verifier_receipts
            for reason in receipt.reason_codes
        ]
        if not batch.verifier_receipts and batch.audit_only:
            expected_reason_codes = list(batch.audit_reason_codes)
        if (
            not equal(
                diagnose.inputs["operating_regions"],
                observe.outputs["operating_regions"],
            )
            or not equal(
                diagnose.inputs["semantic_outcomes"],
                verify.outputs["semantic_outcomes"],
            )
            or not equal(diagnose.outputs["reason_codes"], expected_reason_codes)
            or diagnose.outputs["repair_required"]
            != any(item.repair_required for item in batch.verifier_receipts)
        ):
            raise BatchRejected("DIAGNOSE_PHASE_BINDING_INVALID")

        emit = phases[TickPhase.EMIT]
        accepted_publication = any(
            _text(item.disposition) == "ACCEPT"
            and _text(item.semantic_outcome) == "INTENDED"
            for item in batch.verifier_receipts
        )
        if (
            not equal(
                emit.inputs["verifier_receipt_ids"],
                [item.receipt_id for item in batch.verifier_receipts],
            )
            or not equal(
                emit.outputs["state_intent_ids"],
                [item.intent_id for item in batch.state_intents],
            )
            or not equal(
                emit.outputs["model_intent_ids"],
                [item.intent_id for item in batch.model_intents],
            )
            or not equal(
                emit.outputs["memory_intent_ids"],
                [item.intent_id for item in batch.memory_intents],
            )
            or not equal(
                emit.outputs["repair_ids"],
                [item.repair_id for item in batch.repair_frames],
            )
            or not equal(
                emit.outputs.get("repair_outcome_ids", []),
                [item.outcome_id for item in batch.repair_outcomes],
            )
            or emit.outputs["publication_requested"] is not accepted_publication
        ):
            raise BatchRejected("EMIT_PHASE_BINDING_INVALID")

        commit = phases[TickPhase.COMMIT]
        trace = phases[TickPhase.TRACE]
        if (
            commit.outputs["proposed_post_state_digest"] != after.state_digest
            or commit.outputs["proposed_post_model_digest"] != after.model_digest
            or trace.inputs["previous_trace_digest"] != batch.base_trace_digest
        ):
            raise BatchRejected("COMMIT_OR_TRACE_PHASE_BINDING_INVALID")

    def _candidates(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
    ) -> tuple[
        dict[str, dict[str, Any]],
        dict[str, dict[str, Any]],
        dict[str, dict[str, Any]],
    ]:
        candidates = _unique_by(
            batch.candidate_effects, "candidate_effect_id", label="candidate effect"
        )
        if len({item.producer_cjt_id for item in batch.candidate_effects}) != len(
            batch.candidate_effects
        ):
            raise BatchRejected("CANDIDATE_PRODUCER_DUPLICATE")
        receipts = _unique_by(
            batch.verifier_receipts, "receipt_id", label="verifier receipt"
        )
        by_candidate: dict[str, dict[str, Any]] = {}
        for receipt in receipts.values():
            _require_digest(receipt, "receipt_digest", "verifier receipt")
            if not self._receipt_identity_valid(receipt):
                raise BatchRejected("VERIFIER_RECEIPT_IDENTITY_INVALID")
            candidate_id = receipt.get("candidate_effect_id")
            if not isinstance(candidate_id, str) or candidate_id in by_candidate:
                raise BatchRejected("VERIFIER_RECEIPT_BINDING_INVALID")
            by_candidate[candidate_id] = receipt
        if set(candidates) != set(by_candidate):
            raise BatchRejected("EVERY_CANDIDATE_REQUIRES_ONE_VERIFIER_RECEIPT")
        eligible_cjts = {
            item.cjt_id for item in self._eligible_biases(batch.cause, before)
        }
        typed_candidates = {
            item.candidate_effect_id: item for item in batch.candidate_effects
        }
        for candidate_id, candidate in candidates.items():
            _require_digest(candidate, "candidate_digest", "candidate effect")
            if not self._candidate_identity_valid(candidate):
                raise BatchRejected("CANDIDATE_EFFECT_IDENTITY_INVALID")
            bias = before.by_bias_id.get(str(candidate.get("bias_id")))
            if bias is None:
                raise BatchRejected("CANDIDATE_BIAS_UNKNOWN")
            contract = self.operation_contracts.get(
                str(candidate.get("operation_contract_id"))
            )
            registered_contract = self._contract_for_bias(bias)
            expected = {
                "tick": batch.tick,
                "parent_cause_id": batch.cause.cause_id,
                "producer_cjt_id": bias.cjt_id,
                "operation_id": bias.stable.registered_operation_id,
                "bias_id": bias.bias_id,
                "bias_version": bias.version,
                "bias_digest": bias.state_digest,
                "model_digest": before.model_digest,
                "authoritative": False,
            }
            if any(candidate.get(key) != value for key, value in expected.items()):
                raise BatchRejected("CANDIDATE_CJT_BINDING_INVALID")
            if (
                bias.cjt_id not in eligible_cjts
                or candidate.get("operation_id")
                not in batch.cause.candidate_operation_ids
            ):
                raise BatchRejected("CANDIDATE_NOT_CAUSE_ELIGIBLE")
            if (
                contract is None
                or contract != registered_contract
                or candidate.get("operation_contract_digest")
                != contract.contract_digest
            ):
                raise BatchRejected("OPERATION_CONTRACT_NOT_ADMITTED")
            if batch.cause.cause_kind not in contract.accepted_cause_kinds:
                raise BatchRejected("CAUSE_KIND_NOT_ACCEPTED")
            if batch.cause.schema_version not in contract.accepted_schema_versions:
                raise BatchRejected("CAUSE_SCHEMA_NOT_ACCEPTED")
            if bias.rpm.readiness.profile_id != contract.readiness_profile_id:
                raise BatchRejected("READINESS_PROFILE_NOT_ADMITTED")
            if "PROPOSE_EFFECT" not in contract.legal_actions:
                raise BatchRejected("EFFECT_PROPOSAL_NOT_LEGAL")
            if not validate_operation_io(
                batch.cause,
                typed_candidates[candidate_id],
                contract,
            ):
                raise BatchRejected("OPERATION_IO_NOT_ADMITTED")
            receipt = by_candidate[candidate_id]
            receipt_expected = {
                "tick": batch.tick,
                "cause_id": batch.cause.cause_id,
                "candidate_effect_id": candidate_id,
                "candidate_effect_digest": candidate.get("candidate_digest"),
                "bias_id": bias.bias_id,
                "bias_version": bias.version,
                "bias_digest": bias.state_digest,
                "operation_contract_id": candidate.get("operation_contract_id"),
                "operation_contract_digest": contract.contract_digest,
                "model_digest": before.model_digest,
                "verifier_id": contract.verifier_id,
                "verifier_version": contract.verifier_version,
                "verifier_digest": contract.verifier_digest,
                "independent": True,
            }
            if any(receipt.get(key) != value for key, value in receipt_expected.items()):
                raise BatchRejected("VERIFIER_RECEIPT_BINDING_INVALID")
            if contract.verifier_id == bias.cjt_id:
                raise BatchRejected("SELF_VERIFICATION_FORBIDDEN")
            if _text(receipt.get("disposition")) == "ACCEPT" and (
                _text(receipt.get("semantic_outcome")) != "INTENDED"
                or receipt.get("repair_required") is not False
            ):
                raise BatchRejected("ACCEPT_RECEIPT_NOT_INTENDED")
        return candidates, receipts, by_candidate

    def _semantic_evidence(
        self,
        batch: NetworkCommitBatch,
        candidates: Mapping[str, Mapping[str, Any]],
        receipts: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        descriptors = _unique_by(
            batch.semantic_evidence, "evidence_id", label="semantic evidence"
        )
        evidence_keys = {
            "schema_version",
            "evidence_id",
            "source_id",
            "port_id",
            "expected_content",
            "opposite_content",
            "provenance",
            "evidence_digest",
        }
        by_receipt: dict[str, dict[str, Any]] = {}
        for receipt_id, receipt in receipts.items():
            references = set(receipt.get("evidence_refs", []))
            matches = [
                descriptor
                for evidence_id, descriptor in descriptors.items()
                if evidence_id in references
            ]
            if len(matches) != 1:
                raise BatchRejected("VERIFIER_EVIDENCE_BINDING_INVALID")
            descriptor = matches[0]
            if set(descriptor) != evidence_keys:
                raise BatchRejected("SEMANTIC_EVIDENCE_FIELDS_NOT_EXACT")
            if not verify_evidence_descriptor(descriptor):
                raise BatchRejected("SEMANTIC_EVIDENCE_DIGEST_INVALID")
            digest = descriptor.get("evidence_digest")
            if f"evidence-digest:{digest}" not in references:
                raise BatchRejected("VERIFIER_EVIDENCE_DIGEST_NOT_BOUND")
            source = descriptor.get("source_id")
            port = descriptor.get("port_id")
            candidate = candidates[str(receipt["candidate_effect_id"])]
            contract = self.operation_contracts.get(
                str(candidate["operation_contract_id"])
            )
            permitted = () if contract is None else contract.permitted_evidence_ports
            if source not in self.trusted_evidence_sources or port not in permitted:
                raise BatchRejected("SEMANTIC_EVIDENCE_SOURCE_OR_PORT_DENIED")
            if source == candidate.get("producer_cjt_id"):
                raise BatchRejected("SEMANTIC_EVIDENCE_NOT_INDEPENDENT")
            by_receipt[receipt_id] = descriptor
        if len(by_receipt) != len(descriptors):
            raise BatchRejected("UNBOUND_SEMANTIC_EVIDENCE")
        return by_receipt

    def _recompute_verifier_receipts(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
        evidence_by_receipt: Mapping[str, Mapping[str, Any]],
    ) -> None:
        """Replay the admitted verifier from trusted inputs and compare bytes."""

        typed_candidates = {
            item.candidate_effect_id: item for item in batch.candidate_effects
        }
        observe = next(
            item for item in batch.phase_records if item.phase is TickPhase.OBSERVE
        )
        observed_ids = tuple(observe.outputs["candidate_effect_ids"])
        try:
            region_by_candidate = {
                candidate_id: OperatingRegion(region)
                for candidate_id, region in zip(
                    observed_ids,
                    observe.outputs["operating_regions"],
                    strict=True,
                )
            }
        except (TypeError, ValueError) as error:
            raise BatchRejected("OPERATING_REGION_INVALID") from error

        if batch.audit_only and not batch.verifier_receipts:
            raise BatchRejected("AUDIT_REQUIRES_VERIFIED_CANDIDATE")
        authoritative_outcome = False
        for receipt in batch.verifier_receipts:
            candidate = typed_candidates.get(receipt.candidate_effect_id)
            descriptor = evidence_by_receipt.get(receipt.receipt_id)
            if candidate is None or descriptor is None:
                raise BatchRejected("VERIFIER_RECEIPT_BINDING_INVALID")
            bias = before.by_bias_id.get(candidate.bias_id)
            contract = self.operation_contracts.get(
                candidate.operation_contract_id
            )
            if bias is None or contract is None:
                raise BatchRejected("VERIFIER_RECEIPT_BINDING_INVALID")
            try:
                evidence = SemanticEvidence(
                    evidence_id=str(descriptor["evidence_id"]),
                    source_id=str(descriptor["source_id"]),
                    port_id=str(descriptor["port_id"]),
                    expected_content=descriptor["expected_content"],
                    opposite_content=descriptor["opposite_content"],
                    provenance=tuple(descriptor["provenance"]),
                )
                expected = IndependentVerifier(
                    contract.verifier_id,
                    verifier_version=contract.verifier_version,
                ).evaluate(
                    batch.cause,
                    candidate,
                    contract,
                    evidence,
                    bias=bias,
                    operating_region=region_by_candidate[candidate.candidate_effect_id],
                ).receipt
            except Exception as error:
                raise BatchRejected("VERIFIER_REPLAY_FAILED") from error
            if canonical_json(receipt.to_dict()) != canonical_json(expected.to_dict()):
                raise BatchRejected("VERIFIER_RECEIPT_NOT_EXACT_REPLAY")
            if receipt.disposition.value in {"ACCEPT", "REPAIR"}:
                authoritative_outcome = True
            if receipt.disposition.value == "ACCEPT" and (
                contract.ontology_status is not OntologyStatus.CANONICAL_ADMITTED
                or "execute" not in bias.governance.hard_permissions
                or bias.governance.quarantined
            ):
                raise BatchRejected("ACCEPT_NOT_AUTHORITY_ADMITTED")

        if batch.verifier_receipts and batch.audit_only is authoritative_outcome:
            raise BatchRejected("AUDIT_MODE_DOES_NOT_MATCH_VERIFIER_OUTCOME")
        if batch.audit_only and batch.verifier_receipts:
            expected_reasons = tuple(
                dict.fromkeys(
                    reason
                    for receipt in batch.verifier_receipts
                    for reason in receipt.reason_codes
                )
            )
            if tuple(batch.audit_reason_codes) != expected_reasons:
                raise BatchRejected("AUDIT_REASON_CODES_NOT_EXACT")

    def _resolve_artifact(
        self,
        batch: NetworkCommitBatch,
        reference: TensorArtifactRef,
    ) -> StoredArtifact:
        supplied = {item.artifact_id: item for item in batch.artifacts}
        artifact = supplied.get(reference.artifact_id)
        if artifact is None:
            try:
                artifact = self.store.load_artifact(reference.artifact_id)
            except PersistenceError as error:
                raise BatchRejected("ARTIFACT_REFERENCE_NOT_RETAINED") from error
        if artifact.sha256 != reference.sha256:
            raise BatchRejected("ARTIFACT_REFERENCE_DIGEST_MISMATCH")
        return artifact

    def _validate_memory_reads(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
    ) -> None:
        """Reproduce every claimed read from the Cause and durable records."""

        refs = tuple(batch.memory_read_refs)
        if (
            any(not isinstance(item, str) or not item for item in refs)
            or len(set(refs)) != len(refs)
        ):
            raise BatchRejected("MEMORY_READ_BINDING_INVALID")
        phases = {record.phase: record for record in batch.phase_records}
        route = phases[TickPhase.ROUTE]
        control_cjt_id = route.inputs["control_cjt_id"]
        try:
            bias = before.by_cjt_id[str(control_cjt_id)]
        except KeyError as error:
            raise BatchRejected("ROUTE_CONTROL_CJT_INVALID") from error
        _, memory_ceilings = _authoritative_array(
            batch.compute_plan.get("memory_read_quanta"),
            label="memory_read_quanta",
            boolean=False,
        )
        _, conducting = _authoritative_array(
            route.outputs.get("conducting_query_mask"),
            label="conducting_query_mask",
            boolean=True,
        )
        if len(memory_ceilings) != len(conducting):
            raise BatchRejected("MEMORY_READ_BINDING_INVALID")
        try:
            max_reads = global_memory_read_limit(
                tuple(int(ceiling) for ceiling in memory_ceilings),
                tuple(bool(has_flow) for has_flow in conducting),
                global_ceiling=bias.governance.compute_ceiling_units,
            )
        except RoutingError as error:
            raise BatchRejected("MEMORY_READ_BINDING_INVALID") from error
        can_read = (
            "read_memory" in bias.governance.hard_permissions
            and not bias.governance.quarantined
        )
        if refs and "READ_REFERENCES" not in self._contract_for_bias(
            bias
        ).memory_interface:
            raise BatchRejected("MEMORY_READ_INTERFACE_NOT_ADMITTED")
        requested = tuple(sorted(set(batch.cause.memory_refs)))
        expected = requested[:max_reads] if can_read else ()
        if refs and not can_read:
            raise BatchRejected("MEMORY_READ_NOT_PERMITTED")
        if refs != expected:
            raise BatchRejected("MEMORY_READ_BINDING_INVALID")

        for record_id in refs:
            record, _ = self._durable_memory_projection(record_id)
            content_ref = record.get("content_ref")
            if content_ref is None:
                continue
            if not isinstance(content_ref, Mapping):
                raise BatchRejected("MEMORY_ARTIFACT_REFERENCE_INVALID")
            try:
                reference = tensor_ref_from_mapping(content_ref)
                exact_reference = canonical_json(reference.to_dict()) == canonical_json(
                    content_ref
                )
            except (KeyError, TypeError, ValueError) as error:
                raise BatchRejected("MEMORY_ARTIFACT_REFERENCE_INVALID") from error
            if not exact_reference or not self.store.has_artifact(
                reference.artifact_id, reference.sha256
            ):
                raise BatchRejected("MEMORY_ARTIFACT_NOT_RETAINED")
            try:
                artifact = self.store.load_artifact(reference.artifact_id)
                decode_tensor(reference, artifact)
            except (ArtifactError, PersistenceError) as error:
                raise BatchRejected("MEMORY_ARTIFACT_REFERENCE_INVALID") from error

    def _validate_candidate_artifacts(
        self,
        batch: NetworkCommitBatch,
        by_candidate: Mapping[str, Mapping[str, Any]],
    ) -> None:
        candidate_ids = set(by_candidate)
        if not candidate_ids:
            return
        if batch.decoder_contract is None or self.candidate_validator is None:
            raise BatchRejected("SEMANTIC_DECODER_REQUIRED")
        decoder = _wire(batch.decoder_contract, label="decoder contract")
        if not verify_declared_digest(decoder, "decoder_digest"):
            raise BatchRejected("SEMANTIC_DECODER_CONTRACT_INVALID")
        decoder_digest = str(decoder["decoder_digest"])
        observe = next(
            item for item in batch.phase_records if item.phase is TickPhase.OBSERVE
        )
        control_digest = observe.diagnostics.get("control_binding_digest")
        typed = {
            item.candidate_effect_id: item for item in batch.candidate_effects
        }
        for candidate_id in candidate_ids:
            candidate = typed[candidate_id]
            admitted_decoder = self.decoder_contracts.get(candidate.producer_cjt_id)
            if (
                admitted_decoder is None
                or canonical_json(decoder) != canonical_json(admitted_decoder)
            ):
                raise BatchRejected("SEMANTIC_DECODER_CONTRACT_NOT_ADMITTED")
            expected_provenance = (
                f"cause:{batch.cause.cause_id}",
                f"bias:{candidate.bias_digest}",
                f"model:{candidate.model_digest}",
                f"decoder:{decoder_digest}",
                f"control-binding:{control_digest}",
            )
            if (
                not isinstance(control_digest, str)
                or candidate.provenance != expected_provenance
                or candidate.uncertainty_ppm != 0
            ):
                raise BatchRejected("CANDIDATE_PROVENANCE_INVALID")
            if (
                candidate.content_ref is None
                or f"decoder:{decoder_digest}" not in candidate.provenance
            ):
                raise BatchRejected("CANDIDATE_DECODER_BINDING_MISSING")
            artifact = self._resolve_artifact(batch, candidate.content_ref)
            try:
                valid = self.candidate_validator(candidate, artifact)
            except Exception as error:  # validator is untrusted proposal-side code
                raise BatchRejected("CANDIDATE_SEMANTIC_DECODE_FAILED") from error
            if valid is not True:
                raise BatchRejected("CANDIDATE_CONTENT_NOT_DERIVED_FROM_ARTIFACT")

    def _repairs(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
        after: NetworkStateEnvelope,
        candidates: Mapping[str, Mapping[str, Any]],
        receipts: Mapping[str, Mapping[str, Any]],
    ) -> tuple[StoredDocument, ...]:
        frames = _unique_by(batch.repair_frames, "repair_id", label="repair frame")
        repair_receipts: set[str] = set()
        documents: list[StoredDocument] = []
        cycle_keys: set[tuple[str, str]] = set()
        opened_by_bias: dict[str, set[str]] = {}
        typed_candidates = {
            item.candidate_effect_id: item for item in batch.candidate_effects
        }
        typed_receipts = {item.receipt_id: item for item in batch.verifier_receipts}
        for repair_id, frame in frames.items():
            _require_digest(frame, "frame_digest", "repair frame")
            receipt = receipts.get(str(frame.get("verifier_receipt_id")))
            candidate = candidates.get(str(frame.get("rejected_candidate_effect_id")))
            bias = before.by_bias_id.get(str(frame.get("suspended_bias_id")))
            if (
                receipt is None
                or candidate is None
                or bias is None
                or bool(bias.rpm.open_repair_ids)
                or receipt.get("candidate_effect_id") != candidate.get("candidate_effect_id")
                or _text(receipt.get("disposition")) != "REPAIR"
                or receipt.get("repair_required") is not True
                or frame.get("opened_tick") != batch.tick
                or frame.get("eligible_tick") != batch.tick + 1
                or frame.get("parent_cause_id") != batch.cause.cause_id
                or frame.get("suspended_bias_version") != bias.version
            ):
                raise BatchRejected("REPAIR_FRAME_BINDING_INVALID")
            if not self._viable_repair_cjts(before, bias.cjt_id):
                raise BatchRejected("REPAIR_ROUND_TRIP_NOT_VIABLE")
            try:
                retained_open_frames = tuple(
                    repair_frame_from_dict(
                        self.store.immutable_document("repair_frames", open_id)
                    )
                    for open_id in bias.rpm.open_repair_ids
                )
                expected_frame, expected_subgoal = open_repair(
                    cause=batch.cause,
                    candidate=typed_candidates[
                        str(frame["rejected_candidate_effect_id"])
                    ],
                    receipt=typed_receipts[str(frame["verifier_receipt_id"])],
                    bias=bias,
                    branch_count=len(retained_open_frames) + 1,
                    parent_depth=max(
                        (item.depth for item in retained_open_frames), default=0
                    ),
                    active_cycle_keys=tuple(
                        item.cycle_key for item in retained_open_frames
                    ),
                )
                typed_frame = repair_frame_from_dict(frame)
            except Exception as error:
                raise BatchRejected("REPAIR_FRAME_NOT_EXACT_REPLAY") from error
            if (
                typed_frame != expected_frame
                or typed_frame.subgoal_cause_id != expected_subgoal.cause_id
            ):
                raise BatchRejected("REPAIR_FRAME_NOT_EXACT_REPLAY")
            if self.coordinator_id not in bias.governance.state_write_authorities:
                raise BatchRejected("COORDINATOR_HAS_NO_REPAIR_GRANT")
            if (
                "write_bias" not in bias.governance.hard_permissions
                or "execute" not in bias.governance.hard_permissions
                or bias.governance.quarantined
            ):
                raise BatchRejected("REPAIR_WRITE_NOT_PERMITTED")
            key = (bias.bias_id, str(frame.get("cycle_key")))
            if not key[1] or key in cycle_keys:
                raise BatchRejected("REPAIR_CYCLE_KEY_INVALID")
            cycle_keys.add(key)
            repair_receipts.add(str(receipt["receipt_id"]))
            opened_by_bias.setdefault(bias.bias_id, set()).add(repair_id)
            documents.append(StoredDocument(repair_id, typed_frame))
        required = {
            receipt_id
            for receipt_id, receipt in receipts.items()
            if _text(receipt.get("disposition")) == "REPAIR"
            and receipt.get("repair_required") is True
        }
        if repair_receipts != required:
            raise BatchRejected("EVERY_REPAIR_RECEIPT_REQUIRES_ONE_FRAME")
        for bias_id, old in before.by_bias_id.items():
            new = after.by_bias_id[bias_id]
            added = set(new.rpm.open_repair_ids) - set(old.rpm.open_repair_ids)
            if added != opened_by_bias.get(bias_id, set()):
                raise BatchRejected("REPAIR_OPEN_DELTA_NOT_EXACT")
            if added:
                repair_id = next(iter(added))
                frame = next(
                    (
                        document.payload
                        if isinstance(document.payload, RepairFrame)
                        else repair_frame_from_dict(document.payload)
                    )
                    for document in documents
                    if document.record_id == repair_id
                )
                if (
                    new.rpm.open_repair_ids != (repair_id,)
                    or new.rpm.suspended_parent_cause_id != frame.parent_cause_id
                    or new.rpm.return_addresses != (frame.return_address,)
                    or repair_id not in new.memory.repair_frame_ids
                ):
                    raise BatchRejected("REPAIR_OPEN_STATE_CROSS_LINK_INVALID")
        return tuple(documents)

    def _repair_outcomes(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
        after: NetworkStateEnvelope,
        candidates: Mapping[str, Mapping[str, Any]],
        receipts: Mapping[str, Mapping[str, Any]],
    ) -> tuple[StoredDocument, ...]:
        """Validate immutable evidence for every repair removed from live state."""

        outcomes = _unique_by(
            batch.repair_outcomes, "outcome_id", label="repair outcome"
        )
        documents: list[StoredDocument] = []
        closed_by_bias: dict[str, set[str]] = {}
        seen_repairs: set[str] = set()
        for outcome_id, raw in outcomes.items():
            try:
                outcome = repair_outcome_from_dict(raw)
            except Exception as error:
                raise BatchRejected("REPAIR_OUTCOME_DIGEST_INVALID") from error
            if outcome.repair_id in seen_repairs:
                raise BatchRejected("REPAIR_OUTCOME_REPAIR_DUPLICATE")
            seen_repairs.add(outcome.repair_id)
            bias = before.by_bias_id.get(outcome.target_bias_id)
            candidate = candidates.get(outcome.resumed_candidate_effect_id)
            receipt = receipts.get(outcome.verifier_receipt_id)
            if (
                outcome.tick != batch.tick
                or outcome.resumed_cause_id != batch.cause.cause_id
                or batch.cause.parent_effect_id != outcome.result_effect_id
                or bias is None
                or outcome.target_bias_version != bias.version
                or outcome.target_bias_digest != bias.state_digest
                or outcome.repair_id not in bias.rpm.open_repair_ids
                or candidate is None
                or receipt is None
                or candidate.get("parent_cause_id") != batch.cause.cause_id
                or candidate.get("bias_id") != bias.bias_id
                or receipt.get("candidate_effect_id")
                != outcome.resumed_candidate_effect_id
                or receipt.get("cause_id") != batch.cause.cause_id
                or receipt.get("bias_id") != bias.bias_id
                or _text(receipt.get("disposition")) != "ACCEPT"
                or _text(receipt.get("semantic_outcome")) != "INTENDED"
                or receipt.get("repair_required") is not False
            ):
                raise BatchRejected("REPAIR_OUTCOME_BINDING_INVALID")
            try:
                stored_frame = self.store.immutable_document(
                    "repair_frames", outcome.repair_id
                )
                frame = repair_frame_from_dict(stored_frame)
                result_effect = self.store.immutable_document(
                    "published_effects", outcome.result_effect_id
                )
                result_candidate = self.store.immutable_document(
                    "candidate_effects", str(result_effect["candidate_effect_id"])
                )
                result_receipt = self.store.immutable_document(
                    "verifier_receipts", str(result_effect["verifier_receipt_id"])
                )
                parent_cause = self.store.immutable_document(
                    "causes", frame.parent_cause_id
                )
                rebuilt_cause = cause_from_committed_effect(
                    self.store,
                    outcome.result_effect_id,
                    tick=batch.tick,
                    candidate_operation_ids=tuple(
                        parent_cause["candidate_operation_ids"]
                    ),
                    goal_context=parent_cause["goal_context"],
                )
            except Exception as error:
                raise BatchRejected("REPAIR_OUTCOME_EVIDENCE_NOT_RETAINED") from error
            if (
                frame.status.value != "OPEN"
                or frame.frame_digest != outcome.frame_digest
                or frame.suspended_bias_id != bias.bias_id
                or frame.parent_cause_id != bias.rpm.suspended_parent_cause_id
                or bias.rpm.return_addresses != (frame.return_address,)
                or outcome.tick != frame.eligible_tick + 1
                or result_effect.get("published_effect_id") != outcome.result_effect_id
                or result_effect.get("publication_digest")
                != outcome.result_effect_digest
                or result_effect.get("commit_receipt_id")
                != outcome.result_effect_commit_receipt_id
                or rebuilt_cause != batch.cause
                or not verify_declared_digest(result_effect, "publication_digest")
                or result_candidate.get("parent_cause_id") != frame.subgoal_cause_id
                or result_candidate.get("tick") != frame.eligible_tick
                or result_candidate.get("producer_cjt_id")
                not in self._viable_repair_cjts(before, bias.cjt_id)
                or result_effect.get("candidate_effect_id")
                != result_candidate.get("candidate_effect_id")
                or result_receipt.get("candidate_effect_id")
                != result_candidate.get("candidate_effect_id")
                or _text(result_receipt.get("disposition")) != "ACCEPT"
                or _text(result_receipt.get("semantic_outcome")) != "INTENDED"
                or not verify_declared_digest(result_candidate, "candidate_digest")
                or not verify_declared_digest(result_receipt, "receipt_digest")
            ):
                raise BatchRejected("REPAIR_OUTCOME_EVIDENCE_INVALID")
            closed_by_bias.setdefault(bias.bias_id, set()).add(outcome.repair_id)
            documents.append(StoredDocument(outcome_id, outcome))

        for bias_id, old in before.by_bias_id.items():
            new = after.by_bias_id[bias_id]
            removed = set(old.rpm.open_repair_ids) - set(new.rpm.open_repair_ids)
            declared = closed_by_bias.get(bias_id, set())
            if removed != declared:
                raise BatchRejected("REPAIR_CLOSED_WITHOUT_EXACT_OUTCOME")
            expected_history = list(old.rpm.repair_history)
            for repair_id in old.rpm.open_repair_ids:
                if repair_id in declared and repair_id not in expected_history:
                    expected_history.append(repair_id)
            if (
                new.rpm.repair_history != tuple(expected_history[-16:])
                or (
                    bool(declared)
                    and new.memory.repair_frame_ids != old.memory.repair_frame_ids
                )
                or any(
                any(
                    repair_id in candidate_bias.rpm.open_repair_ids
                    for candidate_bias in after.biases
                )
                for repair_id in declared
                )
            ):
                raise BatchRejected("REPAIR_OUTCOME_NOT_REFLECTED_IN_STATE")
        return tuple(documents)

    def _state_intents(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
        after: NetworkStateEnvelope,
        candidates: Mapping[str, Mapping[str, Any]],
        receipts: Mapping[str, Mapping[str, Any]],
        repair_documents: Sequence[StoredDocument],
        repair_outcome_documents: Sequence[StoredDocument],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        intents = _unique_by(batch.state_intents, "intent_id", label="state intent")
        model_intents = _unique_by(
            batch.model_intents, "intent_id", label="model intent"
        )
        global_model_changed = (
            after.model_version != before.model_version
            or after.model_digest != before.model_digest
            or after.model_artifact_ref != before.model_artifact_ref
        )
        model_initiator_bias_id: str | None = None
        if global_model_changed:
            if len(model_intents) != 1:
                raise BatchRejected("GLOBAL_MODEL_CHANGED_WITHOUT_ONE_INTENT")
            model_intent = next(iter(model_intents.values()))
            model_receipt = receipts.get(str(model_intent.get("verifier_receipt_id")))
            if model_receipt is None or not isinstance(
                model_receipt.get("bias_id"), str
            ):
                raise BatchRejected("MODEL_INTENT_RECEIPT_MISSING")
            model_initiator_bias_id = str(model_receipt["bias_id"])

        def derived_theta(old: BiasState) -> dict[str, Any]:
            value = _json_clone(old.theta.to_dict())
            references: list[dict[str, Any]] = []
            replaced_global = False
            for reference in old.theta.parameter_artifacts:
                if reference == before.model_artifact_ref:
                    references.append(after.model_artifact_ref.to_dict())
                    replaced_global = True
                else:
                    references.append(reference.to_dict())
            if not replaced_global:
                raise BatchRejected("BIAS_GLOBAL_MODEL_POINTER_MISSING")
            value["model_id"] = after.model_id
            value["model_version"] = after.model_version
            value["model_digest"] = after.model_digest
            value["parameter_artifacts"] = references
            return value

        by_bias: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        repair_receipts = {
            _wire(item.payload, label="repair frame")["verifier_receipt_id"]
            for item in repair_documents
        }
        mapped: list[dict[str, Any]] = []
        for intent_id, intent in intents.items():
            _require_digest(intent, "intent_digest", "state intent")
            try:
                expected_intent_id = content_id(
                    "intent-state",
                    {
                        "tick": intent.get("tick"),
                        "bias_digest": intent.get("expected_bias_digest"),
                        "receipt_id": intent.get("verifier_receipt_id"),
                        "target_path": intent.get("target_path"),
                        "replacement": intent.get("replacement"),
                        "issuer_id": intent.get("issuer_id"),
                    },
                )
            except (TypeError, ValueError) as error:
                raise BatchRejected("STATE_INTENT_IDENTITY_INVALID") from error
            if intent_id != expected_intent_id:
                raise BatchRejected("STATE_INTENT_IDENTITY_INVALID")
            bias_id = str(intent.get("target_bias_id"))
            bias = before.by_bias_id.get(bias_id)
            if bias is None:
                raise BatchRejected("STATE_INTENT_BIAS_UNKNOWN")
            if intent.get("authority_capability") != PROPOSE_STATE_UPDATE:
                raise BatchRejected("STATE_INTENT_CAPABILITY_INVALID")
            if any(
                intent.get(key) != value
                for key, value in {
                    "tick": batch.tick,
                    "expected_bias_version": bias.version,
                    "expected_bias_digest": bias.state_digest,
                }.items()
            ):
                raise BatchRejected("STATE_INTENT_HEAD_BINDING_INVALID")
            if self.coordinator_id not in bias.governance.state_write_authorities:
                raise BatchRejected("COORDINATOR_HAS_NO_STATE_WRITE_GRANT")
            if (
                "write_bias" not in bias.governance.hard_permissions
                or "execute" not in bias.governance.hard_permissions
                or bias.governance.quarantined
            ):
                raise BatchRejected("BIAS_STATE_WRITE_NOT_PERMITTED")
            if intent.get("issuer_id") not in {
                bias.cjt_id,
                *bias.governance.state_write_authorities,
            }:
                raise BatchRejected("STATE_INTENT_ISSUER_INVALID")
            path = _decode_pointer(str(intent.get("target_path")))
            if len(path) != 1 or path[0] not in {"memory", "rpm", "operating", "theta"}:
                raise BatchRejected("STATE_INTENT_ROOT_PATH_INVALID")
            if tuple(intent.get("reason_codes", ())) != (
                f"PROPOSE_{path[0].upper()}_SUCCESSOR",
            ):
                raise BatchRejected("STATE_INTENT_REASON_CODES_INVALID")
            if path[0] == "theta" and (
                not global_model_changed or bias_id != model_initiator_bias_id
            ):
                raise BatchRejected("THETA_INTENT_NOT_GLOBAL_MODEL_INITIATOR")
            receipt = receipts.get(str(intent.get("verifier_receipt_id")))
            if receipt is None or receipt.get("bias_id") != bias_id:
                raise BatchRejected("STATE_INTENT_RECEIPT_MISSING")
            contract = self.operation_contracts.get(
                str(receipt.get("operation_contract_id"))
            )
            if contract is None or str(intent.get("target_path")) not in set(
                contract.legal_bias_paths
            ):
                raise BatchRejected("STATE_INTENT_PATH_NOT_LEGAL")
            disposition = _text(receipt.get("disposition"))
            if disposition == "ACCEPT":
                if _text(receipt.get("semantic_outcome")) != "INTENDED":
                    raise BatchRejected("STATE_INTENT_NOT_ACCEPTED")
            elif disposition == "REPAIR":
                if path[0] not in {"memory", "rpm", "operating"} or receipt.get(
                    "receipt_id"
                ) not in repair_receipts:
                    raise BatchRejected("REPAIR_INTENT_SCOPE_INVALID")
            elif path[0] != "operating":
                raise BatchRejected("NONACCEPT_INTENT_SCOPE_INVALID")
            by_bias.setdefault(bias_id, []).append((intent_id, intent))
            mapped.append(intent)

        for bias_id, old in before.by_bias_id.items():
            new = after.by_bias_id[bias_id]
            selected = by_bias.get(bias_id, [])
            if global_model_changed and bias_id != model_initiator_bias_id and selected:
                raise BatchRejected("INACTIVE_BIAS_MAY_ONLY_RECEIVE_DERIVED_THETA")
            roots = [str(item[1]["target_path"]) for item in selected]
            if len(set(roots)) != len(roots):
                raise BatchRejected("STATE_INTENT_PATHS_OVERLAP")
            if global_model_changed and bias_id == model_initiator_bias_id:
                if "/theta" not in roots:
                    raise BatchRejected("MODEL_INITIATOR_THETA_INTENT_REQUIRED")
            if not selected and not global_model_changed:
                if new != old:
                    raise BatchRejected("BIAS_CHANGED_WITHOUT_STATE_INTENT")
                continue
            projected = _json_clone(old.to_dict())
            for _, intent in selected:
                root = str(intent["target_path"])[1:]
                projected[root] = _json_clone(intent["replacement"])
            if global_model_changed:
                expected_theta = derived_theta(old)
                if "/theta" in roots and projected["theta"] != expected_theta:
                    raise BatchRejected("THETA_INTENT_NOT_EXACT_GLOBAL_POINTER")
                projected["theta"] = expected_theta
            projected["version"] = old.version + 1
            projected["previous_digest"] = old.state_digest
            projected["state_digest"] = new.state_digest
            if projected != new.to_dict():
                raise BatchRejected("BIAS_AFTER_DOES_NOT_EQUAL_INTENT_RESULT")

        observe = next(
            item for item in batch.phase_records if item.phase is TickPhase.OBSERVE
        )
        region_by_candidate = {
            candidate_id: OperatingRegion(region)
            for candidate_id, region in zip(
                observe.outputs["candidate_effect_ids"],
                observe.outputs["operating_regions"],
                strict=True,
            )
        }
        frames_by_receipt = {
            str(_wire(item.payload, label="repair frame")["verifier_receipt_id"]):
            str(_wire(item.payload, label="repair frame")["repair_id"])
            for item in repair_documents
        }
        outcomes_by_receipt: dict[str, str] = {}
        for document in repair_outcome_documents:
            outcome = _wire(document.payload, label="repair outcome")
            receipt_id = str(outcome["verifier_receipt_id"])
            if receipt_id in outcomes_by_receipt:
                raise BatchRejected("REPAIR_OUTCOME_RECEIPT_DUPLICATE")
            outcomes_by_receipt[receipt_id] = str(outcome["repair_id"])
        route_record = next(
            item for item in batch.phase_records if item.phase is TickPhase.ROUTE
        )
        control_cjt_id = str(route_record.inputs["control_cjt_id"])
        consumed_memory = [
            self._durable_memory_projection(record_id)[0]
            for record_id in batch.memory_read_refs
        ]
        consumed_memory_ids = tuple(
            str(item["memory_record_id"]) for item in consumed_memory
        )
        consumed_provenance = tuple(
            str(reference)
            for item in consumed_memory
            for reference in item["provenance"]
        )
        for receipt_id, receipt in receipts.items():
            disposition = _text(receipt.get("disposition"))
            if disposition not in {"ACCEPT", "REPAIR"}:
                continue
            candidate = candidates.get(str(receipt.get("candidate_effect_id")))
            if candidate is None:
                raise BatchRejected("BIAS_SUCCESSOR_NOT_EXACT_ADVANCE")
            old = before.by_bias_id[str(receipt["bias_id"])]
            new = after.by_bias_id[old.bias_id]
            try:
                region = region_by_candidate[str(candidate["candidate_effect_id"])]
                semantic_outcome = receipt["semantic_outcome"]
                if disposition == "ACCEPT":
                    close_repair_id = outcomes_by_receipt.get(receipt_id)
                    if old.rpm.open_repair_ids and tuple(
                        old.rpm.open_repair_ids
                    ) != (close_repair_id,):
                        raise BatchRejected(
                            "SUSPENDED_BIAS_ACCEPT_REQUIRES_EXACT_REPAIR_OUTCOME"
                        )
                    recurrent_ref = new.memory.recurrent_state_ref
                    if recurrent_ref is not None:
                        candidate_ref = candidate.get("content_ref")
                        artifact = self._resolve_artifact(batch, recurrent_ref)
                        decode_tensor(recurrent_ref, artifact)
                        if (
                            artifact.kind != "persistent-recurrent-bias"
                            or not isinstance(candidate_ref, Mapping)
                            or tuple(recurrent_ref.shape)
                            != tuple(candidate_ref.get("shape", ()))
                            or recurrent_ref.dtype != candidate_ref.get("dtype")
                        ):
                            raise BatchRejected(
                                "RECURRENT_STATE_ARTIFACT_NOT_ADMITTED"
                            )
                    expected = advance_bias(
                        old,
                        tick=batch.tick,
                        region=region,
                        semantic_outcome=semantic_outcome,
                        verifier_receipt_id=receipt_id,
                        cause_id=batch.cause.cause_id,
                        effect_id=str(candidate["candidate_effect_id"]),
                        recurrent_state_ref=recurrent_ref,
                        close_repair_id=close_repair_id,
                        retrieved_memory_refs=(
                            consumed_memory_ids
                            if candidate["producer_cjt_id"] == control_cjt_id
                            else ()
                        ),
                        provenance_refs=(
                            consumed_provenance
                            if candidate["producer_cjt_id"] == control_cjt_id
                            else ()
                        ),
                    )
                else:
                    repair_id = frames_by_receipt.get(receipt_id)
                    if repair_id is None:
                        raise BatchRejected("BIAS_SUCCESSOR_NOT_EXACT_ADVANCE")
                    frame = next(
                        (
                            item.payload
                            if isinstance(item.payload, RepairFrame)
                            else repair_frame_from_dict(item.payload)
                        )
                        for item in repair_documents
                        if item.record_id == repair_id
                    )
                    expected = advance_bias(
                        old,
                        tick=batch.tick,
                        region=region,
                        semantic_outcome=semantic_outcome,
                        verifier_receipt_id=receipt_id,
                        cause_id=batch.cause.cause_id,
                        open_repair_id=repair_id,
                        open_repair_return_address=frame.return_address,
                        record_memory=False,
                    )
            except BatchRejected:
                raise
            except Exception as error:
                raise BatchRejected("BIAS_SUCCESSOR_NOT_EXACT_ADVANCE") from error
            if (
                new.memory != expected.memory
                or new.rpm != expected.rpm
                or new.operating != expected.operating
            ):
                raise BatchRejected("BIAS_SUCCESSOR_NOT_EXACT_ADVANCE")
        return list(intents), mapped

    def _memory_intents(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
        candidates: Mapping[str, Mapping[str, Any]],
        receipts: Mapping[str, Mapping[str, Any]],
    ) -> tuple[list[str], tuple[StoredDocument, ...], list[dict[str, Any]]]:
        intents = _unique_by(batch.memory_intents, "intent_id", label="memory intent")
        documents: list[StoredDocument] = []
        record_ids: set[str] = set()
        for intent in intents.values():
            _require_digest(intent, "intent_digest", "memory intent")
            bias = before.by_bias_id.get(str(intent.get("target_bias_id")))
            if bias is None:
                raise BatchRejected("MEMORY_INTENT_BIAS_UNKNOWN")
            if intent.get("authority_capability") != PROPOSE_MEMORY_WRITE:
                raise BatchRejected("MEMORY_INTENT_CAPABILITY_INVALID")
            if any(
                intent.get(key) != value
                for key, value in {
                    "tick": batch.tick,
                    "expected_bias_version": bias.version,
                    "expected_bias_digest": bias.state_digest,
                }.items()
            ):
                raise BatchRejected("MEMORY_INTENT_HEAD_BINDING_INVALID")
            if self.coordinator_id not in bias.governance.memory_write_authorities:
                raise BatchRejected("COORDINATOR_HAS_NO_MEMORY_WRITE_GRANT")
            if (
                "write_memory" not in bias.governance.hard_permissions
                or "execute" not in bias.governance.hard_permissions
                or bias.governance.quarantined
            ):
                raise BatchRejected("MEMORY_WRITE_NOT_PERMITTED")
            if intent.get("issuer_id") not in {
                bias.cjt_id,
                *bias.governance.memory_write_authorities,
            }:
                raise BatchRejected("MEMORY_INTENT_ISSUER_INVALID")
            receipt = receipts.get(str(intent.get("verifier_receipt_id")))
            candidate = None if receipt is None else candidates.get(
                str(receipt.get("candidate_effect_id"))
            )
            if (
                receipt is None
                or candidate is None
                or receipt.get("bias_id") != bias.bias_id
                or _text(receipt.get("disposition")) != "ACCEPT"
                or _text(receipt.get("semantic_outcome")) != "INTENDED"
            ):
                raise BatchRejected("MEMORY_INTENT_NOT_ACCEPTED")
            contract = self.operation_contracts.get(
                str(receipt.get("operation_contract_id"))
            )
            if contract is None or "PROPOSE_WRITE" not in contract.memory_interface:
                raise BatchRejected("MEMORY_WRITE_INTERFACE_NOT_ADMITTED")
            expected_content = {
                "cause_id": batch.cause.cause_id,
                "candidate_effect_id": candidate["candidate_effect_id"],
                "semantic_content": candidate["content"],
            }
            expected_provenance = [
                f"bias:{bias.state_digest}",
                f"verifier:{receipt['receipt_id']}",
            ]
            expected_evidence = list(receipt.get("evidence_refs", ()))
            exact_fields = {
                "issuer_id": candidate["producer_cjt_id"],
                "target_bias_id": bias.bias_id,
                "expected_bias_version": bias.version,
                "expected_bias_digest": bias.state_digest,
                "verifier_receipt_id": receipt["receipt_id"],
                "memory_kind": "EPISODIC",
                "content": expected_content,
                "content_ref": candidate.get("content_ref"),
                "confidence_ppm": 1_000_000,
                "provenance": expected_provenance,
                "evidence_refs": expected_evidence,
            }
            try:
                semantic_matches = all(
                    canonical_json(intent.get(name)) == canonical_json(value)
                    for name, value in exact_fields.items()
                )
            except (TypeError, ValueError):
                semantic_matches = False
            if not semantic_matches:
                raise BatchRejected("MEMORY_INTENT_SEMANTICS_NOT_EXACT")
            identity = {
                "tick": batch.tick,
                **exact_fields,
            }
            try:
                expected_intent_id = content_id("intent-memory", identity)
                expected_record_id = content_id("memory", identity)
            except (TypeError, ValueError) as error:
                raise BatchRejected("MEMORY_INTENT_IDENTITY_INVALID") from error
            if (
                intent.get("intent_id") != expected_intent_id
                or intent.get("memory_record_id") != expected_record_id
            ):
                raise BatchRejected("MEMORY_INTENT_IDENTITY_INVALID")
            record_id = intent.get("memory_record_id")
            if not isinstance(record_id, str) or not record_id or record_id in record_ids:
                raise BatchRejected("MEMORY_RECORD_ID_INVALID")
            record_ids.add(record_id)
            typed_intent = next(
                item
                for item in batch.memory_intents
                if item.intent_id == intent["intent_id"]
            )
            documents.append(
                StoredDocument(
                    record_id,
                    memory_document(typed_intent, committed_by=self.coordinator_id),
                )
            )
        return list(intents), tuple(documents), list(intents.values())

    def _validate_outcome_state_transitions(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
        after: NetworkStateEnvelope,
        receipts: Mapping[str, Mapping[str, Any]],
        state_values: Sequence[Mapping[str, Any]],
        repair_documents: Sequence[StoredDocument],
    ) -> None:
        """Require every authority-bearing outcome to advance its producer Bias."""

        roots_by_receipt: dict[str, set[str]] = {}
        for intent in state_values:
            roots_by_receipt.setdefault(
                str(intent["verifier_receipt_id"]), set()
            ).add(str(intent["target_path"]))
        repairs_by_receipt = {
            str(_wire(item.payload, label="repair frame")["verifier_receipt_id"])
            for item in repair_documents
        }
        observe = next(
            item for item in batch.phase_records if item.phase is TickPhase.OBSERVE
        )
        region_by_candidate = {
            candidate_id: OperatingRegion(region)
            for candidate_id, region in zip(
                observe.outputs["candidate_effect_ids"],
                observe.outputs["operating_regions"],
                strict=True,
            )
        }
        for receipt_id, receipt in receipts.items():
            disposition = _text(receipt.get("disposition"))
            if disposition not in {"ACCEPT", "REPAIR"}:
                continue
            bias_id = str(receipt["bias_id"])
            old = before.by_bias_id[bias_id]
            new = after.by_bias_id[bias_id]
            roots = roots_by_receipt.get(receipt_id, set())
            required_roots = (
                {"/operating"}
                if disposition == "ACCEPT"
                else {"/rpm", "/operating"}
            )
            candidate_id = str(receipt["candidate_effect_id"])
            expected_region = region_by_candidate[candidate_id]
            if (
                new == old
                or not required_roots.issubset(roots)
                or new.operating.region is not expected_region
                or new.operating.semantic_outcome.value
                != _text(receipt["semantic_outcome"])
                or new.operating.previous_committed_verifier_receipt_id
                != receipt_id
                or new.operating.last_tick != batch.tick
            ):
                raise BatchRejected("VERIFIER_OUTCOME_BIAS_TRANSITION_MISSING")
            if disposition == "REPAIR" and receipt_id not in repairs_by_receipt:
                raise BatchRejected("REPAIR_OUTCOME_FRAME_MISSING")

    def _model_intents(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
        after: NetworkStateEnvelope,
        candidates: Mapping[str, Mapping[str, Any]],
        receipts: Mapping[str, Mapping[str, Any]],
    ) -> tuple[list[str], list[dict[str, Any]], str]:
        intents = _unique_by(batch.model_intents, "intent_id", label="model intent")
        if len(intents) > 1:
            raise BatchRejected("ONLY_ONE_GLOBAL_MODEL_UPDATE_PER_COMMIT")
        if not intents:
            if (
                batch.model_version is not None
                or after.model_version != before.model_version
                or after.model_digest != before.model_digest
                or batch.qualification_receipts
            ):
                raise BatchRejected("GLOBAL_MODEL_CHANGED_WITHOUT_INTENT")
            return [], [], before.model_digest

        intent_id, intent = next(iter(intents.items()))
        _require_digest(intent, "intent_digest", "model intent")
        if intent.get("authority_capability") != PROPOSE_MODEL_UPDATE:
            raise BatchRejected("MODEL_INTENT_CAPABILITY_INVALID")
        if (
            _text(intent.get("update_kind")) != "GRADIENT_DELTA"
            or not isinstance(intent.get("gradient_artifact"), Mapping)
        ):
            raise BatchRejected("MODEL_INTENT_UPDATE_KIND_INVALID")
        if tuple(intent.get("reason_codes", ())) != (
            "VERIFIED_EXPERIENCE",
            "SELECTIVE_PLASTICITY",
            "QUALIFIED",
        ):
            raise BatchRejected("MODEL_INTENT_REASON_CODES_INVALID")
        if any(
            intent.get(key) != value
            for key, value in {
                "tick": batch.tick,
                "model_id": before.model_id,
                "expected_model_version": before.model_version,
                "expected_model_digest": before.model_digest,
            }.items()
        ):
            raise BatchRejected("MODEL_INTENT_HEAD_BINDING_INVALID")
        receipt = receipts.get(str(intent.get("verifier_receipt_id")))
        candidate = None if receipt is None else candidates.get(
            str(receipt.get("candidate_effect_id"))
        )
        bias = None if candidate is None else before.by_bias_id.get(
            str(candidate.get("bias_id"))
        )
        if (
            receipt is None
            or candidate is None
            or bias is None
            or intent.get("issuer_id") != candidate.get("producer_cjt_id")
            or _text(receipt.get("disposition")) != "ACCEPT"
            or _text(receipt.get("semantic_outcome")) != "INTENDED"
        ):
            raise BatchRejected("MODEL_INTENT_NOT_ACCEPTED")
        groups = set(intent.get("parameter_group_ids", []))
        producer = str(candidate.get("producer_cjt_id"))
        operation_contract = self._contract_for_bias(bias)
        normalized_groups: set[str] = set()
        for group in groups:
            if not isinstance(group, str):
                raise BatchRejected("MODEL_PARAMETER_GROUP_ROLE_INVALID")
            operation_prefix = f"cjt:{producer}:operation:"
            if group.startswith(operation_prefix):
                normalized_groups.add(f"operation:{group[len(operation_prefix):]}")
            elif group == f"cjt:{producer}:bias_update_head":
                normalized_groups.add("bias_update_head")
            else:
                raise BatchRejected("MODEL_PARAMETER_GROUP_ROLE_INVALID")
        if not normalized_groups.issubset(
            set(operation_contract.plasticity_groups)
        ):
            raise BatchRejected("MODEL_PARAMETER_GROUP_ROLE_NOT_IN_CONTRACT")
        route = next(
            item for item in batch.phase_records if item.phase is TickPhase.ROUTE
        )
        _, total_current_units = _authoritative_array(
            route.outputs["total_current_microunits"],
            label="total_current_microunits",
            boolean=False,
        )
        try:
            flow_ppm = bounded_mean_flow_ppm(
                tuple(int(item) for item in total_current_units)
            )
        except RoutingError as error:
            raise BatchRejected("MODEL_PLASTICITY_FLOW_INVALID") from error
        expected_plasticity_ppm = min(
            bias.rpm.readiness.readiness_ppm,
            flow_ppm,
        )
        if (
            not groups
            or not groups.issubset(set(bias.theta.parameter_group_ids))
            or "learn" not in bias.governance.learning_permissions
            or not groups.issubset(set(bias.governance.learning_permissions))
        ):
            raise BatchRejected("MODEL_PARAMETER_GROUP_NOT_ADMITTED")
        if intent.get("plasticity_ppm") != expected_plasticity_ppm:
            raise BatchRejected("MODEL_PLASTICITY_NOT_EXACT")
        if (
            "execute" not in bias.governance.hard_permissions
            or "write_bias" not in bias.governance.hard_permissions
            or bias.governance.quarantined
        ):
            raise BatchRejected("MODEL_UPDATE_NOT_PERMITTED")
        if self.coordinator_id not in bias.governance.state_write_authorities:
            raise BatchRejected("COORDINATOR_HAS_NO_MODEL_WRITE_GRANT")
        qualifications = {}
        for value in batch.qualification_receipts:
            mapped = _wire(value, label="qualification receipt")
            identity = mapped.get("qualification_receipt_id", mapped.get("receipt_id"))
            if not isinstance(identity, str) or not identity or identity in qualifications:
                raise BatchRejected("QUALIFICATION_RECEIPT_IDENTITY_INVALID")
            qualifications[identity] = mapped
        qualification = qualifications.get(str(intent.get("qualification_receipt_id")))
        if set(qualifications) != {str(intent.get("qualification_receipt_id"))}:
            raise BatchRejected("UNBOUND_QUALIFICATION_RECEIPT")
        if qualification is None:
            raise BatchRejected("QUALIFICATION_RECEIPT_DIGEST_INVALID")
        try:
            qualification = validate_qualification_receipt(
                qualification,
                policy=self.learning_policy,
            )
        except LearningError as error:
            raise BatchRejected("QUALIFICATION_RECEIPT_NOT_ADMITTED") from error
        qualified_digest = qualification.get(
            "candidate_model_digest", qualification.get("model_digest")
        )
        if (
            qualification.get("independent") is not True
            or qualified_digest != after.model_digest
            or _text(qualification.get("disposition", qualification.get("outcome")))
            not in {"ACCEPT", "PASS", "QUALIFIED"}
            or qualification.get("qualified") is not True
            or qualification.get("target_improved") is not True
            or qualification.get("retention_passed") is not True
            or qualification.get("regression_passed") is not True
        ):
            raise BatchRejected("MODEL_UPDATE_NOT_INDEPENDENTLY_QUALIFIED")
        if (
            after.model_version != before.model_version + 1
            or batch.model_version is None
            or batch.model_version.model_digest != after.model_digest
            or batch.model_version.parent_model_digest != before.model_digest
            or batch.model_version.artifact_id
            != intent.get("candidate_artifact", {}).get("artifact_id")
            or after.model_digest != intent.get("candidate_artifact", {}).get("sha256")
            or after.model_artifact_ref.artifact_id
            != intent.get("candidate_artifact", {}).get("artifact_id")
        ):
            raise BatchRejected("MODEL_VERSION_BINDING_INVALID")
        model_manifest_keys = {
            "schema_version",
            "model_id",
            "model_version",
            "model_digest",
            "model_artifact_ref",
            "network",
            "config",
            "decoder_labels",
            "parent_model_digest",
            "learning_tick",
            "initiating_cjt_id",
            "qualification_receipt_id",
            "changed_parameter_names",
        }
        try:
            model_manifest = _wire(
                batch.model_version.payload,
                label="model version manifest",
            )
            static_context_matches = all(
                canonical_json(model_manifest[name])
                == canonical_json(self.model_manifest_context[name])
                for name in ("network", "config", "decoder_labels")
            )
        except (KeyError, TypeError, ValueError) as error:
            raise BatchRejected("MODEL_VERSION_MANIFEST_INVALID") from error
        if (
            set(model_manifest) != model_manifest_keys
            or model_manifest["schema_version"]
            != "cas.neural-cjt.model-version/0.2"
            or model_manifest["model_id"] != before.model_id
            or model_manifest["model_version"] != after.model_version
            or model_manifest["model_digest"] != after.model_digest
            or canonical_json(model_manifest["model_artifact_ref"])
            != canonical_json(after.model_artifact_ref.to_dict())
            or not static_context_matches
            or model_manifest["parent_model_digest"] != before.model_digest
            or model_manifest["learning_tick"] != batch.tick
            or model_manifest["initiating_cjt_id"]
            != candidate.get("producer_cjt_id")
            or model_manifest["qualification_receipt_id"]
            != qualification["qualification_receipt_id"]
            or not isinstance(model_manifest["changed_parameter_names"], list)
        ):
            raise BatchRejected("MODEL_VERSION_MANIFEST_INVALID")

        candidate_ref = tensor_ref_from_mapping(intent["candidate_artifact"])
        active_artifact = self._resolve_artifact(batch, before.model_artifact_ref)
        candidate_artifact = self._resolve_artifact(batch, candidate_ref)
        active_entries = _checkpoint_entries(before.model_artifact_ref, active_artifact)
        candidate_entries = _checkpoint_entries(candidate_ref, candidate_artifact)
        if set(active_entries) != set(candidate_entries):
            raise BatchRejected("CHECKPOINT_LAYOUT_CHANGED")
        changed = tuple(
            name
            for name in sorted(active_entries)
            if active_entries[name] != candidate_entries[name]
        )
        candidate_artifact_value = intent.get("candidate_artifact")
        gradient_artifact_value = intent.get("gradient_artifact")
        try:
            expected_model_intent_id = content_id(
                "intent-model",
                {
                    "tick": intent.get("tick"),
                    "model_id": intent.get("model_id"),
                    "expected_model_digest": intent.get(
                        "expected_model_digest"
                    ),
                    "update_kind": _text(intent.get("update_kind")),
                    "candidate_model_digest": candidate_artifact_value.get(
                        "sha256"
                    ),
                    "gradient_digest": (
                        None
                        if gradient_artifact_value is None
                        else gradient_artifact_value.get("sha256")
                    ),
                    "parameter_names": list(changed),
                    "parameter_group_ids": list(
                        intent.get("parameter_group_ids", ())
                    ),
                    "plasticity_ppm": intent.get("plasticity_ppm"),
                    "verifier_receipt_id": intent.get(
                        "verifier_receipt_id"
                    ),
                    "qualification_receipt_id": intent.get(
                        "qualification_receipt_id"
                    ),
                },
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise BatchRejected("MODEL_INTENT_IDENTITY_INVALID") from error
        if intent_id != expected_model_intent_id:
            raise BatchRejected("MODEL_INTENT_IDENTITY_INVALID")
        declared_changed = qualification.get("changed_parameter_names")
        if (
            not changed
            or not isinstance(declared_changed, list)
            or tuple(declared_changed) != changed
            or tuple(model_manifest["changed_parameter_names"]) != changed
        ):
            raise BatchRejected("QUALIFICATION_PARAMETER_DIFF_MISMATCH")
        allowed_prefixes = tuple(
            prefix
            for group in sorted(groups)
            for prefix in self.parameter_scope_prefixes.get(group, ())
        )
        expected_allowed = tuple(
            name
            for name in sorted(active_entries)
            if allowed_prefixes and name.startswith(allowed_prefixes)
        )
        declared_allowed = qualification.get("allowed_parameter_names")
        if (
            not allowed_prefixes
            or any(not name.startswith(allowed_prefixes) for name in changed)
            or not isinstance(declared_allowed, list)
            or tuple(declared_allowed) != expected_allowed
            or not set(changed).issubset(expected_allowed)
        ):
            raise BatchRejected("CHECKPOINT_PARAMETER_SCOPE_ESCAPE")

        for old in before.biases:
            new = after.by_bias_id[old.bias_id]
            if self.coordinator_id not in old.governance.state_write_authorities:
                raise BatchRejected("COORDINATOR_HAS_NO_GLOBAL_MODEL_PROPAGATION_GRANT")
            if "write_bias" not in old.governance.hard_permissions:
                raise BatchRejected("GLOBAL_MODEL_PROPAGATION_NOT_PERMITTED")
            if (
                new.theta.model_id != before.model_id
                or new.theta.model_version != after.model_version
                or new.theta.model_digest != after.model_digest
                or after.model_artifact_ref not in new.theta.parameter_artifacts
            ):
                raise BatchRejected("GLOBAL_MODEL_POINTER_NOT_PROPAGATED")
        return [intent_id], [intent], after.model_digest

    def _effects(
        self,
        batch: NetworkCommitBatch,
        before: NetworkStateEnvelope,
        candidates: Mapping[str, Mapping[str, Any]],
        by_candidate: Mapping[str, Mapping[str, Any]],
        commit_receipt_id: str,
    ) -> tuple[StoredDocument, ...]:
        accepted = [
            (candidate_id, candidate, by_candidate[candidate_id])
            for candidate_id, candidate in candidates.items()
            if _text(by_candidate[candidate_id].get("disposition")) == "ACCEPT"
            and _text(by_candidate[candidate_id].get("semantic_outcome")) == "INTENDED"
        ]
        if accepted and batch.effect_publication_capability != REQUEST_EFFECT_PUBLICATION:
            raise BatchRejected("EFFECT_PUBLICATION_CAPABILITY_INVALID")
        documents: list[StoredDocument] = []
        for candidate_id, candidate, receipt in accepted:
            bias = before.by_bias_id[str(candidate["bias_id"])]
            contract = self.operation_contracts.get(
                str(candidate["operation_contract_id"])
            )
            if (
                contract is None
                or contract.ontology_status is not OntologyStatus.CANONICAL_ADMITTED
                or "PROPOSE_EFFECT" not in contract.legal_actions
            ):
                raise BatchRejected("EFFECT_PUBLICATION_NOT_LEGAL")
            if self.coordinator_id not in bias.governance.effect_publication_authorities:
                raise BatchRejected("COORDINATOR_HAS_NO_EFFECT_PUBLICATION_GRANT")
            if (
                "publish_effect" not in bias.governance.hard_permissions
                or "execute" not in bias.governance.hard_permissions
                or bias.governance.quarantined
            ):
                raise BatchRejected("EFFECT_PUBLICATION_NOT_PERMITTED")
            provenance = tuple(
                dict.fromkeys(
                    (
                        *candidate.get("provenance", []),
                        str(receipt["receipt_id"]),
                        self.authority_contract_id,
                    )
                )
            )
            core: dict[str, Any] = {
                "contract_type": PublishedEffect.CONTRACT_TYPE,
                "schema_version": PublishedEffect.SCHEMA_VERSION,
                "published_effect_id": "pending",
                "candidate_effect_id": candidate_id,
                "tick": batch.tick,
                "producer_cjt_id": candidate["producer_cjt_id"],
                "content": candidate["content"],
                "content_ref": candidate.get("content_ref"),
                "verifier_receipt_id": receipt["receipt_id"],
                "commit_receipt_id": commit_receipt_id,
                "provenance": list(provenance),
                "authoritative": True,
            }
            identity = canonical_digest(core)
            core["published_effect_id"] = f"effect-{identity[:24]}"
            core["publication_digest"] = canonical_digest(core)
            content_ref = core["content_ref"]
            if isinstance(content_ref, Mapping):
                names = {item.name for item in dataclass_fields(TensorArtifactRef)}
                content_ref = TensorArtifactRef(
                    **{key: value for key, value in content_ref.items() if key in names}
                )
            effect = PublishedEffect(
                **{
                    key: content_ref if key == "content_ref" else value
                    for key, value in core.items()
                    if key not in {"contract_type", "schema_version"}
                }
            )
            if not verify_declared_digest(effect, "publication_digest"):
                raise BatchRejected("PUBLISHED_EFFECT_DIGEST_INVALID")
            documents.append(StoredDocument(effect.published_effect_id, effect))
        return tuple(documents)

    def _artifacts(
        self, batch: NetworkCommitBatch, values: Iterable[Any]
    ) -> None:
        supplied = {item.artifact_id: item for item in batch.artifacts}
        if len(supplied) != len(batch.artifacts):
            raise BatchRejected("ARTIFACT_ID_DUPLICATE")
        try:
            for artifact in supplied.values():
                artifact.verify()
        except ArtifactError as error:
            raise BatchRejected("ARTIFACT_INVALID") from error
        for value in values:
            for artifact_id, digest in _artifact_references(value):
                artifact = supplied.get(artifact_id)
                if artifact is not None:
                    if artifact.sha256 != digest:
                        raise BatchRejected("ARTIFACT_REFERENCE_DIGEST_MISMATCH")
                elif not self.store.has_artifact(artifact_id, digest):
                    raise BatchRejected("ARTIFACT_REFERENCE_NOT_RETAINED")
        if batch.model_version is not None:
            artifact = supplied.get(batch.model_version.artifact_id)
            if artifact is None and not self.store.has_artifact(
                batch.model_version.artifact_id, batch.model_version.model_digest
            ):
                raise BatchRejected("MODEL_ARTIFACT_NOT_RETAINED")

    def _trace(
        self,
        batch: NetworkCommitBatch,
        *,
        request_digest: str,
        receipt_id: str,
        published_ids: Sequence[str],
        repair_ids: Sequence[str],
        repair_outcome_ids: Sequence[str],
        accepted_intent_ids: Sequence[str],
        post_model_digest: str,
        audit_document: StoredDocument | None,
    ) -> SealedTrace:
        # Full inputs, decisions, and proposals are intentionally retained in
        # the private trace so an offline process can reconstruct the batch.
        payload = {
            "tick": batch.tick,
            "runtime_id": batch.runtime_id,
            "software_digest": batch.software_digest,
            "cause_id": batch.cause.cause_id,
            "cjt_ids": list(batch.cjt_ids),
            "pre_state_digest": batch.state_before.state_digest,
            "post_state_digest": batch.state_after.state_digest,
            "pre_model_digest": batch.state_before.model_digest,
            "post_model_digest": post_model_digest,
            "phases": list(batch.phase_records),
            "candidate_effect_ids": [
                item.candidate_effect_id for item in batch.candidate_effects
            ],
            "published_effect_ids": list(published_ids),
            "verifier_receipt_ids": [item.receipt_id for item in batch.verifier_receipts],
            "commit_receipt_id": receipt_id,
            "memory_read_refs": list(batch.memory_read_refs),
            "memory_write_refs": [item.memory_record_id for item in batch.memory_intents],
            "accepted_intent_ids": list(accepted_intent_ids),
            "rejected_intent_ids": [],
            "repair_frame_ids": list(repair_ids),
            "repair_outcome_ids": list(repair_outcome_ids),
            "sealed": True,
            "network_request_digest": request_digest,
            "state_before": batch.state_before.to_dict(),
            "state_after": batch.state_after.to_dict(),
            "cause": batch.cause.to_dict(),
            "candidate_effects": [item.to_dict() for item in batch.candidate_effects],
            "verifier_receipts": [item.to_dict() for item in batch.verifier_receipts],
            "state_intents": [
                *[item.to_dict() for item in batch.state_intents],
                *(
                    []
                    if audit_document is None
                    else [_wire(audit_document.payload, label="audit transition")]
                ),
            ],
            "model_intents": [item.to_dict() for item in batch.model_intents],
            "memory_intents": [item.to_dict() for item in batch.memory_intents],
            "repair_frames": [item.to_dict() for item in batch.repair_frames],
            "repair_outcomes": [item.to_dict() for item in batch.repair_outcomes],
            "qualification_receipts": [
                _wire(item, label="qualification receipt")
                for item in batch.qualification_receipts
            ],
            "semantic_evidence": [
                _wire(item, label="semantic evidence")
                for item in batch.semantic_evidence
            ],
            "decoder_contract": None
            if batch.decoder_contract is None
            else _wire(batch.decoder_contract, label="decoder contract"),
            "artifacts": [item.public_descriptor() for item in batch.artifacts],
            "model_version": None
            if batch.model_version is None
            else {
                "model_digest": batch.model_version.model_digest,
                "parent_model_digest": batch.model_version.parent_model_digest,
                "artifact_id": batch.model_version.artifact_id,
                "payload": _wire(batch.model_version.payload, label="model version"),
            },
            "compute_plan": dict(batch.compute_plan),
            "compute_observations": dict(batch.compute_observations),
            "audit_transition": None
            if not batch.audit_only
            else {
                "contract_type": "AUDIT_TRANSITION_INTENT",
                "schema_version": "cas.neural-cjt.audit-transition/0.2",
                "audit_id": f"audit-{request_digest[:24]}",
                "reason_codes": list(batch.audit_reason_codes),
                "bias_and_model_bytes_unchanged": True,
            },
        }
        return seal_trace(
            payload,
            previous_trace_digest=batch.base_trace_digest,
            sensitive_fields=batch.sensitive_trace_fields,
        )

    def _receipt(
        self,
        *,
        receipt_id: str,
        batch: NetworkCommitBatch,
        trace_id: str,
        post_model_digest: str,
        accepted_intent_ids: Sequence[str],
        published_effect_ids: Sequence[str],
        repair_ids: Sequence[str],
    ) -> CommitReceipt:
        data = {
            "receipt_id": receipt_id,
            "tick": batch.tick,
            "batch_id": batch.batch_id,
            "coordinator_id": self.coordinator_id,
            "authority_contract_id": self.authority_contract_id,
            "authorized": True,
            "disposition": CommitDisposition.COMMITTED,
            "pre_state_digest": batch.state_before.state_digest,
            "post_state_digest": batch.state_after.state_digest,
            "pre_model_digest": batch.state_before.model_digest,
            "post_model_digest": post_model_digest,
            "accepted_intent_ids": tuple(accepted_intent_ids),
            "rejected_intent_ids": (),
            "published_effect_ids": tuple(published_effect_ids),
            "opened_repair_ids": tuple(repair_ids),
            "reason_codes": (
                "AUTHORIZED_GOVERNED_AUDIT_TRANSITION"
                if batch.audit_only
                else "AUTHORIZED_GLOBAL_ATOMIC_COMMIT",
            ),
            "atomic": True,
            "rollback_of_receipt_id": None,
            "persisted_snapshot_id": f"snapshot-{batch.state_after.state_digest[:24]}",
            "trace_id": trace_id,
        }
        digest_payload = {
            "contract_type": CommitReceipt.CONTRACT_TYPE,
            "schema_version": CommitReceipt.SCHEMA_VERSION,
            **data,
        }
        data["receipt_digest"] = canonical_digest(digest_payload)
        receipt = CommitReceipt(**data)
        if not verify_declared_digest(receipt, "receipt_digest"):
            raise BatchRejected("COMMIT_RECEIPT_DIGEST_INVALID")
        return receipt

    def _qualification_documents(
        self, batch: NetworkCommitBatch
    ) -> tuple[StoredDocument, ...]:
        documents: list[StoredDocument] = []
        identities: set[str] = set()
        for value in batch.qualification_receipts:
            payload = _wire(value, label="qualification receipt")
            identity = payload.get("qualification_receipt_id")
            if (
                not isinstance(identity, str)
                or not identity
                or identity in identities
            ):
                raise BatchRejected("QUALIFICATION_RECEIPT_IDENTITY_INVALID")
            identities.add(identity)
            _require_digest(payload, "receipt_digest", "qualification receipt")
            documents.append(StoredDocument(identity, payload))
        return tuple(documents)

    def _audit_transition_document(
        self,
        batch: NetworkCommitBatch,
        *,
        request_digest: str,
    ) -> StoredDocument:
        identity = f"audit-transition-{request_digest[:24]}"
        body = {
            "contract_type": "AUDIT_TRANSITION_INTENT",
            "schema_version": "cas.neural-cjt.audit-transition-intent/0.2",
            "intent_id": identity,
            "tick": batch.tick,
            "issuer_id": self.coordinator_id,
            "authority_capability": PROPOSE_STATE_UPDATE,
            "expected_state_version": batch.state_before.state_version,
            "expected_state_digest": batch.state_before.state_digest,
            "proposed_state_version": batch.state_after.state_version,
            "proposed_state_digest": batch.state_after.state_digest,
            "reason_codes": list(batch.audit_reason_codes),
            "bias_and_model_bytes_unchanged": True,
        }
        return StoredDocument(identity, {**body, "intent_digest": canonical_digest(body)})

    def _record_rejection(
        self,
        batch: NetworkCommitBatch,
        *,
        request_payload: Mapping[str, Any],
        request_digest: str,
        reason_codes: Sequence[str],
    ) -> None:
        head = self.store.head
        rejected_intent_ids = [
            item.intent_id
            for collection in (
                batch.state_intents,
                batch.model_intents,
                batch.memory_intents,
            )
            for item in collection
        ]
        self.store.record_rejection(
            batch_id=batch.batch_id,
            request_digest=request_digest,
            payload={
                "tick": batch.tick,
                "runtime_id": batch.runtime_id,
                "software_digest": batch.software_digest,
                "cause_id": batch.cause.cause_id,
                "cjt_ids": list(batch.cjt_ids),
                "pre_state_digest": head.state_digest,
                "post_state_digest": head.state_digest,
                "pre_state_version": head.state_version,
                "post_state_version": head.state_version,
                "pre_model_digest": head.model_digest,
                "post_model_digest": head.model_digest,
                "active_trace_digest": head.trace_digest,
                "active_commit_receipt_id": head.commit_receipt_id,
                "candidate_effect_ids": [
                    item.candidate_effect_id for item in batch.candidate_effects
                ],
                "verifier_receipt_ids": [
                    item.receipt_id for item in batch.verifier_receipts
                ],
                "accepted_intent_ids": [],
                "rejected_intent_ids": list(dict.fromkeys(rejected_intent_ids)),
                "published_effect_ids": [],
                "opened_repair_ids": [],
                "reason_codes": list(dict.fromkeys(reason_codes)),
                "atomic_rollback": True,
                "request": dict(request_payload),
            },
            sensitive_fields=batch.sensitive_trace_fields,
        )

    def _commit_authoritative(
        self, batch: NetworkCommitBatch, *, fault_at: str | None = None
    ) -> CommitReceipt:
        """Validate all CJTs first; commit all records once or commit nothing."""

        request_payload = self._request_payload(batch)
        request_digest = canonical_digest(request_payload)
        prior = self._idempotent(batch.batch_id, request_digest)
        if prior is not None:
            return prior
        before, after, head = self._common(batch)
        candidates, receipts, by_candidate = self._candidates(batch, before)
        evidence_by_receipt = self._semantic_evidence(
            batch, candidates, receipts
        )
        self._recompute_verifier_receipts(
            batch, before, evidence_by_receipt
        )
        self._validate_memory_reads(batch, before)
        repair_documents = self._repairs(
            batch, before, after, candidates, receipts
        )
        repair_outcome_documents = self._repair_outcomes(
            batch, before, after, candidates, receipts
        )
        state_ids, state_values = self._state_intents(
            batch,
            before,
            after,
            candidates,
            receipts,
            repair_documents,
            repair_outcome_documents,
        )
        memory_ids, memory_documents, memory_values = self._memory_intents(
            batch, before, candidates, receipts
        )
        model_ids, model_values, post_model_digest = self._model_intents(
            batch, before, after, candidates, receipts
        )
        accepted_ids = [*state_ids, *memory_ids, *model_ids]
        receipt_id = f"commit-{request_digest[:24]}"
        effect_documents = self._effects(
            batch, before, candidates, by_candidate, receipt_id
        )
        if batch.audit_only:
            if (
                any(after.by_bias_id[key] != value for key, value in before.by_bias_id.items())
                or accepted_ids
                or effect_documents
                or repair_documents
                or repair_outcome_documents
                or batch.model_version is not None
                or any(
                    self.coordinator_id not in bias.governance.state_write_authorities
                    for bias in before.biases
                )
            ):
                raise BatchRejected("AUDIT_TRANSITION_HAS_COGNITIVE_WRITES")
            audit_document = self._audit_transition_document(
                batch, request_digest=request_digest
            )
            accepted_ids = [audit_document.record_id]
        else:
            audit_document = None
        if (
            not accepted_ids
            and not effect_documents
            and not repair_documents
            and not repair_outcome_documents
        ):
            raise BatchRejected("EMPTY_GLOBAL_COMMIT_FORBIDDEN")
        self._artifacts(
            batch,
            (request_payload,),
        )
        self._validate_candidate_artifacts(batch, by_candidate)
        self._validate_outcome_state_transitions(
            batch,
            before,
            after,
            receipts,
            state_values,
            repair_documents,
        )
        if head.model_digest != before.model_digest:
            raise StaleHeadError("global model is stale relative to the active head")
        published_ids = [item.record_id for item in effect_documents]
        repair_ids = [item.record_id for item in repair_documents]
        repair_outcome_ids = [item.record_id for item in repair_outcome_documents]
        trace = self._trace(
            batch,
            request_digest=request_digest,
            receipt_id=receipt_id,
            published_ids=published_ids,
            repair_ids=repair_ids,
            repair_outcome_ids=repair_outcome_ids,
            accepted_intent_ids=accepted_ids,
            post_model_digest=post_model_digest,
            audit_document=audit_document,
        )
        receipt = self._receipt(
            receipt_id=receipt_id,
            batch=batch,
            trace_id=trace.trace_id,
            post_model_digest=post_model_digest,
            accepted_intent_ids=accepted_ids,
            published_effect_ids=published_ids,
            repair_ids=repair_ids,
        )
        qualification_documents = self._qualification_documents(batch)
        state_documents = tuple(
            StoredDocument(str(payload["intent_id"]), payload)
            for payload in state_values
        )
        if audit_document is not None:
            state_documents = (*state_documents, audit_document)
        stored = self.store.commit(
            AtomicWriteSet(
                batch_id=batch.batch_id,
                request_digest=request_digest,
                expected_state_digest=before.state_digest,
                expected_state_version=before.state_version,
                expected_trace_digest=batch.base_trace_digest,
                expected_model_digest=before.model_digest,
                post_state_digest=after.state_digest,
                post_state_version=after.state_version,
                post_state=after.to_dict(),
                post_model_digest=post_model_digest,
                trace=trace,
                receipt_id=receipt.receipt_id,
                receipt=receipt,
                transition_batch=StoredDocument(batch.batch_id, request_payload),
                causes=(StoredDocument(batch.cause.cause_id, batch.cause),),
                candidate_effects=tuple(
                    StoredDocument(identity, payload)
                    for identity, payload in candidates.items()
                ),
                verifier_receipts=tuple(
                    StoredDocument(identity, payload)
                    for identity, payload in receipts.items()
                ),
                qualification_receipts=qualification_documents,
                state_intents=state_documents,
                model_intents=tuple(
                    StoredDocument(str(payload["intent_id"]), payload)
                    for payload in model_values
                ),
                memory_intents=tuple(
                    StoredDocument(str(payload["intent_id"]), payload)
                    for payload in memory_values
                ),
                artifacts=batch.artifacts,
                published_effects=effect_documents,
                memory_records=memory_documents,
                repair_frames=repair_documents,
                repair_outcomes=repair_outcome_documents,
                model_version=batch.model_version,
            ),
            fault_at=fault_at,
        )
        return CommitReceipt(**_receipt_kwargs(stored))

    def commit(
        self, batch: NetworkCommitBatch, *, fault_at: str | None = None
    ) -> CommitReceipt:
        """Commit a valid network batch or append only a rejection audit."""

        request_payload = self._request_payload(batch)
        request_digest = canonical_digest(request_payload)
        try:
            return self._commit_authoritative(batch, fault_at=fault_at)
        except BatchRejected as error:
            self._record_rejection(
                batch,
                request_payload=request_payload,
                request_digest=request_digest,
                reason_codes=error.reason_codes,
            )
            raise
        except StaleHeadError:
            self._record_rejection(
                batch,
                request_payload=request_payload,
                request_digest=request_digest,
                reason_codes=("STALE_ACTIVE_HEAD",),
            )
            raise

    def restore_and_verify(self) -> NetworkRecoverySnapshot:
        if not self.store.verify_integrity():
            raise PersistenceError("durable network history failed integrity checks")
        head = self.store.head
        state = self.store.load_state()
        try:
            rebuilt = NetworkStateEnvelope.from_dict(state)
        except ValueError as error:
            raise PersistenceError("active network envelope is malformed") from error
        if (
            rebuilt.state_version != head.state_version
            or rebuilt.state_digest != head.state_digest
            or rebuilt.model_digest != head.model_digest
        ):
            raise PersistenceError("active network envelope does not match its head")
        traces = self.store.trace_events()
        if traces and not verify_trace_chain(traces):
            raise PersistenceError("durable network trace chain is invalid")
        return NetworkRecoverySnapshot(head, state, traces)


__all__ = [
    "NetworkAtomicCoordinator",
    "NetworkBatchRejected",
    "NetworkCommitBatch",
    "NetworkRecoverySnapshot",
    "NetworkStateEnvelope",
]
