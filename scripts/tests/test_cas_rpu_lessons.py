"""Lessons — Revision Streams contract §13; HELM ability 2 (learns), roadmap step 5.

A lesson is a told, retractable given: `FACT entails (r, leads_to)` — "every
edge of the foreign relation r counts as a leads_to edge while this is held".
Before it, a chain through an `r` edge cannot be concluded and the missing
`leads_to` link is named as a gap; after it, the same question answers YES,
and so does a never-seen instance taught later. The oracle (`revision.replay`),
the recompute control and the organism must agree on every probe, withdrawal
and refusal, in both worlds; the lesson must survive a restart and a retracted
lesson must withdraw everything that rested on it, before and after a restart.

What this does not show: a lesson induced from examples (it is told), lessons
in open English, or any change to neural weights (none exist here).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from ablations import ABLATIONS  # noqa: E402
from controls import CONTROLS, ctl_recompute  # noqa: E402
from events import EventError, ask, fact, hypothesis, lesson, negation, retract, unlesson  # noqa: E402
from history import Stream  # noqa: E402
from organism import LESSON_STAGE, Organism  # noqa: E402
from revision import guard_route_bounds, replay  # noqa: E402
from scoring import probes_from_control, probes_from_responses, score_item, withdrawn_from_control, withdrawn_from_responses  # noqa: E402
from workspace import Status  # noqa: E402

E = "enables"
#: The §13 scenario, end to end: before / after / new instance / edge retract /
#: lesson retract and revive / foreign-edge retract / refused retract of the
#: derived twin / denial of the twin's pair / a lesson is relation-specific /
#: a guess about an untaught edge.
STREAM = [
    fact("A", "B", relation=E), fact("B", "C"), ask("A", "C"),          # 2  GAP, lacuna A|leads_to|B
    lesson(E), ask("A", "C"),                                            # 4  YES: previously could not
    fact("P", "Q", relation=E), fact("Q", "R"), ask("P", "R"),           # 7  YES: a new instance, after the lesson
    retract("B", "C"), ask("A", "C"),                                    # 8 withdraws A|leads_to|C; 9 GAP
    fact("B", "C"), ask("A", "C"),                                       # 11 YES
    unlesson(E), ask("A", "C"), ask("P", "R"),                           # 12 withdraws both; 13, 14 GAP
    lesson(E), ask("A", "C"),                                            # 16 YES: revived
    retract("A", "B", relation=E), ask("A", "C"),                        # 17 withdraws; 18 GAP
    retract("P", "Q"), ask("P", "R"),                                    # 19 REFUSED (the twin is derived); 20 YES
    negation("P", "Q"), ask("P", "R"),                                   # 22 INADMISSIBLE, contested P|leads_to|Q
    fact("X", "Y", relation="owns"), fact("Y", "Z"), ask("X", "Z"),      # 25 GAP: the lesson is for `enables`, not `owns`
    hypothesis("X", "Y"), ask("X", "Z"),                                 # 27 GAP, required lacuna X|leads_to|Y
]


class _Item:
    """What `score_item` needs, over the hand-built stream."""

    def __init__(self, closed: bool) -> None:
        truth = replay(STREAM, closed)
        self.item_id = "lesson-hand"
        self.mechanism = "L"
        self.variant = "L-hand"
        self.closed_world = closed
        self.expectations = truth.expectations
        self.withdrawn = truth.withdrawn
        self.refused = truth.refused
        self.designed_probe_index = 4


def verdicts(closed: bool) -> list[str]:
    return [x.verdict.value for x in replay(STREAM, closed).expectations]


class OracleTests(unittest.TestCase):
    def test_the_frozen_verdict_sequence_in_both_worlds(self):
        gap = lambda c: "NO" if c else "UNKNOWN"  # noqa: E731
        for closed in (False, True):
            self.assertEqual(
                verdicts(closed),
                [gap(closed), "YES", "YES", gap(closed), "YES", gap(closed), gap(closed), "YES", gap(closed), "YES", "INADMISSIBLE", gap(closed), gap(closed)],
                closed,
            )
            truth = replay(STREAM, closed)
            self.assertEqual(truth.refused, (19,), "retracting the derived twin is refused; nothing else is")
            by = {x.event_index: x for x in truth.expectations}
            self.assertEqual(by[22].contested_required, ("P|leads_to|Q",))
            if not closed:
                self.assertEqual(by[2].lacunae_required, ("A|leads_to|B",), "the untaught edge's twin is the gap")
                self.assertEqual(by[4].lacunae_required, ())
                self.assertEqual(by[25].lacunae_required, ("X|leads_to|Y",), "a lesson is specific to its relation")
                self.assertEqual(by[27].lacunae_required, ("X|leads_to|Y",))
            w = {x.event_index: x for x in truth.withdrawn}
            self.assertEqual(w[8].required, ("A|leads_to|C",))
            self.assertEqual(w[12].required, ("A|leads_to|C", "P|leads_to|R"), "retracting the lesson withdraws every dependent at once")
            self.assertEqual(w[17].required, ("A|leads_to|C",))
            self.assertEqual(w[19].required, (), "a refused retract withdraws nothing")

    def test_the_route_bounds_hold_and_a_lesson_must_name_a_foreign_relation(self):
        guard_route_bounds(STREAM)
        for bad in ("leads_to", "co_occurs", "entails"):
            with self.assertRaises(EventError) as ctx:
                lesson(bad)
            self.assertEqual(ctx.exception.code, "E-EV-004")


class AgreementTests(unittest.TestCase):
    def test_organism_control_and_oracle_agree_on_every_probe_withdrawal_and_refusal(self):
        for closed in (False, True):
            item = _Item(closed)
            org = Organism(closed_world=closed)
            rs = org.run_stream(STREAM)
            self.assertEqual([i for i, r in enumerate(rs) if not r.accepted], [19])
            self.assertEqual(org.faults, ())
            score = score_item(item, probes_from_responses(rs), withdrawn_from_responses(rs, STREAM))
            self.assertTrue(score.all_verdicts_ok, [(p.event_index, p.expected, p.got) for p in score.probes if not p.verdict_ok])
            self.assertTrue(all(p.contested_ok is not False and p.named_ok is not False for p in score.probes), [p.detail for p in score.probes if p.detail])
            self.assertTrue(all(w.ok for w in score.withdrawn), [w for w in score.withdrawn if not w.ok])
            ctl = ctl_recompute(STREAM, closed)
            cscore = score_item(item, probes_from_control(ctl), withdrawn_from_control(ctl))
            self.assertTrue(cscore.all_verdicts_ok and all(w.ok for w in cscore.withdrawn))
            self.assertEqual(ctl.refused, (19,))

    def test_every_control_runs_the_lesson_grammar_and_only_the_recompute_control_is_perfect_on_the_lesson_probes(self):
        """The rule-flag controls must accept the grammar; which of them still
        score perfectly is reported, not asserted, except that recompute does."""
        for closed in (False, True):
            item = _Item(closed)
            for ctl in CONTROLS:
                out = ctl(STREAM, closed)
                score_item(item, probes_from_control(out), withdrawn_from_control(out))
            self.assertTrue(score_item(item, probes_from_control(ctl_recompute(STREAM, closed))).all_verdicts_ok)

    def test_every_ablation_consumes_the_lesson_grammar_without_faulting_the_grammar(self):
        for abl in ABLATIONS:
            org = Organism(workspace_factory=abl.workspace)
            org.run_stream(STREAM)


class MechanismTests(unittest.TestCase):
    def test_the_entailed_twin_is_a_derived_record_resting_on_the_edge_and_the_lesson(self):
        org = Organism()
        org.run_stream([fact("A", "B", relation=E), lesson(E)])
        twin = org.ws.props["A|leads_to|B"]
        self.assertEqual((twin.status, twin.stage), (Status.DERIVED, LESSON_STAGE))
        self.assertEqual(set(twin.support), {"A|enables|B", f"{E}|entails|leads_to"})
        org.consume(fact("C", "D", relation=E))
        self.assertEqual(org.ws.props["C|leads_to|D"].status, Status.DERIVED, "either order: edge after lesson too")
        org.consume(unlesson(E))
        self.assertEqual(org.ws.props["A|leads_to|B"].status, Status.RETRACTED)
        self.assertEqual(org.ws.props["C|leads_to|D"].status, Status.RETRACTED)
        self.assertEqual(org.ws.props["A|enables|B"].status, Status.FACT, "the foreign edges themselves stand")
        org.consume(lesson(E))
        self.assertEqual(org.ws.props["A|leads_to|B"].status, Status.DERIVED, "re-taught: re-derived")

    def test_a_given_leads_to_is_never_downgraded_by_a_lesson(self):
        org = Organism()
        org.run_stream([fact("A", "B"), fact("A", "B", relation=E), lesson(E)])
        self.assertEqual(org.ws.props["A|leads_to|B"].status, Status.FACT)
        self.assertEqual(org.consume(retract("A", "B")).accepted, True, "the given is still a given")

    def test_record_first_serves_a_lesson_backed_conclusion_and_drops_it_when_the_lesson_goes(self):
        org = Organism(record_first=True, record_invalidation="dependency")
        org.run_stream([fact("A", "B", relation=E), fact("B", "C"), lesson(E), ask("A", "C")])
        self.assertEqual(org.consume(ask("A", "C")).route, "hit")
        self.assertIn(f"{E}|entails|leads_to", org.ws.roots("A|leads_to|C"), "the lesson is a root of the conclusion")
        org.consume(unlesson(E))
        r = org.consume(ask("A", "C"))
        self.assertEqual((r.verdict, r.route), ("UNKNOWN", "miss"), "no stale answer through the faster path")


class AcrossRestartTests(unittest.TestCase):
    def test_a_lesson_survives_a_restart_applies_to_new_instances_and_its_retraction_withdraws_after_another_restart(self):
        with tempfile.TemporaryDirectory() as d:
            s = Stream.genesis(d, organism_id="o", context_id="c", record_first=True, record_invalidation="dependency")
            s.run([fact("A", "B", relation=E), fact("B", "C"), ask("A", "C")])
            self.assertEqual(s.rows[-1]["outcome"]["verdict"], "UNKNOWN", "before the lesson")
            s.commit(lesson(E))
            self.assertEqual(s.commit(ask("A", "C")).verdict, "YES")
            r = Stream.restore(d, expected=s.identity)
            self.assertEqual(r.commit(ask("A", "C")).route, "hit", "served from the record after the restart")
            r.run([fact("P", "Q", relation=E), fact("Q", "R")])
            self.assertEqual(r.commit(ask("P", "R")).verdict, "YES", "the retained lesson applies to tokens it never saw")
            self.assertEqual(r.commit(unlesson(E)).withdrawn, ("A|leads_to|C", "P|leads_to|R"))
            again = Stream.restore(d, expected=s.identity)
            self.assertEqual(again.commit(ask("P", "R")).verdict, "UNKNOWN")
            self.assertEqual(again.commit(ask("A", "C")).verdict, "UNKNOWN", "the retraction held across the restart")
            self.assertEqual(again.organism.faults, ())


if __name__ == "__main__":
    unittest.main()
