from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.config import Settings, settings
from api.db import _async_database_url
from api.services.cas_harness_audit_sessions import create_session
from api.state_ledger_bootstrap import _postgres_state_store_dsn


def _account_settings(**overrides) -> Settings:
    values = {
        "accounts_enabled": True,
        "debug": True,
        "jwt_secret": "j" * 32,
        "jwt_algorithm": "HS256",
        "account_credential_pepper": "p" * 32,
        "account_bootstrap_secret": "b" * 32,
        "accounts_allow_single_host_sqlite": True,
        "state_ledger_path": "C:/tmp/cas-account-test.db",
        "database_url": None,
    }
    values.update(overrides)
    return Settings.model_construct(**values)


def test_account_storage_validation_rejects_hosted_sqlite_and_weak_auth() -> None:
    with pytest.raises(RuntimeError, match="EVIDENCE_PACKET_OBJECT_STORE_ENABLED"):
        _account_settings(
            debug=False,
            database_url="postgresql://db/cas",
            evidence_packet_object_store_enabled=False,
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="Hosted account mode requires"):
        _account_settings(
            debug=False,
            database_url=None,
            evidence_packet_object_store_enabled=True,
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        _account_settings(jwt_secret="short").validate_account_storage()
    with pytest.raises(RuntimeError, match="pins NC_JWT_ALGORITHM"):
        _account_settings(jwt_algorithm="RS256").validate_account_storage()
    with pytest.raises(RuntimeError, match="absolute NC_STATE_LEDGER_PATH"):
        _account_settings(state_ledger_path="relative.db").validate_account_storage()


def test_account_storage_validation_accepts_postgres_and_acknowledged_local_sqlite() -> None:
    _account_settings(
        database_url="postgresql://db/cas",
        debug=False,
        evidence_packet_object_store_enabled=True,
    ).validate_account_storage()
    _account_settings().validate_account_storage()


@pytest.mark.parametrize(
    ("raw", "async_url", "state_dsn"),
    (
        (
            "postgres://user:pass@db/cas",
            "postgresql+asyncpg://user:pass@db/cas",
            "postgresql://user:pass@db/cas",
        ),
        (
            "postgresql://user:pass@db/cas",
            "postgresql+asyncpg://user:pass@db/cas",
            "postgresql://user:pass@db/cas",
        ),
        (
            "postgresql+asyncpg://user:pass@db/cas",
            "postgresql+asyncpg://user:pass@db/cas",
            "postgresql://user:pass@db/cas",
        ),
    ),
)
def test_postgres_dsn_normalization(raw: str, async_url: str, state_dsn: str) -> None:
    assert _async_database_url(raw) == async_url
    assert _postgres_state_store_dsn(raw) == state_dsn


def test_lifespan_shares_one_store_and_clears_it_on_shutdown(tmp_path, monkeypatch) -> None:
    from api.main import app

    patches = {
        "accounts_enabled": True,
        "debug": True,
        "jwt_secret": "j" * 32,
        "jwt_algorithm": "HS256",
        "account_credential_pepper": "p" * 32,
        "account_bootstrap_secret": "b" * 32,
        "accounts_allow_single_host_sqlite": True,
        "state_ledger_path": str((tmp_path / "shared.db").resolve()),
        "state_ledger_enabled": False,
        "state_ledger_read_authority": False,
        "database_url": None,
        "quotas_enabled": False,
    }
    for name, value in patches.items():
        monkeypatch.setattr(settings, name, value)

    with TestClient(app):
        shared = app.state.shared_state_store
        assert shared is not None
        assert app.state.account_store._store is shared
        assert app.state.session_store._store is shared
        durable = create_session(
            {
                "model_id": "EleutherAI/pythia-160m",
                "audit_mode": "BALANCED",
                "prompt": "shared lifecycle",
                "selected_modules": ["active_trace"],
            },
            tenant_id="tenant-a",
            account_id="acct-a",
        )
        assert durable.audit_id

    assert app.state.shared_state_store is None
    assert app.state.account_store is None
    assert app.state.session_store is None
