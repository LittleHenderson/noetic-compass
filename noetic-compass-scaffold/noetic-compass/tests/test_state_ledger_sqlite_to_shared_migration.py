from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from api.services.production.state_substrate import LedgerRecord
from api.services.production.state_substrate.memory_store import InMemoryStateStore
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.services.production.state_substrate.sqlite_to_shared_migration import (
    MIGRATION_KIND,
    MIGRATION_RECORD_ID,
    MIGRATION_TENANT,
    StateLedgerMigrationError,
    fingerprint_records,
    migrate_sqlite_ledger_records_once,
    read_sqlite_ledger_records,
)


STAMP = datetime(2026, 7, 14, 9, 30, tzinfo=UTC)


class ExactTimestampMemoryStore(InMemoryStateStore):
    """Test double matching PostgresStateStore's supplied timestamp behavior."""

    def put(self, record: LedgerRecord, *, expected_version: int) -> LedgerRecord:
        stored = super().put(record, expected_version=expected_version)
        exact = replace(stored, updated_at=record.updated_at)
        self._records[(record.tenant_id, record.kind, record.record_id)] = exact
        return exact

    def migration_record_keys(self) -> tuple[tuple[str, str, str], ...]:
        return tuple(sorted(self._records))


def _seed_source(path) -> tuple[LedgerRecord, LedgerRecord]:
    source = SqliteStateStore(path)
    first = source.put(
        LedgerRecord.new(
            tenant_id="public",
            kind="distributed_audit",
            record_id="audit-1",
            payload={"status": "RUNNING", "nested": {"count": 1}},
            parent_ids=("request-1",),
            source="hosted_api",
            trace_id="trace-1",
            now=STAMP,
        ),
        expected_version=0,
    )
    first = source.put(
        first.with_payload(
            {"status": "COMPLETE", "nested": {"count": 2}},
            now=STAMP + timedelta(minutes=2),
        ),
        expected_version=first.version,
    )
    second = source.put(
        LedgerRecord.new(
            tenant_id="tenant-b",
            kind="worker",
            record_id="worker-1",
            payload={"model_id": "EleutherAI/pythia-160m"},
            source="fleet_registration",
            now=STAMP + timedelta(minutes=3),
        ),
        expected_version=0,
    )
    source.acquire_lease(
        "public",
        "run-lease-1",
        holder="old-process",
        ttl_seconds=3600,
        now=STAMP,
    )
    source.close()
    return first, second


def test_reads_every_record_and_fingerprint_is_deterministic(tmp_path) -> None:
    path = tmp_path / "state.db"
    _seed_source(path)
    first = read_sqlite_ledger_records(path)
    second = read_sqlite_ledger_records(path)
    assert len(first) == 2
    assert first == second
    assert fingerprint_records(first) == fingerprint_records(second)


def test_migration_preserves_exact_records_and_never_replays_leases(tmp_path) -> None:
    path = tmp_path / "state.db"
    _seed_source(path)
    expected = read_sqlite_ledger_records(path)
    destination = ExactTimestampMemoryStore()

    result = migrate_sqlite_ledger_records_once(path, destination)

    assert result["already_completed"] is False
    assert result["record_count"] == 2
    for record in expected:
        assert destination.get(record.tenant_id, record.kind, record.record_id) == record
    assert destination.get_lease("public", "run-lease-1", now=STAMP) is None
    marker = destination.get(MIGRATION_TENANT, MIGRATION_KIND, MIGRATION_RECORD_ID)
    assert marker is not None
    assert marker.payload["leases_migrated"] is False


def test_repeated_start_is_idempotent_when_source_fingerprint_matches(tmp_path) -> None:
    path = tmp_path / "state.db"
    _seed_source(path)
    destination = ExactTimestampMemoryStore()
    migrate_sqlite_ledger_records_once(path, destination)

    result = migrate_sqlite_ledger_records_once(path, destination)

    assert result["already_completed"] is True
    assert result["record_count"] == 2


def test_source_change_after_marker_fails_loud(tmp_path) -> None:
    path = tmp_path / "state.db"
    _seed_source(path)
    destination = ExactTimestampMemoryStore()
    migrate_sqlite_ledger_records_once(path, destination)

    source = SqliteStateStore(path)
    source.put(
        LedgerRecord.new(
            tenant_id="public",
            kind="worker",
            record_id="worker-new",
            payload={"status": "new"},
        ),
        expected_version=0,
    )
    source.close()

    with pytest.raises(StateLedgerMigrationError, match="marker"):
        migrate_sqlite_ledger_records_once(path, destination)


def test_conflicting_destination_record_is_never_overwritten(tmp_path) -> None:
    path = tmp_path / "state.db"
    _seed_source(path)
    destination = ExactTimestampMemoryStore()
    destination.put(
        LedgerRecord.new(
            tenant_id="public",
            kind="distributed_audit",
            record_id="audit-1",
            payload={"foreign": True},
            now=STAMP - timedelta(days=1),
        ),
        expected_version=0,
    )

    with pytest.raises(StateLedgerMigrationError, match="identity conflicts"):
        migrate_sqlite_ledger_records_once(path, destination)
    assert destination.get(MIGRATION_TENANT, MIGRATION_KIND, MIGRATION_RECORD_ID) is None


def test_unrelated_destination_record_is_rejected_before_copy(tmp_path) -> None:
    path = tmp_path / "state.db"
    _seed_source(path)
    destination = ExactTimestampMemoryStore()
    destination.put(
        LedgerRecord.new(
            tenant_id="foreign",
            kind="account",
            record_id="not-from-source",
            payload={"foreign": True},
        ),
        expected_version=0,
    )

    with pytest.raises(StateLedgerMigrationError, match="outside the SQLite source"):
        migrate_sqlite_ledger_records_once(path, destination)


def test_partial_destination_may_resume_only_for_source_keys(tmp_path) -> None:
    path = tmp_path / "state.db"
    _seed_source(path)
    records = read_sqlite_ledger_records(path)
    destination = ExactTimestampMemoryStore()
    destination.put(replace(records[0], version=0), expected_version=0)

    result = migrate_sqlite_ledger_records_once(path, destination)

    assert result["record_count"] == 2
    assert destination.get(MIGRATION_TENANT, MIGRATION_KIND, MIGRATION_RECORD_ID)


def test_missing_or_wrong_schema_source_fails_loud(tmp_path) -> None:
    with pytest.raises(StateLedgerMigrationError, match="does not exist"):
        read_sqlite_ledger_records(tmp_path / "missing.db")

    wrong = tmp_path / "wrong.db"
    wrong.write_bytes(b"not sqlite")
    with pytest.raises(StateLedgerMigrationError):
        read_sqlite_ledger_records(wrong)
