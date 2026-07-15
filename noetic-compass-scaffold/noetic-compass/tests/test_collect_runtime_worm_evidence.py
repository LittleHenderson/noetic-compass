from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
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
    / "collect_runtime_worm_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("runtime_worm_collector", MODULE_PATH)
assert SPEC and SPEC.loader
collector_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = collector_module
SPEC.loader.exec_module(collector_module)

VERIFIER_PATH = REPO_ROOT / "scripts" / "verify_customer_production_acceptance.py"
VERIFIER_SPEC = importlib.util.spec_from_file_location(
    "runtime_worm_acceptance_verifier", VERIFIER_PATH
)
assert VERIFIER_SPEC and VERIFIER_SPEC.loader
verifier = importlib.util.module_from_spec(VERIFIER_SPEC)
sys.modules[VERIFIER_SPEC.name] = verifier
VERIFIER_SPEC.loader.exec_module(verifier)

from api.services import (  # noqa: E402
    customer_production_acceptance_authority as authority_service,
)


FIXED_NOW = datetime(2026, 7, 14, 20, 10, tzinfo=UTC)
MASTER_SHA = "a" * 40
DEPLOY_ID = "dep-d9ba0km7r5hc73e9ojkg"
DEPLOYED_AT = "2026-07-14T20:00:00Z"
TOKEN = "private-runtime-bearer-token"
RENDER_TOKEN = "private-render-api-key"
NONCE = "0123456789abcdef01234567"
AUDIT_ID = "cas-audit-0123456789abcdef"
TRACE_ID = "cas-live-0123456789abcdef-0123456789ab"
BUCKET = "private-provider-bucket-name"
OBJECT_KEY = f"packets/{TRACE_ID}.json"
VERSION_ID = "private-provider-version-id"
MANIFEST_SHA = "c" * 64
WORM_WRITTEN_AT = "2026-07-14T20:10:00Z"
EXPECTED_PROMPT = (
    "Customer-production runtime WORM evidence probe. Return one short factual "
    f"trace. probe_nonce={NONCE}"
)


def _body(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _result(status: int, value: Mapping[str, Any]) -> Any:
    return collector_module.HttpResult(
        status=status,
        headers={"content-type": "application/json; charset=utf-8"},
        body=_body(value),
    )


def _readiness(*, worm_status: str = "ok") -> dict[str, Any]:
    return {
        "status": "ok",
        "ready": True,
        "checks": {
            "api": {"status": "ok"},
            "cas_engine": {"status": "ok"},
            "database": {"status": "ok"},
            "live_worker": {
                "configured": True,
                "required": True,
                "status": "ok",
                "authority": "verified",
                "real_weights": True,
                "model_id": collector_module.MODEL_ID,
                "worker_version": "m2-real-pythia",
            },
            "s3_worm": {
                "configured": True,
                "required": True,
                "status": worm_status,
                "authority": "verified",
                "object_lock_mode": "GOVERNANCE",
                "retention_days": 31,
            },
        },
    }


def _worker(*, model_id: str | None = None) -> dict[str, Any]:
    return {
        "verdict": collector_module.REALMODE_VERDICT,
        "is_real_model": True,
        "fake_runtime_env": False,
        "model_loaded": True,
        "load_error": None,
        "manifest_is_real_model": True,
        "model_id": model_id or collector_module.MODEL_ID,
        "worker_version": "m2-real-pythia",
    }


def _retain_until(requested_at: str, retention_days: int) -> str:
    parsed = datetime.fromisoformat(requested_at.replace("Z", "+00:00"))
    return (parsed + timedelta(days=retention_days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _anchor(
    *, retention_days: int = 31, requested_at: str = WORM_WRITTEN_AT
) -> dict[str, Any]:
    retain_until = _retain_until(requested_at, retention_days)
    return {
        "status": "anchored",
        "mode": "s3",
        "anchor_uri": f"s3://{BUCKET}/{OBJECT_KEY}?versionId={VERSION_ID}",
        "bucket": BUCKET,
        "key": OBJECT_KEY,
        "version_id": VERSION_ID,
        "manifest_sha256": MANIFEST_SHA,
        "anchored_at": requested_at,
        "object_lock_mode": "GOVERNANCE",
        "retention_days": retention_days,
        "retention_requested_at": requested_at,
        "object_lock_retain_until": retain_until,
    }


def _receipt(
    *,
    retention_days: int = 31,
    observed_version_id: str = VERSION_ID,
    receipt_timestamp: str = "2026-07-14T20:10:00Z",
    requested_at: str = WORM_WRITTEN_AT,
) -> dict[str, Any]:
    retain_until = _retain_until(requested_at, retention_days)
    return {
        "schema_version": "cas_harness_object_lock_verification.v1",
        "verified": True,
        "verified_at": receipt_timestamp,
        "evaluated_at": receipt_timestamp,
        "retain_until_rule": "observed_not_before_requested",
        "expected": {
            "bucket": BUCKET,
            "key": OBJECT_KEY,
            "version_id": VERSION_ID,
            "content_sha256": MANIFEST_SHA,
            "mode": "GOVERNANCE",
            "retention_days": retention_days,
            "requested_at": requested_at,
            "retain_until": retain_until,
        },
        "observed": {
            "bucket": BUCKET,
            "key": OBJECT_KEY,
            "get_version_id": observed_version_id,
            "head_version_id": observed_version_id,
            "content_sha256": MANIFEST_SHA,
            "mode": "GOVERNANCE",
            "retain_until": retain_until,
            "reread_verified": True,
        },
        "failure_reasons": [],
        "issuer_attestation": "d" * 64,
    }


def _packet(
    *,
    retention_days: int = 31,
    prompt: str = EXPECTED_PROMPT,
    code_commit_sha: str = MASTER_SHA,
    requested_at: str = WORM_WRITTEN_AT,
) -> dict[str, Any]:
    return {
        "trace_id": TRACE_ID,
        "input": {
            "text": prompt,
            "audit_id": AUDIT_ID,
            "audit_mode": collector_module.AUDIT_MODE,
            "selected_modules": ["active_trace", "confidence_margin"],
        },
        "audit_scope": {
            "kind": "open_weight_live_trace",
            "verdict_disposition": "held_for_human_review",
        },
        "verification": {"accepted": None, "proof_chips": []},
        "model": {
            "model_key": collector_module.MODEL_ID,
            "runtime": "atlas_live_worker",
            "manifest": {"is_real_model": True},
        },
        "live_audit": {
            "audit_id": AUDIT_ID,
            "worker_endpoint": "ATLAS_LIVE_WORKER_URL",
            "request": {
                "prompt": prompt,
                "model_id": collector_module.MODEL_ID,
                "method_config": {
                    "audit_mode": collector_module.AUDIT_MODE,
                    "selected_modules": ["active_trace", "confidence_margin"],
                    "source": "cas_harness_audit_run",
                },
            },
            "events": [],
            "event_counts": {},
        },
        "provenance": {
            "method_label": "cas_harness_live_worker_v1",
            "code_commit_sha": code_commit_sha,
        },
        "hashes": {
            "external_anchor": _anchor(
                retention_days=retention_days, requested_at=requested_at
            )
        },
    }


def _verification(
    *,
    retention_days: int = 31,
    observed_version_id: str = VERSION_ID,
    receipt_timestamp: str = "2026-07-14T20:10:00Z",
    requested_at: str = WORM_WRITTEN_AT,
) -> dict[str, Any]:
    return {
        "trace_id": TRACE_ID,
        "overall": "all_match",
        "checks": [
            {
                "artifact": "merged_packet_external_anchor",
                "expected": MANIFEST_SHA,
                "actual": MANIFEST_SHA,
                "match": True,
                "object_lock_verification": _receipt(
                    retention_days=retention_days,
                    observed_version_id=observed_version_id,
                    receipt_timestamp=receipt_timestamp,
                    requested_at=requested_at,
                ),
            }
        ],
    }


class FakeTransport:
    def __init__(
        self,
        *,
        model_id: str | None = None,
        worm_status: str = "ok",
        audit_verdict: str = "FLAG_FOR_HUMAN_REVIEW",
        retention_days: int = 31,
        observed_version_id: str = VERSION_ID,
        render_commit: str = MASTER_SHA,
        packet_prompt: str = EXPECTED_PROMPT,
        packet_commit: str = MASTER_SHA,
        receipt_timestamp: str = "2026-07-14T20:10:00Z",
        worm_written_at: str = WORM_WRITTEN_AT,
        render_created_at: str = "2026-07-14T19:58:00Z",
        render_deployed_at: str = DEPLOYED_AT,
        render_final_changes: Mapping[str, Any] | None = None,
    ) -> None:
        self.model_id = model_id
        self.worm_status = worm_status
        self.audit_verdict = audit_verdict
        self.retention_days = retention_days
        self.observed_version_id = observed_version_id
        self.render_commit = render_commit
        self.packet_prompt = packet_prompt
        self.packet_commit = packet_commit
        self.receipt_timestamp = receipt_timestamp
        self.worm_written_at = worm_written_at
        self.render_created_at = render_created_at
        self.render_deployed_at = render_deployed_at
        self.render_final_changes = dict(render_final_changes or {})
        self.render_reads = 0
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        base_url: str,
        path: str,
        method: str,
        payload: Mapping[str, Any] | None,
        headers: Mapping[str, str],
        timeout: float,
    ) -> Any:
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
        if base_url == collector_module.RENDER_API_ORIGIN:
            self.render_reads += 1
            assert path == (
                f"/v1/services/{collector_module.PRODUCTION_SERVICE_ID}"
                f"/deploys/{DEPLOY_ID}"
            )
            assert method == "GET"
            assert payload is None
            assert headers == {"Authorization": f"Bearer {RENDER_TOKEN}"}
            render_deploy = {
                "id": DEPLOY_ID,
                "status": "live",
                "trigger": "new_commit",
                "createdAt": self.render_created_at,
                "finishedAt": self.render_deployed_at,
                "commit": {"id": self.render_commit},
            }
            if self.render_reads > 1:
                render_deploy.update(self.render_final_changes)
            return _result(200, render_deploy)
        assert base_url == collector_module.PRODUCTION_API_ORIGIN
        authenticated = path.startswith("/api/cas-harness/audit") or path.startswith(
            "/evidence/"
        )
        assert headers == (
            {"Authorization": f"Bearer {TOKEN}"} if authenticated else {}
        )
        if method == "GET" and path == "/health/ready":
            return _result(200, _readiness(worm_status=self.worm_status))
        if method == "GET" and path == "/atlas/live/health/realmode":
            return _result(200, _worker(model_id=self.model_id))
        if method == "POST" and path == "/api/cas-harness/audit/session":
            assert payload is not None
            assert payload["model_id"] == collector_module.MODEL_ID
            assert f"probe_nonce={NONCE}" in str(payload["prompt"])
            return _result(
                200,
                {
                    "audit_id": AUDIT_ID,
                    "status": "DRAFT",
                    "model_id": collector_module.MODEL_ID,
                    "audit_mode": collector_module.AUDIT_MODE,
                },
            )
        if method == "POST" and path == f"/api/cas-harness/audit/session/{AUDIT_ID}/run":
            assert timeout == 600.0
            return _result(
                200,
                {
                    "audit_id": AUDIT_ID,
                    "status": "COMPLETE",
                    "verdict": self.audit_verdict,
                    "model_id": collector_module.MODEL_ID,
                    "evidence_packet_trace_id": TRACE_ID,
                },
            )
        if method == "GET" and path == f"/evidence/{TRACE_ID}":
            return _result(
                200,
                _packet(
                    retention_days=self.retention_days,
                    prompt=self.packet_prompt,
                    code_commit_sha=self.packet_commit,
                    requested_at=self.worm_written_at,
                ),
            )
        if method == "POST" and path == f"/evidence/{TRACE_ID}/verify":
            return _result(
                200,
                _verification(
                    retention_days=self.retention_days,
                    observed_version_id=self.observed_version_id,
                    receipt_timestamp=self.receipt_timestamp,
                    requested_at=self.worm_written_at,
                ),
            )
        raise AssertionError(f"unexpected call: {method} {path}")


def _collector(
    transport: Any,
    *,
    deployed_at: str = DEPLOYED_AT,
    clock: Callable[[], datetime] = lambda: FIXED_NOW,
) -> Any:
    return collector_module.RuntimeWormCollector(
        base_url=collector_module.PRODUCTION_API_ORIGIN,
        bearer_token=TOKEN,
        render_api_key=RENDER_TOKEN,
        master_head_sha=MASTER_SHA,
        deploy_id=DEPLOY_ID,
        deployed_at_utc=deployed_at,
        transport=transport,
        clock=clock,
        nonce=NONCE,
    )


def test_collects_canonical_verifier_compatible_secret_safe_draft() -> None:
    transport = FakeTransport()
    evidence, artifact = _collector(transport).collect()

    canonical = collector_module.canonicalize_acceptance_evidence(
        "runtime_worm", evidence, now=FIXED_NOW
    )
    assert canonical == collector_module._canonical_bytes(evidence)
    context = verifier.ValidationContext(
        repo_root=REPO_ROOT,
        evidence_root=REPO_ROOT,
        verification_time=FIXED_NOW,
        generated_at=FIXED_NOW,
        expected_master_head=MASTER_SHA,
        expected_deploy_id=DEPLOY_ID,
        repository_commit=MASTER_SHA,
        live=True,
        trusted_issuers={},
        registry_sha256="0" * 64,
    )
    verifier._validate_runtime_worm(evidence, context)
    assert context.errors == []

    assert evidence["deployment"]["commit_sha"] == MASTER_SHA
    assert evidence["deployment"]["deploy_id"] == DEPLOY_ID
    assert evidence["deployment"]["deployed_at_utc"] == DEPLOYED_AT
    assert evidence["event_at_utc"] == "2026-07-14T20:10:00Z"
    assert evidence["worker"]["model_id"] == collector_module.MODEL_ID
    assert evidence["worm"]["write_verified"] is True
    assert evidence["worm"]["readback_verified"] is True
    assert evidence["worm"]["configured_retention_days"] == 31
    assert artifact["authority_published"] is False
    assert artifact["customer_production_status"] == "OPEN"
    assert artifact["schema_version"] == "cas_runtime_worm_source_receipt.v2"
    assert artifact["event_at_utc"] == evidence["event_at_utc"]
    assert (
        artifact["render_deploy_preflight_sha256"]
        == artifact["render_deploy_final_sha256"]
    )
    assert evidence["artifact_sha256"] == collector_module._digest_bytes(
        collector_module._canonical_bytes(artifact)
    )

    output = collector_module._canonical_bytes(evidence) + collector_module._canonical_bytes(
        artifact
    )
    for raw in (
        TOKEN,
        RENDER_TOKEN,
        AUDIT_ID,
        TRACE_ID,
        BUCKET,
        OBJECT_KEY,
        VERSION_ID,
    ):
        assert raw.encode("utf-8") not in output


def test_gate_schema_is_exactly_aligned_across_collector_authority_and_verifier() -> None:
    evidence, _ = _collector(FakeTransport()).collect()

    assert (
        collector_module.EVIDENCE_SCHEMA_VERSION
        == authority_service.EVIDENCE_SCHEMA_VERSION
        == verifier.EVIDENCE_SCHEMA_VERSION
        == "cas_harness_customer_production_gate_evidence.v3"
    )
    assert evidence["schema_version"] == authority_service.EVIDENCE_SCHEMA_VERSION


def test_sends_bearer_only_to_authenticated_audit_and_packet_routes() -> None:
    transport = FakeTransport()
    _collector(transport).collect()

    for call in transport.calls:
        if call["base_url"] == collector_module.RENDER_API_ORIGIN:
            assert call["headers"] == {
                "Authorization": f"Bearer {RENDER_TOKEN}"
            }
        elif call["path"] in {"/health/ready", "/atlas/live/health/realmode"}:
            assert call["headers"] == {}
        else:
            assert call["headers"] == {"Authorization": f"Bearer {TOKEN}"}


def test_rejects_accept_verdict_instead_of_promoting_it() -> None:
    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="must remain FLAG_FOR_HUMAN_REVIEW",
    ):
        _collector(FakeTransport(audit_verdict="ACCEPT")).collect()


def test_rejects_replayed_packet_that_does_not_echo_probe_nonce() -> None:
    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="input.text.*live_audit.request.prompt",
    ):
        _collector(
            FakeTransport(packet_prompt="older runtime WORM evidence probe")
        ).collect()


def test_rejects_packet_produced_by_a_different_code_commit() -> None:
    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="provenance.code_commit_sha",
    ):
        _collector(FakeTransport(packet_commit="b" * 40)).collect()


def test_rejects_wrong_live_model_before_creating_audit() -> None:
    transport = FakeTransport(model_id="EleutherAI/pythia-1b")
    with pytest.raises(collector_module.RuntimeWormFailure, match="model_id"):
        _collector(transport).collect()

    assert [call["path"] for call in transport.calls] == [
        f"/v1/services/{collector_module.PRODUCTION_SERVICE_ID}/deploys/{DEPLOY_ID}",
        "/health/ready",
        "/atlas/live/health/realmode",
    ]


def test_rejects_missing_null_worker_field_instead_of_fabricating_it() -> None:
    payload = _worker()
    payload.pop("load_error")

    with pytest.raises(collector_module.RuntimeWormFailure, match="load_error"):
        collector_module.RuntimeWormCollector._assert_worker(payload)


def test_rejects_unverified_readiness_worm_before_creating_audit() -> None:
    transport = FakeTransport(worm_status="error")
    with pytest.raises(collector_module.RuntimeWormFailure, match="S3 WORM readback"):
        _collector(transport).collect()

    assert [call["path"] for call in transport.calls] == [
        f"/v1/services/{collector_module.PRODUCTION_SERVICE_ID}/deploys/{DEPLOY_ID}",
        "/health/ready",
    ]


def test_rejects_render_commit_mismatch_before_runtime_probe_or_worm_write() -> None:
    transport = FakeTransport(render_commit="b" * 40)
    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="exact deployment is not live at the pinned commit",
    ):
        _collector(transport).collect()

    assert len(transport.calls) == 1
    assert transport.calls[0]["base_url"] == collector_module.RENDER_API_ORIGIN


def test_rejects_cross_wired_exact_s3_version_readback() -> None:
    with pytest.raises(collector_module.RuntimeWormFailure, match="cross-wired"):
        _collector(
            FakeTransport(observed_version_id="different-provider-version")
        ).collect()


def test_rejects_configured_retention_below_31_days() -> None:
    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="configured retention_days must be >= 31",
    ):
        _collector(FakeTransport(retention_days=30)).collect()


def test_accepts_bounded_positive_receipt_issuer_clock_skew() -> None:
    evidence, _artifact = _collector(
        FakeTransport(receipt_timestamp="2026-07-14T20:10:05Z")
    ).collect()

    assert evidence["worm"]["verified_at_utc"] == "2026-07-14T20:10:05Z"


def test_rejects_receipt_issuer_clock_skew_beyond_bound() -> None:
    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="structured Object Lock receipt timestamps are invalid",
    ):
        _collector(
            FakeTransport(receipt_timestamp="2026-07-14T20:10:06Z")
        ).collect()


def test_accepts_bounded_worm_provider_clock_skew_after_worker_check() -> None:
    evidence, _artifact = _collector(
        FakeTransport(worm_written_at="2026-07-14T20:09:55Z")
    ).collect()

    assert evidence["event_at_utc"] == "2026-07-14T20:09:55Z"
    assert evidence["worm"]["written_at_utc"] == "2026-07-14T20:09:55Z"


def test_rejects_worm_write_that_predates_worker_beyond_clock_skew() -> None:
    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="WORM write predates worker verification beyond allowed clock skew",
    ):
        _collector(
            FakeTransport(worm_written_at="2026-07-14T20:09:54Z")
        ).collect()


def test_rejects_local_clock_rollback_between_readiness_and_worker() -> None:
    worker_time = datetime(2026, 7, 14, 20, 9, 59, tzinfo=UTC)
    clock_values = iter(
        (FIXED_NOW, FIXED_NOW, FIXED_NOW, FIXED_NOW, worker_time)
    )
    transport = FakeTransport()

    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="worker verification precedes readiness verification",
    ):
        _collector(transport, clock=lambda: next(clock_values)).collect()

    assert [call["path"] for call in transport.calls] == [
        f"/v1/services/{collector_module.PRODUCTION_SERVICE_ID}/deploys/{DEPLOY_ID}",
        "/health/ready",
        "/atlas/live/health/realmode",
    ]


def test_authority_rejects_worker_proof_before_readiness_proof() -> None:
    evidence, _artifact = _collector(FakeTransport()).collect()
    evidence["event_at_utc"] = "2026-07-14T20:09:59Z"
    evidence["worker"]["verified_at_utc"] = "2026-07-14T20:09:59Z"

    with pytest.raises(
        collector_module.AcceptanceAuthorityInvalid,
        match="worker.verified_at_utc precedes readiness.verified_at_utc",
    ):
        collector_module.canonicalize_acceptance_evidence(
            "runtime_worm", evidence, now=FIXED_NOW
        )


def test_authority_rejects_worm_write_before_worker_beyond_skew() -> None:
    evidence, _artifact = _collector(FakeTransport()).collect()
    evidence["event_at_utc"] = "2026-07-14T20:09:54Z"
    evidence["worm"]["written_at_utc"] = "2026-07-14T20:09:54Z"

    with pytest.raises(
        collector_module.AcceptanceAuthorityInvalid,
        match="worm.written_at_utc predates worker verification beyond allowed clock skew",
    ):
        collector_module.canonicalize_acceptance_evidence(
            "runtime_worm", evidence, now=FIXED_NOW
        )


def test_accepts_older_exact_deployment_with_fresh_runtime_and_worm_proof() -> None:
    deployed_at = "2026-07-14T18:00:00Z"
    transport = FakeTransport(
        render_created_at="2026-07-14T17:58:00Z",
        render_deployed_at=deployed_at,
    )

    evidence, artifact = _collector(transport, deployed_at=deployed_at).collect()

    assert evidence["deployment"]["deployed_at_utc"] == deployed_at
    assert evidence["event_at_utc"] == "2026-07-14T20:10:00Z"
    assert artifact["deployed_at_utc"] == deployed_at
    assert artifact["event_at_utc"] == evidence["event_at_utc"]
    assert transport.render_reads == 2


def test_rejects_future_deployment_before_network_or_worm_write() -> None:
    transport = FakeTransport()
    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="deployment timestamp is in the future",
    ):
        _collector(transport, deployed_at="2026-07-14T20:10:01Z")
    assert transport.calls == []


def test_rejects_any_render_deployment_record_drift_during_collection() -> None:
    transport = FakeTransport(render_final_changes={"unexpected": "drift"})

    with pytest.raises(
        collector_module.RuntimeWormFailure,
        match="deployment record changed during collection",
    ):
        _collector(transport).collect()

    assert transport.render_reads == 2


def test_output_pair_tamper_fails_before_persistence() -> None:
    evidence, artifact = _collector(FakeTransport()).collect()
    artifact["version_id_sha256"] = "f" * 64

    with pytest.raises(collector_module.RuntimeWormFailure, match="diverged"):
        collector_module._validate_output_pair(evidence, artifact, now=FIXED_NOW)
