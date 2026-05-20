"""Emit Stage 24A CAS Sonar + component-attribution pre-registration.

This is a no-GPU artifact. It fixes the token-level and component-level
experiment boundary before any new Pythia hook or SAE work runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from stage24a_sonar_component_spec import stage24a_preregistration_payload


_HERE = Path(__file__).resolve().parent


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = _HERE / candidate
    return candidate


def _write_markdown(payload: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 24A CAS Sonar + Component Attribution Pre-Registration",
        "",
        f"**Status:** `{payload['status']}`",
        "",
        "## Scope",
        "",
        "Stage 24A is a bounded research escalation for CAS Harness. It tests",
        "token-level CAS signatures first, then a component-level attribution pilot.",
        "It does not authorize SAE training, exact-neuron claims, or product-language",
        "changes before results exist.",
        "",
        "## Required Inputs",
        "",
        "| Input | Value |",
        "|---|---|",
    ]
    for key, value in payload["required_inputs"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(["", "## Tracks", ""])
    for track in payload["tracks"]:
        lines.extend(
            [
                f"### `{track['name']}`",
                "",
                f"- Subject: `{track['subject']}`",
                f"- Status: `{track['status']}`",
                f"- Primary artifact: `{track['primary_artifact']}`",
                f"- Question: {track['question']}",
                "",
                "Method:",
            ]
        )
        for item in track["method"]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("PASS gate:")
        for item in track["pass_gate"]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("NULL gate:")
        for item in track["null_gate"]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append(f"Claim if PASS: {track['claim_if_pass']}")
        lines.append("")
        lines.append(f"Claim if NULL: {track['claim_if_null']}")
        lines.append("")
        lines.append("Forbidden claims:")
        for item in track["forbidden_claims"]:
            lines.append(f"- {item}")
        lines.append("")

    lines.extend(
        [
            "## Claim Boundary",
            "",
            f"- Licensed if pass: {payload['claim_boundary']['licensed_if_pass']}",
            f"- Not yet claimed: {payload['claim_boundary']['not_yet_claimed']}",
            f"- Product relevance: {payload['claim_boundary']['product_relevance']}",
            "",
            "## SAE Follow-Up",
            "",
            f"- Status: `{payload['sae_followup']['status']}`",
            f"- Trigger: {payload['sae_followup']['trigger']}",
            f"- Authorized by Stage 24A: `{not payload['sae_followup']['not_authorized_by_stage24a']}`",
            "",
            "## Validation",
            "",
        ]
    )
    invalid = {k: v for k, v in payload["validation"].items() if v}
    if invalid:
        for key, errors in invalid.items():
            lines.append(f"- `{key}`: INVALID - {', '.join(errors)}")
    else:
        lines.append("- valid")
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", default="stage24a_sonar_component_prereg_20260520.json")
    parser.add_argument("--out-md", default="STAGE24A_SONAR_COMPONENT_PREREG_20260520.md")
    args = parser.parse_args(argv)

    payload = stage24a_preregistration_payload()
    invalid = {key: errors for key, errors in payload["validation"].items() if errors}
    if invalid:
        raise SystemExit(f"Stage 24A pre-registration is invalid: {invalid}")

    out_json = _resolve(args.out_json)
    out_md = _resolve(args.out_md)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, out_md)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "tracks": payload["execution_order"],
                "sae_authorized": not payload["sae_followup"]["not_authorized_by_stage24a"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
