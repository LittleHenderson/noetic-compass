"""SI1 records for the existing native acquisition harness, before outcome access.

Only finite typed configuration/composition is executable. These records neither
authorize a model change nor authenticate themselves as an independent review.
"""
from dataclasses import asdict, dataclass
import hashlib
import json

SCHEMA = "helm.si.native-acquisition/1"
OPERATIONS = ("NO_CHANGE", "CHANGE_CONFIG", "COMPOSE_SUPPORTED_COMPONENTS")
COMPONENTS = ("parent_transform", "prerequisite_acquisition", "verification_commit")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ParentIdentity:
    source_sha: str
    runtime_sha: str
    branch: str
    source_manifest_sha256: str
    checkpoint_sha256: str | None = None
    schema: str = SCHEMA


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
    entrypoint: str = "research.cas_closed_loop_1.run_closed_loop.run_episode"
    supported_edits: tuple = OPERATIONS
    model_execution: str = "NOT_SUPPORTED_IN_THIS_SYMBOLIC_ENGINEERING_SLICE"
    tensor_shapes: tuple = ()
    observed_memory_bytes: int | None = None


@dataclass(frozen=True)
class FailureObservation:
    parent: ParentIdentity
    input_sha256: str
    trace_sha256: str
    original_prediction: str | None
    checked_effect: bool
    feedback: str
    provenance: str = "PUBLIC_ENGINEERING_INJECTED_ACQUISITION_DISABLED"
    visibility: str = "PUBLIC_ORIGINAL_INPUT_AND_RUNTIME_TRACE_ONLY"


@dataclass(frozen=True)
class ModificationProposal:
    parent: ParentIdentity
    observation_sha256: str
    operation: str
    parameters: tuple
    proposer: str
    hypothesis: str
    alternatives: tuple
    attribution: str = "ENGINEERING_ASSISTED"


@dataclass(frozen=True)
class CandidateBuild:
    parent: ParentIdentity
    proposal: ModificationProposal
    config: HarnessConfig
    candidate_id: str
    edit_level: str
    isolation: str = "TYPED_DATA_ONLY_NO_CANDIDATE_CODE_PATH_OR_IMPORT"


def public_observation(parent, payload):
    expected = {"input_sha256", "trace_sha256", "original_prediction", "checked_effect", "feedback"}
    if type(payload) is not dict or set(payload) != expected:
        raise ValueError("NON_PUBLIC_OR_UNKNOWN_OBSERVATION_FIELDS")
    if payload["feedback"] not in ("BLOCKED", "CHECKED", "FAILED"):
        raise ValueError("UNSUPPORTED_FEEDBACK")
    if type(payload["checked_effect"]) is not bool:
        raise ValueError("BOOLEAN_EFFECT_REQUIRED")
    if payload["original_prediction"] is not None and type(payload["original_prediction"]) is not str:
        raise ValueError("RAW_PUBLIC_PREDICTION_REQUIRED")
    for field in ("input_sha256", "trace_sha256"):
        value = payload[field]
        if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("OBSERVATION_DIGEST_REQUIRED")
    return FailureObservation(parent=parent, **payload)


def build_candidate(description, observation, proposal):
    if not isinstance(description, SelfDescription) or not isinstance(observation, FailureObservation):
        raise ValueError("TYPED_OBSERVATION_REQUIRED")
    if type(proposal) is not ModificationProposal:
        raise ValueError("TYPED_PROPOSAL_REQUIRED")
    if proposal.parent != description.parent or observation.parent != description.parent:
        raise ValueError("STALE_OR_FOREIGN_PARENT")
    if proposal.observation_sha256 != digest(asdict(observation)):
        raise ValueError("WRONG_OBSERVATION")
    if proposal.attribution != "ENGINEERING_ASSISTED" or not proposal.proposer:
        raise ValueError("PROPOSER_ATTRIBUTION_REQUIRED")
    if type(proposal.parameters) is not tuple:
        raise ValueError("TYPED_PARAMETERS_REQUIRED")
    if proposal.operation == "NO_CHANGE":
        if proposal.parameters:
            raise ValueError("NO_CHANGE_HAS_NO_PARAMETERS")
        config, level = description.config, "H1"
    elif proposal.operation == "CHANGE_CONFIG":
        if len(proposal.parameters) != 1 or type(proposal.parameters[0]) is not bool:
            raise ValueError("ONLY_ALLOW_ACQUISITION_BOOLEAN_IS_EDITABLE")
        config, level = HarnessConfig(proposal.parameters[0]), "H1"
    elif proposal.operation == "COMPOSE_SUPPORTED_COMPONENTS":
        if proposal.parameters not in (COMPONENTS, (COMPONENTS[0], COMPONENTS[2])):
            raise ValueError("UNSUPPORTED_COMPOSITION_OR_MISSING_OBLIGATION")
        config, level = HarnessConfig("prerequisite_acquisition" in proposal.parameters), "H2"
    else:
        raise ValueError("UNSUPPORTED_EDIT_MODE")
    body = {"parent": asdict(description.parent), "proposal": asdict(proposal), "config": asdict(config)}
    return CandidateBuild(description.parent, proposal, config, digest(body), level)


def execution_config(description, observation, candidate, mode):
    if mode not in ("disabled", "shadow", "active"):
        raise ValueError("UNKNOWN_EXECUTION_MODE")
    if mode == "disabled":
        return description.config
    rebuilt = build_candidate(description, observation, candidate.proposal)
    if rebuilt != candidate:
        raise ValueError("CANDIDATE_BUILD_ALTERED")
    return description.config if mode == "shadow" else candidate.config
