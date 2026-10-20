"""helm_voice.py -- HELM's everyday-English WRITER (Fix F, 2026-10-18).

What it is, in plain words:
  The brain hands over a RECEIPT (what happened: an answer with a yield, a refusal, an "I can't tell", a request
  for one missing amount, something learned, something repaired, a gap). This module turns that receipt into
  one to three sentences of plain American English. It is deterministic: no second model, no network, stdlib only.

Rules it keeps:
  1. Facts come ONLY from the receipt (plus, when the user said it, the user's own words for an amount that the
     receipt confirms). The writer never adds a fact.
  2. No CAS notation or CAS jargon in the output, unless the user asked for the technical view; then the
     technical line is added AFTER the English, built straight from the receipt.
  3. Variety without guessing: each phrasing in phrasebook.json is equally correct. The first choice is fixed by the
     receipt's hash. A seeded alternative is drawn only when that first choice was used in the last N turns (the
     restart-fallback discipline from rb_c4: exact first, seeded alternatives only when stuck, the checker decides,
     the seed is saved in the trace). The same sentence is never said twice in a row.
  4. Guard: every rendered sentence is read back -- numbers, ingredient names and outcome words are pulled out of
     the English and compared with the receipt. A sentence that fails is refused; the plain template is used.

Tone (Register, CAS v7.5): f warm (default), A analytical (when the user asks for detail), E hands-on,
T big-picture. Dialogue acts: statement, question back, offer.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

try:  # typing only; the writer accepts plain dicts
    from typing import TypedDict
except ImportError:  # pragma: no cover
    TypedDict = dict

HERE = os.path.dirname(os.path.abspath(__file__))
PHRASEBOOK_PATH = os.path.join(HERE, "phrasebook.json")

# --------------------------------------------------------------------------------------------- receipt shape
KINDS = ("ANSWER", "UNDETERMINED", "CLARIFY", "REFUSE")
SITUATIONS = ("success", "blocked_missing", "cant_determine", "dont_know", "clarify", "refused", "learned",
              "repaired", "never_learned", "faded")
KIND_OF = {"success": "ANSWER", "learned": "ANSWER", "repaired": "ANSWER",
           "blocked_missing": "REFUSE", "refused": "REFUSE",
           "clarify": "CLARIFY", "dont_know": "CLARIFY",
           "cant_determine": "UNDETERMINED", "never_learned": "UNDETERMINED", "faded": "UNDETERMINED"}
REGISTERS = ("f", "A", "E", "T")
ACTS = ("statement", "question", "offer")
RECENT_N = 3          # a phrasing used in the last N turns counts as "stuck" -> seeded alternative
K_FALLBACK = 8        # at most 8 seeded alternatives, as in rb_c4


class VoiceReceipt(TypedDict, total=False):
    """What the brain hands the writer. Every field is optional except kind (or situation).

    kind          ANSWER | UNDETERMINED | CLARIFY | REFUSE
    situation     one of SITUATIONS (derived from kind + fields when absent)
    product       what is being made, plain words ("bread")
    unit          unit of the yield ("loaves"); "units" when absent
    yield_value   exact yield as a decimal string or "p/q"
    limiting      limiting ingredient name (the one that runs out first)
    limiting_qty  amount of the limiting ingredient on hand (decimal string)
    limiting_unit unit of that amount ("lbs")
    missing       required ingredients that are absent
    lacunae       cells never taught (lacunarity machine state LACUNA)
    faded         cells taught before that no longer hold (state FADED)
    repair        what was put right, plain words
    learned       what was learned, plain words (a clause)
    reason        refusal reason, plain words (a clause)
    clarify_item  the one amount the brain needs
    topic         what the user asked about, plain words
    receipt_id    the brain's receipt hash
    telemetry     diagnostic numbers (never said in everyday mode)
    """
    kind: str
    situation: str
    product: str
    unit: str
    yield_value: str
    limiting: str
    limiting_qty: str
    limiting_unit: str
    missing: List[str]
    lacunae: List[str]
    faded: List[str]
    repair: str
    learned: str
    reason: str
    clarify_item: str
    topic: str
    receipt_id: str
    telemetry: Dict[str, str]


def situation_of(r: Dict[str, Any]) -> str:
    if r.get("situation"):
        s = r["situation"]
        if s not in SITUATIONS:
            raise ValueError("unknown situation %r" % s)
        return s
    k = r.get("kind")
    if k == "ANSWER":
        return "repaired" if r.get("repair") else ("learned" if r.get("learned") else "success")
    if k == "REFUSE":
        return "blocked_missing" if r.get("missing") else "refused"
    if k == "CLARIFY":
        return "clarify" if r.get("clarify_item") else "dont_know"
    if k == "UNDETERMINED":
        if r.get("lacunae"):
            return "never_learned"
        if r.get("faded"):
            return "faded"
        return "cant_determine"
    raise ValueError("receipt needs kind or situation")


REQUIRED_FIELDS = {"success": ("yield_value", "limiting"), "blocked_missing": ("missing",),
                   "clarify": ("clarify_item",), "refused": ("reason",), "learned": ("learned",),
                   "repaired": ("repair",), "never_learned": ("lacunae",), "faded": ("faded",),
                   "cant_determine": (), "dont_know": ()}


def validate_receipt(r: Dict[str, Any]) -> str:
    s = situation_of(r)
    if r.get("kind") and r["kind"] != KIND_OF[s]:
        raise ValueError("kind %s does not fit situation %s" % (r["kind"], s))
    for f in REQUIRED_FIELDS[s]:
        if not r.get(f):
            raise ValueError("situation %s needs %s" % (s, f))
    if r.get("yield_value") is not None:
        _as_fraction(r["yield_value"])
    return s


def receipt_hash(r: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def derive_seed(*parts) -> int:
    """Same rule as rb_c4 grammar.derive_seed: sha256 of the joined parts, first 16 hex digits."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16], 16)


# --------------------------------------------------------------------------------------------- words and numbers
INGREDIENTS_22 = ["Flour", "Water", "Sugar", "Egg", "Salt", "Yeast", "Milk", "Butter", "Cocoa", "Vanilla", "Honey",
                  "Oil", "Oats", "Almonds", "Cinnamon", "Nutmeg", "Ginger", "BakingPowder", "BakingSoda",
                  "Cornstarch", "LemonZest", "Molasses"]
EXTRA_NAMES = ["chocolate", "rice", "beans", "coffee", "tea", "cream", "cheese", "tomato", "onion", "garlic", "pepper",
               "lemon", "apple", "raisin", "walnut", "pecan", "bread", "cookie", "cake", "muffin", "pancake", "loaf",
               "loaves", "pie", "soup", "dough", "glaze", "jam", "sourdough", "starter", "rye", "brownie", "biscuit",
               "granola", "syrup", "yogurt", "banana", "blueberry", "strawberry", "potato", "carrot", "pasta"]
COUNTABLE = {"egg", "almond", "apple", "lemon", "onion", "tomato", "banana", "potato", "carrot"}
UNIT_WORDS = r"lbs?|pounds?|cups?|kg|kilograms?|grams?|g|oz|ounces?|tbsp|tablespoons?|tsp|teaspoons?|liters?|litres?|ml|quarts?|pints?|sticks?|packets?|bags?"


def say_name(n: str) -> str:
    """'BakingPowder' -> 'baking powder'; 'Flour' -> 'flour'."""
    n = (n or "").strip()
    n = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n)
    return n.lower()


def _norm_name(s: str) -> str:
    s = re.sub(r"[^a-z ]", "", say_name(s)).strip()
    s = re.sub(r"\s+", " ", s)
    if s.endswith("ies"):
        s = s[:-3] + "y"
    elif s.endswith("es") and s[:-2].endswith(("o", "ch", "sh")):
        s = s[:-2]
    elif s.endswith("s") and not s.endswith("ss") and s not in ("molasses", "oats"):
        s = s[:-1]
    return s


LEXICON = sorted({_norm_name(x) for x in INGREDIENTS_22 + EXTRA_NAMES}, key=lambda x: -len(x))


def say_list(names: List[str]) -> str:
    names = [say_name(n) for n in names]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return "%s and %s" % tuple(names)
    return ", ".join(names[:-1]) + ", and " + names[-1]


def cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _as_fraction(v) -> Fraction:
    if isinstance(v, Fraction):
        return v
    s = str(v).strip().replace(",", "")
    if "/" in s:
        p, q = s.split("/")
        return Fraction(int(p), int(q))
    try:
        return Fraction(Decimal(s))
    except (InvalidOperation, ValueError):
        raise ValueError("not a number: %r" % v)


def _dec_str(d: Decimal) -> str:
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def round_to(value, places: int) -> str:
    fr = _as_fraction(value)
    d = (Decimal(fr.numerator) / Decimal(fr.denominator)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return _dec_str(d)


def say_amount(value, register: str) -> str:
    """'exactly 12' when the shown number is the exact value, else 'about 8.45'. A shows up to 4 places."""
    places = 4 if register == "A" else 2
    shown = round_to(value, places)
    exact = _as_fraction(shown) == _as_fraction(value)
    return ("exactly " if exact else "about ") + shown


# --------------------------------------------------------------------------------------------- CAS detectors
CAS_NOTATION_RX = re.compile(
    r"\^\d|[ΩΘΛκι]|\bF[1-7]\b|\|[TAfE]\b|\b[PCEO][0-9]\b|\bCO-\d\b|\bG-[A-Z]+\b|"
    r"\b(?:RPM|RPA|ASOM|CJT|CCE|UNDETERMINED|CLARIFY|REFUSE_CLAIM|GATE_[A-Z_]+|A0|D[1-7]|W[1-7])\b")
CAS_JARGON_RX = re.compile(
    r"\b(?:noetic\w*|lacuna\w*|stoichiometr\w*|registers?|operators?|entropy|aperture|valve|receipts?|40-digit|"
    r"decimal precision|limiting reagent|topological|admissib\w*|simplex|cognitive states?|pathways?|"
    r"prerequisite gate|novelty|kahn)\b", re.I)


def cas_tokens(text: str) -> List[str]:
    """Every CAS notation token and every CAS jargon word in the text (both count as 'speaking CAS')."""
    return [m.group(0) for m in CAS_NOTATION_RX.finditer(text)] + [m.group(0) for m in CAS_JARGON_RX.finditer(text)]


# --------------------------------------------------------------------------------------------- the guard
MARKERS = {
    "success": r"\b(?:you can make|we can get|you'll get|works out to|comes to|comes out to|the most you can make|"
               r"is doable|adds up to|produce that much|carry you to|caps you at|caps this run at|it gives|enough for|"
               r"yield|gets you|the result is|the answer is|the total is|can produce|we can produce)\b",
    "blocked": r"\b(?:missing|(?:we're|we are|you're|ran) out of|no \w+ on hand|can't (?:run|make|go ahead|work out)|stopped|held off|holding off|"
               r"halted|blocked|has to wait|won't come together|depends on|you'll need|must-have|halt)\b",
    "uncertain": r"\b(?:can't tell|cannot tell|not sure|can't call|either way|undecided|can't pick|isn't settled|"
                 r"(?:not|isn't) clear enough|won't pretend)\b",
    "nodata": r"\b(?:no verified facts|don't know|outside what I know|no reliable|don't have reliable|no solid facts|"
              r"beyond what I've got facts|any grounding|can't support an answer|don't have verified|"
              r"nothing I have covers|can't answer that)\b",
    "clarify": r"\b(?:how much|what is the amount|the amount of|i need)\b[^?]*\?",
    "refuse": r"\b(?:won't do|won't help|not going to do|rather not do|declining|won't proceed|not do that|"
              r"not doing that|won't do it|things I won't do|will not do)\b",
    "learned": r"\b(?:learned|taught me something|now I know|updated my notes|updated what I know|new fact stored|"
               r"got it)\b",
    "repaired": r"\b(?:fixed|corrected|put it right|put right|found the slip|correction|correcting)\b",
    "never": r"\b(?:never been taught|never taught|nobody's taught|haven't been taught|"
             r"outside anything I've been taught|a gap for me|true gap)\b",
    "faded": r"\b(?:faded|slipped|can't rely|rusty|lost my grip|used to (?:know|be|have)|no longer checks out)\b",
}
MARKER_RX = {k: re.compile(v, re.I) for k, v in MARKERS.items()}
OWN_MARKER = {"success": "success", "blocked_missing": "blocked", "cant_determine": "uncertain", "dont_know": "nodata",
              "clarify": "clarify", "refused": "refuse", "learned": "learned", "repaired": "repaired",
              "never_learned": "never", "faded": "faded"}
FORBIDDEN_MARKERS = {
    "success": ("blocked", "uncertain", "nodata", "refuse", "never", "faded"),
    "blocked_missing": ("success", "uncertain", "nodata", "refuse", "never", "faded"),
    "cant_determine": ("success", "blocked", "nodata", "refuse", "never", "faded"),
    "dont_know": ("success", "blocked", "uncertain", "never", "faded"),
    "clarify": ("success", "blocked", "uncertain", "nodata", "refuse", "never", "faded"),
    "refused": ("success", "uncertain", "never", "faded"),
    "learned": ("blocked", "uncertain", "nodata", "refuse", "never", "faded"),
    "repaired": ("blocked", "uncertain", "nodata", "refuse", "never", "faded"),
    "never_learned": ("success", "learned", "faded", "repaired"),
    "faded": ("success", "never", "refuse"),
}
NUM_RX = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?:/\d+)?(?![\w])")
NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "eleven": 11, "twelve": 12, "dozen": 12, "twenty": 20, "hundred": 100}
TEXT_FACT_FIELDS = ("product", "unit", "topic", "reason", "learned", "repair", "clarify_item")


def outcome_classes(text: str) -> List[str]:
    return [k for k, rx in MARKER_RX.items() if rx.search(text)]


def _numbers_in(text: str) -> List[Fraction]:
    out = []
    for m in NUM_RX.finditer(text):
        tok = m.group(0).rstrip(",")
        try:
            out.append(_as_fraction(tok))
        except (ValueError, ZeroDivisionError):
            continue
    for w, v in NUMBER_WORDS.items():
        if re.search(r"\b%s\b" % w, text, re.I):
            out.append(Fraction(v))
    return out


def _names_in(text: str) -> set:
    t = " " + re.sub(r"[^a-z ]", " ", text.lower()) + " "
    t = re.sub(r"\s+", " ", t)
    words = [_norm_name(w) for w in t.split()]
    joined = " " + " ".join(words) + " "
    found = set()
    for name in LEXICON:
        if (" %s " % name) in joined:
            found.add(name)
    return found


def allowed_facts(r: Dict[str, Any], user_have: Optional[str] = None) -> Tuple[set, set]:
    """(allowed numbers, allowed names): everything the receipt says, plus the user's own quoted amount."""
    nums = set()
    if r.get("yield_value") is not None:
        for p in range(0, 7):
            nums.add(_as_fraction(round_to(r["yield_value"], p)))
        nums.add(_as_fraction(r["yield_value"]))
    for f in ("limiting_qty",):
        if r.get(f) is not None:
            nums.add(_as_fraction(r[f]))
    for v in (r.get("telemetry") or {}).values():
        try:
            nums.add(_as_fraction(v))
        except (ValueError, ZeroDivisionError):
            pass
    texts = [str(r.get(f) or "") for f in TEXT_FACT_FIELDS] + [user_have or ""]
    for t in texts:
        nums.update(_numbers_in(t))
    names = set()
    for f in ("limiting",):
        if r.get(f):
            names.add(_norm_name(r[f]))
    for f in ("missing", "lacunae", "faded"):
        for n in r.get(f) or []:
            names |= _names_in(say_name(n)) | {_norm_name(n)}
    for t in texts:
        names |= _names_in(t)
    return nums, names


def _key_facts(r: Dict[str, Any], situation: str) -> List[Tuple[str, List[str]]]:
    """Each key fact with the spellings that count as saying it."""
    keys = []
    if situation in ("success",) or (situation == "repaired" and r.get("yield_value") is not None):
        keys.append(("yield", [round_to(r["yield_value"], p) for p in range(0, 7)]))
    if situation == "success" and r.get("limiting"):
        keys.append(("limiting", [say_name(r["limiting"])]))
    if situation == "blocked_missing":
        keys += [("missing:" + n, [say_name(n)]) for n in r.get("missing") or []]
    if situation == "clarify":
        keys.append(("item", [say_name(r["clarify_item"])]))
    if situation == "refused":
        keys.append(("reason", [r["reason"]]))
    if situation == "learned":
        keys.append(("learned", [r["learned"]]))
    if situation == "repaired":
        keys.append(("repair", [r["repair"]]))
    if situation == "never_learned":
        keys += [("gap:" + n, [say_name(n)]) for n in r.get("lacunae") or []]
    if situation == "faded":
        keys += [("faded:" + n, [say_name(n)]) for n in r.get("faded") or []]
    return keys


def _mask_facts(text: str, r: Dict[str, Any]) -> str:
    """Hide the receipt's own free-text facts so their words cannot trip the outcome-word check."""
    out = text
    for f in ("reason", "learned", "repair", "topic"):
        v = r.get(f)
        if v:
            out = re.sub(re.escape(v), " FACT ", out, flags=re.I)
    return out


def sentence_count(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()])


def verify(text: str, r: Dict[str, Any], situation: Optional[str] = None, user_have: Optional[str] = None,
           check_outcome: bool = True, max_sentences: Optional[int] = 3) -> List[str]:
    """Read the English back and compare it with the receipt. Returns the list of problems (empty = PASS)."""
    situation = situation or situation_of(r)
    problems = []
    toks = cas_tokens(text)
    if toks:
        problems.append("CAS_TOKENS:%s" % ",".join(toks))
    nums, names = allowed_facts(r, user_have)
    for n in _numbers_in(text):
        if n not in nums:
            problems.append("INVENTED_NUMBER:%s" % n)
    for n in _names_in(text):
        if n not in names:
            problems.append("INVENTED_NAME:%s" % n)
    exact_vals = {_as_fraction(r[f]) for f in ("yield_value", "limiting_qty") if r.get(f) is not None}
    for m in re.finditer(r"\bexactly\s+(\d[\d,]*(?:\.\d+)?)", text, re.I):
        if _as_fraction(m.group(1)) not in exact_vals:  # "exactly 3.333" for 10/3 is a false claim
            problems.append("FALSE_EXACT:%s" % m.group(1))
    low = text.lower()
    for key, spellings in _key_facts(r, situation):
        if key == "yield":
            said = any(_as_fraction(s) in set(_numbers_in(text)) for s in spellings)
        else:
            said = any(s.lower() in low for s in spellings)
        if not said:
            problems.append("DROPPED_FACT:%s" % key)
    if check_outcome:
        masked = _mask_facts(text, r)
        own = OWN_MARKER[situation]
        if not MARKER_RX[own].search(masked):
            problems.append("NO_OUTCOME_WORD:%s" % own)
        for bad in FORBIDDEN_MARKERS[situation]:
            if MARKER_RX[bad].search(masked):
                problems.append("WRONG_OUTCOME_WORD:%s" % bad)
    if max_sentences is not None and not 1 <= sentence_count(text) <= max_sentences:
        problems.append("SENTENCES:%d" % sentence_count(text))
    return problems


def facts_preserved(text: str, r: Dict[str, Any], user_have: Optional[str] = None) -> bool:
    """Harness metric, same for every renderer: key facts said, no invented numbers, no invented names."""
    probs = verify(text, r, user_have=user_have, check_outcome=False, max_sentences=None)
    return not [p for p in probs if not p.startswith("CAS_TOKENS")]


# --------------------------------------------------------------------------------------------- reading level
def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def reading_grade(text: str) -> float:
    """Flesch-Kincaid grade level: 0.39 * words/sentence + 11.8 * syllables/word - 15.59."""
    words = re.findall(r"[A-Za-z']+|\d[\d.,/]*", text)
    if not words:
        return 0.0
    sents = max(1, sentence_count(text))
    syl = sum(syllables(w) if w[0].isalpha() else 1 for w in words)
    return 0.39 * len(words) / sents + 11.8 * syl / len(words) - 15.59


# --------------------------------------------------------------------------------------------- tone and acts
def choose_register(user_text: Optional[str]) -> str:
    t = (user_text or "").lower()
    if re.search(r"\b(?:details?|exact|exactly|precise|precisely|technical|break it down|show (?:me )?the "
                 r"(?:math|numbers)|why|how come|specifics)\b", t):
        return "A"
    if re.search(r"\b(?:how do i|step by step|walk me through|what should i do|hands-on|in the kitchen)\b", t):
        return "E"
    if re.search(r"\b(?:big picture|overall|in general|the gist|bottom line)\b", t):
        return "T"
    return "f"


def wants_technical(user_text: Optional[str]) -> bool:
    return bool(re.search(r"\b(?:technical view|raw receipt|cas view|cas notation|show (?:me )?the receipt)\b",
                          (user_text or "").lower()))


# --------------------------------------------------------------------------------------------- phrasebook
_BOOK_CACHE: Dict[str, Any] = {}


def load_phrasebook(path: str = PHRASEBOOK_PATH) -> Dict[str, Any]:
    if path not in _BOOK_CACHE:
        with open(path, encoding="utf-8") as f:
            _BOOK_CACHE[path] = json.load(f)
    return _BOOK_CACHE[path]


SLOT_RX = re.compile(r"\{(\w+)\}")
KEY_SLOTS = {"success": ("yield_q", "limiting"), "blocked_missing": ("missing",), "clarify": ("item",),
             "refused": ("reason",), "learned": ("learned",), "repaired": ("repair", "yield_q"),
             "never_learned": ("gaps",), "faded": ("gaps",), "cant_determine": (), "dont_know": ()}
SLOT_ALIASES = {"limiting": ("limiting", "Limiting", "user_have"), "missing": ("missing", "Missing"),
                "gaps": ("gaps", "Gaps"), "repair": ("repair", "Repair"), "yield_q": ("yield_q",),
                "item": ("item",), "reason": ("reason",), "learned": ("learned",)}


def fill(text: str, slots: Dict[str, str]) -> str:
    return SLOT_RX.sub(lambda m: slots[m.group(1)], text)


def _eligible(text: str, needs: List[str], slots: Dict[str, str], flags: Dict[str, bool], situation: str) -> bool:
    used = set(SLOT_RX.findall(text))
    if any(not slots.get(u) for u in used):
        return False
    if any(not flags.get(n) for n in needs):
        return False
    for key in KEY_SLOTS[situation]:
        if slots.get(key) and not (used & set(SLOT_ALIASES[key])):
            return False
    return True


# --------------------------------------------------------------------------------------------- conversation state
@dataclass
class VoiceState:
    """Per-conversation memory the writer needs: what it said lately and what the user said."""
    # phrasing ids said lately, kept per situation (main) and per situation+act (tail): "used in the last N turns
    # of this kind" -> the fixed first choice is skipped and a seeded alternative is drawn
    recent_main: Dict[str, deque] = field(default_factory=dict)
    recent_tail: Dict[str, deque] = field(default_factory=dict)
    last_main: Optional[str] = None
    last_text: Optional[str] = None
    last_act: Optional[str] = None
    last_situation: Optional[str] = None
    last_limiting: Optional[str] = None
    last_missing: Optional[Tuple[str, ...]] = None
    user_said: Dict[str, Dict[str, str]] = field(default_factory=dict)
    turn: int = 0
    traces: List[Dict[str, Any]] = field(default_factory=list)

    def recent(self, table: Dict[str, deque], key: str) -> deque:
        if key not in table:
            table[key] = deque(maxlen=RECENT_N)
        return table[key]

    def note_user_words(self, text: str) -> Dict[str, Dict[str, str]]:
        """Keep the user's own words for amounts ('5 lbs of flour') so the writer can quote them back."""
        found = {}
        for raw in INGREDIENTS_22 + EXTRA_NAMES:
            spoken = say_name(raw)
            name_rx = r"\s+".join(re.escape(w) for w in spoken.split()) + r"(?:e?s)?"
            rx = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:(%s)\.?\s+)?(?:of\s+)?(?:the\s+)?(%s)\b"
                            % (UNIT_WORDS, name_rx), re.I)
            m = rx.search(text)
            if not m:
                continue
            qty, unit, name_words = m.group(1), m.group(2), m.group(3)
            if not unit and _norm_name(spoken) not in COUNTABLE:
                continue  # "50 Flour" quoted back reads badly; only quote amounts with a unit or countable things
            words = "%s %s of %s" % (qty, unit, name_words.lower()) if unit else "%s %s" % (qty, name_words.lower())
            found[_norm_name(spoken)] = {"qty": qty, "unit": unit or "", "words": words, "turn": str(self.turn)}
        self.user_said.update(found)
        return found


@dataclass
class VoiceResult:
    text: str
    situation: str
    register: str
    act: str
    trace: Dict[str, Any]


# --------------------------------------------------------------------------------------------- the writer
class HELMVoice:
    def __init__(self, phrasebook_path: str = PHRASEBOOK_PATH, state: Optional[VoiceState] = None):
        self.book = load_phrasebook(phrasebook_path)
        self.state = state or VoiceState()

    # ---- slots: every value comes from the receipt or the user's own words
    def slots_for(self, r: Dict[str, Any], situation: str, register: str) -> Tuple[Dict[str, str], Dict[str, bool]]:
        st = self.state
        s: Dict[str, str] = {}
        s["unit"] = r.get("unit") or "units"
        if r.get("product") and _norm_name(r["product"]) != _norm_name(s["unit"]):  # no "24 cookies of cookies"
            s["product"] = r["product"]
        if r.get("yield_value") is not None:
            s["yield_q"] = say_amount(r["yield_value"], register)
        if r.get("limiting"):
            s["limiting"] = say_name(r["limiting"])
            s["Limiting"] = cap(s["limiting"])
            if r.get("limiting_qty") is not None:
                q = _dec_str(Decimal(str(r["limiting_qty"])))
                s["lim_have"] = ("%s %s" % (q, r["limiting_unit"])) if r.get("limiting_unit") else q
        if r.get("missing"):
            m = list(r["missing"])
            s["missing"] = say_list(m)
            s["Missing"] = cap(s["missing"])
            s["missing_verb"] = "is" if len(m) == 1 else "are"
            s["missing_pron"] = "it" if len(m) == 1 else "them"
        gaps = r.get("lacunae") if situation == "never_learned" else (r.get("faded") if situation == "faded" else None)
        if gaps:
            s["gaps"] = say_list(gaps)
            s["Gaps"] = cap(s["gaps"])
            s["gaps_verb"] = "is" if len(gaps) == 1 else "are"
            s["gaps_pron"] = "it" if len(gaps) == 1 else "them"
        for f, slot in (("repair", "repair"), ("learned", "learned"), ("reason", "reason"), ("topic", "topic")):
            if r.get(f):
                s[slot] = r[f]
        if r.get("repair"):
            s["Repair"] = cap(r["repair"])
        if r.get("clarify_item"):
            s["item"] = say_name(r["clarify_item"])
        flags = {"user_said": False, "same_limiting": False, "same_missing": False}
        if r.get("limiting") and r.get("limiting_qty") is not None:
            said = st.user_said.get(_norm_name(r["limiting"]))
            if said and _as_fraction(said["qty"]) == _as_fraction(r["limiting_qty"]):
                s["user_have"] = said["words"]
                flags["user_said"] = True
        if situation == "success" and st.last_situation == "success" and r.get("limiting") \
                and st.last_limiting == _norm_name(r["limiting"]):
            flags["same_limiting"] = True
        if situation == "blocked_missing" and st.last_situation == "blocked_missing" \
                and st.last_missing == tuple(sorted(_norm_name(x) for x in r.get("missing") or [])):
            flags["same_missing"] = True
        return s, flags

    # ---- restart-fallback choice among equally-correct phrasings
    def _choose(self, pool: List[Dict[str, Any]], salt: str, rh: str, recent, render, check, last: Optional[str]):
        tr: Dict[str, Any] = {"pool": [p["id"] for p in pool], "fallback_fired": False}
        if not pool:
            tr["kept"] = None
            return None, None, tr
        first_seed = derive_seed("VOICE", salt, rh)
        i0 = first_seed % len(pool)
        tr["first_choice"], tr["first_seed"] = pool[i0]["id"], first_seed
        tried = []

        def attempt(idx):
            p = pool[idx]
            text = render(p)
            probs = check(text)
            tried.append({"id": p["id"], "problems": probs})
            return text, (not probs and text != last)

        if pool[i0]["id"] not in recent:
            text, ok = attempt(i0)
            if ok:
                tr.update(kept=pool[i0]["id"], tried=tried)
                return pool[i0], text, tr
        # stuck: the fixed first choice was used lately, repeats the last sentence, or failed the guard
        tr["fallback_fired"] = True
        fb_seed = derive_seed("VOICE", salt, rh, "RESTART", self.state.turn)
        order = random.Random(fb_seed).sample(range(len(pool)), len(pool))
        tr["fallback_seed"] = fb_seed
        draws = 0
        for idx in order:
            if idx == i0 or pool[idx]["id"] in recent:
                continue
            if draws >= K_FALLBACK:
                break
            draws += 1
            text, ok = attempt(idx)
            if ok:
                tr.update(kept=pool[idx]["id"], tried=tried, fallback_draws=draws)
                return pool[idx], text, tr
        # every fresh option is spent: allow a recent one (still never the identical last sentence)
        for idx in order:
            if any(t["id"] == pool[idx]["id"] for t in tried):
                continue
            text, ok = attempt(idx)
            if ok:
                tr.update(kept=pool[idx]["id"], tried=tried, fallback_draws=draws, reused_recent=True)
                return pool[idx], text, tr
        tr.update(kept=None, tried=tried)
        return None, None, tr

    # ---- fix H (2026-10-18): the English reader's questions and stock notes, said through the same guard
    def _say_plain(self, kind: str, variants: List[str], user_text: Optional[str], slot_values: List[str],
                   salt: str) -> VoiceResult:
        """Pick one of several equally-correct plain sentences (seeded, never the last sentence again) and check it:
        no CAS words, and every number and food name must come from the user's words or the reader's slots."""
        st = self.state
        st.turn += 1
        if user_text:
            st.note_user_words(user_text)
        source = " ".join([user_text or ""] + [str(v) for v in slot_values])
        allowed_nums, allowed_names = set(_numbers_in(source)), _names_in(source)

        def problems(text: str) -> List[str]:
            out = ["CAS_TOKENS:%s" % ",".join(cas_tokens(text))] if cas_tokens(text) else []
            out += ["INVENTED_NUMBER:%s" % n for n in _numbers_in(text) if n not in allowed_nums]
            out += ["INVENTED_NAME:%s" % n for n in _names_in(text) if n not in allowed_names]
            return out

        first = derive_seed("PLAIN", kind, salt) % len(variants)
        order = [first] + [i for i in range(len(variants)) if i != first]
        chosen, text, tried = None, None, []
        for i in order:
            cand = variants[i]
            probs = problems(cand)
            tried.append({"variant": i, "problems": probs})
            if not probs and cand != st.last_text:
                chosen, text = i, cand
                break
        if text is None:
            ok = [variants[t["variant"]] for t in tried if not t["problems"]]
            text = ok[0] if ok else "Could you say that another way? I didn't act on it."
        trace = {"turn": st.turn, "situation": kind, "plain": True, "variant": chosen, "tried": tried,
                 "guard": "PASS" if chosen is not None else "FALLBACK"}
        st.last_main = st.last_text = text
        st.last_situation = kind
        st.traces.append(trace)
        return VoiceResult(text=text, situation=kind, register="f", act="question" if text.endswith("?")
                           else "statement", trace=trace)

    def say_reader_question(self, clarify: Dict[str, Any], user_text: Optional[str] = None) -> VoiceResult:
        """Say the English reader's question (helm_english_in) in plain words."""
        code = (clarify or {}).get("code") or "ROUND_TRIP_FAILED"
        slots = dict((clarify or {}).get("slots") or {})
        variants = reader_question_variants(code, slots)
        return self._say_plain("reader:" + code, variants, user_text, [v for v in slots.values()
                                                                       if isinstance(v, str)], code + "|" +
                               json.dumps(slots, sort_keys=True))

    def say_stock_noted(self, stocks: List[Dict[str, Any]], absent: List[str],
                        user_text: Optional[str] = None) -> VoiceResult:
        """'Got it: I've recorded 12 cups of flour and no water on hand.' Quotes the user's own words for amounts."""
        items = [s.get("words") or "%s %s" % (s["amount"], say_name(s["name"])) for s in stocks]
        items += ["no %s" % say_name(a) for a in absent]
        lst = items[0] if len(items) == 1 else (" and ".join(items) if len(items) == 2
                                                 else ", ".join(items[:-1]) + ", and " + items[-1])
        variants = ["Got it: I've recorded %s on hand." % lst, "Okay, recorded: %s on hand." % lst,
                    "Noted and recorded: %s." % lst]
        return self._say_plain("stock_noted", variants, user_text, items, lst)

    def render(self, r: Dict[str, Any], register: Optional[str] = None, act: Optional[str] = None,
               user_text: Optional[str] = None, technical: Optional[bool] = None, concise: bool = False) -> VoiceResult:
        if r.get("reader_question"):
            return self.say_reader_question(r["reader_question"], user_text)
        st = self.state
        st.turn += 1
        situation = validate_receipt(r)
        if user_text:
            st.note_user_words(user_text)
        register = register or choose_register(user_text)
        technical = wants_technical(user_text) if technical is None else technical
        rh = receipt_hash(r)
        slots, flags = self.slots_for(r, situation, register)
        user_have = slots.get("user_have")

        def check(text):
            return verify(text, r, situation, user_have=user_have)

        # main sentence(s): memory-backed phrasings first when they apply, then the register's pool
        entries = [e for e in self.book["entries"] if e["situation"] == situation]
        reg_used = register
        pool_all = [e for e in entries if e["register"] == register and _eligible(e["text"], e["needs"], slots, flags, situation)]
        if not pool_all:
            reg_used = "f"
            pool_all = [e for e in entries if e["register"] == "f" and _eligible(e["text"], e["needs"], slots, flags, situation)]
        if not pool_all:
            pool_all = [e for e in entries if _eligible(e["text"], e["needs"], slots, flags, situation)]
        with_needs = [e for e in pool_all if e["needs"]]
        recent_main = st.recent(st.recent_main, situation)
        pool = with_needs if (with_needs and not all(e["id"] in recent_main for e in with_needs)) else pool_all
        chosen, main, tr_main = self._choose(pool, "MAIN|%s|%s" % (situation, reg_used), rh, recent_main,
                                             lambda e: fill(e["text"], slots), check, st.last_main)
        if chosen is None and pool is not pool_all:
            chosen, main, tr_main = self._choose(pool_all, "MAIN2|%s|%s" % (situation, reg_used), rh, recent_main,
                                                 lambda e: fill(e["text"], slots), check, st.last_main)
        plain_used = False
        if chosen is None:
            key = "repaired+yield" if (situation == "repaired" and slots.get("yield_q")) else situation
            plains = [fill(t, slots) for t in self.book["plain"][key]]
            main = plains[1] if plains[0] == st.last_main else plains[0]
            plain_used = True
        # dialogue act: statement, question back, or offer
        if act is None:
            if concise or situation == "clarify":
                act = "statement"
            else:
                act = ACTS[derive_seed("ACT", rh) % 3]
                if act == st.last_act and situation == st.last_situation:
                    act = ACTS[(ACTS.index(act) + 1) % 3]
        tail_text, tr_tail = None, None
        if act != "statement" and sentence_count(main) < 3:
            tails = [t for t in self.book["tails"] if t["situation"] == situation and t["act"] == act
                     and all(slots.get(u) for u in SLOT_RX.findall(t["text"]))]
            chosen_t, full, tr_tail = self._choose(
                tails, "TAIL|%s|%s" % (situation, act), rh, st.recent(st.recent_tail, situation + "|" + act),
                lambda t: main + " " + fill(t["text"], slots), check, st.last_text)
            if chosen_t is not None:
                tail_text = full
                st.recent(st.recent_tail, situation + "|" + act).append(chosen_t["id"])
            else:
                act = "statement"
        else:
            act = "statement" if act != "statement" and sentence_count(main) >= 3 else act
        text = tail_text or main
        if text == st.last_text:  # never the identical sentence twice in a row
            text = main if tail_text else text
        final_problems = check(text)
        if final_problems and not plain_used:  # belt and braces: the plain template is the floor
            key = "repaired+yield" if (situation == "repaired" and slots.get("yield_q")) else situation
            plains = [fill(t, slots) for t in self.book["plain"][key]]
            text = plains[1] if plains[0] == st.last_text else plains[0]
            plain_used, act = True, "statement"
        clash = mood_fact_clash(user_text, r, situation)
        if clash.get("asked"):
            text = text + " " + clash["question"]
        if technical:
            text = text + "\n" + self.technical_line(r, situation)
        trace = {"turn": st.turn, "receipt_sha256": rh, "situation": situation, "register_asked": register,
                 "register_used": reg_used, "act": act, "main": tr_main, "tail": tr_tail, "plain_used": plain_used,
                 "guard": "PASS" if not final_problems else "FAIL->PLAIN:" + ";".join(final_problems),
                 "memory_flags": flags, "technical": bool(technical), "mood_fact_clash": clash}
        if chosen is not None:
            recent_main.append(chosen["id"])
        st.last_main = main
        st.last_text = text.split("\n")[0]
        st.last_act = act
        st.last_situation = situation
        st.last_limiting = _norm_name(r["limiting"]) if r.get("limiting") else None
        st.last_missing = tuple(sorted(_norm_name(x) for x in r.get("missing") or [])) or None
        st.traces.append(trace)
        return VoiceResult(text=text, situation=situation, register=reg_used, act=act, trace=trace)

    @staticmethod
    def technical_line(r: Dict[str, Any], situation: str) -> str:
        parts = ["kind=%s" % KIND_OF[situation], "situation=%s" % situation]
        if r.get("yield_value") is not None:
            parts.append("Y=%s" % r["yield_value"])
        if r.get("limiting"):
            parts.append("limiting reagent=%s" % r["limiting"])
        if r.get("missing"):
            parts.append("G-ABSENT=%s" % ",".join(r["missing"]))
        if r.get("lacunae"):
            parts.append("LACUNA=%s" % ",".join(r["lacunae"]))
        if r.get("faded"):
            parts.append("FADED=%s" % ",".join(r["faded"]))
        if r.get("receipt_id"):
            parts.append("receipt=%s" % r["receipt_id"])
        return "Technical view: " + "; ".join(parts)


# --------------------------------------------------------------------------------------------- reader questions
# Fix H (2026-10-18). The plain questions HELM asks when the English reader (helm_english_in.py) cannot restate a
# sentence without guessing. Two or more equally-correct wordings each; slots come only from the reader.
READER_QUESTIONS: Dict[str, List[str]] = {
    "NO_NUMBER": ["How much {item} is there?",
                  "How much {item} do we have? I need the number before I can use it."],
    "NO_NUMBER_COUNTABLE": ["How many {item} are there?",
                            "How many {item} do we have? I need the number before I can use it."],
    "NEGATED_AMOUNT": ["You said we don't have {words}. How much {item} is there?",
                       "So not {words}. How much {item} do we have, then?"],
    "APPROXIMATE": ["You said {hedge} {words}. I only work with exact amounts, so how much {item} is there exactly?",
                    "I need an exact number, not {hedge} {words}. How much {item} is there?"],
    "WHAT_IF": ["Is {words} what we have right now? If it is, say \"we have {words}\" and I'll work from it.",
                "Do we really have {words} on hand, or is that a what-if? I only work from what's actually here."],
    "WHAT_IF_ABSENT": ["Are you telling me we're out of {item} right now? If so, say \"we're out of {item}\" and "
                       "I'll note it.",
                       "Is the {item} really gone, or is that a what-if? I only work from what's actually here."],
    "RELATIVE_AMOUNT": ["Do you mean {words} in total, or {words} on top of what's there? I don't want to guess.",
                        "Is that {words} all together, or on top of what we had? I'd rather ask than guess."],
    "UNKNOWN_INGREDIENT": ["I don't know an ingredient called {name}. I only keep track of {known}.",
                           "{Name} isn't one of the ingredients I know. I can work with {known}."],
    "UNKNOWN_PRODUCT": ["I don't know a recipe for {name}. I know {known}.",
                        "{Name} isn't something I have a recipe for. I can work out {known}."],
    "PRODUCT_AS_STOCK": ["I only keep track of ingredients ({known}), not finished {name}.",
                         "I count ingredients, not finished {name}. Which ingredients do you have, and how much?"],
    "NO_INGREDIENT_NAMED": ["{Words} of what?", "{Words} of which ingredient?"],
    "UNIT_MISMATCH": ["Earlier you gave {item} in {old_unit}, and now in {new_unit}. I won't convert between them, "
                      "so which one should I use?",
                      "You switched {item} from {old_unit} to {new_unit}. I don't convert units, so which should "
                      "I go with?"],
    "CONVERSION_REFUSED": ["I don't convert between {units}. That would be a guess on my part. Tell me the amount "
                           "in the unit you're actually using.",
                           "Switching between {units} would mean guessing, so I won't. Which amount should I use, "
                           "in one unit?"],
    "CONVERSION_REFUSED_PLAIN": ["I don't convert between units. That would be a guess on my part. Tell me the "
                                 "amount in the unit you're actually using.",
                                 "Converting units would mean guessing, so I won't. Which amount should I use, in "
                                 "one unit?"],
    "CONTRADICTION": ["You gave me two different things for {item}: {a} and {b}. Which one is right?",
                      "I heard both {a} and {b} for {item}. Which is it?"],
    "MULTIPLE_PRODUCTS": ["Let's take one at a time: {a} or {b} first?",
                          "One at a time is easier. Should I start with {a} or {b}?"],
    "WHICH_PRODUCT": ["Which one do you want me to work out: {known}?", "Sure. Which one: {known}?"],
    "STATED_RECIPE": ["I can't take a recipe as stated. I learn how much each ingredient needs from batches you "
                      "actually made: what you started with, how much you made, and what ran out first.",
                      "I don't take recipes on word alone. Tell me about a batch you actually made: what you started "
                      "with, how much it made, and what ran out first."],
    "BATCH_NEEDS_RAN_OUT": ["Which ingredient ran out first in that batch?", "In that batch, what ran out first?"],
    "BATCH_TWO_RAN_OUT": ["Which one ran out first: {a} or {b}?",
                          "Only one can run out first. Was it the {a} or the {b}?"],
    "BATCH_NEEDS_MADE": ["How much {product} did that batch make?", "And how much {product} came out of it?"],
    "BATCH_NEEDS_MADE_PLAIN": ["What did that batch make, and how much of it?",
                               "What came out of that batch, and how much?"],
    "BATCH_NEEDS_PRODUCT": ["What did that batch make: {words} of what?", "{Words} of what, in that batch?"],
    "BATCH_NEEDS_STOCK": ["How much of each ingredient did you start that batch with?",
                          "What did that batch start with? I need the amount of each ingredient."],
    # rule 6 (STOCK_FRAME_REQUIRED, 2026-10-19): an amount or absence said, but not as what we have on hand
    "NO_STOCK_FRAME": ["Is {words} what we have on hand right now? If it is, say \"we have {words}\" and I'll "
                       "save it.",
                       "Do we have {words} on hand right now? I only save stock when you tell me it's what we have."],
    "NO_STOCK_FRAME_ABSENT": ["Are you telling me we're out of {item} right now? If so, say \"we're out of {item}\" "
                              "and I'll note it.",
                              "Is the {item} really gone from what we have? I only note that when you tell me."],
    "ROUND_TRIP_FAILED": ["I couldn't read that back exactly the way you said it, so I didn't act on it. Could you "
                          "say it another way?",
                          "I couldn't restate that exactly, so I left it alone. Could you put it another way?"],
}


def reader_question_variants(code: str, slots: Dict[str, Any]) -> List[str]:
    """The filled wordings for one reader question. Unknown codes fall back to the round-trip question."""
    key = code
    if code == "NO_NUMBER" and slots.get("countable"):
        key = "NO_NUMBER_COUNTABLE"
    if code == "CONVERSION_REFUSED" and not slots.get("units"):
        key = "CONVERSION_REFUSED_PLAIN"
    if code == "BATCH_NEEDS_MADE" and not slots.get("product"):
        key = "BATCH_NEEDS_MADE_PLAIN"
    if code == "APPROXIMATE" and not slots.get("hedge"):
        slots = dict(slots, hedge="roughly")
    filled = {k: str(v) for k, v in slots.items() if v is not None and not isinstance(v, bool)}
    for k in list(filled):
        filled[k[:1].upper() + k[1:]] = cap(filled[k])
    out = []
    for tpl in READER_QUESTIONS.get(key, READER_QUESTIONS["ROUND_TRIP_FAILED"]):
        if slots.get("countable"):                    # countable things: "how many eggs are there"
            tpl = (tpl.replace("how much {item} is there", "how many {item} are there")
                   .replace("How much {item} is there", "How many {item} are there")
                   .replace("how much {item} do we have", "how many {item} do we have")
                   .replace("How much {item} do we have", "How many {item} do we have"))
        try:
            out.append(fill(tpl, filled))
        except KeyError:
            continue
    return out or list(READER_QUESTIONS["ROUND_TRIP_FAILED"])


def reader_question_text(code: str, slots: Dict[str, Any]) -> str:
    """The first wording (used by the loop for its own message and the trace)."""
    return reader_question_variants(code, dict(slots or {}))[0]


# --------------------------------------------------------------------------------------------- mood vs facts
# MOOD_FACT_CLASH_CHECK -- ENGINEERED-NOT-VALIDATED. HELM does NOT understand sarcasm. This is one written rule:
# when the user's words carry a clearly positive mood word and the brain's receipt is a refusal, a missing
# ingredient or an "I can't tell", the voice adds ONE plain question. It never changes the facts.
MOOD_FACT_CLASH_LABEL = "MOOD_FACT_CLASH_CHECK"
MOOD_FACT_CLASH_STATUS = "ENGINEERED-NOT-VALIDATED"
MOOD_WORDS = ("great", "perfect", "love it", "wonderful", "awesome", "fantastic", "excellent", "amazing",
              "brilliant", "lovely")                                       # the 10-word list
CLASH_SITUATIONS = ("blocked_missing", "refused", "cant_determine", "never_learned", "faded")


def mood_word(user_text: Optional[str]) -> Optional[str]:
    """The first positive mood word in the user's text that is not negated ('not great' does not count)."""
    t = (user_text or "").lower().replace("’", "'")
    best = None
    for w in MOOD_WORDS:
        for m in re.finditer(r"(?<![\w'])%s(?![\w'])" % re.escape(w), t):
            before = t[max(0, m.start() - 16):m.start()]
            if re.search(r"(?:\bnot|n't|\bnever|\bno)\s+(?:so\s+|very\s+|that\s+|too\s+)?$", before):
                continue
            if best is None or m.start() < best[0]:
                best = (m.start(), w)
    return best[1] if best else None


def mood_fact_clash(user_text: Optional[str], r: Dict[str, Any], situation: str) -> Dict[str, Any]:
    word = mood_word(user_text)
    rec: Dict[str, Any] = {"label": MOOD_FACT_CLASH_LABEL, "status": MOOD_FACT_CLASH_STATUS, "word": word,
                           "situation": situation, "asked": False}
    if word is None or situation not in CLASH_SITUATIONS:
        return rec
    if situation == "blocked_missing" and r.get("missing"):
        but = "there's no %s on hand that I know of" % say_list(list(r["missing"]))
    elif situation == "never_learned":
        but = "I haven't been taught that part yet"
    elif situation == "refused":
        but = "I couldn't use that"
    else:
        but = "I couldn't give a sure answer"
    question = "You said '%s', but %s. Did you mean that?" % (word, but)
    names_ok = _names_in(question) <= ({_norm_name(n) for n in r.get("missing") or []} |
                                       _names_in(" ".join(r.get("missing") or [])))
    if cas_tokens(question) or _numbers_in(question) or not names_ok:
        rec["refused_by_guard"] = True
        return rec
    rec.update(asked=True, question=question)
    return rec


# --------------------------------------------------------------------------------------------- loop adapter
_MISSING_MSG_RX = re.compile(r"missing essential ingredients: (.+?)\.", re.I)


def receipt_from_loop_result(res: Dict[str, Any], effective_inputs: Optional[Dict[str, Any]] = None,
                             units: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Turn a helm_end_to_end_loop.process_turn result into a voice receipt. None = not a recipe receipt.
    `units` (fix H): the unit words the user gave per ingredient, so the voice can say '12 cups'."""
    status = str(res.get("loop_status") or "")
    rid = res.get("receipt_hash")
    inputs = effective_inputs or {}
    if status == "SUCCESS_EVALUATED":
        lim = res.get("limiting_reagent")
        product = (res.get("recipe_receipt") or {}).get("product")
        # the yield's unit: the word the user counted this product in when teaching it ("loaves"), else "units"
        unit = (units or {}).get(product) if product else None
        r: Dict[str, Any] = {"kind": "ANSWER", "situation": "success", "yield_value": str(res.get("output_value")),
                             "limiting": lim, "unit": unit or "units", "receipt_id": rid}
        if lim in inputs:
            r["limiting_qty"] = str(inputs[lim])
            if units and units.get(lim):
                r["limiting_unit"] = units[lim]
        return r
    if status.startswith("CLARIFY_ENGLISH_"):
        clarify = (res.get("english_in") or {}).get("clarify") or {"code": status[len("CLARIFY_ENGLISH_"):],
                                                                    "slots": {}}
        return {"kind": "CLARIFY", "situation": "dont_know", "reader_question": clarify, "receipt_id": rid}
    said = str(res.get("everyday_english_response") or res.get("response") or res.get("text") or "")
    if status.startswith("VALVE_HALT") or status == "RECIPE_BRAIN_REFUSAL":
        if status == "RECIPE_BRAIN_REFUSAL":
            missing = [res.get("limiting_reagent")] if res.get("limiting_reagent") else []
        else:
            telem = res.get("valve_telemetry") or {}
            missing = list(telem.get("missing_reagents") or [])
            if not missing:
                m = _MISSING_MSG_RX.search(said)
                missing = [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []
        if not missing:
            return None
        return {"kind": "REFUSE", "situation": "blocked_missing", "missing": missing, "receipt_id": rid}
    # --- statuses of the wired loop (fix C, 2026-10-18): the gate / brain said "can't tell yet" ---
    if status == "UNDETERMINED_CLARIFY":
        m = (re.search(r"don't know how much (.+?) we have", said)
             or re.search(r"there's no (.+?) on hand\. When there is", said)
             or re.search(r"missing how much (.+?) you started with", said)
             or re.search(r"missing (?:essential )?ingredients?: (.+?)[.\n]", said))
        if m:
            names = [x.strip() for x in re.split(r",| and | or ", m.group(1)) if x.strip()]
            if names:
                return {"kind": "REFUSE", "situation": "blocked_missing", "missing": names, "receipt_id": rid}
        m = re.search(r"how much (.+?) goes into", said)
        if m:
            names = [x.strip() for x in re.split(r",| and | or ", m.group(1)) if x.strip()]
            return {"kind": "UNDETERMINED", "situation": "never_learned", "lacunae": names, "receipt_id": rid}
        return {"kind": "UNDETERMINED", "situation": "cant_determine", "receipt_id": rid}
    if status == "BRAIN_UNDETERMINED":
        return {"kind": "UNDETERMINED", "situation": "cant_determine", "receipt_id": rid}
    if status == "WITNESS_ADMITTED":
        rec = res.get("recipe_receipt") or {}
        learned = f"{rec.get('ran_out', 'one ingredient')} per batch of {rec.get('product') or 'that'}"
        # fix H: the loop's own line says the learned requirement exactly ("Learned: one Bread needs 2 Flour.")
        m = re.search(r"Learned: one (\w+) needs (\S+) (\w+)\.", said)
        if m:
            learned = "one %s needs %s %s" % (say_name(m.group(1)), m.group(2), say_name(m.group(3)))
        return {"kind": "ANSWER", "situation": "learned", "learned": learned, "receipt_id": rid}
    if status == "REPAIRED_RETEACH_NEEDED":
        return {"kind": "ANSWER", "situation": "repaired", "repair": "the batches agree on a second look",
                "receipt_id": rid}
    if status in ("CONFLICT_UNDETERMINED", "REFUSE_RECEIPT_INCONSISTENT") or status.startswith("TEACH_REFUSED_"):
        reason = ("that batch contradicts what I already know" if status == "CONFLICT_UNDETERMINED"
                  else "my own check did not hold")
        return {"kind": "REFUSE", "situation": "refused", "reason": reason, "receipt_id": rid}
    if (status.startswith("CLARIFY") or status in ("VERIFIED_NO_RECIPE_CONTENT", "STATED_RECIPE_NOT_TAKEN",
                                                   "REFUSE_NOT_VERIFIED")):
        return {"kind": "CLARIFY", "situation": "dont_know", "receipt_id": rid}
    return None
