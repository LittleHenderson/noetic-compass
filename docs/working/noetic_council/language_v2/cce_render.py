"""cce_render.py -- CASContent -> CCE v0.1 English.

render(content, wording=None) with wording=None returns the CANON-tier sentence: the FIXED
TWIN. A wording index returns one of the lossless variants (ALIAS tier, tail order, term order,
number form). Every wording this module can build keeps every content slot -- a frame is only
offered when its slot set EQUALS the term's slot set -- so the wordings enumerated here are the
ones that can pass the round trip, not a random guess at it.

Numbers are rendered exactly (numbers.py). A non-terminating coefficient is written p/q; there
is no path in this file that rounds one.

UNDETERMINED is rendered as exactly "I cannot tell." and is never drawn.
"""

from __future__ import annotations

import itertools
import re

import lexicon as LX
from content import CASContent, N, Refusal, State, Term

FIXED_UNDETERMINED = LX.FIXED_UNDETERMINED
MAX_WORDINGS = 96               # the enumeration cap; the fixed twin is always index 0
MAX_INNER_WORDINGS = 6          # how many of a nested content's own wordings may be drawn on
_TOKEN = re.compile(r"(\{[A-Z]\}|~\w+)")
BY_TID = {template.tid: template for template in LX.TEMPLATES}


class Wording:
    """One lossless way of saying a content. Randomness in this package only ever picks one
    of these; it never touches content (MAP.md binding constraint 2)."""

    __slots__ = ("wid", "templates", "tails", "order", "number_style", "definition", "fractal_form",
                 "inner")

    def __init__(self, wid, templates, tails, order, number_style, definition, fractal_form="colon",
                 inner=()):
        self.wid = wid
        self.templates = tuple(templates)
        self.tails = tuple(tails)
        self.order = tuple(order)
        self.number_style = number_style
        self.definition = bool(definition)
        self.fractal_form = fractal_form
        self.inner = tuple(inner)

    @property
    def tier(self) -> str:
        tiers = {BY_TID[tid].tier for tid in self.templates}
        if not tiers:
            return "CANON"
        return "CANON" if tiers == {"CANON"} else "ALIAS"

    def inner_index(self, index: int) -> int:
        if not self.inner:
            return 0
        return self.inner[min(index, len(self.inner) - 1)]

    def record(self) -> dict:
        return {"wording_id": self.wid, "tier": self.tier,
                "templates": [BY_TID[tid].text for tid in self.templates],
                "number_style": self.number_style, "definition_ref": self.definition,
                "fractal_form": self.fractal_form, "inner": list(self.inner)}

    def __repr__(self) -> str:
        return "Wording(%d, %s)" % (self.wid, self.tier)


# --- what a term can be said with ------------------------------------------------------------------------------
def template_options(term: Term) -> tuple:
    """Frames of THIS Noetic whose slot set equals the term's slot set, CANON first, table order kept.

    The Noetic is part of the filter: a wording may change the verb, the order and the number
    form, never which Noetic was meant. The slot set filter keeps every content slot: a frame
    that would drop one (for example the ^1 alias with no ACT) is simply not offered.
    """
    wanted = frozenset(term.slot_names())
    act = term.slot("ACT")
    options = [template for template in LX.TEMPLATES
               if template.noetic == term.noetic and template.slots == wanted and template.act == act]
    canon = [template for template in options if template.tier == "CANON"]
    alias = [template for template in options if template.tier == "ALIAS"]
    return tuple(canon) + tuple(alias)


def tail_items(term: Term) -> tuple:
    items = []
    if term.domain is not None:
        items.append("domain")
    if term.register is not None:
        items.append("register")
    if term.drive is not None:
        items.append("drive")
    return tuple(items)


def tail_orders(term: Term) -> tuple:
    """Every order of the tail items, canonical order first. The tail is a set of tags, so the
    order is wording, not content (GRAMMAR_CCE_v0_1.md section 4)."""
    items = tail_items(term)
    if len(items) <= 1:
        return (items,)
    seen, orders = set(), []
    for permutation in itertools.permutations(items):
        if permutation not in seen:
            seen.add(permutation)
            orders.append(permutation)
    return tuple(orders)


def _tail_text(term: Term, order) -> str:
    pieces = []
    for kind in order:
        if kind == "domain":
            pieces.append(LX.DOMAINS[term.domain])
        elif kind == "register":
            words = [LX.REGISTERS[letter] for letter in term.register]
            if len(words) == 1:
                pieces.append(words[0] + " register")
            else:
                pieces.append("in " + ", ".join(words[:-1]) + " and " + words[-1] + " registers")
        elif kind == "drive":
            pieces.append("for " + LX.DRIVES[term.drive])
    return (", " + ", ".join(pieces)) if pieces else ""


def _number_style_for(values) -> tuple:
    """The number forms every value in the content can be written in. Intersection, so a
    non-terminating coefficient keeps the whole sentence off the decimal form."""
    styles = None
    for value in values:
        available = set(N.styles_for(value))
        styles = available if styles is None else (styles & available)
    if not styles:
        return ("exact",)
    order = ("exact", "fraction", "decimal", "word")
    return tuple(style for style in order if style in styles)


def _recipe_values(recipe) -> list:
    values = [entry.coefficient for entry in recipe.terms]
    values.extend(leak.coefficient for leak in recipe.leakage if leak.coefficient is not None)
    return values


def wordings(content: CASContent, cap: int = MAX_WORDINGS) -> tuple:
    """Every lossless wording of one content, fixed twin first, capped at `cap`."""
    terms = content.terms
    per_term_templates = [template_options(term) for term in terms]
    for term, options in zip(terms, per_term_templates):
        if not options:
            raise Refusal("NO_FORM", "no frozen frame has the slot set %s of ^%d"
                          % (sorted(term.slot_names()), term.noetic))
    per_term_tails = [tail_orders(term) for term in terms]
    slots_to_order = len(terms)
    if not slots_to_order and content.recipe is not None:
        slots_to_order = len(content.recipe.terms)      # recipe terms are a multiset too
    orders = [tuple(range(slots_to_order))]
    if slots_to_order > 1:
        for permutation in itertools.permutations(range(slots_to_order)):
            if permutation not in orders:
                orders.append(permutation)
    values = _recipe_values(content.recipe) if content.recipe is not None else []
    number_styles = _number_style_for(values) if values else ("exact",)
    fractal_forms = ("colon", "inside") if content.fractal else ("colon",)
    # A definition reference is only a second wording of a state phrase (recipe or fractal).
    definition_options = (False, True) if (content.recipe is not None or content.fractal) else (False,)
    # A nested slot may be said in any of the inner content's own wordings (capped).
    nested_counts = []
    for term in terms:
        count = 1
        for inner in term.nested():
            try:
                count *= min(MAX_INNER_WORDINGS, len(wordings(inner)))
            except Refusal:
                count *= 1
        nested_counts.append(count)

    built, seen = [], set()
    for number_style in number_styles:
        for definition in definition_options:
            for fractal_form in fractal_forms:
                for order in orders:
                    for tail_choice in itertools.product(*per_term_tails) if per_term_tails else [()]:
                        for template_choice in (itertools.product(*per_term_templates)
                                                if per_term_templates else [()]):
                            for inner_choice in (itertools.product(*[range(count) for count in nested_counts])
                                                 if nested_counts else [()]):
                                signature = (tuple(template.tid for template in template_choice),
                                             tuple(tail_choice), order, number_style, definition,
                                             fractal_form, tuple(inner_choice))
                                if signature in seen:
                                    continue
                                seen.add(signature)
                                built.append(Wording(len(built),
                                                     [template.tid for template in template_choice],
                                                     tail_choice, order, number_style, definition,
                                                     fractal_form, inner_choice))
                                if len(built) >= cap:
                                    return tuple(built)
    return tuple(built)


def fixed_twin(content: CASContent) -> Wording:
    """Index 0 of the enumeration: CANON templates, canonical tail order, stored term order."""
    return wordings(content)[0]


def resolve(content: CASContent, wording) -> Wording:
    if wording is None:
        return fixed_twin(content)
    if isinstance(wording, Wording):
        return wording
    if isinstance(wording, int):
        table = wordings(content)
        if not 0 <= wording < len(table):
            raise Refusal("NO_FORM", "wording %d does not exist (there are %d)" % (wording, len(table)))
        return table[wording]
    raise Refusal("NO_FORM", "wording must be None, an index or a Wording")


# --- filling one frame -----------------------------------------------------------------------------------------
def _subject_kind(value: str) -> str:
    if value == "I":
        return "I"
    if value == "you":
        return "you"
    return "3"


def _object_mind(value: str) -> str:
    return "me" if value == "I" else value


def _fill(template, values: dict, kind: str, polarity: str) -> str:
    pieces = []
    first = True
    for piece in _TOKEN.split(template.text):
        if not piece:
            continue
        at_subject = first
        first = False
        if piece == "{M}":
            pieces.append(values["M"] if at_subject else _object_mind(values["M"]))
        elif piece == "{W}":
            mind = values["M"]
            pieces.append({"I": "I am", "you": "you are"}.get(mind, mind + " is"))
        elif piece in ("{I}", "{J}"):
            pieces.append(values[piece[1]])
        elif piece in ("{D}", "{R}", "{U}", "{P}"):
            pieces.append(values[piece[1]])
        elif piece.startswith("~"):
            forms = LX.VERBS[piece[1:]]
            key = ("neg" if polarity == "DENIED" else "") + kind
            pieces.append(forms[key])
        else:
            pieces.append(piece)
    return "".join(pieces)


def _slot_values(term: Term, template, wording: Wording, inner_index: int = 0) -> dict:
    values = {}
    for name, value in term.slots:
        if isinstance(value, CASContent):
            options = wordings(value)
            pick = options[min(inner_index, len(options) - 1)]
            values[name] = "that [%s]" % _render_inner(value, pick)
        elif name in ("D", "R"):
            values[name] = N.render_number(N.parse_number(value), wording.number_style)
        else:
            values[name] = value
    missing = template.slots - set(values)
    if missing:
        raise Refusal("UNFILLED_SLOT", "slot %s is empty: a lacuna, never filled by the renderer"
                      % sorted(missing))
    return values


def render_term(term: Term, wording=None, index: int = 0, content: CASContent = None) -> str:
    """One term as one sentence under one wording choice."""
    if content is None:
        content = CASContent(terms=(term,))
    chosen = resolve(content, wording)
    options = template_options(term)
    if not options:
        raise Refusal("NO_FORM", "no frozen frame has the slot set %s of ^%d"
                      % (sorted(term.slot_names()), term.noetic))
    tid = chosen.templates[min(index, len(chosen.templates) - 1)]
    template = BY_TID[tid]
    if template.slots != frozenset(term.slot_names()):
        raise Refusal("NO_FORM", "wording pick does not fit this term (templates and slots differ)")
    kind = _subject_kind(term.slot("M", "")) if template.text.startswith("{M}") else "3"
    values = _slot_values(term, template, chosen, chosen.inner_index(index))
    sentence = _fill(template, values, kind, term.polarity)
    tail = _tail_text(term, chosen.tails[min(index, len(chosen.tails) - 1)])
    return sentence + tail + "."


def _render_inner(content: CASContent, wording: Wording) -> str:
    """The text inside `that [...]`: one frame, no period, nothing else."""
    if (content.gate != "RIGHT_PATH" or content.evidence != "NONE" or content.recipe is not None
            or content.relations or content.fractal or content.turn != "ANSWER" or len(content.terms) != 1):
        raise Refusal("NEST_IN_SLOT_UNSAYABLE",
                      "a nested slot holds one plain frame; this content is more than that")
    inner = content.terms[0]
    sentence = render_term(inner, wording, 0, content)
    return sentence[:-1]


# --- states, relations, recipes, fractals ----------------------------------------------------------------------
def _state_text(state: State, wording: Wording) -> str:
    head = LX.DEF_REF[state.noetic] if wording.definition else LX.NOETIC_NAMES[state.noetic]
    term = Term(state.noetic, domain=state.domain, register=state.register, drive=state.drive)
    return head + _tail_text(term, tail_items(term))


def _relation_text(relation) -> str:
    kind = relation[0]
    if kind == "is_a":
        article = "an" if relation[2].lower().startswith("i") else "a"
        return "%s is %s %s." % (relation[1], article, relation[2])
    if kind == "one_of":
        return '%s is one of {%s}.' % (relation[1], ", ".join(relation[2]))
    if kind == "leads_to":
        return "Fact: %s leads to %s." % (relation[1], relation[2])
    if kind == "needs_first":
        return "%s needs %s first." % (relation[1], relation[2])
    if kind == "absent":
        return "There is no %s." % relation[1]
    if kind == "stock":
        return "There is %s of %s." % (N.render_number(N.parse_number(relation[1]), "exact"), relation[2])
    raise Refusal("NO_FORM", "no CCE sentence for the relation %r" % (kind,))


def _render_fractal(fractal, wording: Wording) -> str:
    phrases = [_state_text(state, wording) for state in fractal]
    if wording.fractal_form == "inside":
        return "The nesting is %s." % " inside ".join(phrases)
    return "The fractal sequence is %s." % " : ".join(phrases)


def _render_recipe_term(entry, wording: Wording) -> str:
    number = N.render_number(entry.coefficient, wording.number_style)
    if entry.kind == "outcome":
        return "%s of %s" % (number, entry.name)
    if entry.kind == "emergent":
        parts = " combined with ".join(_state_text(component, wording) for component in entry.components)
        return "%s of (%s into %s)" % (number, parts, entry.result)
    return "%s of %s" % (number, _state_text(entry.state, wording))


def _render_recipe(recipe, wording: Wording) -> str:
    order = [index for index in wording.order if index < len(recipe.terms)] or list(range(len(recipe.terms)))
    parts = [_render_recipe_term(recipe.terms[index], wording) for index in order]
    if not parts:
        raise Refusal("NO_FORM", "a recipe with no prerequisite has no CCE form")
    text = "To make %s, use %s." % (recipe.omega, "; plus ".join(parts))
    for leak in recipe.leakage:
        if leak.coefficient is None:
            text += " Side product: %s." % leak.side
        else:
            text += " Side product: %s of %s." % (N.render_number(leak.coefficient, wording.number_style),
                                                 leak.side)
    for catalyst in recipe.catalysts:
        text += " Helped by %s." % catalyst
    for inhibitor in recipe.inhibitors:
        text += " Slowed by %s." % inhibitor
    return text


# --- the entry point -------------------------------------------------------------------------------------------
def render(content: CASContent, wording=None) -> str:
    """Render one content to one CCE sentence (or a short sequence of them).

    Raises Refusal with NO_FORM when the content has no CCE form at all -- which is how a
    station reports a FORM gap instead of approximating one.
    """
    if not isinstance(content, CASContent):
        raise TypeError("render() takes a CASContent")
    if content.gate == "UNDETERMINED":
        return FIXED_UNDETERMINED              # fixed, never drawn, never varied
    chosen = resolve(content, wording)
    prefix = {"CHECKED": "I checked: ", "USER_SAID": "You said: "}.get(content.evidence, "")

    if content.turn == "CLARIFY":
        if not content.lacunae:
            raise Refusal("NO_FORM", "a CLARIFY must name the unfilled slot")
        if not content.omega:
            raise Refusal("NO_FORM", "a CLARIFY must name its target Omega")
        return prefix + "I need %s for %s. What is it?" % (content.lacunae[0], content.omega)
    if content.turn == "REFUSE_CLAIM":
        if not content.reason:
            raise Refusal("NO_FORM", "a REFUSE_CLAIM must give its reason words")
        return prefix + "I cannot support that: %s." % content.reason

    parts = []
    for relation in content.relations:
        parts.append(_relation_text(relation))
    if content.omega is not None and content.recipe is None:
        head = "New subject: %s." % content.omega if content.turn == "ACK" else "Topic: %s." % content.omega
        parts.append(head)
    if content.fractal:
        parts.append(_render_fractal(content.fractal, chosen))
    if content.recipe is not None:
        parts.append(_render_recipe(content.recipe, chosen))
    if content.terms:
        order = [index for index in chosen.order if index < len(content.terms)]
        order += [index for index in range(len(content.terms)) if index not in order]
        for index in order:
            parts.append(render_term(content.terms[index], chosen, index, content))
    if not parts:
        raise Refusal("NO_FORM", "this content has no CCE sentence")
    return prefix + " ".join(parts)


def render_report(content: CASContent, wording=None) -> dict:
    """Render and report either the sentence or the typed refusal word. Never raises."""
    try:
        sentence = render(content, wording)
    except Refusal as exc:
        return {"status": "NO_FORM", "code": exc.code, "detail": exc.detail, "sentence": None}
    return {"status": "RENDERED", "code": None, "detail": "", "sentence": sentence}
