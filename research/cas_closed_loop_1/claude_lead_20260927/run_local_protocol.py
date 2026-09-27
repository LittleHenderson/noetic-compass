"""Wave A1: run the frozen public CPU acceptance protocol locally, off-cloud.

Mirrors the command sequence of aws_validation/worker.py after its offline
package installation: instance Git preflight, artifact check, runtime
bootstrap, source check, the four predeclared test files, retained replay,
a fresh witness and a fresh-process replay. No AWS call, no model call, no
edit to any Codex-owned file. The result is a LOCAL public engineering check
of the amended source; it is not CAS_AWS_ENGINEERING_VALIDATED and it does
not replace the Codex-owned Lane A job.
"""
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
ROOT = LANE.parents[1]
RUNTIME_COMMIT = "8182ad52b4468f18f140837dffee0e7debcfe786"
RETAINED_BUNDLE_DIGEST = "eae7eb1bedb67af537187d409c89fca9e55a1580d52bf14be9b01e560a198d2c"


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-tests", type=int, required=True,
                        help="predeclared case count for the four frozen files; never hardcoded")
    args = parser.parse_args()
    EXPECTED_TESTS = args.expected_tests
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = HERE / ("run_" + stamp)
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    env = os.environ.copy()
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "GIT_TERMINAL_PROMPT": "0"})
    record = {"schema": "cas.closed-loop.claude-local-protocol/0.1", "wave": "A1",
              "expected_tests_argument": EXPECTED_TESTS,
              "start_utc": utc(), "status": "RUNNING", "paid_job": False,
              "model_invocations": 0, "aws_calls": 0, "codex_files_edited": 0,
              "commands": [], "claim_boundary": (
                  "LOCAL public CPU engineering check of the amended source only. "
                  "Not CAS_AWS_ENGINEERING_VALIDATED. Does not replace the Codex-owned "
                  "Lane A AWS job, its instance Git preflight, or its pinned Python 3.12 "
                  "wheelhouse. No learned-model, comparative-advantage or production claim.")}

    def save():
        (out / "record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    def command(name, argv, *, allow_failure=False, limit=900):
        row = {"name": name, "argv": argv, "start_utc": utc()}
        record["commands"].append(row)
        save()
        stdout_path, stderr_path = out / (name + ".stdout"), out / (name + ".stderr")
        with stdout_path.open("wb") as so, stderr_path.open("wb") as se:
            t0 = time.monotonic()
            proc = subprocess.run(argv, cwd=ROOT, stdout=so, stderr=se, env=env, timeout=limit)
            row["seconds"] = round(time.monotonic() - t0, 3)
        row["returncode"] = proc.returncode
        row["end_utc"] = utc()
        row["stdout_sha256"] = sha(stdout_path)
        save()
        if proc.returncode != 0 and not allow_failure:
            raise RuntimeError("COMMAND_FAILED:" + name)
        return stdout_path.read_text(encoding="utf-8", errors="replace")

    try:
        head = command("git_head", ["git", "rev-parse", "HEAD"]).strip()
        record["source_commit"] = head
        record["git_branch"] = command("git_branch", ["git", "branch", "--show-current"]).strip()
        record["git_status_porcelain"] = command("git_status", ["git", "status", "--porcelain"]).splitlines()
        record["environment"] = {"python": sys.version, "executable": sys.executable,
                                 "platform": platform.platform(),
                                 "git": command("git_version", ["git", "--version"]).strip()}
        pins = {}
        for mod in ("pytest", "pydantic", "pydantic_core"):
            pins[mod] = command("pin_" + mod, [sys.executable, "-c",
                                f"import {mod}; print({mod}.__version__)"]).strip()
        record["environment"]["pins_observed"] = pins
        record["environment"]["pins_declared_by_aws_package"] = {
            "python": "3.12 (AWS worker requirement; not satisfied locally)",
            "pytest": "9.0.2", "pydantic": "2.12.5", "pydantic_core": "2.41.5"}
        command("runtime_commit_exists", ["git", "cat-file", "-e", RUNTIME_COMMIT])
        record["runtime_commit"] = RUNTIME_COMMIT
        # Informational: the recovery branch records these as MISSING_FROM_LIVE_REPOSITORY.
        historical = {}
        for obj in ("348638c9d9b6069eebab7853db6b98bfef453092", "2636bbb6e0f41a37ba2c20df08cdf51185718617"):
            command("historical_object_" + obj[:8], ["git", "cat-file", "-e", obj], allow_failure=True)
            historical[obj] = "PRESENT_ON_ORIGIN" if record["commands"][-1]["returncode"] == 0 else "ABSENT"
        record["historical_objects_in_this_clone"] = historical
        command("committed_artifact_check", [sys.executable, str(LANE / "check_artifacts.py"), "--git-ref", head])
        command("runtime_bootstrap", [sys.executable, str(LANE / "bootstrap_runtime.py")])
        record["runtime_bootstrap"] = json.loads((out / "runtime_bootstrap.stdout").read_text())
        command("source_check", [sys.executable, str(LANE / "run_closed_loop.py"), "check"])
        record["source_check"] = json.loads((out / "source_check.stdout").read_text())
        command("artifact_check", [sys.executable, str(LANE / "check_artifacts.py")])
        record["artifact_check"] = json.loads((out / "artifact_check.stdout").read_text())
        command("focused_tests", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                "--junitxml=" + str(out / "pytest.xml"),
                str(LANE / "test_native_step_adapter.py"), str(LANE / "test_closed_loop.py"),
                str(LANE / "test_artifacts.py"), str(LANE / "aws_validation/test_launch_transport.py")],
                allow_failure=True)
        root = ET.parse(out / "pytest.xml").getroot()
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
                  for key in ("tests", "failures", "errors", "skipped")}
        by_file = {}
        for case in root.iter("testcase"):
            key = Path(case.attrib.get("file") or case.attrib.get("classname", "")).name
            by_file[key] = by_file.get(key, 0) + 1
        record["tests"] = {**totals, "expected_tests": EXPECTED_TESTS, "by_file": by_file,
                           "seconds": record["commands"][-1]["seconds"]}
        if totals != {"tests": EXPECTED_TESTS, "failures": 0, "errors": 0, "skipped": 0}:
            raise ValueError("PREDECLARED_TEST_COUNTS_REQUIRED_WITHOUT_SKIPS")
        command("retained_replay", [sys.executable, str(LANE / "run_closed_loop.py"), "replay",
                "--directory", str(LANE / "evidence"), "--expected-bundle-digest", RETAINED_BUNDLE_DIGEST])
        record["retained_replay"] = json.loads((out / "retained_replay.stdout").read_text())
        witness = out / "witness"
        command("witness", [sys.executable, str(LANE / "run_closed_loop.py"), "demo", "--output", str(witness)])
        result = json.loads((out / "witness.stdout").read_text())
        retained = result["bundle_digest"]
        (out / "caller_retained_digest.txt").write_text(retained + "\n")
        command("fresh_process_replay", [sys.executable, str(LANE / "run_closed_loop.py"), "replay",
                "--directory", str(witness), "--expected-bundle-digest", retained])
        replay = json.loads((out / "fresh_process_replay.stdout").read_text())
        expectations = {"output": ("3", result["output"]), "host_entries": (12, result["host_entries"]),
                        "native_events": (18, result["native_events"]),
                        "replay_status": ("EXACT_NATIVE_REPLAY_AND_CHECKED_EFFECT", replay["status"])}
        record["witness_expectations"] = {k: {"expected": e, "observed": o, "match": e == o}
                                          for k, (e, o) in expectations.items()}
        if not all(v["match"] for v in record["witness_expectations"].values()):
            raise ValueError("ENGINEERING_WITNESS_EXPECTATIONS_DIFFER")
        record["witness"] = result
        record["fresh_process_replay"] = replay
        record["witness_files"] = {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)}
                                   for p in sorted(witness.iterdir())}
        record["status"] = "PASS_LOCAL_PUBLIC_ENGINEERING_CHECK_ONLY"
    except BaseException as exc:  # record, never hide
        record["status"] = "FAILED"
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)
        import traceback
        (out / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        record["end_utc"] = utc()
        record["seconds"] = round(time.monotonic() - started, 3)
        save()
        print(json.dumps({"status": record["status"], "run_dir": str(out.relative_to(ROOT)),
                          "tests": record.get("tests"), "error": record.get("error")}))
    return 0 if record["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
