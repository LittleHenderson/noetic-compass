from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from api.routes.cas_harness_audit import DataCaptureSummaryResponse
from api.services.cas_harness_retention_disclosure import (
    RETENTION_MODEL,
    ObjectLockRetentionDisclosureModel,
    canonical_retention_disclosure,
    configured_object_lock_retention_disclosure,
    evaluate_object_lock_receipt,
    object_lock_retention_disclosure,
    revalidate_object_lock_verification,
    runtime_object_lock_policy_target,
)
from api.config import settings
from api.services.cas_harness_static_evidence_anchor import (
    summarize_static_anchor_worm_status,
)
from tests.object_lock_test_support import issue_test_object_lock_receipt


def _configure(monkeypatch: pytest.MonkeyPatch, *, mode: str = "GOVERNANCE", days: str = "31") -> None:
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", mode)
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", days)


def _verification(
    *,
    now: datetime | None = None,
    mode: str = "GOVERNANCE",
    days: object = 31,
    requested_until: object | None = None,
    observed_until: object | None = None,
    expected_version: str = "version-7",
    get_version: str = "version-7",
    head_version: str = "version-7",
):
    now = now or datetime.now(UTC)
    requested_until = requested_until or now + timedelta(days=31)
    observed_until = observed_until or requested_until
    return issue_test_object_lock_receipt(
        expected={
            "bucket": "receipt-bucket",
            "key": "anchors/trace.json",
            "version_id": expected_version,
            "content_sha256": "a" * 64,
            "mode": mode,
            "retention_days": days,
            "requested_at": now,
            "retain_until": requested_until,
        },
        observed={
            "bucket": "receipt-bucket",
            "key": "anchors/trace.json",
            "get_version_id": get_version,
            "head_version_id": head_version,
            "content_sha256": "a" * 64,
            "mode": mode,
            "retain_until": observed_until,
            "reread_verified": True,
        },
        verified_at=now,
    )


def _committed_payload(receipt: dict[str, object]) -> dict[str, object]:
    return {
        "status": "DATA_CAPTURE_WORM_COMMITTED",
        "acknowledged": True,
        "capture_committed": True,
        "captured_signal_classes": ["model_input_output"],
        "retention_model": "untrusted stored label",
        "retention_disclosure": {
            "receipt_verified": True,
            "permanent_or_indefinite": True,
            "notice": "immutable forever because this prose says so",
            "verification_receipt": receipt,
        },
        "reuse_purpose": "cas_native_training_corpus",
        "notice": "immutable forever",
        "reasons": [],
    }


def test_configured_target_is_runtime_derived_not_a_deployment_constant(monkeypatch) -> None:
    _configure(monkeypatch, mode="COMPLIANCE", days="9")

    target = runtime_object_lock_policy_target()
    disclosure = configured_object_lock_retention_disclosure(
        subject="Evidence Packet trace-runtime"
    )

    assert target.mode == "COMPLIANCE"
    assert target.retention_days == 9
    assert disclosure.claim_basis == "configured_target"
    assert disclosure.mode == "COMPLIANCE"
    assert disclosure.retention_days == 9
    assert disclosure.receipt_verified is False
    assert disclosure.retain_until is None
    assert disclosure.tamper_evident_on_reverify is False
    assert "target, not proof" in disclosure.notice


def test_arbitrary_scalar_arguments_cannot_invent_a_configured_target(monkeypatch) -> None:
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", raising=False)
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", raising=False)

    disclosure = object_lock_retention_disclosure(
        subject="customer packet",
        mode="COMPLIANCE",
        retention_days=9999,
        retain_until="2099-01-01T00:00:00+00:00",
        receipt_verified=True,
    )

    assert disclosure.claim_basis == "unconfigured"
    assert disclosure.policy_configured is False
    assert disclosure.mode is None
    assert disclosure.retention_days is None
    assert disclosure.receipt_verified is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mode", "COMPLIANCE"),
        ("retention_days", 1),
        ("policy_configured", False),
        ("rolling_from_each_write", False),
        ("privileged_operator_override_possible", False),
        ("tamper_evident_on_reverify", False),
    ],
)
def test_direct_disclosure_model_rejects_fields_inconsistent_with_receipt(
    field: str,
    value: object,
) -> None:
    receipt = _verification()
    payload = object_lock_retention_disclosure(
        subject="customer packet",
        verification_receipt=receipt,
    ).to_dict()
    payload[field] = value

    with pytest.raises(ValueError):
        ObjectLockRetentionDisclosureModel.model_validate(payload)


def test_direct_disclosure_model_rejects_false_configured_target() -> None:
    payload = configured_object_lock_retention_disclosure(
        subject="customer packet",
        environ={
            "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE": "GOVERNANCE",
            "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS": "31",
        },
    ).to_dict()
    payload["policy_configured"] = False

    with pytest.raises(ValueError):
        ObjectLockRetentionDisclosureModel.model_validate(payload)


def test_retention_days_requires_the_full_window_from_request_time() -> None:
    requested_at = datetime.now(UTC).replace(microsecond=0)
    verification = _verification(
        now=requested_at,
        days=31,
        requested_until=requested_at + timedelta(days=31) - timedelta(seconds=1),
        observed_until=requested_at + timedelta(days=31),
    )

    assert verification.verified is False
    assert (
        "requested retain_until is shorter than the full retention_days window"
        in verification.failure_reasons
    )


def test_historical_revalidation_preserves_verified_at_and_records_evaluated_at() -> None:
    original_at = datetime.now(UTC).replace(microsecond=0)
    original = _verification(now=original_at)
    evaluated_at = original_at + timedelta(hours=2)

    reevaluated = revalidate_object_lock_verification(
        original.to_dict(),
        evaluated_at=evaluated_at,
    )

    assert reevaluated is not None and reevaluated.verified is True
    assert reevaluated.verified_at == original.verified_at
    assert reevaluated.evaluated_at == evaluated_at.isoformat()
    assert reevaluated.evaluated_at != reevaluated.verified_at


def test_self_consistent_public_predicate_mapping_cannot_mint_receipt(monkeypatch) -> None:
    _configure(monkeypatch)
    signed = _verification()
    diagnostic = evaluate_object_lock_receipt(
        expected=signed.expected,
        observed=signed.observed,
    )

    assert diagnostic.verified is True
    assert diagnostic.issuer_attestation is None
    assert revalidate_object_lock_verification(diagnostic.to_dict()) is None
    disclosure = canonical_retention_disclosure(
        {"verification_receipt": diagnostic.to_dict()},
        subject="forged stored packet",
    )
    assert disclosure.claim_basis == "configured_target"
    assert disclosure.receipt_verified is False
    assert disclosure.tamper_evident_on_reverify is False


def test_expected_override_must_equal_attested_binding() -> None:
    receipt = _verification()
    substituted = dict(receipt.expected)
    # This weaker duration would still be self-consistent with the same observed
    # deadline, so the attested expected mapping itself must be compared.
    substituted["retention_days"] = 1

    assert (
        revalidate_object_lock_verification(receipt.to_dict(), expected=substituted)
        is None
    )


def test_attestation_key_rotation_fails_closed_until_original_key_is_restored(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "object_lock_receipt_attestation_key", "a" * 32)
    receipt = _verification()
    assert revalidate_object_lock_verification(receipt.to_dict()) is not None

    monkeypatch.setattr(settings, "object_lock_receipt_attestation_key", "b" * 32)
    assert revalidate_object_lock_verification(receipt.to_dict()) is None

    monkeypatch.setattr(settings, "object_lock_receipt_attestation_key", "a" * 32)
    restored = revalidate_object_lock_verification(receipt.to_dict())
    assert restored is not None and restored.verified is True


def test_revalidation_uses_current_time_not_historical_verified_at() -> None:
    original_at = datetime.now(UTC) - timedelta(days=3)
    deadline = original_at + timedelta(days=2)
    receipt = _verification(
        now=original_at,
        days=1,
        requested_until=deadline,
        observed_until=deadline,
    )
    # Explicit historical issuance is valid at its recorded evaluation time.
    receipt = issue_test_object_lock_receipt(
        expected=receipt.expected,
        observed=receipt.observed,
        verified_at=original_at,
        evaluated_at=original_at,
    )
    assert receipt.verified is True and receipt.issuer_attestation

    current = revalidate_object_lock_verification(receipt.to_dict())
    assert current is not None
    assert current.verified is False
    assert current.issuer_attestation is None
    assert "observed retain_until is expired" in current.failure_reasons


def test_config_drift_rebuilds_target_and_does_not_preserve_stored_claim(monkeypatch) -> None:
    _configure(monkeypatch, mode="GOVERNANCE", days="31")
    stale = configured_object_lock_retention_disclosure(subject="captured audit signal").to_dict()
    stale["notice"] = "immutable forever"
    _configure(monkeypatch, mode="COMPLIANCE", days="7")

    payload = _committed_payload({})
    payload["retention_disclosure"] = stale
    response = DataCaptureSummaryResponse.model_validate(payload)

    assert response.status == "DATA_CAPTURE_ACKNOWLEDGED"
    assert response.retention_disclosure.claim_basis == "configured_target"
    assert response.retention_disclosure.mode == "COMPLIANCE"
    assert response.retention_disclosure.retention_days == 7
    assert "immutable forever" not in response.retention_disclosure.notice


def test_old_durable_data_capture_claim_is_sanitized_before_api_response(monkeypatch) -> None:
    _configure(monkeypatch)
    old_payload = {
        "status": "DATA_CAPTURE_ACKNOWLEDGED",
        "acknowledged": True,
        "capture_committed": False,
        "captured_signal_classes": ["model_input_output"],
        "retention_model": "write_once_read_many",
        "reuse_purpose": "cas_native_training_corpus",
        "notice": "captured signal is retained indefinitely and cannot be deleted",
        "reasons": [],
    }

    response = DataCaptureSummaryResponse.model_validate(old_payload)

    assert response.retention_model == "s3_object_lock_governance_time_bounded"
    assert response.retention_disclosure.mode == "GOVERNANCE"
    assert response.retention_disclosure.retention_days == 31
    assert response.retention_disclosure.receipt_verified is False
    assert response.retention_disclosure.permanent_or_indefinite is False
    assert "indefinitely and cannot be deleted" not in response.notice


def test_api_response_preserves_only_a_structured_receipt_backed_commit(monkeypatch) -> None:
    _configure(monkeypatch)
    verification = _verification()
    response = DataCaptureSummaryResponse.model_validate(
        _committed_payload(verification.to_dict())
    )

    assert response.status == "DATA_CAPTURE_WORM_COMMITTED"
    assert response.capture_committed is True
    assert response.retention_disclosure.claim_basis == "verified_receipt"
    assert response.retention_disclosure.receipt_verified is True
    assert response.retention_disclosure.permanent_or_indefinite is False
    assert response.retention_disclosure.verification_receipt is not None
    assert "immutable forever" not in response.notice


@pytest.mark.parametrize(
    "mutation",
    [
        "expired",
        "malformed_deadline",
        "shortened",
        "get_version_swap",
        "head_version_swap",
        "key_swap",
        "bucket_swap",
        "mode_swap",
        "hash_swap",
        "boolean_days",
    ],
)
def test_adversarial_receipts_cannot_preserve_worm_commit(monkeypatch, mutation: str) -> None:
    _configure(monkeypatch)
    now = datetime.now(UTC)
    receipt = deepcopy(_verification(now=now).to_dict())
    expected = receipt["expected"]
    observed = receipt["observed"]
    assert isinstance(expected, dict) and isinstance(observed, dict)
    if mutation == "expired":
        expected["retain_until"] = (now - timedelta(days=2)).isoformat()
        observed["retain_until"] = (now - timedelta(days=1)).isoformat()
    elif mutation == "malformed_deadline":
        observed["retain_until"] = "tomorrow-ish"
    elif mutation == "shortened":
        observed["retain_until"] = (now + timedelta(days=1)).isoformat()
    elif mutation == "get_version_swap":
        observed["get_version_id"] = "attacker-version"
    elif mutation == "head_version_swap":
        observed["head_version_id"] = "attacker-version"
    elif mutation == "key_swap":
        observed["key"] = "anchors/substituted.json"
    elif mutation == "bucket_swap":
        observed["bucket"] = "attacker-bucket"
    elif mutation == "mode_swap":
        observed["mode"] = "COMPLIANCE"
    elif mutation == "hash_swap":
        observed["content_sha256"] = "b" * 64
    elif mutation == "boolean_days":
        expected["retention_days"] = True

    response = DataCaptureSummaryResponse.model_validate(_committed_payload(receipt))

    assert response.status == "DATA_CAPTURE_ACKNOWLEDGED"
    assert response.capture_committed is False
    assert response.retention_disclosure.receipt_verified is False
    assert response.retention_disclosure.verification_receipt is None


def test_fake_verifier_prose_cannot_make_static_packet_worm_retained(monkeypatch) -> None:
    _configure(monkeypatch)
    anchored = {
        "trace_id": "trace-fake-prose",
        "hashes": {
            "external_anchor": {
                "status": "anchored",
                "mode": "s3",
                "bucket": "receipt-bucket",
                "key": "anchors/trace.json",
                "version_id": "version-7",
                "manifest_sha256": "a" * 64,
                "object_lock_mode": "GOVERNANCE",
                "object_lock_retain_until": (datetime.now(UTC) + timedelta(days=31)).isoformat(),
                "retention_days": 31,
            }
        },
    }
    verify = {
        "overall": "all_match",
        "checks": [
            {
                "artifact": "merged_packet_external_anchor",
                "match": True,
                "notes": "object was re-read; Object Lock retention is active forever",
            }
        ],
    }

    summary = summarize_static_anchor_worm_status(anchored, verify)

    assert summary["worm_retained"] is False
    assert summary["retention_disclosure"]["receipt_verified"] is False


def test_structured_static_verifier_receipt_licenses_finite_worm_claim(monkeypatch) -> None:
    _configure(monkeypatch)
    verification = _verification()
    expected = verification.expected
    anchored = {
        "trace_id": "trace-structured",
        "hashes": {
            "external_anchor": {
                "status": "anchored",
                "mode": "s3",
                "anchor_uri": "s3://receipt-bucket/anchors/trace.json?versionId=version-7",
                "bucket": expected["bucket"],
                "key": expected["key"],
                "version_id": expected["version_id"],
                "manifest_sha256": expected["content_sha256"],
                "object_lock_mode": expected["mode"],
                "retention_requested_at": expected["requested_at"],
                "object_lock_retain_until": expected["retain_until"],
                "retention_days": expected["retention_days"],
            }
        },
    }
    verify = {
        "overall": "all_match",
        "checks": [
            {
                "artifact": "merged_packet_external_anchor",
                "match": True,
                "notes": "display prose is irrelevant",
                "object_lock_verification": verification.to_dict(),
            }
        ],
    }

    summary = summarize_static_anchor_worm_status(anchored, verify)

    assert summary["worm_retained"] is True
    assert summary["retention_disclosure"]["claim_basis"] == "verified_receipt"
    assert summary["retention_disclosure"]["receipt_verified"] is True
    assert summary["retention_disclosure"]["permanent_or_indefinite"] is False


def test_openapi_uses_strict_retention_disclosure_models(client) -> None:
    openapi = client.get("/openapi.json").json()
    schemas = openapi["components"]["schemas"]
    capture = schemas["DataCaptureSummaryResponse"]["properties"]["retention_disclosure"]
    anchor = schemas["AnchorEvidenceResponse"]["properties"]["retention_disclosure"]

    assert capture["$ref"].endswith("/ObjectLockRetentionDisclosureModel")
    assert anchor["$ref"].endswith("/ObjectLockRetentionDisclosureModel")
    disclosure_schema = schemas["ObjectLockRetentionDisclosureModel"]
    assert disclosure_schema["additionalProperties"] is False
    assert "verification_receipt" in disclosure_schema["properties"]


def test_customer_faq_separates_target_from_receipt() -> None:
    faq = Path("dashboard/src/pages/FaqPage.tsx").read_text(encoding="utf-8")

    assert "immutable hash logging" not in faq
    assert "tamper-evident hash logging with re-verification" in faq
    assert "runtime-configured target separately from the exact verified receipt" in faq
    assert "GOVERNANCE mode, when actually used" in faq
    assert "31-day" not in faq
    assert RETENTION_MODEL == "s3_object_lock_time_bounded"
