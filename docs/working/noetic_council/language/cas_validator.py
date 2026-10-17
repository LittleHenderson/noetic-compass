"""cas_validator.py -- an INDEPENDENT validator of the CAS side. It never sees the English.

WHY THIS FILE EXISTS (TRANSLATOR_SPEC.md section 5, "Why the round trip is not enough alone")
A grammar that adds a made-up word to both its parser and its renderer passes its own round
trip. The spec stops that with three extra checks; this file is the third one. It is separate on
purpose:

  * it imports content.py (the record type) and the exact number layer, and NOTHING else --
    not the lexicon, not the parser, not the renderer;
  * it holds its OWN copy of the canon tables, typed out from CLAUDE.md and
    CAS_FOUNDATIONAL_CLARIFICATIONS Clarifications 1, 8, 9 and 10, so a word invented inside
    those two files cannot appear here;
  * it checks the CAS record only: Noetic numbers, Domains, Registers, Drives, slot kinds, the
    derivation each Noetic's definition forces (^5 a Mind subject, ^6 an Idea subject, ^8 two
    different Ideas), exact coefficients, and the gate/evidence rules.

So if cce_parse.py and cce_render.py both learned a new Noetic called "Blend", the round trip
would still pass and this file would still say UNKNOWN_NOETIC. That is what test_all.py checks.
"""

from __future__ import annotations

import re

from content import CASContent, N

# --- the canon, written here independently ---------------------------------------------------------------------
NOETIC_NAMES = {
    0: "Idea", 1: "Mind", 2: "Positive", 3: "Negative", 4: "Vibration",
    5: "Female", 6: "Male", 7: "Rhythm", 8: "Above/Cause", 9: "Below/Effect",
}
DOMAINS = ("P", "C", "E", "O")                 # principled, cognitive, evaluative, operational
REGISTERS = ("T", "A", "f", "E")               # transcendent, analytical, affective, embodied
DRIVES = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")   # Unity Wisdom Vitality Connection Agency
POLARITIES = ("ASSERTED", "DENIED")
EVIDENCES = ("CHECKED", "USER_SAID", "NONE")
GATES = ("RIGHT_PATH", "UNDETERMINED")
TURNS = ("OPEN", "ACK", "MIRROR", "CLARIFY", "EMPATHIZE", "ANSWER", "PLAN", "REFUSE",
         "REFUSE_CLAIM", "REPAIR", "CLOSE")
ACTS = ("intakes", "processes", "stores", "outputs")
SLOTS = ("M", "I", "J", "ACT", "D", "R", "U", "P")
UNITS = ("day", "week", "hour", "month", "year", "session")
PATTERNS = ("daily", "weekly", "hourly", "monthly", "yearly", "regular", "irregular", "alternating")
MAX_NEST = 2

# Which participants each Noetic's verbatim definition forces (Clarification 1, read here again).
REQUIRED = {
    0: ("I",),                      # "All things in and outside the Mind."  -> one Idea
    1: ("M", "I"),                  # a Mind with an Idea
    2: ("M", "I"),                  # the Mind ... an Idea
    3: ("M", "I"),
    4: ("M", "I"),                  # the degree to which an Idea resonates with the Mind
    5: ("M", "I"),                  # A MIND impregnated with an Idea
    6: ("I", "J"),                  # AN IDEA impregnated with ANOTHER Idea
    7: ("M", "I"),                  # rate and pattern a MIND is exposed to an IDEA
    8: ("I", "J", "M"),             # an Idea that triggers a DIFFERENT Idea to come to Mind
    9: ("J", "M"),                  # the Idea brought to Mind by a trigger (trigger may be unknown)
}
FORBIDDEN = {
    0: ("M", "J", "ACT"),           # ^0 carries no Mind and no second Idea
    1: ("J",),
    2: ("J",),
    3: ("J",),
    5: ("J",),
    7: ("J",),
    8: ("ACT",),
    9: ("ACT",),
}

QUOTED = re.compile(r'"[^"\r\n]{1,200}"')
OMEGA = re.compile(r"Ω_[A-Za-z0-9_]{1,64}")
MIND = re.compile(r"(?:I|you|[A-Z][A-Za-z0-9_]{0,63})")


def _quoted_or_omega(value: str) -> bool:
    return bool(QUOTED.fullmatch(value) or OMEGA.fullmatch(value))


def _mind_shaped(value: str) -> bool:
    return bool(MIND.fullmatch(value))


def _name_problems(value: str, where: str):
    """Identifiers are copied byte for byte: no stray spacing, no generated text."""
    if not isinstance(value, str) or not value:
        return ["EMPTY_NAME: %s" % where]
    if value != value.strip():
        return ["NAME_WHITESPACE: %s holds %r" % (where, value)]
    if "\u201c" in value or "\u201d" in value or "'" in value:
        return ["NAME_NOT_BYTE_FOR_BYTE: %s holds %r (double quotes only)" % (where, value)]
    return []


def _check_number(text, where):
    try:
        value = N.parse_number(text)
    except N.NumberRefusal as exc:
        return ["BAD_NUMBER: %s holds %r (%s)" % (where, text, exc.code)], None
    if value < 0:
        return ["NEGATIVE_COEFFICIENT: %s holds %r" % (where, text)], None
    return [], value


def _check_term(term, where, depth=0):
    problems = []
    if not isinstance(term.noetic, int) or not 0 <= term.noetic <= 9:
        return ["UNKNOWN_NOETIC: %s holds %r (the ten Noetics are 0-9)" % (where, term.noetic)]
    if term.domain is not None and term.domain not in DOMAINS:
        problems.append("UNKNOWN_DOMAIN: %s holds %r" % (where, term.domain))
    if term.register is not None:
        for letter in term.register:
            if letter not in REGISTERS:
                problems.append("UNKNOWN_REGISTER: %s holds %r" % (where, letter))
        if len(set(term.register)) != len(term.register):
            problems.append("REPEATED_REGISTER: %s holds %r" % (where, term.register))
    if term.drive is not None and term.drive not in DRIVES:
        problems.append("UNKNOWN_DRIVE: %s holds %r" % (where, term.drive))
    if term.polarity not in POLARITIES:
        problems.append("UNKNOWN_POLARITY: %s holds %r" % (where, term.polarity))
    if term.coefficient is not None and not isinstance(term.coefficient, N.Fraction):
        problems.append("INEXACT_COEFFICIENT: %s is not an exact Fraction" % where)

    present = set(term.slot_names())
    for name in present:
        if name not in SLOTS:
            problems.append("UNKNOWN_SLOT: %s holds the slot %r" % (where, name))
    for name in REQUIRED.get(term.noetic, ()):
        if name not in present:
            problems.append("MISSING_SLOT: %s (^%d) needs the %s slot" % (where, term.noetic, name))
    for name in FORBIDDEN.get(term.noetic, ()):
        if name in present:
            problems.append("FORBIDDEN_SLOT: %s (^%d) carries no %s slot" % (where, term.noetic, name))

    for name, value in term.slots:
        spot = "%s.%s" % (where, name)
        if isinstance(value, CASContent):
            if depth + 1 > MAX_NEST:
                problems.append("NEST_TOO_DEEP: %s" % where)
            else:
                problems.extend(_check_content(value, spot, depth + 1))
            continue
        problems.extend(_name_problems(value, spot))
        if name == "M" and not _mind_shaped(value):
            problems.append("SLOT_KIND: %s holds %r but a Mind slot takes I, you or a declared name"
                            % (spot, value))
        if name in ("I", "J") and not _quoted_or_omega(value):
            problems.append("SLOT_KIND: %s holds %r but an Idea slot takes a quoted name or Omega_"
                            % (spot, value))
        if name == "ACT" and value not in ACTS:
            problems.append("UNKNOWN_ACT: %s holds %r" % (spot, value))
        if name in ("D", "R"):
            extra, _ = _check_number(value, spot)
            problems.extend(extra)
        if name == "U" and value not in UNITS:
            problems.append("UNKNOWN_UNIT: %s holds %r" % (spot, value))
        if name == "P" and value not in PATTERNS:
            problems.append("UNKNOWN_PATTERN: %s holds %r" % (spot, value))
    if term.noetic in (6, 8, 9):
        first, second = term.slot("I"), term.slot("J")
        if isinstance(first, str) and isinstance(second, str) and first == second:
            # ^6 needs "ANOTHER Idea"; ^8 needs "a DIFFERENT Idea than itself"; ^9 likewise.
            problems.append("SAME_IDEA: %s (^%d) holds the same Idea twice (%r)" % (where, term.noetic, first))
    return problems


def _check_state(state, where):
    problems = []
    if state.noetic not in NOETIC_NAMES:
        problems.append("UNKNOWN_NOETIC: %s holds %r" % (where, state.noetic))
    if state.domain is not None and state.domain not in DOMAINS:
        problems.append("UNKNOWN_DOMAIN: %s holds %r" % (where, state.domain))
    if state.drive is not None and state.drive not in DRIVES:
        problems.append("UNKNOWN_DRIVE: %s holds %r" % (where, state.drive))
    if state.register is not None:
        for letter in state.register:
            if letter not in REGISTERS:
                problems.append("UNKNOWN_REGISTER: %s holds %r" % (where, letter))
    return problems


def _check_omega(value, where):
    if not isinstance(value, str) or not OMEGA.fullmatch(value):
        return ["BAD_OMEGA_NAME: %s holds %r" % (where, value)]
    return []


def _check_content(content: CASContent, where="content", depth=0) -> list:
    problems = []
    if content.turn not in TURNS:
        problems.append("UNKNOWN_TURN: %s holds %r" % (where, content.turn))
    if content.evidence not in EVIDENCES:
        problems.append("UNKNOWN_EVIDENCE: %s holds %r" % (where, content.evidence))
    if content.gate not in GATES:
        problems.append("UNKNOWN_GATE: %s holds %r" % (where, content.gate))
    if content.gate == "UNDETERMINED":
        if content.terms or content.recipe or content.relations or content.fractal or content.lacunae:
            problems.append("UNDETERMINED_DRAWS_SOMETHING: %s says 'I cannot tell.' and nothing else" % where)
        if content.evidence != "NONE":
            problems.append("UNDETERMINED_WITH_EVIDENCE: %s (the fixed sentence carries no prefix)" % where)
    if content.omega is not None:
        problems.extend(_check_omega(content.omega, where + ".omega"))
    if content.terms:
        if content.turn not in ("ANSWER", "ACK"):
            problems.append("TURN_WITH_TERMS: %s holds %r with terms" % (where, content.turn))
    if content.turn == "CLARIFY" and not content.lacunae:
        problems.append("CLARIFY_WITHOUT_SLOT: %s" % where)
    if content.turn == "REFUSE_CLAIM" and not content.reason:
        problems.append("REFUSE_WITHOUT_REASON: %s" % where)
    for index, term in enumerate(content.terms):
        problems.extend(_check_term(term, "%s.term[%d]" % (where, index), depth))
    for index, state in enumerate(content.fractal):
        problems.extend(_check_state(state, "%s.fractal[%d]" % (where, index)))
    if len(content.fractal) == 1:
        problems.append("FRACTAL_TOO_SHORT: %s (a sequence names two or more Noetics)" % where)
    if content.recipe is not None:
        recipe = content.recipe
        problems.extend(_check_omega(recipe.omega, where + ".recipe.omega"))
        if not recipe.terms:
            problems.append("EMPTY_RECIPE: %s" % where)
        for index, entry in enumerate(recipe.terms):
            spot = "%s.recipe.term[%d]" % (where, index)
            if not isinstance(entry.coefficient, N.Fraction):
                problems.append("INEXACT_COEFFICIENT: %s" % spot)
            elif entry.coefficient < 0:
                problems.append("NEGATIVE_COEFFICIENT: %s" % spot)
            if entry.kind not in ("state", "outcome", "emergent"):
                problems.append("UNKNOWN_RECIPE_TERM: %s holds %r" % (spot, entry.kind))
            if entry.kind == "state":
                if entry.state.domain is None:
                    problems.append("RECIPE_STATE_WITHOUT_DOMAIN: %s (the spec's STATEPHRASE "
                                    "carries its Domain)" % spot)
                problems.extend(_check_state(entry.state, spot))
            elif entry.kind == "outcome":
                problems.extend(_check_omega(entry.name, spot + ".name"))
            else:
                if len(entry.components) < 2:
                    problems.append("EMERGENT_NEEDS_TWO_COMPONENTS: %s" % spot)
                for index2, component in enumerate(entry.components):
                    problems.extend(_check_state(component, "%s.component[%d]" % (spot, index2)))
                problems.extend(_check_omega(entry.result, spot + ".result"))
        for index, leak in enumerate(recipe.leakage):
            spot = "%s.recipe.leakage[%d]" % (where, index)
            problems.extend(_check_omega(leak.side, spot))
            if leak.coefficient is None and not leak.implicit:
                problems.append("SILENT_IMPLICIT_COEFFICIENT: %s (no number and not marked implicit)" % spot)
            if leak.coefficient is not None and not isinstance(leak.coefficient, N.Fraction):
                problems.append("INEXACT_COEFFICIENT: %s" % spot)
        for name in tuple(recipe.catalysts) + tuple(recipe.inhibitors):
            problems.extend(_check_omega(name, where + ".recipe.catalyst_or_inhibitor"))
    for index, relation in enumerate(content.relations):
        spot = "%s.relation[%d]" % (where, index)
        if not relation:
            problems.append("EMPTY_RELATION: %s" % spot)
            continue
        kind = relation[0]
        if kind == "is_a":
            if len(relation) != 3 or relation[2] not in ("Mind", "Idea"):
                problems.append("BAD_DECLARATION: %s holds %r" % (spot, relation))
            else:
                problems.extend(_name_problems(relation[1], spot))
        elif kind == "one_of":
            if len(relation) != 3 or len(relation[2]) < 1:
                problems.append("BAD_MEMBERSHIP: %s holds %r" % (spot, relation))
            else:
                for item in relation[2]:
                    if not _quoted_or_omega(item):
                        problems.append("SLOT_KIND: %s member %r is not an Idea name" % (spot, item))
        elif kind == "leads_to":
            for item in relation[1:]:
                if not _quoted_or_omega(item):
                    problems.append("SLOT_KIND: %s holds %r" % (spot, item))
        elif kind == "needs_first":
            for item in relation[1:]:
                problems.extend(_check_omega(item, spot))
        elif kind == "absent":
            if len(relation) != 2:
                problems.append("BAD_ABSENCE: %s holds %r" % (spot, relation))
            else:
                problems.extend(_check_omega(relation[1], spot))
        elif kind == "stock":
            if len(relation) != 3:
                problems.append("BAD_STOCK: %s holds %r" % (spot, relation))
            else:
                extra, _ = _check_number(relation[1], spot)
                problems.extend(extra)
                target = relation[2]
                if not (_quoted_or_omega(target) or target in NOETIC_NAMES.values()
                        or any(target.startswith(name + ",") for name in NOETIC_NAMES.values())):
                    problems.append("SLOT_KIND: %s stock of %r" % (spot, target))
        else:
            problems.append("UNKNOWN_RELATION: %s holds %r" % (spot, kind))
    for index, lacuna in enumerate(content.lacunae):
        problems.extend(_name_problems(lacuna, "%s.lacuna[%d]" % (where, index)))
    return problems


def validate(content) -> tuple:
    """Every problem found, as typed words. Empty tuple means the CAS side is well formed."""
    if not isinstance(content, CASContent):
        return ("NOT_A_CONTENT: %r" % (type(content).__name__,),)
    return tuple(_check_content(content))


def is_valid(content) -> bool:
    return not validate(content)


def report(content) -> dict:
    problems = validate(content)
    return {"ok": not problems, "problems": list(problems),
            "content_hash": content.digest() if isinstance(content, CASContent) else None}


def self_check() -> dict:
    """The validator can tell a sound record from a broken one, with no English involved."""
    from content import Term

    sound = CASContent(terms=(Term(5, slots={"M": "I", "I": '"x"'}),))
    missing_participant = CASContent(terms=(Term(5, slots={"I": '"x"'}),))
    same_idea = CASContent(terms=(Term(8, slots={"I": '"x"', "J": '"x"', "M": "I"}),))
    wrong_kind = CASContent(terms=(Term(5, slots={"M": '"x"', "I": '"y"'}),))
    return {
        "sound_is_valid": is_valid(sound),
        "missing_participant_problems": list(validate(missing_participant)),
        "same_idea_problems": list(validate(same_idea)),
        "wrong_slot_kind_problems": list(validate(wrong_kind)),
    }
