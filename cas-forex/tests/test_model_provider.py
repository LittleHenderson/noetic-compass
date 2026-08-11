"""Tests for the role-aware CAS Forex model-provider failover layer."""

from __future__ import annotations

import threading
import time
import json
from types import SimpleNamespace

import pytest

from cas_forex import model_provider, operator_secrets
from cas_forex.ai_model import AIModelResult
from cas_forex.model_provider import ModelProvider, build_provider_chain


@pytest.fixture(autouse=True)
def _isolate_operator_secret_store(tmp_path, monkeypatch):
    # build_provider_chain consults the durable secret store for a pasted key;
    # point it at an empty temp file so tests never read the owner's real key.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    operator_secrets.set_secrets_path_for_tests(tmp_path / "operator-secrets.json")
    yield
    operator_secrets.set_secrets_path_for_tests(None)


def _config(**over):
    base = dict(
        ai_operator_primary_api_key="sk-test-key",
        ai_operator_primary_backend="frontier_anthropic",
        ai_operator_primary_model="claude-test",
        ai_operator_primary_base_url="https://api.anthropic.com",
        ai_operator_token_budget=0,
        ai_operator_gemma_backup_enabled=False,
        ai_operator_gemma_backup_transport="ollama_cloud",
        ai_operator_gemma_backup_model="gemma4:31b-cloud",
        ai_operator_gemma_backup_ollama_base_url="http://127.0.0.1:11434",
        ai_model_backend="ollama",
        ai_model_name="llama-test",
        ai_model_base_url="http://127.0.0.1:11434",
        ai_model_api_key=None,
        ai_model_max_tokens=256,
        ai_model_context_tokens=16384,
        ai_model_structured_max_tokens=512,
        ai_model_temperature=0.2,
        ai_model_control_plane="CAS_HARNESS_PCBA",
        ai_model_pcba_guard_enabled=False,
        ai_model_enabled=True,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _provider(tmp_path, cfg, monkeypatch, responses):
    """Patch AIModelClient.generate to a scripted per-backend response map."""
    calls = []

    def fake_generate(self, prompt, system=None):
        backend = str(getattr(self.config, "ai_model_backend", "")).lower()
        calls.append(backend)
        resp = responses.get(backend)
        if resp is None:
            return AIModelResult(ok=False, error="not configured", backend=backend)
        return resp(backend) if callable(resp) else resp

    monkeypatch.setattr("cas_forex.model_provider.AIModelClient.generate", fake_generate)
    mp = ModelProvider(
        cfg,
        state_path=tmp_path / "state.json",
        events_path=tmp_path / "events.jsonl",
        cooldown_seconds=900,
    )
    return mp, calls


def test_chain_has_paid_primary_then_free_fallback(tmp_path):
    chain = build_provider_chain(_config())
    assert [p.name for p in chain] == ["claude", "local-fallback"]
    assert chain[0].paid is True
    assert chain[1].paid is False


def test_no_primary_key_means_free_fallback_is_active(tmp_path):
    chain = build_provider_chain(_config(ai_operator_primary_api_key=None))
    assert [p.name for p in chain] == ["local-fallback"]
    assert chain[0].paid is False


def test_deepseek_flash_and_pro_are_role_routed_ahead_of_existing_fallbacks():
    cfg = _config(
        ai_operator_deepseek_api_key="ds-test-key",
        ai_operator_deepseek_enabled=True,
        ai_operator_deepseek_transport="direct",
        ai_operator_deepseek_base_url="https://api.deepseek.com",
        ai_operator_flash_model="deepseek-v4-flash",
        ai_operator_pro_model="deepseek-v4-pro",
        ai_operator_pro_request_kinds="compound_scale_in,money_movement",
    )

    fast = build_provider_chain(cfg, request_kind="operator_chat")
    pro = build_provider_chain(cfg, request_kind="compound_scale_in")

    assert [row.name for row in fast] == [
        "deepseek-flash",
        "claude",
        "local-fallback",
    ]
    assert [row.name for row in pro] == [
        "deepseek-pro",
        "deepseek-flash",
        "claude",
        "local-fallback",
    ]
    assert fast[0].model_name == "deepseek-v4-flash"
    assert pro[0].model_name == "deepseek-v4-pro"
    assert fast[0].backend == "frontier_deepseek"


def test_ollama_cloud_role_routes_use_cloud_model_ids_without_claiming_free():
    cfg = _config(
        ai_operator_deepseek_api_key=None,
        ai_operator_deepseek_enabled=True,
        ai_operator_deepseek_transport="ollama_cloud",
        ai_operator_deepseek_ollama_base_url="http://127.0.0.1:11434",
        ai_operator_flash_model="deepseek-v4-flash",
        ai_operator_pro_model="deepseek-v4-pro",
        ai_operator_pro_request_kinds="compound_scale_in",
    )

    fast = build_provider_chain(cfg, model_role="fast")[0]
    pro = build_provider_chain(cfg, model_role="pro")[0]

    assert fast.model_name == "deepseek-v4-flash:cloud"
    assert pro.model_name == "deepseek-v4-pro:cloud"
    assert fast.backend == "ollama"
    assert fast.paid is True
    assert "sign-in required" in fast.free_note


def test_gemma4_31b_cloud_is_large_model_backup_after_deepseek():
    cfg = _config(
        ai_operator_deepseek_api_key=None,
        ai_operator_deepseek_enabled=True,
        ai_operator_deepseek_transport="ollama_cloud",
        ai_operator_deepseek_ollama_base_url="http://127.0.0.1:11434",
        ai_operator_flash_model="deepseek-v4-flash",
        ai_operator_pro_model="deepseek-v4-pro",
        ai_operator_pro_request_kinds="compound_scale_in",
        ai_operator_gemma_backup_enabled=True,
        ai_operator_gemma_backup_model="gemma4:31b",
    )

    fast = build_provider_chain(cfg, model_role="fast")
    pro = build_provider_chain(cfg, model_role="pro")

    assert [row.name for row in fast] == [
        "deepseek-flash",
        "gemma4-backup",
        "claude",
        "local-fallback",
    ]
    assert [row.name for row in pro] == [
        "deepseek-pro",
        "deepseek-flash",
        "gemma4-backup",
        "claude",
        "local-fallback",
    ]
    backup = fast[1]
    assert backup.model_name == "gemma4:31b-cloud"
    assert backup.backend == "ollama"
    assert backup.role == "backup"
    assert backup.paid is True
    assert "sign-in required" in backup.free_note


def test_deepseek_failure_reaches_gemma_before_legacy_fallbacks(
    tmp_path,
    monkeypatch,
):
    cfg = _config(
        ai_operator_deepseek_api_key=None,
        ai_operator_deepseek_enabled=True,
        ai_operator_deepseek_transport="ollama_cloud",
        ai_operator_deepseek_ollama_base_url="http://127.0.0.1:11434",
        ai_operator_flash_model="deepseek-v4-flash",
        ai_operator_pro_model="deepseek-v4-pro",
        ai_operator_gemma_backup_enabled=True,
        ai_operator_gemma_backup_model="gemma4:31b-cloud",
    )
    calls: list[str] = []

    def fake_generate(self, prompt, system=None, **kwargs):  # noqa: ARG001
        model_name = str(self.config.ai_model_name)
        calls.append(model_name)
        if model_name.startswith("deepseek-"):
            return AIModelResult(
                ok=False,
                error="simulated DeepSeek outage",
                model_name=model_name,
                backend=self.config.ai_model_backend,
            )
        return AIModelResult(
            ok=True,
            text='{"status":"STAND_DOWN"}',
            model_name=model_name,
            backend=self.config.ai_model_backend,
        )

    monkeypatch.setattr(
        "cas_forex.model_provider.AIModelClient.generate",
        fake_generate,
    )
    provider = ModelProvider(
        cfg,
        state_path=tmp_path / "state.json",
        events_path=tmp_path / "events.jsonl",
    )

    result = provider.generate("bounded decision", model_role="fast")

    assert result["ok"] is True
    assert result["provider"] == "gemma4-backup"
    assert result["model_ref"] == "gemma4:31b-cloud"
    assert result["model_role"] == "backup"
    assert result["requested_model_role"] == "fast"
    assert result["failover"] is True
    assert result["switch_reason"] == "failed over to Gemma 4 backup"
    assert calls == ["deepseek-v4-flash:cloud", "gemma4:31b-cloud"]
    assert [row["provider"] for row in result["attempts"]] == [
        "deepseek-flash",
        "gemma4-backup",
    ]


def test_gemma_backup_status_reports_independent_capability_health(tmp_path):
    cfg = _config(
        ai_operator_gemma_backup_enabled=True,
        ai_operator_gemma_backup_model="gemma4:31b-cloud",
    )
    provider = ModelProvider(
        cfg,
        state_path=tmp_path / "state.json",
        events_path=tmp_path / "events.jsonl",
    )
    provider._state["provider_health"] = {
        "gemma4-backup": {
            "reachability": "READY",
            "checked_at": "2026-07-15T00:00:00+00:00",
            "checked_at_epoch": time.time(),
            "error": None,
        },
    }

    status = provider.status()

    assert status["gemma4_backup_configured"] is True
    assert status["gemma4_backup_transport"] == "ollama_cloud"
    assert status["role_routes"]["backup"]["provider"] == "gemma4-backup"
    assert status["role_routes"]["backup"]["model_ref"] == "gemma4:31b-cloud"
    assert status["role_routes"]["backup"]["reachability"] == "READY"


def test_role_routes_report_independent_fresh_generation_health(tmp_path):
    cfg = _config(
        ai_operator_deepseek_api_key="ds-test-key",
        ai_operator_deepseek_enabled=True,
        ai_operator_deepseek_transport="direct",
        ai_operator_flash_model="deepseek-v4-flash",
        ai_operator_pro_model="deepseek-v4-pro",
    )
    provider = ModelProvider(
        cfg,
        state_path=tmp_path / "state.json",
        events_path=tmp_path / "events.jsonl",
    )
    checked_at_epoch = time.time()
    provider._state["provider_health"] = {
        "deepseek-flash": {
            "reachability": "READY",
            "checked_at": "2026-07-15T00:00:00+00:00",
            "checked_at_epoch": checked_at_epoch,
            "error": None,
        },
        "deepseek-pro": {
            "reachability": "READY",
            "checked_at": "2026-07-15T00:00:01+00:00",
            "checked_at_epoch": checked_at_epoch,
            "error": None,
        },
    }

    routes = provider.status()["role_routes"]

    assert routes["fast"]["model_ref"] == "deepseek-v4-flash"
    assert routes["fast"]["reachability"] == "READY"
    assert routes["pro"]["model_ref"] == "deepseek-v4-pro"
    assert routes["pro"]["reachability"] == "READY"


def test_deepseek_pro_escalation_is_not_blocked_by_exhausted_claude_budget(
    tmp_path,
    monkeypatch,
):
    cfg = _config(
        ai_operator_token_budget=100,
        ai_operator_deepseek_api_key="ds-test-key",
        ai_operator_deepseek_enabled=True,
        ai_operator_deepseek_transport="direct",
        ai_operator_deepseek_base_url="https://api.deepseek.com",
        ai_operator_flash_model="deepseek-v4-flash",
        ai_operator_pro_model="deepseek-v4-pro",
        ai_operator_pro_request_kinds="compound_scale_in",
    )
    calls = []

    def fake_generate(self, prompt, system=None, **kwargs):  # noqa: ARG001
        calls.append(self.config.ai_model_name)
        return AIModelResult(
            ok=True,
            text='{"position_decisions":[]}',
            model_name=self.config.ai_model_name,
            backend=self.config.ai_model_backend,
        )

    monkeypatch.setattr(
        "cas_forex.model_provider.AIModelClient.generate",
        fake_generate,
    )
    mp = ModelProvider(
        cfg,
        state_path=tmp_path / "state.json",
        events_path=tmp_path / "events.jsonl",
    )
    mp._state["spent_tokens"] = 100
    mp._save()

    result = mp.generate("decide", request_kind="compound_scale_in")

    assert result["ok"] is True
    assert result["provider"] == "deepseek-pro"
    assert result["model_ref"] == "deepseek-v4-pro"
    assert result["requested_model_role"] == "pro"
    assert result["model_role"] == "pro"
    assert result["switch_reason"] == "routed to Pro escalation"
    assert mp._state["spent_tokens"] == 100
    assert calls == ["deepseek-v4-pro"]


def test_legacy_deepseek_switch_reason_is_migrated_to_role_truth(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "active_provider": "deepseek-flash",
                "last_switch": {
                    "from": "claude",
                    "to": "deepseek-flash",
                    "reason": "recovered to primary",
                    "at": "2026-07-14T23:51:36+00:00",
                },
            }
        ),
        encoding="utf-8",
    )
    cfg = _config(
        ai_operator_deepseek_api_key="ds-test-key",
        ai_operator_deepseek_enabled=True,
        ai_operator_deepseek_transport="direct",
        ai_operator_flash_model="deepseek-v4-flash",
        ai_operator_pro_model="deepseek-v4-pro",
    )

    provider = ModelProvider(
        cfg,
        state_path=state_path,
        events_path=tmp_path / "events.jsonl",
    )

    assert provider.status()["last_switch"]["reason"] == (
        "routed to Flash continuous lane"
    )


def test_operator_secret_store_encrypts_runtime_key(tmp_path):
    path = tmp_path / "operator-secrets.json"
    operator_secrets.set_secrets_path_for_tests(path)

    operator_secrets.set_secret("primary_api_key", "OPERATOR_RUNTIME_SECRET")

    persisted = path.read_text(encoding="utf-8")
    assert "OPERATOR_RUNTIME_SECRET" not in persisted
    assert '"encrypted": true' in persisted.lower()
    assert '"secret_storage"' in persisted
    assert operator_secrets.get_secret("primary_api_key") == "OPERATOR_RUNTIME_SECRET"
    status = operator_secrets.store_status()
    assert status["at_rest_encrypted"] is True


def test_operator_secret_store_migrates_legacy_plaintext(tmp_path):
    path = tmp_path / "operator-secrets.json"
    path.write_text(
        json.dumps({"primary_api_key": "LEGACY_OPERATOR_SECRET"}),
        encoding="utf-8",
    )
    operator_secrets.set_secrets_path_for_tests(path)

    assert operator_secrets.get_secret("primary_api_key") == "LEGACY_OPERATOR_SECRET"
    rewritten = path.read_text(encoding="utf-8")
    assert "LEGACY_OPERATOR_SECRET" not in rewritten
    assert '"encrypted": true' in rewritten.lower()


def test_primary_used_when_it_succeeds(tmp_path, monkeypatch):
    cfg = _config()
    mp, calls = _provider(
        tmp_path, cfg, monkeypatch,
        {
            "frontier_anthropic": AIModelResult(ok=True, text='{"actions": []}', backend="frontier_anthropic"),
            "ollama": AIModelResult(ok=True, text="free", backend="ollama"),
        },
    )
    out = mp.generate("hello")
    assert out["ok"] is True
    assert out["provider"] == "claude"
    assert out["paid"] is True
    assert calls == ["frontier_anthropic"]  # free fallback never touched
    status = mp.status()
    assert status["provider_reachability"] == "READY"
    assert status["provider_last_error"] is None
    assert status["active_model"] == "claude-test"


def test_credit_error_fails_over_to_free_and_cools_primary(tmp_path, monkeypatch):
    cfg = _config()
    mp, calls = _provider(
        tmp_path, cfg, monkeypatch,
        {
            "frontier_anthropic": AIModelResult(ok=False, error="Your credit balance is too low (400)", backend="frontier_anthropic"),
            "ollama": AIModelResult(ok=True, text="free answer", backend="ollama"),
        },
    )
    out = mp.generate("hello")
    assert out["ok"] is True
    assert out["provider"] == "local-fallback"
    assert out["failover"] is True
    assert calls == ["frontier_anthropic", "ollama"]  # tried primary, fell to free

    status = mp.status()
    assert status["primary_in_cooldown"] is True
    assert status["active_provider"] == "local-fallback"
    assert status["last_switch"]["to"] == "local-fallback"


def test_budget_exhaustion_skips_primary_without_calling_it(tmp_path, monkeypatch):
    cfg = _config(ai_operator_token_budget=100)
    mp, calls = _provider(
        tmp_path, cfg, monkeypatch,
        {
            "frontier_anthropic": AIModelResult(ok=True, text="paid", backend="frontier_anthropic"),
            "ollama": AIModelResult(ok=True, text="free", backend="ollama"),
        },
    )
    # Spend the budget.
    mp._state["spent_tokens"] = 100
    mp._save()
    out = mp.generate("hello")
    assert out["ok"] is True
    assert out["provider"] == "local-fallback"
    assert "frontier_anthropic" not in calls  # never even called the paid primary


def test_top_up_flips_back_to_primary(tmp_path, monkeypatch):
    cfg = _config(ai_operator_token_budget=100)
    mp, calls = _provider(
        tmp_path, cfg, monkeypatch,
        {
            "frontier_anthropic": AIModelResult(ok=True, text="paid", backend="frontier_anthropic"),
            "ollama": AIModelResult(ok=True, text="free", backend="ollama"),
        },
    )
    mp._state["spent_tokens"] = 100
    mp._save()
    assert mp.generate("x")["provider"] == "local-fallback"

    mp.top_up(50_000)
    out = mp.generate("y")
    assert out["provider"] == "claude"
    assert out["paid"] is True


def test_all_providers_fail_returns_not_ok(tmp_path, monkeypatch):
    cfg = _config()
    mp, calls = _provider(
        tmp_path, cfg, monkeypatch,
        {
            "frontier_anthropic": AIModelResult(ok=False, error="credit too low", backend="frontier_anthropic"),
            "ollama": AIModelResult(ok=False, error="connection refused", backend="ollama"),
        },
    )
    out = mp.generate("hello")
    assert out["ok"] is False
    assert out["provider"] is None
    status = mp.status()
    assert status["provider_reachability"] == "FAILED"
    assert status["provider_last_error"] == "connection refused"


def test_provider_health_becomes_stale_without_claiming_current_readiness(
    tmp_path,
    monkeypatch,
):
    cfg = _config(ai_operator_primary_api_key=None)
    mp, _calls = _provider(
        tmp_path,
        cfg,
        monkeypatch,
        {"ollama": AIModelResult(ok=True, text="free", backend="ollama")},
    )
    assert mp.generate("hello")["ok"] is True
    mp._state["provider_health"]["local-fallback"]["checked_at_epoch"] = (
        time.time() - model_provider.PROVIDER_HEALTH_FRESH_SECONDS - 1
    )

    status = mp.status()

    assert status["provider_reachability"] == "STALE"
    assert status["provider_last_observed_reachability"] == "READY"
    assert status["provider_health_age_seconds"] > model_provider.PROVIDER_HEALTH_FRESH_SECONDS


def test_generate_can_limit_attempts_for_responsive_chat(tmp_path, monkeypatch):
    cfg = _config()
    mp, calls = _provider(
        tmp_path, cfg, monkeypatch,
        {
            "frontier_anthropic": AIModelResult(ok=False, error="read timed out", backend="frontier_anthropic"),
            "ollama": AIModelResult(ok=True, text="free answer", backend="ollama"),
        },
    )

    out = mp.generate("hello", request_timeout=0.5, max_attempts=1)

    assert out["ok"] is False
    assert out["provider"] is None
    assert calls == ["frontier_anthropic"]


def test_generate_can_bound_output_tokens_for_responsive_chat(tmp_path, monkeypatch):
    cfg = _config(ai_operator_primary_api_key=None, ai_operator_max_tokens=4000)
    captured = {}

    def fake_generate(self, prompt, system=None):  # noqa: ARG001
        captured["max_tokens"] = self.config.ai_model_max_tokens
        return AIModelResult(ok=True, text="short answer", backend="ollama")

    monkeypatch.setattr("cas_forex.model_provider.AIModelClient.generate", fake_generate)
    mp = ModelProvider(
        cfg,
        state_path=tmp_path / "state.json",
        events_path=tmp_path / "events.jsonl",
    )

    out = mp.generate("hello", max_output_tokens=512)

    assert out["ok"] is True
    assert captured["max_tokens"] == 512


def test_generate_bounds_structured_output_tokens_too(tmp_path, monkeypatch):
    cfg = _config(ai_operator_primary_api_key=None, ai_operator_max_tokens=4000)
    captured = {}

    def fake_generate(self, prompt, system=None, **kwargs):  # noqa: ARG001
        captured["max_tokens"] = self.config.ai_model_max_tokens
        captured["structured_max_tokens"] = (
            self.config.ai_model_structured_max_tokens
        )
        return AIModelResult(ok=True, text='{"summary":"ok"}', backend="ollama")

    monkeypatch.setattr("cas_forex.model_provider.AIModelClient.generate", fake_generate)
    mp = ModelProvider(
        cfg,
        state_path=tmp_path / "state.json",
        events_path=tmp_path / "events.jsonl",
    )

    out = mp.generate(
        "decide",
        max_output_tokens=384,
        response_format="json",
    )

    assert out["ok"] is True
    assert captured["max_tokens"] == 384
    assert captured["structured_max_tokens"] == 384


def test_structured_response_format_reaches_model_client(tmp_path, monkeypatch):
    cfg = _config(ai_operator_primary_api_key=None)
    captured = {}

    def fake_generate(self, prompt, system=None, **kwargs):  # noqa: ARG001
        captured.update(kwargs)
        return AIModelResult(ok=True, text='{"summary":"ok"}', backend="ollama")

    monkeypatch.setattr("cas_forex.model_provider.AIModelClient.generate", fake_generate)
    mp = ModelProvider(
        cfg,
        state_path=tmp_path / "state.json",
        events_path=tmp_path / "events.jsonl",
    )

    result = mp.generate("decide", response_format="json")

    assert result["ok"] is True
    assert captured["response_format"] == "json"


def test_status_does_not_wait_behind_in_flight_generate(tmp_path, monkeypatch):
    cfg = _config()
    started = threading.Event()
    release = threading.Event()

    def slow_generate(self, prompt, system=None):  # noqa: ARG001
        started.set()
        release.wait(timeout=1.0)
        return AIModelResult(ok=True, text="ok", backend="frontier_anthropic")

    monkeypatch.setattr("cas_forex.model_provider.AIModelClient.generate", slow_generate)
    mp = ModelProvider(
        cfg,
        state_path=tmp_path / "state.json",
        events_path=tmp_path / "events.jsonl",
        cooldown_seconds=900,
    )
    thread = threading.Thread(target=lambda: mp.generate("hello"), daemon=True)
    thread.start()
    assert started.wait(timeout=1.0)

    before = time.monotonic()
    status = mp.status()
    elapsed = time.monotonic() - before

    release.set()
    thread.join(timeout=1.0)
    assert status["report_kind"] == model_provider.REPORT_KIND
    assert elapsed < 0.25
    # This is the honest "no model available" — the trading loop is unaffected.
