"""Run a CJT bias/vibration diagnostic across many captured layers."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

from joblib import Parallel, delayed
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.evaluate_cjt_bias_vibration_diagnostic import (  # noqa: E402
    evaluate_cjt_bias_vibration_diagnostic,
)


SCHEMA_VERSION = "cas_harness_cjt_bias_vibration_layer_sweep.v0"


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--summary-output", required=True, type=Path)
    parser.add_argument("--layers", default="nonzero")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-dim", type=int, default=4096)
    parser.add_argument("--min-prompt-groups", type=int, default=5)
    parser.add_argument("--min-delta-rows-per-label", type=int, default=12)
    parser.add_argument("--permutations", type=int, default=1000)
    parser.add_argument("--shuffle-controls", type=int, default=50)
    parser.add_argument("--probe-C", type=float, default=0.25)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    parser.add_argument("--jobs", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_layer_sweep(
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        summary_output_path=args.summary_output,
        layers_arg=args.layers,
        folds=args.folds,
        seed=args.seed,
        text_dim=args.text_dim,
        min_prompt_groups=args.min_prompt_groups,
        min_delta_rows_per_label=args.min_delta_rows_per_label,
        permutations=args.permutations,
        shuffle_controls=args.shuffle_controls,
        probe_C=args.probe_C,
        probe_max_iter=args.probe_max_iter,
        jobs=args.jobs,
    )
    print(json.dumps(public_summary(summary), indent=2, sort_keys=True))
    print(f"[cjt-bias-vibration-sweep] wrote {args.summary_output}")
    return 0


def run_layer_sweep(
    *,
    dataset_path: Path,
    output_dir: Path,
    summary_output_path: Path,
    layers_arg: str,
    folds: int,
    seed: int,
    text_dim: int,
    min_prompt_groups: int,
    min_delta_rows_per_label: int,
    permutations: int,
    shuffle_controls: int,
    probe_C: float = 0.25,
    probe_max_iter: int = 1000,
    jobs: int = 1,
) -> dict[str, Any]:
    layers = resolve_layers(dataset_path, layers_arg)
    output_dir.mkdir(parents=True, exist_ok=True)
    workers = max(1, int(jobs))
    if workers == 1:
        reports = [
            evaluate_layer(
                dataset_path=dataset_path,
                output_dir=output_dir,
                layer=layer,
                folds=folds,
                seed=seed,
                text_dim=text_dim,
                min_prompt_groups=min_prompt_groups,
                min_delta_rows_per_label=min_delta_rows_per_label,
                permutations=permutations,
                shuffle_controls=shuffle_controls,
                probe_C=probe_C,
                probe_max_iter=probe_max_iter,
            )
            for layer in layers
        ]
    else:
        reports = Parallel(n_jobs=workers, prefer="processes")(
            delayed(evaluate_layer)(
                dataset_path=dataset_path,
                output_dir=output_dir,
                layer=layer,
                folds=folds,
                seed=seed,
                text_dim=text_dim,
                min_prompt_groups=min_prompt_groups,
                min_delta_rows_per_label=min_delta_rows_per_label,
                permutations=permutations,
                shuffle_controls=shuffle_controls,
                probe_C=probe_C,
                probe_max_iter=probe_max_iter,
            )
            for layer in layers
        )

    reports = sorted(reports, key=lambda row: row["layer"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset_path),
        "output_dir": str(output_dir),
        "layers": [int(layer) for layer in layers],
        "jobs": workers,
        "report_count": len(reports),
        "passing_layers": [row["layer"] for row in reports if row["status"] == "PASS"],
        "best_hidden_balanced_accuracy": best_report(reports, "hidden_balanced_accuracy"),
        "best_hidden_minus_char_text_balanced_accuracy": best_report(
            reports,
            "hidden_minus_char_text_balanced_accuracy",
        ),
        "reports": reports,
        "claim": (
            "OPEN / NOT LICENSED for CJT bias/vibration hidden response detection unless at least one "
            "layer report is PASS."
        ),
    }
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def evaluate_layer(
    *,
    dataset_path: Path,
    output_dir: Path,
    layer: int,
    folds: int,
    seed: int,
    text_dim: int,
    min_prompt_groups: int,
    min_delta_rows_per_label: int,
    permutations: int,
    shuffle_controls: int,
    probe_C: float,
    probe_max_iter: int,
) -> dict[str, Any]:
    report_path = output_dir / f"cjt_bias_vibration_layer_{layer}.json"
    report = evaluate_cjt_bias_vibration_diagnostic(
        dataset_path=dataset_path,
        layer=layer,
        folds=folds,
        seed=seed,
        text_dim=text_dim,
        min_prompt_groups=min_prompt_groups,
        min_delta_rows_per_label=min_delta_rows_per_label,
        permutations=permutations,
        shuffle_controls=shuffle_controls,
        probe_C=probe_C,
        probe_max_iter=probe_max_iter,
    )
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    summary = summarize_report(report, report_path=report_path)
    print(
        json.dumps(
            {
                "layer": int(layer),
                "status": report["status"],
                "hidden_balanced_accuracy": report["metrics"].get("hidden_balanced_accuracy"),
                "hidden_minus_char_text_balanced_accuracy": report["metrics"].get(
                    "hidden_minus_char_text_balanced_accuracy"
                ),
                "failed_gates": failed_gates(report),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return summary


def resolve_layers(dataset_path: Path, layers_arg: str) -> list[int]:
    with np.load(dataset_path, allow_pickle=True) as data:
        available = [int(layer) for layer in np.asarray(data["layers"], dtype=int).tolist()]
    if layers_arg == "all":
        return available
    if layers_arg == "nonzero":
        return [layer for layer in available if layer != 0]
    requested = [int(part.strip()) for part in layers_arg.split(",") if part.strip()]
    missing = [layer for layer in requested if layer not in available]
    if missing:
        raise RuntimeError(f"Requested layers are absent from dataset: {missing}")
    return requested


def summarize_report(report: dict[str, Any], *, report_path: Path) -> dict[str, Any]:
    metrics = report.get("metrics", {})
    return {
        "layer": int(report.get("layer", -1)),
        "status": str(report.get("status", "")),
        "report": str(report_path),
        "failed_gates": failed_gates(report),
        "hidden_balanced_accuracy": float(metrics.get("hidden_balanced_accuracy", 0.0)),
        "word_text_delta_balanced_accuracy": float(metrics.get("word_text_delta_balanced_accuracy", 0.0)),
        "char_text_delta_balanced_accuracy": float(metrics.get("char_text_delta_balanced_accuracy", 0.0)),
        "length_delta_balanced_accuracy": float(metrics.get("length_delta_balanced_accuracy", 0.0)),
        "l0_delta_balanced_accuracy": metrics.get("l0_delta_balanced_accuracy"),
        "hidden_minus_l0_balanced_accuracy": metrics.get("hidden_minus_l0_balanced_accuracy"),
        "hidden_minus_char_text_balanced_accuracy": float(
            metrics.get("hidden_minus_char_text_balanced_accuracy", 0.0)
        ),
        "within_family_payload_permutation_p": float(
            metrics.get("within_family_payload_permutation_p", 1.0)
        ),
    }


def failed_gates(report: dict[str, Any]) -> list[str]:
    return sorted(key for key, value in report.get("gates", {}).items() if not value)


def best_report(reports: list[dict[str, Any]], metric: str) -> dict[str, Any] | None:
    if not reports:
        return None
    return max(reports, key=lambda row: float(row.get(metric, 0.0)))


def public_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_count": summary["report_count"],
        "passing_layers": summary["passing_layers"],
        "best_hidden_balanced_accuracy": summary["best_hidden_balanced_accuracy"],
        "best_hidden_minus_char_text_balanced_accuracy": summary[
            "best_hidden_minus_char_text_balanced_accuracy"
        ],
        "claim": summary["claim"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
