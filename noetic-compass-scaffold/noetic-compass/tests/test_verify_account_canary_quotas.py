from __future__ import annotations

import re

import httpx
import pytest

import scripts.verify_account_canary_quotas as quota_proof
from api.routes.cas_harness_audit import (
    HOSTED_OPEN_WEIGHT_MODEL_IDS,
    _should_run_api_endpoint,
    _should_run_hosted_open_weight,
)
from scripts.verify_account_canary_quotas import (
    ACCOUNT_CANARY_DATABASE_HOST,
    ACCOUNT_CANARY_DATABASE_NAME,
    ACCOUNT_CANARY_DATABASE_USER,
    ACCOUNT_CANARY_GIT_BRANCH,
    ACCOUNT_CANARY_MODEL_ID,
    ACCOUNT_CANARY_OBJECT_LOCK_MODE,
    ACCOUNT_CANARY_OBJECT_LOCK_RETENTION_DAYS,
    ACCOUNT_CANARY_OBJECT_STORE_PREFIX,
    ACCOUNT_CANARY_OBJECT_STORE_REGION,
    ACCOUNT_CANARY_QUOTA_LIMIT,
    ACCOUNT_CANARY_SERVICE_ID,
    ProofFailure,
    _credential,
    _expect_quota_429,
    _expect_status,
    _proof_client,
    _redact,
    _response_body,
    _require_canary_database_url,
    _require_canary_environment,
    _safe_loopback_url,
    main,
)


_AUDIT_A1 = "cas-audit-1111111111111111"
_AUDIT_A2 = "cas-audit-2222222222222222"
_AUDIT_A_OVERFLOW = "cas-audit-3333333333333333"
_AUDIT_B1 = "cas-audit-4444444444444444"
_AUDIT_B2 = "cas-audit-5555555555555555"
_AUDIT_B_OVERFLOW = "cas-audit-6666666666666666"


def _valid_marker_payload() -> dict[str, object]:
    return {
        "schema_version": quota_proof.PROOF_SCHEMA_VERSION,
        "phase": "awaiting_restart",
        "pre_host_fingerprint": "pre-instance",
        "expected_limit": ACCOUNT_CANARY_QUOTA_LIMIT,
        "execution_period": quota_proof.current_monthly_period_key(),
        "tenant_a_audit_ids": [_AUDIT_A1, _AUDIT_A2],
        "tenant_a_overflow_audit_id": _AUDIT_A_OVERFLOW,
        "tenant_b_first_audit_id": _AUDIT_B1,
    }


def test_derived_proof_credentials_are_stable_scoped_and_never_echo_secret() -> None:
    platform_secret = "platform-secret-" + ("x" * 48)
    first = _credential(platform_secret, "proof-123", "a")

    assert first == _credential(platform_secret, "proof-123", "a")
    assert first != _credential(platform_secret, "proof-123", "b")
    assert first != _credential(platform_secret, "proof-456", "a")
    assert re.fullmatch(r"casak_[A-Za-z0-9_-]{43}", first)
    assert platform_secret not in first


def test_marker_audit_ids_accept_exact_v1_shape() -> None:
    allowed_a, overflow_a, first_b = quota_proof._marker_audit_ids(
        _valid_marker_payload(), expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT
    )

    assert allowed_a == [_AUDIT_A1, _AUDIT_A2]
    assert overflow_a == _AUDIT_A_OVERFLOW
    assert first_b == _AUDIT_B1


@pytest.mark.parametrize(
    "updates",
    (
        {"schema_version": 2},
        {"tenant_a_audit_ids": [_AUDIT_A1]},
        {"tenant_a_audit_ids": "not-a-list"},
        {"tenant_a_audit_ids": [_AUDIT_A1, 7]},
        {"tenant_a_audit_ids": [_AUDIT_A1, "../../unsafe"]},
        {"tenant_a_overflow_audit_id": "not-a-safe-id"},
        {"tenant_b_first_audit_id": None},
        {"tenant_a_audit_ids": [_AUDIT_A1, _AUDIT_A1]},
        {"tenant_a_overflow_audit_id": _AUDIT_A1},
        {"tenant_b_first_audit_id": _AUDIT_A2},
    ),
)
def test_marker_audit_ids_reject_malformed_or_overlapping_references(
    updates: dict[str, object],
) -> None:
    payload = _valid_marker_payload()
    payload.update(updates)

    with pytest.raises(ProofFailure) as exc_info:
        quota_proof._marker_audit_ids(
            payload, expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT
        )

    message = str(exc_info.value)
    assert "../../unsafe" not in message
    assert "not-a-safe-id" not in message


def test_load_durable_session_accepts_public_projection_without_prompt_text() -> None:
    prompt = quota_proof._prompt("q20260713a1", "a", 1)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(f"/{_AUDIT_A1}/status")
        return httpx.Response(
            200,
            json={
                "audit_id": _AUDIT_A1,
                "prompt_summary": prompt,
                "model_id": ACCOUNT_CANARY_MODEL_ID,
                "audit_mode": "BALANCED",
                "selected_modules": ["active_trace"],
                "endpoint_url": None,
                "provider": None,
            },
        )

    with httpx.Client(
        base_url="http://127.0.0.1:10000", transport=httpx.MockTransport(handler)
    ) as client:
        observed = quota_proof._load_durable_session(
            client,
            token="safe-test-token",
            audit_id=_AUDIT_A1,
            expected_prompt=prompt,
            label="tenant A allowed audit 1",
        )

    assert observed["audit_id"] == _AUDIT_A1
    assert "prompt_text" not in observed


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("audit_id", _AUDIT_A2),
        ("prompt_summary", "untrusted-response-value"),
        ("model_id", "untrusted-response-value"),
        ("audit_mode", "FAST"),
        ("selected_modules", ["untrusted-response-value"]),
        ("endpoint_url", "https://untrusted.example.invalid"),
        ("provider", "untrusted-response-value"),
    ),
)
def test_load_durable_session_rejects_contract_drift_without_echoing_body(
    field: str, value: object
) -> None:
    prompt = quota_proof._prompt("q20260713a1", "a", 1)
    body: dict[str, object] = {
        "audit_id": _AUDIT_A1,
        "prompt_summary": prompt,
        "model_id": ACCOUNT_CANARY_MODEL_ID,
        "audit_mode": "BALANCED",
        "selected_modules": ["active_trace"],
        "endpoint_url": None,
        "provider": None,
    }
    body[field] = value

    with httpx.Client(
        base_url="http://127.0.0.1:10000",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
    ) as client:
        with pytest.raises(ProofFailure) as exc_info:
            quota_proof._load_durable_session(
                client,
                token="safe-test-token",
                audit_id=_AUDIT_A1,
                expected_prompt=prompt,
                label="tenant A allowed audit 1",
            )

    assert "untrusted-response-value" not in str(exc_info.value)


def test_ensure_session_reuses_public_prompt_summary_without_posting() -> None:
    prompt = quota_proof._prompt("q20260713a1", "a", 1)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(
            200,
            json={"sessions": [{"audit_id": _AUDIT_A1, "prompt_summary": prompt}]},
        )

    with httpx.Client(
        base_url="http://127.0.0.1:10000", transport=httpx.MockTransport(handler)
    ) as client:
        observed = quota_proof._ensure_session(
            client,
            token="safe-test-token",
            proof_id="q20260713a1",
            lane="a",
            ordinal=1,
        )

    assert observed["audit_id"] == _AUDIT_A1


def test_run_post_uses_sealed_marker_ids_and_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker_payload = _valid_marker_payload()

    class FakeStore:
        def get(self, tenant_id: str, kind: str, record_id: str):
            return type("Marker", (), {"payload": marker_payload})()

    session_contracts = {
        _AUDIT_A1: quota_proof._prompt("q20260713a1", "a", 1),
        _AUDIT_A2: quota_proof._prompt("q20260713a1", "a", 2),
        _AUDIT_A_OVERFLOW: quota_proof._prompt("q20260713a1", "a", 3),
        _AUDIT_B1: quota_proof._prompt("q20260713a1", "b", 1),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        audit_id = request.url.path.rsplit("/", 2)[-2]
        return httpx.Response(
            200,
            json={
                "audit_id": audit_id,
                "prompt_summary": session_contracts[audit_id],
                "model_id": ACCOUNT_CANARY_MODEL_ID,
                "audit_mode": "BALANCED",
                "selected_modules": ["active_trace"],
                "endpoint_url": None,
                "provider": None,
            },
        )

    monkeypatch.setattr(quota_proof, "_provision", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        quota_proof,
        "_login",
        lambda client, *, proof_id, lane, credential: f"token-{lane}",
    )

    def fake_run(client, token: str, audit_id: str) -> httpx.Response:
        if audit_id in {_AUDIT_A_OVERFLOW, _AUDIT_B_OVERFLOW}:
            return httpx.Response(
                429,
                json={
                    "detail": {
                        "code": "audit_quota_exceeded",
                        "limit": ACCOUNT_CANARY_QUOTA_LIMIT,
                        "count": ACCOUNT_CANARY_QUOTA_LIMIT,
                        "period": quota_proof.current_monthly_period_key(),
                    }
                },
            )
        return httpx.Response(200, json={})

    monkeypatch.setattr(quota_proof, "_run", fake_run)
    monkeypatch.setattr(
        quota_proof,
        "_ensure_session",
        lambda client, *, token, proof_id, lane, ordinal: {
            "audit_id": _AUDIT_B2 if ordinal == 2 else _AUDIT_B_OVERFLOW
        },
    )
    monkeypatch.setattr(
        quota_proof, "_assert_cross_tenant_404", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        quota_proof,
        "get_usage",
        lambda store, *, tenant_id, period_key: ACCOUNT_CANARY_QUOTA_LIMIT,
    )
    monkeypatch.setattr(
        quota_proof,
        "_assert_boundary_survived",
        lambda *args, **kwargs: {"status": "present"},
    )
    rotations: list[str] = []
    monkeypatch.setattr(
        quota_proof,
        "_rotate_and_invalidate",
        lambda client, *, token, proof_id, lane, old_credential: rotations.append(lane),
    )
    monkeypatch.setattr(
        quota_proof,
        "_update_marker",
        lambda store, *, tenant_id, proof_id, updates: marker_payload.update(updates),
    )

    with httpx.Client(
        base_url="http://127.0.0.1:10000", transport=httpx.MockTransport(handler)
    ) as client:
        report = quota_proof._run_post(
            client,
            FakeStore(),
            proof_id="q20260713a1",
            platform_secret="platform-secret-" + ("x" * 48),
            expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
            host_fingerprint="post-instance",
            restart_receipt="dep-12345678",
        )

    assert report["status"] == "present"
    assert report["restart_shared_postgres"] == "present"
    assert rotations == ["a", "b"]
    assert marker_payload["phase"] == "complete"
    assert marker_payload["restart_receipt"] == "dep-12345678"


def test_run_post_rejects_corrupt_marker_before_rotation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker_payload = _valid_marker_payload()
    marker_payload["tenant_a_overflow_audit_id"] = _AUDIT_A1

    class FakeStore:
        def get(self, tenant_id: str, kind: str, record_id: str):
            return type("Marker", (), {"payload": marker_payload})()

    rotations: list[str] = []
    monkeypatch.setattr(
        quota_proof,
        "_rotate_and_invalidate",
        lambda *args, **kwargs: rotations.append("unexpected"),
    )

    with pytest.raises(ProofFailure):
        quota_proof._run_post(
            None,
            FakeStore(),
            proof_id="q20260713a1",
            platform_secret="platform-secret-" + ("x" * 48),
            expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
            host_fingerprint="post-instance",
            restart_receipt="dep-12345678",
        )

    assert rotations == []
    assert marker_payload["phase"] == "awaiting_restart"


def test_report_redaction_is_recursive() -> None:
    payload = {
        "token": "bearer-value",
        "nested": {
            "api_credential": "casak_value",
            "Authorization": "Bearer value",
            "safe": [{"platform_secret": "secret"}, "present"],
        },
    }

    redacted = _redact(payload)

    assert redacted["token"] == "[REDACTED]"
    assert redacted["nested"]["api_credential"] == "[REDACTED]"
    assert redacted["nested"]["Authorization"] == "[REDACTED]"
    assert redacted["nested"]["safe"][0]["platform_secret"] == "[REDACTED]"
    assert redacted["nested"]["safe"][1] == "present"


@pytest.mark.parametrize(
    "sensitive_value",
    (
        "casak_pydanticRejectedInput123",
        "Bearer eyJhbGciOiJub25lIn0.payload.signature",
        "postgresql://proof-user:proof-password@db.example.invalid/canary",
    ),
)
def test_report_redaction_masks_sensitive_values_under_generic_keys(
    sensitive_value: str,
) -> None:
    payload = {
        "detail": [
            {
                "type": "string_pattern_mismatch",
                "loc": ["body", "credential"],
                "input": sensitive_value,
            }
        ]
    }

    redacted = _redact(payload)

    assert redacted["detail"][0]["input"] == "[REDACTED]"


def test_response_body_redacts_sensitive_plain_text() -> None:
    response = httpx.Response(
        422,
        text=(
            "rejected casak_plainTextSecret123 with Bearer bearer-token-123 "
            "from postgresql://proof-user:proof-password@db.example.invalid/canary"
        ),
    )

    assert _response_body(response) == {"body": "[REDACTED]"}


def test_status_mismatch_never_prints_an_arbitrary_response_body() -> None:
    naked_secret = "unpatterned-platform-authority-value"
    response = httpx.Response(422, text=naked_secret)

    with pytest.raises(ProofFailure) as exc_info:
        _expect_status(response, 200, "provision tenant")

    message = str(exc_info.value)
    assert naked_secret not in message
    assert message == "provision tenant: expected HTTP 200, received 422"


def test_quota_mismatch_projects_only_safe_contract_fields() -> None:
    naked_secret = "unpatterned-platform-authority-value"
    response = httpx.Response(
        429,
        json={
            "detail": {
                "code": naked_secret,
                "limit": naked_secret,
                "count": naked_secret,
                "period": naked_secret,
                "extra": naked_secret,
            }
        },
    )

    with pytest.raises(ProofFailure) as exc_info:
        _expect_quota_429(response, expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT)

    message = str(exc_info.value)
    assert naked_secret not in message
    assert '"code": "[INVALID]"' in message
    assert '"period_matches": false' in message
    assert "actual=" not in message


def test_proof_client_ignores_proxy_environment_and_redirects(monkeypatch) -> None:
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://proxy.example.invalid:8080")

    with _proof_client(base_url="http://127.0.0.1:10000", timeout=5.0) as client:
        assert client._trust_env is False
        assert client.follow_redirects is False
        assert client._mounts == {}


@pytest.mark.parametrize(
    "url",
    (
        "https://noetic-compass-api.onrender.com",
        "http://10.0.0.5:10000",
        "https://localhost:8443",
        "ftp://127.0.0.1:10000",
        "http://user:pass@127.0.0.1:10000",
    ),
)
def test_proof_refuses_non_loopback_or_credentialed_targets(url: str) -> None:
    with pytest.raises(ProofFailure):
        _safe_loopback_url(url)


def test_proof_accepts_only_loopback_http_targets() -> None:
    assert _safe_loopback_url("http://127.0.0.1:10000/") == "http://127.0.0.1:10000"
    assert _safe_loopback_url("https://[::1]:8443") == "https://[::1]:8443"


def test_post_phase_rejects_generic_restart_receipt() -> None:
    with pytest.raises(ProofFailure, match="safe Render restart/deploy receipt"):
        main(
            [
                "post",
                "--proof-id",
                "proof-123",
                "--expected-service-id",
                ACCOUNT_CANARY_SERVICE_ID,
                "--restart-receipt",
                "abcdef",
            ]
        )


def _set_valid_canary_environment(monkeypatch) -> None:
    values = {
        "NC_DEPLOYMENT_PROFILE": "accounts-canary",
        "NC_ACCOUNTS_ENABLED": "true",
        "NC_QUOTAS_ENABLED": "true",
        "NC_QUOTA_MONTHLY_AUDIT_LIMIT": "2",
        "NC_BILLING_ENTITLEMENTS_ENABLED": "false",
        "NC_BILLING_PROVIDER": "null",
        "NC_FLEET_SERVICE_AUTH_ENABLED": "false",
        "NC_DEBUG": "false",
        "NC_STATE_LEDGER_ENABLED": "true",
        "NC_STATE_LEDGER_READ_AUTHORITY": "true",
        "NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE": "false",
        "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED": "true",
        "CAS_HARNESS_EVIDENCE_ANCHOR_MODE": "disabled",
        "NC_DEFAULT_LLM_PROVIDER": "mock",
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX": ACCOUNT_CANARY_OBJECT_STORE_PREFIX,
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION": ACCOUNT_CANARY_OBJECT_STORE_REGION,
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE": ACCOUNT_CANARY_OBJECT_LOCK_MODE,
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS": str(
            ACCOUNT_CANARY_OBJECT_LOCK_RETENTION_DAYS
        ),
        "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY": "r" * 32,
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET": "test-only-canary-bucket",
        "AWS_ACCESS_KEY_ID": "test-only-access-key",
        "AWS_SECRET_ACCESS_KEY": "test-only-secret-key",
        "NC_MOCK_LLM": "true",
        "NC_DATABASE_URL": (
            f"postgresql://{ACCOUNT_CANARY_DATABASE_USER}:test-only-password@"
            f"{ACCOUNT_CANARY_DATABASE_HOST}:5432/{ACCOUNT_CANARY_DATABASE_NAME}"
        ),
        "NC_PLATFORM_TENANT_PROVISIONING_SECRET": "p" * 32,
        "RENDER_SERVICE_ID": ACCOUNT_CANARY_SERVICE_ID,
        "RENDER_SERVICE_TYPE": "pserv",
        "RENDER_GIT_BRANCH": ACCOUNT_CANARY_GIT_BRANCH,
        # Render can populate this for a private service. It is not a reliable
        # public/private discriminator, so the guard deliberately ignores it.
        "RENDER_EXTERNAL_URL": "https://not-used-by-the-proof.example.invalid",
    }
    monkeypatch.delenv("NC_ACCOUNT_BOOTSTRAP_SECRET", raising=False)
    monkeypatch.delenv("ACCOUNT_BOOTSTRAP_SECRET", raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_canary_environment_guard_accepts_only_the_pinned_private_canary(monkeypatch) -> None:
    _set_valid_canary_environment(monkeypatch)

    database_url, platform_secret = _require_canary_environment(
        expected_limit=2,
        expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
    )
    assert database_url.startswith("postgresql://")
    assert len(platform_secret) == 32


def test_canary_environment_guard_accepts_visible_platform_authority(monkeypatch) -> None:
    _set_valid_canary_environment(monkeypatch)
    token = "abcdefghijklmnopqrstuvwxyzABCDEF012345-_"
    monkeypatch.setenv("NC_PLATFORM_TENANT_PROVISIONING_SECRET", token)

    _, platform_secret = _require_canary_environment(
        expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
        expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
    )

    assert platform_secret == token


@pytest.mark.parametrize(
    "secret",
    (
        " " * 32,
        ("x" * 31) + " ",
        " " + ("x" * 32),
        ("x" * 32) + "\n",
        ("x" * 31) + "é",
    ),
)
def test_canary_environment_guard_rejects_unsafe_platform_authority(
    monkeypatch, secret: str
) -> None:
    _set_valid_canary_environment(monkeypatch)
    monkeypatch.setenv("NC_PLATFORM_TENANT_PROVISIONING_SECRET", secret)

    with pytest.raises(ProofFailure, match="platform provisioning authority has an unsafe syntax") as exc_info:
        _require_canary_environment(
            expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )

    assert secret not in str(exc_info.value)


def test_canary_model_is_forced_onto_the_local_mock_path(monkeypatch) -> None:
    _set_valid_canary_environment(monkeypatch)
    record = type(
        "ProofRecord",
        (),
        {
            "status": "CREATED",
            "evidence_packet_trace_id": None,
            "endpoint_url": None,
            "model_id": ACCOUNT_CANARY_MODEL_ID,
            "provider": None,
        },
    )()

    assert ACCOUNT_CANARY_MODEL_ID not in HOSTED_OPEN_WEIGHT_MODEL_IDS
    assert _should_run_hosted_open_weight(record) is False
    assert _should_run_api_endpoint(record) is False
    _require_canary_environment(
        expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
        expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
    )


@pytest.mark.parametrize(
    ("key", "value", "message"),
    (
        ("NC_ACCOUNTS_ENABLED", "1", "NC_ACCOUNTS_ENABLED=true"),
        ("NC_QUOTAS_ENABLED", "yes", "NC_QUOTAS_ENABLED=true"),
        (
            "NC_BILLING_ENTITLEMENTS_ENABLED",
            "true",
            "NC_BILLING_ENTITLEMENTS_ENABLED=false",
        ),
        (
            "NC_FLEET_SERVICE_AUTH_ENABLED",
            "true",
            "NC_FLEET_SERVICE_AUTH_ENABLED=false",
        ),
        ("NC_DEBUG", "true", "NC_DEBUG=false"),
        ("NC_DEBUG", "0", "NC_DEBUG=false"),
        ("NC_STATE_LEDGER_ENABLED", "false", "NC_STATE_LEDGER_ENABLED=true"),
        (
            "NC_STATE_LEDGER_READ_AUTHORITY",
            "false",
            "NC_STATE_LEDGER_READ_AUTHORITY=true",
        ),
        (
            "NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE",
            "true",
            "NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE=false",
        ),
        (
            "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED",
            "false",
            "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED=true",
        ),
        (
            "CAS_HARNESS_EVIDENCE_ANCHOR_MODE",
            "global",
            "CAS_HARNESS_EVIDENCE_ANCHOR_MODE=disabled",
        ),
        (
            "NC_DEFAULT_LLM_PROVIDER",
            "openai",
            "NC_DEFAULT_LLM_PROVIDER=mock",
        ),
        ("NC_MOCK_LLM", "on", "NC_MOCK_LLM=true"),
        (
            "RENDER_SERVICE_ID",
            "srv-aaaaaaaaaaaaaaaaaaaa",
            "RENDER_SERVICE_ID is the stable account canary",
        ),
        ("RENDER_SERVICE_TYPE", "web", "RENDER_SERVICE_TYPE=pserv"),
        (
            "RENDER_GIT_BRANCH",
            "master",
            "RENDER_GIT_BRANCH=release/accounts-canary-20260713",
        ),
    ),
)
def test_canary_environment_guard_rejects_boundary_drift(
    monkeypatch, key: str, value: str, message: str
) -> None:
    _set_valid_canary_environment(monkeypatch)
    monkeypatch.setenv(key, value)

    with pytest.raises(ProofFailure, match=re.escape(message)):
        _require_canary_environment(
            expected_limit=2,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )


def test_canary_environment_guard_requires_explicit_false_flags(monkeypatch) -> None:
    _set_valid_canary_environment(monkeypatch)
    monkeypatch.delenv("NC_FLEET_SERVICE_AUTH_ENABLED")

    with pytest.raises(ProofFailure, match="NC_FLEET_SERVICE_AUTH_ENABLED=false"):
        _require_canary_environment(
            expected_limit=2,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )


@pytest.mark.parametrize(
    "name", ("NC_ACCOUNT_BOOTSTRAP_SECRET", "ACCOUNT_BOOTSTRAP_SECRET")
)
def test_canary_environment_guard_rejects_bootstrap_secret_aliases_without_echoing(
    monkeypatch, name: str
) -> None:
    _set_valid_canary_environment(monkeypatch)
    secret = "bootstrap-authority-must-not-appear"
    monkeypatch.setenv(name, secret)

    with pytest.raises(ProofFailure, match=f"{name} is absent") as exc_info:
        _require_canary_environment(
            expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )

    assert secret not in str(exc_info.value)


@pytest.mark.parametrize(
    "name", ("NC_ACCOUNT_BOOTSTRAP_SECRET", "ACCOUNT_BOOTSTRAP_SECRET")
)
def test_canary_environment_guard_rejects_whitespace_bootstrap_secret_aliases(
    monkeypatch, name: str
) -> None:
    _set_valid_canary_environment(monkeypatch)
    secret = " " * 32
    monkeypatch.setenv(name, secret)

    with pytest.raises(ProofFailure, match=f"{name} is absent") as exc_info:
        _require_canary_environment(
            expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )

    assert secret not in str(exc_info.value)


@pytest.mark.parametrize(
    ("name", "value", "message"),
    (
        (
            "CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX",
            "cas-harness/evidence-anchors",
            "S3_PREFIX is account-canary scoped",
        ),
        (
            "CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION",
            "us-east-1",
            "S3_REGION=us-west-2",
        ),
        (
            "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE",
            "COMPLIANCE",
            "S3_OBJECT_LOCK_MODE=GOVERNANCE",
        ),
        (
            "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS",
            "30",
            "S3_RETENTION_DAYS=31",
        ),
    ),
)
def test_canary_environment_guard_rejects_object_store_boundary_drift(
    monkeypatch, name: str, value: str, message: str
) -> None:
    _set_valid_canary_environment(monkeypatch)
    monkeypatch.setenv(name, value)

    with pytest.raises(ProofFailure, match=message):
        _require_canary_environment(
            expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )


@pytest.mark.parametrize(
    "secret",
    (
        "",
        "r" * 31,
        ("r" * 31) + " ",
        " " + ("r" * 32),
        ("r" * 32) + "\n",
        ("r" * 31) + "é",
    ),
)
def test_canary_environment_guard_requires_safe_receipt_attestation_authority(
    monkeypatch, secret: str
) -> None:
    _set_valid_canary_environment(monkeypatch)
    monkeypatch.setenv("NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY", secret)

    with pytest.raises(
        ProofFailure,
        match="Object Lock receipt attestation authority has safe syntax",
    ) as exc_info:
        _require_canary_environment(
            expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )

    if secret:
        assert secret not in str(exc_info.value)


@pytest.mark.parametrize(
    "name",
    (
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    ),
)
def test_canary_environment_guard_requires_object_store_authority(
    monkeypatch, name: str
) -> None:
    _set_valid_canary_environment(monkeypatch)
    monkeypatch.delenv(name)

    with pytest.raises(ProofFailure, match=f"{name} is present"):
        _require_canary_environment(
            expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )


def test_canary_environment_guard_rejects_operator_supplied_service_id_drift(
    monkeypatch,
) -> None:
    _set_valid_canary_environment(monkeypatch)

    with pytest.raises(ProofFailure, match="expected Render service id is the stable"):
        _require_canary_environment(
            expected_limit=2,
            expected_service_id="srv-aaaaaaaaaaaaaaaaaaaa",
        )


def test_canary_environment_guard_rejects_matching_quota_limit_drift(monkeypatch) -> None:
    _set_valid_canary_environment(monkeypatch)
    drifted_limit = ACCOUNT_CANARY_QUOTA_LIMIT + 8
    monkeypatch.setenv("NC_QUOTA_MONTHLY_AUDIT_LIMIT", str(drifted_limit))

    with pytest.raises(ProofFailure, match="pinned account canary limit"):
        _require_canary_environment(
            expected_limit=drifted_limit,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )


@pytest.mark.parametrize(
    "name",
    (
        "PGHOSTADDR",
        "PGSERVICE",
        "PGSERVICEFILE",
        "PGOPTIONS",
        "PGFUTUREOVERRIDE",
    ),
)
def test_canary_environment_guard_rejects_all_libpq_environment_overrides(
    monkeypatch, name: str
) -> None:
    _set_valid_canary_environment(monkeypatch)
    secret_value = "must-not-appear-in-proof-output"
    monkeypatch.setenv(name, secret_value)

    with pytest.raises(ProofFailure, match=r"no libpq PG\* environment overrides") as exc_info:
        _require_canary_environment(
            expected_limit=ACCOUNT_CANARY_QUOTA_LIMIT,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )

    assert secret_value not in str(exc_info.value)


def test_canary_database_guard_pins_host_without_echoing_credentials(monkeypatch) -> None:
    _set_valid_canary_environment(monkeypatch)
    secret = "do-not-echo-this-database-password"
    unsafe_url = (
        f"postgresql://cas_harness_canary:{secret}@"
        "dpg-not-the-account-canary-a:5432/cas_harness_accounts_canary"
    )
    monkeypatch.setenv("NC_DATABASE_URL", unsafe_url)

    with pytest.raises(ProofFailure) as exc_info:
        _require_canary_environment(
            expected_limit=2,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )
    assert secret not in str(exc_info.value)
    assert unsafe_url not in str(exc_info.value)


@pytest.mark.parametrize(
    "url",
    (
        "postgresql://user:password@[::1",
        f"https://user:password@{ACCOUNT_CANARY_DATABASE_HOST}/canary",
        f"postgresql://user@{ACCOUNT_CANARY_DATABASE_HOST}/canary",
        f"postgresql://user:password@{ACCOUNT_CANARY_DATABASE_HOST}:6432/canary",
    ),
)
def test_canary_database_guard_rejects_malformed_or_unsafe_targets(url: str) -> None:
    with pytest.raises(ProofFailure):
        _require_canary_database_url(url)


@pytest.mark.parametrize(
    "url",
    (
        f"postgresql://wrong-role:password@{ACCOUNT_CANARY_DATABASE_HOST}:5432/{ACCOUNT_CANARY_DATABASE_NAME}",
        f"postgresql://{ACCOUNT_CANARY_DATABASE_USER}:password@{ACCOUNT_CANARY_DATABASE_HOST}:5432/postgres",
        f"postgresql://{ACCOUNT_CANARY_DATABASE_USER}:password@{ACCOUNT_CANARY_DATABASE_HOST}:5432/{ACCOUNT_CANARY_DATABASE_NAME}/shadow",
        f"postgresql://{ACCOUNT_CANARY_DATABASE_USER}:password@{ACCOUNT_CANARY_DATABASE_HOST}:5432/{ACCOUNT_CANARY_DATABASE_NAME}%2Fshadow",
        f"postgresql://{ACCOUNT_CANARY_DATABASE_USER}:password@{ACCOUNT_CANARY_DATABASE_HOST}:5432/%2e%2e/{ACCOUNT_CANARY_DATABASE_NAME}",
    ),
)
def test_canary_database_guard_pins_decoded_role_and_single_database_path(
    url: str,
) -> None:
    with pytest.raises(ProofFailure):
        _require_canary_database_url(url)


@pytest.mark.parametrize(
    "query",
    (
        "host=evil.example",
        "hostaddr=203.0.113.7",
        "sslmode=require",
    ),
)
def test_canary_database_guard_rejects_all_query_parameters(query: str) -> None:
    url = (
        "postgresql://user:password@"
        f"{ACCOUNT_CANARY_DATABASE_HOST}:5432/canary?{query}"
    )

    with pytest.raises(ProofFailure):
        _require_canary_database_url(url)


def test_canary_database_guard_rejects_path_parameters() -> None:
    url = (
        "postgresql://user:password@"
        f"{ACCOUNT_CANARY_DATABASE_HOST}:5432/canary;host=evil.example"
    )

    with pytest.raises(ProofFailure):
        _require_canary_database_url(url)


def test_canary_environment_guard_requires_exact_dark_billing_posture(monkeypatch) -> None:
    _set_valid_canary_environment(monkeypatch)
    monkeypatch.setenv("NC_BILLING_ENTITLEMENTS_ENABLED", "true")
    with pytest.raises(ProofFailure, match="NC_BILLING_ENTITLEMENTS_ENABLED=false"):
        _require_canary_environment(
            expected_limit=2,
            expected_service_id=ACCOUNT_CANARY_SERVICE_ID,
        )
