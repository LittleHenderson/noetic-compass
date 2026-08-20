"""Offline tests for the inert interpretability-adapter planner."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from api.services.cas_harness_interpretability_adapter import (
    ArchitectureDeclaration,
    ModelIdentity,
    RuntimeVerification,
    build_interpretability_adapter_plan,
    canonical_json_bytes,
    discover_loaded_architecture,
    normalize_model_type,
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
