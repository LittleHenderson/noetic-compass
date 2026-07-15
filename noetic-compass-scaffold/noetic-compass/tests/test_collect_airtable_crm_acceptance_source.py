from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest

from api.services.crm import (
    CRM_CONSENT_SCHEMA_VERSION,
    CRM_PRIVACY_NOTICE_URL,
    CRM_SCHEMA_VERSION,
    CRMSyncResult,
    CRMVerificationReceipt,
    Lead,
    LeadSubmission,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "collect_airtable_crm_acceptance_source.py"
)
SPEC = importlib.util.spec_from_file_location("airtable_crm_source_collector", MODULE_PATH)
assert SPEC and SPEC.loader
collector_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = collector_module
SPEC.loader.exec_module(collector_module)


FIXED_NOW = datetime(2026, 7, 15, 0, 2, tzinfo=UTC)
MASTER_SHA = "a" * 40
DEPLOY_ID = "dep-d9ba0km7r5hc73e9ojkg"
NONCE = "0123456789abcdef01234567"
LEAD_ID = "lead-0123456789abcdef"
EXTERNAL_ID = "rec0123456789ABCD"
PRIVACY_VERSION = "privacy-2026-07-15"
CONSENT_AT = "2026-07-15T00:00:00Z"
VERIFIED_AT = "2026-07-15T00:01:00Z"
RESPONSE_DIGEST = "sha256:" + ("b" * 64)


def _runtime_env(path: Path) -> dict[str, str]:
    return {
        "RENDER_SERVICE_ID": collector_module.PRODUCTION_SERVICE_ID,
        "RENDER_GIT_COMMIT": MASTER_SHA,
        "NC_CRM_PROVIDER": "airtable",
        "NC_CRM_LEAD_STORE_PATH": str(path.resolve()),
        "NC_AIRTABLE_TOKEN": "pat-secret-never-output",
        "NC_AIRTABLE_BASE_ID": "app123",
        "NC_AIRTABLE_TABLE_NAME": "Leads",
        "NC_AIRTABLE_API_BASE_URL": collector_module.CANONICAL_AIRTABLE_API_BASE_URL,
        "NC_AIRTABLE_DEDUP_FIELD": "Email Dedup Key",
        "NC_AIRTABLE_OWNER_FIELD": "Owner",
        "NC_AIRTABLE_OWNER_VALUE": "CAS Sales",
        "NC_AIRTABLE_LIFECYCLE_FIELD": "Lifecycle",
    }


def _synced_lead(**overrides: Any) -> Lead:
    captured = Lead.from_submission(
        LeadSubmission(
            email=f"crm-acceptance-{NONCE}@acceptance.invalid",
            interest="cas_harness",
            metadata={"probe": "support_crm"},
            consent_to_contact=True,
            privacy_notice_version=PRIVACY_VERSION,
        ).validated(),
        source="customer_production_acceptance_probe",
        trace_id="req-collector",
    )
    # Reconstruct the capture with deterministic consent evidence for timestamp assertions.
    captured = Lead(
        **{
            **captured.__dict__,
            "lead_id": LEAD_ID,
            "consent_recorded_at_utc": CONSENT_AT,
        }
    )
    receipt = CRMVerificationReceipt(
        provider="airtable",
        readback_verified=True,
        deduplicated=True,
        owner_assigned=True,
        lifecycle_stage="new",
        verified_at=VERIFIED_AT,
        response_digest=RESPONSE_DIGEST,
    )
    synced = captured.with_sync_result(
        CRMSyncResult(
            provider="airtable",
            synced=True,
            is_real=True,
            external_id=EXTERNAL_ID,
            synced_at=VERIFIED_AT,
            verification_receipt=receipt,
        )
    )
    if not overrides:
        return synced
    return Lead(**{**synced.__dict__, **overrides})


def _response(**overrides: Any) -> dict[str, Any]:
    value = {
        "lead_id": LEAD_ID,
        "captured": True,
        "sync_status": "synced",
        "synced": True,
        "schema_version": CRM_SCHEMA_VERSION,
        "consent_to_contact": True,
        "privacy_notice_url": CRM_PRIVACY_NOTICE_URL,
        "privacy_notice_version": PRIVACY_VERSION,
        "consent_recorded_at_utc": CONSENT_AT,
        "consent_schema_version": CRM_CONSENT_SCHEMA_VERSION,
        "message": "received",
    }
    value.update(overrides)
    return value


def _http_result(
    value: object,
    *,
    status: int = 200,
    content_type: str = "application/json",
    raw: bytes | None = None,
):
    body = raw if raw is not None else json.dumps(value).encode("utf-8")
    return collector_module.HttpResult(
        status=status,
        headers={"content-type": content_type},
        body=body,
    )


def _collector(
    tmp_path: Path,
    *,
    response: dict[str, Any] | None = None,
    lead: Lead | None = None,
    environment: dict[str, str] | None = None,
):
    expected_response = _response() if response is None else response
    expected_lead = _synced_lead() if lead is None else lead

    def transport(**kwargs):
        assert kwargs["base_url"] == collector_module.PRODUCTION_API_ORIGIN
        assert kwargs["path"] == collector_module.PUBLIC_LEAD_PATH
        assert kwargs["method"] == "POST"
        assert kwargs["payload"]["consent_to_contact"] is True
        assert kwargs["payload"]["privacy_notice_version"] == PRIVACY_VERSION
        assert kwargs["payload"]["email"].endswith("@acceptance.invalid")
        return _http_result(expected_response)

    def read_lead(path: str, lead_id: str):
        assert Path(path) == (tmp_path / "leads.jsonl").resolve()
        assert lead_id == LEAD_ID
        return expected_lead

    return collector_module.AirtableCRMSourceCollector(
        base_url=collector_module.PRODUCTION_API_ORIGIN,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        privacy_notice_version=PRIVACY_VERSION,
        runtime_environment=(
            _runtime_env(tmp_path / "leads.jsonl")
            if environment is None
            else environment
        ),
        transport=transport,
        lead_reader=read_lead,
        clock=lambda: FIXED_NOW,
        nonce=NONCE,
    )


def test_collects_provider_bound_pii_free_open_fragment(tmp_path: Path) -> None:
    source, fragment = _collector(tmp_path).collect()

    assert source["provider"] == "airtable"
    assert source["adapter_response_digest"] == RESPONSE_DIGEST
    assert source["lead_id_sha256"] != LEAD_ID
    assert source["trace_id_sha256"] != "req-collector"
    assert source["airtable_record_id_sha256"] != EXTERNAL_ID
    assert fragment["status"] == "OPEN"
    assert fragment["missing_required_evidence"] == ["resolved_support_ticket_sla"]
    assert fragment["crm_lead"] == {
        "system": "airtable",
        "provider": "airtable",
        "lead_id_sha256": source["lead_id_sha256"],
        "airtable_record_id_sha256": source["airtable_record_id_sha256"],
        "adapter_response_digest": RESPONSE_DIGEST,
        "source_receipt_sha256": fragment["source_receipt_sha256"],
        "persisted": True,
        "readback_verified": True,
        "deduplicated": True,
        "owner_assigned": True,
        "lifecycle_stage": "new",
        "verified_at_utc": VERIFIED_AT,
    }
    assert fragment["consent"] == {
        "capture_consent_recorded": True,
        "consent_to_contact": True,
        "source_attribution_recorded": True,
        "privacy_notice_linked": True,
        "privacy_notice_url": CRM_PRIVACY_NOTICE_URL,
        "privacy_notice_version": PRIVACY_VERSION,
        "consent_schema_version": CRM_CONSENT_SCHEMA_VERSION,
        "recorded_at_utc": CONSENT_AT,
    }
    rendered = json.dumps([source, fragment], sort_keys=True)
    assert "@acceptance.invalid" not in rendered
    assert LEAD_ID not in rendered
    assert EXTERNAL_ID not in rendered
    assert "pat-secret" not in rendered


@pytest.mark.parametrize(
    "change",
    [
        {"synced": False},
        {"sync_status": "sync_pending"},
        {"schema_version": "noetic_crm.v1"},
        {"consent_to_contact": False},
        {"privacy_notice_url": "https://example.invalid/privacy"},
        {"privacy_notice_version": "stale"},
    ],
)
def test_public_capture_response_must_be_exactly_bound(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    with pytest.raises(
        collector_module.CRMCollectionFailure,
        match="capture response did not prove",
    ):
        _collector(tmp_path, response=_response(**change)).collect()


def test_public_capture_response_rejects_extra_fields(tmp_path: Path) -> None:
    with pytest.raises(collector_module.CRMCollectionFailure, match="fields drifted"):
        _collector(tmp_path, response=_response(raw_email="do-not-accept")).collect()


@pytest.mark.parametrize(
    "overrides",
    [
        {"source": "other"},
        {"trace_id": None},
        {"sync_status": "sync_pending", "external_id": None},
        {"consent_to_contact": False, "schema_version": "noetic_crm.v1"},
        {"privacy_notice_version": "stale"},
        {"consent_recorded_at_utc": "2026-07-15T00:00:01Z"},
    ],
)
def test_durable_lead_must_match_public_capture(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    lead = _synced_lead(**overrides)
    with pytest.raises(collector_module.CRMCollectionFailure, match="durable lead"):
        _collector(tmp_path, lead=lead).collect()


def test_missing_durable_lead_fails_closed(tmp_path: Path) -> None:
    collector = _collector(tmp_path)
    collector.lead_reader = lambda path, lead_id: None

    with pytest.raises(collector_module.CRMCollectionFailure, match="not durable"):
        collector.collect()


@pytest.mark.parametrize(
    "receipt_override",
    [
        {"provider": "hubspot"},
        {"readback_verified": False},
        {"response_digest": "b" * 64},
        {"lifecycle_stage": "qualified"},
    ],
)
def test_adapter_receipt_must_be_airtable_bound(
    tmp_path: Path, receipt_override: dict[str, Any]
) -> None:
    # Invalid receipt objects are blocked at construction; use a minimal duck-typed object to
    # prove the collector independently rejects corrupt persisted state.
    receipt = type(
        "CorruptReceipt",
        (),
        {
            "provider": "airtable",
            "readback_verified": True,
            "deduplicated": True,
            "owner_assigned": True,
            "lifecycle_stage": "new",
            "verified_at": VERIFIED_AT,
            "response_digest": RESPONSE_DIGEST,
            **receipt_override,
        },
    )()
    lead = _synced_lead()
    object.__setattr__(lead, "verification_receipt", receipt)

    with pytest.raises(
        collector_module.CRMCollectionFailure, match="incomplete or cross-wired"
    ):
        _collector(tmp_path, lead=lead).collect()


def test_airtable_record_id_is_hashed_only_after_shape_validation(tmp_path: Path) -> None:
    with pytest.raises(collector_module.CRMCollectionFailure, match="record ID is invalid"):
        _collector(tmp_path, lead=_synced_lead(external_id="not-airtable")).collect()


def test_timestamp_order_fails_closed(tmp_path: Path) -> None:
    lead = _synced_lead(consent_recorded_at_utc="2026-07-15T00:01:01Z")
    with pytest.raises(collector_module.CRMCollectionFailure, match="not monotonic"):
        _collector(
            tmp_path,
            lead=lead,
            response=_response(consent_recorded_at_utc="2026-07-15T00:01:01Z"),
        ).collect()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("RENDER_GIT_COMMIT", "c" * 40, "runtime commit"),
        ("RENDER_SERVICE_ID", "srv-other", "pinned production service"),
        ("NC_CRM_PROVIDER", "null", "not exact airtable"),
        ("NC_AIRTABLE_TOKEN", "", "provider contract is incomplete"),
        (
            "NC_AIRTABLE_API_BASE_URL",
            "https://evil.invalid/v0",
            "origin is not canonical",
        ),
        ("NC_CRM_LEAD_STORE_PATH", "relative/leads.jsonl", "absolute durable path"),
    ],
)
def test_runtime_and_provider_binding_fail_closed(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    environment = _runtime_env(tmp_path / "leads.jsonl")
    environment[field] = value

    with pytest.raises(collector_module.CRMCollectionFailure, match=message):
        _collector(tmp_path, environment=environment)


def test_fragment_tampering_breaks_source_receipt_binding(tmp_path: Path) -> None:
    source, fragment = _collector(tmp_path).collect()
    fragment["crm_lead"]["adapter_response_digest"] = "sha256:" + ("c" * 64)

    with pytest.raises(collector_module.CRMCollectionFailure, match="diverged"):
        collector_module._validate_output_pair(source, fragment)


def test_atomic_output_is_owner_only_and_canonical(tmp_path: Path) -> None:
    source, _fragment = _collector(tmp_path).collect()
    target = tmp_path / "receipt.json"

    collector_module._atomic_write(target, source)

    assert json.loads(target.read_text(encoding="utf-8")) == source
    if os.name != "nt":
        assert target.stat().st_mode & 0o777 == 0o600


def test_duplicate_json_response_is_rejected(tmp_path: Path) -> None:
    collector = _collector(tmp_path)
    collector.transport = lambda **kwargs: _http_result(
        {}, raw=b'{"lead_id":"one","lead_id":"two"}'
    )

    with pytest.raises(collector_module.CRMCollectionFailure, match="duplicate JSON key"):
        collector.collect()


def test_production_image_contains_the_bounded_collector() -> None:
    dockerfile = (MODULE_PATH.parent.parent / "Dockerfile.api").read_text(encoding="utf-8")
    assert (
        "COPY scripts/collect_airtable_crm_acceptance_source.py "
        "scripts/collect_airtable_crm_acceptance_source.py"
    ) in dockerfile
