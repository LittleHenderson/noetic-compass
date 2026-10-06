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
from workspace import Status, Workspace  # noqa: E402
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


class LocalizedContradictionTests(unittest.TestCase):
    """Contradiction is local to the question. Rule C."""

    def test_a_contradiction_off_the_queried_route_does_not_poison_the_answer(self):
        """The earlier design refused every question the moment any
        contradiction existed anywhere. A living workspace would be useless
        after its first dispute."""
        problem = Problem(
            "off-route",
            "leads_to",
            (("VS", "leads_to", "QS"), ("QS", "leads_to", "IU"), ("AA", "leads_to", "BB")),
            ("VS", "IU"),
            negated_premises=(("AA", "leads_to", "BB"),),
        )
        episode = processor().run(problem)
        self.assertIs(episode.terminal, Terminal.CONCLUDED)
        self.assertEqual(episode.answer, "YES")
        self.assertIn("AA|leads_to|BB", episode.workspace.contradictions())

    def test_a_contradiction_on_the_only_route_is_inadmissible_and_named(self):
        problem = Problem(
            "on-route",
            "leads_to",
            (("VS", "leads_to", "QS"), ("QS", "leads_to", "IU")),
            ("VS", "IU"),
            negated_premises=(("QS", "leads_to", "IU"),),
        )
        episode = processor().run(problem)
        self.assertIs(episode.terminal, Terminal.INADMISSIBLE)
        self.assertIn("QS|leads_to|IU", episode.note)

    def test_a_clean_route_beats_a_contested_one(self):
        problem = Problem(
            "bypass",
            "leads_to",
            (
                ("VS", "leads_to", "QS"), ("QS", "leads_to", "IU"),
                ("VS", "leads_to", "ZZ"), ("ZZ", "leads_to", "IU"),
            ),
            ("VS", "IU"),
            negated_premises=(("QS", "leads_to", "IU"),),
        )
        episode = processor().run(problem)
        self.assertIs(episode.terminal, Terminal.CONCLUDED)
        self.assertEqual(episode.answer, "YES")
        self.assertEqual(
            episode.conclusion.support, ("VS|leads_to|ZZ", "ZZ|leads_to|IU")
        )

    def test_a_route_with_one_contested_and_one_absent_link_is_not_inadmissible(self):
        """Rule C is 'every absent link is disputed', not 'any link is'. A
        route that is also missing an undisputed link is simply unknown."""
        problem = Problem(
            "mixed",
            "leads_to",
            (("VS", "leads_to", "QS"), ("QS", "co_occurs", "IU"), ("IU", "leads_to", "TR")),
            ("VS", "TR"),
            negated_premises=(("VS", "leads_to", "QS"),),
        )
        episode = processor().run(problem)
        self.assertIs(episode.terminal, Terminal.NEEDS_INFORMATION)

    def test_a_derivable_claim_whose_denial_is_given_is_a_dispute_not_a_yes(self):
        """A clean chain reaches Z, and 'A does not lead to Z' is also given.
        Deriving the chain does not make the claim true; it makes the
        workspace disagree with itself about that exact claim."""
        problem = Problem(
            "denied-conclusion",
            "leads_to",
            (("VS", "leads_to", "QS"), ("QS", "leads_to", "IU")),
            ("VS", "IU"),
            negated_premises=(("VS", "leads_to", "IU"),),
        )
        episode = processor().run(problem)
        self.assertIs(episode.terminal, Terminal.INADMISSIBLE)
        self.assertIn("VS|leads_to|IU", episode.note)
        self.assertTrue(episode.workspace.contested("VS", "leads_to", "IU"))

    def test_an_explicit_denial_is_a_no_under_an_open_world(self):
        """Being told something is false is knowledge, not a gap."""
        problem = Problem(
            "denied", "leads_to", (), ("VS", "IU"),
            negated_premises=(("VS", "leads_to", "IU"),),
        )
        episode = processor().run(problem)
        self.assertIs(episode.terminal, Terminal.CONCLUDED)
        self.assertEqual(episode.answer, "NO")

    def test_a_given_denial_outranks_a_partial_route_association_surfaced(self):
        """Told "VS does not lead to IU", reminded of a route VS -> QS ~ IU by a
        mere association: the answer is NO in both worlds, not "I do not know".
        Without this a reasoner would abstain on a question it was explicitly
        told the answer to, because something reminded it of a route."""
        for closed in (False, True):
            ws = Workspace(closed_world=closed)
            ws.fact("VS", "leads_to", "QS")
            ws.fact("QS", "co_occurs", "IU")
            ws.fact("VS", "leads_to", "IU", negated=True)
            episode = processor().run_in(
                ws, Problem("denied-partial", "leads_to", (), ("VS", "IU"), closed_world=closed)
            )
            self.assertIs(episode.terminal, Terminal.CONCLUDED, closed)
            self.assertEqual(episode.answer, "NO", closed)
            self.assertTrue(episode.candidates, "^8 did surface the partial route")
        # The same with the gap given as a guess rather than an association.
        ws = Workspace()
        ws.fact("VS", "leads_to", "QS")
        ws.hypothesize("QS", "leads_to", "IU", stage="stream")
        ws.fact("VS", "leads_to", "IU", negated=True)
        episode = processor().run_in(ws, Problem("denied-guess", "leads_to", (), ("VS", "IU")))
        self.assertEqual(episode.answer, "NO")

    def test_a_contested_claim_asked_directly_is_a_dispute_not_a_denial(self):
        """F(a,b), N(a,b), ask a->b: both polarities are held, so the question
        is inadmissible and names the pair; a denial that is itself disputed
        is not knowledge."""
        ws = Workspace()
        ws.fact("VS", "leads_to", "IU")
        ws.fact("VS", "leads_to", "IU", negated=True)
        episode = processor().run_in(ws, Problem("contested", "leads_to", (), ("VS", "IU")))
        self.assertIs(episode.terminal, Terminal.INADMISSIBLE)
        self.assertIn("VS|leads_to|IU", episode.note)


class SuppliedWorkspaceTests(unittest.TestCase):
    """`run_in` is the organism's entry point: the workspace outlives the episode."""

    def test_run_in_reasons_against_a_supplied_workspace(self):
        ws = Workspace()
        ws.fact("VS", "leads_to", "QS")
        ws.fact("QS", "leads_to", "IU")
        episode = processor().run_in(ws, Problem("t", "leads_to", (), ("VS", "IU")))
        self.assertEqual(episode.answer, "YES")
        self.assertIs(episode.workspace, ws)

    def test_a_conclusion_landed_earlier_is_held_and_answered_directly(self):
        ws = Workspace()
        ws.fact("VS", "leads_to", "QS")
        ws.fact("QS", "leads_to", "IU")
        proc = processor()
        first = proc.run_in(ws, Problem("t1", "leads_to", (), ("VS", "IU")))
        self.assertIs(first.conclusion.status, Status.DERIVED)
        second = proc.run_in(ws, Problem("t2", "leads_to", (), ("VS", "IU")))
        self.assertEqual(second.answer, "YES")
        infer = next(s for s in second.trace if s.phase is Phase.INFER)
        self.assertIn("YES", infer.note)
        self.assertIs(second.conclusion, first.conclusion)

    def test_a_retracted_support_takes_the_held_conclusion_down_with_it(self):
        ws = Workspace()
        ws.fact("VS", "leads_to", "QS")
        ws.fact("QS", "leads_to", "IU")
        proc = processor()
        proc.run_in(ws, Problem("t1", "leads_to", (), ("VS", "IU")))
        ws.retract("QS|leads_to|IU")
        again = proc.run_in(ws, Problem("t2", "leads_to", (), ("VS", "IU")))
        self.assertEqual(again.answer, "UNKNOWN")

    def test_route_guesses_are_swept_so_the_next_episode_starts_clean(self):
        ws = Workspace()
        ws.fact("VS", "leads_to", "QS")
        processor().run_in(ws, Problem("t", "leads_to", (), ("VS", "IU")))
        self.assertEqual([p for p in ws.live() if p.stage == "^8"], [])

    def test_lacunae_reported_are_only_this_episodes(self):
        ws = Workspace()
        ws.fact("VS", "leads_to", "QS")
        proc = processor()
        proc.run_in(ws, Problem("t1", "leads_to", (), ("VS", "IU")))
        ws.fact("AA", "leads_to", "BB")
        second = proc.run_in(ws, Problem("t2", "leads_to", (), ("AA", "CC")))
        self.assertIn("AA|leads_to|CC", second.note)
        self.assertNotIn("VS|leads_to|IU", second.note)

    def test_a_supplied_profile_reaches_prime_but_not_the_verdict(self):
        """Two identical workspaces, two ambitions, one answer and one
        confidence. (Identical workspaces, not one shared: the first run
        lands a derived edge that the second would then see as a shorter
        route -- that is state, not ambition, and a different test.)"""
        def fresh():
            ws = Workspace()
            ws.fact("VS", "leads_to", "QS")
            ws.fact("QS", "leads_to", "IU")
            return ws
        proc = processor()
        base = proc.run_in(fresh(), Problem("t", "leads_to", (), ("VS", "IU")))
        keen = proc.run_in(
            fresh(), Problem("t", "leads_to", (), ("VS", "IU")),
            profile=focused_profile("F2|A", 1.0),
        )
        self.assertEqual(base.answer, keen.answer)
        self.assertEqual(base.confidence, keen.confidence)
        self.assertEqual(base.conclusion.support, keen.conclusion.support)
        self.assertEqual(keen.profile.dominant(), "F2|A")
        prime = next(s for s in keen.trace if s.phase is Phase.PRIME)
        self.assertIn("F2|A", prime.note)


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
