"""The reasoning runtime — the cycle, the gates, and the two constitutional rules.

The rules are enforced structurally, so the tests check the structure rather
than the behaviour where they can: the bias firewall is a property of two
function signatures, and domain descent is a property of the phase order.
"""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from cmb import CognitiveMemoryBoard  # noqa: E402
from rpm import Terminal  # noqa: E402

from banks import DecompositionBank, InferenceBank  # noqa: E402
from foundations import FoundationProfile, focused_profile  # noqa: E402
from runtime import (  # noqa: E402
    DOMAIN_ORDER,
    PHASE_DOMAIN,
    CommitGate,
    Phase,
    Problem,
    ReasoningProcessor,
    RuntimeError_,
)


def chain(*edges, closed=False, query=("VS", "IU"), name="t"):
    premises = tuple(
        (e[0], e[1], e[2]) if len(e) == 3 else (e[0], "leads_to", e[1]) for e in edges
    )
    return Problem(name, "leads_to", premises, query, closed_world=closed)


def processor(**kw):
    return ReasoningProcessor(focused_profile("F2|A", 0.9), **kw)


class BiasFirewallTests(unittest.TestCase):
    """Ambition may choose the question. It must not choose the answer."""

    def test_the_evaluation_banks_cannot_be_handed_the_ambition(self):
        """There is no parameter through which a FoundationProfile could reach
        `^6` or `^9`. This is a property of the signatures, so it cannot be
        undone by a caller being careless -- only by editing the signature,
        which fails this test."""
        for method in (DecompositionBank.decompose, InferenceBank.land):
            params = inspect.signature(method).parameters
            for name, param in params.items():
                annotation = str(param.annotation)
                self.assertNotIn("FoundationProfile", annotation, method.__name__)
                self.assertNotIn("profile", name.lower(), method.__name__)

    def test_the_ambition_is_consulted_only_at_prime_and_compare(self):
        episode = processor().run(chain(("VS", "QS"), ("QS", "IU")))
        phases = [s.phase for s in episode.trace if "TF" in s.note or "dominant" in s.note]
        self.assertTrue(phases)
        for phase in phases:
            self.assertIn(phase, (Phase.PRIME, Phase.COMPARE))

    def test_a_stronger_ambition_does_not_change_the_verdict(self):
        """Same premises, same question wanted, different intensity of wanting.

        Both profiles carry enough Desire for the problem's target channel to
        engage, so the only difference is how badly the processor wants it. If
        ambition could reach the evaluation stages, the keener one would report
        higher confidence or turn an abstention into a claim. It reports
        neither."""
        premises = chain(("VS", "QS"), ("QS", "IU"))
        weak = ReasoningProcessor(focused_profile("F2|A", 0.55)).run(premises)
        strong = ReasoningProcessor(focused_profile("F2|A", 1.0)).run(premises)
        self.assertEqual(weak.answer, strong.answer)
        self.assertEqual(weak.confidence, strong.confidence)
        self.assertEqual(
            weak.conclusion.support, strong.conclusion.support
        )

    def test_wanting_it_more_does_not_close_a_gap(self):
        """The gap stays open at every intensity of wanting, including total."""
        gap = chain(("VS", "QS"), ("AA", "IU"))
        for level in (0.55, 0.8, 1.0):
            episode = ReasoningProcessor(focused_profile("F2|A", level)).run(gap)
            self.assertEqual(episode.answer, "UNKNOWN", f"level {level}")
            self.assertIsNone(episode.conclusion)

    def test_no_desire_stops_the_episode_rather_than_altering_the_answer(self):
        """Ambition decides whether to engage. That is choosing the question.

        A processor with no Desire for the target channel halts at the RPM
        Desire block -- it does not go on to give a different answer. The two
        outcomes a leak would produce (a changed verdict, a changed
        confidence) are exactly what this rules out."""
        premises = chain(("VS", "QS"), ("QS", "IU"))
        uninterested = ReasoningProcessor(focused_profile("F5|A", 1.0)).run(premises)
        self.assertIs(uninterested.terminal, Terminal.NEEDS_DESIRE)
        self.assertEqual(uninterested.answer, "UNKNOWN")
        self.assertIsNone(uninterested.conclusion)


class DomainDescentTests(unittest.TestCase):
    def test_every_phase_declares_a_domain(self):
        self.assertEqual(set(PHASE_DOMAIN), set(Phase))
        for domain in PHASE_DOMAIN.values():
            self.assertIn(domain, DOMAIN_ORDER)

    def test_action_is_the_only_operational_phase(self):
        operational = [p for p, d in PHASE_DOMAIN.items() if d == "O"]
        self.assertEqual(operational, [Phase.ACT])

    def test_act_never_runs_before_p_c_and_e_have_reported(self):
        episode = processor().run(chain(("VS", "QS"), ("QS", "IU")))
        order = [s.phase for s in episode.trace]
        act = order.index(Phase.ACT)
        seen = {PHASE_DOMAIN[p] for p in order[:act]}
        self.assertTrue({"P", "C", "E"} <= seen)


class CommitGateTests(unittest.TestCase):
    def test_hysteresis_stops_a_borderline_case_chattering(self):
        gate = CommitGate(high=0.65, low=0.35)
        self.assertFalse(gate.decide(0.5))
        self.assertTrue(gate.decide(0.5, committed=True))

    def test_an_inverted_band_is_refused(self):
        with self.assertRaises(RuntimeError_) as ctx:
            CommitGate(high=0.3, low=0.6)
        self.assertEqual(ctx.exception.code, "E-RT-001")

    def test_confidence_below_the_threshold_withholds_rather_than_guesses(self):
        episode = processor(gate=CommitGate(high=0.99, low=0.98)).run(
            chain(("VS", "QS"), ("QS", "IU"))
        )
        self.assertIs(episode.terminal, Terminal.NEEDS_INFORMATION)
        self.assertEqual(episode.answer, "UNKNOWN")


class LearningTests(unittest.TestCase):
    def test_feedback_gain_must_be_low(self):
        """One outcome must not rewrite the machine's principles."""
        for beta in (0.5, 1.0, 0.0):
            with self.assertRaises(RuntimeError_) as ctx:
                processor(learn_beta=beta)
            self.assertEqual(ctx.exception.code, "E-RT-003")

    def test_a_concluded_episode_writes_experience_back(self):
        memory = CognitiveMemoryBoard()
        proc = ReasoningProcessor(focused_profile("F2|A", 0.9), memory)
        self.assertTrue(memory.recall("C5", decay=False).is_lacuna)
        proc.run(chain(("VS", "QS"), ("QS", "IU")))
        self.assertGreater(memory.recall("C5", decay=False).charge, 0.0)

    def test_one_episode_cannot_saturate_the_experience_cell(self):
        memory = CognitiveMemoryBoard()
        proc = ReasoningProcessor(focused_profile("F2|A", 0.9), memory)
        proc.run(chain(("VS", "QS"), ("QS", "IU")))
        self.assertLess(memory.recall("C5", decay=False).charge, 0.2)


class TerminationTests(unittest.TestCase):
    def test_every_episode_ends_in_exactly_one_terminal(self):
        cases = [
            chain(("VS", "QS"), ("QS", "IU")),
            chain(("VS", "QS"), ("AA", "IU")),
            chain(("VS", "QS"), ("AA", "IU"), closed=True),
            chain(),
        ]
        for problem in cases:
            episode = processor().run(problem)
            self.assertIsInstance(episode.terminal, Terminal)
            self.assertTrue(episode.trace)

    def test_a_contradictory_premise_set_is_inadmissible(self):
        problem = Problem(
            "contra",
            "leads_to",
            (("VS", "leads_to", "QS"),),
            ("VS", "QS"),
            negated_premises=(("VS", "leads_to", "QS"),),
        )
        episode = processor().run(problem)
        self.assertIs(episode.terminal, Terminal.INADMISSIBLE)
        self.assertIn("contradictory", episode.note)

    def test_an_unreachable_target_abstains_under_an_open_world(self):
        episode = processor().run(chain(("VS", "QS"), ("AA", "IU")))
        self.assertIs(episode.terminal, Terminal.NEEDS_INFORMATION)
        self.assertEqual(episode.answer, "UNKNOWN")

    def test_the_same_gap_is_a_legitimate_no_under_a_closed_world(self):
        episode = processor().run(chain(("VS", "QS"), ("AA", "IU"), closed=True))
        self.assertIs(episode.terminal, Terminal.CONCLUDED)
        self.assertEqual(episode.answer, "NO")

    def test_a_tick_budget_too_small_for_one_cycle_is_refused(self):
        with self.assertRaises(RuntimeError_) as ctx:
            processor(max_ticks=3)
        self.assertEqual(ctx.exception.code, "E-RT-002")


class TraceTests(unittest.TestCase):
    def test_a_concluded_run_reports_all_ten_phases_in_order(self):
        episode = processor().run(chain(("VS", "QS"), ("QS", "IU")))
        phases = [s.phase for s in episode.trace]
        for phase in Phase:
            self.assertIn(phase, phases)
        self.assertEqual(phases.index(Phase.ASSOCIATE) < phases.index(Phase.DECOMPOSE), True)
        self.assertEqual(phases.index(Phase.DECOMPOSE) < phases.index(Phase.INFER), True)
        self.assertEqual(phases.index(Phase.COMMIT) < phases.index(Phase.ACT), True)

    def test_the_report_names_the_query_the_terminal_and_the_support(self):
        episode = processor().run(chain(("VS", "QS"), ("QS", "IU")))
        report = episode.report()
        for fragment in ("CONCLUDED", "VS", "IU", "rests on", "^8", "^6", "^9"):
            self.assertIn(fragment, report)

    def test_drive_totals_are_reported_for_every_rail(self):
        episode = processor().run(chain(("VS", "QS"), ("QS", "IU")))
        self.assertEqual(len(episode.drive_totals), 7)

    def test_prime_reports_the_recipe_and_its_limiting_reagent(self):
        """The bank's one real job appears in the trace, not just in an API."""
        episode = processor().run(chain(("VS", "QS"), ("QS", "IU")))
        prime = next(s for s in episode.trace if s.phase is Phase.PRIME)
        self.assertIn("limiting reagent", prime.note)
        self.assertIn("Theta(deduction)", prime.note)
        self.assertIn("limiting_reagent", prime.data)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
