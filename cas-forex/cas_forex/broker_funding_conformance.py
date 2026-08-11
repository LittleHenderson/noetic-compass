"""Load the latest broker-funding sandbox conformance evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "evidence_runs" / "broker_funding_conformance"
REPORT_KIND = "cas_forex_broker_funding_conformance_status"


def latest_broker_funding_conformance(
    evidence_dir: Path | str = DEFAULT_EVIDENCE_DIR,
) -> dict[str, Any]:
    directory = Path(evidence_dir)
    candidates = sorted(directory.glob("broker-funding-conformance-*.json"))
    if not candidates:
        return _unavailable("No broker-funding sandbox conformance artifact is present.")
    path = candidates[-1]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _unavailable(f"Latest conformance artifact is unreadable: {exc}")
    if not isinstance(payload, Mapping) or payload.get("report_kind") != (
        "cas_forex_broker_funding_conformance"
    ):
        return _unavailable("Latest conformance artifact has the wrong report kind.")
    checks = list(payload.get("checks") or [])
    checks_passed = sum(
        1 for item in checks if isinstance(item, Mapping) and item.get("passed") is True
    )
    source_status = str(payload.get("status") or "FLAG_FOR_HUMAN_REVIEW")
    status = (
        "ACCEPT"
        if source_status == "ACCEPT"
        and payload.get("sandbox_only") is True
        and checks
        and checks_passed == len(checks)
        else "FLAG_FOR_HUMAN_REVIEW"
    )
    return {
        "report_kind": REPORT_KIND,
        "status": status,
        "present": True,
        "sandbox_only": True,
        "generated_at": payload.get("generated_at"),
        "provider_reference": payload.get("provider_reference"),
        "checks_total": len(checks),
        "checks_passed": checks_passed,
        "artifact_path": str(path),
        "detail": (
            "Loopback broker-middleware contract evidence passed. This does not "
            "prove a live Hugo's Way funding API or external funds movement."
            if status == "ACCEPT"
            else "Broker-funding sandbox conformance needs review."
        ),
    }


def _unavailable(detail: str) -> dict[str, Any]:
    return {
        "report_kind": REPORT_KIND,
        "status": "unavailable",
        "present": False,
        "sandbox_only": True,
        "generated_at": None,
        "provider_reference": None,
        "checks_total": 0,
        "checks_passed": 0,
        "artifact_path": None,
        "detail": detail,
    }
