"""Read-only operator view of the durable state-ledger posture.

The state-ledger rollout (``api/state_ledger_bootstrap.py`` + the strangler-fig seam in
``api/services/production/state_substrate/migration.py``) is gated on an operator being able
to WATCH zero-divergence evidence accumulate on live traffic before read-authority moves onto
the ledger. This endpoint is that window: a single read-only GET that reports the honest
posture and the live shadow-compare tally.

It is a thin shell over the pure :func:`ledger_status` function -- all the logic and all the
honesty live there and are unit-tested without the app. The route only fetches the handle the
lifespan stashed on ``app.state.state_ledger`` and hands it to that function. When no mirror is
installed (production's dark default) the handle is ``None`` and the response is
``{"posture": "dark"}`` -- it reads nothing and changes nothing. The route is observation only:
it never mutates state and never touches what serves reads.

Defensive read of ``app.state``: ``getattr(..., "state_ledger", None)`` so that even a context
where the lifespan never ran (some minimal test client) degrades to the dark posture rather
than raising. A status endpoint must never be the thing that breaks.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.services.production.state_substrate import ledger_status

router = APIRouter(prefix="/api/state-ledger", tags=["state_ledger"])


@router.get("/status")
async def get_state_ledger_status(request: Request) -> dict[str, object]:
    """Return the live state-ledger posture + shadow-compare tally (read-only).

    Dark by default: with no mirror installed, reports ``{"posture": "dark"}`` and
    touches nothing. When enabled, reports the posture
    (``enabled_shadow_dict_authoritative`` or ``enabled_ledger_read_authoritative``),
    the rehydrated ``audit_count`` / ``fleet_counts``, and the real measured
    ``divergence_tally`` (``reads_compared`` / ``divergences_found`` / ``last_divergence``).
    """

    handle = getattr(request.app.state, "state_ledger", None)
    return ledger_status(handle)
