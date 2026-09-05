"""Pure source/data verification; reject even an attempted torch import."""
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
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class NoNeuralImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"torch", "tensorflow", "jax", "casformer"}:
            raise RuntimeError("LOCAL_NEURAL_IMPORT_FORBIDDEN:" + fullname)
        return None


def source_files():
    return sorted(p for base in ("cas_meta2", "aws", "tools", "tests")
                  for p in (ROOT / base).rglob("*.py"))


def protected():
    pilot = ROOT.parent / "CAS_META_1_LEARNED_SELECTION"
    manifest = json.loads((pilot / "BASELINE_MANIFEST.json").read_bytes())
    for item in manifest["files"]:
        path = (ROOT.parent / item["path"]).resolve()
        if not path.is_relative_to(ROOT.parent) or sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("PROTECTED_BASELINE_CHANGED:" + item["path"])
    return {"baseline_sha": manifest["baseline_sha"], "files_verified": len(manifest["files"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if args.child:
        sys.path.insert(0, str(ROOT))
        sys.meta_path.insert(0, NoNeuralImports())
        import pytest
        return pytest.main(["tests", "-q", "-m", "not gpu", "-p", "no:cacheprovider",
                            "--junitxml=" + str(args.output / "tests.xml")])
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "records") or output.exists():
        raise ValueError("NEW_VALIDATION_RECORD_DIRECTORY_REQUIRED")
    output.mkdir(parents=True)
    started = time.monotonic()
    before = protected()
    paths = source_files()
    for path in paths:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hashes = {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths}
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", "--output", str(output)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", CAS_META2_RUN_GPU_TESTS="0",
               CAS_META1_RUN_GPU_TESTS="0", CUDA_VISIBLE_DEVICES="")
    run = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=180)
    (output / "stdout.txt").write_text(run.stdout, encoding="utf-8")
    (output / "stderr.txt").write_text(run.stderr, encoding="utf-8")
    counts = None
    if (output / "tests.xml").is_file():
        xml = ET.parse(output / "tests.xml").getroot()
        suites = [xml] if xml.tag == "testsuite" else list(xml.findall("testsuite"))
        counts = {k: sum(int(s.get(k, "0")) for s in suites)
                  for k in ("tests", "failures", "errors", "skipped")}
    after = protected()
    unchanged = hashes == {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest()
                           for p in source_files()}
    success = run.returncode == 0 and unchanged and before == after
    passed = re.findall(r"(?<!subtests )(\d+) passed", run.stdout)
    subtests = re.findall(r"(\d+) subtests passed", run.stdout)
    receipt = {"schema": "cas-meta2-pure-validation/1",
               "status": "PURE_CHECKS_PASSED" if success else "PURE_CHECKS_FAILED",
               "command": command, "returncode": run.returncode, "counts": counts,
               "passed_test_functions": int(passed[-1]) if passed else None,
               "passed_subtests": int(subtests[-1]) if subtests else 0,
               "junit_count_includes_subtests": True,
               "protected_before": before, "protected_after": after,
               "source_sha256": hashes, "sources_unchanged": unchanged,
               "neural_imports_blocked": True, "local_neural_work": False,
               "gpu_tests_run": False, "scope": "Syntax, pure data/control and mock-backend tests only.",
               "utc": datetime.now(timezone.utc).isoformat(),
               "wall_seconds": time.monotonic() - started}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(run.stdout)
    print(run.stderr)
    print(json.dumps(receipt, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
