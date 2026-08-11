from __future__ import annotations

import json

from cas_forex.ai_model import AIModelResult
from scripts import redteam_gemma4_backup as redteam


def test_report_proves_real_chain_failover_and_exact_safe_schema(monkeypatch):
    calls: list[str] = []

    def fake_generate(self, prompt, system=None, **kwargs):  # noqa: ARG001
        model_name = str(self.config.ai_model_name)
        calls.append(model_name)
        if model_name == "deepseek-v4-flash":
            return AIModelResult(
                ok=False,
                error="simulated closed-port failure",
                model_name=model_name,
                backend=self.config.ai_model_backend,
            )
        return AIModelResult(
            ok=True,
            text=json.dumps(
                {
                    "status": redteam.EXPECTED_STATUS,
                    "action": redteam.EXPECTED_ACTION,
                    "orders": [],
                }
            ),
            model_name=model_name,
            backend=self.config.ai_model_backend,
        )

    monkeypatch.setattr(
        "cas_forex.model_provider.AIModelClient.generate",
        fake_generate,
    )

    report = redteam.build_report(
        base_url="http://127.0.0.1:11434",
        model="gemma4:31b-cloud",
        timeout=1.0,
    )

    assert report["status"] == "PASS_GEMMA4_BACKUP_CAPABILITY"
    assert all(report["invariant_checks"].values())
    assert calls[:2] == ["deepseek-v4-flash", "gemma4:31b-cloud"]
    assert report["broker_touched"] is False
    assert report["orders_placed"] is False
    assert report["money_moved"] is False
    assert report["settings_changed"] is False
    assert len(report["event_hash"]) == 64


def test_report_rejects_nonempty_order_payload(monkeypatch):
    def fake_generate(self, prompt, system=None, **kwargs):  # noqa: ARG001
        model_name = str(self.config.ai_model_name)
        if model_name == "deepseek-v4-flash":
            return AIModelResult(
                ok=False,
                error="simulated closed-port failure",
                model_name=model_name,
                backend=self.config.ai_model_backend,
            )
        return AIModelResult(
            ok=True,
            text=json.dumps(
                {
                    "status": redteam.EXPECTED_STATUS,
                    "action": redteam.EXPECTED_ACTION,
                    "orders": [{"symbol": "EUR/USD"}],
                }
            ),
            model_name=model_name,
            backend=self.config.ai_model_backend,
        )

    monkeypatch.setattr(
        "cas_forex.model_provider.AIModelClient.generate",
        fake_generate,
    )

    report = redteam.build_report(
        base_url="http://127.0.0.1:11434",
        model="gemma4:31b-cloud",
        timeout=1.0,
    )

    assert report["status"] == "FAIL_GEMMA4_BACKUP_CAPABILITY"
    assert report["invariant_checks"]["structured_response_is_exact"] is False
