"""Standalone guest driver for one teaching allocation and two fresh readers.

No imports from the repository, tensor libraries or AWS SDKs. The optional real
adapters use subprocesses; importing this file performs no external operation.
Guest observations and hashes are not independent provider or learning proof.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from zipfile import ZipFile, ZIP_DEFLATED

SCHEMA = "cas-teaching-guest-config/1"
PERMIT_SCHEMA = "cas-teaching-guest-permit/1"
ACCOUNT, REGION, INSTANCE_TYPE = "807562639912", "us-west-2", "g7.2xlarge"
JOB_PATTERN = r"cas-meta2-teaching-\d{14}-[0-9a-f]{8}"
ARTIFACT_MAX = 2684354560
ARCHIVE_MAX, EXPANDED_MAX, PUBLIC_MAX = 33554432, 67108864, 1048576
LOG_MAX, FILES_MAX = 1048576, 20000
FINALIZE_RESERVE_SECONDS = 180
BOOTSTRAP_MAX = 16 * 1024**2
BOOTSTRAP_FILES = ("bootstrap.log", "torch_install.json", "wheel_install.json",
                   "dependency_install.json", "environment.txt")
ARMS = ("cas.aligned", "cas.ordinary", "generic.aligned", "generic.ordinary")
SPLITS = ("test_fresh", "test_context", "test_names")
WORKER_FILES = ("cas_meta2/__init__.py", "cas_meta2/codec.py", "cas_meta2/features_v2.py", "cas_meta2/policy.py") + tuple(
    "cas_meta2/teaching_cycle/" + name + ".py" for name in
    ("__init__", "lesson_contract", "guided_application", "controller", "gpu_adapter", "journal", "runner", "worker_contract", "worker"))
WHEEL = "wheels/casformer_reference-0.1.0-py3-none-any.whl"
WHEEL_SHA = "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee"
MEMBERS = frozenset((*WORKER_FILES, WHEEL, "train.json", "development.json", "manifest.json"))
BINDINGS = frozenset(("source_commit", "source_sha256", "archive_sha256", "manifest_sha256",
    "training_cases_sha256", "development_cases_sha256", "material_receipt_sha256", "public_sets_sha256",
    "scorer_sha256", "parent_driver_sha256", "guest_driver_sha256", "bootstrap_sha256",
    "provider_source_sha256", "provider_dependencies_sha256", "proposal_sha256", "authority_sha256", "pricing_receipt_sha256"))


class GuestError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise GuestError("TEACHING_GUEST:" + reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: require(False, "NONFINITE_JSON"))
    canonical(value)
    return value


def pin(value, length=64):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{" + str(length) + "}", value) is not None and value != "0" * length


def safe(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "LINK_OR_TRAVERSAL")
    return path


def info(path, maximum=ARTIFACT_MAX):
    value = safe(path).stat()
    require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1 and 0 <= value.st_size <= maximum, "FILE_BOUND")
    return value


def file_hash(path, maximum=ARTIFACT_MAX):
    before, digest = info(path, maximum), sha256()
    with safe(path).open("rb") as stream:
        while chunk := stream.read(1024**2):
            digest.update(chunk)
    after = info(path, maximum)
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "FILE_CHANGED")
    return {"sha256": digest.hexdigest(), "bytes": before.st_size}


def read(path, maximum=PUBLIC_MAX):
    size = info(path, maximum).st_size
    raw = safe(path).read_bytes()
    require(len(raw) == size, "FILE_CHANGED")
    return raw


def write(path, value, *, raw=False):
    path = safe(path)
    payload = value if raw else canonical(value) + b"\n"
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), **file_hash(path)}


def validate_config(config, config_sha256, permit, *, driver_path=None):
    require(type(config) is dict and set(config) == {"schema", "job", "run_id", "request_sha256",
        "resource_plan_sha256", "bindings", "resource_plan", "bucket", "prefix", "launch_started_unix", "deadline_unix"}, "CONFIG_FIELDS")
    require(config["schema"] == SCHEMA and re.fullmatch(JOB_PATTERN, config["job"] or "") is not None
            and config["run_id"] == config["job"], "JOB_SCOPE")
    require(pin(config_sha256) and pin(config["request_sha256"]) and pin(config["resource_plan_sha256"]), "CONFIG_PINS")
    require(config["bucket"] == config["job"] + "-" + ACCOUNT and config["prefix"] == "", "BUCKET_SCOPE")
    bindings, plan = config["bindings"], config["resource_plan"]
    require(type(bindings) is dict and set(bindings) == BINDINGS and all(pin(value, 40 if name == "source_commit" else 64)
            for name, value in bindings.items()), "BINDING_PINS")
    require(sha256(canonical(plan)).hexdigest() == config["resource_plan_sha256"], "RESOURCE_PLAN_PIN")
    fixed = {"account_id": ACCOUNT, "region": REGION, "instance_type": INSTANCE_TYPE, "instance_count": 1,
        "runtime_seconds_max": 7200, "training_worker_seconds_max": 4800, "prediction_process_count_max": 2,
        "prediction_seconds_per_process_max": 300, "artifact_expanded_bytes_max": ARTIFACT_MAX,
        "artifact_download_bytes_max": ARTIFACT_MAX, "artifact_upload_bytes_max": ARTIFACT_MAX,
        "public_release_bytes_max": PUBLIC_MAX, "automatic_retries": 0,
        "shared_lifetime_not_reset_between_processes": True, "final_public_inputs_released_only_after_checkpoint_seal": True}
    require(type(plan) is dict and all(type(plan.get(key)) is type(value) and plan[key] == value for key, value in fixed.items()), "RESOURCE_SCOPE")
    require(plan["worksheet_limits"]["guest_s3_api_attempts_max"] == 896, "GUEST_REQUEST_ALLOCATION")
    start, end = config["launch_started_unix"], config["deadline_unix"]
    require(all(type(value) in (int, float) and math.isfinite(value) for value in (start, end))
            and 0 < end - start <= 7200, "LIFETIME_BOUND")
    require(type(permit) is dict and set(permit) == {"schema", "job", "run_id", "config_sha256", "request_sha256",
        "instance_id", "deadline_unix", "shutdown_schedule_arn", "shutdown_schedule_confirmed", "automatic_retries"}, "PERMIT_FIELDS")
    require(all(permit.get(key) == value for key, value in {"schema": PERMIT_SCHEMA, "job": config["job"],
        "run_id": config["run_id"], "config_sha256": config_sha256, "request_sha256": config["request_sha256"],
        "deadline_unix": end}.items()), "PERMIT_IDENTITY")
    require(permit["shutdown_schedule_confirmed"] is True and type(permit["automatic_retries"]) is int
            and permit["automatic_retries"] == 0, "SCHEDULE_GATE")
    require(re.fullmatch(r"i-(?:[0-9a-f]{8}|[0-9a-f]{17})", permit["instance_id"] or "") is not None, "INSTANCE_ID")
    require(type(permit["shutdown_schedule_arn"]) is str and permit["shutdown_schedule_arn"].startswith(
        f"arn:aws:scheduler:{REGION}:{ACCOUNT}:schedule/"), "SCHEDULE_ARN")
    require(file_hash(driver_path or __file__, ARCHIVE_MAX)["sha256"] == bindings["guest_driver_sha256"], "GUEST_SOURCE_PIN")
    return config


class Clock:
    monotonic = staticmethod(time.monotonic)
    sleep = staticmethod(time.sleep)
    time = staticmethod(time.time)


class Budget:
    def __init__(self, config, clock):
        self.clock, self.end = clock, config["deadline_unix"]
        require(config["launch_started_unix"] <= clock.time() < self.end, "LIFETIME_EXPIRED")
        self.monotonic_end = clock.monotonic() + min(7200, self.end - clock.time())
        self.operations, self.read_operations, self.write_operations = 0, 0, 0
        self.uploaded, self.downloaded, self.peak_expanded = 0, 0, 0

    def remaining(self):
        return min(self.end - self.clock.time(), self.monotonic_end - self.clock.monotonic())

    def check(self):
        require(self.remaining() > 0, "LIFETIME_EXPIRED")

    def operation(self, write_operation=False):
        self.check()
        # head+get for reads, put for writes; failures and empty polls consume allocation.
        count = 1 if write_operation else 2
        require(self.operations + count <= 896, "S3_REQUEST_BOUND")
        self.operations += count
        if write_operation:
            self.write_operations += count
        else:
            self.read_operations += count

    def transfer(self, size, upload=False):
        require(type(size) is int and size >= 0, "TRANSFER_SIZE")
        name = "uploaded" if upload else "downloaded"
        require(getattr(self, name) + size <= ARTIFACT_MAX, "TRANSFER_BYTE_BOUND")
        setattr(self, name, getattr(self, name) + size)

    def scan(self, root, *, active=False):
        total, count = 0, 0
        try:
            for path in safe(root).rglob("*"):
                try:
                    safe(path)
                    if path.is_file():
                        count += 1
                        total += info(path).st_size
                        require(count <= FILES_MAX and total <= ARTIFACT_MAX, "EXPANDED_ARTIFACT_BOUND")
                        if path.parent.name == "driver" and path.suffix == ".log":
                            require(path.stat().st_size <= LOG_MAX, "PROCESS_LOG_BOUND")
                except FileNotFoundError:
                    # A live journal atomically renames staging to committed.
                    # A vanished entry is revisited next poll, never trusted.
                    if not active:
                        raise
        except FileNotFoundError:
            if not active:
                raise
        self.peak_expanded = max(total, self.peak_expanded)
        return total

    def report(self):
        return {"s3_api_attempts_upper_bound": self.operations, "s3_read_attempts_upper_bound": self.read_operations,
            "s3_write_attempts_upper_bound": self.write_operations, "uploaded_bytes": self.uploaded,
            "downloaded_bytes": self.downloaded, "peak_expanded_bytes": self.peak_expanded,
            "guest_attempt_allocation": 896, "bootstrap_attempt_allocation_separate": 128,
            "shared_deadline_unix": self.end, "remaining_seconds": max(0, self.remaining())}


def extract_training(archive, destination, bindings):
    require(file_hash(archive, ARCHIVE_MAX)["sha256"] == bindings["archive_sha256"], "ARCHIVE_PIN")
    destination = safe(destination)
    require(not destination.exists() and destination.parent.is_dir(), "FRESH_BUNDLE_REQUIRED")
    with ZipFile(archive) as zipped:
        members = zipped.infolist()
        require(len(members) == len(MEMBERS) and {member.filename for member in members} == MEMBERS, "BUNDLE_INVENTORY")
        require(sum(member.file_size for member in members) <= EXPANDED_MAX, "BUNDLE_EXPANDED_BOUND")
        for member in members:
            require(not member.is_dir() and not member.flag_bits & 1 and member.file_size <= 8 * 1024**2
                    and stat.S_IFMT(member.external_attr >> 16) in (0, stat.S_IFREG), "BUNDLE_MEMBER_TYPE")
        raw = zipped.read("manifest.json")
        require(sha256(raw).hexdigest() == bindings["manifest_sha256"], "MANIFEST_PIN")
        manifest = parse(raw)
        require(manifest.get("schema") == "cas-meta2-teaching-cycle-training-bundle/1" and
            all(manifest.get(key) == bindings[key] for key in ("source_commit", "source_sha256", "training_cases_sha256", "development_cases_sha256")), "BUNDLE_IDENTITIES")
        require(type(manifest.get("files")) is dict and set(manifest["files"]) == MEMBERS - {"manifest.json"}, "MANIFEST_INVENTORY")
        source = {}
        for member in members:
            if member.filename == "manifest.json":
                continue
            raw = zipped.read(member)
            declared = manifest["files"][member.filename]
            require(declared == {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}, "MEMBER_PIN")
            if member.filename in WORKER_FILES:
                source[member.filename] = declared["sha256"]
            if member.filename == WHEEL:
                require(declared["sha256"] == WHEEL_SHA, "FROZEN_WHEEL_PIN")
        require(sha256(canonical(source)).hexdigest() == bindings["source_sha256"], "WORKER_SOURCE_MAP")
        destination.mkdir()
        for member in members:
            target = destination / member.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            write(target, zipped.read(member), raw=True)
    return manifest


def valid_reference(reference):
    return (type(reference) is dict and set(reference) == {"path", "sha256", "state_sha256", "transaction", "receipt_sha256"} and
        type(reference["path"]) is str and type(reference["transaction"]) is int and reference["transaction"] > 0 and
        all(pin(reference[key]) for key in ("sha256", "state_sha256", "receipt_sha256")))


def validate_campaign(document, config):
    require(type(document) is dict and document.get("schema") == "cas-teaching-four-arm-campaign/1"
            and document.get("run_id") == config["run_id"] and document.get("source_sha256") == config["bindings"]["source_sha256"]
            and document.get("manifest_sha256") == config["bindings"]["manifest_sha256"]
            and document.get("held_out_opened") is False and document.get("accepted_weights_updated") is False
            and type(document.get("arms")) is dict and set(document["arms"]) == set(ARMS), "CAMPAIGN_IDENTITY")
    if document.get("all_allocations_finished") is not True:
        return False
    for arm, report in document["arms"].items():
        require(report.get("allocation_finished") is True and report.get("curriculum") == arm.split(".")[1]
                and valid_reference(report.get("initial_checkpoint")) and valid_reference(report.get("selected_checkpoint")), "CAMPAIGN_SELECTION")
    return True


class Subprocesses:
    def start(self, command, *, cwd, env, stdout_path, stderr_path):
        stdout, stderr = safe(stdout_path).open("xb"), safe(stderr_path).open("xb")
        try:
            child = subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        finally:
            stdout.close()
            stderr.close()
        return child

    def stop(self, child):
        # This adapter is Linux-guest only: kill the process group, then observe exit.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return child.wait(timeout=10)


def first_update_marker(root, config):
    """Observe complete event bytes only; a partial write is tried next poll.

    The caller durably copies the observed bytes before publication. This does
    not establish provider provenance or commit the learner's checkpoint.
    """
    for arm in ARMS:
        key = f"train/campaign/{arm}/events/step-00000001.result.json"
        path = root / key
        try:
            raw = read(path, PUBLIC_MAX)
            event = parse(raw)
            raw_text = raw.decode("utf-8")
        except (FileNotFoundError, ValueError, UnicodeError):
            continue
        family, curriculum = arm.split(".")
        if not (type(event) is dict and set(event) == {"sequence", "intent_sha256", "receipt"}
                and type(event["sequence"]) is int and event["sequence"] == 1 and pin(event["intent_sha256"])):
            continue
        receipt = event["receipt"]
        if not (type(receipt) is dict and receipt.get("schema") == "cas-teaching-binding-cuda/1"
                and receipt.get("execution_mode") == "cuda"
                and receipt.get("run_id") == config["run_id"] + "." + curriculum + "." + family
                and type(receipt.get("optimizer_steps")) is int and receipt["optimizer_steps"] == 1
                and type(receipt.get("cumulative_optimizer_steps")) is int and receipt["cumulative_optimizer_steps"] >= 1
                and receipt.get("accepted_weights_updated") is False):
            continue
        marker = {"schema": "cas-teaching-first-update/1", "job": config["job"], "run_id": config["run_id"],
            "source_sha256": config["bindings"]["source_sha256"], "manifest_sha256": config["bindings"]["manifest_sha256"],
            "material_sha256": config["bindings"]["material_receipt_sha256"], "request_sha256": config["request_sha256"],
            "arm": arm, "event": {"key": key, "raw_utf8": raw_text, "sha256": sha256(raw).hexdigest(), "bytes": len(raw)},
            "boundary": "WORKER_REPORTED_NOT_INDEPENDENT_LEARNING_PROOF"}
        if len(canonical(marker)) + 1 <= PUBLIC_MAX:
            return marker
    return None


def run_worker(root, phase, index, config, permit, python, budget, processes, *, public=None, campaign_sha=None, progress_callback=None):
    label = "train" if phase == "train" else f"predict{index}"
    output, bundle = root / label, root / "bundle"
    cap = 4800 if phase == "train" else 300
    available = min(cap, budget.remaining() - FINALIZE_RESERVE_SECONDS)
    require(available > 35, "INSUFFICIENT_PROCESS_TIME")
    command = [str(python), "-I", "-B", str(bundle / "cas_meta2/teaching_cycle/worker.py"), phase,
        "--bundle", str(bundle), "--manifest-sha256", config["bindings"]["manifest_sha256"],
        "--output", str(output), "--run-id", config["run_id"], "--expected-instance-id", permit["instance_id"],
        "--expected-account", ACCOUNT, "--expected-region", REGION, "--expected-instance-type", INSTANCE_TYPE,
        "--worker-seconds", str(int(available) - 30)]
    if phase == "predict":
        command += ["--campaign-summary", str(root / "train/campaign_summary.json"), "--campaign-summary-sha256", campaign_sha,
            "--public-sets", str(public), "--public-sets-sha256", config["bindings"]["public_sets_sha256"]]
    intent = {"phase": label, "command": command, "timeout_seconds": available, "absolute_deadline_unix": budget.end,
              "automatic_retries": 0, "started_monotonic": budget.clock.monotonic()}
    write(root / "driver" / f"{label}.intent.json", intent)
    child, failure, code = None, None, None
    try:
        child = processes.start(command, cwd=str(root), env={**os.environ, "CAS_META2_RUN_TEACHING_CYCLE": "1",
            "PYTHONDONTWRITEBYTECODE": "1", "AWS_MAX_ATTEMPTS": "1"},
            stdout_path=root / "driver" / f"{label}.stdout.log", stderr_path=root / "driver" / f"{label}.stderr.log")
        require(type(child.pid) is int and child.pid > 0, "PROCESS_PID")
        phase_end = budget.clock.monotonic() + available
        while child.poll() is None:
            budget.check()
            budget.scan(root, active=True)
            if phase == "train" and progress_callback is not None:
                progress_callback()
            require(budget.clock.monotonic() < phase_end, "PROCESS_TIMEOUT")
            budget.clock.sleep(min(1.0, max(0.01, phase_end - budget.clock.monotonic())))
        code = child.wait(timeout=10)
        budget.scan(root)
        if phase == "train" and progress_callback is not None:
            progress_callback()
    except BaseException as error:
        failure = {"type": type(error).__name__, "reason": str(error)[:1000]}
        if child is not None:
            code = processes.stop(child)
    receipt = {"phase": phase, "run_index": index, "pid": None if child is None else child.pid,
        "exit_code": code, "exited": code is not None, "failure": failure, "command": command,
        "absolute_deadline_unix": budget.end, "automatic_retries": 0}
    write(root / "driver" / f"{label}.exit.json", receipt)
    return receipt


def package_results(root, destination, budget):
    """Stream one member at a time; source bundle is retained as its original ZIP."""
    budget.scan(root)
    paths = []
    for path in root.rglob("*"):
        if path.is_file() and not path.is_relative_to(root / "bundle") and path != destination:
            relative = path.relative_to(root).as_posix()
            require(relative.split("/")[0] in {"train", "predict1", "predict2", "driver", "input", "bootstrap_evidence"}, "ARTIFACT_SCOPE")
            require("evaluator_private" not in path.parts and "final.targets" not in path.name, "PRIVATE_ARTIFACT_REJECTED")
            paths.append(path)
    require(sum(info(path).st_size for path in paths) <= ARTIFACT_MAX, "ARTIFACT_BOUND")
    with ZipFile(destination, "x", compression=ZIP_DEFLATED, allowZip64=True) as archive:
        for path in sorted(paths):
            budget.check()
            with path.open("rb") as source, archive.open(path.relative_to(root).as_posix(), "w", force_zip64=True) as target:
                while chunk := source.read(1024**2):
                    budget.check()
                    target.write(chunk)
                    require(destination.stat().st_size <= ARTIFACT_MAX, "ARCHIVE_OUTPUT_BOUND")
    return file_hash(destination, ARTIFACT_MAX)


def execute(config, root, *, config_sha256, permit, python, transport, processes=None, clock=None, bootstrap_evidence=None):
    """Execute once. Injected adapters let pure tests exercise every transition."""
    validate_config(config, config_sha256, permit)
    clock, processes = clock or Clock(), processes or Subprocesses()
    budget = Budget(config, clock)
    root = safe(root)
    require(not root.exists() and root.parent.is_dir(), "FRESH_ROOT_REQUIRED")
    root.mkdir()
    (root / "input").mkdir()
    (root / "driver").mkdir()
    bindings = config["bindings"]
    common = {"job": config["job"], "run_id": config["run_id"], "source_sha256": bindings["source_sha256"],
        "manifest_sha256": bindings["manifest_sha256"], "material_sha256": bindings["material_receipt_sha256"]}
    result = {"schema": "cas-teaching-guest-complete/1", **common, "status": "BLOCKED", "artifact": None,
        "training_ready_sha256": None, "campaign_summary_sha256": None, "prediction_seals": [],
        "processes": [], "automatic_retries": 0, "provider_identity_proved": False, "native_execution": "UNEXECUTED"}
    write(root / "driver/identity.json", {**common, "config_sha256": config_sha256, "request_sha256": config["request_sha256"],
        "resource_plan_sha256": config["resource_plan_sha256"], "permit": permit, "started_unix": clock.time()})
    write(root / "driver/remote.py", read(__file__, ARCHIVE_MAX), raw=True)

    def upload(path, key):
        identity = file_hash(path)
        budget.operation(True)
        budget.transfer(identity["bytes"], True)
        transport.upload(path, key, identity["bytes"], budget.end)
        return {"key": key, **identity}

    def download(key, path, maximum):
        budget.operation()
        transport.download(key, path, maximum, budget.end)
        budget.transfer(info(path, maximum).st_size)

    first_update_attempted = False

    def publish_first_update():
        nonlocal first_update_attempted
        if first_update_attempted:
            return
        marker = first_update_marker(root, config)
        if marker is None:
            return
        first_update_attempted = True  # This optional observation never retries.
        try:
            write(root / "driver/first_update.result.json", marker["event"]["raw_utf8"].encode("utf-8"), raw=True)
            path = root / "driver/first_update.json"
            write(path, marker)
            result["first_update"] = upload(path, "results/first_update.json")
        except Exception as error:
            # A status-channel failure must not become a new training gate.
            detail = {"type": type(error).__name__, "reason": str(error)[:1000], "automatic_retries": 0}
            write(root / "driver/first_update_error.json", detail)
            result["first_update_error"] = detail

    try:
        source = root / "input/source.zip"
        download("input/source.zip", source, ARCHIVE_MAX)
        extract_training(source, root / "bundle", bindings)
        train_exit = run_worker(root, "train", 0, config, permit, python, budget, processes,
                                progress_callback=publish_first_update)
        result["processes"].append(train_exit)
        require(train_exit["exited"] and train_exit["exit_code"] == 0 and train_exit["failure"] is None, "TRAIN_PROCESS_FAILED")
        summary_path = root / "train/campaign_summary.json"
        summary = parse(read(summary_path, 32 * 1024**2))
        complete = validate_campaign(summary, config)
        summary_ref = upload(summary_path, "results/train/campaign_summary.json")
        result["campaign_summary_sha256"] = summary_ref["sha256"]
        if not complete:
            result["status"] = "TEACHING_INCOMPLETE"
        else:
            ready = {"schema": "cas-teaching-training-ready/1", **common, "campaign_summary": summary_ref,
                "train_exit": train_exit, "all_allocations_finished": True,
                "selected_checkpoints": {arm: summary["arms"][arm]["selected_checkpoint"] for arm in ARMS}}
            ready_path = root / "driver/training_ready.json"
            write(ready_path, ready)
            ready_ref = upload(ready_path, "results/train_ready.json")
            result["training_ready_sha256"] = ready_ref["sha256"]
            release = None
            while release is None:
                require(budget.remaining() > 600 + FINALIZE_RESERVE_SECONDS, "PUBLIC_RELEASE_WAIT_EXPIRED")
                budget.operation()
                raw = transport.fetch_optional("input/public_release.json", PUBLIC_MAX, budget.end)
                if raw is None:
                    clock.sleep(min(20, budget.remaining() - 600 - FINALIZE_RESERVE_SECONDS))
                    continue
                require(type(raw) is bytes and len(raw) <= PUBLIC_MAX, "PUBLIC_RELEASE_BOUND")
                budget.transfer(len(raw))
                release = parse(raw)
                require(type(release) is dict and all(release.get(key) == value for key, value in {
                    "schema": "cas-teaching-public-release/1", **common, "training_ready_sha256": ready_ref["sha256"],
                    "campaign_summary_sha256": summary_ref["sha256"], "automatic_retries": 0}.items()), "PUBLIC_RELEASE_IDENTITY")
                declaration = release.get("public_sets")
                require(type(declaration) is dict and declaration.get("key") == "input/public.json"
                    and declaration.get("sha256") == bindings["public_sets_sha256"]
                    and type(declaration.get("bytes")) is int and 0 < declaration["bytes"] <= PUBLIC_MAX, "PUBLIC_RELEASE_FILE")
                write(root / "input/public_release.json", raw, raw=True)
            public_path = root / "input/public.json"
            download("input/public.json", public_path, release["public_sets"]["bytes"])
            require(file_hash(public_path, PUBLIC_MAX) == {key: release["public_sets"][key] for key in ("sha256", "bytes")}, "PUBLIC_FILE_PIN")
            publics = parse(read(public_path))
            require(type(publics) is dict and set(publics) == set(SPLITS) and all(type(rows) is list and len(rows) == 64 for rows in publics.values()), "PUBLIC_SPLITS")
            for rows in publics.values():
                for public in rows:
                    require(type(public) is dict and set(public) == {"problem", "observations"}
                        and type(public["problem"]) is str and 0 < len(public["problem"]) <= 8192
                        and type(public["observations"]) is list and len(public["observations"]) == 3, "PUBLIC_ONLY_FIELDS")
                    for observation in public["observations"]:
                        require(type(observation) is dict and set(observation) == {"slot", "tag", "values"}
                            and type(observation["slot"]) is int and observation["slot"] in (0, 1, 2)
                            and type(observation["tag"]) is str and 0 < len(observation["tag"]) <= 256
                            and type(observation["values"]) is list and len(observation["values"]) == 8
                            and all(type(value) in (int, float) and math.isfinite(value) for value in observation["values"]), "PUBLIC_OBSERVATION_FIELDS")
            pids = {train_exit["pid"]}
            for index in (1, 2):
                require(file_hash(summary_path)["sha256"] == summary_ref["sha256"], "TRAIN_SUMMARY_CHANGED")
                exit_receipt = run_worker(root, "predict", index, config, permit, python, budget, processes,
                    public=public_path, campaign_sha=summary_ref["sha256"])
                result["processes"].append(exit_receipt)
                require(exit_receipt["exited"] and exit_receipt["exit_code"] == 0 and exit_receipt["failure"] is None, "PREDICT_PROCESS_FAILED")
                require(exit_receipt["pid"] not in pids, "FRESH_PROCESS_REQUIRED")
                pids.add(exit_receipt["pid"])
                seal_path = root / f"predict{index}/prediction_seal.json"
                seal = parse(read(seal_path, 32 * 1024**2))
                require(seal.get("schema") == "cas-teaching-blind-prediction-seal/1" and seal.get("source_sha256") == bindings["source_sha256"]
                    and seal.get("private_targets_opened") is False and type(seal.get("artifacts")) is dict and len(seal["artifacts"]) == 24, "PREDICTION_SEAL")
                for name, declared in seal["artifacts"].items():
                    require(type(name) is str and re.fullmatch(r"(?:cas|generic)\.(?:aligned|ordinary)\.(?:untrained|trained)\.test_(?:fresh|context|names)\.json", name), "PREDICTION_MEMBER")
                    require(file_hash(seal_path.parent / name) == {key: declared[key] for key in ("sha256", "bytes")}, "PREDICTION_MEMBER_PIN")
                seal_ref = upload(seal_path, f"results/predict{index}/prediction_seal.json")
                result["prediction_seals"].append({"run_index": index, **seal_ref})
                prediction_ready = {"schema": "cas-teaching-prediction-ready/1", **common, "run_index": index,
                    "training_ready_sha256": ready_ref["sha256"], "campaign_summary_sha256": summary_ref["sha256"],
                    "prediction_exit": exit_receipt, "prediction_seal": seal_ref, "files": seal["artifacts"]}
                path = root / "driver" / f"prediction{index}_ready.json"
                write(path, prediction_ready)
                upload(path, f"results/prediction{index}_ready.json")
            result["status"] = "COMPLETE"
    except BaseException as error:
        result["reason"] = {"type": type(error).__name__, "message": str(error)[:1000]}
    try:
        if bootstrap_evidence is not None:
            destination = root / "bootstrap_evidence"
            destination.mkdir()
            total = 0
            for name in BOOTSTRAP_FILES:
                path = safe(bootstrap_evidence) / name
                if path.exists():
                    raw = read(path, BOOTSTRAP_MAX)
                    total += len(raw)
                    require(total <= BOOTSTRAP_MAX, "BOOTSTRAP_EVIDENCE_BOUND")
                    write(destination / name, raw, raw=True)
        write(root / "driver/outcome.json", {**result, "resources_before_packaging": budget.report()})
        archive = root / "artifacts.zip"
        package_results(root, archive, budget)
        result["artifact"] = upload(archive, "results/artifacts.zip")
    except BaseException as error:
        result["packaging_error"] = {"type": type(error).__name__, "message": str(error)[:1000]}
        if result["status"] == "COMPLETE":
            result["status"] = "BLOCKED"
    # Include the last put and its bytes in the shared receipt, not just the
    # earlier calls. The tiny fixed-point loop resolves the JSON digit count.
    budget.operation(True)
    before_final = budget.uploaded
    result["resources"] = budget.report()
    for _ in range(8):
        final_raw = canonical(result) + b"\n"
        total = before_final + len(final_raw)
        require(total <= ARTIFACT_MAX, "TRANSFER_BYTE_BOUND")
        if result["resources"]["uploaded_bytes"] == total:
            break
        result["resources"]["uploaded_bytes"] = total
    else:
        raise GuestError("TEACHING_GUEST:FINAL_RECEIPT_SIZE_UNSTABLE")
    budget.uploaded = total
    final_path = root / "driver/complete.json"
    write(final_path, final_raw, raw=True)
    # Completion is the final upload. The parent must collect its bound archive
    # before deleting cloud evidence; this guest never deletes cloud objects.
    transport.upload(final_path, "results/complete.json", len(final_raw), budget.end)
    return result


class S3CLI:
    """Real guest seam, never instantiated or executed by the pure tests."""
    def __init__(self, bucket, *, clock=None, executable="aws"):
        self.bucket, self.clock, self.executable = bucket, clock or Clock(), executable

    def _call(self, arguments, deadline, *, absent=False):
        require(deadline > self.clock.time(), "TRANSPORT_DEADLINE")
        process = subprocess.run([self.executable, "s3api", *arguments, "--region", REGION, "--no-cli-pager"],
            capture_output=True, timeout=min(60, deadline - self.clock.time()),
            env={**os.environ, "AWS_MAX_ATTEMPTS": "1", "AWS_RETRY_MODE": "standard", "AWS_PAGER": ""})
        require(len(process.stdout) + len(process.stderr) <= LOG_MAX, "TRANSPORT_LOG_BOUND")
        if absent and process.returncode and (b"NoSuchKey" in process.stderr or b"(404)" in process.stderr):
            return None
        require(process.returncode == 0, "S3_CLI_FAILED")
        return parse(process.stdout or b"{}")

    def _head(self, key, maximum, deadline, absent=False):
        value = self._call(["head-object", "--bucket", self.bucket, "--key", key], deadline, absent=absent)
        if value is not None:
            require(type(value.get("ContentLength")) is int and 0 < value["ContentLength"] <= maximum
                and type(value.get("ETag")) is str, "S3_OBJECT_BOUND")
        return value

    def download(self, key, destination, maximum, deadline):
        require(not safe(destination).exists(), "FRESH_DOWNLOAD_REQUIRED")
        head = self._head(key, maximum, deadline)
        self._call(["get-object", "--bucket", self.bucket, "--key", key, "--if-match", head["ETag"],
            "--range", f"bytes=0-{head['ContentLength'] - 1}", str(destination)], deadline)
        require(info(destination, maximum).st_size == head["ContentLength"], "S3_DOWNLOAD_SIZE")

    def fetch_optional(self, key, maximum, deadline):
        head = self._head(key, maximum, deadline, True)
        if head is None:
            return None
        import tempfile
        with tempfile.TemporaryDirectory(prefix="cas-public-release-") as scratch:
            path = Path(scratch) / "release.json"
            self._call(["get-object", "--bucket", self.bucket, "--key", key, "--if-match", head["ETag"],
                "--range", f"bytes=0-{head['ContentLength'] - 1}", str(path)], deadline)
            return read(path, maximum)

    def upload(self, path, key, maximum, deadline):
        info(path, maximum)
        self._call(["put-object", "--bucket", self.bucket, "--key", key, "--body", str(path),
            "--server-side-encryption", "AES256"], deadline)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "config-sha256", "permit", "permit-sha256", "root", "python"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--bootstrap-evidence")
    args = parser.parse_args(argv)
    require(sys.platform == "linux" and sys.flags.isolated and sys.dont_write_bytecode, "ISOLATED_LINUX_DRIVER_REQUIRED")
    config_raw, permit_raw = read(args.config), read(args.permit)
    require(pin(args.config_sha256) and sha256(config_raw).hexdigest() == args.config_sha256, "CONFIG_RAW_PIN")
    require(pin(args.permit_sha256) and sha256(permit_raw).hexdigest() == args.permit_sha256, "PERMIT_RAW_PIN")
    config, permit = parse(config_raw), parse(permit_raw)
    result = execute(config, args.root, config_sha256=args.config_sha256, permit=permit, python=args.python,
        transport=S3CLI(config["bucket"]), bootstrap_evidence=args.bootstrap_evidence)
    print(json.dumps({"status": result["status"], "artifact": result["artifact"], "resources": result["resources"]}))
    return 0 if result["status"] in ("COMPLETE", "TEACHING_INCOMPLETE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
