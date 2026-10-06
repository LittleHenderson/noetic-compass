#!/usr/bin/env python3
"""Fail-closed verifier for the typed TKS v8 Gate 1 reference candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "docs"
    / "working"
    / "project_coherence"
    / "gate1"
    / "tks_v8"
    / "TKS_V8_CORE_PROTOTYPE_MANIFEST_v0.1.json"
)

EXPECTED_BOUND_PATHS = {
    "src/tks_v8_core/__init__.py",
    "src/tks_v8_core/category.py",
    "src/tks_v8_core/deterministic_lift.py",
    "src/tks_v8_core/normal_forms.py",
    "tests/tks_v8_core/test_category.py",
    "tests/tks_v8_core/test_deterministic_lift.py",
    "tests/tks_v8_core/test_manifest_boundaries.py",
    "tests/tks_v8_core/test_normal_forms.py",
    "docs/working/project_coherence/gate1/tks_v8/TKS_V8_CORE_FORMAL_SPEC_AND_PROOF_OBLIGATIONS_v0.1.md",
    "docs/working/project_coherence/gate1/formal/LEAN_PROOF_MANIFEST_v0.1.json",
    "docs/working/project_coherence/gate1/formal/lift_functor/LEAN_DETERMINISTIC_LIFT_FUNCTOR_MANIFEST_v0.1.json",
    "scripts/verify_tks_v8_gate1.py",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest["admission_ring"] == 4, "typed core escaped Ring 4")
    require(manifest["license_status"] == "NOT LICENSED", "typed core licensed a claim")
    require(
        manifest["integration_boundary"]["canonical_tks_v8_status"] == "OPEN",
        "prototype was mislabeled as canonical TKS v8",
    )
    require(
        manifest["formal_verification"]["status"] == "PARTIAL / PRESENT",
        "scoped Lean evidence is missing or overstated",
    )

    bindings = manifest.get("artifact_bindings")
    require(isinstance(bindings, list), "artifact bindings are missing")
    paths = [record.get("path") for record in bindings]
    require(len(paths) == len(set(paths)), "artifact bindings contain duplicate paths")
    require(set(paths) == EXPECTED_BOUND_PATHS, "artifact binding set drift")
    for record in bindings:
        path = ROOT / record["path"]
        require(path.is_file(), f"bound artifact is missing: {path}")
        require(path.stat().st_size == record["bytes"], f"byte-size drift: {path}")
        require(sha256(path) == record["sha256"], f"SHA-256 drift: {path}")

    require(
        set(manifest["implementation_files"])
        == {path for path in EXPECTED_BOUND_PATHS if path.startswith("src/tks_v8_core/")},
        "implementation file list and hash bindings disagree",
    )
    formal_ref = manifest["formal_verification"]["manifest_ref"]
    require(formal_ref in EXPECTED_BOUND_PATHS, "formal manifest is not hash-bound")
    require(
        manifest["validation_snapshot"]["tests_run"] == 20
        and manifest["validation_snapshot"]["result"] == "PASS",
        "validation snapshot is not the expected bounded PASS",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/tks_v8_core",
            "-v",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    output = completed.stdout + completed.stderr
    require(completed.returncode == 0, f"typed-core tests failed:\n{output}")
    require("Ran 20 tests" in output and "OK" in output, "test receipt count/result drift")

    print("Typed TKS v8 Gate 1 verification passed")
    print(f"  hash-bound artifacts: {len(bindings)}")
    print("  executable tests: 20 / PASS")
    print("  Lean status: PARTIAL / PRESENT (exact linked manifest)")
    print("  integration: OPEN / Ring 4 / NOT LICENSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"Typed TKS v8 Gate 1 verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
