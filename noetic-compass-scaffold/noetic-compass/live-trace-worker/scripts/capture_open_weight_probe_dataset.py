"""Capture real hidden vectors for open-weight CAS probe training.

This is the missing piece between "we ran a 20B forward pass" and "we can
train/evaluate a CAS probe on 20B." It writes raw pooled hidden vectors to NPZ
instead of only top-neuron summaries, so downstream probe tests can use heldout
splits and controls without rerunning the model.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_dataset_common import label_distributions, load_labeled_scenarios  # noqa: E402
from run_open_weight_probe_shard import (  # noqa: E402
    count_parameters,
    first_real_parameter_device,
    inference_context,
    locate_transformer_layers,
    resolve_torch_dtype,
    select_assigned_layers,
)


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--scenario-path", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata-output", type=Path)
    parser.add_argument("--model-revision")
    parser.add_argument("--torch-dtype", default="float16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--layer-start", type=int, default=0)
    parser.add_argument("--layer-end", type=int)
    parser.add_argument("--max-scenarios", type=int, default=0)
    parser.add_argument("--max-length", type=int, default=192)
    parser.add_argument("--trust-remote-code", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scenarios = load_labeled_scenarios(args.scenario_path)
    if args.max_scenarios > 0:
        scenarios = scenarios[: args.max_scenarios]
    model, tokenizer, model_info = load_model(args)
    layer_modules = locate_transformer_layers(model)
    layer_end = args.layer_end if args.layer_end is not None else len(layer_modules) - 1
    selected_layers = select_assigned_layers(layer_modules, args.layer_start, layer_end)
    features = []
    token_counts: list[int] = []
    for index, scenario in enumerate(scenarios, start=1):
        vectors, token_count = capture_vectors(
            model=model,
            tokenizer=tokenizer,
            prompt=scenario.prompt,
            selected_layers=selected_layers,
            max_length=args.max_length,
        )
        features.append(vectors)
        token_counts.append(token_count)
        print(
            f"[capture] {index}/{len(scenarios)} {scenario.scenario_id} "
            f"tokens={token_count} layers={vectors.shape[0]}",
            flush=True,
        )
    feature_array = np.stack(features, axis=0).astype(np.float16)
    layers = np.asarray([idx for idx, _layer in selected_layers], dtype=np.int16)
    axis_names = sorted({axis for scenario in scenarios for axis in scenario.labels})
    np_payload: dict[str, Any] = {
        "features": feature_array,
        "layers": layers,
        "scenario_ids": np.asarray([s.scenario_id for s in scenarios], dtype="U128"),
        "prompts": np.asarray([s.prompt for s in scenarios], dtype=object),
        "token_counts": np.asarray(token_counts, dtype=np.int32),
        "axis_names": np.asarray(axis_names, dtype="U32"),
    }
    for axis in axis_names:
        np_payload[f"labels_{axis}"] = np.asarray(
            [scenario.labels.get(axis, "") for scenario in scenarios],
            dtype="U64",
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **np_payload)
    metadata = {
        "schema_version": "cas_harness_open_weight_probe_dataset.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "model_id": args.model_id,
        "model_revision": args.model_revision,
        "model_info": model_info,
        "scenario_path": str(args.scenario_path),
        "scenario_count": len(scenarios),
        "layers": layers.tolist(),
        "hidden_size": int(feature_array.shape[-1]),
        "feature_shape": list(feature_array.shape),
        "label_distributions": label_distributions(scenarios),
        "output": str(args.output),
        "important_limit": "This is a raw activation dataset, not a CAS verdict.",
    }
    metadata_path = args.metadata_output or args.output.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[capture] wrote {args.output}")
    print(f"[capture] wrote {metadata_path}")
    return 0


def load_model(args: Any) -> tuple[Any, Any, dict[str, Any]]:
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

    dtype = resolve_torch_dtype(torch, args.torch_dtype)
    model_config = AutoConfig.from_pretrained(
        args.model_id,
        revision=args.model_revision,
        trust_remote_code=args.trust_remote_code,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_id,
        revision=args.model_revision,
        trust_remote_code=args.trust_remote_code,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        revision=args.model_revision,
        torch_dtype=dtype,
        device_map=args.device_map,
        low_cpu_mem_usage=True,
        trust_remote_code=args.trust_remote_code,
    )
    model.eval()
    return model, tokenizer, {
        "architectures": list(getattr(model_config, "architectures", []) or []),
        "model_type": getattr(model_config, "model_type", None),
        "hidden_size": getattr(model_config, "hidden_size", None),
        "num_hidden_layers": getattr(model_config, "num_hidden_layers", None),
        "num_attention_heads": getattr(model_config, "num_attention_heads", None),
        "vocab_size": getattr(model_config, "vocab_size", None),
        "torch_dtype": str(dtype) if dtype is not None else "auto",
        "device_map": args.device_map,
        "parameter_count": count_parameters(model),
    }


def capture_vectors(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    selected_layers: list[tuple[int, Any]],
    max_length: int,
) -> tuple[np.ndarray, int]:
    captures: dict[int, Any] = {}
    handles = []
    try:
        for layer_idx, layer in selected_layers:
            module = getattr(layer, "mlp", layer)
            handles.append(module.register_forward_hook(_capture_last_token(captures, layer_idx)))
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
        token_count = int(inputs["input_ids"].shape[-1])
        device = first_real_parameter_device(model)
        if device is not None:
            inputs = {key: value.to(device) for key, value in inputs.items()}
        with inference_context():
            model(**inputs, use_cache=False)
    finally:
        for handle in handles:
            handle.remove()
    missing = [layer_idx for layer_idx, _layer in selected_layers if layer_idx not in captures]
    if missing:
        raise RuntimeError(f"Missing activation captures for layers: {missing}")
    vectors = np.stack([captures[layer_idx].numpy() for layer_idx, _layer in selected_layers], axis=0)
    return vectors.astype(np.float16), token_count


def _capture_last_token(captures: dict[int, Any], layer_idx: int):
    def hook(_module: Any, _inputs: Any, output: Any) -> None:
        value = output[0] if isinstance(output, tuple) else output
        captures[layer_idx] = value[0, -1].detach().float().cpu()

    return hook


if __name__ == "__main__":
    raise SystemExit(main())
