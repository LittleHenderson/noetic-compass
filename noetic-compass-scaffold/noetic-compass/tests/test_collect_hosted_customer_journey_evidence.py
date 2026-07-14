from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "collect_hosted_customer_journey_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("hosted_customer_journey_collector", MODULE_PATH)
assert SPEC and SPEC.loader
collector_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = collector_module
SPEC.loader.exec_module(collector_module)

VERIFIER_PATH = REPO_ROOT / "scripts" / "verify_customer_production_acceptance.py"
VERIFIER_SPEC = importlib.util.spec_from_file_location("customer_acceptance_verifier", VERIFIER_PATH)
assert VERIFIER_SPEC and VERIFIER_SPEC.loader
verifier = importlib.util.module_from_spec(VERIFIER_SPEC)
sys.modules[VERIFIER_SPEC.name] = verifier
VERIFIER_SPEC.loader.exec_module(verifier)


FIXED_NOW = datetime(2026, 7, 14, 20, 10, tzinfo=UTC)
MASTER_SHA = "a" * 40
DEPLOY_ID = "dep-d9ba0km7r5hc73e9ojkg"
PLATFORM_SECRET = "platform-secret-value"
BILLING_SECRET = "billing-secret-value"
TOKEN_A = "token-a-private-value"
TOKEN_B = "token-b-private-value"
SHARE_TOKEN = "share-token-private-value"
TRACE_ID = "cas-live-customer-production-trace"
AUDIT_ID = "cas-audit-0123456789abcdef"


def _body(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _result(
    status: int, value: Mapping[str, Any], *, content_type: str = "application/json"
):
    return collector_module.HttpResult(
        status=status,
        headers={"content-type": content_type},
        body=_body(value),
    )


def _packet(*, anchored: bool = True) -> dict[str, Any]:
    return {
        "trace_id": TRACE_ID,
        "verdict": "FLAG_FOR_HUMAN_REVIEW",
        "hashes": {
            "external_anchor": {
                "status": "anchored" if anchored else "failed",
                "mode": "s3",
                "object_lock_mode": "GOVERNANCE",
                "retention_days": 31,
                "retention_requested_at": "2026-07-14T20:00:00Z",
                "object_lock_retain_until": "2026-08-14T20:00:00Z",
            }
        },
        "live_audit": {"model_id": collector_module.MODEL_ID},
    }


class FakeJourneyTransport:
    def __init__(self, *, anchored: bool = True, foreign_status: int = 404) -> None:
        self.calls: list[dict[str, Any]] = []
        self.packet = _packet(anchored=anchored)
        self.foreign_status = foreign_status
        self.account_a = "acct-primary-secret-id"
        self.account_b = "acct-foreign-secret-id"

    def __call__(
        self,
        *,
        base_url: str,
        path: str,
        method: str,
        payload: Mapping[str, Any] | None,
        headers: Mapping[str, str],
        timeout: float,
    ):
        self.calls.append(
            {
                "base_url": base_url,
                "path": path,
                "method": method,
                "payload": payload,
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        index = len(self.calls)
        # Failed probes perform best-effort session cleanup immediately rather
        # than continuing through the happy-path sequence.
        if path == "/auth/logout" and index not in {16, 17}:
            return _result(200, {"revoked": True})
        expected = [
            ("POST", "/platform/tenants"),
            ("POST", "/platform/billing/manual-comped-subscription"),
            ("POST", "/auth/token"),
            ("POST", "/api/cas-harness/audit/session"),
            ("POST", f"/api/cas-harness/audit/session/{AUDIT_ID}/run"),
            ("GET", f"/evidence/{TRACE_ID}"),
            ("POST", f"/evidence/{TRACE_ID}/verify"),
            ("POST", f"/evidence/{TRACE_ID}/shares"),
            ("GET", "/evidence/shared/shr_0123456789abcdef01234567"),
            ("POST", "/platform/tenants"),
            ("POST", "/auth/token"),
            ("GET", f"/api/cas-harness/audit/session/{AUDIT_ID}/status"),
            ("GET", f"/evidence/{TRACE_ID}"),
            ("DELETE", "/evidence/shares/shr_0123456789abcdef01234567"),
            ("GET", "/evidence/shared/shr_0123456789abcdef01234567"),
            ("POST", "/auth/logout"),
            ("POST", "/auth/logout"),
        ]
        assert (method, path) == expected[index - 1]
        assert base_url == collector_module.PRODUCTION_API_ORIGIN

        if index == 1:
            assert headers == {"X-Platform-Provisioning-Secret": PLATFORM_SECRET}
            assert payload is not None
            return _result(
                200,
                {
                    "provisioning_id": "provision-a",
                    "receipt_id": "receipt-a",
                    "completed_at": "2026-07-14T20:00:00Z",
                    "owner": {
                        "account_id": self.account_a,
                        "email_or_username": payload["email_or_username"],
                        "role": "owner",
                        "tenant_id": payload["tenant_id"],
                        "status": "active",
                        "created_at": "2026-07-14T20:00:00Z",
                        "updated_at": "2026-07-14T20:00:00Z",
                    },
                },
            )
        if index == 2:
            assert headers == {"X-Billing-Admin-Secret": BILLING_SECRET}
            return _result(
                200,
                {
                    "tenant_id": payload["tenant_id"],
                    "plan_id": "professional_live",
                    "status": "active",
                    "source": "manual_comped",
                    "expires_at": "2026-07-14T22:10:00Z",
                },
            )
        if index == 3:
            return _result(200, {"token": TOKEN_A, "expires_in_minutes": 60})
        if index == 4:
            assert headers == {"Authorization": f"Bearer {TOKEN_A}"}
            return _result(
                200,
                {
                    "audit_id": AUDIT_ID,
                    "status": "DRAFT",
                    "model_id": collector_module.MODEL_ID,
                },
            )
        if index == 5:
            assert timeout == 600.0
            return _result(
                200,
                {
                    "audit_id": AUDIT_ID,
                    "status": "COMPLETE",
                    "model_id": collector_module.MODEL_ID,
                    "audit_mode": "BALANCED",
                    "verdict": "FLAG_FOR_HUMAN_REVIEW",
                    "evidence_packet_trace_id": TRACE_ID,
                    "updated_at": "2026-07-14T20:00:00.800000+00:00",
                },
            )
        if index == 6:
            return _result(200, self.packet, content_type="application/json; charset=utf-8")
        if index == 7:
            return _result(
                200,
                {
                    "trace_id": TRACE_ID,
                    "overall": "all_match",
                    "checks": [
                        {
                            "artifact": "merged_packet_external_anchor",
                            "match": True,
                        }
                    ],
                },
            )
        if index == 8:
            return _result(
                201,
                {
                    "share_id": "shr_0123456789abcdef01234567",
                    "trace_id": TRACE_ID,
                    "created_at": "2026-07-14T20:01:00.900000Z",
                    "expires_at": "2026-07-15T20:10:00Z",
                    "revoked_at": None,
                    "status": "active",
                    "share_token": SHARE_TOKEN,
                    "anonymous_fetch_path": "/evidence/shared/shr_0123456789abcdef01234567",
                },
            )
        if index == 9:
            assert headers == {"X-Evidence-Share-Token": SHARE_TOKEN}
            assert "Authorization" not in headers
            return _result(200, self.packet)
        if index == 10:
            assert headers == {"X-Platform-Provisioning-Secret": PLATFORM_SECRET}
            return _result(
                200,
                {
                    "provisioning_id": "provision-b",
                    "receipt_id": "receipt-b",
                    "completed_at": "2026-07-14T20:02:00Z",
                    "owner": {
                        "account_id": self.account_b,
                        "email_or_username": payload["email_or_username"],
                        "role": "owner",
                        "tenant_id": payload["tenant_id"],
                        "status": "active",
                        "created_at": "2026-07-14T20:02:00Z",
                        "updated_at": "2026-07-14T20:02:00Z",
                    },
                },
            )
        if index == 11:
            return _result(200, {"token": TOKEN_B, "expires_in_minutes": 60})
        if index in {12, 13}:
            assert headers == {"Authorization": f"Bearer {TOKEN_B}"}
            return _result(self.foreign_status, {"detail": "not found"})
        if index == 14:
            assert headers == {"Authorization": f"Bearer {TOKEN_A}"}
            return _result(
                200,
                {
                    "share_id": "shr_0123456789abcdef01234567",
                    "trace_id": TRACE_ID,
                    "created_at": "2026-07-14T20:01:00Z",
                    "expires_at": "2026-07-15T20:10:00Z",
                    "revoked_at": "2026-07-14T20:10:00.100000Z",
                    "status": "revoked",
                },
            )
        if index == 15:
            assert headers == {"X-Evidence-Share-Token": SHARE_TOKEN}
            return _result(404, {"detail": "Shared Evidence Packet is unavailable."})
        if index == 16:
            assert headers == {"Authorization": f"Bearer {TOKEN_A}"}
            return _result(200, {"revoked": True})
        if index == 17:
            assert headers == {"Authorization": f"Bearer {TOKEN_B}"}
            return _result(200, {"revoked": True})
        raise AssertionError("unexpected call")


def _collect(*, anchored: bool = True, foreign_status: int = 404):
    transport = FakeJourneyTransport(anchored=anchored, foreign_status=foreign_status)
    collector = collector_module.JourneyCollector(
        base_url=collector_module.PRODUCTION_API_ORIGIN,
        platform_secret=PLATFORM_SECRET,
        billing_secret=BILLING_SECRET,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        transport=transport,
        clock=lambda: FIXED_NOW,
        nonce="0123456789abcdef01234567",
    )
    evidence, artifact = collector.collect()
    return transport, evidence, artifact


def test_collects_contract_valid_secret_safe_hosted_journey() -> None:
    transport, evidence, artifact = _collect()

    assert evidence["gate"] == "hosted_customer_journey"
    assert evidence["audit"]["terminal_status"] == "completed"
    assert evidence["audit"]["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert evidence["packet_download"]["worm_receipt_bound"] is True
    assert evidence["share"]["scope"] == "read_only"
    assert evidence["share"]["revoked_fetch_http_status"] == 404
    assert evidence["tenant_isolation"] == {
        "foreign_audit_http_status": 404,
        "foreign_packet_http_status": 404,
        "verified_at_utc": "2026-07-14T20:10:00Z",
    }
    assert artifact["schema_version"] == collector_module.SAFE_ARTIFACT_SCHEMA_VERSION
    assert evidence["artifact_sha256"] == collector_module._digest_bytes(
        collector_module._canonical_bytes(artifact)
    )

    serialized = json.dumps({"evidence": evidence, "artifact": artifact})
    provision_payloads = [
        call["payload"] for call in transport.calls if call["path"] == "/platform/tenants"
    ]
    forbidden = [
        PLATFORM_SECRET,
        BILLING_SECRET,
        TOKEN_A,
        TOKEN_B,
        SHARE_TOKEN,
        transport.account_a,
        transport.account_b,
    ]
    forbidden.extend(str(payload["tenant_id"]) for payload in provision_payloads)
    forbidden.extend(str(payload["email_or_username"]) for payload in provision_payloads)
    forbidden.extend(str(payload["api_credential"]) for payload in provision_payloads)
    assert all(secret not in serialized for secret in forbidden)

    context = verifier.ValidationContext(
        repo_root=REPO_ROOT,
        evidence_root=REPO_ROOT,
        verification_time=datetime(2026, 7, 14, 20, 20, tzinfo=UTC),
        generated_at=datetime(2026, 7, 14, 20, 20, tzinfo=UTC),
        expected_master_head=MASTER_SHA,
        expected_deploy_id=DEPLOY_ID,
        repository_commit=MASTER_SHA,
        live=True,
        trusted_issuers={},
        registry_sha256="b" * 64,
        authorities={
            "hosted_customer_journey": {
                "mode": "live_https",
                "subject_uri": collector_module.AUTHORITY_URI,
            }
        },
    )
    verifier._validate_hosted_customer(evidence, context)
    assert context.errors == []


def test_fails_closed_without_verified_worm_anchor() -> None:
    with pytest.raises(collector_module.JourneyFailure, match="Object Lock anchor"):
        _collect(anchored=False)


def test_fails_closed_when_foreign_tenant_can_enumerate() -> None:
    with pytest.raises(collector_module.JourneyFailure, match="exact 404s"):
        _collect(foreign_status=403)


def test_rejects_nonproduction_origin_and_missing_operator_credentials() -> None:
    with pytest.raises(collector_module.JourneyFailure, match="pinned public production"):
        collector_module.JourneyCollector(
            base_url="https://example.com",
            platform_secret=PLATFORM_SECRET,
            billing_secret=BILLING_SECRET,
            master_head_sha=MASTER_SHA,
            deploy_id=DEPLOY_ID,
        )
    with pytest.raises(collector_module.JourneyFailure, match="credentials"):
        collector_module.JourneyCollector(
            base_url=collector_module.PRODUCTION_API_ORIGIN,
            platform_secret="",
            billing_secret=BILLING_SECRET,
            master_head_sha=MASTER_SHA,
            deploy_id=DEPLOY_ID,
        )


def test_duplicate_json_keys_are_rejected() -> None:
    result = collector_module.HttpResult(
        status=200,
        headers={"content-type": "application/json"},
        body=b'{"status":"first","status":"second"}',
    )
    with pytest.raises(collector_module.JourneyFailure, match="duplicate JSON key"):
        collector_module._decode_object(result, "duplicate-test")
