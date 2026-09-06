"""Read-only cleanup check for the registered saved-state repair job."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
M2 = ROOT.parents[1]
JOB = "cas-meta2-20260906165606-cbc41523"
INSTANCE = "i-0a8f1b0d591cf9da1"
GROUP = "sg-0a417046758a68747"
SOURCE = "e85d224842c50b2be202c8a15181df0526fa26cc"
ARCHIVE = "c965a1dabb584f49a6d549129121de61de921658adbcb7cb57ced807d89f9b3d"
MANIFEST = "6a08b2e500a85f9ca4f8d886434e4b5da330d6ff3e291f5aba6f0f9c4914d75d"
REQUEST = "925629d418561f38453cb9fe9dce7c9fdd9e1035775e9cc0a1ba784ab81f10a9"
AUTHORITY = "e112b25fdda5556dfcb1ea6a5401145a20ee61436865586257fa38882b571919"
CAPTURE = "c26ad4553f9408c8e6d31f0fb107bb233b25b7f2eef278cd42bbc0b5b8196742"
HELPER = ROOT.parent / "aws_child_qualification_v8_001/post_run_provider_read.py"
HELPER_SHA = "b28b9d6f1d642b68f277a1dcec6a39ff64a3cc751b70caea9e08171ac02945a9"
PINS = {
    "registration_001/launch_request.json": REQUEST,
    "registration_001/standing_authority.json": AUTHORITY,
    "registration_001/capture_parent.py": CAPTURE,
    "registration_001/registration_receipt.json": "e61afa66c8d556389f97ffe8d8d7dcff837ade34f49ad699a9b02e81beb442c4",
    "registration_001/parent_process_start.json": "3e8f0993d6df2e988790098a67ce2abee16bb7bdce50d4943f503d7249a8e920",
    "registration_001/parent_process_identity.json": "2f1dcba8bbb828a7526551c1dd3c341577270e870b152336f7047ce306cd212a",
}
EXPERIMENT = {"profile": "saved_native_repair_v8", "entrypoint": "cas_meta2.saved_repair_gpu_v8"}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def helper():
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
        for p in (HELPER, *HELPER.parents)), "HELPER_LINK")
    require(HELPER.stat().st_size < 1024**2 and sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA,
        "GETTER_HELPER_CHANGED")
    spec = importlib.util.spec_from_file_location("saved_repair_private_getters", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, value in {"JOB": JOB, "INSTANCE": INSTANCE, "GROUP": GROUP,
        "BUCKET": JOB + "-807562639912"}.items():
        setattr(module, name, value)
    return module


def gate(h):
    names = [*PINS, "registration_001/parent_process_completion.json",
        "execution_001/launch_receipt.json", "execution_001/lifecycle/launch_receipt.json",
        "execution_001/lifecycle/launch_request.json"]
    raw = {str(ROOT / name): h.read(ROOT / name) for name in names}
    def value(name):
        return json.loads(raw[str(ROOT / name)])
    for name, pin in PINS.items():
        require(sha256(raw[str(ROOT / name)]).hexdigest() == pin, "PIN_CHANGED:" + name)
    require(sha256(raw[str(ROOT / "execution_001/lifecycle/launch_request.json")]).hexdigest() == REQUEST,
        "TRANSPORT_REQUEST_CHANGED")
    start = value("registration_001/parent_process_start.json")
    process = value("registration_001/parent_process_identity.json")
    completed = value("registration_001/parent_process_completion.json")
    require(completed.get("schema") == "cas-meta2-saved-repair-parent-capture/8"
        and type(completed.get("exit_code")) is int and completed.get("process_created") is True
        and "capture_failure" not in completed and completed.get("capture_source_sha256") == CAPTURE
        and completed.get("request_sha256") == REQUEST and completed.get("authority_sha256") == AUTHORITY
        and completed.get("pid") == process.get("pid") == 55504
        and completed.get("command") == process.get("command") == start.get("command")
        and all(completed.get(k) == v for k, v in start.items()), "PARENT_COMPLETION_NOT_CONFIRMED")
    begun, finished = (datetime.fromisoformat(completed[k]) for k in ("started_utc", "finished_utc"))
    require(begun.tzinfo and finished.tzinfo and begun <= finished <= datetime.now(timezone.utc), "PARENT_TIME")
    outer = value("execution_001/launch_receipt.json")
    inner = value("execution_001/lifecycle/launch_receipt.json")
    require(outer.get("schema") == "cas-meta2-saved-repair-launch-receipt/8"
        and inner.get("schema") == "cas-meta2-child-qualification-launch-receipt/8"
        and outer.get("transport_status") == inner.get("status")
        and outer.get("transport_receipt_sha256") == sha256(raw[str(ROOT / "execution_001/lifecycle/launch_receipt.json")]).hexdigest()
        and outer.get("source_postcheck") == {"ok": True}, "OUTER_TRANSPORT_BINDING")
    for record in (outer, inner):
        require(record.get("job") == JOB and record.get("request_sha256") == REQUEST
            and record.get("source_sha") == record.get("parent_source_sha") == SOURCE
            and record.get("archive_sha256") == ARCHIVE and record.get("source_manifest_sha256") == MANIFEST
            and record.get("experiment") == EXPERIMENT and record.get("termination_confirmed") is True
            and any(e.get("event") == "INSTANCE_TERMINATION_CONFIRMED" and e.get("instance_id") == INSTANCE
                for e in record.get("events", [])), "SOURCE_OR_TERMINATION_NOT_CONFIRMED")
    require(outer.get("resources") == inner.get("resources") and outer.get("events") == inner.get("events")
        and outer.get("result") == inner.get("result") and outer.get("training") is False
        and outer.get("outer_caller_restored") is False, "OUTER_SCOPE_CHANGED")
    resources = inner["resources"]
    require(resources.get("instance") == INSTANCE and resources.get("security_group") == GROUP
        and resources.get("bucket") == JOB + "-807562639912"
        and resources.get("instance_profile") == JOB + "-worker" and resources.get("schedule") == JOB,
        "RESOURCE_IDENTITY_CHANGED")
    sys.path.insert(0, str(M2))
    from aws import launch_saved_repair_v8 as launcher
    request = value("registration_001/launch_request.json")
    require(launcher.verify_parent_source(SOURCE) == request["parent_file_sha256"], "EXECUTABLE_SOURCE_CHANGED")
    for name in request["parent_file_sha256"]:
        raw[str(M2 / name)] = h.read(M2 / name)
    require(set(completed.get("outputs", {})) == {"parent_stdout.txt", "parent_stderr.txt"}, "CAPTURE_OUTPUTS")
    for name, item in completed["outputs"].items():
        path = ROOT / "registration_001" / name
        data = h.read(path)
        require(len(data) == item["bytes"] and sha256(data).hexdigest() == item["sha256"], "CAPTURE_OUTPUT_CHANGED")
        raw[str(path)] = data
    raw[str(HELPER)] = h.read(HELPER)
    return raw, outer, completed


def main():
    h = helper()
    output = h.safe(ROOT / "provider_check_001")
    require(not output.exists(), "NEW_PROVIDER_RECEIPT_REQUIRED")
    raw, launch, completed = gate(h)  # No provider access until actual parent exit.
    script = h.read(Path(__file__))
    output.mkdir()
    receipt = {"schema": "cas-meta2-saved-repair-provider-read/8", "job": JOB,
        "source_sha": SOURCE, "source_archive_sha256": ARCHIVE, "source_manifest_sha256": MANIFEST,
        "registration_commit": "8af76a090e9f0659a0c84e26c731eb54c3aa285d",
        "parent_exit_code": completed["exit_code"], "resources": launch["resources"],
        "started_utc": h.utc(), "command": [sys.executable, *sys.argv], "cwd": str(Path.cwd()),
        "python": sys.version, "script_sha256": sha256(script).hexdigest(), "getter_helper_sha256": HELPER_SHA,
        "read_only": True, "provider_calls_started": False, "maximum_getter_calls": 13,
        "automatic_retries": 0, "checks": {}, "queries": [],
        "input_files": {path: {"bytes": len(data), "sha256": sha256(data).hexdigest()} for path, data in raw.items()}}
    try:
        import boto3
        from botocore.config import Config
        session = boto3.Session(profile_name="default", region_name="us-west-2")
        config = Config(connect_timeout=10, read_timeout=20, retries={"total_max_attempts": 1})
        clients = {name: session.client(name, config=config) for name in ("sts", "ec2", "iam", "scheduler", "s3")}
        receipt["provider_calls_started"] = True
        h.observe(clients, receipt, launch)
        require(len(receipt["queries"]) <= 13, "GETTER_LIMIT")
    except Exception as error:
        receipt.update(status="POST_RUN_READ_FAILED", error={"type": type(error).__name__, "message": str(error)})
    finally:
        try:
            receipt["checks"]["local_evidence_unchanged"] = h.read(Path(__file__)) == script and all(
                h.read(Path(path)) == data for path, data in raw.items())
        except Exception as error:
            receipt["checks"]["local_evidence_unchanged"] = False
            receipt["local_evidence_error"] = {"type": type(error).__name__, "message": str(error)}
        if not receipt["checks"]["local_evidence_unchanged"]:
            receipt["status"] = "POST_RUN_CHECK_FAILED"
        receipt["finished_utc"] = h.utc()
        receipt["boundary"] = ("Read-only cleanup observation, not an invoice or native repair result. "
            "Retained result objects are not downloaded or rehashed here. No new launch or cleanup mutation.")
        with (output / "receipt.json").open("xb") as stream:
            stream.write(h.encoded(receipt))
    print(json.dumps({"status": receipt["status"], "checks": receipt["checks"], "receipt": str(output / "receipt.json")}))
    return 0 if receipt["status"] == "POST_RUN_CLEANUP_CONFIRMED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
