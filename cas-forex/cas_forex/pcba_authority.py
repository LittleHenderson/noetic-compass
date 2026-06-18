"""PCBA licensing and authority-gate evaluation.

This module turns evidence receipts into readiness decisions. It does not
fabricate human, time-based, legal, broker, or red-team proof.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from pydantic import BaseModel, Field, model_validator

from cas_forex.pcba_readiness import DEFAULT_STATUS, REQUIRED_EVIDENCE, _rationale
from cas_forex.schemas.pcba import (
    PcbaClaimCeiling,
    PcbaProductionFeature,
    PcbaProductionReadinessCheck,
    PcbaProductionReadinessReport,
    PcbaReadinessStatus,
)
from cas_forex.time_utils import utc_now


PERMANENTLY_NON_LICENSABLE = {PcbaProductionFeature.BROKER_ACCEPT_CREATION}


class PcbaAuthorityReceipt(BaseModel):
    """Signed evidence receipt for a PCBA production-readiness gate."""

    evidence_key: str
    feature: PcbaProductionFeature
    approved: bool = False
    operator_id: str = ""
    signed_reason: str = ""
    signature: str = ""
    artifact_refs: list[str] = Field(default_factory=list)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    receipt_hash: Optional[str] = None

    @model_validator(mode="after")
    def _validate_receipt(self):
        if self.approved:
            if not self.operator_id:
                raise ValueError("Approved receipt requires operator_id")
            if not self.signed_reason:
                raise ValueError("Approved receipt requires signed_reason")
            if not self.signature:
                raise ValueError("Approved receipt requires signature")
        return self

    def compute_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def finalize(self) -> "PcbaAuthorityReceipt":
        self.receipt_hash = self.compute_hash()
        return self

    def verify(self, artifact_root: str | Path | None = None) -> bool:
        if not (self.approved and self.receipt_hash and self.receipt_hash == self.compute_hash()):
            return False
        return self._artifact_hashes_verified(artifact_root)

    def _artifact_hashes_verified(self, artifact_root: str | Path | None = None) -> bool:
        for ref in self.artifact_refs:
            expected = self.artifact_hashes.get(ref)
            if not expected:
                return False
            path = _resolve_artifact_ref(ref, artifact_root)
            if not path.exists() or _sha256_file(path) != expected:
                return False
        return True


def write_receipt_template(
    path: str | Path,
    evidence_key: str,
    feature: PcbaProductionFeature,
    artifact_refs: Optional[list[str]] = None,
    artifact_root: str | Path | None = None,
) -> PcbaAuthorityReceipt:
    """Write an unsigned receipt template for the owner/human reviewer."""

    refs = artifact_refs or []
    receipt = PcbaAuthorityReceipt(
        evidence_key=evidence_key,
        feature=feature,
        approved=False,
        artifact_refs=refs,
        artifact_hashes={
            ref: _sha256_file(_resolve_artifact_ref(ref, artifact_root))
            for ref in refs
            if _resolve_artifact_ref(ref, artifact_root).exists()
        },
    )
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
    return receipt


def write_missing_receipt_templates(
    report: PcbaProductionReadinessReport,
    output_dir: str | Path,
    clear_existing: bool = False,
    preserve_paths: Optional[Iterable[str | Path]] = None,
) -> list[str]:
    """Write unsigned templates for every missing external/signed evidence key."""

    written: list[str] = []
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    preserved = {Path(path).resolve() for path in (preserve_paths or [])}
    if clear_existing:
        for path in out_dir.glob("*.json"):
            if path.resolve() not in preserved:
                path.unlink()
    local_evidence_prefixes = (
        "pcba_grammar_",
        "pcba_parser_",
        "pcba_invalid_",
        "pcba_ir_",
        "pcba_component_",
        "pcba_production_compiler_",
        "pcba_no_accept_",
        "no_pcba_",
        "auditor_accept_",
        "broker_accept_",
        "csb_shadow_",
        "cpmb_brownout_",
    )
    for check in report.checks:
        for key in check.missing_evidence:
            if key.startswith(local_evidence_prefixes):
                continue
            filename = f"{check.feature.value}__{key}.json"
            path = out_dir / filename
            if path.resolve() in preserved:
                continue
            write_receipt_template(path, key, check.feature)
            written.append(str(path))
    return written


def load_authority_receipts(
    paths: Iterable[str | Path],
    artifact_root: str | Path | None = None,
) -> tuple[dict[str, bool], list[dict[str, Any]]]:
    """Load signed receipts and convert verified approvals to evidence flags."""

    evidence: dict[str, bool] = {}
    diagnostics: list[dict[str, Any]] = []
    for raw_path in paths:
        path = Path(raw_path)
        try:
            receipt = PcbaAuthorityReceipt.model_validate_json(path.read_text(encoding="utf-8"))
            verified = receipt.verify(artifact_root=artifact_root)
            diagnostics.append(
                {
                    "path": str(path),
                    "evidence_key": receipt.evidence_key,
                    "feature": receipt.feature.value,
                    "approved": receipt.approved,
                    "verified": verified,
                    "operator_id": receipt.operator_id,
                    "receipt_hash": receipt.receipt_hash,
                    "artifact_refs": receipt.artifact_refs,
                }
            )
            evidence[receipt.evidence_key] = verified
        except Exception as exc:
            diagnostics.append({"path": str(path), "verified": False, "error": str(exc)})
    return evidence, diagnostics


def build_pcba_licensing_report(
    evidence: Optional[Mapping[str, bool]] = None,
) -> PcbaProductionReadinessReport:
    """Build the licensing report from local and signed external evidence."""

    supplied = evidence or {}
    checks: list[PcbaProductionReadinessCheck] = []
    for feature in PcbaProductionFeature:
        required = REQUIRED_EVIDENCE[feature]
        present = [item for item in required if bool(supplied.get(item))]
        missing = [item for item in required if item not in present]
        all_present = not missing
        non_licensable = feature in PERMANENTLY_NON_LICENSABLE
        ready = all_present and not non_licensable
        status = (
            PcbaReadinessStatus.LICENSED
            if ready
            else (
                PcbaReadinessStatus.NOT_LICENSED
                if non_licensable
                else DEFAULT_STATUS[feature]
            )
        )
        checks.append(
            PcbaProductionReadinessCheck(
                feature=feature,
                status=status,
                ready=ready,
                claim_ceiling=(
                    PcbaClaimCeiling.OPEN
                    if ready or DEFAULT_STATUS[feature] == PcbaReadinessStatus.OPEN
                    else PcbaClaimCeiling.NOT_LICENSED
                ),
                required_evidence=required,
                present_evidence=present,
                missing_evidence=missing,
                can_affect_live_trading=ready and feature == PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH,
                can_create_broker_accept=False,
                rationale=_licensing_rationale(feature, ready, non_licensable),
            )
        )
    return PcbaProductionReadinessReport(
        report_id=f"pcba-authority-{hashlib.sha256(json.dumps(dict(supplied), sort_keys=True).encode()).hexdigest()[:12]}",
        checks=checks,
        summary=(
            "PCBA licensing report: local and signed evidence may license syntax or claims, "
            "but PCBA direct broker ACCEPT remains permanently NOT LICENSED."
        ),
    )


def merge_evidence(*sources: Mapping[str, bool]) -> dict[str, bool]:
    merged: dict[str, bool] = {}
    for source in sources:
        for key, value in source.items():
            merged[key] = bool(value)
    return merged


def _licensing_rationale(
    feature: PcbaProductionFeature,
    ready: bool,
    non_licensable: bool,
) -> str:
    if non_licensable:
        return "PCBA broker ACCEPT creation is intentionally non-licensable; ACCEPT must come only from the CAS Forex auditor/broker path."
    if ready:
        return "All required evidence is present and verified for this feature."
    return _rationale(feature)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_artifact_ref(ref: str, artifact_root: str | Path | None = None) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    root = Path(artifact_root) if artifact_root is not None else Path.cwd()
    return root / path
