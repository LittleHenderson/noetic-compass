from __future__ import annotations


def _session_payload() -> dict:
    return {
        "prompt": "inspect this",
        "model_id": "EleutherAI/pythia-160m",
        "max_new_tokens": 1,
        "temperature": 0.0,
    }


def test_worker_token_auth_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv("ATLAS_LIVE_WORKER_TOKEN", raising=False)

    r = client.post("/sessions", json=_session_payload())

    assert r.status_code == 200, r.text
    assert r.json()["session_id"]


def test_worker_token_auth_rejects_missing_or_wrong_token(client, monkeypatch):
    monkeypatch.setenv("ATLAS_LIVE_WORKER_TOKEN", "worker-secret")

    missing = client.post("/sessions", json=_session_payload())
    wrong = client.post(
        "/sessions",
        headers={"X-Atlas-Worker-Token": "wrong"},
        json=_session_payload(),
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401


def test_worker_token_auth_accepts_matching_token(client, monkeypatch):
    monkeypatch.setenv("ATLAS_LIVE_WORKER_TOKEN", "worker-secret")

    r = client.post(
        "/sessions",
        headers={"X-Atlas-Worker-Token": "worker-secret"},
        json=_session_payload(),
    )

    assert r.status_code == 200, r.text
    assert r.json()["session_id"]


def test_worker_token_auth_exempts_health_routes(client, monkeypatch):
    monkeypatch.setenv("ATLAS_LIVE_WORKER_TOKEN", "worker-secret")

    assert client.get("/health").status_code == 200
    assert client.get("/health/realmode").status_code == 200
