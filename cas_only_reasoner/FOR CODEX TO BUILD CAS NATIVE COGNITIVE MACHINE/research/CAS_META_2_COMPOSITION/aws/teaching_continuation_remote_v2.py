"""Standalone slice-two continuation driver; frozen helpers are separately byte-pinned.

One new cloud job restores one old logical run, waits for the parent's restore
admission, and trains one slice. No repository/neural/SDK imports occur here.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
from zipfile import ZipFile, ZIP_DEFLATED

SCHEMA = "cas-teaching-continuation-guest-config/1"
LOGICAL_RUN = "cas-meta2-teaching-20260908052915-8b5df59c"
CAMPAIGN_ROOT = "/opt/cas-teaching/job/train/campaign"
RESUME_SUMMARY = "train_continued_001/campaign_summary.json"
LATEST_SUMMARY = "train_continued_002/campaign_summary.json"
BASE_SHA = "14a09d391435ffc354343f64ede83a079540000694dbd273bc55bedd13928a2e"
PRIOR_MAX, PRIOR_EXPANDED_MAX = 536870912, 1073741824
CONTINUATION_PINS = frozenset(("prior_state_archive_sha256", "prior_state_manifest_sha256",
    "prior_package_receipt_sha256", "prior_summary_sha256", "prior_inspection_sha256",
    "prior_parent_result_sha256", "prior_complete_sha256", "prior_cleanup_sha256",
    "prior_result_archive_sha256", "prior_package_validator_sha256", "base_guest_driver_sha256",
    "restore_probe_sha256", "continuation_plan_sha256", "profile_sha256"))


def require(condition, code):
    if not condition:
        raise ValueError("TEACHING_CONTINUATION_GUEST:" + code)


def raw_read(path, maximum=4 * 1024**2):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "SUPPORT_PATH")
    info = path.stat()
    require(path.is_file() and info.st_nlink == 1 and 0 < info.st_size <= maximum, "SUPPORT_BOUND")
    raw = path.read_bytes()
    require(len(raw) == info.st_size, "SUPPORT_CHANGED")
    return raw


def private_module(path, expected, name):
    require(sha256(raw_read(path)).hexdigest() == expected, "SUPPORT_SOURCE_PIN:" + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_support(directory, continuation):
    directory = Path(directory)
    require(continuation["base_guest_driver_sha256"] == BASE_SHA, "FROZEN_BASE_DRIVER")
    base = private_module(directory / "base_remote.py", BASE_SHA, "_continuation_frozen_guest_helpers")
    validator = private_module(directory / "continuation_package.py", continuation["prior_package_validator_sha256"],
                               "_continuation_pinned_prior_validator")
    require(sha256(raw_read(directory / "restore_probe.py")).hexdigest() == continuation["restore_probe_sha256"], "PROBE_SOURCE_PIN")
    return base, validator


def validate_config(config, config_sha, permit, base):
    require(type(config) is dict and set(config) == {"schema", "job", "run_id", "request_sha256",
        "resource_plan_sha256", "bindings", "resource_plan", "bucket", "prefix", "launch_started_unix",
        "deadline_unix", "continuation"}, "CONFIG_FIELDS")
    require(config["schema"] == SCHEMA and re.fullmatch(base.JOB_PATTERN, config["job"] or "")
            and config["run_id"] == LOGICAL_RUN and config["job"] != LOGICAL_RUN, "SEPARATE_CLOUD_AND_LOGICAL_ID")
    require(base.pin(config_sha) and base.pin(config["request_sha256"]), "CONFIG_PINS")
    require(config["bucket"] == config["job"] + "-" + base.ACCOUNT and config["prefix"] == "", "BUCKET_SCOPE")
    bindings, plan, prior = config["bindings"], config["resource_plan"], config["continuation"]
    require(type(bindings) is dict and set(bindings) == base.BINDINGS
            and all(base.pin(v, 40 if k == "source_commit" else 64) for k, v in bindings.items()), "WORKER_BINDINGS")
    require(type(prior) is dict and set(prior) == CONTINUATION_PINS | {
        "prior_state_archive_bytes", "prior_state_expanded_bytes", "original_campaign_root"}
        and all(base.pin(prior[k]) for k in CONTINUATION_PINS), "CONTINUATION_FIELDS")
    require(prior["original_campaign_root"] == CAMPAIGN_ROOT
            and type(prior["prior_state_archive_bytes"]) is int and 0 < prior["prior_state_archive_bytes"] <= PRIOR_MAX
            and type(prior["prior_state_expanded_bytes"]) is int and 0 < prior["prior_state_expanded_bytes"] <= PRIOR_EXPANDED_MAX,
            "PRIOR_PATH_OR_BOUND")
    require(sha256(base.canonical(plan)).hexdigest() == config["resource_plan_sha256"], "PLAN_DIGEST")
    fixed = {"account_id": base.ACCOUNT, "region": base.REGION, "instance_type": base.INSTANCE_TYPE,
        "instance_count": 1, "runtime_seconds_max": 7200, "training_worker_seconds_max": 4800,
        "restore_probe_seconds_max": 900, "prediction_process_count_max": 2, "prediction_seconds_per_process_max": 300,
        "artifact_expanded_bytes_max": base.ARTIFACT_MAX, "artifact_download_bytes_max": base.ARTIFACT_MAX,
        "artifact_upload_bytes_max": base.ARTIFACT_MAX, "automatic_retries": 0,
        "prior_state_archive_bytes_max": PRIOR_MAX, "prior_state_expanded_bytes_max": PRIOR_EXPANDED_MAX}
    require(all(type(plan.get(k)) is type(v) and plan[k] == v for k, v in fixed.items()), "RESOURCE_SCOPE")
    require(plan["worksheet_limits"]["guest_s3_api_attempts_max"] == 896, "REQUEST_ALLOCATION")
    require(all(type(config[k]) in (int, float) and math.isfinite(config[k])
                for k in ("deadline_unix", "launch_started_unix"))
            and 0 < config["deadline_unix"] - config["launch_started_unix"] <= 7200, "LIFETIME_BOUND")
    require(type(permit) is dict and set(permit) == {"schema", "job", "run_id", "config_sha256", "request_sha256",
        "instance_id", "deadline_unix", "shutdown_schedule_arn", "shutdown_schedule_confirmed", "automatic_retries"}, "PERMIT_FIELDS")
    require(all(permit.get(k) == v for k, v in {"schema": base.PERMIT_SCHEMA, "job": config["job"],
        "run_id": LOGICAL_RUN, "config_sha256": config_sha, "request_sha256": config["request_sha256"],
        "deadline_unix": config["deadline_unix"], "shutdown_schedule_confirmed": True, "automatic_retries": 0}.items()), "PERMIT_IDENTITY")
    require(permit["shutdown_schedule_confirmed"] is True and type(permit["automatic_retries"]) is int,
            "PERMIT_STRICT_GATE")
    require(re.fullmatch(r"i-[0-9a-f]{17}", permit["instance_id"] or "")
        and permit["instance_id"] not in ("i-0272a6d80f3b5ad75", "i-0c89cf580dd58a803")
        and permit["shutdown_schedule_arn"] == f"arn:aws:scheduler:{base.REGION}:{base.ACCOUNT}:schedule/default/" + config["job"],
        "NEW_INSTANCE_AND_SCHEDULE")
    require(base.file_hash(__file__)["sha256"] == bindings["guest_driver_sha256"], "DRIVER_PIN")


def prior_expected(config):
    b, c = config["bindings"], config["continuation"]
    return {"logical_run_id": config["run_id"], "original_campaign_root": c["original_campaign_root"],
        "source_sha256": b["source_sha256"], "bundle_manifest_sha256": b["manifest_sha256"],
        "source_archive_sha256": b["archive_sha256"], "material_receipt_sha256": b["material_receipt_sha256"],
        "summary_sha256": c["prior_summary_sha256"], "parent_sha256": c["prior_parent_result_sha256"],
        "complete_sha256": c["prior_complete_sha256"], "prior_result_archive_sha256": c["prior_result_archive_sha256"],
        "inspection_sha256": c["prior_inspection_sha256"], "training_cases_sha256": b["training_cases_sha256"],
        "development_cases_sha256": b["development_cases_sha256"], "profile_sha256": c["profile_sha256"]}


def restore_files(archive, root, manifest, base, budget):
    require(str((root / "train/campaign").as_posix()) == manifest["original_campaign_root"], "LITERAL_CAMPAIGN_ROOT")
    require(manifest.get("schema") == "cas-teaching-prior-state/2"
            and manifest.get("summary_path") == RESUME_SUMMARY
            and manifest.get("retained_summary_path") == "train/campaign_summary.json",
            "SLICE_TWO_PRIOR_SUMMARIES_REQUIRED")
    with ZipFile(archive) as zipped:
        for name, expected in manifest["members"].items():
            budget.check()
            require((name in (RESUME_SUMMARY, "train/campaign_summary.json") or name.startswith("train/campaign/"))
                    and ".." not in Path(name).parts, "PRIOR_MEMBER_SCOPE")
            path = base.safe(root / name)
            require(not path.exists(), "RESTORE_WOULD_OVERWRITE")
            path.parent.mkdir(parents=True, exist_ok=True)
            digest, size = sha256(), 0
            with zipped.open(name) as source, path.open("xb") as target:
                while chunk := source.read(1024**2):
                    budget.check()
                    size += len(chunk)
                    require(size <= expected["bytes"], "RESTORE_MEMBER_SIZE")
                    digest.update(chunk)
                    target.write(chunk)
            require(size == expected["bytes"] and digest.hexdigest() == expected["sha256"], "RESTORE_MEMBER_PIN")
    budget.scan(root)


def verify_prior_prefix(root, manifest, base):
    # Journals append transactions; no prior member may be rewritten or trimmed.
    for name, expected in manifest["members"].items():
        require(base.file_hash(root / name) == expected, "PRIOR_HISTORY_CHANGED:" + name)


def process_command(root, phase, config, permit, python, support, seconds, *, campaign_sha=None, public=None):
    b, c = config["bindings"], config["continuation"]
    if phase == "restore":
        pairs = {"bundle": root / "bundle", "bundle-manifest-sha256": b["manifest_sha256"],
            "source-archive": root / "input/source.zip", "source-archive-sha256": b["archive_sha256"],
            "prior-archive": root / "input/prior_state.zip", "prior-archive-sha256": c["prior_state_archive_sha256"],
            "prior-manifest": root / "input/prior_state_manifest.json", "prior-manifest-sha256": c["prior_state_manifest_sha256"],
            "validator": support / "continuation_package.py", "validator-sha256": c["prior_package_validator_sha256"],
            "probe-sha256": c["restore_probe_sha256"], "material-sha256": b["material_receipt_sha256"],
            "output": root / "restore", "job": config["job"], "run-id": config["run_id"],
            "expected-instance-id": permit["instance_id"], "expected-account": "807562639912",
            "expected-region": "us-west-2", "expected-instance-type": "g7.2xlarge", "max-seconds": seconds}
        command = [str(python), "-I", "-B", str(support / "restore_probe.py")]
    else:
        label = "train_continued_002" if phase == "train" else phase
        pairs = {"bundle": root / "bundle", "manifest-sha256": b["manifest_sha256"], "output": root / label,
            "run-id": config["run_id"], "expected-instance-id": permit["instance_id"], "expected-account": "807562639912",
            "expected-region": "us-west-2", "expected-instance-type": "g7.2xlarge", "worker-seconds": seconds}
        command = [str(python), "-I", "-B", str(root / "bundle/cas_meta2/teaching_cycle/worker.py"),
                   "train" if phase == "train" else "predict"]
        if phase == "train":
            pairs.update({"resume-summary": root / RESUME_SUMMARY, "resume-summary-sha256": c["prior_summary_sha256"]})
        else:
            pairs.update({"campaign-summary": root / LATEST_SUMMARY, "campaign-summary-sha256": campaign_sha,
                          "public-sets": public, "public-sets-sha256": b["public_sets_sha256"]})
    return command + [item for name, value in pairs.items() for item in ("--" + name, str(value))]


def run_process(root, phase, config, permit, python, support, base, budget, processes, *, callback=None, **kwargs):
    cap = 900 if phase == "restore" else 4800 if phase == "train" else 300
    # Match the parent training wait. The 30-second worker gap below leaves
    # room for a graceful summary before that wait ends, even after slow setup.
    reserve = 900 if phase == "train" else base.FINALIZE_RESERVE_SECONDS
    available = min(cap, budget.remaining() - reserve)
    require(available > 35, "INSUFFICIENT_PROCESS_TIME")
    command = process_command(root, phase, config, permit, python, support, int(available) - (0 if phase == "restore" else 30), **kwargs)
    base.write(root / "driver" / (phase + ".intent.json"), {"phase": phase, "command": command,
        "timeout_seconds": available, "absolute_deadline_unix": budget.end, "automatic_retries": 0})
    child, code, failure = None, None, None
    try:
        child = processes.start(command, cwd=str(root), env={**os.environ, "CAS_META2_RUN_TEACHING_CYCLE": "1",
            "PYTHONDONTWRITEBYTECODE": "1", "AWS_MAX_ATTEMPTS": "1"},
            stdout_path=root / "driver" / (phase + ".stdout.log"), stderr_path=root / "driver" / (phase + ".stderr.log"))
        require(type(child.pid) is int and child.pid > 0, "PROCESS_PID")
        end = budget.clock.monotonic() + available
        while child.poll() is None:
            budget.check()
            budget.scan(root, active=True)
            if callback is not None:
                callback()
            require(budget.clock.monotonic() < end, "PROCESS_TIMEOUT")
            budget.clock.sleep(min(1, max(0.01, end - budget.clock.monotonic())))
        code = child.wait(timeout=10)
        budget.check()
        require(budget.clock.monotonic() <= end, "PROCESS_EXIT_AFTER_DEADLINE")
        budget.scan(root)
        if callback is not None:
            callback()
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error)[:1000]}
        if child is not None:
            code = processes.stop(child)
    result = {"phase": "predict" if phase.startswith("predict") else phase,
        "run_index": int(phase[-1]) if phase.startswith("predict") else 0,
        "pid": None if child is None else child.pid, "exit_code": code, "exited": code is not None,
        "failure": failure, "command": command, "automatic_retries": 0, "absolute_deadline_unix": budget.end}
    base.write(root / "driver" / (phase + ".exit.json"), result)
    return result


def validate_restore(document, config):
    b, c = config["bindings"], config["continuation"]
    wanted = {"schema": "cas-teaching-gpu-restore/1", "status": "RESTORED_NO_TRAINING", "job": config["job"],
        "run_id": config["run_id"], "source_sha256": b["source_sha256"], "bundle_manifest_sha256": b["manifest_sha256"],
        "material_sha256": b["material_receipt_sha256"], "prior_archive_sha256": c["prior_state_archive_sha256"],
        "prior_manifest_sha256": c["prior_state_manifest_sha256"], "summary_sha256": c["prior_summary_sha256"],
        "probe_sha256": c["restore_probe_sha256"], "input_tree_unchanged": True,
        "optimizer_steps_performed": 0, "predictions_run": False}
    require(type(document) is dict and all(type(document.get(k)) is type(v) and document[k] == v for k, v in wanted.items()),
            "RESTORE_PROOF_REJECTED")


def new_progress(root, config, manifest, base):
    for arm, prior in manifest["arms"].items():
        previous = prior["committed_optimizer_steps"]
        relative = f"train/campaign/{arm}/events/step-{previous + 1:08d}.result.json"
        path = root / relative
        if not path.is_file():
            continue
        try:
            raw = base.read(path, 256 * 1024)
            event = base.parse(raw)
            receipt = event["receipt"]
            family, curriculum = arm.split(".")
            require(set(event) == {"sequence", "intent_sha256", "receipt"}
                and base.pin(event["intent_sha256"]) and receipt.get("schema") == "cas-teaching-binding-cuda/1"
                and type(event["sequence"]) is int and event["sequence"] == previous + 1
                and receipt["run_id"] == config["run_id"] + "." + curriculum + "." + family
                and receipt["execution_mode"] == "cuda" and receipt["accepted_weights_updated"] is False
                and type(receipt["optimizer_steps"]) is int and receipt["optimizer_steps"] == 1
                and type(receipt["cumulative_optimizer_steps"]) is int
                and receipt["cumulative_optimizer_steps"] == previous + 1, "NEW_UPDATE_IDENTITY")
            return {"schema": "cas-teaching-continuation-progress/1", "job": config["job"], "run_id": config["run_id"],
                "request_sha256": config["request_sha256"], "source_sha256": config["bindings"]["source_sha256"],
                "manifest_sha256": config["bindings"]["manifest_sha256"], "arm": arm,
                "prior_optimizer_steps": previous, "event": {"key": relative, "raw_utf8": raw.decode("utf-8"),
                    "sha256": sha256(raw).hexdigest(), "bytes": len(raw)},
                "boundary": "WORKER_REPORTED_NEW_CUDA_UPDATE_NOT_INDEPENDENT_LEARNING_PROOF"}
        except (ValueError, KeyError, TypeError, OSError):
            continue  # Atomic publication may not yet be complete; never report an old event.
    return None


def package_results(root, output, base, budget):
    budget.scan(root)
    allowed = {"train", "train_continued_001", "train_continued_002", "restore", "predict1", "predict2", "driver", "input", "bootstrap_evidence"}
    paths = []
    for path in root.rglob("*"):
        if path.is_file() and not path.is_relative_to(root / "bundle") and path != output:
            relative = path.relative_to(root).as_posix()
            require(relative.split("/")[0] in allowed, "ARTIFACT_SCOPE")
            require(not any(word in relative.lower() for word in ("evaluation_private", "evaluator_private", "final_gold", "teacherdata")), "PRIVATE_ARTIFACT_REJECTED")
            paths.append(path)
    require(len(paths) <= base.FILES_MAX and sum(base.info(p).st_size for p in paths) <= base.ARTIFACT_MAX, "ARCHIVE_BOUND")
    with ZipFile(output, "x", compression=ZIP_DEFLATED, allowZip64=True) as zipped:
        for path in sorted(paths):
            budget.check()
            with path.open("rb") as source, zipped.open(path.relative_to(root).as_posix(), "w", force_zip64=True) as target:
                while chunk := source.read(1024**2):
                    budget.check()
                    target.write(chunk)
                    require(output.stat().st_size <= base.ARTIFACT_MAX, "ARCHIVE_OUTPUT_BOUND")
    return base.file_hash(output)


def execute(config, root, *, config_sha256, permit, python, transport, support_dir,
            processes=None, clock=None, bootstrap_evidence=None, validator_override=None):
    base, validator = load_support(support_dir, config["continuation"])
    if validator_override is not None:  # Pure test seam; never exposed by the CLI.
        validator = validator_override
    validate_config(config, config_sha256, permit, base)
    clock, processes = clock or base.Clock(), processes or base.Subprocesses()
    budget = base.Budget(config, clock)
    root, support = base.safe(root), base.safe(support_dir)
    require(not root.exists() and root.parent.is_dir(), "FRESH_ROOT")
    root.mkdir()
    for name in ("input", "driver"):
        (root / name).mkdir()
    c, b = config["continuation"], config["bindings"]
    common = {"job": config["job"], "run_id": config["run_id"], "source_sha256": b["source_sha256"],
        "manifest_sha256": b["manifest_sha256"], "material_sha256": b["material_receipt_sha256"],
        "continuation_sha256": sha256(base.canonical(c)).hexdigest()}
    result = {"schema": "cas-teaching-guest-complete/1", **common, "status": "BLOCKED", "artifact": None,
        "restore_ready_sha256": None, "restore_receipt_sha256": None, "training_ready_sha256": None,
        "campaign_summary_sha256": None, "latest_summary_path": LATEST_SUMMARY,
        "original_summary_path": RESUME_SUMMARY, "prediction_seals": [], "processes": [],
        "automatic_retries": 0, "native_execution": "UNEXECUTED", "provider_identity_proved": False}
    base.write(root / "driver/identity.json", {**common, "config_sha256": config_sha256,
        "request_sha256": config["request_sha256"], "permit": permit, "prior": c})
    for name, path in (("remote.py", Path(__file__)), ("base_remote.py", support / "base_remote.py"),
                       ("continuation_package.py", support / "continuation_package.py"), ("restore_probe.py", support / "restore_probe.py")):
        base.write(root / "driver" / name, base.read(path), raw=True)

    def upload(path, key):
        identity = base.file_hash(path)
        budget.operation(True)
        budget.transfer(identity["bytes"], True)
        transport.upload(path, key, identity["bytes"], budget.end)
        return {"key": key, **identity}

    def download(key, path, maximum):
        budget.operation()
        transport.download(key, path, maximum, budget.end)
        budget.transfer(base.info(path, maximum).st_size)

    def wait_release(key, schema, fields, minimum):
        while True:
            require(budget.remaining() > minimum + base.FINALIZE_RESERVE_SECONDS, "RELEASE_WAIT_EXPIRED")
            budget.operation()
            raw = transport.fetch_optional(key, base.PUBLIC_MAX, budget.end)
            if raw is None:
                clock.sleep(min(20, budget.remaining() - minimum - base.FINALIZE_RESERVE_SECONDS))
                continue
            require(type(raw) is bytes and len(raw) <= base.PUBLIC_MAX, "RELEASE_BOUND")
            budget.transfer(len(raw))
            doc = base.parse(raw)
            require(type(doc) is dict and type(doc.get("automatic_retries")) is int, "RELEASE_TYPES")
            require(all(doc.get(k) == v for k, v in {"schema": schema, **common, **fields, "automatic_retries": 0}.items()),
                    "RELEASE_IDENTITY")
            base.write(root / "input" / key.rsplit("/", 1)[-1], raw, raw=True)
            return doc

    manifest, progress_attempted = None, False

    def progress():
        nonlocal progress_attempted
        if progress_attempted:
            return
        marker = new_progress(root, config, manifest, base)
        if marker is not None:
            progress_attempted = True
            try:
                require(len(base.canonical(marker)) + 1 <= base.PUBLIC_MAX, "PROGRESS_BOUND")
                path = root / "driver/new_update.json"
                base.write(path, marker)
                result["first_new_update"] = upload(path, "results/new_update.json")
            except Exception as error:
                result["progress_error"] = {"type": type(error).__name__, "message": str(error)[:500]}

    try:
        source, prior, prior_manifest = root / "input/source.zip", root / "input/prior_state.zip", root / "input/prior_state_manifest.json"
        download("input/source.zip", source, base.ARCHIVE_MAX)
        base.extract_training(source, root / "bundle", b)
        download("input/prior_state.zip", prior, c["prior_state_archive_bytes"])
        download("input/prior_state_manifest.json", prior_manifest, 4 * 1024**2)
        require(base.info(prior).st_size == c["prior_state_archive_bytes"], "PRIOR_ARCHIVE_BYTES")
        manifest = validator.validate_package(prior, prior_manifest, archive_sha256=c["prior_state_archive_sha256"],
            manifest_sha256=c["prior_state_manifest_sha256"], expected_bindings=prior_expected(config))
        require(manifest["expanded_bytes"] + base.info(prior_manifest).st_size == c["prior_state_expanded_bytes"], "PRIOR_EXPANDED_BYTES")
        restore_files(prior, root, manifest, base, budget)
        restored = run_process(root, "restore", config, permit, python, support, base, budget, processes)
        result["processes"].append(restored)
        require(restored["exited"] and restored["exit_code"] == 0 and restored["failure"] is None, "RESTORE_PROCESS_FAILED")
        probe_path = root / "restore/restore_receipt.json"
        validate_restore(base.parse(base.read(probe_path, 4 * 1024**2)), config)
        verify_prior_prefix(root, manifest, base)
        probe_ref = upload(probe_path, "results/restore/restore_receipt.json")
        ready = {"schema": "cas-teaching-continuation-restore-ready/1", **common,
                 "restore_receipt": probe_ref, "restore_exit": restored}
        base.write(root / "driver/restore_ready.json", ready)
        ready_ref = upload(root / "driver/restore_ready.json", "results/restore_ready.json")
        result.update(restore_ready_sha256=ready_ref["sha256"], restore_receipt_sha256=probe_ref["sha256"])
        restore_fields = {k: result[k] for k in ("restore_ready_sha256", "restore_receipt_sha256")}
        wait_release("input/train_release.json", "cas-teaching-continuation-train-release/1", restore_fields, 60)
        verify_prior_prefix(root, manifest, base)
        trained = run_process(root, "train", config, permit, python, support, base, budget, processes, callback=progress)
        result["processes"].append(trained)
        require(trained["pid"] != restored["pid"] and trained["exited"] and trained["exit_code"] == 0
                and trained["failure"] is None, "TRAIN_PROCESS_FAILED")
        verify_prior_prefix(root, manifest, base)
        summary_path = root / LATEST_SUMMARY
        summary = base.parse(base.read(summary_path, 32 * 1024**2))
        complete = base.validate_campaign(summary, config)
        require(summary.get("resumed_summary_sha256") == c["prior_summary_sha256"]
                and summary.get("campaign_root") == CAMPAIGN_ROOT, "RESUMED_SUMMARY_IDENTITY")
        require(all(report.get("max_epochs") == 16 for report in summary["arms"].values()), "UNCHANGED_16_EPOCH_ALLOCATION")
        if complete:
            require(all(report["cursor"] == {"epoch": 16, "batch": 0, "stage": 0} for report in summary["arms"].values()), "FULL_16_EPOCHS_REQUIRED")
        summary_ref = upload(summary_path, "results/" + LATEST_SUMMARY)
        result["campaign_summary_sha256"] = summary_ref["sha256"]
        if not complete:
            result["status"] = "TEACHING_INCOMPLETE"
        else:
            ready = {"schema": "cas-teaching-training-ready/1", **common, **restore_fields,
                "campaign_summary": summary_ref, "train_exit": trained, "all_allocations_finished": True,
                "latest_summary_path": LATEST_SUMMARY,
                "selected_checkpoints": {arm: summary["arms"][arm]["selected_checkpoint"] for arm in base.ARMS}}
            base.write(root / "driver/training_ready.json", ready)
            ready_ref = upload(root / "driver/training_ready.json", "results/train_ready.json")
            result["training_ready_sha256"] = ready_ref["sha256"]
            release = wait_release("input/public_release.json", "cas-teaching-public-release/1",
                {**restore_fields, "training_ready_sha256": ready_ref["sha256"], "campaign_summary_sha256": summary_ref["sha256"]}, 600)
            declared = release["public_sets"]
            require(declared.get("key") == "input/public.json" and declared.get("sha256") == b["public_sets_sha256"]
                    and type(declared.get("bytes")) is int and 0 < declared["bytes"] <= base.PUBLIC_MAX, "PUBLIC_FILE_IDENTITY")
            public = root / "input/public.json"
            download("input/public.json", public, declared["bytes"])
            require(base.file_hash(public) == {k: declared[k] for k in ("sha256", "bytes")}, "PUBLIC_PIN")
            pids = {restored["pid"], trained["pid"]}
            for index in (1, 2):
                require(base.file_hash(summary_path)["sha256"] == summary_ref["sha256"], "SUMMARY_CHANGED")
                exited = run_process(root, f"predict{index}", config, permit, python, support, base, budget, processes,
                                     campaign_sha=summary_ref["sha256"], public=public)
                result["processes"].append(exited)
                require(exited["exited"] and exited["exit_code"] == 0 and exited["failure"] is None
                        and exited["pid"] not in pids, "PREDICTION_PROCESS_FAILED")
                pids.add(exited["pid"])
                seal_path = root / f"predict{index}/prediction_seal.json"
                seal = base.parse(base.read(seal_path))
                require(seal.get("schema") == "cas-teaching-blind-prediction-seal/1"
                        and seal.get("source_sha256") == b["source_sha256"] and seal.get("private_targets_opened") is False
                        and type(seal.get("artifacts")) is dict and len(seal["artifacts"]) == 24, "PREDICTION_SEAL")
                for name, declaration in seal["artifacts"].items():
                    require(re.fullmatch(r"(?:cas|generic)\.(?:aligned|ordinary)\.(?:untrained|trained)\.test_(?:fresh|context|names)\.json", name)
                            and base.file_hash(seal_path.parent / name) == {k: declaration[k] for k in ("sha256", "bytes")}, "PREDICTION_MEMBER")
                seal_ref = upload(seal_path, f"results/predict{index}/prediction_seal.json")
                result["prediction_seals"].append({"run_index": index, **seal_ref})
                ready = {"schema": "cas-teaching-prediction-ready/1", **common, **restore_fields, "run_index": index,
                    "training_ready_sha256": result["training_ready_sha256"], "campaign_summary_sha256": summary_ref["sha256"],
                    "prediction_exit": exited, "prediction_seal": seal_ref, "files": seal["artifacts"]}
                path = root / "driver" / f"prediction{index}_ready.json"
                base.write(path, ready)
                upload(path, f"results/prediction{index}_ready.json")
            result["status"] = "COMPLETE"
    except BaseException as error:
        result["reason"] = {"type": type(error).__name__, "message": str(error)[:1000]}
    try:
        if bootstrap_evidence is not None:
            (root / "bootstrap_evidence").mkdir()
            total = 0
            for name in base.BOOTSTRAP_FILES:
                path = base.safe(bootstrap_evidence) / name
                if path.exists():
                    raw = base.read(path, base.BOOTSTRAP_MAX)
                    total += len(raw)
                    require(total <= base.BOOTSTRAP_MAX, "BOOTSTRAP_LOG_BOUND")
                    base.write(root / "bootstrap_evidence" / name, raw, raw=True)
        base.write(root / "driver/outcome.json", {**result, "resources_before_packaging": budget.report()})
        archive = root / "artifacts.zip"
        package_results(root, archive, base, budget)
        result["artifact"] = upload(archive, "results/artifacts.zip")
    except BaseException as error:
        result["packaging_error"] = {"type": type(error).__name__, "message": str(error)[:1000]}
        result["status"] = "BLOCKED"
    budget.operation(True)
    result["resources"] = budget.report()
    for _ in range(8):
        raw = base.canonical(result) + b"\n"
        total = budget.uploaded + len(raw)
        require(total <= base.ARTIFACT_MAX, "FINAL_UPLOAD_BOUND")
        if result["resources"]["uploaded_bytes"] == total:
            break
        result["resources"]["uploaded_bytes"] = total
    else:
        raise ValueError("COMPLETE_RECEIPT_UNSTABLE")
    raw = base.canonical(result) + b"\n"
    path = root / "driver/complete.json"
    base.write(path, raw, raw=True)
    transport.upload(path, "results/complete.json", len(raw), budget.end)  # Completion always last.
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("config", "config-sha256", "permit", "permit-sha256", "root", "python"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--bootstrap-evidence")
    args = parser.parse_args(argv)
    require(sys.platform == "linux" and sys.flags.isolated and sys.dont_write_bytecode, "ISOLATED_LINUX_DRIVER")
    config_raw, permit_raw = raw_read(args.config), raw_read(args.permit)
    require(sha256(config_raw).hexdigest() == args.config_sha256 and sha256(permit_raw).hexdigest() == args.permit_sha256, "EXTERNAL_RAW_PINS")
    config = json.loads(config_raw)
    support = Path(__file__).resolve().parent
    base, _ = load_support(support, config["continuation"])
    result = execute(base.parse(config_raw), args.root, config_sha256=args.config_sha256, permit=base.parse(permit_raw),
        python=args.python, transport=base.S3CLI(config["bucket"]), support_dir=support, bootstrap_evidence=args.bootstrap_evidence)
    print(json.dumps({"status": result["status"], "artifact": result["artifact"], "resources": result["resources"]}))
    return 0 if result["status"] in ("COMPLETE", "TEACHING_INCOMPLETE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
