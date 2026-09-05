"""Local syntax and pure storage/link checks; no model or tensor work."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class NoNeuralImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"torch", "tensorflow", "jax", "casformer"}:
            raise RuntimeError("LOCAL_NEURAL_IMPORT_FORBIDDEN:" + fullname)
        return None


def sources():
    return {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest()
            for directory in ("cas_meta3", "tests", "tools")
            for p in sorted((ROOT / directory).rglob("*.py"))}


def protected():
    manifest = json.loads((ROOT.parent / "CAS_META_1_LEARNED_SELECTION" /
                           "BASELINE_MANIFEST.json").read_bytes())
    for item in manifest["files"]:
        path = (ROOT.parent / item["path"]).resolve()
        if (not path.is_relative_to(ROOT.parent)
                or sha256(path.read_bytes()).hexdigest() != item["sha256"]):
            raise ValueError("PROTECTED_BASELINE_CHANGED:" + item["path"])
    return {"baseline_sha": manifest["baseline_sha"],
            "files_verified": len(manifest["files"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    sys.meta_path.insert(0, NoNeuralImports())
    from cas_meta3.registry import dependency_receipt, verify_dependency_git
    if args.child:
        if args.scratch is None:
            raise ValueError("EXPLICIT_TEST_SCRATCH_REQUIRED")
        dependency_receipt()
        import pytest
        return pytest.main(["tests", "-q", "-p", "no:cacheprovider",
                            "--basetemp=" + str(args.scratch / "pytest"),
                            "--junitxml=" + str(args.output / "tests.xml")])
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "records") or output.exists():
        raise ValueError("NEW_VALIDATION_RECORD_DIRECTORY_REQUIRED")
    before, dependency_before, hashes = protected(), dependency_receipt(), sources()
    git_pin_check = verify_dependency_git()
    for name in hashes:
        ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)
    output.mkdir(parents=True)
    # Windows Python startup can stall with a deeply nested TEMP directory.
    # Use the shortest ancestor CNCM homebase, without leaving its write scope.
    homebases = [p for p in ROOT.parents if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"]
    if not homebases:
        raise ValueError("CNCM_HOMEBASE_REQUIRED")
    scratch = homebases[-1] / "_tmp" / ("meta3-" + uuid4().hex[:12])
    if not scratch.is_relative_to(homebases[-1]):
        raise ValueError("TEST_SCRATCH_OUTSIDE_HOMEBASE")
    runtime_tmp = scratch / "temp"
    runtime_tmp.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-B", str(Path(__file__).resolve()),
               "--child", "--output", str(output), "--scratch", str(scratch)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", CUDA_VISIBLE_DEVICES="",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               TEMP=str(runtime_tmp), TMP=str(runtime_tmp), TMPDIR=str(runtime_tmp),
               CAS_META1_RUN_GPU_TESTS="0", CAS_META2_RUN_GPU_TESTS="0")
    started = time.monotonic()
    failure = None
    try:
        run = subprocess.run(command, cwd=ROOT, env=env, text=True,
                             capture_output=True, timeout=180)
        stdout, stderr, code = run.stdout, run.stderr, run.returncode
    except subprocess.TimeoutExpired as error:
        stdout = (error.stdout or b"").decode("utf-8", errors="replace") if isinstance(error.stdout, bytes) else error.stdout or ""
        stderr = (error.stderr or b"").decode("utf-8", errors="replace") if isinstance(error.stderr, bytes) else error.stderr or ""
        code, failure = 124, "PURE_TEST_TIMEOUT"
    (output / "stdout.txt").write_text(stdout, encoding="utf-8")
    (output / "stderr.txt").write_text(stderr, encoding="utf-8")
    counts = None
    if (output / "tests.xml").is_file():
        xml = ET.parse(output / "tests.xml").getroot()
        suites = [xml] if xml.tag == "testsuite" else list(xml.findall("testsuite"))
        counts = {key: sum(int(s.get(key, "0")) for s in suites)
                  for key in ("tests", "failures", "errors", "skipped")}
    after, dependency_after = protected(), dependency_receipt()
    unchanged = hashes == sources()
    success = (code == 0 and counts is not None and unchanged
               and before == after and dependency_before == dependency_after)
    matches = re.findall(r"(?<!subtests )(\d+) passed", stdout)
    subtests = re.findall(r"(\d+) subtests passed", stdout)
    receipt = {
        "schema": "cas-meta3-pure-validation/0.1",
        "status": "PURE_CHECKS_PASSED" if success else "PURE_CHECKS_FAILED",
        "failure": failure, "command": command, "returncode": code, "counts": counts,
        "test_scratch": str(scratch), "scratch_retained": True,
        "passed_test_functions": int(matches[-1]) if matches else None,
        "passed_subtests": int(subtests[-1]) if subtests else 0,
        "junit_count_includes_subtests": True, "source_sha256": hashes,
        "sources_unchanged": unchanged, "protected_before": before,
        "protected_after": after, "dependency_before": dependency_before,
        "dependency_after": dependency_after,
        "build_git_pin_verification": git_pin_check,
        "utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic() - started,
        "environment": {"python": sys.version, "executable": sys.executable,
                        "platform": sys.platform},
        "neural_imports_blocked": True, "local_neural_work": False,
        "native_execution_performed": False, "qualification": "UNQUALIFIED",
        "scope": "Pure storage/linking tests, including synthetic identities; no model or tensor execution.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(stdout)
    if stderr:
        print(stderr)
    print(json.dumps({key: receipt[key] for key in ("status", "returncode", "counts",
               "passed_test_functions", "passed_subtests", "sources_unchanged", "wall_seconds")}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
