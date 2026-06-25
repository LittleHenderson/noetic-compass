"""Append-only operator audit log primitive.

Operator-side state changes today happen across many different surfaces
(strategy promote/demote/reject/archive, Fury promotions, runtime gate
flips, dev-queue actions, notification subscribe/unsubscribe, legacy
receipts archive, etc.). Each surface persists its OWN evidence file;
there is no single chronological view of "what did I, the operator,
DO today / yesterday / this week."

This module ships that view as a primitive: an append-only JSONL log
of :class:`OperatorAuditEntry` records, plus pure read APIs over it.

Framing (observational, never advisory):
    Audit entries describe WHAT HAPPENED. They MUST NOT include trade-pick
    or recommendation language ("you should...", "we recommend...",
    "good entry", "buy now"). Construction enforces this at
    :meth:`OperatorAuditLog.append` time via
    ``OBSERVATIONAL_GUARD_PHRASES`` — case-insensitive substring match
    on the ``summary`` field. The architectural commitment is that call
    sites never write advisory summaries; the guard is a regression
    backstop.

Storage:
    Entries are persisted as JSONL at
    ``evidence_runs/operator_audit/operator-audit.jsonl``. Writes are
    APPEND-ONLY: each :meth:`append` opens the file in append mode,
    writes one JSON line, flushes and fsyncs the file descriptor, then
    closes. Prior entries are NEVER rewritten — the file grows
    monotonically. If the underlying I/O raises mid-append the entry
    is NOT persisted and the exception propagates; the file remains
    in its prior state.

Concurrency:
    The append path assumes a single writer process. The cockpit API
    runs as a single uvicorn worker today. Multi-worker deployment
    needs a file lock or a SQLite/Redis backend; that is out of scope.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


# ---------------------------------------------------------------------------
# Action kinds — closed enum (string values, not Python ``Enum`` so JSON
# round-trips trivially).
# ---------------------------------------------------------------------------


ACTION_KINDS: tuple[str, ...] = (
    "STRATEGY_PROMOTED",
    "STRATEGY_DEMOTED",
    "STRATEGY_REJECTED",
    "STRATEGY_ARCHIVED",
    "STRATEGY_REVIEWED",
    "FOREX_FURY_PROMOTED",
    "RUNTIME_GATE_FLIP",
    "NOTIFICATION_SUBSCRIBED",
    "NOTIFICATION_UNSUBSCRIBED",
    "WEBHOOK_SUBSCRIBED",
    "WEBHOOK_UNSUBSCRIBED",
    "LEGACY_RECEIPTS_ARCHIVED",
    "OTHER",
)


# ---------------------------------------------------------------------------
# Observational guard phrases
# ---------------------------------------------------------------------------


# Substring matches (case-insensitive) on the ``summary`` field. Every
# phrase here would betray trade-advisory framing — audit log is
# OBSERVATIONAL: it records what HAPPENED, never what to do next.
OBSERVATIONAL_GUARD_PHRASES: tuple[str, ...] = (
    "you should",
    "should have",
    "we recommend",
    "good entry",
    "buy now",
    "sell now",
    "consider closing",
    "is a good",
)


GUARD_PHRASE_ERROR_MESSAGE = "advisory phrase in summary"


# ---------------------------------------------------------------------------
# Defaults / paths
# ---------------------------------------------------------------------------


DEFAULT_LOG_DIR = Path("evidence_runs") / "operator_audit"
DEFAULT_LOG_FILENAME = "operator-audit.jsonl"


# ---------------------------------------------------------------------------
# Data shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperatorAuditEntry:
    """One operator-initiated state-change record.

    ``entry_id`` is deterministic from
    ``action_kind | target_id | recorded_at_iso`` (sha256 truncated to
    16 hex chars). Same triple → same id; this lets callers dedupe
    on retry without coordinating sequence numbers.

    ``payload`` is a free-form structured field; the contract is that
    every value JSON-serializes. The constructor coerces the mapping
    to a plain ``dict``.

    ``reversible`` is True for actions that can be undone by a single
    counter-action (queue ENQUEUE, gate FLIP, notification SUBSCRIBE);
    False for snapshot / destructive actions (LEGACY_RECEIPTS_ARCHIVED,
    STRATEGY_ARCHIVED). ``reversal_hint`` is a single-sentence FACTUAL
    description of the inverse step (e.g., "Re-promote via
    /api/forex/strategy-dev-actions/promote") — observational, not
    advisory.
    """

    entry_id: str
    action_kind: str
    actor: str
    target_id: Optional[str]
    target_label: Optional[str]
    summary: str
    payload: Mapping[str, Any]
    recorded_at_iso: str
    reversible: bool
    reversal_hint: Optional[str]

    def to_jsonl_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "action_kind": self.action_kind,
            "actor": self.actor,
            "target_id": self.target_id,
            "target_label": self.target_label,
            "summary": self.summary,
            "payload": dict(self.payload),
            "recorded_at_iso": self.recorded_at_iso,
            "reversible": bool(self.reversible),
            "reversal_hint": self.reversal_hint,
        }

    @classmethod
    def from_jsonl_dict(cls, payload: dict) -> "OperatorAuditEntry":
        raw_payload = payload.get("payload") or {}
        if not isinstance(raw_payload, Mapping):
            raw_payload = {}
        target_id = payload.get("target_id")
        target_label = payload.get("target_label")
        reversal_hint = payload.get("reversal_hint")
        return cls(
            entry_id=str(payload["entry_id"]),
            action_kind=str(payload.get("action_kind", "OTHER") or "OTHER"),
            actor=str(payload.get("actor", "operator") or "operator"),
            target_id=str(target_id) if target_id else None,
            target_label=str(target_label) if target_label else None,
            summary=str(payload.get("summary", "") or ""),
            payload=dict(raw_payload),
            recorded_at_iso=str(payload.get("recorded_at_iso", "")),
            reversible=bool(payload.get("reversible", False)),
            reversal_hint=str(reversal_hint) if reversal_hint else None,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow_iso(when: Optional[datetime] = None) -> str:
    if when is None:
        when = datetime.now(tz=timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _entry_id(action_kind: str, target_id: Optional[str], recorded_at_iso: str) -> str:
    raw = f"{action_kind}|{target_id or ''}|{recorded_at_iso}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _contains_guard_phrase(summary: str) -> Optional[str]:
    """Return the first guard phrase substring found in ``summary`` (lower
    case match), or None when the summary is clean."""
    if not isinstance(summary, str):
        return None
    haystack = summary.lower()
    for phrase in OBSERVATIONAL_GUARD_PHRASES:
        if phrase in haystack:
            return phrase
    return None


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_entry(
    *,
    action_kind: str,
    summary: str,
    actor: str = "operator",
    target_id: Optional[str] = None,
    target_label: Optional[str] = None,
    payload: Optional[Mapping[str, Any]] = None,
    reversible: bool = False,
    reversal_hint: Optional[str] = None,
    when: Optional[datetime] = None,
) -> OperatorAuditEntry:
    """Construct an :class:`OperatorAuditEntry`, assigning a deterministic
    ``entry_id`` from ``(action_kind, target_id, recorded_at_iso)``.

    Unknown ``action_kind`` values are accepted but will fall outside the
    closed :data:`ACTION_KINDS` enum — callers SHOULD prefer ``"OTHER"``
    over a free-form string. Validation of ``summary`` against the guard
    phrases happens at :meth:`OperatorAuditLog.append` time, not here:
    builders are pure and let the log decide whether to persist.
    """
    recorded = _utcnow_iso(when)
    return OperatorAuditEntry(
        entry_id=_entry_id(action_kind, target_id, recorded),
        action_kind=str(action_kind),
        actor=str(actor or "operator"),
        target_id=str(target_id) if target_id else None,
        target_label=str(target_label) if target_label else None,
        summary=str(summary or ""),
        payload=dict(payload or {}),
        recorded_at_iso=recorded,
        reversible=bool(reversible),
        reversal_hint=str(reversal_hint) if reversal_hint else None,
    )


# ---------------------------------------------------------------------------
# Append-only file log
# ---------------------------------------------------------------------------


class OperatorAuditLog:
    """Append-only JSONL log of :class:`OperatorAuditEntry` records.

    Append semantics: every :meth:`append` opens the file in append mode,
    writes one JSON line, flushes the Python buffer, fsyncs the OS-level
    file descriptor, then closes. Prior entries are NEVER overwritten.
    If the write raises (disk full, permission error) the file is left
    in its prior state and the entry is NOT considered persisted; the
    exception propagates so the caller can react.

    Read APIs are pure (no mutation), tolerate corrupt lines by skipping
    them, and return entries in NEWEST-FIRST order.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = (
            Path(path)
            if path is not None
            else (DEFAULT_LOG_DIR / DEFAULT_LOG_FILENAME)
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # -- introspection ------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    # -- mutate -------------------------------------------------------------

    def append(self, entry: OperatorAuditEntry) -> OperatorAuditEntry:
        """Append ``entry`` to the log. Validates ``summary`` against
        :data:`OBSERVATIONAL_GUARD_PHRASES` (case-insensitive substring
        match) and raises :class:`ValueError` if any guard phrase is
        present — the entry is NOT written in that case.

        Raises any I/O exception raised by the underlying write; the
        file is left in its prior state on failure.
        """
        offending = _contains_guard_phrase(entry.summary)
        if offending is not None:
            raise ValueError(f"{GUARD_PHRASE_ERROR_MESSAGE}: {offending!r}")

        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry.to_jsonl_dict(), ensure_ascii=False) + "\n"
        # Append-only: open with "a", write, flush + fsync, close.
        fh = open(self._path, "a", encoding="utf-8")
        try:
            fh.write(line)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:  # pragma: no cover - fsync may be unsupported
                pass
        finally:
            fh.close()
        return entry

    # -- read ---------------------------------------------------------------

    def _read_all(self) -> list[OperatorAuditEntry]:
        if not self._path.exists():
            return []
        entries: list[OperatorAuditEntry] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                try:
                    entries.append(OperatorAuditEntry.from_jsonl_dict(payload))
                except (KeyError, TypeError):
                    continue
        return entries

    def list_recent(
        self,
        *,
        limit: int = 50,
        since_iso: Optional[str] = None,
        action_kinds: Optional[Sequence[str]] = None,
    ) -> list[OperatorAuditEntry]:
        """Return up to ``limit`` entries in newest-first order.

        ``since_iso`` is an ISO-8601 timestamp; entries with
        ``recorded_at_iso`` strictly less than ``since_iso`` are dropped
        (lexicographic comparison — safe because all timestamps are
        normalised to UTC with the same offset suffix).

        ``action_kinds`` is an optional whitelist; entries whose
        ``action_kind`` is not in the set are dropped.
        """
        if limit < 0:
            limit = 0
        all_entries = self._read_all()
        kinds_set: Optional[set[str]] = (
            {str(k) for k in action_kinds} if action_kinds else None
        )

        filtered: list[OperatorAuditEntry] = []
        for entry in all_entries:
            if since_iso is not None and entry.recorded_at_iso < since_iso:
                continue
            if kinds_set is not None and entry.action_kind not in kinds_set:
                continue
            filtered.append(entry)

        # Newest first: sort by recorded_at_iso descending, then entry_id
        # as deterministic tiebreaker.
        filtered.sort(
            key=lambda e: (e.recorded_at_iso, e.entry_id),
            reverse=True,
        )
        return filtered[:limit] if limit else filtered

    def count_by_kind(
        self,
        *,
        since_iso: Optional[str] = None,
    ) -> dict[str, int]:
        """Tally of entries grouped by ``action_kind``. Optional
        ``since_iso`` cutoff matches :meth:`list_recent` semantics."""
        counts: dict[str, int] = {}
        for entry in self._read_all():
            if since_iso is not None and entry.recorded_at_iso < since_iso:
                continue
            counts[entry.action_kind] = counts.get(entry.action_kind, 0) + 1
        return counts

    def stats(
        self,
        *,
        since_iso: Optional[str] = None,
    ) -> dict[str, Any]:
        """Summary statistics over the (optionally bounded) log window.

        Returns the keys: ``total``, ``by_kind``, ``oldest_at_iso``,
        ``newest_at_iso``, ``reversible_count``. When the window is
        empty, ``oldest_at_iso`` and ``newest_at_iso`` are None and
        the counts are 0 / {}.
        """
        all_entries = self._read_all()
        if since_iso is not None:
            all_entries = [
                e for e in all_entries if e.recorded_at_iso >= since_iso
            ]
        if not all_entries:
            return {
                "total": 0,
                "by_kind": {},
                "oldest_at_iso": None,
                "newest_at_iso": None,
                "reversible_count": 0,
            }
        by_kind: dict[str, int] = {}
        reversible_count = 0
        timestamps: list[str] = []
        for entry in all_entries:
            by_kind[entry.action_kind] = by_kind.get(entry.action_kind, 0) + 1
            if entry.reversible:
                reversible_count += 1
            timestamps.append(entry.recorded_at_iso)
        return {
            "total": len(all_entries),
            "by_kind": by_kind,
            "oldest_at_iso": min(timestamps),
            "newest_at_iso": max(timestamps),
            "reversible_count": reversible_count,
        }


__all__ = [
    "ACTION_KINDS",
    "DEFAULT_LOG_DIR",
    "DEFAULT_LOG_FILENAME",
    "GUARD_PHRASE_ERROR_MESSAGE",
    "OBSERVATIONAL_GUARD_PHRASES",
    "OperatorAuditEntry",
    "OperatorAuditLog",
    "build_entry",
]
