"""CAS Harness EvidencePacket v1 schema helpers.

The schema is intentionally plain dataclass/dict Python so it can be consumed
by scripts, API routes, or a dashboard without introducing a new dependency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "cas_harness_evidence_packet_v1"

VERIFICATION_MODES = {
    "HIGH_PRECISION",
    "BALANCED",
    "MAX_COVERAGE_TRIAGE",
}

READINESS_ACTIONS = {
    "allow",
    "caveat",
    "constrain",
    "suppress",
}

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "trace_id",
    "created_at",
    "model",
    "provenance",
    "readout",
    "diagnostics",
    "verification",
    "generation_readiness",
    "controls",
    "conditioning",
    "claim_badges",
    "caveats",
    "rejected_claims",
    "boundary",
}


class EvidencePacketValidationError(ValueError):
    """Raised when an EvidencePacket dict violates the v1 schema."""


def _path(packet: dict[str, Any], dotted: str) -> Any:
    current: Any = packet
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def validate_evidence_packet(packet: dict[str, Any]) -> bool:
    """Validate a CAS Harness EvidencePacket v1 dict.

    The validator checks structural completeness plus the product-critical
    readiness invariants established by Stage 20B.
    """
    errors: list[str] = []

    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(packet))
    if missing:
        errors.append(f"missing top-level keys: {missing}")

    if packet.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {SCHEMA_VERSION!r}, got {packet.get('schema_version')!r}"
        )

    mode = _path(packet, "verification.mode")
    if mode not in VERIFICATION_MODES:
        errors.append(f"verification.mode must be one of {sorted(VERIFICATION_MODES)}")

    action = _path(packet, "generation_readiness.generation_readiness")
    if action not in READINESS_ACTIONS:
        errors.append(
            "generation_readiness.generation_readiness must be one of "
            f"{sorted(READINESS_ACTIONS)}"
        )

    for key in (
        "model.name",
        "model.revision",
        "provenance.code_commit",
        "provenance.fixture_sha256",
        "provenance.activation_sha256",
        "readout.axis",
        "readout.label",
        "verification.mode",
        "generation_readiness.policy_version",
    ):
        value = _path(packet, key)
        if value in (None, ""):
            errors.append(f"{key} is required")

    accepted = _path(packet, "verification.accepted")
    confidence_tier = _path(packet, "verification.confidence_tier")
    suppression_reasons = _path(packet, "verification.suppression_reasons")

    if accepted is False and mode in {"HIGH_PRECISION", "BALANCED"} and action != "suppress":
        errors.append("rejected HIGH_PRECISION/BALANCED packets must suppress")
    if accepted is False and mode == "MAX_COVERAGE_TRIAGE" and action != "constrain":
        errors.append("rejected MAX_COVERAGE_TRIAGE packets must constrain")
    if accepted is False and not suppression_reasons:
        errors.append("rejected packets must include suppression_reasons")
    if accepted is True and confidence_tier == "medium" and action != "caveat":
        errors.append("medium-confidence accepted packets must caveat")

    caveats = packet.get("caveats")
    if not isinstance(caveats, list) or not caveats:
        errors.append("caveats must be a non-empty list")

    rejected_claims = packet.get("rejected_claims")
    if not isinstance(rejected_claims, list) or "exact_sentence_forcing_in_free_form_decoding" not in rejected_claims:
        errors.append("rejected_claims must include exact_sentence_forcing_in_free_form_decoding")

    source_reports = _path(packet, "provenance.source_reports")
    if not isinstance(source_reports, list) or not source_reports:
        errors.append("provenance.source_reports must be a non-empty list")

    if errors:
        raise EvidencePacketValidationError("; ".join(errors))
    return True


def render_evidence_packet_markdown(packet: dict[str, Any]) -> str:
    """Render a reviewer-readable Markdown summary for one packet."""
    validate_evidence_packet(packet)
    verification = packet["verification"]
    readiness = packet["generation_readiness"]
    readout = packet["readout"]
    model = packet["model"]
    provenance = packet["provenance"]
    diagnostics = packet["diagnostics"]
    controls = packet["controls"]
    conditioning = packet["conditioning"]

    lines = [
        f"# Evidence Packet: {packet['trace_id']}",
        "",
        f"Status: `{readiness['generation_readiness']}`",
        "",
        "## Boundary",
        "",
        packet["boundary"],
        "",
        "## Model",
        "",
        f"- Name: `{model['name']}`",
        f"- Family: `{model.get('family', 'unknown')}`",
        f"- Revision: `{model['revision']}`",
        "",
        "## Provenance",
        "",
        f"- Code commit: `{provenance['code_commit']}`",
        f"- Fixture SHA-256: `{provenance['fixture_sha256']}`",
        f"- Activation SHA-256: `{provenance['activation_sha256']}`",
        f"- Source reports: `{', '.join(provenance['source_reports'])}`",
        "",
        "## Readout",
        "",
        f"- Axis: `{readout['axis']}`",
        f"- Layer: `{readout['layer']}`",
        f"- Position: `{readout['position']}`",
        f"- Label: `{readout['label']}`",
        f"- Confidence tier: `{verification['confidence_tier']}`",
        "",
        "## Verification",
        "",
        f"- Mode: `{verification['mode']}`",
        f"- Accepted: `{verification['accepted']}`",
        f"- Suppression reasons: `{', '.join(verification['suppression_reasons']) or 'none'}`",
        f"- Mode profile: `{json.dumps(verification['mode_profile'], sort_keys=True)}`",
        "",
        "## Generation Readiness",
        "",
        f"- Policy: `{readiness['generation_readiness']}`",
        f"- Risk score: `{readiness['risk_score']}`",
        f"- Reasons: `{', '.join(readiness['reasons'])}`",
        f"- Recommended mode: `{readiness['recommended_mode']}`",
        "",
        "## Diagnostics",
        "",
        f"- Lacunarity: `{diagnostics.get('lacunarity')}`",
        f"- Blindspot flags: `{', '.join(diagnostics.get('blindspot_flags', [])) or 'none'}`",
        "",
        "## Controls",
        "",
        f"- Text baseline: `{controls.get('text_baseline')}`",
        f"- Metadata baseline: `{controls.get('metadata_baseline')}`",
        f"- Random ablation: `{controls.get('random_ablation')}`",
        f"- Raw-symbol delta: `{controls.get('raw_symbol_delta')}`",
        "",
        "## Conditioning",
        "",
        f"- Probe-readable delta: `{conditioning.get('probe_readable_delta')}`",
        f"- Partner margin: `{conditioning.get('partner_margin')}`",
        f"- p-value: `{conditioning.get('p_value')}`",
        "",
        "## Caveats",
        "",
    ]
    lines.extend(f"- {item}" for item in packet["caveats"])
    lines.extend([
        "",
        "## Rejected Claims",
        "",
    ])
    lines.extend(f"- `{item}`" for item in packet["rejected_claims"])
    lines.append("")
    return "\n".join(lines)


def write_evidence_packet(packet: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Validate and write one packet as JSON and Markdown."""
    validate_evidence_packet(packet)
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_id = packet["trace_id"]
    json_path = output_dir / f"{trace_id}.json"
    md_path = output_dir / f"{trace_id}.md"
    json_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_evidence_packet_markdown(packet), encoding="utf-8")
    return json_path, md_path
