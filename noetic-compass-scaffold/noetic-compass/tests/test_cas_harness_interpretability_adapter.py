"""Offline tests for inert planning and safe executable-adapter generation."""

from __future__ import annotations

import ast
import builtins
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

import api.services.cas_harness_interpretability_adapter as adapter_module
from api.services.cas_harness_interpretability_adapter import (
    ADAPTER_ENGINE_API_VERSION,
    ArchitectureDeclaration,
    ExecutableAdapterArtifact,
    EXECUTABLE_GENERATION_STATUS,
    LayerHookPlan,
    MODEL_BYTE_BINDING_STATUS,
    ModelIdentity,
    RuntimeVerification,
    build_interpretability_adapter_plan,
    canonical_json_bytes,
    discover_loaded_architecture,
    generate_executable_adapter_artifact,
    normalize_model_type,
    verify_generated_adapter_artifact,
    verify_serialized_plan,
)


CONFIG_SHA = "A" * 64
WEIGHTS_SHA = "B" * 64
RUNTIME_SHA = "C" * 64
REVISION = "1" * 40


class Hookable:
    def register_forward_hook(self, _callback):  # pragma: no cover - never called
        raise AssertionError("architecture discovery must not install hooks")


class Layer(Hookable):
    def __init__(self, attention_name: str, mlp_name: str) -> None:
        setattr(self, attention_name, Hookable())
        setattr(self, mlp_name, Hookable())


def fake_model(model_type: str, count: int = 3):
    config = SimpleNamespace(
        model_type=model_type,
        num_hidden_layers=count,
        hidden_size=64,
        num_attention_heads=4,
    )
    if model_type == "gpt_neox":
        return SimpleNamespace(
            config=config,
            gpt_neox=SimpleNamespace(
                layers=[Layer("attention", "mlp") for _ in range(count)]
            )
        )
    if model_type == "llama":
        return SimpleNamespace(
            config=config,
            model=SimpleNamespace(
                layers=[Layer("self_attn", "mlp") for _ in range(count)]
            )
        )
    if model_type == "gpt2":
        return SimpleNamespace(
            config=config,
            transformer=SimpleNamespace(
                h=[Layer("attn", "mlp") for _ in range(count)]
            )
        )
    if model_type == "mpt":
        return SimpleNamespace(
            config=config,
            transformer=SimpleNamespace(
                blocks=[Layer("attn", "ffn") for _ in range(count)]
            )
        )
    raise AssertionError(model_type)


class ExecutableConfig:
    def __init__(self, *, count: int = 2) -> None:
        self.model_type = "llama"
        self.num_hidden_layers = count
        self.hidden_size = 64
        self.num_attention_heads = 4


class ExecutableHook:
    def __init__(self) -> None:
        self.callbacks: list[object] = []

    def register_forward_hook(self, callback):
        self.callbacks.append(callback)
        return ("registered", len(self.callbacks))


class ExecutableLayer(ExecutableHook):
    def __init__(self) -> None:
        super().__init__()
        self.self_attn = ExecutableHook()
        self.mlp = ExecutableHook()


class ExecutableModel:
    def __init__(self, *, count: int = 2) -> None:
        self.config = ExecutableConfig(count=count)
        self.model = SimpleNamespace(
            layers=[ExecutableLayer() for _ in range(count)]
        )


def executable_declaration(count: int = 2) -> ArchitectureDeclaration:
    return ArchitectureDeclaration(
        model_type="llama",
        num_hidden_layers=count,
        hidden_size=64,
        num_attention_heads=4,
    )


def executable_plan(
    model: ExecutableModel,
    *,
    identity_value: ModelIdentity | None = None,
):
    return build_interpretability_adapter_plan(
        model=model,
        identity=identity_value or identity(),
        declaration=executable_declaration(len(model.model.layers)),
    )


def generated_artifact(model: ExecutableModel | None = None):
    selected = model or ExecutableModel()
    return selected, generate_executable_adapter_artifact(
        model=selected,
        plan=executable_plan(selected),
    )


def import_generated_adapter(artifact, directory: Path):
    path = directory / artifact.source_filename
    path.write_bytes(artifact.source_bytes)
    module_name = f"_test_generated_{artifact.source_sha256.lower()}"
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def generated_identity_arguments(artifact) -> dict[str, str]:
    return {
        "engine_api_version": ADAPTER_ENGINE_API_VERSION,
        "profile_family": artifact.spec.profile_family,
        "model_byte_binding_status": MODEL_BYTE_BINDING_STATUS,
    }


def identity(**overrides):
    values = {
        "model_id": "org/model",
        "revision": REVISION,
        "config_sha256": CONFIG_SHA,
        "weights_manifest_sha256": WEIGHTS_SHA,
        "trust_remote_code": False,
    }
    values.update(overrides)
    return ModelIdentity(**values)


def declaration(model_type: str = "llama", count: int = 3):
    return ArchitectureDeclaration(
        model_type=model_type,
        num_hidden_layers=count,
        hidden_size=64,
        num_attention_heads=4,
    )


@pytest.mark.parametrize(
    ("model_type", "family", "stack", "attention", "mlp"),
    [
        ("gpt_neox", "gpt_neox", "gpt_neox.layers", "attention", "mlp"),
        ("llama", "llama_like", "model.layers", "self_attn", "mlp"),
        ("gpt2", "gpt2_like", "transformer.h", "attn", "mlp"),
        ("mpt", "mpt_like", "transformer.blocks", "attn", "ffn"),
    ],
)
def test_registered_architectures_are_discovered_without_running_model(
    model_type, family, stack, attention, mlp
):
    result = discover_loaded_architecture(fake_model(model_type), declaration(model_type))

    assert result.status == "STRUCTURE_VERIFIED"
    assert result.family == family
    assert result.layer_stack_attr == stack
    assert result.observed_layer_count == 3
    assert result.layer_hooks[0].attention_module == f"{stack}.0.{attention}"
    assert result.layer_hooks[0].mlp_module == f"{stack}.0.{mlp}"
    assert set(result.available_mechanics) >= {
        "adapter_manifest",
        "architecture_discovery",
        "attention_capture",
        "layer_stack",
        "mlp_capture",
        "residual_capture",
    }


def test_unknown_model_type_fails_closed_even_if_object_has_familiar_path():
    with pytest.raises(ValueError, match="unsupported model_type"):
        discover_loaded_architecture(fake_model("llama"), declaration("mamba"))


def test_declared_layer_count_must_equal_observed_count():
    model = fake_model("llama", count=2)
    model.config.num_hidden_layers = 3
    with pytest.raises(ValueError, match="layer-count mismatch"):
        discover_loaded_architecture(model, declaration("llama", count=3))


def test_missing_stack_path_fails_closed():
    config = SimpleNamespace(
        model_type="llama",
        num_hidden_layers=3,
        hidden_size=64,
        num_attention_heads=4,
    )
    with pytest.raises(ValueError, match="model layout missing model"):
        discover_loaded_architecture(SimpleNamespace(config=config), declaration("llama"))


def test_empty_stack_is_rejected():
    config = SimpleNamespace(
        model_type="llama",
        num_hidden_layers=1,
        hidden_size=64,
        num_attention_heads=4,
    )
    model = SimpleNamespace(config=config, model=SimpleNamespace(layers=[]))
    with pytest.raises(ValueError, match="empty"):
        discover_loaded_architecture(model, declaration("llama", count=1))


def test_non_hookable_attention_is_reported_missing_not_assumed():
    layer = Hookable()
    layer.self_attn = object()
    layer.mlp = Hookable()
    config = SimpleNamespace(
        model_type="llama",
        num_hidden_layers=1,
        hidden_size=64,
        num_attention_heads=4,
    )
    model = SimpleNamespace(config=config, model=SimpleNamespace(layers=[layer]))

    result = discover_loaded_architecture(model, declaration("llama", count=1))

    assert "attention_capture" not in result.available_mechanics
    assert result.layer_hooks[0].attention_module is None


def test_non_hookable_decoder_block_fails_closed_even_if_children_are_hookable():
    layer = SimpleNamespace(self_attn=Hookable(), mlp=Hookable())
    config = SimpleNamespace(
        model_type="llama",
        num_hidden_layers=1,
        hidden_size=64,
        num_attention_heads=4,
    )
    model = SimpleNamespace(config=config, model=SimpleNamespace(layers=[layer]))

    with pytest.raises(ValueError, match="decoder blocks lack register_forward_hook"):
        discover_loaded_architecture(model, declaration("llama", count=1))


def test_loaded_config_model_type_must_match_declaration():
    model = fake_model("llama")
    model.config.model_type = "mistral"
    with pytest.raises(ValueError, match="model_type mismatch"):
        discover_loaded_architecture(model, declaration("llama"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("num_hidden_layers", 4),
        ("hidden_size", 65),
        ("num_attention_heads", 5),
    ],
)
def test_loaded_config_dimensions_must_match_declaration(field, value):
    model = fake_model("llama")
    setattr(model.config, field, value)
    with pytest.raises(ValueError, match=field):
        discover_loaded_architecture(model, declaration("llama"))


def test_loaded_model_without_config_is_rejected():
    bare = SimpleNamespace(model=SimpleNamespace(layers=[Layer("self_attn", "mlp")]))
    with pytest.raises(ValueError, match="no config object"):
        discover_loaded_architecture(bare, declaration("llama", count=1))


def test_model_identity_rejects_unpinned_revision():
    with pytest.raises(ValueError, match="revision"):
        identity(revision="main").validate()


def test_model_identity_rejects_lowercase_or_short_hash():
    with pytest.raises(ValueError, match="config_sha256"):
        identity(config_sha256="a" * 64).validate()
    with pytest.raises(ValueError, match="weights_manifest_sha256"):
        identity(weights_manifest_sha256="B" * 63).validate()


def test_remote_code_is_outside_inert_boundary():
    with pytest.raises(ValueError, match="trust_remote_code"):
        identity(trust_remote_code=True).validate()


def test_static_plan_contains_all_fourteen_capabilities_and_never_claims_results():
    plan = build_interpretability_adapter_plan(
        model=fake_model("llama"),
        identity=identity(),
        declaration=declaration(),
    )

    assert len(plan.capabilities) == 14
    assert [item.capability_id for item in plan.capabilities] == [
        f"C{i:02d}" for i in range(1, 15)
    ]
    assert all(item.evidence_status == "NOT_RUN" for item in plan.capabilities)
    by_name = {item.name: item for item in plan.capabilities}
    assert by_name["hidden_state_analysis"].status == "MECHANICALLY_PLANNED_NOT_RUN"
    assert by_name["architecture_discovery"].status == "MECHANICALLY_PLANNED_NOT_RUN"
    assert by_name["harness_adapter_generation"].status == "MECHANICALLY_PLANNED_NOT_RUN"
    assert by_name["pre_output_trajectories"].status == "BLOCKED_MISSING_MECHANICS"
    assert set(by_name["pre_output_trajectories"].missing_mechanics) == {
        "generation_step_capture",
        "logit_capture",
    }
    assert by_name["hallucination_detection"].external_scientific_requirements == (
        "external_truth_labels",
        "abstention_policy",
        "surface_controls",
    )
    assert "NOT AN EXPERIMENT" in plan.claim_boundary
    plan.verify_hash()


def test_untrusted_runtime_receipt_reference_never_unlocks_mechanics():
    runtime = RuntimeVerification(
        receipt_sha256=RUNTIME_SHA,
        verified_features=(
            "generation_step_capture",
            "logit_capture",
            "output_replacement_intervention",
        ),
    )
    plan = build_interpretability_adapter_plan(
        model=fake_model("llama"),
        identity=identity(),
        declaration=declaration(),
        runtime_verification=runtime,
    )

    by_name = {item.name: item for item in plan.capabilities}
    for name in (
        "pre_output_trajectories",
        "pre_speech_interception",
        "ablation",
        "bounded_causal_steering",
        "reasoning_break_detection",
    ):
        assert by_name[name].status == "BLOCKED_MISSING_MECHANICS"
        assert by_name[name].evidence_status == "NOT_RUN"
    assert (
        plan.runtime_verification.to_dict()["trust_status"]
        == "UNTRUSTED_REFERENCE_ONLY_DOES_NOT_UNLOCK_MECHANICS"
    )


def test_runtime_verification_rejects_unknown_or_duplicate_features():
    with pytest.raises(ValueError, match="unknown runtime"):
        RuntimeVerification(RUNTIME_SHA, ("magic",)).validate()
    with pytest.raises(ValueError, match="duplicates"):
        RuntimeVerification(RUNTIME_SHA, ("logit_capture", "logit_capture")).validate()


def test_plan_serialization_is_deterministic_and_self_verifying():
    kwargs = {
        "model": fake_model("llama"),
        "identity": identity(),
        "declaration": declaration(),
    }
    first = build_interpretability_adapter_plan(**kwargs)
    second = build_interpretability_adapter_plan(**kwargs)

    assert first.plan_sha256 == second.plan_sha256
    assert first.to_json_bytes() == second.to_json_bytes()
    parsed = json.loads(first.to_json_bytes())
    verify_serialized_plan(parsed)


def test_serialized_plan_tamper_is_rejected():
    plan = build_interpretability_adapter_plan(
        model=fake_model("llama"), identity=identity(), declaration=declaration()
    )
    payload = json.loads(plan.to_json_bytes())
    payload["capabilities"][0]["evidence_status"] = "PASS"

    with pytest.raises(ValueError, match="evidence_status must remain NOT_RUN"):
        verify_serialized_plan(payload)


def test_rehashed_semantic_forgery_is_rejected_before_self_hash():
    import hashlib

    plan = build_interpretability_adapter_plan(
        model=fake_model("llama"), identity=identity(), declaration=declaration()
    )
    payload = json.loads(plan.to_json_bytes())
    payload["capabilities"][0]["evidence_status"] = "PASS"
    payload["claim_boundary"] = "EXECUTION AUTHORITY"
    unsigned = dict(payload)
    unsigned.pop("plan_sha256")
    payload["plan_sha256"] = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest().upper()

    with pytest.raises(ValueError, match="claim_boundary mismatch"):
        verify_serialized_plan(payload)


def test_rehashed_available_mechanics_forgery_is_rejected_as_not_structurally_derived():
    import hashlib

    plan = build_interpretability_adapter_plan(
        model=fake_model("llama"), identity=identity(), declaration=declaration()
    )
    payload = json.loads(plan.to_json_bytes())
    payload["discovery"]["available_mechanics"].extend(
        sorted(
            {
                "generation_step_capture",
                "logit_capture",
                "output_replacement_intervention",
            }
        )
    )
    payload["discovery"]["available_mechanics"].sort()
    for row in payload["capabilities"]:
        missing = sorted(
            set(row["mechanical_requirements"])
            - set(payload["discovery"]["available_mechanics"])
        )
        row["missing_mechanics"] = missing
        row["status"] = (
            "BLOCKED_MISSING_MECHANICS"
            if missing
            else "MECHANICALLY_PLANNED_NOT_RUN"
        )
    unsigned = dict(payload)
    unsigned.pop("plan_sha256")
    payload["plan_sha256"] = hashlib.sha256(
        canonical_json_bytes(unsigned)
    ).hexdigest().upper()

    with pytest.raises(ValueError, match="not structurally derived"):
        verify_serialized_plan(payload)


def test_serialized_identity_schema_and_unverified_binding_are_enforced():
    import hashlib

    plan = build_interpretability_adapter_plan(
        model=fake_model("llama"), identity=identity(), declaration=declaration()
    )
    payload = json.loads(plan.to_json_bytes())
    assert payload["identity"]["binding_status"] == (
        "DECLARED_REFERENCE_NOT_LOADED_MODEL_BYTE_VERIFIED"
    )
    payload["identity"] = {"anything": "goes"}
    unsigned = dict(payload)
    unsigned.pop("plan_sha256")
    payload["plan_sha256"] = hashlib.sha256(
        canonical_json_bytes(unsigned)
    ).hexdigest().upper()

    with pytest.raises(ValueError, match="identity keyset mismatch"):
        verify_serialized_plan(payload)


def test_serialized_plan_extra_key_is_rejected_before_hash_check():
    plan = build_interpretability_adapter_plan(
        model=fake_model("llama"), identity=identity(), declaration=declaration()
    )
    payload = json.loads(plan.to_json_bytes())
    payload["surprise"] = True

    with pytest.raises(ValueError, match="keyset mismatch"):
        verify_serialized_plan(payload)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (" GPT-NeoX ", "gpt_neox"),
        ("deepseekv3", "deepseek_v3"),
        ("COMMAND-R", "command_r"),
        ("qwen", "qwen2"),
    ],
)
def test_model_type_normalization(source, expected):
    assert normalize_model_type(source) == expected


def test_canonical_json_has_sorted_keys_one_lf_and_no_ascii_escaping():
    encoded = canonical_json_bytes({"z": "Δ", "a": 1})
    assert encoded == '{"a":1,"z":"Δ"}\n'.encode("utf-8")


def test_generated_artifact_binds_reviewable_source_profile_paths_and_not_run_statuses():
    model, artifact = generated_artifact()

    artifact.verify()
    verify_generated_adapter_artifact(artifact)
    manifest = artifact.to_manifest_dict()
    source = artifact.source_bytes.decode("utf-8")

    assert manifest["source_sha256"] == hashlib.sha256(
        artifact.source_bytes
    ).hexdigest().upper()
    assert manifest["engine_api_version"] == ADAPTER_ENGINE_API_VERSION
    assert manifest["model_byte_binding_status"] == MODEL_BYTE_BINDING_STATUS
    assert manifest["profile_family"] == "llama_like"
    assert manifest["model_type"] == "llama"
    assert manifest["layer_stack_attr"] == "model.layers"
    assert manifest["expected_layer_count"] == len(model.model.layers)
    assert manifest["generation_status"] == EXECUTABLE_GENERATION_STATUS
    assert len(manifest["capture_paths"]) == 6
    assert manifest["capture_paths"] == manifest["intervention_paths"]
    assert manifest["capability_evidence_statuses"] == [
        {"capability_id": f"C{index:02d}", "evidence_status": "NOT_RUN"}
        for index in range(1, 15)
    ]
    assert f"SPEC_SHA256 = '{artifact.spec.spec_sha256}'" in source
    assert "def capture_attachment_point(" in source
    assert "def intervention_attachment_point(" in source
    assert "DECLARED CONFIG/WEIGHT HASHES ARE NOT LOADED-MODEL BYTE ATTESTATION" in source
    assert 'SOURCE_SHA256_BINDING = "EXTERNAL_ARTIFACT_MANIFEST"' in source


def test_generated_source_round_trips_ast_compile_and_isolated_temp_import(tmp_path):
    _, artifact = generated_artifact()
    source_text = artifact.source_bytes.decode("utf-8", errors="strict")

    ast.parse(source_text, filename=artifact.source_filename, mode="exec")
    compile(source_text, artifact.source_filename, "exec")
    source_path = tmp_path / artifact.source_filename
    source_path.write_bytes(artifact.source_bytes)
    driver = r"""
import importlib.util
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("isolated_generated_adapter", path)
if spec is None or spec.loader is None:
    raise SystemExit("loader unavailable")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps({
    "engine": module.ENGINE_API_VERSION,
    "family": module.PROFILE_FAMILY,
    "layers": module.EXPECTED_LAYER_COUNT,
    "statuses": module.CAPABILITY_EVIDENCE_STATUSES,
}, sort_keys=True))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", driver, str(source_path)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert completed.returncode == 0, completed.stderr
    imported = json.loads(completed.stdout)
    assert imported == {
        "engine": ADAPTER_ENGINE_API_VERSION,
        "family": "llama_like",
        "layers": 2,
        "statuses": [[f"C{index:02d}", "NOT_RUN"] for index in range(1, 15)],
    }


def test_generation_does_not_eval_exec_or_import_generated_code(monkeypatch):
    model = ExecutableModel()
    plan = executable_plan(model)
    observed_calls: list[str] = []

    def observing(name, original):
        def wrapper(*args, **kwargs):
            observed_calls.append(f"{name}:{args[0] if args else ''}")
            return original(*args, **kwargs)

        return wrapper

    with monkeypatch.context() as context:
        context.setattr(builtins, "eval", observing("eval", builtins.eval))
        context.setattr(builtins, "exec", observing("exec", builtins.exec))
        context.setattr(
            builtins,
            "__import__",
            observing("__import__", builtins.__import__),
        )
        artifact = generate_executable_adapter_artifact(model=model, plan=plan)

    assert observed_calls == []
    assert artifact.source_sha256


def test_hostile_model_identity_text_is_hash_bound_but_never_copied_into_source(tmp_path):
    model = ExecutableModel()
    marker = tmp_path / "hostile_generation_marker"
    payload = (
        "x';__import__('pathlib').Path(" + repr(str(marker)) + ").write_text('owned');#"
    )
    plan = executable_plan(model, identity_value=identity(model_id=payload))

    artifact = generate_executable_adapter_artifact(model=model, plan=plan)

    assert payload.encode("utf-8") not in artifact.source_bytes
    assert str(marker).encode("utf-8") not in artifact.source_bytes
    import_generated_adapter(artifact, tmp_path)
    assert not marker.exists()


def test_hostile_traversal_hook_path_is_rejected_before_source_reconstruction():
    _, artifact = generated_artifact()
    original = artifact.spec.layer_hooks[0]
    hostile = LayerHookPlan(
        layer_index=original.layer_index,
        residual_module=original.residual_module,
        attention_module="model.layers.0.__class__",
        mlp_module=original.mlp_module,
    )
    bad_spec = replace(
        artifact.spec,
        layer_hooks=(hostile, *artifact.spec.layer_hooks[1:]),
    )
    bad_artifact = replace(artifact, spec=bad_spec)

    with pytest.raises(ValueError, match="attention path is not registered"):
        bad_artifact.verify()


def test_profile_registry_drift_is_rejected():
    _, artifact = generated_artifact()
    bad_artifact = replace(
        artifact,
        spec=replace(artifact.spec, profile_family="gpt_neox"),
    )

    with pytest.raises(ValueError, match="profile family drift"):
        bad_artifact.verify()


def test_generated_runtime_rejects_missing_hook_and_runtime_traversal(tmp_path):
    _, artifact = generated_artifact()
    module = import_generated_adapter(artifact, tmp_path)
    runtime_model = ExecutableModel()
    del runtime_model.model.layers[0].mlp

    with pytest.raises(RuntimeError, match="does not resolve"):
        module.verify_model(runtime_model, **generated_identity_arguments(artifact))

    intact_model = ExecutableModel()
    with pytest.raises(RuntimeError, match="closed allowlist"):
        module.capture_attachment_point(
            intact_model,
            "model.layers.0.__class__",
            **generated_identity_arguments(artifact),
        )


def test_generated_runtime_rejects_exact_class_subclass_mismatch(tmp_path):
    _, artifact = generated_artifact()
    module = import_generated_adapter(artifact, tmp_path)

    class ExecutableLayerSubclass(ExecutableLayer):
        pass

    runtime_model = ExecutableModel()
    runtime_model.model.layers[0] = ExecutableLayerSubclass()

    with pytest.raises(RuntimeError, match="class/subclass mismatch"):
        module.verify_model(runtime_model, **generated_identity_arguments(artifact))


def test_generated_runtime_rejects_post_generation_hook_module_alias_drift(tmp_path):
    _, artifact = generated_artifact()
    module = import_generated_adapter(artifact, tmp_path)
    runtime_model = ExecutableModel()
    runtime_model.model.layers[0].mlp = runtime_model.model.layers[0].self_attn

    with pytest.raises(RuntimeError, match="live hook-module alias drift"):
        module.verify_model(runtime_model, **generated_identity_arguments(artifact))


def test_generated_runtime_rejects_forged_class_identity_and_method_replacement(tmp_path):
    _, artifact = generated_artifact()
    module = import_generated_adapter(artifact, tmp_path)
    kwargs = generated_identity_arguments(artifact)

    forged_type = type("ForgedLayer", (ExecutableHook,), {})
    forged_type.__module__ = ExecutableLayer.__module__
    forged_type.__qualname__ = ExecutableLayer.__qualname__
    forged = forged_type()
    forged.self_attn = ExecutableHook()
    forged.mlp = ExecutableHook()
    forged_model = ExecutableModel()
    forged_model.model.layers[0] = forged
    with pytest.raises(RuntimeError, match="class/subclass mismatch"):
        module.verify_model(forged_model, **kwargs)

    method_drift = ExecutableModel()

    def mutate_then_raise(_callback):
        method_drift.model.layers[0].mlp.callbacks.append("partial")
        raise RuntimeError("should never execute")

    method_drift.model.layers[0].mlp.register_forward_hook = mutate_then_raise
    with pytest.raises(RuntimeError, match="hook registration API drift"):
        module.intervention_attachment_point(
            method_drift,
            "model.layers.0.mlp",
            **kwargs,
        )
    assert method_drift.model.layers[0].mlp.callbacks == []


def test_generation_rejects_duplicate_hook_module_aliases():
    model = ExecutableModel()
    model.model.layers[0].mlp = model.model.layers[0].self_attn
    plan = executable_plan(model)

    with pytest.raises(ValueError, match="aliases.*duplicate paths"):
        generate_executable_adapter_artifact(model=model, plan=plan)


def test_generated_runtime_rejects_config_profile_layer_and_identity_drift(tmp_path):
    _, artifact = generated_artifact()
    module = import_generated_adapter(artifact, tmp_path)
    kwargs = generated_identity_arguments(artifact)

    config_drift = ExecutableModel()
    config_drift.config.hidden_size = 65
    with pytest.raises(RuntimeError, match="config drift: hidden_size"):
        module.verify_model(config_drift, **kwargs)

    profile_drift = ExecutableModel()
    profile_drift.config.model_type = "mistral"
    with pytest.raises(RuntimeError, match="config drift: model_type"):
        module.verify_model(profile_drift, **kwargs)

    layer_drift = ExecutableModel(count=3)
    layer_drift.config.num_hidden_layers = 2
    with pytest.raises(RuntimeError, match="layer-count drift"):
        module.verify_model(layer_drift, **kwargs)

    with pytest.raises(RuntimeError, match="engine API version mismatch"):
        module.verify_model(
            ExecutableModel(),
            **{**kwargs, "engine_api_version": "cas_harness_interpretability_engine.v2"},
        )
    with pytest.raises(RuntimeError, match="byte-binding boundary mismatch"):
        module.verify_model(
            ExecutableModel(),
            **{**kwargs, "model_byte_binding_status": "LOADED_MODEL_BYTE_VERIFIED"},
        )


def test_generated_attachment_points_are_allowlisted_and_side_effect_free(tmp_path):
    model, artifact = generated_artifact()
    module = import_generated_adapter(artifact, tmp_path)
    kwargs = generated_identity_arguments(artifact)

    capture_module = module.capture_attachment_point(
        model,
        "model.layers.0.self_attn",
        **kwargs,
    )
    intervention_module = module.intervention_attachment_point(
        model,
        "model.layers.0.mlp",
        **kwargs,
    )

    assert capture_module is model.model.layers[0].self_attn
    assert intervention_module is model.model.layers[0].mlp
    assert model.model.layers[0].self_attn.callbacks == []
    assert model.model.layers[0].mlp.callbacks == []


def test_generated_source_hash_tamper_and_rehashed_tamper_are_rejected():
    _, artifact = generated_artifact()
    tampered_bytes = artifact.source_bytes + b"# tampered\n"

    with pytest.raises(ValueError, match="source SHA-256 mismatch"):
        replace(artifact, source_bytes=tampered_bytes).verify()

    with pytest.raises(ValueError, match="canonical reconstruction"):
        replace(
            artifact,
            source_bytes=tampered_bytes,
            source_sha256=hashlib.sha256(tampered_bytes).hexdigest().upper(),
        ).verify()


def test_generated_adapter_rebuild_is_byte_deterministic():
    _, first = generated_artifact(ExecutableModel())
    _, second = generated_artifact(ExecutableModel())

    assert first.spec.to_dict() == second.spec.to_dict()
    assert first.spec.spec_sha256 == second.spec.spec_sha256
    assert first.source_bytes == second.source_bytes
    assert first.source_sha256 == second.source_sha256
    assert first.to_manifest_json_bytes() == second.to_manifest_json_bytes()


def test_generated_render_is_independent_of_mutable_planner_alias_map(monkeypatch):
    model, artifact = generated_artifact()
    original_spec_sha256 = artifact.spec.spec_sha256
    original_source = artifact.source_bytes

    monkeypatch.setitem(adapter_module._MODEL_TYPE_ALIASES, "irrelevantalias", "llama")
    artifact.verify()
    rebuilt = generate_executable_adapter_artifact(
        model=model,
        plan=executable_plan(model),
    )

    assert artifact.spec.spec_sha256 == original_spec_sha256
    assert artifact.source_bytes == original_source
    assert rebuilt.spec.spec_sha256 == original_spec_sha256
    assert rebuilt.source_bytes == original_source
