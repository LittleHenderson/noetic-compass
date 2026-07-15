"""Adversarial contract tests for verified Airtable CRM upserts."""

from __future__ import annotations

import io
import json
from copy import deepcopy
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

from api.config import Settings
from api.services.crm import (
    AirtableCRMProvider,
    CRMConfigError,
    CRMProviderError,
    CRMService,
    CRMStateError,
    CRMSyncResult,
    CRMVerificationReceipt,
    JsonlFileLeadStore,
    Lead,
    LeadSubmission,
    airtable_email_dedup_key,
)
from api.services.crm.sync import _AIRTABLE_NO_REDIRECT_OPENER, _RejectRedirects


class _Response:
    def __init__(self, payload: object, *, raw: bytes | None = None) -> None:
        self._body = raw if raw is not None else json.dumps(payload).encode("utf-8")
        self.last_read_amount: int | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, amount: int = -1) -> bytes:
        self.last_read_amount = amount
        return self._body if amount < 0 else self._body[:amount]


class _FakeAirtable:
    """Small stateful implementation of the three Airtable calls the provider requires."""

    def __init__(self) -> None:
        self.requests = []
        self.records: dict[str, dict[str, object]] = {}
        self.record_by_dedup: dict[str, str] = {}
        self.duplicate_list = False
        self.list_record_id_override: str | None = None
        self.list_offset: object = _MISSING
        self.direct_field_overrides: dict[str, object] = {}

    def __call__(self, request, timeout):
        assert timeout == 15
        self.requests.append(request)
        method = request.get_method()
        if method == "PATCH":
            payload = json.loads(request.data.decode("utf-8"))
            dedup_field = payload["performUpsert"]["fieldsToMergeOn"][0]
            fields = payload["records"][0]["fields"]
            dedup_key = fields[dedup_field]
            record_id = self.record_by_dedup.get(dedup_key)
            created = record_id is None
            if record_id is None:
                record_id = f"rec{len(self.records) + 1:014d}"
                self.record_by_dedup[dedup_key] = record_id
            record = {"id": record_id, "fields": deepcopy(fields)}
            self.records[record_id] = record
            return _Response(
                {
                    "records": [deepcopy(record)],
                    "createdRecords": [record_id] if created else [],
                    "updatedRecords": [] if created else [record_id],
                }
            )

        parsed = urlparse(request.full_url)
        if parsed.query:
            query = parse_qs(parsed.query)
            assert query["maxRecords"] == ["2"]
            assert query["pageSize"] == ["2"]
            # The filter contains only the configured field and pseudonymous key, never an email.
            assert "filterByFormula" in query
            formula = query["filterByFormula"][0]
            prefix = "{Email Dedup Key}='"
            assert formula.startswith(prefix) and formula.endswith("'")
            dedup_key = formula[len(prefix) : -1]
            records = [
                deepcopy(record)
                for record in self.records.values()
                if record["fields"]["Email Dedup Key"] == dedup_key  # type: ignore[index]
            ]
            if records and self.list_record_id_override is not None:
                records[0]["id"] = self.list_record_id_override
            if self.duplicate_list and records:
                duplicate = deepcopy(records[0])
                duplicate["id"] = "rec99999999999999"
                records.append(duplicate)
            response: dict[str, object] = {"records": records[:2]}
            if self.list_offset is not _MISSING:
                response["offset"] = self.list_offset
            return _Response(response)

        record_id = parsed.path.rsplit("/", 1)[-1]
        record = deepcopy(self.records[record_id])
        fields = record["fields"]
        assert isinstance(fields, dict)
        for field_name, value in self.direct_field_overrides.items():
            if value is _MISSING:
                fields.pop(field_name, None)
            else:
                fields[field_name] = value
        return _Response(record)


_MISSING = object()


def _lead(email: str = "Lead@Example.com") -> Lead:
    return Lead.from_submission(
        LeadSubmission(
            email=email,
            name="Ada Lovelace",
            organization="Analytical Engines Ltd",
            message="Please arrange a CAS Harness demo.",
            interest="cas_harness",
            metadata={"campaign": "acceptance"},
            consent_to_contact=True,
            privacy_notice_version="privacy-2026-07-15",
        ).validated(),
        source="customer_production_acceptance_probe",
        trace_id="crm-verification-test",
    )


def _provider(fake_open, **overrides) -> AirtableCRMProvider:
    values = {
        "token": "pat-secret-do-not-persist",
        "base_id": "app123",
        "table_name": "Leads",
        "dedup_field": "Email Dedup Key",
        "owner_field": "Owner",
        "owner_value": "CAS Sales",
        "lifecycle_field": "Lifecycle",
        "http_open": fake_open,
    }
    values.update(overrides)
    return AirtableCRMProvider(**values)


def test_email_dedup_key_is_stable_normalized_and_privacy_safe() -> None:
    first = airtable_email_dedup_key("  Lead@Example.COM ")
    second = airtable_email_dedup_key("lead@example.com")

    assert first == second
    assert first.startswith("nc-email-sha256-v1:")
    assert "lead" not in first and "example.com" not in first and "@" not in first


def test_settings_keep_crm_dark_and_map_all_airtable_contract_fields(monkeypatch) -> None:
    for name in (
        "NC_CRM_PROVIDER",
        "NC_AIRTABLE_DEDUP_FIELD",
        "NC_AIRTABLE_OWNER_FIELD",
        "NC_AIRTABLE_OWNER_VALUE",
        "NC_AIRTABLE_LIFECYCLE_FIELD",
    ):
        monkeypatch.delenv(name, raising=False)

    defaults = Settings(_env_file=None)
    assert defaults.crm_provider == "null"

    monkeypatch.setenv("NC_CRM_PROVIDER", "airtable")
    monkeypatch.setenv("NC_AIRTABLE_DEDUP_FIELD", "Email Dedup Key")
    monkeypatch.setenv("NC_AIRTABLE_OWNER_FIELD", "Accountable Owner")
    monkeypatch.setenv("NC_AIRTABLE_OWNER_VALUE", "CAS Sales")
    monkeypatch.setenv("NC_AIRTABLE_LIFECYCLE_FIELD", "Lifecycle")
    configured = Settings(_env_file=None)
    assert configured.crm_provider == "airtable"
    assert configured.crm_airtable_dedup_field == "Email Dedup Key"
    assert configured.crm_airtable_owner_field == "Accountable Owner"
    assert configured.crm_airtable_owner_value == "CAS Sales"
    assert configured.crm_airtable_lifecycle_field == "Lifecycle"


def test_create_then_retry_updates_the_same_external_record_and_unique_list() -> None:
    fake = _FakeAirtable()
    provider = _provider(fake)

    created = provider.sync_lead(_lead("Lead@Example.com"))
    retried = provider.sync_lead(_lead(" lead@example.COM "))

    assert created.external_id == retried.external_id
    assert len(fake.records) == 1
    assert created.verification_receipt is not None
    assert retried.verification_receipt is not None
    assert retried.verification_receipt.readback_verified is True
    assert retried.verification_receipt.deduplicated is True
    assert retried.verification_receipt.owner_assigned is True
    assert retried.verification_receipt.provider == "airtable"
    assert retried.verification_receipt.lifecycle_stage == "new"
    assert len(retried.verification_receipt.verified_at) == 20
    datetime.strptime(retried.verification_receipt.verified_at, "%Y-%m-%dT%H:%M:%SZ")
    assert retried.verification_receipt.response_digest.startswith("sha256:")
    assert len(retried.verification_receipt.response_digest) == 71
    patches = [request for request in fake.requests if request.get_method() == "PATCH"]
    assert len(patches) == 2
    for request in patches:
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["performUpsert"] == {"fieldsToMergeOn": ["Email Dedup Key"]}
    list_requests = [request for request in fake.requests if urlparse(request.full_url).query]
    assert len(list_requests) == 2
    assert all("lead%40example.com" not in request.full_url.lower() for request in list_requests)


def test_verification_receipt_survives_jsonl_restart(tmp_path) -> None:
    fake = _FakeAirtable()
    path = tmp_path / "leads.jsonl"
    service = CRMService(JsonlFileLeadStore(path), _provider(fake))

    synced = service.capture(
        LeadSubmission(
            email="lead@example.com",
            consent_to_contact=True,
            privacy_notice_version="privacy-2026-07-15",
        ),
        source="acceptance",
        trace_id="receipt-persistence",
    )
    reopened = JsonlFileLeadStore(path).get(synced.lead_id)

    assert reopened is not None
    assert reopened.sync_status == "synced"
    assert reopened.verification_receipt == synced.verification_receipt
    assert reopened.verification_receipt is not None
    assert reopened.verification_receipt.response_digest.startswith("sha256:")


def test_ambiguous_filtered_readback_is_not_synced() -> None:
    fake = _FakeAirtable()
    fake.duplicate_list = True

    with pytest.raises(CRMProviderError, match="category=ambiguous_deduplication"):
        _provider(fake).sync_lead(_lead())


def test_unique_filtered_readback_for_a_different_record_is_not_synced() -> None:
    fake = _FakeAirtable()
    fake.list_record_id_override = "recDifferent000001"

    with pytest.raises(CRMProviderError, match="category=record_id_mismatch"):
        _provider(fake).sync_lead(_lead())


@pytest.mark.parametrize("owner_readback", [_MISSING, "Wrong Owner"])
def test_missing_or_wrong_owner_readback_is_not_synced(owner_readback: object) -> None:
    fake = _FakeAirtable()
    fake.direct_field_overrides["Owner"] = owner_readback

    with pytest.raises(CRMProviderError, match="category=owner_mismatch"):
        _provider(fake).sync_lead(_lead())


def test_airtable_configuration_fails_loud_without_owner_value() -> None:
    with pytest.raises(CRMConfigError, match="NC_AIRTABLE_OWNER_VALUE"):
        _provider(_FakeAirtable(), owner_value="")


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "http://api.airtable.com/v0",
        "https://api.airtable.com.evil.example/v0",
        "https://user@api.airtable.com/v0",
        "https://api.airtable.com/v0?redirect=evil",
        "https://api.airtable.com/v0#fragment",
        "https://api.airtable.com/v1",
    ],
)
def test_airtable_configuration_refuses_unsafe_bearer_destinations(unsafe_url: str) -> None:
    fake = _FakeAirtable()

    with pytest.raises(CRMConfigError, match="must be exactly"):
        _provider(fake, api_base_url=unsafe_url)

    assert fake.requests == []


def test_default_airtable_transport_disables_redirects() -> None:
    assert any(
        isinstance(handler, _RejectRedirects)
        for handler in _AIRTABLE_NO_REDIRECT_OPENER.handlers
    )


def test_filtered_readback_rejects_even_an_empty_pagination_offset() -> None:
    fake = _FakeAirtable()
    fake.list_offset = ""

    with pytest.raises(CRMProviderError, match="category=ambiguous_deduplication"):
        _provider(fake).sync_lead(_lead())


@pytest.mark.parametrize(
    ("field_name", "wrong_value", "category"),
    [
        ("Lead ID", "lead-stale-version", "stale_readback"),
        ("Email", "other@example.com", "stale_readback"),
        ("Consent to Contact", False, "stale_readback"),
        ("Consent Recorded At UTC", "2026-01-01T00:00:00Z", "stale_readback"),
        ("Privacy Notice URL", "https://example.invalid/privacy", "stale_readback"),
        ("Privacy Notice Version", "stale-version", "stale_readback"),
        ("Lifecycle", "qualified", "lifecycle_mismatch"),
        ("Email Dedup Key", "nc-email-sha256-v1:" + ("f" * 64), "dedup_key_mismatch"),
    ],
)
def test_wrong_or_stale_direct_readback_is_not_synced(
    field_name: str, wrong_value: object, category: str
) -> None:
    fake = _FakeAirtable()
    fake.direct_field_overrides[field_name] = wrong_value

    with pytest.raises(CRMProviderError, match=f"category={category}"):
        _provider(fake).sync_lead(_lead())


def test_cleared_optional_field_cannot_leave_stale_airtable_pii() -> None:
    fake = _FakeAirtable()
    fake.direct_field_overrides["Message"] = "stale message from an older submission"
    lead = Lead.from_submission(
        LeadSubmission(
            email="lead@example.com",
            consent_to_contact=True,
            privacy_notice_version="privacy-2026-07-15",
        ).validated(),
        source="acceptance",
        trace_id=None,
    )

    with pytest.raises(CRMProviderError, match="category=stale_readback"):
        _provider(fake).sync_lead(lead)


@pytest.mark.parametrize("failure_kind", ["http", "transport", "invalid_json"])
def test_provider_errors_are_normalized_and_secret_safe(failure_kind: str) -> None:
    secret_material = "pat-secret-do-not-persist lead@example.com provider-body-secret"

    def failing_open(request, timeout):
        if failure_kind == "http":
            raise HTTPError(
                request.full_url,
                422,
                "provider-body-secret",
                None,
                io.BytesIO(secret_material.encode("utf-8")),
            )
        if failure_kind == "transport":
            raise URLError(secret_material)
        return _Response({}, raw=secret_material.encode("utf-8"))

    with pytest.raises(CRMProviderError) as captured:
        _provider(failing_open).sync_lead(_lead())

    rendered = str(captured.value)
    assert "pat-secret" not in rendered
    assert "lead@example.com" not in rendered
    assert "provider-body-secret" not in rendered
    assert "stage=upsert" in rendered


def test_oversized_provider_response_is_rejected_after_a_bounded_read() -> None:
    oversized = b"{" + (b"x" * 2_000_000)
    response = _Response({}, raw=oversized)

    with pytest.raises(CRMProviderError, match="category=response_too_large"):
        _provider(lambda request, timeout: response).sync_lead(_lead())

    assert response.last_read_amount == 2_000_001


def test_duplicate_provider_json_keys_are_rejected() -> None:
    duplicate_keys = b'{"records":[],"records":[]}'

    with pytest.raises(CRMProviderError, match="category=duplicate_json_key"):
        _provider(lambda request, timeout: _Response({}, raw=duplicate_keys)).sync_lead(_lead())


@pytest.mark.parametrize("constant", [b"NaN", b"Infinity", b"-Infinity"])
def test_nonstandard_provider_json_constants_are_rejected(constant: bytes) -> None:
    invalid_json = b'{"records":' + constant + b"}"

    with pytest.raises(CRMProviderError, match="category=invalid_json"):
        _provider(lambda request, timeout: _Response({}, raw=invalid_json)).sync_lead(_lead())


def test_legacy_lead_json_without_verification_receipt_remains_readable() -> None:
    legacy = _lead().to_dict()
    legacy.pop("verification_receipt")
    legacy["sync_status"] = "synced"
    legacy["external_id"] = "recLegacy0000001"

    restored = Lead.from_dict(legacy)

    assert restored.sync_status == "synced"
    assert restored.external_id == "recLegacy0000001"
    assert restored.verification_receipt is None


def test_v1_lead_without_consent_fields_remains_readable_but_not_acceptance_ready() -> None:
    legacy = _lead().to_dict()
    legacy["schema_version"] = "noetic_crm.v1"
    for field in (
        "consent_to_contact",
        "privacy_notice_url",
        "privacy_notice_version",
        "consent_recorded_at_utc",
        "consent_schema_version",
    ):
        legacy.pop(field)

    restored = Lead.from_dict(legacy)

    assert restored.schema_version == "noetic_crm.v1"
    assert restored.consent_to_contact is False
    assert restored.consent_recorded_at_utc == ""


def test_v2_lead_missing_consent_fields_fails_closed() -> None:
    corrupt = _lead().to_dict()
    corrupt.pop("consent_recorded_at_utc")

    with pytest.raises(CRMStateError, match="consent_recorded_at_utc"):
        Lead.from_dict(corrupt)


def test_corrupt_persisted_verification_receipt_fails_loud() -> None:
    corrupt = _lead().to_dict()
    corrupt["verification_receipt"] = {
        "readback_verified": True,
        "deduplicated": False,
        "owner_assigned": True,
        "lifecycle_stage": "new",
        "verified_at": "2026-07-14T20:00:00Z",
        "response_digest": "sha256:" + ("0" * 64),
    }

    with pytest.raises(CRMStateError, match="all verified"):
        Lead.from_dict(corrupt)


def test_non_object_persisted_verification_receipt_fails_loud() -> None:
    corrupt = _lead().to_dict()
    corrupt["verification_receipt"] = "not-a-receipt"

    with pytest.raises(CRMStateError, match="JSON object or null"):
        Lead.from_dict(corrupt)


@pytest.mark.parametrize("malformed", [123, "New", " new", "qualified "])
def test_malformed_persisted_receipt_lifecycle_fails_loud(malformed: object) -> None:
    corrupt = _lead().to_dict()
    corrupt["verification_receipt"] = {
        "readback_verified": True,
        "deduplicated": True,
        "owner_assigned": True,
        "lifecycle_stage": malformed,
        "verified_at": "2026-07-14T20:00:00Z",
        "response_digest": "sha256:" + ("0" * 64),
    }

    with pytest.raises(CRMStateError, match="exact canonical value"):
        Lead.from_dict(corrupt)


@pytest.mark.parametrize(
    "noncanonical",
    [
        "2026-07-14T20:00:00+00:00",
        "2026-07-14T20:00:00.123456Z",
        "2026-07-14 20:00:00Z",
    ],
)
def test_verification_receipt_requires_canonical_whole_second_utc(
    noncanonical: str,
) -> None:
    with pytest.raises(CRMStateError, match="whole-second UTC"):
        CRMVerificationReceipt(
            readback_verified=True,
            deduplicated=True,
            owner_assigned=True,
            lifecycle_stage="new",
            verified_at=noncanonical,
            response_digest="sha256:" + ("0" * 64),
        )


def test_airtable_sync_result_cannot_claim_success_without_verified_receipt() -> None:
    with pytest.raises(ValueError, match="verification receipt"):
        CRMSyncResult(
            provider="airtable",
            synced=True,
            is_real=True,
            external_id="recUnverified0001",
        )


def test_incomplete_verification_receipt_cannot_exist() -> None:
    with pytest.raises(ValueError, match="all verified"):
        CRMVerificationReceipt(
            readback_verified=True,
            deduplicated=False,
            owner_assigned=True,
            lifecycle_stage="new",
            verified_at="2026-07-14T20:00:00Z",
            response_digest="sha256:" + ("0" * 64),
        )
