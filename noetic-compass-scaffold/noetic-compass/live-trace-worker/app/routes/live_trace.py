"""Live-trace session endpoints.

POST /sessions                  -> create session, returns id + events URL
GET  /sessions/{id}/events      -> SSE stream of LiveTraceEvent payloads
GET  /sessions/{id}/manifest    -> snapshot manifest (no streaming)

The API proxy at noetic-compass-api/routes/atlas_live.py forwards user
requests here after enforcing auth/license. Browsers never hit this
service directly.
"""

from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..runtime import get_manifest, stream_fake_trace
from ..schemas.requests import CreateSessionRequest, CreateSessionResponse

router = APIRouter()


# In-memory session store. Milestone 2 may swap this for a Redis-backed store
# once we want multi-worker fanout; for milestone-1 single-worker scaffold
# this is intentionally minimal.
_SESSIONS: dict[str, CreateSessionRequest] = {}


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    # Validate model_id early so the caller gets a 400, not a stream error.
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
    """Wrap the typed event stream into the SSE wire format."""
    async for event in stream_fake_trace(req):
        payload = event.model_dump_json()
        # Each SSE message: `event: <type>\ndata: <json>\n\n`. The event:
        # line lets consumers filter without parsing the JSON.
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
            "X-Accel-Buffering": "no",  # Disable proxy buffering (nginx).
        },
    )


# Test/debug surface — non-SSE one-shot dump of the event sequence as JSON.
# Useful for unit tests + curl checks without parsing SSE.
@router.post("/sessions/dump")
async def dump_session(req: CreateSessionRequest) -> dict:
    try:
        get_manifest(req.model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    events = []
    async for event in stream_fake_trace(req):
        events.append(json.loads(event.model_dump_json()))
    return {"events": events}
