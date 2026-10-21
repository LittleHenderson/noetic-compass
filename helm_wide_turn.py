"""helm_wide_turn.py -- the reader, the voice and the live-loop turn for RB-W1, the WIDE recipe brain: HELM's canonical
brain since the owner's ruling of 2026-10-20 ("YES TO WIDE BRAIN", SPEC 7.56).

Used when the WIDE_BRAIN switch is ON, which is the default since 2026-10-20 (helm_brain_wide.wide_brain_on;
HELM_WIDE_BRAIN set to 0 / OFF / FALSE / NO turns it off). With it OFF the live loop never imports this module, and
helm_english_in.py / helm_voice.py / the licensed reference brain behave exactly as before.

READER (deterministic, stdlib, no model). Three sentence shapes, all or nothing (one doubtful part -> one question,
nothing saved):
    "We made 1 gingerbread from 2 1/4 cups flour, sifted, 1/3 cup brown sugar and 2 eggs and ran out of flour."
                                                    -> a witnessed batch (the teaching channel)
    "We have 3 cups flour, 1 cup brown sugar and 12 eggs."                -> stock on hand
    "How much gingerbread can we make?" / "Can we make gingerbread?"      -> a question to the brain
Each ingredient line is  AMOUNT [UNIT[.]] [of] NAME [, note]. AMOUNT is exact (integers, decimals, 1/3, 1 1/2, 1-1/2,
unicode fractions, number words, "a"/"an", "two thirds", "one and a half"). A range ("2 or 3", "2-3"), "about 2",
or no amount at all is a question, never a guess. UNIT must be one of the 20 table units (helm_brain_wide.UNITS);
a known unit word outside the table ("stick", "dozen", "liter") is a question. NAME is open: any words the reader can
bind (lower case; leading size words such as "large" dropped; the last word made singular; OUR_CONVENTION). It is
never checked against a fixed list -- the brain decides whether it knows it.

VOICE. Plain everyday English, built only from the brain's record and the user's own units. Amounts are said exactly
("1 1/3", "1/3 cup", "2 1/4 cups"); nothing is rounded; no CAS notation.

TURN. The same stations as the licensed path: CCE skin (render -> parse round trip, Omega names built from the bound
names), S0 atlas head, S1 trigger, S2 Bias (stock), S3 arrival (absent / unlearned), S4 valve, S5 RPM gate, brain,
store (a cube write only after the gate and the brain's receipt passed, then read back), S6 next.

CLAIM STATUS: see helm_brain_wide: VALIDATED for the SPEC 7.89 / 7.96 sentences only (NAMED_CORPORA_ONLY + SYNTHETIC_ONLY).
This reader is v5 (relative amounts bundled with their line), the version scored in job c50 (SPEC 7.96).

STAGE 1c (2026-10-20, switch WIDE_UNITS_NOTE, default OFF; see helm_brain_wide's header): with the switch ON this same
reader also reads the 6 widened units (liter, deciliter, centiliter, gallon, fluid ounce, dozen) and reads a line with no
exact amount, or with a unit nobody can size, as a NOTE line {"name", "amount": None, "unit": "", "note": True}: present,
never a requirement. OFF, every line above is exactly v5. ENGINEERED-NOT-VALIDATED; no claim moved.
"""
from __future__ import annotations

import json
import re
import unicodedata
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

import helm_brain_wide as W

READER_VERSION = "helm_wide_turn reader RB-W1 v5 (2026-10-20)"
CLAIM_STATUS = W.CLAIM_STATUS

# ---------------------------------------------------------------------------------------------------- names
#: size/freshness words dropped from the FRONT of an ingredient name (same list as helm_english_in.ADJECTIVES_SKIPPED)
LEADING_DROPPED = {"fresh", "large", "big", "small", "whole", "plain", "cold", "warm", "soft", "raw", "fine", "coarse",
                   "regular", "extra-large", "medium", "the", "a", "an", "some", "of"}
#: words that make a comma segment a note on the line before it ("2 cups flour, sifted"), not a new ingredient
NOTE_WORDS = set("""sifted chopped melted softened beaten divided diced minced sliced packed grated shredded peeled cored
crushed ground halved quartered cubed drained rinsed toasted optional finely coarsely lightly freshly roughly thinly
well firmly room temperature at cut into pieces to taste or more less if needed as needed for garnish serving and
separated whisked cooled warmed scalded heaping level rounded
very fine thin thick coarse whole small large medium generous scant heaped piece cubes strips rings dice dices diced
seeded stoned pitted skinned boned cleaned washed trimmed shelled blanched mashed strained scraped soaked cooked boiled
picked stemmed hulled crumbled lengthwise crosswise inch inches the a of in smashed bruised pounded torn""".split())
SINGULAR_EXCEPTIONS = {"molasses": "molasses", "hummus": "hummus", "couscous": "couscous", "asparagus": "asparagus",
                       "swiss": "swiss", "loaves": "loaf", "leaves": "leaf", "halves": "half", "knives": "knife",
                       "cheeses": "cheese", "glasses": "glass", "grits": "grits", "oats": "oats", "greens": "greens",
                       # v3: -ie nouns ("cookies" was read as "cooky", "pies" as "py")
                       "cookies": "cookie", "pies": "pie", "brownies": "brownie", "smoothies": "smoothie",
                       "veggies": "veggie", "calories": "calorie"}
APPROX_RX = re.compile(r"^(?:about|around|roughly|approximately|approx\.?|nearly|almost|over|under|at least|up to)\b")
#: v4 (2026-10-20, wave-6 FIX FIRST): a piece of a stock or batch sentence that is a CLAUSE about the ingredients
#: ("..., but the butter is past its best", "and nobody needs sauce today", "but I'm saving the egg for something
#: else") is something this reader cannot hold: the faces (Purpose / Wisdom / Power) live in the triad, which wraps
#: only the licensed brain. All or nothing: the whole sentence becomes one question and nothing is saved. Before v4
#: such a clause was kept as a "note" of the line before it and silently ignored (23 wrong answers on wave 6's practice
#: conversations).
CLAUSE_RX = re.compile(
    r"^(?:but|except|although|though|however|yet|unless|whereas)\b"
    r"|^(?:i|i'm|i've|i'd|we're|we've|we don't|we do not|nobody|no one|there's|there is|my|our)\b"
    r"|^the\b[^,]*?\b(?:is|are|was|were|isn't|aren't|wasn't|has|hasn't|have|haven't)\b", re.IGNORECASE)
#: v6 (2026-10-20, wave-7 round 3 FIX FIRST): a piece of a batch or stock sentence that is an amount of a CONDITION,
#: not of an ingredient -- a temperature ("80 degrees Fahrenheit", "350 F"), a time ("20 minutes"), a head count
#: ("4 people"), a percentage -- is a note on the ingredient line before it ("2 cups water, 80 degrees Fahrenheit"),
#: never an ingredient line of its own. Before v6 the reader bound such a piece as an ingredient named by the condition
#: word ("degrees fahrenheit"), so the wide brain waited for a batch where that "ingredient" ran out, never got one,
#: and asked at the question with every real lesson learned (c52: 1 unexplained ask, K4 missed). Same family as
#: helm_english_in.IGNORED_COUNT_NOUNS; kept here as the wide reader's own table.
CONDITION_NOUNS = {"degree", "degrees", "deg", "fahrenheit", "celsius", "centigrade", "f", "c",
                   "minute", "minutes", "min", "mins", "hour", "hours", "hr", "hrs", "second", "seconds", "sec", "secs",
                   "day", "days", "week", "weeks", "overnight",
                   "people", "person", "persons", "guest", "guests", "serving", "servings", "portion", "portions",
                   "percent", "pct", "times", "time", "step", "steps"}
CONDITION_RX = re.compile(r"^\s*(?:°|º)?\s*([A-Za-z]+)\.?(?=\s|$)")


def condition_fragment(seg: str) -> bool:
    """v6: is this piece an amount of a condition (temperature, time, head count, percentage) rather than of an
    ingredient? True for "80 degrees Fahrenheit", "350 F", "20 minutes", "4 people"; False for "2 cups water",
    "3 eggs", "2 cups flour, sifted"."""
    s = seg.strip()
    try:
        got = W.match_amount(s, 0)
    except W.WideRefused:
        return False
    if got is None:
        return False
    rest = s[got[1]:]
    m = CONDITION_RX.match(rest)
    if not m:
        return bool(re.match(r"\s*(?:°|º)", rest))
    word = m.group(1).lower()
    if word in ("f", "c"):                         # "350 F" is a temperature; "2 c flour" is two cups of flour
        return not rest[m.end():].strip() or bool(re.match(r"\s*(?:°|º)", rest))
    return word in CONDITION_NOUNS


def singular(word: str) -> str:
    w = word.lower()
    if w in SINGULAR_EXCEPTIONS:
        return SINGULAR_EXCEPTIONS[w]
    if len(w) > 3 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("oes"):
        return w[:-2]
    if len(w) > 3 and re.search(r"(?:ch|sh|ss|x)es$", w):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not re.search(r"(?:ss|us|is)$", w):
        return w[:-1]
    return w


def plural(name: str) -> str:
    """Voice only: 'egg' -> 'eggs', 'tomato' -> 'tomatoes', 'berry' -> 'berries' (OUR_CONVENTION)."""
    words = name.split()
    w = words[-1]
    if re.search(r"[^aeiou]y$", w):
        w = w[:-1] + "ies"
    elif re.search(r"(?:s|x|z|ch|sh|o)$", w):
        w = w + "es"
    else:
        w = w + "s"
    return " ".join(words[:-1] + [w])


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def bind_name(phrase: str, *, drop_leading: bool = True) -> Optional[str]:
    """Bind a written name to the brain's name: lower case, notes cut, leading size words dropped, last word singular."""
    s = phrase.split("(")[0].split(",")[0]
    s = _ascii(s.lower()).replace("-", " ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    words = s.split()
    while drop_leading and words and words[0] in LEADING_DROPPED:
        words = words[1:]
    if not words:
        return None
    words[-1] = singular(words[-1])
    return " ".join(words)


def omega(name: str) -> str:
    """The checked-form token for a bound name: 'brown sugar' -> 'Ω_Brown_sugar' (reversible for bound names)."""
    token = "_".join(name.split())
    return "Ω_" + token[:1].upper() + token[1:]


# ---------------------------------------------------------------------------------------------------- reader
def _ask(code: str, **slots: Any) -> Dict[str, Any]:
    return {"code": code, "slots": {k: v for k, v in slots.items() if v is not None}}


#: v3: two amounts for ONE ingredient are asked about, never summed and never split into a made-up ingredient (v2 read
#: "1/2 cup plus 1 tablespoon water" as an ingredient named "cup"): "X plus 1 tablespoon ..." anywhere, and "2 large
#: or 4 small peppers" (a second amount right after the first). "250 g tahini or 200 g peanut butter" (an alternative
#: INGREDIENT later in the line) is not matched: the line keeps its first amount and its whole text as the name, as v2.
_AMT_START = r"(?:\d|[" + "".join(W.VULGAR) + r"])"
ALTERNATIVE_RX = re.compile(r"\bplus\s+" + _AMT_START + r"|^(?:[A-Za-z-]+\s+)?or\s+" + _AMT_START, re.IGNORECASE)

#: v5 (2026-10-20, from the K4 diagnosis of HELM-R1 wave 6 c48; tested on our own practice recipes): a RELATIVE amount
#: ("1 teaspoon cream tartar, and half as much soda", "twice as much butter", "as much salt", "the same amount of
#: sugar") is said relative to the line BEFORE it. v4 read "half" as an amount of 1/2 with no unit and bound a made-up
#: ingredient named "as much soda"; that ingredient never ran out in any batch, so the brain asked even when every real
#: line was learned. ("twice as much X" and "as much X" were instead dropped silently as notes.) v5 keeps the pair as
#: ONE bundled line, named "cream tartar and half as much soda", amount 1 teaspoon. This is exact, not a guess: the
#: bundle always holds its two parts in the stated proportion r, so a batch where either part ran out first teaches
#: max(a_Y, a_X / r) per unit (in Y's unit), and stock of the same bundle gives Y_stock / that, which is exactly the
#: smaller of the two parts' own limits. Stock or a batch that names the parts any other way (Y alone, X on its own
#: line, another proportion) is a different line, so the brain asks. A proportion outside the table below, a relative
#: amount with no line before it, "... as much X as Y", or two relative amounts on one line -> ONE question
#: (AMOUNT_RELATIVE), nothing saved.
RELATIVE_WORDS_RX = re.compile(r"\bas\s+(?:much|many)\b|\b(?:same|equal)\s+(?:amount|quantity|measure)\b",
                               re.IGNORECASE)
RELATIVE_RX = re.compile(r"^(?:(?P<times>.+?)\s+)?as\s+(?:much|many)\s+(?:of\s+)?(?:the\s+)?(?P<name>[a-z].*)$"
                         r"|^(?:the\s+same|an?\s+equal)\s+(?:amount|quantity|measure)\s+of\s+(?:the\s+)?"
                         r"(?P<name2>[a-z].*)$", re.IGNORECASE)
#: the proportions v5 reads, and the one way each is said inside a bundled name (OUR_CONVENTION)
RELATIVE_SAID = {Fraction(1): "as much", Fraction(1, 2): "half as much", Fraction(2): "twice as much",
                 Fraction(1, 3): "a third as much", Fraction(1, 4): "a quarter as much",
                 Fraction(2, 3): "two thirds as much", Fraction(3, 4): "three quarters as much",
                 Fraction(3, 2): "one and a half times as much"}
RELATIVE_SAID.update({Fraction(v): f"{w} times as much" for w, v in W.NUMBER_WORDS.items() if v >= 3})


def read_relative(piece: str) -> Optional[Tuple[Fraction, str]]:
    """v5: "half as much soda" -> (1/2, "soda"); "twice as much butter" -> (2, "butter"); "the same amount of sugar"
    -> (1, "sugar"). None when the piece is not one clean relative amount that RELATIVE_SAID can say exactly."""
    s = piece.strip().strip(".").strip()
    m = RELATIVE_RX.match(s)
    if not m:
        return None
    phrase = m.group("name") or m.group("name2")
    if re.search(r"\bas\b", phrase, re.IGNORECASE):           # "... as much butter as flour": names another line
        return None
    times = re.sub(r"\s*\btimes$", "", (m.group("times") or "").strip().lower()).strip()
    r: Optional[Fraction]
    if not times:
        r = Fraction(1)
    elif times in ("twice", "double"):
        r = Fraction(2)
    elif times == "thrice":
        r = Fraction(3)
    else:
        try:
            got = W.match_amount(times, 0)
        except W.WideRefused:
            return None
        r = got[0] if got is not None and got[1] == len(times) else None
    name = bind_name(phrase)
    if r is None or r not in RELATIVE_SAID or not name:
        return None
    return r, name


#: stage 1c (WIDE_UNITS_NOTE ON): tails that say "no exact amount" on a bare ingredient line ("pepper to taste",
#: "butter for frying", "sugar if desired"); the name is what stands before them
NOTE_TAIL_RX = re.compile(r"\s+(?:to taste|as needed|as required|as desired|if needed|if desired|if liked|if wanted|"
                          r"or more|or less|for\b|optional)\b.*$", re.IGNORECASE)
#: a bare line that is NOT an ingredient said to be present: an absence ("no water"), a heading ("For the sauce:"), a
#: connective left over from a split; these stay the NO_AMOUNT question reader v5 asks
NOT_A_NOTE_RX = re.compile(r"^(?:no|none|without|zero|for|to|and|or|with|plus|minus|less|the same)\b", re.IGNORECASE)


def note_name(text: str) -> Optional[str]:
    """Stage 1c: the ingredient a bare line names as PRESENT with no exact amount: "salt" -> "salt", "Pepper to taste"
    -> "pepper", "butter for frying" -> "butter"; None when the line is an absence, a heading, or only note words
    ("sifted"), so that the deterministic question of reader v5 stands."""
    s = text.strip().strip(".").strip()
    if not s or s.endswith(":") or NOT_A_NOTE_RX.match(s) or re.search(r"\d|[" + "".join(W.VULGAR) + "]", s):
        return None
    s = NOTE_TAIL_RX.sub("", s)
    words = s.split()
    while words and re.sub(r"[^a-z]", "", words[-1].lower()) in NOTE_WORDS:
        words.pop()
    if not words or _is_note(" ".join(words)):
        return None
    return bind_name(" ".join(words))


def _note_line(name: str, said: str, why: str) -> Dict[str, Any]:
    """Stage 1c: a NOTE line: present, no amount, no unit; `why` names the rule that made it one."""
    return {"name": name, "amount": None, "unit": "", "said": said, "note": True, "note_why": why}


def parse_line(line: str, notes: str = "") -> Dict[str, Any]:
    """One ingredient line -> {"name", "amount" (Fraction), "unit", "said"} or {"clarify": {...}}.
    v3: `notes` is the rest of the same line after a comma or "and" that does not start a new amount ("cold, cooked
    rice", "squash, steamed and strained"). The name comes from the line's own words; the notes are used only when
    those words alone bind to nothing ("1 cup cold, cooked rice" -> "cooked rice").
    Stage 1c (WIDE_UNITS_NOTE ON, default OFF): a line with no amount, or with an amount in a unit that has no exact size,
    comes back as a NOTE line {"name", "amount": None, "unit": "", "note": True} instead of a question; see
    helm_brain_wide's header. OFF: exactly reader v5."""
    s = line.strip().strip(".").strip()
    stage_1c = W.units_note_on()
    if RELATIVE_WORDS_RX.search(s):                # v5: a relative amount with no line before it to be relative to
        return {"clarify": _ask("AMOUNT_RELATIVE", words=s)}
    companion: Optional[Tuple[Fraction, str]] = None
    if RELATIVE_WORDS_RX.search(notes):            # v5: "1 teaspoon cream tartar, and half as much soda"
        pieces = [x for x in SEP_RX.split(notes) if x.strip()]
        rel = [x for x in pieces if RELATIVE_WORDS_RX.search(x)]
        companion = read_relative(rel[0]) if len(rel) == 1 else None
        if companion is None:
            return {"clarify": _ask("AMOUNT_RELATIVE", words=(rel[0] if rel else notes).strip().strip("."))}
        notes = ", ".join(x.strip() for x in pieces if x is not rel[0])
    if APPROX_RX.match(s):
        return {"clarify": _ask("AMOUNT_APPROXIMATE", words=s)}
    try:
        got = W.match_amount(s, 0)
    except W.WideRefused as exc:
        return {"clarify": _ask(exc.code, words=s)}
    if got is None:
        if stage_1c and companion is None:         # stage 1c: "salt", "pepper to taste" -> present, no amount
            nm = note_name(s)
            if nm:
                return _note_line(nm, s, "NO_AMOUNT")
        return {"clarify": _ask("NO_AMOUNT", item=bind_name(s), words=s)}
    amount, end = got
    if condition_fragment(s):                      # v6: "80 degrees Fahrenheit" alone names no ingredient
        return {"clarify": _ask("NO_NAME", words=s)}
    rest = s[end:].strip()
    unit = ""
    note_unit = ""                                 # stage 1c: a unit word with no exact size ("stick", "dash")
    q = re.match(r"(?:level|heaping|heaped|rounded|scant|good|generous|large|small)\s+(?=[A-Za-z])", rest, re.IGNORECASE)
    if q:                                          # "1 heaping teaspoon": a size word before a unit word
        m2 = re.match(r"([A-Za-z]+(?:-[A-Za-z]+)*)\.?(?=\s|$)", rest[q.end():])
        if m2 and W.unit_of(m2.group(1).replace("-", "")) is not None:
            rest = rest[q.end():]
    m: Optional[re.Match] = None
    if stage_1c:                                   # stage 1c: a two-word unit ("fluid ounce", "fl oz") first
        m2w = re.match(r"([A-Za-z]+)\.?\s+([A-Za-z]+)\.?(?=\s|$)", rest)
        u2 = W.unit_of_two_words(m2w.group(1), m2w.group(2)) if m2w else None
        if u2 is not None:
            unit, rest = u2, rest[m2w.end():].strip()
    if not unit:
        m = re.match(r"([A-Za-z]+(?:-[A-Za-z]+)*)\.?(?=\s|$)", rest)
    if m:
        word = m.group(1).replace("-", "")
        u = W.unit_of(word)
        if u is not None:
            unit, rest = u, rest[m.end():].strip()
        elif word.lower() in W.OTHER_UNIT_WORDS:
            if stage_1c and word.lower() in W.NOTE_UNIT_WORDS:
                note_unit, rest = word.lower(), rest[m.end():].strip()
            else:
                return {"clarify": _ask("UNIT_NOT_IN_TABLE", unit=word.lower(), words=s)}
    rest = re.sub(r"^of\s+", "", rest)
    if ALTERNATIVE_RX.search(rest) or re.match(r"plus\b", rest, re.IGNORECASE):
        return {"clarify": _ask("AMOUNT_HAS_TWO_PARTS", words=s)}
    note = notes.strip().strip(".").strip()
    alt = re.split(r"\s+or\s+", rest, maxsplit=1)
    if len(alt) == 2 and alt[0].strip() and not re.search(r"\d", alt[1]):
        # v6: "dry beans or whole peas" -> the ingredient is the first alternative (the K-R key's head rule); the
        # alternative stays a note of the line, never a made-up name
        rest = alt[0].strip()
        note = (note + ", or " + alt[1].strip()).strip(", ")
    if unit and not bind_name(rest) and m is not None and not bind_name(note):
        unit, rest = "", m.group(1)
    if note_unit and not bind_name(rest) and not bind_name(note):   # stage 1c: "2 sticks" alone: the word is the name
        note_unit, rest = "", note_unit if not rest.strip() else rest
    if re.search(r"\bto taste\b|\bas needed\b", rest) and not unit and amount is None:
        return {"clarify": _ask("NO_AMOUNT", words=s)}
    name = bind_name(rest)
    if not name and note:                          # v3: "1 cup cold, cooked rice" -> "cooked rice"
        name = bind_name((rest + " " + note).replace(",", " "))
    if not name and rest.strip():                  # v3: a line made only of a size word ("12 large, ripe tomatoes")
        name = bind_name(rest, drop_leading=False)
    if not name:
        return {"clarify": _ask("NO_NAME", words=s)}
    if stage_1c and companion is None:
        if note_unit:                              # "2 sticks butter", "1 dash salt": no exact size -> present, no amount
            return _note_line(name, s, "UNIT_NO_EXACT_SIZE:" + note_unit)
        if unit and unit in W.OWN_UNITS_AS_NOTES:  # EMPTY today: own-count units ("2 cans") stay exact counts
            return _note_line(name, s, "UNIT_NO_EXACT_SIZE:" + unit)
    said = s + (", " + note if note else "")
    if companion is not None:                      # v5: one bundled line; its proportion is part of its name
        r, other = companion
        if other == name:
            return {"clarify": _ask("AMOUNT_RELATIVE", words=s)}
        name = f"{name} and {RELATIVE_SAID[r]} {other}"
        said = f"{said}, {RELATIVE_SAID[r]} {other}"
    return {"name": name, "amount": amount, "unit": unit, "said": said}


def _is_note(segment: str) -> bool:
    words = re.findall(r"[a-z]+", segment.lower())
    return bool(words) and all(w in NOTE_WORDS for w in words)


#: where one ingredient line may end: ", " / ", and " / "; " / " and " / " & " (never inside "one and a half")
SEP_RX = re.compile(r",\s*(?:and\s+(?!an?\s+(?:half|third|quarter)\b))?|;\s*(?:and\s+)?"
                    r"|\s+and\s+(?!an?\s+(?:half|third|quarter)\b)|\s+&\s+")
#: "a little salt", "a few drops": not an exact amount; after a separator they stay a note of the line before
VAGUE_AFTER_A = {"little", "few", "bit", "touch", "couple", "lot", "dash", "sprinkle", "sprinkling", "squeeze",
                 "splash", "drizzle", "knob", "good", "handful", "suspicion", "grating", "dusting", "trifle"}


def starts_line(seg: str) -> bool:
    """v3: does this piece (after a separator) begin a NEW ingredient line? Only if it begins with an amount, a rough
    or range amount, or "no X" (the line reader then asks about those). Anything else ("cooked rice", "steamed and
    strained", "whites and yolks separately", "a little salt") is the rest of the line before it."""
    s = seg.strip()
    if RELATIVE_WORDS_RX.search(s):                # v5: "half as much soda" belongs to the line before it
        return False
    if condition_fragment(s):                      # v6: "80 degrees Fahrenheit" belongs to the line before it
        return False
    if re.match(r"no\s+[a-z]", s, re.IGNORECASE):
        return True
    m = APPROX_RX.match(s.lower())
    if m and re.match(r"\s*(?:\d|[" + "".join(W.VULGAR) + r"])", s[m.end():]):
        return True
    try:
        got = W.match_amount(s, 0)
    except W.WideRefused:
        return True
    if got is None:
        return False
    if s[:got[1]].strip().lower() in ("a", "an"):
        nxt = re.match(r"\s*([a-z]+)", s[got[1]:].lower())
        return bool(nxt) and nxt.group(1) not in VAGUE_AFTER_A
    return True


def split_lines(text: str) -> List[Tuple[str, str]]:
    """'a, b and c' -> [(line, notes)]: cut at a separator only where a new amount begins (v3; v2 cut at every comma
    and "and", so "1 cup squash, steamed and strained" became three lines and the whole batch was refused)."""
    pieces: List[Tuple[str, str]] = []
    pos, sep = 0, ""
    for m in SEP_RX.finditer(text):
        pieces.append((sep, text[pos:m.start()]))
        sep, pos = m.group(0), m.end()
    pieces.append((sep, text[pos:]))
    out: List[List[str]] = []
    leading = ""                                   # v6: a condition piece before the first line waits for that line
    for sep, seg in pieces:
        if not seg.strip():
            continue
        if not out and condition_fragment(seg):
            leading = (leading + ", " + seg.strip()) if leading else seg.strip()
            continue
        if not out or starts_line(seg):
            out.append([seg.strip(), leading])
            leading = ""
        else:
            out[-1][1] = (out[-1][1] + sep + seg.strip()) if out[-1][1] else seg.strip()
    if leading and not out:                        # only conditions, no ingredient: one line, so the reader asks
        out.append([leading, ""])
    return [(a, b) for a, b in out]


def parse_lines(text: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """A list of ingredient lines ('a, b and c'). Notes after a comma stay with their line. All or nothing."""
    lines: List[Dict[str, Any]] = []
    for m in SEP_RX.finditer(text):                                # v4: a clause after a separator -> one question
        piece = text[m.end():].strip()
        if CLAUSE_RX.match(piece):
            return [], _ask("UNREAD_CLAUSE", words=piece.split(",")[0].strip().rstrip("."))
    stage_1c = W.units_note_on()
    for seg, notes in split_lines(text):
        rec = parse_line(seg, notes)
        if "clarify" in rec:
            return [], rec["clarify"]
        lines.append(rec)
        if stage_1c and rec.get("note") and rec.get("note_why") == "NO_AMOUNT" and notes:
            # stage 1c: "salt and pepper to taste": bare names after a bare name are NOTE lines of their own
            for piece in SEP_RX.split(notes):
                nm = note_name(piece)
                if nm:
                    lines.append(_note_line(nm, piece.strip().strip(".").strip(), "NO_AMOUNT"))
    names = [x["name"] for x in lines]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        return [], _ask("SAME_INGREDIENT_TWICE", item=dup[0])
    if not lines:
        return [], _ask("NO_AMOUNT")
    return lines, None


def normalize_text(text: str) -> str:
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace("_", "")
    while True:                                   # remove (asides), innermost first; numbers inside are not amounts
        t2 = re.sub(r"\s*\([^()]*\)", "", t)
        if t2 == t:
            break
        t = t2
    t = re.sub(r"\s+", " ", t).strip()
    return GREETING_RX.sub("", t)


WITNESS_RX = re.compile(r"^(?:so\s+|ok(?:ay)?,?\s+)?(?:we|i)\s+(?:just\s+)?(?:made|baked|cooked|produced|whipped up)\s+"
                        r"(?P<rest>.+?)\s*[.!]?$", re.IGNORECASE)
END_RX = re.compile(r"^(?P<lines>.+?),?\s+and\s+(?:then\s+)?(?:(?:we|i)\s+)?(?:"
                    r"ran out of\s+(?P<out>.+)"
                    r"|(?P<none>nothing ran out|(?:we\s+|i\s+)?(?:did not|didn't) run out of anything|"
                    r"(?:we\s+|i\s+)?ran out of nothing))$", re.IGNORECASE)
#: v4: a restatement ("Actually, we have 4 pounds of sugar now.") is stock too, so the new amount replaces the old one:
#: the brain then converts it through its unit table or asks (UNIT_KIND_MISMATCH); it never answers from the old one
STOCK_RX = re.compile(r"^(?:(?:actually|now|ok(?:ay)?|so|sorry|correction|update)\s*,?\s+)?"
                      r"(?:we(?:'ve| have)? got|we (?:still |now )?have|there (?:is|are)|there's|our pantry has|"
                      r"in the pantry we have)\s+(?P<lines>.+?)(?:\s+(?:on hand|left|in stock|now|instead))?\s*[.!]?$",
                      re.IGNORECASE)
QUESTION_RX = re.compile(r"^(?:how\s+(?:much|many)\s+(?P<p1>.+?)\s+(?:can|could)\s+(?:we|i)\s+(?:make|bake|cook)"
                         r"(?:\s+now)?(?:\s+with what we have)?|(?:can|could)\s+(?:we|i)\s+(?:make|bake|cook)\s+"
                         r"(?:any\s+|some\s+)?(?P<p2>.+?)"
                         # v6 (wave-7 FIX FIRST): wave 3b's two other question forms, which the chat's gate otherwise
                         # answered as general knowledge
                         r"|(?:could|can|would)\s+you\s+tell\s+me\s+how\s+(?:much|many)\s+(?P<p3>.+?)\s+that\s+makes"
                         r"|how\s+(?:much|many)\s+(?P<p4>.+?)\s+do\s+(?:we|i)\s+have\s+the\s+makings\s+of"
                         r")\s*\??$", re.IGNORECASE)
#: v6: a greeting in front of a kitchen sentence ("Hi again. How much X can we make?") is not part of it
GREETING_RX = re.compile(r"^(?:hi|hello|hey|good (?:morning|afternoon|evening))(?:\s+(?:again|there))?[.,!]\s+", re.IGNORECASE)
#: v6: a stock sentence that ends "but we've run out of X" states an absence; the brain asks rather than guessing a name
ABSENT_TAIL_RX = re.compile(r"^(?P<lines>.+?),?\s+(?:but|and)\s+(?:we(?:'ve| have)|i(?:'ve| have))\s+run out of\s+(?P<absent>.+)$",
                            re.IGNORECASE)


def _words(text: str) -> List[str]:
    """Lower-case words of a text, each made singular (for matching a ran-out phrase inside a line)."""
    return [singular(w) for w in re.sub(r"[^a-z0-9]+", " ", _ascii(text.lower())).split()]


def _contains(hay: List[str], needle: List[str]) -> bool:
    k = len(needle)
    return k > 0 and any(hay[i:i + k] == needle for i in range(len(hay) - k + 1))


def resolve_ran_out(name: str, batch: List[str], said: Optional[Dict[str, str]] = None) -> str:
    """The batch ingredient a ran-out name means: itself if in the batch; else with leading unit words and "of" dropped
    ("cupfuls of stock" -> "stock"); else the ONE batch name it begins ("granulated" -> "granulated or powdered sugar")
    or the ONE batch name that ends with it ("sugar" -> "brown sugar"); else (v3) the ONE batch line whose own words
    contain the phrase ("cold" -> the line "1 cup cold, cooked rice"). Two candidates at any step -> unchanged (the
    brain refuses: the ingredient is not in the batch). OUR_CONVENTION."""
    if name in batch:
        return name
    words = name.split()
    while words:
        if len(words) > 1 and W.unit_of(words[0] + words[1]) is not None:      # "table spoons"
            words = words[2:]
        elif (W.unit_of(words[0]) is not None or words[0] in W.OTHER_UNIT_WORDS or words[0] in LEADING_DROPPED
              or words[0] in ("level", "heaping", "heaped", "rounded", "good", "scant", "generous")):
            words = words[1:]
        else:
            break
    stripped = bind_name(" ".join(words)) if words else None
    if stripped and stripped in batch:
        return stripped
    name2 = stripped or name
    for test in (lambda b: b.startswith(name2 + " "), lambda b: b.endswith(" " + name2)):
        hits = [b for b in batch if test(b)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            return name
    if said:                                       # v3: the phrase inside exactly one line's own words
        needle = _words(name)
        hits = [b for b in batch if _contains(_words(said.get(b, b)), needle)]
        if len(hits) == 1:
            return hits[0]
    return name


# ---------------------------------------------------------------------------------------------------- dish names
#: words that stand where a dish name should be but name no dish ("We made 2 of it from ...", "We made a batch from")
NOT_A_DISH = {"it", "one", "ones", "some", "thing", "things", "something", "stuff", "that", "this", "them", "those",
              "these", "batch", "dish", "recipe", "lot", "food", "more", "any", "what"}
_WRAPPER_RX = re.compile(r"^(?:(?:a|an|the|one|our|my|your|some|this|that)\s+)?(?:(?:double|single|half|whole|big|small|"
                         r"large|full|new|first|second|another)\s+)?(?:batch(?:es)?|loaf|loaves|pan|pans|tray|trays|"
                         r"serving|servings|portion|portions|recipe|recipes|lot|lots|round|rounds)\s+(?:of|for)\s+")


def bind_product(phrase: str) -> Optional[str]:
    """v3: the dish name as written, in any case, singular or plural, with "a"/"the", multiword, hyphenated or
    possessive, wrapped as "a batch of X", "X recipe", "the recipe for X" -> one bound name. None if no dish is named
    ("it", "a batch"); the wide path then asks for the name once."""
    s = _ascii(phrase.replace("’", "'").strip().lower())
    s = re.sub(r"[.!?]+$", "", s).strip()
    s = _WRAPPER_RX.sub("", s)
    s = re.sub(r"\s+recipes?$", "", s)
    s = re.sub(r"'s\b|s'(?=\s|$)", lambda m: "" if m.group(0) == "'s" else "s", s)   # grandma's -> grandma
    s = re.sub(r"^(?:(?:a|an|the|our|my|your|some|this|that)\s+)+", "", s)
    name = bind_name(s, drop_leading=False)
    if not name or name in NOT_A_DISH or re.search(r"\d", name):
        return None
    return name


def product_key(name: str) -> str:
    """Two written forms are the same dish when every word, made singular, is the same ("Apple-Pies" = "apple pie")."""
    return " ".join(_words(name))


def match_product(book: W.WideRecipeBook, name: Optional[str]) -> Optional[str]:
    """The dish in the wide book a bound name means: itself, else the ONE dish with the same product_key."""
    if not name:
        return None
    exact = book.product_of(name)
    if exact is not None:
        return exact
    hits = [p for p in book.recipes if product_key(p) == product_key(name)]
    return hits[0] if len(hits) == 1 else None


def answer_dish_name(text: str) -> Optional[str]:
    """v3: a reply to "What did that batch make?" -> the bound dish name, or None. Accepts "Gingerbread.", "It was
    gingerbread", "That's my grandma's apple pie", "We made pancakes", "the recipe for scones"."""
    t = normalize_text(text).strip()
    if not t or len(t.split()) > 10 or re.search(r"\d", t) or t.endswith("?"):
        return None
    t = re.sub(r"^(?:oh\s+|well\s+|sorry\s+|yes\s+|ok(?:ay)?\s+)?,?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^(?:it\s+(?:was|is)|it's|that\s+(?:was|is)|that's|they\s+(?:were|are)|those\s+(?:were|are)|"
               r"we\s+(?:made|baked|cooked)|i\s+(?:made|baked|cooked)|it'?s\s+called|they'?re|the\s+dish\s+(?:was|is))\s+",
               "", t, flags=re.IGNORECASE)
    return bind_product(t)


def read_wide(text: str, last_topic: Optional[str] = None) -> Dict[str, Any]:
    """Read one sentence. Status WITNESS, STOCK, QUESTION, CLARIFY or NOT_MINE. Never invents an amount."""
    t = normalize_text(text)
    out: Dict[str, Any] = {"reader": READER_VERSION, "claim_status": CLAIM_STATUS, "status": "NOT_MINE",
                           "normalized": t, "witness": None, "stock": None, "topic": None, "clarify": None}

    def clarify(c: Dict[str, Any]) -> Dict[str, Any]:
        out.update(status="CLARIFY", clarify=c)
        return out

    m = WITNESS_RX.match(t)
    if m:
        rest = m.group("rest")
        try:
            got = W.match_amount(rest, 0)
        except W.WideRefused as exc:
            return clarify(_ask(exc.code, words=rest))
        if got is None:
            return clarify(_ask("NO_MADE_AMOUNT"))
        made, end = got
        rest = rest[end:].strip()
        # v3: the dish name may itself hold "with"/"from" ("chicken with rice from 2 cups rice ..."): try each
        # separator in turn and keep the first whose tail reads as a batch
        seps = list(re.finditer(r"(?:^|\s+)(?:from|using|with)\s+", rest))
        if not seps:
            return clarify(_ask("NO_INGREDIENTS"))
        first_problem: Optional[Dict[str, Any]] = None
        for sep in seps:
            e = END_RX.match(rest[sep.end():])
            if not e:
                first_problem = first_problem or _ask("NO_RAN_OUT", product=bind_product(rest[:sep.start()]))
                continue
            lines, c = parse_lines(e.group("lines"))
            if c:
                first_problem = first_problem or c
                continue
            break
        else:
            return clarify(first_problem or _ask("NO_INGREDIENTS"))
        product = bind_product(rest[:sep.start()])
        ran_out: List[str] = []
        if e.group("out"):
            words = re.sub(r"\b(?:at the same time|at once|first|both|the|too)\b", " ", e.group("out").lower())
            for part in re.split(r",\s*|\s+and\s+|\s+&\s+", words):
                n = bind_name(part) or bind_name(part, drop_leading=False)     # v3: "ran out of large" -> "large"
                if n and n not in ran_out:
                    ran_out.append(n)
        names = [x["name"] for x in lines]
        said = {x["name"]: x["said"] for x in lines}
        ran_out = [resolve_ran_out(n, names, said) for n in ran_out]
        batch = {"product": product, "made": made, "ran_out": ran_out,
                 "stock": {x["name"]: (x["amount"], x["unit"]) for x in lines}, "said": said}
        if not product:                            # v3: the batch is kept so the dish name can be asked for ONCE
            out["pending"] = batch
            return clarify(_ask("NO_PRODUCT"))
        out.update(status="WITNESS", witness=batch)
        return out
    m = STOCK_RX.match(t)
    if m:
        a = ABSENT_TAIL_RX.match(m.group("lines"))
        if a:                                      # v6: "..., but we've run out of sugar" -> a question, never a name
            return clarify(_ask("ABSENT_STATED", item=bind_name(a.group("absent")) or a.group("absent").strip(),
                                words=a.group("lines")))
        lines, c = parse_lines(m.group("lines"))
        if c:
            return clarify(c)
        out.update(status="STOCK", stock={x["name"]: (x["amount"], x["unit"]) for x in lines})
        return out
    m = QUESTION_RX.match(t)
    if m:
        phrase = m.group("p1") or m.group("p2") or m.group("p3") or m.group("p4")
        product = bind_product(phrase)
        if not product:
            return clarify(_ask("NO_PRODUCT"))
        out.update(status="QUESTION", topic=product)
        return out
    return out


def public(reading: Dict[str, Any]) -> Dict[str, Any]:
    """A JSON-safe copy of a reading (exact amounts as text)."""
    def conv(x: Any) -> Any:
        if isinstance(x, Fraction):
            return W.frac_text(x)
        if isinstance(x, dict):
            return {k: conv(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [conv(v) for v in x]
        return x
    return conv(reading)


# ---------------------------------------------------------------------------------------------------- voice
def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def say_and(names: List[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]


def say_amount_of(q: Optional[Fraction], unit: str, name: str) -> str:
    """'1/3 cup of brown sugar', '2 eggs', '1 egg'; stage 1c: a NOTE entry (q None) -> 'salt (no amount given)'."""
    if q is None:
        return f"{name} (no amount given)"
    if unit == "dozen":                            # stage 1c: a plain-count multiplier reads "2 dozen eggs"
        return f"{W.say_quantity(q)} dozen {plural(name)}"
    if unit:
        return f"{W.say_measure(q, unit)} of {name}"
    return f"{W.say_quantity(q)} {plural(name) if q > 1 else name}"


def say_wide(rec: Dict[str, Any]) -> str:
    """The brain's evaluate record in plain English."""
    p = rec["product"]
    gate = rec.get("gate")
    if rec.get("status") == W.EVALUATED and rec.get("tied"):          # v3: a tie still fixes the amount
        return (f"With what's on hand we can make {rec['yield_said']} {p}. {cap(say_and(rec['tied']))} would run out "
                f"at exactly the same moment, so no single one sets the limit.") + say_notes(rec.get("notes"))
    if rec.get("status") == W.EVALUATED:
        return (f"With what's on hand we can make {rec['yield_said']} {p}. "
                f"{cap(rec['limiting_reagent'])} runs out first, so it sets the limit.") + say_notes(rec.get("notes"))
    if gate == "UNKNOWN_PRODUCT":
        return (f"I haven't seen a batch of {p} made yet, so I can't say how much we can make. Tell me about one "
                f"batch: what went in, how much came out, and what ran out first. I didn't guess.")
    if gate == "G1" and rec.get("absent"):
        first = rec["absent"][0]
        ask = (f"How many {plural(first)} are there?" if first in rec.get("count_items", [])
               else f"How much {first} is there?")
        return (f"I can't say how much {p} we can make yet, because I don't know how much "
                f"{say_and(rec['absent'])} we have. {ask} I didn't guess.")
    if gate == "G1":
        todo = rec["unlearned"]
        if len(todo) == 1:
            need = f"one batch where {todo[0]} ran out first while everything else was left over"
        else:
            need = (f"one batch for each of {say_and(todo)}: a batch where that one ran out first while everything "
                    f"else was left over")
        return f"I can't say yet how much {p} we can make. I still need {need}. I didn't guess."
    if gate == "UNIT_KIND_MISMATCH":
        mm = rec["mismatch"][0]
        learned = "as a plain count" if mm["recipe_unit"] == "plain count" else f"in {W.say_unit(mm['recipe_unit'], 2)}"
        said = "a plain count" if mm["said_unit"] == "plain count" else f"in {W.say_unit(mm['said_unit'], 2)}"
        return (f"I learned {mm['ingredient']} for {p} {learned}, but the amount on hand is {said}. I can't turn one "
                f"into the other without guessing, so please give it {learned}. I didn't guess.")
    if gate == "G2":
        return f"With what's on hand we can't make any {p}: we're out of {say_and(rec.get('zero') or ['something'])}."
    if gate == "G3":
        return (f"I can't name one thing that runs out first: {say_and(rec['tied'])} would run out at exactly the "
                f"same moment. I didn't guess.")
    return f"I can't work out {p} right now. I didn't guess, and nothing was saved."


def say_notes(notes: Optional[List[str]]) -> str:
    """Stage 1c: the sentence about NOTE ingredients (present, no amount); '' when there are none."""
    if not notes:
        return ""
    many = len(notes) > 1
    return (f" {cap(say_and(notes))} {'go' if many else 'goes'} in too, with no set amount, so I didn't count "
            f"{'them' if many else 'it'} toward the limit.")


def say_learned(record: Dict[str, Any], brain: W.WideRecipeBook) -> str:
    p, n = record["product"], record["ingredient"]
    unit = brain.recipes[p]["taught_unit"][n]
    q = W.from_base(brain.coefficient(p, n), unit)
    msg = f"Got it: one {p} needs {say_amount_of(q, unit, n)}." + say_notes(record.get("notes"))
    left = brain.unlearned(p)
    if left:
        msg += (f" I still need one batch for each of {say_and(left)} before I can work out {p}."
                if len(left) > 1 else f" I still need one batch where {left[0]} ran out first.")
    else:
        msg += f" That's every ingredient of {p}."
    return msg


def say_refused(record: Dict[str, Any], brain: W.WideRecipeBook) -> str:
    reason, p = record["reason"], record.get("product") or "that"
    d = record.get("detail") or {}
    tail = " Nothing was saved."
    if reason == "REFUSED_NOTHING_RAN_OUT":
        return f"Nothing ran out in that batch, so it can't tell me how much of anything one {p} needs.{tail}"
    if reason == "REFUSED_TWO_RAN_OUT":
        return (f"{cap(say_and(d.get('ran_out') or record['ran_out']))} ran out at the same time, so I can't tell "
                f"which one set the limit.{tail}")
    if reason == "RECEIPT_FAILED":
        tied = d.get("tied_with") or []
        who = say_and(tied) if tied else "another ingredient"
        return (f"That batch doesn't add up: from what I've already learned, {who} would have run out at the same "
                f"moment as {say_and(record['ran_out'])}.{tail}")
    if reason == "MEMORY_CHECK_REFUSED":
        return f"That batch disagrees with a batch of {p} you told me about before, so I didn't change anything.{tail}"
    if reason == "REFUSED_CONFLICT":
        n = d.get("ingredient")
        unit = brain.recipes[p]["taught_unit"].get(n, "") if p in brain.recipes else ""
        old = say_amount_of(W.from_base(Fraction(d["old"]), unit), unit, n)
        new = say_amount_of(W.from_base(Fraction(d["new"]), unit), unit, n)
        return (f"Earlier batches say one {p} needs {old}; this one says {new}. Those can't both be right, so I kept "
                f"what I had.{tail}")
    if reason == "REFUSED_SUPPORT_MISMATCH":
        parts = []
        if d.get("missing"):
            parts.append(f"it has no {say_and(d['missing'])}")
        if d.get("extra"):
            parts.append(f"it has {say_and(d['extra'])}, which the {p} I know doesn't use")
        return f"That batch doesn't match the {p} I know: {' and '.join(parts)}.{tail}"
    if reason == "REFUSED_UNIT_KIND_MISMATCH":
        return (f"{cap(say_and(d.get('ingredients') or []))} was given in a kind of unit I can't turn into the one I "
                f"learned it in (like cups into grams).{tail}")
    if reason == "REFUSED_TOO_MANY_INGREDIENTS":
        return f"That batch has {d.get('count')} ingredients; I can hold at most {W.MAX_INGREDIENTS} per recipe.{tail}"
    if reason == "REFUSED_UNIT_NOT_IN_TABLE":
        return f"I don't have an exact size for one of those units, so I can't use that batch.{tail}"
    if reason == W.REFUSED_RAN_OUT_IS_A_NOTE:      # stage 1c
        return (f"{cap(d.get('ingredient', 'that'))} was given with no exact amount, so I can't learn how much of it "
                f"one {p} needs from this batch. Tell me the amount in a unit I can size and I'll learn it.{tail}")
    if reason == "REFUSED_ZERO_YIELD":
        return f"That batch made nothing, so it can't teach me anything.{tail}"
    if reason == "REFUSED_RAN_OUT_NOT_IN_BATCH":
        return f"{cap(d.get('ran_out', 'That'))} wasn't in that batch, so it can't be what ran out.{tail}"
    return f"I couldn't use that batch.{tail}"


def say_reader_question(c: Dict[str, Any]) -> str:
    code, s = c["code"], c.get("slots") or {}
    if code == "AMOUNT_IS_A_RANGE":
        return f"You gave a range (\"{s.get('words', '')}\"). I need one exact amount. How much was it?"
    if code == "AMOUNT_APPROXIMATE":
        return f"\"{s.get('words', '')}\" sounds like a rough amount. I need the exact amount. How much was it?"
    if code == "NO_AMOUNT":
        item = s.get("item")
        return (f"How much {item} is there? I need a number to work with." if item
                else "How much is there? I need a number to work with.")
    if code == "UNIT_NOT_IN_TABLE":
        return (f"I don't have an exact size for \"{s.get('unit', '')}\". Could you give that amount in cups, "
                f"spoons, ounces, pounds, grams or milliliters?")
    if code == "NO_RAN_OUT":
        return "Which ingredient ran out first in that batch?"
    if code == "NO_MADE_AMOUNT":
        return "How much did that batch make?"
    if code == "SAME_INGREDIENT_TWICE":
        return f"You named {s.get('item', 'one ingredient')} twice. Which amount is right?"
    if code == "NO_PRODUCT":
        return ("I got the batch, but not what it made. What's the dish called? Tell me its name and I'll learn "
                "from that batch. Nothing is saved until then.")
    if code == "AMOUNT_RELATIVE":
        return (f"You said \"{s.get('words', '')}\". I can only use an amount like that when it is half, twice or "
                f"the same as the line right before it. How much is it exactly, on its own?")
    if code == "ABSENT_STATED":
        item = s.get("item") or "that"
        return (f"You said we've run out of {item}. I don't record stock from a sentence like that, so I didn't save "
                f"anything. Tell me the amounts on hand exactly, and say {item} is 0 if that's what you mean.")
    if code == "NO_INGREDIENTS":
        return "What went into that batch, and how much of each?"
    return "Could you say that another way? Nothing was saved."


NOT_MINE_LINE = ("I'm not sure what to do with that. I can learn from a batch you made, note what's on hand, or tell "
                 "you how much of something we can make. Nothing was saved.")


# ---------------------------------------------------------------------------------------------------- the turn
def _cce_amount(cce: Any, q: Fraction) -> str:
    return cce.num(W.frac_text(q))


#: licensed loop statuses meaning "the licensed reader or brain could not bind this turn" (and nothing was written)
CANNOT_BIND = {"CLARIFY_ENGLISH_UNKNOWN_INGREDIENT", "CLARIFY_ENGLISH_UNKNOWN_PRODUCT",
               "CLARIFY_ENGLISH_BATCH_NEEDS_PRODUCT", "CLARIFY_ENGLISH_NO_INGREDIENT_NAMED",
               "CLARIFY_ENGLISH_NO_NUMBER", "CLARIFY_ENGLISH_CONVERSION_REFUSED", "CLARIFY_ENGLISH_UNIT_MISMATCH",
               "CLARIFY_NOT_CCE", "CLARIFY_BATCH_NOT_USABLE", "CLARIFY_UNKNOWN_PRODUCT", "NOTHING_TO_SAVE",
               "CLARIFY_STOCK_NOT_RECORDED", "CLARIFY_ENGLISH_PRODUCT_AS_STOCK"}
#: for a QUESTION about a product the wide book holds, the licensed path also "cannot" when it only asked
#: v3: the statuses where the wide path may take a turn (the same set as v2)
WIDE_MAY_TAKE = CANNOT_BIND
QUESTION_NOT_ANSWERED = WIDE_MAY_TAKE | {"UNDETERMINED_CLARIFY", "BRAIN_UNDETERMINED"}
#: v3: a whole batch with no dish name ("We made a batch from ..."): the licensed path asks what it made but cannot use
#: the reply; the wide path asks for the dish name once and keeps the batch for that one reply
PENDING_MAY_TAKE = {"CLARIFY_ENGLISH_BATCH_NEEDS_MADE"}
STOCK_DONE = {"INVENTORY_RECORDED"}


def take_over(loop: Any, licensed: Dict[str, Any], reading: Dict[str, Any]) -> bool:
    """Should the wide path take this turn? Only if the licensed path could not bind it and wrote nothing, AND the
    wide reader reads it as something the wide brain can use: a witnessed batch (v3: also one whose dish name is
    missing -- the wide path then asks for it once); stock whose every ingredient is in a recipe the wide brain holds;
    a question about a product the wide brain holds."""
    if licensed.get("cubes_written"):
        return False
    status = licensed.get("loop_status")
    book = loop.wide_book
    if reading["status"] == "QUESTION":
        return status in QUESTION_NOT_ANSWERED and match_product(book, reading["topic"]) is not None
    if reading["status"] == "CLARIFY" and reading.get("pending") is not None:
        return status in WIDE_MAY_TAKE or status in PENDING_MAY_TAKE
    if status not in WIDE_MAY_TAKE:
        return False
    if reading["status"] == "WITNESS":
        return True
    if reading["status"] == "STOCK":
        known = set(book.ingredients)
        if W.units_note_on():                      # stage 1c: a NOTE ingredient of a wide recipe is known too
            known |= set(book.note_names())
        return bool(reading["stock"]) and all(n in known for n in reading["stock"])
    return False


def _answer_pending(loop: Any, user_english: str, tick: int, licensed: Dict[str, Any],
                    reading: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """v3: the turn right after the wide path asked for a dish name. The batch waits for ONE reply; it is then used
    (the reply binds a dish name) or dropped (it does not). Never asked twice. A reply that is itself a batch, stock
    or question, or one the licensed path used (it wrote something), is handled as usual and the batch is dropped."""
    pending = getattr(loop, "wide_pending", None)
    if pending is None:
        return None
    loop.wide_pending = None
    if licensed.get("cubes_written") or reading["status"] in ("WITNESS", "STOCK", "QUESTION"):
        return None
    name = answer_dish_name(user_english)
    if name is None:
        result = loop._new_result(user_english, tick)
        writes_before = loop._store_writes()
        loop._emit(tick, "user", text=user_english.strip())
        loop._emit(tick, "English in (wide)", reader=READER_VERSION, status="DISH_NAME_NOT_BOUND")
        return loop._finish(result, tick, "CLARIFY_WIDE_DISH_NAME_NOT_BOUND",
                            "I still couldn't tell what that batch made, so I didn't learn from it. Nothing was "
                            "saved. You can tell me the whole batch again with the dish name in it.",
                            writes_before, "WAIT_FOR_USER")
    product = match_product(loop.wide_book, name) or name
    result = loop._new_result(user_english, tick)
    result["english_in"] = {"reader": READER_VERSION, "status": "DISH_NAME", "product": product}
    return wide_witness(loop, product, pending["stock"], pending["made"], pending["ran_out"], tick, result=result)


def extended_turn(loop: Any, user_english: str, tick: int, current_inventory: Any = None) -> Dict[str, Any]:
    """WIDE_BRAIN ON: the licensed path first, unchanged; the wide path only where the licensed one cannot bind."""
    res = loop._process_turn_licensed(user_english, tick, current_inventory)
    reading = read_wide(user_english.strip(), last_topic=loop.last_topic)
    answered = _answer_pending(loop, user_english, tick, res, reading)
    if answered is not None:
        answered["path"] = "wide"
        answered["licensed_first"] = {"loop_status": res.get("loop_status")}
        return answered
    recorded = res.get("loop_status") in STOCK_DONE and reading["status"] == "STOCK"
    if recorded:
        _stock_of(loop).update(reading["stock"])          # one stock on hand; the wide brain reads it too (no write)
    taken = take_over(loop, res, reading)
    if not taken and not recorded and reading["status"] != "QUESTION":
        _withdraw_mentioned_stock(loop, user_english, tick)   # v4: never answer from stock the person just restated
    if taken:
        wres = wide_turn(loop, user_english, tick)
        wres["path"] = "wide"
        wres["licensed_first"] = {"loop_status": res.get("loop_status")}
        return wres
    res["path"] = "licensed"
    return res


def extended_witness(loop: Any, product: str, stock_before: Dict[str, Any], made: Any, ran_out: Any,
                     tick: int) -> Dict[str, Any]:
    """WIDE_BRAIN ON, the structured teaching channel: licensed first; the wide brain only for a product or ingredient
    the licensed brain cannot bind."""
    res = loop._witness_batch_licensed(product, stock_before, made, ran_out, tick)
    if not res.get("cubes_written") and res.get("loop_status") in CANNOT_BIND:
        wres = wide_witness(loop, product, stock_before, made, ran_out, tick)
        wres["path"] = "wide"
        wres["licensed_first"] = {"loop_status": res.get("loop_status")}
        return wres
    res["path"] = "licensed"
    return res


def wide_turn(loop: Any, user_english: str, tick: int) -> Dict[str, Any]:
    """One user turn with WIDE_BRAIN ON. `loop` is a helm_end_to_end_loop.HELMEndToEndLoop."""
    import helm_end_to_end_loop as E
    result = loop._new_result(user_english, tick)
    writes_before = loop._store_writes()
    text = user_english.strip()
    loop._emit(tick, "user", text=text)
    reading = read_wide(text, last_topic=loop.last_topic)
    result["english_in"] = public(reading)
    loop._emit(tick, "English in (wide)", reader=READER_VERSION, status=reading["status"],
               witness=public(reading["witness"]), stock=public(reading["stock"]), topic=reading["topic"],
               clarify=reading["clarify"])
    if reading["status"] == "NOT_MINE":
        return loop._finish(result, tick, "WIDE_NOT_MINE", NOT_MINE_LINE, writes_before, "WAIT_FOR_USER")
    if reading["status"] == "CLARIFY":
        code = reading["clarify"]["code"]
        if reading.get("pending") is not None:     # v3: keep the batch for ONE reply naming the dish
            loop.wide_pending = reading["pending"]
        return loop._finish(result, tick, f"CLARIFY_WIDE_{code}", say_reader_question(reading["clarify"]),
                            writes_before, f"WAIT_FOR_USER: {code}")
    if E.cce is None:
        return loop._finish(result, tick, "REFUSE_NOT_VERIFIED", E.HELMVoiceAdapter.format_not_verified(),
                            writes_before, "STOP")
    if reading["status"] == "WITNESS":
        w = reading["witness"]
        return wide_witness(loop, w["product"], w["stock"], w["made"], w["ran_out"], tick, result=result,
                            writes_before=writes_before)
    if reading["status"] == "STOCK":
        return _wide_stock(loop, reading["stock"], tick, result, writes_before)
    return _wide_question(loop, reading["topic"], tick, result, writes_before)


def faces_said_about(loop: Any, product: str, support: List[str]) -> List[Dict[str, str]]:
    """v4 (wave-6 FIX FIRST): faces the person stated (held by the licensed triad, helm_triad.TriadTable) that touch
    this wide recipe: a face on an ingredient whose name is a wide ingredient's name or its last word ("the butter is
    past its best" touches "butter" and "melted butter"), or a recipe Purpose on this dish, at any stage but Peak. The
    wide brain does not apply faces (the triad wraps only the licensed brain), so the question is asked instead."""
    table = getattr(getattr(loop, "brain", None), "table", None)
    records = getattr(table, "records", None)
    if not records:
        return []
    names = {n.lower() for n in support} | {singular(n.split()[-1]).lower() for n in support if n.split()}
    out = []
    for key in sorted(records):
        try:
            rec = json.loads(records[key])
        except (TypeError, ValueError):
            continue
        if rec.get("stage") == "PEAK":
            continue
        nm = str(rec.get("name", "")).lower()
        if (rec.get("scope") == "ingredient" and (nm in names or singular(nm) in names)) or \
                (rec.get("scope") == "recipe" and product_key(nm) == product_key(product)):
            out.append({"scope": rec.get("scope"), "name": rec.get("name"), "face": rec.get("face"),
                        "stage": rec.get("stage")})
    return out


def _withdraw_mentioned_stock(loop: Any, user_english: str, tick: int) -> List[str]:
    """v4 (wave-6 FIX FIRST): a turn the wide path could not take that names an ingredient whose stock the wide brain
    holds (a restatement it could not read, an amount in a unit it does not know, a face or purpose clause) makes that
    held amount stale: it is withdrawn, so the next question asks instead of answering from the old amount. Nothing is
    written to the store; the withdrawal is traced."""
    held = _stock_of(loop)
    if not held:
        return []
    words = normalize_text(user_english).lower()
    gone = []
    for n in list(held):
        forms = {n.lower(), plural(n).lower()}
        if any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(f), words) for f in forms if f):
            held.pop(n)
            gone.append(n)
    if gone:
        loop._emit(tick, "S2 Bias ^5", what="stock_withdrawn (wide)", reason="restated but not read",
                   withdrawn=sorted(gone))
    return gone


def _stock_of(loop: Any) -> Dict[str, Tuple[Fraction, str]]:
    if not hasattr(loop, "wide_stock"):
        loop.wide_stock = {}
    return loop.wide_stock


def _wide_stock(loop: Any, stock: Dict[str, Tuple[Fraction, str]], tick: int, result: Dict[str, Any],
                writes_before: int) -> Dict[str, Any]:
    import helm_end_to_end_loop as E
    amounts = {n: (q, u) for n, (q, u) in stock.items() if q is not None}
    if amounts:
        form = E.cce.empty_content()
        form["stocks"] = [{"amount": _cce_amount(E.cce, q), "ref": {"outcome": omega(n)}} for n, (q, _u) in amounts.items()]
        rt = loop.verify_cce_round_trip(form)
        result["cce_round_trip"] = {k: v for k, v in rt.items() if k != "content"}
        loop._emit(tick, "CCE skin", **result["cce_round_trip"])
        if not rt["verified"]:
            return loop._finish(result, tick, "CLARIFY_ROUND_TRIP_FAILED", E.HELMVoiceAdapter.format_round_trip_failed(),
                                writes_before, "WAIT_FOR_USER")
    else:                                          # stage 1c: NOTE entries only: no number to round-trip, none saved
        result["cce_round_trip"] = {"verified": None, "skipped": "notes only: no amount to round-trip; no number is saved"}
        loop._emit(tick, "CCE skin", **result["cce_round_trip"])
    held = _stock_of(loop)
    held.update(stock)
    loop.bias_version += 1
    said = [say_amount_of(q, u, n) for n, (q, u) in stock.items()]
    loop._emit(tick, "S2 Bias ^5", what="stock_on_hand (wide)", bias_version=loop.bias_version,
               stock={n: [W.frac_text(q), u] for n, (q, u) in held.items()})
    statement = "Stock on hand (user said): " + "; ".join(said)
    write = loop._write_event_cube(f"wide_stock_t{tick}", "Stock on hand", statement, "USER_SAID", tick)
    loop._emit(tick, "store", what="cube_write", **write)
    result["cube_receipt"] = write
    return loop._finish(result, tick, "STOCK_RECORDED", f"Noted: we have {say_and(said)}.", writes_before, "DONE")


def _wide_question(loop: Any, topic: str, tick: int, result: Dict[str, Any], writes_before: int) -> Dict[str, Any]:
    import helm_end_to_end_loop as E
    brain = loop.wide_book
    held = _stock_of(loop)
    product = match_product(brain, topic)
    loop._emit(tick, "S0 atlas head", topic=topic, product=product, brain=brain.provenance())
    if product is None:
        rec = brain.evaluate(topic, {})
        result["recipe_receipt"] = rec
        return loop._finish(result, tick, "UNDETERMINED_UNKNOWN_PRODUCT", say_wide(rec), writes_before,
                            "WAIT_FOR_USER: a witnessed batch")
    loop.last_topic = product
    support = brain.support_of(product)
    faced = faces_said_about(loop, product, support)
    if faced:                                      # v4: a stated face this brain cannot apply -> ask, never ignore it
        loop._emit(tick, "S1 trigger ^8", product=product, faces_not_held=faced)
        result["faces_not_held"] = faced
        what = "the " + faced[0]["name"].lower() if faced[0]["scope"] == "ingredient" else "whether it's needed"
        return loop._finish(result, tick, "CLARIFY_WIDE_FACE_NOT_HELD",
                            f"You told me something about {what}, and I can't use that for {product} yet, so I won't "
                            f"guess how much we can make. Can you tell me the amounts to count on instead?",
                            writes_before, "WAIT_FOR_USER: amounts that already allow for it")
    loop._emit(tick, "S1 trigger ^8", product=product, prerequisites=support,
               requirements=brain.requirements(product))
    loop._emit(tick, "S2 Bias ^5", what="stock_on_hand (wide)", bias_version=loop.bias_version,
               stock={n: [W.frac_text(q), u] for n, (q, u) in held.items()})
    absent = [n for n in support if n not in held]
    unlearned = brain.unlearned(product)
    loop._emit(tick, "S3 arrival ^9", present=[n for n in support if n in held], absent=absent,
               unlearned_requirements=unlearned)
    allowed, telem = loop.valve.evaluate_reagents(tick, product, support, list(held), "EXACT")
    result["valve_telemetry"] = telem.as_dict()
    loop._emit(tick, "S4 operating point", valve=telem.as_dict())
    unsatisfied = [f"the stock of {omega(n)}" for n in absent] + \
                  [f"the requirement of {omega(n)} for {omega(product)}" for n in unlearned]
    request = loop._gate_request(tick, f"compute {omega(product)} from the stock on hand", support, unsatisfied,
                                 omega(product))
    verdict = E.RPM.rpm_gate(request)
    loop._emit(tick, "S5 RPM link", what="gate", request=request.as_dict(), verdict=verdict.as_dict())
    result["gate_verdict"] = verdict.as_dict()
    stock = {n: held[n] for n in support if n in held}
    if verdict.verdict != E.RPM.PROCEED:
        rec = brain.evaluate(product, stock)
        result["recipe_receipt"] = rec
        return loop._finish(result, tick, "UNDETERMINED_CLARIFY", say_wide(rec), writes_before,
                            f"WAIT_FOR_USER: {verdict.gap}")
    form = E.cce.empty_content()
    form["topic"] = omega(product)
    form["stocks"] = [{"amount": _cce_amount(E.cce, q), "ref": {"outcome": omega(n)}} for n, (q, _u) in stock.items()]
    rt = loop.verify_cce_round_trip(form)
    result["cce_round_trip"] = {k: v for k, v in rt.items() if k != "content"}
    loop._emit(tick, "CCE skin", **result["cce_round_trip"])
    if not rt["verified"]:
        return loop._finish(result, tick, "CLARIFY_ROUND_TRIP_FAILED", E.HELMVoiceAdapter.format_round_trip_failed(),
                            writes_before, "WAIT_FOR_USER")
    rec = brain.evaluate(product, stock)
    result["recipe_receipt"] = rec
    loop._emit(tick, "brain", **rec)
    if rec["status"] != W.EVALUATED:
        return loop._finish(result, tick, "BRAIN_UNDETERMINED", say_wide(rec), writes_before, "WAIT_FOR_USER")
    y, lim = rec["yield"], rec["limiting_reagent"]
    result.update({"output_value": y, "total_output": y, "output": y, "limiting_reagent": lim})
    statement = (f"Theoretical yield {y} of {product} from stock "
                 f"{'; '.join(say_amount_of(q, u, n) for n, (q, u) in stock.items())}; "
                 f"{('limiting reagent ' + lim) if lim else ('tied at the limit: ' + ', '.join(rec['tied']))}; "
                 f"wide brain {rec['learned_digest'][:16]}")
    write = loop._write_event_cube(f"wide_yield_{'_'.join(product.split())}_t{tick}", f"{product} yield", statement,
                                   "CHECKED", tick, kind="instance")
    loop._emit(tick, "store", what="cube_write", **write)
    result["cube_receipt"] = write
    return loop._finish(result, tick, "SUCCESS_EVALUATED", say_wide(rec), writes_before, "DONE")


def wide_witness(loop: Any, product: str, stock_before: Dict[str, Any], made: Any, ran_out: Any, tick: int,
                 result: Optional[Dict[str, Any]] = None, writes_before: Optional[int] = None) -> Dict[str, Any]:
    """The teaching channel with WIDE_BRAIN ON: CCE form receipt -> gate -> the wide brain's own checks -> store."""
    import helm_end_to_end_loop as E
    brain = loop.wide_book
    if result is None:
        result = loop._new_result(f"[witnessed batch] {product}", tick)
    if writes_before is None:
        writes_before = loop._store_writes()
    p = W.norm_name(product)
    p = match_product(brain, p) or p               # v3: "Apple-Pies" teaches the same dish as "apple pie"
    try:
        stock = {W.norm_name(k): W._stock_entry(v) for k, v in stock_before.items()}
        made_q = W.parse_quantity(made)
    except W.WideRefused as exc:
        return loop._finish(result, tick, f"CLARIFY_WIDE_{exc.code}", say_reader_question({"code": exc.code}),
                            writes_before, "WAIT_FOR_USER")
    names_out = [ran_out] if isinstance(ran_out, str) else list(ran_out or [])
    loop._emit(tick, "user", what="witnessed_batch (wide)", product=p,
               stock_before={n: [W.frac_text(q), u] for n, (q, u) in stock.items()}, made=W.frac_text(made_q),
               ran_out=names_out)
    if E.cce is None:
        return loop._finish(result, tick, "REFUSE_NOT_VERIFIED", E.HELMVoiceAdapter.format_not_verified(),
                            writes_before, "STOP")
    form = E.cce.empty_content()
    form["topic"] = omega(p)
    form["stocks"] = ([{"amount": _cce_amount(E.cce, q), "ref": {"outcome": omega(n)}} for n, (q, _u) in stock.items()
                       if q is not None]          # stage 1c: NOTE entries carry no amount
                      + [{"amount": _cce_amount(E.cce, made_q), "ref": {"outcome": omega(p)}}])
    rt = loop.verify_cce_round_trip(form)
    result["cce_round_trip"] = {k: v for k, v in rt.items() if k != "content"}
    loop._emit(tick, "CCE skin", **result["cce_round_trip"])
    if not rt["verified"]:
        return loop._finish(result, tick, "CLARIFY_ROUND_TRIP_FAILED", E.HELMVoiceAdapter.format_round_trip_failed(),
                            writes_before, "WAIT_FOR_USER")
    names = list(stock)
    loop._emit(tick, "S1 trigger ^8", product=p, prerequisites=names)
    loop._emit(tick, "S3 arrival ^9", present=names, absent=[])
    request = loop._gate_request(tick, f"teach {omega(p)} from a witnessed batch", names, [], omega(p))
    verdict = E.RPM.rpm_gate(request)
    loop._emit(tick, "S5 RPM link", what="gate", request=request.as_dict(), verdict=verdict.as_dict())
    result["gate_verdict"] = verdict.as_dict()
    if verdict.verdict != E.RPM.PROCEED:
        return loop._finish(result, tick, "UNDETERMINED_CLARIFY",
                            "That batch report is missing something I need. I didn't guess, and nothing was saved.",
                            writes_before, f"WAIT_FOR_USER: {verdict.gap}")
    record = brain.witness(p, stock, made_q, names_out)
    result["recipe_receipt"] = record
    loop._emit(tick, "brain", what="writer (wide)", record=record)
    if not record["admitted"]:
        return loop._finish(result, tick, f"TEACH_REFUSED_{record['reason']}", say_refused(record, brain),
                            writes_before, "WAIT_FOR_USER")
    if not (record.get("eta_eps", {}).get("pass") and record.get("memory_check_ok")):
        return loop._finish(result, tick, "REFUSE_RECEIPT_INCONSISTENT",
                            "The brain's own check did not hold, so nothing was saved.", writes_before, "STOP")
    n = record["ingredient"]
    statement = (f"Witnessed batch {record['made']} of {p}; {n} ran out first; requirement {record['value_said']} "
                 f"{n} per {p}; receipt pass")
    write = loop._write_event_cube(f"wide_batch_{'_'.join(p.split())}_{record['seed']}", f"{p} batch", statement,
                                   "USER_SAID", tick)
    loop._emit(tick, "store", what="cube_write", **write)
    result["cube_receipt"] = write
    return loop._finish(result, tick, "WITNESS_ADMITTED", say_learned(record, brain), writes_before, "DONE")
