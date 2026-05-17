"""Capture Pythia-160M activations for Stage 11 expression-shape fixture."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from capture_stage6_role_bound_activations import (
    _MODEL_NAME,
    _find_focus_char_index,
    _find_token_for_char,
    _load_jsonl,
    _resolve,
    _sha256_of_file,
)


_SHAPE_LABELS = (
    "state_literal",
    "binary_composition",
    "let_binding",
    "recipe",
    "rpm_chain",
    "fractal_sequence",
    "cross_register_omega",
    "meta_logic_relation",
    "inversion",
    "diagram_export",
)
_LABEL_TO_INDEX = {label: i for i, label in enumerate(_SHAPE_LABELS)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-activations", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    out_activations = _resolve(args.out_activations)
    out_manifest = _resolve(args.out_manifest)
    rows = _load_jsonl(input_path)
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit(f"no rows loaded from {input_path}")

    try:
        import numpy as np
        import torch
        import transformers as transformers_pkg
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        print(f"missing dependency: {exc}", file=sys.stderr)
        return 2

    tokenizer = AutoTokenizer.from_pretrained(
        _MODEL_NAME,
        local_files_only=not args.allow_download,
        use_fast=True,
    )
    if not getattr(tokenizer, "is_fast", False):
        raise SystemExit("Stage 11 focus-token capture requires a fast tokenizer with offset mapping")
    model = AutoModel.from_pretrained(
        _MODEL_NAME,
        output_hidden_states=True,
        local_files_only=not args.allow_download,
    )
    model.eval()
    device = args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu"
    model.to(device)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    n_layers = int(model.config.num_hidden_layers) + 1
    hidden_dim = int(model.config.hidden_size)
    shape = (len(rows), n_layers, hidden_dim)
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
            label = str(row["shape_label"])
            if label not in _LABEL_TO_INDEX:
                raise ValueError(f"unknown shape_label {label!r} in {row['sample_id']}")
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
            for layer_idx, hs in enumerate(outputs.hidden_states):
                layer = hs[0]
                X_focus[i, layer_idx, :] = layer[focus_token_idx].cpu().float().numpy()
                X_final[i, layer_idx, :] = layer[final_token_idx].cpu().float().numpy()
                X_mean[i, layer_idx, :] = layer[:seq_len].mean(dim=0).cpu().float().numpy()

            if (i + 1) % 100 == 0 or i == len(rows) - 1:
                elapsed = time.perf_counter() - started
                rate = (i + 1) / max(elapsed, 1e-6)
                print(f"[{i + 1}/{len(rows)}] elapsed={elapsed:.1f}s rate={rate:.2f}/s")

    sample_ids_arr = np.array(sample_ids)
    label_names_arr = np.array(_SHAPE_LABELS)
    if sample_ids_arr.dtype.kind != "U":
        raise SystemExit(f"sample_ids dtype must be fixed unicode, got {sample_ids_arr.dtype}")
    np.savez_compressed(
        out_activations,
        X_focus=X_focus,
        X_final=X_final,
        X_mean=X_mean,
        y=y,
        label_names=label_names_arr,
        sample_ids=sample_ids_arr,
        focus_token_indices=focus_token_indices,
        final_token_indices=final_token_indices,
    )

    manifest = {
        "schema_version": "stage11_expression_shape_activations.v1",
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "device": device,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "n_records": int(len(rows)),
        "n_classes": len(_SHAPE_LABELS),
        "label_names": list(_SHAPE_LABELS),
        "hidden_dim": hidden_dim,
        "n_layer_positions": n_layers,
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
