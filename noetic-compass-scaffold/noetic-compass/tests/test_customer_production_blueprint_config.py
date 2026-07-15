from __future__ import annotations

import re
from pathlib import Path

import pytest

from api.config import Settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parents[1]
CUSTOMER_BLUEPRINT = REPOSITORY_ROOT / "render.customer.yaml"
CUSTOMER_API_DOCKERFILE = APP_ROOT / "Dockerfile.api"
ROOT_WORKFLOWS = REPOSITORY_ROOT / ".github" / "workflows"
PSEUDONYM_KEY_ID = "hatk_0123456789abcdef0123456789abcdef"
PSEUDONYM_KEY_SECRET = (
    "base64url:5EfvyXp5BYNrpodyw-DoiFemHziedgI06tZHVjtmvow"
)
PSEUDONYM_KEYRING_JSON = (
    '{"' + PSEUDONYM_KEY_ID + '":"' + PSEUDONYM_KEY_SECRET + '"}'
)
CUSTOMER_PSEUDONYM_KEY_ID = "cpk_89abcdef0123456789abcdef01234567"
CUSTOMER_PSEUDONYM_KEY_SECRET = (
    "base64url:ba72v6mRNqQ2kA0GZljcsAF4HpatDbaOpVkvpGl_QmA"
)
CUSTOMER_PSEUDONYM_KEYRING_JSON = (
    '{"'
    + CUSTOMER_PSEUDONYM_KEY_ID
    + '":"'
    + CUSTOMER_PSEUDONYM_KEY_SECRET
    + '"}'
)


def _env_value(key: str) -> str:
    text = CUSTOMER_BLUEPRINT.read_text(encoding="utf-8")
    match = re.search(
        rf"(?m)^\s*- key: {re.escape(key)}\s*\r?\n\s+value:\s*([^#\r\n]+)",
        text,
    )
    assert match is not None, f"{key} missing from {CUSTOMER_BLUEPRINT.name}"
    return match.group(1).strip().strip('"\'')


def _declaration_mode(key: str) -> str:
    text = CUSTOMER_BLUEPRINT.read_text(encoding="utf-8")
    match = re.search(
        rf"(?m)^\s*- key: {re.escape(key)}\s*\r?\n"
        r"[ \t]+(generateValue|sync|fromDatabase):[ \t]*([^#\r\n]*)",
        text,
    )
    assert match is not None, f"{key} declaration missing from {CUSTOMER_BLUEPRINT.name}"
    value = (match.group(2) or "").strip().strip('"\'')
    return f"{match.group(1)}:{value}"


def _safe_customer_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "debug": False,
        "jwt_algorithm": "HS256",
        "jwt_secret": "jwt-authority-00000000000000000000000000000001",
        "database_url": "postgresql://customer:secret@postgres/customer",
        "state_ledger_enabled": True,
        "state_ledger_read_authority": True,
        "NC_ACCOUNTS_ENABLED": True,
        "NC_ACCOUNT_CREDENTIAL_PEPPER": (
            "account-pepper-000000000000000000000000000001"
        ),
        "NC_HUMAN_ATTESTATION_PSEUDONYM_ACTIVE_KEY_ID": PSEUDONYM_KEY_ID,
        "NC_HUMAN_ATTESTATION_PSEUDONYM_KEYRING_JSON": PSEUDONYM_KEYRING_JSON,
        "NC_CUSTOMER_PRODUCTION_PSEUDONYM_ACTIVE_KEY_ID": (
            CUSTOMER_PSEUDONYM_KEY_ID
        ),
        "NC_CUSTOMER_PRODUCTION_PSEUDONYM_KEYRING_JSON": (
            CUSTOMER_PSEUDONYM_KEYRING_JSON
        ),
        "NC_ACCOUNT_BOOTSTRAP_SECRET": (
            "bootstrap-secret-00000000000000000000000000001"
        ),
        "NC_PLATFORM_TENANT_PROVISIONING_SECRET": (
            "provisioning-secret-000000000000000000000000001"
        ),
        "NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE": False,
        "NC_QUOTAS_ENABLED": True,
        "NC_BILLING_ENTITLEMENTS_ENABLED": True,
        "NC_BILLING_ADMIN_SECRET": (
            "billing-admin-000000000000000000000000000001"
        ),
        "NC_BILLING_PROVIDER": "null",
        "NC_BILLING_RECONCILIATION_ENABLED": False,
        "NC_BILLING_WORKER_MEASUREMENT_ENABLED": False,
        "NC_BILLING_USAGE_DISPATCH_ENABLED": False,
        "NC_FLEET_SERVICE_AUTH_ENABLED": False,
        "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED": True,
        "NC_EVIDENCE_SHARES_ENABLED": True,
        "NC_EVIDENCE_SHARE_TOKEN_PEPPER": (
            "share-pepper-0000000000000000000000000000001"
        ),
        "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY": (
            "receipt-authority-0000000000000000000000000001"
        ),
    }
    values.update(overrides)
    return Settings(**values)


def test_customer_blueprint_enables_airtable_while_privacy_intake_stays_closed() -> None:
    expected_literals = {
        "NC_ACCOUNTS_ENABLED": "true",
        "NC_QUOTAS_ENABLED": "true",
        "NC_BILLING_ENTITLEMENTS_ENABLED": "true",
        "NC_BILLING_PROVIDER": "null",
        "NC_BILLING_RECONCILIATION_ENABLED": "false",
        "NC_BILLING_WORKER_MEASUREMENT_ENABLED": "false",
        "NC_BILLING_USAGE_DISPATCH_ENABLED": "false",
        "NC_FLEET_SERVICE_AUTH_ENABLED": "false",
        "NC_STATE_LEDGER_ENABLED": "true",
        "NC_STATE_LEDGER_READ_AUTHORITY": "true",
        "NC_CRM_PROVIDER": "airtable",
        "NC_AIRTABLE_API_BASE_URL": "https://api.airtable.com/v0",
        "NC_CRM_LEAD_STORE_BACKEND": "state_store",
        "NC_SUPPORT_TICKET_STORE_BACKEND": "state_store",
        "NC_SUPPORT_ACK_SLA_SECONDS": "86400",
        "NC_CRM_PRIVACY_NOTICE_PUBLICATION_STATUS": "OPEN",
        "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED": "true",
        "CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR": (
            "/var/customer-support/evidence_packets"
        ),
        "NC_EVIDENCE_SHARES_ENABLED": "true",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET": "cas-harness-runpod-92754088",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX": (
            "cas-harness/customer-production/evidence-anchors"
        ),
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION": "us-west-2",
        "ATLAS_ALLOWED_ORIGINS": (
            "https://atlas.noeticcompass.com,"
            "https://atlas-viewer-app.onrender.com,"
            "https://cascompass.ai,https://www.cascompass.ai"
        ),
        "NC_CORS_ORIGIN_REGEX": "^$",
    }
    assert {key: _env_value(key) for key in expected_literals} == expected_literals

    generated = {
        "NC_JWT_SECRET",
        "NC_ACCOUNT_CREDENTIAL_PEPPER",
        "NC_ACCOUNT_BOOTSTRAP_SECRET",
        "NC_PLATFORM_TENANT_PROVISIONING_SECRET",
        "NC_BILLING_ADMIN_SECRET",
        "NC_EVIDENCE_SHARE_TOKEN_PEPPER",
        "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY",
    }
    assert {_declaration_mode(key) for key in generated} == {"generateValue:true"}
    injected = {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "ATLAS_LIVE_WORKER_URL",
        "ATLAS_LIVE_WORKER_TOKEN",
        "NC_HUMAN_ATTESTATION_PSEUDONYM_ACTIVE_KEY_ID",
        "NC_HUMAN_ATTESTATION_PSEUDONYM_KEYRING_JSON",
        "NC_CUSTOMER_PRODUCTION_PSEUDONYM_ACTIVE_KEY_ID",
        "NC_CUSTOMER_PRODUCTION_PSEUDONYM_KEYRING_JSON",
        "NC_AIRTABLE_TOKEN",
        "NC_AIRTABLE_BASE_ID",
        "NC_AIRTABLE_TABLE_NAME",
        "NC_AIRTABLE_DEDUP_FIELD",
        "NC_AIRTABLE_OWNER_FIELD",
        "NC_AIRTABLE_OWNER_VALUE",
        "NC_AIRTABLE_LIFECYCLE_FIELD",
    }
    assert {_declaration_mode(key) for key in injected} == {"sync:false"}
    assert _declaration_mode("NC_DATABASE_URL") == "fromDatabase:"


def test_customer_api_image_contains_bounded_support_crm_finalizer() -> None:
    dockerfile = CUSTOMER_API_DOCKERFILE.read_text(encoding="utf-8")
    assert (
        "COPY scripts/build_support_crm_acceptance_evidence.py "
        "scripts/build_support_crm_acceptance_evidence.py"
    ) in dockerfile


def test_customer_pseudonym_key_material_is_absent_from_github_actions() -> None:
    workflows = sorted(ROOT_WORKFLOWS.glob("*.yml")) + sorted(
        ROOT_WORKFLOWS.glob("*.yaml")
    )
    assert workflows
    forbidden_names = {
        "NC_CUSTOMER_PRODUCTION_PSEUDONYM_ACTIVE_KEY_ID",
        "NC_CUSTOMER_PRODUCTION_PSEUDONYM_KEYRING_JSON",
    }
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        assert not any(name in text for name in forbidden_names), workflow
        assert re.search(r"\bcpk_[0-9a-f]{32}\b", text) is None, workflow
        assert (
            re.search(r"base64url:[A-Za-z0-9_-]{43,86}", text) is None
        ), workflow


def test_customer_startup_configuration_is_valid_without_effect_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "31")

    configured = _safe_customer_settings()
    configured.validate_account_storage()

    assert configured.accounts_enabled is True
    assert configured.quotas_enabled is True
    assert configured.billing_entitlements_enabled is True
    assert configured.billing_provider == "null"
    assert configured.billing_reconciliation_enabled is False
    assert configured.billing_worker_measurement_enabled is False
    assert configured.billing_usage_dispatch_enabled is False
    assert configured.fleet_service_auth_enabled is False
    assert configured.evidence_packet_object_store_enabled is True
    assert configured.evidence_shares_enabled is True


def test_customer_attestation_keyring_is_required_bound_and_dedicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE"
    )
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "31")

    with pytest.raises(RuntimeError, match="configured together"):
        _safe_customer_settings(
            NC_HUMAN_ATTESTATION_PSEUDONYM_KEYRING_JSON=""
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="active pseudonym key is unavailable"):
        _safe_customer_settings(
            NC_HUMAN_ATTESTATION_PSEUDONYM_ACTIVE_KEY_ID=(
                "hatk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            )
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="must be dedicated"):
        _safe_customer_settings(
            NC_ACCOUNT_CREDENTIAL_PEPPER=PSEUDONYM_KEY_SECRET,
        ).validate_account_storage()


def test_customer_production_keyring_is_required_bound_and_dedicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE"
    )
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "31")

    with pytest.raises(RuntimeError, match="configured together"):
        _safe_customer_settings(
            NC_CUSTOMER_PRODUCTION_PSEUDONYM_KEYRING_JSON=""
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="active pseudonym key is unavailable"):
        _safe_customer_settings(
            NC_CUSTOMER_PRODUCTION_PSEUDONYM_ACTIVE_KEY_ID=(
                "cpk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            )
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="must be dedicated"):
        _safe_customer_settings(
            NC_ACCOUNT_CREDENTIAL_PEPPER=CUSTOMER_PSEUDONYM_KEY_SECRET,
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="must be dedicated"):
        _safe_customer_settings(
            NC_CUSTOMER_PRODUCTION_PSEUDONYM_KEYRING_JSON=(
                '{"'
                + CUSTOMER_PSEUDONYM_KEY_ID
                + '":"'
                + PSEUDONYM_KEY_SECRET
                + '"}'
            ),
        ).validate_account_storage()


def test_attestation_key_validation_precedes_accounts_disabled_return() -> None:
    accounts_off = Settings.model_construct(
        accounts_enabled=False,
        human_attestation_pseudonym_active_key_id="",
        human_attestation_pseudonym_keyring_json="",
    )
    accounts_off.validate_account_storage()

    with pytest.raises(RuntimeError, match="configured together"):
        Settings.model_construct(
            accounts_enabled=False,
            human_attestation_pseudonym_active_key_id=PSEUDONYM_KEY_ID,
            human_attestation_pseudonym_keyring_json="",
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="configured together"):
        Settings.model_construct(
            accounts_enabled=False,
            human_attestation_pseudonym_active_key_id="",
            human_attestation_pseudonym_keyring_json=PSEUDONYM_KEYRING_JSON,
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="independently random"):
        Settings.model_construct(
            accounts_enabled=False,
            human_attestation_pseudonym_active_key_id=PSEUDONYM_KEY_ID,
            human_attestation_pseudonym_keyring_json=(
                '{"' + PSEUDONYM_KEY_ID + '":'
                '"base64url:YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE"}'
            ),
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="must be dedicated"):
        Settings.model_construct(
            accounts_enabled=False,
            account_credential_pepper=PSEUDONYM_KEY_SECRET,
            human_attestation_pseudonym_active_key_id=PSEUDONYM_KEY_ID,
            human_attestation_pseudonym_keyring_json=PSEUDONYM_KEYRING_JSON,
        ).validate_account_storage()


def test_customer_key_validation_precedes_accounts_disabled_return() -> None:
    with pytest.raises(RuntimeError, match="configured together"):
        Settings.model_construct(
            accounts_enabled=False,
            customer_production_pseudonym_active_key_id=(
                CUSTOMER_PSEUDONYM_KEY_ID
            ),
            customer_production_pseudonym_keyring_json="",
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="must be independently random"):
        Settings.model_construct(
            accounts_enabled=False,
            customer_production_pseudonym_active_key_id=(
                CUSTOMER_PSEUDONYM_KEY_ID
            ),
            customer_production_pseudonym_keyring_json=(
                '{"'
                + CUSTOMER_PSEUDONYM_KEY_ID
                + '":'
                '"base64url:YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE"}'
            ),
        ).validate_account_storage()
    with pytest.raises(RuntimeError, match="must be dedicated"):
        Settings.model_construct(
            accounts_enabled=False,
            human_attestation_pseudonym_active_key_id=PSEUDONYM_KEY_ID,
            human_attestation_pseudonym_keyring_json=PSEUDONYM_KEYRING_JSON,
            customer_production_pseudonym_active_key_id=(
                CUSTOMER_PSEUDONYM_KEY_ID
            ),
            customer_production_pseudonym_keyring_json=(
                '{"'
                + CUSTOMER_PSEUDONYM_KEY_ID
                + '":"'
                + PSEUDONYM_KEY_SECRET
                + '"}'
            ),
        ).validate_account_storage()


def test_customer_effect_gate_mutation_fails_startup_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "s3")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE")
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "31")

    configured = _safe_customer_settings(NC_BILLING_RECONCILIATION_ENABLED=True)
    with pytest.raises(RuntimeError, match="requires NC_BILLING_PROVIDER=stripe"):
        configured.validate_account_storage()
