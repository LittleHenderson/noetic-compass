from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, replace
import json
from pathlib import Path
import pickle

import pytest

import cas_harness_v2.universal_probe_contract as probe_module
from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    BEHAVIOR_GENERATION,
    CLOSED_WEIGHT,
    COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    HIDDEN_STATE_OBSERVATION,
    LOGPROB_OBSERVATION,
    OPEN_WEIGHT,
    STEERING_INTERVENTION,
    SUPPORTED_WITH_EVIDENCE,
    TOOL_CALL_OBSERVATION,
    UNAVAILABLE_BY_ACCESS_MODEL,
    UNAVAILABLE_NOT_IMPLEMENTED,
    UNKNOWN_UNVERIFIED,
    build_comparison_capability_evidence_body,
    build_comparison_model_capabilities,
    build_comparison_model_configuration_body,
    build_comparison_model_identity,
    build_comparison_model_weight_identity_body,
)
from cas_harness_v2.universal_probe_contract import (
    ALL_TOKENS,
    AMBIGUOUS_CONFIG_STRUCTURE,
    AMBIGUOUS_VALIDATION,
    ARCHITECTURE_DISCOVERY_EVIDENCE_MEDIA_TYPE,
    ARCHITECTURE_FAMILIES,
    ATTENTION,
    ATTENTION_OUTPUT,
    BFLOAT16,
    CAPABILITY_UNAVAILABLE_BY_ACCESS_MODEL,
    CONFIG_STRUCTURE_RECORDED,
    DENSE_DECODER,
    DISCOVERY_UNAVAILABLE_BY_ACCESS_MODEL,
    ENCODER_DECODER,
    EXPERT,
    EXPERT_OUTPUT,
    FLOAT16,
    GENERATED_PROBE_ADAPTER_MANIFEST_MEDIA_TYPE,
    IDENTITY_TRANSFORM,
    LAST_TOKEN,
    MIXTURE_OF_EXPERTS,
    MLP,
    MLP_OUTPUT,
    MULTIMODAL,
    MULTIMODAL_FUSION,
    MULTIMODAL_FUSION_TRANSFORM,
    MULTIMODAL_SITE,
    NO_QUANTIZATION,
    NON_AUTHORITY,
    POST,
    PROBE_VALIDATION_EVIDENCE_MEDIA_TYPE,
    RECURRENT,
    RECURRENT_STATE,
    RECURRENT_STATE_TRANSFORM,
    REPLAY_FIXTURE_MATCH,
    REPLAY_ONLY,
    RESIDUAL,
    RESIDUAL_STREAM,
    ROUTER,
    ROUTER_LOGITS,
    ROUTER_LOGITS_TRANSFORM,
    SELECT_EXPERT_TRANSFORM,
    SELECT_HEAD_TRANSFORM,
    SSM_RECURRENT,
    STRUCTURE_ONLY,
    UNMEASURED,
    UNIVERSAL_PROBE_CANARY_PLAN_MEDIA_TYPE,
    UniversalProbeBackendUnavailableError,
    UniversalProbeContractValidationError,
    UniversalProbeReplayRequest,
    ProbeSiteSpec,
    ProbeValidationResult,
    ReplayUniversalProbeBackend,
    UnavailableUniversalProbeBackend,
    build_architecture_discovery_evidence_body,
    build_architecture_discovery_receipt,
    build_generated_probe_adapter_manifest,
    build_probe_validation_evidence_body,
    build_probe_validation_receipt,
    build_replay_universal_probe_backend,
    build_unavailable_universal_probe_backend,
    build_universal_probe_canary_plan,
    load_architecture_discovery_receipt,
    load_generated_probe_adapter_manifest,
    load_probe_validation_receipt,
    load_universal_probe_canary_plan,
    probe_capability_state,
    replay_architecture_discovery_receipt,
    replay_generated_probe_adapter_manifest,
    replay_probe_validation_receipt,
    replay_universal_probe_canary_plan,
    replay_universal_probe_validation,
)


def ref(artifact_id: str, body: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(body),
        byte_length=len(body),
        media_type=media_type,
    )


FAMILY_PATHS = {
    DENSE_DECODER: (
        "config.hidden_size",
        "config.intermediate_size",
        "config.num_attention_heads",
        "config.num_hidden_layers",
    ),
    ENCODER_DECODER: (
        "config.d_model",
        "config.decoder_attention_heads",
        "config.decoder_layers",
        "config.encoder_attention_heads",
        "config.encoder_layers",
    ),
    MIXTURE_OF_EXPERTS: (
        "config.hidden_size",
        "config.num_experts",
        "config.num_experts_per_tok",
        "config.num_hidden_layers",
    ),
    SSM_RECURRENT: (
        "config.conv_kernel",
        "config.hidden_size",
        "config.num_hidden_layers",
        "config.state_size",
    ),
    MULTIMODAL: (
        "config.hidden_size",
        "config.projector_type",
        "config.text_hidden_size",
        "config.vision_hidden_size",
    ),
}

FAMILY_SITES = {
    DENSE_DECODER: (RESIDUAL, ATTENTION, MLP),
    ENCODER_DECODER: (RESIDUAL, ATTENTION, MLP),
    MIXTURE_OF_EXPERTS: (RESIDUAL, ATTENTION, MLP, ROUTER, EXPERT),
    SSM_RECURRENT: (RESIDUAL, RECURRENT),
    MULTIMODAL: (RESIDUAL, ATTENTION, MLP, MULTIMODAL_SITE),
}

PROJECTIONS = {
    RESIDUAL: RESIDUAL_STREAM,
    ATTENTION: ATTENTION_OUTPUT,
    MLP: MLP_OUTPUT,
    ROUTER: ROUTER_LOGITS,
    EXPERT: EXPERT_OUTPUT,
    RECURRENT: RECURRENT_STATE,
    MULTIMODAL_SITE: MULTIMODAL_FUSION,
}

TRANSFORMS = {
    RESIDUAL: IDENTITY_TRANSFORM,
    ATTENTION: SELECT_HEAD_TRANSFORM,
    MLP: IDENTITY_TRANSFORM,
    ROUTER: ROUTER_LOGITS_TRANSFORM,
    EXPERT: SELECT_EXPERT_TRANSFORM,
    RECURRENT: RECURRENT_STATE_TRANSFORM,
    MULTIMODAL_SITE: MULTIMODAL_FUSION_TRANSFORM,
}


@dataclass(frozen=True)
class Bundle:
    identity: object
    capabilities: object
    configuration_ref: ArtifactRef
    configuration_bytes: bytes
    discovery: object
    manifest: object
    validation: object
    plan: object


def _machine_suffix(family: str) -> str:
    return family.lower().replace("_", "-")


def make_sites(family: str, version: str = "universal-probe-v1") -> tuple[ProbeSiteSpec, ...]:
    result = []
    for index, semantic in enumerate(FAMILY_SITES[family]):
        lowered = semantic.lower()
        result.append(
            ProbeSiteSpec(
                site_id=f"site-{lowered}",
                semantic_site=semantic,
                semantic_projection=PROJECTIONS[semantic],
                native_path=f"model.layers.0.{lowered}",
                hook_location=POST,
                layer_index=0,
                token_scope=ALL_TOKENS if semantic != RECURRENT else LAST_TOKEN,
                head_index=0 if semantic == ATTENTION else None,
                expert_index=0 if semantic == EXPERT else None,
                owning_rank=index,
                shape=(1, 8, 16),
                dtype=FLOAT16,
                quantization=NO_QUANTIZATION,
                transform=TRANSFORMS[semantic],
                adapter_version=version,
            )
        )
    return tuple(result)


def make_result(
    *,
    identity: object,
    configuration_ref: ArtifactRef,
    manifest: object,
    site: ProbeSiteSpec,
) -> ProbeValidationResult:
    evidence_id = f"validation-evidence-{site.site_id}"
    evidence_bytes = build_probe_validation_evidence_body(
        evidence_id=evidence_id,
        identity=identity,
        configuration_ref=configuration_ref,
        manifest_ref=manifest.artifact_ref,
        site=site,
    )
    evidence_ref = ref(
        evidence_id, evidence_bytes, PROBE_VALIDATION_EVIDENCE_MEDIA_TYPE
    )
    return ProbeValidationResult(
        site_id=site.site_id,
        validation_state=REPLAY_FIXTURE_MATCH,
        observed_native_path=site.native_path,
        observed_semantic_projection=site.semantic_projection,
        observed_hook_location=site.hook_location,
        observed_layer_index=site.layer_index,
        observed_token_scope=site.token_scope,
        observed_head_index=site.head_index,
        observed_expert_index=site.expert_index,
        observed_owning_rank=site.owning_rank,
        observed_shape=site.shape,
        observed_dtype=site.dtype,
        observed_quantization=site.quantization,
        observed_transform=site.transform,
        hook_registration_count=1,
        nonempty_capture=True,
        sentinel_roundtrip=True,
        zero_control_unchanged=True,
        sham_control_unchanged=True,
        evidence_ref=evidence_ref,
        evidence_bytes=evidence_bytes,
        ambiguity_reason=None,
    )


def make_open_model(family: str) -> tuple[object, object, ArtifactRef, bytes]:
    suffix = _machine_suffix(family)
    weight_bytes = build_comparison_model_weight_identity_body(
        provider="fixture-provider",
        model_id=f"fixture/{suffix}",
        revision="fixture-revision-20260810",
    )
    weight_ref = ref(
        f"weights-{suffix}",
        weight_bytes,
        COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    )
    identity = build_comparison_model_identity(
        identity_id=f"identity-{suffix}",
        access_kind=OPEN_WEIGHT,
        provider="fixture-provider",
        model_id=f"fixture/{suffix}",
        revision="fixture-revision-20260810",
        weight_artifact_ref=weight_ref,
        weight_artifact_bytes=weight_bytes,
    )
    configuration_bytes = build_comparison_model_configuration_body(
        configuration_id=f"configuration-{suffix}", identity=identity
    )
    configuration_ref = ref(
        f"configuration-{suffix}",
        configuration_bytes,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    )
    statuses = {
        BEHAVIOR_GENERATION: UNKNOWN_UNVERIFIED,
        TOOL_CALL_OBSERVATION: UNKNOWN_UNVERIFIED,
        LOGPROB_OBSERVATION: UNAVAILABLE_NOT_IMPLEMENTED,
        HIDDEN_STATE_OBSERVATION: SUPPORTED_WITH_EVIDENCE,
        ACTIVATION_CAPTURE: SUPPORTED_WITH_EVIDENCE,
        STEERING_INTERVENTION: UNAVAILABLE_NOT_IMPLEMENTED,
    }
    evidence_bytes = {}
    evidence_refs = {}
    for capability_name in statuses:
        if statuses[capability_name] == SUPPORTED_WITH_EVIDENCE:
            evidence_id = f"capability-{capability_name.lower()}-{suffix}"
            body = build_comparison_capability_evidence_body(
                evidence_id=evidence_id,
                capability_name=capability_name,
                identity=identity,
                configuration_ref=configuration_ref,
            )
            evidence_bytes[capability_name] = body
            evidence_refs[capability_name] = ref(
                evidence_id, body, COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE
            )
        else:
            evidence_bytes[capability_name] = None
            evidence_refs[capability_name] = None
    capabilities = build_comparison_model_capabilities(
        capabilities_id=f"capabilities-{suffix}",
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=statuses,
        capability_evidence_refs=evidence_refs,
        capability_evidence_bytes=evidence_bytes,
    )
    return identity, capabilities, configuration_ref, configuration_bytes


def make_closed_model() -> tuple[object, object, ArtifactRef, bytes]:
    identity = build_comparison_model_identity(
        identity_id="identity-closed",
        access_kind=CLOSED_WEIGHT,
        provider="fixture-provider",
        model_id="fixture/closed",
        revision="fixture-revision-20260810",
        weight_artifact_ref=None,
    )
    configuration_bytes = build_comparison_model_configuration_body(
        configuration_id="configuration-closed", identity=identity
    )
    configuration_ref = ref(
        "configuration-closed",
        configuration_bytes,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    )
    statuses = {
        BEHAVIOR_GENERATION: UNKNOWN_UNVERIFIED,
        TOOL_CALL_OBSERVATION: UNKNOWN_UNVERIFIED,
        LOGPROB_OBSERVATION: UNAVAILABLE_BY_ACCESS_MODEL,
        HIDDEN_STATE_OBSERVATION: UNAVAILABLE_BY_ACCESS_MODEL,
        ACTIVATION_CAPTURE: UNAVAILABLE_BY_ACCESS_MODEL,
        STEERING_INTERVENTION: UNAVAILABLE_BY_ACCESS_MODEL,
    }
    capabilities = build_comparison_model_capabilities(
        capabilities_id="capabilities-closed",
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=statuses,
        capability_evidence_refs={name: None for name in statuses},
        capability_evidence_bytes={name: None for name in statuses},
    )
    return identity, capabilities, configuration_ref, configuration_bytes


def make_bundle(family: str = DENSE_DECODER) -> Bundle:
    suffix = _machine_suffix(family)
    identity, capabilities, configuration_ref, configuration_bytes = make_open_model(
        family
    )
    discovery_evidence_bytes = build_architecture_discovery_evidence_body(
        evidence_id=f"discovery-evidence-{suffix}",
        identity=identity,
        configuration_ref=configuration_ref,
        discovery_state=CONFIG_STRUCTURE_RECORDED,
        architecture_family=family,
        candidate_families=(),
        observed_config_paths=FAMILY_PATHS[family],
    )
    discovery_evidence_ref = ref(
        f"discovery-evidence-{suffix}",
        discovery_evidence_bytes,
        ARCHITECTURE_DISCOVERY_EVIDENCE_MEDIA_TYPE,
    )
    discovery = build_architecture_discovery_receipt(
        discovery_id=f"discovery-{suffix}",
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        discovery_state=CONFIG_STRUCTURE_RECORDED,
        architecture_family=family,
        candidate_families=(),
        observed_config_paths=FAMILY_PATHS[family],
        evidence_ref=discovery_evidence_ref,
        evidence_bytes=discovery_evidence_bytes,
    )
    sites = make_sites(family)
    manifest = build_generated_probe_adapter_manifest(
        manifest_id=f"manifest-{suffix}",
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        adapter_version="universal-probe-v1",
        sites=sites,
        remote_code_required=False,
    )
    results = tuple(
        make_result(
            identity=identity,
            configuration_ref=configuration_ref,
            manifest=manifest,
            site=site,
        )
        for site in manifest.sites
    )
    validation = build_probe_validation_receipt(
        validation_id=f"validation-{suffix}",
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        results=results,
    )
    plan = build_universal_probe_canary_plan(
        plan_id=f"canary-plan-{suffix}",
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        max_canaries=len(sites),
    )
    return Bundle(
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        discovery=discovery,
        manifest=manifest,
        validation=validation,
        plan=plan,
    )


@pytest.mark.parametrize("family", ARCHITECTURE_FAMILIES)
def test_all_five_architecture_families_have_exact_semantic_probe_manifests(
    family: str,
) -> None:
    bundle = make_bundle(family)
    assert bundle.discovery.architecture_family == family
    assert bundle.discovery.discovery_state == CONFIG_STRUCTURE_RECORDED
    assert tuple(item.semantic_site for item in bundle.manifest.sites) == FAMILY_SITES[
        family
    ]
    assert bundle.validation.model_capability_state == UNMEASURED
    assert all(
        item.validation_state == REPLAY_FIXTURE_MATCH
        for item in bundle.validation.results
    )
    assert bundle.plan.max_canaries == len(bundle.manifest.sites)
    assert bundle.plan.payload["executed_canaries"] == 0
    for artifact in (
        bundle.discovery,
        bundle.manifest,
        bundle.validation,
        bundle.plan,
    ):
        assert artifact.payload["status"] == {
            "scope": STRUCTURE_ONLY,
            "authority": NON_AUTHORITY,
            "license": "NOT_LICENSED",
        }
        assert all(
            artifact.payload["boundary"][field] == 0
            for field in (
                "live_loader_calls",
                "model_calls",
                "provider_calls",
                "network_calls",
                "filesystem_calls",
                "hook_registrations",
                "torch_calls",
                "spend_microusd",
            )
        )


def test_every_artifact_round_trips_against_exact_dependencies() -> None:
    bundle = make_bundle()
    assert load_architecture_discovery_receipt(
        bundle.discovery.raw_bytes,
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        configuration_ref=bundle.configuration_ref,
        configuration_bytes=bundle.configuration_bytes,
        evidence_bytes=bundle.discovery.evidence_bytes,
    ) == bundle.discovery
    assert replay_architecture_discovery_receipt(
        bundle.discovery,
        identity=bundle.identity,
        capabilities=bundle.capabilities,
    ) == bundle.discovery
    assert load_generated_probe_adapter_manifest(
        bundle.manifest.raw_bytes,
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        discovery=bundle.discovery,
    ) == bundle.manifest
    assert replay_generated_probe_adapter_manifest(
        bundle.manifest,
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        discovery=bundle.discovery,
    ) == bundle.manifest
    evidence_bytes = {
        item.site_id: item.evidence_bytes for item in bundle.validation.results
    }
    assert load_probe_validation_receipt(
        bundle.validation.raw_bytes,
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        discovery=bundle.discovery,
        manifest=bundle.manifest,
        evidence_bytes_by_site=evidence_bytes,
    ) == bundle.validation
    assert replay_probe_validation_receipt(
        bundle.validation,
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        discovery=bundle.discovery,
        manifest=bundle.manifest,
    ) == bundle.validation
    assert load_universal_probe_canary_plan(
        bundle.plan.raw_bytes,
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        discovery=bundle.discovery,
        manifest=bundle.manifest,
    ) == bundle.plan
    assert replay_universal_probe_canary_plan(
        bundle.plan,
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        discovery=bundle.discovery,
        manifest=bundle.manifest,
    ) == bundle.plan


def test_config_only_discovery_allows_ambiguity_without_a_family_claim() -> None:
    identity, capabilities, configuration_ref, configuration_bytes = make_open_model(
        DENSE_DECODER
    )
    candidates = (DENSE_DECODER, MIXTURE_OF_EXPERTS)
    paths = ("config.hidden_size", "config.num_hidden_layers")
    evidence_bytes = build_architecture_discovery_evidence_body(
        evidence_id="ambiguous-discovery-evidence",
        identity=identity,
        configuration_ref=configuration_ref,
        discovery_state=AMBIGUOUS_CONFIG_STRUCTURE,
        architecture_family=None,
        candidate_families=candidates,
        observed_config_paths=paths,
    )
    evidence_ref = ref(
        "ambiguous-discovery-evidence",
        evidence_bytes,
        ARCHITECTURE_DISCOVERY_EVIDENCE_MEDIA_TYPE,
    )
    discovery = build_architecture_discovery_receipt(
        discovery_id="ambiguous-discovery",
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        discovery_state=AMBIGUOUS_CONFIG_STRUCTURE,
        architecture_family=None,
        candidate_families=candidates,
        observed_config_paths=paths,
        evidence_ref=evidence_ref,
        evidence_bytes=evidence_bytes,
    )
    assert discovery.architecture_family is None
    assert discovery.candidate_families == candidates
    with pytest.raises(SchemaValidationError, match="unambiguous"):
        build_generated_probe_adapter_manifest(
            manifest_id="forbidden-ambiguous-manifest",
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            adapter_version="universal-probe-v1",
            sites=make_sites(DENSE_DECODER),
            remote_code_required=False,
        )


def test_closed_weight_mechanistic_capability_is_unavailable_by_access_model() -> None:
    identity, capabilities, configuration_ref, configuration_bytes = make_closed_model()
    assert probe_capability_state(
        identity=identity, capabilities=capabilities
    ) == CAPABILITY_UNAVAILABLE_BY_ACCESS_MODEL
    evidence_bytes = build_architecture_discovery_evidence_body(
        evidence_id="closed-discovery-evidence",
        identity=identity,
        configuration_ref=configuration_ref,
        discovery_state=DISCOVERY_UNAVAILABLE_BY_ACCESS_MODEL,
        architecture_family=None,
        candidate_families=(),
        observed_config_paths=(),
    )
    evidence_ref = ref(
        "closed-discovery-evidence",
        evidence_bytes,
        ARCHITECTURE_DISCOVERY_EVIDENCE_MEDIA_TYPE,
    )
    discovery = build_architecture_discovery_receipt(
        discovery_id="closed-discovery",
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        discovery_state=DISCOVERY_UNAVAILABLE_BY_ACCESS_MODEL,
        architecture_family=None,
        candidate_families=(),
        observed_config_paths=(),
        evidence_ref=evidence_ref,
        evidence_bytes=evidence_bytes,
    )
    assert discovery.discovery_state == DISCOVERY_UNAVAILABLE_BY_ACCESS_MODEL
    with pytest.raises(SchemaValidationError, match="unambiguous"):
        build_generated_probe_adapter_manifest(
            manifest_id="closed-manifest",
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            adapter_version="universal-probe-v1",
            sites=make_sites(DENSE_DECODER),
            remote_code_required=False,
        )


@pytest.mark.parametrize(
    ("family", "paths", "message"),
    (
        ("LLAMA_70B", FAMILY_PATHS[DENSE_DECODER], "one of"),
        (
            DENSE_DECODER,
            ("config.model_type", "config.num_hidden_layers"),
            "cannot infer architecture",
        ),
        (
            DENSE_DECODER,
            ("config.num_hidden_layers", "config.parameter_count"),
            "cannot infer architecture",
        ),
        (
            DENSE_DECODER,
            ("config.hidden_size", "config.num_hidden_layers"),
            "lacks required structural fields",
        ),
    ),
)
def test_false_family_names_and_name_or_parameter_inference_are_rejected(
    family: str,
    paths: tuple[str, ...],
    message: str,
) -> None:
    identity, _, configuration_ref, _ = make_open_model(DENSE_DECODER)
    with pytest.raises(SchemaValidationError, match=message):
        build_architecture_discovery_evidence_body(
            evidence_id="invalid-family-discovery",
            identity=identity,
            configuration_ref=configuration_ref,
            discovery_state=CONFIG_STRUCTURE_RECORDED,
            architecture_family=family,
            candidate_families=(),
            observed_config_paths=paths,
        )


def test_ambiguous_candidate_families_must_be_unique_and_in_fixed_order() -> None:
    identity, _, configuration_ref, _ = make_open_model(DENSE_DECODER)
    with pytest.raises(SchemaValidationError, match="fixed architecture-family order"):
        build_architecture_discovery_evidence_body(
            evidence_id="wrong-order-discovery",
            identity=identity,
            configuration_ref=configuration_ref,
            discovery_state=AMBIGUOUS_CONFIG_STRUCTURE,
            architecture_family=None,
            candidate_families=(MIXTURE_OF_EXPERTS, DENSE_DECODER),
            observed_config_paths=("config.hidden_size", "config.num_hidden_layers"),
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"observed_shape": (1, 8, 17)}, "shape, dtype, rank"),
        ({"observed_dtype": BFLOAT16}, "shape, dtype, rank"),
        ({"observed_owning_rank": 99}, "shape, dtype, rank"),
        ({"observed_native_path": "model.layers.1.residual"}, "shape, dtype, rank"),
        ({"hook_registration_count": 0}, "did not pass every exact control"),
        ({"hook_registration_count": 2}, "outside"),
        ({"nonempty_capture": False}, "did not pass every exact control"),
        ({"sentinel_roundtrip": False}, "did not pass every exact control"),
        ({"zero_control_unchanged": False}, "did not pass every exact control"),
        ({"sham_control_unchanged": False}, "did not pass every exact control"),
    ),
)
def test_validation_rejects_wrong_shape_dtype_rank_hook_and_control_results(
    changes: dict[str, object],
    message: str,
) -> None:
    bundle = make_bundle()
    bad = replace(bundle.validation.results[0], **changes)
    with pytest.raises(SchemaValidationError, match=message):
        build_probe_validation_receipt(
            validation_id="bad-validation",
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
            manifest=bundle.manifest,
            results=(bad, *bundle.validation.results[1:]),
        )


def test_whole_block_semantic_substitution_is_rejected() -> None:
    with pytest.raises(SchemaValidationError, match="whole block"):
        ProbeSiteSpec(
            site_id="wrong-attention-projection",
            semantic_site=ATTENTION,
            semantic_projection=RESIDUAL_STREAM,
            native_path="model.layers.0.block",
            hook_location=POST,
            layer_index=0,
            token_scope=ALL_TOKENS,
            head_index=0,
            expert_index=None,
            owning_rank=0,
            shape=(1, 8, 16),
            dtype=FLOAT16,
            quantization=NO_QUANTIZATION,
            transform=SELECT_HEAD_TRANSFORM,
            adapter_version="universal-probe-v1",
        )


def test_missing_projection_and_duplicate_hook_are_rejected() -> None:
    bundle = make_bundle()
    with pytest.raises(SchemaValidationError, match="missing required semantic"):
        build_generated_probe_adapter_manifest(
            manifest_id="missing-mlp-manifest",
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
            adapter_version="universal-probe-v1",
            sites=bundle.manifest.sites[:-1],
            remote_code_required=False,
        )
    duplicate = replace(bundle.manifest.sites[0], site_id="duplicate-residual")
    with pytest.raises(SchemaValidationError, match="duplicate hook"):
        build_generated_probe_adapter_manifest(
            manifest_id="duplicate-hook-manifest",
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
            adapter_version="universal-probe-v1",
            sites=(*bundle.manifest.sites, duplicate),
            remote_code_required=False,
        )


def test_head_expert_dtype_quantization_and_shape_contracts_are_exact() -> None:
    attention = make_sites(DENSE_DECODER)[1]
    with pytest.raises(SchemaValidationError, match="require one exact head"):
        replace(attention, head_index=None)
    with pytest.raises(SchemaValidationError, match="head/expert indices are forbidden"):
        replace(make_sites(DENSE_DECODER)[0], expert_index=0)
    with pytest.raises(SchemaValidationError, match="INT8 quantization requires"):
        replace(attention, quantization="INT8", dtype=FLOAT16)
    with pytest.raises(SchemaValidationError, match="rank-2 through rank-8"):
        replace(attention, shape=(16,))


def test_remote_code_and_dynamic_native_paths_are_rejected() -> None:
    bundle = make_bundle()
    with pytest.raises(SchemaValidationError, match="remote-code-required"):
        build_generated_probe_adapter_manifest(
            manifest_id="remote-code-manifest",
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
            adapter_version="universal-probe-v1",
            sites=bundle.manifest.sites,
            remote_code_required=True,
        )
    with pytest.raises(SchemaValidationError, match="static dotted"):
        replace(
            bundle.manifest.sites[0],
            native_path="model.layers[0].residual()",
        )
    with pytest.raises(SchemaValidationError, match="dynamic or executable"):
        replace(bundle.manifest.sites[0], native_path="model.__dict__.residual")


def test_ambiguous_validation_is_explicit_and_never_promotes_model_capability() -> None:
    bundle = make_bundle()
    first = bundle.validation.results[0]
    ambiguous = ProbeValidationResult(
        site_id=first.site_id,
        validation_state=AMBIGUOUS_VALIDATION,
        observed_native_path=None,
        observed_semantic_projection=None,
        observed_hook_location=None,
        observed_layer_index=None,
        observed_token_scope=None,
        observed_head_index=None,
        observed_expert_index=None,
        observed_owning_rank=None,
        observed_shape=None,
        observed_dtype=None,
        observed_quantization=None,
        observed_transform=None,
        hook_registration_count=0,
        nonempty_capture=False,
        sentinel_roundtrip=False,
        zero_control_unchanged=False,
        sham_control_unchanged=False,
        evidence_ref=None,
        evidence_bytes=None,
        ambiguity_reason="STATIC_SIGNATURE_HAS_MULTIPLE_MATCHES",
    )
    receipt = build_probe_validation_receipt(
        validation_id="ambiguous-validation",
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        discovery=bundle.discovery,
        manifest=bundle.manifest,
        results=(ambiguous, *bundle.validation.results[1:]),
    )
    assert receipt.results[0].validation_state == AMBIGUOUS_VALIDATION
    assert receipt.model_capability_state == UNMEASURED
    assert "aggregate_pass" not in receipt.payload
    assert "licensed" not in receipt.payload


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("executed_canaries", 1, "outside"),
        ("attempts_per_canary", 2, "outside"),
        ("max_canaries", 999, "outside"),
        ("execution_state", "EXECUTED", "NOT_EXECUTED"),
        ("retry", "ALLOWED", "replacement and retry"),
    ),
)
def test_canary_plan_tampering_cannot_create_execution_or_extra_attempts(
    field: str,
    value: object,
    message: str,
) -> None:
    bundle = make_bundle()
    payload = json.loads(bundle.plan.raw_bytes)
    payload[field] = value
    with pytest.raises(SchemaValidationError, match=message):
        load_universal_probe_canary_plan(
            canonical_json_bytes(payload),
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
            manifest=bundle.manifest,
        )


def test_zero_call_boundary_tampering_and_model_capability_promotion_fail_closed() -> None:
    bundle = make_bundle()
    plan_payload = json.loads(bundle.plan.raw_bytes)
    plan_payload["boundary"]["model_calls"] = 1
    with pytest.raises(SchemaValidationError, match="zero-call boundary"):
        load_universal_probe_canary_plan(
            canonical_json_bytes(plan_payload),
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
            manifest=bundle.manifest,
        )

    validation_payload = json.loads(bundle.validation.raw_bytes)
    validation_payload["model_probe_capability_state"] = (
        CAPABILITY_UNAVAILABLE_BY_ACCESS_MODEL
    )
    with pytest.raises(SchemaValidationError, match="inferred model capability"):
        load_probe_validation_receipt(
            canonical_json_bytes(validation_payload),
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
            manifest=bundle.manifest,
            evidence_bytes_by_site={
                item.site_id: item.evidence_bytes
                for item in bundle.validation.results
            },
        )


def test_loaded_manifest_cannot_enable_remote_code() -> None:
    bundle = make_bundle()
    payload = json.loads(bundle.manifest.raw_bytes)
    payload["remote_code_required"] = True
    with pytest.raises(SchemaValidationError, match="reject remote code"):
        load_generated_probe_adapter_manifest(
            canonical_json_bytes(payload),
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
        )


def test_exact_model_revision_configuration_and_capability_binding_rejects_substitution() -> None:
    dense = make_bundle(DENSE_DECODER)
    moe = make_bundle(MIXTURE_OF_EXPERTS)
    with pytest.raises(SchemaValidationError):
        replay_architecture_discovery_receipt(
            dense.discovery,
            identity=moe.identity,
            capabilities=moe.capabilities,
        )
    with pytest.raises(SchemaValidationError, match="configuration bytes"):
        load_architecture_discovery_receipt(
            dense.discovery.raw_bytes,
            identity=dense.identity,
            capabilities=dense.capabilities,
            configuration_ref=dense.configuration_ref,
            configuration_bytes=b"substituted configuration",
            evidence_bytes=dense.discovery.evidence_bytes,
        )

    object.__setattr__(dense.capabilities, "revision", "forged-revision-20260811")
    with pytest.raises(SchemaValidationError):
        replay_generated_probe_adapter_manifest(
            dense.manifest,
            identity=dense.identity,
            capabilities=dense.capabilities,
            discovery=dense.discovery,
        )


def test_artifact_mutation_replacement_and_forgery_fail_exact_replay() -> None:
    bundle = make_bundle()
    with pytest.raises(TypeError):
        bundle.manifest.payload["manifest_id"] = "mutated"

    replaced_manifest = replace(bundle.manifest, raw_bytes=b"forged")
    with pytest.raises(SchemaValidationError):
        replay_generated_probe_adapter_manifest(
            replaced_manifest,
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
        )

    forged = object.__new__(type(bundle.manifest))
    with pytest.raises(SchemaValidationError, match="storage projections"):
        replay_generated_probe_adapter_manifest(
            forged,
            identity=bundle.identity,
            capabilities=bundle.capabilities,
            discovery=bundle.discovery,
        )


def test_request_closure_rejects_artifact_id_and_content_aliases() -> None:
    bundle = make_bundle()
    expected = UniversalProbeReplayRequest(
        identity_ref=bundle.identity.artifact_ref,
        capabilities_ref=bundle.capabilities.artifact_ref,
        configuration_ref=bundle.configuration_ref,
        discovery_ref=bundle.discovery.artifact_ref,
        manifest_ref=bundle.manifest.artifact_ref,
        validation_ref=bundle.validation.artifact_ref,
        canary_plan_ref=bundle.plan.artifact_ref,
    )
    assert expected.manifest_ref == bundle.manifest.artifact_ref

    content_alias = ArtifactRef(
        artifact_id="capabilities-content-alias",
        sha256=bundle.identity.artifact_ref.sha256,
        byte_length=bundle.identity.artifact_ref.byte_length,
        media_type=bundle.capabilities.artifact_ref.media_type,
    )
    with pytest.raises(SchemaValidationError, match="content identity"):
        replace(expected, capabilities_ref=content_alias)

    id_alias = ArtifactRef(
        artifact_id=bundle.identity.artifact_ref.artifact_id,
        sha256=bundle.capabilities.artifact_ref.sha256,
        byte_length=bundle.capabilities.artifact_ref.byte_length,
        media_type=bundle.capabilities.artifact_ref.media_type,
    )
    with pytest.raises(SchemaValidationError, match="artifact ID"):
        replace(expected, capabilities_ref=id_alias)


def test_replay_backend_is_exact_single_use_and_returns_a_detached_receipt() -> None:
    bundle = make_bundle()
    backend, request = build_replay_universal_probe_backend(
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        discovery=bundle.discovery,
        manifest=bundle.manifest,
        validation=bundle.validation,
        plan=bundle.plan,
    )
    assert backend.mode == REPLAY_ONLY
    assert backend.status == STRUCTURE_ONLY
    assert backend.authority == NON_AUTHORITY
    assert backend.consumed is False
    with pytest.raises(SchemaValidationError, match="exact sealed request object"):
        replay_universal_probe_validation(backend, replace(request))
    result = replay_universal_probe_validation(backend, request)
    assert result == bundle.validation
    assert result is not bundle.validation
    assert backend.consumed is True
    with pytest.raises(SchemaValidationError, match="already consumed"):
        replay_universal_probe_validation(backend, request)


@pytest.mark.parametrize(
    "operation",
    (
        lambda value: copy.copy(value),
        lambda value: copy.deepcopy(value),
        lambda value: pickle.dumps(value),
        lambda value: value.__replace__(),
    ),
)
def test_backends_reject_copy_deepcopy_pickle_and_replace(operation) -> None:
    bundle = make_bundle()
    replay_backend, _ = build_replay_universal_probe_backend(
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        discovery=bundle.discovery,
        manifest=bundle.manifest,
        validation=bundle.validation,
        plan=bundle.plan,
    )
    unavailable = build_unavailable_universal_probe_backend(
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        configuration_ref=bundle.configuration_ref,
        configuration_bytes=bundle.configuration_bytes,
        reason="NO_LIVE_PROBE_BACKEND",
    )
    with pytest.raises(TypeError, match="cannot be copied"):
        operation(replay_backend)
    with pytest.raises(TypeError, match="cannot be copied"):
        operation(unavailable)


def test_direct_construction_subclassing_and_object_forgery_are_rejected() -> None:
    with pytest.raises(TypeError, match="factory-only"):
        ReplayUniversalProbeBackend()
    with pytest.raises(TypeError, match="factory-only"):
        UnavailableUniversalProbeBackend()
    with pytest.raises(TypeError, match="cannot be subclassed"):
        class ForgedReplaySubclass(ReplayUniversalProbeBackend):
            pass
    replay_forgery = object.__new__(ReplayUniversalProbeBackend)
    unavailable_forgery = object.__new__(UnavailableUniversalProbeBackend)
    with pytest.raises(SchemaValidationError, match="process-sealed"):
        _ = replay_forgery.mode
    with pytest.raises(SchemaValidationError, match="process-sealed"):
        _ = unavailable_forgery.mode


def test_unavailable_backend_fails_before_inspecting_input() -> None:
    bundle = make_bundle()
    backend = build_unavailable_universal_probe_backend(
        identity=bundle.identity,
        capabilities=bundle.capabilities,
        configuration_ref=bundle.configuration_ref,
        configuration_bytes=bundle.configuration_bytes,
        reason="NO_LIVE_PROBE_BACKEND",
    )

    class ExplosiveInput:
        def __getattribute__(self, name):
            raise AssertionError(f"input was inspected: {name}")

    with pytest.raises(
        UniversalProbeBackendUnavailableError, match="NO_LIVE_PROBE_BACKEND"
    ):
        replay_universal_probe_validation(backend, ExplosiveInput())


def test_arbitrary_backend_is_rejected_without_calling_it() -> None:
    class ArbitraryBackend:
        called = False

        def replay(self, request):
            del request
            self.called = True
            raise AssertionError("arbitrary backend ran")

    backend = ArbitraryBackend()
    with pytest.raises(SchemaValidationError, match="not installed"):
        replay_universal_probe_validation(backend, object())
    assert backend.called is False


def test_module_has_no_live_loader_torch_provider_network_or_filesystem_imports() -> None:
    source_path = Path(probe_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots.isdisjoint(
        {
            "torch",
            "transformers",
            "accelerate",
            "requests",
            "httpx",
            "socket",
            "subprocess",
            "urllib",
            "os",
            "pathlib",
        }
    )
    lowered = source_path.read_text(encoding="utf-8").lower()
    for forbidden in (
        "trust_remote_code=true",
        "from_pretrained(",
        "register_forward_hook(",
        "urlopen(",
        "requests.get(",
        "subprocess.run(",
    ):
        assert forbidden not in lowered


def test_public_export_surface_is_unique_and_backend_neutral() -> None:
    assert len(probe_module.__all__) == len(set(probe_module.__all__))
    assert all(hasattr(probe_module, name) for name in probe_module.__all__)
    assert not any(
        word in name.lower()
        for name in probe_module.__all__
        for word in ("runpod", "huggingface", "openai", "anthropic", "torch")
    )
