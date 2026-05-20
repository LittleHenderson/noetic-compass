"""Stage 22.2 diagnostic-gate instrumentation contract.

Stage 22.1 showed that RPM, lacunarity, and inversion cannot be attributed
from the locked Stage 19/20 artifacts. Stage 22.2 defines the per-row fields a
fresh runner must emit before those gates can be credited, blamed, or removed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

DiagnosticGate = Literal["rpm_gate", "lacunarity_gate", "inversion_scan_gate"]
FieldStatus = Literal["required", "optional"]


@dataclass(frozen=True)
class DiagnosticField:
    name: str
    gate: DiagnosticGate
    status: FieldStatus
    expected_type: str
    purpose: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "gate": self.gate,
            "status": self.status,
            "expected_type": self.expected_type,
            "purpose": self.purpose,
        }


STAGE22_2_REQUIRED_FIELDS: tuple[DiagnosticField, ...] = (
    DiagnosticField(
        "rpm_satisfaction",
        "rpm_gate",
        "required",
        "float in [0, 1]",
        "Scalar runtime RPM-chain satisfaction used by the readiness gate.",
    ),
    DiagnosticField(
        "rpm_gate_decision",
        "rpm_gate",
        "required",
        "allow|caveat|constrain|suppress",
        "Per-row decision attributable specifically to RPM.",
    ),
    DiagnosticField(
        "lacunarity_scores",
        "lacunarity_gate",
        "required",
        "object or numeric vector",
        "Per-row state/fractal/domain/drive/RPM lacunarity values.",
    ),
    DiagnosticField(
        "gap_map_summary",
        "lacunarity_gate",
        "required",
        "object",
        "Compact count/max/mean summary of the per-slot gap map.",
    ),
    DiagnosticField(
        "lacunarity_gate_decision",
        "lacunarity_gate",
        "required",
        "allow|caveat|constrain|suppress",
        "Per-row decision attributable specifically to lacunarity/gap evidence.",
    ),
    DiagnosticField(
        "inversion_axis_scores",
        "inversion_scan_gate",
        "required",
        "array[7] float in [0, 1]",
        "Per-axis inversion-resistance or inversion-risk scores.",
    ),
    DiagnosticField(
        "inversion_flag_count",
        "inversion_scan_gate",
        "required",
        "integer >= 0",
        "Number of inversion axes crossing the configured flag threshold.",
    ),
    DiagnosticField(
        "inversion_gate_decision",
        "inversion_scan_gate",
        "required",
        "allow|caveat|constrain|suppress",
        "Per-row decision attributable specifically to inversion evidence.",
    ),
    DiagnosticField(
        "gate_decisions",
        "rpm_gate",
        "required",
        "object",
        "Merged per-gate decisions for all diagnostic gates, preserving individual attribution.",
    ),
)


def required_field_names() -> tuple[str, ...]:
    return tuple(field.name for field in STAGE22_2_REQUIRED_FIELDS)


def instrumentation_contract() -> dict[str, Any]:
    return {
        "schema_version": "stage22_2_diagnostic_instrumentation_contract_v1",
        "required_fields": [field.as_dict() for field in STAGE22_2_REQUIRED_FIELDS],
        "boundary": (
            "A diagnostic gate may receive numeric attribution only when its "
            "per-row fields are present in the locked artifact. Placeholder "
            "defaults such as rpm_satisfaction=1.0 or max_lacunarity=0.0 are "
            "not evidence of gate behavior."
        ),
    }


def audit_artifact_for_required_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Check whether a locked artifact exposes Stage 22.2 diagnostic fields.

    The audit is intentionally shallow and schema-oriented: it detects whether
    any row-like objects contain the required keys. It does not infer gate
    values from aggregate summaries.
    """
    found = {name: 0 for name in required_field_names()}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for name in found:
                if name in value:
                    found[name] += 1
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    missing = [name for name, count in found.items() if count == 0]
    present = [name for name, count in found.items() if count > 0]
    return {
        "present_fields": present,
        "missing_fields": missing,
        "field_occurrences": found,
        "instrumented": not missing,
    }

