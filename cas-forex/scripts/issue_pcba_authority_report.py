"""Issue a PCBA authority report from local evidence and signed receipts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.pcba_authority import (  # noqa: E402
    build_pcba_licensing_report,
    load_authority_receipts,
    merge_evidence,
    write_missing_receipt_templates,
    write_receipt_template,
)
from cas_forex.pcba_semantics_review import SEMANTICS_RECEIPT_ARTIFACT_REFS  # noqa: E402
from cas_forex.schemas.pcba import PcbaProductionFeature  # noqa: E402


def _load_local_evidence(path: Path) -> dict[str, bool]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "local_evidence" in payload:
        return {key: bool(value) for key, value in payload["local_evidence"].items()}
    return {key: bool(value) for key, value in payload.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--local-evidence",
        default=r"..\docs\working\pcba_model_local_evidence_20260617.json",
    )
    parser.add_argument("--receipt", action="append", default=[])
    parser.add_argument("--out", default=r"..\docs\working\pcba_authority_report_20260617.json")
    parser.add_argument(
        "--write-semantics-template",
        default=r"..\docs\working\pcba_semantics_review_request_20260617.json",
    )
    parser.add_argument(
        "--force-write-semantics-template",
        action="store_true",
        help="Overwrite an existing semantics template. Disabled by default to protect signed receipts.",
    )
    parser.add_argument(
        "--write-missing-templates-dir",
        default=r"..\docs\working\pcba_authority_receipts_needed_20260617",
    )
    parser.add_argument(
        "--artifact-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Workspace root used to hash and verify artifact_refs in signed receipts.",
    )
    args = parser.parse_args()
    artifact_root = Path(args.artifact_root)

    if args.write_semantics_template and (
        args.force_write_semantics_template or not Path(args.write_semantics_template).exists()
    ):
        write_receipt_template(
            args.write_semantics_template,
            evidence_key="pcba_semantics_review_signed",
            feature=PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX,
            artifact_refs=SEMANTICS_RECEIPT_ARTIFACT_REFS,
            artifact_root=artifact_root,
        )

    local = _load_local_evidence(Path(args.local_evidence))
    receipt_evidence, receipt_diagnostics = load_authority_receipts(
        args.receipt,
        artifact_root=artifact_root,
    )
    evidence = merge_evidence(local, receipt_evidence)
    report = build_pcba_licensing_report(evidence)
    missing_templates = (
        write_missing_receipt_templates(
            report,
            args.write_missing_templates_dir,
            clear_existing=True,
            preserve_paths=args.receipt,
        )
        if args.write_missing_templates_dir
        else []
    )
    payload = {
        "evidence": evidence,
        "receipt_diagnostics": receipt_diagnostics,
        "readiness_report": report.model_dump(mode="json"),
        "non_licensable": ["broker_accept_creation"],
        "missing_receipt_templates": missing_templates,
    }
    text = json.dumps(payload, indent=2)
    print(text)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
