"""Capture Pythia-160M hidden states for each English description in the
frozen probe snapshot.

For each English description, the script:

1. Tokenizes the description.
2. Runs a forward pass through Pythia-160M with ``output_hidden_states=True``.
3. Captures the **mean-pooled hidden state** at each transformer layer
   (12 hidden layers for Pythia-160M, plus the embedding layer = 13 total).
4. Records the per-layer activation vectors plus the noetic label.
5. Dumps a single ``.npz`` archive with arrays sized
   ``(N_records, N_layers, hidden_dim)`` for X and ``(N_records,)`` for y.

Why mean-pool: the simplest input for a linear probe is one vector per
prompt per layer. Last-token-only would also work; mean-pool is more
stable for short prompts. Stage 2 can re-try with last-token if mean-pool
underperforms.

This script is research-only, governed by the README guardrails. Pythia
weights are downloaded to the Hugging Face cache (default
``~/.cache/huggingface/``) and never copied into the production stack.

Usage (after installing transformers + downloading Pythia):

    pip install "transformers>=4.40"
    python noetic-compass-scaffold/noetic-compass/research/cas_probe/capture_pythia_activations.py

A ``--smoke`` flag runs the capture over just the first N records for a
fast sanity check before doing the full 458-record run.

    python ...capture_pythia_activations.py --smoke 10
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_TODAY = "20260515"
_LABELS_PATH = _HERE / f"pythia_probe_labels_{_TODAY}.jsonl"
_OUT_ACTIVATIONS = _HERE / f"pythia_probe_activations_{_TODAY}.npz"
_OUT_RUN_MANIFEST = _HERE / f"pythia_probe_activations_manifest_{_TODAY}.json"

_MODEL_NAME = "EleutherAI/pythia-160m"


def _load_snapshot() -> list[dict[str, Any]]:
    if not _LABELS_PATH.is_file():
        raise SystemExit(
            f"missing frozen snapshot: {_LABELS_PATH}\n"
            f"  run build_pythia_probe_snapshot.py first."
        )
    rows: list[dict[str, Any]] = []
    with _LABELS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke",
        type=int,
        default=0,
        help="If >0, run only the first N records as a sanity check.",
    )
    parser.add_argument(
        "--device",
        choices=("cpu", "cuda"),
        default="cpu",
        help="Device to run Pythia on. CPU is fine for 160M.",
    )
    args = parser.parse_args(argv)

    # Lazy imports so the script fails with a clear message if transformers
    # is not installed.
    try:
        import numpy as np
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        print(
            f"missing dependency: {exc}\n"
            f"  pip install 'transformers>=4.40' numpy torch",
            file=sys.stderr,
        )
        return 2

    rows = _load_snapshot()
    if args.smoke > 0:
        rows = rows[: args.smoke]

    print(f"loading tokenizer + model: {_MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
    model = AutoModel.from_pretrained(_MODEL_NAME, output_hidden_states=True)
    model.eval()
    model.to(args.device)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    config = model.config
    hidden_dim = config.hidden_size
    n_hidden_layers = config.num_hidden_layers
    # Hidden states from HF include the embedding layer at index 0, so
    # there are n_hidden_layers + 1 total positions.
    n_layer_positions = n_hidden_layers + 1
    print(
        f"model loaded: hidden_dim={hidden_dim} "
        f"n_layers={n_hidden_layers} (capturing {n_layer_positions} positions including embedding)"
    )

    N = len(rows)
    X = np.zeros((N, n_layer_positions, hidden_dim), dtype=np.float32)
    y = np.zeros((N,), dtype=np.int64)
    sample_ids: list[str] = []

    started = time.perf_counter()
    with torch.no_grad():
        for i, row in enumerate(rows):
            text = row["english"]
            sample_ids.append(row["sample_id"])
            y[i] = int(row["noetic_label"])

            encoded = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=256,
            ).to(args.device)
            outputs = model(**encoded)
            # outputs.hidden_states is a tuple of length n_layer_positions.
            # Each entry is shape (1, seq_len, hidden_dim). Mean-pool over
            # the seq_len dimension, masking padding (we use no padding
            # here because we encode one prompt at a time).
            for layer_idx, hs in enumerate(outputs.hidden_states):
                X[i, layer_idx, :] = hs[0].mean(dim=0).cpu().float().numpy()

            if (i + 1) % 50 == 0 or i == N - 1:
                elapsed = time.perf_counter() - started
                rate = (i + 1) / max(elapsed, 1e-6)
                print(
                    f"  [{i + 1}/{N}] elapsed={elapsed:.1f}s "
                    f"rate={rate:.2f}/s eta={(N - i - 1) / max(rate, 1e-6):.0f}s"
                )

    np.savez_compressed(
        _OUT_ACTIVATIONS,
        X=X,
        y=y,
        sample_ids=np.array(sample_ids, dtype=object),
    )

    manifest = {
        "schema_version": "pythia_probe_activations.v1",
        "model_name": _MODEL_NAME,
        "device": args.device,
        "snapshot_used": _LABELS_PATH.name,
        "n_records": N,
        "smoke_only": args.smoke > 0,
        "hidden_dim": int(hidden_dim),
        "n_layer_positions": int(n_layer_positions),
        "pool_method": "mean_over_seq_len",
        "tokenizer_pad_token": tokenizer.pad_token,
        "max_tokens": 256,
        "elapsed_seconds": time.perf_counter() - started,
        "output_file": _OUT_ACTIVATIONS.name,
    }
    with _OUT_RUN_MANIFEST.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    print(f"activations written: {_OUT_ACTIVATIONS}")
    print(f"run manifest: {_OUT_RUN_MANIFEST}")
    print(f"shape: X={X.shape} y={y.shape}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
