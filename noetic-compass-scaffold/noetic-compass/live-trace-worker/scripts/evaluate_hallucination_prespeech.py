"""Evaluate W0/W1/W8 hidden-state hallucination-risk readout.

This evaluator tests whether timing hidden states separate SUPPORTED versus
UNSUPPORTED factual answers before the answer is displayed. W0 is prompt-stage
before any answer token exists. W1/W8 are early-generation pre-display states,
so they must also beat generated-prefix text controls. It is not a prevention
proof. A PASS only makes a scoped detection claim eligible for review;
hallucination prevention still requires an intervention/guardrail proof that
reduces unsupported answers without breaking answer quality.
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
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

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


SCHEMA_VERSION = "cas_harness_hallucination_prespeech_eval.v1"
SUPPORT_LABELS = ("SUPPORTED", "UNSUPPORTED")


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--layer", type=int, default=None)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-dim", type=int, default=4096)
    parser.add_argument("--min-topic-classes", type=int, default=5)
    parser.add_argument("--min-label-per-topic", type=int, default=40)
    parser.add_argument("--min-mixed-prompt-groups", type=int, default=20)
    parser.add_argument("--permutations", type=int, default=1000)
    parser.add_argument("--shuffle-controls", type=int, default=50)
    parser.add_argument("--control-jobs", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=0)
    parser.add_argument("--probe-C", type=float, default=0.25)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    parser.add_argument(
        "--prefix-residual-control",
        action="store_true",
        help=(
            "Also test whether hidden states still predict labels after fold-local "
            "linear residualization against generated-prefix word+char features."
        ),
    )
    parser.add_argument("--prefix-residual-alpha", type=float, default=10.0)
    parser.add_argument(
        "--prefix-residual-dim",
        type=int,
        default=256,
        help="Hash dimension per generated-prefix word/char channel for the residual diagnostic.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate_hallucination_prespeech(
        dataset_path=args.dataset,
        layer=args.layer,
        folds=args.folds,
        seed=args.seed,
        text_dim=args.text_dim,
        min_topic_classes=args.min_topic_classes,
        min_label_per_topic=args.min_label_per_topic,
        min_mixed_prompt_groups=args.min_mixed_prompt_groups,
        permutations=args.permutations,
        shuffle_controls=args.shuffle_controls,
        control_jobs=args.control_jobs,
        progress_every=args.progress_every,
        probe_C=args.probe_C,
        probe_max_iter=args.probe_max_iter,
        prefix_residual_control=args.prefix_residual_control,
        prefix_residual_alpha=args.prefix_residual_alpha,
        prefix_residual_dim=args.prefix_residual_dim,
    )
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "claim": report["claim"],
                "hidden_balanced_accuracy": report["metrics"].get("hidden_balanced_accuracy"),
                "hidden_minus_char_text_balanced_accuracy": report["metrics"].get(
                    "hidden_minus_char_text_balanced_accuracy"
                ),
                "within_topic_permutation_p": report["metrics"].get("within_topic_permutation_p"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"[hallucination-prespeech] wrote {args.output_report}")
    return 0


def evaluate_hallucination_prespeech(
    *,
    dataset_path: Path,
    layer: int | None,
    folds: int,
    seed: int,
    text_dim: int,
    min_topic_classes: int,
    min_label_per_topic: int,
    min_mixed_prompt_groups: int,
    permutations: int,
    shuffle_controls: int,
    control_jobs: int = 1,
    progress_every: int = 0,
    probe_C: float = 0.25,
    probe_max_iter: int = 1000,
    prefix_residual_control: bool = False,
    prefix_residual_alpha: float = 10.0,
    prefix_residual_dim: int = 256,
) -> dict[str, Any]:
    data = load_dataset(dataset_path, layer=layer)
    prepared = filter_balanced_topics(
        data,
        min_topic_classes=min_topic_classes,
        min_label_per_topic=min_label_per_topic,
    )
    if prepared["status"] != "ready":
        return blocked_report(
            dataset_path=dataset_path,
            data=data,
            prepared=prepared,
            min_topic_classes=min_topic_classes,
            min_label_per_topic=min_label_per_topic,
            min_mixed_prompt_groups=min_mixed_prompt_groups,
            reason="Dataset lacks enough balanced SUPPORTED/UNSUPPORTED rows per topic.",
        )

    groups = prepared["groups"]
    prompts = prepared["prompts"]
    generated_prefix_texts = prepared["generated_prefix_texts"]
    y = prepared["support_status"]
    timing_summary = summarize_timing_points(prepared["timing_points"], prepared["timing_indices"])
    prompt_contract = summarize_prompt_group_contract(groups, prompts, y)
    if len(set(groups.tolist())) < folds:
        return blocked_report(
            dataset_path=dataset_path,
            data=data,
            prepared=prepared,
            min_topic_classes=min_topic_classes,
            min_label_per_topic=min_label_per_topic,
            min_mixed_prompt_groups=min_mixed_prompt_groups,
            reason=f"Need at least {folds} exact prompt groups for grouped folds.",
            prompt_contract=prompt_contract,
        )

    x = prepared["features"]
    topics = prepared["topic"]
    domains = prepared["domain"]
    evidence_sources = prepared["evidence_source"]
    retrieval_conditions = prepared["retrieval_condition"]
    retrieval_score_buckets = prepared["retrieval_score_bucket"]
    challenge_modes = prepared["challenge_mode"]
    evidence_lengths = prepared["evidence_length"]
    fold_indices = make_group_folds(groups, n_folds=folds, seed=seed)

    hidden_pred = cross_val_linear_probe_predict(
        x,
        y,
        fold_indices,
        C=probe_C,
        max_iter=probe_max_iter,
    )
    hidden_ba = balanced_accuracy(y, hidden_pred)

    l0_x = layer_zero_features(prepared)
    if l0_x is not None and int(prepared["layer"]) != 0:
        l0_pred = cross_val_linear_probe_predict(
            l0_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        )
        l0_ba: float | None = balanced_accuracy(y, l0_pred)
    else:
        l0_ba = None

    prompt_word_x = hash_text_features(prompts, dim=text_dim)
    prompt_char_x = hash_char_ngram_features(prompts, dim=text_dim)
    generated_prefix_word_x = hash_text_features(generated_prefix_texts, dim=text_dim)
    generated_prefix_char_x = hash_char_ngram_features(generated_prefix_texts, dim=text_dim)

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
    generated_prefix_text_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            generated_prefix_word_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    generated_prefix_char_text_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            generated_prefix_char_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    prefix_residual_ba: float | None = None
    prefix_residual_minus_prefix_char_ba: float | None = None
    if prefix_residual_control:
        residual_dim = max(16, int(prefix_residual_dim))
        residual_prefix_word_x = hash_text_features(generated_prefix_texts, dim=residual_dim)
        residual_prefix_char_x = hash_char_ngram_features(
            generated_prefix_texts,
            dim=residual_dim,
        )
        generated_prefix_joint_x = np.hstack(
            [residual_prefix_word_x, residual_prefix_char_x],
        ).astype(np.float32)
        prefix_residual_pred = cross_val_prefix_residual_probe_predict(
            hidden_x=x,
            prefix_x=generated_prefix_joint_x,
            y=y,
            fold_indices=fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
            ridge_alpha=prefix_residual_alpha,
        )
        prefix_residual_ba = balanced_accuracy(y, prefix_residual_pred)
        prefix_residual_minus_prefix_char_ba = (
            prefix_residual_ba - generated_prefix_char_text_ba
        )
    length_x = np.asarray([[len(prompt)] for prompt in prompts], dtype=np.float32)
    prompt_length_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            length_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    evidence_length_x = np.asarray(evidence_lengths, dtype=np.float32).reshape(-1, 1)
    evidence_length_ba = balanced_accuracy(
        y,
        cross_val_linear_probe_predict(
            evidence_length_x,
            y,
            fold_indices,
            C=probe_C,
            max_iter=probe_max_iter,
        ),
    )
    topic_ba = balanced_accuracy(y, cross_val_category_majority_predict(topics, y, fold_indices))
    domain_ba = balanced_accuracy(y, cross_val_category_majority_predict(domains, y, fold_indices))
    evidence_source_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(evidence_sources, y, fold_indices),
    )
    retrieval_condition_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(retrieval_conditions, y, fold_indices),
    )
    retrieval_score_bucket_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(retrieval_score_buckets, y, fold_indices),
    )
    challenge_mode_ba = balanced_accuracy(
        y,
        cross_val_category_majority_predict(challenge_modes, y, fold_indices),
    )
    topic_breakdown = {
        topic: balanced_accuracy(y[topics == topic], hidden_pred[topics == topic])
        for topic in sorted(set(topics.tolist()))
    }
    permutation_p = restricted_payload_permutation_p(
        x=x,
        y=y,
        payloads=topics,
        fold_indices=fold_indices,
        observed_ba=hidden_ba,
        seed=seed,
        permutations=permutations,
        probe_C=probe_C,
        probe_max_iter=probe_max_iter,
        jobs=control_jobs,
        progress_label="within-topic permutation",
        progress_every=progress_every,
    )
    shuffled_mean = shuffled_label_control_mean(
        x=x,
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

    pre_display_requires_residual = timing_summary["primary_timing_point"] != "W0"
    gates = {
        "exact_prompt_group_pass": prompt_contract["non_exact_prompt_group_count"] == 0,
        "same_prompt_mixed_group_floor_pass": (
            prompt_contract["mixed_prompt_group_count"] >= min_mixed_prompt_groups
        ),
        "topic_floor_pass": prepared["testable_topic_count"] >= min_topic_classes,
        "label_per_topic_floor_pass": prepared["label_per_topic_floor_pass"],
        "hidden_balanced_accuracy_pass": hidden_ba >= PASS_BA,
        "l0_baseline_present_pass": l0_ba is not None,
        "l0_margin_pass": l0_ba is not None and hidden_ba - l0_ba >= PASS_BASELINE_MARGIN,
        "text_margin_pass": hidden_ba - text_ba >= PASS_BASELINE_MARGIN,
        "char_text_margin_pass": hidden_ba - char_text_ba >= PASS_BASELINE_MARGIN,
        "generated_prefix_text_margin_pass": hidden_ba - generated_prefix_text_ba >= PASS_BASELINE_MARGIN,
        "generated_prefix_char_text_margin_pass": (
            hidden_ba - generated_prefix_char_text_ba >= PASS_BASELINE_MARGIN
        ),
        "topic_margin_pass": hidden_ba - topic_ba >= PASS_BASELINE_MARGIN,
        "domain_margin_pass": hidden_ba - domain_ba >= PASS_BASELINE_MARGIN,
        "evidence_source_margin_pass": hidden_ba - evidence_source_ba >= PASS_BASELINE_MARGIN,
        "retrieval_condition_margin_pass": hidden_ba - retrieval_condition_ba >= PASS_BASELINE_MARGIN,
        "retrieval_score_bucket_margin_pass": hidden_ba - retrieval_score_bucket_ba >= PASS_BASELINE_MARGIN,
        "challenge_mode_margin_pass": hidden_ba - challenge_mode_ba >= PASS_BASELINE_MARGIN,
        "prompt_length_margin_pass": hidden_ba - prompt_length_ba >= PASS_BASELINE_MARGIN,
        "evidence_length_margin_pass": hidden_ba - evidence_length_ba >= PASS_BASELINE_MARGIN,
        "shuffled_control_pass": shuffled_mean <= PASS_SHUFFLED_MEAN_MAX,
        "within_topic_permutation_pass": permutation_p < PASS_PERMUTATION_P,
        "per_topic_floor_pass": all(score >= PASS_PAYLOAD_BA for score in topic_breakdown.values()),
    }
    if pre_display_requires_residual:
        gates.update(
            {
                "prefix_residual_control_run_pass": prefix_residual_ba is not None,
                "prefix_residual_hidden_balanced_accuracy_pass": (
                    prefix_residual_ba is not None and prefix_residual_ba >= PASS_BA
                ),
                "prefix_residual_generated_prefix_char_margin_pass": (
                    prefix_residual_minus_prefix_char_ba is not None
                    and prefix_residual_minus_prefix_char_ba >= PASS_BASELINE_MARGIN
                ),
            }
        )
    overall = all(gates.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset_path),
        "status": "PASS" if overall else "FAIL",
        "claim": (
            "LICENSED only for this model/layer/protocol "
            f"{timing_summary['primary_timing_point']} hidden-state hallucination-risk detection screen."
            if overall
            else "OPEN / NOT LICENSED for internal hallucination-risk timing detection."
        ),
        "claim_ceiling": (
            "This is detection only. It does not license hallucination prevention "
            "unless a separate intervention/guardrail proof reduces unsupported "
            "answers while preserving answer quality."
        ),
        "target": {
            "primary": (
                "prompt-stage W0 future answer support status"
                if timing_summary["primary_timing_point"] == "W0"
                else f"{timing_summary['primary_timing_point']} early-generation pre-display support status"
            ),
            "labels": list(SUPPORT_LABELS),
            "positive_label": "UNSUPPORTED",
            "timing": timing_summary,
        },
        "readout_method": {
            "hidden_readout": "StandardScaler + LogisticRegression",
            "class_weight": "balanced",
            "solver": "lbfgs",
            "C": float(probe_C),
            "max_iter": int(probe_max_iter),
            "control_jobs": int(control_jobs),
            "progress_every": int(progress_every),
            "grouped_folds": "prompt_group_id / derived exact prompt carrier",
            "min_mixed_prompt_groups": int(min_mixed_prompt_groups),
            "generated_prefix_controls": "word and character n-gram baselines over generated_prefix_texts",
            "prefix_residual_control": bool(prefix_residual_control),
            "prefix_residual_required_for_license": bool(pre_display_requires_residual),
            "prefix_residual_control_method": (
                "Fold-local Ridge residualization of hidden states against generated-prefix "
                "word+char features, followed by logistic probe on hidden residuals."
                if prefix_residual_control
                else "not_run"
            ),
            "prefix_residual_alpha": float(prefix_residual_alpha),
            "prefix_residual_dim_per_channel": int(max(16, prefix_residual_dim)),
        },
        "layer": prepared["layer"],
        "row_count": int(len(y)),
        "fold_count": int(len(fold_indices)),
        "prompt_group_count": int(prompt_contract["prompt_group_count"]),
        "exact_prompt_group_count": int(prompt_contract["exact_prompt_group_count"]),
        "mixed_prompt_group_count": int(prompt_contract["mixed_prompt_group_count"]),
        "prompt_group_contract": prompt_contract,
        "topic_distribution": prepared["topic_distribution"],
        "support_status_distribution": dict(sorted(Counter(y.tolist()).items())),
        "domain_distribution": dict(sorted(Counter(domains.tolist()).items())),
        "evidence_source_distribution": dict(sorted(Counter(evidence_sources.tolist()).items())),
        "retrieval_condition_distribution": dict(sorted(Counter(retrieval_conditions.tolist()).items())),
        "retrieval_score_bucket_distribution": dict(sorted(Counter(retrieval_score_buckets.tolist()).items())),
        "challenge_mode_distribution": dict(sorted(Counter(challenge_modes.tolist()).items())),
        "metrics": {
            "hidden_balanced_accuracy": round(hidden_ba, 6),
            "l0_embedding_balanced_accuracy": round(l0_ba, 6) if l0_ba is not None else None,
            "text_hash_balanced_accuracy": round(text_ba, 6),
            "char_text_hash_balanced_accuracy": round(char_text_ba, 6),
            "generated_prefix_text_hash_balanced_accuracy": round(generated_prefix_text_ba, 6),
            "generated_prefix_char_text_hash_balanced_accuracy": round(generated_prefix_char_text_ba, 6),
            "prefix_residual_hidden_balanced_accuracy": (
                round(prefix_residual_ba, 6) if prefix_residual_ba is not None else None
            ),
            "prefix_residual_hidden_minus_generated_prefix_char_text_balanced_accuracy": (
                round(prefix_residual_minus_prefix_char_ba, 6)
                if prefix_residual_minus_prefix_char_ba is not None
                else None
            ),
            "topic_majority_balanced_accuracy": round(topic_ba, 6),
            "domain_majority_balanced_accuracy": round(domain_ba, 6),
            "evidence_source_majority_balanced_accuracy": round(evidence_source_ba, 6),
            "retrieval_condition_majority_balanced_accuracy": round(retrieval_condition_ba, 6),
            "retrieval_score_bucket_majority_balanced_accuracy": round(retrieval_score_bucket_ba, 6),
            "challenge_mode_majority_balanced_accuracy": round(challenge_mode_ba, 6),
            "prompt_length_balanced_accuracy": round(prompt_length_ba, 6),
            "evidence_length_balanced_accuracy": round(evidence_length_ba, 6),
            "hidden_minus_l0_embedding_balanced_accuracy": (
                round(hidden_ba - l0_ba, 6) if l0_ba is not None else None
            ),
            "hidden_minus_text_balanced_accuracy": round(hidden_ba - text_ba, 6),
            "hidden_minus_char_text_balanced_accuracy": round(hidden_ba - char_text_ba, 6),
            "hidden_minus_generated_prefix_text_balanced_accuracy": round(
                hidden_ba - generated_prefix_text_ba,
                6,
            ),
            "hidden_minus_generated_prefix_char_text_balanced_accuracy": round(
                hidden_ba - generated_prefix_char_text_ba,
                6,
            ),
            "hidden_minus_topic_balanced_accuracy": round(hidden_ba - topic_ba, 6),
            "hidden_minus_domain_balanced_accuracy": round(hidden_ba - domain_ba, 6),
            "hidden_minus_evidence_source_balanced_accuracy": round(hidden_ba - evidence_source_ba, 6),
            "hidden_minus_retrieval_condition_balanced_accuracy": round(hidden_ba - retrieval_condition_ba, 6),
            "hidden_minus_retrieval_score_bucket_balanced_accuracy": (
                round(hidden_ba - retrieval_score_bucket_ba, 6)
            ),
            "hidden_minus_challenge_mode_balanced_accuracy": round(hidden_ba - challenge_mode_ba, 6),
            "hidden_minus_prompt_length_balanced_accuracy": round(hidden_ba - prompt_length_ba, 6),
            "hidden_minus_evidence_length_balanced_accuracy": round(hidden_ba - evidence_length_ba, 6),
            "within_topic_permutation_p": round(permutation_p, 6),
            "shuffled_label_hidden_mean_balanced_accuracy": round(shuffled_mean, 6),
            "per_topic_hidden_balanced_accuracy": {
                key: round(value, 6) for key, value in topic_breakdown.items()
            },
        },
        "gates": gates,
        "important_limits": [
            "Grouped folds keep exact prompt/evidence carriers out of both train and test.",
            "Prompt groups must contain both SUPPORTED and UNSUPPORTED realizations of the same factual setup.",
            "Layer-0, word text, char text, topic, domain, evidence source, retrieval condition, retrieval score, challenge mode, prompt length, and evidence length baselines must lose by margin.",
            "For W1/W8 pre-display states, generated-prefix word and character text baselines must also lose by margin.",
            "For non-W0 pre-display states, prefix-residual hidden features must still pass after generated-prefix word+char signal is removed.",
            "Permutation shuffles labels only inside topic.",
            "This script does not prove prevention or causality.",
            "The prefix-residual control is a licensing gate whenever generated prefix text exists.",
        ],
    }


def load_dataset(path: Path, *, layer: int | None) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as data:
        features = data["features"].astype(np.float32)
        layers = data["layers"].astype(int)
        support_status = load_support_labels(data)
        topic = load_string_array(data, "labels_topic", fallback_name="labels_payload_class")
        domain = load_string_array(data, "labels_domain", default="unknown", count=len(support_status))
        evidence_source = load_string_array(
            data,
            "labels_evidence_source",
            default="unknown",
            count=len(support_status),
        )
        retrieval_condition = load_string_array(
            data,
            "labels_retrieval_condition",
            default="unknown",
            count=len(support_status),
        )
        retrieval_score_bucket = load_string_array(
            data,
            "labels_retrieval_score_bucket",
            default="unknown",
            count=len(support_status),
        )
        challenge_mode = load_string_array(
            data,
            "labels_challenge_mode",
            default="unknown",
            count=len(support_status),
        )
        evidence_text = load_string_array(
            data,
            "evidence_texts",
            default="",
            count=len(support_status),
        )
        generated_prefix_texts = load_string_array(
            data,
            "generated_prefix_texts",
            default="",
            count=len(support_status),
        )
        timing_points = load_string_array(
            data,
            "timing_points",
            default="W0",
            count=len(support_status),
        )
        timing_indices = (
            np.asarray(data["timing_indices"], dtype=np.int64)
            if "timing_indices" in data.files
            else np.zeros(len(support_status), dtype=np.int64)
        )
        prompts = np.asarray(data["prompts"], dtype=object).astype(str)
        scenario_ids = np.asarray(data["scenario_ids"], dtype=object).astype(str)
        prompt_group_ids = (
            np.asarray(data["prompt_group_ids"], dtype=object).astype(str)
            if "prompt_group_ids" in data.files
            else None
        )
        trace_ids = (
            np.asarray(data["trace_ids"], dtype=object).astype(str)
            if "trace_ids" in data.files
            else scenario_ids.copy()
        )
        if features.ndim == 2:
            features = features[:, None, :]
        if layer is None:
            layer_position = 0
            resolved_layer = int(layers[0]) if len(layers) else 0
        else:
            matches = np.where(layers == layer)[0]
            if len(matches) == 0:
                raise RuntimeError(f"Layer {layer} is not present in dataset layers {layers.tolist()}")
            layer_position = int(matches[0])
            resolved_layer = int(layer)
    return {
        "features": features[:, layer_position, :],
        "features_by_layer": features,
        "layers": layers,
        "layer": resolved_layer,
        "support_status": support_status,
        "topic": topic,
        "domain": domain,
        "evidence_source": evidence_source,
        "retrieval_condition": retrieval_condition,
        "retrieval_score_bucket": retrieval_score_bucket,
        "challenge_mode": challenge_mode,
        "evidence_length": np.asarray([len(text) for text in evidence_text.tolist()], dtype=np.float32),
        "generated_prefix_texts": generated_prefix_texts,
        "timing_points": timing_points,
        "timing_indices": timing_indices,
        "prompts": prompts,
        "scenario_ids": scenario_ids,
        "trace_ids": trace_ids,
        "groups": prompt_group_ids
        if prompt_group_ids is not None
        else np.asarray(
            [derive_group_id(sid, prompt) for sid, prompt in zip(scenario_ids, prompts, strict=True)],
            dtype=object,
        ),
    }


def load_support_labels(data: Any) -> np.ndarray:
    if "labels_support_status" not in data.files:
        raise RuntimeError("Dataset must contain labels_support_status with SUPPORTED/UNSUPPORTED labels.")
    labels = [normalise_support_label(value) for value in np.asarray(data["labels_support_status"], dtype=object).tolist()]
    if any(label is None for label in labels):
        raise RuntimeError("labels_support_status must contain only SUPPORTED/UNSUPPORTED labels.")
    return np.asarray(labels, dtype=object).astype(str)


def normalise_support_label(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    aliases = {
        "SUPPORT": "SUPPORTED",
        "GROUNDED": "SUPPORTED",
        "TRUE_SUPPORTED": "SUPPORTED",
        "UNSUPPORT": "UNSUPPORTED",
        "UNSUPPORTED_CLAIM": "UNSUPPORTED",
        "HALLUCINATED": "UNSUPPORTED",
        "HALLUCINATION": "UNSUPPORTED",
    }
    text = aliases.get(text, text)
    return text if text in SUPPORT_LABELS else None


def load_string_array(
    data: Any,
    name: str,
    *,
    fallback_name: str | None = None,
    default: str | None = None,
    count: int | None = None,
) -> np.ndarray:
    if name in data.files:
        return np.asarray(data[name], dtype=object).astype(str)
    if fallback_name and fallback_name in data.files:
        return np.asarray(data[fallback_name], dtype=object).astype(str)
    if default is not None and count is not None:
        return np.asarray([default] * count, dtype=object).astype(str)
    raise RuntimeError(f"Dataset must contain {name}.")


def filter_balanced_topics(
    data: dict[str, Any],
    *,
    min_topic_classes: int,
    min_label_per_topic: int,
) -> dict[str, Any]:
    labels = data["support_status"]
    topics = data["topic"]
    keep_topics: list[str] = []
    distribution: dict[str, dict[str, int]] = {}
    label_floor_pass = True
    for topic in sorted(set(topics.tolist())):
        mask = topics == topic
        counts = Counter(labels[mask].tolist())
        distribution[topic] = dict(sorted(counts.items()))
        has_floor = all(counts.get(label, 0) >= min_label_per_topic for label in SUPPORT_LABELS)
        label_floor_pass = label_floor_pass and has_floor
        if has_floor:
            keep_topics.append(topic)
    if len(keep_topics) < min_topic_classes:
        return {
            "status": "blocked_insufficient_balanced_topics",
            "testable_topic_count": len(keep_topics),
            "label_per_topic_floor_pass": False,
            "topic_distribution": distribution,
        }
    mask = np.isin(topics, np.asarray(keep_topics, dtype=str)) & np.isin(
        labels,
        np.asarray(SUPPORT_LABELS, dtype=str),
    )
    out = {
        "status": "ready",
        "testable_topic_count": len(keep_topics),
        "label_per_topic_floor_pass": label_floor_pass,
    }
    for key, value in data.items():
        if isinstance(value, np.ndarray) and len(value) == len(mask):
            out[key] = value[mask]
        else:
            out[key] = value
    out["topic_distribution"] = {topic: distribution[topic] for topic in keep_topics}
    return out


def layer_zero_features(prepared: dict[str, Any]) -> np.ndarray | None:
    layers = np.asarray(prepared.get("layers", []), dtype=int)
    matches = np.where(layers == 0)[0]
    if len(matches) == 0:
        return None
    features_by_layer = prepared.get("features_by_layer")
    if not isinstance(features_by_layer, np.ndarray) or features_by_layer.ndim != 3:
        return None
    return features_by_layer[:, int(matches[0]), :]


def cross_val_prefix_residual_probe_predict(
    *,
    hidden_x: np.ndarray,
    prefix_x: np.ndarray,
    y: np.ndarray,
    fold_indices: list[np.ndarray],
    C: float,
    max_iter: int,
    ridge_alpha: float,
) -> np.ndarray:
    """Predict from hidden signal left after removing generated-prefix explainers.

    Each fold fits the prefix-to-hidden residualizer only on train rows. This
    keeps the generated-prefix control honest: test-row hidden vectors are
    residualized by a model that has never seen that exact prompt group.
    """

    predictions = np.empty(len(y), dtype=object)
    all_indices = np.arange(len(y))
    for test_idx in fold_indices:
        train_idx = np.setdiff1d(all_indices, test_idx)
        prefix_scaler = StandardScaler()
        hidden_scaler = StandardScaler()
        prefix_train = prefix_scaler.fit_transform(prefix_x[train_idx])
        prefix_test = prefix_scaler.transform(prefix_x[test_idx])
        hidden_train = hidden_scaler.fit_transform(hidden_x[train_idx])
        hidden_test = hidden_scaler.transform(hidden_x[test_idx])
        residualizer = Ridge(alpha=float(ridge_alpha), solver="svd")
        residualizer.fit(prefix_train, hidden_train)
        residual_train = hidden_train - residualizer.predict(prefix_train)
        residual_test = hidden_test - residualizer.predict(prefix_test)
        clf = LogisticRegression(
            C=C,
            class_weight="balanced",
            max_iter=max_iter,
            solver="lbfgs",
        )
        clf.fit(residual_train, y[train_idx])
        predictions[test_idx] = clf.predict(residual_test)
    return predictions.astype(str)


def summarize_prompt_group_contract(
    groups: np.ndarray,
    prompts: np.ndarray,
    labels: np.ndarray,
) -> dict[str, Any]:
    prompts_by_group: dict[str, set[str]] = defaultdict(set)
    labels_by_group: dict[str, set[str]] = defaultdict(set)
    rows_by_group: Counter[str] = Counter()
    for group, prompt, label in zip(groups.tolist(), prompts.tolist(), labels.tolist(), strict=True):
        key = str(group)
        prompts_by_group[key].add(str(prompt))
        labels_by_group[key].add(str(label))
        rows_by_group[key] += 1
    non_exact = sorted(group for group, group_prompts in prompts_by_group.items() if len(group_prompts) != 1)
    mixed = sorted(
        group
        for group, group_labels in labels_by_group.items()
        if {"SUPPORTED", "UNSUPPORTED"}.issubset(group_labels)
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
            "Every prompt group must hold one exact prompt/evidence setup, and "
            "enough groups must contain both SUPPORTED and UNSUPPORTED outcomes."
        ),
    }


def summarize_timing_points(timing_points: np.ndarray, timing_indices: np.ndarray) -> dict[str, Any]:
    points = np.asarray(timing_points, dtype=object).astype(str)
    indices = np.asarray(timing_indices, dtype=np.int64)
    point_distribution = dict(sorted(Counter(points.tolist()).items()))
    index_distribution = {
        str(key): int(value)
        for key, value in sorted(Counter(int(value) for value in indices.tolist()).items())
    }
    unique_points = sorted(point_distribution)
    primary = unique_points[0] if len(unique_points) == 1 else "MIXED_TIMING"
    return {
        "primary_timing_point": primary,
        "timing_point_distribution": point_distribution,
        "timing_index_distribution": index_distribution,
        "pre_display": primary != "W0",
        "contract": (
            "W0 means before any generated token exists. W1/W8 mean early generated "
            "prefix states before the answer is displayed to the user."
        ),
    }


def blocked_report(
    *,
    dataset_path: Path,
    data: dict[str, Any],
    prepared: dict[str, Any],
    min_topic_classes: int,
    min_label_per_topic: int,
    min_mixed_prompt_groups: int,
    reason: str,
    prompt_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    labels = data.get("support_status", np.asarray([], dtype=object))
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset_path),
        "status": "BLOCKED",
        "claim": "OPEN / NOT LICENSED for internal hallucination-risk timing detection.",
        "claim_ceiling": "Dataset cannot be evaluated as a hallucination-risk timing gate.",
        "blocker": reason,
        "layer": data.get("layer"),
        "timing": summarize_timing_points(
            data.get("timing_points", np.asarray(["W0"], dtype=object)),
            data.get("timing_indices", np.asarray([0], dtype=np.int64)),
        ),
        "row_count": int(len(labels)),
        "required_topic_classes": int(min_topic_classes),
        "required_label_per_topic": int(min_label_per_topic),
        "required_mixed_prompt_groups": int(min_mixed_prompt_groups),
        "testable_topic_count": int(prepared.get("testable_topic_count", 0)),
        "support_status_distribution": dict(sorted(Counter(labels.tolist()).items())),
        "topic_distribution": prepared.get("topic_distribution", {}),
        "prompt_group_contract": prompt_contract or {},
        "metrics": {},
        "gates": {
            "topic_floor_pass": False,
            "label_per_topic_floor_pass": False,
            "exact_prompt_group_pass": False,
            "same_prompt_mixed_group_floor_pass": False,
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
