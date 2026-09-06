"""AWS-only, read-only SQLite export of one preserved failed native execution.

Importing this module does not import SQLite, neural packages or AWS SDKs.
This is forensic export, not replay, native execution, training or qualification.
"""
import base64
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import platform
import re
import shlex
import signal
import stat
import subprocess
import sys
import time
from zipfile import ZipFile, ZIP_DEFLATED

EXPERIMENT = {"profile": "native_failure_sqlite_inspection_v8", "entrypoint": "read_only_sqlite_export"}
ROOT = Path("/opt/cas-meta2-native-inspection")
ORIGINAL_JOB = "cas-meta2-20260906155525-195f5ad8"
EVIDENCE_SHA = "39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f"
EVIDENCE_BYTES = 893323
DB_MEMBER = "qualification/cases/case_00/candidate_03/native.db"
TABLES = frozenset(("store_metadata", "artifacts", "state_versions", "model_versions", "trace_events",
    "commit_receipts", "published_effects", "memory_records", "repair_frames", "repair_outcomes",
    "transition_batches", "causes", "candidate_effects", "verifier_receipts", "qualification_receipts",
    "state_intents", "model_intents", "memory_intents", "rejection_audits", "active_head"))
MAX_OUTPUT = 16 * 1024**2


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decoded(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: require(False, "NONFINITE_JSON"))


def digest(raw):
    return sha256(raw).hexdigest()


def write_new(path, value):
    raw = encoded(value)
    require(len(raw) <= MAX_OUTPUT, "OUTPUT_SIZE_BOUND")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def validate_config(config):
    require(type(config) is dict, "CONFIG_REQUIRED")
    require(re.fullmatch(r"cas-meta2-[0-9]{14}-[a-f0-9]{8}", config.get("job", "")), "JOB_REQUIRED")
    require(config.get("bucket") == config["job"] + "-807562639912"
        and config.get("region") == "us-west-2" and config.get("account_id") == "807562639912", "AWS_SCOPE")
    require(config.get("source_archive_sha256") == EVIDENCE_SHA
        and config.get("source_archive_bytes") == EVIDENCE_BYTES
        and config.get("original_job") == ORIGINAL_JOB, "EXACT_FAILED_EVIDENCE_REQUIRED")
    for key in ("parent_source_sha", "worker_source_sha"):
        require(re.fullmatch("[a-f0-9]{40}", config.get(key, "")), "SOURCE_COMMIT_REQUIRED")
    require(config["parent_source_sha"] == config["worker_source_sha"], "SOURCE_COMMIT_MISMATCH")
    plan = config.get("resource_plan", {})
    require(plan.get("instance_type") == "g7.2xlarge" and plan.get("training") is False
        and plan.get("native_execution") is False and plan.get("sqlite_read_only") is True
        and plan.get("worker_seconds_max") == 180 and plan.get("automatic_retries") == 0,
        "READ_ONLY_INSPECTION_SCOPE_REQUIRED")


def render_remote(config):
    validate_config(config)
    return "CONFIG = " + repr(config) + "\n" + Path(__file__).read_bytes().decode("utf-8")


def user_data(config, remote_sha):
    validate_config(config)
    require(re.fullmatch("[a-f0-9]{64}", remote_sha), "SCRIPT_HASH_REQUIRED")
    bucket, root = shlex.quote(config["bucket"]), ROOT.as_posix()
    return "\n".join(["#!/bin/bash", "set -eu", "umask 077",
        "export PYTHONDONTWRITEBYTECODE=1 AWS_MAX_ATTEMPTS=1 AWS_PAGER=''",
        "trap 'test ! -f " + root + "/bootstrap.log || { tail -c 1048576 " + root + "/bootstrap.log > "
        + root + "/bootstrap-tail.log; timeout 20 aws s3api put-object --bucket " + bucket
        + " --key results/bootstrap.log --body " + root + "/bootstrap-tail.log --region us-west-2 || true; }; shutdown -h now' EXIT",
        "( sleep 3400; shutdown -h now ) >/dev/null 2>&1 &",
        "mkdir -p " + root, "exec > " + root + "/bootstrap.log 2>&1",
        "command -v aws >/dev/null", "command -v python3 >/dev/null",
        "timeout 90 aws s3api get-object --bucket " + bucket + " --key input/remote.py " + root + "/remote.py --region us-west-2",
        "echo '" + remote_sha + "  " + root + "/remote.py' | sha256sum -c -",
        "export CAS_META2_SQLITE_INSPECTION_REMOTE=1 CAS_META2_AWS_JOB_ID=" + shlex.quote(config["job"]),
        "timeout 600 python3 -I -B " + root + "/remote.py", ""])


def identity():
    from urllib.request import Request, build_opener, ProxyHandler
    opener = build_opener(ProxyHandler({}))
    base = "http://169.254.169.254/latest/"
    with opener.open(Request(base + "api/token", method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"}), timeout=3) as response:
        token = response.read(1024).decode("ascii")
    with opener.open(Request(base + "dynamic/instance-identity/document",
            headers={"X-aws-ec2-metadata-token": token}), timeout=3) as response:
        raw = response.read(65537)
    require(len(raw) <= 65536, "IDENTITY_SIZE")
    return decoded(raw)


def checked_permit(config, permit, actual_identity):
    require(permit.get("job") == config["job"] and permit.get("cloud_deadline_confirmed") is True,
        "PERMIT_JOB_OR_SHUTDOWN")
    plan = permit["worker_plan"]
    require(digest(encoded(plan)) == permit.get("worker_plan_sha256"), "PLAN_HASH")
    require(plan.get("schema") == "cas-meta2-native-failure-inspection-plan/8"
        and plan.get("launch_enabled") is True and plan.get("experiment") == EXPERIMENT
        and plan.get("original_job") == ORIGINAL_JOB
        and plan.get("parent_source_sha") == config["parent_source_sha"]
        and plan.get("source_manifest_sha256") == config["source_manifest_sha256"]
        and plan.get("resource_plan") == config["resource_plan"]
        and plan.get("max_cost_usd") == "4.00", "PLAN_IDENTITY_AND_LIMITS")
    require(plan.get("job") == config["job"] and plan.get("source_sha") == config["worker_source_sha"]
        and plan.get("instance_id") == permit.get("instance_id")
        and plan.get("source_archive_sha256") == EVIDENCE_SHA and plan.get("max_seconds") == 180
        and plan.get("training") is False and plan.get("native_execution") is False
        and plan.get("sqlite_read_only") is True, "PLAN_SCOPE")
    require(actual_identity.get("instanceId") == permit.get("instance_id")
        and actual_identity.get("accountId") == config["account_id"]
        and actual_identity.get("region") == config["region"]
        and actual_identity.get("instanceType") == "g7.2xlarge", "LIVE_INSTANCE_IDENTITY")
    deadline = datetime.fromisoformat(permit["deadline"])
    require(deadline.utcoffset() is not None and deadline.utcoffset().total_seconds() == 0
        and 240 < deadline.timestamp() - time.time() <= 3600, "DEADLINE_REQUIRED")
    reservation_receipt, ledger = permit["reservation_receipt"], permit["ledger_snapshot"]
    reservation = reservation_receipt["reservation"]
    require(reservation.get("job") == config["job"] and reservation.get("source_sha") == config["worker_source_sha"]
        and reservation.get("archive_sha256") == EVIDENCE_SHA
        and reservation.get("reserved_usd") == "4.00"
        and reservation_receipt.get("ledger_sha256") == digest(encoded(ledger)), "RESERVATION_REQUIRED")
    matches = [r for r in ledger.get("reservations", []) if r.get("job") == config["job"]]
    require(len(matches) == 1 and matches[0] == reservation
        and reservation.get("status") == "RESERVED_NO_AUTOMATIC_REFUND"
        and reservation.get("plan_sha256") == digest(encoded(config["resource_plan"]))
        and matches[0].get("plan") == config["resource_plan"] and ledger.get("owner_task_cap_usd") == "400.00",
        "LEDGER_SCOPE")
    return deadline.timestamp()


def database_bytes(raw):
    require(len(raw) == EVIDENCE_BYTES and digest(raw) == EVIDENCE_SHA, "EVIDENCE_BYTES_CHANGED")
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        require(len(names) == len(set(names)) == len({name.casefold() for name in names}), "DUPLICATE_MEMBER")
        require(all(not item.is_dir() and item.filename == item.orig_filename
            and stat.S_IFMT(item.external_attr >> 16) in (0, stat.S_IFREG)
            and not item.flag_bits & 1 for item in infos), "UNSAFE_MEMBER")
        require(sum(item.file_size for item in infos) <= 64 * 1024**2, "EXPANDED_INPUT_BOUND")
        require(DB_MEMBER in names and not any(name.startswith(DB_MEMBER + "-") for name in names), "DB_OR_SIDECAR_SCOPE")
        index = decoded(archive.read("artifact_collection_receipt.json"))
        require(index.get("job") == ORIGINAL_JOB and index.get("partial_evidence") is False
            and index.get("omitted_full_file_count") == 0, "ORIGINAL_COLLECTION_INCOMPLETE")
        payload = archive.read(DB_MEMBER)
        require(index["files"][DB_MEMBER] == {"bytes": len(payload), "sha256": digest(payload)}, "DB_MEMBER_IDENTITY")
        require(payload.startswith(b"SQLite format 3\x00") and len(payload) <= 8 * 1024**2, "DATABASE_FORMAT_BOUND")
        return payload, {"archive_sha256": EVIDENCE_SHA, "member": DB_MEMBER,
            "bytes": len(payload), "sha256": digest(payload), "sidecars_present": False,
            "historical_uncaptured_state_recovered": False}


def export_tables(connection):
    """Export the stored image using SELECT only; fake connections are usable in tests."""
    schema_cursor = connection.execute("SELECT name, type, sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY name")
    schema = [dict(zip(("name", "type", "sql"), row)) for row in schema_cursor.fetchall()]
    triggers = {table + "_immutable_" + action for table in TABLES - {"store_metadata", "active_head"}
        for action in ("update", "delete")}
    require({row["name"] for row in schema if row["type"] == "table"} == TABLES
        and {row["name"] for row in schema if row["type"] == "trigger"} == triggers
        and len(schema) == len(TABLES) + len(triggers)
        and all(row["type"] in ("table", "trigger") for row in schema), "EXACT_NATIVE_TABLE_SCHEMA")
    tables, total_rows = {}, 0
    for table in sorted(TABLES):
        cursor = connection.execute('SELECT * FROM "' + table + '" ORDER BY rowid LIMIT 10001')
        columns = [column[0] for column in cursor.description]
        require(len(columns) == len(set(columns)), "DUPLICATE_COLUMNS")
        rows = cursor.fetchall()
        require(len(rows) <= 10000, "TABLE_ROW_LIMIT")
        total_rows += len(rows)
        require(total_rows <= 50000, "TOTAL_ROW_LIMIT")
        converted = []
        for row in rows:
            require(len(row) == len(columns), "ROW_WIDTH")
            converted.append({key: ({"encoding": "base64", "bytes": len(value), "sha256": digest(value),
                "data": base64.b64encode(value).decode("ascii")} if isinstance(value, bytes) else value)
                for key, value in zip(columns, row)})
        tables[table] = {"columns": columns, "row_count": len(rows), "rows": converted}
        require(len(encoded(tables)) <= MAX_OUTPUT - 65536, "EXPORT_SIZE_LIMIT")
    return {"schema": schema, "tables": tables, "total_rows": total_rows,
        "scope": "Stored database image, not uncaptured process state or independent native replay."}


def authorizer(sqlite):
    allowed = {sqlite.SQLITE_SELECT, sqlite.SQLITE_READ, sqlite.SQLITE_FUNCTION}
    def authorize(action, arg1, arg2, database, trigger):
        if action == sqlite.SQLITE_PRAGMA and arg1 == "quick_check" and arg2 is None:
            return sqlite.SQLITE_OK
        return sqlite.SQLITE_OK if action in allowed and trigger is None else sqlite.SQLITE_DENY
    return authorize


def inspect_database(path, expected_sha, admission):
    require(admission is True and platform.system() == "Linux"
        and os.environ.get("CAS_META2_SQLITE_INSPECTION_REMOTE") == "1", "AWS_ADMISSION_BEFORE_SQLITE")
    require(digest(path.read_bytes()) == expected_sha and not path.is_symlink(), "DATABASE_PIN")
    require(not any(path.with_name(path.name + suffix).exists() for suffix in ("-wal", "-shm", "-journal")), "NO_SIDECARS_ALLOWED")
    import sqlite3  # Deliberately unreachable in local pure tests.
    started = time.monotonic()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=2)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.set_authorizer(authorizer(sqlite3))
        connection.set_progress_handler(lambda: 1 if time.monotonic() - started > 60 else 0, 10000)
        quick_check = connection.execute("PRAGMA quick_check").fetchall()
        require(quick_check == [("ok",)], "DATABASE_QUICK_CHECK_FAILED")
        result = export_tables(connection)
        result.update(sqlite_version=sqlite3.sqlite_version, quick_check="ok", read_only_uri=True,
            query_only=True, trusted_schema=False, authorizer_select_only=True)
    finally:
        connection.close()
    require(digest(path.read_bytes()) == expected_sha, "DATABASE_CHANGED")
    require(not any(path.with_name(path.name + suffix).exists() for suffix in ("-wal", "-shm", "-journal")), "SIDECAR_CREATED")
    return result


def transfer(config, operation, key, path, seconds=60):
    args = ["aws", "s3api", operation, "--bucket", config["bucket"], "--key", key, "--region", "us-west-2"]
    args += ["--body", str(path)] if operation == "put-object" else [str(path)]
    return subprocess.run(args, capture_output=True, timeout=seconds, check=True)


def run_remote(config):
    validate_config(config)
    require(platform.system() == "Linux" and os.environ.get("CAS_META2_SQLITE_INSPECTION_REMOTE") == "1"
        and os.environ.get("CAS_META2_AWS_JOB_ID") == config["job"], "REMOTE_ONLY")
    started = datetime.now(timezone.utc).isoformat()
    output = ROOT / "inspection"
    output.mkdir(exist_ok=False)
    permit = None
    code, failure = 1, None
    report = {"schema": "cas-meta2-native-failure-inspection/8", "status": "INSPECTION_FAILED",
        "job": config["job"], "source_sha": config["worker_source_sha"],
        "parent_source_sha": config["parent_source_sha"], "archive_sha256": EVIDENCE_SHA,
        "source_archive_sha256": EVIDENCE_SHA,
        "experiment": EXPERIMENT, "training": False, "native_execution": False,
        "sqlite_read_only": True, "input_unchanged": False, "started_utc": started}
    try:
        manifest = config["inspection_input_manifest"]
        require(digest(encoded(manifest)) == config["source_manifest_sha256"], "INPUT_MANIFEST_HASH")
        require(manifest.get("source_archive_sha256") == EVIDENCE_SHA
            and manifest.get("source_archive_bytes") == EVIDENCE_BYTES
            and manifest.get("original_job") == ORIGINAL_JOB
            and manifest.get("worker_source_sha") == config["worker_source_sha"]
            and manifest.get("parent_source_sha") == config["parent_source_sha"], "INPUT_MANIFEST_SCOPE")
        rendered_bytes = Path(__file__).read_bytes()
        require(rendered_bytes.startswith(b"CONFIG = ")
            and digest(rendered_bytes.split(b"\n", 1)[1]) == manifest.get("exporter_source_sha256"), "EXPORTER_SOURCE_HASH")
        actual_identity = identity()
        permit_path = ROOT / "permit.json"
        wait_deadline = time.monotonic() + 120
        while True:
            try:
                transfer(config, "get-object", "input/permit.json", permit_path, seconds=10)
                break
            except subprocess.CalledProcessError:
                require(time.monotonic() < wait_deadline, "PERMIT_WAIT_EXPIRED")
                time.sleep(5)
        require(permit_path.stat().st_size <= 1024**2, "PERMIT_SIZE")
        permit = decoded(permit_path.read_bytes())
        checked_permit(config, permit, actual_identity)
        report.update(instance_identity=actual_identity, plan_sha256=permit["worker_plan_sha256"])
        def timeout_handler(_signal, _frame):
            raise TimeoutError("INSPECTION_180_SECOND_LIMIT")
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(180)
        archive_path = ROOT / "source.zip"
        transfer(config, "get-object", "input/source.zip", archive_path, seconds=60)
        require(archive_path.stat().st_size == EVIDENCE_BYTES, "INPUT_SIZE")
        raw = archive_path.read_bytes()
        payload, binding = database_bytes(raw)
        db_path = ROOT / "native.db"
        with db_path.open("xb") as stream:
            stream.write(payload)
        exported = inspect_database(db_path, binding["sha256"], True)
        exported.update(database=binding, job=config["job"], source_sha=config["worker_source_sha"],
            parent_source_sha=config["parent_source_sha"], plan_sha256=permit["worker_plan_sha256"])
        write_new(output / "export.json", exported)
        require(digest(archive_path.read_bytes()) == EVIDENCE_SHA, "INPUT_ARCHIVE_CHANGED")
        report.update(status="NATIVE_FAILURE_DATABASE_EXPORTED", database=binding, input_unchanged=True,
            total_rows=exported["total_rows"], table_counts={k: v["row_count"] for k, v in exported["tables"].items()},
            python=sys.version, sqlite_version=exported["sqlite_version"])
        code = 0
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error)}
    finally:
        signal.alarm(0)
        report.update(failure=failure, finished_utc=datetime.now(timezone.utc).isoformat())
        write_new(output / "receipt.json", report)
        files = {"inspection/" + path.name: {"bytes": path.stat().st_size, "sha256": digest(path.read_bytes())}
            for path in output.iterdir() if path.is_file()}
        collection = {"job": config["job"], "source_sha": config["worker_source_sha"],
            "parent_source_sha": config["parent_source_sha"], "experiment": EXPERIMENT,
            "returncode": code, "files": files, "partial_evidence": False, "omitted_full_file_count": 0,
            "original_file_count": len(files), "included_full_file_count": len(files)}
        target = ROOT / "artifacts.zip"
        with ZipFile(target, "x", compression=ZIP_DEFLATED) as archive:
            for name in files:
                archive.write(ROOT / name, name)
            archive.writestr("artifact_collection_receipt.json", encoded(collection))
        require(target.stat().st_size <= 32 * 1024**2, "RESULT_ARCHIVE_BOUND")
        transfer(config, "put-object", "results/artifacts.zip", target, seconds=90)
        complete = {"job": config["job"], "source_sha": config["worker_source_sha"],
            "parent_source_sha": config["parent_source_sha"], "experiment": EXPERIMENT,
            "returncode": code, "sha256": digest(target.read_bytes()), "bytes": target.stat().st_size,
            "partial_evidence": False, "omitted_full_file_count": 0}
        write_new(ROOT / "complete.json", complete)
        transfer(config, "put-object", "results/complete.json", ROOT / "complete.json", seconds=30)
    return code


if __name__ == "__main__":
    require("CONFIG" in globals(), "RENDERED_CONFIG_REQUIRED")
    raise SystemExit(run_remote(CONFIG))
