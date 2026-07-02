"""Multi-provider LLM failover for the CAS Forex AI operator.

Owner concern (2026-07-02): frontier AI (Claude) costs tokens. This layer keeps
a PAID primary provider (Claude via the Anthropic API) and one or more FREE
fallbacks (a local Ollama server is fully free; an optional OpenAI-compatible
free endpoint can follow). When the paid primary runs out of its owner-set token
budget, or the provider reports a credit / rate / auth error, the chain fails
over to the next free provider automatically and records the switch so the UI
can show it. When the owner tops the paid budget back up (or a cooldown lapses),
the chain flips back to the primary on the next call.

Boundary: this module only decides WHICH language model answers the operator's
questions. It never trades, moves money, mints edge tokens, creates owner/broker
ACCEPT, or authorizes live trading. The trading engine is local math and does
not depend on any of this.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from cas_forex.ai_model import AIModelClient, AIModelResult
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "model-provider-state.json"
DEFAULT_EVENTS_PATH = REPO_ROOT / "runtime" / "model-provider-events.jsonl"

REPORT_KIND = "cas_forex_model_provider"

# After the paid primary fails on a credit/budget/auth error, do not retry it on
# every tick — wait out a cooldown so a token-less primary cannot burn the loop.
DEFAULT_PRIMARY_COOLDOWN_SECONDS = 900

# Rough token estimate (chars/4) — a budget meter, not billing. The owner tops
# the budget up from the app; this only decides when to fail over to free.
_CHARS_PER_TOKEN = 4

_CREDIT_ERROR_MARKERS = (
    "credit",
    "quota",
    "billing",
    "insufficient",
    "payment",
    "rate limit",
    "rate_limit",
    "429",
    "401",
    "403",
    "invalid x-api-key",
    "authentication",
    "overloaded",
    "529",
)

CLAIM_BOUNDARY = (
    "Model provider failover only selects which language model answers the AI "
    "operator. It never trades, places orders, moves money, mints edge tokens, "
    "creates owner/broker ACCEPT, or authorizes live trading."
)


@dataclass(frozen=True)
class ProviderSpec:
    """One rung of the failover ladder."""

    name: str  # short id shown in the UI (e.g. "claude", "local-ollama")
    label: str  # human label (e.g. "Claude (Anthropic API)")
    backend: str  # ai_model backend id (frontier_anthropic / ollama / openai_compatible / ...)
    model_name: str
    base_url: str
    api_key: Optional[str]
    paid: bool  # True => consumes the owner token budget
    free_note: str = ""  # UI note, e.g. "local, fully free"


class _ProviderConfigView:
    """Read-only view of the base config with this provider's ai_model_* fields
    overridden, so the existing :class:`AIModelClient` can drive any provider."""

    def __init__(self, base_config: Any, spec: ProviderSpec):
        self._base = base_config
        self._overrides = {
            "ai_model_enabled": True,
            "ai_model_backend": spec.backend,
            "ai_model_name": spec.model_name,
            "ai_model_base_url": spec.base_url,
            "ai_model_api_key": spec.api_key,
            # Operator calls need room for extended-thinking models: the JSON
            # answer follows the thinking budget, so use the operator ceiling.
            "ai_model_max_tokens": int(
                getattr(base_config, "ai_operator_max_tokens", 4000) or 4000
            ),
        }

    def __getattr__(self, item: str) -> Any:
        if item in self._overrides:
            return self._overrides[item]
        return getattr(self._base, item)


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def _is_credit_error(error: str) -> bool:
    low = (error or "").lower()
    return any(marker in low for marker in _CREDIT_ERROR_MARKERS)


def build_provider_chain(config: Any = None) -> list[ProviderSpec]:
    """Ordered failover ladder from config. Primary (paid) first, then free."""
    config = _resolve_config(config)
    chain: list[ProviderSpec] = []

    # Key resolution order: an in-app key the owner pasted (durable, git-ignored
    # secret store) wins, then config/env. This makes an in-app key take effect
    # on the next call with no restart.
    try:
        from cas_forex.operator_secrets import get_secret

        stored_key = get_secret("primary_api_key")
    except Exception:
        stored_key = None
    primary_key = (
        stored_key
        or getattr(config, "ai_operator_primary_api_key", None)
        or os.environ.get("ANTHROPIC_API_KEY")
        or None
    )
    primary_backend = str(getattr(config, "ai_operator_primary_backend", "frontier_anthropic") or "frontier_anthropic")
    # Only offer the paid primary when it actually has a key — otherwise the free
    # fallback is the honest active provider from the start.
    if primary_key:
        chain.append(
            ProviderSpec(
                name="claude",
                label="Claude (Anthropic API)",
                backend=primary_backend,
                model_name=str(getattr(config, "ai_operator_primary_model", "claude-sonnet-5") or "claude-sonnet-5"),
                base_url=str(getattr(config, "ai_operator_primary_base_url", "https://api.anthropic.com") or "https://api.anthropic.com"),
                api_key=primary_key,
                paid=True,
                free_note="paid — consumes your token budget",
            )
        )

    # Free local fallback: the existing ai_model_* config (Ollama by default).
    fallback_backend = str(getattr(config, "ai_model_backend", "ollama") or "ollama")
    if fallback_backend:
        chain.append(
            ProviderSpec(
                name="local-fallback",
                label=f"Local model ({getattr(config, 'ai_model_name', 'ollama')})",
                backend=fallback_backend,
                model_name=str(getattr(config, "ai_model_name", "") or ""),
                base_url=str(getattr(config, "ai_model_base_url", "") or ""),
                api_key=getattr(config, "ai_model_api_key", None),
                paid=False,
                free_note="local, fully free" if fallback_backend == "ollama" else "free / owner-configured",
            )
        )
    return chain


class ModelProvider:
    """Durable failover state machine over a provider chain."""

    def __init__(
        self,
        config: Any = None,
        *,
        state_path: Path | str = DEFAULT_STATE_PATH,
        events_path: Path | str = DEFAULT_EVENTS_PATH,
        cooldown_seconds: int = DEFAULT_PRIMARY_COOLDOWN_SECONDS,
    ):
        self.config = _resolve_config(config)
        self.state_path = Path(state_path)
        self.events_path = Path(events_path)
        self.cooldown_seconds = int(cooldown_seconds)
        # Generous per-call timeout: extended-thinking models on the full
        # operator context run well past the 60s default; a too-short timeout
        # causes spurious failovers that read as "NO MODEL".
        self.request_timeout = float(getattr(self.config, "ai_operator_request_timeout", 150) or 150)
        self._lock = threading.RLock()
        self._state = self._load()

    # -- durable state ----------------------------------------------------
    def _default_state(self) -> dict[str, Any]:
        budget = int(getattr(self.config, "ai_operator_token_budget", 0) or 0)
        return {
            "report_kind": REPORT_KIND,
            "budget_tokens": budget,
            "spent_tokens": 0,
            "active_provider": None,
            "primary_cooldown_until_epoch": 0.0,
            "last_switch": None,
            "updated_at": utc_now().isoformat(),
        }

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._default_state()
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._default_state()
        base = self._default_state()
        if isinstance(data, dict):
            base.update({k: data.get(k, base[k]) for k in base})
        return base

    def _save(self) -> None:
        self._state["updated_at"] = utc_now().isoformat()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        payload = json.dumps(self._state, indent=2, sort_keys=True, default=str)
        last_error: OSError | None = None
        for attempt in range(5):
            try:
                tmp.write_text(payload, encoding="utf-8")
                tmp.replace(self.state_path)
                return
            except OSError as exc:  # transient OneDrive/AV lock
                last_error = exc
                time.sleep(0.2 * (attempt + 1))
        if last_error is not None:
            raise last_error

    def _record_event(self, event: dict[str, Any]) -> None:
        event = {"at": utc_now().isoformat(), **event}
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, default=str) + "\n")
        except OSError:
            pass

    # -- budget -----------------------------------------------------------
    def _budget_remaining(self) -> Optional[int]:
        budget = int(self._state.get("budget_tokens", 0) or 0)
        if budget <= 0:
            return None  # no cap
        return max(0, budget - int(self._state.get("spent_tokens", 0) or 0))

    def top_up(self, tokens: int) -> dict[str, Any]:
        """Owner adds paid tokens; clears the primary cooldown so the next call
        flips back to Claude."""
        with self._lock:
            add = max(0, int(tokens))
            self._state["budget_tokens"] = int(self._state.get("budget_tokens", 0) or 0) + add
            self._state["primary_cooldown_until_epoch"] = 0.0
            self._save()
            self._record_event({"type": "TOP_UP", "added_tokens": add, "budget_tokens": self._state["budget_tokens"]})
            return self.status()

    def reset_budget(self, *, budget_tokens: int) -> dict[str, Any]:
        with self._lock:
            self._state["budget_tokens"] = max(0, int(budget_tokens))
            self._state["spent_tokens"] = 0
            self._state["primary_cooldown_until_epoch"] = 0.0
            self._save()
            self._record_event({"type": "RESET_BUDGET", "budget_tokens": self._state["budget_tokens"]})
            return self.status()

    # -- provider selection ----------------------------------------------
    def _primary_available(self, chain: list[ProviderSpec], *, now_epoch: float) -> bool:
        primary = next((p for p in chain if p.paid), None)
        if primary is None:
            return False
        if now_epoch < float(self._state.get("primary_cooldown_until_epoch", 0.0) or 0.0):
            return False
        remaining = self._budget_remaining()
        if remaining is not None and remaining <= 0:
            return False
        return True

    def active_provider(self) -> Optional[ProviderSpec]:
        """The provider that WOULD answer right now (no call made)."""
        with self._lock:
            chain = build_provider_chain(self.config)
            if not chain:
                return None
            now_epoch = utc_now().timestamp()
            if self._primary_available(chain, now_epoch=now_epoch):
                return next((p for p in chain if p.paid), chain[0])
            free = next((p for p in chain if not p.paid), None)
            return free or chain[0]

    def _mark_switch(self, *, to_name: str, reason: str) -> None:
        prev = self._state.get("active_provider")
        if prev != to_name:
            self._state["last_switch"] = {
                "from": prev,
                "to": to_name,
                "reason": reason,
                "at": utc_now().isoformat(),
            }
            self._record_event({"type": "SWITCH", "from": prev, "to": to_name, "reason": reason})
        self._state["active_provider"] = to_name

    def generate(self, prompt: str, system: Optional[str] = None) -> dict[str, Any]:
        """Try the chain in order; fail over on credit/budget/transient error.

        Returns a dict: {ok, text, provider, provider_label, paid, failover,
        switch_reason, attempts, error}. Never raises for provider failure."""
        with self._lock:
            chain = build_provider_chain(self.config)
            if not chain:
                return {
                    "ok": False,
                    "error": "no LLM provider configured (set a Claude key or a local model)",
                    "provider": None,
                    "attempts": [],
                    "failover": False,
                }
            now_epoch = utc_now().timestamp()
            primary_ok = self._primary_available(chain, now_epoch=now_epoch)
            ordered: list[ProviderSpec] = []
            if primary_ok:
                ordered = chain[:]  # primary first, then fallbacks
            else:
                ordered = [p for p in chain if not p.paid] + [p for p in chain if p.paid]
            previous_active = self._state.get("active_provider")
            attempts: list[dict[str, Any]] = []

            for spec in ordered:
                view = _ProviderConfigView(self.config, spec)
                result: AIModelResult = AIModelClient(view, timeout=self.request_timeout).generate(prompt, system)
                if result.ok:
                    if spec.paid:
                        est = (len(prompt) + len(system or "") + len(result.text or "")) // _CHARS_PER_TOKEN
                        self._state["spent_tokens"] = int(self._state.get("spent_tokens", 0) or 0) + int(est)
                    switch_reason = ""
                    if previous_active != spec.name:
                        switch_reason = (
                            "recovered to primary" if spec.paid else "failed over to free fallback"
                        )
                    self._mark_switch(to_name=spec.name, reason=switch_reason or "active")
                    self._save()
                    attempts.append({"provider": spec.name, "ok": True})
                    return {
                        "ok": True,
                        "text": result.text,
                        "provider": spec.name,
                        "provider_label": spec.label,
                        "paid": spec.paid,
                        "failover": bool(switch_reason and not spec.paid),
                        "switch_reason": switch_reason,
                        "attempts": attempts,
                        "budget_remaining": self._budget_remaining(),
                        "error": None,
                    }
                # provider failed
                attempts.append({"provider": spec.name, "ok": False, "error": result.error})
                if spec.paid and _is_credit_error(result.error or ""):
                    # Out of credit / rate-limited / bad key: cool the primary
                    # down so we stop hammering it and use free until top-up.
                    self._state["primary_cooldown_until_epoch"] = now_epoch + self.cooldown_seconds
                    self._record_event(
                        {"type": "PRIMARY_COOLDOWN", "reason": result.error, "seconds": self.cooldown_seconds}
                    )
                # otherwise: transient — fall through to the next provider

            self._save()
            return {
                "ok": False,
                "error": "; ".join(str(a.get("error")) for a in attempts if not a.get("ok")) or "all providers failed",
                "provider": None,
                "attempts": attempts,
                "failover": True,
            }

    # -- status -----------------------------------------------------------
    def status(self) -> dict[str, Any]:
        with self._lock:
            chain = build_provider_chain(self.config)
            active = self.active_provider()
            now_epoch = utc_now().timestamp()
            cooldown_until = float(self._state.get("primary_cooldown_until_epoch", 0.0) or 0.0)
            primary = next((p for p in chain if p.paid), None)
            remaining = self._budget_remaining()
            try:
                from cas_forex.operator_secrets import get_secret, mask

                stored = get_secret("primary_api_key")
                primary_key_present = bool(primary) or bool(stored)
                primary_key_hint = mask(stored) if stored else ""
            except Exception:
                primary_key_present = bool(primary)
                primary_key_hint = ""
            return {
                "report_kind": REPORT_KIND,
                "primary_key_present": primary_key_present,
                "primary_key_hint": primary_key_hint,
                "active_provider": active.name if active else None,
                "active_provider_label": active.label if active else None,
                "active_is_paid": bool(active.paid) if active else False,
                "active_note": active.free_note if active else "",
                "primary_configured": primary is not None,
                "primary_name": primary.name if primary else None,
                "primary_model": primary.model_name if primary else None,
                "primary_in_cooldown": now_epoch < cooldown_until,
                "primary_cooldown_seconds_left": max(0, int(cooldown_until - now_epoch)),
                "budget_tokens": int(self._state.get("budget_tokens", 0) or 0),
                "spent_tokens": int(self._state.get("spent_tokens", 0) or 0),
                "budget_remaining": remaining,
                "budget_capped": remaining is not None,
                "last_switch": self._state.get("last_switch"),
                "chain": [
                    {"name": p.name, "label": p.label, "paid": p.paid, "note": p.free_note}
                    for p in chain
                ],
                "claim_boundary": CLAIM_BOUNDARY,
                "updated_at": self._state.get("updated_at"),
            }


# -- process-global singleton --------------------------------------------
_PROVIDER: Optional[ModelProvider] = None
_PROVIDER_LOCK = threading.Lock()


def get_model_provider(config: Any = None) -> ModelProvider:
    global _PROVIDER
    with _PROVIDER_LOCK:
        if _PROVIDER is None:
            _PROVIDER = ModelProvider(config)
        return _PROVIDER


def set_model_provider_for_tests(provider: Optional[ModelProvider]) -> None:
    global _PROVIDER
    with _PROVIDER_LOCK:
        _PROVIDER = provider
