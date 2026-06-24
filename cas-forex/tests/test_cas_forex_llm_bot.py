"""Tests for the CAS Forex LLM bot — provider dispatch, tool registry, and
confirmation interception. The LLM is mocked; no live HTTP calls are made.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence

import pytest

from cas_forex.cas_forex_bot import BotCapability, BotState
from cas_forex import cas_forex_llm_bot as llm_bot
from cas_forex.cas_forex_llm_bot import (
    ANTHROPIC_API_KEY_ENV,
    AI_GATEWAY_KEY_ENV,
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    GatewayError,
    LLMConfig,
    PROVIDER_ANTHROPIC_DIRECT,
    PROVIDER_VERCEL_GATEWAY,
    build_tools_from_capabilities,
    call_gateway,
    capability_for_tool_name,
    capability_tool_name,
    execute_tool_call,
)


@dataclass
class FakeResponse:
    status_code: int
    body: Dict[str, Any]
    text: str = ""

    def json(self) -> Dict[str, Any]:
        return self.body


class FakeTransport:
    """Captures the last HTTP call and returns canned responses."""

    def __init__(self, responses: Sequence[FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, url: str, *, json: Mapping[str, Any], headers: Mapping[str, str], timeout: int) -> FakeResponse:
        self.calls.append({"url": url, "json": dict(json), "headers": dict(headers), "timeout": timeout})
        if not self._responses:
            raise AssertionError("FakeTransport ran out of responses")
        return self._responses.pop(0)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


def test_tools_cover_every_capability():
    tools = build_tools_from_capabilities()
    assert len(tools) == 31, f"expected 31 tools, got {len(tools)}"
    for tool in tools:
        assert tool["type"] == "function"
        fn = tool["function"]
        assert fn["name"].startswith("cas_forex_")
        assert fn["description"], "tool descriptions must be non-empty"
        params = fn["parameters"]
        assert params["type"] == "object"
        assert params["required"] == []


def test_tool_name_is_reversible_to_capability():
    sample = BotCapability(key="cy", group="workflow", label="cycle", description="run cycle")
    name = capability_tool_name(sample)
    assert capability_for_tool_name(name, [sample]) is sample


def test_tool_name_sanitizes_non_alnum_keys():
    cap = BotCapability(key="m-o", group="mt5", label="x", description="y")
    assert capability_tool_name(cap) == "cas_forex_m_o"


# ---------------------------------------------------------------------------
# Provider config
# ---------------------------------------------------------------------------


def test_default_provider_is_anthropic_direct(monkeypatch):
    monkeypatch.delenv("CAS_FOREX_LLM_PROVIDER", raising=False)
    monkeypatch.setenv(ANTHROPIC_API_KEY_ENV, "sk-test")
    monkeypatch.delenv(AI_GATEWAY_KEY_ENV, raising=False)
    cfg = LLMConfig.from_env()
    assert DEFAULT_PROVIDER == PROVIDER_ANTHROPIC_DIRECT
    assert cfg.provider == PROVIDER_ANTHROPIC_DIRECT
    assert cfg.model == DEFAULT_ANTHROPIC_MODEL
    assert cfg.api_key == "sk-test"
    assert cfg.required_key_env == ANTHROPIC_API_KEY_ENV


def test_explicit_vercel_gateway_uses_gateway_envs(monkeypatch):
    monkeypatch.delenv("CAS_FOREX_LLM_PROVIDER", raising=False)
    monkeypatch.setenv(AI_GATEWAY_KEY_ENV, "test-key")
    monkeypatch.delenv(ANTHROPIC_API_KEY_ENV, raising=False)
    cfg = LLMConfig.from_env(provider=PROVIDER_VERCEL_GATEWAY)
    assert cfg.provider == PROVIDER_VERCEL_GATEWAY
    assert cfg.model == DEFAULT_MODEL
    assert cfg.api_key == "test-key"
    assert cfg.required_key_env == AI_GATEWAY_KEY_ENV


def test_anthropic_direct_uses_anthropic_envs(monkeypatch):
    monkeypatch.setenv(ANTHROPIC_API_KEY_ENV, "sk-test")
    monkeypatch.delenv(AI_GATEWAY_KEY_ENV, raising=False)
    cfg = LLMConfig.from_env(provider=PROVIDER_ANTHROPIC_DIRECT)
    assert cfg.provider == PROVIDER_ANTHROPIC_DIRECT
    assert cfg.model == DEFAULT_ANTHROPIC_MODEL
    assert cfg.api_key == "sk-test"
    assert cfg.required_key_env == ANTHROPIC_API_KEY_ENV


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.delenv("CAS_FOREX_LLM_PROVIDER", raising=False)
    with pytest.raises(GatewayError):
        LLMConfig.from_env(provider="not-a-provider")


def test_missing_api_key_raises_on_call():
    cfg = LLMConfig(provider=PROVIDER_VERCEL_GATEWAY, api_key=None, model="x")
    with pytest.raises(GatewayError):
        call_gateway(messages=[], tools=[], config=cfg, transport=FakeTransport([]))


# ---------------------------------------------------------------------------
# Vercel Gateway adapter
# ---------------------------------------------------------------------------


def test_vercel_gateway_call_shape():
    transport = FakeTransport(
        [
            FakeResponse(
                status_code=200,
                body={
                    "choices": [
                        {"message": {"role": "assistant", "content": "hi from gateway"}}
                    ]
                },
            )
        ]
    )
    cfg = LLMConfig(provider=PROVIDER_VERCEL_GATEWAY, api_key="k", model="anthropic/claude-sonnet-4-6")
    msg = call_gateway(
        messages=[{"role": "user", "content": "ping"}],
        tools=build_tools_from_capabilities()[:2],
        config=cfg,
        transport=transport,
    )
    assert msg["content"] == "hi from gateway"
    call = transport.calls[0]
    assert call["url"].endswith("/chat/completions")
    assert call["headers"]["Authorization"] == "Bearer k"
    assert call["json"]["model"] == "anthropic/claude-sonnet-4-6"
    assert call["json"]["tool_choice"] == "auto"


# ---------------------------------------------------------------------------
# Anthropic-direct adapter
# ---------------------------------------------------------------------------


def test_anthropic_direct_call_shape_translates_messages_and_tools():
    transport = FakeTransport(
        [
            FakeResponse(
                status_code=200,
                body={
                    "id": "msg_1",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "hi from claude"}],
                },
            )
        ]
    )
    cfg = LLMConfig(
        provider=PROVIDER_ANTHROPIC_DIRECT,
        base_url="https://api.anthropic.com/v1",
        api_key="sk-test",
        model=DEFAULT_ANTHROPIC_MODEL,
    )
    msg = call_gateway(
        messages=[
            {"role": "system", "content": "You help."},
            {"role": "user", "content": "ping"},
        ],
        tools=build_tools_from_capabilities()[:1],
        config=cfg,
        transport=transport,
    )
    assert msg == {"role": "assistant", "content": "hi from claude"}
    call = transport.calls[0]
    assert call["url"].endswith("/messages")
    assert call["headers"]["x-api-key"] == "sk-test"
    assert call["headers"]["anthropic-version"]
    payload = call["json"]
    assert payload["model"] == DEFAULT_ANTHROPIC_MODEL
    assert payload["system"] == "You help."
    assert payload["messages"][0]["role"] == "user"
    assert payload["tools"][0]["name"].startswith("cas_forex_")
    assert payload["tools"][0]["input_schema"]["type"] == "object"


def test_anthropic_response_with_tool_use_is_normalized_to_tool_calls():
    transport = FakeTransport(
        [
            FakeResponse(
                status_code=200,
                body={
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "let me check"},
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "cas_forex_1",
                            "input": {},
                        },
                    ],
                },
            )
        ]
    )
    cfg = LLMConfig(
        provider=PROVIDER_ANTHROPIC_DIRECT,
        base_url="https://api.anthropic.com/v1",
        api_key="sk-test",
        model=DEFAULT_ANTHROPIC_MODEL,
    )
    msg = call_gateway(
        messages=[{"role": "user", "content": "status?"}],
        tools=build_tools_from_capabilities(),
        config=cfg,
        transport=transport,
    )
    assert msg["content"] == "let me check"
    assert msg["tool_calls"][0]["id"] == "toolu_1"
    assert msg["tool_calls"][0]["function"]["name"] == "cas_forex_1"
    assert msg["tool_calls"][0]["function"]["arguments"] == "{}"


# ---------------------------------------------------------------------------
# Tool execution + confirmation gate
# ---------------------------------------------------------------------------


def test_execute_tool_call_unknown_name_returns_failure():
    state = BotState()
    result = execute_tool_call(
        {"id": "x", "function": {"name": "cas_forex_does_not_exist"}},
        state,
    )
    assert result.success is False
    assert "Unknown capability tool" in result.output


def test_execute_tool_call_requires_confirm_without_callback_declines():
    state = BotState()
    confirm_cap = next(c for c in llm_bot.CAPABILITIES if c.requires_confirm)
    result = execute_tool_call(
        {"id": "x", "function": {"name": capability_tool_name(confirm_cap)}},
        state,
    )
    assert result.success is False
    assert result.intercepted_for_confirmation is True
    assert "requires operator confirmation" in result.output


def test_execute_tool_call_requires_confirm_with_callback_no_runs_nothing(monkeypatch):
    state = BotState()
    confirm_cap = next(c for c in llm_bot.CAPABILITIES if c.requires_confirm)
    monkeypatch.setattr(
        llm_bot, "execute_capability",
        lambda cap, st: pytest.fail("execute_capability must not run when operator declines"),
    )
    result = execute_tool_call(
        {"id": "x", "function": {"name": capability_tool_name(confirm_cap)}},
        state,
        confirmation_callback=lambda cap: False,
    )
    assert result.success is False
    assert result.intercepted_for_confirmation is True


def test_execute_tool_call_safe_capability_runs(monkeypatch):
    state = BotState()
    safe_cap = next(c for c in llm_bot.CAPABILITIES if not c.requires_confirm)
    captured: List[BotCapability] = []

    def fake_execute(cap, st):
        captured.append(cap)
        return True, "ok"

    monkeypatch.setattr(llm_bot, "execute_capability", fake_execute)
    result = execute_tool_call(
        {"id": "x", "function": {"name": capability_tool_name(safe_cap)}},
        state,
    )
    assert result.success is True
    assert captured == [safe_cap]


# ---------------------------------------------------------------------------
# Conversation step — happy path + tool round-trip
# ---------------------------------------------------------------------------


def test_step_conversation_executes_tool_then_returns_final_text(monkeypatch):
    safe_cap = next(c for c in llm_bot.CAPABILITIES if not c.requires_confirm)
    transport = FakeTransport(
        [
            FakeResponse(
                status_code=200,
                body={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": capability_tool_name(safe_cap),
                                            "arguments": "{}",
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
            ),
            FakeResponse(
                status_code=200,
                body={
                    "choices": [
                        {"message": {"role": "assistant", "content": "done"}}
                    ]
                },
            ),
        ]
    )
    monkeypatch.setattr(llm_bot, "execute_capability", lambda cap, st: (True, "tool ran"))

    cfg = LLMConfig(provider=PROVIDER_VERCEL_GATEWAY, api_key="k", model="m")
    convo = llm_bot.ConversationState(messages=[{"role": "user", "content": "status?"}])
    final = llm_bot.step_conversation(
        convo=convo,
        bot_state=BotState(),
        config=cfg,
        tools=build_tools_from_capabilities(),
        transport=transport,
        runtime_gates_fetcher=lambda: None,
    )
    assert final == "done"
    assert convo.last_tool_results[0].output == "tool ran"
    assert len(transport.calls) == 2


def test_execute_tool_call_validator_reject_blocks_dispatch(monkeypatch):
    """Stage 3 REJECT must short-circuit before Stage 4 deterministic dispatch."""
    state = BotState()
    dangerous_cap = BotCapability(
        key="LIVE",
        group="mt5",
        label="LIVE order",
        description="real money",
        danger_level="dangerous",
        requires_confirm=True,
    )

    def fake_execute(cap, st):
        pytest.fail("Stage 4 dispatch must not run after validator REJECT")

    monkeypatch.setattr(llm_bot, "execute_capability", fake_execute)
    monkeypatch.setattr(llm_bot, "capability_for_tool_name", lambda name: dangerous_cap)

    # All gates closed → validator rejects.
    runtime_gates = {
        "decisions": {
            gate: {"capability": gate, "authorized": False, "status": "CURRENTLY NOT LICENSED"}
            for gate in (
                "live_trading",
                "broker_accept",
                "auto_deposit",
                "bank_card_movement",
                "payout_automation",
            )
        }
    }

    result = llm_bot.execute_tool_call(
        {"id": "x", "function": {"name": "cas_forex_LIVE"}},
        state,
        runtime_gates=runtime_gates,
        confirmation_callback=lambda cap: pytest.fail("manual approval must not be asked when validator rejects"),
    )
    assert result.success is False
    assert result.intercepted_by_validator is True
    assert result.validation is not None
    assert result.validation.decision == "REJECT"
    assert "[cas-validator:REJECTED]" in result.output
    assert "live_trading" in result.output


def test_execute_tool_call_skip_validation_runs_dispatch(monkeypatch):
    """`skip_validation=True` bypasses Stage 3 — escape hatch for deterministic tests."""
    state = BotState()
    safe_cap = next(c for c in llm_bot.CAPABILITIES if not c.requires_confirm)
    monkeypatch.setattr(llm_bot, "execute_capability", lambda cap, st: (True, "ran without validator"))
    result = llm_bot.execute_tool_call(
        {"id": "x", "function": {"name": capability_tool_name(safe_cap)}},
        state,
        skip_validation=True,
    )
    assert result.success is True
    assert result.validation is None


def test_step_conversation_passes_runtime_gates_to_tool_dispatch(monkeypatch):
    """The fetched runtime gates from Stage 3 input must reach execute_tool_call."""
    safe_cap = next(c for c in llm_bot.CAPABILITIES if not c.requires_confirm)
    captured: List[Any] = []

    def fake_execute_tool_call(tool_call, state, *, runtime_gates=None, **kwargs):
        captured.append(runtime_gates)
        return llm_bot.ToolCallResult(
            tool_call_id=str(tool_call.get("id") or ""),
            name=str((tool_call.get("function") or {}).get("name") or ""),
            capability_key=safe_cap.key,
            output="ok",
            success=True,
        )

    monkeypatch.setattr(llm_bot, "execute_tool_call", fake_execute_tool_call)
    sentinel_gates = {"decisions": {}, "marker": "from-fetcher"}

    transport = FakeTransport(
        [
            FakeResponse(
                status_code=200,
                body={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": capability_tool_name(safe_cap),
                                            "arguments": "{}",
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
            ),
            FakeResponse(
                status_code=200,
                body={"choices": [{"message": {"role": "assistant", "content": "done"}}]},
            ),
        ]
    )
    cfg = LLMConfig(provider=PROVIDER_VERCEL_GATEWAY, api_key="k", model="m")
    convo = llm_bot.ConversationState(messages=[{"role": "user", "content": "go"}])
    final = llm_bot.step_conversation(
        convo=convo,
        bot_state=BotState(),
        config=cfg,
        tools=build_tools_from_capabilities()[:1],
        transport=transport,
        runtime_gates_fetcher=lambda: sentinel_gates,
    )
    assert final == "done"
    assert captured == [sentinel_gates]


def test_step_conversation_respects_round_cap(monkeypatch):
    safe_cap = next(c for c in llm_bot.CAPABILITIES if not c.requires_confirm)
    def loop_response():
        return FakeResponse(
            status_code=200,
            body={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "loop",
                                    "type": "function",
                                    "function": {
                                        "name": capability_tool_name(safe_cap),
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    transport = FakeTransport([loop_response() for _ in range(10)])
    monkeypatch.setattr(llm_bot, "execute_capability", lambda cap, st: (True, "loop"))
    cfg = LLMConfig(provider=PROVIDER_VERCEL_GATEWAY, api_key="k", model="m")
    convo = llm_bot.ConversationState(messages=[{"role": "user", "content": "spin"}])
    final = llm_bot.step_conversation(
        convo=convo,
        bot_state=BotState(),
        config=cfg,
        tools=build_tools_from_capabilities(),
        transport=transport,
        max_tool_rounds=2,
        runtime_gates_fetcher=lambda: None,
    )
    assert "tool-round cap" in final
