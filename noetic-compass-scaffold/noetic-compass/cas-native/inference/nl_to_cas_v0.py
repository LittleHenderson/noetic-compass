"""NL → CAS heuristic bridge v0.

Step 5B Option C per `decisions.md` 2026-05-13T18:25Z. The first NL
surface for CAS-Native — converts constrained English to canonical
CAS expressions deterministically, so the chat REPL feels alive
without waiting on a trained NL model (Stage 4).

Per Codex 2026-05-13: "Minimal NL is the next experiment after the
REPL shell. Not full open chat. Just enough for a user/stakeholder
to feel like they can talk to CAS naturally."

This is rule-based v0. Future Stage 4 training will supersede it,
but the heuristic stays in production as a deterministic fast-path —
known patterns short-circuit the model.

Discipline (mirrors plain_english.py "does not lie"):
- NEVER invent a CAS expression. If no pattern matches, return None.
- The REPL falls through to the existing bridge-text refusal in
  that case.
- Every match carries a `confidence` score so the UI can show
  uncertainty when phrasing is ambiguous.
- Every match carries the `matched_pattern` description so the user
  sees WHY the bridge mapped their text to this CAS expression.

Public surface:
- `match_nl_to_cas(text) -> NLMatchResult | None`
- `NLMatchResult` dataclass

Bounded scope (per decisions.md 2026-05-13T18:25Z):
- No model call. No training. No corpus engineering.
- No foreign LLMs (per memory `feedback_no_foreign_architecture_cas_only.md`
  and `feedback_cas_native_data_strategy_2026_05_13.md`).
- Curated patterns only. ~15 initial mappings from Codex's directive.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class NLMatchResult:
    """Outcome of an NL→CAS heuristic match.

    Fields:
        matched_pattern: human-readable description of WHY the bridge
            chose this mapping. Surfaced to the user.
        cas_expression: the canonical CAS expression the model will
            consume.
        rationale: one-line plain-English explanation of the CAS,
            shown to the user before the model's full explanation.
        confidence: float in [0, 1]. 1.0 = exact-phrase match;
            lower = approximate / fuzzy. Surfaced to UI for badges.
    """
    matched_pattern: str
    cas_expression: str
    rationale: str
    confidence: float


# ---------------------------------------------------------------------------
# Curated patterns. Each entry:
#   - regex pattern (case-insensitive, word-aware)
#   - matched_pattern description (what we tell the user)
#   - cas_expression (canonical form)
#   - rationale (one-line plain-English meaning)
#   - confidence (1.0 for exact phrase, lower for looser shapes)
# ---------------------------------------------------------------------------

_NL_PATTERNS: list[tuple[re.Pattern, str, str, str, float]] = [
    # --- Chains (highest specificity first) ---
    (
        re.compile(
            r"\b(?:cas\s+)?chain\s+for\s+(?:awareness|attention)\s+"
            r"(?:leading|going)\s+to\s+(?:action|behavior)\b",
            re.IGNORECASE,
        ),
        "awareness leading to action chain",
        "^1^C -> ^9^O",
        "Mind in the Cognitive domain triggers an Effect in the "
        "Operational domain.",
        1.0,
    ),
    (
        re.compile(
            r"\bthought\s+becoming\s+(?:action|behavior)\b",
            re.IGNORECASE,
        ),
        "thought becoming action",
        "^9^O",
        "An Idea brought to Mind in the Operational domain — a "
        "thought that lands as behavior.",
        0.95,
    ),
    (
        re.compile(
            r"\b(?:decision|choice)\s+in\s+cas\b",
            re.IGNORECASE,
        ),
        "decision in CAS",
        "^8^P -> ^9^O",
        "An Above/Cause in the Principled domain triggers a "
        "Below/Effect in the Operational domain — a principled "
        "decision producing an action.",
        0.9,
    ),
    # --- Feelings / emotions (Affective register) ---
    (
        re.compile(r"\bturn\s+anger\s+into\s+cas\b", re.IGNORECASE),
        "anger as CAS state",
        "^3^E|f",
        "Negative in the Evaluative domain, Affective register — "
        "felt aversion.",
        1.0,
    ),
    (
        re.compile(r"\b(?:explain|express)\s+anger(?:\s+in\s+cas)?\b",
                   re.IGNORECASE),
        "anger as CAS state",
        "^3^E|f",
        "Negative in the Evaluative domain, Affective register — "
        "felt aversion.",
        0.85,
    ),
    (
        re.compile(r"\b(?:turn|explain)\s+joy\s+(?:into|in)\s+cas\b",
                   re.IGNORECASE),
        "joy as CAS state",
        "^2^E|f",
        "Positive in the Evaluative domain, Affective register — "
        "felt attraction.",
        0.95,
    ),
    (
        re.compile(r"\b(?:turn|explain)\s+grief\s+(?:into|in)\s+cas\b",
                   re.IGNORECASE),
        "grief as CAS state",
        "^4^E|f",
        "Vibration in the Evaluative domain, Affective register — "
        "the impression of loss.",
        0.9,
    ),
    (
        re.compile(r"\b(?:explain|turn)\s+a?\s*feeling\s+(?:in|into)\s+cas\b",
                   re.IGNORECASE),
        "a feeling as CAS state",
        "^4^E|f",
        "Vibration in the Evaluative domain, Affective register — "
        "an impression that resonates.",
        0.7,
    ),
    # --- Awareness / attention (Mind in Cognitive) ---
    (
        re.compile(r"\b(?:explain|describe)\s+(?:awareness|attention)\b",
                   re.IGNORECASE),
        "awareness as CAS state",
        "^1^C",
        "Mind in the Cognitive domain — the degree of awareness "
        "processing an idea.",
        0.8,
    ),
    # --- Practice / habit (Rhythm) ---
    (
        re.compile(r"\b(?:explain|describe)\s+(?:practice|habit|routine)\b",
                   re.IGNORECASE),
        "practice as CAS state",
        "^7^O",
        "Rhythm in the Operational domain — the rate and pattern of "
        "repeated exposure that conditions behavior.",
        0.85,
    ),
    # --- Simple-example requests ---
    (
        re.compile(
            r"\bshow\s+(?:me\s+)?a?\s*simple\s+cas\s+example\b",
            re.IGNORECASE,
        ),
        "simple example request",
        "let stageA0_4_857 = ^7^P_{F5}; let stageD3_4_857 = ^6^P_{F2}; "
        "stageA0_4_857 -> stageD3_4_857",
        "A canonical two-stage RPM chain — practiced rhythm with "
        "agency leading into compositional thinking.",
        1.0,
    ),
    (
        re.compile(
            r"\bgive\s+(?:me\s+)?(?:a\s+)?cas\s+example\b",
            re.IGNORECASE,
        ),
        "simple example request",
        "let stageA0_4_857 = ^7^P_{F5}; let stageD3_4_857 = ^6^P_{F2}; "
        "stageA0_4_857 -> stageD3_4_857",
        "A canonical two-stage RPM chain — practiced rhythm with "
        "agency leading into compositional thinking.",
        0.95,
    ),
    # --- Idea (^0) requests ---
    (
        re.compile(r"\b(?:explain|describe|what\s+is)\s+an?\s+idea\b",
                   re.IGNORECASE),
        "idea as CAS state",
        "^0",
        "All things in and outside the Mind — the most abstract "
        "structural primitive in CAS.",
        0.85,
    ),
    # --- Aversion / refusal (visceral Negative) ---
    (
        re.compile(
            r"\b(?:explain|describe)\s+(?:disgust|refusal|aversion)\b",
            re.IGNORECASE,
        ),
        "visceral aversion",
        "^3^E|f",
        "Negative in the Evaluative domain, Affective register — "
        "visceral aversion, not analytical critique.",
        0.85,
    ),
    # --- Composition / Male operator ---
    (
        re.compile(
            r"\b(?:explain|describe)\s+(?:composition|unpacking|decomposition)\b",
            re.IGNORECASE,
        ),
        "compositional thinking",
        "^6^P",
        "Male in the Principled domain — an idea impregnated with "
        "another idea, decomposing a thought into its parts.",
        0.85,
    ),
]


def match_nl_to_cas(text: str) -> Optional[NLMatchResult]:
    """Match English text against the heuristic pattern table.

    Args:
        text: the user's input. Stripped + case-folded internally.

    Returns:
        `NLMatchResult` on first matching pattern (most specific
        patterns come first in `_NL_PATTERNS`), or `None` if no
        pattern matches. NEVER fabricates a CAS expression.
    """
    if not text or not text.strip():
        return None
    for pattern, matched_pattern, cas_expr, rationale, confidence in _NL_PATTERNS:
        if pattern.search(text):
            return NLMatchResult(
                matched_pattern=matched_pattern,
                cas_expression=cas_expr,
                rationale=rationale,
                confidence=confidence,
            )
    return None


def list_supported_patterns() -> list[str]:
    """Return a human-readable list of supported NL patterns. The REPL
    surfaces this when no pattern matches — gives the user examples
    of phrasings the heuristic understands."""
    seen: set[str] = set()
    out: list[str] = []
    for _, matched_pattern, _, _, _ in _NL_PATTERNS:
        if matched_pattern not in seen:
            seen.add(matched_pattern)
            out.append(matched_pattern)
    return out
