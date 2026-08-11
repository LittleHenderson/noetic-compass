from __future__ import annotations

import os
from types import SimpleNamespace

from cas_forex.managed_secret_store import build_managed_secret_store_report


def _cfg(**overrides):
    data = {
        "secret_store_backend": "auto",
        "secret_manager_provider": "",
        "secret_manager_configured": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_managed_secret_store_reports_local_backend_without_raw_secrets(monkeypatch):
    monkeypatch.delenv("CAS_FOREX_CLOUD_MODE", raising=False)
    report = build_managed_secret_store_report(_cfg())

    assert report["report_kind"] == "cas_forex_managed_secret_store"
    assert report["status"] in {"OK", "ATTENTION"}
    assert report["backend_status"] in {
        "OS_MANAGED_CURRENT_USER",
        "LOCAL_ENCRYPTED_ENVELOPE",
        "NO_MANAGED_STORE",
    }
    assert report["server_side_only"] is True
    assert report["raw_secret_returned"] is False
    assert "does not return raw secrets" in report["claim_boundary"]
    assert "runtime_secret_envelope" in report
    if os.name == "nt":
        assert report["os_current_user_store"]["provider"] == "windows_dpapi_current_user"


def test_managed_secret_store_cloud_mode_requires_external_manager(monkeypatch):
    monkeypatch.setenv("CAS_FOREX_CLOUD_MODE", "1")
    report = build_managed_secret_store_report(_cfg())

    assert report["cloud_mode"] is True
    assert report["status"] == "ATTENTION"
    assert "Cloud/public mode requires an external managed secrets manager." in report["attention_items"]


def test_managed_secret_store_external_provider_satisfies_cloud_mode(monkeypatch):
    monkeypatch.setenv("CAS_FOREX_CLOUD_MODE", "1")
    report = build_managed_secret_store_report(
        _cfg(secret_manager_provider="aws_secrets_manager", secret_manager_configured=True)
    )

    assert report["status"] == "OK"
    assert report["backend_status"] == "EXTERNAL_MANAGED_STORE_CONFIGURED"
    assert report["external_secret_manager"]["configured"] is True
    assert report["external_secret_manager"]["provider"] == "aws_secrets_manager"
