"""Emit the Stage 22 CAS Harness ablation pre-registration artifacts.

This is a no-GPU scaffold. It records the ablation matrix, metric discipline,
and naming boundary before any Stage 22 execution run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stage22_harness_ablation_spec import stage22_preregistration_payload

_HERE = Path(__file__).resolve().parent


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = _HERE / candidate
    return candidate


def _write_markdown(payload: dict, out_md: Path) -> None:
    lines = [
        "# Stage 22 CAS Harness Ablation Pre-Registration",
        "",
        "**Status:** `PREREGISTERED_NO_GPU`",
        "",
        "## Scope",
        "",
        "Stage 22 ablates the external **CAS Harness** product around frozen open-weight model artifacts.",
        "It does not ablate the future CAS Native inner loop. That later work should be named",
        "**CAS Native Cognitive Runtime**, not CAS Harness, to avoid product ambiguity.",
        "",
        "## Naming Boundary",
        "",
        "| Term | Meaning |",
        "|---|---|",
    ]
    for term, meaning in payload["naming_boundary"].items():
        lines.append(f"| `{term}` | {meaning} |")

    lines.extend(
        [
            "",
            "## Conditions",
            "",
            "| Mode | Status | Active layers | Hypothesis | Boundary |",
            "|---|---|---|---|---|",
        ]
    )
    for condition in payload["conditions"]:
        active = [
            key
            for key, value in condition["layers"].items()
            if value is True or (isinstance(value, str) and value != "OFF")
        ]
        lines.append(
            "| "
            f"`{condition['mode']}` | "
            f"`{condition['status']}` | "
            f"{', '.join(active)} | "
            f"{condition['hypothesis']} | "
            f"{condition['boundary']} |"
        )

    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Metric | Direction | Why it is required |",
            "|---|---|---|",
        ]
    )
    for metric in payload["metrics"]:
        lines.append(
            f"| `{metric['name']}` | `{metric['direction']}` | {metric['rationale']} |"
        )

    lines.extend(
        [
            "",
            "## Required Discipline",
            "",
            "- Report floor and ceiling comparators; do not interpret a harness number alone.",
            "- Pair suppression rate with useful-output rate and coverage.",
            "- Treat `BALANCED` as the default customer mode unless Stage 22 data overturns it.",
            "- Treat `HIGH_PRECISION` as opt-in for regulator/legal/safety workflows.",
            "- Treat `MAX_COVERAGE_TRIAGE` as opt-in for human-review queues.",
            "- Do not claim visible free-form generation control from likelihood-only evidence.",
            "",
            "## Validation",
            "",
        ]
    )
    for mode, errors in payload["validation"].items():
        if errors:
            lines.append(f"- `{mode}`: INVALID — {', '.join(errors)}")
        else:
            lines.append(f"- `{mode}`: valid")

    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-json",
        default="stage22_cas_harness_ablation_prereg_20260519.json",
    )
    parser.add_argument(
        "--out-md",
        default="STAGE22_CAS_HARNESS_ABLATION_PREREG_20260519.md",
    )
    args = parser.parse_args(argv)

    payload = stage22_preregistration_payload()
    invalid = {
        mode: errors for mode, errors in payload["validation"].items() if errors
    }
    if invalid:
        raise SystemExit(f"Stage 22 pre-registration is invalid: {invalid}")

    out_json = _resolve(args.out_json)
    out_md = _resolve(args.out_md)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, out_md)
    print(
        json.dumps(
            {
                "status": "PREREGISTERED_NO_GPU",
                "conditions": [condition["mode"] for condition in payload["conditions"]],
                "default_customer_mode": payload["default_customer_mode"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

