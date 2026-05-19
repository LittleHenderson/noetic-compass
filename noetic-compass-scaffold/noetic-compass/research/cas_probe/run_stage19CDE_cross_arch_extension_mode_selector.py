"""Build Stage 19CDE user-selectable Verification Stack modes for the Phi-2 /
TinyLlama-1.1B cross-architecture extension.

This script does not retrain probes. It reads the locked Stage 19BDE report
(`stage19BDE_cross_arch_extension_foundation_verification_stack_20260519.json`)
and turns the already-measured component ladder into user-facing operating
modes, exactly mirroring Stage 19C:

* HIGH_PRECISION -> final stack
* BALANCED -> factor-consistent component
* MAX_COVERAGE_TRIAGE -> ensemble-only component

Per-mode pre-registered targets are identical to Stage 19C:

* HIGH_PRECISION: accepted_accuracy >= 0.98, silent_error_rate <= 0.02
* BALANCED: accepted_accuracy >= 0.94, coverage >= 0.80, silent_error_rate <= 0.06
* MAX_COVERAGE_TRIAGE: accepted_accuracy >= 0.88, coverage >= 0.88

Status taxonomy mirrors Stage 19C: `MODE_SELECTOR_READY` overall;
`MODE_SUPPORTED_CROSS_ARCH` / `MODE_PARTIAL` / `MODE_NOT_SUPPORTED` per mode.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent

_MODES = {
    "HIGH_PRECISION": {
        "source": "stack",
        "target": {"accepted_accuracy_min": 0.980, "silent_error_rate_max": 0.020},
        "recommended_use": "Regulator, legal, safety, and high-trust review where suppression is preferred over a wrong accepted answer.",
        "claim_boundary": "Highest precision; lower coverage is expected.",
    },
    "BALANCED": {
        "source": "factor_consistent",
        "target": {
            "coverage_min": 0.800,
            "accepted_accuracy_min": 0.940,
            "silent_error_rate_max": 0.060,
        },
        "recommended_use": "Normal customer audit flow where throughput matters but factor conflicts should still be suppressed.",
        "claim_boundary": "Coverage restored above 80% with lower precision than HIGH_PRECISION.",
    },
    "MAX_COVERAGE_TRIAGE": {
        "source": "ensemble_only",
        "target": {"coverage_min": 0.880, "accepted_accuracy_min": 0.880},
        "recommended_use": "Exploratory triage and batch review queues where human review remains expected.",
        "claim_boundary": "Triage mode only; not a licensed high-confidence claim mode.",
    },
}

_DEFAULT_MODE = "BALANCED"
_DEFAULT_RATIONALE = (
    "BALANCED is the new-customer default because it restores the Stage 19BDE "
    "coverage floor while retaining factor-decomposition agreement. "
    "HIGH_PRECISION remains opt-in for regulator/legal workflows; "
    "MAX_COVERAGE_TRIAGE remains opt-in for human-review queues."
)


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _component_metrics(model_report: dict[str, Any], source: str) -> dict[str, Any]:
    block = model_report[source]
    if source == "stack":
        accepted_accuracy = float(block["accepted_accuracy"])
        coverage = float(block["coverage"])
        silent_error = float(block["silent_error_rate"])
        suppressed = float(block["suppressed_rate"])
        accepted = int(block["accepted"])
    else:
        accepted_accuracy = float(block["accuracy"])
        coverage = float(block["coverage"])
        silent_error = 1.0 - accepted_accuracy
        suppressed = 1.0 - coverage
        accepted = int(block["accepted"])
    return {
        "accepted": accepted,
        "accepted_accuracy": accepted_accuracy,
        "coverage": coverage,
        "silent_error_rate": silent_error,
        "suppressed_rate": suppressed,
    }


def _passes(metrics: dict[str, Any], target: dict[str, float]) -> bool:
    if "coverage_min" in target and float(metrics["coverage"]) < float(target["coverage_min"]):
        return False
    if "accepted_accuracy_min" in target and float(metrics["accepted_accuracy"]) < float(target["accepted_accuracy_min"]):
        return False
    if "silent_error_rate_max" in target and float(metrics["silent_error_rate"]) > float(target["silent_error_rate_max"]):
        return False
    return True


def _overall(statuses: list[bool]) -> str:
    if statuses and all(statuses):
        return "MODE_SUPPORTED_CROSS_ARCH"
    if any(statuses):
        return "MODE_PARTIAL"
    return "MODE_NOT_SUPPORTED"


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 19CDE Verification Mode Selector (Phi-2 / TinyLlama-1.1B Cross-Architecture Extension)",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        "| Mode | Cross-arch status | Product use |",
        "|---|---|---|",
    ]
    for mode, row in report["modes"].items():
        lines.append(f"| `{mode}` | `{row['cross_arch_status']}` | {row['recommended_use']} |")

    lines.extend(["", "## Per-Model Mode Table", ""])
    for mode, row in report["modes"].items():
        lines.extend(
            [
                f"### `{mode}`",
                "",
                row["claim_boundary"],
                "",
                "| Model | Meets target | Accepted acc | Coverage | Silent error | Suppressed |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for model in row["models"].values():
            lines.append(
                "| "
                f"{model['display_name']} | `{str(model['meets_target']).lower()}` | "
                f"`{model['accepted_accuracy']:.4f}` | "
                f"`{model['coverage']:.4f}` | "
                f"`{model['silent_error_rate']:.4f}` | "
                f"`{model['suppressed_rate']:.4f}` |"
            )
        lines.append("")

    lines.extend(
        [
            "## Product Boundary",
            "",
            "Users can choose the operating mode. They cannot choose away the tradeoff:",
            "",
            "- `HIGH_PRECISION` gives the strongest accepted predictions and suppresses more.",
            "- `BALANCED` is the default new-customer mode: it recovers coverage with lower accepted accuracy.",
            "- `MAX_COVERAGE_TRIAGE` is for surfacing candidates, not final high-confidence claims.",
            "",
            f"Default mode: `{report['default_mode']}`.",
            "",
            report["default_rationale"],
            "",
            "## Source Component Verification",
            "",
            report["source_component_verification"],
            "",
            "Gold labels are used only to score these mode profiles after the fact. Runtime mode selection uses the same non-oracle signals from Stage 19BDE.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="stage19BDE_cross_arch_extension_foundation_verification_stack_20260519.json",
    )
    parser.add_argument(
        "--out-json",
        default="stage19CDE_cross_arch_extension_mode_selector_20260519.json",
    )
    parser.add_argument(
        "--out-md",
        default="STAGE19CDE_CROSS_ARCH_EXTENSION_MODE_SELECTOR_20260519.md",
    )
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    out_json = _resolve(args.out_json)
    out_md = _resolve(args.out_md)
    stage19bde = json.loads(input_path.read_text(encoding="utf-8"))

    modes: dict[str, Any] = {}
    for mode, spec in _MODES.items():
        model_rows: dict[str, Any] = {}
        pass_flags: list[bool] = []
        for model_key, model_report in stage19bde["models"].items():
            metrics = _component_metrics(model_report, str(spec["source"]))
            meets = _passes(metrics, dict(spec["target"]))
            pass_flags.append(meets)
            model_rows[model_key] = {
                "display_name": model_report["display_name"],
                "source_component": spec["source"],
                "meets_target": meets,
                **metrics,
            }
        modes[mode] = {
            "source_component": spec["source"],
            "target": spec["target"],
            "cross_arch_status": _overall(pass_flags),
            "recommended_use": spec["recommended_use"],
            "claim_boundary": spec["claim_boundary"],
            "models": model_rows,
        }

    report = {
        "status": "MODE_SELECTOR_READY",
        "schema_version": "stage19CDE_cross_arch_extension_mode_selector_v1",
        "pre_registration": "STAGE19DE_CROSS_ARCH_EXTENSION_GATES_20260519.md",
        "input_report": input_path.name,
        "modes": modes,
        "default_mode": _DEFAULT_MODE,
        "default_rationale": _DEFAULT_RATIONALE,
        "source_component_verification": (
            "Source review confirms `factor_consistent` means Foundation factor-decomposition agreement: "
            "the Stage 19BDE runner first requires 2-of-3 Foundation readout consensus, then separately "
            "requires Drive and Register readout consensus, recomposes Drive x Register into a 28-way "
            "Foundation label, and suppresses the row as `factor_conflicted` if the recomposed label does "
            "not match the Foundation consensus."
        ),
        "boundary": (
            "Stage 19CDE is product-mode packaging over the locked Stage 19BDE result. "
            "It is not a fresh hidden-state test and does not upgrade Stage 19BDE's strict product-gate "
            "status. It extends the Stage 19C Mode Selector to the Phi-2 and TinyLlama-1.1B cross-"
            "architecture additions; the OLMo-1B / Qwen2.5-1.5B Stage 19C result is unchanged."
        ),
    }
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(json.dumps({"status": report["status"], "modes": {k: v["cross_arch_status"] for k, v in modes.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
