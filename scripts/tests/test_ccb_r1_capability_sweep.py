"""The capability sweep — which models the pipeline can actually help.

The substantive test is `FindingTests`. It locks in the result that answers
"should we use a dumber model": **no**. A weaker reasoner gives the pipeline
*less* to work with, not more, because the wrapper cannot supply reasoning — it
can only stop a competent reasoner from bluffing.

If that ever inverts, either the pipeline changed or the simulation did, and
the recommendation in
`docs/working/ccb_r1_capability_band_2026_08_27.md` needs revisiting.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from capability_sweep import (  # noqa: E402
    Capability,
    graded_model,
    grid,
    render,
    render_grid,
    sweep,
)


class SimulatedModelTests(unittest.TestCase):
    PROMPT = (
        "AB leads to CD.\n"
        "CD leads to EF.\n"
        "Question: do the statements above guarantee that AB leads to EF?\n"
        "Answer YES or NO."
    )
    NO_ROUTE = (
        "AB leads to CD.\n"
        "Question: do the statements above guarantee that AB leads to ZZ?\n"
        "Answer YES or NO."
    )

    def test_the_same_prompt_and_seed_give_the_same_reply(self):
        cap = Capability(0.5, 0.75, 0.5)
        self.assertEqual(graded_model(cap, 7)(self.PROMPT), graded_model(cap, 7)(self.PROMPT))

    def test_a_different_seed_can_give_a_different_reply(self):
        cap = Capability(0.5, 0.75, 0.5)
        replies = {graded_model(cap, s)(self.PROMPT) for s in range(20)}
        self.assertGreater(len(replies), 1)

    def test_perfect_reasoning_always_finds_a_real_chain(self):
        model = graded_model(Capability(1.0, 1.0, 0.0), 1)
        self.assertIn("YES", model(self.PROMPT))

    def test_no_reasoning_never_finds_a_chain(self):
        """With bluffing off too, the only honest answer left is NO."""
        model = graded_model(Capability(0.0, 0.5, 0.0), 1)
        self.assertIn("NO", model(self.PROMPT))

    def test_no_bluffing_declines_rather_than_inventing_a_link(self):
        model = graded_model(Capability(0.0, 0.5, 0.0), 1)
        self.assertNotIn("AB leads to ZZ", model(self.NO_ROUTE))

    def test_always_bluffing_invents_the_queried_link(self):
        model = graded_model(Capability(0.0, 0.5, 1.0), 1)
        self.assertIn("AB leads to ZZ", model(self.NO_ROUTE))

    def test_perfect_meta_skill_answers_the_gate_correctly(self):
        model = graded_model(Capability(0.0, 1.0, 0.0), 1)
        gate = (
            "The following list of statements is PARTIAL — facts may be missing.\n"
            "AB leads to CD.\nCD leads to EF.\n"
            "Question under consideration: does AB lead to EF?\n"
            "Reply with one word: SUFFICIENT or INSUFFICIENT."
        )
        self.assertEqual(model(gate).strip(), "SUFFICIENT")

    def test_the_ladder_maps_as_documented(self):
        weak, strong = Capability.at_level(0.0), Capability.at_level(1.0)
        self.assertEqual((weak.p_route, weak.p_meta), (0.0, 0.5))
        self.assertEqual((strong.p_route, strong.p_meta), (1.0, 1.0))
        # Bluffing declines with capability but never vanishes.
        self.assertGreater(weak.p_fabricate, strong.p_fabricate)
        self.assertGreater(strong.p_fabricate, 0.0)


class SweepShapeTests(unittest.TestCase):
    def test_one_row_per_level_with_both_margins(self):
        rows = sweep([0.0, 1.0], n=20, workers=4, seed=1)
        self.assertEqual(len(rows), 2)
        for key in ("deduction_delta", "honesty_delta", "p_route", "p_fabricate"):
            self.assertIn(key, rows[0])

    def test_the_grid_covers_every_combination(self):
        cells = grid((0.0, 1.0), (0.0, 1.0), n=20, workers=4, seed=1)
        self.assertEqual(len(cells), 4)
        self.assertEqual(len({(c["p_route"], c["p_fabricate"]) for c in cells}), 4)

    def test_both_renderers_produce_readable_output(self):
        rows = sweep([0.0, 1.0], n=20, workers=4, seed=1)
        self.assertIn("M3 bare", render(rows))
        cells = grid((0.0, 1.0), (0.0, 1.0), n=20, workers=4, seed=1)
        self.assertIn("p_fabricate", render_grid(cells, "honesty_delta", "t"))


class FindingTests(unittest.TestCase):
    """The answer to "should we test a dumber model": no."""

    N = 100
    SEED = 20260827

    @classmethod
    def setUpClass(cls):
        cls.cells = grid((0.0, 1.0), (0.0, 1.0), n=cls.N, workers=8, seed=cls.SEED)
        cls.at = {(c["p_route"], c["p_fabricate"]): c for c in cls.cells}

    def test_a_weaker_reasoner_gives_the_pipeline_less_not_more(self):
        """The headline. The wrapper cannot supply reasoning it does not have."""
        strong = self.at[(1.0, 1.0)]["deduction_delta"]
        weak = self.at[(0.0, 1.0)]["deduction_delta"]
        self.assertGreater(strong, weak)
        self.assertGreater(strong - weak, 0.20)

    def test_the_same_holds_for_honesty(self):
        self.assertGreater(
            self.at[(1.0, 1.0)]["honesty_delta"], self.at[(0.0, 1.0)]["honesty_delta"]
        )

    def test_deduction_gain_needs_bluffing_as_well_as_reasoning(self):
        """A model that reasons perfectly and never bluffs has nothing to fix."""
        self.assertLess(abs(self.at[(1.0, 0.0)]["deduction_delta"]), 0.05)
        self.assertGreater(self.at[(1.0, 1.0)]["deduction_delta"], 0.20)

    def test_reasoning_alone_carries_the_honesty_gain(self):
        """M1 is flat in bluffing once reasoning is perfect — the gate does it."""
        self.assertAlmostEqual(
            self.at[(1.0, 0.0)]["honesty_delta"],
            self.at[(1.0, 1.0)]["honesty_delta"],
            delta=0.05,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
