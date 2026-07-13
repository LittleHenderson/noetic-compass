from __future__ import annotations

import sys
from types import ModuleType

import pytest

from api.services import production_dependency_readiness as readiness


@pytest.fixture(autouse=True)
def _reset_dependency_configuration(monkeypatch):
    monkeypatch.setattr(readiness.settings, "atlas_live_worker_url", "")
    monkeypatch.setattr(readiness.settings, "atlas_live_worker_token", "")
    monkeypatch.setattr(readiness.settings, "atlas_live_http_timeout_seconds", 30.0)
    monkeypatch.setattr(
        readiness.settings, "evidence_packet_object_store_enabled", False
    )
    for name in (
        "CAS_HARNESS_EVIDENCE_ANCHOR_MODE",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    readiness.clear_production_dependency_readiness_cache()
    yield
    readiness.clear_production_dependency_readiness_cache()


class _Response:
    def __init__(self, status_code: int, payload: object):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _mock_async_client(monkeypatch, response: _Response):
    seen: dict[str, object] = {}

    class _Client:
        def __init__(self, *args, **kwargs):
            seen["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            seen["url"] = url
            seen["headers"] = kwargs.get("headers")
            return response

    monkeypatch.setattr(readiness.httpx, "AsyncClient", _Client)
    return seen


@pytest.mark.asyncio
async def test_remote_worker_without_service_token_fails_readiness(monkeypatch):
    monkeypatch.setattr(
        readiness.settings,
        "atlas_live_worker_url",
        "https://worker.example",
    )

    check = await readiness.check_live_worker_readiness()

    assert check == {
        "configured": True,
        "required": True,
        "status": "error",
        "reason": "worker_token_required",
    }


@pytest.mark.asyncio
async def test_worker_realmode_probe_is_strict_metadata_only(monkeypatch):
    monkeypatch.setattr(
        readiness.settings,
        "atlas_live_worker_url",
        "https://worker.example",
    )
    monkeypatch.setattr(
        readiness.settings,
        "atlas_live_worker_token",
        "test-service-token",
    )
    seen = _mock_async_client(
        monkeypatch,
        _Response(
            200,
            {
                "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
                "is_real_model": True,
                "fake_runtime_env": False,
                "model_loaded": True,
                "load_error": None,
                "manifest_is_real_model": True,
                "model_id": "EleutherAI/pythia-160m",
                "worker_version": "worker-v1",
            },
        ),
    )

    check = await readiness.check_live_worker_readiness()

    assert check["status"] == "ok"
    assert check["authority"] == "verified"
    assert check["real_weights"] is True
    assert str(seen["url"]).endswith("/health/realmode")
    assert seen["headers"] == {"X-Atlas-Worker-Token": "test-service-token"}


@pytest.mark.asyncio
async def test_worker_demo_payload_fails_without_exposing_load_error(monkeypatch):
    monkeypatch.setattr(
        readiness.settings,
        "atlas_live_worker_url",
        "https://worker.example",
    )
    monkeypatch.setattr(readiness.settings, "atlas_live_worker_token", "token")
    _mock_async_client(
        monkeypatch,
        _Response(
            200,
            {
                "verdict": "NOT_REAL_PYTHIA_WEIGHTS",
                "is_real_model": False,
                "fake_runtime_env": True,
                "model_loaded": False,
                "load_error": "sensitive provider detail",
                "manifest_is_real_model": True,
                "model_id": "EleutherAI/pythia-160m",
            },
        ),
    )

    check = await readiness.check_live_worker_readiness()

    assert check["status"] == "error"
    assert check["reason"] == "realmode_contract_failed"
    assert "sensitive provider detail" not in repr(check)


def _configure_s3(monkeypatch):
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET", "evidence-bucket")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION", "us-west-2")
    monkeypatch.setenv(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE"
    )
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "30")


@pytest.mark.asyncio
async def test_s3_worm_probe_requires_object_lock_and_versioning(monkeypatch):
    _configure_s3(monkeypatch)
    seen: dict[str, str] = {}

    def _probe(bucket: str, region: str):
        seen.update(bucket=bucket, region=region)
        return {"object_lock_enabled": True, "versioning_enabled": True}

    monkeypatch.setattr(readiness, "_probe_s3_worm_authority", _probe)

    check = await readiness.check_s3_worm_readiness()

    assert check == {
        "configured": True,
        "required": True,
        "status": "ok",
        "authority": "verified",
        "object_lock_mode": "GOVERNANCE",
        "retention_days": 30,
    }
    assert seen == {"bucket": "evidence-bucket", "region": "us-west-2"}


@pytest.mark.asyncio
async def test_s3_authentication_failure_is_normalized_without_sdk_detail(monkeypatch):
    _configure_s3(monkeypatch)

    class _ProviderError(Exception):
        response = {
            "Error": {
                "Code": "InvalidAccessKeyId",
                "Message": "do not expose this provider response",
            }
        }

    def _probe(bucket: str, region: str):
        raise _ProviderError(f"secret detail for {bucket} in {region}")

    monkeypatch.setattr(readiness, "_probe_s3_worm_authority", _probe)

    check = await readiness.check_s3_worm_readiness()

    assert check == {
        "configured": True,
        "required": True,
        "status": "error",
        "reason": "authentication_failed",
    }
    assert "do not expose" not in repr(check)
    assert "evidence-bucket" not in repr(check)


@pytest.mark.asyncio
async def test_dark_dependencies_are_non_blocking():
    snapshot = await readiness.get_production_dependency_readiness(
        force_refresh=True
    )

    assert snapshot["ready"] is True
    assert snapshot["checks"]["live_worker"]["status"] == "not_configured"
    assert snapshot["checks"]["s3_worm"]["status"] == "not_configured"


def test_ready_endpoint_returns_503_for_broken_configured_dependency(
    client, monkeypatch
):
    import api.services.production_dependency_readiness as dependency_service

    monkeypatch.setitem(sys.modules, "cas_engine", ModuleType("cas_engine"))

    async def _broken_dependencies():
        return {
            "ready": False,
            "checked_at": "2026-07-13T12:00:00+00:00",
            "cache_ttl_seconds": 30,
            "checks": {
                "live_worker": {
                    "configured": True,
                    "required": True,
                    "status": "error",
                    "reason": "worker_token_required",
                },
                "s3_worm": {
                    "configured": True,
                    "required": True,
                    "status": "error",
                    "reason": "authentication_failed",
                },
            },
        }

    monkeypatch.setattr(
        dependency_service,
        "get_production_dependency_readiness",
        _broken_dependencies,
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["status"] == "degraded"
    assert body["ready"] is False
    assert body["checks"]["live_worker"]["reason"] == "worker_token_required"
    assert body["checks"]["s3_worm"]["reason"] == "authentication_failed"


def test_process_liveness_does_not_call_external_dependencies(client, monkeypatch):
    import api.services.production_dependency_readiness as dependency_service

    async def _must_not_run():
        raise AssertionError("/health must not call dependency readiness")

    monkeypatch.setattr(
        dependency_service,
        "get_production_dependency_readiness",
        _must_not_run,
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
