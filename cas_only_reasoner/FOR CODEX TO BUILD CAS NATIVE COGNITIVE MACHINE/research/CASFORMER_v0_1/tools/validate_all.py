"""Run the complete local CASformer v0.1 handoff gate and write one receipt."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HOMEBASE = ROOT.parents[1]
CORE_RECEIPT = ROOT / "artifacts" / "CASFORMER_V0_1_VALIDATION_RECEIPT.json"
COMPLETION_RECEIPT = ROOT / "artifacts" / "CASFORMER_V0_1_COMPLETION_RECEIPT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(label: str, args: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    nonempty_lines = [line.strip() for line in combined.splitlines() if line.strip()]
    test_match = re.search(r"(?P<count>\d+) passed(?:[^\n]*)", combined)
    return {
        "label": label,
        "argv": args,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "test_count": int(test_match.group("count")) if test_match else None,
        "last_output_line": nonempty_lines[-1] if nonempty_lines else "",
        "output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
    }


def main() -> None:
    python = sys.executable
    commands: list[dict[str, Any]] = []
    commands.append(
        run("source_manifest", [python, "tools/build_source_manifest.py"], ROOT)
    )
    if commands[-1]["passed"]:
        commands.append(
            run(
                "core_engineering_checks",
                [
                    python,
                    "tools/validate_reference.py",
                    "--output",
                    "artifacts/CASFORMER_V0_1_VALIDATION_RECEIPT.json",
                ],
                ROOT,
            )
        )
    if all(command["passed"] for command in commands):
        commands.append(run("casformer_pytest", [python, "-m", "pytest"], ROOT))
    if all(command["passed"] for command in commands):
        commands.append(run("cncm_pytest", [python, "-m", "pytest"], HOMEBASE))
    if all(command["passed"] for command in commands):
        commands.append(
            run("untrained_forward_example", [python, "examples/minimal_forward.py"], ROOT)
        )

    manifest_path = ROOT / "SOURCE_MANIFEST.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {}
    )
    core_receipt = (
        json.loads(CORE_RECEIPT.read_text(encoding="utf-8"))
        if CORE_RECEIPT.is_file()
        else {}
    )
    command_map = {command["label"]: command for command in commands}
    package_tests = command_map.get("casformer_pytest", {}).get("test_count")
    cncm_tests = command_map.get("cncm_pytest", {}).get("test_count")
    passed = (
        len(commands) == 5
        and all(command["passed"] for command in commands)
        and package_tests is not None
        and cncm_tests is not None
        and core_receipt.get("status") == "CORE_ENGINEERING_CHECKS_PASSED"
        and bool(core_receipt.get("checks"))
        and all(core_receipt.get("checks", {}).values())
    )
    receipt = {
        "schema_version": "cas.casformer.completion-receipt/0.1",
        "status": "REFERENCE_IMPLEMENTATION_COMPLETE" if passed else "VALIDATION_FAILED",
        "scope": "LOCAL_ENGINEERING_REFERENCE_ONLY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest": {
            "path": "SOURCE_MANIFEST.json",
            "sha256": sha256(manifest_path) if manifest_path.is_file() else None,
            "aggregate_sha256": manifest.get("aggregate_sha256"),
            "file_count": manifest.get("file_count"),
        },
        "core_receipt": {
            "path": "artifacts/CASFORMER_V0_1_VALIDATION_RECEIPT.json",
            "sha256": sha256(CORE_RECEIPT) if CORE_RECEIPT.is_file() else None,
            "check_count": len(core_receipt.get("checks", {})),
            "all_checks_passed": bool(core_receipt.get("checks"))
            and all(core_receipt.get("checks", {}).values()),
        },
        "git": core_receipt.get("git", {"commit_identity_scope": "UNAVAILABLE"}),
        "commands": commands,
        "tests": {
            "casformer_pytest_passed": package_tests,
            "existing_cncm_pytest_passed": cncm_tests,
        },
        "claims": {
            "software_reference_implementation": "IMPLEMENTED",
            "neural_training": "NOT_RUN",
            "language_capability": "NOT_ESTABLISHED",
            "reasoning_capability": "NOT_ESTABLISHED",
            "cas_specific_advantage": "NOT_ESTABLISHED",
            "cncm_kernel_integration": "ABSENT",
            "production_readiness": "NOT_ESTABLISHED",
        },
    }
    COMPLETION_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    COMPLETION_RECEIPT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
