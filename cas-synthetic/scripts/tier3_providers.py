"""Async dialogue provider abstraction for Tier 3 generation.

Two providers, one call surface. Used by ``generate_tier3_dialogue_v1.py``
to generate dialogue text against either Anthropic Claude or Google Gemini
without leaking provider semantics into the orchestration code.

The abstraction normalizes:
- Async generation call shape
- Token usage reporting (input + output)
- Retryable vs non-retryable errors
- 404 / unsupported-model signal that triggers fallback-model swap
- Pricing constants (per-1M input / output USD)

Anthropic's SDK exception types are imported lazily so callers without
that SDK can still import this module to construct a Gemini-only provider,
and vice versa. Live API calls are kept inside the concrete classes;
tests can pass mock clients via the ``client`` constructor arg.
"""

from __future__ import annotations

import abc
import asyncio
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Pricing — per 1M tokens, USD. Update when provider pricing changes.
# ---------------------------------------------------------------------------

# Anthropic Claude (Sonnet-4 / 3.5 Sonnet — same price).
CLAUDE_PRICE_PER_M_INPUT = 3.00
CLAUDE_PRICE_PER_M_OUTPUT = 15.00

# Google Gemini 3.1 Flash-Lite Preview (paid, non-batch).
# Source: https://ai.google.dev/gemini-api/docs/pricing — verified 2026-05-06.
GEMINI_FLASH_LITE_PRICE_PER_M_INPUT = 0.25
GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT = 1.50

# Google Gemini 3.1 Flash-Lite Preview, Batch API (50% discount).
GEMINI_FLASH_LITE_BATCH_PRICE_PER_M_INPUT = 0.125
GEMINI_FLASH_LITE_BATCH_PRICE_PER_M_OUTPUT = 0.75

# Google Gemini 3.1 Pro-Preview — current Pro tier as of 2026-05-06.
# Source: https://ai.google.dev/gemini-api/docs/gemini-3 — verified.
# Standard tier (≤200k tokens) is what dialogue SDG uses; the higher
# tier ($4/$18) only applies above 200k tokens per call which Tier 3
# dialogue never approaches.
GEMINI_PRO_PREVIEW_PRICE_PER_M_INPUT = 2.00
GEMINI_PRO_PREVIEW_PRICE_PER_M_OUTPUT = 12.00
GEMINI_PRO_PREVIEW_HIGH_TIER_PRICE_PER_M_INPUT = 4.00
GEMINI_PRO_PREVIEW_HIGH_TIER_PRICE_PER_M_OUTPUT = 18.00
GEMINI_PRO_PREVIEW_BATCH_PRICE_PER_M_INPUT = 1.00
GEMINI_PRO_PREVIEW_BATCH_PRICE_PER_M_OUTPUT = 6.00
GEMINI_PRO_PREVIEW_BATCH_HIGH_TIER_PRICE_PER_M_INPUT = 2.00
GEMINI_PRO_PREVIEW_BATCH_HIGH_TIER_PRICE_PER_M_OUTPUT = 9.00
GEMINI_PRO_PREVIEW_TIER_BREAK_TOKENS = 200_000

CLAUDE_DEFAULT_PRIMARY = "claude-sonnet-4-6"
CLAUDE_DEFAULT_FALLBACK = "claude-3-5-sonnet-20241022"

# Per user directive 2026-05-06 (memory: feedback_gemini_default_model.md):
# the default Gemini model for Tier 3 SDG is gemini-3.1-pro-preview, NOT
# Flash-Lite. Flash-Lite failed the manual blind review (20/20
# distinguishable, replies 51% the length of Claude's). Flash-Lite
# remains useful for auxiliary / non-load-bearing tasks but requires an
# explicit `--primary-model gemini-3.1-flash-lite-preview` to opt into.
GEMINI_DEFAULT_PRIMARY = "gemini-3.1-pro-preview"
GEMINI_DEFAULT_FALLBACK = "gemini-2.5-pro"

DEFAULT_MAX_RETRIES = 5


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ProviderCallResult:
    """Normalized result of a single provider call.

    Either ``text`` is a non-empty string (success) and ``error_reason`` is
    None, or ``text`` is None and ``error_reason`` is a stable string the
    orchestration code can branch on (``api_status_404``,
    ``cost_cap_exceeded``, ``rate_limit_retries_exhausted``, etc.).
    """

    text: Optional[str]
    model_used: str
    input_tokens: int
    output_tokens: int
    error_reason: Optional[str]


# ---------------------------------------------------------------------------
# Base provider
# ---------------------------------------------------------------------------

class BatchDialogueProvider(abc.ABC):
    """Async dialogue provider for batch SDG generation.

    Concrete providers implement ``_call_once`` for a single API call; the
    base class wraps it with the shared retry/cost-cap/usage-reporting
    contract. ``cost_tracker`` is the same async cost tracker used by the
    seed SDG script — it exposes an ``await add(in_tokens, out_tokens)``
    method that returns False when the cap is exceeded.
    """

    name: str = ""

    def __init__(
        self,
        *,
        primary_model: str,
        fallback_model: str,
        price_per_m_input: float,
        price_per_m_output: float,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.price_per_m_input = float(price_per_m_input)
        self.price_per_m_output = float(price_per_m_output)
        self.max_retries = int(max_retries)

    @abc.abstractmethod
    async def _call_once(
        self,
        *,
        system_prompt: str,
        user_message: str,
        model: str,
        max_output_tokens: int,
        temperature: float,
    ) -> ProviderCallResult:
        """One API call, no retry. Subclasses raise nothing — they map all
        errors to a populated ``ProviderCallResult.error_reason``.

        Stable error_reason values (for branching downstream):
            - ``rate_limit`` — caller should retry with backoff
            - ``connection`` — caller should retry with backoff
            - ``transient_status`` — caller should retry with backoff
            - ``api_status_404`` — caller should swap to fallback model
            - ``api_status_<N>`` — non-retryable HTTP error
            - ``unexpected:<type>:<msg>`` — non-retryable other failure
        """
        raise NotImplementedError

    async def call(
        self,
        *,
        system_prompt: str,
        user_message: str,
        model: str,
        cost_tracker: Any,
        max_output_tokens: int,
        temperature: float,
    ) -> ProviderCallResult:
        """Retry-wrapped call. Returns a populated ProviderCallResult.

        On success: text is the model's reply, tokens are reported.
        On retry exhaustion: error_reason is ``retries_exhausted:<last>``.
        On cost cap: error_reason is ``cost_cap_exceeded`` (text is None).
        """
        last_reason: Optional[str] = None
        for attempt in range(self.max_retries):
            result = await self._call_once(
                system_prompt=system_prompt,
                user_message=user_message,
                model=model,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
            )
            if result.error_reason is None:
                # Success path — record token usage against cost tracker.
                ok = await cost_tracker.add(result.input_tokens, result.output_tokens)
                if not ok:
                    return ProviderCallResult(
                        text=None,
                        model_used=model,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        error_reason="cost_cap_exceeded",
                    )
                return result

            reason = result.error_reason
            last_reason = reason

            if reason in ("rate_limit", "transient_status"):
                await asyncio.sleep(min(60.0, 2.0 ** attempt + random.random()))
                continue
            if reason == "connection":
                await asyncio.sleep(min(30.0, 2.0 ** attempt + random.random()))
                continue
            # Non-retryable: 404, other status codes, unexpected exceptions.
            return result

        return ProviderCallResult(
            text=None,
            model_used=model,
            input_tokens=0,
            output_tokens=0,
            error_reason=f"retries_exhausted:{last_reason or 'unknown'}",
        )

    def manifest_block(self) -> dict[str, Any]:
        """Provenance entry for the run manifest."""
        return {
            "provider": self.name,
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "price_per_m_input_usd": self.price_per_m_input,
            "price_per_m_output_usd": self.price_per_m_output,
            "max_retries": self.max_retries,
        }


# ---------------------------------------------------------------------------
# Claude provider
# ---------------------------------------------------------------------------

class ClaudeBatchDialogueProvider(BatchDialogueProvider):
    """Async Anthropic Claude provider.

    Wraps ``anthropic.AsyncAnthropic.messages.create``. Lazily imports
    SDK exception types so this module is importable without the
    ``anthropic`` package installed (Gemini-only callers).
    """

    name = "claude"

    def __init__(
        self,
        *,
        client: Any,
        primary_model: str = CLAUDE_DEFAULT_PRIMARY,
        fallback_model: str = CLAUDE_DEFAULT_FALLBACK,
        price_per_m_input: float = CLAUDE_PRICE_PER_M_INPUT,
        price_per_m_output: float = CLAUDE_PRICE_PER_M_OUTPUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        super().__init__(
            primary_model=primary_model,
            fallback_model=fallback_model,
            price_per_m_input=price_per_m_input,
            price_per_m_output=price_per_m_output,
            max_retries=max_retries,
        )
        self.client = client
        self._exc_types_cached: Optional[tuple] = None

    def _exc_types(self) -> tuple:
        if self._exc_types_cached is not None:
            return self._exc_types_cached
        try:
            from anthropic import (  # type: ignore[import-not-found]
                APIConnectionError,
                APIStatusError,
                RateLimitError,
            )
        except Exception:  # pragma: no cover — anthropic not installed
            APIConnectionError = APIStatusError = RateLimitError = ()
        self._exc_types_cached = (RateLimitError, APIStatusError, APIConnectionError)
        return self._exc_types_cached

    async def _call_once(
        self,
        *,
        system_prompt: str,
        user_message: str,
        model: str,
        max_output_tokens: int,
        temperature: float,
    ) -> ProviderCallResult:
        RateLimitError, APIStatusError, APIConnectionError = self._exc_types()
        try:
            resp = await self.client.messages.create(
                model=model,
                max_tokens=max_output_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except RateLimitError:
            return ProviderCallResult(None, model, 0, 0, "rate_limit")
        except APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            if status in (429, 529, 500, 502, 503, 504):
                return ProviderCallResult(None, model, 0, 0, "transient_status")
            if status == 404:
                return ProviderCallResult(None, model, 0, 0, "api_status_404")
            return ProviderCallResult(None, model, 0, 0, f"api_status_{status}")
        except APIConnectionError:
            return ProviderCallResult(None, model, 0, 0, "connection")
        except Exception as exc:  # noqa: BLE001
            return ProviderCallResult(
                None, model, 0, 0, f"unexpected:{type(exc).__name__}:{exc}"
            )

        try:
            in_tokens = int(getattr(resp.usage, "input_tokens", 0) or 0)
            out_tokens = int(getattr(resp.usage, "output_tokens", 0) or 0)
        except Exception:  # noqa: BLE001
            in_tokens = 0
            out_tokens = 0

        text_parts: list[str] = []
        for part in (getattr(resp, "content", None) or []):
            text = getattr(part, "text", None)
            if text:
                text_parts.append(text)
        text = "".join(text_parts) or None
        return ProviderCallResult(
            text=text,
            model_used=model,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            error_reason=None if text else "empty_response",
        )


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class GeminiBatchDialogueProvider(BatchDialogueProvider):
    """Async Google Gemini provider.

    Uses ``google.generativeai.GenerativeModel.generate_content_async``.
    The client param is a callable factory that returns a configured
    ``GenerativeModel`` for a given model name; this lets tests inject a
    mock factory without touching the real google.generativeai module.
    """

    name = "gemini"

    def __init__(
        self,
        *,
        client_factory: Any,
        primary_model: str = GEMINI_DEFAULT_PRIMARY,
        fallback_model: str = GEMINI_DEFAULT_FALLBACK,
        price_per_m_input: Optional[float] = None,
        price_per_m_output: Optional[float] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        default_in_price, default_out_price = _gemini_pricing_for_model(primary_model)
        super().__init__(
            primary_model=primary_model,
            fallback_model=fallback_model,
            price_per_m_input=default_in_price if price_per_m_input is None else price_per_m_input,
            price_per_m_output=default_out_price if price_per_m_output is None else price_per_m_output,
            max_retries=max_retries,
        )
        self.client_factory = client_factory
        self._model_cache: dict[str, Any] = {}

    def _model_for(self, model_name: str) -> Any:
        cached = self._model_cache.get(model_name)
        if cached is not None:
            return cached
        m = self.client_factory(model_name)
        self._model_cache[model_name] = m
        return m

    async def _call_once(
        self,
        *,
        system_prompt: str,
        user_message: str,
        model: str,
        max_output_tokens: int,
        temperature: float,
    ) -> ProviderCallResult:
        try:
            gm = self._model_for(model)
            # Gemini takes the system prompt at construction time on some
            # versions; on 0.8.x it accepts a system_instruction param.
            # Pass it via the call config when supported, otherwise
            # prepend to the user message defensively.
            generation_config = {
                "max_output_tokens": int(max_output_tokens),
                "temperature": float(temperature),
            }
            try:
                resp = await gm.generate_content_async(
                    [{"role": "user", "parts": [user_message]}],
                    generation_config=generation_config,
                    system_instruction=system_prompt,
                )
            except TypeError:
                # Older API surface — fold system prompt into user content.
                folded = f"{system_prompt}\n\n{user_message}"
                resp = await gm.generate_content_async(
                    folded,
                    generation_config=generation_config,
                )
        except Exception as exc:  # noqa: BLE001
            text = f"{type(exc).__name__}:{exc}"
            lower = text.lower()
            # Gemini SDK doesn't expose a clean exception hierarchy, so
            # we string-match common transient/permanent signals. Errs on
            # the side of treating ambiguous failures as retryable.
            if "rate" in lower or "429" in lower or "quota" in lower:
                return ProviderCallResult(None, model, 0, 0, "rate_limit")
            if "503" in lower or "504" in lower or "500" in lower or "529" in lower or "502" in lower:
                return ProviderCallResult(None, model, 0, 0, "transient_status")
            if "404" in lower or "not found" in lower:
                return ProviderCallResult(None, model, 0, 0, "api_status_404")
            if "connection" in lower or "timeout" in lower:
                return ProviderCallResult(None, model, 0, 0, "connection")
            return ProviderCallResult(
                None, model, 0, 0, f"unexpected:{type(exc).__name__}:{exc}"
            )

        # Token counting: google.generativeai exposes usage_metadata on the
        # response when supported.
        try:
            usage = getattr(resp, "usage_metadata", None)
            if usage is not None:
                in_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
                out_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
            else:
                in_tokens = 0
                out_tokens = 0
        except Exception:  # noqa: BLE001
            in_tokens = 0
            out_tokens = 0

        # Extract text. Gemini responses can be a single .text string or
        # candidate parts.
        text: Optional[str] = None
        try:
            text = getattr(resp, "text", None)
        except Exception:  # noqa: BLE001
            text = None
        if not text:
            try:
                candidates = getattr(resp, "candidates", None) or []
                parts: list[str] = []
                for cand in candidates:
                    content = getattr(cand, "content", None)
                    for part in getattr(content, "parts", None) or []:
                        t = getattr(part, "text", None)
                        if t:
                            parts.append(t)
                text = "".join(parts) or None
            except Exception:  # noqa: BLE001
                text = None
        return ProviderCallResult(
            text=text or None,
            model_used=model,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            error_reason=None if text else "empty_response",
        )


# ---------------------------------------------------------------------------
# API key + factory
# ---------------------------------------------------------------------------

def load_gemini_api_key(env_file: Optional[Path] = None) -> Optional[str]:
    """Load Gemini API key from environment or .env file. No-op safe.

    Tries (in order):
      1. ``NC_GEMINI_API_KEY`` env var
      2. ``GEMINI_API_KEY`` env var
      3. ``GOOGLE_API_KEY`` env var
      4. ``env_file`` parsing for any of the above keys

    Returns the raw key string with surrounding quotes/whitespace stripped,
    or None if no key is found. Never logs or prints the value.
    """
    for var in ("NC_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = os.environ.get(var)
        if v and v.strip():
            return v.strip().strip('"').strip("'")
    if env_file is None or not env_file.exists():
        return None
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() in ("NC_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
                return val.strip().strip('"').strip("'")
    except Exception:  # noqa: BLE001
        return None
    return None


def _gemini_pricing_for_model(
    model_name: str,
    *,
    use_batch_pricing: bool = False,
) -> tuple[float, float]:
    """Return (price_per_m_input, price_per_m_output) for a Gemini model.

    Pro-preview is the durable default per user directive 2026-05-06.
    Falls back to Flash-Lite pricing for explicitly-named flash-lite
    models. Update this map when Google rotates pricing.
    """
    n = (model_name or "").strip().lower()
    if "pro-preview" in n or "pro" in n.replace("preview", ""):
        # Pro-preview standard tier ($2/$12, ≤200k tokens). Tier 3 dialogue
        # SDG never approaches the 200k threshold per call.
        if use_batch_pricing:
            return (
                GEMINI_PRO_PREVIEW_BATCH_PRICE_PER_M_INPUT,
                GEMINI_PRO_PREVIEW_BATCH_PRICE_PER_M_OUTPUT,
            )
        return GEMINI_PRO_PREVIEW_PRICE_PER_M_INPUT, GEMINI_PRO_PREVIEW_PRICE_PER_M_OUTPUT
    if "flash-lite" in n:
        if use_batch_pricing:
            return (
                GEMINI_FLASH_LITE_BATCH_PRICE_PER_M_INPUT,
                GEMINI_FLASH_LITE_BATCH_PRICE_PER_M_OUTPUT,
            )
        return GEMINI_FLASH_LITE_PRICE_PER_M_INPUT, GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT
    # Conservative default: Pro-preview rates. Over-estimating cost in
    # the cap math is safer than under-estimating.
    return GEMINI_PRO_PREVIEW_PRICE_PER_M_INPUT, GEMINI_PRO_PREVIEW_PRICE_PER_M_OUTPUT


def make_provider(
    name: str,
    *,
    primary_model: Optional[str] = None,
    fallback_model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Any = None,
    client_factory: Any = None,
    use_batch_pricing: bool = False,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> BatchDialogueProvider:
    """Construct a provider by name. ``client`` / ``client_factory`` lets
    tests inject a mock without touching SDK init.

    Pricing for Gemini is derived from ``primary_model`` automatically:
    pro-preview models get Pro-preview rates ($2/$12 or $1/$6 with batch), flash-lite models
    get Flash-Lite rates ($0.25/$1.50 or $0.125/$0.75 with batch).

    Raises:
        RuntimeError: if the SDK for ``name`` is not importable AND no
            client is injected.
        ValueError: if ``name`` is unknown.
    """
    n = name.strip().lower()
    if n == "claude":
        if client is None:
            try:
                from anthropic import AsyncAnthropic  # type: ignore[import-not-found]
            except ImportError as exc:
                raise RuntimeError(
                    f"anthropic SDK not installed; cannot make claude provider: {exc}"
                ) from exc
            if not api_key:
                raise RuntimeError(
                    "claude provider requires api_key (or pass an injected client)"
                )
            client = AsyncAnthropic(api_key=api_key)
        return ClaudeBatchDialogueProvider(
            client=client,
            primary_model=primary_model or CLAUDE_DEFAULT_PRIMARY,
            fallback_model=fallback_model or CLAUDE_DEFAULT_FALLBACK,
            max_retries=max_retries,
        )

    if n == "gemini":
        active_primary = primary_model or GEMINI_DEFAULT_PRIMARY
        in_price, out_price = _gemini_pricing_for_model(
            active_primary, use_batch_pricing=use_batch_pricing
        )
        if client_factory is None:
            try:
                import google.generativeai as genai  # type: ignore[import-not-found]
            except ImportError as exc:
                raise RuntimeError(
                    f"google.generativeai SDK not installed; cannot make gemini provider: {exc}"
                ) from exc
            if not api_key:
                raise RuntimeError(
                    "gemini provider requires api_key (or pass an injected client_factory)"
                )
            genai.configure(api_key=api_key)
            client_factory = lambda model_name: genai.GenerativeModel(model_name)
        return GeminiBatchDialogueProvider(
            client_factory=client_factory,
            primary_model=active_primary,
            fallback_model=fallback_model or GEMINI_DEFAULT_FALLBACK,
            price_per_m_input=in_price,
            price_per_m_output=out_price,
            max_retries=max_retries,
        )

    raise ValueError(f"unknown provider: {name!r} (expected 'claude' or 'gemini')")


class ProviderCostTracker:
    """Async cost tracker with provider-aware pricing.

    The seed Tier 1/2 CostTracker hardcodes Claude pricing via module-level
    constants. For Tier 3 we need accurate dollar accounting per provider —
    a Gemini run charged at Claude rates over-estimates by ~30x and would
    falsely trip a tight ``--cost-cap`` set on the actual provider's
    economics.

    API matches seed.CostTracker exactly (``input_tokens``,
    ``output_tokens``, ``api_calls``, ``total_usd``, ``aborted``,
    ``hard_cap_usd``, ``async add(in, out) -> bool``) so the field can be
    swapped in without touching consumers.
    """

    def __init__(
        self,
        hard_cap_usd: float,
        *,
        price_per_m_input: float,
        price_per_m_output: float,
    ) -> None:
        self.hard_cap_usd = float(hard_cap_usd)
        self.price_per_m_input = float(price_per_m_input)
        self.price_per_m_output = float(price_per_m_output)
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_calls = 0
        self._lock = asyncio.Lock()
        self._aborted = False

    @property
    def total_usd(self) -> float:
        return (
            self.input_tokens * self.price_per_m_input / 1_000_000.0
            + self.output_tokens * self.price_per_m_output / 1_000_000.0
        )

    async def add(self, in_tokens: int, out_tokens: int) -> bool:
        async with self._lock:
            self.input_tokens += int(in_tokens)
            self.output_tokens += int(out_tokens)
            self.api_calls += 1
            if self.total_usd > self.hard_cap_usd:
                self._aborted = True
                return False
            return True

    @property
    def aborted(self) -> bool:
        return self._aborted


__all__ = [
    "BatchDialogueProvider",
    "ClaudeBatchDialogueProvider",
    "GeminiBatchDialogueProvider",
    "ProviderCallResult",
    "ProviderCostTracker",
    "make_provider",
    "load_gemini_api_key",
    "CLAUDE_DEFAULT_PRIMARY",
    "CLAUDE_DEFAULT_FALLBACK",
    "CLAUDE_PRICE_PER_M_INPUT",
    "CLAUDE_PRICE_PER_M_OUTPUT",
    "GEMINI_DEFAULT_PRIMARY",
    "GEMINI_DEFAULT_FALLBACK",
    "GEMINI_FLASH_LITE_PRICE_PER_M_INPUT",
    "GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT",
    "GEMINI_FLASH_LITE_BATCH_PRICE_PER_M_INPUT",
    "GEMINI_FLASH_LITE_BATCH_PRICE_PER_M_OUTPUT",
    "GEMINI_PRO_PREVIEW_PRICE_PER_M_INPUT",
    "GEMINI_PRO_PREVIEW_PRICE_PER_M_OUTPUT",
    "GEMINI_PRO_PREVIEW_HIGH_TIER_PRICE_PER_M_INPUT",
    "GEMINI_PRO_PREVIEW_HIGH_TIER_PRICE_PER_M_OUTPUT",
    "GEMINI_PRO_PREVIEW_TIER_BREAK_TOKENS",
]
