"""Verify the signed PCBA semantics receipt and report syntax licensing status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.pcba_authority import (  # noqa: E402
    build_pcba_licensing_report,
    load_authority_receipts,
    merge_evidence,
)
from cas_forex.schemas.pcba import PcbaProductionFeature, PcbaReadinessStatus  # noqa: E402


def _load_local_evidence(path: Path) -> dict[str, bool]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "local_evidence" in payload:
        return {key: bool(value) for key, value in payload["local_evidence"].items()}
    return {key: bool(value) for key, value in payload.items()}


def _syntax_check(report):
    for check in report.checks:
        if check.feature == PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX:
            return check
    raise RuntimeError("production_pcba_component_syntax check missing")


def _claim_check(report, feature: PcbaProductionFeature):
    for check in report.checks:
        if check.feature == feature:
            return check
    raise RuntimeError(f"{feature.value} check missing")


def verify_semantics_receipt(
    *,
    receipt_path: Path,
    local_evidence_path: Path,
    artifact_root: Path,
) -> tuple[bool, dict[str, Any]]:
    local = _load_local_evidence(local_evidence_path)
    receipt_evidence, receipt_diagnostics = load_authority_receipts(
        [receipt_path],
        artifact_root=artifact_root,
    )
    evidence = merge_evidence(local, receipt_evidence)
    report = build_pcba_licensing_report(evidence)
    syntax = _syntax_check(report)

    safety = _claim_check(report, PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM)
    prompt = _claim_check(report, PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM)
    broker_accept = _claim_check(report, PcbaProductionFeature.BROKER_ACCEPT_CREATION)

    licensed = (
        syntax.ready
        and syntax.status == PcbaReadinessStatus.LICENSED
        and bool(evidence.get("pcba_semantics_review_signed"))
    )
    payload = {
        "receipt_path": str(receipt_path),
        "artifact_root": str(artifact_root),
        "licensed": licensed,
        "syntax_check": syntax.model_dump(mode="json"),
        "receipt_diagnostics": receipt_diagnostics,
        "guardrails": {
            "compiler_enforced_safety_claim": safety.model_dump(mode="json"),
            "prompt_injection_prevention_claim": prompt.model_dump(mode="json"),
            "broker_accept_creation": broker_accept.model_dump(mode="json"),
        },
        "summary": (
            "Production PCBA component syntax is LICENSED by a verified semantics receipt."
            if licensed
            else "Production PCBA component syntax remains OPEN; verified pcba_semantics_review_signed receipt is missing or invalid."
        ),
    }
    return licensed, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--receipt",
        default=r"..\docs\working\pcba_semantics_review_request_20260617.json",
    )
    parser.add_argument(
        "--local-evidence",
        default=r"..\docs\working\pcba_model_local_evidence_20260617.json",
    )
    parser.add_argument(
        "--artifact-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Workspace root used to verify receipt artifact_refs.",
    )
    parser.add_argument(
        "--out",
        default=r"..\docs\working\pcba_semantics_receipt_verification_20260617.json",
    )
    args = parser.parse_args()

    licensed, payload = verify_semantics_receipt(
        receipt_path=Path(args.receipt),
        local_evidence_path=Path(args.local_evidence),
        artifact_root=Path(args.artifact_root),
    )
    text = json.dumps(payload, indent=2)
    print(text)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    return 0 if licensed else 1


if __name__ == "__main__":
    raise SystemExit(main())
