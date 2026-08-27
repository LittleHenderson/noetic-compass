"""Baselines B0-B2 — the controls that make a green stage mean something."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from baselines import (  # noqa: E402
    Syllogism,
    b0_association_only,
    b0_full_reasoner,
    b1_no_bias,
    b2_random_bias,
    reference_conclude_rate,
)

TRANSITIVE = Syllogism(premises=(("A", "B"), ("B", "C")), query=("A", "C"))
ONE_HOP = Syllogism(premises=(("A", "B"), ("B", "C")), query=("A", "B"))
NOT_ENTAILED = Syllogism(premises=(("A", "B"), ("C", "D")), query=("A", "D"))


class B0AssociationIsNotDeduction(unittest.TestCase):
    def test_the_transitive_task_is_genuinely_entailed(self) -> None:
        self.assertTrue(TRANSITIVE.entailed(), "the task must have a right answer")

    def test_association_only_fails_the_transitive_task(self) -> None:
        """If B0 passed, the task would not be testing deduction at all."""
        self.assertFalse(b0_association_only(TRANSITIVE))

    def test_the_full_reasoner_passes_it(self) -> None:
        self.assertTrue(b0_full_reasoner(TRANSITIVE))

    def test_association_only_still_handles_one_hop(self) -> None:
        """B0 is a control, not a strawman — it must succeed where ^8 suffices."""
        self.assertTrue(b0_association_only(ONE_HOP))

    def test_neither_asserts_an_unentailed_conclusion(self) -> None:
        self.assertFalse(b0_association_only(NOT_ENTAILED))
        self.assertFalse(b0_full_reasoner(NOT_ENTAILED))

    def test_the_control_separates_the_two(self) -> None:
        """The whole point: same task, different answer."""
        self.assertNotEqual(
            b0_association_only(TRANSITIVE), b0_full_reasoner(TRANSITIVE)
        )


class B1NoBiasAblation(unittest.TestCase):
    def test_removing_the_bias_is_a_construction_error(self) -> None:
        result = b1_no_bias()
        self.assertFalse(result.concluded)
        self.assertIn("E-CJT-001", result.detail)


class B2RandomBiasControl(unittest.TestCase):
    def test_the_structured_board_concludes(self) -> None:
        self.assertEqual(reference_conclude_rate(), 1.0)

    def test_random_bias_concludes_strictly_less_often(self) -> None:
        """If randomness matched the structured board, topology earns nothing."""
        result = b2_random_bias(trials=200)
        rate = float(result.detail.split()[-1].rstrip("%")) / 100.0
        self.assertLess(
            rate, reference_conclude_rate(),
            "a randomly-biased board must not conclude as often as a sound one",
        )

    def test_random_bias_is_deterministic_under_a_fixed_seed(self) -> None:
        self.assertEqual(b2_random_bias(trials=50).detail, b2_random_bias(trials=50).detail)


if __name__ == "__main__":
    unittest.main()
