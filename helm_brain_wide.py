"""helm_brain_wide.py -- RB-W1, the WIDE recipe brain (owner order "WIDEN THE BRAIN", 2026-10-19). Behind a switch.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
The licensed recipe brain (helm_brain_canonical.py -> rb2.brain_b.RecipeBookBrain, HELM-R1 wave 1) knows 8 ingredient
words, 4 fixed recipe shapes of 2 or 3 ingredients, and only numbers that are exactly one binary64 (no thirds). The
recipe-shape survey (Documents/Codex/2026-10-19/recipe_shape_survey_v1/SURVEY.md) found that this holds 1 of 13,686
real recipes. This module is a SEPARATE, wider brain built beside it. It uses the same rule to learn:

    one witnessed batch, one ingredient ran out first  ->  a[recipe][ingredient] := stock_of_it / amount_made (exact)

and the same answer rule (CAS v7.6 recipe semantics): Theta(Omega) = sum a_i * X_i -> Omega, yield = min_i x_i / a_i,
the ingredient with the smallest ratio is the Limiting Reagent. What is wider:

  Stage 1  exact rational amounts end to end (Fraction: thirds, sixths, mixed numbers; never a float) and a unit table:
           the survey's top 20 units, converted exactly through 9 named factors (US customary + metric definitions).
           Units with no exact standard (can, clove, pinch, ...) stay their own count unit and are never converted.
           A volume is never turned into a weight (that would need a density, a number nobody witnessed).
  Stage 2  open ingredient vocabulary (any name the reader binds; names, not a fixed list), recipes of up to 10
           ingredients, any product name.

WHAT GROWS, AND ONLY WHEN
-------------------------
- A recipe (product name + which ingredients it uses) is added ONLY when an ADMITTED witnessed batch introduces it.
  The ingredients the batch was made from ARE the recipe's support (structure, not a learned number).
- A coefficient a[recipe][ingredient] is written ONLY from a batch where that ingredient was the single ingredient that
  ran out first, and only if the brain's own checks pass:
    receipt (eta/epsilon read-back): over the recipe's coefficients learned so far plus the new one, the batch's
      stock reads back exactly the amount made, with the named ingredient as the ONLY one at the minimum;
    memory check (STRICT, OUR_CONVENTION, labeled): every earlier admitted batch of that recipe still reads back the
      same way. The licensed writer allows one added not-right answer (rb.writer.ALLOWANCE = 1); this brain allows 0.
- Everything not witnessed stays UNDETERMINED, and the brain asks for the batch it needs. UNDETERMINED is not wrong.

Refused batches (nothing is written, no recipe is added): nothing ran out; two or more ran out at once; zero made;
the ran-out ingredient is not in the batch; more than 10 ingredients; a unit not in the table; a unit of another kind
than the recipe's (volume vs weight vs count); a batch whose ingredients differ from the recipe's; a new amount that
contradicts a learned one (REFUSED_CONFLICT); a failed receipt; a failed memory check.

PARAMETERS (Capacity Rules v0.1: every parameter has a job). `parameter_table()` lists them; a test prints it.
  learned:     a[recipe][ingredient], one per (recipe, ingredient on that recipe's support); job = how much of that
               ingredient (in its kind's base unit) one unit of the product needs. Exact Fraction or ABSENT.
  programmed:  9 unit factors (exact definitions, never learned), each used by at least one unit conversion.
  structure:   product names, ingredient names, each recipe's support and each cell's unit kind (all from witnessed
               batches), MAX_INGREDIENTS = 10 (the owner's design limit). Not numbers the brain learns.
Nothing else is learned. The witness log is a record of what the user said; the answer path never reads it.

SWITCH: WIDE_BRAIN, default ON since the owner's ruling of 2026-10-20 ("YES TO WIDE BRAIN: Wide brain becomes HELM's
canonical brain", SPEC 7.56). `wide_brain_on()` reads an explicit argument, else the environment variable
HELM_WIDE_BRAIN: "0" / "OFF" / "FALSE" / "NO" turn it off; anything else, or no variable at all, leaves it on. With it
OFF the live loop never imports this module and the licensed reference brain is the only brain
(helm_end_to_end_loop.HELMEndToEndLoop). Before 2026-10-20 the default was OFF; every sealed test package pins its own
copy of HELM, so none is changed by this default.

CLAIM STATUS: VALIDATED for two sentences only (SPEC 7.89: 128 real recipes, no other parts, job c47; SPEC 7.96: with every
other part on, job c50), ceiling NAMED_CORPORA_ONLY for real recipes + SYNTHETIC_ONLY for the rest. HELM's canonical brain
since the owner's ruling of 2026-10-20 (SPEC 7.56); a ruling is not a result and did not change the claim. NOT licensed:
"better than the licensed brain" outside those sentences; real kitchens or cooks; typed English in general. The licensed
wave-1 brain keeps its own LICENSED claim as the reference brain and still reads every live-loop turn first.
Standard library only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from decimal import Decimal
from fractions import Fraction
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

CLAIM_STATUS = "VALIDATED"                 # for the SPEC 7.89 / 7.96 sentences only; see the header
CLAIM_CEILING = "NAMED_CORPORA_ONLY (real recipes) + SYNTHETIC_ONLY (drive loop, English-64 / Faces-64, conversation)"
CANONICAL_SINCE = "2026-10-20 (owner ruling \"YES TO WIDE BRAIN\", SPEC 7.56)"
BRAIN_VERSION = "helm_brain_wide RB-W1 v1 (2026-10-19)"
WIDE_BRAIN_ENV = "HELM_WIDE_BRAIN"
WIDE_BRAIN_OFF_WORDS = ("0", "OFF", "FALSE", "NO")   # the only values that switch the canonical brain off
MAX_INGREDIENTS = 10                     # owner order: "up to 10 ingredients per recipe"
EVALUATED = "EVALUATED"
UNDETERMINED = "UNDETERMINED"
ADMITTED = "ADMITTED"
#: every attribute a WideRecipeBook instance holds (the parameter-accounting test checks this set)
BRAIN_ATTRIBUTES = {"recipes", "witness_log", "_seed", "memory"}


class WideRefused(ValueError):
    """A refusal with a stable code (an amount, a unit or a conversion the wide brain will not accept)."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def wide_brain_on(value: Optional[bool] = None) -> bool:
    """The WIDE_BRAIN switch. Default ON since the owner's ruling of 2026-10-20 (SPEC 7.56): an explicit argument wins;
    else the environment variable HELM_WIDE_BRAIN set to 0 / OFF / FALSE / NO switches it off; anything else is on."""
    if value is not None:
        return bool(value)
    return os.environ.get(WIDE_BRAIN_ENV, "").strip().upper() not in WIDE_BRAIN_OFF_WORDS


# =====================================================================================================================
# Stage 1a: exact quantities
# =====================================================================================================================
VULGAR = {"½": Fraction(1, 2), "⅓": Fraction(1, 3), "⅔": Fraction(2, 3), "¼": Fraction(1, 4), "¾": Fraction(3, 4),
          "⅕": Fraction(1, 5), "⅖": Fraction(2, 5), "⅗": Fraction(3, 5), "⅘": Fraction(4, 5), "⅙": Fraction(1, 6),
          "⅚": Fraction(5, 6), "⅛": Fraction(1, 8), "⅜": Fraction(3, 8), "⅝": Fraction(5, 8), "⅞": Fraction(7, 8)}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
                "ten": 10, "eleven": 11, "twelve": 12}
PART_WORDS = {"half": 2, "halves": 2, "third": 3, "thirds": 3, "quarter": 4, "quarters": 4, "fourth": 4,
              "fourths": 4, "eighth": 8, "eighths": 8}
_V = "".join(VULGAR)
_INT = r"\d+"
_DEC = r"\d+\.\d+|\.\d+"
_FRAC = r"\d+/\d+"
_WORD = "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
_PART = "|".join(sorted(PART_WORDS, key=len, reverse=True))
#: one amount, as it can start an ingredient line (longest forms first). Exactly one alternative matches.
AMOUNT_RX = re.compile(
    r"(?P<amt>"
    r"\d+\s+and\s+an?\s+(?:half|third|quarter)"       # 1 and a half (v3: was read as 1)
    r"|\d+\s*-\s*\d+/\d+"                             # 1-1/2  (mixed, hyphen)
    r"|\d+\s+\d+/\d+"                                 # 1 1/2  (mixed)
    r"|\d+\s*[" + _V + r"]"                           # 1½ / 1 ½
    r"|" + _FRAC + r"|" + _DEC + r"|" + _INT +
    r"|[" + _V + r"]"
    r"|(?:" + _WORD + r"|an?)\s+and\s+an?\s+(?:half|third|quarter)"     # one and a half
    r"|(?:" + _WORD + r"|an?)\s+(?:" + _PART + r")"                      # two thirds / a third
    r"|" + _WORD + r"|half|an?"
    r")(?![\w/" + _V + r"])", re.IGNORECASE)
#: a range right after an amount ("2 or 3", "2-3", "1 to 1 1/2", "2–3")
RANGE_TAIL_RX = re.compile(r"\s*(?:-|–|—|\bto\b|\bor\b)\s*(?:\d|[" + _V + r"]|(?:" + _WORD + r")\b)", re.IGNORECASE)


def _word_amount(s: str) -> Fraction:
    w = s.lower()
    if w in ("a", "an"):
        return Fraction(1)
    if w == "half":
        return Fraction(1, 2)
    if w.isdigit():                              # v3: "1 and a half"
        return Fraction(int(w))
    return Fraction(NUMBER_WORDS[w])


def _amount_value(text: str) -> Fraction:
    """The exact value of one AMOUNT_RX match."""
    t = re.sub(r"\s+", " ", text.strip().lower())
    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)/(\d+)", t) or re.fullmatch(r"(\d+) (\d+)/(\d+)", t)
    if m:
        return Fraction(int(m.group(1))) + Fraction(int(m.group(2)), int(m.group(3)))
    m = re.fullmatch(r"(\d+) ?([" + _V + r"])", t)
    if m:
        return Fraction(int(m.group(1))) + VULGAR[m.group(2)]
    if t in VULGAR:
        return VULGAR[t]
    if re.fullmatch(_FRAC, t):
        a, b = t.split("/")
        return Fraction(int(a), int(b))
    if re.fullmatch(_DEC + "|" + _INT, t):
        return Fraction(t)                       # Fraction("0.25") is exact; no float is ever made
    m = re.fullmatch(r"(\w+) and an? (half|third|quarter)", t)
    if m:
        return _word_amount(m.group(1)) + Fraction(1, PART_WORDS[m.group(2)])
    m = re.fullmatch(r"(\w+) (\w+)", t)
    if m and m.group(2) in PART_WORDS:
        return _word_amount(m.group(1)) * Fraction(1, PART_WORDS[m.group(2)])
    return _word_amount(t)


def match_amount(text: str, pos: int = 0) -> Optional[Tuple[Fraction, int]]:
    """An amount starting exactly at `pos`: (value, end) or None. Raises AMOUNT_IS_A_RANGE for '2 or 3' and kin."""
    m = AMOUNT_RX.match(text, pos)
    if not m:
        return None
    try:
        value = _amount_value(m.group("amt"))
    except (ZeroDivisionError, KeyError, ValueError) as exc:
        raise WideRefused("AMOUNT_NOT_A_NUMBER", m.group("amt")) from exc
    if RANGE_TAIL_RX.match(text, m.end()) and m.group("amt").lower() not in ("a", "an"):
        raise WideRefused("AMOUNT_IS_A_RANGE", text[pos:].strip()[:40])
    return value, m.end()


def parse_quantity(value: Any) -> Fraction:
    """Any accepted amount -> an exact Fraction. Floats (and bools) are refused: no silent rounding."""
    if isinstance(value, bool) or isinstance(value, float):
        raise WideRefused("AMOUNT_NOT_EXACT", f"{value!r}: pass text, int, Decimal or Fraction")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, (int, Decimal)):
        return Fraction(value)
    text = str(value).strip()
    if not text:
        raise WideRefused("AMOUNT_NOT_A_NUMBER", "empty")
    got = match_amount(text, 0)
    if got is None or text[got[1]:].strip():
        raise WideRefused("AMOUNT_NOT_A_NUMBER", text)
    return got[0]


def say_quantity(q: Fraction) -> str:
    """Exact words for an amount: 3, 2/3, 1 1/3. parse_quantity(say_quantity(q)) == q for every q > 0."""
    q = Fraction(q)
    if q < 0:
        raise WideRefused("AMOUNT_NEGATIVE", str(q))
    if q.denominator == 1:
        return str(q.numerator)
    whole, rest = divmod(q.numerator, q.denominator)
    part = f"{rest}/{q.denominator}"
    return f"{whole} {part}" if whole else part


def frac_text(v: Optional[Fraction]) -> Optional[str]:
    if v is None:
        return None
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


# =====================================================================================================================
# Stage 1b: the unit table (survey top 20; exact definitions; OUR_CONVENTION = US customary for cup/pint/quart/gill)
# =====================================================================================================================
#: 9 named factors. Programmed exact definitions, never learned. Each one has a job (it converts at least one unit).
NAMED_FACTORS: Dict[str, Dict[str, Any]] = {
    "TSP_PER_TBSP": {"value": Fraction(3), "job": "1 tablespoon = 3 teaspoons (US)"},
    "TBSP_PER_CUP": {"value": Fraction(16), "job": "1 cup = 16 tablespoons (US)"},
    "CUP_PER_PINT": {"value": Fraction(2), "job": "1 pint = 2 cups (US)"},
    "PINT_PER_QUART": {"value": Fraction(2), "job": "1 quart = 2 pints (US)"},
    "GILL_PER_PINT": {"value": Fraction(4), "job": "1 pint = 4 gills (US)"},
    "ML_PER_TSP": {"value": Fraction("4.92892159375"), "job": "1 US teaspoon = 4.92892159375 mL (exact by definition)"},
    "G_PER_OZ": {"value": Fraction("28.349523125"), "job": "1 avoirdupois ounce = 28.349523125 g (exact by definition)"},
    "OZ_PER_LB": {"value": Fraction(16), "job": "1 pound = 16 ounces"},
    "G_PER_KG": {"value": Fraction(1000), "job": "1 kilogram = 1000 grams"},
}
VOLUME, MASS, COUNT = "volume", "mass", "count"


def _f(*names: str) -> Fraction:
    out = Fraction(1)
    for n in names:
        out *= NAMED_FACTORS[n]["value"]
    return out


#: unit -> kind, size in the kind's base unit (volume: teaspoon; mass: gram; own count units: 1 of itself), the named
#: factors that size is built from, and whether an exact standard exists. Built ONLY from NAMED_FACTORS.
UNITS: Dict[str, Dict[str, Any]] = {
    "teaspoon": {"kind": VOLUME, "base": Fraction(1), "factors": [], "exact_standard": True},
    "tablespoon": {"kind": VOLUME, "base": _f("TSP_PER_TBSP"), "factors": ["TSP_PER_TBSP"], "exact_standard": True},
    "cup": {"kind": VOLUME, "base": _f("TSP_PER_TBSP", "TBSP_PER_CUP"), "factors": ["TSP_PER_TBSP", "TBSP_PER_CUP"],
            "exact_standard": True},
    "pint": {"kind": VOLUME, "base": _f("TSP_PER_TBSP", "TBSP_PER_CUP", "CUP_PER_PINT"),
             "factors": ["TSP_PER_TBSP", "TBSP_PER_CUP", "CUP_PER_PINT"], "exact_standard": True},
    "quart": {"kind": VOLUME, "base": _f("TSP_PER_TBSP", "TBSP_PER_CUP", "CUP_PER_PINT", "PINT_PER_QUART"),
              "factors": ["TSP_PER_TBSP", "TBSP_PER_CUP", "CUP_PER_PINT", "PINT_PER_QUART"], "exact_standard": True},
    "gill": {"kind": VOLUME, "base": _f("TSP_PER_TBSP", "TBSP_PER_CUP", "CUP_PER_PINT") / _f("GILL_PER_PINT"),
             "factors": ["TSP_PER_TBSP", "TBSP_PER_CUP", "CUP_PER_PINT", "GILL_PER_PINT"], "exact_standard": True},
    "milliliter": {"kind": VOLUME, "base": 1 / _f("ML_PER_TSP"), "factors": ["ML_PER_TSP"], "exact_standard": True},
    "gram": {"kind": MASS, "base": Fraction(1), "factors": [], "exact_standard": True},
    "ounce": {"kind": MASS, "base": _f("G_PER_OZ"), "factors": ["G_PER_OZ"], "exact_standard": True},
    "pound": {"kind": MASS, "base": _f("G_PER_OZ", "OZ_PER_LB"), "factors": ["G_PER_OZ", "OZ_PER_LB"],
              "exact_standard": True},
    "kilogram": {"kind": MASS, "base": _f("G_PER_KG"), "factors": ["G_PER_KG"], "exact_standard": True},
}
for _own in ("can", "clove", "slice", "pinch", "package", "bunch", "square", "saltspoon", "teacup"):
    # no exact standard size: the unit is its own kind, never converted to anything else
    UNITS[_own] = {"kind": "own:" + _own, "base": Fraction(1), "factors": [], "exact_standard": False}
BASE_UNIT = {VOLUME: "teaspoon", MASS: "gram"}

#: spellings the reader accepts for each table unit (OUR_CONVENTION; "t."/"T." are NOT read: their case is ambiguous)
UNIT_WORDS: Dict[str, str] = {}
for _u, _forms in {
        "teaspoon": "teaspoon teaspoons teaspoonful teaspoonfuls tsp tsps",
        "tablespoon": "tablespoon tablespoons tablespoonful tablespoonfuls tbsp tbsps tbs tbl",
        "cup": "cup cups cupful cupfuls", "pint": "pint pints pt pts", "quart": "quart quarts qt qts",
        "gill": "gill gills", "milliliter": "milliliter milliliters millilitre millilitres ml mls",
        "gram": "gram grams gramme grammes g gr", "ounce": "ounce ounces oz ozs",
        "pound": "pound pounds lb lbs", "kilogram": "kilogram kilograms kilo kilos kg kgs",
        "can": "can cans tin tins", "clove": "clove cloves", "slice": "slice slices", "pinch": "pinch pinches",
        "package": "package packages pkg pkgs packet packets",   # v3: a packet is a package "bunch": "bunch bunches", "square": "square squares",
        "saltspoon": "saltspoon saltspoons saltspoonful saltspoonfuls", "teacup": "teacup teacups teacupful teacupfuls",
}.items():
    for _w in _forms.split():
        UNIT_WORDS[_w] = _u
#: unit words the reader knows are units but the table does not hold (the survey's other units): it asks, never guesses
OTHER_UNIT_WORDS = set("""stick sticks dozen dozens liter liters litre litres l gallon gallons gal bag bags box boxes jar
jars carton cartons dash dashes pack packs head heads sprig sprigs piece pieces stalk stalks handful
handfuls drop drops cake cakes glass glasses wineglass wineglasses wineglassful peck pecks bushel bushels dessertspoon
dessertspoons dessertspoonful breakfastcup breakfastcups coffeecup coffeecups dram drams cube cubes strip strips inch
inches sheet sheets scoop scoops bottle bottles ear ears rasher rashers fillet fillets knob knobs tumbler tumblers
spoonful spoonfuls deciliter deciliters centiliter centiliters fluid fl quarter-pound""".split())
UNIT_PLURAL = {"pinch": "pinches", "bunch": "bunches"}


def unit_of(word: str) -> Optional[str]:
    """A table unit for one written word ('Cups', 'tbsp.', 'lbs') or None. '' (no unit) is a plain count."""
    return UNIT_WORDS.get(word.lower().rstrip("."))


def unit_kind(unit: str) -> str:
    if not unit:
        return COUNT
    if unit not in UNITS:
        raise WideRefused("UNIT_NOT_IN_TABLE", unit)
    return UNITS[unit]["kind"]


def to_base(amount: Any, unit: str) -> Tuple[str, Fraction]:
    """(kind, exact amount in the kind's base unit)."""
    q = parse_quantity(amount)
    if not unit:
        return COUNT, q
    kind = unit_kind(unit)
    return kind, q * UNITS[unit]["base"]


def from_base(base_amount: Fraction, unit: str) -> Fraction:
    return Fraction(base_amount) / (UNITS[unit]["base"] if unit else 1)


def convert(amount: Any, unit_from: str, unit_to: str) -> Fraction:
    """Exact conversion inside one kind. Across kinds (cup -> gram, can -> cup) is refused: UNIT_KIND_MISMATCH."""
    kind_a, base = to_base(amount, unit_from)
    kind_b = unit_kind(unit_to)
    if kind_a != kind_b:
        raise WideRefused("UNIT_KIND_MISMATCH", f"{unit_from or 'plain count'} -> {unit_to or 'plain count'}")
    return from_base(base, unit_to)


def say_unit(unit: str, q: Fraction) -> str:
    if not unit:
        return ""
    return unit if Fraction(q) <= 1 else UNIT_PLURAL.get(unit, unit + "s")


def say_measure(q: Fraction, unit: str) -> str:
    """'1/3 cup', '1 1/2 cups', '2' (a plain count)."""
    words = say_quantity(q)
    u = say_unit(unit, q)
    return f"{words} {u}" if u else words


# =====================================================================================================================
# Stage 2: the open recipe book
# =====================================================================================================================
def norm_name(name: str) -> str:
    """The brain's name for an ingredient or product: lower case, single spaces. (The reader does the rest.)"""
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _stock_entry(v: Any) -> Tuple[Fraction, str]:
    """A stock value: (amount, unit) or a bare amount (a plain count)."""
    if isinstance(v, (tuple, list)) and len(v) == 2:
        unit = v[1] or ""
        if unit and unit not in UNITS:
            raise WideRefused("UNIT_NOT_IN_TABLE", unit)
        return parse_quantity(v[0]), unit
    return parse_quantity(v), ""


class WideRecipeBook:
    """The wide recipe book. Learned: one exact coefficient per (recipe, ingredient on its support). Nothing else."""

    kind = "wide_recipe_book_rb_w1"

    def __init__(self) -> None:
        #: product -> {"support": [names in first-batch order], "kinds": {name: kind}, "taught_unit": {name: unit},
        #:             "a": {name: Fraction | None}, "introduced_by": seed, "lessons": [admitted batch rows]}
        self.recipes: Dict[str, Dict[str, Any]] = {}
        self.witness_log: List[Dict[str, Any]] = []      # record of what the user said (never read when answering)
        self._seed = 0
        self.memory: Dict[str, Any] = {"stock_base": None}  # M: an exact copy of the last stock read (eta write)

    # ------------------------------------------------------------------ names (the loop's adapter surface)
    @property
    def brain(self) -> "WideRecipeBook":
        """The live loop reads `loop.brain.brain.learned_digest()` (the licensed adapter wraps its brain); the wide
        book is its own brain."""
        return self

    @property
    def products(self) -> Dict[str, int]:
        return {p: i for i, p in enumerate(self.recipes)}

    @property
    def ingredients(self) -> List[str]:
        out: List[str] = []
        for r in self.recipes.values():
            for n in r["support"]:
                if n not in out:
                    out.append(n)
        return out

    def product_of(self, name: str) -> Optional[str]:
        n = norm_name(name[2:] if name.startswith("Ω_") else name)
        return n if n in self.recipes else None

    def ingredient_of(self, name: str) -> Optional[str]:
        n = norm_name(name[2:] if name.startswith("Ω_") else name)
        return n if n in self.ingredients else None

    def support_of(self, product: str) -> List[str]:
        return list(self.recipes[norm_name(product)]["support"])

    def unlearned(self, product: str) -> List[str]:
        r = self.recipes[norm_name(product)]
        return [n for n in r["support"] if r["a"][n] is None]

    def coefficient(self, product: str, ingredient: str) -> Optional[Fraction]:
        return self.recipes[norm_name(product)]["a"][norm_name(ingredient)]

    def requirements(self, product: str) -> Dict[str, Optional[str]]:
        r = self.recipes[norm_name(product)]
        return {n: frac_text(r["a"][n]) for n in r["support"]}

    def requirement_said(self, product: str, ingredient: str) -> Optional[str]:
        """The learned requirement in the unit it was taught in, exact ('1/3 cup', '2 1/4 cups', '2')."""
        r = self.recipes[norm_name(product)]
        n = norm_name(ingredient)
        a = r["a"][n]
        if a is None:
            return None
        unit = r["taught_unit"][n]
        return say_measure(from_base(a, unit), unit)

    def filled(self) -> int:
        return sum(1 for r in self.recipes.values() for v in r["a"].values() if v is not None)

    # ------------------------------------------------------------------ state
    def learned_state(self) -> Dict[str, Any]:
        """Everything the brain has learned or been given as structure. Coefficients are the only numbers."""
        return {"kind": self.kind,
                "recipes": {p: {"support": list(r["support"]), "kinds": dict(r["kinds"]),
                                "taught_unit": dict(r["taught_unit"]),
                                "a": {n: frac_text(r["a"][n]) for n in r["support"]}}
                            for p, r in self.recipes.items()}}

    def learned_digest(self) -> str:
        return hashlib.sha256(_canon(self.learned_state())).hexdigest()

    def provenance(self) -> Dict[str, Any]:
        return {"brain": "RB-W1 wide recipe book (helm_brain_wide.WideRecipeBook)", "version": BRAIN_VERSION,
                "claim_status": CLAIM_STATUS, "licensed": False,
                "note": "built beside the licensed brain; the licensed brain is unchanged and canonical",
                "learned_digest": self.learned_digest(), "recipes": len(self.recipes), "filled": self.filled()}

    # ------------------------------------------------------------------ reading
    @staticmethod
    def _read(recipe: Dict[str, Any], stock_base: Dict[str, Fraction], only_learned: bool
              ) -> Tuple[Optional[Fraction], List[str]]:
        """min_i x_i / a_i over the recipe's coefficients (all, or only the learned ones), and who sits at the min."""
        ratios = {n: stock_base[n] / recipe["a"][n] for n in recipe["support"]
                  if recipe["a"][n] is not None or not only_learned}
        if not ratios:
            return None, []
        y = min(ratios.values())
        return y, [n for n in recipe["support"] if n in ratios and ratios[n] == y]

    def evaluate(self, product: str, stock: Dict[str, Any]) -> Dict[str, Any]:
        """How much `product` the stock can make, and which ingredient runs out first. Behind the gate:
        UNKNOWN_PRODUCT (never witnessed), G1 (stock absent or a coefficient unlearned), UNIT_KIND_MISMATCH,
        G2 (yield 0). Every gate -> UNDETERMINED, which is not wrong. v3: two or more ingredients tied at the
        minimum -> EVALUATED with the amount, `tied` naming them and no single limiting reagent (was gate G3)."""
        p = norm_name(product)
        rec: Dict[str, Any] = {"product": p, "status": UNDETERMINED, "gate": None, "yield": None,
                               "limiting_reagent": None, "absent": [], "unlearned": [], "mismatch": [],
                               "tied": [], "learned_digest": self.learned_digest(), "brain": self.kind}
        if p not in self.recipes:
            rec["gate"] = "UNKNOWN_PRODUCT"
            return rec
        r = self.recipes[p]
        given = {norm_name(k): _stock_entry(v) for k, v in stock.items()}
        rec["count_items"] = [n for n in r["support"] if r["kinds"][n] == COUNT]
        rec["absent"] = [n for n in r["support"] if n not in given]
        rec["unlearned"] = [n for n in r["support"] if r["a"][n] is None]
        if rec["absent"] or rec["unlearned"]:
            rec["gate"] = "G1"
            return rec
        base: Dict[str, Fraction] = {}
        for n in r["support"]:
            q, unit = given[n]
            kind = unit_kind(unit)
            if kind != r["kinds"][n]:
                rec["mismatch"].append({"ingredient": n, "said_unit": unit or "plain count",
                                        "recipe_unit": r["taught_unit"][n] or "plain count"})
                continue
            base[n] = to_base(q, unit)[1]
        if rec["mismatch"]:
            rec["gate"] = "UNIT_KIND_MISMATCH"
            return rec
        y, winners = self._read(r, base, only_learned=False)
        # eta/epsilon: write the stock into M, read it back from M, the two answers must agree
        self.memory["stock_base"] = {n: frac_text(v) for n, v in base.items()}
        back = {n: Fraction(v) for n, v in self.memory["stock_base"].items()}
        y2, winners2 = self._read(r, back, only_learned=False)
        rec["eta_eps_read_back"] = {"via": "memory write -> read", "pass": (y, winners) == (y2, winners2)}
        rec["yield"] = frac_text(y)
        if y == 0:
            rec["gate"] = "G2"
            rec["zero"] = [n for n in r["support"] if base[n] == 0]
            return rec
        if len(winners) > 1:
            # v3 (2026-10-20): a tie at the minimum leaves the AMOUNT fully determined (every tied ingredient gives
            # the same y); only "which one runs out first" has no single answer. v2 refused the whole answer (G3).
            # Now the amount is answered and the tied ingredients are named; no single limiting reagent is claimed.
            rec["tied"] = winners
            rec["yield_said"] = say_quantity(y)
            rec["status"] = EVALUATED if rec["eta_eps_read_back"]["pass"] else UNDETERMINED
            return rec
        rec["limiting_reagent"] = winners[0]
        rec["yield_said"] = say_quantity(y)
        rec["status"] = EVALUATED if rec["eta_eps_read_back"]["pass"] else UNDETERMINED
        return rec

    # ------------------------------------------------------------------ teaching
    def witness(self, product: str, stock_before: Dict[str, Any], made: Any, ran_out: Any) -> Dict[str, Any]:
        """One witnessed batch: what went in (stock before), how much came out, which ingredient(s) ran out first.
        `ran_out` is a name or a list of names. Admitted only if every check passes; otherwise nothing changes."""
        self._seed += 1
        seed = self._seed
        names_out = [ran_out] if isinstance(ran_out, str) else list(ran_out or [])
        row = {"seed": seed, "product": norm_name(product), "made": None, "ran_out": [norm_name(n) for n in names_out],
               "stock_before": {}}
        try:
            stock = {norm_name(k): _stock_entry(v) for k, v in stock_before.items()}
            row["stock_before"] = {k: [frac_text(q), u] for k, (q, u) in stock.items()}
            made_q = parse_quantity(made)
            row["made"] = frac_text(made_q)
            new_book, record = self._propose(row["product"], stock, made_q, row["ran_out"], seed)
        except WideRefused as exc:
            code = {"UNIT_NOT_IN_TABLE": "REFUSED_UNIT_NOT_IN_TABLE"}.get(exc.code, "REFUSED_" + exc.code)
            new_book, record = None, {"reason": code, "detail": {"refusal": exc.detail}}
        record.update({"seed": seed, "product": row["product"], "ran_out": row["ran_out"], "made": row["made"]})
        record["admitted"] = new_book is not None
        if new_book is not None:
            self.recipes = new_book
            record["reason"] = ADMITTED
        row.update(admitted=record["admitted"], reason=record["reason"])
        self.witness_log.append(row)
        record["learned_digest_after"] = self.learned_digest()
        return record

    def _propose(self, p: str, stock: Dict[str, Tuple[Fraction, str]], made: Fraction, ran_out: List[str],
                 seed: int) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        def refuse(reason: str, **detail: Any):
            return None, {"reason": reason, "detail": detail}

        if not p:
            return refuse("REFUSED_NO_PRODUCT_NAME")
        if made <= 0:
            return refuse("REFUSED_ZERO_YIELD")
        if not ran_out:
            return refuse("REFUSED_NOTHING_RAN_OUT")
        if len(set(ran_out)) > 1:
            return refuse("REFUSED_TWO_RAN_OUT", ran_out=sorted(set(ran_out)))
        cell = ran_out[0]
        if not stock:
            return refuse("REFUSED_EMPTY_BATCH")
        if len(stock) > MAX_INGREDIENTS:
            return refuse("REFUSED_TOO_MANY_INGREDIENTS", count=len(stock), limit=MAX_INGREDIENTS)
        if cell not in stock:
            return refuse("REFUSED_RAN_OUT_NOT_IN_BATCH", ran_out=cell, batch=sorted(stock))
        if any(q < 0 for q, _ in stock.values()):
            return refuse("REFUSED_NEGATIVE_AMOUNT")
        book = copy.deepcopy(self.recipes)
        is_new = p not in book
        if is_new:
            book[p] = {"support": list(stock), "kinds": {n: unit_kind(u) for n, (_, u) in stock.items()},
                       "taught_unit": {}, "a": {n: None for n in stock}, "introduced_by": seed, "lessons": []}
        r = book[p]
        missing = [n for n in r["support"] if n not in stock]
        extra = [n for n in stock if n not in r["support"]]
        if missing or extra:
            return refuse("REFUSED_SUPPORT_MISMATCH", missing=missing, extra=extra)
        wrong_kind = [n for n, (_, u) in stock.items() if unit_kind(u) != r["kinds"][n]]
        if wrong_kind:
            return refuse("REFUSED_UNIT_KIND_MISMATCH", ingredients=wrong_kind)
        base = {n: to_base(q, u)[1] for n, (q, u) in stock.items()}
        value = base[cell] / made                                   # witnessed_lr_ratio_v1, exact
        old = r["a"][cell]
        if old is not None and old != value:
            return refuse("REFUSED_CONFLICT", ingredient=cell, old=frac_text(old), new=frac_text(value))
        if value == 0:
            return refuse("REFUSED_ZERO_REQUIREMENT", ingredient=cell)
        r["a"][cell] = value
        if cell not in r["taught_unit"]:
            r["taught_unit"][cell] = stock[cell][1]
        # receipt: over the learned coefficients, this batch reads back `made` with `cell` alone at the minimum
        back, winners = self._read(r, base, only_learned=True)
        receipt = {"yield_fed_back": frac_text(made), "yield_read_back": frac_text(back), "limiting_read_back": winners,
                   "checked": "at_admission_on_this_batch", "invented_cells": [],
                   "pass": back == made and winners == [cell]}
        if not receipt["pass"]:
            return None, {"reason": "RECEIPT_FAILED", "eta_eps": receipt,
                          "detail": {"tied_with": [w for w in winners if w != cell]}}
        # memory check (strict): every earlier admitted batch of this recipe still reads back the same way
        faded = []
        for lesson in r["lessons"]:
            b2 = {n: Fraction(v) for n, v in lesson["stock_base"].items()}
            y2, w2 = self._read(r, b2, only_learned=True)
            if not (y2 == Fraction(lesson["made"]) and w2 == [lesson["ran_out"]]):
                faded.append(lesson["seed"])
        if faded:
            return None, {"reason": "MEMORY_CHECK_REFUSED", "eta_eps": receipt, "faded_seeds": faded,
                          "memory_check_ok": False, "detail": {"faded_seeds": faded}}
        r["lessons"].append({"seed": seed, "made": frac_text(made), "ran_out": cell,
                             "stock_base": {n: frac_text(v) for n, v in base.items()}})
        return book, {"reason": ADMITTED, "eta_eps": receipt, "memory_check_ok": True, "faded_seeds": [],
                      "new_recipe": is_new, "ingredient": cell, "value_base": frac_text(value),
                      "value_said": say_measure(from_base(value, r["taught_unit"][cell]), r["taught_unit"][cell]),
                      "detail": {}}

    def replay(self, rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """Replay witnessed rows, in order, on a FRESH brain. Changes nothing here."""
        fresh = WideRecipeBook()
        out = []
        for row in rows:
            stock = {k: (Fraction(v[0]), v[1]) for k, v in row["stock_before"].items()}
            rec = fresh.witness(row["product"], stock, Fraction(row["made"]) if row["made"] else 0, row["ran_out"])
            out.append({"seed": row["seed"], "admitted": rec["admitted"], "reason": rec["reason"]})
        return {"rows": out, "learned_digest": fresh.learned_digest()}


# =====================================================================================================================
# Parameter accounting
# =====================================================================================================================
def numbers_in_learned_state(brain: WideRecipeBook) -> List[Fraction]:
    """Every number in the brain's learned state (by walking it). The test asserts these are the coefficients."""
    found: List[Fraction] = []

    def walk(x: Any, key: str = "") -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif isinstance(x, (int, float, Fraction)) and not isinstance(x, bool):
            found.append(Fraction(x))
        elif isinstance(x, str) and re.fullmatch(r"-?\d+(?:/\d+)?", x):
            found.append(Fraction(x))

    walk(brain.learned_state())
    return found


def _exact_decimal(v: Fraction) -> str:
    """'4.92892159375' for a terminating fraction (exact), else 'p/q'."""
    d = v.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d != 1:
        return frac_text(v)
    places = 0
    while (v * 10 ** places).denominator != 1:
        places += 1
    text = str(Decimal(v.numerator) / Decimal(v.denominator)) if places == 0 else         str((Decimal(v.numerator * 10 ** places // v.denominator)).scaleb(-places))
    return text


def parameter_table(brain: Optional[WideRecipeBook] = None) -> List[Dict[str, Any]]:
    brain = brain or WideRecipeBook()
    slots = sum(len(r["support"]) for r in brain.recipes.values())
    return [
        {"class": "requirement coefficient a[recipe][ingredient]", "learned": True,
         "job": "how much of that ingredient (base unit of its kind) one unit of the product needs",
         "how_learned": "one witnessed batch where that ingredient alone ran out first (x_i / made, exact)",
         "slots_with_a_job": slots, "filled": brain.filled(), "count": slots,
         "per_recipe": {p: {"ingredients": len(r["support"]),
                            "filled": sum(1 for v in r["a"].values() if v is not None)}
                        for p, r in brain.recipes.items()}},
        {"class": "unit factor", "learned": False, "count": len(NAMED_FACTORS),
         "job": "convert a stated amount exactly into its kind's base unit (one conversion each)",
         "how_learned": "never learned: exact definitions, programmed",
         "factors": {k: {"value": _exact_decimal(v["value"]), "job": v["job"]} for k, v in NAMED_FACTORS.items()}},
    ]


def print_parameter_table(brain: Optional[WideRecipeBook] = None) -> List[Dict[str, Any]]:
    table = parameter_table(brain)
    print("RB-W1 parameter table (every parameter class and its job)")
    print(f"{'class':<48} {'learned':<8} {'count':>6}  job")
    for row in table:
        print(f"{row['class']:<48} {str(row['learned']):<8} {row['count']:>6}  {row['job']}")
    coef, unit = table
    print(f"  coefficients filled {coef['filled']} of {coef['slots_with_a_job']} slots with a job; "
          f"per recipe: {json.dumps(coef['per_recipe'], sort_keys=True)}")
    for k, v in unit["factors"].items():
        print(f"  {k:<15} = {v['value']:<26} {v['job']}")
    print("  structure (not learned numbers): product names, ingredient names, recipe supports, unit kinds, "
          f"MAX_INGREDIENTS = {MAX_INGREDIENTS}")
    print("  records (not parameters; the answer path never reads them): the witness log, and each recipe's saved "
          "admitted batches, which the memory check re-reads before admitting a new batch")
    print("  no other learned numbers exist (checked by walking the learned state)")
    return table
