"""Durable, cross-operator LESSONS journal.

The current trades are a learning curve. Whatever the operator concludes from
them — "the trailing stop nets worse than holding on M1 scalps", "that US30
SHORT run was a lucky cluster, not edge", "GBP/USD LONG is a chronic loser" —
must OUTLIVE this operator and this session, so future operators inherit the
hard-won knowledge instead of re-deriving (or repeating) it.

Each operator tick reads the accumulated lessons FIRST (they are injected into
its context) and may APPEND a new lesson when it learns something durable. The
journal is append-only and curated: near-duplicate lessons are collapsed, and
the newest supersede stale ones, so the knowledge compounds without bloating.

This module records knowledge only. It never trades, moves money, or changes a
dial — the operator acts through the fenced control surface; lessons just shape
how it (and its successors) reason.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LESSONS_PATH = REPO_ROOT / "runtime" / "operator-lessons.json"

REPORT_KIND = "cas_forex_operator_lessons"
MAX_LESSONS = 120
MAX_LESSON_CHARS = 600

VALID_CATEGORIES = (
    "market",        # a specific symbol/direction/profile behaves a certain way
    "exit_policy",   # trailing stop / take-profit / stop behaviour
    "sizing_risk",   # position sizing, risk, compounding
    "data_quality",  # clustering, survivorship, what to trust
    "edge",          # what does / does not constitute a real edge here
    "general",
)

CLAIM_BOUNDARY = (
    "The operator lessons journal is durable cross-operator knowledge. It records "
    "conclusions only; it never trades, moves money, or changes a dial. Future "
    "operators read it to avoid re-learning the same mistakes."
)

_LOCK = threading.RLock()
_PATH = DEFAULT_LESSONS_PATH
_SEEDED = False

# Founding principles every operator inherits from the start (owner-ratified,
# 2026-07-03). These are the epistemic rules of the desk, not per-trade findings.
FOUNDING_PRINCIPLES = [
    {
        "text": "Nothing here is random — every move has a cause. Never dismiss a profitable pattern as 'luck'. A win that came in a correlated cluster is ONE independent observation copied many times (it overcounts evidence), not a fake signal. Treat it as an UNCONFIRMED, promising lead: keep it and gather INDEPENDENT out-of-sample setups to test whether its cause repeats.",
        "category": "edge",
        "source": "owner_principle",
    },
    {
        "text": "Confirm an edge the same way regardless of how promising it looks: it must keep profiting on NEW independent setups, after real cost, and beat a shuffled null. Cut a market for sustained INDEPENDENT losses — not because a winner arrived in a burst.",
        "category": "edge",
        "source": "owner_principle",
    },
    {
        "text": "The current trades are a learning curve. Record what you learn so future operators inherit it and do not re-derive or repeat mistakes.",
        "category": "general",
        "source": "owner_principle",
    },
]


def seed_founding_principles() -> None:
    """Ensure the founding principles exist (idempotent via near-dup dedup).
    Runs once per process."""
    global _SEEDED
    if _SEEDED:
        return
    try:
        for p in FOUNDING_PRINCIPLES:
            record_lesson(p["text"], category=p["category"], source=p["source"])
        _SEEDED = True
    except Exception:
        pass


def set_lessons_path_for_tests(path: Optional[Path]) -> None:
    global _PATH, _SEEDED
    _PATH = Path(path) if path is not None else DEFAULT_LESSONS_PATH
    _SEEDED = False  # re-seed founding principles into the new (test) store


def _load() -> dict[str, Any]:
    if not _PATH.exists():
        return {"report_kind": REPORT_KIND, "lessons": []}
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"report_kind": REPORT_KIND, "lessons": []}
    if not isinstance(data, dict) or not isinstance(data.get("lessons"), list):
        return {"report_kind": REPORT_KIND, "lessons": []}
    return data


def _save(data: dict[str, Any]) -> None:
    data["report_kind"] = REPORT_KIND
    data["updated_at"] = utc_now().isoformat()
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(_PATH.suffix + ".tmp")
    payload = json.dumps(data, indent=1, sort_keys=True, default=str)
    last_error: OSError | None = None
    for attempt in range(5):
        try:
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(_PATH)
            return
        except OSError as exc:  # transient OneDrive/AV lock
            last_error = exc
            time.sleep(0.2 * (attempt + 1))
    if last_error is not None:
        raise last_error


def _norm(text: str) -> str:
    # Lower-case, strip punctuation, collapse whitespace — so "cluster," and
    # "cluster" match when comparing the leading gist of two lessons.
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in str(text or "").lower())
    return " ".join(cleaned.split())


def _similar(a: str, b: str) -> bool:
    """Cheap near-duplicate check: same leading gist (first ~8 words)."""
    aw = _norm(a).split()[:8]
    bw = _norm(b).split()[:8]
    return bool(aw) and aw == bw


def record_lesson(
    text: str,
    *,
    category: str = "general",
    evidence: str = "",
    source: str = "operator",
) -> Optional[dict[str, Any]]:
    """Append a durable lesson (newest first). Near-duplicates of an existing
    lesson refresh that lesson instead of adding a new row. Returns the stored
    lesson, or None if the text was empty."""
    cleaned = str(text or "").strip()[:MAX_LESSON_CHARS]
    if not cleaned:
        return None
    cat = category if category in VALID_CATEGORIES else "general"
    lesson = {
        "lesson_id": f"lesson-{uuid.uuid4().hex[:10]}",
        "status": "ACTIVE",
        "text": cleaned,
        "category": cat,
        "evidence": str(evidence or "").strip()[:MAX_LESSON_CHARS],
        "source": str(source or "operator"),
        "created_at": utc_now().isoformat(),
        "reinforced_count": 1,
    }
    with _LOCK:
        data = _load()
        lessons = [l for l in data["lessons"] if isinstance(l, dict)]
        for existing in lessons:
            if str(existing.get("status") or "ACTIVE").upper() == "SUPERSEDED":
                continue
            if _similar(existing.get("text", ""), cleaned):
                # Same gist learned again — reinforce + refresh instead of dupe.
                existing["reinforced_count"] = int(existing.get("reinforced_count", 1)) + 1
                existing["text"] = cleaned
                existing["evidence"] = lesson["evidence"] or existing.get("evidence", "")
                existing["updated_at"] = lesson["created_at"]
                lessons.remove(existing)
                lessons.insert(0, existing)
                data["lessons"] = lessons[:MAX_LESSONS]
                _save(data)
                return existing
        lessons.insert(0, lesson)
        data["lessons"] = lessons[:MAX_LESSONS]
        _save(data)
    return lesson


def list_lessons(
    limit: int = 60,
    *,
    include_superseded: bool = False,
) -> list[dict[str, Any]]:
    with _LOCK:
        rows = [dict(l) for l in _load()["lessons"] if isinstance(l, dict)]
        if not include_superseded:
            rows = [
                row
                for row in rows
                if str(row.get("status") or "ACTIVE").upper() != "SUPERSEDED"
            ]
        return rows[: max(1, limit)]


def supersede_lesson(
    lesson_id: str,
    *,
    reason: str,
    replacement_lesson_id: str | None = None,
) -> Optional[dict[str, Any]]:
    """Keep a stale lesson in the journal while excluding it from future prompts."""

    target = str(lesson_id or "").strip()
    if not target:
        return None
    with _LOCK:
        data = _load()
        lessons = [row for row in data["lessons"] if isinstance(row, dict)]
        for row in lessons:
            if str(row.get("lesson_id") or "") != target:
                continue
            row["status"] = "SUPERSEDED"
            row["superseded_at"] = utc_now().isoformat()
            row["supersede_reason"] = str(reason or "").strip()[:MAX_LESSON_CHARS]
            row["replacement_lesson_id"] = replacement_lesson_id
            data["lessons"] = lessons
            _save(data)
            return dict(row)
    return None


def lessons_for_prompt(limit: int = 25) -> list[dict[str, Any]]:
    """Compact lessons for the operator prompt — the inherited knowledge base.
    Founding principles are seeded once so every operator inherits them."""
    seed_founding_principles()
    out = []
    for l in list_lessons(limit=limit):
        out.append(
            {
                "category": l.get("category"),
                "lesson": l.get("text"),
                "reinforced": l.get("reinforced_count", 1),
            }
        )
    return out


def lessons_count(*, include_superseded: bool = False) -> int:
    with _LOCK:
        rows = [row for row in _load()["lessons"] if isinstance(row, dict)]
        if not include_superseded:
            rows = [
                row
                for row in rows
                if str(row.get("status") or "ACTIVE").upper() != "SUPERSEDED"
            ]
        return len(rows)


__all__ = [
    "CLAIM_BOUNDARY",
    "DEFAULT_LESSONS_PATH",
    "FOUNDING_PRINCIPLES",
    "REPORT_KIND",
    "VALID_CATEGORIES",
    "lessons_count",
    "lessons_for_prompt",
    "list_lessons",
    "record_lesson",
    "seed_founding_principles",
    "set_lessons_path_for_tests",
    "supersede_lesson",
]
