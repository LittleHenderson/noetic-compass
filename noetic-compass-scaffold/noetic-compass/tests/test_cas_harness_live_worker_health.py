from __future__ import annotations

import httpx
import pytest

from api.routes import cas_harness_live_worker_health as live_worker


@pytest.fixture(autouse=True)
def reset_worker_settings(monkeypatch):
    monkeypatch.setattr(live_worker.settings, "atlas_live_worker_url", "https://worker.example")
    monkeypatch.setattr(live_worker.settings, "atlas_live_worker_token", "test-worker-secret")
    monkeypatch.setattr(live_worker.settings, "atlas_live_http_timeout_seconds", 30.0)


class _MockResp:
    def __init__(self, status_code: int, payload: dict | None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


def _install_mock_async_client(monkeypatch, get_handler):
    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            return await get_handler(url)

    monkeypatch.setattr(live_worker.httpx, "AsyncClient", _Client)


def test_live_worker_health_reachable_real_weights(client, monkeypatch):
    payload = {
        "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
        "is_real_model": True,
        "model_loaded": True,
        "load_error": None,
        "model_id": "EleutherAI/pythia-160m",
        "worker_version": "m2-real-pythia",
    }
    seen: dict[str, str] = {}

    async def _get(url):
        seen["url"] = url
        return _MockResp(200, payload)

    _install_mock_async_client(monkeypatch, _get)

    resp = client.get("/api/cas-harness/live-worker/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["reachable"] is True
    assert body["real_weights"] is True
    assert body["model_id"] == "EleutherAI/pythia-160m"
    assert body["worker_version"] == "m2-real-pythia"
    assert body["label"] == "Live worker connected · real Pythia weights"
    assert seen["url"].endswith("/health/realmode")


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        (
            "fake runtime env",
            {
                "verdict": "NOT_REAL_PYTHIA_WEIGHTS",
                "is_real_model": False,
                "fake_runtime_env": True,
                "model_loaded": True,
                "load_error": None,
                "model_id": "EleutherAI/pythia-160m",
                "worker_version": "m2-real-pythia",
            },
        ),
        (
            "real verdict but is_real_model false",
            {
                "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
                "is_real_model": False,
                "model_loaded": True,
                "load_error": None,
                "model_id": "EleutherAI/pythia-160m",
                "worker_version": "m2-real-pythia",
            },
        ),
        (
            "real is_real_model but wrong verdict",
            {
                "verdict": "NOT_REAL_PYTHIA_WEIGHTS",
                "is_real_model": True,
                "model_loaded": True,
                "load_error": None,
                "model_id": "EleutherAI/pythia-160m",
                "worker_version": "m2-real-pythia",
            },
        ),
    ],
)
def test_live_worker_health_reachable_demo_mode(client, monkeypatch, name, payload):
    async def _get(url):
        assert url.endswith("/health/realmode"), name
        return _MockResp(200, payload)

    _install_mock_async_client(monkeypatch, _get)

    resp = client.get("/api/cas-harness/live-worker/health")

    assert resp.status_code == 200, name
    body = resp.json()
    assert body["configured"] is True, name
    assert body["reachable"] is True, name
    assert body["real_weights"] is False, name
    assert body["label"] == "Live worker reachable · demo mode (not real weights)", name


def test_live_worker_health_unreachable(client, monkeypatch):
    async def _timeout(url):
        raise httpx.ReadTimeout("simulated worker timeout")

    _install_mock_async_client(monkeypatch, _timeout)

    resp = client.get("/api/cas-harness/live-worker/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["reachable"] is False
    assert body["real_weights"] is False
    assert body["model_id"] is None
    assert body["worker_version"] is None
    assert body["label"] == "Live worker unavailable · no live audit will run"


def test_live_worker_health_http_error_status_is_unreachable(client, monkeypatch):
    async def _get(url):
        return _MockResp(503, {"detail": "model still loading"})

    _install_mock_async_client(monkeypatch, _get)

    resp = client.get("/api/cas-harness/live-worker/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["reachable"] is False
    assert body["real_weights"] is False
    assert body["label"] == "Live worker unavailable · no live audit will run"


def test_live_worker_health_not_configured(client, monkeypatch):
    monkeypatch.setattr(live_worker.settings, "atlas_live_worker_url", "")

    resp = client.get("/api/cas-harness/live-worker/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert body["reachable"] is False
    assert body["real_weights"] is False
    assert body["model_id"] is None
    assert body["worker_version"] is None
    assert body["label"] == "Live worker not configured"


def test_live_worker_health_blocks_remote_url_without_service_token(client, monkeypatch):
    monkeypatch.setattr(live_worker.settings, "atlas_live_worker_token", "")

    resp = client.get("/api/cas-harness/live-worker/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["reachable"] is False
    assert body["real_weights"] is False
    assert body["configuration_error"] == "worker_token_required"
    assert body["label"] == "Live worker blocked · service token required"
