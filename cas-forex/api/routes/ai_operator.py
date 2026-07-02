"""HTTP routes for the always-on AI operator + model failover.

``GET /state`` returns the operator scheduler status, the active model provider
(Claude vs free local fallback), the token budget, and recent operator actions.
``POST /start`` `/stop` toggle the always-on loop; ``/run-now`` runs one tick.
``/config`` sets the interval. The ``/model-provider/*`` routes read failover
status, top up the paid token budget, and set the budget.

Boundary: the operator adjusts only owner-fenced AI dials. Nothing here places
orders, moves money, or authorizes live trading.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from cas_forex.ai_operator_runner import (
    DEFAULT_INTERVAL_SECONDS,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    run_operator_tick_now,
    runner_status,
    set_desired_runner_state,
    start_runner,
    stop_runner,
)
from cas_forex.model_provider import get_model_provider

router = APIRouter()


class OperatorConfig(BaseModel):
    interval_seconds: int = Field(
        default=DEFAULT_INTERVAL_SECONDS,
        ge=MIN_INTERVAL_SECONDS,
        le=MAX_INTERVAL_SECONDS,
    )


class TopUp(BaseModel):
    tokens: int = Field(ge=0)


class SetKey(BaseModel):
    api_key: str = Field(default="")


class BudgetReset(BaseModel):
    budget_tokens: int = Field(ge=0)


@router.get("/state")
async def get_state() -> dict[str, Any]:
    return runner_status()


@router.post("/start")
async def post_start(body: OperatorConfig) -> dict[str, Any]:
    return start_runner(body.interval_seconds)


@router.post("/stop")
async def post_stop() -> dict[str, Any]:
    return stop_runner()


@router.post("/run-now")
async def post_run_now() -> dict[str, Any]:
    return run_operator_tick_now()


@router.post("/config")
async def post_config(body: OperatorConfig) -> dict[str, Any]:
    # Persist the interval; re-arm only if the owner already had it running.
    status = runner_status()
    if status.get("running"):
        return start_runner(body.interval_seconds)
    return set_desired_runner_state(body.interval_seconds, desired_running=False)


@router.get("/model-provider/state")
async def get_model_provider_state() -> dict[str, Any]:
    return get_model_provider().status()


@router.post("/model-provider/add-tokens")
async def post_add_tokens(body: TopUp) -> dict[str, Any]:
    return get_model_provider().top_up(body.tokens)


@router.post("/model-provider/reset-budget")
async def post_reset_budget(body: BudgetReset) -> dict[str, Any]:
    return get_model_provider().reset_budget(budget_tokens=body.budget_tokens)


@router.post("/model-provider/set-key")
async def post_set_key(body: SetKey) -> dict[str, Any]:
    """Store (or, with an empty value, clear) the owner's Claude API key in the
    local git-ignored secret store. Takes effect on the next model call — no
    restart. The key is never logged or echoed; the response only confirms
    presence + a masked hint."""
    from cas_forex.operator_secrets import set_secret

    set_secret("primary_api_key", body.api_key.strip() or None)
    # Clear any primary cooldown so the freshly-set key is tried immediately.
    provider = get_model_provider()
    try:
        provider._state["primary_cooldown_until_epoch"] = 0.0  # noqa: SLF001 (same-package owner action)
        provider._save()
    except Exception:
        pass
    return provider.status()
