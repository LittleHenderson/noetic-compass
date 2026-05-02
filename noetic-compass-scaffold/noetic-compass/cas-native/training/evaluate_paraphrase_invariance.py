#!/usr/bin/env python3
"""Evaluate structured-token prediction stability under deterministic paraphrases."""

from __future__ import annotations

import argparse
import json
import sys
import types
from collections import defaultdict
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


from cas_native.training.paraphrase_templates import (
    EVAL_PARAPHRASE_TEMPLATES,
    KNOWN_SUFFIXES,
    apply_template,
    extract_recoverable_slots,
)


# Backward-compat: the prior module name. Prefer EVAL_PARAPHRASE_TEMPLATES
# in new callers.
PARAPHRASE_TEMPLATES: tuple[str, ...] = EVAL_PARAPHRASE_TEMPLATES

EVAL_PARAPHRASE_SOURCE_LABEL = "deterministic_recoverable_slot_template"


def paraphrase_record(
    record: dict[str, Any],
    *,
    paraphrase_index: int,
) -> dict[str, Any]:
    """Return a copy of a Level 3 record with a deterministic eval paraphrase."""

    template = EVAL_PARAPHRASE_TEMPLATES[
        paraphrase_index % len(EVAL_PARAPHRASE_TEMPLATES)
    ]
    return apply_template(
        record,
        template,
        paraphrase_index=paraphrase_index,
        paraphrase_source=EVAL_PARAPHRASE_SOURCE_LABEL,
    )


def make_paraphrase_records(
    records: Iterable[dict[str, Any]],
    *,
    variants_per_record: int,
) -> list[dict[str, Any]]:
    if variants_per_record <= 0:
        raise ValueError("variants_per_record must be positive")
    return [
        paraphrase_record(record, paraphrase_index=index)
        for record in records
        for index in range(variants_per_record)
    ]


def evaluate_records_with_saved_run(
    records: list[dict[str, Any]],
    *,
    run_dir: Path,
    checkpoint: Path | None = None,
    d_model: int | None = None,
    bottleneck_dim: int | None = None,
    batch_size: int = 128,
    max_length: int | None = None,
    device: str = "cpu",
) -> dict[str, Any]:
    manifest_config = _manifest_config(run_dir)
    d_model = int(d_model or manifest_config.get("d_model", 128))
    bottleneck_dim = int(bottleneck_dim or manifest_config.get("bottleneck_dim", 64))
    max_length = int(max_length or manifest_config.get("max_length", 256))
    checkpoint = checkpoint or (run_dir / "best_structured_token_model.pt")
    vocabulary = StructuredTokenVocabulary.load(run_dir / "structured_token_vocab.json")

    embedding = StructuredTokenEmbedding(vocab_size=len(vocabulary), d_model=d_model)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)
    model = StructuredTokenStructuredPredictor(embedding, head)
    model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
    model.to(torch.device(device))
    return evaluate_structured_token_prediction(
        model,
        records,
        vocabulary,
        device=device,
        batch_size=batch_size,
        max_length=max_length,
    )


def build_invariance_report(
    canonical_samples: list[dict[str, Any]],
    paraphrase_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    canonical_by_id = {sample["id"]: sample for sample in canonical_samples}
    comparable = [
        sample
        for sample in paraphrase_samples
        if sample.get("base_id") in canonical_by_id
    ]
    if not comparable:
        raise ValueError("no paraphrase samples could be matched to canonical samples")
    head_keys = sorted(
        {
            key
            for sample in comparable
            for key in sample.get("prediction", {}).keys()
        }
    )
    per_head_consistent = {
        head: sum(
            1
            for sample in comparable
            if sample["prediction"].get(head)
            == canonical_by_id[sample["base_id"]]["prediction"].get(head)
        )
        for head in head_keys
    }
    all_heads_consistent = sum(
        1
        for sample in comparable
        if all(
            sample["prediction"].get(head)
            == canonical_by_id[sample["base_id"]]["prediction"].get(head)
            for head in head_keys
        )
    )
    canonical_exact_ids = {
        sample["id"] for sample in canonical_samples if sample.get("all_heads_exact")
    }
    exact_base_samples = [
        sample for sample in comparable if sample.get("base_id") in canonical_exact_ids
    ]
    exact_retained = sum(1 for sample in exact_base_samples if sample.get("all_heads_exact"))

    return {
        "n_canonical": len(canonical_samples),
        "n_paraphrase": len(paraphrase_samples),
        "n_comparable": len(comparable),
        "canonical_all_heads_exact": sum(
            1 for sample in canonical_samples if sample.get("all_heads_exact")
        ),
        "paraphrase_all_heads_exact": sum(
            1 for sample in comparable if sample.get("all_heads_exact")
        ),
        "paraphrase_all_heads_exact_rate": _rate(
            sum(1 for sample in comparable if sample.get("all_heads_exact")),
            len(comparable),
        ),
        "all_heads_prediction_consistent": all_heads_consistent,
        "all_heads_prediction_consistency_rate": _rate(
            all_heads_consistent,
            len(comparable),
        ),
        "canonical_exact_retained": exact_retained,
        "canonical_exact_retention_rate": _rate(exact_retained, len(exact_base_samples)),
        "per_head_prediction_consistency": {
            head: _rate(count, len(comparable))
            for head, count in per_head_consistent.items()
        },
        "by_bucket": _bucket_invariance(canonical_by_id, comparable, head_keys),
    }


def write_invariance_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Structured-Token Paraphrase-Invariance Report",
        "",
        f"Canonical samples: {report['n_canonical']}",
        f"Paraphrase samples: {report['n_paraphrase']}",
        f"Comparable samples: {report['n_comparable']}",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Paraphrase all-heads exact | {report['paraphrase_all_heads_exact_rate']:.3f} |",
        f"| Prediction consistency vs canonical | {report['all_heads_prediction_consistency_rate']:.3f} |",
        f"| Canonical-exact retention | {report['canonical_exact_retention_rate']:.3f} |",
        "",
        "## Per-Head Prediction Consistency",
        "",
        "| Head | Rate |",
        "|---|---:|",
    ]
    for head, rate in sorted(
        report["per_head_prediction_consistency"].items(),
        key=lambda item: (item[1], item[0]),
    ):
        lines.append(f"| {head} | {rate:.3f} |")
    lines.extend(["", "## Bucket Summary", "", "| Bucket | n | Exact Rate | Consistency |", "|---|---:|---:|---:|"])
    for bucket, entry in sorted(report["by_bucket"].items()):
        lines.append(
            f"| {bucket} | {entry['n']} | {entry['paraphrase_all_heads_exact_rate']:.3f} | "
            f"{entry['all_heads_prediction_consistency_rate']:.3f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _bucket_invariance(
    canonical_by_id: dict[str, dict[str, Any]],
    samples: list[dict[str, Any]],
    head_keys: list[str],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        grouped[str(sample.get("bucket") or "unknown")].append(sample)
    out: dict[str, Any] = {}
    for bucket, bucket_samples in grouped.items():
        exact = sum(1 for sample in bucket_samples if sample.get("all_heads_exact"))
        consistent = sum(
            1
            for sample in bucket_samples
            if all(
                sample["prediction"].get(head)
                == canonical_by_id[sample["base_id"]]["prediction"].get(head)
                for head in head_keys
            )
        )
        out[bucket] = {
            "n": len(bucket_samples),
            "paraphrase_all_heads_exact": exact,
            "paraphrase_all_heads_exact_rate": _rate(exact, len(bucket_samples)),
            "all_heads_prediction_consistent": consistent,
            "all_heads_prediction_consistency_rate": _rate(
                consistent,
                len(bucket_samples),
            ),
        }
    return out


def _manifest_config(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "manifest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("config", {}))


def _rate(numer: int, denom: int) -> float:
    return 0.0 if denom <= 0 else numer / denom


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
    parser.add_argument("--prefix", default="paraphrase_eval")
    parser.add_argument("--variants-per-record", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--d-model", type=int, default=None)
    parser.add_argument("--bottleneck-dim", type=int, default=None)
    args = parser.parse_args()

    canonical_records = load_level3_jsonl(args.eval_input, limit=args.limit)
    paraphrase_records = make_paraphrase_records(
        canonical_records,
        variants_per_record=args.variants_per_record,
    )
    common_kwargs = {
        "run_dir": args.run_dir,
        "checkpoint": args.checkpoint,
        "d_model": args.d_model,
        "bottleneck_dim": args.bottleneck_dim,
        "batch_size": args.batch_size,
        "max_length": args.max_length,
        "device": args.device,
    }
    canonical_manifest = evaluate_records_with_saved_run(canonical_records, **common_kwargs)
    paraphrase_manifest = evaluate_records_with_saved_run(paraphrase_records, **common_kwargs)
    report = build_invariance_report(
        list(canonical_manifest.get("samples", [])),
        list(paraphrase_manifest.get("samples", [])),
    )

    out_dir = args.out_dir or args.run_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    canonical_out = out_dir / f"{args.prefix}_canonical_manifest.json"
    paraphrase_out = out_dir / f"{args.prefix}_manifest.json"
    samples_out = out_dir / f"{args.prefix}_samples.jsonl"
    report_json_out = out_dir / f"{args.prefix}_report.json"
    report_md_out = out_dir / f"{args.prefix}_report.md"
    _write_json(canonical_out, canonical_manifest)
    _write_json(paraphrase_out, paraphrase_manifest)
    _write_samples(samples_out, paraphrase_manifest.get("samples", []))
    _write_json(report_json_out, report)
    write_invariance_markdown(report, report_md_out)

    print(
        json.dumps(
            {
                "canonical_all_heads_exact_rate": canonical_manifest["all_heads_exact_rate"],
                "paraphrase_all_heads_exact_rate": report["paraphrase_all_heads_exact_rate"],
                "all_heads_prediction_consistency_rate": report[
                    "all_heads_prediction_consistency_rate"
                ],
                "canonical_exact_retention_rate": report[
                    "canonical_exact_retention_rate"
                ],
                "report": str(report_md_out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
