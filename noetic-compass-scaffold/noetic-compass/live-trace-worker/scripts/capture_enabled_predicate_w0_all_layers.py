"""Capture all prompt-stage W0 hidden-state layers for an enabled-predicate bank.

This script performs forward passes only. It does not generate completions and
does not label behavior from model output text. Labels are copied from an
existing judged/screened label JSONL when provided, or from expected behavior
metadata as a fallback for diagnostics.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_enabled_predicate_capture import (  # noqa: E402
    first_real_parameter_device,
    format_model_prompt,
    inference_context,
    load_model,
    load_prompt_bank,
)


SCHEMA_VERSION = "cas_harness_enabled_predicate_w0_all_layers_capture.v1"


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--prompt-bank", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--label-path", action="append", type=Path, default=[])
    parser.add_argument("--model-revision")
    parser.add_argument("--torch-dtype", default="float16")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--max-scenarios", type=int, default=0)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--prompt-format", choices=("chat-auto", "raw"), default="chat-auto")
    parser.add_argument("--layers", default="all", help="'all' or comma-separated hidden_states indices")
    parser.add_argument("--trust-remote-code", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = capture_w0_all_layers(
        model_id=args.model_id,
        prompt_bank_path=args.prompt_bank,
        output_dir=args.output_dir,
        label_paths=tuple(args.label_path),
        model_revision=args.model_revision,
        torch_dtype=args.torch_dtype,
        device_map=args.device_map,
        max_scenarios=args.max_scenarios,
        max_length=args.max_length,
        prompt_format=args.prompt_format,
        layers_arg=args.layers,
        trust_remote_code=args.trust_remote_code,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def capture_w0_all_layers(
    *,
    model_id: str,
    prompt_bank_path: Path,
    output_dir: Path,
    label_paths: tuple[Path, ...],
    model_revision: str | None,
    torch_dtype: str,
    device_map: str,
    max_scenarios: int,
    max_length: int,
    prompt_format: str,
    layers_arg: str,
    trust_remote_code: bool,
) -> dict[str, Any]:
    scenarios = load_prompt_bank(prompt_bank_path)
    if max_scenarios > 0:
        scenarios = scenarios[:max_scenarios]
    label_map = load_label_map(label_paths)
    model, tokenizer, model_info = load_model(
        model_id=model_id,
        model_revision=model_revision,
        torch_dtype=torch_dtype,
        device_map=device_map,
        trust_remote_code=trust_remote_code,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "enabled_predicate_w0_all_layers_dataset.npz"
    metadata_path = output_dir / "enabled_predicate_w0_all_layers_manifest.json"
    rows_path = output_dir / "enabled_predicate_w0_all_layers_rows.jsonl"

    features: list[np.ndarray] = []
    rows: list[dict[str, Any]] = []
    resolved_layers: list[int] | None = None
    for index, scenario in enumerate(scenarios, 1):
        model_prompt = format_model_prompt(
            tokenizer=tokenizer,
            prompt=str(scenario["prompt"]),
            prompt_format=prompt_format,
        )
        layer_vectors, layer_indices, token_count = capture_prompt_final_layers(
            model=model,
            tokenizer=tokenizer,
            prompt=model_prompt,
            max_length=max_length,
            layers_arg=layers_arg,
        )
        if resolved_layers is None:
            resolved_layers = layer_indices
        elif resolved_layers != layer_indices:
            raise RuntimeError(f"Layer set changed during capture: {resolved_layers} vs {layer_indices}")
        features.append(layer_vectors)
        scenario_id = str(scenario["id"])
        label = label_map.get(scenario_id) or label_map.get(f"{scenario_id}::capture")
        label_source = "label_jsonl" if label else "expected_behavior"
        if not label:
            label = str(scenario.get("expected_behavior") or "")
        row = {
            "trace_id": f"{scenario_id}::w0_all_layers",
            "scenario_id": scenario_id,
            "prompt_group_id": scenario.get("prompt_group_id", derive_prompt_group_id(scenario_id)),
            "payload_class": scenario.get("payload_class", ""),
            "domain": scenario.get("expected_cas_axes", {}).get("domain", ""),
            "prompt": scenario["prompt"],
            "model_prompt_format": prompt_format,
            "expected_behavior": scenario.get("expected_behavior", ""),
            "target_enabled_predicate": scenario.get("target_enabled_predicate", ""),
            "target_operator": scenario.get("target_operator", ""),
            "label": str(label),
            "label_source": label_source,
            "prompt_token_count": token_count,
        }
        rows.append(row)
        print(
            f"[w0-all-layers] {index}/{len(scenarios)} {scenario_id} "
            f"label={label} layers={len(layer_indices)} prompt_tokens={token_count}",
            flush=True,
        )

    if resolved_layers is None:
        raise RuntimeError("No rows captured.")
    write_npz(
        rows=rows,
        features=np.stack(features, axis=0).astype(np.float32),
        layers=np.asarray(resolved_layers, dtype=np.int64),
        path=dataset_path,
    )
    rows_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    summary = build_summary(
        rows=rows,
        model_id=model_id,
        model_revision=model_revision,
        model_info=model_info,
        prompt_bank_path=prompt_bank_path,
        label_paths=label_paths,
        prompt_format=prompt_format,
        dataset_path=dataset_path,
        metadata_path=metadata_path,
        rows_path=rows_path,
        layers=resolved_layers,
        max_length=max_length,
    )
    metadata_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[w0-all-layers] wrote {dataset_path}")
    print(f"[w0-all-layers] wrote {rows_path}")
    print(f"[w0-all-layers] wrote {metadata_path}")
    return summary


def capture_prompt_final_layers(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    max_length: int,
    layers_arg: str,
) -> tuple[np.ndarray, list[int], int]:
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
    token_count = int(inputs["input_ids"].shape[-1])
    device = first_real_parameter_device(model)
    if device is not None:
        inputs = {key: value.to(device) for key, value in inputs.items()}
    with inference_context():
        output = model(**inputs, use_cache=False, output_hidden_states=True, return_dict=True)
    hidden_states = getattr(output, "hidden_states", None)
    if hidden_states is None:
        raise RuntimeError("Model did not return hidden_states; cannot capture W0 layers.")
    layer_indices = parse_layers_arg(layers_arg, hidden_state_count=len(hidden_states))
    vectors = np.stack(
        [
            hidden_states[layer][0, -1].detach().float().cpu().numpy().astype(np.float32)
            for layer in layer_indices
        ],
        axis=0,
    )
    return vectors, layer_indices, token_count


def parse_layers_arg(layers_arg: str, *, hidden_state_count: int) -> list[int]:
    value = str(layers_arg or "all").strip().lower()
    if value == "all":
        return list(range(hidden_state_count))
    layers = [int(part.strip()) for part in value.split(",") if part.strip()]
    bad = [layer for layer in layers if layer < 0 or layer >= hidden_state_count]
    if bad:
        raise RuntimeError(f"Requested layers {bad} outside hidden_states range 0..{hidden_state_count - 1}.")
    if not layers:
        raise RuntimeError("No layers requested.")
    return layers


def load_label_map(paths: tuple[Path, ...]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for path in paths:
        if not path:
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                label = str(row.get("label") or "").strip()
                if not label:
                    continue
                for key_name in ("scenario_id", "prompt_id", "trace_id"):
                    key = str(row.get(key_name) or "").strip()
                    if key:
                        labels[key] = label
    return labels


def write_npz(*, rows: list[dict[str, Any]], features: np.ndarray, layers: np.ndarray, path: Path) -> None:
    np.savez_compressed(
        path,
        features=features,
        layers=layers,
        prompts=np.asarray([row["prompt"] for row in rows], dtype=object),
        scenario_ids=np.asarray([row["scenario_id"] for row in rows], dtype=object),
        trace_ids=np.asarray([row["trace_id"] for row in rows], dtype=object),
        axis_names=np.asarray(
            ["behavior", "expected_behavior", "payload_class", "domain", "target_operator"],
            dtype=object,
        ),
        labels_behavior=np.asarray([row["label"] for row in rows], dtype=object),
        labels_expected_behavior=np.asarray([row["expected_behavior"] for row in rows], dtype=object),
        labels_payload_class=np.asarray([row["payload_class"] for row in rows], dtype=object),
        labels_domain=np.asarray([row["domain"] for row in rows], dtype=object),
        labels_target_operator=np.asarray([row["target_operator"] for row in rows], dtype=object),
        labels_target_enabled_predicate=np.asarray(
            [row["target_enabled_predicate"] for row in rows],
            dtype=object,
        ),
        label_sources=np.asarray([row["label_source"] for row in rows], dtype=object),
        prompt_token_counts=np.asarray([row["prompt_token_count"] for row in rows], dtype=np.int64),
    )


def build_summary(
    *,
    rows: list[dict[str, Any]],
    model_id: str,
    model_revision: str | None,
    model_info: dict[str, Any],
    prompt_bank_path: Path,
    label_paths: tuple[Path, ...],
    prompt_format: str,
    dataset_path: Path,
    metadata_path: Path,
    rows_path: Path,
    layers: list[int],
    max_length: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "model_id": model_id,
        "model_revision": model_revision,
        "model_info": model_info,
        "prompt_bank": str(prompt_bank_path),
        "label_paths": [str(path) for path in label_paths],
        "prompt_format": prompt_format,
        "max_length": int(max_length),
        "row_count": int(len(rows)),
        "layers": [int(layer) for layer in layers],
        "layer_count": int(len(layers)),
        "feature_shape": [int(len(rows)), int(len(layers)), int(model_info.get("hidden_size") or 0)],
        "behavior_distribution": dict(sorted(Counter(row["label"] for row in rows).items())),
        "expected_behavior_distribution": dict(sorted(Counter(row["expected_behavior"] for row in rows).items())),
        "payload_class_distribution": dict(sorted(Counter(row["payload_class"] for row in rows).items())),
        "label_source_distribution": dict(sorted(Counter(row["label_source"] for row in rows).items())),
        "dataset": str(dataset_path),
        "rows": str(rows_path),
        "manifest": str(metadata_path),
        "claim": "OPEN / NOT LICENSED for pre-speech detection.",
        "important_limit": (
            "This is prompt-stage hidden-state capture only. It is not a detector, prevention claim, "
            "or causal proof until evaluated against text/layer-0 baselines and live steering gates."
        ),
    }


def derive_prompt_group_id(scenario_id: str) -> str:
    return str(scenario_id).split("::", 1)[0]


if __name__ == "__main__":
    raise SystemExit(main())
