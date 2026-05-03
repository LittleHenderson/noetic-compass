#!/usr/bin/env python3
"""Evaluate self-conditioning invariance: oracle-prior paraphrase consistency.

This harness measures the ceiling on what self-conditioning can achieve when
the model receives its own canonical CAS prediction as a [PRIOR] block
prepended to a paraphrase prompt.

Two passes per eval run:
  1. Canonical eval (no prior) — standard forward pass on each eval record.
  2. Paraphrase-with-prior eval — for each paraphrase variant, set
     prior_cas_state = canonical's cas_expression (oracle prior), then
     forward-pass with the [PRIOR] block prepended.

Metrics reported:
  - all_heads_exact: standard paraphrase accuracy (same as evaluate_paraphrase_invariance).
  - per_head_prediction_consistency: canonical-vs-(paraphrase-with-prior) agreement.
  - prior_lift_pp: consistency lift vs standard paraphrase (without prior).

NOTE: This eval ONLY runs on CPU. Do NOT pass --device cuda.

Usage:
    python evaluate_self_conditioning_invariance.py \\
        --run-dir path/to/run \\
        --eval-input path/to/level3_recoverable_eval_1000_v77_relabeled.jsonl \\
        --out-dir path/to/out \\
        --prefix sc_invariance \\
        --variants-per-record 3
"""

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
from cas_native.training.structured_prediction_ingest import (
    get_effective_prompt,
    load_level3_jsonl,
)
from cas_native.training.train_structured_prediction import (
    evaluate_structured_token_prediction,
)
from cas_native.training.paraphrase_templates import (
    EVAL_PARAPHRASE_TEMPLATES,
    apply_template,
)


EVAL_PARAPHRASE_SOURCE_LABEL = "sc_invariance_eval"


def _load_model(
    run_dir: Path,
    *,
    checkpoint: Path | None,
    d_model: int | None,
    bottleneck_dim: int | None,
    max_length: int | None,
    device: str,
) -> tuple[StructuredTokenStructuredPredictor, StructuredTokenVocabulary, int, int]:
    manifest_config = _manifest_config(run_dir)
    d_model = int(d_model or manifest_config.get("d_model", 128))
    bottleneck_dim = int(bottleneck_dim or manifest_config.get("bottleneck_dim", 64))
    max_length = int(max_length or manifest_config.get("max_length", 256))
    checkpoint = checkpoint or (run_dir / "best_structured_token_model.pt")
    vocabulary = StructuredTokenVocabulary.load(run_dir / "structured_token_vocab.json")

    embedding = StructuredTokenEmbedding(vocab_size=len(vocabulary), d_model=d_model)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)
    model = StructuredTokenStructuredPredictor(embedding, head)
    model.load_state_dict(
        torch.load(checkpoint, map_location=device, weights_only=True)
    )
    model.to(torch.device(device))
    return model, vocabulary, d_model, max_length


def make_sc_paraphrase_records(
    canonical_records: list[dict[str, Any]],
    *,
    variants_per_record: int,
) -> list[dict[str, Any]]:
    """Build paraphrase records with oracle prior_cas_state.

    Uses the EVAL_PARAPHRASE_TEMPLATES (same as evaluate_paraphrase_invariance).
    Sets prior_cas_state to the canonical record's cas_expression so that
    get_effective_prompt prepends the [PRIOR] block at tokenization time.
    """

    if variants_per_record <= 0:
        raise ValueError("variants_per_record must be positive")
    records: list[dict[str, Any]] = []
    for canonical in canonical_records:
        oracle_prior = str(canonical.get("cas_expression") or "")
        for index in range(variants_per_record):
            template = EVAL_PARAPHRASE_TEMPLATES[index % len(EVAL_PARAPHRASE_TEMPLATES)]
            para = apply_template(
                canonical,
                template,
                paraphrase_index=index,
                paraphrase_source=EVAL_PARAPHRASE_SOURCE_LABEL,
            )
            para["prior_cas_state"] = oracle_prior
            records.append(para)
    return records


def evaluate_records_with_model(
    records: list[dict[str, Any]],
    model: StructuredTokenStructuredPredictor,
    vocabulary: StructuredTokenVocabulary,
    *,
    batch_size: int,
    max_length: int,
    device: str,
) -> dict[str, Any]:
    """Forward-pass records through the model and return an eval manifest."""
    return evaluate_structured_token_prediction(
        model,
        records,
        vocabulary,
        device=device,
        batch_size=batch_size,
        max_length=max_length,
    )


def build_sc_invariance_report(
    canonical_samples: list[dict[str, Any]],
    sc_paraphrase_samples: list[dict[str, Any]],
    standard_paraphrase_rate: float | None = None,
) -> dict[str, Any]:
    """Compute oracle-prior consistency metrics.

    Args:
        canonical_samples: samples from the canonical forward pass (no prior).
        sc_paraphrase_samples: samples from the paraphrase-with-oracle-prior pass.
        standard_paraphrase_rate: optional all_heads_exact_rate from a standard
            paraphrase eval (no prior), used to compute the prior_lift_pp metric.
    """

    canonical_by_id = {sample["id"]: sample for sample in canonical_samples}
    comparable = [
        s for s in sc_paraphrase_samples if s.get("base_id") in canonical_by_id
    ]
    if not comparable:
        raise ValueError("no SC paraphrase samples matched canonical samples by base_id")

    head_keys = sorted(
        {key for s in comparable for key in s.get("prediction", {}).keys()}
    )

    per_head_consistent = {
        head: sum(
            1
            for s in comparable
            if s["prediction"].get(head)
            == canonical_by_id[s["base_id"]]["prediction"].get(head)
        )
        for head in head_keys
    }

    all_heads_consistent = sum(
        1
        for s in comparable
        if all(
            s["prediction"].get(h) == canonical_by_id[s["base_id"]]["prediction"].get(h)
            for h in head_keys
        )
    )

    sc_exact = sum(1 for s in comparable if s.get("all_heads_exact"))
    sc_exact_rate = _rate(sc_exact, len(comparable))
    consistency_rate = _rate(all_heads_consistent, len(comparable))

    canonical_exact_ids = {
        s["id"] for s in canonical_samples if s.get("all_heads_exact")
    }
    exact_base_samples = [s for s in comparable if s.get("base_id") in canonical_exact_ids]
    exact_retained = sum(1 for s in exact_base_samples if s.get("all_heads_exact"))

    report: dict[str, Any] = {
        "n_canonical": len(canonical_samples),
        "n_sc_paraphrase": len(sc_paraphrase_samples),
        "n_comparable": len(comparable),
        "canonical_all_heads_exact": sum(
            1 for s in canonical_samples if s.get("all_heads_exact")
        ),
        "sc_paraphrase_all_heads_exact": sc_exact,
        "sc_paraphrase_all_heads_exact_rate": sc_exact_rate,
        "all_heads_prediction_consistent": all_heads_consistent,
        "all_heads_prediction_consistency_rate": consistency_rate,
        "canonical_exact_retained": exact_retained,
        "canonical_exact_retention_rate": _rate(exact_retained, len(exact_base_samples)),
        "per_head_prediction_consistency": {
            head: _rate(count, len(comparable))
            for head, count in per_head_consistent.items()
        },
        "by_bucket": _bucket_invariance(canonical_by_id, comparable, head_keys),
    }

    if standard_paraphrase_rate is not None:
        report["standard_paraphrase_all_heads_exact_rate"] = standard_paraphrase_rate
        report["prior_lift_pp"] = round(
            (sc_exact_rate - standard_paraphrase_rate) * 100, 2
        )

    return report


def write_sc_invariance_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Self-Conditioning Invariance Report (Oracle Prior)",
        "",
        f"Canonical samples: {report['n_canonical']}",
        f"SC paraphrase samples (with oracle prior): {report['n_sc_paraphrase']}",
        f"Comparable: {report['n_comparable']}",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| SC paraphrase all-heads exact (oracle prior) | "
        f"{report['sc_paraphrase_all_heads_exact_rate']:.3f} |",
        f"| Prediction consistency vs canonical | "
        f"{report['all_heads_prediction_consistency_rate']:.3f} |",
        f"| Canonical-exact retention | "
        f"{report['canonical_exact_retention_rate']:.3f} |",
    ]
    if "standard_paraphrase_all_heads_exact_rate" in report:
        lines.append(
            f"| Standard paraphrase all-heads exact (no prior) | "
            f"{report['standard_paraphrase_all_heads_exact_rate']:.3f} |"
        )
        lines.append(
            f"| Prior lift (pp, oracle) | {report['prior_lift_pp']:+.2f} |"
        )
    lines += [
        "",
        "## Per-Head Prediction Consistency (canonical vs SC paraphrase)",
        "",
        "| Head | Rate |",
        "|---|---:|",
    ]
    for head, rate in sorted(
        report["per_head_prediction_consistency"].items(),
        key=lambda item: (item[1], item[0]),
    ):
        lines.append(f"| {head} | {rate:.3f} |")
    lines += [
        "",
        "## Bucket Summary",
        "",
        "| Bucket | n | SC Exact Rate | Consistency |",
        "|---|---:|---:|---:|",
    ]
    for bucket, entry in sorted(report["by_bucket"].items()):
        lines.append(
            f"| {bucket} | {entry['n']} | "
            f"{entry['sc_all_heads_exact_rate']:.3f} | "
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
    for s in samples:
        grouped[str(s.get("bucket") or "unknown")].append(s)
    out: dict[str, Any] = {}
    for bucket, bucket_samples in grouped.items():
        exact = sum(1 for s in bucket_samples if s.get("all_heads_exact"))
        consistent = sum(
            1
            for s in bucket_samples
            if all(
                s["prediction"].get(h) == canonical_by_id[s["base_id"]]["prediction"].get(h)
                for h in head_keys
            )
        )
        out[bucket] = {
            "n": len(bucket_samples),
            "sc_all_heads_exact": exact,
            "sc_all_heads_exact_rate": _rate(exact, len(bucket_samples)),
            "all_heads_prediction_consistent": consistent,
            "all_heads_prediction_consistency_rate": _rate(
                consistent, len(bucket_samples)
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
    parser.add_argument("--prefix", default="sc_invariance")
    parser.add_argument("--variants-per-record", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--device", default="cpu",
                        help="Inference device. CPU only — do NOT pass cuda.")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--d-model", type=int, default=None)
    parser.add_argument("--bottleneck-dim", type=int, default=None)
    args = parser.parse_args()

    canonical_records = load_level3_jsonl(args.eval_input, limit=args.limit)
    sc_paraphrase_records = make_sc_paraphrase_records(
        canonical_records, variants_per_record=args.variants_per_record
    )

    model, vocabulary, d_model, max_length = _load_model(
        args.run_dir,
        checkpoint=args.checkpoint,
        d_model=args.d_model,
        bottleneck_dim=args.bottleneck_dim,
        max_length=args.max_length,
        device=args.device,
    )
    common_eval_kwargs = dict(
        model=model,
        vocabulary=vocabulary,
        batch_size=args.batch_size,
        max_length=max_length,
        device=args.device,
    )

    canonical_manifest = evaluate_records_with_model(canonical_records, **common_eval_kwargs)
    sc_manifest = evaluate_records_with_model(sc_paraphrase_records, **common_eval_kwargs)

    report = build_sc_invariance_report(
        list(canonical_manifest.get("samples", [])),
        list(sc_manifest.get("samples", [])),
    )

    out_dir = args.out_dir or args.run_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    canonical_out = out_dir / f"{args.prefix}_canonical_manifest.json"
    sc_out = out_dir / f"{args.prefix}_manifest.json"
    samples_out = out_dir / f"{args.prefix}_samples.jsonl"
    report_json_out = out_dir / f"{args.prefix}_report.json"
    report_md_out = out_dir / f"{args.prefix}_report.md"

    _write_json(canonical_out, canonical_manifest)
    _write_json(sc_out, sc_manifest)
    _write_samples(samples_out, sc_manifest.get("samples", []))
    _write_json(report_json_out, report)
    write_sc_invariance_markdown(report, report_md_out)

    summary = {
        "canonical_all_heads_exact_rate": canonical_manifest["all_heads_exact_rate"],
        "sc_paraphrase_all_heads_exact_rate": report["sc_paraphrase_all_heads_exact_rate"],
        "all_heads_prediction_consistency_rate": report[
            "all_heads_prediction_consistency_rate"
        ],
        "canonical_exact_retention_rate": report["canonical_exact_retention_rate"],
        "report": str(report_md_out),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
