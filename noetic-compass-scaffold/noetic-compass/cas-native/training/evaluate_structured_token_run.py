#!/usr/bin/env python3
"""Evaluate a saved structured-token prediction run and write confusion reports."""

from __future__ import annotations

import argparse
import json
import sys
import types
from collections import Counter, defaultdict
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

from cas_native.model.structured_prediction import StructuredPredictionHead
from cas_native.model.structured_token_embedding import (
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.tokenizer.vocabulary import StructuredTokenVocabulary
from cas_native.training.structured_prediction_ingest import load_level3_jsonl
from cas_native.training.train_structured_prediction import (
    evaluate_structured_token_prediction,
)


DEFAULT_CONFUSION_HEADS = ("expression_family", "transition_kind")


def evaluate_saved_run(
    *,
    run_dir: Path,
    eval_input: Path,
    checkpoint: Path | None = None,
    d_model: int | None = None,
    bottleneck_dim: int | None = None,
    batch_size: int = 128,
    max_length: int | None = None,
    device: str = "cpu",
) -> dict[str, Any]:
    """Load a saved structured-token run and evaluate it against JSONL records."""

    manifest_config = _manifest_config(run_dir)
    d_model = int(d_model or manifest_config.get("d_model", 128))
    bottleneck_dim = int(bottleneck_dim or manifest_config.get("bottleneck_dim", 64))
    max_length = int(max_length or manifest_config.get("max_length", 256))
    checkpoint = checkpoint or (run_dir / "best_structured_token_model.pt")
    vocab_path = run_dir / "structured_token_vocab.json"

    if not checkpoint.exists():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint}")
    if not vocab_path.exists():
        raise FileNotFoundError(f"structured-token vocabulary not found: {vocab_path}")
    if not eval_input.exists():
        raise FileNotFoundError(f"eval input not found: {eval_input}")

    vocabulary = StructuredTokenVocabulary.load(vocab_path)
    embedding = StructuredTokenEmbedding(vocab_size=len(vocabulary), d_model=d_model)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)
    model = StructuredTokenStructuredPredictor(embedding, head)
    state = torch.load(checkpoint, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.to(torch.device(device))

    records = load_level3_jsonl(eval_input)
    return evaluate_structured_token_prediction(
        model,
        records,
        vocabulary,
        device=device,
        batch_size=batch_size,
        max_length=max_length,
    )


def build_confusion_report(
    samples: Iterable[dict[str, Any]],
    *,
    focus_bucket: str = "v77_rule_four",
    confusion_heads: Iterable[str] = DEFAULT_CONFUSION_HEADS,
) -> dict[str, Any]:
    """Build aggregate head-failure and target-vs-prediction confusion data."""

    sample_list = list(samples)
    head_keys = sorted(
        {
            key
            for sample in sample_list
            for key in dict(sample.get("head_correct", {})).keys()
        }
    )
    confusion_head_list = list(confusion_heads)
    by_bucket: dict[str, dict[str, Any]] = {}
    for bucket, bucket_samples in _group_by_bucket(sample_list).items():
        head_failures = {
            head: sum(1 for sample in bucket_samples if not sample["head_correct"].get(head, True))
            for head in head_keys
        }
        by_bucket[bucket] = {
            "n": len(bucket_samples),
            "all_heads_failures": sum(
                1 for sample in bucket_samples if not sample.get("all_heads_exact", False)
            ),
            "head_failures": head_failures,
        }

    return {
        "n": len(sample_list),
        "all_heads_exact": sum(1 for sample in sample_list if sample.get("all_heads_exact")),
        "all_heads_failures": sum(
            1 for sample in sample_list if not sample.get("all_heads_exact", False)
        ),
        "head_failures": {
            head: sum(1 for sample in sample_list if not sample["head_correct"].get(head, True))
            for head in head_keys
        },
        "by_bucket": by_bucket,
        "focus_bucket": focus_bucket,
        "focus_patterns": _pattern_breakdown(sample_list, bucket=focus_bucket),
        "confusion": {
            head: _confusion_for_head(sample_list, head, bucket=focus_bucket)
            for head in confusion_head_list
        },
    }


def write_report_markdown(report: dict[str, Any], path: Path) -> None:
    """Write a compact Markdown report for a confusion summary."""

    lines = [
        "# Structured-Token Eval Confusion Report",
        "",
        f"Total samples: {report['n']}",
        f"All-heads exact: {report['all_heads_exact']}",
        f"All-heads failures: {report['all_heads_failures']}",
        "",
        "## Head Failures",
        "",
        "| Head | Failures |",
        "|---|---:|",
    ]
    for head, failures in sorted(
        report["head_failures"].items(),
        key=lambda item: (-int(item[1]), item[0]),
    ):
        lines.append(f"| {head} | {failures} |")

    lines.extend(["", "## Bucket Failures", "", "| Bucket | n | Failures |", "|---|---:|---:|"])
    for bucket, entry in sorted(
        report["by_bucket"].items(),
        key=lambda item: (-int(item[1]["all_heads_failures"]), item[0]),
    ):
        lines.append(f"| {bucket} | {entry['n']} | {entry['all_heads_failures']} |")

    lines.extend(["", f"## {report['focus_bucket']} Confusions"])
    lines.extend(["", "### Expression Patterns", "", "| Pattern | n | Exact | Rate |", "|---|---:|---:|---:|"])
    for pattern, entry in sorted(
        report.get("focus_patterns", {}).items(),
        key=lambda item: (-int(item[1]["n"]), item[0]),
    ):
        rate = 0.0 if entry["n"] == 0 else 100.0 * entry["exact"] / entry["n"]
        lines.append(f"| {pattern} | {entry['n']} | {entry['exact']} | {rate:.1f}% |")

    for head, entries in report["confusion"].items():
        lines.extend(["", f"### {head}", "", "| Target | Prediction | Count |", "|---|---|---:|"])
        if entries:
            for entry in entries:
                lines.append(
                    f"| {entry['target']} | {entry['prediction']} | {entry['count']} |"
                )
        else:
            lines.append("| - | - | 0 |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _manifest_config(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "manifest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("config", {}))


def _group_by_bucket(samples: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        buckets[str(sample.get("bucket") or "unknown")].append(sample)
    return dict(buckets)


def _confusion_for_head(
    samples: list[dict[str, Any]],
    head: str,
    *,
    bucket: str | None = None,
) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for sample in samples:
        if bucket is not None and sample.get("bucket") != bucket:
            continue
        target = dict(sample.get("target", {})).get(head)
        prediction = dict(sample.get("prediction", {})).get(head)
        if target == prediction:
            continue
        counts[(_label_key(target), _label_key(prediction))] += 1
    return [
        {"target": target, "prediction": prediction, "count": count}
        for (target, prediction), count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1]),
        )
    ]


def _pattern_breakdown(
    samples: list[dict[str, Any]],
    *,
    bucket: str,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        if sample.get("bucket") != bucket:
            continue
        grouped[_expression_pattern(str(sample.get("cas_expression") or ""))].append(sample)
    return {
        pattern: {
            "n": len(pattern_samples),
            "exact": sum(1 for sample in pattern_samples if sample.get("all_heads_exact")),
            "head_failures": {
                head: sum(
                    1
                    for sample in pattern_samples
                    if not sample.get("head_correct", {}).get(head, True)
                )
                for head in sorted(
                    {
                        key
                        for sample in pattern_samples
                        for key in sample.get("head_correct", {}).keys()
                    }
                )
            },
        }
        for pattern, pattern_samples in sorted(grouped.items())
    }


def _expression_pattern(expression: str) -> str:
    if "\u03a9" in expression or "Omega" in expression:
        return "omega_emergent"
    if " + " in expression:
        return "plus_copresence"
    if "\u27e8" in expression or "|<" in expression:
        return "register_set"
    if "\u00d7" in expression or " x " in expression:
        return "cross_register"
    return "other"


def _label_key(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value) if value else "<none>"
    if value is None:
        return "<missing>"
    return str(value)


def _write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def _write_samples(path: Path, samples: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--eval-input", required=True, type=Path)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--prefix", default="current_eval")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--d-model", type=int, default=None)
    parser.add_argument("--bottleneck-dim", type=int, default=None)
    parser.add_argument("--focus-bucket", default="v77_rule_four")
    parser.add_argument(
        "--confusion-head",
        action="append",
        default=None,
        help="Head to include in the focused confusion report; may be repeated.",
    )
    args = parser.parse_args()

    result = evaluate_saved_run(
        run_dir=args.run_dir,
        eval_input=args.eval_input,
        checkpoint=args.checkpoint,
        d_model=args.d_model,
        bottleneck_dim=args.bottleneck_dim,
        batch_size=args.batch_size,
        max_length=args.max_length,
        device=args.device,
    )
    out_dir = args.out_dir or args.run_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = list(result.get("samples", []))
    report = build_confusion_report(
        samples,
        focus_bucket=args.focus_bucket,
        confusion_heads=args.confusion_head or DEFAULT_CONFUSION_HEADS,
    )

    manifest_out = out_dir / f"{args.prefix}_manifest.json"
    samples_out = out_dir / f"{args.prefix}_samples.jsonl"
    report_json_out = out_dir / f"{args.prefix}_confusion.json"
    report_md_out = out_dir / f"{args.prefix}_confusion.md"
    _write_json(manifest_out, result)
    _write_samples(samples_out, samples)
    _write_json(report_json_out, report)
    write_report_markdown(report, report_md_out)

    print(
        json.dumps(
            {
                "n": result["n"],
                "all_heads_exact": result["all_heads_exact"],
                "all_heads_exact_rate": result["all_heads_exact_rate"],
                "manifest": str(manifest_out),
                "samples": str(samples_out),
                "confusion_json": str(report_json_out),
                "confusion_md": str(report_md_out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
