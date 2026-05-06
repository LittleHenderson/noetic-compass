"""Generate Tier 3 native-NL dialogue records for Path B.

Tier 3 records are multi-turn dialogue rows shaped for the native English
generation head:

    user prompt -> sampled CAS state -> fluent reply

The CAS state is sampled by this script, not by Claude. Claude only writes
the natural-language user prompt and reply for each turn. That keeps labels
auditable and lets the script enforce the same no-jargon reply validator used
by the Tier 1/2 seed generator.

The default run is the first proof shard: 500 records, one shard per 5,000
records, $500 hard cap for API mode, and resume enabled. Use --dry-run for a
zero-cost structural proof that never touches the Anthropic API.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import random
import re
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


# ---------------------------------------------------------------------------
# Load the shipped Tier 1/2 generator as the source of truth for constants.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SEED_SCRIPT = _REPO_ROOT / "cas-synthetic" / "scripts" / "generate_native_nl_sdg_v1.py"


def _load_seed_module():
    mod_name = "_native_nl_sdg_v1_seed_for_tier3"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _SEED_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load seed SDG module from {_SEED_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


seed = _load_seed_module()


# Local provider abstraction (Claude + Gemini). Imported lazily-friendly:
# this module imports without requiring either SDK to be installed,
# concrete providers raise on construction if their SDK is missing.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tier3_providers import (  # noqa: E402
    BatchDialogueProvider,
    ClaudeBatchDialogueProvider,
    GeminiBatchDialogueProvider,
    ProviderCallResult,
    make_provider,
    load_gemini_api_key,
    CLAUDE_DEFAULT_PRIMARY,
    CLAUDE_DEFAULT_FALLBACK,
    CLAUDE_PRICE_PER_M_INPUT,
    CLAUDE_PRICE_PER_M_OUTPUT,
    GEMINI_DEFAULT_PRIMARY,
    GEMINI_DEFAULT_FALLBACK,
    GEMINI_FLASH_LITE_PRICE_PER_M_INPUT,
    GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT,
)


SCHEMA_VERSION = seed.SCHEMA_VERSION
GENERATION_VERSION = "native_nl_tier3_dialogue_v1"
PRIMARY_MODEL = seed.PRIMARY_MODEL
FALLBACK_MODEL = seed.FALLBACK_MODEL
PRICE_PER_M_INPUT = seed.PRICE_PER_M_INPUT
PRICE_PER_M_OUTPUT = seed.PRICE_PER_M_OUTPUT
SUPPORTED_PROVIDERS = ("claude", "gemini")
DEFAULT_PROVIDER = "claude"
DEFAULT_CONCURRENCY = 5
DEFAULT_COST_CAP_USD = 500.0
DEFAULT_TARGET_RECORDS = 500
DEFAULT_RECORDS_PER_SHARD = 5_000
DEFAULT_TEMPERATURE = 0.8
MAX_RETRIES = seed.MAX_RETRIES
MAX_OUTPUT_TOKENS_PER_TURN = 210
COST_LOG_INTERVAL = 1_000

DEFAULT_OUT_PREFIX = _REPO_ROOT / "cas-synthetic" / "data" / "native_nl" / "v1_dialogue"
DEFAULT_MANIFEST = (
    _REPO_ROOT / "cas-synthetic" / "data" / "native_nl" / "v1_dialogue_manifest.json"
)
ENV_FILE_DEFAULT = (
    _REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass" / ".env"
)

NOETICS = seed.NOETICS
DOMAINS = seed.DOMAINS
DRIVES = seed.DRIVES
REGISTERS = seed.REGISTERS
NOETIC_NUDGES = seed.NOETIC_NUDGES
REGISTER_INSTRUCTIONS = seed.REGISTER_INSTRUCTIONS
TIER1_TOPICS = seed.TIER1_TOPICS
PROFILE_TONE_PAIRS = tuple(
    (profile.code, tone.code)
    for profile in seed.PROFILES
    for tone in seed.TONES
)
AsyncAnthropic = seed.AsyncAnthropic
RateLimitError = seed.RateLimitError
APIStatusError = seed.APIStatusError
APIConnectionError = seed.APIConnectionError


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TurnSpec:
    """The auditable CAS state sampled for one dialogue turn."""

    noetic: str
    domain: str
    drive: str
    register: str
    topic: str
    expression_family: str
    cas_expression: str
    register_set: tuple[str, ...]


@dataclass(frozen=True)
class DialogueJob:
    """One conversation request sent to Claude or dry-run rendering."""

    conversation_id: str
    turn_specs: tuple[TurnSpec, ...]
    profile_code: str
    tone_code: str
    user_message: str


@dataclass
class Tier3RunContext:
    client: Any  # legacy: AsyncAnthropic. Kept for backwards-compat with tests.
    cost_tracker: Any
    trace_id: str
    writer: "ShardWriter"
    primary_model: str
    fallback_model: str
    max_output_tokens: int
    failure_counter: Counter[str]
    current_model: str
    provider: BatchDialogueProvider | None = None
    records_written: int = 0
    last_logged_at: int = 0
    records_lock: asyncio.Lock | None = None

    def __post_init__(self) -> None:
        if self.records_lock is None:
            self.records_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# CAS state sampling
# ---------------------------------------------------------------------------


def axis_complete_iter() -> Iterable[tuple[str, str, str, str]]:
    for n in NOETICS:
        for d in DOMAINS:
            for f in DRIVES:
                for r in REGISTERS:
                    yield (n, d, f, r)


def _base_expression(noetic: str, domain: str, drive: str, register: str) -> str:
    return seed.build_cas_expression(noetic, domain, drive, register)


def _family_for_index(index: int) -> str:
    i = index + 1
    if i % 29 == 0:
        return "recipe"
    if i % 23 == 0:
        return "omega_emergent"
    if i % 17 == 0:
        return "copresence"
    if i % 10 == 0:
        return "register_set"
    return "base"


def _rotate_registers(primary: str, count: int = 3) -> tuple[str, ...]:
    ordered = list(REGISTERS.keys())
    if primary not in ordered:
        return tuple(ordered[:count])
    start = ordered.index(primary)
    return tuple(ordered[(start + i) % len(ordered)] for i in range(count))


def _omega_name(topic: str, index: int) -> str:
    clean = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
    clean = clean[:32] or "dialogue_state"
    return f"Omega_{clean}_{index:04d}"


def _build_expression(
    *,
    family: str,
    primary: tuple[str, str, str, str],
    secondary: tuple[str, str, str, str],
    topic: str,
    index: int,
) -> tuple[str, tuple[str, ...]]:
    n, d, f, r = primary
    base = _base_expression(n, d, f, r)
    n2, d2, f2, r2 = secondary
    other = _base_expression(n2, d2, f2, r2)

    if family == "register_set":
        regs = _rotate_registers(r, 3)
        return f"{n}^{d}_{{{f}}}|<{','.join(regs)}>", regs
    if family == "copresence":
        return f"{base} + {other}", (r, r2)
    if family == "omega_emergent":
        regs = _rotate_registers(r, 2)
        left = _base_expression(n, d, f, regs[0])
        right = _base_expression(n, d, f, regs[1])
        return f"({left} x {right}) = {_omega_name(topic, index)}", regs
    if family == "recipe":
        omega = _omega_name(topic, index)
        return f"Theta({omega}) = 2*{base} + {other} -> {omega}", (r, r2)
    return base, (r,)


def _make_turn_spec(
    *,
    index: int,
    cells: Sequence[tuple[str, str, str, str]],
    rng: random.Random,
) -> TurnSpec:
    primary = cells[index % len(cells)]
    secondary = cells[(index * 7 + 13) % len(cells)]
    topic = TIER1_TOPICS[(index + rng.randrange(0, 997)) % len(TIER1_TOPICS)]
    family = _family_for_index(index)
    cas_expression, register_set = _build_expression(
        family=family,
        primary=primary,
        secondary=secondary,
        topic=topic,
        index=index,
    )
    n, d, f, r = primary
    return TurnSpec(
        noetic=n,
        domain=d,
        drive=f,
        register=r,
        topic=topic,
        expression_family=family,
        cas_expression=cas_expression,
        register_set=register_set,
    )


def _add_specs(
    specs: list[TurnSpec],
    *,
    count: int,
    next_index: int,
    cells: Sequence[tuple[str, str, str, str]],
    rng: random.Random,
) -> int:
    for _ in range(count):
        specs.append(_make_turn_spec(index=next_index, cells=cells, rng=rng))
        next_index += 1
    return next_index


def _turn_counts_for_target(target_records: int, rng: random.Random) -> list[int]:
    """Return 3-7 turn counts that sum exactly to target_records when possible."""
    if target_records <= 0:
        return []
    counts: list[int] = []
    remaining = target_records
    while remaining > 0:
        if remaining <= 7:
            if remaining < 3 and counts and counts[-1] + remaining <= 7:
                counts[-1] += remaining
            else:
                counts.append(remaining)
            break

        choices = [
            c for c in range(3, min(7, remaining) + 1)
            if (remaining - c == 0 or remaining - c >= 3)
        ]
        chosen = rng.choice(choices)
        counts.append(chosen)
        remaining -= chosen
    return counts


def build_dialogue_jobs(
    *,
    target_records: int,
    seed_value: int,
    skip_conversation_ids: set[str] | None = None,
) -> list[DialogueJob]:
    """Build deterministic dialogue jobs for the requested number of rows."""
    skip_conversation_ids = skip_conversation_ids or set()
    rng = random.Random(seed_value)
    cells = list(axis_complete_iter())
    rng.shuffle(cells)
    profile_tone_pairs = list(PROFILE_TONE_PAIRS)
    rng.shuffle(profile_tone_pairs)

    jobs: list[DialogueJob] = []
    next_turn_index = 0
    counts = _turn_counts_for_target(target_records, rng)
    for conv_index, turn_count in enumerate(counts):
        specs: list[TurnSpec] = []
        next_turn_index = _add_specs(
            specs,
            count=turn_count,
            next_index=next_turn_index,
            cells=cells,
            rng=rng,
        )
        first = specs[0]
        conversation_id = seed.deterministic_id(
            "tier3", str(seed_value), str(conv_index), first.cas_expression,
            prefix="conv_",
        )
        if conversation_id in skip_conversation_ids:
            continue
        profile_code, tone_code = profile_tone_pairs[conv_index % len(profile_tone_pairs)]
        job = DialogueJob(
            conversation_id=conversation_id,
            turn_specs=tuple(specs),
            profile_code=profile_code,
            tone_code=tone_code,
            user_message=render_tier3_user_message(
                conversation_id=conversation_id,
                turn_specs=specs,
                profile_code=profile_code,
                tone_code=tone_code,
            ),
        )
        jobs.append(job)
    return jobs


# ---------------------------------------------------------------------------
# Prompting and parsing
# ---------------------------------------------------------------------------


TIER3_SYSTEM_PROMPT = (
    "You generate training data for a native English reply model. The labels "
    "are already chosen by the caller. Your job is only to write realistic "
    "English user prompts and fluent English replies for each turn. Never "
    "mention the hidden labels, CAS, Noetic, Domain, Drive, Register, operator, "
    "or symbolic notation in the reply."
)


def render_tier3_user_message(
    *,
    conversation_id: str,
    turn_specs: Sequence[TurnSpec],
    profile_code: str,
    tone_code: str,
) -> str:
    profile = seed.profile_for(profile_code)
    tone = seed.tone_for(tone_code)

    turn_lines: list[str] = []
    for i, spec in enumerate(turn_specs):
        noetic_name, _noetic_def = NOETICS[spec.noetic]
        domain_name = DOMAINS[spec.domain]
        drive_name = DRIVES[spec.drive]
        register_name = REGISTERS[spec.register]
        turn_lines.append(
            "\n".join(
                [
                    f"Turn {i}:",
                    f"- Topic: {spec.topic}",
                    f"- Hidden CAS expression: {spec.cas_expression}",
                    f"- Hidden state: {spec.noetic} {noetic_name}; "
                    f"{spec.domain} {domain_name}; {spec.drive} {drive_name}; "
                    f"{spec.register} {register_name}",
                    f"- Expression family: {spec.expression_family}",
                    f"- Noetic anti-drift cue: {NOETIC_NUDGES[spec.noetic]}",
                    f"- Register cue: {REGISTER_INSTRUCTIONS[spec.register]}",
                ]
            )
        )

    return (
        f"Conversation ID: {conversation_id}\n\n"
        "Voice for the whole conversation:\n"
        f"- Demographic profile: {profile.name} - {profile.description}\n"
        f"- Tone: {tone.name} - {tone.description}\n\n"
        "Write a short conversation with exactly the requested turns. For each "
        "turn, invent a natural user prompt that fits the hidden state and a "
        "1-3 sentence assistant reply grounded in that state.\n\n"
        "Hard constraints:\n"
        "- Output valid JSON only. No markdown.\n"
        "- Use this shape: {\"turns\":[{\"turn_index\":0,\"prompt_text\":\"...\","
        "\"reply_text\":\"...\"}]}\n"
        "- turn_index values must be 0..N-1 in order.\n"
        "- The reply_text must be fluent natural English and must not mention "
        "CAS, noetic, domain, drive, register, F1-F7, symbolic notation, "
        "operators, or framework terms.\n"
        "- The literal words 'register', 'noetic', 'domain', 'drive', and 'CAS' "
        "are forbidden in reply_text.\n"
        "- Keep each reply_text under 480 characters.\n\n"
        "Turns to write:\n"
        + "\n\n".join(turn_lines)
    )


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def parse_dialogue_json(text: str) -> dict:
    raw = text.strip()
    fence = _JSON_FENCE_RE.search(raw)
    if fence:
        raw = fence.group(1).strip()
    if not raw.startswith("{"):
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start:end + 1]
    parsed = json.loads(raw)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("turns"), list):
        raise ValueError("dialogue JSON must be an object with a turns list")
    return parsed


def validate_prompt(text: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    s = (text or "").strip()
    if len(s) < 8:
        reasons.append("prompt_too_short")
    if len(s) > 700:
        reasons.append("prompt_too_long")
    if not seed.looks_like_english(s):
        reasons.append("prompt_low_letter_density")
    return len(reasons) == 0, reasons


def _validate_turn_payload(payload: dict, turn_index: int) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if payload.get("turn_index") != turn_index:
        reasons.append("turn_index_mismatch")
    ok_prompt, prompt_reasons = validate_prompt(str(payload.get("prompt_text", "")))
    ok_reply, reply_reasons = seed.validate_reply(str(payload.get("reply_text", "")))
    if not ok_prompt:
        reasons.extend(prompt_reasons)
    if not ok_reply:
        reasons.extend(reply_reasons)
    return len(reasons) == 0, reasons


# ---------------------------------------------------------------------------
# Dry-run rendering
# ---------------------------------------------------------------------------


_DRY_REPLY_BY_NOETIC = {
    "^0": "Pause before answering. There may be less here than the urgency makes it seem.",
    "^1": "Start with the simplest honest fact. Strip away the noise and name what is actually in front of you.",
    "^2": "There is a good pattern here if you slow down enough to see it. Choose the next step that preserves what is valuable.",
    "^3": "Something about this should not be ignored. If it makes your body pull back, treat that as information before you commit.",
    "^4": "This is hitting a deeper chord than the surface issue. Notice what keeps resonating after the first reaction fades.",
    "^5": "Let the question open a little. The useful answer may arrive after you stop forcing the first explanation to fit.",
    "^6": "Break the situation into parts and check the assumptions one by one. The weak point is probably hiding in the setup.",
    "^7": "Look for the repeated rhythm. If the same pattern keeps returning, build your next move around that regularity.",
    "^8": "This is bringing another memory or situation to mind. Follow that association carefully without turning it into proof too fast.",
    "^9": "Name the idea that finally clicked. Once it is visible, you can decide whether it deserves action.",
}


_DRY_PROMPTS = (
    "I keep circling around {topic}. What should I do with it?",
    "Can you help me think through {topic} without overcomplicating it?",
    "Something about {topic} is bothering me, but I cannot quite name why.",
    "What is the next sane step with {topic}?",
    "I need a grounded read on {topic}. Where should I start?",
)


_TONE_PREFIX = {
    "T1": "",
    "T2": "Honestly, ",
    "T3": "Look, ",
    "T4": "In practical terms, ",
    "T5": "If you sit with it for a moment, ",
}


def render_dry_turns(job: DialogueJob) -> list[dict]:
    out: list[dict] = []
    for i, spec in enumerate(job.turn_specs):
        prompt = _DRY_PROMPTS[i % len(_DRY_PROMPTS)].format(topic=spec.topic)
        reply = (
            _TONE_PREFIX.get(job.tone_code, "")
            + _DRY_REPLY_BY_NOETIC[spec.noetic]
        ).strip()
        out.append({
            "turn_index": i,
            "prompt_text": prompt,
            "reply_text": reply,
        })
    return out


# ---------------------------------------------------------------------------
# API calls and record construction
# ---------------------------------------------------------------------------


async def call_dialogue(
    provider: BatchDialogueProvider,
    user_message: str,
    *,
    system_prompt: str,
    model: str,
    cost_tracker: Any,
    max_output_tokens: int,
    temperature: float = DEFAULT_TEMPERATURE,
) -> tuple[str | None, str, str | None]:
    """Provider-agnostic dialogue call with retries.

    Returns ``(text, model_used, error_reason)`` for compatibility with the
    existing orchestration code. Provider handles retries internally; cost
    tracking is enforced inside ``provider.call`` against ``cost_tracker``.
    """
    result = await provider.call(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        cost_tracker=cost_tracker,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )
    if result.error_reason is None:
        return result.text, result.model_used, None
    return None, result.model_used, result.error_reason


async def call_claude_dialogue(
    client: Any,
    user_message: str,
    *,
    system_prompt: str,
    model: str,
    cost_tracker: Any,
    max_output_tokens: int,
    temperature: float = DEFAULT_TEMPERATURE,
) -> tuple[str | None, str, str | None]:
    """Call Claude with retries. Returns (text, model_used, error_reason)."""
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.messages.create(
                model=model,
                max_tokens=max_output_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except RateLimitError as exc:
            last_exc = exc
            await asyncio.sleep(min(60.0, 2.0 ** attempt + random.random()))
            continue
        except APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            if status in (429, 529, 500, 502, 503, 504):
                last_exc = exc
                await asyncio.sleep(min(60.0, 2.0 ** attempt + random.random()))
                continue
            if status == 404:
                return None, model, "api_status_404"
            return None, model, f"api_status_{status}"
        except APIConnectionError as exc:
            last_exc = exc
            await asyncio.sleep(min(30.0, 2.0 ** attempt + random.random()))
            continue
        except Exception as exc:  # noqa: BLE001
            return None, model, f"unexpected:{type(exc).__name__}:{exc}"

        try:
            in_tokens = getattr(resp.usage, "input_tokens", 0) or 0
            out_tokens = getattr(resp.usage, "output_tokens", 0) or 0
        except Exception:  # noqa: BLE001
            in_tokens = 0
            out_tokens = 0
        ok = await cost_tracker.add(in_tokens, out_tokens)
        if not ok:
            return None, model, "cost_cap_exceeded"

        text_parts: list[str] = []
        for part in (resp.content or []):
            text = getattr(part, "text", None)
            if text:
                text_parts.append(text)
        return "".join(text_parts), model, None

    return None, model, f"retries_exhausted:{type(last_exc).__name__ if last_exc else 'unknown'}"


def records_from_turns(
    *,
    job: DialogueJob,
    turn_payloads: Sequence[dict],
    trace_id: str,
    model_used: str,
    source: str,
) -> list[dict]:
    profile = seed.profile_for(job.profile_code)
    tone = seed.tone_for(job.tone_code)
    records: list[dict] = []
    turn_count = len(job.turn_specs)
    gen_ts = seed.utc_now_iso()

    for i, spec in enumerate(job.turn_specs):
        payload = turn_payloads[i]
        prompt = str(payload["prompt_text"]).strip()
        reply = seed.clean_reply(str(payload["reply_text"]))
        ok, reasons = seed.validate_reply(reply)
        prompt_ok, prompt_reasons = validate_prompt(prompt)
        if not prompt_ok:
            ok = False
            reasons = list(reasons) + list(prompt_reasons)
        rec_id = seed.deterministic_id(
            spec.cas_expression,
            prompt,
            "tier3",
            model_used,
            gen_ts,
            job.conversation_id,
            str(i),
        )
        records.append({
            "id": rec_id,
            "created_at": gen_ts,
            "schema_version": SCHEMA_VERSION,
            "trace_id": trace_id,
            "tier": "tier3",
            "parent_ids": [],
            "source": source,
            "source_template_id": None,
            "generator_model": model_used,
            "generation_timestamp": gen_ts,
            "conversation_id": job.conversation_id,
            "turn_index": i,
            "turn_count": turn_count,
            "cas_expression": spec.cas_expression,
            "expression_family": spec.expression_family,
            "noetic": spec.noetic,
            "domain": spec.domain,
            "drive": spec.drive,
            "register": spec.register,
            "register_set": list(spec.register_set),
            "topic": spec.topic,
            "prompt": prompt,
            "prompt_text": prompt,
            "reply": reply,
            "reply_text": reply,
            "demographic_profile": profile.name,
            "demographic_profile_code": profile.code,
            "tone": tone.name,
            "tone_code": tone.code,
            "validator_pass": ok,
            "validator_reasons": list(reasons),
            "round_trip_validator": "deferred",
            "generation_version": GENERATION_VERSION,
        })
    return records


async def generate_dialogue_records(ctx: Tier3RunContext, job: DialogueJob) -> list[dict]:
    if ctx.cost_tracker.aborted:
        return []

    if ctx.provider is None:
        # Defensive: orchestration should always set provider before calling.
        # Fall back to Claude-direct path for any legacy test that builds a
        # ctx with only `client` populated.
        text, model_used, err = await call_claude_dialogue(
            ctx.client,
            job.user_message,
            system_prompt=TIER3_SYSTEM_PROMPT,
            model=ctx.current_model,
            cost_tracker=ctx.cost_tracker,
            max_output_tokens=ctx.max_output_tokens,
        )
    else:
        text, model_used, err = await call_dialogue(
            ctx.provider,
            job.user_message,
            system_prompt=TIER3_SYSTEM_PROMPT,
            model=ctx.current_model,
            cost_tracker=ctx.cost_tracker,
            max_output_tokens=ctx.max_output_tokens,
        )
    if text is None and err == "api_status_404" and ctx.current_model == ctx.primary_model:
        ctx.current_model = ctx.fallback_model
        if ctx.provider is None:
            text, model_used, err = await call_claude_dialogue(
                ctx.client,
                job.user_message,
                system_prompt=TIER3_SYSTEM_PROMPT,
                model=ctx.current_model,
                cost_tracker=ctx.cost_tracker,
                max_output_tokens=ctx.max_output_tokens,
            )
        else:
            text, model_used, err = await call_dialogue(
                ctx.provider,
                job.user_message,
                system_prompt=TIER3_SYSTEM_PROMPT,
                model=ctx.current_model,
                cost_tracker=ctx.cost_tracker,
                max_output_tokens=ctx.max_output_tokens,
            )
    if text is None:
        ctx.failure_counter[err or "unknown_api_error"] += 1
        return []

    try:
        parsed = parse_dialogue_json(text)
    except Exception as exc:  # noqa: BLE001
        ctx.failure_counter[f"json_parse:{type(exc).__name__}"] += 1
        return []

    turns = parsed.get("turns", [])
    if len(turns) != len(job.turn_specs):
        ctx.failure_counter["turn_count_mismatch"] += 1
        return []
    failures: list[str] = []
    for i, payload in enumerate(turns):
        ok, reasons = _validate_turn_payload(payload, i)
        if not ok:
            failures.extend(reasons)
    if failures:
        # One lower-temperature retry for validation failures.
        text2, model_used2, err2 = await call_claude_dialogue(
            ctx.client,
            job.user_message,
            system_prompt=TIER3_SYSTEM_PROMPT,
            model=ctx.current_model,
            cost_tracker=ctx.cost_tracker,
            max_output_tokens=ctx.max_output_tokens,
            temperature=0.55,
        )
        if text2 is None:
            ctx.failure_counter[f"retry_api:{err2 or 'unknown'}"] += 1
            return []
        try:
            parsed2 = parse_dialogue_json(text2)
        except Exception as exc:  # noqa: BLE001
            ctx.failure_counter[f"retry_json_parse:{type(exc).__name__}"] += 1
            return []
        turns2 = parsed2.get("turns", [])
        failures2: list[str] = []
        if len(turns2) != len(job.turn_specs):
            failures2.append("turn_count_mismatch")
        else:
            for i, payload in enumerate(turns2):
                ok, reasons = _validate_turn_payload(payload, i)
                if not ok:
                    failures2.extend(reasons)
        if failures2:
            ctx.failure_counter[f"validation:{failures2[0]}"] += 1
            return []
        turns = turns2
        model_used = model_used2

    return records_from_turns(
        job=job,
        turn_payloads=turns,
        trace_id=ctx.trace_id,
        model_used=model_used,
        source="claude_api",
    )


async def tier3_worker(
    ctx: Tier3RunContext,
    sem: asyncio.Semaphore,
    job: DialogueJob,
) -> None:
    if ctx.cost_tracker.aborted:
        return
    async with sem:
        if ctx.cost_tracker.aborted:
            return
        records = await generate_dialogue_records(ctx, job)
        if not records:
            return
        assert ctx.records_lock is not None
        async with ctx.records_lock:
            ctx.writer.append_records(records)
            ctx.records_written += len(records)
            if ctx.records_written - ctx.last_logged_at >= COST_LOG_INTERVAL:
                ctx.last_logged_at = ctx.records_written
                print(
                    f"[tier3 progress] new_records={ctx.records_written} "
                    f"api_calls={ctx.cost_tracker.api_calls} "
                    f"cost_estimate=${ctx.cost_tracker.total_usd:.2f} "
                    f"failures={sum(ctx.failure_counter.values())}",
                    flush=True,
                )


# ---------------------------------------------------------------------------
# Shards, manifest, and resume
# ---------------------------------------------------------------------------


def shard_path(out_prefix: Path, shard_index: int) -> Path:
    return out_prefix.parent / f"{out_prefix.name}_{shard_index:04d}.jsonl"


def iter_shard_paths(out_prefix: Path) -> list[Path]:
    return sorted(out_prefix.parent.glob(f"{out_prefix.name}_*.jsonl"))


def load_existing_records(out_prefix: Path) -> list[dict]:
    records: list[dict] = []
    for path in iter_shard_paths(out_prefix):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


class ShardWriter:
    def __init__(self, out_prefix: Path, records_per_shard: int, existing_count: int) -> None:
        if records_per_shard < 1:
            raise ValueError("records_per_shard must be >= 1")
        self.out_prefix = out_prefix
        self.records_per_shard = records_per_shard
        self.count = existing_count
        self.out_prefix.parent.mkdir(parents=True, exist_ok=True)

    def append_records(self, records: Sequence[dict]) -> None:
        for rec in records:
            shard_index = self.count // self.records_per_shard
            path = shard_path(self.out_prefix, shard_index)
            with path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.count += 1


def compute_distributions(records: Sequence[dict]) -> dict[str, dict[str, int]]:
    keys = (
        "tier",
        "noetic",
        "domain",
        "drive",
        "register",
        "expression_family",
        "demographic_profile",
        "tone",
        "generator_model",
    )
    out: dict[str, Counter[str]] = {k: Counter() for k in keys}
    for rec in records:
        for key in keys:
            out[key][str(rec.get(key, "?"))] += 1
    return {k: dict(v) for k, v in out.items()}


def write_manifest(
    manifest_path: Path,
    *,
    records: Sequence[dict],
    started_iso: str,
    completed_iso: str,
    cost_tracker: Any,
    failure_counter: Counter[str],
    trace_id: str,
    seed_value: int,
    target_records: int,
    out_prefix: Path,
    records_per_shard: int,
    primary_model: str,
    final_model: str,
    api_key_status: str,
    dry_run: bool,
    resumed_records: int,
    notes: Sequence[str],
    provider_name: str = DEFAULT_PROVIDER,
    fallback_model: str | None = None,
    price_per_m_input_usd: float | None = None,
    price_per_m_output_usd: float | None = None,
) -> dict:
    validator_pass_count = sum(1 for rec in records if rec.get("validator_pass"))
    conversation_ids = {str(rec.get("conversation_id")) for rec in records}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generation_version": GENERATION_VERSION,
        "trace_id": trace_id,
        "seed": seed_value,
        "target_records": target_records,
        "total_records": len(records),
        "tier3_records": sum(1 for rec in records if rec.get("tier") == "tier3"),
        "total_conversations": len(conversation_ids),
        "resumed_records": resumed_records,
        "validator_pass_count": validator_pass_count,
        "validator_pass_rate": validator_pass_count / max(1, len(records)),
        "provider": provider_name,
        "primary_model": primary_model,
        "fallback_model": fallback_model,
        "final_model": final_model,
        "price_per_m_input_usd": price_per_m_input_usd,
        "price_per_m_output_usd": price_per_m_output_usd,
        "api_key_status": api_key_status,
        "dry_run": dry_run,
        "distributions": compute_distributions(records),
        "total_cost_usd": round(cost_tracker.total_usd, 4),
        "input_tokens": cost_tracker.input_tokens,
        "output_tokens": cost_tracker.output_tokens,
        "api_calls": cost_tracker.api_calls,
        "hard_cost_cap_usd": cost_tracker.hard_cap_usd,
        "cost_aborted": cost_tracker.aborted,
        "failure_counts": dict(failure_counter),
        "generation_started": started_iso,
        "generation_completed": completed_iso,
        "out_prefix": str(out_prefix),
        "records_per_shard": records_per_shard,
        "shard_paths": [str(p) for p in iter_shard_paths(out_prefix)],
        "round_trip_validator": "deferred",
        "notes": list(notes),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def estimate_cost_usd(target_records: int) -> float:
    # Dialogue prompt is amortized over 3-7 turns. These values are deliberately
    # conservative enough to catch bad targets without blocking the 500 proof.
    input_tokens_per_record = 320
    output_tokens_per_record = 130
    return (
        target_records * input_tokens_per_record * PRICE_PER_M_INPUT / 1_000_000.0
        + target_records * output_tokens_per_record * PRICE_PER_M_OUTPUT / 1_000_000.0
    )


async def run_tier3_api(
    *,
    jobs: Sequence[DialogueJob],
    cost_cap_usd: float,
    cost_tracker: Any | None = None,
    concurrency: int,
    primary_model: str,
    fallback_model: str,
    api_key: str | None = None,
    trace_id: str,
    writer: ShardWriter,
    provider: BatchDialogueProvider | None = None,
    provider_name: str = "claude",
) -> tuple[Any, Counter[str], str, int]:
    """Drive the API loop with retries + cost tracking.

    The provider is the source of truth for SDK-level semantics (call shape,
    error mapping, token usage, pricing). Callers can either pass a fully
    constructed ``provider`` or pass ``provider_name`` + ``api_key`` and let
    this function build it. Defaulting to claude preserves prior behavior
    for callers that did not pass ``provider_name``.
    """
    if cost_tracker is None:
        cost_tracker = seed.CostTracker(cost_cap_usd)
    if not jobs:
        return cost_tracker, Counter(), primary_model, 0

    if provider is None:
        provider = make_provider(
            provider_name,
            primary_model=primary_model,
            fallback_model=fallback_model,
            api_key=api_key,
        )

    max_turns = max(len(job.turn_specs) for job in jobs)
    max_output_tokens = max_turns * MAX_OUTPUT_TOKENS_PER_TURN
    ctx = Tier3RunContext(
        client=getattr(provider, "client", None),
        cost_tracker=cost_tracker,
        trace_id=trace_id,
        writer=writer,
        primary_model=primary_model,
        fallback_model=fallback_model,
        max_output_tokens=max_output_tokens,
        failure_counter=Counter(),
        current_model=primary_model,
        provider=provider,
    )

    probe_text, _probe_model, probe_err = await call_dialogue(
        provider,
        "Return JSON only: {\"turns\":[{\"turn_index\":0,\"prompt_text\":\"ok\","
        "\"reply_text\":\"ok\"}]}",
        system_prompt=TIER3_SYSTEM_PROMPT,
        model=primary_model,
        cost_tracker=cost_tracker,
        max_output_tokens=80,
        temperature=0.0,
    )
    if probe_text is None and probe_err == "api_status_404":
        print(
            f"[preflight] primary model {primary_model} unavailable; "
            f"falling back to {fallback_model}",
            flush=True,
        )
        ctx.current_model = fallback_model
        probe_text, _probe_model, probe_err = await call_dialogue(
            provider,
            "Return JSON only: {\"turns\":[{\"turn_index\":0,\"prompt_text\":\"ok\","
            "\"reply_text\":\"ok\"}]}",
            system_prompt=TIER3_SYSTEM_PROMPT,
            model=fallback_model,
            cost_tracker=cost_tracker,
            max_output_tokens=80,
            temperature=0.0,
        )
    if probe_text is None:
        raise RuntimeError(f"preflight call failed: {probe_err}")
    print(
        f"[preflight] provider={provider.name} model={ctx.current_model}; probe ok",
        flush=True,
    )

    sem = asyncio.Semaphore(concurrency)
    tasks = [asyncio.create_task(tier3_worker(ctx, sem, job)) for job in jobs]
    await asyncio.gather(*tasks, return_exceptions=False)
    return cost_tracker, ctx.failure_counter, ctx.current_model, ctx.records_written


def run(
    *,
    target_records: int,
    out_prefix: Path,
    manifest_path: Path,
    records_per_shard: int,
    seed_value: int,
    concurrency: int,
    cost_cap_usd: float,
    primary_model: str,
    fallback_model: str,
    env_file: Path,
    dry_run: bool,
    resume: bool,
    provider_name: str = DEFAULT_PROVIDER,
) -> int:
    started_iso = seed.utc_now_iso()
    trace_id = str(uuid.uuid4())
    notes: list[str] = []

    existing_records = load_existing_records(out_prefix) if resume else []
    existing_conversation_ids = {
        str(rec.get("conversation_id"))
        for rec in existing_records
        if rec.get("conversation_id")
    }
    new_target = max(0, target_records - len(existing_records))
    writer = ShardWriter(
        out_prefix=out_prefix,
        records_per_shard=records_per_shard,
        existing_count=len(existing_records),
    )

    print(
        f"[run] trace_id={trace_id} seed={seed_value} target_records={target_records} "
        f"existing_records={len(existing_records)} new_target={new_target} "
        f"dry_run={dry_run}",
        flush=True,
    )

    failure_counter: Counter[str] = Counter()
    cost_tracker = seed.CostTracker(cost_cap_usd)
    final_model = primary_model
    api_key_status = "dry-run" if dry_run else "unused"

    if new_target > 0:
        if dry_run:
            jobs = build_dialogue_jobs(
                target_records=new_target,
                seed_value=seed_value + len(existing_records),
                skip_conversation_ids=existing_conversation_ids,
            )
            prepared_records = sum(len(job.turn_specs) for job in jobs)
            print(
                f"[tier3] prepared {len(jobs)} conversations / {prepared_records} turns",
                flush=True,
            )
            for job in jobs:
                records = records_from_turns(
                    job=job,
                    turn_payloads=render_dry_turns(job),
                    trace_id=trace_id,
                    model_used="dry-run",
                    source="dry-run",
                )
                writer.append_records(records)
            print(f"[tier3 dry-run] wrote {prepared_records} records", flush=True)
        else:
            if provider_name == "claude":
                api_key = seed.load_api_key(env_file)
                key_ok = bool(api_key and api_key.startswith("sk-ant-"))
                if not key_ok:
                    print(
                        f"[abort] NC_ANTHROPIC_API_KEY missing or malformed in {env_file}",
                        flush=True,
                    )
                    api_key_status = "missing"
                    notes.append("API key missing or invalid; no API spend occurred.")
            elif provider_name == "gemini":
                api_key = load_gemini_api_key(env_file)
                key_ok = bool(api_key)
                if not key_ok:
                    print(
                        f"[abort] gemini API key missing in {env_file} "
                        f"(NC_GEMINI_API_KEY / GEMINI_API_KEY / GOOGLE_API_KEY)",
                        flush=True,
                    )
                    api_key_status = "missing"
                    notes.append("Gemini API key missing; no API spend occurred.")
            else:
                api_key = None
                key_ok = False
                api_key_status = "unknown_provider"
                notes.append(f"Unknown provider {provider_name!r}.")

            if key_ok:
                api_key_status = "present"
                max_rounds = 8
                for round_index in range(max_rounds):
                    current_records = load_existing_records(out_prefix)
                    remaining = max(0, target_records - len(current_records))
                    if remaining <= 0:
                        break
                    if cost_tracker.aborted:
                        notes.append("Cost tracker aborted before target was filled.")
                        break
                    existing_conversation_ids = {
                        str(rec.get("conversation_id"))
                        for rec in current_records
                        if rec.get("conversation_id")
                    }
                    jobs = build_dialogue_jobs(
                        target_records=remaining,
                        seed_value=seed_value + len(current_records) + (round_index * 100_000),
                        skip_conversation_ids=existing_conversation_ids,
                    )
                    prepared_records = sum(len(job.turn_specs) for job in jobs)
                    print(
                        f"[tier3] round={round_index + 1} prepared "
                        f"{len(jobs)} conversations / {prepared_records} turns "
                        f"(remaining={remaining})",
                        flush=True,
                    )
                    estimate = estimate_cost_usd(prepared_records)
                    print(
                        f"[preflight] estimated tier3 cost for {prepared_records} "
                        f"records this round: ~${estimate:.2f} "
                        f"(spent=${cost_tracker.total_usd:.2f}, cap=${cost_cap_usd:.2f})",
                        flush=True,
                    )
                    if cost_tracker.total_usd + estimate > cost_cap_usd:
                        print(
                            f"[abort] estimated cumulative cost "
                            f"${cost_tracker.total_usd + estimate:.2f} exceeds cap "
                            f"${cost_cap_usd:.2f}",
                            flush=True,
                        )
                        notes.append("Estimated cumulative cost exceeded cap.")
                        break
                    try:
                        before = len(current_records)
                        cost_tracker, round_failures, final_model, written = asyncio.run(
                            run_tier3_api(
                                jobs=jobs,
                                cost_cap_usd=cost_cap_usd,
                                cost_tracker=cost_tracker,
                                concurrency=concurrency,
                                primary_model=primary_model,
                                fallback_model=fallback_model,
                                api_key=api_key,
                                trace_id=trace_id,
                                writer=writer,
                                provider_name=provider_name,
                            )
                        )
                        failure_counter.update(round_failures)
                        after = len(load_existing_records(out_prefix))
                        print(
                            f"[tier3] round={round_index + 1} wrote {written} "
                            f"new records (accepted_delta={after - before}) "
                            f"cost=${cost_tracker.total_usd:.2f}",
                            flush=True,
                        )
                        if after <= before:
                            notes.append("No new accepted records in top-up round; stopped.")
                            break
                    except RuntimeError as exc:
                        print(f"[tier3] aborted: {exc}", flush=True)
                        notes.append(f"Tier 3 aborted: {exc}")
                        break
                if len(load_existing_records(out_prefix)) < target_records:
                    notes.append(
                        "Accepted records ended below target after top-up rounds; "
                        "inspect failure_counts before scaling."
                    )

    all_records = load_existing_records(out_prefix)
    completed_iso = seed.utc_now_iso()
    if provider_name == "gemini":
        price_in = GEMINI_FLASH_LITE_PRICE_PER_M_INPUT
        price_out = GEMINI_FLASH_LITE_PRICE_PER_M_OUTPUT
    else:
        price_in = CLAUDE_PRICE_PER_M_INPUT
        price_out = CLAUDE_PRICE_PER_M_OUTPUT
    write_manifest(
        manifest_path,
        records=all_records,
        started_iso=started_iso,
        completed_iso=completed_iso,
        cost_tracker=cost_tracker,
        failure_counter=failure_counter,
        trace_id=trace_id,
        seed_value=seed_value,
        target_records=target_records,
        out_prefix=out_prefix,
        records_per_shard=records_per_shard,
        primary_model=primary_model,
        final_model=final_model,
        api_key_status=api_key_status,
        dry_run=dry_run,
        resumed_records=len(existing_records),
        notes=notes,
        provider_name=provider_name,
        fallback_model=fallback_model,
        price_per_m_input_usd=price_in,
        price_per_m_output_usd=price_out,
    )
    print(
        f"[done] total={len(all_records)} "
        f"conversations={len({r.get('conversation_id') for r in all_records})} "
        f"cost=${cost_tracker.total_usd:.2f} "
        f"api_calls={cost_tracker.api_calls} "
        f"failures={sum(failure_counter.values())} "
        f"aborted={cost_tracker.aborted}",
        flush=True,
    )
    if failure_counter:
        print("[done] failure causes:", flush=True)
        for cause, count in failure_counter.most_common():
            print(f"   {count:>5d}  {cause}", flush=True)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-records", type=int, default=DEFAULT_TARGET_RECORDS)
    parser.add_argument("--out-prefix", type=Path, default=DEFAULT_OUT_PREFIX)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--records-per-shard", type=int, default=DEFAULT_RECORDS_PER_SHARD)
    parser.add_argument("--seed", type=int, default=20260506)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--cost-cap", type=float, default=DEFAULT_COST_CAP_USD)
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default=DEFAULT_PROVIDER,
        help="LLM provider for dialogue generation. Default: claude.",
    )
    parser.add_argument(
        "--primary-model",
        default=None,
        help=(
            "Primary model name. Default per-provider: "
            f"claude={CLAUDE_DEFAULT_PRIMARY}, gemini={GEMINI_DEFAULT_PRIMARY}."
        ),
    )
    parser.add_argument(
        "--fallback-model",
        default=None,
        help=(
            "Fallback model when primary returns 404. Default per-provider: "
            f"claude={CLAUDE_DEFAULT_FALLBACK}, gemini={GEMINI_DEFAULT_FALLBACK}."
        ),
    )
    parser.add_argument("--env-file", type=Path, default=ENV_FILE_DEFAULT)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate deterministic placeholder dialogues with no API spend.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing shards for this out-prefix.",
    )
    return parser.parse_args(argv)


def _provider_default_models(provider_name: str) -> tuple[str, str]:
    if provider_name == "gemini":
        return GEMINI_DEFAULT_PRIMARY, GEMINI_DEFAULT_FALLBACK
    return CLAUDE_DEFAULT_PRIMARY, CLAUDE_DEFAULT_FALLBACK


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    default_primary, default_fallback = _provider_default_models(args.provider)
    primary_model = args.primary_model or default_primary
    fallback_model = args.fallback_model or default_fallback
    return run(
        target_records=args.target_records,
        out_prefix=args.out_prefix,
        manifest_path=args.manifest,
        records_per_shard=args.records_per_shard,
        seed_value=args.seed,
        concurrency=args.concurrency,
        cost_cap_usd=args.cost_cap,
        primary_model=primary_model,
        fallback_model=fallback_model,
        env_file=args.env_file,
        dry_run=args.dry_run,
        resume=not args.no_resume,
        provider_name=args.provider,
    )


if __name__ == "__main__":
    raise SystemExit(main())
