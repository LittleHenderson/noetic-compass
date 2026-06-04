from __future__ import annotations

from api.services import atlas_live_worker_auth as worker_auth


def test_worker_auth_headers_empty_when_token_unset(monkeypatch):
    monkeypatch.setattr(worker_auth.settings, "atlas_live_worker_token", "   ")

    assert worker_auth.atlas_worker_auth_headers() == {}


def test_worker_auth_headers_send_trimmed_shared_secret(monkeypatch):
    monkeypatch.setattr(worker_auth.settings, "atlas_live_worker_token", "  worker-secret  ")

    assert worker_auth.atlas_worker_auth_headers() == {
        "X-Atlas-Worker-Token": "worker-secret"
    }
