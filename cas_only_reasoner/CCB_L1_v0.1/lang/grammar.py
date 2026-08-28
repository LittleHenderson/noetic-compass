"""The v0.1 grammar fragment: deterministic parse and generate.

Every parse failure is TYPED and LOCATED: the machine reports the exact
word it did not understand and its position. Generation is the inverse
template map; round-trip is a conformance property, not an accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .discourse import Discourse, PRONOUNS
from .lexicon import Lexicon
from .sem import negation, proposition, question, strip_wrappers


@dataclass
class ParseError(Exception):
    token: str
    index: int
    reason: str
    sentence: str

    def message(self) -> str:
        return (f"I did not understand '{self.token}' at word {self.index + 1} "
                f"of '{self.sentence}' ({self.reason})")


def tokenize(sentence: str) -> List[str]:
    return sentence.strip().lower().replace(".", " .").replace("?", " ?").split()


def _expect_noun(lexicon: Lexicon, token: str, index: int, sentence: str) -> str:
    entry = lexicon.lookup(token)
    if entry is None:
        raise ParseError(token, index, "word not understood", sentence)
    if entry.pos != "noun":
        raise ParseError(token, index, f"'{token}' is not a noun", sentence)
    return entry.sense


def _expect_adj(lexicon: Lexicon, token: str, index: int, sentence: str) -> str:
    entry = lexicon.lookup(token)
    if entry is None:
        raise ParseError(token, index, "word not understood", sentence)
    if entry.pos != "adj":
        raise ParseError(token, index, f"'{token}' is not an adjective", sentence)
    return entry.sense


def _expect_verb(lexicon: Lexicon, token: str, index: int, sentence: str) -> str:
    entry = lexicon.lookup(token)
    if entry is None:
        raise ParseError(token, index, "word not understood", sentence)
    if entry.pos != "verb":
        raise ParseError(token, index, f"'{token}' is not a verb", sentence)
    return entry.sense


def parse(sentence: str, lexicon: Lexicon,
          discourse: Optional[Discourse] = None) -> Tuple[Dict, Discourse]:
    discourse = discourse or Discourse()
    tokens = tokenize(sentence)
    if not tokens:
        raise ParseError("", 0, "empty sentence", sentence)
    if tokens[-1] not in (".", "?"):
        raise ParseError(tokens[-1], len(tokens) - 1, "missing punctuation",
                         sentence)
    is_q = tokens[-1] == "?"
    body = tokens[:-1]

    if is_q:
        if len(body) == 4 and body[0] == "is" and body[1] == "the":
            entity = _expect_noun(lexicon, body[2], 2, sentence)
            prop = _expect_adj(lexicon, body[3], 3, sentence)
            discourse.mention(entity)
            return question(proposition("property", entity, prop)), discourse
        if len(body) == 3 and body[0] == "is" and body[1] in PRONOUNS:
            entity = discourse.resolve(body[1])
            prop = _expect_adj(lexicon, body[2], 2, sentence)
            return question(proposition("property", entity, prop)), discourse
        raise ParseError(body[0], 0, "question pattern not supported", sentence)

    # the N is ADJ .
    if (len(body) == 4 and body[0] == "the" and body[2] == "is"):
        entity = _expect_noun(lexicon, body[1], 1, sentence)
        prop = _expect_adj(lexicon, body[3], 3, sentence)
        discourse.mention(entity)
        return proposition("property", entity, prop), discourse

    # the N is not ADJ .
    if (len(body) == 5 and body[0] == "the" and body[2] == "is"
            and body[3] == "not"):
        entity = _expect_noun(lexicon, body[1], 1, sentence)
        prop = _expect_adj(lexicon, body[4], 4, sentence)
        discourse.mention(entity)
        return negation(proposition("property", entity, prop)), discourse

    # the N1 V the N2 .
    if (len(body) == 5 and body[0] == "the" and body[3] == "the"):
        subject = _expect_noun(lexicon, body[1], 1, sentence)
        verb = _expect_verb(lexicon, body[2], 2, sentence)
        obj = _expect_noun(lexicon, body[4], 4, sentence)
        discourse.mention(subject)
        discourse.mention(obj)
        return proposition("relation", verb, subject, obj), discourse

    # PRON V the N2 .
    if (len(body) == 4 and body[0] in PRONOUNS and body[2] == "the"):
        subject = discourse.resolve(body[0])
        verb = _expect_verb(lexicon, body[1], 1, sentence)
        obj = _expect_noun(lexicon, body[3], 3, sentence)
        discourse.mention(obj)
        return proposition("relation", verb, subject, obj), discourse

    # PRON is ADJ .
    if (len(body) == 3 and body[0] in PRONOUNS and body[1] == "is"):
        entity = discourse.resolve(body[0])
        prop = _expect_adj(lexicon, body[2], 2, sentence)
        return proposition("property", entity, prop), discourse

    # PRON is not ADJ .
    if (len(body) == 4 and body[0] in PRONOUNS and body[1] == "is"
            and body[2] == "not"):
        entity = discourse.resolve(body[0])
        prop = _expect_adj(lexicon, body[3], 3, sentence)
        return negation(proposition("property", entity, prop)), discourse

    raise ParseError(body[0], 0, "sentence pattern not supported", sentence)


def generate(prop: Dict, lexicon: Lexicon) -> str:
    """CAS-Sem proposition -> canonical English sentence."""
    if prop.get("pred") == "question":
        inner_prop = strip_wrappers(prop)
        stmt = _generate_statement(inner_prop, lexicon)   # "the cat is gray."
        parts = stmt[:-1].split()                          # the cat is gray
        if len(parts) == 4 and parts[0] == "the" and parts[2] == "is":
            return f"is the {parts[1]} {parts[3]}?"
        raise ValueError(f"cannot generate a question for {prop}")
    if prop.get("pred") == "negation":
        inner_prop = strip_wrappers(prop)
        return _generate_statement(inner_prop, lexicon).replace(
            " is ", " is not ", 1)
    return _generate_statement(prop, lexicon)


def _generate_statement(prop: Dict, lexicon: Lexicon) -> str:
    pred = prop.get("pred")
    args = prop.get("args", [])
    if pred == "property":
        entity, quality = args
        return f"the {_noun_surface(entity, lexicon)} is " \
               f"{_adj_surface(quality, lexicon)}."
    if pred == "relation":
        verb, subject, obj = args
        return f"the {_noun_surface(subject, lexicon)} " \
               f"{_verb_surface(verb, lexicon)} the {_noun_surface(obj, lexicon)}."
    raise ValueError(f"cannot generate English for {prop}")


def _noun_surface(sense: str, lexicon: Lexicon) -> str:
    forms = lexicon.forms_by_sense("noun", sense)
    if not forms:
        raise ValueError(f"no noun surface form for sense '{sense}'")
    return forms[0]


def _adj_surface(sense: str, lexicon: Lexicon) -> str:
    forms = lexicon.forms_by_sense("adj", sense)
    if not forms:
        raise ValueError(f"no adjective surface form for sense '{sense}'")
    return forms[0]


def _verb_surface(sense: str, lexicon: Lexicon) -> str:
    forms = lexicon.forms_by_sense("verb", sense)
    if not forms:
        raise ValueError(f"no verb surface form for sense '{sense}'")
    return forms[0]
