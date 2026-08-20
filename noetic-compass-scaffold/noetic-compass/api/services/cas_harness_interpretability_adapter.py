"""Fail-closed architecture discovery and interpretability-adapter generation.

This module is deliberately model-free.  It inspects an *already loaded* local
model object, verifies a registered decoder-stack layout, and emits either a
deterministic data manifest or reviewable Python adapter source.  Generation
does not import or execute the generated module, install hooks, download
weights, run a forward pass, or claim that an experiment succeeded.

The distinction matters:

* ``STRUCTURE_VERIFIED`` means the requested modules exist on the loaded
  object and expose the hook API.
* ``MECHANICALLY_PLANNED_NOT_RUN`` means an experiment can be wired from that
  structure, but has not been executed.
* ``BLOCKED_MISSING_MECHANICS`` means the adapter cannot honestly wire the
  requested capability.

Every one of the fourteen programme capabilities is present in the plan.  The
plan records mechanical prerequisites and external scientific prerequisites
separately so a hookable model is never confused with a validated detector or
causal result.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Literal, Mapping


ArchitectureStatus = Literal["STRUCTURE_VERIFIED", "UNSUPPORTED"]
CapabilityStatus = Literal[
    "MECHANICALLY_PLANNED_NOT_RUN",
    "BLOCKED_MISSING_MECHANICS",
]

_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_SAFE_ATTR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SAFE_HOOK_PATH_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.(?:[A-Za-z_][A-Za-z0-9_]*|0|[1-9][0-9]*))*$"
)

SCHEMA_VERSION = "cas_harness_interpretability_adapter_plan.v1"
EXECUTABLE_ADAPTER_SCHEMA_VERSION = "cas_harness_executable_adapter.v1"
ADAPTER_ENGINE_API_VERSION = "cas_harness_interpretability_engine.v1"
EXECUTABLE_GENERATION_STATUS = "EXECUTABLE_ADAPTER_GENERATED_NOT_RUN"
MAX_GENERATED_LAYERS = 4096
CLAIM_BOUNDARY = (
    "STRUCTURE/MECHANICS ONLY. NOT AN EXPERIMENT, DETECTOR, CAUSAL RESULT, "
    "MODEL-SAFETY CLAIM, OR EXECUTION AUTHORITY. DECLARED MODEL IDENTITY IS NOT "
    "LOADED-MODEL BYTE ATTESTATION. ALL CAPABILITY EVIDENCE IS NOT_RUN."
)
EXECUTABLE_CLAIM_BOUNDARY = (
    "GENERATED ATTACHMENT MECHANICS ONLY. NOT A MODEL RUN, CAPTURE RESULT, "
    "INTERVENTION RESULT, DETECTOR, CAUSAL RESULT, MODEL-SAFETY CLAIM, OR "
    "EXECUTION AUTHORITY. DECLARED CONFIG/WEIGHT HASHES ARE NOT LOADED-MODEL "
    "BYTE ATTESTATION. ALL CAPABILITY EVIDENCE IS NOT_RUN."
)
MODEL_BYTE_BINDING_STATUS = "DECLARED_REFERENCE_NOT_LOADED_MODEL_BYTE_VERIFIED"

RUNTIME_FEATURES = frozenset(
    {
        "generation_step_capture",
        "logit_capture",
        "output_replacement_intervention",
    }
)


@dataclass(frozen=True)
class ArchitectureProfile:
    """Registered, inspectable decoder layout for one model family."""

    family: str
    model_types: frozenset[str]
    layer_stack_path: tuple[str, ...]
    attention_candidates: tuple[str, ...]
    mlp_candidates: tuple[str, ...]

    @property
    def layer_stack_attr(self) -> str:
        return ".".join(self.layer_stack_path)


ARCHITECTURE_PROFILES: tuple[ArchitectureProfile, ...] = (
    ArchitectureProfile(
        family="gpt_neox",
        model_types=frozenset({"gpt_neox", "gptneox"}),
        layer_stack_path=("gpt_neox", "layers"),
        attention_candidates=("attention",),
        mlp_candidates=("mlp",),
    ),
    ArchitectureProfile(
        family="llama_like",
        model_types=frozenset(
            {
                "cohere",
                "command_r",
                "deepseek",
                "deepseek_v2",
                "deepseek_v3",
                "gemma",
                "gemma2",
                "gemma3_text",
                "granite",
                "llama",
                "mistral",
                "mixtral",
                "nemotron",
                "olmo",
                "olmo2",
                "phi",
                "phi3",
                "qwen2",
                "qwen2_moe",
                "qwen3",
                "qwen3_moe",
            }
        ),
        layer_stack_path=("model", "layers"),
        attention_candidates=("self_attn", "attention"),
        mlp_candidates=("mlp", "feed_forward"),
    ),
    ArchitectureProfile(
        family="gpt2_like",
        model_types=frozenset({"bloom", "falcon", "gpt2", "gpt_neo", "gptj", "rw"}),
        layer_stack_path=("transformer", "h"),
        attention_candidates=("attn", "self_attention"),
        mlp_candidates=("mlp",),
    ),
    ArchitectureProfile(
        family="mpt_like",
        model_types=frozenset({"mpt"}),
        layer_stack_path=("transformer", "blocks"),
        attention_candidates=("attn",),
        mlp_candidates=("ffn",),
    ),
)

_MODEL_TYPE_ALIASES = {
    "commandr": "command_r",
    "deepseekv2": "deepseek_v2",
    "deepseekv3": "deepseek_v3",
    "gptneox": "gpt_neox",
    "qwen": "qwen2",
}

_EXECUTABLE_MODEL_TYPE_ALIASES: tuple[tuple[str, str], ...] = (
    ("commandr", "command_r"),
    ("deepseekv2", "deepseek_v2"),
    ("deepseekv3", "deepseek_v3"),
    ("gptneox", "gpt_neox"),
    ("qwen", "qwen2"),
)

_EXECUTABLE_CONFIG_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("model_type", ("model_type",)),
    ("num_hidden_layers", ("num_hidden_layers", "n_layer", "n_layers")),
    ("hidden_size", ("hidden_size", "n_embd", "d_model")),
    ("num_attention_heads", ("num_attention_heads", "n_head", "n_heads")),
)


@dataclass(frozen=True)
class ModelIdentity:
    """Declared identity references required before an adapter may be planned.

    These fields are syntax-checked and included in the plan hash, but this
    model-free module cannot prove that an already-loaded Python object came
    from those exact config/weight bytes.  That limitation is explicit in the
    serialized record and therefore cannot be mistaken for byte attestation.
    """

    model_id: str
    revision: str
    config_sha256: str
    weights_manifest_sha256: str
    trust_remote_code: bool = False

    def validate(self) -> None:
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("model_id must be non-empty")
        if not isinstance(self.revision, str) or not _REVISION_RE.fullmatch(self.revision):
            raise ValueError("revision must be a pinned lowercase 40-64 hex identity")
        _require_sha256(self.config_sha256, "config_sha256")
        _require_sha256(self.weights_manifest_sha256, "weights_manifest_sha256")
        if self.trust_remote_code is not False:
            raise ValueError("trust_remote_code must be exactly false in this inert boundary")

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "config_sha256": self.config_sha256,
            "weights_manifest_sha256": self.weights_manifest_sha256,
            "trust_remote_code": self.trust_remote_code,
            "binding_status": "DECLARED_REFERENCE_NOT_LOADED_MODEL_BYTE_VERIFIED",
        }


@dataclass(frozen=True)
class ArchitectureDeclaration:
    """Expected architecture fields read from a separately hashed config."""

    model_type: str
    num_hidden_layers: int
    hidden_size: int
    num_attention_heads: int

    def validate(self) -> None:
        if not isinstance(self.model_type, str) or not normalize_model_type(self.model_type):
            raise ValueError("model_type must be non-empty")
        for name, value in (
            ("num_hidden_layers", self.num_hidden_layers),
            ("hidden_size", self.hidden_size),
            ("num_attention_heads", self.num_attention_heads),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")

    def to_dict(self) -> dict[str, object]:
        return {
            "model_type": normalize_model_type(self.model_type),
            "num_hidden_layers": self.num_hidden_layers,
            "hidden_size": self.hidden_size,
            "num_attention_heads": self.num_attention_heads,
        }


@dataclass(frozen=True)
class RuntimeVerification:
    """Untrusted reference to features claimed by a separate dry-run receipt.

    A bare SHA-256-shaped string does not authenticate a receipt or prove that
    code ran. The planner records this reference for later evidence binding but
    deliberately does *not* use it to unlock mechanics. A future admitted
    runtime verifier must validate the receipt bytes, model/adapter identities,
    canary observations, and an external trust boundary.
    """

    receipt_sha256: str
    verified_features: tuple[str, ...]

    def validate(self) -> None:
        _require_sha256(self.receipt_sha256, "runtime receipt_sha256")
        features = tuple(self.verified_features)
        if len(features) != len(set(features)):
            raise ValueError("runtime verified_features contains duplicates")
        unknown = sorted(set(features) - RUNTIME_FEATURES)
        if unknown:
            raise ValueError(f"unknown runtime verified features: {unknown}")

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_sha256": self.receipt_sha256,
            "verified_features": sorted(self.verified_features),
            "trust_status": "UNTRUSTED_REFERENCE_ONLY_DOES_NOT_UNLOCK_MECHANICS",
        }


@dataclass(frozen=True)
class LayerHookPlan:
    layer_index: int
    residual_module: str
    attention_module: str | None
    mlp_module: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "layer_index": self.layer_index,
            "residual_module": self.residual_module,
            "attention_module": self.attention_module,
            "mlp_module": self.mlp_module,
        }


@dataclass(frozen=True)
class ArchitectureDiscovery:
    status: ArchitectureStatus
    model_type: str
    family: str
    layer_stack_attr: str
    observed_layer_count: int
    available_mechanics: tuple[str, ...]
    layer_hooks: tuple[LayerHookPlan, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "model_type": self.model_type,
            "family": self.family,
            "layer_stack_attr": self.layer_stack_attr,
            "observed_layer_count": self.observed_layer_count,
            "available_mechanics": list(self.available_mechanics),
            "layer_hooks": [item.to_dict() for item in self.layer_hooks],
        }


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    name: str
    mechanical_requirements: tuple[str, ...]
    external_scientific_requirements: tuple[str, ...]


CAPABILITY_DEFINITIONS: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition("C01", "hidden_state_analysis", ("residual_capture",), ("frozen_prompts",)),
    CapabilityDefinition("C02", "layer_sweeps", ("layer_stack", "residual_capture"), ("selection_rule",)),
    CapabilityDefinition("C03", "probing", ("residual_capture",), ("labels", "group_splits", "surface_controls")),
    CapabilityDefinition(
        "C04",
        "pre_output_trajectories",
        ("residual_capture", "generation_step_capture", "logit_capture"),
        ("matched_generation_pairs",),
    ),
    CapabilityDefinition(
        "C05",
        "pre_speech_interception",
        (
            "generation_step_capture",
            "logit_capture",
            "output_replacement_intervention",
        ),
        ("pre_registered_intercept_rule", "matched_pairs"),
    ),
    CapabilityDefinition("C06", "architecture_discovery", ("architecture_discovery",), ()),
    CapabilityDefinition(
        "C07",
        "semantic_circuit_discovery",
        ("residual_capture", "attention_capture", "mlp_capture"),
        ("held_out_labels", "matched_random_components"),
    ),
    CapabilityDefinition(
        "C08",
        "ablation",
        ("output_replacement_intervention",),
        ("matched_random_ablation", "patch_back_control"),
    ),
    CapabilityDefinition("C09", "matched_controls", ("adapter_manifest",), ("control_design",)),
    CapabilityDefinition(
        "C10",
        "bounded_causal_steering",
        ("generation_step_capture", "output_replacement_intervention"),
        ("dose_schedule", "same_norm_random", "stop_rule", "collateral_harm_rule"),
    ),
    CapabilityDefinition(
        "C11",
        "prompt_injection_detection",
        ("residual_capture",),
        ("independent_labeled_corpus", "character_surface_control", "held_out_split"),
    ),
    CapabilityDefinition(
        "C12",
        "hallucination_detection",
        ("residual_capture", "logit_capture"),
        ("external_truth_labels", "abstention_policy", "surface_controls"),
    ),
    CapabilityDefinition(
        "C13",
        "reasoning_break_detection",
        ("residual_capture", "generation_step_capture"),
        ("independent_reasoning_event_labels", "matched_difficulty_controls"),
    ),
    CapabilityDefinition(
        "C14",
        "harness_adapter_generation",
        ("adapter_manifest", "deterministic_executable_adapter_generation"),
        (),
    ),
)


@dataclass(frozen=True)
class CapabilityPlan:
    capability_id: str
    name: str
    status: CapabilityStatus
    mechanical_requirements: tuple[str, ...]
    missing_mechanics: tuple[str, ...]
    external_scientific_requirements: tuple[str, ...]
    evidence_status: Literal["NOT_RUN"] = "NOT_RUN"

    def to_dict(self) -> dict[str, object]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "status": self.status,
            "mechanical_requirements": list(self.mechanical_requirements),
            "missing_mechanics": list(self.missing_mechanics),
            "external_scientific_requirements": list(self.external_scientific_requirements),
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True)
class InterpretabilityAdapterPlan:
    schema_version: str
    identity: ModelIdentity
    declaration: ArchitectureDeclaration
    discovery: ArchitectureDiscovery
    runtime_verification: RuntimeVerification | None
    capabilities: tuple[CapabilityPlan, ...]
    claim_boundary: str
    plan_sha256: str

    def unsigned_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "identity": self.identity.to_dict(),
            "declaration": self.declaration.to_dict(),
            "discovery": self.discovery.to_dict(),
            "runtime_verification": (
                self.runtime_verification.to_dict() if self.runtime_verification else None
            ),
            "capabilities": [item.to_dict() for item in self.capabilities],
            "claim_boundary": self.claim_boundary,
        }

    def to_dict(self) -> dict[str, object]:
        payload = self.unsigned_dict()
        payload["plan_sha256"] = self.plan_sha256
        return payload

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def verify_hash(self) -> None:
        expected = hashlib.sha256(canonical_json_bytes(self.unsigned_dict())).hexdigest().upper()
        if expected != self.plan_sha256:
            raise ValueError("adapter plan hash mismatch")


@dataclass(frozen=True)
class ExecutableConfigBinding:
    """One exact loaded-config field used by generated runtime verification."""

    logical_name: str
    attribute_name: str
    expected_value: str | int

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_name": self.logical_name,
            "attribute_name": self.attribute_name,
            "expected_value": self.expected_value,
        }


@dataclass(frozen=True)
class ExecutableTypeBinding:
    """SHA-256 of an observed runtime class module/qualified-name pair."""

    path: str
    type_fingerprint_sha256: str
    hook_api_fingerprint_sha256: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "type_fingerprint_sha256": self.type_fingerprint_sha256,
            "hook_api_fingerprint_sha256": self.hook_api_fingerprint_sha256,
        }


@dataclass(frozen=True)
class ExecutableAdapterSpec:
    """Closed data needed to deterministically render one executable adapter.

    Deliberately absent are ``model_id`` and every other caller-controlled text
    field.  The plan digest binds those values without copying them into Python
    source.  Every text value that *is* rendered is either a fixed protocol
    constant, a registered profile value/path, or uppercase hexadecimal.
    """

    schema_version: str
    engine_api_version: str
    plan_sha256: str
    config_sha256: str
    weights_manifest_sha256: str
    profile_family: str
    model_type: str
    model_type_aliases: tuple[tuple[str, str], ...]
    layer_stack_attr: str
    expected_layer_count: int
    config_bindings: tuple[ExecutableConfigBinding, ...]
    layer_hooks: tuple[LayerHookPlan, ...]
    type_bindings: tuple[ExecutableTypeBinding, ...]
    capability_evidence_statuses: tuple[tuple[str, str], ...]
    generation_status: str
    model_byte_binding_status: str
    claim_boundary: str

    @property
    def capture_paths(self) -> tuple[str, ...]:
        paths: list[str] = []
        for hook in self.layer_hooks:
            paths.append(hook.residual_module)
            if hook.attention_module is not None:
                paths.append(hook.attention_module)
            if hook.mlp_module is not None:
                paths.append(hook.mlp_module)
        return tuple(paths)

    @property
    def intervention_paths(self) -> tuple[str, ...]:
        # A forward hook may return a replacement output.  This exposes the
        # attachment seam only; no intervention has run or been validated.
        return self.capture_paths

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "engine_api_version": self.engine_api_version,
            "plan_sha256": self.plan_sha256,
            "config_sha256": self.config_sha256,
            "weights_manifest_sha256": self.weights_manifest_sha256,
            "profile_family": self.profile_family,
            "model_type": self.model_type,
            "model_type_aliases": [list(item) for item in self.model_type_aliases],
            "layer_stack_attr": self.layer_stack_attr,
            "expected_layer_count": self.expected_layer_count,
            "config_bindings": [item.to_dict() for item in self.config_bindings],
            "layer_hooks": [item.to_dict() for item in self.layer_hooks],
            "type_bindings": [item.to_dict() for item in self.type_bindings],
            "capture_paths": list(self.capture_paths),
            "intervention_paths": list(self.intervention_paths),
            "capability_evidence_statuses": [
                {"capability_id": capability_id, "evidence_status": status}
                for capability_id, status in self.capability_evidence_statuses
            ],
            "generation_status": self.generation_status,
            "model_byte_binding_status": self.model_byte_binding_status,
            "claim_boundary": self.claim_boundary,
        }

    @property
    def spec_sha256(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.to_dict())).hexdigest().upper()

    def verify(self) -> None:
        verify_executable_adapter_spec(self)


@dataclass(frozen=True)
class ExecutableAdapterArtifact:
    """Canonical generated source plus its closed generation specification."""

    spec: ExecutableAdapterSpec
    source_bytes: bytes
    source_sha256: str

    @property
    def source_filename(self) -> str:
        return f"cas_generated_adapter_{self.source_sha256.lower()}.py"

    def to_manifest_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "schema_version": self.spec.schema_version,
            "engine_api_version": self.spec.engine_api_version,
            "plan_sha256": self.spec.plan_sha256,
            "spec_sha256": self.spec.spec_sha256,
            "source_sha256": self.source_sha256,
            "source_filename": self.source_filename,
            "profile_family": self.spec.profile_family,
            "model_type": self.spec.model_type,
            "model_byte_binding_status": self.spec.model_byte_binding_status,
            "layer_stack_attr": self.spec.layer_stack_attr,
            "expected_layer_count": self.spec.expected_layer_count,
            "capture_paths": list(self.spec.capture_paths),
            "intervention_paths": list(self.spec.intervention_paths),
            "capability_evidence_statuses": [
                {"capability_id": capability_id, "evidence_status": status}
                for capability_id, status in self.spec.capability_evidence_statuses
            ],
            "generation_status": self.spec.generation_status,
            "claim_boundary": self.spec.claim_boundary,
        }

    def to_manifest_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_manifest_dict())

    def verify(self) -> None:
        verify_generated_adapter_artifact(self)


def normalize_model_type(value: str) -> str:
    normalized = _NON_ALNUM.sub("_", value.strip().lower()).strip("_")
    return _MODEL_TYPE_ALIASES.get(normalized, normalized)


def find_profile(model_type: str) -> ArchitectureProfile | None:
    normalized = normalize_model_type(model_type)
    for profile in ARCHITECTURE_PROFILES:
        if normalized in profile.model_types:
            return profile
    return None


def generate_executable_adapter_artifact(
    *,
    model: object,
    plan: InterpretabilityAdapterPlan,
) -> ExecutableAdapterArtifact:
    """Render a deterministic adapter from a re-verified discovery plan.

    Generation is data-only: this function performs attribute inspection,
    validates the closed specification, renders text, and parses its AST.  It
    never imports or executes the generated module and never installs a hook.
    """

    _require_exact_plan_types(plan)
    plan.verify_hash()
    serialized = plan.to_dict()
    verify_serialized_plan(serialized)

    observed = discover_loaded_architecture(model, plan.declaration)
    if observed.to_dict() != plan.discovery.to_dict():
        raise ValueError("loaded architecture drifted from verified discovery output")
    profile = find_profile(observed.model_type)
    if profile is None:  # pragma: no cover - discovery already enforces this
        raise ValueError("verified discovery references an unregistered profile")

    try:
        config = getattr(model, "config")
    except AttributeError as exc:  # pragma: no cover - discovery already checks
        raise ValueError("loaded model has no config object to bind") from exc
    declaration_values: dict[str, str | int] = {
        "model_type": observed.model_type,
        "num_hidden_layers": plan.declaration.num_hidden_layers,
        "hidden_size": plan.declaration.hidden_size,
        "num_attention_heads": plan.declaration.num_attention_heads,
    }
    config_bindings = tuple(
        _select_executable_config_binding(
            config=config,
            logical_name=logical_name,
            candidates=candidates,
            expected_value=declaration_values[logical_name],
        )
        for logical_name, candidates in _EXECUTABLE_CONFIG_FIELDS
    )

    stack = _resolve_registered_runtime_path(model, profile.layer_stack_attr)
    capture_paths = _capture_paths_from_hooks(observed.layer_hooks)
    if len(capture_paths) != len(set(capture_paths)):
        raise ValueError("verified discovery contains duplicate hook paths")
    seen_module_ids: dict[int, str] = {}
    runtime_modules: list[tuple[str, object]] = []
    for path in capture_paths:
        module = _resolve_registered_runtime_path(model, path)
        if not _has_forward_hook_api(module):
            raise ValueError(f"verified hook path is no longer hookable: {path}")
        prior = seen_module_ids.get(id(module))
        if prior is not None:
            raise ValueError(
                "verified discovery aliases one hook module through duplicate paths: "
                f"{prior} and {path}"
            )
        seen_module_ids[id(module)] = path
        runtime_modules.append((path, module))

    type_bindings = tuple(
        ExecutableTypeBinding(
            path=path,
            type_fingerprint_sha256=_runtime_type_fingerprint(value),
            hook_api_fingerprint_sha256=(
                _runtime_callable_fingerprint(getattr(value, "register_forward_hook"))
                if path in capture_paths
                else None
            ),
        )
        for path, value in (
            ("$model", model),
            ("config", config),
            (profile.layer_stack_attr, stack),
            *runtime_modules,
        )
    )
    spec = ExecutableAdapterSpec(
        schema_version=EXECUTABLE_ADAPTER_SCHEMA_VERSION,
        engine_api_version=ADAPTER_ENGINE_API_VERSION,
        plan_sha256=plan.plan_sha256,
        config_sha256=plan.identity.config_sha256,
        weights_manifest_sha256=plan.identity.weights_manifest_sha256,
        profile_family=profile.family,
        model_type=observed.model_type,
        model_type_aliases=_EXECUTABLE_MODEL_TYPE_ALIASES,
        layer_stack_attr=profile.layer_stack_attr,
        expected_layer_count=observed.observed_layer_count,
        config_bindings=config_bindings,
        layer_hooks=observed.layer_hooks,
        type_bindings=type_bindings,
        capability_evidence_statuses=tuple(
            (item.capability_id, item.evidence_status) for item in plan.capabilities
        ),
        generation_status=EXECUTABLE_GENERATION_STATUS,
        model_byte_binding_status=MODEL_BYTE_BINDING_STATUS,
        claim_boundary=EXECUTABLE_CLAIM_BOUNDARY,
    )
    spec.verify()
    source_text = _render_executable_adapter_source(spec)
    # AST parsing checks syntax without importing or executing generated code.
    ast.parse(source_text, filename="<cas-generated-interpretability-adapter>", mode="exec")
    source_bytes = source_text.encode("utf-8")
    artifact = ExecutableAdapterArtifact(
        spec=spec,
        source_bytes=source_bytes,
        source_sha256=hashlib.sha256(source_bytes).hexdigest().upper(),
    )
    artifact.verify()
    return artifact


def verify_executable_adapter_spec(spec: ExecutableAdapterSpec) -> None:
    """Enforce the closed, registry-derived executable-adapter specification."""

    if type(spec) is not ExecutableAdapterSpec:
        raise ValueError("executable adapter spec must use the exact registered dataclass")
    if spec.schema_version != EXECUTABLE_ADAPTER_SCHEMA_VERSION:
        raise ValueError("executable adapter schema_version mismatch")
    if spec.engine_api_version != ADAPTER_ENGINE_API_VERSION:
        raise ValueError("executable adapter engine_api_version mismatch")
    if spec.generation_status != EXECUTABLE_GENERATION_STATUS:
        raise ValueError("executable adapter generation_status mismatch")
    if spec.model_byte_binding_status != MODEL_BYTE_BINDING_STATUS:
        raise ValueError("executable adapter model byte-binding status mismatch")
    if spec.claim_boundary != EXECUTABLE_CLAIM_BOUNDARY:
        raise ValueError("executable adapter claim_boundary mismatch")
    _require_sha256(spec.plan_sha256, "executable adapter plan_sha256")
    _require_sha256(spec.config_sha256, "executable adapter config_sha256")
    _require_sha256(
        spec.weights_manifest_sha256,
        "executable adapter weights_manifest_sha256",
    )

    if normalize_model_type(spec.model_type) != spec.model_type:
        raise ValueError("executable adapter model_type must be canonical")
    if spec.model_type_aliases != _EXECUTABLE_MODEL_TYPE_ALIASES:
        raise ValueError("executable adapter model-type alias registry mismatch")
    profile = find_profile(spec.model_type)
    if profile is None:
        raise ValueError("executable adapter model_type is not registered")
    if spec.profile_family != profile.family:
        raise ValueError("executable adapter profile family drift")
    if spec.layer_stack_attr != profile.layer_stack_attr:
        raise ValueError("executable adapter layer stack path drift")
    if (
        isinstance(spec.expected_layer_count, bool)
        or not isinstance(spec.expected_layer_count, int)
        or not 1 <= spec.expected_layer_count <= MAX_GENERATED_LAYERS
    ):
        raise ValueError(
            f"executable adapter expected_layer_count must be 1..{MAX_GENERATED_LAYERS}"
        )

    if not isinstance(spec.config_bindings, tuple) or len(spec.config_bindings) != len(
        _EXECUTABLE_CONFIG_FIELDS
    ):
        raise ValueError("executable adapter config bindings are incomplete")
    for binding, (logical_name, allowed_attributes) in zip(
        spec.config_bindings, _EXECUTABLE_CONFIG_FIELDS, strict=True
    ):
        if type(binding) is not ExecutableConfigBinding:
            raise ValueError("executable adapter config binding type mismatch")
        if binding.logical_name != logical_name:
            raise ValueError("executable adapter config binding order/name mismatch")
        if binding.attribute_name not in allowed_attributes or not _SAFE_ATTR_RE.fullmatch(
            binding.attribute_name
        ):
            raise ValueError("executable adapter config attribute is not registered")
        if logical_name == "model_type":
            if binding.expected_value != spec.model_type:
                raise ValueError("executable adapter config model_type mismatch")
        elif (
            isinstance(binding.expected_value, bool)
            or not isinstance(binding.expected_value, int)
            or binding.expected_value <= 0
        ):
            raise ValueError("executable adapter numeric config value must be positive")
    if spec.config_bindings[1].expected_value != spec.expected_layer_count:
        raise ValueError("executable adapter config/layer count mismatch")

    if not isinstance(spec.layer_hooks, tuple) or len(spec.layer_hooks) != (
        spec.expected_layer_count
    ):
        raise ValueError("executable adapter layer hook count mismatch")
    for index, hook in enumerate(spec.layer_hooks):
        if type(hook) is not LayerHookPlan:
            raise ValueError("executable adapter layer hook type mismatch")
        residual = f"{profile.layer_stack_attr}.{index}"
        if hook.layer_index != index or hook.residual_module != residual:
            raise ValueError("executable adapter residual path/index drift")
        allowed_attention = {
            f"{residual}.{candidate}" for candidate in profile.attention_candidates
        }
        if hook.attention_module is not None and hook.attention_module not in allowed_attention:
            raise ValueError("executable adapter attention path is not registered")
        allowed_mlp = {f"{residual}.{candidate}" for candidate in profile.mlp_candidates}
        if hook.mlp_module is not None and hook.mlp_module not in allowed_mlp:
            raise ValueError("executable adapter MLP path is not registered")
        for path in (
            hook.residual_module,
            hook.attention_module,
            hook.mlp_module,
        ):
            if path is not None and not _SAFE_HOOK_PATH_RE.fullmatch(path):
                raise ValueError("executable adapter contains unsafe/traversal hook path")

    capture_paths = spec.capture_paths
    if not capture_paths or len(capture_paths) != len(set(capture_paths)):
        raise ValueError("executable adapter contains duplicate hook paths")
    if spec.intervention_paths != capture_paths:
        raise ValueError("executable adapter intervention path derivation mismatch")

    expected_type_paths = (
        "$model",
        "config",
        profile.layer_stack_attr,
        *capture_paths,
    )
    if not isinstance(spec.type_bindings, tuple) or tuple(
        item.path if type(item) is ExecutableTypeBinding else None
        for item in spec.type_bindings
    ) != expected_type_paths:
        raise ValueError("executable adapter runtime type-binding paths mismatch")
    for index, binding in enumerate(spec.type_bindings):
        if type(binding) is not ExecutableTypeBinding:
            raise ValueError("executable adapter runtime type binding type mismatch")
        _require_sha256(
            binding.type_fingerprint_sha256,
            "executable adapter runtime type fingerprint",
        )
        if index < 3:
            if binding.hook_api_fingerprint_sha256 is not None:
                raise ValueError("non-hook runtime type has a hook API fingerprint")
        else:
            _require_sha256(
                binding.hook_api_fingerprint_sha256,
                "executable adapter hook API fingerprint",
            )

    expected_evidence = tuple(
        (definition.capability_id, "NOT_RUN") for definition in CAPABILITY_DEFINITIONS
    )
    if spec.capability_evidence_statuses != expected_evidence:
        raise ValueError("executable adapter capability evidence must remain NOT_RUN")


def verify_generated_adapter_artifact(artifact: ExecutableAdapterArtifact) -> None:
    """Verify source bytes by hash *and* exact deterministic reconstruction."""

    if type(artifact) is not ExecutableAdapterArtifact:
        raise ValueError("generated adapter artifact must use the exact dataclass")
    artifact.spec.verify()
    if type(artifact.source_bytes) is not bytes:
        raise ValueError("generated adapter source must be immutable bytes")
    if len(artifact.source_bytes) > 4 * 1024 * 1024:
        raise ValueError("generated adapter source exceeds the closed size limit")
    _require_sha256(artifact.source_sha256, "generated adapter source_sha256")
    observed_sha256 = hashlib.sha256(artifact.source_bytes).hexdigest().upper()
    if observed_sha256 != artifact.source_sha256:
        raise ValueError("generated adapter source SHA-256 mismatch")
    expected_source = _render_executable_adapter_source(artifact.spec).encode("utf-8")
    if artifact.source_bytes != expected_source:
        raise ValueError("generated adapter source differs from canonical reconstruction")
    try:
        source_text = artifact.source_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:  # pragma: no cover - reconstruction precedes this
        raise ValueError("generated adapter source is not strict UTF-8") from exc
    tree = ast.parse(
        source_text,
        filename="<cas-generated-interpretability-adapter>",
        mode="exec",
    )
    _verify_generated_source_ast(tree)


def discover_loaded_architecture(
    model: object,
    declaration: ArchitectureDeclaration,
) -> ArchitectureDiscovery:
    """Inspect one loaded model without running it or installing hooks."""

    declaration.validate()
    model_type = normalize_model_type(declaration.model_type)
    profile = find_profile(model_type)
    if profile is None:
        raise ValueError(f"unsupported model_type: {model_type}")

    _verify_loaded_config(model, declaration)

    stack = _resolve_attr_path(model, profile.layer_stack_path)
    layers = _materialize_indexed_layers(stack)
    if len(layers) != declaration.num_hidden_layers:
        raise ValueError(
            "declared/observed layer-count mismatch: "
            f"declared={declaration.num_hidden_layers} observed={len(layers)}"
        )

    plans: list[LayerHookPlan] = []
    residual_ready = True
    attention_ready = True
    mlp_ready = True
    for index, layer in enumerate(layers):
        residual_path = f"{profile.layer_stack_attr}.{index}"
        if not _has_forward_hook_api(layer):
            residual_ready = False
        attention_name = _first_hookable_child(layer, profile.attention_candidates)
        mlp_name = _first_hookable_child(layer, profile.mlp_candidates)
        if attention_name is None:
            attention_ready = False
        if mlp_name is None:
            mlp_ready = False
        plans.append(
            LayerHookPlan(
                layer_index=index,
                residual_module=residual_path,
                attention_module=(
                    f"{residual_path}.{attention_name}" if attention_name is not None else None
                ),
                mlp_module=f"{residual_path}.{mlp_name}" if mlp_name is not None else None,
            )
        )

    if not residual_ready:
        raise ValueError(
            "one or more decoder blocks lack register_forward_hook; residual capture "
            "cannot be represented by this adapter"
        )

    mechanics = {
        "adapter_manifest",
        "architecture_discovery",
        "deterministic_executable_adapter_generation",
        "layer_stack",
    }
    mechanics.add("residual_capture")
    if attention_ready:
        mechanics.add("attention_capture")
    if mlp_ready:
        mechanics.add("mlp_capture")

    return ArchitectureDiscovery(
        status="STRUCTURE_VERIFIED",
        model_type=model_type,
        family=profile.family,
        layer_stack_attr=profile.layer_stack_attr,
        observed_layer_count=len(layers),
        available_mechanics=tuple(sorted(mechanics)),
        layer_hooks=tuple(plans),
    )


def build_interpretability_adapter_plan(
    *,
    model: object,
    identity: ModelIdentity,
    declaration: ArchitectureDeclaration,
    runtime_verification: RuntimeVerification | None = None,
) -> InterpretabilityAdapterPlan:
    """Build a deterministic, non-executable plan for all 14 capabilities."""

    identity.validate()
    declaration.validate()
    if runtime_verification is not None:
        runtime_verification.validate()
    discovery = discover_loaded_architecture(model, declaration)
    mechanics = set(discovery.available_mechanics)
    # A caller-supplied receipt hash is an inert reference, not proof. Do not
    # merge its asserted features into available mechanics.

    capability_plans = tuple(
        _plan_capability(definition, mechanics) for definition in CAPABILITY_DEFINITIONS
    )
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "identity": identity.to_dict(),
        "declaration": declaration.to_dict(),
        "discovery": discovery.to_dict(),
        "runtime_verification": (
            runtime_verification.to_dict() if runtime_verification else None
        ),
        "capabilities": [item.to_dict() for item in capability_plans],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    digest = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest().upper()
    plan = InterpretabilityAdapterPlan(
        schema_version=SCHEMA_VERSION,
        identity=identity,
        declaration=declaration,
        discovery=discovery,
        runtime_verification=runtime_verification,
        capabilities=capability_plans,
        claim_boundary=unsigned["claim_boundary"],
        plan_sha256=digest,
    )
    plan.verify_hash()
    return plan


def verify_serialized_plan(payload: Mapping[str, object]) -> None:
    """Check corruption and enforce the plan's non-authority semantics.

    The unkeyed hash is not a signature and does not authenticate the producer.
    Fixed schema, claim boundary, capability definitions, status derivation,
    and ``NOT_RUN`` evidence values are therefore checked independently before
    the self-hash is considered.
    """

    keys = set(payload)
    expected_keys = {
        "schema_version",
        "identity",
        "declaration",
        "discovery",
        "runtime_verification",
        "capabilities",
        "claim_boundary",
        "plan_sha256",
    }
    if keys != expected_keys:
        raise ValueError(f"adapter plan keyset mismatch: {sorted(keys ^ expected_keys)}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("adapter plan schema_version mismatch")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise ValueError("adapter plan claim_boundary mismatch")

    identity_value = payload.get("identity")
    if not isinstance(identity_value, Mapping) or set(identity_value) != {
        "model_id",
        "revision",
        "config_sha256",
        "weights_manifest_sha256",
        "trust_remote_code",
        "binding_status",
    }:
        raise ValueError("adapter plan identity keyset mismatch")
    if identity_value.get("binding_status") != (
        "DECLARED_REFERENCE_NOT_LOADED_MODEL_BYTE_VERIFIED"
    ):
        raise ValueError("adapter plan identity binding_status mismatch")
    identity = ModelIdentity(
        model_id=identity_value.get("model_id"),
        revision=identity_value.get("revision"),
        config_sha256=identity_value.get("config_sha256"),
        weights_manifest_sha256=identity_value.get("weights_manifest_sha256"),
        trust_remote_code=identity_value.get("trust_remote_code"),
    )
    identity.validate()
    if identity.to_dict() != dict(identity_value):
        raise ValueError("adapter plan identity normalization mismatch")

    declaration_value = payload.get("declaration")
    if not isinstance(declaration_value, Mapping) or set(declaration_value) != {
        "model_type",
        "num_hidden_layers",
        "hidden_size",
        "num_attention_heads",
    }:
        raise ValueError("adapter plan declaration keyset mismatch")
    declaration = ArchitectureDeclaration(
        model_type=declaration_value.get("model_type"),
        num_hidden_layers=declaration_value.get("num_hidden_layers"),
        hidden_size=declaration_value.get("hidden_size"),
        num_attention_heads=declaration_value.get("num_attention_heads"),
    )
    declaration.validate()
    if declaration.to_dict() != dict(declaration_value):
        raise ValueError("adapter plan declaration normalization mismatch")

    runtime_value = payload.get("runtime_verification")
    if runtime_value is not None:
        if not isinstance(runtime_value, Mapping) or set(runtime_value) != {
            "receipt_sha256",
            "verified_features",
            "trust_status",
        }:
            raise ValueError("adapter runtime_verification keyset mismatch")
        if runtime_value.get("trust_status") != (
            "UNTRUSTED_REFERENCE_ONLY_DOES_NOT_UNLOCK_MECHANICS"
        ):
            raise ValueError("adapter runtime_verification trust_status mismatch")
        features = runtime_value.get("verified_features")
        if not isinstance(features, list) or not all(
            isinstance(item, str) for item in features
        ):
            raise ValueError("adapter runtime verified_features must be a string list")
        runtime = RuntimeVerification(
            receipt_sha256=runtime_value.get("receipt_sha256"),
            verified_features=tuple(features),
        )
        runtime.validate()
        if runtime.to_dict() != dict(runtime_value):
            raise ValueError("adapter runtime_verification normalization mismatch")

    discovery = payload.get("discovery")
    if not isinstance(discovery, Mapping):
        raise ValueError("adapter plan discovery must be an object")
    if set(discovery) != {
        "status",
        "model_type",
        "family",
        "layer_stack_attr",
        "observed_layer_count",
        "available_mechanics",
        "layer_hooks",
    }:
        raise ValueError("adapter plan discovery keyset mismatch")
    profile = find_profile(declaration.model_type)
    if profile is None:
        raise ValueError("adapter plan declaration has unsupported model_type")
    if discovery.get("status") != "STRUCTURE_VERIFIED":
        raise ValueError("adapter plan discovery status mismatch")
    if discovery.get("model_type") != normalize_model_type(declaration.model_type):
        raise ValueError("adapter plan discovery model_type mismatch")
    if discovery.get("family") != profile.family:
        raise ValueError("adapter plan discovery family mismatch")
    if discovery.get("layer_stack_attr") != profile.layer_stack_attr:
        raise ValueError("adapter plan discovery layer_stack_attr mismatch")
    if discovery.get("observed_layer_count") != declaration.num_hidden_layers:
        raise ValueError("adapter plan discovery layer count mismatch")
    hooks = discovery.get("layer_hooks")
    if not isinstance(hooks, list) or len(hooks) != declaration.num_hidden_layers:
        raise ValueError("adapter plan discovery layer_hooks length mismatch")
    attention_ready = True
    mlp_ready = True
    for index, hook in enumerate(hooks):
        if not isinstance(hook, Mapping) or set(hook) != {
            "layer_index",
            "residual_module",
            "attention_module",
            "mlp_module",
        }:
            raise ValueError("adapter layer hook keyset mismatch")
        prefix = f"{profile.layer_stack_attr}.{index}"
        if hook.get("layer_index") != index or hook.get("residual_module") != prefix:
            raise ValueError("adapter residual layer hook mismatch")
        attention = hook.get("attention_module")
        allowed_attention = {f"{prefix}.{name}" for name in profile.attention_candidates}
        if attention is not None and attention not in allowed_attention:
            raise ValueError("adapter attention layer hook mismatch")
        attention_ready &= attention is not None
        mlp = hook.get("mlp_module")
        allowed_mlp = {f"{prefix}.{name}" for name in profile.mlp_candidates}
        if mlp is not None and mlp not in allowed_mlp:
            raise ValueError("adapter MLP layer hook mismatch")
        mlp_ready &= mlp is not None
    mechanics_value = discovery.get("available_mechanics")
    if not isinstance(mechanics_value, list) or not all(
        isinstance(item, str) for item in mechanics_value
    ):
        raise ValueError("adapter plan available_mechanics must be a string list")
    mechanics = {
        "adapter_manifest",
        "architecture_discovery",
        "deterministic_executable_adapter_generation",
        "layer_stack",
        "residual_capture",
    }
    if attention_ready:
        mechanics.add("attention_capture")
    if mlp_ready:
        mechanics.add("mlp_capture")
    if mechanics_value != sorted(mechanics):
        raise ValueError("adapter plan available_mechanics is not structurally derived")

    capability_rows = payload.get("capabilities")
    if not isinstance(capability_rows, list) or len(capability_rows) != len(
        CAPABILITY_DEFINITIONS
    ):
        raise ValueError("adapter plan must contain exactly 14 capabilities")
    capability_keys = {
        "capability_id",
        "name",
        "status",
        "mechanical_requirements",
        "missing_mechanics",
        "external_scientific_requirements",
        "evidence_status",
    }
    for definition, row in zip(CAPABILITY_DEFINITIONS, capability_rows, strict=True):
        if not isinstance(row, Mapping) or set(row) != capability_keys:
            raise ValueError("adapter capability keyset mismatch")
        if row.get("capability_id") != definition.capability_id:
            raise ValueError("adapter capability_id/order mismatch")
        if row.get("name") != definition.name:
            raise ValueError("adapter capability name mismatch")
        if row.get("mechanical_requirements") != list(
            definition.mechanical_requirements
        ):
            raise ValueError("adapter mechanical_requirements mismatch")
        if row.get("external_scientific_requirements") != list(
            definition.external_scientific_requirements
        ):
            raise ValueError("adapter external_scientific_requirements mismatch")
        missing = sorted(set(definition.mechanical_requirements) - mechanics)
        if row.get("missing_mechanics") != missing:
            raise ValueError("adapter missing_mechanics mismatch")
        expected_status = (
            "BLOCKED_MISSING_MECHANICS"
            if missing
            else "MECHANICALLY_PLANNED_NOT_RUN"
        )
        if row.get("status") != expected_status:
            raise ValueError("adapter capability status mismatch")
        if row.get("evidence_status") != "NOT_RUN":
            raise ValueError("adapter capability evidence_status must remain NOT_RUN")
    digest = payload.get("plan_sha256")
    if not isinstance(digest, str):
        raise ValueError("plan_sha256 must be a string")
    _require_sha256(digest, "plan_sha256")
    unsigned = dict(payload)
    unsigned.pop("plan_sha256")
    observed = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest().upper()
    if observed != digest:
        raise ValueError("serialized adapter plan hash mismatch")


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _plan_capability(
    definition: CapabilityDefinition,
    mechanics: set[str],
) -> CapabilityPlan:
    missing = tuple(sorted(set(definition.mechanical_requirements) - mechanics))
    status: CapabilityStatus = (
        "BLOCKED_MISSING_MECHANICS" if missing else "MECHANICALLY_PLANNED_NOT_RUN"
    )
    return CapabilityPlan(
        capability_id=definition.capability_id,
        name=definition.name,
        status=status,
        mechanical_requirements=definition.mechanical_requirements,
        missing_mechanics=missing,
        external_scientific_requirements=definition.external_scientific_requirements,
    )


def _resolve_attr_path(root: object, path: Iterable[str]) -> object:
    current = root
    traversed: list[str] = []
    for segment in path:
        traversed.append(segment)
        try:
            current = getattr(current, segment)
        except AttributeError:
            raise ValueError(f"model layout missing {'.'.join(traversed)}")
    return current


def _verify_loaded_config(model: object, declaration: ArchitectureDeclaration) -> None:
    """Bind declared dimensions to the config on the loaded model object."""

    try:
        config = getattr(model, "config")
    except AttributeError as exc:
        raise ValueError("loaded model has no config object to cross-check") from exc
    observed_type = normalize_model_type(str(getattr(config, "model_type", "")))
    declared_type = normalize_model_type(declaration.model_type)
    if observed_type != declared_type:
        raise ValueError(
            "declared/loaded model_type mismatch: "
            f"declared={declared_type} observed={observed_type or '<missing>'}"
        )
    comparisons = (
        (
            "num_hidden_layers",
            declaration.num_hidden_layers,
            ("num_hidden_layers", "n_layer", "n_layers"),
        ),
        ("hidden_size", declaration.hidden_size, ("hidden_size", "n_embd", "d_model")),
        (
            "num_attention_heads",
            declaration.num_attention_heads,
            ("num_attention_heads", "n_head", "n_heads"),
        ),
    )
    for field_name, declared, candidates in comparisons:
        observed = _first_config_int(config, candidates)
        if observed is None:
            raise ValueError(f"loaded model config does not expose {field_name}")
        if observed != declared:
            raise ValueError(
                f"declared/loaded {field_name} mismatch: "
                f"declared={declared} observed={observed}"
            )


def _first_config_int(config: object, candidates: Iterable[str]) -> int | None:
    for name in candidates:
        value = getattr(config, name, None)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
    return None


def _materialize_indexed_layers(value: object) -> tuple[object, ...]:
    if isinstance(value, (str, bytes, bytearray, Mapping)):
        raise ValueError("decoder layer stack is not an indexed module sequence")
    try:
        count = len(value)  # type: ignore[arg-type]
        layers = tuple(value[index] for index in range(count))  # type: ignore[index]
    except Exception as exc:
        raise ValueError("decoder layer stack is not an indexed module sequence") from exc
    if not layers:
        raise ValueError("decoder layer stack is empty")
    return layers


def _first_hookable_child(layer: object, candidates: Iterable[str]) -> str | None:
    for name in candidates:
        if hasattr(layer, name) and _has_forward_hook_api(getattr(layer, name)):
            return name
    return None


def _has_forward_hook_api(value: object) -> bool:
    return callable(getattr(value, "register_forward_hook", None))


def _require_exact_plan_types(plan: InterpretabilityAdapterPlan) -> None:
    if type(plan) is not InterpretabilityAdapterPlan:
        raise ValueError("executable generation requires the exact adapter plan type")
    if type(plan.identity) is not ModelIdentity:
        raise ValueError("executable generation requires the exact model identity type")
    if type(plan.declaration) is not ArchitectureDeclaration:
        raise ValueError("executable generation requires the exact declaration type")
    if type(plan.discovery) is not ArchitectureDiscovery:
        raise ValueError("executable generation requires the exact discovery type")
    if plan.runtime_verification is not None and type(plan.runtime_verification) is not (
        RuntimeVerification
    ):
        raise ValueError("executable generation requires the exact runtime reference type")
    if not isinstance(plan.capabilities, tuple) or not all(
        type(item) is CapabilityPlan for item in plan.capabilities
    ):
        raise ValueError("executable generation requires exact capability plan rows")
    if not isinstance(plan.discovery.layer_hooks, tuple) or not all(
        type(item) is LayerHookPlan for item in plan.discovery.layer_hooks
    ):
        raise ValueError("executable generation requires exact layer hook rows")


def _select_executable_config_binding(
    *,
    config: object,
    logical_name: str,
    candidates: tuple[str, ...],
    expected_value: str | int,
) -> ExecutableConfigBinding:
    for attribute_name in candidates:
        try:
            observed = getattr(config, attribute_name)
        except AttributeError:
            continue
        if logical_name == "model_type":
            if not isinstance(observed, str):
                continue
            normalized: str | int = normalize_model_type(observed)
        else:
            if isinstance(observed, bool) or not isinstance(observed, int) or observed <= 0:
                continue
            normalized = observed
        if normalized == expected_value:
            return ExecutableConfigBinding(
                logical_name=logical_name,
                attribute_name=attribute_name,
                expected_value=expected_value,
            )
    raise ValueError(f"loaded model config cannot be bound exactly for {logical_name}")


def _capture_paths_from_hooks(hooks: Iterable[LayerHookPlan]) -> tuple[str, ...]:
    paths: list[str] = []
    for hook in hooks:
        paths.append(hook.residual_module)
        if hook.attention_module is not None:
            paths.append(hook.attention_module)
        if hook.mlp_module is not None:
            paths.append(hook.mlp_module)
    return tuple(paths)


def _resolve_registered_runtime_path(root: object, dotted_path: str) -> object:
    if not isinstance(dotted_path, str) or not _SAFE_HOOK_PATH_RE.fullmatch(dotted_path):
        raise ValueError("runtime path is not a closed registered attribute path")
    current = root
    for component in dotted_path.split("."):
        try:
            if component.isdigit():
                current = current[int(component)]  # type: ignore[index]
            else:
                current = getattr(current, component)
        except (AttributeError, IndexError, KeyError, TypeError) as exc:
            raise ValueError(f"registered runtime path does not resolve: {dotted_path}") from exc
    return current


def _runtime_type_fingerprint(value: object) -> str:
    runtime_type = type(value)
    parts: list[str] = []
    for member in getattr(runtime_type, "__mro__", ()):
        module_name = getattr(member, "__module__", None)
        qualified_name = getattr(member, "__qualname__", None)
        if (
            not isinstance(module_name, str)
            or not module_name
            or not isinstance(qualified_name, str)
            or not qualified_name
        ):
            raise ValueError("runtime class lacks a stable module/qualified-name identity")
        parts.extend((module_name, qualified_name))
        namespace = getattr(member, "__dict__", {})
        for attribute_name in sorted(
            name for name in namespace if isinstance(name, str)
        ):
            attribute = namespace[attribute_name]
            attribute_type = type(attribute)
            parts.extend(
                (
                    attribute_name,
                    str(getattr(attribute_type, "__module__", "")),
                    str(getattr(attribute_type, "__qualname__", "")),
                )
            )
            if callable(attribute):
                parts.append(_runtime_callable_fingerprint(attribute))
    if not parts:
        raise ValueError("runtime class has no stable MRO identity")
    payload = "\0".join(parts).encode("utf-8", errors="strict")
    return hashlib.sha256(payload).hexdigest().upper()


def _runtime_callable_fingerprint(value: object) -> str:
    if not callable(value):
        raise ValueError("hook registration API is not callable")
    function = getattr(value, "__func__", value)
    parts = [
        str(getattr(type(function), "__module__", "")),
        str(getattr(type(function), "__qualname__", "")),
        str(getattr(function, "__module__", "")),
        str(getattr(function, "__qualname__", "")),
    ]
    code = getattr(function, "__code__", None)
    if code is not None:
        parts.extend(
            (
                code.co_code.hex(),
                str(code.co_argcount),
                str(code.co_posonlyargcount),
                str(code.co_kwonlyargcount),
                "\0".join(code.co_names),
                "\0".join(code.co_varnames),
                "\0".join(code.co_freevars),
                "\0".join(code.co_cellvars),
                _stable_code_constant(code.co_consts),
            )
        )
    payload = "\x1e".join(parts).encode("utf-8", errors="strict")
    return hashlib.sha256(payload).hexdigest().upper()


def _stable_code_constant(value: object) -> str:
    if value is None:
        return "none"
    if type(value) is bool:
        return "bool:" + ("1" if value else "0")
    if type(value) is int:
        return "int:" + str(value)
    if type(value) is float:
        return "float:" + value.hex()  # type: ignore[union-attr]
    if type(value) is complex:
        return "complex:" + value.real.hex() + ":" + value.imag.hex()  # type: ignore[union-attr]
    if type(value) is str:
        return "str:" + value  # type: ignore[operator]
    if type(value) is bytes:
        return "bytes:" + value.hex()  # type: ignore[union-attr]
    if type(value) is tuple:
        return "tuple:[" + ",".join(_stable_code_constant(item) for item in value) + "]"  # type: ignore[union-attr]
    code_bytes = getattr(value, "co_code", None)
    if isinstance(code_bytes, bytes):
        return "code:" + code_bytes.hex()
    runtime_type = type(value)
    return "object:" + str(getattr(runtime_type, "__module__", "")) + ":" + str(
        getattr(runtime_type, "__qualname__", "")
    )


def _append_generated_tuple(
    lines: list[str], name: str, values: Iterable[object]
) -> None:
    lines.append(f"{name} = (")
    for value in values:
        lines.append(f"    {value!r},")
    lines.append(")")
    lines.append("")


def _render_executable_adapter_source(spec: ExecutableAdapterSpec) -> str:
    spec.verify()
    config_rows = tuple(
        (item.logical_name, item.attribute_name, item.expected_value)
        for item in spec.config_bindings
    )
    layer_rows = tuple(
        (
            item.layer_index,
            item.residual_module,
            item.attention_module,
            item.mlp_module,
        )
        for item in spec.layer_hooks
    )
    type_rows = tuple(
        (
            item.path,
            item.type_fingerprint_sha256,
            item.hook_api_fingerprint_sha256,
        )
        for item in spec.type_bindings
    )
    alias_rows = spec.model_type_aliases
    lines = [
        '"""Deterministic CAS Harness attachment adapter; all evidence is NOT_RUN."""',
        "",
        "from __future__ import annotations",
        "",
        "import hashlib",
        "",
        f"SCHEMA_VERSION = {spec.schema_version!r}",
        f"ENGINE_API_VERSION = {spec.engine_api_version!r}",
        f"PLAN_SHA256 = {spec.plan_sha256!r}",
        f"SPEC_SHA256 = {spec.spec_sha256!r}",
        f"CONFIG_SHA256 = {spec.config_sha256!r}",
        f"WEIGHTS_MANIFEST_SHA256 = {spec.weights_manifest_sha256!r}",
        f"PROFILE_FAMILY = {spec.profile_family!r}",
        f"MODEL_TYPE = {spec.model_type!r}",
        f"LAYER_STACK_PATH = {spec.layer_stack_attr!r}",
        f"EXPECTED_LAYER_COUNT = {spec.expected_layer_count!r}",
        f"GENERATION_STATUS = {spec.generation_status!r}",
        f"MODEL_BYTE_BINDING_STATUS = {spec.model_byte_binding_status!r}",
        f"CLAIM_BOUNDARY = {spec.claim_boundary!r}",
        'SOURCE_SHA256_BINDING = "EXTERNAL_ARTIFACT_MANIFEST"',
        "",
    ]
    _append_generated_tuple(lines, "_MODEL_TYPE_ALIASES", alias_rows)
    _append_generated_tuple(lines, "CONFIG_BINDINGS", config_rows)
    _append_generated_tuple(lines, "LAYER_HOOKS", layer_rows)
    _append_generated_tuple(lines, "CAPTURE_PATHS", spec.capture_paths)
    _append_generated_tuple(lines, "INTERVENTION_PATHS", spec.intervention_paths)
    _append_generated_tuple(lines, "TYPE_BINDINGS", type_rows)
    _append_generated_tuple(
        lines,
        "CAPABILITY_EVIDENCE_STATUSES",
        spec.capability_evidence_statuses,
    )
    lines.extend(
        '''def _normalize_model_type(value):
    if type(value) is not str:
        raise RuntimeError("loaded config model_type must be exact text")
    output = []
    separator_pending = False
    for character in value.strip().lower():
        if ("a" <= character <= "z") or ("0" <= character <= "9"):
            if separator_pending and output:
                output.append("_")
            output.append(character)
            separator_pending = False
        else:
            separator_pending = True
    normalized = "".join(output).strip("_")
    for alias, target in _MODEL_TYPE_ALIASES:
        if normalized == alias:
            return target
    return normalized


def _resolve_path(root, dotted_path):
    current = root
    for component in dotted_path.split("."):
        try:
            if component.isdigit():
                current = current[int(component)]
            else:
                current = getattr(current, component)
        except (AttributeError, IndexError, KeyError, TypeError) as exc:
            raise RuntimeError(
                "generated adapter path does not resolve: " + dotted_path
            ) from exc
    return current


def _type_fingerprint(value):
    runtime_type = type(value)
    parts = []
    for member in getattr(runtime_type, "__mro__", ()):
        module_name = getattr(member, "__module__", None)
        qualified_name = getattr(member, "__qualname__", None)
        if type(module_name) is not str or not module_name:
            raise RuntimeError("runtime class module identity is unavailable")
        if type(qualified_name) is not str or not qualified_name:
            raise RuntimeError("runtime class qualified-name identity is unavailable")
        parts.extend((module_name, qualified_name))
        namespace = getattr(member, "__dict__", {})
        for attribute_name in sorted(
            name for name in namespace if type(name) is str
        ):
            attribute = namespace[attribute_name]
            attribute_type = type(attribute)
            parts.extend(
                (
                    attribute_name,
                    str(getattr(attribute_type, "__module__", "")),
                    str(getattr(attribute_type, "__qualname__", "")),
                )
            )
            if callable(attribute):
                parts.append(_callable_fingerprint(attribute))
    if not parts:
        raise RuntimeError("runtime class MRO identity is unavailable")
    payload = "\\0".join(parts).encode("utf-8", errors="strict")
    return hashlib.sha256(payload).hexdigest().upper()


def _stable_code_constant(value):
    if value is None:
        return "none"
    if type(value) is bool:
        return "bool:" + ("1" if value else "0")
    if type(value) is int:
        return "int:" + str(value)
    if type(value) is float:
        return "float:" + value.hex()
    if type(value) is complex:
        return "complex:" + value.real.hex() + ":" + value.imag.hex()
    if type(value) is str:
        return "str:" + value
    if type(value) is bytes:
        return "bytes:" + value.hex()
    if type(value) is tuple:
        return "tuple:[" + ",".join(_stable_code_constant(item) for item in value) + "]"
    code_bytes = getattr(value, "co_code", None)
    if type(code_bytes) is bytes:
        return "code:" + code_bytes.hex()
    runtime_type = type(value)
    return (
        "object:"
        + str(getattr(runtime_type, "__module__", ""))
        + ":"
        + str(getattr(runtime_type, "__qualname__", ""))
    )


def _callable_fingerprint(value):
    if not callable(value):
        raise RuntimeError("hook registration API is not callable")
    function = getattr(value, "__func__", value)
    parts = [
        str(getattr(type(function), "__module__", "")),
        str(getattr(type(function), "__qualname__", "")),
        str(getattr(function, "__module__", "")),
        str(getattr(function, "__qualname__", "")),
    ]
    code = getattr(function, "__code__", None)
    if code is not None:
        parts.extend(
            (
                code.co_code.hex(),
                str(code.co_argcount),
                str(code.co_posonlyargcount),
                str(code.co_kwonlyargcount),
                "\\0".join(code.co_names),
                "\\0".join(code.co_varnames),
                "\\0".join(code.co_freevars),
                "\\0".join(code.co_cellvars),
                _stable_code_constant(code.co_consts),
            )
        )
    payload = "\\x1e".join(parts).encode("utf-8", errors="strict")
    return hashlib.sha256(payload).hexdigest().upper()


def verify_model(
    model,
    *,
    engine_api_version,
    profile_family,
    model_byte_binding_status,
):
    if type(engine_api_version) is not str or engine_api_version != ENGINE_API_VERSION:
        raise RuntimeError("generated adapter engine API version mismatch")
    if type(profile_family) is not str or profile_family != PROFILE_FAMILY:
        raise RuntimeError("generated adapter profile family mismatch")
    if (
        type(model_byte_binding_status) is not str
        or model_byte_binding_status != MODEL_BYTE_BINDING_STATUS
    ):
        raise RuntimeError("generated adapter model byte-binding boundary mismatch")
    if len(CAPTURE_PATHS) != len(set(CAPTURE_PATHS)):
        raise RuntimeError("generated adapter contains duplicate capture paths")
    if INTERVENTION_PATHS != CAPTURE_PATHS:
        raise RuntimeError("generated adapter intervention paths drifted")
    if CAPABILITY_EVIDENCE_STATUSES != tuple(
        ("C" + str(index).zfill(2), "NOT_RUN") for index in range(1, 15)
    ):
        raise RuntimeError("generated adapter evidence status drifted from NOT_RUN")

    config = _resolve_path(model, "config")
    for logical_name, attribute_name, expected_value in CONFIG_BINDINGS:
        try:
            observed = getattr(config, attribute_name)
        except AttributeError as exc:
            raise RuntimeError(
                "generated adapter config field is missing: " + logical_name
            ) from exc
        if logical_name == "model_type":
            observed = _normalize_model_type(observed)
        elif type(observed) is not int or observed <= 0:
            raise RuntimeError(
                "generated adapter config field is not a positive exact integer: "
                + logical_name
            )
        if observed != expected_value:
            raise RuntimeError("generated adapter config drift: " + logical_name)

    stack = _resolve_path(model, LAYER_STACK_PATH)
    try:
        layer_count = len(stack)
    except (TypeError, AttributeError) as exc:
        raise RuntimeError("generated adapter layer stack is not sized") from exc
    if layer_count != EXPECTED_LAYER_COUNT:
        raise RuntimeError("generated adapter layer-count drift")

    seen_hook_objects = {}
    for path, expected_fingerprint, expected_hook_api in TYPE_BINDINGS:
        value = model if path == "$model" else _resolve_path(model, path)
        if _type_fingerprint(value) != expected_fingerprint:
            raise RuntimeError("generated adapter runtime class/subclass mismatch: " + path)
        if expected_hook_api is not None:
            register = getattr(value, "register_forward_hook", None)
            if _callable_fingerprint(register) != expected_hook_api:
                raise RuntimeError("generated adapter hook registration API drift: " + path)
    for path in CAPTURE_PATHS:
        module = _resolve_path(model, path)
        if not callable(getattr(module, "register_forward_hook", None)):
            raise RuntimeError("generated adapter hook is missing/not hookable: " + path)
        module_identity = id(module)
        if module_identity in seen_hook_objects:
            raise RuntimeError(
                "generated adapter live hook-module alias drift: "
                + seen_hook_objects[module_identity]
                + " and "
                + path
            )
        seen_hook_objects[module_identity] = path


def _attachment_point(
    model,
    hook_path,
    *,
    allowed_paths,
    engine_api_version,
    profile_family,
    model_byte_binding_status,
):
    verify_model(
        model,
        engine_api_version=engine_api_version,
        profile_family=profile_family,
        model_byte_binding_status=model_byte_binding_status,
    )
    if type(hook_path) is not str or hook_path not in allowed_paths:
        raise RuntimeError("generated adapter hook path is not in the closed allowlist")
    module = _resolve_path(model, hook_path)
    return module


def capture_attachment_point(
    model,
    hook_path,
    *,
    engine_api_version,
    profile_family,
    model_byte_binding_status,
):
    """Return one verified capture module without installing or executing a hook."""
    return _attachment_point(
        model,
        hook_path,
        allowed_paths=CAPTURE_PATHS,
        engine_api_version=engine_api_version,
        profile_family=profile_family,
        model_byte_binding_status=model_byte_binding_status,
    )


def intervention_attachment_point(
    model,
    hook_path,
    *,
    engine_api_version,
    profile_family,
    model_byte_binding_status,
):
    """Return one verified intervention module; no intervention is executed."""
    return _attachment_point(
        model,
        hook_path,
        allowed_paths=INTERVENTION_PATHS,
        engine_api_version=engine_api_version,
        profile_family=profile_family,
        model_byte_binding_status=model_byte_binding_status,
    )


__all__ = (
    "CAPABILITY_EVIDENCE_STATUSES",
    "CAPTURE_PATHS",
    "CLAIM_BOUNDARY",
    "CONFIG_SHA256",
    "ENGINE_API_VERSION",
    "EXPECTED_LAYER_COUNT",
    "GENERATION_STATUS",
    "INTERVENTION_PATHS",
    "LAYER_HOOKS",
    "LAYER_STACK_PATH",
    "MODEL_BYTE_BINDING_STATUS",
    "MODEL_TYPE",
    "PLAN_SHA256",
    "PROFILE_FAMILY",
    "SCHEMA_VERSION",
    "SOURCE_SHA256_BINDING",
    "SPEC_SHA256",
    "TYPE_BINDINGS",
    "WEIGHTS_MANIFEST_SHA256",
    "capture_attachment_point",
    "intervention_attachment_point",
    "verify_model",
)
'''.splitlines()
    )
    return "\n".join(lines) + "\n"


def _verify_generated_source_ast(tree: ast.Module) -> None:
    allowed_imports = 0
    for node in tree.body:
        if isinstance(node, ast.Expr):
            if not isinstance(node.value, ast.Constant) or not isinstance(
                node.value.value, str
            ):
                raise ValueError("generated adapter has a non-docstring top-level expression")
        elif isinstance(node, ast.ImportFrom):
            if not (
                node.module == "__future__"
                and len(node.names) == 1
                and node.names[0].name == "annotations"
                and node.names[0].asname is None
            ):
                raise ValueError("generated adapter has an unapproved future import")
            allowed_imports += 1
        elif isinstance(node, ast.Import):
            if not (
                len(node.names) == 1
                and node.names[0].name == "hashlib"
                and node.names[0].asname is None
            ):
                raise ValueError("generated adapter has an unapproved import")
            allowed_imports += 1
        elif isinstance(node, ast.Assign):
            if any(
                isinstance(item, ast.Call)
                for item in _iter_ast_nodes_without_import(node.value)
            ):
                raise ValueError("generated adapter has a top-level executable assignment")
        elif not isinstance(node, ast.FunctionDef):
            raise ValueError("generated adapter has an unapproved top-level statement")
    if allowed_imports != 2:
        raise ValueError("generated adapter import set mismatch")
    prohibited_calls = {"compile", "eval", "exec", "open", "__import__"}
    for node in _iter_ast_nodes_without_import(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            raise ValueError("generated adapter contains an unapproved executable construct")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in prohibited_calls:
                raise ValueError("generated adapter contains a prohibited dynamic call")


def _iter_ast_nodes_without_import(root: ast.AST) -> Iterable[ast.AST]:
    """Depth-first AST walk without ``ast.walk``'s lazy collections import."""

    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(tuple(ast.iter_child_nodes(node))))


def _require_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be uppercase 64-hex SHA-256")


__all__ = [
    "ADAPTER_ENGINE_API_VERSION",
    "ARCHITECTURE_PROFILES",
    "CAPABILITY_DEFINITIONS",
    "CLAIM_BOUNDARY",
    "EXECUTABLE_ADAPTER_SCHEMA_VERSION",
    "EXECUTABLE_CLAIM_BOUNDARY",
    "EXECUTABLE_GENERATION_STATUS",
    "MAX_GENERATED_LAYERS",
    "MODEL_BYTE_BINDING_STATUS",
    "RUNTIME_FEATURES",
    "SCHEMA_VERSION",
    "ArchitectureDeclaration",
    "ArchitectureDiscovery",
    "CapabilityPlan",
    "ExecutableAdapterArtifact",
    "ExecutableAdapterSpec",
    "ExecutableConfigBinding",
    "ExecutableTypeBinding",
    "InterpretabilityAdapterPlan",
    "LayerHookPlan",
    "ModelIdentity",
    "RuntimeVerification",
    "build_interpretability_adapter_plan",
    "canonical_json_bytes",
    "discover_loaded_architecture",
    "find_profile",
    "generate_executable_adapter_artifact",
    "normalize_model_type",
    "verify_executable_adapter_spec",
    "verify_generated_adapter_artifact",
    "verify_serialized_plan",
]
