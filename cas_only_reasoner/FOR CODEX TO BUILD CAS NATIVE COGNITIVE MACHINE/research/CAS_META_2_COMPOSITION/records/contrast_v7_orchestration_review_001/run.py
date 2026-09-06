"""Retain the focused synthetic orchestration suite and byte identities."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "checks_001"


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def snapshot():
    names = ["cas_meta2/contrast_v7/" + name + ".py" for name in
             ("campaign", "gpu_preflight", "native_evaluation", "train", "checks", "data", "parent")]
    names += ["cas_meta2/campaign_v3.py", "tests/test_contrast_v7_orchestration.py"]
    selected = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
    manifest_path = ROOT.parent / "CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    assert len(manifest["files"]) == 316
    protected = {}
    for item in manifest["files"]:
        path = (ROOT.parent / item["path"]).resolve()
        assert path.is_relative_to(ROOT.parent.resolve())
        pin = sha256(path.read_bytes()).hexdigest()
        assert pin == item["sha256"], item["path"]
        protected[item["path"]] = pin
    return {"selected_source_sha256": selected, "protected_sha256": protected}


def main():
    assert not OUTPUT.exists()
    OUTPUT.mkdir()
    before = snapshot()
    save(OUTPUT / "source_before.json", before)
    command = [sys.executable, "-B", "-m", "pytest", "-q", "-rA", "-s",
               str(ROOT / "tests/test_contrast_v7_orchestration.py"), "-p", "no:cacheprovider",
               "--junitxml", str(OUTPUT / "tests.xml")]
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="", PYTEST_PLUGINS="",
               PYTHONDONTWRITEBYTECODE="1", CUDA_VISIBLE_DEVICES="",
               CAS_META1_RUN_GPU_TESTS="0", CAS_META2_RUN_GPU_TESTS="0")
    env.pop("PYTHONPATH", None)
    started = datetime.now(timezone.utc).isoformat()
    run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=120)
    (OUTPUT / "stdout.txt").write_bytes(run.stdout)
    (OUTPUT / "stderr.txt").write_bytes(run.stderr)
    after = snapshot()
    save(OUTPUT / "source_after.json", after)
    xml = ET.parse(OUTPUT / "tests.xml") if (OUTPUT / "tests.xml").exists() else None
    cases = xml.findall(".//testcase") if xml is not None else []
    counts = {"entries": len(cases), "failures": sum(x.find("failure") is not None for x in cases),
              "errors": sum(x.find("error") is not None for x in cases),
              "skipped": sum(x.find("skipped") is not None for x in cases)}
    receipt = {"completed": run.returncode == 0 and before == after and len(cases) == 22
                            and not counts["failures"] and not counts["errors"] and not counts["skipped"],
        "command": command, "cwd": str(ROOT), "returncode": run.returncode,
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "executable": sys.executable, "counts": counts,
        "source_unchanged": before == after, "selected_source_files": len(before["selected_source_sha256"]),
        "protected_files": 316, "selected_source_sha256": before["selected_source_sha256"],
        "stdout_sha256": sha256(run.stdout).hexdigest(), "stderr_sha256": sha256(run.stderr).hexdigest(),
        "existing_environment_not_fresh_install": True,
        "phase_processes_simulated": True, "gpu_receipts_synthetic": True,
        "tasks_generated": False, "neural_execution": False, "provider_calls": False,
        "execution_readiness_flags_changed_on_disk": False,
        "boundary": "Synthetic orchestration and saved receipt validation only. Process launch and training/native outcome functions are mocked; no live GPU, provider, dataset construction or model execution. Initial mismatch finding remains preserved separately."}
    save(OUTPUT / "receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("completed", "returncode", "counts",
          "source_unchanged", "selected_source_files", "protected_files")}, indent=2))
    return 0 if receipt["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
