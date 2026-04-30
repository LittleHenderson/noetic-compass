"""Eval-only entry point for the semantic reranker against a held-out file.

Loads a saved ``semantic_reranker.pt`` checkpoint and the tokenizer used at
training time, builds candidate banks from a training corpus (NOT from the
held-out file — that would leak), and evaluates the reranker on every record
in ``--eval-input`` using the same ``evaluate()`` function the trainer uses
for in-loop eval.

Output shape matches the existing trainer eval artifacts so M2 comparisons can
read the same JSON keys (``eval_summary.json`` and ``samples.jsonl``).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import types
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(REPO_ROOT / "cas-native")]
sys.modules.setdefault("cas_native", pkg)
sys.path.insert(0, str(REPO_ROOT))

import torch  # noqa: E402

from cas_native.inference.semantic_reranker import load_semantic_reranker  # noqa: E402
from cas_native.inference.train_semantic_reranker import (  # noqa: E402
    BUCKETS,
    build_candidate_banks,
    evaluate,
    record_bucket,
    records_by_bucket,
)
from cas_native.training.data_pipeline import load_cas_data  # noqa: E402
from cas_native.training.tokenizer import HybridCASTokenizer  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", required=True, type=Path,
                   help="Training corpus (used for candidate-bank construction).")
    p.add_argument("--tokenizer", required=True, type=Path)
    p.add_argument("--checkpoint", required=True, type=Path,
                   help="Path to a semantic_reranker.pt produced by the trainer.")
    p.add_argument("--eval-input", required=True, type=Path,
                   help="JSONL file of held-out eval records.")
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--max-candidates", type=int, default=5000)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--min-filter-candidates", type=int, default=1)
    p.add_argument("--device",
                   default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--eval-limit", type=int, default=None,
                   help="Optional cap on the number of eval records (debug only).")
    return p.parse_args()


def _load_eval_records(path: Path, limit: int | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
            if limit is not None and len(out) >= limit:
                break
    return out


def _filter_candidate_source_records(
    train_records: list[dict[str, Any]],
    eval_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Exclude eval-overlapping records before candidate-bank construction."""

    keys = ("id", "source_level2_id", "cas_expression")
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
    return kept, {"removed": removed, "by_key": by_key}


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    started = time.time()

    print("[1/5] Loading tokenizer + training corpus + held-out eval records...")
    tokenizer = HybridCASTokenizer.load(args.tokenizer)
    train_records = load_cas_data(args.dataset)
    eval_records = _load_eval_records(args.eval_input, args.eval_limit)
    if not eval_records:
        raise SystemExit(f"no eval records loaded from {args.eval_input}")
    filtered_train_records, overlap_filter = _filter_candidate_source_records(
        train_records,
        eval_records,
    )
    print(
        f"      records={len(train_records)} filtered={len(filtered_train_records)} "
        f"eval={len(eval_records)} vocab={tokenizer.vocab_size} device={device}"
    )
    if not filtered_train_records:
        raise SystemExit(
            "candidate source records were exhausted after eval-overlap filtering"
        )

    print("[2/5] Building candidate banks from filtered training corpus...")
    candidate_banks = build_candidate_banks(
        filtered_train_records,
        max_candidates=args.max_candidates,
    )
    for bucket in BUCKETS:
        print(f"      {bucket}: {len(candidate_banks[bucket])} candidates")

    print("[3/5] Loading checkpoint...")
    model, metadata = load_semantic_reranker(args.checkpoint, device=device)
    eval_buckets = records_by_bucket(eval_records)
    for bucket in BUCKETS:
        print(f"      {bucket} eval n={len(eval_buckets.get(bucket, []))}")

    print(f"[4/5] Evaluating on {len(eval_records)} held-out records...")
    samples, summary = evaluate(
        model,
        tokenizer,
        eval_records,
        candidate_banks,
        device=device,
        batch_size=args.batch_size,
        min_filter_candidates=args.min_filter_candidates,
    )

    wall_clock = time.time() - started

    print("[5/5] Writing artifacts...")
    with (args.out_dir / "samples.jsonl").open("w", encoding="utf-8") as f:
        for row in samples:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (args.out_dir / "eval_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    metrics = {
        "mode": "eval_only_on_heldout",
        "dataset": str(args.dataset),
        "tokenizer": str(args.tokenizer),
        "checkpoint": str(args.checkpoint),
        "eval_input": str(args.eval_input),
        "eval_record_count": len(eval_records),
        "candidate_source_record_count_raw": len(train_records),
        "candidate_source_record_count_filtered": len(filtered_train_records),
        "candidate_source_overlap_filter": overlap_filter,
        "candidate_bank_sizes": {b: len(candidate_banks[b]) for b in BUCKETS},
        "device": str(device),
        "batch_size": args.batch_size,
        "min_filter_candidates": args.min_filter_candidates,
        "max_candidates": args.max_candidates,
        "wall_clock_seconds": wall_clock,
        "checkpoint_metadata": {k: v for k, v in metadata.items()
                                 if isinstance(v, (str, int, float, bool, type(None)))},
    }
    (args.out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"      exact={summary['n_exact_match']}/{summary['n_total']} "
        f"top5={summary['n_ground_truth_top5']}/{summary['n_total']} "
        f"mean_rank={summary['mean_ground_truth_rank']:.4f} "
        f"wall_clock={wall_clock:.1f}s out={args.out_dir}"
    )


if __name__ == "__main__":
    main()
