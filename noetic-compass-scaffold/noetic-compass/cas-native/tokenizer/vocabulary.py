"""Stable vocabulary IDs for CAS structured-token streams.

The Wave-1 tokenizer creates ``StructuredToken`` records but intentionally
leaves ``vocab_id`` unset. This module is the next layer: it assigns stable
integer IDs while preserving the tokenizer's CAS provenance.

The important design choice is that the key is source-aware. A literal CAS
token, a lexicon phrase, and an unknown surface word can share characters but
should not collapse to the same embedding by accident.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable, Sequence

from .assembler import tokenize
from .lexicon.schema import CASLexicon
from .structured_token import StructuredToken, TokenSource


VOCAB_SCHEMA_VERSION = "structured_token_vocab.v1"

PAD_TOKEN = "<pad>"
BOS_TOKEN = "<bos>"
EOS_TOKEN = "<eos>"
UNK_TOKEN = "<unk>"
MASK_TOKEN = "<mask>"
CAS_LITERAL_TOKEN = "<cas_literal>"
LEXICON_HIT_TOKEN = "<lexicon_hit>"
FALLBACK_NEUTRAL_TOKEN = "<fallback_neutral>"

RESERVED_TOKENS: tuple[str, ...] = (
    PAD_TOKEN,
    BOS_TOKEN,
    EOS_TOKEN,
    UNK_TOKEN,
    MASK_TOKEN,
    CAS_LITERAL_TOKEN,
    LEXICON_HIT_TOKEN,
    FALLBACK_NEUTRAL_TOKEN,
)

PAD_ID = 0
BOS_ID = 1
EOS_ID = 2
UNK_ID = 3
MASK_ID = 4
CAS_LITERAL_ID = 5
LEXICON_HIT_ID = 6
FALLBACK_NEUTRAL_ID = 7

# Reserved CAS-literal tokens — vocabulary entries that MUST exist regardless
# of corpus frequency. These cover meta-logic typed constructors and v7.6
# bare production-semantics symbols which are absent or low-frequency in many
# training corpora. Keeping them in the vocabulary ensures the model can
# learn distinct embeddings for them rather than collapsing them to <unk> or
# to a surface-level fallback. See:
#   docs/working/v76_meta_logic_deep_dive_2026_05_04.md
#   docs/working/vocab14_prep_memo_2026_05_04.md
#
# Order is stable; do not reorder. New entries should be APPENDED so existing
# IDs (8..21) remain unchanged across patches.
RESERVED_CAS_TOKENS: tuple[str, ...] = (
    # 7 typed meta-logic constructors (set-theoretic on CAS primitives).
    "cas:NoeticCluster",
    "cas:StateSet",
    "cas:StateCluster",
    "cas:RelationCluster",
    "cas:CoverOf",
    "cas:PartitionOf",
    "cas:Product",
    # 4 set-relation operators most load-bearing for meta_logic bucket.
    "cas:∪",
    "cas:∩",
    "cas:∈",
    "cas:⊆",
    # 3 bare v7.6 production-semantics symbols (Lambda, Omega, Theta) without
    # the qualifier-suffix forms (Ω_label, Θ() ) already covered by other
    # patterns. Bare forms are needed for recipe and side-reaction notation.
    "cas:Λ",
    "cas:Ω",
    "cas:Θ",
)


def normalize_surface(surface_text: str) -> str:
    """Normalize natural-language surfaces while preserving internal spacing."""

    return " ".join(surface_text.strip().lower().split())


def structured_token_key(token: StructuredToken) -> str:
    """Return the source-aware vocabulary key for ``token``."""

    surface = token.surface_text.strip()
    if not surface:
        return FALLBACK_NEUTRAL_TOKEN
    if token.source == TokenSource.CAS_NOTATION:
        # CAS notation is already formal; preserve case/symbols exactly.
        return f"cas:{surface}"
    if token.source == TokenSource.LEXICON:
        return f"lex:{normalize_surface(surface)}"
    if token.source == TokenSource.LEARNED:
        return f"learned:{normalize_surface(surface)}"
    return f"surf:{normalize_surface(surface)}"


@dataclass(frozen=True)
class StructuredTokenVocabulary:
    """Deterministic mapping from structured-token keys to integer IDs."""

    token_to_id: dict[str, int]
    min_count: int = 1
    max_size: int | None = None

    def __post_init__(self) -> None:
        for expected_id, token in enumerate(RESERVED_TOKENS):
            actual_id = self.token_to_id.get(token)
            if actual_id != expected_id:
                raise ValueError(
                    f"reserved token {token!r} must have id {expected_id}, got {actual_id}"
                )
        # Reserved CAS tokens must occupy IDs immediately after the special
        # tokens. They are seeded by ``empty()`` and ``from_token_sequences``;
        # the contiguity check below guarantees no gaps and the per-token
        # check below guarantees stable ordering.
        base = len(RESERVED_TOKENS)
        for offset, token in enumerate(RESERVED_CAS_TOKENS):
            expected = base + offset
            actual = self.token_to_id.get(token)
            if actual != expected:
                raise ValueError(
                    f"reserved CAS token {token!r} must have id {expected}, got {actual}"
                )
        ids = sorted(self.token_to_id.values())
        if ids != list(range(len(ids))):
            raise ValueError("token_to_id must be contiguous from 0")

    @classmethod
    def empty(cls) -> "StructuredTokenVocabulary":
        seed: dict[str, int] = {}
        for idx, token in enumerate(RESERVED_TOKENS):
            seed[token] = idx
        offset = len(RESERVED_TOKENS)
        for idx, token in enumerate(RESERVED_CAS_TOKENS):
            seed[token] = offset + idx
        return cls(seed)

    @classmethod
    def from_token_sequences(
        cls,
        token_sequences: Iterable[Sequence[StructuredToken]],
        *,
        min_count: int = 1,
        max_size: int | None = None,
        extra_tokens: Iterable[str] = (),
    ) -> "StructuredTokenVocabulary":
        """Build a deterministic vocabulary from already-tokenized records."""

        seed_size = len(RESERVED_TOKENS) + len(RESERVED_CAS_TOKENS)
        if min_count <= 0:
            raise ValueError(f"min_count must be > 0, got {min_count}")
        if max_size is not None and max_size < seed_size:
            raise ValueError(
                f"max_size must be at least {seed_size}, got {max_size}"
            )

        # Seed the vocabulary with both the special-token reserved set and
        # the reserved CAS-literal set. The reserved CAS tokens are present
        # regardless of corpus frequency so the model can learn distinct
        # embeddings for them; see RESERVED_CAS_TOKENS docstring.
        token_to_id: dict[str, int] = {}
        for idx, token in enumerate(RESERVED_TOKENS):
            token_to_id[token] = idx
        offset = len(RESERVED_TOKENS)
        for idx, token in enumerate(RESERVED_CAS_TOKENS):
            token_to_id[token] = offset + idx

        counts: Counter[str] = Counter()
        for sequence in token_sequences:
            for token in sequence:
                key = structured_token_key(token)
                if key not in token_to_id:
                    counts[key] += 1
        for token in extra_tokens:
            key = str(token)
            if key not in token_to_id:
                counts[key] += max(min_count, 1)

        candidates = [
            (key, count)
            for key, count in counts.items()
            if count >= min_count and key not in token_to_id
        ]
        candidates.sort(key=lambda item: (-item[1], item[0]))

        remaining = None if max_size is None else max_size - len(token_to_id)
        if remaining is not None:
            candidates = candidates[:remaining]
        for key, _count in candidates:
            token_to_id[key] = len(token_to_id)
        return cls(token_to_id=token_to_id, min_count=min_count, max_size=max_size)

    @classmethod
    def from_texts(
        cls,
        texts: Iterable[str],
        *,
        lexicon: CASLexicon | None = None,
        include_whitespace: bool = False,
        min_count: int = 1,
        max_size: int | None = None,
    ) -> "StructuredTokenVocabulary":
        sequences = [
            tokenize(
                str(text),
                lexicon=lexicon,
                include_whitespace=include_whitespace,
            )
            for text in texts
        ]
        return cls.from_token_sequences(
            sequences,
            min_count=min_count,
            max_size=max_size,
        )

    @classmethod
    def from_records(
        cls,
        records: Iterable[dict[str, Any]],
        *,
        text_field: str = "user_prompt",
        lexicon: CASLexicon | None = None,
        include_whitespace: bool = False,
        min_count: int = 1,
        max_size: int | None = None,
    ) -> "StructuredTokenVocabulary":
        """Build from one text field only.

        The default is deliberately ``user_prompt`` so labels, assistant
        responses, and CAS answers do not leak into the input vocabulary.
        """

        texts = [str(record.get(text_field) or "") for record in records]
        return cls.from_texts(
            texts,
            lexicon=lexicon,
            include_whitespace=include_whitespace,
            min_count=min_count,
            max_size=max_size,
        )

    def __len__(self) -> int:
        return len(self.token_to_id)

    @property
    def id_to_token(self) -> tuple[str, ...]:
        ordered = [""] * len(self.token_to_id)
        for token, idx in self.token_to_id.items():
            ordered[idx] = token
        return tuple(ordered)

    def id_for_key(self, key: str) -> int:
        return self.token_to_id.get(key, UNK_ID)

    def id_for_token(self, token: StructuredToken) -> int:
        key = structured_token_key(token)
        known = self.token_to_id.get(key)
        if known is not None:
            return known
        if key == FALLBACK_NEUTRAL_TOKEN:
            return FALLBACK_NEUTRAL_ID
        if token.source == TokenSource.CAS_NOTATION:
            return CAS_LITERAL_ID
        if token.source == TokenSource.LEXICON:
            return LEXICON_HIT_ID
        return UNK_ID

    def ids_for_tokens(self, tokens: Sequence[StructuredToken]) -> list[int]:
        return [self.id_for_token(token) for token in tokens]

    def assign_ids(self, tokens: Sequence[StructuredToken]) -> list[StructuredToken]:
        """Return copies of ``tokens`` with ``vocab_id`` populated."""

        return [
            replace(token, vocab_id=self.id_for_token(token))
            for token in tokens
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": VOCAB_SCHEMA_VERSION,
            "token_to_id": dict(sorted(self.token_to_id.items(), key=lambda item: item[1])),
            "min_count": self.min_count,
            "max_size": self.max_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructuredTokenVocabulary":
        version = data.get("schema_version")
        if version != VOCAB_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported vocabulary schema_version {version!r}; "
                f"expected {VOCAB_SCHEMA_VERSION!r}"
            )
        token_to_id = {
            str(token): int(idx)
            for token, idx in dict(data["token_to_id"]).items()
        }
        return cls(
            token_to_id=token_to_id,
            min_count=int(data.get("min_count", 1)),
            max_size=data.get("max_size"),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "StructuredTokenVocabulary":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


__all__ = [
    "VOCAB_SCHEMA_VERSION",
    "PAD_TOKEN",
    "BOS_TOKEN",
    "EOS_TOKEN",
    "UNK_TOKEN",
    "MASK_TOKEN",
    "CAS_LITERAL_TOKEN",
    "LEXICON_HIT_TOKEN",
    "FALLBACK_NEUTRAL_TOKEN",
    "RESERVED_TOKENS",
    "RESERVED_CAS_TOKENS",
    "PAD_ID",
    "BOS_ID",
    "EOS_ID",
    "UNK_ID",
    "MASK_ID",
    "CAS_LITERAL_ID",
    "LEXICON_HIT_ID",
    "FALLBACK_NEUTRAL_ID",
    "normalize_surface",
    "structured_token_key",
    "StructuredTokenVocabulary",
]
