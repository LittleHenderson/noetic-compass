"""Plain English Mode — translates CAS internals into stakeholder-facing language.

Codex framing 2026-05-13: "Plain English Mode should be the front door.
Technical CAS should be the glass floor underneath it." This module is
that front door.

Pure functions, no model dependencies. Maps internal signals (slot
trace counts, identifier coverage, confidence numbers) to human
sentences. Rule-based v0 — deterministic and audit-able. The "plain
mode does not lie" discipline: every claim plain mode makes MUST be
derivable from a verifiable field in the technical output. If an ID is
missing, plain mode says so. If confidence is unknown, plain mode does
NOT claim certainty.

Bounded scope (per `decisions.md` 2026-05-13T15:30Z):
- consumed by `cas explain` Step 4 today
- consumed by chat REPL Step 5 next
- consumed by Mode 7 / Living Thought Atlas Step 7 (plain + technical
  side-by-side; this module only produces plain)

Public surface:
- `translate_explain(report)` — takes the dict produced by `cas explain`
  (with all technical fields), returns the `plain_english` sub-dict
  ready to drop in.
- `qualitative_coverage_band(coverage)` — float → "strong"/"partial"/"weak"/"none".
- `qualitative_slot_quality(slot_summary)` — slot summary → short phrase.
- `human_slot_label(slot_id)` — int → human label.

Style discipline (per user memory `feedback_plain_language_no_jargon.md`):
- No "load-bearing" / "modality mismatch" / "structured-prediction"
- Translate technical terms inline when unavoidable
- Lead with the result, not the mechanism
"""
from __future__ import annotations

from typing import Any, Optional


# Slot type IDs map (per cas_native/training/datasets/simplex_collator.py).
# Plain-English label is what the user sees; the int is what the model
# uses internally.
_SLOT_HUMAN_LABEL: dict[int, str] = {
    0: "joining word",        # CONNECTIVE
    1: "outcome marker",       # OMEGA
    2: "named identifier",     # STAGE_VAR
    3: "operator notation",    # OPERATOR
    4: "domain marker",        # DOMAIN
    5: "drive marker",         # DRIVE
    6: "register marker",      # REGISTER
    7: "fractal expression",   # FRACTAL
    8: "noetic phrase",        # NOETIC_PHRASE
}


def human_slot_label(slot_id: int) -> str:
    """Translate an internal slot_type id to a human-readable label.

    Returns "unknown slot" for ids outside the documented range, NEVER
    fabricates a label. Per the "plain mode does not lie" discipline.
    """
    return _SLOT_HUMAN_LABEL.get(int(slot_id), "unknown slot")


def qualitative_coverage_band(coverage: Optional[float]) -> str:
    """Map a coverage rate (copied/expected, in [0, 1]) to a qualitative
    band. Returns "unknown" when the input is None or not a number, NOT
    a guess. Bands:

      coverage >= 0.85  → "strong"
      coverage >= 0.50  → "partial"
      coverage >  0.0   → "weak"
      coverage == 0.0   → "none"
    """
    if coverage is None:
        return "unknown"
    try:
        c = float(coverage)
    except (TypeError, ValueError):
        return "unknown"
    if c >= 0.85:
        return "strong"
    if c >= 0.50:
        return "partial"
    if c > 0.0:
        return "weak"
    return "none"


def qualitative_slot_quality(slot_summary: dict[str, Any]) -> str:
    """Short phrase describing the slot-trace shape. Looks at length +
    longest_stage_var_run + counts to decide whether the generation
    looks structurally clean.

    Returns "unknown structure" when slot_summary is empty / missing
    expected keys — NEVER fabricates.

    Heuristics (deterministic, easy to update):
    - No tokens generated → "no tokens generated"
    - longest_stage_var_run >= 5 → "the model held a long named-identifier sequence intact"
    - At least one stage_var run >= 1 → "the model produced at least one named identifier"
    - All-connective trace → "the model only generated joining words"
    """
    if not isinstance(slot_summary, dict):
        return "unknown structure"
    length = slot_summary.get("length")
    longest = slot_summary.get("longest_stage_var_run")
    counts = slot_summary.get("counts", {})
    if not isinstance(length, int) or length <= 0:
        return "no tokens generated"
    if not isinstance(longest, int):
        return "unknown structure"
    stage_var_count = int(counts.get("2", 0)) if isinstance(counts, dict) else 0
    if longest >= 5:
        return "the model held a long named-identifier sequence intact"
    if longest >= 1 or stage_var_count >= 1:
        return "the model produced at least one named identifier"
    return "the model only generated joining words"


def _short_answer(report: dict[str, Any]) -> str:
    """One sentence: did the explain attempt succeed at producing
    SOMETHING reasonable on this checkpoint?"""
    gates = report.get("gates", {})
    generated = bool(gates.get("generated_non_empty"))
    one_copied = bool(gates.get("ge_one_identifier_copied"))
    identifiers = report.get("identifiers", {})
    n_expected = len(identifiers.get("expected", []) or [])
    n_copied = len(identifiers.get("copied", []) or [])

    if not generated:
        return "The model produced no output on this input."
    if n_expected == 0:
        return "The model produced an explanation of the expression."
    if not one_copied:
        return (
            f"The model produced an explanation but did not "
            f"carry over any of the {n_expected} named ideas in the input."
        )
    if n_copied >= n_expected:
        return (
            f"The model carried over all {n_expected} named ideas "
            f"from the input."
        )
    return (
        f"The model carried over {n_copied} of {n_expected} "
        f"named ideas from the input."
    )


def _plain_meaning(report: dict[str, Any]) -> str:
    """1-3 sentences explaining WHAT the model did, in normal language.
    Includes a per-missing-identifier note when relevant."""
    identifiers = report.get("identifiers", {})
    copied = identifiers.get("copied", []) or []
    missing = identifiers.get("missing", []) or []
    n_expected = len(identifiers.get("expected", []) or [])

    parts: list[str] = []

    if copied:
        parts.append(
            f"It correctly recognized {len(copied)} named idea(s) "
            f"from the input and carried them into the output."
        )

    if missing:
        # De-duplicate while preserving order for the user-facing list
        seen: set[str] = set()
        unique_missing: list[str] = []
        for m in missing:
            if m not in seen:
                seen.add(m)
                unique_missing.append(m)
        if len(unique_missing) == 1:
            parts.append(
                f"It missed one source idea ({unique_missing[0]})."
            )
        else:
            parts.append(
                f"It missed {len(unique_missing)} source ideas "
                f"({', '.join(unique_missing)})."
            )

    if not parts and n_expected == 0:
        parts.append(
            "The input did not contain named identifiers, so there was "
            "nothing for the model to carry over."
        )

    if not parts:
        parts.append("The model produced output but did not match "
                     "any expected source idea.")

    return " ".join(parts)


def _confidence_caveat(report: dict[str, Any]) -> Optional[str]:
    """Surface a caveat IF the technical output indicates uncertainty.
    Returns None when no caveat is warranted (plain mode does not invent
    uncertainty either).

    v0 caveats:
    - decode_seconds > 10 and identifier coverage low → "took longer than
      usual; the model may have been searching."
    - n_tokens_generated very low → "the model generated very few tokens;
      output may be incomplete."
    """
    model_block = report.get("model", {}) or {}
    decode_seconds = model_block.get("decode_seconds")
    identifiers = report.get("identifiers", {}) or {}
    coverage = identifiers.get("coverage")
    n_tokens = report.get("n_tokens_generated")

    if isinstance(decode_seconds, (int, float)) and decode_seconds > 10.0:
        if isinstance(coverage, (int, float)) and coverage < 0.5:
            return (
                "Decoding took longer than usual and copy coverage is "
                "low; the model may have been uncertain."
            )

    if isinstance(n_tokens, int) and 0 < n_tokens < 8:
        return (
            "The model generated very few tokens; the output may be "
            "incomplete."
        )

    return None


def translate_explain(report: dict[str, Any]) -> dict[str, Any]:
    """Top-level translator. Takes a `cas explain` output dict (with all
    technical fields populated) and returns a `plain_english` sub-dict
    ready to drop in alongside the technical fields.

    The returned dict shape (forward-compatible, additive):

        {
          "short_answer": "...",
          "plain_meaning": "...",
          "qualitative_coverage": "strong|partial|weak|none|unknown",
          "qualitative_slot_quality": "...",
          "confidence_caveat": None or "..."
        }

    Discipline: every claim is derivable from a field in `report`. If
    `report` lacks a required field, the corresponding output field is
    "unknown" or None, NEVER a fabricated value.
    """
    identifiers = report.get("identifiers", {}) or {}
    coverage = identifiers.get("coverage")
    slot_summary = report.get("slot_summary", {}) or {}

    return {
        "short_answer": _short_answer(report),
        "plain_meaning": _plain_meaning(report),
        "qualitative_coverage": qualitative_coverage_band(coverage),
        "qualitative_slot_quality": qualitative_slot_quality(slot_summary),
        "confidence_caveat": _confidence_caveat(report),
    }
