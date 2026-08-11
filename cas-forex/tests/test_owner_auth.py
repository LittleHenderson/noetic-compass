"""Owner-auth policy tests.

The whole point: the owner's own machine (loopback) drives with zero friction,
while any OTHER device on the network is refused unless the owner turned LAN
mode on AND the request carries the owner token. Proven here as pure policy
(``evaluate_request``) plus the token store round-trip.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from cas_forex import owner_auth


@pytest.fixture(autouse=True)
def _isolated_auth(tmp_path):
    owner_auth.set_auth_path_for_tests(tmp_path / "owner-auth.json")
    yield
    owner_auth.set_auth_path_for_tests(None)


def _eval(host, *, path="/api/forex/money-movement/deposit", method="POST", headers=None):
    return owner_auth.evaluate_request(
        method=method, client_host=host, path=path, headers=headers or {}
    )


# --- loopback is always the owner --------------------------------------------

@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost", "testclient"])
def test_loopback_is_always_allowed_no_token(host):
    # Even a mutating money route, LAN mode off, no token: the owner's own PC.
    assert _eval(host).allow is True


def test_loopback_preview_proxy_uses_forwarded_phone_host():
    headers = {"X-Forwarded-For": "10.0.0.55"}

    lan_off = _eval("127.0.0.1", headers=headers)
    assert lan_off.allow is False
    assert lan_off.status == 403

    owner_auth.set_lan_mode(True)
    no_token = _eval("127.0.0.1", headers=headers)
    assert no_token.allow is False
    assert no_token.status == 401

    token = owner_auth.current_token()
    assert token
    with_token = _eval("127.0.0.1", headers=headers | {"X-CAS-Owner-Token": token})
    assert with_token.allow is True


def test_loopback_preview_proxy_with_loopback_forwarded_host_stays_local():
    assert _eval("127.0.0.1", headers={"X-Forwarded-For": "127.0.0.1"}).allow is True
    assert _eval("127.0.0.1", headers={"X-Forwarded-For": "::1"}).allow is True


def test_offbox_cannot_spoof_forwarded_loopback():
    d = _eval("10.0.0.55", headers={"X-Forwarded-For": "127.0.0.1"})
    assert d.allow is False
    assert d.status == 403


# --- off-box requires LAN mode + token ---------------------------------------

def test_offbox_with_lan_off_is_refused_403():
    d = _eval("10.0.0.6")
    assert d.allow is False
    assert d.status == 403


def test_offbox_lan_on_without_token_is_401():
    owner_auth.set_lan_mode(True)
    d = _eval("10.0.0.6")
    assert d.allow is False
    assert d.status == 401


def test_offbox_lan_on_wrong_token_is_401():
    owner_auth.set_lan_mode(True)
    d = _eval("10.0.0.6", headers={"X-CAS-Owner-Token": "not-the-token"})
    assert d.allow is False
    assert d.status == 401


def test_offbox_lan_on_correct_token_header_allows():
    token = owner_auth.get_or_create_token()
    owner_auth.set_lan_mode(True)
    assert _eval("10.0.0.6", headers={"X-CAS-Owner-Token": token}).allow is True


def test_offbox_lan_on_correct_bearer_allows():
    token = owner_auth.get_or_create_token()
    owner_auth.set_lan_mode(True)
    assert _eval("10.0.0.6", headers={"Authorization": f"Bearer {token}"}).allow is True


# --- exemptions ---------------------------------------------------------------

def test_cors_preflight_always_allowed():
    assert _eval("10.0.0.6", method="OPTIONS").allow is True


def test_health_is_exempt_offbox():
    assert _eval("10.0.0.6", path="/api/forex/health", method="GET").allow is True


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/forex/notifications/backend"),
        ("GET", "/api/forex/notifications/subscriptions"),
        ("POST", "/api/forex/notifications/backend/update"),
        ("POST", "/api/forex/notifications/backend/reset"),
        ("POST", "/api/forex/notifications/subscribe"),
        ("POST", "/api/forex/notifications/unsubscribe"),
        ("POST", "/api/forex/notifications/test-push"),
        ("GET", "/api/forex/webhook-notifications/subscriptions"),
        ("GET", "/api/forex/webhook-notifications/critical-readiness"),
        ("POST", "/api/forex/webhook-notifications/subscribe"),
        ("POST", "/api/forex/webhook-notifications/unsubscribe"),
        ("POST", "/api/forex/webhook-notifications/test"),
        ("POST", "/api/forex/external-monitoring/update"),
        ("POST", "/api/forex/external-monitoring/reset"),
    ],
)
def test_notification_operator_routes_are_not_public_offbox(method, path):
    lan_off = _eval("10.0.0.55", method=method, path=path)
    assert lan_off.allow is False
    assert lan_off.status == 403

    owner_auth.set_lan_mode(True)
    no_token = _eval("10.0.0.55", method=method, path=path)
    assert no_token.allow is False
    assert no_token.status == 401

    token = owner_auth.current_token()
    assert token
    paired_phone = _eval(
        "10.0.0.55",
        method=method,
        path=path,
        headers={"X-CAS-Owner-Token": token},
    )
    assert paired_phone.allow is True


# --- token store --------------------------------------------------------------

def test_token_is_created_once_and_stable():
    assert owner_auth.current_token() is None
    t1 = owner_auth.get_or_create_token()
    t2 = owner_auth.get_or_create_token()
    assert t1 and t1 == t2
    assert owner_auth.current_token() == t1


def test_owner_token_is_encrypted_on_disk(tmp_path, monkeypatch):
    monkeypatch.delenv("CAS_FOREX_OWNER_TOKEN", raising=False)
    path = tmp_path / "owner-auth.json"

    token = owner_auth.get_or_create_token()

    persisted = path.read_text(encoding="utf-8")
    assert token not in persisted
    assert '"encrypted": true' in persisted.lower()
    assert '"secret_storage"' in persisted
    assert owner_auth.current_token() == token
    assert owner_auth.auth_store_status()["at_rest_encrypted"] is True


def test_legacy_plaintext_owner_token_is_migrated_to_encrypted(tmp_path, monkeypatch):
    monkeypatch.delenv("CAS_FOREX_OWNER_TOKEN", raising=False)
    path = tmp_path / "owner-auth.json"
    path.write_text(
        json.dumps({"owner_token": "legacy-owner-token", "lan_mode_enabled": True}),
        encoding="utf-8",
    )

    assert owner_auth.current_token() == "legacy-owner-token"
    assert owner_auth.lan_mode_enabled() is True
    rewritten = path.read_text(encoding="utf-8")
    assert "legacy-owner-token" not in rewritten
    assert '"encrypted": true' in rewritten.lower()


def test_rotate_changes_the_token_and_unpairs():
    t1 = owner_auth.get_or_create_token()
    t2 = owner_auth.rotate_token()
    assert t2 != t1
    assert owner_auth.verify_token(t1) is False
    assert owner_auth.verify_token(t2) is True


def test_verify_token_is_false_without_a_store():
    assert owner_auth.verify_token("anything") is False
    assert owner_auth.verify_token(None) is False


def test_extract_token_from_both_header_forms():
    assert owner_auth.extract_token({"X-CAS-Owner-Token": "abc"}) == "abc"
    assert owner_auth.extract_token({"Authorization": "Bearer xyz"}) == "xyz"
    assert owner_auth.extract_token({"authorization": "bearer LOWER"}) == "LOWER"
    assert owner_auth.extract_token({}) is None


def test_enabling_lan_mode_ensures_a_token_exists():
    assert owner_auth.current_token() is None
    owner_auth.set_lan_mode(True)
    assert owner_auth.current_token() is not None
    assert owner_auth.lan_mode_enabled() is True


def test_mask_never_reveals_full_token():
    token = owner_auth.get_or_create_token()
    masked = owner_auth.mask_token(token)
    assert masked.endswith(token[-4:])
    assert token not in masked


def test_pairing_payload_includes_fragment_only_phone_url(monkeypatch):
    monkeypatch.setenv("CAS_FOREX_LAN_HOST", "10.9.8.7")
    token = owner_auth.get_or_create_token()

    payload = owner_auth.pairing_payload()

    assert payload["owner_token"] == token
    assert payload["pairing_hash_key"] == owner_auth.PAIRING_HASH_KEY
    pairing_url = next(url for url in payload["pairing_urls"] if "10.9.8.7:4173" in url)
    parsed = urlsplit(pairing_url)
    assert parsed.scheme == "http"
    assert parsed.netloc == "10.9.8.7:4173"
    assert parse_qs(parsed.query) == {"page": ["quick-start"]}
    assert token not in parsed.query
    assert parse_qs(parsed.fragment) == {
        owner_auth.PAIRING_HASH_KEY: [token],
        owner_auth.API_BASE_HASH_KEY: ["http://10.9.8.7:4173/api/forex"],
    }
    assert payload["api_base_hash_key"] == owner_auth.API_BASE_HASH_KEY
    assert payload["pairing_api_bases"][0] == "http://10.9.8.7:4173/api/forex"
    assert payload["direct_api_bases"][0] == "http://10.9.8.7:8765/api/forex"
    native_url = payload["native_pairing_urls"][0]
    native = urlsplit(native_url)
    assert native.scheme == owner_auth.NATIVE_PAIRING_SCHEME
    assert native.netloc == "pair"
    assert parse_qs(native.query) == {
        owner_auth.PAIRING_HASH_KEY: [token],
        owner_auth.API_BASE_HASH_KEY: ["http://10.9.8.7:8765/api/forex"],
        "page": ["quick-start"],
    }


def test_pairing_route_blocks_proxied_offbox_client():
    from fastapi.testclient import TestClient

    from api.server import app

    response = TestClient(app).get(
        "/api/forex/owner-auth/pairing",
        headers={"X-Forwarded-For": "10.0.0.55"},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "loopback_only"


def test_owner_auth_mutation_routes_block_proxied_offbox_client():
    from fastapi.testclient import TestClient

    from api.server import app

    client = TestClient(app)
    headers = {"X-Forwarded-For": "10.0.0.55"}

    lan_response = client.post(
        "/api/forex/owner-auth/lan-mode",
        json={"enabled": True},
        headers=headers,
    )
    rotate_response = client.post("/api/forex/owner-auth/rotate", headers=headers)

    assert lan_response.status_code == 403
    assert rotate_response.status_code == 403


def test_pairing_urls_prefer_likely_wifi_lan_before_virtual_adapters(monkeypatch):
    monkeypatch.setattr(
        owner_auth.socket,
        "gethostbyname_ex",
        lambda _hostname: ("pc", [], ["172.17.128.1", "10.0.0.6", "192.168.1.50"]),
    )

    urls = owner_auth.phone_pairing_urls("owner-token")

    assert urls[0].startswith("http://10.0.0.6:4173/")
    assert urls[1].startswith("http://192.168.1.50:4173/")
    assert urls[2].startswith("http://172.17.128.1:4173/")


# --- cloud mode: on the internet, never trust loopback ------------------------

def test_cloud_mode_loopback_without_token_is_refused(monkeypatch):
    monkeypatch.setenv("CAS_FOREX_CLOUD_MODE", "1")
    owner_auth.get_or_create_token()
    # Even from 127.0.0.1 (a reverse proxy in front of the app), no token = 401.
    d = _eval("127.0.0.1", headers={})
    assert d.allow is False
    assert d.status == 401


def test_cloud_mode_valid_token_from_anywhere_allows(monkeypatch):
    monkeypatch.setenv("CAS_FOREX_CLOUD_MODE", "1")
    token = owner_auth.get_or_create_token()
    assert _eval("203.0.113.7", headers={"X-CAS-Owner-Token": token}).allow is True
    assert _eval("127.0.0.1", headers={"Authorization": f"Bearer {token}"}).allow is True


def test_cloud_mode_health_still_exempt(monkeypatch):
    monkeypatch.setenv("CAS_FOREX_CLOUD_MODE", "1")
    assert _eval("203.0.113.7", path="/api/forex/health", method="GET").allow is True


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/index.html",
        "/manifest.webmanifest",
        "/sw.js",
        "/registerSW.js",
        "/assets/index-abc123.js",
        "/icons/cas-forex-192.png",
        "/?page=settings",
    ],
)
def test_cloud_mode_allows_static_web_shell_without_token(monkeypatch, path):
    monkeypatch.setenv("CAS_FOREX_CLOUD_MODE", "1")
    owner_auth.get_or_create_token()

    d = _eval("127.0.0.1", path=path, method="GET", headers={})

    assert d.allow is True


def test_cloud_mode_static_shell_exemption_does_not_cover_api(monkeypatch):
    monkeypatch.setenv("CAS_FOREX_CLOUD_MODE", "1")
    owner_auth.get_or_create_token()

    d = _eval("127.0.0.1", path="/api/forex/dashboard", method="GET", headers={})

    assert d.allow is False
    assert d.status == 401


def test_cloud_mode_static_shell_exemption_is_read_only(monkeypatch):
    monkeypatch.setenv("CAS_FOREX_CLOUD_MODE", "1")
    owner_auth.get_or_create_token()

    d = _eval("127.0.0.1", path="/owner-command", method="POST", headers={})

    assert d.allow is False
    assert d.status == 401


def test_env_token_overrides_stored_token(monkeypatch):
    owner_auth.get_or_create_token()  # a stored token exists
    monkeypatch.setenv("CAS_FOREX_OWNER_TOKEN", "deploy-injected-token")
    assert owner_auth.current_token() == "deploy-injected-token"
    assert owner_auth.verify_token("deploy-injected-token") is True
