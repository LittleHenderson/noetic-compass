"""Token assembler — wires pre-tokenization, CAS-notation recognition, and
lexicon lookup into the final ``tokenize(text) -> list[StructuredToken]``
entry point.

Resolution order at each cursor position:

  1. CAS-notation literal — tried first. If the longest match anchored at
     ``cursor`` is a valid CAS-notation literal, emit it as a
     ``CAS_NOTATION`` token (confidence 1.0) and skip past it.
  2. Lexicon multi-word match — greedy longest-first across all multi-word
     entries with context-required / context-blocked checks. Emit a
     ``LEXICON`` token covering the matched span.
  3. Single-word lexicon lookup — for the next word-shaped pre-token.
     Emit a ``LEXICON`` token if found, otherwise a ``FALLBACK`` token
     with neutral signature.
  4. Whitespace and punctuation — emit ``FALLBACK`` tokens with neutral
     signature so the audit trail has full character coverage. (The
     embedding adapter may choose to skip these later.)

Every emitted token preserves ``surface_span`` over the original input.
"""

from __future__ import annotations

from dataclasses import dataclass

from .cas_notation import CASNotationMatch, match_cas_notation
from .lexicon.schema import CASLexicon, LexiconLookup, load_seed_lexicon
from .pretokenizer import (
    KIND_CAS_CANDIDATE,
    KIND_PUNCT,
    KIND_WHITESPACE,
    KIND_WORD,
    PretokenSpan,
    pretokenize,
)
from .structured_token import (
    CASSignature,
    StructuredToken,
    TokenSource,
)


@dataclass(frozen=True)
class TokenizeStats:
    """Summary statistics for one ``tokenize()`` call. Useful for audit."""

    n_tokens: int
    n_cas_notation: int
    n_lexicon: int
    n_fallback: int
    n_multiword: int

    def to_dict(self) -> dict[str, int]:
        return {
            "n_tokens": self.n_tokens,
            "n_cas_notation": self.n_cas_notation,
            "n_lexicon": self.n_lexicon,
            "n_fallback": self.n_fallback,
            "n_multiword": self.n_multiword,
        }


def tokenize(
    text: str,
    *,
    lexicon: CASLexicon | None = None,
    include_whitespace: bool = False,
) -> list[StructuredToken]:
    """End-to-end CAS tokenization.

    Args:
        text: Input string. May contain natural language, CAS notation, or a
            mix.
        lexicon: ``CASLexicon`` to use for lookups. If ``None``, the bundled
            seed lexicon is loaded.
        include_whitespace: If ``True``, whitespace spans are emitted as
            FALLBACK tokens with neutral signature; if ``False`` (default),
            whitespace is skipped (but offsets in remaining tokens are
            preserved).

    Returns:
        Ordered list of ``StructuredToken`` covering the input.
    """
    if lexicon is None:
        lexicon = load_seed_lexicon()
    tokens: list[StructuredToken] = []
    cursor = 0
    n = len(text)

    while cursor < n:
        # 1. CAS-notation literal.
        cas_match = match_cas_notation(text, cursor)
        if cas_match is not None and cas_match.span[0] == cursor:
            tokens.append(
                StructuredToken(
                    surface_text=cas_match.matched_text,
                    surface_span=cas_match.span,
                    cas_signature=cas_match.signature,
                    confidence=1.0,
                    source=TokenSource.CAS_NOTATION,
                )
            )
            cursor = cas_match.span[1]
            continue

        # 2. Multi-word lexicon match (only at word boundaries; multi-word
        #    surfaces always start on a non-whitespace, non-punct char).
        if not text[cursor].isspace():
            lookup = lexicon.lookup_multiword_at(text, cursor)
            if lookup is not None and lookup.consumed_chars > 0:
                tokens.append(
                    StructuredToken(
                        surface_text=lookup.matched_text,
                        surface_span=(cursor, cursor + lookup.consumed_chars),
                        cas_signature=lookup.entry.signature,
                        confidence=lookup.entry.confidence,
                        source=TokenSource.LEXICON,
                    )
                )
                cursor += lookup.consumed_chars
                continue

        # 3. Pre-tokenize at cursor — what kind of single span lives here?
        spans = pretokenize(text[cursor : cursor + 1024])
        if not spans:
            cursor += 1
            continue
        first = spans[0]
        # Re-anchor span offsets to the absolute input.
        absolute_span = (cursor + first.start, cursor + first.end)

        if first.kind == KIND_WORD:
            entry = lexicon.lookup_single_word(first.text)
            if entry is not None:
                tokens.append(
                    StructuredToken(
                        surface_text=first.text,
                        surface_span=absolute_span,
                        cas_signature=entry.signature,
                        confidence=entry.confidence,
                        source=TokenSource.LEXICON,
                    )
                )
            else:
                tokens.append(
                    StructuredToken(
                        surface_text=first.text,
                        surface_span=absolute_span,
                        cas_signature=CASSignature.neutral(),
                        confidence=0.0,
                        source=TokenSource.FALLBACK,
                    )
                )
        elif first.kind == KIND_WHITESPACE:
            if include_whitespace:
                tokens.append(
                    StructuredToken(
                        surface_text=first.text,
                        surface_span=absolute_span,
                        cas_signature=CASSignature.neutral(),
                        confidence=0.0,
                        source=TokenSource.FALLBACK,
                    )
                )
            # else: skip whitespace silently.
        elif first.kind == KIND_CAS_CANDIDATE:
            # CAS-notation match failed at step 1 (otherwise we wouldn't be
            # here). Emit the candidate as FALLBACK so audit can see it was
            # an unrecognized CAS-shaped span.
            tokens.append(
                StructuredToken(
                    surface_text=first.text,
                    surface_span=absolute_span,
                    cas_signature=CASSignature.neutral(),
                    confidence=0.0,
                    source=TokenSource.FALLBACK,
                )
            )
        else:  # KIND_PUNCT
            tokens.append(
                StructuredToken(
                    surface_text=first.text,
                    surface_span=absolute_span,
                    cas_signature=CASSignature.neutral(),
                    confidence=0.0,
                    source=TokenSource.FALLBACK,
                )
            )

        cursor = absolute_span[1]

    return tokens


def tokenize_with_stats(
    text: str,
    *,
    lexicon: CASLexicon | None = None,
    include_whitespace: bool = False,
) -> tuple[list[StructuredToken], TokenizeStats]:
    """Same as ``tokenize`` but also returns audit statistics."""
    toks = tokenize(text, lexicon=lexicon, include_whitespace=include_whitespace)
    n_cas = sum(1 for t in toks if t.source == TokenSource.CAS_NOTATION)
    n_lex = sum(1 for t in toks if t.source == TokenSource.LEXICON)
    n_fall = sum(1 for t in toks if t.source == TokenSource.FALLBACK)
    n_multi = sum(1 for t in toks if " " in t.surface_text and t.source == TokenSource.LEXICON)
    return (
        toks,
        TokenizeStats(
            n_tokens=len(toks),
            n_cas_notation=n_cas,
            n_lexicon=n_lex,
            n_fallback=n_fall,
            n_multiword=n_multi,
        ),
    )


__all__ = [
    "TokenizeStats",
    "tokenize",
    "tokenize_with_stats",
]
