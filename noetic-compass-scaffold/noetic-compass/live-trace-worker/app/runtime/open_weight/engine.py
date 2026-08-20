"""Local-only, real-model trajectory capture and bounded interventions.

This is an engineering vertical slice.  It loads one exact local snapshot,
verifies loaded parameter values against the safetensors values, consumes the
registered architecture adapter, and performs deterministic manual greedy
generation while capturing full-width residual, MLP, and logit tensors.

The output remains ``NOT_PACKET_ELIGIBLE``: local hashes and self-checks are
integrity evidence, not external custody, preregistration, labels, controls, or
scientific validation.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import importlib.metadata
import importlib
import inspect
import math
import marshal
import os
from pathlib import Path
import platform
import random
import secrets
import sys
import threading
import time
import types
from typing import Any, Iterable, Literal, Mapping, Sequence

import numpy as np

from .adapter_binding import (
    ExecutableAdapterBinding,
    build_executable_adapter_binding,
    resolve_attr_path,
    verify_loaded_model_config,
)
from .contracts import (
    CAPTURE_SCHEMA,
    CAPTURE_STATUS,
    OBSERVATION_CLAIM_BOUNDARY,
    PACKET_ELIGIBILITY,
    SCIENTIFIC_STATUS,
)
from .identity import (
    LocalModelSnapshot,
    SnapshotAttestation,
    attest_local_snapshot,
    canonical_json_bytes,
    require_same_attestation,
)


InterventionMode = Literal["baseline", "noop", "zero", "additive", "patch"]


@dataclass(frozen=True)
class RuntimeLoadConfig:
    snapshot: LocalModelSnapshot
    adapter_source_path: Path
    entrypoint_source_path: Path
    device: str = "cpu"
    dtype: str = "auto"
    minimum_available_memory_bytes: int = 4 * 1024 * 1024 * 1024
    minimum_capture_available_bytes: int = 1024 * 1024 * 1024

    def validate(self) -> None:
        self.snapshot.validate()
        if not self.adapter_source_path.is_absolute() or not self.adapter_source_path.is_file():
            raise ValueError("adapter_source_path must be an existing absolute file")
        if not self.entrypoint_source_path.is_absolute() or not self.entrypoint_source_path.is_file():
            raise ValueError("entrypoint_source_path must be an existing absolute file")
        if self.device != "cpu" and not self.device.startswith("cuda:"):
            raise ValueError("device must be cpu or an explicit cuda:N device")
        if self.dtype != "auto":
            raise ValueError("dtype must be auto so loaded bytes retain the source dtype")
        for label, value in (
            ("minimum_available_memory_bytes", self.minimum_available_memory_bytes),
            ("minimum_capture_available_bytes", self.minimum_capture_available_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{label} must be a non-negative integer")


@dataclass(frozen=True)
class InterventionSpec:
    mode: InterventionMode = "baseline"
    layer_index: int | None = None
    active_steps: tuple[int, ...] = ()
    vector: tuple[float, ...] | None = None
    max_vector_norm: float = 0.0

    def validate(self, *, layer_count: int, hidden_size: int) -> None:
        if self.mode == "baseline":
            if self.layer_index is not None or self.active_steps or self.vector is not None:
                raise ValueError("baseline intervention must not carry layer/step/vector fields")
            if self.max_vector_norm != 0.0:
                raise ValueError("baseline max_vector_norm must be zero")
            return
        if isinstance(self.layer_index, bool) or not isinstance(self.layer_index, int):
            raise ValueError("non-baseline intervention requires an integer layer_index")
        if not 0 <= self.layer_index < layer_count:
            raise ValueError("intervention layer_index is outside the adapter plan")
        if not self.active_steps:
            raise ValueError("non-baseline intervention requires active_steps")
        if any(isinstance(step, bool) or not isinstance(step, int) or step < 0 for step in self.active_steps):
            raise ValueError("active_steps must contain non-negative integers")
        if len(self.active_steps) != len(set(self.active_steps)):
            raise ValueError("active_steps must be unique")
        if self.mode in {"noop", "zero"}:
            if self.vector is not None:
                raise ValueError(f"{self.mode} intervention must not carry a vector")
            if self.max_vector_norm != 0.0:
                raise ValueError(f"{self.mode} max_vector_norm must be zero")
            return
        if self.mode not in {"additive", "patch"}:
            raise ValueError(f"unsupported intervention mode: {self.mode}")
        if self.vector is None or len(self.vector) != hidden_size:
            raise ValueError(f"{self.mode} vector must have exactly hidden_size values")
        if not all(math.isfinite(float(value)) for value in self.vector):
            raise ValueError("intervention vector must contain only finite values")
        if not math.isfinite(self.max_vector_norm) or self.max_vector_norm <= 0:
            raise ValueError("vector intervention requires a finite positive max_vector_norm")
        norm = math.sqrt(sum(float(value) ** 2 for value in self.vector))
        if norm > self.max_vector_norm + 1e-12:
            raise ValueError("intervention vector exceeds max_vector_norm")

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "layer_index": self.layer_index,
            "active_steps": list(self.active_steps),
            "vector_sha256": (
                hashlib.sha256(
                    np.asarray(self.vector, dtype=np.float32).tobytes(order="C")
                ).hexdigest().upper()
                if self.vector is not None
                else None
            ),
            "vector_length": len(self.vector) if self.vector is not None else 0,
            "max_vector_norm": self.max_vector_norm,
        }


@dataclass
class LoadedOpenWeightRuntime:
    config: RuntimeLoadConfig
    model: Any
    tokenizer: Any
    initial_attestation: SnapshotAttestation
    adapter: ExecutableAdapterBinding
    weight_value_manifest_sha256: str
    tokenizer_canary: Mapping[str, object]
    dependency_versions: Mapping[str, str]
    runtime_source_manifest: tuple[Mapping[str, object], ...]
    python_executable_identity: Mapping[str, object]
    hardware_runtime_identity: Mapping[str, object]
    callable_manifest: tuple[Mapping[str, object], ...]
    tokenizer_callable_manifest: tuple[Mapping[str, object], ...]
    tokenizer_state_manifest: Mapping[str, object]
    module_attribute_manifest: tuple[Mapping[str, object], ...]
    named_buffer_manifest: tuple[Mapping[str, object], ...]
    model_config_runtime_manifest: Mapping[str, object]
    _execution_hmac_key: bytes = field(repr=False)
    _consumed_execution_nonces: set[str] = field(repr=False)
    _capture_lock: Any = field(repr=False)
    _persistence_lock: Any = field(repr=False)
    _callable_identity_objects: tuple[Any, ...] = field(repr=False)
    _tokenizer_callable_identity_objects: tuple[Any, ...] = field(repr=False)

    @property
    def layer_count(self) -> int:
        return len(self.adapter.residual_paths)

    @property
    def hidden_size(self) -> int:
        return int(self.adapter.plan["declaration"]["hidden_size"])

    def reattest(self) -> None:
        observed = attest_local_snapshot(self.config.snapshot)
        require_same_attestation(self.initial_attestation, observed)
        loaded_digest = verify_loaded_weight_values(
            model=self.model,
            snapshot_root=self.config.snapshot.snapshot_root,
        )
        if loaded_digest != self.weight_value_manifest_sha256:
            raise RuntimeError("loaded model tensor values changed after initial verification")
        config_projection = verify_loaded_model_config(
            self.initial_attestation, self.model
        )
        if config_projection != dict(self.adapter.config_projection):
            raise RuntimeError("loaded model config changed after adapter binding")
        if _runtime_source_manifest(self.config, self.model, self.tokenizer) != self.runtime_source_manifest:
            raise RuntimeError("runtime source bytes changed after initial verification")
        if _file_identity(Path(sys.executable)) != self.python_executable_identity:
            raise RuntimeError("Python executable bytes changed after initial verification")
        if _callable_manifest(self.model, self.adapter) != self.callable_manifest:
            raise RuntimeError("model or hook-target forward callable identity changed")
        current_callables = _callable_identity_objects(self.model)
        if len(current_callables) != len(self._callable_identity_objects) or any(
            observed is not expected
            for observed, expected in zip(
                current_callables, self._callable_identity_objects, strict=True
            )
        ):
            raise RuntimeError("model forward callable object identity changed")
        if _tokenizer_callable_manifest(self.tokenizer) != self.tokenizer_callable_manifest:
            raise RuntimeError("tokenizer callable identity changed")
        current_tokenizer_callables = _tokenizer_callable_identity_objects(self.tokenizer)
        if len(current_tokenizer_callables) != len(
            self._tokenizer_callable_identity_objects
        ) or any(
            observed is not expected
            for observed, expected in zip(
                current_tokenizer_callables,
                self._tokenizer_callable_identity_objects,
                strict=True,
            )
        ):
            raise RuntimeError("tokenizer callable object identity changed")
        if _tokenizer_state_manifest(self.tokenizer) != self.tokenizer_state_manifest:
            raise RuntimeError("tokenizer behavioral state changed")
        if _model_config_runtime_manifest(self.model) != self.model_config_runtime_manifest:
            raise RuntimeError("loaded model configuration state changed")
        if _module_attribute_manifest(self.model) != self.module_attribute_manifest:
            raise RuntimeError("model non-state runtime attributes changed")
        if _named_buffer_manifest(self.model) != self.named_buffer_manifest:
            raise RuntimeError("model named-buffer values changed")
        if _run_tokenizer_canary(self.tokenizer) != dict(self.tokenizer_canary):
            raise RuntimeError("tokenizer canary changed after initial verification")


@dataclass(frozen=True)
class TrajectoryCapture:
    scenario_id: str
    prompt: str
    prompt_sha256: str
    generated_text: str
    arrays: Mapping[str, np.ndarray]
    observation: Mapping[str, object]
    execution_record: Mapping[str, object]


def load_open_weight_runtime(config: RuntimeLoadConfig) -> LoadedOpenWeightRuntime:
    """Load a pinned local snapshot with networking disabled and verify values."""

    config.validate()
    _require_available_memory(
        config.minimum_available_memory_bytes, phase="model-load preflight"
    )
    initial = attest_local_snapshot(config.snapshot)
    with _offline_environment():
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception as exc:  # pragma: no cover - environment-specific
            raise RuntimeError(f"real-model dependencies are unavailable: {exc}") from exc
        dtype = _resolve_dtype(torch, config.dtype)
        tokenizer = AutoTokenizer.from_pretrained(
            str(config.snapshot.snapshot_root),
            local_files_only=True,
            trust_remote_code=False,
        )
        model = AutoModelForCausalLM.from_pretrained(
            str(config.snapshot.snapshot_root),
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
            dtype=dtype,
        )
    model.eval()
    model.to(config.device)
    observed = attest_local_snapshot(config.snapshot)
    require_same_attestation(initial, observed)
    weight_value_manifest_sha256 = verify_loaded_weight_values(
        model=model,
        snapshot_root=config.snapshot.snapshot_root,
    )
    adapter = build_executable_adapter_binding(
        model=model,
        model_id=config.snapshot.model_id,
        revision=config.snapshot.revision,
        snapshot=initial,
        adapter_source_path=config.adapter_source_path,
    )
    tokenizer_canary = _run_tokenizer_canary(tokenizer)
    runtime_source_manifest = _runtime_source_manifest(config, model, tokenizer)
    python_executable_identity = _file_identity(Path(sys.executable))
    hardware_runtime_identity = _hardware_runtime_identity(torch, config.device)
    callable_manifest = _callable_manifest(model, adapter)
    tokenizer_callable_manifest = _tokenizer_callable_manifest(tokenizer)
    tokenizer_state_manifest = _tokenizer_state_manifest(tokenizer)
    module_attribute_manifest = _module_attribute_manifest(model)
    named_buffer_manifest = _named_buffer_manifest(model)
    model_config_runtime_manifest = _model_config_runtime_manifest(model)
    return LoadedOpenWeightRuntime(
        config=config,
        model=model,
        tokenizer=tokenizer,
        initial_attestation=initial,
        adapter=adapter,
        weight_value_manifest_sha256=weight_value_manifest_sha256,
        tokenizer_canary=tokenizer_canary,
        dependency_versions=_dependency_versions(),
        runtime_source_manifest=runtime_source_manifest,
        python_executable_identity=python_executable_identity,
        hardware_runtime_identity=hardware_runtime_identity,
        callable_manifest=callable_manifest,
        tokenizer_callable_manifest=tokenizer_callable_manifest,
        tokenizer_state_manifest=tokenizer_state_manifest,
        module_attribute_manifest=module_attribute_manifest,
        named_buffer_manifest=named_buffer_manifest,
        model_config_runtime_manifest=model_config_runtime_manifest,
        _execution_hmac_key=secrets.token_bytes(32),
        _consumed_execution_nonces=set(),
        _capture_lock=threading.Lock(),
        _persistence_lock=threading.RLock(),
        _callable_identity_objects=_callable_identity_objects(model),
        _tokenizer_callable_identity_objects=_tokenizer_callable_identity_objects(
            tokenizer
        ),
    )


def verify_loaded_weight_values(*, model: Any, snapshot_root: Path) -> str:
    """Compare every loaded state tensor to the exact safetensors value bytes."""

    try:
        import torch
        from safetensors import safe_open
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(f"weight verification dependencies unavailable: {exc}") from exc

    source_rows: list[dict[str, object]] = []
    source_names: set[str] = set()
    weight_paths = sorted(snapshot_root.glob("*.safetensors"), key=lambda p: p.name)
    if not weight_paths:
        raise RuntimeError("no safetensors weights found after attestation")
    for path in weight_paths:
        with safe_open(str(path), framework="pt", device="cpu") as handle:
            for name in sorted(handle.keys()):
                if name in source_names:
                    raise RuntimeError(f"duplicate tensor key across weight shards: {name}")
                source_names.add(name)
                source_rows.append(_tensor_value_row(name, handle.get_tensor(name), torch))

    state = model.state_dict()
    loaded_rows = [
        _tensor_value_row(name, state[name], torch) for name in sorted(state)
    ]
    source_rows.sort(key=lambda row: str(row["name"]).encode("utf-8"))
    loaded_rows.sort(key=lambda row: str(row["name"]).encode("utf-8"))
    if source_rows != loaded_rows:
        source_by_name = {str(row["name"]): row for row in source_rows}
        loaded_by_name = {str(row["name"]): row for row in loaded_rows}
        missing = sorted(set(source_by_name) - set(loaded_by_name))
        extra = sorted(set(loaded_by_name) - set(source_by_name))
        changed = sorted(
            name
            for name in set(source_by_name) & set(loaded_by_name)
            if source_by_name[name] != loaded_by_name[name]
        )
        raise RuntimeError(
            "loaded model values do not match safetensors bytes: "
            f"missing={missing[:5]} extra={extra[:5]} changed={changed[:5]}"
        )
    return hashlib.sha256(canonical_json_bytes(source_rows)).hexdigest().upper()


def capture_greedy_trajectory(
    runtime: LoadedOpenWeightRuntime,
    *,
    scenario_id: str,
    prompt: str,
    max_new_tokens: int,
    intervention: InterventionSpec | None = None,
    seed: int = 0,
    scenario_source: Mapping[str, object] | None = None,
) -> TrajectoryCapture:
    """Run exactly one capture at a time on a loaded runtime."""

    if not runtime._capture_lock.acquire(blocking=False):
        raise RuntimeError("concurrent captures on one runtime are forbidden")
    try:
        return _capture_greedy_trajectory_locked(
            runtime,
            scenario_id=scenario_id,
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            intervention=intervention,
            seed=seed,
            scenario_source=scenario_source,
        )
    finally:
        runtime._capture_lock.release()


def _capture_greedy_trajectory_locked(
    runtime: LoadedOpenWeightRuntime,
    *,
    scenario_id: str,
    prompt: str,
    max_new_tokens: int,
    intervention: InterventionSpec | None = None,
    seed: int = 0,
    scenario_source: Mapping[str, object] | None = None,
) -> TrajectoryCapture:
    """Capture one deterministic full-width manual greedy generation trajectory."""

    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ValueError("scenario_id must be non-empty")
    if not isinstance(prompt, str) or not prompt:
        raise ValueError("prompt must be non-empty")
    if len(prompt.encode("utf-8")) > 64 * 1024:
        raise ValueError("prompt UTF-8 bytes exceed the 64 KiB capture cap")
    if isinstance(max_new_tokens, bool) or not isinstance(max_new_tokens, int):
        raise ValueError("max_new_tokens must be an integer")
    if not 1 <= max_new_tokens <= 64:
        raise ValueError("max_new_tokens must be in [1, 64]")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    spec = intervention or InterventionSpec()
    spec.validate(layer_count=runtime.layer_count, hidden_size=runtime.hidden_size)
    if spec.active_steps and max(spec.active_steps) >= max_new_tokens:
        raise ValueError("intervention active_steps exceed the capture horizon")
    started_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    started_monotonic_ns = time.monotonic_ns()
    _require_available_memory(
        runtime.config.minimum_capture_available_bytes,
        phase="capture preflight",
    )
    runtime.reattest()

    import torch

    _require_exact_hook_state(runtime.model, expected_forward_hook_ids=set())

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    encoded = runtime.tokenizer(prompt, return_tensors="pt", add_special_tokens=True)
    if "input_ids" not in encoded or "attention_mask" not in encoded:
        raise RuntimeError("tokenizer did not return input_ids and attention_mask")
    input_ids = encoded["input_ids"].to(runtime.config.device)
    attention_mask = encoded["attention_mask"].to(runtime.config.device)
    if input_ids.ndim != 2 or input_ids.shape[0] != 1 or input_ids.shape[1] < 1:
        raise RuntimeError("tokenizer returned an invalid input_ids shape")
    context_limit = int(runtime.adapter.config_projection["max_position_embeddings"])
    if int(input_ids.shape[1]) + max_new_tokens > context_limit:
        raise ValueError("prompt plus generation horizon exceeds model context length")

    residual_steps: list[np.ndarray] = []
    mlp_steps: list[np.ndarray] = []
    logit_steps: list[np.ndarray] = []
    generated_ids: list[int] = []
    input_lengths: list[int] = []
    current_step = {"value": -1}
    per_step_residual: dict[int, dict[int, list[Any]]] = {}
    per_step_mlp: dict[int, dict[int, list[Any]]] = {}
    intervention_calls: dict[int, int] = {}
    handles: list[Any] = []

    def make_capture_hook(
        target: dict[int, dict[int, list[Any]]], layer_index: int
    ):
        def hook(_module: Any, _inputs: object, output: object) -> None:
            step = current_step["value"]
            tensor = _primary_tensor(output)
            if tensor.ndim != 3 or tensor.shape[0] != 1:
                raise RuntimeError(
                    f"hook output at layer {layer_index} is not [1, tokens, hidden]"
                )
            by_layer = target.setdefault(step, {})
            by_layer.setdefault(layer_index, []).append(
                tensor[0, -1, :].detach().cpu().clone()
            )

        return hook

    intervention_handle = None
    if spec.mode != "baseline":
        target_module = resolve_attr_path(
            runtime.model, runtime.adapter.residual_paths[int(spec.layer_index)]
        )
        vector_tensor = (
            torch.tensor(spec.vector, dtype=torch.float32)
            if spec.vector is not None
            else None
        )

        def intervention_hook(_module: Any, _inputs: object, output: object) -> object:
            step = current_step["value"]
            intervention_calls[step] = intervention_calls.get(step, 0) + 1
            if step not in spec.active_steps or spec.mode == "noop":
                return output
            tensor = _primary_tensor(output)
            if tensor.ndim != 3 or tensor.shape[-1] != runtime.hidden_size:
                raise RuntimeError("intervention hook observed an unexpected tensor shape")
            modified = tensor.clone()
            if spec.mode == "zero":
                modified[0, -1, :] = 0
            elif spec.mode == "additive":
                assert vector_tensor is not None
                delta = vector_tensor.to(device=modified.device, dtype=modified.dtype)
                modified[0, -1, :] = modified[0, -1, :] + delta
            elif spec.mode == "patch":
                assert vector_tensor is not None
                patch = vector_tensor.to(device=modified.device, dtype=modified.dtype)
                modified[0, -1, :] = patch
            else:  # pragma: no cover - validated above
                raise RuntimeError(f"unhandled intervention mode: {spec.mode}")
            if not torch.isfinite(modified).all():
                raise RuntimeError("intervention produced non-finite residual values")
            return _replace_primary_tensor(output, modified)

        intervention_handle = target_module.register_forward_hook(intervention_hook)

    try:
        for layer_index, path in enumerate(runtime.adapter.residual_paths):
            module = resolve_attr_path(runtime.model, path)
            handles.append(
                module.register_forward_hook(
                    make_capture_hook(per_step_residual, layer_index)
                )
            )
        for layer_index, path in enumerate(runtime.adapter.mlp_paths):
            module = resolve_attr_path(runtime.model, path)
            handles.append(
                module.register_forward_hook(make_capture_hook(per_step_mlp, layer_index))
            )

        expected_hook_ids = {int(handle.id) for handle in handles}
        if intervention_handle is not None:
            expected_hook_ids.add(int(intervention_handle.id))
        _require_exact_hook_state(
            runtime.model, expected_forward_hook_ids=expected_hook_ids
        )

        with torch.inference_mode():
            for step in range(max_new_tokens):
                _require_exact_hook_state(
                    runtime.model, expected_forward_hook_ids=expected_hook_ids
                )
                current_step["value"] = step
                input_lengths.append(int(input_ids.shape[1]))
                output = runtime.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    use_cache=False,
                    return_dict=True,
                )
                _require_exact_hook_state(
                    runtime.model, expected_forward_hook_ids=expected_hook_ids
                )
                if spec.mode != "baseline" and intervention_calls.get(step) != 1:
                    raise RuntimeError(
                        "intervention target invocation mismatch at step "
                        f"{step}: expected=1 observed={intervention_calls.get(step, 0)}"
                    )
                logits = output.logits[0, -1, :]
                if logits.ndim != 1 or not torch.isfinite(logits).all():
                    raise RuntimeError("model returned invalid or non-finite next-token logits")
                residual_rows = _require_exact_hook_rows(
                    per_step_residual, step, runtime.layer_count, "residual"
                )
                mlp_rows = _require_exact_hook_rows(
                    per_step_mlp, step, runtime.layer_count, "MLP"
                )
                residual_steps.append(
                    torch.stack(residual_rows).float().numpy().copy()
                )
                mlp_steps.append(torch.stack(mlp_rows).float().numpy().copy())
                logit_steps.append(logits.detach().cpu().float().numpy().copy())
                next_token = int(torch.argmax(logits).item())
                generated_ids.append(next_token)
                next_tensor = torch.tensor(
                    [[next_token]], dtype=input_ids.dtype, device=input_ids.device
                )
                input_ids = torch.cat((input_ids, next_tensor), dim=1)
                attention_mask = torch.cat(
                    (
                        attention_mask,
                        torch.ones(
                            (1, 1),
                            dtype=attention_mask.dtype,
                            device=attention_mask.device,
                        ),
                    ),
                    dim=1,
                )
    finally:
        for handle in reversed(handles):
            handle.remove()
        if intervention_handle is not None:
            intervention_handle.remove()
        _require_exact_hook_state(runtime.model, expected_forward_hook_ids=set())

    arrays = {
        "prompt_input_ids": encoded["input_ids"].detach().cpu().numpy().astype(np.int64),
        "prompt_attention_mask": encoded["attention_mask"].detach().cpu().numpy().astype(np.int64),
        "generated_token_ids": np.asarray(generated_ids, dtype=np.int64),
        "input_lengths": np.asarray(input_lengths, dtype=np.int64),
        "residual_states": np.stack(residual_steps).astype(np.float32, copy=False),
        "mlp_states": np.stack(mlp_steps).astype(np.float32, copy=False),
        "pre_selection_logits": np.stack(logit_steps).astype(np.float32, copy=False),
    }
    _validate_capture_arrays(
        arrays,
        steps=max_new_tokens,
        layers=runtime.layer_count,
        hidden=runtime.hidden_size,
    )
    generated_text = runtime.tokenizer.decode(
        generated_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False
    )
    reencoded = runtime.tokenizer(
        prompt, return_tensors="pt", add_special_tokens=True
    )
    for key in ("input_ids", "attention_mask"):
        if key not in reencoded or not torch.equal(
            encoded[key].detach().cpu(), reencoded[key].detach().cpu()
        ):
            raise RuntimeError(f"tokenizer {key} changed across the capture")
    redecoded = runtime.tokenizer.decode(
        generated_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False
    )
    if redecoded != generated_text:
        raise RuntimeError("tokenizer generated-text decode changed across the capture")
    runtime.reattest()
    observation = {
        "schema_version": CAPTURE_SCHEMA,
        "status": CAPTURE_STATUS,
        "packet_eligibility": PACKET_ELIGIBILITY,
        "scientific_status": SCIENTIFIC_STATUS,
        "scenario_id": scenario_id,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest().upper(),
        "seed": seed,
        "generation": {
            "method": "manual_greedy_argmax",
            "max_new_tokens": max_new_tokens,
            "temperature": None,
            "sampling": False,
        },
        "capture_contract": {
            "residual": "full_width_last_current_token_for_every_decoder_layer",
            "mlp": "full_width_last_current_token_for_every_decoder_layer",
            "logits": "full_vocabulary_pre_selection_each_generation_step",
            "attention": "NOT_CAPTURED_IN_V1",
            "shapes": {key: list(value.shape) for key, value in arrays.items()},
        },
        "intervention": spec.to_dict(),
        "model_snapshot": runtime.initial_attestation.to_dict(),
        "loaded_weight_value_manifest_sha256": runtime.weight_value_manifest_sha256,
        "tokenizer_canary": dict(runtime.tokenizer_canary),
        "adapter": runtime.adapter.to_receipt_dict(),
        "dependencies": dict(runtime.dependency_versions),
        "runtime": runtime_observation(runtime),
        "claim_boundary": OBSERVATION_CLAIM_BOUNDARY,
    }
    if scenario_source is not None:
        observation["scenario_source"] = dict(scenario_source)
    execution_record = _make_execution_record(
        runtime=runtime,
        observation=observation,
        arrays=arrays,
        generated_text=generated_text,
        residual_hooks=per_step_residual,
        mlp_hooks=per_step_mlp,
        intervention_calls=intervention_calls,
        started_utc=started_utc,
        started_monotonic_ns=started_monotonic_ns,
        ended_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        ended_monotonic_ns=time.monotonic_ns(),
    )
    observation["execution_record"] = execution_record
    return TrajectoryCapture(
        scenario_id=scenario_id,
        prompt=prompt,
        prompt_sha256=observation["prompt_sha256"],
        generated_text=generated_text,
        arrays=arrays,
        observation=observation,
        execution_record=execution_record,
    )


def verify_and_consume_execution_record(
    runtime: LoadedOpenWeightRuntime, capture: TrajectoryCapture
) -> None:
    """Verify one engine-issued capture record and consume its nonce once."""

    if not runtime._persistence_lock.acquire(blocking=False):
        raise RuntimeError("concurrent capture persistence on one runtime is forbidden")
    try:
        _verify_and_consume_execution_record_locked(runtime, capture)
    finally:
        runtime._persistence_lock.release()


def _verify_and_consume_execution_record_locked(
    runtime: LoadedOpenWeightRuntime, capture: TrajectoryCapture
) -> None:
    """Verify and reserve one nonce while the runtime persistence lock is held."""

    record = capture.execution_record
    if not isinstance(record, Mapping) or record != capture.observation.get("execution_record"):
        raise RuntimeError("capture execution record is missing or detached")
    required = {
        "schema_version",
        "execution_nonce",
        "scenario_id",
        "prompt_sha256",
        "generated_text_sha256",
        "intervention",
        "residual_hook_invocations",
        "mlp_hook_invocations",
        "intervention_hook_invocations",
        "array_manifest_sha256",
        "observation_without_execution_record_sha256",
        "model_tree_manifest_sha256",
        "adapter_plan_sha256",
        "runtime_source_manifest_sha256",
        "hook_state_before",
        "hook_state_after",
        "claim_boundary",
        "started_utc",
        "ended_utc",
        "started_monotonic_ns",
        "ended_monotonic_ns",
        "model_forward_calls",
        "execution_hmac_sha256",
    }
    if set(record) != required:
        raise RuntimeError("capture execution record keyset mismatch")
    if record["schema_version"] != "cas_open_weight_engine_execution_record.v1":
        raise RuntimeError("capture execution record schema mismatch")
    nonce = record["execution_nonce"]
    if not isinstance(nonce, str) or len(nonce) != 64 or any(
        character not in "0123456789ABCDEF" for character in nonce
    ):
        raise RuntimeError("capture execution nonce is malformed")
    if nonce in runtime._consumed_execution_nonces:
        raise RuntimeError("capture execution nonce was already consumed")
    started_ns = record.get("started_monotonic_ns")
    ended_ns = record.get("ended_monotonic_ns")
    if (
        isinstance(started_ns, bool)
        or not isinstance(started_ns, int)
        or isinstance(ended_ns, bool)
        or not isinstance(ended_ns, int)
        or ended_ns < started_ns
    ):
        raise RuntimeError("capture execution monotonic chronology is invalid")
    try:
        started_time = datetime.fromisoformat(str(record["started_utc"]).replace("Z", "+00:00"))
        ended_time = datetime.fromisoformat(str(record["ended_utc"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError("capture execution UTC chronology is malformed") from exc
    if started_time.tzinfo != timezone.utc or ended_time.tzinfo != timezone.utc or ended_time < started_time:
        raise RuntimeError("capture execution UTC chronology is invalid")
    unsigned = dict(record)
    signature = unsigned.pop("execution_hmac_sha256")
    expected_signature = hmac.new(
        runtime._execution_hmac_key,
        canonical_json_bytes(unsigned),
        hashlib.sha256,
    ).hexdigest().upper()
    if not isinstance(signature, str) or not hmac.compare_digest(signature, expected_signature):
        raise RuntimeError("capture execution record HMAC mismatch")
    observation_without_record = dict(capture.observation)
    observation_without_record.pop("execution_record", None)
    expected_values = {
        "scenario_id": capture.scenario_id,
        "prompt_sha256": capture.prompt_sha256,
        "generated_text_sha256": hashlib.sha256(
            capture.generated_text.encode("utf-8")
        ).hexdigest().upper(),
        "intervention": observation_without_record.get("intervention"),
        "array_manifest_sha256": _capture_array_manifest_sha256(capture.arrays),
        "observation_without_execution_record_sha256": hashlib.sha256(
            canonical_json_bytes(observation_without_record)
        ).hexdigest().upper(),
        "model_tree_manifest_sha256": runtime.initial_attestation.tree_manifest_sha256,
        "adapter_plan_sha256": runtime.adapter.plan["plan_sha256"],
        "runtime_source_manifest_sha256": hashlib.sha256(
            canonical_json_bytes([dict(row) for row in runtime.runtime_source_manifest])
        ).hexdigest().upper(),
        "hook_state_before": "CLEAN",
        "hook_state_after": "CLEAN",
        "claim_boundary": (
            "Engine-issued one-use local execution record. HMAC key is process-local; "
            "durable authenticity still requires an external result-manifest anchor."
        ),
    }
    for key, expected in expected_values.items():
        if record.get(key) != expected:
            raise RuntimeError(f"capture execution record {key} mismatch")
    steps = int(capture.observation["generation"]["max_new_tokens"])
    layers = runtime.layer_count
    expected_layer_calls = {
        str(step): {str(layer): 1 for layer in range(layers)}
        for step in range(steps)
    }
    if record["residual_hook_invocations"] != expected_layer_calls:
        raise RuntimeError("capture residual hook execution record mismatch")
    if record["mlp_hook_invocations"] != expected_layer_calls:
        raise RuntimeError("capture MLP hook execution record mismatch")
    mode = capture.observation["intervention"]["mode"]
    expected_intervention_calls = {
        str(step): 0 if mode == "baseline" else 1 for step in range(steps)
    }
    if record["intervention_hook_invocations"] != expected_intervention_calls:
        raise RuntimeError("capture intervention hook execution record mismatch")
    if record["model_forward_calls"] != steps:
        raise RuntimeError("capture model forward-call count mismatch")
    runtime._consumed_execution_nonces.add(nonce)


def _make_execution_record(
    *,
    runtime: LoadedOpenWeightRuntime,
    observation: Mapping[str, object],
    arrays: Mapping[str, np.ndarray],
    generated_text: str,
    residual_hooks: Mapping[int, Mapping[int, list[Any]]],
    mlp_hooks: Mapping[int, Mapping[int, list[Any]]],
    intervention_calls: Mapping[int, int],
    started_utc: str,
    started_monotonic_ns: int,
    ended_utc: str,
    ended_monotonic_ns: int,
) -> dict[str, object]:
    steps = int(observation["generation"]["max_new_tokens"])
    unsigned: dict[str, object] = {
        "schema_version": "cas_open_weight_engine_execution_record.v1",
        "execution_nonce": secrets.token_hex(32).upper(),
        "scenario_id": observation["scenario_id"],
        "prompt_sha256": observation["prompt_sha256"],
        "generated_text_sha256": hashlib.sha256(
            generated_text.encode("utf-8")
        ).hexdigest().upper(),
        "intervention": observation["intervention"],
        "residual_hook_invocations": {
            str(step): {
                str(layer): len(residual_hooks.get(step, {}).get(layer, []))
                for layer in range(runtime.layer_count)
            }
            for step in range(steps)
        },
        "mlp_hook_invocations": {
            str(step): {
                str(layer): len(mlp_hooks.get(step, {}).get(layer, []))
                for layer in range(runtime.layer_count)
            }
            for step in range(steps)
        },
        "intervention_hook_invocations": {
            str(step): int(intervention_calls.get(step, 0)) for step in range(steps)
        },
        "array_manifest_sha256": _capture_array_manifest_sha256(arrays),
        "observation_without_execution_record_sha256": hashlib.sha256(
            canonical_json_bytes(observation)
        ).hexdigest().upper(),
        "model_tree_manifest_sha256": runtime.initial_attestation.tree_manifest_sha256,
        "adapter_plan_sha256": runtime.adapter.plan["plan_sha256"],
        "runtime_source_manifest_sha256": hashlib.sha256(
            canonical_json_bytes([dict(row) for row in runtime.runtime_source_manifest])
        ).hexdigest().upper(),
        "hook_state_before": "CLEAN",
        "hook_state_after": "CLEAN",
        "started_utc": started_utc,
        "ended_utc": ended_utc,
        "started_monotonic_ns": started_monotonic_ns,
        "ended_monotonic_ns": ended_monotonic_ns,
        "model_forward_calls": steps,
        "claim_boundary": (
            "Engine-issued one-use local execution record. HMAC key is process-local; "
            "durable authenticity still requires an external result-manifest anchor."
        ),
    }
    record = dict(unsigned)
    record["execution_hmac_sha256"] = hmac.new(
        runtime._execution_hmac_key,
        canonical_json_bytes(unsigned),
        hashlib.sha256,
    ).hexdigest().upper()
    return record


def _capture_array_manifest_sha256(arrays: Mapping[str, np.ndarray]) -> str:
    rows = []
    for name, value in sorted(arrays.items()):
        array = np.ascontiguousarray(value)
        rows.append(
            {
                "name": name,
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "byte_count": int(array.nbytes),
                "value_sha256": hashlib.sha256(
                    array.tobytes(order="C")
                ).hexdigest().upper(),
            }
        )
    return hashlib.sha256(canonical_json_bytes(rows)).hexdigest().upper()


def _tensor_value_row(name: str, tensor: Any, torch: Any) -> dict[str, object]:
    value = tensor.detach().cpu().contiguous()
    raw = value.reshape(-1).view(torch.uint8).numpy().tobytes(order="C")
    return {
        "name": name,
        "shape": [int(item) for item in value.shape],
        "dtype": str(value.dtype).replace("torch.", ""),
        "byte_count": len(raw),
        "value_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def _primary_tensor(output: object) -> Any:
    if hasattr(output, "ndim"):
        return output
    if isinstance(output, (tuple, list)) and output and hasattr(output[0], "ndim"):
        return output[0]
    raise RuntimeError("hook output does not expose a primary tensor")


def _require_exact_hook_state(
    model: Any, *, expected_forward_hook_ids: set[int]
) -> None:
    import torch.nn.modules.module as module_hooks

    global_names = (
        "_global_forward_hooks",
        "_global_forward_pre_hooks",
        "_global_backward_hooks",
        "_global_backward_pre_hooks",
    )
    for name in global_names:
        registry = getattr(module_hooks, name, {})
        if registry:
            raise RuntimeError(f"pre-existing or unexpected global model hook: {name}")
    observed_forward: set[int] = set()
    for module in model.modules():
        forward = getattr(module, "_forward_hooks", {})
        observed_forward.update(int(key) for key in forward)
        for name in ("_forward_pre_hooks", "_backward_hooks", "_backward_pre_hooks"):
            registry = getattr(module, name, {})
            if registry:
                raise RuntimeError(
                    f"pre-existing or unexpected module hook: {name} on {type(module).__name__}"
                )
    if observed_forward != expected_forward_hook_ids:
        raise RuntimeError(
            "model forward-hook ownership mismatch: "
            f"expected={sorted(expected_forward_hook_ids)} "
            f"observed={sorted(observed_forward)}"
        )


def _replace_primary_tensor(output: object, replacement: Any) -> object:
    if hasattr(output, "ndim"):
        return replacement
    if isinstance(output, tuple):
        return (replacement, *output[1:])
    if isinstance(output, list):
        return [replacement, *output[1:]]
    raise RuntimeError("hook output cannot be safely reconstructed")


def _require_exact_hook_rows(
    values: Mapping[int, Mapping[int, list[Any]]],
    step: int,
    layer_count: int,
    label: str,
) -> list[Any]:
    rows = values.get(step, {})
    expected_layers = set(range(layer_count))
    observed_layers = set(rows)
    if observed_layers != expected_layers:
        raise RuntimeError(
            f"{label} hook coverage mismatch at step {step}: "
            f"missing={sorted(expected_layers - observed_layers)} "
            f"extra={sorted(observed_layers - expected_layers)}"
        )
    duplicates = sorted(layer for layer, values_for_layer in rows.items() if len(values_for_layer) != 1)
    if duplicates:
        raise RuntimeError(
            f"{label} hook invocation count mismatch at step {step}, layers={duplicates}"
        )
    return [rows[layer][0] for layer in range(layer_count)]


def _validate_capture_arrays(
    arrays: Mapping[str, np.ndarray], *, steps: int, layers: int, hidden: int
) -> None:
    expected_prefixes = {
        "residual_states": (steps, layers, hidden),
        "mlp_states": (steps, layers, hidden),
        "pre_selection_logits": (steps,),
        "generated_token_ids": (steps,),
        "input_lengths": (steps,),
    }
    for key, prefix in expected_prefixes.items():
        value = arrays[key]
        if value.shape[: len(prefix)] != prefix:
            raise RuntimeError(f"capture array {key} has unexpected shape {value.shape}")
        if value.dtype == object:
            raise RuntimeError(f"capture array {key} must never use object dtype")
        if np.issubdtype(value.dtype, np.floating) and not np.isfinite(value).all():
            raise RuntimeError(f"capture array {key} contains non-finite values")


def _run_tokenizer_canary(tokenizer: Any) -> dict[str, object]:
    text = "CAS byte-attested tokenizer canary: 0, 1, 2."
    encoded = tokenizer(text, add_special_tokens=True)["input_ids"]
    if not isinstance(encoded, list) or not encoded or not all(
        isinstance(value, int) for value in encoded
    ):
        raise RuntimeError("tokenizer canary did not return a non-empty integer sequence")
    decoded = tokenizer.decode(
        encoded, skip_special_tokens=False, clean_up_tokenization_spaces=False
    )
    return {
        "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest().upper(),
        "token_ids": encoded,
        "token_ids_sha256": hashlib.sha256(
            np.asarray(encoded, dtype=np.int64).tobytes(order="C")
        ).hexdigest().upper(),
        "decoded_sha256": hashlib.sha256(decoded.encode("utf-8")).hexdigest().upper(),
    }


def _dependency_versions() -> dict[str, str]:
    values: dict[str, str] = {}
    for name in ("numpy", "safetensors", "torch", "transformers"):
        try:
            values[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            values[name] = "MISSING"
    return values


def runtime_observation(runtime: LoadedOpenWeightRuntime) -> dict[str, object]:
    import torch

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "device": runtime.config.device,
        "dtype_request": runtime.config.dtype,
        "torch_deterministic_algorithms_enabled": bool(
            torch.are_deterministic_algorithms_enabled()
        ),
        "source_manifest": [dict(row) for row in runtime.runtime_source_manifest],
        "python_executable": dict(runtime.python_executable_identity),
        "hardware": dict(runtime.hardware_runtime_identity),
        "callable_manifest": [dict(row) for row in runtime.callable_manifest],
        "tokenizer_callable_manifest": [
            dict(row) for row in runtime.tokenizer_callable_manifest
        ],
        "tokenizer_state_manifest": dict(runtime.tokenizer_state_manifest),
        "module_attribute_manifest": [
            dict(row) for row in runtime.module_attribute_manifest
        ],
        "named_buffer_manifest": [
            dict(row) for row in runtime.named_buffer_manifest
        ],
        "model_config_runtime_manifest": dict(
            runtime.model_config_runtime_manifest
        ),
    }


def _callable_manifest(
    model: Any, adapter: ExecutableAdapterBinding
) -> tuple[Mapping[str, object], ...]:
    dispatch_state = _module_dispatch_state()
    dispatch_raw = canonical_json_bytes(dispatch_state)
    targets: list[tuple[str, Any]] = [
        ("model:<root>" if not name else f"model:{name}", module)
        for name, module in model.named_modules()
    ]
    known_modules = {id(module) for _label, module in targets}
    for path in (*adapter.residual_paths, *adapter.mlp_paths):
        if id(resolve_attr_path(model, path)) not in known_modules:
            raise RuntimeError("adapter hook target is outside the model module tree")
    rows: list[dict[str, object]] = []
    for label, target in targets:
        if "forward" in vars(target):
            raise RuntimeError(f"instance-level forward override is forbidden: {label}")
        bound = getattr(target, "forward", None)
        class_forward = getattr(type(target), "forward", None)
        function = getattr(bound, "__func__", None)
        if function is not class_forward:
            raise RuntimeError(f"forward callable is not class-bound: {label}")
        code = getattr(function, "__code__", None)
        if code is None:
            raise RuntimeError(f"forward callable has no auditable Python code: {label}")
        semantic = _runtime_value_identity(
            function, introspect_object_state=True
        )
        if not isinstance(semantic, Mapping):
            raise RuntimeError(f"forward callable semantic identity is invalid: {label}")
        class_state = _class_referenced_state(
            type(target), set(code.co_names) | set(_MODULE_DISPATCH_NAMES)
        )
        class_state_raw = canonical_json_bytes(class_state)
        row = {
                "label": label,
                "class_module": type(target).__module__,
                "class_qualname": type(target).__qualname__,
                "forward_module": function.__module__,
                "forward_qualname": function.__qualname__,
                "forward_object_id": id(function),
                "forward_code_sha256": hashlib.sha256(
                    marshal.dumps(code)
                ).hexdigest().upper(),
                "semantic_state_byte_count": semantic["semantic_state_byte_count"],
                "semantic_state_sha256": semantic["semantic_state_sha256"],
                "referenced_class_state_byte_count": len(class_state_raw),
                "referenced_class_state_sha256": hashlib.sha256(
                    class_state_raw
                ).hexdigest().upper(),
            }
        if label == "model:<root>":
            row["module_dispatch_state_byte_count"] = len(dispatch_raw)
            row["module_dispatch_state_sha256"] = hashlib.sha256(
                dispatch_raw
            ).hexdigest().upper()
        rows.append(row)
    return tuple(rows)


def _callable_identity_objects(model: Any) -> tuple[Any, ...]:
    """Hold strong references to every behavior-bearing class callable."""

    objects: list[Any] = []
    for _name, module in model.named_modules():
        function = getattr(type(module), "forward", None)
        objects.append(function)
        code = getattr(function, "__code__", None)
        if code is not None:
            objects.extend(
                value
                for _owner, _name, value in _class_referenced_objects(
                    type(module), set(code.co_names) | set(_MODULE_DISPATCH_NAMES)
                )
            )
    objects.extend(value for _name, value in _module_dispatch_objects())
    return tuple(objects)


_MODULE_DISPATCH_NAMES = (
    "__call__",
    "_wrapped_call_impl",
    "_call_impl",
    "__getattr__",
    "__getattribute__",
    "state_dict",
    "named_modules",
    "named_buffers",
    "register_forward_hook",
)


def _descriptor_function(value: Any) -> Any:
    if isinstance(value, (staticmethod, classmethod)):
        return value.__func__
    return value


def _class_referenced_objects(
    target_type: type[Any], names: set[str]
) -> tuple[tuple[type[Any], str, Any], ...]:
    rows: list[tuple[type[Any], str, Any]] = []
    pending = list(sorted(names))
    seen: set[tuple[type[Any], str]] = set()
    while pending:
        name = pending.pop(0)
        for owner in target_type.__mro__:
            if name in vars(owner):
                key = (owner, name)
                if key in seen:
                    break
                seen.add(key)
                value = _descriptor_function(vars(owner)[name])
                rows.append((owner, name, value))
                code = getattr(value, "__code__", None)
                if code is not None:
                    for referenced_name in sorted(set(code.co_names)):
                        if referenced_name not in pending and any(
                            referenced_name in vars(candidate)
                            for candidate in target_type.__mro__
                        ):
                            pending.append(referenced_name)
                break
        if len(rows) > 256:
            raise RuntimeError("class behavior surface exceeds the bounded audit limit")
    return tuple(rows)


def _class_referenced_state(
    target_type: type[Any], names: set[str]
) -> tuple[Mapping[str, object], ...]:
    return tuple(
        {
            "name": name,
            "owner_module": owner.__module__,
            "owner_qualname": owner.__qualname__,
            "value": (
                _direct_callable_identity(value)
                if inspect.isfunction(value)
                or inspect.ismethoddescriptor(value)
                or inspect.isbuiltin(value)
                else _runtime_value_identity(value, introspect_object_state=True)
            ),
        }
        for owner, name, value in _class_referenced_objects(target_type, names)
    )


def _module_dispatch_objects() -> tuple[tuple[str, Any], ...]:
    import torch

    module_type = torch.nn.Module
    module_rows = _class_referenced_objects(
        module_type, set(_MODULE_DISPATCH_NAMES)
    )
    rows = [
        (f"{owner.__module__}.{owner.__qualname__}.{name}", value)
        for owner, name, value in module_rows
    ]
    observed_seed_names = {name for _owner, name, _value in module_rows}
    rows.extend(
        (
            ("RemovableHandle.__init__", torch.utils.hooks.RemovableHandle.__init__),
            ("RemovableHandle.remove", torch.utils.hooks.RemovableHandle.remove),
        )
    )
    if not set(_MODULE_DISPATCH_NAMES).issubset(observed_seed_names):
        raise RuntimeError("PyTorch module dispatch surface is incomplete")
    return tuple(rows)


def _module_dispatch_state() -> tuple[Mapping[str, object], ...]:
    return tuple(
        {
            "name": name,
            "identity": _direct_callable_identity(value),
        }
        for name, value in _module_dispatch_objects()
    )


def _direct_callable_identity(value: Any) -> Mapping[str, object]:
    code = getattr(value, "__code__", None)
    return {
        "class_module": type(value).__module__,
        "class_qualname": type(value).__qualname__,
        "callable_module": getattr(value, "__module__", None),
        "callable_qualname": getattr(value, "__qualname__", None),
        "object_id": id(value),
        "code_sha256": (
            hashlib.sha256(marshal.dumps(code)).hexdigest().upper()
            if code is not None
            else None
        ),
    }


_MODULE_RUNTIME_REGISTRY_KEYS = frozenset(
    {
        "_parameters",
        "_buffers",
        "_non_persistent_buffers_set",
        "_backward_pre_hooks",
        "_backward_hooks",
        "_is_full_backward_hook",
        "_forward_hooks",
        "_forward_hooks_with_kwargs",
        "_forward_hooks_always_called",
        "_forward_pre_hooks",
        "_forward_pre_hooks_with_kwargs",
        "_state_dict_hooks",
        "_state_dict_pre_hooks",
        "_load_state_dict_pre_hooks",
        "_load_state_dict_post_hooks",
        "_modules",
        "_compiled_call_impl",
    }
)


def _module_attribute_manifest(model: Any) -> tuple[Mapping[str, object], ...]:
    """Bind non-state module settings that can alter a forward pass."""

    rows: list[dict[str, object]] = []
    for name, module in model.named_modules():
        if getattr(module, "_compiled_call_impl", None) is not None:
            raise RuntimeError(
                "compiled module call overrides are forbidden: "
                f"{'<root>' if not name else name}"
            )
        attributes = {
            key: _runtime_value_identity(value, introspect_object_state=True)
            for key, value in sorted(vars(module).items())
            if key not in _MODULE_RUNTIME_REGISTRY_KEYS
        }
        attributes_raw = canonical_json_bytes(attributes)
        rows.append(
            {
                "module_path": name,
                "class_module": type(module).__module__,
                "class_qualname": type(module).__qualname__,
                "attribute_count": len(attributes),
                "attributes_byte_count": len(attributes_raw),
                "attributes_sha256": hashlib.sha256(
                    attributes_raw
                ).hexdigest().upper(),
            }
        )
    return tuple(rows)


def _named_buffer_manifest(model: Any) -> tuple[Mapping[str, object], ...]:
    """Hash every persistent and nonpersistent named model buffer."""

    import torch

    rows = [
        _tensor_value_row(name, value, torch)
        for name, value in sorted(model.named_buffers(), key=lambda item: item[0])
    ]
    return tuple(rows)


def _model_config_runtime_manifest(model: Any) -> Mapping[str, object]:
    """Bind the complete resolved runtime config, including private dispatch state."""

    config = model.config
    to_dict = getattr(config, "to_dict", None)
    normalized = to_dict() if callable(to_dict) else dict(vars(config))
    payload = {
        "config_class_module": type(config).__module__,
        "config_class_qualname": type(config).__qualname__,
        "normalized": _runtime_value_identity(normalized),
        "attn_implementation": _runtime_value_identity(
            getattr(config, "_attn_implementation", None)
        ),
        "attn_implementation_internal": _runtime_value_identity(
            getattr(config, "_attn_implementation_internal", None)
        ),
        "rope_parameters": _runtime_value_identity(
            getattr(config, "rope_parameters", None)
        ),
    }
    raw = canonical_json_bytes(payload)
    return {
        "schema_version": "cas_loaded_model_runtime_config_manifest.v1",
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "payload": payload,
    }


def _runtime_value_identity(
    value: Any,
    *,
    depth: int = 0,
    introspect_object_state: bool = False,
    _seen: set[int] | None = None,
) -> object:
    """Return a bounded process-local identity for behavior-affecting values."""

    if _seen is None:
        _seen = set()
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RuntimeError("non-finite module runtime attribute is forbidden")
        return {"kind": "float", "hex": value.hex()}
    if isinstance(value, bytes):
        return {
            "kind": "bytes",
            "byte_count": len(value),
            "sha256": hashlib.sha256(value).hexdigest().upper(),
        }
    if depth > 2 and inspect.isfunction(value):
        return {
            "kind": "depth_limited_python_function",
            "module": value.__module__,
            "qualname": value.__qualname__,
            "object_id": id(value),
            "code_sha256": hashlib.sha256(
                marshal.dumps(value.__code__)
            ).hexdigest().upper(),
        }
    if depth > 4:
        return {
            "kind": "depth_limited_object",
            "class_module": type(value).__module__,
            "class_qualname": type(value).__qualname__,
            "object_id": id(value),
        }
    if depth > 2 and isinstance(value, (tuple, list)):
        return {
            "kind": (
                "depth_limited_tuple" if isinstance(value, tuple) else "depth_limited_list"
            ),
            "items": [
                _runtime_value_identity(
                    item,
                    depth=depth + 1,
                    introspect_object_state=False,
                    _seen=_seen,
                )
                for item in value
            ],
        }
    if depth > 2 and isinstance(value, Mapping):
        return {
            "kind": "depth_limited_mapping",
            "items": [
                {
                    "key": _runtime_value_identity(
                        key,
                        depth=depth + 1,
                        introspect_object_state=False,
                        _seen=_seen,
                    ),
                    "value": _runtime_value_identity(
                        item,
                        depth=depth + 1,
                        introspect_object_state=False,
                        _seen=_seen,
                    ),
                }
                for key, item in sorted(
                    value.items(), key=lambda item: repr(item[0])
                )
            ],
        }
    if depth > 2:
        return {
            "kind": "depth_limited_object",
            "class_module": type(value).__module__,
            "class_qualname": type(value).__qualname__,
            "object_id": id(value),
        }
    if isinstance(value, (tuple, list)):
        if len(value) > 1024:
            digest = hashlib.sha256()
            for item in value:
                digest.update(
                    canonical_json_bytes(
                        _runtime_value_identity(
                            item,
                            depth=depth + 1,
                            introspect_object_state=introspect_object_state,
                            _seen=_seen,
                        )
                    )
                )
            return {
                "kind": "large_tuple_digest" if isinstance(value, tuple) else "large_list_digest",
                "item_count": len(value),
                "items_sha256": digest.hexdigest().upper(),
            }
        return {
            "kind": "tuple" if isinstance(value, tuple) else "list",
            "items": [
                _runtime_value_identity(
                    item,
                    depth=depth + 1,
                    introspect_object_state=introspect_object_state,
                    _seen=_seen,
                )
                for item in value
            ],
        }
    if isinstance(value, Mapping):
        if len(value) > 1024:
            encoded_items = [
                canonical_json_bytes(
                    {
                        "key": _runtime_value_identity(
                            key,
                            depth=depth + 1,
                            introspect_object_state=introspect_object_state,
                            _seen=_seen,
                        ),
                        "value": _runtime_value_identity(
                            item,
                            depth=depth + 1,
                            introspect_object_state=introspect_object_state,
                            _seen=_seen,
                        ),
                    }
                )
                for key, item in value.items()
            ]
            encoded_items.sort()
            digest = hashlib.sha256()
            for encoded in encoded_items:
                digest.update(encoded)
            return {
                "kind": "large_mapping_digest",
                "item_count": len(value),
                "items_sha256": digest.hexdigest().upper(),
            }
        if not all(isinstance(key, str) for key in value):
            items = [
                {
                    "key": _runtime_value_identity(
                        key,
                        depth=depth + 1,
                        introspect_object_state=introspect_object_state,
                        _seen=_seen,
                    ),
                    "value": _runtime_value_identity(
                        item,
                        depth=depth + 1,
                        introspect_object_state=introspect_object_state,
                        _seen=_seen,
                    ),
                }
                for key, item in value.items()
            ]
            items.sort(key=canonical_json_bytes)
            return {"kind": "mapping_items", "items": items}
        return {
            "kind": "mapping",
            "items": {
                key: _runtime_value_identity(
                    value[key],
                    depth=depth + 1,
                    introspect_object_state=introspect_object_state,
                    _seen=_seen,
                )
                for key in sorted(value)
            },
        }
    if isinstance(value, types.ModuleType):
        return {
            "kind": "module",
            "name": value.__name__,
            "object_id": id(value),
        }
    if inspect.isfunction(value):
        code = value.__code__
        value_id = id(value)
        base = {
            "kind": "python_function",
            "module": value.__module__,
            "qualname": value.__qualname__,
            "object_id": value_id,
            "code_sha256": hashlib.sha256(marshal.dumps(code)).hexdigest().upper(),
        }
        if value_id in _seen:
            return {**base, "semantic_state": "CYCLE_REFERENCE"}
        _seen.add(value_id)
        try:
            semantic_state = {
                "defaults": _runtime_value_identity(
                    value.__defaults__,
                    depth=depth + 1,
                    introspect_object_state=True,
                    _seen=_seen,
                ),
                "keyword_defaults": _runtime_value_identity(
                    value.__kwdefaults__,
                    depth=depth + 1,
                    introspect_object_state=True,
                    _seen=_seen,
                ),
                "closure": _runtime_value_identity(
                    tuple(
                        cell.cell_contents
                        for cell in (value.__closure__ or ())
                    ),
                    depth=depth + 1,
                    introspect_object_state=True,
                    _seen=_seen,
                ),
                "referenced_globals": {
                    name: _referenced_global_identity(
                        value.__globals__[name],
                        set(code.co_names),
                        depth=depth + 1,
                        _seen=_seen,
                    )
                    for name in sorted(set(code.co_names))
                    if name.isidentifier() and name in value.__globals__
                },
            }
            semantic_raw = canonical_json_bytes(semantic_state)
            return {
                **base,
                "semantic_state_byte_count": len(semantic_raw),
                "semantic_state_sha256": hashlib.sha256(
                    semantic_raw
                ).hexdigest().upper(),
            }
        finally:
            _seen.remove(value_id)
    try:
        import torch
    except Exception:  # pragma: no cover - torch is a declared runtime dependency
        torch = None
    if torch is not None and isinstance(value, torch.Tensor):
        try:
            row = _tensor_value_row("module_runtime_attribute", value, torch)
            return {"kind": "tensor", **row}
        except Exception as exc:
            raise RuntimeError("module runtime tensor attribute cannot be attested") from exc
    if introspect_object_state and _declared_slot_names(type(value)):
        value_id = id(value)
        if value_id in _seen:
            return {
                "kind": "slotted_object_cycle",
                "class_module": type(value).__module__,
                "class_qualname": type(value).__qualname__,
                "object_id": value_id,
            }
        _seen.add(value_id)
        try:
            slot_values = {
                label: _runtime_value_identity(
                    getattr(value, attribute_name),
                    depth=depth + 1,
                    introspect_object_state=True,
                    _seen=_seen,
                )
                for label, attribute_name in _declared_slot_names(type(value))
                if hasattr(value, attribute_name)
            }
            type_call = None
            class_state: object = ()
            if callable(value):
                raw_call = _descriptor_function(vars(type(value)).get("__call__"))
                if raw_call is not None:
                    type_call = _runtime_value_identity(
                        raw_call,
                        depth=depth + 1,
                        introspect_object_state=True,
                        _seen=_seen,
                    )
                    code = getattr(raw_call, "__code__", None)
                    if code is not None:
                        class_state = _class_referenced_state(
                            type(value), set(code.co_names)
                        )
        finally:
            _seen.remove(value_id)
        state_raw = canonical_json_bytes(
            {
                "slot_values": slot_values,
                "type_call": type_call,
                "referenced_class_state": class_state,
            }
        )
        return {
            "kind": "slotted_stateful_object",
            "class_module": type(value).__module__,
            "class_qualname": type(value).__qualname__,
            "object_id": value_id,
            "state_byte_count": len(state_raw),
            "state_sha256": hashlib.sha256(state_raw).hexdigest().upper(),
        }
    if introspect_object_state and hasattr(value, "__dict__"):
        value_id = id(value)
        if value_id in _seen:
            return {
                "kind": "object_cycle",
                "class_module": type(value).__module__,
                "class_qualname": type(value).__qualname__,
                "object_id": value_id,
            }
        _seen.add(value_id)
        try:
            attributes = {
                key: _runtime_value_identity(
                    item,
                    depth=depth + 1,
                    introspect_object_state=True,
                    _seen=_seen,
                )
                for key, item in sorted(vars(value).items())
            }
            class_state = {
                key: _runtime_value_identity(
                    getattr(type(value), key),
                    depth=depth + 1,
                    introspect_object_state=True,
                    _seen=_seen,
                )
                for key in ("_global_mapping",)
                if hasattr(type(value), key)
            }
        finally:
            _seen.remove(value_id)
        state_raw = canonical_json_bytes(
            {"attributes": attributes, "class_state": class_state}
        )
        return {
            "kind": "stateful_object",
            "class_module": type(value).__module__,
            "class_qualname": type(value).__qualname__,
            "object_id": value_id,
            "state_byte_count": len(state_raw),
            "state_sha256": hashlib.sha256(state_raw).hexdigest().upper(),
        }
    return {
        "kind": "object_identity",
        "class_module": type(value).__module__,
        "class_qualname": type(value).__qualname__,
        "object_id": id(value),
    }


def _declared_slot_names(target_type: type[Any]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for owner in target_type.__mro__:
        raw_slots = vars(owner).get("__slots__", ())
        if isinstance(raw_slots, str):
            raw_slots = (raw_slots,)
        for slot in raw_slots:
            if not isinstance(slot, str) or slot in {"__dict__", "__weakref__"}:
                continue
            attribute_name = slot
            if slot.startswith("__") and not slot.endswith("__"):
                attribute_name = f"_{owner.__name__.lstrip('_')}{slot}"
            rows.append((f"{owner.__module__}.{owner.__qualname__}:{slot}", attribute_name))
    rows.sort()
    return tuple(rows)


def _referenced_global_identity(
    value: Any,
    names: set[str],
    *,
    depth: int = 0,
    _seen: set[int] | None = None,
) -> object:
    """Bind a referenced global and same-code module attributes it may dispatch."""

    if _seen is None:
        _seen = set()
    if not isinstance(value, types.ModuleType):
        identity = _runtime_value_identity(
            value,
            depth=depth,
            introspect_object_state=True,
            _seen=_seen,
        )
        class_state = _class_referenced_state(type(value), names)
        class_state_raw = canonical_json_bytes(class_state)
        return {
            "kind": "referenced_global_object",
            "identity": identity,
            "referenced_class_state_byte_count": len(class_state_raw),
            "referenced_class_state_sha256": hashlib.sha256(
                class_state_raw
            ).hexdigest().upper(),
        }
    return _referenced_module_identity(value, names, depth=depth, _seen=_seen)


def _referenced_module_identity(
    module: types.ModuleType,
    names: set[str],
    *,
    depth: int,
    _seen: set[int] | None = None,
) -> object:
    if _seen is None:
        _seen = set()
    module_id = id(module)
    if module_id in _seen:
        return {
            "kind": "referenced_module_cycle",
            "name": module.__name__,
            "object_id": module_id,
        }
    _seen.add(module_id)
    attributes: dict[str, object] = {}
    try:
        if depth < 3:
            for name in sorted(names):
                if not hasattr(module, name):
                    continue
                item = getattr(module, name)
                if isinstance(item, types.ModuleType):
                    attributes[name] = _referenced_module_identity(
                        item,
                        names,
                        depth=depth + 1,
                        _seen=_seen,
                    )
                else:
                    attributes[name] = _runtime_value_identity(
                        item,
                        depth=depth + 1,
                        introspect_object_state=True,
                        _seen=_seen,
                    )
        return {
            "kind": "referenced_module",
            "name": module.__name__,
            "object_id": module_id,
            "attributes": attributes,
        }
    finally:
        _seen.remove(module_id)


def _tokenizer_state_manifest(tokenizer: Any) -> Mapping[str, object]:
    """Bind tokenizer Python state and serialized native backend behavior."""

    backend = getattr(tokenizer, "backend_tokenizer", None)
    if backend is None:
        backend = getattr(tokenizer, "_tokenizer", None)
    backend_row: object = None
    if backend is not None:
        to_str = getattr(backend, "to_str", None)
        if callable(to_str):
            raw = to_str().encode("utf-8", errors="strict")
            backend_row = {
                "class_module": type(backend).__module__,
                "class_qualname": type(backend).__qualname__,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest().upper(),
            }
        else:
            backend_row = _runtime_value_identity(backend)
    payload = {
        "tokenizer_class_module": type(tokenizer).__module__,
        "tokenizer_class_qualname": type(tokenizer).__qualname__,
        "python_attributes": _runtime_value_identity(dict(vars(tokenizer))),
        "native_backend": backend_row,
    }
    raw = canonical_json_bytes(payload)
    return {
        "schema_version": "cas_tokenizer_behavioral_state_manifest.v1",
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "payload": payload,
    }


def _tokenizer_callable_manifest(tokenizer: Any) -> tuple[Mapping[str, object], ...]:
    rows: list[dict[str, object]] = []
    for name in ("__call__", "decode"):
        if name in vars(tokenizer):
            raise RuntimeError(f"instance-level tokenizer {name} override is forbidden")
        bound = getattr(tokenizer, name, None)
        class_callable = getattr(type(tokenizer), name, None)
        function = getattr(bound, "__func__", None)
        if function is not class_callable:
            raise RuntimeError(f"tokenizer {name} callable is not class-bound")
        code = getattr(function, "__code__", None)
        if code is None:
            raise RuntimeError(f"tokenizer {name} has no auditable Python code")
        semantic = _runtime_value_identity(
            function, introspect_object_state=True
        )
        if not isinstance(semantic, Mapping):
            raise RuntimeError(f"tokenizer {name} semantic identity is invalid")
        class_state = _class_referenced_state(type(tokenizer), set(code.co_names))
        class_state_raw = canonical_json_bytes(class_state)
        rows.append(
            {
                "name": name,
                "class_module": type(tokenizer).__module__,
                "class_qualname": type(tokenizer).__qualname__,
                "callable_module": function.__module__,
                "callable_qualname": function.__qualname__,
                "callable_object_id": id(function),
                "code_sha256": hashlib.sha256(marshal.dumps(code)).hexdigest().upper(),
                "semantic_state_byte_count": semantic["semantic_state_byte_count"],
                "semantic_state_sha256": semantic["semantic_state_sha256"],
                "referenced_class_state_byte_count": len(class_state_raw),
                "referenced_class_state_sha256": hashlib.sha256(
                    class_state_raw
                ).hexdigest().upper(),
            }
        )
    return tuple(rows)


def _tokenizer_callable_identity_objects(tokenizer: Any) -> tuple[Any, ...]:
    """Hold strong references to the exact class-bound tokenizer callables."""

    objects: list[Any] = []
    for name in ("__call__", "decode"):
        function = getattr(type(tokenizer), name, None)
        objects.append(function)
        code = getattr(function, "__code__", None)
        if code is not None:
            objects.extend(
                value
                for _owner, _name, value in _class_referenced_objects(
                    type(tokenizer), set(code.co_names)
                )
            )
    return tuple(objects)


def _runtime_source_manifest(
    config: RuntimeLoadConfig, model: Any, tokenizer: Any
) -> tuple[Mapping[str, object], ...]:
    source_directory = Path(__file__).resolve().parent
    paths: list[Path] = [
        source_directory / "contracts.py",
        source_directory / "identity.py",
        source_directory / "adapter_binding.py",
        source_directory / "engine.py",
        source_directory / "artifacts.py",
        config.adapter_source_path,
        config.entrypoint_source_path,
    ]
    for module_name in (
        "numpy",
        "safetensors",
        "safetensors._safetensors_rust",
        "torch",
        "torch._C",
        "transformers",
        "tokenizers",
        "tokenizers.tokenizers",
    ):
        module = importlib.import_module(module_name)
        module_file = getattr(module, "__file__", None)
        if isinstance(module_file, str):
            paths.append(Path(module_file).resolve())
    for value in (type(model), type(tokenizer)):
        source = inspect.getsourcefile(value)
        if source is not None:
            paths.append(Path(source).resolve())
    if getattr(model, "gpt_neox", None) is not None and len(model.gpt_neox.layers):
        source = inspect.getsourcefile(type(model.gpt_neox.layers[0]))
        if source is not None:
            paths.append(Path(source).resolve())
    unique_paths = {
        str(path).casefold(): path for path in paths
    }
    rows = [_file_identity(path) for path in unique_paths.values()]
    rows.sort(key=lambda row: str(row["path"]).encode("utf-8"))
    return tuple(rows)


def _file_identity(path: Path) -> dict[str, object]:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise RuntimeError(f"runtime identity path must be a plain absolute file: {path}")
    raw = path.read_bytes()
    if not raw:
        raise RuntimeError(f"runtime identity file must not be empty: {path}")
    return {
        "path": str(path),
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def _hardware_runtime_identity(torch: Any, device: str) -> dict[str, object]:
    cuda_available = bool(torch.cuda.is_available())
    row: dict[str, object] = {
        "requested_device": device,
        "cuda_available": cuda_available,
        "torch_cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version() if cuda_available else None,
        "device_name": None,
        "device_capability": None,
    }
    if device.startswith("cuda:"):
        index = int(device.split(":", 1)[1])
        row["device_name"] = torch.cuda.get_device_name(index)
        row["device_capability"] = list(torch.cuda.get_device_capability(index))
    return row


def _require_available_memory(minimum_bytes: int, *, phase: str) -> None:
    if minimum_bytes == 0:
        return
    observed = _available_memory_bytes()
    if observed < minimum_bytes:
        raise RuntimeError(
            f"{phase} available-memory floor failed: "
            f"observed={observed} required={minimum_bytes}"
        )


def _available_memory_bytes() -> int:
    if os.name == "nt":
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("GlobalMemoryStatusEx failed")
        return int(status.ullAvailPhys)
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                fields = line.split()
                if len(fields) == 3 and fields[2] == "kB":
                    return int(fields[1]) * 1024
    page_size = int(os.sysconf("SC_PAGE_SIZE"))
    available_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
    return page_size * available_pages


def _resolve_dtype(torch: Any, value: str) -> Any:
    if value != "auto":  # pragma: no cover - guarded by RuntimeLoadConfig
        raise ValueError("only exact source dtype loading is admitted")
    return "auto"


@contextmanager
def _offline_environment() -> Iterable[None]:
    keys = {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
    }
    prior = {key: os.environ.get(key) for key in keys}
    os.environ.update(keys)
    try:
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
