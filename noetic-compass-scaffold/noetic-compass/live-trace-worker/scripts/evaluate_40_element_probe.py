#!/usr/bin/env python3
r"""Evaluate the 40-Element (10 Noetics x 4 Domains) readout on a captured
open-weight probe dataset.

Replicates the Pythia-160M 40-Element closure target (89.8% readout, +39.7pp
over text baseline; CAS_HARNESS_SPEC_SHEET_v1_5_20260519) on a different
substrate, using only labels already present in the captured dataset.

The 40-Element label is constructed at runtime as `operator|domain` from the
existing `labels_operator` (10 Noetics: ^0..^9) and `labels_domain`
(4 Domains: P/C/E/O) arrays. No new capture is needed.

Usage on RunPod (canonical dataset location):

    python evaluate_40_element_probe.py \
      --dataset /workspace/cas-harness-large-eval/data/gpt_neox_20b_augmented_400_layers_0_43.npz \
      --metadata /workspace/cas-harness-large-eval/data/gpt_neox_20b_augmented_400_layers_0_43.metadata.json \
      --output /workspace/cas-harness-large-eval/results/gpt_neox_20b_40_element_probe_eval_report.json

Usage locally (against the archived copy):

    python evaluate_40_element_probe.py ^
      --dataset D:\tksCAS-archive\gpt_neox_20b_probe_dataset_eval_20260526\gpt_neox_20b_augmented_400_layers_0_43.npz ^
      --metadata D:\tksCAS-archive\gpt_neox_20b_probe_dataset_eval_20260526\gpt_neox_20b_augmented_400_layers_0_43.metadata.json ^
      --output .\gpt_neox_20b_40_element_probe_eval_report.json

Output schema matches the existing per-axis probe eval reports for direct
comparison: best_layer, per_layer, controls (majority, shuffled-label,
text-hash), populated cell count, and an explicit Pythia-160M comparator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


SCHEMA_VERSION = "cas_harness_40_element_probe_eval.v3"
EXPECTED_OPERATORS = tuple(f"^{i}" for i in range(10))
EXPECTED_DOMAINS = ("P", "C", "E", "O")
EXPECTED_40E_CELLS = tuple(
    f"{operator}|{domain}"
    for operator in EXPECTED_OPERATORS
    for domain in EXPECTED_DOMAINS
)
DEFAULT_MIN_SAMPLES_PER_CELL = 10
REGISTERED_STAGE9_DATASET_SHA256 = (
    "5f9a14714dcad87991a04a8317119b4eeb8097af7377446e59efb1c65f428610"
)
REGISTERED_STAGE9_SCENARIO_SHA256 = (
    "b2ad0481daaa1e5597a445a7ad8a9f2a4d108ead213818edd2ffb665af55b537"
)
REGISTERED_STAGE9_METADATA_SHA256 = (
    "22d5e6c19c4dd25d549e82bc2509282634878df465967df1d68f11d90accf6ef"
)
REGISTERED_STAGE9_MODEL_ID = "EleutherAI/gpt-neox-20b"
REQUIRED_NPZ_KEYS = (
    "features",
    "layers",
    "labels_domain",
    "labels_operator",
    "prompts",
    "scenario_ids",
)


def _strip_framing_tags(prompt: str) -> str:
    """Strip leading [bracket framing] tags so paraphrase siblings share a base."""
    s = str(prompt)
    while s.startswith("[") and "]" in s:
        s = s.split("]", 1)[1].lstrip()
    return s


def _cell_sort_key(cell: str) -> tuple[int, int, str]:
    operator, _, domain = cell.partition("|")
    try:
        operator_idx = int(operator.removeprefix("^"))
    except ValueError:
        operator_idx = 99
    try:
        domain_idx = EXPECTED_DOMAINS.index(domain)
    except ValueError:
        domain_idx = 99
    return operator_idx, domain_idx, cell


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def load_json_snapshot(
    path: Path,
    *,
    after_read_hook: Callable[[], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.read_bytes()
    if after_read_hook is not None:
        after_read_hook()
    payload = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=_reject_nonfinite_json,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload, {
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "snapshot_captured_at": datetime.now(UTC).isoformat(),
    }


def _artifact_descriptor(
    artifact_id: str,
    artifact_type: str,
    path: Path,
    *,
    content_sha256: str | None = None,
    byte_count: int | None = None,
    snapshot_captured_at: str | None = None,
    snapshot_semantics: str | None = None,
) -> dict:
    if content_sha256 is None or byte_count is None:
        raw = path.read_bytes()
        content_sha256 = hashlib.sha256(raw).hexdigest()
        byte_count = len(raw)
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "content_sha256": content_sha256,
        "byte_count": int(byte_count),
        "storage_uri": str(path),
        "redaction_class": "internal_eval_artifact",
        "snapshot_captured_at": snapshot_captured_at or datetime.now(UTC).isoformat(),
        "snapshot_semantics": snapshot_semantics or "bytes read once and hashed in memory",
    }


def _sha256_open_file(handle: Any) -> str:
    handle.seek(0)
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _file_identity(stat: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(stat.st_dev),
        int(stat.st_ino),
        int(stat.st_size),
        int(stat.st_mtime_ns),
        int(stat.st_ctime_ns),
    )


def _stable_descriptor_identity(stat: os.stat_result) -> tuple[int, int, int]:
    # Windows can report slightly different ctime precision through fstat and
    # Path.stat for the same descriptor. Device, inode/file-index, and size are
    # stable across those APIs and detect a swapped path here; the before/after
    # digest and same-handle full identity checks cover in-place mutation.
    return (int(stat.st_dev), int(stat.st_ino), int(stat.st_size))


def load_npz_without_pickle(
    path: Path,
    *,
    snapshot_out: dict[str, Any] | None = None,
    after_first_hash_hook: Callable[[], None] | None = None,
) -> dict[str, np.ndarray | None]:
    """Load the evaluator surface without permitting pickle execution.

    Historical NumPy object arrays require pickle and are not directly
    admissible. They must first be converted into a separately hashed NPZ whose
    text fields use fixed-width Unicode or byte dtypes. That conversion is an
    explicit evidence step, not a hidden ``allow_pickle=True`` exception here.
    """

    try:
        with path.open("rb") as handle:
            initial_stat = os.fstat(handle.fileno())
            initial_sha256 = _sha256_open_file(handle)
            if after_first_hash_hook is not None:
                after_first_hash_hook()
            handle.seek(0)
            with np.load(handle, allow_pickle=False) as archive:
                missing = set(REQUIRED_NPZ_KEYS) - set(archive.files)
                if missing:
                    raise ValueError(f"dataset missing required keys: {sorted(missing)}")
                arrays: dict[str, np.ndarray | None] = {}
                for key in REQUIRED_NPZ_KEYS:
                    try:
                        value = np.asarray(archive[key])
                    except ValueError as exc:
                        if key == "prompts":
                            # Never unpickle the historical object array. Exact
                            # prompts come from the independently hashed JSON
                            # snapshot after both registered hashes are checked.
                            arrays[key] = None
                            continue
                        raise ValueError(
                            f"dataset key {key!r} requires pickle/object loading; "
                            "convert it to a separately hashed fixed-width Unicode/byte "
                            "array before evaluation"
                        ) from exc
                    if value.dtype.hasobject:
                        raise ValueError(
                            f"dataset key {key!r} has object dtype; pickle-bearing arrays "
                            "are forbidden"
                        )
                    arrays[key] = value

            final_sha256 = _sha256_open_file(handle)
            final_stat = os.fstat(handle.fileno())
            current_path_stat = path.stat()
            if initial_sha256 != final_sha256:
                raise ValueError("activation dataset bytes changed during snapshot load")
            if _file_identity(initial_stat) != _file_identity(final_stat):
                raise ValueError("activation dataset file identity changed during load")
            if _stable_descriptor_identity(final_stat) != _stable_descriptor_identity(
                current_path_stat
            ):
                raise ValueError("activation dataset path was replaced during load")
            if snapshot_out is not None:
                snapshot_out.update(
                    {
                        "content_sha256": final_sha256,
                        "byte_count": int(final_stat.st_size),
                        "snapshot_captured_at": datetime.now(UTC).isoformat(),
                        "snapshot_semantics": (
                            "same open file handle hashed before and after all arrays "
                            "were materialized; descriptor/path identity unchanged"
                        ),
                    }
                )
            return arrays
    except OSError as exc:
        raise ValueError(f"could not safely load NPZ dataset {path}: {exc}") from exc


def build_40e_readiness_gate(
    class_distribution: dict[str, int],
    *,
    min_samples_per_cell: int = DEFAULT_MIN_SAMPLES_PER_CELL,
) -> dict:
    expected_cells = set(EXPECTED_40E_CELLS)
    observed_cells = set(class_distribution)
    missing_cells = sorted(expected_cells - observed_cells, key=_cell_sort_key)
    unexpected_cells = sorted(observed_cells - expected_cells, key=_cell_sort_key)
    sparse_cells = {
        cell: int(class_distribution[cell])
        for cell in sorted(expected_cells & observed_cells, key=_cell_sort_key)
        if int(class_distribution[cell]) < min_samples_per_cell
    }

    blocking_reasons: list[str] = []
    if missing_cells:
        blocking_reasons.append(f"{len(missing_cells)} expected 40E cells are absent")
    if sparse_cells:
        blocking_reasons.append(
            f"{len(sparse_cells)} populated cells have fewer than "
            f"{min_samples_per_cell} samples"
        )
    if unexpected_cells:
        blocking_reasons.append(
            f"{len(unexpected_cells)} labels are outside the canonical ^0..^9 x P/C/E/O grid"
        )

    packet_ready = not blocking_reasons
    return {
        "status": "packet_ready" if packet_ready else "blocked_missing_balanced_40e_artifact",
        "packet_ready": packet_ready,
        "axis": "40_element_operator_x_domain",
        "expected_cells": len(EXPECTED_40E_CELLS),
        "populated_expected_cells": len(expected_cells & observed_cells),
        "min_samples_per_cell_required": int(min_samples_per_cell),
        "missing_cells": missing_cells,
        "sparse_cells": sparse_cells,
        "unexpected_cells": unexpected_cells,
        "blocking_reasons": blocking_reasons,
        "required_artifact": {
            "name": "balanced_40_element_activation_dataset",
            "description": (
                "A source-derived TKS40 activation dataset with every canonical "
                "^0..^9 x P/C/E/O cell populated at or above the configured "
                "minimum sample count."
            ),
            "required_npz_keys": list(REQUIRED_NPZ_KEYS),
            "feature_shape": "[N_scenarios, N_layers, hidden_dim]",
            "labels": ["labels_operator", "labels_domain"],
            "how_to_supply": (
                "Capture or copy the balanced 40E .npz plus its metadata JSON, then run "
                "this evaluator with --dataset PATH --metadata PATH --output PATH. "
                "Use --require-balanced-40e to make packet assembly fail fast when "
                "the artifact is incomplete."
            ),
        },
    }


def build_registered_artifact_binding(
    *,
    dataset_sha256: str,
    metadata_sha256: str,
    scenario_sha256: str | None,
    metadata: dict,
) -> tuple[dict, list[str]]:
    """Bind the historical Stage-9 files without fabricating model identity.

    The registered metadata bytes are known exactly, and those bytes contain no
    model revision. A revision pasted into a modified copy cannot repair that
    historical omission because the metadata digest would then differ. A future
    capture needs a pre-capture receipt before a new digest can be admitted.
    """

    failures: list[str] = []
    model_id = metadata.get("model_id")
    model_revision = metadata.get("model_revision")
    if dataset_sha256 != REGISTERED_STAGE9_DATASET_SHA256:
        failures.append("ACTIVATION_DATASET_SHA256_MISMATCH")
    if metadata_sha256 != REGISTERED_STAGE9_METADATA_SHA256:
        failures.append("CAPTURE_METADATA_SHA256_MISMATCH")
    if scenario_sha256 != REGISTERED_STAGE9_SCENARIO_SHA256:
        failures.append("SCENARIO_MANIFEST_SHA256_MISMATCH")
    if model_id != REGISTERED_STAGE9_MODEL_ID:
        failures.append("MODEL_ID_MISMATCH")

    exact_historical_metadata = metadata_sha256 == REGISTERED_STAGE9_METADATA_SHA256
    if exact_historical_metadata:
        # This is a permanent property of the captured bytes, not a runtime
        # field that a later operator may fill in.
        failures.append("MODEL_REVISION_UNAVAILABLE")
        identity_status = "MODEL_REVISION_UNAVAILABLE"
    elif not isinstance(model_revision, str) or not re.fullmatch(
        r"[0-9a-f]{40,64}", model_revision
    ):
        failures.append("MODEL_REVISION_NOT_PINNED")
        identity_status = "MODEL_REVISION_NOT_PINNED"
    else:
        # A SHA-shaped value in unregistered metadata is only a declaration.
        failures.append("PRE_CAPTURE_RECEIPT_UNAVAILABLE")
        identity_status = "UNREGISTERED_REVISION_DECLARATION_ONLY"

    return (
        {
            "dataset_sha256": dataset_sha256,
            "expected_dataset_sha256": REGISTERED_STAGE9_DATASET_SHA256,
            "metadata_sha256": metadata_sha256,
            "expected_metadata_sha256": REGISTERED_STAGE9_METADATA_SHA256,
            "scenario_sha256": scenario_sha256,
            "expected_scenario_sha256": REGISTERED_STAGE9_SCENARIO_SHA256,
            "model_id": model_id,
            "expected_model_id": REGISTERED_STAGE9_MODEL_ID,
            "model_revision": model_revision,
            "identity_status": identity_status,
            "packet_eligibility": "NOT_PACKET_ELIGIBLE",
            "status": "BLOCKED",
            "future_capture_requirement": (
                "A new run requires an immutable pre-capture receipt binding the "
                "pinned model revision, tokenizer artifacts, scenario manifest, "
                "capture source/dependencies, and resulting activation artifact."
            ),
        },
        failures,
    )


def _build_linear_probe(C: float, max_iter: int):
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=C,
            max_iter=max_iter,
            class_weight="balanced",
            solver="lbfgs",
            n_jobs=-1,
        ),
    )


def _fit_linear_probe(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    C: float,
    max_iter: int,
) -> tuple[float, float]:
    """Fit StandardScaler + balanced logistic regression; return (acc, macro_f1)."""
    clf = _build_linear_probe(C, max_iter)
    with warnings.catch_warnings():
        # An unconverged fit is not a completed scientific measurement.
        warnings.simplefilter("error", ConvergenceWarning)
        clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    return acc, f1


def build_group_train_validation_test_split(
    features: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    *,
    validation_size: float,
    test_size: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create disjoint group-aware train/validation/test indices.

    The test partition is cut first and never consulted during layer selection.
    The validation partition is then cut from the remaining groups.  Sizes are
    fractions of the full dataset, not fractions of the intermediate split.
    """

    if not 0.0 < validation_size < 1.0:
        raise ValueError("validation_size must be between 0 and 1")
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be between 0 and 1")
    if validation_size + test_size >= 1.0:
        raise ValueError("validation_size + test_size must be less than 1")
    if len(features) != len(labels) or len(features) != len(groups):
        raise ValueError("features, labels, and groups must have equal length")

    outer = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_val_idx, test_idx = next(outer.split(features, labels, groups=groups))
    relative_validation_size = validation_size / (1.0 - test_size)
    inner = GroupShuffleSplit(
        n_splits=1,
        test_size=relative_validation_size,
        random_state=seed + 1,
    )
    train_rel, validation_rel = next(
        inner.split(
            features[train_val_idx],
            labels[train_val_idx],
            groups=groups[train_val_idx],
        )
    )
    train_idx = train_val_idx[train_rel]
    validation_idx = train_val_idx[validation_rel]

    train_groups = set(groups[train_idx].tolist())
    validation_groups = set(groups[validation_idx].tolist())
    test_groups = set(groups[test_idx].tolist())
    if train_groups & validation_groups or train_groups & test_groups or validation_groups & test_groups:
        raise RuntimeError("group leakage detected across train/validation/test")
    return train_idx, validation_idx, test_idx


def select_layer_on_validation(per_layer_results: list[dict]) -> dict:
    """Select without reading test outcomes.

    Predeclared tie order: highest validation accuracy, then highest validation
    macro-F1, then the lowest numeric layer.  The returned dictionary is one of
    ``per_layer_results`` and therefore contains validation metrics only.
    """

    if not per_layer_results:
        raise ValueError("at least one layer result is required")
    required = {"layer", "validation_acc", "validation_macro_f1"}
    for item in per_layer_results:
        if set(item) != required:
            raise ValueError("per-layer selection rows must contain validation metrics only")
    return min(
        per_layer_results,
        key=lambda item: (
            -float(item["validation_acc"]),
            -float(item["validation_macro_f1"]),
            int(item["layer"]),
        ),
    )


def _permute_group_labels_within_splits(
    labels: np.ndarray,
    groups: np.ndarray,
    splits: tuple[np.ndarray, np.ndarray, np.ndarray],
    rng: np.random.Generator,
) -> np.ndarray:
    """Permute whole ordered label vectors by group, separately inside each split."""

    permuted = labels.copy()
    for split_indices in splits:
        group_to_indices: dict[str, list[int]] = {}
        for index in split_indices.tolist():
            group_to_indices.setdefault(str(groups[index]), []).append(int(index))
        groups_by_size: dict[int, list[str]] = {}
        for group, positions in group_to_indices.items():
            groups_by_size.setdefault(len(positions), []).append(group)
        for size, compatible_groups in sorted(groups_by_size.items()):
            ordered_groups = sorted(compatible_groups)
            vectors = [
                tuple(str(labels[index]) for index in group_to_indices[group])
                for group in ordered_groups
            ]
            order = rng.permutation(len(vectors)).tolist()
            for group, source_index in zip(ordered_groups, order, strict=True):
                source_vector = vectors[int(source_index)]
                if len(source_vector) != size:
                    raise RuntimeError("group-vector permutation changed cardinality")
                for index, label in zip(
                    group_to_indices[group], source_vector, strict=True
                ):
                    permuted[index] = label
    return permuted


def selection_aware_shuffled_label_control(
    *,
    features: np.ndarray,
    layers: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    train_idx: np.ndarray,
    validation_idx: np.ndarray,
    test_idx: np.ndarray,
    trials: int,
    seed: int,
    probe_c: float,
    probe_max_iter: int,
) -> dict:
    """Repeat permutation, validation layer selection, refit, and test."""

    if trials <= 0:
        raise ValueError("shuffled-label trials must be positive")
    rng = np.random.default_rng(seed)
    scores: list[float] = []
    selected_layers: list[int] = []
    fit_failures: list[dict[str, int | str]] = []
    fit_idx = np.concatenate((train_idx, validation_idx))
    for _trial in range(trials):
        permuted = _permute_group_labels_within_splits(
            labels,
            groups,
            (train_idx, validation_idx, test_idx),
            rng,
        )
        candidates: list[dict] = []
        for layer_index in range(features.shape[1]):
            X = features[:, layer_index, :].astype(np.float32)
            try:
                acc, macro_f1 = _fit_linear_probe(
                    X[train_idx],
                    permuted[train_idx],
                    X[validation_idx],
                    permuted[validation_idx],
                    probe_c,
                    probe_max_iter,
                )
            except Exception as exc:
                acc, macro_f1 = 0.0, 0.0
                fit_failures.append(
                    {
                        "trial": _trial + 1,
                        "layer": int(layers[layer_index]),
                        "stage": "validation_layer_fit",
                        "error_type": type(exc).__name__,
                    }
                )
            candidates.append(
                {
                    "layer": int(layers[layer_index]),
                    "validation_acc": acc,
                    "validation_macro_f1": macro_f1,
                }
            )
        selected = select_layer_on_validation(candidates)
        selected_index = candidates.index(selected)
        X_selected = features[:, selected_index, :].astype(np.float32)
        try:
            test_acc, _ = _fit_linear_probe(
                X_selected[fit_idx],
                permuted[fit_idx],
                X_selected[test_idx],
                permuted[test_idx],
                probe_c,
                probe_max_iter,
            )
        except Exception as exc:
            test_acc = 0.0
            fit_failures.append(
                {
                    "trial": _trial + 1,
                    "layer": int(selected["layer"]),
                    "stage": "train_plus_validation_refit",
                    "error_type": type(exc).__name__,
                }
            )
        scores.append(float(test_acc))
        selected_layers.append(int(selected["layer"]))
    return {
        "algorithm": (
            "GROUP_LABEL_PERMUTATION_WITHIN_SPLIT_THEN_VALIDATION_LAYER_SELECTION_"
            "REFIT_TRAIN_PLUS_VALIDATION_TEST_ONCE"
        ),
        "selection_aware": True,
        "trials": trials,
        "all_trials": scores,
        "selected_layers": selected_layers,
        "convergence_status": "PASS" if not fit_failures else "FAILED",
        "fit_failures": fit_failures,
        "mean_test_acc": float(np.mean(scores)),
        "std_test_acc": float(np.std(scores)),
        "max_test_acc": float(np.max(scores)),
    }


def resolve_scenario_manifest(
    *,
    metadata: dict,
    metadata_path: Path,
    explicit_path: Path | None,
) -> Path | None:
    """Resolve the preregistered scenario manifest without guessing content."""

    if explicit_path is not None:
        if not explicit_path.is_file():
            raise ValueError(f"scenario manifest does not exist: {explicit_path}")
        return explicit_path.resolve()
    declared = metadata.get("scenario_path")
    if not isinstance(declared, str) or not declared.strip():
        return None
    declared_path = Path(declared)
    candidates = [declared_path]
    if not declared_path.is_absolute():
        candidates.append(metadata_path.parent / declared_path)
    candidates.append(metadata_path.parent / declared_path.name)
    existing = []
    for candidate in candidates:
        if candidate.is_file():
            resolved = candidate.resolve()
            if resolved not in existing:
                existing.append(resolved)
    if len(existing) > 1:
        raise ValueError(f"scenario manifest resolution is ambiguous: {existing}")
    return existing[0] if existing else None


def load_prompts_from_registered_manifest(
    scenario_manifest: Path,
    scenario_ids: np.ndarray,
    *,
    manifest_payload: dict[str, Any] | None = None,
) -> np.ndarray:
    payload = (
        manifest_payload
        if manifest_payload is not None
        else load_json_snapshot(scenario_manifest)[0]
    )
    items = payload.get("scenarios") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("scenario manifest must contain a non-empty scenarios list")
    prompts: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("scenario manifest rows must be objects")
        scenario_id = str(item.get("id") or item.get("scenario_id") or "").strip()
        prompt = item.get("prompt")
        if not scenario_id or scenario_id in prompts:
            raise ValueError("scenario manifest IDs must be non-empty and unique")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError(f"scenario {scenario_id!r} has no prompt text")
        prompts[scenario_id] = prompt
    ordered_ids = [str(value) for value in scenario_ids.tolist()]
    if set(ordered_ids) != set(prompts):
        raise ValueError("scenario manifest prompt IDs do not match activation rows")
    return np.asarray([prompts[scenario_id] for scenario_id in ordered_ids], dtype=str)


def load_registered_split_contract(
    *,
    scenario_manifest: Path,
    scenario_ids: np.ndarray,
    labels: np.ndarray,
    manifest_payload: dict[str, Any] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Load exact preregistered splits and counterfactual-pair grouping.

    The manifest must cover the activation rows one-to-one. Every row must bind
    an exact ``train|val|test`` split, counterfactual-pair ID, and 40E label.
    Counterfactual pairs may not cross partitions, and every partition must
    contain all forty canonical cells.
    """

    payload = (
        manifest_payload
        if manifest_payload is not None
        else load_json_snapshot(scenario_manifest)[0]
    )
    items = payload.get("scenarios") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("scenario manifest must contain a non-empty scenarios list")
    by_id: dict[str, dict] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("scenario manifest rows must be objects")
        scenario_id = str(item.get("id") or item.get("scenario_id") or "").strip()
        if not scenario_id or scenario_id in by_id:
            raise ValueError("scenario manifest IDs must be non-empty and unique")
        by_id[scenario_id] = item

    dataset_ids = [str(value) for value in scenario_ids.tolist()]
    if len(dataset_ids) != len(set(dataset_ids)):
        raise ValueError("activation dataset scenario_ids must be unique")
    if set(dataset_ids) != set(by_id):
        missing = sorted(set(dataset_ids) - set(by_id))
        extra = sorted(set(by_id) - set(dataset_ids))
        raise ValueError(
            "scenario manifest/dataset ID mismatch: "
            f"missing={missing[:3]} extra={extra[:3]}"
        )

    indices: dict[str, list[int]] = {"train": [], "val": [], "test": []}
    pair_splits: dict[str, str] = {}
    pair_members: dict[str, list[tuple[str, str]]] = {}
    pair_ids: list[str] = []
    for index, (scenario_id, observed_label) in enumerate(
        zip(dataset_ids, labels.tolist(), strict=True)
    ):
        item = by_id[scenario_id]
        metadata = item.get("metadata")
        expected_axes = item.get("expected_cas_axes")
        if not isinstance(metadata, dict) or not isinstance(expected_axes, dict):
            raise ValueError(f"scenario {scenario_id} lacks metadata/expected_cas_axes")
        split = str(metadata.get("split") or "")
        if split not in indices:
            raise ValueError(f"scenario {scenario_id} has invalid registered split {split!r}")
        pair_id = str(metadata.get("counterfactual_pair_id") or "").strip()
        if not pair_id:
            raise ValueError(f"scenario {scenario_id} lacks counterfactual_pair_id")
        prior_split = pair_splits.setdefault(pair_id, split)
        if prior_split != split:
            raise ValueError(f"counterfactual pair crosses splits: {pair_id}")
        expected_label = str(
            expected_axes.get("element")
            or f"{expected_axes.get('operator', '')}|{expected_axes.get('domain', '')}"
        )
        if expected_label != str(observed_label):
            raise ValueError(
                f"scenario label mismatch for {scenario_id}: "
                f"manifest={expected_label!r} dataset={observed_label!r}"
            )
        prompt = item.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError(f"scenario {scenario_id} lacks prompt text")
        pair_members.setdefault(pair_id, []).append((prompt, expected_label))
        indices[split].append(index)
        pair_ids.append(pair_id)

    for pair_id, members in pair_members.items():
        if len(members) != 2:
            raise ValueError(
                f"counterfactual pair {pair_id!r} must contain exactly two rows"
            )
        prompts = [prompt for prompt, _label in members]
        labels_in_pair = {label for _prompt, label in members}
        if len(labels_in_pair) != 2:
            raise ValueError(
                f"counterfactual pair {pair_id!r} must contain two different labels"
            )
        if not all(prompt.endswith(("Focus: A.", "Focus: B.")) for prompt in prompts):
            raise ValueError(
                f"counterfactual pair {pair_id!r} lacks the registered Focus A/B suffix"
            )
        bases = {prompt.rsplit("Focus: ", 1)[0] for prompt in prompts}
        suffixes = {prompt.rsplit("Focus: ", 1)[1] for prompt in prompts}
        if len(bases) != 1 or suffixes != {"A.", "B."}:
            raise ValueError(
                f"counterfactual pair {pair_id!r} is not an exact Focus A/B contrast"
            )

    expected_cells = set(EXPECTED_40E_CELLS)
    for split, split_indices in indices.items():
        observed_cells = set(labels[np.asarray(split_indices, dtype=int)].tolist())
        if observed_cells != expected_cells:
            raise ValueError(
                f"registered {split} split lacks exact 40E coverage: "
                f"missing={sorted(expected_cells - observed_cells, key=_cell_sort_key)} "
                f"extra={sorted(observed_cells - expected_cells, key=_cell_sort_key)}"
            )
    return (
        np.asarray(indices["train"], dtype=int),
        np.asarray(indices["val"], dtype=int),
        np.asarray(indices["test"], dtype=int),
        np.asarray(pair_ids, dtype=str),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument(
        "--scenario-manifest",
        type=Path,
        help=(
            "Exact preregistered scenario JSON containing metadata.split and "
            "metadata.counterfactual_pair_id. Required for packet-ready evaluation."
        ),
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--validation-size", type=float, default=0.2)
    parser.add_argument("--shuffled-trials", type=int, default=20)
    parser.add_argument("--probe-C", type=float, default=0.1)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--min-samples-per-cell", type=int, default=DEFAULT_MIN_SAMPLES_PER_CELL)
    parser.add_argument(
        "--require-balanced-40e",
        action="store_true",
        help=(
            "Exit before probe training unless all 40 canonical cells have at least "
            "--min-samples-per-cell samples. Writes a guard report to --output."
        ),
    )
    args = parser.parse_args()

    print(f"loading dataset: {args.dataset}")
    dataset_snapshot: dict[str, Any] = {}
    try:
        data = load_npz_without_pickle(args.dataset, snapshot_out=dataset_snapshot)
    except ValueError as exc:
        raise SystemExit(f"unsafe or invalid activation dataset: {exc}") from exc

    features = data["features"]
    layers = data["layers"]
    labels_domain = data["labels_domain"]
    labels_operator = data["labels_operator"]
    prompts = data["prompts"]
    scenario_ids = data["scenario_ids"]
    if any(
        value is None
        for value in (features, layers, labels_domain, labels_operator, scenario_ids)
    ):
        raise SystemExit("required non-prompt arrays may not use object/pickle storage")

    if features.ndim != 3:
        raise SystemExit(f"features must be [N, num_layers, hidden_dim]; got {features.shape}")
    n_samples, n_layers, hidden_dim = features.shape
    print(f"shape: N={n_samples}, layers={n_layers}, hidden_dim={hidden_dim}")

    # --- Construct 40-Element label = operator | domain ------------------
    forty_element = np.array(
        [f"{op}|{dom}" for op, dom in zip(labels_operator, labels_domain)]
    )
    unique_classes = sorted(set(forty_element.tolist()))
    class_distribution = {c: int((forty_element == c).sum()) for c in unique_classes}
    populated_cells = len(unique_classes)
    print(f"40-Element classes populated: {populated_cells}/40")
    sparse_cells = sum(1 for c in class_distribution.values() if c < args.min_samples_per_cell)
    print(f"  cells with <{args.min_samples_per_cell} samples: {sparse_cells}")

    readiness_gate = build_40e_readiness_gate(
        class_distribution,
        min_samples_per_cell=args.min_samples_per_cell,
    )
    metadata, metadata_snapshot = load_json_snapshot(args.metadata)
    scenario_manifest = resolve_scenario_manifest(
        metadata=metadata,
        metadata_path=args.metadata,
        explicit_path=args.scenario_manifest,
    )
    registered_split: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None
    scenario_payload: dict[str, Any] | None = None
    scenario_snapshot: dict[str, Any] | None = None
    if scenario_manifest is not None:
        scenario_payload, scenario_snapshot = load_json_snapshot(scenario_manifest)
        dataset_sha256 = str(dataset_snapshot["content_sha256"])
        scenario_sha256 = str(scenario_snapshot["content_sha256"])
        if prompts is None:
            if (
                dataset_sha256 != REGISTERED_STAGE9_DATASET_SHA256
                or scenario_sha256 != REGISTERED_STAGE9_SCENARIO_SHA256
            ):
                raise SystemExit(
                    "object-array prompts are forbidden unless both the exact "
                    "precommitted Stage-9 NPZ and scenario manifest hashes match"
                )
            prompts = load_prompts_from_registered_manifest(
                scenario_manifest,
                scenario_ids,
                manifest_payload=scenario_payload,
            )
        registered_split = load_registered_split_contract(
            scenario_manifest=scenario_manifest,
            scenario_ids=scenario_ids,
            labels=forty_element,
            manifest_payload=scenario_payload,
        )
        readiness_gate["registered_split_contract"] = {
            "status": "PASS",
            "scenario_manifest": str(scenario_manifest),
            "scenario_manifest_sha256": scenario_sha256,
            "source": "metadata.split + metadata.counterfactual_pair_id",
        }
    else:
        readiness_gate["registered_split_contract"] = {
            "status": "MISSING",
            "scenario_manifest": None,
            "source": None,
        }
        readiness_gate["blocking_reasons"].append(
            "registered scenario manifest with split and counterfactual-pair metadata is unavailable"
        )
        readiness_gate["packet_ready"] = False
        readiness_gate["status"] = "blocked_missing_registered_split_manifest"
    if prompts is None:
        raise SystemExit(
            "prompt array requires pickle and no exact registered manifest supplied a safe replacement"
        )

    dataset_sha256 = str(dataset_snapshot["content_sha256"])
    metadata_sha256 = str(metadata_snapshot["content_sha256"])
    scenario_sha256 = (
        str(scenario_snapshot["content_sha256"])
        if scenario_snapshot is not None
        else None
    )
    registered_artifact_binding, binding_failures = build_registered_artifact_binding(
        dataset_sha256=dataset_sha256,
        metadata_sha256=metadata_sha256,
        scenario_sha256=scenario_sha256,
        metadata=metadata,
    )
    if binding_failures:
        readiness_gate["blocking_reasons"].extend(binding_failures)
        readiness_gate["packet_ready"] = False
        readiness_gate["status"] = (
            "blocked_historical_model_revision_unavailable_not_packet_eligible"
            if registered_artifact_binding["identity_status"]
            == "MODEL_REVISION_UNAVAILABLE"
            else "blocked_unverified_registered_artifact_or_model_binding"
        )
    readiness_gate["registered_artifact_binding"] = registered_artifact_binding
    if readiness_gate["blocking_reasons"]:
        print("40E packet readiness: BLOCKED")
        for reason in readiness_gate["blocking_reasons"]:
            print(f"  - {reason}")
    else:
        print("40E packet readiness: packet_ready")
    artifacts = [
        _artifact_descriptor(
            "activation_dataset_npz",
            "40e_activation_dataset_npz",
            args.dataset,
            **dataset_snapshot,
        ),
        _artifact_descriptor(
            "metadata_json",
            "40e_capture_metadata_json",
            args.metadata,
            **metadata_snapshot,
        ),
    ]
    if scenario_manifest is not None:
        artifacts.append(
            _artifact_descriptor(
                "scenario_manifest_json",
                "40e_registered_scenario_manifest_json",
                scenario_manifest,
                **scenario_snapshot,
            )
        )
    split_description = (
        "registered train/val/test from scenario metadata; counterfactual pairs disjoint"
        if registered_split is not None
        else "diagnostic-only resplit by normalized prompt; not packet eligible"
    )
    method_contract = {
        "readout": "StandardScaler + LogisticRegression",
        "class_weight": "balanced",
        "solver": "lbfgs",
        "probe_C": float(args.probe_C),
        "probe_max_iter": int(args.probe_max_iter),
        "split": split_description,
        "layer_selection": (
            "validation only: highest accuracy, then highest macro-F1, then lowest layer"
        ),
        "test_set_role": (
            "selected hidden-state probe evaluated once after layer selection; "
            "the shuffled-label null repeats validation-only layer selection; no "
            "test metric selects a layer or hyperparameter"
        ),
        "diagnostic_resplit_parameters": (
            None
            if registered_split is not None
            else {
                "validation_size": float(args.validation_size),
                "test_size": float(args.test_size),
                "seed": int(args.seed),
            }
        ),
        "shuffled_trials": int(args.shuffled_trials),
        "min_samples_per_cell": int(args.min_samples_per_cell),
        "convergence_policy": (
            "sklearn ConvergenceWarning is promoted to an exception; an unconverged "
            "fit is never reported as a completed metric"
        ),
        "source_dependency_binding": {
            "evaluator_source_sha256": _sha256_file(Path(__file__)),
            "python_version": sys.version.split()[0],
            "numpy_version": np.__version__,
            "scikit_learn_version": sklearn.__version__,
        },
    }

    if args.require_balanced_40e and not readiness_gate["packet_ready"]:
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": readiness_gate["status"],
            "created_at": datetime.now(UTC).isoformat(),
            "dataset": str(args.dataset),
            "metadata_path": str(args.metadata),
            "model_id": metadata.get("model_id"),
            "n_samples": int(n_samples),
            "n_layers": int(n_layers),
            "hidden_dim": int(hidden_dim),
            "axis": "40_element_operator_x_domain",
            "populated_cells": populated_cells,
            "total_cells": 40,
            "class_distribution": class_distribution,
            "readiness_gate": readiness_gate,
            "artifacts": artifacts,
            "method_contract": method_contract,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nwrote guard report: {args.output}")
        return 2

    # --- Preregistered split, or explicitly diagnostic fallback ----------
    if registered_split is not None:
        train_idx, validation_idx, test_idx, base_groups = registered_split
        n_unique_groups = len(set(base_groups.tolist()))
        print(f"registered counterfactual-pair groups: {n_unique_groups}")
    else:
        base_groups = np.array([_strip_framing_tags(p) for p in prompts])
        n_unique_groups = len(set(base_groups.tolist()))
        print(f"diagnostic normalized-prompt groups: {n_unique_groups}")
        train_idx, validation_idx, test_idx = build_group_train_validation_test_split(
            features,
            forty_element,
            base_groups,
            validation_size=args.validation_size,
            test_size=args.test_size,
            seed=args.seed,
        )
    split_limit = (
        "The exact preregistered scenario metadata supplies train/val/test and "
        "counterfactual-pair IDs; pair IDs are disjoint across partitions and each "
        "partition contains all 40 cells."
        if registered_split is not None
        else "This diagnostic fallback resamples normalized prompts because the "
        "registered scenario manifest is unavailable; it is not packet-eligible."
    )
    print(
        f"train={len(train_idx)}, validation={len(validation_idx)}, "
        f"test={len(test_idx)} (group-aware split)"
    )

    y_train = forty_element[train_idx]
    y_validation = forty_element[validation_idx]
    y_test = forty_element[test_idx]

    # --- Per-layer hidden-state linear probe -----------------------------
    print("training per-layer probes...")
    per_layer_results = []
    per_layer_fit_failures: list[dict[str, int | str]] = []
    for li in range(n_layers):
        X = features[:, li, :].astype(np.float32)
        X_train_l, X_validation_l = X[train_idx], X[validation_idx]
        try:
            acc, f1 = _fit_linear_probe(
                X_train_l,
                y_train,
                X_validation_l,
                y_validation,
                args.probe_C,
                args.probe_max_iter,
            )
        except Exception as exc:
            print(f"  layer {int(layers[li])}: probe failed -> {exc}")
            acc, f1 = 0.0, 0.0
            per_layer_fit_failures.append(
                {
                    "layer": int(layers[li]),
                    "stage": "validation_layer_fit",
                    "error_type": type(exc).__name__,
                }
            )
        per_layer_results.append(
            {
                "layer": int(layers[li]),
                "validation_acc": acc,
                "validation_macro_f1": f1,
            }
        )
        print(
            f"  layer {int(layers[li]):3d}: validation_acc={acc*100:5.2f}%  "
            f"validation_macro_f1={f1*100:5.2f}%"
        )

    selected = select_layer_on_validation(per_layer_results)
    best_layer_idx = per_layer_results.index(selected)
    print(
        f"\nselected layer: {selected['layer']} "
        f"(validation acc={selected['validation_acc']*100:.2f}%)"
    )

    # The selected layer is now fixed. Refit once on train+validation, and use
    # the untouched test partition exactly once for the headline.
    fit_idx = np.concatenate((train_idx, validation_idx))
    y_fit = forty_element[fit_idx]
    X_selected = features[:, best_layer_idx, :].astype(np.float32)
    test_acc, test_f1 = _fit_linear_probe(
        X_selected[fit_idx],
        y_fit,
        X_selected[test_idx],
        y_test,
        args.probe_C,
        args.probe_max_iter,
    )
    best = {
        "layer": int(selected["layer"]),
        "selection_validation_acc": float(selected["validation_acc"]),
        "selection_validation_macro_f1": float(selected["validation_macro_f1"]),
        "test_acc": test_acc,
        "test_macro_f1": test_f1,
        "selection_rule": (
            "highest validation accuracy; tie highest validation macro-F1; "
            "tie lowest numeric layer"
        ),
    }

    # --- Control 1: majority class ---------------------------------------
    test_class_counts = {c: int((y_test == c).sum()) for c in unique_classes}
    fit_class_distribution = {c: int((y_fit == c).sum()) for c in unique_classes}
    most_common_in_train = max(fit_class_distribution, key=fit_class_distribution.get)
    majority_test_acc = float((y_test == most_common_in_train).mean())

    # --- Control 2: selection-aware group-label permutation -------------
    print(
        f"\nrunning {args.shuffled_trials} shuffled-label trials through the "
        "complete layer-selection pipeline..."
    )
    shuffled_control = selection_aware_shuffled_label_control(
        features=features,
        layers=layers,
        labels=forty_element,
        groups=base_groups,
        train_idx=train_idx,
        validation_idx=validation_idx,
        test_idx=test_idx,
        trials=args.shuffled_trials,
        seed=args.seed,
        probe_c=args.probe_C,
        probe_max_iter=args.probe_max_iter,
    )
    shuffled_accs = shuffled_control["all_trials"]
    shuffled_mean = shuffled_control["mean_test_acc"]
    shuffled_std = shuffled_control["std_test_acc"]
    shuffled_max = shuffled_control["max_test_acc"]
    if per_layer_fit_failures or shuffled_control["fit_failures"]:
        readiness_gate["packet_ready"] = False
        readiness_gate["status"] = "blocked_probe_fit_or_convergence_failure"
        readiness_gate["blocking_reasons"].append(
            "one or more logistic probe fits failed or did not converge"
        )
    for trial, (acc_s, layer) in enumerate(
        zip(shuffled_accs, shuffled_control["selected_layers"], strict=True), 1
    ):
        print(f"  trial {trial:2d}: selected_layer={layer} acc={acc_s*100:.2f}%")
    print(
        f"shuffled mean={shuffled_mean*100:.2f}% "
        f"std={shuffled_std*100:.2f}% max={shuffled_max*100:.2f}%"
    )

    # --- Control 3: text-hash baseline (canonical English surface) -------
    print("\ntraining text-hash baseline...")
    vec = HashingVectorizer(n_features=2**14, ngram_range=(1, 2), alternate_sign=False)
    text_train_X = vec.transform([str(p) for p in prompts[fit_idx]])
    text_test_X = vec.transform([str(p) for p in prompts[test_idx]])
    text_clf = LogisticRegression(
        C=1.0,
        max_iter=args.probe_max_iter,
        class_weight="balanced",
        solver="lbfgs",
        n_jobs=-1,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        text_clf.fit(text_train_X, y_fit)
    text_pred = text_clf.predict(text_test_X)
    text_acc = float(accuracy_score(y_test, text_pred))
    text_f1 = float(f1_score(y_test, text_pred, average="macro", zero_division=0))
    print(f"text-hash: acc={text_acc*100:.2f}%  macro_f1={text_f1*100:.2f}%")

    # --- Composite report -----------------------------------------------
    label_drop_minus_random_mean = best["test_acc"] - shuffled_mean

    report = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "packet_ready_evaluation_completed"
            if readiness_gate["packet_ready"]
            else "diagnostic_completed_not_packet_ready"
        ),
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "metadata_path": str(args.metadata),
        "model_id": metadata.get("model_id"),
        "artifacts": artifacts,
        "method_contract": method_contract,
        "n_samples": int(n_samples),
        "n_layers": int(n_layers),
        "hidden_dim": int(hidden_dim),
        "n_train": int(len(train_idx)),
        "n_validation": int(len(validation_idx)),
        "n_test": int(len(test_idx)),
        "n_group_ids": int(n_unique_groups),
        "group_id_type": (
            "metadata.counterfactual_pair_id"
            if registered_split is not None
            else "normalized_prompt_diagnostic"
        ),
        "split": split_description,
        "validation_size": (
            None if registered_split is not None else float(args.validation_size)
        ),
        "test_size": None if registered_split is not None else float(args.test_size),
        "axis": "40_element_operator_x_domain",
        "populated_cells": populated_cells,
        "total_cells": 40,
        "sparse_cells_lt_min_samples": sparse_cells,
        "class_distribution": class_distribution,
        "test_class_distribution": test_class_counts,
        "readiness_gate": readiness_gate,
        "best_layer": best,
        "per_layer": per_layer_results,
        "per_layer_fit_failures": per_layer_fit_failures,
        "controls": {
            "majority_class_test_acc": majority_test_acc,
            "majority_class_label": most_common_in_train,
            "shuffled_label_hidden_selection_aware": shuffled_control,
            "text_hash_logistic_regression": {
                "test_acc": text_acc,
                "test_macro_f1": text_f1,
                "description": "HashingVectorizer(1-2 ngrams, 2^14 features) + LogisticRegression on prompt text",
            },
        },
        "result_summary": {
            "hidden_probe_test_acc": best["test_acc"],
            "hidden_probe_minus_shuffled_mean_pp": label_drop_minus_random_mean * 100,
            "hidden_probe_exceeds_shuffled_max": best["test_acc"] > shuffled_max,
            "hidden_probe_beats_majority": best["test_acc"] > majority_test_acc,
            "hidden_probe_exceeds_word_hashing_text_control": best["test_acc"] > text_acc,
            "interpretation": (
                (
                    "Registered-split 40E evaluation completed on this substrate. "
                    "Any scientific claim remains conditional on the reported controls, "
                    "readiness gates, and separate Evidence Packet review."
                )
                if readiness_gate["packet_ready"]
                else (
                    "Diagnostic evaluation only. Missing readiness or registered-split "
                    "evidence prevents protocol-replication or packet claims."
                )
            ),
        },
        "pythia_160m_comparator": {
            "axis": "40-Element (10 Noetics x 4 Domains)",
            "readout_test_acc": 0.898,
            "text_baseline_gap_pp": 39.7,
            "source": "CAS_HARNESS_SPEC_SHEET_v1_5_20260519_409e9efe",
        },
        "important_limit": (
            f"Dataset has {populated_cells}/40 cells populated, with {sparse_cells} "
            f"cells under the configured minimum of {args.min_samples_per_cell} samples. "
            "Probe is undertrained for sparse cells. "
            f"{split_limit} "
            "Layer selection uses validation metrics only; the selected hidden-state "
            "probe is evaluated once after the layer is fixed. The shuffled-label "
            "control repeats validation layer selection under every group-level null "
            "draw. The word HashingVectorizer control measures whether prompt surface "
            "forms (which carry "
            "canonical CAS colloquialisms) encode the label. A high text baseline is "
            "the framework's intended English surface, NOT a contamination control. "
            "No character-level surface control is implemented here, so any claim "
            "relative to text controls remains PARTIAL. "
            "Methodology minimum is 10 samples per cell; headline closure can be "
            "rerun with --min-samples-per-cell 25 for the stricter ~1000-scenario "
            "packet threshold."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote report: {args.output}")

    # --- Headline summary printed last ----------------------------------
    print()
    print("=" * 64)
    print("40-ELEMENT READOUT HEADLINE")
    print("=" * 64)
    print(f"  Hidden probe (best layer={best['layer']:>3d}):  {best['test_acc']*100:6.2f}%")
    print(f"  Majority baseline:                {majority_test_acc*100:6.2f}%")
    print(f"  Shuffled-label control (mean):    {shuffled_mean*100:6.2f}%   (max {shuffled_max*100:.2f}, std {shuffled_std*100:.2f})")
    print(f"  Text-hash baseline:               {text_acc*100:6.2f}%")
    print(f"  Pythia-160M comparator:           {89.80:6.2f}%   (spec sheet v1.5)")
    print()
    print(f"  Probe above shuffled max:         {report['result_summary']['hidden_probe_exceeds_shuffled_max']}")
    print(f"  Probe above majority:             {report['result_summary']['hidden_probe_beats_majority']}")
    print(
        "  Probe above word-hashing control: "
        f"{report['result_summary']['hidden_probe_exceeds_word_hashing_text_control']}"
    )
    print(f"  Probe minus shuffled mean:        {label_drop_minus_random_mean*100:+6.2f} pp")
    print("=" * 64)

    return 0


if __name__ == "__main__":
    sys.exit(main())
