"""Integrated Neural CJT network inference and governed learning runtime."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor

from casformer import CASformerConfig

from .artifacts import StoredArtifact, encode_tensor
from .checkpoint import (
    CheckpointBundle,
    encode_module_checkpoint,
    load_module_checkpoint,
)
from .contracts import canonical_digest
from .control import BiasControlMaterializer, MaterializedControl, RouteSettings
from .learning import (
    GovernedLearner,
    LearningPolicy,
    LearningProposal,
    LossFunction,
    ScoreFunction,
)
from .memory import propose_memory_write
from .network import CJTNodeSpec, NeuralCJTNetwork, TopologyEdge
from .network_coordinator import (
    NetworkAtomicCoordinator,
    NetworkCommitBatch,
    NetworkStateEnvelope,
)
from .persistence import ModelVersionWrite, SQLiteAtomicStore
from .phase_contract import validate_phase_contract
from .proposals import (
    freeze_candidate_effect,
    phase_records,
    state_update_intents_for_successor,
)
from .repair import make_repair_outcome, open_repair, repair_frame_from_dict
from .routing import (
    PostExecutionObservation,
    allocate_global_charge_tensor,
    bounded_mean_flow_ppm,
)
from .semantic import (
    DecoderContract,
    DeterministicSemanticDecoder,
    make_bound_evidence,
    validate_operation_io,
)
from .state import (
    advance_bias,
    bias_from_dict,
    cause_from_committed_effect,
    content_id,
    make_cause,
    make_initial_bias,
    make_operation_contract,
    tensor_ref_from_mapping,
    verify_cause_identity,
)
from .types import (
    BiasState,
    CandidateEffect,
    CauseKind,
    CausePacket,
    CommitReceipt,
    MemoryKind,
    OperatingRegion,
    OperationContract,
    PublishedEffect,
    RepairFrame,
    RepairOutcome,
    SemanticOutcome,
    TickPhase,
    VerifierDisposition,
    VerifierReceipt,
)
from .verifier import IndependentVerifier


RUNTIME_ID = "cas-neural-cjt-runtime/0.2"
AUTHORITY_CONTRACT_ID = "cas-neural-cjt-research-authority/0.2"
COORDINATOR_ID = "prototype-atomic-coordinator"
EVIDENCE_SOURCE_ID = "prototype-fixed-oracle"


class RuntimeContractError(RuntimeError):
    """The integrated runtime could not complete a governed tick."""


@dataclass(frozen=True)
class InferenceTickResult:
    tick: int
    cjt_id: str
    cause: CausePacket
    bias_before: BiasState
    bias_after: BiasState
    candidate_effect: CandidateEffect
    verifier_receipt: VerifierReceipt
    commit_receipt: CommitReceipt
    published_effect: Mapping[str, Any] | None
    repair_frame: RepairFrame | None
    repair_subgoal: CausePacket | None
    repair_outcome: RepairOutcome | None
    materialized: MaterializedControl

    @property
    def accepted(self) -> bool:
        return self.verifier_receipt.disposition is VerifierDisposition.ACCEPT


@dataclass(frozen=True)
class LearningTickResult:
    tick: int
    cjt_id: str
    inference: InferenceTickResult | None
    learning_proposal: LearningProposal
    bias_before: BiasState
    bias_after: BiasState
    commit_receipt: CommitReceipt
    pre_model_digest: str
    post_model_digest: str


@dataclass(frozen=True)
class _PreparedInference:
    state: NetworkStateEnvelope
    bias: BiasState
    contract: OperationContract
    decoder: DeterministicSemanticDecoder
    evidence_descriptor: Mapping[str, Any]
    materialized: MaterializedControl
    candidate_effect: CandidateEffect
    candidate_artifact: StoredArtifact
    verifier_receipt: VerifierReceipt
    next_bias: BiasState
    recurrent_artifact: StoredArtifact | None
    repair_frame: RepairFrame | None
    repair_subgoal: CausePacket | None
    repair_outcome: RepairOutcome | None
    memory_intents: tuple[Any, ...]
    region: OperatingRegion
    audit_only: bool


def _unique_artifacts(values: Sequence[StoredArtifact]) -> tuple[StoredArtifact, ...]:
    result: dict[str, StoredArtifact] = {}
    for value in values:
        previous = result.get(value.artifact_id)
        if previous is not None and previous.sha256 != value.sha256:
            raise RuntimeContractError("artifact identity collision")
        result[value.artifact_id] = value
    return tuple(result[key] for key in sorted(result))


def _int_values(value: Tensor) -> Any:
    return value.detach().to(device="cpu").tolist()


def _reseal_bias(bias: BiasState) -> BiasState:
    draft = replace(bias, state_digest="0" * 64)
    return replace(
        draft,
        state_digest=canonical_digest(draft.to_dict(), omit_keys=("state_digest",)),
    )


def _region(materialized: MaterializedControl, proposal: Any) -> OperatingRegion:
    values = set(int(item) for item in proposal.telemetry.operating_region.detach().cpu().reshape(-1))
    if 3 in values:
        return OperatingRegion.BREAKDOWN
    if not bool((materialized.routing.total_current > 0).any().item()):
        return OperatingRegion.CUTOFF
    if 2 in values:
        return OperatingRegion.SATURATION
    if 1 in values:
        return OperatingRegion.ACTIVE
    return OperatingRegion.CUTOFF


def _state_from_wire(value: Mapping[str, Any]) -> NetworkStateEnvelope:
    from_dict = getattr(NetworkStateEnvelope, "from_dict", None)
    if callable(from_dict):
        return from_dict(value)
    return NetworkStateEnvelope(
        state_version=value["state_version"],
        previous_state_digest=value["previous_state_digest"],
        model_id=value["model_id"],
        model_version=value["model_version"],
        model_digest=value["model_digest"],
        model_artifact_ref=tensor_ref_from_mapping(value["model_artifact_ref"]),
        biases=tuple(bias_from_dict(item) for item in value["biases"]),
        state_digest=value["state_digest"],
    )


def _model_config_wire(config: CASformerConfig) -> dict[str, Any]:
    return {
        "d_model": config.d_model,
        "num_heads": config.num_heads,
        "num_relations": config.num_relations,
        "num_layers": config.num_layers,
        "d_ff": config.d_ff,
        "dropout": str(config.dropout),
        "attention_dropout": str(config.attention_dropout),
        "minimum_total_resistance": str(config.minimum_total_resistance),
        "reference_resistance": str(config.reference_resistance),
        "reference_drive": str(config.reference_drive),
        "initial_beta": str(config.initial_beta),
        "beta_max": str(config.beta_max),
        "initial_cutoff": str(config.initial_cutoff),
        "initial_saturation": str(config.initial_saturation),
        "linear_weight_mode": config.linear_weight_mode,
        "minimum_weight_resistance": str(config.minimum_weight_resistance),
    }


def _model_manifest_context(
    network: NeuralCJTNetwork,
    decoder_labels: Sequence[str],
) -> dict[str, Any]:
    return {
        "network": network.topology_manifest(),
        "config": _model_config_wire(network.config),
        "decoder_labels": list(decoder_labels),
    }


def _model_manifest(
    network: NeuralCJTNetwork,
    checkpoint: CheckpointBundle,
    *,
    model_id: str,
    model_version: int,
    decoder_labels: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema_version": "cas.neural-cjt.model-version/0.2",
        "model_id": model_id,
        "model_version": model_version,
        "model_digest": checkpoint.model_digest,
        "model_artifact_ref": checkpoint.reference.to_dict(),
        **_model_manifest_context(network, decoder_labels),
    }


class NeuralCJTRuntime:
    """One global model, many persistent Biases, one atomic authority head."""

    def __init__(
        self,
        *,
        store: SQLiteAtomicStore,
        network: NeuralCJTNetwork,
        contracts: Mapping[str, OperationContract],
        decoders: Mapping[str, DeterministicSemanticDecoder],
    ) -> None:
        self.store = store
        self.network = network
        self.contracts = dict(contracts)
        self.decoders = dict(decoders)
        decoder_label_sets = {
            tuple(decoder.contract.labels) for decoder in self.decoders.values()
        }
        if len(decoder_label_sets) != 1:
            raise RuntimeContractError(
                "all admitted decoders must share one nonempty label set"
            )
        decoder_labels = next(iter(decoder_label_sets))
        self.verifier = IndependentVerifier("independent-effect-verifier")
        self.software_digest = canonical_digest(
            {
                "runtime_id": RUNTIME_ID,
                "authority_contract_id": AUTHORITY_CONTRACT_ID,
                "topology": network.topology_manifest(),
                "operation_contracts": {
                    key: value.contract_digest for key, value in sorted(self.contracts.items())
                },
                "decoders": {
                    key: value.contract.decoder_digest
                    for key, value in sorted(self.decoders.items())
                },
            }
        )

        def candidate_validator(candidate: CandidateEffect, artifact: StoredArtifact) -> bool:
            decoder = self.decoders.get(candidate.producer_cjt_id)
            return decoder is not None and decoder.validate_candidate(candidate, artifact)

        scope_prefixes: dict[str, tuple[str, ...]] = {}
        for spec in network.node_specs:
            operation_names = network.parameter_names_for_node(spec.cjt_id)
            bias_names = network.parameter_names_for_node(
                spec.cjt_id, include_bias_head=True
            )
            bias_only = tuple(name for name in bias_names if "bias_update_head" in name)
            scope_prefixes[f"cjt:{spec.cjt_id}:operation:{spec.operation_id}"] = operation_names
            scope_prefixes[f"cjt:{spec.cjt_id}:bias_update_head"] = bias_only
        self.coordinator = NetworkAtomicCoordinator(
            store,
            coordinator_id=COORDINATOR_ID,
            authority_contract_id=AUTHORITY_CONTRACT_ID,
            runtime_id=RUNTIME_ID,
            software_digest=self.software_digest,
            num_attention_heads=network.config.num_heads,
            model_manifest_context=_model_manifest_context(
                network,
                decoder_labels,
            ),
            operation_contracts={
                contract.contract_id: contract
                for contract in self.contracts.values()
            },
            decoder_contracts={
                cjt_id: decoder.contract
                for cjt_id, decoder in self.decoders.items()
            },
            permitted_topology_edges=tuple(
                (str(edge["source_cjt_id"]), str(edge["target_cjt_id"]))
                for edge in network.topology_manifest()["edges"]
                if edge["permitted"] is True
            ),
            trusted_evidence_sources=(EVIDENCE_SOURCE_ID,),
            candidate_validator=candidate_validator,
            parameter_scope_prefixes=scope_prefixes,
        )
        self.materializer = BiasControlMaterializer(network, store)

    @classmethod
    def create(
        cls,
        path: str | Path,
        *,
        config: CASformerConfig,
        node_specs: Sequence[CJTNodeSpec],
        topology: Sequence[TopologyEdge],
        seed: int = 7,
        labels: Sequence[str] | None = None,
        model_id: str = "cas-cjt-network-model",
    ) -> "NeuralCJTRuntime":
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            network = NeuralCJTNetwork(config, node_specs, topology=topology)
        checkpoint = encode_module_checkpoint(network)
        contracts = {
            operation_id: make_operation_contract(operation_id)
            for operation_id in sorted({item.operation_id for item in node_specs})
        }
        label_values = tuple(labels) if labels is not None else tuple(
            f"CLASS_{index}" for index in range(config.d_model)
        )
        if len(label_values) != config.d_model:
            raise RuntimeContractError("decoder label count must equal d_model")
        decoders: dict[str, DeterministicSemanticDecoder] = {}
        biases = []
        for spec in node_specs:
            contract = contracts[spec.operation_id]
            effect_kind = contract.effect_schema_id.rsplit(":", 1)[-1]
            decoders[spec.cjt_id] = DeterministicSemanticDecoder(
                DecoderContract(
                    decoder_id=f"decoder:{spec.cjt_id}",
                    version=1,
                    operation_id=spec.operation_id,
                    effect_kind=effect_kind,
                    labels=label_values,
                )
            )
            biases.append(
                make_initial_bias(
                    cjt_id=spec.cjt_id,
                    operation_id=spec.operation_id,
                    model_id=model_id,
                    model_digest=checkpoint.model_digest,
                    checkpoint_ref=checkpoint.reference,
                    beta_microunits=int(round(config.initial_beta * 1_000_000)),
                )
            )
        state = NetworkStateEnvelope.create(
            biases,
            model_id=model_id,
            model_version=0,
            model_digest=checkpoint.model_digest,
            model_artifact_ref=checkpoint.reference,
        )
        store = SQLiteAtomicStore(path)
        root_model = ModelVersionWrite(
            model_digest=checkpoint.model_digest,
            parent_model_digest=None,
            artifact_id=checkpoint.reference.artifact_id,
            payload=_model_manifest(
                network,
                checkpoint,
                model_id=model_id,
                model_version=0,
                decoder_labels=label_values,
            ),
        )
        store.initialize(
            state_digest=state.state_digest,
            state_version=state.state_version,
            state_payload=state.to_dict(),
            model_digest=checkpoint.model_digest,
            initial_artifacts=(checkpoint.artifact,),
            initial_model_version=root_model,
        )
        runtime = cls(
            store=store,
            network=network,
            contracts=contracts,
            decoders=decoders,
        )
        runtime.coordinator.restore_and_verify()
        return runtime

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        config: CASformerConfig,
        node_specs: Sequence[CJTNodeSpec],
        topology: Sequence[TopologyEdge],
        labels: Sequence[str] | None = None,
    ) -> "NeuralCJTRuntime":
        network = NeuralCJTNetwork(config, node_specs, topology=topology)
        store = SQLiteAtomicStore(path)
        state = _state_from_wire(store.load_state())
        checkpoint_artifact = store.load_artifact(state.model_artifact_ref.artifact_id)
        load_module_checkpoint(network, state.model_artifact_ref, checkpoint_artifact)
        contracts = {
            operation_id: make_operation_contract(operation_id)
            for operation_id in sorted({item.operation_id for item in node_specs})
        }
        label_values = tuple(labels) if labels is not None else tuple(
            f"CLASS_{index}" for index in range(config.d_model)
        )
        decoders = {
            spec.cjt_id: DeterministicSemanticDecoder(
                DecoderContract(
                    decoder_id=f"decoder:{spec.cjt_id}",
                    version=1,
                    operation_id=spec.operation_id,
                    effect_kind=contracts[spec.operation_id].effect_schema_id.rsplit(":", 1)[-1],
                    labels=label_values,
                )
            )
            for spec in node_specs
        }
        persisted_manifest = store.model_version_record(state.model_digest)
        expected_manifest = _model_manifest(
            network,
            CheckpointBundle(state.model_artifact_ref, checkpoint_artifact),
            model_id=state.model_id,
            model_version=state.model_version,
            decoder_labels=label_values,
        )
        for key in (
            "schema_version",
            "model_id",
            "model_version",
            "model_digest",
            "model_artifact_ref",
            "network",
            "config",
            "decoder_labels",
        ):
            if persisted_manifest.get(key) != expected_manifest[key]:
                store.close()
                raise RuntimeContractError(
                    f"restart configuration does not match persisted {key}"
                )
        runtime = cls(
            store=store,
            network=network,
            contracts=contracts,
            decoders=decoders,
        )
        runtime.coordinator.restore_and_verify()
        return runtime

    def close(self) -> None:
        self.store.close()

    @property
    def state(self) -> NetworkStateEnvelope:
        return _state_from_wire(self.store.load_state())

    def make_input_cause(
        self,
        tensor: Tensor,
        *,
        tick: int,
        content: Mapping[str, Any],
        goal_context: Mapping[str, Any],
        candidate_operation_ids: Sequence[str] = ("^6",),
        cause_kind: CauseKind = CauseKind.IDEA,
        source: str = "prototype:user-input",
        provenance: Sequence[str] = ("prototype:local-input",),
        uncertainty_ppm: int = 0,
        entity_bindings: Sequence[str] = (),
        relation_bindings: Sequence[str] = (),
        memory_refs: Sequence[str] = (),
        originating_modality: str | None = None,
    ) -> tuple[CausePacket, StoredArtifact]:
        reference, artifact = encode_tensor(tensor, kind="cause-input")
        cause = make_cause(
            tick=tick,
            content=content,
            goal_context=goal_context,
            cause_kind=cause_kind,
            candidate_operation_ids=candidate_operation_ids,
            source=source,
            provenance=provenance,
            uncertainty_ppm=uncertainty_ppm,
            entity_bindings=entity_bindings,
            relation_bindings=relation_bindings,
            memory_refs=memory_refs,
            originating_modality=originating_modality,
            content_ref=tensor_ref_from_mapping(reference),
        )
        return cause, artifact

    def cause_from_effect(
        self,
        published_effect_id: str,
        *,
        tick: int,
        candidate_operation_ids: Sequence[str],
        goal_context: Mapping[str, Any],
    ) -> CausePacket:
        return cause_from_committed_effect(
            self.store,
            published_effect_id,
            tick=tick,
            candidate_operation_ids=candidate_operation_ids,
            goal_context=goal_context,
        )

    def _require_monotonic_tick(self, tick: int) -> None:
        traces = self.store.trace_events()
        if traces and tick != int(traces[-1]["tick"]) + 1:
            raise RuntimeContractError("runtime ticks must advance by exactly one")

    def _viable_repair_cjts(
        self,
        state: NetworkStateEnvelope,
        suspended_cjt_id: str,
    ) -> tuple[str, ...]:
        """Return durable ^6 executors with an eligible round trip."""

        source = state.by_cjt_id.get(suspended_cjt_id)
        if source is None or "cascade" not in source.governance.topology_permissions:
            return ()
        nonconducting_regions = {
            OperatingRegion.BREAKDOWN,
            OperatingRegion.NON_OHMIC,
            OperatingRegion.UNSTABLE,
        }
        viable: list[str] = []
        for candidate in state.biases:
            contract = self.contracts.get(
                candidate.stable.registered_operation_id
            )
            if (
                contract is None
                or candidate.cjt_id == suspended_cjt_id
                or contract.operation_id != "^6"
                or contract.ontology_status.value != "CANONICAL_ADMITTED"
                or CauseKind.RPM_SUBGOAL not in contract.accepted_cause_kinds
                or "PROPOSE_EFFECT" not in contract.legal_actions
                or not self.network.edge_permitted(suspended_cjt_id, candidate.cjt_id)
                or not self.network.edge_permitted(candidate.cjt_id, suspended_cjt_id)
                or "cascade" not in candidate.governance.topology_permissions
                or "execute" not in candidate.governance.hard_permissions
                or "publish_effect" not in candidate.governance.hard_permissions
                or COORDINATOR_ID
                not in candidate.governance.effect_publication_authorities
                or candidate.governance.quarantined
                or not candidate.rpm.readiness.hard_open
                or candidate.operating.region in nonconducting_regions
            ):
                continue
            viable.append(candidate.cjt_id)
        return tuple(sorted(viable))

    def _reserved_repair_frame(
        self,
        *,
        state: NetworkStateEnvelope,
        cause: CausePacket,
        cjt_id: str,
        resume_repair_id: str | None,
    ) -> RepairFrame | None:
        """Reserve t+1 for repair work and t+2 for its exact resumption."""

        open_ids = [
            repair_id
            for bias in state.biases
            for repair_id in bias.rpm.open_repair_ids
        ]
        if len(open_ids) > 1:
            raise RuntimeContractError("v0.2 permits one OPEN repair globally")
        if not open_ids:
            return None
        try:
            frame = repair_frame_from_dict(
                self.store.immutable_document("repair_frames", open_ids[0])
            )
            suspended = state.by_bias_id[frame.suspended_bias_id]
        except Exception as error:
            raise RuntimeContractError("global OPEN repair is not reconstructible") from error
        if (
            frame.status.value != "OPEN"
            or suspended.rpm.open_repair_ids != (frame.repair_id,)
            or suspended.rpm.suspended_parent_cause_id != frame.parent_cause_id
            or suspended.rpm.return_addresses != (frame.return_address,)
        ):
            raise RuntimeContractError("global OPEN repair cross-links are invalid")
        viable = self._viable_repair_cjts(state, suspended.cjt_id)
        if cause.tick == frame.eligible_tick:
            if (
                cause.cause_kind is not CauseKind.RPM_SUBGOAL
                or cause.cause_id != frame.subgoal_cause_id
                or cause.content.get("repair_id") != frame.repair_id
                or cjt_id not in viable
                or resume_repair_id is not None
            ):
                raise RuntimeContractError(
                    "the next global tick is reserved for the exact repair subgoal"
                )
            return frame
        if cause.tick != frame.eligible_tick + 1:
            raise RuntimeContractError("global OPEN repair missed its reserved stage")

        traces = self.store.trace_events()
        latest = traces[-1] if traces else None
        result_effects: list[Mapping[str, Any]] = []
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
                    raise RuntimeContractError(
                        "retained repair result is not reconstructible"
                    ) from error
                if (
                    candidate.get("parent_cause_id") == frame.subgoal_cause_id
                    and candidate.get("tick") == frame.eligible_tick
                ):
                    result_effects.append(effect)
        if len(result_effects) != 1:
            raise RuntimeContractError(
                "the open repair lacks exactly one accepted t+1 result"
            )
        result_effect = result_effects[0]
        if (
            cause.cause_kind is not CauseKind.EFFECT
            or cause.parent_effect_id != result_effect.get("published_effect_id")
            or cjt_id != suspended.cjt_id
            or resume_repair_id != frame.repair_id
        ):
            raise RuntimeContractError(
                "the next global tick is reserved for the exact repair resumption"
            )
        return frame

    def _validate_repair_resume(
        self,
        *,
        cause: CausePacket,
        bias: BiasState,
        repair_id: str,
    ) -> tuple[RepairFrame, Mapping[str, Any]]:
        """Prove that a committed next-tick repair Effect resumes this Bias."""

        try:
            frame = repair_frame_from_dict(
                self.store.immutable_document("repair_frames", repair_id)
            )
        except Exception as error:
            raise RuntimeContractError("repair frame is missing or corrupt") from error
        if (
            frame.repair_id not in bias.rpm.open_repair_ids
            or frame.suspended_bias_id != bias.bias_id
            or frame.parent_cause_id != bias.rpm.suspended_parent_cause_id
            or bias.rpm.return_addresses != (frame.return_address,)
            or frame.status.value != "OPEN"
        ):
            raise RuntimeContractError("repair frame does not suspend this Bias")
        if cause.parent_effect_id is None:
            raise RuntimeContractError("repair resumption requires a committed Effect Cause")
        try:
            parent_cause = self.store.immutable_document(
                "causes", frame.parent_cause_id
            )
            parent_operations = tuple(parent_cause["candidate_operation_ids"])
            parent_goal = parent_cause["goal_context"]
            rebuilt = cause_from_committed_effect(
                self.store,
                cause.parent_effect_id,
                tick=cause.tick,
                candidate_operation_ids=parent_operations,
                goal_context=parent_goal,
            )
            effect = self.store.immutable_document(
                "published_effects", cause.parent_effect_id
            )
            candidate = self.store.immutable_document(
                "candidate_effects", str(effect["candidate_effect_id"])
            )
        except Exception as error:
            raise RuntimeContractError("repair result is not a retained committed Effect") from error
        if rebuilt != cause:
            raise RuntimeContractError("repair Cause was not derived from the committed Effect")
        if (
            candidate.get("parent_cause_id") != frame.subgoal_cause_id
            or candidate.get("tick") != frame.eligible_tick
            or candidate.get("producer_cjt_id")
            not in self._viable_repair_cjts(self.state, bias.cjt_id)
            or cause.tick != frame.eligible_tick + 1
        ):
            raise RuntimeContractError(
                "repair must execute at t+1 and resume its parent on the following tick"
            )
        return frame, effect

    def _prepare_inference(
        self,
        *,
        cause: CausePacket,
        cjt_id: str,
        expected_symbol: str | None,
        opposite_symbol: str | None,
        settings: RouteSettings | None,
        supplied_artifacts: Sequence[StoredArtifact],
        resume_repair_id: str | None,
        write_memory: bool,
    ) -> _PreparedInference:
        if not verify_cause_identity(cause):
            raise RuntimeContractError("Cause identity does not bind its full payload")
        self._require_monotonic_tick(cause.tick)
        state = self.state
        self._reserved_repair_frame(
            state=state,
            cause=cause,
            cjt_id=cjt_id,
            resume_repair_id=resume_repair_id,
        )
        if cjt_id not in self.network.select_candidates(cause):
            raise RuntimeContractError("CJT is not selected by Cause operation/topology")
        bias = state.by_cjt_id[cjt_id]
        if bias.rpm.open_repair_ids and resume_repair_id is None:
            raise RuntimeContractError(
                "suspended Bias requires its exact resume_repair_id"
            )
        resume_frame: RepairFrame | None = None
        resume_effect: Mapping[str, Any] | None = None
        if resume_repair_id is not None:
            resume_frame, resume_effect = self._validate_repair_resume(
                cause=cause,
                bias=bias,
                repair_id=resume_repair_id,
            )
        contract = self.contracts[bias.stable.registered_operation_id]
        self.network.node(cjt_id).operations.bind_contract(contract)
        decoder = self.decoders[cjt_id]
        # This oracle evidence is frozen before neural execution.  It is never
        # inferred from the network's result.
        evidence, evidence_descriptor = make_bound_evidence(
            evidence_id=content_id(
                "evidence",
                {
                    "cause_id": cause.cause_id,
                    "cjt_id": cjt_id,
                    "expected_symbol": expected_symbol,
                    "opposite_symbol": opposite_symbol,
                },
            ),
            source_id=EVIDENCE_SOURCE_ID,
            port_id="AUTHORED_TARGET",
            operation_id=contract.operation_id,
            effect_kind=contract.effect_schema_id.rsplit(":", 1)[-1],
            expected_symbol=expected_symbol,
            opposite_symbol=opposite_symbol,
            provenance=(f"cause:{cause.cause_id}",),
        )
        materialized = self.materializer.materialize(
            state=state,
            cause=cause,
            cjt_id=cjt_id,
            settings=RouteSettings() if settings is None else settings,
            supplied_artifacts=supplied_artifacts,
        )
        proposal = self.network.forward_node(
            cjt_id,
            materialized.cause_tensor,
            materialized.control,
        )
        neural_route = proposal.telemetry.attention
        if (
            not torch.equal(
                neural_route.effective_path_mask,
                materialized.routing.effective_mask,
            )
            or not torch.equal(neural_route.current, materialized.routing.current)
            or not torch.equal(
                neural_route.total_current,
                materialized.routing.total_current,
            )
        ):
            raise RuntimeContractError(
                "executed neural routing does not match the materialized control route"
            )
        region = _region(materialized, proposal)
        semantic_content = decoder.decode(proposal.candidate_effect)
        candidate, candidate_artifact = freeze_candidate_effect(
            cause=cause,
            bias=bias,
            contract=contract,
            effect_tensor=proposal.candidate_effect,
            semantic_content=semantic_content,
            decoder_digest=decoder.contract.decoder_digest,
            control_binding_digest=materialized.binding_digest,
        )
        if not decoder.validate_candidate(candidate, candidate_artifact):
            raise RuntimeContractError("candidate semantic content is not tensor-derived")
        if not validate_operation_io(cause, candidate, contract):
            raise RuntimeContractError("Cause/Effect violates its operation contract")
        verification = self.verifier.evaluate(
            cause,
            candidate,
            contract,
            evidence,
            bias=bias,
            operating_region=region,
        )
        receipt = verification.receipt
        linked_repair_subgoal: RepairFrame | None = None
        if cause.cause_kind is CauseKind.RPM_SUBGOAL:
            repair_id = cause.content.get("repair_id")
            if not isinstance(repair_id, str) or not repair_id:
                raise RuntimeContractError("RPM_SUBGOAL does not name a repair frame")
            try:
                linked_repair_subgoal = repair_frame_from_dict(
                    self.store.immutable_document("repair_frames", repair_id)
                )
            except Exception as error:
                raise RuntimeContractError(
                    "RPM_SUBGOAL repair frame is missing or corrupt"
                ) from error
            if (
                linked_repair_subgoal.status.value != "OPEN"
                or linked_repair_subgoal.subgoal_cause_id != cause.cause_id
                or linked_repair_subgoal.eligible_tick != cause.tick
                or linked_repair_subgoal.parent_cause_id
                != cause.content.get("parent_cause_id")
                or linked_repair_subgoal.rejected_candidate_effect_id
                != cause.content.get("rejected_candidate_effect_id")
            ):
                raise RuntimeContractError(
                    "RPM_SUBGOAL does not exactly bind its open repair frame"
                )
            if receipt.disposition is not VerifierDisposition.ACCEPT:
                raise RuntimeContractError(
                    "an open repair subgoal must verify ACCEPT before tick advancement"
                )
        if (
            resume_frame is not None
            and receipt.disposition is not VerifierDisposition.ACCEPT
        ):
            raise RuntimeContractError(
                "a repair resume must verify ACCEPT and close its original frame"
            )
        next_bias = bias
        recurrent_artifact: StoredArtifact | None = None
        repair_frame: RepairFrame | None = None
        repair_subgoal: CausePacket | None = None
        repair_outcome: RepairOutcome | None = None
        memory_intents: tuple[Any, ...] = ()
        audit_only = False
        if receipt.disposition is VerifierDisposition.ACCEPT:
            next_recurrent = materialized.bias_tensor + proposal.proposed_bias_delta
            recurrent_reference, recurrent_artifact = encode_tensor(
                next_recurrent, kind="persistent-recurrent-bias"
            )
            next_bias = advance_bias(
                bias,
                tick=cause.tick,
                region=region,
                semantic_outcome=receipt.semantic_outcome,
                verifier_receipt_id=receipt.receipt_id,
                cause_id=cause.cause_id,
                effect_id=candidate.candidate_effect_id,
                recurrent_state_ref=tensor_ref_from_mapping(recurrent_reference),
                close_repair_id=resume_repair_id,
                retrieved_memory_refs=tuple(
                    str(item["memory_record_id"])
                    for item in materialized.memory_reads
                ),
                provenance_refs=tuple(
                    str(provenance)
                    for item in materialized.memory_reads
                    for provenance in item["provenance"]
                ),
            )
            if resume_frame is not None and resume_effect is not None:
                repair_outcome = make_repair_outcome(
                    frame=resume_frame,
                    tick=cause.tick,
                    result_effect=resume_effect,
                    resumed_cause=cause,
                    resumed_candidate=candidate,
                    receipt=receipt,
                    target_bias=bias,
                )
            if write_memory:
                memory_intents = (
                    propose_memory_write(
                        tick=cause.tick,
                        issuer_id=cjt_id,
                        bias=bias,
                        receipt=receipt,
                        cause=cause,
                        candidate=candidate,
                    ),
                )
        elif receipt.disposition is VerifierDisposition.REPAIR:
            if bias.rpm.open_repair_ids:
                raise RuntimeContractError(
                    "v0.2 cannot open a second repair for a suspended Bias"
                )
            if not self._viable_repair_cjts(state, bias.cjt_id):
                raise RuntimeContractError(
                    "repair cannot open without a durable distinct ^6 round trip"
                )
            open_frames = []
            for open_id in bias.rpm.open_repair_ids:
                try:
                    open_frames.append(
                        repair_frame_from_dict(
                            self.store.immutable_document("repair_frames", open_id)
                        )
                    )
                except Exception as error:
                    raise RuntimeContractError("open repair state is not reconstructible") from error
            repair_frame, repair_subgoal = open_repair(
                cause=cause,
                candidate=candidate,
                receipt=receipt,
                bias=bias,
                branch_count=len(open_frames) + 1,
                parent_depth=max((item.depth for item in open_frames), default=0),
                active_cycle_keys=tuple(item.cycle_key for item in open_frames),
            )
            next_bias = advance_bias(
                bias,
                tick=cause.tick,
                region=region,
                semantic_outcome=receipt.semantic_outcome,
                verifier_receipt_id=receipt.receipt_id,
                cause_id=cause.cause_id,
                open_repair_id=repair_frame.repair_id,
                open_repair_return_address=repair_frame.return_address,
                record_memory=False,
            )
        else:
            audit_only = True
        branch_usage = allocate_global_charge_tensor(
            materialized.routing.compute_plan.branch_quanta,
            materialized.conducting_query_mask.to(
                device=materialized.routing.compute_plan.branch_quanta.device
            ),
            0 if repair_frame is None else 1,
        )
        materialized = replace(
            materialized,
            observation=PostExecutionObservation(
                routes_executed=materialized.observation.routes_executed,
                reasoning_steps_used=materialized.observation.reasoning_steps_used,
                branches_opened=branch_usage,
                memory_reads_used=materialized.observation.memory_reads_used,
                diagnostic_probes_used=(
                    materialized.observation.diagnostic_probes_used
                ),
            ),
        )
        materialized.observation.validate_against(
            materialized.routing.compute_plan
        )
        return _PreparedInference(
            state=state,
            bias=bias,
            contract=contract,
            decoder=decoder,
            evidence_descriptor=evidence_descriptor,
            materialized=materialized,
            candidate_effect=candidate,
            candidate_artifact=candidate_artifact,
            verifier_receipt=receipt,
            next_bias=next_bias,
            recurrent_artifact=recurrent_artifact,
            repair_frame=repair_frame,
            repair_subgoal=repair_subgoal,
            repair_outcome=repair_outcome,
            memory_intents=memory_intents,
            region=region,
            audit_only=audit_only,
        )

    def _phases(
        self,
        *,
        tick: int,
        state: NetworkStateEnvelope,
        cause: CausePacket,
        cjt_id: str,
        materialized: MaterializedControl,
        candidate: CandidateEffect,
        receipt: VerifierReceipt,
        evidence_descriptor: Mapping[str, Any],
        region: OperatingRegion,
        state_intents: Sequence[Any],
        model_intents: Sequence[Any],
        memory_intents: Sequence[Any],
        repair_frames: Sequence[RepairFrame],
        repair_outcomes: Sequence[RepairOutcome],
        state_after: NetworkStateEnvelope,
    ) -> tuple[Any, ...]:
        bias = materialized.bias
        route = materialized.routing
        observation = materialized.observation
        selected = (
            [cjt_id]
            if bool(materialized.conducting_query_mask.any().item())
            else []
        )
        records = phase_records(
            tick=tick,
            phase_payloads={
                TickPhase.READ: {
                    "inputs": {
                        "cause_id": cause.cause_id,
                        "state_digest": state.state_digest,
                        "model_digest": state.model_digest,
                    },
                    "outputs": {
                        "bias_ids": [item.bias_id for item in state.biases],
                        "bias_digests": [item.state_digest for item in state.biases],
                        "memory_read_refs": [
                            item["memory_record_id"]
                            for item in materialized.memory_reads
                        ],
                    },
                },
                TickPhase.CANDIDATE: {
                    "inputs": {"candidate_operation_ids": list(cause.candidate_operation_ids)},
                    "outputs": {
                        "candidate_cjt_ids": list(self.network.select_candidates(cause)),
                        "operation_contract_ids": [
                            self.contracts[
                                self.network.spec(candidate_cjt_id).operation_id
                            ].contract_id
                            for candidate_cjt_id in self.network.select_candidates(cause)
                        ],
                    },
                },
                TickPhase.READINESS: {
                    "inputs": {"profile_ids": [bias.rpm.readiness.profile_id]},
                    "outputs": {
                        "desire": bias.rpm.readiness.desire.to_dict(),
                        "wisdom": bias.rpm.readiness.wisdom.to_dict(),
                        "power": bias.rpm.readiness.power.to_dict(),
                        "hard_open": bias.rpm.readiness.hard_open,
                    },
                },
                TickPhase.ROUTE: {
                    "inputs": {
                        "control_cjt_id": cjt_id,
                        "topology_mask": materialized.binding_manifest["hard_masks"][
                            "topology_mask"
                        ],
                        "permission_mask": materialized.binding_manifest["hard_masks"][
                            "permission_mask"
                        ],
                        "quarantine_mask": materialized.binding_manifest["hard_masks"][
                            "quarantine_mask"
                        ],
                        "budget_mask": materialized.binding_manifest["hard_masks"][
                            "budget_mask"
                        ],
                        "readiness_hard_mask": materialized.binding_manifest[
                            "hard_masks"
                        ]["readiness_hard_mask"],
                        "route_settings": materialized.binding_manifest[
                            "route_settings"
                        ],
                        "native_compute": materialized.binding_manifest["native_compute"],
                        "compute_policy": materialized.binding_manifest["compute_policy"],
                        "control_binding_manifest": dict(
                            materialized.binding_manifest
                        ),
                    },
                    "outputs": {
                        "compute_plan": route.compute_plan.to_authoritative_dict(),
                        "effective_path_mask": _int_values(route.effective_mask),
                        "conducting_query_mask": _int_values(
                            materialized.conducting_query_mask
                        ),
                        "current_microunits": _int_values(
                            materialized.current_microunits
                        ),
                        "total_current_microunits": _int_values(
                            materialized.total_current_microunits
                        ),
                        "flow_allocation_ppm": _int_values(
                            materialized.flow_allocation_ppm
                        ),
                    },
                },
                TickPhase.EXECUTE: {
                    "inputs": {
                        "scheduled_cjt_ids": selected,
                        "operation_ids": [bias.stable.registered_operation_id],
                    },
                    "outputs": {
                        "executed_cjt_ids": selected,
                        "compute_units_used": int(observation.reasoning_steps_used.sum().item()),
                    },
                    "compute_units": int(observation.reasoning_steps_used.sum().item()),
                },
                TickPhase.OBSERVE: {
                    "inputs": {"executed_cjt_ids": selected},
                    "outputs": {
                        "candidate_effect_ids": [candidate.candidate_effect_id],
                        "operating_regions": [region.value],
                        "artifact_ids": [candidate.content_ref.artifact_id],
                        "compute_observations": {
                            "routes_executed": _int_values(
                                observation.routes_executed
                            ),
                            "reasoning_steps_used": _int_values(
                                observation.reasoning_steps_used
                            ),
                            "branches_opened": _int_values(
                                observation.branches_opened
                            ),
                            "memory_reads_used": _int_values(
                                observation.memory_reads_used
                            ),
                            "diagnostic_probes_used": _int_values(
                                observation.diagnostic_probes_used
                            ),
                        },
                    },
                    "diagnostics": {
                        "control_binding_digest": materialized.binding_digest,
                        "declared_beta_microunits": bias.theta.beta_microunits,
                        "live_beta_by_head_microunits": materialized.binding_manifest[
                            "live_beta_by_head_microunits"
                        ],
                    },
                },
                TickPhase.VERIFY: {
                    "inputs": {
                        "candidate_effect_ids": [candidate.candidate_effect_id],
                        "evidence_ids": [evidence_descriptor["evidence_id"]],
                    },
                    "outputs": {
                        "verifier_receipt_ids": [receipt.receipt_id],
                        "semantic_outcomes": [receipt.semantic_outcome.value],
                        "dispositions": [receipt.disposition.value],
                    },
                },
                TickPhase.DIAGNOSE: {
                    "inputs": {
                        "operating_regions": [region.value],
                        "semantic_outcomes": [receipt.semantic_outcome.value],
                    },
                    "outputs": {
                        "reason_codes": list(receipt.reason_codes),
                        "repair_required": receipt.repair_required,
                    },
                },
                TickPhase.EMIT: {
                    "inputs": {"verifier_receipt_ids": [receipt.receipt_id]},
                    "outputs": {
                        "state_intent_ids": [item.intent_id for item in state_intents],
                        "model_intent_ids": [item.intent_id for item in model_intents],
                        "memory_intent_ids": [item.intent_id for item in memory_intents],
                        "repair_ids": [item.repair_id for item in repair_frames],
                        "repair_outcome_ids": [
                            item.outcome_id for item in repair_outcomes
                        ],
                        "publication_requested": receipt.disposition is VerifierDisposition.ACCEPT,
                    },
                },
                TickPhase.COMMIT: {
                    "inputs": {
                        "pre_state_digest": state.state_digest,
                        "pre_model_digest": state.model_digest,
                    },
                    "outputs": {
                        "proposed_post_state_digest": state_after.state_digest,
                        "proposed_post_model_digest": state_after.model_digest,
                    },
                },
                TickPhase.TRACE: {
                    "inputs": {"previous_trace_digest": self.store.head.trace_digest},
                    "outputs": {"seal_requested": True, "phase_count": 11},
                },
            },
        )
        validate_phase_contract(
            records,
            cause_id=cause.cause_id,
            pre_state_digest=state.state_digest,
            pre_model_digest=state.model_digest,
        )
        return records

    def inference_tick(
        self,
        *,
        cause: CausePacket,
        cjt_id: str,
        expected_symbol: str | None,
        opposite_symbol: str | None = None,
        settings: RouteSettings | None = None,
        supplied_artifacts: Sequence[StoredArtifact] = (),
        resume_repair_id: str | None = None,
        write_memory: bool = True,
    ) -> InferenceTickResult:
        """Execute and atomically record one complete eleven-phase CJT tick."""

        prepared = self._prepare_inference(
            cause=cause,
            cjt_id=cjt_id,
            expected_symbol=expected_symbol,
            opposite_symbol=opposite_symbol,
            settings=settings,
            supplied_artifacts=supplied_artifacts,
            resume_repair_id=resume_repair_id,
            write_memory=write_memory,
        )
        state = prepared.state
        bias = prepared.bias
        decoder = prepared.decoder
        evidence_descriptor = prepared.evidence_descriptor
        materialized = prepared.materialized
        candidate = prepared.candidate_effect
        candidate_artifact = prepared.candidate_artifact
        receipt = prepared.verifier_receipt
        next_bias = prepared.next_bias
        recurrent_artifact = prepared.recurrent_artifact
        repair_frame = prepared.repair_frame
        repair_subgoal = prepared.repair_subgoal
        repair_outcome = prepared.repair_outcome
        memory_intents = prepared.memory_intents
        region = prepared.region
        audit_only = prepared.audit_only

        biases = [
            next_bias if item.bias_id == bias.bias_id else item for item in state.biases
        ]
        state_after = state.successor(biases=biases)
        state_intents = (
            ()
            if audit_only
            else state_update_intents_for_successor(
                bias,
                next_bias,
                tick=cause.tick,
                receipt=receipt,
                issuer_id=cjt_id,
            )
        )
        repairs = () if repair_frame is None else (repair_frame,)
        repair_outcomes = () if repair_outcome is None else (repair_outcome,)
        phases = self._phases(
            tick=cause.tick,
            state=state,
            cause=cause,
            cjt_id=cjt_id,
            materialized=materialized,
            candidate=candidate,
            receipt=receipt,
            evidence_descriptor=evidence_descriptor,
            region=region,
            state_intents=state_intents,
            model_intents=(),
            memory_intents=memory_intents,
            repair_frames=repairs,
            repair_outcomes=repair_outcomes,
            state_after=state_after,
        )
        artifacts = _unique_artifacts(
            (
                *supplied_artifacts,
                candidate_artifact,
                *(() if recurrent_artifact is None else (recurrent_artifact,)),
            )
        )
        batch = NetworkCommitBatch(
            batch_id=content_id(
                "batch",
                {
                    "state": state.state_digest,
                    "cause": cause.cause_id,
                    "candidate": candidate.candidate_digest,
                    "receipt": receipt.receipt_digest,
                },
            ),
            tick=cause.tick,
            base_trace_digest=self.store.head.trace_digest,
            state_before=state,
            state_after=state_after,
            cause=cause,
            candidate_effects=(candidate,),
            verifier_receipts=(receipt,),
            state_intents=state_intents,
            model_intents=(),
            memory_intents=memory_intents,
            repair_frames=repairs,
            repair_outcomes=repair_outcomes,
            phase_records=phases,
            runtime_id=RUNTIME_ID,
            software_digest=self.software_digest,
            cjt_ids=tuple(item.cjt_id for item in state.biases),
            artifacts=artifacts,
            semantic_evidence=(evidence_descriptor,),
            decoder_contract=decoder.contract,
            memory_read_refs=tuple(
                str(item["memory_record_id"])
                for item in materialized.memory_reads
            ),
            compute_plan=materialized.routing.compute_plan.to_authoritative_dict(),
            compute_observations={
                "routes_executed": _int_values(materialized.observation.routes_executed),
                "reasoning_steps_used": _int_values(
                    materialized.observation.reasoning_steps_used
                ),
                "branches_opened": _int_values(materialized.observation.branches_opened),
                "memory_reads_used": _int_values(
                    materialized.observation.memory_reads_used
                ),
                "diagnostic_probes_used": _int_values(
                    materialized.observation.diagnostic_probes_used
                ),
            },
            audit_only=audit_only,
            audit_reason_codes=receipt.reason_codes if audit_only else (),
        )
        commit_receipt = self.coordinator.commit(batch)
        published = (
            None
            if not commit_receipt.published_effect_ids
            else self.store.immutable_document(
                "published_effects", commit_receipt.published_effect_ids[0]
            )
        )
        committed_state = self.state
        committed_bias = committed_state.by_cjt_id[cjt_id]
        return InferenceTickResult(
            tick=cause.tick,
            cjt_id=cjt_id,
            cause=cause,
            bias_before=bias,
            bias_after=committed_bias,
            candidate_effect=candidate,
            verifier_receipt=receipt,
            commit_receipt=commit_receipt,
            published_effect=published,
            repair_frame=repair_frame,
            repair_subgoal=repair_subgoal,
            repair_outcome=repair_outcome,
            materialized=materialized,
        )

    def learning_tick(
        self,
        *,
        cause: CausePacket,
        cjt_id: str,
        expected_symbol: str,
        loss_fn: LossFunction,
        score_fn: ScoreFunction,
        opposite_symbol: str | None = None,
        settings: RouteSettings | None = None,
        supplied_artifacts: Sequence[StoredArtifact] = (),
        allowed_parameter_names: Sequence[str] | None = None,
        parameter_group_ids: Sequence[str] | None = None,
        policy: LearningPolicy | None = None,
        regression_passed: bool = False,
        resume_repair_id: str | None = None,
        write_memory: bool = True,
    ) -> LearningTickResult:
        """Verify experience, stage a selective update, and commit it once.

        The active module is never optimized in place.  The coordinator checks
        the exact checkpoint-byte diff and propagates the one new global model
        pointer through every Bias in the same transaction.
        """

        if cause.cause_kind is CauseKind.RPM_SUBGOAL and any(
            bias.rpm.open_repair_ids for bias in self.state.biases
        ):
            raise RuntimeContractError(
                "v0.2 forbids model learning during the reserved repair subgoal tick"
            )

        prepared = self._prepare_inference(
            cause=cause,
            cjt_id=cjt_id,
            expected_symbol=expected_symbol,
            opposite_symbol=opposite_symbol,
            settings=settings,
            supplied_artifacts=supplied_artifacts,
            resume_repair_id=resume_repair_id,
            write_memory=write_memory,
        )
        if prepared.verifier_receipt.disposition is not VerifierDisposition.ACCEPT:
            raise RuntimeContractError(
                "learning requires an independently accepted candidate Effect"
            )

        operation_group = (
            f"cjt:{cjt_id}:operation:{prepared.contract.operation_id}"
        )
        groups = (
            (operation_group,)
            if parameter_group_ids is None
            else tuple(parameter_group_ids)
        )
        include_bias_head = f"cjt:{cjt_id}:bias_update_head" in groups
        allowed = (
            self.network.parameter_names_for_node(
                cjt_id,
                include_bias_head=include_bias_head,
            )
            if allowed_parameter_names is None
            else tuple(allowed_parameter_names)
        )
        admitted_policy = LearningPolicy()
        if policy is not None and policy != admitted_policy:
            raise RuntimeContractError(
                "runtime learning admits only LearningPolicy() in schema 0.2"
            )
        learning = GovernedLearner(admitted_policy)
        proposal = learning.propose(
            active_model=self.network,
            bias=prepared.bias,
            operation_contract=prepared.contract,
            verifier_receipt=prepared.verifier_receipt,
            tick=cause.tick,
            loss_fn=loss_fn,
            score_fn=score_fn,
            allowed_parameter_names=allowed,
            parameter_group_ids=groups,
            flow_ppm=bounded_mean_flow_ppm(
                tuple(
                    int(item)
                    for item in prepared.materialized.total_current_microunits.reshape(
                        -1
                    ).tolist()
                )
            ),
            regression_passed=regression_passed,
            issuer_id=cjt_id,
        )

        state = prepared.state
        next_model_version = state.model_version + 1
        next_reference = proposal.checkpoint.reference
        next_biases: list[BiasState] = []
        for old in state.biases:
            references = tuple(
                next_reference if item == state.model_artifact_ref else item
                for item in old.theta.parameter_artifacts
            )
            if next_reference not in references:
                raise RuntimeContractError("Bias lost its global checkpoint pointer")
            theta = replace(
                old.theta,
                model_version=next_model_version,
                model_digest=proposal.checkpoint.model_digest,
                parameter_artifacts=references,
            )
            base = prepared.next_bias if old.bias_id == prepared.bias.bias_id else old
            next_biases.append(
                _reseal_bias(
                    replace(
                        base,
                        version=old.version + 1,
                        previous_digest=old.state_digest,
                        theta=theta,
                    )
                )
            )
        state_after = state.successor(
            biases=next_biases,
            model_version=next_model_version,
            model_digest=proposal.checkpoint.model_digest,
            model_artifact_ref=next_reference,
        )
        initiator_after = state_after.by_bias_id[prepared.bias.bias_id]
        state_intents = state_update_intents_for_successor(
            prepared.bias,
            initiator_after,
            tick=cause.tick,
            receipt=prepared.verifier_receipt,
            issuer_id=cjt_id,
        )
        phases = self._phases(
            tick=cause.tick,
            state=state,
            cause=cause,
            cjt_id=cjt_id,
            materialized=prepared.materialized,
            candidate=prepared.candidate_effect,
            receipt=prepared.verifier_receipt,
            evidence_descriptor=prepared.evidence_descriptor,
            region=prepared.region,
            state_intents=state_intents,
            model_intents=(proposal.intent,),
            memory_intents=prepared.memory_intents,
            repair_frames=(),
            repair_outcomes=(
                ()
                if prepared.repair_outcome is None
                else (prepared.repair_outcome,)
            ),
            state_after=state_after,
        )
        manifest = {
            **_model_manifest(
                proposal.staged_model,
                proposal.checkpoint,
                model_id=state.model_id,
                model_version=next_model_version,
                decoder_labels=prepared.decoder.contract.labels,
            ),
            "parent_model_digest": state.model_digest,
            "learning_tick": cause.tick,
            "initiating_cjt_id": cjt_id,
            "qualification_receipt_id": (
                proposal.qualification.qualification_receipt_id
            ),
            "changed_parameter_names": list(proposal.changed_parameter_names),
        }
        model_version = ModelVersionWrite(
            model_digest=proposal.checkpoint.model_digest,
            parent_model_digest=state.model_digest,
            artifact_id=proposal.checkpoint.reference.artifact_id,
            payload=manifest,
        )
        artifacts = _unique_artifacts(
            (
                *supplied_artifacts,
                prepared.candidate_artifact,
                *(
                    ()
                    if prepared.recurrent_artifact is None
                    else (prepared.recurrent_artifact,)
                ),
                *proposal.artifacts,
            )
        )
        batch = NetworkCommitBatch(
            batch_id=content_id(
                "batch-learning",
                {
                    "state": state.state_digest,
                    "cause": cause.cause_id,
                    "candidate": prepared.candidate_effect.candidate_digest,
                    "receipt": prepared.verifier_receipt.receipt_digest,
                    "model": proposal.checkpoint.model_digest,
                    "qualification": proposal.qualification.receipt_digest,
                },
            ),
            tick=cause.tick,
            base_trace_digest=self.store.head.trace_digest,
            state_before=state,
            state_after=state_after,
            cause=cause,
            candidate_effects=(prepared.candidate_effect,),
            verifier_receipts=(prepared.verifier_receipt,),
            state_intents=state_intents,
            model_intents=(proposal.intent,),
            memory_intents=prepared.memory_intents,
            repair_frames=(),
            repair_outcomes=(
                ()
                if prepared.repair_outcome is None
                else (prepared.repair_outcome,)
            ),
            phase_records=phases,
            runtime_id=RUNTIME_ID,
            software_digest=self.software_digest,
            cjt_ids=tuple(item.cjt_id for item in state.biases),
            artifacts=artifacts,
            model_version=model_version,
            qualification_receipts=(proposal.qualification,),
            semantic_evidence=(prepared.evidence_descriptor,),
            decoder_contract=prepared.decoder.contract,
            memory_read_refs=tuple(
                str(item["memory_record_id"])
                for item in prepared.materialized.memory_reads
            ),
            compute_plan=(
                prepared.materialized.routing.compute_plan.to_authoritative_dict()
            ),
            compute_observations={
                "routes_executed": _int_values(
                    prepared.materialized.observation.routes_executed
                ),
                "reasoning_steps_used": _int_values(
                    prepared.materialized.observation.reasoning_steps_used
                ),
                "branches_opened": _int_values(
                    prepared.materialized.observation.branches_opened
                ),
                "memory_reads_used": _int_values(
                    prepared.materialized.observation.memory_reads_used
                ),
                "diagnostic_probes_used": _int_values(
                    prepared.materialized.observation.diagnostic_probes_used
                ),
            },
        )
        commit_receipt = self.coordinator.commit(batch)
        # The durable commit is now authoritative; make the in-memory module
        # match it before any later Cause is processed.
        load_module_checkpoint(
            self.network,
            proposal.checkpoint.reference,
            proposal.checkpoint.artifact,
        )
        published = (
            None
            if not commit_receipt.published_effect_ids
            else self.store.immutable_document(
                "published_effects", commit_receipt.published_effect_ids[0]
            )
        )
        committed_bias = self.state.by_cjt_id[cjt_id]
        inference = InferenceTickResult(
            tick=cause.tick,
            cjt_id=cjt_id,
            cause=cause,
            bias_before=prepared.bias,
            bias_after=committed_bias,
            candidate_effect=prepared.candidate_effect,
            verifier_receipt=prepared.verifier_receipt,
            commit_receipt=commit_receipt,
            published_effect=published,
            repair_frame=None,
            repair_subgoal=None,
            repair_outcome=prepared.repair_outcome,
            materialized=prepared.materialized,
        )
        return LearningTickResult(
            tick=cause.tick,
            cjt_id=cjt_id,
            inference=inference,
            learning_proposal=proposal,
            bias_before=prepared.bias,
            bias_after=committed_bias,
            commit_receipt=commit_receipt,
            pre_model_digest=state.model_digest,
            post_model_digest=proposal.checkpoint.model_digest,
        )


__all__ = [
    "AUTHORITY_CONTRACT_ID",
    "COORDINATOR_ID",
    "EVIDENCE_SOURCE_ID",
    "InferenceTickResult",
    "LearningTickResult",
    "NeuralCJTRuntime",
    "RUNTIME_ID",
    "RuntimeContractError",
]
