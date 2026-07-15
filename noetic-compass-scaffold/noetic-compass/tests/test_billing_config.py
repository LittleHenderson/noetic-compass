from __future__ import annotations

from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient

from api.config import Settings, settings
from api.services.stripe_billing import NullBillingProvider


BILLING_REFERENCE_KEY = "billing-ref-HMAC-v1-7f3a9c2e5d8b1a6f4c0e"


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


def test_stripe_key_mode_binding_applies_while_reconciliation_is_dark() -> None:
    base = {
        "billing_provider": "stripe",
        "billing_reconciliation_enabled": False,
        "stripe_professional_price_id": "price_pro",
        "stripe_enterprise_price_id": "price_ent",
        "stripe_secret_key": "sk_test_private",
        "stripe_livemode": False,
    }
    _settings(**base).validate_account_storage()
    with pytest.raises(RuntimeError, match="does not match NC_STRIPE_LIVEMODE"):
        _settings(**{**base, "stripe_livemode": True}).validate_account_storage()


def test_dark_defaults_are_inert() -> None:
    dark = Settings.model_construct(
        accounts_enabled=False,
        quotas_enabled=False,
        billing_entitlements_enabled=False,
        # Disabled feature configuration remains inert rather than breaking an
        # existing deployment because of unused placeholder values.
        billing_provider="unused-future-provider",
        billing_admin_secret="weak-unused-placeholder",
        billing_reconciliation_enabled=False,
        billing_provider_reference_hash_key="weak-unused-placeholder",
        billing_usage_meter_event_name="unsafe placeholder with spaces",
        billing_usage_meter_version="",
        billing_usage_currency="not-a-currency",
        stripe_secret_key="untyped-unused-placeholder",
        stripe_usage_price_id="",
        stripe_livemode=True,
        billing_customer_receipt_allowed_hosts="unsafe host",
    )
    dark.validate_account_storage()


def test_reconciliation_enablement_requires_entitlements_and_stripe() -> None:
    with pytest.raises(RuntimeError, match="requires NC_BILLING_ENTITLEMENTS"):
        _settings(
            billing_reconciliation_enabled=True,
            billing_entitlements_enabled=False,
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="requires NC_BILLING_PROVIDER=stripe"):
        _settings(
            billing_reconciliation_enabled=True,
            billing_provider="null",
        ).validate_account_storage()


def test_reconciliation_enablement_fails_loud_on_incomplete_contract() -> None:
    base = {
        "billing_reconciliation_enabled": True,
        "billing_provider": "stripe",
        "stripe_professional_price_id": "price_pro",
        "stripe_enterprise_price_id": "price_ent",
        "billing_provider_reference_hash_key": BILLING_REFERENCE_KEY,
        "billing_usage_meter_event_name": "cas.accelerator_milliseconds",
        "billing_usage_meter_version": "cas_meter.v1",
        "billing_usage_currency": "usd",
        "stripe_secret_key": "sk_test_private",
        "stripe_usage_price_id": "price_usage",
        "stripe_livemode": False,
        "billing_customer_receipt_allowed_hosts": "receipts.stripe.test",
    }
    _settings(**base).validate_account_storage()
    with pytest.raises(RuntimeError, match="HASH_KEY.*32 bytes"):
        _settings(
            **{**base, "billing_provider_reference_hash_key": "weak"}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="must be dedicated"):
        _settings(
            **{
                **base,
                "billing_provider_reference_hash_key": "j" * 32,
            }
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="METER_EVENT_NAME"):
        _settings(
            **{**base, "billing_usage_meter_event_name": "unsafe name"}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="METER_VERSION"):
        _settings(
            **{**base, "billing_usage_meter_version": ""}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="USAGE_PRICE_ID"):
        _settings(
            **{**base, "stripe_usage_price_id": ""}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="USAGE_PRICE_ID"):
        _settings(
            **{**base, "stripe_usage_price_id": "prod_not_a_price"}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="USAGE_PRICE_ID"):
        _settings(
            **{**base, "stripe_usage_price_id": " price_usage"}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="distinct"):
        _settings(
            **{**base, "stripe_usage_price_id": "price_pro"}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="does not match NC_STRIPE_LIVEMODE"):
        _settings(
            **{**base, "stripe_livemode": True}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="does not match NC_STRIPE_LIVEMODE"):
        _settings(
            **{
                **base,
                "stripe_secret_key": "rk_live_private",
                "stripe_livemode": False,
            }
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="recognizable Stripe live/test prefix"):
        _settings(
            **{**base, "stripe_secret_key": "untyped-private-key"}
        ).validate_account_storage()
    _settings(
        **{
            **base,
            "stripe_secret_key": "rk_live_private",
            "stripe_livemode": True,
        }
    ).validate_account_storage()
    with pytest.raises(RuntimeError, match="CURRENCY"):
        _settings(
            **{**base, "billing_usage_currency": "dollars"}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="CURRENCY"):
        _settings(
            **{**base, "billing_usage_currency": "USD"}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="RECEIPT_ALLOWED_HOSTS"):
        _settings(
            **{**base, "billing_customer_receipt_allowed_hosts": "*"}
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="RECEIPT_ALLOWED_HOSTS"):
        _settings(
            **{
                **base,
                "billing_customer_receipt_allowed_hosts": "receipts.stripe.test, pay.stripe.test",
            }
        ).validate_account_storage()


@pytest.mark.parametrize(
    ("weak_key", "message"),
    (
        (" " * 32, "whitespace or control"),
        ("\t" * 32, "whitespace or control"),
        ("\x00" * 32, "whitespace or control"),
        ("x" * 32, "unpredictable"),
        ("abcd" * 8, "unpredictable"),
        ("change-me-in-production-change-me-now", "unpredictable"),
    ),
)
def test_reconciliation_rejects_blank_control_and_predictable_reference_keys(
    weak_key: str, message: str
) -> None:
    with pytest.raises(RuntimeError, match=message):
        _settings(
            billing_reconciliation_enabled=True,
            billing_provider="stripe",
            stripe_professional_price_id="price_pro",
            stripe_enterprise_price_id="price_ent",
            billing_provider_reference_hash_key=weak_key,
            billing_usage_meter_event_name="cas.accelerator_milliseconds",
            billing_usage_meter_version="cas_meter.v1",
            billing_usage_currency="usd",
            stripe_usage_price_id="price_usage",
            billing_customer_receipt_allowed_hosts="receipts.stripe.test",
        ).validate_account_storage()


@pytest.mark.parametrize(
    ("credential_field", "credential_value"),
    tuple(
        (field_name, BILLING_REFERENCE_KEY)
        for field_name in (
            "crm_airtable_token",
            "jwt_secret",
            "auth_mint_secret",
            "account_credential_pepper",
            "account_bootstrap_secret",
            "platform_tenant_provisioning_secret",
            "evidence_share_token_pepper",
            "object_lock_receipt_attestation_key",
            "fleet_service_credential_pepper",
            "billing_admin_secret",
            "stripe_secret_key",
            "stripe_webhook_secret",
            "openai_api_key",
            "anthropic_api_key",
            "google_api_key",
            "meta_api_key",
            "xai_api_key",
            "deepseek_api_key",
            "qwen_api_key",
            "atlas_live_worker_token",
            "db_password",
        )
    )
    + (
        (
            "atlas_live_invite_codes",
            f"alpha-code,{BILLING_REFERENCE_KEY},omega-code",
        ),
        (
            "database_url",
            f"postgresql://cas:{BILLING_REFERENCE_KEY}@db.internal/cas",
        ),
    ),
)
def test_reconciliation_reference_key_is_separate_from_every_credential(
    credential_field: str, credential_value: str
) -> None:
    with pytest.raises(RuntimeError, match="must be dedicated"):
        _settings(
            billing_reconciliation_enabled=True,
            billing_provider="stripe",
            stripe_professional_price_id="price_pro",
            stripe_enterprise_price_id="price_ent",
            billing_provider_reference_hash_key=BILLING_REFERENCE_KEY,
            billing_usage_meter_event_name="cas.accelerator_milliseconds",
            billing_usage_meter_version="cas_meter.v1",
            billing_usage_currency="usd",
            stripe_usage_price_id="price_usage",
            billing_customer_receipt_allowed_hosts="receipts.stripe.test",
            **{credential_field: credential_value},
        ).validate_account_storage()


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


def test_lifespan_installs_enabled_reconciliation_service_without_api_claim(
    tmp_path, monkeypatch
) -> None:
    from api.main import app
    from api.services import stripe_billing

    monkeypatch.setattr(
        stripe_billing,
        "build_billing_provider",
        lambda _settings: NullBillingProvider(),
    )
    patches = {
        "accounts_enabled": True,
        "quotas_enabled": True,
        "billing_entitlements_enabled": True,
        "billing_provider": "stripe",
        "billing_reconciliation_enabled": True,
        "billing_provider_reference_hash_key": BILLING_REFERENCE_KEY,
        "billing_usage_meter_event_name": "cas.accelerator_milliseconds",
        "billing_usage_meter_version": "cas_meter.v1",
        "billing_usage_currency": "usd",
        "stripe_usage_price_id": "price_usage",
        "stripe_professional_price_id": "price_pro",
        "stripe_enterprise_price_id": "price_ent",
        "stripe_secret_key": "sk_test_private",
        "stripe_livemode": False,
        "billing_customer_receipt_allowed_hosts": "receipts.stripe.test",
        "billing_admin_secret": "a" * 32,
        "debug": True,
        "jwt_secret": "j" * 32,
        "jwt_algorithm": "HS256",
        "account_credential_pepper": "p" * 32,
        "account_bootstrap_secret": "b" * 32,
        "accounts_allow_single_host_sqlite": True,
        "state_ledger_path": str((tmp_path / "billing-reconciliation.db").resolve()),
        "state_ledger_enabled": False,
        "state_ledger_read_authority": False,
        "database_url": None,
    }
    for name, value in patches.items():
        monkeypatch.setattr(settings, name, value)

    with TestClient(app):
        shared = app.state.shared_state_store
        reconciliation = app.state.billing_reconciliation_store
        assert reconciliation is not None
        assert reconciliation._store is shared
        assert reconciliation._entitlements is app.state.billing_entitlement_store
        assert not any(
            "reconciliation" in str(getattr(route, "path", ""))
            for route in app.routes
        )

    assert app.state.billing_reconciliation_store is None
