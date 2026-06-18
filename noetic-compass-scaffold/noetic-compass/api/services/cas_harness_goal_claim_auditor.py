"""Claim auditor for the active CAS Harness safety/research goal.

This module turns the big product/research objective into explicit gates. It
does not run a model and it does not promote claims. It reads the strongest
current artifacts and records whether each claim is licensed or still open.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, Mapping


ClaimStatus = Literal["LICENSED", "OPEN"]
LicenseStatus = Literal["LICENSED", "NOT LICENSED"]
EvidenceStatus = Literal["present", "unavailable", "failed", "shadow_only"]

SCHEMA_VERSION = "cas_harness_active_goal_claim_audit.v0"
DEFAULT_W0_FULL_CONTROL_REPORT = (
    Path("docs")
    / "working"
    / "qwen_v6_expanded_prespeech_eval_v2_s16_20260615"
    / "layer_28_full_controls.json"
)
DEFAULT_W0_DATA_READINESS_MANIFEST = (
    Path("docs")
    / "working"
    / "qwen_v6_expanded_chain_break_combined_gate_v2_s16_20260615"
    / "combined_gate_manifest.json"
)
DEFAULT_HIDDEN_INJECTION_SURFACE_SCREEN = (
    Path("docs")
    / "working"
    / "hidden_prompt_injection_surface_screen_large_v1_20260617.json"
)
W0_REPORT_SCHEMA_VERSION = "cas_harness_behavior_v6_matched_prespeech_eval.v1"
HIDDEN_INJECTION_W0_REPORT_SCHEMA_VERSION = (
    "cas_harness_hidden_prompt_injection_prespeech_eval.v1"
)

W0_REQUIRED_GATES = (
    "exact_prompt_group_pass",
    "prompt_risk_class_floor_pass",
    "row_chain_label_floor_pass",
    "same_prompt_mixed_group_floor_pass",
    "risk_hidden_balanced_accuracy_pass",
    "risk_text_margin_pass",
    "risk_l0_baseline_present_pass",
    "risk_l0_margin_pass",
    "risk_payload_margin_pass",
    "risk_domain_margin_pass",
    "risk_length_margin_pass",
    "risk_shuffled_control_pass",
    "risk_within_payload_permutation_pass",
    "risk_per_payload_floor_pass",
)

HIDDEN_INJECTION_REQUIRED_GATES = (
    "exact_prompt_group_pass",
    "payload_floor_pass",
    "label_per_payload_floor_pass",
    "hidden_balanced_accuracy_pass",
    "l0_baseline_present_pass",
    "l0_margin_pass",
    "text_margin_pass",
    "char_text_margin_pass",
    "payload_margin_pass",
    "domain_margin_pass",
    "encoding_margin_pass",
    "length_margin_pass",
    "shuffled_control_pass",
    "within_payload_permutation_pass",
    "per_payload_floor_pass",
)

ACTIVE_GOAL_CLAIMS = (
    "internal_w0_prompt_injection_detection",
    "live_pre_speech_interception",
    "prompt_injection_prevention_removal_reversal",
    "hallucination_prevention",
    "cjt_prediction_head_claims",
    "causal_proof",
)


@dataclass(frozen=True)
class GoalClaimAuditRow:
    claim_id: str
    claim_status: ClaimStatus
    license_status: LicenseStatus
    evidence_status: EvidenceStatus
    decision: str
    reason: str
    required_evidence: list[str]
    evidence_refs: list[str]
    failing_gates: list[str]
    observed_metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def audit_active_goal_claims(root: Path | str) -> dict[str, Any]:
    """Audit whether current artifacts license the six active-goal claims."""

    root_path = Path(root)
    data_readiness = _load_artifact(root_path, DEFAULT_W0_DATA_READINESS_MANIFEST)
    hidden_injection_surface_screen = _load_artifact(
        root_path,
        DEFAULT_HIDDEN_INJECTION_SURFACE_SCREEN,
    )
    w0_report = _load_artifact(root_path, DEFAULT_W0_FULL_CONTROL_REPORT)
    w0_scan = _scan_existing_w0_reports(root_path)
    hidden_injection_w0_scan = _scan_existing_hidden_injection_w0_reports(root_path)

    rows = [
        _audit_internal_w0_detection(
            w0_report,
            data_readiness,
            w0_scan,
            hidden_injection_surface_screen,
            hidden_injection_w0_scan,
        ),
        _static_not_licensed_row(
            claim_id="live_pre_speech_interception",
            evidence_status="unavailable",
            reason=(
                "No hosted/live interceptor receipt proves a W0 decision was read "
                "and used before generation. A failed or open W0 detector cannot "
                "license live interception."
            ),
            required_evidence=[
                "LICENSED internal W0 prompt-injection detector",
                "hosted/live worker receipt with prompt-stage activations before first generated token",
                "audit packet proving the live path used the W0 signal before output",
                "WORM/verifier evidence that the path has verdict_effect control boundaries",
            ],
        ),
        _static_not_licensed_row(
            claim_id="prompt_injection_prevention_removal_reversal",
            evidence_status="shadow_only",
            reason=(
                "CAS Harness has a shadow instruction-integrity screen and active-context "
                "quarantine proposal, but the public prevention/removal/reversal claim "
                "requires hosted enforcement, external red-team gates, WORM evidence, "
                "and human/product claim review."
            ),
            required_evidence=[
                "hosted enforcement proof, not only shadow detection",
                "external prompt-injection red-team pass",
                "false-positive control floor",
                "WORM-backed Evidence Packet chain",
                "signed claim review preserving FLAG_FOR_HUMAN_REVIEW versus ACCEPT",
            ],
        ),
        _static_not_licensed_row(
            claim_id="hallucination_prevention",
            evidence_status="unavailable",
            reason=(
                "Current claim-grounding screens can flag unsupported claims, but no "
                "artifact proves prevention of hallucinations before or during generation."
            ),
            required_evidence=[
                "pre-registered hallucination benchmark",
                "intervention or guardrail proof that reduces hallucination rate",
                "held-out controls and false-positive floor",
                "hosted Evidence Packet verification",
            ],
        ),
        _static_not_licensed_row(
            claim_id="cjt_prediction_head_claims",
            evidence_status="unavailable",
            reason=(
                "No current CAS Harness artifact proves a CjtPredictionHead readout, "
                "training/eval result, or product route. Existing StructuredPredictionHead "
                "references are not enough to license CjtPredictionHead claims."
            ),
            required_evidence=[
                "implemented CjtPredictionHead artifact",
                "training/eval report with frozen thresholds",
                "text/layer-0/payload/domain/length controls",
                "claim review tying the head to a product-safe claim ceiling",
            ],
        ),
        _static_not_licensed_row(
            claim_id="causal_proof",
            evidence_status="unavailable",
            reason=(
                "The active goal needs causal proof for the prompt-injection/compliance "
                "state: intervene on the relevant hidden direction and show behavior "
                "changes under matched controls. No such prompt-injection W0 ablation "
                "receipt is present."
            ),
            required_evidence=[
                "LICENSED W0 direction or readout",
                "real-model intervention on the hidden direction before generation",
                "matched control intervention",
                "behavior-change effect size and confidence interval",
                "WORM/verifier receipt that causal proof is present",
            ],
        ),
    ]

    unlicensed = [row.claim_id for row in rows if row.license_status != "LICENSED"]
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "goal_complete": not unlicensed,
        "claim_boundary_honest": True,
        "summary": {
            "claims_total": len(rows),
            "claims_licensed": len(rows) - len(unlicensed),
            "claims_not_licensed": len(unlicensed),
            "unlicensed_claim_ids": unlicensed,
        },
        "claim_ceiling": (
            "Only claims with license_status LICENSED may be marketed as working. "
            "All OPEN / NOT LICENSED rows remain research or shadow-only until "
            "their required evidence is present."
        ),
        "claims": [row.to_dict() for row in rows],
    }


def _audit_internal_w0_detection(
    w0_report_artifact: dict[str, Any],
    data_readiness_artifact: dict[str, Any],
    w0_scan: dict[str, Any],
    hidden_injection_surface_artifact: dict[str, Any],
    hidden_injection_w0_scan: dict[str, Any],
) -> GoalClaimAuditRow:
    report = w0_report_artifact.get("json")
    manifest = data_readiness_artifact.get("json")
    hidden_injection_surface = hidden_injection_surface_artifact.get("json")
    evidence_refs = list(
        filter(
            None,
            [
                w0_report_artifact.get("ref"),
                data_readiness_artifact.get("ref"),
                hidden_injection_surface_artifact.get("ref"),
            ],
        )
    )
    if not isinstance(report, Mapping):
        return _static_not_licensed_row(
            claim_id="internal_w0_prompt_injection_detection",
            evidence_status="unavailable",
            reason="The W0 full-control report is missing or malformed.",
            required_evidence=list(W0_REQUIRED_GATES),
            evidence_refs=evidence_refs,
        )

    passing_reports = [
        candidate
        for candidate in w0_scan.get("candidates", [])
        if candidate.get("license_eligible") is True
    ]
    passing_hidden_injection_reports = [
        candidate
        for candidate in hidden_injection_w0_scan.get("candidates", [])
        if candidate.get("license_eligible") is True
    ]
    if passing_hidden_injection_reports:
        best_hidden = passing_hidden_injection_reports[0]
        return GoalClaimAuditRow(
            claim_id="internal_w0_prompt_injection_detection",
            claim_status="LICENSED",
            license_status="LICENSED",
            evidence_status="present",
            decision="LICENSED",
            reason=(
                "A hidden/encoded prompt-injection W0 prespeech report passed "
                "every frozen gate."
            ),
            required_evidence=list(HIDDEN_INJECTION_REQUIRED_GATES),
            evidence_refs=[str(best_hidden.get("ref"))],
            failing_gates=[],
            observed_metrics={
                "existing_w0_report_count": w0_scan.get("report_count", 0),
                "passing_w0_report_count": len(passing_reports),
                "best_existing_w0_candidate": w0_scan.get("best_candidate"),
                "existing_hidden_injection_w0_report_count": hidden_injection_w0_scan.get(
                    "report_count",
                    0,
                ),
                "passing_hidden_injection_w0_report_count": len(
                    passing_hidden_injection_reports
                ),
                "best_hidden_injection_w0_candidate": best_hidden,
                "next_hidden_injection_surface_screen": _hidden_injection_surface_metrics(
                    hidden_injection_surface
                ),
            },
        )
    if passing_reports:
        best_passing = passing_reports[0]
        return GoalClaimAuditRow(
            claim_id="internal_w0_prompt_injection_detection",
            claim_status="LICENSED",
            license_status="LICENSED",
            evidence_status="present",
            decision="LICENSED",
            reason="At least one existing W0 prespeech report passed every frozen gate.",
            required_evidence=list(W0_REQUIRED_GATES),
            evidence_refs=[str(best_passing.get("ref"))],
            failing_gates=[],
            observed_metrics={
                "existing_w0_report_count": w0_scan.get("report_count", 0),
                "passing_w0_report_count": len(passing_reports),
                "best_existing_w0_candidate": best_passing,
                "existing_hidden_injection_w0_report_count": hidden_injection_w0_scan.get(
                    "report_count",
                    0,
                ),
                "passing_hidden_injection_w0_report_count": len(
                    passing_hidden_injection_reports
                ),
                "best_hidden_injection_w0_candidate": hidden_injection_w0_scan.get(
                    "best_candidate"
                ),
                "next_hidden_injection_surface_screen": _hidden_injection_surface_metrics(
                    hidden_injection_surface
                ),
            },
        )

    gates = report.get("gates") if isinstance(report.get("gates"), Mapping) else {}
    failing_gates = [
        gate_name for gate_name in W0_REQUIRED_GATES if gates.get(gate_name) is not True
    ]
    status = str(report.get("status") or "UNKNOWN")
    licensed = status == "PASS" and not failing_gates
    metrics = report.get("metrics") if isinstance(report.get("metrics"), Mapping) else {}
    observed_metrics = {
        "status": status,
        "layer": report.get("layer"),
        "data_readiness_status": (
            manifest.get("status") if isinstance(manifest, Mapping) else None
        ),
        "risk_hidden_balanced_accuracy": metrics.get("risk_hidden_balanced_accuracy"),
        "risk_text_hash_balanced_accuracy": metrics.get("risk_text_hash_balanced_accuracy"),
        "risk_hidden_minus_text_balanced_accuracy": metrics.get(
            "risk_hidden_minus_text_balanced_accuracy"
        ),
        "risk_l0_embedding_balanced_accuracy": metrics.get(
            "risk_l0_embedding_balanced_accuracy"
        ),
        "risk_payload_majority_balanced_accuracy": metrics.get(
            "risk_payload_majority_balanced_accuracy"
        ),
        "risk_domain_majority_balanced_accuracy": metrics.get(
            "risk_domain_majority_balanced_accuracy"
        ),
        "risk_length_balanced_accuracy": metrics.get("risk_length_balanced_accuracy"),
        "risk_within_payload_permutation_p": metrics.get(
            "risk_within_payload_permutation_p"
        ),
        "risk_per_payload_hidden_balanced_accuracy": metrics.get(
            "risk_per_payload_hidden_balanced_accuracy"
        ),
        "existing_w0_report_count": w0_scan.get("report_count", 0),
        "passing_w0_report_count": len(passing_reports),
        "best_existing_w0_candidate": w0_scan.get("best_candidate"),
        "existing_hidden_injection_w0_report_count": hidden_injection_w0_scan.get(
            "report_count",
            0,
        ),
        "passing_hidden_injection_w0_report_count": len(
            passing_hidden_injection_reports
        ),
        "best_hidden_injection_w0_candidate": hidden_injection_w0_scan.get(
            "best_candidate"
        ),
        "next_hidden_injection_surface_screen": _hidden_injection_surface_metrics(
            hidden_injection_surface
        ),
    }
    return GoalClaimAuditRow(
        claim_id="internal_w0_prompt_injection_detection",
        claim_status="LICENSED" if licensed else "OPEN",
        license_status="LICENSED" if licensed else "NOT LICENSED",
        evidence_status="present" if licensed else "failed",
        decision="LICENSED" if licensed else "keep_OPEN_NOT_LICENSED",
        reason=(
            "W0 report passed every frozen full-control gate."
            if licensed
            else (
                "No current W0 prespeech report licenses the internal "
                "prompt-injection detector claim. Headline report missing gates: "
                + ", ".join(failing_gates)
            )
        ),
        required_evidence=list(W0_REQUIRED_GATES),
        evidence_refs=evidence_refs,
        failing_gates=failing_gates,
        observed_metrics=observed_metrics,
    )


def _hidden_injection_surface_metrics(artifact: Any) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return {
            "status": "unavailable",
            "claim": "OPEN / NOT LICENSED for internal W0 prompt-injection detection.",
        }
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), Mapping) else {}
    return {
        "status": artifact.get("status"),
        "claim": artifact.get("claim"),
        "row_count": artifact.get("row_count"),
        "prompt_group_count": artifact.get("prompt_group_count"),
        "testable_payload_class_count": artifact.get("testable_payload_class_count"),
        "text_hash_balanced_accuracy": metrics.get("text_hash_balanced_accuracy"),
        "length_balanced_accuracy": metrics.get("length_balanced_accuracy"),
        "payload_majority_balanced_accuracy": metrics.get("payload_majority_balanced_accuracy"),
        "domain_majority_balanced_accuracy": metrics.get("domain_majority_balanced_accuracy"),
        "encoding_majority_balanced_accuracy": metrics.get("encoding_majority_balanced_accuracy"),
    }


def _static_not_licensed_row(
    *,
    claim_id: str,
    evidence_status: EvidenceStatus,
    reason: str,
    required_evidence: list[str],
    evidence_refs: list[str] | None = None,
) -> GoalClaimAuditRow:
    return GoalClaimAuditRow(
        claim_id=claim_id,
        claim_status="OPEN",
        license_status="NOT LICENSED",
        evidence_status=evidence_status,
        decision="keep_OPEN_NOT_LICENSED",
        reason=reason,
        required_evidence=required_evidence,
        evidence_refs=evidence_refs or [],
        failing_gates=list(required_evidence),
        observed_metrics={},
    )


def _load_artifact(root: Path, relative_path: Path) -> dict[str, Any]:
    path = root / relative_path
    if not path.exists():
        return {
            "ref": str(relative_path),
            "status": "missing",
            "sha256": None,
            "json": None,
        }
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = None
    return {
        "ref": str(relative_path),
        "status": "present" if isinstance(parsed, Mapping) else "malformed",
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "json": parsed,
    }


def _scan_existing_w0_reports(root: Path) -> dict[str, Any]:
    docs_working = root / "docs" / "working"
    if not docs_working.exists():
        return {"report_count": 0, "candidates": [], "best_candidate": None}

    candidates: list[dict[str, Any]] = []
    for path in docs_working.rglob("*.json"):
        artifact = _load_json_path(path)
        parsed = artifact.get("json")
        if not isinstance(parsed, Mapping):
            continue
        if parsed.get("schema_version") != W0_REPORT_SCHEMA_VERSION:
            continue
        gates = parsed.get("gates") if isinstance(parsed.get("gates"), Mapping) else {}
        metrics = parsed.get("metrics") if isinstance(parsed.get("metrics"), Mapping) else {}
        failing_gates = [
            gate_name for gate_name in W0_REQUIRED_GATES if gates.get(gate_name) is not True
        ]
        gate_pass_count = len(W0_REQUIRED_GATES) - len(failing_gates)
        status = str(parsed.get("status") or "UNKNOWN")
        candidate = {
            "ref": str(path.relative_to(root)),
            "sha256": artifact["sha256"],
            "status": status,
            "layer": parsed.get("layer"),
            "gate_pass_count": gate_pass_count,
            "gate_total": len(W0_REQUIRED_GATES),
            "license_eligible": status == "PASS" and not failing_gates,
            "failing_gates": failing_gates,
            "risk_hidden_balanced_accuracy": metrics.get(
                "risk_hidden_balanced_accuracy"
            ),
            "risk_text_hash_balanced_accuracy": metrics.get(
                "risk_text_hash_balanced_accuracy"
            ),
            "risk_hidden_minus_text_balanced_accuracy": metrics.get(
                "risk_hidden_minus_text_balanced_accuracy"
            ),
            "risk_within_payload_permutation_p": metrics.get(
                "risk_within_payload_permutation_p"
            ),
        }
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            bool(item["license_eligible"]),
            int(item["gate_pass_count"]),
            _float_or_low(item.get("risk_hidden_minus_text_balanced_accuracy")),
            _float_or_low(item.get("risk_hidden_balanced_accuracy")),
        ),
        reverse=True,
    )
    return {
        "report_count": len(candidates),
        "candidates": candidates,
        "best_candidate": candidates[0] if candidates else None,
    }


def _scan_existing_hidden_injection_w0_reports(root: Path) -> dict[str, Any]:
    docs_working = root / "docs" / "working"
    if not docs_working.exists():
        return {"report_count": 0, "candidates": [], "best_candidate": None}

    candidates: list[dict[str, Any]] = []
    for path in docs_working.rglob("*.json"):
        artifact = _load_json_path(path)
        parsed = artifact.get("json")
        if not isinstance(parsed, Mapping):
            continue
        if parsed.get("schema_version") != HIDDEN_INJECTION_W0_REPORT_SCHEMA_VERSION:
            continue
        gates = parsed.get("gates") if isinstance(parsed.get("gates"), Mapping) else {}
        metrics = parsed.get("metrics") if isinstance(parsed.get("metrics"), Mapping) else {}
        failing_gates = [
            gate_name
            for gate_name in HIDDEN_INJECTION_REQUIRED_GATES
            if gates.get(gate_name) is not True
        ]
        gate_pass_count = len(HIDDEN_INJECTION_REQUIRED_GATES) - len(failing_gates)
        status = str(parsed.get("status") or "UNKNOWN")
        candidate = {
            "ref": str(path.relative_to(root)),
            "sha256": artifact["sha256"],
            "status": status,
            "layer": parsed.get("layer"),
            "gate_pass_count": gate_pass_count,
            "gate_total": len(HIDDEN_INJECTION_REQUIRED_GATES),
            "license_eligible": status == "PASS" and not failing_gates,
            "failing_gates": failing_gates,
            "hidden_balanced_accuracy": metrics.get("hidden_balanced_accuracy"),
            "text_hash_balanced_accuracy": metrics.get("text_hash_balanced_accuracy"),
            "hidden_minus_text_balanced_accuracy": metrics.get(
                "hidden_minus_text_balanced_accuracy"
            ),
            "within_payload_permutation_p": metrics.get(
                "within_payload_permutation_p"
            ),
        }
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            bool(item["license_eligible"]),
            int(item["gate_pass_count"]),
            _float_or_low(item.get("hidden_minus_text_balanced_accuracy")),
            _float_or_low(item.get("hidden_balanced_accuracy")),
        ),
        reverse=True,
    )
    return {
        "report_count": len(candidates),
        "candidates": candidates,
        "best_candidate": candidates[0] if candidates else None,
    }


def _load_json_path(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = None
    return {
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "json": parsed,
    }


def _float_or_low(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return -1.0
