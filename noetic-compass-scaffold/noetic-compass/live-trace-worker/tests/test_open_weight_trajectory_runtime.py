"""Offline contract tests for the byte-attested trajectory runtime."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
import sys
import threading
import types

import numpy as np
import pytest
import torch
from torch import nn

from app.runtime.open_weight.adapter_binding import build_executable_adapter_binding
from app.runtime.open_weight.artifacts import (
    CaptureVerificationContext,
    persist_capture_create_new,
    verify_capture_receipt,
)
from app.runtime.open_weight import artifacts as capture_artifacts
from app.runtime.open_weight.engine import (
    InterventionSpec,
    LoadedOpenWeightRuntime,
    RuntimeLoadConfig,
    capture_greedy_trajectory,
    verify_loaded_weight_values,
    _file_identity,
    _hardware_runtime_identity,
    _runtime_source_manifest,
    _callable_manifest,
    _callable_identity_objects,
    _module_attribute_manifest,
    _named_buffer_manifest,
    _model_config_runtime_manifest,
    _tokenizer_callable_manifest,
    _tokenizer_callable_identity_objects,
    _tokenizer_state_manifest,
    _run_tokenizer_canary,
)
from app.runtime.open_weight.identity import (
    LocalModelSnapshot,
    attest_local_snapshot,
    canonical_json_bytes,
)


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_SOURCE = ROOT / "api" / "services" / "cas_harness_interpretability_adapter.py"


class FakeBlock(nn.Module):
    def __init__(self, hidden_size: int, offset: float):
        super().__init__()
        self.attention = nn.Identity()
        self.mlp = nn.Identity()
        self.offset = offset

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        _ = self.attention(hidden)
        return hidden + self.mlp(hidden) * 0.25 + self.offset


class FakeModel(nn.Module):
    def __init__(self, layers: int = 2, hidden_size: int = 4, vocab_size: int = 8):
        super().__init__()
        self.config = types.SimpleNamespace(
            model_type="gpt_neox",
            num_hidden_layers=layers,
            hidden_size=hidden_size,
            num_attention_heads=2,
            max_position_embeddings=128,
            vocab_size=vocab_size,
            intermediate_size=16,
            hidden_act="gelu",
            layer_norm_eps=1e-5,
            rotary_pct=0.25,
            rotary_emb_base=10000,
            use_parallel_residual=True,
            tie_word_embeddings=False,
            bos_token_id=0,
            eos_token_id=0,
            initializer_range=0.02,
            use_cache=True,
            torch_dtype="float32",
            architectures=["FakeModel"],
        )
        self.gpt_neox = nn.Module()
        self.gpt_neox.layers = nn.ModuleList(
            [FakeBlock(hidden_size, float(index + 1)) for index in range(layers)]
        )
        self.vocab_size = vocab_size
        self.scale = nn.Parameter(torch.ones(1, dtype=torch.float32))

    def forward(self, *, input_ids, attention_mask, use_cache, return_dict):
        assert use_cache is False and return_dict is True
        assert input_ids.shape == attention_mask.shape
        hidden = input_ids.float().unsqueeze(-1).repeat(1, 1, self.config.hidden_size) * self.scale
        for block in self.gpt_neox.layers:
            hidden = block(hidden)
        base = hidden.mean(dim=-1, keepdim=True)
        logits = base + torch.arange(self.vocab_size, dtype=hidden.dtype).view(1, 1, -1)
        return types.SimpleNamespace(logits=logits)


class FakeTokenizer:
    def __call__(self, text: str, *, return_tensors=None, add_special_tokens=True):
        values = [1, 2] if text else []
        if return_tensors == "pt":
            return {
                "input_ids": torch.tensor([values], dtype=torch.int64),
                "attention_mask": torch.ones((1, len(values)), dtype=torch.int64),
            }
        return {"input_ids": values}

    def decode(self, values, *, skip_special_tokens, clean_up_tokenization_spaces):
        assert skip_special_tokens is False
        assert clean_up_tokenization_spaces is False
        return " ".join(str(int(value)) for value in values)


class LongFakeTokenizer(FakeTokenizer):
    def __call__(self, text: str, *, return_tensors=None, add_special_tokens=True):
        values = [1] * 128 if text else []
        if return_tensors == "pt":
            return {
                "input_ids": torch.tensor([values], dtype=torch.int64),
                "attention_mask": torch.ones((1, len(values)), dtype=torch.int64),
            }
        return {"input_ids": values}


class ConditionalTokenizer(FakeTokenizer):
    def __init__(self):
        self.flip_hello = False

    def __call__(self, text: str, *, return_tensors=None, add_special_tokens=True):
        values = [3, 4] if text == "hello" and self.flip_hello else [1, 2]
        if return_tensors == "pt":
            return {
                "input_ids": torch.tensor([values], dtype=torch.int64),
                "attention_mask": torch.ones((1, len(values)), dtype=torch.int64),
            }
        return {"input_ids": values}


class TransitiveTokenizer(FakeTokenizer):
    def _encode(self, text: str) -> list[int]:
        return [1, 2] if text else []

    def __call__(self, text: str, *, return_tensors=None, add_special_tokens=True):
        values = self._encode(text)
        if return_tensors == "pt":
            return {
                "input_ids": torch.tensor([values], dtype=torch.int64),
                "attention_mask": torch.ones((1, len(values)), dtype=torch.int64),
            }
        return {"input_ids": values}


class StatefulTransform:
    def __init__(self, bias: float = 0.0):
        self.bias = bias

    def __call__(self, value):
        return value + self.bias


class NestedStateModel(FakeModel):
    def __init__(self):
        super().__init__()
        self.behavior = StatefulTransform()

    def forward(self, *, input_ids, attention_mask, use_cache, return_dict):
        output = super().forward(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_cache=use_cache,
            return_dict=return_dict,
        )
        output.logits = self.behavior(output.logits)
        return output


class SlottedTransform:
    __slots__ = ("bias",)

    def __init__(self, bias: float = 0.0):
        self.bias = bias

    def __call__(self, value):
        return value + self.bias


class SlottedStateModel(FakeModel):
    def __init__(self):
        super().__init__()
        self.behavior = SlottedTransform()

    def forward(self, *, input_ids, attention_mask, use_cache, return_dict):
        output = super().forward(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_cache=use_cache,
            return_dict=return_dict,
        )
        output.logits = self.behavior(output.logits)
        return output


class ClassStateModel(FakeModel):
    class_bias = 0.0

    def forward(self, *, input_ids, attention_mask, use_cache, return_dict):
        output = super().forward(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_cache=use_cache,
            return_dict=return_dict,
        )
        output.logits = output.logits + self.class_bias
        return output


HELPER_BIAS = 0.0


def helper_for_probe(value):
    return value + HELPER_BIAS


class HelperGlobalModel(FakeModel):
    def forward(self, *, input_ids, attention_mask, use_cache, return_dict):
        output = super().forward(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_cache=use_cache,
            return_dict=return_dict,
        )
        output.logits = helper_for_probe(output.logits)
        return output


class NonPersistentBufferModel(FakeModel):
    def __init__(self):
        super().__init__()
        self.register_buffer(
            "forward_bias", torch.tensor(0.0), persistent=False
        )

    def forward(self, *, input_ids, attention_mask, use_cache, return_dict):
        output = super().forward(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_cache=use_cache,
            return_dict=return_dict,
        )
        return types.SimpleNamespace(logits=output.logits + self.forward_bias)


class ConfigBiasModel(FakeModel):
    def __init__(self):
        super().__init__()
        self.config.unbound_bias = 0.0

    def forward(self, *, input_ids, attention_mask, use_cache, return_dict):
        output = super().forward(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_cache=use_cache,
            return_dict=return_dict,
        )
        return types.SimpleNamespace(logits=output.logits + self.config.unbound_bias)


class DuplicateFirstLayerModel(FakeModel):
    def forward(self, *, input_ids, attention_mask, use_cache, return_dict):
        assert use_cache is False and return_dict is True
        hidden = input_ids.float().unsqueeze(-1).repeat(1, 1, self.config.hidden_size) * self.scale
        hidden = self.gpt_neox.layers[0](hidden)
        hidden = self.gpt_neox.layers[0](hidden)
        base = hidden.mean(dim=-1, keepdim=True)
        logits = base + torch.arange(self.vocab_size, dtype=hidden.dtype).view(1, 1, -1)
        return types.SimpleNamespace(logits=logits)


def _snapshot(tmp_path: Path) -> tuple[LocalModelSnapshot, object]:
    storage = tmp_path / "model-store"
    snapshot_root = storage / "snapshots" / ("1" * 40)
    snapshot_root.mkdir(parents=True)
    (snapshot_root / "config.json").write_text(
        json.dumps(
            {
                "model_type": "gpt_neox",
                "num_hidden_layers": 2,
                "hidden_size": 4,
                "num_attention_heads": 2,
                "vocab_size": 8,
                "max_position_embeddings": 128,
                "intermediate_size": 16,
                "hidden_act": "gelu",
                "layer_norm_eps": 1e-5,
                "rotary_pct": 0.25,
                "rotary_emb_base": 10000,
                "use_parallel_residual": True,
                "tie_word_embeddings": False,
                "bos_token_id": 0,
                "eos_token_id": 0,
                "initializer_range": 0.02,
                "use_cache": True,
                "torch_dtype": "float32",
                "architectures": ["FakeModel"],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (snapshot_root / "tokenizer.json").write_text('{"version":"1.0"}', encoding="utf-8")
    (snapshot_root / "model.safetensors").write_bytes(b"not-a-real-weight-file")
    definition = LocalModelSnapshot(
        model_id="test/tiny",
        revision="1" * 40,
        snapshot_root=snapshot_root,
        model_storage_root=storage,
    )
    return definition, attest_local_snapshot(definition)


def _runtime(
    tmp_path: Path,
    model: FakeModel | None = None,
    tokenizer: FakeTokenizer | None = None,
) -> LoadedOpenWeightRuntime:
    from safetensors.torch import save_file

    definition, _ = _snapshot(tmp_path)
    model = model or FakeModel()
    save_file(model.state_dict(), definition.snapshot_root / "model.safetensors")
    attestation = attest_local_snapshot(definition)
    binding = build_executable_adapter_binding(
        model=model,
        model_id=definition.model_id,
        revision=definition.revision,
        snapshot=attestation,
        adapter_source_path=ADAPTER_SOURCE,
    )
    config = RuntimeLoadConfig(
        snapshot=definition,
        adapter_source_path=ADAPTER_SOURCE,
        entrypoint_source_path=Path(__file__).resolve(),
        minimum_available_memory_bytes=0,
        minimum_capture_available_bytes=0,
    )
    tokenizer = tokenizer or FakeTokenizer()
    return LoadedOpenWeightRuntime(
        config=config,
        model=model,
        tokenizer=tokenizer,
        initial_attestation=attestation,
        adapter=binding,
        weight_value_manifest_sha256=verify_loaded_weight_values(
            model=model, snapshot_root=definition.snapshot_root
        ),
        tokenizer_canary=_run_tokenizer_canary(tokenizer),
        dependency_versions={"torch": torch.__version__},
        runtime_source_manifest=_runtime_source_manifest(
            config, model, tokenizer
        ),
        python_executable_identity=_file_identity(Path(sys.executable)),
        hardware_runtime_identity=_hardware_runtime_identity(torch, "cpu"),
        callable_manifest=_callable_manifest(model, binding),
        tokenizer_callable_manifest=_tokenizer_callable_manifest(tokenizer),
        tokenizer_state_manifest=_tokenizer_state_manifest(tokenizer),
        module_attribute_manifest=_module_attribute_manifest(model),
        named_buffer_manifest=_named_buffer_manifest(model),
        model_config_runtime_manifest=_model_config_runtime_manifest(model),
        _execution_hmac_key=b"T" * 32,
        _consumed_execution_nonces=set(),
        _capture_lock=threading.Lock(),
        _persistence_lock=threading.RLock(),
        _callable_identity_objects=_callable_identity_objects(model),
        _tokenizer_callable_identity_objects=_tokenizer_callable_identity_objects(
            tokenizer
        ),
    )


def test_snapshot_attestation_binds_exact_config_weights_and_tokenizer(tmp_path: Path):
    definition, attestation = _snapshot(tmp_path)

    assert attestation.config_sha256 == hashlib.sha256(
        (definition.snapshot_root / "config.json").read_bytes()
    ).hexdigest().upper()
    assert len(attestation.files) == 3
    assert len(attestation.weights_manifest_sha256) == 64
    assert len(attestation.tokenizer_manifest_sha256) == 64


def test_snapshot_attestation_rejects_pickle_weights(tmp_path: Path):
    definition, _ = _snapshot(tmp_path)
    (definition.snapshot_root / "pytorch_model.bin").write_bytes(b"pickle-is-not-admitted")

    with pytest.raises(ValueError, match="not on the local-safe allowlist"):
        attest_local_snapshot(definition)


def test_snapshot_attestation_rejects_nested_files(tmp_path: Path):
    definition, _ = _snapshot(tmp_path)
    nested = definition.snapshot_root / "nested"
    nested.mkdir()
    (nested / "tokenizer.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="nested snapshot entries"):
        attest_local_snapshot(definition)


def test_snapshot_revision_must_match_snapshot_directory(tmp_path: Path):
    definition, _ = _snapshot(tmp_path)
    mismatched = LocalModelSnapshot(
        model_id=definition.model_id,
        revision="2" * 40,
        snapshot_root=definition.snapshot_root,
        model_storage_root=definition.model_storage_root,
    )

    with pytest.raises(ValueError, match="directory name"):
        attest_local_snapshot(mismatched)


def test_adapter_rejects_config_bytes_that_disagree_with_loaded_model(tmp_path: Path):
    definition, _ = _snapshot(tmp_path)
    config_path = definition.snapshot_root / "config.json"
    value = json.loads(config_path.read_text(encoding="utf-8"))
    value["hidden_size"] = 999
    config_path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    attestation = attest_local_snapshot(definition)

    with pytest.raises(RuntimeError, match="loaded model config differs"):
        build_executable_adapter_binding(
            model=FakeModel(),
            model_id=definition.model_id,
            revision=definition.revision,
            snapshot=attestation,
            adapter_source_path=ADAPTER_SOURCE,
        )


def test_adapter_rejects_behavior_critical_config_mismatch(tmp_path: Path):
    definition, _ = _snapshot(tmp_path)
    config_path = definition.snapshot_root / "config.json"
    value = json.loads(config_path.read_text(encoding="utf-8"))
    value["rotary_pct"] = 0.5
    config_path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    attestation = attest_local_snapshot(definition)

    with pytest.raises(RuntimeError, match="loaded model config differs"):
        build_executable_adapter_binding(
            model=FakeModel(),
            model_id=definition.model_id,
            revision=definition.revision,
            snapshot=attestation,
            adapter_source_path=ADAPTER_SOURCE,
        )


def test_loaded_weight_values_are_compared_to_safetensors_values(tmp_path: Path):
    from safetensors.torch import save_file

    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir()
    expected = torch.arange(6, dtype=torch.float32).reshape(2, 3)
    save_file({"weight": expected}, snapshot_root / "model.safetensors")
    model = nn.Module()
    model.register_parameter("weight", nn.Parameter(expected.clone()))

    digest = verify_loaded_weight_values(model=model, snapshot_root=snapshot_root)
    assert len(digest) == 64
    with torch.no_grad():
        model.weight[0, 0] = 99
    with pytest.raises(RuntimeError, match="do not match safetensors bytes"):
        verify_loaded_weight_values(model=model, snapshot_root=snapshot_root)


def test_loaded_weight_hash_supports_scalar_and_bfloat16_tensors(tmp_path: Path):
    from safetensors.torch import save_file

    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir()
    model = nn.Module()
    model.register_parameter("scalar", nn.Parameter(torch.tensor(1.25)))
    model.register_parameter(
        "bf16", nn.Parameter(torch.arange(4, dtype=torch.bfloat16).reshape(2, 2))
    )
    save_file(model.state_dict(), snapshot_root / "model.safetensors")

    digest = verify_loaded_weight_values(model=model, snapshot_root=snapshot_root)
    assert len(digest) == 64


def test_capture_rechecks_loaded_values_before_forward(tmp_path: Path):
    runtime = _runtime(tmp_path)
    with torch.no_grad():
        runtime.model.scale.add_(1.0)

    with pytest.raises(RuntimeError, match="loaded model values do not match"):
        capture_greedy_trajectory(
            runtime,
            scenario_id="mutated-runtime",
            prompt="hello",
            max_new_tokens=1,
        )


def test_real_hook_paths_capture_full_width_all_layers_and_steps(tmp_path: Path):
    runtime = _runtime(tmp_path)

    capture = capture_greedy_trajectory(
        runtime,
        scenario_id="tiny-baseline",
        prompt="hello",
        max_new_tokens=2,
        seed=0,
    )

    assert capture.arrays["residual_states"].shape == (2, 2, 4)
    assert capture.arrays["mlp_states"].shape == (2, 2, 4)
    assert capture.arrays["pre_selection_logits"].shape == (2, 8)
    assert capture.arrays["generated_token_ids"].tolist() == [7, 7]
    assert capture.observation["packet_eligibility"] == "NOT_PACKET_ELIGIBLE"
    assert capture.observation["scientific_status"] == "NOT_A_SCIENTIFIC_EXPERIMENT_RESULT"
    assert all(value.dtype != object for value in capture.arrays.values())
    assert all(not block._forward_hooks for block in runtime.model.gpt_neox.layers)
    assert all(not block.mlp._forward_hooks for block in runtime.model.gpt_neox.layers)


def test_duplicate_and_missing_layer_hook_invocations_fail_closed(tmp_path: Path):
    runtime = _runtime(tmp_path, DuplicateFirstLayerModel())

    with pytest.raises(RuntimeError, match="hook coverage mismatch"):
        capture_greedy_trajectory(
            runtime,
            scenario_id="duplicate-layer",
            prompt="hello",
            max_new_tokens=1,
        )


def test_intervention_target_must_fire_exactly_once(tmp_path: Path):
    runtime = _runtime(tmp_path, DuplicateFirstLayerModel())

    with pytest.raises(RuntimeError, match="intervention target invocation mismatch"):
        capture_greedy_trajectory(
            runtime,
            scenario_id="duplicate-target",
            prompt="hello",
            max_new_tokens=1,
            intervention=InterventionSpec(mode="zero", layer_index=0, active_steps=(0,)),
        )


def test_preexisting_model_hook_is_rejected_before_capture(tmp_path: Path):
    runtime = _runtime(tmp_path)
    handle = runtime.model.gpt_neox.layers[0].register_forward_hook(
        lambda _module, _inputs, output: output * 0
    )
    try:
        with pytest.raises(RuntimeError, match="hook ownership mismatch"):
            capture_greedy_trajectory(
                runtime,
                scenario_id="external-hook",
                prompt="hello",
                max_new_tokens=1,
            )
    finally:
        handle.remove()


def test_instance_level_model_forward_override_is_rejected(tmp_path: Path):
    runtime = _runtime(tmp_path)
    original = runtime.model.forward

    def altered(self, **kwargs):
        output = original(**kwargs)
        output.logits[..., 0] += 1000
        return output

    runtime.model.forward = types.MethodType(altered, runtime.model)
    with pytest.raises(RuntimeError, match="forward override"):
        capture_greedy_trajectory(
            runtime,
            scenario_id="altered-forward",
            prompt="hello",
            max_new_tokens=1,
        )


def test_instance_level_tokenizer_decode_override_is_rejected(tmp_path: Path):
    runtime = _runtime(tmp_path)
    runtime.tokenizer.decode = lambda *_args, **_kwargs: "forged"

    with pytest.raises(RuntimeError, match="tokenizer decode override"):
        capture_greedy_trajectory(
            runtime,
            scenario_id="altered-tokenizer",
            prompt="hello",
            max_new_tokens=1,
        )


def test_reattest_rejects_tokenizer_class_callable_replacement_with_same_code(
    tmp_path: Path,
):
    runtime = _runtime(tmp_path)
    original = FakeTokenizer.__call__
    changed_globals = dict(original.__globals__)
    changed_globals["torch"] = types.SimpleNamespace(
        tensor=lambda values, **kwargs: torch.tensor(
            [[3, 4]] if values == [[1, 2]] else values, **kwargs
        ),
        ones=torch.ones,
    )
    replacement = types.FunctionType(
        original.__code__,
        changed_globals,
        name=original.__name__,
        argdefs=original.__defaults__,
        closure=original.__closure__,
    )
    replacement.__module__ = original.__module__
    replacement.__qualname__ = original.__qualname__
    FakeTokenizer.__call__ = replacement
    try:
        with pytest.raises(RuntimeError, match="tokenizer callable"):
            runtime.reattest()
    finally:
        FakeTokenizer.__call__ = original


def test_prompt_plus_horizon_must_fit_context_window(tmp_path: Path):
    runtime = _runtime(tmp_path, tokenizer=LongFakeTokenizer())

    with pytest.raises(ValueError, match="exceeds model context"):
        capture_greedy_trajectory(
            runtime,
            scenario_id="too-long",
            prompt="hello",
            max_new_tokens=1,
        )


def test_noop_intervention_is_exactly_equal_to_baseline(tmp_path: Path):
    runtime = _runtime(tmp_path)
    baseline = capture_greedy_trajectory(
        runtime,
        scenario_id="baseline",
        prompt="hello",
        max_new_tokens=2,
    )
    noop = capture_greedy_trajectory(
        runtime,
        scenario_id="noop",
        prompt="hello",
        max_new_tokens=2,
        intervention=InterventionSpec(
            mode="noop", layer_index=0, active_steps=(0, 1)
        ),
    )

    for key in baseline.arrays:
        np.testing.assert_array_equal(baseline.arrays[key], noop.arrays[key])


def test_zero_intervention_changes_registered_residual_only_when_active(tmp_path: Path):
    runtime = _runtime(tmp_path)
    baseline = capture_greedy_trajectory(
        runtime,
        scenario_id="baseline",
        prompt="hello",
        max_new_tokens=2,
    )
    zeroed = capture_greedy_trajectory(
        runtime,
        scenario_id="zero",
        prompt="hello",
        max_new_tokens=2,
        intervention=InterventionSpec(
            mode="zero", layer_index=0, active_steps=(0,)
        ),
    )

    np.testing.assert_array_equal(zeroed.arrays["residual_states"][0, 0], 0)
    assert not np.array_equal(
        baseline.arrays["residual_states"][0], zeroed.arrays["residual_states"][0]
    )
    np.testing.assert_array_equal(
        baseline.arrays["residual_states"][1], zeroed.arrays["residual_states"][1]
    )


def test_vector_intervention_fails_closed_on_norm_or_shape():
    with pytest.raises(ValueError, match="hidden_size"):
        InterventionSpec(
            mode="additive",
            layer_index=0,
            active_steps=(0,),
            vector=(1.0,),
            max_vector_norm=2.0,
        ).validate(layer_count=2, hidden_size=4)
    with pytest.raises(ValueError, match="exceeds"):
        InterventionSpec(
            mode="additive",
            layer_index=0,
            active_steps=(0,),
            vector=(1.0, 1.0, 1.0, 1.0),
            max_vector_norm=1.0,
        ).validate(layer_count=2, hidden_size=4)


def test_create_once_receipt_rejects_artifact_tamper_and_overwrite(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime")
    capture = capture_greedy_trajectory(
        runtime,
        scenario_id="persisted",
        prompt="hello",
        max_new_tokens=1,
    )
    output = tmp_path / "output"
    output.mkdir()
    receipt = persist_capture_create_new(
        runtime=runtime,
        capture=capture,
        output_directory=output,
        artifact_stem="capture",
    )
    context = CaptureVerificationContext.from_runtime_capture(runtime, capture)

    receipt_path = output / "capture.receipt.json"
    assert verify_capture_receipt(receipt_path, context=context)["receipt_sha256"] == receipt["receipt_sha256"]
    with pytest.raises(FileExistsError):
        persist_capture_create_new(
            runtime=runtime,
            capture=capture,
            output_directory=output,
            artifact_stem="capture",
        )
    with pytest.raises(RuntimeError, match="nonce was already consumed"):
        persist_capture_create_new(
            runtime=runtime,
            capture=capture,
            output_directory=output,
            artifact_stem="second-name",
        )
    tensor_path = output / "capture.safetensors"
    tensor_path.write_bytes(tensor_path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="byte count mismatch"):
        verify_capture_receipt(receipt_path, context=context)


def test_execution_nonce_is_atomically_one_use_under_concurrent_persistence(
    tmp_path: Path,
):
    runtime = _runtime(tmp_path / "runtime")
    capture = capture_greedy_trajectory(
        runtime,
        scenario_id="concurrent-one-use",
        prompt="hello",
        max_new_tokens=1,
    )
    outputs = [tmp_path / "output-a", tmp_path / "output-b"]
    for output in outputs:
        output.mkdir()
    barrier = threading.Barrier(3)
    results: list[tuple[str, object]] = []
    result_lock = threading.Lock()

    def persist(index: int) -> None:
        barrier.wait()
        try:
            value: object = persist_capture_create_new(
                runtime=runtime,
                capture=capture,
                output_directory=outputs[index],
                artifact_stem="capture",
            )
            status = "accepted"
        except Exception as exc:  # expected for exactly one contender
            value = exc
            status = "rejected"
        with result_lock:
            results.append((status, value))

    threads = [threading.Thread(target=persist, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive()

    assert [status for status, _value in results].count("accepted") == 1
    assert [status for status, _value in results].count("rejected") == 1
    rejection = next(value for status, value in results if status == "rejected")
    assert isinstance(rejection, RuntimeError)


def test_persistence_rejects_overlap_with_an_active_capture_lock(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime")
    capture = capture_greedy_trajectory(
        runtime,
        scenario_id="capture-persistence-exclusion",
        prompt="hello",
        max_new_tokens=1,
    )
    output = tmp_path / "output"
    output.mkdir()
    assert runtime._capture_lock.acquire(blocking=False)
    try:
        with pytest.raises(RuntimeError, match="may not overlap"):
            persist_capture_create_new(
                runtime=runtime,
                capture=capture,
                output_directory=output,
                artifact_stem="capture",
            )
    finally:
        runtime._capture_lock.release()


def test_reattest_rejects_behavior_changing_non_state_module_attribute(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime")
    runtime.model.gpt_neox.layers[0].offset = 1000.0
    with pytest.raises(RuntimeError, match="non-state runtime attributes changed"):
        runtime.reattest()


def test_reattest_rejects_nested_stateful_module_attribute_mutation(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime", model=NestedStateModel())
    runtime.model.behavior.bias = 100.0
    with pytest.raises(RuntimeError, match="non-state runtime attributes changed"):
        runtime.reattest()


def test_reattest_rejects_slotted_callable_attribute_mutation(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime", model=SlottedStateModel())
    runtime.model.behavior.bias = 100.0
    with pytest.raises(RuntimeError, match="non-state runtime attributes changed"):
        runtime.reattest()


def test_reattest_rejects_referenced_class_state_mutation(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime", model=ClassStateModel())
    ClassStateModel.class_bias = 100.0
    try:
        with pytest.raises(RuntimeError, match="callable identity changed"):
            runtime.reattest()
    finally:
        ClassStateModel.class_bias = 0.0


def test_reattest_rejects_class_forward_object_replacement_with_same_code(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime")
    original = FakeModel.forward
    replacement = types.FunctionType(
        original.__code__,
        dict(original.__globals__),
        name=original.__name__,
        argdefs=original.__defaults__,
        closure=original.__closure__,
    )
    replacement.__module__ = original.__module__
    replacement.__qualname__ = original.__qualname__
    FakeModel.forward = replacement
    try:
        with pytest.raises(RuntimeError, match="callable"):
            runtime.reattest()
    finally:
        FakeModel.forward = original


def test_reattest_rejects_referenced_helper_global_mutation(tmp_path: Path):
    global HELPER_BIAS

    runtime = _runtime(tmp_path / "runtime", model=HelperGlobalModel())
    HELPER_BIAS = 100.0
    try:
        with pytest.raises(RuntimeError, match="callable identity changed"):
            runtime.reattest()
    finally:
        HELPER_BIAS = 0.0


def test_reattest_rejects_tokenizer_state_change_outside_canary_text(tmp_path: Path):
    tokenizer = ConditionalTokenizer()
    runtime = _runtime(tmp_path / "runtime", tokenizer=tokenizer)
    tokenizer.flip_hello = True
    with pytest.raises(RuntimeError, match="tokenizer behavioral state changed"):
        runtime.reattest()


def test_reattest_rejects_transitive_tokenizer_method_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runtime = _runtime(tmp_path / "runtime", tokenizer=TransitiveTokenizer())

    def changed_encode(self, text: str) -> list[int]:
        return [9] if text else []

    monkeypatch.setattr(TransitiveTokenizer, "_encode", changed_encode)
    with pytest.raises(RuntimeError, match="tokenizer callable identity changed"):
        runtime.reattest()


def test_reattest_rejects_nonpersistent_named_buffer_mutation(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime", model=NonPersistentBufferModel())
    runtime.model.forward_bias.fill_(100.0)
    with pytest.raises(RuntimeError, match="named-buffer values changed"):
        runtime.reattest()


def test_reattest_rejects_unprojected_runtime_config_mutation(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime", model=ConfigBiasModel())
    runtime.model.config.unbound_bias = 100.0
    with pytest.raises(RuntimeError, match="configuration state changed"):
        runtime.reattest()


def test_reattest_rejects_compiled_call_override(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime")
    runtime.model._compiled_call_impl = lambda *args, **kwargs: runtime.model.forward(
        *args, **kwargs
    )
    with pytest.raises(RuntimeError, match="compiled module call overrides"):
        runtime.reattest()


def test_reattest_rejects_pytorch_module_dispatch_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runtime = _runtime(tmp_path / "runtime")
    original = nn.Module._call_impl

    def changed_call_impl(self, *args, **kwargs):
        return original(self, *args, **kwargs)

    monkeypatch.setattr(nn.Module, "_call_impl", changed_call_impl)
    with pytest.raises(RuntimeError, match="callable identity changed"):
        runtime.reattest()


def test_reattest_rejects_pytorch_module_getattr_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runtime = _runtime(tmp_path / "runtime")
    original = nn.Module.__getattr__

    def changed_getattr(self, name):
        return original(self, name)

    monkeypatch.setattr(nn.Module, "__getattr__", changed_getattr)
    with pytest.raises(RuntimeError, match="callable identity changed"):
        runtime.reattest()


def test_reattest_rejects_forward_hook_registration_api_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runtime = _runtime(tmp_path / "runtime")
    original = nn.Module.register_forward_hook

    def changed_register_forward_hook(self, hook, *args, **kwargs):
        return original(self, hook, *args, **kwargs)

    monkeypatch.setattr(nn.Module, "register_forward_hook", changed_register_forward_hook)
    with pytest.raises(RuntimeError, match="callable identity changed"):
        runtime.reattest()


def test_reattest_rejects_state_dict_spoof_after_parameter_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runtime = _runtime(tmp_path / "runtime")
    original_state_dict = nn.Module.state_dict
    saved = {name: value.detach().clone() for name, value in runtime.model.state_dict().items()}
    runtime.model.scale.data.mul_(10.0)

    def spoofed_state_dict(self, *args, **kwargs):
        if self is runtime.model:
            return {name: value.detach().clone() for name, value in saved.items()}
        return original_state_dict(self, *args, **kwargs)

    monkeypatch.setattr(nn.Module, "state_dict", spoofed_state_dict)
    with pytest.raises(RuntimeError, match="callable identity changed"):
        runtime.reattest()


def test_reattest_rejects_referenced_module_callable_mutation(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime")
    original = torch.arange

    def changed_arange(*args, **kwargs):
        return original(*args, **kwargs) + 100

    torch.arange = changed_arange
    try:
        with pytest.raises(RuntimeError, match="callable identity changed"):
            runtime.reattest()
    finally:
        torch.arange = original


def test_persistence_serializes_private_array_snapshot_after_record_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from safetensors.numpy import load

    runtime = _runtime(tmp_path / "runtime")
    capture = capture_greedy_trajectory(
        runtime,
        scenario_id="private-array-snapshot",
        prompt="hello",
        max_new_tokens=1,
    )
    expected = np.array(capture.arrays["residual_states"], copy=True)
    original_verify = capture_artifacts.verify_and_consume_execution_record

    def verify_then_mutate_caller_capture(runtime_arg, private_capture):
        original_verify(runtime_arg, private_capture)
        capture.arrays["residual_states"].fill(np.float32(12345.0))

    monkeypatch.setattr(
        capture_artifacts,
        "verify_and_consume_execution_record",
        verify_then_mutate_caller_capture,
    )
    output = tmp_path / "output"
    output.mkdir()
    receipt = persist_capture_create_new(
        runtime=runtime,
        capture=capture,
        output_directory=output,
        artifact_stem="capture",
    )
    arrays = load((output / "capture.safetensors").read_bytes())
    np.testing.assert_array_equal(arrays["residual_states"], expected)
    manifest_digest = hashlib.sha256(
        canonical_json_bytes(receipt["output"]["array_manifest"])
    ).hexdigest().upper()
    assert receipt["observation"]["execution_record"]["array_manifest_sha256"] == manifest_digest


def _persist_for_hostile_test(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime")
    capture = capture_greedy_trajectory(
        runtime,
        scenario_id="hostile",
        prompt="hello",
        max_new_tokens=1,
    )
    output = tmp_path / "output"
    output.mkdir()
    persist_capture_create_new(
        runtime=runtime,
        capture=capture,
        output_directory=output,
        artifact_stem="capture",
    )
    return output, CaptureVerificationContext.from_runtime_capture(runtime, capture)


def _rewrite_receipt(path: Path, mutate) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    value.pop("receipt_sha256", None)
    value["receipt_sha256"] = hashlib.sha256(canonical_json_bytes(value)).hexdigest().upper()
    path.write_bytes(canonical_json_bytes(value))


def test_receipt_rejects_rehashed_semantic_claim_forgery(tmp_path: Path):
    output, context = _persist_for_hostile_test(tmp_path)
    receipt_path = output / "capture.receipt.json"

    def mutate(value):
        value["status"] = "SCIENTIFICALLY_VALIDATED_CAUSAL_SAFETY_RESULT"
        value["scientific_status"] = "VALIDATED"
        value["claim_boundary"] = "PRODUCTION EVIDENCE PACKET"

    _rewrite_receipt(receipt_path, mutate)
    with pytest.raises(ValueError, match="status literal mismatch"):
        verify_capture_receipt(receipt_path, context=context)


def test_persistence_rejects_baseline_capture_relabelled_as_noop(tmp_path: Path):
    runtime = _runtime(tmp_path / "runtime")
    baseline = capture_greedy_trajectory(
        runtime,
        scenario_id="baseline",
        prompt="hello",
        max_new_tokens=1,
    )
    observation = dict(baseline.observation)
    observation["intervention"] = InterventionSpec(
        mode="noop", layer_index=0, active_steps=(0,)
    ).to_dict()
    relabelled = replace(baseline, observation=observation)
    output = tmp_path / "output"
    output.mkdir()

    with pytest.raises(RuntimeError, match="execution record"):
        persist_capture_create_new(
            runtime=runtime,
            capture=relabelled,
            output_directory=output,
            artifact_stem="false-noop",
        )


def test_receipt_rejects_rehashed_plan_substitution(tmp_path: Path):
    output, context = _persist_for_hostile_test(tmp_path)
    receipt_path = output / "capture.receipt.json"
    plan_path = output / "capture.adapter-plan.json"
    replacement = b"NOT JSON OR AN ADAPTER PLAN"
    plan_path.write_bytes(replacement)

    def mutate(value):
        digest = hashlib.sha256(replacement).hexdigest().upper()
        value["output"]["adapter_plan_byte_count"] = len(replacement)
        value["output"]["adapter_plan_file_sha256"] = digest
        value["observation"]["adapter"]["adapter_plan_file_sha256"] = digest

    _rewrite_receipt(receipt_path, mutate)
    with pytest.raises((ValueError, json.JSONDecodeError)):
        verify_capture_receipt(receipt_path, context=context)


def test_receipt_rejects_rehashed_tensor_path_substitution(tmp_path: Path):
    output, context = _persist_for_hostile_test(tmp_path)
    receipt_path = output / "capture.receipt.json"
    outside = tmp_path / "outside.safetensors"
    outside.write_bytes((output / "capture.safetensors").read_bytes())

    def mutate(value):
        value["output"]["tensor_path"] = str(outside)

    _rewrite_receipt(receipt_path, mutate)
    with pytest.raises(ValueError, match="fixed same-directory"):
        verify_capture_receipt(receipt_path, context=context)


def test_receipt_rejects_rehashed_generated_text_substitution(tmp_path: Path):
    output, context = _persist_for_hostile_test(tmp_path)
    receipt_path = output / "capture.receipt.json"

    def mutate(value):
        value["output"]["generated_text"] = "fabricated output"

    _rewrite_receipt(receipt_path, mutate)
    with pytest.raises(ValueError, match="generated_text differs"):
        verify_capture_receipt(receipt_path, context=context)


def test_receipt_rejects_rehashed_tensor_value_substitution(tmp_path: Path):
    from safetensors.numpy import load, save

    output, context = _persist_for_hostile_test(tmp_path)
    receipt_path = output / "capture.receipt.json"
    tensor_path = output / "capture.safetensors"
    arrays = load(tensor_path.read_bytes())
    arrays["residual_states"] = arrays["residual_states"].copy()
    arrays["residual_states"][0, 0, 0] += np.float32(100.0)
    metadata = {
        "schema_version": "cas_open_weight_trajectory_tensors.v1",
        "scenario_id": context.scenario_id,
        "prompt_sha256": hashlib.sha256(context.prompt.encode("utf-8")).hexdigest().upper(),
        "model_tree_manifest_sha256": context.model_attestation.tree_manifest_sha256,
        "loaded_weight_value_manifest_sha256": context.loaded_weight_value_manifest_sha256,
        "adapter_plan_sha256": context.adapter_plan_sha256,
        "packet_eligibility": "NOT_PACKET_ELIGIBLE",
    }
    replacement = save(arrays, metadata=metadata)
    tensor_path.write_bytes(replacement)

    def mutate(value):
        value["output"]["tensor_byte_count"] = len(replacement)
        value["output"]["tensor_sha256"] = hashlib.sha256(replacement).hexdigest().upper()
        rows = []
        for name, array in sorted(arrays.items()):
            rows.append(
                {
                    "name": name,
                    "shape": list(array.shape),
                    "dtype": str(array.dtype),
                    "byte_count": int(array.nbytes),
                    "value_sha256": hashlib.sha256(
                        np.ascontiguousarray(array).tobytes(order="C")
                    ).hexdigest().upper(),
                }
            )
        value["output"]["array_manifest"] = rows

    _rewrite_receipt(receipt_path, mutate)
    with pytest.raises(ValueError, match="array manifest differs"):
        verify_capture_receipt(receipt_path, context=context)
