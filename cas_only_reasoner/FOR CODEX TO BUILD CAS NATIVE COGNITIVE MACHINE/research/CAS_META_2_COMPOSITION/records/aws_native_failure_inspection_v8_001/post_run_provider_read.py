"""One read-only post-run cleanup check for the new stored-database inspection.

The previous checker contributes only pure file helpers and its 13 getter
observations. Its main(), previous-job gate and paid launch paths are not used.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT.parents[1]
JOB = "cas-meta2-20260906162339-56837284"
ACCOUNT, REGION = "807562639912", "us-west-2"
INSTANCE, GROUP = "i-048a3cc3dfddf75e6", "sg-051a6cd8348206b21"
BUCKET = JOB + "-" + ACCOUNT
SOURCE_SHA = "37c591f3d6ae0606b27334c26d4392e0da94c675"
REQUEST_SHA = "33abe7173efd939e6821afe0d1b493a303f253c67e7f423857094a1f4d786e8e"
AUTHORITY_SHA = "1272a507f6f95daaabf41b42dc46343cd86cd21505f2635ad8296124ae69f7c4"
CAPTURE_SHA = "2a930c66cbe0574deaf0781f924df15681d273ba8a35609250fc24d94071b982"
MANIFEST_SHA = "a4b04cb0d97c4fa28883c3b210abf4632ea4b04b7c79d267b4efe0f18ea81fb1"
ARCHIVE_SHA = "39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f"
EXPERIMENT = {"profile": "native_failure_sqlite_inspection_v8", "entrypoint": "read_only_sqlite_export"}
HELPER_PATH = ROOT.parent / "aws_child_qualification_v8_001/post_run_provider_read.py"
HELPER_SHA = "b28b9d6f1d642b68f277a1dcec6a39ff64a3cc751b70caea9e08171ac02945a9"
PINNED = {
    "registration_001/launch_request.json": REQUEST_SHA,
    "registration_001/standing_authority.json": AUTHORITY_SHA,
    "registration_001/capture_parent.py": CAPTURE_SHA,
    "registration_001/registration_receipt.json": "88eab49f7641595ddee871e012802d4648525d85a966e25cc1e04bc8a12e0c62",
    "registration_001/parent_process_start.json": "134657eda0c935179d3ab73e0eefa4e50b27d7c17dac9b52fce852cfbd86bd73",
    "registration_001/parent_process_identity.json": "eb266a76c3001383b018e31908decd697d0fd94c4245a9b81e2e5a6de4335c3b",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def helper():
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (HELPER_PATH, *HELPER_PATH.parents)), "INSPECTION_CHECKER_HELPER_LINK")
    require(HELPER_PATH.is_file() and HELPER_PATH.stat().st_size <= 1024**2
            and sha256(HELPER_PATH.read_bytes()).hexdigest() == HELPER_SHA, "INSPECTION_CHECKER_HELPER_CHANGED")
    spec = importlib.util.spec_from_file_location("inspection_private_postrun_getters", HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # Its imports are standard-library only.
    for name, value in {"JOB": JOB, "ACCOUNT": ACCOUNT, "REGION": REGION,
                        "INSTANCE": INSTANCE, "GROUP": GROUP, "BUCKET": BUCKET}.items():
        setattr(module, name, value)
    return module


def load_gate(h):
    """Verify fixed local source, capture, outer launch, and inner transport bytes."""
    paths = [ROOT / name for name in PINNED]
    paths += [ROOT / "registration_001/parent_process_completion.json",
              ROOT / "execution_001/launch_receipt.json",
              ROOT / "execution_001/lifecycle/launch_request.json",
              ROOT / "execution_001/lifecycle/launch_receipt.json", HELPER_PATH]
    raw = {str(path): h.read(path) for path in paths}
    def value(name):
        return json.loads(raw[str(ROOT / name)])
    for name, expected in PINNED.items():
        require(sha256(raw[str(ROOT / name)]).hexdigest() == expected, "INSPECTION_POSTRUN_PIN_CHANGED:" + name)
    require(sha256(raw[str(HELPER_PATH)]).hexdigest() == HELPER_SHA, "INSPECTION_POSTRUN_HELPER_CHANGED")
    require(sha256(raw[str(ROOT / "execution_001/lifecycle/launch_request.json")]).hexdigest() == REQUEST_SHA,
            "INSPECTION_POSTRUN_LIFECYCLE_REQUEST_CHANGED")
    request = value("registration_001/launch_request.json")
    completion = value("registration_001/parent_process_completion.json")
    start = value("registration_001/parent_process_start.json")
    identity = value("registration_001/parent_process_identity.json")
    launch = value("execution_001/launch_receipt.json")
    inner = value("execution_001/lifecycle/launch_receipt.json")
    require(completion.get("schema") == "cas-meta2-native-inspection-parent-capture/8"
            and type(completion.get("exit_code")) is int and completion.get("process_created") is True
            and "capture_failure" not in completion and completion.get("capture_source_sha256") == CAPTURE_SHA
            and completion.get("request_sha256") == REQUEST_SHA and completion.get("authority_sha256") == AUTHORITY_SHA
            and type(completion.get("pid")) is int and completion["pid"] == identity.get("pid") == 71176
            and completion.get("command") == identity.get("command") == start.get("command")
            and all(completion.get(key) == entry for key, entry in start.items()), "INSPECTION_POSTRUN_PARENT_NOT_EXITED")
    command = completion["command"]
    require(command[1:5] == ["-B", "-m", "aws.launch_native_failure_inspection_v8", "--execute"]
            and command[command.index("--request-sha256") + 1] == REQUEST_SHA
            and command[command.index("--authority-sha256") + 1] == AUTHORITY_SHA,
            "INSPECTION_POSTRUN_CAPTURE_COMMAND_CHANGED")
    finished, begun = (datetime.fromisoformat(completion[key]) for key in ("finished_utc", "started_utc"))
    require(finished.tzinfo is not None and begun.tzinfo is not None
            and begun <= finished <= datetime.now(timezone.utc), "INSPECTION_POSTRUN_PARENT_TIME")
    require(launch.get("schema") == "cas-meta2-native-failure-inspection-launch-receipt/8"
            and inner.get("schema") == "cas-meta2-child-qualification-launch-receipt/8"
            and launch.get("transport_schema") == inner["schema"]
            and launch.get("transport_status") == inner.get("status")
            and launch.get("transport_receipt_sha256") == sha256(raw[str(ROOT / "execution_001/lifecycle/launch_receipt.json")]).hexdigest()
            and Path(launch["transport_receipt_path"]).resolve() == (ROOT / "execution_001/lifecycle/launch_receipt.json").resolve(),
            "INSPECTION_POSTRUN_TRANSPORT_BINDING")
    for record in (launch, inner):
        require(record.get("job") == request.get("job") == JOB and record.get("request_sha256") == REQUEST_SHA
                and record.get("source_sha") == record.get("parent_source_sha") == SOURCE_SHA
                and record.get("archive_sha256") == ARCHIVE_SHA and record.get("source_manifest_sha256") == MANIFEST_SHA
                and record.get("experiment") == EXPERIMENT and record.get("termination_confirmed") is True
                and any(event.get("event") == "INSTANCE_TERMINATION_CONFIRMED"
                        and event.get("instance_id") == INSTANCE for event in record.get("events", [])),
                "INSPECTION_POSTRUN_SOURCE_OR_TERMINATION_UNCONFIRMED")
    require(launch.get("resources") == inner.get("resources") and launch.get("result") == inner.get("result")
            and launch.get("events") == inner.get("events") and launch.get("training") is False
            and launch.get("native_execution") is False and launch.get("sqlite_read_only") is True
            and launch.get("source_postcheck") == {"ok": True}, "INSPECTION_POSTRUN_OUTER_SCOPE_CHANGED")
    resources = inner["resources"]
    require(resources.get("instance") == INSTANCE and resources.get("security_group") == GROUP
            and resources.get("bucket") == BUCKET and resources.get("instance_profile") == JOB + "-worker"
            and resources.get("schedule") == JOB, "INSPECTION_POSTRUN_RESOURCE_IDENTITY")
    for name, expected in request["parent_file_sha256"].items():
        require(name in ("aws/launch_native_failure_inspection_v8.py", "aws/native_failure_inspection_v8.py",
            "aws/launch_child_qualification_v8.py", "aws/launch_prefix_diagnostic_v8.py", "aws/prefix_remote_v8.py",
            "aws/launch_prototype_v7.py", "aws/budget.py", "tools/experiment_profiles_prototype_v7.py"),
            "INSPECTION_POSTRUN_SOURCE_NAME")
        path = SOURCE_ROOT / name
        raw[str(path)] = h.read(path)
        require(sha256(raw[str(path)]).hexdigest() == expected, "INSPECTION_POSTRUN_EXECUTABLE_SOURCE_CHANGED:" + name)
    require(set(completion.get("outputs", {})) == {"parent_stdout.txt", "parent_stderr.txt"},
            "INSPECTION_POSTRUN_CAPTURE_OUTPUTS_REQUIRED")
    for name, entry in completion["outputs"].items():
        path = ROOT / "registration_001" / name
        raw[str(path)] = h.read(path)
        require(len(raw[str(path)]) == entry["bytes"] and sha256(raw[str(path)]).hexdigest() == entry["sha256"],
                "INSPECTION_POSTRUN_CAPTURE_OUTPUT_CHANGED")
    return raw, launch, completion


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, default=ROOT / "provider_check_001")
    args = parser.parse_args(argv)
    h = helper()
    output = h.safe(args.output)
    require(output.parent == h.safe(ROOT) and re.fullmatch(r"provider_check_[0-9]{3}", output.name)
            and not output.exists(), "INSPECTION_POSTRUN_FRESH_OUTPUT_REQUIRED")
    raw, launch, completion = load_gate(h)  # Must pass BEFORE boto3 import or provider calls.
    script_raw = h.read(Path(__file__))
    output.mkdir()
    receipt = {"schema": "cas-meta2-native-failure-inspection-post-run-provider-read/8",
        "job": JOB, "account_id": ACCOUNT, "region": REGION, "source_sha": SOURCE_SHA, "parent_source_sha": SOURCE_SHA,
        "request_sha256": REQUEST_SHA, "source_archive_sha256": ARCHIVE_SHA, "source_manifest_sha256": MANIFEST_SHA,
        "resources": launch["resources"], "parent_exit_code": completion["exit_code"],
        "parent_finished_utc": completion["finished_utc"], "parent_launch_status": launch["status"],
        "parent_result": launch.get("result"), "started_utc": h.utc(), "command": [sys.executable, *sys.argv],
        "cwd": str(Path.cwd()), "python": sys.version, "script_sha256": sha256(script_raw).hexdigest(),
        "getter_helper_sha256": HELPER_SHA, "read_only": True, "automatic_retries": 0, "maximum_getter_calls": 13,
        "provider_calls_started": False, "checks": {}, "queries": [],
        "input_files": {name: {"bytes": len(value), "sha256": sha256(value).hexdigest()} for name, value in raw.items()}}
    try:
        import boto3
        from botocore.config import Config
        session = boto3.Session(profile_name="default", region_name=REGION)
        config = Config(connect_timeout=10, read_timeout=20, retries={"total_max_attempts": 1})
        clients = {name: session.client(name, config=config) for name in ("sts", "ec2", "iam", "scheduler", "s3")}
        receipt["provider_calls_started"] = True
        h.observe(clients, receipt, launch)
        require(len(receipt["queries"]) <= 13, "INSPECTION_POSTRUN_GETTER_LIMIT")
    except Exception as error:
        receipt.update(status="POST_RUN_READ_FAILED", error={"type": type(error).__name__, "message": str(error)})
    finally:
        try:
            unchanged = h.read(Path(__file__)) == script_raw and all(h.read(Path(name)) == value for name, value in raw.items())
        except Exception as error:
            unchanged = False
            receipt["local_evidence_postcheck_error"] = {"type": type(error).__name__, "message": str(error)}
        receipt["checks"]["local_evidence_unchanged"] = unchanged
        if not unchanged:
            receipt["status"] = "POST_RUN_CHECK_FAILED"
        receipt["finished_utc"] = h.utc()
        receipt["boundary"] = ("One read-only cleanup observation, not an invoice or database-export verification. "
            "The inner CHQ-named receipt is transport only. The bucket and results remain under the observed lifecycle. "
            "This check does not download or rehash object contents; matching archive size is not content identity. "
            "No launch, cleanup mutation, SQLite connection or model work.")
        destination = output / "receipt.json"
        with destination.open("xb") as stream:
            stream.write(h.encoded(receipt))
    print(json.dumps({"status": receipt["status"], "checks": receipt["checks"], "receipt": str(destination),
        "receipt_sha256": sha256(h.read(destination)).hexdigest()}))
    return 0 if receipt["status"] == "POST_RUN_CLEANUP_CONFIRMED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

