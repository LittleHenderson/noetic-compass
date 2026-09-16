"""Post-fix launch tests only; reuse the previously reviewed import guard."""
from hashlib import sha256
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
BASE = OUTPUT.parent
TEST = "research/CAS_META_2_COMPOSITION/tests/test_ingestion_smoke_launch.py"
HELPER = ROOT / "records/learning_smoke_001/run_focused.py"


def save(name, value):
    with (OUTPUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":")); stream.write("\n")


def main():
    require = lambda value, reason: value or (_ for _ in ()).throw(RuntimeError(reason))
    require(not (OUTPUT / "receipt.json").exists(), "NO_TEST_RECORD_REUSE")
    namespace = runpy.run_path(str(HELPER))
    prior = json.loads((BASE / "focused_001/inputs_before.json").read_bytes())
    names = {row["path"] for row in prior} | {Path(__file__).relative_to(ROOT).as_posix()}
    before = [namespace["pin"](name) for name in sorted(names)]
    save("inputs_before.json", before)
    temporary = namespace["HOME"] / "_tmp/learning_smoke_package_fix_001"
    require(not temporary.exists(), "NO_TEMPORARY_REUSE")
    arguments = ["-q", TEST, "--basetemp=" + str(temporary), "--junitxml=" + str(OUTPUT / "tests.xml")]
    command = [sys.executable, "-B", "-c", namespace["CHILD"], *arguments]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="",
        PYTHONPATH=str(ROOT) + os.pathsep + str(ROOT / "research/CAS_META_2_COMPOSITION"),
        CAS_INGESTION_GUARD_RECEIPT=str(OUTPUT / "guard.json"), TEMP=str(temporary.parent), TMP=str(temporary.parent))
    save("launch.json", {"argv": command, "cwd": str(ROOT), "python": sys.version,
        "optimization": sys.flags.optimize, "temporary": str(temporary), "test_scope": [TEST],
        "parent_helper_sha256": sha256(HELPER.read_bytes()).hexdigest()})
    started = time.monotonic()
    with (OUTPUT / "stdout.txt").open("xb") as stdout, (OUTPUT / "stderr.txt").open("xb") as stderr:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=180)
    after = [namespace["pin"](name) for name in sorted(names)]
    save("inputs_after.json", after)
    suites = list(ET.parse(OUTPUT / "tests.xml").getroot().iter("testsuite"))
    counts = {key: sum(int(row.get(key, "0")) for row in suites) for key in ("tests", "failures", "errors", "skipped")}
    guard = json.loads((OUTPUT / "guard.json").read_bytes())
    passed = result.returncode == 0 and before == after and counts["tests"] > 0 and not any(
        counts[key] for key in ("failures", "errors", "skipped")) and not guard["forbidden_modules_loaded"] and not guard["forbidden_import_attempts"]
    save("receipt.json", {"status": "PASS" if passed else "FAIL", "counts": counts,
        "exit_code": result.returncode, "inputs_unchanged": before == after, "guard": guard,
        "elapsed_seconds": time.monotonic() - started,
        "boundary": "Targeted pure launcher tests with real local Git reads. No numerical, model, provider or network execution.",
        "artifacts": [{"path": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
            for path in sorted(OUTPUT.iterdir()) if path.is_file() for raw in [path.read_bytes()]]})
    print(json.dumps({"status": "PASS" if passed else "FAIL", "counts": counts, "inputs_unchanged": before == after}), flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
