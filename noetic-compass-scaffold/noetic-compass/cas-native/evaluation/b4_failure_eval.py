"""B-4 human-relevance failure eval harness.

Step B of the four-step v1 plan after the B-3 model failed the human relevance
audit on 2026-05-07. This harness runs the B-3 checkpoint against a curated
50-100 prompt fixture set and scores every reply along seven user-facing
dimensions plus a delegated compiler-structural-preservation check (Agent D).

The goal is automation: never put a human through that audit again until the
model has passed automated checks first.

Failure modes targeted (from docs/working/path_B4_human_relevance_failure_2026_05_07.md):

  1. Irrelevance              — fluent reply that does not address the prompt
  2. Drunk coherence          — token-level fluent, discourse-level incoherent
  3. OOD ships anyway         — K=9 produces confident CAS for casual prompts
  4. Compiler round-trip lost — recipe ingredients/coefficients/arrows stripped
  5. Structural-shape-only    — silhouette preserved, content stripped

Scoring dimensions
------------------

User-facing (per reply):

  * relevance              1-5  prompt<->reply embedding/TF-IDF cosine bucketed
  * directness             1-5  2nd-person addressing markers + question-shape
  * non_rambling           1-5  inverse log-length penalty above threshold
  * compiler_validity      bool reply parses + compiles via api/notation/compiler
  * structural_preservation delegated to Agent D's compiler_preservation_scorer
                            (placeholder used when Agent D's file is missing)
  * plain_language_clarity 1-5  inverse-correlated to CAS-jargon density
  * leakage                bool any CAS notation visible to the user

Auto-scorer notes (transparent proxies, NOT human judgement):

  Auto-relevance is a TF-IDF cosine proxy for prompt<->reply topical overlap.
  It catches the documented "fluent prose unrelated to prompt" failure but
  cannot judge semantic relevance the way a human can. Treat it as a coarse
  fail-detector: very low scores indicate the documented irrelevance failure;
  middling scores still need human review.

  Auto-directness counts 2nd-person pronouns and clarifying-question markers.
  Catches monologic reflective prose; cannot distinguish good direct address
  from awkward direct address.

  Auto-non_rambling is a length penalty above an empirical threshold.
  Catches the documented "rambling reflective prose" mode; not a stylistic
  judgement.

  Auto-plain_language_clarity is inversely correlated to CAS-jargon density.
  Catches stage-2 outputs that explain CAS using CAS terminology.

CLI
---

    python -m cas_native.evaluation.b4_failure_eval \
        --checkpoint <path-to-runs/b3_full_50k_prodshape_20260507> \
        --prompts cas-native/evaluation/fixtures/b4_failure_prompts.jsonl \
        --out runs/b4_eval/b4_failure_eval_<date>.json

The harness is deliberately self-contained except for two integrations:

  * inference: ``cas_native.inference.predict_cas.load_predictor`` (Stage 1
    K=9 classifier) plus ``cas_native.inference.native_nl_generate.generate_reply``
    (Stage 2 native NL generation). It re-implements the load+chain logic
    that ``cas_native.inference.chat.py`` performs so this harness does NOT
    touch chat.py (Agent C owns chat.py).

  * scoring: ``cas_native.evaluation.compiler_preservation_scorer.score_preservation``
    (Agent D) for ground-truth ↔ Stage-1 prediction structural preservation.
    A placeholder is used until Agent D's file lands.

This harness MEASURES the failures. It does not fix them.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import re
import sys
import types
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Any


# ---------------------------------------------------------------------------
# Path bootstrap — mirror predict_cas.py / chat.py
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT_CANDIDATE = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
if _REPO_ROOT_CANDIDATE.exists():
    REPO_ROOT = _REPO_ROOT_CANDIDATE
else:
    # _THIS_FILE = .../cas-native/evaluation/b4_failure_eval.py
    # parents[2]  = .../noetic-compass
    REPO_ROOT = _THIS_FILE.resolve().parents[2]

if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(REPO_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Constants & regexes
# ---------------------------------------------------------------------------

# leakage = does the user-facing reply contain CAS notation? Per-spec regex.
_LEAKAGE_PATTERN = re.compile(r"\^[0-9]\^[PCEO]|\bF[1-7]\b|\|⟨|Δ°|RPM")

# Wider CAS-jargon density regex — used by plain_language_clarity scorer only.
_CAS_JARGON_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\^[0-9]"),                               # ^0..^9
    re.compile(r"\bF[1-7]\b"),                            # F1..F7
    re.compile(r"\|[TAfE]\b"),                            # |T |A |f |E
    re.compile(r"\bnoetic[s]?\b", re.IGNORECASE),
    re.compile(r"\bregister[s]?\b", re.IGNORECASE),
    re.compile(r"\bdomain[s]?\b", re.IGNORECASE),
    re.compile(r"\bdrive[s]?\b", re.IGNORECASE),
    re.compile(r"\binvolution\b", re.IGNORECASE),
    re.compile(r"\bRPM\b"),
    re.compile(r"\bCAS\b"),
    re.compile(r"Θ|Ω|⟨|⟩"),                                 # Theta, Omega, angle brackets
]

# directness markers — 2nd-person / addressing markers
_DIRECTNESS_PRONOUNS = re.compile(r"\byou(?:r|'re|'ve|'ll|'d)?\b", re.IGNORECASE)
_DIRECTNESS_QUESTION_OPENERS = re.compile(
    r"^\s*(?:what|why|how|when|where|which|who|are|is|do|does|did|can|could|"
    r"will|would|should)\b",
    re.IGNORECASE,
)

# default rambling threshold (chars). Beyond this we begin to penalize.
_RAMBLE_SOFT_THRESHOLD = 240
_RAMBLE_HARD_THRESHOLD = 800


# ---------------------------------------------------------------------------
# Compiler-preservation placeholder (Agent D owns the real one)
# ---------------------------------------------------------------------------


@dataclass
class PreservationResult:
    """Placeholder shape for Agent D's compiler_preservation_scorer output.

    DO NOT replace this with a real scorer; Agent D writes the canonical
    version at ``cas_native.evaluation.compiler_preservation_scorer``. This
    harness imports that module if available and falls back to this stub
    otherwise so the run can still produce a manifest before Agent D lands.

    Sub-check fields (booleans) match the failure record's structural-shape
    decomposition: operands, operators, drives, coefficients, named targets.
    """

    operands_preserved: bool = False
    operators_preserved: bool = False
    drives_preserved: bool = False
    coefficients_preserved: bool = False
    named_targets_preserved: bool = False
    score: float = 0.0  # 0.0 == placeholder, real scorer will fill this
    placeholder: bool = True
    notes: str = "Agent D scorer not yet imported; placeholder used."


def _placeholder_score_preservation(
    ground_truth: str | None,
    predicted_expression: str,
) -> PreservationResult:
    """Conservative stub: report all-false + placeholder=True.

    The real scorer is the responsibility of Agent D
    (``compiler_preservation_scorer.score_preservation``). When this module is
    not yet on disk, we emit a placeholder so the harness still produces a
    manifest. Agent D's signature is expected to be::

        score_preservation(ground_truth: str | None, predicted: str) -> PreservationResult

    with a richer ``PreservationResult`` carrying the same field names.
    """
    return PreservationResult(
        placeholder=True,
        score=0.0,
        notes=(
            "compiler_preservation_scorer not importable; per-sub-check booleans "
            "default to False. This is NOT a real preservation failure — re-run "
            "after Agent D lands."
        ),
    )


def _resolve_preservation_scorer():
    """Import Agent D's scorer if available; else return the placeholder.

    Returns a callable ``(ground_truth, predicted) -> PreservationResult``.
    """
    try:
        mod = importlib.import_module(
            "cas_native.evaluation.compiler_preservation_scorer"
        )
    except ImportError:
        return _placeholder_score_preservation

    # Agent D is expected to expose score_preservation. Be defensive about names.
    fn = getattr(mod, "score_preservation", None)
    if fn is None:
        # Agent D may name it differently — fall back to placeholder rather
        # than guessing. This is logged by the harness.
        return _placeholder_score_preservation
    return fn


# ---------------------------------------------------------------------------
# Auto-scorer primitives
# ---------------------------------------------------------------------------


def _word_set(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w\s]", " ", (text or "").lower())
    return {w for w in cleaned.split() if len(w) >= 2}


def _word_list(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\s]", " ", (text or "").lower())
    return [w for w in cleaned.split() if len(w) >= 2]


def tfidf_cosine(prompt: str, reply: str) -> float:
    """Stand-in TF-IDF cosine on a 2-document corpus.

    Cosine is computed over the union vocabulary of the prompt and reply.
    Each document's term-frequency is normalized (TF), and inverse-document-
    frequency uses log((1+N)/(1+df)) + 1 over the 2-document corpus.

    Returns a float in [0, 1]. Empty inputs return 0.0.

    This is deliberately dependency-free (no sklearn / sentence-transformers).
    The cost is a less semantically-informed similarity; the benefit is the
    harness runs anywhere the model runs.
    """
    p_words = _word_list(prompt)
    r_words = _word_list(reply)
    if not p_words or not r_words:
        return 0.0

    docs = [p_words, r_words]
    vocab = sorted(set(p_words) | set(r_words))
    if not vocab:
        return 0.0

    n_docs = 2
    df = {term: sum(1 for d in docs if term in d) for term in vocab}
    idf = {
        term: math.log((1 + n_docs) / (1 + df[term])) + 1.0 for term in vocab
    }

    def tfidf_vec(doc_words: list[str]) -> list[float]:
        if not doc_words:
            return [0.0] * len(vocab)
        counts: dict[str, int] = defaultdict(int)
        for w in doc_words:
            counts[w] += 1
        total = float(len(doc_words))
        return [(counts.get(t, 0) / total) * idf[t] for t in vocab]

    v_p = tfidf_vec(p_words)
    v_r = tfidf_vec(r_words)
    dot = sum(a * b for a, b in zip(v_p, v_r))
    norm_p = math.sqrt(sum(a * a for a in v_p))
    norm_r = math.sqrt(sum(a * a for a in v_r))
    if norm_p == 0.0 or norm_r == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_p * norm_r)))


def _maybe_sentence_transformer_cosine(prompt: str, reply: str) -> float | None:
    """Try sentence-transformers if installed; otherwise return None.

    Cached at module level so the model is loaded at most once.
    """
    try:
        st = importlib.import_module("sentence_transformers")
    except ImportError:
        return None

    global _ST_MODEL  # noqa: PLW0603 — module-level cache is intentional
    try:
        _ST_MODEL  # type: ignore[name-defined]
    except NameError:
        try:
            _ST_MODEL = st.SentenceTransformer("all-MiniLM-L6-v2")  # type: ignore[name-defined]
        except Exception:  # pragma: no cover - hostile environment
            return None

    try:
        embeddings = _ST_MODEL.encode([prompt, reply], convert_to_numpy=True)  # type: ignore[name-defined]
        import numpy as _np

        a, b = embeddings[0], embeddings[1]
        denom = float(_np.linalg.norm(a) * _np.linalg.norm(b))
        if denom == 0.0:
            return 0.0
        return float(_np.dot(a, b) / denom)
    except Exception:  # pragma: no cover - hostile environment
        return None


def score_relevance(prompt: str, reply: str) -> tuple[int, float, str]:
    """Map prompt<->reply similarity to a 1-5 bucketed score.

    Bucket boundaries are calibrated to the documented failure modes:
      - 0.00..0.10  -> 1   (irrelevant; documented "drunk coherence" failure)
      - 0.10..0.25  -> 2
      - 0.25..0.40  -> 3
      - 0.40..0.60  -> 4
      - >= 0.60     -> 5

    Returns (score_1_5, raw_similarity, source) where source is the underlying
    metric name. sentence-transformers is preferred when available.
    """
    sim = _maybe_sentence_transformer_cosine(prompt, reply)
    if sim is not None:
        source = "sentence_transformers"
    else:
        sim = tfidf_cosine(prompt, reply)
        source = "tfidf_cosine"

    if sim < 0.10:
        bucket = 1
    elif sim < 0.25:
        bucket = 2
    elif sim < 0.40:
        bucket = 3
    elif sim < 0.60:
        bucket = 4
    else:
        bucket = 5
    return bucket, float(sim), source


def score_directness(prompt: str, reply: str) -> tuple[int, dict[str, Any]]:
    """1-5 directness score from 2nd-person addressing markers + question shape.

    Heuristic, not a semantic judgement:
      * count "you / your / you're / you'll / you've / you'd"
      * count clarifying-question opener words
      * one bullet point of credit per pronoun (capped at 3)
      * +1 if reply contains an explicit clarifying question
      * +1 if reply opens with addressing the user (first 30 chars contain "you")
    """
    if not reply.strip():
        return 1, {"reason": "empty_reply"}

    pronoun_hits = _DIRECTNESS_PRONOUNS.findall(reply)
    n_pronouns = len(pronoun_hits)
    has_question = "?" in reply
    open_window = reply[:30]
    opens_with_addressing = bool(_DIRECTNESS_PRONOUNS.search(open_window))
    is_question_shape = bool(_DIRECTNESS_QUESTION_OPENERS.search(reply.lstrip()))

    score = 1
    score += min(n_pronouns, 3)  # up to +3 for repeated direct address
    if has_question:
        score += 1
    if opens_with_addressing or is_question_shape:
        # bounded — ensures the +1 bonus applies once
        score = min(5, score + 1)
    score = max(1, min(5, score))
    return score, {
        "n_pronouns": n_pronouns,
        "has_question": has_question,
        "opens_with_addressing": opens_with_addressing,
        "is_question_shape": is_question_shape,
    }


def score_non_rambling(reply: str) -> tuple[int, dict[str, Any]]:
    """1-5 score that decreases as reply length grows past _RAMBLE_SOFT_THRESHOLD.

    Empirical thresholds calibrated against the documented failure mode of
    long reflective monologues. <120 chars -> 5, ramping down to 1 by ~800.
    """
    n_chars = len(reply or "")
    if n_chars == 0:
        # Empty reply is itself a failure mode but not "rambling".
        return 1, {"n_chars": 0, "reason": "empty_reply"}

    if n_chars < 120:
        score = 5
    elif n_chars < _RAMBLE_SOFT_THRESHOLD:
        score = 4
    elif n_chars < 400:
        score = 3
    elif n_chars < _RAMBLE_HARD_THRESHOLD:
        score = 2
    else:
        score = 1
    return score, {"n_chars": n_chars}


def detect_leakage(reply: str) -> tuple[bool, list[str]]:
    """Return (leaks, hits). leaks=True iff any CAS notation pattern matched.

    Pattern matches the spec exactly:
        re.search(r"\\^[0-9]\\^[PCEO]|\\bF[1-7]\\b|\\|⟨|Δ°|RPM", reply)
    """
    hits = _LEAKAGE_PATTERN.findall(reply or "")
    return bool(hits), hits


def score_plain_language_clarity(reply: str) -> tuple[int, dict[str, Any]]:
    """1-5 score inversely correlated with CAS-jargon density.

    Density = (# jargon-pattern hits) / (# words). Buckets:
      density >= 0.20  -> 1   (every fifth word is CAS jargon)
      density >= 0.10  -> 2
      density >= 0.05  -> 3
      density >  0.00  -> 4
      density == 0.00  -> 5
    """
    if not reply.strip():
        return 1, {"reason": "empty_reply"}

    hits = 0
    for pat in _CAS_JARGON_PATTERNS:
        hits += len(pat.findall(reply))
    n_words = max(1, len(_word_list(reply)))
    density = hits / float(n_words)

    if density >= 0.20:
        score = 1
    elif density >= 0.10:
        score = 2
    elif density >= 0.05:
        score = 3
    elif density > 0.0:
        score = 4
    else:
        score = 5
    return score, {"jargon_hits": hits, "n_words": n_words, "density": density}


def score_compiler_validity(expression: str | None) -> tuple[bool, dict[str, Any]]:
    """Try to compile via api/notation/compiler.compile_expression.

    Returns (is_valid, info). On any compiler exception we return False with
    the exception message; we never raise out of the harness.
    """
    if not expression or not expression.strip():
        return False, {"reason": "empty_expression"}
    try:
        from api.notation.compiler import compile_expression  # type: ignore[import-not-found]
    except ImportError as exc:
        return False, {"reason": "compiler_import_failed", "error": str(exc)}

    try:
        artifact = compile_expression(expression)
    except Exception as exc:  # pragma: no cover - defensive
        return False, {"reason": "compiler_raised", "error": str(exc)}

    info: dict[str, Any] = {
        "valid": bool(getattr(artifact, "valid", False)),
        "engine": getattr(artifact, "engine", None),
    }
    err = getattr(artifact, "error", None)
    if err is not None:
        info["error"] = err
    warnings = getattr(artifact, "warnings", None) or []
    if warnings:
        info["warnings"] = list(warnings)
    return bool(info["valid"]), info


# ---------------------------------------------------------------------------
# Stage-1 + Stage-2 chaining (mirror chat.py without modifying it)
# ---------------------------------------------------------------------------


@dataclass
class HarnessConfig:
    """Frozen harness configuration; surfaced in the manifest for provenance."""

    checkpoint: str
    prompts: str
    out_path: str
    device: str
    max_new_tokens: int
    sampling: str
    temperature: float
    top_p: float
    use_cas_prefix: bool
    seed: int


def _expression_from_prediction(prediction: dict[str, Any]) -> str:
    """Reuse chat.py's renderer to extract the expression string.

    chat.py extracts the backticked expression from the renderer's lead
    sentence. We do the same here so the harness's "stage-1 expression" is
    exactly what a human would see in the REPL.
    """
    def _fallback() -> str:
        # Build a minimal canonical surface from the prediction dict so we
        # still have an input to the compiler-validity check.
        n = prediction.get("noetic")
        d = prediction.get("domain")
        f = prediction.get("drive")
        regs = prediction.get("registers") or []
        reg = regs[0] if regs else None
        parts: list[str] = []
        if n is not None:
            parts.append(f"^{n}")
        if d:
            parts.append(f"^{d}")
        if f:
            parts.append(f"_{{{f}}}")
        head = "".join(parts) if parts else "?"
        if reg:
            head = f"{head}|{reg}"
        return head

    try:
        from cas_native.inference.cas_renderer import render_cas_prediction
    except ImportError:
        return _fallback()

    try:
        rendered = render_cas_prediction(prediction)
    except Exception:
        # Renderer may raise on stub or out-of-range prediction values.
        return _fallback()

    if "`" in rendered:
        first = rendered.split("`", 1)[1]
        if "`" in first:
            return first.split("`", 1)[0]
    return rendered


def _load_b3_native_generator(checkpoint_dir: Path, device: str = "cpu") -> dict[str, Any] | None:
    """Build the B-3 native generator the way chat.py does, without touching chat.py.

    Returns None if any required file is missing; this lets the harness
    produce a manifest of stage-1-only scoring even when the generator
    cannot load (e.g. CPU-only environments where torch can still load
    but a cuda-trained checkpoint mismatches).
    """
    if not checkpoint_dir.exists():
        return None

    try:
        import torch
        from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
        from cas_native.model.nl_generation_head import (
            NLGenerationHead,
            NLGenerationHeadConfig,
        )
        from cas_native.training.tokenizer import HybridCASTokenizer
    except Exception as exc:  # pragma: no cover - import surface
        return {"_error": f"failed to import generator deps: {exc}"}

    tokenizer_path = checkpoint_dir / "tokenizer.json"
    bpe_path = checkpoint_dir / "english_bpe.json"
    ckpt_path = checkpoint_dir / "model_final.pt"
    if not tokenizer_path.exists() or not ckpt_path.exists():
        return None

    try:
        tokenizer = HybridCASTokenizer.load(tokenizer_path)
        if bpe_path.exists():
            tokenizer = tokenizer.with_english_bpe(bpe_path)
        vocab_size = int(tokenizer.vocab_size)
        torch_device = torch.device(device)

        enc_cfg = CASNativeConfig(d_model=512, n_layers=6, n_heads=8, vocab_size=vocab_size)
        model = CASNativeModel(enc_cfg).to(torch_device)
        head_cfg = NLGenerationHeadConfig(vocab_size=vocab_size, d_model=512, n_heads=8, n_layers=6)
        head = NLGenerationHead(head_cfg).to(torch_device)
        model.attach_nl_gen_head(head)

        state = torch.load(ckpt_path, map_location=torch_device)
        model.load_state_dict(state["model"])
        model.eval()
        return {"model": model, "tokenizer": tokenizer, "device": torch_device}
    except Exception as exc:
        return {"_error": f"generator load failed: {exc}"}


def run_stage_2_reply(
    *,
    native_generator: dict[str, Any],
    prompt_text: str,
    expression: str,
    register: str,
    config: HarnessConfig,
) -> dict[str, Any]:
    """Run B-3 native generation. Mirrors chat.py settings, no modifications there."""
    from cas_native.inference.native_nl_generate import generate_reply

    out = generate_reply(
        model=native_generator["model"],
        tokenizer=native_generator["tokenizer"],
        prompt_text=prompt_text,
        cas_expression=expression,
        register=register,
        max_new_tokens=config.max_new_tokens,
        sampling=config.sampling,
        temperature=config.temperature,
        top_p=config.top_p,
        use_cas_prefix=config.use_cas_prefix,
        device=native_generator["device"],
    )
    return out


# ---------------------------------------------------------------------------
# Per-prompt evaluation
# ---------------------------------------------------------------------------


@dataclass
class PerPromptResult:
    """One row in the harness manifest."""

    id: str
    category: str
    prompt_text: str
    expected_route: str
    ground_truth_cas: str | None
    notes: str | None

    # Stage 1
    stage1_prediction: dict[str, Any] = field(default_factory=dict)
    stage1_expression: str = ""
    stage1_register: str | None = None

    # Stage 2 (None when generator missing)
    stage2_reply: str | None = None
    stage2_n_steps: int | None = None
    stage2_stopped_on_eos: bool | None = None

    # Auto-scored user-facing dimensions
    relevance_score: int = 0
    relevance_raw: float = 0.0
    relevance_source: str = ""

    directness_score: int = 0
    directness_info: dict[str, Any] = field(default_factory=dict)

    non_rambling_score: int = 0
    non_rambling_info: dict[str, Any] = field(default_factory=dict)

    compiler_validity: bool = False
    compiler_validity_info: dict[str, Any] = field(default_factory=dict)

    plain_language_clarity_score: int = 0
    plain_language_clarity_info: dict[str, Any] = field(default_factory=dict)

    leakage: bool = False
    leakage_hits: list[str] = field(default_factory=list)

    # Delegated structural-preservation (Agent D)
    preservation: dict[str, Any] = field(default_factory=dict)

    # Aggregate failure flags per category-relevant heuristic
    failed: bool = False
    failure_reasons: list[str] = field(default_factory=list)


# Per-category failure-flag policy. A row is `failed=True` for the per-category
# fail-rate aggregate iff one of these conditions fires.
#
# Rule semantics:
#   leakage              -- detect_leakage() found CAS notation in user-facing reply
#   non_rambling_lt_3    -- length-rambling score < 3
#   plain_lt_3           -- plain-language clarity < 3 (jargon density too high)
#   relevance_lt_3       -- prompt<->reply auto-relevance score < 3
#   directness_lt_3      -- 2nd-person addressing score < 3
#   stage2_empty         -- generator returned empty / missing reply
#   preservation_failed  -- Agent D's preservation_score < 0.6 (only counted
#                           when scorer is non-placeholder)
_CATEGORY_FAIL_POLICY: dict[str, list[str]] = {
    "casual_greeting":     ["leakage", "non_rambling_lt_3", "relevance_lt_3", "directness_lt_3", "stage2_empty"],
    "confusion":           ["leakage", "non_rambling_lt_3", "relevance_lt_3", "directness_lt_3", "stage2_empty"],
    "frustration":         ["leakage", "non_rambling_lt_3", "relevance_lt_3", "directness_lt_3", "stage2_empty"],
    "simple_cas_question": ["leakage", "plain_lt_3", "relevance_lt_3", "stage2_empty"],
    "valid_cas_notation":  ["leakage", "relevance_lt_3", "stage2_empty"],
    # invalid_cas: the model must engage with the invalidity. Acceptable
    # responses are clarifying questions, plain-language acknowledgement
    # that the input is broken, or a compiler-valid repair. The original
    # ["stage2_empty"]-only policy let irrelevant ramble pass; tightened
    # 2026-05-07 (post-Codex audit) to mirror the casual categories: any
    # reply with leakage, low relevance to the broken input, weak
    # user-addressing, or empty Stage 2 fails.
    "invalid_cas":         ["leakage", "relevance_lt_3", "directness_lt_3", "stage2_empty"],
    "v76_production":      ["preservation_failed", "stage2_empty"],
    "v77_omega":           ["preservation_failed", "stage2_empty"],
    "meta_logic":          ["preservation_failed", "stage2_empty"],
    "fractal_composition": ["preservation_failed", "stage2_empty"],
}


def _apply_failure_policy(row: PerPromptResult) -> None:
    rules = _CATEGORY_FAIL_POLICY.get(row.category, [])
    reasons: list[str] = []
    if "leakage" in rules and row.leakage:
        reasons.append("leakage")
    if "non_rambling_lt_3" in rules and row.non_rambling_score < 3:
        reasons.append("non_rambling_lt_3")
    if "plain_lt_3" in rules and row.plain_language_clarity_score < 3:
        reasons.append("plain_language_lt_3")
    if "relevance_lt_3" in rules and row.relevance_score < 3:
        reasons.append("relevance_lt_3")
    if "directness_lt_3" in rules and row.directness_score < 3:
        reasons.append("directness_lt_3")
    if "stage2_empty" in rules:
        if row.stage2_reply is None or not row.stage2_reply.strip():
            reasons.append("stage2_empty")
    if "preservation_failed" in rules:
        # Agent D's real scorer surfaces `preservation_score` (mean of 10
        # boolean axes). The harness placeholder uses `placeholder=True` and
        # `score=0.0`. Resolve both shapes here:
        is_placeholder = bool(row.preservation.get("placeholder", False))
        score = None
        if isinstance(row.preservation, dict):
            score = row.preservation.get("preservation_score")
            if score is None:
                # Backward compatibility with placeholder field name.
                score = row.preservation.get("score")
        if not is_placeholder and (score is None or score < 0.6):
            reasons.append("preservation_failed")
    row.failure_reasons = reasons
    row.failed = bool(reasons)


def evaluate_prompt(
    *,
    prompt: dict[str, Any],
    predictor: Any,
    native_generator: dict[str, Any] | None,
    preservation_scorer: Any,
    config: HarnessConfig,
) -> PerPromptResult:
    """Run the full per-prompt evaluation."""
    row = PerPromptResult(
        id=str(prompt["id"]),
        category=str(prompt["category"]),
        prompt_text=str(prompt["prompt_text"]),
        expected_route=str(prompt.get("expected_route", "cas_pipeline")),
        ground_truth_cas=prompt.get("ground_truth_cas"),
        notes=prompt.get("notes"),
    )

    # ---------------- Stage 1 ----------------
    try:
        prediction = predictor(row.prompt_text)
    except Exception as exc:  # pragma: no cover - defensive
        row.stage1_prediction = {"_error": f"predictor failed: {exc}"}
        row.stage1_expression = ""
    else:
        row.stage1_prediction = prediction if isinstance(prediction, dict) else {"_raw": str(prediction)}
        row.stage1_expression = _expression_from_prediction(row.stage1_prediction) if isinstance(prediction, dict) else ""

    registers_list = (
        row.stage1_prediction.get("registers") if isinstance(row.stage1_prediction, dict) else None
    ) or []
    row.stage1_register = str(registers_list[0]) if registers_list else "T"

    # ---------------- Stage 2 ----------------
    if native_generator is not None and "_error" not in native_generator:
        try:
            stage2_out = run_stage_2_reply(
                native_generator=native_generator,
                prompt_text=row.prompt_text,
                expression=row.stage1_expression or "",
                register=row.stage1_register or "T",
                config=config,
            )
            row.stage2_reply = str(stage2_out.get("reply_text", ""))
            row.stage2_n_steps = int(stage2_out.get("n_steps", 0))
            row.stage2_stopped_on_eos = bool(stage2_out.get("stopped_on_eos", False))
        except Exception as exc:
            row.stage2_reply = ""
            row.stage2_n_steps = 0
            row.stage2_stopped_on_eos = False
            row.failure_reasons.append(f"stage2_exception:{exc}")

    # The user-facing reply for scoring. If stage 2 didn't run (no generator),
    # we score on stage-1 expression only and flag the row accordingly.
    user_facing_reply: str
    if row.stage2_reply is not None:
        user_facing_reply = row.stage2_reply
    else:
        user_facing_reply = ""

    # ---------------- User-facing scorers ----------------
    rel_score, rel_raw, rel_source = score_relevance(row.prompt_text, user_facing_reply)
    row.relevance_score = rel_score
    row.relevance_raw = rel_raw
    row.relevance_source = rel_source

    dir_score, dir_info = score_directness(row.prompt_text, user_facing_reply)
    row.directness_score = dir_score
    row.directness_info = dir_info

    nr_score, nr_info = score_non_rambling(user_facing_reply)
    row.non_rambling_score = nr_score
    row.non_rambling_info = nr_info

    # Compiler validity is asked of the STAGE-1 EXPRESSION (since the user-facing
    # reply is plain English and would never compile). Catches the "stage-1
    # produced a malformed expression" failure mode.
    cv, cv_info = score_compiler_validity(row.stage1_expression)
    row.compiler_validity = cv
    row.compiler_validity_info = cv_info

    plc_score, plc_info = score_plain_language_clarity(user_facing_reply)
    row.plain_language_clarity_score = plc_score
    row.plain_language_clarity_info = plc_info

    leaks, hits = detect_leakage(user_facing_reply)
    row.leakage = leaks
    row.leakage_hits = hits

    # ---------------- Preservation (Agent D) ----------------
    # Skip preservation scoring when ground_truth_cas is None (e.g. casual
    # greetings, confusion, frustration prompts). Agent D's real scorer
    # requires both inputs; passing None raises. The placeholder flag stays
    # True so failure policy ignores this axis for these rows.
    if not row.ground_truth_cas:
        row.preservation = {
            "placeholder": True,
            "skipped": True,
            "reason": "no_ground_truth",
        }
    else:
        try:
            preservation = preservation_scorer(row.ground_truth_cas, row.stage1_expression)
            if hasattr(preservation, "__dataclass_fields__"):
                row.preservation = asdict(preservation)
                # Agent D's real scorer has no `placeholder` field; mark
                # explicitly so failure policy treats it as authoritative.
                row.preservation.setdefault("placeholder", False)
            elif hasattr(preservation, "__dict__"):
                row.preservation = dict(preservation.__dict__)
            elif isinstance(preservation, dict):
                row.preservation = dict(preservation)
            else:
                row.preservation = {"_raw": str(preservation)}
        except Exception as exc:  # pragma: no cover - defensive
            row.preservation = {
                "placeholder": True,
                "error": f"scorer raised: {exc}",
            }

    # ---------------- Per-category failure policy ----------------
    _apply_failure_policy(row)
    return row


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_results(results: list[PerPromptResult]) -> dict[str, Any]:
    """Per-category fail rates + global means for each scoring dimension."""
    by_category: dict[str, list[PerPromptResult]] = defaultdict(list)
    for r in results:
        by_category[r.category].append(r)

    categories: dict[str, dict[str, Any]] = {}
    for cat, rows in by_category.items():
        n = len(rows)
        n_failed = sum(1 for r in rows if r.failed)
        cat_summary = {
            "n": n,
            "n_failed": n_failed,
            "fail_rate": n_failed / n if n else 0.0,
            "leakage_rate": sum(1 for r in rows if r.leakage) / n if n else 0.0,
            "compiler_validity_rate": sum(1 for r in rows if r.compiler_validity) / n if n else 0.0,
            "mean_relevance": mean(r.relevance_score for r in rows) if rows else 0.0,
            "mean_directness": mean(r.directness_score for r in rows) if rows else 0.0,
            "mean_non_rambling": mean(r.non_rambling_score for r in rows) if rows else 0.0,
            "mean_plain_language": mean(r.plain_language_clarity_score for r in rows) if rows else 0.0,
            "median_relevance_raw": median(r.relevance_raw for r in rows) if rows else 0.0,
            "failure_reason_breakdown": _failure_reason_counts(rows),
        }
        categories[cat] = cat_summary

    n_total = len(results)
    n_failed_total = sum(1 for r in results if r.failed)
    return {
        "total": {
            "n": n_total,
            "n_failed": n_failed_total,
            "fail_rate": n_failed_total / n_total if n_total else 0.0,
            "leakage_rate": sum(1 for r in results if r.leakage) / n_total if n_total else 0.0,
            "compiler_validity_rate": sum(1 for r in results if r.compiler_validity) / n_total if n_total else 0.0,
            "mean_relevance": mean(r.relevance_score for r in results) if results else 0.0,
            "mean_directness": mean(r.directness_score for r in results) if results else 0.0,
            "mean_non_rambling": mean(r.non_rambling_score for r in results) if results else 0.0,
            "mean_plain_language": mean(r.plain_language_clarity_score for r in results) if results else 0.0,
        },
        "categories": categories,
    }


def _failure_reason_counts(rows: list[PerPromptResult]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        for reason in r.failure_reasons:
            counts[reason] += 1
    return dict(counts)


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------


def load_prompts(path: Path) -> list[dict[str, Any]]:
    """Load fixture prompts. Tolerates blank lines (used as visual section breaks)."""
    prompts: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for ln_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"failed to parse prompt JSONL at {path}:{ln_no}: {exc}"
                ) from exc
            if not isinstance(obj, dict):
                raise ValueError(
                    f"prompt at {path}:{ln_no} is not an object: {obj!r}"
                )
            for key in ("id", "category", "prompt_text"):
                if key not in obj:
                    raise ValueError(
                        f"prompt at {path}:{ln_no} missing required key {key!r}"
                    )
            prompts.append(obj)
    if not prompts:
        raise ValueError(f"no prompts loaded from {path}")
    return prompts


def write_manifest(out_path: Path, manifest: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="B-4 human-relevance failure eval harness")
    p.add_argument(
        "--checkpoint",
        type=Path,
        required=True,
        help="Path to a CAS-Native run dir (must contain best_structured_token_model.pt "
        "OR model_final.pt + tokenizer.json + manifest.json). The B-3 prodshape run dir is the "
        "intended target, but any compatible run dir works.",
    )
    p.add_argument(
        "--prompts",
        type=Path,
        required=True,
        help="Path to fixture JSONL (one prompt object per line).",
    )
    p.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Path to write the manifest JSON.",
    )
    p.add_argument("--device", default="cpu", help="torch device (cpu|cuda)")
    p.add_argument("--max-new-tokens", type=int, default=120)
    p.add_argument("--sampling", default="top_p", choices=["greedy", "temperature", "top_p"])
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument(
        "--use-cas-prefix",
        action="store_true",
        help="Pass cas_prefix_ids into generation. Default OFF (matches training).",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--stage1-checkpoint",
        type=Path,
        default=None,
        help=(
            "Optional override for the Stage-1 K=9 predictor run dir. "
            "Defaults to the v77fix 20epoch GPU run that chat.py uses."
        ),
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of prompts (smoke testing).",
    )
    return p.parse_args(argv)


def _default_stage1_dir() -> Path:
    """Mirror chat.py's CHECKPOINT_RUN_DIR default for Stage-1 K=9 loading."""
    return (
        REPO_ROOT
        / "cas-native"
        / "training"
        / "runs"
        / "structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045"
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Programmatic entry point. Returns the manifest dict."""
    from cas_native.inference.predict_cas import load_predictor

    config = HarnessConfig(
        checkpoint=str(args.checkpoint),
        prompts=str(args.prompts),
        out_path=str(args.out),
        device=str(args.device),
        max_new_tokens=int(args.max_new_tokens),
        sampling=str(args.sampling),
        temperature=float(args.temperature),
        top_p=float(args.top_p),
        use_cas_prefix=bool(args.use_cas_prefix),
        seed=int(args.seed),
    )

    prompts = load_prompts(args.prompts)
    if args.limit is not None and args.limit > 0:
        prompts = prompts[: args.limit]

    stage1_dir = args.stage1_checkpoint if args.stage1_checkpoint is not None else _default_stage1_dir()
    predictor = load_predictor(stage1_dir, device=str(args.device))

    native_generator = _load_b3_native_generator(args.checkpoint, device=str(args.device))
    generator_status: str
    if native_generator is None:
        generator_status = "missing_files"
    elif "_error" in native_generator:
        generator_status = native_generator["_error"]
    else:
        generator_status = "loaded"

    preservation_scorer = _resolve_preservation_scorer()
    preservation_status = (
        "loaded_from_agent_d"
        if preservation_scorer is not _placeholder_score_preservation
        else "placeholder"
    )

    rows: list[PerPromptResult] = []
    for prompt in prompts:
        row = evaluate_prompt(
            prompt=prompt,
            predictor=predictor,
            native_generator=native_generator if isinstance(native_generator, dict) and "_error" not in native_generator else None,
            preservation_scorer=preservation_scorer,
            config=config,
        )
        rows.append(row)

    aggregate = aggregate_results(rows)

    manifest = {
        "schema_version": "b4_failure_eval.v1",
        "config": asdict(config),
        "stage1_dir": str(stage1_dir),
        "generator_status": generator_status,
        "preservation_scorer_status": preservation_status,
        "n_prompts": len(prompts),
        "rows": [asdict(r) for r in rows],
        "aggregate": aggregate,
    }
    write_manifest(args.out, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = run(args)
    # Compact stdout summary so callers can grep the headline numbers.
    agg = manifest["aggregate"]
    print(json.dumps({
        "event": "b4_eval_done",
        "n_prompts": manifest["n_prompts"],
        "generator_status": manifest["generator_status"],
        "preservation_scorer_status": manifest["preservation_scorer_status"],
        "fail_rate_total": agg["total"]["fail_rate"],
        "leakage_rate_total": agg["total"]["leakage_rate"],
        "compiler_validity_rate_total": agg["total"]["compiler_validity_rate"],
        "category_fail_rates": {
            cat: round(c["fail_rate"], 3) for cat, c in agg["categories"].items()
        },
        "out_path": manifest["config"]["out_path"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
