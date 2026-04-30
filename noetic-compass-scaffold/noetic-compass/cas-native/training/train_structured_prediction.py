"""Local trainer/eval harness for the CAS Transformer structured-prediction head.

This module covers two modes:

* ``train_structured_prediction_smoke`` — full-batch overfit smoke for proving
  the head + ingest + loss path works end-to-end on a handful of records.
* ``train_structured_prediction_local`` — mini-batched, multi-epoch local
  train/eval harness over Level 3 training records with periodic evaluation
  against the strict held-out ``level3_recoverable_eval_1000.jsonl`` set,
  best-checkpoint tracking, per-bucket stratified metrics, and a manifest that
  is shape-compatible with the existing reranker eval reports so M2 deltas are
  directly comparable.

This is still a Step-7 harness. The text features are deterministic hashed
features (see ``text_features``); a real backbone embedding is the Step-10
upgrade. The harness exists to make the train/eval loop, eval discipline,
and manifest format concrete before any GPU spend.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import types
from pathlib import Path
from typing import Any, Iterable

import torch

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    package.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = package

from cas_native.model.structured_prediction import (
    META_RELATION_LABELS,
    REGISTER_LABELS,
    StructuredPredictionHead,
    structured_prediction_loss,
)
from cas_native.training.structured_prediction_ingest import (
    batch_targets_from_records,
    load_level3_jsonl,
)


DEFAULT_D_MODEL = 128


DISJOINTNESS_KEYS = ("id", "source_level2_id", "cas_expression")


def text_features(
    records: Iterable[dict[str, Any]],
    *,
    d_model: int = DEFAULT_D_MODEL,
    device: torch.device | str | None = None,
) -> torch.Tensor:
    """Map user prompts into deterministic hashed features for local smoke tests.

    Only ``user_prompt`` is included. Assistant responses contain the target
    CAS expression in the recoverable Level 3 corpora, so using them as input
    would turn held-out evaluation into answer leakage.
    """

    dev = torch.device(device) if device is not None else None
    rows: list[list[float]] = []
    for record in records:
        text = _record_text(record)
        features = [0.0] * d_model
        tokens = _tokens(text)
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            raw = int.from_bytes(digest, byteorder="little", signed=False)
            index = raw % d_model
            sign = 1.0 if ((raw >> 8) & 1) else -1.0
            features[index] += sign
        denom = max(1.0, sum(abs(value) for value in features) ** 0.5)
        rows.append([value / denom for value in features])
    return torch.tensor(rows, dtype=torch.float32, device=dev)


def train_structured_prediction_smoke(
    records: list[dict[str, Any]],
    *,
    d_model: int = DEFAULT_D_MODEL,
    bottleneck_dim: int = 64,
    steps: int = 25,
    lr: float = 0.01,
    device: torch.device | str = "cpu",
) -> tuple[StructuredPredictionHead, dict[str, float]]:
    """Train a tiny local head over deterministic features and return metrics."""

    if not records:
        raise ValueError("records must be non-empty")
    dev = torch.device(device)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim).to(dev)
    features = text_features(records, d_model=d_model, device=dev)
    targets = batch_targets_from_records(records, device=dev)
    optimizer = torch.optim.AdamW(head.parameters(), lr=lr)

    loss = torch.tensor(0.0, device=dev)
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        outputs = head(features)
        loss = structured_prediction_loss(outputs, targets)
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        outputs = head(features)
        metrics = structured_prediction_accuracy(outputs, targets)
        metrics["loss"] = float(structured_prediction_loss(outputs, targets).item())
        metrics["records"] = float(len(records))
    return head, metrics


_SCALAR_HEAD_PAIRS: tuple[tuple[str, str], ...] = (
    ("turn_type", "turn_type_logits"),
    ("expression_family", "expression_family_logits"),
    ("transition_kind", "transition_kind_logits"),
    ("noetic", "noetic_logits"),
    ("domain", "domain_logits"),
    ("drive", "drive_logits"),
    ("register_mode", "register_mode_logits"),
    ("authority", "authority_logits"),
    ("has_omega", "omega_logits"),
    ("has_meta_logic", "meta_logic_logits"),
)


def evaluate_structured_prediction(
    head: StructuredPredictionHead,
    records: list[dict[str, Any]],
    *,
    d_model: int,
    device: torch.device | str = "cpu",
    batch_size: int = 64,
) -> dict[str, Any]:
    """Run the held-out eval pass and return a manifest with per-sample,
    overall, and per-bucket metrics.

    The returned dict has shape::

        {
          "n": int,
          "all_heads_exact": int,
          "all_heads_exact_rate": float,
          "per_head_acc": {head_name: float, ...},
          "by_bucket": {bucket: {n, all_heads_exact, all_heads_exact_rate,
                                  per_head_acc}, ...},
          "samples": [
            {"id": ..., "bucket": ..., "all_heads_exact": bool,
             "head_correct": {head_name: bool, ...}}, ...
          ],
        }

    ``all_heads_exact`` is the strictest sample-level metric: every prediction
    head must match its target on the sample. Per-head accuracies are looser.
    Per-bucket stratification is mandatory because the held-out 1K is not
    evenly distributed (v75_register=262 vs v76_production=104).
    """

    if not records:
        raise ValueError("records must be non-empty to evaluate")

    dev = torch.device(device)
    head.eval()

    features_all = text_features(records, d_model=d_model, device=dev)
    targets_all = batch_targets_from_records(records, device=dev)

    n = len(records)
    logit_keys = [pair[1] for pair in _SCALAR_HEAD_PAIRS] + [
        "register_logits",
        "meta_relation_logits",
    ]
    chunks: dict[str, list[torch.Tensor]] = {key: [] for key in logit_keys}
    with torch.no_grad():
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch_features = features_all[start:end]
            batch_outputs = head(batch_features)
            for key in logit_keys:
                chunks[key].append(batch_outputs[key])
    outputs = {key: torch.cat(parts, dim=0) for key, parts in chunks.items()}

    # Per-sample boolean correctness per head.
    correct: dict[str, list[bool]] = {}
    for target_key, logit_key in _SCALAR_HEAD_PAIRS:
        if target_key in targets_all:
            preds = outputs[logit_key].argmax(dim=-1)
            correct[target_key] = (preds == targets_all[target_key]).cpu().tolist()
    if "registers" in targets_all:
        register_pred = (outputs["register_logits"].sigmoid() >= 0.5).to(
            targets_all["registers"].dtype
        )
        correct["registers"] = (
            (register_pred == targets_all["registers"]).all(dim=-1).cpu().tolist()
        )
    if "meta_relations" in targets_all:
        mr_pred = (outputs["meta_relation_logits"].sigmoid() >= 0.5).to(
            targets_all["meta_relations"].dtype
        )
        correct["meta_relations"] = (
            (mr_pred == targets_all["meta_relations"]).all(dim=-1).cpu().tolist()
        )

    head_keys = list(correct.keys())
    all_exact = [all(correct[key][i] for key in head_keys) for i in range(n)]

    samples: list[dict[str, Any]] = []
    for i, record in enumerate(records):
        samples.append(
            {
                "id": record.get("id"),
                "bucket": record.get("bucket"),
                "source_level2_id": record.get("source_level2_id"),
                "all_heads_exact": bool(all_exact[i]),
                "head_correct": {key: bool(correct[key][i]) for key in head_keys},
            }
        )

    bucket_indices: dict[str, list[int]] = {}
    for i, record in enumerate(records):
        bucket = str(record.get("bucket") or "unknown")
        bucket_indices.setdefault(bucket, []).append(i)

    by_bucket: dict[str, dict[str, Any]] = {}
    for bucket, idxs in sorted(bucket_indices.items()):
        n_b = len(idxs)
        bucket_exact = [all_exact[i] for i in idxs]
        per_head_acc = {
            key: sum(correct[key][i] for i in idxs) / n_b for key in head_keys
        }
        by_bucket[bucket] = {
            "n": n_b,
            "all_heads_exact": int(sum(bucket_exact)),
            "all_heads_exact_rate": sum(bucket_exact) / n_b,
            "per_head_acc": per_head_acc,
        }

    head.train()

    return {
        "n": n,
        "all_heads_exact": int(sum(all_exact)),
        "all_heads_exact_rate": sum(all_exact) / n,
        "per_head_acc": {key: sum(correct[key]) / n for key in head_keys},
        "by_bucket": by_bucket,
        "samples": samples,
    }


def train_structured_prediction_local(
    train_records: list[dict[str, Any]],
    eval_records: list[dict[str, Any]] | None,
    *,
    d_model: int = DEFAULT_D_MODEL,
    bottleneck_dim: int = 64,
    batch_size: int = 64,
    epochs: int = 3,
    eval_every_steps: int | None = None,
    lr: float = 1e-3,
    weight_decay: float = 0.0,
    seed: int = 42,
    device: torch.device | str = "cpu",
    out_dir: Path | None = None,
    progress_print: bool = True,
    filter_eval_overlaps: bool = True,
) -> tuple[StructuredPredictionHead, dict[str, Any]]:
    """Mini-batched, multi-epoch local train/eval harness.

    The training loop iterates ``epochs`` times over ``train_records`` in
    mini-batches of size ``batch_size``. After each epoch (and optionally every
    ``eval_every_steps`` gradient updates) we evaluate against ``eval_records``
    and track the best ``all_heads_exact_rate`` checkpoint. Final head state
    is the best-eval checkpoint, not the last-step checkpoint.

    ``out_dir`` writes ``manifest.json`` (config + per-eval history +
    final-eval block) and ``samples.jsonl`` (one row per held-out sample with
    per-head correctness) so the run is sample-aligned with the existing
    reranker eval reports.
    """

    if not train_records:
        raise ValueError("train_records must be non-empty")
    raw_train_count = len(train_records)
    overlap_report: dict[str, Any] = {
        "enabled": bool(filter_eval_overlaps and eval_records),
        "removed": 0,
        "by_key": {key: 0 for key in DISJOINTNESS_KEYS},
    }
    if eval_records and filter_eval_overlaps:
        train_records, overlap_report = filter_eval_overlapping_records(
            train_records,
            eval_records,
        )
        if not train_records:
            raise ValueError(
                "all train_records overlap eval_records by id/source_level2_id/"
                "cas_expression; provide a disjoint training split or disable "
                "filter_eval_overlaps only for debug"
            )

    torch.manual_seed(seed)
    rng = random.Random(seed)

    dev = torch.device(device)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim).to(dev)
    optimizer = torch.optim.AdamW(head.parameters(), lr=lr, weight_decay=weight_decay)

    train_features = text_features(train_records, d_model=d_model, device=dev)
    train_targets = batch_targets_from_records(train_records, device=dev)
    n_train = len(train_records)

    history: list[dict[str, Any]] = []
    best_eval: dict[str, Any] | None = None
    best_state: dict[str, torch.Tensor] | None = None
    global_step = 0

    def _maybe_eval(epoch_index: int, train_loss_avg: float) -> None:
        nonlocal best_eval, best_state
        if not eval_records:
            return
        snapshot = evaluate_structured_prediction(
            head,
            eval_records,
            d_model=d_model,
            device=dev,
            batch_size=batch_size,
        )
        snapshot_entry = {
            "epoch": epoch_index,
            "global_step": global_step,
            "train_loss_avg": train_loss_avg,
            "n_eval": snapshot["n"],
            "all_heads_exact": snapshot["all_heads_exact"],
            "all_heads_exact_rate": snapshot["all_heads_exact_rate"],
            "per_head_acc": dict(snapshot["per_head_acc"]),
            "by_bucket": {
                bucket: {
                    "n": entry["n"],
                    "all_heads_exact": entry["all_heads_exact"],
                    "all_heads_exact_rate": entry["all_heads_exact_rate"],
                    "per_head_acc": dict(entry["per_head_acc"]),
                }
                for bucket, entry in snapshot["by_bucket"].items()
            },
        }
        history.append(snapshot_entry)
        if (
            best_eval is None
            or snapshot["all_heads_exact_rate"] > best_eval["all_heads_exact_rate"]
        ):
            best_eval = snapshot
            best_state = {key: value.detach().clone() for key, value in head.state_dict().items()}
        if progress_print:
            print(
                json.dumps(
                    {
                        "event": "eval",
                        "epoch": epoch_index,
                        "step": global_step,
                        "train_loss_avg": round(train_loss_avg, 6),
                        "all_heads_exact": snapshot["all_heads_exact"],
                        "n_eval": snapshot["n"],
                        "rate": round(snapshot["all_heads_exact_rate"], 6),
                    },
                    sort_keys=True,
                )
            )

    indices = list(range(n_train))
    for epoch in range(epochs):
        rng.shuffle(indices)
        epoch_loss_total = 0.0
        epoch_batches = 0
        head.train()
        for batch_start in range(0, n_train, batch_size):
            batch_idx = indices[batch_start:batch_start + batch_size]
            idx_tensor = torch.tensor(batch_idx, dtype=torch.long, device=dev)
            batch_features = train_features.index_select(0, idx_tensor)
            batch_targets = {
                key: tensor.index_select(0, idx_tensor)
                for key, tensor in train_targets.items()
            }

            optimizer.zero_grad(set_to_none=True)
            outputs = head(batch_features)
            loss = structured_prediction_loss(outputs, batch_targets)
            loss.backward()
            optimizer.step()

            epoch_loss_total += float(loss.item())
            epoch_batches += 1
            global_step += 1

            if eval_every_steps and eval_records and global_step % eval_every_steps == 0:
                _maybe_eval(epoch, epoch_loss_total / max(epoch_batches, 1))

        avg_train_loss = epoch_loss_total / max(epoch_batches, 1)
        if progress_print:
            print(
                json.dumps(
                    {
                        "event": "epoch_end",
                        "epoch": epoch,
                        "step": global_step,
                        "train_loss_avg": round(avg_train_loss, 6),
                    },
                    sort_keys=True,
                )
            )
        _maybe_eval(epoch, avg_train_loss)

    if best_state is not None:
        head.load_state_dict(best_state)

    final_eval = best_eval if best_eval is not None else {}

    manifest = {
        "config": {
            "d_model": d_model,
            "bottleneck_dim": bottleneck_dim,
            "batch_size": batch_size,
            "epochs": epochs,
            "eval_every_steps": eval_every_steps,
            "lr": lr,
            "weight_decay": weight_decay,
            "seed": seed,
            "n_train": n_train,
            "n_train_raw": raw_train_count,
            "eval_overlap_filter": overlap_report,
            "n_eval": len(eval_records) if eval_records else 0,
        },
        "training": {
            "total_steps": global_step,
            "history": history,
        },
        "eval": {
            "n": final_eval.get("n", 0),
            "all_heads_exact": final_eval.get("all_heads_exact", 0),
            "all_heads_exact_rate": final_eval.get("all_heads_exact_rate", 0.0),
            "per_head_acc": dict(final_eval.get("per_head_acc", {})),
            "by_bucket": {
                bucket: {
                    "n": entry["n"],
                    "all_heads_exact": entry["all_heads_exact"],
                    "all_heads_exact_rate": entry["all_heads_exact_rate"],
                    "per_head_acc": dict(entry["per_head_acc"]),
                }
                for bucket, entry in final_eval.get("by_bucket", {}).items()
            },
        },
    }

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        torch.save(head.state_dict(), out_dir / "best_head.pt")
        if final_eval:
            with (out_dir / "samples.jsonl").open("w", encoding="utf-8") as f:
                for sample in final_eval.get("samples", []):
                    f.write(json.dumps(sample, sort_keys=True) + "\n")

    return head, manifest


def structured_prediction_accuracy(
    outputs: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
) -> dict[str, float]:
    """Compute per-head exact accuracy for scalar and multi-label heads."""

    metrics: dict[str, float] = {}
    scalar_pairs = {
        "turn_type": "turn_type_logits",
        "expression_family": "expression_family_logits",
        "transition_kind": "transition_kind_logits",
        "noetic": "noetic_logits",
        "domain": "domain_logits",
        "drive": "drive_logits",
        "register_mode": "register_mode_logits",
        "authority": "authority_logits",
        "has_omega": "omega_logits",
        "has_meta_logic": "meta_logic_logits",
    }
    for target_key, logit_key in scalar_pairs.items():
        if target_key in targets:
            pred = outputs[logit_key].argmax(dim=-1)
            metrics[f"{target_key}_acc"] = float((pred == targets[target_key]).float().mean().item())
    if "registers" in targets:
        pred = (outputs["register_logits"].sigmoid() >= 0.5).to(targets["registers"].dtype)
        metrics["register_exact_acc"] = float((pred == targets["registers"]).all(dim=-1).float().mean().item())
        metrics["register_label_count"] = float(len(REGISTER_LABELS))
    if "meta_relations" in targets:
        pred = (outputs["meta_relation_logits"].sigmoid() >= 0.5).to(targets["meta_relations"].dtype)
        metrics["meta_relation_exact_acc"] = float((pred == targets["meta_relations"]).all(dim=-1).float().mean().item())
        metrics["meta_relation_label_count"] = float(len(META_RELATION_LABELS))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Level 3 JSONL training records")
    parser.add_argument("--limit", type=int, default=128)
    parser.add_argument("--steps", type=int, default=25, help="Smoke-mode gradient steps")
    parser.add_argument("--d-model", type=int, default=DEFAULT_D_MODEL)
    parser.add_argument("--bottleneck-dim", type=int, default=64)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument(
        "--allow-heldout-train",
        action="store_true",
        help="Allow training on the held-out eval file for debug only.",
    )
    # Local train/eval harness flags. When --eval-input is supplied the runner
    # switches from smoke mode to the multi-epoch mini-batched harness.
    parser.add_argument(
        "--eval-input",
        default=None,
        help="Held-out eval JSONL. When set, runs the local train/eval harness "
        "instead of the smoke trainer. The held-out file is never used for "
        "training; the path guard rejects it as a training input.",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--eval-every-steps", type=int, default=None)
    parser.add_argument("--eval-limit", type=int, default=None)
    parser.add_argument(
        "--allow-eval-overlap",
        action="store_true",
        help="Debug only: do not filter training records that overlap the eval "
        "set by id/source_level2_id/cas_expression.",
    )
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory for manifest.json, best_head.pt, and samples.jsonl.",
    )
    args = parser.parse_args()

    path = Path(args.input)
    if _is_heldout_eval_path(path) and not args.allow_heldout_train:
        raise SystemExit(
            "Refusing to train on held-out eval data. Use a training JSONL or pass "
            "--allow-heldout-train for a throwaway debug smoke."
        )

    train_records = load_level3_jsonl(path, limit=args.limit)

    if args.eval_input is None:
        _head, metrics = train_structured_prediction_smoke(
            train_records,
            d_model=args.d_model,
            bottleneck_dim=args.bottleneck_dim,
            steps=args.steps,
            lr=args.lr,
        )
        print(json.dumps(metrics, indent=2, sort_keys=True))
        return

    eval_path = Path(args.eval_input)
    if not _is_heldout_eval_path(eval_path):
        # Soft warning: the eval-set discipline is to use the canonical
        # held-out file. Allow override but make it visible.
        print(
            json.dumps(
                {
                    "event": "warning",
                    "message": "eval_input does not look like the canonical held-out 1K eval set",
                    "eval_input": str(eval_path),
                },
                sort_keys=True,
            )
        )
    eval_records = load_level3_jsonl(eval_path, limit=args.eval_limit)

    out_dir = Path(args.out_dir) if args.out_dir else None
    _head, manifest = train_structured_prediction_local(
        train_records,
        eval_records,
        d_model=args.d_model,
        bottleneck_dim=args.bottleneck_dim,
        batch_size=args.batch_size,
        epochs=args.epochs,
        eval_every_steps=args.eval_every_steps,
        lr=args.lr,
        weight_decay=args.weight_decay,
        seed=args.seed,
        device=args.device,
        out_dir=out_dir,
        filter_eval_overlaps=not args.allow_eval_overlap,
    )
    summary = {
        "config": manifest["config"],
        "total_steps": manifest["training"]["total_steps"],
        "eval": {
            "n": manifest["eval"]["n"],
            "all_heads_exact": manifest["eval"]["all_heads_exact"],
            "all_heads_exact_rate": manifest["eval"]["all_heads_exact_rate"],
            "per_head_acc": manifest["eval"]["per_head_acc"],
            "by_bucket_summary": {
                bucket: {
                    "n": entry["n"],
                    "all_heads_exact": entry["all_heads_exact"],
                    "all_heads_exact_rate": entry["all_heads_exact_rate"],
                }
                for bucket, entry in manifest["eval"].get("by_bucket", {}).items()
            },
        },
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def _record_text(record: dict[str, Any]) -> str:
    return str(record.get("user_prompt") or "")


def filter_eval_overlapping_records(
    train_records: list[dict[str, Any]],
    eval_records: list[dict[str, Any]],
    *,
    keys: tuple[str, ...] = DISJOINTNESS_KEYS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Remove train records that overlap eval records on leakage-prone keys."""

    eval_values = {
        key: {
            record.get(key)
            for record in eval_records
            if record.get(key) not in (None, "")
        }
        for key in keys
    }
    kept: list[dict[str, Any]] = []
    by_key = {key: 0 for key in keys}
    removed = 0
    for record in train_records:
        matched = [
            key
            for key in keys
            if record.get(key) not in (None, "") and record.get(key) in eval_values[key]
        ]
        if matched:
            removed += 1
            for key in matched:
                by_key[key] += 1
            continue
        kept.append(record)
    return kept, {
        "enabled": True,
        "removed": removed,
        "by_key": by_key,
    }


def _tokens(text: str) -> list[str]:
    tokens = text.lower().replace("\n", " ").split()
    return tokens or ["<empty>"]


def _is_heldout_eval_path(path: Path) -> bool:
    return "level3_recoverable_eval_1000" in path.name


if __name__ == "__main__":
    main()
