"""CAS Forex AI model adapter (CAS Harness + PCBA controlled).

Attaches local/open-weight models and frontier LLM APIs to the cockpit for
research and evidence analysis. This adapter is intentionally advisory only:

  - It has NO authority to trade, create broker ACCEPT, deposit, move money, or
    automate payouts. Every real-money capability is gated separately in
    ``cas_forex.runtime_gates``.
  - It is controlled by CAS Harness + PCBA: prompt-injection checks run before
    calls and on returned text, and every response carries the authority
    boundary.
  - Frontier APIs require an owner-provided API key. No key => no call.

Supported backends:
  - ``ollama``: local open-weight server (e.g. llama3.1:70b-instruct, qwen2.5).
  - ``openai_compatible``: vLLM / LM Studio / llama.cpp / OpenAI-compatible.
  - ``frontier_openai``: OpenAI-style /v1/chat/completions.
  - ``frontier_anthropic``: Anthropic /v1/messages.
  - ``frontier_google``: Google Generative Language generateContent endpoint.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from cas_forex.pcba_prompt_injection import evaluate_pcba_prompt_injection

AI_AUTHORITY_BOUNDARY = (
    "Research/advisory only. This model cannot trade, create broker ACCEPT, "
    "deposit, move money, or automate payouts; all such capabilities are "
    "owner-controlled in runtime_gates and are unaffected by this model."
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
    )


_SYSTEM_PROMPT = (
    "You are the CAS Forex research assistant controlled by CAS Harness + PCBA. "
    "Analyze evidence and produce research-only suggestions. You have no "
    "authority to trade, create broker ACCEPT, deposit, move money, or automate "
    "payouts. Never claim that you do. Be concise and direct."
)


class AIModelClient:
    """Thin client for local/open-weight and frontier LLM backends."""

    def __init__(self, config: Any = None, timeout: float = 60.0):
        self.config = _resolve_config(config)
        self.timeout = timeout

    def status(self) -> AIModelStatus:
        return model_status(self.config)

    def generate(self, prompt: str, system: Optional[str] = None) -> AIModelResult:
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
                text = self._generate_ollama(prompt, system or _SYSTEM_PROMPT)
            elif backend in ("openai_compatible", "openai", "vllm", "frontier_openai"):
                text = self._generate_openai_compatible(prompt, system or _SYSTEM_PROMPT)
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

        return AIModelResult(ok=True, text=text, model_name=status.model_name, backend=status.backend)

    def _post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 (owner-configured URL)
            return json.loads(resp.read().decode("utf-8"))

    def _generate_ollama(self, prompt: str, system: str) -> str:
        url = f"{self.config.ai_model_base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.config.ai_model_name,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": float(getattr(self.config, "ai_model_temperature", 0.2)),
                "num_predict": int(getattr(self.config, "ai_model_max_tokens", 1024)),
            },
        }
        body = self._post_json(url, payload, {"Content-Type": "application/json"})
        return (body.get("message") or {}).get("content", "")

    def _generate_openai_compatible(self, prompt: str, system: str) -> str:
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
        body = self._post_json(url, payload, headers)
        choices = body.get("choices") or []
        if not choices:
            return ""
        return (choices[0].get("message") or {}).get("content", "")

    def _generate_anthropic(self, prompt: str, system: str) -> str:
        url = f"{self.config.ai_model_base_url.rstrip('/')}/v1/messages"
        # ``temperature`` is deprecated on the Claude 5 model family and returns
        # a 400 if sent, so it is omitted for the Anthropic backend. Structured/
        # reliable output comes from the system prompt, not the sampling temp.
        payload = {
            "model": self.config.ai_model_name,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(getattr(self.config, "ai_model_max_tokens", 1024)),
        }
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
