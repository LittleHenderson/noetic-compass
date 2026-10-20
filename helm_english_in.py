"""helm_english_in.py -- everyday English IN (fix H, 2026-10-18).

What it is, in plain words
--------------------------
A deterministic READER. It takes an everyday sentence about stock or recipes and restates it in the checked form
(CASContent) that the live loop already verifies. It is not a model, has no network, and uses stdlib only.

    "We have 50 flour, 30 sugar and 20 butter"      -> stocks
    "there's 12 cups of flour"                       -> a stock, with the unit words kept ("12 cups of flour")
    "we're out of water" / "no water"                -> an "absent" relation
    "can we bake bread?" / "how much bread can we make?"   -> topic Omega_Bread
    "bake a batch"                                   -> the topic the conversation is already on; if there is none,
                                                        a question ("which one?"), never a guess
    "we made 5 loaves from 10 flour and 8 water and ran out of flour"  -> a witnessed batch (teaching channel)

Rules it keeps
--------------
1. No new facts. The reader only restates the user's own words. It never infers an amount, never converts a unit,
   never fills a missing number, never picks a product the user did not name.
2. The brain knows 8 ingredients and 4 recipes. Everyday words map to those names through a small labeled table
   (EVERYDAY_NAMES, OUR_CONVENTION). Anything else is UNKNOWN and gets a plain question.
3. All or nothing. If any part of the sentence needs a question, the whole turn is a question and nothing is
   read into the checked form (so nothing is written).
4. Every reading is rendered to checked form with the canonical translator (language_v3/cce.py) and parsed back;
   the reading is used only if parse(render(C)) == C. The loop then checks it again, exactly as a checked-form turn.
5. Units: the number and the unit words are kept as said, in the receipt, so the voice can quote them.
   The same ingredient in two different units is a question, not a conversion.
6. STOCK_FRAME_REQUIRED (2026-10-19, after X-REAL c42, spec sheet 7.81). Naming an ingredient is not a stock
   statement. A stock or "none on hand" record is read ONLY when a stock frame holds the ingredient as its object:
   a possession frame ("we have", "we've got", "our pantry has"), an existential frame ("there is / there are"),
   a "we're out of / we ran out of / we don't have any" frame, or a sentence that is nothing but an inventory list
   ("50 flour, 30 sugar", "no water", "3 eggs left", "12 cups of flour on hand"). "Tom pulled Mary out of the
   water", "she ate 3 eggs" or "we used 2 cups of sugar" have no stock frame: the reader asks (NO_STOCK_FRAME) when
   the sentence is about our kitchen, and otherwise says there is nothing to save (status NOTHING_TO_SAVE).
   Every kept record carries its frame; the frames are rendered to a frame form and parsed back
   (render_frames / parse_frames), and the loop checks that form again before it writes a cube.

Word lists borrowed from the language line: the number words, hedge words and polarity words are the frozen
ALIAS-WIDE lists (ALIAS_WIDE_LEXICON_v0_1.json, which lexicon_v2 keeps unchanged; `lexicon_v2_agrees()` checks
that when lexicon_v2 can be imported). The ingredient and product words are NOT from the lexicon: they are the
brain's own names plus the labeled everyday table below.

Claim status: ENGINEERED-NOT-VALIDATED. It reads a closed set of sentence shapes about the brain's 8 ingredients
and 4 recipes. It is not a general English reader and makes no meaning claim beyond restating the user.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
LANG_V3 = os.path.join(HERE, "docs", "working", "noetic_council", "language_v3")
if os.path.isdir(LANG_V3) and LANG_V3 not in sys.path:
    sys.path.insert(0, LANG_V3)

try:
    import cce  # the canonical checked-form translator (render / parse / normalize)
except ImportError:  # pragma: no cover - the loop refuses every turn without it anyway
    cce = None

READER_VERSION = "helm_english_in v1.1 (2026-10-19, stock-frame rule)"
CLAIM_STATUS = "ENGINEERED-NOT-VALIDATED"

# ------------------------------------------------------------------------------------------------ frozen word lists
LEXICON_PATH = os.path.join(LANG_V3, "ALIAS_WIDE_LEXICON_v0_1.json")
with open(LEXICON_PATH, "rb") as _fh:
    _LEX_BYTES = _fh.read()
LEXICON_SHA256 = hashlib.sha256(_LEX_BYTES).hexdigest()
_LEX = json.loads(_LEX_BYTES.decode("utf-8"))
NUMBER_WORDS: Dict[str, str] = dict(_LEX["number_words"])          # one..ten, half
HEDGE_WORDS: List[str] = list(_LEX["hedge_words"])                   # if, unless, maybe, perhaps, ... could
POLARITY_WORDS: List[str] = list(_LEX["polarity_words"])             # not, no, never, without, absent, ...
BORROWED_LISTS = ("number_words", "hedge_words", "polarity_words")


def lexicon_v2_agrees() -> Optional[bool]:
    """True when lexicon_v2's merged lexicon has the same three lists; None when lexicon_v2 cannot be imported
    (it needs sdg_bridge_v2 on the path, see language_v3/PROVENANCE.md)."""
    try:
        import lexicon_v2  # noqa: WPS433 (deliberately lazy)
    except Exception:
        return None
    merged = lexicon_v2.merged_lexicon()
    return all(merged[k] == _LEX[k] for k in BORROWED_LISTS)


# ------------------------------------------------------------------------------------------------ the labeled names
#: OUR_CONVENTION: everyday words -> the brain's own names (helm_brain_canonical.DEFAULT_BINDING). Plural forms are
#: listed one by one; nothing else is matched. A word not in this table is UNKNOWN.
EVERYDAY_INGREDIENTS: Dict[str, str] = {
    "flour": "Flour", "water": "Water", "sugar": "Sugar", "butter": "Butter", "milk": "Milk",
    "egg": "Egg", "eggs": "Egg", "yeast": "Yeast", "salt": "Salt",
}
EVERYDAY_PRODUCTS: Dict[str, str] = {
    "bread": "Bread", "breads": "Bread", "loaf": "Bread", "loaves": "Bread",
    "frosting": "Frosting", "starter": "Starter", "starters": "Starter",
    "meringue": "Meringue", "meringues": "Meringue",
}
EVERYDAY_NAMES = {"ingredients": EVERYDAY_INGREDIENTS, "products": EVERYDAY_PRODUCTS,
                  "label": "OUR_CONVENTION everyday names for the brain's 8 cells and 4 recipes"}
COUNTABLE = {"Egg"}
SPOKEN = {"Egg": "eggs"}  # how a name is said in a list or a "how many" question

UNIT_FORMS = {
    "cup": "cup", "cups": "cup", "lb": "pound", "lbs": "pound", "pound": "pound", "pounds": "pound",
    "kg": "kilogram", "kgs": "kilogram", "kilo": "kilogram", "kilos": "kilogram", "kilogram": "kilogram",
    "kilograms": "kilogram", "g": "gram", "gram": "gram", "grams": "gram", "oz": "ounce", "ounce": "ounce",
    "ounces": "ounce", "tbsp": "tablespoon", "tablespoon": "tablespoon", "tablespoons": "tablespoon",
    "tsp": "teaspoon", "teaspoon": "teaspoon", "teaspoons": "teaspoon", "l": "liter", "liter": "liter",
    "liters": "liter", "litre": "liter", "litres": "liter", "ml": "milliliter", "milliliter": "milliliter",
    "milliliters": "milliliter", "quart": "quart", "quarts": "quart", "pint": "pint", "pints": "pint",
    "gallon": "gallon", "gallons": "gallon", "stick": "stick", "sticks": "stick", "packet": "packet",
    "packets": "packet", "pack": "pack", "packs": "pack", "bag": "bag", "bags": "bag", "can": "can",
    "cans": "can", "jar": "jar", "jars": "jar", "box": "box", "boxes": "box", "carton": "carton",
    "cartons": "carton", "dozen": "dozen", "pinch": "pinch", "pinches": "pinch", "dash": "dash",
    "dashes": "dash", "unit": "", "units": "", "batch": "batch", "batches": "batch",
}
_UNIT_ALT = "|".join(sorted((re.escape(u) for u in UNIT_FORMS), key=len, reverse=True))

#: Counted things that are not stock (times, people, steps). Their numbers are left alone and listed as ignored.
IGNORED_COUNT_NOUNS = {"minute", "minutes", "hour", "hours", "day", "days", "week", "weeks", "pm", "am",
                       "degree", "degrees", "people", "person", "guests", "guest", "times", "time", "steps",
                       "step", "o'clock", "oclock", "percent", "kids", "friends"}
ADJECTIVES_SKIPPED = {"fresh", "large", "big", "small", "whole", "plain", "cold", "warm", "soft", "raw", "fine",
                      "coarse", "regular", "extra-large", "medium"}
FUNCTION_WORDS = {"and", "or", "but", "of", "in", "on", "to", "for", "with", "from", "the", "a", "an", "we", "it",
                  "that", "this", "is", "are", "was", "be", "so", "left", "total", "now", "then", "too", "also",
                  "can", "could", "will", "would", "should", "do", "does", "make", "bake", "here", "there",
                  "please", "thanks", "ok", "okay", "right", "on", "hand", "available", "at", "by", "up", "about"}
RELATIVE_WORDS = {"more", "extra", "another", "additional"}

NUM_RX = re.compile(r"(?<![\w.,/])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?(?:/\d+)?|\.\d+)(?![\w/])")
NUMWORD_RX = re.compile(r"(?<![\w'])(%s)(?![\w'])" % "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)))
TAIL_RX = re.compile(
    r"\s*(?:(?P<unit>%s)(?![\w])\.?\s*)?(?:(?P<of>of)\s+)?(?:(?:the|our|my|some|all|of)\s+)?"
    r"(?P<w1>[a-zω_][\w'ω-]*)?(?:\s+(?P<w2>[a-z][\w'-]*))?" % _UNIT_ALT)

CONTRACTIONS = [
    (r"\bthere's\b", "there is"), (r"\bthere're\b", "there are"), (r"\bwe're\b", "we are"),
    (r"\bwe've\b", "we have"), (r"\bi've\b", "i have"), (r"\byou've\b", "you have"), (r"\bthey've\b", "they have"),
    (r"\bwe'd\b", "we would"), (r"\bdon't\b", "do not"), (r"\bdoesn't\b", "does not"), (r"\bdidn't\b", "did not"),
    (r"\bhaven't\b", "have not"), (r"\bhasn't\b", "has not"), (r"\bisn't\b", "is not"), (r"\baren't\b", "are not"),
    (r"\bcan't\b", "cannot"), (r"\bwon't\b", "will not"), (r"\bit's\b", "it is"), (r"\bwhat's\b", "what is"),
    (r"\bi'm\b", "i am"), (r"\blet's\b", "let us"), (r"\bthat's\b", "that is"), (r"\bwasn't\b", "was not"),
    (r"\bweren't\b", "were not"), (r"\bhow's\b", "how is"),
]
Q_START = {"can", "could", "how", "what", "do", "does", "did", "is", "are", "will", "would", "should", "shall",
           "may", "which", "when", "where", "why", "have", "has"}
STOCK_VERB_RX = re.compile(
    r"(?<!do )(?<!did )(?<!if )(?<!does )\b(?:we|i|you|they)\s+(?:have|has|had|got|have got|still have)\b"
    r"(?!\s+(?:to|made|baked|produced|been)\b)|(?<!is )\bthere\s+(?:is|are)\b|\bon hand\b|\bin stock\b|"
    r"\bin the (?:pantry|cupboard|fridge|kitchen)\b|\bleft\b")
REQUEST_RX = re.compile(r"\b(?:make|makes|making|bake|baking|whip|whip up|cook|produce|get|calculate|figure out|"
                        r"work out|run|start|try|do|enough)\b|\bwhat about\b|\bhow about\b|\bhow (?:much|many)\b")
BATCH_REF_RX = re.compile(r"\b(?:a|another|one more|the|next) batch\b|\bhow (?:much|many) can we "
                          r"(?:make|bake|get|produce)\b|\bwhat can we (?:make|bake)\b")
UNKNOWN_PRODUCT_RX = re.compile(
    r"\b(?:bake|baking|cook|cooking|whip up)\s+(?:us\s+|me\s+)?(?:some\s+|a\s+|an\s+|any\s+|the\s+|more\s+|"
    r"another\s+)?(?P<n1>[a-z][\w'-]*)|\bhow (?:much|many) (?P<n2>[a-z][\w'-]*) (?:can|could|will|would) we "
    r"(?:make|bake|get|produce)\b|\b(?:make|making)\s+(?:us\s+|me\s+)?(?:some\s+|a\s+|an\s+|any\s+|the\s+|"
    r"more\s+)?(?P<n3>[a-z][\w'-]*)")
PANTRY_RX = re.compile(r"\b(?:pantry|in stock|on hand|ingredients?|recipes?|oven|kitchen)\b")
COOK_VERB_RX = re.compile(r"\b(?:bake|baked|baking|cook|cooked|whip|whipped)\b")
BATCH_REPORT_RX = re.compile(r"\b(?:we|i)\s+(?:just\s+)?(?:made|baked|produced|got|whipped up|whipped)\s+(?=\S)")
RAN_OUT_RXS = (  # run one by one, so "we ran out of flour" is never eaten by the "X ran out" shape
    re.compile(r"\b(?:ran out of|run out of|out of|used up(?: all)?(?: of)?)\s+(?:the\s+|our\s+|all the\s+)?"
               r"(?P<w>[a-z][\w'-]*)"),
    re.compile(r"\b(?:the\s+|our\s+)?(?P<w>[a-z][\w'-]*)\s+(?:ran out|was the first to run out|went first|"
               r"was used up)\b"),
    re.compile(r"\b(?:ran out of|run out of|out of)\s+(?:the\s+)?[a-z][\w'-]*\s+(?:and|&)\s+(?:the\s+)?"
               r"(?P<w>[a-z][\w'-]*)"),
)
ABSENT_RXS = (  # (pattern, strong?) run one by one; a strong shape names the missing thing for sure
    (re.compile(r"\b(?P<kind>out of|no more|none of the|without|zero)\s+(?:the\s+|any\s+|our\s+|more\s+)?"
                r"(?P<w>[a-z][\w'-]*)"), True),
    (re.compile(r"\b(?P<kind>no)\s+(?:the\s+|any\s+|our\s+|more\s+)?(?P<w>[a-z][\w'-]*)"), False),
    (re.compile(r"\b(?:do|does|did) not have any\s+(?P<w>[a-z][\w'-]*)"), True),
    (re.compile(r"\bhave not got any\s+(?P<w>[a-z][\w'-]*)"), True),
    (re.compile(r"\b(?:the\s+|our\s+)?(?P<w>[a-z][\w'-]*)\s+(?:is|are)\s+(?:all\s+)?(?:gone|used up|finished)\b"),
     True),
    (re.compile(r"\b(?:the\s+|our\s+)?(?P<w>[a-z][\w'-]*)\s+ran out\b"), True),
)
APPROX_BEFORE_RX = re.compile(r"(?:\babout|\baround|\broughly|\bapproximately|\bapprox\.?|\bnearly|\balmost|\bover|"
                              r"\bunder|\bmore than|\bless than|\bat least|\bat most|\bup to|\bmaybe|\bperhaps|~)\s*$")
APPROX_AFTER_RX = re.compile(r"^\s*(?:or so|-?ish|give or take|or more|or less|tops)\b")
HYPOTHETICAL_EXTRA = ("suppose", "supposing", "imagine", "would", "what if")
STATED_RECIPE_RX = re.compile(r"\b(?:needs|need|takes|take|requires|require|calls for|uses|use)\b")
CONVERT_RX = re.compile(r"\b(?:convert|conversion)\b|\bhow many (?:%s)\b|\b(?:in|into|to) (?:%s)\s*\??\s*$"
                        % (_UNIT_ALT, _UNIT_ALT))
SEP_RX = re.compile(r",|;|\band\b|\bbut\b|\bplus\b|&|\bwith\b|\bfrom\b|\busing\b")

# ------------------------------------------------------------------------------------------------ stock frames (rule 6)
#: Words that may stand around the amounts of an inventory list without changing what it says.
LIST_WORDS = {"and", "plus", "also", "now", "still", "only", "just", "exactly", "currently", "ok", "okay", "so",
              "oh", "well", "update", "stock", "inventory", "pantry", "total", "in", "all", "together", "then",
              "here", "right", "yes", "yeah", "yep", "the", "of", "our", "my", "some", "any", "no", "more", "both",
              "about", "too", "as", "at", "moment", "today", "&", "anymore"}
#: A label in front of a list ("Stock check: 4 cups of sugar", "Pantry update: no milk") is part of the list frame.
LABEL_RX = re.compile(r"^\s*(?:(?:stock|inventory|pantry|kitchen|fridge|check|update|count|tally|supplies|current|"
                      r"today's|our|the|list|of)\s*)+:")
#: State phrases that make a bare list a stock list ("3 eggs left", "12 cups of flour on hand").
STATE_RX = re.compile(r"\b(?:on hand|in stock|left|remaining|available|in the (?:pantry|cupboard|fridge|kitchen)|"
                      r"right now|at the moment|at all|any ?more|for now)\b")
#: Possession and existential heads. The subject comes first (a statement, never "do we have" / "have we got").
HEAD_RX = re.compile(
    r"\b(?P<head>(?:(?:we|i)|(?:our|the|my)\s+(?:pantry|kitchen|fridge|cupboard|stock|inventory|shelf))"
    r"(?:\s+(?:now|still|also|only|just|currently|already|actually|really|all))*"
    r"\s+(?:have got|have|has|got)(?:\s+(?:still|only|just|now|got))*"
    r"|there\s+(?:is|are)(?:\s+(?:still|now|only|just|currently|also))*)\b"
    r"(?!\s+(?:to|made|baked|produced|been|used|added|bought|eaten|had)\b)")
#: Words that, right before a head, turn it into a question, a condition or someone else's report.
HEAD_BLOCKERS = {"do", "does", "did", "have", "has", "had", "can", "could", "will", "would", "should", "shall", "may",
                 "might", "must", "if", "when", "whenever", "once", "after", "before", "until", "unless", "since",
                 "because", "what", "how", "is", "are", "was", "were", "wish", "hope", "think", "guess", "suppose",
                 "imagine", "said", "says", "thought", "told", "tells", "know", "knew", "whether", "that", "where",
                 "why", "who", "not", "never"}
#: "we're out of", "we ran out of", "we've run out of", "I'm fresh out of", "the pantry is out of", "we're without".
OUT_HEAD_RX = re.compile(r"(?:^|\s)(?:we|i|(?:our|the)\s+(?:pantry|kitchen|fridge|cupboard))"
                         r"(?:\s+(?:are|am|is|have|has))?(?:\s+(?:now|all|completely|totally|clean|fresh|just|"
                         r"already|still|been|run|ran|running|gone|basically|pretty much))*\s*$")
NEG_HEAD_RX = re.compile(r"(?:^|\s)(?:we|i|(?:our|the)\s+(?:pantry|kitchen|fridge|cupboard))\s*$")
#: Clues that a sentence is about our own kitchen (then an unframed amount is a question, not nothing).
KITCHEN_CUE_RX = re.compile(
    r"\b(?:we|i|us|our|ours|my|me|you|your|pantry|in stock|on hand|ingredients?|recipes?|oven|kitchen|batch|"
    r"bake|baked|baking|cook|cooked|cooking|whip|whipped)\b|^(?:let us|add|mix|use|put|pour|stir|combine|whisk|"
    r"beat|melt|heat|knead|sift|measure|fold|buy|get|grab|take|need|bring|pass|give)\b")
FRAME_FORM_RX = re.compile(r'(Stock|Absent) frame ([A-Z_]+) "([^"]*)": Ω_([A-Za-z]+)\.')


def _residue_ok(text: str) -> bool:
    """True when `text` holds only list words and punctuation (amounts and frames already blanked out)."""
    return all(w in LIST_WORDS for w in re.findall(r"[a-z][\w'-]*|\d+", text))


def _blank(text: str, spans: Sequence[Tuple[int, int]], lo: int = 0) -> str:
    """`text` (starting at clause offset lo) with the given clause spans replaced by spaces."""
    chars = list(text)
    for a, b in spans:
        for i in range(max(a, lo), min(b, lo + len(chars))):
            chars[i - lo] = " "
    return "".join(chars)


def _segment_start(clause: str, pos: int) -> int:
    last = 0
    for m in SEP_RX.finditer(clause, 0, pos):
        last = m.end()
    return last


def _segment_end(clause: str, pos: int) -> int:
    m = SEP_RX.search(clause, pos)
    return m.start() if m else len(clause)


def _list_frame(clause: str, spans: Sequence[Tuple[int, int]], is_q: bool) -> Optional[Dict[str, str]]:
    """The whole clause is an inventory list: amounts, 'no X', state words and list words only."""
    if is_q:
        return None
    blanked = _blank(clause, spans)
    label = LABEL_RX.match(blanked)
    if label:
        blanked = " " * label.end() + blanked[label.end():]
    state = STATE_RX.search(blanked)
    blanked = STATE_RX.sub(" ", blanked)
    if _residue_ok(blanked):
        return {"rule": "LIST", "words": (state.group(0) if state else
                                          (label.group(0).rstrip(":").strip() if label else ""))}
    return None


def _head_frame(clause: str, pos: int, spans: Sequence[Tuple[int, int]]) -> Optional[Dict[str, str]]:
    """A possession / existential head before clause position `pos` that holds the thing at `pos` as its object:
    the words between the head and `pos` are list words, amounts or other list items only."""
    best = None
    for m in HEAD_RX.finditer(clause, 0, pos):
        before = re.findall(r"[a-z][\w'-]*", clause[_segment_start(clause, m.start()):m.start()])
        if before and before[-1] in HEAD_BLOCKERS:
            continue
        if any(w not in LIST_WORDS for w in before):
            continue                                   # "Tom said we have ...": someone else's report
        gap = _blank(clause[m.end():pos], spans, m.end())
        gap = STATE_RX.sub(" ", gap)
        if _residue_ok(gap):
            best = m
    if best is None:
        return None
    head = re.sub(r"\s+", " ", best.group("head")).strip()
    return {"rule": "EXISTENTIAL" if head.startswith("there") else "POSSESSION", "words": head}


def stock_frame(clause: str, start: int, spans: Sequence[Tuple[int, int]], is_q: bool) -> Optional[Dict[str, str]]:
    """The stock frame for an amount at `start` in `clause`, or None. A question only keeps a statement-order head."""
    return _head_frame(clause, start, spans) or _list_frame(clause, spans, is_q)


def absent_frame(clause: str, start: int, end: int, shape: int, spans: Sequence[Tuple[int, int]],
                 is_q: bool) -> Optional[Dict[str, str]]:
    """The frame that makes an absence hit (ABSENT_RXS[shape] at start..end) a 'none on hand' statement, or None."""
    seg_lo = _segment_start(clause, start)
    lead = clause[seg_lo:start]
    hit = clause[start:end]
    if shape == 0 and (hit.startswith("out of") or hit.startswith("without")):
        m = OUT_HEAD_RX.search(lead)
        if m and _residue_ok(lead[:m.start()]):
            return {"rule": "OUT_OF", "words": (lead[m.start():] + hit.split()[0] + " " + hit.split()[1]).strip()
                    if hit.startswith("out of") else (lead[m.start():] + "without").strip()}
        if hit.startswith("without"):
            return None
    if shape in (2, 3):                                # "we don't have any X", "we haven't got any X"
        m = NEG_HEAD_RX.search(lead)
        if m and _residue_ok(lead[:m.start()]) and not is_q:
            return {"rule": "NONE_HELD", "words": (lead[m.start():] + hit.rsplit(" ", 1)[0]).strip()}
        return None
    if shape in (4, 5):                                # "the water is all gone", "the water ran out"
        tail = clause[end:_segment_end(clause, end)]
        if _residue_ok(lead) and _residue_ok(STATE_RX.sub(" ", tail)) and not is_q:
            return {"rule": "GONE", "words": hit.split(" ", 1)[1] if hit.startswith(("the ", "our ")) else hit}
        return None
    if not hit.startswith("out of"):                   # "no X", "no more X", "zero X", "none of the X"
        f = _head_frame(clause, start, spans)
        if f:
            return f
    return _list_frame(clause, spans, is_q)


def render_frames(frames: Sequence[Dict[str, str]]) -> str:
    """The frame form: one sentence per kept record, e.g. 'Stock frame POSSESSION "we have": Ω_Flour.'"""
    return " ".join('%s frame %s "%s": Ω_%s.' % ("Absent" if f["kind"] == "absent" else "Stock", f["rule"],
                                                f["words"], f["name"]) for f in frames)


def parse_frames(text: str) -> List[Dict[str, str]]:
    out = []
    for m in FRAME_FORM_RX.finditer(text or ""):
        out.append({"kind": "absent" if m.group(1) == "Absent" else "stock", "rule": m.group(2),
                    "words": m.group(3), "name": m.group(4)})
    if FRAME_FORM_RX.sub("", text or "").strip():
        raise ValueError("frame form has text that is not a frame sentence")
    return out


def check_frame_form(reading: Dict[str, Any]) -> Tuple[bool, str]:
    """Rule 6, checked again from the reading alone (the loop calls this before any cube is written): the frame
    form parses back to the reading's frames, every stock and absence has exactly one frame, and every frame's words
    are the user's own words."""
    frames = reading.get("frames") or []
    try:
        back = parse_frames(reading.get("frame_form") or "")
    except ValueError as exc:
        return False, str(exc)
    if [dict(f) for f in back] != [{k: f[k] for k in ("kind", "rule", "words", "name")} for f in frames]:
        return False, "frame form does not round-trip"
    want = sorted([("stock", s["name"]) for s in reading.get("stocks") or []] +
                  [("absent", a["name"]) for a in reading.get("absent") or []])
    have = sorted((f["kind"], f["name"]) for f in frames)
    if want != have:
        return False, "a stock or absence has no stock frame"
    norm = reading.get("normalized") or ""
    for f in frames:
        if f["words"] and f["words"] not in re.sub(r"\s+", " ", norm):
            return False, "frame words %r are not the user's words" % f["words"]
    return True, "ok"


# ------------------------------------------------------------------------------------------------ small helpers
def normalize_text(text: str) -> str:
    t = (text or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace("Ω", "ω")  # keep checked-form names as one token after lowercasing
    t = t.lower()
    for rx, rep in CONTRACTIONS:
        t = re.sub(rx, rep, t)
    return re.sub(r"[ \t]+", " ", t).strip()


def split_clauses(text: str) -> List[Tuple[str, bool]]:
    """Sentences and dash-separated clauses, each with 'is it a question'."""
    out = []
    for part in re.split(r"(?<=[.!?;])\s+|\s+[—–]\s+|\s*—\s*|\s+--?\s+", text):
        p = part.strip()
        if not p:
            continue
        words = re.findall(r"[a-z']+", p)
        is_q = p.endswith("?") or (bool(words) and words[0] in Q_START)
        out.append((p.rstrip(".!;").strip(), is_q))
    return out


def canonical_amount(said: str) -> Optional[str]:
    """The checked-form amount text for what the user said, or None if it is not a number cce accepts."""
    raw = NUMBER_WORDS.get(said, said).replace(",", "")
    if cce is None:
        return None
    try:
        return cce.num(raw)
    except Exception:
        return None


def say_name(name: str) -> str:
    return SPOKEN.get(name, name.lower())


def say_list(names: Sequence[str]) -> str:
    words = [say_name(n) for n in names]
    if len(words) <= 1:
        return "".join(words)
    if len(words) == 2:
        return "%s or %s" % tuple(words)
    return ", ".join(words[:-1]) + ", or " + words[-1]


def say_list_and(names: Sequence[str]) -> str:
    words = [say_name(n) for n in names]
    if len(words) <= 1:
        return "".join(words)
    if len(words) == 2:
        return "%s and %s" % tuple(words)
    return ", ".join(words[:-1]) + ", and " + words[-1]


def same_unit(a: Optional[str], b: Optional[str]) -> bool:
    """Spelling variants of one unit are the same unit ('lbs' and 'pounds'); this is not a conversion."""
    return UNIT_FORMS.get(a or "", a or "") == UNIT_FORMS.get(b or "", b or "")


# ------------------------------------------------------------------------------------------------ the reader
class _Reading:
    def __init__(self, text: str, ingredients: Sequence[str], products: Sequence[str]):
        self.text = text
        self.ingredient_words = {w: n for w, n in EVERYDAY_INGREDIENTS.items() if n in ingredients}
        self.product_words = {w: n for w, n in EVERYDAY_PRODUCTS.items() if n in products}
        self.ingredients = list(ingredients)
        self.products = list(products)
        self.stocks: List[Dict[str, Any]] = []
        self.absent: List[Dict[str, Any]] = []
        self.topics: List[Dict[str, Any]] = []
        self.witness: Optional[Dict[str, Any]] = None
        self.ignored: List[str] = []
        self.rules: List[str] = []
        self.clarifications: List[Dict[str, Any]] = []
        self.frames: List[Dict[str, str]] = []          # rule 6: the stock frame of every kept record
        self.unframed: List[Dict[str, Any]] = []        # rule 6: amounts / absences said with no stock frame

    def ask(self, code: str, **slots: Any) -> None:
        if slots.get("item") in {say_name(n) for n in COUNTABLE}:
            slots["countable"] = True                 # "how many eggs", never "how much eggs"
        self.clarifications.append({"code": code, "slots": {k: v for k, v in slots.items() if v is not None}})

    def known(self, word: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """('ingredient' | 'product' | None, brain name) for one everyday word."""
        if not word:
            return None, None
        if word in self.ingredient_words:
            return "ingredient", self.ingredient_words[word]
        if word in self.product_words:
            return "product", self.product_words[word]
        return None, None


def _numbers(clause: str) -> List[Tuple[int, int, str]]:
    out = [(m.start(1), m.end(1), m.group(1)) for m in NUM_RX.finditer(clause)]
    out += [(m.start(1), m.end(1), m.group(1)) for m in NUMWORD_RX.finditer(clause)]
    return sorted(out)


def _quantity(rd: _Reading, clause: str, start: int, end: int, said: str) -> Dict[str, Any]:
    """Read the words after one number: unit, 'of', the thing counted. Returns a quantity record."""
    m = TAIL_RX.match(clause, end)
    unit = m.group("unit") if m else None
    w1 = m.group("w1") if m else None
    w2 = m.group("w2") if m else None
    q: Dict[str, Any] = {"said": said, "unit": unit or "", "start": start, "end": m.end() if m else end,
                         "kind": None, "name": None, "noun_words": None}
    if w1 in ADJECTIVES_SKIPPED and w2:
        w1, w2 = w2, None
    kind, name = rd.known(w1)
    if kind:
        q.update(kind=kind, name=name, noun_words=w1)
        if kind == "product" and w2 and rd.known(w2)[0] == "ingredient":   # "bread flour": a different flour
            q.update(kind="unknown", name=None, noun_words="%s %s" % (w1, w2))
        elif w2 and m and kind == "ingredient":
            q["end"] = m.end("w1")
        elif m and w1:
            q["end"] = m.end("w1")
        return q
    if w1 in IGNORED_COUNT_NOUNS:
        q.update(kind="ignored", noun_words=w1)
        q["end"] = m.end("w1")
        return q
    if w1 in RELATIVE_WORDS:
        q.update(kind="relative", noun_words=(w2 or ""))
        k2, n2 = rd.known(w2)
        q["name"] = n2
        return q
    if w1 is None or w1 in FUNCTION_WORDS or not re.match(r"[a-z]", w1 or ""):
        q.update(kind="no_noun")
        if m and m.group("unit"):
            q["end"] = m.end("unit")
        return q
    k2, n2 = rd.known(w2)
    q.update(kind="unknown", noun_words=("%s %s" % (w1, w2)) if k2 == "ingredient" else w1)
    q["end"] = m.end("w2") if k2 == "ingredient" else m.end("w1")
    return q


def _qty_words(clause: str, q: Dict[str, Any]) -> str:
    return clause[q["start"]:q["end"]].strip()


def _prefix(clause: str, start: int) -> str:
    """Text between the previous separator (comma, 'and', 'but', ...) and this number."""
    last = 0
    for m in SEP_RX.finditer(clause, 0, start):
        last = m.end()
    return clause[last:start]


def _hedged(clause: str, is_q: bool) -> Optional[str]:
    words = set(re.findall(r"[a-z']+", clause))
    for h in HEDGE_WORDS:
        if h == "could" and (is_q or clause.startswith("could ")):
            continue
        if h in words:
            return h
    for h in HYPOTHETICAL_EXTRA:
        if re.search(r"\b%s\b" % re.escape(h), clause):
            return h
    return None


def _scan_quantities(rd: _Reading, clause: str) -> List[Dict[str, Any]]:
    qs = []
    taken_end = -1
    for start, end, said in _numbers(clause):
        if start < taken_end:
            continue
        q = _quantity(rd, clause, start, end, said)
        if said in NUMBER_WORDS and q["kind"] not in ("ingredient", "product") and not q["unit"]:
            continue            # 'which one', 'one of us': a number word only counts before a known thing or unit
        q["words"] = _qty_words(clause, q)
        q["prefix"] = _prefix(clause, start)
        q["after"] = clause[q["end"]:q["end"] + 20]
        qs.append(q)
        taken_end = q["end"]
    return qs


def _claimed(rd: _Reading, t: str) -> bool:
    words = set(re.findall(r"[a-z][\w'-]*", t))
    if words & set(rd.ingredient_words) or words & set(rd.product_words):
        return True
    if PANTRY_RX.search(t) or COOK_VERB_RX.search(t):
        return True
    if re.search(r"(?:\d|\b(?:%s)\b)\s*(?:%s)(?![\w])" % ("|".join(NUMBER_WORDS), _UNIT_ALT), t):
        return True
    if BATCH_REF_RX.search(t) or re.search(r"\bhow (?:much|many) [a-z]+ (?:can|could) we (?:make|bake)\b", t):
        return True
    return False


def _read_batch(rd: _Reading, t: str, m: "re.Match[str]") -> None:
    """A witnessed batch: what was made, from what, and what ran out first. Every part must be said."""
    rd.rules.append("BATCH_REPORTED")
    made_q = None
    nums = _numbers(t)
    after = [n for n in nums if n[0] >= m.end()]
    if after and after[0][0] - m.end() <= 1:
        made_q = _quantity(rd, t, after[0][0], after[0][1], after[0][2])
        made_q["words"] = _qty_words(t, made_q)
    product = None
    made_unit = ""
    if made_q is not None:
        if made_q["kind"] == "product":
            product = made_q["name"]
            made_unit = made_q["unit"] or ("" if made_q["noun_words"] in ("bread",) else made_q["noun_words"])
        elif made_q["kind"] in ("unknown",):
            rd.ask("UNKNOWN_PRODUCT", name=made_q["noun_words"], known=say_list_and(rd.products))
            return
        else:
            # "we made 5 batches" / "we made 5" -> the product was not named in the counted words
            for w, n in rd.product_words.items():
                if re.search(r"\b%s\b" % w, t[made_q["end"]:made_q["end"] + 30]):
                    product, made_unit = n, made_q["unit"]
                    break
    if product is None:
        named = sorted({n for w, n in rd.product_words.items() if re.search(r"\b%s\b" % w, t)})
        if made_q is None:
            rd.ask("BATCH_NEEDS_MADE", product=say_name(named[0]) if len(named) == 1 else None)
            return
        if len(named) == 1:
            product = named[0]
        else:
            rd.ask("BATCH_NEEDS_PRODUCT", words=made_q["words"])
            return
    if made_q is None:
        rd.ask("BATCH_NEEDS_MADE", product=say_name(product))
        return
    made_amount = canonical_amount(made_q["said"])
    if made_amount is None:
        rd.ask("ROUND_TRIP_FAILED")
        return
    stock_before: Dict[str, Dict[str, Any]] = {}
    for q in _scan_quantities(rd, t):
        if q["start"] == made_q["start"]:
            continue
        if APPROX_BEFORE_RX.search(q["prefix"]) or APPROX_AFTER_RX.match(q["after"]):
            rd.ask("APPROXIMATE", words=q["words"], item=say_name(q["name"]) if q["name"] else None)
            return
        if q["kind"] == "ingredient":
            amt = canonical_amount(q["said"])
            prev = stock_before.get(q["name"])
            if prev is not None and (prev["amount"] != amt or not same_unit(prev["unit"], q["unit"])):
                code = "CONVERSION_REFUSED" if not same_unit(prev["unit"], q["unit"]) else "CONTRADICTION"
                rd.ask(code, item=say_name(q["name"]), a=prev["words"], b=q["words"])
                return
            stock_before[q["name"]] = {"name": q["name"], "amount": amt, "said": q["said"], "unit": q["unit"],
                                       "words": q["words"]}
        elif q["kind"] == "unknown":
            rd.ask("UNKNOWN_INGREDIENT", name=q["noun_words"], known=say_list_and(rd.ingredients))
            return
        elif q["kind"] == "ignored":
            rd.ignored.append(q["words"])
    if not stock_before:
        rd.ask("BATCH_NEEDS_STOCK", product=say_name(product))
        return
    ran = []
    hits = sorted((r.start(), r.group("w"), i) for i, rx in enumerate(RAN_OUT_RXS) for r in rx.finditer(t))
    for _pos, word, shape in hits:
        kind, name = rd.known(word)
        if kind == "ingredient" and name not in ran:
            ran.append(name)
        elif kind is None and shape == 0 and word not in FUNCTION_WORDS:
            rd.ask("UNKNOWN_INGREDIENT", name=word, known=say_list_and(rd.ingredients))
            return
    if not ran:
        rd.ask("BATCH_NEEDS_RAN_OUT")
        return
    if len(ran) > 1:
        rd.ask("BATCH_TWO_RAN_OUT", a=say_name(ran[0]), b=say_name(ran[1]))
        return
    rd.witness = {"product": product, "made": made_amount, "made_said": made_q["said"], "made_unit": made_unit,
                  "made_words": made_q["words"], "ran_out": ran[0],
                  "stock_before": {k: v["amount"] for k, v in stock_before.items()},
                  "stock_words": stock_before}


def _read_clause(rd: _Reading, clause: str, is_q: bool, last_topic: Optional[str]) -> None:
    qs = _scan_quantities(rd, clause)
    has_stock_verb = bool(STOCK_VERB_RX.search(clause))
    hedge = _hedged(clause, is_q)
    product_words_here = [(m.start(), m.group(0)) for w in rd.product_words
                          for m in re.finditer(r"\b%s\b" % re.escape(w), clause)]
    consumed = [(q["start"], q["end"]) for q in qs]
    hits = sorted((m.start(), m.end(), m.group("w"), strong, m.groupdict().get("kind"), shape)
                  for shape, (rx, strong) in enumerate(ABSENT_RXS) for m in rx.finditer(clause))
    # rule 6: the spans a list frame may skip over -- every amount and every 'none of X' said about an ingredient
    list_spans = list(consumed) + [(h[0], h[1]) for h in hits if rd.known(h[2])[0] == "ingredient"]

    # stated recipe: "bread needs 2 flour", "to make bread, use 2 flour and 1 water"
    if product_words_here and qs and STATED_RECIPE_RX.search(clause) and any(q["kind"] == "ingredient" for q in qs):
        rd.ask("STATED_RECIPE")
        return

    # 1. quantities
    for q in qs:
        if q["kind"] == "ignored":
            rd.ignored.append(q["words"])
            continue
        if q["kind"] == "product":
            if is_q or REQUEST_RX.search(clause):
                rd.ignored.append(q["words"])           # "bake 2 loaves?" -> the request size is not stock
                continue
            rd.ask("PRODUCT_AS_STOCK", name=q["noun_words"], known=say_list_and(rd.ingredients))
            continue
        if q["kind"] == "unknown":
            rd.ask("UNKNOWN_INGREDIENT", name=q["noun_words"], known=say_list_and(rd.ingredients))
            continue
        if q["kind"] == "no_noun":
            if q["unit"] or has_stock_verb:
                rd.ask("NO_INGREDIENT_NAMED", words=q["words"] or q["said"])
            else:
                rd.ignored.append(q["said"])
            continue
        item = say_name(q["name"]) if q["name"] else None
        if q["kind"] == "relative" or re.search(r"\b(?:add|added|adding|another|extra|more|top up)\b", q["prefix"]):
            rd.ask("RELATIVE_AMOUNT", words=q["words"], item=item)
            continue
        if APPROX_BEFORE_RX.search(q["prefix"]) or APPROX_AFTER_RX.match(q["after"]):
            hedge_word = (APPROX_BEFORE_RX.search(q["prefix"]) or APPROX_AFTER_RX.match(q["after"])).group(0).strip()
            rd.ask("APPROXIMATE", words=q["words"], item=item, hedge=hedge_word)
            continue
        if re.search(r"\b(?:%s|cannot)\b" % "|".join(POLARITY_WORDS), q["prefix"]):
            rd.ask("NEGATED_AMOUNT", words=q["words"], item=item)
            continue
        if hedge:
            rd.ask("WHAT_IF", words=q["words"], item=item, hedge=hedge)
            continue
        if is_q and not has_stock_verb:
            rd.ask("WHAT_IF", words=q["words"], item=item)
            continue
        amount = canonical_amount(q["said"])
        if amount is None:
            rd.ask("ROUND_TRIP_FAILED")
            continue
        frame = stock_frame(clause, q["start"], list_spans, is_q)
        if frame is None:                               # rule 6: an amount said, but not as what we have
            if is_q:
                rd.ask("WHAT_IF", words=q["words"], item=item)
            else:
                rd.unframed.append({"kind": "absent" if amount == "0" else "stock", "name": q["name"],
                                    "words": q["words"], "amount": amount, "unit": q["unit"]})
            continue
        if amount == "0":
            rd.absent.append({"name": q["name"], "words": q["words"], "rule": "ZERO_SAID_AS_NONE"})
            rd.frames.append(dict(frame, kind="absent", name=q["name"]))
            continue
        rd.stocks.append({"name": q["name"], "amount": amount, "said": q["said"], "unit": q["unit"],
                          "words": q["words"], "rule": "STOCK_STATED"})
        rd.frames.append(dict(frame, kind="stock", name=q["name"]))

    # 2. absences
    absent_here = set()
    for start, end, word, strong, kind_word, shape in hits:
        if any(a <= start < b for a, b in consumed):
            continue
        kind, name = rd.known(word)
        if kind == "ingredient":
            if name in absent_here:
                continue
            absent_here.add(name)
            consumed.append((start, end))
            if is_q or hedge:
                rd.ask("WHAT_IF_ABSENT", item=say_name(name))
                continue
            frame = absent_frame(clause, start, end, shape, list_spans, is_q)
            if frame is None:                           # rule 6: "out of the water" is not "we're out of water"
                rd.unframed.append({"kind": "absent", "name": name, "words": clause[start:end].strip()})
                continue
            rd.absent.append({"name": name, "words": clause[start:end].strip(), "rule": "ABSENT_STATED"})
            rd.frames.append(dict(frame, kind="absent", name=name))
        elif kind is None and strong and kind_word in ("out of", "no more", "none of the", "zero") \
                and word not in FUNCTION_WORDS and word not in IGNORED_COUNT_NOUNS and word not in UNIT_FORMS:
            rd.ask("UNKNOWN_INGREDIENT", name=word, known=say_list_and(rd.ingredients))

    # 3. an ingredient named with no number, in a statement about stock: ask, never fill
    if has_stock_verb and not is_q:
        for w, name in rd.ingredient_words.items():
            for m in re.finditer(r"\b%s\b" % re.escape(w), clause):
                if any(a <= m.start() < b for a, b in consumed):
                    continue
                if any(s["name"] == name for s in rd.stocks) or any(a["name"] == name for a in rd.absent):
                    continue
                rd.ask("NO_NUMBER", item=say_name(name), countable=name in COUNTABLE)
                consumed.append((m.start(), m.end()))

    # 4. the product asked about
    # a product is the subject only when the user asks for it: a make/bake/how-much request, or the bare name
    filler = {"and", "or", "the", "some", "more", "what", "about", "how", "then", "now", "ok", "okay", "so", "a"}
    bare_name = all(w in rd.product_words or w in filler for w in re.findall(r"[a-z']+", clause))
    asks = bool(REQUEST_RX.search(clause)) or bare_name
    named = []
    for pos, w in sorted(product_words_here):
        if any(a <= pos < b for a, b in consumed):
            continue
        name = rd.product_words[w]
        if name not in [n for n, _ in named]:
            named.append((name, w))
    if named and asks:
        for name, w in named:
            rd.topics.append({"name": name, "words": w, "rule": "PRODUCT_NAMED"})
        return
    if not named and asks:
        um = UNKNOWN_PRODUCT_RX.search(clause)
        if um:
            word = um.group("n1") or um.group("n2") or um.group("n3")
            kind, _n = rd.known(word)
            generic = word in ("batch", "it", "that", "this", "them", "some", "something", "enough", "any", "one",
                               "more", "much", "many", "a", "an", "the", "us", "me", "do", "with")
            if kind is None and not generic and word not in FUNCTION_WORDS and word not in UNIT_FORMS \
                    and not rd.known(word)[0] and (um.group("n1") or um.group("n2")):
                rd.ask("UNKNOWN_PRODUCT", name=word, known=say_list_and(rd.products))
                return
        if BATCH_REF_RX.search(clause):
            if last_topic:
                rd.topics.append({"name": last_topic, "words": BATCH_REF_RX.search(clause).group(0),
                                  "rule": "BATCH_REFERS_TO_LAST_TOPIC"})
            else:
                rd.ask("WHICH_PRODUCT", known=say_list(rd.products))


def read(text: str, ingredients: Sequence[str], products: Sequence[str], last_topic: Optional[str] = None,
         known_units: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Read one everyday sentence. Returns a reading dict with status CONTENT, WITNESS, CLARIFY, NOTHING_TO_SAVE
    (rule 6: an ingredient was named, but not as stock, in a sentence that is not about our kitchen) or NOT_MINE."""
    t = normalize_text(text)
    rd = _Reading(t, ingredients, products)
    out: Dict[str, Any] = {"reader": READER_VERSION, "claim_status": CLAIM_STATUS, "status": "NOT_MINE",
                           "normalized": t, "lexicon": {"file": os.path.basename(LEXICON_PATH),
                                                         "sha256": LEXICON_SHA256, "lists": list(BORROWED_LISTS)},
                           "names_table": EVERYDAY_NAMES["label"], "stocks": [], "absent": [], "topic": None,
                           "witness": None, "ignored": [], "rules": [], "clarify": None, "content": None,
                           "checked_form": None, "round_trip_ok": None, "frames": [], "frame_form": None,
                           "frame_round_trip_ok": None, "unframed": []}
    if not t or not _claimed(rd, t):
        return out
    if cce is None:
        out.update(status="CLARIFY", clarify={"code": "ROUND_TRIP_FAILED", "slots": {}})
        return out
    known_units = dict(known_units or {})

    # conversions are refused, whatever else the sentence says
    if CONVERT_RX.search(t):
        units = sorted({u for u in re.findall(r"\b(%s)\b" % _UNIT_ALT, t) if UNIT_FORMS.get(u)})
        rd.ask("CONVERSION_REFUSED", units=" and ".join(units) if units else None)
    else:
        bm = BATCH_REPORT_RX.search(t)
        if bm and any(n[0] >= bm.end() for n in _numbers(t)):
            _read_batch(rd, t, bm)
        else:
            for clause, is_q in split_clauses(t):
                _read_clause(rd, clause, is_q, last_topic)

    # one turn, one consistent story: the same ingredient twice, or stated both present and absent, is a question
    if not rd.clarifications:
        seen: Dict[str, Dict[str, Any]] = {}
        # an unframed amount of an ingredient also stated as stock: two amounts are a question first (rules 5, 6)
        framed_names = {s["name"] for s in rd.stocks}
        for s in rd.stocks + [u for u in rd.unframed if u["kind"] == "stock" and u["name"] in framed_names]:
            prev = seen.get(s["name"])
            if prev is not None:
                if not same_unit(prev["unit"], s["unit"]):
                    rd.ask("CONVERSION_REFUSED", units="%s and %s" % (prev["unit"] or "plain numbers",
                                                                       s["unit"] or "plain numbers"))
                elif prev["amount"] != s["amount"]:
                    rd.ask("CONTRADICTION", item=say_name(s["name"]), a=prev["words"], b=s["words"])
            seen[s["name"]] = s
        absent_names = {a["name"] for a in rd.absent}
        for s in rd.stocks:
            if s["name"] in absent_names:
                rd.ask("CONTRADICTION", item=say_name(s["name"]), a=s["words"],
                       b=[a["words"] for a in rd.absent if a["name"] == s["name"]][0])
        topic_names = []
        for tp in rd.topics:
            if tp["name"] not in topic_names:
                topic_names.append(tp["name"])
        if len(topic_names) > 1:
            rd.ask("MULTIPLE_PRODUCTS", a=say_name(topic_names[0]), b=say_name(topic_names[1]))
    # a unit that differs from the one this ingredient was given in before is a question, not a conversion
    if not rd.clarifications:
        entries = list(rd.stocks)
        if rd.witness:
            entries += [dict(v, name=k) for k, v in rd.witness["stock_words"].items()]
        for s in entries:
            old = known_units.get(s["name"])
            if old and s["unit"] and not same_unit(old, s["unit"]):
                rd.ask("UNIT_MISMATCH", item=say_name(s["name"]), old_unit=old, new_unit=s["unit"])
                break

    # rule 6 (STOCK_FRAME_REQUIRED): an ingredient amount or absence said without a stock frame is never written.
    # About our kitchen -> one plain question; anything else -> nothing to save. All or nothing, as rule 3.
    nothing_to_save = False
    if rd.unframed and not rd.clarifications:
        rd.rules.append("STOCK_FRAME_REQUIRED")
        first = rd.unframed[0]
        kitchen = bool(rd.stocks or rd.absent or rd.topics or rd.witness or KITCHEN_CUE_RX.search(t)
                       or any(re.search(r"%s" % re.escape(w), t) for w in rd.product_words))
        if not kitchen:
            nothing_to_save = True
        elif first["kind"] == "absent":
            rd.ask("NO_STOCK_FRAME_ABSENT", item=say_name(first["name"]))
        else:
            rd.ask("NO_STOCK_FRAME", words=first["words"], item=say_name(first["name"]))

    out.update(stocks=rd.stocks, absent=rd.absent, ignored=rd.ignored, rules=sorted(set(rd.rules)),
               unframed=rd.unframed)
    if nothing_to_save:
        out.update(status="NOTHING_TO_SAVE", stocks=[], absent=[], ignored=rd.ignored)
        return out
    if rd.clarifications:
        out.update(status="CLARIFY", clarify=rd.clarifications[0], all_clarify=rd.clarifications)
        return out
    if rd.witness is not None:
        form = cce.empty_content()
        form["topic"] = "Ω_" + rd.witness["product"]
        form["stocks"] = [{"amount": a, "ref": {"outcome": "Ω_" + k}} for k, a in rd.witness["stock_before"].items()]
        form["stocks"].append({"amount": rd.witness["made"], "ref": {"outcome": "Ω_" + rd.witness["product"]}})
        ok, checked = _round_trip(form)
        out.update(witness=rd.witness, content=form, checked_form=checked, round_trip_ok=ok,
                   status="WITNESS" if ok else "CLARIFY",
                   clarify=None if ok else {"code": "ROUND_TRIP_FAILED", "slots": {}})
        return out
    if not (rd.stocks or rd.absent or rd.topics):
        return out                               # claimed words, but nothing to read: not a stock or recipe turn
    content = cce.empty_content()
    content["stocks"] = [{"amount": s["amount"], "ref": {"outcome": "Ω_" + s["name"]}} for s in rd.stocks]
    content["relations"] = [["absent", "Ω_" + a["name"]] for a in rd.absent]
    if rd.topics:
        content["topic"] = "Ω_" + rd.topics[0]["name"]
        out["topic"] = rd.topics[0]
    ok, checked = _round_trip(content)
    # rule 6: the frames ride beside the checked form and must render back exactly, like the checked form itself
    out.update(frames=rd.frames, frame_form=render_frames(rd.frames))
    frame_ok, _why = check_frame_form(out)
    out["frame_round_trip_ok"] = frame_ok
    ok = ok and frame_ok
    out.update(content=content, checked_form=checked, round_trip_ok=ok, status="CONTENT" if ok else "CLARIFY",
               clarify=None if ok else {"code": "ROUND_TRIP_FAILED", "slots": {}})
    return out


def _round_trip(content: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Render to checked form and parse back. The reading is used only when the two are identical."""
    try:
        checked = cce.render(content)
        back = cce.parse(checked)
        return cce.normalize(back) == cce.normalize(content), checked
    except Exception:
        return False, None


def quantities_said(reading: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """The user's own words for each amount in a reading: {name: {qty, unit, words}} (for the voice to quote)."""
    out = {}
    for s in reading.get("stocks") or []:
        out[s["name"]] = {"qty": s["amount"], "said": s["said"], "unit": s["unit"], "words": s["words"]}
    w = reading.get("witness")
    if w:
        for k, v in w["stock_words"].items():
            out[k] = {"qty": v["amount"], "said": v["said"], "unit": v["unit"], "words": v["words"]}
    return out
