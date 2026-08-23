"""Run one real open-weight CAS probe shard.

This command consumes CAS_FLEET_* environment variables, loads the declared
open-weight model through Hugging Face Transformers, runs the assigned layer
range on real prompts, and writes a result JSON to CAS_FLEET_RESULT_PATH. No
in-repository fleet wrapper currently invokes it; callers must check its exit
code and the versioned result schema directly. CAS_FLEET_ADAPTER_PLAN_PATH is
required; the worker re-verifies that plan and uses its exact selected MLP hook
paths instead of independently guessing an adapter layout.

Strictness rule: this script never fabricates CAS proof outputs. It can always
produce ``layer_activation_summary`` and ``worker_evidence_manifest`` after a
real model forward pass. The activation summary is deliberately lossy: it keeps
only the largest absolute activations (with their indices and signs). It is not
a full-width hidden-state vector and therefore cannot be fed to a linear probe.
The legacy ``cas_probe_linear_v1`` summary readout is rejected fail-closed.
``blindspot_overlay`` is currently disabled even when a cover map is supplied:
there is no admitted typed cover schema with the required byte bindings.
Missing or incompatible proof inputs remain missing outputs, and the process
exits nonzero, so a caller cannot mistake a rejection for worker success.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable


SCHEMA_VERSION = "cas_harness_open_weight_probe_shard.v2"
ADAPTER_SCHEMA_VERSION = "cas_harness_interpretability_adapter_plan.v1"
ADAPTER_SOURCE_PATH = (
    Path(__file__).resolve().parents[2]
    / "api"
    / "services"
    / "cas_harness_interpretability_adapter.py"
)
KNOWN_OUTPUTS = frozenset(
    {
        "layer_activation_summary",
        "worker_evidence_manifest",
        "cas_axis_readout",
        "blindspot_overlay",
    }
)
KNOWN_ASSIGNED_METHODS = frozenset({"foundation_probe", "blindspot_detection"})
REQUIRED_BASE_OUTPUTS = frozenset(
    {"layer_activation_summary", "worker_evidence_manifest"}
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
    torch_dtype: str = "auto"
    device_map: str = "auto"
    max_scenarios: int = 25
    max_length: int = 512
    top_k: int = 8
    trust_remote_code: bool = False
    probe_weights_path: Path | None = None
    cover_map_path: Path | None = None
    adapter_plan_path: Path | None = None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "ProbeShardConfig":
        source = env or os.environ
        result_path = _required_path(source, "CAS_FLEET_RESULT_PATH")
        layer_start = _required_int(source, "CAS_FLEET_LAYER_START")
        layer_end = _required_int(source, "CAS_FLEET_LAYER_END")
        if layer_end < layer_start:
            raise ValueError("CAS_FLEET_LAYER_END must be >= CAS_FLEET_LAYER_START")
        config = cls(
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
            model_revision=_required_text(source, "CAS_FLEET_MODEL_REVISION"),
            torch_dtype=_optional_text(source.get("CAS_FLEET_TORCH_DTYPE")) or "auto",
            device_map=_optional_text(source.get("CAS_FLEET_DEVICE_MAP")) or "auto",
            max_scenarios=int(source.get("CAS_FLEET_MAX_SCENARIOS", "25")),
            max_length=int(source.get("CAS_FLEET_MAX_LENGTH", "512")),
            top_k=int(source.get("CAS_FLEET_TOP_K", "8")),
            trust_remote_code=_truthy(source.get("CAS_FLEET_TRUST_REMOTE_CODE")),
            probe_weights_path=_optional_path(source.get("CAS_FLEET_PROBE_WEIGHTS_PATH")),
            cover_map_path=_optional_path(source.get("CAS_FLEET_COVER_MAP_PATH")),
            adapter_plan_path=_optional_path(source.get("CAS_FLEET_ADAPTER_PLAN_PATH")),
        )
        validate_config(config)
        return config


def main() -> int:
    result_path_text = os.environ.get("CAS_FLEET_RESULT_PATH")
    result_path = Path(result_path_text) if result_path_text else None
    try:
        config = ProbeShardConfig.from_env()
        payload = run_probe_shard(config)
        _write_json(config.result_path, payload)
        return 3 if payload["error_message"] or payload["missing_outputs"] else 0
    except Exception as exc:
        if result_path is not None:
            _write_json(
                result_path,
                {
                    "produced_outputs": [],
                    "missing_outputs": _safe_expected_outputs(),
                    "error_message": str(exc),
                    "evidence_payload": {
                        "schema_version": SCHEMA_VERSION,
                        "status": "failed_before_or_during_model_forward",
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                },
            )
            return 2
        print(f"CAS_FLEET_RESULT_PATH missing and probe shard failed: {exc}", file=sys.stderr)
        return 2


def run_probe_shard(config: ProbeShardConfig) -> dict[str, Any]:
    validate_config(config)
    scenarios, scenario_file_snapshot = load_scenarios_snapshot(config)
    model, tokenizer, model_info = load_open_weight_model(config)
    layer_modules = locate_transformer_layers(model)
    selected_layers = select_assigned_layers(layer_modules, config.layer_start, config.layer_end)
    adapter_binding, planned_mlp_paths = bind_adapter_plan(
        config=config,
        model=model,
        model_info=model_info,
        selected_layers=selected_layers,
    )
    scenario_contract = [
        {
            "scenario_id": scenario.scenario_id,
            "prompt_sha256": hashlib.sha256(scenario.prompt.encode("utf-8")).hexdigest(),
        }
        for scenario in scenarios[: config.max_scenarios]
    ]
    scenario_contract_sha256 = hashlib.sha256(
        canonical_json_bytes(scenario_contract)
    ).hexdigest()
    capture_contract = {
        "layer_start": config.layer_start,
        "layer_end": config.layer_end,
        "selected_mlp_hook_paths": [
            planned_mlp_paths[index] for index in sorted(planned_mlp_paths)
        ],
        "token_position": "final_input_tensor_position",
        "max_length": config.max_length,
        "top_k": config.top_k,
        "summary_semantics": "lossy_signed_top_k_with_indices",
    }
    capture_contract_sha256 = hashlib.sha256(
        canonical_json_bytes(capture_contract)
    ).hexdigest()
    activation_summary = [
        run_activation_capture(
            model=model,
            tokenizer=tokenizer,
            prompt=scenario.prompt,
            scenario_id=scenario.scenario_id,
            selected_layers=selected_layers,
            max_length=config.max_length,
            top_k=config.top_k,
            planned_mlp_paths=planned_mlp_paths,
        )
        for scenario in scenarios[: config.max_scenarios]
    ]
    evidence_payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "real_model_forward_completed_structurally_bound_not_packet_eligible",
        "packet_eligibility": "NOT_PACKET_ELIGIBLE",
        "packet_eligibility_reason": (
            "Adapter structure and declared revision are bound, but exact loaded "
            "model-weight and tokenizer-file bytes are not attested."
        ),
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
        "adapter_binding": adapter_binding,
        "scenario_count": len(activation_summary),
        "scenario_ids": [item["scenario_id"] for item in activation_summary],
        "scenario_contract": scenario_contract,
        "scenario_contract_sha256": scenario_contract_sha256,
        "capture_contract": capture_contract,
        "capture_contract_sha256": capture_contract_sha256,
        "activation_summary": activation_summary,
        "proof_inputs": {
            "probe_weights_path": str(config.probe_weights_path) if config.probe_weights_path else None,
            "cover_map_path": str(config.cover_map_path) if config.cover_map_path else None,
            "scenario_path": str(config.scenario_path) if config.scenario_path else None,
            "scenario_file_sha256": (
                scenario_file_snapshot["content_sha256"]
                if scenario_file_snapshot is not None
                else None
            ),
            "scenario_file_snapshot": scenario_file_snapshot,
        },
    }
    proof_input_rejections: dict[str, str] = {}
    if config.probe_weights_path is not None:
        try:
            evidence_payload["cas_axis_readout"] = compute_cas_axis_readout(
                evidence_payload,
                config.probe_weights_path,
            )
        except Exception as exc:
            proof_input_rejections["probe_weights"] = str(exc)
    if config.cover_map_path is not None:
        try:
            evidence_payload["blindspot_overlay"] = load_blindspot_cover_map(
                config.cover_map_path,
                model_id=config.model_id,
                model_revision=config.model_revision,
            )
        except Exception as exc:
            proof_input_rejections["cover_map"] = str(exc)
    if proof_input_rejections:
        evidence_payload["proof_input_rejections"] = proof_input_rejections
        evidence_payload["status"] = (
            "real_model_forward_completed_proof_inputs_rejected_not_packet_eligible"
        )

    produced, missing = classify_outputs(config.expected_outputs, evidence_payload)
    return {
        "produced_outputs": produced,
        "missing_outputs": missing,
        "error_message": (
            None
            if not proof_input_rejections
            else "; ".join(
                f"{name}: {message}"
                for name, message in sorted(proof_input_rejections.items())
            )
        ),
        "evidence_payload": evidence_payload,
    }


def validate_config(config: ProbeShardConfig) -> None:
    if config.layer_start < 0 or config.layer_end < config.layer_start:
        raise ValueError("assigned layer range must be non-negative and ordered")
    if config.max_scenarios < 1:
        raise ValueError("CAS_FLEET_MAX_SCENARIOS must be at least 1")
    if config.max_length < 1:
        raise ValueError("CAS_FLEET_MAX_LENGTH must be at least 1")
    if config.top_k < 1:
        raise ValueError("CAS_FLEET_TOP_K must be at least 1")
    if not isinstance(config.model_revision, str) or not re.fullmatch(
        r"[0-9a-f]{40,64}", config.model_revision
    ):
        raise ValueError("CAS_FLEET_MODEL_REVISION must be a pinned lowercase 40-64 hex commit")
    if config.trust_remote_code:
        raise ValueError("CAS_FLEET_TRUST_REMOTE_CODE must remain false")
    if not config.assigned_methods:
        raise ValueError("assigned_methods must be non-empty")
    if len(config.assigned_methods) != len(set(config.assigned_methods)):
        raise ValueError("assigned_methods must be unique")
    unknown_methods = sorted(set(config.assigned_methods) - KNOWN_ASSIGNED_METHODS)
    if unknown_methods:
        raise ValueError(f"unsupported assigned_methods: {unknown_methods}")
    if "foundation_probe" not in config.assigned_methods:
        raise ValueError("assigned_methods must include foundation_probe")
    if not config.expected_outputs:
        raise ValueError("expected_outputs must be non-empty")
    if len(config.expected_outputs) != len(set(config.expected_outputs)):
        raise ValueError("expected_outputs must be unique")
    unknown_outputs = sorted(set(config.expected_outputs) - KNOWN_OUTPUTS)
    if unknown_outputs:
        raise ValueError(f"unsupported expected_outputs: {unknown_outputs}")
    missing_base = sorted(REQUIRED_BASE_OUTPUTS - set(config.expected_outputs))
    if missing_base:
        raise ValueError(f"expected_outputs missing required base outputs: {missing_base}")
    has_blindspot_method = "blindspot_detection" in config.assigned_methods
    has_blindspot_output = "blindspot_overlay" in config.expected_outputs
    if has_blindspot_method != has_blindspot_output:
        raise ValueError(
            "blindspot_detection and blindspot_overlay must be declared together"
        )


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def parse_json_snapshot(raw: bytes, *, label: str) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"{label} is not strict JSON: {exc}") from exc


def read_json_snapshot(
    path: Path,
    *,
    label: str,
    after_read_hook: Callable[[], None] | None = None,
) -> tuple[Any, dict[str, Any]]:
    raw = path.read_bytes()
    if after_read_hook is not None:
        after_read_hook()
    return parse_json_snapshot(raw, label=label), {
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "snapshot_semantics": "bytes read once, then hashed and strict-parsed in memory",
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_attr_path(root: Any, dotted_path: str) -> Any:
    value = root
    for component in dotted_path.split("."):
        if not component:
            raise RuntimeError(f"invalid empty adapter path component in {dotted_path!r}")
        if component.isdigit():
            try:
                value = value[int(component)]
            except (IndexError, KeyError, TypeError) as exc:
                raise RuntimeError(f"adapter path does not resolve: {dotted_path}") from exc
        else:
            if not hasattr(value, component):
                raise RuntimeError(f"adapter path does not resolve: {dotted_path}")
            value = getattr(value, component)
    return value


def _load_adapter_verifier() -> tuple[Any, str]:
    if not ADAPTER_SOURCE_PATH.is_file():
        raise RuntimeError(f"adapter verifier source is missing: {ADAPTER_SOURCE_PATH}")
    source_sha256 = sha256_file(ADAPTER_SOURCE_PATH)
    module_name = "_cas_harness_bound_interpretability_adapter"
    spec = importlib.util.spec_from_file_location(module_name, ADAPTER_SOURCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the pinned in-repository adapter verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module, source_sha256


def bind_adapter_plan(
    *,
    config: ProbeShardConfig,
    model: Any,
    model_info: dict[str, Any],
    selected_layers: list[tuple[int, Any]],
) -> tuple[dict[str, Any], dict[int, str]]:
    """Verify and consume the adapter plan for the exact selected hook paths."""

    if config.adapter_plan_path is None:
        raise RuntimeError(
            "CAS_FLEET_ADAPTER_PLAN_PATH is required; this worker will not infer "
            "hook paths independently of the verified adapter plan"
        )
    plan_bytes = config.adapter_plan_path.read_bytes()
    plan = parse_json_snapshot(plan_bytes, label="adapter plan")
    if not isinstance(plan, dict) or plan.get("schema_version") != ADAPTER_SCHEMA_VERSION:
        raise RuntimeError(
            f"adapter plan must use schema_version={ADAPTER_SCHEMA_VERSION}"
        )
    adapter_module, adapter_source_sha256 = _load_adapter_verifier()
    adapter_module.verify_serialized_plan(plan)

    identity = plan["identity"]
    declaration = plan["declaration"]
    discovery = plan["discovery"]
    expected_identity = {
        "model_id": config.model_id,
        "revision": config.model_revision,
        "config_sha256": str(model_info["normalized_config_payload_sha256"]).upper(),
        "weights_manifest_sha256": str(
            model_info["parameter_name_shape_dtype_manifest_sha256"]
        ).upper(),
    }
    for key, expected in expected_identity.items():
        if identity.get(key) != expected:
            raise RuntimeError(
                f"adapter plan {key} does not match loaded-model structural binding"
            )
    declaration_checks = {
        "model_type": model_info.get("model_type"),
        "num_hidden_layers": model_info.get("num_hidden_layers"),
        "hidden_size": model_info.get("hidden_size"),
        "num_attention_heads": model_info.get("num_attention_heads"),
    }
    for key, observed in declaration_checks.items():
        if declaration.get(key) != observed:
            raise RuntimeError(f"adapter plan declaration {key} mismatch")

    stack_path = discovery.get("layer_stack_attr")
    if not isinstance(stack_path, str):
        raise RuntimeError("adapter plan lacks a layer_stack_attr")
    stack = _resolve_attr_path(model, stack_path)
    if len(stack) != discovery.get("observed_layer_count"):
        raise RuntimeError("adapter plan layer count no longer matches loaded model")
    hook_rows = discovery.get("layer_hooks")
    if not isinstance(hook_rows, list) or len(hook_rows) != len(stack):
        raise RuntimeError("adapter plan layer_hooks do not cover the loaded stack")

    planned_mlp_paths: dict[int, str] = {}
    for layer_index, layer in selected_layers:
        row = hook_rows[layer_index]
        mlp_path = row.get("mlp_module") if isinstance(row, dict) else None
        if not isinstance(mlp_path, str):
            raise RuntimeError(f"adapter plan has no MLP path for layer {layer_index}")
        planned_module = _resolve_attr_path(model, mlp_path)
        discovered_module, discovered_name = select_mlp_capture_module(layer)
        expected_path = f"{stack_path}.{layer_index}.{discovered_name}"
        if mlp_path != expected_path or planned_module is not discovered_module:
            raise RuntimeError(f"adapter MLP hook path mismatch at layer {layer_index}")
        planned_mlp_paths[layer_index] = mlp_path

    plan_file_sha256 = hashlib.sha256(plan_bytes).hexdigest()
    return (
        {
            "schema_version": ADAPTER_SCHEMA_VERSION,
            "adapter_plan_sha256": plan["plan_sha256"],
            "adapter_plan_file_sha256": plan_file_sha256,
            "adapter_verifier_source_sha256": adapter_source_sha256,
            "adapter_plan_path": str(config.adapter_plan_path),
            "selected_mlp_hook_paths": [
                planned_mlp_paths[index] for index in sorted(planned_mlp_paths)
            ],
            "binding_status": (
                "PLAN_SCHEMA_HASH_IDENTITY_DECLARATION_AND_SELECTED_HOOK_PATHS_VERIFIED"
            ),
            "claim_boundary": (
                "Structural binding only. Exact model-weight and tokenizer-file bytes "
                "are not attested."
            ),
        },
        planned_mlp_paths,
    )


def load_open_weight_model(config: ProbeShardConfig) -> tuple[Any, Any, dict[str, Any]]:
    try:
        import torch
        from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:  # pragma: no cover - depends on deployment image
        raise RuntimeError(f"torch/transformers unavailable for real open-weight eval: {exc}") from exc

    dtype = resolve_torch_dtype(torch, config.torch_dtype)
    model_config = AutoConfig.from_pretrained(
        config.model_id,
        revision=config.model_revision,
        trust_remote_code=config.trust_remote_code,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        config.model_id,
        revision=config.model_revision,
        trust_remote_code=config.trust_remote_code,
    )
    model = AutoModelForCausalLM.from_pretrained(
        config.model_id,
        revision=config.model_revision,
        torch_dtype=dtype,
        device_map=config.device_map,
        low_cpu_mem_usage=True,
        trust_remote_code=config.trust_remote_code,
    )
    model.eval()
    resolved_config_revision = getattr(model_config, "_commit_hash", None)
    resolved_model_revision = getattr(getattr(model, "config", None), "_commit_hash", None)
    resolved_tokenizer_revision = (
        getattr(tokenizer, "_commit_hash", None)
        or getattr(tokenizer, "init_kwargs", {}).get("_commit_hash")
    )
    for label, observed in (
        ("AutoConfig", resolved_config_revision),
        ("loaded model config", resolved_model_revision),
        ("tokenizer", resolved_tokenizer_revision),
    ):
        if observed != config.model_revision:
            raise RuntimeError(
                f"{label} resolved revision {observed!r}, expected exact pinned "
                f"revision {config.model_revision!r}"
            )
    config_payload = model_config.to_dict()
    config_payload_sha256 = hashlib.sha256(
        (json.dumps(config_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ).hexdigest()
    parameter_manifest = [
        {
            "name": name,
            "shape": [int(value) for value in parameter.shape],
            "dtype": str(parameter.dtype),
        }
        for name, parameter in model.named_parameters()
    ]
    parameter_manifest_sha256 = hashlib.sha256(
        (json.dumps(parameter_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ).hexdigest()
    tokenizer_contract = {
        "class": type(tokenizer).__name__,
        "name_or_path": str(getattr(tokenizer, "name_or_path", "")),
        "vocab_size": int(getattr(tokenizer, "vocab_size", 0)),
        "special_tokens_map": {
            str(key): str(value)
            for key, value in sorted(
                dict(getattr(tokenizer, "special_tokens_map", {}) or {}).items()
            )
        },
        "resolved_revision": resolved_tokenizer_revision,
    }
    tokenizer_contract_sha256 = hashlib.sha256(
        canonical_json_bytes(tokenizer_contract)
    ).hexdigest()
    try:
        import torch
        import transformers
    except Exception as exc:  # pragma: no cover - imports already succeeded above
        raise RuntimeError(f"could not bind runtime dependency versions: {exc}") from exc
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
        "resolved_config_revision": resolved_config_revision,
        "resolved_model_revision": resolved_model_revision,
        "resolved_tokenizer_revision": resolved_tokenizer_revision,
        "normalized_config_payload_sha256": config_payload_sha256,
        "parameter_name_shape_dtype_manifest_sha256": parameter_manifest_sha256,
        "tokenizer_contract": tokenizer_contract,
        "tokenizer_contract_sha256": tokenizer_contract_sha256,
        "worker_source_sha256": sha256_file(Path(__file__)),
        "dependency_versions": {
            "python": sys.version.split()[0],
            "torch": str(torch.__version__),
            "transformers": str(transformers.__version__),
        },
        "identity_status": (
            "PINNED_RESOLVED_REVISION_AND_STRUCTURE_RECORDED_"
            "WEIGHT_VALUES_NOT_BYTE_ATTESTED"
        ),
        "identity_claim_boundary": (
            "The revision and normalized config/parameter structure are recorded. "
            "This worker does not hash every loaded weight value and therefore does "
            "not prove exact model-weight bytes or packet eligibility."
        ),
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
    planned_mlp_paths: dict[int, str],
) -> dict[str, Any]:
    captures: dict[int, Any] = {}
    capture_modules: dict[int, str] = {}
    handles = []
    try:
        for layer_idx, layer in selected_layers:
            module, module_name = select_mlp_capture_module(layer)
            planned_path = planned_mlp_paths.get(layer_idx)
            if not planned_path or not planned_path.endswith(f".{module_name}"):
                raise RuntimeError(
                    f"verified adapter plan is missing the active MLP hook for layer {layer_idx}"
                )
            capture_modules[layer_idx] = planned_path
            handles.append(module.register_forward_hook(_capture_last_token(captures, layer_idx)))
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
        device = first_real_parameter_device(model)
        if device is not None:
            inputs = {key: value.to(device) for key, value in inputs.items()}
        with inference_context():
            outputs = model(**inputs, use_cache=False)
        confidence = softmax_margin(outputs.logits[0, -1])
    finally:
        for handle in handles:
            handle.remove()
    expected_layers = {layer_index for layer_index, _layer in selected_layers}
    if set(captures) != expected_layers:
        missing = sorted(expected_layers - set(captures))
        unexpected = sorted(set(captures) - expected_layers)
        raise RuntimeError(
            "activation hook coverage mismatch: "
            f"missing={missing} unexpected={unexpected}"
        )
    input_tensor_sha256 = {
        str(name): hashlib.sha256(
            canonical_json_bytes(tensor.detach().cpu().tolist())
        ).hexdigest()
        for name, tensor in sorted(inputs.items())
    }
    return {
        "scenario_id": scenario_id,
        "token_count": int(inputs["input_ids"].shape[-1]),
        "input_tensor_sha256": input_tensor_sha256,
        "token_position": "final_input_tensor_position",
        "confidence_margin": confidence,
        "layers": [
            {
                **summarise_layer(layer_idx, vector, top_k=top_k),
                "capture_module": capture_modules[layer_idx],
            }
            for layer_idx, vector in sorted(captures.items())
        ],
    }


def _capture_last_token(captures: dict[int, Any], layer_idx: int):
    def hook(_module: Any, _inputs: Any, output: Any) -> None:
        value = output[0] if isinstance(output, tuple) else output
        captures[layer_idx] = value[0, -1].detach().float().cpu()

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
    if layer_end >= len(layers):
        raise RuntimeError(
            f"Assigned layer_end {layer_end} is outside model layer count {len(layers)}."
        )
    return [(idx, layers[idx]) for idx in range(layer_start, layer_end + 1)]


def select_mlp_capture_module(layer: Any) -> tuple[Any, str]:
    candidates = [
        (name, getattr(layer, name))
        for name in ("mlp", "ffn", "feed_forward")
        if hasattr(layer, name)
        and callable(getattr(getattr(layer, name), "register_forward_hook", None))
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            "expected exactly one registered MLP/FFN capture module; "
            f"found {[name for name, _module in candidates]}"
        )
    name, module = candidates[0]
    return module, name


def summarise_layer(layer_idx: int, vector: Any, *, top_k: int) -> dict[str, Any]:
    values = vector.abs()
    k = max(1, min(int(top_k), int(values.numel())))
    top = values.topk(k)
    return {
        "layer": layer_idx,
        "captured_vector_shape": [int(value) for value in vector.shape],
        "captured_vector_dtype": str(vector.dtype),
        "mean_abs_activation": round(float(values.mean().item()), 6),
        "max_abs_activation": round(float(values.max().item()), 6),
        "top_neurons": [
            {
                "index": int(index),
                "abs_activation": round(float(score), 6),
                "activation": round(float(vector[int(index)].item()), 6),
            }
            for score, index in zip(top.values.tolist(), top.indices.tolist(), strict=False)
        ],
    }


def softmax_margin(logits: Any) -> float:
    probs = logits.float().softmax(dim=-1)
    top2 = probs.topk(2).values
    return round(float((top2[0] - top2[1]).item()), 6)


def compute_cas_axis_readout(evidence_payload: dict[str, Any], probe_weights_path: Path) -> dict[str, Any]:
    """Reject the legacy lossy-summary readout.

    Previous code concatenated absolute top-k magnitudes across scenarios and
    layers, discarded neuron identity/sign, and then called the result a hidden
    vector.  A linear readout over that representation is not the registered
    probe applied to the model state.  Until an independently replayable,
    full-width signed-vector artifact and layer/token contract are implemented,
    this output must remain absent.
    """

    weights, _snapshot = read_json_snapshot(
        probe_weights_path,
        label="CAS probe weights",
    )
    if weights.get("schema_version") != "cas_probe_linear_v1":
        raise RuntimeError("CAS probe weights must use schema_version=cas_probe_linear_v1.")
    if not evidence_payload.get("activation_summary"):
        raise RuntimeError("Cannot inspect probe compatibility without activation summary.")
    raise RuntimeError(
        "cas_probe_linear_v1 readout is disabled: layer_activation_summary is a "
        "lossy top-k diagnostic, not a full-width signed hidden-state vector. "
        "A separately sealed full-vector artifact and registered layer/token "
        "contract are required before cas_axis_readout can be emitted."
    )


def load_blindspot_cover_map(path: Path, *, model_id: str, model_revision: str) -> dict[str, Any]:
    payload, _snapshot = read_json_snapshot(path, label="blindspot cover map")
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "model_id",
        "model_revision",
        "covers",
    }:
        raise RuntimeError("Blindspot cover map has an unexpected keyset.")
    if payload.get("schema_version") != "cas_blindspot_cover_map.v1":
        raise RuntimeError("Blindspot cover map schema_version mismatch.")
    if payload.get("model_id") != model_id:
        raise RuntimeError("Blindspot cover map model_id does not match the audited model.")
    if payload.get("model_revision") != model_revision:
        raise RuntimeError("Blindspot cover map model_revision does not match the pinned model.")
    raise RuntimeError(
        "blindspot_overlay is disabled: no admitted typed cover schema currently "
        "binds per-cover coordinates, capture module, adapter identity, config bytes, "
        "and exact model-weight bytes"
    )


def classify_outputs(expected_outputs: tuple[str, ...], evidence_payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    unknown_outputs = sorted(set(expected_outputs) - KNOWN_OUTPUTS)
    if unknown_outputs:
        raise RuntimeError(f"unsupported expected_outputs: {unknown_outputs}")
    activation_rows = evidence_payload.get("activation_summary")
    activation_ready = (
        isinstance(activation_rows, list)
        and bool(activation_rows)
        and all(
            isinstance(row, dict)
            and isinstance(row.get("layers"), list)
            and bool(row["layers"])
            for row in activation_rows
        )
    )
    available = {
        "layer_activation_summary": activation_ready,
        "worker_evidence_manifest": True,
        "cas_axis_readout": "cas_axis_readout" in evidence_payload,
        "blindspot_overlay": "blindspot_overlay" in evidence_payload,
    }
    produced = [name for name in expected_outputs if available.get(name, False)]
    missing = [name for name in expected_outputs if name not in produced]
    return produced, missing


def load_scenarios_snapshot(
    config: ProbeShardConfig,
    *,
    after_read_hook: Callable[[], None] | None = None,
) -> tuple[list[ProbeScenario], dict[str, Any] | None]:
    scenarios: list[ProbeScenario] = []
    scenario_snapshot: dict[str, Any] | None = None
    if config.scenario_path is not None:
        payload, scenario_snapshot = read_json_snapshot(
            config.scenario_path,
            label="scenario file",
            after_read_hook=after_read_hook,
        )
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
    scenario_ids = [scenario.scenario_id for scenario in scenarios]
    if any(not scenario_id.strip() for scenario_id in scenario_ids):
        raise RuntimeError("Scenario IDs must be non-empty.")
    if len(scenario_ids) != len(set(scenario_ids)):
        raise RuntimeError("Scenario IDs must be unique.")
    return scenarios, scenario_snapshot


def load_scenarios(config: ProbeShardConfig) -> list[ProbeScenario]:
    scenarios, _snapshot = load_scenarios_snapshot(config)
    return scenarios


def resolve_torch_dtype(torch: Any, value: str) -> Any:
    normalized = (value or "auto").strip().lower()
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


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
