"""Strategy-development queue mutation primitives.

This module turns the strategy-development queue from a read-only artifact
into something the operator can act on through the API. It exposes a small
set of pure functions for stage-transition logic and one I/O wrapper that
atomically rewrites the queue file on disk.

The action surface is intentionally limited to research/replay/paper/review
movement. Nothing here flips a runtime gate, enables live trading, or
authorizes real-money execution. ``PROMOTED`` here is a queue-stage label
meaning "ready for further review" — it does NOT mean ``LIVE_PROMOTED`` or
any other runtime gate. The license-gated boundary is unchanged.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional


# Stages that may be promoted to a higher stage.
PROMOTABLE_STAGES = ("RESEARCH", "REPLAY", "PAPER", "REVIEW")

# Every legal stage label (including terminal labels).
ALL_STAGES = PROMOTABLE_STAGES + ("PROMOTED", "REJECTED", "ARCHIVED")

# Total order for promotion/demotion arithmetic. Higher = more advanced
# along the review pipeline. Terminal stages (PROMOTED / REJECTED /
# ARCHIVED) sit above PROMOTABLE_STAGES.
STAGE_ORDER: dict[str, int] = {
    "RESEARCH": 0,
    "REPLAY": 1,
    "PAPER": 2,
    "REVIEW": 3,
    "PROMOTED": 4,
    "REJECTED": 5,
    "ARCHIVED": 6,
}


VALID_ACTIONS = ("PROMOTE", "DEMOTE", "REJECT", "ARCHIVE", "REVIEW")


@dataclass(frozen=True)
class StrategyActionResult:
    """Outcome of a stage-mutation action."""

    strategy_id: str
    previous_stage: Optional[str]
    next_stage: Optional[str]
    action: str
    accepted: bool
    rejection_reason: Optional[str]
    actioned_at_iso: str
    note: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pure predicates / transitions (no I/O)
# ---------------------------------------------------------------------------


def _strategy_stage(strategy: Mapping[str, Any]) -> str:
    """Return the strategy's current stage, defaulting to RESEARCH."""
    return str(strategy.get("stage") or "RESEARCH")


def can_promote(strategy: Mapping[str, Any]) -> tuple[bool, str]:
    """Return (yes/no, reason) for whether ``strategy`` may be promoted."""
    stage = _strategy_stage(strategy)
    if stage == "PROMOTED":
        return False, "already promoted"
    if stage in ("REJECTED", "ARCHIVED"):
        return False, f"terminal stage {stage} cannot be promoted"
    if stage not in PROMOTABLE_STAGES:
        return False, f"unknown stage {stage}"
    return True, ""


def can_demote(strategy: Mapping[str, Any]) -> tuple[bool, str]:
    """Return (yes/no, reason) for whether ``strategy`` may be demoted."""
    stage = _strategy_stage(strategy)
    if stage == "RESEARCH":
        return False, "RESEARCH is the earliest stage; cannot demote"
    if stage in ("REJECTED", "ARCHIVED"):
        return False, f"terminal stage {stage} cannot be demoted"
    if stage not in PROMOTABLE_STAGES + ("PROMOTED",):
        return False, f"unknown stage {stage}"
    return True, ""


def next_stage_for_promotion(current: str) -> Optional[str]:
    """Return the stage one step above ``current`` along the promote axis."""
    chain = list(PROMOTABLE_STAGES) + ["PROMOTED"]
    if current not in chain:
        return None
    idx = chain.index(current)
    if idx + 1 >= len(chain):
        return None
    return chain[idx + 1]


def previous_stage_for_demotion(current: str) -> Optional[str]:
    """Return the stage one step below ``current`` along the demote axis."""
    chain = list(PROMOTABLE_STAGES) + ["PROMOTED"]
    if current not in chain:
        return None
    idx = chain.index(current)
    if idx - 1 < 0:
        return None
    return chain[idx - 1]


# ---------------------------------------------------------------------------
# I/O wrapper
# ---------------------------------------------------------------------------


def _now_iso(now: Optional[datetime]) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.isoformat()


def _items_key(queue: Mapping[str, Any]) -> str:
    """Resolve which top-level key holds the strategy list.

    The task spec describes ``queue["items"]``. The real strategy_dev_queue
    report uses ``work_items``. Accept either so this module composes with
    both shapes."""
    if "items" in queue and isinstance(queue["items"], list):
        return "items"
    if "work_items" in queue and isinstance(queue["work_items"], list):
        return "work_items"
    # Default to "items" so a freshly-created in-memory queue dict gets a
    # sensible key when the strategy is absent.
    return "items"


def _strategy_id_of(item: Mapping[str, Any]) -> Optional[str]:
    for key in ("strategy_id", "item_id", "id"):
        value = item.get(key)
        if value is not None:
            return str(value)
    return None


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write ``payload`` to ``path`` atomically.

    Uses a same-directory temp file + ``os.replace`` so a partial write or
    serialization failure cannot leave a half-written queue file on disk.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _reject(strategy_id: str, action: str, reason: str, note: Optional[str], now_iso: str) -> StrategyActionResult:
    return StrategyActionResult(
        strategy_id=strategy_id,
        previous_stage=None,
        next_stage=None,
        action=action,
        accepted=False,
        rejection_reason=reason,
        actioned_at_iso=now_iso,
        note=note,
    )


def apply_action(
    *,
    strategy_id: str,
    action: str,
    queue: Mapping[str, Any],
    queue_path: Path,
    note: Optional[str] = None,
    now: Optional[datetime] = None,
) -> StrategyActionResult:
    """Apply ``action`` to the strategy with ``strategy_id`` inside ``queue``.

    On acceptance, the queue file at ``queue_path`` is rewritten atomically
    with the updated stage and a new ``history`` entry appended. ``queue`` is
    treated as a parsed dict (not a path) so the function is unit-testable
    without touching disk for the in-memory portion of its work.
    """
    now_iso = _now_iso(now)
    action = str(action).upper()
    if action not in VALID_ACTIONS:
        return _reject(strategy_id, action, f"unknown action {action}", note, now_iso)

    items_key = _items_key(queue)
    items_list = list(queue.get(items_key) or [])

    target_index: Optional[int] = None
    target_strategy: Optional[Mapping[str, Any]] = None
    for idx, item in enumerate(items_list):
        if not isinstance(item, Mapping):
            continue
        if _strategy_id_of(item) == strategy_id:
            target_index = idx
            target_strategy = item
            break

    if target_strategy is None or target_index is None:
        return _reject(strategy_id, action, "strategy_id not found in queue", note, now_iso)

    current_stage = _strategy_stage(target_strategy)
    next_stage: Optional[str] = None

    if action == "PROMOTE":
        ok, reason = can_promote(target_strategy)
        if not ok:
            return StrategyActionResult(
                strategy_id=strategy_id,
                previous_stage=current_stage,
                next_stage=None,
                action=action,
                accepted=False,
                rejection_reason=reason,
                actioned_at_iso=now_iso,
                note=note,
            )
        next_stage = next_stage_for_promotion(current_stage)
        if next_stage is None:
            return StrategyActionResult(
                strategy_id=strategy_id,
                previous_stage=current_stage,
                next_stage=None,
                action=action,
                accepted=False,
                rejection_reason="no further promotion stage available",
                actioned_at_iso=now_iso,
                note=note,
            )
    elif action == "DEMOTE":
        ok, reason = can_demote(target_strategy)
        if not ok:
            return StrategyActionResult(
                strategy_id=strategy_id,
                previous_stage=current_stage,
                next_stage=None,
                action=action,
                accepted=False,
                rejection_reason=reason,
                actioned_at_iso=now_iso,
                note=note,
            )
        next_stage = previous_stage_for_demotion(current_stage)
        if next_stage is None:
            return StrategyActionResult(
                strategy_id=strategy_id,
                previous_stage=current_stage,
                next_stage=None,
                action=action,
                accepted=False,
                rejection_reason="no further demotion stage available",
                actioned_at_iso=now_iso,
                note=note,
            )
    elif action == "REJECT":
        next_stage = "REJECTED"
    elif action == "ARCHIVE":
        next_stage = "ARCHIVED"
    elif action == "REVIEW":
        # REVIEW does NOT change the stage. We still append a history entry
        # and tag last_reviewed_at_iso. Treat next_stage == current_stage.
        next_stage = current_stage

    # Build mutable copies (the input mapping is intentionally treated as
    # immutable so the caller's parsed queue isn't tweaked in place before
    # the atomic rewrite succeeds).
    new_queue: MutableMapping[str, Any] = json.loads(json.dumps(queue))
    new_items = list(new_queue.get(items_key) or [])
    new_strategy = dict(new_items[target_index])

    history = list(new_strategy.get("history") or [])
    history.append(
        {
            "action": action,
            "from_stage": current_stage,
            "to_stage": next_stage,
            "actioned_at_iso": now_iso,
            "note": note,
        }
    )
    new_strategy["history"] = history

    if action == "REVIEW":
        new_strategy["last_reviewed_at_iso"] = now_iso
    else:
        new_strategy["stage"] = next_stage

    new_items[target_index] = new_strategy
    new_queue[items_key] = new_items

    _atomic_write_json(Path(queue_path), new_queue)

    return StrategyActionResult(
        strategy_id=strategy_id,
        previous_stage=current_stage,
        next_stage=next_stage,
        action=action,
        accepted=True,
        rejection_reason=None,
        actioned_at_iso=now_iso,
        note=note,
    )
