"""Build the PCBA semantics review bundle for human signature."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.pcba_semantics_review import build_pcba_semantics_review_bundle  # noqa: E402


def _load_local_evidence(path: Path) -> dict[str, bool]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "local_evidence" in payload:
        return {key: bool(value) for key, value in payload["local_evidence"].items()}
    return {key: bool(value) for key, value in payload.items()}


def _write_markdown(path: Path, bundle: dict[str, Any]) -> None:
    lines = [
        "# PCBA Semantics Review Bundle",
        "",
        f"Generated: `{bundle['generated_at']}`",
        f"Scope: `{bundle['scope']}`",
        f"Ready for human signature: `{str(bundle['ready_for_human_signature']).lower()}`",
        f"Licensed: `{str(bundle['licensed']).lower()}`",
        "",
        "## Reviewed Artifacts",
        "",
        "| Artifact | Exists | SHA-256 |",
        "|---|---:|---|",
    ]
    for item in bundle["reviewed_artifacts"]:
        lines.append(f"| `{item['ref']}` | `{str(item['exists']).lower()}` | `{item['sha256']}` |")

    lines.extend(
        [
            "",
            "## Parser Cases",
            "",
            "| Expression | Passed | Component |",
            "|---|---:|---|",
        ]
    )
    for item in bundle["parse_cases"]:
        lines.append(
            f"| `{item['expression']}` | `{str(item['passed']).lower()}` | `{item.get('component_kind', '')}` |"
        )

    lines.extend(
        [
            "",
            "## Invalid Parser Cases",
            "",
            "| Expression | Rejected | Error |",
            "|---|---:|---|",
        ]
    )
    for item in bundle["invalid_parse_cases"]:
        lines.append(f"| `{item['expression']}` | `{str(item['passed']).lower()}` | `{item.get('error', '')}` |")

    lines.extend(
        [
            "",
            "## Compiler Cases",
            "",
            "| Expression | Expected | Valid | Reason |",
            "|---|---|---:|---|",
        ]
    )
    for item in bundle["compiler_pass_cases"]:
        lines.append(f"| `{item['source_expression']}` | pass | `{str(item['valid']).lower()}` | {item['reason']} |")
    for item in bundle["compiler_fail_cases"]:
        lines.append(f"| `{item['source_expression']}` | fail | `{str(item['valid']).lower()}` | {item['reason']} |")

    lines.extend(
        [
            "",
            "## Claim Boundaries",
            "",
            f"- `production_pcba_component_syntax`: `{bundle['syntax_gate']['status']}`",
            f"- `compiler_enforced_safety_claim`: `{bundle['claim_boundaries']['compiler_enforced_safety_claim']['status']}`",
            f"- `prompt_injection_prevention_claim`: `{bundle['claim_boundaries']['prompt_injection_prevention_claim']['status']}`",
            f"- `broker_accept_creation`: `{bundle['claim_boundaries']['broker_accept_creation']['status']}`",
            "",
            "## Commands",
            "",
            f"- Finalize: `{bundle['finalize_command']}`",
            f"- Verify: `{bundle['verify_command']}`",
            "",
            bundle["summary"],
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--local-evidence",
        default=r"..\docs\working\pcba_model_local_evidence_20260617.json",
    )
    parser.add_argument(
        "--artifact-root",
        default=str(Path(__file__).resolve().parents[2]),
    )
    parser.add_argument(
        "--json-out",
        default=r"..\docs\working\pcba_semantics_review_bundle_20260617.json",
    )
    parser.add_argument(
        "--md-out",
        default=r"..\docs\working\pcba_semantics_review_bundle_20260617.md",
    )
    args = parser.parse_args()

    bundle = build_pcba_semantics_review_bundle(
        workspace_root=Path(args.artifact_root),
        local_evidence=_load_local_evidence(Path(args.local_evidence)),
    )
    json_text = json.dumps(bundle, indent=2)
    print(json_text)

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json_text + "\n", encoding="utf-8")
    _write_markdown(Path(args.md_out), bundle)
    return 0 if bundle["ready_for_human_signature"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
