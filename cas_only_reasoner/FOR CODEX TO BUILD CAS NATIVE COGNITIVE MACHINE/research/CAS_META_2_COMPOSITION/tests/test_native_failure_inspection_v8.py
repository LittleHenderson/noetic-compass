"""Pure exporter tests: fake SQL only; never connect to a native database.

One byte-only fixture test reads the exact retained cloud ZIP. The test suite
therefore also requires that external pinned evidence file; it does not claim
that the source archive alone contains the real evidence.
"""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import io
from pathlib import Path
import re
from types import SimpleNamespace
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pure_native_failure_exporter", ROOT / "aws/native_failure_inspection_v8.py")
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)
NOW = 1800000000
SOURCE = "a" * 40
JOB = "cas-meta2-20260906170000-1234abcd"
INSTANCE = "i-0123456789abcdef0"


def valid_config():
    return {
        "job": JOB,
        "bucket": JOB + "-807562639912",
        "region": "us-west-2",
        "account_id": "807562639912",
        "original_job": exporter.ORIGINAL_JOB,
        "source_archive_sha256": exporter.EVIDENCE_SHA,
        "source_archive_bytes": exporter.EVIDENCE_BYTES,
        "parent_source_sha": SOURCE,
        "worker_source_sha": SOURCE,
        "source_manifest_sha256": "c" * 64,
        "resource_plan": {
            "instance_type": "g7.2xlarge",
            "training": False,
            "native_execution": False,
            "sqlite_read_only": True,
            "worker_seconds_max": 180,
            "automatic_retries": 0,
        },
    }


def valid_permit(config):
    plan = {
        "schema": "cas-meta2-native-failure-inspection-plan/8",
        "launch_enabled": True, "experiment": deepcopy(exporter.EXPERIMENT),
        "original_job": exporter.ORIGINAL_JOB, "parent_source_sha": SOURCE,
        "source_manifest_sha256": config["source_manifest_sha256"],
        "resource_plan": deepcopy(config["resource_plan"]), "max_cost_usd": "4.00",
        "job": JOB, "source_sha": SOURCE, "instance_id": INSTANCE,
        "source_archive_sha256": exporter.EVIDENCE_SHA, "max_seconds": 180,
        "training": False, "native_execution": False, "sqlite_read_only": True,
    }
    reservation = {
        "job": JOB, "source_sha": SOURCE, "archive_sha256": exporter.EVIDENCE_SHA,
        "reserved_usd": "4.00", "plan": deepcopy(config["resource_plan"]),
        "plan_sha256": exporter.digest(exporter.encoded(config["resource_plan"])),
        "status": "RESERVED_NO_AUTOMATIC_REFUND",
    }
    ledger = {"owner_task_cap_usd": "400.00", "reservations": [deepcopy(reservation)]}
    return {
        "job": JOB, "instance_id": INSTANCE, "cloud_deadline_confirmed": True,
        "deadline": datetime.fromtimestamp(NOW + 900, timezone.utc).isoformat(),
        "worker_plan": plan, "worker_plan_sha256": exporter.digest(exporter.encoded(plan)),
        "reservation_receipt": {
            "reservation": reservation, "ledger_sha256": exporter.digest(exporter.encoded(ledger))},
        "ledger_snapshot": ledger,
    }


def actual_identity():
    return {"instanceId": INSTANCE, "accountId": "807562639912",
            "region": "us-west-2", "instanceType": "g7.2xlarge"}


class FakeCursor:
    def __init__(self, rows, columns=()):
        self.rows = rows
        self.description = [(name,) for name in columns]

    def fetchall(self):
        return self.rows


def native_schema():
    result = [(name, "table", 'CREATE TABLE "' + name + '" (record_id TEXT)')
              for name in sorted(exporter.TABLES)]
    for name in sorted(exporter.TABLES - {"store_metadata", "active_head"}):
        for action in ("update", "delete"):
            result.append((name + "_immutable_" + action, "trigger",
                           "CREATE TRIGGER " + name + "_immutable_" + action))
    return sorted(result)


class FakeConnection:
    """Only recognizes the exact SELECT statements; there is no SQL engine."""
    def __init__(self, *, schema=None, rows=None, columns=None):
        self.schema = native_schema() if schema is None else schema
        self.rows = {} if rows is None else rows
        self.columns = {} if columns is None else columns
        self.commands = []

    def execute(self, sql):
        self.commands.append(sql)
        if sql == ("SELECT name, type, sql FROM sqlite_schema "
                   "WHERE name NOT LIKE 'sqlite_%' ORDER BY name"):
            return FakeCursor(self.schema)
        match = re.fullmatch(r'SELECT \* FROM "([a-z_]+)" ORDER BY rowid LIMIT 10001', sql)
        assert match, "Unexpected command in fake connection: " + sql
        name = match.group(1)
        assert name in exporter.TABLES
        return FakeCursor(self.rows.get(name, []), self.columns.get(name, ("record_id",)))


def sqlite_constants():
    # Symbolic constants only; this does not import or instantiate sqlite3.
    return SimpleNamespace(SQLITE_SELECT=21, SQLITE_READ=20, SQLITE_FUNCTION=31,
                           SQLITE_PRAGMA=19, SQLITE_OK=0, SQLITE_DENY=1)


def synthetic_packet(monkeypatch, *, payload=b"SQLite format 3\x00FAKE_NOT_A_DATABASE",
                     extra=None, index_change=None):
    index = {
        "job": exporter.ORIGINAL_JOB, "partial_evidence": False,
        "omitted_full_file_count": 0,
        "files": {exporter.DB_MEMBER: {"bytes": len(payload), "sha256": exporter.digest(payload)}},
    }
    if index_change:
        index_change(index)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(exporter.DB_MEMBER, payload)
        archive.writestr("artifact_collection_receipt.json", exporter.encoded(index))
        if extra:
            for name, data in extra:
                archive.writestr(name, data)
    raw = stream.getvalue()
    monkeypatch.setattr(exporter, "EVIDENCE_SHA", exporter.digest(raw))
    monkeypatch.setattr(exporter, "EVIDENCE_BYTES", len(raw))
    return raw


def test_module_is_import_pure_and_read_only_scope_is_explicit():
    config = valid_config()
    assert exporter.validate_config(config) is None
    assert exporter.EXPERIMENT == {
        "profile": "native_failure_sqlite_inspection_v8",
        "entrypoint": "read_only_sqlite_export",
    }
    assert len(exporter.TABLES) == 20
    assert "semantic_evidence" not in exporter.TABLES


@pytest.mark.parametrize(("key", "value", "reason"), [
    ("job", "../other", "JOB_REQUIRED"),
    ("bucket", "unrelated", "AWS_SCOPE"),
    ("region", "us-east-1", "AWS_SCOPE"),
    ("account_id", "000000000000", "AWS_SCOPE"),
    ("source_archive_sha256", "0" * 64, "EXACT_FAILED_EVIDENCE_REQUIRED"),
    ("source_archive_bytes", 1, "EXACT_FAILED_EVIDENCE_REQUIRED"),
    ("original_job", "another-job", "EXACT_FAILED_EVIDENCE_REQUIRED"),
    ("parent_source_sha", "A" * 40, "SOURCE_COMMIT_REQUIRED"),
    ("worker_source_sha", "b" * 40, "SOURCE_COMMIT_MISMATCH"),
])
def test_config_refuses_wrong_identity(key, value, reason):
    config = valid_config()
    config[key] = value
    with pytest.raises(ValueError, match=reason):
        exporter.validate_config(config)


@pytest.mark.parametrize(("key", "value"), [
    ("instance_type", "g4dn.xlarge"), ("training", True),
    ("native_execution", True), ("sqlite_read_only", False),
    ("worker_seconds_max", 181), ("automatic_retries", 1),
])
def test_config_refuses_expanded_execution(key, value):
    config = valid_config()
    config["resource_plan"][key] = value
    with pytest.raises(ValueError, match="READ_ONLY_INSPECTION_SCOPE_REQUIRED"):
        exporter.validate_config(config)


def test_checked_permit_accepts_exact_nested_reservation(monkeypatch):
    monkeypatch.setattr(exporter.time, "time", lambda: NOW)
    config = valid_config()
    permit = valid_permit(config)
    assert exporter.checked_permit(config, permit, actual_identity()) == NOW + 900


@pytest.mark.parametrize(("key", "value"), [
    ("training", True), ("native_execution", True), ("sqlite_read_only", False),
    ("max_seconds", 181), ("source_sha", "b" * 40),
    ("source_archive_sha256", "0" * 64), ("instance_id", "i-wrong"),
])
def test_resealed_plan_still_cannot_expand_scope(monkeypatch, key, value):
    monkeypatch.setattr(exporter.time, "time", lambda: NOW)
    config = valid_config()
    permit = valid_permit(config)
    permit["worker_plan"][key] = value
    permit["worker_plan_sha256"] = exporter.digest(exporter.encoded(permit["worker_plan"]))
    with pytest.raises(ValueError, match="PLAN_SCOPE"):
        exporter.checked_permit(config, permit, actual_identity())


@pytest.mark.parametrize(("key", "value"), [
    ("schema", "other/8"), ("launch_enabled", False),
    ("experiment", {"profile": "training", "entrypoint": "other"}),
    ("original_job", "another-job"), ("parent_source_sha", "b" * 40),
    ("source_manifest_sha256", "0" * 64), ("resource_plan", {}),
    ("max_cost_usd", "5.00"),
])
def test_resealed_plan_identity_and_cost_limits(monkeypatch, key, value):
    monkeypatch.setattr(exporter.time, "time", lambda: NOW)
    config = valid_config()
    permit = valid_permit(config)
    permit["worker_plan"][key] = value
    permit["worker_plan_sha256"] = exporter.digest(exporter.encoded(permit["worker_plan"]))
    with pytest.raises(ValueError, match="PLAN_IDENTITY_AND_LIMITS"):
        exporter.checked_permit(config, permit, actual_identity())


@pytest.mark.parametrize("change", ["header_extra", "status", "plan_hash"])
def test_canonical_reservation_full_match(monkeypatch, change):
    monkeypatch.setattr(exporter.time, "time", lambda: NOW)
    config = valid_config()
    permit = valid_permit(config)
    reservation = permit["reservation_receipt"]["reservation"]
    if change == "header_extra":
        reservation["not_in_canonical_ledger"] = True
    else:
        key, value = (("status", "REFUNDED") if change == "status" else ("plan_sha256", "0" * 64))
        reservation[key] = value
        permit["ledger_snapshot"]["reservations"][0][key] = value
        permit["reservation_receipt"]["ledger_sha256"] = exporter.digest(exporter.encoded(permit["ledger_snapshot"]))
    with pytest.raises(ValueError, match="LEDGER_SCOPE"):
        exporter.checked_permit(config, permit, actual_identity())


@pytest.mark.parametrize(("key", "value"), [
    ("instanceId", "i-other"), ("accountId", "000000000000"),
    ("region", "us-east-1"), ("instanceType", "g4dn.xlarge"),
])
def test_live_identity_must_match(monkeypatch, key, value):
    monkeypatch.setattr(exporter.time, "time", lambda: NOW)
    config = valid_config()
    identity = actual_identity()
    identity[key] = value
    with pytest.raises(ValueError, match="LIVE_INSTANCE_IDENTITY"):
        exporter.checked_permit(config, valid_permit(config), identity)


@pytest.mark.parametrize("seconds", [-1, 0, 240, 3601])
def test_deadline_bounds(monkeypatch, seconds):
    monkeypatch.setattr(exporter.time, "time", lambda: NOW)
    config = valid_config()
    permit = valid_permit(config)
    permit["deadline"] = datetime.fromtimestamp(NOW + seconds, timezone.utc).isoformat()
    with pytest.raises(ValueError, match="DEADLINE_REQUIRED"):
        exporter.checked_permit(config, permit, actual_identity())


@pytest.mark.parametrize("change", ["shutdown", "job", "plan_hash", "ledger_hash", "amount", "cap", "duplicate"])
def test_permit_and_ledger_faults(monkeypatch, change):
    monkeypatch.setattr(exporter.time, "time", lambda: NOW)
    config = valid_config()
    permit = valid_permit(config)
    expected = {
        "shutdown": "PERMIT_JOB_OR_SHUTDOWN", "job": "PERMIT_JOB_OR_SHUTDOWN",
        "plan_hash": "PLAN_HASH", "ledger_hash": "RESERVATION_REQUIRED",
        "amount": "RESERVATION_REQUIRED", "cap": "LEDGER_SCOPE", "duplicate": "LEDGER_SCOPE",
    }[change]
    if change == "shutdown":
        permit["cloud_deadline_confirmed"] = False
    elif change == "job":
        permit["job"] = "wrong"
    elif change == "plan_hash":
        permit["worker_plan_sha256"] = "0" * 64
    elif change == "ledger_hash":
        permit["reservation_receipt"]["ledger_sha256"] = "0" * 64
    elif change == "amount":
        permit["reservation_receipt"]["reservation"]["reserved_usd"] = "5.00"
    else:
        if change == "cap":
            permit["ledger_snapshot"]["owner_task_cap_usd"] = "500.00"
        else:
            permit["ledger_snapshot"]["reservations"] *= 2
        permit["reservation_receipt"]["ledger_sha256"] = exporter.digest(
            exporter.encoded(permit["ledger_snapshot"]))
    with pytest.raises(ValueError, match=expected):
        exporter.checked_permit(config, permit, actual_identity())


def test_export_accepts_exact_native_tables_and_immutable_triggers():
    fake = FakeConnection(rows={"trace_events": [(1, "json")]},
                          columns={"trace_events": ("sequence", "payload_json")})
    result = exporter.export_tables(fake)
    assert len(result["schema"]) == 56
    assert set(result["tables"]) == exporter.TABLES
    assert result["total_rows"] == 1
    assert result["tables"]["trace_events"]["rows"] == [{"sequence": 1, "payload_json": "json"}]
    assert len(fake.commands) == 21
    assert all(command.startswith("SELECT ") for command in fake.commands)
    assert "not uncaptured process state" in result["scope"]


def test_blob_export_is_opaque_base64_not_tensor_loading():
    raw = b"\x00\xffFAKE_BYTES"
    result = exporter.export_tables(FakeConnection(
        rows={"artifacts": [("artifact-test", raw)]},
        columns={"artifacts": ("artifact_id", "payload")}))
    saved = result["tables"]["artifacts"]["rows"][0]["payload"]
    assert saved == {"encoding": "base64", "bytes": len(raw),
                     "sha256": exporter.digest(raw),
                     "data": base64.b64encode(raw).decode("ascii")}
    assert base64.b64decode(saved["data"]) == raw


@pytest.mark.parametrize("change", ["missing_table", "extra_table", "view", "missing_trigger", "extra_trigger", "duplicate"])
def test_export_refuses_unknown_or_incomplete_schema(change):
    schema = native_schema()
    if change == "missing_table":
        schema = [row for row in schema if row[0] != "active_head"]
    elif change == "missing_trigger":
        schema = [row for row in schema if row[0] != "artifacts_immutable_delete"]
    elif change == "extra_table":
        schema.append(("foreign_table", "table", "CREATE TABLE foreign_table(x)"))
    elif change == "extra_trigger":
        schema.append(("foreign_trigger", "trigger", "CREATE TRIGGER foreign_trigger"))
    elif change == "view":
        schema = [(name, "view" if name == "active_head" else kind, sql)
                  for name, kind, sql in schema]
    else:
        schema.append(schema[0])
    fake = FakeConnection(schema=schema)
    with pytest.raises(ValueError, match="EXACT_NATIVE_TABLE_SCHEMA"):
        exporter.export_tables(fake)
    assert len(fake.commands) == 1


def test_table_row_limit():
    with pytest.raises(ValueError, match="TABLE_ROW_LIMIT"):
        exporter.export_tables(FakeConnection(rows={"active_head": [(None,)] * 10001}))


def test_total_row_limit():
    rows = {name: [(None,)] * 10000 for name in sorted(exporter.TABLES)[:6]}
    with pytest.raises(ValueError, match="TOTAL_ROW_LIMIT"):
        exporter.export_tables(FakeConnection(rows=rows))


@pytest.mark.parametrize(("columns", "rows", "reason"), [
    (("id", "id"), [(1, 2)], "DUPLICATE_COLUMNS"),
    (("id",), [(1, 2)], "ROW_WIDTH"),
])
def test_bad_result_shape(columns, rows, reason):
    with pytest.raises(ValueError, match=reason):
        exporter.export_tables(FakeConnection(
            columns={"active_head": columns}, rows={"active_head": rows}))


def test_export_byte_limit(monkeypatch):
    monkeypatch.setattr(exporter, "MAX_OUTPUT", 65540)
    with pytest.raises(ValueError, match="EXPORT_SIZE_LIMIT"):
        exporter.export_tables(FakeConnection())


@pytest.mark.parametrize("action", [9, 18, 23, 24, 25, 26, 2, 11, 22])
def test_authorizer_denies_mutations_attach_and_transactions(action):
    fake = sqlite_constants()
    assert exporter.authorizer(fake)(action, "x", None, "main", None) == fake.SQLITE_DENY


@pytest.mark.parametrize("action", [21, 20, 31])
def test_authorizer_allows_direct_reads_but_not_trigger_execution(action):
    fake = sqlite_constants()
    check = exporter.authorizer(fake)
    assert check(action, "trace_events", None, "main", None) == fake.SQLITE_OK
    assert check(action, "trace_events", None, "main", "unexpected_trigger") == fake.SQLITE_DENY


@pytest.mark.parametrize(("pragma", "argument", "allowed"), [
    ("quick_check", None, True), ("quick_check", "1", False),
    ("journal_mode", "WAL", False), ("wal_checkpoint", None, False),
    ("writable_schema", "ON", False), ("query_only", "OFF", False),
])
def test_authorizer_pragma_whitelist(pragma, argument, allowed):
    fake = sqlite_constants()
    result = exporter.authorizer(fake)(fake.SQLITE_PRAGMA, pragma, argument, "main", None)
    assert result == (fake.SQLITE_OK if allowed else fake.SQLITE_DENY)


@pytest.mark.parametrize(("admission", "system", "environment"), [
    (False, "Linux", "1"), (1, "Linux", "1"),
    (True, "Windows", "1"), (True, "Linux", None), (True, "Linux", "0"),
])
def test_local_inspection_rejected_before_file_read_or_sqlite_import(monkeypatch, admission, system, environment):
    class UnreadablePath:
        def read_bytes(self):
            raise AssertionError("Admission failure must not touch the database bytes")
    monkeypatch.setattr(exporter.platform, "system", lambda: system)
    if environment is None:
        monkeypatch.delenv("CAS_META2_SQLITE_INSPECTION_REMOTE", raising=False)
    else:
        monkeypatch.setenv("CAS_META2_SQLITE_INSPECTION_REMOTE", environment)
    with pytest.raises(ValueError, match="AWS_ADMISSION_BEFORE_SQLITE"):
        exporter.inspect_database(UnreadablePath(), "0" * 64, admission)


def test_database_pin_refused_before_sqlite_import(monkeypatch):
    path = SimpleNamespace(read_bytes=lambda: b"synthetic bytes", is_symlink=lambda: False)
    monkeypatch.setattr(exporter.platform, "system", lambda: "Linux")
    monkeypatch.setenv("CAS_META2_SQLITE_INSPECTION_REMOTE", "1")
    with pytest.raises(ValueError, match="DATABASE_PIN"):
        exporter.inspect_database(path, "0" * 64, True)


def test_sidecar_refused_before_sqlite_import(monkeypatch):
    class FakePath:
        name = "native.db"
        def read_bytes(self):
            return b"synthetic bytes"
        def is_symlink(self):
            return False
        def with_name(self, name):
            return SimpleNamespace(exists=lambda: name.endswith("-wal"))
    monkeypatch.setattr(exporter.platform, "system", lambda: "Linux")
    monkeypatch.setenv("CAS_META2_SQLITE_INSPECTION_REMOTE", "1")
    with pytest.raises(ValueError, match="NO_SIDECARS_ALLOWED"):
        exporter.inspect_database(FakePath(), exporter.digest(b"synthetic bytes"), True)


def test_exact_original_archive_read_as_bytes_only():
    path = ROOT / "records/aws_child_qualification_v8_001/execution_001/cloud_artifacts.zip"
    raw = path.read_bytes()
    before = exporter.digest(raw)
    payload, identity = exporter.database_bytes(raw)
    assert len(payload) == 1523712
    assert identity["sha256"] == "41e3d9636cc9ffc026a87ca4bae3901cbf58dcff3c17039229c742f8898f14b2"
    assert identity["historical_uncaptured_state_recovered"] is False
    assert identity["sidecars_present"] is False
    assert before == exporter.digest(path.read_bytes()) == exporter.EVIDENCE_SHA


def test_packet_wrong_pin_rejected_before_zip_parsing():
    with pytest.raises(ValueError, match="EVIDENCE_BYTES_CHANGED"):
        exporter.database_bytes(b"not a packet")


def test_synthetic_packet_extracts_opaque_bytes(monkeypatch):
    payload = b"SQLite format 3\x00FAKE_NOT_A_DATABASE"
    raw = synthetic_packet(monkeypatch, payload=payload)
    assert exporter.database_bytes(raw)[0] == payload


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_packet_sidecars_rejected(monkeypatch, suffix):
    raw = synthetic_packet(monkeypatch, extra=[(exporter.DB_MEMBER + suffix, b"not used")])
    with pytest.raises(ValueError, match="DB_OR_SIDECAR_SCOPE"):
        exporter.database_bytes(raw)


@pytest.mark.parametrize("change", ["partial", "omitted", "job", "hash", "bytes"])
def test_packet_index_faults(monkeypatch, change):
    def alter(index):
        if change == "partial":
            index["partial_evidence"] = True
        elif change == "omitted":
            index["omitted_full_file_count"] = 1
        elif change == "job":
            index["job"] = "another-job"
        elif change == "hash":
            index["files"][exporter.DB_MEMBER]["sha256"] = "0" * 64
        else:
            index["files"][exporter.DB_MEMBER]["bytes"] = 0
    raw = synthetic_packet(monkeypatch, index_change=alter)
    reason = "DB_MEMBER_IDENTITY" if change in ("hash", "bytes") else "ORIGINAL_COLLECTION_INCOMPLETE"
    with pytest.raises(ValueError, match=reason):
        exporter.database_bytes(raw)


def test_packet_wrong_database_header(monkeypatch):
    raw = synthetic_packet(monkeypatch, payload=b"SIMULATED_NOT_SQLITE")
    with pytest.raises(ValueError, match="DATABASE_FORMAT_BOUND"):
        exporter.database_bytes(raw)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_strict_json_refuses_duplicate_and_nonfinite_values(raw):
    with pytest.raises(ValueError):
        exporter.decoded(raw)


def test_rendered_source_identity_and_user_data_are_only_strings():
    config = valid_config()
    rendered = exporter.render_remote(config)
    assert rendered.startswith("CONFIG = ")
    # Rendered source must preserve the exact unrendered bytes for the worker pin.
    assert rendered.split("\n", 1)[1].encode() == (ROOT / "aws/native_failure_inspection_v8.py").read_bytes()
    script = exporter.user_data(config, "a" * 64)
    assert "sleep 3400; shutdown -h now" in script
    assert "CAS_META2_SQLITE_INSPECTION_REMOTE=1" in script
    assert "timeout 600 python3 -I -B" in script
    assert "pip install" not in script
    assert "torch" not in script
