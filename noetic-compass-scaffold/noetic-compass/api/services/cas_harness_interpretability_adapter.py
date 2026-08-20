"""Fail-closed architecture discovery and interpretability-adapter planning.

This module is deliberately model-free.  It inspects an *already loaded* local
model object, verifies a registered decoder-stack layout, and emits a
deterministic data manifest describing where a later, separately authorised
worker may attach capture hooks.  It never downloads weights, runs a forward
pass, generates Python source, or claims that an experiment succeeded.

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

SCHEMA_VERSION = "cas_harness_interpretability_adapter_plan.v1"
CLAIM_BOUNDARY = (
    "STRUCTURE/MECHANICS ONLY. NOT AN EXPERIMENT, DETECTOR, CAUSAL RESULT, "
    "MODEL-SAFETY CLAIM, OR EXECUTION AUTHORITY. DECLARED MODEL IDENTITY IS NOT "
    "LOADED-MODEL BYTE ATTESTATION. ALL CAPABILITY EVIDENCE IS NOT_RUN."
)

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
    CapabilityDefinition("C14", "harness_adapter_generation", ("adapter_manifest",), ()),
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


def normalize_model_type(value: str) -> str:
    normalized = _NON_ALNUM.sub("_", value.strip().lower()).strip("_")
    return _MODEL_TYPE_ALIASES.get(normalized, normalized)


def find_profile(model_type: str) -> ArchitectureProfile | None:
    normalized = normalize_model_type(model_type)
    for profile in ARCHITECTURE_PROFILES:
        if normalized in profile.model_types:
            return profile
    return None


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

    mechanics = {"adapter_manifest", "architecture_discovery", "layer_stack"}
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


def _require_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be uppercase 64-hex SHA-256")


__all__ = [
    "ARCHITECTURE_PROFILES",
    "CAPABILITY_DEFINITIONS",
    "CLAIM_BOUNDARY",
    "RUNTIME_FEATURES",
    "SCHEMA_VERSION",
    "ArchitectureDeclaration",
    "ArchitectureDiscovery",
    "CapabilityPlan",
    "InterpretabilityAdapterPlan",
    "LayerHookPlan",
    "ModelIdentity",
    "RuntimeVerification",
    "build_interpretability_adapter_plan",
    "canonical_json_bytes",
    "discover_loaded_architecture",
    "find_profile",
    "normalize_model_type",
    "verify_serialized_plan",
]
