"""The recompute oracle is correct by construction; each other control breaks one rule.

The hand streams below are the contract's §3 verdict order, §4 lacuna bounds,
§5 withdrawn column and §2 refusals worked by hand. `ctl_recompute` must
reproduce every one. Each broken control must fail the probe its rule
protects and nothing else on the same stream -- that is what makes it a
control rather than a second broken solver.

The generated-set agreement test (`ctl_recompute` versus the oracle in
`revision.py` on every probe of both worlds) lives at the bottom and is
skipped until that module exists; it is the independent re-implementation
check of the contract.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))

import controls  # noqa: E402
from controls import (  # noqa: E402
    CONTROLS,
    CORRECT_BY_CONSTRUCTION,
    INADMISSIBLE,
    NO,
    ORACLE_RULES,
    UNKNOWN,
    YES,
    Replayer,
    Rules,
    ctl_credulous,
    ctl_fixed_world,
    ctl_global_poison,
    ctl_last_writer,
    ctl_memo,
    ctl_memo_flush,
    ctl_mute,
    ctl_no_forget,
    ctl_order_blind,
    ctl_recompute,
)
from events import ask, associate, fact, hypothesis, negation, retract  # noqa: E402

CHAIN = [fact("A", "B"), fact("B", "C"), fact("C", "D")]
GAP = [fact("A", "B"), fact("C", "D")]            # B -> C missing
K = lambda s, o: f"{s}|leads_to|{o}"  # noqa: E731


def verdicts(control, events, closed=False):
    return control(events, closed).verdicts()


class VerdictOrderTests(unittest.TestCase):
    """One test per §3 rule, on `ctl_recompute`."""

    def test_rule_1_denied_but_reachable_is_a_dispute_about_the_claim_itself(self):
        for closed in (False, True):
            run = ctl_recompute(CHAIN + [negation("A", "D"), ask("A", "D")], closed)
            a = run.answers[0]
            self.assertEqual(a.verdict, INADMISSIBLE)
            self.assertEqual(a.contested, (K("A", "D"),))
            self.assertEqual(a.lacunae, ())

    def test_rule_2_a_clean_route_is_yes(self):
        for closed in (False, True):
            self.assertEqual(verdicts(ctl_recompute, CHAIN + [ask("A", "D")], closed), (YES,))

    def test_rule_3_a_disputed_only_route_is_inadmissible_and_names_the_link(self):
        for closed in (False, True):
            a = ctl_recompute(CHAIN + [negation("B", "C"), ask("A", "D")], closed).answers[0]
            self.assertEqual(a.verdict, INADMISSIBLE)
            self.assertEqual(a.contested, (K("B", "C"),))

    def test_rule_3_a_contested_pair_asked_directly_is_a_dispute_not_a_denial(self):
        """F(a,b) N(a,b) ask a->b: the denial is itself disputed, so it is not knowledge."""
        for closed in (False, True):
            a = ctl_recompute([fact("A", "B"), negation("A", "B"), ask("A", "B")], closed).answers[0]
            self.assertEqual((a.verdict, a.contested), (INADMISSIBLE, (K("A", "B"),)))

    def test_rule_3_a_denied_pair_behind_a_disputed_route_is_inadmissible(self):
        stream = [fact("A", "B"), fact("B", "C"), negation("B", "C"), negation("A", "C"), ask("A", "C")]
        for closed in (False, True):
            a = ctl_recompute(stream, closed).answers[0]
            self.assertEqual((a.verdict, a.contested), (INADMISSIBLE, (K("B", "C"),)))

    def test_rule_3_names_contested_links_on_simple_routes_only(self):
        """A contested link on a cycle through route nodes is not on any simple
        s->t route, so it is not named -- the same set ^8's walk surfaces."""
        stream = [fact("S", "A"), fact("A", "B"), fact("B", "C"), fact("C", "A"), fact("C", "T"),
                  negation("A", "B"), negation("C", "A"), ask("S", "T")]
        a = ctl_recompute(stream).answers[0]
        self.assertEqual((a.verdict, a.contested), (INADMISSIBLE, (K("A", "B"),)))

    def test_rule_4_an_explicit_denial_with_no_route_is_no_in_both_worlds(self):
        for closed in (False, True):
            a = ctl_recompute([negation("A", "D"), ask("A", "D")], closed).answers[0]
            self.assertEqual(a.verdict, NO)
            self.assertEqual(a.lacunae, (), "a denial is knowledge, not a gap")

    def test_rule_4_a_denial_outranks_a_partial_route(self):
        """A shadow or a guess completes no route; the given denial settles it."""
        for bridge in (associate("B", "C"), hypothesis("B", "C")):
            for closed in (False, True):
                a = ctl_recompute([fact("A", "B"), bridge, negation("A", "C"), ask("A", "C")], closed).answers[0]
                self.assertEqual((a.verdict, a.lacunae), (NO, ()), (bridge, closed))

    def test_rule_3_contested_required_uses_reflexive_reach_at_both_ends(self):
        first = ctl_recompute(CHAIN + [negation("A", "B"), ask("A", "D")]).answers[0]
        last = ctl_recompute(CHAIN + [negation("C", "D"), ask("A", "D")]).answers[0]
        self.assertEqual((first.verdict, first.contested), (INADMISSIBLE, (K("A", "B"),)))
        self.assertEqual((last.verdict, last.contested), (INADMISSIBLE, (K("C", "D"),)))

    def test_rule_3_names_only_disputes_on_the_route(self):
        stream = CHAIN + [negation("B", "C"), fact("X", "Y"), negation("X", "Y"), ask("A", "D")]
        a = ctl_recompute(stream).answers[0]
        self.assertEqual(a.contested, (K("B", "C"),), "X -> Y is disputed but off the route")

    def test_rule_2_beats_rule_3_when_a_clean_second_route_exists(self):
        stream = CHAIN + [fact("A", "E"), fact("E", "D"), negation("B", "C"), ask("A", "D")]
        self.assertEqual(verdicts(ctl_recompute, stream), (YES,))

    def test_rule_5_closed_world_absence_is_no(self):
        a = ctl_recompute(GAP + [ask("A", "D")], True).answers[0]
        self.assertEqual((a.verdict, a.lacunae), (NO, ()))

    def test_rule_6_open_world_absence_is_unknown(self):
        a = ctl_recompute(GAP + [ask("A", "D")], False).answers[0]
        self.assertEqual(a.verdict, UNKNOWN)


class LacunaTests(unittest.TestCase):
    def test_a_shadowed_gap_is_named(self):
        a = ctl_recompute(GAP + [associate("B", "C"), ask("A", "D")]).answers[0]
        self.assertEqual((a.verdict, a.lacunae), (UNKNOWN, (K("B", "C"),)))

    def test_a_hypothesised_gap_is_named(self):
        a = ctl_recompute(GAP + [hypothesis("B", "C"), ask("A", "D")]).answers[0]
        self.assertEqual((a.verdict, a.lacunae), (UNKNOWN, (K("B", "C"),)))

    def test_a_denied_pair_is_never_a_lacuna(self):
        stream = GAP + [associate("B", "C"), hypothesis("B", "C"), negation("B", "C"), ask("A", "D")]
        a = ctl_recompute(stream).answers[0]
        self.assertEqual(a.verdict, UNKNOWN, "a refuted guess is not a dispute")
        self.assertEqual(a.lacunae, ())

    def test_a_gap_beyond_a_contested_link_is_a_lacuna_and_the_contested_link_is_not(self):
        """The walk graph keeps the disputed link (^8 walks it); the gap past it is
        on a surfaced route and is named; the disputed link itself never is."""
        stream = [fact("A", "B"), associate("B", "C"), fact("C", "D"), negation("A", "B"), ask("A", "D")]
        a = ctl_recompute(stream).answers[0]
        self.assertEqual((a.verdict, a.lacunae, a.contested), (UNKNOWN, (K("B", "C"),), ()))

    def test_a_guess_or_denial_under_another_relation_is_refused(self):
        from events import Event, EventKind
        for kind in (EventKind.HYPOTHESIS, EventKind.NEGATION):
            with self.assertRaises(ValueError):
                ctl_recompute([Event(kind, "A", "B", "co_occurs"), ask("A", "B")])

    def test_an_off_route_hypothesis_is_not_a_lacuna(self):
        a = ctl_recompute(GAP + [hypothesis("X", "Y"), ask("A", "D")]).answers[0]
        self.assertEqual(a.lacunae, ())

    def test_a_gap_with_nothing_pointing_at_it_names_nothing(self):
        """`required` is empty; the query pair is admissible but not required."""
        a = ctl_recompute(GAP + [ask("A", "D")]).answers[0]
        self.assertEqual(a.lacunae, ())

    def test_lacunae_are_not_reported_on_other_verdicts(self):
        for stream, closed in (
            (CHAIN + [ask("A", "D")], False),
            (CHAIN + [negation("B", "C"), associate("B", "C"), ask("A", "D")], False),
            (GAP + [associate("B", "C"), ask("A", "D")], True),
        ):
            self.assertEqual(ctl_recompute(stream, closed).answers[0].lacunae, ())


class TransitionTests(unittest.TestCase):
    def test_retract_of_a_derived_only_pair_is_refused_and_changes_nothing(self):
        run = ctl_recompute(CHAIN + [ask("A", "D"), retract("A", "D"), ask("A", "D")])
        self.assertEqual(run.refused, (4,))
        self.assertEqual(run.verdicts(), (YES, YES))

    def test_retract_of_what_was_never_given_is_refused(self):
        self.assertEqual(ctl_recompute([retract("A", "B")]).refused, (0,))

    def test_retract_of_a_contested_pair_leaves_it_merely_denied(self):
        stream = CHAIN + [negation("B", "C"), retract("B", "C"), ask("A", "D"), ask("B", "C")]
        run = ctl_recompute(stream)
        self.assertEqual(run.refused, ())
        self.assertEqual(run.verdicts(), (UNKNOWN, NO))

    def test_a_hypothesis_against_a_known_fact_or_denial_is_a_no_op(self):
        a = ctl_recompute(GAP + [negation("B", "C"), hypothesis("B", "C"), ask("A", "D")]).answers[0]
        self.assertEqual((a.verdict, a.lacunae), (UNKNOWN, ()))
        b = ctl_recompute(CHAIN + [hypothesis("B", "C"), retract("B", "C"), ask("A", "D")]).answers[0]
        self.assertEqual((b.verdict, b.lacunae), (UNKNOWN, ()), "the guess did not survive the fact")

    def test_a_fact_confirms_and_absorbs_a_hypothesis(self):
        run = ctl_recompute(GAP + [hypothesis("B", "C"), ask("A", "D"), fact("B", "C"), ask("A", "D")])
        self.assertEqual(run.verdicts(), (UNKNOWN, YES))

    def test_a_retracted_fact_can_be_re_asserted(self):
        run = ctl_recompute(CHAIN + [ask("A", "D"), retract("B", "C"), ask("A", "D"), fact("B", "C"), ask("A", "D")])
        self.assertEqual(run.verdicts(), (YES, UNKNOWN, YES))


class WithdrawnTests(unittest.TestCase):
    def test_an_earlier_yes_that_falls_is_reported_at_the_event_that_felled_it(self):
        run = ctl_recompute(CHAIN + [ask("A", "D"), ask("B", "D"), retract("B", "C")])
        self.assertEqual(run.withdrawn, (controls.Withdrawn(5, (K("A", "D"), K("B", "D"))),))

    def test_an_off_route_retraction_withdraws_nothing(self):
        run = ctl_recompute(CHAIN + [fact("X", "Y"), ask("A", "D"), retract("X", "Y")])
        self.assertEqual(run.withdrawn, (controls.Withdrawn(5, ()),))

    def test_a_negation_can_withdraw_too(self):
        run = ctl_recompute(CHAIN + [ask("A", "D"), negation("B", "C")])
        self.assertEqual(run.withdrawn[0].keys, (K("A", "D"),))

    def test_a_withdrawn_answer_is_not_withdrawn_twice(self):
        run = ctl_recompute(CHAIN + [ask("A", "D"), retract("B", "C"), retract("C", "D")])
        self.assertEqual([w.keys for w in run.withdrawn], [(K("A", "D"),), ()])


class PairedWorldTests(unittest.TestCase):
    STREAM = (
        CHAIN
        + [ask("A", "D"), negation("A", "Z"), ask("A", "Z"), ask("A", "Q"),
           associate("D", "Q"), ask("A", "Q"), negation("B", "C"), ask("A", "D"), ask("B", "D")]
    )

    def test_open_and_closed_differ_only_by_unknown_to_no_and_emptied_lacunae(self):
        open_run = ctl_recompute(self.STREAM, False)
        closed_run = ctl_recompute(self.STREAM, True)
        self.assertEqual(len(open_run.answers), len(closed_run.answers))
        changed = 0
        for o, c in zip(open_run.answers, closed_run.answers):
            self.assertEqual((o.subject, o.obj, o.event_index), (c.subject, c.obj, c.event_index))
            self.assertEqual(o.contested, c.contested)
            if o.verdict == UNKNOWN:
                changed += 1
                self.assertEqual(c.verdict, NO)
                self.assertEqual(c.lacunae, ())
            else:
                self.assertEqual(o.verdict, c.verdict)
                self.assertEqual(o.lacunae, c.lacunae)
        self.assertGreater(changed, 0)
        self.assertEqual(open_run.refused, closed_run.refused)


class OneRuleAtATimeTests(unittest.TestCase):
    def test_every_control_differs_from_the_oracle_in_at_most_one_rule(self):
        for c in CONTROLS:
            diff = c.rules.differences(ORACLE_RULES)
            if c.name == "ctl_recompute":
                self.assertEqual(diff, (), c.name)
            else:
                self.assertEqual(len(diff), 1, f"{c.name} differs in {diff}")

    def test_control_names_are_unique_and_the_headline_is_first(self):
        names = [c.name for c in CONTROLS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names[0], "ctl_recompute")
        self.assertEqual(set(CORRECT_BY_CONSTRUCTION), {"ctl_recompute", "ctl_memo_flush"})

    def test_an_unknown_memo_rule_is_refused(self):
        with self.assertRaises(ValueError):
            Replayer("bad", Rules(memo="sometimes"))

    def test_the_memo_flush_control_agrees_with_the_headline_on_every_hand_stream(self):
        streams = [
            CHAIN + [ask("A", "D"), retract("B", "C"), ask("A", "D"), fact("B", "C"), ask("A", "D")],
            GAP + [associate("B", "C"), ask("A", "D"), fact("B", "C"), ask("A", "D")],
            CHAIN + [ask("A", "D"), negation("B", "C"), ask("A", "D"), retract("B", "C"), ask("A", "D")],
            PairedWorldTests.STREAM,
        ]
        for stream in streams:
            for closed in (False, True):
                a = ctl_recompute(stream, closed)
                b = ctl_memo_flush(stream, closed)
                self.assertEqual([(x.verdict, x.lacunae, x.contested) for x in a.answers],
                                 [(x.verdict, x.lacunae, x.contested) for x in b.answers])
                self.assertEqual(a.refused, b.refused)


class BrokenControlTests(unittest.TestCase):
    """Each broken control fails the probe its rule protects, and only that one."""

    R_STALE = CHAIN + [ask("A", "D"), retract("B", "C"), fact("X", "Y"), ask("A", "D")]
    R_REVIVE = CHAIN + [ask("A", "D"), retract("B", "C"), fact("B", "C"), ask("A", "D")]
    R_CONTROL = CHAIN + [fact("X", "Y"), ask("A", "D"), retract("X", "Y"), ask("A", "D")]
    H_BRIDGE = GAP + [hypothesis("B", "C"), ask("A", "D")]
    H_REFUTE = GAP + [hypothesis("B", "C"), negation("B", "C"), ask("A", "D")]
    H_CONTROL = CHAIN + [hypothesis("X", "Y"), ask("A", "D")]
    C_BLOCKED = CHAIN + [negation("B", "C"), ask("A", "D")]
    C_BYPASSED = CHAIN + [fact("A", "E"), fact("E", "D"), negation("B", "C"), ask("A", "D")]
    C_UNRELATED = CHAIN + [fact("X", "Y"), negation("X", "Y"), ask("A", "D")]
    N_GAP = GAP + [associate("B", "C"), ask("A", "D")]

    def test_order_blind_fails_exactly_the_stale_probe(self):
        self.assertEqual(verdicts(ctl_recompute, self.R_STALE), (YES, UNKNOWN))
        self.assertEqual(verdicts(ctl_order_blind, self.R_STALE), (UNKNOWN, UNKNOWN))
        self.assertEqual(verdicts(ctl_order_blind, self.R_REVIVE), verdicts(ctl_recompute, self.R_REVIVE))
        self.assertEqual(verdicts(ctl_order_blind, self.R_CONTROL), verdicts(ctl_recompute, self.R_CONTROL))

    def test_no_forget_keeps_saying_yes_after_the_support_is_withdrawn(self):
        self.assertEqual(verdicts(ctl_no_forget, self.R_STALE), (YES, YES))
        self.assertEqual(verdicts(ctl_no_forget, self.R_CONTROL), (YES, YES))
        self.assertEqual(ctl_no_forget(self.R_STALE).refused, (), "it still accepts the retract; it just does nothing")

    def test_credulous_turns_a_guess_into_a_yes_and_a_refuted_guess_into_a_dispute(self):
        self.assertEqual(verdicts(ctl_recompute, self.H_BRIDGE), (UNKNOWN,))
        self.assertEqual(verdicts(ctl_credulous, self.H_BRIDGE), (YES,))
        self.assertEqual(verdicts(ctl_recompute, self.H_REFUTE), (UNKNOWN,))
        self.assertEqual(verdicts(ctl_credulous, self.H_REFUTE), (INADMISSIBLE,))
        self.assertEqual(verdicts(ctl_credulous, self.H_CONTROL), (YES,))

    def test_last_writer_never_reports_a_dispute(self):
        self.assertEqual(verdicts(ctl_recompute, self.C_BLOCKED), (INADMISSIBLE,))
        self.assertEqual(verdicts(ctl_last_writer, self.C_BLOCKED), (UNKNOWN,))
        self.assertEqual(verdicts(ctl_last_writer, self.C_BLOCKED, True), (NO,))
        self.assertEqual(verdicts(ctl_last_writer, self.C_BYPASSED), (YES,))
        self.assertEqual(verdicts(ctl_last_writer, self.C_UNRELATED), (YES,))

    def test_global_poison_refuses_an_unrelated_question(self):
        self.assertEqual(verdicts(ctl_recompute, self.C_UNRELATED), (YES,))
        self.assertEqual(verdicts(ctl_global_poison, self.C_UNRELATED), (INADMISSIBLE,))
        self.assertEqual(verdicts(ctl_global_poison, self.C_BYPASSED), (INADMISSIBLE,))
        self.assertEqual(verdicts(ctl_global_poison, self.C_BLOCKED), (INADMISSIBLE,))

    def test_mute_gets_the_verdict_and_names_nothing(self):
        a = ctl_mute(self.N_GAP).answers[0]
        self.assertEqual((a.verdict, a.lacunae), (UNKNOWN, ()))
        self.assertEqual(ctl_recompute(self.N_GAP).answers[0].lacunae, (K("B", "C"),))

    def test_fixed_world_is_perfect_open_and_wrong_on_closure_probes(self):
        for stream in (self.N_GAP, self.R_STALE, self.H_BRIDGE):
            self.assertEqual(verdicts(ctl_fixed_world, stream, False), verdicts(ctl_recompute, stream, False))
        self.assertEqual(verdicts(ctl_recompute, self.N_GAP, True), (NO,))
        self.assertEqual(verdicts(ctl_fixed_world, self.N_GAP, True), (UNKNOWN,))
        self.assertEqual(verdicts(ctl_fixed_world, self.C_BLOCKED, True), (INADMISSIBLE,), "not a closure probe")

    def test_memo_repeats_its_first_answer_and_memo_flush_does_not(self):
        self.assertEqual(verdicts(ctl_memo, self.R_STALE), (YES, YES))
        self.assertEqual(verdicts(ctl_memo_flush, self.R_STALE), (YES, UNKNOWN))
        self.assertEqual(verdicts(ctl_memo, self.R_REVIVE), (YES, YES), "right by accident: the first answer happened to hold")
        self.assertEqual(ctl_memo(self.R_STALE).answers[1].work, 1, "a memo hit costs one read")

    def test_memo_never_withdraws(self):
        self.assertEqual([w.keys for w in ctl_memo(self.R_STALE).withdrawn], [()])
        self.assertEqual([w.keys for w in ctl_memo_flush(self.R_STALE).withdrawn], [(K("A", "D"),)])


class CostTests(unittest.TestCase):
    def test_recompute_work_grows_with_the_graph(self):
        short = ctl_recompute(CHAIN + [ask("A", "D")]).answers[0].work
        # A branch off the source that never reaches the target: the walk must
        # still visit it. (A disconnected component would, correctly, cost nothing.)
        long_chain = [fact("A", "N0")] + [fact(f"N{i}", f"N{i+1}") for i in range(12)] + CHAIN
        long = ctl_recompute(long_chain + [ask("A", "D")]).answers[0].work
        self.assertGreater(short, 0)
        self.assertGreater(long, short)

    def test_recompute_pays_the_walk_again_on_a_repeat_ask(self):
        run = ctl_recompute(CHAIN + [ask("A", "D"), ask("A", "D")])
        self.assertEqual(run.answers[0].work, run.answers[1].work)
        self.assertEqual(run.work, sum(a.work for a in run.answers))


class PurityTests(unittest.TestCase):
    def test_the_controls_import_only_stdlib_and_events(self):
        source = Path(controls.__file__).read_text()
        for line in source.splitlines():
            line = line.strip()
            if line.startswith("from ") and " import " in line:
                module = line.split()[1].split(".")[0]
                self.assertIn(module, {"__future__", "collections", "dataclasses", "typing", "events"}, line)
            self.assertFalse(line.startswith("import "), line)


class GeneratedSetAgreementTests(unittest.TestCase):
    """`ctl_recompute` is an independent implementation of the same contract the
    oracle in `revision.py` implements. On every probe of generated sets in both
    worlds they must agree on verdict, contested keys and the lacuna bounds."""

    def setUp(self):
        try:
            import revision  # noqa: F401
        except ImportError:
            self.skipTest("revision.py not present yet")

    def test_recompute_agrees_with_the_oracle_on_every_probe(self):
        from revision import StreamDifficulty, generate_revision_set

        for closed in (False, True):
            stream_set = generate_revision_set(24, seed=20261006, difficulty=StreamDifficulty(), closed_world=closed)
            for item in stream_set.items:
                run = ctl_recompute(item.events, closed)
                self.assertEqual(len(run.answers), len(item.expectations), item.item_id)
                for ans, exp in zip(run.answers, item.expectations):
                    self.assertEqual(ans.event_index, exp.event_index, item.item_id)
                    self.assertEqual(ans.verdict, exp.verdict, f"{item.item_id} @ {exp.event_index}")
                    self.assertEqual(ans.contested, tuple(exp.contested_required), item.item_id)
                    if exp.verdict == UNKNOWN:
                        self.assertTrue(set(exp.lacunae_required) <= set(ans.lacunae) <= set(exp.lacunae_admissible),
                                        f"{item.item_id}: {ans.lacunae} vs [{exp.lacunae_required}, {exp.lacunae_admissible}]")
                self.assertEqual(run.refused, tuple(item.refused) if hasattr(item, "refused") else run.refused)


if __name__ == "__main__":
    unittest.main()
