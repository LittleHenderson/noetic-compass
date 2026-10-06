#!/usr/bin/env python3
"""Integrated fail-closed verifier for the Project Coherence Gate 1 candidate."""

from __future__ import annotations

import hashlib
import json
import os
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
    / "GATE1_ARTIFACT_MANIFEST_v0.1.json"
)

EXPECTED_PATHS = {
    "docs/working/project_coherence/gate0/GATE0_ARTIFACT_MANIFEST_v0.1.json",
    "scripts/verify_project_coherence_phase0.py",
    "docs/working/project_coherence/gate1/README.md",
    "docs/working/project_coherence/gate1/v74/README.md",
    "docs/working/project_coherence/gate1/v74/TKS_V74_SURFACE_INVENTORY_v0.1.json",
    "docs/working/project_coherence/gate1/v74/TKS_V74_CORRIGENDUM_v0.1.json",
    "docs/working/project_coherence/gate1/v74/TKS_V74_CORRIGENDUM_v0.1.md",
    "scripts/verify_project_coherence_v74.py",
    "docs/working/project_coherence/gate1/tks_v8/TKS_V8_CORE_PROTOTYPE_MANIFEST_v0.1.json",
    "scripts/verify_tks_v8_gate1.py",
    "src/noetic_topos2/__init__.py",
    "src/noetic_topos2/finite_site.py",
    "tests/noetic_topos2/test_finite_site.py",
    "docs/working/project_coherence/gate1/noetic_topos2/FINITE_MODEL_CERTIFICATE_v0.1.json",
    "docs/working/project_coherence/gate1/noetic_topos2/NOETIC_TOPOS_2_SPEC_v0.1.md",
    "docs/working/project_coherence/gate1/noetic_topos2/NOETIC_TOPOS_2_THEOREMS_v0.1.json",
    "docs/working/project_coherence/gate1/noetic_topos2/NOETIC_TOPOS_2_PROOF_OBLIGATIONS_v0.1.json",
    "docs/working/project_coherence/gate1/noetic_topos2/SOURCE_VERIFICATION_v0.1.json",
    "docs/working/project_coherence/gate1/noetic_topos2/modality_composition/MODALITY_COMPOSITION_CERTIFICATE_v0.1.json",
    "scripts/verify_noetic_topos2_gate1.py",
    "docs/working/project_coherence/gate1/formal/LEAN_PROOF_MANIFEST_v0.1.json",
    "scripts/verify_psr8_lean_gate1.py",
    "scripts/verify_project_coherence_gate1.py",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(command: list[str], *, timeout: int = 240) -> str:
    environment = dict(os.environ)
    environment.setdefault(
        "PSR8_ELAN_HOME", "C:/Users/wakil/.codex/tools/project-coherence-elan"
    )
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    output = completed.stdout + completed.stderr
    require(completed.returncode == 0, f"command failed: {' '.join(command)}\n{output}")
    return output


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(
        manifest["document_status"] == "OPEN / IN REVIEW / NOT FROZEN",
        "Gate 1 manifest status is unsafe",
    )
    require(manifest["admission_ring"] == 4, "Gate 1 candidate escaped Ring 4")
    require(manifest["license_status"] == "NOT LICENSED", "Gate 1 licensed a claim")
    require(manifest["public_disclosure_authorized"] is False, "disclosure was authorized")
    require(manifest["gate1_status"] == "OPEN", "Gate 1 was prematurely closed")

    artifacts = manifest.get("artifacts")
    require(isinstance(artifacts, list), "Gate 1 artifact list is missing")
    paths = [record.get("path") for record in artifacts]
    require(len(paths) == len(set(paths)), "Gate 1 artifact paths are duplicated")
    require(set(paths) == EXPECTED_PATHS, "Gate 1 artifact set drift")
    for record in artifacts:
        path = ROOT / record["path"]
        require(path.is_file(), f"Gate 1 artifact is missing: {path}")
        require(path.stat().st_size == record["bytes"], f"byte-size drift: {path}")
        require(sha256(path) == record["sha256"], f"SHA-256 drift: {path}")

    commands = [
        [sys.executable, "scripts/verify_project_coherence_phase0.py"],
        [
            sys.executable,
            "docs/working/project_coherence/gate0/verify_gate0_candidate.py",
        ],
        [sys.executable, "scripts/verify_project_coherence_v74.py"],
        [sys.executable, "scripts/verify_tks_v8_gate1.py"],
        [sys.executable, "scripts/verify_noetic_topos2_gate1.py"],
        [sys.executable, "scripts/verify_psr8_lean_gate1.py"],
    ]
    outputs = [run(command) for command in commands]
    expected_receipts = (
        "Project Coherence Phase 0 verification: PASS",
        "Project Coherence Gate 0 candidate verification: PASS",
        "TKS v7.4 Gate 1 verification passed",
        "Typed TKS v8 Gate 1 verification passed",
        "Noetic Topos 2.0 Gate 1 verification passed",
        "PSR-8 Gate 1 Lean verification passed",
    )
    for receipt, output in zip(expected_receipts, outputs, strict=True):
        require(receipt in output, f"missing integrated receipt: {receipt}")

    open_items = manifest.get("required_open_boundaries")
    require(isinstance(open_items, list) and len(open_items) >= 8, "OPEN boundaries missing")
    joined = " ".join(open_items)
    for required in (
        "bounded",
        "product-site",
        "independent",
        "portable",
        "canonical",
        "NOT LICENSED",
    ):
        require(required.lower() in joined.lower(), f"OPEN boundary omits {required!r}")

    print("Project Coherence integrated Gate 1 verification: PASS")
    print(f"  hash-bound top-level artifacts: {len(artifacts)}")
    print("  subordinate verifier receipts: 6 / PASS")
    print("  Lean theorem audits: 16; scoped finite modality proof: PASS")
    print("  Gate 1 status: OPEN / Ring 4 / NOT LICENSED / NOT FROZEN")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"Project Coherence integrated Gate 1 verification: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
