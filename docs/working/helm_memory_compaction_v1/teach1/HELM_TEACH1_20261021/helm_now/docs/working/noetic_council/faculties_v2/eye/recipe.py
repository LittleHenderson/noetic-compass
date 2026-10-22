"""eye/recipe.py -- the eye's one recipe, and the Limiting Reagent readout.

UNITY_EYE.md section 2.1 gives the MINI-VERSION form (ACCEPTED_BY_OWNER): one recipe over the
measured health signals, all requirements a_i = 1, and the readout

    Y_T = min_i (x_i / a_i)          (CAS_FOUNDATIONAL_CLARIFICATIONS.md:440)
    the Limiting Reagent = the ingredient at the minimum   (:453)

so the readout names **the component most short of unity**, instead of printing a list of flags.

The gate is the design's own (`UNITY_EYE.md:94-97`, following `ADDENDUM_RPM_GATE_20261014.md`
:18-27):

    G1  an ingredient is ABSENT this stage -- named, and the reading is UNDETERMINED, not a guess
    G2  the stage had nothing to read at all
    G3  two or more ingredients tie at the minimum -- all named, no single remedy
    G4  the eye's own last reading failed its receipt

Two sentences from the design that this module keeps literal:

  * "No `×` anywhere in the eye's recipe: no emergent fused state is named" (:100). The recipe
    is a `+` of co-present ingredients (Clarification 10 section 12), and nothing here fuses.
  * "Limiting Reagent ≠ Lacunarity" (:102). A low x_i is a shortage among present measurements.
    An ABSENT x_i is a gap in the eye's own ledger and reads UNDETERMINED.

A reading is exact: every x_i is a `Fraction`, Y_T is a `Fraction`, and no number is rounded.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM.
"""

from __future__ import annotations

import dataclasses
import json
from fractions import Fraction

__all__ = [
    "ONE", "G1_INGREDIENT_ABSENT", "G2_NOTHING_READ", "G3_TIE_AT_THE_MINIMUM",
    "G4_LAST_RECEIPT_FAILED", "UNDETERMINED",
    "Ingredient", "Recipe", "RecipeReading", "RecipeRefusal", "recipe_from_counts",
]

ONE = Fraction(1)

#: The gate words. They are words, never a score.
G1_INGREDIENT_ABSENT = "G1_INGREDIENT_ABSENT"
G2_NOTHING_READ = "G2_NOTHING_READ"
G3_TIE_AT_THE_MINIMUM = "G3_TIE_AT_THE_MINIMUM"
G4_LAST_RECEIPT_FAILED = "G4_LAST_RECEIPT_FAILED"
UNDETERMINED = "UNDETERMINED"

#: Refusal codes.
RECIPE_NEEDS_INGREDIENTS = "RECIPE_NEEDS_INGREDIENTS"
RECIPE_BAD_MEASUREMENT = "RECIPE_BAD_MEASUREMENT"
RECIPE_BAD_REQUIREMENT = "RECIPE_BAD_REQUIREMENT"

# UNDECIDED IN SOURCES: what each ingredient's requirement a_i is, when UNITY_EYE.md section 2.1 sets every a_i = 1 as PROPOSED and Q24 leaves the numbers to the owner -- so this build uses exactly 1 for every ingredient and lets a caller pass another requirement, and never learns one from an invented gold.
# UNDECIDED IN SOURCES: whether the eye's readout must be reported per stage of 16 ticks, when UNITY_EYE.md section 2.1 says "per stage (16 ticks, DRIVE_LOOP.md:128)" and this project's packages have no ticks at all -- so this build reads once per call, names the call a stage, and records the stage id in the log instead of inventing a tick count.


class RecipeRefusal(Exception):
    """A refusal with a stable code. Nothing here is ever a guess."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclasses.dataclass(frozen=True)
class Ingredient:
    """One prerequisite of unity, with its count rule, its requirement and its measurement.

    `measured` is the exact fraction this stage read, or `None` when nothing of that kind was
    measured. `None` is ABSENT, and ABSENT is not zero: zero would say the component failed,
    when the truth is that the eye did not see it (the design's G1).
    """

    name: str
    count_rule: str
    required: Fraction = ONE
    measured: object = None
    detail: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise RecipeRefusal(RECIPE_BAD_MEASUREMENT, f"an ingredient needs a name, got {self.name!r}")
        if isinstance(self.required, bool) or not isinstance(self.required, Fraction) or self.required <= 0:
            raise RecipeRefusal(
                RECIPE_BAD_REQUIREMENT,
                f"ingredient {self.name!r} has requirement {self.required!r}; a requirement is a "
                f"positive exact Fraction",
            )
        if self.measured is not None:
            value = self.measured
            if isinstance(value, bool) or not isinstance(value, Fraction):
                raise RecipeRefusal(
                    RECIPE_BAD_MEASUREMENT,
                    f"ingredient {self.name!r} measured {value!r}; a measurement is an exact "
                    f"Fraction or ABSENT, and a float would round",
                )
            if value < 0 or value > 1:
                raise RecipeRefusal(
                    RECIPE_BAD_MEASUREMENT,
                    f"ingredient {self.name!r} measured {value!r}, outside [0, 1]; a normalized "
                    f"health signal cannot be more than whole or less than nothing",
                )

    @property
    def present(self) -> bool:
        return self.measured is not None

    def yield_(self) -> object:
        """x_i / a_i, or None when the ingredient is ABSENT."""
        if self.measured is None:
            return None
        return self.measured / self.required

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "count_rule": self.count_rule,
            "required": str(self.required),
            "measured": None if self.measured is None else str(self.measured),
            "detail": self.detail,
        }


@dataclasses.dataclass(frozen=True)
class Recipe:
    """The eye's recipe for one component: the ingredients, in a fixed order, nothing fused."""

    omega: str
    ingredients: tuple = ()

    def __post_init__(self) -> None:
        if not isinstance(self.omega, str) or not self.omega.strip():
            raise RecipeRefusal(RECIPE_BAD_MEASUREMENT, f"a recipe names its target, got {self.omega!r}")
        materialised = tuple(self.ingredients)
        if not materialised:
            raise RecipeRefusal(
                RECIPE_NEEDS_INGREDIENTS,
                f"the recipe for {self.omega!r} has no ingredients, so it has no readout",
            )
        for ingredient in materialised:
            if not isinstance(ingredient, Ingredient):
                raise RecipeRefusal(
                    RECIPE_BAD_MEASUREMENT,
                    f"a recipe holds Ingredients, got {type(ingredient).__name__}",
                )
        object.__setattr__(self, "ingredients", materialised)

    def names(self) -> tuple:
        return tuple(ingredient.name for ingredient in self.ingredients)

    def get(self, name) -> Ingredient:
        for ingredient in self.ingredients:
            if ingredient.name == name:
                return ingredient
        raise RecipeRefusal("RECIPE_NO_SUCH_INGREDIENT", f"{name!r} is not in {list(self.names())}")

    def read(self) -> "RecipeReading":
        return RecipeReading(component=self.omega, ingredients=self.ingredients)

    def as_dict(self) -> dict:
        return {"omega": self.omega, "ingredients": [item.as_dict() for item in self.ingredients]}

    def __repr__(self) -> str:
        return "Recipe(%s, %d ingredients)" % (self.omega, len(self.ingredients))


@dataclasses.dataclass(frozen=True)
class RecipeReading:
    """One reading of one recipe: Y_T, the Limiting Reagent, the gate, and the receipt.

    The receipt is the design's eta / epsilon pair (`UNITY_EYE.md:98-99`): eta writes the
    reading record; epsilon re-reads it from the record and recomputes Y_T and L from the stored
    counts; the two must be equal. `recheck()` is epsilon, and it recomputes from `counts`, never
    from the numbers it just printed.
    """

    component: str
    ingredients: tuple

    # -- the readout --------------------------------------------------------- #
    @property
    def counts(self) -> tuple:
        """The stored counts a re-read recomputes from: (name, requirement, measured)."""
        return tuple((item.name, item.required, item.measured) for item in self.ingredients)

    def theoretical_yield(self) -> object:
        """Y_T = min_i(x_i / a_i) over the ingredients that were measured, or None."""
        yields = [item.yield_() for item in self.ingredients if item.present]
        if not yields:
            return None
        return min(yields)

    def limiting(self) -> tuple:
        """The names at the minimum. More than one name means a tie, which the gate names."""
        target = self.theoretical_yield()
        if target is None:
            return ()
        return tuple(item.name for item in self.ingredients if item.present and item.yield_() == target)

    def absent(self) -> tuple:
        return tuple(item.name for item in self.ingredients if not item.present)

    def get(self, name) -> Ingredient:
        """One ingredient by name, so a caller reads the count and the rule behind a number."""
        for item in self.ingredients:
            if item.name == name:
                return item
        raise RecipeRefusal(
            "RECIPE_NO_SUCH_INGREDIENT",
            f"{name!r} is not in {[item.name for item in self.ingredients]}",
        )

    def gate(self) -> object:
        """G1 / G2 / G3, or None when nothing is short and there is one limiting reagent.

        G4 is the eye's own check and lives in `eye.py`, because it is about the eye's last
        reading rather than about this recipe. "Nothing is short" means every ingredient met its
        requirement (x_i >= a_i, so Y_T >= 1): a tie at the top is not a shortage, and reporting
        G3 there would cry wolf on a perfect reading.
        """
        if not any(item.present for item in self.ingredients):
            return G2_NOTHING_READ
        if self.absent():
            return G1_INGREDIENT_ABSENT
        target = self.theoretical_yield()
        if target is not None and target >= ONE and len(self.limiting()) > 1:
            return None
        if len(self.limiting()) > 1:
            return G3_TIE_AT_THE_MINIMUM
        return None

    # -- the receipt --------------------------------------------------------- #
    def record(self) -> dict:
        """eta: the reading record, as it is written to the eye's log."""
        return {
            "component": self.component,
            "ingredients": [item.as_dict() for item in self.ingredients],
            "Y_T": None if self.theoretical_yield() is None else str(self.theoretical_yield()),
            "limiting": list(self.limiting()),
            "absent": list(self.absent()),
            "gate": self.gate(),
        }

    @staticmethod
    def recompute(counts):
        """epsilon: Y_T and L recomputed from stored counts alone."""
        present = [(name, required, measured) for name, required, measured in counts
                   if measured is not None]
        if not present:
            return None, ()
        yields = [(measured / required, name) for name, required, measured in present]
        target = min(value for value, _name in yields)
        return target, tuple(name for value, name in yields if value == target)

    def receipt(self) -> dict:
        """The eta / epsilon receipt: what was written, what was re-read, and whether they hold."""
        stored = self.record()
        recorded = json.dumps(stored, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        reparsed = json.loads(recorded)
        counts = tuple((item["name"], Fraction(item["required"]),
                        None if item["measured"] is None else Fraction(item["measured"]))
                       for item in reparsed["ingredients"])
        why, limiting = RecipeReading.recompute(counts)
        written_yield = None if reparsed["Y_T"] is None else Fraction(reparsed["Y_T"])
        holds = (written_yield == why) and (tuple(reparsed["limiting"]) == limiting)
        return {
            "component": self.component,
            "holds": holds,
            "written_Y_T": None if written_yield is None else str(written_yield),
            "reread_Y_T": None if why is None else str(why),
            "written_limiting": list(reparsed["limiting"]),
            "reread_limiting": list(limiting),
            "record_digest": __import__("hashlib").sha256(recorded.encode("utf-8")).hexdigest(),
        }

    def text(self) -> str:
        """The one-line readout, in plain words."""
        target = self.theoretical_yield()
        if target is None:
            return "%s: nothing was measured, so the reading is %s" % (self.component, UNDETERMINED)
        if target >= ONE:
            return "%s: every ingredient met its requirement (Y_T %s); nothing is short" % (
                self.component, _plain_fraction(target)
            )
        names = ", ".join(self.limiting())
        gate = self.gate()
        tail = "" if gate is None else " (gate %s)" % (gate,)
        return "%s: Y_T %s, limiting reagent %s%s" % (
            self.component, _plain_fraction(target), names, tail
        )

    def __repr__(self) -> str:
        return "RecipeReading(%s, Y_T=%r, limiting=%r)" % (
            self.component, self.theoretical_yield(), self.limiting()
        )


def _plain_fraction(value) -> str:
    """`4/9 = 0.444...` style, exact first and never rounded into a float."""
    value = Fraction(value)
    if value.denominator == 1:
        return "%d" % (value.numerator,)
    return "%d/%d" % (value.numerator, value.denominator)


def recipe_from_counts(omega, counts) -> Recipe:
    """Build a recipe from `(name, count_rule, present, required)` tuples plus measured counts.

    `counts` is `(name, measured_or_None, detail)`; `required` defaults to ONE, the design's
    PROPOSED requirement for every ingredient (`UNITY_EYE.md:93`).
    """
    ingredients = []
    for name, count_rule, requirement, measured, detail in counts:
        ingredients.append(
            Ingredient(name=name, count_rule=count_rule, required=requirement, measured=measured,
                       detail=detail)
        )
    return Recipe(omega, tuple(ingredients))
