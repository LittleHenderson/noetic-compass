"""Multi-provider LLM failover for the CAS Forex AI operator.

This layer routes continuous reasoning to DeepSeek V4 Flash when configured,
escalated decisions to DeepSeek V4 Pro, then uses Gemma 4 31B Cloud as an
independent large-model backup before the established Claude and local-Ollama
fallbacks. Provider selection is evidence-bearing: configuration does not
count as readiness until a real generation request succeeds.

Boundary: this module only decides WHICH language model supplies Operator
reasoning. The resulting Operator decision can autonomously reach trading or
configured money movement through the separate guarded execution runtimes; the
provider selector itself is not a broker/provider dispatch path.
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
PROVIDER_HEALTH_FRESH_SECONDS = 300

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
    "Model provider failover selects which language model supplies AI Operator "
    "reasoning. The Operator may originate autonomous trade or configured "
    "money-movement intent; broker/provider effects execute separately through "
    "the guarded dispatch, authority, and receipt paths."
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
    paid: bool  # True => external usage may be metered or billed
    free_note: str = ""  # UI note, e.g. "local, fully free"
    role: str = "general"  # fast / pro / general / fallback
    budget_group: Optional[str] = None


class _ProviderConfigView:
    """Read-only view of the base config with this provider's ai_model_* fields
    overridden, so the existing :class:`AIModelClient` can drive any provider."""

    def __init__(
        self,
        base_config: Any,
        spec: ProviderSpec,
        *,
        max_output_tokens: int | None = None,
    ):
        self._base = base_config
        output_tokens = (
            max(64, int(max_output_tokens))
            if max_output_tokens is not None
            else int(getattr(base_config, "ai_operator_max_tokens", 4000) or 4000)
        )
        structured_output_tokens = (
            output_tokens
            if max_output_tokens is not None
            else int(
                getattr(base_config, "ai_model_structured_max_tokens", 1024)
                or 1024
            )
        )
        self._overrides = {
            "ai_model_enabled": True,
            "ai_model_backend": spec.backend,
            "ai_model_name": spec.model_name,
            "ai_model_base_url": spec.base_url,
            "ai_model_api_key": spec.api_key,
            # Operator calls need room for extended-thinking models: the JSON
            # answer follows the thinking budget, so use the operator ceiling.
            "ai_model_max_tokens": output_tokens,
            # Ollama selects this separate setting whenever a JSON schema is
            # supplied. Honor per-call bounds there too; otherwise a focused
            # 200-token decision silently expands back to the global ceiling.
            "ai_model_structured_max_tokens": structured_output_tokens,
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


def _csv_tokens(value: Any) -> set[str]:
    return {
        token.strip().lower()
        for token in str(value or "").split(",")
        if token.strip()
    }


def resolve_model_role(
    config: Any = None,
    *,
    request_kind: Optional[str] = None,
    model_role: Optional[str] = None,
) -> str:
    """Resolve a request to the continuous (Flash) or escalation (Pro) lane."""

    config = _resolve_config(config)
    explicit = str(model_role or "").strip().lower()
    if explicit in {"pro", "escalation", "high_consequence"}:
        return "pro"
    if explicit in {"fast", "flash", "continuous", "default"}:
        return "fast"
    kind = str(request_kind or "").strip().lower()
    pro_kinds = _csv_tokens(
        getattr(
            config,
            "ai_operator_pro_request_kinds",
            (
                "compound_scale_in,trade_entry_escalation,"
                "position_management_escalation,money_movement,emergency_recovery"
            ),
        )
    )
    return "pro" if kind and kind in pro_kinds else "fast"


def _ollama_cloud_model(model_name: str) -> str:
    model = str(model_name or "").strip()
    if model.endswith(":cloud") or model.endswith("-cloud"):
        return model
    if ":" in model:
        family, tag = model.rsplit(":", 1)
        return f"{family}:{tag}-cloud"
    return f"{model}:cloud"


def build_provider_chain(
    config: Any = None,
    *,
    request_kind: Optional[str] = None,
    model_role: Optional[str] = None,
) -> list[ProviderSpec]:
    """Ordered role-aware failover ladder from current configuration."""
    config = _resolve_config(config)
    chain: list[ProviderSpec] = []
    resolved_role = resolve_model_role(
        config,
        request_kind=request_kind,
        model_role=model_role,
    )

    # Key resolution order: an in-app key the owner pasted (durable, git-ignored
    # secret store) wins, then config/env. This makes an in-app key take effect
    # on the next call with no restart.
    try:
        from cas_forex.operator_secrets import get_secret

        stored_key = get_secret("primary_api_key")
        stored_deepseek_key = get_secret("deepseek_api_key")
    except Exception:
        stored_key = None
        stored_deepseek_key = None

    deepseek_transport = str(
        getattr(config, "ai_operator_deepseek_transport", "direct") or "direct"
    ).strip().lower()
    deepseek_key = (
        stored_deepseek_key
        or getattr(config, "ai_operator_deepseek_api_key", None)
        or os.environ.get("DEEPSEEK_API_KEY")
        or None
    )
    deepseek_enabled = bool(
        getattr(config, "ai_operator_deepseek_enabled", True)
    )
    deepseek_cloud = deepseek_transport in {
        "ollama",
        "ollama_cloud",
        "ollama-cloud",
        "cloud",
    }
    if deepseek_enabled and (deepseek_key or deepseek_cloud):
        backend = "ollama" if deepseek_cloud else "frontier_deepseek"
        base_url = str(
            getattr(
                config,
                (
                    "ai_operator_deepseek_ollama_base_url"
                    if deepseek_cloud
                    else "ai_operator_deepseek_base_url"
                ),
                (
                    "http://127.0.0.1:11434"
                    if deepseek_cloud
                    else "https://api.deepseek.com"
                ),
            )
        ).strip()
        flash_model = str(
            getattr(config, "ai_operator_flash_model", "deepseek-v4-flash")
            or "deepseek-v4-flash"
        )
        pro_model = str(
            getattr(config, "ai_operator_pro_model", "deepseek-v4-pro")
            or "deepseek-v4-pro"
        )
        if deepseek_cloud:
            flash_model = _ollama_cloud_model(flash_model)
            pro_model = _ollama_cloud_model(pro_model)
        transport_label = "Ollama Cloud" if deepseek_cloud else "DeepSeek API"
        flash = ProviderSpec(
            name="deepseek-flash",
            label=f"DeepSeek V4 Flash ({transport_label})",
            backend=backend,
            model_name=flash_model,
            base_url=base_url,
            api_key=None if deepseek_cloud else deepseek_key,
            paid=True,
            free_note=(
                "cloud usage; Ollama sign-in required"
                if deepseek_cloud
                else "metered DeepSeek API"
            ),
            role="fast",
        )
        pro = ProviderSpec(
            name="deepseek-pro",
            label=f"DeepSeek V4 Pro ({transport_label})",
            backend=backend,
            model_name=pro_model,
            base_url=base_url,
            api_key=None if deepseek_cloud else deepseek_key,
            paid=True,
            free_note=(
                "cloud escalation usage; Ollama sign-in required"
                if deepseek_cloud
                else "metered DeepSeek API escalation"
            ),
            role="pro",
        )
        chain.extend([pro, flash] if resolved_role == "pro" else [flash])

    gemma_transport = str(
        getattr(
            config,
            "ai_operator_gemma_backup_transport",
            "ollama_cloud",
        )
        or "ollama_cloud"
    ).strip().lower()
    gemma_enabled = bool(
        getattr(config, "ai_operator_gemma_backup_enabled", False)
    )
    gemma_cloud = gemma_transport in {
        "ollama",
        "ollama_cloud",
        "ollama-cloud",
        "cloud",
    }
    if gemma_enabled and gemma_cloud:
        gemma_model = _ollama_cloud_model(
            str(
                getattr(
                    config,
                    "ai_operator_gemma_backup_model",
                    "gemma4:31b-cloud",
                )
                or "gemma4:31b-cloud"
            )
        )
        chain.append(
            ProviderSpec(
                name="gemma4-backup",
                label="Gemma 4 31B Backup (Ollama Cloud)",
                backend="ollama",
                model_name=gemma_model,
                base_url=str(
                    getattr(
                        config,
                        "ai_operator_gemma_backup_ollama_base_url",
                        "http://127.0.0.1:11434",
                    )
                    or "http://127.0.0.1:11434"
                ).strip(),
                api_key=None,
                paid=True,
                role="backup",
                free_note="cloud backup usage; Ollama sign-in required",
            )
        )

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
                role="general",
                budget_group="legacy_primary",
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
                role="fallback",
                free_note="local, fully free" if fallback_backend == "ollama" else "free / owner-configured",
            )
        )
    # Avoid a duplicate when the generic fallback points at the same Ollama
    # Cloud model as a role-specific or backup route.
    deduped: list[ProviderSpec] = []
    seen: set[tuple[str, str, str]] = set()
    for spec in chain:
        identity = (spec.backend, spec.model_name, spec.base_url.rstrip("/"))
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(spec)
    return deduped


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
            "provider_health": {},
            "last_attempt": None,
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
        last_switch = base.get("last_switch")
        if isinstance(last_switch, dict):
            switched_to = str(last_switch.get("to") or "")
            legacy_reason = str(last_switch.get("reason") or "")
            if switched_to.startswith("deepseek-") and legacy_reason in {
                "recovered to primary",
                "failed over to free fallback",
            }:
                last_switch = dict(last_switch)
                last_switch["reason"] = (
                    "routed to Pro escalation"
                    if switched_to == "deepseek-pro"
                    else "routed to Flash continuous lane"
                )
                base["last_switch"] = last_switch
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
    def _provider_available(self, spec: ProviderSpec, *, now_epoch: float) -> bool:
        # The legacy owner token meter belongs to the Claude primary only.
        # DeepSeek/Gemma cloud usage is reported as metered, but must not
        # inherit an exhausted Claude-only budget.
        if spec.budget_group != "legacy_primary":
            return True
        if now_epoch < float(
            self._state.get("primary_cooldown_until_epoch", 0.0) or 0.0
        ):
            return False
        remaining = self._budget_remaining()
        return remaining is None or remaining > 0

    def _primary_available(self, chain: list[ProviderSpec], *, now_epoch: float) -> bool:
        primary = next(
            (p for p in chain if p.budget_group == "legacy_primary"),
            None,
        )
        if primary is None:
            return False
        return self._provider_available(primary, now_epoch=now_epoch)

    def active_provider(
        self,
        *,
        request_kind: Optional[str] = None,
        model_role: Optional[str] = None,
    ) -> Optional[ProviderSpec]:
        """The provider that WOULD answer right now (no call made)."""
        with self._lock:
            chain = build_provider_chain(
                self.config,
                request_kind=request_kind,
                model_role=model_role,
            )
            if not chain:
                return None
            now_epoch = utc_now().timestamp()
            return next(
                (
                    spec
                    for spec in chain
                    if self._provider_available(spec, now_epoch=now_epoch)
                ),
                None,
            )

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

    def _record_provider_health(
        self,
        spec: ProviderSpec,
        result: AIModelResult,
    ) -> None:
        """Persist the last real generation result for each provider.

        Provider selection and credential presence are configuration facts, not
        proof that a model can answer. This record lets every UI surface report
        the most recent capability result without issuing an expensive probe.
        The caller holds ``self._lock``.
        """

        now = utc_now()
        row = {
            "provider": spec.name,
            "provider_label": spec.label,
            "model_ref": spec.model_name,
            "model_backend": spec.backend,
            "reachability": "READY" if result.ok else "FAILED",
            "checked_at": now.isoformat(),
            "checked_at_epoch": now.timestamp(),
            "error": None if result.ok else str(result.error or "provider generation failed"),
        }
        health = dict(self._state.get("provider_health") or {})
        health[spec.name] = row
        self._state["provider_health"] = health
        self._state["last_attempt"] = row

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        *,
        request_kind: Optional[str] = None,
        model_role: Optional[str] = None,
        request_timeout: Optional[float] = None,
        max_attempts: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        response_format: str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Try the chain in order; fail over on credit/budget/transient error.

        Returns a dict: {ok, text, provider, provider_label, model_ref,
        model_backend, paid, failover, switch_reason, attempts, error}. Never
        raises for provider failure."""
        return self._generate_without_provider_lock(
            prompt,
            system,
            request_kind=request_kind,
            model_role=model_role,
            request_timeout=request_timeout,
            max_attempts=max_attempts,
            max_output_tokens=max_output_tokens,
            response_format=response_format,
        )

    def _generate_without_provider_lock(
        self,
        prompt: str,
        system: Optional[str] = None,
        *,
        request_kind: Optional[str] = None,
        model_role: Optional[str] = None,
        request_timeout: Optional[float] = None,
        max_attempts: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        response_format: str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate without holding the provider state lock during HTTP calls."""
        with self._lock:
            resolved_role = resolve_model_role(
                self.config,
                request_kind=request_kind,
                model_role=model_role,
            )
            chain = build_provider_chain(
                self.config,
                request_kind=request_kind,
                model_role=resolved_role,
            )
            if not chain:
                return {
                    "ok": False,
                    "error": (
                        "no LLM provider configured (enable DeepSeek or Gemma "
                        "Cloud, set a Claude key, or configure local Ollama)"
                    ),
                    "provider": None,
                    "attempts": [],
                    "failover": False,
                    "requested_model_role": resolved_role,
                }
            now_epoch = utc_now().timestamp()
            ordered = [
                spec
                for spec in chain
                if self._provider_available(spec, now_epoch=now_epoch)
            ]
            previous_active = self._state.get("active_provider")

        timeout = self.request_timeout if request_timeout is None else max(0.1, float(request_timeout))
        attempt_limit = None if max_attempts is None else max(1, int(max_attempts))
        if attempt_limit is not None:
            ordered = ordered[:attempt_limit]
        attempts: list[dict[str, Any]] = []

        for spec in ordered:
            view = _ProviderConfigView(
                self.config,
                spec,
                max_output_tokens=max_output_tokens,
            )
            client = AIModelClient(view, timeout=timeout)
            result: AIModelResult = (
                client.generate(prompt, system, response_format=response_format)
                if response_format is not None
                else client.generate(prompt, system)
            )
            with self._lock:
                self._record_provider_health(spec, result)
                if result.ok:
                    if spec.budget_group == "legacy_primary":
                        est = (len(prompt) + len(system or "") + len(result.text or "")) // _CHARS_PER_TOKEN
                        self._state["spent_tokens"] = int(self._state.get("spent_tokens", 0) or 0) + int(est)
                    switch_reason = ""
                    if previous_active != spec.name:
                        if spec.role == "pro":
                            switch_reason = "routed to Pro escalation"
                        elif spec.role == "fast":
                            switch_reason = "routed to Flash continuous lane"
                        elif spec.name == "gemma4-backup":
                            switch_reason = "failed over to Gemma 4 backup"
                        elif not spec.paid:
                            switch_reason = "failed over to local fallback"
                        else:
                            switch_reason = "recovered to provider"
                    self._mark_switch(to_name=spec.name, reason=switch_reason or "active")
                    self._save()
                    attempts.append(
                        {
                            "provider": spec.name,
                            "model_ref": spec.model_name,
                            "model_role": spec.role,
                            "ok": True,
                        }
                    )
                    return {
                        "ok": True,
                        "text": result.text,
                        "provider": spec.name,
                        "provider_label": spec.label,
                        "model_ref": spec.model_name,
                        "model_backend": spec.backend,
                        "model_role": spec.role,
                        "requested_model_role": resolved_role,
                        "request_kind": request_kind,
                        "paid": spec.paid,
                        "failover": len(attempts) > 1,
                        "switch_reason": switch_reason,
                        "attempts": attempts,
                        "budget_remaining": (
                            self._budget_remaining()
                            if spec.budget_group == "legacy_primary"
                            else None
                        ),
                        "error": None,
                    }
                attempts.append(
                    {
                        "provider": spec.name,
                        "model_ref": spec.model_name,
                        "model_role": spec.role,
                        "ok": False,
                        "error": result.error,
                    }
                )
                if (
                    spec.budget_group == "legacy_primary"
                    and _is_credit_error(result.error or "")
                ):
                    self._state["primary_cooldown_until_epoch"] = utc_now().timestamp() + self.cooldown_seconds
                    self._record_event(
                        {"type": "PRIMARY_COOLDOWN", "reason": result.error, "seconds": self.cooldown_seconds}
                    )

        with self._lock:
            self._save()
            return {
                "ok": False,
                "error": "; ".join(str(a.get("error")) for a in attempts if not a.get("ok")) or "all providers failed",
                "provider": None,
                "attempts": attempts,
                "failover": True,
                "requested_model_role": resolved_role,
                "request_kind": request_kind,
            }

    # -- status -----------------------------------------------------------
    def status(self) -> dict[str, Any]:
        with self._lock:
            chain = build_provider_chain(self.config)
            active = self.active_provider()
            now_epoch = time.time()
            cooldown_until = float(self._state.get("primary_cooldown_until_epoch", 0.0) or 0.0)
            primary = next(
                (p for p in chain if p.budget_group == "legacy_primary"),
                None,
            )
            fast_route = self.active_provider(model_role="fast")
            pro_route = self.active_provider(model_role="pro")
            deepseek_specs = [
                p for p in build_provider_chain(self.config, model_role="pro")
                if p.name.startswith("deepseek-")
            ]
            gemma_backup = next(
                (p for p in chain if p.name == "gemma4-backup"),
                None,
            )
            remaining = self._budget_remaining()
            provider_health = dict(self._state.get("provider_health") or {})

            def _route_status(spec: ProviderSpec | None) -> dict[str, Any]:
                health = (
                    dict(provider_health.get(spec.name) or {})
                    if spec is not None
                    else {}
                )
                checked_epoch = float(health.get("checked_at_epoch", 0.0) or 0.0)
                age_seconds = (
                    max(0, int(now_epoch - checked_epoch))
                    if checked_epoch > 0
                    else None
                )
                observed = str(health.get("reachability") or "NOT_PROBED")
                reachability = observed
                if (
                    age_seconds is not None
                    and age_seconds >= PROVIDER_HEALTH_FRESH_SECONDS
                ):
                    reachability = "STALE"
                return {
                    "provider": spec.name if spec else None,
                    "provider_label": spec.label if spec else None,
                    "model_ref": spec.model_name if spec else None,
                    "backend": spec.backend if spec else None,
                    "reachability": reachability,
                    "last_observed_reachability": observed,
                    "health_age_seconds": age_seconds,
                    "last_attempt_at": health.get("checked_at"),
                    "last_error": health.get("error"),
                }

            selected_health = (
                dict(provider_health.get(active.name) or {})
                if active is not None
                else {}
            )
            checked_at_epoch = float(
                selected_health.get("checked_at_epoch", 0.0) or 0.0
            )
            health_age_seconds = (
                max(0, int(now_epoch - checked_at_epoch))
                if checked_at_epoch > 0
                else None
            )
            raw_reachability = str(
                selected_health.get("reachability") or "NOT_PROBED"
            )
            provider_reachability = raw_reachability
            if (
                health_age_seconds is not None
                and health_age_seconds >= PROVIDER_HEALTH_FRESH_SECONDS
            ):
                provider_reachability = "STALE"
            try:
                from cas_forex.operator_secrets import get_secret, mask

                stored = get_secret("primary_api_key")
                stored_deepseek = get_secret("deepseek_api_key")
                primary_key_present = bool(primary) or bool(stored)
                primary_key_hint = mask(stored) if stored else ""
                configured_deepseek_key = (
                    stored_deepseek
                    or getattr(self.config, "ai_operator_deepseek_api_key", None)
                )
                deepseek_key_present = bool(configured_deepseek_key)
                deepseek_key_hint = mask(configured_deepseek_key)
            except Exception:
                primary_key_present = bool(primary)
                primary_key_hint = ""
                deepseek_key_present = bool(
                    getattr(self.config, "ai_operator_deepseek_api_key", None)
                )
                deepseek_key_hint = ""
            return {
                "report_kind": REPORT_KIND,
                "primary_key_present": primary_key_present,
                "primary_key_hint": primary_key_hint,
                "deepseek_configured": bool(deepseek_specs),
                "deepseek_key_present": deepseek_key_present,
                "deepseek_key_hint": deepseek_key_hint,
                "deepseek_transport": str(
                    getattr(
                        self.config,
                        "ai_operator_deepseek_transport",
                        "direct",
                    )
                    or "direct"
                ),
                "gemma4_backup_configured": gemma_backup is not None,
                "gemma4_backup_transport": str(
                    getattr(
                        self.config,
                        "ai_operator_gemma_backup_transport",
                        "ollama_cloud",
                    )
                    or "ollama_cloud"
                ),
                "active_provider": active.name if active else None,
                "active_provider_label": active.label if active else None,
                "active_is_paid": bool(active.paid) if active else False,
                "active_note": active.free_note if active else "",
                "active_model": active.model_name if active else None,
                "active_backend": active.backend if active else None,
                "active_model_role": active.role if active else None,
                "provider_reachability": provider_reachability,
                "provider_last_observed_reachability": raw_reachability,
                "provider_health_age_seconds": health_age_seconds,
                "provider_health_fresh_seconds": PROVIDER_HEALTH_FRESH_SECONDS,
                "provider_last_attempt_at": selected_health.get("checked_at"),
                "provider_last_error": selected_health.get("error"),
                "last_attempt": self._state.get("last_attempt"),
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
                "role_routes": {
                    "fast": _route_status(fast_route),
                    "pro": _route_status(pro_route),
                    "backup": _route_status(gemma_backup),
                },
                "chain": [
                    {
                        "name": p.name,
                        "label": p.label,
                        "model_ref": p.model_name,
                        "backend": p.backend,
                        "model_role": p.role,
                        "paid": p.paid,
                        "note": p.free_note,
                    }
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
