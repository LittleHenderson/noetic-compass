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
