#!/usr/bin/env python3
"""Fail-closed verifier for the PSR-8 Gate 1 Lean proof seed."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
LEAN_DIR = ROOT / "formal" / "lean"
MANIFEST = (
    ROOT
    / "docs"
    / "working"
    / "project_coherence"
    / "gate1"
    / "formal"
    / "LEAN_PROOF_MANIFEST_v0.1.json"
)
LIFT_FUNCTOR_MANIFEST = (
    ROOT
    / "docs"
    / "working"
    / "project_coherence"
    / "gate1"
    / "formal"
    / "lift_functor"
    / "LEAN_DETERMINISTIC_LIFT_FUNCTOR_MANIFEST_v0.1.json"
)
DEFAULT_ISOLATED_ELAN_HOME = Path(
    "C:/Users/wakil/.codex/tools/project-coherence-elan"
)
COMMAND_TIMEOUT_SECONDS = 120
ALLOWED_STANDARD_AXIOMS = {"propext"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def tool_path(name: str) -> tuple[Path, Path | None]:
    configured = os.environ.get("PSR8_ELAN_HOME") or os.environ.get("ELAN_HOME")
    elan_home = Path(configured) if configured else DEFAULT_ISOLATED_ELAN_HOME
    candidate = elan_home / "bin" / f"{name}.exe"
    if candidate.is_file():
        return candidate, elan_home
    discovered = shutil.which(name)
    require(discovered is not None, f"{name} is unavailable; install the pinned Lean toolchain")
    return Path(discovered), None


def run(command: list[str], *, env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=LEAN_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    output = completed.stdout + completed.stderr
    require(completed.returncode == 0, f"command failed: {' '.join(command)}\n{output}")
    return output


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lift_manifest = json.loads(LIFT_FUNCTOR_MANIFEST.read_text(encoding="utf-8"))
    require(manifest["admission_ring"] == 4, "formal seed escaped Ring 4")
    require(manifest["license_status"] == "NOT LICENSED", "formal seed licensed a claim")
    require(manifest["toolchain"]["lean"] == "4.32.1", "Lean toolchain is not pinned")
    require(
        manifest["validation_snapshot"]["project_specific_axioms_declared"] is False,
        "project-specific axioms are not allowed in the Gate 1 seed",
    )
    require(
        lift_manifest["evidence_ring"] == "RING_4"
        and lift_manifest["license_status"] == "NOT_LICENSED"
        and lift_manifest["public_release_authorized"] is False,
        "lift-functor subreceipt escaped its conservative boundary",
    )
    require(
        len(lift_manifest["verification"]["theorem_audits"]) == 9
        and all(
            not record["axiom_dependencies"]
            for record in lift_manifest["verification"]["theorem_audits"]
        ),
        "lift-functor subreceipt does not record nine axiom-free audits",
    )
    require(
        any("finite-sum" in item.lower() for item in lift_manifest["open_claims"]),
        "lift-functor numerical matrix boundary disappeared",
    )
    deterministic_scope = next(
        module["scope"]
        for module in manifest["checked_modules"]
        if module["path"].endswith("DeterministicLiftCounterexample.lean")
    )
    require(
        "not present" in deterministic_scope and "literal" in deterministic_scope,
        "deterministic-lift formal scope overclaims matrix/trace/rank bridges",
    )
    functor_scope = next(
        module["scope"]
        for module in manifest["checked_modules"]
        if module["path"].endswith("DeterministicLiftFunctor.lean")
    )
    require(
        "Finite-sum numerical matrix multiplication" in functor_scope
        and "not modeled" in functor_scope,
        "lift-functor scope overclaims numerical matrix multiplication",
    )

    for artifact in manifest["source_artifacts"]:
        path = ROOT / artifact["path"]
        require(path.is_file(), f"missing Lean source artifact: {path}")
        require(path.stat().st_size == artifact["bytes"], f"byte-size drift: {path}")
        require(sha256(path) == artifact["sha256"], f"SHA-256 drift: {path}")
        if path.suffix == ".lean":
            source_text = path.read_text(encoding="utf-8")
            require(
                re.search(r"(?m)^\s*axiom\b", source_text) is None,
                f"project-specific axiom declaration found: {path}",
            )

    lake, elan_home = tool_path("lake")
    lean, lean_home = tool_path("lean")
    require(elan_home == lean_home, "lake and lean were resolved from different toolchains")
    env = dict(os.environ)
    if elan_home is not None:
        env["ELAN_HOME"] = str(elan_home)

    version = run([str(lean), "--version"], env=env)
    require("Lean (version 4.32.1" in version, f"unexpected Lean version:\n{version}")
    require(
        manifest["toolchain"]["lean_commit"] in version,
        "Lean commit does not match the manifest",
    )
    lake_lean_version = run([str(lake), "env", "lean", "--version"], env=env)
    require(
        "Lean (version 4.32.1" in lake_lean_version
        and manifest["toolchain"]["lean_commit"] in lake_lean_version,
        f"lake project environment resolved a different Lean:\n{lake_lean_version}",
    )

    build_output = run([str(lake), "build"], env=env)
    audit_output = run([str(lake), "env", "lean", "ProofAudit.lean"], env=env)
    lift_audit_output = run(
        [str(lake), "env", "lean", "DeterministicLiftFunctorAudit.lean"],
        env=env,
    )
    combined_audit_output = audit_output + lift_audit_output
    lowered = (build_output + combined_audit_output).lower()
    for prohibited in ("sorryax", "declaration uses 'sorry'", "build failed"):
        require(prohibited not in lowered, f"prohibited Lean audit token: {prohibited}")

    dependency_lines = [
        line.strip()
        for line in combined_audit_output.splitlines()
        if "depend" in line and "axiom" in line
    ]
    require(len(dependency_lines) == 16, "proof audit did not report all sixteen theorems")
    allowed = set(manifest["validation_snapshot"]["allowed_kernel_axiom_dependencies"])
    require(
        allowed == ALLOWED_STANDARD_AXIOMS,
        "manifest axiom allowlist drifted from the hardcoded Gate 1 policy",
    )
    for line in dependency_lines:
        match = re.search(r"depends on axioms: \[(.*)\]", line)
        if not match:
            require("does not depend on any axioms" in line, f"unparsed axiom report: {line}")
            continue
        dependencies = {item.strip() for item in match.group(1).split(",") if item.strip()}
        require(dependencies <= allowed, f"unexpected axiom dependency: {line}")

    print("PSR-8 Gate 1 Lean verification passed")
    print("  Lean: 4.32.1 at f054605aea4b840552cca2e725580bffd1e1b704")
    print("  Lake build: PASS")
    print("  theorem axiom audits: 16 (no sorry/project axioms; standard propext allowed)")
    print("  deterministic-lift identity/composition: kernel-checked at entry/basis/support levels")
    print("  matrix/Gram/trace/rank bridge: OPEN and explicitly scoped")
    print("  admission: Ring 4 / NOT LICENSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"PSR-8 Gate 1 Lean verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
