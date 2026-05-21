"""Write the Stage 27F targeted MLP-neuron cover pre-registration."""

from __future__ import annotations

import json
from pathlib import Path

from stage27f_targeted_mlp_neuron_covers_spec import stage27f_payload


HERE = Path(__file__).resolve().parent
OUT_JSON = HERE / "stage27f_targeted_mlp_neuron_covers_prereg_20260521.json"
OUT_MD = HERE / "STAGE27F_TARGETED_MLP_NEURON_COVERS_PREREG_20260521.md"


def _write_md(payload: dict) -> None:
    lines = [
        "# Stage 27F Targeted MLP-Neuron Covers Pre-Registration",
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
    ]
    for key, value in payload["required_inputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Method", ""])
    for idx, step in enumerate(payload["method"], start=1):
        lines.append(f"{idx}. {step}")
    lines.extend(["", "## Gates", "", "| Gate | Kind | Criterion |", "|---|---|---|"])
    for gate in payload["gates"]:
        lines.append(f"| `{gate['name']}` | `{gate['kind']}` | {gate['criterion']} |")
    lines.extend(["", "## Claim Boundary", ""])
    for key, value in payload["claim_boundary"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Validation", ""])
    validation = payload.get("validation", {})
    if validation:
        for key, messages in validation.items():
            lines.append(f"- `{key}`: {'; '.join(messages)}")
    else:
        lines.append("- No validation errors.")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    payload = stage27f_payload()
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(payload)
    print(json.dumps({"json": str(OUT_JSON), "markdown": str(OUT_MD), "validation": payload["validation"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
