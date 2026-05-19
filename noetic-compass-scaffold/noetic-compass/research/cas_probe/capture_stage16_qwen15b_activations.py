"""Capture Qwen2.5-1.5B activations for Stage 16 cross-architecture replication.

This mirrors the Stage 15 capture but uses ``Qwen/Qwen2.5-1.5B`` and stores
only the pre-registered candidate layer positions 8 through 28.
The full binary is intentionally git-ignored; commit the manifest and SHA-256.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from capture_stage6_role_bound_activations import (
    _find_focus_char_index,
    _find_token_for_char,
    _load_jsonl,
    _resolve,
    _sha256_of_file,
)


_MODEL_NAME = "Qwen/Qwen2.5-1.5B"
_REGISTERS = ("T", "A", "f", "E")
_LABELS = tuple(f"F{drive}{register}" for drive in range(1, 8) for register in _REGISTERS)
_LABEL_TO_INDEX = {label: i for i, label in enumerate(_LABELS)}


def _parse_layer_positions(spec: str) -> list[int]:
    positions: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_s, end_s = chunk.split("-", 1)
            start = int(start_s)
            end = int(end_s)
            if end < start:
                raise ValueError(f"bad descending layer range: {chunk!r}")
            positions.extend(range(start, end + 1))
        else:
            positions.append(int(chunk))
    out = sorted(set(positions))
    if not out:
        raise ValueError("no layer positions parsed")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--out-activations", default="stage16_qwen15b_activations_20260519.npz")
    parser.add_argument("--out-manifest", default="stage16_qwen15b_activations_manifest_20260519.json")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--layers", default="8-28", help="Layer positions to store, e.g. 8-28 or 12,20,28")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    out_activations = _resolve(args.out_activations)
    out_manifest = _resolve(args.out_manifest)
    layer_positions = _parse_layer_positions(str(args.layers))
    rows = _load_jsonl(input_path)
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit(f"no rows loaded from {input_path}")

    try:
        import numpy as np
        import torch
        import transformers as transformers_pkg
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        print(f"missing dependency: {exc}", file=sys.stderr)
        return 2

    tokenizer = AutoTokenizer.from_pretrained(
        _MODEL_NAME,
        local_files_only=not args.allow_download,
        use_fast=True,
    )
    if not getattr(tokenizer, "is_fast", False):
        raise SystemExit("Stage 16 focus-token capture requires a fast tokenizer with offset mapping")
    model = AutoModelForCausalLM.from_pretrained(
        _MODEL_NAME,
        output_hidden_states=True,
        local_files_only=not args.allow_download,
    )
    model.eval()
    device = args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu"
    model.to(device)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    n_hidden_positions = int(model.config.num_hidden_layers) + 1
    bad_layers = [pos for pos in layer_positions if pos < 0 or pos >= n_hidden_positions]
    if bad_layers:
        raise SystemExit(f"layer positions outside available 0..{n_hidden_positions - 1}: {bad_layers}")
    hidden_dim = int(model.config.hidden_size)
    shape = (len(rows), len(layer_positions), hidden_dim)
    X_focus = np.zeros(shape, dtype=np.float32)
    X_final = np.zeros(shape, dtype=np.float32)
    X_mean = np.zeros(shape, dtype=np.float32)
    y = np.zeros((len(rows),), dtype=np.int64)
    focus_token_indices = np.zeros((len(rows),), dtype=np.int64)
    final_token_indices = np.zeros((len(rows),), dtype=np.int64)
    sample_ids: list[str] = []

    started = time.perf_counter()
    with torch.no_grad():
        for i, row in enumerate(rows):
            text = str(row["english"])
            focus = str(row["focus_span"])
            label = str(row["foundation_label"])
            if label not in _LABEL_TO_INDEX:
                raise ValueError(f"unknown foundation_label {label!r} in {row['sample_id']}")
            focus_char_index = _find_focus_char_index(text, focus)
            encoded = tokenizer(
                text,
                return_tensors="pt",
                return_offsets_mapping=True,
                truncation=True,
                max_length=256,
            )
            offsets = [(int(a), int(b)) for a, b in encoded.pop("offset_mapping")[0].tolist()]
            focus_token_idx = _find_token_for_char(offsets, focus_char_index)
            encoded = encoded.to(device)
            outputs = model(**encoded)
            attention = encoded["attention_mask"][0]
            final_token_idx = int(torch.nonzero(attention, as_tuple=False)[-1].item())

            sample_ids.append(str(row["sample_id"]))
            y[i] = int(_LABEL_TO_INDEX[label])
            focus_token_indices[i] = focus_token_idx
            final_token_indices[i] = final_token_idx
            seq_len = final_token_idx + 1
            for out_pos, layer_idx in enumerate(layer_positions):
                layer = outputs.hidden_states[layer_idx][0]
                X_focus[i, out_pos, :] = layer[focus_token_idx].cpu().float().numpy()
                X_final[i, out_pos, :] = layer[final_token_idx].cpu().float().numpy()
                X_mean[i, out_pos, :] = layer[:seq_len].mean(dim=0).cpu().float().numpy()

            if (i + 1) % 50 == 0 or i == len(rows) - 1:
                elapsed = time.perf_counter() - started
                rate = (i + 1) / max(elapsed, 1e-6)
                print(f"[{i + 1}/{len(rows)}] elapsed={elapsed:.1f}s rate={rate:.2f}/s")

    sample_ids_arr = np.array(sample_ids)
    label_names_arr = np.array(_LABELS)
    layer_positions_arr = np.array(layer_positions, dtype=np.int64)
    if sample_ids_arr.dtype.kind != "U":
        raise SystemExit(f"sample_ids dtype must be fixed unicode, got {sample_ids_arr.dtype}")
    np.savez_compressed(
        out_activations,
        X_focus=X_focus,
        X_final=X_final,
        X_mean=X_mean,
        y=y,
        label_names=label_names_arr,
        layer_positions=layer_positions_arr,
        sample_ids=sample_ids_arr,
        focus_token_indices=focus_token_indices,
        final_token_indices=final_token_indices,
    )

    manifest = {
        "schema_version": "stage16_qwen15b_foundation_activations.v1",
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "device": device,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "n_records": int(len(rows)),
        "n_classes": len(_LABELS),
        "label_names": list(_LABELS),
        "hidden_dim": hidden_dim,
        "n_available_layer_positions": n_hidden_positions,
        "stored_layer_positions": layer_positions,
        "readouts": ["focus_token", "final_token", "mean_over_seq_len"],
        "max_tokens": 256,
        "sample_ids_dtype": str(sample_ids_arr.dtype),
        "package_versions": {
            "transformers": getattr(transformers_pkg, "__version__", "unknown"),
            "torch": getattr(torch, "__version__", "unknown"),
            "numpy": np.__version__,
        },
        "elapsed_seconds": time.perf_counter() - started,
        "output_file": out_activations.name,
        "output_sha256": _sha256_of_file(out_activations),
    }
    out_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"activations written: {out_activations}")
    print(f"manifest written: {out_manifest}")
    print(f"shape: X_focus={X_focus.shape} X_final={X_final.shape} X_mean={X_mean.shape} y={y.shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
