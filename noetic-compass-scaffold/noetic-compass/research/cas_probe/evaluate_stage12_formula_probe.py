"""Evaluate Stage 12 equation/formula readout and readout-subspace ablation."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import evaluate_stage6_role_bound_full as stage6
import evaluate_stage11_expression_shape_probe as stage11


_HERE = Path(__file__).resolve().parent
_FORMULA_LABELS = (
    "relation_dependency",
    "typed_program",
    "production_recipe",
    "yield_query",
    "state_vector",
    "emergent_register_assignment",
    "membership_assertion",
    "cardinality_assertion",
    "set_operation_formula",
    "cover_partition_formula",
)
_LABEL_TO_INDEX = {label: i for i, label in enumerate(_FORMULA_LABELS)}
_READOUT_KEYS = {
    "focus_token": "X_focus",
    "final_token": "X_final",
    "mean_over_seq_len": "X_mean",
}
_GATES = {
    "chance_accuracy": 0.10,
    "readout_test_acc_min": 0.25,
    "test_acc_lift_over_text_min": 0.05,
    "mcnemar_p_max": 0.05,
    "ablation_acc_slack_over_chance": 0.05,
    "random_ge_task_empirical_p_max": 0.05,
}


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows = stage6._load_jsonl(path)
    for row in rows:
        row["hard_contrast_labels"] = [
            int(_LABEL_TO_INDEX[str(label)]) for label in row["hard_contrast_formulas"]
        ]
    return rows


def _split_indices(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> dict[str, Any]:
    import numpy as np

    split_to_indices: dict[str, list[int]] = defaultdict(list)
    for i, sid in enumerate(sample_ids):
        if sid not in rows_by_id:
            raise ValueError(f"activation sample_id missing from input JSONL: {sid}")
        split_to_indices[str(rows_by_id[sid]["split"])].append(i)
    missing = sorted({"train", "val", "test"} - set(split_to_indices))
    if missing:
        raise ValueError(f"missing required splits: {missing}")
    return {split: np.array(indices, dtype=np.int64) for split, indices in split_to_indices.items()}


def _class_distribution(y: Any, indices: Any) -> dict[str, int]:
    return {
        _FORMULA_LABELS[int(k)]: int(v)
        for k, v in sorted(Counter(int(x) for x in y[indices].tolist()).items())
    }


def _status(headline: dict[str, Any], best_text: dict[str, Any], paired: dict[str, Any], ablation: dict[str, Any]) -> str:
    text_lift = float(headline["test"]["acc"] - best_text["test"]["acc"])
    readout_pass = (
        float(headline["test"]["acc"]) >= _GATES["readout_test_acc_min"]
        and text_lift >= _GATES["test_acc_lift_over_text_min"]
        and float(paired["exact_binomial_mcnemar_p"]) < _GATES["mcnemar_p_max"]
    )
    ablated_acc = float(ablation["targeted_subspace_ablation"]["test"]["acc"])
    random_p = float(ablation["random_complement_controls"]["one_sided_empirical_p_random_ge_targeted"])
    ablation_pass = (
        ablated_acc <= _GATES["chance_accuracy"] + _GATES["ablation_acc_slack_over_chance"]
        and random_p < _GATES["random_ge_task_empirical_p_max"]
    )
    if readout_pass and ablation_pass:
        return "STAGE12_EQUATIONS_FORMULAS_FULL_PASS"
    if readout_pass:
        return "STAGE12_EQUATIONS_FORMULAS_READOUT_ONLY"
    if headline["test"]["acc"] > best_text["test"]["acc"]:
        return "STAGE12_EQUATIONS_FORMULAS_GREY"
    return "STAGE12_EQUATIONS_FORMULAS_NULL"


def _strip_predictions(block: dict[str, Any]) -> dict[str, Any]:
    return {k: {kk: vv for kk, vv in v.items() if kk != "test_predictions"} for k, v in block.items()}


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    headline = report["headline"]
    best_text_name = report["best_text_baseline_by_val"]
    best_text = report["language_baselines"][best_text_name]
    best_metadata_name = report["best_metadata_baseline_by_val"]
    best_metadata = report["metadata_baselines"][best_metadata_name]
    ablation = report["ablation"]
    lines = [
        "# Stage 12 Equations And Formulas Probe Report",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        f"- Readout: `{headline['readout']}`",
        f"- Layer: `{headline['layer']}`",
        f"- Activation test accuracy: `{headline['test']['acc']:.4f}`",
        f"- Best text baseline: `{best_text_name}` test `{best_text['test']['acc']:.4f}`",
        f"- Best metadata baseline: `{best_metadata_name}` test `{best_metadata['test']['acc']:.4f}`",
        f"- Lift over text: `{headline['test_acc_lift_over_best_text']:+.4f}`",
        f"- McNemar p vs text: `{headline['paired_vs_best_text']['exact_binomial_mcnemar_p']:.6g}`",
        "",
        "## Ablation",
        "",
        f"- Subspace rank: `{ablation['subspace']['rank']}`",
        f"- Targeted ablated accuracy: `{ablation['targeted_subspace_ablation']['test']['acc']:.4f}`",
        f"- Targeted disruption: `{ablation['targeted_subspace_ablation']['disruption']:+.4f}`",
        f"- Random max disruption: `{ablation['random_complement_controls']['max_disruption']:+.4f}`",
        f"- p(random >= targeted): `{ablation['random_complement_controls']['one_sided_empirical_p_random_ge_targeted']:.4f}`",
        "",
        "## Boundary",
        "",
        "This is a hidden-state readout and readout-subspace ablation result for compiler-validated "
        "CAS equation/formula families. It does not prove that Pythia executes formulas, parses raw "
        "CAS symbols, performs compiler validation internally, controls visible generation, or generalizes cross-model.",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--out-md", default="STAGE12_EQUATIONS_FORMULAS_PROBE_REPORT_20260517.md")
    parser.add_argument("--n-random", type=int, default=30)
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)

    try:
        import numpy as np
    except ImportError as exc:
        print(f"missing dependency: {exc}", file=sys.stderr)
        return 2

    stage6._LABELS = tuple(range(len(_FORMULA_LABELS)))
    stage11._SHAPE_LABELS = _FORMULA_LABELS
    rows = _load_rows(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    missing = sorted(set(sample_ids) - set(rows_by_id))
    if missing:
        raise SystemExit(f"activation sample ids missing from input JSONL: {missing[:5]}")

    y = data["y"]
    english = np.array([rows_by_id[sid]["english"] for sid in sample_ids], dtype=object)
    splits = _split_indices(rows_by_id, sample_ids)
    idx_train = splits["train"]
    idx_val = splits["val"]
    idx_test = splits["test"]

    started = time.perf_counter()
    language_baselines = stage6._fit_language_baselines(english, y, idx_train, idx_val, idx_test)
    metadata_baselines = stage6._fit_metadata_baselines(rows, sample_ids, y, idx_train, idx_val, idx_test)
    best_text_name, best_text = max(
        ((name, row) for name, row in language_baselines.items() if name not in {"majority", "stratified_dummy"}),
        key=lambda item: (item[1]["val"]["acc"], item[1]["val"]["macro_f1"], item[1]["test"]["acc"], item[0]),
    )
    best_metadata_name, best_metadata = max(
        metadata_baselines.items(),
        key=lambda item: (item[1]["val"]["acc"], item[1]["val"]["macro_f1"], item[1]["test"]["acc"], item[0]),
    )
    best_text_correct = np.array(best_text["test_predictions"], dtype=np.int64) == y[idx_test]
    best_metadata_correct = np.array(best_metadata["test_predictions"], dtype=np.int64) == y[idx_test]

    readouts: dict[str, Any] = {}
    for readout_name, array_key in _READOUT_KEYS.items():
        readouts[readout_name] = stage6._fit_readout_layers(
            data[array_key],
            y,
            idx_train,
            idx_val,
            idx_test,
            readout_name,
        )

    overall_readout_name, overall = max(
        readouts.items(),
        key=lambda item: (
            item[1]["headline"]["val"]["acc"],
            item[1]["headline"]["val"]["macro_f1"],
            -int(item[1]["headline"]["layer"]),
            item[0],
        ),
    )
    headline_layer = int(overall["headline"]["layer"])
    headline_predictions = np.array(overall["headline_predictions"], dtype=np.int64)
    headline_correct = headline_predictions == y[idx_test]
    paired_vs_text = stage11._paired(headline_correct, best_text_correct, "activation_headline", best_text_name)
    paired_vs_metadata = stage11._paired(headline_correct, best_metadata_correct, "activation_headline", best_metadata_name)

    X_layer = data[_READOUT_KEYS[overall_readout_name]][:, headline_layer, :]
    ablation = stage11._run_ablation(X_layer, y, idx_train, idx_val, idx_test, int(args.n_random))
    status = _status(overall["headline"], best_text, paired_vs_text, ablation)

    report = {
        "schema_version": "stage12_equations_formulas_probe_report.v1",
        "experiment": "Stage 12 CAS equation/formula family readout and readout-subspace ablation",
        "status": status,
        "decision_gates": _GATES,
        "label_names": list(_FORMULA_LABELS),
        "input_file": input_path.name,
        "input_sha256": stage6._sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": stage6._sha256_of_file(activations_path),
        "n_records": int(len(sample_ids)),
        "split": {
            "train": int(len(idx_train)),
            "val": int(len(idx_val)),
            "test": int(len(idx_test)),
            "train_distribution": _class_distribution(y, idx_train),
            "val_distribution": _class_distribution(y, idx_val),
            "test_distribution": _class_distribution(y, idx_test),
        },
        "language_baselines": _strip_predictions(language_baselines),
        "metadata_baselines": _strip_predictions(metadata_baselines),
        "best_text_baseline_by_val": best_text_name,
        "best_metadata_baseline_by_val": best_metadata_name,
        "readouts": {
            name: {k: v for k, v in row.items() if k != "headline_predictions"}
            for name, row in readouts.items()
        },
        "headline": {
            "readout": overall_readout_name,
            "layer": headline_layer,
            "val": overall["headline"]["val"],
            "test": overall["headline"]["test"],
            "test_acc_lift_over_best_text": float(overall["headline"]["test"]["acc"] - best_text["test"]["acc"]),
            "test_acc_lift_over_best_metadata": float(overall["headline"]["test"]["acc"] - best_metadata["test"]["acc"]),
            "paired_vs_best_text": paired_vs_text,
            "paired_vs_best_metadata": paired_vs_metadata,
        },
        "ablation": ablation,
        "reserved_interpretation": (
            "This is hidden-state readout plus readout-subspace ablation for compiler-validated "
            "CAS equation/formula families. A pass does not prove raw-symbol parsing, formula execution, "
            "or generation steering."
        ),
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report, out_md)
    print(
        json.dumps(
            {
                "status": status,
                "headline": report["headline"],
                "ablation": {
                    "rank": ablation["subspace"]["rank"],
                    "ablated_acc": ablation["targeted_subspace_ablation"]["test"]["acc"],
                    "random_p": ablation["random_complement_controls"]["one_sided_empirical_p_random_ge_targeted"],
                },
                "best_text": best_text_name,
            },
            indent=2,
        )
    )
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
