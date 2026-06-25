"""Tests for cas_forex.legacy_receipts_archive."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cas_forex.legacy_receipts_archive import (
    LegacyReceiptArchiveResult,
    archive_stale_receipts,
    identify_stale_pending_receipts,
)


NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)


def _iso(now: datetime, hours_old: float) -> str:
    return (now - timedelta(hours=hours_old)).isoformat()


# ---------------------------------------------------------------------------
# Pure identification tests
# ---------------------------------------------------------------------------


def test_identify_empty_returns_empty_tuple() -> None:
    assert identify_stale_pending_receipts([]) == ()


def test_identify_ignores_rows_without_kind_field() -> None:
    events = [
        {"broker_mode": "MT4-live", "created_at": _iso(NOW, 48.0)},
        {"foo": "bar"},
    ]
    assert identify_stale_pending_receipts(events, now=NOW) == ()


def test_identify_mixed_returns_only_stale_mt4_pending() -> None:
    events = [
        # 0: stale MT4 pending — INCLUDED
        {
            "kind": "RECEIPT_PENDING",
            "broker_mode": "MT4-live",
            "created_at": _iso(NOW, 48.0),
        },
        # 1: MT4 but acknowledged — excluded
        {
            "kind": "RECEIPT_ACKNOWLEDGED",
            "broker_mode": "MT4-live",
            "created_at": _iso(NOW, 48.0),
        },
        # 2: MT5 pending — excluded
        {
            "kind": "RECEIPT_PENDING",
            "broker_mode": "MT5-live",
            "created_at": _iso(NOW, 48.0),
        },
        # 3: stale MT4 pending nested in command — INCLUDED
        {
            "event_kind": "RECEIPT_PENDING",
            "command": {"broker_mode": "mt4-paper"},
            "timestamp": _iso(NOW, 72.0),
        },
        # 4: stale MT4 pending nested in intent — INCLUDED
        {
            "kind": "RECEIPT_PENDING",
            "intent": {"broker_mode": "MT4"},
            "created_at_iso": _iso(NOW, 25.0),
        },
    ]
    assert identify_stale_pending_receipts(events, now=NOW) == (0, 3, 4)


def test_identify_age_threshold_excludes_recent_includes_old() -> None:
    events = [
        {
            "kind": "RECEIPT_PENDING",
            "broker_mode": "MT4-live",
            "created_at": _iso(NOW, 12.0),  # younger than 24h — excluded
        },
        {
            "kind": "RECEIPT_PENDING",
            "broker_mode": "MT4-live",
            "created_at": _iso(NOW, 36.0),  # older than 24h — included
        },
    ]
    assert identify_stale_pending_receipts(
        events, age_threshold_hours=24.0, now=NOW
    ) == (1,)


def test_identify_unparseable_timestamp_is_not_stale() -> None:
    events = [
        {
            "kind": "RECEIPT_PENDING",
            "broker_mode": "MT4-live",
            "created_at": "not-a-timestamp",
        },
        {
            "kind": "RECEIPT_PENDING",
            "broker_mode": "MT4-live",
            # no timestamp keys at all
        },
    ]
    assert identify_stale_pending_receipts(events, now=NOW) == ()


def test_identify_row_without_broker_mode_is_not_stale() -> None:
    events = [
        {
            "kind": "RECEIPT_PENDING",
            "created_at": _iso(NOW, 48.0),
        }
    ]
    assert identify_stale_pending_receipts(events, now=NOW) == ()


def test_identify_terminal_receipt_pending_via_event_type_no_broker_mode() -> None:
    """Live agent cycle writes `event_type: TERMINAL_RECEIPT_PENDING` with no
    top-level broker_mode. These rows ARE stale-archivable when old enough
    because the lane is implicit in consumer_agent_ids and there's no other
    way to age them out."""
    events = [
        # Fresh — should NOT be archived
        {
            "event_type": "TERMINAL_RECEIPT_PENDING",
            "created_at": _iso(NOW, 1.0),
        },
        # Old — should be archived
        {
            "event_type": "TERMINAL_RECEIPT_PENDING",
            "created_at": _iso(NOW, 48.0),
        },
        # Old but wrong type — should NOT be archived
        {
            "event_type": "AGENT_HEARTBEAT",
            "created_at": _iso(NOW, 48.0),
        },
    ]
    assert identify_stale_pending_receipts(events, now=NOW) == (1,)


# ---------------------------------------------------------------------------
# I/O tests
# ---------------------------------------------------------------------------


def _write_journal(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            out.append(json.loads(stripped))
    return out


def _sample_rows() -> list[dict]:
    return [
        {
            "kind": "RECEIPT_PENDING",
            "broker_mode": "MT4-live",
            "created_at": _iso(NOW, 48.0),
            "id": "row-0-stale",
        },
        {
            "kind": "RECEIPT_ACKNOWLEDGED",
            "broker_mode": "MT4-live",
            "created_at": _iso(NOW, 48.0),
            "id": "row-1-kept",
        },
        {
            "kind": "RECEIPT_PENDING",
            "broker_mode": "MT5-live",
            "created_at": _iso(NOW, 48.0),
            "id": "row-2-kept-mt5",
        },
        {
            "kind": "RECEIPT_PENDING",
            "broker_mode": "MT4-paper",
            "created_at": _iso(NOW, 72.0),
            "id": "row-3-stale",
        },
    ]


def test_dry_run_does_not_write_snapshot_or_modify_journal(tmp_path: Path) -> None:
    journal = tmp_path / "agent-events.jsonl"
    snapshot_dir = tmp_path / "snapshots"
    rows = _sample_rows()
    _write_journal(journal, rows)
    original_text = journal.read_text(encoding="utf-8")

    result = archive_stale_receipts(
        journal_path=journal,
        snapshot_dir=snapshot_dir,
        dry_run=True,
        now=NOW,
    )

    assert isinstance(result, LegacyReceiptArchiveResult)
    assert result.dry_run is True
    assert result.snapshot_path is None
    assert result.pending_receipt_rows_archived == 2
    assert result.total_rows_before == 4
    assert result.error_message is None

    # Journal unmodified.
    assert journal.read_text(encoding="utf-8") == original_text
    # Snapshot dir was not even created (or if created, empty).
    if snapshot_dir.exists():
        assert list(snapshot_dir.iterdir()) == []


def test_execute_writes_snapshot_and_rewrites_journal(tmp_path: Path) -> None:
    journal = tmp_path / "agent-events.jsonl"
    snapshot_dir = tmp_path / "snapshots"
    rows = _sample_rows()
    _write_journal(journal, rows)

    result = archive_stale_receipts(
        journal_path=journal,
        snapshot_dir=snapshot_dir,
        dry_run=False,
        now=NOW,
    )

    assert result.dry_run is False
    assert result.pending_receipt_rows_archived == 2
    assert result.rows_remaining == 2
    assert result.error_message is None
    assert result.snapshot_path is not None

    # Snapshot has meta header + 2 archived rows.
    snapshot_path = Path(result.snapshot_path)
    assert snapshot_path.exists()
    snapshot_rows = _read_jsonl(snapshot_path)
    assert len(snapshot_rows) == 3
    assert "_archive_meta" in snapshot_rows[0]
    assert snapshot_rows[0]["_archive_meta"]["count"] == 2
    archived_ids = {row["id"] for row in snapshot_rows[1:]}
    assert archived_ids == {"row-0-stale", "row-3-stale"}

    # Journal rewritten preserving non-archived rows in original order.
    remaining = _read_jsonl(journal)
    assert [row["id"] for row in remaining] == ["row-1-kept", "row-2-kept-mt5"]


def test_archive_is_idempotent(tmp_path: Path) -> None:
    journal = tmp_path / "agent-events.jsonl"
    snapshot_dir = tmp_path / "snapshots"
    _write_journal(journal, _sample_rows())

    first = archive_stale_receipts(
        journal_path=journal,
        snapshot_dir=snapshot_dir,
        dry_run=False,
        now=NOW,
    )
    assert first.pending_receipt_rows_archived == 2

    # Second run on already-cleaned journal — nothing to archive.
    second = archive_stale_receipts(
        journal_path=journal,
        snapshot_dir=snapshot_dir,
        dry_run=False,
        now=NOW,
    )
    assert second.pending_receipt_rows_archived == 0
    assert second.error_message is None
    # Second run should not produce a new snapshot since count is zero.
    assert second.snapshot_path is None


def test_nonexistent_journal_returns_error_no_exception(tmp_path: Path) -> None:
    missing_journal = tmp_path / "does-not-exist.jsonl"
    snapshot_dir = tmp_path / "snapshots"

    result = archive_stale_receipts(
        journal_path=missing_journal,
        snapshot_dir=snapshot_dir,
        dry_run=False,
        now=NOW,
    )

    assert result.error_message is not None
    assert "does not exist" in result.error_message
    assert result.pending_receipt_rows_archived == 0
    assert result.snapshot_path is None
    # Snapshot dir was not created.
    assert not snapshot_dir.exists()
