from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from scripts import hosted_live_worker_worm_smoke as smoke


def test_smoke_requires_worker_url_before_network_access(monkeypatch):
    for name in smoke.WORKER_URL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv(smoke.WORKER_TOKEN_ENV_VAR, raising=False)

    with pytest.raises(smoke.HostedSmokeFailure, match="worker-url"):
        smoke.main(["--worker-token", "secret"])


def test_smoke_requires_worker_token_before_network_access(monkeypatch):
    monkeypatch.delenv(smoke.WORKER_TOKEN_ENV_VAR, raising=False)

    with pytest.raises(smoke.HostedSmokeFailure, match="worker-token"):
        smoke.main(["--worker-url", "https://pod-id-8080.proxy.runpod.net"])


def test_smoke_realmode_gate_rejects_demo_worker():
    with pytest.raises(smoke.HostedSmokeFailure, match="worker-health"):
        smoke.assert_realmode(
            "worker-health",
            {
                "verdict": "NOT_REAL_PYTHIA_WEIGHTS",
                "is_real_model": False,
                "fake_runtime_env": True,
                "model_loaded": False,
                "load_error": None,
                "manifest_is_real_model": False,
                "model_id": smoke.MODEL_ID,
            },
        )


def test_smoke_preserves_flag_for_human_review_proof_chip_vocabulary():
    assert smoke.chip_present({"causal_proof": "present"}, "causal_proof") is True
    assert (
        smoke.chip_present({"control_proof": "unavailable"}, "control_proof")
        is False
    )
    with pytest.raises(smoke.HostedSmokeFailure, match="unexpected"):
        smoke.chip_present({"packet_proof": "ACCEPT"}, "packet_proof")


def test_smoke_audit_prompt_includes_unique_run_nonce():
    first = smoke.build_audit_prompt("nonce-one")
    second = smoke.build_audit_prompt("nonce-two")

    assert first != second
    assert "run_nonce=nonce-one" in first
    assert "run_nonce=nonce-two" in second


def test_smoke_audit_prompt_rejects_empty_run_nonce():
    with pytest.raises(smoke.HostedSmokeFailure, match="run-nonce"):
        smoke.build_audit_prompt("  ")


def test_smoke_identifies_urllib_requests_for_runpod_proxy(monkeypatch):
    captured = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout):
        captured["user_agent"] = request.get_header("User-agent")
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(smoke, "urlopen", fake_urlopen)

    status, payload = smoke.request_json(
        "https://pod-id-8080.proxy.runpod.net",
        "/health",
        method="GET",
        payload=None,
        bearer_token=None,
        extra_headers=None,
        expected_statuses={200},
        gate="worker-health",
    )

    assert status == 200
    assert payload == {}
    assert captured["user_agent"] == smoke.USER_AGENT
    assert captured["timeout"] == 120


def test_customer_production_retention_accepts_exact_minimum_with_offset_timestamp():
    verified_at = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
    retention_days, requested_at, retain_until, remaining = (
        smoke.assert_customer_production_retention(
            {
                "retention_days": 31,
                "retention_requested_at": "2026-07-13T05:00:00-07:00",
                "object_lock_retain_until": "2026-08-13T05:00:00-07:00",
            },
            verified_at=verified_at,
        )
    )

    assert retention_days == 31
    assert requested_at == datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    assert retain_until == datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    assert remaining == timedelta(days=30)


def test_customer_production_retention_parses_z_timestamp():
    parsed = smoke.parse_timezone_aware_timestamp(
        "2026-08-14T12:00:00.123456Z",
        field="object_lock_retain_until",
    )

    assert parsed == datetime(2026, 8, 14, 12, 0, 0, 123456, tzinfo=timezone.utc)


@pytest.mark.parametrize("retention_days", [30, 0, True, 31.0, None])
def test_customer_production_retention_rejects_short_or_non_integer_configuration(retention_days):
    with pytest.raises(
        smoke.HostedSmokeFailure,
        match=r"configured retention_days >= 31",
    ):
        smoke.assert_customer_production_retention(
            {
                "retention_days": retention_days,
                "retention_requested_at": "2026-07-14T12:00:00Z",
                "object_lock_retain_until": "2026-09-14T12:00:00Z",
            },
            verified_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        )


def test_customer_production_retention_rejects_less_than_30_days_remaining():
    verified_at = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)

    with pytest.raises(smoke.HostedSmokeFailure, match="at least 30 days"):
        smoke.assert_customer_production_retention(
            {
                "retention_days": 31,
                "retention_requested_at": "2026-07-13T11:59:59.999999Z",
                "object_lock_retain_until": "2026-08-13T11:59:59.999999Z",
            },
            verified_at=verified_at,
        )


@pytest.mark.parametrize(
    "retain_until",
    [
        "2026-08-14T12:00:00",
        "not-a-timestamp",
        "",
        None,
    ],
)
def test_customer_production_retention_rejects_ambiguous_or_invalid_timestamp(retain_until):
    with pytest.raises(smoke.HostedSmokeFailure, match="timezone-aware|include Z"):
        smoke.assert_customer_production_retention(
            {
                "retention_days": 31,
                "retention_requested_at": "2026-07-14T12:00:00Z",
                "object_lock_retain_until": retain_until,
            },
            verified_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    "requested_at",
    ["2026-07-14T12:00:00", "not-a-timestamp", "", None],
)
def test_customer_production_retention_requires_timezone_aware_request_boundary(
    requested_at,
):
    with pytest.raises(smoke.HostedSmokeFailure, match="retention_requested_at"):
        smoke.assert_customer_production_retention(
            {
                "retention_days": 31,
                "retention_requested_at": requested_at,
                "object_lock_retain_until": "2026-08-14T12:00:00Z",
            },
            verified_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        )


def test_customer_production_retention_rejects_receipt_shorter_than_configured_window():
    with pytest.raises(
        smoke.HostedSmokeFailure,
        match="shorter than the configured retention window",
    ):
        smoke.assert_customer_production_retention(
            {
                "retention_days": 31,
                "retention_requested_at": "2026-07-14T12:00:00Z",
                "object_lock_retain_until": "2026-08-14T11:59:59.999999Z",
            },
            verified_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        )


def test_customer_production_retention_rejects_verification_before_request_boundary():
    with pytest.raises(
        smoke.HostedSmokeFailure,
        match="predates the Object Lock request boundary",
    ):
        smoke.assert_customer_production_retention(
            {
                "retention_days": 31,
                "retention_requested_at": "2026-07-14T12:00:01Z",
                "object_lock_retain_until": "2026-08-14T12:00:01Z",
            },
            verified_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        )
