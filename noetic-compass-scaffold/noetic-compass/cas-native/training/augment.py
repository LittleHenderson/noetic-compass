"""Training data augmentation using the CAS inversion engine.

Takes scored prompt-response pairs and generates inverted variants
with adjusted expected scores. Multiplies training data without
needing more real assessments.
"""

from __future__ import annotations

import copy
from typing import Any

from scenarios.generator.inversion_engine import (
    Scenario,
    invert_all_axes,
    OPERATOR_INVOLUTIONS,
    DRIVE_INVERSIONS,
    DOMAIN_SWAPS,
)


def _flip_operator_scores(scores: list[float], axis: str) -> list[float]:
    """Adjust operator scores based on inversion axis.

    N-axis: swap involution pair scores (CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9)
    Other axes: apply moderate dampening to all scores (simulates confusion)
    """
    result = list(scores)
    if axis == "N":
        for a, b in ((2, 3), (5, 6), (8, 9)):
            if a < len(result) and b < len(result):
                result[a], result[b] = result[b], result[a]
    elif axis in ("W", "F", "E", "S"):
        # Moderate dampening — inversion should lower scores
        result = [max(0.0, s * 0.7) for s in result]
    elif axis == "A":
        # RPM scramble — minimal operator impact
        result = [max(0.0, s * 0.9) for s in result]
    elif axis == "P":
        # Compound — most severe
        for a, b in ((2, 3), (5, 6), (8, 9)):
            if a < len(result) and b < len(result):
                result[a], result[b] = result[b], result[a]
        result = [max(0.0, s * 0.75) for s in result]
    return result


def _flip_domain_averages(avgs: list[float], axis: str) -> list[float]:
    """Adjust domain averages based on inversion axis.

    W-axis: swap P↔O and C↔E
    Other axes: slight dampening
    """
    result = list(avgs)
    if len(result) != 4:
        return result

    if axis in ("W", "P"):
        # P↔O, C↔E
        result[0], result[3] = result[3], result[0]
        result[1], result[2] = result[2], result[1]
    elif axis in ("S", "E"):
        result = [max(0.01, a * 0.8) for a in result]

    # Re-normalize to sum ~1.0 (open simplex)
    total = sum(result)
    if total > 0:
        result = [r / total for r in result]
    return result


def _flip_drive_scores(drives: list[float], axis: str) -> list[float]:
    """Adjust drive scores based on inversion axis.

    F-axis: swap drive inversion pairs
    Other axes: moderate dampening
    """
    result = list(drives)
    if axis in ("F", "P"):
        for a, b in ((0, 6), (1, 5), (2, 4)):
            if a < len(result) and b < len(result):
                result[a], result[b] = result[b], result[a]
    elif axis in ("S", "E"):
        result = [max(0.0, d * 0.75) for d in result]
    return result


def augment_training_item(
    item: dict[str, Any],
) -> list[dict[str, Any]]:
    """Augment a single training item with 7 inverted variants.

    Takes a scored prompt-response pair (from baseline_results.json)
    and returns 7 variants with adjusted expected scores.

    Args:
        item: Dict with keys like 'prompt', 'operator_scores',
              'domain_averages', 'drive_scores', 'composite', etc.

    Returns:
        List of 7 augmented dicts, each tagged with inversion metadata.
    """
    prompt = item.get("prompt", "")
    idx = item.get("index", 0)

    # Build a Scenario for the inversion engine
    ops = item.get("operator_scores", [])
    top_ops = sorted(range(len(ops)), key=lambda i: ops[i] if i < len(ops) else 0, reverse=True)[:3]

    scenario = Scenario(
        id=f"train_{idx}",
        prompt=prompt,
        target_operators=top_ops,
        target_domain="O",
        target_drives=[0, 3],
    )

    inverted_scenarios = invert_all_axes(scenario)
    results: list[dict[str, Any]] = []

    for inv in inverted_scenarios:
        augmented = copy.deepcopy(item)
        augmented["prompt"] = inv.prompt
        augmented["augmentation"] = {
            "source_index": idx,
            "inversion_axis": inv.inversion_axis,
            "axis_description": inv.axis_description,
            "expected_detection": inv.expected_detection,
        }

        # Adjust scores
        if "operator_scores" in augmented:
            augmented["operator_scores"] = _flip_operator_scores(
                augmented["operator_scores"], inv.inversion_axis
            )
        if "domain_averages" in augmented:
            augmented["domain_averages"] = _flip_domain_averages(
                augmented["domain_averages"], inv.inversion_axis
            )
        if "drive_scores" in augmented:
            augmented["drive_scores"] = _flip_drive_scores(
                augmented["drive_scores"], inv.inversion_axis
            )

        # Composite should decrease for inverted scenarios
        if "composite" in augmented:
            dampen = {"N": 0.85, "W": 0.80, "F": 0.80, "E": 0.75, "S": 0.82, "A": 0.88, "P": 0.65}
            factor = dampen.get(inv.inversion_axis, 0.8)
            augmented["composite"] = augmented["composite"] * factor

        results.append(augmented)

    return results


def augment_dataset(
    data: list[dict[str, Any]],
    max_augmented: int | None = None,
) -> list[dict[str, Any]]:
    """Augment an entire dataset with inverted variants.

    Returns the original data + augmented variants.
    """
    augmented: list[dict[str, Any]] = list(data)  # keep originals

    for item in data:
        variants = augment_training_item(item)
        augmented.extend(variants)
        if max_augmented and len(augmented) >= max_augmented:
            break

    if max_augmented:
        augmented = augmented[:max_augmented]

    return augmented
