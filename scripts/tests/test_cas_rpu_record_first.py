"""The guarded positive-answer path: a held YES served without a walk, never a stale one.

Memory contract M8. The flag is off by default and the organism is then PR #248's
walk-first reasoner unchanged. On, only a still-valid held YES is served from
the record; NO, UNKNOWN, INADMISSIBLE and every uncertain check fall back to
the walk and say why. The hard law is the same as the motivation's: the flag
may change how an answer is reached and what it costs; it may never change
the answer.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from ablations import NoCascade  # noqa: E402
from events import ask, fact, negation, retract  # noqa: E402
from history import Stream  # noqa: E402
from organism import Organism, OrganismError  # noqa: E402
from revision import generate_revision_set  # noqa: E402

CHAIN = [fact("A", "B"), fact("B", "C"), fact("C", "D")]
K = "A|leads_to|D"


def verdict_triples(responses):
    return [(r.verdict, r.lacunae, r.contested) for r in responses if r.verdict is not None]


class HardLawTests(unittest.TestCase):
    def test_record_first_never_changes_an_answer_on_generated_streams(self):
        """Both invalidation modes, both worlds: identical verdicts, lacunae and
        contested keys on every probe, and at least one hit so the law is not vacuous."""
        for closed in (False, True):
            sset = generate_revision_set(40, seed=20261006, closed_world=closed)
            for mode in ("context", "dependency"):
                hits = 0
                for item in sset.items:
                    walk = Organism(closed_world=closed).run_stream(item.events)
                    rf = Organism(closed_world=closed, record_first=True, record_invalidation=mode).run_stream(item.events)
                    self.assertEqual(verdict_triples(walk), verdict_triples(rf), (closed, mode, item.item_id))
                    hits += sum(1 for r in rf if r.route == "hit")
                    self.assertFalse(any(r.beat.faults for r in rf), item.item_id)
                if mode == "dependency":
                    self.assertGreater(hits, 0, (closed, mode), )
                # Context mode may legitimately hit nowhere: the generator interleaves
                # unrelated facts before most probes, which is exactly what whole-context
                # invalidation refuses. Reported by the experiment, not asserted here.

    def test_dependency_invalidation_serves_more_hits_than_context_invalidation_never_fewer(self):
        sset = generate_revision_set(40, seed=20261006)
        ctx = dep = 0
        for item in sset.items:
            ctx += sum(1 for r in Organism(record_first=True, record_invalidation="context").run_stream(item.events) if r.route == "hit")
            dep += sum(1 for r in Organism(record_first=True, record_invalidation="dependency").run_stream(item.events) if r.route == "hit")
        self.assertGreaterEqual(dep, ctx)


class HitTests(unittest.TestCase):
    def test_a_hit_answers_without_a_walk_and_reports_its_work(self):
        org = Organism(record_first=True)
        org.run_stream(CHAIN)
        first = org.consume(ask("A", "D"))
        self.assertEqual((first.verdict, first.route), ("YES", "miss"))
        self.assertGreater(first.work_asks, 0, "the first answer walked")
        again = org.consume(ask("A", "D"))
        self.assertEqual((again.verdict, again.route), ("YES", "hit"))
        self.assertEqual((again.work_asks, again.work_scanned), (0, 0), "no walk, no workspace asks")
        self.assertEqual(again.records_examined, 1)
        self.assertEqual(again.dependency_edges_checked, 4, "the conclusion and its three roots")
        self.assertEqual(again.work, 4)
        self.assertIsNone(again.episode)
        self.assertEqual(org.record_stats, {"hit": 1, "miss": 1, "rejected": 0})

    def test_with_the_flag_off_every_ask_walks(self):
        org = Organism()
        org.run_stream(CHAIN + [ask("A", "D")])
        r = org.consume(ask("A", "D"))
        self.assertEqual(r.route, "disabled")
        self.assertGreater(r.work_asks, 0)

    def test_an_unknown_mode_is_refused(self):
        with self.assertRaises(OrganismError) as ctx:
            Organism(record_first=True, record_invalidation="sometimes")
        self.assertEqual(ctx.exception.code, "E-ORG-006")

    def test_a_hit_does_not_touch_the_workspace(self):
        org = Organism(record_first=True)
        org.run_stream(CHAIN + [ask("A", "D")])
        before = {pid: p.status for pid, p in org.ws.props.items()}
        org.consume(ask("A", "D"))
        self.assertEqual({pid: p.status for pid, p in org.ws.props.items()}, before)


class NoStaleAnswerTests(unittest.TestCase):
    def test_a_retracted_support_means_a_miss_never_a_hit(self):
        org = Organism(record_first=True, record_invalidation="dependency")
        org.run_stream(CHAIN + [ask("A", "D")])
        org.consume(retract("B", "C"))
        r = org.consume(ask("A", "D"))
        self.assertEqual((r.verdict, r.route), ("UNKNOWN", "miss"), "the cascade removed the standing record")

    def test_a_denied_link_means_a_miss_and_an_inadmissible_walk(self):
        org = Organism(record_first=True, record_invalidation="dependency")
        org.run_stream(CHAIN + [ask("A", "D")])
        org.consume(negation("B", "C"))
        r = org.consume(ask("A", "D"))
        self.assertEqual((r.verdict, r.route), ("INADMISSIBLE", "miss"))

    def test_a_denied_conclusion_is_never_served_from_the_record(self):
        org = Organism(record_first=True, record_invalidation="dependency")
        org.run_stream(CHAIN + [ask("A", "D")])
        org.consume(negation("A", "D"))
        r = org.consume(ask("A", "D"))
        self.assertEqual(r.verdict, "INADMISSIBLE")
        self.assertNotEqual(r.route, "hit")

    def test_a_revived_given_does_not_revive_the_record_until_re_derived(self):
        org = Organism(record_first=True, record_invalidation="dependency")
        org.run_stream(CHAIN + [ask("A", "D"), retract("B", "C"), fact("B", "C")])
        r = org.consume(ask("A", "D"))
        self.assertEqual((r.verdict, r.route), ("YES", "miss"), "re-derived by the walk, then held again")
        self.assertEqual(org.consume(ask("A", "D")).route, "hit")

    def test_context_invalidation_rejects_after_any_mutation(self):
        org = Organism(record_first=True, record_invalidation="context")
        org.run_stream(CHAIN + [ask("A", "D"), fact("X", "Y")])
        r = org.consume(ask("A", "D"))
        self.assertEqual((r.verdict, r.route), ("YES", "rejected:context-changed"))
        self.assertEqual(org.consume(ask("A", "D")).route, "hit", "the walk refreshed the record")

    def test_a_broken_cascade_is_rejected_by_the_record_check(self):
        """Under the no-cascade ablation a disputed link leaves the derived conclusion
        standing on a dead root. The record check refuses it (the heartbeat has
        faulted, and the root is dead), so the fast path never serves it. The walk
        that follows reproduces the ablation's own known defect (`^8` walks the
        DERIVED edge and `^9` lands it as a direct hit): the fast path adds no stale
        answer beyond what walk-first already gives under the same broken rule."""
        org = Organism(record_first=True, record_invalidation="dependency", workspace_factory=NoCascade)
        org.run_stream(CHAIN + [ask("A", "D")])
        org.consume(negation("B", "C"))
        self.assertTrue(org.faults, "the heartbeat caught the dead root")
        r = org.consume(ask("A", "D"))
        self.assertTrue(r.route.startswith("rejected:"), r.route)
        self.assertNotEqual(r.route, "hit")
        walk_only = Organism(workspace_factory=NoCascade)
        walk_only.run_stream(CHAIN + [ask("A", "D"), negation("B", "C")])
        self.assertEqual(r.verdict, walk_only.consume(ask("A", "D")).verdict, "identical to walk-first under the same ablation")


class AcrossRestartTests(unittest.TestCase):
    def test_the_flag_is_identity_and_a_restored_stream_hits_from_the_replayed_record(self):
        with tempfile.TemporaryDirectory() as d:
            s = Stream.genesis(d, organism_id="o", context_id="c", record_first=True, record_invalidation="dependency")
            s.run(CHAIN + [ask("A", "D")])
            restored = Stream.restore(d, expected=s.identity)
            self.assertTrue(restored.organism.record_first)
            r = restored.commit(ask("A", "D"))
            self.assertEqual((r.verdict, r.route), ("YES", "hit"))
            restored.commit(retract("C", "D"))
            self.assertEqual(restored.commit(ask("A", "D")).verdict, "UNKNOWN")
            again = Stream.restore(d, expected=s.identity)
            self.assertEqual(again.commit(ask("A", "D")).verdict, "UNKNOWN", "no stale YES after restart either")


if __name__ == "__main__":
    unittest.main()
