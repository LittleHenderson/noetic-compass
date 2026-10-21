"""Tests for stage 1c of the wide brain (recipe-shape packet Q7, owner word "build both"): the widened unit table and
NOTE lines behind the switch WIDE_UNITS_NOTE (helm_brain_wide.units_note_on; HELM_WIDE_UNITS_NOTE = 1 / ON / TRUE / YES).

Proved here, nothing more: OFF is reader v5 / brain v1 unchanged (the 20-unit table, 9 factors, the same questions);
ON adds 6 units with exact programmed factors and reads lines with no exact amount as NOTE lines that are present,
never a requirement, never the limiting ingredient, never a number. Standard library only; no network."""
from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import contextmanager, redirect_stdout
from fractions import Fraction

import helm_brain_wide as W
import helm_wide_turn as WT


@contextmanager
def stage_1c(on: bool):
    old = os.environ.get(W.WIDE_UNITS_NOTE_ENV)
    try:
        if on:
            os.environ[W.WIDE_UNITS_NOTE_ENV] = "1"
        else:
            os.environ.pop(W.WIDE_UNITS_NOTE_ENV, None)
        yield
    finally:
        if old is None:
            os.environ.pop(W.WIDE_UNITS_NOTE_ENV, None)
        else:
            os.environ[W.WIDE_UNITS_NOTE_ENV] = old


def names(text):
    lines, ask = WT.parse_lines(text)
    return [(x["name"], x["amount"], x["unit"], bool(x.get("note"))) for x in lines], ask


class A_SwitchOffIsReaderV5(unittest.TestCase):
    def test_default_off_and_words(self):
        with stage_1c(False):
            self.assertFalse(W.units_note_on())
        for w in ("1", "ON", "true", "Yes"):
            os.environ[W.WIDE_UNITS_NOTE_ENV] = w
            try:
                self.assertTrue(W.units_note_on(), w)
            finally:
                os.environ.pop(W.WIDE_UNITS_NOTE_ENV, None)
        os.environ[W.WIDE_UNITS_NOTE_ENV] = "0"
        try:
            self.assertFalse(W.units_note_on())
        finally:
            os.environ.pop(W.WIDE_UNITS_NOTE_ENV, None)
        self.assertTrue(W.units_note_on(True))
        self.assertFalse(W.units_note_on(False))

    def test_off_tables_and_questions_unchanged(self):
        with stage_1c(False):
            self.assertEqual(len(W.unit_table()), 20)
            self.assertEqual(len(W.named_factors()), 9)
            self.assertIsNone(W.unit_of("liter"))
            self.assertIsNone(W.unit_of("dozen"))
            self.assertIsNone(W.unit_of_two_words("fl", "oz"))
            with self.assertRaises(W.WideRefused) as cm:
                W.unit_kind("liter")
            self.assertEqual(cm.exception.code, "UNIT_NOT_IN_TABLE")
            for text, code in (("salt", "NO_AMOUNT"), ("pepper to taste", "NO_AMOUNT"), ("2 sticks butter", "UNIT_NOT_IN_TABLE"),
                               ("1 liter milk", "UNIT_NOT_IN_TABLE"), ("1 dash salt", "UNIT_NOT_IN_TABLE"),
                               ("no water", "NO_AMOUNT")):
                lines, ask = WT.parse_lines(text)
                self.assertEqual((lines, ask["code"]), ([], code), text)
            got, ask = names("a pinch of salt")             # OFF: the own count unit of reader v5, unchanged
            self.assertEqual((got, ask), ([("salt", Fraction(1), "pinch", False)], None))
            got, ask = names("2 cans tomatoes")
            self.assertEqual((got, ask), ([("tomato", Fraction(2), "can", False)], None))
            with self.assertRaises(W.WideRefused):          # OFF: a None stock value is not an amount
                W._stock_entry(None)
            self.assertEqual(W.parameter_table()[1]["count"], 9)


class B_WidenedUnits(unittest.TestCase):
    def test_six_units_each_from_exact_programmed_factors(self):
        with stage_1c(True):
            self.assertEqual(sorted(W.UNITS_WIDENED), ["centiliter", "deciliter", "dozen", "fluid ounce", "gallon", "liter"])
            self.assertEqual(sorted(W.UNITS), sorted(W.UNITS))          # the 20-unit table itself is not touched
            self.assertEqual(len(W.UNITS), 20)
            self.assertEqual(len(W.unit_table()), 26)
            self.assertEqual(len(W.NAMED_FACTORS), 9)
            self.assertEqual(len(W.NAMED_FACTORS_WIDENED), 6)
            self.assertEqual(len(W.named_factors()), 15)
            self.assertEqual(W.parameter_table()[1]["count"], 15)
            used = set()
            for u in W.UNITS_WIDENED.values():
                used |= set(u["factors"])
                self.assertTrue(u["exact_standard"])
                self.assertIsInstance(u["base"], Fraction)
            self.assertTrue(set(W.NAMED_FACTORS_WIDENED) <= used)     # every new factor converts at least one unit
            for name, f in W.NAMED_FACTORS_WIDENED.items():
                self.assertIsInstance(f["value"], Fraction)
                self.assertTrue(f["job"], name)
            self.assertEqual(W.NAMED_FACTORS_WIDENED["ML_PER_L"]["value"], 1000)
            self.assertEqual(W.NAMED_FACTORS_WIDENED["QUART_PER_GALLON"]["value"], 4)
            self.assertEqual(W.NAMED_FACTORS_WIDENED["TBSP_PER_FLOZ"]["value"], 2)
            self.assertEqual(W.NAMED_FACTORS_WIDENED["EACH_PER_DOZEN"]["value"], 12)

    def test_exact_conversions(self):
        with stage_1c(True):
            cv = W.convert
            self.assertEqual(cv(1, "gallon", "cup"), 16)
            self.assertEqual(cv(1, "gallon", "quart"), 4)
            self.assertEqual(cv(1, "liter", "milliliter"), 1000)
            self.assertEqual(cv(1, "deciliter", "milliliter"), 100)
            self.assertEqual(cv(1, "centiliter", "milliliter"), 10)
            self.assertEqual(cv(1, "liter", "teaspoon"), Fraction(1000) / Fraction("4.92892159375"))
            self.assertEqual(cv(1, "fluid ounce", "tablespoon"), 2)
            self.assertEqual(cv(1, "fluid ounce", "teaspoon"), 6)
            self.assertEqual(cv(1, "fluid ounce", "milliliter"), Fraction("29.5735295625"))
            self.assertEqual(cv(1, "cup", "fluid ounce"), 8)
            self.assertEqual(cv(1, "gallon", "liter"), Fraction("3.785411784"))
            self.assertEqual(cv(1, "dozen", ""), 12)
            self.assertEqual(cv(30, "", "dozen"), Fraction(5, 2))
            table = W.unit_table()
            for a in table:
                for b in table:
                    if table[a]["kind"] == table[b]["kind"]:
                        self.assertEqual(cv(cv(Fraction(7, 3), a, b), b, a), Fraction(7, 3), (a, b))
            for a, b in (("liter", "gram"), ("gallon", "pound"), ("dozen", "cup"), ("fluid ounce", "ounce"), ("liter", "can")):
                with self.assertRaises(W.WideRefused) as cm:
                    cv(1, a, b)
                self.assertEqual(cm.exception.code, "UNIT_KIND_MISMATCH", (a, b))
            self.assertEqual(W.say_measure(Fraction(2), "dozen"), "2 dozen")
            self.assertEqual(W.say_measure(Fraction(3, 2), "liter"), "1 1/2 liters")
            self.assertEqual(W.say_measure(Fraction(4), "fluid ounce"), "4 fluid ounces")

    def test_unit_words(self):
        with stage_1c(True):
            for word, unit in (("liter", "liter"), ("litres", "liter"), ("l", "liter"), ("dl", "deciliter"), ("cl", "centiliter"),
                               ("gallons", "gallon"), ("gal.", "gallon"), ("dozen", "dozen"), ("doz", "dozen"), ("Cups", "cup")):
                self.assertEqual(W.unit_of(word), unit, word)
            self.assertEqual(W.unit_of_two_words("fl", "oz"), "fluid ounce")
            self.assertEqual(W.unit_of_two_words("Fluid", "ounces"), "fluid ounce")
            self.assertIsNone(W.unit_of_two_words("fl", "cup"))
            self.assertIsNone(W.unit_of("stick"))

    def test_note_unit_words_partition_the_other_unit_words(self):
        self.assertTrue(W.NOTE_UNIT_WORDS <= W.OTHER_UNIT_WORDS)
        self.assertTrue(W.NOTE_UNIT_WORDS.isdisjoint(W.UNIT_WORDS_WIDENED))
        self.assertTrue(W.NOTE_UNIT_WORDS.isdisjoint(W.UNIT_WORDS))
        self.assertEqual(W.OTHER_UNIT_WORDS - W.NOTE_UNIT_WORDS - set(W.UNIT_WORDS_WIDENED), {"fluid", "fl"})
        self.assertEqual(sorted(W.OWN_UNITS_AS_NOTES), ["bunch", "can", "clove", "package", "pinch", "saltspoon", "slice",
                                                        "square", "teacup"])


class C_NoteLinesReader(unittest.TestCase):
    def test_lines_with_no_exact_amount_are_present_no_amount(self):
        with stage_1c(True):
            for text, name, why in (("salt", "salt", "NO_AMOUNT"), ("Pepper to taste", "pepper", "NO_AMOUNT"),
                                    ("butter for frying", "butter", "NO_AMOUNT"), ("sugar if desired", "sugar", "NO_AMOUNT"),
                                    ("2 sticks butter", "butter", "UNIT_NO_EXACT_SIZE:sticks"),
                                    ("1 dash salt", "salt", "UNIT_NO_EXACT_SIZE:dash"),
                                    ("a handful of raisins", "raisin", "UNIT_NO_EXACT_SIZE:handful"),
                                    ("a pinch of salt", "salt", "UNIT_NO_EXACT_SIZE:pinch"),
                                    ("1 can tomatoes", "tomato", "UNIT_NO_EXACT_SIZE:can"),
                                    ("2 cloves garlic", "garlic", "UNIT_NO_EXACT_SIZE:clove")):
                lines, ask = WT.parse_lines(text)
                self.assertIsNone(ask, text)
                self.assertEqual(len(lines), 1, text)
                x = lines[0]
                self.assertEqual((x["name"], x["amount"], x["unit"], x["note"], x["note_why"]), (name, None, "", True, why), text)
            got, ask = names("salt and pepper to taste")
            self.assertEqual((got, ask), ([("salt", None, "", True), ("pepper", None, "", True)], None))
            got, ask = names("2 cups flour, sifted")                 # a note on an amount line stays a note
            self.assertEqual((got, ask), ([("flour", Fraction(2), "cup", False)], None))
            got, ask = names("3 cloves")                              # v3: the unit word alone is the name, a count
            self.assertEqual((got, ask), ([("clove", Fraction(3), "", False)], None))
            got, ask = names("2 sticks")
            self.assertEqual((got, ask), ([("stick", Fraction(2), "", False)], None))

    def test_what_stays_a_question(self):
        with stage_1c(True):
            for text, code in (("no water", "NO_AMOUNT"), ("For the sauce:", "NO_AMOUNT"), ("sifted", "NO_AMOUNT"),
                               ("2 to 3 cups flour", "AMOUNT_IS_A_RANGE"), ("about 2 cups flour", "AMOUNT_APPROXIMATE"),
                               ("1/2 cup plus 1 tablespoon water", "AMOUNT_HAS_TWO_PARTS"), ("1 fl brandy", "UNIT_NOT_IN_TABLE"),
                               ("half as much soda", "AMOUNT_RELATIVE")):
                lines, ask = WT.parse_lines(text)
                self.assertEqual((lines, ask["code"]), ([], code), text)
            r = WT.read_wide("We have 12 cups of flour and no water.")
            self.assertEqual((r["status"], r["clarify"]["code"]), ("CLARIFY", "NO_AMOUNT"))
            r = WT.read_wide("We have 2 or 3 cups flour.")
            self.assertEqual((r["status"], r["clarify"]["code"]), ("CLARIFY", "AMOUNT_IS_A_RANGE"))

    def test_widened_units_read(self):
        with stage_1c(True):
            got, ask = names("1 liter milk, 2 fl oz brandy, 4 fluid ounces cream, 1 dozen eggs, 1/2 gallon water and 2 dl stock")
            self.assertIsNone(ask)
            self.assertEqual(got, [("milk", Fraction(1), "liter", False), ("brandy", Fraction(2), "fluid ounce", False),
                                   ("cream", Fraction(4), "fluid ounce", False), ("egg", Fraction(1), "dozen", False),
                                   ("water", Fraction(1, 2), "gallon", False), ("stock", Fraction(2), "deciliter", False)])
            r = WT.read_wide("We made 1 cake from 2 cups flour, 1 dozen eggs, a pinch of salt and 1 liter milk and ran out of flour.")
            self.assertEqual(r["status"], "WITNESS")
            self.assertEqual(r["witness"]["stock"], {"flour": (Fraction(2), "cup"), "egg": (Fraction(1), "dozen"),
                                                     "salt": (None, ""), "milk": (Fraction(1), "liter")})
            r = WT.read_wide("We have salt, pepper and 2 cups flour.")
            self.assertEqual((r["status"], r["stock"]), ("STOCK", {"salt": (None, ""), "pepper": (None, ""), "flour": (Fraction(2), "cup")}))
            self.assertEqual(WT.public(r)["stock"]["salt"], [None, ""])

    def test_note_name_rules(self):
        self.assertEqual(WT.note_name("Pepper, to taste"), "pepper")
        self.assertEqual(WT.note_name("butter for frying"), "butter")
        self.assertEqual(WT.note_name("Salt."), "salt")
        self.assertEqual(WT.note_name("fresh parsley, chopped"), "parsley")
        for bad in ("no salt", "without butter", "For the icing:", "to taste", "sifted", "and", "2 eggs", "½ lemon", ""):
            self.assertIsNone(WT.note_name(bad), bad)


class D_NoteLinesBrain(unittest.TestCase):
    STOCK = {"flour": (Fraction(2), "cup"), "egg": (Fraction(2), "dozen"), "salt": None, "milk": (Fraction(2), "liter")}

    def test_notes_are_present_never_a_requirement(self):
        with stage_1c(True):
            b = W.WideRecipeBook()
            rec = b.witness("cake", self.STOCK, 1, ["flour"])
            self.assertEqual((rec["admitted"], rec["reason"], rec["notes"]), (True, W.ADMITTED, ["salt"]))
            self.assertEqual(b.support_of("cake"), ["flour", "egg", "milk"])         # notes are not on the support
            self.assertEqual(b.notes_of("cake"), ["salt"])
            self.assertEqual(b.note_names(), ["salt"])
            self.assertNotIn("salt", b.ingredients)
            self.assertEqual(b.requirements("cake"), {"flour": "96", "egg": None, "milk": None})
            self.assertEqual(b.learned_state()["recipes"]["cake"]["notes"], ["salt"])
            self.assertEqual(b.witness_log[0]["stock_before"]["salt"], [None, ""])
            # every number in the learned state is still a coefficient: a note adds no number
            nums = W.numbers_in_learned_state(b)
            self.assertEqual(nums, [Fraction(96)])
            self.assertEqual(set(vars(b)), W.BRAIN_ATTRIBUTES)
            buf = io.StringIO()
            with redirect_stdout(buf):
                table = W.print_parameter_table(b)
            self.assertEqual([r["class"] for r in table], ["requirement coefficient a[recipe][ingredient]", "unit factor"])
            self.assertIn("WIDE_UNITS_NOTE is ON", buf.getvalue())
            # the two other lessons, then an answer: salt never limits and is never counted
            self.assertTrue(b.witness("cake", {"flour": (3, "cup"), "egg": (1, "dozen"), "salt": None, "milk": (2, "liter")}, 1, ["egg"])["admitted"])
            self.assertTrue(b.witness("cake", {"flour": (3, "cup"), "egg": (2, "dozen"), "milk": (1, "liter")}, 1, ["milk"])["admitted"])
            ev = b.evaluate("cake", {"flour": (Fraction(4), "cup"), "egg": 36, "milk": (Fraction(10), "liter"), "salt": None})
            self.assertEqual((ev["status"], ev["yield"], ev["limiting_reagent"], ev["notes"]), (W.EVALUATED, "2", "flour", ["salt"]))
            ev2 = b.evaluate("cake", {"flour": (Fraction(4), "cup"), "egg": 36, "milk": (Fraction(10), "liter")})
            self.assertEqual((ev2["yield"], ev2["limiting_reagent"]), ("2", "flour"))    # a note absent changes nothing
            ev3 = b.evaluate("cake", {"flour": None, "egg": 36, "milk": (Fraction(10), "liter")})
            self.assertEqual((ev3["status"], ev3["gate"], ev3["absent"]), (W.UNDETERMINED, "G1", ["flour"]))  # no amount = unknown
            self.assertEqual(WT.say_wide(ev), "With what's on hand we can make 2 cake. Flour runs out first, so it sets the "
                                              "limit. Salt goes in too, with no set amount, so I didn't count it toward the limit.")
            # replay with notes gives the same digest
            self.assertEqual(b.replay(b.witness_log)["learned_digest"], b.learned_digest())

    def test_a_note_cannot_be_what_ran_out(self):
        with stage_1c(True):
            b = W.WideRecipeBook()
            rec = b.witness("cake", self.STOCK, 1, ["salt"])
            self.assertEqual((rec["admitted"], rec["reason"], rec["detail"]), (False, W.REFUSED_RAN_OUT_IS_A_NOTE, {"ingredient": "salt"}))
            self.assertEqual(b.recipes, {})
            self.assertIn("no exact amount", WT.say_refused(rec, b))

    def test_notes_count_toward_the_ingredient_limit_and_add_up_across_batches(self):
        with stage_1c(True):
            b = W.WideRecipeBook()
            many = {f"spice {c}": None for c in "abcdefghij"}
            many["flour"] = (Fraction(1), "cup")
            rec = b.witness("curry", many, 1, ["flour"])
            self.assertEqual(rec["reason"], "REFUSED_TOO_MANY_INGREDIENTS")
            self.assertTrue(b.witness("cake", {"flour": (2, "cup"), "salt": None}, 1, ["flour"])["admitted"])
            self.assertTrue(b.witness("cake", {"flour": (2, "cup"), "salt": None, "vanilla": None}, 1, ["flour"])["admitted"])
            self.assertEqual(b.notes_of("cake"), ["salt", "vanilla"])
            # an exact amount for a noted ingredient later is a different recipe shape: the brain asks, never merges
            rec = b.witness("cake", {"flour": (2, "cup"), "salt": (1, "teaspoon")}, 1, ["flour"])
            self.assertEqual((rec["reason"], rec["detail"]["extra"]), ("REFUSED_SUPPORT_MISMATCH", ["salt"]))


class E_LiveLoop(unittest.TestCase):
    def test_conversation_with_notes(self):
        import helm_end_to_end_loop as E
        with stage_1c(True):
            loop = E.HELMEndToEndLoop()
            r = loop.process_turn("We made 1 cake from 2 cups flour, 2 dozen eggs and a pinch of salt and ran out of flour.", tick=1)
            self.assertEqual((r["loop_status"], r["path"]), ("WITNESS_ADMITTED", "wide"))
            self.assertEqual(r["response"], "Got it: one cake needs 2 cups of flour. Salt goes in too, with no set amount, so I "
                                            "didn't count it toward the limit. I still need one batch where egg ran out first.")
            r = loop.process_turn("We made 1 cake from 3 cups flour, 1 dozen eggs and a pinch of salt and ran out of eggs.", tick=2)
            self.assertEqual(r["loop_status"], "WITNESS_ADMITTED")
            r = loop.process_turn("We have 4 cups flour and 36 eggs.", tick=3)   # the licensed path records; wide reads too
            self.assertIn(r["loop_status"], ("INVENTORY_RECORDED", "STOCK_RECORDED"))
            r = loop.process_turn("We have salt.", tick=4)                   # a note ingredient the wide book knows
            self.assertEqual((r["loop_status"], r["path"]), ("STOCK_RECORDED", "wide"))
            self.assertEqual(r["response"], "Noted: we have salt (no amount given).")
            r = loop.process_turn("How many cakes can we make?", tick=5)
            self.assertEqual((r["loop_status"], r["limiting_reagent"]), ("SUCCESS_EVALUATED", "flour"))
            self.assertEqual(r["output"], "2")
            self.assertIn("Salt goes in too, with no set amount", r["response"])
            self.assertNotEqual(r["limiting_reagent"], "salt")
            r = loop.process_turn("We made 1 cake from 2 cups flour, 1 dozen eggs and a pinch of salt and ran out of salt.", tick=6)
            self.assertEqual(r["loop_status"], "TEACH_REFUSED_REFUSED_RAN_OUT_IS_A_NOTE")
            self.assertEqual(loop.wide_book.learned_state()["recipes"]["cake"]["notes"], ["salt"])
            print("\n[stage 1c] live loop with notes:", json.dumps([t["station"] for t in loop.trace if t["tick"] == 5]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
