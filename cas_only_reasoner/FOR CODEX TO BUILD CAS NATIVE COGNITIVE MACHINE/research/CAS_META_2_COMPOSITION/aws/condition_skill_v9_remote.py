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
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from zipfile import ZipFile

from aws.condition_skill_v9_package import (MAX_ARCHIVE_BYTES, MAX_MEMBER_BYTES,
                                            MAX_MEMBER_COUNT, MAX_EXPANDED_BYTES, digest, require,
                                            inspect_archive, verify_extracted)

SCHEMA = "cas-meta2-condition-skill-v9-remote/9"
JOB_PATTERN = r"cas-meta2-\d{14}-[a-f0-9]{8}"
WORKER_SECONDS_MAX = 600
TRAINER_OUTPUT_BYTES_MAX = 32 * 1024**2
LOG_BYTES_MAX = 1024**2
OUTPUT_FILES_MAX = 32
FAMILIES = ("cas", "generic_attention")
STAGES = ("untrained", "trained")
SPLITS = ("train_probe", "validation", "test_instances", "test_direction_pair")
PILOT_DIR = "research/CAS_META_2_COMPOSITION"
DATASET_DIR = "records/condition_skill_v9_001/dataset_001"


def safe_path(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or
        getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents)),
        "REMOTE_PATH_LINK_OR_TRAVERSAL")
    return path


def regular_info(path, limit):
    info = safe_path(path).stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            "REMOTE_REGULAR_SINGLE_LINK_FILE_REQUIRED")
    require(0 <= info.st_size <= limit, "REMOTE_FILE_BOUND")
    return info


def read_bounded(path, limit):
    """Check size before allocating; recheck the opened file and its identity."""
    path = safe_path(path)
    before = regular_info(path, limit)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        require((opened.st_dev, opened.st_ino, opened.st_size, opened.st_nlink) ==
                (before.st_dev, before.st_ino, before.st_size, 1), "REMOTE_FILE_CHANGED")
        raw = stream.read(limit + 1)
        require(len(raw) == before.st_size and os.fstat(stream.fileno()).st_size == before.st_size,
                "REMOTE_FILE_CHANGED")
    return raw


def write_new(path, raw):
    with safe_path(path).open("xb") as stream:
        stream.write(raw)


def write_json(path, value):
    write_new(path, (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))


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
            and "\\" not in name and ":" not in name and not any(ord(char) < 32 for char in name)
            and all(part not in ("", ".", "..") and not part.endswith((" ", "."))
                    for part in name.split("/")),
            "REMOTE_UNSAFE_MEMBER_NAME")
    require(name.casefold() not in seen, "REMOTE_DUPLICATE_MEMBER_NAME")
    seen.add(name.casefold())
    return name


def extract_archive(archive_path, destination):
    """Bounded extraction with path and link safety; no symlink members.

    Every member name and size is validated before the destination directory
    is created, so a rejected archive leaves nothing behind.
    """
    archive_path = safe_path(archive_path)
    destination = safe_path(destination)
    require(not destination.exists() and destination.parent.is_dir(),
            "REMOTE_FRESH_DESTINATION_REQUIRED")
    raw = read_bounded(archive_path, MAX_ARCHIVE_BYTES)
    require(bool(raw), "REMOTE_ARCHIVE_EMPTY")
    plan, seen, total = [], set(), 0
    with ZipFile(io.BytesIO(raw)) as zipped:
        infos = zipped.infolist()
        require(0 < len(infos) <= MAX_MEMBER_COUNT, "REMOTE_MEMBER_COUNT_BOUND")
        for info in infos:
            name = safe_member_name(info.filename, seen)
            require(not info.is_dir(), "REMOTE_DIRECTORY_MEMBER")
            mode = stat.S_IFMT(info.external_attr >> 16)
            require(mode != stat.S_IFLNK, "REMOTE_SYMLINK_MEMBER")
            require(mode in (0, stat.S_IFREG) and not info.flag_bits & 1,
                    "REMOTE_REGULAR_UNENCRYPTED_MEMBER_REQUIRED")
            require(0 <= info.file_size <= MAX_MEMBER_BYTES, "REMOTE_MEMBER_SIZE:" + name)
            total += info.file_size
            require(total <= MAX_EXPANDED_BYTES, "REMOTE_EXPANDED_BOUND")
            plan.append((info, name))
        require(not any("/".join(name.split("/")[:index]).casefold() in seen
                for _, name in plan for index in range(1, len(name.split("/")))),
                "REMOTE_FILE_DIRECTORY_COLLISION")
        destination.mkdir()
        for info, name in plan:
            with zipped.open(info) as stream:
                payload = stream.read(info.file_size + 1)
            require(len(payload) == info.file_size, "REMOTE_MEMBER_CHANGED:" + name)
            target = safe_path(destination / name)
            require(target.is_relative_to(destination), "REMOTE_MEMBER_ESCAPE")
            target.parent.mkdir(parents=True, exist_ok=True)
            write_new(target, payload)
    return {"members": len(seen), "bytes": total, "destination": str(destination)}


def verify_extracted_package(archive_path, destination, *, expected_sha256,
                             expected_source_sha, expected_manifest_sha256):
    """Archive hash + manifest closure + on-disk rehash of every member."""
    manifest = inspect_archive(archive_path,
                               expected_sha256=expected_sha256,
                               expected_source_sha=expected_source_sha,
                               expected_manifest_sha256=expected_manifest_sha256)
    return verify_extracted(destination, manifest, imported_paths=())


def scoped_layout(package_dir, output_dir, dataset_dir, job):
    require(type(job) is str and re.fullmatch(JOB_PATTERN, job) is not None,
            "REMOTE_JOB_LABEL_REQUIRED")
    package = safe_path(package_dir)
    pilot = safe_path(package / PILOT_DIR)
    output, dataset = safe_path(output_dir), safe_path(dataset_dir)
    require(output == pilot / "runs" / job, "REMOTE_OUTPUT_MUST_BE_PILOT_RUN_JOB")
    require(dataset == pilot / DATASET_DIR, "REMOTE_FROZEN_DATASET_PATH_REQUIRED")
    require(not output.exists(), "REMOTE_FRESH_OUTPUT_REQUIRED")
    require(not safe_path(output.with_name(output.name + ".evidence")).exists(),
            "REMOTE_FRESH_EVIDENCE_REQUIRED")
    return package, pilot, output, dataset


def venv_python(package_dir, python_executable):
    """Require the isolated task venv. Outer receipts attest its installation.

    A normal Unix venv Python may itself link to the base interpreter. Its
    directory ancestors and pyvenv.cfg must be link-free. A path is not proof
    that this executable or the installed wheels passed the outer GPU probe.
    """
    path = Path(python_executable)
    require(path.is_absolute() and ".." not in path.parts
            and path.parent.name in ("bin", "Scripts")
            and re.fullmatch(r"python(?:\d+(?:\.\d+)?)?(?:\.exe)?", path.name) is not None,
            "REMOTE_EXPLICIT_VENV_PYTHON_REQUIRED")
    expected = safe_path(package_dir).parent / "venv"
    require(safe_path(path.parent).parent == expected, "REMOTE_TASK_VENV_REQUIRED")
    require(path.is_file(), "REMOTE_VENV_PYTHON_MISSING")
    if not path.is_symlink():
        regular_info(path, 128 * 1024**2)
    config = read_bounded(expected / "pyvenv.cfg", 16384).decode("utf-8")
    options = dict(line.split("=", 1) for line in config.splitlines() if "=" in line)
    options = {key.strip().lower(): value.strip().lower() for key, value in options.items()}
    require(options.get("include-system-site-packages") == "false", "REMOTE_ISOLATED_VENV_REQUIRED")
    return str(path)


def trainer_command(package_dir, output_dir, dataset_dir, job, *, python_executable):
    package, pilot, output, dataset = scoped_layout(package_dir, output_dir, dataset_dir, job)
    require(pilot.is_dir(), "REMOTE_PILOT_MISSING")
    require(dataset.is_dir(), "REMOTE_FROZEN_DATASET_MISSING")
    python = venv_python(package, python_executable)
    command = [python, "-s", "-B", "-m", "cas_meta2.condition_skill_v9.train",
               "--output", str(output), "--dataset", str(dataset)]
    # Only the byte-verified pilot is on PYTHONPATH. casformer/cas_cjt must
    # resolve to the installed wheels, not sibling sources or user-site paths.
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith("PYTHON")}
    environment.update({"CAS_META2_RUN_CONDITION_SKILL_V9": "1",
        "CAS_META2_AWS_JOB_ID": job, "CUDA_VISIBLE_DEVICES": "0",
        "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(pilot)})
    return command, environment, str(pilot)


def _kill_tree(process):
    """Independent termination; works on both worker and harness hosts."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=30)
    else:
        import signal
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()


def validate_timeout(timeout):
    require(type(timeout) in (int, float) and math.isfinite(timeout)
            and 0 < timeout <= WORKER_SECONDS_MAX, "REMOTE_TIMEOUT_BOUND")
    # The trainer is import-pure; validate only its fixed scalar configuration.
    from cas_meta2.condition_skill_v9.train import validate_config
    config = validate_config()
    require(config["max_seconds"] <= WORKER_SECONDS_MAX and
            config["max_output_bytes"] <= TRAINER_OUTPUT_BYTES_MAX, "REMOTE_TRAINER_CONFIG_BOUND")
    return config


def run_trainer(package_dir, output_dir, dataset_dir, job, *, python_executable, popen=subprocess.Popen,
                kill_tree=_kill_tree, timeout=WORKER_SECONDS_MAX):
    config = validate_timeout(timeout)
    command, environment, cwd = trainer_command(package_dir, output_dir, dataset_dir, job,
                                                python_executable=python_executable)
    output = safe_path(output_dir)
    require(output.parent.is_dir(), "REMOTE_RUNS_DIRECTORY_MISSING")
    stdout_path = output.with_name(output.name + ".trainer.stdout.log")
    stderr_path = output.with_name(output.name + ".trainer.stderr.log")
    require(not stdout_path.exists() and not stderr_path.exists(), "REMOTE_FRESH_LOGS_REQUIRED")
    started, code, timed_out, launched, failure = time.monotonic(), None, False, False, None
    with safe_path(stdout_path).open("xb") as stdout, safe_path(stderr_path).open("xb") as stderr:
        try:
            kwargs = ({"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
                      if os.name == "nt" else {"start_new_session": True})
            process = popen(command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr, **kwargs)
            launched = True
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_tree(process)
                code = process.wait(timeout=30)
        except Exception as error:
            failure = {"type": type(error).__name__, "message": str(error)[:2000]}
    return {"exit_code": code, "timed_out": timed_out, "process_started": launched,
            "process_reaped": launched and code is not None,
            "process_attempts": 1, "automatic_retries": 0, "failure": failure,
            "elapsed_seconds": time.monotonic() - started, "timeout_seconds": timeout,
            "trainer_config": config, "command": command, "cwd": cwd,
            "stdout_log": str(stdout_path), "stderr_log": str(stderr_path)}


def collect_trainer_output(output_dir, evidence_dir, *, allowed=allowed_trainer_output):
    """Missing/partial results are evidence, not a reason to drop failure logs."""
    output_dir, evidence_dir = safe_path(output_dir), safe_path(evidence_dir)
    require(evidence_dir == output_dir.with_name(output_dir.name + ".evidence"),
            "REMOTE_EVIDENCE_PATH_REQUIRED")
    require(not evidence_dir.exists() and evidence_dir.parent.is_dir(),
            "REMOTE_FRESH_EVIDENCE_REQUIRED")
    plan, total, errors = [], 0, []
    if not output_dir.exists():
        errors.append("REMOTE_TRAINER_OUTPUT_MISSING")
    else:
        require(output_dir.is_dir(), "REMOTE_OUTPUT_ENTRY")
        for path in output_dir.iterdir():
            require(len(plan) < OUTPUT_FILES_MAX, "REMOTE_OUTPUT_FILE_COUNT_BOUND")
            require(allowed(path.name), "REMOTE_UNALLOWED_TRAINER_OUTPUT:" + path.name)
            info = regular_info(path, TRAINER_OUTPUT_BYTES_MAX)
            total += info.st_size
            require(total <= TRAINER_OUTPUT_BYTES_MAX, "REMOTE_TRAINER_OUTPUT_BOUND")
            plan.append((path, info.st_size))
    if not any(path.name == "result.json" for path, _ in plan):
        errors.append("REMOTE_RESULT_JSON_MISSING")
    evidence_dir.mkdir()
    files = {}
    for path, size in sorted(plan):
        raw = read_bounded(path, size)
        write_new(evidence_dir / path.name, raw)
        files[path.name] = {"bytes": len(raw), "sha256": digest(raw)}
    collected = {"schema": SCHEMA, "files": files, "total_bytes": total,
                 "result_present": "result.json" in files, "errors": errors}
    write_json(evidence_dir / "collected.json", collected)
    return collected


def collect_logs(outcome, evidence_dir):
    """Retain a bounded prefix of each raw log; disclose any truncation."""
    records = {}
    for stream in ("stdout", "stderr"):
        name = "trainer." + stream + ".log"
        source = safe_path(outcome[stream + "_log"])
        info = regular_info(source, 2**63 - 1)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(source, flags), "rb") as handle:
            opened = os.fstat(handle.fileno())
            require((opened.st_dev, opened.st_ino, opened.st_size, opened.st_nlink) ==
                    (info.st_dev, info.st_ino, info.st_size, 1), "REMOTE_LOG_CHANGED")
            raw = handle.read(LOG_BYTES_MAX)
        require(len(raw) == min(info.st_size, LOG_BYTES_MAX), "REMOTE_LOG_CHANGED")
        write_new(Path(evidence_dir) / name, raw)
        records[name] = {"bytes": len(raw), "source_bytes": info.st_size,
                        "sha256": digest(raw), "truncated": info.st_size > len(raw)}
    return records


def orchestrate(archive_path, destination, output_dir, dataset_dir, job, *,
                expected_sha256, expected_source_sha, expected_manifest_sha256,
                python_executable, popen=subprocess.Popen, kill_tree=_kill_tree,
                timeout=WORKER_SECONDS_MAX):
    validate_timeout(timeout)
    _, pilot, output_dir, _ = scoped_layout(destination, output_dir, dataset_dir, job)
    venv_python(destination, python_executable)
    inspect_archive(archive_path, expected_sha256=expected_sha256,
        expected_source_sha=expected_source_sha, expected_manifest_sha256=expected_manifest_sha256)
    extraction = extract_archive(archive_path, destination)
    source = verify_extracted_package(archive_path, destination, expected_sha256=expected_sha256,
                             expected_source_sha=expected_source_sha,
                             expected_manifest_sha256=expected_manifest_sha256)
    safe_path(pilot / "runs").mkdir(exist_ok=True)
    outcome = run_trainer(destination, output_dir, dataset_dir, job,
                          python_executable=python_executable,
                          popen=popen, kill_tree=kill_tree, timeout=timeout)
    evidence_dir = output_dir.parent / (output_dir.name + ".evidence")
    try:
        collected = collect_trainer_output(output_dir, evidence_dir)
    except Exception as error:
        safe_path(evidence_dir).mkdir(exist_ok=True)
        collected = {"schema": SCHEMA, "files": {}, "total_bytes": 0,
                     "result_present": False, "errors": ["REMOTE_COLLECTION_FAILED"],
                     "failure": {"type": type(error).__name__, "message": str(error)[:2000]}}
        # Any partial copied files remain available, but are not a full result.
        if not (evidence_dir / "collected.json").exists():
            write_json(evidence_dir / "collected.json", collected)
    try:
        logs, log_failure = collect_logs(outcome, evidence_dir), None
    except Exception as error:
        logs = {}
        log_failure = {"type": type(error).__name__, "message": str(error)[:2000]}
    finished = (outcome["exit_code"] == 0 and not outcome["timed_out"]
                and outcome["failure"] is None and not collected["errors"] and log_failure is None)
    status = "REMOTE_FINISHED" if finished else "REMOTE_FAILED"
    receipt = {"schema": SCHEMA, "status": status, "job": job,
               "extraction": extraction, "source": source,
               "outcome": outcome, "collected": collected, "logs": logs, "log_failure": log_failure,
               "claims": {"provider_identity_proved": False,
                          "learning_improvement_claimed": False,
                          "identity_evidence_required": "independent outer launch receipt"}}
    write_json(evidence_dir / "remote_receipt.json", receipt)
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
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--timeout", type=float, default=WORKER_SECONDS_MAX)
    arguments = parser.parse_args()
    receipt = orchestrate(arguments.archive, arguments.destination, arguments.output,
                          arguments.dataset, arguments.job,
                          expected_sha256=arguments.expected_sha256,
                          expected_source_sha=arguments.expected_source_sha,
                          expected_manifest_sha256=arguments.expected_manifest_sha256,
                          python_executable=arguments.python_executable, timeout=arguments.timeout)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "REMOTE_FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
