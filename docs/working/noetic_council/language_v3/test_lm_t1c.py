"""LM-T1c unit tests (builder fixtures only)."""
import unittest

import cce_v01c as c
import cas_ast as ca


class Dotted(unittest.TestCase):
    def test_no_reversal(self):
        x = c.parse("The Noetic fractal is 5.1.3.")
        self.assertEqual([t["noetic"] for t in c.canonical(x)["fractal"]], [5, 1, 3])
        self.assertEqual(ca.fractal_cas(c.canonical(x)["fractal"]), "Φ⟨5:1:3⟩")

    def test_words_equal_digits(self):
        a = c.parse("The Noetic fractal is 5.1.3.")
        w = c.parse("The Noetic fractal is Female within Mind within Negative.")
        self.assertEqual(c.normalize(a), c.normalize(w))

    def test_notation_kept_and_round_trips(self):
        a = c.parse("The Noetic fractal is 8.8.9.")
        p = c.parse("The fractal sequence is Above/Cause : Above/Cause : Below/Effect.")
        self.assertEqual(c.canonical(a)["fractal_notation"], "DOTTED")
        self.assertEqual(c.canonical(p)["fractal_notation"], "PHI")
        self.assertNotEqual(c.normalize(a), c.normalize(p))
        self.assertTrue(c.round_trip(a)["ok"] and c.round_trip(p)["ok"])
        self.assertIn("8.8.9", c.render(a))

    def test_no_flag(self):
        self.assertNotIn("flags", c.canonical(c.parse("The Noetic fractal is 2.7.")))

    def test_refusals(self):
        for text, code in (("The Noetic fractal is 5.1:3.", "NOT_CCE"), ("The Noetic fractal is 1.2.3.4.5.6.", "NEST_TOO_DEEP")):
            with self.assertRaises(c.Refusal) as e:
                c.parse(text)
            self.assertEqual(e.exception.code, code)


if __name__ == "__main__":
    unittest.main()
