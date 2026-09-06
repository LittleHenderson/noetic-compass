"""Retain one focused cold-child test run and its exact local evidence."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "checks_002"
TEST = ROOT / "tests/test_contrast_v7_cold_child.py"


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def snapshot():
    paths = [*sorted((ROOT / "cas_meta2/contrast_v7").glob("*.py")),
             ROOT / "cas_meta2/campaign_v3.py", ROOT / "cas_meta2/contrast_recovery_v6/source_manifest.json",
             TEST, HERE / "probe.py", HERE / "sitecustomize.py"]
    return {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    assert not OUTPUT.exists()
    OUTPUT.mkdir()
    before = snapshot()
    save(OUTPUT / "source_before.json", before)
    command = [sys.executable, "-B", "-m", "pytest", "-q", "-rA", "-s", str(TEST),
               "--junitxml", str(OUTPUT / "tests.xml"), "-p", "no:cacheprovider"]
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="", PYTEST_PLUGINS="",
               PYTHONDONTWRITEBYTECODE="1", CUDA_VISIBLE_DEVICES="",
               CAS_META1_RUN_GPU_TESTS="0", CAS_META2_RUN_GPU_TESTS="0")
    env.pop("PYTHONPATH", None)
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=360)
    (OUTPUT / "stdout.txt").write_bytes(result.stdout)
    (OUTPUT / "stderr.txt").write_bytes(result.stderr)
    after = snapshot()
    save(OUTPUT / "source_after.json", after)
    xml = ET.parse(OUTPUT / "tests.xml") if (OUTPUT / "tests.xml").exists() else None
    cases = xml.findall(".//testcase") if xml is not None else []
    counts = {"entries": len(cases), "failures": sum(c.find("failure") is not None for c in cases),
              "errors": sum(c.find("error") is not None for c in cases),
              "skipped": sum(c.find("skipped") is not None for c in cases)}
    found = re.search(r"PURE_COLD_CHILD_RETAINED_OUTPUT=(.+)", result.stdout.decode(errors="replace"))
    probe_path = Path(found.group(1).strip()).resolve() if found else None
    probe = None
    if probe_path:
        assert probe_path.is_relative_to(ROOT / "runs") and probe_path.is_dir()
        target = OUTPUT / "probe_records"
        target.mkdir()
        for path in probe_path.iterdir():
            if path.is_file():
                shutil.copyfile(path, target / path.name)
            elif path.name not in ("dataset", "frozen_wheel_files", "synthetic_training_fixture"):
                shutil.copytree(path, target / path.name)
        probe = json.loads((probe_path / "probe_receipt.json").read_bytes())
    receipt = {"completed": result.returncode == 0 and before == after and probe is not None
                              and probe["completed"] is True and not counts["failures"] and not counts["errors"],
        "command": command, "cwd": str(ROOT), "returncode": result.returncode,
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "executable": sys.executable, "existing_environment_not_fresh_install": True,
        "counts": counts, "source_before": before, "source_after": after, "source_unchanged": before == after,
        "probe_path": str(probe_path) if probe_path else None,
        "probe_receipt_sha256": sha256((probe_path / "probe_receipt.json").read_bytes()).hexdigest() if probe_path else None,
        "raw_stdout_sha256": sha256(result.stdout).hexdigest(), "raw_stderr_sha256": sha256(result.stderr).hexdigest(),
        "actual_aws": False, "neural_or_provider_execution": False,
        "earlier_attempts_retained": [
            {"path": str(ROOT / "runs/v7cold-d74699be4213"), "result": "test-helper typo before child launch; no production finding"},
            {"path": str(ROOT / "runs/v7cold-c99de044b6fe"), "result": "14 passed; find_spec callable with no package discovery; superseded only by stronger frozen-wheel fixture"}],
        "boundary": "Focused pure regression over saved diagnostic data and exact protected wheel file copies, using an explicitly mocked AWS request gate and a real local process-group adapter. Not live AWS, training, a fresh installation or native task execution."}
    save(OUTPUT / "receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("completed", "returncode", "counts",
                     "source_unchanged", "probe_path", "probe_receipt_sha256")}, indent=2), flush=True)
    return 0 if receipt["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
