"""Live-trace worker — FastAPI entrypoint.

M2 change vs M1: a lifespan handler runs ``warm_load`` once at startup so
the first /sessions request doesn't pay the model-load latency. If the
load fails (no torch / no GPU / network blocked), the worker stays up and
serves demo-mode responses — the cockpit's provenance badge then says
"Live mode unavailable" instead of "actual weights".
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .auth import WorkerTokenMiddleware
from .routes import health, live_trace
from .runtime import warm_load

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Warm-load the model once at startup; tear down would go here."""
    loaded = warm_load()
    logger.info(
        "startup: model_id=%s is_real=%s load_error=%s",
        loaded.manifest.model_id,
        loaded.is_real,
        loaded.load_error,
    )
    yield
    # M2 has nothing to tear down; M3+ may add stream-token cleanup.


def create_app() -> FastAPI:
    app = FastAPI(
        title="Atlas Live-Trace Worker",
        version="m2-real-pythia",
        description=(
            "Private worker that runs Pythia-160M + probe pipeline and "
            "streams trace events as SSE. Lives behind the noetic-compass-api "
            "proxy — browsers never hit this service directly. "
            "Falls back to a fake schema-valid demo stream if torch is "
            "unavailable or weights fail to load."
        ),
        lifespan=_lifespan,
    )
    # Optional app-level auth. No-op unless ATLAS_LIVE_WORKER_TOKEN is set, so
    # local dev / CI / the existing SSH-tunnel deploy are unaffected. When the
    # worker's HTTP port is exposed (RunPod proxy), set the env var on both the
    # worker and the API so only our API can reach it. See
    # docs/working/atlas_live_worker_launch_grade_exposure_2026_05_31.md.
    app.add_middleware(WorkerTokenMiddleware)
    app.include_router(health.router, tags=["health"])
    app.include_router(live_trace.router, tags=["live-trace"])
    return app


app = create_app()
