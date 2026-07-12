from __future__ import annotations

import pytest

from api.services import atlas_live_worker_config as worker_config


@pytest.fixture(autouse=True)
def reset_worker_settings(monkeypatch):
    monkeypatch.setattr(worker_config.settings, "atlas_live_worker_url", "")
    monkeypatch.setattr(worker_config.settings, "atlas_live_worker_token", "")


def test_empty_url_keeps_live_worker_dark():
    target = worker_config.atlas_worker_target()

    assert target.configured is False
    assert target.allowed is False
    assert target.error == worker_config.WORKER_CONFIG_NOT_CONFIGURED


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8080",
        "http://worker.localhost:8080",
        "http://127.0.0.1:8080",
        "http://[::1]:8080",
    ],
)
def test_loopback_worker_may_remain_tokenless_for_local_development(monkeypatch, url):
    monkeypatch.setattr(worker_config.settings, "atlas_live_worker_url", url)

    target = worker_config.atlas_worker_target()

    assert target.allowed is True
    assert target.base_url == url
    assert target.error is None


def test_remote_worker_without_service_token_is_blocked(monkeypatch):
    monkeypatch.setattr(
        worker_config.settings,
        "atlas_live_worker_url",
        "https://pod-id-8080.proxy.runpod.net",
    )

    target = worker_config.atlas_worker_target()

    assert target.configured is True
    assert target.allowed is False
    assert target.error == worker_config.WORKER_CONFIG_TOKEN_REQUIRED


def test_remote_worker_with_service_token_is_allowed_and_normalized(monkeypatch):
    monkeypatch.setattr(
        worker_config.settings,
        "atlas_live_worker_url",
        "  https://pod-id-8080.proxy.runpod.net/  ",
    )
    monkeypatch.setattr(worker_config.settings, "atlas_live_worker_token", " secret ")

    target = worker_config.atlas_worker_target()

    assert target.allowed is True
    assert target.base_url == "https://pod-id-8080.proxy.runpod.net"


@pytest.mark.parametrize(
    "url",
    [
        "pod-id-8080.proxy.runpod.net",
        "ftp://pod-id-8080.proxy.runpod.net",
        "https://user:secret@pod-id-8080.proxy.runpod.net",
        "https://pod-id-8080.proxy.runpod.net/#fragment",
    ],
)
def test_invalid_or_secret_bearing_worker_url_is_blocked(monkeypatch, url):
    monkeypatch.setattr(worker_config.settings, "atlas_live_worker_url", url)
    monkeypatch.setattr(worker_config.settings, "atlas_live_worker_token", "secret")

    target = worker_config.atlas_worker_target()

    assert target.allowed is False
    assert target.error == worker_config.WORKER_CONFIG_INVALID_URL
