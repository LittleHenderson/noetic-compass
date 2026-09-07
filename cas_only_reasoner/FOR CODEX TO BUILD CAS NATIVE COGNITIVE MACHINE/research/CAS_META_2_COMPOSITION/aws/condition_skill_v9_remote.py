"""Remote worker for the condition-skill v9 launch. One run, no restart.

This module runs on the admitted CUDA worker. It extracts the byte-bound
source package into a fresh directory, hash-verifies every extracted file
against the root manifest, runs the trainer exactly once with the explicit
enable flag and job label under an independent wall-clock kill, and collects
only allowlisted trainer outputs with a hard byte bound. A timeout, crash, or
CUDA refusal is a recorded failed launch, never authority to retry.

Pure-testable: extraction, collection, and orchestration take injected
process/package functions; no tensor, provider, or database work occurs at
import time.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
from zipfile import ZipFile

from aws.condition_skill_v9_package import (MAX_ARCHIVE_BYTES, MAX_MEMBER_BYTES,
                                            MAX_EXPANDED_BYTES, digest, require,
                                            inspect_archive, verify_extracted)

SCHEMA = "cas-meta2-condition-skill-v9-remote/9"
JOB_PATTERN = r"cas-meta2-\d{14}-[a-f0-9]{8}"
WORKER_SECONDS_MAX = 600
TRAINER_OUTPUT_BYTES_MAX = 32 * 1024**2
FAMILIES = ("cas", "generic_attention")
STAGES = ("untrained", "trained")
SPLITS = ("train_probe", "validation", "test_instances", "test_direction_pair")
PILOT_DIR = "research/CAS_META_2_COMPOSITION"


def allowed_trainer_output(name):
    """Exact allowlist of trainer output names; everything else is refused."""
    if name in ("result.json", "config.json", "selection.json",
                "test_predictions_blind.json", "training_history.json"):
        return True
    if name.endswith((".initial.pt", ".selected.pt")) and name.rsplit(".", 2)[0] in FAMILIES:
        return True
    if name.endswith(".predictions.json") or name.endswith(".controls.json"):
        key = name.rsplit(".", 2)[0]
        return key in {family + "." + stage for family in FAMILIES for stage in STAGES}
    if name.endswith(".baselines.json"):
        return name.rsplit(".baselines.json", 1)[0] in SPLITS
    return False


def safe_member_name(name, seen):
    require(type(name) is str and name and not name.startswith("/")
            and "\\" not in name and name == name.replace("//", "/")
            and all(part not in ("", ".", "..") for part in name.split("/")),
            "REMOTE_UNSAFE_MEMBER_NAME")
    require(name not in seen, "REMOTE_DUPLICATE_MEMBER_NAME")
    seen.add(name)
    return name


def extract_archive(archive_path, destination):
    """Bounded extraction with path and link safety; no symlink members.

    Every member name and size is validated before the destination directory
    is created, so a rejected archive leaves nothing behind.
    """
    archive_path = Path(archive_path).absolute()
    destination = Path(destination).absolute()
    require(archive_path.is_file() and archive_path.stat().st_size <= MAX_ARCHIVE_BYTES,
            "REMOTE_ARCHIVE_BOUND")
    require(not destination.exists() and destination.parent.is_dir(),
            "REMOTE_FRESH_DESTINATION_REQUIRED")
    raw = archive_path.read_bytes()
    require(digest(raw), "REMOTE_ARCHIVE_EMPTY")
    plan, seen, total = [], set(), 0
    with ZipFile(archive_path) as zipped:
        for info in zipped.infolist():
            name = safe_member_name(info.filename, seen)
            require(not info.is_dir(), "REMOTE_DIRECTORY_MEMBER")
            require((info.external_attr >> 16) & 0o170000 != 0o120000, "REMOTE_SYMLINK_MEMBER")
            require(0 <= info.file_size <= MAX_MEMBER_BYTES, "REMOTE_MEMBER_SIZE:" + name)
            total += info.file_size
            require(total <= MAX_EXPANDED_BYTES, "REMOTE_EXPANDED_BOUND")
            plan.append((info, name))
    destination.mkdir()
    with ZipFile(archive_path) as zipped:
        for info, name in plan:
            payload = zipped.read(info)
            require(len(payload) == info.file_size, "REMOTE_MEMBER_CHANGED:" + name)
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(payload)
    return {"members": len(seen), "bytes": total, "destination": str(destination)}


def verify_extracted_package(archive_path, destination, *, expected_sha256,
                             expected_source_sha, expected_manifest_sha256):
    """Archive hash + manifest closure + on-disk rehash of every member."""
    manifest = inspect_archive(archive_path,
                               expected_sha256=expected_sha256,
                               expected_source_sha=expected_source_sha,
                               expected_manifest_sha256=expected_manifest_sha256)
    return verify_extracted(destination, manifest, imported_paths=())


def trainer_command(package_dir, output_dir, dataset_dir):
    pilot = Path(package_dir).absolute() / PILOT_DIR
    require(pilot.is_dir(), "REMOTE_PILOT_MISSING")
    command = [sys.executable, "-B", "-m", "cas_meta2.condition_skill_v9.train",
               "--output", str(Path(output_dir).absolute()),
               "--dataset", str(Path(dataset_dir).absolute())]
    environment = dict(os.environ)
    environment["CAS_META2_RUN_CONDITION_SKILL_V9"] = "1"
    environment["CAS_META2_AWS_JOB_ID"] = os.environ.get("CAS_META2_AWS_JOB_ID", "")
    environment["CUDA_VISIBLE_DEVICES"] = "0"
    source_paths = [str(Path(package_dir).absolute() / "research" / "CASFORMER_v0_1"),
                    str(Path(package_dir).absolute() / "research" / "CAS_CJT_TRANSFORMER_v0_2"),
                    str(Path(package_dir).absolute() / "research" / "CAS_META_1_LEARNED_SELECTION")]
    environment["PYTHONPATH"] = os.pathsep.join(
        [environment.get("PYTHONPATH", "")] + source_paths).strip(os.pathsep)
    return command, environment, str(pilot)


def _kill_tree(process):
    """Independent termination; works on both worker and harness hosts."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        import signal
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()


def run_trainer(package_dir, output_dir, dataset_dir, job, *, popen=subprocess.Popen,
                kill_tree=_kill_tree, timeout=WORKER_SECONDS_MAX):
    require(re.fullmatch(JOB_PATTERN, job) is not None, "REMOTE_JOB_LABEL_REQUIRED")
    command, environment, cwd = trainer_command(package_dir, output_dir, dataset_dir)
    environment["CAS_META2_AWS_JOB_ID"] = job
    stdout_path = Path(output_dir).absolute().parent / "trainer.stdout.log"
    stderr_path = Path(output_dir).absolute().parent / "trainer.stderr.log"
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        if os.name == "nt":
            process = popen(command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr,
                            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        else:
            process = popen(command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr,
                            start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_tree(process)
            code = process.wait(timeout=30)
            timed_out = True
        else:
            timed_out = False
    return {"exit_code": code, "timed_out": timed_out, "elapsed_seconds": time.monotonic() - started,
            "command": command, "cwd": cwd,
            "stdout_log": str(stdout_path), "stderr_log": str(stderr_path)}


def collect_trainer_output(output_dir, evidence_dir, *, allowed=allowed_trainer_output):
    output_dir = Path(output_dir).absolute()
    evidence_dir = Path(evidence_dir).absolute()
    require(output_dir.is_dir(), "REMOTE_TRAINER_OUTPUT_MISSING")
    require(not evidence_dir.exists() and evidence_dir.parent.is_dir(),
            "REMOTE_FRESH_EVIDENCE_REQUIRED")
    evidence_dir.mkdir()
    files, total = {}, 0
    for path in sorted(output_dir.iterdir()):
        require(path.is_file() and not path.is_symlink(), "REMOTE_OUTPUT_ENTRY")
        require(allowed(path.name), "REMOTE_UNALLOWED_TRAINER_OUTPUT:" + path.name)
        raw = path.read_bytes()
        total += len(raw)
        require(total <= TRAINER_OUTPUT_BYTES_MAX, "REMOTE_TRAINER_OUTPUT_BOUND")
        target = evidence_dir / path.name
        shutil.copyfile(path, target)
        files[path.name] = {"bytes": len(raw), "sha256": digest(raw)}
    require("result.json" in files, "REMOTE_RESULT_JSON_MISSING")
    collected = {"schema": SCHEMA, "files": files, "total_bytes": total}
    with (evidence_dir / "collected.json").open("xb") as stream:
        stream.write((json.dumps(collected, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return collected


def orchestrate(archive_path, destination, output_dir, dataset_dir, job, *,
                expected_sha256, expected_source_sha, expected_manifest_sha256,
                popen=subprocess.Popen, kill_tree=_kill_tree):
    extraction = extract_archive(archive_path, destination)
    verify_extracted_package(archive_path, destination, expected_sha256=expected_sha256,
                             expected_source_sha=expected_source_sha,
                             expected_manifest_sha256=expected_manifest_sha256)
    output_dir = Path(output_dir).absolute()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    outcome = run_trainer(destination, output_dir, dataset_dir, job,
                          popen=popen, kill_tree=kill_tree)
    evidence_dir = output_dir.parent / (output_dir.name + ".evidence")
    collected = collect_trainer_output(output_dir, evidence_dir)
    status = ("REMOTE_FINISHED" if outcome["exit_code"] == 0 and not outcome["timed_out"]
              else "REMOTE_FAILED")
    receipt = {"schema": SCHEMA, "status": status, "job": job,
               "extraction": extraction, "outcome": outcome, "collected": collected,
               "claims": {"provider_identity_proved": False,
                          "identity_evidence_required": "independent outer launch receipt"}}
    with (evidence_dir / "remote_receipt.json").open("xb") as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    arguments = parser.parse_args()
    receipt = orchestrate(arguments.archive, arguments.destination, arguments.output,
                          arguments.dataset, arguments.job,
                          expected_sha256=arguments.expected_sha256,
                          expected_source_sha=arguments.expected_source_sha,
                          expected_manifest_sha256=arguments.expected_manifest_sha256)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "REMOTE_FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
