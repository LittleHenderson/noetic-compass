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
SHARE_TOKEN = "share_token_private_value_0123456789abcdef01234567"
TRACE_ID = "cas-live-0123456789abcdef-0123456789ab"
AUDIT_ID = "cas-audit-0123456789abcdef"
RUNTIME_ENV = {
    "RENDER_SERVICE_ID": collector_module.PRODUCTION_SERVICE_ID,
    "RENDER_GIT_COMMIT": MASTER_SHA,
}
ANCHOR_MANIFEST_SHA = "c" * 64
ANCHOR_BUCKET = "acceptance-evidence-bucket"
ANCHOR_KEY = f"packets/{TRACE_ID}.json"
ANCHOR_VERSION = "version-0123456789"


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


def _empty_result(status: int):
    return collector_module.HttpResult(status=status, headers={}, body=b"")


def _packet(*, anchored: bool = True) -> dict[str, Any]:
    return {
        "trace_id": TRACE_ID,
        "verdict": "FLAG_FOR_HUMAN_REVIEW",
        "input": {"audit_id": AUDIT_ID, "audit_mode": "BALANCED"},
        "model": {
            "model_key": collector_module.MODEL_ID,
            "runtime": "atlas_live_worker",
        },
        "provenance": {"method_label": "cas_harness_live_worker_v1"},
        "hashes": {
            "external_anchor": {
                "status": "anchored" if anchored else "failed",
                "mode": "s3",
                "anchor_uri": (
                    f"s3://{ANCHOR_BUCKET}/{ANCHOR_KEY}?versionId={ANCHOR_VERSION}"
                ),
                "bucket": ANCHOR_BUCKET,
                "key": ANCHOR_KEY,
                "version_id": ANCHOR_VERSION,
                "manifest_sha256": ANCHOR_MANIFEST_SHA,
                "anchored_at": "2026-07-14T20:00:00Z",
                "object_lock_mode": "GOVERNANCE",
                "retention_days": 31,
                "retention_requested_at": "2026-07-14T20:00:00Z",
                "object_lock_retain_until": "2026-08-14T20:00:00Z",
            }
        },
        "live_audit": {
            "audit_id": AUDIT_ID,
            "model_id": collector_module.MODEL_ID,
        },
    }


def _object_lock_receipt() -> dict[str, Any]:
    return {
        "schema_version": collector_module.OBJECT_LOCK_VERIFICATION_SCHEMA,
        "verified": True,
        "verified_at": "2026-07-14T20:05:00Z",
        "evaluated_at": "2026-07-14T20:05:00Z",
        "retain_until_rule": collector_module.OBJECT_LOCK_RETAIN_UNTIL_RULE,
        "expected": {
            "bucket": ANCHOR_BUCKET,
            "key": ANCHOR_KEY,
            "version_id": ANCHOR_VERSION,
            "content_sha256": ANCHOR_MANIFEST_SHA,
            "mode": "GOVERNANCE",
            "retention_days": 31,
            "requested_at": "2026-07-14T20:00:00Z",
            "retain_until": "2026-08-14T20:00:00Z",
        },
        "observed": {
            "bucket": ANCHOR_BUCKET,
            "key": ANCHOR_KEY,
            "get_version_id": ANCHOR_VERSION,
            "head_version_id": ANCHOR_VERSION,
            "content_sha256": ANCHOR_MANIFEST_SHA,
            "mode": "GOVERNANCE",
            "retain_until": "2026-08-14T20:00:00Z",
            "reread_verified": True,
        },
        "failure_reasons": [],
        "issuer_attestation": "d" * 64,
    }


def _verification() -> dict[str, Any]:
    return {
        "trace_id": TRACE_ID,
        "overall": "all_match",
        "checks": [
            {
                "artifact": "merged_packet_external_anchor",
                "expected": ANCHOR_MANIFEST_SHA,
                "actual": ANCHOR_MANIFEST_SHA,
                "match": True,
                "object_lock_verification": _object_lock_receipt(),
            }
        ],
    }


class FakeJourneyTransport:
    def __init__(
        self,
        *,
        anchored: bool = True,
        foreign_status: int = 404,
        run_transient_once: bool = False,
        revoked_at: str = "2026-07-14T20:10:00Z",
        revoke_status: int = 200,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self.packet = _packet(anchored=anchored)
        self.foreign_status = foreign_status
        self.account_a = "acct-" + "a" * 32
        self.account_b = "acct-" + "b" * 32
        self.provision_count = 0
        self.login_count = 0
        self.revoked = False
        self.run_transient_once = run_transient_once
        self.run_attempts = 0
        self.revoked_at = revoked_at
        self.revoke_status = revoke_status

    @staticmethod
    def _share_metadata(*, revoked: bool, revoked_at: str) -> dict[str, Any]:
        return {
            "share_id": "shr_0123456789abcdef01234567",
            "trace_id": TRACE_ID,
            "created_at": "2026-07-14T20:10:00Z",
            "expires_at": "2026-07-14T20:25:00Z",
            "revoked_at": revoked_at if revoked else None,
            "status": "revoked" if revoked else "active",
        }

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
        assert base_url == collector_module.PRODUCTION_API_ORIGIN

        if method == "POST" and path == "/platform/tenants":
            assert headers == {"X-Platform-Provisioning-Secret": PLATFORM_SECRET}
            assert payload is not None
            self.provision_count += 1
            suffix = "a" if self.provision_count == 1 else "b"
            account_id = self.account_a if suffix == "a" else self.account_b
            return _result(
                200,
                {
                    "provisioning_id": "tenantprov-" + suffix * 32,
                    "receipt_id": "tenantprovrct-" + suffix * 32,
                    "completed_at": f"2026-07-14T20:0{self.provision_count}:00Z",
                    "owner": {
                        "account_id": account_id,
                        "email_or_username": payload["email_or_username"],
                        "role": "owner",
                        "tenant_id": payload["tenant_id"],
                        "status": "active",
                        "created_at": "2026-07-14T20:00:00Z",
                        "updated_at": "2026-07-14T20:00:00Z",
                    },
                },
            )
        if method == "POST" and path == "/platform/billing/manual-comped-subscription":
            assert headers == {"X-Billing-Admin-Secret": BILLING_SECRET}
            return _result(
                200,
                {
                    "tenant_id": payload["tenant_id"],
                    "plan_id": "beta_comped",
                    "status": "active",
                    "source": "manual_comped",
                    "expires_at": "2026-07-14T22:10:00Z",
                },
            )
        if method == "POST" and path == "/auth/token":
            self.login_count += 1
            token = TOKEN_A if self.login_count == 1 else TOKEN_B
            return _result(200, {"token": token, "expires_in_minutes": 60})
        if method == "POST" and path == "/api/cas-harness/audit/session":
            assert headers == {"Authorization": f"Bearer {TOKEN_A}"}
            return _result(
                200,
                {
                    "audit_id": AUDIT_ID,
                    "status": "DRAFT",
                    "model_id": collector_module.MODEL_ID,
                    "audit_mode": "BALANCED",
                    "selected_modules": ["active_trace", "confidence_margin"],
                },
            )
        if method == "POST" and path == f"/api/cas-harness/audit/session/{AUDIT_ID}/run":
            assert timeout == 600.0
            self.run_attempts += 1
            if self.run_transient_once and self.run_attempts == 1:
                return _result(503, {"detail": "transient proxy ambiguity"})
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
        if method == "GET" and path == f"/evidence/{TRACE_ID}":
            if headers == {"Authorization": f"Bearer {TOKEN_B}"}:
                return _result(self.foreign_status, {"detail": "not found"})
            return _result(200, self.packet, content_type="application/json; charset=utf-8")
        if method == "POST" and path == f"/evidence/{TRACE_ID}/verify":
            return _result(200, _verification())
        if method == "POST" and path == f"/evidence/{TRACE_ID}/shares":
            if headers == {"Authorization": f"Bearer {TOKEN_B}"}:
                return _result(self.foreign_status, {"detail": "not found"})
            assert payload == {"expires_at": "2026-07-14T20:25:00+00:00"}
            return _result(
                201,
                {
                    **self._share_metadata(revoked=False, revoked_at=self.revoked_at),
                    "share_token": SHARE_TOKEN,
                    "anonymous_fetch_path": "/evidence/shared/shr_0123456789abcdef01234567",
                },
            )
        if method == "GET" and path == "/evidence/shared/shr_0123456789abcdef01234567":
            assert headers == {"X-Evidence-Share-Token": SHARE_TOKEN}
            if self.revoked:
                return _result(404, {"detail": "Shared Evidence Packet is unavailable."})
            return _result(200, self.packet)
        if path == "/evidence/shares/shr_0123456789abcdef01234567":
            if headers == {"Authorization": f"Bearer {TOKEN_B}"}:
                return _result(self.foreign_status, {"detail": "not found"})
            if "Authorization" not in headers:
                return _result(401, {"detail": "missing auth"})
            assert headers == {"Authorization": f"Bearer {TOKEN_A}"}
            if method == "DELETE":
                self.revoked = True
                if self.revoke_status == 204:
                    return _empty_result(204)
            return _result(
                200,
                self._share_metadata(revoked=self.revoked, revoked_at=self.revoked_at),
            )
        if method == "GET" and path == f"/api/cas-harness/audit/session/{AUDIT_ID}/status":
            assert headers == {"Authorization": f"Bearer {TOKEN_B}"}
            return _result(self.foreign_status, {"detail": "not found"})
        if method == "POST" and path == "/auth/logout":
            return _result(200, {"revoked": True})
        raise AssertionError(f"unexpected call: {method} {path}")


def _collect(
    *,
    anchored: bool = True,
    foreign_status: int = 404,
    run_transient_once: bool = False,
    revoked_at: str = "2026-07-14T20:10:00Z",
    revoke_status: int = 200,
):
    transport = FakeJourneyTransport(
        anchored=anchored,
        foreign_status=foreign_status,
        run_transient_once=run_transient_once,
        revoked_at=revoked_at,
        revoke_status=revoke_status,
    )
    collector = collector_module.JourneyCollector(
        base_url=collector_module.PRODUCTION_API_ORIGIN,
        platform_secret=PLATFORM_SECRET,
        billing_secret=BILLING_SECRET,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        transport=transport,
        clock=lambda: FIXED_NOW,
        nonce="0123456789abcdef01234567",
        runtime_environment=RUNTIME_ENV,
    )
    evidence, artifact = collector.collect()
    return transport, evidence, artifact


def _bound_collector() -> Any:
    return collector_module.JourneyCollector(
        base_url=collector_module.PRODUCTION_API_ORIGIN,
        platform_secret=PLATFORM_SECRET,
        billing_secret=BILLING_SECRET,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        transport=FakeJourneyTransport(),
        clock=lambda: FIXED_NOW,
        nonce="0123456789abcdef01234567",
        runtime_environment=RUNTIME_ENV,
    )


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
    assert artifact["packet_canonical_sha256"] == artifact[
        "share_packet_canonical_sha256"
    ]
    assert artifact["share_token_write_http_status"] == 401
    assert artifact["foreign_share_create_http_status"] == 404
    assert artifact["foreign_share_metadata_http_status"] == 404
    assert artifact["foreign_share_revoke_http_status"] == 404
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
    transport = FakeJourneyTransport(foreign_status=403)
    collector = collector_module.JourneyCollector(
        base_url=collector_module.PRODUCTION_API_ORIGIN,
        platform_secret=PLATFORM_SECRET,
        billing_secret=BILLING_SECRET,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        transport=transport,
        clock=lambda: FIXED_NOW,
        nonce="0123456789abcdef01234567",
        runtime_environment=RUNTIME_ENV,
    )
    with pytest.raises(collector_module.JourneyFailure, match="exact 404s"):
        collector.collect()
    assert transport.revoked is True
    assert sum(call["path"] == "/auth/logout" for call in transport.calls) == 2


def test_rejects_nonproduction_origin_and_missing_operator_credentials() -> None:
    with pytest.raises(collector_module.JourneyFailure, match="pinned public production"):
        collector_module.JourneyCollector(
            base_url="https://example.com",
            platform_secret=PLATFORM_SECRET,
            billing_secret=BILLING_SECRET,
            master_head_sha=MASTER_SHA,
            deploy_id=DEPLOY_ID,
            runtime_environment=RUNTIME_ENV,
        )
    with pytest.raises(collector_module.JourneyFailure, match="credentials"):
        collector_module.JourneyCollector(
            base_url=collector_module.PRODUCTION_API_ORIGIN,
            platform_secret="",
            billing_secret=BILLING_SECRET,
            master_head_sha=MASTER_SHA,
            deploy_id=DEPLOY_ID,
            runtime_environment=RUNTIME_ENV,
        )


def test_duplicate_json_keys_are_rejected() -> None:
    result = collector_module.HttpResult(
        status=200,
        headers={"content-type": "application/json"},
        body=b'{"status":"first","status":"second"}',
    )
    with pytest.raises(collector_module.JourneyFailure, match="duplicate JSON key"):
        collector_module._decode_object(result, "duplicate-test")


@pytest.mark.parametrize("constant", [b"NaN", b"Infinity", b"-Infinity"])
def test_nonfinite_json_numbers_are_rejected(constant: bytes) -> None:
    result = collector_module.HttpResult(
        status=200,
        headers={"content-type": "application/json"},
        body=b'{"value":' + constant + b"}",
    )
    with pytest.raises(collector_module.JourneyFailure, match="non-finite"):
        collector_module._decode_object(result, "number-test")


def test_oversized_json_and_query_paths_are_rejected() -> None:
    result = collector_module.HttpResult(
        status=200,
        headers={"content-type": "application/json"},
        body=b" " * (collector_module.MAX_RESPONSE_BYTES + 1),
    )
    with pytest.raises(collector_module.JourneyFailure, match="bounded size"):
        collector_module._decode_object(result, "size-test")
    with pytest.raises(collector_module.JourneyFailure, match="query-free"):
        _bound_collector()._call("/health?target=elsewhere")


def test_redirects_are_never_followed() -> None:
    handler = collector_module._NoRedirect()
    request = collector_module.Request(collector_module.PRODUCTION_API_ORIGIN + "/health")
    assert (
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://attacker.invalid/collect",
        )
        is None
    )


def test_structured_worm_receipt_cross_wire_is_rejected() -> None:
    verification = _verification()
    verification["checks"][0]["object_lock_verification"]["observed"][
        "head_version_id"
    ] = "different-version"
    with pytest.raises(collector_module.JourneyFailure, match="cross-wired"):
        _bound_collector()._assert_worm(
            _packet(), verification, trace_id=TRACE_ID
        )


def test_timestamp_order_and_runtime_identity_fail_closed() -> None:
    with pytest.raises(collector_module.JourneyFailure, match="revocation time"):
        _collect(revoked_at="2026-07-14T19:59:00Z")
    with pytest.raises(collector_module.JourneyFailure, match="pinned production service"):
        collector_module.JourneyCollector(
            base_url=collector_module.PRODUCTION_API_ORIGIN,
            platform_secret=PLATFORM_SECRET,
            billing_secret=BILLING_SECRET,
            master_head_sha=MASTER_SHA,
            deploy_id=DEPLOY_ID,
            runtime_environment={
                "RENDER_SERVICE_ID": "srv-wrong",
                "RENDER_GIT_COMMIT": MASTER_SHA,
            },
        )


def test_idempotent_run_retry_204_revoke_and_source_receipt_binding() -> None:
    transport, evidence, artifact = _collect(
        run_transient_once=True, revoke_status=204
    )
    assert transport.run_attempts == 2
    assert evidence["share"]["revoke_http_status"] == 204
    tampered = dict(artifact)
    tampered["packet_sha256"] = "f" * 64
    with pytest.raises(collector_module.JourneyFailure, match="diverged"):
        collector_module._validate_output_pair(evidence, tampered)


def test_production_image_contains_collector() -> None:
    dockerfile = (MODULE_PATH.parent.parent / "Dockerfile.api").read_text(encoding="utf-8")
    assert (
        "COPY scripts/collect_hosted_customer_journey_evidence.py "
        "scripts/collect_hosted_customer_journey_evidence.py"
    ) in dockerfile
