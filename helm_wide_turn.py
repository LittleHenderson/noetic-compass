"""helm_wide_turn.py -- the reader, the voice and the live-loop turn for RB-W1, the WIDE recipe brain. Behind a switch.

Used ONLY when the WIDE_BRAIN switch is ON (helm_brain_wide.wide_brain_on). With it OFF the live loop never imports
this module, and helm_english_in.py / helm_voice.py / the licensed brain behave exactly as before.

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

CLAIM STATUS: ENGINEERED-NOT-VALIDATED. Not tested on a sealed exam.
"""
from __future__ import annotations

import re
import unicodedata
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

import helm_brain_wide as W

READER_VERSION = "helm_wide_turn reader RB-W1 v1 (2026-10-19)"
CLAIM_STATUS = W.CLAIM_STATUS

# ---------------------------------------------------------------------------------------------------- names
#: size/freshness words dropped from the FRONT of an ingredient name (same list as helm_english_in.ADJECTIVES_SKIPPED)
LEADING_DROPPED = {"fresh", "large", "big", "small", "whole", "plain", "cold", "warm", "soft", "raw", "fine", "coarse",
                   "regular", "extra-large", "medium", "the", "a", "an", "some", "of"}
#: words that make a comma segment a note on the line before it ("2 cups flour, sifted"), not a new ingredient
NOTE_WORDS = set("""sifted chopped melted softened beaten divided diced minced sliced packed grated shredded peeled cored
crushed ground halved quartered cubed drained rinsed toasted optional finely coarsely lightly freshly roughly thinly
well firmly room temperature at cut into pieces to taste or more less if needed as needed for garnish serving and
separated whisked cooled warmed scalded heaping level rounded""".split())
SINGULAR_EXCEPTIONS = {"molasses": "molasses", "hummus": "hummus", "couscous": "couscous", "asparagus": "asparagus",
                       "swiss": "swiss", "loaves": "loaf", "leaves": "leaf", "halves": "half", "knives": "knife",
                       "cheeses": "cheese", "glasses": "glass", "grits": "grits", "oats": "oats", "greens": "greens"}
APPROX_RX = re.compile(r"^(?:about|around|roughly|approximately|approx\.?|nearly|almost|over|under|at least|up to)\b")


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


def parse_line(line: str) -> Dict[str, Any]:
    """One ingredient line -> {"name", "amount" (Fraction), "unit", "said"} or {"clarify": {...}}."""
    s = line.strip().strip(".").strip()
    if APPROX_RX.match(s):
        return {"clarify": _ask("AMOUNT_APPROXIMATE", words=s)}
    try:
        got = W.match_amount(s, 0)
    except W.WideRefused as exc:
        return {"clarify": _ask(exc.code, words=s)}
    if got is None:
        return {"clarify": _ask("NO_AMOUNT", item=bind_name(s), words=s)}
    amount, end = got
    rest = s[end:].strip()
    unit = ""
    m = re.match(r"([A-Za-z]+)\.?(?=\s|$)", rest)
    if m:
        u = W.unit_of(m.group(1))
        if u is not None:
            unit, rest = u, rest[m.end():].strip()
        elif m.group(1).lower() in W.OTHER_UNIT_WORDS:
            return {"clarify": _ask("UNIT_NOT_IN_TABLE", unit=m.group(1).lower(), words=s)}
    rest = re.sub(r"^of\s+", "", rest)
    if re.search(r"\bto taste\b|\bas needed\b", rest) and not unit and amount is None:
        return {"clarify": _ask("NO_AMOUNT", words=s)}
    name = bind_name(rest)
    if not name:
        return {"clarify": _ask("NO_NAME", words=s)}
    return {"name": name, "amount": amount, "unit": unit, "said": s}


def _is_note(segment: str) -> bool:
    words = re.findall(r"[a-z]+", segment.lower())
    return bool(words) and all(w in NOTE_WORDS for w in words)


def parse_lines(text: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """A list of ingredient lines ('a, b and c'). Notes after a comma stay with their line. All or nothing."""
    segments = [x for x in re.split(r",\s*|;\s*|\s+and\s+(?!an?\s+(?:half|third|quarter)\b)|\s+&\s+|\s+plus\s+", text)
                if x and x.strip()]
    lines: List[Dict[str, Any]] = []
    for seg in segments:
        if lines and _is_note(seg):
            continue
        rec = parse_line(seg)
        if "clarify" in rec:
            return [], rec["clarify"]
        lines.append(rec)
    names = [x["name"] for x in lines]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        return [], _ask("SAME_INGREDIENT_TWICE", item=dup[0])
    if not lines:
        return [], _ask("NO_AMOUNT")
    return lines, None


def normalize_text(text: str) -> str:
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", t).strip()


WITNESS_RX = re.compile(r"^(?:so\s+|ok(?:ay)?,?\s+)?(?:we|i)\s+(?:just\s+)?(?:made|baked|cooked|produced|whipped up)\s+"
                        r"(?P<rest>.+?)\s*[.!]?$", re.IGNORECASE)
END_RX = re.compile(r"^(?P<lines>.+?),?\s+and\s+(?:then\s+)?(?:(?:we|i)\s+)?(?:"
                    r"ran out of\s+(?P<out>.+)"
                    r"|(?P<none>nothing ran out|(?:we\s+|i\s+)?(?:did not|didn't) run out of anything|"
                    r"(?:we\s+|i\s+)?ran out of nothing))$", re.IGNORECASE)
STOCK_RX = re.compile(r"^(?:we(?:'ve| have)? got|we (?:still )?have|there (?:is|are)|there's|our pantry has|"
                      r"in the pantry we have)\s+(?P<lines>.+?)(?:\s+(?:on hand|left|in stock))?\s*[.!]?$",
                      re.IGNORECASE)
QUESTION_RX = re.compile(r"^(?:how\s+(?:much|many)\s+(?P<p1>.+?)\s+(?:can|could)\s+(?:we|i)\s+(?:make|bake|cook)"
                         r"(?:\s+now)?(?:\s+with what we have)?|(?:can|could)\s+(?:we|i)\s+(?:make|bake|cook)\s+"
                         r"(?:any\s+|some\s+)?(?P<p2>.+?))\s*\??$", re.IGNORECASE)


def bind_product(phrase: str) -> Optional[str]:
    s = re.sub(r"^(?:batch(?:es)? of|a batch of|loaf of|loaves of)\s+", "", phrase.strip().lower())
    return bind_name(s)


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
        sep = re.search(r"\s+(?:from|using|with)\s+", rest)
        if not sep:
            return clarify(_ask("NO_INGREDIENTS"))
        product = bind_product(rest[:sep.start()])
        tail = rest[sep.end():]
        e = END_RX.match(tail)
        if not e:
            return clarify(_ask("NO_RAN_OUT", product=product))
        lines, c = parse_lines(e.group("lines"))
        if c:
            return clarify(c)
        ran_out: List[str] = []
        if e.group("out"):
            words = re.sub(r"\b(?:at the same time|at once|first|both|the|too)\b", " ", e.group("out").lower())
            for part in re.split(r",\s*|\s+and\s+|\s+&\s+", words):
                n = bind_name(part)
                if n and n not in ran_out:
                    ran_out.append(n)
        if not product:
            return clarify(_ask("NO_PRODUCT"))
        out.update(status="WITNESS", witness={"product": product, "made": made, "ran_out": ran_out,
                                              "stock": {x["name"]: (x["amount"], x["unit"]) for x in lines},
                                              "said": {x["name"]: x["said"] for x in lines}})
        return out
    m = STOCK_RX.match(t)
    if m:
        lines, c = parse_lines(m.group("lines"))
        if c:
            return clarify(c)
        out.update(status="STOCK", stock={x["name"]: (x["amount"], x["unit"]) for x in lines})
        return out
    m = QUESTION_RX.match(t)
    if m:
        phrase = m.group("p1") or m.group("p2")
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


def say_amount_of(q: Fraction, unit: str, name: str) -> str:
    """'1/3 cup of brown sugar', '2 eggs', '1 egg'."""
    if unit:
        return f"{W.say_measure(q, unit)} of {name}"
    return f"{W.say_quantity(q)} {plural(name) if q > 1 else name}"


def say_wide(rec: Dict[str, Any]) -> str:
    """The brain's evaluate record in plain English."""
    p = rec["product"]
    gate = rec.get("gate")
    if rec.get("status") == W.EVALUATED:
        return (f"With what's on hand we can make {rec['yield_said']} {p}. "
                f"{cap(rec['limiting_reagent'])} runs out first, so it sets the limit.")
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


def say_learned(record: Dict[str, Any], brain: W.WideRecipeBook) -> str:
    p, n = record["product"], record["ingredient"]
    unit = brain.recipes[p]["taught_unit"][n]
    q = W.from_base(brain.coefficient(p, n), unit)
    msg = f"Got it: one {p} needs {say_amount_of(q, unit, n)}."
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
        return "What was being made?"
    if code == "NO_INGREDIENTS":
        return "What went into that batch, and how much of each?"
    return "Could you say that another way? Nothing was saved."


NOT_MINE_LINE = ("I'm not sure what to do with that. I can learn from a batch you made, note what's on hand, or tell "
                 "you how much of something we can make. Nothing was saved.")


# ---------------------------------------------------------------------------------------------------- the turn
def _cce_amount(cce: Any, q: Fraction) -> str:
    return cce.num(W.frac_text(q))


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


def _stock_of(loop: Any) -> Dict[str, Tuple[Fraction, str]]:
    if not hasattr(loop, "wide_stock"):
        loop.wide_stock = {}
    return loop.wide_stock


def _wide_stock(loop: Any, stock: Dict[str, Tuple[Fraction, str]], tick: int, result: Dict[str, Any],
                writes_before: int) -> Dict[str, Any]:
    import helm_end_to_end_loop as E
    form = E.cce.empty_content()
    form["stocks"] = [{"amount": _cce_amount(E.cce, q), "ref": {"outcome": omega(n)}} for n, (q, _u) in stock.items()]
    rt = loop.verify_cce_round_trip(form)
    result["cce_round_trip"] = {k: v for k, v in rt.items() if k != "content"}
    loop._emit(tick, "CCE skin", **result["cce_round_trip"])
    if not rt["verified"]:
        return loop._finish(result, tick, "CLARIFY_ROUND_TRIP_FAILED", E.HELMVoiceAdapter.format_round_trip_failed(),
                            writes_before, "WAIT_FOR_USER")
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
    brain = loop.brain
    held = _stock_of(loop)
    product = brain.product_of(topic)
    loop._emit(tick, "S0 atlas head", topic=topic, product=product, brain=brain.provenance())
    if product is None:
        rec = brain.evaluate(topic, {})
        result["recipe_receipt"] = rec
        return loop._finish(result, tick, "UNDETERMINED_UNKNOWN_PRODUCT", say_wide(rec), writes_before,
                            "WAIT_FOR_USER: a witnessed batch")
    loop.last_topic = product
    support = brain.support_of(product)
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
                 f"{'; '.join(say_amount_of(q, u, n) for n, (q, u) in stock.items())}; limiting reagent {lim}; "
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
    brain = loop.brain
    if result is None:
        result = loop._new_result(f"[witnessed batch] {product}", tick)
    if writes_before is None:
        writes_before = loop._store_writes()
    p = W.norm_name(product)
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
    form["stocks"] = ([{"amount": _cce_amount(E.cce, q), "ref": {"outcome": omega(n)}} for n, (q, _u) in stock.items()]
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
