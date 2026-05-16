"""Capture Pythia-160M activations for a chosen noetic-probe label JSONL."""

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


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--out-activations", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args(argv)

    labels_path = _resolve(args.labels)
    out_activations = _resolve(args.out_activations)
    out_manifest = _resolve(args.out_manifest)
    rows = _load_jsonl(labels_path)
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit(f"no rows loaded from {labels_path}")

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
    )
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
    X = np.zeros((len(rows), n_layers, hidden_dim), dtype=np.float32)
    y = np.zeros((len(rows),), dtype=np.int64)
    sample_ids: list[str] = []

    started = time.perf_counter()
    with torch.no_grad():
        for i, row in enumerate(rows):
            sample_ids.append(str(row["sample_id"]))
            y[i] = int(row["noetic_label"])
            encoded = tokenizer(
                row["english"],
                return_tensors="pt",
                truncation=True,
                max_length=256,
            ).to(args.device)
            outputs = model(**encoded)
            for layer_idx, hs in enumerate(outputs.hidden_states):
                X[i, layer_idx, :] = hs[0].mean(dim=0).cpu().float().numpy()
            if (i + 1) % 100 == 0 or i == len(rows) - 1:
                elapsed = time.perf_counter() - started
                rate = (i + 1) / max(elapsed, 1e-6)
                print(f"[{i + 1}/{len(rows)}] elapsed={elapsed:.1f}s rate={rate:.2f}/s")

    sample_ids_arr = np.array(sample_ids)
    if sample_ids_arr.dtype.kind != "U":
        raise SystemExit(f"sample_ids dtype must be fixed unicode, got {sample_ids_arr.dtype}")
    np.savez_compressed(out_activations, X=X, y=y, sample_ids=sample_ids_arr)

    manifest = {
        "schema_version": "pythia_probe_activations.v2",
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "device": args.device,
        "labels_file": labels_path.name,
        "labels_sha256": _sha256_of_file(labels_path),
        "n_records": int(len(rows)),
        "hidden_dim": hidden_dim,
        "n_layer_positions": n_layers,
        "pool_method": "mean_over_seq_len",
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
    with out_manifest.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    print(f"activations written: {out_activations}")
    print(f"manifest written: {out_manifest}")
    print(f"shape: X={X.shape} y={y.shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
