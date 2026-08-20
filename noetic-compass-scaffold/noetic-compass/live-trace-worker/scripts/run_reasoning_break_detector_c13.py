#!/usr/bin/env python3
"""Strict offline C13 reasoning-break detector engineering pipeline.

This module deliberately starts with a canonical synthetic full-width trajectory
fixture.  It exercises the complete detector method without presenting synthetic
measurements as model evidence.  Every result is therefore permanently marked
``NOT_PACKET_ELIGIBLE`` and ``NOT_REAL_MODEL_VERIFIED``.

The method keeps event labels in an independent table, enforces group-disjoint
registered train/validation/test partitions, chooses the temporal window and
layer from validation data only, calibrates risk on validation data, and opens
the test partition only after the detector and abstention thresholds are frozen.

CLI examples (all local and offline)::

    python run_reasoning_break_detector_c13.py emit-synthetic --directory ./c13
    python run_reasoning_break_detector_c13.py evaluate \
        --config ./c13/c13.preregistration.json \
        --dataset ./c13/c13.synthetic-dataset.json \
        --output ./c13/c13.result.json
    python run_reasoning_break_detector_c13.py verify \
        --config ./c13/c13.preregistration.json \
        --dataset ./c13/c13.synthetic-dataset.json \
        --result ./c13/c13.result.json

No network, provider, model, credential, or production service is used here.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping, Sequence
import warnings

import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


CONFIG_SCHEMA = "cas_reasoning_break_c13_preregistration.v1"
DATASET_SCHEMA = "cas_reasoning_break_c13_dataset.v1"
RESULT_SCHEMA = "cas_reasoning_break_c13_result.v1"
CAPABILITY_ID = "C13_REASONING_BREAK_DETECTION"
ARTIFACT_KIND = "CANONICAL_SYNTHETIC_FULL_WIDTH_TRAJECTORY_FIXTURE"
PACKET_ELIGIBILITY = "NOT_PACKET_ELIGIBLE"
REAL_MODEL_VERIFICATION = "NOT_REAL_MODEL_VERIFIED"
SCIENTIFIC_STATUS = "NOT_A_SCIENTIFIC_RESULT"
CONFIG_STATUS = "PREREGISTERED_OFFLINE_ENGINEERING_PROTOCOL"
DATASET_STATUS = "CANONICAL_SYNTHETIC_FIXTURE_ONLY"
RESULT_STATUS = "SYNTHETIC_OFFLINE_ENGINEERING_EVALUATION_COMPLETED"
SPLITS = ("train", "validation", "test")
WINDOWS = ("W0", "W1", "Wk")
HASH_RE = re.compile(r"^[0-9A-F]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

CONFIG_CLAIM_BOUNDARY = (
    "A self-hashed local preregistration is an integrity binding, not an "
    "external timestamp, signature, or proof that registration preceded data access."
)
DATASET_CLAIM_BOUNDARY = (
    "Deterministic synthetic trajectories and generator-ground-truth labels only. "
    "They test pipeline mechanics and do not measure a model or a real reasoning event."
)
RESULT_CLAIM_BOUNDARY = (
    "Offline synthetic engineering result only. Calibration, abstention, controls, "
    "and gates reported here do not validate a model safety detector or Evidence Packet."
)
LABEL_SOURCE = "CANONICAL_SYNTHETIC_EVENT_PLAN_FIXED_BEFORE_TRAJECTORY_SYNTHESIS"
LABEL_STAGE = "BEFORE_TRAJECTORY_SYNTHESIS"
SELECTION_RULE = (
    "LOWEST_VALIDATION_BRIER_THEN_HIGHEST_VALIDATION_SELECTIVE_BALANCED_"
    "ACCURACY_THEN_PREREGISTERED_WINDOW_ORDER_THEN_LOWEST_LAYER"
)
TEST_POLICY = (
    "NO_TEST_ACCESS_UNTIL_WINDOW_LAYER_CALIBRATOR_AND_THRESHOLDS_ARE_FROZEN"
)
TREE_ALGORITHM = "SHA256_CANONICAL_SORTED_FEATURE_AND_LABEL_LEAVES_V1"


def canonical_json_bytes(value: object) -> bytes:
    """Return the only admitted JSON byte representation."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def self_hash(value: Mapping[str, object], field: str) -> dict[str, object]:
    unsigned = deepcopy(dict(value))
    unsigned.pop(field, None)
    unsigned[field] = sha256_bytes(canonical_json_bytes(unsigned))
    return unsigned


def _verify_self_hash(value: Mapping[str, object], field: str, label: str) -> str:
    claimed = value.get(field)
    _require_sha256(claimed, f"{label}.{field}")
    unsigned = deepcopy(dict(value))
    unsigned.pop(field, None)
    observed = sha256_bytes(canonical_json_bytes(unsigned))
    if claimed != observed:
        raise ValueError(f"{label} self-hash mismatch")
    return observed


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def strict_json_bytes(raw: bytes, *, label: str, max_bytes: int) -> dict[str, Any]:
    if not raw or len(raw) > max_bytes:
        raise ValueError(f"{label} byte count is outside the admitted range")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} must be strict UTF-8") from exc
    value = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_nonfinite_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    _assert_finite_json(value, label)
    if raw != canonical_json_bytes(value):
        raise ValueError(f"{label} bytes are not canonical JSON")
    return value


def read_canonical_snapshot(
    path: Path, *, label: str, max_bytes: int
) -> tuple[dict[str, Any], bytes]:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} path must be an absolute plain file")
    with path.open("rb") as handle:
        raw = handle.read(max_bytes + 1)
    return strict_json_bytes(raw, label=label, max_bytes=max_bytes), raw


def _assert_finite_json(value: object, label: str) -> None:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} contains non-finite data")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_finite_json(item, f"{label}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{label} contains a non-text object key")
            _assert_finite_json(item, f"{label}.{key}")
        return
    raise ValueError(f"{label} contains a non-JSON value")


def _require_exact_keys(value: object, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    if set(value) != expected:
        raise ValueError(f"{label} keyset mismatch")
    return value


def _require_literal(value: Mapping[str, Any], key: str, expected: object, label: str) -> None:
    if value.get(key) != expected:
        raise ValueError(f"{label}.{key} must equal {expected!r}")


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be an uppercase SHA-256")
    return value


def _require_id(value: object, label: str) -> str:
    if not isinstance(value, str) or ID_RE.fullmatch(value) is None:
        raise ValueError(f"{label} is not a canonical identifier")
    return value


def _require_int(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer in [{minimum}, {maximum}]")
    return value


def _require_number(value: object, label: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{label} must be finite and in [{minimum}, {maximum}]")
    return result


def build_default_preregistration() -> dict[str, object]:
    """Build the fixed offline C13 method declaration used by the fixture."""

    unsigned: dict[str, object] = {
        "schema_version": CONFIG_SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": CONFIG_STATUS,
        "seed": 130013,
        "candidate_layers": [0, 1, 2],
        "windows": {
            "order": list(WINDOWS),
            "W0": "CURRENT_EVENT_STATE",
            "W1": "CURRENT_STATE_PLUS_ONE_STEP_DELTA",
            "Wk": "CURRENT_STATE_PLUS_K_STEP_DELTA_MEAN_VELOCITY_AND_RMS_VELOCITY",
            "k": 3,
        },
        "probe": {
            "method": "STANDARD_SCALER_BALANCED_LOGISTIC_REGRESSION",
            "C": 1.0,
            "max_iter": 1000,
            "solver": "lbfgs",
        },
        "calibration": {
            "method": "PLATT_LOGISTIC_VALIDATION_ONLY",
            "C": 1.0,
            "max_iter": 1000,
            "ece_bins": 10,
        },
        "decision": {
            "thresholds": {
                "clear_max_risk": 0.35,
                "alert_min_risk": 0.65,
            },
            "gates": {
                "min_test_coverage": 0.70,
                "min_test_selective_balanced_accuracy": 0.80,
                "max_validation_ece": 0.20,
                "min_hidden_minus_surface_balanced_accuracy": 0.10,
                "min_hidden_minus_shuffled_max_balanced_accuracy": 0.05,
            },
        },
        "negative_control": {
            "method": "GROUP_LABEL_PERMUTATION_WITHIN_EACH_SPLIT_SELECTION_AWARE",
            "trials": 5,
        },
        "surface_baseline": {
            "method": "CHARACTER_1_TO_2_GRAM_HASHING_PLUS_BALANCED_LOGISTIC",
            "n_features": 256,
        },
        "selection_rule": SELECTION_RULE,
        "test_policy": TEST_POLICY,
        "claim_boundary": CONFIG_CLAIM_BOUNDARY,
    }
    return self_hash(unsigned, "config_sha256")


def validate_preregistration(value: Mapping[str, object]) -> dict[str, object]:
    _assert_finite_json(value, "preregistration")
    config = _require_exact_keys(
        value,
        {
            "schema_version",
            "capability_id",
            "status",
            "seed",
            "candidate_layers",
            "windows",
            "probe",
            "calibration",
            "decision",
            "negative_control",
            "surface_baseline",
            "selection_rule",
            "test_policy",
            "claim_boundary",
            "config_sha256",
        },
        "preregistration",
    )
    _require_literal(config, "schema_version", CONFIG_SCHEMA, "preregistration")
    _require_literal(config, "capability_id", CAPABILITY_ID, "preregistration")
    _require_literal(config, "status", CONFIG_STATUS, "preregistration")
    _require_literal(config, "selection_rule", SELECTION_RULE, "preregistration")
    _require_literal(config, "test_policy", TEST_POLICY, "preregistration")
    _require_literal(config, "claim_boundary", CONFIG_CLAIM_BOUNDARY, "preregistration")
    _verify_self_hash(config, "config_sha256", "preregistration")
    _require_int(config["seed"], "preregistration.seed", minimum=0, maximum=2**31 - 1)

    layers = config["candidate_layers"]
    if (
        not isinstance(layers, list)
        or not 1 <= len(layers) <= 256
        or any(isinstance(layer, bool) or not isinstance(layer, int) for layer in layers)
        or layers != sorted(set(layers))
        or layers != list(range(len(layers)))
    ):
        raise ValueError("candidate_layers must be sorted unique contiguous zero-based integers")

    windows = _require_exact_keys(
        config["windows"], {"order", "W0", "W1", "Wk", "k"}, "preregistration.windows"
    )
    _require_literal(windows, "order", list(WINDOWS), "preregistration.windows")
    _require_literal(windows, "W0", "CURRENT_EVENT_STATE", "preregistration.windows")
    _require_literal(
        windows,
        "W1",
        "CURRENT_STATE_PLUS_ONE_STEP_DELTA",
        "preregistration.windows",
    )
    _require_literal(
        windows,
        "Wk",
        "CURRENT_STATE_PLUS_K_STEP_DELTA_MEAN_VELOCITY_AND_RMS_VELOCITY",
        "preregistration.windows",
    )
    _require_int(windows["k"], "preregistration.windows.k", minimum=2, maximum=32)

    probe = _require_exact_keys(
        config["probe"], {"method", "C", "max_iter", "solver"}, "preregistration.probe"
    )
    _require_literal(
        probe, "method", "STANDARD_SCALER_BALANCED_LOGISTIC_REGRESSION", "preregistration.probe"
    )
    _require_literal(probe, "solver", "lbfgs", "preregistration.probe")
    _require_number(probe["C"], "preregistration.probe.C", minimum=1e-9, maximum=1e6)
    _require_int(probe["max_iter"], "preregistration.probe.max_iter", minimum=10, maximum=100000)

    calibration = _require_exact_keys(
        config["calibration"],
        {"method", "C", "max_iter", "ece_bins"},
        "preregistration.calibration",
    )
    _require_literal(
        calibration, "method", "PLATT_LOGISTIC_VALIDATION_ONLY", "preregistration.calibration"
    )
    _require_number(calibration["C"], "preregistration.calibration.C", minimum=1e-9, maximum=1e6)
    _require_int(
        calibration["max_iter"],
        "preregistration.calibration.max_iter",
        minimum=10,
        maximum=100000,
    )
    _require_int(calibration["ece_bins"], "preregistration.calibration.ece_bins", minimum=2, maximum=100)

    decision = _require_exact_keys(
        config["decision"], {"thresholds", "gates"}, "preregistration.decision"
    )
    thresholds = _require_exact_keys(
        decision["thresholds"],
        {"clear_max_risk", "alert_min_risk"},
        "preregistration.decision.thresholds",
    )
    clear = _require_number(
        thresholds["clear_max_risk"],
        "preregistration.decision.thresholds.clear_max_risk",
        minimum=0.0,
        maximum=1.0,
    )
    alert = _require_number(
        thresholds["alert_min_risk"],
        "preregistration.decision.thresholds.alert_min_risk",
        minimum=0.0,
        maximum=1.0,
    )
    if not clear < 0.5 < alert:
        raise ValueError("preregistered abstention thresholds must straddle 0.5")
    gates = _require_exact_keys(
        decision["gates"],
        {
            "min_test_coverage",
            "min_test_selective_balanced_accuracy",
            "max_validation_ece",
            "min_hidden_minus_surface_balanced_accuracy",
            "min_hidden_minus_shuffled_max_balanced_accuracy",
        },
        "preregistration.decision.gates",
    )
    for key, raw in gates.items():
        _require_number(raw, f"preregistration.decision.gates.{key}", minimum=0.0, maximum=1.0)

    negative = _require_exact_keys(
        config["negative_control"], {"method", "trials"}, "preregistration.negative_control"
    )
    _require_literal(
        negative,
        "method",
        "GROUP_LABEL_PERMUTATION_WITHIN_EACH_SPLIT_SELECTION_AWARE",
        "preregistration.negative_control",
    )
    _require_int(negative["trials"], "preregistration.negative_control.trials", minimum=1, maximum=100)
    surface = _require_exact_keys(
        config["surface_baseline"], {"method", "n_features"}, "preregistration.surface_baseline"
    )
    _require_literal(
        surface,
        "method",
        "CHARACTER_1_TO_2_GRAM_HASHING_PLUS_BALANCED_LOGISTIC",
        "preregistration.surface_baseline",
    )
    n_features = _require_int(
        surface["n_features"], "preregistration.surface_baseline.n_features", minimum=16, maximum=65536
    )
    if n_features & (n_features - 1):
        raise ValueError("surface_baseline.n_features must be a power of two")
    return deepcopy(dict(config))


def _capture_sha256(feature: Mapping[str, object]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "capture_id": feature["capture_id"],
                "trajectory": feature["trajectory"],
            }
        )
    )


def _label_sha256(label: Mapping[str, object]) -> str:
    unsigned = deepcopy(dict(label))
    unsigned.pop("label_sha256", None)
    return sha256_bytes(canonical_json_bytes(unsigned))


def _feature_leaf_sha256(feature: Mapping[str, object]) -> str:
    return sha256_bytes(canonical_json_bytes(feature))


def _dataset_tree(feature_records: Sequence[Mapping[str, object]], labels: Sequence[Mapping[str, object]]) -> tuple[list[dict[str, str]], str]:
    leaves = [
        {
            "kind": "FEATURE_RECORD",
            "id": str(row["record_id"]),
            "sha256": _feature_leaf_sha256(row),
        }
        for row in feature_records
    ] + [
        {
            "kind": "EVENT_LABEL",
            "id": str(row["event_id"]),
            "sha256": _label_sha256(row),
        }
        for row in labels
    ]
    leaves.sort(key=lambda row: (row["kind"], row["id"]))
    return leaves, sha256_bytes(canonical_json_bytes(leaves))


def resign_dataset(value: Mapping[str, object]) -> dict[str, object]:
    """Recompute all dataset integrity fields; useful for fixture construction/tests."""

    dataset = deepcopy(dict(value))
    features = dataset["feature_records"]
    labels = dataset["event_labels"]
    if not isinstance(features, list) or not isinstance(labels, list):
        raise ValueError("dataset tables must be lists")
    for feature in features:
        if not isinstance(feature, dict):
            raise ValueError("feature row must be an object")
        feature["capture_sha256"] = _capture_sha256(feature)
    for label in labels:
        if not isinstance(label, dict):
            raise ValueError("label row must be an object")
        label["label_sha256"] = _label_sha256(label)
    _leaves, tree_sha256 = _dataset_tree(features, labels)
    registration = dataset.get("registration")
    if not isinstance(registration, dict):
        raise ValueError("dataset registration must be an object")
    registration["feature_table_sha256"] = sha256_bytes(canonical_json_bytes(features))
    registration["label_table_sha256"] = sha256_bytes(canonical_json_bytes(labels))
    registration["tree_sha256"] = tree_sha256
    dataset.pop("dataset_sha256", None)
    return self_hash(dataset, "dataset_sha256")


def build_canonical_synthetic_fixture(
    preregistration: Mapping[str, object],
    *,
    groups_per_split: int = 18,
    records_per_group: int = 2,
) -> dict[str, object]:
    """Create deterministic full-width trajectories with preplanned event labels."""

    config = validate_preregistration(preregistration)
    if groups_per_split < 6 or groups_per_split % 2:
        raise ValueError("groups_per_split must be an even integer of at least six")
    if records_per_group < 1 or records_per_group > 8:
        raise ValueError("records_per_group must be in [1, 8]")
    seed = int(config["seed"])
    rng = np.random.default_rng(seed)
    layers = len(config["candidate_layers"])
    k = int(config["windows"]["k"])
    steps = k + 2
    hidden_width = 4

    # Labels are fixed first.  Trajectories are synthesized only after this
    # independent event plan exists in memory.
    event_plan: list[tuple[str, str, int, int]] = []
    for split_index, split in enumerate(SPLITS):
        planned = np.asarray([0] * (groups_per_split // 2) + [1] * (groups_per_split // 2))
        planned = rng.permutation(planned)
        for group_index, label in enumerate(planned.tolist()):
            group_id = f"{split}-group-{group_index:03d}"
            event_plan.append((split, group_id, int(label), split_index))

    feature_records: list[dict[str, object]] = []
    event_labels: list[dict[str, object]] = []
    for split, group_id, label, split_index in event_plan:
        for record_index in range(records_per_group):
            record_id = f"{group_id}-record-{record_index:02d}"
            event_id = f"{group_id}-event-{record_index:02d}"
            capture_id = f"{group_id}-capture-{record_index:02d}"
            residual = rng.normal(0.0, 0.08, size=(steps, layers, hidden_width))
            mlp = rng.normal(0.0, 0.08, size=(steps, layers, hidden_width))
            # The endpoint is shared; direction reverses before the endpoint.
            # W1/Wk contain signal while W0 remains mostly uninformative.
            direction = 1.0 if label == 1 else -1.0
            pattern = np.asarray([-2.0, -1.0, 0.0, 1.0, 0.0], dtype=np.float64) * direction
            residual[:, 1, 0] = pattern + rng.normal(0.0, 0.03, size=steps)
            residual[:, 1, 1] = -0.5 * pattern + rng.normal(0.0, 0.03, size=steps)
            mlp[:, 1, 0] = 0.7 * pattern + rng.normal(0.0, 0.03, size=steps)
            mlp[:, 1, 2] = -0.4 * pattern + rng.normal(0.0, 0.03, size=steps)
            trajectory = {
                "residual_states": np.round(residual, 7).tolist(),
                "mlp_states": np.round(mlp, 7).tolist(),
            }
            feature: dict[str, object] = {
                "record_id": record_id,
                "event_id": event_id,
                "group_id": group_id,
                "split": split,
                "surface_text": (
                    "Routine status review variant alpha."
                    if record_index % 2 == 0
                    else "Routine status review variant beta."
                ),
                "capture_id": capture_id,
                "trajectory": trajectory,
                "capture_sha256": "0" * 64,
            }
            label_row: dict[str, object] = {
                "event_id": event_id,
                "record_id": record_id,
                "group_id": group_id,
                "split": split,
                "break_label": label,
                "annotation_source": LABEL_SOURCE,
                "label_assignment_stage": LABEL_STAGE,
                "annotated_without_trajectory_access": True,
                "label_sha256": "0" * 64,
            }
            feature_records.append(feature)
            event_labels.append(label_row)

    unsigned: dict[str, object] = {
        "schema_version": DATASET_SCHEMA,
        "artifact_kind": ARTIFACT_KIND,
        "status": DATASET_STATUS,
        "preregistration_sha256": config["config_sha256"],
        "capture_contract": {
            "residual": "SYNTHETIC_FULL_WIDTH_EVERY_STEP_EVERY_LAYER",
            "mlp": "SYNTHETIC_FULL_WIDTH_EVERY_STEP_EVERY_LAYER",
            "steps": steps,
            "layers": layers,
            "hidden_width": hidden_width,
            "numeric_encoding": "CANONICAL_JSON_FINITE_NUMBERS_INTERPRETED_AS_FLOAT64",
        },
        "label_contract": {
            "task": "BINARY_REASONING_BREAK_EVENT",
            "values": {"0": "NO_BREAK", "1": "BREAK"},
            "source": LABEL_SOURCE,
            "assignment_stage": LABEL_STAGE,
            "feature_table_contains_labels": False,
        },
        "feature_records": feature_records,
        "event_labels": event_labels,
        "registration": {
            "tree_algorithm": TREE_ALGORITHM,
            "feature_table_sha256": "0" * 64,
            "label_table_sha256": "0" * 64,
            "tree_sha256": "0" * 64,
        },
        "claim_boundary": DATASET_CLAIM_BOUNDARY,
    }
    return resign_dataset(unsigned)


class DatasetView:
    def __init__(
        self,
        *,
        record_ids: list[str],
        event_ids: list[str],
        group_ids: np.ndarray,
        splits: np.ndarray,
        surface_texts: list[str],
        residual: np.ndarray,
        mlp: np.ndarray,
        labels: np.ndarray,
    ) -> None:
        self.record_ids = record_ids
        self.event_ids = event_ids
        self.group_ids = group_ids
        self.splits = splits
        self.surface_texts = surface_texts
        self.residual = residual
        self.mlp = mlp
        self.labels = labels
        self.indices = {
            split: np.asarray([i for i, observed in enumerate(splits.tolist()) if observed == split], dtype=int)
            for split in SPLITS
        }


def _validate_numeric_cube(
    value: object,
    *,
    label: str,
    expected_shape: tuple[int, int, int],
) -> np.ndarray:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a nested list")
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only numeric values") from exc
    if array.shape != expected_shape:
        raise ValueError(f"{label} shape mismatch")
    if not np.isfinite(array).all():
        raise ValueError(f"{label} contains non-finite data")
    return array


def validate_dataset(
    value: Mapping[str, object], preregistration: Mapping[str, object]
) -> DatasetView:
    _assert_finite_json(value, "dataset")
    config = validate_preregistration(preregistration)
    dataset = _require_exact_keys(
        value,
        {
            "schema_version",
            "artifact_kind",
            "status",
            "preregistration_sha256",
            "capture_contract",
            "label_contract",
            "feature_records",
            "event_labels",
            "registration",
            "claim_boundary",
            "dataset_sha256",
        },
        "dataset",
    )
    _require_literal(dataset, "schema_version", DATASET_SCHEMA, "dataset")
    _require_literal(dataset, "artifact_kind", ARTIFACT_KIND, "dataset")
    _require_literal(dataset, "status", DATASET_STATUS, "dataset")
    _require_literal(dataset, "claim_boundary", DATASET_CLAIM_BOUNDARY, "dataset")
    _verify_self_hash(dataset, "dataset_sha256", "dataset")
    if dataset["preregistration_sha256"] != config["config_sha256"]:
        raise ValueError("dataset preregistration hash mismatch; threshold/config drift detected")

    capture = _require_exact_keys(
        dataset["capture_contract"],
        {"residual", "mlp", "steps", "layers", "hidden_width", "numeric_encoding"},
        "dataset.capture_contract",
    )
    _require_literal(
        capture, "residual", "SYNTHETIC_FULL_WIDTH_EVERY_STEP_EVERY_LAYER", "dataset.capture_contract"
    )
    _require_literal(
        capture, "mlp", "SYNTHETIC_FULL_WIDTH_EVERY_STEP_EVERY_LAYER", "dataset.capture_contract"
    )
    _require_literal(
        capture,
        "numeric_encoding",
        "CANONICAL_JSON_FINITE_NUMBERS_INTERPRETED_AS_FLOAT64",
        "dataset.capture_contract",
    )
    steps = _require_int(capture["steps"], "dataset.capture_contract.steps", minimum=3, maximum=128)
    layers = _require_int(capture["layers"], "dataset.capture_contract.layers", minimum=1, maximum=256)
    hidden = _require_int(
        capture["hidden_width"], "dataset.capture_contract.hidden_width", minimum=1, maximum=65536
    )
    if layers != len(config["candidate_layers"]):
        raise ValueError("dataset layer count does not match preregistered candidate layers")
    if steps <= int(config["windows"]["k"]):
        raise ValueError("dataset has too few steps for preregistered Wk")

    label_contract = _require_exact_keys(
        dataset["label_contract"],
        {"task", "values", "source", "assignment_stage", "feature_table_contains_labels"},
        "dataset.label_contract",
    )
    _require_literal(label_contract, "task", "BINARY_REASONING_BREAK_EVENT", "dataset.label_contract")
    _require_literal(label_contract, "values", {"0": "NO_BREAK", "1": "BREAK"}, "dataset.label_contract")
    _require_literal(label_contract, "source", LABEL_SOURCE, "dataset.label_contract")
    _require_literal(label_contract, "assignment_stage", LABEL_STAGE, "dataset.label_contract")
    _require_literal(label_contract, "feature_table_contains_labels", False, "dataset.label_contract")

    features = dataset["feature_records"]
    labels = dataset["event_labels"]
    if not isinstance(features, list) or not 12 <= len(features) <= 10000:
        raise ValueError("dataset.feature_records count is outside [12, 10000]")
    if not isinstance(labels, list) or len(labels) != len(features):
        raise ValueError("event label count must equal feature record count")

    feature_by_record: dict[str, Mapping[str, Any]] = {}
    seen_events: set[str] = set()
    seen_captures: set[str] = set()
    residual_rows: list[np.ndarray] = []
    mlp_rows: list[np.ndarray] = []
    for index, raw_feature in enumerate(features):
        feature = _require_exact_keys(
            raw_feature,
            {
                "record_id",
                "event_id",
                "group_id",
                "split",
                "surface_text",
                "capture_id",
                "trajectory",
                "capture_sha256",
            },
            f"dataset.feature_records[{index}]",
        )
        record_id = _require_id(feature["record_id"], f"feature[{index}].record_id")
        event_id = _require_id(feature["event_id"], f"feature[{index}].event_id")
        _require_id(feature["group_id"], f"feature[{index}].group_id")
        capture_id = _require_id(feature["capture_id"], f"feature[{index}].capture_id")
        if record_id.casefold() in feature_by_record:
            raise ValueError("duplicate record IDs are forbidden")
        if event_id.casefold() in seen_events:
            raise ValueError("duplicate feature event IDs are forbidden")
        if capture_id.casefold() in seen_captures:
            raise ValueError("duplicate capture IDs are forbidden")
        feature_by_record[record_id.casefold()] = feature
        seen_events.add(event_id.casefold())
        seen_captures.add(capture_id.casefold())
        if feature["split"] not in SPLITS:
            raise ValueError("feature split is not train/validation/test")
        surface_text = feature["surface_text"]
        if not isinstance(surface_text, str) or not surface_text or len(surface_text) > 4096:
            raise ValueError("surface_text must be non-empty bounded text")
        trajectory = _require_exact_keys(
            feature["trajectory"], {"residual_states", "mlp_states"}, f"feature[{index}].trajectory"
        )
        expected_shape = (steps, layers, hidden)
        residual_rows.append(
            _validate_numeric_cube(
                trajectory["residual_states"],
                label=f"feature[{index}].trajectory.residual_states",
                expected_shape=expected_shape,
            )
        )
        mlp_rows.append(
            _validate_numeric_cube(
                trajectory["mlp_states"],
                label=f"feature[{index}].trajectory.mlp_states",
                expected_shape=expected_shape,
            )
        )
        _require_sha256(feature["capture_sha256"], f"feature[{index}].capture_sha256")
        if feature["capture_sha256"] != _capture_sha256(feature):
            raise ValueError("capture hash mismatch")

    label_by_record: dict[str, Mapping[str, Any]] = {}
    label_event_ids: set[str] = set()
    for index, raw_label in enumerate(labels):
        label = _require_exact_keys(
            raw_label,
            {
                "event_id",
                "record_id",
                "group_id",
                "split",
                "break_label",
                "annotation_source",
                "label_assignment_stage",
                "annotated_without_trajectory_access",
                "label_sha256",
            },
            f"dataset.event_labels[{index}]",
        )
        record_id = _require_id(label["record_id"], f"label[{index}].record_id")
        event_id = _require_id(label["event_id"], f"label[{index}].event_id")
        _require_id(label["group_id"], f"label[{index}].group_id")
        if record_id.casefold() in label_by_record:
            raise ValueError("duplicate label record IDs are forbidden")
        if event_id.casefold() in label_event_ids:
            raise ValueError("duplicate label event IDs are forbidden")
        label_by_record[record_id.casefold()] = label
        label_event_ids.add(event_id.casefold())
        if label["split"] not in SPLITS:
            raise ValueError("label split is not train/validation/test")
        if isinstance(label["break_label"], bool) or label["break_label"] not in (0, 1):
            raise ValueError("break_label must be integer 0 or 1")
        _require_literal(label, "annotation_source", LABEL_SOURCE, f"label[{index}]")
        _require_literal(label, "label_assignment_stage", LABEL_STAGE, f"label[{index}]")
        _require_literal(label, "annotated_without_trajectory_access", True, f"label[{index}]")
        _require_sha256(label["label_sha256"], f"label[{index}].label_sha256")
        if label["label_sha256"] != _label_sha256(label):
            raise ValueError("event label hash mismatch")

    if set(feature_by_record) != set(label_by_record):
        raise ValueError("label/feature record IDs do not match")
    ordered_labels: list[int] = []
    record_ids: list[str] = []
    event_ids: list[str] = []
    group_ids: list[str] = []
    split_values: list[str] = []
    surface_texts: list[str] = []
    group_split: dict[str, str] = {}
    for feature in features:
        record_id = str(feature["record_id"])
        label = label_by_record[record_id.casefold()]
        for key in ("record_id", "event_id", "group_id", "split"):
            if feature[key] != label[key]:
                raise ValueError(f"label/feature mismatch for {key}")
        group = str(feature["group_id"])
        split = str(feature["split"])
        previous = group_split.setdefault(group.casefold(), split)
        if previous != split:
            raise ValueError("group leakage detected across train/validation/test")
        record_ids.append(record_id)
        event_ids.append(str(feature["event_id"]))
        group_ids.append(group)
        split_values.append(split)
        surface_texts.append(str(feature["surface_text"]))
        ordered_labels.append(int(label["break_label"]))

    label_array = np.asarray(ordered_labels, dtype=np.int64)
    if set(label_array.tolist()) != {0, 1}:
        raise ValueError("all-one-class labels are forbidden")
    group_array = np.asarray(group_ids, dtype=str)
    split_array = np.asarray(split_values, dtype=str)
    for split in SPLITS:
        indices = np.flatnonzero(split_array == split)
        if len(indices) < 4 or set(label_array[indices].tolist()) != {0, 1}:
            raise ValueError(f"split {split} must contain both label classes")
        split_groups = set(group_array[indices].tolist())
        if len(split_groups) < 2:
            raise ValueError(f"split {split} must contain at least two groups")

    registration = _require_exact_keys(
        dataset["registration"],
        {"tree_algorithm", "feature_table_sha256", "label_table_sha256", "tree_sha256"},
        "dataset.registration",
    )
    _require_literal(registration, "tree_algorithm", TREE_ALGORITHM, "dataset.registration")
    for key in ("feature_table_sha256", "label_table_sha256", "tree_sha256"):
        _require_sha256(registration[key], f"dataset.registration.{key}")
    if registration["feature_table_sha256"] != sha256_bytes(canonical_json_bytes(features)):
        raise ValueError("feature table hash mismatch")
    if registration["label_table_sha256"] != sha256_bytes(canonical_json_bytes(labels)):
        raise ValueError("label table hash mismatch")
    _leaves, observed_tree = _dataset_tree(features, labels)
    if registration["tree_sha256"] != observed_tree:
        raise ValueError("input tree hash mismatch")

    return DatasetView(
        record_ids=record_ids,
        event_ids=event_ids,
        group_ids=group_array,
        splits=split_array,
        surface_texts=surface_texts,
        residual=np.stack(residual_rows),
        mlp=np.stack(mlp_rows),
        labels=label_array,
    )


def temporal_features(view: DatasetView, *, window: str, layer: int, k: int) -> np.ndarray:
    state = np.concatenate((view.residual[:, :, layer, :], view.mlp[:, :, layer, :]), axis=2)
    current = state[:, -1, :]
    if window == "W0":
        result = current
    elif window == "W1":
        result = np.concatenate((current, current - state[:, -2, :]), axis=1)
    elif window == "Wk":
        segment = state[:, -(k + 1) :, :]
        velocities = np.diff(segment, axis=1)
        result = np.concatenate(
            (
                current,
                current - segment[:, 0, :],
                velocities.mean(axis=1),
                np.sqrt(np.mean(np.square(velocities), axis=1)),
            ),
            axis=1,
        )
    else:
        raise ValueError("unknown temporal window")
    if not np.isfinite(result).all():
        raise ValueError("derived temporal features contain non-finite data")
    return result.astype(np.float64, copy=False)


def _fit_probe(X: np.ndarray, y: np.ndarray, config: Mapping[str, object], *, seed: int):
    if set(np.asarray(y).tolist()) != {0, 1}:
        raise ValueError("probe training requires both classes")
    probe = config["probe"]
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=float(probe["C"]),
            max_iter=int(probe["max_iter"]),
            class_weight="balanced",
            solver="lbfgs",
            random_state=seed,
        ),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(X, y)
    return model


def _fit_calibrator(scores: np.ndarray, y: np.ndarray, config: Mapping[str, object], *, seed: int):
    if set(np.asarray(y).tolist()) != {0, 1}:
        raise ValueError("calibration requires both classes")
    calibration = config["calibration"]
    model = LogisticRegression(
        C=float(calibration["C"]),
        max_iter=int(calibration["max_iter"]),
        solver="lbfgs",
        random_state=seed,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(np.asarray(scores, dtype=np.float64).reshape(-1, 1), y)
    return model


def _calibrated_risk(calibrator: Any, scores: np.ndarray) -> np.ndarray:
    risks = calibrator.predict_proba(np.asarray(scores, dtype=np.float64).reshape(-1, 1))[:, 1]
    if not np.isfinite(risks).all() or (risks < 0).any() or (risks > 1).any():
        raise RuntimeError("calibrator produced invalid risk values")
    return risks


def _ece(risks: np.ndarray, labels: np.ndarray, bins: int) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(labels)
    result = 0.0
    for index in range(bins):
        lower, upper = edges[index], edges[index + 1]
        mask = (risks >= lower) & ((risks < upper) if index < bins - 1 else (risks <= upper))
        if mask.any():
            result += float(mask.sum()) / total * abs(float(risks[mask].mean()) - float(labels[mask].mean()))
    return float(result)


def _decision_metrics(
    risks: np.ndarray,
    labels: np.ndarray,
    thresholds: Mapping[str, object],
    *,
    ece_bins: int,
) -> dict[str, object]:
    clear = float(thresholds["clear_max_risk"])
    alert = float(thresholds["alert_min_risk"])
    decisions = np.full(len(risks), -1, dtype=np.int64)
    decisions[risks <= clear] = 0
    decisions[risks >= alert] = 1
    decided = decisions >= 0
    ordinary_predictions = (risks >= 0.5).astype(np.int64)
    balanced = float(balanced_accuracy_score(labels, ordinary_predictions))
    coverage = float(decided.mean())
    if decided.any() and set(labels[decided].tolist()) == {0, 1}:
        selective_balanced = float(balanced_accuracy_score(labels[decided], decisions[decided]))
        selective_accuracy = float((labels[decided] == decisions[decided]).mean())
    else:
        selective_balanced = 0.0
        selective_accuracy = 0.0
    return {
        "balanced_accuracy": balanced,
        "brier": float(brier_score_loss(labels, risks)),
        "ece": _ece(risks, labels, ece_bins),
        "coverage": coverage,
        "abstention_rate": 1.0 - coverage,
        "selective_balanced_accuracy": selective_balanced,
        "selective_accuracy": selective_accuracy,
        "decision_counts": {
            "CLEAR": int((decisions == 0).sum()),
            "ALERT": int((decisions == 1).sum()),
            "ABSTAIN": int((decisions == -1).sum()),
        },
    }


CANDIDATE_ROW_KEYS = {
    "window",
    "layer",
    "validation_brier",
    "validation_ece",
    "validation_balanced_accuracy",
    "validation_coverage",
    "validation_selective_balanced_accuracy",
}


def select_candidate_on_validation(
    rows: Sequence[Mapping[str, object]], *, window_order: Sequence[str]
) -> Mapping[str, object]:
    """Select from validation-only rows; any test field is a hard error."""

    if not rows:
        raise ValueError("candidate selection requires at least one row")
    order = {name: index for index, name in enumerate(window_order)}
    for row in rows:
        if set(row) != CANDIDATE_ROW_KEYS or any("test" in key.casefold() for key in row):
            raise ValueError("candidate selection rows must contain validation metrics only; test peeking rejected")
        if row["window"] not in order:
            raise ValueError("candidate row has an unregistered temporal window")
    return min(
        rows,
        key=lambda row: (
            float(row["validation_brier"]),
            -float(row["validation_selective_balanced_accuracy"]),
            order[str(row["window"])],
            int(row["layer"]),
        ),
    )


class TestPartitionGuard:
    """Make the no-test-before-freeze invariant executable."""

    def __init__(self, indices: np.ndarray) -> None:
        self._indices = np.asarray(indices, dtype=int).copy()
        self._freeze_sha256: str | None = None
        self.reads_before_freeze = 0
        self.reads_after_freeze = 0

    def freeze(self, freeze_sha256: str) -> None:
        _require_sha256(freeze_sha256, "freeze_sha256")
        if self._freeze_sha256 is not None:
            raise RuntimeError("test partition is already frozen")
        self._freeze_sha256 = freeze_sha256

    def read(self, freeze_sha256: str) -> np.ndarray:
        if self._freeze_sha256 is None:
            self.reads_before_freeze += 1
            raise RuntimeError("test access before decision freeze is forbidden")
        if freeze_sha256 != self._freeze_sha256:
            raise RuntimeError("test access freeze hash mismatch")
        self.reads_after_freeze += 1
        return self._indices.copy()


def _fit_candidates(
    feature_matrices: Mapping[tuple[str, int], np.ndarray],
    labels: np.ndarray,
    train_idx: np.ndarray,
    validation_idx: np.ndarray,
    config: Mapping[str, object],
    *,
    seed_offset: int = 0,
) -> tuple[list[dict[str, object]], dict[tuple[str, int], tuple[Any, Any]]]:
    rows: list[dict[str, object]] = []
    fitted: dict[tuple[str, int], tuple[Any, Any]] = {}
    thresholds = config["decision"]["thresholds"]
    ece_bins = int(config["calibration"]["ece_bins"])
    seed = int(config["seed"]) + seed_offset
    for window in config["windows"]["order"]:
        for layer in config["candidate_layers"]:
            key = (str(window), int(layer))
            X = feature_matrices[key]
            model = _fit_probe(X[train_idx], labels[train_idx], config, seed=seed)
            validation_scores = model.decision_function(X[validation_idx])
            calibrator = _fit_calibrator(
                validation_scores,
                labels[validation_idx],
                config,
                seed=seed + 1,
            )
            risks = _calibrated_risk(calibrator, validation_scores)
            metrics = _decision_metrics(
                risks, labels[validation_idx], thresholds, ece_bins=ece_bins
            )
            rows.append(
                {
                    "window": key[0],
                    "layer": key[1],
                    "validation_brier": metrics["brier"],
                    "validation_ece": metrics["ece"],
                    "validation_balanced_accuracy": metrics["balanced_accuracy"],
                    "validation_coverage": metrics["coverage"],
                    "validation_selective_balanced_accuracy": metrics[
                        "selective_balanced_accuracy"
                    ],
                }
            )
            fitted[key] = (model, calibrator)
    return rows, fitted


def _permute_group_labels(
    labels: np.ndarray,
    groups: np.ndarray,
    split_indices: Sequence[np.ndarray],
    rng: np.random.Generator,
) -> np.ndarray:
    result = labels.copy()
    for indices in split_indices:
        positions: dict[str, list[int]] = {}
        for index in indices.tolist():
            positions.setdefault(str(groups[index]), []).append(int(index))
        by_size: dict[int, list[str]] = {}
        for group, group_positions in positions.items():
            by_size.setdefault(len(group_positions), []).append(group)
        for size, compatible in sorted(by_size.items()):
            ordered = sorted(compatible)
            vectors = [tuple(int(labels[index]) for index in positions[group]) for group in ordered]
            permutation = rng.permutation(len(ordered)).tolist()
            if len(ordered) > 1 and permutation == list(range(len(ordered))):
                permutation = permutation[1:] + permutation[:1]
            for target, source_index in zip(ordered, permutation, strict=True):
                source = vectors[int(source_index)]
                if len(source) != size:
                    raise RuntimeError("group-label permutation changed vector size")
                for index, label in zip(positions[target], source, strict=True):
                    result[index] = label
    return result


def _surface_baseline(
    view: DatasetView,
    train_idx: np.ndarray,
    validation_idx: np.ndarray,
    test_idx: np.ndarray,
    config: Mapping[str, object],
) -> dict[str, object]:
    n_features = int(config["surface_baseline"]["n_features"])
    vectorizer = HashingVectorizer(
        n_features=n_features,
        analyzer="char",
        ngram_range=(1, 2),
        alternate_sign=False,
        norm=None,
        lowercase=True,
    )
    train_X = vectorizer.transform([view.surface_texts[index] for index in train_idx])
    validation_X = vectorizer.transform([view.surface_texts[index] for index in validation_idx])
    test_X = vectorizer.transform([view.surface_texts[index] for index in test_idx])
    probe_cfg = config["probe"]
    model = LogisticRegression(
        C=float(probe_cfg["C"]),
        max_iter=int(probe_cfg["max_iter"]),
        class_weight="balanced",
        solver="lbfgs",
        random_state=int(config["seed"]),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(train_X, view.labels[train_idx])
    validation_scores = model.decision_function(validation_X)
    calibrator = _fit_calibrator(
        validation_scores,
        view.labels[validation_idx],
        config,
        seed=int(config["seed"]) + 17,
    )
    validation_risks = _calibrated_risk(calibrator, validation_scores)
    test_risks = _calibrated_risk(calibrator, model.decision_function(test_X))
    thresholds = config["decision"]["thresholds"]
    bins = int(config["calibration"]["ece_bins"])
    return {
        "method": config["surface_baseline"]["method"],
        "feature_source": "surface_text_only_no_trajectory_values",
        "validation": _decision_metrics(
            validation_risks, view.labels[validation_idx], thresholds, ece_bins=bins
        ),
        "test": _decision_metrics(test_risks, view.labels[test_idx], thresholds, ece_bins=bins),
    }


def _negative_control(
    feature_matrices: Mapping[tuple[str, int], np.ndarray],
    view: DatasetView,
    train_idx: np.ndarray,
    validation_idx: np.ndarray,
    test_idx: np.ndarray,
    config: Mapping[str, object],
) -> dict[str, object]:
    trials = int(config["negative_control"]["trials"])
    rng = np.random.default_rng(int(config["seed"]) + 9001)
    trial_rows: list[dict[str, object]] = []
    for trial in range(trials):
        shuffled = _permute_group_labels(
            view.labels,
            view.group_ids,
            (train_idx, validation_idx, test_idx),
            rng,
        )
        rows, fitted = _fit_candidates(
            feature_matrices,
            shuffled,
            train_idx,
            validation_idx,
            config,
            seed_offset=1000 + trial * 10,
        )
        selected = select_candidate_on_validation(
            rows, window_order=config["windows"]["order"]
        )
        key = (str(selected["window"]), int(selected["layer"]))
        freeze = sha256_bytes(
            canonical_json_bytes(
                {
                    "trial": trial,
                    "selected": dict(selected),
                    "thresholds": config["decision"]["thresholds"],
                }
            )
        )
        guard = TestPartitionGuard(test_idx)
        guard.freeze(freeze)
        guarded_test = guard.read(freeze)
        model, calibrator = fitted[key]
        scores = model.decision_function(feature_matrices[key][guarded_test])
        risks = _calibrated_risk(calibrator, scores)
        metrics = _decision_metrics(
            risks,
            shuffled[guarded_test],
            config["decision"]["thresholds"],
            ece_bins=int(config["calibration"]["ece_bins"]),
        )
        trial_rows.append(
            {
                "trial": trial + 1,
                "selected_window": key[0],
                "selected_layer": key[1],
                "test_balanced_accuracy": metrics["balanced_accuracy"],
                "test_coverage": metrics["coverage"],
                "test_selective_balanced_accuracy": metrics[
                    "selective_balanced_accuracy"
                ],
            }
        )
    scores = [float(row["test_balanced_accuracy"]) for row in trial_rows]
    return {
        "method": config["negative_control"]["method"],
        "selection_aware": True,
        "group_vectors_permuted_without_crossing_splits": True,
        "trials": trial_rows,
        "mean_test_balanced_accuracy": float(np.mean(scores)),
        "max_test_balanced_accuracy": float(np.max(scores)),
    }


def _gate_rows(
    config: Mapping[str, object],
    selected: Mapping[str, object],
    hidden_test: Mapping[str, object],
    surface: Mapping[str, object],
    shuffled: Mapping[str, object],
) -> tuple[list[dict[str, object]], str]:
    gates = config["decision"]["gates"]
    observed = {
        "min_test_coverage": float(hidden_test["coverage"]),
        "min_test_selective_balanced_accuracy": float(
            hidden_test["selective_balanced_accuracy"]
        ),
        "max_validation_ece": float(selected["validation_ece"]),
        "min_hidden_minus_surface_balanced_accuracy": float(
            hidden_test["balanced_accuracy"] - surface["test"]["balanced_accuracy"]
        ),
        "min_hidden_minus_shuffled_max_balanced_accuracy": float(
            hidden_test["balanced_accuracy"]
            - shuffled["max_test_balanced_accuracy"]
        ),
    }
    rows: list[dict[str, object]] = []
    for name in sorted(gates):
        threshold = float(gates[name])
        direction = "MAX" if name.startswith("max_") else "MIN"
        passed = observed[name] <= threshold if direction == "MAX" else observed[name] >= threshold
        rows.append(
            {
                "gate": name,
                "direction": direction,
                "preregistered_threshold": threshold,
                "observed": observed[name],
                "passed": bool(passed),
            }
        )
    status = "PASS_SYNTHETIC_ENGINEERING_GATES" if all(row["passed"] for row in rows) else "FAIL_SYNTHETIC_ENGINEERING_GATES"
    return rows, status


def run_pipeline(
    dataset: Mapping[str, object],
    preregistration: Mapping[str, object],
    *,
    input_raw: bytes | None = None,
    config_raw: bytes | None = None,
    code_path: Path | None = None,
) -> dict[str, object]:
    """Run the deterministic offline pipeline and return a self-hashed result."""

    config = validate_preregistration(preregistration)
    view = validate_dataset(dataset, config)
    canonical_input = canonical_json_bytes(dataset)
    canonical_config = canonical_json_bytes(config)
    if input_raw is None:
        input_raw = canonical_input
    if config_raw is None:
        config_raw = canonical_config
    if input_raw != canonical_input or config_raw != canonical_config:
        raise ValueError("pipeline inputs must be the exact canonical snapshots parsed in memory")
    source_path = (code_path or Path(__file__)).resolve()
    source_raw = source_path.read_bytes()
    if not source_raw:
        raise ValueError("pipeline source file is empty")

    train_idx = view.indices["train"]
    validation_idx = view.indices["validation"]
    test_guard = TestPartitionGuard(view.indices["test"])
    k = int(config["windows"]["k"])
    feature_matrices = {
        (str(window), int(layer)): temporal_features(
            view, window=str(window), layer=int(layer), k=k
        )
        for window in config["windows"]["order"]
        for layer in config["candidate_layers"]
    }
    candidate_rows, fitted = _fit_candidates(
        feature_matrices, view.labels, train_idx, validation_idx, config
    )
    selected = select_candidate_on_validation(
        candidate_rows, window_order=config["windows"]["order"]
    )
    selected_key = (str(selected["window"]), int(selected["layer"]))
    freeze_payload = {
        "selection_rule": config["selection_rule"],
        "selected_window": selected_key[0],
        "selected_layer": selected_key[1],
        "calibration_method": config["calibration"]["method"],
        "thresholds": config["decision"]["thresholds"],
        "config_sha256": config["config_sha256"],
    }
    freeze_sha256 = sha256_bytes(canonical_json_bytes(freeze_payload))
    test_guard.freeze(freeze_sha256)
    test_idx = test_guard.read(freeze_sha256)

    model, calibrator = fitted[selected_key]
    test_scores = model.decision_function(feature_matrices[selected_key][test_idx])
    test_risks = _calibrated_risk(calibrator, test_scores)
    hidden_test = _decision_metrics(
        test_risks,
        view.labels[test_idx],
        config["decision"]["thresholds"],
        ece_bins=int(config["calibration"]["ece_bins"]),
    )
    thresholds = config["decision"]["thresholds"]
    predictions = []
    for index, risk in zip(test_idx.tolist(), test_risks.tolist(), strict=True):
        decision = (
            "CLEAR"
            if risk <= float(thresholds["clear_max_risk"])
            else "ALERT"
            if risk >= float(thresholds["alert_min_risk"])
            else "ABSTAIN"
        )
        predictions.append(
            {
                "record_id": view.record_ids[index],
                "event_id": view.event_ids[index],
                "calibrated_break_risk": float(risk),
                "decision": decision,
            }
        )

    surface = _surface_baseline(view, train_idx, validation_idx, test_idx, config)
    shuffled = _negative_control(
        feature_matrices, view, train_idx, validation_idx, test_idx, config
    )
    gate_rows, gate_status = _gate_rows(
        config, selected, hidden_test, surface, shuffled
    )
    group_sets = {
        split: sorted(set(view.group_ids[view.indices[split]].tolist())) for split in SPLITS
    }
    group_set_hashes = {
        split: sha256_bytes(canonical_json_bytes(groups))
        for split, groups in group_sets.items()
    }
    result_unsigned: dict[str, object] = {
        "schema_version": RESULT_SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": RESULT_STATUS,
        "packet_eligibility": PACKET_ELIGIBILITY,
        "real_model_verification": REAL_MODEL_VERIFICATION,
        "scientific_status": SCIENTIFIC_STATUS,
        "provenance": {
            "input_artifact": {
                "schema_version": DATASET_SCHEMA,
                "raw_sha256": sha256_bytes(input_raw),
                "byte_count": len(input_raw),
                "self_hash_sha256": dataset["dataset_sha256"],
                "tree_sha256": dataset["registration"]["tree_sha256"],
            },
            "configuration": {
                "schema_version": CONFIG_SCHEMA,
                "raw_sha256": sha256_bytes(config_raw),
                "byte_count": len(config_raw),
                "self_hash_sha256": config["config_sha256"],
            },
            "code": {
                "artifact_name": source_path.name,
                "sha256": sha256_bytes(source_raw),
                "byte_count": len(source_raw),
                "python_version": sys.version.split()[0],
                "numpy_version": np.__version__,
                "scikit_learn_version": sklearn.__version__,
            },
        },
        "data_contract": {
            "artifact_kind": ARTIFACT_KIND,
            "capture_contract": deepcopy(dataset["capture_contract"]),
            "label_contract": deepcopy(dataset["label_contract"]),
            "record_count": len(view.record_ids),
            "class_distribution": {
                "NO_BREAK": int((view.labels == 0).sum()),
                "BREAK": int((view.labels == 1).sum()),
            },
        },
        "split_audit": {
            "method": "REGISTERED_GROUP_OWNED_SPLITS",
            "group_disjoint": True,
            "counts": {split: int(len(view.indices[split])) for split in SPLITS},
            "group_counts": {split: len(group_sets[split]) for split in SPLITS},
            "group_set_sha256": group_set_hashes,
        },
        "feature_contract": {
            "temporal_windows": deepcopy(config["windows"]),
            "candidate_layers": deepcopy(config["candidate_layers"]),
            "feature_dimensions": {
                f"{window}:layer:{layer}": int(matrix.shape[1])
                for (window, layer), matrix in sorted(feature_matrices.items())
            },
        },
        "selection": {
            "rule": SELECTION_RULE,
            "candidates_validation_only": candidate_rows,
            "selected": dict(selected),
            "frozen_decision": freeze_payload,
            "freeze_sha256": freeze_sha256,
            "test_access_audit": {
                "policy": TEST_POLICY,
                "reads_before_freeze": test_guard.reads_before_freeze,
                "reads_after_freeze": test_guard.reads_after_freeze,
            },
        },
        "calibration": {
            "method": config["calibration"]["method"],
            "fit_partition": "validation",
            "threshold_source": "preregistration_exact_no_runtime_override",
            "thresholds": deepcopy(config["decision"]["thresholds"]),
            "selected_validation_brier": selected["validation_brier"],
            "selected_validation_ece": selected["validation_ece"],
        },
        "hidden_detector": {
            "selected_window": selected_key[0],
            "selected_layer": selected_key[1],
            "test_metrics": hidden_test,
            "test_predictions": predictions,
        },
        "controls": {
            "surface_only": surface,
            "shuffled_labels": shuffled,
        },
        "preregistered_decision_gates": {
            "status": gate_status,
            "scope": "SYNTHETIC_ENGINEERING_ONLY",
            "gates": gate_rows,
        },
        "boundaries": {
            "packet_eligibility": PACKET_ELIGIBILITY,
            "real_model_verification": REAL_MODEL_VERIFICATION,
            "scientific_status": SCIENTIFIC_STATUS,
            "claim_boundary": RESULT_CLAIM_BOUNDARY,
        },
    }
    return self_hash(result_unsigned, "result_sha256")


def verify_result(
    result: Mapping[str, object],
    dataset: Mapping[str, object],
    preregistration: Mapping[str, object],
    *,
    input_raw: bytes | None = None,
    config_raw: bytes | None = None,
    code_path: Path | None = None,
) -> dict[str, object]:
    """Fully recompute the deterministic result and reject any semantic drift."""

    _assert_finite_json(result, "result")
    expected_keys = {
        "schema_version",
        "capability_id",
        "status",
        "packet_eligibility",
        "real_model_verification",
        "scientific_status",
        "provenance",
        "data_contract",
        "split_audit",
        "feature_contract",
        "selection",
        "calibration",
        "hidden_detector",
        "controls",
        "preregistered_decision_gates",
        "boundaries",
        "result_sha256",
    }
    checked = _require_exact_keys(result, expected_keys, "result")
    _require_literal(checked, "schema_version", RESULT_SCHEMA, "result")
    _require_literal(checked, "capability_id", CAPABILITY_ID, "result")
    _require_literal(checked, "status", RESULT_STATUS, "result")
    _require_literal(checked, "packet_eligibility", PACKET_ELIGIBILITY, "result")
    _require_literal(
        checked, "real_model_verification", REAL_MODEL_VERIFICATION, "result"
    )
    _require_literal(checked, "scientific_status", SCIENTIFIC_STATUS, "result")
    _verify_self_hash(checked, "result_sha256", "result")
    config = validate_preregistration(preregistration)
    calibration = _require_exact_keys(
        checked["calibration"],
        {
            "method",
            "fit_partition",
            "threshold_source",
            "thresholds",
            "selected_validation_brier",
            "selected_validation_ece",
        },
        "result.calibration",
    )
    if calibration["thresholds"] != config["decision"]["thresholds"]:
        raise ValueError("result threshold drift from preregistration")
    selection = _require_exact_keys(
        checked["selection"],
        {
            "rule",
            "candidates_validation_only",
            "selected",
            "frozen_decision",
            "freeze_sha256",
            "test_access_audit",
        },
        "result.selection",
    )
    selected = select_candidate_on_validation(
        selection["candidates_validation_only"],
        window_order=config["windows"]["order"],
    )
    if dict(selected) != selection["selected"]:
        raise ValueError("result selected candidate differs from validation-only rule")
    if selection["frozen_decision"].get("thresholds") != config["decision"]["thresholds"]:
        raise ValueError("frozen decision threshold drift from preregistration")
    expected = run_pipeline(
        dataset,
        config,
        input_raw=input_raw,
        config_raw=config_raw,
        code_path=code_path,
    )
    if canonical_json_bytes(checked) != canonical_json_bytes(expected):
        raise ValueError("result does not equal a full deterministic recomputation")
    return deepcopy(dict(checked))


def _write_create_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()


def _absolute_path(raw: str, label: str) -> Path:
    path = Path(raw).resolve()
    if not path.is_absolute():
        raise ValueError(f"{label} must resolve to an absolute path")
    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    emit = subparsers.add_parser("emit-synthetic", help="create the strict synthetic input pair")
    emit.add_argument("--directory", required=True)
    evaluate = subparsers.add_parser("evaluate", help="run the offline C13 evaluation")
    evaluate.add_argument("--config", required=True)
    evaluate.add_argument("--dataset", required=True)
    evaluate.add_argument("--output", required=True)
    verify = subparsers.add_parser("verify", help="recompute and verify one result")
    verify.add_argument("--config", required=True)
    verify.add_argument("--dataset", required=True)
    verify.add_argument("--result", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "emit-synthetic":
        directory = _absolute_path(args.directory, "directory")
        config_path = directory / "c13.preregistration.json"
        dataset_path = directory / "c13.synthetic-dataset.json"
        if config_path.exists() or dataset_path.exists():
            raise FileExistsError("synthetic output paths must both be absent")
        config = build_default_preregistration()
        dataset = build_canonical_synthetic_fixture(config)
        _write_create_new(config_path, canonical_json_bytes(config))
        _write_create_new(dataset_path, canonical_json_bytes(dataset))
        print(f"wrote {config_path}")
        print(f"wrote {dataset_path}")
        return 0
    config_path = _absolute_path(args.config, "config")
    dataset_path = _absolute_path(args.dataset, "dataset")
    config, config_raw = read_canonical_snapshot(
        config_path, label="preregistration", max_bytes=1024 * 1024
    )
    dataset, input_raw = read_canonical_snapshot(
        dataset_path, label="dataset", max_bytes=256 * 1024 * 1024
    )
    if args.command == "evaluate":
        output_path = _absolute_path(args.output, "output")
        result = run_pipeline(
            dataset,
            config,
            input_raw=input_raw,
            config_raw=config_raw,
        )
        _write_create_new(output_path, canonical_json_bytes(result))
        print(result["result_sha256"])
        return 0
    result_path = _absolute_path(args.result, "result")
    result, _result_raw = read_canonical_snapshot(
        result_path, label="result", max_bytes=64 * 1024 * 1024
    )
    verified = verify_result(
        result,
        dataset,
        config,
        input_raw=input_raw,
        config_raw=config_raw,
    )
    print(verified["result_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
