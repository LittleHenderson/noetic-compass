"""Capture Pythia activations for Stage 6 role-bound fixtures.

Unlike the older mean-pooled capture script, this stores three readouts:

- X_focus: residual stream at the focused A/B token
- X_final: residual stream at the final non-padding token
- X_mean: mean over the full sequence

Run from repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/capture_stage6_role_bound_activations.py \
      --input stage6_role_bound_pilot_20260516.jsonl \
      --out-activations stage6_role_bound_pilot_activations_20260516.npz \
      --out-manifest stage6_role_bound_pilot_activations_manifest_20260516.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _find_focus_char_index(text: str, expected_focus: str) -> int:
    marker = "Focus:"
    marker_idx = text.rfind(marker)
    if marker_idx < 0:
        raise ValueError(f"missing {marker!r} marker: {text!r}")
    tail = text[marker_idx + len(marker) :]
    rel_idx = tail.find(expected_focus)
    if rel_idx < 0:
        raise ValueError(f"focus {expected_focus!r} not found after marker in {text!r}")
    return marker_idx + len(marker) + rel_idx


def _find_token_for_char(offsets: list[tuple[int, int]], char_index: int) -> int:
    for i, (start, end) in enumerate(offsets):
        if start <= char_index < end:
            return i
    # Some tokenizers attach the focus letter to a whitespace-prefixed token
    # with a span starting one char earlier. Fall back to the nearest token.
    candidates = [
        (abs(start - char_index), i)
        for i, (start, end) in enumerate(offsets)
        if end > 0 and start <= char_index + 1
    ]
    if not candidates:
        raise ValueError(f"could not map char index {char_index} to token offsets")
    return min(candidates)[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Stage 6 JSONL fixture")
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
        raise SystemExit("Stage 6 focus-token capture requires a fast tokenizer with offset mapping")
    model = AutoModel.from_pretrained(
        _MODEL_NAME,
        output_hidden_states=True,
        local_files_only=not args.allow_download,
    )
    model.eval()
    model.to(args.device)
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
            encoded = encoded.to(args.device)
            outputs = model(**encoded)
            attention = encoded["attention_mask"][0]
            final_token_idx = int(torch.nonzero(attention, as_tuple=False)[-1].item())

            sample_ids.append(str(row["sample_id"]))
            y[i] = int(row["noetic_label"])
            focus_token_indices[i] = focus_token_idx
            final_token_indices[i] = final_token_idx
            seq_len = final_token_idx + 1
            for layer_idx, hs in enumerate(outputs.hidden_states):
                layer = hs[0]
                X_focus[i, layer_idx, :] = layer[focus_token_idx].cpu().float().numpy()
                X_final[i, layer_idx, :] = layer[final_token_idx].cpu().float().numpy()
                X_mean[i, layer_idx, :] = layer[:seq_len].mean(dim=0).cpu().float().numpy()

            if (i + 1) % 25 == 0 or i == len(rows) - 1:
                elapsed = time.perf_counter() - started
                rate = (i + 1) / max(elapsed, 1e-6)
                print(f"[{i + 1}/{len(rows)}] elapsed={elapsed:.1f}s rate={rate:.2f}/s")

    sample_ids_arr = np.array(sample_ids)
    if sample_ids_arr.dtype.kind != "U":
        raise SystemExit(f"sample_ids dtype must be fixed unicode, got {sample_ids_arr.dtype}")
    np.savez_compressed(
        out_activations,
        X_focus=X_focus,
        X_final=X_final,
        X_mean=X_mean,
        y=y,
        sample_ids=sample_ids_arr,
        focus_token_indices=focus_token_indices,
        final_token_indices=final_token_indices,
    )

    manifest = {
        "schema_version": "stage6_role_bound_activations.v1",
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "device": args.device,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "n_records": int(len(rows)),
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
