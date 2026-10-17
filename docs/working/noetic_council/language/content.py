"""content.py -- CASContent, the one record type the round trip must preserve.

TRANSLATOR_SPEC.md section 2 fixes what a content record holds and how two records are
compared. This module is that record, written once, with the declared normalization:

    * terms compare as a MULTISET (order free);
    * coefficients compare as exact Fractions (see numbers.py, the owner's Q13 ruling;
      TRANSLATOR_SPEC section 2 still says "exact Decimal", which the ruling replaces for
      non-terminating values);
    * register-unspecified STAYS unspecified -- it is never read as "neutral = A";
    * names compare BYTE FOR BYTE (nothing is lowercased, trimmed or generated);
    * nothing else is normalized.

Two contents are equal only if their normalized forms are equal, so __eq__ and the
digest are both defined through normalized().

Standard library only. No model, no network, no floats in content.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys

# --- load the number layer under a private alias (see numbers.py, LOADING NOTE) -------------------------------
def _load_sibling(alias: str, filename: str):
    existing = sys.modules.get(alias)
    if existing is not None:
        return existing
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError("cannot load %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


N = _load_sibling("cce_numbers", "numbers.py")
Fraction = N.Fraction

# --- frozen structural vocabularies (CLAUDE.md; CAS_FOUNDATIONAL_CLARIFICATIONS 1, 8, 9, 10) -------------------
DOMAIN_LETTERS = ("P", "C", "E", "O")
REGISTER_ORDER = "TAfE"                     # canonical order used only for storage/diffing
REGISTER_LETTERS = tuple(REGISTER_ORDER)
DRIVE_KEYS = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
POLARITIES = ("ASSERTED", "DENIED")
EVIDENCES = ("CHECKED", "USER_SAID", "NONE")
GATE_WORDS = ("RIGHT_PATH", "UNDETERMINED")
# turn_admissibility.TURN_TYPES, as the spec cites it (section 2, "turn").
TURN_TYPES = ("OPEN", "ACK", "MIRROR", "CLARIFY", "EMPATHIZE", "ANSWER", "PLAN",
              "REFUSE", "REFUSE_CLAIM", "REPAIR", "CLOSE")
SLOT_NAMES = ("M", "I", "J", "ACT", "D", "R", "U", "P")
MAX_NEST_DEPTH = 2                          # OPEN_QUESTIONS Q9 default; TRANSLATOR_SPEC section 2

# --- typed refusals --------------------------------------------------------------------------------------------
PARSE_CODES = (
    "NOT_CCE", "AMBIGUOUS", "SLOT_TYPE", "SAME_IDEA_TRIGGER", "UNDECLARED_NAME",
    "HEDGE", "VAGUE_QUANTITY", "NEST_TOO_DEEP", "OPERATOR_DISCIPLINE",
)
RENDER_CODES = (
    "NO_FORM",              # the content has no CCE sentence at all (a FORM gap)
    "UNFILLED_SLOT",        # a frame slot is empty: a lacuna, never filled by the renderer
    "NEST_IN_SLOT_UNSAYABLE",
)
NUMBER_CODES = N.NUMBER_CODES
ALL_CODES = PARSE_CODES + RENDER_CODES + NUMBER_CODES


class Refusal(Exception):
    """A typed refusal. The word is in .code and is never invented at the call site."""

    CODES = ALL_CODES

    def __init__(self, code: str, detail: str = ""):
        if code not in ALL_CODES:
            raise ValueError("unknown refusal code %r" % (code,))
        super().__init__(code + (": " + detail if detail else ""))
        self.code = code
        self.detail = detail


def _key(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _check_letter(name: str, value, allowed) -> None:
    if value is not None and value not in allowed:
        raise ValueError("%s %r is not one of %s" % (name, value, list(allowed)))


def _canonical_register(register):
    """None stays None; a register tuple is de-duplicated into the canonical order.

    # UNDECIDED IN SPEC: does a one-element register set <A> equal the single register A?
    # TRANSLATOR_SPEC section 3 gives both a single register word ("analytical register") and a
    # register set ("in analytical and affective registers") and never says whether the two
    # coincide for one element. This build stores both as the one-letter tuple ("A",), so they
    # compare equal. test_all.py pins that choice so a change to it is visible.
    """
    if register is None:
        return None
    letters = tuple(sorted(set(register), key=REGISTER_ORDER.index))
    for letter in letters:
        if letter not in REGISTER_LETTERS:
            raise ValueError("register letter %r is not one of %s" % (letter, list(REGISTER_LETTERS)))
    return letters


# ===============================================================================================================
# Recipe pieces
# ===============================================================================================================
class State:
    """A bare state reference (noetic + domain + register + drive), used by recipe terms."""

    __slots__ = ("noetic", "domain", "register", "drive")

    def __init__(self, noetic: int, domain=None, register=None, drive=None):
        if not isinstance(noetic, int) or isinstance(noetic, bool) or not 0 <= noetic <= 9:
            raise ValueError("noetic %r is not 0-9" % (noetic,))
        _check_letter("domain", domain, DOMAIN_LETTERS)
        _check_letter("drive", drive, DRIVE_KEYS)
        self.noetic = noetic
        self.domain = domain
        self.register = _canonical_register(register)
        self.drive = drive

    def normalized(self) -> dict:
        return {"noetic": self.noetic, "domain": self.domain,
                "register": list(self.register) if self.register else None, "drive": self.drive}

    def key(self) -> str:
        return _key(self.normalized())

    def _key(self) -> str:
        return self.key()

    def __eq__(self, other):
        return isinstance(other, State) and self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __repr__(self) -> str:
        return "State(%s)" % self._key()


class RecipeTerm:
    """One prerequisite of a recipe: a state with a coefficient, an outcome, or an emergent term.

    coefficient is an exact Fraction and is NEVER None inside a recipe: a recipe term with no
    number is a lacuna, not a default of 1 (TRANSLATOR_SPEC section 3, "no number invention").
    """

    __slots__ = ("kind", "coefficient", "state", "name", "components", "result")
    KINDS = ("state", "outcome", "emergent")

    def __init__(self, coefficient, kind: str = "state", state: State = None, name: str = None,
                 components=(), result: str = None):
        if kind not in self.KINDS:
            raise ValueError("recipe term kind %r is not one of %s" % (kind, list(self.KINDS)))
        if coefficient is None:
            raise ValueError("a recipe term needs an exact coefficient; None is a lacuna")
        self.kind = kind
        self.coefficient = N.to_fraction(coefficient)
        self.state = state
        self.name = name
        self.components = tuple(components)
        self.result = result
        if kind == "state" and state is None:
            raise ValueError("a state recipe term needs a state")
        if kind == "outcome" and not name:
            raise ValueError("an outcome recipe term needs a name")
        if kind == "emergent" and (len(self.components) < 2 or not result):
            raise ValueError("an emergent recipe term needs two components and a named result")

    def normalized(self) -> dict:
        base = {"kind": self.kind, "coefficient": N.fraction_text(self.coefficient)}
        if self.kind == "state":
            base["state"] = self.state.normalized()
        elif self.kind == "outcome":
            base["name"] = self.name
        else:
            base["components"] = sorted((c.normalized() for c in self.components), key=_key)
            base["result"] = self.result
        return base

    def key(self) -> str:
        return _key(self.normalized())

    def _key(self) -> str:
        return self.key()

    def __eq__(self, other):
        return isinstance(other, RecipeTerm) and self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __repr__(self) -> str:
        return "RecipeTerm(%s)" % self._key()


class Leakage:
    """b * Lambda * Omega_side. When no number was written, coefficient stays None and
    implicit is True -- never a silent 1 (TRANSLATOR_SPEC section 3)."""

    __slots__ = ("coefficient", "side", "implicit")

    def __init__(self, coefficient, side: str, implicit: bool = False):
        if coefficient is None:
            implicit = True
        self.coefficient = None if coefficient is None else N.to_fraction(coefficient)
        self.side = side
        self.implicit = bool(implicit)

    def normalized(self) -> dict:
        return {"coefficient": None if self.coefficient is None else N.fraction_text(self.coefficient),
                "side": self.side, "implicit": self.implicit}

    def key(self) -> str:
        return _key(self.normalized())

    def _key(self) -> str:
        return self.key()

    def __eq__(self, other):
        return isinstance(other, Leakage) and self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __repr__(self) -> str:
        return "Leakage(%s)" % self._key()


class Recipe:
    """Theta(Omega): target name, prerequisite terms, leakage, catalysts, inhibitors (Clarification 9)."""

    __slots__ = ("omega", "terms", "leakage", "catalysts", "inhibitors")

    def __init__(self, omega: str, terms=(), leakage=(), catalysts=(), inhibitors=()):
        if not omega:
            raise ValueError("a recipe needs its target name (Omega)")
        self.omega = omega
        self.terms = tuple(terms)
        self.leakage = tuple(leakage)
        self.catalysts = tuple(catalysts)
        self.inhibitors = tuple(inhibitors)
        for entry in self.terms:
            if not isinstance(entry, RecipeTerm):
                raise ValueError("recipe terms are RecipeTerm records, not %r" % (entry,))
        for entry in self.leakage:
            if not isinstance(entry, Leakage):
                raise ValueError("recipe leakage entries are Leakage records, not %r" % (entry,))

    def normalized(self) -> dict:
        return {
            "omega": self.omega,
            "terms": sorted((t.normalized() for t in self.terms), key=_key),
            "leakage": sorted((l.normalized() for l in self.leakage), key=_key),
            "catalysts": sorted(self.catalysts),
            "inhibitors": sorted(self.inhibitors),
        }

    def key(self) -> str:
        return _key(self.normalized())

    def _key(self) -> str:
        return self.key()

    def __eq__(self, other):
        return isinstance(other, Recipe) and self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __repr__(self) -> str:
        return "Recipe(%s)" % self._key()


# ===============================================================================================================
# Terms
# ===============================================================================================================
class Term:
    """One CAS term: a Noetic with its slots, polarity, tail, and (in a recipe) a coefficient.

    slots is a tuple of (name, value) pairs sorted by name. A value is either a string copied
    byte for byte, or a nested CASContent (the NEST form "that [...]", depth at most 2).
    """

    __slots__ = ("noetic", "slots", "domain", "register", "drive", "polarity", "coefficient")

    def __init__(self, noetic: int, slots=None, domain=None, register=None, drive=None,
                 polarity: str = "ASSERTED", coefficient=None):
        if not isinstance(noetic, int) or isinstance(noetic, bool) or not 0 <= noetic <= 9:
            raise ValueError("noetic %r is not 0-9" % (noetic,))
        _check_letter("domain", domain, DOMAIN_LETTERS)
        _check_letter("drive", drive, DRIVE_KEYS)
        _check_letter("polarity", polarity, POLARITIES)
        self.noetic = noetic
        self.domain = domain
        self.register = _canonical_register(register)
        self.drive = drive
        self.polarity = polarity
        self.coefficient = None if coefficient is None else N.to_fraction(coefficient)
        pairs = slots or ()
        if isinstance(pairs, dict):
            pairs = pairs.items()
        cleaned = []
        for name, value in pairs:
            if name not in SLOT_NAMES:
                raise ValueError("slot name %r is not one of %s" % (name, list(SLOT_NAMES)))
            if not isinstance(value, (str, CASContent)):
                raise ValueError("slot %s holds %r; a slot holds a name or a nested content" % (name, value))
            if isinstance(value, CASContent) and value.depth() >= MAX_NEST_DEPTH:
                raise ValueError("nesting deeper than %d is refused (NEST_TOO_DEEP)" % MAX_NEST_DEPTH)
            if name in ("D", "R") and isinstance(value, str):
                # A number slot holds its exact value in ONE written form, so "0.5" and "1/2" are
                # the same slot value (the spec's normalisation, applied at the slot).
                value = N.fraction_text(N.parse_number(value))
            cleaned.append((name, value))
        cleaned.sort(key=lambda pair: pair[0])
        names = [name for name, _ in cleaned]
        if len(names) != len(set(names)):
            raise ValueError("duplicate slot name in %s" % (names,))
        self.slots = tuple(cleaned)

    # --- access ---------------------------------------------------------------------------------------------
    def slot(self, name: str, default=None):
        for key, value in self.slots:
            if key == name:
                return value
        return default

    def slot_names(self) -> tuple:
        return tuple(name for name, _ in self.slots)

    def nested(self):
        return tuple(value for _, value in self.slots if isinstance(value, CASContent))

    def depth(self) -> int:
        inner = self.nested()
        return 0 if not inner else 1 + max(item.depth() for item in inner)

    # --- comparison -----------------------------------------------------------------------------------------
    def normalized(self) -> dict:
        return {
            "noetic": self.noetic,
            "domain": self.domain,
            "register": list(self.register) if self.register else None,
            "drive": self.drive,
            "polarity": self.polarity,
            "coefficient": None if self.coefficient is None else N.fraction_text(self.coefficient),
            "slots": {name: ({"nested": value.normalized()} if isinstance(value, CASContent) else value)
                      for name, value in self.slots},
        }

    def key(self) -> str:
        return _key(self.normalized())

    def _key(self) -> str:
        return self.key()

    def __eq__(self, other):
        return isinstance(other, Term) and self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __repr__(self) -> str:
        return "Term(%s)" % self._key()


# ===============================================================================================================
# The content record
# ===============================================================================================================
class CASContent:
    """Everything the round trip must preserve, and nothing else (TRANSLATOR_SPEC section 2).

    Fields: turn, omega (the turn's target Omega), terms, recipe, relations, nesting (derived
    from nested slots, see the property), evidence, gate, lacunae, names (derived, see the
    property), plus reason for a REFUSE_CLAIM turn and fractal for the FRACTAL sentence form.
    """

    __slots__ = ("turn", "omega", "terms", "recipe", "relations", "evidence", "gate",
                 "lacunae", "reason", "fractal")

    def __init__(self, turn: str = "ANSWER", omega=None, terms=(), recipe=None, relations=(),
                 evidence: str = "NONE", gate: str = "RIGHT_PATH", lacunae=(), reason=None,
                 fractal=()):
        _check_letter("turn", turn, TURN_TYPES)
        _check_letter("evidence", evidence, EVIDENCES)
        _check_letter("gate", gate, GATE_WORDS)
        self.turn = turn
        self.omega = omega
        self.terms = tuple(terms)
        for term in self.terms:
            if not isinstance(term, Term):
                raise ValueError("terms hold Term records, not %r" % (term,))
        self.recipe = recipe
        if recipe is not None and not isinstance(recipe, Recipe):
            raise ValueError("recipe is a Recipe record")
        self.relations = tuple(tuple(relation) for relation in relations)
        self.evidence = evidence
        self.gate = gate
        self.lacunae = tuple(lacunae)
        self.reason = reason
        self.fractal = tuple(fractal)
        if gate == "UNDETERMINED":
            # "I cannot tell." says nothing else. A content that draws something while the
            # gate is UNDETERMINED could never round-trip, so it is refused here instead.
            if self.terms or self.recipe or self.relations or self.fractal or self.lacunae:
                raise ValueError("gate UNDETERMINED carries no drawn content (it is said as "
                                 "'I cannot tell.' and nothing else)")
        depth = self.depth()
        if depth > MAX_NEST_DEPTH:
            raise ValueError("nesting depth %d is deeper than %d (NEST_TOO_DEEP)" % (depth, MAX_NEST_DEPTH))

    # --- derived views over the spec's field list -----------------------------------------------------------
    @property
    def nesting(self) -> tuple:
        """The inner content records, in written order. Derived from the nested slots, so it
        cannot drift from them: the spec lists nesting as a field, and this is that field.

        # UNDECIDED IN SPEC: is "nesting" a stored field of the record or a derived view of the nested slots?
        # TRANSLATOR_SPEC section 2 lists it as a field but the NEST sentence form puts the inner
        # frame inside an Idea slot. This build derives it, so the two can never disagree; a
        # stored copy could.
        """
        inner = []
        for term in self.terms:
            inner.extend(term.nested())
        return tuple(inner)

    @property
    def names(self) -> tuple:
        """Every identifier used, byte for byte, in written order (repeats kept)."""
        found = []
        if self.omega:
            found.append(self.omega)
        for term in self.terms:
            for _, value in term.slots:
                if isinstance(value, CASContent):
                    found.extend(value.names)
                else:
                    found.append(value)
        if self.recipe is not None:
            found.append(self.recipe.omega)
            for entry in self.recipe.terms:
                if entry.kind == "state":
                    pass
                elif entry.kind == "outcome":
                    found.append(entry.name)
                else:
                    found.append(entry.result)
            found.extend(leak.side for leak in self.recipe.leakage)
            found.extend(self.recipe.catalysts)
            found.extend(self.recipe.inhibitors)
        for relation in self.relations:
            for item in relation[1:]:
                if isinstance(item, str):
                    found.append(item)
                elif isinstance(item, tuple):
                    found.extend(x for x in item if isinstance(x, str))
        found.extend(self.lacunae)
        return tuple(found)

    def depth(self) -> int:
        return max([term.depth() for term in self.terms], default=0)

    # --- normalization / identity ---------------------------------------------------------------------------
    def normalized(self) -> dict:
        return {
            "turn": self.turn,
            "evidence": self.evidence,
            "gate": self.gate,
            "omega": self.omega,
            "reason": self.reason,
            "terms": sorted((term.normalized() for term in self.terms), key=_key),
            "recipe": None if self.recipe is None else self.recipe.normalized(),
            "relations": sorted((_relation_normalized(r) for r in self.relations), key=_key),
            "fractal": [state.normalized() for state in self.fractal],
            "lacunae": sorted(self.lacunae),
            "nesting": [inner.normalized() for inner in self.nesting],
        }

    def key(self) -> str:
        return _key(self.normalized())

    def digest(self) -> str:
        return hashlib.sha256(self.key().encode("utf-8")).hexdigest()

    def record(self) -> dict:
        """The full record as plain JSON-able data, derived views included, for printing."""
        out = self.normalized()
        out["names"] = list(self.names)
        out["nesting_depth"] = self.depth()
        return out

    # --- comparison -----------------------------------------------------------------------------------------
    def __eq__(self, other):
        return isinstance(other, CASContent) and self.key() == other.key()

    def __hash__(self):
        return hash(self.key())

    def __repr__(self) -> str:
        return "CASContent(%s)" % self.key()


def _relation_normalized(relation) -> list:
    head = relation[0]
    if head == "one_of":
        return ["one_of", relation[1], sorted(set(relation[2]))]
    if head in ("cover", "partition"):
        return [head, relation[1], list(relation[2])]
    if head == "size":
        return ["size", relation[1], N.fraction_text(N.parse_number(relation[2]))]
    if head == "stock":
        return ["stock", N.fraction_text(N.parse_number(relation[1])), _key_able(relation[2])]
    return [head] + list(relation[1:])


def _key_able(value):
    if isinstance(value, State):
        return value.normalized()
    if isinstance(value, Term):
        return value.normalized()
    if isinstance(value, (tuple, list)):
        return [_key_able(item) for item in value]
    return value


def equal(left: CASContent, right: CASContent) -> bool:
    """The equality the round trip uses: normalized forms only."""
    return left.key() == right.key()


def content_hash(content: CASContent) -> str:
    return content.digest()
