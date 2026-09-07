"""Reproduce a v9 package from committed bytes, then check its own verifier.

This performs only source/JSON/ZIP work. It does not install wheels, import a
neural library, open SQLite, contact a provider, reserve money, or train.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = frozenset(("sqlite3", "_sqlite3", "torch", "numpy", "casformer", "cas_cjt",
                       "cas_meta", "boto3", "botocore", "tensorflow", "jax"))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("REPRODUCTION_FORBIDDEN_IMPORT:" + fullname)


def admit_pure_operations():
    require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_IMPORT_ALREADY_PRESENT")
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("REPRODUCTION_FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)


def destination(path):
    result = Path(path).absolute()
    owned = ROOT / "records/condition_skill_v9_001"
    require(result.is_relative_to(owned) and result != owned and ".." not in result.parts,
            "REPRODUCTION_OWNED_OUTPUT_REQUIRED")
    require(not result.exists() and result.parent.is_dir(), "REPRODUCTION_FRESH_OUTPUT_REQUIRED")
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (result, *result.parents)), "REPRODUCTION_LINK_REFUSED")
    return result


def child(package, archive, archive_sha, source_sha, manifest_sha):
    admit_pure_operations()
    package = Path(package).resolve()
    pilot = package / "research/CAS_META_2_COMPOSITION"
    sys.path.insert(0, str(pilot))
    from aws import condition_skill_v9_package as pkg
    require(Path(pkg.__file__).resolve() == pilot / "aws/condition_skill_v9_package.py",
            "VERIFIER_NOT_IMPORTED_FROM_EXTRACTED_PACKAGE")
    manifest = pkg.inspect_archive(archive, expected_sha256=archive_sha,
        expected_source_sha=source_sha, expected_manifest_sha256=manifest_sha)
    checked = pkg.verify_extracted(package, manifest)
    from cas_meta2.condition_skill_v9 import bundle
    from aws.condition_skill_v9_resource_plan import DATASET_MANIFEST_SHA256
    require(Path(bundle.__file__).resolve() == pilot / "cas_meta2/condition_skill_v9/bundle.py",
            "BUNDLE_NOT_IMPORTED_FROM_EXTRACTED_PACKAGE")
    # Packaging-stage byte checks are outside the learner. No targets are parsed.
    dataset, dataset_sha = bundle.inspect(pilot / "records/condition_skill_v9_001/dataset_001",
                                          expected_manifest_sha256=DATASET_MANIFEST_SHA256)
    require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_IMPORT_AFTER_CHECK")
    report = {"status": "EXTRACTED_PACKAGE_SELF_VERIFIED", "source_sha": source_sha,
        "package": checked, "dataset_manifest_sha256": dataset_sha,
        "dataset_counts": dataset["counts"],
        "verifier_path": str(Path(pkg.__file__).resolve()),
        "verifier_sha256": sha256(Path(pkg.__file__).read_bytes()).hexdigest(),
        "neural_execution": False, "sqlite_execution": False, "provider_calls": 0}
    print(json.dumps(report, sort_keys=True))
    return 0


def run(source_sha, output):
    admit_pure_operations()
    sys.path.insert(0, str(ROOT))
    from aws import condition_skill_v9_package as pkg
    from aws import condition_skill_v9_remote as remote
    output = destination(output)
    # The packager, extractor and this capture must be the committed versions.
    current_files = ("aws/condition_skill_v9_package.py", "aws/condition_skill_v9_remote.py",
                     "tools/check_condition_skill_v9_package_reproduction.py")
    source_files = {}
    for name in current_files:
        raw = (ROOT / name).read_bytes()
        require(pkg.git_bytes(ROOT, source_sha, pkg.PILOT + name) == raw,
                "COMMITTED_REPRODUCTION_SOURCE_MISMATCH:" + name)
        source_files[name] = sha256(raw).hexdigest()
    ledger = ROOT / "records/budget/campaign_ledger.json"
    ledger_before = sha256(ledger.read_bytes()).hexdigest()
    started = datetime.now(timezone.utc).isoformat()
    output.mkdir()
    receipt = {"schema": "cas-meta2-condition-skill-package-reproduction/9",
        "status": "FAILED", "source_sha": source_sha, "source_files": source_files,
        "started_utc": started, "python": sys.version,
        "command": [sys.executable, "-B", str(Path(__file__).resolve()),
                    "--source", source_sha, "--output", str(output)],
        "ledger_before": ledger_before, "neural_execution": False,
        "sqlite_execution": False, "provider_calls": 0, "new_reservation": False}
    try:
        built = pkg.build_package(output / "source", source_sha=source_sha)
        receipt["package"] = {key: built[key] for key in
            ("archive", "archive_sha256", "archive_bytes", "source_sha", "manifest_sha256", "member_count")}
        extracted = output / "package"
        receipt["extraction"] = remote.extract_archive(built["archive"], extracted)
        command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child",
                   str(extracted), built["archive"], built["archive_sha256"],
                   source_sha, built["manifest_sha256"]]
        receipt["child_command"] = command
        with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(command, cwd=extracted, stdout=stdout, stderr=stderr,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                code = process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait(timeout=15)
                receipt["timed_out"] = True
        receipt["exit_code"] = code
        require(code == 0 and not receipt.get("timed_out"), "EXTRACTED_VERIFIER_FAILED")
        receipt["child"] = json.loads((output / "stdout.txt").read_bytes())
        require(receipt["child"]["status"] == "EXTRACTED_PACKAGE_SELF_VERIFIED",
                "EXTRACTED_VERIFIER_STATUS")
        receipt["status"] = "SOURCE_PACKAGE_REPRODUCED_NO_NEURAL_EXECUTION"
    except Exception as error:
        receipt["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        receipt["ledger_after"] = sha256(ledger.read_bytes()).hexdigest()
        receipt["source_unchanged"] = all(sha256((ROOT / name).read_bytes()).hexdigest() == expected
                                           for name, expected in source_files.items())
        receipt["unchanged"] = receipt["source_unchanged"] and receipt["ledger_after"] == ledger_before
        if not receipt["unchanged"]:
            receipt["status"] = "FAILED_SOURCE_OR_LEDGER_CHANGED"
        receipt["outputs"] = {name: {"bytes": (output / name).stat().st_size,
            "sha256": sha256((output / name).read_bytes()).hexdigest()}
            for name in ("stdout.txt", "stderr.txt") if (output / name).is_file()}
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (output / "receipt.json").write_bytes((json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "SOURCE_PACKAGE_REPRODUCED_NO_NEURAL_EXECUTION" else 1


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        return child(*sys.argv[2:])
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    return run(args.source, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
