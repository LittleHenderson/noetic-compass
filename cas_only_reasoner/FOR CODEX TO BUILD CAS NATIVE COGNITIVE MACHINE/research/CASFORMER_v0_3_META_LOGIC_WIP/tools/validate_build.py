"""Capture a local fixed-weight WIP rerun; never modifies the v0.2 source."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT.parent / "CAS_CJT_TRANSFORMER_v0_2"


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def hashes(paths):
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def source_files():
    paths = [path for folder in ("cas_meta", "tests", "schemas", "programs", "tools")
             for path in (ROOT / folder).rglob("*")
             if path.is_file() and "__pycache__" not in path.parts
             and path.suffix in (".py", ".json")]
    paths.extend(ROOT / name for name in ("README.md", "requirements-meta.txt",
                                          "META_LOGIC_WIP_BOUNDARY.md", ".gitignore"))
    return paths


def git_head():
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def installed_identity():
    identities = {}
    for package, wheel in (("cas_cjt", "cas_neural_cjt-0.2.0-py3-none-any.whl"),
                           ("casformer", "casformer_reference-0.1.0-py3-none-any.whl")):
        module = importlib.import_module(package)
        installed = Path(module.__file__).resolve().parent
        archive = V2 / "artifacts" / "release_reproduction" / "dist" / wheel
        compared = {}
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.infolist():
                if member.is_dir() or not member.filename.startswith(package + "/"):
                    continue
                relative = member.filename.removeprefix(package + "/")
                wheel_bytes = zipped.read(member)
                if (installed / relative).read_bytes() != wheel_bytes:
                    raise AssertionError("Installed package differs from frozen wheel: " + member.filename)
                compared[relative] = sha256(wheel_bytes).hexdigest()
        if not compared:
            raise AssertionError("No package files checked in wheel")
        identities[package] = {"installed_path": str(installed), "wheel": str(archive),
                               "wheel_sha256": sha256(archive.read_bytes()).hexdigest(),
                               "matched_files": compared}
    return identities


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    initial_head = git_head()
    initial_sources = hashes(source_files())
    dump(output / "installed_wheel_identity.json", installed_identity())
    # Short owned paths under this WIP homebase avoid Windows path-length
    # failures. pytest may clear only these dedicated scratch directories.
    scratch = Path(tempfile.mkdtemp(prefix="_verify_", dir=ROOT))
    packages = {distribution.metadata["Name"]: distribution.version
                for distribution in importlib.metadata.distributions()}
    dump(output / "environment.json", {
        "utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
        "executable": sys.executable, "platform": platform.platform(),
        "cwd": str(ROOT), "packages": packages,
    })
    commands = [
        ("v02_existing_evidence", [sys.executable, "-I", str(V2 / "artifacts" /
            "release_reproduction" / "probes" / "verify_evidence_bundle.py")]),
        ("meta_tests", [sys.executable, "-m", "pytest", "tests", "-q", "--tb=short",
                        "--basetemp", str(scratch / "meta"),
                        "--junitxml", str(output / "meta_tests.xml")]),
        ("v02_manifest", [sys.executable, "-m", "pytest", str(V2 / "tests" / "test_source_manifest.py"),
                          "-q", "--tb=short", "--basetemp", str(scratch / "manifest"),
                          "--junitxml", str(output / "v02_manifest.xml")]),
        ("demo", [sys.executable, "-m", "cas_meta.demo", "--output", str(output / "demo")]),
        ("installed_imports", [sys.executable, "-I", "-c",
            "import cas_cjt,casformer,json; print(json.dumps({'cas_cjt':cas_cjt.__file__,'casformer':casformer.__file__}))"]),
    ]
    records = []
    for name, command in commands:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        (output / (name + ".stdout.txt")).write_text(completed.stdout, encoding="utf-8")
        (output / (name + ".stderr.txt")).write_text(completed.stderr, encoding="utf-8")
        records.append({"name": name, "argv": command, "returncode": completed.returncode})
        dump(output / "commands.json", records)
        print(f"{name}: exit {completed.returncode}", flush=True)
        if completed.returncode:
            raise SystemExit(f"Validation stopped; see {output / (name + '.stdout.txt')}")
    counts = {}
    for name in ("meta_tests", "v02_manifest"):
        suites = ET.parse(output / (name + ".xml")).getroot()
        counts[name] = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
                        for key in ("tests", "failures", "errors", "skipped")}
        if counts[name]["tests"] < 1 or any(counts[name][key] for key in ("failures", "errors", "skipped")):
            raise AssertionError("Incomplete test run: " + name)
    source_hashes = hashes(source_files())
    if source_hashes != initial_sources or git_head() != initial_head:
        raise AssertionError("Source or Git HEAD changed during validation")
    dump(output / "source_sha256.json", source_hashes)
    native_manifest = json.loads((V2 / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    receipt = {
        "status": "CAS_META_0_FIXED_WEIGHT_COMPOSITION_TEST_PASSED",
        "classification": "WIP_UNREVIEWED_NOT_PART_OF_V0_2",
        "git_head_at_run": initial_head,
        "source_and_head_unchanged_during_run": True,
        "tested_source_hashes": "source_sha256.json",
        "counts": counts,
        "v02_controlled_files": native_manifest["file_count"],
        "v02_aggregate_sha256": native_manifest["aggregate_sha256"],
        "v02_source_freeze_sha": "dec08c81644f1c47b4b94c29a406a9432df7c7bd",
        "v02_evidence_sha": "b5d52d1fc9d5dce231ccb0f91ece2be0168dfa78",
        "new_training_performed": False,
        "full_v02_v01_cncm_regressions_rerun": False,
        "scope": "This run covers the new composition layer and unchanged v0.2 manifest. The prior full release reproduction remains separate evidence.",
        "demo": json.loads((output / "demo" / "result.json").read_text(encoding="utf-8")),
    }
    dump(output / "receipt.json", receipt)
    files = [path for path in output.rglob("*") if path.is_file()]
    dump(output / "payload_sha256.json", {
        path.relative_to(output).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in sorted(files)
    })
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    run(arguments.output.resolve())
