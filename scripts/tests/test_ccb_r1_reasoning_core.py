"""Stages 1 and 4 — RPM, memory, comparison, and the episode controller.

Stage 1 covers the reasoning tasks the test program names. Stage 4 covers the
dynamics: section-retraction (CLAUDE.md Correction 2) as a property test,
memory retention and lacuna accuracy, and rumination termination.
"""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from cdab import Candidate, CdabError, compare, tournament  # noqa: E402
from cmb import CognitiveMemoryBoard, Tier  # noqa: E402
from episode import Stage, linear_board, run_episode  # noqa: E402
from cjt_sim import CjtSpec, Scale  # noqa: E402
from rpm import (  # noqa: E402
    DEFAULT_SUFFICIENCY,
    Goal,
    PrereqState,
    Prereq,
    RpmPlanner,
    Terminal,
    retract,
)


def goal(name: str, d: float, w: float, p: float) -> Goal:
    return Goal(name, PrereqState(d), PrereqState(w), PrereqState(p))


# ===========================================================================
# Stage 1 — the reasoning tasks
# ===========================================================================


class RpmFirstBlockDescent(unittest.TestCase):
    """Guide p.15: "the first insufficient state becomes the next goal"."""

    def test_scan_order_is_d_then_w_then_p(self) -> None:
        g = goal("all_blocked", 1.0, 1.0, 1.0)
        self.assertIs(g.first_block(), Prereq.D, "D is scanned first")

    def test_first_block_is_wisdom_when_desire_holds(self) -> None:
        """The guide's own worked scan: D sufficient, W the first block."""
        g = goal("publish", 10.0, 2.5, 4.0)
        self.assertIs(g.first_block(), Prereq.W)

    def test_a_wisdom_block_terminates_as_needs_information(self) -> None:
        result = RpmPlanner().run(goal("publish", 10.0, 2.5, 9.0))
        self.assertIs(result.terminal, Terminal.NEEDS_INFORMATION)

    def test_a_power_block_terminates_as_needs_capability(self) -> None:
        result = RpmPlanner().run(goal("publish", 10.0, 9.0, 1.0))
        self.assertIs(result.terminal, Terminal.NEEDS_CAPABILITY)

    def test_a_desire_block_has_its_own_terminal(self) -> None:
        """The audited design had four terminals and no exit for a D-block."""
        result = RpmPlanner().run(goal("publish", 1.0, 9.0, 9.0))
        self.assertIs(result.terminal, Terminal.NEEDS_DESIRE)

    def test_resolving_a_subgoal_ascends_and_concludes(self) -> None:
        parent = goal("publish", 9.0, 2.0, 9.0)
        child = goal("acquire_market_knowledge", 9.0, 9.0, 9.0)
        result = RpmPlanner().run(parent, {("publish", Prereq.W): child})
        self.assertIs(result.terminal, Terminal.CONCLUDED)
        self.assertIn("acquire_market_knowledge", result.resolved)

    def test_inadmissible_short_circuits_before_any_scan(self) -> None:
        result = RpmPlanner().run(goal("x", 9.0, 9.0, 9.0), admissible=False)
        self.assertIs(result.terminal, Terminal.INADMISSIBLE)
        self.assertEqual(result.trace, [])


class CdabControlledComparison(unittest.TestCase):
    """Matched gain and shared bias, or the comparator invents the difference."""

    def test_unshared_bias_is_refused(self) -> None:
        a = Candidate("A", bias="charter", beta=1.0, activation=2.0)
        b = Candidate("B", bias="ambition", beta=1.0, activation=1.0)
        with self.assertRaises(CdabError):
            compare(a, b)

    def test_mismatched_gain_is_refused(self) -> None:
        a = Candidate("A", bias="charter", beta=1.0, activation=2.0)
        b = Candidate("B", bias="charter", beta=2.0, activation=1.0)
        with self.assertRaises(CdabError):
            compare(a, b)

    def test_shared_bias_and_matched_gain_yields_the_divergence(self) -> None:
        a = Candidate("A", bias="charter", beta=2.0, activation=3.0)
        b = Candidate("B", bias="charter", beta=2.0, activation=1.0)
        diff = compare(a, b)
        self.assertEqual(diff.winner, "A")
        self.assertAlmostEqual(diff.margin, 4.0)
        self.assertAlmostEqual(diff.common_mode_rejected, 1.0)

    def test_a_tie_produces_no_winner(self) -> None:
        a = Candidate("A", bias="charter", beta=1.0, activation=2.0)
        b = Candidate("B", bias="charter", beta=1.0, activation=2.0)
        self.assertIsNone(compare(a, b).winner)

    def test_tournament_scales_past_two_candidates(self) -> None:
        cands = [
            Candidate("A", "charter", 1.0, 1.0),
            Candidate("B", "charter", 1.0, 5.0),
            Candidate("C", "charter", 1.0, 3.0),
        ]
        self.assertEqual(tournament(cands).winner, "B")


class EpisodeGating(unittest.TestCase):
    """P>C>E>O descent and the ambition firewall, enforced structurally."""

    def test_the_reference_board_concludes(self) -> None:
        self.assertTrue(run_episode(linear_board()).concluded)

    def test_a_domain_ascent_is_inadmissible(self) -> None:
        stages = linear_board()
        bad = Stage("infer", "C", "P", 7, stages[2].spec, stages[2].v, stages[2].r_total)
        stages[2] = bad
        result = run_episode(stages)
        self.assertIs(result.terminal, Terminal.INADMISSIBLE)
        self.assertTrue(any("W-axis" in v for v in result.violations))

    def test_ambition_on_the_inference_stage_is_inadmissible(self) -> None:
        stages = linear_board()
        s = stages[2]
        stages[2] = Stage(s.label, s.domain, "E", 5, s.spec, s.v, s.r_total)
        result = run_episode(stages)
        self.assertIs(result.terminal, Terminal.INADMISSIBLE)
        self.assertTrue(any("firewall" in v for v in result.violations))

    def test_a_principled_charter_on_inference_is_allowed(self) -> None:
        """F7 in the Principled domain is a charter, not ambition."""
        stages = linear_board()
        s = stages[2]
        stages[2] = Stage(s.label, s.domain, "P", 7, s.spec, s.v, s.r_total)
        self.assertTrue(run_episode(stages).concluded)

    def test_a_lacuna_becomes_needs_information_not_a_guess(self) -> None:
        memory = CognitiveMemoryBoard()
        memory.write("C2", 0.9)
        result = run_episode(
            linear_board(), memory=memory, required_recall=("C2", "E7")
        )
        self.assertIs(result.terminal, Terminal.NEEDS_INFORMATION)
        self.assertIn("E7", result.lacunae_hit)

    def test_every_episode_reaches_exactly_one_terminal(self) -> None:
        self.assertIsInstance(run_episode(linear_board()).terminal, Terminal)


# ===========================================================================
# Stage 4 — dynamics
# ===========================================================================


class SectionRetractionProperty(unittest.TestCase):
    """Correction 2: prerequisite satisfaction is ONE-DIRECTIONAL.

    "RPM Gate must NOT assume reversibility. Cache initial satisfaction results."
    Property-tested rather than spot-checked.
    """

    CASES = 10_000

    def test_satisfaction_never_silently_retracts(self) -> None:
        rng = random.Random(20260827)
        for _ in range(self.CASES):
            state = PrereqState(rng.uniform(DEFAULT_SUFFICIENCY, 10.0))
            self.assertTrue(state.sufficient(), "starts sufficient")
            # Re-measure downward as many times as you like; it may not un-satisfy.
            state.score = rng.uniform(0.0, DEFAULT_SUFFICIENCY - 1e-9)
            self.assertTrue(
                state.sufficient(),
                "a cached-sufficient prerequisite must not retract on re-measurement",
            )

    def test_insufficient_states_can_still_rise(self) -> None:
        """One-directional means monotone up, not frozen."""
        rng = random.Random(11)
        for _ in range(1000):
            state = PrereqState(rng.uniform(0.0, DEFAULT_SUFFICIENCY - 1e-9))
            self.assertFalse(state.sufficient())
            state.score = rng.uniform(DEFAULT_SUFFICIENCY, 10.0)
            self.assertTrue(state.sufficient())

    def test_genuine_loss_requires_an_explicit_auditable_retraction(self) -> None:
        state = PrereqState(9.0)
        self.assertTrue(state.sufficient())
        retract(state, 1.0)
        self.assertFalse(state.sufficient(), "explicit retraction is the only way down")


class RuminationTermination(unittest.TestCase):
    """The stop gate: a reasoning oscillator must not become rumination."""

    def test_unbounded_descent_terminates_as_nonterminating(self) -> None:
        """Each sub-goal blocks again, forever. The depth bound must catch it."""
        chain: dict[tuple[str, Prereq], Goal] = {}
        for i in range(50):
            chain[(f"g{i}", Prereq.W)] = goal(f"g{i + 1}", 9.0, 1.0, 9.0)
        result = RpmPlanner(max_depth=8).run(goal("g0", 9.0, 1.0, 9.0), chain)
        self.assertIs(result.terminal, Terminal.NONTERMINATING)
        self.assertLessEqual(result.depth_reached, 8)

    def test_a_cycle_terminates_rather_than_looping(self) -> None:
        a = goal("a", 9.0, 1.0, 9.0)
        b = goal("b", 9.0, 1.0, 9.0)
        result = RpmPlanner().run(a, {("a", Prereq.W): b, ("b", Prereq.W): a})
        self.assertIs(result.terminal, Terminal.NONTERMINATING)

    def test_depth_bound_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            RpmPlanner(max_depth=0)


class MemoryDynamics(unittest.TestCase):
    """CMB retention, recall, and lacuna accuracy across the three tiers."""

    def test_the_bank_has_exactly_forty_cells_keyed_by_cas_states(self) -> None:
        board = CognitiveMemoryBoard()
        self.assertEqual(len(board.cells), 40)
        for key in ("P0", "C9", "E4", "O7"):
            self.assertIn(key, board.cells)

    def test_an_empty_bank_is_all_lacunae(self) -> None:
        board = CognitiveMemoryBoard()
        self.assertEqual(len(board.lacunae()), 40)
        self.assertEqual(board.occupancy(), 0.0)

    def test_working_memory_fades_faster_than_constitutional(self) -> None:
        board = CognitiveMemoryBoard()
        board.write("C1", 1.0, Tier.WORKING)
        board.write("P1", 1.0, Tier.CONSTITUTIONAL)
        for _ in range(5):
            board.recall("C1")
            board.recall("P1")
        self.assertLess(board.cells["C1"].charge, board.cells["P1"].charge)

    def test_working_memory_decays_to_a_lacuna_but_constitutional_does_not(self) -> None:
        board = CognitiveMemoryBoard()
        board.write("C1", 1.0, Tier.WORKING)
        board.write("P1", 1.0, Tier.CONSTITUTIONAL)
        for _ in range(20):
            board.recall("C1")
            board.recall("P1")
        self.assertTrue(board.recall("C1", decay=False).is_lacuna)
        self.assertFalse(board.recall("P1", decay=False).is_lacuna)

    def test_refresh_restores_a_durable_cell(self) -> None:
        board = CognitiveMemoryBoard()
        board.write("P3", 1.0, Tier.CONSTITUTIONAL)
        for _ in range(10):
            board.recall("P3")
        board.refresh("P3", 1.0)
        self.assertFalse(board.recall("P3", decay=False).is_lacuna)

    def test_lacuna_detection_is_domain_addressable(self) -> None:
        board = CognitiveMemoryBoard()
        for n in range(10):
            board.write(f"C{n}", 0.9)
        self.assertEqual(board.domain_lacunae("C"), ())
        self.assertEqual(len(board.domain_lacunae("E")), 10)

    def test_writing_outside_the_forty_states_is_refused(self) -> None:
        with self.assertRaises(KeyError):
            CognitiveMemoryBoard().write("X1", 1.0)


if __name__ == "__main__":
    unittest.main()
