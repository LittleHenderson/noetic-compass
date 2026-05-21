"""Emit Stage 28B Noetic colloquialism realization pre-registration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from stage28b_noetic_colloquialism_realization_spec import stage28b_payload


_HERE = Path(__file__).resolve().parent


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _write_markdown(payload: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 28B Noetic Colloquialism Realization Pre-Registration",
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
    lines.extend(["", "## Locked Colloquialism Fixture", "", "| Noetic | Name | Phrase |", "|---|---|---|"])
    for row in payload["colloquialism_fixture"]:
        lines.append(f"| `{row['noetic']}` | {row['name']} | {row['phrase']} |")
    lines.extend(["", "## Method", ""])
    for item in payload["method"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Gates", "", "| Gate | Kind | Criterion |", "|---|---|---|"])
    for gate in payload["gates"]:
        lines.append(f"| `{gate['name']}` | `{gate['kind']}` | {gate['criterion']} |")
    lines.extend(["", "## Claim Boundary", ""])
    for key, value in payload["claim_boundary"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Execution Order", ""])
    for item in payload["execution_order"]:
        lines.append(f"- {item}")
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
    parser.add_argument("--out-json", default="stage28b_noetic_colloquialism_prereg_20260521.json")
    parser.add_argument("--out-md", default="STAGE28B_NOETIC_COLLOQUIALISM_PREREG_20260521.md")
    args = parser.parse_args(argv)

    payload = stage28b_payload()
    invalid = {key: errors for key, errors in payload["validation"].items() if errors}
    if invalid:
        raise SystemExit(f"Stage 28B pre-registration is invalid: {invalid}")

    out_json = _resolve(args.out_json)
    out_md = _resolve(args.out_md)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, out_md)
    print(json.dumps({"status": payload["status"], "stage": payload["stage"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
