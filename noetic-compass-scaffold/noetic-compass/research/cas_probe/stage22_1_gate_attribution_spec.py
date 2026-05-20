"""Stage 22.1 fine-grained CAS Harness gate attribution spec.

Stage 22 measured the coarse harness stack. Stage 22.1 asks which gates inside
that stack can be attributed from the locked artifacts. The key discipline is
to report unavailable attribution explicitly instead of treating missing
per-row signals as null effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

GateStatus = Literal[
    "measurable_from_locked_artifacts",
    "partially_measurable_from_locked_artifacts",
    "not_measurable_from_locked_artifacts",
    "reference_only",
]


@dataclass(frozen=True)
class GateAttributionSpec:
    gate: str
    status: GateStatus
    source_component: str
    question: str
    measurable_metrics: tuple[str, ...]
    limitation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "status": self.status,
            "source_component": self.source_component,
            "question": self.question,
            "measurable_metrics": list(self.measurable_metrics),
            "limitation": self.limitation,
        }


STAGE22_1_GATES: tuple[GateAttributionSpec, ...] = (
    GateAttributionSpec(
        gate="wrap_output_gate",
        status="reference_only",
        source_component="raw/no-prefix floor and CPL2 likelihood comparator",
        question="How much structure appears before any CAS Harness wrapper is applied?",
        measurable_metrics=("none_margin_mean", "cpl2_delta_vs_none"),
        limitation="The locked artifacts do not contain a live Wrap Output Gate toggle.",
    ),
    GateAttributionSpec(
        gate="ensemble_gate",
        status="measurable_from_locked_artifacts",
        source_component="Stage 19B ensemble_only",
        question="What happens when only readout-position consensus is required?",
        measurable_metrics=("coverage", "accepted_accuracy", "silent_error_rate"),
        limitation="Measured on OLMo/Qwen Stage 19B cross-architecture fixtures.",
    ),
    GateAttributionSpec(
        gate="factor_consistency_gate",
        status="measurable_from_locked_artifacts",
        source_component="Stage 19B factor_consistent",
        question="What does Drive/Register recomposition consistency add over ensemble-only?",
        measurable_metrics=("delta_coverage", "delta_accuracy", "delta_silent_error"),
        limitation="This measures factor consistency, not the whole CAS compiler.",
    ),
    GateAttributionSpec(
        gate="trace_stability_gate",
        status="measurable_from_locked_artifacts",
        source_component="Stage 19B stack minus factor_consistent",
        question="What does trace-stability suppression add over factor consistency?",
        measurable_metrics=("delta_coverage", "delta_accuracy", "delta_silent_error"),
        limitation="Gold labels score the result after the fact; runtime gate remains non-oracle.",
    ),
    GateAttributionSpec(
        gate="mode_selector_gate",
        status="measurable_from_locked_artifacts",
        source_component="Stage 19C mode selector",
        question="How does user-selected mode move precision and coverage?",
        measurable_metrics=("coverage", "accepted_accuracy", "silent_error_rate"),
        limitation="Packages existing Stage 19B components; no fresh hidden-state inference.",
    ),
    GateAttributionSpec(
        gate="generation_readiness_gate",
        status="partially_measurable_from_locked_artifacts",
        source_component="Stage 20B readiness packets",
        question="How does readiness policy convert accept/suppress into allow/caveat/constrain/suppress?",
        measurable_metrics=("useful_output_rate", "suppression_rate", "policy_counts"),
        limitation="Stage 20B validates the Verification Stack path only; neural lacunarity/RPM/inversion signals are absent.",
    ),
    GateAttributionSpec(
        gate="evidence_packet_gate",
        status="measurable_from_locked_artifacts",
        source_component="Stage 21A packet export",
        question="Does the audit surface preserve complete per-trace evidence?",
        measurable_metrics=("packet_completeness_rate", "readiness_action_coverage"),
        limitation="Evidence Packet completeness is auditability, not model accuracy.",
    ),
    GateAttributionSpec(
        gate="rpm_gate",
        status="not_measurable_from_locked_artifacts",
        source_component="not recorded per row in Stage 19/20 locked reports",
        question="Does RPM satisfaction independently improve useful output or suppress unsupported traces?",
        measurable_metrics=(),
        limitation="Stage 20B sample evidence sets rpm_satisfaction to 1.0 placeholders; no attribution possible.",
    ),
    GateAttributionSpec(
        gate="lacunarity_gate",
        status="not_measurable_from_locked_artifacts",
        source_component="not recorded per row in Stage 19/20 locked reports",
        question="Does lacunarity independently flag blind spots beyond ensemble/factor/trace instability?",
        measurable_metrics=(),
        limitation="Stage 20B explicitly says neural lacunarity-head values are not present.",
    ),
    GateAttributionSpec(
        gate="inversion_scan_gate",
        status="not_measurable_from_locked_artifacts",
        source_component="not recorded per row in Stage 19/20 locked reports",
        question="Does inversion scanning independently catch unsupported or structurally inverted cases?",
        measurable_metrics=(),
        limitation="Stage 20B sample evidence sets inversion_flag_count to zero placeholders; no attribution possible.",
    ),
)


def stage22_1_gate_matrix() -> list[dict[str, Any]]:
    return [gate.as_dict() for gate in STAGE22_1_GATES]


def stage22_1_preregistration_payload() -> dict[str, Any]:
    return {
        "schema_version": "stage22_1_gate_attribution_spec_v1",
        "scope": "fine_grained_gate_attribution_from_locked_artifacts",
        "gates": stage22_1_gate_matrix(),
        "required_boundary": (
            "Only gates with per-row or component-level measurements in locked "
            "artifacts may receive numeric attribution. RPM, lacunarity, and "
            "inversion require a fresh Stage 22.2 runner unless per-row signals "
            "are added to the artifact set."
        ),
    }

