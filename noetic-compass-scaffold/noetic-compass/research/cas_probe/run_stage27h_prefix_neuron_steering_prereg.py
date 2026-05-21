"""Write the Stage 27H prefix-plus-neuron steering pre-registration."""

from __future__ import annotations

import json
from pathlib import Path

from stage27h_prefix_neuron_steering_spec import stage27h_payload


_HERE = Path(__file__).resolve().parent


def _write_md(payload: dict, out_md: Path) -> None:
    lines = [
        "# Stage 27H Prefix-Plus-Neuron Steering Pre-Registration",
        "",
        f"**Status:** `{payload['status']}`",
        "",
        "## Motivation",
        "",
        payload["motivation"],
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
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"]["scope_boundary"],
            "",
            "## Forbidden Claims",
            "",
            payload["claim_boundary"]["forbidden_claims"],
            "",
            "## Validation",
            "",
            f"`{payload['validation']}`",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    payload = stage27h_payload()
    out_json = _HERE / "stage27h_prefix_neuron_steering_prereg_20260521.json"
    out_md = _HERE / "STAGE27H_PREFIX_NEURON_STEERING_PREREG_20260521.md"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(payload, out_md)
    print(json.dumps({"status": payload["status"], "validation": payload["validation"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
