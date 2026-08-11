from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "redteam_deepseek_v4_role_routing.py"
)
SPEC = importlib.util.spec_from_file_location(
    "redteam_deepseek_v4_role_routing",
    SCRIPT_PATH,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_role_probe_requires_exact_flash_and_pro_generation(monkeypatch):
    def fake_generate(base_url, *, model, expected, timeout):  # noqa: ARG001
        return {
            "http_status": 200,
            "elapsed_ms": 12,
            "model_ref": model,
            "response": expected,
            "expected": expected,
            "matched": True,
            "done": True,
            "done_reason": "stop",
        }

    monkeypatch.setattr(MODULE, "_generate", fake_generate)

    report = MODULE.build_report(
        base_url="http://127.0.0.1:11434",
        flash_model="deepseek-v4-flash",
        pro_model="deepseek-v4-pro",
        timeout=10.0,
    )

    assert report["status"] == "PASS_DEEPSEEK_V4_ROLE_CAPABILITY"
    assert all(report["invariant_checks"].values())
    assert report["role_routes"]["fast"]["model_ref"] == "deepseek-v4-flash:cloud"
    assert report["role_routes"]["pro"]["model_ref"] == "deepseek-v4-pro:cloud"
    assert report["broker_touched"] is False
    assert report["money_moved"] is False
    assert len(report["event_hash"]) == 64


def test_role_probe_retries_a_transient_shortened_marker(monkeypatch):
    calls = {"count": 0}

    def fake_generate_once(base_url, *, model, expected, timeout):  # noqa: ARG001
        calls["count"] += 1
        response = expected.rsplit("_", 1)[0] if calls["count"] == 1 else expected
        return {
            "http_status": 200,
            "elapsed_ms": 12,
            "model_ref": model,
            "response": response,
            "expected": expected,
            "matched": response == expected,
            "done": True,
            "done_reason": "stop",
        }

    monkeypatch.setattr(MODULE, "_generate_once", fake_generate_once)

    result = MODULE._generate(
        "http://127.0.0.1:11434",
        model="deepseek-v4-flash:cloud",
        expected="CAS_FLASH_READY",
        timeout=10.0,
    )

    assert result["matched"] is True
    assert result["attempt_count"] == 2
    assert result["attempts"][0]["matched"] is False
    assert result["attempts"][1]["matched"] is True
