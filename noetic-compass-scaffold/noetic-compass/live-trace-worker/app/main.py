"""Live-trace worker FastAPI entrypoint.

The production lifespan validates authentication and read-only isolation,
then warm-loads the exact real model. A load failure aborts startup; it cannot
silently substitute demo execution. Explicit development demo mode remains a
separate, non-production profile.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .auth import WorkerTokenMiddleware, auth_enabled
from .routes import health, live_trace
from .runtime import warm_load
from .runtime import model_loader

logger = logging.getLogger(__name__)


def _root_filesystem_is_read_only() -> bool:
    read_only_flag = getattr(os, "ST_RDONLY", 1)
    return bool(os.statvfs("/").f_flag & read_only_flag)


def _validate_startup_profile() -> None:
    """Reject an under-protected production container before model loading."""

    if not model_loader._is_production_profile():
        return
    if not auth_enabled():
        raise RuntimeError(
            "production worker profile requires ATLAS_LIVE_WORKER_TOKEN"
        )
    if not _root_filesystem_is_read_only():
        raise RuntimeError("production worker profile requires a read-only root filesystem")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Warm-load the model once at startup; tear down would go here."""
    _validate_startup_profile()
    loaded = warm_load()
    if model_loader._is_production_profile() and not loaded.is_real:
        raise RuntimeError("production worker failed to establish real-model readiness")
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
            "Demo mode is available only when explicitly requested outside "
            "the fail-closed production profile."
        ),
        lifespan=_lifespan,
    )
    # App-level auth remains optional for explicit local/demo profiles. The
    # production profile refuses startup unless the token is configured on
    # both the worker and API. See
    # docs/working/atlas_live_worker_launch_grade_exposure_2026_05_31.md.
    app.add_middleware(WorkerTokenMiddleware)
    app.include_router(health.router, tags=["health"])
    app.include_router(live_trace.router, tags=["live-trace"])
    return app


app = create_app()
