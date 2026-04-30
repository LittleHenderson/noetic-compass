"""Train/eval runner for CAS Transformer structured prediction over backbone states.

This is the Step-10 comparison runner. It uses the same held-out discipline and
metrics as ``train_structured_prediction.py``, but replaces hashed prompt
features with pooled hidden states from ``CASNativeModel`` through
``CASBackboneStructuredPredictor``.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import types
from pathlib import Path
from typing import Any

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

from cas_native.model import CASNativeConfig, CASNativeModel, StructuredPredictionHead
from cas_native.model.structured_prediction import structured_prediction_loss
from cas_native.training.structured_backbone_adapter import (
    CASBackboneStructuredPredictor,
    records_to_backbone_batch,
)
from cas_native.training.structured_prediction_ingest import (
    batch_targets_from_records,
    load_level3_jsonl,
)
from cas_native.training.tokenizer import HybridCASTokenizer
from cas_native.training.train_structured_prediction import (
    _is_heldout_eval_path,
    evaluate_structured_prediction,
    filter_eval_overlapping_records,
)


def evaluate_backbone_structured_prediction(
    model: CASBackboneStructuredPredictor,
    records: list[dict[str, Any]],
    tokenizer: HybridCASTokenizer,
    *,
    device: torch.device | str = "cpu",
    batch_size: int = 32,
    max_length: int = 256,
) -> dict[str, Any]:
    """Evaluate the backbone-structured model with Step-7-compatible metrics."""

    if not records:
        raise ValueError("records must be non-empty to evaluate")

    dev = torch.device(device)
    model.eval()
    targets_all = batch_targets_from_records(records, device=dev)

    logit_keys = [
        "turn_type_logits",
        "expression_family_logits",
        "transition_kind_logits",
        "noetic_logits",
        "domain_logits",
        "drive_logits",
        "register_mode_logits",
        "authority_logits",
        "omega_logits",
        "meta_logic_logits",
        "register_logits",
        "meta_relation_logits",
    ]
    chunks: dict[str, list[torch.Tensor]] = {key: [] for key in logit_keys}
    with torch.no_grad():
        for start in range(0, len(records), batch_size):
            batch_records = records[start:start + batch_size]
            batch = records_to_backbone_batch(
                batch_records,
                tokenizer,
                max_length=max_length,
                device=dev,
            )
            outputs = model(batch.input_ids, attention_mask=batch.attention_mask)
            for key in logit_keys:
                chunks[key].append(outputs[key])
    outputs = {key: torch.cat(parts, dim=0) for key, parts in chunks.items()}

    # Reuse the hash-feature evaluator's exact metric logic by feeding it a
    # tiny shim head is brittle. Keep this implementation local and parallel.
    correct: dict[str, list[bool]] = {}
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
        pred = outputs[logit_key].argmax(dim=-1)
        correct[target_key] = (pred == targets_all[target_key]).cpu().tolist()

    register_pred = (outputs["register_logits"].sigmoid() >= 0.5).to(
        targets_all["registers"].dtype
    )
    correct["registers"] = (
        (register_pred == targets_all["registers"]).all(dim=-1).cpu().tolist()
    )
    meta_pred = (outputs["meta_relation_logits"].sigmoid() >= 0.5).to(
        targets_all["meta_relations"].dtype
    )
    correct["meta_relations"] = (
        (meta_pred == targets_all["meta_relations"]).all(dim=-1).cpu().tolist()
    )

    head_keys = list(correct.keys())
    all_exact = [all(correct[key][i] for key in head_keys) for i in range(len(records))]
    samples = [
        {
            "id": record.get("id"),
            "bucket": record.get("bucket"),
            "source_level2_id": record.get("source_level2_id"),
            "all_heads_exact": bool(all_exact[i]),
            "head_correct": {key: bool(correct[key][i]) for key in head_keys},
        }
        for i, record in enumerate(records)
    ]

    bucket_indices: dict[str, list[int]] = {}
    for i, record in enumerate(records):
        bucket_indices.setdefault(str(record.get("bucket") or "unknown"), []).append(i)

    by_bucket: dict[str, dict[str, Any]] = {}
    for bucket, idxs in sorted(bucket_indices.items()):
        n_b = len(idxs)
        exact_b = [all_exact[i] for i in idxs]
        by_bucket[bucket] = {
            "n": n_b,
            "all_heads_exact": int(sum(exact_b)),
            "all_heads_exact_rate": sum(exact_b) / n_b,
            "per_head_acc": {
                key: sum(correct[key][i] for i in idxs) / n_b for key in head_keys
            },
        }

    model.train()
    return {
        "n": len(records),
        "all_heads_exact": int(sum(all_exact)),
        "all_heads_exact_rate": sum(all_exact) / len(records),
        "per_head_acc": {key: sum(correct[key]) / len(records) for key in head_keys},
        "by_bucket": by_bucket,
        "samples": samples,
    }


def train_backbone_structured_local(
    train_records: list[dict[str, Any]],
    eval_records: list[dict[str, Any]] | None,
    *,
    tokenizer: HybridCASTokenizer,
    d_model: int = 64,
    n_layers: int = 1,
    n_heads: int = 4,
    bottleneck_dim: int = 32,
    batch_size: int = 16,
    epochs: int = 1,
    lr: float = 1e-3,
    weight_decay: float = 0.0,
    seed: int = 42,
    device: torch.device | str = "cpu",
    max_length: int = 128,
    freeze_backbone: bool = False,
    filter_eval_overlaps: bool = True,
    progress_print: bool = True,
    out_dir: Path | None = None,
) -> tuple[CASBackboneStructuredPredictor, dict[str, Any]]:
    """Train the structured head through CAS-Native pooled hidden states."""

    if not train_records:
        raise ValueError("train_records must be non-empty")

    raw_train_count = len(train_records)
    overlap_report: dict[str, Any] = {
        "enabled": bool(filter_eval_overlaps and eval_records),
        "removed": 0,
        "by_key": {"id": 0, "source_level2_id": 0, "cas_expression": 0},
    }
    if eval_records and filter_eval_overlaps:
        train_records, overlap_report = filter_eval_overlapping_records(
            train_records,
            eval_records,
        )
        if not train_records:
            raise ValueError("all train_records overlap eval_records")

    torch.manual_seed(seed)
    rng = random.Random(seed)
    dev = torch.device(device)
    config = CASNativeConfig(
        d_model=d_model,
        n_layers=n_layers,
        n_heads=n_heads,
        vocab_size=tokenizer.vocab_size,
        max_seq_len=max_length,
        fractal_depth=1,
        num_ethical_propositions=3,
        dropout=0.0,
    )
    backbone = CASNativeModel(config)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)
    model = CASBackboneStructuredPredictor(
        backbone,
        head,
        freeze_backbone=freeze_backbone,
    ).to(dev)
    optimizer = torch.optim.AdamW(
        [param for param in model.parameters() if param.requires_grad],
        lr=lr,
        weight_decay=weight_decay,
    )

    history: list[dict[str, Any]] = []
    best_eval: dict[str, Any] | None = None
    best_state: dict[str, torch.Tensor] | None = None
    global_step = 0

    def _eval(epoch: int, train_loss_avg: float) -> None:
        nonlocal best_eval, best_state
        if not eval_records:
            return
        snapshot = evaluate_backbone_structured_prediction(
            model,
            eval_records,
            tokenizer,
            device=dev,
            batch_size=batch_size,
            max_length=max_length,
        )
        history.append(
            {
                "epoch": epoch,
                "global_step": global_step,
                "train_loss_avg": train_loss_avg,
                "n_eval": snapshot["n"],
                "all_heads_exact": snapshot["all_heads_exact"],
                "all_heads_exact_rate": snapshot["all_heads_exact_rate"],
                "per_head_acc": dict(snapshot["per_head_acc"]),
                "by_bucket": {
                    bucket: {
                        "n": item["n"],
                        "all_heads_exact": item["all_heads_exact"],
                        "all_heads_exact_rate": item["all_heads_exact_rate"],
                        "per_head_acc": dict(item["per_head_acc"]),
                    }
                    for bucket, item in snapshot["by_bucket"].items()
                },
            }
        )
        if (
            best_eval is None
            or snapshot["all_heads_exact_rate"] > best_eval["all_heads_exact_rate"]
        ):
            best_eval = snapshot
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
        if progress_print:
            print(
                json.dumps(
                    {
                        "event": "eval",
                        "epoch": epoch,
                        "step": global_step,
                        "train_loss_avg": round(train_loss_avg, 6),
                        "all_heads_exact": snapshot["all_heads_exact"],
                        "n_eval": snapshot["n"],
                        "rate": round(snapshot["all_heads_exact_rate"], 6),
                    },
                    sort_keys=True,
                )
            )

    indices = list(range(len(train_records)))
    for epoch in range(epochs):
        rng.shuffle(indices)
        loss_total = 0.0
        batches = 0
        model.train()
        for start in range(0, len(train_records), batch_size):
            batch_indices = indices[start:start + batch_size]
            batch_records = [train_records[i] for i in batch_indices]
            batch = records_to_backbone_batch(
                batch_records,
                tokenizer,
                max_length=max_length,
                device=dev,
            )
            targets = batch_targets_from_records(batch_records, device=dev)
            optimizer.zero_grad(set_to_none=True)
            outputs = model(batch.input_ids, attention_mask=batch.attention_mask)
            loss = structured_prediction_loss(outputs, targets)
            loss.backward()
            optimizer.step()
            loss_total += float(loss.item())
            batches += 1
            global_step += 1
        avg_loss = loss_total / max(batches, 1)
        if progress_print:
            print(
                json.dumps(
                    {
                        "event": "epoch_end",
                        "epoch": epoch,
                        "step": global_step,
                        "train_loss_avg": round(avg_loss, 6),
                    },
                    sort_keys=True,
                )
            )
        _eval(epoch, avg_loss)

    if best_state is not None:
        model.load_state_dict({key: value.to(dev) for key, value in best_state.items()})
    final_eval = best_eval if best_eval is not None else {}

    manifest = {
        "config": {
            "mode": "backbone_structured_prediction",
            "d_model": d_model,
            "n_layers": n_layers,
            "n_heads": n_heads,
            "bottleneck_dim": bottleneck_dim,
            "batch_size": batch_size,
            "epochs": epochs,
            "lr": lr,
            "weight_decay": weight_decay,
            "seed": seed,
            "max_length": max_length,
            "freeze_backbone": freeze_backbone,
            "tokenizer": tokenizer.metadata(),
            "n_train_raw": raw_train_count,
            "n_train": len(train_records),
            "n_eval": len(eval_records) if eval_records else 0,
            "eval_overlap_filter": overlap_report,
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
                    "n": item["n"],
                    "all_heads_exact": item["all_heads_exact"],
                    "all_heads_exact_rate": item["all_heads_exact_rate"],
                    "per_head_acc": dict(item["per_head_acc"]),
                }
                for bucket, item in final_eval.get("by_bucket", {}).items()
            },
        },
    }

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        if final_eval:
            with (out_dir / "samples.jsonl").open("w", encoding="utf-8") as f:
                for sample in final_eval.get("samples", []):
                    f.write(json.dumps(sample, sort_keys=True) + "\n")
        torch.save(model.state_dict(), out_dir / "best_backbone_structured.pt")

    return model, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--eval-input", default=None)
    parser.add_argument("--limit", type=int, default=128)
    parser.add_argument("--eval-limit", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--n-layers", type=int, default=1)
    parser.add_argument("--n-heads", type=int, default=4)
    parser.add_argument("--bottleneck-dim", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--freeze-backbone", action="store_true")
    parser.add_argument("--allow-eval-overlap", action="store_true")
    parser.add_argument("--allow-heldout-train", action="store_true")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    if _is_heldout_eval_path(input_path) and not args.allow_heldout_train:
        raise SystemExit(
            "Refusing to train on held-out eval data. Use a training JSONL or "
            "pass --allow-heldout-train for throwaway debug only."
        )

    train_records = load_level3_jsonl(input_path, limit=args.limit)
    eval_records = (
        load_level3_jsonl(Path(args.eval_input), limit=args.eval_limit)
        if args.eval_input
        else None
    )
    tokenizer = HybridCASTokenizer.from_texts(
        [str(record.get("user_prompt") or "") for record in train_records],
        freeze=True,
    )

    out_dir = Path(args.out_dir) if args.out_dir else None
    _model, manifest = train_backbone_structured_local(
        train_records,
        eval_records,
        tokenizer=tokenizer,
        d_model=args.d_model,
        n_layers=args.n_layers,
        n_heads=args.n_heads,
        bottleneck_dim=args.bottleneck_dim,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        seed=args.seed,
        device=args.device,
        max_length=args.max_length,
        freeze_backbone=args.freeze_backbone,
        filter_eval_overlaps=not args.allow_eval_overlap,
        out_dir=out_dir,
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
                    "n": item["n"],
                    "all_heads_exact": item["all_heads_exact"],
                    "all_heads_exact_rate": item["all_heads_exact_rate"],
                }
                for bucket, item in manifest["eval"].get("by_bucket", {}).items()
            },
        },
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
