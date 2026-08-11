"""Archive stale legacy MT4 paper commands from the agent events journal.

The supervisor's `pending_receipt_count` and the operability cockpit's
`cas_open_position_count_legacy_total` are inflated by stale RECEIPT_PENDING
rows for an MT4 lane the operator never actually ran. The lane-aware reporting
hides them from active totals, but the legacy_total still surfaces them.

This module provides a SAFE, idempotent way to:

  1. Identify which rows in the journal qualify as stale (pure function).
  2. Archive them to a snapshot file and rewrite the journal without them
     (I/O function). Default is dry_run so the operator previews first.

Conservative identification rules:
  * Legacy receipt-pending rows remain eligible under their historical rules.
  * A `TERMINAL_COMMAND_WRITTEN` row is eligible only when its nested payload
    explicitly identifies a paper/demo MT4 lane and `live_money_authorized` is
    false.
  * A command or pending row with any terminal receipt successor is preserved.
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
    command_files_identified: int = 0
    command_files_quarantined: int = 0
    command_quarantine_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LegacyMailboxCommandArchiveResult:
    command_dir: str
    snapshot_path: str | None
    command_files_identified: int
    command_files_quarantined: int
    command_quarantine_dir: str | None
    archived_at_iso: str
    dry_run: bool
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pure identification
# ---------------------------------------------------------------------------


def _extract_kind(event: Mapping[str, Any]) -> str | None:
    # The journal historically used `kind` / `event_kind`; the live agent
    # cycle writes `event_type`. Check all three so the identifier matches
    # the actual on-disk shape regardless of producer vintage.
    for field in ("kind", "event_kind", "event_type"):
        value = event.get(field)
        if isinstance(value, str):
            return value
    return None


def _extract_broker_mode(event: Mapping[str, Any]) -> str | None:
    candidates = [event.get("broker_mode")]
    for nested_key in ("command", "intent", "payload"):
        nested = event.get(nested_key)
        if isinstance(nested, Mapping):
            candidates.append(nested.get("broker_mode"))
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _extract_command_id(event: Mapping[str, Any]) -> str | None:
    candidates = [event.get("command_id")]
    payload = event.get("payload")
    if isinstance(payload, Mapping):
        candidates.append(payload.get("command_id"))
    candidates.extend((event.get("correlation_id"), event.get("subject")))
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_live_money_authorized(event: Mapping[str, Any]) -> bool | None:
    candidates = [event.get("live_money_authorized")]
    payload = event.get("payload")
    if isinstance(payload, Mapping):
        candidates.append(payload.get("live_money_authorized"))
    for value in candidates:
        if isinstance(value, bool):
            return value
    return None


def _receipt_successor_command_ids(events: Sequence[Mapping[str, Any]]) -> set[str]:
    successor_types = {
        "TERMINAL_RECEIPT_RECEIVED",
        "TERMINAL_RECEIPT_MISMATCH",
        "TERMINAL_RECEIPT_RECONCILED",
        "NEXT_CYCLE_ALLOWED",
    }
    successor_statuses = {"RECEIPT_VERIFIED", "RECONCILED", "NEXT_CYCLE_ALLOWED"}
    command_ids: set[str] = set()
    for event in events:
        if not isinstance(event, Mapping):
            continue
        if _extract_kind(event) not in successor_types and str(event.get("status") or "") not in successor_statuses:
            continue
        command_id = _extract_command_id(event)
        if command_id:
            command_ids.add(command_id)
    return command_ids


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
    """Return indices of expired, unresolved MT4 paper command-chain rows.

    Pure. No I/O. Conservative — anything ambiguous is left alone.
    """

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    cutoff = now - timedelta(hours=age_threshold_hours)
    stale: list[int] = []
    closed_command_ids = _receipt_successor_command_ids(events)

    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            continue
        kind = _extract_kind(event)
        command_id = _extract_command_id(event)
        if command_id and command_id in closed_command_ids:
            continue
        if kind == "RECEIPT_PENDING":
            # Legacy strict path: bare RECEIPT_PENDING events MUST carry an
            # MT4 broker_mode marker. Conservative — anything ambiguous is
            # left alone.
            broker_mode = _extract_broker_mode(event)
            if broker_mode is None or "MT4" not in broker_mode.upper():
                continue
        elif kind == "TERMINAL_RECEIPT_PENDING":
            # The live agent cycle writes TERMINAL_RECEIPT_PENDING with no
            # top-level broker_mode; the lane is implicit in the
            # consumer_agent_ids ("mt4_or_mt5_terminal"). These rows are
            # only archived via the age threshold below — a stale terminal
            # receipt is one that's been waiting >24h with no successor
            # event ever ack'ing it, regardless of which lane was intended.
            broker_mode = _extract_broker_mode(event)
            if broker_mode is not None and "MT4" not in broker_mode.upper():
                continue
        elif kind == "TERMINAL_COMMAND_WRITTEN":
            broker_mode = _extract_broker_mode(event)
            normalized_mode = str(broker_mode or "").upper()
            if "MT4" not in normalized_mode or not any(token in normalized_mode for token in ("PAPER", "DEMO")):
                continue
            if _extract_live_money_authorized(event) is not False:
                continue
            if not command_id:
                continue
        else:
            continue
        timestamp = _extract_timestamp(event)
        if timestamp is None:
            continue
        if timestamp >= cutoff:
            continue
        stale.append(index)

    return tuple(stale)


def _command_paths_for_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[Path, ...]:
    paths: list[Path] = []
    seen: set[str] = set()
    for row in rows:
        if _extract_kind(row) != "TERMINAL_COMMAND_WRITTEN":
            continue
        payload = row.get("payload")
        raw_path = payload.get("command_path") if isinstance(payload, Mapping) else None
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        path = Path(raw_path).expanduser().resolve()
        normalized = os.path.normcase(str(path))
        if normalized in seen:
            continue
        seen.add(normalized)
        paths.append(path)
    return tuple(paths)


def _quarantine_command_files(
    paths: Sequence[Path],
    *,
    allowed_root: Path,
    quarantine_dir: Path,
) -> tuple[int, str | None]:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return 0, None

    allowed_root = allowed_root.resolve()
    for path in existing:
        try:
            path.relative_to(allowed_root)
        except ValueError:
            return 0, f"refusing to quarantine command outside evidence root: {path}"
        if not path.is_file() or path.suffix.lower() != ".json":
            return 0, f"refusing to quarantine non-JSON command artifact: {path}"

    quarantine_dir.mkdir(parents=True, exist_ok=True)
    moved: list[tuple[Path, Path]] = []
    try:
        for source in existing:
            destination = quarantine_dir / source.name
            if destination.exists():
                destination = quarantine_dir / f"{source.stem}-{len(moved) + 1}{source.suffix}"
            os.replace(source, destination)
            moved.append((source, destination))
    except OSError as exc:
        for source, destination in reversed(moved):
            try:
                os.replace(destination, source)
            except OSError:
                pass
        return 0, f"failed to quarantine stale command artifact: {exc}"
    return len(moved), None


def archive_stale_mailbox_commands(
    *,
    command_dir: Path,
    receipt_dir: Path,
    snapshot_dir: Path,
    dry_run: bool = True,
    age_threshold_hours: float = 24.0,
    now: datetime | None = None,
) -> LegacyMailboxCommandArchiveResult:
    """Archive expired paper MT4 command files that predate the journal."""

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    archived_at_iso = now.astimezone(timezone.utc).isoformat()
    cutoff = now - timedelta(hours=age_threshold_hours)
    command_dir = Path(command_dir).expanduser().resolve()
    receipt_dir = Path(receipt_dir).expanduser().resolve()
    snapshot_dir = Path(snapshot_dir).expanduser().resolve()

    receipt_command_ids: set[str] = set()
    if receipt_dir.exists():
        for path in receipt_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, Mapping):
                command_id = _extract_command_id(payload)
                if command_id:
                    receipt_command_ids.add(command_id)

    eligible_paths: list[Path] = []
    eligible_rows: list[Mapping[str, Any]] = []
    if command_dir.exists():
        for path in sorted(command_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, Mapping):
                continue
            broker_mode = str(_extract_broker_mode(payload) or "").upper()
            command_id = _extract_command_id(payload)
            created_at = _extract_timestamp(payload)
            if "MT4" not in broker_mode or not any(token in broker_mode for token in ("PAPER", "DEMO")):
                continue
            if _extract_live_money_authorized(payload) is not False:
                continue
            if not command_id or command_id in receipt_command_ids:
                continue
            if created_at is None or created_at >= cutoff:
                continue
            eligible_paths.append(path)
            eligible_rows.append({**dict(payload), "archived_source_command_path": str(path)})

    identified = len(eligible_paths)
    if dry_run or identified == 0:
        return LegacyMailboxCommandArchiveResult(
            command_dir=str(command_dir),
            snapshot_path=None,
            command_files_identified=identified,
            command_files_quarantined=0,
            command_quarantine_dir=None,
            archived_at_iso=archived_at_iso,
            dry_run=dry_run,
            error_message=None,
        )

    snapshot_filename = f"orphaned-mt4-command-archive-{archived_at_iso}.jsonl".replace(":", "-")
    snapshot_path = snapshot_dir / snapshot_filename
    quarantine_dir = snapshot_dir / f"{snapshot_path.stem}-commands"
    try:
        _write_snapshot(
            snapshot_path,
            archived_rows=eligible_rows,
            journal_path=command_dir,
            archived_at_iso=archived_at_iso,
        )
    except OSError as exc:
        return LegacyMailboxCommandArchiveResult(
            command_dir=str(command_dir),
            snapshot_path=None,
            command_files_identified=identified,
            command_files_quarantined=0,
            command_quarantine_dir=None,
            archived_at_iso=archived_at_iso,
            dry_run=False,
            error_message=f"failed to write orphan command snapshot: {exc}",
        )

    quarantined, error = _quarantine_command_files(
        eligible_paths,
        allowed_root=command_dir,
        quarantine_dir=quarantine_dir,
    )
    return LegacyMailboxCommandArchiveResult(
        command_dir=str(command_dir),
        snapshot_path=str(snapshot_path),
        command_files_identified=identified,
        command_files_quarantined=quarantined,
        command_quarantine_dir=str(quarantine_dir) if quarantined else None,
        archived_at_iso=archived_at_iso,
        dry_run=False,
        error_message=error,
    )


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
    command_paths = _command_paths_for_rows(archived_rows)
    command_files_identified = sum(1 for path in command_paths if path.exists())

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
            command_files_identified=command_files_identified,
        )

    snapshot_filename = f"legacy-mt4-receipts-archive-{archived_at_iso}.jsonl"
    # ISO timestamps contain ":" which is invalid in Windows filenames.
    snapshot_filename = snapshot_filename.replace(":", "-")
    snapshot_path = snapshot_dir / snapshot_filename
    command_quarantine_dir = snapshot_dir / f"{snapshot_path.stem}-commands"

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
            command_files_identified=command_files_identified,
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
            command_files_identified=command_files_identified,
        )

    command_files_quarantined, quarantine_error = _quarantine_command_files(
        command_paths,
        allowed_root=journal_path.parent.parent,
        quarantine_dir=command_quarantine_dir,
    )
    if quarantine_error:
        return LegacyReceiptArchiveResult(
            journal_path=str(journal_path),
            snapshot_path=str(snapshot_path),
            total_rows_before=total_rows_before,
            pending_receipt_rows_archived=0,
            rows_remaining=total_rows_before,
            archived_at_iso=archived_at_iso,
            dry_run=False,
            error_message=quarantine_error,
            command_files_identified=command_files_identified,
            command_files_quarantined=0,
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
            command_files_identified=command_files_identified,
            command_files_quarantined=command_files_quarantined,
            command_quarantine_dir=str(command_quarantine_dir) if command_files_quarantined else None,
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
        command_files_identified=command_files_identified,
        command_files_quarantined=command_files_quarantined,
        command_quarantine_dir=str(command_quarantine_dir) if command_files_quarantined else None,
    )


__all__ = [
    "LegacyMailboxCommandArchiveResult",
    "LegacyReceiptArchiveResult",
    "archive_stale_mailbox_commands",
    "identify_stale_pending_receipts",
    "archive_stale_receipts",
]
