"""One-time, fail-closed SQLite-to-shared-ledger record migration.

The production service historically served from a persistent SQLite ledger. Merely
setting ``NC_DATABASE_URL`` would otherwise switch read authority to an empty
Postgres ledger on restart. This module copies the exact versioned records before
the mirror is installed, then writes a durable fingerprint marker. Leases are
intentionally not migrated: a process restart invalidates old execution ownership,
and replaying a stale lease would be less safe than reacquiring one.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Iterable

from .interface import LedgerRecord, StateStore, StateStoreError, VersionConflict


MIGRATION_SCHEMA_VERSION = "cas_state_ledger_sqlite_to_shared.v1"
MIGRATION_TENANT = "__cas_system__"
MIGRATION_KIND = "state_ledger_migration"
MIGRATION_RECORD_ID = "sqlite_to_shared_v1"


class StateLedgerMigrationError(StateStoreError):
    """The source or destination cannot support an exact, safe migration."""


def _parse_timestamp(raw: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError as exc:
        raise StateLedgerMigrationError("SQLite ledger contains an invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise StateLedgerMigrationError("SQLite ledger timestamp has no timezone")
    return parsed.astimezone(UTC)


def read_sqlite_ledger_records(path: str | Path) -> tuple[LedgerRecord, ...]:
    """Read every committed record from ``path`` without opening it for writes."""
    source = Path(path)
    if not source.is_file():
        raise StateLedgerMigrationError("configured SQLite migration source does not exist")
    uri = f"file:{source.resolve().as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise StateLedgerMigrationError("could not open SQLite migration source") from exc
    try:
        rows = connection.execute(
            """
            SELECT tenant_id, kind, record_id, version, created_at, updated_at,
                   payload, parent_ids, source, trace_id
              FROM records
             ORDER BY tenant_id, kind, record_id
            """
        ).fetchall()
    except sqlite3.Error as exc:
        raise StateLedgerMigrationError(
            "SQLite migration source does not contain the expected ledger schema"
        ) from exc
    finally:
        connection.close()

    records: list[LedgerRecord] = []
    for row in rows:
        try:
            payload = json.loads(row[6])
            parent_ids = json.loads(row[7])
            version = int(row[3])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StateLedgerMigrationError(
                "SQLite migration source contains an invalid record envelope"
            ) from exc
        if not isinstance(payload, dict) or not isinstance(parent_ids, list) or version < 1:
            raise StateLedgerMigrationError(
                "SQLite migration source contains an invalid record payload or version"
            )
        records.append(
            LedgerRecord(
                tenant_id=str(row[0]),
                kind=str(row[1]),
                record_id=str(row[2]),
                version=version,
                created_at=_parse_timestamp(row[4]),
                updated_at=_parse_timestamp(row[5]),
                payload=payload,
                parent_ids=tuple(str(value) for value in parent_ids),
                source=str(row[8]),
                trace_id=None if row[9] is None else str(row[9]),
            )
        )
    return tuple(records)


def fingerprint_records(records: Iterable[LedgerRecord]) -> str:
    canonical = [
        {
            "tenant_id": record.tenant_id,
            "kind": record.kind,
            "record_id": record.record_id,
            "version": record.version,
            "created_at": record.created_at.astimezone(UTC).isoformat(),
            "updated_at": record.updated_at.astimezone(UTC).isoformat(),
            "payload": dict(record.payload),
            "parent_ids": list(record.parent_ids),
            "source": record.source,
            "trace_id": record.trace_id,
        }
        for record in records
    ]
    encoded = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _record_matches(actual: LedgerRecord, expected: LedgerRecord) -> bool:
    return (
        actual.tenant_id == expected.tenant_id
        and actual.kind == expected.kind
        and actual.record_id == expected.record_id
        and actual.version == expected.version
        and actual.created_at == expected.created_at
        and actual.updated_at == expected.updated_at
        and dict(actual.payload) == dict(expected.payload)
        and tuple(actual.parent_ids) == tuple(expected.parent_ids)
        and actual.source == expected.source
        and actual.trace_id == expected.trace_id
    )


def _copy_record(destination: StateStore, source: LedgerRecord) -> None:
    current = destination.get(source.tenant_id, source.kind, source.record_id)
    if current is not None and current.version > source.version:
        raise StateLedgerMigrationError(
            "destination contains a newer record; refusing to overwrite or mix ledgers"
        )

    if current is None:
        candidate = replace(source, version=0)
        try:
            current = destination.put(candidate, expected_version=0)
        except VersionConflict:
            current = destination.get(source.tenant_id, source.kind, source.record_id)
            if current is None:
                raise StateLedgerMigrationError(
                    "destination record creation raced but no record is readable"
                )

    if current.created_at != source.created_at:
        raise StateLedgerMigrationError(
            "destination record identity conflicts with the SQLite source"
        )

    while current.version < source.version:
        candidate = LedgerRecord(
            tenant_id=source.tenant_id,
            kind=source.kind,
            record_id=source.record_id,
            version=current.version,
            created_at=source.created_at,
            updated_at=source.updated_at,
            payload=dict(source.payload),
            parent_ids=tuple(source.parent_ids),
            source=source.source,
            trace_id=source.trace_id,
        )
        try:
            current = destination.put(candidate, expected_version=current.version)
        except VersionConflict:
            reread = destination.get(source.tenant_id, source.kind, source.record_id)
            if reread is None or reread.version <= current.version:
                raise StateLedgerMigrationError(
                    "destination record update conflicted without forward progress"
                )
            current = reread
            if current.version > source.version:
                raise StateLedgerMigrationError(
                    "destination advanced beyond the migration source"
                )

    if not _record_matches(current, source):
        raise StateLedgerMigrationError(
            "destination record does not exactly match the SQLite source"
        )


def migrate_sqlite_ledger_records_once(
    source_path: str | Path, destination: StateStore
) -> dict[str, object]:
    """Copy source records and create/verify an idempotency marker.

    A marker mismatch fails loud. The marker contains only a SHA-256 and count;
    no source filesystem path, payload, customer identifier, or credential is stored.
    """
    records = read_sqlite_ledger_records(source_path)
    fingerprint = fingerprint_records(records)
    marker = destination.get(MIGRATION_TENANT, MIGRATION_KIND, MIGRATION_RECORD_ID)
    if marker is not None:
        payload = dict(marker.payload)
        if (
            payload.get("schema_version") != MIGRATION_SCHEMA_VERSION
            or payload.get("source_fingerprint_sha256") != fingerprint
            or payload.get("record_count") != len(records)
            or payload.get("leases_migrated") is not False
        ):
            raise StateLedgerMigrationError(
                "existing migration marker does not match the SQLite source"
            )
        return {
            "already_completed": True,
            "record_count": len(records),
            "source_fingerprint_sha256": fingerprint,
            "leases_migrated": False,
        }

    key_reader = getattr(destination, "migration_record_keys", None)
    if callable(key_reader):
        source_keys = {
            (record.tenant_id, record.kind, record.record_id) for record in records
        }
        destination_keys = {tuple(item) for item in key_reader()}
        unexpected = destination_keys - source_keys
        if unexpected:
            raise StateLedgerMigrationError(
                "unmarked destination contains records outside the SQLite source"
            )

    for record in records:
        _copy_record(destination, record)

    marker_payload = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "source_fingerprint_sha256": fingerprint,
        "record_count": len(records),
        "leases_migrated": False,
    }
    marker_record = LedgerRecord.new(
        tenant_id=MIGRATION_TENANT,
        kind=MIGRATION_KIND,
        record_id=MIGRATION_RECORD_ID,
        payload=marker_payload,
        source="sqlite_to_shared_startup_migration",
    )
    try:
        destination.put(marker_record, expected_version=0)
    except VersionConflict:
        raced = destination.get(MIGRATION_TENANT, MIGRATION_KIND, MIGRATION_RECORD_ID)
        if raced is None or dict(raced.payload) != marker_payload:
            raise StateLedgerMigrationError(
                "migration marker creation conflicted with a different receipt"
            )

    return {
        "already_completed": False,
        "record_count": len(records),
        "source_fingerprint_sha256": fingerprint,
        "leases_migrated": False,
    }
