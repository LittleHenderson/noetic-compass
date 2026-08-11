"""CAS Forex AI model adapter (CAS Harness + PCBA controlled).

Attaches local/open-weight models and frontier LLM APIs to the cockpit for
research and evidence analysis. This adapter is not a direct execution path:

  - It may inform Operator/spec reasoning, but broker/provider side effects are
    handled by the owner-delegated Operator and guarded runtime paths.
  - It is controlled by CAS Harness + PCBA: prompt-injection checks run before
    calls and on returned text, and every response carries the authority
    boundary.
  - Frontier APIs require an owner-provided API key. No key => no call.

Supported backends:
  - ``ollama``: local open-weight server (e.g. deepseek-r1, qwen2.5).
  - ``openai_compatible``: vLLM / LM Studio / llama.cpp / OpenAI-compatible.
  - ``frontier_openai``: OpenAI-style /v1/chat/completions.
  - ``frontier_deepseek``: DeepSeek's OpenAI-compatible API.
  - ``frontier_anthropic``: Anthropic /v1/messages.
  - ``frontier_google``: Google Generative Language generateContent endpoint.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from cas_forex.pcba_prompt_injection import evaluate_pcba_prompt_injection

AI_AUTHORITY_BOUNDARY = (
    "Research/model adapter only, not a direct execution path. Autonomous "
    "trading and configured money movement belong to the owner-delegated "
    "Operator plus runtime_gates, dispatch/provider gates, receipts, and "
    "kill-switch checks."
)


@dataclass(frozen=True)
class AIModelStatus:
    enabled: bool
    backend: str
    model_name: str
    base_url: str
    configured: bool
    has_api_key: bool
    control_plane: str
    pcba_guard_enabled: bool
    context_window_tokens: int
    authority_boundary: str = AI_AUTHORITY_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "backend": self.backend,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "configured": self.configured,
            "has_api_key": self.has_api_key,
            "control_plane": self.control_plane,
            "pcba_guard_enabled": self.pcba_guard_enabled,
            "context_window_tokens": self.context_window_tokens,
            "authority_boundary": self.authority_boundary,
        }


@dataclass(frozen=True)
class AIModelResult:
    ok: bool
    text: str = ""
    error: str = ""
    model_name: str = ""
    backend: str = ""
    pcba_guard_verdict: str = "PASS"
    authority_boundary: str = AI_AUTHORITY_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "text": self.text,
            "error": self.error,
            "model_name": self.model_name,
            "backend": self.backend,
            "pcba_guard_verdict": self.pcba_guard_verdict,
            "authority_boundary": self.authority_boundary,
        }


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def model_status(config: Any = None) -> AIModelStatus:
    config = _resolve_config(config)
    backend = str(getattr(config, "ai_model_backend", "") or "")
    base_url = str(getattr(config, "ai_model_base_url", "") or "")
    enabled = bool(getattr(config, "ai_model_enabled", False))
    configured = enabled and bool(backend) and bool(base_url)
    return AIModelStatus(
        enabled=enabled,
        backend=backend,
        model_name=str(getattr(config, "ai_model_name", "") or ""),
        base_url=base_url,
        configured=configured,
        has_api_key=bool(getattr(config, "ai_model_api_key", None)),
        control_plane=str(getattr(config, "ai_model_control_plane", "CAS_HARNESS_PCBA") or "CAS_HARNESS_PCBA"),
        pcba_guard_enabled=bool(getattr(config, "ai_model_pcba_guard_enabled", True)),
        context_window_tokens=int(getattr(config, "ai_model_context_tokens", 16384) or 16384),
    )


_SYSTEM_PROMPT = (
    "You are the CAS Forex research assistant controlled by CAS Harness + PCBA. "
    "Analyze evidence and produce concise suggestions. This model adapter is "
    "not a direct execution path; autonomous trading and configured money "
    "movement belong to the owner-delegated Operator and guarded runtime "
    "dispatch/provider paths."
)


def _clean_model_text(value: Any) -> str:
    """Remove a stray non-English preamble emitted before an English answer."""
    text = str(value or "").strip()
    text = re.sub(r"(?is)^.*?<think>.*?</think>\s*", "", text).strip()
    lines = text.splitlines()
    if len(lines) < 2 or not any(ord(char) > 127 for char in lines[0]):
        return text

    remainder = "\n".join(lines[1:]).strip()
    if not remainder:
        return text
    printable = [char for char in remainder if not char.isspace()]
    ascii_ratio = (
        sum(ord(char) < 128 for char in printable) / len(printable)
        if printable
        else 0.0
    )
    return remainder if ascii_ratio >= 0.95 else text


def _clean_structured_model_text(value: Any) -> str:
    """Normalize one JSON fence, then require syntactically valid JSON.

    Some otherwise capable Ollama Cloud models wrap schema-constrained output
    in a single Markdown fence. Accepting that fence at the shared adapter is
    deterministic; accepting commentary or malformed JSON is not.
    """

    text = _clean_model_text(value)
    fenced = re.fullmatch(
        r"(?is)\x60{3}(?:json)?\s*(.*?)\s*\x60{3}",
        text,
    )
    if fenced:
        text = fenced.group(1).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, (dict, list)):
        raise ValueError("structured response must be a JSON object or array")
    return text


class AIModelClient:
    """Thin client for local/open-weight and frontier LLM backends."""

    def __init__(self, config: Any = None, timeout: float = 60.0):
        self.config = _resolve_config(config)
        self.timeout = timeout

    def status(self) -> AIModelStatus:
        return model_status(self.config)

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        *,
        response_format: str | Mapping[str, Any] | None = None,
    ) -> AIModelResult:
        status = self.status()
        if not status.enabled:
            return AIModelResult(ok=False, error="AI model disabled. Set AI_MODEL_ENABLED=true and configure a backend.")
        if not status.configured:
            return AIModelResult(ok=False, error="AI model not configured. Set AI_MODEL_BACKEND and AI_MODEL_BASE_URL.")
        if status.backend.lower().startswith("frontier_") and not status.has_api_key:
            return AIModelResult(
                ok=False,
                error="Frontier AI backend requires AI_MODEL_API_KEY.",
                model_name=status.model_name,
                backend=status.backend,
            )
        if status.pcba_guard_enabled:
            detected, patterns = evaluate_pcba_prompt_injection(prompt)
            if detected:
                return AIModelResult(
                    ok=False,
                    error=f"PCBA guard rejected prompt-injection surface: {', '.join(patterns)}",
                    model_name=status.model_name,
                    backend=status.backend,
                    pcba_guard_verdict="REJECT",
                )

        backend = status.backend.lower()
        try:
            if backend == "ollama":
                text = self._generate_ollama(
                    prompt,
                    system or _SYSTEM_PROMPT,
                    response_format=response_format,
                )
            elif backend in (
                "openai_compatible",
                "openai",
                "vllm",
                "frontier_openai",
                "frontier_deepseek",
            ):
                text = self._generate_openai_compatible(
                    prompt,
                    system or _SYSTEM_PROMPT,
                    response_format=response_format,
                )
            elif backend == "frontier_anthropic":
                text = self._generate_anthropic(prompt, system or _SYSTEM_PROMPT)
            elif backend == "frontier_google":
                text = self._generate_google(prompt, system or _SYSTEM_PROMPT)
            else:
                return AIModelResult(ok=False, error=f"Unknown AI backend: {status.backend}")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            return AIModelResult(
                ok=False,
                error=f"AI backend call failed: {exc}",
                model_name=status.model_name,
                backend=status.backend,
            )

        if status.pcba_guard_enabled:
            detected, patterns = evaluate_pcba_prompt_injection(text)
            if detected:
                return AIModelResult(
                    ok=False,
                    error=f"PCBA guard rejected model output surface: {', '.join(patterns)}",
                    model_name=status.model_name,
                    backend=status.backend,
                    pcba_guard_verdict="REJECT",
                )

        cleaned_text = _clean_model_text(text)
        if response_format is not None:
            try:
                cleaned_text = _clean_structured_model_text(text)
            except (json.JSONDecodeError, ValueError) as exc:
                return AIModelResult(
                    ok=False,
                    error=f"AI backend returned invalid structured JSON: {exc}",
                    model_name=status.model_name,
                    backend=status.backend,
                )

        return AIModelResult(
            ok=True,
            text=cleaned_text,
            model_name=status.model_name,
            backend=status.backend,
        )

    def _post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 (owner-configured URL)
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Ollama and compatible providers put the actionable cause in the
            # response body (for example, insufficient RAM/VRAM). Preserve that
            # detail instead of collapsing every failure to "HTTP Error 500".
            try:
                raw = exc.read().decode("utf-8", errors="replace").strip()
            except Exception:
                raw = ""
            detail = raw
            if raw:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, Mapping):
                        detail = str(
                            parsed.get("error")
                            or parsed.get("message")
                            or raw
                        ).strip()
                except json.JSONDecodeError:
                    pass
            raise ValueError(
                f"HTTP {exc.code}: {detail or exc.reason or 'provider request failed'}"
            ) from exc

    def _generate_ollama(
        self,
        prompt: str,
        system: str,
        *,
        response_format: str | Mapping[str, Any] | None = None,
    ) -> str:
        url = f"{self.config.ai_model_base_url.rstrip('/')}/api/chat"
        local_system = (
            f"{system}\nRespond only in concise English. Begin directly with the "
            "answer. Do not emit analysis, thinking tags, or a foreign-language preamble."
        )
        payload = {
            "model": self.config.ai_model_name,
            "messages": [{"role": "system", "content": local_system}, {"role": "user", "content": prompt}],
            "stream": False,
            # Reasoning models can otherwise spend the entire output budget in
            # an internal thinking field and return an empty visible answer.
            "think": False,
            # Avoid an 80+ second cold reload between bounded chat/decision calls.
            "keep_alive": "30m",
            "options": {
                "temperature": float(getattr(self.config, "ai_model_temperature", 0.2)),
                "num_predict": int(
                    getattr(
                        self.config,
                        (
                            "ai_model_structured_max_tokens"
                            if response_format is not None
                            else "ai_model_max_tokens"
                        ),
                        1024,
                    )
                    or 1024
                ),
                # Ollama otherwise defaults this workstation to 4096 tokens even
                # when the model advertises a much larger native context window.
                "num_ctx": int(
                    getattr(self.config, "ai_model_context_tokens", 16384) or 16384
                ),
            },
        }
        if response_format is not None:
            payload["format"] = (
                dict(response_format)
                if isinstance(response_format, Mapping)
                else str(response_format)
            )
        body = self._post_json(url, payload, {"Content-Type": "application/json"})
        return (body.get("message") or {}).get("content", "")

    def _generate_openai_compatible(
        self,
        prompt: str,
        system: str,
        *,
        response_format: str | Mapping[str, Any] | None = None,
    ) -> str:
        url = f"{self.config.ai_model_base_url.rstrip('/')}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        api_key = getattr(self.config, "ai_model_api_key", None)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": self.config.ai_model_name,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "temperature": float(getattr(self.config, "ai_model_temperature", 0.2)),
            "max_tokens": int(getattr(self.config, "ai_model_max_tokens", 1024)),
        }
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}
        elif isinstance(response_format, Mapping):
            # DeepSeek currently documents JSON-object output, not OpenAI's
            # provider-specific json_schema envelope. The exact schema remains
            # in the Operator prompt and CAS validates the returned object
            # before it can authorize any action.
            if str(getattr(self.config, "ai_model_backend", "")).lower() == "frontier_deepseek":
                payload["response_format"] = {"type": "json_object"}
            else:
                payload["response_format"] = dict(response_format)
        body = self._post_json(url, payload, headers)
        choices = body.get("choices") or []
        if not choices:
            return ""
        return (choices[0].get("message") or {}).get("content", "")

    def _generate_anthropic(self, prompt: str, system: str) -> str:
        # ``temperature`` is deprecated on the Claude 5 model family and returns
        # a 400 if sent, so it is omitted for the Anthropic backend. Structured/
        # reliable output comes from the system prompt, not the sampling temp.
        payload = {
            "model": self.config.ai_model_name,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(getattr(self.config, "ai_model_max_tokens", 1024)),
        }

        # Use Anthropic's SDK when it is installed. The Assistant already uses
        # this transport successfully, while urllib can intermittently fail on
        # this Windows/Python runtime during TLS record handling.
        try:
            import anthropic
        except ImportError:
            anthropic = None

        if anthropic is not None:
            try:
                try:
                    client = anthropic.Anthropic(
                        api_key=str(getattr(self.config, "ai_model_api_key", "")),
                        base_url=str(self.config.ai_model_base_url).rstrip("/"),
                        timeout=self.timeout,
                        max_retries=1,
                    )
                except TypeError:
                    # Keep lightweight test doubles and older SDKs compatible.
                    client = anthropic.Anthropic(
                        api_key=str(getattr(self.config, "ai_model_api_key", ""))
                    )
                response = client.messages.create(**payload)
                return "".join(
                    (
                        str(part.get("text") or "")
                        if isinstance(part, dict)
                        else str(getattr(part, "text", "") or "")
                    )
                    for part in (getattr(response, "content", None) or [])
                )
            except Exception as exc:
                raise OSError(
                    f"Anthropic SDK call failed: {type(exc).__name__}: {exc}"
                ) from exc

        url = f"{self.config.ai_model_base_url.rstrip('/')}/v1/messages"
        body = self._post_json(
            url,
            payload,
            {
                "Content-Type": "application/json",
                "x-api-key": str(getattr(self.config, "ai_model_api_key", "")),
                "anthropic-version": "2023-06-01",
            },
        )
        parts = body.get("content") or []
        return "".join(part.get("text", "") for part in parts if isinstance(part, dict))

    def _generate_google(self, prompt: str, system: str) -> str:
        api_key = str(getattr(self.config, "ai_model_api_key", ""))
        base = self.config.ai_model_base_url.rstrip("/")
        model = self.config.ai_model_name
        url = f"{base}/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": float(getattr(self.config, "ai_model_temperature", 0.2)),
                "maxOutputTokens": int(getattr(self.config, "ai_model_max_tokens", 1024)),
            },
        }
        body = self._post_json(url, payload, {"Content-Type": "application/json"})
        candidates = body.get("candidates") or []
        if not candidates:
            return ""
        parts = ((candidates[0].get("content") or {}).get("parts")) or []
        return "".join(part.get("text", "") for part in parts if isinstance(part, dict))
