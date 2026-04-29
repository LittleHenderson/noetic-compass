"""Train and evaluate a prompt-candidate semantic reranker.

This is the next layer after grammar-constrained decoding: candidate banks keep
the compiler-valid guarantee, while this scorer learns which valid candidate
best matches the prompt.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import types
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
if not REPO_ROOT.exists():
    REPO_ROOT = Path(__file__).resolve().parents[2]
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(REPO_ROOT / "cas-native")]
sys.modules.setdefault("cas_native", pkg)
sys.path.insert(0, str(REPO_ROOT))

import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

from api.notation import compile_expression  # noqa: E402
from cas_native.inference.constrained_sampling import (  # noqa: E402
    BUCKETS,
    build_dataset_candidate_expressions,
    candidate_matches_required_terms,
    candidate_matches_slot_policy,
    candidate_matches_slots,
    expression_families,
    expression_slots,
    filter_candidates_for_prompt,
    infer_prompt_families,
    infer_prompt_required_terms,
    infer_prompt_slot_policies,
    infer_prompt_slots,
)
from cas_native.inference.semantic_reranker import (  # noqa: E402
    SemanticReranker,
    SemanticRerankerConfig,
    encode_text_batch,
    save_semantic_reranker,
    score_candidates,
)
from cas_native.training.data_pipeline import load_cas_data  # noqa: E402
from cas_native.training.tokenizer import HybridCASTokenizer  # noqa: E402


@dataclass(frozen=True)
class TrainingPair:
    bucket: str
    prompt: str
    positive: str
    negative: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--tokenizer", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--train-records", type=int, default=8000)
    p.add_argument("--eval-per-bucket", type=int, default=5)
    p.add_argument("--max-candidates", type=int, default=5000)
    p.add_argument("--negatives-per-positive", type=int, default=4)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--d-model", type=int, default=192)
    p.add_argument("--hidden-dim", type=int, default=384)
    p.add_argument("--dropout", type=float, default=0.10)
    p.add_argument("--min-filter-candidates", type=int, default=1)
    return p.parse_args()


def prompt_text(record: dict[str, Any]) -> str:
    return str(record.get("prompt") or record.get("user_prompt") or "").strip()


def target_expression(record: dict[str, Any]) -> str:
    return str(record.get("cas_expression") or "").strip()


def record_bucket(record: dict[str, Any]) -> str:
    meta = record.get("_meta")
    if isinstance(meta, dict) and meta.get("bucket"):
        return str(meta["bucket"])
    return str(record.get("bucket") or "")


def format_generation_prompt(prompt: str) -> str:
    return f"[TASK_EXPR] [PROMPT] {prompt} [RESPONSE]".strip()


def records_by_bucket(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        bucket = record_bucket(record)
        if bucket in BUCKETS:
            by_bucket[str(bucket)].append(record)
    return by_bucket


def choose_eval_records(
    by_bucket: dict[str, list[dict[str, Any]]],
    *,
    per_bucket: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    for bucket in BUCKETS:
        bucket_records = by_bucket.get(bucket, [])
        if len(bucket_records) >= per_bucket:
            out.extend(rng.sample(bucket_records, per_bucket))
    return out


def build_candidate_banks(
    records: list[dict[str, Any]],
    *,
    max_candidates: int,
) -> dict[str, tuple[str, ...]]:
    return {
        bucket: build_dataset_candidate_expressions(
            records,
            bucket,
            max_candidates=max_candidates,
            include_builtin=True,
        )
        for bucket in BUCKETS
    }


def filtered_candidates(
    bank: tuple[str, ...],
    prompt: str,
    bucket: str,
    *,
    min_candidates: int,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    candidates, diagnostics = filter_candidates_for_prompt(
        bank,
        prompt,
        bucket,
        min_candidates=min_candidates,
    )
    return candidates, diagnostics


def make_training_pairs(
    records: list[dict[str, Any]],
    candidate_banks: dict[str, tuple[str, ...]],
    eval_records: list[dict[str, Any]],
    *,
    train_records: int,
    negatives_per_positive: int,
    min_filter_candidates: int,
    seed: int,
) -> tuple[list[TrainingPair], dict[str, Any]]:
    rng = random.Random(seed)
    eval_ids = {id(record) for record in eval_records}
    pairs: list[TrainingPair] = []
    diagnostics = {
        "eligible_records": 0,
        "skipped_eval_records": 0,
        "skipped_no_prompt_or_target": 0,
        "skipped_bucket": 0,
        "skipped_target_not_scoreable": 0,
        "per_bucket_pairs": defaultdict(int),
    }

    for record in records:
        if id(record) in eval_ids:
            diagnostics["skipped_eval_records"] += 1
            continue
        if len(pairs) >= train_records * negatives_per_positive:
            break
        bucket = record_bucket(record)
        if bucket not in BUCKETS:
            diagnostics["skipped_bucket"] += 1
            continue
        prompt = prompt_text(record)
        target = target_expression(record)
        if not prompt or not target:
            diagnostics["skipped_no_prompt_or_target"] += 1
            continue
        candidates, _ = filtered_candidates(
            candidate_banks[str(bucket)],
            prompt,
            str(bucket),
            min_candidates=min_filter_candidates,
        )
        if target not in candidates:
            diagnostics["skipped_target_not_scoreable"] += 1
            continue
        negatives = [candidate for candidate in candidates if candidate != target]
        if not negatives:
            diagnostics["skipped_target_not_scoreable"] += 1
            continue
        diagnostics["eligible_records"] += 1
        for _ in range(negatives_per_positive):
            negative = rng.choice(negatives)
            pairs.append(
                TrainingPair(
                    bucket=str(bucket),
                    prompt=format_generation_prompt(prompt),
                    positive=target,
                    negative=negative,
                )
            )
            diagnostics["per_bucket_pairs"][str(bucket)] += 1

    diagnostics["per_bucket_pairs"] = dict(diagnostics["per_bucket_pairs"])
    return pairs, diagnostics


def train_one_epoch(
    model: SemanticReranker,
    tokenizer: HybridCASTokenizer,
    pairs: list[TrainingPair],
    *,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    batch_size: int,
    rng: random.Random,
) -> dict[str, float]:
    rng.shuffle(pairs)
    model.train()
    losses: list[float] = []
    accuracies: list[float] = []
    for start in range(0, len(pairs), batch_size):
        batch = pairs[start : start + batch_size]
        prompts = [pair.prompt for pair in batch]
        positives = [pair.positive for pair in batch]
        negatives = [pair.negative for pair in batch]

        prompt_ids, prompt_mask = encode_text_batch(
            tokenizer,
            prompts,
            device=device,
            max_length=192,
            add_special=False,
        )
        pos_ids, pos_mask = encode_text_batch(
            tokenizer,
            positives,
            device=device,
            max_length=192,
            add_special=False,
        )
        neg_ids, neg_mask = encode_text_batch(
            tokenizer,
            negatives,
            device=device,
            max_length=192,
            add_special=False,
        )

        pos_scores = model(prompt_ids, prompt_mask, pos_ids, pos_mask)
        neg_scores = model(prompt_ids, prompt_mask, neg_ids, neg_mask)
        loss = F.softplus(neg_scores - pos_scores).mean()

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        with torch.no_grad():
            accuracies.append(float((pos_scores > neg_scores).float().mean().item()))
            losses.append(float(loss.item()))

    return {
        "loss": sum(losses) / max(len(losses), 1),
        "pairwise_accuracy": sum(accuracies) / max(len(accuracies), 1),
        "batches": float(len(losses)),
    }


def rank_diagnostics(scored: list[dict[str, Any]], target: str) -> dict[str, Any]:
    if not scored:
        return {
            "ground_truth_scoreable": False,
            "ground_truth_rank": None,
            "ground_truth_top1": False,
            "ground_truth_top5": False,
        }
    for idx, item in enumerate(scored, start=1):
        if item["candidate"] == target:
            return {
                "ground_truth_scoreable": True,
                "ground_truth_rank": idx,
                "ground_truth_rank_percentile": idx / max(len(scored), 1),
                "ground_truth_top1": idx == 1,
                "ground_truth_top5": idx <= 5,
                "ground_truth_semantic_score": item["semantic_score"],
                "best_semantic_score": scored[0]["semantic_score"],
                "score_margin": scored[0]["semantic_score"] - item["semantic_score"],
            }
    return {
        "ground_truth_scoreable": False,
        "ground_truth_rank": None,
        "ground_truth_top1": False,
        "ground_truth_top5": False,
    }


def compile_valid(expr: str) -> bool:
    try:
        return bool(compile_expression(expr).valid)
    except Exception:
        return False


def evaluate(
    model: SemanticReranker,
    tokenizer: HybridCASTokenizer,
    eval_records: list[dict[str, Any]],
    candidate_banks: dict[str, tuple[str, ...]],
    *,
    device: torch.device,
    batch_size: int,
    min_filter_candidates: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for idx, record in enumerate(eval_records):
        bucket = record_bucket(record)
        prompt = prompt_text(record)
        target = target_expression(record)
        candidates, filter_diagnostics = filtered_candidates(
            candidate_banks.get(bucket, ()),
            prompt,
            bucket,
            min_candidates=min_filter_candidates,
        )
        generation_prompt = format_generation_prompt(prompt)
        scored = score_candidates(
            model,
            tokenizer,
            generation_prompt,
            candidates,
            device=device,
            batch_size=batch_size,
        )
        generated = scored[0]["candidate"] if scored else ""
        prompt_families = tuple(filter_diagnostics.get("prompt_families", ()))
        generated_families = tuple(sorted(expression_families(generated)))
        prompt_slots = infer_prompt_slots(prompt, bucket)
        prompt_policies = infer_prompt_slot_policies(prompt, bucket)
        prompt_terms = infer_prompt_required_terms(prompt)
        rank = rank_diagnostics(scored, target)
        sample = {
            "bucket": bucket,
            "sample_idx": idx,
            "prompt": prompt,
            "generation_prompt": generation_prompt,
            "ground_truth_cas_expression": target,
            "generated_response": generated,
            "exact_match": generated == target,
            "whole_compile_valid": compile_valid(generated),
            "structured_cas_valid": bool(expression_families(generated)),
            "family_match": not prompt_families or bool(set(prompt_families) & set(generated_families)),
            "required_terms_applicable": bool(prompt_terms),
            "required_terms_match": candidate_matches_required_terms(generated, prompt_terms),
            "slot_match_applicable": any(prompt_slots.values()),
            "slot_match": candidate_matches_slots(generated, prompt_slots),
            "slot_policy_match_applicable": any(prompt_policies.values()),
            "slot_policy_match": candidate_matches_slot_policy(generated, prompt_slots, prompt_policies),
            "generated_families": list(generated_families),
            "prompt_families": list(prompt_families),
            "generated_slots": {key: list(value) for key, value in expression_slots(generated).items()},
            "prompt_slots": {key: list(value) for key, value in prompt_slots.items()},
            "prompt_slot_policies": {key: list(value) for key, value in prompt_policies.items()},
            "decode_diagnostics": {
                "decode_mode": "semantic_rerank",
                "candidate_count": len(candidates),
                "top_candidates": scored[:5],
                **rank,
                **filter_diagnostics,
            },
            **rank,
        }
        samples.append(sample)
        by_bucket[bucket].append(sample)

    bucket_summary: dict[str, Any] = {}
    for bucket in BUCKETS:
        bucket_samples = by_bucket.get(bucket, [])
        if not bucket_samples:
            continue
        ranks = [s["ground_truth_rank"] for s in bucket_samples if s.get("ground_truth_rank") is not None]
        bucket_summary[bucket] = summarize_samples(bucket_samples, ranks)

    ranks = [s["ground_truth_rank"] for s in samples if s.get("ground_truth_rank") is not None]
    summary = {
        "n_total": len(samples),
        "n_exact_match": sum(1 for s in samples if s["exact_match"]),
        "exact_match_rate": sum(1 for s in samples if s["exact_match"]) / max(len(samples), 1),
        "n_whole_compile_valid": sum(1 for s in samples if s["whole_compile_valid"]),
        "n_structured_cas_valid": sum(1 for s in samples if s["structured_cas_valid"]),
        "n_ground_truth_scoreable": sum(1 for s in samples if s["ground_truth_scoreable"]),
        "n_ground_truth_top1": sum(1 for s in samples if s["ground_truth_top1"]),
        "n_ground_truth_top5": sum(1 for s in samples if s["ground_truth_top5"]),
        "mean_ground_truth_rank": sum(ranks) / len(ranks) if ranks else None,
        "n_family_match": sum(1 for s in samples if s["family_match"]),
        "n_required_terms_match": sum(
            1 for s in samples if s["required_terms_applicable"] and s["required_terms_match"]
        ),
        "n_slot_match": sum(1 for s in samples if s["slot_match_applicable"] and s["slot_match"]),
        "n_slot_policy_match": sum(
            1 for s in samples if s["slot_policy_match_applicable"] and s["slot_policy_match"]
        ),
        "by_bucket": bucket_summary,
    }
    return samples, summary


def summarize_samples(samples: list[dict[str, Any]], ranks: list[int]) -> dict[str, Any]:
    return {
        "n_total": len(samples),
        "n_exact_match": sum(1 for s in samples if s["exact_match"]),
        "exact_match_rate": sum(1 for s in samples if s["exact_match"]) / max(len(samples), 1),
        "n_whole_compile_valid": sum(1 for s in samples if s["whole_compile_valid"]),
        "n_structured_cas_valid": sum(1 for s in samples if s["structured_cas_valid"]),
        "n_ground_truth_scoreable": sum(1 for s in samples if s["ground_truth_scoreable"]),
        "n_ground_truth_top1": sum(1 for s in samples if s["ground_truth_top1"]),
        "n_ground_truth_top5": sum(1 for s in samples if s["ground_truth_top5"]),
        "mean_ground_truth_rank": sum(ranks) / len(ranks) if ranks else None,
        "n_family_match": sum(1 for s in samples if s["family_match"]),
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_report(path: Path, metrics: dict[str, Any], summary: dict[str, Any]) -> None:
    lines = [
        "# Semantic Reranker Validation",
        "",
        "## Headline",
        "",
        (
            f"- Exact top-1: {summary['n_exact_match']} / {summary['n_total']} "
            f"({summary['exact_match_rate']:.1%})"
        ),
        f"- Ground truth top-1: {summary['n_ground_truth_top1']} / {summary['n_total']}",
        f"- Ground truth top-5: {summary['n_ground_truth_top5']} / {summary['n_total']}",
        f"- Mean ground-truth rank: {summary['mean_ground_truth_rank']}",
        f"- Compiler-valid outputs: {summary['n_whole_compile_valid']} / {summary['n_total']}",
        "",
        "## Interpretation",
        "",
    ]
    final_epoch = metrics["epoch_metrics"][-1] if metrics.get("epoch_metrics") else {}
    pairwise_accuracy = float(final_epoch.get("pairwise_accuracy", 0.0))
    if summary["exact_match_rate"] < 0.20 and pairwise_accuracy >= 0.60:
        lines.extend(
            [
                "This run learned a weak prompt-candidate preference signal but did not solve exact recovery.",
                "",
                (
                    "Likely cause: many Level 2 prompts are underdetermined for exact CAS recovery. "
                    "The prompt may name a scenario but not the Noetic/Domain/Drive/Register slots "
                    "needed to identify one hidden target expression among thousands of valid candidates."
                ),
                "",
                (
                    "Engineering implication: add a recoverable natural-language prompt layer to the SDG "
                    "or evaluate multiple semantically valid candidates instead of a single hidden exact string."
                ),
                "",
            ]
        )
    else:
        lines.extend(
            [
                "The semantic reranker improved exact candidate selection under the current evaluation.",
                "",
            ]
        )
    lines.extend(
        [
        "## Training",
        "",
        f"- Train pairs: {metrics['train_pair_count']}",
        f"- Eligible records: {metrics['pair_build']['eligible_records']}",
        f"- Epochs: {metrics['epochs']}",
        f"- Batch size: {metrics['batch_size']}",
        f"- Wall clock seconds: {metrics['wall_clock_seconds']:.1f}",
        "",
        "## Epoch Metrics",
        "",
        ]
    )
    for epoch in metrics["epoch_metrics"]:
        lines.append(
            f"- epoch {epoch['epoch']}: loss={epoch['loss']:.4f}, "
            f"pairwise_accuracy={epoch['pairwise_accuracy']:.3f}"
        )
    lines.extend(["", "## By Bucket", ""])
    for bucket, bucket_metrics in summary["by_bucket"].items():
        lines.append(
            f"- {bucket}: exact={bucket_metrics['n_exact_match']}/{bucket_metrics['n_total']}, "
            f"top5={bucket_metrics['n_ground_truth_top5']}/{bucket_metrics['n_total']}, "
            f"mean_rank={bucket_metrics['mean_ground_truth_rank']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    start_time = time.time()

    print("[1/6] Loading data/tokenizer...")
    records = load_cas_data(args.dataset)
    tokenizer = HybridCASTokenizer.load(args.tokenizer)
    by_bucket = records_by_bucket(records)
    print(f"      records={len(records)} vocab={tokenizer.vocab_size} device={device}")

    print("[2/6] Building candidate banks...")
    candidate_banks = build_candidate_banks(records, max_candidates=args.max_candidates)
    for bucket in BUCKETS:
        print(f"      {bucket}: {len(candidate_banks[bucket])} candidates")

    print("[3/6] Building contrastive pairs...")
    eval_records = choose_eval_records(by_bucket, per_bucket=args.eval_per_bucket, seed=args.seed)
    pairs, pair_diagnostics = make_training_pairs(
        records,
        candidate_banks,
        eval_records,
        train_records=args.train_records,
        negatives_per_positive=args.negatives_per_positive,
        min_filter_candidates=args.min_filter_candidates,
        seed=args.seed,
    )
    if not pairs:
        raise RuntimeError("no semantic-reranker training pairs were built")
    print(f"      pairs={len(pairs)} eval_records={len(eval_records)}")

    print("[4/6] Training semantic reranker...")
    config = SemanticRerankerConfig(
        vocab_size=tokenizer.vocab_size,
        d_model=args.d_model,
        hidden_dim=args.hidden_dim,
        dropout=args.dropout,
    )
    model = SemanticReranker(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    epoch_metrics: list[dict[str, Any]] = []
    for epoch in range(1, args.epochs + 1):
        metrics = train_one_epoch(
            model,
            tokenizer,
            pairs,
            optimizer=optimizer,
            device=device,
            batch_size=args.batch_size,
            rng=rng,
        )
        metrics["epoch"] = epoch
        epoch_metrics.append(metrics)
        print(
            f"      epoch={epoch} loss={metrics['loss']:.4f} "
            f"pairwise_acc={metrics['pairwise_accuracy']:.3f}"
        )

    print("[5/6] Evaluating semantic rerank...")
    samples, summary = evaluate(
        model,
        tokenizer,
        eval_records,
        candidate_banks,
        device=device,
        batch_size=args.batch_size,
        min_filter_candidates=args.min_filter_candidates,
    )

    wall_clock = time.time() - start_time
    metrics = {
        "dataset": str(args.dataset),
        "tokenizer": str(args.tokenizer),
        "train_record_limit": args.train_records,
        "train_pair_count": len(pairs),
        "eval_record_count": len(eval_records),
        "candidate_bank_sizes": {bucket: len(values) for bucket, values in candidate_banks.items()},
        "pair_build": pair_diagnostics,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "seed": args.seed,
        "device": str(device),
        "epoch_metrics": epoch_metrics,
        "wall_clock_seconds": wall_clock,
        "model_config": config.__dict__,
    }

    print("[6/6] Writing artifacts...")
    write_jsonl(args.out_dir / "samples.jsonl", samples)
    (args.out_dir / "eval_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_semantic_reranker(
        args.out_dir / "semantic_reranker.pt",
        model,
        metadata={
            "tokenizer_path": str(args.tokenizer),
            "dataset": str(args.dataset),
            "summary": summary,
        },
    )
    write_report(args.out_dir / "SEMANTIC_RERANKER_VALIDATION_REPORT.md", metrics, summary)
    print(
        f"      exact={summary['n_exact_match']}/{summary['n_total']} "
        f"top5={summary['n_ground_truth_top5']}/{summary['n_total']} "
        f"mean_rank={summary['mean_ground_truth_rank']} out={args.out_dir}"
    )


if __name__ == "__main__":
    main()
