"""CAS Notation Renderer — renders parsed notation as plain English or HTML.

Transforms ParseResult into human-readable text or color-coded HTML tokens.
"""

from __future__ import annotations

from .parser import ParseResult, OPERATOR_NAMES, DOMAIN_NAMES, DRIVE_NAMES


def render_plain_english(result: ParseResult) -> str:
    """Render parsed CAS notation as plain English."""
    if not result.valid:
        return f"Invalid notation: {result.error}"

    parts: list[str] = []

    # Operators
    for op_idx in result.operators:
        name = OPERATOR_NAMES[op_idx] if op_idx < len(OPERATOR_NAMES) else f"CO-{op_idx}"
        parts.append(f"CO-{op_idx} ({name})")

    # Domains
    domain_parts = []
    for d in result.domains:
        domain_parts.append(f"{DOMAIN_NAMES.get(d, d)} Domain")

    # Drives
    drive_parts = []
    for d_idx in result.drives:
        name = DRIVE_NAMES[d_idx] if d_idx < len(DRIVE_NAMES) else f"F{d_idx + 1}"
        drive_parts.append(f"F{d_idx + 1} ({name})")

    # Build description
    desc_parts: list[str] = []
    if parts:
        desc_parts.append(" and ".join(parts))
    if domain_parts:
        desc_parts.append("in the " + " and ".join(domain_parts))
    if drive_parts:
        desc_parts.append("grounded in " + " and ".join(drive_parts))
    if result.is_rpm:
        desc_parts.append("(RPM prerequisite chain)")
    if result.fractal:
        indices = ":".join(str(i) for i in result.fractal)
        desc_parts.append(f"Cognitive Fractal sequence [{indices}]")

    return " ".join(desc_parts) if desc_parts else "Empty notation"


def render_assessment_config(result: ParseResult) -> dict:
    """Convert parsed notation into an assessment configuration.

    Returns a dict specifying which COs, Domains, and Drives to test.
    """
    return {
        "target_operators": result.operators,
        "target_domains": result.domains,
        "target_drives": result.drives,
        "is_rpm_test": result.is_rpm,
        "fractal_sequence": result.fractal,
    }
