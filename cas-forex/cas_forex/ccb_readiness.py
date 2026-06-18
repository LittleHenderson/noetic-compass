"""C: CCB safety-claim + CjtPredictionHead readiness gates.

Bridges the executable CCB designs (which can be *well-formed* — see
``ccb_designs``) to their *claims* (which stay NOT LICENSED / OPEN until external
evidence lands). A board passing CRC says the design is structurally sound; it
does NOT license a safety, memory, power, or governance claim.

This module fabricates no external evidence. Red-team reports, false-positive
evals, privacy reviews, legal reviews, and trained-model evals are all marked
missing until independently supplied.
"""

from __future__ import annotations

import uuid
from typing import Mapping, Optional

from pydantic import BaseModel, Field, model_validator

from cas_forex.ccb_designs import build_all_ccbs
from cas_forex.crc_linter import run_crc
from cas_forex.schemas.cjt import CjtClaimCeiling, CjtReadinessStatus
from cas_forex.schemas.pcba import PcbaBoardKind


# Required external evidence per board claim (none present locally).
BOARD_REQUIRED_EVIDENCE: dict[PcbaBoardKind, list[str]] = {
    PcbaBoardKind.COGNITIVE_SAFETY_BOARD: [
        "csb_design_well_formed",
        "csb_shadow_mode_tests_pass",
        "csb_false_positive_eval_pass",
        "csb_red_team_report_pass",
        "csb_claim_review_signed",
    ],
    PcbaBoardKind.COGNITIVE_OSCILLATOR_BOARD: [
        "cob_design_well_formed",
        "cob_entrainment_eval_pass",
        "cob_claim_review_signed",
    ],
    PcbaBoardKind.COGNITIVE_DIFFERENTIAL_AMPLIFIER_BOARD: [
        "cdab_design_well_formed",
        "cdab_false_positive_eval_pass",
        "cdab_red_team_report_pass",
        "cdab_claim_review_signed",
    ],
    PcbaBoardKind.COGNITIVE_MEMORY_BOARD: [
        "cmb_design_well_formed",
        "cmb_memory_retrieval_eval_pass",
        "cmb_lacunarity_eval_pass",
        "cmb_privacy_review_signed",
        "cmb_claim_review_signed",
    ],
    PcbaBoardKind.COGNITIVE_POWER_MANAGEMENT_BOARD: [
        "cpmb_design_well_formed",
        "cpmb_load_budget_eval_pass",
        "cpmb_brownout_lock_tests_pass",
        "cpmb_human_factors_review_signed",
        "cpmb_claim_review_signed",
    ],
}

_WELL_FORMED_FLAG: dict[PcbaBoardKind, str] = {
    PcbaBoardKind.COGNITIVE_SAFETY_BOARD: "csb_design_well_formed",
    PcbaBoardKind.COGNITIVE_OSCILLATOR_BOARD: "cob_design_well_formed",
    PcbaBoardKind.COGNITIVE_DIFFERENTIAL_AMPLIFIER_BOARD: "cdab_design_well_formed",
    PcbaBoardKind.COGNITIVE_MEMORY_BOARD: "cmb_design_well_formed",
    PcbaBoardKind.COGNITIVE_POWER_MANAGEMENT_BOARD: "cpmb_design_well_formed",
}

# CjtPredictionHead is a CAS-Native training artifact — not built/trained here.
CJT_PREDICTION_HEAD_REQUIRED_EVIDENCE = [
    "cjt_labeled_traces_collected",
    "cjt_prediction_head_trained",
    "cjt_sample_level_eval_pass",
    "cjt_control_comparison_pass",
    "cjt_prediction_head_claim_review_signed",
]


class CcbReadinessCheck(BaseModel):
    board_kind: PcbaBoardKind
    design_well_formed: bool
    design_error_count: int = 0
    design_warn_count: int = 0
    status: CjtReadinessStatus = CjtReadinessStatus.NOT_LICENSED
    ready: bool = False
    claim_ceiling: CjtClaimCeiling = CjtClaimCeiling.NOT_LICENSED
    required_evidence: list[str] = Field(default_factory=list)
    present_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    rationale: str = ""

    @model_validator(mode="after")
    def _enforce_boundary(self):
        if self.ready and self.status != CjtReadinessStatus.LICENSED:
            raise ValueError("Ready CCB checks must be LICENSED")
        return self


class CjtPredictionHeadReadiness(BaseModel):
    status: CjtReadinessStatus = CjtReadinessStatus.OPEN
    ready: bool = False
    required_evidence: list[str] = Field(default_factory=lambda: list(CJT_PREDICTION_HEAD_REQUIRED_EVIDENCE))
    present_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    rationale: str = (
        "CjtPredictionHead is a CAS-Native training artifact. Architecture is "
        "specified, but no head is trained or evaluated; sample-level eval is the "
        "only acceptance metric and has not run."
    )


class CcbReadinessReport(BaseModel):
    report_id: str
    board_checks: list[CcbReadinessCheck] = Field(default_factory=list)
    prediction_head: CjtPredictionHeadReadiness = Field(default_factory=CjtPredictionHeadReadiness)
    summary: str = ""

    @property
    def all_designs_well_formed(self) -> bool:
        return bool(self.board_checks) and all(c.design_well_formed for c in self.board_checks)

    @property
    def any_claim_licensed(self) -> bool:
        return any(c.status == CjtReadinessStatus.LICENSED for c in self.board_checks)


def build_ccb_readiness_report(
    evidence: Optional[Mapping[str, bool]] = None,
) -> CcbReadinessReport:
    """Run each CCB design through CRC and report its NOT-LICENSED claim gate."""

    supplied = dict(evidence or {})
    reports = {kind: run_crc(circuit) for kind, circuit in build_all_ccbs().items()}

    checks: list[CcbReadinessCheck] = []
    for kind, required in BOARD_REQUIRED_EVIDENCE.items():
        crc = reports[kind]
        # The design-well-formed flag is derived from CRC, not caller-supplied.
        supplied[_WELL_FORMED_FLAG[kind]] = crc.well_formed
        present = [name for name in required if bool(supplied.get(name))]
        missing = [name for name in required if name not in present]
        checks.append(
            CcbReadinessCheck(
                board_kind=kind,
                design_well_formed=crc.well_formed,
                design_error_count=crc.error_count,
                design_warn_count=crc.warn_count,
                status=CjtReadinessStatus.NOT_LICENSED,
                ready=False,
                claim_ceiling=CjtClaimCeiling.NOT_LICENSED,
                required_evidence=required,
                present_evidence=present,
                missing_evidence=missing,
                rationale=(
                    "Design is a well-formed reference circuit; the safety/behavior "
                    "claim is NOT LICENSED until red-team and evaluation evidence pass."
                ),
            )
        )

    head = CjtPredictionHeadReadiness(
        present_evidence=[],
        missing_evidence=list(CJT_PREDICTION_HEAD_REQUIRED_EVIDENCE),
    )

    return CcbReadinessReport(
        report_id=str(uuid.uuid4()),
        board_checks=checks,
        prediction_head=head,
        summary=(
            "CCB designs may be well-formed (CRC pass); all board safety/behavior "
            "claims and the CjtPredictionHead remain OPEN / NOT LICENSED."
        ),
    )


def assert_no_ccb_claim_licensed(report: CcbReadinessReport) -> bool:
    """Raise if any CCB claim or the prediction head is accidentally licensed."""

    for check in report.board_checks:
        if check.ready or check.status == CjtReadinessStatus.LICENSED:
            raise AssertionError(f"{check.board_kind.value} claim unexpectedly licensed")
    if report.prediction_head.ready or report.prediction_head.status == CjtReadinessStatus.LICENSED:
        raise AssertionError("CjtPredictionHead unexpectedly licensed")
    return True
