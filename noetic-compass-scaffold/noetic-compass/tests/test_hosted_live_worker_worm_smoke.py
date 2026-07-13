from __future__ import annotations

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
