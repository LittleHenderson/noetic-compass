"""Evaluate hidden-state trajectory breaks across W0/W1 or W0/W1/W8.

This is a research gate for the "break in reasoning" idea: the model's hidden
state should move differently between early timing points when a prompt-injection
risk is adopted or when a factual answer becomes unsupported. The target is the
internal trajectory, not output text. A PASS is still detection-only; it does not
prove prevention, removal, reversal, or causality.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_behavior_v5_prespeech import (  # noqa: E402
    PASS_BA,
    PASS_BASELINE_MARGIN,
    PASS_PAYLOAD_BA,
    PASS_PERMUTATION_P,
    PASS_SHUFFLED_MEAN_MAX,
    balanced_accuracy,
    cross_val_category_majority_predict,
    cross_val_linear_probe_predict,
    derive_group_id,
    hash_char_ngram_features,
    hash_text_features,
    make_group_folds,
    restricted_payload_permutation_p,
    shuffled_label_control_mean,
)


SCHEMA_VERSION = "cas_harness_timing_trajectory_break_eval.v0"
DEFAULT_LABEL_AXIS = "support_status"
DEFAULT_POSITIVE_LABEL = "UNSUPPORTED"
DEFAULT_NEGATIVE_LABEL = "SUPPORTED"
IDENTITY_FIELDS = (
    "model_output_sha256s",
    "judged_answer_sha256s",
    "answer_boundary_target_sha256s",
    "continuation_sha256s",
    "continuation_token_sha256s",
    "forced_continuation_sha256s",
)


class TrajectoryAlignmentError(RuntimeError):
    """Raised when timing captures cannot be proven to be the same rows."""


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--w0-dataset", required=True, type=Path)
    parser.add_argument("--w1-dataset", required=True, type=Path)
    parser.add_argument("--w8-dataset", type=Path, default=None)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--layer", type=int, default=None)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-dim", type=int, default=4096)
    parser.add_argument("--label-axis", default=DEFAULT_LABEL_AXIS)
    parser.add_argument("--positive-label", default=DEFAULT_POSITIVE_LABEL)
    parser.add_argument("--negative-label", default=DEFAULT_NEGATIVE_LABEL)
    parser.add_argument("--strata-axis", default="topic")
    parser.add_argument("--min-strata-classes", type=int, default=5)
    parser.add_argument("--min-label-per-stratum", type=int, default=40)
    parser.add_argument("--min-mixed-prompt-groups", type=int, default=20)
    parser.add_argument("--permutations", type=int, default=1000)
    parser.add_argument("--shuffle-controls", type=int, default=50)
    parser.add_argument("--control-jobs", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=0)
    parser.add_argument(
        "--allow-row-intersection",
        action="store_true",
        help=(
            "Evaluate only trajectory IDs present at all timing points when a later timing "
            "capture is missing a small number of rows. The retained fraction is reported "
            "and must clear --min-row-retention."
        ),
    )
    parser.add_argument("--min-row-retention", type=float, default=0.95)
    parser.add_argument("--probe-C", type=float, default=0.25)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate_timing_trajectory_break(
        w0_dataset_path=args.w0_dataset,
        w1_dataset_path=args.w1_dataset,
        w8_dataset_path=args.w8_dataset,
        layer=args.layer,
        folds=args.folds,
        seed=args.seed,
        text_dim=args.text_dim,
        label_axis=args.label_axis,
        positive_label=args.positive_label,
        negative_label=args.negative_label,
        strata_axis=args.strata_axis,
        min_strata_classes=args.min_strata_classes,
        min_label_per_stratum=args.min_label_per_stratum,
        min_mixed_prompt_groups=args.min_mixed_prompt_groups,
        permutations=args.permutations,
        shuffle_controls=args.shuffle_controls,
        control_jobs=args.control_jobs,
        progress_every=args.progress_every,
        allow_row_intersection=args.allow_row_intersection,
        min_row_retention=args.min_row_retention,
        probe_C=args.probe_C,
        probe_max_iter=args.probe_max_iter,
    )
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "claim": report["claim"],
                "trajectory_balanced_accuracy": report["metrics"].get(
                    "trajectory_hidden_balanced_accuracy"
                ),
                "trajectory_minus_w0_balanced_accuracy": report["metrics"].get(
                    "trajectory_minus_w0_hidden_balanced_accuracy"
                ),
                "permutation_p": report["metrics"].get("within_stratum_permutation_p"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"[trajectory-break] wrote {args.output_report}")
    return 0


def evaluate_timing_trajectory_break(
    *,
    w0_dataset_path: Path,
    w1_dataset_path: Path,
    w8_dataset_path: Path | None,
    layer: int | None,
    folds: int,
    seed: int,
    text_dim: int,
    label_axis: str = DEFAULT_LABEL_AXIS,
    positive_label: str = DEFAULT_POSITIVE_LABEL,
    negative_label: str = DEFAULT_NEGATIVE_LABEL,
    strata_axis: str = "topic",
    min_strata_classes: int = 5,
    min_label_per_stratum: int = 40,
    min_mixed_prompt_groups: int = 20,
    permutations: int = 1000,
    shuffle_controls: int = 50,
    control_jobs: int = 1,
    progress_every: int = 0,
    allow_row_intersection: bool = False,
    min_row_retention: float = 0.95,
    probe_C: float = 0.25,
    probe_max_iter: int = 1000,
) -> dict[str, Any]:
    positive = normalise_label(positive_label)
    negative = normalise_label(negative_label)
    try:
        datasets = {
            "W0": load_timing_dataset(
                w0_dataset_path,
                layer=layer,
                label_axis=label_axis,
                positive_label=positive,
                negative_label=negative,
                strata_axis=strata_axis,
            ),
            "W1": load_timing_dataset(
                w1_dataset_path,
                layer=layer,
                label_axis=label_axis,
                positive_label=positive,
                negative_label=negative,
                strata_axis=strata_axis,
            ),
        }
        if w8_dataset_path is not None:
            datasets["W8"] = load_timing_dataset(
                w8_dataset_path,
                layer=layer,
                label_axis=label_axis,
                positive_label=positive,
                negative_label=negative,
                strata_axis=strata_axis,
            )
        aligned = align_timing_datasets(
            datasets,
            allow_row_intersection=allow_row_intersection,
            min_row_retention=min_row_retention,
        )
    except TrajectoryAlignmentError as exc:
        return blocked_report(
            w0_dataset_path=w0_dataset_path,
            w1_dataset_path=w1_dataset_path,
            w8_dataset_path=w8_dataset_path,
            layer=layer,
            label_axis=label_axis,
            positive_label=positive,
            negative_label=negative,
            strata_axis=strata_axis,
            reason=str(exc),
        )

    prepared = filter_balanced_strata(
        aligned,
        min_strata_classes=min_strata_classes,
        min_label_per_stratum=min_label_per_stratum,
        positive_label=positive,
        negative_label=negative,
    )
    if prepared["status"] != "ready":
        return blocked_report(
            w0_dataset_path=w0_dataset_path,
            w1_dataset_path=w1_dataset_path,
            w8_dataset_path=w8_dataset_path,
            layer=aligned["layer"],
            label_axis=label_axis,
            positive_label=positive,
            negative_label=negative,
            strata_axis=strata_axis,
            reason="Dataset lacks enough balanced labels inside the requested strata.",
            aligned=aligned,
            prepared=prepared,
            min_strata_classes=min_strata_classes,
            min_label_per_stratum=min_label_per_stratum,
            min_mixed_prompt_groups=min_mixed_prompt_groups,
        )

    y = prepared["labels"]
    groups = prepared["groups"]
    prompts = prepared["prompts"]
    strata = prepared["strata"]
    fold_indices = make_group_folds(groups, n_folds=folds, seed=seed)
    timing_order = list(prepared["timing_order"])
    last_timing = str(timing_order[-1])
    trajectory_label = " -> ".join(timing_order)
    prompt_contract = summarize_prompt_group_contract(
        groups=groups,
        prompts=prompts,
        labels=y,
        positive_label=positive,
        negative_label=negative,
    )
    cross_validation = summarize_grouped_folds(groups, fold_indices)

    w0 = prepared["W0"]["features"]
    trajectory_states = [prepared[timing]["features"] for timing in timing_order]
    trajectory_x = build_trajectory_features(*trajectory_states)

    trajectory_pred = cross_val_linear_probe_predict(
        trajectory_x,
        y,
        fold_indices,
        C=probe_C,
        max_iter=probe_max_iter,
    )
    trajectory_ba = balanced_accuracy(y, trajectory_pred)

    w0_pred = cross_val_linear_probe_predict(
        w0,
        y,
        fold_indices,
        C=probe_C,
        max_iter=probe_max_iter,
    )
    w0_ba = balanced_accuracy(y, w0_pred)

    shuffled_time_x = build_shuffled_time_features(*trajectory_states, seed=seed)
    shuffled_time_pred = cross_val_linear_probe_predict(
        shuffled_time_x,
        y,
        fold_indices,
        C=probe_C,
        max_iter=probe_max_iter,
    )
    shuffled_time_ba = balanced_accuracy(y, shuffled_time_pred)

    l0_ba: float | None = None
    l0_x = layer_zero_trajectory_features(prepared)
    if l0_x is not None and int(prepared["layer"]) != 0:
        l0_pred = cross_val_linear_probe_predict(
            l0_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        )
        l0_ba = balanced_accuracy(y, l0_pred)

    prompt_word_x = hash_text_features(prompts, dim=text_dim)
    prompt_char_x = hash_char_ngram_features(prompts, dim=text_dim)
    prefix_texts = prepared[last_timing]["generated_prefix_texts"]
    prefix_word_x = hash_text_features(prefix_texts, dim=text_dim)
    prefix_char_x = hash_char_ngram_features(prefix_texts, dim=text_dim)

    text_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            prompt_word_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    char_text_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            prompt_char_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    prefix_text_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            prefix_word_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    prefix_char_text_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            prefix_char_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )

    prompt_length_x = np.asarray([[len(text)] for text in prompts.tolist()], dtype=np.float32)
    prefix_length_x = np.asarray([[len(text)] for text in prefix_texts.tolist()], dtype=np.float32)
    prompt_length_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            prompt_length_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    prefix_length_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            prefix_length_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )

    category_scores = {
        name: balanced_accuracy(
            y,
            cross_val_category_majority_predict(prepared[name], y, fold_indices),
        )
        for name in (
            "strata",
            "payload_class",
            "domain",
            "evidence_source",
            "retrieval_condition",
            "retrieval_score_bucket",
            "challenge_mode",
        )
    }
    per_stratum_ba = {
        stratum: balanced_accuracy(y[strata == stratum], trajectory_pred[strata == stratum])
        for stratum in sorted(set(strata.tolist()))
    }
    permutation_p = restricted_payload_permutation_p(
        x=trajectory_x,
        y=y,
        payloads=strata,
        fold_indices=fold_indices,
        observed_ba=trajectory_ba,
        seed=seed,
        permutations=permutations,
        probe_C=probe_C,
        probe_max_iter=probe_max_iter,
        jobs=control_jobs,
        progress_label="within-stratum permutation",
        progress_every=progress_every,
    )
    shuffled_label_mean = shuffled_label_control_mean(
        x=trajectory_x,
        y=y,
        fold_indices=fold_indices,
        seed=seed,
        rounds=shuffle_controls,
        probe_C=probe_C,
        probe_max_iter=probe_max_iter,
        jobs=control_jobs,
        progress_label="shuffled-label control",
        progress_every=progress_every,
    )

    gates = {
        "row_alignment_pass": bool(prepared["alignment"].get("row_alignment_pass", False)),
        "forced_continuation_identity_pass": bool(
            prepared["alignment"].get("forced_continuation_identity_pass", False)
        ),
        "row_intersection_retention_pass": bool(
            prepared["alignment"].get("row_intersection_retention_pass", False)
        ),
        "grouped_prompt_fold_pass": cross_validation["train_test_group_overlap_count"] == 0,
        "exact_prompt_group_pass": prompt_contract["non_exact_prompt_group_count"] == 0,
        "same_prompt_mixed_group_floor_pass": (
            prompt_contract["mixed_prompt_group_count"] >= min_mixed_prompt_groups
        ),
        "strata_floor_pass": prepared["testable_strata_count"] >= min_strata_classes,
        "label_per_stratum_floor_pass": prepared["label_per_stratum_floor_pass"],
        "trajectory_balanced_accuracy_pass": trajectory_ba >= PASS_BA,
        "w0_static_control_margin_pass": trajectory_ba - w0_ba >= PASS_BASELINE_MARGIN,
        "shuffled_time_control_margin_pass": (
            trajectory_ba - shuffled_time_ba >= PASS_BASELINE_MARGIN
        ),
        "l0_baseline_present_pass": l0_ba is not None,
        "l0_trajectory_margin_pass": (
            l0_ba is not None and trajectory_ba - l0_ba >= PASS_BASELINE_MARGIN
        ),
        "prompt_text_margin_pass": trajectory_ba - text_ba >= PASS_BASELINE_MARGIN,
        "prompt_char_text_margin_pass": trajectory_ba - char_text_ba >= PASS_BASELINE_MARGIN,
        "generated_prefix_text_margin_pass": (
            trajectory_ba - prefix_text_ba >= PASS_BASELINE_MARGIN
        ),
        "generated_prefix_char_text_margin_pass": (
            trajectory_ba - prefix_char_text_ba >= PASS_BASELINE_MARGIN
        ),
        "strata_margin_pass": trajectory_ba - category_scores["strata"] >= PASS_BASELINE_MARGIN,
        "payload_class_margin_pass": (
            trajectory_ba - category_scores["payload_class"] >= PASS_BASELINE_MARGIN
        ),
        "domain_margin_pass": trajectory_ba - category_scores["domain"] >= PASS_BASELINE_MARGIN,
        "evidence_source_margin_pass": (
            trajectory_ba - category_scores["evidence_source"] >= PASS_BASELINE_MARGIN
        ),
        "retrieval_condition_margin_pass": (
            trajectory_ba - category_scores["retrieval_condition"] >= PASS_BASELINE_MARGIN
        ),
        "retrieval_score_bucket_margin_pass": (
            trajectory_ba - category_scores["retrieval_score_bucket"] >= PASS_BASELINE_MARGIN
        ),
        "challenge_mode_margin_pass": (
            trajectory_ba - category_scores["challenge_mode"] >= PASS_BASELINE_MARGIN
        ),
        "prompt_length_margin_pass": trajectory_ba - prompt_length_ba >= PASS_BASELINE_MARGIN,
        "prefix_length_margin_pass": trajectory_ba - prefix_length_ba >= PASS_BASELINE_MARGIN,
        "per_stratum_floor_pass": all(score >= PASS_PAYLOAD_BA for score in per_stratum_ba.values()),
        "shuffled_label_control_pass": shuffled_label_mean <= PASS_SHUFFLED_MEAN_MAX,
        "within_stratum_permutation_pass": permutation_p < PASS_PERMUTATION_P,
    }
    overall = all(gates.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "datasets": {
            "W0": str(w0_dataset_path),
            "W1": str(w1_dataset_path),
            **({"W8": str(w8_dataset_path)} if w8_dataset_path is not None else {}),
        },
        "status": "PASS" if overall else "FAIL",
        "claim": (
            "LICENSED only for this model/layer/protocol timing-trajectory hidden-state detection screen."
            if overall
            else "OPEN / NOT LICENSED for timing-trajectory hidden-state detection."
        ),
        "claim_ceiling": (
            f"This is detection only. It tests whether {trajectory_label} hidden-state movement "
            "carries a label signal beyond text, metadata, W0-static, layer-0, and shuffled-time controls. "
            "It does not license live interception, prompt-injection prevention/removal/reversal, "
            "hallucination prevention, or causal proof."
        ),
        "target": {
            "label_axis": label_axis,
            "labels": [negative, positive],
            "positive_label": positive,
            "negative_label": negative,
            "trajectory": f"{trajectory_label} hidden-state movement before the final answer is shown",
        },
        "readout_method": {
            "trajectory_features": trajectory_feature_description(timing_order),
            "hidden_readout": "StandardScaler + LogisticRegression",
            "class_weight": "balanced",
            "solver": "lbfgs",
            "C": float(probe_C),
            "max_iter": int(probe_max_iter),
            "grouped_folds": "prompt_group_id / exact prompt carrier",
            "control_jobs": int(control_jobs),
            "progress_every": int(progress_every),
            "allow_row_intersection": bool(allow_row_intersection),
            "min_row_retention": float(min_row_retention),
        },
        "layer": int(prepared["layer"]),
        "row_count": int(len(y)),
        "trajectory_timing_points": timing_order,
        "generated_prefix_control_timing_point": last_timing,
        "fold_count": int(len(fold_indices)),
        "prompt_group_count": int(prompt_contract["prompt_group_count"]),
        "mixed_prompt_group_count": int(prompt_contract["mixed_prompt_group_count"]),
        "prompt_group_contract": prompt_contract,
        "cross_validation": cross_validation,
        "alignment": prepared["alignment"],
        "strata_axis": strata_axis,
        "strata_distribution": prepared["strata_distribution"],
        "label_distribution": dict(sorted(Counter(y.tolist()).items())),
        "metrics": {
            "trajectory_hidden_balanced_accuracy": round(trajectory_ba, 6),
            "w0_static_hidden_balanced_accuracy": round(w0_ba, 6),
            "shuffled_time_hidden_balanced_accuracy": round(shuffled_time_ba, 6),
            "l0_trajectory_balanced_accuracy": round(l0_ba, 6) if l0_ba is not None else None,
            "prompt_text_hash_balanced_accuracy": round(text_ba, 6),
            "prompt_char_text_hash_balanced_accuracy": round(char_text_ba, 6),
            "generated_prefix_text_hash_balanced_accuracy": round(prefix_text_ba, 6),
            "generated_prefix_char_text_hash_balanced_accuracy": round(prefix_char_text_ba, 6),
            "prompt_length_balanced_accuracy": round(prompt_length_ba, 6),
            "prefix_length_balanced_accuracy": round(prefix_length_ba, 6),
            "strata_majority_balanced_accuracy": round(category_scores["strata"], 6),
            "payload_class_majority_balanced_accuracy": round(category_scores["payload_class"], 6),
            "domain_majority_balanced_accuracy": round(category_scores["domain"], 6),
            "evidence_source_majority_balanced_accuracy": round(category_scores["evidence_source"], 6),
            "retrieval_condition_majority_balanced_accuracy": round(
                category_scores["retrieval_condition"],
                6,
            ),
            "retrieval_score_bucket_majority_balanced_accuracy": round(
                category_scores["retrieval_score_bucket"],
                6,
            ),
            "challenge_mode_majority_balanced_accuracy": round(
                category_scores["challenge_mode"],
                6,
            ),
            "trajectory_minus_w0_hidden_balanced_accuracy": round(trajectory_ba - w0_ba, 6),
            "trajectory_minus_shuffled_time_balanced_accuracy": round(
                trajectory_ba - shuffled_time_ba,
                6,
            ),
            "trajectory_minus_l0_balanced_accuracy": (
                round(trajectory_ba - l0_ba, 6) if l0_ba is not None else None
            ),
            "trajectory_minus_prompt_text_balanced_accuracy": round(trajectory_ba - text_ba, 6),
            "trajectory_minus_prompt_char_text_balanced_accuracy": round(
                trajectory_ba - char_text_ba,
                6,
            ),
            "trajectory_minus_generated_prefix_text_balanced_accuracy": round(
                trajectory_ba - prefix_text_ba,
                6,
            ),
            "trajectory_minus_generated_prefix_char_text_balanced_accuracy": round(
                trajectory_ba - prefix_char_text_ba,
                6,
            ),
            "trajectory_minus_strata_balanced_accuracy": round(
                trajectory_ba - category_scores["strata"],
                6,
            ),
            "within_stratum_permutation_p": round(permutation_p, 6),
            "shuffled_label_trajectory_mean_balanced_accuracy": round(shuffled_label_mean, 6),
            "per_stratum_trajectory_balanced_accuracy": {
                key: round(value, 6) for key, value in per_stratum_ba.items()
            },
        },
        "gates": gates,
        "important_limits": [
            f"{trajectory_label} rows must align by trajectory ID before evaluation.",
            "Forced-continuation/output identity hashes must match across timing captures when present.",
            "Grouped folds keep exact prompt carriers out of both train and test.",
            "Same-prompt mixed groups are required; otherwise the evaluator can only learn prompt content.",
            "Prompt text, generated-prefix text, metadata, length, W0-static, layer-0, shuffled-time, shuffled-label, and within-stratum permutation controls must lose by margin.",
            "This script does not run an intervention and therefore does not prove causality.",
        ],
    }


def load_timing_dataset(
    path: Path,
    *,
    layer: int | None,
    label_axis: str,
    positive_label: str,
    negative_label: str,
    strata_axis: str,
) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as data:
        features = data["features"].astype(np.float32)
        if features.ndim == 2:
            features = features[:, None, :]
        layers = (
            np.asarray(data["layers"], dtype=int)
            if "layers" in data.files
            else np.arange(features.shape[1], dtype=int)
        )
        if layer is None:
            layer_position = 0
            resolved_layer = int(layers[0]) if len(layers) else 0
        else:
            matches = np.where(layers == layer)[0]
            if len(matches) == 0:
                raise RuntimeError(f"Layer {layer} is not present in dataset layers {layers.tolist()}")
            layer_position = int(matches[0])
            resolved_layer = int(layer)
        labels = load_label_array(
            data,
            axis=label_axis,
            positive_label=positive_label,
            negative_label=negative_label,
        )
        count = len(labels)
        prompts = load_string_array(data, "prompts", default="", count=count)
        scenario_ids = load_string_array(data, "scenario_ids", default="", count=count)
        trace_ids = load_string_array(data, "trace_ids", default="", count=count)
        prompt_group_ids = (
            load_string_array(data, "prompt_group_ids", default="", count=count)
            if "prompt_group_ids" in data.files
            else np.asarray(
                [
                    derive_group_id(sid, prompt)
                    for sid, prompt in zip(scenario_ids.tolist(), prompts.tolist(), strict=True)
                ],
                dtype=object,
            ).astype(str)
        )
        trajectory_ids = load_trajectory_ids(data, scenario_ids=scenario_ids, trace_ids=trace_ids)
        identity = {
            name: load_string_array(data, name, default="", count=count)
            for name in IDENTITY_FIELDS
            if name in data.files
        }
        return {
            "path": str(path),
            "features": features[:, layer_position, :],
            "features_by_layer": features,
            "layers": layers,
            "layer": resolved_layer,
            "labels": labels,
            "prompts": prompts,
            "scenario_ids": scenario_ids,
            "trace_ids": trace_ids,
            "trajectory_ids": trajectory_ids,
            "groups": prompt_group_ids,
            "strata": load_axis_array(data, strata_axis, default="unknown", count=count),
            "payload_class": load_axis_array(data, "payload_class", default="unknown", count=count),
            "domain": load_axis_array(data, "domain", default="unknown", count=count),
            "evidence_source": load_axis_array(data, "evidence_source", default="unknown", count=count),
            "retrieval_condition": load_axis_array(
                data,
                "retrieval_condition",
                default="unknown",
                count=count,
            ),
            "retrieval_score_bucket": load_axis_array(
                data,
                "retrieval_score_bucket",
                default="unknown",
                count=count,
            ),
            "challenge_mode": load_axis_array(data, "challenge_mode", default="unknown", count=count),
            "generated_prefix_texts": load_string_array(
                data,
                "generated_prefix_texts",
                default="",
                count=count,
            ),
            "timing_points": load_string_array(data, "timing_points", default="", count=count),
            "identity": identity,
        }


def align_timing_datasets(
    datasets: dict[str, dict[str, Any]],
    *,
    allow_row_intersection: bool,
    min_row_retention: float,
) -> dict[str, Any]:
    timing_order = [timing for timing in ("W0", "W1", "W8") if timing in datasets]
    w0_ids = datasets["W0"]["trajectory_ids"].tolist()
    if len(set(w0_ids)) != len(w0_ids):
        duplicates = sorted([key for key, count in Counter(w0_ids).items() if count > 1])
        raise TrajectoryAlignmentError(f"W0 has duplicate trajectory IDs: {duplicates[:5]}")
    order: dict[str, dict[str, int]] = {}
    id_sets: dict[str, set[str]] = {}
    for timing, dataset in datasets.items():
        ids = dataset["trajectory_ids"].tolist()
        if len(set(ids)) != len(ids):
            duplicates = sorted([key for key, count in Counter(ids).items() if count > 1])
            raise TrajectoryAlignmentError(f"{timing} has duplicate trajectory IDs: {duplicates[:5]}")
        id_sets[timing] = set(ids)
        if set(ids) != set(w0_ids) and not allow_row_intersection:
            missing = sorted(set(w0_ids) - set(ids))[:5]
            extra = sorted(set(ids) - set(w0_ids))[:5]
            raise TrajectoryAlignmentError(
                f"{timing} trajectory IDs do not match W0; missing={missing}, extra={extra}"
            )
        order[timing] = {str(value): index for index, value in enumerate(ids)}

    common_ids = set(w0_ids)
    for values in id_sets.values():
        common_ids &= values
    retained_ids = [str(row_id) for row_id in w0_ids if str(row_id) in common_ids]
    if not retained_ids:
        raise TrajectoryAlignmentError(
            f"No trajectory IDs are present at all {'/'.join(timing_order)} timing points."
        )
    retention_fraction = len(retained_ids) / max(1, len(w0_ids))
    if retention_fraction < float(min_row_retention):
        raise TrajectoryAlignmentError(
            "Timing row intersection retained "
            f"{len(retained_ids)}/{len(w0_ids)} rows ({retention_fraction:.6f}), "
            f"below required {float(min_row_retention):.6f}."
        )
    if len(retained_ids) != len(w0_ids) and not allow_row_intersection:
        raise TrajectoryAlignmentError(
            f"Timing datasets do not have identical trajectory IDs; retained {len(retained_ids)}/{len(w0_ids)}."
        )

    w0_label_by_id = {
        str(row_id): str(label)
        for row_id, label in zip(
            datasets["W0"]["trajectory_ids"].tolist(),
            datasets["W0"]["labels"].tolist(),
            strict=True,
        )
    }
    excluded_by_timing: dict[str, list[str]] = {}
    excluded_label_distribution: dict[str, dict[str, int]] = {}
    extra_by_timing: dict[str, list[str]] = {}
    for timing, ids in id_sets.items():
        excluded = sorted(set(w0_ids) - ids)
        excluded_by_timing[timing] = excluded
        excluded_label_distribution[timing] = dict(
            sorted(Counter(w0_label_by_id.get(row_id, "unknown") for row_id in excluded).items())
        )
        extra_by_timing[timing] = sorted(ids - set(w0_ids))

    aligned: dict[str, Any] = {
        "layer": int(datasets["W0"]["layer"]),
        "trajectory_ids": np.asarray(retained_ids, dtype=object).astype(str),
        "alignment": {
            "row_alignment_pass": True,
            "row_intersection_mode": bool(allow_row_intersection),
            "row_intersection_retention_pass": retention_fraction >= float(min_row_retention),
            "original_timing_row_counts": {
                timing: int(len(values)) for timing, values in id_sets.items()
            },
            "retained_trajectory_count": int(len(retained_ids)),
            "retention_fraction": round(float(retention_fraction), 6),
            "excluded_by_timing_counts": {
                timing: int(len(values)) for timing, values in excluded_by_timing.items()
            },
            "excluded_by_timing_examples": {
                timing: values[:10] for timing, values in excluded_by_timing.items()
            },
            "excluded_label_distribution_by_timing": excluded_label_distribution,
            "extra_by_timing_counts": {
                timing: int(len(values)) for timing, values in extra_by_timing.items()
            },
            "extra_by_timing_examples": {
                timing: values[:10] for timing, values in extra_by_timing.items()
            },
            "forced_continuation_identity_pass": True,
            "trajectory_count": int(len(retained_ids)),
            "identity_fields_checked": [],
            "timing_order": timing_order,
            "contract": (
                f"Every W0 row must be the same scenario/trajectory as {' and '.join(timing_order[1:])}, "
                "with matching label, prompt group, prompt, and forced continuation identity when present."
            ),
        },
    }
    for timing, dataset in datasets.items():
        positions = np.asarray([order[timing][str(row_id)] for row_id in retained_ids], dtype=np.int64)
        aligned[timing] = subset_dataset(dataset, positions)

    for timing in timing_order[1:]:
        for field in ("labels", "groups", "prompts", "strata"):
            if not np.array_equal(aligned["W0"][field], aligned[timing][field]):
                raise TrajectoryAlignmentError(f"{timing} {field} does not match W0 after alignment.")
    checked_fields: list[str] = []
    for field in IDENTITY_FIELDS:
        if field not in aligned["W0"]["identity"]:
            continue
        if any(field not in aligned[timing]["identity"] for timing in timing_order[1:]):
            continue
        w0_values = aligned["W0"]["identity"][field]
        if not has_any_value(w0_values):
            continue
        checked_fields.append(field)
        for timing in timing_order[1:]:
            if not np.array_equal(w0_values, aligned[timing]["identity"][field]):
                raise TrajectoryAlignmentError(
                    f"{field} mismatch between W0 and {timing}; forced continuation identity is not proven."
                )
    aligned["alignment"]["identity_fields_checked"] = checked_fields
    if not checked_fields:
        aligned["alignment"]["forced_continuation_identity_pass"] = False
        aligned["alignment"]["identity_warning"] = (
            "No forced-continuation/output identity hash fields were present; row alignment can be tested, "
            "but continuation identity is not licensed."
        )
    for field in (
        "labels",
        "groups",
        "prompts",
        "strata",
        "payload_class",
        "domain",
        "evidence_source",
        "retrieval_condition",
        "retrieval_score_bucket",
        "challenge_mode",
    ):
        aligned[field] = aligned["W0"][field]
    aligned["timing_order"] = timing_order
    return aligned


def subset_dataset(dataset: dict[str, Any], positions: np.ndarray) -> dict[str, Any]:
    out: dict[str, Any] = {}
    count = len(dataset["labels"])
    for key, value in dataset.items():
        if isinstance(value, np.ndarray) and len(value) == count:
            out[key] = value[positions]
        elif key == "identity":
            out[key] = {name: array[positions] for name, array in value.items()}
        else:
            out[key] = value
    return out


def filter_balanced_strata(
    aligned: dict[str, Any],
    *,
    min_strata_classes: int,
    min_label_per_stratum: int,
    positive_label: str,
    negative_label: str,
) -> dict[str, Any]:
    labels = aligned["labels"]
    strata = aligned["strata"]
    keep: list[str] = []
    distribution: dict[str, dict[str, int]] = {}
    label_floor_pass = True
    for stratum in sorted(set(strata.tolist())):
        mask = strata == stratum
        counts = Counter(labels[mask].tolist())
        distribution[stratum] = dict(sorted(counts.items()))
        has_floor = (
            counts.get(positive_label, 0) >= min_label_per_stratum
            and counts.get(negative_label, 0) >= min_label_per_stratum
        )
        label_floor_pass = label_floor_pass and has_floor
        if has_floor:
            keep.append(stratum)
    if len(keep) < min_strata_classes:
        return {
            "status": "blocked_insufficient_balanced_strata",
            "testable_strata_count": len(keep),
            "label_per_stratum_floor_pass": False,
            "strata_distribution": distribution,
        }
    mask = np.isin(strata, np.asarray(keep, dtype=object))
    out: dict[str, Any] = {
        "status": "ready",
        "testable_strata_count": len(keep),
        "label_per_stratum_floor_pass": label_floor_pass,
        "strata_distribution": {key: distribution[key] for key in keep},
        "alignment": dict(aligned["alignment"]),
        "layer": int(aligned["layer"]),
        "timing_order": list(aligned["timing_order"]),
    }
    for key, value in aligned.items():
        if isinstance(value, np.ndarray) and len(value) == len(mask):
            out[key] = value[mask]
        elif key in set(aligned.get("timing_order", [])):
            out[key] = subset_dataset(value, np.where(mask)[0])
        elif key not in out:
            out[key] = value
    return out


def build_trajectory_features(*states: np.ndarray) -> np.ndarray:
    if len(states) < 2:
        raise RuntimeError("Trajectory features require at least two timing states.")
    consecutive_deltas = [states[index + 1] - states[index] for index in range(len(states) - 1)]
    span_delta = states[-1] - states[0]
    deltas = consecutive_deltas if len(states) == 2 else [*consecutive_deltas, span_delta]
    scalar_columns: list[np.ndarray] = []
    for delta in deltas:
        scalar_columns.append(np.linalg.norm(delta, axis=1))
    for left_index in range(len(states)):
        for right_index in range(left_index + 1, len(states)):
            scalar_columns.append(cosine_rows(states[left_index], states[right_index]))
    scalar_features = np.column_stack(scalar_columns).astype(np.float32)
    return np.hstack([*deltas, scalar_features]).astype(np.float32)


def build_shuffled_time_features(*states: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 30_000)
    shuffled_states = [states[0]]
    for state in states[1:]:
        shuffled_states.append(state[rng.permutation(len(state))])
    return build_trajectory_features(*shuffled_states)


def layer_zero_trajectory_features(prepared: dict[str, Any]) -> np.ndarray | None:
    per_timing: list[np.ndarray] = []
    for timing in prepared["timing_order"]:
        dataset = prepared[timing]
        layers = np.asarray(dataset.get("layers", []), dtype=int)
        matches = np.where(layers == 0)[0]
        features_by_layer = dataset.get("features_by_layer")
        if len(matches) == 0 or not isinstance(features_by_layer, np.ndarray) or features_by_layer.ndim != 3:
            return None
        per_timing.append(features_by_layer[:, int(matches[0]), :])
    return build_trajectory_features(*per_timing)


def trajectory_feature_description(timing_order: list[str]) -> str:
    consecutive = [
        f"{timing_order[index + 1]}-{timing_order[index]}"
        for index in range(len(timing_order) - 1)
    ]
    deltas = consecutive if len(timing_order) == 2 else [
        *consecutive,
        f"{timing_order[-1]}-{timing_order[0]}",
    ]
    pairs = [
        f"cos({timing_order[left]},{timing_order[right]})"
        for left in range(len(timing_order))
        for right in range(left + 1, len(timing_order))
    ]
    return f"concat({', '.join(deltas)}, delta norms, {', '.join(pairs)})"


def cosine_rows(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left_norm = np.linalg.norm(left, axis=1)
    right_norm = np.linalg.norm(right, axis=1)
    denom = left_norm * right_norm
    denom[denom < 1e-8] = 1.0
    return ((left * right).sum(axis=1) / denom).astype(np.float32)


def summarize_prompt_group_contract(
    *,
    groups: np.ndarray,
    prompts: np.ndarray,
    labels: np.ndarray,
    positive_label: str,
    negative_label: str,
) -> dict[str, Any]:
    prompts_by_group: dict[str, set[str]] = defaultdict(set)
    labels_by_group: dict[str, set[str]] = defaultdict(set)
    rows_by_group: Counter[str] = Counter()
    for group, prompt, label in zip(groups.tolist(), prompts.tolist(), labels.tolist(), strict=True):
        key = str(group)
        prompts_by_group[key].add(hashlib.sha256(str(prompt).encode("utf-8")).hexdigest())
        labels_by_group[key].add(str(label))
        rows_by_group[key] += 1
    non_exact = sorted(group for group, hashes in prompts_by_group.items() if len(hashes) != 1)
    mixed = sorted(
        group
        for group, group_labels in labels_by_group.items()
        if {positive_label, negative_label}.issubset(group_labels)
    )
    singleton = sorted(group for group, count in rows_by_group.items() if count < 2)
    return {
        "prompt_group_count": len(prompts_by_group),
        "exact_prompt_group_count": len(prompts_by_group) - len(non_exact),
        "non_exact_prompt_group_count": len(non_exact),
        "mixed_prompt_group_count": len(mixed),
        "singleton_prompt_group_count": len(singleton),
        "non_exact_prompt_group_examples": non_exact[:10],
        "mixed_prompt_group_examples": mixed[:10],
        "singleton_prompt_group_examples": singleton[:10],
        "contract": (
            "Every prompt group must hold one exact prompt/evidence setup, and enough groups must contain "
            f"both {negative_label} and {positive_label} outcomes."
        ),
    }


def summarize_grouped_folds(groups: np.ndarray, fold_indices: list[np.ndarray]) -> dict[str, Any]:
    all_indices = np.arange(len(groups))
    overlap_count = 0
    fold_sizes: list[int] = []
    fold_group_counts: list[int] = []
    for test_idx in fold_indices:
        train_idx = np.setdiff1d(all_indices, test_idx, assume_unique=False)
        train_groups = set(groups[train_idx].tolist())
        test_groups = set(groups[test_idx].tolist())
        overlap_count += len(train_groups & test_groups)
        fold_sizes.append(int(len(test_idx)))
        fold_group_counts.append(int(len(test_groups)))
    return {
        "fold_count": int(len(fold_indices)),
        "fold_sizes": fold_sizes,
        "fold_group_counts": fold_group_counts,
        "train_test_group_overlap_count": int(overlap_count),
        "contract": "All rows for one prompt_group_id stay inside exactly one test fold.",
    }


def blocked_report(
    *,
    w0_dataset_path: Path,
    w1_dataset_path: Path,
    w8_dataset_path: Path | None,
    layer: int | None,
    label_axis: str,
    positive_label: str,
    negative_label: str,
    strata_axis: str,
    reason: str,
    aligned: dict[str, Any] | None = None,
    prepared: dict[str, Any] | None = None,
    min_strata_classes: int = 0,
    min_label_per_stratum: int = 0,
    min_mixed_prompt_groups: int = 0,
) -> dict[str, Any]:
    labels = (
        aligned.get("labels", np.asarray([], dtype=object))
        if isinstance(aligned, dict)
        else np.asarray([], dtype=object)
    )
    timing_order = (
        list(aligned.get("timing_order", []))
        if isinstance(aligned, dict) and aligned.get("timing_order")
        else (["W0", "W1", "W8"] if w8_dataset_path is not None else ["W0", "W1"])
    )
    trajectory_label = " -> ".join(timing_order)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "datasets": {
            "W0": str(w0_dataset_path),
            "W1": str(w1_dataset_path),
            **({"W8": str(w8_dataset_path)} if w8_dataset_path is not None else {}),
        },
        "status": "BLOCKED",
        "claim": "OPEN / NOT LICENSED for timing-trajectory hidden-state detection.",
        "claim_ceiling": f"Dataset cannot be evaluated as a {trajectory_label} trajectory-break gate.",
        "blocker": reason,
        "target": {
            "label_axis": label_axis,
            "positive_label": positive_label,
            "negative_label": negative_label,
            "trajectory": f"{trajectory_label} hidden-state movement before the final answer is shown",
        },
        "layer": layer,
        "row_count": int(len(labels)),
        "required_strata_classes": int(min_strata_classes),
        "required_label_per_stratum": int(min_label_per_stratum),
        "required_mixed_prompt_groups": int(min_mixed_prompt_groups),
        "testable_strata_count": int((prepared or {}).get("testable_strata_count", 0)),
        "strata_axis": strata_axis,
        "strata_distribution": (prepared or {}).get("strata_distribution", {}),
        "label_distribution": dict(sorted(Counter(labels.tolist()).items())),
        "alignment": (aligned or {}).get(
            "alignment",
            {
                "row_alignment_pass": False,
                "forced_continuation_identity_pass": False,
            },
        ),
        "metrics": {},
        "gates": {
            "row_alignment_pass": False,
            "forced_continuation_identity_pass": False,
            "strata_floor_pass": False,
            "label_per_stratum_floor_pass": False,
            "same_prompt_mixed_group_floor_pass": False,
        },
    }


def load_label_array(
    data: Any,
    *,
    axis: str,
    positive_label: str,
    negative_label: str,
) -> np.ndarray:
    name = f"labels_{axis}"
    if name not in data.files:
        raise TrajectoryAlignmentError(f"Dataset must contain {name}.")
    raw = np.asarray(data[name], dtype=object).astype(str)
    labels = np.asarray([normalise_label(value) for value in raw.tolist()], dtype=object)
    allowed = {positive_label, negative_label}
    if any(label not in allowed for label in labels.tolist()):
        bad = sorted(set(labels.tolist()) - allowed)
        raise TrajectoryAlignmentError(f"{name} contains labels outside {sorted(allowed)}: {bad[:5]}")
    return labels.astype(str)


def load_axis_array(data: Any, axis: str, *, default: str, count: int) -> np.ndarray:
    primary = f"labels_{axis}"
    fallbacks = {
        "strata": ("labels_topic", "labels_payload_class"),
        "topic": ("labels_topic", "labels_payload_class"),
        "payload": ("labels_payload_class",),
        "payload_class": ("labels_payload_class",),
    }
    names = (primary, *fallbacks.get(axis, ()))
    for name in names:
        if name in data.files:
            return np.asarray(data[name], dtype=object).astype(str)
    return np.asarray([default] * count, dtype=object).astype(str)


def load_string_array(data: Any, name: str, *, default: str, count: int) -> np.ndarray:
    if name in data.files:
        return np.asarray(data[name], dtype=object).astype(str)
    return np.asarray([default] * count, dtype=object).astype(str)


def load_trajectory_ids(data: Any, *, scenario_ids: np.ndarray, trace_ids: np.ndarray) -> np.ndarray:
    if "trajectory_ids" in data.files:
        return np.asarray(data["trajectory_ids"], dtype=object).astype(str)
    if has_any_value(scenario_ids):
        return scenario_ids.astype(str)
    return np.asarray([strip_timing_suffix(value) for value in trace_ids.tolist()], dtype=object).astype(str)


def strip_timing_suffix(value: Any) -> str:
    text = str(value or "")
    lowered = text.lower()
    for suffix in ("::w0_all_layers", "::w1_all_layers", "::w8_all_layers", "::w0", "::w1", "::w8"):
        if lowered.endswith(suffix):
            return text[: -len(suffix)]
    return text


def has_any_value(values: np.ndarray) -> bool:
    return any(str(value).strip() for value in values.tolist())


def normalise_label(value: Any) -> str:
    text = str(value or "").strip().upper()
    aliases = {
        "SUPPORT": "SUPPORTED",
        "GROUNDED": "SUPPORTED",
        "TRUE_SUPPORTED": "SUPPORTED",
        "UNSUPPORT": "UNSUPPORTED",
        "UNSUPPORTED_CLAIM": "UNSUPPORTED",
        "HALLUCINATED": "UNSUPPORTED",
        "HALLUCINATION": "UNSUPPORTED",
        "PROMPT_INJECTION_PRESENT": "PRESENT",
        "INJECTION_PRESENT": "PRESENT",
        "PROMPT_INJECTION_ABSENT": "ABSENT",
        "INJECTION_ABSENT": "ABSENT",
        "CLEAN": "ABSENT",
    }
    return aliases.get(text, text)


if __name__ == "__main__":
    raise SystemExit(main())
