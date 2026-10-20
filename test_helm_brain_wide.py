"""test_helm_brain_wide.py -- tests for RB-W1, the WIDE recipe brain (owner order "WIDEN THE BRAIN", 2026-10-19).

Written before the modules. What each group checks:
  A  exact numbers: Fraction round trips (thirds, mixed numbers, unicode fractions, number words), floats refused
  B  the unit table: 20 units, exact conversions, 9 named factors each with a job, no cross-dimension conversion
  C  one witnessed lesson per ingredient (X-REAL v2 scheme: that ingredient at its amount, the others in surplus)
     teaches all 6 coefficients of a 6-ingredient recipe exactly
  D  refusals: nothing ran out, two ran out at once, a learned ingredient would have tied, conflicts, too many
     ingredients, a batch that does not match the recipe, a unit of another kind
  E  UNDETERMINED on unlearned ingredients, unknown products and missing stock; the brain asks
  F  parameter accounting: a printed table; no other learned numbers exist
  G  reader -> brain -> voice end to end in exact fractions, through the live loop with WIDE_BRAIN ON
  H  switch OFF: the licensed brain is the loop's brain and nothing it says or writes changes
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_brain_wide as W
import helm_wide_turn as WT

# A 6-ingredient recipe written the way a cookbook writes it (thirds, mixed numbers, a count, a unicode fraction).
GINGER = [("2 1/4 cups flour", "flour", Fraction(9, 4), "cup"),
          ("1/3 cup brown sugar", "brown sugar", Fraction(1, 3), "cup"),
          ("2 eggs", "egg", Fraction(2), ""),
          ("1 teaspoon salt", "salt", Fraction(1), "teaspoon"),
          ("¾ cup milk", "milk", Fraction(3, 4), "cup"),
          ("1 1/2 tablespoons butter", "butter", Fraction(3, 2), "tablespoon")]


def lesson_stock(j):
    """X-REAL v2 lesson j: ingredient j at its listed amount, every other ingredient at twice its amount."""
    return {name: ((amt if i == j else 2 * amt), unit) for i, (_, name, amt, unit) in enumerate(GINGER)}


def taught(n=6):
    brain = W.WideRecipeBook()
    for j in range(n):
        rec = brain.witness("gingerbread", lesson_stock(j), 1, [GINGER[j][1]])
        assert rec["admitted"], rec
    return brain


class A_ExactNumbers(unittest.TestCase):
    def test_parse_forms(self):
        cases = {"3": Fraction(3), "1/3": Fraction(1, 3), "2/3": Fraction(2, 3), "1 1/3": Fraction(4, 3),
                 "1-1/2": Fraction(3, 2), "⅓": Fraction(1, 3), "1⅔": Fraction(5, 3), "1 ½": Fraction(3, 2),
                 "0.25": Fraction(1, 4), "one": Fraction(1), "twelve": Fraction(12), "a": Fraction(1),
                 "half": Fraction(1, 2), "a third": Fraction(1, 3), "two thirds": Fraction(2, 3),
                 "three quarters": Fraction(3, 4), "one and a half": Fraction(3, 2), "1/6": Fraction(1, 6),
                 "5/16": Fraction(5, 16)}
        for text, want in cases.items():
            self.assertEqual(W.parse_quantity(text), want, text)

    def test_round_trip_every_small_fraction(self):
        n = 0
        for den in range(1, 33):
            for num in range(1, 4 * den + 1):
                q = Fraction(num, den)
                said = W.say_quantity(q)
                self.assertEqual(W.parse_quantity(said), q, said)
                n += 1
        self.assertGreater(n, 2000)
        self.assertEqual(W.say_quantity(Fraction(4, 3)), "1 1/3")
        self.assertEqual(W.say_quantity(Fraction(2, 3)), "2/3")
        self.assertEqual(W.say_quantity(Fraction(6)), "6")

    def test_floats_ranges_and_junk_refused(self):
        for bad, code in ((0.1, "AMOUNT_NOT_EXACT"), (True, "AMOUNT_NOT_EXACT"), ("2 or 3", "AMOUNT_IS_A_RANGE"),
                          ("2-3", "AMOUNT_IS_A_RANGE"), ("1 to 1 1/2", "AMOUNT_IS_A_RANGE"),
                          ("some", "AMOUNT_NOT_A_NUMBER"), ("1/0", "AMOUNT_NOT_A_NUMBER"), ("", "AMOUNT_NOT_A_NUMBER")):
            with self.assertRaises(W.WideRefused) as cm:
                W.parse_quantity(bad)
            self.assertEqual(cm.exception.code, code, bad)

    def test_thirds_are_stored_exactly_not_refused(self):
        """The licensed brain refuses 1/3 (AMOUNT_NOT_BINARY64_EXACT); the wide brain keeps it exact."""
        brain = W.WideRecipeBook()
        rec = brain.witness("frosting", {"sugar": (Fraction(1, 3), "cup"), "butter": (Fraction(2), "cup")}, 1,
                            ["sugar"])
        self.assertTrue(rec["admitted"], rec)
        self.assertEqual(brain.coefficient("frosting", "sugar"), Fraction(16))      # 1/3 cup = 16 teaspoons
        self.assertEqual(brain.requirement_said("frosting", "sugar"), "1/3 cup")


class B_UnitTable(unittest.TestCase):
    def test_twenty_units_from_the_survey(self):
        survey_top20 = ["cup", "teaspoon", "tablespoon", "pound", "pint", "quart", "ounce", "gram", "can", "clove",
                        "slice", "gill", "milliliter", "pinch", "package", "bunch", "square", "saltspoon", "teacup",
                        "kilogram"]
        self.assertEqual(sorted(W.UNITS), sorted(survey_top20))

    def test_exact_conversions(self):
        cv = W.convert
        self.assertEqual(cv(1, "cup", "teaspoon"), 48)
        self.assertEqual(cv(1, "cup", "tablespoon"), 16)
        self.assertEqual(cv(1, "quart", "cup"), 4)
        self.assertEqual(cv(1, "pint", "gill"), 4)
        self.assertEqual(cv(1, "teaspoon", "milliliter"), Fraction("4.92892159375"))
        self.assertEqual(cv(1, "cup", "milliliter"), Fraction("236.5882365"))
        self.assertEqual(cv(1, "pound", "gram"), Fraction("453.59237"))
        self.assertEqual(cv(1, "pound", "ounce"), 16)
        self.assertEqual(cv(1, "kilogram", "pound"), Fraction(1000) / Fraction("453.59237"))
        self.assertEqual(cv(Fraction(1, 3), "cup", "tablespoon"), Fraction(16, 3))
        for a in W.UNITS:                     # every conversion inside one kind round-trips exactly
            for b in W.UNITS:
                if W.UNITS[a]["kind"] == W.UNITS[b]["kind"]:
                    self.assertEqual(cv(cv(Fraction(7, 3), a, b), b, a), Fraction(7, 3))

    def test_no_conversion_across_kinds(self):
        for a, b in (("cup", "gram"), ("pound", "teaspoon"), ("can", "cup"), ("clove", "pinch"), ("", "cup")):
            with self.assertRaises(W.WideRefused) as cm:
                W.convert(1, a, b)
            self.assertEqual(cm.exception.code, "UNIT_KIND_MISMATCH")

    def test_nine_named_factors_each_with_a_job(self):
        self.assertEqual(len(W.NAMED_FACTORS), 9)
        used = set()
        for u in W.UNITS.values():
            used |= set(u["factors"])
        self.assertEqual(used, set(W.NAMED_FACTORS))          # every factor is used by at least one unit
        for name, f in W.NAMED_FACTORS.items():
            self.assertIsInstance(f["value"], Fraction)
            self.assertTrue(f["job"])
        no_standard = sorted(u for u, d in W.UNITS.items() if not d["exact_standard"])
        self.assertEqual(no_standard, ["bunch", "can", "clove", "package", "pinch", "saltspoon", "slice", "square",
                                       "teacup"])


class C_OneLessonPerIngredient(unittest.TestCase):
    def test_six_ingredients_all_exact(self):
        brain = taught(6)
        req = {name: brain.requirement_said("gingerbread", name) for _, name, _, _ in GINGER}
        self.assertEqual(req, {"flour": "2 1/4 cups", "brown sugar": "1/3 cup", "egg": "2", "salt": "1 teaspoon",
                               "milk": "3/4 cup", "butter": "1 1/2 tablespoons"})
        for _, name, amt, unit in GINGER:
            self.assertEqual(brain.coefficient("gingerbread", name), W.to_base(amt, unit)[1])
        self.assertEqual(brain.unlearned("gingerbread"), [])
        self.assertEqual(len(brain.witness_log), 6)

    def test_answer_after_learning(self):
        brain = taught(6)
        stock = {"flour": (Fraction(9), "cup"), "brown sugar": (Fraction(2), "cup"), "egg": (Fraction(12), ""),
                 "salt": (Fraction(1, 3), "cup"), "milk": (Fraction(1), "quart"), "butter": (Fraction(1, 4), "pound")}
        rec = brain.evaluate("gingerbread", stock)           # butter in pounds vs taught in tablespoons: no density
        self.assertEqual((rec["status"], rec["gate"]), (W.UNDETERMINED, "UNIT_KIND_MISMATCH"))
        self.assertIn("butter", WT.say_wide(rec))
        stock["butter"] = (Fraction(1), "cup")               # 16 tablespoons -> 32/3 batches
        rec = brain.evaluate("gingerbread", stock)
        self.assertEqual(rec["status"], W.EVALUATED, rec)
        self.assertEqual(rec["yield"], "4")                  # flour 9/(9/4) = 4 is the smallest
        self.assertEqual(rec["limiting_reagent"], "flour")
        stock["flour"] = (Fraction(20), "cup")                # now egg is the smallest: 12 / 2 = 6
        stock["milk"] = (Fraction(2), "quart")
        stock["brown sugar"] = (Fraction(3), "cup")
        rec = brain.evaluate("gingerbread", stock)
        self.assertEqual((rec["yield"], rec["limiting_reagent"]), ("6", "egg"))   # 12 eggs / 2

    def test_lessons_in_any_order_give_the_same_book(self):
        a = taught(6)
        b = W.WideRecipeBook()
        for j in (5, 2, 0, 4, 1, 3):
            self.assertTrue(b.witness("gingerbread", lesson_stock(j), 1, [GINGER[j][1]])["admitted"])
        self.assertEqual(a.learned_digest(), b.learned_digest())

    def test_made_more_than_one(self):
        brain = W.WideRecipeBook()
        rec = brain.witness("bread", {"flour": (Fraction(10), "cup"), "water": (Fraction(8), "cup")}, 3, ["flour"])
        self.assertTrue(rec["admitted"])
        self.assertEqual(brain.requirement_said("bread", "flour"), "3 1/3 cups")

    def test_replay_rebuilds_the_same_book(self):
        brain = taught(6)
        fresh = brain.replay(brain.witness_log)
        self.assertTrue(all(r["admitted"] for r in fresh["rows"]))
        self.assertEqual(fresh["learned_digest"], brain.learned_digest())

    def test_ten_ingredients_allowed(self):
        brain = W.WideRecipeBook()
        stock = {f"spice {c}": (Fraction(2), "teaspoon") for c in "abcdefghi"}
        stock["flour"] = (Fraction(1), "cup")
        rec = brain.witness("cake", stock, 1, ["spice a"])
        self.assertTrue(rec["admitted"], rec)
        self.assertEqual(len(brain.support_of("cake")), 10)


class D_Refusals(unittest.TestCase):
    def assertRefused(self, rec, reason):
        self.assertFalse(rec["admitted"], rec)
        self.assertEqual(rec["reason"], reason, rec)

    def test_nothing_ran_out(self):
        brain = W.WideRecipeBook()
        self.assertRefused(brain.witness("gingerbread", lesson_stock(0), 1, []), "REFUSED_NOTHING_RAN_OUT")
        self.assertEqual(brain.products, {})                  # no recipe grows from a refused batch
        self.assertEqual(brain.filled(), 0)

    def test_two_ran_out_at_once(self):
        brain = W.WideRecipeBook()
        self.assertRefused(brain.witness("gingerbread", lesson_stock(0), 1, ["flour", "egg"]),
                           "REFUSED_TWO_RAN_OUT")
        self.assertEqual(brain.filled(), 0)

    def test_tie_the_brain_detects_itself(self):
        """The user says only flour ran out, but egg (already learned) would have run out at the same moment."""
        brain = taught(0)
        self.assertTrue(brain.witness("gingerbread", lesson_stock(2), 1, ["egg"])["admitted"])     # egg = 2
        stock = lesson_stock(0)
        stock["egg"] = (Fraction(2), "")                     # flour at its amount AND egg at its amount
        self.assertRefused(brain.witness("gingerbread", stock, 1, ["flour"]), "RECEIPT_FAILED")
        self.assertIsNone(brain.coefficient("gingerbread", "flour"))

    def test_memory_check_refuses_a_lesson_that_breaks_an_earlier_one(self):
        brain = W.WideRecipeBook()
        # lesson 1: flour ran out with water NOT in surplus (water 3 cups for 1 loaf)
        self.assertTrue(brain.witness("bread", {"flour": (Fraction(2), "cup"), "water": (Fraction(3), "cup")}, 1,
                                      ["flour"])["admitted"])
        # lesson 2 says water needs 3 cups: then lesson 1 had BOTH run out at once -> refused, nothing changes
        before = brain.learned_digest()
        rec = brain.witness("bread", {"flour": (Fraction(10), "cup"), "water": (Fraction(3), "cup")}, 1, ["water"])
        self.assertRefused(rec, "MEMORY_CHECK_REFUSED")
        self.assertEqual(rec["faded_seeds"], [1])
        self.assertEqual(brain.learned_digest(), before)

    def test_conflict(self):
        brain = taught(1)
        stock = lesson_stock(0)
        stock["flour"] = (Fraction(3), "cup")
        self.assertRefused(brain.witness("gingerbread", stock, 1, ["flour"]), "REFUSED_CONFLICT")

    def test_zero_made_and_unknown_ran_out(self):
        brain = W.WideRecipeBook()
        self.assertRefused(brain.witness("gingerbread", lesson_stock(0), 0, ["flour"]), "REFUSED_ZERO_YIELD")
        self.assertRefused(brain.witness("gingerbread", lesson_stock(0), 1, ["cocoa"]),
                           "REFUSED_RAN_OUT_NOT_IN_BATCH")

    def test_too_many_ingredients(self):
        stock = {f"spice {c}": (Fraction(1), "pinch") for c in "abcdefghijk"}
        self.assertRefused(W.WideRecipeBook().witness("cake", stock, 1, ["spice a"]), "REFUSED_TOO_MANY_INGREDIENTS")

    def test_batch_must_match_the_recipe(self):
        brain = taught(1)
        stock = lesson_stock(1)
        del stock["salt"]
        rec = brain.witness("gingerbread", stock, 1, ["brown sugar"])
        self.assertRefused(rec, "REFUSED_SUPPORT_MISMATCH")
        self.assertEqual(rec["detail"]["missing"], ["salt"])
        stock = lesson_stock(1)
        stock["cocoa"] = (Fraction(1), "cup")
        rec = brain.witness("gingerbread", stock, 1, ["brown sugar"])
        self.assertRefused(rec, "REFUSED_SUPPORT_MISMATCH")
        self.assertEqual(rec["detail"]["extra"], ["cocoa"])

    def test_unit_of_another_kind(self):
        brain = taught(1)
        stock = lesson_stock(1)
        stock["flour"] = (Fraction(2), "pound")
        self.assertRefused(brain.witness("gingerbread", stock, 1, ["brown sugar"]), "REFUSED_UNIT_KIND_MISMATCH")

    def test_unit_not_in_table(self):
        self.assertRefused(W.WideRecipeBook().witness("cake", {"butter": (Fraction(1), "stick"),
                                                               "flour": (Fraction(1), "cup")}, 1, ["butter"]),
                           "REFUSED_UNIT_NOT_IN_TABLE")


class E_Undetermined(unittest.TestCase):
    STOCK = {"flour": (Fraction(9), "cup"), "brown sugar": (Fraction(2), "cup"), "egg": (Fraction(12), ""),
             "salt": (Fraction(1, 3), "cup"), "milk": (Fraction(1), "quart"), "butter": (Fraction(1), "cup")}

    def test_unlearned_ingredients(self):
        brain = taught(3)
        rec = brain.evaluate("gingerbread", self.STOCK)
        self.assertEqual(rec["status"], W.UNDETERMINED)
        self.assertEqual(rec["gate"], "G1")
        self.assertEqual(rec["unlearned"], ["salt", "milk", "butter"])
        self.assertIsNone(rec["yield"])
        said = WT.say_wide(rec)
        self.assertIn("salt, milk, and butter", said)
        self.assertIn("didn't guess", said)

    def test_unknown_product_and_missing_stock(self):
        brain = taught(6)
        rec = brain.evaluate("pancake", self.STOCK)
        self.assertEqual((rec["status"], rec["gate"]), (W.UNDETERMINED, "UNKNOWN_PRODUCT"))
        stock = dict(self.STOCK)
        del stock["milk"]
        rec = brain.evaluate("gingerbread", stock)
        self.assertEqual((rec["status"], rec["gate"], rec["absent"]), (W.UNDETERMINED, "G1", ["milk"]))
        self.assertIn("How much milk", WT.say_wide(rec))

    def test_tie_and_zero(self):
        brain = taught(6)
        stock = dict(self.STOCK)
        stock["flour"] = (Fraction(9, 2), "cup")              # flour 2, egg 6, ... ; make egg tie at 2
        stock["egg"] = (Fraction(4), "")
        rec = brain.evaluate("gingerbread", stock)
        # v3: a tie fixes the amount (2); no single limiting reagent is claimed, the tied ones are named
        self.assertEqual((rec["status"], rec["gate"], rec["yield"], rec["limiting_reagent"]),
                         (W.EVALUATED, None, "2", None))
        self.assertEqual(sorted(rec["tied"]), ["egg", "flour"])
        self.assertIn("at exactly the same moment", WT.say_wide(rec))
        stock["egg"] = (Fraction(0), "")
        rec = brain.evaluate("gingerbread", stock)
        self.assertEqual((rec["status"], rec["gate"]), (W.UNDETERMINED, "G2"))


class F_ParameterAccounting(unittest.TestCase):
    def test_table_printed_and_no_other_learned_numbers(self):
        brain = taught(6)
        brain.witness("bread", {"flour": (Fraction(10), "cup"), "water": (Fraction(8), "cup")}, 5, ["flour"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            table = W.print_parameter_table(brain)
        text = buf.getvalue()
        print("\n" + text)
        classes = [row["class"] for row in table]
        self.assertEqual(classes, ["requirement coefficient a[recipe][ingredient]", "unit factor"])
        coef, unit = table
        self.assertEqual(coef["learned"], True)
        self.assertEqual(coef["filled"], 7)
        self.assertEqual(coef["slots_with_a_job"], 8)          # 6 gingerbread + 2 bread support cells
        self.assertEqual(unit["learned"], False)
        self.assertEqual(unit["count"], 9)
        self.assertIn("unit factor", text)
        # every number in the brain's learned state sits in a coefficient slot; nothing else is learned
        nums = W.numbers_in_learned_state(brain)
        self.assertEqual(len(nums), 7)
        self.assertEqual(sorted(nums), sorted(v for p in brain.products for v in
                                              (brain.coefficient(p, n) for n in brain.support_of(p)) if v is not None))
        self.assertEqual(set(vars(brain)), W.BRAIN_ATTRIBUTES)

    def test_witness_log_is_a_record_not_a_parameter(self):
        brain = taught(6)
        rec1 = brain.evaluate("gingerbread", E_Undetermined.STOCK)
        brain.witness_log.clear()
        rec2 = brain.evaluate("gingerbread", E_Undetermined.STOCK)
        self.assertEqual(rec1, rec2)


class G_EndToEnd(unittest.TestCase):
    """Reader -> brain -> voice, through the live loop with the switch ON."""

    @classmethod
    def setUpClass(cls):
        import helm_end_to_end_loop as E2E
        cls.E2E = E2E

    def lesson_sentence(self, j):
        """X-REAL v2 lesson j in words: line j at its listed amount, the others at twice theirs."""
        parts = []
        for i, (line, name, amt, unit) in enumerate(GINGER):
            q = amt if i == j else 2 * amt
            parts.append(line if i == j else WT.say_amount_of(q, unit, name))
        return ("We made 1 gingerbread from " + ", ".join(parts[:-1]) + " and " + parts[-1] +
                " and ran out of " + GINGER[j][1] + ".")

    def test_reader_lines(self):
        r = WT.read_wide("We made 1 gingerbread from 2 1/4 cups flour, sifted, 2/3 cup brown sugar and 4 large eggs "
                         "and ran out of flour.")
        self.assertEqual(r["status"], "WITNESS", r)
        w = r["witness"]
        self.assertEqual(w["product"], "gingerbread")
        self.assertEqual(w["made"], Fraction(1))
        self.assertEqual(w["ran_out"], ["flour"])
        self.assertEqual(w["stock"], {"flour": (Fraction(9, 4), "cup"), "brown sugar": (Fraction(2, 3), "cup"),
                                      "egg": (Fraction(4), "")})
        for text, code in (("We have 2 or 3 cups flour.", "AMOUNT_IS_A_RANGE"), ("We have salt to taste.", "NO_AMOUNT"),
                           ("We have 2 sticks butter.", "UNIT_NOT_IN_TABLE")):
            r = WT.read_wide(text)
            self.assertEqual((r["status"], r["clarify"]["code"]), ("CLARIFY", code), text)
        r = WT.read_wide("We made 1 bread from 2 cups flour and 1 cup water and ran out of flour and water.")
        self.assertEqual(r["witness"]["ran_out"], ["flour", "water"])
        r = WT.read_wide("We made 1 bread from 2 cups flour and 1 cup water and nothing ran out.")
        self.assertEqual(r["witness"]["ran_out"], [])
        self.assertEqual(WT.read_wide("How many gingerbreads can we make?")["topic"], "gingerbread")

    def test_live_loop_learns_six_and_answers_in_thirds(self):
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        self.assertIsInstance(loop.wide_book, W.WideRecipeBook)
        self.assertNotIsInstance(loop.brain, W.WideRecipeBook)          # v2: the licensed brain stays S0's brain
        out = loop.process_turn("How much gingerbread can we make?", tick=1)
        self.assertEqual(out["path"], "licensed")                        # the wide book does not hold it yet
        self.assertTrue(out["loop_status"].startswith("CLARIFY"), out["loop_status"])
        self.assertEqual(out["cubes_written"], [])
        for j in range(6):
            sentence = self.lesson_sentence(j)
            out = loop.process_turn(sentence, tick=2 + j)
            self.assertEqual(out["loop_status"], "WITNESS_ADMITTED", (sentence, out["response"]))
            self.assertEqual(out["path"], "wide")
            self.assertTrue(out["cube_receipt"]["read_back_ok"])
            if j == 1:
                self.assertIn("1/3 cup of brown sugar", out["response"])
        out = loop.process_turn("We have 3 cups flour, 1 cup brown sugar, 12 eggs, 1 tablespoon salt, 1 pint milk "
                                "and 1 cup butter.", tick=10)
        self.assertEqual(out["loop_status"], "STOCK_RECORDED", out["response"])
        out = loop.process_turn("How much gingerbread can we make?", tick=11)
        self.assertEqual(out["loop_status"], "SUCCESS_EVALUATED", out["response"])
        self.assertEqual(out["output_value"], "4/3")          # 3 cups flour / (9/4 cups) = 4/3
        self.assertIn("1 1/3 gingerbread", out["response"])
        self.assertIn("Flour runs out first", out["response"])
        self.assertTrue(out["cce_round_trip"]["verified"])
        out = loop.process_turn("We made 1 gingerbread from 3 cups flour and 1 cup milk and nothing ran out.", tick=12)
        self.assertEqual(out["loop_status"], "TEACH_REFUSED_REFUSED_NOTHING_RAN_OUT")
        self.assertEqual(out["cubes_written"], [])

    def test_live_loop_undetermined_asks(self):
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        loop.process_turn(self.lesson_sentence(0), tick=1)
        loop.process_turn("We have 3 cups flour, 1 cup brown sugar, 12 eggs, 1 tablespoon salt, 1 pint milk "
                          "and 1 cup butter.", tick=2)
        out = loop.process_turn("How much gingerbread can we make?", tick=3)
        self.assertEqual(out["loop_status"], "UNDETERMINED_CLARIFY")
        self.assertIn("didn't guess", out["response"])
        self.assertIn("brown sugar", out["response"])
        self.assertEqual(out["cubes_written"], [])


class I_V2ReaderFixes(unittest.TestCase):
    """RB-W1 v2 reader fixes (each a failure class found on RB-W1T's PUBLISHED practice draw, never an exam)."""

    def test_parenthetical_asides_are_not_names_or_amounts(self):
        self.assertEqual(WT.parse_line(WT.normalize_text("1 cup (250 ml or 8.5 fl oz) dry rice")),
                         {"name": "dry rice", "amount": Fraction(1), "unit": "cup", "said": "1 cup dry rice"})

    def test_comma_and_is_one_separator(self):
        lines, c = WT.parse_lines("One egg,, Four tablespoons of potato water, and 8 tablespoons of cornstarch")
        self.assertIsNone(c)
        self.assertEqual([x["name"] for x in lines], ["egg", "potato water", "cornstarch"])

    def test_more_note_words_and_emphasis(self):
        lines, c = WT.parse_lines(WT.normalize_text("1 cup of minced chicken, _very_ fine and 2 eggs"))
        self.assertIsNone(c)
        self.assertEqual([x["name"] for x in lines], ["minced chicken", "egg"])

    def test_hyphenated_and_qualified_units(self):
        self.assertEqual(WT.parse_line("2 table-spoons milk")["unit"], "tablespoon")
        r = WT.parse_line("1 heaping teaspoon salt")
        self.assertEqual((r["name"], r["unit"]), ("salt", "teaspoon"))

    def test_unit_word_alone_is_the_name(self):
        r = WT.parse_line("3 cloves")
        self.assertEqual((r["name"], r["amount"], r["unit"]), ("clove", Fraction(3), ""))

    def test_ran_out_name_resolved_against_the_batch(self):
        self.assertEqual(WT.resolve_ran_out("cupfuls of stock", ["stock", "chopped onion"]), "stock")
        self.assertEqual(WT.resolve_ran_out("table spoons milk", ["powdered sugar", "milk"]), "milk")
        self.assertEqual(WT.resolve_ran_out("granulated", ["shortening", "granulated or powdered sugar"]),
                         "granulated or powdered sugar")
        self.assertEqual(WT.resolve_ran_out("sugar", ["flour", "brown sugar"]), "brown sugar")
        self.assertEqual(WT.resolve_ran_out("sugar", ["white sugar", "brown sugar"]), "sugar")   # two: no guess
        r = WT.read_wide("We made 1 pie from 2 cupfuls of stock and 2 onions and ran out of cupfuls of stock.")
        self.assertEqual(r["witness"]["ran_out"], ["stock"])

    def test_product_made_of_a_size_word(self):
        r = WT.read_wide("We made 1 fine from 2 soaked rolls and 6 eggs and ran out of soaked rolls.")
        self.assertEqual(r["witness"]["product"], "fine")


class J_V2Routing(unittest.TestCase):
    """v2: the switch EXTENDS the licensed path; the wide path takes only turns the licensed path cannot bind."""

    @classmethod
    def setUpClass(cls):
        import helm_end_to_end_loop as E2E
        cls.E2E = E2E

    def turns(self):
        return [("w", "Bread", {"Flour": 10, "Water": 8}, 5, "Flour"), ("w", "Bread", {"Flour": 10, "Water": 2}, 2, "Water"),
                ("t", "There is 12 of Ω_Flour."), ("t", "Topic: Ω_Bread."),
                ("t", "How much bread could we bake with whatever is around?"), ("t", "There is 9 of Ω_Water."),
                ("t", "Topic: Ω_Bread."), ("t", "We have 12 cups of flour and no water. Can we bake bread?"),
                ("t", "Now we've got 9 cups of water — how much bread can we make?"),
                ("t", "We have 3 cups of saffron."), ("t", "What do we have on hand?"), ("t", "We're out of milk.")]

    def run_turns(self, on):
        loop = self.E2E.HELMEndToEndLoop(wide_brain=on) if on else self.E2E.HELMEndToEndLoop()
        out = []
        for i, t in enumerate(self.turns(), 1):
            r = loop.witness_batch(*t[1:], tick=i) if t[0] == "w" else loop.process_turn(t[1], tick=i)
            out.append((r["loop_status"], r.get("output_value"), r.get("limiting_reagent"), r["response"],
                        len(r["cubes_written"])))
            if on:
                self.assertEqual(r["path"], "licensed", t)
        return out

    def test_licensed_turns_identical_with_the_switch_on(self):
        old = os.environ.pop(W.WIDE_BRAIN_ENV, None)
        try:
            self.assertEqual(self.run_turns(True), self.run_turns(False))
        finally:
            if old is not None:
                os.environ[W.WIDE_BRAIN_ENV] = old

    def test_unknown_ingredient_stock_stays_a_question_when_the_wide_book_does_not_hold_it(self):
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        out = loop.process_turn("We have 3 cups of saffron.", tick=1)
        self.assertEqual(out["path"], "licensed")
        self.assertEqual(out["cubes_written"], [])
        self.assertEqual(loop.wide_book.recipes, {})

    def test_a_bread_the_licensed_brain_cannot_answer_goes_to_the_wide_book(self):
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        lines = ["1 cup sweet milk", "1/2 cup brown sugar", "1 teaspoon salt"]
        doubled = ["2 cup sweet milk", "1 cup brown sugar", "2 teaspoon salt"]
        for j, name in enumerate(["sweet milk", "brown sugar", "salt"]):
            parts = [lines[i] if i == j else doubled[i] for i in range(3)]
            r = loop.process_turn(f"We made 1 bread from {parts[0]}, {parts[1]} and {parts[2]} and ran out of {name}.",
                                  tick=1 + j)
            self.assertEqual((r["loop_status"], r["path"]), ("WITNESS_ADMITTED", "wide"), r["response"])
        r = loop.process_turn("We have 2 cups sweet milk, 1 cup brown sugar and 1 teaspoon salt.", tick=4)
        self.assertEqual((r["loop_status"], r["path"]), ("STOCK_RECORDED", "wide"), r["response"])
        r = loop.process_turn("How much bread can we make?", tick=5)
        self.assertEqual((r["loop_status"], r["path"], r["output_value"], r["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", "wide", "1", "salt"), r["response"])


class K_V3DishNamesAndLines(unittest.TestCase):
    """RB-W1 v3 fixes (2026-10-20), each a failure class found on the builder's NEW practice draw v2 (seed text
    RBW1-DISHNAME-FIX-PRACTICE-V2-20261020-builder-published), never on a sealed exam."""

    @classmethod
    def setUpClass(cls):
        import helm_end_to_end_loop as E2E
        cls.E2E = E2E

    def names(self, text):
        lines, c = WT.parse_lines(WT.normalize_text(text))
        self.assertIsNone(c, text)
        return [x["name"] for x in lines]

    def test_a_comma_or_and_without_a_new_amount_stays_in_its_line(self):
        self.assertEqual(self.names("1 cup squash, steamed and strained, 2 cup heavy cream and 6 eggs, slightly beaten"),
                         ["squash", "heavy cream", "egg"])
        self.assertEqual(self.names("6 eggs, whites and yolks separately., 2 cup butter. and 6 cups sugar."),
                         ["egg", "butter", "sugar"])
        self.assertEqual(self.names("1 cup cold, cooked rice. and 4 tablespoons flour."), ["cooked rice", "flour"])
        self.assertEqual(self.names("12 large, ripe tomatoes and 6 green peppers"), ["ripe tomato", "green pepper"])
        self.assertEqual(self.names("3/4 cup of milk and a little salt and 2 eggs"), ["milk", "egg"])
        self.assertEqual(self.names("250 g raw tahini or 200 g natural peanut butter and 2 g salt"),
                         ["tahini or 200 g natural peanut butter", "salt"])
        self.assertEqual(self.names("1 and a half cups flour and an egg"), ["flour", "egg"])

    def test_two_amounts_for_one_ingredient_are_asked_never_summed(self):
        for text in ("1/2 cup plus 1 tablespoon water", "2 large or 4 small green peppers"):
            lines, c = WT.parse_lines(text)
            self.assertEqual((lines, c["code"]), ([], "AMOUNT_HAS_TWO_PARTS"), text)
        r = WT.read_wide("We have 12 cups of flour and no water.")
        self.assertEqual((r["status"], r["clarify"]["code"]), ("CLARIFY", "NO_AMOUNT"))

    def test_ran_out_phrase_found_inside_exactly_one_line(self):
        r = WT.read_wide("We made 1 balls from 1 cup cold, cooked rice., 4 tablespoons flour. and 2 egg slightly "
                         "beaten. and ran out of cold.")
        self.assertEqual((r["status"], r["witness"]["ran_out"]), ("WITNESS", ["cooked rice"]))
        r = WT.read_wide("We made 1 sauce from 12 large, ripe tomatoes, 6 green peppers and 4 onions and ran out of "
                         "large.")
        self.assertEqual(r["witness"]["ran_out"], ["ripe tomato"])
        said = {"white sugar": "1 cup white sugar, sifted", "brown sugar": "1 cup brown sugar, sifted"}
        self.assertEqual(WT.resolve_ran_out("sifted", list(said), said), "sifted")     # two lines hold it: no guess

    def test_dish_name_variants_bind_to_one_dish(self):
        forms = ["gingerbread", "Gingerbread", "the gingerbreads", "a batch of gingerbread", "Gingerbread recipe",
                 "the recipe for gingerbread", "our gingerbread"]
        self.assertEqual({WT.product_key(WT.bind_product(f)) for f in forms}, {"gingerbread"})
        self.assertEqual(WT.product_key(WT.bind_product("Grandma's Apple-Pies")),
                         WT.product_key(WT.bind_product("grandmas apple pie")))
        self.assertEqual(WT.bind_product("cookies"), "cookie")
        for f in ("it", "a batch", "some", "2"):
            self.assertIsNone(WT.bind_product(f), f)
        r = WT.read_wide("We made 1 chicken with rice from 2 cups rice and 1 pound chicken and ran out of rice.")
        self.assertEqual(r["witness"]["product"], "chicken with rice")

    def test_live_loop_dish_name_variants_teach_and_answer_one_dish(self):
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        for t, text in enumerate(("We made 1 Grandma's Apple-Pies from 2 cups flour and 12 apples and ran out of flour.",
                                  "We made 1 grandmas apple pie from 4 cups flour and 6 apples and ran out of apples."),
                                 1):
            r = loop.process_turn(text, tick=t)
            self.assertEqual((r["loop_status"], r["path"]), ("WITNESS_ADMITTED", "wide"), r["response"])
        self.assertEqual(list(loop.wide_book.recipes), ["grandma apple pie"])
        loop.process_turn("We have 5 cups flour and 9 apples.", tick=3)
        r = loop.process_turn("How much grandma's apple pie can we make?", tick=4)
        self.assertEqual((r["loop_status"], r["output_value"], r["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", "3/2", "apple"), r["response"])

    def test_missing_dish_name_is_asked_once_then_accepted(self):
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        r = loop.process_turn("We made 1 from 2 cups flour and 1 cup water and ran out of flour.", tick=1)
        self.assertEqual((r["loop_status"], r["path"], r["cubes_written"]), ("CLARIFY_WIDE_NO_PRODUCT", "wide", []))
        self.assertIn("What's the dish called?", r["response"])
        self.assertEqual(loop.wide_book.recipes, {})
        r = loop.process_turn("It was flatbread.", tick=2)
        self.assertEqual((r["loop_status"], r["path"]), ("WITNESS_ADMITTED", "wide"), r["response"])
        self.assertEqual(loop.wide_book.coefficient("flatbread", "flour"), 2 * 16 * 3)    # 2 cups, in teaspoons
        r = loop.process_turn("We made a batch from 2 cups rice and 1 cup milk and ran out of rice.", tick=3)
        self.assertEqual((r["loop_status"], r["path"]), ("CLARIFY_WIDE_NO_PRODUCT", "wide"), r["response"])
        r = loop.process_turn("hmm?", tick=4)                       # not a dish name: dropped, never asked twice
        self.assertEqual(r["loop_status"], "CLARIFY_WIDE_DISH_NAME_NOT_BOUND")
        self.assertEqual(r["cubes_written"], [])
        r = loop.process_turn("rice pudding", tick=5)
        self.assertEqual(r["path"], "licensed")
        self.assertNotIn("rice pudding", loop.wide_book.recipes)

    def test_ten_whole_number_ingredients_with_equal_amounts(self):
        """10 ingredients, every one 2 (a whole number), the others at twice theirs in each lesson: all ten lessons
        admitted; a pantry where two tie answers the amount and names both."""
        loop = self.E2E.HELMEndToEndLoop(wide_brain=True)
        names = ["flour", "sugar", "oat", "raisin", "walnut", "date", "fig", "almond", "pecan", "cashew"]
        for j, n in enumerate(names):
            parts = [f"{2 if i == j else 4} cups {m}" for i, m in enumerate(names)]
            text = "We made 1 trail cake from " + ", ".join(parts[:-1]) + " and " + parts[-1] + f" and ran out of {n}."
            r = loop.process_turn(text, tick=1 + j)
            self.assertEqual(r["loop_status"], "WITNESS_ADMITTED", (n, r["response"]))
        self.assertEqual(loop.wide_book.unlearned("trail cake"), [])
        stock = [f"{6 if i < 2 else 10} cups {m}" for i, m in enumerate(names)]
        loop.process_turn("We have " + ", ".join(stock[:-1]) + " and " + stock[-1] + ".", tick=20)
        r = loop.process_turn("How much trail cake can we make?", tick=21)
        self.assertEqual((r["loop_status"], r["output_value"], r["limiting_reagent"]),
                         ("SUCCESS_EVALUATED", "3", None), r["response"])
        self.assertIn("Flour and sugar would run out at exactly the same moment", r["response"])


class H_SwitchOff(unittest.TestCase):
    def test_switch_default_off(self):
        old = os.environ.pop(W.WIDE_BRAIN_ENV, None)
        try:
            self.assertFalse(W.wide_brain_on())
            self.assertTrue(W.wide_brain_on(True))
            os.environ[W.WIDE_BRAIN_ENV] = "1"
            self.assertTrue(W.wide_brain_on())
            self.assertFalse(W.wide_brain_on(False))
        finally:
            os.environ.pop(W.WIDE_BRAIN_ENV, None)
            if old is not None:
                os.environ[W.WIDE_BRAIN_ENV] = old

    def test_off_loop_uses_the_licensed_brain_and_never_loads_the_wide_modules(self):
        code = ("import sys, os; sys.path.insert(0, %r); os.environ.pop(%r, None); import helm_end_to_end_loop as E;"
                "l = E.HELMEndToEndLoop(); from helm_brain_canonical import CanonicalRecipeBrain as C;"
                "print(isinstance(l.brain, C), 'helm_brain_wide' in sys.modules, 'helm_wide_turn' in sys.modules,"
                "len(l.brain.ingredients), sorted(l.brain.products))") % (HERE, W.WIDE_BRAIN_ENV)
        out = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "True False False 8 ['Bread', 'Frosting', 'Meringue', 'Starter']")

    def test_licensed_files_untouched(self):
        """helm_brain_canonical.py and the reader are byte-identical to the thread branch this build started from."""
        base = "d4488f2a"
        for rel in ("helm_brain_canonical.py", "helm_english_in.py", "helm_voice.py"):
            git = subprocess.run(["git", "-C", HERE, "show", f"{base}:{rel}"], capture_output=True, timeout=60)
            if git.returncode != 0:
                self.skipTest("base commit not reachable in this checkout")
            with open(os.path.join(HERE, rel), "rb") as fh:
                self.assertEqual(fh.read().replace(b"\r\n", b"\n"), git.stdout.replace(b"\r\n", b"\n"), rel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
