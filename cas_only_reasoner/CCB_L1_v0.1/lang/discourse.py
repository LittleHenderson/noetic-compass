"""Discourse state: pronoun resolution for the v0.1 fragment.

Pronouns are REFERENTIAL CONTENT: "it" resolves to the last mentioned
entity. Resolution failure is a typed, located error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class DiscourseError(Exception):
    pass


PRONOUNS = {"it", "he", "she"}


@dataclass
class Discourse:
    last_noun: Optional[str] = None
    history: list = field(default_factory=list)

    def mention(self, entity: str) -> None:
        self.last_noun = entity
        self.history.append(entity)

    def resolve(self, pronoun: str) -> str:
        if pronoun == "it":
            if self.last_noun is None:
                raise DiscourseError(
                    f"pronoun 'it' has no referent in the discourse")
            return self.last_noun
        raise DiscourseError(
            f"pronoun '{pronoun}' is not supported in v0.1 (only 'it')")
