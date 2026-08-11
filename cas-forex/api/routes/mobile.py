"""Mobile/PWA/APK readiness evidence routes."""

from __future__ import annotations

import threading
import time
from typing import Any

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from cas_forex.mobile_apk_artifact import (
    APK_MEDIA_TYPE,
    DEFAULT_DOWNLOAD_PATH,
    DEFAULT_RELEASE_DOWNLOAD_PATH,
    DOWNLOAD_FILENAME,
    RELEASE_DOWNLOAD_FILENAME,
    debug_apk_artifact_metadata,
    release_apk_artifact_metadata,
)
from cas_forex.mobile_readiness_latest import latest_mobile_readiness_report
from cas_forex.mobile_phone_proof import (
    build_phone_runtime_proof,
    latest_phone_runtime_proof,
    record_phone_runtime_proof,
)
from cas_forex.mobile_proof_session import (
    build_mobile_proof_session,
    mobile_proof_session_to_dict,
)
from cas_forex.mobile_final_verification import (
    DEFAULT_OUTPUT_DIR as DEFAULT_MOBILE_FINAL_VERIFICATION_OUTPUT_DIR,
    build_mobile_final_verification,
    mobile_final_verification_to_dict,
    write_mobile_final_verification,
)
from cas_forex.mobile_verification_plan import (
    DEFAULT_OUTPUT_DIR as DEFAULT_MOBILE_VERIFICATION_PLAN_OUTPUT_DIR,
    build_mobile_verification_plan,
    write_mobile_verification_plan,
)
from cas_forex.phone_verification_session import (
    DEFAULT_OUTPUT_DIR as DEFAULT_PHONE_VERIFICATION_SESSION_OUTPUT_DIR,
    build_phone_verification_session,
    redact_phone_verification_session,
    write_phone_verification_session,
)


router = APIRouter()
_MOBILE_EVIDENCE_CACHE_TTL_SECONDS = 5.0
_mobile_evidence_cache_lock = threading.Lock()
_mobile_evidence_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _cached_mobile_payload(key: str, builder) -> dict[str, Any]:
    now = time.monotonic()
    with _mobile_evidence_cache_lock:
        cached = _mobile_evidence_cache.get(key)
        if cached and now - cached[0] <= _MOBILE_EVIDENCE_CACHE_TTL_SECONDS:
            return cached[1]
    payload = builder()
    with _mobile_evidence_cache_lock:
        _mobile_evidence_cache[key] = (time.monotonic(), payload)
    return payload


def _cache_mobile_payload(key: str, payload: dict[str, Any]) -> None:
    with _mobile_evidence_cache_lock:
        _mobile_evidence_cache[key] = (time.monotonic(), payload)


def _default_phone_verification_session_paths() -> dict[str, str]:
    out = Path(DEFAULT_PHONE_VERIFICATION_SESSION_OUTPUT_DIR)
    return {
        "json_path": str(out / "phone_verification_session.json"),
        "readme_path": str(out / "README.md"),
    }


def _default_mobile_verification_plan_paths() -> dict[str, str]:
    out = Path(DEFAULT_MOBILE_VERIFICATION_PLAN_OUTPUT_DIR)
    return {
        "json_path": str(out / "mobile_verification_plan.json"),
        "readme_path": str(out / "README.md"),
    }


def _default_mobile_final_verification_paths() -> dict[str, str]:
    out = Path(DEFAULT_MOBILE_FINAL_VERIFICATION_OUTPUT_DIR)
    return {
        "json_path": str(out / "mobile_final_verification.json"),
        "readme_path": str(out / "README.md"),
    }


def _mobile_verification_session_payload() -> dict[str, Any]:
    report = dict(build_phone_verification_session())
    report["default_output_paths"] = _default_phone_verification_session_paths()
    return redact_phone_verification_session(report)


def _mobile_proof_session_payload() -> dict[str, Any]:
    session = build_mobile_proof_session()
    return redact_phone_verification_session(mobile_proof_session_to_dict(session))


def _mobile_verification_plan_payload() -> dict[str, Any]:
    plan = dict(build_mobile_verification_plan())
    plan["default_output_paths"] = _default_mobile_verification_plan_paths()
    return redact_phone_verification_session(plan)


def _mobile_final_verification_payload() -> dict[str, Any]:
    report = build_mobile_final_verification()
    payload = mobile_final_verification_to_dict(report)
    payload["default_output_paths"] = _default_mobile_final_verification_paths()
    return redact_phone_verification_session(payload)


class PhoneRuntimeProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str | None = Field(default=None, max_length=80)
    app_surface: str | None = Field(default=None, max_length=20)
    url_origin: str | None = Field(default=None, max_length=180)
    url_path: str | None = Field(default=None, max_length=180)
    api_base: str | None = Field(default=None, max_length=240)
    display_mode: str | None = Field(default=None, max_length=40)
    standalone_pwa: bool | None = None
    user_agent: str | None = Field(default=None, max_length=320)
    platform: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=40)
    timezone: str | None = Field(default=None, max_length=80)
    viewport_width: int | None = Field(default=None, ge=0, le=10000)
    viewport_height: int | None = Field(default=None, ge=0, le=10000)
    screen_width: int | None = Field(default=None, ge=0, le=10000)
    screen_height: int | None = Field(default=None, ge=0, le=10000)
    device_pixel_ratio: float | None = Field(default=None, ge=0, le=10)
    max_touch_points: int | None = Field(default=None, ge=0, le=64)
    online: bool | None = None
    dry_run: bool | None = None


@router.get("/readiness/latest")
def get_mobile_readiness_latest() -> JSONResponse:
    """Return the latest token-redacted mobile readiness evidence."""
    payload = _cached_mobile_payload("readiness_latest", latest_mobile_readiness_report)
    return JSONResponse(content=payload)


@router.get("/verification-session/latest")
def get_mobile_verification_session_latest() -> JSONResponse:
    """Return the current token-redacted phone verification handoff."""
    payload = _cached_mobile_payload("verification_session_latest", _mobile_verification_session_payload)
    return JSONResponse(content=payload)


@router.get("/proof-session/latest")
def get_mobile_proof_session_latest() -> JSONResponse:
    """Return the current token-redacted phone/APK/Docker proof checklist."""
    payload = _cached_mobile_payload("proof_session_latest", _mobile_proof_session_payload)
    return JSONResponse(content=payload)


@router.get("/verification-plan/latest")
def get_mobile_verification_plan_latest() -> JSONResponse:
    """Return the current token-redacted owner verification plan."""
    payload = _cached_mobile_payload("verification_plan_latest", _mobile_verification_plan_payload)
    return JSONResponse(content=payload)


@router.get("/final-verification/latest")
def get_mobile_final_verification_latest() -> JSONResponse:
    """Return the current token-redacted final mobile verification handoff."""
    payload = _cached_mobile_payload("final_verification_latest", _mobile_final_verification_payload)
    return JSONResponse(content=payload)


@router.post("/final-verification/refresh")
def post_mobile_final_verification_refresh() -> JSONResponse:
    """Refresh the token-redacted final mobile verification handoff on disk."""
    report = build_mobile_final_verification()
    written_paths = write_mobile_final_verification(report)
    payload = mobile_final_verification_to_dict(report)
    payload["default_output_paths"] = _default_mobile_final_verification_paths()
    payload["written_paths"] = written_paths
    redacted = redact_phone_verification_session(payload)
    _cache_mobile_payload("final_verification_latest", redacted)
    _cache_mobile_payload("proof_session_latest", _mobile_proof_session_payload())
    _cache_mobile_payload("verification_plan_latest", _mobile_verification_plan_payload())
    return JSONResponse(content=redacted)


@router.post("/verification-plan/refresh")
def post_mobile_verification_plan_refresh() -> JSONResponse:
    """Refresh the token-redacted owner verification plan on disk."""
    plan = dict(build_mobile_verification_plan())
    written_paths = write_mobile_verification_plan(plan)
    payload = dict(plan)
    payload["default_output_paths"] = _default_mobile_verification_plan_paths()
    payload["written_paths"] = written_paths
    redacted = redact_phone_verification_session(payload)
    _cache_mobile_payload("verification_plan_latest", redacted)
    return JSONResponse(content=redacted)


@router.post("/verification-session/refresh")
def post_mobile_verification_session_refresh() -> JSONResponse:
    """Refresh the token-redacted phone verification handoff on disk."""
    report = dict(build_phone_verification_session())
    written_paths = write_phone_verification_session(report)
    payload = dict(report)
    payload["written_paths"] = written_paths
    redacted = redact_phone_verification_session(payload)
    _cache_mobile_payload("verification_session_latest", redacted)
    _cache_mobile_payload("verification_plan_latest", _mobile_verification_plan_payload())
    return JSONResponse(content=redacted)


@router.get("/apk/debug/metadata")
async def get_mobile_debug_apk_metadata() -> dict[str, Any]:
    """Return checksum-first metadata for the locally built debug APK."""
    return debug_apk_artifact_metadata()


@router.get("/apk/debug/download")
async def get_mobile_debug_apk_download():
    """Download the locally built debug APK through the owner-authenticated API."""
    artifact = debug_apk_artifact_metadata(download_path=DEFAULT_DOWNLOAD_PATH)
    apk_path = Path(str(artifact.get("path") or ""))
    if not artifact.get("exists") or not apk_path.exists() or not apk_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Android debug APK is missing. Run npm --prefix ui run mobile:apk:debug first.",
        )
    headers: dict[str, str] = {}
    sha256 = artifact.get("sha256")
    if isinstance(sha256, str) and sha256:
        headers["X-CAS-APK-SHA256"] = sha256
    return FileResponse(
        path=str(apk_path),
        media_type=APK_MEDIA_TYPE,
        filename=DOWNLOAD_FILENAME,
        headers=headers,
    )


@router.get("/apk/release/metadata")
async def get_mobile_release_apk_metadata() -> dict[str, Any]:
    """Return checksum-first metadata for the locally built signed release APK."""
    return release_apk_artifact_metadata()


@router.get("/apk/release/download")
async def get_mobile_release_apk_download():
    """Download the locally built signed release APK through the owner-authenticated API."""
    artifact = release_apk_artifact_metadata(download_path=DEFAULT_RELEASE_DOWNLOAD_PATH)
    apk_path = Path(str(artifact.get("path") or ""))
    if not artifact.get("exists") or not apk_path.exists() or not apk_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Android signed release APK is missing. Run npm --prefix ui run mobile:apk:release first.",
        )
    headers: dict[str, str] = {}
    sha256 = artifact.get("sha256")
    if isinstance(sha256, str) and sha256:
        headers["X-CAS-APK-SHA256"] = sha256
    return FileResponse(
        path=str(apk_path),
        media_type=APK_MEDIA_TYPE,
        filename=RELEASE_DOWNLOAD_FILENAME,
        headers=headers,
    )


@router.post("/phone-proof")
async def post_mobile_phone_proof(payload: PhoneRuntimeProofRequest, request: Request) -> dict:
    """Record bounded observational proof from the phone/PWA/APK runtime."""
    body: dict[str, Any]
    if hasattr(payload, "model_dump"):
        body = payload.model_dump()
    else:
        body = payload.dict()
    dry_run = bool(body.pop("dry_run", False))
    client_host = request.client.host if request.client else None
    proof_args = {
        "client_host": client_host,
        "forwarded_for": request.headers.get("x-forwarded-for"),
        "real_ip": request.headers.get("x-real-ip"),
        "request_user_agent": request.headers.get("user-agent"),
        "client_api_base": request.headers.get("x-cas-client-api-base"),
    }
    if dry_run:
        proof = build_phone_runtime_proof(body, **proof_args)
        proof["dry_run"] = True
        proof["status"] = "DRY_RUN_NOT_RECORDED"
        return proof
    proof = record_phone_runtime_proof(
        body,
        **proof_args,
    )
    return proof


@router.get("/phone-proof/latest")
async def get_mobile_phone_proof_latest() -> dict:
    """Return the latest fresh phone-like runtime proof, if available."""
    proof = latest_phone_runtime_proof()
    return proof or {
        "report_kind": "cas_forex_phone_runtime_proof_latest",
        "status": "MISSING",
        "phone_browser_verified": False,
        "summary": "No phone-like browser/app runtime proof has been recorded yet.",
    }
