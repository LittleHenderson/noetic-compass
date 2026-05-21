"""Emit Stage 26 component-attribution preregistration artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from stage26_component_attribution_spec import stage26_payload


_HERE = Path(__file__).resolve().parent


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _write_markdown(payload: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 26 Component Attribution Pre-Registration",
        "",
        f"**Status:** `{payload['status']}`",
        "",
        "## Motivation",
        "",
        payload["motivation"],
        "",
        "## Formal Anchor",
        "",
        payload["formal_anchor"],
        "",
        "## Required Inputs",
        "",
        "| Input | Value |",
        "|---|---|",
    ]
    for key, value in payload["required_inputs"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Component Scope", "", "```json"])
    lines.append(json.dumps(payload["component_scope"], indent=2, sort_keys=True))
    lines.extend(["```", "", "## Method", ""])
    for item in payload["method"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Gates", "", "| Gate | Kind | Criterion |", "|---|---|---|"])
    for gate in payload["gates"]:
        lines.append(f"| `{gate['name']}` | `{gate['kind']}` | {gate['criterion']} |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- PASS status: `{payload['claim_boundary']['pass_status']}`",
            f"- GREY status: `{payload['claim_boundary']['grey_status']}`",
            f"- NULL status: `{payload['claim_boundary']['null_status']}`",
            f"- Claim if PASS: {payload['claim_boundary']['claim_if_pass']}",
            f"- Claim if NULL: {payload['claim_boundary']['claim_if_null']}",
            f"- Forbidden claims: {payload['claim_boundary']['forbidden_claims']}",
            "",
            "## Execution Order",
            "",
        ]
    )
    for item in payload["execution_order"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Validation", ""])
    invalid = {key: errors for key, errors in payload["validation"].items() if errors}
    if invalid:
        for key, errors in invalid.items():
            lines.append(f"- `{key}`: INVALID - {', '.join(errors)}")
    else:
        lines.append("- valid")
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", default="stage26_component_attribution_prereg_20260521.json")
    parser.add_argument("--out-md", default="STAGE26_COMPONENT_ATTRIBUTION_PREREG_20260521.md")
    args = parser.parse_args(argv)

    payload = stage26_payload()
    invalid = {key: errors for key, errors in payload["validation"].items() if errors}
    if invalid:
        raise SystemExit(f"Stage 26 preregistration is invalid: {invalid}")

    out_json = _resolve(args.out_json)
    out_md = _resolve(args.out_md)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, out_md)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "total_heads": payload["component_scope"]["attention_heads"]["total_heads"],
                "gates": [gate["name"] for gate in payload["gates"]],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
