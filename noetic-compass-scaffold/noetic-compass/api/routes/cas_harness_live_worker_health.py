"""CAS Harness live-worker health route.

The Audit Console needs an honest, never-throwing signal about whether the
live-trace worker (`EleutherAI/pythia-160m`) is actually reachable AND serving
real Pythia weights — versus unconfigured, unreachable, or running in a
schema-valid demo/fake mode.

Honesty contract (see project memory "20B run results" + the live-worker
runner): we claim real weights ONLY when the worker's `/health/realmode`
endpoint reports BOTH `verdict == "REAL_PYTHIA_WEIGHTS_LOADED"` AND
`is_real_model is True`. Anything else is reported plainly as demo/unavailable.

This route NEVER raises to the client on a worker outage. A down or misbehaving
worker is a normal, expected state and is surfaced as `reachable: false` with an
honest label, so the console can render a calm status chip instead of an error.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from api.config import settings


router = APIRouter(prefix="/api/cas-harness/live-worker", tags=["cas_harness_live_worker"])

_REAL_WEIGHTS_VERDICT = "REAL_PYTHIA_WEIGHTS_LOADED"

# Keep the probe snappy so the console chip resolves fast even when the worker
# is wedged. Reuse the configured Atlas-live timeout but cap it small.
_MAX_HEALTH_TIMEOUT_SECONDS = 5.0

_LABEL_NOT_CONFIGURED = "Live worker not configured"
_LABEL_REAL = "Live worker connected · real Pythia weights"
_LABEL_DEMO = "Live worker reachable · demo mode (not real weights)"
_LABEL_UNREACHABLE = "Live worker unavailable · no live audit will run"


class CasHarnessLiveWorkerHealth(BaseModel):
    """Honest live-worker connection state for the Audit Console chip."""

    configured: bool
    reachable: bool
    real_weights: bool
    model_id: str | None = None
    worker_version: str | None = None
    label: str


def _health_timeout_seconds() -> float:
    configured = float(settings.atlas_live_http_timeout_seconds)
    if configured <= 0:
        return _MAX_HEALTH_TIMEOUT_SECONDS
    return min(_MAX_HEALTH_TIMEOUT_SECONDS, configured)


def _coerce_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


@router.get("/health", response_model=CasHarnessLiveWorkerHealth)
async def get_live_worker_health() -> CasHarnessLiveWorkerHealth:
    """Report whether the live-trace worker is reachable and serving real weights.

    Never raises on worker-down: an unreachable or misbehaving worker is reported
    honestly as ``reachable: false`` rather than propagated as a client error.
    """

    base = settings.atlas_live_worker_url.strip().rstrip("/")
    if not base:
        return CasHarnessLiveWorkerHealth(
            configured=False,
            reachable=False,
            real_weights=False,
            model_id=None,
            worker_version=None,
            label=_LABEL_NOT_CONFIGURED,
        )

    timeout = httpx.Timeout(_health_timeout_seconds())
    payload: dict[str, object] | None = None
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{base}/health/realmode")
        if resp.status_code < 400:
            body = resp.json()
            if isinstance(body, dict):
                payload = body
    except httpx.HTTPError:
        payload = None
    except ValueError:
        # Worker answered but body was not JSON — treat as unreachable-for-trust.
        payload = None

    if payload is None:
        return CasHarnessLiveWorkerHealth(
            configured=True,
            reachable=False,
            real_weights=False,
            model_id=None,
            worker_version=None,
            label=_LABEL_UNREACHABLE,
        )

    model_id = _coerce_str(payload.get("model_id"))
    worker_version = _coerce_str(payload.get("worker_version"))
    real_weights = (
        payload.get("verdict") == _REAL_WEIGHTS_VERDICT
        and payload.get("is_real_model") is True
    )

    label = _LABEL_REAL if real_weights else _LABEL_DEMO
    return CasHarnessLiveWorkerHealth(
        configured=True,
        reachable=True,
        real_weights=real_weights,
        model_id=model_id,
        worker_version=worker_version,
        label=label,
    )
