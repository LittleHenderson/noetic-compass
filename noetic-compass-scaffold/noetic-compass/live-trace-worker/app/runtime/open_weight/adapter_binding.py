"""Load the in-repository adapter verifier from one immutable byte snapshot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any, Mapping

from .contracts import ADAPTER_BINDING_STATUS, ADAPTER_CLAIM_BOUNDARY
from .identity import SnapshotAttestation, canonical_json_bytes


@dataclass(frozen=True)
class ExecutableAdapterBinding:
    plan: Mapping[str, object]
    plan_bytes: bytes
    plan_file_sha256: str
    adapter_source_sha256: str
    adapter_source_path: str
    residual_paths: tuple[str, ...]
    mlp_paths: tuple[str, ...]
    attention_paths: tuple[str | None, ...]
    config_projection: Mapping[str, object]

    def to_receipt_dict(self) -> dict[str, object]:
        return {
            "adapter_plan_sha256": self.plan["plan_sha256"],
            "adapter_plan_file_sha256": self.plan_file_sha256,
            "adapter_source_sha256": self.adapter_source_sha256,
            "adapter_source_path": self.adapter_source_path,
            "residual_paths": list(self.residual_paths),
            "mlp_paths": list(self.mlp_paths),
            "attention_paths": list(self.attention_paths),
            "config_projection": dict(self.config_projection),
            "binding_status": ADAPTER_BINDING_STATUS,
            "claim_boundary": ADAPTER_CLAIM_BOUNDARY,
        }


def build_executable_adapter_binding(
    *,
    model: Any,
    model_id: str,
    revision: str,
    snapshot: SnapshotAttestation,
    adapter_source_path: Path,
) -> ExecutableAdapterBinding:
    """Create and re-verify one adapter plan against the loaded model object."""

    adapter, source_sha256 = _load_module_from_exact_snapshot(adapter_source_path)
    config_projection = verify_loaded_model_config(snapshot, model)
    declaration = adapter.ArchitectureDeclaration(
        model_type=str(config_projection["model_type"]),
        num_hidden_layers=int(config_projection["num_hidden_layers"]),
        hidden_size=int(config_projection["hidden_size"]),
        num_attention_heads=int(config_projection["num_attention_heads"]),
    )
    plan_object = adapter.build_interpretability_adapter_plan(
        model=model,
        identity=adapter.ModelIdentity(
            model_id=model_id,
            revision=revision,
            config_sha256=snapshot.config_sha256,
            weights_manifest_sha256=snapshot.weights_manifest_sha256,
            trust_remote_code=False,
        ),
        declaration=declaration,
    )
    plan = plan_object.to_dict()
    adapter.verify_serialized_plan(plan)
    plan_bytes = canonical_json_bytes(plan)
    decoded = _strict_json(plan_bytes)
    adapter.verify_serialized_plan(decoded)

    identity = decoded["identity"]
    if identity["model_id"] != model_id or identity["revision"] != revision:
        raise RuntimeError("adapter plan model identity mismatch")
    if identity["config_sha256"] != snapshot.config_sha256:
        raise RuntimeError("adapter plan config-byte identity mismatch")
    if identity["weights_manifest_sha256"] != snapshot.weights_manifest_sha256:
        raise RuntimeError("adapter plan weight-byte manifest mismatch")

    hook_rows = decoded["discovery"]["layer_hooks"]
    residual_paths: list[str] = []
    mlp_paths: list[str] = []
    attention_paths: list[str | None] = []
    for layer_index, row in enumerate(hook_rows):
        residual = _required_hook_path(row, "residual_module", layer_index)
        mlp = _required_hook_path(row, "mlp_module", layer_index)
        attention = row.get("attention_module")
        if attention is not None and not isinstance(attention, str):
            raise RuntimeError("adapter attention hook path must be string or null")
        for label, path in (("residual", residual), ("MLP", mlp)):
            module = resolve_attr_path(model, path)
            if not callable(getattr(module, "register_forward_hook", None)):
                raise RuntimeError(
                    f"adapter {label} path is not hookable at layer {layer_index}"
                )
        if attention is not None:
            module = resolve_attr_path(model, attention)
            if not callable(getattr(module, "register_forward_hook", None)):
                raise RuntimeError(
                    f"adapter attention path is not hookable at layer {layer_index}"
                )
        residual_paths.append(residual)
        mlp_paths.append(mlp)
        attention_paths.append(attention)

    return ExecutableAdapterBinding(
        plan=decoded,
        plan_bytes=plan_bytes,
        plan_file_sha256=hashlib.sha256(plan_bytes).hexdigest().upper(),
        adapter_source_sha256=source_sha256,
        adapter_source_path=str(adapter_source_path),
        residual_paths=tuple(residual_paths),
        mlp_paths=tuple(mlp_paths),
        attention_paths=tuple(attention_paths),
        config_projection=config_projection,
    )


def verify_attested_config_projection(
    snapshot: SnapshotAttestation,
) -> dict[str, object]:
    """Strict-parse behavior-critical architecture fields from attested config bytes."""

    path = Path(snapshot.snapshot_root) / "config.json"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != snapshot.config_sha256:
        raise RuntimeError("config.json bytes differ from the snapshot attestation")
    value = _strict_json(raw)
    projection: dict[str, object] = {}
    positive_integer_keys = (
        "num_hidden_layers",
        "hidden_size",
        "num_attention_heads",
        "vocab_size",
        "max_position_embeddings",
        "intermediate_size",
        "rotary_emb_base",
    )
    nonnegative_integer_keys = ("bos_token_id", "eos_token_id")
    for key in (
        "model_type",
        *positive_integer_keys,
        *nonnegative_integer_keys,
        "hidden_act",
        "layer_norm_eps",
        "rotary_pct",
        "use_parallel_residual",
        "tie_word_embeddings",
        "initializer_range",
        "use_cache",
        "torch_dtype",
        "architectures",
    ):
        item = value.get(key)
        if key in {"model_type", "hidden_act", "torch_dtype"}:
            if not isinstance(item, str) or not item:
                raise RuntimeError(f"attested config {key} must be non-empty text")
        elif key in positive_integer_keys:
            if isinstance(item, bool) or not isinstance(item, int) or item <= 0:
                raise RuntimeError(f"attested config {key} must be a positive integer")
        elif key in nonnegative_integer_keys:
            if isinstance(item, bool) or not isinstance(item, int) or item < 0:
                raise RuntimeError(f"attested config {key} must be a non-negative integer")
        elif key in {"use_parallel_residual", "tie_word_embeddings", "use_cache"}:
            if not isinstance(item, bool):
                raise RuntimeError(f"attested config {key} must be boolean")
        elif key in {"layer_norm_eps", "rotary_pct", "initializer_range"}:
            if (
                isinstance(item, bool)
                or not isinstance(item, (int, float))
                or not (float("-inf") < float(item) < float("inf"))
                or float(item) <= 0
            ):
                raise RuntimeError(f"attested config {key} must be finite and positive")
            item = float(item)
        elif key == "architectures":
            if (
                not isinstance(item, list)
                or not item
                or not all(isinstance(name, str) and name for name in item)
            ):
                raise RuntimeError("attested config architectures must be non-empty text names")
        else:  # pragma: no cover - closed key list above
            raise RuntimeError(f"attested config {key} must be a positive integer")
        projection[key] = item
    return projection


def verify_loaded_model_config(
    snapshot: SnapshotAttestation, model: Any
) -> dict[str, object]:
    expected = verify_attested_config_projection(snapshot)
    config = model.config
    to_dict = getattr(config, "to_dict", None)
    normalized = to_dict() if callable(to_dict) else {}
    rope = normalized.get("rope_parameters")
    if not isinstance(rope, Mapping):
        rope = {}

    def observed_value(key: str) -> object:
        if key == "rotary_emb_base":
            direct = getattr(config, key, None)
            return direct if direct is not None else rope.get("rope_theta")
        if key == "rotary_pct":
            direct = getattr(config, key, None)
            return direct if direct is not None else rope.get("partial_rotary_factor")
        if key == "torch_dtype":
            direct = normalized.get("dtype", getattr(config, "torch_dtype", None))
            return str(direct).replace("torch.", "")
        if key in normalized:
            return normalized[key]
        return getattr(config, key, None)

    observed = {
        key: observed_value(key) for key in expected
    }
    if observed != expected:
        raise RuntimeError("loaded model config differs from attested config.json")
    return expected


def verify_bound_adapter_plan(
    *, plan_bytes: bytes, adapter_source_path: Path
) -> tuple[dict[str, object], str]:
    """Verify plan semantics with code compiled from the exact hashed source bytes."""

    plan = _strict_json(plan_bytes)
    adapter, source_sha256 = _load_module_from_exact_snapshot(adapter_source_path)
    adapter.verify_serialized_plan(plan)
    return plan, source_sha256


def resolve_attr_path(root: Any, dotted_path: str) -> Any:
    value = root
    for component in dotted_path.split("."):
        if not component:
            raise RuntimeError(f"empty adapter path component in {dotted_path!r}")
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


def _load_module_from_exact_snapshot(source_path: Path) -> tuple[Any, str]:
    if not source_path.is_absolute() or not source_path.is_file():
        raise RuntimeError("adapter source path must be an existing absolute file")
    raw = source_path.read_bytes()
    source_sha256 = hashlib.sha256(raw).hexdigest().upper()
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RuntimeError("adapter source must be strict UTF-8") from exc
    module_name = f"_cas_exact_adapter_{source_sha256.lower()}"
    module = types.ModuleType(module_name)
    module.__file__ = str(source_path)
    sys.modules[module_name] = module
    try:
        exec(compile(text, str(source_path), "exec"), module.__dict__)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    if hashlib.sha256(raw).hexdigest().upper() != source_sha256:
        raise RuntimeError("adapter source snapshot changed in memory")
    return module, source_sha256


def _required_hook_path(row: object, field: str, layer_index: int) -> str:
    if not isinstance(row, Mapping):
        raise RuntimeError(f"adapter hook row {layer_index} must be an object")
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"adapter hook row {layer_index} lacks {field}")
    return value


def _strict_json(raw: bytes) -> dict[str, object]:
    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number is forbidden: {value}")

    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=pairs_hook,
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("adapter plan must be a JSON object")
    return value
