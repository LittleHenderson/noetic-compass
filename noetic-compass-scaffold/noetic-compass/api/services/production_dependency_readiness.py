"""Cheap, non-secret readiness checks for configured production dependencies.

``/health`` is process liveness and must stay independent of external services.
This module backs ``/health/ready`` with a stricter contract: a configured live
worker or S3 Object-Lock authority is load-bearing, so a broken configuration
or failed authority probe makes readiness unavailable.

The probes deliberately avoid writes and model inference.  The worker check
reads its metadata-only ``/health/realmode`` endpoint; the S3 check reads only
bucket Object-Lock and versioning configuration.  Results are cached briefly
to keep operator polling from hammering either dependency.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
import os
import threading
import time
from typing import Any, Mapping

import httpx

from api.config import settings
from api.services.atlas_live_worker_auth import atlas_worker_auth_headers
from api.services.atlas_live_worker_config import (
    WORKER_CONFIG_NOT_CONFIGURED,
    atlas_worker_target,
)


EXPECTED_MODEL_ID = "EleutherAI/pythia-160m"
REALMODE_PASS = "REAL_PYTHIA_WEIGHTS_LOADED"
_MAX_WORKER_TIMEOUT_SECONDS = 5.0
_CACHE_TTL_SECONDS = 30.0

_cache_lock = threading.Lock()
_cache_entry: tuple[tuple[Any, ...], float, dict[str, Any]] | None = None


def clear_production_dependency_readiness_cache() -> None:
    """Clear the short-lived probe cache (primarily for tests/config reloads)."""

    global _cache_entry
    with _cache_lock:
        _cache_entry = None


def _cache_key() -> tuple[Any, ...]:
    """Return a private configuration key without retaining credential values."""

    return (
        settings.atlas_live_worker_url.strip(),
        bool(settings.atlas_live_worker_token.strip()),
        float(settings.atlas_live_http_timeout_seconds),
        bool(settings.evidence_packet_object_store_enabled),
        os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "").strip().lower(),
        os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "").strip(),
        os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION", "").strip(),
        os.environ.get(
            "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", ""
        ).strip().upper(),
        os.environ.get(
            "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", ""
        ).strip(),
        bool(os.environ.get("AWS_ACCESS_KEY_ID", "").strip()),
        bool(os.environ.get("AWS_SESSION_TOKEN", "").strip()),
    )


async def get_production_dependency_readiness(
    *, force_refresh: bool = False
) -> dict[str, Any]:
    """Return cached readiness for configured worker and WORM dependencies."""

    global _cache_entry
    key = _cache_key()
    now = time.monotonic()
    if not force_refresh:
        with _cache_lock:
            if _cache_entry is not None:
                cached_key, expires_at, payload = _cache_entry
                if cached_key == key and expires_at > now:
                    return deepcopy(payload)

    worker, worm = await asyncio.gather(
        check_live_worker_readiness(),
        check_s3_worm_readiness(),
    )
    checks = {"live_worker": worker, "s3_worm": worm}
    payload = {
        "ready": all(_dependency_ready(check) for check in checks.values()),
        "checked_at": datetime.now(UTC).isoformat(),
        "cache_ttl_seconds": int(_CACHE_TTL_SECONDS),
        "checks": checks,
    }
    with _cache_lock:
        _cache_entry = (key, time.monotonic() + _CACHE_TTL_SECONDS, deepcopy(payload))
    return payload


def _dependency_ready(check: Mapping[str, Any]) -> bool:
    return check.get("required") is not True or check.get("status") == "ok"


async def check_live_worker_readiness() -> dict[str, Any]:
    """Verify configured worker authority and real-weight metadata, without inference."""

    target = atlas_worker_target()
    if target.error == WORKER_CONFIG_NOT_CONFIGURED:
        return {
            "configured": False,
            "required": False,
            "status": "not_configured",
        }
    if not target.allowed:
        return {
            "configured": True,
            "required": True,
            "status": "error",
            "reason": target.error or "invalid_worker_configuration",
        }

    timeout_seconds = min(
        _MAX_WORKER_TIMEOUT_SECONDS,
        max(0.1, float(settings.atlas_live_http_timeout_seconds)),
    )
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:
            response = await client.get(
                f"{target.base_url}/health/realmode",
                headers=atlas_worker_auth_headers(),
            )
    except httpx.TimeoutException:
        return _worker_error("timeout")
    except httpx.HTTPError:
        return _worker_error("unreachable")

    if response.status_code in {401, 403}:
        return _worker_error("authentication_failed")
    if response.status_code != 200:
        return _worker_error("unreachable")
    try:
        payload = response.json()
    except ValueError:
        return _worker_error("invalid_response")
    if not isinstance(payload, Mapping):
        return _worker_error("invalid_response")
    if not _realmode_is_ready(payload):
        return _worker_error("realmode_contract_failed")

    result: dict[str, Any] = {
        "configured": True,
        "required": True,
        "status": "ok",
        "authority": "verified",
        "real_weights": True,
    }
    model_id = _safe_text(payload.get("model_id"))
    worker_version = _safe_text(payload.get("worker_version"))
    if model_id:
        result["model_id"] = model_id
    if worker_version:
        result["worker_version"] = worker_version
    return result


def _worker_error(reason: str) -> dict[str, Any]:
    return {
        "configured": True,
        "required": True,
        "status": "error",
        "reason": reason,
        "real_weights": False,
    }


def _realmode_is_ready(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("verdict") == REALMODE_PASS
        and payload.get("is_real_model") is True
        and payload.get("fake_runtime_env") is False
        and payload.get("model_loaded") is True
        and payload.get("load_error") is None
        and payload.get("manifest_is_real_model") is True
        and payload.get("model_id") == EXPECTED_MODEL_ID
    )


async def check_s3_worm_readiness() -> dict[str, Any]:
    """Verify configured S3 WORM authority with read-only bucket metadata calls."""

    mode = (
        os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "disabled")
        .strip()
        .lower()
        or "disabled"
    )
    object_store_enabled = bool(settings.evidence_packet_object_store_enabled)
    if mode not in {"disabled", "local", "s3"}:
        return _worm_error("unsupported_anchor_mode")
    if mode != "s3" and not object_store_enabled:
        return {
            "configured": mode == "local",
            "required": False,
            "status": "local_only" if mode == "local" else "not_configured",
        }

    bucket = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "").strip()
    region = os.environ.get("CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION", "").strip()
    lock_mode = os.environ.get(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", ""
    ).strip().upper()
    retention_days = os.environ.get(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", ""
    ).strip()
    if not bucket or not lock_mode or not retention_days:
        return _worm_error("s3_configuration_incomplete")
    if bucket.startswith("s3://") or "/" in bucket or "\\" in bucket:
        return _worm_error("s3_configuration_invalid")
    if lock_mode not in {"GOVERNANCE", "COMPLIANCE"}:
        return _worm_error("object_lock_policy_invalid")
    if not retention_days.isdigit() or int(retention_days) < 1:
        return _worm_error("object_lock_policy_invalid")

    try:
        probe = await asyncio.to_thread(_probe_s3_worm_authority, bucket, region)
    except ImportError:
        return _worm_error("s3_client_unavailable")
    except Exception as exc:  # SDK exception types are optional runtime imports.
        return _worm_error(_normalize_s3_error(exc))

    if probe.get("object_lock_enabled") is not True:
        return _worm_error("object_lock_disabled")
    if probe.get("versioning_enabled") is not True:
        return _worm_error("versioning_disabled")
    return {
        "configured": True,
        "required": True,
        "status": "ok",
        "authority": "verified",
        "object_lock_mode": lock_mode,
        "retention_days": int(retention_days),
    }


def _worm_error(reason: str) -> dict[str, Any]:
    return {
        "configured": True,
        "required": True,
        "status": "error",
        "reason": reason,
    }


def _probe_s3_worm_authority(bucket: str, region: str) -> dict[str, bool]:
    """Perform the two read-only S3 calls needed for WORM capability proof."""

    import boto3  # type: ignore[import-not-found]
    from botocore.config import Config  # type: ignore[import-not-found]

    kwargs: dict[str, Any] = {
        "config": Config(
            connect_timeout=3,
            read_timeout=3,
            retries={"max_attempts": 1, "mode": "standard"},
        )
    }
    if region:
        kwargs["region_name"] = region
    client = boto3.client("s3", **kwargs)
    lock = client.get_object_lock_configuration(Bucket=bucket)
    versioning = client.get_bucket_versioning(Bucket=bucket)
    lock_config = (
        lock.get("ObjectLockConfiguration") if isinstance(lock, Mapping) else None
    )
    return {
        "object_lock_enabled": isinstance(lock_config, Mapping)
        and lock_config.get("ObjectLockEnabled") == "Enabled",
        "versioning_enabled": isinstance(versioning, Mapping)
        and versioning.get("Status") == "Enabled",
    }


def _normalize_s3_error(exc: Exception) -> str:
    """Map provider exceptions to stable non-secret readiness reasons."""

    error_code = ""
    response = getattr(exc, "response", None)
    if isinstance(response, Mapping):
        error = response.get("Error")
        if isinstance(error, Mapping):
            error_code = str(error.get("Code") or "")
    class_name = type(exc).__name__
    if class_name in {"NoCredentialsError", "PartialCredentialsError"}:
        return "credentials_unavailable"
    if error_code in {
        "InvalidAccessKeyId",
        "InvalidClientTokenId",
        "SignatureDoesNotMatch",
        "ExpiredToken",
        "TokenRefreshRequired",
    }:
        return "authentication_failed"
    if error_code in {"AccessDenied", "AllAccessDisabled", "UnauthorizedOperation"}:
        return "authority_denied"
    if error_code in {"NoSuchBucket", "NotFound", "404"}:
        return "bucket_unavailable"
    if error_code == "ObjectLockConfigurationNotFoundError":
        return "object_lock_disabled"
    if class_name in {
        "ConnectTimeoutError",
        "EndpointConnectionError",
        "ReadTimeoutError",
    }:
        return "unreachable"
    return "authority_check_failed"


def _safe_text(value: object) -> str | None:
    return value if isinstance(value, str) and 0 < len(value) <= 200 else None


__all__ = [
    "check_live_worker_readiness",
    "check_s3_worm_readiness",
    "clear_production_dependency_readiness_cache",
    "get_production_dependency_readiness",
]
