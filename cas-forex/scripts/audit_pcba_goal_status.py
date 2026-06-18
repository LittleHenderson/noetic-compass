"""Audit the active PCBA objective status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.pcba_goal_status import build_pcba_goal_status, load_local_pcba_evidence  # noqa: E402


def _write_markdown(path: Path, status: dict[str, Any]) -> None:
    checks = status["checks"]
    lines = [
        "# PCBA Goal Status",
        "",
        f"Generated: `{status['generated_at']}`",
        f"Goal complete: `{str(status['goal_complete']).lower()}`",
        f"Current boundary honest: `{str(status['current_boundary_honest']).lower()}`",
        "",
        "## Gate Status",
        "",
        "| Gate | Status | Ready | Missing Evidence |",
        "|---|---|---:|---|",
    ]
    for key in [
        "production_pcba_component_syntax",
        "compiler_enforced_safety_claim",
        "prompt_injection_prevention_claim",
        "live_trading_permission_path",
        "broker_accept_creation",
    ]:
        check = checks[key]
        missing = ", ".join(check["missing_evidence"]) or "none"
        lines.append(f"| `{key}` | `{check['status']}` | `{str(check['ready']).lower()}` | `{missing}` |")

    lines.extend(["", "## Receipt Diagnostics", ""])
    if status["receipt_diagnostics"]:
        lines.extend(["| Path | Evidence Key | Approved | Verified |", "|---|---|---:|---:|"])
        for item in status["receipt_diagnostics"]:
            lines.append(
                f"| `{item.get('path', '')}` | `{item.get('evidence_key', '')}` | "
                f"`{str(item.get('approved', False)).lower()}` | `{str(item.get('verified', False)).lower()}` |"
            )
    else:
        lines.append("No receipts supplied.")

    lines.extend(["", "## Blockers", ""])
    if status["human_or_external_blockers"]:
        lines.extend(f"- `{item}`" for item in status["human_or_external_blockers"])
    else:
        lines.append("- none")

    lines.extend(["", "## Next Commands", ""])
    lines.extend(f"- `{item}`" for item in status["next_commands"])
    lines.extend(["", status["summary"], ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--local-evidence",
        default=r"..\docs\working\pcba_model_local_evidence_20260617.json",
    )
    parser.add_argument(
        "--receipt",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--artifact-root",
        default=str(Path(__file__).resolve().parents[2]),
    )
    parser.add_argument(
        "--json-out",
        default=r"..\docs\working\pcba_goal_status_20260617.json",
    )
    parser.add_argument(
        "--md-out",
        default=r"..\docs\working\pcba_goal_status_20260617.md",
    )
    args = parser.parse_args()

    status = build_pcba_goal_status(
        local_evidence=load_local_pcba_evidence(Path(args.local_evidence)),
        receipt_paths=[
            Path(item)
            for item in (
                args.receipt
                or [r"..\docs\working\pcba_semantics_review_request_20260617.json"]
            )
        ],
        artifact_root=Path(args.artifact_root),
    )
    text = json.dumps(status, indent=2)
    print(text)

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(text + "\n", encoding="utf-8")
    _write_markdown(Path(args.md_out), status)
    return 0 if status["goal_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
