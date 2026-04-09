"""Cognitive Fractal Analysis — pure Python implementation.

Analyzes the dominant operator sequence from an assessment as a
Cognitive Fractal, applying v6.1 Chapter 8 rules:
- Dual cancellation for involution pairs
- Canonical form computation
- Classification (Stabilizing/Amplifying/Oscillatory/Neutral)

This is a Python fallback for when the Rust cas_engine fractal
module isn't available via PyO3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Involution pairs (0-indexed): CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9
INVOLUTION_PAIRS = {(2, 3), (3, 2), (5, 6), (6, 5), (8, 9), (9, 8)}


def is_dual_pair(a: int, b: int) -> bool:
    return (a, b) in INVOLUTION_PAIRS


def canonicalize(operators: list[int]) -> tuple[list[int], int]:
    """Reduce an operator sequence to canonical form.

    Returns (canonical_form, cancellation_count).
    """
    ops = list(operators)
    cancellations = 0

    changed = True
    while changed:
        changed = False
        # Dual cancellation pass
        i = 0
        while i + 1 < len(ops):
            if is_dual_pair(ops[i], ops[i + 1]):
                ops[i] = 0
                ops.pop(i + 1)
                cancellations += 1
                changed = True
            else:
                i += 1

        # Identity elimination
        if len(ops) > 1:
            new_ops = [op for op in ops if op != 0]
            if not new_ops:
                new_ops = [0]
            if len(new_ops) != len(ops):
                ops = new_ops
                changed = True

    return ops, cancellations


def classify_fractal(operators: list[int], max_iterations: int = 50) -> str:
    """Classify a fractal's dynamic behavior.

    Returns one of: "stabilizing", "amplifying", "oscillatory", "neutral"
    """
    if not operators:
        return "neutral"
    if operators == [0]:
        return "neutral"

    # Simulate orbit on a test state (operator index)
    state = 1  # Start with CO-1
    seen: dict[int, int] = {state: 0}
    history = [state]

    for step in range(1, max_iterations + 1):
        # Apply fractal right-to-left via modular composition
        for op in reversed(operators):
            state = (state + op) % 10
        if state == history[-1]:
            return "stabilizing"
        if state in seen:
            period = step - seen[state]
            if period == 1:
                return "stabilizing"
            return "oscillatory"
        seen[state] = step
        history.append(state)

    return "amplifying"


@dataclass
class FractalAnalysisResult:
    """Result of analyzing an operator sequence as a Cognitive Fractal."""
    dominant_sequence: list[int]
    canonical_form: list[int]
    cancellations_detected: int
    classification: str
    orbit_length: int
    has_fixed_point: bool


def extract_dominant_sequence(operator_scores: list[float], top_n: int = 5) -> list[int]:
    """Extract the dominant operator sequence from scores.

    Selects the top_n operators by score, ordered by index.
    """
    if not operator_scores:
        return [0]

    indexed = sorted(enumerate(operator_scores), key=lambda x: -x[1])
    top = sorted([idx for idx, _ in indexed[:top_n]])
    return top if top else [0]


def analyze_fractal(operator_scores: list[float]) -> FractalAnalysisResult:
    """Perform full fractal analysis on operator scores.

    1. Extract dominant operator sequence
    2. Compute canonical form
    3. Classify dynamic behavior
    4. Detect fixed points
    """
    sequence = extract_dominant_sequence(operator_scores)
    canonical, cancellations = canonicalize(sequence)
    classification = classify_fractal(canonical)

    # Check for fixed point
    state = 1
    for op in reversed(canonical):
        state = (state + op) % 10
    has_fixed_point = (state == 1)  # Returns to start

    # Compute orbit length
    orbit_states = {1}
    current = 1
    for _ in range(50):
        for op in reversed(canonical):
            current = (current + op) % 10
        if current in orbit_states:
            break
        orbit_states.add(current)

    return FractalAnalysisResult(
        dominant_sequence=sequence,
        canonical_form=canonical,
        cancellations_detected=cancellations,
        classification=classification,
        orbit_length=len(orbit_states),
        has_fixed_point=has_fixed_point,
    )
