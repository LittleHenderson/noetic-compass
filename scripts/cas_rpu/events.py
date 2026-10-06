"""Events — what a living reasoner is told, one statement at a time.

The processor's input type was a `Problem`: a fixed premise set plus one
query. An organism is not handed a premise set. It is told things, one at a
time, and asked things in between, and some of what it was told is later taken
back. `Event` is the unit of that stream.

This module is deliberately tiny and dependency-free: it is the shared
contract between the organism (which consumes events), the task-family
generator (which emits them), the encoder (which parses English into them),
and the oracle (which replays them). Everything downstream agrees on this
type, so nothing downstream has to agree with anything else.

Five kinds, and no sixth hidden in a flag:

    FACT         a positive given.  "A leads to B."
    HYPOTHESIS   a guess, entered at Status.HYPOTHESIS. "Maybe A leads to B."
    NEGATION     a negative given.  "A does not lead to B."
    RETRACT      epistemic withdrawal of a given. "Forget that A leads to B."
                 Absence afterwards is UNKNOWN (open world), not NO.
    ASK          the only event that produces a verdict. "Does A lead to B?"
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DEFAULT_RELATION = "leads_to"
ASSOCIATIVE_RELATION = "co_occurs"
#: A lesson is a FACT under this relation: `FACT(r, leads_to, relation="entails")`
#: says "every edge of relation r counts as a leads_to edge while this is held"
#: (Revision Streams contract §13). Told, retractable, never induced.
LESSON_RELATION = "entails"
RESERVED_RELATIONS = (DEFAULT_RELATION, ASSOCIATIVE_RELATION, LESSON_RELATION)


def is_foreign(relation: str) -> bool:
    """A relation the organism cannot chain over until a lesson entails it."""
    return relation not in RESERVED_RELATIONS


class EventKind(str, Enum):
    FACT = "fact"
    HYPOTHESIS = "hypothesis"
    NEGATION = "negation"
    RETRACT = "retract"
    ASK = "ask"


class EventError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class Event:
    """One statement to, or question for, the organism."""

    kind: EventKind
    subject: str
    obj: str
    relation: str = DEFAULT_RELATION

    def __post_init__(self) -> None:
        for name, value in (("subject", self.subject), ("obj", self.obj), ("relation", self.relation)):
            if not isinstance(value, str) or not value.strip():
                raise EventError("E-EV-001", f"{name} must be a non-empty string")
            if "|" in value or "~" in value:
                raise EventError(
                    "E-EV-002",
                    f"{name} {value!r} contains a reserved character ('|' or '~')",
                )
        if self.subject == self.obj:
            raise EventError("E-EV-003", f"reflexive event {self.subject} -> {self.obj}")

    @property
    def key(self) -> str:
        """The workspace key of the claim this event is about."""
        return f"{self.subject}|{self.relation}|{self.obj}"

    @property
    def pair(self) -> tuple[str, str]:
        return (self.subject, self.obj)

    def canonical(self) -> dict:
        """Stable form for fingerprints and journals."""
        return {
            "kind": self.kind.value,
            "subject": self.subject,
            "relation": self.relation,
            "obj": self.obj,
        }

    def __str__(self) -> str:
        arrow = {
            EventKind.FACT: "->",
            EventKind.HYPOTHESIS: "?>",
            EventKind.NEGATION: "-/->",
            EventKind.RETRACT: "-x->",
            EventKind.ASK: "?",
        }[self.kind]
        if self.kind is EventKind.ASK:
            return f"? {self.subject} -[{self.relation}]-> {self.obj}"
        return f"{self.subject} {arrow}[{self.relation}] {self.obj}"


# ---- constructors, so callers never spell the enum -------------------------

def fact(subject: str, obj: str, relation: str = DEFAULT_RELATION) -> Event:
    return Event(EventKind.FACT, subject, obj, relation)


def hypothesis(subject: str, obj: str, relation: str = DEFAULT_RELATION) -> Event:
    return Event(EventKind.HYPOTHESIS, subject, obj, relation)


def negation(subject: str, obj: str, relation: str = DEFAULT_RELATION) -> Event:
    return Event(EventKind.NEGATION, subject, obj, relation)


def retract(subject: str, obj: str, relation: str = DEFAULT_RELATION) -> Event:
    return Event(EventKind.RETRACT, subject, obj, relation)


def ask(subject: str, obj: str, relation: str = DEFAULT_RELATION) -> Event:
    return Event(EventKind.ASK, subject, obj, relation)


def lesson(relation: str) -> Event:
    """`relation` entails `leads_to`: the one kind of lesson the grammar admits (§13)."""
    if not is_foreign(relation):
        raise EventError("E-EV-004", f"a lesson must name a foreign relation, not {relation!r}")
    return Event(EventKind.FACT, relation, DEFAULT_RELATION, LESSON_RELATION)


def unlesson(relation: str) -> Event:
    """Withdraw the lesson for `relation`."""
    if not is_foreign(relation):
        raise EventError("E-EV-004", f"a lesson must name a foreign relation, not {relation!r}")
    return Event(EventKind.RETRACT, relation, DEFAULT_RELATION, LESSON_RELATION)


def associate(subject: str, obj: str) -> Event:
    """A FACT under the associative relation: `^8` follows it, `^6` rejects it."""
    return Event(EventKind.FACT, subject, obj, ASSOCIATIVE_RELATION)
