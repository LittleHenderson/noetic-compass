"""Stage 5.x - original-TKS-style noetic transfer eval.

This script evaluates the saved Pythia-160M noetic probe on a
hand-authored fixture derived from original TKS noetic semantics. It
does not train anything new.

Why this eval exists:

* The probe-training snapshot was synthetic/CAS-derived English.
* The transfer examples are original-TKS-style semantic examples.
* Passing this transfer set would show the saved noetic probe can
  recognize clean external TKS semantics, not only the snapshot style.

This is a small semantic smoke, not a statistical benchmark.

Run:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/evaluate_tks_dog_noetics.py

Optional:

    python .../evaluate_tks_dog_noetics.py \
      --fixture tks_dog_training_noetic_eval_20260516.jsonl \
      --out-report tks_dog_training_noetic_eval_report_20260516.json
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
_TRAIN_DATE = "20260515"
_EVAL_DATE = "20260516"

_MODEL_NAME = "EleutherAI/pythia-160m"
_DEFAULT_FIXTURE = _HERE / f"tks_noetic_transfer_eval_{_EVAL_DATE}.jsonl"
_SNAPSHOT_LABELS = _HERE / f"pythia_probe_labels_{_TRAIN_DATE}.jsonl"
_PROBES_PATH = _HERE / f"pythia_noetic_probes_{_TRAIN_DATE}.npz"
_DEFAULT_OUT_REPORT = _HERE / f"tks_noetic_transfer_eval_report_{_EVAL_DATE}.json"

_HEADLINE_LAYER = 3
_NOETIC_LABELS = {
    0: "Idea",
    1: "Mind",
    2: "Positive",
    3: "Negative",
    4: "Vibration",
    5: "Female",
    6: "Male",
    7: "Rhythm",
    8: "Above/Cause",
    9: "Below/Effect",
}


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


def _resolve_local_path(value: str, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    if not path.is_absolute():
        path = _HERE / path
    return path


def _softmax(x: "np.ndarray") -> "np.ndarray":
    import numpy as np

    shifted = x - np.max(x)
    exps = np.exp(shifted)
    return exps / np.sum(exps)


def _top_k(logits: "np.ndarray", k: int = 3) -> list[dict[str, Any]]:
    import numpy as np

    probs = _softmax(logits)
    idx = np.argsort(probs)[::-1][:k]
    return [
        {
            "label": int(i),
            "name": _NOETIC_LABELS[int(i)],
            "probability": float(probs[int(i)]),
        }
        for i in idx
    ]


def _capture_pythia(rows: list[dict[str, Any]], device: str, local_files_only: bool) -> tuple["np.ndarray", dict[str, Any]]:
    try:
        import numpy as np
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        print(
            f"missing dependency: {exc}\n  pip install transformers torch numpy",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    tokenizer = AutoTokenizer.from_pretrained(
        _MODEL_NAME,
        local_files_only=local_files_only,
    )
    model = AutoModel.from_pretrained(
        _MODEL_NAME,
        output_hidden_states=True,
        local_files_only=local_files_only,
    )
    model.eval()
    model.to(device)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    n_layers = int(model.config.num_hidden_layers) + 1
    hidden_dim = int(model.config.hidden_size)
    X = np.zeros((len(rows), n_layers, hidden_dim), dtype=np.float32)

    started = time.perf_counter()
    with torch.no_grad():
        for i, row in enumerate(rows):
            encoded = tokenizer(
                row["english"],
                return_tensors="pt",
                truncation=True,
                max_length=256,
            ).to(device)
            outputs = model(**encoded)
            for layer_idx, hs in enumerate(outputs.hidden_states):
                X[i, layer_idx, :] = hs[0].mean(dim=0).cpu().float().numpy()

    manifest = {
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "device": device,
        "local_files_only": local_files_only,
        "n_layer_positions": n_layers,
        "hidden_dim": hidden_dim,
        "pool_method": "mean_over_seq_len",
        "max_tokens": 256,
        "elapsed_seconds": time.perf_counter() - started,
    }
    return X, manifest


def _apply_saved_probe(
    X: "np.ndarray",
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import numpy as np

    if not _PROBES_PATH.is_file():
        raise SystemExit(f"missing saved probe artifact: {_PROBES_PATH}")
    probes = np.load(_PROBES_PATH, allow_pickle=False)
    coefs = probes["coefs"]
    intercepts = probes["intercepts"]
    scaler_mean = probes["scaler_mean"]
    scaler_scale = probes["scaler_scale"]

    per_layer: list[dict[str, Any]] = []
    per_row_layer3: list[dict[str, Any]] = []
    y = np.array([int(r["canonical_noetic"]) for r in rows], dtype=np.int64)

    for layer in range(X.shape[1]):
        scale = np.where(scaler_scale[layer] == 0.0, 1.0, scaler_scale[layer])
        Xs = (X[:, layer, :] - scaler_mean[layer]) / scale
        logits = Xs @ coefs[layer].T + intercepts[layer]
        pred = np.argmax(logits, axis=1).astype(np.int64)
        accuracy = float(np.mean(pred == y))
        per_layer.append(
            {
                "layer": layer,
                "accuracy": accuracy,
                "correct": int(np.sum(pred == y)),
                "total": int(len(y)),
            }
        )
        if layer == _HEADLINE_LAYER:
            for i in range(len(y)):
                per_row_layer3.append(
                    {
                        "sample_id": str(rows[i]["sample_id"]),
                        "english": str(rows[i]["english"]),
                        "gold": int(y[i]),
                        "gold_name": _NOETIC_LABELS[int(y[i])],
                        "predicted": int(pred[i]),
                        "predicted_name": _NOETIC_LABELS[int(pred[i])],
                        "correct": bool(pred[i] == y[i]),
                        "top3": _top_k(logits[i], k=3),
                    }
                )

    return per_layer, per_row_layer3


def _text_baselines(rows: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        import numpy as np
        from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
    except ImportError as exc:
        print(
            f"missing dependency: {exc}\n  pip install scikit-learn numpy",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    snapshot = _load_jsonl(_SNAPSHOT_LABELS)
    probes = np.load(_PROBES_PATH, allow_pickle=False)
    idx_train = probes["idx_train"]
    train_text = np.array([r["english"] for r in snapshot], dtype=object)[idx_train]
    train_y = np.array([int(r["noetic_label"]) for r in snapshot], dtype=np.int64)[idx_train]
    eval_text = [r["english"] for r in rows]
    eval_y = np.array([int(r["canonical_noetic"]) for r in rows], dtype=np.int64)

    outputs: dict[str, Any] = {}
    for name, vectorizer in {
        "count_vector_logreg": CountVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
        ),
        "tfidf_logreg": TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
        ),
    }.items():
        X_train = vectorizer.fit_transform(train_text)
        X_eval = vectorizer.transform(eval_text)
        clf = LogisticRegression(
            solver="lbfgs",
            max_iter=2000,
            class_weight="balanced",
            random_state=42,
        )
        clf.fit(X_train, train_y)
        pred = clf.predict(X_eval).astype(np.int64)
        outputs[name] = {
            "accuracy": float(np.mean(pred == eval_y)),
            "correct": int(np.sum(pred == eval_y)),
            "total": int(len(eval_y)),
            "predictions": [
                {
                    "sample_id": rows[i]["sample_id"],
                    "gold": int(eval_y[i]),
                    "gold_name": _NOETIC_LABELS[int(eval_y[i])],
                    "predicted": int(pred[i]),
                    "predicted_name": _NOETIC_LABELS[int(pred[i])],
                    "correct": bool(pred[i] == eval_y[i]),
                }
                for i in range(len(rows))
            ],
        }
    return outputs


def _accuracy_by_field(
    predictions: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    row_by_id = {str(row["sample_id"]): row for row in rows}
    buckets: dict[str, list[bool]] = {}
    for pred in predictions:
        row = row_by_id[pred["sample_id"]]
        key = str(row.get(field, "unknown"))
        buckets.setdefault(key, []).append(bool(pred["correct"]))
    return {
        key: {
            "correct": int(sum(vals)),
            "total": len(vals),
            "accuracy": float(sum(vals) / len(vals)) if vals else 0.0,
        }
        for key, vals in sorted(buckets.items())
    }


def _verdict(layer3_accuracy: float, count_accuracy: float, tfidf_accuracy: float) -> str:
    best_text = max(count_accuracy, tfidf_accuracy)
    if layer3_accuracy >= 0.8 and layer3_accuracy > best_text:
        return "TKS_NOETIC_TRANSFER_STRONG_BUT_TINY_N"
    if layer3_accuracy >= 0.7:
        return "TKS_NOETIC_TRANSFER_PASSED_TINY_N"
    if layer3_accuracy > 0.3:
        return "TKS_NOETIC_TRANSFER_MIXED"
    return "TKS_NOETIC_TRANSFER_WEAK"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument(
        "--fixture",
        default=str(_DEFAULT_FIXTURE),
        help="JSONL transfer fixture. Relative paths resolve inside research/cas_probe.",
    )
    parser.add_argument(
        "--out-report",
        default=str(_DEFAULT_OUT_REPORT),
        help="Output report JSON. Relative paths resolve inside research/cas_probe.",
    )
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Allow Hugging Face to download Pythia files if not already cached.",
    )
    args = parser.parse_args(argv)

    fixture_path = _resolve_local_path(args.fixture, _DEFAULT_FIXTURE)
    out_report = _resolve_local_path(args.out_report, _DEFAULT_OUT_REPORT)
    rows = _load_jsonl(fixture_path)
    if not rows:
        raise SystemExit(f"no rows loaded from {fixture_path}")

    labels = [int(r["canonical_noetic"]) for r in rows]
    if sorted(set(labels)) != list(range(10)):
        raise SystemExit(f"expected coverage of noetics 0..9, got {sorted(set(labels))}")

    X, capture_manifest = _capture_pythia(
        rows,
        device=args.device,
        local_files_only=not args.allow_download,
    )
    per_layer, layer3_rows = _apply_saved_probe(X, rows)
    text = _text_baselines(rows)

    layer3 = next(r for r in per_layer if r["layer"] == _HEADLINE_LAYER)
    count_acc = text["count_vector_logreg"]["accuracy"]
    tfidf_acc = text["tfidf_logreg"]["accuracy"]
    report = {
        "schema_version": "tks_noetic_transfer_eval.v1",
        "experiment": "Original-TKS-style noetic transfer eval",
        "status": "research_only_tiny_n_semantic_smoke",
        "fixture_file": fixture_path.name,
        "fixture_sha256": _sha256_of_file(fixture_path),
        "probe_file": _PROBES_PATH.name,
        "probe_sha256": _sha256_of_file(_PROBES_PATH),
        "n_records": len(rows),
        "headline_layer": _HEADLINE_LAYER,
        "capture": capture_manifest,
        "caveats": [
            "This is a small hand-authored semantic transfer smoke, not a statistical benchmark.",
            "Rows with source=definition_anchored_hand_authored are not quoted source text; they are canonical semantic fixtures built from the authoritative TKS/CAS noetic definitions.",
            "Strong performance here would support transfer to original-TKS-style examples, but does not by itself prove mechanistic encoding.",
        ],
        "layer3_probe_accuracy": layer3["accuracy"],
        "best_layer": max(per_layer, key=lambda r: r["accuracy"]),
        "text_baselines": {
            "count_vector_logreg_accuracy": count_acc,
            "tfidf_logreg_accuracy": tfidf_acc,
        },
        "verdict": _verdict(layer3["accuracy"], count_acc, tfidf_acc),
        "per_layer": per_layer,
        "layer3_predictions": layer3_rows,
        "layer3_accuracy_by_scenario": _accuracy_by_field(
            layer3_rows,
            rows,
            "scenario_id",
        ),
        "layer3_accuracy_by_noetic": _accuracy_by_field(
            layer3_rows,
            rows,
            "canonical_label",
        ),
        "text_baseline_predictions": text,
        "fixture_rows": rows,
    }

    with out_report.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    print(f"headline layer {_HEADLINE_LAYER}: {layer3['correct']}/{layer3['total']} = {layer3['accuracy']:.3f}")
    print(f"best layer: {report['best_layer']}")
    print(f"count baseline: {count_acc:.3f}")
    print(f"tfidf baseline: {tfidf_acc:.3f}")
    print(f"verdict: {report['verdict']}")
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
