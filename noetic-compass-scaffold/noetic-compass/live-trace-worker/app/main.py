"""Live-trace worker — FastAPI entrypoint.

Runs locally on uvicorn for development; runs on RunPod via the Dockerfile.
Bound to /sessions + /health; expected to live behind noetic-compass-api,
not exposed to the public internet directly.
"""

from __future__ import annotations

from fastapi import FastAPI

from .routes import health, live_trace


def create_app() -> FastAPI:
    app = FastAPI(
        title="Atlas Live-Trace Worker",
        version="m1-scaffold",
        description=(
            "Private worker that runs the model (Pythia-160M at v0.1) + probe "
            "pipeline and streams trace events as SSE. Lives behind the "
            "noetic-compass-api proxy — browsers never hit this service "
            "directly."
        ),
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(live_trace.router, tags=["live-trace"])
    return app


app = create_app()
