"""Phase 1 — strict log-only verifier for rendered fractal sequences.

Per Codex-team R&D recommendation 2026-05-10 (post 3-agent synthesis):
fractal_sequence is the next-best lever after meta-logic Phase 1.5
because records 13/14/15 all fail for the same reason — the model is
not preserving the exact ``Φ<…>`` k-sequence order, count, and
content. Three records of possible lift, structurally clean problem.

Phase 1 narrow scope (Codex-team-specified):
  - parse source like ``Φ<6:9:7:0:9:5:2:0>`` or ``Phi<3:7>``
  - extract the ordered Noetic sequence from the rendered English
    via the canonical colloquialism map
  - log expected vs observed: cardinality mismatch, position drift,
    missing positions, extra positions, repeat runs
  - DO NOT rewrite ``final_text``; the verifier passes through

This module is policy-line clean (`feedback_postprocessor_policy_line`):
no inventing content, no choosing meanings, no replacing semantic
work. The decision whether to rewrite, regenerate, or retrain is
explicitly deferred — Phase 1 produces evidence; the next round
decides the fix from data.

Three-layer gating mirrors rpm_repair / meta_logic_repair:
  1. ``apply_fractal_repair`` flag in postprocess() (default True
     since the verifier is log-only — no mutation, no risk)
  2. ``routing.task_type == "cas_to_english"`` (invalid CAS skipped)
  3. ``parse_fractal`` returns None for non-fractal sources
     (state literals, recipes, rpm_chains, meta-logic, CRO all
     no-op via ``sequence_parsed=False``)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Source-side parsing
# ---------------------------------------------------------------------------

# Match `Φ<k1:k2:...:kn>` or `Phi<k1:k2:...:kn>`. Each k is a single
# digit 0-9 (the 10 Noetics). Greek phi (U+03A6) and ASCII "Phi" are
# both supported.
_FRACTAL_RX = re.compile(
    r"(?P<notation>Φ|Phi)\s*<\s*(?P<body>\d(?:\s*:\s*\d)*)\s*>"
)


@dataclass(frozen=True)
class FractalSequence:
    """Source-side ordered k-sequence for a Φ<…> expression."""
    k_values: tuple[int, ...]
    notation: str  # "Φ" or "Phi"


def parse_fractal(source_cas: str) -> Optional[FractalSequence]:
    """Extract the ordered k-sequence from a fractal source CAS.
    Returns ``None`` for non-fractal shapes — the structural gate
    Phase 1 uses to no-op on state literals, rpm_chains, recipes,
    meta-logic, CRO."""
    m = _FRACTAL_RX.search(source_cas)
    if m is None:
        return None
    body = m.group("body")
    notation = m.group("notation")
    parts = [p.strip() for p in body.split(":")]
    try:
        k_values = tuple(int(p) for p in parts)
    except ValueError:
        return None
    return FractalSequence(k_values=k_values, notation=notation)


# ---------------------------------------------------------------------------
# Noetic colloquialism extraction from rendered text
# ---------------------------------------------------------------------------

# Mirrors the canonical map from CLAUDE.md Clarification 6, scoped
# to detection-only (no rewriting). Indicator strings are lower-case;
# the matcher is case-insensitive on the input. Order within each
# noetic does not matter for detection — we use longest-match-wins
# at each position to disambiguate overlapping phrases (e.g.,
# "popped into mind" vs "popped").
_NOETIC_INDICATORS: dict[int, tuple[str, ...]] = {
    0: ("foundational thought", "an idea", "a thought", "in your head", "all in"),
    1: ("paying attention", "make up your mind", "using your head",
        "cognitive attention", "pay attention", "pays attention",
        "paid attention", "give attention", "gives attention",
        "given attention"),
    2: ("drawn to", "speaks to", "attracted toward", "drawn toward",
        "attracted"),
    3: ("rubs the wrong way", "averse to", "repelled", "pushed away",
        "can't stomach", "wouldn't touch", "an aversion",
        "the aversion", "aversion", "averse"),
    4: ("struck a chord", "made an impression", "resonated", "hit me",
        "strikes a chord", "resonates", "resonates with",
        "strike a chord", "hits me", "resonance"),
    5: ("who one is", "who you are", "shaped by experiences",
        "shaped by experience", "sum of experiences",
        "sense of self", "one's sense of self", "one's experiences",
        "part of what makes"),
    6: ("breaking it down", "unpacking", "pulling apart",
        "what's underneath"),
    7: ("muscle memory", "practice makes perfect", "into a groove",
        "repeatedly do", "practiced rhythm", "practice-based"),
    8: ("that reminds", "one thing leads", "triggered a memory",
        "made me think", "memory trigger", "memory triggers"),
    9: ("popped into mind", "popped to mind", "just clicked",
        "out of nowhere", "came to me", "popped", "clicked"),
}


def _build_indicator_table() -> list[tuple[str, int]]:
    """Flatten the indicator dict into a longest-first sorted list
    so longest-match-wins at each scan position."""
    table: list[tuple[str, int]] = []
    for n, indicators in _NOETIC_INDICATORS.items():
        for ind in indicators:
            table.append((ind, n))
    table.sort(key=lambda x: -len(x[0]))
    return table


_INDICATOR_TABLE = _build_indicator_table()


# When two same-Noetic indicators abut on pure whitespace (e.g., "who
# one is shaped by experiences" matches both "who one is" AND "shaped
# by experiences" — both ^5 — separated only by a space), the second
# match is an ELABORATION of the first, not a separate stage emission.
# We dedup on PURE-WHITESPACE-AND-SHORT gap, NOT on punctuation gap.
#
# Trace examples:
#   "who one is shaped by experiences"   gap=" "    -> dedup (elaboration)
#   "who one is who you are"             gap=" "    -> dedup (chained elaboration)
#   "paying attention, paying attention" gap=", "   -> NO dedup (enumeration)
#   "who one is, then who one is again"  gap=", then " -> NO dedup (enumeration)
#
# The dedup is keyed on LAST-SEEN-same-k end position (whether the
# previous same-k match was emitted or suppressed) so a 3-indicator
# elaboration chain collapses to one emission.
_ELABORATION_GAP_MAX_CHARS = 3  # at most 3 whitespace chars between matches


def extract_noetic_sequence(text: str) -> list[int]:
    """Scan ``text`` left-to-right and return the ordered list of
    Noetic k-values detected via the colloquialism map. Each detected
    indicator contributes one item; longest-match-wins at each
    starting position; word boundaries enforced so "thought" doesn't
    match inside "thoughtful".

    Abutting same-Noetic matches (e.g., "who one is shaped by
    experiences" matching both `who one is` and `shaped by
    experiences` for ^5) are collapsed when separated only by pure
    whitespace. Comma-separated repetitions ("paying attention,
    paying attention") are preserved as distinct stages.
    """
    if not text:
        return []
    text_lower = text.lower()
    n = len(text_lower)
    # Track last-seen end position per k (whether emitted or suppressed)
    # so a 3-indicator chain can dedup against the most recent same-k
    # match even if the middle one was suppressed.
    last_seen_end_per_k: dict[int, int] = {}
    emitted: list[tuple[int, int, int]] = []
    i = 0
    while i < n:
        matched = False
        for ind, k in _INDICATOR_TABLE:
            ind_len = len(ind)
            if i + ind_len > n:
                continue
            if text_lower[i:i + ind_len] != ind:
                continue
            before_ok = (i == 0) or not (
                text_lower[i - 1].isalnum() or text_lower[i - 1] in "'-"
            )
            after_idx = i + ind_len
            after_ok = (after_idx == n) or not (
                text_lower[after_idx].isalnum()
                or text_lower[after_idx] in "'-"
            )
            if before_ok and after_ok:
                # Elaboration dedup: same k AND gap is pure whitespace
                # AND short -> suppress as elaboration of prior match.
                should_emit = True
                if k in last_seen_end_per_k:
                    prev_end = last_seen_end_per_k[k]
                    gap_text = text_lower[prev_end:i]
                    if (
                        gap_text.strip() == ""
                        and len(gap_text) <= _ELABORATION_GAP_MAX_CHARS
                    ):
                        should_emit = False
                if should_emit:
                    emitted.append((i, i + ind_len, k))
                # Always update last-seen tracker, whether emitted or
                # suppressed — chained elaborations need this.
                last_seen_end_per_k[k] = i + ind_len
                i += ind_len
                matched = True
                break
        if not matched:
            i += 1
    return [k for _, _, k in emitted]


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RepeatRun:
    """A run of repeated identical k-values in the FOUND sequence."""
    k_value: int
    start_position: int
    length: int


@dataclass
class FractalRepairLog:
    """Audit-friendly summary of one fractal verification pass.

    Phase 1 is LOG-ONLY: no field of this log drives mutation of
    the rendered text. The fields are diagnostic substrate for the
    next round's decision (retry, target cleanup, training)."""
    sequence_parsed: bool = False
    notation: Optional[str] = None
    expected_k_count: int = 0
    expected_k_values: list[int] = field(default_factory=list)
    found_k_count: int = 0
    found_k_sequence: list[int] = field(default_factory=list)
    cardinality_matches: bool = False
    sequence_matches: bool = False  # exact ordered match
    # When cardinality matches: positions where expected[i] != found[i].
    # When found is too long: trailing positions in found (beyond expected).
    # When found is too short: trailing positions in expected (beyond found).
    mismatch_positions: list[int] = field(default_factory=list)
    repeat_runs: list[RepeatRun] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence_parsed": self.sequence_parsed,
            "notation": self.notation,
            "expected_k_count": self.expected_k_count,
            "expected_k_values": list(self.expected_k_values),
            "found_k_count": self.found_k_count,
            "found_k_sequence": list(self.found_k_sequence),
            "cardinality_matches": self.cardinality_matches,
            "sequence_matches": self.sequence_matches,
            "mismatch_positions": list(self.mismatch_positions),
            "n_repeat_runs": len(self.repeat_runs),
            "repeat_runs": [
                {
                    "k_value": r.k_value,
                    "start_position": r.start_position,
                    "length": r.length,
                }
                for r in self.repeat_runs
            ],
            "notes": list(self.notes),
        }


def _detect_repeat_runs(seq: list[int]) -> list[RepeatRun]:
    """Find runs of length >=2 in ``seq``. Returns one RepeatRun per
    run (e.g., [3,3,3,1,2,2] -> two runs: k=3 length 3, k=2 length 2)."""
    runs: list[RepeatRun] = []
    if not seq:
        return runs
    run_start = 0
    for i in range(1, len(seq)):
        if seq[i] != seq[i - 1]:
            run_len = i - run_start
            if run_len >= 2:
                runs.append(RepeatRun(
                    k_value=seq[run_start],
                    start_position=run_start,
                    length=run_len,
                ))
            run_start = i
    final_len = len(seq) - run_start
    if final_len >= 2:
        runs.append(RepeatRun(
            k_value=seq[run_start],
            start_position=run_start,
            length=final_len,
        ))
    return runs


def _compare_sequences(
    expected: list[int], found: list[int],
) -> tuple[bool, bool, list[int]]:
    """Return (cardinality_matches, sequence_matches, mismatch_positions).

    mismatch_positions:
      - if cardinality matches: positions i where expected[i] != found[i]
      - if found is too long: trailing positions in found (extras)
      - if found is too short: trailing positions in expected (missing)
    """
    cardinality_matches = len(expected) == len(found)
    sequence_matches = expected == found
    mismatch_positions: list[int] = []
    if cardinality_matches:
        for i, (e, f) in enumerate(zip(expected, found)):
            if e != f:
                mismatch_positions.append(i)
    elif len(found) > len(expected):
        # Trailing positions in found are extras.
        mismatch_positions = list(range(len(expected), len(found)))
    else:
        # Trailing positions in expected are missing.
        mismatch_positions = list(range(len(found), len(expected)))
    return cardinality_matches, sequence_matches, mismatch_positions


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def verify_fractal_rendering(
    *,
    source_cas: str,
    rendered: str,
    sequence: Optional[FractalSequence] = None,
) -> tuple[str, FractalRepairLog]:
    """Run Phase 1 fractal verification on ``rendered``.

    Returns ``(rendered_text_unchanged, log)``. Phase 1 is strict
    log-only: ``rendered_text_unchanged`` is exactly the input.
    Callers that want to act on the diagnostic must inspect
    ``log`` and decide separately (retry, cleanup, training, ...).

    No-op contract: when the source isn't a fractal expression
    (parse_fractal returns None) or the rendered text is empty,
    return the input verbatim with ``sequence_parsed=False`` and
    no further log fields populated.
    """
    log = FractalRepairLog()
    if sequence is None:
        sequence = parse_fractal(source_cas)
    if sequence is None or not rendered:
        return rendered, log

    log.sequence_parsed = True
    log.notation = sequence.notation
    log.expected_k_count = len(sequence.k_values)
    log.expected_k_values = list(sequence.k_values)

    found = extract_noetic_sequence(rendered)
    log.found_k_sequence = found
    log.found_k_count = len(found)

    cardinality_matches, sequence_matches, mismatch_positions = (
        _compare_sequences(list(sequence.k_values), found)
    )
    log.cardinality_matches = cardinality_matches
    log.sequence_matches = sequence_matches
    log.mismatch_positions = mismatch_positions

    log.repeat_runs = _detect_repeat_runs(found)

    return rendered, log


__all__ = [
    "FractalRepairLog",
    "FractalSequence",
    "RepeatRun",
    "extract_noetic_sequence",
    "parse_fractal",
    "verify_fractal_rendering",
]
