#!/usr/bin/env python3
"""Evaluate structured-token prediction stability under the diagram-loop lever.

Two-pass evaluation:
  Pass 1 — canonical records (no prior diagram, text-only path).
  Pass 2 — same records but with ``prior_diagram`` populated from the
            ground-truth ``cas_expression`` compiled to a graph dict.

The invariance property under test: when the correct CAS diagram is fed as
prior context, the model's predictions should be at least as accurate and
ideally more consistent than the text-only baseline.

Metrics reported:
  - canonical_all_heads_exact_rate      — baseline accuracy
  - diagram_loop_all_heads_exact_rate   — accuracy with prior diagram
  - accuracy_delta                      — diagram_loop − canonical (>0 = improvement)
  - all_heads_prediction_consistency_rate — Pass-1/Pass-2 prediction agreement
  - per_head_prediction_consistency     — per-head agreement rates
  - by_bucket                           — per-expression-family breakdown
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

from cas_native.model.graph_encoder import GraphEncoder
from cas_native.model.graph_text_fusion import GraphTextFusion
from cas_native.model.structured_prediction import (
    DOMAIN_LABELS,
    DRIVE_LABELS,
    EXPRESSION_FAMILY_LABELS,
    META_RELATION_LABELS,
    REGISTER_LABELS,
    TURN_TYPE_LABELS,
    StructuredPredictionHead,
)
from cas_native.model.structured_token_embedding import (
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.tokenizer.vocabulary import StructuredTokenVocabulary
from cas_native.training.diagram_serialization import (
    EDGE_FEATURE_DIM,
    NODE_FEATURE_DIM,
    compile_to_graph,
    serialize_diagram_for_batch,
)
from cas_native.training.structured_prediction_ingest import (
    batch_targets_from_records,
    load_level3_jsonl,
)
from cas_native.training.structured_token_adapter import (
    records_to_structured_token_sequences,
    tokens_to_structured_token_batch,
)

DIAGRAM_LOOP_EVAL_SOURCE_LABEL = "diagram_loop_invariance_eval"

_EVAL_LOGIT_KEYS = (
    "turn_type_logits",
    "expression_family_logits",
    "transition_kind_logits",
    "noetic_logits",
    "domain_logits",
    "drive_logits",
    "register_mode_logits",
    "authority_logits",
)

_HEAD_LABEL_MAPS: dict[str, tuple[str, ...]] = {
    "turn_type": TURN_TYPE_LABELS,
    "expression_family": EXPRESSION_FAMILY_LABELS,
    "domain": DOMAIN_LABELS,
    "drive": DRIVE_LABELS,
}


# ---------------------------------------------------------------------------
# Record helpers
# ---------------------------------------------------------------------------

def make_diagram_loop_records(
    records: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a copy of each record with ``prior_diagram`` populated.

    The prior diagram is compiled from the record's ground-truth
    ``cas_expression``, so Pass 2 tells the model exactly what structure the
    expression encodes. ``base_id`` is set to ``record["id"]`` for matching.
    """
    result: list[dict[str, Any]] = []
    for record in records:
        variant = dict(record)
        variant["prior_diagram"] = compile_to_graph(
            str(record.get("cas_expression", ""))
        )
        variant["base_id"] = record.get("id")
        variant["paraphrase_source"] = DIAGRAM_LOOP_EVAL_SOURCE_LABEL
        result.append(variant)
    return result


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model_for_eval(
    run_dir: Path,
    *,
    checkpoint: Path | None = None,
    d_model: int | None = None,
    bottleneck_dim: int | None = None,
    with_graph_path: bool | None = None,
    device: str = "cpu",
) -> tuple[StructuredTokenStructuredPredictor, StructuredTokenVocabulary]:
    """Load model + vocabulary from a training run directory.

    When ``with_graph_path`` is ``None`` (default), the manifest is inspected:
    if ``diagram_loop_augmentation_report.variants_per_record > 0``, the graph
    path is initialised.  Pass ``True`` or ``False`` to override.
    """
    manifest_cfg = _manifest_config(run_dir)
    d_model = int(d_model or manifest_cfg.get("d_model", 128))
    bottleneck_dim = int(bottleneck_dim or manifest_cfg.get("bottleneck_dim", 64))
    checkpoint = checkpoint or (run_dir / "best_structured_token_model.pt")
    vocabulary = StructuredTokenVocabulary.load(run_dir / "structured_token_vocab.json")

    if with_graph_path is None:
        dl_report = manifest_cfg.get("diagram_loop_augmentation_report", {})
        with_graph_path = int(dl_report.get("variants_per_record", 0)) > 0

    embedding = StructuredTokenEmbedding(vocab_size=len(vocabulary), d_model=d_model)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)

    if with_graph_path:
        graph_encoder = GraphEncoder(NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64)
        graph_fusion = GraphTextFusion(d_text=d_model, d_graph=64)
        model = StructuredTokenStructuredPredictor(embedding, head, graph_encoder, graph_fusion)
    else:
        model = StructuredTokenStructuredPredictor(embedding, head)

    model.load_state_dict(
        torch.load(str(checkpoint), map_location=device, weights_only=True)
    )
    model.to(torch.device(device))
    return model, vocabulary


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _eval_pass(
    model: StructuredTokenStructuredPredictor,
    records: list[dict[str, Any]],
    vocabulary: StructuredTokenVocabulary,
    *,
    device: str = "cpu",
    batch_size: int = 128,
    max_length: int = 256,
    use_graph_path: bool = False,
) -> dict[str, Any]:
    """Single-pass evaluation returning a sample-level manifest dict."""
    dev = torch.device(device)
    model.eval()
    token_sequences = records_to_structured_token_sequences(records)
    targets_all = batch_targets_from_records(records, device=dev)

    all_logits: dict[str, list[torch.Tensor]] = {k: [] for k in _EVAL_LOGIT_KEYS}
    with torch.no_grad():
        for start in range(0, len(records), batch_size):
            end = start + batch_size
            batch_seqs = token_sequences[start:end]
            batch_recs = records[start:end]
            batch = tokens_to_structured_token_batch(
                batch_seqs, vocabulary, max_length=max_length, device=dev
            )
            graph_batch = None
            if use_graph_path and model.graph_encoder is not None:
                prior_diagrams = [
                    r.get("prior_diagram") or compile_to_graph("")
                    for r in batch_recs
                ]
                graph_batch = serialize_diagram_for_batch(prior_diagrams, device=dev)
            outputs = model(batch, graph_batch=graph_batch)
            for key in _EVAL_LOGIT_KEYS:
                all_logits[key].append(outputs[key])

    logits = {key: torch.cat(parts, dim=0) for key, parts in all_logits.items()}
    return _build_sample_manifest(logits, targets_all, records)


def _build_sample_manifest(
    logits: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Convert raw logits + targets into sample-level predictions and summary."""
    head_preds: dict[str, list[int]] = {}
    head_correct: dict[str, list[bool]] = {}

    # Scalar classification heads
    scalar_heads = {
        "turn_type": "turn_type_logits",
        "expression_family": "expression_family_logits",
        "transition_kind": "transition_kind_logits",
        "noetic": "noetic_logits",
        "domain": "domain_logits",
        "drive": "drive_logits",
        "register_mode": "register_mode_logits",
        "authority": "authority_logits",
    }
    for head_name, logit_key in scalar_heads.items():
        if logit_key not in logits:
            continue
        preds = logits[logit_key].argmax(dim=-1).tolist()
        if head_name in targets:
            tgts = targets[head_name].tolist()
            correct = [p == t for p, t in zip(preds, tgts)]
        else:
            correct = [False] * len(preds)
        head_preds[head_name] = preds
        head_correct[head_name] = correct

    n = len(records)
    all_heads_exact = [
        all(head_correct[h][i] for h in head_correct)
        for i in range(n)
    ]

    samples = []
    for i, record in enumerate(records):
        prediction = {h: head_preds[h][i] for h in head_preds}
        correctness = {h: head_correct[h][i] for h in head_correct}
        samples.append({
            "id": record.get("id"),
            "base_id": record.get("base_id", record.get("id")),
            "bucket": record.get("bucket"),
            "prediction": prediction,
            "correctness": correctness,
            "all_heads_exact": all_heads_exact[i],
        })

    n_exact = sum(all_heads_exact)
    return {
        "n": n,
        "all_heads_exact": n_exact,
        "all_heads_exact_rate": n_exact / n if n > 0 else 0.0,
        "samples": samples,
    }


# ---------------------------------------------------------------------------
# Invariance report
# ---------------------------------------------------------------------------

def build_diagram_loop_invariance_report(
    canonical_samples: list[dict[str, Any]],
    diagram_loop_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a comparison report between canonical and diagram-loop passes."""
    canonical_by_id = {s["id"]: s for s in canonical_samples}
    comparable = [
        s for s in diagram_loop_samples
        if s.get("base_id") in canonical_by_id
    ]
    if not comparable:
        raise ValueError("no diagram-loop samples matched canonical samples")

    head_keys = sorted({
        key
        for s in comparable
        for key in s.get("prediction", {}).keys()
    })

    per_head_consistent = {
        head: sum(
            1 for s in comparable
            if s["prediction"].get(head)
            == canonical_by_id[s["base_id"]]["prediction"].get(head)
        )
        for head in head_keys
    }
    all_consistent = sum(
        1 for s in comparable
        if all(
            s["prediction"].get(h) == canonical_by_id[s["base_id"]]["prediction"].get(h)
            for h in head_keys
        )
    )
    n_dl_exact = sum(1 for s in comparable if s.get("all_heads_exact"))
    n_can_exact = sum(1 for s in canonical_samples if s.get("all_heads_exact"))
    dl_exact_rate = _rate(n_dl_exact, len(comparable))
    can_exact_rate = _rate(n_can_exact, len(canonical_samples))

    return {
        "n_canonical": len(canonical_samples),
        "n_diagram_loop": len(diagram_loop_samples),
        "n_comparable": len(comparable),
        "canonical_all_heads_exact": n_can_exact,
        "canonical_all_heads_exact_rate": can_exact_rate,
        "diagram_loop_all_heads_exact": n_dl_exact,
        "diagram_loop_all_heads_exact_rate": dl_exact_rate,
        "accuracy_delta": round(dl_exact_rate - can_exact_rate, 6),
        "all_heads_prediction_consistent": all_consistent,
        "all_heads_prediction_consistency_rate": _rate(all_consistent, len(comparable)),
        "per_head_prediction_consistency": {
            head: _rate(count, len(comparable))
            for head, count in per_head_consistent.items()
        },
        "by_bucket": _bucket_invariance(canonical_by_id, comparable, head_keys),
    }


def write_diagram_loop_invariance_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Structured-Token Diagram-Loop Invariance Report",
        "",
        f"Canonical samples: {report['n_canonical']}",
        f"Diagram-loop samples: {report['n_diagram_loop']}",
        f"Comparable samples: {report['n_comparable']}",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Canonical all-heads exact | {report['canonical_all_heads_exact_rate']:.3f} |",
        f"| Diagram-loop all-heads exact | {report['diagram_loop_all_heads_exact_rate']:.3f} |",
        f"| Accuracy delta (DL − canonical) | {report['accuracy_delta']:+.3f} |",
        f"| Prediction consistency vs canonical | {report['all_heads_prediction_consistency_rate']:.3f} |",
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
    lines.extend([
        "",
        "## Bucket Summary",
        "",
        "| Bucket | n | DL Exact | Consistency |",
        "|---|---:|---:|---:|",
    ])
    for bucket, entry in sorted(report["by_bucket"].items()):
        lines.append(
            f"| {bucket} | {entry['n']} | "
            f"{entry['diagram_loop_all_heads_exact_rate']:.3f} | "
            f"{entry['all_heads_prediction_consistency_rate']:.3f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
            1 for s in bucket_samples
            if all(
                s["prediction"].get(h)
                == canonical_by_id[s["base_id"]]["prediction"].get(h)
                for h in head_keys
            )
        )
        out[bucket] = {
            "n": len(bucket_samples),
            "diagram_loop_all_heads_exact": exact,
            "diagram_loop_all_heads_exact_rate": _rate(exact, len(bucket_samples)),
            "all_heads_prediction_consistent": consistent,
            "all_heads_prediction_consistency_rate": _rate(consistent, len(bucket_samples)),
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--eval-input", required=True, type=Path)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--prefix", default="diagram_loop_eval")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--d-model", type=int, default=None)
    parser.add_argument("--bottleneck-dim", type=int, default=None)
    parser.add_argument(
        "--with-graph-path",
        action="store_true",
        default=None,
        help="Force graph path on (default: auto-detect from manifest)",
    )
    args = parser.parse_args()

    manifest_cfg = _manifest_config(args.run_dir)
    max_length = int(args.max_length or manifest_cfg.get("max_length", 256))
    with_graph = args.with_graph_path

    model, vocabulary = load_model_for_eval(
        args.run_dir,
        checkpoint=args.checkpoint,
        d_model=args.d_model,
        bottleneck_dim=args.bottleneck_dim,
        with_graph_path=with_graph,
        device=args.device,
    )

    canonical_records = load_level3_jsonl(args.eval_input, limit=args.limit)
    diagram_loop_records = make_diagram_loop_records(canonical_records)

    has_graph = model.graph_encoder is not None

    canonical_manifest = _eval_pass(
        model, canonical_records, vocabulary,
        device=args.device, batch_size=args.batch_size,
        max_length=max_length, use_graph_path=False,
    )
    diagram_loop_manifest = _eval_pass(
        model, diagram_loop_records, vocabulary,
        device=args.device, batch_size=args.batch_size,
        max_length=max_length, use_graph_path=has_graph,
    )
    report = build_diagram_loop_invariance_report(
        list(canonical_manifest["samples"]),
        list(diagram_loop_manifest["samples"]),
    )

    out_dir = args.out_dir or args.run_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / f"{args.prefix}_canonical_manifest.json", canonical_manifest)
    _write_json(out_dir / f"{args.prefix}_manifest.json", diagram_loop_manifest)
    _write_samples(out_dir / f"{args.prefix}_samples.jsonl", diagram_loop_manifest["samples"])
    _write_json(out_dir / f"{args.prefix}_report.json", report)
    write_diagram_loop_invariance_markdown(report, out_dir / f"{args.prefix}_report.md")

    print(
        json.dumps(
            {
                "canonical_all_heads_exact_rate": report["canonical_all_heads_exact_rate"],
                "diagram_loop_all_heads_exact_rate": report["diagram_loop_all_heads_exact_rate"],
                "accuracy_delta": report["accuracy_delta"],
                "all_heads_prediction_consistency_rate": report[
                    "all_heads_prediction_consistency_rate"
                ],
                "report": str(out_dir / f"{args.prefix}_report.md"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
