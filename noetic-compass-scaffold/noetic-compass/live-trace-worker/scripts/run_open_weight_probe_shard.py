"""Run one real open-weight CAS probe shard.

This is the command meant to sit behind ``scripts/run_fleet_worker.py --``.
It consumes the CAS_FLEET_* environment variables from the fleet daemon,
loads the declared open-weight model through Hugging Face Transformers, runs
the assigned layer range on real prompts, and writes a result JSON to
``CAS_FLEET_RESULT_PATH``.

Strictness rule: this script never fabricates CAS proof outputs. It can always
produce ``layer_activation_summary`` and ``worker_evidence_manifest`` after a
real model forward pass. It produces ``cas_axis_readout`` only when a compatible
probe-weight file is supplied. It produces ``blindspot_overlay`` only when a
model-matched cover-map file is supplied. Missing proof inputs are reported as
missing outputs so the fleet merge/verifier cannot overclaim.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from typing import Any

try:  # Package import for tests/tools; direct import for the executable script.
    from .open_weight_artifact_guard import (
        reverify_open_weight_artifacts_after_load,
        require_commit_revision,
        require_sha256,
        verify_open_weight_artifact_manifest,
    )
except ImportError:  # pragma: no cover - exercised by direct script execution
    from open_weight_artifact_guard import (
        reverify_open_weight_artifacts_after_load,
        require_commit_revision,
        require_sha256,
        verify_open_weight_artifact_manifest,
    )


@dataclass(frozen=True)
class ProbeScenario:
    scenario_id: str
    prompt: str


@dataclass(frozen=True)
class ProbeShardConfig:
    model_id: str
    worker_id: str
    audit_id: str
    job_id: str
    layer_start: int
    layer_end: int
    shard_id: str
    assigned_methods: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    result_path: Path
    scenario_path: Path | None = None
    prompt: str | None = None
    model_revision: str | None = None
    model_artifact_manifest_path: Path | None = None
    model_artifact_manifest_sha256: str | None = None
    torch_dtype: str = "auto"
    device_map: str = "auto"
    max_scenarios: int = 25
    max_length: int = 512
    top_k: int = 8
    trust_remote_code: bool = False
    probe_weights_path: Path | None = None
    cover_map_path: Path | None = None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "ProbeShardConfig":
        source = env or os.environ
        result_path = _required_path(source, "CAS_FLEET_RESULT_PATH")
        layer_start = _required_int(source, "CAS_FLEET_LAYER_START")
        layer_end = _required_int(source, "CAS_FLEET_LAYER_END")
        if layer_end < layer_start:
            raise ValueError("CAS_FLEET_LAYER_END must be >= CAS_FLEET_LAYER_START")
        return cls(
            model_id=_required_text(source, "CAS_FLEET_MODEL_ID"),
            worker_id=_required_text(source, "CAS_FLEET_WORKER_ID"),
            audit_id=_required_text(source, "CAS_FLEET_AUDIT_ID"),
            job_id=_required_text(source, "CAS_FLEET_JOB_ID"),
            layer_start=layer_start,
            layer_end=layer_end,
            shard_id=_required_text(source, "CAS_FLEET_SHARD_ID"),
            assigned_methods=tuple(_json_string_list(source.get("CAS_FLEET_ASSIGNED_METHODS_JSON"), "assigned_methods")),
            expected_outputs=tuple(_json_string_list(source.get("CAS_FLEET_EXPECTED_OUTPUTS_JSON"), "expected_outputs")),
            result_path=result_path,
            scenario_path=_optional_path(source.get("CAS_FLEET_SCENARIO_PATH")),
            prompt=_optional_text(source.get("CAS_FLEET_PROMPT")),
            model_revision=require_commit_revision(
                _required_text(source, "CAS_FLEET_MODEL_REVISION"),
                field_name="CAS_FLEET_MODEL_REVISION",
            ),
            model_artifact_manifest_path=_required_path(
                source,
                "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_PATH",
            ),
            model_artifact_manifest_sha256=require_sha256(
                _required_text(source, "CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256"),
                field_name="CAS_FLEET_MODEL_ARTIFACT_MANIFEST_SHA256",
            ),
            torch_dtype=_optional_text(source.get("CAS_FLEET_TORCH_DTYPE")) or "auto",
            device_map=_optional_text(source.get("CAS_FLEET_DEVICE_MAP")) or "auto",
            max_scenarios=int(source.get("CAS_FLEET_MAX_SCENARIOS", "25")),
            max_length=int(source.get("CAS_FLEET_MAX_LENGTH", "512")),
            top_k=int(source.get("CAS_FLEET_TOP_K", "8")),
            trust_remote_code=_require_remote_code_disabled(
                source.get("CAS_FLEET_TRUST_REMOTE_CODE")
            ),
            probe_weights_path=_optional_path(source.get("CAS_FLEET_PROBE_WEIGHTS_PATH")),
            cover_map_path=_optional_path(source.get("CAS_FLEET_COVER_MAP_PATH")),
        )


def main() -> int:
    result_path_text = os.environ.get("CAS_FLEET_RESULT_PATH")
    result_path = Path(result_path_text) if result_path_text else None
    try:
        config = ProbeShardConfig.from_env()
        payload = run_probe_shard(config)
        _write_json(config.result_path, payload)
        return 0
    except Exception as exc:
        if result_path is not None:
            _write_json(
                result_path,
                {
                    "produced_outputs": [],
                    "missing_outputs": _safe_expected_outputs(),
                    "error_message": str(exc),
                    "evidence_payload": {
                        "schema_version": "cas_harness_open_weight_probe_shard.v1",
                        "status": "failed_before_or_during_model_forward",
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                },
            )
            return 0
        print(f"CAS_FLEET_RESULT_PATH missing and probe shard failed: {exc}", file=sys.stderr)
        return 2


def run_probe_shard(config: ProbeShardConfig) -> dict[str, Any]:
    scenarios = load_scenarios(config)
    probe_weights = (
        load_cas_probe_weights(config.probe_weights_path)
        if config.probe_weights_path is not None
        else None
    )
    blindspot_overlay = (
        load_blindspot_cover_map(config.cover_map_path, model_id=config.model_id)
        if config.cover_map_path is not None
        else None
    )
    model, tokenizer, model_info = load_open_weight_model(config)
    layer_modules = locate_transformer_layers(model)
    selected_layers = select_assigned_layers(layer_modules, config.layer_start, config.layer_end)
    activation_summary = [
        run_activation_capture(
            model=model,
            tokenizer=tokenizer,
            prompt=scenario.prompt,
            scenario_id=scenario.scenario_id,
            selected_layers=selected_layers,
            max_length=config.max_length,
            top_k=config.top_k,
        )
        for scenario in scenarios[: config.max_scenarios]
    ]
    evidence_payload: dict[str, Any] = {
        "schema_version": "cas_harness_open_weight_probe_shard.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "real_model_forward_completed",
        "audit_id": config.audit_id,
        "job_id": config.job_id,
        "worker_id": config.worker_id,
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "shard_id": config.shard_id,
        "layer_start": config.layer_start,
        "layer_end": config.layer_end,
        "assigned_methods": list(config.assigned_methods),
        "expected_outputs": list(config.expected_outputs),
        "model_info": model_info,
        "scenario_count": len(activation_summary),
        "scenario_ids": [item["scenario_id"] for item in activation_summary],
        "activation_summary": activation_summary,
        "proof_inputs": {
            "probe_weights_path": str(config.probe_weights_path) if config.probe_weights_path else None,
            "cover_map_path": str(config.cover_map_path) if config.cover_map_path else None,
        },
    }
    if probe_weights is not None:
        evidence_payload["cas_axis_readout"] = compute_cas_axis_readout(
            evidence_payload,
            probe_weights,
        )
    if blindspot_overlay is not None:
        evidence_payload["blindspot_overlay"] = blindspot_overlay

    produced, missing = classify_outputs(config.expected_outputs, evidence_payload)
    return {
        "produced_outputs": produced,
        "missing_outputs": missing,
        "error_message": None,
        "evidence_payload": evidence_payload,
    }


def load_open_weight_model(config: ProbeShardConfig) -> tuple[Any, Any, dict[str, Any]]:
    verified_artifacts = verify_open_weight_artifact_manifest(
        manifest_path=config.model_artifact_manifest_path,
        expected_manifest_sha256=config.model_artifact_manifest_sha256,
        model_id=config.model_id,
        model_revision=config.model_revision,
        trust_remote_code=config.trust_remote_code,
    )
    try:
        import torch
        from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:  # pragma: no cover - depends on deployment image
        raise RuntimeError(f"torch/transformers unavailable for real open-weight eval: {exc}") from exc

    dtype = resolve_torch_dtype(torch, config.torch_dtype, config.device_map)
    model_source = os.fspath(verified_artifacts.model_root)
    model_config = AutoConfig.from_pretrained(
        model_source,
        revision=verified_artifacts.model_revision,
        local_files_only=True,
        trust_remote_code=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        model_source,
        revision=verified_artifacts.model_revision,
        local_files_only=True,
        trust_remote_code=False,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_source,
        revision=verified_artifacts.model_revision,
        dtype=dtype,
        device_map=config.device_map,
        low_cpu_mem_usage=True,
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
    )
    model.eval()
    verified_artifacts = reverify_open_weight_artifacts_after_load(verified_artifacts)
    validate_loaded_model_execution(torch, model)
    model_info = {
        "architectures": list(getattr(model_config, "architectures", []) or []),
        "model_type": getattr(model_config, "model_type", None),
        "hidden_size": getattr(model_config, "hidden_size", None),
        "num_hidden_layers": getattr(model_config, "num_hidden_layers", None),
        "num_attention_heads": getattr(model_config, "num_attention_heads", None),
        "vocab_size": getattr(model_config, "vocab_size", None),
        "torch_dtype": str(dtype) if dtype is not None else "auto",
        "device_map": config.device_map,
        "parameter_count": count_parameters(model),
        "artifact_identity": verified_artifacts.evidence(post_load_reverified=True),
    }
    return model, tokenizer, model_info


def run_activation_capture(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    scenario_id: str,
    selected_layers: list[tuple[int, Any]],
    max_length: int,
    top_k: int,
) -> dict[str, Any]:
    captures: dict[int, Any] = {}
    handles = []
    try:
        for layer_idx, layer in selected_layers:
            module = getattr(layer, "mlp", layer)
            handles.append(module.register_forward_hook(_capture_last_token(captures, layer_idx)))
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
        device = first_real_parameter_device(model)
        if device is not None:
            inputs = {key: value.to(device) for key, value in inputs.items()}
        with inference_context():
            outputs = model(**inputs, use_cache=False)
        require_finite_tensor(outputs.logits, label="model logits")
        confidence = softmax_margin(outputs.logits[0, -1])
    finally:
        for handle in handles:
            handle.remove()
    return {
        "scenario_id": scenario_id,
        "token_count": int(inputs["input_ids"].shape[-1]),
        "confidence_margin": confidence,
        "layers": [
            summarise_layer(layer_idx, vector, top_k=top_k)
            for layer_idx, vector in sorted(captures.items())
        ],
    }


def _capture_last_token(captures: dict[int, Any], layer_idx: int):
    def hook(_module: Any, _inputs: Any, output: Any) -> None:
        value = output[0] if isinstance(output, tuple) else output
        captured = value[0, -1].detach().float().cpu()
        require_finite_tensor(captured, label=f"layer {layer_idx} activation")
        captures[layer_idx] = captured

    return hook


def locate_transformer_layers(model: Any) -> list[Any]:
    for path in (
        ("gpt_neox", "layers"),
        ("model", "layers"),
        ("transformer", "h"),
        ("transformer", "blocks"),
    ):
        value = model
        for attr in path:
            value = getattr(value, attr, None)
            if value is None:
                break
        if value is not None:
            return list(value)
    raise RuntimeError("Could not locate transformer layer stack for this architecture.")


def select_assigned_layers(layers: list[Any], layer_start: int, layer_end: int) -> list[tuple[int, Any]]:
    if layer_start >= len(layers):
        raise RuntimeError(f"Assigned layer_start {layer_start} is outside model layer count {len(layers)}.")
    end = min(layer_end, len(layers) - 1)
    return [(idx, layers[idx]) for idx in range(layer_start, end + 1)]


def summarise_layer(layer_idx: int, vector: Any, *, top_k: int) -> dict[str, Any]:
    values = vector.abs()
    k = max(1, min(int(top_k), int(values.numel())))
    top = values.topk(k)
    return {
        "layer": layer_idx,
        "mean_abs_activation": round(float(values.mean().item()), 6),
        "max_abs_activation": round(float(values.max().item()), 6),
        "top_neurons": [
            {
                "index": int(index),
                "abs_activation": round(float(score), 6),
            }
            for score, index in zip(top.values.tolist(), top.indices.tolist(), strict=False)
        ],
    }


def softmax_margin(logits: Any) -> float:
    require_finite_tensor(logits, label="softmax logits")
    probs = logits.float().softmax(dim=-1)
    top2 = probs.topk(2).values
    return round(float((top2[0] - top2[1]).item()), 6)


def load_cas_probe_weights(probe_weights_path: Path) -> dict[str, Any]:
    """Parse the cheap proof input before allocating the open-weight model."""

    weights = json.loads(probe_weights_path.read_text(encoding="utf-8"))
    if not isinstance(weights, dict):
        raise RuntimeError("CAS probe weights must contain one JSON object.")
    if weights.get("schema_version") != "cas_probe_linear_v1":
        raise RuntimeError("CAS probe weights must use schema_version=cas_probe_linear_v1.")
    axes = weights.get("axes")
    vectors = weights.get("weights")
    if not isinstance(axes, list) or not isinstance(vectors, dict):
        raise RuntimeError("CAS probe weights require axes and weights.")
    return weights


def compute_cas_axis_readout(
    evidence_payload: dict[str, Any],
    weights: dict[str, Any],
) -> dict[str, Any]:
    axes = weights["axes"]
    vectors = weights["weights"]
    bias = weights.get("bias", {})
    pooled = pooled_activation_vector(evidence_payload)
    scores: dict[str, float] = {}
    for axis in axes:
        vector = vectors.get(axis)
        if not isinstance(vector, list) or len(vector) != len(pooled):
            raise RuntimeError(f"CAS probe axis {axis!r} has incompatible hidden size.")
        score = sum(float(w) * value for w, value in zip(vector, pooled, strict=False)) + float(bias.get(axis, 0.0))
        scores[str(axis)] = round(score, 6)
    return {
        "schema_version": weights["schema_version"],
        "probe_id": weights.get("probe_id"),
        "axes": axes,
        "scores": scores,
        "score_source": "linear_probe_over_assigned_layer_activation_summary",
    }


def pooled_activation_vector(evidence_payload: dict[str, Any]) -> list[float]:
    top_values: list[float] = []
    for scenario in evidence_payload.get("activation_summary", []):
        for layer in scenario.get("layers", []):
            top_values.extend(float(item["abs_activation"]) for item in layer.get("top_neurons", []))
    if not top_values:
        raise RuntimeError("Cannot compute CAS readout without activation summary.")
    return top_values


def load_blindspot_cover_map(path: Path, *, model_id: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("model_id") != model_id:
        raise RuntimeError("Blindspot cover map model_id does not match the audited model.")
    if "covers" not in payload:
        raise RuntimeError("Blindspot cover map requires covers.")
    return payload


def classify_outputs(expected_outputs: tuple[str, ...], evidence_payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    available = {
        "layer_activation_summary": bool(evidence_payload.get("activation_summary")),
        "worker_evidence_manifest": True,
        "cas_axis_readout": "cas_axis_readout" in evidence_payload,
        "blindspot_overlay": "blindspot_overlay" in evidence_payload,
    }
    produced = [name for name in expected_outputs if available.get(name, False)]
    missing = [name for name in expected_outputs if name not in produced]
    return produced, missing


def load_scenarios(config: ProbeShardConfig) -> list[ProbeScenario]:
    scenarios: list[ProbeScenario] = []
    if config.scenario_path is not None:
        payload = json.loads(config.scenario_path.read_text(encoding="utf-8"))
        items = payload.get("scenarios", payload) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise RuntimeError("Scenario file must be a list or contain a scenarios list.")
        for index, item in enumerate(items):
            if isinstance(item, str):
                scenarios.append(ProbeScenario(scenario_id=f"scenario-{index + 1:03d}", prompt=item))
            elif isinstance(item, dict):
                prompt = str(item.get("prompt") or item.get("text") or "").strip()
                if prompt:
                    scenarios.append(
                        ProbeScenario(
                            scenario_id=str(item.get("id") or item.get("scenario_id") or f"scenario-{index + 1:03d}"),
                            prompt=prompt,
                        )
                    )
    if config.prompt:
        scenarios.append(ProbeScenario(scenario_id="single-prompt", prompt=config.prompt))
    if not scenarios:
        raise RuntimeError("Set CAS_FLEET_SCENARIO_PATH or CAS_FLEET_PROMPT for a genuine eval.")
    return scenarios


def resolve_torch_dtype(torch: Any, value: str, device_map: str = "auto") -> Any:
    normalized = (value or "auto").strip().lower()
    normalized_device = (device_map or "auto").strip().lower()
    cuda_available = bool(torch.cuda.is_available())
    if normalized_device.startswith("cuda") and not cuda_available:
        raise RuntimeError("CUDA device_map requested but CUDA is unavailable.")
    cpu_execution = normalized_device == "cpu" or not cuda_available
    if cpu_execution:
        # Pythia CPU-half can load successfully while producing only NaNs.
        # The actual dtype, not the caller's requested hint, is recorded in
        # model_info so this coercion cannot be hidden in evidence.
        return torch.float32
    if normalized == "auto":
        return None
    mapping = {
        "float16": torch.float16,
        "fp16": torch.float16,
        "bfloat16": torch.bfloat16,
        "bf16": torch.bfloat16,
        "float32": torch.float32,
        "fp32": torch.float32,
    }
    if normalized not in mapping:
        raise RuntimeError(f"Unsupported CAS_FLEET_TORCH_DTYPE={value!r}.")
    return mapping[normalized]


def validate_loaded_model_execution(torch: Any, model: Any) -> None:
    """Reject materialized CPU-half parameters before any evidence is emitted."""

    try:
        parameters = list(model.parameters())
    except Exception as exc:
        raise RuntimeError("Loaded model parameters are not inspectable.") from exc
    materialized = [
        parameter
        for parameter in parameters
        if getattr(getattr(parameter, "device", None), "type", "") != "meta"
    ]
    if not materialized:
        raise RuntimeError("Loaded model has no materialized parameters.")
    incompatible = [
        parameter
        for parameter in materialized
        if getattr(getattr(parameter, "device", None), "type", "") == "cpu"
        and getattr(parameter, "dtype", None) != torch.float32
    ]
    if incompatible:
        raise RuntimeError(
            "Loaded model contains CPU parameters outside float32; refusing nonfinite evidence risk."
        )


def require_finite_tensor(value: Any, *, label: str) -> None:
    """Fail closed when a model output or captured activation is nonfinite."""

    try:
        finite = bool(value.isfinite().all().item())
    except Exception as exc:
        raise RuntimeError(f"{label} cannot be checked for finiteness.") from exc
    if not finite:
        raise RuntimeError(f"{label} contains NaN or infinity.")


def count_parameters(model: Any) -> int:
    try:
        return int(sum(param.numel() for param in model.parameters()))
    except Exception:
        return 0


def first_real_parameter_device(model: Any) -> Any | None:
    try:
        for param in model.parameters():
            device = getattr(param, "device", None)
            if device is not None and getattr(device, "type", "") != "meta":
                return device
    except Exception:
        return None
    return None


def inference_context():
    import torch

    return torch.inference_mode()


def _required_text(env: dict[str, str], key: str) -> str:
    value = _optional_text(env.get(key))
    if value is None:
        raise ValueError(f"{key} is required")
    return value


def _required_int(env: dict[str, str], key: str) -> int:
    return int(_required_text(env, key))


def _required_path(env: dict[str, str], key: str) -> Path:
    return Path(_required_text(env, key))


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _optional_path(value: str | None) -> Path | None:
    text = _optional_text(value)
    return Path(text) if text else None


def _json_string_list(value: str | None, field_name: str) -> list[str]:
    if value is None:
        return []
    payload = json.loads(value)
    if not isinstance(payload, list):
        raise ValueError(f"{field_name} must be a JSON list")
    out = [str(item).strip() for item in payload if str(item).strip()]
    if not out:
        raise ValueError(f"{field_name} must not be empty")
    return out


def _safe_expected_outputs() -> list[str]:
    try:
        return _json_string_list(os.environ.get("CAS_FLEET_EXPECTED_OUTPUTS_JSON"), "expected_outputs")
    except Exception:
        return []


def _require_remote_code_disabled(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"", "0", "false", "no", "off"}:
        return False
    raise ValueError("CAS_FLEET_TRUST_REMOTE_CODE must be false for real-model execution")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
