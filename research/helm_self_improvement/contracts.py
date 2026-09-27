"""Typed H1/H2 data. Authority belongs to the separately admitted host."""
from dataclasses import asdict, dataclass
import hashlib
import json

SCHEMA = "helm.si.native-acquisition/2"
OPERATIONS = ("NO_CHANGE", "CHANGE_CONFIG", "COMPOSE_SUPPORTED_COMPONENTS")
COMPONENTS = ("parent_transform", "prerequisite_acquisition", "verification_commit")
PROVENANCE = "PUBLIC_ENGINEERING_HOST_RECORDED_CONFIGURATION_FIXTURE"
VISIBILITY = "PUBLIC_ORIGINAL_INPUT_AND_RUNTIME_TRACE_ONLY"
ENTRYPOINT = "research.cas_closed_loop_1.run_closed_loop.run_episode"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def require_hash(value, length=64):
    if type(value) is not str or len(value) != length or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("MALFORMED_IDENTITY_HASH")


@dataclass(frozen=True)
class ParentIdentity:
    source_sha: str
    runtime_sha: str
    branch: str
    source_manifest_sha256: str
    harness_sha256: str
    checkpoint_sha256: str | None = None
    schema: str = SCHEMA

    def __post_init__(self):
        require_hash(self.source_sha, 40)
        require_hash(self.runtime_sha, 40)
        require_hash(self.source_manifest_sha256)
        require_hash(self.harness_sha256)
        if self.schema != SCHEMA:
            raise ValueError("INCOMPATIBLE_PARENT_SCHEMA")
        if type(self.branch) is not str or not self.branch or len(self.branch) > 200:
            raise ValueError("INVALID_BRANCH_CONTEXT")
        if self.checkpoint_sha256 is not None:
            raise ValueError("CHECKPOINT_NOT_SUPPORTED")


@dataclass(frozen=True)
class HarnessConfig:
    allow_acquisition: bool = False

    def __post_init__(self):
        if type(self.allow_acquisition) is not bool:
            raise ValueError("BOOLEAN_CONFIGURATION_REQUIRED")


@dataclass(frozen=True)
class SelfDescription:
    parent: ParentIdentity
    config: HarnessConfig
    entrypoint: str = ENTRYPOINT
    supported_edits: tuple = OPERATIONS
    model_execution: str = "NOT_SUPPORTED_IN_THIS_SYMBOLIC_ENGINEERING_SLICE"
    tensor_shapes: tuple = ()
    tensor_dtypes: tuple = ()
    trainable_parameters: int = 0
    visibility: str = VISIBILITY
    observed_memory_bytes: int | None = None

    def __post_init__(self):
        ParentIdentity(**asdict(self.parent))
        HarnessConfig(**asdict(self.config))
        if (self.entrypoint != ENTRYPOINT or self.supported_edits != OPERATIONS or
                self.tensor_shapes or self.tensor_dtypes or type(self.trainable_parameters) is not int or
                self.trainable_parameters != 0 or self.visibility != VISIBILITY or
                self.model_execution != "NOT_SUPPORTED_IN_THIS_SYMBOLIC_ENGINEERING_SLICE"):
            raise ValueError("UNSUPPORTED_SELF_DESCRIPTION")
        if self.observed_memory_bytes is not None and (type(self.observed_memory_bytes) is not int or self.observed_memory_bytes < 0):
            raise ValueError("INVALID_MEMORY_MEASUREMENT")


@dataclass(frozen=True)
class FailureObservation:
    parent: ParentIdentity
    run_id: str
    run_sequence: int
    input_sha256: str
    trace_sha256: str
    journal_digest: str
    original_prediction: str | None
    checked_effect: bool
    feedback: str
    provenance: str = PROVENANCE
    visibility: str = VISIBILITY

    def __post_init__(self):
        ParentIdentity(**asdict(self.parent))
        if (type(self.run_id) is not str or not self.run_id.startswith("run_") or
                len(self.run_id) != 10 or not self.run_id[4:].isdigit() or
                type(self.run_sequence) is not int or self.run_sequence < 1):
            raise ValueError("INVALID_RUN_ORDER")
        for value in (self.input_sha256, self.trace_sha256, self.journal_digest):
            require_hash(value)
        if self.provenance != PROVENANCE or self.visibility != VISIBILITY:
            raise ValueError("NON_PUBLIC_OBSERVATION_PROVENANCE")
        if type(self.checked_effect) is not bool or self.feedback not in ("BLOCKED", "CHECKED"):
            raise ValueError("INVALID_PUBLIC_FEEDBACK")
        if (self.feedback == "CHECKED") != self.checked_effect:
            raise ValueError("INCONSISTENT_PUBLIC_FEEDBACK")
        if self.original_prediction is not None and (type(self.original_prediction) is not str or len(self.original_prediction) > 256):
            raise ValueError("INVALID_PUBLIC_PREDICTION")


@dataclass(frozen=True)
class ModificationProposal:
    parent: ParentIdentity
    observation_sha256: str
    operation: str
    parameters: tuple
    proposer: str = "EXTERNALLY_AUTHORED_FIXTURE"
    hypothesis: str = "PERMIT_EXISTING_PREREQUISITE_ACQUISITION"
    alternatives: tuple = ("NO_CHANGE",)
    attribution: str = "ENGINEERING_ASSISTED"

    def __post_init__(self):
        ParentIdentity(**asdict(self.parent))
        require_hash(self.observation_sha256)
        if (self.proposer != "EXTERNALLY_AUTHORED_FIXTURE" or
                self.hypothesis != "PERMIT_EXISTING_PREREQUISITE_ACQUISITION" or
                self.alternatives != ("NO_CHANGE",) or self.attribution != "ENGINEERING_ASSISTED"):
            raise ValueError("UNSUPPORTED_PROPOSAL_CHANNEL")
        if self.operation not in OPERATIONS:
            raise ValueError("UNSUPPORTED_EDIT_MODE")
        if type(self.parameters) is not tuple:
            raise ValueError("TYPED_PARAMETERS_REQUIRED")


@dataclass(frozen=True)
class CandidateBuild:
    parent: ParentIdentity
    proposal: ModificationProposal
    config: HarnessConfig
    candidate_id: str
    edit_level: str
    build_sequence: int
    isolation: str = "TYPED_DATA_ONLY_NO_CANDIDATE_CODE_PATH_OR_IMPORT"


def public_observation(parent, payload):
    expected = {"run_id", "run_sequence", "input_sha256", "trace_sha256", "journal_digest",
                "original_prediction", "checked_effect", "feedback"}
    if type(payload) is not dict or set(payload) != expected:
        raise ValueError("NON_PUBLIC_OR_UNKNOWN_OBSERVATION_FIELDS")
    return FailureObservation(parent=parent, **payload)


def candidate_configuration(description, proposal):
    if proposal.operation not in description.supported_edits:
        raise ValueError("UNSUPPORTED_EDIT_MODE")
    if proposal.operation == "NO_CHANGE":
        if proposal.parameters:
            raise ValueError("NO_CHANGE_HAS_NO_PARAMETERS")
        return description.config, "H1"
    if proposal.operation == "CHANGE_CONFIG":
        if len(proposal.parameters) != 1 or type(proposal.parameters[0]) is not bool:
            raise ValueError("ONLY_ALLOW_ACQUISITION_BOOLEAN_IS_EDITABLE")
        return HarnessConfig(proposal.parameters[0]), "H1"
    if proposal.parameters not in (COMPONENTS, (COMPONENTS[0], COMPONENTS[2])):
        raise ValueError("UNSUPPORTED_COMPOSITION_OR_MISSING_OBLIGATION")
    return HarnessConfig(COMPONENTS[1] in proposal.parameters), "H2"


def build_candidate(host, description, observation, proposal):
    from .admission import TrustedHost
    if type(host) is not TrustedHost:
        raise ValueError("TRUSTED_HOST_ADMISSION_REQUIRED")
    # Validation repeats at boundaries, including directly constructed/deserialized data.
    host.validate_description(description)
    host.verify_observation(observation)
    if type(proposal) is not ModificationProposal:
        raise ValueError("TYPED_PROPOSAL_REQUIRED")
    ModificationProposal(**(asdict(proposal) | {"parent": proposal.parent}))
    host.validate_parent(proposal.parent)
    if proposal.observation_sha256 != digest(asdict(observation)):
        raise ValueError("WRONG_OBSERVATION")
    config, level = candidate_configuration(description, proposal)
    sequence = host.next_sequence()
    body = {"parent": asdict(host.parent), "proposal": asdict(proposal), "config": asdict(config),
            "edit_level": level, "build_sequence": sequence}
    candidate = CandidateBuild(host.parent, proposal, config, digest(body), level, sequence)
    host.record_build(candidate, observation)
    return candidate


def execution_config(host, description, observation, candidate, mode):
    from .admission import TrustedHost
    if type(host) is not TrustedHost:
        raise ValueError("TRUSTED_HOST_ADMISSION_REQUIRED")
    host.validate_description(description)
    if mode not in ("disabled", "shadow", "active"):
        raise ValueError("UNKNOWN_EXECUTION_MODE")
    # Disabled ignores the proposal but never takes baseline settings from it.
    if mode != "disabled":
        host.verify_candidate(description, observation, candidate)
    return candidate.config if mode == "active" else host.baseline_config
