"""LM-T1v3 tests: the p/q number form (the owner's Q13 ruling) and the REFUSE and CLOSE turns.

New behaviour only. Nothing in test_lm_t1.py, test_lm_t1b.py or test_lm_t1c.py was weakened, changed or deleted;
those three files are byte-identical to the base build, and this file is the whole of the new testing.

Run from this folder, with PYTHONPATH as recorded in PROVENANCE.md:

    C:\\Python314\\python.exe -X utf8 -B test_lm_t1v3.py
"""
from fractions import Fraction
import random
import unittest

import cce
import coverage


def content(**kw):
    c = cce.empty_content()
    c.update(kw)
    return c


FRAME = {"noetic": 2, "domain": "P", "register": None, "drive": None, "polarity": "ASSERTED",
         "slots": {"M": "I", "I": '"x"'}}


def recipe(coef):
    """One recipe whose only term has the coefficient given, so the number is the only thing under test."""
    return content(recipe={"omega": "Ω_t", "leakage": [], "catalysts": [], "inhibitors": [],
                           "terms": [{"kind": "state", "noetic": 9, "domain": "O", "register": None,
                                      "drive": None, "coefficient": coef}]})


class FractionForm(unittest.TestCase):
    """A fraction is written p/q, kept exact, and never turned into a decimal it does not have."""

    def test_one_third_round_trips_exactly(self):
        c = recipe("1/3")
        receipt = cce.round_trip(c)
        self.assertTrue(receipt["ok"], receipt)
        self.assertIn("1/3", receipt["sentence"])
        back = cce.parse(receipt["sentence"])
        self.assertEqual(cce.fraction_value(back["recipe"]["terms"][0]["coefficient"]), Fraction(1, 3))
        self.assertEqual(cce.normalize(back), cce.normalize(c))

    def test_one_third_round_trips_in_every_number_slot(self):
        # a recipe coefficient, a stock amount, and a frame degree
        stock = content(stocks=[{"amount": "1/3", "ref": {"outcome": "Ω_flour"}}])
        self.assertTrue(cce.round_trip(stock)["ok"])
        degree = content(terms=[{"noetic": 4, "domain": "E", "register": None, "drive": None,
                                 "polarity": "ASSERTED", "slots": {"I": '"the speech"', "M": "I", "D": "1/3"}}])
        self.assertTrue(cce.round_trip(degree)["ok"])
        self.assertEqual(cce.parse(cce.render(degree))["terms"][0]["slots"]["D"], "1/3")

    def test_non_dyadic_fraction_is_refused_not_decimalised(self):
        for written in ("1/3", "3/7", "22/7", "1/6", "5/9"):
            with self.assertRaises(cce.Refusal, msg=written) as e:
                cce.decimal_text(written)
            self.assertEqual(e.exception.code, "LOSSY_CONVERSION_REFUSED", written)
            self.assertIn("/", cce.num(written), written)

    def test_quarter_and_its_decimal_are_one_quantity(self):
        self.assertEqual(cce.num("1/4"), "0.25")
        self.assertEqual(cce.num("0.25"), "0.25")
        self.assertEqual(cce.fraction_value("1/4"), cce.fraction_value("0.25"))
        a = cce.parse("To make Ω_t, use 1/4 of Negative, principled.")
        b = cce.parse("To make Ω_t, use 0.25 of Negative, principled.")
        self.assertEqual(cce.normalize(a), cce.normalize(b))
        self.assertTrue(cce.round_trip(a)["ok"])
        self.assertTrue(cce.round_trip(b)["ok"])
        self.assertEqual(cce.num("1/4"), cce.num("2/8"))

    def test_half_three_ways_is_one_quantity(self):
        forms = ('"x" resonates with me to degree 1/2.',
                 '"x" resonates with me to degree 0.5.',
                 '"x" resonates with me to degree half.')
        parsed = [cce.parse(t) for t in forms]
        for c in parsed[1:]:
            self.assertEqual(cce.normalize(parsed[0]), cce.normalize(c))
        self.assertEqual(parsed[0]["terms"][0]["slots"]["D"], "0.5")

    def test_a_repetend_is_never_written_as_decimals(self):
        for written in ("1/3", "2/3", "1/7", "22/7"):
            text = cce.num(written)
            self.assertNotIn(".", text, written)
            self.assertTrue(cce.round_trip(recipe(written))["ok"], written)
        self.assertNotIn("0.333", cce.render(recipe("1/3")))
        self.assertNotIn("0.333", cce.num("1/3"))

    def test_fraction_survives_wording_draws(self):
        rng = random.Random(7)
        for _ in range(12):
            r = cce.round_trip(recipe("1/3"), rng)
            self.assertTrue(r["ok"], r)
            self.assertIn("1/3", r["sentence"])

    def test_a_fraction_that_is_not_a_number_is_refused(self):
        for written in ("1/0", "1/", "/3", "1//3", "one/half", ""):
            with self.assertRaises(cce.Refusal, msg=written) as e:
                cce.fraction_value(written)
            self.assertEqual(e.exception.code, "NOT_CCE", written)
        for text in ("To make Ω_t, use 1/0 of Negative, principled.",
                     "To make Ω_t, use -1/3 of Negative, principled.",
                     "To make Ω_t, use 1/03 of Negative, principled."):
            with self.assertRaises(cce.Refusal, msg=text) as e:
                cce.parse(text)
            self.assertEqual(e.exception.code, "NOT_CCE", text)

    def test_zero_fraction_coefficient_is_refused(self):
        with self.assertRaises(cce.Refusal) as e:
            cce.parse("To make Ω_t, use 0/1 of Negative, principled.")
        self.assertEqual(e.exception.code, "NOT_CCE")

    def test_the_number_words_did_not_grow(self):
        # Q8 stays as it was: digits, one..ten and half. No new number word was invented for a fraction.
        self.assertEqual(sorted(cce.NUMBER_WORDS),
                         sorted(["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                                 "half"]))


class EachTurnHasItsOwnSentence(unittest.TestCase):
    """Six turn types, six sentences, six different readings. None collapses into another."""

    CASES = (
        ("ANSWER", 'I have an affinity for "x".'),
        ("ACK", "New subject: Ω_x."),
        ("CLARIFY", "I need the stock of Ω_leaves for Ω_tea. What is it?"),
        ("REFUSE_CLAIM", "I cannot support that: no evidence."),
        ("REFUSE", "I will not do that: boundary violation."),
        ("CLOSE", "That closes the turn."),
    )

    def test_six_turns_read_as_six_different_turns(self):
        seen = {}
        for turn, text in self.CASES:
            c = cce.parse(text)
            self.assertEqual(c["turn"], turn, text)
            said = cce.render(c)
            self.assertNotIn(said, seen, text)
            seen[said] = turn
            self.assertTrue(cce.round_trip(c)["ok"], text)
        self.assertEqual(len(set(seen.values())), 6)

    def test_a_sentence_for_a_formless_turn_is_refused(self):
        for text in ('I would suggest "x".', "Shall we plan?", "Let us open Ω_x.", "I am sorry about that."):
            with self.assertRaises(cce.Refusal, msg=text):
                cce.parse(text)


class RefuseTurn(unittest.TestCase):
    """REFUSE: the boundary was not crossed. It needs its boundary words and says nothing else."""

    def test_refuse_parses_from_its_own_sentence(self):
        c = cce.parse("I will not do that: boundary violation.")
        self.assertEqual((c["turn"], c["reason"]), ("REFUSE", "boundary violation"))
        self.assertEqual(cce.render(c), "I will not do that: boundary violation.")
        self.assertTrue(cce.round_trip(c)["ok"])

    def test_refuse_is_not_a_claim_refusal(self):
        claim = cce.parse("I cannot support that: no evidence.")
        refuse = cce.parse("I will not do that: boundary violation.")
        self.assertEqual(claim["turn"], "REFUSE_CLAIM")
        self.assertEqual(refuse["turn"], "REFUSE")
        self.assertNotEqual(cce.render(claim), cce.render(refuse))
        self.assertEqual(cce.parse(cce.render(claim))["turn"], "REFUSE_CLAIM")
        self.assertEqual(cce.parse(cce.render(refuse))["turn"], "REFUSE")
        self.assertNotEqual(cce.normalize(claim), cce.normalize(refuse))

    def test_refuse_keeps_the_evidence_prefix(self):
        text = "I checked: I will not do that: boundary violation."
        c = cce.parse(text)
        self.assertEqual((c["turn"], c["evidence"], c["reason"]), ("REFUSE", "CHECKED", "boundary violation"))
        self.assertEqual(cce.render(c), text)

    def test_refuse_carries_nothing_it_cannot_say(self):
        with self.assertRaises(ValueError):
            cce.render(content(turn="REFUSE", reason="boundary violation", terms=[FRAME]))
        with self.assertRaises(ValueError):
            cce.render(content(turn="REFUSE", reason="boundary violation", topic="Ω_x"))
        with self.assertRaises(ValueError):
            cce.render(content(turn="REFUSE"))
        self.assertFalse(cce.round_trip(content(turn="REFUSE", terms=[FRAME]))["ok"])


class CloseTurn(unittest.TestCase):
    """CLOSE: the closing turn. It names its subject if it has one, and carries nothing else."""

    def test_close_parses_from_its_own_sentence(self):
        c = cce.parse("That closes the turn.")
        self.assertEqual(c["turn"], "CLOSE")
        self.assertEqual(cce.render(c), "That closes the turn.")
        self.assertTrue(cce.round_trip(c)["ok"])

    def test_close_can_name_its_subject(self):
        c = cce.parse("That closes Ω_tea.")
        self.assertEqual((c["turn"], c["topic"]), ("CLOSE", "Ω_tea"))
        self.assertEqual(cce.render(c), "That closes Ω_tea.")
        self.assertTrue(cce.round_trip(c)["ok"])

    def test_close_keeps_the_evidence_prefix(self):
        text = "You said: That closes the turn."
        c = cce.parse(text)
        self.assertEqual((c["turn"], c["evidence"]), ("CLOSE", "USER_SAID"))
        self.assertEqual(cce.render(c), text)

    def test_close_is_not_an_answer_and_drops_nothing(self):
        answer = cce.parse('I have an affinity for "x".')
        self.assertNotEqual(cce.render(content(turn="CLOSE")), cce.render(answer))
        self.assertEqual(cce.parse(cce.render(content(turn="CLOSE")))["turn"], "CLOSE")
        with self.assertRaises(ValueError):
            cce.render(content(turn="CLOSE", terms=[FRAME]))
        with self.assertRaises(ValueError):
            cce.render(content(turn="CLOSE", reason="no evidence"))
        self.assertFalse(cce.round_trip(content(turn="CLOSE", terms=[FRAME]))["ok"])


class NoFormStaysNoForm(unittest.TestCase):
    """Every turn the grammar has no form for still raises. Adding two forms added exactly two."""

    def test_turns_without_a_form_raise(self):
        for turn in ("OPEN", "MIRROR", "EMPATHIZE", "PLAN", "REPAIR", "PROPOSE"):
            with self.assertRaises(ValueError, msg=turn) as e:
                cce.render(content(turn=turn))
            self.assertIn("no CCE v0.1 form", str(e.exception))


class TurnLedger(unittest.TestCase):
    """The ledger the task is judged on, read from the same code that produced the base numbers."""

    def test_u_turn_is_fully_covered(self):
        u = coverage.side_universes()["U-TURN"]
        self.assertEqual(u["state_counts"]["COVERED"], 6)
        self.assertEqual(u["state_counts"]["LACUNA"], 0)
        self.assertEqual(u["gap_set"], [])

    def test_the_other_side_universes_did_not_move(self):
        side = coverage.side_universes()
        self.assertEqual(side["U-DRIVE"]["state_counts"]["COVERED"], 8)
        self.assertEqual(side["U-RECIPE"]["state_counts"]["COVERED"], 7)
        self.assertEqual(side["U-CATEGORY"]["state_counts"]["COVERED"], 14)
        self.assertEqual(side["U-CATEGORY"]["state_counts"]["LACUNA"], 7)

    def test_main_ledger_is_unchanged(self):
        read, receipts = coverage.run_main()
        rows = read["rows"]
        self.assertEqual(read["n_eligible"], 2600)
        self.assertEqual(read["state_counts"]["COVERED"], 2600)
        self.assertEqual(sum(r["covered_without_charge"] for r in rows), 0)
        self.assertTrue(all(r["receipt_id"] for r in rows))
        self.assertEqual(len(receipts), 2600)


class NothingElseMoved(unittest.TestCase):
    """The base's own numbers, asserted where they can be asserted cheaply."""

    def test_round_trip_fixtures_still_exact(self):
        for t in ("I have an affinity for \"the offer\", evaluative, affective register, for Connection.",
                  "\"the song\" triggers \"the summer\" to come to me, operational, for Purpose."):
            c = cce.parse(t)
            self.assertEqual(cce.render(c), t)
            self.assertTrue(cce.round_trip(c)["ok"])

    def test_decimal_text_agrees_with_num_on_terminating_values(self):
        for written in ("2", "0.5", "0.25", "1.25", "10", "0.0625", "2.0", "half", "1/4", "3/8", "7/20"):
            self.assertEqual(cce.decimal_text(written), cce.num(written), written)


if __name__ == "__main__":
    unittest.main()
