from __future__ import annotations

import re

import pytest

from scripts.verify_account_canary_quotas import (
    ProofFailure,
    _credential,
    _redact,
    _require_canary_environment,
    _safe_loopback_url,
)


def test_derived_proof_credentials_are_stable_scoped_and_never_echo_secret() -> None:
    platform_secret = "platform-secret-" + ("x" * 48)
    first = _credential(platform_secret, "proof-123", "a")

    assert first == _credential(platform_secret, "proof-123", "a")
    assert first != _credential(platform_secret, "proof-123", "b")
    assert first != _credential(platform_secret, "proof-456", "a")
    assert re.fullmatch(r"casak_[A-Za-z0-9_-]{43}", first)
    assert platform_secret not in first


def test_report_redaction_is_recursive() -> None:
    payload = {
        "token": "bearer-value",
        "nested": {
            "api_credential": "casak_value",
            "Authorization": "Bearer value",
            "safe": [{"platform_secret": "secret"}, "present"],
        },
    }

    redacted = _redact(payload)

    assert redacted["token"] == "[REDACTED]"
    assert redacted["nested"]["api_credential"] == "[REDACTED]"
    assert redacted["nested"]["Authorization"] == "[REDACTED]"
    assert redacted["nested"]["safe"][0]["platform_secret"] == "[REDACTED]"
    assert redacted["nested"]["safe"][1] == "present"


@pytest.mark.parametrize(
    "url",
    (
        "https://noetic-compass-api.onrender.com",
        "http://10.0.0.5:10000",
        "ftp://127.0.0.1:10000",
        "http://user:pass@127.0.0.1:10000",
    ),
)
def test_proof_refuses_non_loopback_or_credentialed_targets(url: str) -> None:
    with pytest.raises(ProofFailure):
        _safe_loopback_url(url)


def test_proof_accepts_only_loopback_http_targets() -> None:
    assert _safe_loopback_url("http://127.0.0.1:10000/") == "http://127.0.0.1:10000"
    assert _safe_loopback_url("https://localhost:8443") == "https://localhost:8443"


def test_canary_environment_guard_requires_exact_dark_billing_posture(monkeypatch) -> None:
    values = {
        "NC_DEPLOYMENT_PROFILE": "accounts-canary",
        "NC_ACCOUNTS_ENABLED": "true",
        "NC_QUOTAS_ENABLED": "true",
        "NC_QUOTA_MONTHLY_AUDIT_LIMIT": "2",
        "NC_BILLING_ENTITLEMENTS_ENABLED": "false",
        "NC_BILLING_PROVIDER": "null",
        "NC_MOCK_LLM": "true",
        "NC_DATABASE_URL": "postgresql://example.invalid/canary",
        "NC_PLATFORM_TENANT_PROVISIONING_SECRET": "p" * 32,
        "RENDER_SERVICE_ID": "srv-d9akoolaeets73bp3e7g",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    database_url, platform_secret = _require_canary_environment(
        expected_limit=2,
        expected_service_id="srv-d9akoolaeets73bp3e7g",
    )
    assert database_url.startswith("postgresql://")
    assert len(platform_secret) == 32

    monkeypatch.setenv("NC_BILLING_ENTITLEMENTS_ENABLED", "true")
    with pytest.raises(ProofFailure, match="NC_BILLING_ENTITLEMENTS_ENABLED=false"):
        _require_canary_environment(
            expected_limit=2,
            expected_service_id="srv-d9akoolaeets73bp3e7g",
        )
