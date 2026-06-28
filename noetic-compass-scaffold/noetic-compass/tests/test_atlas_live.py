from __future__ import annotations

import httpx

from api.routes import atlas_live


def _mock_worker_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        atlas_live.httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(transport=transport, **kwargs),
    )


def test_atlas_live_proxy_forwards_method_configs(client, auth_headers, monkeypatch):
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"session_id": "session-1", "events_url": "/sessions/session-1/events"}

    monkeypatch.setattr(atlas_live, "_post_worker_json", fake_post)

    r = client.post(
        "/atlas/live/sessions",
        headers=auth_headers,
        json={
            "prompt": "inspect this",
            "seed": 7,
            "method_configs": {
                "foundation_probe": {
                    "enabled": True,
                    "knobs": {"layer_range": ["2"], "top_k": 3},
                },
                "evidence_packet": {
                    "enabled": False,
                    "knobs": {"export_format": "JSON"},
                },
            },
        },
    )

    assert r.status_code == 200, r.text
    assert captured["path"] == "/sessions"
    assert captured["payload"]["method_configs"]["foundation_probe"]["knobs"][
        "top_k"
    ] == 3
    assert captured["payload"]["method_configs"]["evidence_packet"]["enabled"] is False
    assert r.json()["events_url"] == "/atlas/live/session/session-1/events"
    assert r.json()["worker_events_url"] == "/sessions/session-1/events"


def test_atlas_live_proxy_rejects_payload_only_method_when_enabled(
    client,
    auth_headers,
):
    r = client.post(
        "/atlas/live/sessions",
        headers=auth_headers,
        json={
            "prompt": "inspect this",
            "method_configs": {
                "evidence_packet": {
                    "enabled": True,
                    "knobs": {"export_format": "JSON"},
                }
            },
        },
    )

    assert r.status_code == 422
    assert "evidence_packet=payload_only" in r.text


def test_atlas_live_proxy_rejects_unsupported_method_when_enabled(
    client,
    auth_headers,
):
    r = client.post(
        "/atlas/live/sessions",
        headers=auth_headers,
        json={
            "prompt": "inspect this",
            "method_configs": {
                "drive_local_eraser": {
                    "enabled": True,
                    "knobs": {"drive": "F1", "gain": 1.0},
                }
            },
        },
    )

    assert r.status_code == 422
    assert "drive_local_eraser=unsupported" in r.text


def test_atlas_live_proxy_sends_worker_token_header(client, auth_headers, monkeypatch):
    seen_headers = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers.get("X-Atlas-Worker-Token"))
        assert request.method == "POST"
        assert request.url.path == "/sessions"
        return httpx.Response(
            200,
            json={"session_id": "session-token", "events_url": "/sessions/session-token/events"},
        )

    monkeypatch.setattr(atlas_live.settings, "live_trace_worker_url", "http://worker.test")
    monkeypatch.setattr(atlas_live.settings, "atlas_live_worker_token", "  worker-secret  ")
    _mock_worker_transport(monkeypatch, handler)

    r = client.post(
        "/atlas/live/sessions",
        headers=auth_headers,
        json={"prompt": "inspect this"},
    )

    assert r.status_code == 200, r.text
    assert r.json()["session_id"] == "session-token"
    assert seen_headers == ["worker-secret"]


def test_atlas_live_realmode_health_sends_worker_token_header(
    client,
    auth_headers,
    monkeypatch,
):
    seen_headers = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers.get("X-Atlas-Worker-Token"))
        assert request.method == "GET"
        assert request.url.path == "/health/realmode"
        return httpx.Response(
            200,
            json={
                "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
                "is_real_model": True,
                "model_loaded": True,
                "model_id": "EleutherAI/pythia-160m",
            },
        )

    monkeypatch.setattr(atlas_live.settings, "live_trace_worker_url", "http://worker.test")
    monkeypatch.setattr(atlas_live.settings, "atlas_live_worker_token", "worker-secret")
    _mock_worker_transport(monkeypatch, handler)

    r = client.get("/atlas/live/health/realmode", headers=auth_headers)

    assert r.status_code == 200, r.text
    assert r.json()["verdict"] == "REAL_PYTHIA_WEIGHTS_LOADED"
    assert seen_headers == ["worker-secret"]
