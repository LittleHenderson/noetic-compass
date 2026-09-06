"""Standalone AWS-only one-child qualification lifecycle; import and render are pure.

The parent must confirm independent termination before publishing the permit.
Only generic, byte-pinned prefix lifecycle helpers are embedded in the script.
No B/R experiment, prefix diagnostic, training coordinator, or provider launch is invoked here.
"""
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

HELPER_SHA256 = "e72f5937895d856797e9dae200100b279a39bdbe4850f67b5405a70cb9719f8b"
HELPERS = ("require", "canonical", "decode", "file_hash", "write_new", "safe_name",
           "instance_identity", "effective_deadline", "stage_process", "collect_artifacts",
           "emergency_artifacts")
REMOTE_ROOT = Path("/opt/cas-meta2-child-qualification")
PILOT = "research/CAS_META_2_COMPOSITION"
MANIFEST_NAME = "child_qualification_source_manifest.json"
EXPERIMENT = {"profile": "one_child_full_task_qualification_v8", "entrypoint": "cas_meta2.child_qualification_gpu_v8"}
COLLECTION_SECONDS = 240
BASE_SOURCE_SHA = "13f424981d7434b1a92815d1ad5759d543bbd3be"
BASE_ARCHIVE_SHA256 = "c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1"
BASE_MANIFEST_SHA256 = "10f3283e5dcb3045dac2131e021d3ca383c35ae8b34c9e439e7fc82ff58cdd9c"
BASELINE_MANIFEST_SHA256 = "476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0"
FIXED_SCOPE = {"max_seconds": 1800, "max_cost_usd": "4.00", "seed": 7,
    "task_count": 4, "candidates_per_task": 4, "planned_complete_executions": 20,
    "planned_native_ticks": 110, "binding": 0, "training": False,
    "native_execution": True, "max_output_bytes": 512 * 1024**2,
    "return_child_result": True, "automatic_retries": 0}
FIXED_PLAN = {"schema": "cas-meta2-child-qualification-plan/8",
              "launch_enabled": True, "experiment": EXPERIMENT, **FIXED_SCOPE}
LIFECYCLE_TEMPLATE_SHA256 = "c03b9f80466053ec3a05e1c3f851dd9d04a215029a16112cdd0e7fb8ae068940"
BR_SOURCE_SHA = "d047540a635ecccdd2cfd4d96ee3b43da59f7ce7"
BR_ARCHIVE_SHA256 = "1b13fbeb96465e2122b1709b87c99cdd06860f78a2bc4bbbfa4874e96ef7658a"
BR_PRESERVED_FILES = {
    "aws/br_package_v8.py": "23a30b7e4e3862702699e078bee953436be630f1390127f8668f519c1119b2e8",
    "cas_meta2/br_construction_v8.py": "96b9fcff510d74863ce720fcc2f0c1f6f730d7ce808e59ef59bbac660d108719",
    "cas_meta2/br_snapshot_v8.py": "fe11da6ae0399d58f22093c3a13e2b5faec481d75de260af818a7b98cd0ee5d0",
    "cas_meta2/br_witness_v8.py": "5cffd02a8653dcc8c1e90a2d571ce2c3a4ed4bbfb0b90093883130c808af7c5f",
    "cas_meta2/child_scaffold_v8.py": "4ca4f80dc173d3567cd7cb32a146299c4fc9b5b8e2db797a0d6612ac5aa1570b",
    "tests/test_br_construction_v8.py": "895188e7a43ed778fe1c9060435651798de512519d3b442ce0ddd561edb4738f",
    "tests/test_br_package_v8.py": "271f211b50de9d993a21a50b87702f16bdcf821f0f734919efcba3b225b306e0",
    "tests/test_br_snapshot_capture_v8.py": "be627866d9d38fd956f41b0cc2289c8c368d726abafd6fc4864f068aaf5f4d46",
    "tests/test_br_snapshot_v8.py": "7ecd15783de57b3ba2778e17275ef8db074f207a5487842f0109a6549409b133",
    "tests/test_br_witness_v8.py": "b7907a524f7d2ffb2b9f2a8cfb0450e32168b0cbe6796da5a40d8557198fc632",
    "tests/test_child_scaffold_v8.py": "ac69f4470ce20226899346fb71aafdfcc27f04f23a5072ebf46b1698591f3d08",
    "tools/check_br_snapshot_v8.py": "4801d72d5492b6e85bf810b16e86d4a3938286ae5cd0e63fad43efb6d5b1b2f7",
    "tools/check_child_call_preparation_v8.py": "7846c3ce82a4a65893b5989ae9b4cf386c386381a0a0c421ccb9c05c87c33db1",
}
NEW_ADDITIONS = (
    "cas_meta2/child_curriculum_v8.py", "cas_meta2/child_qualification_v8.py",
    "cas_meta2/child_qualification_gpu_v8.py", "tests/test_child_curriculum_v8.py",
    "tests/test_child_qualification_v8.py", "tests/test_child_qualification_gpu_v8.py",
    "aws/child_qualification_package_v8.py", "tests/test_child_qualification_package_v8.py",
    "tools/check_child_qualification_v8.py",
)
ADDITIONS = tuple(BR_PRESERVED_FILES) + NEW_ADDITIONS
SOURCE_MEMBER_COUNT = 639


def helper_source():
    path = Path(__file__).with_name("prefix_remote_v8.py")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != HELPER_SHA256:
        raise ValueError("CHQ_GENERIC_HELPER_SOURCE_CHANGED")
    source = raw.decode("utf-8")
    definitions = {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body
                   if isinstance(n, ast.FunctionDef) and n.name in HELPERS}
    if set(definitions) != set(HELPERS):
        raise ValueError("CHQ_GENERIC_HELPER_SET_CHANGED")
    return "\n\n".join(definitions[n] for n in HELPERS) + "\n"


if not globals().get("_CHQ_EMBEDDED_HELPERS", False):
    # Execute only these hash-checked function definitions, never the old main.
    exec(compile(helper_source(), "<pinned-generic-lifecycle-helpers>", "exec"), globals())


def strict_name(name):
    safe_name(name)
    require(not any(ord(c) < 32 for c in name)
            and all(not p.endswith((" ", ".")) for p in name.split("/")), "CHQ_UNSAFE_MEMBER_PATH")
    return name


def checked_names(names):
    names = [strict_name(n) for n in names]
    folded = {n.casefold() for n in names}
    require(len(names) == len(folded), "CHQ_MEMBER_COLLISION")
    require(not any("/".join(n.split("/")[:i]).casefold() in folded
                    for n in names for i in range(1, len(n.split("/")))), "CHQ_FILE_DIRECTORY_COLLISION")
    return names


def validate_config(config):
    fixed = {"schema": "cas-meta2-child-qualification-remote-config/8", "region": "us-west-2",
        "account_id": "807562639912", "max_worker_seconds": 1800,
        "artifact_bytes_max": 256 * 1024**2, "evidence_expanded_bytes_max": 512 * 1024**2}
    require(type(config) is dict and all(type(config.get(k)) is type(v) and config[k] == v
            for k, v in fixed.items()) and config.get("experiment") == EXPERIMENT,
            "CHQ_REMOTE_SCOPE_CHANGED")
    for name in ("worker_source_sha", "parent_source_sha"):
        require(type(config.get(name)) is str and re.fullmatch("[a-f0-9]{40}", config[name]), "CHQ_REMOTE_SOURCE_ID")
    for name in ("source_archive_sha256", "source_manifest_sha256"):
        require(type(config.get(name)) is str and re.fullmatch("[a-f0-9]{64}", config[name]), "CHQ_REMOTE_SHA256")
    require(type(config.get("job")) is str and re.fullmatch(r"cas-meta2-[0-9]{14}-[a-f0-9]{8}", config["job"])
            and config.get("bucket") == config["job"] + "-" + config["account_id"], "CHQ_REMOTE_JOB_IDENTITY")
    require(type(config.get("source_archive_bytes")) is int and 0 < config["source_archive_bytes"] <= 16 * 1024**2,
            "CHQ_REMOTE_ARCHIVE_SIZE")
    resource = config["resource_plan"]
    bounds = {"instance_type": "g7.2xlarge", "instance_count": 1, "runtime_seconds_max": 3600,
              "automatic_retries": 0, "ebs_gb": 75, "ebs_iops": 3000, "ebs_throughput_mib_per_second": 125}
    require(all(type(resource.get(k)) is type(v) and resource[k] == v for k, v in bounds.items()), "CHQ_REMOTE_RESOURCE_BOUND")
    manifest = config["source_manifest"]
    require(sha256(canonical(manifest)).hexdigest() == config["source_manifest_sha256"]
            and manifest.get("schema") == "cas-meta2-child-qualification-source-package/8"
            and manifest.get("source_sha") == config["worker_source_sha"]
            and manifest.get("root_manifest") == MANIFEST_NAME
            and manifest.get("experiment") == EXPERIMENT and manifest.get("old_br_launch_authorized") is False
            and all(manifest.get(n) is False for n in ("launch_enabled", "neural_execution", "native_execution", "training", "reservation_created")),
            "CHQ_REMOTE_SOURCE_MANIFEST")
    mapping, lengths = manifest["files_sha256"], manifest["files_bytes"]
    checked_names(mapping)
    require(set(mapping) == set(lengths) and MANIFEST_NAME not in mapping
            and len(mapping) == SOURCE_MEMBER_COUNT - 1
            and all(type(h) is str and re.fullmatch("[a-f0-9]{64}", h) for h in mapping.values())
            and all(type(n) is int and 0 <= n <= 128 * 1024**2 for n in lengths.values())
            and sum(lengths.values()) <= 128 * 1024**2, "CHQ_REMOTE_SOURCE_MAP")
    require(manifest.get("additions") == sorted(PILOT + "/" + n for n in ADDITIONS)
            and manifest.get("preserved_br") == {"source_sha": BR_SOURCE_SHA,
                "archive_sha256": BR_ARCHIVE_SHA256,
                "files_sha256": {PILOT + "/" + n: h for n, h in BR_PRESERVED_FILES.items()}}
            and all(mapping.get(PILOT + "/" + n) == h for n, h in BR_PRESERVED_FILES.items())
            and all(PILOT + "/" + n in mapping for n in NEW_ADDITIONS), "CHQ_REMOTE_PRESERVED_BR_CLOSURE")
    base = manifest["base"]
    require(base.get("source_sha") == BASE_SOURCE_SHA and base.get("archive_sha256") == BASE_ARCHIVE_SHA256
            and base.get("archive_bytes") == 7952045 and base.get("member_count") == 616
            and base.get("prefix_manifest_sha256") == BASE_MANIFEST_SHA256
            and base.get("accepted_baseline", {}).get("source_sha") == "0917267b1354e5d036263eaa6ba9a7197eafb776"
            and base["accepted_baseline"].get("manifest_sha256") == BASELINE_MANIFEST_SHA256
            and base["accepted_baseline"].get("file_count") == 316, "CHQ_REMOTE_BASE_IDENTITY")
    dist = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
    layout = {"pilot_dir": PILOT, "meta1_dir": "research/CAS_META_1_LEARNED_SELECTION",
        "meta_runtime_dir": "research/CASFORMER_v0_3_META_LOGIC_WIP", "dependency_lock": PILOT + "/requirements-gpu.txt",
        "wheel_paths": [dist + "casformer_reference-0.1.0-py3-none-any.whl", dist + "cas_neural_cjt-0.2.0-py3-none-any.whl"]}
    require(config["package_layout"] == layout == base["package_layout"], "CHQ_REMOTE_PACKAGE_LAYOUT")
    for name in [layout["dependency_lock"], *layout["wheel_paths"], PILOT + "/aws/child_qualification_package_v8.py",
                 PILOT + "/cas_meta2/child_qualification_gpu_v8.py"]:
        require(name in mapping, "CHQ_REMOTE_REQUIRED_SOURCE_MISSING")
    require(mapping.get("research/CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json") == BASELINE_MANIFEST_SHA256
            and mapping.get("prefix_source_manifest.json") == BASE_MANIFEST_SHA256,
            "CHQ_REMOTE_BASE_MANIFEST_BINDING")
    for name in layout["wheel_paths"]:
        require(base["wheels"].get(name) == {"sha256": mapping[name], "bytes": lengths[name]},
                "CHQ_REMOTE_WHEEL_BINDING")
    require(base.get("dependency_lock") == {"sha256": mapping[layout["dependency_lock"]],
                "bytes": lengths[layout["dependency_lock"]]}, "CHQ_REMOTE_LOCK_BINDING")
    return config


def render_remote(config):
    validate_config(config)
    # Helpers need only standard-library globals imported by the module below.
    return ("CONFIG = " + repr(config) + "\n_CHQ_EMBEDDED_HELPERS = True\n" + helper_source()
            + Path(__file__).read_text(encoding="utf-8"))


def user_data(config, remote_sha):
    validate_config(config)
    require(type(remote_sha) is str and re.fullmatch("[a-f0-9]{64}", remote_sha), "CHQ_REMOTE_SCRIPT_PIN")
    bucket = shlex.quote(config["bucket"])
    root = REMOTE_ROOT.as_posix()
    text = "\n".join(["#!/bin/bash", "set -eu", "umask 077",
        "export PYTHONDONTWRITEBYTECODE=1 AWS_MAX_ATTEMPTS=1 AWS_PAGER=''",
        "trap 'test ! -f " + root + "/bootstrap.log || { tail -c 1048576 " + root + "/bootstrap.log > " + root
        + "/bootstrap-tail.log; timeout 20 aws s3api put-object --bucket " + bucket
        + " --key results/bootstrap.log --body " + root + "/bootstrap-tail.log --region us-west-2 || true; }; shutdown -h now' EXIT",
        "export CAS_META2_GUEST_DEADLINE_EPOCH=$(( $(date +%s) + 3400 ))",
        "( sleep 3400; shutdown -h now ) >/dev/null 2>&1 &",
        "mkdir -p " + root, "exec > " + root + "/bootstrap.log 2>&1",
        "command -v aws >/dev/null || { echo AWS_CLI_REQUIRED; exit 1; }", "PY=''",
        "for p in python3.12 python3.11 /opt/conda/bin/python /opt/pytorch/bin/python /home/ubuntu/anaconda3/bin/python /home/ubuntu/miniconda3/bin/python python3; do",
        "  if command -v \"$p\" >/dev/null 2>&1 && \"$p\" -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,12)' 2>/dev/null; then PY=\"$p\"; break; fi", "done",
        "test -n \"$PY\" || { echo SUPPORTED_PYTHON_REQUIRED; exit 1; }",
        "timeout 90 aws s3api get-object --bucket " + bucket + " --key input/remote.py " + root + "/remote.py --region us-west-2",
        "echo '" + remote_sha + "  " + root + "/remote.py' | sha256sum -c -",
        "export CAS_META2_CHILD_QUALIFICATION_REMOTE=1 CAS_META2_AWS_JOB_ID=" + shlex.quote(config["job"]),
        '"$PY" -B ' + root + "/remote.py", ""])
    require(len(text.encode()) <= 16384, "CHQ_USER_DATA_BOUND")
    return text


def checked_permit(config, permit):
    require(type(permit) is dict and permit.get("job") == config["job"]
            and permit.get("archive_sha256") == config["source_archive_sha256"]
            and permit.get("cloud_deadline_confirmed") is True
            and type(permit.get("instance_id")) is str and re.fullmatch("i-[a-f0-9]{17}", permit["instance_id"]),
            "CHQ_CLOUD_PERMISSION_MISMATCH")
    deadline = datetime.fromisoformat(permit["deadline"])
    require(deadline.utcoffset() is not None and deadline.utcoffset().total_seconds() == 0
            and 0 < deadline.timestamp() - time.time() <= 3600, "CHQ_UTC_DEADLINE_BOUND")
    plan = permit["worker_plan"]
    require(sha256(canonical(plan)).hexdigest() == permit["worker_plan_sha256"], "CHQ_WORKER_PLAN_HASH")
    require(all(type(plan.get(k)) is type(v) and plan[k] == v for k, v in FIXED_PLAN.items())
            and plan.get("job") == config["job"] and plan.get("instance_id") == permit["instance_id"]
            and plan.get("source_sha") == config["worker_source_sha"]
            and plan.get("resource_plan") == config["resource_plan"], "CHQ_WORKER_PLAN_SCOPE")
    refs = {"source_manifest": (REMOTE_ROOT / "package" / MANIFEST_NAME, config["source_manifest_sha256"]),
        "source_archive": (REMOTE_ROOT / "source.zip", config["source_archive_sha256"]),
        "reservation_receipt": (REMOTE_ROOT / "launch/reservation_receipt.json", sha256(canonical(permit["reservation_receipt"])).hexdigest()),
        "ledger_snapshot": (REMOTE_ROOT / "launch/ledger_snapshot.json", sha256(canonical(permit["ledger_snapshot"])).hexdigest())}
    require(all(plan.get(k) == {"path": p.as_posix(), "sha256": h} for k, (p, h) in refs.items()), "CHQ_PLAN_PATH_OR_BYTES")
    return deadline.timestamp()


def extract_source(archive, output, config):
    require(file_hash(archive) == config["source_archive_sha256"]
            and archive.stat().st_size == config["source_archive_bytes"] and not output.exists(), "CHQ_SOURCE_ARCHIVE_OR_DESTINATION")
    manifest = config["source_manifest"]
    mapping = {**manifest["files_sha256"], MANIFEST_NAME: config["source_manifest_sha256"]}
    sizes = {**manifest["files_bytes"], MANIFEST_NAME: len(canonical(manifest))}
    with ZipFile(archive) as zipped:
        infos = zipped.infolist()
        names = checked_names([i.orig_filename for i in infos])
        require(set(names) == set(mapping) and all(i.orig_filename == i.filename
            and not i.is_dir() and stat.S_IFMT(i.external_attr >> 16) in (0, stat.S_IFREG)
            and not i.flag_bits & 1 and i.file_size == sizes[i.filename] for i in infos)
            and sum(i.file_size for i in infos) <= 128 * 1024**2, "CHQ_ARCHIVE_COVERAGE_SIZE_OR_TYPE")
        for i in infos:
            require(sha256(zipped.read(i)).hexdigest() == mapping[i.filename], "CHQ_ARCHIVE_MEMBER_CHANGED")
        output.mkdir(parents=True, exist_ok=False)
        for i in infos:
            path = output / i.filename
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(zipped.read(i))
    require(all(file_hash(output / n) == h for n, h in mapping.items()), "CHQ_EXTRACTED_BYTES_CHANGED")


def verify_package(config, archive, package):
    # This module is imported only after its exact bytes were checked above.
    path = package / PILOT / "aws/child_qualification_package_v8.py"
    require(file_hash(path) == config["source_manifest"]["files_sha256"][PILOT + "/aws/child_qualification_package_v8.py"], "CHQ_PACKAGE_CHECKER_CHANGED")
    spec = importlib.util.spec_from_file_location("child_qualification_package_v8_remote", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = module.inspect_archive(archive, expected_sha256=config["source_archive_sha256"],
        expected_source_sha=config["worker_source_sha"], expected_manifest_sha256=config["source_manifest_sha256"])
    require(manifest == config["source_manifest"], "CHQ_PACKAGE_MANIFEST_CHANGED")
    return module.verify_extracted(package, manifest, imported_paths=(path,))


def validate_result(output, config, permit):
    result = decode((output / "worker_receipt.json").read_bytes())
    require(result.get("schema") == "cas-meta2-child-qualification-gpu/8"
            and result.get("status") == "CHILD_CURRICULUM_NATIVE_QUALIFIED"
            and result.get("experiment") == EXPERIMENT
            and result.get("job") == config["job"] and result.get("source_sha") == config["worker_source_sha"]
            and result.get("source_archive_sha256") == config["source_archive_sha256"]
            and result.get("source_manifest_sha256") == config["source_manifest_sha256"]
            and result.get("plan_sha256") == permit["worker_plan_sha256"]
            and result.get("training") is False and result.get("native_execution") is True
            and result.get("cleanup_errors") == [] and result.get("failure") is None
            and all(result.get("postchecks", {}).get(n) == {"ok": True} for n in ("source", "reservation")),
            "CHQ_WORKER_COMPLETION_RECEIPT")
    qualification = result.get("qualification")
    fixed = {"status": "QUALIFIED", "qualified": True, "training": False,
        "evidence_kind": "AWS_NATIVE_CUDA_FROZEN_EXECUTOR",
        "scheduled_execution_count": 20, "scheduled_native_ticks": 110,
        "attempted_execution_count": 20, "reported_executed_count": 20,
        "completed_execution_count": 20, "audited_native_ticks": 110, "completed_native_ticks": 110,
        "all_scheduled_executions_completed": True, "unattempted_execution_count": 0,
        "failed_or_unaudited_attempts": 0}
    require(type(qualification) is dict and all(type(qualification.get(k)) is type(v)
            and qualification[k] == v for k, v in fixed.items())
            and qualification.get("failure") is None and qualification.get("receipt_saved") is not False,
            "CHQ_WORKER_QUALIFICATION_COUNTS")
    cases = qualification.get("cases")
    require(type(cases) is list and len(cases) == 4, "CHQ_WORKER_CASE_COVERAGE")
    for case in cases:
        require(case.get("status") == "QUALIFIED"
                and len(case.get("executions", [])) == 5
                and all(row.get("status") == "EXECUTED_AND_STORED_AUDITED" for row in case["executions"]),
                "CHQ_WORKER_CASE_NOT_FULLY_AUDITED")
        comparisons = case.get("comparisons")
        require(type(comparisons) is list and len(comparisons) == 4
                and sum(row.get("correct_target") is True for row in comparisons) == 1
                and all(type(row.get("correct_target")) is bool for row in comparisons),
                "CHQ_WORKER_COMPARISON_COVERAGE")
        for row in comparisons:
            require(row.get("task_correct") is row["correct_target"]
                    and row.get("final_output_differs_from_reference") is (not row["correct_target"]),
                    "CHQ_WORKER_TASK_OR_FINAL_BYTES_NOT_DISCRIMINATED")
    mapping = result["files_sha256"]
    checked_names(mapping)
    paths = [p for p in output.rglob("*") if p.is_file()]
    require({p.relative_to(output).as_posix() for p in paths} == set(mapping) | {"worker_receipt.json"},
            "CHQ_WORKER_FILE_COVERAGE")
    require(all(file_hash(output / n) == h for n, h in mapping.items()), "CHQ_WORKER_RESULT_BYTES_CHANGED")
    return result


def run_remote(config):
    validate_config(config)
    require(sys.platform == "linux" and (3, 11) <= sys.version_info[:2] <= (3, 12)
            and os.environ.get("CAS_META2_CHILD_QUALIFICATION_REMOTE") == "1"
            and os.environ.get("CAS_META2_AWS_JOB_ID") == config["job"], "CHQ_AWS_GUEST_REQUIRED")
    root = REMOTE_ROOT
    evidence = root / "evidence"
    evidence.mkdir(parents=True, exist_ok=False)
    archive, package = root / "source.zip", root / "package"
    output = package / PILOT / "runs/child_qualification"
    started = datetime.now(timezone.utc).isoformat()
    code, failure, permitted, package_verified = 1, None, False, False
    result = None
    transfer_count = 0
    env = {**{k: v for k, v in os.environ.items() if not k.startswith("CAS_META2_RUN_")}, "AWS_MAX_ATTEMPTS": "1", "AWS_PAGER": "", "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_NO_INPUT": "1", "CUBLAS_WORKSPACE_CONFIG": ":4096:8", "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "CUDA_VISIBLE_DEVICES": "0"}
    deadline = time.time() + 300

    def transfer(source, destination, seconds=60):
        nonlocal transfer_count
        transfer_count += 1
        require(transfer_count <= 36, "CHQ_TRANSFER_CALL_BOUND")
        source, destination = str(source), str(destination)
        prefix = "s3://" + config["bucket"] + "/"
        if source.startswith(prefix):
            argv = ["get-object", "--bucket", config["bucket"], "--key", strict_name(source[len(prefix):]), destination]
        else:
            require(destination.startswith(prefix), "CHQ_TRANSFER_BUCKET_MISMATCH")
            argv = ["put-object", "--bucket", config["bucket"], "--key", strict_name(destination[len(prefix):]), "--body", source]
        seconds = min(seconds, deadline - time.time() - 15) if permitted else seconds
        require(seconds > 0, "CHQ_TRANSFER_DEADLINE")
        command = ["aws", "s3api", *argv, "--region", "us-west-2", "--cli-connect-timeout", "5", "--cli-read-timeout", "15"]
        at = datetime.now(timezone.utc).isoformat()
        rc, error = None, None
        try:
            done = subprocess.run(command, check=True, timeout=seconds, env=env)
            rc = done.returncode
        except BaseException as caught:
            rc = getattr(caught, "returncode", None)
            error = {"type": type(caught).__name__, "message": str(caught)}
            raise
        finally:
            write_new(evidence / ("transfer_%02d.json" % transfer_count), {"argv": command,
                "started_utc": at, "finished_utc": datetime.now(timezone.utc).isoformat(),
                "maximum_seconds": seconds, "exit_code": rc, "failure": error})

    try:
        write_new(evidence / "remote_config.json", config)
        for _ in range(30):
            try:
                transfer("s3://" + config["bucket"] + "/input/permit.json", root / "permit.json", seconds=10)
                break
            except subprocess.CalledProcessError:
                require(time.time() < deadline, "CHQ_CLOUD_PERMISSION_TIMEOUT")
                time.sleep(3)
        else:
            raise ValueError("CHQ_CLOUD_PERMISSION_UNAVAILABLE")
        require((root / "permit.json").stat().st_size <= 4 * 1024**2, "CHQ_PERMIT_SIZE")
        permit = decode((root / "permit.json").read_bytes())
        cloud_deadline = checked_permit(config, permit)
        deadline = effective_deadline(cloud_deadline, env.get("CAS_META2_GUEST_DEADLINE_EPOCH"), time.time())
        permitted = True
        identity = instance_identity()
        require(identity.get("accountId") == config["account_id"] and identity.get("region") == config["region"]
                and identity.get("instanceId") == permit["instance_id"]
                and identity.get("instanceType") == "g7.2xlarge", "CHQ_LIVE_INSTANCE_MISMATCH")
        write_new(evidence / "instance_identity.json", identity)
        write_new(evidence / "permit.json", permit)
        write_new(evidence / "deadline_limits.json", {"cloud_deadline_epoch": cloud_deadline,
            "guest_deadline_epoch": int(env["CAS_META2_GUEST_DEADLINE_EPOCH"]), "effective_deadline_epoch": deadline,
            "worker_seconds": 1800, "collection_reserved_seconds": COLLECTION_SECONDS})
        for name in ("worker_plan", "reservation_receipt", "ledger_snapshot"):
            write_new(root / "launch" / (name + ".json"), permit[name])
        transfer("s3://" + config["bucket"] + "/input/source.zip", archive)
        extract_source(archive, package, config)
        write_new(evidence / "source_before.json", verify_package(config, archive, package))
        package_verified = True
        setup_deadline = deadline - 1800 - COLLECTION_SECONDS
        layout, py = config["package_layout"], root / "venv/bin/python"
        installs = [("venv", [sys.executable, "-m", "venv", str(root / "venv")]),
            ("torch_install", [str(py), "-m", "pip", "install", "--disable-pip-version-check", "torch==2.11.0",
                "--index-url", "https://download.pytorch.org/whl/cu128", "--report", str(evidence / "torch_install.json")]),
            ("dependency_install", [str(py), "-m", "pip", "install", "--disable-pip-version-check", "-r",
                str(package / layout["dependency_lock"]), "--report", str(evidence / "dependency_install.json")]),
            ("wheel_install", [str(py), "-m", "pip", "install", "--no-deps", *[str(package / n) for n in layout["wheel_paths"]],
                "--report", str(evidence / "wheel_install.json")]),
            ("pip_freeze", [str(py), "-m", "pip", "freeze", "--all"])]
        for name, argv in installs:
            stage_process(argv, evidence / name, env=env, cwd=root, seconds=900, deadline=setup_deadline, output_root=evidence)
        env["PYTHONPATH"] = ":".join(str(package / layout[k]) for k in ("pilot_dir", "meta1_dir", "meta_runtime_dir"))
        env["CAS_META2_RUN_CHILD_QUALIFICATION"] = "1"
        probe = ("import torch,json,sys; assert (3,11)<=sys.version_info[:2]<=(3,12); "
            "assert torch.__version__=='2.11.0+cu128' and torch.version.cuda=='12.8'; "
            "assert torch.cuda.is_available() and torch.cuda.device_count()==1; "
            "name=torch.cuda.get_device_name(0); assert 'RTX PRO 4500' in name.upper() and 'T4' not in name.upper(); "
            "print(json.dumps({'python':sys.version,'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':name,'gpu_count':torch.cuda.device_count()}))")
        stage_process([str(py), "-B", "-c", probe], evidence / "cuda_identity", env=env, cwd=root,
            seconds=60, deadline=setup_deadline, output_root=evidence)
        require(deadline - time.time() >= 1800 + COLLECTION_SECONDS, "CHQ_INSUFFICIENT_FULL_WORKER_WINDOW")
        require(not output.exists(), "CHQ_FRESH_WORKER_OUTPUT_REQUIRED")
        argv = [str(py), "-B", "-m", "cas_meta2.child_qualification_gpu_v8", "--output", str(output),
            "--job", config["job"], "--plan", str(root / "launch/worker_plan.json"),
            "--plan-sha256", permit["worker_plan_sha256"]]
        stage_process(argv, evidence / "worker", env=env, cwd=package / PILOT, seconds=1800,
            deadline=deadline - COLLECTION_SECONDS, output_root=package / PILOT / "runs")
        result = validate_result(output, config, permit)
        code = 0
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        if package_verified:
            try:
                write_new(evidence / "source_after.json", verify_package(config, archive, package))
            except BaseException as error:
                code = 1
                failure = {"earlier_failure": failure, "type": type(error).__name__, "message": str(error),
                           "stage": "SOURCE_POSTCHECK", "traceback": traceback.format_exc()}
        worker_receipt = evidence / "worker/receipt.json"
        process_record = None
        try:
            process_record = decode(worker_receipt.read_bytes()) if worker_receipt.is_file() else None
            require(process_record is None or type(process_record) is dict, "CHQ_PROCESS_RECEIPT_TYPE")
        except BaseException as error:
            code = 1
            failure = {"earlier_failure": failure, "type": type(error).__name__, "message": str(error),
                       "stage": "PROCESS_RECEIPT_READ"}
        record = {"schema": "cas-meta2-child-qualification-remote-receipt/8", "job": config["job"],
            "source_sha": config["worker_source_sha"], "parent_source_sha": config["parent_source_sha"],
            "archive_sha256": config["source_archive_sha256"], "source_manifest_sha256": config["source_manifest_sha256"],
            "generic_helper_sha256": HELPER_SHA256, "experiment": EXPERIMENT, "returncode": code, "failure": failure,
            "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(), "smoke_only": False,
            "neural_training": False, "native_execution_requested": True,
            "worker_process_started": bool(process_record and process_record.get("pid") is not None),
            "worker_qualification_completed": result is not None,
            "native_qualification_result": None if result is None else result["status"],
            "task_conditioned_correctness": None}
        write_new(evidence / "remote_receipt.json", record)
        target = root / "artifacts.zip"
        try:
            collected = collect_artifacts({"lifecycle": evidence, "qualification": output}, target, record,
                deadline=deadline - 150 if permitted else time.time() + 30)
        except BaseException as error:
            target = root / "failure_artifacts.zip"
            collected = emergency_artifacts(target, record, error)
        transfer(target, "s3://" + config["bucket"] + "/results/artifacts.zip", seconds=120)
        complete = {"job": config["job"], "source_sha": config["worker_source_sha"],
            "parent_source_sha": config["parent_source_sha"], "sha256": file_hash(target), "bytes": target.stat().st_size,
            "returncode": collected["returncode"], "experiment": EXPERIMENT, "smoke_only": False,
            "partial_evidence": collected["partial_evidence"], "omitted_full_file_count": collected["omitted_full_file_count"]}
        write_new(root / "complete.json", complete)
        transfer(root / "complete.json", "s3://" + config["bucket"] + "/results/complete.json", seconds=30)
    return collected["returncode"]


if __name__ == "__main__":
    require("CONFIG" in globals(), "CHQ_RENDERED_AWS_CONFIG_REQUIRED")
    raise SystemExit(run_remote(CONFIG))
