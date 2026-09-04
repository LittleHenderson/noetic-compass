"""Stable public API for the CAS Neural CJT Transformer v0.2 prototype.

The package uses lazy exports so its typed contracts and schemas remain usable
without importing PyTorch or the separate CASformer dependency.  Accessing a
neural or runtime symbol imports that symbol's owning module on demand.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Final


__version__ = "0.2.0"


# Each name below is already declared public by its owning module.  Keeping one
# explicit package manifest makes accidental internal helpers unavailable and
# gives callers a stable ``from cas_cjt import ...`` surface.
_EXPORT_GROUPS: Final[dict[str, tuple[str, ...]]] = {
    "types": (
        "PPM_SCALE",
        "MANDATORY_TICK_ORDER",
        "BUILTIN_OPERATION_IDENTITIES",
        "ContractTypeError",
        "CauseKind",
        "ReadinessAxisName",
        "ReadinessStatus",
        "OperatingRegion",
        "SemanticOutcome",
        "VerifierDisposition",
        "OntologyStatus",
        "RepairStatus",
        "ModelUpdateKind",
        "MemoryKind",
        "CommitDisposition",
        "AuthorityCapability",
        "TickPhase",
        "TensorArtifactRef",
        "CausePacket",
        "ReadinessAxis",
        "ReadinessState",
        "StableSubstrate",
        "LocalMemory",
        "RPMState",
        "OperatingRecord",
        "ThetaRef",
        "Governance",
        "BiasState",
        "CandidateEffect",
        "PublishedEffect",
        "OperationContract",
        "VerifierReceipt",
        "RepairFrame",
        "RepairOutcome",
        "StateUpdateIntent",
        "ModelUpdateIntent",
        "MemoryWriteIntent",
        "CommitReceipt",
        "PhaseRecord",
        "TickTrace",
    ),
    "contracts": (
        "SCHEMA_FILENAME",
        "ContractSchemaError",
        "assert_no_json_floats",
        "canonical_json",
        "canonical_digest",
        "verify_declared_digest",
        "load_contract_schema",
        "validate_contract",
        "is_valid_contract",
    ),
    "artifacts": (
        "ARTIFACT_ENCODING",
        "ArtifactError",
        "StoredArtifact",
        "decode_tensor",
        "encode_tensor",
        "make_artifact",
        "make_model_artifact",
    ),
    "checkpoint": (
        "CHECKPOINT_ENCODING",
        "CheckpointBundle",
        "CheckpointError",
        "changed_parameter_names",
        "checkpoint_entry_digests",
        "diff_checkpoint_artifacts",
        "encode_module_checkpoint",
        "load_module_checkpoint",
        "verify_checkpoint",
    ),
    "state": (
        "CandidateEffectSchema",
        "READINESS_PROFILE_ID",
        "RUNTIME_STATE_SCHEMA",
        "StateContractError",
        "ZERO_DIGEST",
        "advance_bias",
        "bias_from_dict",
        "cause_from_committed_effect",
        "content_id",
        "load_runtime_biases",
        "make_cause",
        "make_initial_bias",
        "make_operation_contract",
        "make_readiness",
        "make_runtime_state",
        "tensor_ref_from_mapping",
        "verify_cause_identity",
    ),
    "readiness": (
        "DWPProfile",
        "ReadinessError",
    ),
    "routing": (
        "CASOhmRouter",
        "CASOhmRoutingResult",
        "ComputePolicy",
        "NativeComputeInputs",
        "PostExecutionObservation",
        "PredeclaredComputePlan",
        "RouteInputs",
        "RoutingError",
        "compiled_attention_twin",
    ),
    "control": (
        "BiasControlMaterializer",
        "ControlBindingError",
        "MaterializedControl",
        "RouteSettings",
    ),
    "neural": (
        "ATTRACT",
        "AVERT",
        "DECOMPOSE",
        "TRIGGER",
        "NeuralCJT",
        "NeuralCJTError",
        "NeuralCJTProposal",
        "OPERATION_REGISTRATIONS",
        "OperationAdmission",
        "OperationRegistration",
        "RegisteredOperationBank",
    ),
    "network": (
        "CJTNodeSpec",
        "NetworkError",
        "NeuralCJTNetwork",
        "TopologyEdge",
    ),
    "semantic": (
        "DecoderContract",
        "DeterministicSemanticDecoder",
        "SemanticDecodeError",
        "make_bound_evidence",
        "validate_operation_io",
        "verify_evidence_descriptor",
    ),
    "verifier": (
        "IndependentEffectVerifier",
        "IndependentVerifier",
        "SemanticEvidence",
        "VerificationError",
        "VerificationResult",
    ),
    "proposals": (
        "ProposalError",
        "freeze_candidate_effect",
        "make_state_update_intent",
        "phase_records",
        "state_update_intents_for_successor",
    ),
    "repair": (
        "RepairBranchExhausted",
        "RepairBudgetExhausted",
        "RepairCycleDetected",
        "RepairDepthExhausted",
        "RepairError",
        "make_repair_outcome",
        "open_repair",
        "repair_frame_from_dict",
        "repair_outcome_from_dict",
    ),
    "memory": (
        "MemoryError",
        "memory_document",
        "propose_memory_write",
        "retrieve_memory",
    ),
    "learning": (
        "GovernedLearner",
        "LearningError",
        "LearningPolicy",
        "LearningProposal",
        "QualificationFailed",
        "QualificationReceipt",
        "validate_qualification_receipt",
    ),
    "persistence": (
        "STORE_SCHEMA_VERSION",
        "ActiveHead",
        "IdempotencyConflict",
        "InjectedFailure",
        "ModelVersionWrite",
        "PersistenceError",
        "SQLiteAtomicStore",
        "StaleHeadError",
        "StoredDocument",
    ),
    "network_coordinator": (
        "NetworkAtomicCoordinator",
        "NetworkBatchRejected",
        "NetworkCommitBatch",
        "NetworkRecoverySnapshot",
        "NetworkStateEnvelope",
    ),
    "phase_contract": (
        "PhaseContractError",
        "REQUIRED_PHASE_FIELDS",
        "validate_phase_contract",
    ),
    "trace": (
        "MANDATORY_PHASES",
        "REJECTION_AUDIT_SCHEMA_VERSION",
        "TRACE_SCHEMA_VERSION",
        "SealedTrace",
        "SealedRejectionAudit",
        "TraceError",
        "make_public_trace",
        "make_public_rejection_audit",
        "reconstruct_trace",
        "seal_trace",
        "seal_rejection_audit",
        "validate_phase_order",
        "verify_public_trace",
        "verify_public_rejection_audit",
        "verify_rejection_audit",
        "verify_rejection_audit_chain",
        "verify_trace",
        "verify_trace_chain",
    ),
    "runtime": (
        "AUTHORITY_CONTRACT_ID",
        "COORDINATOR_ID",
        "EVIDENCE_SOURCE_ID",
        "InferenceTickResult",
        "LearningTickResult",
        "NeuralCJTRuntime",
        "RUNTIME_ID",
        "RuntimeContractError",
    ),
    "cncm_bridge": (
        "AUTHORITY_STATUS",
        "BRIDGE_ADAPTER_ID",
        "BRIDGE_SCHEMA_VERSION",
        "FUTURE_REVISION_STATUS",
        "PERMITTED_USES",
        "PROHIBITED_AUTHORITIES",
        "CNCMBridgeError",
        "CommittedEffectEvidenceStore",
        "InertCNCMCandidateEnvelope",
        "ProposalOnlyCNCMBridge",
    ),
}


_EXPORTS: Final[dict[str, tuple[str, str]]] = {}
for _module_name, _names in _EXPORT_GROUPS.items():
    for _name in _names:
        if _name in _EXPORTS:  # pragma: no cover - import-time manifest guard
            raise RuntimeError(f"duplicate public API name: {_name}")
        _EXPORTS[_name] = (f".{_module_name}", _name)


def __getattr__(name: str) -> Any:
    """Load one declared public symbol from its owning module."""

    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_EXPORTS})


__all__ = ("__version__", *_EXPORTS)
