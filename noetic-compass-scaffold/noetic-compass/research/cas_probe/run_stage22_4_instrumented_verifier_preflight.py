"""Stage 22.4 preflight for the instrumented Stage 19B verifier.

This does not rerun OLMo/Qwen probes. It checks whether the Stage 19B runner
can emit the Stage 22.2 diagnostic row contract and whether the local activation
artifacts needed for a full rerun are present.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "run_stage19b_cross_arch_foundation_verification_stack.py"
OUT_JSON = ROOT / "stage22_4_instrumented_verifier_preflight_20260519.json"
OUT_MD = ROOT / "STAGE22_4_INSTRUMENTED_VERIFIER_PREFLIGHT_20260519.md"

REQUIRED_FIELDS = [
    "rpm_satisfaction",
    "rpm_gate_decision",
    "lacunarity_scores",
    "gap_map_summary",
    "lacunarity_gate_decision",
    "inversion_axis_scores",
    "inversion_flag_count",
    "inversion_gate_decision",
    "gate_decisions",
]

ACTIVATION_ARTIFACTS = [
    ROOT / "stage15_olmo1b_activations_20260519.npz",
    ROOT / "stage16_qwen15b_activations_20260519.npz",
]


def build_report() -> dict[str, Any]:
    source = RUNNER.read_text(encoding="utf-8")
    required_field_presence = {field: field in source for field in REQUIRED_FIELDS}
    activation_presence = {path.name: path.exists() for path in ACTIVATION_ARTIFACTS}
    runner_ready = all(
        [
            "--emit-diagnostics" in source,
            "_diagnostic_contract_row" in source,
            "diagnostic_rows" in source,
            all(required_field_presence.values()),
        ]
    )
    local_artifacts_present = all(activation_presence.values())
    can_run_locally = runner_ready and local_artifacts_present
    status = (
        "READY_TO_RUN_LOCALLY"
        if can_run_locally
        else "RUNNER_PATCH_READY_LOCAL_ARTIFACTS_MISSING"
        if runner_ready
        else "RUNNER_PATCH_INCOMPLETE"
    )
    return {
        "status": status,
        "schema_version": "stage22_4_instrumented_verifier_preflight_v1",
        "runner": RUNNER.name,
        "runner_ready": runner_ready,
        "emit_diagnostics_flag_present": "--emit-diagnostics" in source,
        "diagnostic_helper_present": "_diagnostic_contract_row" in source,
        "diagnostic_rows_present": "diagnostic_rows" in source,
        "required_field_presence": required_field_presence,
        "activation_artifacts": activation_presence,
        "local_artifacts_present": local_artifacts_present,
        "can_run_locally": can_run_locally,
        "rpm_lacunarity_proxy_ready": runner_ready,
        "inversion_numeric_ready": False,
        "boundary": (
            "The runner now emits Stage 22.2-compatible row fields. RPM and "
            "lacunarity are runtime proxy diagnostics. Inversion fields are "
            "reserved and emitted as not_evaluated until a real inversion "
            "scanner is wired into the verifier."
        ),
        "pod_command": (
            "python research/cas_probe/run_stage19b_cross_arch_foundation_verification_stack.py "
            "--models olmo1b,qwen15b --emit-diagnostics "
            "--out-report stage22_4_instrumented_cross_arch_verification_stack_20260519.json "
            "--out-md STAGE22_4_INSTRUMENTED_CROSS_ARCH_VERIFICATION_STACK_20260519.md"
        ),
    }


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Stage 22.4 Instrumented Verifier Preflight",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Checks",
        "",
        f"- Runner patched: `{report['runner_ready']}`",
        f"- `--emit-diagnostics` flag present: `{report['emit_diagnostics_flag_present']}`",
        f"- Diagnostic row helper present: `{report['diagnostic_helper_present']}`",
        f"- Diagnostic rows emitted by runner: `{report['diagnostic_rows_present']}`",
        f"- Local activation artifacts present: `{report['local_artifacts_present']}`",
        f"- Can run locally: `{report['can_run_locally']}`",
        "",
        "## Required Fields",
        "",
        "| Field | Present |",
        "|---|---:|",
    ]
    for field, present in report["required_field_presence"].items():
        lines.append(f"| `{field}` | `{present}` |")
    lines.extend(["", "## Activation Artifacts", "", "| Artifact | Present |", "|---|---:|"])
    for name, present in report["activation_artifacts"].items():
        lines.append(f"| `{name}` | `{present}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            str(report["boundary"]),
            "",
            "## Pod Command",
            "",
            "```bash",
            str(report["pod_command"]),
            "```",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = build_report()
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report)
    print(json.dumps({"status": report["status"], "can_run_locally": report["can_run_locally"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
