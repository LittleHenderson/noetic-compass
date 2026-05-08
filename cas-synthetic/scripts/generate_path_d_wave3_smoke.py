"""Path D Wave 3 — NL annotation pipeline (5K SMOKE RUN).

First API-spend deliverable for Path D. Validates quality + cost actuals
before scaling to the full ~26K corpus. Reads:

  cas-synthetic/data/path_d/seeds.jsonl     (5802 compiler-validated seeds)
  cas-synthetic/data/path_d/invalids.jsonl  (5581 invalid CAS samples)

Produces ~5,000 NL annotation samples across 4 task slots with stratified
sampling across grammar / error categories. Every generated CAS expression
in the english_to_cas slot round-trips through
``noetic-compass-scaffold/noetic-compass/api/notation/compiler.py``; up to 2
retries with the compiler error fed back into the prompt; samples that
still fail after 3 attempts are logged to ``wave3_smoke_rejected.jsonl``.

Outputs:
  cas-synthetic/data/path_d/wave3_smoke_<timestamp>.jsonl
  cas-synthetic/data/path_d/wave3_smoke_rejected.jsonl
  cas-synthetic/data/path_d/wave3_smoke_leakage.jsonl
  cas-synthetic/data/path_d/wave3_smoke_cost_manifest.json
  cas-synthetic/data/path_d/wave3_smoke_exemplars.md

Hard constraints:
  - $30 cost cap (HARD STOP).
  - Compiler validation REQUIRED for english_to_cas (no skip).
  - Models: claude-haiku-4-5-20251001 (haiku) / claude-sonnet-4-6 (sonnet) — exact strings.
  - API key from ANTHROPIC_API_KEY or NC_ANTHROPIC_API_KEY env var (or .env).

Usage:
  python -m cas_synthetic.scripts.generate_path_d_wave3_smoke \
      --seeds cas-synthetic/data/path_d/seeds.jsonl \
      --invalids cas-synthetic/data/path_d/invalids.jsonl \
      --out-dir cas-synthetic/data/path_d \
      --target-total 5000 \
      --cost-cap-usd 30.0 \
      --seed 4242
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import re
import sys
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


# ---------------------------------------------------------------------------
# Repo / compiler loader
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPILER_PATH = (
    _REPO_ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)
_DEFAULT_ENV_FILE = (
    _REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass" / ".env"
)


def _load_compiler():
    module_name = "cas_synthetic_path_d_wave3_compiler"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load compiler module from {_COMPILER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "path_d_wave3_smoke_v1"
GENERATION_VERSION = "wave3_smoke_2026_05_07"

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
OPUS_MODEL = "claude-opus-4-7"

# Pricing per 1M tokens (USD). Source: Anthropic public pricing.
HAIKU_PRICE_PER_M_INPUT = 1.00
HAIKU_PRICE_PER_M_OUTPUT = 5.00
SONNET_PRICE_PER_M_INPUT = 3.00
SONNET_PRICE_PER_M_OUTPUT = 15.00
OPUS_PRICE_PER_M_INPUT = 5.00   # Opus 4.7 (was $15 on Opus 4.1)
OPUS_PRICE_PER_M_OUTPUT = 25.00  # Opus 4.7 (was $75 on Opus 4.1)

PRICING = {
    HAIKU_MODEL: (HAIKU_PRICE_PER_M_INPUT, HAIKU_PRICE_PER_M_OUTPUT),
    SONNET_MODEL: (SONNET_PRICE_PER_M_INPUT, SONNET_PRICE_PER_M_OUTPUT),
    OPUS_MODEL: (OPUS_PRICE_PER_M_INPUT, OPUS_PRICE_PER_M_OUTPUT),
}

DEFAULT_COST_CAP_USD = 30.0
DEFAULT_TARGET_TOTAL = 5000
DEFAULT_MAX_RETRIES = 3
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_OUTPUT_TOKENS = 400
COMPILER_VALIDATION_MAX_ATTEMPTS = 3  # 1 initial + 2 retries

GRAMMAR_CATEGORIES = (
    "state_literal",
    "binary_composition",
    "cross_register_omega",
    "recipe",
    "meta_logic_relation",
    "fractal_sequence",
    "let_binding",
    "diagram_export",
    "rpm_chain",
    "inversion",
)

ERROR_CLASSES = (
    "parse",
    "admissibility",
    "rpm",
    "recipe",
    "meta_logic",
    "fractal",
)

SLOTS = (
    "cas_to_english",
    "english_to_cas",
    "invalid_to_explanation",
    "invalid_to_corrected",
)

DEFAULT_SLOT_TARGETS = {
    "cas_to_english": 1500,
    "english_to_cas": 1500,
    "invalid_to_explanation": 1000,
    "invalid_to_corrected": 1000,
}

SLOT_MODEL = {
    "cas_to_english": HAIKU_MODEL,
    "english_to_cas": SONNET_MODEL,
    "invalid_to_explanation": SONNET_MODEL,
    "invalid_to_corrected": SONNET_MODEL,
}


# ---------------------------------------------------------------------------
# Leakage regex (mirrors b4_failure_eval._LEAKAGE_PATTERN).
# ---------------------------------------------------------------------------

_LEAKAGE_PATTERN = re.compile(r"\^[0-9]\^[PCEO]|\bF[1-7]\b|\|⟨|Δ°|RPM")


def detect_leakage(reply: str) -> bool:
    """Return True if reply contains user-visible CAS notation.

    Mirrors the per-spec regex from
    ``cas-native/evaluation/b4_failure_eval.py``.
    """
    if not reply:
        return False
    return bool(_LEAKAGE_PATTERN.search(reply))


# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------


@dataclass
class CostTracker:
    cost_cap_usd: float
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    per_model_input_tokens: Counter = field(default_factory=Counter)
    per_model_output_tokens: Counter = field(default_factory=Counter)
    per_slot_cost_usd: Counter = field(default_factory=Counter)
    per_slot_input_tokens: Counter = field(default_factory=Counter)
    per_slot_output_tokens: Counter = field(default_factory=Counter)
    per_slot_count: Counter = field(default_factory=Counter)

    def add(
        self,
        *,
        slot: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        in_price, out_price = PRICING[model]
        cost = (input_tokens / 1_000_000.0) * in_price + (
            output_tokens / 1_000_000.0
        ) * out_price
        self.total_cost_usd += cost
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.per_model_input_tokens[model] += input_tokens
        self.per_model_output_tokens[model] += output_tokens
        self.per_slot_cost_usd[slot] += cost
        self.per_slot_input_tokens[slot] += input_tokens
        self.per_slot_output_tokens[slot] += output_tokens
        self.per_slot_count[slot] += 1
        return cost

    def would_exceed(self, projected_call_cost: float = 0.0) -> bool:
        return (self.total_cost_usd + projected_call_cost) > self.cost_cap_usd

    def remaining_usd(self) -> float:
        return max(0.0, self.cost_cap_usd - self.total_cost_usd)


# ---------------------------------------------------------------------------
# API key loader (ANTHROPIC_API_KEY → NC_ANTHROPIC_API_KEY → .env file).
# ---------------------------------------------------------------------------

_QUOTE_PAIRS = ('"', "'")


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] in _QUOTE_PAIRS and s[-1] == s[0]:
        return s[1:-1]
    return s


def load_api_key(env_file: Optional[Path] = None) -> Optional[str]:
    """Resolve the Anthropic API key.

    Resolution order:
      1. ANTHROPIC_API_KEY env var (the spec-named var).
      2. NC_ANTHROPIC_API_KEY env var (project-local convention).
      3. .env file lookup for either of the above.
    """
    for var in ("ANTHROPIC_API_KEY", "NC_ANTHROPIC_API_KEY"):
        v = os.environ.get(var)
        if v:
            return _strip_quotes(v)
    if env_file is None:
        env_file = _DEFAULT_ENV_FILE
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in ("ANTHROPIC_API_KEY", "NC_ANTHROPIC_API_KEY"):
                return _strip_quotes(v)
    return None


# ---------------------------------------------------------------------------
# Stratified sampler
# ---------------------------------------------------------------------------


def stratified_sample(
    items: list[dict[str, Any]],
    *,
    key: str,
    target_n: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Stratified sample of ``items`` aiming for ``target_n`` records.

    Items are bucketed by ``key``. Each bucket gets at most ``target_n // n_buckets``
    items, falling back to the bucket size when smaller. Remaining slots are
    filled by uniform random sampling across all items (with replacement
    only when the global pool is smaller than the residual).
    """
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        by_bucket[it.get(key, "_unknown")].append(it)
    buckets = sorted(by_bucket.keys())
    if not buckets:
        return []
    base_per_bucket = max(1, target_n // len(buckets))
    selected: list[dict[str, Any]] = []
    used_ids: set[int] = set()
    for b in buckets:
        pool = by_bucket[b]
        rng.shuffle(pool)
        take = min(base_per_bucket, len(pool))
        for it in pool[:take]:
            selected.append(it)
            used_ids.add(id(it))
    # Fill residual.
    if len(selected) < target_n:
        rest = [it for it in items if id(it) not in used_ids]
        rng.shuffle(rest)
        for it in rest:
            if len(selected) >= target_n:
                break
            selected.append(it)
    rng.shuffle(selected)
    return selected[:target_n]


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

# Plain-language guard rails reused across slots.
#
# Patched 2026-05-07 post-Codex audit: added explicit anti-drift rules.
# The first smoke pass (5K samples) showed Haiku 4.5 occasionally invented
# chemistry metaphors ("carbon-based / oxygen-based" — confusing CAS
# Domains C and O with elements) and unsupported cardinalities ("seven out
# of nine") that weren't in the source expression. Both make CAS sound
# incoherent to outsiders, which is the same failure shape as v0.
_PLAIN_LANGUAGE_GUIDANCE = (
    "Write a concise, plain-English description aimed at a curious adult "
    "reader. Do NOT echo CAS notation, operator symbols, or jargon like "
    "'noetic', 'register', 'RPM', or 'F1' in your reply. Describe the meaning "
    "in everyday language. Keep it under 60 words.\n"
    "\n"
    "STRICT anti-drift rules:\n"
    "- Do NOT use chemistry / physics / biology / finance metaphors. Never "
    "  describe CAS Domains as elements (no 'carbon', 'oxygen', 'hydrogen'); "
    "  Domain letters (P, C, E, O) are abstract abbreviations, not chemical "
    "  shorthand.\n"
    "- Do NOT invent cardinalities or counts that aren't literally in the "
    "  source expression. If the expression doesn't say '7 out of 9', don't "
    "  introduce that ratio. Quantify only what the expression itself "
    "  quantifies.\n"
    "- Do NOT invent intensity, strength, weight, or probability quantities. "
    "  If the expression has no numeric coefficient, don't introduce one.\n"
    "- Describe the relation as it literally is, not as an analogy. "
    "  'A connects to B' is fine; 'A is like a parent to B' is invented "
    "  framing unless the source says 'parent'.\n"
    "- Stay neutral on emotional valence unless the expression explicitly "
    "  encodes it (e.g., explicit ^2 Positive or ^3 Negative).\n"
    "- NEVER describe Noetic operators as 'levels' or 'tiers'. No "
    "  'fourth-level', 'seventh-tier', 'fifth-order', 'level of "
    "  intensity', 'level of complexity', 'level of abstraction', or "
    "  'level of detail'. Noetic indices 0-9 are operator slots in a "
    "  formal vocabulary, not a hierarchy. Use the approved everyday "
    "  phrasings below (Mind, Positive, Vibration, Female, Male, "
    "  Rhythm, etc.) instead — they are the right English for each "
    "  operator."
)


# Approved everyday English phrasings for each Noetic operator. Layered
# into the cas_to_english prompt 2026-05-07 post-Codex+user audit. These
# are CAS-canonical colloquialisms (verbatim from the Tootra Math
# Handbook per docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md Clarification 6),
# used as APPROVED ALIASES for cognitive operators — NOT as decoration.
# Codex's guidance: "Preserve the structure first, naturalize second."
# Use ONLY in cas_to_english (and later conversational-response slots);
# do NOT contaminate english_to_cas which needs strict compiler syntax.
_COLLOQUIALISM_GUIDANCE = (
    "Approved everyday English phrasings for each Noetic operator (use "
    "only when one fits naturally — NEVER force):\n"
    "- ^0 Idea: 'it's all in your head', 'a thought', 'something on your mind'\n"
    "- ^1 Mind: 'paying attention', 'using your head', 'making up your mind', "
    "'becoming aware'\n"
    "- ^2 Positive: 'drawn to it', 'speaks to me', \"can't resist\", "
    "'pulled toward'\n"
    "- ^3 Negative: \"can't stomach it\", 'rubs the wrong way', "
    "\"wouldn't touch with a ten-foot pole\", 'pushed away from'\n"
    "- ^4 Vibration: 'hit hard', 'struck a chord', 'resonated', "
    "'made an impression'\n"
    "- ^5 Female: 'sum of one's experiences', 'who one is', "
    "'what makes someone themselves', 'shaped by'\n"
    "- ^6 Male: 'unpacking an idea', 'breaking it down', "
    "'pulling apart the argument', \"looking at what's underneath\"\n"
    "- ^7 Rhythm: 'practice makes perfect', 'muscle memory', "
    "'in a groove', 'getting used to it'\n"
    "- ^8 Above/Cause: 'that reminds me', 'triggered a memory', "
    "'one thing leads to another', 'made me think of'\n"
    "- ^9 Below/Effect: 'popped into mind', 'out of nowhere', "
    "'it just clicked', 'the thought came'\n"
    "\n"
    "Rules for using these phrasings:\n"
    "- Preserve the structural relation FIRST, naturalize SECOND. "
    "Faithfulness to the expression beats stylistic smoothness.\n"
    "- Use a colloquialism only when it fits the source structure. "
    "Don't force one. Don't pile multiple together.\n"
    "- Domain context: P = principled/foundational, C = cognitive/mental, "
    "E = evaluative/judging, O = operational/behavioral. Don't use a "
    "feel-toned colloquialism (e.g., 'gut reaction') for a P-Domain "
    "expression — that's a category error.\n"
    "- These are aliases for the OPERATORS, not decoration. Each phrase "
    "maps to a specific Noetic; using one is making a structural claim, "
    "not just adding flavor."
)


def build_cas_to_english_prompt(seed: dict[str, Any]) -> tuple[str, str]:
    expr = seed["expression"]
    cat = seed.get("grammar_category", "unknown")
    system = (
        "You are a translator that turns formal CAS (Cognitive Architecture "
        "System) expressions into clear English paraphrases. CAS is a formal "
        "notation describing cognitive states and operations. Your job is to "
        "express what an expression MEANS in plain English, using approved "
        "colloquial aliases for cognitive operators where they fit the "
        "structure naturally."
    )
    user = (
        f"CAS expression (grammar category: {cat}):\n\n"
        f"    {expr}\n\n"
        f"{_PLAIN_LANGUAGE_GUIDANCE}\n\n"
        f"{_COLLOQUIALISM_GUIDANCE}\n\n"
        f"Reply with ONLY the English paraphrase. No preamble, no list, no "
        f"explanation of CAS notation, no quotes around the answer."
    )
    return system, user


def build_english_to_cas_prompt(
    seed: dict[str, Any],
    *,
    prior_attempt: Optional[str] = None,
    prior_error: Optional[str] = None,
) -> tuple[str, str]:
    """Prompt the model to PRODUCE a CAS expression from an English description.

    For the smoke run we use the seed's known plain-English description (or
    derive one from the seed expression's grammar category) as the input
    English. The model should generate a CAS expression equivalent to the
    seed; the compiler decides validity. If a prior attempt failed, we
    feed the compiler error back into the prompt for retry.
    """
    expr = seed["expression"]
    cat = seed.get("grammar_category", "unknown")
    # Use the same paraphrase prompt to derive the English the model will
    # translate from. Since we don't have human-written English here, we
    # ask the model to generate CAS for a target English description that
    # is auto-derived from the seed's grammar slot.
    english_hint = _derive_english_hint(seed)
    system = (
        "You are a translator that produces compiler-valid CAS (Cognitive "
        "Architecture System) expressions from English descriptions. CAS is a "
        "formal notation. Your output must parse and admissibility-check via "
        "the CAS compiler."
    )
    user_parts = [
        f"English description (grammar category: {cat}):\n\n    {english_hint}\n",
        f"Produce a valid CAS expression that captures this description.",
        (
            "Reply with ONLY the CAS expression on a single line. No preamble, "
            "no markdown fences, no commentary. The expression alone."
        ),
    ]
    if prior_attempt is not None and prior_error is not None:
        user_parts.append(
            f"\nYour previous attempt was:\n\n    {prior_attempt}\n\n"
            f"It failed compiler validation with:\n\n    {prior_error}\n\n"
            f"Try again. Produce a corrected expression."
        )
    return system, "\n\n".join(user_parts)


def _derive_english_hint(seed: dict[str, Any]) -> str:
    """Derive a short English hint for the EN→CAS direction.

    For the smoke run we emit a deterministic English description based on
    the grammar category and the seed's surface axes. Production runs can
    later swap in human-written English; smoke run uses category-anchored
    hints so we exercise the compiler-loop without spending API budget on
    prerequisite paraphrase generation.
    """
    expr = seed["expression"]
    cat = seed.get("grammar_category", "unknown")
    axes = seed.get("axes", {}) or {}
    noetics = axes.get("noetics_used") or []
    domains = axes.get("domains_used") or []
    drives = axes.get("drives_used") or []
    registers = axes.get("registers_used") or []
    # Provide the seed expression itself as the load-bearing reference so
    # the model has a clean target to translate to. The model still has to
    # render the formal expression — it cannot copy because the compiler
    # checks every output.
    pieces = [
        f"Express the following ({cat} grammar slot) as compiler-valid CAS:",
        f"reference target (for guidance only — do not paste verbatim, render afresh): {expr}",
    ]
    if noetics:
        pieces.append(f"Noetic operators used: {noetics}")
    if domains:
        pieces.append(f"Domains used: {domains}")
    if drives:
        pieces.append(f"Drives used: {drives}")
    if registers:
        pieces.append(f"Registers used: {registers}")
    return " | ".join(pieces)


def build_invalid_to_explanation_prompt(invalid: dict[str, Any]) -> tuple[str, str]:
    expr = invalid["expression"]
    err = invalid.get("compiler_error_message", "")
    cls = invalid.get("error_class", "unknown")
    system = (
        "You are an explainer that describes why a CAS (Cognitive "
        "Architecture System) expression is invalid. CAS is a formal notation "
        "with a strict compiler. Your job is to say in plain English what is "
        "wrong with a malformed expression and why a careful reader should "
        "spot it."
    )
    user = (
        f"Invalid CAS expression (error class: {cls}):\n\n"
        f"    {expr}\n\n"
        f"Compiler error message:\n\n"
        f"    {err}\n\n"
        f"{_PLAIN_LANGUAGE_GUIDANCE}\n\n"
        f"Explain in plain English what is wrong with the expression. Do NOT "
        f"echo the compiler error verbatim — describe it in your own words. "
        f"Reply with ONLY the explanation. No preamble, no markdown."
    )
    return system, user


def build_invalid_to_corrected_prompt(invalid: dict[str, Any]) -> tuple[str, str]:
    expr = invalid["expression"]
    corrected = invalid.get("corrected_form", "")
    err = invalid.get("compiler_error_message", "")
    cls = invalid.get("error_class", "unknown")
    system = (
        "You are a CAS (Cognitive Architecture System) repair assistant. CAS "
        "is a formal notation. The user shows you a malformed expression and "
        "the compiler error. You describe the FIX in plain English — what was "
        "wrong and what change makes it valid."
    )
    user = (
        f"Invalid CAS expression (error class: {cls}):\n\n"
        f"    {expr}\n\n"
        f"Corrected expression (the valid form):\n\n"
        f"    {corrected}\n\n"
        f"Compiler error on the invalid form:\n\n"
        f"    {err}\n\n"
        f"{_PLAIN_LANGUAGE_GUIDANCE}\n\n"
        f"Describe the repair in plain English: what was wrong, what change "
        f"makes the expression valid. Do NOT copy CAS notation into the reply. "
        f"Reply with ONLY the description. No preamble, no markdown."
    )
    return system, user


def parse_cas_from_response(text: str) -> str:
    """Strip markdown fences / preambles around a CAS expression.

    The Sonnet model is reasonably good at returning bare expressions but
    occasionally wraps them in fences or prepends a label. This function
    pulls the most-likely expression out.
    """
    if not text:
        return ""
    s = text.strip()
    # Strip triple-backtick fences (with or without language tag).
    fence_re = re.compile(r"```[a-zA-Z0-9_-]*\n?(.*?)```", re.DOTALL)
    m = fence_re.search(s)
    if m:
        s = m.group(1).strip()
    # Strip a leading label like "CAS:", "Expression:", etc.
    s = re.sub(r"^(?:CAS|Expression|Output|Answer)\s*:\s*", "", s, flags=re.IGNORECASE)
    # Take the first non-empty line.
    for line in s.splitlines():
        line = line.strip()
        if line:
            return line
    return s


# ---------------------------------------------------------------------------
# API client wrapper (sync; minimal retry).
# ---------------------------------------------------------------------------


@dataclass
class ApiCallResult:
    text: Optional[str]
    input_tokens: int
    output_tokens: int
    error_reason: Optional[str]


class AnthropicClient:
    """Minimal sync wrapper around the official Anthropic SDK.

    Built for clarity over performance — the smoke run is small enough
    that sync calls + ordered iteration is the right default. Retries
    (with exponential backoff) on rate-limit and transient 5xx.
    """

    def __init__(self, api_key: str, *, max_retries: int = DEFAULT_MAX_RETRIES):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self.max_retries = max_retries

    def call(
        self,
        *,
        model: str,
        system_prompt: str,
        user_message: str,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> ApiCallResult:
        from anthropic import (
            APIConnectionError,
            APIStatusError,
            RateLimitError,
        )

        # Opus 4.7+ deprecated the ``temperature`` parameter and returns
        # 400 if it's passed. Detect and omit it for those models. Other
        # newer models may follow the same pattern; fail loudly if we see
        # the same message body for a model not in this list and add it.
        _NO_TEMPERATURE_MODELS = ("claude-opus-4-7",)
        omit_temperature = any(model.startswith(m) for m in _NO_TEMPERATURE_MODELS)

        last_err: Optional[str] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                kwargs = dict(
                    model=model,
                    max_tokens=max_output_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                if not omit_temperature:
                    kwargs["temperature"] = temperature
                resp = self._client.messages.create(**kwargs)
            except RateLimitError:
                last_err = "rate_limit"
                _backoff_sleep(attempt)
                continue
            except APIStatusError as exc:
                status = getattr(exc, "status_code", None)
                if status in (429, 500, 502, 503, 504, 529):
                    last_err = f"status_{status}_transient"
                    _backoff_sleep(attempt)
                    continue
                if status == 404:
                    return ApiCallResult(None, 0, 0, "api_status_404")
                return ApiCallResult(None, 0, 0, f"api_status_{status}")
            except APIConnectionError:
                last_err = "connection"
                _backoff_sleep(attempt)
                continue
            except Exception as exc:  # noqa: BLE001
                return ApiCallResult(
                    None, 0, 0, f"unexpected:{type(exc).__name__}:{exc}"
                )

            try:
                in_tokens = int(getattr(resp.usage, "input_tokens", 0) or 0)
                out_tokens = int(getattr(resp.usage, "output_tokens", 0) or 0)
            except Exception:  # noqa: BLE001
                in_tokens = 0
                out_tokens = 0

            text_parts: list[str] = []
            for part in (getattr(resp, "content", None) or []):
                t = getattr(part, "text", None)
                if t:
                    text_parts.append(t)
            text = "".join(text_parts) or None
            return ApiCallResult(
                text=text,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                error_reason=None if text else "empty_response",
            )

        return ApiCallResult(None, 0, 0, last_err or "max_retries_exceeded")


def _backoff_sleep(attempt: int) -> None:
    base = min(60.0, 2.0 ** attempt)
    jitter = random.uniform(0, 0.5 * base)
    time.sleep(base + jitter)


# ---------------------------------------------------------------------------
# Slot generators
# ---------------------------------------------------------------------------


@dataclass
class SampleRecord:
    sample_id: str
    slot: str
    source_id: str
    source_grammar_category_or_error_class: str
    prompt_to_model: str
    model_used: str
    raw_response: str
    generated_cas: Optional[str]
    compiler_validated: Optional[bool]
    compiler_validation_attempts: int
    leakage_in_reply: bool
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    timestamp_utc: str

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _estimate_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    in_price, out_price = PRICING[model]
    return (in_tokens / 1_000_000.0) * in_price + (
        out_tokens / 1_000_000.0
    ) * out_price


def _full_prompt_text(system_prompt: str, user_message: str) -> str:
    """Combine system+user into a single audit string for the manifest.

    We store the full prompt text so any sample can be replayed exactly.
    """
    return f"<<SYSTEM>>\n{system_prompt}\n<<USER>>\n{user_message}"


def generate_cas_to_english(
    seed: dict[str, Any],
    *,
    client: AnthropicClient,
    cost: CostTracker,
    rng: random.Random,
    leakage_writer,
) -> Optional[SampleRecord]:
    system, user = build_cas_to_english_prompt(seed)
    res = client.call(
        model=HAIKU_MODEL, system_prompt=system, user_message=user
    )
    if res.text is None:
        return None
    sample_cost = cost.add(
        slot="cas_to_english",
        model=HAIKU_MODEL,
        input_tokens=res.input_tokens,
        output_tokens=res.output_tokens,
    )
    leak = detect_leakage(res.text)
    sid = seed.get("seed_id", f"unknown_{uuid.uuid4().hex[:8]}")
    rec = SampleRecord(
        sample_id=f"wave3_cas_to_english_{cost.per_slot_count['cas_to_english']:05d}",
        slot="cas_to_english",
        source_id=sid,
        source_grammar_category_or_error_class=seed.get("grammar_category", "unknown"),
        prompt_to_model=_full_prompt_text(system, user),
        model_used=HAIKU_MODEL,
        raw_response=res.text,
        generated_cas=None,
        compiler_validated=None,
        compiler_validation_attempts=0,
        leakage_in_reply=leak,
        input_tokens=res.input_tokens,
        output_tokens=res.output_tokens,
        estimated_cost_usd=sample_cost,
        timestamp_utc=_now_utc_iso(),
    )
    if leak:
        leakage_writer(rec.to_record())
        return None
    return rec


def generate_english_to_cas(
    seed: dict[str, Any],
    *,
    client: AnthropicClient,
    cost: CostTracker,
    compile_expression,
    rng: random.Random,
    rejection_writer,
) -> Optional[SampleRecord]:
    """Generate a CAS expression for a seed; compiler-validate; up to 3 attempts."""
    last_attempt: Optional[str] = None
    last_error: Optional[str] = None
    full_prompt_audit = ""
    raw_response_audit = ""
    total_in_tokens = 0
    total_out_tokens = 0
    total_cost = 0.0
    final_validated = False
    attempts_used = 0

    for attempt in range(1, COMPILER_VALIDATION_MAX_ATTEMPTS + 1):
        attempts_used = attempt
        system, user = build_english_to_cas_prompt(
            seed,
            prior_attempt=last_attempt if attempt > 1 else None,
            prior_error=last_error if attempt > 1 else None,
        )
        res = client.call(model=SONNET_MODEL, system_prompt=system, user_message=user)
        if res.text is None:
            # API failure — count cost (probably zero) and break.
            break
        sample_cost = cost.add(
            slot="english_to_cas",
            model=SONNET_MODEL,
            input_tokens=res.input_tokens,
            output_tokens=res.output_tokens,
        )
        total_in_tokens += res.input_tokens
        total_out_tokens += res.output_tokens
        total_cost += sample_cost
        full_prompt_audit = _full_prompt_text(system, user)
        raw_response_audit = res.text
        candidate = parse_cas_from_response(res.text)
        last_attempt = candidate

        try:
            artifact = compile_expression(candidate)
            valid = bool(getattr(artifact, "valid", False))
        except Exception as exc:  # noqa: BLE001
            valid = False
            artifact = None
        if valid:
            final_validated = True
            sid = seed.get("seed_id", f"unknown_{uuid.uuid4().hex[:8]}")
            rec = SampleRecord(
                sample_id=f"wave3_english_to_cas_{cost.per_slot_count['english_to_cas']:05d}",
                slot="english_to_cas",
                source_id=sid,
                source_grammar_category_or_error_class=seed.get(
                    "grammar_category", "unknown"
                ),
                prompt_to_model=full_prompt_audit,
                model_used=SONNET_MODEL,
                raw_response=raw_response_audit,
                generated_cas=candidate,
                compiler_validated=True,
                compiler_validation_attempts=attempts_used,
                leakage_in_reply=False,  # CAS slot — leakage check N/A.
                input_tokens=total_in_tokens,
                output_tokens=total_out_tokens,
                estimated_cost_usd=total_cost,
                timestamp_utc=_now_utc_iso(),
            )
            return rec
        # Capture error for retry.
        last_error = (
            getattr(artifact, "error", None)
            if artifact is not None
            else "compiler raised exception"
        ) or "unknown compiler failure"

    # All attempts exhausted.
    rejection_writer(
        {
            "source_seed_id": seed.get("seed_id", ""),
            "grammar_category": seed.get("grammar_category", "unknown"),
            "prompt_to_model": full_prompt_audit,
            "last_attempt": last_attempt,
            "last_error": last_error,
            "attempts_used": attempts_used,
            "total_cost_usd": total_cost,
            "timestamp_utc": _now_utc_iso(),
        }
    )
    return None


def generate_invalid_to_explanation(
    invalid: dict[str, Any],
    *,
    client: AnthropicClient,
    cost: CostTracker,
    leakage_writer,
) -> Optional[SampleRecord]:
    system, user = build_invalid_to_explanation_prompt(invalid)
    res = client.call(model=SONNET_MODEL, system_prompt=system, user_message=user)
    if res.text is None:
        return None
    sample_cost = cost.add(
        slot="invalid_to_explanation",
        model=SONNET_MODEL,
        input_tokens=res.input_tokens,
        output_tokens=res.output_tokens,
    )
    leak = detect_leakage(res.text)
    sid = invalid.get("invalid_id", f"unknown_{uuid.uuid4().hex[:8]}")
    rec = SampleRecord(
        sample_id=f"wave3_invalid_to_explanation_{cost.per_slot_count['invalid_to_explanation']:05d}",
        slot="invalid_to_explanation",
        source_id=sid,
        source_grammar_category_or_error_class=invalid.get("error_class", "unknown"),
        prompt_to_model=_full_prompt_text(system, user),
        model_used=SONNET_MODEL,
        raw_response=res.text,
        generated_cas=None,
        compiler_validated=None,
        compiler_validation_attempts=0,
        leakage_in_reply=leak,
        input_tokens=res.input_tokens,
        output_tokens=res.output_tokens,
        estimated_cost_usd=sample_cost,
        timestamp_utc=_now_utc_iso(),
    )
    if leak:
        leakage_writer(rec.to_record())
        return None
    return rec


def generate_invalid_to_corrected(
    invalid: dict[str, Any],
    *,
    client: AnthropicClient,
    cost: CostTracker,
    leakage_writer,
) -> Optional[SampleRecord]:
    system, user = build_invalid_to_corrected_prompt(invalid)
    res = client.call(model=SONNET_MODEL, system_prompt=system, user_message=user)
    if res.text is None:
        return None
    sample_cost = cost.add(
        slot="invalid_to_corrected",
        model=SONNET_MODEL,
        input_tokens=res.input_tokens,
        output_tokens=res.output_tokens,
    )
    leak = detect_leakage(res.text)
    sid = invalid.get("invalid_id", f"unknown_{uuid.uuid4().hex[:8]}")
    rec = SampleRecord(
        sample_id=f"wave3_invalid_to_corrected_{cost.per_slot_count['invalid_to_corrected']:05d}",
        slot="invalid_to_corrected",
        source_id=sid,
        source_grammar_category_or_error_class=invalid.get("error_class", "unknown"),
        prompt_to_model=_full_prompt_text(system, user),
        model_used=SONNET_MODEL,
        raw_response=res.text,
        generated_cas=None,
        compiler_validated=None,
        compiler_validation_attempts=0,
        leakage_in_reply=leak,
        input_tokens=res.input_tokens,
        output_tokens=res.output_tokens,
        estimated_cost_usd=sample_cost,
        timestamp_utc=_now_utc_iso(),
    )
    if leak:
        leakage_writer(rec.to_record())
        return None
    return rec


# ---------------------------------------------------------------------------
# Exemplars + cost manifest writers
# ---------------------------------------------------------------------------


def _score_exemplar(rec: dict[str, Any]) -> tuple[int, ...]:
    """Return a tuple sort key for ranking exemplars; HIGHER is better.

    Components: compiler_validated bonus, no-leakage bonus, length sanity
    (40-300 chars optimal), single-line bonus.
    """
    s_validated = 0
    if rec.get("slot") == "english_to_cas":
        s_validated = 2 if rec.get("compiler_validated") else -2
        s_validated += max(0, 3 - int(rec.get("compiler_validation_attempts", 0)))
    s_leak = -3 if rec.get("leakage_in_reply") else 1
    reply = (rec.get("raw_response") or "").strip()
    rl = len(reply)
    if rl < 5:
        s_len = -3
    elif rl < 20:
        s_len = 0
    elif 20 <= rl <= 300:
        s_len = 2
    elif 300 < rl <= 600:
        s_len = 1
    else:
        s_len = -1
    s_single = 1 if "\n" not in reply else 0
    return (s_validated, s_leak, s_len, s_single)


def write_exemplars_md(
    out_path: Path, samples: Iterable[dict[str, Any]], top_n: int = 5
) -> None:
    by_slot: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in samples:
        by_slot[s["slot"]].append(s)
    lines: list[str] = []
    lines.append("# Path D Wave 3 — Smoke run quality exemplars")
    lines.append("")
    lines.append(
        f"Generated {_now_utc_iso()}. Best/worst {top_n} samples per slot for "
        f"human review. Best = highest score, Worst = lowest score, where "
        f"score reflects compiler-validity (for english_to_cas), reply "
        f"length sanity, leakage status, and single-line shape."
    )
    lines.append("")
    for slot in SLOTS:
        recs = by_slot.get(slot, [])
        if not recs:
            lines.append(f"## Slot: `{slot}` — (no samples)")
            lines.append("")
            continue
        ranked = sorted(recs, key=_score_exemplar, reverse=True)
        bests = ranked[:top_n]
        worsts = ranked[-top_n:][::-1] if len(ranked) >= top_n else ranked[::-1]
        lines.append(f"## Slot: `{slot}` (n={len(recs)})")
        lines.append("")
        lines.append(f"### Best {len(bests)}")
        lines.append("")
        for r in bests:
            lines.append(f"- **{r['sample_id']}** (source: `{r['source_id']}`, "
                         f"category/class: `{r['source_grammar_category_or_error_class']}`)")
            if r.get("generated_cas"):
                lines.append(f"  - generated CAS: `{r['generated_cas']}`")
                lines.append(f"  - compiler_validated: {r['compiler_validated']} "
                             f"(attempts: {r['compiler_validation_attempts']})")
            reply = (r.get("raw_response") or "").replace("\n", " ").strip()
            if len(reply) > 280:
                reply = reply[:280] + "..."
            lines.append(f"  - reply: {reply}")
            lines.append(f"  - leakage: {r.get('leakage_in_reply')}, "
                         f"cost: ${r.get('estimated_cost_usd', 0):.5f}")
            lines.append("")
        lines.append(f"### Worst {len(worsts)}")
        lines.append("")
        for r in worsts:
            lines.append(f"- **{r['sample_id']}** (source: `{r['source_id']}`, "
                         f"category/class: `{r['source_grammar_category_or_error_class']}`)")
            if r.get("generated_cas") is not None:
                lines.append(f"  - generated CAS: `{r['generated_cas']}`")
                lines.append(f"  - compiler_validated: {r['compiler_validated']} "
                             f"(attempts: {r['compiler_validation_attempts']})")
            reply = (r.get("raw_response") or "").replace("\n", " ").strip()
            if len(reply) > 280:
                reply = reply[:280] + "..."
            lines.append(f"  - reply: {reply}")
            lines.append(f"  - leakage: {r.get('leakage_in_reply')}, "
                         f"cost: ${r.get('estimated_cost_usd', 0):.5f}")
            lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_cost_manifest(
    out_path: Path,
    *,
    cost: CostTracker,
    started_at: str,
    ended_at: str,
    stopped_reason: str,
    rejection_counts: dict[str, int],
    rejection_per_category: dict[str, dict[str, int]],
    leakage_counts: dict[str, int],
    full_corpus_target: int,
    smoke_target_total: int,
) -> None:
    per_slot_cost = {k: round(v, 5) for k, v in cost.per_slot_cost_usd.items()}
    per_slot_count = dict(cost.per_slot_count)
    per_slot_compiler_rejection_rate: dict[str, float] = {}
    for slot in SLOTS:
        attempts = per_slot_count.get(slot, 0) + rejection_counts.get(slot, 0)
        if attempts:
            per_slot_compiler_rejection_rate[slot] = round(
                rejection_counts.get(slot, 0) / attempts, 4
            )
        else:
            per_slot_compiler_rejection_rate[slot] = 0.0
    leakage_rate_per_slot: dict[str, float] = {}
    for slot in SLOTS:
        attempts = per_slot_count.get(slot, 0) + leakage_counts.get(slot, 0)
        if attempts:
            leakage_rate_per_slot[slot] = round(
                leakage_counts.get(slot, 0) / attempts, 4
            )
        else:
            leakage_rate_per_slot[slot] = 0.0

    haiku_n = cost.per_slot_count.get("cas_to_english", 0)
    sonnet_n = sum(
        cost.per_slot_count.get(s, 0)
        for s in (
            "english_to_cas",
            "invalid_to_explanation",
            "invalid_to_corrected",
        )
    )
    haiku_cost = cost.per_slot_cost_usd.get("cas_to_english", 0.0)
    sonnet_cost = sum(
        cost.per_slot_cost_usd.get(s, 0.0)
        for s in (
            "english_to_cas",
            "invalid_to_explanation",
            "invalid_to_corrected",
        )
    )
    actual_cost_per_sample = {
        "haiku_avg": round(haiku_cost / haiku_n, 6) if haiku_n else 0.0,
        "sonnet_avg": round(sonnet_cost / sonnet_n, 6) if sonnet_n else 0.0,
    }

    # Decision text
    actual_per_sample_blended = (
        cost.total_cost_usd / sum(per_slot_count.values()) if sum(per_slot_count.values()) else 0.0
    )
    projected_full_cost = actual_per_sample_blended * full_corpus_target
    decision = (
        f"smoke produced {sum(per_slot_count.values())} samples for "
        f"${cost.total_cost_usd:.4f}; blended cost ${actual_per_sample_blended:.6f}/sample; "
        f"projected full {full_corpus_target}-sample cost ${projected_full_cost:.2f}. "
    )
    if stopped_reason == "hit_cost_cap":
        decision += "Cost cap hit during smoke — review per-slot rejection + leakage before scaling."
    else:
        decision += "Smoke completed within cap; review quality + per-category rejection before scaling."

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generation_version": GENERATION_VERSION,
        "started_at": started_at,
        "ended_at": ended_at,
        "stopped_reason": stopped_reason,
        "smoke_target_total": smoke_target_total,
        "cost_cap_usd": cost.cost_cap_usd,
        "total_cost_usd": round(cost.total_cost_usd, 5),
        "per_slot_cost": per_slot_cost,
        "per_slot_count": per_slot_count,
        "per_slot_compiler_rejection_rate": per_slot_compiler_rejection_rate,
        "per_slot_rejection_count": dict(rejection_counts),
        "per_category_rejection_rate": rejection_per_category,
        "leakage_rate_per_slot": leakage_rate_per_slot,
        "leakage_count_per_slot": dict(leakage_counts),
        "total_input_tokens": cost.total_input_tokens,
        "total_output_tokens": cost.total_output_tokens,
        "per_model_input_tokens": dict(cost.per_model_input_tokens),
        "per_model_output_tokens": dict(cost.per_model_output_tokens),
        "actual_cost_per_sample": actual_cost_per_sample,
        "ready_for_full_scale_decision": decision,
    }
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def run_smoke(
    *,
    seeds_path: Path,
    invalids_path: Path,
    out_dir: Path,
    target_total: int = DEFAULT_TARGET_TOTAL,
    cost_cap_usd: float = DEFAULT_COST_CAP_USD,
    seed: int = 4242,
    full_corpus_target: int = 26000,
    api_key: Optional[str] = None,
    client: Optional[AnthropicClient] = None,
    compile_expression=None,
    dry_run: bool = False,
    timestamp_slug: Optional[str] = None,
) -> dict[str, Any]:
    """Execute the smoke run end-to-end. Returns the manifest dict."""
    if compile_expression is None:
        compile_expression = _load_compiler().compile_expression
    if client is None and not dry_run:
        if api_key is None:
            api_key = load_api_key()
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY (or NC_ANTHROPIC_API_KEY) is required to run "
                "the smoke. Set it in the environment or "
                f"{_DEFAULT_ENV_FILE}."
            )
        client = AnthropicClient(api_key=api_key)

    rng = random.Random(seed)

    seeds = load_jsonl(seeds_path)
    invalids = load_jsonl(invalids_path)

    # Distribute target_total across slots proportionally to defaults.
    default_sum = sum(DEFAULT_SLOT_TARGETS.values())
    scale = target_total / default_sum
    slot_targets = {
        s: max(1, int(round(DEFAULT_SLOT_TARGETS[s] * scale))) for s in SLOTS
    }

    # Build slot-specific stratified samples (independent picks per slot).
    cas_to_english_samples = stratified_sample(
        seeds,
        key="grammar_category",
        target_n=slot_targets["cas_to_english"],
        rng=random.Random(seed + 1),
    )
    english_to_cas_samples = stratified_sample(
        seeds,
        key="grammar_category",
        target_n=slot_targets["english_to_cas"],
        rng=random.Random(seed + 2),
    )
    invalid_to_explanation_samples = stratified_sample(
        invalids,
        key="error_class",
        target_n=slot_targets["invalid_to_explanation"],
        rng=random.Random(seed + 3),
    )
    invalid_to_corrected_samples = stratified_sample(
        invalids,
        key="error_class",
        target_n=slot_targets["invalid_to_corrected"],
        rng=random.Random(seed + 4),
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    if timestamp_slug is None:
        timestamp_slug = _timestamp_slug()
    main_path = out_dir / f"wave3_smoke_{timestamp_slug}.jsonl"
    rejected_path = out_dir / "wave3_smoke_rejected.jsonl"
    leakage_path = out_dir / "wave3_smoke_leakage.jsonl"
    cost_path = out_dir / "wave3_smoke_cost_manifest.json"
    exemplars_path = out_dir / "wave3_smoke_exemplars.md"

    cost = CostTracker(cost_cap_usd=cost_cap_usd)
    rejection_counts: Counter = Counter()
    rejection_per_category: dict[str, Counter] = defaultdict(Counter)
    leakage_counts: Counter = Counter()
    started_at = _now_utc_iso()
    stopped_reason = "completed"

    main_fp = main_path.open("w", encoding="utf-8")
    rejected_fp = rejected_path.open("w", encoding="utf-8")
    leakage_fp = leakage_path.open("w", encoding="utf-8")
    in_memory_records: list[dict[str, Any]] = []

    def write_main(rec: dict[str, Any]) -> None:
        main_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        main_fp.flush()
        in_memory_records.append(rec)

    def write_rejected(rec: dict[str, Any]) -> None:
        rejected_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        rejected_fp.flush()

    def write_leakage(rec: dict[str, Any]) -> None:
        leakage_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        leakage_fp.flush()
        leakage_counts[rec["slot"]] += 1

    # Cost cap pre-check helper
    def _budget_ok() -> bool:
        # Reserve a small headroom so a single in-flight call cannot push
        # us over. ~1c headroom is enough to cover a Sonnet retry.
        return cost.total_cost_usd < (cost_cap_usd - 0.02)

    try:
        # Pre-build slot iteration order — interleave so partial caps
        # leave a balanced corpus rather than only-one-slot.
        slot_iters: dict[str, list[dict[str, Any]]] = {
            "cas_to_english": list(cas_to_english_samples),
            "english_to_cas": list(english_to_cas_samples),
            "invalid_to_explanation": list(invalid_to_explanation_samples),
            "invalid_to_corrected": list(invalid_to_corrected_samples),
        }

        # Round-robin across slots until each is exhausted or cap hit.
        slot_indices = {s: 0 for s in SLOTS}
        while True:
            if not _budget_ok():
                stopped_reason = "hit_cost_cap"
                break
            progressed = False
            for slot in SLOTS:
                if not _budget_ok():
                    stopped_reason = "hit_cost_cap"
                    break
                pool = slot_iters[slot]
                idx = slot_indices[slot]
                if idx >= len(pool):
                    continue
                src = pool[idx]
                slot_indices[slot] += 1
                progressed = True

                if dry_run:
                    # Produce a synthetic record for shape testing only.
                    rec = SampleRecord(
                        sample_id=f"wave3_{slot}_{cost.per_slot_count[slot]:05d}",
                        slot=slot,
                        source_id=src.get(
                            "seed_id" if slot in ("cas_to_english", "english_to_cas") else "invalid_id",
                            "unknown",
                        ),
                        source_grammar_category_or_error_class=src.get(
                            "grammar_category" if slot in ("cas_to_english", "english_to_cas") else "error_class",
                            "unknown",
                        ),
                        prompt_to_model="<dry-run>",
                        model_used=SLOT_MODEL[slot],
                        raw_response=f"<dry-run reply for {slot}>",
                        generated_cas=src["expression"] if slot == "english_to_cas" else None,
                        compiler_validated=True if slot == "english_to_cas" else None,
                        compiler_validation_attempts=1 if slot == "english_to_cas" else 0,
                        leakage_in_reply=False,
                        input_tokens=10,
                        output_tokens=10,
                        estimated_cost_usd=0.0,
                        timestamp_utc=_now_utc_iso(),
                    )
                    cost.add(
                        slot=slot, model=SLOT_MODEL[slot],
                        input_tokens=10, output_tokens=10,
                    )
                    write_main(rec.to_record())
                    continue

                if slot == "cas_to_english":
                    rec = generate_cas_to_english(
                        src,
                        client=client,
                        cost=cost,
                        rng=rng,
                        leakage_writer=write_leakage,
                    )
                elif slot == "english_to_cas":
                    rec = generate_english_to_cas(
                        src,
                        client=client,
                        cost=cost,
                        compile_expression=compile_expression,
                        rng=rng,
                        rejection_writer=lambda r, _src=src: (
                            rejection_counts.__setitem__(slot, rejection_counts[slot] + 1),
                            rejection_per_category[_src.get("grammar_category", "unknown")].__setitem__(slot, rejection_per_category[_src.get("grammar_category", "unknown")][slot] + 1),
                            write_rejected({**r, "source_grammar_category": _src.get("grammar_category", "unknown")}),
                        ),
                    )
                elif slot == "invalid_to_explanation":
                    rec = generate_invalid_to_explanation(
                        src,
                        client=client,
                        cost=cost,
                        leakage_writer=write_leakage,
                    )
                elif slot == "invalid_to_corrected":
                    rec = generate_invalid_to_corrected(
                        src,
                        client=client,
                        cost=cost,
                        leakage_writer=write_leakage,
                    )
                else:
                    continue

                if rec is not None:
                    write_main(rec.to_record())

                if cost.total_cost_usd >= cost_cap_usd:
                    stopped_reason = "hit_cost_cap"
                    break

            if not progressed:
                break  # all slot pools exhausted

        # Did we hit the per-slot targets? If everyone hit, stopped_reason = completed.

    finally:
        main_fp.close()
        rejected_fp.close()
        leakage_fp.close()

    ended_at = _now_utc_iso()

    # Per-category rejection-rate dict (collapsed).
    cat_rej: dict[str, dict[str, int]] = {}
    for cat, counter in rejection_per_category.items():
        cat_rej[cat] = dict(counter)

    write_cost_manifest(
        cost_path,
        cost=cost,
        started_at=started_at,
        ended_at=ended_at,
        stopped_reason=stopped_reason,
        rejection_counts=dict(rejection_counts),
        rejection_per_category=cat_rej,
        leakage_counts=dict(leakage_counts),
        full_corpus_target=full_corpus_target,
        smoke_target_total=target_total,
    )
    write_exemplars_md(exemplars_path, in_memory_records, top_n=5)

    return {
        "main_path": str(main_path),
        "rejected_path": str(rejected_path),
        "leakage_path": str(leakage_path),
        "cost_manifest_path": str(cost_path),
        "exemplars_path": str(exemplars_path),
        "stopped_reason": stopped_reason,
        "total_cost_usd": cost.total_cost_usd,
        "per_slot_count": dict(cost.per_slot_count),
        "rejection_counts": dict(rejection_counts),
        "leakage_counts": dict(leakage_counts),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Path D Wave 3 — NL annotation pipeline (5K SMOKE RUN). "
            "Produces ~5K NL annotation samples across 4 slots, "
            "compiler-validates english_to_cas, stops at $30 hard cap."
        )
    )
    p.add_argument("--seeds", type=Path,
                   default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "seeds.jsonl")
    p.add_argument("--invalids", type=Path,
                   default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "invalids.jsonl")
    p.add_argument("--out-dir", type=Path,
                   default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d")
    p.add_argument("--target-total", type=int, default=DEFAULT_TARGET_TOTAL)
    p.add_argument("--cost-cap-usd", type=float, default=DEFAULT_COST_CAP_USD)
    p.add_argument("--seed", type=int, default=4242)
    p.add_argument("--full-corpus-target", type=int, default=26000,
                   help="used for the full-scale projection in the cost manifest")
    p.add_argument("--dry-run", action="store_true",
                   help="don't call the API; produce synthetic records for shape testing")
    p.add_argument("--env-file", type=Path, default=_DEFAULT_ENV_FILE,
                   help="fallback .env file when ANTHROPIC_API_KEY is not set in env")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    api_key = None if args.dry_run else load_api_key(args.env_file)
    if not args.dry_run and not api_key:
        sys.stderr.write(
            "[error] ANTHROPIC_API_KEY (or NC_ANTHROPIC_API_KEY) not found in "
            f"environment or {args.env_file}. Set the key or pass --dry-run.\n"
        )
        return 2
    result = run_smoke(
        seeds_path=args.seeds,
        invalids_path=args.invalids,
        out_dir=args.out_dir,
        target_total=args.target_total,
        cost_cap_usd=args.cost_cap_usd,
        seed=args.seed,
        full_corpus_target=args.full_corpus_target,
        api_key=api_key,
        dry_run=args.dry_run,
    )
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
