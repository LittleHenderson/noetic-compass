"""A-2: CJT circuit-view renderer.

Deterministic markdown/ASCII renderer for ``CjtCircuitDiagnostic`` and
``CrcReport``. This is the text core of the Audit Console "circuit panel": it
turns "the AI was biased" into a readable Cause → [Bias] → Effect flow with the
operating region, gain, gate outcome, and evidence links.

Pure formatting — it renders existing evidence and makes no new claim.
"""

from __future__ import annotations

from cas_forex.crc_linter import CrcReport, CrcSeverity
from cas_forex.schemas.cjt import CjtCircuitDiagnostic, CjtObservation, CjtRegion

_REGION_GLYPH = {
    CjtRegion.CUTOFF: "○ cutoff",
    CjtRegion.ACTIVE: "● active",
    CjtRegion.SATURATION: "▣ saturation",
    CjtRegion.BREAKDOWN: "⚡ breakdown",
    CjtRegion.UNKNOWN: "? unknown",
}

_SEVERITY_GLYPH = {
    CrcSeverity.ERROR: "✗ ERROR",
    CrcSeverity.WARN: "△ WARN",
    CrcSeverity.INFO: "· INFO",
}


def _beta_text(observation: CjtObservation) -> str:
    if observation.beta_estimate is None:
        return "β=—"
    return f"β={observation.beta_estimate:g}"


def render_observation_line(observation: CjtObservation) -> str:
    """One-line ASCII flow: cause ──[bias]──▶ effect (region, β)."""

    region = _REGION_GLYPH.get(observation.region, observation.region.value)
    return (
        f"{observation.cause_ref} ──[{observation.bias_ref}]──▶ "
        f"{observation.effect_ref}   ({region}, {_beta_text(observation)})"
    )


def render_diagnostic(diagnostic: CjtCircuitDiagnostic) -> str:
    """Render a CJT circuit diagnostic as markdown."""

    lines: list[str] = []
    lines.append(f"### CJT Circuit Diagnostic — {diagnostic.kind.value}")
    if diagnostic.trace_id:
        lines.append(f"- trace: `{diagnostic.trace_id}`")
    lines.append(f"- overall region: {_REGION_GLYPH.get(diagnostic.overall_region, diagnostic.overall_region.value)}")
    lines.append(f"- gate (claim ceiling): **{diagnostic.claim_ceiling.value}**")
    lines.append("")
    if not diagnostic.observations:
        lines.append("_no observations_")
    for observation in diagnostic.observations:
        lines.append(f"```\n{render_observation_line(observation)}\n```")
        for note in observation.notes:
            lines.append(f"- {note}")
        if observation.evidence_refs:
            refs = ", ".join(f"`{ref}`" for ref in observation.evidence_refs)
            lines.append(f"- evidence: {refs}")
    lines.append("")
    lines.append(
        "_Evidence-only diagnostic: may explain, SUPPRESS, FLAG_FOR_HUMAN_REVIEW, "
        "or LIVE_LOCK. It cannot authorize ACCEPT._"
    )
    return "\n".join(lines)


def render_crc_report(report: CrcReport) -> str:
    """Render a Cognitive Rule Check report as markdown."""

    status = "WELL-FORMED ✓" if report.well_formed else "MALFORMED ✗"
    lines: list[str] = []
    lines.append(f"### Cognitive Rule Check — {report.circuit_name}")
    lines.append(
        f"- result: **{status}** "
        f"({report.error_count} error(s), {report.warn_count} warning(s))"
    )
    lines.append("")
    if not report.findings:
        lines.append("_no findings — circuit is structurally clean_")
    else:
        lines.append("| code | severity | subject | message |")
        lines.append("|---|---|---|---|")
        for finding in report.findings:
            sev = _SEVERITY_GLYPH.get(finding.severity, finding.severity.value)
            message = finding.message.replace("|", "\\|")
            subject = finding.subject.replace("|", "\\|")
            lines.append(f"| {finding.code} | {sev} | {subject} | {message} |")
    lines.append("")
    lines.append(f"_{report.claim_note}_")
    return "\n".join(lines)
