"""Create NEW symbolic diagnostic receipts against three explicit sources.

Old Git source is replayed today; this never recreates a missing historical run.
Run with Python that has pytest installed. No application conftest/plugins,
training/model imports, cloud calls or old record modifications are performed.
"""
from pathlib import Path
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / ".git").exists())
MODULE = "noetic-compass-scaffold/noetic-compass/api/cas_ohm"
BASE = "eb9985566bd11a89f485d627186ef0efa7177f02"
PEER = "a4b2e0d7c6726968903b99c714b7b5a6b15d401f"
PYTEST = [sys.executable, "-B", "-m", "pytest", "--noconftest", "-c", os.devnull,
          "-o", "addopts=", "-p", "no:cacheprovider", "-q"]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def functions(data):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(data))
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")}


def main():
    originals = git("show", f"{BASE}:{MODULE}/test_quantifiers.py")
    carried = (ROOT / MODULE / "test_quantifiers.py").read_bytes()
    new = (ROOT / MODULE / "test_numeric_boundaries.py").read_bytes()
    assert carried == git("show", f"{PEER}:{MODULE}/test_quantifiers.py")
    old_functions = functions(originals)
    carry_functions = functions(carried)
    assert all(carry_functions.get(k) == v for k, v in old_functions.items())
    tests = {"test_quantifiers.py": carried, "test_numeric_boundaries.py": new}
    new_functions = functions(new)
    assert not set(carry_functions).intersection(new_functions)
    tracked = git("ls-tree", "-r", "--name-only", BASE).decode().splitlines()
    selected = [f"{MODULE}/{name}" for name in tests]
    all_tests = sorted(set(p for p in tracked if Path(p).name.startswith("test_") and p.endswith(".py")) | set(selected))
    report = {
        "schema": "cas.ohm.numeric-repair-receipts/0.1", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "meaning": "NEW diagnostic unit-test runs, not recovered historical receipts; no measurement or model execution",
        "base_commit": BASE, "peer_hardening_commit": PEER, "python": sys.version,
        "test_accounting": {
            "original_at_base_functions_and_cases": len(old_functions),
            "carried_peer_functions_and_cases": len(carry_functions) - len(old_functions),
            "existing_at_peer_functions_and_cases": len(carry_functions),
            "new_functions": len(new_functions), "selected_files": selected,
            "unloaded_files_in_diagnostic_package": [],
            "repository_test_file_census_definition": "tracked test_*.py at base plus this newly added selected module; not source coverage",
            "repository_unloaded_test_files": [p for p in all_tests if p not in selected],
        },
        "test_sources": [{"path": f"{MODULE}/{name}", "bytes": len(data), "sha256": sha(data)} for name, data in tests.items()],
        "runs": [],
    }
    source_versions = [
        ("before_eb998556", git("show", f"{BASE}:{MODULE}/quantifiers.py"), BASE),
        ("peer_a4b2e0d7", git("show", f"{PEER}:{MODULE}/quantifiers.py"), PEER),
        ("repaired", (ROOT / MODULE / "quantifiers.py").read_bytes(), "WORKING_TREE_BOUND_BY_SHA256"),
    ]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONIOENCODING="utf-8")
    # Worktree is nested inside the approved CNCM write boundary.
    scratch = ROOT.parent.parent / "_test_runs"
    scratch.mkdir(exist_ok=True)
    for label, source, ref in source_versions:
        with tempfile.TemporaryDirectory(prefix=f"ohm_{label}_", dir=scratch) as temporary:
            stage = Path(temporary)
            (stage / "quantifiers.py").write_bytes(source)
            for name, data in tests.items():
                (stage / name).write_bytes(data)
            env["CAS_OHM_TEST_SOURCE"] = str(stage / "quantifiers.py")
            xml = HERE / f"{label}.xml"
            command = PYTEST + list(tests) + [f"--junitxml={xml}"]
            started = datetime.now(timezone.utc).isoformat()
            run = subprocess.run(command, cwd=stage, env=env, capture_output=True)
            log = HERE / f"{label}.txt"
            log.write_bytes(run.stdout + run.stderr)
            cases = []
            for case in ET.parse(xml).getroot().iter("testcase"):
                status = next((kind for kind in ("failure", "error", "skipped") if case.find(kind) is not None), "passed")
                name = case.attrib["name"]
                function = name.split("[", 1)[0]
                # Some pytest environments emit an empty JUnit classname.
                # Resolve against the disjoint source-function inventories.
                assert function in new_functions or function in carry_functions
                is_new = function in new_functions
                test_file = "test_numeric_boundaries.py" if is_new else "test_quantifiers.py"
                cases.append({"id": f"{test_file}::{name}", "status": status,
                              "group": "new" if is_new else "existing_at_peer"})
            counts = {kind: sum(c["status"] == kind for c in cases) for kind in ("passed", "failure", "error", "skipped")}
            report["runs"].append({"label": label, "source_ref": ref, "source_path": f"{MODULE}/quantifiers.py",
                "source_sha256": sha(source), "source_bytes": len(source), "started_utc": started,
                "finished_utc": datetime.now(timezone.utc).isoformat(), "command": command, "cwd": str(stage),
                "exit_code": run.returncode, "cases": len(cases), "counts": counts, "case_results": cases,
                "receipts": [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                              "sha256": sha(p.read_bytes())} for p in (xml, log)]})
            print(label, run.returncode, counts)
    final = report["runs"][-1]
    report["test_accounting"]["new_cases"] = sum(c["group"] == "new" for c in final["case_results"])
    report["test_accounting"]["total_selected_cases"] = final["cases"]
    report["test_accounting"]["total_test_functions"] = len(carry_functions) + len(new_functions)
    report["test_accounting"]["integration_case_delta"] = final["cases"] - len(old_functions)
    report["test_accounting"]["integration_function_delta"] = len(carry_functions) + len(new_functions) - len(old_functions)
    for before in report["runs"][:-1]:
        final_by_id = {case["id"]: case["status"] for case in final["case_results"]}
        before["failed_case_reconciliation"] = [{"id": case["id"], "before_status": case["status"],
            "final_status": final_by_id.get(case["id"], "NOT_RERUN")} for case in before["case_results"]
            if case["status"] in ("failure", "error")]
    (HERE / "RECEIPTS.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    if final["exit_code"]:
        raise SystemExit(final["exit_code"])


if __name__ == "__main__":
    main()
