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

SYSTEM_PROMPT = """You are the operator's instrument panel for CAS Forex — their personal forex trading system. The system trades on the operator's behalf autonomously through the agent cycle. The explicit purpose of that autonomy is to REMOVE detrimental trading psychology — anxiety-driven, emotional, in-the-moment decisions — from the operator's loop.

Your job is therefore very specific: help the operator UNDERSTAND what the system is doing and why. You are an educator and a window into the system's reasoning. You are NOT a trade advisor, NOT a trade picker, NOT an oracle to query for action.

When the operator asks a question, treat it as a request for explanation, not a request for a trade pick. Good responses:
- "Why did the agent trade EURUSD just now?" → call the cycle / event-journal / agent-memory capabilities and walk the decision chain.
- "How does the swing strategy work?" → pull from strategy-dev queue, walk-forward, leads; explain in plain language.
- "What's a runtime gate?" / "What does Stage 3 do?" → explain the concept; surface current state only if it directly answers the question.
- "What's the system doing right now?" → report the current cycle state from evidence (`cy` dry-run, `aw` autowake, `ml` daily learning).
- "How does the agent decide what to trade?" → walk through strategy-dev → walk-forward → PCBA → cycle from evidence.

When the operator asks "what should I trade?" / "should I take this trade?" / "is this a good entry?" / "what's hot right now?" — DO NOT pick a trade. Redirect: the agent cycle makes those decisions to keep the operator out of the emotional loop. Offer to explain the agent's most recent decision (`cy` cycle, `ml` daily rollup) or show the current cycle state.

Operational discipline:
- Plain text. No markdown headers, no tables, no emojis, no bullet trees. Two or three sentences plus the key numbers. If they want detail, they will ask.
- Surface real numbers from tool results. Do not paraphrase a verdict more favorably than the JSON says, and do not paraphrase it more pessimistically either.
- TRACEABILITY: name the capability key you used (e.g. `cy`, `mt`, `pp`) so the operator can rerun deterministically.
- Runtime gates are the OPERATOR's own settings. Mention them only when the operator asks OR Stage 3 validator REJECTs an initiated tool call. Do not lecture.
- Capabilities flagged `requires_confirm=True` prompt for explicit operator y/n. The harness handles this; do not bypass it.

Validator handling (Stage 3): if a tool result starts with `[cas-validator:REJECTED]`, name the gate and the next-action hint exactly as the validator stated, once, and stop. If `[cas-validator:DEGRADED]`, say so once and report the result anyway.
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


# ---------------------------------------------------------------------------
# Dry-run CLI — exercise the Stage 1→7 pipeline without an LLM call
# ---------------------------------------------------------------------------


DRY_RUN_HELP = (
    "Dry-run mode. Type a capability key (e.g. `cy`, `mt`, `pp`) optionally "
    "followed by a natural-language hint, or `menu`/`q`."
)


def _dry_run_render_commands(cap: BotCapability, state: BotState) -> List[str]:
    """Return the underlying command strings `execute_capability` would shell out.

    Pulled from `cap.commands` (the canonical deterministic dispatch surface)
    so the dry-run trace matches what Stage 4 would actually run. Falls back to
    a placeholder when the capability has no shell commands attached.
    """
    raw_commands = getattr(cap, "commands", None) or []
    rendered: List[str] = []
    for cmd in raw_commands:
        try:
            rendered.append(cmd.format(state=state))
        except Exception:
            rendered.append(str(cmd))
    return rendered


def run_dry_run_once(
    raw_input_line: str,
    state: BotState,
    *,
    runtime_gates: Optional[Mapping[str, Any]] = None,
    actually_execute: bool = False,
    confirm_callback: Optional[Any] = None,
    out: Any = None,
) -> Dict[str, Any]:
    """Run one dry-run turn for the given operator input line.

    Returns a dict describing every Stage trace fired so tests can assert on
    the pipeline without scraping stdout. `out` is the stream to print to;
    defaults to `sys.stdout` so production callers see human output.

    Pipeline mirrored:
      Stage 1 — echo input
      Stage 2 — synthetic LLM tool-selection trace
      Stage 3 — `validate_capability(cap, runtime_gates)` (the real validator)
      Stage 5 — operator confirmation prompt (if `cap.requires_confirm`)
      Stage 4 — render-or-execute underlying commands
      Stage 7 — synthetic LLM summary trace
    """
    stream = out if out is not None else sys.stdout

    def emit(line: str) -> None:
        print(line, file=stream)

    trace: Dict[str, Any] = {
        "input": raw_input_line,
        "key": None,
        "hint": None,
        "capability": None,
        "validation": None,
        "validator_rejected": False,
        "confirmation_required": False,
        "confirmed": None,
        "commands": [],
        "executed": False,
        "execution_success": None,
        "execution_output": None,
        "stages_run": [],
    }

    raw = raw_input_line.strip()
    if not raw:
        emit("[dry-run] empty input — nothing to trace.")
        return trace

    parts = raw.split(None, 1)
    key = parts[0]
    hint = parts[1] if len(parts) > 1 else None
    trace["key"] = key
    trace["hint"] = hint

    cap = find_capability(key)
    if cap is None:
        emit(f"[dry-run] Unknown capability key: `{key}`. Type `menu` for the list.")
        return trace
    trace["capability"] = cap

    # Stage 1 — echo
    trace["stages_run"].append(1)
    emit(f"[Stage 1] operator input: {raw}")
    if hint:
        emit(f"          natural-language hint: {hint}")

    # Stage 2 — synthetic LLM tool selection
    trace["stages_run"].append(2)
    tool_name = capability_tool_name(cap)
    emit(
        f"[Stage 2] LLM would select tool: `{tool_name}` "
        f"(`{cap.label}`, danger=`{cap.danger_level}`)"
    )

    # Stage 3 — CAS validator
    trace["stages_run"].append(3)
    validation = validate_capability(cap, runtime_gates)
    trace["validation"] = validation
    emit("[Stage 3] CAS validator:")
    emit(validation.structured_message)

    if validation.decision == DECISION_REJECT:
        trace["validator_rejected"] = True
        emit(
            "[dry-run] validator REJECTED — stopping before Stage 4. "
            "Real bot would feed `[cas-validator:REJECTED]` back to LLM for explanation."
        )
        return trace

    # Stage 5 — operator confirmation gate
    if cap.requires_confirm:
        trace["stages_run"].append(5)
        trace["confirmation_required"] = True
        emit(
            f"[Stage 5] real bot would prompt operator: Approve `{cap.key}`? [y/N]"
        )
        if actually_execute:
            cb = confirm_callback if confirm_callback is not None else _interactive_confirmation
            approved = bool(cb(cap))
            trace["confirmed"] = approved
            if not approved:
                emit("[dry-run] operator declined — stopping before Stage 4.")
                return trace
        else:
            emit(
                "[dry-run] confirmation gate NOT exercised (use --actually-execute to prompt for real)."
            )

    # Stage 4 — render or execute underlying commands
    trace["stages_run"].append(4)
    commands = _dry_run_render_commands(cap, state)
    trace["commands"] = commands
    emit("[Stage 4] underlying command(s) that would run:")
    if commands:
        for cmd in commands:
            emit(f"           $ {cmd}")
    else:
        emit("           (capability has no shell commands; runs Python dispatch path)")

    if actually_execute:
        emit("[Stage 4] --actually-execute passed; dispatching via execute_capability...")
        success, output = execute_capability(cap, state)
        trace["executed"] = True
        trace["execution_success"] = success
        trace["execution_output"] = output
        emit(f"[Stage 4] result success={success}")
        emit(output)
    else:
        emit("[Stage 4] commands NOT executed (dry-run). Pass --actually-execute to run.")

    # Stage 7 — synthetic LLM summary trace
    trace["stages_run"].append(7)
    emit("[Stage 7] real bot would feed result back to LLM for plain-English summary.")
    return trace


def run_dry_run_cli(
    *,
    api_base: str = "http://127.0.0.1:8765",
    mt5_path: Optional[str] = None,
    actually_execute: bool = False,
    runtime_gates_fetcher: Optional[Any] = None,
    input_fn: Optional[Any] = None,
    out: Any = None,
) -> None:
    """Interactive dry-run that traces Stages 1→7 without ever calling the LLM.

    No API key is required. The operator types `<key>` or `<key> <hint>`; the
    bot looks up the capability, runs the real CAS validator against fetched
    runtime gates, and prints what each stage WOULD do. With
    `actually_execute=True`, Stage 4 dispatches deterministically and Stage 5
    actually prompts the operator for `requires_confirm` capabilities.
    """
    _ensure_utf8_console()
    stream = out if out is not None else sys.stdout
    reader = input_fn if input_fn is not None else input

    bot_state = BotState()
    bot_state.api_base = api_base
    if mt5_path:
        bot_state.mt5_path = mt5_path

    if runtime_gates_fetcher is None:
        runtime_gates = fetch_runtime_gates(bot_state.api_base)
    else:
        runtime_gates = runtime_gates_fetcher()

    print("CAS Forex LLM Bot — DRY-RUN mode (no LLM call, no API key required).", file=stream)
    print(f"API base: {bot_state.api_base}", file=stream)
    print(
        f"Execution: {'LIVE (--actually-execute)' if actually_execute else 'TRACE ONLY'}",
        file=stream,
    )
    print(DRY_RUN_HELP, file=stream)
    print("", file=stream)

    while True:
        try:
            raw = reader("dry-run> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCAS Forex LLM Bot dry-run signing off.", file=stream)
            return
        if not raw:
            continue
        if raw.lower() in ("q", "quit", "exit"):
            print("CAS Forex LLM Bot dry-run signing off.", file=stream)
            return
        if raw.lower() in ("menu", "h", "help"):
            print(render_all_commands(), file=stream)
            continue

        run_dry_run_once(
            raw,
            bot_state,
            runtime_gates=runtime_gates,
            actually_execute=actually_execute,
            out=stream,
        )
        print("", file=stream)


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
