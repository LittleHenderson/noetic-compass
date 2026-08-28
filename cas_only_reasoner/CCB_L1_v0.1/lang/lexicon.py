"""The surface language memory: word forms, POS, senses, status.

Entries are VERSIONED content. Verified entries never change silently:
a correction versions the entry and keeps its history. Promotion and
correction both leave a paper trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class LexiconError(Exception):
    """A lexicon operation violated the acquisition rules."""


@dataclass
class LexiconEntry:
    form: str
    pos: str                  # noun | adj | verb | article | pronoun | copula
    sense: str
    status: str = "provisional"   # provisional | verified
    provenance: str = "teacher"
    revision: int = 1
    history: List[Dict] = field(default_factory=list)

    def to_json(self) -> Dict:
        return {
            "form": self.form, "pos": self.pos, "sense": self.sense,
            "status": self.status, "provenance": self.provenance,
            "revision": self.revision, "history": list(self.history),
        }


class Lexicon:
    def __init__(self, entries=None) -> None:
        self.entries: Dict[str, LexiconEntry] = {}
        if isinstance(entries, dict):
            for form, raw in entries.items():
                entry = LexiconEntry(form, raw.get("pos"), raw.get("sense"))
                entry.status = raw.get("status", "verified")
                entry.provenance = raw.get("provenance", "seed")
                entry.revision = raw.get("revision", 1)
                self.entries[form] = entry
        else:
            for raw in entries or []:
                entry = LexiconEntry(**{k: raw[k] for k in
                                        ("form", "pos", "sense")})
                entry.status = raw.get("status", "verified")
                entry.provenance = raw.get("provenance", "seed")
                entry.revision = raw.get("revision", 1)
                self.entries[entry.form] = entry

    def lookup(self, form: str) -> Optional[LexiconEntry]:
        return self.entries.get(form)

    def add_provisional(self, form: str, pos: str, sense: str,
                        provenance: str = "teacher") -> LexiconEntry:
        if form in self.entries:
            raise LexiconError(f"word '{form}' already in lexicon")
        entry = LexiconEntry(form, pos, sense, "provisional", provenance, 1)
        self.entries[form] = entry
        return entry

    def promote(self, form: str) -> LexiconEntry:
        entry = self.entries.get(form)
        if entry is None:
            raise LexiconError(f"word '{form}' not in lexicon")
        entry.history.append({"revision": entry.revision, "status": entry.status,
                              "sense": entry.sense})
        entry.status = "verified"
        entry.revision += 1
        return entry

    def correct(self, form: str, new_sense: str,
                provenance: str = "correction") -> LexiconEntry:
        """Explicit, versioned correction. Verified entries never change
        silently: their prior sense stays in history."""
        entry = self.entries.get(form)
        if entry is None:
            raise LexiconError(f"word '{form}' not in lexicon")
        if entry.sense == new_sense:
            return entry
        entry.history.append({"revision": entry.revision, "status": entry.status,
                              "sense": entry.sense, "provenance": entry.provenance})
        entry.sense = new_sense
        entry.provenance = provenance
        entry.revision += 1
        if entry.status == "verified":
            entry.status = "verified"   # corrections keep verified status but bump revision
        return entry

    def remove(self, form: str) -> None:
        if form not in self.entries:
            raise LexiconError(f"word '{form}' not in lexicon")
        del self.entries[form]

    def forms_by_sense(self, pos: str, sense: str) -> List[str]:
        return sorted(f for f, e in self.entries.items()
                      if e.pos == pos and e.sense == sense)

    def to_json(self) -> Dict:
        return {form: e.to_json() for form, e in sorted(self.entries.items())}
