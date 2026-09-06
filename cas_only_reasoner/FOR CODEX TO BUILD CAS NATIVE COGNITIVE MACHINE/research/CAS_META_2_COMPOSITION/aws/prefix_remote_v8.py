"""Dedicated remote lifecycle for the frozen prefix diagnostic; no training.

Import and render are pure. Only an enabled, identity-checked AWS Linux guest
runs commands. The parent independently schedules termination before permission.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time
import traceback
from zipfile import ZipFile, ZIP_DEFLATED

REMOTE_ROOT = Path("/opt/cas-meta2-prefix")
SOURCE_SHA = "13f424981d7434b1a92815d1ad5759d543bbd3be"
SOURCE_ARCHIVE_SHA = "c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1"
DEVELOPMENT_ARCHIVE_SHA = "1874508d0baad7d6620001505c39f184b3cb091c59de4e96197f309beee0a042"
BUNDLE_SHA = "b4d7970ca59c07342942584e4752ad8c129c3125e25ecc241e3d76c9ddd1c629"
MANIFEST_SHA = "10f3283e5dcb3045dac2131e021d3ca383c35ae8b34c9e439e7fc82ff58cdd9c"
PILOT = "research/CAS_META_2_COMPOSITION"
EXPERIMENT = {"profile": "saved_prefix_diagnostic_v8", "entrypoint": "cas_meta2.diagnostic_v8.gpu"}
COLLECTION_SECONDS = 240


def require(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "PREFIX_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("PREFIX_NONFINITE_JSON")))
    canonical(value)
    return value


def file_hash(path):
    path = Path(path)
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), "PREFIX_REGULAR_FILE_REQUIRED")
    with path.open("rb") as stream:
        return __import__("hashlib").file_digest(stream, "sha256").hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def validate_config(config):
    fixed = {"schema": "cas-meta2-prefix-remote-config/8", "region": "us-west-2",
             "account_id": "807562639912", "worker_source_sha": SOURCE_SHA,
             "source_archive_sha256": SOURCE_ARCHIVE_SHA, "development_archive_sha256": DEVELOPMENT_ARCHIVE_SHA,
             "bundle_manifest_sha256": BUNDLE_SHA, "source_manifest_sha256": MANIFEST_SHA,
             "max_worker_seconds": 1800, "artifact_bytes_max": 256 * 1024**2,
             "evidence_expanded_bytes_max": 512 * 1024**2}
    require(type(config) is dict and all(type(config.get(k)) is type(v) and config[k] == v for k, v in fixed.items()),
            "PREFIX_REMOTE_CONFIG_CHANGED")
    require(re.fullmatch(r"cas-meta2-[0-9]{14}-[a-f0-9]{8}", config.get("job", ""))
            and re.fullmatch(r"[a-f0-9]{40}", config.get("parent_source_sha", ""))
            and config.get("bucket") == config["job"] + "-" + config["account_id"], "PREFIX_REMOTE_JOB_IDENTITY")
    resource = config["resource_plan"]
    require(resource.get("instance_type") == "g7.2xlarge" and resource.get("instance_count") == 1
            and resource.get("runtime_seconds_max") == 3600 and resource.get("automatic_retries") == 0,
            "PREFIX_REMOTE_RESOURCE_BOUND")
    manifest = config["source_manifest"]
    require(sha256(canonical(manifest)).hexdigest() == MANIFEST_SHA
            and manifest["source_sha"] == SOURCE_SHA and len(manifest["files_sha256"]) == 615,
            "PREFIX_REMOTE_SOURCE_MANIFEST")
    layout = config["package_layout"]
    require(layout.get("pilot_dir") == PILOT
            and layout.get("meta1_dir") == "research/CAS_META_1_LEARNED_SELECTION"
            and layout.get("meta_runtime_dir") == "research/CASFORMER_v0_3_META_LOGIC_WIP"
            and layout.get("dependency_lock") == PILOT + "/requirements-gpu.txt",
            "PREFIX_REMOTE_PACKAGE_LAYOUT")
    dist = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
    require(layout.get("wheel_paths") == [dist + "casformer_reference-0.1.0-py3-none-any.whl",
                                          dist + "cas_neural_cjt-0.2.0-py3-none-any.whl"], "PREFIX_REMOTE_WHEELS")
    return config


def render_remote(config):
    validate_config(config)
    return "CONFIG = " + repr(config) + "\n" + Path(__file__).read_text(encoding="utf-8")


def user_data(config, remote_sha):
    validate_config(config)
    require(type(remote_sha) is str and re.fullmatch("[a-f0-9]{64}", remote_sha), "PREFIX_REMOTE_SCRIPT_PIN")
    bucket = shlex.quote("s3://" + config["bucket"])
    text = "\n".join([
        "#!/bin/bash", "set -eu", "umask 077", "export PYTHONDONTWRITEBYTECODE=1 AWS_MAX_ATTEMPTS=1 AWS_PAGER=''",
        "trap 'test ! -f /opt/cas-meta2-prefix/bootstrap.log || { tail -c 1048576 /opt/cas-meta2-prefix/bootstrap.log > /opt/cas-meta2-prefix/bootstrap-tail.log; timeout 20 aws s3 cp /opt/cas-meta2-prefix/bootstrap-tail.log " + bucket + "/results/bootstrap.log --region us-west-2 || true; }; shutdown -h now' EXIT",
        "export CAS_META2_GUEST_DEADLINE_EPOCH=$(( $(date +%s) + 3400 ))",
        "( sleep 3400; shutdown -h now ) >/dev/null 2>&1 &",
        "mkdir -p /opt/cas-meta2-prefix", "exec > /opt/cas-meta2-prefix/bootstrap.log 2>&1",
        "command -v aws >/dev/null || { echo AWS_CLI_REQUIRED; exit 1; }", "PY=''",
        "for p in python3.12 python3.11 /opt/conda/bin/python /opt/pytorch/bin/python /home/ubuntu/anaconda3/bin/python /home/ubuntu/miniconda3/bin/python python3; do",
        "  if command -v \"$p\" >/dev/null 2>&1 && \"$p\" -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,12)' 2>/dev/null; then PY=\"$p\"; break; fi", "done",
        "test -n \"$PY\" || { echo SUPPORTED_PYTHON_REQUIRED; exit 1; }",
        "timeout 90 aws s3 cp " + bucket + "/input/remote.py /opt/cas-meta2-prefix/remote.py --region us-west-2",
        "echo '" + remote_sha + "  /opt/cas-meta2-prefix/remote.py' | sha256sum -c -",
        "export CAS_META2_PREFIX_REMOTE=1 CAS_META2_AWS_JOB_ID=" + shlex.quote(config["job"]),
        '"$PY" -B /opt/cas-meta2-prefix/remote.py', ""])
    require(len(text.encode()) <= 16384, "PREFIX_USER_DATA_BOUND")
    return text


def safe_name(name):
    require(type(name) is str and name and not name.startswith("/") and ":" not in name and "\\" not in name
            and all(p not in ("", ".", "..") for p in name.split("/")), "PREFIX_UNSAFE_ZIP_PATH")
    return name


def extract_checked(archive_path, output, expected_sha, mapping):
    require(file_hash(archive_path) == expected_sha and not output.exists(), "PREFIX_ARCHIVE_OR_NEW_DIRECTORY")
    with ZipFile(archive_path) as zipped:
        infos = zipped.infolist()
        names = [safe_name(i.filename) for i in infos]
        require(len(names) == len(set(names)) == len({n.casefold() for n in names}) == len(mapping)
                and set(names) == set(mapping), "PREFIX_ZIP_COVERAGE")
        require(sum(i.file_size for i in infos) <= 512 * 1024**2
                and all(not i.is_dir() and not stat.S_ISLNK(i.external_attr >> 16) and not i.flag_bits & 1 for i in infos),
                "PREFIX_ZIP_SIZE_OR_LINK")
        for name in names:
            require(sha256(zipped.read(name)).hexdigest() == mapping[name], "PREFIX_ZIP_MEMBER_CHANGED")
        output.mkdir(parents=True, exist_ok=False)
        for name in names:
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(zipped.read(name))
    require(all(file_hash(output / name) == expected for name, expected in mapping.items()), "PREFIX_EXTRACTED_BYTES_CHANGED")


def instance_identity():
    from urllib.request import Request, build_opener, ProxyHandler
    opener = build_opener(ProxyHandler({}))
    base = "http://169.254.169.254/latest/"
    with opener.open(Request(base + "api/token", method="PUT", headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"}), timeout=3) as response:
        token = response.read(1024).decode("ascii")
    with opener.open(Request(base + "dynamic/instance-identity/document", headers={"X-aws-ec2-metadata-token": token}), timeout=3) as response:
        raw = response.read(65537)
    require(len(raw) <= 65536, "PREFIX_IMDS_SIZE")
    return decode(raw)


def checked_permit(config, permit):
    require(permit.get("job") == config["job"] and permit.get("archive_sha256") == SOURCE_ARCHIVE_SHA
            and permit.get("cloud_deadline_confirmed") is True
            and re.fullmatch(r"i-[0-9a-f]{17}", permit.get("instance_id", "")), "PREFIX_CLOUD_PERMISSION_MISMATCH")
    deadline = datetime.fromisoformat(permit["deadline"])
    require(deadline.utcoffset() is not None and deadline.utcoffset().total_seconds() == 0,
            "PREFIX_UTC_DEADLINE_REQUIRED")
    require(0 < deadline.timestamp() - time.time() <= 3600, "PREFIX_EXPIRED_OR_EXTENDED_DEADLINE")
    plan = permit["worker_plan"]
    require(sha256(canonical(plan)).hexdigest() == permit["worker_plan_sha256"], "PREFIX_WORKER_PLAN_HASH")
    launch = REMOTE_ROOT / "launch"
    expected_refs = {"source_manifest": (REMOTE_ROOT / "package/prefix_source_manifest.json", MANIFEST_SHA),
                     "source_archive": (REMOTE_ROOT / "source.zip", SOURCE_ARCHIVE_SHA),
                     "reservation_receipt": (launch / "reservation_receipt.json", sha256(canonical(permit["reservation_receipt"])).hexdigest()),
                     "ledger_snapshot": (launch / "ledger_snapshot.json", sha256(canonical(permit["ledger_snapshot"])).hexdigest())}
    require(all(plan.get(key) == {"path": str(path), "sha256": digest} for key, (path, digest) in expected_refs.items()),
            "PREFIX_REMOTE_PLAN_PATH_OR_BYTES")
    require(plan.get("job") == config["job"] and plan.get("instance_id") == permit["instance_id"]
            and plan.get("source_sha") == SOURCE_SHA and plan.get("bundle_manifest_sha256") == BUNDLE_SHA
            and plan.get("max_seconds") == 1800 and plan.get("launch_enabled") is True
            and plan.get("resource_plan") == config["resource_plan"], "PREFIX_REMOTE_PLAN_SCOPE")
    return deadline.timestamp()


def effective_deadline(cloud_deadline, guest_epoch, now):
    require(type(guest_epoch) is str and re.fullmatch(r"[0-9]{10}", guest_epoch), "PREFIX_GUEST_DEADLINE_REQUIRED")
    guest = int(guest_epoch)
    require(0 < guest - now <= 3400 and 0 < cloud_deadline - now <= 3600, "PREFIX_GUEST_OR_CLOUD_DEADLINE_INVALID")
    return min(float(guest), cloud_deadline)


def stage_process(argv, directory, *, env, cwd, seconds, deadline, output_root):
    """Bound a process group and receipt failures even before child output exists."""
    directory.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    timeout = min(float(seconds), deadline - time.time())
    require(timeout > 0, "PREFIX_STAGE_DEADLINE")
    process = None
    failure = None
    code = None
    with (directory / "stdout.txt").open("xb") as stdout, (directory / "stderr.txt").open("xb") as stderr:
        try:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            while process.poll() is None:
                require(time.monotonic() - tick < timeout and time.time() < deadline, "PREFIX_STAGE_TIME_BOUND")
                monitored = {p for root in (output_root, directory) for p in root.rglob("*")
                             if p.is_file() and not p.is_symlink()}
                total = sum(p.stat().st_size for p in monitored)
                require(total <= 500 * 1024**2, "PREFIX_STAGE_ARTIFACT_BOUND")
                time.sleep(0.5)
            code = process.returncode
        except BaseException as error:
            failure = {"type": type(error).__name__, "message": str(error)}
        finally:
            if process is not None and (process.poll() is None or process.returncode != 0):
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
            if process is not None:
                code = process.returncode
    receipt = {"argv": argv, "cwd": str(cwd), "pid": process.pid if process else None,
               "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
               "wall_seconds": time.monotonic() - tick, "maximum_seconds": seconds,
               "deadline_epoch": deadline, "exit_code": code, "failure": failure,
               "outputs": {name: {"sha256": file_hash(directory / name), "bytes": (directory / name).stat().st_size}
                           for name in ("stdout.txt", "stderr.txt")}}
    write_new(directory / "receipt.json", receipt)
    require(code == 0 and failure is None, "PREFIX_CHILD_PROCESS_FAILED:" + directory.name)
    return receipt


def collect_artifacts(roots, destination, record, *, limit=254 * 1024**2, deadline=None):
    """Keep failure evidence and explicit omitted counts; never truncate originals."""
    files = {}
    unsafe = []
    def time_check():
        require(deadline is None or time.time() < deadline, "PREFIX_COLLECTION_TIME_BOUND")
    for prefix, root in roots.items():
        time_check()
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            time_check()
            name = safe_name(prefix + "/" + path.relative_to(root).as_posix())
            if path.is_symlink():
                unsafe.append(name)
            elif path.is_file():
                files[name] = path
    index = {}
    for name, path in files.items():
        time_check()
        index[name] = {"bytes": path.stat().st_size, "sha256": file_hash(path)}
    expanded = sum(item["bytes"] for item in index.values())
    partial = expanded > limit - 2 * 1024**2 or bool(unsafe)
    selected = {}
    used = 0
    for name, path in files.items():
        size = index[name]["bytes"]
        if not partial or (size <= 1024**2 and used + size <= limit - 2 * 1024**2):
            selected[name] = path
            used += size
    receipt = {**record, "partial_evidence": partial, "original_file_count": len(files),
               "included_full_file_count": len(selected), "omitted_full_file_count": len(files) - len(selected),
               "original_bytes": expanded, "files": index, "unsafe_paths": unsafe}
    if partial:
        receipt["returncode"] = 1
    with ZipFile(destination, "x", ZIP_DEFLATED) as zipped:
        for name, path in selected.items():
            time_check()
            zipped.write(path, name)
        if partial:
            for number, (name, path) in enumerate((n, p) for n, p in files.items() if p.name in ("stdout.txt", "stderr.txt")):
                if number >= 12:
                    break
                with path.open("rb") as stream:
                    stream.seek(max(0, path.stat().st_size - 16384))
                    zipped.writestr("failure_tails/" + str(number) + ".txt", stream.read(16384))
        zipped.writestr("artifact_collection_receipt.json", canonical(receipt))
    require(destination.stat().st_size <= limit, "PREFIX_COMPRESSED_ARTIFACT_LIMIT")
    return receipt


def emergency_artifacts(destination, record, error):
    """Last small failure receipt; it explicitly does not claim full collection."""
    receipt = {**record, "returncode": 1, "partial_evidence": True,
               "original_file_count": None, "included_full_file_count": 0,
               "omitted_full_file_count": None, "full_file_counts_known": False,
               "collection_failure": {"type": type(error).__name__, "message": str(error)}}
    with ZipFile(destination, "x", ZIP_DEFLATED) as zipped:
        zipped.writestr("artifact_collection_receipt.json", canonical(receipt))
    return receipt


def run_remote(config):
    validate_config(config)
    require(sys.platform == "linux" and (3, 11) <= sys.version_info[:2] <= (3, 12)
            and os.environ.get("CAS_META2_PREFIX_REMOTE") == "1"
            and os.environ.get("CAS_META2_AWS_JOB_ID") == config["job"], "PREFIX_AWS_GUEST_REQUIRED")
    root = REMOTE_ROOT
    evidence = root / "evidence"
    evidence.mkdir(parents=True, exist_ok=False)
    source_zip, dev_zip = root / "source.zip", root / "development.zip"
    package = root / "package"
    worker_output = package / PILOT / "runs/prefix_diagnostic"
    started = datetime.now(timezone.utc).isoformat()
    code = 1
    failure = None
    permitted = False
    env = {**os.environ, "AWS_MAX_ATTEMPTS": "1", "AWS_PAGER": "", "PYTHONDONTWRITEBYTECODE": "1",
           "CUBLAS_WORKSPACE_CONFIG": ":4096:8", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
           "OPENBLAS_NUM_THREADS": "1", "CUDA_VISIBLE_DEVICES": "0"}
    deadline = time.time() + 300
    def transfer(source, destination, seconds=60):
        source, destination = str(source), str(destination)
        prefix = "s3://" + config["bucket"] + "/"
        if source.startswith(prefix):
            key = safe_name(source[len(prefix):])
            argv = ["get-object", "--bucket", config["bucket"], "--key", key, destination]
        else:
            require(destination.startswith(prefix), "PREFIX_TRANSFER_BUCKET_MISMATCH")
            key = safe_name(destination[len(prefix):])
            argv = ["put-object", "--bucket", config["bucket"], "--key", key, "--body", source]
        if permitted:
            # Preserve a final log/shutdown margin even when a transfer stalls.
            seconds = min(seconds, deadline - time.time() - 15)
        require(seconds > 0, "PREFIX_TRANSFER_DEADLINE")
        # Every call is one object API, not a multipart transfer manager.
        # At most30 permit reads +2 archive reads +2 result writes; retries off.
        subprocess.run(["aws", "s3api", *argv, "--region", "us-west-2",
                        "--cli-connect-timeout", "5", "--cli-read-timeout", "15"],
                       check=True, timeout=seconds, env=env)
    try:
        permit_file = root / "permit.json"
        for attempt in range(30):
            try:
                transfer("s3://" + config["bucket"] + "/input/permit.json", permit_file, seconds=10)
                break
            except subprocess.CalledProcessError:
                require(time.time() < deadline, "PREFIX_CLOUD_PERMISSION_TIMEOUT")
                time.sleep(3)
        else:
            raise ValueError("PREFIX_CLOUD_PERMISSION_UNAVAILABLE")
        permit = decode(permit_file.read_bytes())
        cloud_deadline = checked_permit(config, permit)
        deadline = effective_deadline(cloud_deadline, os.environ.get("CAS_META2_GUEST_DEADLINE_EPOCH"), time.time())
        permitted = True
        identity = instance_identity()
        require(identity.get("accountId") == config["account_id"] and identity.get("region") == config["region"]
                and identity.get("instanceId") == permit["instance_id"]
                and identity.get("instanceType") == "g7.2xlarge", "PREFIX_LIVE_INSTANCE_MISMATCH")
        write_new(evidence / "instance_identity.json", identity)
        write_new(evidence / "deadline_limits.json", {"cloud_deadline_epoch": cloud_deadline,
            "guest_deadline_epoch": int(env["CAS_META2_GUEST_DEADLINE_EPOCH"]),
            "effective_deadline_epoch": deadline, "collection_reserved_seconds": COLLECTION_SECONDS})
        write_new(evidence / "remote_config.json", config)
        write_new(evidence / "permit.json", permit)
        write_new(root / "launch/worker_plan.json", permit["worker_plan"])
        write_new(root / "launch/reservation_receipt.json", permit["reservation_receipt"])
        write_new(root / "launch/ledger_snapshot.json", permit["ledger_snapshot"])
        transfer("s3://" + config["bucket"] + "/input/source.zip", source_zip)
        transfer("s3://" + config["bucket"] + "/input/development.zip", dev_zip)
        extract_checked(source_zip, package, SOURCE_ARCHIVE_SHA,
            {**config["source_manifest"]["files_sha256"], "prefix_source_manifest.json": MANIFEST_SHA})
        require(file_hash(dev_zip) == DEVELOPMENT_ARCHIVE_SHA, "PREFIX_DEVELOPMENT_ARCHIVE_CHANGED")
        with ZipFile(dev_zip) as zipped:
            manifest_raw = zipped.read("bundle_001/manifest.json")
            require(sha256(manifest_raw).hexdigest() == BUNDLE_SHA, "PREFIX_DEVELOPMENT_MANIFEST_CHANGED")
            data_manifest = decode(manifest_raw)
        extract_checked(dev_zip, root / "development", DEVELOPMENT_ARCHIVE_SHA,
            {**{"bundle_001/" + name: value["sha256"] for name, value in data_manifest["files"].items()},
             "bundle_001/manifest.json": BUNDLE_SHA})
        setup_deadline = deadline - 1800 - COLLECTION_SECONDS
        layout = config["package_layout"]
        py = root / "venv/bin/python"
        installs = [("venv", [sys.executable, "-m", "venv", str(root / "venv")]),
                    ("torch_install", [str(py), "-m", "pip", "install", "--disable-pip-version-check", "torch==2.11.0",
                                       "--index-url", "https://download.pytorch.org/whl/cu128", "--report", str(evidence / "torch_install.json")]),
                    ("dependency_install", [str(py), "-m", "pip", "install", "--disable-pip-version-check", "-r",
                                            str(package / layout["dependency_lock"]), "--report", str(evidence / "dependency_install.json")]),
                    ("wheel_install", [str(py), "-m", "pip", "install", "--no-deps", *[str(package / name) for name in layout["wheel_paths"]],
                                       "--report", str(evidence / "wheel_install.json")]),
                    ("pip_freeze", [str(py), "-m", "pip", "freeze", "--all"])]
        for name, argv in installs:
            stage_process(argv, evidence / name, env=env, cwd=root, seconds=900, deadline=setup_deadline, output_root=evidence)
        env["PYTHONPATH"] = ":".join(str(package / layout[name]) for name in ("pilot_dir", "meta1_dir", "meta_runtime_dir"))
        env["CAS_META2_RUN_PREFIX_DIAGNOSTIC"] = "1"
        probe = ("import torch,json,sys; assert (3,11)<=sys.version_info[:2]<=(3,12); "
                 "assert torch.__version__=='2.11.0+cu128' and torch.version.cuda=='12.8'; "
                 "assert torch.cuda.is_available() and torch.cuda.device_count()==1; "
                 "name=torch.cuda.get_device_name(0); assert 'RTX PRO 4500' in name.upper() and 'T4' not in name.upper(); "
                 "print(json.dumps({'python':sys.version,'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':name,'gpu_count':torch.cuda.device_count()}))")
        stage_process([str(py), "-B", "-c", probe], evidence / "cuda_identity", env=env, cwd=root,
                      seconds=60, deadline=setup_deadline, output_root=evidence)
        require(deadline - time.time() >= 1800 + COLLECTION_SECONDS, "PREFIX_INSUFFICIENT_FULL_WORKER_WINDOW")
        argv = [str(py), "-B", "-m", "cas_meta2.diagnostic_v8.gpu", "--bundle", str(root / "development/bundle_001"),
                "--output", str(worker_output), "--job", config["job"], "--manifest-sha256", BUNDLE_SHA,
                "--plan", str(root / "launch/worker_plan.json"), "--plan-sha256", permit["worker_plan_sha256"]]
        stage_process(argv, evidence / "worker", env=env, cwd=package / PILOT, seconds=1800,
                      deadline=deadline - COLLECTION_SECONDS, output_root=package / PILOT / "runs")
        result = decode((worker_output / "diagnostic_receipt.json").read_bytes())
        require(result.get("completed") is True and result.get("job") == config["job"]
                and result.get("source_sha") == SOURCE_SHA and result.get("plan_sha256") == permit["worker_plan_sha256"]
                and result.get("task_rows_completed") == 480 and result.get("scheduled_reference_opportunities") == 9088
                and result.get("neural_training") is False and result.get("native_execution") is False,
                "PREFIX_WORKER_COMPLETION_RECEIPT")
        for name, expected in result["files_sha256"].items():
            require("/" not in name and "\\" not in name and file_hash(worker_output / name) == expected,
                    "PREFIX_WORKER_RESULT_BYTES_CHANGED")
        require(len(result["files_sha256"]) == 480, "PREFIX_WORKER_RESULT_COVERAGE")
        code = 0
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        record = {"schema": "cas-meta2-prefix-remote-receipt/8", "job": config["job"],
                  "source_sha": SOURCE_SHA, "parent_source_sha": config["parent_source_sha"],
                  "archive_sha256": SOURCE_ARCHIVE_SHA, "development_archive_sha256": DEVELOPMENT_ARCHIVE_SHA,
                  "experiment": EXPERIMENT, "returncode": code, "failure": failure,
                  "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
                  "smoke_only": False, "neural_training": False, "native_execution": False}
        write_new(evidence / "remote_receipt.json", record)
        target = root / "artifacts.zip"
        try:
            collected = collect_artifacts({"lifecycle": evidence, "diagnostic": worker_output}, target, record,
                                          deadline=deadline - 150 if permitted else time.time() + 30)
        except BaseException as error:
            target = root / "failure_artifacts.zip"
            collected = emergency_artifacts(target, record, error)
        transfer(target, "s3://" + config["bucket"] + "/results/artifacts.zip", seconds=120)
        complete = {"job": config["job"], "source_sha": SOURCE_SHA, "parent_source_sha": config["parent_source_sha"],
                    "sha256": file_hash(target), "bytes": target.stat().st_size,
                    "returncode": collected["returncode"], "experiment": EXPERIMENT, "smoke_only": False,
                    "partial_evidence": collected["partial_evidence"], "omitted_full_file_count": collected["omitted_full_file_count"]}
        write_new(root / "complete.json", complete)
        transfer(root / "complete.json", "s3://" + config["bucket"] + "/results/complete.json", seconds=30)
    return collected["returncode"]


if __name__ == "__main__":
    require("CONFIG" in globals(), "PREFIX_RENDERED_AWS_CONFIG_REQUIRED")
    raise SystemExit(run_remote(CONFIG))
