"""NL-Generation SDG v1: paired (prompt, CAS expression, fluent reply) triples.

Foundation training data for the NL Generation Head — Phase 4 of Version B.

For N records, this script:

  1. Samples a CAS expression covering 10 Noetics x 4 Domains x 7 Drives x 4 Registers,
     with demographic profile + tone varied via the existing
     ``cas_synthetic.generator.demographic_tonal_axes`` taxonomy.
  2. Synthesizes a stylistically plausible English prompt that would naturally
     elicit the sampled CAS state from a respondent.
  3. Calls the Anthropic API to generate a fluent 1-3 sentence English reply
     that EXPRESSES the structural dynamic of the CAS expression without
     mentioning any framework jargon.
  4. Validates each generated reply (length, jargon-absence, ASCII-ish density).
  5. Writes records to JSONL and an aggregate manifest JSON.

USAGE
    # Full 5K run.
    python cas-synthetic/scripts/generate_paired_replies_v1.py \
        --target 5000 \
        --out cas-synthetic/data/generation/v1_paired_5k.jsonl \
        --manifest cas-synthetic/data/generation/v1_paired_5k_manifest.json

    # Smoke test (50 records, half cost cap, no real spend in dry-run).
    python cas-synthetic/scripts/generate_paired_replies_v1.py \
        --target 50 --out /tmp/v1_smoke.jsonl --manifest /tmp/v1_smoke.json \
        --dry-run

ENVIRONMENT
    NC_ANTHROPIC_API_KEY in noetic-compass-scaffold/noetic-compass/.env, or in
    the calling environment. Quotes are stripped on read.

CONSTRAINTS (hard)
    - HARD COST CAP: $100 USD. Aborts mid-run if running estimate exceeds.
    - No files outside cas-synthetic/ are touched by this script.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Load ``demographic_tonal_axes`` directly by file path so we don't trigger
# the rest of the ``generator`` package's __init__ (which imports modules
# requiring an editable install of ``cas_synthetic``).
import importlib.util as _importlib_util  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEMO_AXES_PATH = (
    _REPO_ROOT / "cas-synthetic" / "generator" / "demographic_tonal_axes.py"
)


def _load_demographic_tonal_axes():
    mod_name = "demographic_tonal_axes_local"
    spec = _importlib_util.spec_from_file_location(
        mod_name, _DEMO_AXES_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module spec for {_DEMO_AXES_PATH}")
    module = _importlib_util.module_from_spec(spec)
    # Register in sys.modules BEFORE exec so @dataclass introspection works.
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


_dta = _load_demographic_tonal_axes()
PROFILES = _dta.PROFILES
TONES = _dta.TONES
profile_for = _dta.profile_for
tone_for = _dta.tone_for

try:
    from anthropic import AsyncAnthropic
    from anthropic import APIStatusError, APIConnectionError, RateLimitError
except ImportError:  # pragma: no cover
    AsyncAnthropic = None  # validated lazily in main()
    APIStatusError = APIConnectionError = RateLimitError = Exception  # type: ignore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIMARY_MODEL = "claude-sonnet-4-6"
FALLBACK_MODEL = "claude-3-5-sonnet-20241022"

# Anthropic public list pricing (USD per 1M tokens). Sonnet-class.
# Conservative numbers used for cost ESTIMATION only.
PRICE_PER_M_INPUT = 3.00
PRICE_PER_M_OUTPUT = 15.00

HARD_COST_CAP_USD = 100.0

DEFAULT_CONCURRENCY = 5
MAX_RETRIES = 5
DEFAULT_TEMPERATURE = 0.85
MAX_OUTPUT_TOKENS = 220

REPLY_MIN_CHARS = 10
# 3 fluent English sentences regularly land in the 300-450 char range. The
# 600-char ceiling preserves the "1-3 sentence" target without dropping
# good-quality replies on length alone (the system prompt biases the model
# toward <=480 chars; this ceiling tolerates a small overshoot).
REPLY_MAX_CHARS = 600

ENV_FILE_DEFAULT = (
    _REPO_ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / ".env"
)

NOETICS = {
    "^0": ("Idea", "All things in and outside the Mind."),
    "^1": ("Mind", "Various degrees of awareness that processes, stores, outputs, and intakes Ideas."),
    "^2": ("Positive", "An Idea the Mind has an affinity for and is attracted toward."),
    "^3": ("Negative", "An Idea the Mind is adverse to and repelled by."),
    "^4": ("Vibration", "The degree to which an Idea resonates with the Mind, its impression."),
    "^5": ("Female", "A Mind impregnated with an Idea, the Ideas a Mind is composed of."),
    "^6": ("Male", "An Idea impregnated with another Idea, the Ideas an Idea is composed of."),
    "^7": ("Rhythm", "The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it."),
    "^8": ("Above/Cause", "An Idea that triggers a different Idea than itself to come to Mind."),
    "^9": ("Below/Effect", "The Idea brought to Mind by an Above/Cause trigger."),
}

DOMAINS = {
    "P": "Principled",
    "C": "Cognitive",
    "E": "Evaluative",
    "O": "Operational",
}

DRIVES = {
    "F1": "Unity",
    "F2": "Wisdom",
    "F3": "Vitality",
    "F4": "Connection",
    "F5": "Agency",
    "F6": "Structure",
    "F7": "Purpose",
}

REGISTERS = {
    "T": "Transcendent",
    "A": "Analytical",
    "f": "Affective",
    "E": "Embodied",
}

REGISTER_INSTRUCTIONS = {
    "T": (
        "transcendent — high-abstraction, purpose-orienting, integrative; "
        "felt sense of meaning or vision, NOT a felt-emotion line and NOT a "
        "step-by-step argument."
    ),
    "A": (
        "analytical — explicit, sequential, logical reasoning; lay out a "
        "step or premise; do NOT lead with a feeling word."
    ),
    "f": (
        "affective — feeling-toned, value-laden; the sentence should carry "
        "an emotional valence; do NOT present a chain of reasoning."
    ),
    "E": (
        "embodied — sensorimotor, bodily, concrete; gut/body language, "
        "physical action vocabulary; do NOT abstract away from the body."
    ),
}


# Anti-drift register-aware nudges, layered on top of the Noetic colloquialism map.
NOETIC_NUDGES = {
    "^0": "neutral content / 'an idea'.",
    "^1": "paying attention / making up your mind / using your head.",
    "^2": "drawn to / speaks to me / can't resist.",
    "^3": (
        "VISCERAL aversion (NOT analytical critique) — can't stomach it / "
        "rubs me the wrong way / wouldn't touch it with a ten-foot pole."
    ),
    "^4": "struck a chord / hit me hard / made an impression / resonated.",
    "^5": (
        "accumulated experience composing the Mind — shaped by years / "
        "made me who I am / part of what makes me me."
    ),
    "^6": (
        "compositional decomposition (NOT aversion) — unpacking, breaking it down, "
        "looking at what's underneath, pulling apart the argument."
    ),
    "^7": (
        "rhythmic repetition entraining the Mind — practice, every day, "
        "muscle memory, getting into a groove."
    ),
    "^8": (
        "ASSOCIATIVE TRIGGERING (NOT deductive reasoning) — that reminds me / "
        "one thing leads to another / triggered a memory."
    ),
    "^9": (
        "the surfaced Idea — popped into my head / out of nowhere I thought of / "
        "it just clicked.",
    ),
}
# Flatten any tuple in NOETIC_NUDGES (the ^9 entry above is a tuple typo guard).
for _k, _v in list(NOETIC_NUDGES.items()):
    if isinstance(_v, tuple):
        NOETIC_NUDGES[_k] = " ".join(_v)


# ---------------------------------------------------------------------------
# Prompt-elicitation seeds (varied by domain)
# ---------------------------------------------------------------------------

PROMPT_SEEDS = {
    "P": [
        "What's your honest take on the situation in {topic}?",
        "Where do you draw the line on {topic}?",
        "If someone asked you what you stand for around {topic}, what would you say?",
        "Is there a principle you wouldn't bend on when it comes to {topic}?",
        "How do you decide what's right when {topic} comes up?",
    ],
    "C": [
        "Walk me through your thinking on {topic}.",
        "How do you make sense of {topic}?",
        "What model do you use to understand {topic}?",
        "Can you explain how you'd analyze {topic}?",
        "What's the structure you see in {topic}?",
    ],
    "E": [
        "How do you feel about {topic}?",
        "What's your reaction to {topic}?",
        "When {topic} comes up, what's the first thing that hits you?",
        "Can you describe the impression {topic} leaves on you?",
        "What does {topic} bring up for you?",
    ],
    "O": [
        "What would you actually do about {topic}?",
        "If you had to take action on {topic} this week, what would you start with?",
        "How would you put {topic} into practice?",
        "What's your routine around {topic}?",
        "Walk me through how you'd execute on {topic}.",
    ],
}

TOPICS = [
    "a coworker repeatedly cutting corners on safety",
    "the spiritual side of a long career",
    "a habit you've kept for years",
    "an old song that came on the radio",
    "deciding whether to take a risky job offer",
    "the way your mentor shaped you",
    "a community ritual you grew up with",
    "letting someone down to keep a promise to yourself",
    "the smell of a particular meal",
    "watching someone you love struggle",
    "a public figure breaking a vow",
    "the muscle memory of a sport",
    "a rule you're not willing to break",
    "stepping into a leadership role you didn't ask for",
    "a piece of feedback that landed hard",
    "an unexpected memory while driving",
    "the discipline of daily practice",
    "facing a decision with no good options",
    "a sudden realization in the middle of a conversation",
    "the feeling of finally breaking a pattern",
    "training with a difficult teacher",
    "an idea that won't leave you alone",
    "a values clash with a close friend",
    "the texture of a workplace you used to belong to",
    "a piece of art that won't let you go",
    "an instruction that triggered another memory",
    "deciding what to teach the next generation",
    "an old wound that keeps showing up",
    "what 'home' actually means to you",
    "a pattern you're trying to unlearn",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1]
    return v


def load_api_key(env_file: Path) -> str | None:
    """Return the NC_ANTHROPIC_API_KEY value, preferring the env over a .env file."""
    key = os.environ.get("NC_ANTHROPIC_API_KEY")
    if key:
        return _strip_quotes(key)
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "NC_ANTHROPIC_API_KEY":
                return _strip_quotes(v)
    return None


def sample_axes(rng: random.Random) -> dict[str, str]:
    """Sample one (noetic, domain, drive, register, profile_code, tone_code, topic)."""
    n_code = rng.choice(list(NOETICS.keys()))
    d_code = rng.choice(list(DOMAINS.keys()))
    f_code = rng.choice(list(DRIVES.keys()))
    r_code = rng.choice(list(REGISTERS.keys()))
    profile = rng.choice(PROFILES).code
    tone = rng.choice(TONES).code
    topic = rng.choice(TOPICS)
    return {
        "noetic": n_code,
        "domain": d_code,
        "drive": f_code,
        "register": r_code,
        "profile": profile,
        "tone": tone,
        "topic": topic,
    }


def build_cas_expression(noetic: str, domain: str, drive: str, register: str) -> str:
    """Render a v7.5-style Register-specified compound expression: ``^n^D_{F_k}|R``."""
    return f"{noetic}^{domain}_{{{drive}}}|{register}"


def synthesize_prompt(rng: random.Random, axes: dict[str, str]) -> str:
    """Pick a domain-aware seed prompt and fill ``{topic}`` with a sampled topic."""
    seeds = PROMPT_SEEDS[axes["domain"]]
    seed = rng.choice(seeds)
    return seed.format(topic=axes["topic"])


def render_user_message(axes: dict[str, str], prompt_text: str, cas_expr: str) -> str:
    """Render the per-record user-message body Claude sees."""
    n_code = axes["noetic"]
    n_name, n_def = NOETICS[n_code]
    d_code = axes["domain"]
    f_code = axes["drive"]
    r_code = axes["register"]
    nudge = NOETIC_NUDGES[n_code]
    register_instr = REGISTER_INSTRUCTIONS[r_code]

    profile = profile_for(axes["profile"])
    tone = tone_for(axes["tone"])

    return (
        f"CAS expression: {cas_expr}\n"
        f"- Noetic {n_code}: {n_name} — {n_def}\n"
        f"  Anti-drift cue: {nudge}\n"
        f"- Domain {d_code}: {DOMAINS[d_code]}\n"
        f"- Drive {f_code}: {DRIVES[f_code]}\n"
        f"- Register |{r_code}: {REGISTERS[r_code]}\n\n"
        "User context:\n"
        f"- Demographic profile: {profile.name} — {profile.description}\n"
        f"- Tone: {tone.name} — {tone.description}\n\n"
        f"User prompt: \"{prompt_text}\"\n\n"
        "Generate a 1-3 sentence English reply that:\n"
        "1. Expresses the CAS structural dynamic (do NOT mention CAS / Noetic / "
        "Domain / Drive / Register / framework / operator / |[TAfE] / ^N notation).\n"
        "2. Sounds like a real person talking, not a template. Avoid 'Reading "
        "this as...' / 'This maps to a state of...' / 'I sense...' opener "
        "patterns.\n"
        f"3. Matches the Register: {register_instr}\n"
        f"4. Tracks the demographic profile's voice (use the profile's "
        f"natural lexicon, avoid the profile's avoid_lexicon) and the tone's "
        f"energy.\n"
        "5. Keep total length UNDER 480 characters. Brevity is preferred over "
        "elaboration; cut a sentence rather than overshoot.\n\n"
        "CRITICAL: Output ONLY the reply text. No labels, no preamble, no "
        "closing remarks, no quote marks around it."
    )


SYSTEM_PROMPT = (
    "You are generating training data for a CAS LLM. Generate authentic "
    "conversational English replies that internally express specific CAS "
    "structural dynamics. The reply must read as natural human speech in the "
    "given demographic and tonal voice. Never mention any framework jargon."
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Forbidden words / patterns. Case-insensitive.
JARGON_PATTERNS = [
    re.compile(r"\bnoetic[s]?\b", re.IGNORECASE),
    re.compile(r"\bdomain[s]?\b", re.IGNORECASE),
    re.compile(r"\bregister[s]?\b", re.IGNORECASE),
    re.compile(r"\bdrive[s]?\b", re.IGNORECASE),
    re.compile(r"\bcas\b", re.IGNORECASE),
    re.compile(r"\bF[1-7]\b"),
    re.compile(r"\^[0-9]"),
    re.compile(r"\|[TAfE]\b"),
    re.compile(r"\boperator\b", re.IGNORECASE),
    re.compile(r"\bcompound state\b", re.IGNORECASE),
]

TEMPLATE_OPENERS = [
    re.compile(r"^\s*reading this as\b", re.IGNORECASE),
    re.compile(r"^\s*this maps to\b", re.IGNORECASE),
    re.compile(r"^\s*this expresses\b", re.IGNORECASE),
    re.compile(r"^\s*i (?:detect|sense|perceive|interpret)\b", re.IGNORECASE),
]


def looks_like_english(text: str) -> bool:
    """Reject if letter-density is too low (e.g. mostly symbols)."""
    if not text:
        return False
    letters = sum(1 for ch in text if ch.isalpha())
    return letters >= max(8, int(0.5 * len(text)))


def validate_reply(text: str) -> tuple[bool, str]:
    """Return ``(ok, reason)``. On ok=True reason is the empty string."""
    if not text:
        return False, "empty"
    s = text.strip()
    # Strip optional leading/trailing quote marks the model occasionally adds.
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"', "`"):
        s = s[1:-1].strip()
    if len(s) < REPLY_MIN_CHARS:
        return False, "too_short"
    if len(s) > REPLY_MAX_CHARS:
        return False, "too_long"
    if not looks_like_english(s):
        return False, "low_letter_density"
    for pat in JARGON_PATTERNS:
        if pat.search(s):
            return False, f"jargon:{pat.pattern}"
    for pat in TEMPLATE_OPENERS:
        if pat.search(s):
            return False, "template_opener"
    return True, ""


def clean_reply(text: str) -> str:
    """Trim wrapping quotes and surrounding whitespace."""
    s = text.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"', "`"):
        s = s[1:-1].strip()
    return s


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

class CostTracker:
    def __init__(self, hard_cap_usd: float):
        self.hard_cap_usd = hard_cap_usd
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_calls = 0
        self._lock = asyncio.Lock()
        self._aborted = False

    @property
    def total_usd(self) -> float:
        return (
            self.input_tokens * PRICE_PER_M_INPUT / 1_000_000.0
            + self.output_tokens * PRICE_PER_M_OUTPUT / 1_000_000.0
        )

    async def add(self, in_tokens: int, out_tokens: int) -> bool:
        async with self._lock:
            self.input_tokens += in_tokens
            self.output_tokens += out_tokens
            self.api_calls += 1
            if self.total_usd > self.hard_cap_usd:
                self._aborted = True
                return False
            return True

    @property
    def aborted(self) -> bool:
        return self._aborted


# ---------------------------------------------------------------------------
# Anthropic call (async, with retry/backoff and model fallback)
# ---------------------------------------------------------------------------

async def call_claude(
    client: Any,
    user_message: str,
    *,
    model: str,
    cost_tracker: CostTracker,
    temperature: float = DEFAULT_TEMPERATURE,
) -> tuple[str | None, str, str | None]:
    """Call Claude with exponential backoff. Returns ``(text, model_used, error_reason)``.

    On 404 / model-not-found for the primary model, raises an exception so the
    caller can switch to the fallback model globally.
    """
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.messages.create(
                model=model,
                max_tokens=MAX_OUTPUT_TOKENS,
                temperature=temperature,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
        except RateLimitError as exc:
            last_exc = exc
            wait = min(60.0, 2.0 ** attempt + random.random())
            await asyncio.sleep(wait)
            continue
        except APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            if status in (429, 529, 500, 502, 503, 504):
                last_exc = exc
                wait = min(60.0, 2.0 ** attempt + random.random())
                await asyncio.sleep(wait)
                continue
            if status == 404:
                # Caller will switch model globally.
                raise
            return None, model, f"api_status_{status}"
        except APIConnectionError as exc:
            last_exc = exc
            wait = min(30.0, 2.0 ** attempt + random.random())
            await asyncio.sleep(wait)
            continue
        except Exception as exc:  # noqa: BLE001
            return None, model, f"unexpected:{type(exc).__name__}:{exc}"

        # Success path.
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
        for p in (resp.content or []):
            t = getattr(p, "text", None)
            if t:
                text_parts.append(t)
        text = "".join(text_parts)
        return text, model, None

    return None, model, f"retries_exhausted:{type(last_exc).__name__ if last_exc else 'unknown'}"


# ---------------------------------------------------------------------------
# Worker pool
# ---------------------------------------------------------------------------

class GenerationContext:
    """Mutable shared state across concurrent workers."""

    def __init__(
        self,
        client: Any,
        out_path: Path,
        cost_tracker: CostTracker,
        primary_model: str = PRIMARY_MODEL,
        fallback_model: str = FALLBACK_MODEL,
    ) -> None:
        self.client = client
        self.out_path = out_path
        self.cost_tracker = cost_tracker
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.current_model = primary_model
        self.write_lock = asyncio.Lock()
        self.failure_counter: Counter[str] = Counter()
        self.success_count = 0
        self.last_logged_at = 0


async def generate_one_record(
    ctx: GenerationContext,
    rec_id: str,
    axes: dict[str, str],
    cas_expr: str,
    prompt_text: str,
    user_message: str,
) -> dict | None:
    """Generate, validate, and (on success) return the assembled record."""
    if ctx.cost_tracker.aborted:
        return None

    # First attempt at default temperature.
    text, model_used, err = await call_claude(
        ctx.client,
        user_message,
        model=ctx.current_model,
        cost_tracker=ctx.cost_tracker,
    )
    if text is None and err == "api_status_404" and ctx.current_model == ctx.primary_model:
        # Fallback once globally.
        ctx.current_model = ctx.fallback_model
        text, model_used, err = await call_claude(
            ctx.client,
            user_message,
            model=ctx.current_model,
            cost_tracker=ctx.cost_tracker,
        )

    if text is None:
        ctx.failure_counter[err or "unknown_api_error"] += 1
        return None

    cleaned = clean_reply(text)
    ok, reason = validate_reply(cleaned)
    if not ok:
        # Retry once at lower temperature.
        text2, model_used2, err2 = await call_claude(
            ctx.client,
            user_message,
            model=ctx.current_model,
            cost_tracker=ctx.cost_tracker,
            temperature=0.55,
        )
        if text2 is None:
            ctx.failure_counter[f"retry_api:{err2 or 'unknown'}"] += 1
            return None
        cleaned2 = clean_reply(text2)
        ok2, reason2 = validate_reply(cleaned2)
        if not ok2:
            ctx.failure_counter[f"validation:{reason}->{reason2}"] += 1
            return None
        cleaned = cleaned2
        model_used = model_used2

    profile = profile_for(axes["profile"])
    tone = tone_for(axes["tone"])
    record = {
        "id": rec_id,
        "prompt": prompt_text,
        "cas_expression": cas_expr,
        "reply": cleaned,
        "demographic_profile": profile.name,
        "demographic_profile_code": profile.code,
        "tone": tone.name,
        "tone_code": tone.code,
        "noetic": axes["noetic"],
        "domain": axes["domain"],
        "drive": axes["drive"],
        "register": axes["register"],
        "topic_seed": axes["topic"],
        "model_used": model_used,
        "generation_version": "v1",
    }
    return record


async def append_record(ctx: GenerationContext, record: dict) -> None:
    async with ctx.write_lock:
        with ctx.out_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        ctx.success_count += 1
        if ctx.success_count - ctx.last_logged_at >= 500:
            ctx.last_logged_at = ctx.success_count
            print(
                f"[progress] successes={ctx.success_count} "
                f"api_calls={ctx.cost_tracker.api_calls} "
                f"cost_estimate=${ctx.cost_tracker.total_usd:.2f} "
                f"failures={sum(ctx.failure_counter.values())}",
                flush=True,
            )


async def worker(
    ctx: GenerationContext,
    sem: asyncio.Semaphore,
    job: dict,
) -> None:
    if ctx.cost_tracker.aborted:
        return
    async with sem:
        if ctx.cost_tracker.aborted:
            return
        record = await generate_one_record(
            ctx,
            rec_id=job["id"],
            axes=job["axes"],
            cas_expr=job["cas_expression"],
            prompt_text=job["prompt"],
            user_message=job["user_message"],
        )
        if record is not None:
            await append_record(ctx, record)


# ---------------------------------------------------------------------------
# Sampling: build the full job list deterministically
# ---------------------------------------------------------------------------

def build_jobs(
    target: int,
    seed: int,
    already_done: set[str],
) -> list[dict]:
    """Pre-build target jobs deterministically. ``already_done`` IDs are skipped."""
    rng = random.Random(seed)
    jobs: list[dict] = []
    for i in range(1, target + 1):
        rec_id = f"gen_v1_{i:05d}"
        if rec_id in already_done:
            continue
        axes = sample_axes(rng)
        cas_expr = build_cas_expression(
            axes["noetic"], axes["domain"], axes["drive"], axes["register"]
        )
        prompt_text = synthesize_prompt(rng, axes)
        user_message = render_user_message(axes, prompt_text, cas_expr)
        jobs.append({
            "id": rec_id,
            "axes": axes,
            "cas_expression": cas_expr,
            "prompt": prompt_text,
            "user_message": user_message,
        })
    return jobs


def already_done_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    done: set[str] = set()
    with out_path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            rid = rec.get("id")
            if rid:
                done.add(rid)
    return done


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def write_manifest(
    manifest_path: Path,
    *,
    out_path: Path,
    started_iso: str,
    completed_iso: str,
    cost: CostTracker,
    target: int,
    primary_model: str,
    final_model: str,
    failure_counter: Counter,
) -> dict:
    distributions: dict[str, Counter] = {
        "noetic": Counter(),
        "domain": Counter(),
        "drive": Counter(),
        "register": Counter(),
        "demographic_profile": Counter(),
        "tone": Counter(),
        "model_used": Counter(),
    }
    total = 0
    if out_path.exists():
        with out_path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                total += 1
                for key in distributions:
                    if key == "demographic_profile":
                        distributions[key][rec.get("demographic_profile", "?")] += 1
                    elif key == "tone":
                        distributions[key][rec.get("tone", "?")] += 1
                    elif key == "model_used":
                        distributions[key][rec.get("model_used", "?")] += 1
                    else:
                        distributions[key][rec.get(key, "?")] += 1

    manifest = {
        "version": "v1",
        "target_records": target,
        "total_records": total,
        "primary_model": primary_model,
        "final_model": final_model,
        "noetic_distribution": dict(distributions["noetic"]),
        "domain_distribution": dict(distributions["domain"]),
        "drive_distribution": dict(distributions["drive"]),
        "register_distribution": dict(distributions["register"]),
        "demographic_distribution": dict(distributions["demographic_profile"]),
        "tone_distribution": dict(distributions["tone"]),
        "model_used_distribution": dict(distributions["model_used"]),
        "total_cost_usd": round(cost.total_usd, 4),
        "input_tokens": cost.input_tokens,
        "output_tokens": cost.output_tokens,
        "api_calls": cost.api_calls,
        "hard_cost_cap_usd": cost.hard_cap_usd,
        "cost_aborted": cost.aborted,
        "failure_counts": dict(failure_counter),
        "generation_started": started_iso,
        "generation_completed": completed_iso,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(
    target: int,
    out_path: Path,
    manifest_path: Path,
    *,
    concurrency: int,
    seed: int,
    primary_model: str,
    fallback_model: str,
    cost_cap_usd: float,
    api_key: str,
    dry_run: bool,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    done = already_done_ids(out_path)
    if done:
        print(f"[resume] {len(done)} records already in {out_path.name}; skipping these IDs", flush=True)

    started_iso = datetime.now(timezone.utc).isoformat()
    cost_tracker = CostTracker(cost_cap_usd)

    if dry_run:
        # Dry-run path: build a synthetic record per axis sample, no API calls.
        jobs = build_jobs(target, seed, done)
        for job in jobs:
            axes = job["axes"]
            profile = profile_for(axes["profile"])
            tone = tone_for(axes["tone"])
            placeholder = (
                f"Sketch reply for {axes['noetic']}{axes['domain']}|{axes['register']} "
                f"that would read as {profile.name} in a {tone.name} tone."
            )
            record = {
                "id": job["id"],
                "prompt": job["prompt"],
                "cas_expression": job["cas_expression"],
                "reply": placeholder,
                "demographic_profile": profile.name,
                "demographic_profile_code": profile.code,
                "tone": tone.name,
                "tone_code": tone.code,
                "noetic": axes["noetic"],
                "domain": axes["domain"],
                "drive": axes["drive"],
                "register": axes["register"],
                "topic_seed": axes["topic"],
                "model_used": "dry-run",
                "generation_version": "v1",
            }
            with out_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        completed_iso = datetime.now(timezone.utc).isoformat()
        write_manifest(
            manifest_path,
            out_path=out_path,
            started_iso=started_iso,
            completed_iso=completed_iso,
            cost=cost_tracker,
            target=target,
            primary_model=primary_model,
            final_model="dry-run",
            failure_counter=Counter(),
        )
        print(f"[dry-run] wrote {len(jobs)} placeholder records to {out_path}", flush=True)
        return 0

    if AsyncAnthropic is None:
        raise RuntimeError("anthropic SDK not installed. Run: pip install anthropic")

    client = AsyncAnthropic(api_key=api_key)
    ctx = GenerationContext(
        client=client,
        out_path=out_path,
        cost_tracker=cost_tracker,
        primary_model=primary_model,
        fallback_model=fallback_model,
    )

    # Pre-flight: cheap probe call to detect entitlement and pick a model.
    probe_message = "Reply with the single word: ok"
    probe_text, probe_model, probe_err = await call_claude(
        client,
        probe_message,
        model=primary_model,
        cost_tracker=cost_tracker,
        temperature=0.0,
    )
    if probe_text is None and probe_err == "api_status_404":
        print(f"[preflight] primary model {primary_model} unavailable, falling back to {fallback_model}", flush=True)
        ctx.current_model = fallback_model
        probe_text, probe_model, probe_err = await call_claude(
            client,
            probe_message,
            model=fallback_model,
            cost_tracker=cost_tracker,
            temperature=0.0,
        )
    if probe_text is None:
        raise RuntimeError(f"preflight call failed: {probe_err}")
    print(f"[preflight] using model {ctx.current_model}; probe ok", flush=True)

    # Estimate ballpark cost: ~ 600 input tokens + ~ 80 output tokens per call.
    est_in_per = 600
    est_out_per = 80
    est_total = (
        target * est_in_per * PRICE_PER_M_INPUT / 1_000_000.0
        + target * est_out_per * PRICE_PER_M_OUTPUT / 1_000_000.0
    )
    print(f"[preflight] estimated cost for {target} records: ~${est_total:.2f} (cap=${cost_cap_usd:.2f})", flush=True)
    if est_total > cost_cap_usd:
        raise RuntimeError(
            f"estimated cost ${est_total:.2f} exceeds cost cap ${cost_cap_usd:.2f}; "
            f"reduce --target or raise --cost-cap"
        )

    jobs = build_jobs(target, seed, done)
    print(f"[run] {len(jobs)} jobs to execute (target={target}, already_done={len(done)})", flush=True)

    sem = asyncio.Semaphore(concurrency)
    tasks = [asyncio.create_task(worker(ctx, sem, job)) for job in jobs]
    # Fan in.
    await asyncio.gather(*tasks, return_exceptions=False)

    completed_iso = datetime.now(timezone.utc).isoformat()
    manifest = write_manifest(
        manifest_path,
        out_path=out_path,
        started_iso=started_iso,
        completed_iso=completed_iso,
        cost=cost_tracker,
        target=target,
        primary_model=primary_model,
        final_model=ctx.current_model,
        failure_counter=ctx.failure_counter,
    )
    print(
        f"[done] total_records={manifest['total_records']} "
        f"cost=${cost_tracker.total_usd:.2f} "
        f"api_calls={cost_tracker.api_calls} "
        f"failures={sum(ctx.failure_counter.values())} "
        f"aborted={cost_tracker.aborted}",
        flush=True,
    )
    if ctx.failure_counter:
        print("[done] failure causes:", flush=True)
        for cause, count in ctx.failure_counter.most_common():
            print(f"   {count:>5d}  {cause}", flush=True)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", type=int, default=5000)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20260504)
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--primary-model", default=PRIMARY_MODEL)
    p.add_argument("--fallback-model", default=FALLBACK_MODEL)
    p.add_argument("--cost-cap", type=float, default=HARD_COST_CAP_USD)
    p.add_argument("--env-file", type=Path, default=ENV_FILE_DEFAULT)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    api_key = ""
    if not args.dry_run:
        api_key = load_api_key(args.env_file) or ""
        if not api_key or not api_key.startswith("sk-ant-"):
            sys.stderr.write(
                "[fatal] NC_ANTHROPIC_API_KEY missing or malformed. "
                f"Looked in env and {args.env_file}.\n"
            )
            return 2

    return asyncio.run(
        run(
            target=args.target,
            out_path=args.out,
            manifest_path=args.manifest,
            concurrency=args.concurrency,
            seed=args.seed,
            primary_model=args.primary_model,
            fallback_model=args.fallback_model,
            cost_cap_usd=args.cost_cap,
            api_key=api_key,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
