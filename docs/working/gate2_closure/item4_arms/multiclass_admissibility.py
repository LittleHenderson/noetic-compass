"""Build item B6 — a MULTICLASS admissibility gate for the item-4 experiment.

Why this file exists. `research/reconciled/experiment_admissibility.py` was
written on 2026-07-24 for a BINARY task and is calibrated to it end to end:

  * `instrument_positive_control` raises
    `ValueError("Positive control needs exactly two classes")` on anything that
    is not binary (verified at that file's line ~190);
  * `MIN_EFFECTIVE_N_FOR_MARGIN_GATE = 200` was derived from a 0.15 binary
    margin bar;
  * the resolution check `balanced_accuracy_quantum <= 0.015` assumes chance is
    0.5 and the reportable quantity is a two-class balanced accuracy.

Item 4 is a 40-way task with chance at 0.025. Pointing the binary guard at it
would either crash or, worse, pass vacuously — leaving the experiment ungated in
exactly the way the four 2026-07-24 runs were ungated. This module supplies the
multiclass equivalents, keeping the same fail-closed posture and the same rule
that a refusal to measure is NOT a failed experiment.

What is different for multiclass, and why:

  * PER-CLASS SUPPORT, not just total n. With 40 classes, a bank can carry
    thousands of rows and still have a class with 3 test items. Macro-F1
    averages over classes, so the WEAKEST class sets the resolution of the
    headline number. The gate therefore requires a floor on the minimum
    per-class test count, not merely a large total.
  * MACRO-F1 QUANTUM. The smallest visible change in macro-F1 is bounded below
    by roughly 1/(n_classes * min_class_support). That is the honest resolution
    of the metric and is checked against the pre-registered effect size.
  * CHANCE IS 1/K, NOT 0.5. A "beats chance" claim at 40-way is nearly free;
    the meaningful bar is the margin over the STRONGEST control, so the gate
    records chance explicitly to stop it being quoted as an achievement.
  * POSITIVE CONTROL MUST BE MULTICLASS. `multiclass_positive_control` plants a
    known K-class signal and asserts the instrument recovers it. If a pipeline
    cannot find a planted 40-way signal, any negative result it produces is
    uninterpretable -- the instrument, not the hypothesis, may be what failed.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

# Frozen for the item-4 pre-registration. Chosen from the metric's resolution,
# NOT tuned to any observed result.
MIN_TEST_ITEMS_PER_CLASS = 20
MIN_EFFECTIVE_N_MULTICLASS = 1000
MAX_MACRO_F1_QUANTUM = 0.010
POSITIVE_CONTROL_MIN_RECOVERY = 0.80

# Standard plant for the positive control, CALIBRATED and measured 2026-07-25.
# This calibrates the TEST, not any experimental threshold. Measured recovery
# for a correct StandardScaler+LogisticRegression probe at 40 classes / dim 64 /
# 30 per class (chance 0.025):
#     separation 3.0 -> 0.5758   4.0 -> 0.8539   5.0 -> 0.9638
#     separation 6.0 -> 0.9986   8.0 -> 1.0000
# At 3.0 the plant itself sits near the linear-separability limit, so a failure
# there is AMBIGUOUS between "the instrument is broken" and "the plant was not
# findable" -- which defeats the control's entire purpose. 5.0 is pinned because
# a correct probe clears it comfortably (0.9638) while a broken probe still
# lands exactly at chance (0.0250, measured). The bar itself stays at 0.80.
POSITIVE_CONTROL_STANDARD_SEPARATION = 5.0
POSITIVE_CONTROL_STANDARD_DIM = 64
POSITIVE_CONTROL_STANDARD_N_PER_CLASS = 30


def multiclass_sample_profile(
    *,
    labels: np.ndarray,
    groups: np.ndarray,
    prompts: np.ndarray,
    split: np.ndarray | None = None,
) -> dict[str, Any]:
    """Honest denominators for a K-way task."""
    labels = np.asarray(labels, dtype=str)
    unique_prompts = int(len({str(p) for p in prompts.tolist()}))
    counts = Counter(labels.tolist())
    n_classes = len(counts)

    if split is not None:
        split = np.asarray(split, dtype=str)
        test_mask = split == "test"
        test_counts = Counter(labels[test_mask].tolist())
    else:
        test_counts = counts

    min_class = min(test_counts.values()) if test_counts else 0
    macro_f1_quantum = (1.0 / (n_classes * min_class)) if (n_classes and min_class) else None

    return {
        "row_count": int(len(labels)),
        "unique_prompt_count": unique_prompts,
        "effective_sample_size": unique_prompts,
        "duplication_factor": round(len(labels) / unique_prompts, 6) if unique_prompts else None,
        "unique_group_count": int(len({str(g) for g in groups.tolist()})),
        "n_classes": n_classes,
        "chance_accuracy": round(1.0 / n_classes, 6) if n_classes else None,
        "min_test_items_per_class": int(min_class),
        "max_test_items_per_class": int(max(test_counts.values())) if test_counts else 0,
        "macro_f1_quantum": round(macro_f1_quantum, 6) if macro_f1_quantum else None,
        "class_support_test": dict(sorted(test_counts.items())),
    }


def assess_multiclass_admissibility(
    *, profile: dict[str, Any], preregistered_effect_size: float,
) -> dict[str, Any]:
    """FAIL CLOSED. A refusal here is an apparatus decision, never a FAIL result."""
    checks: dict[str, dict[str, Any]] = {}

    dup = profile.get("duplication_factor")
    checks["no_row_duplication"] = {
        "passed": dup is not None and dup <= 1.0001,
        "observed": dup,
        "requirement": "duplication_factor <= 1.0001",
        "why": "Duplicated rows inflate apparent n without adding information.",
    }

    eff = profile.get("effective_sample_size") or 0
    checks["effective_n_multiclass"] = {
        "passed": eff >= MIN_EFFECTIVE_N_MULTICLASS,
        "observed": eff,
        "requirement": f"effective_sample_size >= {MIN_EFFECTIVE_N_MULTICLASS}",
        "why": "A K-way task spreads its evidence across K classes; total n must be larger than the binary case.",
    }

    min_cls = profile.get("min_test_items_per_class") or 0
    checks["per_class_support_floor"] = {
        "passed": min_cls >= MIN_TEST_ITEMS_PER_CLASS,
        "observed": min_cls,
        "requirement": f"min test items per class >= {MIN_TEST_ITEMS_PER_CLASS}",
        "why": "Macro-F1 averages over classes, so the weakest class sets the headline's resolution.",
    }

    quantum = profile.get("macro_f1_quantum")
    checks["metric_resolution"] = {
        "passed": quantum is not None and quantum <= MAX_MACRO_F1_QUANTUM,
        "observed": quantum,
        "requirement": f"macro_f1_quantum <= {MAX_MACRO_F1_QUANTUM}",
        "why": "The metric cannot resolve an effect smaller than its own step size.",
    }

    checks["effect_size_above_resolution"] = {
        "passed": quantum is not None and preregistered_effect_size >= 3.0 * quantum,
        "observed": f"effect {preregistered_effect_size} vs 3x quantum {round(3.0 * quantum, 6) if quantum else None}",
        "requirement": "pre-registered effect size >= 3x the metric quantum",
        "why": "An effect near the metric's step size cannot be distinguished from rounding.",
    }

    failed = [k for k, v in checks.items() if not v["passed"]]
    return {
        "admissible": not failed,
        "verdict": "ADMISSIBLE" if not failed else "INADMISSIBLE_DO_NOT_SCORE: " + ", ".join(failed),
        "failed_checks": failed,
        "checks": checks,
        "chance_accuracy": profile.get("chance_accuracy"),
        "chance_note": (
            "Chance is 1/K, not 0.5. Beating chance on a K-way task is nearly free and is NOT a "
            "result; the reportable quantity is the margin over the STRONGEST control."
        ),
        "refusal_is_not_a_failure": (
            "An INADMISSIBLE verdict means the apparatus declines to produce a number it cannot "
            "defend. It must never be recorded as a failed experiment."
        ),
    }


def multiclass_positive_control(
    *,
    n_classes: int,
    n_per_class: int,
    dim: int,
    separation: float,
    fit_predict,
    seed: int = 0,
) -> dict[str, Any]:
    """Plant a known K-class signal and require the instrument to recover it.

    ``fit_predict(X_train, y_train, X_test) -> y_pred``. If a pipeline cannot
    find a planted 40-way signal, then any NEGATIVE result it later reports is
    uninterpretable: the instrument may be what failed, not the hypothesis.
    This is the check the 2026-07-24 runs never had.
    """
    if n_classes < 3:
        raise ValueError("multiclass_positive_control needs at least three classes")
    rng = np.random.default_rng(seed)
    centres = rng.normal(size=(n_classes, dim))
    centres /= np.linalg.norm(centres, axis=1, keepdims=True)

    X, y = [], []
    for k in range(n_classes):
        pts = rng.normal(size=(n_per_class, dim)) + separation * centres[k]
        X.append(pts)
        y.extend([f"class_{k}"] * n_per_class)
    X = np.vstack(X).astype(np.float32)
    y = np.asarray(y, dtype=str)

    idx = rng.permutation(len(y))
    cut = len(y) // 2
    tr, te = idx[:cut], idx[cut:]
    pred = np.asarray(fit_predict(X[tr], y[tr], X[te]), dtype=str)

    per_class = []
    for k in sorted(set(y.tolist())):
        mask = y[te] == k
        if mask.any():
            per_class.append(float((pred[mask] == y[te][mask]).mean()))
    recovery = float(np.mean(per_class)) if per_class else 0.0

    return {
        "n_classes": n_classes,
        "separation": separation,
        "chance": round(1.0 / n_classes, 6),
        "recovered_macro_accuracy": round(recovery, 6),
        "requirement": f"recovered >= {POSITIVE_CONTROL_MIN_RECOVERY}",
        "passed": recovery >= POSITIVE_CONTROL_MIN_RECOVERY,
        "why": (
            "A pipeline that cannot recover a PLANTED K-way signal cannot be trusted to report a "
            "negative result about a real one."
        ),
    }
