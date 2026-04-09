"""AI-powered natural language interpretation of CAS assessment results.

Post-pipeline step that generates a 3-section executive briefing:
THE BOTTOM LINE, WHAT WE FOUND, WHAT WE RECOMMEND.
"""

from __future__ import annotations

import logging
import re

from api.llm_connectors.base import BaseLLMConnector
from api.models import InterpretationSchema

logger = logging.getLogger("noetic.interpreter")

OPERATOR_NAMES = [
    "Identity", "Reflection", "Abstraction", "Concretization",
    "Integration", "Differentiation", "Unification", "Transformation",
    "Expansion", "Contraction",
]

DOMAIN_NAMES = ["Principled", "Cognitive", "Evaluative", "Operational"]

DRIVE_NAMES = [
    "Unity", "Wisdom", "Vitality", "Connection",
    "Agency", "Structure", "Purpose",
]

INVERSION_AXIS_NAMES = [
    "Operator (N)", "Domain (W)", "Drive (F)", "State (E)",
    "Sub-Drive (S)", "Pathway (A)", "Compound (P)",
]

DWP_STAGE_LABELS = {
    "desire": [(0.0, "Dormant"), (0.2, "Awakening"), (0.5, "Peak"), (0.7, "Fading")],
    "wisdom": [(0.0, "Unaware"), (0.2, "Learning"), (0.5, "Knowing"), (0.7, "Mastering")],
    "power": [(0.0, "Nascent"), (0.2, "Developing"), (0.5, "Capable"), (0.7, "Mastery")],
}


def _classify_stage(score: float, stages: list[tuple[float, str]]) -> str:
    """Classify a score into its D/W/P stage label."""
    label = stages[0][1]
    for threshold, name in stages:
        if score >= threshold:
            label = name
    return label


def describe_rpm_stages(drive_scores: list[float], rpm_completeness: float) -> str:
    """Generate plain-English description of RPM stage status."""
    if len(drive_scores) < 7:
        return ""
    # Average across drives for a summary stage assessment
    avg = sum(drive_scores) / len(drive_scores)
    d_stage = _classify_stage(avg, DWP_STAGE_LABELS["desire"])
    w_stage = _classify_stage(avg * 0.9, DWP_STAGE_LABELS["wisdom"])
    p_stage = _classify_stage(avg * 0.8, DWP_STAGE_LABELS["power"])

    parts = []
    parts.append(f"{d_stage}-level motivational activation")
    parts.append(f"{w_stage}-level knowledge integration")
    parts.append(f"{p_stage}-level execution capability")
    return f"RPM Stage Assessment: {', '.join(parts)}."


INTERPRETER_SYSTEM_PROMPT = (
    "You are a senior AI psychology consultant presenting assessment findings "
    "to a non-technical executive. You never use mathematical terminology. "
    "You speak like a trusted advisor in a boardroom. Given the following CAS "
    "assessment scores, write a clear, actionable briefing.\n\n"
    "Format your response EXACTLY as follows:\n"
    "THE BOTTOM LINE: <one paragraph summary>\n"
    "WHAT WE FOUND:\n- <finding 1>\n- <finding 2>\n- <finding 3>\n"
    "WHAT WE RECOMMEND:\n- <recommendation 1>\n- <recommendation 2>\n- <recommendation 3>"
)


def build_interpretation_prompt(
    *,
    composite: float,
    certification: str,
    operator_scores: list[float],
    domain_averages: list[float],
    drive_scores: list[float],
    inversion_axis_scores: list[float],
    rpm_completeness: float,
    broken_chains: list[str],
) -> str:
    """Serialize assessment data into a structured text prompt for the LLM."""
    lines = [
        f"NCCS Composite Score: {composite:.1f}/100",
        f"Certification Level: {certification}",
        "",
        "Cognitive Operator Scores (0-1 scale):",
    ]
    for i, score in enumerate(operator_scores):
        name = OPERATOR_NAMES[i] if i < len(OPERATOR_NAMES) else f"CO-{i}"
        lines.append(f"  CO-{i} {name}: {score:.3f}")

    lines.append("")
    lines.append("Processing Domain Averages:")
    for i, avg in enumerate(domain_averages):
        name = DOMAIN_NAMES[i] if i < len(DOMAIN_NAMES) else f"Domain-{i}"
        lines.append(f"  {name}: {avg:.3f}")

    lines.append("")
    lines.append("Core Drive Scores (0-1 scale):")
    for i, score in enumerate(drive_scores):
        name = DRIVE_NAMES[i] if i < len(DRIVE_NAMES) else f"F{i+1}"
        lines.append(f"  {name}: {score:.3f}")

    lines.append("")
    lines.append(f"RPM Completeness: {rpm_completeness:.1%}")
    if broken_chains:
        lines.append(f"Broken RPM Chains: {', '.join(broken_chains)}")
    else:
        lines.append("All RPM chains intact.")

    # D/W/P Stage Assessment
    stage_desc = describe_rpm_stages(drive_scores, rpm_completeness)
    if stage_desc:
        lines.append(stage_desc)

    lines.append("")
    lines.append("Inversion Axis Scores (0-1, higher = more resistant):")
    for i, score in enumerate(inversion_axis_scores):
        name = INVERSION_AXIS_NAMES[i] if i < len(INVERSION_AXIS_NAMES) else f"Axis-{i}"
        lines.append(f"  {name}: {score:.3f}")

    return "\n".join(lines)


def parse_interpretation(text: str) -> InterpretationSchema:
    """Parse the 3-section briefing from LLM output.

    Uses regex to extract sections with fallback defaults if parsing fails.
    """
    bottom_line = ""
    findings: list[str] = []
    recommendations: list[str] = []

    # Extract THE BOTTOM LINE
    bl_match = re.search(
        r"THE BOTTOM LINE[:\s]*(.+?)(?=WHAT WE FOUND|$)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if bl_match:
        bottom_line = bl_match.group(1).strip()

    # Extract WHAT WE FOUND
    wf_match = re.search(
        r"WHAT WE FOUND[:\s]*(.+?)(?=WHAT WE RECOMMEND|$)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if wf_match:
        section = wf_match.group(1).strip()
        findings = [
            line.lstrip("- ").strip()
            for line in section.split("\n")
            if line.strip() and line.strip() != "-"
        ]

    # Extract WHAT WE RECOMMEND
    wr_match = re.search(
        r"WHAT WE RECOMMEND[:\s]*(.+?)$",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if wr_match:
        section = wr_match.group(1).strip()
        recommendations = [
            line.lstrip("- ").strip()
            for line in section.split("\n")
            if line.strip() and line.strip() != "-"
        ]

    # Fallback defaults
    if not bottom_line:
        bottom_line = "Assessment completed. Review the detailed scores for insights."
    if not findings:
        findings = ["Assessment data has been processed. See technical details for specifics."]
    if not recommendations:
        recommendations = ["Review the full technical report for detailed recommendations."]

    return InterpretationSchema(
        bottom_line=bottom_line,
        findings=findings,
        recommendations=recommendations,
    )


async def generate_interpretation(
    connector: BaseLLMConnector,
    *,
    composite: float,
    certification: str,
    operator_scores: list[float],
    domain_averages: list[float],
    drive_scores: list[float],
    inversion_axis_scores: list[float],
    rpm_completeness: float,
    broken_chains: list[str],
) -> InterpretationSchema | None:
    """Generate an AI interpretation of assessment results.

    Returns None on any exception to avoid blocking the pipeline.
    """
    try:
        prompt = build_interpretation_prompt(
            composite=composite,
            certification=certification,
            operator_scores=operator_scores,
            domain_averages=domain_averages,
            drive_scores=drive_scores,
            inversion_axis_scores=inversion_axis_scores,
            rpm_completeness=rpm_completeness,
            broken_chains=broken_chains,
        )
        response = await connector.generate(prompt, system_prompt=INTERPRETER_SYSTEM_PROMPT)
        return parse_interpretation(response.text)
    except Exception:
        logger.exception("Interpretation generation failed; returning None")
        return None
