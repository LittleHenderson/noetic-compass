"""HTTP routes for the operator audit log.

The audit log is an append-only chronological record of operator-side
state changes — strategy promote/demote/reject, Fury promotion, runtime
gate flips, queue actions, subscription changes. Today those actions
land in separate evidence files; this route surfaces a single ordered
view.

This slice ships the route as a standalone primitive:

- ``GET  /entries``  — list (newest first), with ``since_iso`` and
  repeatable ``action_kind`` query filters.
- ``GET  /stats``    — aggregate summary (total / by_kind / oldest /
  newest / reversible_count).
- ``POST /record``   — append an entry. The other endpoints
  (strategy-dev-actions, fury-promote, etc.) will call into the
  underlying log in a follow-on slice; this POST route exists so the
  operator can record an action manually today.

Framing (observational, never advisory):
    The route refuses any ``summary`` that matches the audit module's
    observational guard phrases — 400 with a documented error code.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from cas_forex.operator_audit import (
    OperatorAuditEntry,
    OperatorAuditLog,
    build_entry,
)


router = APIRouter()


# ---------------------------------------------------------------------------
# Module-level singleton log + test-injection hooks
# ---------------------------------------------------------------------------


_LOG: OperatorAuditLog = OperatorAuditLog()


def get_log() -> OperatorAuditLog:
    return _LOG


def set_log_for_testing(log: OperatorAuditLog) -> None:
    """Replace the process-singleton log. Tests only."""
    global _LOG
    _LOG = log


def reset_log_for_testing() -> None:
    """Reset to a default log rooted at the default JSONL path. Tests only."""
    global _LOG
    _LOG = OperatorAuditLog()


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------


class RecordRequest(BaseModel):
    action_kind: Optional[str] = None
    summary: Optional[str] = None
    actor: Optional[str] = None
    target_id: Optional[str] = None
    target_label: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    reversible: Optional[bool] = None
    reversal_hint: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_entry(entry: OperatorAuditEntry) -> Dict[str, Any]:
    return {
        "entry_id": entry.entry_id,
        "action_kind": entry.action_kind,
        "actor": entry.actor,
        "target_id": entry.target_id,
        "target_label": entry.target_label,
        "summary": entry.summary,
        "payload": dict(entry.payload),
        "recorded_at_iso": entry.recorded_at_iso,
        "reversible": entry.reversible,
        "reversal_hint": entry.reversal_hint,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/entries")
async def list_entries(
    limit: int = Query(50, ge=0, le=1000),
    since_iso: Optional[str] = Query(None),
    action_kind: Optional[List[str]] = Query(None),
) -> Dict[str, Any]:
    """Return up to ``limit`` audit entries in newest-first order.

    ``action_kind`` is repeatable as a query parameter; when supplied,
    only entries whose ``action_kind`` matches one of the values are
    returned.
    """
    log = get_log()
    entries = log.list_recent(
        limit=limit,
        since_iso=since_iso,
        action_kinds=action_kind,
    )
    return {
        "entries": [_serialize_entry(e) for e in entries],
        "count": len(entries),
        "limit": limit,
        "since_iso": since_iso,
        "action_kinds": action_kind,
    }


@router.get("/stats")
async def get_stats(
    since_iso: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Aggregate summary of the audit log over an optional window."""
    log = get_log()
    return dict(log.stats(since_iso=since_iso))


@router.post("/record")
async def record_entry(body: RecordRequest) -> Dict[str, Any]:
    """Append a single audit entry. Used by the cockpit when the operator
    manually records an action. 400 on missing required fields or when
    the summary matches an observational guard phrase."""
    if not body.action_kind:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_field",
                "message": "action_kind is required",
            },
        )
    if not body.summary:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_field",
                "message": "summary is required",
            },
        )

    entry = build_entry(
        action_kind=body.action_kind,
        summary=body.summary,
        actor=body.actor or "operator",
        target_id=body.target_id,
        target_label=body.target_label,
        payload=body.payload or {},
        reversible=bool(body.reversible) if body.reversible is not None else False,
        reversal_hint=body.reversal_hint,
    )

    log = get_log()
    try:
        log.append(entry)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "advisory_phrase",
                "message": str(exc),
            },
        ) from exc

    return {"entry": _serialize_entry(entry)}
