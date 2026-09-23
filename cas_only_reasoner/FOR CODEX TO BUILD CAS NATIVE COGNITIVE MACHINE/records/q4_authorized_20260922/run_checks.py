"""Retain fresh deterministic Q4 tests; never overwrite an earlier receipt."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CN = ROOT.parents[1]
LAB = CN / "research/helm_cas_expression_lab"
FILES = ["test_learner_q4.py", "test_q4_followup.py", "test_q4_preparation.py",
         "test_q4_conversation_authorization.py", "test_q4_device_capacity.py",
         "test_q4_authorized_supervisor.py"]


def main():
    tag = sys.argv[1]
    if not tag.isidentifier():
        raise ValueError("Use a simple unique receipt name")
    target = ROOT / "tests" / tag
    target.mkdir(parents=True, exist_ok=False)
    temp = Path(os.environ["TEMP"]) / ("cas-q4-" + tag)
    if temp.exists():
        raise ValueError("Use a fresh temporary path")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTHONIOENCODING="utf-8")
    env.pop("PYTHONPATH", None)
    env.pop("HELM_Q4_AUTH_DEPENDENCY_DIR", None)
    command = [sys.executable, "-B", "-m", "pytest", *FILES, "-q", "--noconftest",
               "-o", "addopts=", "-p", "no:cacheprovider", "--basetemp", str(temp),
               "--junitxml", str(target / "cases.xml")]
    started = datetime.now(timezone.utc).isoformat()
    run = subprocess.run(command, cwd=LAB, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (target / "pytest.log").write_bytes(run.stdout)
    rows = []
    if (target / "cases.xml").exists():
        for case in ET.parse(target / "cases.xml").findall(".//testcase"):
            rows.append({"file": case.get("classname"), "name": case.get("name"),
                         "outcome": "ERROR" if case.find("error") is not None else
                         "FAIL" if case.find("failure") is not None else
                         "SKIP" if case.find("skipped") is not None else "PASS"})
    summary = {"started_utc": started, "ended_utc": datetime.now(timezone.utc).isoformat(),
               "command": command, "cwd": str(LAB), "exit_code": run.returncode,
               "case_count": len(rows), "function_count": len({(r["file"], r["name"].split("[")[0]) for r in rows}),
               "cases": rows, "source_hashes": {name: hashlib.sha256((LAB / name).read_bytes()).hexdigest() for name in FILES},
               "neural_execution": "NOT_PERFORMED_BY_TESTS"}
    (target / "receipt.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(run.stdout.decode("utf-8", errors="replace"))
    print(json.dumps({key: summary[key] for key in ("case_count", "function_count", "exit_code")}))
    raise SystemExit(run.returncode)


if __name__ == "__main__":
    main()
