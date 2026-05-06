"""Tests for the Tier 3 provider abstraction (Claude + Gemini)."""

from __future__ import annotations

import asyncio
import importlib.util as _importlib_util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROVIDERS_PATH = _REPO_ROOT / "cas-synthetic" / "scripts" / "tier3_providers.py"
_GENERATOR_PATH = _REPO_ROOT / "cas-synthetic" / "scripts" / "generate_tier3_dialogue_v1.py"


def _load(mod_name: str, path: Path):
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = _importlib_util.spec_from_file_location(mod_name, path)
    module = _importlib_util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


providers = _load("_test_tier3_providers", _PROVIDERS_PATH)


class _FakeCostTracker:
    """Async cost tracker stub that records calls and respects a cap."""

    def __init__(self, cap_usd: float = 1000.0) -> None:
        self.cap_usd = float(cap_usd)
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0
        self.aborted = False

    async def add(self, in_tokens: int, out_tokens: int) -> bool:
        self.input_tokens += int(in_tokens)
        self.output_tokens += int(out_tokens)
        self.calls += 1
        # Toy cost model — assume 1 input + 1 output token cost = $0.001 each
        spent = (self.input_tokens + self.output_tokens) * 0.001
        if spent > self.cap_usd:
            self.aborted = True
            return False
        return True


# ---------------------------------------------------------------------------
# Claude provider
# ---------------------------------------------------------------------------

class _FakeAnthropicClient:
    def __init__(self, response_text: str = "ok response") -> None:
        self.response_text = response_text
        self.messages = SimpleNamespace(create=AsyncMock())
        # Default success response
        resp = SimpleNamespace(
            content=[SimpleNamespace(text=response_text, type="text")],
            usage=SimpleNamespace(input_tokens=12, output_tokens=34),
        )
        self.messages.create.return_value = resp


def test_claude_provider_happy_path():
    client = _FakeAnthropicClient()
    p = providers.ClaudeBatchDialogueProvider(client=client)
    assert p.name == "claude"
    tracker = _FakeCostTracker()
    result = asyncio.run(p.call(
        system_prompt="sys", user_message="hi", model="claude-test",
        cost_tracker=tracker, max_output_tokens=50, temperature=0.5,
    ))
    assert result.error_reason is None
    assert result.text == "ok response"
    assert result.input_tokens == 12
    assert result.output_tokens == 34
    assert tracker.input_tokens == 12
    assert tracker.output_tokens == 34


def test_claude_provider_cost_cap_aborts():
    client = _FakeAnthropicClient()
    p = providers.ClaudeBatchDialogueProvider(client=client)
    # Cap so tight that even one call breaks it
    tracker = _FakeCostTracker(cap_usd=0.001)
    result = asyncio.run(p.call(
        system_prompt="sys", user_message="hi", model="claude-test",
        cost_tracker=tracker, max_output_tokens=50, temperature=0.0,
    ))
    assert result.error_reason == "cost_cap_exceeded"
    assert tracker.aborted is True


def test_claude_provider_manifest_block():
    p = providers.ClaudeBatchDialogueProvider(
        client=_FakeAnthropicClient(),
        primary_model="custom-primary",
        fallback_model="custom-fallback",
    )
    block = p.manifest_block()
    assert block["provider"] == "claude"
    assert block["primary_model"] == "custom-primary"
    assert block["fallback_model"] == "custom-fallback"
    assert block["price_per_m_input_usd"] == providers.CLAUDE_PRICE_PER_M_INPUT
    assert block["price_per_m_output_usd"] == providers.CLAUDE_PRICE_PER_M_OUTPUT


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class _FakeGeminiResponse:
    def __init__(self, text: str = "gemini reply", in_tokens: int = 20, out_tokens: int = 40) -> None:
        self.text = text
        self.usage_metadata = SimpleNamespace(
            prompt_token_count=in_tokens,
            candidates_token_count=out_tokens,
        )


class _FakeGeminiModel:
    def __init__(self, model_name: str, response: _FakeGeminiResponse | None = None) -> None:
        self.model_name = model_name
        self.response = response or _FakeGeminiResponse()
        self.generate_content_async = AsyncMock(return_value=self.response)


def test_gemini_provider_happy_path():
    """Inject a fake client_factory so no real google.generativeai SDK is touched."""
    factory_calls: list[str] = []

    def factory(model_name: str) -> _FakeGeminiModel:
        factory_calls.append(model_name)
        return _FakeGeminiModel(model_name)

    p = providers.GeminiBatchDialogueProvider(client_factory=factory)
    assert p.name == "gemini"
    tracker = _FakeCostTracker()
    result = asyncio.run(p.call(
        system_prompt="sys", user_message="hi", model="gemini-2.5-flash-lite",
        cost_tracker=tracker, max_output_tokens=50, temperature=0.5,
    ))
    assert result.error_reason is None
    assert result.text == "gemini reply"
    assert result.input_tokens == 20
    assert result.output_tokens == 40
    assert factory_calls == ["gemini-2.5-flash-lite"]
    assert tracker.input_tokens == 20


def test_gemini_provider_manifest_block_default_pricing():
    p = providers.GeminiBatchDialogueProvider(client_factory=lambda m: _FakeGeminiModel(m))
    block = p.manifest_block()
    assert block["provider"] == "gemini"
    assert block["primary_model"] == providers.GEMINI_DEFAULT_PRIMARY
    assert block["price_per_m_input_usd"] == providers.GEMINI_FLASH_LITE_PRICE_PER_M_INPUT
    assert block["price_per_m_output_usd"] == providers.GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT


def test_gemini_pricing_is_strictly_cheaper_than_claude():
    """Sanity-check: the bakeoff incentive (much cheaper) must hold."""
    assert providers.GEMINI_FLASH_LITE_PRICE_PER_M_INPUT < providers.CLAUDE_PRICE_PER_M_INPUT
    assert providers.GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT < providers.CLAUDE_PRICE_PER_M_OUTPUT
    # Batch is even cheaper than non-batch.
    assert providers.GEMINI_FLASH_LITE_BATCH_PRICE_PER_M_INPUT < providers.GEMINI_FLASH_LITE_PRICE_PER_M_INPUT


def test_gemini_provider_404_swap_signal():
    """A 404-style error must surface as api_status_404 so orchestration
    can swap to fallback model. Uses a Mock that raises a 404-flavored
    error on the first call."""
    raised = {"count": 0}

    class _Boom(Exception):
        pass

    async def bad_generate(*_a, **_k):
        raised["count"] += 1
        raise _Boom("model not found 404")

    fake_model = _FakeGeminiModel("gemini-2.5-flash-lite")
    fake_model.generate_content_async = bad_generate

    p = providers.GeminiBatchDialogueProvider(
        client_factory=lambda m: fake_model,
        max_retries=1,
    )
    tracker = _FakeCostTracker()
    result = asyncio.run(p.call(
        system_prompt="sys", user_message="hi", model="gemini-2.5-flash-lite",
        cost_tracker=tracker, max_output_tokens=50, temperature=0.0,
    ))
    assert result.error_reason == "api_status_404"
    assert raised["count"] == 1


# ---------------------------------------------------------------------------
# make_provider factory
# ---------------------------------------------------------------------------

def test_make_provider_unknown_name_raises():
    with pytest.raises(ValueError):
        providers.make_provider("openai", api_key="x")


def test_make_provider_claude_with_injected_client_no_sdk_required():
    """Tests can build a Claude provider via injected client without
    needing the anthropic SDK to perform an import path."""
    p = providers.make_provider("claude", client=_FakeAnthropicClient())
    assert isinstance(p, providers.ClaudeBatchDialogueProvider)


def test_make_provider_gemini_with_injected_factory():
    p = providers.make_provider(
        "gemini",
        client_factory=lambda m: _FakeGeminiModel(m),
    )
    assert isinstance(p, providers.GeminiBatchDialogueProvider)


def test_make_provider_gemini_batch_pricing_flag():
    p = providers.make_provider(
        "gemini",
        client_factory=lambda m: _FakeGeminiModel(m),
        use_batch_pricing=True,
    )
    assert p.price_per_m_input == providers.GEMINI_FLASH_LITE_BATCH_PRICE_PER_M_INPUT
    assert p.price_per_m_output == providers.GEMINI_FLASH_LITE_BATCH_PRICE_PER_M_OUTPUT


# ---------------------------------------------------------------------------
# load_gemini_api_key
# ---------------------------------------------------------------------------

def test_load_gemini_api_key_from_env(monkeypatch):
    monkeypatch.setenv("NC_GEMINI_API_KEY", "  test_key_value  ")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert providers.load_gemini_api_key(None) == "test_key_value"


def test_load_gemini_api_key_missing(monkeypatch):
    monkeypatch.delenv("NC_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert providers.load_gemini_api_key(None) is None


def test_load_gemini_api_key_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("NC_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "OTHER=abc\n"
        'GEMINI_API_KEY="loaded_from_file"\n',
        encoding="utf-8",
    )
    assert providers.load_gemini_api_key(env_file) == "loaded_from_file"


# ---------------------------------------------------------------------------
# Generator integration: --provider flag is honored, default is claude,
# manifest records provider/model/pricing
# ---------------------------------------------------------------------------

def test_generator_default_provider_is_claude():
    """Loading the generator's parser should default --provider to claude."""
    generator = _load("_test_tier3_generator_pflag", _GENERATOR_PATH)
    args = generator.parse_args([
        "--dry-run",
        "--target-records", "1",
        "--out-prefix", "tmp/_unused",
        "--manifest", "tmp/_unused.json",
    ])
    assert args.provider == "claude"
    assert generator.DEFAULT_PROVIDER == "claude"
    assert "claude" in generator.SUPPORTED_PROVIDERS
    assert "gemini" in generator.SUPPORTED_PROVIDERS


def test_generator_provider_flag_routes_to_gemini_in_dry_run(tmp_path):
    """A dry-run with --provider gemini writes a manifest tagged gemini.
    Dry-run never touches the SDK, so this verifies the flag plumbing."""
    generator = _load("_test_tier3_generator_dryrun", _GENERATOR_PATH)
    out_prefix = tmp_path / "shard"
    manifest = tmp_path / "manifest.json"
    rc = generator.main([
        "--dry-run",
        "--target-records", "5",
        "--records-per-shard", "5",
        "--concurrency", "1",
        "--out-prefix", str(out_prefix),
        "--manifest", str(manifest),
        "--no-resume",
        "--provider", "gemini",
    ])
    assert rc == 0
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["provider"] == "gemini"
    assert payload["primary_model"] == providers.GEMINI_DEFAULT_PRIMARY
    assert payload["fallback_model"] == providers.GEMINI_DEFAULT_FALLBACK
    assert payload["price_per_m_input_usd"] == providers.GEMINI_FLASH_LITE_PRICE_PER_M_INPUT
    assert payload["price_per_m_output_usd"] == providers.GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT


def test_provider_cost_tracker_uses_provider_pricing():
    """The Tier 3 cost tracker must charge tokens at the provider's actual
    rate, not Claude's. This is the bakeoff fix that prevents 30x
    over-reporting on Gemini runs (and false cost-cap aborts)."""
    tracker = providers.ProviderCostTracker(
        hard_cap_usd=10.0,
        price_per_m_input=providers.GEMINI_FLASH_LITE_PRICE_PER_M_INPUT,
        price_per_m_output=providers.GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT,
    )
    # 100K input + 50K output tokens
    asyncio.run(tracker.add(100_000, 50_000))
    expected = (
        100_000 * providers.GEMINI_FLASH_LITE_PRICE_PER_M_INPUT / 1_000_000.0
        + 50_000 * providers.GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT / 1_000_000.0
    )
    assert abs(tracker.total_usd - expected) < 1e-9
    # Should be much less than the same volume at Claude pricing
    claude_cost = (
        100_000 * providers.CLAUDE_PRICE_PER_M_INPUT / 1_000_000.0
        + 50_000 * providers.CLAUDE_PRICE_PER_M_OUTPUT / 1_000_000.0
    )
    assert tracker.total_usd < claude_cost * 0.1  # at least 10x cheaper


def test_provider_cost_tracker_aborts_when_cap_exceeded():
    tracker = providers.ProviderCostTracker(
        hard_cap_usd=0.0001,
        price_per_m_input=providers.CLAUDE_PRICE_PER_M_INPUT,
        price_per_m_output=providers.CLAUDE_PRICE_PER_M_OUTPUT,
    )
    ok = asyncio.run(tracker.add(1000, 1000))
    assert ok is False
    assert tracker.aborted is True


def test_validation_retry_path_uses_provider_not_legacy_client():
    """Regression test for the bakeoff bug: when a turn fails validation,
    the lower-temperature retry must call ctx.provider, not the legacy
    ctx.client.messages.create path. With ctx.client=None (Gemini case),
    the legacy path raises AttributeError(NoneType.messages); the
    provider path produces an honest failure_counter entry instead."""
    generator = _load("_test_tier3_generator_retry_path", _GENERATOR_PATH)
    src = (Path(_GENERATOR_PATH).read_text(encoding="utf-8"))
    # The retry block must branch on ctx.provider before calling
    # call_claude_dialogue. If anyone reverts the fix, the literal
    # ``ctx.provider is not None`` guard around the retry call should
    # be present right before the ``call_dialogue`` block.
    retry_block_start = src.find("# One lower-temperature retry for validation failures.")
    assert retry_block_start > 0, "retry block comment should exist"
    retry_window = src[retry_block_start: retry_block_start + 1000]
    assert "ctx.provider is not None" in retry_window, (
        "retry-after-validation block must guard on ctx.provider before "
        "calling the legacy claude path"
    )
    assert "call_dialogue(" in retry_window, (
        "retry block must call provider-aware call_dialogue"
    )


def test_generator_validator_unchanged_for_gemini_path(tmp_path):
    """The reply validator behavior must NOT be provider-dependent.
    The dry-run write goes through the same validator as the live path."""
    generator = _load("_test_tier3_generator_validator", _GENERATOR_PATH)
    out_prefix = tmp_path / "shard"
    manifest = tmp_path / "manifest.json"
    rc = generator.main([
        "--dry-run",
        "--target-records", "5",
        "--records-per-shard", "5",
        "--concurrency", "1",
        "--out-prefix", str(out_prefix),
        "--manifest", str(manifest),
        "--no-resume",
        "--provider", "gemini",
    ])
    assert rc == 0
    # All dry-run records pass the validator (their replies are static safe).
    shards = list(tmp_path.glob("shard*.jsonl"))
    assert shards, "expected at least one shard"
    for shard in shards:
        for line in shard.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            assert "validator_pass" in rec
            assert "validator_reasons" in rec
