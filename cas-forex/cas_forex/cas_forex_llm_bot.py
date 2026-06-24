"""CAS Forex LLM Bot — natural-language operator interface.

LLM-first architecture: every operator input is routed to a frontier model.
The default provider is direct Anthropic Claude Sonnet 4.6 (`anthropic-direct`);
the Vercel AI Gateway path (`vercel-gateway`) is available as an explicit
alternative for multi-provider routing. The model is given the existing 31
CAS Forex capabilities as tool definitions and orchestrates calls into the
existing deterministic dispatch (`execute_capability`).

Design boundaries:
- The LLM is the OPERATOR INTERFACE, not the CAS reasoning spine. CAS-Native
  end-to-end work is unaffected; this bot only translates natural language
  into deterministic capability calls.
- Tool execution is auditable. Every model tool call resolves to one of the
  31 known BotCapability entries; nothing else can run.
- `requires_confirm=True` capabilities (MT5 demo orders) intercept before
  execution and hand back to the operator for explicit y/n confirmation.
- The Vercel AI Gateway speaks OpenAI-compatible chat-completions JSON; we
  call it with `requests` so no new SDK dependency is added.

Provider/model selection uses Gateway's plain `"provider/model"` strings so
the same code can switch between Anthropic, OpenAI, Google, etc. without
changing the call shape.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import requests

from cas_forex.cas_forex_bot import (
    CAPABILITIES,
    GROUPS,
    GROUP_ORDER,
    BotCapability,
    BotState,
    build_status_summary,
    execute_capability,
    find_capability,
    render_all_commands,
)
from cas_forex.cas_permission_validator import (
    DECISION_DEGRADED,
    DECISION_PASS,
    DECISION_REJECT,
    ValidationResult,
    fetch_runtime_gates,
    validate_capability,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

AI_GATEWAY_BASE_URL_ENV = "AI_GATEWAY_BASE_URL"
AI_GATEWAY_KEY_ENV = "AI_GATEWAY_API_KEY"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
ANTHROPIC_BASE_URL_ENV = "ANTHROPIC_BASE_URL"

DEFAULT_GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_ANTHROPIC_VERSION = "2023-06-01"

DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"

PROVIDER_VERCEL_GATEWAY = "vercel-gateway"
PROVIDER_ANTHROPIC_DIRECT = "anthropic-direct"
SUPPORTED_PROVIDERS = (PROVIDER_ANTHROPIC_DIRECT, PROVIDER_VERCEL_GATEWAY)

DEFAULT_PROVIDER = PROVIDER_ANTHROPIC_DIRECT

GATEWAY_REQUEST_TIMEOUT_SECONDS = 120

SYSTEM_PROMPT = """You are the CAS Forex operator agent. You help the operator run CAS Forex — a forex research, paper-trading, and MT5-demo-execution platform — by calling the right capability tool and reporting the result in plain English.

Operating boundaries (non-negotiable):
- `live_trading`, `broker_accept`, `auto_deposit`, `bank_card_movement`, and `payout_automation` are CURRENTLY NOT LICENSED. Never claim or imply they are operational.
- Capabilities marked as requiring confirmation (MT5 demo orders, anything that touches the broker) MUST NOT be invoked without an explicit operator-side y/n confirmation. The harness intercepts these for you.
- Surface real numbers and statuses. Do not paraphrase a verdict as more favorable than the JSON says.
- TRACEABILITY IS THE WHOLE PURPOSE: when reporting a result, name the capability key (e.g., `cy`, `mt`) you used so the operator can rerun deterministically.
- Be concise. Two or three short sentences plus the key numbers. The operator can ask for the full JSON if they want it.

Validator (Stage 3): every tool call passes through a CAS permission/risk validator before dispatch. If a tool result starts with `[cas-validator:REJECTED]`, that capability was blocked by a closed runtime gate — name the gate and the next-action hint to the operator instead of retrying. `[cas-validator:DEGRADED]` means the runtime-gates endpoint was unreachable; treat results with appropriate caution and recommend a health check.

When the operator asks an open-ended question ("how are we doing?", "anything wrong?"), choose 1-3 capabilities that answer it, call them, and summarize. Prefer `status` group capabilities for state questions, `workflow` for execution, `mt5` for terminal questions, `proof` for paper-proof maturity.
"""


# ---------------------------------------------------------------------------
# Tool registry — capabilities → OpenAI-format function tools
# ---------------------------------------------------------------------------


def capability_tool_name(cap: BotCapability) -> str:
    """Sanitize a capability key into an OpenAI function name."""
    safe_key = "".join(ch if ch.isalnum() else "_" for ch in cap.key)
    return f"cas_forex_{safe_key}"


def capability_tool_description(cap: BotCapability) -> str:
    parts = [f"[{cap.group}] {cap.label}", cap.description]
    if cap.requires_confirm:
        parts.append("Requires operator confirmation before execution.")
    if cap.danger_level == "dangerous":
        parts.append("DANGER: live/real-money path.")
    return " — ".join(parts)


def build_tools_from_capabilities(
    capabilities: Sequence[BotCapability] = CAPABILITIES,
) -> List[Dict[str, Any]]:
    """Return OpenAI/Gateway-compatible tool definitions for every capability."""
    tools: List[Dict[str, Any]] = []
    for cap in capabilities:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": capability_tool_name(cap),
                    "description": capability_tool_description(cap),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                },
            }
        )
    return tools


def capability_for_tool_name(
    name: str,
    capabilities: Sequence[BotCapability] = CAPABILITIES,
) -> Optional[BotCapability]:
    for cap in capabilities:
        if capability_tool_name(cap) == name:
            return cap
    return None


# ---------------------------------------------------------------------------
# Gateway client
# ---------------------------------------------------------------------------


@dataclass
class LLMConfig:
    provider: str = PROVIDER_VERCEL_GATEWAY
    base_url: str = DEFAULT_GATEWAY_BASE_URL
    api_key: Optional[str] = None
    model: str = DEFAULT_MODEL
    timeout_seconds: int = GATEWAY_REQUEST_TIMEOUT_SECONDS
    anthropic_version: str = DEFAULT_ANTHROPIC_VERSION

    @classmethod
    def from_env(
        cls,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> "LLMConfig":
        chosen = (provider or os.environ.get("CAS_FOREX_LLM_PROVIDER") or DEFAULT_PROVIDER).strip()
        if chosen not in SUPPORTED_PROVIDERS:
            raise GatewayError(
                f"Unknown LLM provider '{chosen}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}"
            )
        if chosen == PROVIDER_ANTHROPIC_DIRECT:
            return cls(
                provider=chosen,
                base_url=os.environ.get(ANTHROPIC_BASE_URL_ENV, DEFAULT_ANTHROPIC_BASE_URL).rstrip("/"),
                api_key=os.environ.get(ANTHROPIC_API_KEY_ENV),
                model=model or os.environ.get("CAS_FOREX_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL),
            )
        return cls(
            provider=chosen,
            base_url=os.environ.get(AI_GATEWAY_BASE_URL_ENV, DEFAULT_GATEWAY_BASE_URL).rstrip("/"),
            api_key=os.environ.get(AI_GATEWAY_KEY_ENV),
            model=model or os.environ.get("CAS_FOREX_LLM_MODEL", DEFAULT_MODEL),
        )

    @property
    def required_key_env(self) -> str:
        return (
            ANTHROPIC_API_KEY_ENV
            if self.provider == PROVIDER_ANTHROPIC_DIRECT
            else AI_GATEWAY_KEY_ENV
        )


# Backwards-compatible alias for older call sites/tests.
GatewayConfig = LLMConfig


class GatewayError(RuntimeError):
    pass


def _post(transport: Any, url: str, *, json_body: Mapping[str, Any], headers: Mapping[str, str], timeout: int) -> Any:
    poster = transport if transport is not None else requests.post
    return poster(url, json=dict(json_body), headers=dict(headers), timeout=timeout)


def _call_vercel_gateway(
    *,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]],
    config: LLMConfig,
    transport: Any = None,
) -> Dict[str, Any]:
    payload = {
        "model": config.model,
        "messages": list(messages),
        "tools": list(tools),
        "tool_choice": "auto",
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    response = _post(
        transport,
        f"{config.base_url}/chat/completions",
        json_body=payload,
        headers=headers,
        timeout=config.timeout_seconds,
    )
    if response.status_code >= 400:
        raise GatewayError(
            f"Gateway returned HTTP {response.status_code}: {response.text[:500]}"
        )
    body = response.json()
    choices = body.get("choices") or []
    if not choices:
        raise GatewayError(f"Gateway returned no choices: {body}")
    return dict(choices[0].get("message") or {})


def _openai_tools_to_anthropic(tools: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    converted: List[Dict[str, Any]] = []
    for tool in tools:
        function = tool.get("function") or {}
        converted.append(
            {
                "name": function.get("name"),
                "description": function.get("description") or "",
                "input_schema": function.get("parameters")
                or {"type": "object", "properties": {}, "required": []},
            }
        )
    return converted


def _openai_messages_to_anthropic(
    messages: Sequence[Mapping[str, Any]],
) -> tuple[str, List[Dict[str, Any]]]:
    """Return (system_text, anthropic_messages) for the Anthropic Messages API."""
    system_parts: List[str] = []
    anthropic_messages: List[Dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        if role == "system":
            content = msg.get("content")
            if isinstance(content, str) and content:
                system_parts.append(content)
            continue
        if role == "user":
            content = msg.get("content")
            anthropic_messages.append(
                {"role": "user", "content": content if isinstance(content, list) else [{"type": "text", "text": str(content or "")}]}
            )
            continue
        if role == "assistant":
            blocks: List[Dict[str, Any]] = []
            text = msg.get("content")
            if isinstance(text, str) and text:
                blocks.append({"type": "text", "text": text})
            for tool_call in msg.get("tool_calls") or []:
                fn = tool_call.get("function") or {}
                raw_args = fn.get("arguments")
                if isinstance(raw_args, str):
                    try:
                        parsed_args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        parsed_args = {}
                elif isinstance(raw_args, Mapping):
                    parsed_args = dict(raw_args)
                else:
                    parsed_args = {}
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": str(tool_call.get("id") or ""),
                        "name": str(fn.get("name") or ""),
                        "input": parsed_args,
                    }
                )
            anthropic_messages.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
            continue
        if role == "tool":
            anthropic_messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": str(msg.get("tool_call_id") or ""),
                            "content": str(msg.get("content") or ""),
                        }
                    ],
                }
            )
            continue
    return ("\n\n".join(system_parts), anthropic_messages)


def _anthropic_response_to_openai_message(body: Mapping[str, Any]) -> Dict[str, Any]:
    text_parts: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    for block in body.get("content") or []:
        block_type = block.get("type")
        if block_type == "text":
            text_parts.append(str(block.get("text") or ""))
        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "id": str(block.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(block.get("name") or ""),
                        "arguments": json.dumps(block.get("input") or {}),
                    },
                }
            )
    message: Dict[str, Any] = {"role": "assistant", "content": "".join(text_parts)}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def _call_anthropic_direct(
    *,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]],
    config: LLMConfig,
    transport: Any = None,
) -> Dict[str, Any]:
    system_text, anthropic_messages = _openai_messages_to_anthropic(messages)
    payload = {
        "model": config.model,
        "max_tokens": 4096,
        "messages": anthropic_messages,
        "tools": _openai_tools_to_anthropic(tools),
    }
    if system_text:
        payload["system"] = system_text
    headers = {
        "x-api-key": config.api_key,
        "anthropic-version": config.anthropic_version,
        "Content-Type": "application/json",
    }
    response = _post(
        transport,
        f"{config.base_url}/messages",
        json_body=payload,
        headers=headers,
        timeout=config.timeout_seconds,
    )
    if response.status_code >= 400:
        raise GatewayError(
            f"Anthropic returned HTTP {response.status_code}: {response.text[:500]}"
        )
    return _anthropic_response_to_openai_message(response.json())


def call_gateway(
    *,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]],
    config: LLMConfig,
    transport: Any = None,
) -> Dict[str, Any]:
    """Dispatch to the configured provider and return an OpenAI-shaped assistant message.

    All call sites consume a canonical OpenAI shape (`content`, optional `tool_calls`);
    provider-specific quirks are confined to `_call_*` adapters.
    """
    if not config.api_key:
        raise GatewayError(
            f"Missing {config.required_key_env}. Set it before running the LLM bot."
        )
    if config.provider == PROVIDER_ANTHROPIC_DIRECT:
        return _call_anthropic_direct(
            messages=messages, tools=tools, config=config, transport=transport
        )
    return _call_vercel_gateway(
        messages=messages, tools=tools, config=config, transport=transport
    )


# ---------------------------------------------------------------------------
# Tool dispatch — bridges LLM tool_calls to existing capability execution
# ---------------------------------------------------------------------------


@dataclass
class ToolCallResult:
    tool_call_id: str
    name: str
    capability_key: Optional[str]
    output: str
    success: bool
    intercepted_for_confirmation: bool = False
    intercepted_by_validator: bool = False
    validation: Optional[ValidationResult] = None


def execute_tool_call(
    tool_call: Mapping[str, Any],
    state: BotState,
    *,
    auto_confirm: bool = False,
    confirmation_callback: Optional[Any] = None,
    runtime_gates: Optional[Mapping[str, Any]] = None,
    skip_validation: bool = False,
) -> ToolCallResult:
    """Execute one LLM tool_call against the deterministic capability dispatch.

    Pipeline ordering (Stages 3-5 of the runtime):
      Stage 3: CAS permission/risk validator (`validate_capability`)
      Stage 4: deterministic capability dispatcher (`execute_capability`)
      Stage 5: manual approval gate (`confirmation_callback`)

    The validator runs FIRST so the operator is never asked to confirm a
    capability that CAS would refuse anyway. Validator REJECT is fed back to
    the model as a structured message and the capability does not execute.

    `runtime_gates` is injected here so a single fetch per LLM turn can be
    reused across multiple tool calls. When None and `skip_validation` is
    False, the validator routes through its DEGRADED path (safe/caution pass,
    dangerous reject).
    """
    tool_call_id = str(tool_call.get("id") or "")
    function = tool_call.get("function") or {}
    name = str(function.get("name") or "")
    cap = capability_for_tool_name(name)
    if cap is None:
        return ToolCallResult(
            tool_call_id=tool_call_id,
            name=name,
            capability_key=None,
            output=f"Unknown capability tool: {name}",
            success=False,
        )

    validation: Optional[ValidationResult] = None
    if not skip_validation:
        validation = validate_capability(cap, runtime_gates)
        if validation.decision == DECISION_REJECT:
            return ToolCallResult(
                tool_call_id=tool_call_id,
                name=name,
                capability_key=cap.key,
                output=validation.structured_message,
                success=False,
                intercepted_by_validator=True,
                validation=validation,
            )

    if cap.requires_confirm and not auto_confirm:
        if confirmation_callback is None:
            return ToolCallResult(
                tool_call_id=tool_call_id,
                name=name,
                capability_key=cap.key,
                output=(
                    f"Capability `{cap.key}` ({cap.label}) requires operator confirmation. "
                    f"No confirmation channel was provided; execution declined."
                ),
                success=False,
                intercepted_for_confirmation=True,
                validation=validation,
            )
        approved = bool(confirmation_callback(cap))
        if not approved:
            return ToolCallResult(
                tool_call_id=tool_call_id,
                name=name,
                capability_key=cap.key,
                output=f"Operator declined to run `{cap.key}` ({cap.label}).",
                success=False,
                intercepted_for_confirmation=True,
                validation=validation,
            )

    success, output = execute_capability(cap, state)
    return ToolCallResult(
        tool_call_id=tool_call_id,
        name=name,
        capability_key=cap.key,
        output=output,
        success=success,
        validation=validation,
    )


# ---------------------------------------------------------------------------
# Conversation runner
# ---------------------------------------------------------------------------


@dataclass
class ConversationState:
    messages: List[Dict[str, Any]] = field(default_factory=list)
    last_tool_results: List[ToolCallResult] = field(default_factory=list)


def initial_messages(state: BotState) -> List[Dict[str, Any]]:
    status_summary = build_status_summary(state)
    grounding = (
        "Operator session starting. Current status snapshot:\n"
        f"{status_summary}\n\n"
        "Capability groups available: "
        + ", ".join(f"{g} ({GROUPS[g]['name']})" for g in GROUP_ORDER)
        + "."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": grounding},
    ]


def step_conversation(
    *,
    convo: ConversationState,
    bot_state: BotState,
    config: GatewayConfig,
    tools: Sequence[Mapping[str, Any]],
    transport: Any = None,
    confirmation_callback: Optional[Any] = None,
    auto_confirm: bool = False,
    max_tool_rounds: int = 4,
    runtime_gates_fetcher: Optional[Any] = None,
) -> str:
    """Drive one operator turn: call the LLM, execute any tool calls, return final text.

    `max_tool_rounds` caps successive tool-use rounds so a runaway model can't
    spin indefinitely. Default 4 is enough for compose-and-summarize patterns.

    Runtime gates are fetched once at the start of the turn (Stage 3 validator
    input). `runtime_gates_fetcher` is injected for tests; production uses
    `fetch_runtime_gates(api_base)`. A None result is tolerated and routes the
    validator through its DEGRADED path.
    """
    if runtime_gates_fetcher is None:
        runtime_gates = fetch_runtime_gates(bot_state.api_base)
    else:
        runtime_gates = runtime_gates_fetcher()

    rounds = 0
    while True:
        assistant_message = call_gateway(
            messages=convo.messages,
            tools=tools,
            config=config,
            transport=transport,
        )
        convo.messages.append(assistant_message)
        tool_calls = assistant_message.get("tool_calls") or []
        if not tool_calls:
            return str(assistant_message.get("content") or "")

        rounds += 1
        if rounds > max_tool_rounds:
            stop_msg = (
                "[tool-round cap reached] Stopping further tool calls after "
                f"{max_tool_rounds} rounds."
            )
            convo.messages.append(
                {"role": "system", "content": stop_msg}
            )
            return stop_msg

        round_results: List[ToolCallResult] = []
        for tool_call in tool_calls:
            result = execute_tool_call(
                tool_call,
                bot_state,
                auto_confirm=auto_confirm,
                confirmation_callback=confirmation_callback,
                runtime_gates=runtime_gates,
            )
            round_results.append(result)
            convo.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": result.output[:8000],
                }
            )
        convo.last_tool_results = round_results


# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------


def _ensure_utf8_console() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None) if stream is not None else None
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _interactive_confirmation(cap: BotCapability) -> bool:
    print(
        f"\n[confirm] The model wants to run `{cap.key}` ({cap.label}).\n"
        f"          {cap.description}\n"
        f"          Approve? [y/N]: ",
        end="",
        flush=True,
    )
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


def run_llm_bot_cli(
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_base: str = "http://127.0.0.1:8765",
    mt5_path: Optional[str] = None,
) -> None:
    """Interactive natural-language CLI backed by the configured LLM provider."""
    _ensure_utf8_console()
    try:
        config = LLMConfig.from_env(provider=provider, model=model)
    except GatewayError as exc:
        print(f"[error] {exc}")
        return
    if not config.api_key:
        print(
            f"[error] {config.required_key_env} is not set. Configure it before launching the LLM bot."
        )
        hint = (
            "https://console.anthropic.com/"
            if config.provider == PROVIDER_ANTHROPIC_DIRECT
            else "https://vercel.com/dashboard"
        )
        print(
            f"        Hint: get a key from {hint} then "
            f"`$env:{config.required_key_env}='...'` in PowerShell."
        )
        return

    bot_state = BotState()
    bot_state.api_base = api_base
    if mt5_path:
        bot_state.mt5_path = mt5_path

    tools = build_tools_from_capabilities()
    convo = ConversationState(messages=initial_messages(bot_state))

    print("CAS Forex LLM Bot — natural-language operator interface.")
    print(f"Provider: {config.provider}  |  Base: {config.base_url}")
    print(f"Model: {config.model}  |  Tools: {len(tools)} capabilities")
    print(f"API: {bot_state.api_base}")
    print("Type 'menu' for the deterministic menu, 'q' to quit.\n")

    while True:
        try:
            raw = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCAS Forex LLM Bot signing off.")
            return

        if not raw:
            continue
        if raw.lower() in ("q", "quit", "exit"):
            print("CAS Forex LLM Bot signing off.")
            return
        if raw.lower() in ("menu", "h", "help"):
            print(render_all_commands())
            continue

        convo.messages.append({"role": "user", "content": raw})
        try:
            reply = step_conversation(
                convo=convo,
                bot_state=bot_state,
                config=config,
                tools=tools,
                confirmation_callback=_interactive_confirmation,
            )
        except GatewayError as exc:
            print(f"[gateway error] {exc}")
            continue
        except Exception as exc:  # noqa: BLE001 — surface anything else to operator
            print(f"[bot error] {exc}")
            continue

        print(f"\nbot> {reply}\n")
