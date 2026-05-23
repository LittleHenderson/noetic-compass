from __future__ import annotations

import pytest

from api.routes import atlas_live


@pytest.fixture(autouse=True)
def reset_live_state(monkeypatch):
    atlas_live._ip_opens.clear()
    atlas_live._code_opens.clear()
    monkeypatch.setattr(atlas_live.settings, "atlas_live_invite_codes", "alpha-code")
    monkeypatch.setattr(atlas_live.settings, "atlas_live_worker_url", "https://worker.example")
    monkeypatch.setattr(atlas_live.settings, "atlas_live_session_rate_limit_per_ip_hour", 3)
    monkeypatch.setattr(atlas_live.settings, "atlas_live_invite_daily_limit", 10)


def test_live_session_requires_invite_code(client):
    resp = client.post("/atlas/live/session", json={"prompt": "hello"})
    assert resp.status_code == 401


def test_live_session_rejects_bad_invite_code(client):
    resp = client.post(
        "/atlas/live/session",
        headers={"X-Atlas-Invite-Code": "wrong"},
        json={"prompt": "hello"},
    )
    assert resp.status_code == 403


def test_live_session_returns_stream_token(client, monkeypatch):
    async def fake_create_worker_session(req):
        return {"session_id": "worker-session-1", "events_url": "/sessions/worker-session-1/events"}

    monkeypatch.setattr(atlas_live, "_create_worker_session", fake_create_worker_session)

    resp = client.post(
        "/atlas/live/session",
        headers={"X-Atlas-Invite-Code": "alpha-code"},
        json={"prompt": "hello", "max_new_tokens": 4},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "live"
    assert body["model_id"] == "EleutherAI/pythia-160m"
    assert body["session_id"] == "worker-session-1"
    assert "stream_token=" in body["stream_url"]
    assert body["stream_token"]


def test_live_session_forwards_method_config_to_worker(client, monkeypatch):
    seen = {}

    async def fake_create_worker_session(req):
        seen["payload"] = req.model_dump()
        return {"session_id": "worker-session-controls", "events_url": "/sessions/worker-session-controls/events"}

    monkeypatch.setattr(atlas_live, "_create_worker_session", fake_create_worker_session)

    resp = client.post(
        "/atlas/live/session",
        headers={"X-Atlas-Invite-Code": "alpha-code"},
        json={
            "prompt": "hello",
            "probes": ["active_trace"],
            "method_config": {
                "enabled_methods": ["foundation_probe"],
                "knobs": {"foundation_probe": {"layer_range": ["5"]}},
            },
        },
    )

    assert resp.status_code == 200
    assert seen["payload"]["probes"] == ["active_trace"]
    assert seen["payload"]["method_config"]["enabled_methods"] == ["foundation_probe"]
    assert seen["payload"]["method_config"]["knobs"]["foundation_probe"]["layer_range"] == ["5"]


def test_live_session_rate_limits_by_ip(client, monkeypatch):
    async def fake_create_worker_session(req):
        return {"session_id": "worker-session-rate", "events_url": "/sessions/worker-session-rate/events"}

    monkeypatch.setattr(atlas_live, "_create_worker_session", fake_create_worker_session)

    for _ in range(3):
        resp = client.post(
            "/atlas/live/session",
            headers={"X-Atlas-Invite-Code": "alpha-code"},
            json={"prompt": "hello"},
        )
        assert resp.status_code == 200

    blocked = client.post(
        "/atlas/live/session",
        headers={"X-Atlas-Invite-Code": "alpha-code"},
        json={"prompt": "hello"},
    )
    assert blocked.status_code == 429


def test_live_session_does_not_count_failed_worker_open_against_limit(client, monkeypatch):
    calls = {"count": 0}

    async def flaky_create_worker_session(req):
        calls["count"] += 1
        if calls["count"] == 1:
            raise atlas_live.HTTPException(status_code=502, detail="simulated worker failure")
        return {"session_id": f"worker-session-{calls['count']}", "events_url": "/sessions/ok/events"}

    monkeypatch.setattr(atlas_live, "_create_worker_session", flaky_create_worker_session)
    monkeypatch.setattr(atlas_live.settings, "atlas_live_session_rate_limit_per_ip_hour", 1)

    failed = client.post(
        "/atlas/live/session",
        headers={"X-Atlas-Invite-Code": "alpha-code"},
        json={"prompt": "hello"},
    )
    assert failed.status_code == 502

    ok = client.post(
        "/atlas/live/session",
        headers={"X-Atlas-Invite-Code": "alpha-code"},
        json={"prompt": "hello"},
    )
    assert ok.status_code == 200

    blocked = client.post(
        "/atlas/live/session",
        headers={"X-Atlas-Invite-Code": "alpha-code"},
        json={"prompt": "hello"},
    )
    assert blocked.status_code == 429


def test_live_events_require_matching_stream_token(client, monkeypatch):
    async def fake_create_worker_session(req):
        return {"session_id": "worker-session-2", "events_url": "/sessions/worker-session-2/events"}

    monkeypatch.setattr(atlas_live, "_create_worker_session", fake_create_worker_session)

    session_resp = client.post(
        "/atlas/live/session",
        headers={"X-Atlas-Invite-Code": "alpha-code"},
        json={"prompt": "hello"},
    )
    token = session_resp.json()["stream_token"]

    missing = client.get("/atlas/live/session/worker-session-2/events")
    assert missing.status_code == 401

    wrong_sid = client.get(f"/atlas/live/session/other-session/events?stream_token={token}")
    assert wrong_sid.status_code == 403


def test_live_events_stream_worker_sse(client, monkeypatch):
    async def fake_create_worker_session(req):
        return {"session_id": "worker-session-3", "events_url": "/sessions/worker-session-3/events"}

    async def fake_iter_worker_events(session_id):
        assert session_id == "worker-session-3"
        yield b'event: manifest\ndata: {"type":"manifest","manifest":{"is_real_model":true}}\n\n'
        yield b'event: token\ndata: {"type":"token","token_index":0,"token":"hello"}\n\n'

    monkeypatch.setattr(atlas_live, "_create_worker_session", fake_create_worker_session)
    monkeypatch.setattr(atlas_live, "_iter_worker_events", fake_iter_worker_events)

    session_resp = client.post(
        "/atlas/live/session",
        headers={"X-Atlas-Invite-Code": "alpha-code"},
        json={"prompt": "hello"},
    )
    stream_url = session_resp.json()["stream_url"]

    with client.stream("GET", stream_url) as resp:
        body = b"".join(resp.iter_bytes()).decode("utf-8")

    assert resp.status_code == 200
    assert "event: manifest" in body
    assert "event: token" in body
