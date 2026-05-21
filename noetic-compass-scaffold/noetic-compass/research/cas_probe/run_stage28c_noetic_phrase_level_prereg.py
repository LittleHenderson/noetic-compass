"""Emit Stage 28C Noetic phrase-level realization pre-registration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from stage28c_noetic_phrase_level_realization_spec import stage28c_payload


_HERE = Path(__file__).resolve().parent


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _write_markdown(payload: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 28C Noetic Phrase-Level Realization Pre-Registration",
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
    parser.add_argument("--out-json", default="stage28c_noetic_phrase_level_prereg_20260521.json")
    parser.add_argument("--out-md", default="STAGE28C_NOETIC_PHRASE_LEVEL_PREREG_20260521.md")
    args = parser.parse_args(argv)

    payload = stage28c_payload()
    invalid = {key: errors for key, errors in payload["validation"].items() if errors}
    if invalid:
        raise SystemExit(f"Stage 28C pre-registration is invalid: {invalid}")

    out_json = _resolve(args.out_json)
    out_md = _resolve(args.out_md)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, out_md)
    print(json.dumps({"status": payload["status"], "stage": payload["stage"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
