"""Hostile tests for dedicated public customer-production pseudonyms."""

from __future__ import annotations

import base64
import hashlib
import json

import pytest

from api.services.customer_production_pseudonyms import (
    ACCOUNT_DOMAIN,
    HOSTED_JOURNEY_TRACE_DOMAIN,
    SUPPORT_CRM_REQUEST_TRACE_DOMAIN,
    TENANT_DOMAIN,
    CustomerProductionPseudonymizer,
    parse_customer_production_pseudonym_keyring,
)


KEY_1_ID = "cpk_0123456789abcdef0123456789abcdef"
KEY_2_ID = "cpk_fedcba9876543210fedcba9876543210"
KEY_1 = hashlib.sha256(b"customer-production-test-key-one").digest()
KEY_2 = hashlib.sha256(b"customer-production-test-key-two").digest()


def _encoded(value: bytes) -> str:
    return "base64url:" + base64.urlsafe_b64encode(value).rstrip(b"=").decode(
        "ascii"
    )


def test_keyring_is_strict_and_public_subjects_are_domain_and_tenant_scoped() -> None:
    parsed = parse_customer_production_pseudonym_keyring(
        json.dumps({KEY_1_ID: _encoded(KEY_1)}, separators=(",", ":")),
        active_key_id=KEY_1_ID,
    )
    pseudonyms = CustomerProductionPseudonymizer(
        parsed, active_key_id=KEY_1_ID
    )

    subject = pseudonyms.subject(
        domain=ACCOUNT_DOMAIN,
        tenant_scope="tenant-one",
        value="acct-raw-private",
    )

    assert subject.startswith("hmac-sha256:")
    assert subject != "hmac-sha256:" + hashlib.sha256(
        b"acct-raw-private"
    ).hexdigest()
    assert subject != pseudonyms.subject(
        domain=TENANT_DOMAIN,
        tenant_scope="tenant-one",
        value="acct-raw-private",
    )
    assert pseudonyms.subject(
        domain=HOSTED_JOURNEY_TRACE_DOMAIN,
        tenant_scope="tenant-one",
        value="caller-trace",
    ) != pseudonyms.subject(
        domain=SUPPORT_CRM_REQUEST_TRACE_DOMAIN,
        tenant_scope="tenant-one",
        value="caller-trace",
    )
    assert subject != pseudonyms.subject(
        domain=ACCOUNT_DOMAIN,
        tenant_scope="tenant-two",
        value="acct-raw-private",
    )


def test_rotation_retains_old_artifact_verification_without_rewriting_subject() -> None:
    old = CustomerProductionPseudonymizer(
        {KEY_1_ID: KEY_1}, active_key_id=KEY_1_ID
    )
    old_subject = old.subject(
        domain=ACCOUNT_DOMAIN,
        tenant_scope="tenant-one",
        value="acct-raw-private",
    )
    rotated = CustomerProductionPseudonymizer(
        {KEY_1_ID: KEY_1, KEY_2_ID: KEY_2}, active_key_id=KEY_2_ID
    )

    assert rotated.assert_subject(
        old_subject,
        domain=ACCOUNT_DOMAIN,
        tenant_scope="tenant-one",
        value="acct-raw-private",
        key_id=KEY_1_ID,
    ) == old_subject
    assert rotated.subject(
        domain=ACCOUNT_DOMAIN,
        tenant_scope="tenant-one",
        value="acct-raw-private",
    ) != old_subject

    without_history = CustomerProductionPseudonymizer(
        {KEY_2_ID: KEY_2}, active_key_id=KEY_2_ID
    )
    with pytest.raises(ValueError, match="unavailable"):
        without_history.assert_subject(
            old_subject,
            domain=ACCOUNT_DOMAIN,
            tenant_scope="tenant-one",
            value="acct-raw-private",
            key_id=KEY_1_ID,
        )


@pytest.mark.parametrize(
    "raw",
    [
        json.dumps({KEY_1_ID: "base64url:" + "A" * 43}),
        '{"cpk_0123456789abcdef0123456789abcdef":"%s",'
        '"cpk_0123456789abcdef0123456789abcdef":"%s"}'
        % (_encoded(KEY_1), _encoded(KEY_2)),
        json.dumps({KEY_1_ID: _encoded(KEY_1) + "="}),
    ],
)
def test_keyring_rejects_weak_duplicate_or_noncanonical_material(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_customer_production_pseudonym_keyring(
            raw, active_key_id=KEY_1_ID
        )
