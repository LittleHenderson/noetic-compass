"""Owner-auth policy tests.

The whole point: the owner's own machine (loopback) drives with zero friction,
while any OTHER device on the network is refused unless the owner turned LAN
mode on AND the request carries the owner token. Proven here as pure policy
(``evaluate_request``) plus the token store round-trip.
"""

from __future__ import annotations

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


# --- token store --------------------------------------------------------------

def test_token_is_created_once_and_stable():
    assert owner_auth.current_token() is None
    t1 = owner_auth.get_or_create_token()
    t2 = owner_auth.get_or_create_token()
    assert t1 and t1 == t2
    assert owner_auth.current_token() == t1


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
