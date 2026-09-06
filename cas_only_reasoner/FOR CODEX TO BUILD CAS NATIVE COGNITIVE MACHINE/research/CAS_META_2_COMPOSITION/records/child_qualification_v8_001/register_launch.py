"""Register one committed qualification job from existing standing authority.

This helper makes no provider call and no reservation. The separate generated
capture_parent.py is a PAID execution entrypoint; this helper never runs it.
Existing registration and execution directories are never overwritten.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import importlib.abc
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
REGISTRATION_ROOT = ROOT / "records/aws_child_qualification_v8_001"
PRIOR_ROOT = ROOT / "records/aws_br_construction_v8_001/registration_001"
PRIOR_REQUEST_SHA256 = "8323d664ead43665ce5259a5f34185df3c083a6326d9963e801592e9dd186677"
PRIOR_AUTHORITY_SHA256 = "2cc6af381b213bfcaadf03b1ffc204632b9b063ab7497282572c6e25bf5863e5"
SUBNET_ID = "subnet-0eb3ca4bf5ca98f24"


def require(value, code):
    if not value:
        raise ValueError(code)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def no_links(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
        for p in (path, *path.parents)), "REGISTRATION_LINK_OR_PATH_ESCAPE")
    return path


def raw_file(path, maximum=32 * 1024**2):
    path = no_links(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum,
            "REGISTRATION_BOUNDED_REGULAR_FILE_REQUIRED")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "REGISTRATION_FILE_SIZE_LIMIT")
    return raw


def hash_bytes(raw):
    return sha256(raw).hexdigest()


def write_new(path, raw):
    path = no_links(path)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(raw_file(path) == raw, "REGISTRATION_WRITTEN_BYTES_CHANGED")


def committed_parent(parent_sha):
    require(type(parent_sha) is str and re.fullmatch(r"[0-9a-f]{40}", parent_sha), "EXACT_PARENT_COMMIT_REQUIRED")
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    require(subprocess.check_output(["git", "rev-parse", parent_sha + "^{commit}"], cwd=repo, text=True).strip()
            == parent_sha, "EXACT_PARENT_COMMIT_REQUIRED")
    parent_path = ROOT / "aws/launch_child_qualification_v8.py"
    raw = raw_file(parent_path)
    committed = subprocess.check_output(["git", "cat-file", "blob",
        parent_sha + ":" + parent_path.relative_to(repo).as_posix()], cwd=repo)
    require(raw == committed, "REGISTRATION_PARENT_NOT_COMMITTED")
    parent = ModuleType("registered_child_qualification_parent")
    parent.__file__ = str(parent_path)
    exec(compile(raw, str(parent_path), "exec"), parent.__dict__)
    return parent


def capture_source(request_sha256, authority_sha256, execution_number):
    """Render a separate one-shot parent capture. Rendering does NOT execute it."""
    require(all(type(h) is str and re.fullmatch(r"[0-9a-f]{64}", h)
                for h in (request_sha256, authority_sha256)), "CAPTURE_EXACT_HASHES_REQUIRED")
    require(type(execution_number) is int and 1 <= execution_number <= 999999, "CAPTURE_EXECUTION_NUMBER")
    template = r'''"""PAID entrypoint: capture one registered qualification launch, with no retry."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parent / "__EXECUTION__"
REQUEST_SHA256 = "__REQUEST_SHA256__"
AUTHORITY_SHA256 = "__AUTHORITY_SHA256__"
COMMAND = [sys.executable, "-B", "-m", "aws.launch_child_qualification_v8", "--execute",
    "--request", str(HERE / "launch_request.json"), "--request-sha256", REQUEST_SHA256,
    "--authority", str(HERE / "standing_authority.json"), "--authority-sha256", AUTHORITY_SHA256,
    "--receipt-dir", str(EXECUTION), "--profile", "default"]


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def safe(path):
    if ".." in path.parts or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                               for p in (path, *path.parents)):
        raise ValueError("CAPTURE_LINK_OR_PATH_ESCAPE")
    return path


def pinned(path, expected):
    safe(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 2 * 1024**2:
        raise ValueError("CAPTURE_BOUNDED_RECORD_REQUIRED")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError("CAPTURE_REGISTERED_BYTES_CHANGED")
    return raw


def write_new(path, value):
    with safe(path).open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def main():
    safe(HERE)
    safe(EXECUTION)
    marker = HERE / "parent_process_start.json"
    if marker.exists() or EXECUTION.exists():
        raise ValueError("Existing launch record: inspect it; never launch again.")
    pinned(HERE / "launch_request.json", REQUEST_SHA256)
    pinned(HERE / "standing_authority.json", AUTHORITY_SHA256)
    record = {"schema": "cas-meta2-child-qualification-parent-capture/8", "command": COMMAND,
        "cwd": str(ROOT), "python": sys.version, "automatic_retries": 0,
        "request_sha256": REQUEST_SHA256, "authority_sha256": AUTHORITY_SHA256,
        "capture_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_utc": datetime.now(timezone.utc).isoformat()}
    # An exclusive marker claims this attempt BEFORE creating a subprocess.
    write_new(marker, record)
    process = None
    completion = {**record, "pid": None, "exit_code": None, "process_created": False}
    try:
        with safe(HERE / "parent_stdout.txt").open("xb") as stdout, safe(HERE / "parent_stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(COMMAND, cwd=ROOT, stdout=stdout, stderr=stderr,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            completion.update(pid=process.pid, process_created=True)
            write_new(HERE / "parent_process_identity.json", {"pid": process.pid, "command": COMMAND})
            print(json.dumps({"status": "PARENT_STARTED", "pid": process.pid}), flush=True)
            completion["exit_code"] = process.wait()
    except BaseException as error:
        completion["capture_failure"] = {"type": type(error).__name__, "message": str(error)}
        # Never launch again after a capture failure, even when process creation
        # is uncertain. The parent/provider receipts must be inspected first.
        if process is not None:
            completion["exit_code"] = process.poll()
    finally:
        completion["finished_utc"] = datetime.now(timezone.utc).isoformat()
        completion["outputs"] = {name: {"bytes": (HERE / name).stat().st_size,
            "sha256": sha256((HERE / name).read_bytes()).hexdigest()}
            for name in ("parent_stdout.txt", "parent_stderr.txt") if (HERE / name).is_file()}
        write_new(HERE / "parent_process_completion.json", completion)
    print(json.dumps({"status": "PARENT_EXITED" if completion["exit_code"] is not None else "CAPTURE_FAILED_PARENT_STATE_UNCONFIRMED",
                      "exit_code": completion["exit_code"]}), flush=True)
    return completion["exit_code"] if type(completion["exit_code"]) is int else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''
    result = template.replace("__EXECUTION__", "execution_%03d" % execution_number).replace(
        "__REQUEST_SHA256__", request_sha256).replace("__AUTHORITY_SHA256__", authority_sha256)
    compile(result, "capture_parent.py", "exec")  # Syntax only, never exec.
    return result.encode()


def register(parent_sha, package_receipt, *, package_receipt_sha256=None, registration_number=1, execution_number=1):
    require(type(registration_number) is int and 1 <= registration_number <= 999999, "REGISTRATION_NUMBER_INVALID")
    require(type(execution_number) is int and 1 <= execution_number <= 999999, "EXECUTION_NUMBER_INVALID")
    output = no_links(REGISTRATION_ROOT / ("registration_%03d" % registration_number))
    execution = no_links(REGISTRATION_ROOT / ("execution_%03d" % execution_number))
    require(not output.exists() and not execution.exists(), "REGISTRATION_OR_EXECUTION_ALREADY_EXISTS")
    parent = committed_parent(parent_sha)
    parent_identity = parent.verify_parent_source(parent_sha)
    receipt_path = no_links(package_receipt)
    receipt_raw = raw_file(receipt_path)
    if package_receipt_sha256 is not None:
        require(type(package_receipt_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", package_receipt_sha256)
                and hash_bytes(receipt_raw) == package_receipt_sha256, "PACKAGE_RECEIPT_PIN_CHANGED")
    package = parent.decoded(receipt_raw)
    require(package.get("schema") == "cas-meta2-child-qualification-source-package-receipt/8"
            and package.get("status") == "SOURCE_ONLY_NO_LAUNCH", "DEDICATED_SOURCE_PACKAGE_RECEIPT_REQUIRED")
    old_request = parent.decoded(parent.read_pinned(PRIOR_ROOT / "launch_request.json", PRIOR_REQUEST_SHA256))
    old_authority = parent.decoded(parent.read_pinned(PRIOR_ROOT / "standing_authority.json", PRIOR_AUTHORITY_SHA256))
    require(old_request.get("subnet_id") == SUBNET_ID, "PRIOR_SUBNET_ID_CHANGED")
    request = parent.build_request(parent_sha, SUBNET_ID, package["archive"], package["archive_sha256"],
                                   package["source_sha"], package["manifest_sha256"])
    h = parent.helpers(parent_sha)
    manifest = parent.source_for(request, h["package"])
    require(manifest == package.get("manifest") and request["source_archive_bytes"] == package.get("archive_bytes")
            and package.get("member_count") == len(manifest["files_sha256"]) + 1,
            "PACKAGE_RECEIPT_MANIFEST_OR_SIZE_DISAGREEMENT")
    ledger = h["old"].budget.read_ledger()  # Canonical history checked under its short owned lock.
    require(Decimal(ledger["remaining_unreserved_usd"]) >= Decimal("4.00"), "CAMPAIGN_HEADROOM_BELOW_PROPOSED_JOB")
    require(not any(row["job"] == request["job"] for row in ledger["reservations"]), "JOB_ALREADY_RESERVED")
    request_raw = parent.encoded(request)
    authority = {"schema": "cas-meta2-child-qualification-standing-authority/8", "standing_campaign_authorization": True,
        "campaign_cap_usd": "400.00", "max_job_cost_usd": "4.00", "experiment": parent.EXPERIMENT,
        "training": False, "native_execution": True, "launch_request_sha256": hash_bytes(request_raw),
        **{key: request[key] for key in ("job", "parent_source_sha", "worker_source_sha", "source_archive_sha256", "source_manifest_sha256")},
        "campaign_approval": old_authority["campaign_approval"], "standing_user_message": old_authority["standing_user_message"],
        "evidence_kind": "Builder registration of existing campaign authorization and standing user direction; not a new human approval or provider receipt.",
        "scope_boundary": "One four-task whole-task native qualification panel only; at most20 full executions/110 ticks if all complete. No training, extra curriculum execution, automatic retry, merge or deployment."}
    require(authority["campaign_approval"] == {k: ledger["approval"][k] for k in ("path", "sha256")},
            "CURRENT_CANONICAL_CAMPAIGN_DIFFERS_FROM_PRIOR_AUTHORITY")
    authority_raw = parent.encoded(authority)
    capture_raw = capture_source(hash_bytes(request_raw), hash_bytes(authority_raw), execution_number)
    source_before = hash_bytes(raw_file(__file__))
    ledger_before = hash_bytes(h["old"].budget.encoded(ledger))
    output.mkdir(parents=True, exist_ok=False)
    try:
        contents = {"launch_request.json": request_raw, "standing_authority.json": authority_raw,
                    "capture_parent.py": capture_raw, "ledger_observation.json": h["old"].budget.encoded(ledger)}
        for name, raw in contents.items():
            write_new(output / name, raw)
        # Use the actual dedicated validator against the saved bytes and live
        # canonical campaign record; no fabricated approval predicate.
        checked_authority = parent.validate_authority(output / "standing_authority.json", hash_bytes(authority_raw),
                                                       request, hash_bytes(request_raw), ledger)
        require(parent.verify_parent_source(parent_sha) == parent_identity, "PARENT_CHANGED_DURING_REGISTRATION")
        require(hash_bytes(raw_file(__file__)) == source_before, "REGISTRAR_CHANGED_DURING_REGISTRATION")
        ledger_after = h["old"].budget.read_ledger()
        require(h["old"].budget.encoded(ledger_after) == h["old"].budget.encoded(ledger), "CANONICAL_LEDGER_CHANGED_DURING_REGISTRATION")
        result = {"schema": "cas-meta2-child-qualification-registration/8", "status": "REGISTERED_NOT_EXECUTED",
            "created_utc": datetime.now(timezone.utc).isoformat(), "job": request["job"],
            "parent_source_sha": parent_sha, "worker_source_sha": request["worker_source_sha"],
            "registration_directory": str(output), "fresh_execution_directory": str(execution),
            "registrar_sha256": source_before, "parent_file_sha256": parent_identity,
            "package_receipt": {"path": str(receipt_path), "sha256": hash_bytes(receipt_raw)},
            "request_sha256": hash_bytes(request_raw), "authority_sha256": checked_authority["authority_artifact_sha256"],
            "capture_source_sha256": hash_bytes(capture_raw), "source_archive_sha256": request["source_archive_sha256"],
            "source_manifest_sha256": request["source_manifest_sha256"], "subnet_id": SUBNET_ID,
            "subnet_recheck": "Provider state and current price are rechecked by the parent only at explicit launch.",
            "budget_observation": {"revision": ledger["revision"], "total_reserved_usd": ledger["total_reserved_usd"],
                "remaining_unreserved_usd": ledger["remaining_unreserved_usd"], "before_sha256": ledger_before,
                "after_sha256": hash_bytes(h["old"].budget.encoded(ledger_after)), "unchanged": True},
            "standing_authority_registered": True, "new_human_approval_created": False,
            "new_reservation": False, "provider_calls": False, "paid_capture_executed": False,
            "capture_is_paid_execution_entrypoint": True,
            "files": {name: {"bytes": len(raw), "sha256": hash_bytes(raw)} for name, raw in contents.items()}}
        write_new(output / "registration_receipt.json", encoded(result))
        return result
    except BaseException as error:
        failure = {"status": "REGISTRATION_FAILED_PARTIAL_FILES_PRESERVED", "error": type(error).__name__,
                   "message": str(error), "provider_calls": False, "new_reservation": False,
                   "paid_capture_executed": False, "registration_directory": str(output)}
        write_new(output / "registration_failure.json", encoded(failure))
        raise


class NoNeuralOrProviderImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"torch", "casformer", "cas_cjt", "boto3", "botocore"}:
            raise RuntimeError("REGISTRATION_FORBIDDEN_IMPORT:" + fullname)
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--parent-source-sha", required=True)
    parser.add_argument("--package-receipt", required=True)
    parser.add_argument("--package-receipt-sha256")
    parser.add_argument("--registration-number", type=int, default=1)
    parser.add_argument("--execution-number", type=int, default=1)
    args = parser.parse_args(argv)
    sys.meta_path.insert(0, NoNeuralOrProviderImports())
    def audit(event, arguments):
        if event == "sqlite3.connect" or event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.sendto", "socket.getaddrinfo"}:
            raise RuntimeError("REGISTRATION_NETWORK_OR_DATABASE_OPERATION_REFUSED:" + event)
    sys.addaudithook(audit)
    result = register(args.parent_source_sha, args.package_receipt, package_receipt_sha256=args.package_receipt_sha256,
                      registration_number=args.registration_number, execution_number=args.execution_number)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
