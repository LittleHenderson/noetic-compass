"""The board-side arm, and the control that bounds what it can be claimed to show.

Two jobs. The first is ordinary: the adapter derives what is derivable, blocks
where information is missing, and keeps identity out of the firewall path.

The second is the reason this file matters. `test_b4_trivial_solver_matches_the_board`
asserts that a ten-line breadth-first search scores exactly what CCB-R1 scores.
That is not a bug being locked in — it is the construct-validity limit being
made non-silent, so nobody reads a green Stage 5 as evidence about CAS when it
is evidence about symbolic solvers. See
`docs/working/ccb_r1_stage5_construct_validity_2026_08_27.md`.
"""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from board import (  # noqa: E402
    MAX_CHAIN,
    b4_trivial_solver,
    board_deduction,
    board_firewall_pair,
    board_honesty,
    rate_case,
    reachable,
)
from flips import flip_report  # noqa: E402
from rpm import Terminal  # noqa: E402
from runners import score_deduction, score_honesty  # noqa: E402
from tasksets import (  # noqa: E402
    Difficulty,
    generate_deduction_set,
    generate_firewall_pairs,
    generate_honesty_set,
)


class ReachabilityTests(unittest.TestCase):
    def test_a_present_chain_is_derived(self):
        result = reachable((("A", "B"), ("B", "C")), ("A", "C"))
        self.assertTrue(result.reachable)
        self.assertIs(result.terminal, Terminal.CONCLUDED)
        self.assertEqual(result.path, ("A", "B", "C"))

    def test_a_missing_link_blocks_on_wisdom(self):
        """NEEDS_INFORMATION falls out of the planner, it is not asserted."""
        result = reachable((("A", "B"),), ("A", "C"))
        self.assertFalse(result.reachable)
        self.assertIs(result.terminal, Terminal.NEEDS_INFORMATION)
        self.assertIsNone(result.path)

    def test_distractor_edges_do_not_manufacture_a_route(self):
        premises = (("A", "B"), ("X", "C"), ("Y", "Z"), ("B", "C"))
        self.assertTrue(reachable(premises, ("A", "C")).reachable)
        self.assertFalse(reachable(premises, ("A", "Z")).reachable)

    def test_a_cycle_does_not_hang(self):
        self.assertFalse(reachable((("A", "B"), ("B", "A")), ("A", "C")).reachable)

    def test_a_chain_longer_than_the_depth_bound_is_not_claimed(self):
        """Not derived rather than wrongly derived — the bound is honest."""
        nodes = [f"N{i}" for i in range(MAX_CHAIN + 4)]
        premises = tuple((nodes[i], nodes[i + 1]) for i in range(len(nodes) - 1))
        self.assertFalse(reachable(premises, (nodes[0], nodes[-1])).reachable)


class WorldAssumptionTests(unittest.TestCase):
    def test_deduction_reads_absence_as_a_legitimate_no(self):
        item = next(i for i in generate_deduction_set(40, 61).items if not i.entailed)
        verdict, outcome = board_deduction(item)
        self.assertEqual(verdict, "NO")
        self.assertIs(outcome.terminal, Terminal.CONCLUDED)

    def test_honesty_reads_the_same_absence_as_unknown(self):
        """The one-line difference M1 exists to measure."""
        item = next(i for i in generate_honesty_set(40, 62).items if not i.answerable)
        verdict, outcome = board_honesty(item)
        self.assertEqual(verdict, "UNKNOWN")
        self.assertIs(outcome.terminal, Terminal.NEEDS_INFORMATION)

    def test_honesty_still_answers_what_the_premises_support(self):
        """Otherwise 'always UNKNOWN' would pass, which is the degenerate case."""
        item = next(i for i in generate_honesty_set(40, 62).items if i.answerable)
        self.assertEqual(board_honesty(item)[0], "YES")


class FirewallPathTests(unittest.TestCase):
    def test_identity_is_not_a_parameter_of_the_rating(self):
        """Structural exclusion, not a filter applied after identity was seen."""
        self.assertEqual(list(inspect.signature(rate_case).parameters), ["evidence", "lo", "hi"])

    def test_both_halves_of_a_pair_are_identical(self):
        pair = generate_firewall_pairs(10, 63).items[0]
        base, variant = board_firewall_pair(pair)
        self.assertEqual(base.value, variant.value)

    def test_no_evidence_concludes_nothing(self):
        self.assertIs(rate_case({}).terminal, Terminal.NEEDS_INFORMATION)

    def test_the_whole_firewall_arm_is_clean(self):
        pairs = generate_firewall_pairs(120, 20260831).items
        report = flip_report({p.pair_id: board_firewall_pair(p) for p in pairs})
        self.assertTrue(report.passed)
        self.assertEqual(report.max_movement, 0.0)


class ConstructValidityTests(unittest.TestCase):
    """What a passing Stage 5 can and cannot be claimed to show."""

    SET = generate_deduction_set(120, 20260827, Difficulty(hops=3, distractors=4))

    def test_the_board_is_correct_by_construction_on_deduction(self):
        scored = sum(score_deduction(i, board_deduction(i)[0]) for i in self.SET.items)
        self.assertEqual(scored, len(self.SET))

    def test_the_board_is_correct_by_construction_on_honesty(self):
        items = generate_honesty_set(120, 20260830).items
        scored = sum(score_honesty(i, board_honesty(i)[0]) for i in items)
        self.assertEqual(scored, len(items))

    def test_b4_trivial_solver_matches_the_board(self):
        """The bound on the claim, asserted so it cannot change silently.

        Ten lines of breadth-first search, no CAS and no RPM, score what the
        board scores. While this holds, a passing M3 is a fact about symbolic
        solvers beating language models at symbolic tasks — not a fact about
        CAS. Any redesign that makes Stage 5 discriminating will break this
        test, and breaking it is the goal.
        """
        board = sum(score_deduction(i, board_deduction(i)[0]) for i in self.SET.items)
        trivial = sum(b4_trivial_solver(i) for i in self.SET.items)
        self.assertEqual(board, trivial)
        self.assertEqual(trivial, len(self.SET))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
