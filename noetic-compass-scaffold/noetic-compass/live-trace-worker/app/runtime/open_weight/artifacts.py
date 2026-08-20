"""Create-once persistence and verification for trajectory capture artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping

import numpy as np

from .adapter_binding import (
    verify_attested_config_projection,
    verify_bound_adapter_plan,
)
from .contracts import (
    ADAPTER_BINDING_STATUS,
    ADAPTER_CLAIM_BOUNDARY,
    CAPTURE_SCHEMA,
    CAPTURE_STATUS,
    OBSERVATION_CLAIM_BOUNDARY,
    PACKET_ELIGIBILITY,
    RECEIPT_CLAIM_BOUNDARY,
    RECEIPT_SCHEMA,
    SCIENTIFIC_STATUS,
    TENSOR_SCHEMA,
)
from .engine import (
    LoadedOpenWeightRuntime,
    TrajectoryCapture,
    verify_and_consume_execution_record,
)
from .identity import (
    LocalModelSnapshot,
    SnapshotAttestation,
    attest_local_snapshot,
    canonical_json_bytes,
    require_same_attestation,
)


_ARRAY_NAMES = frozenset(
    {
        "prompt_input_ids",
        "prompt_attention_mask",
        "generated_token_ids",
        "input_lengths",
        "residual_states",
        "mlp_states",
        "pre_selection_logits",
    }
)


@dataclass(frozen=True)
class CaptureVerificationContext:
    """Externally supplied trust roots for one receipt verification."""

    model_snapshot: LocalModelSnapshot
    model_attestation: SnapshotAttestation
    adapter_source_path: Path
    adapter_source_sha256: str
    adapter_plan_file_sha256: str
    adapter_plan_sha256: str
    adapter_binding: Mapping[str, object]
    runtime_source_manifest: tuple[Mapping[str, object], ...]
    python_executable_identity: Mapping[str, object]
    loaded_weight_value_manifest_sha256: str
    tokenizer_canary: Mapping[str, object]
    dependency_versions: Mapping[str, str]
    runtime_observation: Mapping[str, object]
    generated_text: str
    array_manifest: tuple[Mapping[str, object], ...]
    execution_record: Mapping[str, object]
    scenario_id: str
    prompt: str
    seed: int
    max_new_tokens: int
    intervention: Mapping[str, object]
    scenario_source: Mapping[str, object] | None

    @classmethod
    def from_runtime_capture(
        cls, runtime: LoadedOpenWeightRuntime, capture: TrajectoryCapture
    ) -> "CaptureVerificationContext":
        source = capture.observation.get("scenario_source")
        return cls(
            model_snapshot=runtime.config.snapshot,
            model_attestation=runtime.initial_attestation,
            adapter_source_path=runtime.config.adapter_source_path,
            adapter_source_sha256=runtime.adapter.adapter_source_sha256,
            adapter_plan_file_sha256=runtime.adapter.plan_file_sha256,
            adapter_plan_sha256=str(runtime.adapter.plan["plan_sha256"]),
            adapter_binding=runtime.adapter.to_receipt_dict(),
            runtime_source_manifest=runtime.runtime_source_manifest,
            python_executable_identity=runtime.python_executable_identity,
            loaded_weight_value_manifest_sha256=runtime.weight_value_manifest_sha256,
            tokenizer_canary=runtime.tokenizer_canary,
            dependency_versions=runtime.dependency_versions,
            runtime_observation=_required_mapping(capture.observation, "runtime"),
            generated_text=capture.generated_text,
            array_manifest=tuple(_array_manifest(capture.arrays)),
            execution_record=capture.execution_record,
            scenario_id=capture.scenario_id,
            prompt=capture.prompt,
            seed=_required_int(capture.observation, "seed"),
            max_new_tokens=_required_int(
                _required_mapping(capture.observation, "generation"),
                "max_new_tokens",
            ),
            intervention=_required_mapping(capture.observation, "intervention"),
            scenario_source=source if isinstance(source, Mapping) else None,
        )


def persist_capture_create_new(
    *,
    runtime: LoadedOpenWeightRuntime,
    capture: TrajectoryCapture,
    output_directory: Path,
    artifact_stem: str,
) -> dict[str, object]:
    """Persist safetensors, adapter plan, and receipt without overwriting."""

    if not runtime._capture_lock.acquire(blocking=False):
        raise RuntimeError("capture and persistence may not overlap on one runtime")
    try:
        if not runtime._persistence_lock.acquire(blocking=False):
            raise RuntimeError("concurrent capture persistence on one runtime is forbidden")
        try:
            return _persist_capture_create_new_locked(
                runtime=runtime,
                capture=capture,
                output_directory=output_directory,
                artifact_stem=artifact_stem,
            )
        finally:
            runtime._persistence_lock.release()
    finally:
        runtime._capture_lock.release()


def _persist_capture_create_new_locked(
    *,
    runtime: LoadedOpenWeightRuntime,
    capture: TrajectoryCapture,
    output_directory: Path,
    artifact_stem: str,
) -> dict[str, object]:
    """Persist one private capture snapshot while holding the persistence lock."""

    if not output_directory.is_absolute() or not output_directory.is_dir():
        raise ValueError("output_directory must be an existing absolute directory")
    if output_directory.is_symlink() or _is_reparse(output_directory.lstat()):
        raise ValueError("output_directory must be a plain directory")
    if not artifact_stem or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in artifact_stem
    ):
        raise ValueError("artifact_stem must use only ASCII letters, digits, dash, underscore")
    tensor_path = output_directory / f"{artifact_stem}.safetensors"
    plan_path = output_directory / f"{artifact_stem}.adapter-plan.json"
    receipt_path = output_directory / f"{artifact_stem}.receipt.json"
    for path in (tensor_path, plan_path, receipt_path):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"capture output already exists: {path}")
    capture = _snapshot_capture_for_persistence(capture)
    runtime.reattest()
    verify_and_consume_execution_record(runtime, capture)
    mode = _required_mapping(capture.observation, "intervention").get("mode")
    if mode not in {"baseline", "noop", "zero"}:
        raise ValueError("v1 persistence admits only baseline/noop/zero interventions")

    try:
        from safetensors.numpy import save
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(f"safetensors numpy writer unavailable: {exc}") from exc
    arrays = {
        name: np.ascontiguousarray(value)
        for name, value in capture.arrays.items()
    }
    metadata = {
        "schema_version": TENSOR_SCHEMA,
        "scenario_id": capture.scenario_id,
        "prompt_sha256": capture.prompt_sha256,
        "model_tree_manifest_sha256": runtime.initial_attestation.tree_manifest_sha256,
        "loaded_weight_value_manifest_sha256": runtime.weight_value_manifest_sha256,
        "adapter_plan_sha256": str(runtime.adapter.plan["plan_sha256"]),
        "packet_eligibility": PACKET_ELIGIBILITY,
    }
    tensor_bytes = save(arrays, metadata=metadata)
    _write_create_new(tensor_path, tensor_bytes)
    _write_create_new(plan_path, runtime.adapter.plan_bytes)

    array_manifest = _array_manifest(arrays)
    array_manifest_sha256 = hashlib.sha256(
        canonical_json_bytes(array_manifest)
    ).hexdigest().upper()
    if capture.execution_record.get("array_manifest_sha256") != array_manifest_sha256:
        raise RuntimeError("serialized array manifest differs from the engine execution record")
    unsigned = {
        "schema_version": RECEIPT_SCHEMA,
        "status": CAPTURE_STATUS,
        "packet_eligibility": PACKET_ELIGIBILITY,
        "scientific_status": SCIENTIFIC_STATUS,
        "input": {
            "scenario_id": capture.scenario_id,
            "prompt": capture.prompt,
            "prompt_sha256": capture.prompt_sha256,
        },
        "output": {
            "generated_text": capture.generated_text,
            "tensor_path": tensor_path.name,
            "tensor_byte_count": len(tensor_bytes),
            "tensor_sha256": hashlib.sha256(tensor_bytes).hexdigest().upper(),
            "adapter_plan_path": plan_path.name,
            "adapter_plan_byte_count": len(runtime.adapter.plan_bytes),
            "adapter_plan_file_sha256": runtime.adapter.plan_file_sha256,
            "array_manifest": array_manifest,
        },
        "observation": dict(capture.observation),
        "claim_boundary": RECEIPT_CLAIM_BOUNDARY,
    }
    receipt_hash = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest().upper()
    receipt = dict(unsigned)
    receipt["receipt_sha256"] = receipt_hash
    _write_create_new(receipt_path, canonical_json_bytes(receipt))
    verified = verify_capture_receipt(
        receipt_path,
        context=CaptureVerificationContext.from_runtime_capture(runtime, capture),
    )
    runtime.reattest()
    return verified


def _snapshot_capture_for_persistence(capture: TrajectoryCapture) -> TrajectoryCapture:
    """Deep-copy caller-visible capture data before verification or serialization."""

    if set(capture.arrays) != _ARRAY_NAMES:
        raise RuntimeError("capture array keyset mismatch before persistence")
    arrays: dict[str, np.ndarray] = {}
    for name, value in capture.arrays.items():
        if not isinstance(value, np.ndarray):
            raise RuntimeError(f"capture array {name} is not a NumPy array")
        private = np.array(value, copy=True, order="C")
        private.setflags(write=False)
        arrays[name] = private
    observation = _strict_json(canonical_json_bytes(capture.observation))
    execution_record = _strict_json(canonical_json_bytes(capture.execution_record))
    return TrajectoryCapture(
        scenario_id=capture.scenario_id,
        prompt=capture.prompt,
        prompt_sha256=capture.prompt_sha256,
        generated_text=capture.generated_text,
        arrays=arrays,
        observation=observation,
        execution_record=execution_record,
    )


def verify_capture_receipt(
    receipt_path: Path, *, context: CaptureVerificationContext
) -> dict[str, object]:
    """Verify receipt, exact bound files, and per-array value manifests."""

    raw = _read_plain_file(receipt_path, max_bytes=2 * 1024 * 1024)
    receipt = _strict_json(raw)
    required = {
        "schema_version",
        "status",
        "packet_eligibility",
        "scientific_status",
        "input",
        "output",
        "observation",
        "claim_boundary",
        "receipt_sha256",
    }
    if set(receipt) != required:
        raise ValueError("capture receipt keyset mismatch")
    if receipt["schema_version"] != RECEIPT_SCHEMA:
        raise ValueError("capture receipt schema mismatch")
    _require_literal(receipt, "status", CAPTURE_STATUS)
    _require_literal(receipt, "packet_eligibility", PACKET_ELIGIBILITY)
    _require_literal(receipt, "scientific_status", SCIENTIFIC_STATUS)
    _require_literal(receipt, "claim_boundary", RECEIPT_CLAIM_BOUNDARY)
    expected_hash = receipt["receipt_sha256"]
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError("capture receipt_sha256 is malformed")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    observed_hash = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest().upper()
    if observed_hash != expected_hash:
        raise ValueError("capture receipt self-hash mismatch")

    input_row = _required_mapping(receipt, "input")
    if set(input_row) != {"scenario_id", "prompt", "prompt_sha256"}:
        raise ValueError("capture receipt input keyset mismatch")
    if input_row["scenario_id"] != context.scenario_id:
        raise ValueError("capture scenario does not match the verification context")
    if input_row["prompt"] != context.prompt:
        raise ValueError("capture prompt does not match the verification context")
    prompt_sha256 = hashlib.sha256(context.prompt.encode("utf-8")).hexdigest().upper()
    if input_row["prompt_sha256"] != prompt_sha256:
        raise ValueError("capture prompt hash mismatch")

    output = _required_mapping(receipt, "output")
    if set(output) != {
        "generated_text",
        "tensor_path",
        "tensor_byte_count",
        "tensor_sha256",
        "adapter_plan_path",
        "adapter_plan_byte_count",
        "adapter_plan_file_sha256",
        "array_manifest",
    }:
        raise ValueError("capture receipt output keyset mismatch")
    if not isinstance(output["generated_text"], str):
        raise ValueError("capture generated_text must be text")
    if output["generated_text"] != context.generated_text:
        raise ValueError("capture generated_text differs from the verification context")
    if output["array_manifest"] != [dict(row) for row in context.array_manifest]:
        raise ValueError("capture array manifest differs from the verification context")

    if not receipt_path.is_absolute() or receipt_path.name.endswith(".receipt.json") is False:
        raise ValueError("capture receipt must have an absolute *.receipt.json path")
    artifact_stem = receipt_path.name[: -len(".receipt.json")]
    if not artifact_stem or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in artifact_stem
    ):
        raise ValueError("capture receipt stem is not canonical")
    tensor_expected = receipt_path.parent / f"{artifact_stem}.safetensors"
    plan_expected = receipt_path.parent / f"{artifact_stem}.adapter-plan.json"
    tensor_name = _required_text(output, "tensor_path")
    plan_name = _required_text(output, "adapter_plan_path")
    if tensor_name != tensor_expected.name or plan_name != plan_expected.name:
        raise ValueError("capture artifacts must use fixed same-directory basenames")
    tensor_path = tensor_expected
    plan_path = plan_expected
    expected_array_bytes = sum(
        _required_int(row, "byte_count")
        for row in context.array_manifest
        if isinstance(row, Mapping)
    )
    if expected_array_bytes <= 0 or expected_array_bytes > 1024 * 1024 * 1024:
        raise ValueError("verification context tensor payload exceeds the size cap")
    tensor_raw = _read_plain_file(
        tensor_path, max_bytes=expected_array_bytes + 2 * 1024 * 1024
    )
    plan_raw = _read_plain_file(plan_path, max_bytes=16 * 1024 * 1024)
    if len(tensor_raw) != _required_int(output, "tensor_byte_count"):
        raise ValueError("capture tensor byte count mismatch")
    tensor_sha256 = _required_sha256(output, "tensor_sha256")
    if hashlib.sha256(tensor_raw).hexdigest().upper() != tensor_sha256:
        raise ValueError("capture tensor hash mismatch")
    if len(plan_raw) != _required_int(output, "adapter_plan_byte_count"):
        raise ValueError("capture adapter plan byte count mismatch")
    plan_file_sha256 = _required_sha256(output, "adapter_plan_file_sha256")
    if hashlib.sha256(plan_raw).hexdigest().upper() != plan_file_sha256:
        raise ValueError("capture adapter plan hash mismatch")
    if plan_file_sha256 != context.adapter_plan_file_sha256:
        raise ValueError("adapter plan file differs from the verification context")

    observed_attestation = attest_local_snapshot(context.model_snapshot)
    require_same_attestation(context.model_attestation, observed_attestation)
    observation = _verify_observation(
        receipt["observation"],
        context=context,
        prompt_sha256=prompt_sha256,
    )
    plan, source_sha256 = verify_bound_adapter_plan(
        plan_bytes=plan_raw,
        adapter_source_path=context.adapter_source_path,
    )
    if source_sha256 != context.adapter_source_sha256:
        raise ValueError("adapter source hash differs from the verification context")
    _verify_adapter_binding(
        observation=observation,
        plan=plan,
        plan_file_sha256=plan_file_sha256,
        context=context,
    )

    try:
        from safetensors.numpy import load
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(f"safetensors numpy reader unavailable: {exc}") from exc
    arrays = load(tensor_raw)
    if set(arrays) != _ARRAY_NAMES:
        raise ValueError("capture tensor array keyset mismatch")
    observed_manifest = _array_manifest(arrays)
    if observed_manifest != output.get("array_manifest"):
        raise ValueError("capture tensor array manifest mismatch")
    observed_manifest_sha256 = hashlib.sha256(
        canonical_json_bytes(observed_manifest)
    ).hexdigest().upper()
    if (
        _required_sha256(context.execution_record, "array_manifest_sha256")
        != observed_manifest_sha256
    ):
        raise ValueError("capture tensor arrays differ from the engine execution record")
    _verify_tensor_metadata(
        tensor_raw,
        observation=observation,
        plan=plan,
        context=context,
        prompt_sha256=prompt_sha256,
    )
    _verify_arrays(arrays, observation=observation, plan=plan)
    return receipt


def _verify_observation(
    value: object,
    *,
    context: CaptureVerificationContext,
    prompt_sha256: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("capture observation must be an object")
    required = {
        "schema_version",
        "status",
        "packet_eligibility",
        "scientific_status",
        "scenario_id",
        "prompt_sha256",
        "seed",
        "generation",
        "capture_contract",
        "intervention",
        "model_snapshot",
        "loaded_weight_value_manifest_sha256",
        "tokenizer_canary",
        "adapter",
        "dependencies",
        "runtime",
        "claim_boundary",
        "execution_record",
    }
    if context.scenario_source is not None:
        required.add("scenario_source")
    if set(value) != required:
        raise ValueError("capture observation keyset mismatch")
    _require_literal(value, "schema_version", CAPTURE_SCHEMA)
    _require_literal(value, "status", CAPTURE_STATUS)
    _require_literal(value, "packet_eligibility", PACKET_ELIGIBILITY)
    _require_literal(value, "scientific_status", SCIENTIFIC_STATUS)
    _require_literal(value, "claim_boundary", OBSERVATION_CLAIM_BOUNDARY)
    if value["scenario_id"] != context.scenario_id:
        raise ValueError("observation scenario mismatch")
    if value["prompt_sha256"] != prompt_sha256:
        raise ValueError("observation prompt hash mismatch")
    if _required_int(value, "seed") != context.seed:
        raise ValueError("observation seed mismatch")

    generation = _required_mapping(value, "generation")
    if set(generation) != {"method", "max_new_tokens", "temperature", "sampling"}:
        raise ValueError("capture generation keyset mismatch")
    if generation != {
        "method": "manual_greedy_argmax",
        "max_new_tokens": context.max_new_tokens,
        "temperature": None,
        "sampling": False,
    }:
        raise ValueError("capture generation contract mismatch")
    if _required_mapping(value, "intervention") != dict(context.intervention):
        raise ValueError("capture intervention differs from verification context")
    if value["model_snapshot"] != context.model_attestation.to_dict():
        raise ValueError("observation model snapshot differs from verification context")
    if value["loaded_weight_value_manifest_sha256"] != context.loaded_weight_value_manifest_sha256:
        raise ValueError("observation loaded-weight value manifest mismatch")
    if value["tokenizer_canary"] != dict(context.tokenizer_canary):
        raise ValueError("observation tokenizer canary mismatch")
    if value["dependencies"] != dict(context.dependency_versions):
        raise ValueError("observation dependency versions mismatch")
    if value["runtime"] != dict(context.runtime_observation):
        raise ValueError("observation runtime identity mismatch")
    if value["execution_record"] != dict(context.execution_record):
        raise ValueError("observation execution record mismatch")
    runtime = _required_mapping(value, "runtime")
    if set(runtime) != {
        "python",
        "platform",
        "device",
        "dtype_request",
        "torch_deterministic_algorithms_enabled",
        "source_manifest",
        "python_executable",
        "hardware",
        "callable_manifest",
        "tokenizer_callable_manifest",
        "module_attribute_manifest",
        "tokenizer_state_manifest",
        "named_buffer_manifest",
        "model_config_runtime_manifest",
    }:
        raise ValueError("observation runtime keyset mismatch")
    if runtime["source_manifest"] != [dict(row) for row in context.runtime_source_manifest]:
        raise ValueError("observation runtime source manifest mismatch")
    _verify_file_manifest(context.runtime_source_manifest)
    if runtime["python_executable"] != dict(context.python_executable_identity):
        raise ValueError("observation Python executable identity mismatch")
    _verify_file_identity(context.python_executable_identity)

    if context.scenario_source is not None:
        if value["scenario_source"] != dict(context.scenario_source):
            raise ValueError("observation scenario source mismatch")
        _verify_scenario_source(
            _required_mapping(value, "scenario_source"),
            scenario_id=context.scenario_id,
            prompt=context.prompt,
        )
    return value


def _array_manifest(arrays: Mapping[str, np.ndarray]) -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "shape": list(value.shape),
            "dtype": str(value.dtype),
            "byte_count": int(value.nbytes),
            "value_sha256": hashlib.sha256(
                np.ascontiguousarray(value).tobytes(order="C")
            ).hexdigest().upper(),
        }
        for name, value in sorted(arrays.items())
    ]


def _verify_adapter_binding(
    *,
    observation: Mapping[str, object],
    plan: Mapping[str, object],
    plan_file_sha256: str,
    context: CaptureVerificationContext,
) -> None:
    identity = _required_mapping(plan, "identity")
    attestation = context.model_attestation
    config_projection = verify_attested_config_projection(attestation)
    declaration = _required_mapping(plan, "declaration")
    for key in (
        "model_type",
        "num_hidden_layers",
        "hidden_size",
        "num_attention_heads",
    ):
        if declaration.get(key) != config_projection[key]:
            raise ValueError(f"adapter plan declaration {key} differs from config.json")
    for key, expected in (
        ("model_id", attestation.model_id),
        ("revision", attestation.revision),
        ("config_sha256", attestation.config_sha256),
        ("weights_manifest_sha256", attestation.weights_manifest_sha256),
    ):
        if identity.get(key) != expected:
            raise ValueError(f"adapter plan {key} does not match the model snapshot")
    plan_sha256 = _required_sha256(plan, "plan_sha256")
    if plan_sha256 != context.adapter_plan_sha256:
        raise ValueError("adapter plan identity differs from the verification context")
    hooks = _required_mapping(plan, "discovery").get("layer_hooks")
    if not isinstance(hooks, list) or not hooks:
        raise ValueError("adapter plan layer_hooks must be a non-empty list")
    residual_paths: list[str] = []
    mlp_paths: list[str] = []
    attention_paths: list[str | None] = []
    for index, hook in enumerate(hooks):
        if not isinstance(hook, Mapping):
            raise ValueError(f"adapter hook row {index} must be an object")
        residual_paths.append(_required_text(hook, "residual_module"))
        mlp_paths.append(_required_text(hook, "mlp_module"))
        attention = hook.get("attention_module")
        if attention is not None and not isinstance(attention, str):
            raise ValueError("adapter attention path must be text or null")
        attention_paths.append(attention)
    expected_adapter = {
        "adapter_plan_sha256": plan_sha256,
        "adapter_plan_file_sha256": plan_file_sha256,
        "adapter_source_sha256": context.adapter_source_sha256,
        "adapter_source_path": str(context.adapter_source_path),
        "residual_paths": residual_paths,
        "mlp_paths": mlp_paths,
        "attention_paths": attention_paths,
        "config_projection": config_projection,
        "binding_status": ADAPTER_BINDING_STATUS,
        "claim_boundary": ADAPTER_CLAIM_BOUNDARY,
    }
    if _required_mapping(observation, "adapter") != expected_adapter:
        raise ValueError("observation adapter binding does not match the verified plan")
    if expected_adapter != dict(context.adapter_binding):
        raise ValueError("adapter binding differs from the verification context")


def _verify_tensor_metadata(
    raw: bytes,
    *,
    observation: Mapping[str, object],
    plan: Mapping[str, object],
    context: CaptureVerificationContext,
    prompt_sha256: str,
) -> None:
    if len(raw) < 9:
        raise ValueError("safetensors artifact is too short")
    header_length = int.from_bytes(raw[:8], "little", signed=False)
    if header_length <= 0 or 8 + header_length > len(raw):
        raise ValueError("safetensors header length is invalid")
    header = _strict_json(raw[8 : 8 + header_length])
    if set(header) - {"__metadata__"} != _ARRAY_NAMES:
        raise ValueError("safetensors header tensor keyset mismatch")
    metadata = _required_mapping(header, "__metadata__")
    expected = {
        "schema_version": TENSOR_SCHEMA,
        "scenario_id": context.scenario_id,
        "prompt_sha256": prompt_sha256,
        "model_tree_manifest_sha256": context.model_attestation.tree_manifest_sha256,
        "loaded_weight_value_manifest_sha256": context.loaded_weight_value_manifest_sha256,
        "adapter_plan_sha256": _required_sha256(plan, "plan_sha256"),
        "packet_eligibility": PACKET_ELIGIBILITY,
    }
    if metadata != expected:
        raise ValueError("safetensors metadata does not match the bound observation")
    if observation["scenario_id"] != metadata["scenario_id"]:
        raise ValueError("tensor and observation scenario mismatch")


def _verify_arrays(
    arrays: Mapping[str, np.ndarray],
    *,
    observation: Mapping[str, object],
    plan: Mapping[str, object],
) -> None:
    steps = _required_int(_required_mapping(observation, "generation"), "max_new_tokens")
    declaration = _required_mapping(plan, "declaration")
    layers = _required_int(declaration, "num_hidden_layers")
    hidden = _required_int(declaration, "hidden_size")
    prompt_ids = arrays["prompt_input_ids"]
    mask = arrays["prompt_attention_mask"]
    generated = arrays["generated_token_ids"]
    lengths = arrays["input_lengths"]
    residual = arrays["residual_states"]
    mlp = arrays["mlp_states"]
    logits = arrays["pre_selection_logits"]
    if prompt_ids.dtype != np.int64 or prompt_ids.ndim != 2 or prompt_ids.shape[0] != 1 or prompt_ids.shape[1] <= 0:
        raise ValueError("prompt_input_ids shape/dtype mismatch")
    if mask.dtype != np.int64 or mask.shape != prompt_ids.shape or not np.isin(mask, (0, 1)).all():
        raise ValueError("prompt_attention_mask shape/dtype/value mismatch")
    if generated.dtype != np.int64 or generated.shape != (steps,):
        raise ValueError("generated_token_ids shape/dtype mismatch")
    if lengths.dtype != np.int64 or lengths.shape != (steps,):
        raise ValueError("input_lengths shape/dtype mismatch")
    expected_lengths = np.arange(prompt_ids.shape[1], prompt_ids.shape[1] + steps, dtype=np.int64)
    if not np.array_equal(lengths, expected_lengths):
        raise ValueError("input_lengths do not match the generation trajectory")
    for label, array in (("residual", residual), ("MLP", mlp)):
        if array.dtype != np.float32 or array.shape != (steps, layers, hidden):
            raise ValueError(f"{label} tensor shape/dtype mismatch")
        if not np.isfinite(array).all():
            raise ValueError(f"{label} tensor contains non-finite values")
    adapter = _required_mapping(observation, "adapter")
    vocab_size = _required_int(
        _required_mapping(adapter, "config_projection"), "vocab_size"
    )
    if logits.dtype != np.float32 or logits.shape != (steps, vocab_size):
        raise ValueError("pre_selection_logits shape/dtype mismatch")
    if not np.isfinite(logits).all():
        raise ValueError("pre_selection_logits contains non-finite values")
    if (generated < 0).any() or (generated >= logits.shape[1]).any():
        raise ValueError("generated token ID is outside the captured vocabulary")
    if not np.array_equal(generated, np.argmax(logits, axis=1).astype(np.int64)):
        raise ValueError("generated token IDs do not equal captured greedy argmax")
    capture_contract = _required_mapping(observation, "capture_contract")
    if set(capture_contract) != {"residual", "mlp", "logits", "attention", "shapes"}:
        raise ValueError("capture contract keyset mismatch")
    expected_contract = {
        "residual": "full_width_last_current_token_for_every_decoder_layer",
        "mlp": "full_width_last_current_token_for_every_decoder_layer",
        "logits": "full_vocabulary_pre_selection_each_generation_step",
        "attention": "NOT_CAPTURED_IN_V1",
        "shapes": {name: list(array.shape) for name, array in arrays.items()},
    }
    if capture_contract != expected_contract:
        raise ValueError("capture contract does not match tensor arrays")
    intervention = _required_mapping(observation, "intervention")
    if set(intervention) != {
        "mode",
        "layer_index",
        "active_steps",
        "vector_sha256",
        "vector_length",
        "max_vector_norm",
    }:
        raise ValueError("intervention observation keyset mismatch")
    mode = intervention.get("mode")
    if mode not in {"baseline", "noop", "zero"}:
        raise ValueError("persisted intervention mode is outside v1")
    if mode == "baseline":
        if intervention != {
            "mode": "baseline",
            "layer_index": None,
            "active_steps": [],
            "vector_sha256": None,
            "vector_length": 0,
            "max_vector_norm": 0.0,
        }:
            raise ValueError("baseline intervention fields are invalid")
    else:
        layer_index = _required_int(intervention, "layer_index")
        active_steps = intervention.get("active_steps")
        if not isinstance(active_steps, list) or not active_steps:
            raise ValueError("non-baseline intervention active_steps are invalid")
        if len(active_steps) != len(set(active_steps)) or any(
            isinstance(step, bool) or not isinstance(step, int) or not 0 <= step < steps
            for step in active_steps
        ):
            raise ValueError("non-baseline intervention steps are invalid")
        if not 0 <= layer_index < layers:
            raise ValueError("intervention layer is outside the captured model")
        if intervention.get("vector_sha256") is not None or intervention.get("vector_length") != 0 or intervention.get("max_vector_norm") != 0.0:
            raise ValueError("noop/zero interventions must not carry vector fields")
        if mode == "zero":
            for step in active_steps:
                if np.any(residual[step, layer_index] != 0):
                    raise ValueError("zero intervention target residual is not exactly zero")


def _verify_file_manifest(rows: tuple[Mapping[str, object], ...]) -> None:
    if not rows:
        raise ValueError("runtime source manifest must not be empty")
    seen: set[str] = set()
    for row in rows:
        path_text = _required_text(row, "path")
        folded = path_text.casefold()
        if folded in seen:
            raise ValueError("runtime source manifest contains duplicate paths")
        seen.add(folded)
        _verify_file_identity(row)


def _verify_file_identity(row: Mapping[str, object]) -> None:
    if set(row) != {"path", "byte_count", "sha256"}:
        raise ValueError("file identity keyset mismatch")
    path = Path(_required_text(row, "path"))
    raw = _read_plain_file(path)
    if len(raw) != _required_int(row, "byte_count"):
        raise ValueError(f"file identity byte count mismatch: {path}")
    if hashlib.sha256(raw).hexdigest().upper() != _required_sha256(row, "sha256"):
        raise ValueError(f"file identity hash mismatch: {path}")


def _verify_scenario_source(
    row: Mapping[str, object], *, scenario_id: str, prompt: str
) -> None:
    if set(row) != {"path", "byte_count", "sha256", "snapshot_semantics"}:
        raise ValueError("scenario source keyset mismatch")
    _require_literal(
        row,
        "snapshot_semantics",
        "one immutable byte snapshot strict-parsed and hashed",
    )
    expected_bytes = _required_int(row, "byte_count")
    if expected_bytes <= 0 or expected_bytes > 1024 * 1024:
        raise ValueError("scenario source byte count exceeds the size cap")
    raw = _read_plain_file(
        Path(_required_text(row, "path")), max_bytes=expected_bytes
    )
    if len(raw) != _required_int(row, "byte_count"):
        raise ValueError("scenario source byte count mismatch")
    if hashlib.sha256(raw).hexdigest().upper() != _required_sha256(row, "sha256"):
        raise ValueError("scenario source hash mismatch")
    scenario = _strict_json(raw)
    if scenario != {
        "schema_version": "cas_open_weight_capture_scenario.v1",
        "scenario_id": scenario_id,
        "prompt": prompt,
    }:
        raise ValueError("scenario source content mismatch")


def _write_create_new(path: Path, payload: bytes) -> None:
    with path.open("xb", buffering=0) as handle:
        offset = 0
        while offset < len(payload):
            written = handle.write(payload[offset:])
            if written is None or written <= 0:
                raise OSError(f"short write while creating {path}")
            offset += written
        handle.flush()
        os.fsync(handle.fileno())


def _read_plain_file(path: Path, *, max_bytes: int | None = None) -> bytes:
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"bound capture file is missing: {path}")
    _require_plain_parent_chain(path.parent)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
        raise ValueError(f"bound capture file must be plain: {path}")
    with path.open("rb", buffering=0) as handle:
        before = os.fstat(handle.fileno())
        if max_bytes is not None and before.st_size > max_bytes:
            raise ValueError(f"bound capture file exceeds size cap: {path}")
        raw = handle.read()
        after = os.fstat(handle.fileno())
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity or len(raw) != before.st_size:
        raise ValueError(f"bound capture file changed while reading: {path}")
    return raw


def _require_plain_parent_chain(path: Path) -> None:
    current = path
    while True:
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            raise ValueError(f"bound path ancestor must be plain: {current}")
        parent = current.parent
        if parent == current:
            return
        current = parent


def _strict_json(raw: bytes) -> dict[str, object]:
    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number is forbidden: {value}")

    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=pairs_hook,
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("capture receipt must be a JSON object")
    return value


def _required_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"capture receipt {key} must be non-empty text")
    return item


def _required_mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        raise ValueError(f"capture receipt {key} must be an object")
    return item


def _required_int(value: Mapping[str, Any], key: str) -> int:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError(f"capture receipt {key} must be an integer")
    return item


def _required_sha256(value: Mapping[str, Any], key: str) -> str:
    item = _required_text(value, key)
    if len(item) != 64 or item != item.upper() or any(
        character not in "0123456789ABCDEF" for character in item
    ):
        raise ValueError(f"capture receipt {key} must be uppercase SHA-256")
    return item


def _require_literal(value: Mapping[str, Any], key: str, expected: object) -> None:
    if value.get(key) != expected:
        raise ValueError(f"capture receipt {key} literal mismatch")


def _is_reparse(value: os.stat_result) -> bool:
    attributes = getattr(value, "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & flag)
