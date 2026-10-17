"""lexicon.py -- the three FROZEN lexicon tiers of CCE v0.1, and the closed word list.

TRANSLATOR_SPEC.md section 3 freezes the lexicon before any parser or renderer code:

  CANON tier     the ten Noetic names and the verbs of their verbatim definitions (Clarification
                 1), the Domain words, the Register words, the canonical Drive names.
  ALIAS tier     the canonical colloquialisms of Clarification 6, each turned into a frame with
                 the SAME slots as its definition frame. Bare "cause" and "effect" are dropped
                 (bridge v2 row 00353).
  FUNCTION tier  a closed list of glue words. Nothing outside the three tiers, the names, and
                 digits may appear in a CCE sentence.

This module holds the tiers and the templates, and nothing that parses or renders. Both
cce_parse.py and cce_render.py read their frames from here, so a word cannot enter one
direction only -- and roundtrip.check_lexicon() proves every word a sentence uses is frozen.

The templates are the frames of MAP.md section A (CANON) and of the frozen 2026-10-14 grammar
v0.1b ALIAS tier, which is the reviewed form of Clarification 6.
"""

from __future__ import annotations

import re

from content import N

CCE_VERSION = "cce-v0.1-pq"        # the frozen v0.1 lineage plus the owner's p/q ruling (Q13)
FIXED_UNDETERMINED = "I cannot tell."
DRAW_CAP = 8                       # OPEN_QUESTIONS Q16 default

# --- CANON: the ten names and their verbatim definitions (Clarification 1). Never edited. ----------------------
DEFINITIONS = {
    0: "All things in and outside the Mind.",
    1: "Various degrees of awareness that processes, stores, outputs, and intakes Ideas.",
    2: "An Idea the Mind has an affinity for and is attracted toward.",
    3: "An Idea the Mind is adverse to and repelled by.",
    4: "The degree to which an Idea resonates with the Mind, its impression.",
    5: "A Mind impregnated with an Idea, the Ideas a Mind is composed of.",
    6: "An Idea impregnated with another Idea, the Ideas an Idea is composed of.",
    7: "The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.",
    8: "An Idea that triggers a different Idea than itself to come to Mind.",
    9: "The Idea brought to Mind by an Above/Cause trigger.",
}
NOETIC_NAMES = {0: "Idea", 1: "Mind", 2: "Positive", 3: "Negative", 4: "Vibration", 5: "Female",
                6: "Male", 7: "Rhythm", 8: "Above/Cause", 9: "Below/Effect"}
NAME_OF_NOETIC = {name: number for number, name in NOETIC_NAMES.items()}
# The definition written back as a reference, final period dropped: [The Idea brought to Mind ...]
DEF_REF = {number: "[" + text[:-1] + "]" for number, text in DEFINITIONS.items()}
DEF_REF_OF = {text: number for number, text in DEF_REF.items()}

DOMAINS = {"P": "principled", "C": "cognitive", "E": "evaluative", "O": "operational"}
DOMAIN_OF_WORD = {word: letter for letter, word in DOMAINS.items()}
REG_ORDER = "TAfE"
REGISTERS = {"T": "transcendent", "A": "analytical", "f": "affective", "E": "embodied"}
REGISTER_OF_WORD = {word: letter for letter, word in REGISTERS.items()}
DRIVES = {"F1": "Unity", "F2": "Wisdom", "F3": "Vitality", "F4": "Connection", "F5": "Agency",
          "F6": "Structure", "F7": "Purpose"}          # OPEN_QUESTIONS Q15 default (CLAUDE.md list)
DRIVE_OF_WORD = {word: key for key, word in DRIVES.items()}
ACTS = ("intakes", "processes", "stores", "outputs")
NUMBER_WORDS = N.NUMBER_WORDS

# Closed unit and pattern words for the ^7 Rhythm frame.
# UNDECIDED IN SPEC: may the unit and pattern slots of the Rhythm frame take any lowercase word, or must they come from a closed list?
# cce_sketch.py lets them be any word; an open word cannot be proved to come from a frozen tier, so
# this build closes both lists. A content whose unit or pattern is outside them has NO_FORM (a FORM
# gap), never a paraphrase.
UNITS = ("day", "week", "hour", "month", "year", "session")
PATTERNS = ("daily", "weekly", "hourly", "monthly", "yearly", "regular", "irregular", "alternating")


class Template:
    """One frozen frame. text uses {M} Mind, {W} Mind inside "who ... is", {I}/{J} Ideas,
    {D} degree, {R} rate, {U} unit, {P} pattern, and ~verb for the polarity point."""

    __slots__ = ("tid", "noetic", "tier", "text", "act", "slots", "length", "verb")

    def __init__(self, tid: int, noetic: int, tier: str, text: str, act=None):
        self.tid = tid
        self.noetic = noetic
        self.tier = tier
        self.text = text
        self.act = act
        slots = {"M" if key == "W" else key for key in re.findall(r"\{([A-Z])\}", text)}
        if act:
            slots.add("ACT")
        self.slots = frozenset(slots)
        # Length of the frame without its slot placeholders: the "longest match" measure, and
        # the quantity that decides whether two frames tie (TRANSLATOR_SPEC section 3).
        self.length = len(re.sub(r"\{[A-Z]\}", "", text))
        found = re.search(r"~(\w+)", text)
        self.verb = found.group(1) if found else None

    def __repr__(self) -> str:
        return "Template(%d, %s, %r)" % (self.tid, self.tier, self.text)


# --- The frozen frame table ------------------------------------------------------------------------------------
_RAW_TEMPLATES = [
    # ^0 Idea -----------------------------------------------------------------------------------------------
    (0, "CANON", '{I} ~is an Idea', None),
    # ^1 Mind: the FOUR acts are the definition's own verbs, and the act IS content --------------
    (1, "CANON", '{M} ~intakes {I}', "intakes"),
    (1, "CANON", '{M} ~processes {I}', "processes"),
    (1, "CANON", '{M} ~stores {I}', "stores"),
    (1, "CANON", '{M} ~outputs {I}', "outputs"),
    (1, "ALIAS", '{M} ~is paying attention to {I}', None),      # no ACT: cannot say which act
    # ^2 Positive ---------------------------------------------------------------------------------
    (2, "CANON", '{M} ~has an affinity for {I}', None),
    (2, "CANON", '{M} ~is attracted toward {I}', None),
    (2, "ALIAS", '{M} ~is drawn to {I}', None),
    (2, "ALIAS", '{I} ~speaks to {M}', None),
    (2, "ALIAS", '{M} ~likes {I}', None),
    (2, "ALIAS", '{M} ~loves {I}', None),
    (2, "ALIAS", '{M} ~is fond of {I}', None),
    (2, "ALIAS", '{I} ~appeals to {M}', None),
    (2, "ALIAS", '{M} ~is keen on {I}', None),
    (2, "ALIAS", '{I} ~draws {M} in', None),
    # ^3 Negative: VISCERAL, never analytical (Clarification 6 anti-drift) -------------------------
    (3, "CANON", '{M} ~is adverse to {I}', None),
    (3, "CANON", '{M} ~is repelled by {I}', None),
    (3, "ALIAS", '{I} ~rubs {M} the wrong way', None),
    (3, "ALIAS", '{M} ~hates {I}', None),
    (3, "ALIAS", '{M} ~dislikes {I}', None),
    (3, "ALIAS", '{I} ~disgusts {M}', None),
    (3, "ALIAS", '{I} ~puts {M} off', None),
    (3, "ALIAS", '{I} ~turns {M} off', None),
    # ^4 Vibration: degree optional, and an absent degree is never invented ------------------------
    (4, "CANON", '{I} ~resonates with {M} to degree {D}', None),
    (4, "CANON", '{I} ~resonates with {M}', None),
    (4, "ALIAS", '{I} ~struck a chord with {M}, degree {D}', None),
    (4, "ALIAS", '{I} ~struck a chord with {M}', None),
    (4, "ALIAS", '{I} ~made an impression on {M}, degree {D}', None),
    (4, "ALIAS", '{I} ~made an impression on {M}', None),
    (4, "ALIAS", '{I} ~hit {M} hard, degree {D}', None),
    (4, "ALIAS", '{I} ~hit {M} hard', None),
    (4, "ALIAS", '{I} ~landed on {M}, degree {D}', None),
    (4, "ALIAS", '{I} ~landed on {M}', None),
    # ^5 Female: MIND subject ---------------------------------------------------------------------
    (5, "CANON", '{M} ~is impregnated with {I}', None),
    (5, "CANON", '{M} ~is composed of {I}', None),
    (5, "ALIAS", '{I} ~is part of who {W}', None),
    (5, "ALIAS", '{M} ~is made of {I}', None),
    (5, "ALIAS", '{I} ~shapes {M}', None),
    # ^6 Male: IDEA subject, "another Idea" -------------------------------------------------------
    (6, "CANON", '{I} ~is impregnated with {J}', None),
    (6, "CANON", '{I} ~is composed of {J}', None),
    (6, "ALIAS", '{I} ~breaks down into {J}', None),
    (6, "ALIAS", '{M} ~breaks {I} down into {J}', None),         # a Mind doing the decomposing
    (6, "ALIAS", '{M} ~unpacks {I} into {J}', None),
    (6, "ALIAS", '{I} ~breaks apart into {J}', None),
    (6, "ALIAS", '{M} ~takes {I} apart into {J}', None),
    # ^7 Rhythm: rate/unit/pattern, or not stated -------------------------------------------------
    (7, "CANON", '{M} ~is exposed to {I} at rate {R} per {U}, pattern {P}', None),
    (7, "CANON", '{M} ~is exposed to {I}', None),
    (7, "ALIAS", '{M} ~practices {I} at rate {R} per {U}, pattern {P}', None),
    (7, "ALIAS", '{M} ~keeps at {I} at rate {R} per {U}, pattern {P}', None),
    # ^8 Above/Cause: two DIFFERENT Ideas ----------------------------------------------------------
    (8, "CANON", '{I} ~triggers {J} to come to {M}', None),
    (8, "ALIAS", '{I} ~reminds {M} of {J}', None),
    (8, "ALIAS", '{I} ~made {M} think of {J}', None),
    (8, "ALIAS", '{I} ~makes {M} think of {J}', None),
    (8, "ALIAS", '{I} ~brings {J} to {M}', None),
    # ^9 Below/Effect: the trigger may be unknown, and then it is said as unknown ------------------
    (9, "CANON", '{J} ~is brought to {M} by {I}', None),
    (9, "CANON", '{J} ~is brought to {M} by an unknown trigger', None),
    (9, "ALIAS", '{J} ~came to {M} from {I}', None),
    (9, "ALIAS", '{J} ~came to {M} out of nowhere', None),
    (9, "ALIAS", '{J} ~popped into {M} from {I}', None),
    (9, "ALIAS", '{J} ~popped into {M}', None),
]
TEMPLATES = tuple(Template(index, noetic, tier, text, act)
                  for index, (noetic, tier, text, act) in enumerate(_RAW_TEMPLATES))

CANON_TEMPLATES = tuple(t for t in TEMPLATES if t.tier == "CANON")
ALIAS_TEMPLATES = tuple(t for t in TEMPLATES if t.tier == "ALIAS")

# The frame found first for a given content, in table order: this is the fixed twin wording.
FIRST_OF_NOETIC = {}
for _template in TEMPLATES:
    FIRST_OF_NOETIC.setdefault(_template.noetic, []).append(_template)

# --- Verb forms (surface agreement only; NO-MAP morphology, MAP.md section C) ---------------------------------
def _regular(third: str, base: str) -> dict:
    return {"3": third, "I": base, "you": base,
            "neg3": "does not " + base, "negI": "do not " + base, "negyou": "do not " + base}


def _past(past: str, base: str) -> dict:
    return {"3": past, "I": past, "you": past,
            "neg3": "did not " + base, "negI": "did not " + base, "negyou": "did not " + base}


VERBS = {
    "is": {"3": "is", "I": "am", "you": "are", "neg3": "is not", "negI": "am not", "negyou": "are not"},
    "has": _regular("has", "have"),
    "intakes": _regular("intakes", "intake"),
    "processes": _regular("processes", "process"),
    "stores": _regular("stores", "store"),
    "outputs": _regular("outputs", "output"),
    "resonates": _regular("resonates", "resonate"),
    "triggers": _regular("triggers", "trigger"),
    "speaks": _regular("speaks", "speak"),
    "rubs": _regular("rubs", "rub"),
    "breaks": _regular("breaks", "break"),
    "unpacks": _regular("unpacks", "unpack"),
    "reminds": _regular("reminds", "remind"),
    "practices": _regular("practices", "practice"),
    "struck": _past("struck", "strike"),
    "made": _past("made", "make"),
    "came": _past("came", "come"),
    # the widened ALIAS tier (owner ruling: the inside stays canonical, the outside varies)
    "likes": _regular("likes", "like"),
    "loves": _regular("loves", "love"),
    "appeals": _regular("appeals", "appeal"),
    "draws": _regular("draws", "draw"),
    "hates": _regular("hates", "hate"),
    "dislikes": _regular("dislikes", "dislike"),
    "disgusts": _regular("disgusts", "disgust"),
    "puts": _regular("puts", "put"),
    "turns": _regular("turns", "turn"),
    "shapes": _regular("shapes", "shape"),
    "takes": _regular("takes", "take"),
    "keeps": _regular("keeps", "keep"),
    "makes": _regular("makes", "make"),
    "brings": _regular("brings", "bring"),
    "hit": _past("hit", "hit"),
    "landed": _past("landed", "land"),
    "popped": _past("popped", "pop"),
}

# --- FUNCTION tier: the closed glue list (TRANSLATOR_SPEC section 3, item 3, plus what the
# sentence forms of that section need and nothing else) --------------------------------------------------------
FUNCTION_WORDS = (
    # the spec's own list
    "of use plus to make needs first then not there is no i checked you said i cannot tell "
    "combined into in registers for at rate per pattern degree side product helped by slowed by "
    "is a one of "
    # the forms the spec's own sentence list needs
    "and the an that what it cannot support need fact leads new subject topic are we still on "
    "fractal sequence nesting inside within unknown trigger named no word what"
).split()

PROTECTED_MARKER = "\u0000"


def _split_tokens(text: str):
    return re.findall(r"[A-Za-z]+(?:/[A-Za-z]+)?", text)


def _words_of(text: str):
    for token in _split_tokens(text):
        yield from token.lower().split("/")


def _build_frozen_words() -> frozenset:
    words = set()
    words.update(word.lower() for word in FUNCTION_WORDS)
    for template in TEMPLATES:
        words.update(_words_of(template.text))
    words.update(name.lower() for name in NOETIC_NAMES.values())
    for text in DEFINITIONS.values():          # a definition reference is written verbatim
        words.update(_words_of(text))
    words.update(DOMAINS.values())
    words.update(REGISTERS.values())
    words.update(name.lower() for name in DRIVES.values())
    words.update(ACTS)
    words.update(NUMBER_WORDS)
    words.update(UNITS)
    words.update(PATTERNS)
    for forms in VERBS.values():                # every surface form a frozen verb can take
        for form in forms.values():
            words.update(_words_of(form))
    words.update(("me", "am", "are", "do", "does", "did", "trigger", "unknown", "side", "product",
                  "helped", "slowed", "fact", "topic", "subject", "new", "fractal", "sequence",
                  "nesting", "inside", "within", "named", "size", "set", "registers", "register",
                  "noetic", "one", "all", "if", "so", "cause", "effect", "because", "therefore"))
    return frozenset(words)


FROZEN_WORDS = _build_frozen_words()


def invented_words(sentence: str, copied=()) -> tuple:
    """Every word in the sentence that is NOT in a frozen tier.

    `copied` names the strings that are copied byte for byte rather than read as words:
    double-quoted names, Omega names, declared Mind names, and the free slot words of a
    CLARIFY or a REFUSE_CLAIM reason. They are removed before the check, exactly as the
    grammar says names are not grammar (GRAMMAR_CCE_v0_1.md section 8).

    A capitalized token is also treated as an identifier (a declared Mind name is a name, not a
    word): identifiers are copied byte for byte and are never lexicon words (MAP.md section A).
    """
    text = sentence
    for item in sorted(copied, key=len, reverse=True):
        if not item:
            continue
        text = text.replace(item, " ")
    text = re.sub(r'"[^"]*"', " ", text)              # quoted names
    text = re.sub(r"Ω_[A-Za-z0-9_]+", " ", text)      # Omega names
    text = re.sub(r"\[[^\]]*\]", " ", text)           # a verbatim definition reference
    text = re.sub(r"\b[A-Z][A-Za-z0-9_]*\b", " ", text)   # declared Mind names
    bad = []
    for word in _words_of(text):
        if word not in FROZEN_WORDS:
            bad.append(word)
    return tuple(bad)


def lexicon_report(sentence: str, copied=()) -> dict:
    bad = invented_words(sentence, copied)
    return {"sentence": sentence, "invented": list(bad), "ok": not bad,
            "frozen_word_count": len(FROZEN_WORDS)}


def digest() -> str:
    """A sha256 over the frozen lexicon, so a change to it is visible (TRANSLATOR_SPEC section 11)."""
    import hashlib
    payload = "|".join([CCE_VERSION, FIXED_UNDETERMINED]
                       + ["%d:%s:%s" % (t.tid, t.tier, t.text) for t in TEMPLATES]
                       + sorted(FROZEN_WORDS))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


if __name__ == "__main__":  # pragma: no cover
    print("templates:", len(TEMPLATES), "canon:", len(CANON_TEMPLATES), "alias:", len(ALIAS_TEMPLATES))
    print("frozen words:", len(FROZEN_WORDS))
    print("lexicon digest:", digest())
