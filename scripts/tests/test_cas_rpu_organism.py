"""The organism — held beliefs that stay sound as the stream revises them.

Every verdict asserted here is the one the oracle in
`docs/working/revision_streams_contract_2026_10_06.md` sections 2-5 gives for
the same stream; the organism is correct iff it agrees. The tests are grouped
by the four mechanisms the family diagnoses (retraction, the hypothesis
firewall, localized contradiction, the named lacuna) and then by the three
things the organism adds over a replayer: standing, the heartbeat, and
motivation that may choose the question but never the answer.
"""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "scripts" / "cas_rpu"
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from cmb import CognitiveMemoryBoard  # noqa: E402
from rpm import Terminal  # noqa: E402

from banks import DecompositionBank, InferenceBank  # noqa: E402
from events import EventKind, ask, associate, fact, hypothesis, negation, retract  # noqa: E402
from foundations import Drive, FoundationProfile, focused_profile, reasoning_profile  # noqa: E402
from organism import (  # noqa: E402
    ENGAGEMENT,
    BeatReport,
    Heartbeat,
    MeteredWorkspace,
    Motivation,
    Organism,
    OrganismError,
    Response,
)
from runtime import Phase  # noqa: E402
from workspace import ASSERTIVE, Status, Workspace  # noqa: E402

L = "QS|leads_to|IU"  # the designated link in every backbone below


def backbone():
    """VS -> QS -> IU -> TR, as three FACT events."""
    return [fact("VS", "QS"), fact("QS", "IU"), fact("IU", "TR")]


def verdicts(responses):
    return [
        (r.verdict, r.lacunae, r.contested)
        for r in responses
        if r.event.kind is EventKind.ASK
    ]


class RetractionTests(unittest.TestCase):
    """Class R: transitive retraction of a *held* derivation."""

    def test_state_survives_across_episodes(self):
        """Facts given in two events, asked in a third. The processor alone
        would need them in one premise set; the organism holds them."""
        org = Organism()
        org.consume(fact("VS", "QS"))
        org.consume(fact("QS", "IU"))
        response = org.consume(ask("VS", "IU"))
        self.assertEqual(response.verdict, "YES")
        self.assertIs(response.terminal, Terminal.CONCLUDED)
        self.assertIs(response.episode.conclusion.status, Status.DERIVED)
        self.assertIn("VS|leads_to|IU", org.standing)
        self.assertEqual(org.standing["VS|leads_to|IU"], 2)

    def test_a_standing_conclusion_is_answered_from_the_record_on_re_ask(self):
        org = Organism()
        org.run_stream(backbone())
        first = org.consume(ask("VS", "TR"))
        second = org.consume(ask("VS", "TR"))
        self.assertEqual(second.verdict, "YES")
        infer = next(s for s in second.episode.trace if s.phase is Phase.INFER)
        self.assertIn("YES", infer.note)
        self.assertIs(second.episode.conclusion, first.episode.conclusion)
        self.assertEqual(org.standing["VS|leads_to|TR"], 3)  # the first ask, not the second

    def test_a_retracted_support_withdraws_the_standing_conclusion_and_says_so(self):
        """R-stale. The withdrawn column is the organism's held-state
        discipline made visible: it names the conclusion that fell."""
        for closed, after in ((False, "UNKNOWN"), (True, "NO")):
            with self.subTest(closed_world=closed):
                org = Organism(closed_world=closed)
                org.run_stream(backbone())
                self.assertEqual(org.consume(ask("VS", "TR")).verdict, "YES")
                gone = org.consume(retract("QS", "IU"))
                self.assertTrue(gone.accepted)
                self.assertEqual(gone.withdrawn, ("VS|leads_to|TR",))
                self.assertNotIn("VS|leads_to|TR", org.standing)
                again = org.consume(ask("VS", "TR"))
                self.assertEqual(again.verdict, after)
                self.assertEqual(again.withdrawn, ())

    def test_retracting_an_off_path_distractor_leaves_the_conclusion_standing(self):
        """R-control: the cascade is exact, not a flush."""
        org = Organism()
        org.run_stream(backbone() + [fact("AA", "BB")])
        org.consume(ask("VS", "TR"))
        response = org.consume(retract("AA", "BB"))
        self.assertTrue(response.accepted)
        self.assertEqual(response.withdrawn, ())
        self.assertIn("VS|leads_to|TR", org.standing)
        self.assertEqual(org.consume(ask("VS", "TR")).verdict, "YES")

    def test_a_revived_given_lets_the_conclusion_be_re_derived(self):
        """R-revive: a RETRACTED pid revives on re-assertion; its old
        consequences stay down until re-derived."""
        org = Organism()
        org.run_stream(backbone())
        org.consume(ask("VS", "TR"))
        org.consume(retract("QS", "IU"))
        self.assertNotIn("VS|leads_to|TR", org.standing)
        org.consume(fact("QS", "IU"))
        self.assertIs(org.ws.props["VS|leads_to|TR"].status, Status.RETRACTED)
        response = org.consume(ask("VS", "TR"))
        self.assertEqual(response.verdict, "YES")
        self.assertIn("VS|leads_to|TR", org.standing)


class ForgettingRuleTests(unittest.TestCase):
    """You may forget what you were told. Not what you derived, not what you guessed."""

    def test_forgetting_a_derived_claim_is_refused_and_names_its_supports(self):
        org = Organism()
        org.run_stream(backbone())
        org.consume(ask("VS", "TR"))
        response = org.consume(retract("VS", "TR"))
        self.assertFalse(response.accepted)
        self.assertEqual(response.code, "E-ORG-001")
        for root in ("VS|leads_to|QS", L, "IU|leads_to|TR"):
            self.assertIn(root, response.note)
        self.assertIn("derived, not given", response.note)
        self.assertIn("VS|leads_to|TR", org.standing)
        self.assertEqual(response.withdrawn, ())

    def test_forgetting_what_was_never_given_is_refused(self):
        org = Organism()
        never = org.consume(retract("AA", "BB"))
        self.assertFalse(never.accepted)
        self.assertEqual(never.code, "E-ORG-002")

        org.consume(hypothesis("AA", "BB"))
        guess = org.consume(retract("AA", "BB"))
        self.assertFalse(guess.accepted)
        self.assertEqual(guess.code, "E-ORG-002")
        self.assertIn("guess", guess.note)

        org.consume(fact("CC", "DD"))
        self.assertTrue(org.consume(retract("CC", "DD")).accepted)
        twice = org.consume(retract("CC", "DD"))
        self.assertFalse(twice.accepted)
        self.assertEqual(twice.code, "E-ORG-002")

    def test_forgetting_an_association_follows_the_same_rule(self):
        org = Organism()
        self.assertEqual(org.consume(retract("VS", "QS", "co_occurs")).code, "E-ORG-002")
        org.consume(associate("VS", "QS"))
        response = org.consume(retract("VS", "QS", "co_occurs"))
        self.assertTrue(response.accepted)
        self.assertIs(org.ws.props["VS|co_occurs|QS"].status, Status.RETRACTED)

    def test_forgetting_a_given_in_dispute_is_accepted_and_reinstates_the_denial(self):
        org = Organism()
        org.consume(fact("QS", "IU"))
        org.consume(negation("QS", "IU"))
        self.assertTrue(org.ws.contested("QS", "leads_to", "IU"))
        response = org.consume(retract("QS", "IU"))
        self.assertTrue(response.accepted)
        self.assertIs(org.ws.props["~" + L].status, Status.FACT)
        self.assertFalse(org.ws.contested("QS", "leads_to", "IU"))
        self.assertIn("stands again", response.note)
        self.assertEqual(org.consume(ask("QS", "IU")).verdict, "NO")

    def test_forgetting_a_disputed_derivation_is_still_refused(self):
        """Contract section 11: NEGATION of a pair held only DERIVED puts the
        derivation in dispute. It is still not a given, so it still cannot be
        forgotten, and the refusal still names its roots."""
        org = Organism()
        org.run_stream(backbone())
        org.consume(ask("VS", "TR"))
        org.consume(negation("VS", "TR"))
        response = org.consume(retract("VS", "TR"))
        self.assertEqual(response.code, "E-ORG-001")
        self.assertIn(L, response.note)


class HypothesisFirewallTests(unittest.TestCase):
    """Class H: a guess carries no answer, and a refuted guess is not a dispute."""

    def test_a_hypothesis_never_carries_an_answer_until_confirmed(self):
        """H-bridge then H-confirm."""
        org = Organism()
        org.consume(fact("VS", "QS"))
        org.consume(fact("IU", "TR"))
        org.consume(hypothesis("QS", "IU"))
        bridged = org.consume(ask("VS", "TR"))
        self.assertEqual(bridged.verdict, "UNKNOWN")
        self.assertIs(bridged.terminal, Terminal.NEEDS_INFORMATION)
        self.assertEqual(bridged.lacunae, (L,))
        self.assertEqual(bridged.contested, ())
        self.assertEqual(org.standing, {})

        confirmed = org.consume(fact("QS", "IU"))
        self.assertIs(org.ws.props[L].status, Status.FACT)
        self.assertEqual(confirmed.satisfied, (L,))
        self.assertEqual(org.consume(ask("VS", "TR")).verdict, "YES")

    def test_a_refuted_hypothesis_is_not_a_dispute(self):
        """H-refute, with the associative shadow present so that `^8` does
        surface the route and `^6` has to throw the denied link out."""
        for closed, verdict in ((False, "UNKNOWN"), (True, "NO")):
            with self.subTest(closed_world=closed):
                org = Organism(closed_world=closed)
                org.consume(fact("VS", "QS"))
                org.consume(fact("IU", "TR"))
                org.consume(associate("QS", "IU"))
                org.consume(hypothesis("QS", "IU"))
                refuted = org.consume(negation("QS", "IU"))
                self.assertTrue(refuted.accepted)
                self.assertIs(org.ws.props[L].status, Status.RETRACTED)
                response = org.consume(ask("VS", "TR"))
                self.assertEqual(response.verdict, verdict)
                self.assertIsNot(response.terminal, Terminal.INADMISSIBLE)
                self.assertEqual(response.contested, ())
                self.assertNotIn(L, response.lacunae)

    def test_a_guess_against_a_known_fact_or_denial_is_a_no_op(self):
        org = Organism()
        org.consume(fact("VS", "QS"))
        org.consume(negation("AA", "BB"))
        held = org.consume(hypothesis("VS", "QS"))
        self.assertTrue(held.accepted)
        self.assertIs(org.ws.props["VS|leads_to|QS"].status, Status.FACT)
        dead = org.consume(hypothesis("AA", "BB"))
        self.assertTrue(dead.accepted)
        self.assertIs(org.ws.props["AA|leads_to|BB"].status, Status.RETRACTED)
        self.assertIn("dead on arrival", dead.note)


class LocalizedContradictionTests(unittest.TestCase):
    """Class C: a dispute is local to the route it sits on."""

    def test_a_dispute_off_the_queried_route_does_not_poison_the_answer(self):
        """C-unrelated."""
        org = Organism()
        org.run_stream(backbone() + [fact("AA", "BB"), negation("AA", "BB")])
        self.assertIn("AA|leads_to|BB", org.ws.contradictions())
        response = org.consume(ask("VS", "TR"))
        self.assertEqual(response.verdict, "YES")
        self.assertEqual(response.contested, ())

    def test_a_clean_second_route_beats_a_disputed_one(self):
        """C-bypassed."""
        org = Organism()
        org.run_stream(
            [fact("VS", "QS"), fact("QS", "IU"), fact("VS", "ZZ"), fact("ZZ", "IU"), negation("QS", "IU")]
        )
        response = org.consume(ask("VS", "IU"))
        self.assertEqual(response.verdict, "YES")
        self.assertEqual(
            response.episode.conclusion.support, ("VS|leads_to|ZZ", "ZZ|leads_to|IU")
        )

    def test_a_dispute_on_the_only_route_is_inadmissible_and_named(self):
        """C-blocked."""
        org = Organism()
        org.run_stream(backbone() + [negation("QS", "IU")])
        response = org.consume(ask("VS", "TR"))
        self.assertEqual(response.verdict, "INADMISSIBLE")
        self.assertIs(response.terminal, Terminal.INADMISSIBLE)
        self.assertEqual(response.contested, (L,))
        self.assertEqual(response.lacunae, ())
        self.assertEqual(org.standing, {})

    def test_a_held_conclusion_falls_when_its_support_becomes_disputed(self):
        """C-stale: YES, then the denial arrives, then INADMISSIBLE -- and the
        organism says which held conclusion the denial took down."""
        org = Organism()
        org.run_stream(backbone())
        self.assertEqual(org.consume(ask("VS", "TR")).verdict, "YES")
        denial = org.consume(negation("QS", "IU"))
        self.assertEqual(denial.withdrawn, ("VS|leads_to|TR",))
        self.assertNotIn("VS|leads_to|TR", org.standing)
        again = org.consume(ask("VS", "TR"))
        self.assertEqual(again.verdict, "INADMISSIBLE")
        self.assertEqual(again.contested, (L,))

    def test_a_denied_derivation_is_a_dispute_on_re_ask(self):
        """Contract section 11: the organism and the oracle agree on an event
        the generator never emits."""
        org = Organism()
        org.run_stream(backbone())
        org.consume(ask("VS", "TR"))
        denial = org.consume(negation("VS", "TR"))
        self.assertEqual(denial.withdrawn, ("VS|leads_to|TR",))
        again = org.consume(ask("VS", "TR"))
        self.assertEqual(again.verdict, "INADMISSIBLE")
        self.assertEqual(again.contested, ("VS|leads_to|TR",))


class LacunaTests(unittest.TestCase):
    """Class N: open-world abstention names the gap it would need closed."""

    def test_an_open_world_gap_is_named(self):
        """N-gap with the shadow: `^8` surfaces the route through the
        association and `^6` names the missing `leads_to` link. The lacuna
        set is exactly the designated link, nothing more and nothing less."""
        org = Organism()
        org.run_stream([fact("VS", "QS"), associate("QS", "IU"), fact("IU", "TR")])
        response = org.consume(ask("VS", "TR"))
        self.assertEqual(response.verdict, "UNKNOWN")
        self.assertIs(response.terminal, Terminal.NEEDS_INFORMATION)
        self.assertEqual(response.lacunae, (L,))
        self.assertEqual(response.contested, ())
        self.assertEqual(org.wants(), (L,))

    def test_the_same_gap_is_a_plain_no_under_a_closed_world(self):
        """Paired worlds: identical stream, UNKNOWN becomes NO, and the lacuna
        column is empty because a closed world has no gaps to name."""
        org = Organism(closed_world=True)
        org.run_stream([fact("VS", "QS"), associate("QS", "IU"), fact("IU", "TR")])
        response = org.consume(ask("VS", "TR"))
        self.assertEqual(response.verdict, "NO")
        self.assertIs(response.terminal, Terminal.CONCLUDED)
        self.assertEqual(response.lacunae, ())
        self.assertEqual(org.wants(), ())

    def test_a_complete_chain_with_a_shadow_on_a_present_link_is_a_yes(self):
        """N-control."""
        org = Organism()
        org.run_stream(backbone() + [associate("QS", "IU")])
        response = org.consume(ask("VS", "TR"))
        self.assertEqual(response.verdict, "YES")
        self.assertEqual(response.lacunae, ())


class HeartbeatTests(unittest.TestCase):
    def test_the_heartbeat_decays_experience_and_audits_standing_conclusions(self):
        memory = CognitiveMemoryBoard()
        org = Organism(memory=memory)
        org.run_stream(backbone())
        concluded = org.consume(ask("VS", "TR"))
        self.assertGreater(concluded.beat.charge, 0.0)
        # Experience fades across beats with no LEARN to refresh it.
        later = org.consume(fact("AA", "BB"))
        self.assertLess(later.beat.charge, concluded.beat.charge)
        direct = org.heartbeat.beat(org)
        self.assertLess(direct.charge, later.beat.charge)
        # A healthy organism has nothing to report.
        self.assertEqual(concluded.beat.faults, ())
        self.assertEqual(later.beat.faults, ())
        self.assertEqual(org.faults, ())
        # Retract a premise behind the organism's back. The next beat finds a
        # standing conclusion whose root is dead and says so.
        org.ws.retract(L)
        broken = org.heartbeat.beat(org)
        self.assertEqual(len(broken.faults), 1)
        self.assertIn("E-ORG-003", broken.faults[0])
        self.assertIn("VS|leads_to|TR", broken.faults[0])
        self.assertIn(L, broken.faults[0])
        self.assertEqual(org.faults, broken.faults)

    def test_beats_are_not_events(self):
        org = Organism()
        org.run_stream(backbone())
        before = (org.clock, len(org.log), org.asks_made)
        report = org.heartbeat.beat(org)
        self.assertIsInstance(report, BeatReport)
        self.assertEqual((org.clock, len(org.log), org.asks_made), before)
        self.assertEqual(org.heartbeat.beats, 4)

    def test_every_consume_ends_with_exactly_one_beat(self):
        org = Organism()
        responses = org.run_stream(backbone() + [ask("VS", "TR"), retract("QS", "IU")])
        self.assertEqual([r.beat.beat_no for r in responses], [1, 2, 3, 4, 5])
        self.assertEqual(org.heartbeat.beats, 5)


class MotivationTests(unittest.TestCase):
    """Ambition may choose the question. It must not choose the answer."""

    @staticmethod
    def mixed_stream():
        """One abstention, one conclusion, one dispute, then enough further
        conclusions that a keen motivation would -- without the engagement
        floor -- have relaxed its Wisdom-desire under the RPM Desire gate."""
        events = [fact("VS", "QS"), associate("QS", "IU"), fact("IU", "TR"), ask("VS", "TR")]
        events += [fact("A1", "A2"), fact("A2", "A3"), ask("A1", "A3")]
        events += [fact("B1", "B2"), fact("B2", "B3"), negation("B2", "B3"), ask("B1", "B3")]
        for a, b in (("C1", "C2"), ("D1", "D2"), ("E1", "E2"), ("F1", "F2"), ("G1", "G2"), ("H1", "H2")):
            events += [fact(a, b), ask(a, b)]
        events += [ask("A1", "A3"), fact("QS", "IU"), ask("VS", "TR")]
        return events

    def test_motivation_may_change_what_is_asked_but_never_what_is_answered(self):
        cold = Organism(motivation_kwargs={"beta": 0.0})
        hot = Organism(motivation_kwargs={"beta": 0.2})
        cold_out = cold.run_stream(self.mixed_stream())
        hot_out = hot.run_stream(self.mixed_stream())
        self.assertEqual(verdicts(cold_out), verdicts(hot_out))
        self.assertEqual(
            [r.terminal for r in cold_out if r.episode], [r.terminal for r in hot_out if r.episode]
        )
        # The law is not vacuous: the two motivations really did diverge.
        self.assertNotEqual(cold.motivation.g, hot.motivation.g)
        self.assertEqual(cold.motivation.g[Drive.F2], cold.profile.g[Drive.F2])
        self.assertGreater(hot.motivation.g[Drive.F7], cold.motivation.g[Drive.F7])

    def test_success_cannot_relax_the_will_to_know_below_engagement(self):
        """The RPM Desire gate reads `10 * g[F2]`. If answered questions could
        push Wisdom-desire under it, the next question would not be engaged
        and the verdict would depend on mood. The floor is the constitution's
        own engagement level, and perturbation never crosses it."""
        hot = Organism(motivation_kwargs={"beta": 0.2, "relax": 0.0})
        for a, b in (("C1", "C2"), ("D1", "D2"), ("E1", "E2"), ("F1", "F2"), ("G1", "G2"), ("H1", "H2")):
            hot.consume(fact(a, b))
            response = hot.consume(ask(a, b))
            self.assertIs(response.terminal, Terminal.CONCLUDED, (a, b))
            self.assertGreaterEqual(hot.motivation.g[Drive.F2], ENGAGEMENT)
        self.assertEqual(hot.motivation.g[Drive.F2], ENGAGEMENT)

    def test_perturbation_moves_the_right_drive_and_relax_returns_it(self):
        motivation = Motivation(reasoning_profile(), relax=0.1, beta=0.1)
        base = dict(motivation.g)
        motivation.perturb(Terminal.NEEDS_INFORMATION)
        self.assertAlmostEqual(motivation.g[Drive.F2], min(1.0, base[Drive.F2] + 0.1))
        motivation.perturb(Terminal.INADMISSIBLE)
        self.assertAlmostEqual(motivation.g[Drive.F6], base[Drive.F6] + 0.1)
        motivation.perturb(Terminal.CONCLUDED)
        self.assertAlmostEqual(motivation.g[Drive.F7], base[Drive.F7] + 0.1)
        motivation.perturb(Terminal.NEEDS_DESIRE)  # not an outcome of reasoning
        self.assertEqual(motivation.perturbations, 3)
        for _ in range(200):
            motivation.relax()
        for drive in Drive:
            self.assertAlmostEqual(motivation.g[drive], base[drive], places=6)
        self.assertEqual(motivation.profile().q, motivation.constitution.q)

    def test_motivation_over_the_low_gain_bound_is_refused(self):
        profile = reasoning_profile()
        for kwargs in ({"beta": 0.25}, {"relax": 0.21}, {"beta": 1.0}, {"relax": -0.1}):
            with self.subTest(**kwargs):
                with self.assertRaises(OrganismError) as ctx:
                    Motivation(profile, **kwargs)
                self.assertEqual(ctx.exception.code, "E-ORG-004")
        with self.assertRaises(OrganismError) as ctx:
            Organism(motivation_kwargs={"beta": 0.5})
        self.assertEqual(ctx.exception.code, "E-ORG-004")
        # The bound itself is admissible: the hard law is tested at beta=0.2.
        Motivation(profile, beta=0.2, relax=0.2)

    def test_an_unanswered_want_is_resolved_when_its_lacuna_is_filled(self):
        """N-actionable, from the organism's side: the gap it named is filled,
        so it asks its own question again and reports the answer."""
        org = Organism()
        org.run_stream([fact("VS", "QS"), associate("QS", "IU"), fact("IU", "TR")])
        self.assertEqual(org.consume(ask("VS", "TR")).verdict, "UNKNOWN")
        self.assertEqual(org.wants(), (L,))
        filled = org.consume(fact("QS", "IU"))
        self.assertEqual(filled.satisfied, (L,))
        self.assertEqual(len(filled.resolved), 1)
        self.assertEqual(filled.resolved[0].answer, "YES")
        self.assertEqual(filled.resolved[0].problem.query, ("VS", "TR"))
        self.assertEqual(org.wants(), ())
        # A self-ask is never a probe: it does not enter standing.
        self.assertEqual(org.standing, {})
        self.assertEqual(org.consume(ask("VS", "TR")).verdict, "YES")
        self.assertIn("VS|leads_to|TR", org.standing)

    def test_a_want_is_closed_but_not_re_asked_when_the_organism_does_not_want_to_know(self):
        org = Organism()
        org.run_stream([fact("VS", "QS"), associate("QS", "IU"), fact("IU", "TR"), ask("VS", "TR")])
        org.motivation.g[Drive.F2] = 0.3  # below ENGAGEMENT, by hand
        filled = org.consume(fact("QS", "IU"))
        self.assertEqual(filled.satisfied, (L,))
        self.assertEqual(filled.resolved, ())
        self.assertEqual(org.wants(), ())
        self.assertEqual(org.reasks_made, 0)

    def test_an_unrelated_fact_satisfies_nothing(self):
        org = Organism()
        org.run_stream([fact("VS", "QS"), associate("QS", "IU"), fact("IU", "TR"), ask("VS", "TR")])
        response = org.consume(fact("AA", "BB"))
        self.assertEqual(response.satisfied, ())
        self.assertEqual(response.resolved, ())
        self.assertEqual(org.wants(), (L,))


class BiasFirewallTests(unittest.TestCase):
    def test_the_organism_and_heartbeat_cannot_hand_the_profile_to_the_evaluation_banks(self):
        """The runtime's law, extended: `^6` and `^9` have no parameter a
        profile could enter by, and the organism never calls them at all --
        its only path to the banks is `run_in`, which takes the profile and
        keeps it at PRIME, COMPARE and the Desire gate."""
        for method in (DecompositionBank.decompose, InferenceBank.land):
            for name, param in inspect.signature(method).parameters.items():
                self.assertNotIn("FoundationProfile", str(param.annotation), method.__name__)
                self.assertNotIn("profile", name.lower(), method.__name__)
        source = (PACKAGE / "organism.py").read_text().splitlines()
        for number, line in enumerate(source, 1):
            self.assertNotIn("decompose(", line, f"organism.py:{number}")
            self.assertNotIn(".land(", line, f"organism.py:{number}")
            self.assertNotIn("DecompositionBank", line, f"organism.py:{number}")
            self.assertNotIn("InferenceBank", line, f"organism.py:{number}")
        reaches = [
            line for line in source
            if "profile" in line.lower() and ("decompose" in line or "land(" in line)
        ]
        self.assertEqual(reaches, [])

    def test_the_processor_is_given_this_moments_ambition_not_the_constitution(self):
        org = Organism(motivation_kwargs={"beta": 0.2})
        org.run_stream([fact("VS", "QS"), associate("QS", "IU"), fact("IU", "TR"), ask("VS", "TR")])
        self.assertGreater(org.motivation.g[Drive.F2], org.profile.g[Drive.F2])
        response = org.consume(ask("VS", "TR"))
        self.assertEqual(response.episode.profile.g[Drive.F2], org.motivation.profile().g[Drive.F2])
        self.assertIsInstance(response.episode.profile, FoundationProfile)


class WorkAndDeterminismTests(unittest.TestCase):
    def test_work_is_reported_per_event(self):
        org = Organism()
        for response in org.run_stream(backbone()):
            self.assertEqual((response.work_asks, response.work_scanned, response.work), (0, 0, 0))
        asked = org.consume(ask("VS", "TR"))
        self.assertEqual(asked.work_scanned, 3)  # three propositions held when ^8 walked
        self.assertEqual(asked.work_asks, 3)  # one ask per link of the one route
        self.assertEqual(asked.work, asked.work_asks + asked.work_scanned)
        self.assertEqual(org.ws.asks, 3)
        # A self re-ask is work done during the FACT event that triggered it.
        org2 = Organism()
        org2.run_stream([fact("VS", "QS"), associate("QS", "IU"), fact("IU", "TR"), ask("VS", "TR")])
        filled = org2.consume(fact("QS", "IU"))
        self.assertEqual(len(filled.resolved), 1)
        self.assertGreater(filled.work_asks, 0)
        self.assertGreater(filled.work_scanned, 0)

    def test_a_workspace_subclass_handed_in_is_honoured_and_still_metered(self):
        """An ablation hands in its own Workspace. Its overrides stay in force
        beneath the meter, and the work column is still produced."""
        calls = []

        class Noted(Workspace):
            def ask(self, subject, relation, obj):
                calls.append((subject, relation, obj))
                return super().ask(subject, relation, obj)

        org = Organism(workspace_factory=Noted)
        self.assertIsInstance(org.ws, Noted)
        self.assertIsInstance(org.ws, MeteredWorkspace)
        org.run_stream(backbone())
        asked = org.consume(ask("VS", "TR"))
        self.assertEqual(asked.verdict, "YES")
        self.assertEqual(len(calls), asked.work_asks)
        self.assertIs(type(Organism(workspace_factory=MeteredWorkspace).ws), MeteredWorkspace)
        with self.assertRaises(OrganismError) as ctx:
            Organism(workspace_factory=lambda **kw: Workspace(**kw))
        self.assertEqual(ctx.exception.code, "E-ORG-005")

    def test_outputs_are_deterministic_across_two_identical_organisms(self):
        def fingerprint(responses):
            return [
                (
                    r.index, r.accepted, r.code, r.note, r.verdict, r.lacunae, r.contested,
                    r.withdrawn, r.satisfied, len(r.resolved), r.work_asks, r.work_scanned,
                    r.work, r.beat.beat_no, round(r.beat.charge, 12), r.beat.faults, r.beat.wants,
                    r.terminal,
                )
                for r in responses
            ]
        stream = MotivationTests.mixed_stream() + [
            retract("A2", "A3"), retract("A1", "A3"), ask("A1", "A3"), retract("ZZ", "YY"),
            hypothesis("B1", "B2"), negation("H1", "H2"), ask("H1", "H2"),
        ]
        one = Organism(motivation_kwargs={"beta": 0.2})
        two = Organism(motivation_kwargs={"beta": 0.2})
        self.assertEqual(fingerprint(one.run_stream(stream)), fingerprint(two.run_stream(stream)))
        self.assertEqual(one.standing, two.standing)
        self.assertEqual(one.wants(), two.wants())
        self.assertEqual(one.report(), two.report())

    def test_the_report_summarises_standing_wants_faults_and_beats(self):
        org = Organism()
        org.run_stream(backbone() + [ask("VS", "TR"), fact("AA", "BB"), associate("BB", "CC"), fact("CC", "DD"), ask("AA", "DD")])
        report = org.report()
        for fragment in ("standing", "VS|leads_to|TR", "wants", "BB|leads_to|CC", "faults", "beat", "work"):
            self.assertIn(fragment, report)
        self.assertEqual(str(org), report)
        self.assertIsInstance(org.log[-1], Response)
        self.assertIn("UNKNOWN", str(org.log[-1]))

    def test_the_closed_world_flag_reaches_the_workspace_and_every_problem(self):
        org = Organism(closed_world=True)
        self.assertTrue(org.ws.closed_world)
        org.run_stream([fact("VS", "QS")])
        response = org.consume(ask("VS", "IU"))
        self.assertTrue(response.episode.problem.closed_world)
        self.assertEqual(response.verdict, "NO")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
