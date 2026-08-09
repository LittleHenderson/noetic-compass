"""Local data-integrity tests for the STRUCTURE_ONLY Stage C Qwen W0 seam.

Only tiny fake tensors/modules and an exact typed loader carrier are used.
The suite performs no model-file load, provider call, Docker/HTTP activity,
generation, intervention, or real Stage C execution.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import json
from types import MappingProxyType, SimpleNamespace
from typing import Any, Callable
from unittest.mock import patch

import numpy as np
import pytest
import torch
from torch import nn
from torch.nn.modules import module as torch_module_hooks
from torch.utils.hooks import RemovableHandle

from app.runtime import model_loader
from app.runtime.stagec_capture import (
    AUTHORIZATION_MEDIA_TYPE,
    CAPTURE_INDEX_MEDIA_TYPE,
    REQUEST_MEDIA_TYPE,
    ArtifactIdentity,
    CanonicalJsonArtifact,
    CaptureArtifactIds,
    IN_MEMORY_LOCATION,
    LOADER_IDENTITY_STATUS,
    NON_AUTHORITY_STATUS,
    NOT_ATTESTED,
    NOT_DURABLY_RETAINED,
    RAW_ARRAY_FORMAT,
    RAW_ARRAY_LAYOUT,
    RAW_ARRAY_MEDIA_TYPE,
    RawArrayArtifact,
    STAGEC_MODEL_ID,
    STAGEC_MODEL_REVISION,
    STAGEC_TARGET_MODULE_PATH,
    STAGEC_TOKENIZER_CONFIG_BYTES,
    STAGEC_TOKENIZER_CONFIG_SHA256,
    STAGEC_TOKENIZER_JSON_BYTES,
    STAGEC_TOKENIZER_JSON_SHA256,
    STAGEC_VECTOR_WIDTH,
    STAGEC_VOCAB_SIZE,
    STAGEC_WRONG_LAYER_MODULE_PATH,
    STRUCTURE_ONLY_SCOPE,
    StageCCaptureError,
    StageCCaptureIndex,
    StageCCaptureResult,
    build_stagec_authorization_projection_artifact,
    build_stagec_request_artifact,
    capture_stagec_qwen_w0,
    load_stagec_capture_index,
    replay_stagec_capture_artifacts,
    replay_stagec_capture_result,
)


_PROMPT = "Summarize this bounded research input."
_OTHER_PROMPT = "A substituted prompt must not cross-bind."
_CHAT_TEMPLATE = "qwen-test-template: {{ messages }}"
_INPUT_IDS = torch.tensor([[101, 202, 303, 404]], dtype=torch.int64)
_ATTENTION_MASK = torch.ones_like(_INPUT_IDS)


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest().upper()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_artifact(
    *, artifact_id: str, media_type: str, raw_bytes: bytes
) -> CanonicalJsonArtifact:
    return CanonicalJsonArtifact(
        ref=ArtifactIdentity(
            artifact_id=artifact_id,
            sha256=_digest(raw_bytes),
            byte_length=len(raw_bytes),
            media_type=media_type,
        ),
        raw_bytes=raw_bytes,
    )


class _Projection(nn.Module):
    def __init__(self, *, input_width: int = 4_864, output_width: int = 896) -> None:
        super().__init__()
        self.in_features = input_width
        self.out_features = output_width

    def forward(self, activation: torch.Tensor) -> torch.Tensor:
        return activation[..., : self.out_features].clone()


class _Mlp(nn.Module):
    def __init__(self, *, input_width: int = 4_864, output_width: int = 896) -> None:
        super().__init__()
        self.down_proj = _Projection(input_width=input_width, output_width=output_width)


class _Layer(nn.Module):
    def __init__(self, *, input_width: int = 4_864, output_width: int = 896) -> None:
        super().__init__()
        self.mlp = _Mlp(input_width=input_width, output_width=output_width)


class _Backbone(nn.Module):
    def __init__(
        self,
        *,
        layer_count: int = 24,
        input_width: int = 4_864,
        output_width: int = 896,
    ) -> None:
        super().__init__()
        self.layers = nn.ModuleList(
            [
                _Layer(input_width=input_width, output_width=output_width)
                for _ in range(layer_count)
            ]
        )


class _FakeQwen(nn.Module):
    def __init__(
        self,
        *,
        layer_count: int = 24,
        input_width: int = 4_864,
        output_width: int = 896,
        mode: str = "normal",
        on_forward: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.model = _Backbone(
            layer_count=layer_count,
            input_width=input_width,
            output_width=output_width,
        )
        self.config = SimpleNamespace(
            model_type="qwen2",
            num_hidden_layers=24,
            hidden_size=896,
            intermediate_size=4_864,
            _commit_hash=STAGEC_MODEL_REVISION,
            vocab_size=STAGEC_VOCAB_SIZE,
            max_position_embeddings=32_768,
        )
        self.register_buffer("mutation_canary", torch.tensor([7], dtype=torch.int64))
        self.mode = mode
        self.on_forward = on_forward
        self.forward_calls = 0
        self.generate_calls = 0
        self.last_output: Any = None
        self.eval()

    def _activation(self, input_ids: torch.Tensor, *, layer: int) -> torch.Tensor:
        sequence_length = int(input_ids.shape[1])
        vector = torch.arange(
            STAGEC_VECTOR_WIDTH,
            device=input_ids.device,
            dtype=torch.float32,
        )
        activation = vector.view(1, 1, -1).repeat(1, sequence_length, 1)
        activation.add_(float(layer * 10_000))
        activation.add_(input_ids.to(torch.float32).unsqueeze(-1) / 1_000.0)
        if self.mode == "nonfinite_activation" and layer == 18:
            activation[0, -1, 17] = float("nan")
        return activation

    def _fire(self, layer: int, input_ids: torch.Tensor) -> torch.Tensor:
        return self.model.layers[layer].mlp.down_proj(
            self._activation(input_ids, layer=layer)
        )

    def forward(
        self,
        *,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        use_cache: bool,
        output_attentions: bool,
        output_hidden_states: bool,
        return_dict: bool,
    ) -> Any:
        self.forward_calls += 1
        assert use_cache is False
        assert output_attentions is False
        assert output_hidden_states is False
        assert return_dict is True
        assert attention_mask.shape == input_ids.shape
        if self.on_forward is not None:
            self.on_forward()
        if self.mode == "wrong_order":
            order = (18, 0)
        elif self.mode == "missing_target":
            order = (0,)
        elif self.mode == "duplicate_wrong":
            order = (0, 0, 18)
        else:
            order = (0, 18)
        outputs: list[torch.Tensor] = []
        for layer in order:
            outputs.append(self._fire(layer, input_ids))
            if self.mode == "forward_failure" and layer == 0:
                raise RuntimeError("deliberate tiny-model failure")
        if self.mode == "input_mutation":
            input_ids.add_(1)
        if self.mode == "model_mutation":
            self.mutation_canary.add_(1)
        if self.mode == "training_mutation":
            self.train()
        if self.mode == "config_mutation":
            self.config.intermediate_size = 4_863
        if self.mode == "none_output":
            return None
        width = 17 if self.mode == "bad_logits_width" else STAGEC_VOCAB_SIZE
        logits = outputs[-1][..., :1].expand(1, int(input_ids.shape[1]), width)
        if self.mode == "nonfinite_logits":
            logits = logits.clone()
            logits[0, -1, -1] = float("nan")
        self.last_output = SimpleNamespace(logits=logits)
        return self.last_output

    def generate(self, *_args: Any, **_kwargs: Any) -> Any:
        self.generate_calls += 1
        raise AssertionError("Stage C capture must never call generate")


class _FakeTokenizer:
    def __init__(self, *, mode: str = "normal") -> None:
        self.name_or_path = STAGEC_MODEL_ID
        self.chat_template = _CHAT_TEMPLATE
        self.all_special_tokens = ["<|im_start|>", "<|im_end|>", "<|endoftext|>"]
        self.model_max_length = 32_768
        self.mode = mode
        self.template_calls: list[tuple[Any, dict[str, Any]]] = []
        self.tokenizer_calls: list[tuple[Any, dict[str, Any]]] = []

    def apply_chat_template(self, messages: Any, **kwargs: Any) -> Any:
        self.template_calls.append((messages, dict(kwargs)))
        if self.mode == "template_failure":
            raise ValueError("deliberate template failure")
        if self.mode == "template_nontext":
            return [1, 2, 3]
        if self.mode == "template_identity":
            return messages[0]["content"]
        prompt = messages[0]["content"]
        return f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    def __call__(self, rendered: Any, **kwargs: Any) -> Any:
        self.tokenizer_calls.append((rendered, dict(kwargs)))
        if self.mode == "tokenizer_failure":
            raise ValueError("deliberate tokenizer failure")
        if self.mode == "nonmapping":
            return _INPUT_IDS.clone()
        result: dict[str, Any] = {
            "input_ids": _INPUT_IDS.clone(),
            "attention_mask": _ATTENTION_MASK.clone(),
        }
        if self.mode == "missing_mask":
            result.pop("attention_mask")
        elif self.mode == "float_ids":
            result["input_ids"] = result["input_ids"].to(torch.float32)
        elif self.mode == "rank_one_ids":
            result["input_ids"] = result["input_ids"][0]
        elif self.mode == "mask_shape":
            result["attention_mask"] = torch.ones((1, 3), dtype=torch.int64)
        elif self.mode == "padded_mask":
            result["attention_mask"][0, -1] = 0
        elif self.mode == "negative_id":
            result["input_ids"][0, -1] = -1
        elif self.mode == "vocab_overflow":
            result["input_ids"][0, -1] = STAGEC_VOCAB_SIZE
        elif self.mode == "overflow_marker":
            result["overflowing_tokens"] = torch.tensor([9])
        elif self.mode == "truncated_marker":
            result["num_truncated_tokens"] = 1
        elif self.mode == "identical_one_token":
            result["input_ids"] = torch.ones((1, 1), dtype=torch.int64)
            result["attention_mask"] = torch.ones((1, 1), dtype=torch.int64)
        return result


def _request(
    *,
    artifact_id: str = "stagec-request-001",
    prompt: str = _PROMPT,
    study_id: str = "stagec-study-001",
    case_id: str = "stagec-case-001",
    invocation_id: str = "stagec-invocation-001",
) -> CanonicalJsonArtifact:
    return build_stagec_request_artifact(
        artifact_id=artifact_id,
        study_id=study_id,
        case_id=case_id,
        split_id="stagec-calibration",
        base_intent_group_id="stagec-group-001",
        frozen_variant="ADVERSARIAL_PRESENT",
        frozen_label="ADVERSARIAL_PRESENT",
        invocation_id=invocation_id,
        prompt=prompt,
    )


def _authorization(
    request: CanonicalJsonArtifact,
    *,
    artifact_id: str = "stagec-authorization-001",
) -> CanonicalJsonArtifact:
    return build_stagec_authorization_projection_artifact(
        artifact_id=artifact_id,
        request_artifact=request,
        plan_id="stagec-plan-001",
    )


def _artifact_ids() -> CaptureArtifactIds:
    return CaptureArtifactIds(
        capture_index="stagec-capture-index-001",
        model_config="stagec-model-config-001",
        model_weights="stagec-model-weights-001",
        tokenizer_json="stagec-tokenizer-json-001",
        tokenizer_config="stagec-tokenizer-config-001",
        chat_template="stagec-chat-template-001",
        input_ids="stagec-input-ids-001",
        attention_mask="stagec-attention-mask-001",
        target_vector="stagec-layer-18-vector-001",
        wrong_layer_vector="stagec-layer-0-vector-001",
    )


def _real_manifest() -> Any:
    binding = model_loader.active_model_binding()
    payload = model_loader.bootstrap_manifest(binding).model_dump(mode="json")
    payload.update(
        {
            "execution_kind": "real_model_weights",
            "resolved_revision": binding.revision,
            "revision_verified": True,
            "weights_filename": binding.weights_filename,
            "weights_sha256": binding.weights_sha256,
            "weights_bytes": binding.weights_bytes,
            "weights_hash_verified": True,
            "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
            "runtime_execution": {
                "profile": "development",
                "device": "cpu",
                "dtype": "torch.float32",
                "torch_version": "2.13.0+cu126",
                "torch_native_jit_disabled": False,
                "cuda_bfloat16_supported": None,
                "cuda_runtime_version": None,
                "cuda_driver_version": None,
                "cuda_device_name": None,
                "cuda_device_capability": None,
            },
            "is_real_model": True,
        }
    )
    return type(model_loader.PYTHIA_160M_MANIFEST).model_validate(payload)


def _loaded(
    *,
    model: _FakeQwen | None = None,
    tokenizer: _FakeTokenizer | None = None,
    manifest: Any = None,
    load_error: str | None = None,
) -> model_loader.LoadedModel:
    return model_loader.LoadedModel(
        manifest=manifest if manifest is not None else _real_manifest(),
        model=model or _FakeQwen(),
        tokenizer=tokenizer or _FakeTokenizer(),
        load_error=load_error,
    )


def _capture(
    *,
    loaded: Any = None,
    request: CanonicalJsonArtifact | None = None,
    authorization: CanonicalJsonArtifact | None = None,
    artifact_ids: CaptureArtifactIds | None = None,
) -> StageCCaptureResult:
    selected_request = request or _request()
    selected_loaded = loaded or _loaded()
    with patch.object(model_loader, "get_loaded_model", return_value=selected_loaded):
        return capture_stagec_qwen_w0(
            request_artifact=selected_request,
            authorization_projection_artifact=(
                authorization or _authorization(selected_request)
            ),
            artifact_ids=artifact_ids or _artifact_ids(),
        )


def _hook_registry_fingerprint(model: nn.Module) -> tuple[Any, ...]:
    local_names = (
        "_forward_pre_hooks",
        "_forward_hooks",
        "_forward_pre_hooks_with_kwargs",
        "_forward_hooks_with_kwargs",
        "_forward_hooks_always_called",
    )
    global_names = (
        "_global_forward_pre_hooks",
        "_global_forward_hooks",
        "_global_forward_hooks_with_kwargs",
        "_global_forward_hooks_always_called",
    )
    local = tuple(
        (
            name,
            id(module),
            registry_name,
            id(registry),
            tuple((repr(key), id(value)) for key, value in registry.items()),
        )
        for name, module in model.named_modules()
        for registry_name in local_names
        for registry in (getattr(module, registry_name),)
    )
    global_rows = tuple(
        (
            registry_name,
            id(registry),
            tuple((repr(key), id(value)) for key, value in registry.items()),
        )
        for registry_name in global_names
        for registry in (getattr(torch_module_hooks, registry_name),)
    )
    return local, global_rows


@pytest.fixture(autouse=True)
def _select_qwen_and_restore_global_hooks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    names = (
        "_global_forward_pre_hooks",
        "_global_forward_hooks",
        "_global_forward_hooks_with_kwargs",
        "_global_forward_hooks_always_called",
    )
    originals = {
        name: (getattr(torch_module_hooks, name), tuple(getattr(torch_module_hooks, name).items()))
        for name in names
    }
    try:
        yield
    finally:
        for name, (mapping, entries) in originals.items():
            setattr(torch_module_hooks, name, mapping)
            mapping.clear()
            mapping.update(entries)


def test_success_derives_prompt_and_association_from_request_bytes() -> None:
    model = _FakeQwen()
    tokenizer = _FakeTokenizer()
    request = _request()
    result = _capture(loaded=_loaded(model=model, tokenizer=tokenizer), request=request)

    assert model.forward_calls == 1
    assert model.generate_calls == 0
    assert tokenizer.template_calls == [
        (
            [{"role": "user", "content": _PROMPT}],
            {"tokenize": False, "add_generation_prompt": True},
        )
    ]
    association = result.index.association
    assert association["study_id"] == "stagec-study-001"
    assert association["case_id"] == "stagec-case-001"
    assert association["invocation_id"] == "stagec-invocation-001"
    assert association["request_artifact"]["sha256"] == request.ref.sha256
    assert result.index.payload["prompt"]["raw_utf8_sha256"] == _digest(
        _PROMPT.encode("utf-8")
    )


def test_success_emits_canonical_exact_index_and_full_semantic_replay() -> None:
    result = _capture()
    payload = result.index.to_payload()

    assert result.index_artifact.ref.media_type == CAPTURE_INDEX_MEDIA_TYPE
    assert result.index_artifact.raw_bytes == _canonical_bytes(payload)
    assert result.index_artifact.ref.sha256 == _digest(result.index_artifact.raw_bytes)
    assert load_stagec_capture_index(result.index_artifact).to_payload() == payload
    assert replay_stagec_capture_result(result).to_payload() == payload
    assert payload["scope"] == STRUCTURE_ONLY_SCOPE
    assert payload["retention"] == {
        "location": IN_MEMORY_LOCATION,
        "durability_status": NOT_DURABLY_RETAINED,
    }


def test_success_replays_exact_arrays_and_final_vectors() -> None:
    result = _capture()
    expected_ids = np.asarray(_INPUT_IDS.numpy(), dtype="<i8", order="C")
    assert result.input_ids.raw_bytes == expected_ids.tobytes(order="C")
    expected_wrong = np.arange(STAGEC_VECTOR_WIDTH, dtype=np.float32)
    expected_wrong += np.float32(0.404)
    expected_target = np.arange(STAGEC_VECTOR_WIDTH, dtype=np.float32)
    expected_target += np.float32(180_000.404)
    assert np.array_equal(
        np.frombuffer(result.wrong_layer_vector.raw_bytes, dtype="<f4"),
        expected_wrong,
    )
    assert np.array_equal(
        np.frombuffer(result.target_vector.raw_bytes, dtype="<f4"),
        expected_target,
    )


def test_success_labels_every_raw_payload_in_memory_and_not_durable() -> None:
    result = _capture()
    expected = (
        (result.input_ids, "<i8", (1, 4), "input_ids"),
        (result.attention_mask, "<i8", (1, 4), "attention_mask"),
        (
            result.target_vector,
            "<f4",
            (STAGEC_VECTOR_WIDTH,),
            "target_final_token_activation",
        ),
        (
            result.wrong_layer_vector,
            "<f4",
            (STAGEC_VECTOR_WIDTH,),
            "wrong_layer_final_token_activation",
        ),
    )
    for artifact, dtype, shape, role in expected:
        ref = artifact.ref
        assert ref.media_type == RAW_ARRAY_MEDIA_TYPE
        assert ref.format == RAW_ARRAY_FORMAT
        assert ref.layout == RAW_ARRAY_LAYOUT
        assert ref.dtype == dtype
        assert ref.shape == shape
        assert ref.role == role
        assert ref.retention_location == IN_MEMORY_LOCATION
        assert ref.durability_status == NOT_DURABLY_RETAINED


def test_success_exposes_full_causal_lm_logits_and_scoped_telemetry() -> None:
    result = _capture()
    payload = result.index.to_payload()
    assert payload["logits"]["shape"] == [1, 4, STAGEC_VOCAB_SIZE]
    assert payload["logits"]["all_finite"] is True
    telemetry = payload["telemetry"]
    assert telemetry["direct_capture_model_call_count"] == 1
    assert telemetry["direct_generate_api_call_count"] == 0
    assert {
        telemetry["total_model_forward_count"],
        telemetry["total_generation_count"],
        telemetry["total_intervention_count"],
        telemetry["startup_canary_count"],
    } == {NOT_ATTESTED}
    serialized = result.index_artifact.raw_bytes.decode("utf-8")
    assert "generated_token" not in serialized
    assert "generation_call_count" not in serialized


def test_success_identity_claim_is_loader_carrier_only() -> None:
    identity = _capture().index.payload["identity"]
    assert identity["status"] == LOADER_IDENTITY_STATUS
    assert identity["model_id"] == identity["tokenizer_id"] == STAGEC_MODEL_ID
    assert identity["revision"] == STAGEC_MODEL_REVISION


def test_success_preserves_activation_source_and_narrow_endpoint_statuses() -> None:
    payload = _capture().index.to_payload()
    for name, layer, module_path in (
        ("wrong_layer", 0, STAGEC_WRONG_LAYER_MODULE_PATH),
        ("target", 18, STAGEC_TARGET_MODULE_PATH),
    ):
        source = payload["activations"][name]
        assert source["layer_index"] == layer
        assert source["module_path"] == module_path
        assert source["source_dtype"] == "torch.float32"
        assert source["source_device"] == "cpu"
        assert source["source_autocast_enabled"] is False
    assert payload["endpoint_checks"] == {
        "input_tensors": "METADATA_AND_VALUE_DIGEST_UNCHANGED_AT_CALL_ENDPOINTS",
        "model_tensors": "METADATA_AND_VALUE_DIGEST_UNCHANGED_AT_CALL_ENDPOINTS",
        "output_logits": "METADATA_FINITE_VALUE_DIGEST_OBSERVED_AT_RETURN",
    }


def test_cpu_autocast_state_is_recorded_for_the_activation_device() -> None:
    with torch.autocast("cpu"):
        payload = _capture().index.to_payload()
    assert payload["activations"]["wrong_layer"]["source_device"] == "cpu"
    assert payload["activations"]["target"]["source_device"] == "cpu"
    assert payload["activations"]["wrong_layer"]["source_autocast_enabled"] is True
    assert payload["activations"]["target"]["source_autocast_enabled"] is True


def test_success_exact_hook_cleanup_and_frozen_result() -> None:
    model = _FakeQwen()
    result = _capture(loaded=_loaded(model=model))
    hooks = result.index.payload["hooks"]
    assert hooks["registration_order"] == (0, 18)
    assert hooks["firing_order"] == (0, 18)
    assert hooks["cleanup_order"] == (18, 0)
    assert hooks["registries_before_sha256"] == hooks["registries_after_sha256"]
    assert all(
        not module._forward_pre_hooks and not module._forward_hooks
        for module in model.modules()
    )
    with pytest.raises(FrozenInstanceError):
        result.input_ids = result.attention_mask  # type: ignore[misc]


def test_identical_input_and_mask_bytes_allowed_with_unique_ids_and_roles() -> None:
    tokenizer = _FakeTokenizer(mode="identical_one_token")
    result = _capture(loaded=_loaded(tokenizer=tokenizer))
    assert result.input_ids.ref.sha256 == result.attention_mask.ref.sha256
    assert result.input_ids.ref.artifact_id != result.attention_mask.ref.artifact_id
    assert result.input_ids.ref.role != result.attention_mask.ref.role


def test_prompt_substitution_and_cross_request_authorization_fail_before_template() -> None:
    first = _request()
    authorization = _authorization(first)
    substituted = _request(artifact_id="stagec-request-002", prompt=_OTHER_PROMPT)
    tokenizer = _FakeTokenizer()
    model = _FakeQwen()
    with pytest.raises(StageCCaptureError, match="different request"):
        _capture(
            loaded=_loaded(model=model, tokenizer=tokenizer),
            request=substituted,
            authorization=authorization,
        )
    assert tokenizer.template_calls == []
    assert model.forward_calls == 0


@pytest.mark.parametrize("field", ["study_id", "case_id", "invocation_id"])
def test_authorization_projection_association_drift_fails(field: str) -> None:
    request = _request()
    authorization = _authorization(request)
    payload = json.loads(authorization.raw_bytes)
    payload[field] = f"drifted-{field}"
    forged = _json_artifact(
        artifact_id=authorization.ref.artifact_id,
        media_type=AUTHORIZATION_MEDIA_TYPE,
        raw_bytes=_canonical_bytes(payload),
    )
    with pytest.raises(StageCCaptureError, match=field):
        _capture(request=request, authorization=forged)


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("scope", "EXECUTE", "STRUCTURE_ONLY"),
        ("authority_status", "AUTHORIZED", "non-authority"),
        ("request_sha256", "A" * 64, "different request"),
        ("plan_id", "contains a space", "machine identifier"),
    ],
)
def test_authorization_projection_literal_and_request_binding_fail_closed(
    field: str, bad_value: Any, message: str
) -> None:
    request = _request()
    authorization = _authorization(request)
    payload = json.loads(authorization.raw_bytes)
    payload[field] = bad_value
    forged = _json_artifact(
        artifact_id=authorization.ref.artifact_id,
        media_type=AUTHORIZATION_MEDIA_TYPE,
        raw_bytes=_canonical_bytes(payload),
    )
    with pytest.raises(StageCCaptureError, match=message):
        _capture(request=request, authorization=forged)


@pytest.mark.parametrize("kind", ["duplicate", "whitespace", "extra_key", "wrong_media"])
def test_request_artifact_requires_unique_key_canonical_utf8_exact_schema(kind: str) -> None:
    request = _request()
    payload = json.loads(request.raw_bytes)
    media_type = REQUEST_MEDIA_TYPE
    if kind == "duplicate":
        text = request.raw_bytes.decode("utf-8")
        raw = text[:-1].encode("utf-8") + b',"prompt":"duplicate"}'
    elif kind == "whitespace":
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    elif kind == "extra_key":
        payload["extra"] = 1
        raw = _canonical_bytes(payload)
    else:
        raw = request.raw_bytes
        media_type = "application/json"
    forged = _json_artifact(
        artifact_id=request.ref.artifact_id,
        media_type=media_type,
        raw_bytes=raw,
    )
    with pytest.raises(StageCCaptureError, match="duplicate|canonical|keys drifted|media type"):
        _capture(request=forged, authorization=_authorization(request))


def test_request_bytes_cannot_be_tampered_without_ref_update() -> None:
    request = _request()
    changed = request.raw_bytes.replace(b"bounded", b"changed")
    with pytest.raises(StageCCaptureError, match="length|digest"):
        CanonicalJsonArtifact(ref=request.ref, raw_bytes=changed)


@pytest.mark.parametrize("carrier_kind", ["mapping", "namespace", "subclass"])
def test_loaded_carrier_requires_exact_loaded_model_type(carrier_kind: str) -> None:
    real = _loaded()
    if carrier_kind == "mapping":
        carrier: Any = {"model": real.model, "tokenizer": real.tokenizer, "manifest": real.manifest}
    elif carrier_kind == "namespace":
        carrier = SimpleNamespace(model=real.model, tokenizer=real.tokenizer, manifest=real.manifest, is_real=True)
    else:
        class _LoadedSubclass(model_loader.LoadedModel):
            pass

        carrier = _LoadedSubclass(real.manifest, real.model, real.tokenizer)
    with pytest.raises(StageCCaptureError, match="exact model_loader.LoadedModel"):
        _capture(loaded=carrier)


@pytest.mark.parametrize(
    "defect",
    ["bootstrap", "load_error", "missing_model", "missing_tokenizer", "manifest_weights", "manifest_worker"],
)
def test_loaded_carrier_is_real_and_manifest_drift_fail_before_template(defect: str) -> None:
    tokenizer = _FakeTokenizer()
    model = _FakeQwen()
    manifest = _real_manifest()
    load_error = None
    if defect == "bootstrap":
        manifest = model_loader.bootstrap_manifest(model_loader.active_model_binding())
    elif defect == "load_error":
        load_error = "failed"
    elif defect == "manifest_weights":
        manifest = manifest.model_copy(update={"weights_sha256": "0" * 64})
    elif defect == "manifest_worker":
        manifest = manifest.model_copy(update={"worker_version": "forged-worker"})
    loaded = model_loader.LoadedModel(
        manifest=manifest,
        model=None if defect == "missing_model" else model,
        tokenizer=None if defect == "missing_tokenizer" else tokenizer,
        load_error=load_error,
    )
    with pytest.raises(StageCCaptureError, match="is_real"):
        _capture(loaded=loaded)
    assert tokenizer.template_calls == []
    assert model.forward_calls == 0


def test_runtime_model_and_tokenizer_identity_drift_fail_before_template() -> None:
    model = _FakeQwen()
    model.config.vocab_size -= 1
    tokenizer = _FakeTokenizer()
    with pytest.raises(StageCCaptureError, match="model config identity"):
        _capture(loaded=_loaded(model=model, tokenizer=tokenizer))
    assert tokenizer.template_calls == []

    model = _FakeQwen()
    tokenizer = _FakeTokenizer()
    tokenizer.name_or_path = "Qwen/not-pinned"
    with pytest.raises(StageCCaptureError, match="tokenizer identity"):
        _capture(loaded=_loaded(model=model, tokenizer=tokenizer))
    assert tokenizer.template_calls == []


@pytest.mark.parametrize(
    ("field", "alias"),
    [
        ("num_hidden_layers", 24.0),
        ("hidden_size", 896.0),
        ("intermediate_size", 4_864.0),
        ("vocab_size", 151_936.0),
        ("max_position_embeddings", 32_768.0),
    ],
)
def test_runtime_model_config_rejects_equal_numeric_type_aliases_before_template(
    field: str, alias: float
) -> None:
    model = _FakeQwen()
    tokenizer = _FakeTokenizer()
    setattr(model.config, field, alias)
    with pytest.raises(StageCCaptureError, match="model config identity"):
        _capture(loaded=_loaded(model=model, tokenizer=tokenizer))
    assert tokenizer.template_calls == []
    assert model.forward_calls == 0


@pytest.mark.parametrize(
    ("constant_name", "bad_value"),
    [
        ("QWEN_05B_INSTRUCT_REVISION", "0" * 40),
        ("QWEN_05B_INSTRUCT_WEIGHTS_SHA256", "0" * 64),
        ("QWEN_05B_INSTRUCT_WEIGHTS_BYTES", 1),
    ],
)
def test_selected_binding_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch, constant_name: str, bad_value: Any
) -> None:
    monkeypatch.setattr(model_loader, constant_name, bad_value)
    with pytest.raises(StageCCaptureError, match="exact Stage C Qwen binding"):
        _capture()


def test_selected_binding_full_artifact_manifest_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        model_loader.QWEN_05B_INSTRUCT_ARTIFACTS,
        "generation_config.json",
        ("0" * 64, 242),
    )
    with pytest.raises(StageCCaptureError, match="artifact manifest"):
        _capture()


@pytest.mark.parametrize(
    ("defect", "message"),
    [
        ("arch_type", "architecture has the wrong exact type"),
        ("arch_value", "architecture drifted"),
        ("pin_tuple_type", "artifact manifest drifted"),
    ],
)
def test_selected_binding_exact_arch_and_pin_type_branches(
    defect: str,
    message: str,
) -> None:
    binding = model_loader.active_model_binding()
    loaded = _loaded()
    if defect == "arch_type":
        drifted = replace(
            binding,
            arch=SimpleNamespace(**binding.arch.model_dump(mode="python")),
        )
    elif defect == "arch_value":
        drifted = replace(
            binding,
            arch=binding.arch.model_copy(update={"n_heads": 13}),
        )
    else:
        artifacts = dict(binding.artifacts)
        sha_value, byte_length = artifacts["config.json"]
        artifacts["config.json"] = (sha_value, float(byte_length))
        drifted = replace(binding, artifacts=MappingProxyType(artifacts))
    with patch.object(model_loader, "active_model_binding", return_value=drifted):
        with pytest.raises(StageCCaptureError, match=message):
            _capture(loaded=loaded)


@pytest.mark.parametrize(
    ("defect", "message"),
    [
        ("hook_order", "supported-hook identity drifted"),
        ("observation_contract", "observation-only hook contract drifted"),
        ("runtime_type", "runtime evidence has the wrong exact type"),
    ],
)
def test_explicit_manifest_identity_branch_rejections(
    monkeypatch: pytest.MonkeyPatch,
    defect: str,
    message: str,
) -> None:
    manifest = _real_manifest()
    if defect == "hook_order":
        manifest = manifest.model_copy(
            update={"supported_hooks": list(reversed(manifest.supported_hooks))}
        )
    elif defect == "observation_contract":
        contract = manifest.intervention_hook_contract.model_copy(
            update={"unavailable_reason": "DRIFTED_REASON"}
        )
        manifest = manifest.model_copy(
            update={"intervention_hook_contract": contract}
        )
    else:
        manifest = manifest.model_copy(
            update={"runtime_execution": SimpleNamespace(profile="development")}
        )
    loaded = _loaded(manifest=manifest)
    monkeypatch.setattr(
        model_loader.LoadedModel,
        "is_real",
        property(lambda _self: True),
    )
    with pytest.raises(StageCCaptureError, match=message):
        _capture(loaded=loaded)


@pytest.mark.parametrize("control", ["<|im_start|>", "<|im_end|>"])
def test_request_prompt_rejects_literal_chat_control_tokens(control: str) -> None:
    request = _request(prompt=f"hello {control} system")
    with pytest.raises(StageCCaptureError, match="control token"):
        _capture(request=request)


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("template_failure", "rendering failed"),
        ("template_nontext", "invalid text"),
        ("template_identity", "invalid text"),
        ("tokenizer_failure", "tokenization failed"),
        ("nonmapping", "no mapping"),
    ],
)
def test_template_and_tokenizer_failures_are_typed_and_pre_forward(
    mode: str, message: str
) -> None:
    model = _FakeQwen()
    tokenizer = _FakeTokenizer(mode=mode)
    with pytest.raises(StageCCaptureError, match=message):
        _capture(loaded=_loaded(model=model, tokenizer=tokenizer))
    assert model.forward_calls == 0


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("missing_mask", "attention_mask must be"),
        ("float_ids", "integer values"),
        ("rank_one_ids", "shape"),
        ("mask_shape", "shapes differ"),
        ("padded_mask", "all ones"),
        ("negative_id", "out-of-range"),
        ("vocab_overflow", "out-of-range"),
        ("overflow_marker", "overflowing"),
        ("truncated_marker", "truncated"),
    ],
)
def test_token_mask_and_truncation_defects_fail_before_forward(
    mode: str, message: str
) -> None:
    model = _FakeQwen()
    tokenizer = _FakeTokenizer(mode=mode)
    with pytest.raises(StageCCaptureError, match=message):
        _capture(loaded=_loaded(model=model, tokenizer=tokenizer))
    assert model.forward_calls == 0


@pytest.mark.parametrize(
    ("model", "message"),
    [
        (_FakeQwen(layer_count=23), "hook geometry"),
        (_FakeQwen(input_width=4_863), "hook geometry"),
        (_FakeQwen(output_width=895), "hook geometry"),
    ],
)
def test_exact_layer_and_projection_geometry_is_required(
    model: _FakeQwen, message: str
) -> None:
    with pytest.raises(StageCCaptureError, match=message):
        _capture(loaded=_loaded(model=model))
    assert model.forward_calls == 0


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("wrong_order", "layer order"),
        ("duplicate_wrong", "layer order"),
        ("missing_target", "cardinality/order"),
        ("nonfinite_activation", "nonfinite"),
        ("forward_failure", "direct prefill call failed"),
        ("none_output", "cardinality/output"),
        ("bad_logits_width", "logits shape"),
        ("nonfinite_logits", "logits contain nonfinite"),
    ],
)
def test_forward_hook_and_logits_defects_fail_closed_with_cleanup(
    mode: str, message: str
) -> None:
    model = _FakeQwen(mode=mode)
    with pytest.raises(StageCCaptureError, match=message):
        _capture(loaded=_loaded(model=model))
    assert model.generate_calls == 0
    assert all(not module._forward_pre_hooks for module in model.modules())


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("input_mutation", "input endpoint"),
        ("model_mutation", "model endpoint"),
        ("training_mutation", "evaluation-mode endpoint"),
        ("config_mutation", "model config identity"),
    ],
)
def test_endpoint_metadata_and_value_digest_changes_fail_closed(
    mode: str, message: str
) -> None:
    model = _FakeQwen(mode=mode)
    with pytest.raises(StageCCaptureError, match=message):
        _capture(loaded=_loaded(model=model))
    assert all(not module._forward_pre_hooks for module in model.modules())


@pytest.mark.parametrize("hook_kind", ["local_pre", "local_forward", "local_auxiliary"])
def test_preexisting_local_forward_and_pre_hook_registries_are_rejected(
    hook_kind: str,
) -> None:
    model = _FakeQwen()
    projection = model.model.layers[7].mlp.down_proj
    handle: Any = None
    if hook_kind == "local_pre":
        handle = projection.register_forward_pre_hook(lambda _module, _args: None)
    elif hook_kind == "local_forward":
        handle = projection.register_forward_hook(lambda _module, _args, output: output)
    else:
        projection._forward_pre_hooks_with_kwargs[999_001] = True
    try:
        with pytest.raises(StageCCaptureError, match="pre-existing local"):
            _capture(loaded=_loaded(model=model))
        assert model.forward_calls == 0
    finally:
        if handle is not None:
            handle.remove()
        projection._forward_pre_hooks_with_kwargs.pop(999_001, None)


@pytest.mark.parametrize("hook_kind", ["global_pre", "global_forward", "global_auxiliary"])
def test_preexisting_global_forward_and_pre_hook_registries_are_rejected(
    hook_kind: str,
) -> None:
    handle: Any = None
    if hook_kind == "global_pre":
        handle = torch_module_hooks.register_module_forward_pre_hook(
            lambda _module, _args: None
        )
    elif hook_kind == "global_forward":
        handle = torch_module_hooks.register_module_forward_hook(
            lambda _module, _args, output: output
        )
    else:
        torch_module_hooks._global_forward_hooks_with_kwargs[999_002] = True
    try:
        with pytest.raises(StageCCaptureError, match="pre-existing global"):
            _capture()
    finally:
        if handle is not None:
            handle.remove()
        torch_module_hooks._global_forward_hooks_with_kwargs.pop(999_002, None)


@pytest.mark.parametrize("remove_mode", ["noop", "raise"])
def test_hook_remove_anomaly_fails_but_fallback_restores_exact_local_state(
    monkeypatch: pytest.MonkeyPatch, remove_mode: str
) -> None:
    model = _FakeQwen()
    def remove(_handle: RemovableHandle) -> None:
        if remove_mode == "raise":
            raise RuntimeError("deliberate remove failure")
        return None

    monkeypatch.setattr(RemovableHandle, "remove", remove)
    with pytest.raises(StageCCaptureError, match="registration/removal anomaly"):
        _capture(loaded=_loaded(model=model))
    assert all(not module._forward_pre_hooks for module in model.modules())
    assert all(not module._forward_hooks for module in model.modules())


def test_extra_registration_anomaly_fails_and_wrapper_cleanup_is_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _FakeQwen()
    projection = model.model.layers[0].mlp.down_proj
    real_register = projection.register_forward_pre_hook

    class _BothHandles:
        def __init__(self, first: Any, second: Any) -> None:
            self.first = first
            self.second = second

        def remove(self) -> None:
            self.first.remove()
            self.second.remove()

    def register(hook: Any) -> Any:
        return _BothHandles(
            real_register(hook),
            real_register(lambda _module, _args: None),
        )

    monkeypatch.setattr(projection, "register_forward_pre_hook", register)
    with pytest.raises(StageCCaptureError, match="registration anomaly"):
        _capture(loaded=_loaded(model=model))
    assert all(not module._forward_pre_hooks for module in model.modules())


def test_registration_side_effect_with_no_handle_fails_and_cleanup_is_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _FakeQwen()
    projection = model.model.layers[0].mlp.down_proj
    real_register = projection.register_forward_pre_hook

    def register(hook: Any) -> None:
        real_register(hook)
        return None

    monkeypatch.setattr(projection, "register_forward_pre_hook", register)
    with pytest.raises(StageCCaptureError, match="registration anomaly"):
        _capture(loaded=_loaded(model=model))
    assert all(not module._forward_pre_hooks for module in model.modules())
    assert all(not module._forward_hooks for module in model.modules())


def test_normal_handle_with_extra_local_hook_is_rejected_and_exactly_restored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _FakeQwen()
    projection = model.model.layers[0].mlp.down_proj
    real_register = projection.register_forward_pre_hook
    before = _hook_registry_fingerprint(model)
    extra_handles: list[RemovableHandle] = []

    def register(hook: Any) -> RemovableHandle:
        expected_handle = real_register(hook)
        extra_handles.append(real_register(lambda _module, _args: None))
        return expected_handle

    monkeypatch.setattr(projection, "register_forward_pre_hook", register)
    try:
        with pytest.raises(StageCCaptureError, match="registration/removal anomaly"):
            _capture(loaded=_loaded(model=model))
        assert _hook_registry_fingerprint(model) == before
        assert all(not module._forward_pre_hooks for module in model.modules())
        assert all(not module._forward_hooks for module in model.modules())
    finally:
        for handle in extra_handles:
            handle.remove()


def test_global_hook_added_during_forward_fails_registry_comparison() -> None:
    holder: list[Any] = []

    def add_global_hook() -> None:
        holder.append(
            torch_module_hooks.register_module_forward_hook(
                lambda _module, _args, output: output
            )
        )

    model = _FakeQwen(on_forward=add_global_hook)
    try:
        with pytest.raises(StageCCaptureError, match="registries did not exactly match"):
            _capture(loaded=_loaded(model=model))
        assert all(not module._forward_pre_hooks for module in model.modules())
    finally:
        for handle in holder:
            handle.remove()


@pytest.mark.parametrize(
    "drift_kind",
    ["local_registry_object", "global_registry_object", "local_auxiliary_entry"],
)
def test_forward_registry_drift_is_reported_and_exact_baseline_is_restored(
    drift_kind: str,
) -> None:
    model = _FakeQwen()
    projection = model.model.layers[7].mlp.down_proj
    before = _hook_registry_fingerprint(model)

    def drift_registries() -> None:
        if drift_kind == "local_registry_object":
            projection._forward_hooks = OrderedDict(
                [(777_001, lambda _module, _args, output: output)]
            )
        elif drift_kind == "global_registry_object":
            torch_module_hooks._global_forward_hooks = OrderedDict(
                [(777_002, lambda _module, _args, output: output)]
            )
        else:
            projection._forward_hooks_with_kwargs[777_003] = True

    model.on_forward = drift_registries
    with pytest.raises(StageCCaptureError, match="registries did not exactly match"):
        _capture(loaded=_loaded(model=model))
    assert _hook_registry_fingerprint(model) == before


def test_loaded_carrier_identity_change_during_forward_fails() -> None:
    loaded = _loaded()

    def drift_carrier() -> None:
        loaded.tokenizer = _FakeTokenizer()

    loaded.model.on_forward = drift_carrier
    with pytest.raises(StageCCaptureError, match="carrier identity changed"):
        _capture(loaded=loaded)


def test_tokenizer_template_value_change_during_forward_fails() -> None:
    loaded = _loaded()

    def drift_template() -> None:
        loaded.tokenizer.chat_template = "mutated template"

    loaded.model.on_forward = drift_template
    with pytest.raises(StageCCaptureError, match="chat-template bytes changed"):
        _capture(loaded=loaded)


def test_loader_singleton_object_change_during_capture_fails() -> None:
    first = _loaded()
    second = _loaded()
    request = _request()
    with patch.object(
        model_loader,
        "get_loaded_model",
        side_effect=[first, second],
    ):
        with pytest.raises(StageCCaptureError, match="singleton carrier identity changed"):
            capture_stagec_qwen_w0(
                request_artifact=request,
                authorization_projection_artifact=_authorization(request),
                artifact_ids=_artifact_ids(),
            )


def _index_with_payload(result: StageCCaptureResult, payload: dict[str, Any]) -> CanonicalJsonArtifact:
    return _json_artifact(
        artifact_id=result.index_artifact.ref.artifact_id,
        media_type=CAPTURE_INDEX_MEDIA_TYPE,
        raw_bytes=_canonical_bytes(payload),
    )


@pytest.mark.parametrize("kind", ["duplicate", "whitespace", "tampered_ref", "semantic_scope"])
def test_canonical_index_loader_rejects_duplicate_noncanonical_and_tamper(kind: str) -> None:
    result = _capture()
    payload = result.index.to_payload()
    if kind == "duplicate":
        raw = result.index_artifact.raw_bytes[:-1] + b',"scope":"STRUCTURE_ONLY"}'
        artifact = _json_artifact(
            artifact_id=result.index_artifact.ref.artifact_id,
            media_type=CAPTURE_INDEX_MEDIA_TYPE,
            raw_bytes=raw,
        )
    elif kind == "whitespace":
        artifact = _json_artifact(
            artifact_id=result.index_artifact.ref.artifact_id,
            media_type=CAPTURE_INDEX_MEDIA_TYPE,
            raw_bytes=json.dumps(payload, sort_keys=True).encode("utf-8"),
        )
    elif kind == "tampered_ref":
        changed = result.index_artifact.raw_bytes.replace(b"STRUCTURE_ONLY", b"STRUCTURE_ONLY_X")
        with pytest.raises(StageCCaptureError, match="length|digest"):
            CanonicalJsonArtifact(ref=result.index_artifact.ref, raw_bytes=changed)
        return
    else:
        payload["scope"] = "EXECUTE"
        artifact = _index_with_payload(result, payload)
    with pytest.raises(StageCCaptureError, match="duplicate|canonical|scope"):
        load_stagec_capture_index(artifact)


def test_index_requires_strict_loader_and_its_id_cannot_overlap_nested_refs() -> None:
    with pytest.raises(StageCCaptureError, match="strict loader"):
        StageCCaptureIndex()  # type: ignore[call-arg]

    result = _capture()
    overlapping = _json_artifact(
        artifact_id=result.input_ids.ref.artifact_id,
        media_type=CAPTURE_INDEX_MEDIA_TYPE,
        raw_bytes=result.index_artifact.raw_bytes,
    )
    with pytest.raises(StageCCaptureError, match="overlaps a referenced artifact"):
        load_stagec_capture_index(overlapping)


def _forge_array_and_index(
    result: StageCCaptureResult,
    *,
    field_name: str,
    array: np.ndarray,
) -> tuple[CanonicalJsonArtifact, RawArrayArtifact]:
    original: RawArrayArtifact = getattr(result, field_name)
    raw_bytes = np.asarray(array, dtype=np.dtype(original.ref.dtype), order="C").tobytes(order="C")
    forged_ref = replace(
        original.ref,
        sha256=_digest(raw_bytes),
        byte_length=len(raw_bytes),
    )
    forged = RawArrayArtifact(ref=forged_ref, raw_bytes=raw_bytes)
    payload = result.index.to_payload()
    if field_name == "input_ids":
        payload["tokens"]["input_ids_artifact"] = forged_ref.to_payload()
    elif field_name == "attention_mask":
        payload["tokens"]["attention_mask_artifact"] = forged_ref.to_payload()
    elif field_name == "target_vector":
        payload["activations"]["target"]["array_artifact"] = forged_ref.to_payload()
    else:
        payload["activations"]["wrong_layer"]["array_artifact"] = forged_ref.to_payload()
    return _index_with_payload(result, payload), forged


def _forged_result(
    source: StageCCaptureResult,
    **changes: Any,
) -> StageCCaptureResult:
    forged = object.__new__(StageCCaptureResult)
    for name in (
        "index_artifact",
        "request_artifact",
        "authorization_projection_artifact",
        "input_ids",
        "attention_mask",
        "target_vector",
        "wrong_layer_vector",
    ):
        object.__setattr__(forged, name, changes.get(name, getattr(source, name)))
    object.__setattr__(forged, "index", changes.get("index", source.index))
    return forged


def _replay_artifacts(
    source: StageCCaptureResult,
    **changes: Any,
) -> StageCCaptureIndex:
    return replay_stagec_capture_artifacts(
        index_artifact=changes.get("index_artifact", source.index_artifact),
        request_artifact=changes.get("request_artifact", source.request_artifact),
        authorization_projection_artifact=changes.get(
            "authorization_projection_artifact",
            source.authorization_projection_artifact,
        ),
        input_ids=changes.get("input_ids", source.input_ids),
        attention_mask=changes.get("attention_mask", source.attention_mask),
        target_vector=changes.get("target_vector", source.target_vector),
        wrong_layer_vector=changes.get(
            "wrong_layer_vector", source.wrong_layer_vector
        ),
    )


@pytest.mark.parametrize(
    ("defect", "message"),
    [
        ("mask_zero", "mask is not all ones"),
        ("negative_token", "out-of-range token"),
        ("large_token", "out-of-range token"),
        ("final_mismatch", "final prompt token"),
        ("target_nan", "target vector is nonfinite"),
        ("wrong_nan", "wrong_layer vector is nonfinite"),
    ],
)
def test_artifact_replay_checks_array_semantics(
    defect: str, message: str
) -> None:
    result = _capture()
    kwargs: dict[str, Any] = {}
    if defect == "mask_zero":
        array = np.frombuffer(result.attention_mask.raw_bytes, dtype="<i8").copy().reshape(1, 4)
        array[0, -1] = 0
        index, artifact = _forge_array_and_index(
            result, field_name="attention_mask", array=array
        )
        kwargs["attention_mask"] = artifact
    elif defect in {"negative_token", "large_token"}:
        array = np.frombuffer(result.input_ids.raw_bytes, dtype="<i8").copy().reshape(1, 4)
        array[0, 0] = -1 if defect == "negative_token" else STAGEC_VOCAB_SIZE
        index, artifact = _forge_array_and_index(result, field_name="input_ids", array=array)
        kwargs["input_ids"] = artifact
    elif defect == "final_mismatch":
        payload = result.index.to_payload()
        payload["tokens"]["final_prompt_token_id"] = 405
        index = _index_with_payload(result, payload)
    else:
        field_name = "target_vector" if defect == "target_nan" else "wrong_layer_vector"
        array = np.frombuffer(getattr(result, field_name).raw_bytes, dtype="<f4").copy()
        array[17] = np.nan
        index, artifact = _forge_array_and_index(result, field_name=field_name, array=array)
        kwargs[field_name] = artifact
    with pytest.raises(StageCCaptureError, match=message):
        _replay_artifacts(
            result,
            index_artifact=index,
            input_ids=kwargs.get("input_ids", result.input_ids),
            attention_mask=kwargs.get("attention_mask", result.attention_mask),
            target_vector=kwargs.get("target_vector", result.target_vector),
            wrong_layer_vector=kwargs.get(
                "wrong_layer_vector", result.wrong_layer_vector
            ),
        )


def test_swapped_vector_positions_and_index_roles_are_rejected() -> None:
    result = _capture()
    with pytest.raises(StageCCaptureError, match="exact index role"):
        _replay_artifacts(
            result,
            target_vector=result.wrong_layer_vector,
            wrong_layer_vector=result.target_vector,
        )

    payload = result.index.to_payload()
    target = payload["activations"]["target"]["array_artifact"]
    wrong = payload["activations"]["wrong_layer"]["array_artifact"]
    payload["activations"]["target"]["array_artifact"] = wrong
    payload["activations"]["wrong_layer"]["array_artifact"] = target
    with pytest.raises(StageCCaptureError, match="role/layer/module"):
        load_stagec_capture_index(_index_with_payload(result, payload))


def test_direct_result_construction_and_unregistered_bundle_are_rejected() -> None:
    with pytest.raises(StageCCaptureError, match="direct.*forbidden.*external anchor"):
        StageCCaptureResult()  # type: ignore[call-arg]

    forged = object.__new__(StageCCaptureResult)
    with pytest.raises(StageCCaptureError, match="not registered as capture-created"):
        replay_stagec_capture_result(forged)

    result = _capture()
    with pytest.raises(StageCCaptureError, match="direct.*forbidden"):
        replace(result, input_ids=result.input_ids)

    fully_populated = _forged_result(result)
    with pytest.raises(StageCCaptureError, match="not registered as capture-created"):
        replay_stagec_capture_result(fully_populated)


def test_capture_created_result_seal_and_cached_index_are_checked() -> None:
    result = _capture()
    other_request = _request(
        artifact_id="stagec-request-998",
        prompt=_OTHER_PROMPT,
    )
    object.__setattr__(result, "request_artifact", other_request)
    with pytest.raises(StageCCaptureError, match="artifact fields drifted"):
        replay_stagec_capture_result(result)

    fresh = _capture()
    other = _capture(
        request=_request(
            artifact_id="stagec-request-997",
            prompt=_OTHER_PROMPT,
        )
    )
    object.__setattr__(fresh, "index", other.index)
    with pytest.raises(StageCCaptureError, match="decoded index cache drifted"):
        replay_stagec_capture_result(fresh)

    missing_cache = _capture()
    object.__delattr__(missing_cache, "index")
    with pytest.raises(StageCCaptureError, match="decoded index cache is missing"):
        replay_stagec_capture_result(missing_cache)


def test_artifact_replay_is_consistency_only_and_cross_request_fails() -> None:
    result = _capture()
    assert replay_stagec_capture_artifacts.__doc__ is not None
    assert "trusted external capture-index ref" in replay_stagec_capture_artifacts.__doc__
    assert _replay_artifacts(result).to_payload() == result.index.to_payload()

    other_request = _request(
        artifact_id="stagec-request-999",
        prompt=_OTHER_PROMPT,
    )
    with pytest.raises(StageCCaptureError, match="different request|different request artifact"):
        _replay_artifacts(result, request_artifact=other_request)


def test_index_semantic_drift_cannot_claim_attested_global_counters() -> None:
    result = _capture()
    payload = result.index.to_payload()
    payload["telemetry"]["total_model_forward_count"] = 1
    with pytest.raises(StageCCaptureError, match="NOT_ATTESTED"):
        load_stagec_capture_index(_index_with_payload(result, payload))


@pytest.mark.parametrize(
    "defect",
    [
        "template_count_bool",
        "activation_layer_float",
        "logits_shape_bool",
        "hook_count_bool",
        "direct_generate_bool",
    ],
)
def test_index_rejects_json_bool_float_aliases_for_exact_integer_fields(
    defect: str,
) -> None:
    result = _capture()
    payload = result.index.to_payload()
    if defect == "template_count_bool":
        payload["prompt"]["chat_template_application_count"] = True
    elif defect == "activation_layer_float":
        payload["activations"]["target"]["layer_index"] = 18.0
    elif defect == "logits_shape_bool":
        payload["logits"]["shape"][0] = True
    elif defect == "hook_count_bool":
        payload["hooks"]["target_hook_count"] = True
    else:
        payload["telemetry"]["direct_generate_api_call_count"] = False
    with pytest.raises(StageCCaptureError, match="exact integer|exact integers|logits shape"):
        load_stagec_capture_index(_index_with_payload(result, payload))


def test_every_request_auth_model_tokenizer_array_and_index_id_is_unique() -> None:
    result = _capture()
    payload = result.index.to_payload()
    ids = {
        result.index_artifact.ref.artifact_id,
        result.request_artifact.ref.artifact_id,
        result.authorization_projection_artifact.ref.artifact_id,
        result.input_ids.ref.artifact_id,
        result.attention_mask.ref.artifact_id,
        result.target_vector.ref.artifact_id,
        result.wrong_layer_vector.ref.artifact_id,
        *(
            payload["identity"][name]["artifact_id"]
            for name in (
                "model_config_artifact",
                "model_weights_artifact",
                "tokenizer_json_artifact",
                "tokenizer_config_artifact",
                "chat_template_artifact",
            )
        ),
    }
    assert len(ids) == 12

    request = _request()
    ids_fixture = _artifact_ids()
    overlapping = replace(ids_fixture, capture_index=request.ref.artifact_id)
    with pytest.raises(StageCCaptureError, match="globally unique"):
        _capture(request=request, artifact_ids=overlapping)
