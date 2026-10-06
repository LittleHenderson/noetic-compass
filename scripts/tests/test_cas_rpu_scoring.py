"""Scoring is per probe, bounded where the contract says bounded, and never 0/0 = 100%.

The items here are hand-built stand-ins with the field names contract §2–§5
fix, so the scorer is tested on its own terms. It binds to the real
`revision.StreamItem` through those same names.
"""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))

from controls import ctl_recompute  # noqa: E402
from events import ask, fact, retract  # noqa: E402
from scoring import (  # noqa: E402
    INADMISSIBLE,
    NO,
    UNKNOWN,
    YES,
    Cell,
    Matrix,
    Probe,
    ScoringError,
    WithdrawnReport,
    probes_from_control,
    probes_from_responses,
    score_item,
    withdrawn_from_control,
    withdrawn_from_responses,
)


@dataclass(frozen=True)
class Exp:
    event_index: int
    subject: str
    obj: str
    verdict: str
    lacunae_required: tuple[str, ...] = ()
    lacunae_admissible: tuple[str, ...] = ()
    contested_required: tuple[str, ...] = ()


@dataclass(frozen=True)
class Wd:
    event_index: int
    required: tuple[str, ...]
    permitted: tuple[str, ...]


@dataclass(frozen=True)
class Item:
    item_id: str
    mechanism: str
    variant: str
    closed_world: bool
    events: tuple
    expectations: tuple
    withdrawn: tuple = ()
    designed_probe_index: int = -1


L = "B|leads_to|C"
Q = "A|leads_to|D"


class ProbeColumnTests(unittest.TestCase):
    def test_verdict_is_scored_on_every_probe(self):
        item = Item("i", "R", "R-stale", False, (), (Exp(3, "A", "D", YES), Exp(6, "A", "D", UNKNOWN)), designed_probe_index=6)
        score = score_item(item, [Probe(3, YES), Probe(6, YES)])
        self.assertEqual([p.verdict_ok for p in score.probes], [True, False])
        self.assertEqual([p.designed for p in score.probes], [False, True])
        self.assertFalse(score.all_verdicts_ok)

    def test_contested_is_scored_only_on_inadmissible_and_is_set_equality(self):
        item = Item("i", "C", "C-blocked", False, (), (Exp(4, "A", "D", INADMISSIBLE, contested_required=(L,)), Exp(5, "A", "D", YES)))
        score = score_item(item, [Probe(4, INADMISSIBLE, contested=(L,)), Probe(5, YES, contested=("junk",))])
        self.assertEqual([p.contested_ok for p in score.probes], [True, None])
        worse = score_item(item, [Probe(4, INADMISSIBLE, contested=(L, Q)), Probe(5, YES)])
        self.assertIs(worse.probes[0].contested_ok, False)
        self.assertIn("contested", worse.probes[0].detail)
        wrong = score_item(item, [Probe(4, UNKNOWN), Probe(5, YES)])
        self.assertIsNone(wrong.probes[0].contested_ok, "a wrong verdict is not counted twice")

    def test_named_is_bounded_and_only_on_open_world_unknown(self):
        exp = Exp(3, "A", "D", UNKNOWN, lacunae_required=(L,), lacunae_admissible=(L, Q))
        item = Item("i", "N", "N-gap", False, (), (exp,))
        self.assertIs(score_item(item, [Probe(3, UNKNOWN, lacunae=(L,))]).probes[0].named_ok, True)
        self.assertIs(score_item(item, [Probe(3, UNKNOWN, lacunae=(L, Q))]).probes[0].named_ok, True)
        nothing = score_item(item, [Probe(3, UNKNOWN, lacunae=())]).probes[0]
        self.assertIs(nothing.named_ok, False)
        self.assertIn("missing " + L, nothing.detail)
        too_much = score_item(item, [Probe(3, UNKNOWN, lacunae=(L, "X|leads_to|Y"))]).probes[0]
        self.assertIs(too_much.named_ok, False)
        self.assertIn("inadmissible X|leads_to|Y", too_much.detail)
        closed = Item("i", "N", "N-gap", True, (), (Exp(3, "A", "D", NO),))
        self.assertIsNone(score_item(closed, [Probe(3, NO)]).probes[0].named_ok)
        self.assertIsNone(score_item(item, [Probe(3, YES)]).probes[0].named_ok, "a wrong verdict is not counted twice")

    def test_named_is_scored_when_the_verdict_is_right_and_unscored_when_it_is_not(self):
        exp = Exp(3, "A", "D", UNKNOWN, lacunae_required=(), lacunae_admissible=(Q,))
        item = Item("i", "N", "N-gap", False, (), (exp,))
        self.assertIs(score_item(item, [Probe(3, UNKNOWN)]).probes[0].named_ok, True, "nothing required, nothing named")


class WithdrawnColumnTests(unittest.TestCase):
    ITEM = Item(
        "i", "R", "R-stale", False, (),
        (Exp(3, "A", "D", YES), Exp(5, "A", "D", UNKNOWN)),
        withdrawn=(Wd(4, required=(Q,), permitted=(Q,)),),
    )

    def test_bounded(self):
        ok = score_item(self.ITEM, [Probe(3, YES), Probe(5, UNKNOWN)], [WithdrawnReport(4, (Q,))])
        self.assertEqual([w.ok for w in ok.withdrawn], [True])
        silent = score_item(self.ITEM, [Probe(3, YES), Probe(5, UNKNOWN)], [WithdrawnReport(4, ())])
        self.assertEqual([w.ok for w in silent.withdrawn], [False])
        loud = score_item(self.ITEM, [Probe(3, YES), Probe(5, UNKNOWN)], [WithdrawnReport(4, (Q, L))])
        self.assertEqual([w.ok for w in loud.withdrawn], [False])

    def test_a_missing_report_counts_as_an_empty_one(self):
        none = score_item(self.ITEM, [Probe(3, YES), Probe(5, UNKNOWN)], [])
        self.assertEqual([w.ok for w in none.withdrawn], [False])
        nothing_required = Item("i", "R", "R-control", False, (), (Exp(3, "A", "D", YES),), withdrawn=(Wd(4, (), (Q,)),))
        self.assertEqual([w.ok for w in score_item(nothing_required, [Probe(3, YES)], []).withdrawn], [True])


class RefusalTests(unittest.TestCase):
    def test_a_solver_that_skipped_or_invented_a_probe_is_refused(self):
        item = Item("i", "R", "R-simple", False, (), (Exp(3, "A", "D", YES),))
        with self.assertRaises(ScoringError) as ctx:
            score_item(item, [])
        self.assertEqual(ctx.exception.code, "E-SC-001")
        with self.assertRaises(ScoringError):
            score_item(item, [Probe(2, YES)])

    def test_an_unknown_verdict_is_refused(self):
        item = Item("i", "R", "R-simple", False, (), (Exp(3, "A", "D", YES),))
        with self.assertRaises(ScoringError) as ctx:
            score_item(item, [Probe(3, "MAYBE")])
        self.assertEqual(ctx.exception.code, "E-SC-002")


class MatrixTests(unittest.TestCase):
    def _items(self):
        n_gap = Item("n1", "N", "N-gap", False, (), (Exp(3, "A", "D", UNKNOWN, (L,), (L, Q)),), designed_probe_index=3)
        c_blocked = Item("c1", "C", "C-blocked", False, (), (Exp(4, "A", "D", INADMISSIBLE, contested_required=(L,)),), designed_probe_index=4)
        r_stale = Item("r1", "R", "R-stale", False, (), (Exp(3, "A", "D", YES), Exp(5, "A", "D", UNKNOWN)), (Wd(4, (Q,), (Q,)),), 5)
        return n_gap, c_blocked, r_stale

    def test_cells_keep_their_denominators(self):
        cell = Cell()
        self.assertIsNone(cell.rate)
        self.assertEqual(str(cell).strip(), "—")
        cell.add(None)
        self.assertIsNone(cell.rate, "an unscored probe is not a hit")
        cell.add(True)
        cell.add(False)
        self.assertEqual(cell.rate, 0.5)

    def test_matrix_aggregates_by_class_variant_and_column(self):
        n_gap, c_blocked, r_stale = self._items()
        m = Matrix()
        good = {
            "n1": ([Probe(3, UNKNOWN, lacunae=(L,), work=4)], []),
            "c1": ([Probe(4, INADMISSIBLE, contested=(L,), work=7)], []),
            "r1": ([Probe(3, YES, work=3), Probe(5, UNKNOWN, work=3)], [WithdrawnReport(4, (Q,))]),
        }
        mute = {
            "n1": ([Probe(3, UNKNOWN, lacunae=(), work=1)], []),
            "c1": ([Probe(4, INADMISSIBLE, contested=(L,), work=1)], []),
            "r1": ([Probe(3, YES, work=1), Probe(5, YES, work=1)], [WithdrawnReport(4, ())]),
        }
        for solver, table in (("ctl_recompute", good), ("broken", mute)):
            for item in (n_gap, c_blocked, r_stale):
                probes, wd = table[item.item_id]
                m.add(solver, score_item(item, probes, wd))

        self.assertEqual(m.solvers, ["ctl_recompute", "broken"])
        self.assertTrue(m.perfect("ctl_recompute"))
        self.assertFalse(m.perfect("broken"))
        self.assertEqual(m.rate("ctl_recompute", "N", "named"), 1.0)
        self.assertEqual(m.rate("broken", "N", "named"), 0.0)
        self.assertEqual(m.rate("broken", "N", "verdict"), 1.0)
        self.assertEqual(m.rate("broken", "R", "verdict"), 0.5)
        self.assertEqual(m.rate("broken", "R", "withdrawn"), 0.0)
        self.assertIsNone(m.rate("broken", "H", "verdict"), "no H items: unscored, not perfect")
        self.assertIsNone(m.rate("broken", "N", "contested"))
        self.assertEqual(m.failing_variants("broken"), ["R-stale"])
        self.assertEqual(m.failing_variants("broken", "named"), ["N-gap"])
        self.assertEqual(m.failing_variants("ctl_recompute"), [])
        self.assertEqual(m.probes, 4, "probes are counted once, from the first solver")
        self.assertEqual(m.balance_report()["R"], {YES: 0.5, UNKNOWN: 0.5})
        self.assertAlmostEqual(m.mean_work("ctl_recompute"), (4 + 7 + 3 + 3) / 4)
        self.assertEqual(m.mean_work("broken", "R"), 1.0)
        self.assertEqual(len(m.failures["broken"]), 2)

    def test_render_puts_the_first_solver_first_and_json_round_trips(self):
        n_gap, _, _ = self._items()
        m = Matrix()
        m.add("ctl_recompute", score_item(n_gap, [Probe(3, UNKNOWN, lacunae=(L,))]))
        m.add("organism", score_item(n_gap, [Probe(3, UNKNOWN, lacunae=(L,))]))
        text = m.render(title="t")
        lines = text.splitlines()
        self.assertEqual(lines[0], "t")
        self.assertTrue(lines[3].startswith("ctl_recompute"))
        self.assertTrue(lines[4].startswith("organism"))
        self.assertIn("N:named", lines[1])
        payload = json.loads(m.to_json())
        self.assertEqual(payload["solvers"], ["ctl_recompute", "organism"])
        self.assertEqual(payload["cells"]["organism|N|named"], {"hits": 1, "total": 1})
        self.assertIn("N-gap", m.render_variants())


class AdapterTests(unittest.TestCase):
    STREAM = [fact("A", "B"), fact("B", "C"), fact("C", "D"), ask("A", "D"), retract("B", "C"), ask("A", "D")]

    def test_from_a_control_run(self):
        run = ctl_recompute(self.STREAM)
        probes = probes_from_control(run)
        self.assertEqual([(p.event_index, p.verdict) for p in probes], [(3, YES), (5, UNKNOWN)])
        self.assertTrue(all(p.work > 0 for p in probes))
        self.assertEqual(withdrawn_from_control(run), [WithdrawnReport(4, (Q,))])

    def test_from_organism_shaped_responses(self):
        @dataclass
        class Resp:
            verdict: str | None = None
            lacunae: tuple = ()
            contested: tuple = ()
            withdrawn: tuple = ()
            work: int = 0

        responses = [Resp(), Resp(), Resp(), Resp(YES, work=5), Resp(withdrawn=(Q,)), Resp(UNKNOWN, lacunae=(L,), work=2)]
        probes = probes_from_responses(responses)
        self.assertEqual([(p.event_index, p.verdict, p.lacunae, p.work) for p in probes], [(3, YES, (), 5), (5, UNKNOWN, (L,), 2)])
        self.assertEqual(withdrawn_from_responses(responses, self.STREAM), [WithdrawnReport(4, (Q,))])


if __name__ == "__main__":
    unittest.main()
