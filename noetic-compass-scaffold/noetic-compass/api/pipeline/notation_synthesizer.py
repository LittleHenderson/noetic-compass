"""Real-time CAS notation synthesizer.

Derives a CAS expression from actual pipeline computation results, then
validates it through the compiler.  The notation is a formal description
of what the system *found*, not a prediction of what it expected to find.

Inputs consumed (all produced by earlier pipeline stages):
  - operator_scores       10 floats in [0, 1]
  - raw_scores_0_to_10    10 floats in [0, 10]
  - domain_averages       4  floats  [P, C, E, O]
  - drive_chains          7  lists of [D, W, P] floats
  - a0_score              float
  - rpm_completeness      float
  - inversion_axis_scores 7  floats in [0, 1]
  - inversion_evidence    list of per-axis evidence dicts
  - fractal_sequence      list of ints (dominant operator sequence)
  - fractal_classification str

Output: a ``SynthesizedNotation`` containing the source expression, the
compiler artifact, and provenance metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.notation.compiler import (
    compile_expression,
    CompilationArtifact,
    OPERATOR_NAMES,
    DOMAIN_NAMES,
    DRIVE_NAMES,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOMAIN_CODES = ("P", "C", "E", "O")
DRIVE_COUNT = 7

# An operator must score above this (on the 0-10 scale) to be "significant"
OPERATOR_SIGNIFICANCE_THRESHOLD = 5.0

# A domain average must be above this (normalised 0-1) to qualify
DOMAIN_SIGNIFICANCE_THRESHOLD = 0.45

# A drive chain stage must be above this to count as "satisfied"
DRIVE_CHAIN_STAGE_THRESHOLD = 0.5

# An inversion axis must score *below* this to be flagged (low = vulnerable)
INVERSION_FLAG_THRESHOLD = 0.5

# Maximum operators to include so the expression stays readable
MAX_OPERATORS = 4

# Maximum drives to include
MAX_DRIVES = 3

INVERSION_AXIS_NAMES = ("N", "W", "F", "E", "S", "A", "P")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class SynthesizedNotation:
    """The compiler-validated CAS expression derived from pipeline results."""
    source: str
    valid: bool
    english: str
    compiler_artifact: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core synthesis logic
# ---------------------------------------------------------------------------

def _pick_significant_operators(
    raw_scores: list[float],
) -> list[int]:
    """Return indices of the most significant operators, ordered by score."""
    scored = [
        (idx, score)
        for idx, score in enumerate(raw_scores)
        if score >= OPERATOR_SIGNIFICANCE_THRESHOLD
    ]
    scored.sort(key=lambda pair: -pair[1])
    return [idx for idx, _ in scored[:MAX_OPERATORS]]


def _pick_significant_domains(domain_averages: list[float]) -> list[str]:
    """Return domain codes for domains above the significance threshold."""
    return [
        DOMAIN_CODES[idx]
        for idx, avg in enumerate(domain_averages)
        if avg >= DOMAIN_SIGNIFICANCE_THRESHOLD and idx < len(DOMAIN_CODES)
    ]


def _pick_significant_drives(
    drive_chains: list[list[float]],
    a0_score: float,
) -> tuple[list[int], list[int]]:
    """Return (rpm_drives, plain_drives).

    rpm_drives: drives whose full D->W->P chain is intact (all stages pass).
    plain_drives: drives that are active but have a broken chain.
    """
    rpm_drives: list[int] = []
    plain_drives: list[int] = []

    for drive_idx, chain in enumerate(drive_chains):
        if drive_idx >= DRIVE_COUNT:
            break

        # A chain is "intact" if A0 + all three stages pass
        chain_intact = a0_score >= DRIVE_CHAIN_STAGE_THRESHOLD and all(
            stage >= DRIVE_CHAIN_STAGE_THRESHOLD for stage in chain
        )
        # A drive is "active" if at least the first stage (Dormant/D) passes
        first_stage_active = len(chain) > 0 and chain[0] >= DRIVE_CHAIN_STAGE_THRESHOLD

        if chain_intact:
            rpm_drives.append(drive_idx)
        elif first_stage_active:
            plain_drives.append(drive_idx)

    # Cap total drives to keep expression readable
    rpm_drives = rpm_drives[:MAX_DRIVES]
    remaining_slots = MAX_DRIVES - len(rpm_drives)
    plain_drives = plain_drives[:remaining_slots]

    return rpm_drives, plain_drives


def _pick_flagged_inversions(axis_scores: list[float]) -> list[str]:
    """Return axis names for inversions that were detected (low resistance)."""
    flagged = []
    for idx, score in enumerate(axis_scores):
        if idx < len(INVERSION_AXIS_NAMES) and score < INVERSION_FLAG_THRESHOLD:
            flagged.append(INVERSION_AXIS_NAMES[idx])
    return flagged


def _build_expression(
    operators: list[int],
    domains: list[str],
    rpm_drives: list[int],
    plain_drives: list[int],
    fractal_sequence: list[int] | None,
    fractal_classification: str | None,
) -> str:
    """Assemble a compiler-valid CAS expression from extracted components."""
    statements: list[str] = []

    # 1. Operator-domain state expressions (the core finding)
    if operators and domains:
        # Pair each significant operator with the strongest domain
        # to get precise state expressions like CO-3^P
        state_exprs = []
        for op in operators:
            for dom in domains:
                state_exprs.append(f"CO-{op}^{dom}")
        statements.append(" * ".join(state_exprs) if len(state_exprs) <= 2 else " ".join(state_exprs))
    elif operators:
        statements.append(" ".join(f"CO-{op}" for op in operators))

    # 2. RPM-wrapped drives (complete prerequisite chains)
    for drive_idx in rpm_drives:
        statements.append(f"RPM(F{drive_idx + 1})")

    # 3. Plain drives (active but incomplete chain)
    for drive_idx in plain_drives:
        statements.append(f"F{drive_idx + 1}")

    # 4. Fractal sequence if non-trivial
    if (
        fractal_sequence
        and len(fractal_sequence) >= 2
        and fractal_classification not in (None, "neutral")
    ):
        seq_str = ":".join(str(op) for op in fractal_sequence)
        statements.append(f"Phi<{seq_str}>")

    # Join with semicolons for multi-statement programs
    if len(statements) <= 1:
        return statements[0] if statements else ""

    # If we have states + drives, keep them on one line with spaces
    # Only use semicolons for truly separate concepts (e.g., fractal is separate)
    main_parts = []
    fractal_part = None

    for stmt in statements:
        if stmt.startswith("Phi<"):
            fractal_part = stmt
        else:
            main_parts.append(stmt)

    result = " ".join(main_parts)
    if fractal_part:
        result = f"{result}; {fractal_part}"

    return result


def synthesize_notation(
    *,
    operator_scores: list[float],
    raw_scores_0_to_10: list[float],
    domain_averages: list[float],
    drive_chains: list[list[float]],
    a0_score: float,
    rpm_completeness: float,
    inversion_axis_scores: list[float],
    fractal_sequence: list[int] | None = None,
    fractal_classification: str | None = None,
) -> SynthesizedNotation:
    """Synthesize a CAS notation expression from real pipeline results.

    This is the core function: it reads what the pipeline actually computed
    and produces a compiler-validated formal expression.
    """
    # Extract significant components from the scores
    operators = _pick_significant_operators(raw_scores_0_to_10)
    domains = _pick_significant_domains(domain_averages)
    rpm_drives, plain_drives = _pick_significant_drives(drive_chains, a0_score)
    flagged_inversions = _pick_flagged_inversions(inversion_axis_scores)

    # Build the expression
    source = _build_expression(
        operators=operators,
        domains=domains,
        rpm_drives=rpm_drives,
        plain_drives=plain_drives,
        fractal_sequence=fractal_sequence,
        fractal_classification=fractal_classification,
    )

    if not source.strip():
        return SynthesizedNotation(
            source="",
            valid=False,
            english="No significant cognitive patterns detected",
            provenance={
                "operators_found": 0,
                "domains_found": 0,
                "drives_found": 0,
                "reason": "all scores below significance thresholds",
            },
        )

    # Compile through the real compiler
    artifact: CompilationArtifact = compile_expression(source)

    # If compiler rejects it, try a simplified fallback (operators only)
    if not artifact.valid and operators:
        fallback = " ".join(f"CO-{op}" for op in operators)
        artifact = compile_expression(fallback)
        if artifact.valid:
            source = fallback

    # Build English directly from the extracted components (the parser
    # chokes on semicolons that the compiler handles fine, so we render
    # English ourselves from the semantic components we already have).
    english = _render_english(operators, domains, rpm_drives, plain_drives, fractal_classification)

    provenance = {
        "operators_found": len(operators),
        "operators": [f"CO-{op}" for op in operators],
        "domains_found": len(domains),
        "domains": domains,
        "rpm_drives": [f"F{d + 1}" for d in rpm_drives],
        "plain_drives": [f"F{d + 1}" for d in plain_drives],
        "flagged_inversions": flagged_inversions,
        "fractal_classification": fractal_classification,
        "rpm_completeness": round(rpm_completeness, 4),
        "compiler_engine": artifact.engine,
        "compiler_valid": artifact.valid,
        "compiler_error": artifact.error,
    }

    return SynthesizedNotation(
        source=source,
        valid=artifact.valid,
        english=english,
        compiler_artifact=artifact.to_dict() if artifact.valid else {},
        provenance=provenance,
    )


def _render_english(
    operators: list[int],
    domains: list[str],
    rpm_drives: list[int],
    plain_drives: list[int],
    fractal_classification: str | None,
) -> str:
    """Build a plain-English description from the semantic components."""
    parts: list[str] = []

    if operators:
        op_labels = []
        for op in operators:
            name = OPERATOR_NAMES[op] if op < len(OPERATOR_NAMES) else f"CO-{op}"
            op_labels.append(f"CO-{op} ({name})")
        parts.append(" and ".join(op_labels))

    if domains:
        dom_labels = [f"{DOMAIN_NAMES.get(d, d)}" for d in domains]
        parts.append("in the " + " and ".join(dom_labels) + (" Domains" if len(dom_labels) > 1 else " Domain"))

    drive_labels: list[str] = []
    for d in rpm_drives:
        name = DRIVE_NAMES.get(d + 1, f"F{d + 1}")
        drive_labels.append(f"F{d + 1} ({name}, RPM chain intact)")
    for d in plain_drives:
        name = DRIVE_NAMES.get(d + 1, f"F{d + 1}")
        drive_labels.append(f"F{d + 1} ({name})")
    if drive_labels:
        parts.append("grounded in " + ", ".join(drive_labels))

    if fractal_classification and fractal_classification != "neutral":
        parts.append(f"with {fractal_classification} fractal dynamics")

    return " ".join(parts) if parts else "No significant cognitive patterns detected"
