"""Atlas LIVE proxy routes.

Alpha contract:
Atlas Viewer UI -> noetic-compass-api -> private RunPod live-trace worker.

The browser never receives the RunPod URL. Session creation is gated by an
invite-code allowlist and lightweight in-memory abuse limits. The SSE route
uses a short-lived stream token because EventSource cannot send custom headers.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from api.config import settings


router = APIRouter(prefix="/atlas/live", tags=["atlas_live"])

INVITE_HEADER = "X-Atlas-Invite-Code"
_IP_WINDOW_SECONDS = 60 * 60
_CODE_WINDOW_SECONDS = 24 * 60 * 60
_ip_opens: dict[str, deque[float]] = defaultdict(deque)
_code_opens: dict[str, deque[float]] = defaultdict(deque)


class LiveSessionRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    model_id: str = Field(default="EleutherAI/pythia-160m")
    max_new_tokens: int = Field(default=24, ge=1, le=128)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: int | None = None
    probes: list[
        Literal[
            "active_trace",
            "blindspots_f1",
            "mode7_attribution",
            "confidence_margin",
        ]
    ] = Field(default_factory=list)
    method_config: dict[str, Any] = Field(default_factory=dict)


class LiveSessionResponse(BaseModel):
    session_id: str
    mode: Literal["live"] = "live"
    model_id: str
    stream_url: str
    stream_token: str


def _allowed_codes() -> set[str]:
    return {
        code.strip()
        for code in settings.atlas_live_invite_codes.split(",")
        if code.strip()
    }


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _trim_window(bucket: deque[float], now: float, seconds: int) -> None:
    while bucket and now - bucket[0] > seconds:
        bucket.popleft()


def _check_invite(code: str | None) -> str:
    if not code:
        raise HTTPException(status_code=401, detail="Missing Atlas LIVE invite code")
    allowed = _allowed_codes()
    if not allowed:
        raise HTTPException(status_code=503, detail="Atlas LIVE invite allowlist is not configured")
    if code not in allowed:
        raise HTTPException(status_code=403, detail="Invalid Atlas LIVE invite code")
    return code


def _check_abuse_limits(ip: str, code: str) -> None:
    now = time.time()
    ip_bucket = _ip_opens[ip]
    _trim_window(ip_bucket, now, _IP_WINDOW_SECONDS)
    if len(ip_bucket) >= settings.atlas_live_session_rate_limit_per_ip_hour:
        raise HTTPException(status_code=429, detail="Atlas LIVE per-IP session limit exceeded")

    code_bucket = _code_opens[code]
    _trim_window(code_bucket, now, _CODE_WINDOW_SECONDS)
    if len(code_bucket) >= settings.atlas_live_invite_daily_limit:
        raise HTTPException(status_code=429, detail="Atlas LIVE invite-code daily limit exceeded")

    ip_bucket.append(now)
    code_bucket.append(now)


def _worker_base_url() -> str:
    base = settings.atlas_live_worker_url.strip().rstrip("/")
    if not base:
        raise HTTPException(status_code=503, detail="Atlas LIVE worker URL is not configured")
    return base


def _token_secret() -> str:
    return settings.jwt_secret


def _create_stream_token(session_id: str) -> str:
    exp = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.atlas_live_stream_token_minutes
    )
    payload = {"sub": "atlas-live-stream", "sid": session_id, "exp": exp}
    return jwt.encode(payload, _token_secret(), algorithm=settings.jwt_algorithm)


def _verify_stream_token(session_id: str, token: str | None) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="Missing Atlas LIVE stream token")
    try:
        payload = jwt.decode(token, _token_secret(), algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Atlas LIVE stream token: {exc}") from exc
    if payload.get("sid") != session_id:
        raise HTTPException(status_code=403, detail="Atlas LIVE stream token does not match session")


async def _create_worker_session(req: LiveSessionRequest) -> dict:
    timeout = httpx.Timeout(settings.atlas_live_http_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{_worker_base_url()}/sessions", json=req.model_dump())
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Atlas LIVE worker rejected session: HTTP {resp.status_code}",
        )
    return resp.json()


async def _iter_worker_events(session_id: str) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "GET",
            f"{_worker_base_url()}/sessions/{session_id}/events",
            headers={"Accept": "text/event-stream"},
        ) as resp:
            if resp.status_code >= 400:
                payload = (
                    '{"type":"error","message":"Atlas LIVE worker stream failed",'
                    '"retryable":true}'
                )
                yield f"event: error\ndata: {payload}\n\n".encode()
                return
            async for chunk in resp.aiter_bytes():
                yield chunk


@router.post("/session", response_model=LiveSessionResponse)
async def create_live_session(
    req: LiveSessionRequest,
    request: Request,
    invite_code: str | None = Header(default=None, alias=INVITE_HEADER),
) -> LiveSessionResponse:
    code = _check_invite(invite_code)
    _check_abuse_limits(_client_ip(request), code)

    worker_resp = await _create_worker_session(req)
    session_id = str(worker_resp.get("session_id") or "")
    if not session_id:
        raise HTTPException(status_code=502, detail="Atlas LIVE worker did not return a session_id")

    token = _create_stream_token(session_id)
    stream_url = f"/atlas/live/session/{session_id}/events?stream_token={token}"
    return LiveSessionResponse(
        session_id=session_id,
        model_id=req.model_id,
        stream_url=stream_url,
        stream_token=token,
    )


@router.get("/session/{session_id}/events")
async def live_session_events(
    session_id: str,
    stream_token: str | None = Query(default=None),
) -> StreamingResponse:
    _verify_stream_token(session_id, stream_token)
    return StreamingResponse(
        _iter_worker_events(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
