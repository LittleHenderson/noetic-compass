"""Evaluate paired CJT bias/vibration hidden-state diagnostics.

The CAS PCBA book points at a stronger internal test than a one-shot
classifier: small-signal response. This evaluator compares each risky or
control perturbation against the BASE row in the same prompt group and asks
whether hidden-state deltas identify risky perturbations beyond text controls.

Passing this script does not prove prevention, removal, reversal, or causality.
It is a scoped hidden-state response screen that still needs intervention
proof before any stronger public claim.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.build_cjt_bias_vibration_bank import (  # noqa: E402
    BASE_ROLE,
    BENIGN_ROLE,
    INJECTION_ROLE,
    SUPPORTED_ROLE,
    TRUSTED_CORRECTION_ROLE,
    UNSUPPORTED_ROLE,
)
from scripts.evaluate_behavior_v5_prespeech import (  # noqa: E402
    PASS_BA,
    PASS_BASELINE_MARGIN,
    PASS_PAYLOAD_BA,
    PASS_PERMUTATION_P,
    PASS_SHUFFLED_MEAN_MAX,
    balanced_accuracy,
    cross_val_category_majority_predict,
    cross_val_linear_probe_predict,
    hash_char_ngram_features,
    hash_text_features,
    make_group_folds,
    restricted_payload_permutation_p,
    shuffled_label_control_mean,
)
from scripts.evaluate_hallucination_prespeech import load_string_array  # noqa: E402


SCHEMA_VERSION = "cas_harness_cjt_bias_vibration_diagnostic_eval.v0"
RISK_LABEL = "RISK_PERTURBATION"
CONTROL_LABEL = "CONTROL_PERTURBATION"
RISK_ROLES = {INJECTION_ROLE, UNSUPPORTED_ROLE}
CONTROL_ROLES = {BENIGN_ROLE, TRUSTED_CORRECTION_ROLE, SUPPORTED_ROLE}
DELTA_ROLES = tuple(sorted(RISK_ROLES | CONTROL_ROLES))


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--layer", type=int, default=None)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-dim", type=int, default=4096)
    parser.add_argument("--min-prompt-groups", type=int, default=5)
    parser.add_argument("--min-delta-rows-per-label", type=int, default=12)
    parser.add_argument("--permutations", type=int, default=1000)
    parser.add_argument("--shuffle-controls", type=int, default=50)
    parser.add_argument("--probe-C", type=float, default=0.25)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate_cjt_bias_vibration_diagnostic(
        dataset_path=args.dataset,
        layer=args.layer,
        folds=args.folds,
        seed=args.seed,
        text_dim=args.text_dim,
        min_prompt_groups=args.min_prompt_groups,
        min_delta_rows_per_label=args.min_delta_rows_per_label,
        permutations=args.permutations,
        shuffle_controls=args.shuffle_controls,
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
                "hidden_balanced_accuracy": report["metrics"].get("hidden_balanced_accuracy"),
                "hidden_minus_char_text_balanced_accuracy": report["metrics"].get(
                    "hidden_minus_char_text_balanced_accuracy"
                ),
                "within_family_payload_permutation_p": report["metrics"].get(
                    "within_family_payload_permutation_p"
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"[cjt-bias-vibration] wrote {args.output_report}")
    return 0


def evaluate_cjt_bias_vibration_diagnostic(
    *,
    dataset_path: Path,
    layer: int | None,
    folds: int,
    seed: int,
    text_dim: int,
    min_prompt_groups: int,
    min_delta_rows_per_label: int,
    permutations: int,
    shuffle_controls: int,
    probe_C: float = 0.25,
    probe_max_iter: int = 1000,
) -> dict[str, Any]:
    data = load_dataset(dataset_path, layer=layer)
    delta_rows = build_delta_rows(data)
    if delta_rows["status"] != "ready":
        return blocked_report(
            dataset_path=dataset_path,
            data=data,
            delta_rows=delta_rows,
            reason=str(delta_rows["status"]),
        )

    groups = delta_rows["group_id"]
    y = delta_rows["label"]
    label_counts = Counter(y.tolist())
    group_count = len(set(groups.tolist()))
    timing_summary = summarize_timing(data["timing_points"], data["timing_indices"])
    row_floor_pass = all(
        label_counts.get(label, 0) >= min_delta_rows_per_label
        for label in (RISK_LABEL, CONTROL_LABEL)
    )
    group_floor_pass = group_count >= min_prompt_groups
    timing_contract_pass = timing_summary["primary_timing_point"] in {"W0", "PRE_ANSWER"}
    readiness_gates = {
        "paired_delta_rows_ready_pass": True,
        "prompt_group_floor_pass": group_floor_pass,
        "delta_label_floor_pass": row_floor_pass,
        "timing_contract_pass": timing_contract_pass,
    }
    if not all(readiness_gates.values()):
        return {
            **base_report(dataset_path, data, delta_rows),
            "status": "BLOCKED",
            "claim": "OPEN / NOT LICENSED for CJT bias/vibration hidden response detection.",
            "claim_ceiling": "Dataset lacks enough paired deltas or uses an unsupported timing contract.",
            "readiness_gates": readiness_gates,
            "gates": readiness_gates,
            "metrics": {
                "prompt_group_count": int(group_count),
                "delta_label_distribution": dict(sorted(label_counts.items())),
            },
            "timing": timing_summary,
        }

    assessment = assess_delta_readout(
        delta_rows=delta_rows,
        folds=folds,
        seed=seed,
        text_dim=text_dim,
        permutations=permutations,
        shuffle_controls=shuffle_controls,
        probe_C=probe_C,
        probe_max_iter=probe_max_iter,
    )
    gates = {**readiness_gates, **assessment["gates"]}
    overall = all(gates.values())
    return {
        **base_report(dataset_path, data, delta_rows),
        "status": "PASS" if overall else "FAIL",
        "claim": (
            "LICENSED only for this model/layer/protocol paired CJT bias/vibration hidden response screen."
            if overall
            else "OPEN / NOT LICENSED for CJT bias/vibration hidden response detection."
        ),
        "claim_ceiling": (
            "This evaluates hidden-state deltas under paired perturbations. It is not proof of prompt-injection "
            "removal, reversal, hallucination prevention, live interception, or causal control."
        ),
        "readout_method": {
            "hidden_readout": "StandardScaler + LogisticRegression on role-minus-base hidden deltas",
            "class_weight": "balanced",
            "solver": "lbfgs",
            "C": float(probe_C),
            "max_iter": int(probe_max_iter),
        },
        "pcba_mapping": {
            "bias_terminal": "^5 Female / accumulated substrate: tests whether untrusted perturbations move bias.",
            "vibration": "^4 Vibration / resonance: tests unsupported-lure response before answer display.",
            "gain_terms": "beta/gm/r_pi become measured delta response, framing sensitivity, and resistance.",
            "prompt_injection_signature": "E-CJT-008-style cross-domain bias: low-authority text moving high-authority state.",
        },
        "readiness_gates": readiness_gates,
        "gates": gates,
        "metrics": {
            "prompt_group_count": int(group_count),
            "delta_label_distribution": dict(sorted(label_counts.items())),
            **delta_rows["pcba_response_metrics"],
            **assessment["metrics"],
        },
        "timing": timing_summary,
        "important_limits": [
            "All perturbation deltas are grouped by prompt_group_id; variants from one base prompt stay in one fold.",
            "Word, char, length, layer-0, payload/domain, and family baselines must lose by margin.",
            "The evaluator reads hidden-state response to controlled perturbations, not completed output text.",
            "A PASS is detection-screen evidence only; causal intervention remains separate.",
        ],
        "source_basis": [
            "book/CAS_PCBA_Engineer/Chapter_09_CJT_Deep_Dive.md:28-31 beta/gm/r_pi/saturation",
            "book/CAS_PCBA_Engineer/Chapter_18_CSB_Cognitive_Safety_Board.md:146-148 differential CMRR against injection framing",
            "book/CAS_PCBA_Engineer/Chapter_18_CSB_Cognitive_Safety_Board.md:176-182 low-pass feedback protects bias",
            "book/CAS_PCBA_Engineer/Chapter_23_Testing_Cognitive_Circuits.md:27-31 CJT unit gain test",
            "book/CAS_PCBA_Engineer/Chapter_26_Governance.md:37-56 E-CJT-008 cross-domain bias certification failure",
        ],
    }


def load_dataset(path: Path, *, layer: int | None) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as data:
        features = data["features"].astype(np.float32)
        layers = data["layers"].astype(int)
        prompts = np.asarray(data["prompts"], dtype=object).astype(str)
        scenario_ids = np.asarray(data["scenario_ids"], dtype=object).astype(str)
        groups = load_string_array(data, "prompt_group_ids", count=len(prompts), default="")
        roles = load_string_array(data, "labels_cjt_role", count=len(prompts), default="")
        families = load_string_array(data, "labels_cjt_family", count=len(prompts), default="")
        payloads = load_string_array(data, "labels_payload_class", count=len(prompts), default="unknown")
        domains = load_string_array(data, "labels_domain", count=len(prompts), default="unknown")
        timing_points = load_string_array(data, "timing_points", count=len(prompts), default="W0")
        timing_indices = (
            np.asarray(data["timing_indices"], dtype=np.int64)
            if "timing_indices" in data.files
            else np.zeros(len(prompts), dtype=np.int64)
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
        "prompts": prompts,
        "scenario_ids": scenario_ids,
        "groups": groups,
        "roles": roles,
        "families": families,
        "payloads": payloads,
        "domains": domains,
        "timing_points": timing_points,
        "timing_indices": timing_indices,
    }


def build_delta_rows(data: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    excluded: Counter[str] = Counter()
    by_group: dict[str, list[int]] = defaultdict(list)
    for index, group in enumerate(data["groups"].tolist()):
        by_group[str(group)].append(index)

    for group_id, indices in sorted(by_group.items()):
        role_to_indices: dict[str, list[int]] = defaultdict(list)
        for index in indices:
            role_to_indices[str(data["roles"][index])].append(index)
        if BASE_ROLE not in role_to_indices:
            excluded["missing_base_role"] += 1
            continue
        base_idx = np.asarray(role_to_indices[BASE_ROLE], dtype=int)
        base_hidden = data["features"][base_idx].mean(axis=0)
        base_l0 = layer_zero_group_features(data, base_idx)
        base_prompt = first_prompt(data, base_idx)
        for role in DELTA_ROLES:
            if role not in role_to_indices:
                excluded[f"missing_{role.lower()}"] += 1
                continue
            variant_idx = np.asarray(role_to_indices[role], dtype=int)
            label = RISK_LABEL if role in RISK_ROLES else CONTROL_LABEL
            variant_hidden = data["features"][variant_idx].mean(axis=0)
            variant_l0 = layer_zero_group_features(data, variant_idx)
            rows.append(
                {
                    "group_id": group_id,
                    "role": role,
                    "family": role_family(role, data["families"][variant_idx]),
                    "label": label,
                    "payload_class": str(data["payloads"][variant_idx[0]]),
                    "domain": str(data["domains"][variant_idx[0]]),
                    "features": (variant_hidden - base_hidden).astype(np.float32),
                    "l0_features": None
                    if base_l0 is None or variant_l0 is None
                    else (variant_l0 - base_l0).astype(np.float32),
                    "base_prompt": base_prompt,
                    "variant_prompt": first_prompt(data, variant_idx),
                    "delta_norm": float(np.linalg.norm(variant_hidden - base_hidden)),
                }
            )
    if not rows:
        return {"status": "blocked_no_paired_delta_rows", "excluded": dict(sorted(excluded.items()))}
    labels = np.asarray([row["label"] for row in rows], dtype=object)
    if not {RISK_LABEL, CONTROL_LABEL}.issubset(set(labels.tolist())):
        return {
            "status": "blocked_missing_risk_or_control_delta_rows",
            "excluded": dict(sorted(excluded.items())),
            "delta_label_distribution": dict(sorted(Counter(labels.tolist()).items())),
        }
    return {
        "status": "ready",
        "group_id": np.asarray([row["group_id"] for row in rows], dtype=object),
        "role": np.asarray([row["role"] for row in rows], dtype=object),
        "family": np.asarray([row["family"] for row in rows], dtype=object),
        "label": labels,
        "payload_class": np.asarray([row["payload_class"] for row in rows], dtype=object),
        "domain": np.asarray([row["domain"] for row in rows], dtype=object),
        "features": np.stack([row["features"] for row in rows], axis=0).astype(np.float32),
        "l0_features": stack_optional_l0([row["l0_features"] for row in rows]),
        "base_prompts": np.asarray([row["base_prompt"] for row in rows], dtype=object),
        "variant_prompts": np.asarray([row["variant_prompt"] for row in rows], dtype=object),
        "delta_norms": np.asarray([row["delta_norm"] for row in rows], dtype=np.float32),
        "excluded": dict(sorted(excluded.items())),
        "pcba_response_metrics": pcba_response_metrics(rows),
    }


def assess_delta_readout(
    *,
    delta_rows: dict[str, Any],
    folds: int,
    seed: int,
    text_dim: int,
    permutations: int,
    shuffle_controls: int,
    probe_C: float,
    probe_max_iter: int,
) -> dict[str, Any]:
    x = delta_rows["features"]
    y = delta_rows["label"]
    groups = delta_rows["group_id"]
    payloads = delta_rows["payload_class"]
    domains = delta_rows["domain"]
    families = delta_rows["family"]
    family_payloads = np.asarray(
        [f"{family}:{payload}" for family, payload in zip(families.tolist(), payloads.tolist(), strict=True)],
        dtype=object,
    )
    fold_indices = make_group_folds(groups, n_folds=min(folds, len(set(groups.tolist()))), seed=seed)

    hidden_pred = cross_val_linear_probe_predict(x, y, fold_indices, C=probe_C, max_iter=probe_max_iter)
    hidden_ba = balanced_accuracy(y, hidden_pred)

    l0_x = delta_rows.get("l0_features")
    if isinstance(l0_x, np.ndarray):
        l0_pred = cross_val_linear_probe_predict(l0_x, y, fold_indices, C=probe_C, max_iter=probe_max_iter)
        l0_ba: float | None = balanced_accuracy(y, l0_pred)
    else:
        l0_ba = None

    text_x = delta_hash_features(delta_rows["base_prompts"], delta_rows["variant_prompts"], dim=text_dim, char=False)
    text_pred = cross_val_linear_probe_predict(text_x, y, fold_indices, C=probe_C, max_iter=probe_max_iter)
    text_ba = balanced_accuracy(y, text_pred)

    char_x = delta_hash_features(delta_rows["base_prompts"], delta_rows["variant_prompts"], dim=text_dim, char=True)
    char_pred = cross_val_linear_probe_predict(char_x, y, fold_indices, C=probe_C, max_iter=probe_max_iter)
    char_ba = balanced_accuracy(y, char_pred)

    length_x = length_delta_features(delta_rows["base_prompts"], delta_rows["variant_prompts"])
    length_pred = cross_val_linear_probe_predict(length_x, y, fold_indices, C=probe_C, max_iter=probe_max_iter)
    length_ba = balanced_accuracy(y, length_pred)

    payload_ba = balanced_accuracy(y, cross_val_category_majority_predict(payloads, y, fold_indices))
    domain_ba = balanced_accuracy(y, cross_val_category_majority_predict(domains, y, fold_indices))
    family_ba = balanced_accuracy(y, cross_val_category_majority_predict(families, y, fold_indices))
    permutation_p = restricted_payload_permutation_p(
        x=x,
        y=y,
        payloads=family_payloads,
        fold_indices=fold_indices,
        observed_ba=hidden_ba,
        seed=seed,
        permutations=permutations,
        probe_C=probe_C,
        probe_max_iter=probe_max_iter,
    )
    shuffled_mean = shuffled_label_control_mean(
        x=x,
        y=y,
        fold_indices=fold_indices,
        seed=seed,
        rounds=shuffle_controls,
        probe_C=probe_C,
        probe_max_iter=probe_max_iter,
    )
    per_family_ba = {
        family: balanced_accuracy(y[families == family], hidden_pred[families == family])
        for family in sorted(set(families.tolist()))
        if len(set(y[families == family].tolist())) > 1
    }
    gates = {
        "hidden_balanced_accuracy_pass": hidden_ba >= PASS_BA,
        "text_margin_pass": hidden_ba - text_ba >= PASS_BASELINE_MARGIN,
        "char_text_margin_pass": hidden_ba - char_ba >= PASS_BASELINE_MARGIN,
        "length_margin_pass": hidden_ba - length_ba >= PASS_BASELINE_MARGIN,
        "payload_margin_pass": hidden_ba - payload_ba >= PASS_BASELINE_MARGIN,
        "domain_margin_pass": hidden_ba - domain_ba >= PASS_BASELINE_MARGIN,
        "family_margin_pass": hidden_ba - family_ba >= PASS_BASELINE_MARGIN,
        "l0_baseline_present_pass": l0_ba is not None,
        "l0_margin_pass": bool(l0_ba is not None and hidden_ba - l0_ba >= PASS_BASELINE_MARGIN),
        "per_family_floor_pass": all(value >= PASS_PAYLOAD_BA for value in per_family_ba.values()),
        "shuffled_label_control_pass": shuffled_mean <= PASS_SHUFFLED_MEAN_MAX,
        "within_family_payload_permutation_pass": permutation_p < PASS_PERMUTATION_P,
    }
    return {
        "gates": gates,
        "metrics": {
            "hidden_balanced_accuracy": float(hidden_ba),
            "word_text_delta_balanced_accuracy": float(text_ba),
            "char_text_delta_balanced_accuracy": float(char_ba),
            "length_delta_balanced_accuracy": float(length_ba),
            "payload_class_balanced_accuracy": float(payload_ba),
            "domain_balanced_accuracy": float(domain_ba),
            "family_balanced_accuracy": float(family_ba),
            "l0_delta_balanced_accuracy": None if l0_ba is None else float(l0_ba),
            "hidden_minus_word_text_balanced_accuracy": float(hidden_ba - text_ba),
            "hidden_minus_char_text_balanced_accuracy": float(hidden_ba - char_ba),
            "hidden_minus_length_balanced_accuracy": float(hidden_ba - length_ba),
            "hidden_minus_l0_balanced_accuracy": None if l0_ba is None else float(hidden_ba - l0_ba),
            "per_family_hidden_balanced_accuracy": per_family_ba,
            "within_family_payload_permutation_p": float(permutation_p),
            "shuffled_label_control_mean": float(shuffled_mean),
        },
    }


def delta_hash_features(base_prompts: np.ndarray, variant_prompts: np.ndarray, *, dim: int, char: bool) -> np.ndarray:
    base = hash_char_ngram_features(base_prompts, dim=dim) if char else hash_text_features(base_prompts, dim=dim)
    variant = (
        hash_char_ngram_features(variant_prompts, dim=dim)
        if char
        else hash_text_features(variant_prompts, dim=dim)
    )
    return (variant - base).astype(np.float32)


def length_delta_features(base_prompts: np.ndarray, variant_prompts: np.ndarray) -> np.ndarray:
    base_lengths = np.asarray([len(text) for text in base_prompts.tolist()], dtype=np.float32)
    variant_lengths = np.asarray([len(text) for text in variant_prompts.tolist()], dtype=np.float32)
    delta = variant_lengths - base_lengths
    return np.stack([delta, np.abs(delta), base_lengths, variant_lengths], axis=1).astype(np.float32)


def layer_zero_group_features(data: dict[str, Any], indices: np.ndarray) -> np.ndarray | None:
    layers = np.asarray(data.get("layers", []), dtype=int)
    matches = np.where(layers == 0)[0]
    if len(matches) == 0:
        return None
    features_by_layer = data.get("features_by_layer")
    if not isinstance(features_by_layer, np.ndarray) or features_by_layer.ndim != 3:
        return None
    return features_by_layer[indices, int(matches[0]), :].mean(axis=0)


def stack_optional_l0(values: list[np.ndarray | None]) -> np.ndarray | None:
    if any(value is None for value in values):
        return None
    return np.stack([value for value in values if value is not None], axis=0).astype(np.float32)


def first_prompt(data: dict[str, Any], indices: np.ndarray) -> str:
    prompts = data["prompts"][indices].tolist()
    return str(prompts[0]) if prompts else ""


def role_family(role: str, family_values: np.ndarray) -> str:
    if role in {INJECTION_ROLE, BENIGN_ROLE, TRUSTED_CORRECTION_ROLE}:
        return "instruction_integrity"
    if role in {SUPPORTED_ROLE, UNSUPPORTED_ROLE}:
        return "factual_support"
    for value in family_values.tolist():
        text = str(value).strip()
        if text:
            return text
    return "unknown"


def pcba_response_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_role: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_role[str(row["role"])].append(float(row["delta_norm"]))
    mean_by_role = {role: float(np.mean(values)) for role, values in sorted(by_role.items()) if values}
    eps = 1e-6
    return {
        "mean_hidden_delta_norm_by_role": mean_by_role,
        "cross_domain_bias_response_ratio": ratio(
            mean_by_role.get(INJECTION_ROLE),
            mean_by_role.get(BENIGN_ROLE),
            eps=eps,
        ),
        "untrusted_vs_trusted_bias_response_ratio": ratio(
            mean_by_role.get(INJECTION_ROLE),
            mean_by_role.get(TRUSTED_CORRECTION_ROLE),
            eps=eps,
        ),
        "unsupported_vibration_response_ratio": ratio(
            mean_by_role.get(UNSUPPORTED_ROLE),
            mean_by_role.get(SUPPORTED_ROLE),
            eps=eps,
        ),
    }


def ratio(numerator: float | None, denominator: float | None, *, eps: float) -> float | None:
    if numerator is None or denominator is None:
        return None
    return float(numerator / max(float(denominator), eps))


def summarize_timing(timing_points: np.ndarray, timing_indices: np.ndarray) -> dict[str, Any]:
    points = np.asarray(timing_points, dtype=object).astype(str)
    indices = np.asarray(timing_indices, dtype=np.int64)
    unique = sorted(set(points.tolist()))
    return {
        "primary_timing_point": unique[0] if len(unique) == 1 else "MIXED_TIMING",
        "timing_point_distribution": dict(sorted(Counter(points.tolist()).items())),
        "timing_index_distribution": {
            str(index): int(count) for index, count in sorted(Counter(indices.tolist()).items())
        },
        "contract": "W0 is prompt-stage. PRE_ANSWER requires generated-prefix residual controls elsewhere.",
    }


def base_report(dataset_path: Path, data: dict[str, Any], delta_rows: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset_path),
        "layer": data.get("layer"),
        "row_count": int(len(data.get("prompts", []))),
        "delta_row_count": int(len(delta_rows.get("label", []))) if isinstance(delta_rows.get("label"), np.ndarray) else 0,
        "role_distribution": dict(sorted(Counter(data.get("roles", np.asarray([], dtype=object)).tolist()).items())),
        "payload_class_distribution": dict(
            sorted(Counter(data.get("payloads", np.asarray([], dtype=object)).tolist()).items())
        ),
    }


def blocked_report(
    *,
    dataset_path: Path,
    data: dict[str, Any],
    delta_rows: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        **base_report(dataset_path, data, delta_rows),
        "status": "BLOCKED",
        "claim": "OPEN / NOT LICENSED for CJT bias/vibration hidden response detection.",
        "claim_ceiling": "Dataset cannot be evaluated as a paired CJT bias/vibration diagnostic.",
        "blocker": reason,
        "gates": {
            "paired_delta_rows_ready_pass": False,
        },
        "metrics": {},
        "excluded": delta_rows.get("excluded", {}),
    }


if __name__ == "__main__":
    raise SystemExit(main())
