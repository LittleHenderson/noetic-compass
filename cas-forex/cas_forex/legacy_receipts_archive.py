"""Archive stale legacy MT4 RECEIPT_PENDING rows from the agent events journal.

The supervisor's `pending_receipt_count` and the operability cockpit's
`cas_open_position_count_legacy_total` are inflated by stale RECEIPT_PENDING
rows for an MT4 lane the operator never actually ran. The lane-aware reporting
hides them from active totals, but the legacy_total still surfaces them.

This module provides a SAFE, idempotent way to:

  1. Identify which rows in the journal qualify as stale (pure function).
  2. Archive them to a snapshot file and rewrite the journal without them
     (I/O function). Default is dry_run so the operator previews first.

Conservative identification rules:
  * Row's `kind` (or `event_kind`) must equal `"RECEIPT_PENDING"`.
  * Row's broker_mode (top-level, or nested under `command`/`intent`) must
    contain "MT4" case-insensitively. Rows with no broker_mode are NOT stale.
  * Row's timestamp (`created_at`/`created_at_iso`/`timestamp`) must be older
    than `now - age_threshold_hours`. Rows with no parseable timestamp are
    NOT stale.

The I/O sequence is "snapshot-first": the snapshot is written and fsynced
before the journal is rewritten via temp-file-and-rename. On any I/O error,
no destructive change is made and `error_message` is populated.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class LegacyReceiptArchiveResult:
    journal_path: str
    snapshot_path: str | None
    total_rows_before: int
    pending_receipt_rows_archived: int
    rows_remaining: int
    archived_at_iso: str
    dry_run: bool
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pure identification
# ---------------------------------------------------------------------------


def _extract_kind(event: Mapping[str, Any]) -> str | None:
    kind = event.get("kind")
    if isinstance(kind, str):
        return kind
    event_kind = event.get("event_kind")
    if isinstance(event_kind, str):
        return event_kind
    return None


def _extract_broker_mode(event: Mapping[str, Any]) -> str | None:
    candidates = [event.get("broker_mode")]
    for nested_key in ("command", "intent"):
        nested = event.get(nested_key)
        if isinstance(nested, Mapping):
            candidates.append(nested.get("broker_mode"))
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _extract_timestamp(event: Mapping[str, Any]) -> datetime | None:
    for key in ("created_at", "created_at_iso", "timestamp"):
        raw = event.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        text = raw.strip()
        # Normalize trailing Z to +00:00 for fromisoformat compatibility.
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def identify_stale_pending_receipts(
    events: Sequence[Mapping[str, Any]],
    *,
    age_threshold_hours: float = 24.0,
    now: datetime | None = None,
) -> tuple[int, ...]:
    """Return sorted indices of MT4 RECEIPT_PENDING rows older than threshold.

    Pure. No I/O. Conservative — anything ambiguous is left alone.
    """

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    cutoff = now - timedelta(hours=age_threshold_hours)
    stale: list[int] = []

    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            continue
        kind = _extract_kind(event)
        if kind != "RECEIPT_PENDING":
            continue
        broker_mode = _extract_broker_mode(event)
        if broker_mode is None or "MT4" not in broker_mode.upper():
            continue
        timestamp = _extract_timestamp(event)
        if timestamp is None:
            continue
        if timestamp >= cutoff:
            continue
        stale.append(index)

    return tuple(stale)


# ---------------------------------------------------------------------------
# I/O archive operation
# ---------------------------------------------------------------------------


def _read_journal(journal_path: Path) -> tuple[list[Mapping[str, Any]], list[str]]:
    """Return (parsed_rows, raw_lines_preserved).

    `raw_lines_preserved` keeps the exact textual form for rows we did not
    parse, so a rewrite preserves operator content we don't understand. For
    parsed rows we re-serialize with json.dumps so the file stays canonical.
    """

    parsed: list[Mapping[str, Any]] = []
    raw_lines: list[str] = []
    with journal_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if not stripped:
                # Preserve blank lines as None markers; they will be skipped on
                # rewrite (canonical JSONL has no blanks).
                parsed.append({})
                raw_lines.append("")
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                # Unparseable line — keep raw, will be re-emitted verbatim.
                parsed.append({"_unparsed": True})
                raw_lines.append(stripped)
                continue
            if not isinstance(row, Mapping):
                parsed.append({"_unparsed": True})
                raw_lines.append(stripped)
                continue
            parsed.append(row)
            raw_lines.append(stripped)

    return parsed, raw_lines


def _write_snapshot(
    snapshot_path: Path,
    *,
    archived_rows: Sequence[Mapping[str, Any]],
    journal_path: Path,
    archived_at_iso: str,
) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "_archive_meta": {
            "journal_path": str(journal_path),
            "archived_at_iso": archived_at_iso,
            "count": len(archived_rows),
        }
    }
    with snapshot_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(meta, sort_keys=True) + "\n")
        for row in archived_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            # fsync is best-effort on some platforms (e.g., Windows tmp dirs).
            pass


def _atomic_rewrite_journal(
    journal_path: Path,
    *,
    kept_lines: Sequence[str],
) -> None:
    fd, tmp_name = tempfile.mkstemp(
        prefix=journal_path.name + ".",
        suffix=".tmp",
        dir=str(journal_path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for line in kept_lines:
                if line == "":
                    continue
                handle.write(line + "\n")
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(tmp_name, journal_path)
    except Exception:
        # Best-effort cleanup; original journal remains untouched.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def archive_stale_receipts(
    *,
    journal_path: Path,
    snapshot_dir: Path,
    dry_run: bool = True,
    age_threshold_hours: float = 24.0,
    now: datetime | None = None,
) -> LegacyReceiptArchiveResult:
    """Archive stale MT4 RECEIPT_PENDING rows out of the journal.

    Default is dry_run — no files are written or rewritten and the result
    reports what WOULD have been archived. With dry_run=False, the snapshot
    is written first, then the journal is rewritten atomically (temp file +
    rename). Idempotent: re-running against a clean journal reports zero.
    """

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    archived_at_iso = now.astimezone(timezone.utc).isoformat()

    journal_path = Path(journal_path)
    snapshot_dir = Path(snapshot_dir)

    if not journal_path.exists():
        return LegacyReceiptArchiveResult(
            journal_path=str(journal_path),
            snapshot_path=None,
            total_rows_before=0,
            pending_receipt_rows_archived=0,
            rows_remaining=0,
            archived_at_iso=archived_at_iso,
            dry_run=dry_run,
            error_message=f"journal_path does not exist: {journal_path}",
        )

    try:
        parsed_rows, raw_lines = _read_journal(journal_path)
    except OSError as exc:
        return LegacyReceiptArchiveResult(
            journal_path=str(journal_path),
            snapshot_path=None,
            total_rows_before=0,
            pending_receipt_rows_archived=0,
            rows_remaining=0,
            archived_at_iso=archived_at_iso,
            dry_run=dry_run,
            error_message=f"failed to read journal: {exc}",
        )

    total_rows_before = sum(1 for line in raw_lines if line != "")

    # Identify stale indices using only the well-formed rows (unparsed ones
    # have the _unparsed sentinel and will never match).
    stale_indices = set(
        identify_stale_pending_receipts(
            parsed_rows,
            age_threshold_hours=age_threshold_hours,
            now=now,
        )
    )
    archived_rows = [parsed_rows[i] for i in sorted(stale_indices)]
    pending_receipt_rows_archived = len(archived_rows)

    kept_lines = [
        raw_line
        for index, raw_line in enumerate(raw_lines)
        if index not in stale_indices and raw_line != ""
    ]
    rows_remaining = len(kept_lines)

    if dry_run:
        return LegacyReceiptArchiveResult(
            journal_path=str(journal_path),
            snapshot_path=None,
            total_rows_before=total_rows_before,
            pending_receipt_rows_archived=pending_receipt_rows_archived,
            rows_remaining=total_rows_before - pending_receipt_rows_archived,
            archived_at_iso=archived_at_iso,
            dry_run=True,
            error_message=None,
        )

    snapshot_filename = f"legacy-mt4-receipts-archive-{archived_at_iso}.jsonl"
    # ISO timestamps contain ":" which is invalid in Windows filenames.
    snapshot_filename = snapshot_filename.replace(":", "-")
    snapshot_path = snapshot_dir / snapshot_filename

    if pending_receipt_rows_archived == 0:
        # Nothing to archive — skip snapshot write entirely. Still idempotent.
        return LegacyReceiptArchiveResult(
            journal_path=str(journal_path),
            snapshot_path=None,
            total_rows_before=total_rows_before,
            pending_receipt_rows_archived=0,
            rows_remaining=total_rows_before,
            archived_at_iso=archived_at_iso,
            dry_run=False,
            error_message=None,
        )

    try:
        _write_snapshot(
            snapshot_path,
            archived_rows=archived_rows,
            journal_path=journal_path,
            archived_at_iso=archived_at_iso,
        )
    except OSError as exc:
        return LegacyReceiptArchiveResult(
            journal_path=str(journal_path),
            snapshot_path=None,
            total_rows_before=total_rows_before,
            pending_receipt_rows_archived=0,
            rows_remaining=total_rows_before,
            archived_at_iso=archived_at_iso,
            dry_run=False,
            error_message=f"failed to write snapshot: {exc}",
        )

    try:
        _atomic_rewrite_journal(journal_path, kept_lines=kept_lines)
    except OSError as exc:
        # Snapshot exists but journal was not modified — operator still safe.
        return LegacyReceiptArchiveResult(
            journal_path=str(journal_path),
            snapshot_path=str(snapshot_path),
            total_rows_before=total_rows_before,
            pending_receipt_rows_archived=0,
            rows_remaining=total_rows_before,
            archived_at_iso=archived_at_iso,
            dry_run=False,
            error_message=f"failed to rewrite journal (snapshot preserved): {exc}",
        )

    return LegacyReceiptArchiveResult(
        journal_path=str(journal_path),
        snapshot_path=str(snapshot_path),
        total_rows_before=total_rows_before,
        pending_receipt_rows_archived=pending_receipt_rows_archived,
        rows_remaining=rows_remaining,
        archived_at_iso=archived_at_iso,
        dry_run=False,
        error_message=None,
    )


__all__ = [
    "LegacyReceiptArchiveResult",
    "identify_stale_pending_receipts",
    "archive_stale_receipts",
]
