from __future__ import annotations

from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient

from api.config import Settings, settings
from api.services.stripe_billing import NullBillingProvider


def _settings(**overrides) -> Settings:
    values = {
        "accounts_enabled": True,
        "quotas_enabled": True,
        "billing_entitlements_enabled": True,
        "billing_provider": "null",
        "billing_admin_secret": "a" * 32,
        "debug": True,
        "jwt_secret": "j" * 32,
        "jwt_algorithm": "HS256",
        "account_credential_pepper": "p" * 32,
        "account_bootstrap_secret": "b" * 32,
        "accounts_allow_single_host_sqlite": True,
        "state_ledger_path": str(Path(tempfile.gettempdir()).resolve() / "cas-billing-test.db"),
        "database_url": None,
    }
    values.update(overrides)
    return Settings.model_construct(**values)


def test_billing_requires_accounts_and_quotas() -> None:
    with pytest.raises(RuntimeError, match="requires NC_ACCOUNTS_ENABLED"):
        _settings(accounts_enabled=False).validate_account_storage()
    with pytest.raises(RuntimeError, match="requires NC_QUOTAS_ENABLED"):
        _settings(quotas_enabled=False).validate_account_storage()


def test_billing_rejects_unknown_provider_and_weak_admin_secret() -> None:
    with pytest.raises(RuntimeError, match="must be 'null' or 'stripe'"):
        _settings(billing_provider="attacker").validate_account_storage()
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        _settings(billing_admin_secret="weak").validate_account_storage()
    with pytest.raises(RuntimeError, match="price ids must be distinct"):
        _settings(
            billing_provider="stripe",
            stripe_professional_price_id="price_same",
            stripe_enterprise_price_id="price_same",
        ).validate_account_storage()


def test_dark_defaults_are_inert() -> None:
    dark = Settings.model_construct(
        accounts_enabled=False,
        quotas_enabled=False,
        billing_entitlements_enabled=False,
        # Disabled feature configuration remains inert rather than breaking an
        # existing deployment because of unused placeholder values.
        billing_provider="unused-future-provider",
        billing_admin_secret="weak-unused-placeholder",
    )
    dark.validate_account_storage()


def test_lifespan_installs_billing_on_shared_store_and_clears_it(
    tmp_path, monkeypatch
) -> None:
    from api.main import app

    patches = {
        "accounts_enabled": True,
        "quotas_enabled": True,
        "billing_entitlements_enabled": True,
        "billing_provider": "null",
        "billing_admin_secret": "a" * 32,
        "debug": True,
        "jwt_secret": "j" * 32,
        "jwt_algorithm": "HS256",
        "account_credential_pepper": "p" * 32,
        "account_bootstrap_secret": "b" * 32,
        "accounts_allow_single_host_sqlite": True,
        "state_ledger_path": str((tmp_path / "billing-shared.db").resolve()),
        "state_ledger_enabled": False,
        "state_ledger_read_authority": False,
        "database_url": None,
    }
    for name, value in patches.items():
        monkeypatch.setattr(settings, name, value)

    with TestClient(app):
        shared = app.state.shared_state_store
        assert shared is not None
        assert app.state.billing_entitlement_store._store is shared
        assert isinstance(app.state.billing_provider, NullBillingProvider)

    assert app.state.billing_entitlement_store is None
    assert app.state.billing_provider is None
