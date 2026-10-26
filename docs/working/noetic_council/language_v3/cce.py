"""CCE v0.1: Controlled Core English <-> CAS content. Deterministic parser and renderer.

Built 2026-10-14 (Pacific) from GRAMMAR_CCE_v0_1.md (frozen first; sha256 in FROZEN.json) and the design in
cas_language_first_principles_map_v1/ (MAP.md section A, TRANSLATOR_SPEC.md section 3, cce_sketch.py).

* parse(text) -> content dict (GRAMMAR section 9), or raises Refusal(code).
* render(content, rng=None) -> text. rng=None gives the fixed twin (CANON wording, canonical order).
  With a seeded random.Random, it PROPOSES a wording (template, tail order, term order, name-or-definition,
  number words). Randomness never touches content: names, numbers and slots are copied.
* normalize(content) -> canonical JSON string (the only equality used by the round trip).
* round_trip(content, rng=None) -> receipt; ok only if parse(render(content)) == content after normalization.
* say(content, seed) -> seeded wording draw with read-back, cap 8, then the fixed twin. 'I cannot tell.' is
  never drawn.
* Numbers are exact. A written number may be digits with decimals, one of the words one..ten/half, or p/q (the
  owner's Q13 ruling). Nothing rounds: a value with an exact decimal form is written as that decimal and one
  without is written as reduced p/q. Asking for a decimal a value does not have raises LOSSY_CONVERSION_REFUSED.
* Turn forms: ANSWER, ACK, CLARIFY, REFUSE_CLAIM, REFUSE and CLOSE. Any other turn type raises; it is never
  collapsed into one of these.

Stdlib only. No IO. No floats in content.
"""
from fractions import Fraction
import hashlib
import itertools
import json
import random
import re

CCE_VERSION = "cce-v0.1"
MAX_NEST_DEPTH = 2          # OPEN_QUESTIONS Q9 default
DRAW_CAP = 8                # OPEN_QUESTIONS Q16 default
FIXED_UNDETERMINED = "I cannot tell."
BARE_CLOSE = "That closes the turn."       # the CLOSE turn with nothing named
REFUSE_LEAD = "I will not do that: "       # the REFUSE turn; its reason words carry the boundary_violation

# --- Canon (Clarification 1, verbatim; never edited) ---------------------------------------------------------
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
NOETIC_NAMES = {0: "Idea", 1: "Mind", 2: "Positive", 3: "Negative", 4: "Vibration", 5: "Female", 6: "Male",
                7: "Rhythm", 8: "Above/Cause", 9: "Below/Effect"}
DEF_REF = {n: "[" + d[:-1] + "]" for n, d in DEFINITIONS.items()}       # verbatim definition, final period dropped
DOMAINS = {"P": "principled", "C": "cognitive", "E": "evaluative", "O": "operational"}
REG_ORDER = "TAfE"
REGISTERS = {"T": "transcendent", "A": "analytical", "f": "affective", "E": "embodied"}
DRIVES = {"F1": "Unity", "F2": "Wisdom", "F3": "Vitality", "F4": "Connection", "F5": "Agency",
          "F6": "Structure", "F7": "Purpose"}                           # OPEN_QUESTIONS Q15 default
NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
                "eight": "8", "nine": "9", "ten": "10", "half": "0.5"}
WORD_OF_NUMBER = {v: k for k, v in NUMBER_WORDS.items()}
ACTS = ("intakes", "processes", "stores", "outputs")

NAME_RX = r"[A-Z][A-Za-z0-9_]*"
OMEGA_RX = r"Ω_[A-Za-z0-9_]+"
IDEA_RX = r'"[^"]+"|Ω_[A-Za-z0-9_]+|⟦[0-9]+⟧'
DIGITS_RX = r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"                     # 2 | 0.5 | 2.25
FRACTION_RX = r"(?:0|[1-9][0-9]*)/(?:[1-9][0-9]*)"                 # p/q, q >= 1  (owner's Q13 ruling)
NUM_RX = FRACTION_RX + "|" + DIGITS_RX + "|" + "|".join(NUMBER_WORDS)
WORD_RX = r"[a-z]+"

HEDGE_RX = re.compile(r"\b(might|maybe|perhaps|possibly|could|if|unless)\b", re.I)
VAGUE_RX = re.compile(r"\b(a lot of|some|a bit of|many|few|several|much)\b", re.I)
BANNED_RX = re.compile(r"\b(because|therefore|so|cause|causes|effect|effects)\b", re.I)
PRONOUN_RX = re.compile(r"\b(he|she|him|her|hers|his|they|them|their|theirs|it|its)\b", re.I)


class Refusal(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code + ": " + detail)
        self.code = code
        self.detail = detail


# --- Verbs (surface agreement only; NO-MAP morphology) ---------------------------------------------------------
def _regular(third, base):
    return {"3": third, "I": base, "you": base, "neg3": "does not " + base, "negI": "do not " + base,
            "negyou": "do not " + base}


def _past(past, base):
    return {"3": past, "I": past, "you": past, "neg3": "did not " + base, "negI": "did not " + base,
            "negyou": "did not " + base}


VERBS = {
    "is": {"3": "is", "I": "am", "you": "are", "neg3": "is not", "negI": "am not", "negyou": "are not"},
    "has": _regular("has", "have"),
    "intakes": _regular("intakes", "intake"), "processes": _regular("processes", "process"),
    "stores": _regular("stores", "store"), "outputs": _regular("outputs", "output"),
    "resonates": _regular("resonates", "resonate"), "triggers": _regular("triggers", "trigger"),
    "speaks": _regular("speaks", "speak"), "rubs": _regular("rubs", "rub"), "breaks": _regular("breaks", "break"),
    "unpacks": _regular("unpacks", "unpack"), "reminds": _regular("reminds", "remind"),
    "practices": _regular("practices", "practice"),
    "struck": _past("struck", "strike"), "made": _past("made", "make"), "came": _past("came", "come"),
}

# --- The ten frames: (noetic, tier, template, act) ----------------------------------------------------------
# {M} Mind, {W} Mind inside "who ... is", {I}/{J} Ideas, {D} degree, {R} rate, {U} unit, {P} pattern.
# ~verb marks the polarity point. CANON first: the first template that fits a content is the fixed twin.
TEMPLATES = [
    (0, "CANON", '{I} ~is an Idea', None),
    (1, "CANON", '{M} ~intakes {I}', "intakes"), (1, "CANON", '{M} ~processes {I}', "processes"),
    (1, "CANON", '{M} ~stores {I}', "stores"), (1, "CANON", '{M} ~outputs {I}', "outputs"),
    (1, "ALIAS", '{M} ~is paying attention to {I}', None),
    (2, "CANON", '{M} ~has an affinity for {I}', None), (2, "CANON", '{M} ~is attracted toward {I}', None),
    (2, "ALIAS", '{M} ~is drawn to {I}', None), (2, "ALIAS", '{I} ~speaks to {M}', None),
    (3, "CANON", '{M} ~is adverse to {I}', None), (3, "CANON", '{M} ~is repelled by {I}', None),
    (3, "ALIAS", '{I} ~rubs {M} the wrong way', None),
    (4, "CANON", '{I} ~resonates with {M} to degree {D}', None), (4, "CANON", '{I} ~resonates with {M}', None),
    (4, "ALIAS", '{I} ~struck a chord with {M}, degree {D}', None), (4, "ALIAS", '{I} ~struck a chord with {M}', None),
    (4, "ALIAS", '{I} ~made an impression on {M}, degree {D}', None),
    (4, "ALIAS", '{I} ~made an impression on {M}', None),
    (5, "CANON", '{M} ~is impregnated with {I}', None), (5, "CANON", '{M} ~is composed of {I}', None),
    (5, "ALIAS", '{I} ~is part of who {W}', None),
    (6, "CANON", '{I} ~is impregnated with {J}', None), (6, "CANON", '{I} ~is composed of {J}', None),
    (6, "ALIAS", '{I} ~breaks down into {J}', None), (6, "ALIAS", '{M} ~breaks {I} down into {J}', None),
    (6, "ALIAS", '{M} ~breaks down {I} into {J}', None), (6, "ALIAS", '{M} ~unpacks {I} into {J}', None),
    (7, "CANON", '{M} ~is exposed to {I} at rate {R} per {U}, pattern {P}', None),
    (7, "CANON", '{M} ~is exposed to {I}', None),
    (7, "ALIAS", '{M} ~practices {I} at rate {R} per {U}, pattern {P}', None),
    (8, "CANON", '{I} ~triggers {J} to come to {M}', None),
    (8, "ALIAS", '{I} ~reminds {M} of {J}', None), (8, "ALIAS", '{I} ~made {M} think of {J}', None),
    (9, "CANON", '{J} ~is brought to {M} by {I}', None),
    (9, "CANON", '{J} ~is brought to {M} by an unknown trigger', None),
    (9, "ALIAS", '{J} ~came to {M} from {I}', None), (9, "ALIAS", '{J} ~came to {M} out of nowhere', None),
]
_TOKEN = re.compile(r"(\{[A-Z]\}|~\w+)")


def _slotset(template, act):
    keys = {("M" if k == "W" else k) for k in re.findall(r"\{([A-Z])\}", template)}
    if act:
        keys.add("ACT")
    return frozenset(keys)


def _build(template, kind):
    """Anchored regex for one template and one subject kind ('3', 'I', 'you')."""
    pieces = [p for p in _TOKEN.split(template) if p]
    subject_m = pieces[0] == "{M}"
    vk = kind if subject_m else "3"
    out = []
    for i, p in enumerate(pieces):
        if p == "{M}":
            if i == 0:
                out.append({"I": "(?P<M>I)", "you": "(?P<M>you)"}.get(kind, r"(?P<M>(?!I\b|me\b|you\b)" + NAME_RX + ")"))
            else:
                out.append(r"(?P<M>me|I|you|" + NAME_RX + ")")
        elif p == "{W}":
            out.append(r"(?P<W>I am|you are|" + NAME_RX + " is)")
        elif p in ("{I}", "{J}"):
            out.append("(?P<%s>%s)" % (p[1], IDEA_RX))
        elif p in ("{D}", "{R}"):
            out.append("(?P<%s>%s)" % (p[1], NUM_RX))
        elif p in ("{U}", "{P}"):
            out.append("(?P<%s>%s)" % (p[1], WORD_RX))
        elif p.startswith("~"):
            forms = VERBS[p[1:]]
            out.append("(?:(?P<neg>%s)|%s)" % (re.escape(forms["neg" + vk]), re.escape(forms[vk])))
        else:
            out.append(re.escape(p))
    return re.compile("^" + "".join(out) + "$")


def _loose(template):
    """Same shape, any name in any slot: used only to tell SLOT_TYPE from NOT_CCE."""
    anyname = r'(?:me|I|you|' + NAME_RX + '|"[^"]+"|' + OMEGA_RX + r'|⟦[0-9]+⟧)'
    pieces = [p for p in _TOKEN.split(template) if p]
    out = []
    for p in pieces:
        if p in ("{M}", "{I}", "{J}"):
            out.append(anyname)
        elif p == "{W}":
            out.append(r"(?:I am|you are|\S+ is)")
        elif p in ("{D}", "{R}"):
            out.append("(?:%s)" % NUM_RX)
        elif p in ("{U}", "{P}"):
            out.append(WORD_RX)
        elif p.startswith("~"):
            forms = VERBS[p[1:]]
            out.append("(?:%s)" % "|".join(re.escape(f) for f in sorted(set(forms.values()), key=len, reverse=True)))
        else:
            out.append(re.escape(p))
    return re.compile("^" + "".join(out) + "$")


FRAME_TABLE = []
for _idx, (_n, _tier, _tpl, _act) in enumerate(TEMPLATES):
    _kinds = ("3", "I", "you") if _tpl.startswith("{M}") else ("3",)
    for _k in _kinds:
        FRAME_TABLE.append({"idx": _idx, "noetic": _n, "tier": _tier, "template": _tpl, "act": _act, "kind": _k,
                            "slots": _slotset(_tpl, _act), "rx": _build(_tpl, _k)})
LOOSE_TABLE = [(_tpl, _loose(_tpl)) for (_n, _tier, _tpl, _act) in TEMPLATES]


# --- Numbers: exact values only, and the p/q form (owner's Q13 ruling) ---------------------------------------
# The ruler for this section is NOTHING ROUNDS. A written number is read as an exact fractions.Fraction, never as
# a float and never as a rounded decimal. One value has one canonical text: a value with an exact finite decimal
# form is written as that decimal ('0.25', '2'), and a value with no such form is written as reduced p/q ('1/3',
# '22/7'). So '1/4' and '0.25' are one quantity, and '2/6' is read as 1/3 and written '1/3'.
# Asking for a decimal of a value that has none raises Refusal LOSSY_CONVERSION_REFUSED. That is the rule the
# reference implementation at docs/working/noetic_council/language_v2/numbers.py calls LOSSY_CONVERSION_REFUSED,
# and it is the reason 1/3 could not be said before: a fraction had no form at all.
def fraction_value(text):
    """Exact value of one written number: 'half' -> 1/2, '0.25' -> 1/4, '1/3' -> 1/3. Never a float."""
    t = NUMBER_WORDS.get(text, text)
    try:
        return Fraction(t)
    except (ValueError, ZeroDivisionError, TypeError):
        raise Refusal("NOT_CCE", "not a number: %r" % (text,))


def is_terminating(value):
    """True when the value has an exact finite decimal form: its denominator is 2^a * 5^b and nothing else."""
    denominator = value.denominator
    for prime in (2, 5):
        while denominator % prime == 0:
            denominator //= prime
    return denominator == 1


def _place(scaled, places):
    sign = "-" if scaled < 0 else ""
    digits = str(abs(scaled))
    if places == 0:
        return sign + digits
    digits = digits.rjust(places + 1, "0")
    whole, part = digits[:-places], digits[-places:]
    part = part.rstrip("0")
    return sign + whole if not part else sign + whole + "." + part


def fraction_text_of(value):
    """The p/q form of an exact value. An integer keeps no denominator: 4 -> '4', Fraction(1,3) -> '1/3'."""
    if value.denominator == 1:
        return str(value.numerator)
    return "%d/%d" % (value.numerator, value.denominator)


def _decimal_of(value):
    """The exact decimal text, by integer arithmetic on the reduced value. Refuses when no exact form exists."""
    if not is_terminating(value):
        raise Refusal("LOSSY_CONVERSION_REFUSED",
                      "%s has no exact decimal form: denominator %d has a prime factor other than 2 or 5"
                      % (fraction_text_of(value), value.denominator))
    denominator, twos, fives = value.denominator, 0, 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    places = max(twos, fives)
    return _place(value.numerator * (10 ** places) // value.denominator, places)


def num(text):
    """Exact canonical text: '2.0' -> '2', 'half' -> '0.5', '1/4' -> '0.25', '1/3' -> '1/3'. Raises Refusal."""
    value = fraction_value(text)
    return _decimal_of(value) if is_terminating(value) else fraction_text_of(value)


def decimal_text(text):
    """The exact decimal form of a written number, or Refusal LOSSY_CONVERSION_REFUSED. Never rounds."""
    return _decimal_of(fraction_value(text))


# --- Normalization ---------------------------------------------------------------------------------------------
def _regs(r):
    if r is None:
        return None
    return sorted(set(r), key=REG_ORDER.index)


def _norm_slots(slots):
    out = {}
    for k, v in slots.items():
        if isinstance(v, dict):
            out[k] = {"that": norm_term(v["that"])}
        elif k in ("D", "R"):
            out[k] = num(v)
        else:
            out[k] = v
    return out


def norm_term(t):
    return {"noetic": t["noetic"], "domain": t.get("domain"), "register": _regs(t.get("register")),
            "drive": t.get("drive"), "polarity": t.get("polarity", "ASSERTED"), "slots": _norm_slots(t.get("slots", {}))}


def norm_state(s):
    return {"noetic": s["noetic"], "domain": s.get("domain"), "register": _regs(s.get("register")),
            "drive": s.get("drive")}


def _norm_rterm(t):
    kind = t.get("kind")
    if kind == "state":
        out = norm_state(t)
        out.update({"kind": "state", "coefficient": num(t["coefficient"])})
        return out
    if kind == "outcome":
        return {"kind": "outcome", "coefficient": num(t["coefficient"]), "name": t["name"]}
    if kind == "emergent":
        return {"kind": "emergent", "coefficient": num(t["coefficient"]),
                "components": sorted((norm_state(c) for c in t["components"]), key=_key), "result": t["result"]}
    raise ValueError("unknown recipe term kind %r" % kind)


def _key(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def _norm_rel(r):
    if r[0] == "one_of":
        return [r[0], r[1], sorted(set(r[2]))]
    return list(r)


def canonical(c):
    """Fill absent fields with their empty value and normalize. Returns a plain dict."""
    rec = c.get("recipe")
    if rec is not None:
        rec = {"omega": rec["omega"], "terms": sorted((_norm_rterm(t) for t in rec.get("terms", [])), key=_key),
               "leakage": sorted(({"coefficient": num(k["coefficient"]), "side": k["side"],
                                   "implicit": bool(k.get("implicit", False))} for k in rec.get("leakage", [])), key=_key),
               "catalysts": sorted(rec.get("catalysts", [])), "inhibitors": sorted(rec.get("inhibitors", []))}
    stocks = []
    for s in c.get("stocks", []) or []:
        ref = s["ref"]
        ref = {"outcome": ref["outcome"]} if "outcome" in ref else norm_state(ref)
        stocks.append({"amount": num(s["amount"]), "ref": ref})
    return {"turn": c.get("turn") or "ANSWER", "evidence": c.get("evidence") or "NONE",
            "gate": c.get("gate") or "RIGHT_PATH", "topic": c.get("topic"),
            "terms": sorted((norm_term(t) for t in c.get("terms", []) or []), key=_key),
            "sequence": [norm_term(t) for t in c.get("sequence", []) or []],
            "recipe": rec, "stocks": sorted(stocks, key=_key),
            "relations": sorted((_norm_rel(r) for r in c.get("relations", []) or []), key=_key),
            "fractal": list(c.get("fractal", []) or []), "lacunae": sorted(c.get("lacunae", []) or []),
            "reason": c.get("reason")}


def normalize(c):
    return json.dumps(canonical(c), sort_keys=True, ensure_ascii=False)


def digest(c):
    return hashlib.sha256(normalize(c).encode("utf-8")).hexdigest()


def empty_content():
    return {"turn": "ANSWER", "evidence": "NONE", "gate": "RIGHT_PATH", "topic": None, "terms": [], "sequence": [],
            "recipe": None, "stocks": [], "relations": [], "fractal": [], "lacunae": [], "reason": None}


# --- Splitting helpers -----------------------------------------------------------------------------------------
def _split_top(text, sep):
    """Split on the literal sep outside quotes, square brackets, braces and parentheses."""
    parts, depth, inq, start, i = [], 0, False, 0, 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            inq = not inq
        elif not inq and ch in "[({":
            depth += 1
        elif not inq and ch in "])}":
            depth -= 1
        elif not inq and depth == 0 and text.startswith(sep, i):
            parts.append(text[start:i])
            i += len(sep)
            start = i
            continue
        i += 1
    parts.append(text[start:])
    return parts


def split_sentences(text):
    out, depth, inq, start = [], 0, False, 0
    for i, ch in enumerate(text):
        if ch == '"':
            inq = not inq
        elif not inq and ch in "[({":
            depth += 1
        elif not inq and ch in "])}":
            depth -= 1
        elif not inq and depth == 0 and ch in ".?" and (i + 1 == len(text) or text[i + 1] == " "):
            out.append(text[start:i + 1].strip())
            start = i + 1
    rest = text[start:].strip()
    if rest:
        raise Refusal("NOT_CCE", "a CCE sentence ends with '.' or '?': " + rest[:80])
    return [s for s in out if s]


def _masked(text):
    t = re.sub(r'"[^"]*"', '""', text)
    for d in DEF_REF.values():
        t = t.replace(d, "[]")
    return t.replace("Above/Cause", "AboveName").replace("Below/Effect", "BelowName")


def _global_checks(text):
    m = _masked(text)
    if HEDGE_RX.search(m):
        raise Refusal("HEDGE", HEDGE_RX.search(m).group(1))
    if VAGUE_RX.search(m):
        raise Refusal("VAGUE_QUANTITY", VAGUE_RX.search(m).group(1))
    if BANNED_RX.search(m):
        raise Refusal("NOT_CCE", "banned marker word: " + BANNED_RX.search(m).group(1))
    if PRONOUN_RX.search(m.replace("What is it?", "")):
        raise Refusal("NOT_CCE", "third-person pronoun: " + PRONOUN_RX.search(m.replace("What is it?", "")).group(1))


# --- Tail: domain / register / drive, any order, each at most once ---------------------------------------------
_REGSET_RX = re.compile(r"in ((?:[a-z]+, )*[a-z]+) and ([a-z]+) registers")


def split_tail(body):
    """Return (core, domain, register, drive, order) peeling tail items off the right end."""
    holder = {}

    def keep(m):
        holder[len(holder)] = m.group(0)
        return "⟪%d⟫" % (len(holder) - 1)
    work = _REGSET_RX.sub(keep, body)
    chunks = _split_top(work, ", ")
    domain = register = drive = None
    order = []
    while len(chunks) > 1:
        last = chunks[-1]
        item = _tail_item(last, holder)
        if item is None:
            break
        kind, value = item
        if kind in order:
            raise Refusal("NOT_CCE", "tail item twice: " + kind)
        order.append(kind)
        if kind == "domain":
            domain = value
        elif kind == "register":
            register = value
        else:
            drive = value
        chunks.pop()
    core = ", ".join(chunks)
    for k, v in holder.items():
        core = core.replace("⟪%d⟫" % k, v)
    order.reverse()
    return core, domain, register, drive, order


def _tail_item(chunk, holder):
    for k, v in DOMAINS.items():
        if chunk == v:
            return ("domain", k)
    for k, v in REGISTERS.items():
        if chunk == v + " register":
            return ("register", [k])
    m = re.fullmatch(r"⟪([0-9]+)⟫", chunk)
    if m:
        rm = _REGSET_RX.fullmatch(holder[int(m.group(1))])
        names = [x.strip() for x in rm.group(1).split(",")] + [rm.group(2)]
        inv = {v: k for k, v in REGISTERS.items()}
        if not all(n in inv for n in names):
            raise Refusal("NOT_CCE", "register set word")
        letters = [inv[n] for n in names]
        if len(set(letters)) != len(letters):
            raise Refusal("NOT_CCE", "register named twice in a set")
        return ("register", letters)
    m = re.fullmatch(r"for ([A-Z][a-z]+)", chunk)
    if m:
        for k, v in DRIVES.items():
            if v == m.group(1):
                return ("drive", k)
    return None


def render_tail(domain, register, drive, order=None):
    items = {}
    if domain is not None:
        items["domain"] = DOMAINS[domain]
    if register is not None:
        names = [REGISTERS[r] for r in _regs(register)]
        items["register"] = (names[0] + " register" if len(names) == 1
                             else "in " + ", ".join(names[:-1]) + " and " + names[-1] + " registers")
    if drive is not None:
        items["drive"] = "for " + DRIVES[drive]
    keys = [k for k in (order or ["domain", "register", "drive"]) if k in items]
    keys += [k for k in ("domain", "register", "drive") if k in items and k not in keys]
    return "".join(", " + items[k] for k in keys)


# --- Frames ------------------------------------------------------------------------------------------------------
def _replace_nests(core):
    """Replace top-level 'that [ ... ]' spans with ⟦k⟧. Returns (text, [inner texts])."""
    out, inners, i = [], [], 0
    while True:
        j = core.find("that [", i)
        if j < 0:
            out.append(core[i:])
            break
        out.append(core[i:j])
        depth, k = 0, j + 5
        while k < len(core):
            if core[k] == "[":
                depth += 1
            elif core[k] == "]":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth != 0:
            raise Refusal("NOT_CCE", "unclosed nesting bracket")
        inners.append(core[j + 6:k])
        out.append("⟦%d⟧" % (len(inners) - 1))
        i = k + 1
    return "".join(out), inners


def nest_depth(text):
    depth = best = 0
    for m in re.finditer(r"that \[|\[|\]", text):
        if m.group(0) == "that [":
            depth += 1
            best = max(best, depth)
        elif m.group(0) == "]" and depth > 0:
            depth -= 1
    return best


def parse_frame(body, minds, depth=0, max_depth=MAX_NEST_DEPTH):
    """body = one frame with its tail, no final period."""
    if depth == 0 and nest_depth(body) > max_depth:
        raise Refusal("NEST_TOO_DEEP", "nesting deeper than %d" % max_depth)
    core, domain, register, drive, _ = split_tail(body)
    if "combined" in _masked(core):
        raise Refusal("OPERATOR_DISCIPLINE", "'combined' outside a recipe emergent term with a named result")
    core2, inners = _replace_nests(core)
    hits = []
    for row in FRAME_TABLE:
        m = row["rx"].match(core2)
        if m:
            hits.append((row, m))
    if not hits:
        if any(rx.match(core2) for _, rx in LOOSE_TABLE):
            raise Refusal("SLOT_TYPE", core)
        raise Refusal("NOT_CCE", core)
    contents = {}
    for row, m in hits:
        g = {k: v for k, v in m.groupdict().items() if v is not None}
        slots = {}
        for k, v in g.items():
            if k == "neg":
                continue
            if k == "W":
                v = "I" if v == "I am" else ("you" if v == "you are" else v[:-3])
                k = "M"
            if k == "M" and v == "me":
                v = "I"
            if k in ("I", "J") and v.startswith("⟦"):
                inner = inners[int(v[1:-1])]
                v = {"that": parse_frame(inner, minds, depth + 1, max_depth)}
            if k in ("D", "R"):
                v = num(v)
            slots[k] = v
        if row["act"]:
            slots["ACT"] = row["act"]
        if "M" in slots and slots["M"] not in ("I", "you") and slots["M"] not in minds:
            raise Refusal("UNDECLARED_NAME", slots["M"])
        n = row["noetic"]
        if n in (8, 9) and "I" in slots and slots.get("I") == slots.get("J"):
            raise Refusal("SAME_IDEA_TRIGGER", "^%d needs a different Idea than itself" % n)
        if n == 6 and slots.get("I") == slots.get("J"):
            raise Refusal("SLOT_TYPE", "^6 needs another Idea")
        term = {"noetic": n, "domain": domain, "register": register, "drive": drive,
                "polarity": "DENIED" if m.group("neg") else "ASSERTED", "slots": slots}
        contents[_key(norm_term(term))] = term
    if len(contents) > 1:
        raise Refusal("AMBIGUOUS", core)
    return next(iter(contents.values()))


def _verb_kind(template, slots):
    if not template.startswith("{M}"):
        return "3"
    return {"I": "I", "you": "you"}.get(slots.get("M"), "3")


def frame_options(term):
    """Indexes into TEMPLATES that can say this term (slot set must match exactly; ^1 act must match)."""
    keys = frozenset(term["slots"].keys())
    out = []
    for idx, (n, tier, tpl, act) in enumerate(TEMPLATES):
        if n != term["noetic"] or _slotset(tpl, act) != keys:
            continue
        if n == 1 and act != term["slots"].get("ACT"):
            continue
        out.append(idx)
    return out


def render_frame(term, rng=None, words=False):
    opts = frame_options(term)
    if not opts:
        raise ValueError("no CCE frame can say this term (a FORM gap): noetic %s slots %s"
                         % (term["noetic"], sorted(term["slots"])))
    idx = opts[0] if rng is None else opts[rng.randrange(len(opts))]
    tpl = TEMPLATES[idx][2]
    slots = term["slots"]
    vk = _verb_kind(tpl, slots)
    denied = term.get("polarity", "ASSERTED") == "DENIED"
    pieces = [p for p in _TOKEN.split(tpl) if p]
    out = []
    for i, p in enumerate(pieces):
        if p == "{M}":
            v = slots["M"]
            out.append("me" if (i > 0 and v == "I") else v)
        elif p == "{W}":
            v = slots["M"]
            out.append({"I": "I am", "you": "you are"}.get(v, v + " is"))
        elif p in ("{I}", "{J}"):
            v = slots[p[1]]
            out.append("that [" + render_frame(v["that"], rng, words) + "]" if isinstance(v, dict) else v)
        elif p in ("{D}", "{R}"):
            v = num(slots[p[1]])
            out.append(WORD_OF_NUMBER[v] if (words and v in WORD_OF_NUMBER and rng is not None and rng.random() < 0.5) else v)
        elif p in ("{U}", "{P}"):
            out.append(slots[p[1]])
        elif p.startswith("~"):
            forms = VERBS[p[1:]]
            out.append(forms[("neg" + vk) if denied else vk])
        else:
            out.append(p)
    order = None
    if rng is not None:
        order = ["domain", "register", "drive"]
        rng.shuffle(order)
    return "".join(out) + render_tail(term.get("domain"), term.get("register"), term.get("drive"), order)


# --- Recipes, stocks, states -------------------------------------------------------------------------------------
_NAME_LIST = sorted(NOETIC_NAMES.items(), key=lambda kv: -len(kv[1]))


def parse_state(text, require_domain=True):
    ref = None
    for n, d in DEF_REF.items():
        if text.startswith(d):
            ref, rest = n, text[len(d):]
            break
    if ref is None:
        for n, name in _NAME_LIST:
            if text == name or text.startswith(name + ","):
                ref, rest = n, text[len(name):]
                break
    if ref is None:
        raise Refusal("NOT_CCE", "not a Noetic reference: " + text[:60])
    core, domain, register, drive, _ = split_tail("X" + rest)
    if core != "X":
        raise Refusal("NOT_CCE", "unread words after a Noetic reference: " + rest[:60])
    if require_domain and domain is None:
        raise Refusal("NOT_CCE", "a recipe state needs a Domain word")
    return {"noetic": ref, "domain": domain, "register": register, "drive": drive}


def _parse_result(text):
    if re.fullmatch(OMEGA_RX, text):
        return text
    m = re.fullmatch(r"(.+?), (principled|cognitive|evaluative|operational) named (%s)" % OMEGA_RX, text)
    inv = {v: k for k, v in NOETIC_NAMES.items()}
    dinv = {v: k for k, v in DOMAINS.items()}
    if m and m.group(1) in inv:
        return "^%d^%s|%s" % (inv[m.group(1)], dinv[m.group(2)], m.group(3))
    m = re.fullmatch(r"(.+?) named (%s)" % OMEGA_RX, text)
    if m and m.group(1) in inv:
        return "^%d|%s" % (inv[m.group(1)], m.group(2))
    raise Refusal("OPERATOR_DISCIPLINE", "x needs a named emergent result: " + text[:60])


def parse_rterm(text):
    m = re.fullmatch(r"(%s) of (.+)" % NUM_RX, text)
    if not m:
        raise Refusal("NOT_CCE", "recipe term: " + text[:60])
    coef, rest = num(m.group(1)), m.group(2)
    if fraction_value(coef) <= 0:
        raise Refusal("NOT_CCE", "a coefficient must be > 0")
    if rest.startswith("(") and rest.endswith(")"):
        inner = rest[1:-1]
        parts = _split_top(inner, " into ")
        if len(parts) < 2:
            raise Refusal("OPERATOR_DISCIPLINE", "'combined' with no named result")
        factors_text, result_text = " into ".join(parts[:-1]), parts[-1]
        factors = _split_top(factors_text, " combined with ")
        if len(factors) < 2:
            raise Refusal("OPERATOR_DISCIPLINE", "an emergent term needs at least two factors")
        result = _parse_result(result_text)
        return {"coefficient": coef, "kind": "emergent", "components": [parse_state(f) for f in factors],
                "result": result}
    if "combined" in rest:
        raise Refusal("OPERATOR_DISCIPLINE", "'combined' outside parentheses with a named result")
    if re.fullmatch(OMEGA_RX, rest):
        return {"coefficient": coef, "kind": "outcome", "name": rest}
    st = parse_state(rest)
    st.update({"coefficient": coef, "kind": "state"})
    return st


def render_state(s, rng=None):
    ref = NOETIC_NAMES[s["noetic"]]
    if rng is not None and rng.random() < 0.5:
        ref = DEF_REF[s["noetic"]]
    order = None
    if rng is not None:
        order = ["domain", "register", "drive"]
        rng.shuffle(order)
    return ref + render_tail(s.get("domain"), s.get("register"), s.get("drive"), order)


def _say_num(v, rng):
    v = num(v)
    if rng is not None and v in WORD_OF_NUMBER and rng.random() < 0.5:
        return WORD_OF_NUMBER[v]
    return v


def _render_result(r):
    m = re.fullmatch(r"\^([0-9])\^([PCEO])\|(%s)" % OMEGA_RX, r)
    if m:
        return "%s, %s named %s" % (NOETIC_NAMES[int(m.group(1))], DOMAINS[m.group(2)], m.group(3))
    m = re.fullmatch(r"\^([0-9])\|(%s)" % OMEGA_RX, r)
    if m:
        return "%s named %s" % (NOETIC_NAMES[int(m.group(1))], m.group(2))
    if re.fullmatch(OMEGA_RX, r):
        return r
    raise ValueError("unsayable emergent result %r" % r)


def render_rterm(t, rng=None):
    c = _say_num(t["coefficient"], rng)
    if t["kind"] == "outcome":
        return "%s of %s" % (c, t["name"])
    if t["kind"] == "emergent":
        comps = list(t["components"])
        if rng is not None:
            rng.shuffle(comps)
        return "%s of (%s into %s)" % (c, " combined with ".join(render_state(s, rng) for s in comps),
                                       _render_result(t["result"]))
    return "%s of %s" % (c, render_state(t, rng))


# --- Whole-text parse ----------------------------------------------------------------------------------------------
def parse(text, max_depth=MAX_NEST_DEPTH):
    if not isinstance(text, str) or not text.strip():
        raise Refusal("NOT_CCE", "empty")
    s = text.strip()
    c = empty_content()
    if s == FIXED_UNDETERMINED:
        c["gate"] = "UNDETERMINED"
        return c
    for lead, ev in (("I checked: ", "CHECKED"), ("You said: ", "USER_SAID")):
        if s.startswith(lead):
            s, c["evidence"] = s[len(lead):], ev
            break
    _global_checks(s)
    m = re.fullmatch(r"I need (.+) for (%s)\. What is it\?" % OMEGA_RX, s)
    if m:
        if not re.fullmatch(r"[a-z][a-z ]*(?: %s)?" % OMEGA_RX, m.group(1)):
            raise Refusal("NOT_CCE", "slot words")
        c.update({"turn": "CLARIFY", "topic": m.group(2), "lacunae": [m.group(1)]})
        return c
    m = re.fullmatch(r"I cannot support that: ([a-z][a-z ]*)\.", s)
    if m:
        c.update({"turn": "REFUSE_CLAIM", "reason": m.group(1)})
        return c
    m = re.fullmatch(re.escape(REFUSE_LEAD) + r"([a-z][a-z ]*)\.", s)
    if m:
        c.update({"turn": "REFUSE", "reason": m.group(1)})
        return c
    m = re.fullmatch(r"That closes (%s)\." % OMEGA_RX, s)
    if m:
        c.update({"turn": "CLOSE", "topic": m.group(1)})
        return c
    if s == BARE_CLOSE:
        c["turn"] = "CLOSE"
        return c
    m = re.fullmatch(r"Are we still on (%s)\?" % OMEGA_RX, s)
    if m:
        c.update({"turn": "CLARIFY", "topic": m.group(1)})
        return c
    minds = set()
    for sent in split_sentences(s):
        _parse_sentence(sent, c, minds, max_depth)
    return c


def _parse_sentence(sent, c, minds, max_depth):
    if sent.endswith("?"):
        raise Refusal("NOT_CCE", "question form not in CCE: " + sent[:60])
    body = sent[:-1]
    m = re.fullmatch(r"(New subject|Topic): (%s)" % OMEGA_RX, body)
    if m:
        if c["topic"] is not None:
            raise Refusal("NOT_CCE", "two topics")
        c["topic"] = m.group(2)
        if m.group(1) == "New subject":
            c["turn"] = "ACK"
        return
    m = re.fullmatch(r"(%s) is a Mind" % NAME_RX, body)
    if m and m.group(1) not in ("I",):
        minds.add(m.group(1))
        c["relations"].append(["is_a", m.group(1), "Mind"])
        return
    m = re.fullmatch(r"(%s) is one of \{(.+)\}" % IDEA_RX, body)
    if m:
        members = [x.strip() for x in _split_top(m.group(2), ", ")]
        if not all(re.fullmatch(r'"[^"]+"|' + OMEGA_RX, x) for x in members) or len(members) < 2:
            raise Refusal("NOT_CCE", "set members")
        c["relations"].append(["one_of", m.group(1), sorted(set(members))])
        return
    m = re.fullmatch(r'Fact: ("[^"]+"|%s) leads to ("[^"]+"|%s)' % (OMEGA_RX, OMEGA_RX), body)
    if m:
        c["relations"].append(["leads_to", m.group(1), m.group(2)])
        return
    m = re.fullmatch(r"(%s) needs (%s) first" % (OMEGA_RX, OMEGA_RX), body)
    if m:
        c["relations"].append(["needs_first", m.group(1), m.group(2)])
        return
    m = re.fullmatch(r'There is no ("[^"]+"|%s)' % OMEGA_RX, body)
    if m:
        c["relations"].append(["absent", m.group(1)])
        return
    m = re.fullmatch(r"There is (%s) of (.+)" % NUM_RX, body)
    if m:
        amount, ref = num(m.group(1)), m.group(2)
        ref = {"outcome": ref} if re.fullmatch(OMEGA_RX, ref) else parse_state(ref)
        c["stocks"].append({"amount": amount, "ref": ref})
        return
    m = re.fullmatch(r"To make (%s), use (.+)" % OMEGA_RX, body)
    if m:
        if c["recipe"] is not None:
            raise Refusal("NOT_CCE", "two recipes in one text")
        c["recipe"] = {"omega": m.group(1), "terms": [parse_rterm(t) for t in _split_top(m.group(2), "; plus ")],
                       "leakage": [], "catalysts": [], "inhibitors": []}
        return
    m = re.fullmatch(r"Side product: (?:(%s) of )?(%s)" % (NUM_RX, OMEGA_RX), body)
    if m:
        if c["recipe"] is None:
            raise Refusal("NOT_CCE", "side product with no recipe")
        implicit = m.group(1) is None
        c["recipe"]["leakage"].append({"coefficient": "1" if implicit else num(m.group(1)), "side": m.group(2),
                                       "implicit": implicit})
        return
    m = re.fullmatch(r"(Helped|Slowed) by (%s)" % OMEGA_RX, body)
    if m:
        if c["recipe"] is None:
            raise Refusal("NOT_CCE", "catalyst or inhibitor with no recipe")
        c["recipe"]["catalysts" if m.group(1) == "Helped" else "inhibitors"].append(m.group(2))
        return
    m = re.fullmatch(r"The fractal sequence is (.+)", body)
    if m:
        inv = {v: k for k, v in NOETIC_NAMES.items()}
        names = m.group(1).split(" : ")
        if not 2 <= len(names) <= 4 or not all(n in inv for n in names):
            raise Refusal("NOT_CCE", "fractal sequence")
        c["fractal"] = [inv[n] for n in names]
        return
    if body.startswith("First "):
        steps = _split_top(body[len("First "):], "; then ")
        if len(steps) < 2:
            raise Refusal("NOT_CCE", "a sequence needs '; then'")
        c["sequence"] = [parse_frame(st, minds, 0, max_depth) for st in steps]
        return
    c["terms"].append(parse_frame(body, minds, 0, max_depth))


# --- Whole-text render ---------------------------------------------------------------------------------------------
def _minds_used(c):
    names = set()

    def walk(t):
        m = t["slots"].get("M")
        if m and m not in ("I", "you"):
            names.add(m)
        for k in ("I", "J"):
            v = t["slots"].get(k)
            if isinstance(v, dict):
                walk(v["that"])
    for t in list(c.get("terms", [])) + list(c.get("sequence", [])):
        walk(t)
    return names


_TURN_PAYLOAD = ("terms", "sequence", "recipe", "stocks", "relations", "fractal", "lacunae", "topic", "reason")


def _bare_turn(c, turn, allowed):
    """A turn form that says nothing but the turn. Content it cannot say is refused, never silently dropped."""
    extra = [k for k in _TURN_PAYLOAD if k not in allowed and c[k]]
    if extra:
        raise ValueError("%s carries no %s in CCE: that content would be lost" % (turn, ", ".join(extra)))


def render(content, rng=None):
    c = canonical(content)
    if c["gate"] == "UNDETERMINED":
        return FIXED_UNDETERMINED                      # fixed; never drawn
    lead = {"CHECKED": "I checked: ", "USER_SAID": "You said: ", "NONE": ""}[c["evidence"]]
    if c["turn"] == "CLARIFY":
        if c["lacunae"]:
            if len(c["lacunae"]) != 1:
                raise ValueError("CCE v0.1 names one slot per CLARIFY")
            return lead + "I need %s for %s. What is it?" % (c["lacunae"][0], c["topic"])
        return lead + "Are we still on %s?" % c["topic"]
    if c["turn"] == "REFUSE_CLAIM":
        return lead + "I cannot support that: %s." % c["reason"]
    if c["turn"] == "REFUSE":
        _bare_turn(c, "REFUSE", {"reason"})
        if not c["reason"]:
            raise ValueError("REFUSE carries the boundary that was not crossed, as reason words")
        return lead + REFUSE_LEAD + "%s." % c["reason"]
    if c["turn"] == "CLOSE":
        _bare_turn(c, "CLOSE", {"topic"})
        return lead + ("That closes %s." % c["topic"] if c["topic"] is not None else BARE_CLOSE)
    if c["turn"] not in ("ANSWER", "ACK"):
        raise ValueError("turn type %s has no CCE v0.1 form" % c["turn"])
    out = []
    if c["topic"] is not None:
        out.append(("New subject: %s." if c["turn"] == "ACK" else "Topic: %s.") % c["topic"])
    elif c["turn"] == "ACK":
        raise ValueError("ACK needs a topic")
    rels = list(c["relations"])
    declared = [r for r in rels if r[0] == "is_a"]
    out += ["%s is a Mind." % r[1] for r in declared]
    if {r[1] for r in declared} != _minds_used(c) | ({r[1] for r in declared}):
        raise ValueError("a named Mind without a declaration")
    if _minds_used(c) - {r[1] for r in declared}:
        raise ValueError("a named Mind without a declaration")
    rec = c["recipe"]
    if rec is not None:
        terms = list(rec["terms"])
        if not terms:
            raise ValueError("a recipe needs at least one term")
        if rng is not None:
            rng.shuffle(terms)
        out.append("To make %s, use %s." % (rec["omega"], "; plus ".join(render_rterm(t, rng) for t in terms)))
        for k in rec["leakage"]:
            out.append("Side product: %s." % k["side"] if k["implicit"]
                       else "Side product: %s of %s." % (_say_num(k["coefficient"], rng), k["side"]))
        out += ["Helped by %s." % x for x in rec["catalysts"]]
        out += ["Slowed by %s." % x for x in rec["inhibitors"]]
    for s in c["stocks"]:
        ref = s["ref"]
        out.append("There is %s of %s." % (_say_num(s["amount"], rng),
                                            ref["outcome"] if "outcome" in ref else render_state(ref, rng)))
    for r in rels:
        if r[0] == "is_a":
            if r[2] != "Mind":
                raise ValueError("only 'is a Mind' declarations in v0.1")
            continue
        if r[0] == "one_of":
            members = list(r[2])
            if rng is not None:
                rng.shuffle(members)
            out.append("%s is one of {%s}." % (r[1], ", ".join(members)))
        elif r[0] == "leads_to":
            out.append("Fact: %s leads to %s." % (r[1], r[2]))
        elif r[0] == "needs_first":
            out.append("%s needs %s first." % (r[1], r[2]))
        elif r[0] == "absent":
            out.append("There is no %s." % r[1])
        else:
            raise ValueError("relation %r has no CCE v0.1 form (declared LACUNA)" % r[0])
    terms = list(c["terms"])
    if rng is not None:
        rng.shuffle(terms)
    out += [render_frame(t, rng, words=True) + "." for t in terms]
    if c["sequence"]:
        if len(c["sequence"]) < 2:
            raise ValueError("a sequence needs two steps")
        out.append("First " + "; then ".join(render_frame(t, rng, words=True) for t in c["sequence"]) + ".")
    if c["fractal"]:
        if not 2 <= len(c["fractal"]) <= 4:
            raise ValueError("fractal length 2..4 in v0.1")
        out.append("The fractal sequence is %s." % " : ".join(NOETIC_NAMES[n] for n in c["fractal"]))
    if not out:
        raise ValueError("empty content")
    return lead + " ".join(out)


# --- Receipts --------------------------------------------------------------------------------------------------------
def round_trip(content, rng=None, seed=None):
    """eta = render (write), epsilon = parse (read). ok only when the content comes back identical."""
    receipt = {"cce_version": CCE_VERSION, "content_hash_in": None, "seed": seed, "sentence": None,
               "content_hash_out": None, "ok": False, "rejection": None}
    try:
        receipt["content_hash_in"] = digest(content)
    except (Refusal, ValueError, KeyError, TypeError) as exc:
        receipt["rejection"] = "CONTENT_INVALID_" + type(exc).__name__
        receipt["receipt_id"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return receipt
    try:
        sentence = render(content, rng)
        receipt["sentence"] = sentence
        back = parse(sentence)
        receipt["content_hash_out"] = digest(back)
        receipt["ok"] = receipt["content_hash_out"] == receipt["content_hash_in"]
    except Refusal as exc:
        receipt["rejection"] = exc.code
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        receipt["rejection"] = "RENDER_" + type(exc).__name__
    receipt["receipt_id"] = hashlib.sha256(json.dumps(receipt, sort_keys=True, ensure_ascii=False)
                                           .encode("utf-8")).hexdigest()[:16]
    return receipt


def say(content, seed, cap=DRAW_CAP):
    """Seeded wording draw. Randomness picks wording only; read-back decides; fixed twin is the fallback."""
    if canonical(content)["gate"] == "UNDETERMINED":
        return {"sentence": FIXED_UNDETERMINED, "drawn": False, "tries": 0, "said_failing": 0}
    rng = random.Random(seed)
    for attempt in range(1, cap + 1):
        r = round_trip(content, rng, seed)
        if r["ok"]:
            return {"sentence": r["sentence"], "drawn": True, "tries": attempt, "receipt": r, "said_failing": 0}
    r = round_trip(content, None, seed)
    if not r["ok"]:
        return {"sentence": None, "drawn": False, "tries": cap, "receipt": r, "said_failing": 0, "unsayable": True}
    return {"sentence": r["sentence"], "drawn": False, "tries": cap, "receipt": r, "said_failing": 0}


# --- Lexicon (for the COIN control and the admission check 5) --------------------------------------------------------
def lexicon_words():
    words = set()
    for _, _, tpl, _ in TEMPLATES:
        for p in _TOKEN.split(tpl):
            if p.startswith("~"):
                words.update(" ".join(VERBS[p[1:]].values()).split())
            elif not p.startswith("{"):
                words.update(re.findall(r"[A-Za-z']+", p))
    words.update(DOMAINS.values())
    words.update(REGISTERS.values())
    words.update(DRIVES.values())
    words.update(n for name in NOETIC_NAMES.values() for n in name.split("/"))
    words.update("of use plus to make needs first then not there is no I checked you said cannot tell combined "
                 "into in registers register for at rate per pattern degree side product helped by slowed a one "
                 "fact leads topic new subject named with".split())
    return sorted(words)
