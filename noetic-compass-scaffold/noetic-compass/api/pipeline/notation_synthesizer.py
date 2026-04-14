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


def _pick_significant_domains(
    domain_averages: list[float],
    *,
    need_fallback: bool = False,
) -> list[str]:
    """Return domain codes for domains above the significance threshold.

    When need_fallback is True and no domain passes threshold, returns the
    strongest domain so notation always has proper CO-N^D form.
    """
    result = [
        DOMAIN_CODES[idx]
        for idx, avg in enumerate(domain_averages)
        if avg >= DOMAIN_SIGNIFICANCE_THRESHOLD and idx < len(DOMAIN_CODES)
    ]
    if not result and need_fallback:
        best_idx = max(range(len(domain_averages)), key=lambda i: domain_averages[i])
        if domain_averages[best_idx] > 0:
            result = [DOMAIN_CODES[best_idx]]
    return result


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


_INVOLUTION_PAIRS = {(2, 3), (3, 2), (5, 6), (6, 5), (8, 9), (9, 8)}


def _build_expression(
    operators: list[int],
    domains: list[str],
    rpm_drives: list[int],
    plain_drives: list[int],
    fractal_sequence: list[int] | None,
    fractal_classification: str | None,
    flagged_inversions: list[str] | None = None,
) -> str:
    """Assemble a compiler-valid CAS expression using all 5 generative operations.

    The five CAS compositional operations:
    - × (TIMES)   : algebraic — operators composing in the same domain
    - ÷ (DIVIDE)  : algebraic — involution pairs showing opposition/resolution
    - ∘ (CIRC)    : algebraic — fractal operator sequence composition
    - + (PLUS)    : syntactic — co-present states across domains
    - - (MINUS)   : syntactic — inversions subtracting from expected state
    """
    if not operators:
        parts: list[str] = []
        for d in rpm_drives:
            parts.append(f"RPM(F{d + 1})")
        for d in plain_drives:
            parts.append(f"F{d + 1}")
        return " ".join(parts)

    flagged = flagged_inversions or []

    # Assign primary drive subscript to the lead state
    primary_drive = rpm_drives[0] if rpm_drives else (plain_drives[0] if plain_drives else None)

    # Separate involution pairs from non-paired operators for ÷ expressions
    involution_exprs: list[str] = []
    remaining_ops = list(operators)
    used_in_division: set[int] = set()

    for a_idx, a_op in enumerate(operators):
        if a_op in used_in_division:
            continue
        for b_op in operators[a_idx + 1:]:
            if b_op in used_in_division:
                continue
            if (a_op, b_op) in _INVOLUTION_PAIRS:
                # Division: involution pair shows opposition → resolves to CO-0
                dom = domains[0] if domains else "P"
                involution_exprs.append(f"CO-{a_op}^{dom} / CO-{b_op}^{dom}")
                used_in_division.add(a_op)
                used_in_division.add(b_op)
                break

    remaining_ops = [op for op in remaining_ops if op not in used_in_division]

    # Group remaining operators by domain for × (multiplication)
    domain_groups: dict[str, list[str]] = {}
    for dom in domains:
        group_ops = []
        for op in remaining_ops:
            state = f"CO-{op}^{dom}"
            if primary_drive is not None and not group_ops and not involution_exprs:
                state = f"CO-{op}^{dom}_{{F{primary_drive + 1}}}"
                primary_drive = None
            group_ops.append(state)
        if group_ops:
            domain_groups[dom] = group_ops

    # Build per-domain expressions: × within domain
    domain_exprs: list[str] = []
    for dom in ("P", "C", "E", "O"):
        if dom in domain_groups:
            ops = domain_groups[dom]
            if len(ops) == 1:
                domain_exprs.append(ops[0])
            else:
                domain_exprs.append(" * ".join(ops))

    # Build a multi-statement CAS program where each statement uses
    # the appropriate algebraic operation. Joined by ; (semicolons).
    statements: list[str] = []

    # Statement 1: × (TIMES) — operators multiplied within primary domain
    if domain_exprs:
        statements.append(domain_exprs[0])

    # Statement 2: → (ARROW) — domain descent to secondary domain
    if len(domain_exprs) >= 2:
        # Pick one operator from each domain for the descent relation
        primary_dom = list(domain_groups.keys())[0]
        secondary_dom = list(domain_groups.keys())[1]
        first_op = operators[0]
        statements.append(f"CO-{first_op}^{primary_dom} -> CO-{first_op}^{secondary_dom}")

    # Statement 3: ÷ (DIVIDE) — involution pairs showing opposition
    for expr in involution_exprs:
        statements.append(expr)

    # Statement 4: - (MINUS) — inversion distortions
    # Construct same-domain subtraction pairs for each flagged axis
    inversion_map = {
        "N": ("CO-0", "P"),  # Operator axis
        "W": ("CO-1", "C"),  # Domain axis
        "F": ("CO-4", "E"),  # Drive axis
        "E": ("CO-7", "E"),  # State axis
        "S": ("CO-2", "O"),  # Sub-drive axis
        "A": ("CO-8", "O"),  # Pathway axis
        "P": ("CO-5", "P"),  # Compound axis
    }
    for axis in flagged:
        inv = inversion_map.get(axis)
        if inv:
            op_str, dom = inv
            # Subtract inverted operator from normal state in same domain
            inv_op = inv[0].replace("CO-", "")
            normal_idx = int(inv_op)
            inv_partner = {2: 3, 3: 2, 5: 6, 6: 5, 8: 9, 9: 8}.get(normal_idx, (normal_idx + 5) % 10)
            statements.append(f"CO-{normal_idx}^{dom} - CO-{inv_partner}^{dom}")

    # Statement 5+: RPM drives and plain drives
    drive_parts: list[str] = []
    for d in rpm_drives:
        drive_parts.append(f"RPM(F{d + 1})")
    for d in plain_drives:
        drive_parts.append(f"F{d + 1}")
    if drive_parts:
        statements.append(" ".join(drive_parts))

    # Extra domain expressions (3rd, 4th domain)
    for expr in domain_exprs[2:]:
        statements.append(expr)

    # ∘ (CIRC): fractal operator sequence composition
    if (
        fractal_sequence
        and len(fractal_sequence) >= 2
        and fractal_classification not in (None, "neutral")
    ):
        if len(fractal_sequence) <= 3:
            circ_parts = [f"CO-{op}" for op in fractal_sequence]
            statements.append(" \u2218 ".join(circ_parts))
        else:
            seq_str = ":".join(str(op) for op in fractal_sequence)
            statements.append(f"Phi<{seq_str}>")

    return "; ".join(statements)


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
    domains = _pick_significant_domains(
        domain_averages,
        need_fallback=len(operators) > 0,
    )
    rpm_drives, plain_drives = _pick_significant_drives(drive_chains, a0_score)
    flagged_inversions = _pick_flagged_inversions(inversion_axis_scores)

    # Build the expression using all 5 generative operations
    source = _build_expression(
        operators=operators,
        domains=domains,
        rpm_drives=rpm_drives,
        plain_drives=plain_drives,
        fractal_sequence=fractal_sequence,
        fractal_classification=fractal_classification,
        flagged_inversions=flagged_inversions,
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

    # If compiler rejects it, try progressively simpler fallbacks
    if not artifact.valid and operators:
        # Fallback 1: operators with best domain, joined by multiplication
        if domains:
            best_dom = domains[0]
            fallback = " * ".join(f"CO-{op}^{best_dom}" for op in operators)
            artifact = compile_expression(fallback)
            if artifact.valid:
                source = fallback
        # Fallback 2: operators with best domain, space-separated
        if not artifact.valid and domains:
            best_dom = domains[0]
            fallback = " ".join(f"CO-{op}^{best_dom}" for op in operators)
            artifact = compile_expression(fallback)
            if artifact.valid:
                source = fallback
        # Fallback 3: bare operators (last resort)
        if not artifact.valid:
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
