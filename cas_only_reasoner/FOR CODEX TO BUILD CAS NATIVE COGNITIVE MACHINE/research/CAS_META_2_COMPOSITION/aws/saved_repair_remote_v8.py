"""AWS saved-native-repair transport. Import/render are pure; no prior worker runs."""
import ast
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import signal
import stat
import subprocess
import sys
import time
import traceback
from zipfile import ZipFile, ZIP_DEFLATED

REMOTE_ROOT = Path("/opt/cas-meta2-saved-repair")
PILOT = "research/CAS_META_2_COMPOSITION"
MANIFEST_NAME = "saved_repair_source_manifest.json"
EXPERIMENT = {"profile": "saved_native_repair_v8", "entrypoint": "cas_meta2.saved_repair_gpu_v8"}
PREFIX_SHA = "e72f5937895d856797e9dae200100b279a39bdbe4850f67b5405a70cb9719f8b"
CHQ_SHA = "fbecb2a6e06bde2052983a9073b72e2791b4ebff29c52909d7244c4366b6ab2d"
DATA_SHA = "39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f"
FIXED_SCOPE = {"max_seconds": 600, "max_cost_usd": "4.00", "seed": 7, "max_native_calls": 2, "max_policy_units": 16384,
    "training": False, "native_execution": True, "max_output_bytes": 536870912,
    "automatic_retries": 0, "outer_caller_restored": False}
FIXED_PLAN = {"schema": "cas-meta2-saved-repair-plan/8", "launch_enabled": True,
              "experiment": EXPERIMENT, **FIXED_SCOPE}


def helper_source():
    wanted = {
        "prefix_remote_v8.py": (PREFIX_SHA, ("require", "canonical", "decode", "file_hash", "write_new", "safe_name",
            "instance_identity", "effective_deadline", "stage_process", "collect_artifacts", "emergency_artifacts")),
        "child_qualification_remote_v8.py": (CHQ_SHA, ("strict_name", "checked_names", "extract_source")),
    }
    result = []
    for filename, (pin, names) in wanted.items():
        path = Path(__file__).with_name(filename)
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents)):
            raise ValueError("SAVED_REMOTE_HELPER_LINK")
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != pin:
            raise ValueError("SAVED_REMOTE_HELPER_CHANGED")
        source = raw.decode()
        definitions = {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body
                       if isinstance(n, ast.FunctionDef) and n.name in names}
        if set(definitions) != set(names):
            raise ValueError("SAVED_REMOTE_HELPER_DEFINITIONS")
        result.extend(definitions[n] for n in names)
    return "\n\n".join(result) + "\n"


if not globals().get("_SAVED_REPAIR_EMBEDDED", False):
    exec(compile(helper_source(), "<pinned-generic-transport-functions>", "exec"), globals())


def validate_config(config):
    fixed = {"schema": "cas-meta2-saved-repair-remote/8", "account_id": "807562639912",
        "region": "us-west-2", "max_worker_seconds": 600, "artifact_bytes_max": 268435456,
        "evidence_expanded_bytes_max": 536870912}
    require(type(config) is dict and all(type(config.get(k)) is type(v) and config[k] == v for k, v in fixed.items())
            and config.get("experiment") == EXPERIMENT, "SAVED_REMOTE_SCOPE")
    require(re.fullmatch(r"cas-meta2-[0-9]{14}-[a-f0-9]{8}", config.get("job", ""))
            and config.get("bucket") == config["job"] + "-807562639912", "SAVED_REMOTE_JOB")
    for key in ("parent_source_sha", "worker_source_sha"):
        require(re.fullmatch("[a-f0-9]{40}", config.get(key, "")), "SAVED_REMOTE_COMMIT")
    for key in ("source_archive_sha256", "source_manifest_sha256"):
        require(re.fullmatch("[a-f0-9]{64}", config.get(key, "")), "SAVED_REMOTE_DIGEST")
    require(type(config.get("source_archive_bytes")) is int and 0 < config["source_archive_bytes"] <= 16 * 1024**2,
            "SAVED_REMOTE_SOURCE_BOUND")
    resource = config["resource_plan"]
    fixed_resource = {"instance_type": "g7.2xlarge", "instance_count": 1, "runtime_seconds_max": 3600,
        "worker_seconds_max": 600, "automatic_retries": 0, "native_execution": True, "training": False,
        "per_launch_reserved_cap_usd": "4.00", "max_native_calls": 2, "max_policy_units": 16384,
        "outer_caller_restored": False}
    require(all(type(resource.get(k)) is type(v) and resource[k] == v for k, v in fixed_resource.items()), "SAVED_REMOTE_RESOURCE")
    manifest = config["source_manifest"]
    require(sha256(canonical(manifest)).hexdigest() == config["source_manifest_sha256"]
            and manifest.get("source_sha") == config["worker_source_sha"]
            and manifest.get("schema") == "cas-meta2-saved-repair-source-package/8"
            and manifest.get("root_manifest") == MANIFEST_NAME and manifest.get("experiment") == EXPERIMENT,
            "SAVED_REMOTE_MANIFEST")
    mapping, sizes = manifest["files_sha256"], manifest["files_bytes"]
    checked_names(mapping)
    require(set(mapping) == set(sizes) and len(mapping) == 643 and MANIFEST_NAME not in mapping
            and all(type(v) is str and re.fullmatch("[a-f0-9]{64}", v) for v in mapping.values())
            and all(type(v) is int and 0 <= v <= 128 * 1024**2 for v in sizes.values())
            and sum(sizes.values()) <= 128 * 1024**2, "SAVED_REMOTE_MAPPING")
    require(manifest.get("data") == {"path": "data/prior_failure.zip", "sha256": DATA_SHA, "bytes": 893323,
        "original_job": "cas-meta2-20260906155525-195f5ad8", "role": "inert_prior_failure_archive"}
        and mapping.get("data/prior_failure.zip") == DATA_SHA and sizes.get("data/prior_failure.zip") == 893323,
        "SAVED_REMOTE_DATA")
    require(manifest["base"]["archive_sha256"] == "d93a39f3a264c23f27ac7dcdd2779eca665150a6bd739820651e953958e8f7d3"
            and manifest["base"]["manifest_sha256"] == "a19590941a53a7c3aa0a343501a7330ea5f89e56f10454ad82603eb4c6d0b69d"
            and manifest["base"]["member_count"] == 639 and config["package_layout"] == manifest["base"]["package_layout"],
            "SAVED_REMOTE_PRESERVED_BASE")
    return config


def render_remote(config):
    validate_config(config)
    return ("CONFIG = " + repr(config) + "\n_SAVED_REPAIR_EMBEDDED = True\n" + helper_source()
            + Path(__file__).read_text(encoding="utf-8"))


def user_data(config, remote_sha):
    validate_config(config)
    # Reuse only the reviewed bootstrap formatter in a private pure module.
    path = Path(__file__).with_name("child_qualification_remote_v8.py")
    require(sha256(path.read_bytes()).hexdigest() == CHQ_SHA, "SAVED_BOOTSTRAP_TEMPLATE_CHANGED")
    spec = importlib.util.spec_from_file_location("saved_repair_private_bootstrap", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_config, module.REMOTE_ROOT = validate_config, REMOTE_ROOT
    text = module.user_data(config, remote_sha)
    require(text.count("CAS_META2_CHILD_QUALIFICATION_REMOTE") == 1, "SAVED_BOOTSTRAP_ENABLE_TOKEN")
    return text.replace("CAS_META2_CHILD_QUALIFICATION_REMOTE", "CAS_META2_SAVED_REPAIR_REMOTE")


def checked_permit(config, permit):
    require(permit.get("job") == config["job"] and permit.get("archive_sha256") == config["source_archive_sha256"]
            and permit.get("cloud_deadline_confirmed") is True and re.fullmatch("i-[a-f0-9]{17}", permit.get("instance_id", "")),
            "SAVED_PERMIT_IDENTITY")
    deadline = datetime.fromisoformat(permit["deadline"])
    require(deadline.utcoffset() is not None and deadline.utcoffset().total_seconds() == 0
            and 0 < deadline.timestamp() - time.time() <= 3600, "SAVED_PERMIT_DEADLINE")
    plan = permit["worker_plan"]
    require(sha256(canonical(plan)).hexdigest() == permit["worker_plan_sha256"]
            and all(type(plan.get(k)) is type(v) and plan[k] == v for k, v in FIXED_PLAN.items())
            and plan.get("job") == config["job"] and plan.get("instance_id") == permit["instance_id"]
            and plan.get("source_sha") == config["worker_source_sha"]
            and plan.get("resource_plan") == config["resource_plan"], "SAVED_PERMIT_PLAN")
    refs = {"source_manifest": (REMOTE_ROOT / "package" / MANIFEST_NAME, config["source_manifest_sha256"]),
        "source_archive": (REMOTE_ROOT / "source.zip", config["source_archive_sha256"]),
        "evidence_archive": (REMOTE_ROOT / "package/data/prior_failure.zip", DATA_SHA),
        "reservation_receipt": (REMOTE_ROOT / "launch/reservation_receipt.json", sha256(canonical(permit["reservation_receipt"])).hexdigest()),
        "ledger_snapshot": (REMOTE_ROOT / "launch/ledger_snapshot.json", sha256(canonical(permit["ledger_snapshot"])).hexdigest())}
    require(all(plan.get(k) == {"path": p.as_posix(), "sha256": digest} for k, (p, digest) in refs.items()), "SAVED_PERMIT_PATHS")
    return deadline.timestamp()


def verify_package(config, archive, package):
    path = package / PILOT / "aws/saved_repair_package_v8.py"
    require(file_hash(path) == config["source_manifest"]["files_sha256"][PILOT + "/aws/saved_repair_package_v8.py"],
            "SAVED_PACKAGE_CHECKER_CHANGED")
    spec = importlib.util.spec_from_file_location("saved_repair_remote_package_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = module.inspect_archive(archive, expected_sha256=config["source_archive_sha256"],
        expected_source_sha=config["worker_source_sha"], expected_manifest_sha256=config["source_manifest_sha256"])
    require(manifest == config["source_manifest"], "SAVED_PACKAGE_MANIFEST_CHANGED")
    return module.verify_extracted(package, manifest, imported_paths=(path,))


def validate_result(output, config, permit):
    result = decode((output / "worker_receipt.json").read_bytes())
    require(result.get("schema") == "cas-meta2-saved-repair-gpu/8" and result.get("status") == "SAVED_NATIVE_REPAIR_SUCCEEDED"
            and result.get("job") == config["job"] and result.get("source_sha") == config["worker_source_sha"]
            and result.get("source_archive_sha256") == config["source_archive_sha256"]
            and result.get("source_manifest_sha256") == config["source_manifest_sha256"]
            and result.get("plan_sha256") == permit["worker_plan_sha256"] and result.get("training") is False
            and result.get("native_execution") is True and result.get("outer_caller_restored") is False
            and result.get("cleanup_errors") == [] and result.get("failure") is None
            and all(result.get("postchecks", {}).get(k) == {"ok": True} for k in
                ("source", "reservation", "accepted_sources", "original_database", "output_bound", "deadline")),
            "SAVED_WORKER_SUCCESS_IDENTITY")
    repair = result.get("repair", {})
    require(repair.get("status") == "REPAIR_RESUMED" and repair.get("repaired") is True
            and repair.get("training") is False
            and all(type(repair.get(k)) is int and repair[k] == 2 for k in
                ("native_call_attempts", "returned_native_calls", "completed_new_ticks", "accepted_new_ticks"))
            and type(repair.get("attempted_policy_units")) is int and 0 < repair["attempted_policy_units"] <= 16384,
            "SAVED_WORKER_REPAIR_RECEIPT")
    mapping = result["files_sha256"]
    checked_names(mapping)
    paths = [p for p in output.rglob("*") if p.is_file()]
    require({p.relative_to(output).as_posix() for p in paths} == set(mapping) | {"worker_receipt.json"}
            and all(file_hash(output / n) == digest for n, digest in mapping.items()), "SAVED_WORKER_OUTPUT_CHANGED")
    require("repair/repair_receipt.json" in mapping
            and decode((output / "repair/repair_receipt.json").read_bytes()) == repair, "SAVED_CORE_RECEIPT_COPY")
    return result


def run_remote(config):
    validate_config(config)
    require(sys.platform == "linux" and (3, 11) <= sys.version_info[:2] <= (3, 12)
            and os.environ.get("CAS_META2_SAVED_REPAIR_REMOTE") == "1"
            and os.environ.get("CAS_META2_AWS_JOB_ID") == config["job"], "SAVED_AWS_GUEST_REQUIRED")
    root, evidence = REMOTE_ROOT, REMOTE_ROOT / "evidence"
    evidence.mkdir(parents=True, exist_ok=False)
    archive, package = root / "source.zip", root / "package"
    output = package / PILOT / "runs/saved_repair"
    env = {**{k: v for k, v in os.environ.items() if not k.startswith("CAS_META2_RUN_")},
        "AWS_MAX_ATTEMPTS": "1", "AWS_PAGER": "", "PYTHONDONTWRITEBYTECODE": "1", "PIP_NO_INPUT": "1",
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "CUDA_VISIBLE_DEVICES": "0"}
    started, deadline, verified, permitted = datetime.now(timezone.utc).isoformat(), time.time() + 300, False, False
    result, failure, code, transfers = None, None, 1, 0
    def transfer(operation, key, path, seconds=60):
        nonlocal transfers
        transfers += 1
        require(transfers <= 30, "SAVED_TRANSFER_COUNT")
        argv = ["aws", "s3api", operation, "--bucket", config["bucket"], "--key", key, "--region", "us-west-2"]
        argv += ["--body", str(path)] if operation == "put-object" else [str(path)]
        return subprocess.run(argv, check=True, timeout=seconds, env=env, capture_output=True)
    try:
        permit_path = root / "permit.json"
        until = time.monotonic() + 120
        while True:
            try:
                transfer("get-object", "input/permit.json", permit_path, 10)
                break
            except subprocess.CalledProcessError:
                require(time.monotonic() < until, "SAVED_PERMIT_WAIT")
                time.sleep(5)
        require(permit_path.stat().st_size <= 1024**2, "SAVED_PERMIT_SIZE")
        permit = decode(permit_path.read_bytes())
        cloud_deadline = checked_permit(config, permit)
        actual = instance_identity()
        require(actual.get("instanceId") == permit["instance_id"] and actual.get("accountId") == config["account_id"]
                and actual.get("region") == "us-west-2" and actual.get("instanceType") == "g7.2xlarge", "SAVED_INSTANCE_IDENTITY")
        deadline = effective_deadline(cloud_deadline, os.environ.get("CAS_META2_GUEST_DEADLINE_EPOCH"), time.time())
        permitted = True
        launch = root / "launch"
        launch.mkdir()
        for name in ("worker_plan", "reservation_receipt", "ledger_snapshot"):
            write_new(launch / (name + ".json"), permit[name])
        write_new(evidence / "admission.json", {"identity": actual, "permit": permit, "deadline": deadline})
        transfer("get-object", "input/source.zip", archive, 90)
        extract_source(archive, package, config)
        write_new(evidence / "source_before.json", verify_package(config, archive, package))
        verified = True
        layout, py = config["package_layout"], root / "venv/bin/python"
        setup_deadline = deadline - 600 - 240
        stages = [
            ("venv", [sys.executable, "-m", "venv", str(root / "venv")]),
            ("torch_install", [str(py), "-m", "pip", "install", "--disable-pip-version-check", "torch==2.11.0",
                "--index-url", "https://download.pytorch.org/whl/cu128", "--report", str(evidence / "torch_install.json")]),
            ("dependency_install", [str(py), "-m", "pip", "install", "--disable-pip-version-check", "-r",
                str(package / layout["dependency_lock"]), "--report", str(evidence / "dependency_install.json")]),
            ("wheel_install", [str(py), "-m", "pip", "install", "--no-deps", *[str(package / n) for n in layout["wheel_paths"]],
                "--report", str(evidence / "wheel_install.json")]),
            ("pip_freeze", [str(py), "-m", "pip", "freeze", "--all"])]
        for name, argv in stages:
            stage_process(argv, evidence / name, env=env, cwd=root, seconds=900, deadline=setup_deadline, output_root=evidence)
        env["PYTHONPATH"] = ":".join(str(package / layout[k]) for k in ("pilot_dir", "meta1_dir", "meta_runtime_dir"))
        env["CAS_META2_RUN_SAVED_REPAIR"] = "1"
        probe = ("import torch; assert torch.__version__=='2.11.0+cu128' and torch.version.cuda=='12.8'; "
            "assert torch.cuda.is_available() and torch.cuda.device_count()==1; "
            "n=torch.cuda.get_device_name(0).upper(); assert 'RTX PRO 4500' in n and 'T4' not in n; print(n)")
        stage_process([str(py), "-B", "-c", probe], evidence / "cuda_identity", env=env, cwd=root, seconds=60,
                      deadline=setup_deadline, output_root=evidence)
        require(deadline - time.time() >= 840 and not output.exists(), "SAVED_FULL_WORKER_WINDOW")
        stage_process([str(py), "-B", "-m", EXPERIMENT["entrypoint"], "--output", str(output),
            "--job", config["job"], "--plan", str(launch / "worker_plan.json"), "--plan-sha256", permit["worker_plan_sha256"]],
            evidence / "worker", env=env, cwd=package / PILOT, seconds=600, deadline=deadline - 240,
            output_root=package / PILOT / "runs")
        result = validate_result(output, config, permit)
        code = 0
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        if verified:
            try:
                write_new(evidence / "source_after.json", verify_package(config, archive, package))
            except BaseException as error:
                code, failure = 1, {"earlier_failure": failure, "stage": "SOURCE_POSTCHECK",
                                    "type": type(error).__name__, "message": str(error)}
        record = {"schema": "cas-meta2-saved-repair-remote-receipt/8", "job": config["job"],
            "source_sha": config["worker_source_sha"], "parent_source_sha": config["parent_source_sha"],
            "experiment": EXPERIMENT, "returncode": code, "failure": failure, "started_utc": started,
            "finished_utc": datetime.now(timezone.utc).isoformat(), "training": False, "native_execution_requested": True,
            "outer_caller_restored": False, "worker_repair_completed": result is not None}
        write_new(evidence / "remote_receipt.json", record)
        target = root / "artifacts.zip"
        try:
            collection = collect_artifacts({"lifecycle": evidence, "repair": output}, target, record,
                deadline=deadline - 150 if permitted else time.time() + 30)
        except BaseException as error:
            target = root / "failure_artifacts.zip"
            collection = emergency_artifacts(target, record, error)
        transfer("put-object", "results/artifacts.zip", target, 120)
        complete = {k: collection[k] for k in ("job", "source_sha", "parent_source_sha", "experiment",
            "returncode", "partial_evidence", "omitted_full_file_count")}
        complete.update(bytes=target.stat().st_size, sha256=file_hash(target))
        write_new(root / "complete.json", complete)
        transfer("put-object", "results/complete.json", root / "complete.json", 30)
    return code


if __name__ == "__main__":
    require("CONFIG" in globals(), "SAVED_RENDERED_CONFIG_REQUIRED")
    raise SystemExit(run_remote(CONFIG))
