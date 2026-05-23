"""Live-trace session endpoints.

POST /sessions                  -> create session, returns id + events URL
GET  /sessions/{id}/events      -> SSE stream of LiveTraceEvent payloads
GET  /sessions/{id}/manifest    -> snapshot manifest (no streaming)
POST /sessions/dump             -> debug helper, returns full event list JSON

The dispatcher in runtime.event_stream.stream_trace picks real vs fake
based on whether get_loaded_model().is_real. Routes here don't care.
"""

from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..runtime import get_manifest, stream_trace
from ..schemas.requests import CreateSessionRequest, CreateSessionResponse

router = APIRouter()


_SESSIONS: dict[str, CreateSessionRequest] = {}


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    try:
        get_manifest(req.model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_id = str(uuid.uuid4())
    _SESSIONS[session_id] = req
    return CreateSessionResponse(
        session_id=session_id,
        events_url=f"/sessions/{session_id}/events",
    )


@router.get("/sessions/{session_id}/manifest")
def session_manifest(session_id: str) -> dict:
    req = _SESSIONS.get(session_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")
    return get_manifest(req.model_id).model_dump()


async def _sse_iter(req: CreateSessionRequest) -> AsyncIterator[bytes]:
    async for event in stream_trace(req):
        payload = event.model_dump_json()
        yield f"event: {event.type}\ndata: {payload}\n\n".encode()


@router.get("/sessions/{session_id}/events")
async def session_events(session_id: str) -> StreamingResponse:
    req = _SESSIONS.get(session_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    return StreamingResponse(
        _sse_iter(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions/dump")
async def dump_session(req: CreateSessionRequest) -> dict:
    """Non-SSE one-shot dump. Used by tests + curl checks."""
    try:
        get_manifest(req.model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    events: list[dict] = []
    async for event in stream_trace(req):
        events.append(json.loads(event.model_dump_json()))
    return {"events": events}
