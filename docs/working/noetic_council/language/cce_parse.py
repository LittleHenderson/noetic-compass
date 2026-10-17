"""cce_parse.py -- CCE v0.1 text -> CASContent. Deterministic: exactly one parse or a typed refusal.

The parsing rules are the spec's own (TRANSLATOR_SPEC.md section 3), in this order:

  1. VERB FRAME FIRST, LONGEST MATCH. The frame is found before any noun is read, and the
     longest frame wins. (This removes the bridge v2 failure where "breaking down an idea" was
     read as ^0 because the word "idea" matched first.)
  2. EXACTLY ONE PARSE OR NONE. If two frames match at equal length and yield different
     content, the sentence is AMBIGUOUS and is refused. It is never picked.
  3. SLOT TYPE CHECK. ^5 needs a Mind subject, ^6 an Idea subject, ^8 two DIFFERENT Ideas.
     A failed check is a typed refusal, never a re-guess.
  4. NO NUMBER INVENTION. A slot with no number stays empty; it is never 1.
  5. TYPED REJECTION CODES: NOT_CCE, AMBIGUOUS, SLOT_TYPE, SAME_IDEA_TRIGGER,
     UNDECLARED_NAME, HEDGE, VAGUE_QUANTITY, NEST_TOO_DEEP, OPERATOR_DISCIPLINE, plus the
     number layer's own codes.

Nothing here is learned: there are 0 learned parameters, and no rule is fit to any data.
"""

from __future__ import annotations

import re

import lexicon as LX
from content import (CASContent, Leakage, MAX_NEST_DEPTH, N, Recipe, RecipeTerm, Refusal, State, Term)

FIXED_UNDETERMINED = LX.FIXED_UNDETERMINED

# --- shape of names and numbers --------------------------------------------------------------------------------
NAME = r"[A-Z][A-Za-z0-9_]*"
OMEGA = r"Ω_[A-Za-z0-9_]+"
QUOTED = r'"[^"]+"'
PLACEHOLDER = r"⟦[0-9]+⟧"
IDEA = r"(?:%s|%s|%s)" % (QUOTED, OMEGA, PLACEHOLDER)
MIND_SUBJECT = r"(?:I|you|%s)" % NAME
MIND_OBJECT = r"(?:me|I|you|%s)" % NAME
WHO_IS = r"(?:I am|you are|%s is)" % NAME
NUM = (r"(?:(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:/[1-9][0-9]*)?|one|two|three|four|five|six|seven|eight|"
       r"nine|ten|half)")
UNIT = "(?:%s)" % "|".join(LX.UNITS)
PATTERN = "(?:%s)" % "|".join(LX.PATTERNS)
NOETIC_REF = "(?:%s)" % "|".join(sorted([re.escape(name) for name in LX.NAME_OF_NOETIC]
                                        + [re.escape(ref) for ref in LX.DEF_REF_OF], key=len, reverse=True))

_TOKEN = re.compile(r"(\{[A-Z]\}|~\w+)")
_LOOSE_NAME = r"(?:me|I|you|%s|%s|%s)" % (NAME, QUOTED, OMEGA)


def _alternative(words) -> str:
    return "|".join(map(re.escape, sorted(words, key=len, reverse=True)))


def _compile_strict(template) -> re.Pattern:
    pieces = []
    first = True
    for piece in _TOKEN.split(template.text):
        if not piece:
            continue
        at_subject = first
        first = False
        if piece == "{M}":
            pieces.append("(?P<M>%s)" % (MIND_SUBJECT if at_subject else MIND_OBJECT))
        elif piece == "{W}":
            pieces.append("(?P<W>%s)" % WHO_IS)
        elif piece in ("{I}", "{J}"):
            pieces.append("(?P<%s>%s)" % (piece[1], IDEA))
        elif piece in ("{D}", "{R}"):
            pieces.append("(?P<%s>%s)" % (piece[1], NUM))
        elif piece == "{U}":
            pieces.append("(?P<U>%s)" % UNIT)
        elif piece == "{P}":
            pieces.append("(?P<P>%s)" % PATTERN)
        elif piece.startswith("~"):
            forms = LX.VERBS[piece[1:]]
            positives = _alternative({forms["3"], forms["I"], forms["you"]})
            negatives = _alternative({forms["neg3"], forms["negI"], forms["negyou"]})
            pieces.append("(?:(?P<neg>%s)|%s)" % (negatives, positives))
        else:
            pieces.append(re.escape(piece))
    return re.compile("^" + "".join(pieces) + "$")


def _compile_loose(template) -> re.Pattern:
    """The same frame with every name slot widened to any name.

    Used only to DIAGNOSE a refusal (is this sentence ambiguous, or just undeclared?), never to
    accept one. The two tables are built from the same frozen templates, so the loose table
    cannot say anything the strict table cannot.
    """
    pieces = []
    for piece in [p for p in _TOKEN.split(template.text) if p]:
        if piece in ("{M}", "{I}", "{J}"):
            pieces.append("(?:%s)" % _LOOSE_NAME)
        elif piece == "{W}":
            pieces.append(r"(?:I am|you are|\S+ is)")
        elif piece in ("{D}", "{R}"):
            pieces.append("(?:%s)" % NUM)
        elif piece == "{U}":
            pieces.append(UNIT)
        elif piece == "{P}":
            pieces.append(PATTERN)
        elif piece.startswith("~"):
            forms = LX.VERBS[piece[1:]]
            pieces.append("(?:%s)" % _alternative(set(forms.values())))
        else:
            pieces.append(re.escape(piece))
    return re.compile("^" + "".join(pieces) + "$")


STRICT = [(template, _compile_strict(template)) for template in LX.TEMPLATES]
LOOSE = [(template, _compile_loose(template)) for template in LX.TEMPLATES]

# --- guards that never depend on a frame -----------------------------------------------------------------------
HEDGE_RX = re.compile(r"\b(might|maybe|perhaps|possibly|could|if|unless)\b", re.I)
VAGUE_RX = re.compile(r"\b(a lot of|some|a bit of|many|few|several|much)\b", re.I)
# "because", "therefore" and bare "cause"/"effect" never name a Noetic (MAP.md trap table);
# "side effect" was misread as ^9 on bridge v2 row 00353.
BANNED_RX = re.compile(r"\b(because|therefore|cause|causes|effect|effects|so)\b", re.I)
PRONOUN_RX = re.compile(r"\b(he|she|him|her|hers|his|they|them|their|theirs|it|its)\b", re.I)


class _Context:
    """Declared names seen in the text. Nothing else is carried between sentences."""

    __slots__ = ("minds", "ideas")

    def __init__(self, minds=("I", "you"), ideas=()):
        self.minds = set(minds) | {"I", "you"}
        self.ideas = set(ideas)


def _protect(text: str):
    """Swap the ten Noetic names for placeholders so a marker check cannot read a name as grammar.

    "Above/Cause" contains the word "cause", which is a banned marker. The protection is the
    same idea the sketch used for quoted names: a name is a name, not grammar.
    """
    for number, name in LX.NOETIC_NAMES.items():
        text = text.replace(name, "%sN%d%s" % (LX.PROTECTED_MARKER, number, LX.PROTECTED_MARKER))
    return text


def _unprotect(text: str) -> str:
    return re.sub(LX.PROTECTED_MARKER + r"N([0-9])" + LX.PROTECTED_MARKER,
                  lambda m: LX.NOETIC_NAMES[int(m.group(1))], text)


def _global_checks(sentence: str) -> None:
    """The guards that run before any frame is looked for. Each has its own typed code."""
    unquoted = re.sub(r'"[^"]*"', '""', _protect(sentence))
    if HEDGE_RX.search(unquoted):
        raise Refusal("HEDGE", sentence)
    if VAGUE_RX.search(unquoted):
        raise Refusal("VAGUE_QUANTITY", sentence)
    if BANNED_RX.search(unquoted):
        raise Refusal("NOT_CCE", "a banned marker word (never a Noetic): " + sentence)
    if PRONOUN_RX.search(unquoted):
        raise Refusal("NOT_CCE", "third-person pronouns are not CCE; use a declared name: " + sentence)


def _split_outside(text: str, separator: str):
    """Split on a literal separator that is outside quotes, brackets, braces and parentheses."""
    parts, buffer, depth, quoted, index = [], [], 0, False, 0
    while index < len(text):
        char = text[index]
        if char == '"':
            quoted = not quoted
        elif not quoted and char in "[{(":
            depth += 1
        elif not quoted and char in "]})":
            depth -= 1
        if not quoted and depth == 0 and text.startswith(separator, index):
            parts.append("".join(buffer))
            buffer = []
            index += len(separator)
            continue
        buffer.append(char)
        index += 1
    parts.append("".join(buffer))
    return parts


def _split_sentences(text: str, strict: bool = True):
    """Split a text into sentences, each keeping its final period.

    The separator ". " swallows the period, so it is put back on every piece but the last. The
    last piece must carry its own final period in a CCE text (GRAMMAR_CCE_v0_1.md section 8).
    """
    text = text.strip()
    pieces = [piece.strip() for piece in _split_outside(text, ". ")]
    nonempty = [index for index, piece in enumerate(pieces) if piece]
    last = nonempty[-1] if nonempty else -1
    out = []
    for index, piece in enumerate(pieces):
        if not piece:
            continue
        if index != last:
            out.append(piece + ".")
        elif piece.endswith("."):
            out.append(piece)
        elif strict:
            raise Refusal("NOT_CCE", "a CCE sentence ends with a period: " + piece)
        else:
            out.append(piece + ".")
    return out


def _protect_nesting(text: str):
    """Replace every `that [ ... ]` group with a placeholder and keep the inner text."""
    inner = []
    out = []
    index = 0
    while index < len(text):
        if text.startswith("that [", index):
            depth, cursor = 0, index + len("that ")
            while cursor < len(text):
                if text[cursor] == "[":
                    depth += 1
                elif text[cursor] == "]":
                    depth -= 1
                    if depth == 0:
                        break
                cursor += 1
            if cursor >= len(text):
                raise Refusal("NOT_CCE", "unclosed nesting bracket: " + text)
            inner.append(text[index + len("that ["):cursor])
            out.append("⟦%d⟧" % (len(inner) - 1))
            index = cursor + 1
            continue
        out.append(text[index])
        index += 1
    return "".join(out), inner


def _parse_number_text(text: str):
    try:
        return N.parse_number(text)
    except N.NumberRefusal as exc:
        raise Refusal(exc.code, exc.detail) from None


# --- the tail: domain, register, drive -------------------------------------------------------------------------
# The tail is peeled from the RIGHT END of the sentence with anchored patterns, never by splitting
# on commas: a register set is written "in analytical, affective and transcendent registers", which
# contains commas, so a comma split would tear it apart.
_REGISTER_SET_BODY = r"[a-z]+(?:, [a-z]+)* and [a-z]+"
_PEEL_PATTERNS = (
    ("drive", re.compile(r"^(?P<head>.*), for (?P<value>%s)$" % _alternative(LX.DRIVES.values()))),
    ("register", re.compile(r"^(?P<head>.*), in (?P<value>%s) registers$" % _REGISTER_SET_BODY)),
    ("register", re.compile(r"^(?P<head>.*), (?P<value>%s) register$" % _alternative(LX.REGISTERS.values()))),
    ("domain", re.compile(r"^(?P<head>.*), (?P<value>%s)$" % _alternative(LX.DOMAINS.values()))),
)


def _peel_one(text: str):
    """Remove one tail phrase from the right end, or return None."""
    for kind, pattern in _PEEL_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue
        value = match.group("value").strip()
        if kind == "drive":
            return match.group("head"), "drive", LX.DRIVE_OF_WORD[value]
        if kind == "domain":
            return match.group("head"), "domain", LX.DOMAIN_OF_WORD[value]
        words = [word.strip() for word in re.split(r",| and ", value) if word.strip()]
        letters = []
        for word in words:
            if word not in LX.REGISTER_OF_WORD:
                letters = None
                break
            letters.append(LX.REGISTER_OF_WORD[word])
        if not letters:
            continue
        if len(set(letters)) < 2 and ("," in value or " and " in value):
            raise Refusal("NOT_CCE", "a register set names two or more registers: " + value)
        return match.group("head"), "register", tuple(letters)
    return None


def _split_tail(core: str):
    """Yield (bare sentence, tail dict) from zero peeled segments outwards.

    # UNDECIDED IN SPEC: does a comma segment beside an in-frame slot ("pattern cognitive") belong to the frame or to the tail?
    # TRANSLATOR_SPEC does not say. This build tries the longest frame first and peels a tail phrase
    # only when the longer core matches no frame at all.
    """
    yield core, {}
    current, tail = core, {}
    for _ in range(len(("domain", "register", "drive"))):
        peeled = _peel_one(current)
        if peeled is None:
            return
        current, kind, value = peeled
        if kind in tail:
            return
        tail = dict(tail)
        tail[kind] = value
        yield current, tail


# --- frame matching --------------------------------------------------------------------------------------------
def _hit_report(template, match, ctx: _Context):
    """Read one matched frame under the slot type check. Returns (term_kwargs, problem)."""
    groups = match.groupdict()
    slots = {}
    problem = None
    for group, value in groups.items():
        if group == "neg" or value is None:
            continue
        if group == "W":
            mind = value[:-3].strip() if value.endswith(" is") or value.endswith(" am") or value.endswith(" are") else value
            slots["M"] = mind
            problem = problem or _check_mind(mind, ctx)
        elif group == "M":
            slots["M"] = "I" if value == "me" else value
            problem = problem or _check_mind(slots["M"], ctx)
        elif group in ("I", "J"):
            slots[group] = value
        elif group in ("D", "R"):
            slots[group] = N.fraction_text(_parse_number_text(value))
        else:
            slots[group] = value
    if template.act:
        slots["ACT"] = template.act

    if template.noetic == 8 and slots.get("I") is not None and slots.get("I") == slots.get("J"):
        return None, "different_ideas"
    if template.noetic == 6 and slots.get("I") is not None and slots.get("I") == slots.get("J"):
        return None, "another_idea"
    if template.noetic == 9 and slots.get("I") is not None and slots.get("I") == slots.get("J"):
        return None, "different_ideas"
    if problem is not None:
        return None, problem
    return {"noetic": template.noetic,
            "slots": {name: value for name, value in slots.items()},
            "polarity": "DENIED" if groups.get("neg") else "ASSERTED",
            "act_template": template}, None


def _check_mind(value: str, ctx: _Context):
    if value in ("I", "me"):
        return None
    if value == "you":
        return None
    if value in ctx.minds:
        return None
    if value in ctx.ideas:
        return "slot_type"
    return "undeclared"


_PROBLEM_CODE = {"different_ideas": "SAME_IDEA_TRIGGER", "another_idea": "SLOT_TYPE",
                 "slot_type": "SLOT_TYPE", "undeclared": "UNDECLARED_NAME"}


def _finish_term(kwargs, tail, depth: int) -> Term:
    slots = {}
    for name, value in kwargs["slots"].items():
        match = re.fullmatch(PLACEHOLDER, value) if isinstance(value, str) else None
        if match:
            index = int(value[1:-1])
            inner_text = kwargs.get("inner", ())
            if index >= len(inner_text):
                raise Refusal("NOT_CCE", "dangling nesting placeholder")
            if depth + 1 > MAX_NEST_DEPTH:
                raise Refusal("NEST_TOO_DEEP", "nesting deeper than %d" % MAX_NEST_DEPTH)
            slots[name] = _parse_single_frame(inner_text[index], kwargs["ctx"], depth + 1)
        else:
            slots[name] = value
    try:
        return Term(noetic=kwargs["noetic"], slots=slots, polarity=kwargs["polarity"],
                    domain=tail.get("domain"), register=tail.get("register"), drive=tail.get("drive"))
    except ValueError as exc:
        message = str(exc)
        if "NEST" in message:
            raise Refusal("NEST_TOO_DEEP", message) from None
        raise Refusal("NOT_CCE", message) from None


def _parse_single_frame(text: str, ctx: _Context, depth: int = 0) -> CASContent:
    """Parse one frame (the text inside a `that [...]` slot) into a one-term content."""
    statement = text.strip()
    if not statement.endswith("."):
        statement = statement + "."
    return CASContent(terms=(_parse_frame_with_inner(statement, ctx, depth),))


def _parse_frame_with_inner(sentence: str, ctx: _Context, depth: int = 0) -> Term:
    body = sentence[:-1].strip()
    _global_checks(body)
    protected, inner_text = _protect_nesting(body)
    for bare, tail in _split_tail(protected):
        strict_hits = []
        for template, pattern in STRICT:
            match = pattern.match(bare)
            if match:
                strict_hits.append((template, match))
        if not strict_hits:
            continue
        longest = max(template.length for template, _ in strict_hits)
        top = [(template, match) for template, match in strict_hits if template.length == longest]
        good, problems = [], []
        for template, match in top:
            kwargs, problem = _hit_report(template, match, ctx)
            if kwargs is not None:
                kwargs["inner"] = inner_text
                kwargs["ctx"] = ctx
                good.append((template, kwargs))
            else:
                problems.append(problem)
        if good:
            distinct = {}
            for template, kwargs in good:
                term = _finish_term(kwargs, tail, depth)
                distinct.setdefault(term.key(), (template, term))
            if len(distinct) > 1:
                raise Refusal("AMBIGUOUS", "two frames of equal length with different content: " + bare)
            return next(iter(distinct.values()))[1]
        loose_top = [(template, pattern) for template, pattern in LOOSE if pattern.match(bare)]
        if problems and all(problem == "undeclared" for problem in problems) and loose_top:
            loose_longest = max(template.length for template, _ in loose_top)
            loose_top = [(t, p) for t, p in loose_top if t.length == loose_longest]
            if len({template.noetic for template, _ in loose_top}) >= 2:
                raise Refusal("AMBIGUOUS",
                              "the name could be a Mind or an Idea and the frames read two ways: " + bare)
        for problem in problems:
            if problem in ("different_ideas", "another_idea", "slot_type"):
                raise Refusal(_PROBLEM_CODE[problem], bare)
        if "undeclared" in problems:
            raise Refusal("UNDECLARED_NAME", bare)
        raise Refusal("NOT_CCE", bare)
    raise Refusal("NOT_CCE", "no frozen frame matches: " + sentence)


# --- state phrases (recipes) ------------------------------------------------------------------------------------
def _parse_noetic_ref(text: str) -> int:
    text = text.strip()
    if text in LX.NAME_OF_NOETIC:
        return LX.NAME_OF_NOETIC[text]
    if text in LX.DEF_REF_OF:
        return LX.DEF_REF_OF[text]
    raise Refusal("NOT_CCE", "unknown Noetic reference: " + text)


def _parse_state_phrase(text: str) -> State:
    """`<Noetic name or [definition]>[, <domain>][, <register>][, for <Drive>]`, tail in any order."""
    for core, tail in _split_tail(text.strip()):
        head = core.strip()
        if head in LX.NAME_OF_NOETIC or head in LX.DEF_REF_OF:
            try:
                return State(_parse_noetic_ref(head), domain=tail.get("domain"),
                             register=tail.get("register"), drive=tail.get("drive"))
            except ValueError as exc:
                raise Refusal("NOT_CCE", str(exc)) from None
    raise Refusal("NOT_CCE", "unknown Noetic reference: " + text)


_TERM_STATE = re.compile(r"^(%s) of (.+)$" % NUM)
_TERM_OUTCOME = re.compile(r"^(%s) of (%s)$" % (NUM, OMEGA))
_TERM_EMERGENT = re.compile(r"^(%s) of \((.+?) combined with (.+?) into (%s)\)$" % (NUM, OMEGA))


def _parse_recipe_term(text: str) -> RecipeTerm:
    if "combined with" in text and " into " not in text:
        raise Refusal("OPERATOR_DISCIPLINE", "combined with no named result: " + text)
    match = _TERM_EMERGENT.match(text)
    if match:
        components = [_parse_state_phrase(match.group(2)), _parse_state_phrase(match.group(3))]
        return RecipeTerm(_parse_number_text(match.group(1)), kind="emergent",
                          components=components, result=match.group(4))
    match = _TERM_OUTCOME.match(text)
    if match:
        return RecipeTerm(_parse_number_text(match.group(1)), kind="outcome", name=match.group(2))
    match = _TERM_STATE.match(text)
    if match:
        return RecipeTerm(_parse_number_text(match.group(1)), kind="state",
                          state=_parse_state_phrase(match.group(2)))
    if "combined with" in text:
        raise Refusal("NOT_CCE", "recipe term: " + text)
    raise Refusal("NOT_CCE", "recipe term: " + text)


_RECIPE_RX = re.compile(r"^To make (%s), use (.+)$" % OMEGA)
_SIDE_RX = re.compile(r"^Side product: (%s) of (%s)$" % (NUM, OMEGA))
_SIDE_IMPLICIT_RX = re.compile(r"^Side product: (%s)$" % OMEGA)
_HELPED_RX = re.compile(r"^Helped by (%s)$" % OMEGA)
_SLOWED_RX = re.compile(r"^Slowed by (%s)$" % OMEGA)


def _parse_recipe(sentence: str, recipe_box: dict) -> None:
    body = sentence[:-1].strip() if sentence.endswith(".") else sentence.strip()
    match = _RECIPE_RX.match(body)
    if not match:
        raise Refusal("NOT_CCE", "recipe form: " + sentence)
    if recipe_box.get("recipe") is not None:
        raise Refusal("NOT_CCE", "one recipe per text")
    terms = [_parse_recipe_term(piece) for piece in _split_outside(match.group(2), "; plus ")]
    recipe_box["recipe"] = Recipe(omega=match.group(1), terms=terms)


# --- declarations, facts, statements ---------------------------------------------------------------------------
_DECL_MIND = re.compile(r"^(%s) is a Mind$" % NAME)
_DECL_IDEA = re.compile(r"^(%s) is an Idea$" % NAME)
_ONE_OF = re.compile(r"^(%s) is one of \{(.+)\}$" % IDEA)
_FACT = re.compile(r"^Fact: (%s) leads to (%s)$" % (IDEA, IDEA))
_NEEDS = re.compile(r"^(%s) needs (%s) first$" % (OMEGA, OMEGA))
_ABSENT = re.compile(r"^There is no (%s)$" % OMEGA)
_STOCK = re.compile(r"^There is (%s) of (%s|%s)$" % (NUM, OMEGA, NOETIC_REF))
_TOPIC = re.compile(r"^Topic: (%s)$" % OMEGA)
_NEW_SUBJECT = re.compile(r"^New subject: (%s)$" % OMEGA)
_CLARIFY = re.compile(r"^I need (.+?) for (%s)\. What is it\?$" % OMEGA)
_REFUSE = re.compile(r"^I cannot support that: (.+)\.$")
_FRACTAL = re.compile(r"^The fractal sequence is (?P<body>.+)$")
_NESTING = re.compile(r"^The nesting is (?P<body>.+)$")


def _scan_declarations(text: str, ctx: _Context) -> None:
    """Collect declared Minds and Ideas first, so order inside one text does not matter."""
    for sentence in _split_sentences(text, strict=False):
        body = _unprotect(sentence[:-1].strip() if sentence.endswith(".") else sentence.strip())
        body = body.replace("I checked: ", "").replace("You said: ", "")
        match = _DECL_MIND.match(body)
        if match:
            ctx.minds.add(match.group(1))
        match = _DECL_IDEA.match(body)
        if match:
            ctx.ideas.add(match.group(1))


def _parse_relation_pair(text: str):
    match = _FACT.match(text)
    if match:
        return ("leads_to", match.group(1), match.group(2))
    match = _NEEDS.match(text)
    if match:
        return ("needs_first", match.group(1), match.group(2))
    match = _ABSENT.match(text)
    if match:
        return ("absent", match.group(1))
    match = _STOCK.match(text)
    if match:
        return ("stock", N.fraction_text(_parse_number_text(match.group(1))), match.group(2))
    match = _DECL_MIND.match(text)
    if match:
        return ("is_a", match.group(1), "Mind")
    match = _DECL_IDEA.match(text)
    if match:
        return ("is_a", match.group(1), "Idea")
    match = _ONE_OF.match(text)
    if match:
        members = tuple(sorted(item.strip() for item in re.split(r",\s*", match.group(2)) if item.strip()))
        return ("one_of", match.group(1), members)
    return None


def _parse_fractal(body: str):
    terms = []
    pieces = _split_outside(body, " : ")
    if len(pieces) < 2:
        pieces = _split_outside(body, " inside ")
        if len(pieces) < 2:
            raise Refusal("NOT_CCE", "a fractal sequence names two or more Noetics")
    for piece in pieces:
        state = _parse_state_phrase(piece)
        terms.append(state)
    if len(terms) > 5:
        raise Refusal("NEST_TOO_DEEP", "a fractal sequence of %d levels (cap 5)" % len(terms))
    return tuple(terms)


# --- the entry point -------------------------------------------------------------------------------------------
def parse(text: str, minds=("I", "you"), ideas=()) -> CASContent:
    """Parse one CCE text into one CASContent record, or raise Refusal(code).

    # UNDECIDED IN SPEC: are the REFUSE_CLAIM reason words content, when the section 2 field table does not list them?
    # This build stores them in content.reason, because otherwise "I cannot support that: no
    # evidence." and "I cannot support that: the budget was never supplied." would be one content.
    # UNDECIDED IN SPEC: may a nested frame inside "that [...]" carry its own evidence and turn words?
    # This build says no: a nested frame is one plain frame (evidence NONE, turn ANSWER), and
    # anything else in a slot is NEST_IN_SLOT_UNSAYABLE.
    """
    if not isinstance(text, str) or not text.strip():
        raise Refusal("NOT_CCE", "empty")
    statement = text.strip()
    ctx = _Context(minds=minds, ideas=ideas)
    _scan_declarations(statement, ctx)

    evidence = "NONE"
    for prefix, word in (("I checked: ", "CHECKED"), ("You said: ", "USER_SAID")):
        if statement.startswith(prefix):
            statement = statement[len(prefix):].strip()
            evidence = word
            break

    if statement == FIXED_UNDETERMINED:
        return CASContent(gate="UNDETERMINED")

    match = _CLARIFY.match(statement)
    if match:
        return CASContent(turn="CLARIFY", omega=match.group(2), lacunae=(match.group(1).strip(),),
                          evidence=evidence)

    match = _REFUSE.match(statement)
    if match:
        return CASContent(turn="REFUSE_CLAIM", reason=match.group(1).strip(), evidence=evidence)

    if statement.startswith("To make "):
        return _parse_recipe_text(statement, evidence, ctx)

    match = _FRACTAL.match(statement[:-1] if statement.endswith(".") else statement)
    if match:
        return CASContent(fractal=_parse_fractal(match.group("body")), evidence=evidence)
    match = _NESTING.match(statement[:-1] if statement.endswith(".") else statement)
    if match:
        return CASContent(fractal=_parse_fractal(match.group("body")), evidence=evidence)

    terms, relations = [], []
    omega = None
    turn = "ANSWER"
    recipe_box = {"recipe": None}
    for sentence in _split_sentences(statement):
        if not sentence.endswith("."):
            raise Refusal("NOT_CCE", "a CCE sentence ends with a period: " + sentence)
        body = sentence[:-1].strip()
        _global_checks(body)
        if body.startswith("To make "):
            _parse_recipe(body, recipe_box)
            continue
        if recipe_box["recipe"] is not None:
            match = _SIDE_RX.match(body)
            if match:
                recipe = recipe_box["recipe"]
                recipe_box["recipe"] = Recipe(
                    omega=recipe.omega, terms=recipe.terms,
                    leakage=recipe.leakage + (Leakage(_parse_number_text(match.group(1)), match.group(2)),),
                    catalysts=recipe.catalysts, inhibitors=recipe.inhibitors)
                continue
            match = _SIDE_IMPLICIT_RX.match(body)
            if match:
                recipe = recipe_box["recipe"]
                recipe_box["recipe"] = Recipe(
                    omega=recipe.omega, terms=recipe.terms,
                    leakage=recipe.leakage + (Leakage(None, match.group(1), implicit=True),),
                    catalysts=recipe.catalysts, inhibitors=recipe.inhibitors)
                continue
            match = _HELPED_RX.match(body)
            if match:
                recipe = recipe_box["recipe"]
                recipe_box["recipe"] = Recipe(
                    omega=recipe.omega, terms=recipe.terms, leakage=recipe.leakage,
                    catalysts=recipe.catalysts + (match.group(1),), inhibitors=recipe.inhibitors)
                continue
            match = _SLOWED_RX.match(body)
            if match:
                recipe = recipe_box["recipe"]
                recipe_box["recipe"] = Recipe(
                    omega=recipe.omega, terms=recipe.terms, leakage=recipe.leakage,
                    catalysts=recipe.catalysts, inhibitors=recipe.inhibitors + (match.group(1),))
                continue
        relation = _parse_relation_pair(body)
        if relation is not None:
            relations.append(relation)
            continue
        match = _TOPIC.match(body)
        if match:
            omega = match.group(1)
            continue
        match = _NEW_SUBJECT.match(body)
        if match:
            omega = match.group(1)
            turn = "ACK"
            continue
        terms.append(_parse_term_from_sentence(sentence, ctx))

    return CASContent(turn=turn, omega=omega, terms=terms, recipe=recipe_box["recipe"],
                      relations=relations, evidence=evidence)


def _parse_term_from_sentence(sentence: str, ctx: _Context) -> Term:
    return _parse_frame_with_inner(sentence, ctx, 0)


def _parse_recipe_text(statement: str, evidence: str, ctx: _Context) -> CASContent:
    recipe_box = {"recipe": None}
    sentences = _split_sentences(statement)
    if not sentences or not sentences[0].startswith("To make "):
        raise Refusal("NOT_CCE", "recipe form")
    _parse_recipe(sentences[0], recipe_box)
    for sentence in sentences[1:]:
        if not sentence.endswith("."):
            raise Refusal("NOT_CCE", "a CCE sentence ends with a period: " + sentence)
        body = sentence[:-1].strip()
        _global_checks(body)
        recipe = recipe_box["recipe"]
        match = _SIDE_RX.match(body)
        if match:
            recipe_box["recipe"] = Recipe(recipe.omega, recipe.terms,
                                          recipe.leakage + (Leakage(_parse_number_text(match.group(1)),
                                                                    match.group(2)),),
                                          recipe.catalysts, recipe.inhibitors)
            continue
        match = _SIDE_IMPLICIT_RX.match(body)
        if match:
            recipe_box["recipe"] = Recipe(recipe.omega, recipe.terms,
                                          recipe.leakage + (Leakage(None, match.group(1), implicit=True),),
                                          recipe.catalysts, recipe.inhibitors)
            continue
        match = _HELPED_RX.match(body)
        if match:
            recipe_box["recipe"] = Recipe(recipe.omega, recipe.terms, recipe.leakage,
                                          recipe.catalysts + (match.group(1),), recipe.inhibitors)
            continue
        match = _SLOWED_RX.match(body)
        if match:
            recipe_box["recipe"] = Recipe(recipe.omega, recipe.terms, recipe.leakage,
                                          recipe.catalysts, recipe.inhibitors + (match.group(1),))
            continue
        raise Refusal("NOT_CCE", "not part of a recipe: " + sentence)
    return CASContent(recipe=recipe_box["recipe"], evidence=evidence)


def parse_report(text: str, **kwargs) -> dict:
    """Parse and report either the content or the typed refusal word. Never raises."""
    try:
        content = parse(text, **kwargs)
    except Refusal as exc:
        return {"status": "UNPARSEABLE", "code": exc.code, "detail": exc.detail,
                "sentence": text, "content": None}
    except N.NumberRefusal as exc:
        return {"status": "UNPARSEABLE", "code": exc.code, "detail": exc.detail,
                "sentence": text, "content": None}
    return {"status": "PARSED", "code": None, "detail": "", "sentence": text, "content": content}
