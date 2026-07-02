"""Tests for the LLM failover layer (cas_forex/model_provider.py).

The load-bearing invariant: when the PAID primary (Claude) runs out of budget or
reports a credit error, the chain fails over to the FREE fallback automatically,
records the switch, and flips back to the primary once the owner tops up.
"""

from __future__ import annotations

from types import SimpleNamespace

from cas_forex import model_provider
from cas_forex.ai_model import AIModelResult
from cas_forex.model_provider import ModelProvider, build_provider_chain


def _config(**over):
    base = dict(
        ai_operator_primary_api_key="sk-test-key",
        ai_operator_primary_backend="frontier_anthropic",
        ai_operator_primary_model="claude-test",
        ai_operator_primary_base_url="https://api.anthropic.com",
        ai_operator_token_budget=0,
        ai_model_backend="ollama",
        ai_model_name="llama-test",
        ai_model_base_url="http://127.0.0.1:11434",
        ai_model_api_key=None,
        ai_model_max_tokens=256,
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
    # This is the honest "no model available" — the trading loop is unaffected.
