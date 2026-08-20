"""Dependency-light nearest-centroid metrics shared by offline probe tools.

This module contains no model loading, network access, layer selection, or
claim logic.  It fits on the caller's explicit train indices and reports the
three explicit partitions.  Layer selection remains the caller's job and must
use validation metrics only.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def fit_eval_centroid(
    x: np.ndarray,
    y: np.ndarray,
    split: dict[str, np.ndarray],
) -> tuple[dict[str, float], dict[str, Any]]:
    """Fit a standardized centroid model on ``split['train']`` only."""

    required = {"train", "val", "test"}
    if set(split) != required:
        raise ValueError(f"split keyset must be exactly {sorted(required)}")
    if len(x) != len(y):
        raise ValueError("x and y must have equal first dimension")
    for name in sorted(required):
        indices = np.asarray(split[name])
        if indices.ndim != 1 or len(indices) == 0:
            raise ValueError(f"split[{name!r}] must be a non-empty 1-D array")
        if np.any(indices < 0) or np.any(indices >= len(y)):
            raise ValueError(f"split[{name!r}] contains an out-of-range index")
    train_set = set(np.asarray(split["train"], dtype=int).tolist())
    val_set = set(np.asarray(split["val"], dtype=int).tolist())
    test_set = set(np.asarray(split["test"], dtype=int).tolist())
    if train_set & val_set or train_set & test_set or val_set & test_set:
        raise ValueError("train/val/test indices must be disjoint")

    train_indices = np.asarray(split["train"], dtype=int)
    train_x = np.asarray(x[train_indices], dtype=np.float32)
    mean = train_x.mean(axis=0)
    std = train_x.std(axis=0)
    std[std < 1e-6] = 1.0
    train_scaled = (train_x - mean) / std
    classes = sorted(set(np.asarray(y[train_indices], dtype=str).tolist()))
    if len(classes) < 2:
        raise ValueError("centroid readout requires at least two training classes")
    centroids: dict[str, np.ndarray] = {}
    train_labels = np.asarray(y[train_indices], dtype=str)
    for label in classes:
        members = train_scaled[train_labels == label]
        if len(members) == 0:
            raise RuntimeError(f"training class unexpectedly empty: {label}")
        centroids[label] = members.mean(axis=0)
    model: dict[str, Any] = {
        "mean": mean,
        "std": std,
        "classes": classes,
        "centroids": centroids,
    }
    train_pred = predict_centroid(x[split["train"]], model)
    val_pred = predict_centroid(x[split["val"]], model)
    test_pred = predict_centroid(x[split["test"]], model)
    metrics = {
        "train_acc": accuracy(y[split["train"]], train_pred),
        "val_acc": accuracy(y[split["val"]], val_pred),
        "test_acc": accuracy(y[split["test"]], test_pred),
        "test_macro_f1": macro_f1(y[split["test"]], test_pred, classes),
    }
    return {key: round(float(value), 6) for key, value in metrics.items()}, model


def predict_centroid(x: np.ndarray, model: dict[str, Any]) -> np.ndarray:
    scaled = (np.asarray(x, dtype=np.float32) - model["mean"]) / model["std"]
    centroid_matrix = np.stack(
        [model["centroids"][label] for label in model["classes"]], axis=0
    )
    distances = ((scaled[:, None, :] - centroid_matrix[None, :, :]) ** 2).sum(axis=2)
    return np.asarray(
        [model["classes"][int(index)] for index in distances.argmin(axis=1)],
        dtype=str,
    )


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) == 0:
        return 0.0
    return float((np.asarray(y_true) == np.asarray(y_pred)).mean())


def macro_f1(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    classes: list[str],
) -> float:
    truth = np.asarray(y_true)
    prediction = np.asarray(y_pred)
    scores: list[float] = []
    for label in classes:
        true_positive = int(((truth == label) & (prediction == label)).sum())
        false_positive = int(((truth != label) & (prediction == label)).sum())
        false_negative = int(((truth == label) & (prediction != label)).sum())
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        scores.append(
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
    return float(np.mean(scores)) if scores else 0.0


__all__ = [
    "accuracy",
    "fit_eval_centroid",
    "macro_f1",
    "predict_centroid",
]
