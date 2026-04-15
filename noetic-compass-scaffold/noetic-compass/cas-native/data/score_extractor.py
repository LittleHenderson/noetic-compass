"""Extract ground truth CAS scores from compiled expressions.

Produces the training labels (operator scores, domain scores, drive scores,
lacunarity) from the compilation result and expression structure.
"""

from __future__ import annotations

import re


def extract_scores(expression: str, compilation_result: object | None = None) -> dict:
    """Extract CAS training labels from an expression and its compilation."""

    # Parse operators, domains, drives from the expression text
    op_counts = [0.0] * 10
    dom_counts = [0.0] * 4
    drv_counts = [0.0] * 7
    domain_map = {"P": 0, "C": 1, "E": 2, "O": 3}

    for m in re.finditer(r"CO-(\d+)\^([PCEO])(?:_\{F(\d)\})?", expression):
        op_idx = int(m.group(1))
        dom = m.group(2)
        drv = int(m.group(3)) if m.group(3) else None

        if 0 <= op_idx <= 9:
            op_counts[op_idx] += 1.0
        if dom in domain_map:
            dom_counts[domain_map[dom]] += 1.0
        if drv and 1 <= drv <= 7:
            drv_counts[drv - 1] += 1.0

    # Check for bare drive references (F1, F2, etc.)
    for m in re.finditer(r"\bF(\d)\b", expression):
        d = int(m.group(1))
        if 1 <= d <= 7:
            drv_counts[d - 1] = max(drv_counts[d - 1], 0.5)

    # Normalize operator scores to [0, 1]
    max_op = max(op_counts) if max(op_counts) > 0 else 1.0
    op_scores = [round(s / max_op, 4) for s in op_counts]

    # Normalize domain scores
    max_dom = max(dom_counts) if max(dom_counts) > 0 else 1.0
    dom_scores = [round(s / max_dom, 4) for s in dom_counts]

    # Normalize drive scores
    max_drv = max(drv_counts) if max(drv_counts) > 0 else 1.0
    drv_scores = [round(s / max_drv, 4) for s in drv_counts]

    # RPM completeness
    rpm_complete = 1.0 if "RPM(" in expression else 0.0

    # Fractal classification
    fractal_class = "neutral"
    if "Phi<" in expression:
        fractal_class = "stabilizing"  # default for synthetic data

    # Lacunarity (state lacunarity)
    mean_op = sum(op_scores) / 10.0 if sum(op_scores) > 0 else 0.0
    if mean_op > 0:
        variance = sum((s - mean_op) ** 2 for s in op_scores) / 10.0
        lacunarity = round(variance / (mean_op ** 2), 4)
    else:
        lacunarity = 0.0

    # Has domain descent
    has_descent = "->" in expression
    # Has involution pair
    has_division = " / " in expression

    return {
        "operator_scores": op_scores,
        "domain_scores": dom_scores,
        "drive_scores": drv_scores,
        "rpm_completeness": rpm_complete,
        "fractal_classification": fractal_class,
        "lacunarity": lacunarity,
        "has_descent": has_descent,
        "has_division": has_division,
    }
