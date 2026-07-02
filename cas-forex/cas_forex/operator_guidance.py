"""Standing owner guidance for the AI operator.

The owner can hand the strategy desk considerations in plain language ("take
profit on big winners, then restart the cycle"). Notes persist here and are
injected into EVERY operator tick and chat, so the operator continuously weighs
them. Guidance shapes judgment INSIDE the owner fences — it can never widen a
fence, authorize live trading, or move money; a note asking for that is still
bounded by the same clamped dials as everything else.
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
DEFAULT_GUIDANCE_PATH = REPO_ROOT / "runtime" / "operator-guidance.json"

REPORT_KIND = "cas_forex_operator_guidance"
MAX_NOTES = 50
MAX_NOTE_CHARS = 2000

CLAIM_BOUNDARY = (
    "Owner guidance notes shape the AI operator's judgment inside the owner "
    "fences. They never widen a fence, authorize live trading, create ACCEPTs, "
    "or move money — the same clamps apply to every operator action regardless "
    "of guidance."
)

_LOCK = threading.RLock()
_PATH = DEFAULT_GUIDANCE_PATH


def set_guidance_path_for_tests(path: Optional[Path]) -> None:
    global _PATH
    _PATH = Path(path) if path is not None else DEFAULT_GUIDANCE_PATH


def _load() -> dict[str, Any]:
    if not _PATH.exists():
        return {"report_kind": REPORT_KIND, "notes": []}
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"report_kind": REPORT_KIND, "notes": []}
    if not isinstance(data, dict) or not isinstance(data.get("notes"), list):
        return {"report_kind": REPORT_KIND, "notes": []}
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


def add_note(text: str) -> dict[str, Any]:
    """Add a standing guidance note (newest first). Returns the stored note."""
    cleaned = str(text or "").strip()[:MAX_NOTE_CHARS]
    if not cleaned:
        raise ValueError("guidance note is empty")
    note = {
        "note_id": f"guid-{uuid.uuid4().hex[:10]}",
        "text": cleaned,
        "created_at": utc_now().isoformat(),
        "active": True,
    }
    with _LOCK:
        data = _load()
        notes = [n for n in data["notes"] if isinstance(n, dict)]
        notes.insert(0, note)
        data["notes"] = notes[:MAX_NOTES]
        _save(data)
    return note


def remove_note(note_id: str) -> bool:
    with _LOCK:
        data = _load()
        before = len(data["notes"])
        data["notes"] = [n for n in data["notes"] if str(n.get("note_id")) != str(note_id)]
        changed = len(data["notes"]) != before
        if changed:
            _save(data)
        return changed


def list_notes() -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(n) for n in _load()["notes"] if isinstance(n, dict) and n.get("active", True)]


def guidance_for_prompt(limit: int = 10) -> list[str]:
    """The active notes, newest first, as plain strings for the model prompt."""
    return [str(n.get("text") or "") for n in list_notes()[: max(1, limit)] if n.get("text")]


__all__ = [
    "CLAIM_BOUNDARY",
    "DEFAULT_GUIDANCE_PATH",
    "REPORT_KIND",
    "add_note",
    "guidance_for_prompt",
    "list_notes",
    "remove_note",
    "set_guidance_path_for_tests",
]
