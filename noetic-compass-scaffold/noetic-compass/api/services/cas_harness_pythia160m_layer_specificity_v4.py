"""Prospective, model-free Pythia-160M V4 layer-specificity controller.

This module cannot load a model or execute an intervention.  It freezes and
validates the request matrix and independently evaluates synthetic/result
mappings for the future, separately authorized executor and auditor.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "cas_harness_pythia160m_layer_specificity_controller.v4"
LOCK_SCHEMA_VERSION = "cas_harness_pythia160m_research_lock.v4"
FEATURE_FLAG = "CAS_PYTHIA160M_LAYER_SPECIFICITY_V4_ENABLED"
LIVE_FLAG = "CAS_PYTHIA160M_RESEARCH_LIVE"
TARGET_LAYER = 3
LAYER_UNIVERSE = tuple(range(12))
DOSES = (-0.5, -0.25, 0.25, 0.5)
LAYER_SWEEP_DOSES = (-0.5, 0.5)
CALIBRATION_COUNT = 16
HELDOUT_COUNT = 38
PLANNED_FORWARD_PASSES = 1536


class V4PreparationError(RuntimeError):
    """Raised when a frozen preparation or audit requirement drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise V4PreparationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def framework_modules_loaded() -> list[str]:
    return sorted(name for name in ("torch", "transformers") if name in sys.modules)


def assert_preparation_only() -> dict[str, Any]:
    _require(
        os.environ.get(FEATURE_FLAG, "").strip().lower()
        not in {"1", "true", "yes", "on"},
        "V4 preparation controller cannot execute a research run",
    )
    _require(
        os.environ.get(LIVE_FLAG, "").strip().lower()
        not in {"1", "true", "yes", "on"},
        "Live research mode is prohibited",
    )
    _require(not framework_modules_loaded(), "Framework imported in preparation mode")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PREPARATION_ONLY / DISABLED / RUN_NOT_AUTHORIZED",
        "framework_imports": [],
        "model_loads": 0,
        "output_writes": 0,
    }


def _verify_record(repo_root: Path, record: Mapping[str, Any], label: str) -> None:
    path = repo_root / str(record.get("path", ""))
    _require(path.is_file(), f"{label} missing")
    _require(path.stat().st_size == int(record.get("byte_count", -1)), f"{label} size drift")
    _require(sha256_file(path) == record.get("sha256"), f"{label} hash drift")


def _prompt_rows(prompt_split: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    calibration: list[dict[str, Any]] = []
    heldout: list[dict[str, Any]] = []
    for label in ("^0|C", "^0|E"):
        for prompt_id in prompt_split["calibration"][label]:
            calibration.append(
                {"prompt_id": prompt_id, "label": label, "category": "target_contrast"}
            )
        for prompt_id in prompt_split["heldout"][label]:
            heldout.append(
                {"prompt_id": prompt_id, "label": label, "category": "target_contrast"}
            )
    for item in prompt_split["collateral_heldout"]:
        heldout.append(
            {
                "prompt_id": item["prompt_id"],
                "label": "collateral",
                "category": item["category"],
            }
        )
    _require(len(calibration) == CALIBRATION_COUNT, "Calibration split drift")
    _require(len(heldout) == HELDOUT_COUNT, "Held-out split drift")
    all_ids = [row["prompt_id"] for row in calibration + heldout]
    _require(len(all_ids) == len(set(all_ids)), "Prompt split overlap")
    return calibration, heldout


def build_request_plan(
    lock: Mapping[str, Any], prompt_split: Mapping[str, Any]
) -> list[dict[str, Any]]:
    design = lock["diagnostic_design"]
    _require(design["target_layer"] == TARGET_LAYER, "Target layer drift")
    _require(tuple(design["layer_universe"]) == LAYER_UNIVERSE, "Layer universe drift")
    _require(tuple(design["target_layer_doses_l2"]) == DOSES, "Dose grid drift")
    calibration, heldout = _prompt_rows(prompt_split)
    seed_base = int(design["seed_schedule"]["request_seed_base"])
    requests: list[dict[str, Any]] = []

    for row in calibration:
        requests.append(
            {
                **row,
                "split": "calibration",
                "condition": "readout_calibration_baseline",
                "dose": 0.0,
                "effective_layer": None,
                "seed": seed_base + len(requests),
            }
        )

    for row in heldout:
        conditions: list[tuple[str, float, int | None]] = [
            ("baseline", 0.0, None),
            ("no_op", 0.0, TARGET_LAYER),
        ]
        conditions.extend(
            ("target_layer_direction", dose, TARGET_LAYER) for dose in DOSES
        )
        for layer in LAYER_UNIVERSE:
            if layer == TARGET_LAYER:
                continue
            conditions.extend(
                ("off_target_layer_direction", dose, layer)
                for dose in LAYER_SWEEP_DOSES
            )
        for condition in (
            "same_norm_random_direction",
            "wrong_token",
            "wrong_axis",
            "layer2_projection_patchback",
            "layer2_full_state_patchback",
            "target_layer_full_state_patchback",
        ):
            layer = 2 if condition.startswith("layer2_") else TARGET_LAYER
            conditions.extend((condition, dose, layer) for dose in LAYER_SWEEP_DOSES)
        _require(len(conditions) == 40, "Per-prompt request matrix drift")
        for condition, dose, layer in conditions:
            requests.append(
                {
                    **row,
                    "split": "heldout",
                    "condition": condition,
                    "dose": dose,
                    "effective_layer": layer,
                    "seed": seed_base + len(requests),
                }
            )

    _require(len(requests) == PLANNED_FORWARD_PASSES, "Forward-pass plan drift")
    _require(
        len(requests) == int(lock["compute_cap"]["frozen_planned_forward_passes"]),
        "Frozen forward-pass count drift",
    )
    return requests


def validate_v4_lock(repo_root: Path, lock_path: Path) -> dict[str, Any]:
    assert_preparation_only()
    lock = load_json(lock_path)
    _require(lock.get("schema_version") == LOCK_SCHEMA_VERSION, "V4 lock schema drift")
    _require(
        lock.get("status")
        == "PROSPECTIVE_DIAGNOSTIC_SUCCESSOR_LOCK / MODEL_FREE_LOCAL_PASS / RUN_NOT_AUTHORIZED",
        "V4 lock status drift",
    )
    gates = lock["execution_gates"]
    _require(gates["feature_flag_default"] == "disabled", "Feature default drift")
    _require(gates["receipt_status"] == "ABSENT / CREATION_NOT_AUTHORIZED", "Receipt authority drift")
    _require(gates["output_status"] == "ABSENT", "Output status drift")
    _require(gates["live_worker_integration"] == "prohibited", "Live integration drift")
    for label, record in lock["preserved_v3_evidence"].items():
        _verify_record(repo_root, record, f"preserved_v3_evidence.{label}")
    for label, record in lock["frozen_files"].items():
        _verify_record(repo_root, record, f"frozen_files.{label}")
    prompt_split = load_json(
        repo_root / lock["frozen_files"]["prompt_split"]["path"]
    )
    requests = build_request_plan(lock, prompt_split)
    _require(
        lock["compute_cap"]["max_forward_passes"] == PLANNED_FORWARD_PASSES,
        "Compute ceiling must equal the exact plan",
    )
    _require(lock["compute_cap"]["max_generated_tokens"] == 0, "Generation cap drift")
    for field in (
        "network_allowed",
        "provider_calls_allowed",
        "paid_compute_allowed",
        "runpod_allowed",
        "gpu_query_allowed",
        "gpu_use_allowed",
        "retry_allowed",
        "resume_allowed",
        "repair_top_up_backfill_allowed",
    ):
        _require(lock["compute_cap"][field] is False, f"Compute boundary drift: {field}")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "V4_MODEL_FREE_LOCK_VALIDATION_PASS / RUN_NOT_AUTHORIZED",
        "request_count": len(requests),
        "calibration_prompt_count": CALIBRATION_COUNT,
        "heldout_prompt_count": HELDOUT_COUNT,
        "framework_imports": framework_modules_loaded(),
        "model_loads": 0,
        "receipt_creations": 0,
        "output_writes": 0,
    }


def _median(values: Sequence[float]) -> float:
    _require(bool(values), "Median requested for empty values")
    return float(statistics.median(values))


def _rank(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + end - 1) / 2.0
        for position in range(start, end):
            ranks[order[position]] = rank
        start = end
    return ranks


def _spearman(left: Sequence[float], right: Sequence[float]) -> float:
    _require(len(left) == len(right) and len(left) > 1, "Spearman input drift")
    x = _rank(left)
    y = _rank(right)
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True))
    denominator = math.sqrt(
        sum((a - x_mean) ** 2 for a in x)
        * sum((b - y_mean) ** 2 for b in y)
    )
    return numerator / denominator if denominator else 0.0


def _quantile(values: Sequence[float], share: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(share * len(ordered)) - 1))
    return float(ordered[index])


def audit_result_mapping(
    *,
    lock: Mapping[str, Any],
    prompt_split: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    expected = build_request_plan(lock, prompt_split)
    records = packet.get("records", [])
    _require(isinstance(records, list), "Records must be a list")
    findings: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            findings.append(code)

    key_fields = ("prompt_id", "split", "condition", "dose", "effective_layer", "seed")
    expected_keys = [tuple(row[field] for field in key_fields) for row in expected]
    actual_keys = [tuple(row.get(field) for field in key_fields) for row in records]
    require(actual_keys == expected_keys, "EXACT_REQUEST_MATRIX_DRIFT")
    if actual_keys != expected_keys:
        return {
            "schema_version": "cas_harness_pythia160m_layer_specificity_audit.v4",
            "audit_status": "FAIL_CLOSED",
            "findings": findings,
            "claim_status": "RESEARCH_ONLY / NO DECISION AUTHORITY",
        }

    target_rows = [
        row
        for row in records
        if row["split"] == "heldout" and row["category"] == "target_contrast"
    ]
    collateral_rows = [
        row
        for row in records
        if row["split"] == "heldout" and row["category"] != "target_contrast"
    ]
    baseline = [row for row in target_rows if row["condition"] == "baseline"]
    target_count = sum(row["label"] == "^0|C" for row in baseline)
    contrast_count = sum(row["label"] == "^0|E" for row in baseline)
    target_correct = sum(
        row["label"] == "^0|C" and float(row["final_readout_margin"]) > 0
        for row in baseline
    )
    contrast_correct = sum(
        row["label"] == "^0|E" and float(row["final_readout_margin"]) < 0
        for row in baseline
    )
    balanced_accuracy = 0.5 * (
        target_correct / target_count + contrast_correct / contrast_count
    )
    thresholds = lock["thresholds_and_stop_rules"]
    require(
        balanced_accuracy
        >= float(thresholds["common_readout_validity"]["minimum_heldout_balanced_accuracy"]),
        "COMMON_READOUT_INVALID",
    )

    no_op_limit = float(thresholds["no_op_equivalence"]["max_abs_logit_delta"])
    no_op_max = max(
        abs(float(row["downstream_logit_max_abs_delta"]))
        for row in records
        if row["condition"] == "no_op"
    )
    require(no_op_max <= no_op_limit, "NO_OP_EQUIVALENCE_FAIL")

    effect_lookup: dict[tuple[str, str, float, int | None], float] = {}
    for row in target_rows:
        if row["condition"] == "baseline":
            continue
        effect_lookup[
            (
                row["prompt_id"],
                row["condition"],
                float(row["dose"]),
                row["effective_layer"],
            )
        ] = float(row["final_readout_margin_delta"])

    prompt_ids = [row["prompt_id"] for row in baseline]
    target_medians: dict[float, float] = {}
    for dose in DOSES:
        target_medians[dose] = _median(
            [
                effect_lookup[(prompt_id, "target_layer_direction", dose, TARGET_LAYER)]
                for prompt_id in prompt_ids
            ]
        )
    rho = _spearman(list(DOSES), [target_medians[dose] for dose in DOSES])
    response = thresholds["target_layer_dose_response"]
    require(rho >= float(response["minimum_spearman_rho"]), "TARGET_DOSE_RESPONSE_FAIL")
    for dose in LAYER_SWEEP_DOSES:
        require(
            abs(target_medians[dose])
            >= float(response["minimum_median_abs_effect_at_dose_0_5"]),
            f"TARGET_EFFECT_FLOOR_FAIL:{dose}",
        )
        require(
            math.copysign(1.0, target_medians[dose]) == math.copysign(1.0, dose),
            f"TARGET_EFFECT_SIGN_FAIL:{dose}",
        )

    specificity = thresholds["layer_specificity"]
    ceiling = float(specificity["maximum_off_target_to_target_median_abs_effect_ratio"])
    point_ratios: dict[str, float] = {}
    bootstrap_upper: dict[str, float] = {}
    rng = random.Random(int(specificity["bootstrap_seed"]))
    bootstrap_samples = int(specificity["bootstrap_samples"])
    for dose in LAYER_SWEEP_DOSES:
        target_abs = abs(target_medians[dose])
        layer_effects: dict[int, list[float]] = {}
        for layer in LAYER_UNIVERSE:
            if layer == TARGET_LAYER:
                continue
            layer_effects[layer] = [
                effect_lookup[(prompt_id, "off_target_layer_direction", dose, layer)]
                for prompt_id in prompt_ids
            ]
        ratio = max(abs(_median(values)) for values in layer_effects.values()) / target_abs
        point_ratios[str(dose)] = ratio
        require(ratio <= ceiling, f"LAYER_SPECIFICITY_POINT_FAIL:{dose}")
        require(
            all(abs(_median(values)) < target_abs for values in layer_effects.values()),
            f"TARGET_LAYER_NOT_UNIQUE_MAX:{dose}",
        )
        sampled_ratios: list[float] = []
        for _ in range(bootstrap_samples):
            sampled_ids = [rng.choice(prompt_ids) for _ in prompt_ids]
            sampled_target = abs(
                _median(
                    [
                        effect_lookup[
                            (prompt_id, "target_layer_direction", dose, TARGET_LAYER)
                        ]
                        for prompt_id in sampled_ids
                    ]
                )
            )
            if sampled_target == 0:
                sampled_ratios.append(math.inf)
                continue
            sampled_ratios.append(
                max(
                    abs(
                        _median(
                            [
                                effect_lookup[
                                    (
                                        prompt_id,
                                        "off_target_layer_direction",
                                        dose,
                                        layer,
                                    )
                                ]
                                for prompt_id in sampled_ids
                            ]
                        )
                    )
                    for layer in layer_effects
                )
                / sampled_target
            )
        upper = _quantile(sampled_ratios, float(specificity["bootstrap_upper_quantile"]))
        bootstrap_upper[str(dose)] = upper
        require(upper <= ceiling, f"LAYER_SPECIFICITY_BOOTSTRAP_FAIL:{dose}")

    control_ratios: dict[str, dict[str, float]] = {}
    control_ceiling = float(
        thresholds["non_layer_controls"][
            "maximum_control_to_target_median_abs_effect_ratio"
        ]
    )
    for condition in ("same_norm_random_direction", "wrong_token", "wrong_axis"):
        control_ratios[condition] = {}
        for dose in LAYER_SWEEP_DOSES:
            value = abs(
                _median(
                    [
                        effect_lookup[(prompt_id, condition, dose, TARGET_LAYER)]
                        for prompt_id in prompt_ids
                    ]
                )
            ) / abs(target_medians[dose])
            control_ratios[condition][str(dose)] = value
            require(value <= control_ceiling, f"CONTROL_EFFECT_CEILING_FAIL:{condition}:{dose}")

    full_patch_limit = float(
        thresholds["full_state_patchback"]["maximum_abs_downstream_logit_residual"]
    )
    for condition in ("layer2_full_state_patchback", "target_layer_full_state_patchback"):
        residual = max(
            abs(float(row["downstream_logit_max_abs_delta"]))
            for row in records
            if row["condition"] == condition
        )
        require(residual <= full_patch_limit, f"FULL_STATE_PATCHBACK_FAIL:{condition}")

    minimum_reduction = float(
        thresholds["projection_patchback_diagnostic"][
            "minimum_median_effect_reduction_fraction"
        ]
    )
    projection_reductions: dict[str, float] = {}
    transport_supported = True
    for dose in LAYER_SWEEP_DOSES:
        raw = abs(
            _median(
                [
                    effect_lookup[
                        (prompt_id, "off_target_layer_direction", dose, 2)
                    ]
                    for prompt_id in prompt_ids
                ]
            )
        )
        patched = abs(
            _median(
                [
                    effect_lookup[
                        (prompt_id, "layer2_projection_patchback", dose, 2)
                    ]
                    for prompt_id in prompt_ids
                ]
            )
        )
        reduction = 1.0 - patched / raw if raw else 0.0
        projection_reductions[str(dose)] = reduction
        transport_supported = transport_supported and reduction >= minimum_reduction

    finite_share = sum(bool(row["finite_logits"]) for row in records) / len(records)
    require(
        finite_share == float(thresholds["artifact_integrity"]["finite_logit_share"]),
        "NONFINITE_ARTIFACT",
    )
    collateral_target_rows = [
        row for row in collateral_rows if row["condition"] == "target_layer_direction"
    ]
    collateral_preservation = sum(bool(row["top1_preserved"]) for row in collateral_target_rows) / len(
        collateral_target_rows
    )
    require(
        collateral_preservation
        >= float(thresholds["collateral_floor"]["minimum_top1_preservation_share"]),
        "COLLATERAL_HARM_STOP",
    )

    gates = {
        "exact_request_matrix": True,
        "common_readout_validity": "COMMON_READOUT_INVALID" not in findings,
        "no_op_equivalence": "NO_OP_EQUIVALENCE_FAIL" not in findings,
        "target_layer_dose_response": not any(
            finding.startswith("TARGET_") for finding in findings
        ),
        "layer_specificity": not any(
            finding.startswith("LAYER_SPECIFICITY_")
            or finding.startswith("TARGET_LAYER_NOT_UNIQUE")
            for finding in findings
        ),
        "non_layer_controls": not any(
            finding.startswith("CONTROL_EFFECT_CEILING_FAIL") for finding in findings
        ),
        "full_state_patchback": not any(
            finding.startswith("FULL_STATE_PATCHBACK_FAIL") for finding in findings
        ),
        "artifact_integrity": "NONFINITE_ARTIFACT" not in findings,
        "collateral_floor": "COLLATERAL_HARM_STOP" not in findings,
    }
    return {
        "schema_version": "cas_harness_pythia160m_layer_specificity_audit.v4",
        "audit_status": "AUDIT_PASS_RESEARCH_ONLY" if not findings else "FAIL_CLOSED",
        "findings": findings,
        "gates": gates,
        "common_readout_balanced_accuracy": balanced_accuracy,
        "target_layer_median_effect_by_dose": {
            str(dose): target_medians[dose] for dose in DOSES
        },
        "target_layer_spearman_rho": rho,
        "off_target_to_target_point_ratio_by_sign": point_ratios,
        "off_target_to_target_bootstrap_upper_by_sign": bootstrap_upper,
        "non_layer_control_ratios": control_ratios,
        "projection_patchback_reduction_by_sign": projection_reductions,
        "transport_diagnostic": (
            "ADJACENT_TARGET_PROJECTION_MEDIATION_SUPPORTED_RESEARCH_ONLY"
            if transport_supported
            else "ADJACENT_TRANSPORT_UNRESOLVED"
        ),
        "transport_diagnostic_decision_authority": "NONE",
        "claim_status": "RESEARCH_ONLY / NO LIVE STEERING / NO PRODUCTION OR SAFETY CLAIM",
    }
