"""Stage 22 CAS Harness ablation specification.

Stage 22 measures the external CAS Harness around frozen open-weight model
artifacts. It does not ablate CAS Native's future inner loop. The goal is to
find which wrapper layers contribute useful decisions, which merely suppress
coverage, and which should be product defaults.

The spec is declarative so runners, Evidence Packets, and docs can share one
mode matrix without copying thresholds by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

HarnessSubject = Literal["cas_harness"]
HarnessMode = Literal[
    "floor_raw_model",
    "cpl2_bridge_only",
    "mode_selector_balanced",
    "mode_selector_high_precision",
    "mode_selector_max_coverage_triage",
    "readiness_balanced",
    "evidence_packet_full",
    "frontier_llm_ceiling",
]


@dataclass(frozen=True)
class HarnessLayerSet:
    """Boolean switches for one external CAS Harness condition."""

    frozen_model_logits: bool
    eta_probe_readout: bool = False
    epsilon_readable_prefix: bool = False
    verification_stack: bool = False
    mode_selector: Literal["OFF", "BALANCED", "HIGH_PRECISION", "MAX_COVERAGE_TRIAGE"] = "OFF"
    generation_readiness_gate: bool = False
    evidence_packet_export: bool = False
    atlas_trace_linkage: bool = False
    external_frontier_model: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "frozen_model_logits": self.frozen_model_logits,
            "eta_probe_readout": self.eta_probe_readout,
            "epsilon_readable_prefix": self.epsilon_readable_prefix,
            "verification_stack": self.verification_stack,
            "mode_selector": self.mode_selector,
            "generation_readiness_gate": self.generation_readiness_gate,
            "evidence_packet_export": self.evidence_packet_export,
            "atlas_trace_linkage": self.atlas_trace_linkage,
            "external_frontier_model": self.external_frontier_model,
        }


@dataclass(frozen=True)
class HarnessMetric:
    """One metric Stage 22 must report for every executable condition."""

    name: str
    direction: Literal["higher_is_better", "lower_is_better", "report_only"]
    rationale: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "direction": self.direction,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class HarnessAblationCondition:
    """One locked Stage 22 condition."""

    mode: HarnessMode
    label: str
    subject: HarnessSubject
    status: Literal["executable_now", "reference_only"]
    layers: HarnessLayerSet
    hypothesis: str
    boundary: str
    required_artifacts: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "label": self.label,
            "subject": self.subject,
            "status": self.status,
            "layers": self.layers.as_dict(),
            "hypothesis": self.hypothesis,
            "boundary": self.boundary,
            "required_artifacts": list(self.required_artifacts),
        }


STAGE22_METRICS: tuple[HarnessMetric, ...] = (
    HarnessMetric(
        "useful_output_rate",
        "higher_is_better",
        "Prevents rewarding a harness that suppresses everything safely.",
    ),
    HarnessMetric(
        "unsupported_output_rate",
        "lower_is_better",
        "Measures hallucinated or unsupported emission after the harness decision.",
    ),
    HarnessMetric(
        "accepted_accuracy",
        "higher_is_better",
        "Precision of accepted per-example decisions when gold labels exist.",
    ),
    HarnessMetric(
        "coverage",
        "higher_is_better",
        "Fraction of examples receiving an accepted or useful constrained decision.",
    ),
    HarnessMetric(
        "suppression_rate",
        "report_only",
        "Interpretable only alongside useful_output_rate.",
    ),
    HarnessMetric(
        "cpl2_delta",
        "higher_is_better",
        "Likelihood shift from eta-to-epsilon readable prefix conditioning.",
    ),
    HarnessMetric(
        "evidence_packet_completeness",
        "higher_is_better",
        "How completely the run can be audited by a reviewer.",
    ),
    HarnessMetric(
        "latency_ms",
        "lower_is_better",
        "Runtime cost of the harness condition.",
    ),
)


STAGE22_CONDITIONS: tuple[HarnessAblationCondition, ...] = (
    HarnessAblationCondition(
        mode="floor_raw_model",
        label="Floor: raw frozen model",
        subject="cas_harness",
        status="executable_now",
        layers=HarnessLayerSet(frozen_model_logits=True),
        hypothesis="Defines the no-harness floor for likelihood and output-quality metrics.",
        boundary="No CAS claims attach to this condition; it is a comparator.",
        required_artifacts=(
            "Stage 7/8/15/16 frozen model fixtures",
            "locked prompt rows",
        ),
    ),
    HarnessAblationCondition(
        mode="cpl2_bridge_only",
        label="Eta-to-epsilon bridge only",
        subject="cas_harness",
        status="executable_now",
        layers=HarnessLayerSet(
            frozen_model_logits=True,
            eta_probe_readout=True,
            epsilon_readable_prefix=True,
        ),
        hypothesis="Readable realization should shift semantic likelihood without safety layers.",
        boundary="Likelihood conditioning only; not visible-text control.",
        required_artifacts=(
            "Stage 7 CPL2 report",
            "Stage 8 Pythia-1B CPL2 report",
            "Stage 15 OLMo CPL2 report",
            "Stage 16 Qwen CPL2 report",
        ),
    ),
    HarnessAblationCondition(
        mode="mode_selector_balanced",
        label="Mode Selector: BALANCED",
        subject="cas_harness",
        status="executable_now",
        layers=HarnessLayerSet(
            frozen_model_logits=True,
            eta_probe_readout=True,
            epsilon_readable_prefix=True,
            verification_stack=True,
            mode_selector="BALANCED",
        ),
        hypothesis="Default customer mode should recover coverage while preserving factor consistency.",
        boundary="Balances precision and coverage; not a high-precision legal mode.",
        required_artifacts=(
            "stage19b_cross_arch_foundation_verification_stack_20260519.json",
            "stage19c_verification_mode_selector_20260519.json",
        ),
    ),
    HarnessAblationCondition(
        mode="mode_selector_high_precision",
        label="Mode Selector: HIGH_PRECISION",
        subject="cas_harness",
        status="executable_now",
        layers=HarnessLayerSet(
            frozen_model_logits=True,
            eta_probe_readout=True,
            epsilon_readable_prefix=True,
            verification_stack=True,
            mode_selector="HIGH_PRECISION",
        ),
        hypothesis="High-precision mode should minimize silent error at the cost of coverage.",
        boundary="Opt-in regulator/legal/safety mode.",
        required_artifacts=(
            "stage19b_cross_arch_foundation_verification_stack_20260519.json",
            "stage19c_verification_mode_selector_20260519.json",
        ),
    ),
    HarnessAblationCondition(
        mode="mode_selector_max_coverage_triage",
        label="Mode Selector: MAX_COVERAGE_TRIAGE",
        subject="cas_harness",
        status="executable_now",
        layers=HarnessLayerSet(
            frozen_model_logits=True,
            eta_probe_readout=True,
            epsilon_readable_prefix=True,
            verification_stack=True,
            mode_selector="MAX_COVERAGE_TRIAGE",
        ),
        hypothesis="Triage mode should maximize coverage for human-review queues while carrying a lower-confidence boundary.",
        boundary="Opt-in review-queue mode only; not a licensed high-confidence claim mode.",
        required_artifacts=(
            "stage19b_cross_arch_foundation_verification_stack_20260519.json",
            "stage19c_verification_mode_selector_20260519.json",
        ),
    ),
    HarnessAblationCondition(
        mode="readiness_balanced",
        label="Generation Readiness: BALANCED",
        subject="cas_harness",
        status="executable_now",
        layers=HarnessLayerSet(
            frozen_model_logits=True,
            eta_probe_readout=True,
            epsilon_readable_prefix=True,
            verification_stack=True,
            mode_selector="BALANCED",
            generation_readiness_gate=True,
        ),
        hypothesis="Readiness policy should convert unsafe accept/suppress outcomes into useful allow/caveat/constrain/suppress decisions.",
        boundary="Policy packaging over existing signals; does not change host-model weights.",
        required_artifacts=(
            "stage20b_generation_readiness_packets_20260519.json",
        ),
    ),
    HarnessAblationCondition(
        mode="evidence_packet_full",
        label="Full audit surface",
        subject="cas_harness",
        status="executable_now",
        layers=HarnessLayerSet(
            frozen_model_logits=True,
            eta_probe_readout=True,
            epsilon_readable_prefix=True,
            verification_stack=True,
            mode_selector="BALANCED",
            generation_readiness_gate=True,
            evidence_packet_export=True,
            atlas_trace_linkage=True,
        ),
        hypothesis="Full audit surface should maximize reviewer reproducibility, not necessarily raw output quality.",
        boundary="Audit completeness is a product metric separate from model accuracy.",
        required_artifacts=(
            "stage21a_evidence_packet_export_20260519.json",
            "Stage 21B backend/frontend route",
            "Stage 21C trace-linkage commit",
        ),
    ),
    HarnessAblationCondition(
        mode="frontier_llm_ceiling",
        label="Ceiling: frontier LLM without CAS",
        subject="cas_harness",
        status="reference_only",
        layers=HarnessLayerSet(
            frozen_model_logits=False,
            external_frontier_model=True,
        ),
        hypothesis="Provides a non-CAS quality ceiling for the same prompts/tasks.",
        boundary="Not a CAS mechanism and not comparable as a weight-level intervention.",
        required_artifacts=(
            "locked prompt rows",
            "frontier-model outputs with model/date/version recorded",
        ),
    ),
)


def stage22_condition_matrix() -> list[dict[str, Any]]:
    return [condition.as_dict() for condition in STAGE22_CONDITIONS]


def stage22_metric_matrix() -> list[dict[str, str]]:
    return [metric.as_dict() for metric in STAGE22_METRICS]


def validate_stage22_conditions(
    conditions: tuple[HarnessAblationCondition, ...] = STAGE22_CONDITIONS,
) -> dict[str, list[str]]:
    errors_by_mode: dict[str, list[str]] = {}
    for condition in conditions:
        errors: list[str] = []
        layers = condition.layers
        if condition.subject != "cas_harness":
            errors.append("Stage 22 is scoped to external CAS Harness only")
        if layers.evidence_packet_export and not layers.generation_readiness_gate:
            errors.append("evidence_packet_export requires generation_readiness_gate")
        if layers.atlas_trace_linkage and not layers.evidence_packet_export:
            errors.append("atlas_trace_linkage requires evidence_packet_export")
        if layers.mode_selector != "OFF" and not layers.verification_stack:
            errors.append("mode_selector requires verification_stack")
        if layers.generation_readiness_gate and layers.mode_selector == "OFF":
            errors.append("generation_readiness_gate requires a selected mode")
        if layers.epsilon_readable_prefix and not layers.eta_probe_readout:
            errors.append("epsilon_readable_prefix requires eta_probe_readout")
        if condition.status == "executable_now" and not layers.frozen_model_logits:
            errors.append("executable CAS Harness conditions require frozen_model_logits")
        if not condition.required_artifacts:
            errors.append("required_artifacts must be listed")
        errors_by_mode[condition.mode] = errors
    return errors_by_mode


def stage22_preregistration_payload() -> dict[str, Any]:
    """Return the canonical machine-readable Stage 22 pre-registration."""
    return {
        "schema_version": "stage22_cas_harness_ablation_spec_v1",
        "scope": "external_cas_harness_not_cas_native_inner_loop",
        "default_customer_mode": "BALANCED",
        "naming_boundary": {
            "cas_harness": "External inspection/conditioning product around open-weight models.",
            "cas_native_cognitive_runtime": "Future from-scratch CAS Native inner loop; not Stage 22.",
        },
        "conditions": stage22_condition_matrix(),
        "metrics": stage22_metric_matrix(),
        "validation": validate_stage22_conditions(),
        "stage22_1_followup": {
            "status": "recommended_not_yet_run",
            "scope": "fine_grained_gate_attribution",
            "candidate_switches": [
                "wrap_output_gate",
                "rpm_gate",
                "lacunarity_gate",
                "inversion_scan_gate",
                "verification_stack",
                "mode_selector",
                "generation_readiness_gate",
            ],
            "rationale": (
                "Stage 22 is the coarse harness bench. Stage 22.1 should split "
                "the upstream gate bundle only after the coarse bench names "
                "which bundle is worth deeper attribution."
            ),
        },
        "claim_boundary": (
            "Stage 22 tests harness contribution and tradeoffs. Suppression rate "
            "is never interpreted without useful_output_rate and coverage."
        ),
    }
