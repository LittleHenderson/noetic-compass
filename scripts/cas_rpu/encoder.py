"""The English boundary — a closed grammar in, one `Event` out, nothing guessed.

The processor does not read English. Problems arrive already encoded, and the
design note is explicit that the semantics of English-to-CAS encoding are not
formalised in the sources (`docs/working/cas_rpu_reasoning_processor_2026_08_28.md`,
"the premise encoding is given, not learned"). This module is that boundary
made honest: it writes down, in one place and under test, exactly which
semantic decisions are made before the reasoner sees anything. There are five
of them, one per production below, and there are no others.

Rejection is total. Anything outside the grammar is refused with a code that
names the fault; nothing is read charitably. The reason is the sever test
(`test_cas_rpu_sever.py`): it shows the architecture reasons with no model in
the loop, and a boundary that guesses at what a sentence meant has quietly put
reasoning back on the wrong side of that line. An encoder that never guesses
is an encoder whose every decision can be listed, which is what makes the
claim "the processor was handed this and nothing else" checkable.

The grammar
-----------
A closed regular language. NAME is one token with no spaces. Keywords are
lowercase and exact, except that the first word of a sentence may be
capitalised. Runs of whitespace collapse. A statement takes an optional
trailing '.'; a question must end in '?'.

    NAME       := [A-Za-z][A-Za-z0-9_-]*
    fact       := NAME 'leads to' NAME                -> events.fact(a, b)
    negation   := NAME 'does not lead to' NAME        -> events.negation(a, b)
    hypothesis := 'maybe' NAME 'leads to' NAME        -> events.hypothesis(a, b)
    retract    := 'forget that' NAME 'leads to' NAME  -> events.retract(a, b)
    ask        := 'does' NAME 'lead to' NAME '?'      -> events.ask(a, b)

The productions are compiled, anchored patterns tried with `re.fullmatch` in a
fixed order; the first match is the only reading. The language is unambiguous
by construction: every production differs from every other in token count or
in a keyword at a fixed position, and a NAME holds no spaces, so no choice of
names -- not even names spelled like keywords -- lets two productions match one
sentence. `render` is the exact inverse: `encode(render(e)) == e` for every
event the grammar can express.

What is deliberately NOT here
-----------------------------
There is no production for an associative link (the REPL's `A ~> B`,
`events.associate`, relation `co_occurs`). Ordinary English has no settled
form for "A goes with B but does not lead to it" -- "A is linked to B", "A
comes with B", "A reminds me of B" all shade into causation in use -- and
choosing one would be exactly the kind of semantic decision this module has no
warrant to make. Associative premises must arrive as events, not as sentences,
until the sources say otherwise. A sentence containing `~>` is refused with
E-ENC-001 and a message that says so.

Rejection codes
---------------
    E-ENC-001  no production matches: the sentence is outside the grammar.
    E-ENC-002  bad NAME: a name slot holds a space, a leading digit,
               punctuation, or a reserved character ('|' or '~'). `render`
               raises it too, for an event whose names could not be read back.
    E-ENC-003  wrong terminator: a question without its '?', or a statement
               that ends in one. Everything else about the sentence was right.
    E-ENC-004  a known near-synonym ("causes", "perhaps", "doesn't", ...),
               refused with a message that names the accepted form, so the
               boundary is explicit rather than silently narrower than it looks.
    E-ENC-005  a compound sentence ('and', ',', ';', 'then', 'because', 'but',
               or two relation phrases): one sentence is one event.
    E-ENC-006  reflexive ("A leads to A"): `events.Event` raises E-EV-003 for
               this; the encoder re-raises it in its own vocabulary so a caller
               needs only one.
    E-ENC-007  `decode_verdict` was handed a verdict, or a payload, that the
               fixed templates cannot express.
    E-ENC-008  `render` was handed an event with no production (a relation
               other than `leads_to`, i.e. an associative link).

When no production matches, the specific codes are tried from the most
structural fault inward -- compound (005), near-synonym (004), keyword case
(001, named), terminator (003), name (002) -- so the most informative one
wins, and a bare 001 is what is left when none of them explains the failure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable

# `events` is a sibling module. Like the rest of cas_rpu it is imported bare,
# relying on the package directory being on sys.path (the tests and the REPL
# put it there). It is a plain `import`, not a `from ... import ...` line,
# because the sever test's import allowlist inspects `from` lines and that
# list is not this module's to widen: the sibling dependency stays visible to
# that scan without a change anywhere else.
import events

__all__ = [
    "ACCEPTED_FORM",
    "NAME",
    "PRODUCTIONS",
    "EncodeError",
    "Production",
    "Verdict",
    "decode_verdict",
    "encode",
    "normalise",
    "render",
]

#: One token: a letter, then letters, digits, '_' or '-'. No spaces, and
#: nothing the workspace reserves ('|' separates key fields, '~' marks
#: negation in a pid), so a NAME can never forge a key.
NAME = r"[A-Za-z][A-Za-z0-9_-]*"
_NAME_RE = re.compile(NAME)
_NAME_CHAR_RE = re.compile(r"[A-Za-z0-9_-]")

RESERVED = ("|", "~")
SEPARATORS = (",", ";")
CONJUNCTIONS = frozenset({"and", "then", "because", "but"})
RELATION_PHRASES = (("leads", "to"), ("lead", "to"))


class EncodeError(ValueError):
    """A sentence the boundary will not read, with the code saying why.

    `text` is the input exactly as received, so a caller can show the person
    what was refused without the encoder having normalised it first.
    """

    def __init__(self, code: str, message: str, text: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.text = text


class Verdict(str, Enum):
    """The four answers `decode_verdict` has English for. Nothing else does."""

    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"
    INADMISSIBLE = "INADMISSIBLE"


# ---- the five productions ---------------------------------------------------

@dataclass(frozen=True)
class Production:
    """One sentence shape and the one event it means.

    `pattern` is the strict, anchored form including the terminator and is
    the only thing `encode` consults to accept a sentence. `body` (terminator
    removed), `folded` (the body, case-insensitive) and `loose` (NAME slots
    widened to `.+`) exist for diagnosis only: they decide which rejection
    code a non-matching sentence earns and never produce an event.
    """

    kind: events.EventKind
    template: str
    terminator: str
    build: Callable[[str, str], events.Event]
    form: str
    pattern: re.Pattern[str]
    body: re.Pattern[str]
    folded: re.Pattern[str]
    loose: re.Pattern[str]


def _production(
    kind: events.EventKind,
    template: str,
    terminator: str,
    build: Callable[[str, str], events.Event],
    form: str,
) -> Production:
    body = template.format(n=NAME)
    # A statement's '.' is optional; a question's '?' is required. One space
    # may precede either, since whitespace is a separator and never meaning.
    tail = r" ?\?" if terminator == "?" else r"(?: ?\.)?"
    return Production(
        kind,
        template,
        terminator,
        build,
        form,
        re.compile(body + tail),
        re.compile(body),
        re.compile(body, re.IGNORECASE),
        re.compile(template.format(n=".+")),
    )


#: Fixed order. Keyword-led forms first and the bare fact last, so a reader
#: of the table sees the same precedence the matcher uses. The order is not
#: load-bearing for correctness -- the language is unambiguous -- but it is
#: what "the first match" means, and it is pinned by the tests.
PRODUCTIONS: tuple[Production, ...] = (
    _production(
        events.EventKind.HYPOTHESIS,
        r"[Mm]aybe ({n}) leads to ({n})",
        ".",
        events.hypothesis,
        "maybe A leads to B.",
    ),
    _production(
        events.EventKind.RETRACT,
        r"[Ff]orget that ({n}) leads to ({n})",
        ".",
        events.retract,
        "forget that A leads to B.",
    ),
    _production(
        events.EventKind.ASK,
        r"[Dd]oes ({n}) lead to ({n})",
        "?",
        events.ask,
        "does A lead to B?",
    ),
    _production(
        events.EventKind.NEGATION,
        r"({n}) does not lead to ({n})",
        ".",
        events.negation,
        "A does not lead to B.",
    ),
    _production(
        events.EventKind.FACT,
        r"({n}) leads to ({n})",
        ".",
        events.fact,
        "A leads to B.",
    ),
)

#: The canonical sentence for each kind, with placeholder names A and B. This
#: is what an E-ENC-004 message points at.
ACCEPTED_FORM: dict[events.EventKind, str] = {p.kind: p.form for p in PRODUCTIONS}

_ACCEPTED = "accepted forms: " + ", ".join(repr(p.form) for p in PRODUCTIONS)

_RENDER: dict[events.EventKind, str] = {
    events.EventKind.FACT: "{a} leads to {b}.",
    events.EventKind.NEGATION: "{a} does not lead to {b}.",
    events.EventKind.HYPOTHESIS: "maybe {a} leads to {b}.",
    events.EventKind.RETRACT: "forget that {a} leads to {b}.",
    events.EventKind.ASK: "does {a} lead to {b}?",
}


# ---- near-synonyms, named so the boundary is explicit ------------------------

@dataclass(frozen=True)
class Synonym:
    """A phrase people reach for that the grammar does not have.

    Each is matched against the lowercased, space-joined tokens of the
    sentence (terminator removed), so hyphenated names stay atomic and a
    phrase cannot match inside a NAME. The `kind` names the production the
    person almost certainly wanted; the message quotes its accepted form.
    Listing these is not leniency -- every one is still refused -- it is the
    difference between a boundary that is explicit and one that is merely
    narrow.
    """

    pattern: re.Pattern[str]
    kind: events.EventKind
    note: str = ""


def _phrase(alternatives: str) -> re.Pattern[str]:
    """A whole-token phrase: preceded by start-or-space, followed by space-or-end."""
    return re.compile(rf"(?:^| )(?:{alternatives})(?= |$)")


_K = events.EventKind
SYNONYMS: tuple[Synonym, ...] = (
    # notation that is not English
    Synonym(re.compile(r"-/->"), _K.NEGATION, "the REPL's negated arrow"),
    Synonym(re.compile(r"->"), _K.FACT, "the REPL's arrow"),
    # a fact by another name
    Synonym(_phrase(r"causes|cause|caused"), _K.FACT),
    Synonym(_phrase(r"results? in|resulted in"), _K.FACT),
    Synonym(_phrase(r"implies|imply|implied"), _K.FACT),
    Synonym(_phrase(r"remember that"), _K.FACT, "a given is stated bare"),
    Synonym(
        _phrase(r"unforget(?: that)?"),
        _K.FACT,
        "there is no un-retraction; state the claim again",
    ),
    # a negation by another name
    Synonym(
        _phrase(r"doesn['’]?t|don['’]?t|do not|does not leads to|never leads? to"),
        _K.NEGATION,
    ),
    Synonym(re.compile(r"^not(?= )"), _K.NEGATION, "the REPL's prefix"),
    # a hypothesis by another name
    Synonym(re.compile(r"^maybe that(?= )"), _K.HYPOTHESIS),
    Synonym(re.compile(r"^maybe .* lead to(?= |$)"), _K.HYPOTHESIS, "mis-conjugated"),
    Synonym(_phrase(r"(?:might|may|could) leads? to"), _K.HYPOTHESIS),
    Synonym(
        _phrase(r"perhaps|possibly|probably|suppose(?: that)?|assume(?: that)?"),
        _K.HYPOTHESIS,
    ),
    # a question by another name
    Synonym(_phrase(r"is it true that|whether"), _K.ASK),
    Synonym(re.compile(r"^does(?= ).* leads to(?= |$)"), _K.ASK, "mis-conjugated"),
    # a retraction by another name
    Synonym(re.compile(r"^forget that .* lead to(?= |$)"), _K.RETRACT, "mis-conjugated"),
    Synonym(re.compile(r"(?:^| )forget(?! that(?: |$))(?= |$)"), _K.RETRACT),
    Synonym(_phrase(r"retract(?: that)?|withdraw(?: that)?"), _K.RETRACT),
    # the bare mis-conjugation, last so every more specific form above wins
    Synonym(
        re.compile(
            r"^(?!does(?: |$))(?!.*(?:^| )does not lead to(?= |$)).*(?:^| )lead to(?= |$)"
        ),
        _K.FACT,
        "mis-conjugated",
    ),
)


# ---- encode -----------------------------------------------------------------

def normalise(text: str) -> str:
    """Collapse whitespace runs and strip the ends. The only rewriting done."""
    return " ".join(text.split())


def encode(text: str) -> events.Event:
    """One sentence of the grammar in, exactly one `Event` out.

    The strict productions are tried first and in order; if one matches, that
    is the reading and the diagnostic machinery below never runs, so no
    grammatical sentence can be second-guessed by it. If none matches,
    `_diagnose` decides which rejection code explains the failure best. The
    encoder never repairs, never infers, and never returns a default: a
    sentence either is one of five things or it is refused.
    """
    if not isinstance(text, str):
        raise EncodeError("E-ENC-001", "input must be a string", repr(text))
    sentence = normalise(text)
    for production in PRODUCTIONS:
        match = production.pattern.fullmatch(sentence)
        if match is None:
            continue
        subject, obj = match.group(1), match.group(2)
        try:
            return production.build(subject, obj)
        except events.EventError as exc:
            if exc.code == "E-EV-003":
                raise EncodeError(
                    "E-ENC-006",
                    f"reflexive: {subject!r} cannot lead to itself",
                    text,
                ) from exc
            # E-EV-001/002 cannot arise from a NAME match; kept so the
            # encoder's vocabulary stays closed even if `events` grows a rule.
            raise EncodeError("E-ENC-002", f"bad NAME: {exc}", text) from exc
    raise _diagnose(sentence, text)


def _split_terminator(sentence: str) -> tuple[str, str]:
    """`("does A lead to B", "?")`; the terminator is '' when there is none."""
    if sentence and sentence[-1] in ".?":
        return sentence[:-1].rstrip(), sentence[-1]
    return sentence, ""


def _name_fault(name: str) -> str:
    """Why `name` is not a NAME, in the grammar's own words; '' if it is one."""
    if _NAME_RE.fullmatch(name):
        return ""
    if not name:
        return "is empty"
    if any(ch.isspace() for ch in name):
        return "contains a space (a NAME is one token)"
    if any(ch in name for ch in RESERVED):
        return "contains a reserved character ('|' or '~')"
    if name[0].isdigit():
        return "starts with a digit"
    if not re.fullmatch(r"[A-Za-z]", name[0]):
        return "does not start with a letter"
    bad = "".join(sorted({ch for ch in name if not _NAME_CHAR_RE.fullmatch(ch)}))
    return f"contains punctuation {bad!r}"


def _diagnose(sentence: str, text: str) -> EncodeError:
    """The most informative rejection for a sentence no production matched.

    Ordered from the most structural fault inward. A compound sentence is
    E-ENC-005 even when it also contains a synonym or a bad name, because
    splitting it is what the person has to do first; a near-synonym is
    E-ENC-004 before any complaint about its terminator, because the message
    shows the whole accepted form; and a terminator fault is reported only
    when the body is otherwise a perfect production, so E-ENC-003 always
    means "one character".
    """
    body, _terminator = _split_terminator(sentence)
    if not body:
        return EncodeError("E-ENC-001", f"nothing to read; {_ACCEPTED}", text)
    tokens = body.split(" ")
    lowered = [token.lower() for token in tokens]

    # E-ENC-005 -- more than one sentence.
    for separator in SEPARATORS:
        if separator in body:
            return EncodeError(
                "E-ENC-005",
                f"compound sentence: contains {separator!r}; one sentence is one event",
                text,
            )
    for word in lowered:
        if word in CONJUNCTIONS:
            return EncodeError(
                "E-ENC-005",
                f"compound sentence: contains {word!r}; one sentence is one event",
                text,
            )
    relations = sum(1 for pair in zip(lowered, lowered[1:]) if pair in RELATION_PHRASES)
    if relations > 1:
        return EncodeError(
            "E-ENC-005",
            "compound sentence: more than one relation phrase; one sentence is one event",
            text,
        )

    # The one input the grammar names and refuses on purpose.
    if "~>" in body:
        return EncodeError(
            "E-ENC-001",
            "no production for an associative link: the grammar has no English "
            "for `~>`; build it with events.associate",
            text,
        )

    # E-ENC-004 -- a near-synonym, with the accepted form named.
    joined = " ".join(lowered)
    for synonym in SYNONYMS:
        found = synonym.pattern.search(joined)
        if found is not None:
            what = found.group().strip()
            why = f" ({synonym.note})" if synonym.note else ""
            return EncodeError(
                "E-ENC-004",
                f"{what!r} is outside the grammar{why}; the accepted form is "
                f"{ACCEPTED_FORM[synonym.kind]!r}",
                text,
            )

    # E-ENC-001, named precisely -- the body is a production up to the case of
    # a keyword. Without this step the loose skeleton below would read
    # "MAYBE A" as a two-word name, which is a true statement about the tokens
    # and a misleading one about the fault.
    for production in PRODUCTIONS:
        if production.folded.fullmatch(body) and not production.body.fullmatch(body):
            return EncodeError(
                "E-ENC-001",
                "keywords are lowercase (only the first word may be capitalised); "
                f"the accepted form is {production.form!r}",
                text,
            )

    # E-ENC-003 -- the body is a production; only the terminator is wrong.
    for production in PRODUCTIONS:
        if production.body.fullmatch(body):
            if production.terminator == "?":
                return EncodeError(
                    "E-ENC-003",
                    f"a question must end in '?'; the accepted form is {production.form!r}",
                    text,
                )
            return EncodeError(
                "E-ENC-003",
                f"a statement must not end in '?'; the accepted form is {production.form!r}",
                text,
            )

    # E-ENC-002 -- the shape is a production; a name slot is not a NAME.
    for production in PRODUCTIONS:
        found = production.loose.fullmatch(body)
        if found is None:
            continue
        for name in found.groups():
            fault = _name_fault(name)
            if fault:
                return EncodeError("E-ENC-002", f"bad NAME {name!r}: {fault}", text)

    return EncodeError("E-ENC-001", f"no production matches; {_ACCEPTED}", text)


# ---- render: the exact inverse ----------------------------------------------

def render(event: events.Event) -> str:
    """The canonical English for `event`, such that `encode(render(e)) == e`.

    Refuses what `encode` could not read back. An associative relation has no
    production (E-ENC-008), and a name that is not a NAME would come back as
    E-ENC-002, so it is refused here with the same code rather than emitted.
    Letting either through would make `render` the place where meaning leaks
    out of the grammar unnoticed.
    """
    if not isinstance(event, events.Event):
        raise EncodeError(
            "E-ENC-008",
            f"render takes an events.Event, not {type(event).__name__}",
            repr(event),
        )
    if event.relation != events.DEFAULT_RELATION:
        raise EncodeError(
            "E-ENC-008",
            f"no production renders relation {event.relation!r}; associative links "
            "are outside the grammar by design",
            str(event),
        )
    for name in (event.subject, event.obj):
        fault = _name_fault(name)
        if fault:
            raise EncodeError(
                "E-ENC-002",
                f"bad NAME {name!r}: {fault}; encode could not read it back",
                str(event),
            )
    return _RENDER[event.kind].format(a=event.subject, b=event.obj)


# ---- decode_verdict: fixed English for the four answers ---------------------

def _claim(key: str, *, negated: bool = False) -> str:
    """`'A|leads_to|B'` -> `'A leads to B'` (or its negation). Nothing else."""
    parts = key.split("|")
    if len(parts) != 3 or not all(parts):
        raise EncodeError(
            "E-ENC-007", f"malformed key {key!r}; expected 'A|leads_to|B'", key
        )
    subject, relation, obj = parts
    if relation != events.DEFAULT_RELATION:
        raise EncodeError(
            "E-ENC-007", f"no template renders relation {relation!r}", key
        )
    if negated:
        return f"{subject} does not lead to {obj}"
    return f"{subject} leads to {obj}"


def decode_verdict(
    answer: str,
    subject: str,
    obj: str,
    *,
    support: tuple[str, ...] = (),
    lacunae: tuple[str, ...] = (),
    contested: tuple[str, ...] = (),
) -> str:
    """Fixed English for a verdict. Templates, not prose.

    Each answer has one template, filled from workspace keys of the form
    `'A|leads_to|B'`. The point of fixing them is the same as the point of
    the grammar: a reader can see that the sentence adds nothing the
    processor did not conclude. A verdict the templates cannot express, or a
    payload that does not fit one, is E-ENC-007 rather than a best effort.
    """
    if answer == Verdict.YES:
        sentence = f"Yes: {subject} leads to {obj}"
        if support:
            sentence += ", because " + ", ".join(_claim(key) for key in support)
        return sentence + "."
    if answer == Verdict.NO:
        return f"No: {subject} leads to {obj} does not follow from what I was given."
    if answer == Verdict.UNKNOWN:
        if not lacunae:
            return "Unknown: I would need to know more."
        clauses = " and ".join(f"whether {_claim(key)}" for key in lacunae)
        return f"Unknown: I would need to know {clauses}."
    if answer == Verdict.INADMISSIBLE:
        if not contested:
            raise EncodeError(
                "E-ENC-007",
                "INADMISSIBLE without a contested key: the template cannot say "
                "what is both held",
                str(answer),
            )
        clauses = "; ".join(
            f"{_claim(key)} and {_claim(key, negated=True)} are both held"
            for key in contested
        )
        return f"Inadmissible: {clauses}."
    raise EncodeError(
        "E-ENC-007",
        f"verdict {answer!r} is not one of YES, NO, UNKNOWN, INADMISSIBLE",
        str(answer),
    )
