"""LM-T1b unit tests (builder's own fixtures only; no added hand-set item, no book example)."""
import random
import unittest

import cce_v01b as b
import cas_ast as ca


class Fractal(unittest.TestCase):
    def test_canon_and_alias_same_content(self):
        a = b.parse("The fractal sequence is Above/Cause : Above/Cause : Below/Effect.")
        c = b.parse("The nesting is Above/Cause inside Above/Cause inside Below/Effect.")
        self.assertEqual(b.normalize(a), b.normalize(c))
        self.assertEqual([t["noetic"] for t in b.canonical(a)["fractal"]], [8, 8, 9])

    def test_order_kept_exactly(self):
        a = b.parse("The fractal sequence is Male : Above/Cause.")
        c = b.parse("The fractal sequence is Above/Cause : Male.")
        self.assertNotEqual(b.normalize(a), b.normalize(c))

    def test_depth_cap_five(self):
        self.assertTrue(b.round_trip(b.parse("The fractal sequence is " + " : ".join(["Male"] * 5) + "."))["ok"])
        with self.assertRaises(b.Refusal) as e:
            b.parse("The fractal sequence is " + " : ".join(["Male"] * 6) + ".")
        self.assertEqual(e.exception.code, "NEST_TOO_DEEP")

    def test_per_term_tails_and_compiler(self):
        c = b.parse("The fractal sequence is Above/Cause, evaluative, affective register : Vibration, evaluative, affective register.")
        self.assertEqual(ca.cas_parts(c)["fractal"], "^8^E|f ∘ ^4^E|f")
        v = ca.compile_view("^8^E|f ∘ ^4^E|f")
        self.assertEqual(v["result"]["sequence"], [8, 4])
        for s in range(10):
            self.assertTrue(b.round_trip(c, random.Random(s))["ok"])

    def test_v01_int_form_equivalent(self):
        x = b.empty_content()
        x["fractal"] = [8, 9, 4]
        self.assertEqual(b.normalize(x), b.normalize(b.parse("The fractal sequence is Above/Cause : Below/Effect : Vibration.")))


class Meta(unittest.TestCase):
    def test_statements_round_trip_and_compile(self):
        texts = ["Positive is in the Noetic set {Positive, Rhythm}.",
                 "Positive principled is not in all States.",
                 "the Noetic set {Positive} is strictly within all Noetics.",
                 "all Noetics contains the Noetic set {Rhythm}.",
                 "The size of all States is 40.",
                 "Let the set named Core be the Noetic set {Positive, Rhythm}. the set named Core is within all Noetics.",
                 "all Domains is covered by: the Domain set {principled, cognitive}; the Domain set {evaluative, operational}.",
                 "The size of the pullback of (the Register set {analytical, affective}) and (all Registers) is 2."]
        for t in texts:
            c = b.parse(t)
            self.assertTrue(b.round_trip(c)["ok"], t)
            v = ca.compile_view(ca.cas_parts(c)["meta"])
            self.assertTrue(v["valid"], t)

    def test_elements_are_sets(self):
        a = b.parse("Positive is in the Noetic set {Rhythm, Positive, Positive}.")
        c = b.parse("Positive is in the Noetic set {Positive, Rhythm}.")
        self.assertEqual(b.normalize(a), b.normalize(c))

    def test_unknown_kind_refused(self):
        with self.assertRaises(b.Refusal) as e:
            b.parse("the Widget set {x} is within all Noetics.")
        self.assertEqual(e.exception.code, "NOT_CCE")


class Expr(unittest.TestCase):
    def test_same_noetic_times_refused(self):
        with self.assertRaises(b.Refusal) as e:
            b.parse("The expression is (Positive, principled) integrated with (Positive, cognitive).")
        self.assertEqual(e.exception.code, "OPERATOR_DISCIPLINE")

    def test_cas_bridge(self):
        for src in ("^6^O_{F6}|A + ^4^E_{F7}|f", "Φ⟨8:6:9⟩", "^2^C → ^3^O", "^2^P ∈ States"):
            c = ca.content_from_cas(src)
            back = b.parse(b.render(c))
            self.assertEqual(b.normalize(back), b.normalize(c))
            self.assertEqual(ca.compile_view(list(ca.cas_parts(back).values())[0]), ca.compile_view(src))

    def test_gap_is_named(self):
        with self.assertRaises(ca.FormGap):
            ca.content_from_cas("RPM(F2)")


if __name__ == "__main__":
    unittest.main()
