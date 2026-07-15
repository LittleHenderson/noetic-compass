"""Hostile source-binding tests for hosted-customer-journey evidence."""

from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json

import pytest

from api.services.accounts.models import ACCOUNT_KIND, Account
from api.services.accounts.store import ACCOUNTS_STORAGE_TENANT, AccountStore
from api.services.customer_production_pseudonyms import (
    ACCOUNT_DOMAIN,
    HOSTED_JOURNEY_TRACE_DOMAIN,
    TENANT_DOMAIN,
    CustomerProductionPseudonymizer,
)
from api.services.hosted_customer_journey_acceptance_binding import (
    AUDIT_KIND,
    AUDIT_SOURCE,
    BINDING_KIND,
    BINDING_TENANT_ID,
    SELECTOR_SCHEMA_VERSION,
    HostedCustomerJourneyAcceptanceSourceBindingStore,
    HostedCustomerJourneySourceBindingInvalid,
    HostedCustomerJourneySourceBindingUnavailable,
)
from api.services.production.state_substrate import LedgerRecord
from api.services.production.state_substrate.memory_store import InMemoryStateStore


NOW = datetime(2026, 7, 15, 18, 0, tzinfo=UTC)
TENANT_ID = "tenant-hosted-customer-production"
ACCOUNT_ID = "acct-0123456789abcdef0123456789abcdef"
AUDIT_ID = "cas-audit-hosted-source-001"
TRACE_ID = "cas-live-hosted-source-001"
KEY_ID = "cpk_0123456789abcdef0123456789abcdef"
KEY = hashlib.sha256(b"hosted-journey-source-binding-test-key").digest()
PSEUDONYMIZER = CustomerProductionPseudonymizer(
    {KEY_ID: KEY}, active_key_id=KEY_ID
)


def _stamp(offset_minutes: int = 0) -> str:
    return (NOW + timedelta(minutes=offset_minutes)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _account(
    *,
    account_id: str = ACCOUNT_ID,
    tenant_id: str = TENANT_ID,
    status: str = "active",
) -> Account:
    return Account(
        account_id=account_id,
        email_or_username=f"{account_id}@example.test",
        role="owner",
        tenant_id=tenant_id,
        status=status,  # type: ignore[arg-type]
        created_at=_stamp(),
        updated_at=_stamp(),
    )


def _put_account(backend: InMemoryStateStore, account: Account) -> LedgerRecord:
    return backend.put(
        LedgerRecord.new(
            tenant_id=ACCOUNTS_STORAGE_TENANT,
            kind=ACCOUNT_KIND,
            record_id=account.account_id,
            payload=account.to_payload(),
            source="hosted_journey_binding_test",
            trace_id=account.account_id,
            now=NOW,
        ),
        expected_version=0,
    )


def _audit_payload(
    *,
    account_id: str = ACCOUNT_ID,
    audit_id: str = AUDIT_ID,
    provider_run_phase: str = "FINALIZED",
) -> dict[str, object]:
    return {
        "_account_id": account_id,
        "audit_id": audit_id,
        "status": "COMPLETE",
        "provider_run_phase": provider_run_phase,
        "verdict": "FLAG_FOR_HUMAN_REVIEW",
        "model_id": "EleutherAI/pythia-160m",
        "audit_mode": "live",
        "updated_at": _stamp(),
        "evidence_packet_trace_id": TRACE_ID,
    }


def _put_audit(
    backend: InMemoryStateStore,
    *,
    tenant_id: str = TENANT_ID,
    account_id: str = ACCOUNT_ID,
    audit_id: str = AUDIT_ID,
    provider_run_phase: str = "FINALIZED",
) -> LedgerRecord:
    return backend.put(
        LedgerRecord.new(
            tenant_id=tenant_id,
            kind=AUDIT_KIND,
            record_id=audit_id,
            payload=_audit_payload(
                account_id=account_id,
                audit_id=audit_id,
                provider_run_phase=provider_run_phase,
            ),
            parent_ids=(account_id,),
            source=AUDIT_SOURCE,
            trace_id=audit_id,
            now=NOW,
        ),
        expected_version=0,
    )


def _evidence(
    *,
    tenant_id: str = TENANT_ID,
    account_id: str = ACCOUNT_ID,
    audit_id: str = AUDIT_ID,
    pseudonymizer: CustomerProductionPseudonymizer = PSEUDONYMIZER,
    key_id: str = KEY_ID,
) -> dict[str, object]:
    return {
        "schema_version": "cas_harness_customer_production_gate_evidence.v3",
        "gate": "hosted_customer_journey",
        **pseudonymizer.metadata(key_id=key_id),
        "tenant_subject": pseudonymizer.subject(
            domain=TENANT_DOMAIN,
            tenant_scope=tenant_id,
            value=tenant_id,
            key_id=key_id,
        ),
        "account_subject": pseudonymizer.subject(
            domain=ACCOUNT_DOMAIN,
            tenant_scope=tenant_id,
            value=account_id,
            key_id=key_id,
        ),
        "trace_subject": pseudonymizer.subject(
            domain=HOSTED_JOURNEY_TRACE_DOMAIN,
            tenant_scope=tenant_id,
            value=TRACE_ID,
            key_id=key_id,
        ),
        "audit": {
            "audit_id": audit_id,
            "terminal_status": "completed",
            "verdict": "FLAG_FOR_HUMAN_REVIEW",
            "model_id": "EleutherAI/pythia-160m",
            "mode": "live",
            "completed_at_utc": _stamp(),
        },
        "packet_download": {
            "audit_id": audit_id,
            "download_http_status": 200,
        },
    }


def _selector(
    *,
    tenant_id: str = TENANT_ID,
    account_id: str = ACCOUNT_ID,
    audit_id: str = AUDIT_ID,
) -> dict[str, object]:
    return {
        "schema_version": SELECTOR_SCHEMA_VERSION,
        "gate": "hosted_customer_journey",
        "tenant_id": tenant_id,
        "account_id": account_id,
        "audit_id": audit_id,
    }


def _fixture():
    backend = InMemoryStateStore()
    _put_account(backend, _account())
    _put_audit(backend)
    accounts = AccountStore(
        backend,
        credential_pepper="hosted-binding-test-pepper-not-production-0123456789",
    )
    binding = HostedCustomerJourneyAcceptanceSourceBindingStore(
        backend,
        accounts=accounts,
        pseudonymizer=PSEUDONYMIZER,
    )
    return backend, accounts, binding


def _replace_account(
    backend: InMemoryStateStore, **changes: object
) -> Account:
    record = backend.get(ACCOUNTS_STORAGE_TENANT, ACCOUNT_KIND, ACCOUNT_ID)
    assert record is not None
    updated = replace(Account.from_payload(record.payload), **changes)
    backend.put(
        record.with_payload(updated.to_payload(), now=NOW + timedelta(minutes=1)),
        expected_version=record.version,
    )
    return updated


def _replace_audit(
    backend: InMemoryStateStore, payload: dict[str, object]
) -> LedgerRecord:
    record = backend.get(TENANT_ID, AUDIT_KIND, AUDIT_ID)
    assert record is not None
    return backend.put(
        record.with_payload(payload, now=NOW + timedelta(minutes=1)),
        expected_version=record.version,
    )


def test_valid_binding_is_idempotent_and_public_bytes_are_pseudonymous() -> None:
    backend, _, binding = _fixture()
    evidence = _evidence()

    first = binding.create(evidence, selector=_selector(), now=NOW)
    second = binding.create(
        evidence,
        selector=_selector(),
        now=NOW + timedelta(minutes=1),
    )

    assert first == second
    binding.assert_matches(evidence, evidence_sha256=first)
    public = json.dumps(evidence, sort_keys=True)
    assert TENANT_ID not in public
    assert ACCOUNT_ID not in public
    assert TRACE_ID not in public
    assert base64.urlsafe_b64encode(KEY).rstrip(b"=").decode("ascii") not in public
    assert str(evidence["trace_subject"]).startswith("hmac-sha256:")
    rows = backend.list(BINDING_TENANT_ID, BINDING_KIND)
    assert len(rows) == 1
    assert rows[0].payload["tenant_id"] == TENANT_ID
    assert rows[0].payload["account_id"] == ACCOUNT_ID
    assert rows[0].payload["audit_id"] == AUDIT_ID


@pytest.mark.parametrize(
    "selector",
    [
        {**_selector(), "extra": True},
        _selector(tenant_id="tenant-cross-wired"),
        _selector(account_id="acct-cross-wired"),
        _selector(audit_id="cas-audit-cross-wired"),
    ],
)
def test_wrong_or_cross_wired_private_selectors_fail_closed(
    selector: dict[str, object],
) -> None:
    _, _, binding = _fixture()

    with pytest.raises(HostedCustomerJourneySourceBindingInvalid):
        binding.create(_evidence(), selector=selector, now=NOW)


def test_two_individually_valid_sources_cannot_be_cross_wired() -> None:
    backend, _, binding = _fixture()
    other_tenant = "tenant-hosted-other"
    other_account = "acct-fedcba9876543210fedcba9876543210"
    other_audit = "cas-audit-hosted-source-002"
    _put_account(
        backend,
        _account(account_id=other_account, tenant_id=other_tenant),
    )
    _put_audit(
        backend,
        tenant_id=other_tenant,
        account_id=other_account,
        audit_id=other_audit,
    )

    with pytest.raises(HostedCustomerJourneySourceBindingInvalid):
        binding.create(
            _evidence(),
            selector=_selector(
                tenant_id=other_tenant,
                account_id=other_account,
                audit_id=other_audit,
            ),
            now=NOW,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "disabled"},
        {"tenant_id": "tenant-account-moved"},
    ],
)
def test_active_binding_rechecks_account_status_and_tenant(
    changes: dict[str, object],
) -> None:
    backend, _, binding = _fixture()
    evidence = _evidence()
    digest = binding.create(evidence, selector=_selector(), now=NOW)
    _replace_account(backend, **changes)

    with pytest.raises(HostedCustomerJourneySourceBindingInvalid):
        binding.assert_matches(evidence, evidence_sha256=digest)


def test_missing_and_corrupt_audit_records_fail_closed() -> None:
    backend, _, binding = _fixture()
    evidence = _evidence()
    audit = backend.get(TENANT_ID, AUDIT_KIND, AUDIT_ID)
    assert audit is not None
    backend.delete(
        TENANT_ID,
        AUDIT_KIND,
        AUDIT_ID,
        expected_version=audit.version,
    )
    with pytest.raises(HostedCustomerJourneySourceBindingInvalid):
        binding.create(evidence, selector=_selector(), now=NOW)

    _put_audit(backend)
    corrupt = deepcopy(_audit_payload())
    corrupt.pop("_account_id")
    _replace_audit(backend, corrupt)
    with pytest.raises(HostedCustomerJourneySourceBindingInvalid):
        binding.create(evidence, selector=_selector(), now=NOW)


def test_non_finalized_audit_is_rejected() -> None:
    backend, _, binding = _fixture()
    _replace_audit(
        backend,
        _audit_payload(provider_run_phase="PROVIDER_RUNNING"),
    )

    with pytest.raises(HostedCustomerJourneySourceBindingInvalid):
        binding.create(_evidence(), selector=_selector(), now=NOW)


def test_audit_ledger_version_change_invalidates_pinned_binding() -> None:
    backend, _, binding = _fixture()
    evidence = _evidence()
    digest = binding.create(evidence, selector=_selector(), now=NOW)
    _replace_audit(backend, _audit_payload())

    with pytest.raises(
        HostedCustomerJourneySourceBindingInvalid,
        match="stale|cross-wired",
    ):
        binding.assert_matches(evidence, evidence_sha256=digest)


def test_rotation_requires_retaining_the_historical_pseudonym_key() -> None:
    backend, accounts, binding = _fixture()
    evidence = _evidence()
    digest = binding.create(evidence, selector=_selector(), now=NOW)
    rotated_key_id = "cpk_fedcba9876543210fedcba9876543210"
    rotated_key = hashlib.sha256(b"rotated-hosted-binding-key").digest()
    retaining_history = HostedCustomerJourneyAcceptanceSourceBindingStore(
        backend,
        accounts=accounts,
        pseudonymizer=CustomerProductionPseudonymizer(
            {KEY_ID: KEY, rotated_key_id: rotated_key},
            active_key_id=rotated_key_id,
        ),
    )
    retaining_history.assert_matches(evidence, evidence_sha256=digest)

    without_history = HostedCustomerJourneyAcceptanceSourceBindingStore(
        backend,
        accounts=accounts,
        pseudonymizer=CustomerProductionPseudonymizer(
            {rotated_key_id: rotated_key},
            active_key_id=rotated_key_id,
        ),
    )
    with pytest.raises(HostedCustomerJourneySourceBindingUnavailable, match="key"):
        without_history.assert_matches(evidence, evidence_sha256=digest)


def test_private_binding_hmac_tamper_and_store_read_error_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend, _, binding = _fixture()
    evidence = _evidence()
    digest = binding.create(evidence, selector=_selector(), now=NOW)
    record_id = f"hosted-journey-source-{digest}"
    record = backend.get(BINDING_TENANT_ID, BINDING_KIND, record_id)
    assert record is not None
    payload = dict(record.payload)
    payload["content_binding_hmac"] = "hmac-sha256:" + "a" * 64
    forged = replace(record, payload=payload)
    real_get = backend.get

    def forged_get(tenant_id, kind, requested_id):  # type: ignore[no-untyped-def]
        if (tenant_id, kind, requested_id) == (
            BINDING_TENANT_ID,
            BINDING_KIND,
            record_id,
        ):
            return forged
        return real_get(tenant_id, kind, requested_id)

    monkeypatch.setattr(backend, "get", forged_get)
    with pytest.raises(HostedCustomerJourneySourceBindingUnavailable, match="integrity"):
        binding.assert_matches(evidence, evidence_sha256=digest)

    def unavailable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(backend, "get", unavailable)
    with pytest.raises(HostedCustomerJourneySourceBindingUnavailable, match="store"):
        binding.assert_matches(evidence, evidence_sha256=digest)


def test_binding_store_write_error_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend, _, binding = _fixture()
    real_put = backend.put

    def unavailable(record, *, expected_version):  # type: ignore[no-untyped-def]
        if record.kind == BINDING_KIND:
            raise RuntimeError("binding store unavailable")
        return real_put(record, expected_version=expected_version)

    monkeypatch.setattr(backend, "put", unavailable)
    with pytest.raises(
        HostedCustomerJourneySourceBindingUnavailable,
        match="persistence",
    ):
        binding.create(_evidence(), selector=_selector(), now=NOW)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", "forged.audit.source"),
        ("trace_id", TRACE_ID),
        ("parent_ids", ("acct-cross-wired",)),
        ("tenant_id", "tenant-cross-wired"),
    ],
)
def test_active_binding_rejects_audit_ledger_envelope_tamper(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    backend, _, binding = _fixture()
    evidence = _evidence()
    digest = binding.create(evidence, selector=_selector(), now=NOW)
    audit = backend.get(TENANT_ID, AUDIT_KIND, AUDIT_ID)
    assert audit is not None
    forged = replace(audit, **{field: value})
    real_get = backend.get

    def forged_get(tenant_id, kind, record_id):  # type: ignore[no-untyped-def]
        if (tenant_id, kind, record_id) == (TENANT_ID, AUDIT_KIND, AUDIT_ID):
            return forged
        return real_get(tenant_id, kind, record_id)

    monkeypatch.setattr(backend, "get", forged_get)
    with pytest.raises(
        HostedCustomerJourneySourceBindingInvalid, match="finalized audit"
    ):
        binding.assert_matches(evidence, evidence_sha256=digest)


@pytest.mark.parametrize(
    "legacy_field",
    ["tenant_subject_sha256", "account_subject_sha256", "trace_id_sha256"],
)
def test_legacy_unkeyed_identifier_hashes_are_rejected(
    legacy_field: str,
) -> None:
    _, _, binding = _fixture()
    evidence = _evidence()
    evidence[legacy_field] = hashlib.sha256(legacy_field.encode()).hexdigest()

    with pytest.raises(HostedCustomerJourneySourceBindingInvalid):
        binding.create(evidence, selector=_selector(), now=NOW)


@pytest.mark.parametrize("raw_value", [TENANT_ID, ACCOUNT_ID, TRACE_ID])
def test_public_evidence_cannot_smuggle_raw_tenant_or_account_ids(
    raw_value: str,
) -> None:
    _, _, binding = _fixture()
    evidence = _evidence()
    evidence["debug_private_source"] = raw_value

    with pytest.raises(HostedCustomerJourneySourceBindingInvalid):
        binding.create(evidence, selector=_selector(), now=NOW)
