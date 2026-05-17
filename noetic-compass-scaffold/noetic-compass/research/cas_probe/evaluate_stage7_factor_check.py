"""Stage 7.2: factor the 28-Foundation signal into Drive and Register.

Stage 7.0 showed that Pythia-160M focus-token layer-6 hidden states
carry the original-TKS 28-Foundation labels beyond text baselines.
Stage 7.1 showed that the 28-way readout depends causally on its trained
readout subspace.

This script asks whether that signal decomposes into:

* Drive: 7-way `F1..F7`
* Register: 4-way `T/A/f/E`
* Interaction: the full 28-way `F1T..F7E`

For each task it:

1. trains text-only baselines on the same split,
2. trains surface metadata baselines for diagnostics,
3. trains a locked focus-token layer-6 activation probe,
4. removes the trained task subspace from the readout,
5. compares the removal against same-rank random complement removals.

This remains a readout-level experiment. It does not test language
generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_SEED = 9172
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 6
_REGISTERS = ("T", "A", "f", "E")
_REGISTER_TO_INDEX = {name: i for i, name in enumerate(_REGISTERS)}
_FOUNDATION_LABELS = tuple(f"F{drive}{register}" for drive in range(1, 8) for register in _REGISTERS)
_FOUNDATION_TO_INDEX = {label: i for i, label in enumerate(_FOUNDATION_LABELS)}
_TASKS = {
    "drive": tuple(f"F{drive}" for drive in range(1, 8)),
    "register": _REGISTERS,
    "interaction": _FOUNDATION_LABELS,
}
_GATES = {
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


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
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


def _mcnemar_p_safe(a_only: int, b_only: int) -> float:
    n = a_only + b_only
    if n <= 0:
        return 1.0
    lo = min(a_only, b_only)
    log_half = math.log(0.5)
    logs = [
        math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + n * log_half
        for i in range(lo + 1)
    ]
    m = max(logs)
    cdf = math.exp(m) * sum(math.exp(x - m) for x in logs)
    return float(min(1.0, 2.0 * cdf))


def _paired(a_correct: Any, b_correct: Any, a_name: str, b_name: str) -> dict[str, Any]:
    import numpy as np

    both = a_correct & b_correct
    a_only = a_correct & ~b_correct
    b_only = ~a_correct & b_correct
    neither = ~a_correct & ~b_correct
    out = {
        "a_name": a_name,
        "b_name": b_name,
        "both_correct": int(np.sum(both)),
        "a_only_correct": int(np.sum(a_only)),
        "b_only_correct": int(np.sum(b_only)),
        "both_wrong": int(np.sum(neither)),
    }
    out["discordant"] = out["a_only_correct"] + out["b_only_correct"]
    out["exact_binomial_mcnemar_p"] = _mcnemar_p_safe(out["a_only_correct"], out["b_only_correct"])
    return out


def _label_for_row(row: dict[str, Any], task: str) -> int:
    if task == "drive":
        return int(row["foundation_drive"]) - 1
    if task == "register":
        return _REGISTER_TO_INDEX[str(row["foundation_register"])]
    if task == "interaction":
        return _FOUNDATION_TO_INDEX[str(row["foundation_label"])]
    raise ValueError(f"unknown task {task!r}")


def _labels_for_task(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str], task: str) -> Any:
    import numpy as np

    return np.array([_label_for_row(rows_by_id[sid], task) for sid in sample_ids], dtype=np.int64)


def _hard_contrast_key(row: dict[str, Any], task: str) -> str:
    values: list[int] = []
    for label in row["hard_contrast_foundations"]:
        drive = int(label[1])
        register = label[2:]
        if task == "drive":
            values.append(drive - 1)
        elif task == "register":
            values.append(_REGISTER_TO_INDEX[register])
        elif task == "interaction":
            values.append(_FOUNDATION_TO_INDEX[label])
        else:
            raise ValueError(f"unknown task {task!r}")
    return "_".join(str(v) for v in sorted(set(values)))


def _metadata_features(rows: list[dict[str, Any]], sample_ids: list[str], task: str, variant: str) -> list[list[str]]:
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    features: list[list[str]] = []
    for sid in sample_ids:
        row = rows_by_id[sid]
        focus = str(row["focus_span"])
        pair = _hard_contrast_key(row, task)
        pair_kind = str(row["pair_kind"])
        family = str(row["paraphrase_family"])
        surface = str(row["surface_style"])
        if variant == "focus_only":
            features.append([f"focus={focus}"])
        elif variant == "pair_focus":
            features.append([f"pair={pair}", f"focus={focus}"])
        elif variant == "pair_kind_focus":
            features.append([f"pair_kind={pair_kind}", f"focus={focus}"])
        elif variant == "surface_pair_family_focus":
            features.append([f"surface={surface}", f"pair={pair}", f"family={family}", f"focus={focus}"])
        else:
            raise ValueError(f"unknown metadata variant {variant!r}")
    return features


def _metrics(y_true: Any, y_pred: Any, labels: tuple[str, ...]) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

    label_ids = list(range(len(labels)))
    return {
        "acc": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=label_ids).astype(int).tolist(),
        "pred_distribution": {
            labels[int(k)]: int(v)
            for k, v in sorted(Counter(int(x) for x in y_pred.tolist()).items())
        },
    }


def _class_distribution(y: Any, idx: Any, labels: tuple[str, ...]) -> dict[str, int]:
    return {
        labels[int(k)]: int(v)
        for k, v in sorted(Counter(int(x) for x in y[idx].tolist()).items())
    }


def _fit_language_baselines(english: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any, labels: tuple[str, ...]) -> dict[str, Any]:
    import numpy as np
    from sklearn.dummy import DummyClassifier
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    candidates: dict[str, Any] = {
        "majority": DummyClassifier(strategy="most_frequent"),
        "stratified_dummy": DummyClassifier(strategy="stratified", random_state=_SEED),
        "count_vector_word_1_2": make_pipeline(
            CountVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=3000, class_weight="balanced", random_state=_SEED),
        ),
        "tfidf_word_1_2": make_pipeline(
            TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=3000, class_weight="balanced", random_state=_SEED),
        ),
        "tfidf_char_3_5": make_pipeline(
            TfidfVectorizer(lowercase=True, analyzer="char", ngram_range=(3, 5), min_df=1),
            LogisticRegression(solver="lbfgs", max_iter=3000, class_weight="balanced", random_state=_SEED),
        ),
    }
    out: dict[str, Any] = {}
    for name, model in candidates.items():
        if name in {"majority", "stratified_dummy"}:
            X_train = np.zeros((len(idx_train), 1))
            X_val = np.zeros((len(idx_val), 1))
            X_test = np.zeros((len(idx_test), 1))
        else:
            X_train = english[idx_train]
            X_val = english[idx_val]
            X_test = english[idx_test]
        model.fit(X_train, y[idx_train])
        pred_val = model.predict(X_val)
        pred_test = model.predict(X_test)
        out[name] = {
            "val": _metrics(y[idx_val], pred_val, labels),
            "test": _metrics(y[idx_test], pred_test, labels),
            "test_predictions": [int(x) for x in pred_test.tolist()],
        }
    return out


def _fit_metadata_baselines(rows: list[dict[str, Any]], sample_ids: list[str], task: str, y: Any, idx_train: Any, idx_val: Any, idx_test: Any, labels: tuple[str, ...]) -> dict[str, Any]:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import MultiLabelBinarizer

    variants = ("focus_only", "pair_focus", "pair_kind_focus", "surface_pair_family_focus")
    out: dict[str, Any] = {}
    for variant in variants:
        matrix = np.array(_metadata_features(rows, sample_ids, task, variant), dtype=object)
        encoder = MultiLabelBinarizer()
        X_train = encoder.fit_transform(matrix[idx_train].tolist())
        X_val = encoder.transform(matrix[idx_val].tolist())
        X_test = encoder.transform(matrix[idx_test].tolist())
        model = LogisticRegression(
            solver="lbfgs",
            max_iter=3000,
            class_weight="balanced",
            random_state=_SEED,
        )
        model.fit(X_train, y[idx_train])
        pred_val = model.predict(X_val)
        pred_test = model.predict(X_test)
        out[variant] = {
            "val": _metrics(y[idx_val], pred_val, labels),
            "test": _metrics(y[idx_test], pred_test, labels),
            "test_predictions": [int(x) for x in pred_test.tolist()],
        }
    return out


def _fit_readout(X_layer: Any, y: Any, idx_train: Any, idx_val: Any, idx_test: Any, labels: tuple[str, ...]) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_layer[idx_train])
    X_val = scaler.transform(X_layer[idx_val])
    X_test = scaler.transform(X_layer[idx_test])
    clf = LogisticRegression(
        solver="lbfgs",
        max_iter=3000,
        class_weight="balanced",
        random_state=_SEED,
    )
    clf.fit(X_train, y[idx_train])
    pred_train = clf.predict(X_train)
    pred_val = clf.predict(X_val)
    pred_test = clf.predict(X_test)
    return {
        "scaler": scaler,
        "clf": clf,
        "pred_train": pred_train,
        "pred_val": pred_val,
        "pred_test": pred_test,
        "train": _metrics(y[idx_train], pred_train, labels),
        "val": _metrics(y[idx_val], pred_val, labels),
        "test": _metrics(y[idx_test], pred_test, labels),
    }


def _projection_basis_from_probe(scaler: Any, clf: Any) -> dict[str, Any]:
    import numpy as np

    sigma = scaler.scale_
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = clf.coef_ / sigma_safe[None, :]
    _u, s, vh = np.linalg.svd(w_raw, full_matrices=False)
    threshold = float(s.max() * 1e-6)
    basis_rows = vh[s > threshold]
    return {
        "basis_rows": basis_rows,
        "projection": basis_rows.T @ basis_rows,
        "singular_values": [float(x) for x in s.tolist()],
        "rank": int(basis_rows.shape[0]),
        "threshold": threshold,
    }


def _sample_random_complement_bases(task_basis: Any, hidden_dim: int, rank: int, n_random: int, seed: int) -> list[Any]:
    import numpy as np

    rng = np.random.default_rng(seed)
    p_task = task_basis.T @ task_basis
    p_complement = np.eye(hidden_dim) - p_task
    bases: list[Any] = []
    for _ in range(n_random):
        raw = rng.standard_normal((rank, hidden_dim))
        projected = raw @ p_complement
        q, _ = np.linalg.qr(projected.T)
        bases.append(q[:, :rank].T)
    return bases


def _predict_from_raw(X_raw: Any, scaler: Any, clf: Any) -> Any:
    return clf.predict(scaler.transform(X_raw))


def _strip_predictions(block: dict[str, Any]) -> dict[str, Any]:
    return {k: {kk: vv for kk, vv in v.items() if kk != "test_predictions"} for k, v in block.items()}


def _run_task(
    task: str,
    rows: list[dict[str, Any]],
    rows_by_id: dict[str, dict[str, Any]],
    sample_ids: list[str],
    english: Any,
    X_layer: Any,
    idx_train: Any,
    idx_val: Any,
    idx_test: Any,
    n_random: int,
) -> dict[str, Any]:
    import numpy as np

    labels = _TASKS[task]
    chance = 1.0 / len(labels)
    y = _labels_for_task(rows_by_id, sample_ids, task)
    language = _fit_language_baselines(english, y, idx_train, idx_val, idx_test, labels)
    metadata = _fit_metadata_baselines(rows, sample_ids, task, y, idx_train, idx_val, idx_test, labels)
    best_text_name, best_text = max(
        ((name, row) for name, row in language.items() if name not in {"majority", "stratified_dummy"}),
        key=lambda item: (item[1]["val"]["acc"], item[1]["val"]["macro_f1"], item[1]["test"]["acc"], item[0]),
    )
    best_metadata_name, best_metadata = max(
        metadata.items(),
        key=lambda item: (item[1]["val"]["acc"], item[1]["val"]["macro_f1"], item[1]["test"]["acc"], item[0]),
    )
    fitted = _fit_readout(X_layer, y, idx_train, idx_val, idx_test, labels)
    activation_correct = fitted["pred_test"] == y[idx_test]
    best_text_correct = np.array(best_text["test_predictions"], dtype=np.int64) == y[idx_test]
    best_metadata_correct = np.array(best_metadata["test_predictions"], dtype=np.int64) == y[idx_test]
    paired_text = _paired(activation_correct, best_text_correct, "activation_layer6", best_text_name)
    paired_metadata = _paired(activation_correct, best_metadata_correct, "activation_layer6", best_metadata_name)

    basis = _projection_basis_from_probe(fitted["scaler"], fitted["clf"])
    p_task = basis["projection"]
    X_test = X_layer[idx_test]
    y_test = y[idx_test]
    X_test_task_ablated = X_test - X_test @ p_task
    pred_task_ablated = _predict_from_raw(X_test_task_ablated, fitted["scaler"], fitted["clf"])
    ablated_metrics = _metrics(y_test, pred_task_ablated, labels)

    baseline_acc = fitted["test"]["acc"]
    task_disruption = float(baseline_acc - ablated_metrics["acc"])
    task_correct = pred_task_ablated == y_test
    random_bases = _sample_random_complement_bases(
        basis["basis_rows"],
        hidden_dim=int(X_layer.shape[1]),
        rank=int(basis["rank"]),
        n_random=n_random,
        seed=_SEED + len(labels),
    )
    random_results: list[dict[str, Any]] = []
    random_disruptions: list[float] = []
    max_abs_random_x_task = 0.0
    for i, rbasis in enumerate(random_bases):
        max_abs_random_x_task = max(max_abs_random_x_task, float(np.max(np.abs(rbasis @ basis["basis_rows"].T))))
        p_random = rbasis.T @ rbasis
        pred_random = _predict_from_raw(X_test - X_test @ p_random, fitted["scaler"], fitted["clf"])
        metrics = _metrics(y_test, pred_random, labels)
        disruption = float(baseline_acc - metrics["acc"])
        random_disruptions.append(disruption)
        random_results.append(
            {
                "index": i,
                "rank": int(rbasis.shape[0]),
                "test_acc": metrics["acc"],
                "test_macro_f1": metrics["macro_f1"],
                "disruption": disruption,
                "changed_prediction_rate": float(np.mean(pred_random != fitted["pred_test"])),
            }
        )
    random_array = np.array(random_disruptions, dtype=float)
    p_one_sided = float((1 + np.sum(random_array >= task_disruption)) / (len(random_array) + 1))
    text_lift = float(fitted["test"]["acc"] - best_text["test"]["acc"])
    metadata_lift = float(fitted["test"]["acc"] - best_metadata["test"]["acc"])
    text_pass = text_lift >= _GATES["test_acc_lift_over_text_min"] and paired_text["exact_binomial_mcnemar_p"] < _GATES["mcnemar_p_max"]
    ablation_pass = (
        ablated_metrics["acc"] <= chance + _GATES["ablation_acc_slack_over_chance"]
        and p_one_sided < _GATES["random_ge_task_empirical_p_max"]
    )
    if text_pass and ablation_pass:
        status = "FACTOR_READOUT_AND_ABLATION_PASS"
    elif text_pass:
        status = "FACTOR_READOUT_PASS_ABLATION_FAIL"
    elif ablation_pass:
        status = "FACTOR_ABLATION_PASS_TEXT_GATE_FAIL"
    else:
        status = "FACTOR_CHECK_FAIL"

    return {
        "status": status,
        "label_names": list(labels),
        "chance_accuracy": chance,
        "split_distribution": {
            "train": _class_distribution(y, idx_train, labels),
            "val": _class_distribution(y, idx_val, labels),
            "test": _class_distribution(y, idx_test, labels),
        },
        "language_baselines": _strip_predictions(language),
        "metadata_baselines": _strip_predictions(metadata),
        "best_text_baseline_by_val": best_text_name,
        "best_metadata_baseline_by_val": best_metadata_name,
        "activation_layer6": {
            "train": fitted["train"],
            "val": fitted["val"],
            "test": fitted["test"],
            "test_acc_lift_over_best_text": text_lift,
            "test_acc_lift_over_best_metadata": metadata_lift,
            "paired_vs_best_text": paired_text,
            "paired_vs_best_metadata": paired_metadata,
        },
        "subspace": {
            "rank": int(basis["rank"]),
            "singular_values": basis["singular_values"],
            "svd_threshold": basis["threshold"],
            "max_abs_random_x_task_cosine": max_abs_random_x_task,
        },
        "task_subspace_ablation": {
            "test": ablated_metrics,
            "disruption": task_disruption,
            "changed_prediction_rate": float(np.mean(pred_task_ablated != fitted["pred_test"])),
            "paired_vs_unablated": _paired(task_correct, activation_correct, f"{task}_ablated", "unablated"),
        },
        "random_complement_controls": {
            "mean_disruption": float(np.mean(random_array)),
            "std_disruption": float(np.std(random_array, ddof=1)) if len(random_array) > 1 else 0.0,
            "max_disruption": float(np.max(random_array)) if len(random_array) else 0.0,
            "min_disruption": float(np.min(random_array)) if len(random_array) else 0.0,
            f"one_sided_empirical_p_random_ge_{task}": p_one_sided,
            "results": random_results,
        },
        "notes": {
            "metadata_is_diagnostic_not_gate": (
                "For Drive/Register, pair+focus metadata can identify the factor by construction "
                "because the fixture explicitly contrasts factor pairs. The claim-bearing gate is "
                "activation-vs-text plus readout-subspace ablation."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--stage70-report", required=True)
    parser.add_argument("--stage71-report", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--n-random", type=int, default=30)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    stage70_path = _resolve(args.stage70_report)
    stage71_path = _resolve(args.stage71_report)
    out_report = _resolve(args.out_report)

    try:
        import numpy as np
    except ImportError as exc:
        raise SystemExit(f"missing dependency: {exc}") from exc

    with stage70_path.open(encoding="utf-8") as fh:
        stage70 = json.load(fh)
    with stage71_path.open(encoding="utf-8") as fh:
        stage71 = json.load(fh)
    if stage70.get("status") != "FOUNDATION_PROBE_RELIABLY_ABOVE_TEXT_BASELINE":
        raise SystemExit(f"Stage 7.0 is not pass-clean: {stage70.get('status')}")
    if stage71.get("status") != "FOUNDATION_SUBSPACE_CAUSAL_FOR_PROBE_READOUT":
        raise SystemExit(f"Stage 7.1 is not pass-clean: {stage71.get('status')}")

    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"]]
    if len(sample_ids) != len(set(sample_ids)):
        raise SystemExit("activation sample_ids are not unique")
    splits = _split_indices(rows_by_id, sample_ids)
    english = np.array([rows_by_id[sid]["english"] for sid in sample_ids], dtype=object)
    X_layer = data[_READOUT_KEY][:, _LAYER, :]

    task_reports: dict[str, Any] = {}
    for task in ("drive", "register", "interaction"):
        print(f"running factor task: {task}")
        task_reports[task] = _run_task(
            task,
            rows,
            rows_by_id,
            sample_ids,
            english,
            X_layer,
            splits["train"],
            splits["val"],
            splits["test"],
            int(args.n_random),
        )
        print(
            json.dumps(
                {
                    "task": task,
                    "status": task_reports[task]["status"],
                    "activation_test_acc": task_reports[task]["activation_layer6"]["test"]["acc"],
                    "best_text": task_reports[task]["best_text_baseline_by_val"],
                    "text_lift": task_reports[task]["activation_layer6"]["test_acc_lift_over_best_text"],
                    "ablated_acc": task_reports[task]["task_subspace_ablation"]["test"]["acc"],
                    "random_max": task_reports[task]["random_complement_controls"]["max_disruption"],
                },
                indent=2,
            )
        )

    if all(row["status"] == "FACTOR_READOUT_AND_ABLATION_PASS" for row in task_reports.values()):
        status = "STAGE7_FACTORS_READOUT_AND_ABLATION_PASS"
    elif task_reports["drive"]["status"] == "FACTOR_READOUT_AND_ABLATION_PASS" and task_reports["register"]["status"] == "FACTOR_READOUT_AND_ABLATION_PASS":
        status = "STAGE7_MAIN_FACTORS_PASS_INTERACTION_CAVEATED"
    else:
        status = "STAGE7_FACTOR_CHECK_MIXED"

    report = {
        "schema_version": "stage7_factor_check_report.v1",
        "experiment": "Stage 7.2 factor check: Drive, Register, and 28-way interaction at focus-token layer 6",
        "status": status,
        "decision_gates": _GATES,
        "readout": _READOUT_NAME,
        "layer": _LAYER,
        "n_random_controls": int(args.n_random),
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "stage70_report_file": stage70_path.name,
        "stage70_report_sha256": _sha256_of_file(stage70_path),
        "stage71_report_file": stage71_path.name,
        "stage71_report_sha256": _sha256_of_file(stage71_path),
        "n_records": int(len(sample_ids)),
        "split": {
            "train": int(len(splits["train"])),
            "val": int(len(splits["val"])),
            "test": int(len(splits["test"])),
        },
        "tasks": task_reports,
        "reserved_interpretation": (
            "This is a readout-level factorization test for the Stage 7 Foundation signal. "
            "It asks whether Drive, Register, and the full 28-way interaction are each "
            "readable from focus-token layer-6 activations beyond text baselines and whether "
            "their trained readout subspaces are necessary for those readouts. It does not "
            "test generated-language control."
        ),
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "tasks": {k: v["status"] for k, v in task_reports.items()}}, indent=2))
    print(f"report written: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
