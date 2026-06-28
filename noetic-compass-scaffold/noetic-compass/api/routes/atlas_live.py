"""Atlas LIVE session proxy.

The browser sends method-panel configs here. The API validates that enabled
methods are actually worker-wired for LIVE before forwarding them to the
private live-trace worker.
"""

from __future__ import annotations

from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from api.config import settings
from api.services.atlas_live_worker_auth import atlas_worker_auth_headers

router = APIRouter(prefix="/atlas/live", tags=["atlas-live"])

RuntimeSupportStatus = Literal["wired_runtime_effect", "payload_only", "unsupported"]

WIRED_LIVE_METHODS: frozenset[str] = frozenset(
    {
        "foundation_probe",
        "rpm_gate_check",
        "blindspot_detection",
        "verification_stack",
    }
)
PAYLOAD_ONLY_METHODS: frozenset[str] = frozenset(
    {"evidence_packet", "spatial_evidence_layer"}
)
UNSUPPORTED_LIVE_METHODS: frozenset[str] = frozenset(
    {"inversion_scan", "sparse_neuron_cover", "drive_local_eraser"}
)
ALL_LIVE_METHODS: frozenset[str] = (
    WIRED_LIVE_METHODS | PAYLOAD_ONLY_METHODS | UNSUPPORTED_LIVE_METHODS
)


class AtlasLiveMethodConfig(BaseModel):
    enabled: bool = True
    knobs: dict[str, Any] = Field(default_factory=dict)


class AtlasLiveSessionRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    model_id: str = "EleutherAI/pythia-160m"
    max_new_tokens: int = Field(default=24, ge=1, le=128)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: int | None = None
    probes: list[str] = Field(default_factory=list)
    method_configs: dict[str, AtlasLiveMethodConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_live_methods(self) -> "AtlasLiveSessionRequest":
        unknown = sorted(set(self.method_configs) - ALL_LIVE_METHODS)
        if unknown:
            raise ValueError(f"Unknown LIVE method(s): {', '.join(unknown)}")

        unavailable = []
        for method_id, config in sorted(self.method_configs.items()):
            if not config.enabled:
                continue
            if method_id in WIRED_LIVE_METHODS:
                continue
            if method_id in PAYLOAD_ONLY_METHODS:
                unavailable.append(f"{method_id}=payload_only")
            else:
                unavailable.append(f"{method_id}=unsupported")
        if unavailable:
            raise ValueError(
                "Unsupported LIVE method(s): "
                + ", ".join(unavailable)
                + ". Disable them before starting a live worker session."
            )
        return self


class AtlasLiveSessionResponse(BaseModel):
    session_id: str
    events_url: str
    worker_events_url: str


def _worker_url(path: str) -> str:
    return settings.live_trace_worker_url.rstrip("/") + path


def _worker_payload(req: AtlasLiveSessionRequest) -> dict[str, Any]:
    return req.model_dump(exclude_none=True)


async def _post_worker_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                _worker_url(path),
                json=payload,
                headers=atlas_worker_auth_headers(),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"live trace worker unavailable: {exc}",
        ) from exc

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


async def _get_worker_json(path: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(_worker_url(path), headers=atlas_worker_auth_headers())
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"live trace worker unavailable: {exc}",
        ) from exc

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/health")
async def live_worker_health() -> dict[str, Any]:
    return await _get_worker_json("/health")


@router.get("/health/realmode")
async def live_worker_realmode_health() -> dict[str, Any]:
    return await _get_worker_json("/health/realmode")


@router.post("/sessions", response_model=AtlasLiveSessionResponse)
async def create_live_session(req: AtlasLiveSessionRequest) -> AtlasLiveSessionResponse:
    worker_body = await _post_worker_json("/sessions", _worker_payload(req))
    session_id = str(worker_body["session_id"])
    worker_events_url = str(worker_body["events_url"])
    return AtlasLiveSessionResponse(
        session_id=session_id,
        worker_events_url=worker_events_url,
        events_url=f"/atlas/live/session/{session_id}/events",
    )


@router.post("/sessions/dump")
async def dump_live_session(req: AtlasLiveSessionRequest) -> dict[str, Any]:
    return await _post_worker_json("/sessions/dump", _worker_payload(req))


@router.get("/session/{session_id}/events")
async def live_session_events(session_id: str) -> StreamingResponse:
    async def iter_worker_events():
        url = _worker_url(f"/sessions/{session_id}/events")
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET",
                    url,
                    headers={
                        "Accept": "text/event-stream",
                        **atlas_worker_auth_headers(),
                    },
                ) as resp:
                    if resp.status_code >= 400:
                        detail = await resp.aread()
                        raise HTTPException(
                            status_code=resp.status_code,
                            detail=detail.decode("utf-8", errors="replace"),
                        )
                    async for chunk in resp.aiter_bytes():
                        yield chunk
        except httpx.HTTPError as exc:
            yield (
                "event: error\n"
                f"data: {{\"type\":\"error\",\"message\":\"live trace worker unavailable: {exc}\",\"retryable\":true}}\n\n"
            ).encode()

    return StreamingResponse(
        iter_worker_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
