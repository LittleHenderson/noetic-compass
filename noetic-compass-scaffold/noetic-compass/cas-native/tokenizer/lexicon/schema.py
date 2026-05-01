"""CAS lexicon schema — hand-built surface → CAS-signature dictionary.

The lexicon is the deterministic core of CAS-axis tagging. Every entry maps
a surface form (single word or multi-word expression) to an explicit
``CASSignature`` plus optional context-dependent matching predicates.

Storage format: JSONL (one entry per line). Diff-friendly, audit-friendly,
human-reviewable.

Entry fields:

  - ``surface``            — canonical surface form (case preserved for the
                             record; matching is case-insensitive against
                             ``surface_lower``).
  - ``signature``          — the CAS signature this entry asserts when it
                             matches. Encoded the same way as ``CASSignature.to_dict()``.
  - ``confidence``         — float in (0.0, 1.0], how strongly this entry
                             asserts its signature. Multi-word canonical
                             colloquialisms are typically 0.9-1.0; single
                             words 0.6-0.9.
  - ``is_multiword``       — whether the surface contains whitespace (i.e.,
                             must match across multiple pre-tokenized spans).
  - ``context_required``   — optional regex; the entry only fires when the
                             concatenated surrounding context matches this
                             pattern (case-insensitive). Used for
                             disambiguation (e.g., "kind of" as a confidence
                             hedge requires a linking-verb context).
  - ``context_blocked``    — optional regex; the entry will NOT fire when
                             surrounding context matches this pattern.
  - ``register_variants``  — optional tuple of demographic register tags
                             (e.g., ``("academic",)``, ``("working_class",)``,
                             ``("child",)``). Used by the demographic
                             coverage eval to verify cross-register
                             robustness.
  - ``notes``              — free-form text. Anti-drift annotations,
                             colloquialism citations, etymological
                             references — anything that helps a future
                             reviewer audit the entry.

Anti-drift discipline (per CAS v7.7 CLAUDE.md): ``^3`` Negative entries are
visceral, not analytical (audit/scrutinize go to ``^6`` Male). ``^8``
Above/Cause entries are associative triggering, not deductive reasoning
(deductive analysis decomposes to ``^6`` + ``^9``). ``^4`` Vibration entries
prefer etymological cognates ("struck a chord") where available.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..structured_token import CASSignature


SCHEMA_VERSION = "cas_lexicon.v1"

# Context window (in characters) considered around a candidate match for
# context_required / context_blocked predicates.
CONTEXT_WINDOW_CHARS = 32


@dataclass(frozen=True)
class LexiconEntry:
    """One entry in the CAS lexicon."""

    surface: str
    signature: CASSignature
    confidence: float = 0.85
    is_multiword: bool = False
    context_required: str | None = None
    context_blocked: str | None = None
    register_variants: tuple[str, ...] = ()
    notes: str = ""

    @property
    def surface_lower(self) -> str:
        return self.surface.lower()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.surface:
            errors.append("lexicon entry surface must be non-empty")
        if not (0.0 < self.confidence <= 1.0):
            errors.append(f"confidence={self.confidence} outside (0.0, 1.0]")
        if self.is_multiword and " " not in self.surface:
            errors.append(f"surface={self.surface!r} flagged multiword but contains no whitespace")
        if (not self.is_multiword) and " " in self.surface:
            errors.append(f"surface={self.surface!r} contains whitespace but is_multiword=False")
        for pattern_name, pattern in (
            ("context_required", self.context_required),
            ("context_blocked", self.context_blocked),
        ):
            if pattern is not None:
                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error as exc:
                    errors.append(f"{pattern_name} regex invalid: {exc}")
        errors.extend(self.signature.validate())
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "signature": self.signature.to_dict(),
            "confidence": float(self.confidence),
            "is_multiword": bool(self.is_multiword),
            "context_required": self.context_required,
            "context_blocked": self.context_blocked,
            "register_variants": list(self.register_variants),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LexiconEntry":
        return cls(
            surface=str(data["surface"]),
            signature=CASSignature.from_dict(data.get("signature", {})),
            confidence=float(data.get("confidence", 0.85)),
            is_multiword=bool(data.get("is_multiword", False)),
            context_required=data.get("context_required"),
            context_blocked=data.get("context_blocked"),
            register_variants=tuple(str(v) for v in data.get("register_variants", ())),
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True)
class LexiconLookup:
    """Result of a lexicon lookup at a specific position in the input.

    ``consumed_chars`` indicates how many characters of the original input
    this match covers (relevant for multi-word matches where the matched
    surface may span multiple pre-tokenized words plus whitespace).
    """

    entry: LexiconEntry
    matched_text: str
    consumed_chars: int


class CASLexicon:
    """In-memory CAS lexicon with single-word + multi-word lookup.

    The lexicon is split into two indexes:

      - single-word index: ``surface_lower → LexiconEntry`` for entries
        without whitespace. O(1) lookup.
      - multi-word index: list of ``LexiconEntry`` sorted longest-first by
        surface length; lookup is greedy-longest at the current position
        with context-dependent rejection.
    """

    def __init__(self, entries: Iterable[LexiconEntry]) -> None:
        single_word: dict[str, LexiconEntry] = {}
        multi_word: list[LexiconEntry] = []
        for entry in entries:
            errors = entry.validate()
            if errors:
                raise ValueError(
                    f"invalid lexicon entry surface={entry.surface!r}: {errors}"
                )
            if entry.is_multiword:
                multi_word.append(entry)
            else:
                # Last write wins for duplicate single-word surfaces; this
                # preserves an explicit override pattern. The seed lexicon
                # avoids duplicates.
                single_word[entry.surface_lower] = entry
        multi_word.sort(key=lambda e: len(e.surface), reverse=True)
        self._single_word = single_word
        self._multi_word = tuple(multi_word)
        self._compiled_required: dict[int, re.Pattern[str]] = {}
        self._compiled_blocked: dict[int, re.Pattern[str]] = {}

    @property
    def entries(self) -> tuple[LexiconEntry, ...]:
        items: list[LexiconEntry] = list(self._multi_word)
        items.extend(self._single_word.values())
        return tuple(items)

    @property
    def size(self) -> int:
        return len(self._single_word) + len(self._multi_word)

    def lookup_single_word(self, surface: str) -> LexiconEntry | None:
        return self._single_word.get(surface.lower())

    def lookup_multiword_at(
        self,
        text: str,
        position: int,
    ) -> LexiconLookup | None:
        """Greedy-longest multi-word match at ``text[position:]`` with
        context check.

        Iterates multi-word entries in longest-first order. For each entry
        whose lower-cased surface is a prefix of ``text[position:]`` (case
        insensitive), checks ``context_required`` and ``context_blocked``
        against the surrounding context. Returns the first entry that
        passes; returns ``None`` if nothing matches.
        """
        if position >= len(text):
            return None
        lower_tail = text[position:].lower()
        for entry in self._multi_word:
            surface_lower = entry.surface_lower
            if not lower_tail.startswith(surface_lower):
                continue
            consumed = len(surface_lower)
            if not self._context_passes(entry, text, position, consumed):
                continue
            return LexiconLookup(
                entry=entry,
                matched_text=text[position : position + consumed],
                consumed_chars=consumed,
            )
        return None

    def _context_passes(
        self,
        entry: LexiconEntry,
        text: str,
        position: int,
        consumed: int,
    ) -> bool:
        before_start = max(0, position - CONTEXT_WINDOW_CHARS)
        after_end = min(len(text), position + consumed + CONTEXT_WINDOW_CHARS)
        before = text[before_start:position]
        after = text[position + consumed : after_end]
        joined = f"{before}␟{after}"  # uses unit-separator as boundary
        if entry.context_required is not None:
            pattern = self._compiled_required.get(id(entry))
            if pattern is None:
                pattern = re.compile(entry.context_required, re.IGNORECASE)
                self._compiled_required[id(entry)] = pattern
            if pattern.search(joined) is None:
                return False
        if entry.context_blocked is not None:
            pattern = self._compiled_blocked.get(id(entry))
            if pattern is None:
                pattern = re.compile(entry.context_blocked, re.IGNORECASE)
                self._compiled_blocked[id(entry)] = pattern
            if pattern.search(joined) is not None:
                return False
        return True

    def to_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for entry in self.entries:
                handle.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    @classmethod
    def from_jsonl(cls, path: Path) -> "CASLexicon":
        entries: list[LexiconEntry] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_no, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"lexicon JSONL parse error at line {line_no}: {exc}"
                    ) from exc
                entries.append(LexiconEntry.from_dict(data))
        return cls(entries)


def seed_lexicon_path() -> Path:
    """Return the path to the bundled seed lexicon JSONL file."""
    return Path(__file__).resolve().parent / "seed_lexicon.jsonl"


def load_seed_lexicon() -> CASLexicon:
    """Convenience loader for the bundled seed lexicon."""
    return CASLexicon.from_jsonl(seed_lexicon_path())


__all__ = [
    "SCHEMA_VERSION",
    "CONTEXT_WINDOW_CHARS",
    "LexiconEntry",
    "LexiconLookup",
    "CASLexicon",
    "seed_lexicon_path",
    "load_seed_lexicon",
]
