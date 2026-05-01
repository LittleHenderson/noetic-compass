"""Pre-tokenizer: split input into candidate spans with character offsets.

Produces an ordered list of ``PretokenSpan`` covering the full input. Each
span knows its kind (``word`` / ``punct`` / ``whitespace`` / ``cas_candidate``)
and its character range in the original input. The assembler later promotes
these spans into ``StructuredToken`` instances by running CAS-notation
recognition, multi-word lexicon matching, and single-word lookup over them.

Rules are deterministic; the same input always produces the same spans.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Span kinds.
KIND_WORD = "word"
KIND_PUNCT = "punct"
KIND_WHITESPACE = "whitespace"
KIND_CAS_CANDIDATE = "cas_candidate"

# Characters that can plausibly start a CAS-notation literal. The CAS-notation
# recognizer module owns the actual matching; the pre-tokenizer just flags
# spans that begin with one of these so the recognizer can run cheaply.
CAS_NOTATION_LEADING_CHARS = frozenset({"^", "|", "_", "Ω", "Θ", "Φ", "→", "←", "↔", "⟨", "⟩"})

# A "word" is a run of letters / digits / underscore / apostrophe. Apostrophes
# are kept inside words so contractions ("can't", "won't", "it's") and
# possessives ("user's") survive as single spans.
_WORD_RE = re.compile(r"[A-Za-z0-9_'À-ɏ]+")
# Runs of whitespace.
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class PretokenSpan:
    """A pre-tokenized span over the original input."""

    text: str
    span: tuple[int, int]
    kind: str

    def __post_init__(self) -> None:
        if self.span[1] < self.span[0]:
            raise ValueError(f"PretokenSpan span invalid: {self.span}")

    @property
    def start(self) -> int:
        return self.span[0]

    @property
    def end(self) -> int:
        return self.span[1]


def pretokenize(text: str) -> list[PretokenSpan]:
    """Walk ``text`` left-to-right and emit covering spans.

    Three pass priorities at each cursor position:

      1. CAS-notation candidate (if leading char is in
         ``CAS_NOTATION_LEADING_CHARS``) — emit greedy run of CAS-symbol-class
         characters as a ``cas_candidate`` span. The recognizer module
         validates it.
      2. Word match via ``_WORD_RE``.
      3. Whitespace match via ``_WS_RE``.
      4. Single-character punctuation fallback.

    The result is a covering, non-overlapping span list whose concatenated
    surface_text equals the input.
    """
    spans: list[PretokenSpan] = []
    cursor = 0
    n = len(text)
    while cursor < n:
        char = text[cursor]
        # CAS-notation candidate: greedy run of CAS-symbol-class characters.
        if char in CAS_NOTATION_LEADING_CHARS:
            end = _scan_cas_candidate(text, cursor)
            spans.append(
                PretokenSpan(
                    text=text[cursor:end],
                    span=(cursor, end),
                    kind=KIND_CAS_CANDIDATE,
                )
            )
            cursor = end
            continue
        # Word.
        word_match = _WORD_RE.match(text, cursor)
        if word_match is not None:
            spans.append(
                PretokenSpan(
                    text=word_match.group(0),
                    span=(word_match.start(), word_match.end()),
                    kind=KIND_WORD,
                )
            )
            cursor = word_match.end()
            continue
        # Whitespace.
        ws_match = _WS_RE.match(text, cursor)
        if ws_match is not None:
            spans.append(
                PretokenSpan(
                    text=ws_match.group(0),
                    span=(ws_match.start(), ws_match.end()),
                    kind=KIND_WHITESPACE,
                )
            )
            cursor = ws_match.end()
            continue
        # Single-character punctuation fallback.
        spans.append(
            PretokenSpan(
                text=char,
                span=(cursor, cursor + 1),
                kind=KIND_PUNCT,
            )
        )
        cursor += 1
    return spans


_CAS_SYMBOL_CHARS = frozenset(
    "^|_{}()[]<>⟨⟩,:;=+-*·/÷×∘→←↔∈∉⊂⊆⊃⊇∪∩∖∅ΩΘΦΨ"
    "0123456789"
    "PCEOTAfE"
    "F"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
)


def _scan_cas_candidate(text: str, start: int) -> int:
    """Walk forward while characters look CAS-symbolic, then stop.

    The candidate may extend to include ASCII letters/digits because CAS
    notation includes ``F1``, ``Omega_label``, ``Θ(`` etc. The recognizer
    module is responsible for parsing what's actually inside the span and
    deciding whether it's valid CAS notation; this scan just delimits a
    plausible candidate region. Stops at whitespace or non-CAS characters.
    """
    n = len(text)
    cursor = start
    while cursor < n:
        char = text[cursor]
        if char.isspace():
            break
        if char in _CAS_SYMBOL_CHARS:
            cursor += 1
            continue
        break
    # Always advance at least one character so we make progress.
    if cursor == start:
        cursor = start + 1
    return cursor


def reassemble(spans: list[PretokenSpan]) -> str:
    """Round-trip helper: reconstruct the input from spans."""
    return "".join(span.text for span in spans)


__all__ = [
    "KIND_WORD",
    "KIND_PUNCT",
    "KIND_WHITESPACE",
    "KIND_CAS_CANDIDATE",
    "CAS_NOTATION_LEADING_CHARS",
    "PretokenSpan",
    "pretokenize",
    "reassemble",
]
