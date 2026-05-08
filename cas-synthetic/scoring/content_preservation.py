"""Content-preservation scorer for Path D Wave 3 corpus records.

Background
----------
Wave 3 phase 1 (11,897 records, $24.53 spend) passed all four numerical
anti-drift gates (leakage 0.13%, rejection 2.0%, chemistry 0%,
level-drift 0.07%) but FAILED a content-preservation audit on 2 of 4
slots. The failure modes are semantic, not lexical:

* coefficient drops in recipes (`0.7*X + 1.5*Y` → "X combined with Y")
* fractal k-index misread as counts (`Phi<9:4:7>` → "9 domains, 4
  operations, 7 pathways")
* domain swaps (`^5^C|T + ^5^C|f` → one term moved to evaluative)
* verbatim-copy parrot pipelines (english_to_cas slot)
* unrelated-correction rewrites (invalid_to_corrected slot)

This module provides eleven independent checks, each gated by which
slot/category they apply to:

================================  ====================================
check                             applies to
================================  ====================================
coefficient_preservation          cas_to_english + recipe category
domain_register_preservation      cas_to_english (any with ^N^D / |R)
drive_noetic_preservation         cas_to_english (always)
omega_target_preservation         cas_to_english + english_to_cas
fractal_k_index_preservation      cas_to_english + fractal_sequence
invalid_corrected_pair_overlap    invalid_to_corrected (always)
english_to_cas_anti_copy          english_to_cas (always)
explanation_length                invalid_to_explanation (always)
explanation_specificity           invalid_to_explanation (always)
explanation_anti_jargon           invalid_to_explanation (always)
explanation_error_class_alignment invalid_to_explanation (always)
================================  ====================================

`invalid_corrected_pair_overlap` was renamed from `invalid_corrected_overlap`
in v2 to make explicit that the check measures token overlap between the
SOURCE PAIR's invalid expression and its corrected expression — both
extracted from the prompt — not between the model's English explanation
and the corrected expression. A FAIL on this check therefore points at an
upstream corpus-generation defect (the corrector wrote an unrelated valid
expression instead of a minimal edit), not directly at the model's
narration.

The four `invalid_to_explanation` checks (added in v2) are LIGHTWEIGHT
HEURISTICS, not equivalent in strength to the cas_to_english structural
preservation checks. They proxy for "the explanation is not vacuous, is
about THIS expression, doesn't leak CAS jargon, and aligns with the error
class" — none of these guarantees faithfulness. Pass-rates on these
checks should be reported as "passes lightweight checks", not as
"content-preserving".

Design rules
------------
* Pure stdlib. No ML model dependencies, no embeddings, no neural
  matchers. The compiler is intentionally NOT imported — keeping the
  scorer self-contained avoids the path-bootstrap fragility and lets it
  run offline on any machine. Regex-based extraction is the documented
  approach.
* Every score is traceable. The `expected` / `found` / `missing` lists
  in each check carry the exact tokens that drove the decision.
* Conservative on applicability: a check that doesn't apply to a record
  reports `applicable=False, pass=True` so it never counts against the
  `overall_pass` flag.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Source-of-truth lookup tables (canonical, per CLAUDE.md and the project's
# free-form colloquialism lexicon). Kept inline so the scorer has zero
# imports from the rest of the cas-synthetic package; this keeps it usable
# from anywhere in the repo without path-bootstrap dance.
# ---------------------------------------------------------------------------

# Domain word aliases (lowercase). All English references must hit at least
# one alias when the source contains the domain letter.
_DOMAIN_ALIASES: dict[str, tuple[str, ...]] = {
    "P": (
        "principled",
        "principle",
        "principles",
        "foundational",
        "ethical",
        "ethics",
        "moral",
        "duty",
        "obligation",
        "fairness",
        "ought",
        "should",
        # Anti-drift: "fundamental" appears in many P-domain replies.
        "fundamental",
    ),
    "C": (
        "cognitive",
        "mental",
        "thinking",
        "thought",
        "thoughts",
        "conceptual",
        "concept",
        "concepts",
        "understanding",
        "knowledge",
        "knowing",
        "reasoning",
        "mind",
        "mind's",
        "intellect",
        "intellectual",
        "comprehension",
        # Approved pedagogical alias — domain context note in prompt.
    ),
    "E": (
        "evaluative",
        "evaluating",
        "evaluation",
        "judgment",
        "judging",
        "judge",
        "judges",
        "judged",
        "valuation",
        "value",
        "valuing",
        "verdict",
        "appraisal",
        "appraising",
        "assess",
        "assessing",
        "assessment",
        "feel",
        "feels",
        "feeling",
        "feelings",
        "emotion",
        "emotions",
        "emotional",
        "affective",
        "gut",
    ),
    "O": (
        "operational",
        "operations",
        "operation",
        "behavioral",
        "behaviour",
        "behavior",
        "behave",
        "behaves",
        "doing",
        "doing it",
        "do it",
        "do something",
        "performing",
        "performance",
        "execute",
        "execution",
        "executing",
        "carrying out",
        "in practice",
        "practical",
        "action",
        "actions",
        "act",
        "acts",
        "acting",
        "procedure",
        "procedural",
        "workflow",
        "in the doing",
        "out in",
        # "habit" is borderline; it's also ^7. Excluded to avoid FP.
    ),
}

# Register word aliases (lowercase).
_REGISTER_ALIASES: dict[str, tuple[str, ...]] = {
    "T": (
        "transcendent",
        "strategic",
        "big picture",
        "big-picture",
        "overarching",
        "vision",
        "calling",
        "purpose",
        "meaning",
        "meaningful",
        "high-level",
        "deep",
        "deeper",
        "deepest",
        "encompassing",
        "unifying",
        "the whole",
        "whole thing",
        "whole arc",
        "larger arc",
        "core",
        # "abstract" reads as transcendent in this prompt context.
        "abstract",
        "abstraction",
    ),
    "A": (
        "analytical",
        "analyse",
        "analyze",
        "analysis",
        "reasoned",
        "reasoning",
        "reason",
        "logic",
        "logical",
        "logically",
        "step by step",
        "step-by-step",
        "stepwise",
        "deliberate",
        "deliberation",
        "deliberating",
        "reflection",
        "reflective",
        "argument",
        "argued",
        "arguing",
        "thinking through",
        "thought through",
        "carefully",
        "systematic",
        "systematically",
        "explicit",
        "explicitly",
        "premise",
        "premises",
        "chain of thought",
    ),
    "f": (
        # affective register — note: capital "f" in the cas grammar
        "affective",
        "affect",
        "affects",
        "felt",
        "feeling",
        "feelings",
        "feel",
        "feels",
        "emotion",
        "emotions",
        "emotional",
        "emotionally",
        "gut",
        "visceral",
        "viscerally",
        "value-laden",
        "value",
        "values",
        "mood",
        "tone",
        "warm",
        "tender",
    ),
    "E": (
        # embodied register
        "embodied",
        "body",
        "bodily",
        "somatic",
        "somatically",
        "kinesthetic",
        "physical",
        "physically",
        "in the body",
        "in my body",
        "in the chest",
        "muscle memory",
        "hands-on",
        "doing it",
        "in the doing",
        "sensorimotor",
        "movement",
        "moving",
        "gesture",
        "posture",
        "breath",
        "lived",
        "kinaesthetic",
    ),
}

# Drive aliases (lowercase). Each drive has a canonical name and 2–4
# colloquial phrasings. Hit any one to count as preserved.
_DRIVE_ALIASES: dict[str, tuple[str, ...]] = {
    "F1": (
        "unity",
        "wholeness",
        "tying it together",
        "tying together",
        "integrating",
        "integrated",
        "integration",
        "unifying",
        "unified",
        "as one whole",
        "all of a piece",
        "coherent whole",
    ),
    "F2": (
        "wisdom",
        "wise",
        "insight",
        "insightful",
        "deep understanding",
        "grasping",
        "mature",
        "depth of",
    ),
    "F3": (
        "vitality",
        "vital",
        "energy",
        "energetic",
        "alive",
        "vigour",
        "vigor",
        "spark",
        "lively",
    ),
    "F4": (
        "connection",
        "connect",
        "connected",
        "connecting",
        "relationship",
        "relational",
        "bond",
        "bonded",
        "attachment",
        "attached",
        "tied to",
        "with someone",
        "with people",
        "intimately",
    ),
    "F5": (
        "agency",
        "agentive",
        "control",
        "in command",
        "by my own hand",
        "of my own choice",
        "make the call",
        "making the call",
        "deciding",
        "owning",
        "sovereign",
        "self-direction",
    ),
    "F6": (
        "structure",
        "structured",
        "structural",
        "discipline",
        "disciplined",
        "framework",
        "system",
        "systematic",
        "procedure",
        "procedural",
        "orderly",
        "in order",
        "by the rules",
    ),
    "F7": (
        "purpose",
        "purposeful",
        "purposefully",
        "purposive",
        "intent",
        "intention",
        "intentional",
        "goal",
        "goals",
        "mission",
        "aim",
        "aimed",
        "destination",
        "for a reason",
        "with a why",
    ),
}

# Noetic aliases. Each Noetic has its authoritative name + a tuple of
# approved colloquialisms drawn from CLAUDE.md and the free-form lexicon.
# Hit ANY of these to count the operator as preserved in English.
_NOETIC_ALIASES: dict[str, tuple[str, ...]] = {
    "0": (
        "idea",
        "ideas",
        "thought",
        "thoughts",
        "notion",
        "concept",
        "concepts",
        "all in your head",
        "on your mind",
        "the matter",
        "what we call",
    ),
    "1": (
        "mind",
        "minds",
        "mind's",
        "paying attention",
        "pay attention",
        "attentive",
        "attention",
        "noticing",
        "notice",
        "aware",
        "awareness",
        "make up",
        "making up",
        "made up",
        "using your head",
        "in mind",
        "becoming aware",
    ),
    "2": (
        "positive",
        "drawn to",
        "draw to",
        "speaks to",
        "can't resist",
        "cannot resist",
        "pulled toward",
        "pulled towards",
        "pull toward",
        "pull towards",
        "pull to",
        "attracted to",
        "attraction",
        "affinity",
        "moth to a flame",
        "gravitate",
        "leaning into",
        "leaning toward",
        "like",
        "loved",
        "love it",
    ),
    "3": (
        "negative",
        "can't stomach",
        "cannot stomach",
        "rubs the wrong way",
        "rubs me the wrong way",
        "ten-foot pole",
        "wouldn't touch",
        "would not touch",
        "pushed away",
        "push away",
        "averse",
        "aversion",
        "repelled",
        "repulsion",
        "recoil",
        "bristle",
        "off-putting",
        "loathe",
    ),
    "4": (
        "vibration",
        "resonate",
        "resonates",
        "resonated",
        "resonating",
        "resonance",
        "struck a chord",
        "strike a chord",
        "hit hard",
        "hits hard",
        "hit me hard",
        "made an impression",
        "impression",
        "rings true",
        "ring true",
        "echoes",
        "registered",
        "landed",
        "really landed",
    ),
    "5": (
        "female",
        "sum of",
        "who i am",
        "who one is",
        "what makes",
        "shaped by",
        "shape me",
        "experiences",
        "accumulated",
        "formation",
        "sum of one's experiences",
        "made me",
        "comprises",
        "composed of",
        "the layers",
    ),
    "6": (
        "male",
        "unpacking",
        "unpack",
        "unpacked",
        "breaking it down",
        "breaking down",
        "break it down",
        "break down",
        "broken down",
        "pulling apart",
        "pull apart",
        "looking at what's underneath",
        "what's underneath",
        "decomposing",
        "decomposition",
        "dissecting",
        "dissect",
        "scrutinising",
        "scrutinizing",
        "auditing",
        "examining",
        "examine",
        "piece by piece",
        "line by line",
        "taking apart",
        "take apart",
    ),
    "7": (
        "rhythm",
        "practice",
        "practising",
        "practicing",
        "muscle memory",
        "in a groove",
        "in the groove",
        "groove",
        "habit",
        "habits",
        "habitual",
        "repetition",
        "repeated",
        "repeating",
        "you are what you repeatedly",
        "getting used to",
        "drill",
        "drilling",
        "cadence",
        "loop",
        "cycle",
    ),
    "8": (
        "above/cause",
        "above",
        "cause",
        "trigger",
        "triggered",
        "triggers",
        "triggering",
        "that reminds",
        "reminded",
        "reminds me",
        "made me think",
        "make me think",
        "one thing leads",
        "one thing led",
        "called to mind",
        "brought to mind",
        "set off",
        "summoned",
        "conjured",
        "associated",
    ),
    "9": (
        "below/effect",
        "below",
        "effect",
        "popped into",
        "pop into",
        "out of nowhere",
        "thought came",
        "the thought came",
        "it just clicked",
        "just clicked",
        "clicked",
        "came to mind",
        "surfaced",
        "arrived",
        "arose",
        "landed in",
        "landed on",
        "showed up",
        "dropped in",
        "the answer came",
    ),
}

# Fractal "k-as-count" failure phrases. If any of these patterns appear in
# the English for a fractal_sequence record, flag it as the canonical
# k-misread failure mode. Cover both digit forms ("9 domains") AND
# spelled-out forms ("nine domains") — Haiku in the audit corpus often
# spelled them out.
_NUMBER_WORD = r"(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
_FRACTAL_K_AS_COUNT_NOUNS: tuple[str, ...] = (
    "domains?",
    "operations?",
    "(?:relational\\s+)?pathways?",
    "steps?",
    "(?:cognitive\\s+)?moves?",
    "stages?",
    "(?:distinct\\s+)?(?:cognitive\\s+)?operations?",
    "layers?",
    "levels?",
    "tiers?",
    "dimensions?",
    "phases?",
)
# Optional adjective filler the audit caught between number and noun
# ("nine distinct cognitive operations", "seven relational pathways
# active"). Whitelist rather than wildcard so we don't fire on innocuous
# phrases.
_K_AS_COUNT_FILLER = r"(?:distinct\s+|different\s+|separate\s+|active\s+|key\s+|core\s+|main\s+|primary\s+)*"
_FRACTAL_K_AS_COUNT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{_NUMBER_WORD}\s+{_K_AS_COUNT_FILLER}{noun}\b", re.IGNORECASE)
    for noun in _FRACTAL_K_AS_COUNT_NOUNS
)


# ---------------------------------------------------------------------------
# Source-CAS extraction. Each slot embeds the source CAS in a different
# section of the prompt; we extract by anchored regex.
# ---------------------------------------------------------------------------

_CAS_TO_ENGLISH_RE = re.compile(
    r"CAS expression \(grammar category:[^)]*\):\s*\n\s*\n\s*(.+?)\n\s*\n",
    re.DOTALL,
)
_INVALID_TO_EXPLANATION_RE = re.compile(
    r"Invalid CAS expression \(error class:[^)]*\):\s*\n\s*\n\s*(.+?)\n\s*\n",
    re.DOTALL,
)
_INVALID_TO_CORRECTED_INVALID_RE = re.compile(
    r"Invalid CAS expression \(error class:[^)]*\):\s*\n\s*\n\s*(.+?)\n\s*\n",
    re.DOTALL,
)
_INVALID_TO_CORRECTED_FIX_RE = re.compile(
    r"Corrected expression \(the valid form\):\s*\n\s*\n\s*(.+?)\n\s*\n",
    re.DOTALL,
)
_ENGLISH_TO_CAS_REFERENCE_RE = re.compile(
    # Capture everything between "render afresh):" and the next field
    # separator " | Noetic operators used:" (the prompt's structured
    # follow-on). Naive `[^|]+?` is wrong because the CAS expression
    # itself contains `|` (register separator).
    r"render afresh\):\s*(.+?)\s*\|\s*Noetic operators used:",
    re.DOTALL,
)


def _extract_source_cas(record: dict[str, Any]) -> str | None:
    """Return the source CAS string for a record, or None if not extractable."""
    prompt = record.get("prompt_to_model") or ""
    slot = record.get("slot")
    if slot == "cas_to_english":
        m = _CAS_TO_ENGLISH_RE.search(prompt)
        return m.group(1).strip() if m else None
    if slot == "invalid_to_explanation":
        m = _INVALID_TO_EXPLANATION_RE.search(prompt)
        return m.group(1).strip() if m else None
    if slot == "invalid_to_corrected":
        m = _INVALID_TO_CORRECTED_INVALID_RE.search(prompt)
        return m.group(1).strip() if m else None
    if slot == "english_to_cas":
        m = _ENGLISH_TO_CAS_REFERENCE_RE.search(prompt)
        return m.group(1).strip() if m else None
    return None


def _extract_corrected_cas(record: dict[str, Any]) -> str | None:
    """Return the 'corrected expression' CAS for invalid_to_corrected slots."""
    prompt = record.get("prompt_to_model") or ""
    m = _INVALID_TO_CORRECTED_FIX_RE.search(prompt)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# CAS surface-form parsing helpers (regex level — the compiler is NOT
# imported; see module docstring for rationale).
# ---------------------------------------------------------------------------

# Recipe coefficient: number followed by `*`. Captures `0.7`, `1.5`, `0.05`,
# `1`, etc. Also catches the leakage marker `0.05*Λ·...`.
_RECIPE_COEFF_RE = re.compile(r"(?<![A-Za-z_0-9])(\d+(?:\.\d+)?)\s*\*")

# `^N^D` and `^N^D|R` state literals. D ∈ P/C/E/O. R ∈ T/A/f/E.
_STATE_LITERAL_RE = re.compile(r"\^(\d)\^([PCEO])(?:\|([TAfE]))?")

# `^N|R` — Noetic with register but no explicit domain.
_NOETIC_REG_RE = re.compile(r"\^(\d)\|([TAfE])(?!\^)")

# Drive subscripts `_{Fk}`. Includes optional register on the drive.
_DRIVE_RE = re.compile(r"_\{F([1-7])(?:\|([TAfE]))?\}")

# Standalone Noetic `^N` (used after we've removed the structured ones).
_BARE_NOETIC_RE = re.compile(r"\^(\d)")

# Ω targets. Both Greek `Ω` and ASCII `Omega` spellings.
_OMEGA_RE = re.compile(r"(?:Ω|Omega)_([A-Za-z0-9_]+)")

# Cognitive Fractal angle-bracket sequences. ASCII `Phi<...>` and unicode
# `Φ⟨...⟩`. The body is one or more digits separated by `:`.
_FRACTAL_RE = re.compile(r"(?:Phi|Φ)\s*[<⟨]\s*([\d:\s]+?)\s*[>⟩]")

# Token splitter for Jaccard. Whitespace + most punctuation, but keep `^`,
# `|`, `_`, `:`, alphanumerics so CAS surface tokens stay legible.
_TOKEN_SPLIT_RE = re.compile(r"[\s,;()\[\]{}]+")


def _normalise_whitespace(s: str) -> str:
    """Collapse all runs of whitespace to single spaces and strip."""
    return re.sub(r"\s+", " ", s).strip()


def _tokenise_cas(s: str) -> set[str]:
    """Split a CAS surface form into a set of non-empty tokens."""
    tokens = _TOKEN_SPLIT_RE.split(s.strip())
    return {t for t in tokens if t}


def _english_lower(reply: str) -> str:
    """Lowercase + collapse whitespace for substring scanning."""
    return _normalise_whitespace(reply).lower()


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_coefficient_preservation(
    *, slot: str, category: str, source_cas: str | None, reply: str
) -> dict[str, Any]:
    """`cas_to_english` + recipe — coefficients in the source must surface
    in English (digits, simple word forms allowed). Coefficient `1`/`1.0`
    may be omitted.

    Numeric word fallbacks intentionally cover only the small set the
    audit observed (point-form decimals, "seven tenths", "half"). Edge
    cases like "two-thirds" return as failure rather than be silently
    accepted.
    """
    if not (slot == "cas_to_english" and category == "recipe"):
        return {"applicable": False, "pass": True, "expected": [], "found": [], "missing": []}
    if source_cas is None:
        return {
            "applicable": True,
            "pass": False,
            "expected": [],
            "found": [],
            "missing": ["__source_cas_unextractable__"],
        }
    raw_coeffs = _RECIPE_COEFF_RE.findall(source_cas)
    # Filter coefficient `1` and `1.0` — those may be omitted.
    expected: list[str] = []
    for c in raw_coeffs:
        try:
            if abs(float(c) - 1.0) < 1e-9:
                continue
        except ValueError:  # pragma: no cover — regex is digit-only.
            continue
        expected.append(c)
    if not expected:
        return {"applicable": True, "pass": True, "expected": [], "found": [], "missing": []}

    reply_lower = _english_lower(reply)
    found: list[str] = []
    missing: list[str] = []
    for coeff in expected:
        # Direct digit match (handles `0.7` and `0.70` since we look for the
        # literal source string).
        if coeff in reply_lower:
            found.append(coeff)
            continue
        # Common word-form fallbacks for the audit's typical decimal coeffs.
        words = _coeff_word_forms(coeff)
        if any(w in reply_lower for w in words):
            found.append(coeff)
            continue
        missing.append(coeff)
    return {
        "applicable": True,
        "pass": not missing,
        "expected": expected,
        "found": found,
        "missing": missing,
    }


def _coeff_word_forms(coeff: str) -> tuple[str, ...]:
    """Return a small set of permitted word-form aliases for a coefficient."""
    forms: list[str] = []
    try:
        v = float(coeff)
    except ValueError:
        return ()
    # Decimal coefficients seen in Path D recipes (0.05, 0.5, 0.7, etc).
    if abs(v - 0.5) < 1e-9:
        forms += ["half", "one half"]
    if abs(v - 0.7) < 1e-9:
        forms += ["point seven", "seven tenths", "seventy percent", "70 percent", "70%"]
    if abs(v - 0.3) < 1e-9:
        forms += ["point three", "three tenths", "thirty percent", "30%"]
    if abs(v - 0.05) < 1e-9:
        forms += ["point zero five", "five hundredths", "five percent", "5 percent", "5%", "small amount", "trickle", "tiny amount"]
    if abs(v - 1.5) < 1e-9:
        forms += ["one and a half", "one point five", "1.5", "150 percent", "150%"]
    if abs(v - 2.0) < 1e-9:
        forms += ["double", "twice", "two times"]
    return tuple(forms)


def _check_domain_register_preservation(
    *, slot: str, source_cas: str | None, reply: str
) -> dict[str, Any]:
    """`cas_to_english` — every domain letter and register letter that
    appears in source must have a recognisable English alias in the reply.

    Failure includes both missing (no domain word) and SWAP (the wrong
    domain word appears for that token's domain). For domain swaps we
    cannot prove the swap by text alone; we treat "domain present in
    source but no alias in reply" as failure. Scanned at the
    aggregate-domain-multiset level rather than per-token.
    """
    if slot != "cas_to_english":
        return {"applicable": False, "pass": True, "expected": [], "found": [], "missing": []}
    if source_cas is None:
        return {
            "applicable": False,
            "pass": True,
            "expected": [],
            "found": [],
            "missing": [],
        }

    reply_lower = _english_lower(reply)
    expected_axes: list[str] = []
    missing: list[str] = []

    # Domain coverage: every distinct domain letter in the source.
    domain_letters = {d for _, d, _ in _STATE_LITERAL_RE.findall(source_cas)}
    for d in sorted(domain_letters):
        expected_axes.append(f"D:{d}")
        if not _any_alias_present(_DOMAIN_ALIASES[d], reply_lower):
            missing.append(f"D:{d}")

    # Register coverage: distinct register letters from `^N^D|R` and `^N|R`.
    reg_letters: set[str] = set()
    for _, _, r in _STATE_LITERAL_RE.findall(source_cas):
        if r:
            reg_letters.add(r)
    for _, r in _NOETIC_REG_RE.findall(source_cas):
        if r:
            reg_letters.add(r)
    # Multi-register `|⟨T,A,f⟩` notation.
    for body in re.findall(r"\|⟨([^⟩]+)⟩", source_cas):
        for part in body.split(","):
            p = part.strip()
            if p in ("T", "A", "f", "E"):
                reg_letters.add(p)

    for r in sorted(reg_letters):
        expected_axes.append(f"R:{r}")
        if not _any_alias_present(_REGISTER_ALIASES[r], reply_lower):
            missing.append(f"R:{r}")

    return {
        "applicable": bool(expected_axes),
        "pass": not missing,
        "expected": expected_axes,
        "found": [a for a in expected_axes if a not in missing],
        "missing": missing,
    }


def _any_alias_present(aliases: tuple[str, ...], reply_lower: str) -> bool:
    """Return True if any alias is found in the reply.

    Uses word-boundary matching for short single-word aliases (≤5 chars,
    no whitespace) to avoid false positives from substring matches like
    "act" matching "actual" or "factor". Multi-word aliases and longer
    single words use plain substring matching, which is safe because the
    string itself is distinctive.
    """
    for a in aliases:
        if " " in a or len(a) > 5:
            if a in reply_lower:
                return True
        else:
            if re.search(rf"\b{re.escape(a)}\b", reply_lower):
                return True
    return False


def _check_drive_noetic_preservation(
    *, slot: str, source_cas: str | None, reply: str
) -> dict[str, Any]:
    """`cas_to_english` — every drive subscript and every Noetic operator
    must have at least one alias in the reply.
    """
    if slot != "cas_to_english":
        return {"applicable": False, "pass": True, "expected": [], "found": [], "missing": []}
    if source_cas is None:
        return {
            "applicable": False,
            "pass": True,
            "expected": [],
            "found": [],
            "missing": [],
        }

    reply_lower = _english_lower(reply)
    expected: list[str] = []
    missing: list[str] = []

    # Drives.
    drive_keys = {f"F{k}" for k, _ in _DRIVE_RE.findall(source_cas)}
    for fk in sorted(drive_keys):
        expected.append(fk)
        if not _any_alias_present(_DRIVE_ALIASES[fk], reply_lower):
            missing.append(fk)

    # Noetics. We collect every Noetic index that appears in any state
    # literal, register-attached form, or fractal sequence.
    noetic_indices: set[str] = set()
    for n, _, _ in _STATE_LITERAL_RE.findall(source_cas):
        noetic_indices.add(n)
    for n, _ in _NOETIC_REG_RE.findall(source_cas):
        noetic_indices.add(n)
    # Fractal indices count as Noetic operators (`Phi<9:4:7>`).
    for body in _FRACTAL_RE.findall(source_cas):
        for k in re.findall(r"\d", body):
            noetic_indices.add(k)
    # Any other bare `^N` we haven't already attributed (e.g. operator
    # composition `^4 ∘ ^9`). Be conservative: only count as bare if the
    # source string actually contains `^N` not followed by `^D` or `|R`.
    for m in _BARE_NOETIC_RE.finditer(source_cas):
        n = m.group(1)
        # Skip if next char is `^` (state literal) or `|` (register).
        end = m.end()
        if end < len(source_cas) and source_cas[end] in ("^", "|"):
            continue
        noetic_indices.add(n)

    for n in sorted(noetic_indices):
        expected.append(f"^{n}")
        if not _any_alias_present(_NOETIC_ALIASES[n], reply_lower):
            missing.append(f"^{n}")

    return {
        "applicable": bool(expected),
        "pass": not missing,
        "expected": expected,
        "found": [e for e in expected if e not in missing],
        "missing": missing,
    }


def _check_omega_target_preservation(
    *, slot: str, source_cas: str | None, reply: str, generated_cas: str | None
) -> dict[str, Any]:
    """Every `Ω_<name>` / `Omega_<name>` token in source must surface in
    the output. For cas_to_english the output is English (substring match
    on the name part is fine). For english_to_cas it's CAS (verbatim Ω
    token preservation).
    """
    if slot not in ("cas_to_english", "english_to_cas"):
        return {"applicable": False, "pass": True, "expected": [], "found": [], "missing": []}
    if source_cas is None:
        return {
            "applicable": False,
            "pass": True,
            "expected": [],
            "found": [],
            "missing": [],
        }

    omega_names = sorted(set(_OMEGA_RE.findall(source_cas)))
    if not omega_names:
        return {"applicable": False, "pass": True, "expected": [], "found": [], "missing": []}

    if slot == "cas_to_english":
        reply_lower = _english_lower(reply)
        # Match either the bare suffix word or a humanised form (the
        # underscore split by spaces). E.g. `Omega_creative_insight` →
        # "creative insight".
        found: list[str] = []
        missing: list[str] = []
        for name in omega_names:
            humanised = name.replace("_", " ").lower()
            if humanised in reply_lower or name.lower() in reply_lower:
                found.append(name)
            else:
                missing.append(name)
        return {
            "applicable": True,
            "pass": not missing,
            "expected": omega_names,
            "found": found,
            "missing": missing,
        }
    # english_to_cas — generated_cas should contain each Ω verbatim.
    target = generated_cas or ""
    found = []
    missing = []
    for name in omega_names:
        if (
            f"Ω_{name}" in target
            or f"Omega_{name}" in target
        ):
            found.append(name)
        else:
            missing.append(name)
    return {
        "applicable": True,
        "pass": not missing,
        "expected": omega_names,
        "found": found,
        "missing": missing,
    }


def _check_fractal_k_index_preservation(
    *, slot: str, category: str, source_cas: str | None, reply: str
) -> dict[str, Any]:
    """`cas_to_english` + fractal_sequence — each k-value in the
    `Phi<...>` body must reference the corresponding Noetic operator.
    Specifically flags the canonical "k-as-count" failure mode
    (`Phi<9:4:7>` rendered as "9 domains, 4 operations, 7 pathways").
    """
    if not (slot == "cas_to_english" and category == "fractal_sequence"):
        return {"applicable": False, "pass": True, "expected": [], "found": [], "missing": [], "k_as_count_flag": False}
    if source_cas is None:
        return {
            "applicable": True,
            "pass": False,
            "expected": [],
            "found": [],
            "missing": ["__source_cas_unextractable__"],
            "k_as_count_flag": False,
        }

    bodies = _FRACTAL_RE.findall(source_cas)
    if not bodies:
        return {"applicable": False, "pass": True, "expected": [], "found": [], "missing": [], "k_as_count_flag": False}

    k_values: list[str] = []
    for b in bodies:
        for d in re.findall(r"\d", b):
            k_values.append(d)

    reply_lower = _english_lower(reply)
    expected = sorted(set(k_values))
    found: list[str] = []
    missing: list[str] = []
    for k in expected:
        if _any_alias_present(_NOETIC_ALIASES[k], reply_lower):
            found.append(k)
        else:
            missing.append(k)

    # k-as-count failure: explicit "<digit> <count-noun>" pattern.
    k_as_count = any(p.search(reply) for p in _FRACTAL_K_AS_COUNT_PATTERNS)

    overall_pass = (not missing) and (not k_as_count)
    return {
        "applicable": True,
        "pass": overall_pass,
        "expected": expected,
        "found": found,
        "missing": missing,
        "k_as_count_flag": k_as_count,
    }


def _check_invalid_corrected_pair_overlap(
    *, slot: str, source_cas: str | None, corrected_cas: str | None
) -> dict[str, Any]:
    """`invalid_to_corrected` — Jaccard token overlap between the
    SOURCE PAIR (invalid CAS, corrected CAS) — both extracted from the
    prompt. This measures whether the underlying training pair is a
    minimal edit (invalid → corrected) or whether the corrector wrote
    an unrelated valid expression.

    IMPORTANT — what this check does NOT measure
    --------------------------------------------
    It does NOT measure faithfulness of the model's English narration to
    the actual fix. Both inputs to the Jaccard are CAS surface forms
    extracted from the PROMPT, never the `raw_response`. A FAIL here
    therefore says: "the source pair itself is broken upstream — the
    corrector produced something unrelated to the invalid expression".
    Whether the model's explanation is faithful is a separate question;
    the scorer does not currently address it directly. (If the source
    pair is broken, however, no English narration of it can be
    faithful, so a FAIL still flags the record as content-suspect.)

    Severity tiers: Jaccard < 0.2 is `unrelated`; 0.2–0.6 is
    `suspicious`; ≥ 0.6 is `ok`. The `pass` flag tracks the project's
    promotion threshold: pass = ok.
    """
    if slot != "invalid_to_corrected":
        return {"applicable": False, "pass": True, "jaccard": 1.0, "threshold": 0.6, "severity": "ok"}
    if source_cas is None or corrected_cas is None:
        return {
            "applicable": True,
            "pass": False,
            "jaccard": 0.0,
            "threshold": 0.6,
            "severity": "unrelated",
        }
    inv = _tokenise_cas(source_cas)
    cor = _tokenise_cas(corrected_cas)
    if not inv and not cor:
        jacc = 1.0
    elif not inv or not cor:
        jacc = 0.0
    else:
        jacc = len(inv & cor) / len(inv | cor)

    if jacc >= 0.6:
        sev = "ok"
    elif jacc >= 0.2:
        sev = "suspicious"
    else:
        sev = "unrelated"
    return {
        "applicable": True,
        "pass": sev == "ok",
        "jaccard": round(jacc, 4),
        "threshold": 0.6,
        "severity": sev,
    }


def _check_english_to_cas_anti_copy(
    *, slot: str, source_cas: str | None, generated_cas: str | None
) -> dict[str, Any]:
    """`english_to_cas` — generated CAS must not be a verbatim copy of
    the prompt's reference target.
    """
    if slot != "english_to_cas":
        return {"applicable": False, "pass": True, "is_verbatim_copy": False}
    if source_cas is None or generated_cas is None:
        return {"applicable": True, "pass": False, "is_verbatim_copy": False}
    a = _normalise_whitespace(source_cas)
    b = _normalise_whitespace(generated_cas)
    is_copy = a == b
    return {
        "applicable": True,
        "pass": not is_copy,
        "is_verbatim_copy": is_copy,
    }


# ---------------------------------------------------------------------------
# `invalid_to_explanation` — LIGHTWEIGHT HEURISTIC checks (v2 addition)
#
# These four checks ARE NOT equivalent in strength to the cas_to_english
# structural preservation checks. They are heuristic gates that flag the
# obvious failure modes (vacuous, generic, jargon-leaking, off-class
# explanations) without asserting faithfulness. A record that passes all
# four still might be wrong about the substance of the error — these are
# necessary, not sufficient, conditions for a usable explanation.
# ---------------------------------------------------------------------------


# Anti-jargon: raw CAS terminology that an English explanation must NOT
# contain. Mirrors the prompt's STRICT anti-drift rules but enforces them
# on the explanation slot, where the reply is supposed to stay clinical.
_EXPLANATION_JARGON_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bnoetic(s)?\b", re.IGNORECASE),
    re.compile(r"\bregister(s)?\b", re.IGNORECASE),
    re.compile(r"\bRPM\b"),
    re.compile(r"\bF[1-7]\b"),
    re.compile(r"\bdomain\s+letter(s)?\b", re.IGNORECASE),
    re.compile(r"\bcompile-time\b", re.IGNORECASE),
)

# Error-class alignment: each error class has a small set of concept
# words that a fitting explanation tends to mention. Hit ≥ 1 to count
# as aligned. Lists are deliberately broad (covers the obvious
# colloquialisms) and tolerant (no penalty for compound mentions). This
# is fuzzy — kept as a low-stakes signal rather than a strict gate.
_ERROR_CLASS_ALIGNMENT_TERMS: dict[str, tuple[str, ...]] = {
    "rpm": (
        "chain", "sequence", "order", "step", "steps", "flow",
        "hand off", "handoff", "hands off", "handed off", "handing off",
        "transition", "transitions", "destination", "starting point",
        "stage", "stages",
    ),
    "admissibility": (
        "rule", "rules", "allowed", "not allowed", "can't combine",
        "cannot combine", "valid pairing", "valid combination",
        "out of range", "outside the allowed", "accepted option",
        "permitted", "not permitted", "must be reserved",
    ),
    "parse": (
        "format", "shape", "missing", "structure", "structural",
        "placeholder", "expected", "appears instead", "doesn't match",
        "does not match", "syntax", "two halves", "broken", "breaks down",
        "malformed",
    ),
    "recipe": (
        "weight", "weights", "coefficient", "coefficients", "contribute",
        "contributes", "contribution", "recipe", "proportion",
        "proportions", "ratio", "ratios", "amount", "amounts",
        "quantity", "quantities",
    ),
    "fractal": (
        "sequence", "ordered", "ordering", "order", "indices", "index",
        "k-value", "operator slot", "operator slots", "slot", "slots",
        "fractal", "step", "steps",
    ),
    "meta_logic": (
        "set", "sets", "membership", "belongs", "doesn't belong",
        "subset", "superset", "relation", "relational", "operator",
        "operators", "constructor", "constructors", "vocabulary",
    ),
}


def _check_explanation_length(
    *, slot: str, reply: str
) -> dict[str, Any]:
    """`invalid_to_explanation` — reply length sanity check.

    HEURISTIC. Filters out trivially-short or runaway-rambling replies.
    Passes do NOT imply the explanation is faithful; they only imply
    "not obviously empty / not obviously rambling". Min 30 chars / max
    500 chars chosen to bracket the audit-corpus reply distribution
    without flagging the typical 1-3 sentence explanations.
    """
    if slot != "invalid_to_explanation":
        return {"applicable": False, "pass": True, "char_len": 0, "min": 30, "max": 500}
    reply_clean = (reply or "").strip()
    n = len(reply_clean)
    return {
        "applicable": True,
        "pass": 30 <= n <= 500,
        "char_len": n,
        "min": 30,
        "max": 500,
    }


def _check_explanation_specificity(
    *, slot: str, source_cas: str | None, reply: str
) -> dict[str, Any]:
    """`invalid_to_explanation` — the reply mentions at least one
    structural element from the invalid CAS source (a Noetic alias, a
    domain word, an Ω target stem, or a coefficient digit).

    HEURISTIC. Proxies for "the explanation is about THIS expression,
    not generic boilerplate." A pass does NOT mean the explanation is
    correct — only that it references something concretely tied to the
    source. Implemented via the existing alias tables and Ω/coefficient
    extraction; no new lookup tables.
    """
    if slot != "invalid_to_explanation":
        return {
            "applicable": False,
            "pass": True,
            "matched_signals": [],
            "checked_signals": [],
        }
    if source_cas is None:
        # Cannot validate specificity without a source CAS to anchor on.
        return {
            "applicable": True,
            "pass": False,
            "matched_signals": [],
            "checked_signals": ["__source_cas_unextractable__"],
        }

    reply_lower = _english_lower(reply)
    checked: list[str] = []
    matched: list[str] = []

    # Domain words present in source.
    domain_letters = {d for _, d, _ in _STATE_LITERAL_RE.findall(source_cas)}
    for d in sorted(domain_letters):
        checked.append(f"D:{d}")
        if _any_alias_present(_DOMAIN_ALIASES[d], reply_lower):
            matched.append(f"D:{d}")

    # Noetic indices (state-literal, register-attached, fractal, bare).
    noetic_indices: set[str] = set()
    for n, _, _ in _STATE_LITERAL_RE.findall(source_cas):
        noetic_indices.add(n)
    for n, _ in _NOETIC_REG_RE.findall(source_cas):
        noetic_indices.add(n)
    for body in _FRACTAL_RE.findall(source_cas):
        for k in re.findall(r"\d", body):
            noetic_indices.add(k)
    # Bare ^N — only count valid 0-9. Source CAS may contain malformed
    # tokens like ^20 that aren't valid Noetic indices; filter those.
    for m in _BARE_NOETIC_RE.finditer(source_cas):
        n = m.group(1)
        end = m.end()
        if end < len(source_cas) and source_cas[end] in ("^", "|"):
            continue
        noetic_indices.add(n)
    for n in sorted(noetic_indices):
        if n not in _NOETIC_ALIASES:
            continue
        checked.append(f"^{n}")
        if _any_alias_present(_NOETIC_ALIASES[n], reply_lower):
            matched.append(f"^{n}")

    # Ω target stems (humanised form).
    omega_names = sorted(set(_OMEGA_RE.findall(source_cas)))
    for name in omega_names:
        checked.append(f"Omega:{name}")
        humanised = name.replace("_", " ").lower()
        if humanised in reply_lower or name.lower() in reply_lower:
            matched.append(f"Omega:{name}")

    # Coefficient digits (substring match on the digit form).
    coeffs = [c for c in _RECIPE_COEFF_RE.findall(source_cas)]
    seen_coeffs: set[str] = set()
    for c in coeffs:
        if c in seen_coeffs:
            continue
        seen_coeffs.add(c)
        try:
            if abs(float(c) - 1.0) < 1e-9:
                continue  # `1` / `1.0` may be omitted.
        except ValueError:  # pragma: no cover
            continue
        checked.append(f"coeff:{c}")
        if c in reply_lower:
            matched.append(f"coeff:{c}")

    # Operator-phrase signals — `→`, `+`, `×` rendered in English.
    if "→" in source_cas or "->" in source_cas:
        checked.append("op:arrow")
        if any(t in reply_lower for t in (
            "produces", "leads to", "yields", "results in",
            "hand off", "handed off", "destination", "deliver",
            "transition", "starting point",
        )):
            matched.append("op:arrow")

    # Pass criterion: at least one signal matched, OR no signals checked
    # (degenerate source — fall back to length-only credit).
    overall_pass = bool(matched) if checked else True
    return {
        "applicable": True,
        "pass": overall_pass,
        "matched_signals": matched,
        "checked_signals": checked,
    }


def _check_explanation_anti_jargon(
    *, slot: str, reply: str
) -> dict[str, Any]:
    """`invalid_to_explanation` — reply must not leak raw CAS
    terminology (`noetic`, `register`, `RPM`, `F1`-`F7`, `domain
    letter`, `compile-time`).

    HEURISTIC. The corpus-wide leakage gate already removes the obvious
    cases; this is a slot-specific belt-and-braces gate so the slot's
    pass-rate cannot be inflated by records the corpus-wide regex
    happened to miss.
    """
    if slot != "invalid_to_explanation":
        return {"applicable": False, "pass": True, "jargon_hits": []}
    text = reply or ""
    hits: list[str] = []
    for pat in _EXPLANATION_JARGON_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append(m.group(0))
    return {
        "applicable": True,
        "pass": not hits,
        "jargon_hits": hits,
    }


def _check_explanation_error_class_alignment(
    *, slot: str, error_class: str, reply: str
) -> dict[str, Any]:
    """`invalid_to_explanation` — reply mentions ≥ 1 concept term
    aligned with the prompt's error class (e.g. `rpm` → "chain",
    "sequence", "step"; `parse` → "format", "shape", "missing").

    WEAK HEURISTIC. The term lists are broad and overlapping; this
    catches the obvious off-class explanations (e.g. an `rpm` record
    whose reply talks only about "values" and "ranges"). Records with
    error classes outside the alignment table are marked
    not-applicable rather than failed, so unfamiliar classes do not
    silently fail.
    """
    if slot != "invalid_to_explanation":
        return {
            "applicable": False,
            "pass": True,
            "error_class": error_class,
            "matched_terms": [],
        }
    terms = _ERROR_CLASS_ALIGNMENT_TERMS.get(error_class)
    if not terms:
        # Unfamiliar error class — don't manufacture a failure.
        return {
            "applicable": False,
            "pass": True,
            "error_class": error_class,
            "matched_terms": [],
        }
    reply_lower = _english_lower(reply)
    matched: list[str] = []
    for t in terms:
        if " " in t or len(t) > 5:
            if t in reply_lower:
                matched.append(t)
        else:
            if re.search(rf"\b{re.escape(t)}\b", reply_lower):
                matched.append(t)
    return {
        "applicable": True,
        "pass": bool(matched),
        "error_class": error_class,
        "matched_terms": matched,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_FAILURE_LABELS: dict[str, str] = {
    "coefficient_preservation": "coefficient_drop",
    "domain_register_preservation": "domain_or_register_swap_or_drop",
    "drive_noetic_preservation": "drive_or_noetic_drop",
    "omega_target_preservation": "omega_target_drop",
    "fractal_k_index_preservation": "fractal_k_drop",
    "invalid_corrected_pair_overlap": "invalid_corrected_pair_unrelated",
    "english_to_cas_anti_copy": "english_to_cas_verbatim_copy",
    "explanation_length": "explanation_length_out_of_range",
    "explanation_specificity": "explanation_not_specific_to_source",
    "explanation_anti_jargon": "explanation_leaks_cas_jargon",
    "explanation_error_class_alignment": "explanation_off_error_class",
}


def score_record(record: dict[str, Any]) -> dict[str, Any]:
    """Run all seven checks against one corpus record.

    See module docstring for the failure-mode rationale. The return shape
    is documented in the deliverable spec — every check carries the
    tokens that drove its decision so the result is fully traceable.
    """
    slot = record.get("slot", "")
    category = record.get("source_grammar_category_or_error_class", "")
    sample_id = record.get("sample_id", "")

    source_cas = _extract_source_cas(record)
    corrected_cas = _extract_corrected_cas(record) if slot == "invalid_to_corrected" else None
    reply = record.get("raw_response") or ""
    generated_cas = record.get("generated_cas")

    checks = {
        "coefficient_preservation": _check_coefficient_preservation(
            slot=slot, category=category, source_cas=source_cas, reply=reply
        ),
        "domain_register_preservation": _check_domain_register_preservation(
            slot=slot, source_cas=source_cas, reply=reply
        ),
        "drive_noetic_preservation": _check_drive_noetic_preservation(
            slot=slot, source_cas=source_cas, reply=reply
        ),
        "omega_target_preservation": _check_omega_target_preservation(
            slot=slot, source_cas=source_cas, reply=reply, generated_cas=generated_cas
        ),
        "fractal_k_index_preservation": _check_fractal_k_index_preservation(
            slot=slot, category=category, source_cas=source_cas, reply=reply
        ),
        "invalid_corrected_pair_overlap": _check_invalid_corrected_pair_overlap(
            slot=slot, source_cas=source_cas, corrected_cas=corrected_cas
        ),
        "english_to_cas_anti_copy": _check_english_to_cas_anti_copy(
            slot=slot, source_cas=source_cas, generated_cas=generated_cas
        ),
        "explanation_length": _check_explanation_length(
            slot=slot, reply=reply
        ),
        "explanation_specificity": _check_explanation_specificity(
            slot=slot, source_cas=source_cas, reply=reply
        ),
        "explanation_anti_jargon": _check_explanation_anti_jargon(
            slot=slot, reply=reply
        ),
        "explanation_error_class_alignment": _check_explanation_error_class_alignment(
            slot=slot, error_class=category, reply=reply
        ),
    }

    failure_reasons: list[str] = []
    overall_pass = True
    for name, c in checks.items():
        if c.get("applicable") and not c.get("pass"):
            overall_pass = False
            label = _FAILURE_LABELS[name]
            if name == "fractal_k_index_preservation" and c.get("k_as_count_flag"):
                label += "::k_as_count"
            failure_reasons.append(label)

    return {
        "sample_id": sample_id,
        "slot": slot,
        "category": category,
        "checks": checks,
        "overall_pass": overall_pass,
        "failure_reasons": failure_reasons,
    }


# ---------------------------------------------------------------------------
# Corpus-level entry point
# ---------------------------------------------------------------------------


@dataclass
class _Aggregate:
    total: int = 0
    passes: int = 0
    by_check_fail: Counter = field(default_factory=Counter)


def score_corpus(
    jsonl_path: str | Path,
    output_csv: str | Path,
    summary_json: str | Path | None = None,
) -> dict[str, Any]:
    """Apply :func:`score_record` to every record of `jsonl_path`, write
    one row per record into `output_csv`, and return a summary dict
    (also written to `summary_json` if given).
    """
    jsonl_path = Path(jsonl_path)
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    by_slot: dict[str, _Aggregate] = defaultdict(_Aggregate)
    by_slot_category: dict[tuple[str, str], _Aggregate] = defaultdict(_Aggregate)
    by_failure_mode: Counter = Counter()
    by_failure_mode_slot: dict[str, Counter] = defaultdict(Counter)

    csv_columns = [
        "sample_id",
        "slot",
        "category",
        "overall_pass",
        "failure_reasons",
        "coefficient_preservation_applicable",
        "coefficient_preservation_pass",
        "coefficient_preservation_missing",
        "domain_register_preservation_applicable",
        "domain_register_preservation_pass",
        "domain_register_preservation_missing",
        "drive_noetic_preservation_applicable",
        "drive_noetic_preservation_pass",
        "drive_noetic_preservation_missing",
        "omega_target_preservation_applicable",
        "omega_target_preservation_pass",
        "omega_target_preservation_missing",
        "fractal_k_index_preservation_applicable",
        "fractal_k_index_preservation_pass",
        "fractal_k_index_preservation_missing",
        "fractal_k_index_preservation_k_as_count",
        # invalid_corrected_pair_overlap (renamed from invalid_corrected_overlap
        # in v2). Measures Jaccard between SOURCE invalid CAS and SOURCE
        # corrected CAS — NOT between model output and target. A FAIL means
        # the upstream training pair is broken, not necessarily that the
        # model's English explanation is wrong.
        "invalid_corrected_pair_overlap_applicable",
        "invalid_corrected_pair_overlap_pass",
        "invalid_corrected_pair_overlap_jaccard",
        "invalid_corrected_pair_overlap_severity",
        "english_to_cas_anti_copy_applicable",
        "english_to_cas_anti_copy_pass",
        "english_to_cas_anti_copy_is_verbatim_copy",
        # invalid_to_explanation lightweight checks (v2 addition).
        # These are HEURISTICS, not equivalent to the cas_to_english
        # structural preservation checks. See module docstring.
        "explanation_length_applicable",
        "explanation_length_pass",
        "explanation_length_char_len",
        "explanation_specificity_applicable",
        "explanation_specificity_pass",
        "explanation_specificity_matched_signals",
        "explanation_specificity_checked_signals",
        "explanation_anti_jargon_applicable",
        "explanation_anti_jargon_pass",
        "explanation_anti_jargon_hits",
        "explanation_error_class_alignment_applicable",
        "explanation_error_class_alignment_pass",
        "explanation_error_class_alignment_matched_terms",
    ]

    total_records = 0
    with jsonl_path.open("r", encoding="utf-8") as f, output_csv.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=csv_columns)
        writer.writeheader()
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            result = score_record(record)
            total_records += 1
            slot = result["slot"]
            category = result["category"]
            by_slot[slot].total += 1
            by_slot_category[(slot, category)].total += 1
            if result["overall_pass"]:
                by_slot[slot].passes += 1
                by_slot_category[(slot, category)].passes += 1
            for fr in result["failure_reasons"]:
                by_failure_mode[fr] += 1
                by_failure_mode_slot[slot][fr] += 1
                by_slot[slot].by_check_fail[fr] += 1

            row = _flatten_for_csv(result)
            writer.writerow(row)

    summary = {
        "scorer_version": "v2",
        "scorer_notes": (
            "v2 changes: (1) renamed `invalid_corrected_overlap` → "
            "`invalid_corrected_pair_overlap` to clarify it measures "
            "Jaccard between the SOURCE invalid CAS and the SOURCE "
            "corrected CAS (both extracted from the prompt) — not "
            "between the model's reply and the corrected CAS. A FAIL "
            "indicates an upstream training-pair defect. "
            "(2) added four LIGHTWEIGHT HEURISTIC checks for the "
            "`invalid_to_explanation` slot (length, specificity, "
            "anti-jargon, error-class alignment). These are NOT "
            "equivalent in strength to the cas_to_english structural "
            "preservation checks. A high pass-rate on these heuristics "
            "should be reported as 'passes lightweight checks', not as "
            "'content-preserving'."
        ),
        "jsonl_path": str(jsonl_path),
        "total_records": total_records,
        "by_slot": {
            slot: {
                "total": agg.total,
                "passes": agg.passes,
                "pass_rate": round(agg.passes / agg.total, 4) if agg.total else 0.0,
                "failure_modes": dict(agg.by_check_fail),
            }
            for slot, agg in sorted(by_slot.items())
        },
        "by_slot_category": {
            f"{slot}::{category}": {
                "total": agg.total,
                "passes": agg.passes,
                "pass_rate": round(agg.passes / agg.total, 4) if agg.total else 0.0,
            }
            for (slot, category), agg in sorted(by_slot_category.items())
        },
        "failure_modes": {
            "all": dict(by_failure_mode),
            "by_slot": {slot: dict(c) for slot, c in by_failure_mode_slot.items()},
        },
    }
    if summary_json is not None:
        Path(summary_json).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_json).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _flatten_for_csv(result: dict[str, Any]) -> dict[str, Any]:
    """Flatten `score_record` output into a single CSV row."""
    c = result["checks"]
    return {
        "sample_id": result["sample_id"],
        "slot": result["slot"],
        "category": result["category"],
        "overall_pass": result["overall_pass"],
        "failure_reasons": "|".join(result["failure_reasons"]),
        "coefficient_preservation_applicable": c["coefficient_preservation"]["applicable"],
        "coefficient_preservation_pass": c["coefficient_preservation"]["pass"],
        "coefficient_preservation_missing": "|".join(c["coefficient_preservation"].get("missing", [])),
        "domain_register_preservation_applicable": c["domain_register_preservation"]["applicable"],
        "domain_register_preservation_pass": c["domain_register_preservation"]["pass"],
        "domain_register_preservation_missing": "|".join(c["domain_register_preservation"].get("missing", [])),
        "drive_noetic_preservation_applicable": c["drive_noetic_preservation"]["applicable"],
        "drive_noetic_preservation_pass": c["drive_noetic_preservation"]["pass"],
        "drive_noetic_preservation_missing": "|".join(c["drive_noetic_preservation"].get("missing", [])),
        "omega_target_preservation_applicable": c["omega_target_preservation"]["applicable"],
        "omega_target_preservation_pass": c["omega_target_preservation"]["pass"],
        "omega_target_preservation_missing": "|".join(c["omega_target_preservation"].get("missing", [])),
        "fractal_k_index_preservation_applicable": c["fractal_k_index_preservation"]["applicable"],
        "fractal_k_index_preservation_pass": c["fractal_k_index_preservation"]["pass"],
        "fractal_k_index_preservation_missing": "|".join(c["fractal_k_index_preservation"].get("missing", [])),
        "fractal_k_index_preservation_k_as_count": c["fractal_k_index_preservation"].get("k_as_count_flag", False),
        "invalid_corrected_pair_overlap_applicable": c["invalid_corrected_pair_overlap"]["applicable"],
        "invalid_corrected_pair_overlap_pass": c["invalid_corrected_pair_overlap"]["pass"],
        "invalid_corrected_pair_overlap_jaccard": c["invalid_corrected_pair_overlap"].get("jaccard", ""),
        "invalid_corrected_pair_overlap_severity": c["invalid_corrected_pair_overlap"].get("severity", ""),
        "english_to_cas_anti_copy_applicable": c["english_to_cas_anti_copy"]["applicable"],
        "english_to_cas_anti_copy_pass": c["english_to_cas_anti_copy"]["pass"],
        "english_to_cas_anti_copy_is_verbatim_copy": c["english_to_cas_anti_copy"].get("is_verbatim_copy", False),
        "explanation_length_applicable": c["explanation_length"]["applicable"],
        "explanation_length_pass": c["explanation_length"]["pass"],
        "explanation_length_char_len": c["explanation_length"].get("char_len", ""),
        "explanation_specificity_applicable": c["explanation_specificity"]["applicable"],
        "explanation_specificity_pass": c["explanation_specificity"]["pass"],
        "explanation_specificity_matched_signals": "|".join(c["explanation_specificity"].get("matched_signals", [])),
        "explanation_specificity_checked_signals": "|".join(c["explanation_specificity"].get("checked_signals", [])),
        "explanation_anti_jargon_applicable": c["explanation_anti_jargon"]["applicable"],
        "explanation_anti_jargon_pass": c["explanation_anti_jargon"]["pass"],
        "explanation_anti_jargon_hits": "|".join(c["explanation_anti_jargon"].get("jargon_hits", [])),
        "explanation_error_class_alignment_applicable": c["explanation_error_class_alignment"]["applicable"],
        "explanation_error_class_alignment_pass": c["explanation_error_class_alignment"]["pass"],
        "explanation_error_class_alignment_matched_terms": "|".join(c["explanation_error_class_alignment"].get("matched_terms", [])),
    }


__all__ = ["score_record", "score_corpus"]
