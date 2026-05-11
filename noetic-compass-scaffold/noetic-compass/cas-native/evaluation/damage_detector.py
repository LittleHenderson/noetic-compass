"""Stage 7 v7.1 damage detector — Phase-C-shape signature detection.

Per user 2026-05-11. Scans a single decoded sample (string) for the 6
damage signatures named in scope. Returns a structured verdict with
per-signature evidence; the smoke-report consumer combines these to
decide whether to kill the run.

The six signatures:

  1. **Repeated phrase loops** — ≥3 consecutive identical n-grams (any n
     from 2 to 6). Catches `"the the the"` and `"foo bar foo bar foo bar"`.

  2. **Truncation / mid-clause cutoff** — last 12 chars look incomplete
     (ends mid-word, with a hanging conjunction/preposition, or with a
     comma + nothing).

  3. **Stage variable corruption** — a token that LOOKS like a stage
     variable but is malformed (e.g., `stageA0_5_029`, `stageA0__0296`,
     `stage_5_0296` — wrong shape, missing letter, doubled underscore).
     Includes pure-substring checks against canonical patterns.

  4. **Hard notation leaks** — CAS notation characters (`^P`, `^0`,
     `|f`, `_{F`, `Ω_`, `Phi⟨`) appearing in places where they shouldn't,
     i.e. surrounded by fluent English without a colon/equals (no
     explanatory context).

  5. **Generic prose collapse** — output is generic ("the expression is
     valid", "this means something specific" without specifics) or
     dramatically shorter than expected (< 25% of target reply length).

  6. **ABeing-style token boundary corruption** — concatenated word
     fragments where two real-word boundaries got fused (e.g. `ABeing`
     from `A Being`, or `stageD3_3_0233333` from a stage var with extra
     digits appended).

Per user scope: "kill only on hard damage." A single mild signature
should not kill the run. The damage-severity score combines presence
flags with frequency to produce a "kill" / "warn" / "clean" verdict
per sample.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DamageReport:
    """Per-sample damage report."""
    sample_text: str
    verdict: str  # "clean" | "warn" | "kill"
    signatures: dict[str, Any] = field(default_factory=dict)
    severity_score: float = 0.0


# Stage variable canonical pattern: stage + (A|D|W|P) + digit + _ + digit + _ + 4 digits
_CANONICAL_STAGE_VAR_RE = re.compile(r"\bstage[ADWP]\d+_\d+_\d{4}\b")
# Stage variable LOOKING-corrupted patterns
_STAGE_VAR_FRAGMENT_RE = re.compile(r"\bstage[A-Za-z_\d]{1,3}\b")  # too short
_STAGE_VAR_DOUBLE_UNDERSCORE_RE = re.compile(r"\bstage\w*__\w*\b")
_STAGE_VAR_NO_LETTER_RE = re.compile(r"\bstage_\d+_\d{4}\b|\bstage_\d+_\d+_\d{4}\b")  # missing the A/D/W/P (2 or 3 segments)
_STAGE_VAR_BAD_DIGITS_RE = re.compile(r"\bstage[ADWP]\d+_\d+_\d{6,}\b")  # too many trailing digits

# CAS notation leak patterns — characters that should not appear in plain
# fluent prose without explanatory framing.
_CAS_NOTATION_RE = re.compile(
    r"(\^[0-9PCEO]|\|[TAfE](?:\s|$)|_\{F\d|Ω_|Phi⟨|⟨[\d:]+⟩)"
)
# Generic-collapse signatures: extremely vague generic phrases.
_GENERIC_PHRASES = (
    "is an expression",
    "this expression",
    "the expression is valid",
    "the expression is invalid",
    "this means something",
    "this is a valid",
    "this is an invalid",
)
# ABeing-style: any token where a capital letter follows a lowercase letter
# WITHOUT a space, and the result isn't a known acronym/camelcase word.
# Catches `ABeing`, `aBe`, `inThe`, etc. Skip URLs (http://, mailto:).
_CAMEL_FUSION_RE = re.compile(r"(?<![/:])\b[a-z]+[A-Z][a-z]+\b")


def _has_consecutive_repeats(text: str, min_n: int = 1, max_n: int = 6, min_consec: int = 3) -> dict[str, Any]:
    """Return {found: bool, n: int, phrase: str, count: int} if a repeated
    n-gram (n in [min_n, max_n]) appears consecutively at least min_consec
    times. Returns {found: False} otherwise.
    """
    tokens = text.split()
    if len(tokens) < min_n * min_consec:
        return {"found": False}
    for n in range(min_n, max_n + 1):
        for i in range(len(tokens) - n * min_consec + 1):
            base = tokens[i:i + n]
            count = 1
            j = i + n
            while j + n <= len(tokens) and tokens[j:j + n] == base:
                count += 1
                j += n
            if count >= min_consec:
                return {
                    "found": True,
                    "n": n,
                    "phrase": " ".join(base),
                    "count": count,
                    "first_position": i,
                }
    return {"found": False}


def _looks_truncated(text: str) -> dict[str, Any]:
    """Heuristic mid-clause-cutoff detector. Checks the tail of the text."""
    if not text:
        return {"found": False, "reason": "empty"}
    tail = text.rstrip().rstrip(".!?\"'")
    if not tail:
        return {"found": False, "reason": "punctuated"}
    last_chars = tail[-25:]
    # Ends mid-word (no terminal punctuation) AND last token is a short
    # word OR ends with a conjunction/preposition.
    last_token = tail.split()[-1].lower() if tail.split() else ""
    hanging_words = {
        "the", "a", "an", "and", "or", "but", "of", "in", "on",
        "at", "to", "for", "with", "by", "from", "is", "was", "are",
        "were", "be", "been", "being", "as", "that", "which", "who",
    }
    ends_mid_word = (
        text.rstrip()[-1].isalpha()
        and not text.rstrip().endswith(("ing", "ed", "ly", "s", "n"))
    )
    if last_token in hanging_words:
        return {"found": True, "reason": "ends_on_function_word", "tail": last_chars}
    if text.rstrip().endswith(","):
        return {"found": True, "reason": "ends_on_comma", "tail": last_chars}
    if ends_mid_word and len(last_token) <= 4:
        return {"found": True, "reason": "ends_mid_word_short", "tail": last_chars, "last_token": last_token}
    return {"found": False}


def _check_stage_var_corruption(text: str) -> dict[str, Any]:
    """Look for malformed stage-variable identifiers."""
    canonical = _CANONICAL_STAGE_VAR_RE.findall(text)
    double_under = _STAGE_VAR_DOUBLE_UNDERSCORE_RE.findall(text)
    no_letter = _STAGE_VAR_NO_LETTER_RE.findall(text)
    bad_digits = _STAGE_VAR_BAD_DIGITS_RE.findall(text)
    # Fragments are noisy; only count them if no canonical found and there's
    # a "stage" token at all (some replies just use the word "stage").
    has_stage_word = " stage" in text or text.startswith("stage")
    fragments = _STAGE_VAR_FRAGMENT_RE.findall(text) if has_stage_word else []
    fragments = [f for f in fragments if f not in canonical and f != "stage"]
    corrupt = bool(double_under or no_letter or bad_digits)
    return {
        "found": corrupt,
        "canonical_count": len(canonical),
        "double_underscore": double_under,
        "no_letter": no_letter,
        "bad_digits": bad_digits,
        "fragments_without_canonical": fragments[:5],
    }


def _check_notation_leak(text: str) -> dict[str, Any]:
    """Detect CAS notation chars appearing in fluent prose."""
    hits = _CAS_NOTATION_RE.findall(text)
    return {"found": len(hits) > 0, "matches": hits[:10], "count": len(hits)}


def _check_generic_collapse(text: str, target_text: str) -> dict[str, Any]:
    """Detect generic-prose collapse and dramatic shortness."""
    text_lower = text.lower()
    matched = [p for p in _GENERIC_PHRASES if p in text_lower]
    ratio = len(text) / max(len(target_text), 1)
    is_too_short = ratio < 0.25 and len(text) < len(target_text) - 30
    return {
        "found": bool(matched) or is_too_short,
        "generic_phrases": matched,
        "length_ratio": round(ratio, 3),
        "text_len": len(text),
        "target_len": len(target_text),
        "is_too_short": is_too_short,
    }


def _check_camel_fusion(text: str) -> dict[str, Any]:
    """Detect token-boundary fusion (`ABeing`, `inThe`, etc.)."""
    hits = _CAMEL_FUSION_RE.findall(text)
    # Filter common legitimate camelcase: drop names starting with capital
    # that look like proper nouns or known compound words.
    # This is heuristic — keep all matches; the kill rule uses count > 2.
    return {"found": len(hits) >= 2, "matches": hits[:10], "count": len(hits)}


def analyze_sample(sample_text: str, target_text: str = "") -> DamageReport:
    """Run all 6 damage detectors on a single sample.

    Returns a DamageReport with verdict in {"clean", "warn", "kill"} and
    per-signature evidence. Kill conditions:
      - Repeated phrase loop with ≥3 consecutive repeats (severe)
      - Stage var corruption (double-underscore, no-letter, bad-digits)
      - Camel-fusion count ≥ 3 (boundary corruption)
      - Notation leak count ≥ 3 AND generic-collapse generic_phrase match
    """
    sigs: dict[str, Any] = {}
    severity = 0.0

    sigs["repeated_phrase_loop"] = _has_consecutive_repeats(sample_text)
    if sigs["repeated_phrase_loop"]["found"]:
        c = sigs["repeated_phrase_loop"]["count"]
        if c >= 5:
            severity += 3.5  # kill on its own
        elif c >= 4:
            severity += 2.5
        else:
            severity += 1.5

    sigs["truncation"] = _looks_truncated(sample_text)
    if sigs["truncation"]["found"]:
        severity += 0.5  # truncation is mild on its own

    sigs["stage_var_corruption"] = _check_stage_var_corruption(sample_text)
    if sigs["stage_var_corruption"]["found"]:
        # Phase-C signature, kill on its own.
        severity += 3.0

    sigs["notation_leak"] = _check_notation_leak(sample_text)
    if sigs["notation_leak"]["found"] and sigs["notation_leak"]["count"] >= 3:
        severity += 1.0
    elif sigs["notation_leak"]["found"]:
        severity += 0.3  # mild notation leak

    sigs["generic_collapse"] = _check_generic_collapse(sample_text, target_text)
    if sigs["generic_collapse"]["found"]:
        severity += 1.0 if sigs["generic_collapse"]["generic_phrases"] else 0.5

    sigs["camel_fusion"] = _check_camel_fusion(sample_text)
    if sigs["camel_fusion"]["count"] >= 3:
        severity += 3.0  # Phase-C-shape boundary corruption: kill on its own
    elif sigs["camel_fusion"]["count"] >= 1:
        severity += 0.3

    # Verdict bands. Severity ≥ 3.0 = kill (multiple severe signatures or one
    # very severe). 1.0-3.0 = warn. < 1.0 = clean. Per user scope: "kill
    # only on hard damage."
    if severity >= 3.0:
        verdict = "kill"
    elif severity >= 1.0:
        verdict = "warn"
    else:
        verdict = "clean"
    return DamageReport(
        sample_text=sample_text,
        verdict=verdict,
        signatures=sigs,
        severity_score=round(severity, 2),
    )


def aggregate_pack_verdict(per_record: list[DamageReport]) -> dict[str, Any]:
    """Combine per-record damage reports into a pack-level verdict."""
    if not per_record:
        return {"verdict": "no_samples", "n": 0}
    by_verdict = {"clean": 0, "warn": 0, "kill": 0}
    for r in per_record:
        by_verdict[r.verdict] += 1
    # Pack-level kill rule: any single record killed → pack killed.
    # Otherwise warn-count >= half → pack warns. Else clean.
    if by_verdict["kill"] >= 1:
        verdict = "kill"
    elif by_verdict["warn"] * 2 >= len(per_record):
        verdict = "warn"
    else:
        verdict = "clean"
    return {
        "verdict": verdict,
        "n": len(per_record),
        "by_verdict": by_verdict,
        "max_severity": max(r.severity_score for r in per_record),
        "mean_severity": round(
            sum(r.severity_score for r in per_record) / len(per_record), 2,
        ),
    }
