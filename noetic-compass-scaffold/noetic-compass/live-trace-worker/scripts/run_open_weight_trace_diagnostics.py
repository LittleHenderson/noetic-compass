"""Run Stage-7 trace diagnostics for an open-weight Foundation-28 dataset.

This is the pre-steering gate from the original CAS Harness methodology:

1. Fit the balanced linear Foundation readout across model layers.
2. Compute lacunarity as Var/Mean^2 over per-class readout scores.
3. Classify the layer trajectory as Stabilizing / Amplifying /
   Oscillatory / Neutral.

The fractal classifier here is an open-weight numeric trace classifier over
per-layer readout scores. It uses the same output vocabulary as the CAS engine
fractal classifier, but the report labels it as ``numeric_trace_proxy`` unless
and until the discrete CAS orbit object is available.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


REGISTERS = ("T", "A", "f", "E")
FOUNDATION_LABELS = tuple(f"F{drive}|{register}" for drive in range(1, 8) for register in REGISTERS)
LACUNARITY_PASS_THRESHOLD = 0.05
PYTHIA_160M_FOUNDATION_LACUNARITY = 0.021
PYTHIA_1B_FOUNDATION_LACUNARITY = 0.015
QWEN15B_FOUNDATION_LACUNARITY = 0.0084


@dataclass(frozen=True)
class DiagnosticsConfig:
    dataset: Path
    scenario_path: Path
    output: Path
    bridge_report: Path | None = None
    ablation_report: Path | None = None
    output_md: Path | None = None
    axis: str = "foundation"
    probe_C: float = 0.1
    probe_max_iter: int = 1000
    layer_start: int | None = None
    layer_end: int | None = None
    seed: int = 42


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--scenario-path", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bridge-report", type=Path)
    parser.add_argument("--ablation-report", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--axis", default="foundation", choices=("foundation",))
    parser.add_argument("--probe-C", type=float, default=0.1)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    parser.add_argument("--layer-start", type=int)
    parser.add_argument("--layer-end", type=int)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = DiagnosticsConfig(
        dataset=args.dataset,
        scenario_path=args.scenario_path,
        output=args.output,
        bridge_report=args.bridge_report,
        ablation_report=args.ablation_report,
        output_md=args.output_md,
        axis=args.axis,
        probe_C=args.probe_C,
        probe_max_iter=args.probe_max_iter,
        layer_start=args.layer_start,
        layer_end=args.layer_end,
        seed=args.seed,
    )
    report = run_trace_diagnostics(config)
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if config.output_md:
        config.output_md.parent.mkdir(parents=True, exist_ok=True)
        config.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"[trace-diagnostics] status={report['status']}")
    print(f"[trace-diagnostics] wrote {config.output}")
    if config.output_md:
        print(f"[trace-diagnostics] wrote {config.output_md}")
    return 0


def run_trace_diagnostics(config: DiagnosticsConfig) -> dict[str, Any]:
    scenario_meta = load_scenario_meta(config.scenario_path)
    with np.load(config.dataset, allow_pickle=True) as data:
        features = data["features"].astype(np.float32)
        layers = np.asarray(data["layers"], dtype=int)
        scenario_ids = np.asarray(data["scenario_ids"], dtype=str)
        labels = np.asarray(data[f"labels_{config.axis}"], dtype=str)

    split = split_from_scenario_meta(scenario_ids, scenario_meta)
    selected_layers = select_layers(layers.tolist(), config.layer_start, config.layer_end)
    layer_reports = []
    for layer_position, layer in enumerate(layers.tolist()):
        if layer not in selected_layers:
            continue
        layer_report = fit_eval_layer(
            features=features,
            labels=labels,
            split=split,
            layer_position=layer_position,
            layer=layer,
            C=config.probe_C,
            max_iter=config.probe_max_iter,
            seed=config.seed,
        )
        layer_reports.append(layer_report)
        print(
            "[trace-diagnostics] "
            f"layer={layer} test_acc={layer_report['test_acc']:.6f} "
            f"state_lacunarity={layer_report['state_lacunarity']:.6f}",
            flush=True,
        )

    if not layer_reports:
        raise RuntimeError("No layers selected for diagnostics.")

    validation_best_layer = max(layer_reports, key=lambda row: (row["val_acc"], row["test_acc"]))
    test_trajectory = [row["test_acc"] for row in layer_reports]
    val_trajectory = [row["val_acc"] for row in layer_reports]
    bridge_summary = load_bridge_summary(config.bridge_report)
    gate_layer = select_gate_layer(layer_reports, bridge_summary)
    state_lacunarity = float(gate_layer["state_lacunarity"])
    class_name = lacunarity_class(state_lacunarity)
    fractal = classify_numeric_trace(test_trajectory)
    ablation_summary = load_ablation_summary(config.ablation_report)
    gate_passed = state_lacunarity <= LACUNARITY_PASS_THRESHOLD and fractal["class"] in {
        "Stabilizing",
        "Amplifying",
    }

    return {
        "schema_version": "cas_harness_open_weight_trace_diagnostics.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "TRACE_DIAGNOSTICS_PASS" if gate_passed else "TRACE_DIAGNOSTICS_REVIEW",
        "axis": config.axis,
        "dataset": str(config.dataset),
        "dataset_sha256": sha256_file(config.dataset),
        "scenario_path": str(config.scenario_path),
        "scenario_path_sha256": sha256_file(config.scenario_path),
        "probe_readout": {
            "kind": "balanced_logistic_linear_probe",
            "C": config.probe_C,
            "max_iter": config.probe_max_iter,
            "class_weight": "balanced",
            "standardized": True,
        },
        "layer_scan": {
            "layers": selected_layers,
            "n_layers": len(selected_layers),
            "best_layer": int(gate_layer["layer"]),
            "best_layer_position": int(gate_layer["layer_position"]),
            "best_test_acc": round(float(gate_layer["test_acc"]), 6),
            "best_test_macro_f1": round(float(gate_layer["test_macro_f1"]), 6),
            "gate_layer_selection": gate_layer["selection_reason"],
            "validation_best_layer": int(validation_best_layer["layer"]),
            "validation_best_val_acc": round(float(validation_best_layer["val_acc"]), 6),
            "validation_best_test_acc": round(float(validation_best_layer["test_acc"]), 6),
            "test_trajectory": [round(float(v), 6) for v in test_trajectory],
            "val_trajectory": [round(float(v), 6) for v in val_trajectory],
            "per_layer": layer_reports,
        },
        "lacunarity_gate": {
            "formula": "Var(per_class_test_accuracy) / Mean(per_class_test_accuracy)^2",
            "score": round(state_lacunarity, 6),
            "classification": class_name,
            "threshold": LACUNARITY_PASS_THRESHOLD,
            "passed": state_lacunarity <= LACUNARITY_PASS_THRESHOLD,
            "per_class_accuracy": gate_layer["per_class_accuracy"],
            "per_drive_accuracy": gate_layer["per_drive_accuracy"],
            "per_register_accuracy": gate_layer["per_register_accuracy"],
            "drive_lacunarity": round(float(gate_layer["drive_lacunarity"]), 6),
            "register_lacunarity": round(float(gate_layer["register_lacunarity"]), 6),
            "comparators": {
                "pythia_160m_foundation": PYTHIA_160M_FOUNDATION_LACUNARITY,
                "pythia_1b_foundation": PYTHIA_1B_FOUNDATION_LACUNARITY,
                "qwen25_15b_foundation": QWEN15B_FOUNDATION_LACUNARITY,
            },
        },
        "fractal_preflight": {
            "classifier_kind": "numeric_trace_proxy",
            "class": fractal["class"],
            "passed": fractal["class"] in {"Stabilizing", "Amplifying"},
            "reason": fractal["reason"],
            "metrics": fractal["metrics"],
            "important_limit": (
                "This classifies the per-layer Foundation readout trajectory. "
                "It uses the CAS fractal vocabulary, but is not the discrete "
                "cas-engine orbit classifier over CognitiveFractal objects."
            ),
        },
        "bridge_summary": bridge_summary,
        "ablation_summary": ablation_summary,
        "produced_outputs": [
            "foundation_readout_layer_trajectory",
            "foundation_lacunarity_gate",
            "numeric_trace_fractal_preflight",
            "worker_evidence_manifest",
        ],
        "missing_outputs": [
            "discrete_cas_engine_fractal_orbit",
            "final_verifier_accept_suppress_merge",
            "full_evidence_packet",
        ],
    }


def load_scenario_meta(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        raise RuntimeError("Scenario file must contain a scenarios list.")
    meta: dict[str, dict[str, Any]] = {}
    for scenario in scenarios:
        scenario_id = str(scenario.get("id", ""))
        if not scenario_id:
            raise RuntimeError("Scenario row missing id.")
        row_meta = dict(scenario.get("metadata") or {})
        axes = dict(scenario.get("expected_cas_axes") or {})
        row_meta["foundation"] = canonical_foundation(axes.get("foundation") or row_meta.get("foundation"))
        row_meta["split"] = str(row_meta.get("split") or "train")
        meta[scenario_id] = row_meta
    return meta


def split_from_scenario_meta(
    scenario_ids: np.ndarray,
    scenario_meta: dict[str, dict[str, Any]],
) -> dict[str, np.ndarray]:
    by_split: dict[str, list[int]] = {"train": [], "val": [], "test": []}
    for index, scenario_id in enumerate(scenario_ids.tolist()):
        split = str(scenario_meta[str(scenario_id)]["split"])
        if split not in by_split:
            raise RuntimeError(f"Unsupported scenario split {split!r} for {scenario_id!r}.")
        by_split[split].append(index)
    return {name: np.asarray(indices, dtype=int) for name, indices in by_split.items()}


def select_layers(layers: list[int], start: int | None, end: int | None) -> list[int]:
    selected = []
    for layer in layers:
        if start is not None and layer < start:
            continue
        if end is not None and layer > end:
            continue
        selected.append(int(layer))
    return selected


def select_gate_layer(
    layer_reports: list[dict[str, Any]],
    bridge_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    if bridge_summary and bridge_summary.get("readout_layer") is not None:
        bridge_layer = int(bridge_summary["readout_layer"])
        for row in layer_reports:
            if int(row["layer"]) == bridge_layer:
                selected = dict(row)
                selected["selection_reason"] = "bridge_report_readout_layer"
                return selected
    selected = dict(max(layer_reports, key=lambda row: (row["val_acc"], row["test_acc"])))
    selected["selection_reason"] = "validation_best_layer"
    return selected


def fit_eval_layer(
    *,
    features: np.ndarray,
    labels: np.ndarray,
    split: dict[str, np.ndarray],
    layer_position: int,
    layer: int,
    C: float,
    max_iter: int,
    seed: int,
) -> dict[str, Any]:
    x = features[:, layer_position, :]
    clf = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=C,
            class_weight="balanced",
            max_iter=max_iter,
            random_state=seed,
            solver="lbfgs",
        ),
    )
    clf.fit(x[split["train"]], labels[split["train"]])
    train_pred = clf.predict(x[split["train"]])
    val_pred = clf.predict(x[split["val"]])
    test_pred = clf.predict(x[split["test"]])
    test_labels = labels[split["test"]]
    per_class = grouped_accuracy(test_labels, test_pred, lambda label: label)
    per_drive = grouped_accuracy(test_labels, test_pred, foundation_drive)
    per_register = grouped_accuracy(test_labels, test_pred, foundation_register)
    class_scores = [per_class.get(label, 0.0) for label in FOUNDATION_LABELS]
    drive_scores = [per_drive.get(f"F{drive}", 0.0) for drive in range(1, 8)]
    register_scores = [per_register.get(register, 0.0) for register in REGISTERS]
    return {
        "layer": int(layer),
        "layer_position": int(layer_position),
        "train_acc": round(binary_accuracy(labels[split["train"]], train_pred), 6),
        "val_acc": round(binary_accuracy(labels[split["val"]], val_pred), 6),
        "test_acc": round(binary_accuracy(test_labels, test_pred), 6),
        "test_macro_f1": round(macro_f1(test_labels, test_pred), 6),
        "state_lacunarity": round(lacunarity_from_scores(class_scores), 6),
        "drive_lacunarity": round(lacunarity_from_scores(drive_scores), 6),
        "register_lacunarity": round(lacunarity_from_scores(register_scores), 6),
        "per_class_accuracy": round_dict(per_class),
        "per_drive_accuracy": round_dict(per_drive),
        "per_register_accuracy": round_dict(per_register),
    }


def grouped_accuracy(
    labels: np.ndarray,
    predicted: np.ndarray,
    key_fn: Callable[[str], str],
) -> dict[str, float]:
    totals: dict[str, int] = {}
    correct: dict[str, int] = {}
    for label, pred in zip(labels.tolist(), predicted.tolist(), strict=True):
        key = key_fn(str(label))
        totals[key] = totals.get(key, 0) + 1
        if str(label) == str(pred):
            correct[key] = correct.get(key, 0) + 1
    return {key: correct.get(key, 0) / total for key, total in totals.items()}


def binary_accuracy(labels: np.ndarray, predicted: np.ndarray) -> float:
    if len(labels) == 0:
        return 0.0
    return float(np.mean(labels == predicted))


def macro_f1(labels: np.ndarray, predicted: np.ndarray) -> float:
    classes = sorted(set(labels.tolist()) | set(predicted.tolist()))
    if not classes:
        return 0.0
    scores = []
    for cls in classes:
        tp = int(np.sum((labels == cls) & (predicted == cls)))
        fp = int(np.sum((labels != cls) & (predicted == cls)))
        fn = int(np.sum((labels == cls) & (predicted != cls)))
        if tp == 0 and (fp > 0 or fn > 0):
            scores.append(0.0)
            continue
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        scores.append(2.0 * precision * recall / (precision + recall) if (precision + recall) else 0.0)
    return float(np.mean(scores))


def lacunarity_from_scores(scores: list[float] | tuple[float, ...]) -> float:
    if not scores:
        return 0.0
    values = np.asarray(scores, dtype=float)
    mean = float(np.mean(values))
    if mean <= 0.0:
        return 0.0
    variance = float(np.mean((values - mean) ** 2))
    return variance / (mean * mean)


def lacunarity_class(score: float) -> str:
    if score < 0.5:
        return "Uniform"
    if score < 1.5:
        return "Moderate"
    if score < 3.0:
        return "Concentrated"
    return "Extreme"


def classify_numeric_trace(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"class": "Neutral", "reason": "empty trajectory", "metrics": {}}
    arr = np.asarray(values, dtype=float)
    amplitude = float(np.max(arr) - np.min(arr))
    diffs = np.diff(arr)
    sign_changes = count_sign_changes(diffs)
    first_third = float(np.mean(arr[: max(1, len(arr) // 3)]))
    last_third = float(np.mean(arr[-max(1, len(arr) // 3) :]))
    last_window = arr[-min(4, len(arr)) :]
    last_window_std = float(np.std(last_window))
    max_value = float(np.max(arr))
    final_value = float(arr[-1])
    metrics = {
        "amplitude": round(amplitude, 6),
        "first_third_mean": round(first_third, 6),
        "last_third_mean": round(last_third, 6),
        "last_window_std": round(last_window_std, 6),
        "final_value": round(final_value, 6),
        "max_value": round(max_value, 6),
        "sign_changes": sign_changes,
    }
    if amplitude < 0.03:
        return {"class": "Neutral", "reason": "trajectory is nearly flat", "metrics": metrics}
    if last_window_std <= 0.035 and final_value >= max_value - 0.05:
        return {
            "class": "Stabilizing",
            "reason": "trajectory rises into a high late-layer plateau",
            "metrics": metrics,
        }
    if last_third - first_third >= 0.10:
        return {
            "class": "Amplifying",
            "reason": "late layers are materially stronger than early layers without a stable plateau",
            "metrics": metrics,
        }
    if sign_changes >= max(3, int(0.45 * max(1, len(diffs)))) and amplitude >= 0.10:
        return {
            "class": "Oscillatory",
            "reason": "large trajectory amplitude with frequent direction changes and no late plateau",
            "metrics": metrics,
        }
    return {"class": "Neutral", "reason": "trajectory is structured but does not meet pass-class rules", "metrics": metrics}


def count_sign_changes(diffs: np.ndarray) -> int:
    signs = []
    for value in diffs.tolist():
        if abs(value) < 1e-6:
            continue
        signs.append(1 if value > 0 else -1)
    return sum(1 for left, right in zip(signs, signs[1:], strict=False) if left != right)


def canonical_foundation(label: Any) -> str:
    text = str(label)
    if "|" in text:
        drive, register = text.split("|", 1)
        return f"{drive}|{register}"
    if len(text) >= 3 and text[0] == "F":
        return f"{text[:2]}|{text[2:]}"
    raise RuntimeError(f"Bad Foundation label: {label!r}")


def foundation_drive(label: str) -> str:
    return canonical_foundation(label).split("|", 1)[0]


def foundation_register(label: str) -> str:
    return canonical_foundation(label).split("|", 1)[1]


def round_dict(values: dict[str, float]) -> dict[str, float]:
    return {key: round(float(value), 6) for key, value in sorted(values.items())}


def load_bridge_summary(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "status": payload.get("status"),
        "readout_mode": payload.get("readout_mode"),
        "readout_layer": payload.get("readout_layer"),
        "probe_prediction": payload.get("probe_prediction"),
        "bridge_gates": payload.get("bridge_gates"),
        "n_cases": payload.get("n_cases"),
    }


def load_ablation_summary(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    foundation = payload.get("axes", {}).get("foundation", {})
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "status": foundation.get("status"),
        "clean": foundation.get("clean"),
        "label_specific_cover_ablation": foundation.get("label_specific_cover_ablation"),
        "wrong_cover_control": foundation.get("wrong_cover_control"),
        "result_summary": foundation.get("result_summary"),
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def render_markdown(report: dict[str, Any]) -> str:
    gate = report["lacunarity_gate"]
    fractal = report["fractal_preflight"]
    layer = report["layer_scan"]
    bridge = report.get("bridge_summary") or {}
    ablation = report.get("ablation_summary") or {}
    lines = [
        "# GPT-NeoX-20B Stage 7 Foundation Trace Diagnostics",
        "",
        f"- Status: `{report['status']}`",
        f"- Readout: `{report['probe_readout']['kind']}`",
        f"- Best layer: `{layer['best_layer']}`",
        f"- Gate layer selection: `{layer['gate_layer_selection']}`",
        f"- Best heldout Foundation accuracy: `{layer['best_test_acc']:.6f}`",
        f"- Lacunarity: `{gate['score']:.6f}` ({gate['classification']}; pass <= {gate['threshold']})",
        f"- Fractal preflight: `{fractal['class']}` via `{fractal['classifier_kind']}`",
        f"- Fractal reason: {fractal['reason']}",
        "",
        "## Interpretation",
        "",
        "This report checks whether the 28-Foundation readout is clean enough to keep using as the",
        "load-bearing axis for 20B experiments. Lacunarity is computed as Var/Mean^2 over",
        "per-class heldout accuracy at the best balanced-logistic layer.",
        "",
        "The fractal class is a numeric trace proxy over layer-by-layer readout accuracy. It is",
        "not yet the discrete cas-engine CognitiveFractal orbit classifier.",
        "",
        "## Bridge Context",
        "",
        f"- Bridge status: `{bridge.get('status')}`",
        f"- Bridge readout mode: `{bridge.get('readout_mode')}`",
        f"- Bridge cases: `{bridge.get('n_cases')}`",
        "",
        "## Ablation Context",
        "",
        f"- Ablation status: `{ablation.get('status')}`",
        f"- Clean accuracy: `{((ablation.get('clean') or {}).get('acc'))}`",
        f"- Label-specific drop: `{((ablation.get('label_specific_cover_ablation') or {}).get('drop_from_clean'))}`",
        f"- Wrong-cover drop: `{((ablation.get('wrong_cover_control') or {}).get('drop_from_clean'))}`",
        "",
        "## Honest Limits",
        "",
        "- This is not a final ACCEPT/SUPPRESS verdict.",
        "- This is not a full Evidence Packet.",
        "- This does not replace the discrete cas-engine fractal orbit classifier.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
