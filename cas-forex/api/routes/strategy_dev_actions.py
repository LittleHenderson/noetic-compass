"""HTTP routes for strategy-development queue mutations.

Five POST endpoints — ``/promote``, ``/demote``, ``/reject``, ``/archive``,
``/review`` — each accept ``{"strategy_id": ..., "note": ...}`` and apply
the corresponding action to the latest strategy_dev_queue report on disk.

The route delegates pure stage logic to ``cas_forex.strategy_dev_actions``
and is intentionally thin so it can be tested in isolation via the
``set_loader_for_testing`` hook. Promotion here moves a strategy along the
RESEARCH -> REPLAY -> PAPER -> REVIEW -> PROMOTED queue axis; it does NOT
flip a runtime gate or authorize live trading.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cas_forex.strategy_dev_actions import (
    StrategyActionResult,
    apply_action,
)


router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[2]
QUEUE_GLOB = "evidence_runs/strategy_dev_queue/strategy-dev-queue-*-report.json"


class ActionRequest(BaseModel):
    strategy_id: str
    note: Optional[str] = None


def _default_loader() -> tuple[Optional[dict[str, Any]], Optional[Path]]:
    """Return the parsed latest queue report and its path on disk.

    Returns ``(None, None)`` if no queue report exists or fails to parse.
    """
    candidates = sorted(REPO_ROOT.glob(QUEUE_GLOB), reverse=True)
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload, path
        except (OSError, ValueError):
            continue
    return None, None


_LOADER: Callable[[], tuple[Optional[dict[str, Any]], Optional[Path]]] = _default_loader


def set_loader_for_testing(loader: Callable[[], tuple[Optional[dict[str, Any]], Optional[Path]]]) -> None:
    """Replace the disk-backed queue loader. Tests only."""
    global _LOADER
    _LOADER = loader


def reset_loader_for_testing() -> None:
    """Restore the default disk-backed loader."""
    global _LOADER
    _LOADER = _default_loader


def _strategy_current_stage(queue: dict[str, Any], strategy_id: str) -> Optional[str]:
    """Best-effort lookup for current stage, used in 400 error bodies."""
    for key in ("items", "work_items"):
        items = queue.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            for id_key in ("strategy_id", "item_id", "id"):
                if item.get(id_key) == strategy_id:
                    return item.get("stage")
    return None


def _result_payload(result: StrategyActionResult) -> dict[str, Any]:
    return asdict(result)


def _execute(action: str, body: ActionRequest) -> dict[str, Any]:
    queue, queue_path = _LOADER()
    if queue is None or queue_path is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "queue_unavailable",
                "message": "No strategy-development queue report could be loaded.",
                "current_stage": None,
            },
        )

    result = apply_action(
        strategy_id=body.strategy_id,
        action=action,
        queue=queue,
        queue_path=Path(queue_path),
        note=body.note,
    )
    if not result.accepted:
        current_stage = _strategy_current_stage(queue, body.strategy_id)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "action_rejected",
                "message": result.rejection_reason or "action rejected",
                "current_stage": current_stage,
                "result": _result_payload(result),
            },
        )
    return _result_payload(result)


@router.post("/promote")
async def promote(body: ActionRequest) -> dict[str, Any]:
    """Promote a strategy one stage along RESEARCH -> ... -> PROMOTED."""
    return _execute("PROMOTE", body)


@router.post("/demote")
async def demote(body: ActionRequest) -> dict[str, Any]:
    """Demote a strategy one stage back toward RESEARCH."""
    return _execute("DEMOTE", body)


@router.post("/reject")
async def reject(body: ActionRequest) -> dict[str, Any]:
    """Mark a strategy as REJECTED (terminal)."""
    return _execute("REJECT", body)


@router.post("/archive")
async def archive(body: ActionRequest) -> dict[str, Any]:
    """Mark a strategy as ARCHIVED (terminal)."""
    return _execute("ARCHIVE", body)


@router.post("/review")
async def review(body: ActionRequest) -> dict[str, Any]:
    """Tag a strategy as reviewed without changing its stage."""
    return _execute("REVIEW", body)
