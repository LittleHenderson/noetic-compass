#!/usr/bin/env python3
"""Cross-channel consistency eval harness for the CAS-SDG-Bench tri-channel benchmark.

Three independent score dimensions per held-out eval record:

  1. **Notation channel**  — exact CAS expression string match (surface form).
  2. **Diagram channel**   — structural graph comparison; predicted expression is
     compiled to a typed graph and compared to the ground-truth graph.
  3. **Color channel**     — color-axis metadata match rate across nodes;
     returns None when color metadata is absent (current state).

Cross-channel consistency rate measures whether the channels *agree* on
correctness:
  - ``notation_correct_diagram_wrong``: surface matches but structure does not.
  - ``diagram_correct_notation_wrong``: structure equivalent, surface differs.
  - ``cross_channel_disagreement_rate``: fraction where channels disagree.

This distinction is the load-bearing methodology contribution.  A model may
produce the right notation tokens while encoding the wrong graph structure, or
reconstruct a non-canonical surface form from a structurally-correct embedding.
Only multi-channel evaluation surfaces these failure modes independently.

Forward-compatibility notes
----------------------------
* **PR #9 (feature/cas-value-keyed-palette)**: once the palette PR lands and the
  compiler starts emitting ``color`` metadata on nodes, the color channel becomes
  active automatically.  No code change required here.
* **feature/diagram-diff-utility**: the ``_diagram_similarity_stub`` function below
  is a temporary Jaccard overlap stand-in.  Once ``diagram_diff.py`` is merged,
  replace the stub call with ``diagram_similarity_score`` from
  ``cas-synthetic/schemas/diagram_diff.py``.  The stub is clearly marked.

CLI
---
    python evaluate_cross_channel_consistency.py \\
        --run-dir  <path>            # must contain best_structured_token_model.pt,
                                     # manifest.json, structured_token_vocab.json
        --eval-input  <path>.jsonl   # held-out Level 3 JSONL
        --out-dir  <path>            # where to write outputs (default: run-dir)
        --prefix   cross_channel_eval
        --device   cpu
        --diagram-similarity-threshold 0.95

Outputs:
  <prefix>_report.md     — human-readable summary table
  <prefix>_report.json   — structured metrics
  <prefix>_samples.jsonl — per-sample three-channel scores
"""

from __future__ import annotations

import argparse
import importlib.util
import json
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
_REPO_ROOT = _PROJECT_ROOT.parent.parent  # .../noetic-compass/ (repo root)
_CAS_SYNTHETIC_ROOT = _REPO_ROOT / "cas-synthetic"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_CAS_SYNTHETIC_ROOT) not in sys.path:
    sys.path.insert(0, str(_CAS_SYNTHETIC_ROOT))
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

# ---------------------------------------------------------------------------
# Diagram similarity stub
# TODO: replace once feature/diagram-diff-utility lands.
# Full `diagram_similarity_score` from `cas-synthetic/schemas/diagram_diff.py`
# uses typed graph isomorphism accounting for node kinds, edge semantics,
# and container structure.  The stub below uses Jaccard overlap over
# `canonical_graph_keys` as an approximation sufficient for smoke-testing
# the harness end-to-end.
# ---------------------------------------------------------------------------

try:
    from schemas.diagram_graph import canonical_graph_keys as _canonical_graph_keys
except ImportError:
    # Fallback: dynamic load via importlib (handles non-package environments).
    _dg_path = _CAS_SYNTHETIC_ROOT / "schemas" / "diagram_graph.py"
    _spec = importlib.util.spec_from_file_location("diagram_graph", _dg_path)
    _dg_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_dg_mod)  # type: ignore[union-attr]
    _canonical_graph_keys = _dg_mod.canonical_graph_keys  # type: ignore[attr-defined]


def _diagram_similarity_stub(
    predicted_graph: dict[str, Any],
    gt_graph: dict[str, Any],
) -> float:
    """Jaccard overlap over canonical_graph_keys.

    ``canonical_graph_keys`` returns a dict with three lists
    (``node_keys``, ``container_keys``, ``edge_keys``); callers are expected
    to convert to sets for set-diff operations.  We flatten all three lists
    into a single combined key set so Jaccard captures structural overlap
    across nodes, containers, and edges in one number.

    TODO: replace once feature/diagram-diff-utility lands.
    """
    predicted_keys_dict = _canonical_graph_keys(predicted_graph)
    gt_keys_dict = _canonical_graph_keys(gt_graph)
    predicted_keys: set[str] = set(predicted_keys_dict.get("node_keys", []))
    predicted_keys.update(predicted_keys_dict.get("container_keys", []))
    predicted_keys.update(predicted_keys_dict.get("edge_keys", []))
    gt_keys: set[str] = set(gt_keys_dict.get("node_keys", []))
    gt_keys.update(gt_keys_dict.get("container_keys", []))
    gt_keys.update(gt_keys_dict.get("edge_keys", []))
    if not predicted_keys and not gt_keys:
        return 1.0
    if not predicted_keys or not gt_keys:
        return 0.0
    intersection = len(predicted_keys & gt_keys)
    union = len(predicted_keys | gt_keys)
    return intersection / union


# ---------------------------------------------------------------------------
# Compiler integration — compile a CAS expression string to a diagram dict.
# ---------------------------------------------------------------------------

def _compile_expression_to_graph(expression: str) -> dict[str, Any] | None:
    """Compile a CAS expression string to a diagram dict using the API compiler.

    Returns None if the compiler is unavailable or if the expression fails to
    compile (e.g. syntax error in predicted output).
    """
    try:
        api_path = _PROJECT_ROOT / "api" / "notation" / "compiler.py"
        if "cas_compiler" not in sys.modules:
            spec = importlib.util.spec_from_file_location("cas_compiler", api_path)
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            sys.modules["cas_compiler"] = mod
        else:
            mod = sys.modules["cas_compiler"]
        result = mod.compile(expression)
        return result.diagram  # type: ignore[attr-defined]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Three-channel scoring — core unit of the harness.
# ---------------------------------------------------------------------------

def score_notation_channel(
    predicted_expression: str,
    gt_expression: str,
) -> bool:
    """Exact string match of predicted vs ground-truth CAS expression."""
    return predicted_expression == gt_expression


def score_diagram_channel(
    predicted_graph: dict[str, Any] | None,
    gt_graph: dict[str, Any] | None,
    *,
    similarity_threshold: float = 0.95,
) -> tuple[bool, float | None]:
    """Structural diagram comparison.

    Returns ``(diagram_match, similarity_score)``.
    ``similarity_score`` is None if either graph could not be compiled.
    """
    if predicted_graph is None or gt_graph is None:
        return False, None
    similarity = _diagram_similarity_stub(predicted_graph, gt_graph)
    return similarity >= similarity_threshold, similarity


def score_color_channel(
    predicted_nodes: list[dict[str, Any]],
    gt_nodes: list[dict[str, Any]],
) -> float | None:
    """Color-axis match rate.

    Compares ``color`` metadata on nodes.  Returns None when color metadata
    is absent from either the predicted or ground-truth graph (current state
    before feature/cas-value-keyed-palette PR #9 lands).

    Once PR #9 lands and the compiler emits ``color`` on nodes, this function
    automatically returns a real rate — no further code changes required.
    """
    predicted_colors = [
        node.get("color") for node in predicted_nodes if "color" in node
    ]
    gt_colors = [node.get("color") for node in gt_nodes if "color" in node]
    if not predicted_colors or not gt_colors:
        return None
    n_comparable = min(len(predicted_colors), len(gt_colors))
    if n_comparable == 0:
        return None
    matches = sum(
        1
        for p, g in zip(predicted_colors[:n_comparable], gt_colors[:n_comparable])
        if p == g
    )
    return matches / n_comparable


def score_three_channels(
    predicted_expression: str,
    gt_expression: str,
    *,
    predicted_graph: dict[str, Any] | None = None,
    gt_graph: dict[str, Any] | None = None,
    diagram_similarity_threshold: float = 0.95,
    compile_graphs: bool = True,
) -> dict[str, Any]:
    """Score one record across all three channels.

    Parameters
    ----------
    predicted_expression:
        CAS expression string produced by the model.
    gt_expression:
        Ground-truth CAS expression from the eval record.
    predicted_graph:
        Pre-compiled diagram dict for the predicted expression.  If None and
        ``compile_graphs`` is True, the harness will compile it on the fly.
    gt_graph:
        Pre-compiled diagram dict for the ground-truth expression.  Same rule.
    diagram_similarity_threshold:
        Minimum similarity score to count as a diagram match (default 0.95).
    compile_graphs:
        Whether to compile expressions to graphs when graphs are not provided.

    Returns
    -------
    dict with:
      notation_match  (bool)
      diagram_match   (bool)
      color_match     (bool | None)
      diagram_similarity  (float | None)
      color_match_rate    (float | None)
    """
    notation_match = score_notation_channel(predicted_expression, gt_expression)

    if compile_graphs:
        if predicted_graph is None:
            predicted_graph = _compile_expression_to_graph(predicted_expression)
        if gt_graph is None:
            gt_graph = _compile_expression_to_graph(gt_expression)

    diagram_match, diagram_similarity = score_diagram_channel(
        predicted_graph,
        gt_graph,
        similarity_threshold=diagram_similarity_threshold,
    )

    predicted_nodes = (predicted_graph or {}).get("nodes", [])
    gt_nodes = (gt_graph or {}).get("nodes", [])
    color_match_rate = score_color_channel(predicted_nodes, gt_nodes)
    color_match: bool | None = None
    if color_match_rate is not None:
        color_match = color_match_rate >= 1.0

    return {
        "notation_match": notation_match,
        "diagram_match": diagram_match,
        "color_match": color_match,
        "diagram_similarity": diagram_similarity,
        "color_match_rate": color_match_rate,
    }


# ---------------------------------------------------------------------------
# Cross-channel consistency aggregation.
# ---------------------------------------------------------------------------

def compute_cross_channel_consistency(
    channel_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute cross-channel consistency metrics over a list of per-record results.

    Each element of ``channel_results`` must contain the keys produced by
    ``score_three_channels``: ``notation_match``, ``diagram_match``,
    ``color_match`` (bool or None).

    Returns
    -------
    dict with:
      n                                   total records
      notation_correct                    count where notation_match is True
      diagram_correct                     count where diagram_match is True
      color_correct                       count where color_match is True (None excluded)
      color_records_with_metadata         count where color_match is not None
      notation_correct_rate
      diagram_correct_rate
      color_correct_rate                  (None if no color metadata available)
      all_channels_consistent             count where all available channels agree
      notation_correct_diagram_wrong      surface match, structure mismatch
      diagram_correct_notation_wrong      structure match, surface mismatch
      cross_channel_disagreement_count    notation and diagram disagree (color excluded)
      cross_channel_disagreement_rate     fraction where notation ≠ diagram
    """
    n = len(channel_results)
    if n == 0:
        return {
            "n": 0,
            "notation_correct": 0,
            "diagram_correct": 0,
            "color_correct": 0,
            "color_records_with_metadata": 0,
            "notation_correct_rate": 0.0,
            "diagram_correct_rate": 0.0,
            "color_correct_rate": None,
            "all_channels_consistent": 0,
            "notation_correct_diagram_wrong": 0,
            "diagram_correct_notation_wrong": 0,
            "cross_channel_disagreement_count": 0,
            "cross_channel_disagreement_rate": 0.0,
        }

    notation_correct = sum(1 for r in channel_results if r.get("notation_match"))
    diagram_correct = sum(1 for r in channel_results if r.get("diagram_match"))

    color_with_meta = [r for r in channel_results if r.get("color_match") is not None]
    color_correct_count = sum(1 for r in color_with_meta if r.get("color_match"))

    notation_correct_diagram_wrong = sum(
        1
        for r in channel_results
        if r.get("notation_match") and not r.get("diagram_match")
    )
    diagram_correct_notation_wrong = sum(
        1
        for r in channel_results
        if r.get("diagram_match") and not r.get("notation_match")
    )
    cross_channel_disagreement = sum(
        1
        for r in channel_results
        if r.get("notation_match") != r.get("diagram_match")
    )

    all_consistent = sum(
        1
        for r in channel_results
        if _all_channels_agree(r)
    )

    return {
        "n": n,
        "notation_correct": notation_correct,
        "diagram_correct": diagram_correct,
        "color_correct": color_correct_count,
        "color_records_with_metadata": len(color_with_meta),
        "notation_correct_rate": _rate(notation_correct, n),
        "diagram_correct_rate": _rate(diagram_correct, n),
        "color_correct_rate": _rate(color_correct_count, len(color_with_meta)) if color_with_meta else None,
        "all_channels_consistent": all_consistent,
        "notation_correct_diagram_wrong": notation_correct_diagram_wrong,
        "diagram_correct_notation_wrong": diagram_correct_notation_wrong,
        "cross_channel_disagreement_count": cross_channel_disagreement,
        "cross_channel_disagreement_rate": _rate(cross_channel_disagreement, n),
    }


def _all_channels_agree(result: dict[str, Any]) -> bool:
    """True if all available channels agree on correctness."""
    notation = result.get("notation_match")
    diagram = result.get("diagram_match")
    color = result.get("color_match")
    if notation != diagram:
        return False
    if color is not None and color != notation:
        return False
    return True


# ---------------------------------------------------------------------------
# Expression reconstruction from structured head predictions.
# Used in Phase 2 model wiring to produce a predicted expression string from
# the structured-token model's head-label outputs.
# ---------------------------------------------------------------------------

def reconstruct_expression_from_heads(prediction: dict[str, Any]) -> str:
    """Reconstruct a canonical CAS expression string from structured head predictions.

    This is a best-effort reconstruction.  The structured heads (noetic, domain,
    drive, registers, register_mode) do not always capture the full richness of
    compound expressions — this is precisely why the diagram channel provides an
    independent structural verification that the notation channel cannot.

    Reconstruction rules (all from CAS v7.7 semantics):
      ^{noetic}                          — always present
      ^{domain}                          — if domain != 'P' or drive present
      _{F{drive}}                        — if drive present
      |{register}                        — if register_mode == 'single'
      |<{r1},{r2},...>                   — if register_mode == 'set_spec'
      (X + Y + ...) for co_presence      — if register_mode == 'co_presence'
    """
    noetic = prediction.get("noetic", 0)
    if isinstance(noetic, str):
        try:
            noetic = int(noetic)
        except (ValueError, TypeError):
            noetic = 0

    domain = prediction.get("domain", "P")
    drive = prediction.get("drive")
    registers = prediction.get("registers") or []
    register_mode = prediction.get("register_mode", "none")

    base = f"^{noetic}"
    if domain and domain != "P" or drive:
        base += f"^{domain}"
    if drive and drive not in (None, "None", ""):
        drive_n = str(drive).replace("F", "")
        base += f"_{{F{drive_n}}}"

    if register_mode == "single" and registers:
        reg = registers[0] if isinstance(registers, list) else registers
        base += f"|{reg}"
    elif register_mode in ("set_spec",) and registers:
        reg_list = registers if isinstance(registers, list) else [registers]
        base += "|<" + ",".join(str(r) for r in reg_list) + ">"
    elif register_mode == "co_presence" and isinstance(registers, list) and len(registers) > 1:
        parts = [f"{base}|{r}" for r in registers]
        return " + ".join(parts)

    return base


# ---------------------------------------------------------------------------
# Full model-eval wiring (Phase 2).
# ---------------------------------------------------------------------------

def evaluate_records_cross_channel(
    records: list[dict[str, Any]],
    *,
    run_dir: Path,
    checkpoint: Path | None = None,
    d_model: int | None = None,
    bottleneck_dim: int | None = None,
    batch_size: int = 128,
    max_length: int | None = None,
    device: str = "cpu",
    diagram_similarity_threshold: float = 0.95,
) -> list[dict[str, Any]]:
    """Run the three-channel eval over records using a saved model checkpoint.

    Loads the structured-token model from ``run_dir``, runs inference to get
    head-label predictions, reconstructs a predicted expression from each, then
    scores all three channels.

    Returns a list of per-sample dicts with the full three-channel scores plus
    provenance fields (id, bucket, cas_expression, predicted_expression).
    """
    manifest_config = _manifest_config(run_dir)
    d_model = int(d_model or manifest_config.get("d_model", 128))
    bottleneck_dim = int(bottleneck_dim or manifest_config.get("bottleneck_dim", 64))
    max_length = int(max_length or manifest_config.get("max_length", 256))
    checkpoint = checkpoint or (run_dir / "best_structured_token_model.pt")
    vocab_path = run_dir / "structured_token_vocab.json"

    if not checkpoint.exists():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint}")
    if not vocab_path.exists():
        raise FileNotFoundError(f"vocabulary not found: {vocab_path}")

    vocabulary = StructuredTokenVocabulary.load(vocab_path)
    embedding = StructuredTokenEmbedding(vocab_size=len(vocabulary), d_model=d_model)
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)
    model = StructuredTokenStructuredPredictor(embedding, head)
    model.load_state_dict(
        torch.load(checkpoint, map_location=device, weights_only=True)
    )
    model.to(torch.device(device))

    manifest = evaluate_structured_token_prediction(
        model,
        records,
        vocabulary,
        device=device,
        batch_size=batch_size,
        max_length=max_length,
    )
    raw_samples = manifest.get("samples", [])

    per_record_samples: list[dict[str, Any]] = []
    for sample in raw_samples:
        gt_expression = str(sample.get("cas_expression") or "")
        prediction_heads = dict(sample.get("prediction") or {})
        predicted_expression = reconstruct_expression_from_heads(prediction_heads)

        channel_scores = score_three_channels(
            predicted_expression,
            gt_expression,
            diagram_similarity_threshold=diagram_similarity_threshold,
        )
        per_record_samples.append(
            {
                "id": sample.get("id"),
                "bucket": sample.get("bucket"),
                "cas_expression": gt_expression,
                "predicted_expression": predicted_expression,
                "all_heads_exact": sample.get("all_heads_exact"),
                "head_correct": sample.get("head_correct"),
                "prediction": prediction_heads,
                "notation_match": channel_scores["notation_match"],
                "diagram_match": channel_scores["diagram_match"],
                "color_match": channel_scores["color_match"],
                "diagram_similarity": channel_scores["diagram_similarity"],
                "color_match_rate": channel_scores["color_match_rate"],
            }
        )
    return per_record_samples


# ---------------------------------------------------------------------------
# Report building and writing.
# ---------------------------------------------------------------------------

def build_cross_channel_report(
    samples: list[dict[str, Any]],
    *,
    diagram_similarity_threshold: float = 0.95,
) -> dict[str, Any]:
    """Build the aggregate cross-channel consistency report from per-sample dicts."""
    channel_results = [
        {
            "notation_match": s.get("notation_match"),
            "diagram_match": s.get("diagram_match"),
            "color_match": s.get("color_match"),
        }
        for s in samples
    ]
    consistency = compute_cross_channel_consistency(channel_results)

    # Bucket breakdown.
    by_bucket: dict[str, list[dict[str, Any]]] = {}
    for s in samples:
        bucket = str(s.get("bucket") or "unknown")
        by_bucket.setdefault(bucket, []).append(s)

    bucket_stats: dict[str, Any] = {}
    for bucket, bucket_samples in sorted(by_bucket.items()):
        bucket_channel_results = [
            {
                "notation_match": s.get("notation_match"),
                "diagram_match": s.get("diagram_match"),
                "color_match": s.get("color_match"),
            }
            for s in bucket_samples
        ]
        bucket_stats[bucket] = compute_cross_channel_consistency(bucket_channel_results)

    return {
        "diagram_similarity_threshold": diagram_similarity_threshold,
        "aggregate": consistency,
        "by_bucket": bucket_stats,
    }


def write_cross_channel_markdown(report: dict[str, Any], path: Path) -> None:
    """Write a human-readable Markdown summary of the cross-channel consistency report."""
    agg = report["aggregate"]
    threshold = report.get("diagram_similarity_threshold", 0.95)
    color_rate = agg.get("color_correct_rate")
    color_str = f"{color_rate:.3f}" if color_rate is not None else "N/A (no color metadata)"

    lines = [
        "# CAS Cross-Channel Consistency Eval Report",
        "",
        f"Diagram similarity threshold: {threshold}",
        f"Records: {agg['n']}",
        "",
        "## Aggregate Channel Scores",
        "",
        "| Channel | Correct | Rate |",
        "|---|---:|---:|",
        f"| Notation (exact match) | {agg['notation_correct']} | {agg['notation_correct_rate']:.3f} |",
        f"| Diagram (structural ≥{threshold}) | {agg['diagram_correct']} | {agg['diagram_correct_rate']:.3f} |",
        f"| Color (metadata match) | {agg['color_correct']} | {color_str} |",
        "",
        "## Cross-Channel Consistency",
        "",
        "| Metric | Count | Rate |",
        "|---|---:|---:|",
        f"| All channels consistent | {agg['all_channels_consistent']} | {_rate(agg['all_channels_consistent'], agg['n']):.3f} |",
        f"| Notation correct, diagram wrong | {agg['notation_correct_diagram_wrong']} | {_rate(agg['notation_correct_diagram_wrong'], agg['n']):.3f} |",
        f"| Diagram correct, notation wrong | {agg['diagram_correct_notation_wrong']} | {_rate(agg['diagram_correct_notation_wrong'], agg['n']):.3f} |",
        f"| Cross-channel disagreement | {agg['cross_channel_disagreement_count']} | {agg['cross_channel_disagreement_rate']:.3f} |",
        "",
        "## Bucket Breakdown",
        "",
        "| Bucket | n | Notation | Diagram | Disagree |",
        "|---|---:|---:|---:|---:|",
    ]
    for bucket, stats in sorted(report.get("by_bucket", {}).items()):
        lines.append(
            f"| {bucket} | {stats['n']} "
            f"| {stats['notation_correct_rate']:.3f} "
            f"| {stats['diagram_correct_rate']:.3f} "
            f"| {stats['cross_channel_disagreement_rate']:.3f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Utilities.
# ---------------------------------------------------------------------------

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
# CLI entry point.
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
        help="Training run directory with best_structured_token_model.pt, manifest.json, structured_token_vocab.json",
    )
    parser.add_argument(
        "--eval-input",
        required=True,
        type=Path,
        help="Path to held-out eval JSONL",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (defaults to --run-dir)",
    )
    parser.add_argument(
        "--prefix",
        default="cross_channel_eval",
        help="Filename prefix for output files",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Torch device (cpu or cuda; default: cpu)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--d-model",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--bottleneck-dim",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of eval records (for debugging)",
    )
    parser.add_argument(
        "--diagram-similarity-threshold",
        type=float,
        default=0.95,
        help="Minimum diagram similarity to count as a match (default: 0.95)",
    )
    args = parser.parse_args()

    if not args.eval_input.exists():
        print(f"ERROR: eval-input not found: {args.eval_input}", file=sys.stderr)
        return 1
    if not args.run_dir.exists():
        print(f"ERROR: run-dir not found: {args.run_dir}", file=sys.stderr)
        return 1

    records = load_level3_jsonl(args.eval_input, limit=args.limit)

    samples = evaluate_records_cross_channel(
        records,
        run_dir=args.run_dir,
        d_model=args.d_model,
        bottleneck_dim=args.bottleneck_dim,
        batch_size=args.batch_size,
        max_length=args.max_length,
        device=args.device,
        diagram_similarity_threshold=args.diagram_similarity_threshold,
    )

    report = build_cross_channel_report(
        samples,
        diagram_similarity_threshold=args.diagram_similarity_threshold,
    )

    out_dir = args.out_dir or args.run_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    report_md_out = out_dir / f"{args.prefix}_report.md"
    report_json_out = out_dir / f"{args.prefix}_report.json"
    samples_out = out_dir / f"{args.prefix}_samples.jsonl"

    write_cross_channel_markdown(report, report_md_out)
    _write_json(report_json_out, report)
    _write_samples(samples_out, samples)

    agg = report["aggregate"]
    print(
        json.dumps(
            {
                "n": agg["n"],
                "notation_correct_rate": agg["notation_correct_rate"],
                "diagram_correct_rate": agg["diagram_correct_rate"],
                "color_correct_rate": agg["color_correct_rate"],
                "cross_channel_disagreement_rate": agg["cross_channel_disagreement_rate"],
                "notation_correct_diagram_wrong": agg["notation_correct_diagram_wrong"],
                "diagram_correct_notation_wrong": agg["diagram_correct_notation_wrong"],
                "report": str(report_md_out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
