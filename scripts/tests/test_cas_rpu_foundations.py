"""The Foundation Engine Bank — 28 sub-Foundations, recipes, bottlenecks.

What these tests hold down: the canonical `F_k|R` notation rather than a third
spelling, the two normalisations (independent `g`, per-Drive `q`), and the one
job the bank exists to do — computing which prerequisite is limiting.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))

from foundations import (  # noqa: E402
    INVERSION_PAIRS,
    REASONING_RECIPES,
    SUBFOUNDATIONS,
    Consequence,
    Drive,
    FoundationError,
    FoundationProfile,
    Recipe,
    Register,
    focused_profile,
    parse_subfoundation,
    subfoundation,
    uniform_profile,
)


class NotationTests(unittest.TestCase):
    """`F5|A`, the spelling the compiler already parses."""

    def test_there_are_twenty_eight_sub_foundations(self):
        self.assertEqual(len(SUBFOUNDATIONS), 28)
        self.assertEqual(len(set(SUBFOUNDATIONS)), 28)

    def test_the_four_worlds_are_the_four_registers(self):
        self.assertEqual(
            [r.value for r in Register], ["T", "A", "f", "E"]
        )

    def test_references_round_trip(self):
        for drive in Drive:
            for register in Register:
                ref = subfoundation(drive, register)
                self.assertEqual(parse_subfoundation(ref), (drive, register))

    def test_the_register_suffix_is_case_sensitive(self):
        """`|f` Affective and `|E` Embodied are distinct; case carries meaning."""
        self.assertEqual(parse_subfoundation("F5|f")[1], Register.f)
        self.assertEqual(parse_subfoundation("F5|E")[1], Register.E)
        with self.assertRaises(FoundationError):
            parse_subfoundation("F5|e")

    def test_a_malformed_reference_is_refused(self):
        for bad in ("F8|A", "F1|Z", "TF5b", "F5", "", "F5|"):
            with self.assertRaises(FoundationError) as ctx:
                parse_subfoundation(bad)
            self.assertEqual(ctx.exception.code, "E-FDN-001")

    def test_the_superseded_tf_spelling_is_not_accepted(self):
        """A third spelling for one position is the error being avoided."""
        for bad in ("TF5b", "TF1a", "DF2"):
            with self.assertRaises(FoundationError):
                parse_subfoundation(bad)


class ProfileTests(unittest.TestCase):
    def test_all_seven_drives_may_run_hot_at_once(self):
        """`g` is independent across Drives -- there is no shared pool."""
        profile = uniform_profile(**{d.value: 1.0 for d in Drive})
        self.assertEqual(sum(profile.g.values()), 7.0)
        self.assertAlmostEqual(sum(profile.channels().values()), 7.0)

    def test_the_four_registers_inside_one_drive_must_sum_to_one(self):
        q = {d: {r: 0.25 for r in Register} for d in Drive}
        q[Drive.F1] = {r: 0.5 for r in Register}
        with self.assertRaises(FoundationError) as ctx:
            FoundationProfile(g={d: 0.5 for d in Drive}, q=q)
        self.assertEqual(ctx.exception.code, "E-FDN-006")

    def test_activation_is_the_product_of_drive_and_register_share(self):
        profile = focused_profile("F5|A", 0.8, spread=0.1)
        self.assertAlmostEqual(profile.activation(Drive.F5, Register.A), 0.8 * 0.7)
        self.assertAlmostEqual(profile.activation(Drive.F5, Register.T), 0.8 * 0.1)
        self.assertEqual(profile.dominant(), "F5|A")

    def test_a_drive_level_outside_the_unit_interval_is_refused(self):
        with self.assertRaises(FoundationError) as ctx:
            uniform_profile(F1=1.5)
        self.assertEqual(ctx.exception.code, "E-FDN-003")

    def test_inversion_imbalance_reports_the_three_pairs_and_omits_f4(self):
        profile = focused_profile("F2|A", 0.9)
        imbalance = profile.inversion_imbalance()
        self.assertEqual(len(imbalance), len(INVERSION_PAIRS))
        self.assertAlmostEqual(imbalance["F2<->F6"], 0.9)
        self.assertNotIn("F4", "".join(imbalance))


class RecipeTests(unittest.TestCase):
    """The coefficients are what make a bottleneck computable."""

    def setUp(self):
        self.recipe = Recipe("t", {"F2|A": 1.0, "F6|A": 0.2, "F7|A": 0.3})

    def test_a_recipe_without_prerequisites_is_refused(self):
        with self.assertRaises(FoundationError) as ctx:
            Recipe("empty", {})
        self.assertEqual(ctx.exception.code, "E-FDN-009")

    def test_a_non_positive_coefficient_is_refused(self):
        for weight in (0.0, -1.0):
            with self.assertRaises(FoundationError) as ctx:
                Recipe("t", {"F2|A": weight})
            self.assertEqual(ctx.exception.code, "E-FDN-010")

    def test_theoretical_yield_is_the_minimum_ratio(self):
        profile = uniform_profile(F2=0.8, F6=0.8, F7=0.8)  # 0.2 in every lane
        # ratios: 0.2/1.0, 0.2/0.2, 0.2/0.3 -> min is 0.2
        self.assertAlmostEqual(self.recipe.theoretical_yield(profile), 0.2)

    def test_the_limiting_reagent_is_the_prerequisite_at_that_minimum(self):
        profile = uniform_profile(F2=0.8, F6=0.8, F7=0.8)
        self.assertEqual(self.recipe.limiting_reagent(profile), "F2|A")

    def test_a_single_minded_ambition_bottlenecks_on_what_it_neglected(self):
        """Wanting one thing intensely does not supply the rest of the recipe.

        This is the bank earning its place: it says a purely analytical-Wisdom
        ambition cannot produce a deduction, because the outcome also needs
        Structure and Purpose in that register."""
        profile = focused_profile("F2|A", 1.0, spread=0.0)
        recipe = REASONING_RECIPES["deduction"]
        self.assertEqual(recipe.theoretical_yield(profile), 0.0)
        self.assertIn(recipe.limiting_reagent(profile), ("F6|A", "F7|A"))

    def test_a_balanced_ambition_yields_more_than_a_spiked_one(self):
        spiked = focused_profile("F2|A", 1.0, spread=0.0)
        balanced = uniform_profile(F2=0.9, F6=0.9, F7=0.9)
        recipe = REASONING_RECIPES["deduction"]
        self.assertGreater(
            recipe.theoretical_yield(balanced), recipe.theoretical_yield(spiked)
        )

    def test_excess_capacity_is_zero_at_the_bottleneck(self):
        profile = uniform_profile(F2=0.8, F6=0.8, F7=0.8)
        excess = self.recipe.excess_capacity(profile)
        limiting = self.recipe.limiting_reagent(profile)
        self.assertAlmostEqual(excess[limiting], 0.0)
        self.assertGreater(excess["F6|A"], 0.0)

    def test_efficiency_is_bounded_and_safe_at_zero_yield(self):
        self.assertEqual(Recipe.efficiency(0.5, 1.0), 0.5)
        self.assertEqual(Recipe.efficiency(2.0, 1.0), 1.0)
        self.assertEqual(Recipe.efficiency(1.0, 0.0), 0.0)

    def test_the_recipe_renders_in_v76_notation(self):
        self.assertIn("Theta(t) =", str(self.recipe))
        self.assertIn("-> t", str(self.recipe))

    def test_every_shipped_recipe_is_well_formed(self):
        for name, recipe in REASONING_RECIPES.items():
            self.assertEqual(recipe.target, name)
            for ref in recipe.coefficients:
                parse_subfoundation(ref)


class ConsequenceTests(unittest.TestCase):
    """A plan's effect is 28 lanes, not one number."""

    def test_a_plan_can_advance_one_drive_and_damage_another(self):
        consequence = Consequence(
            "launch", {"F5|A": 0.8, "F6|E": 0.4, "F4|f": -0.5, "F7|A": -0.3}
        )
        self.assertEqual(consequence.advanced(), ("F5|A", "F6|E"))
        self.assertEqual(consequence.damaged(), ("F4|f", "F7|A"))

    def test_scalarising_requires_a_profile_and_two_profiles_disagree(self):
        """The weighting is the ambition, so ranking is profile-relative.

        This is the property that stops 28 lanes collapsing into a universal
        'goodness'. The same candidate serves one set of ambitions and
        disserves another, and the number says which."""
        consequence = Consequence("launch", {"F5|A": 1.0, "F4|f": -1.0})
        agency = focused_profile("F5|A", 1.0, spread=0.0)
        connection = focused_profile("F4|f", 1.0, spread=0.0)
        self.assertGreater(consequence.weighted(agency), 0.0)
        self.assertLess(consequence.weighted(connection), 0.0)

    def test_a_consequence_on_an_unknown_channel_is_refused(self):
        with self.assertRaises(FoundationError) as ctx:
            Consequence("bad", {"F9|Z": 1.0})
        self.assertEqual(ctx.exception.code, "E-FDN-001")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
