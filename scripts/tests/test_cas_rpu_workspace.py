"""The global workspace — binding, truth maintenance, provenance.

Three of the seven mechanisms a native reasoner needs live here, and each has
a test that fails if the mechanism is removed: variables that survive across
steps, epistemic statuses that stay apart, and a conclusion that can be walked
back to the premises it rests on.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "cas_rpu"))

from workspace import (  # noqa: E402
    Pattern,
    Proposition,
    Status,
    Workspace,
    WorkspaceError,
    chain_patterns,
)


def graph(*edges, closed=False):
    ws = Workspace(closed_world=closed)
    for a, b in edges:
        ws.fact(a, "leads_to", b)
    return ws


class BindingTests(unittest.TestCase):
    def test_a_variable_binds_and_holds_across_a_conjunction(self):
        """One dictionary threaded through both patterns is what makes a
        multi-premise rule expressible. Without it each pattern would match
        independently and the chain would not have to join up."""
        ws = graph(("VS", "QS"), ("QS", "IU"), ("AA", "BB"))
        bindings = ws.match_all(chain_patterns("leads_to", 2, "VS"))
        self.assertEqual(bindings, [{"?v1": "QS", "?z": "IU"}])

    def test_a_chain_that_does_not_join_up_yields_nothing(self):
        ws = graph(("VS", "QS"), ("AA", "IU"))
        self.assertEqual(ws.match_all(chain_patterns("leads_to", 2, "VS")), [])

    def test_unify_refuses_an_inconsistent_rebinding(self):
        pattern = Pattern("?x", "leads_to", "?x")
        prop = Proposition("VS", "leads_to", "IU")
        self.assertIsNone(pattern.unify(prop))
        loop = Proposition("VS", "leads_to", "VS")
        self.assertEqual(pattern.unify(loop), {"?x": "VS"})

    def test_polarity_is_part_of_matching(self):
        ws = Workspace()
        ws.fact("VS", "leads_to", "IU", negated=True)
        self.assertEqual(ws.match(Pattern("VS", "leads_to", "IU")), [])
        self.assertEqual(
            ws.match(Pattern("VS", "leads_to", "IU", negated=True)), [{}]
        )


class TruthMaintenanceTests(unittest.TestCase):
    def test_a_claim_and_its_negation_are_both_marked_contradicted(self):
        ws = Workspace()
        ws.fact("A", "is", "B")
        ws.fact("A", "is", "B", negated=True)
        self.assertEqual(ws.contradictions(), ("A|is|B",))
        self.assertEqual(ws.live(), ())

    def test_a_conclusion_may_not_rest_on_a_hypothesis(self):
        """The step by which a machine turns its own guess into its own
        evidence. Refused at the point of derivation, not audited afterwards."""
        ws = graph(("VS", "QS"))
        ws.hypothesize("QS", "leads_to", "IU")
        with self.assertRaises(WorkspaceError) as ctx:
            ws.derive(
                "VS", "leads_to", "IU", ("VS|leads_to|QS", "QS|leads_to|IU")
            )
        self.assertEqual(ctx.exception.code, "E-WS-002")

    def test_a_conclusion_may_not_support_itself(self):
        ws = graph(("VS", "IU"))
        with self.assertRaises(WorkspaceError) as ctx:
            ws.derive("VS", "leads_to", "IU", ("VS|leads_to|IU",))
        self.assertEqual(ctx.exception.code, "E-WS-003")

    def test_retraction_is_transitive(self):
        """Keeping a conclusion after retracting its only support leaves the
        processor believing something for no remaining reason."""
        ws = Workspace()
        ws.assume("VS", "leads_to", "QS")
        ws.fact("QS", "leads_to", "IU")
        derived = ws.derive(
            "VS", "leads_to", "IU", ("VS|leads_to|QS", "QS|leads_to|IU")
        )
        ws.retract("VS|leads_to|QS")
        self.assertIs(ws.props[derived.pid].status, Status.RETRACTED)

    def test_a_stronger_status_wins_and_a_weaker_one_does_not_demote(self):
        ws = Workspace()
        ws.hypothesize("VS", "leads_to", "IU")
        ws.fact("VS", "leads_to", "IU")
        self.assertIs(ws.props["VS|leads_to|IU"].status, Status.FACT)
        ws.hypothesize("VS", "leads_to", "IU")
        self.assertIs(ws.props["VS|leads_to|IU"].status, Status.FACT)


class WorldAssumptionTests(unittest.TestCase):
    def test_absence_is_unknown_under_an_open_world(self):
        ws = graph(("VS", "QS"))
        self.assertEqual(ws.ask("VS", "leads_to", "ZZ"), "UNKNOWN")

    def test_absence_is_no_under_a_closed_world(self):
        ws = graph(("VS", "QS"), closed=True)
        self.assertEqual(ws.ask("VS", "leads_to", "ZZ"), "NO")

    def test_an_explicit_negation_is_no_under_either_world(self):
        for closed in (True, False):
            ws = Workspace(closed_world=closed)
            ws.fact("VS", "leads_to", "ZZ", negated=True)
            self.assertEqual(ws.ask("VS", "leads_to", "ZZ"), "NO")

    def test_asking_records_a_lacuna_that_was_not_answered(self):
        """The lacuna is what the RPM gate turns into a sub-goal, so a question
        the workspace could not answer has to leave a trace of having been
        asked."""
        ws = graph(("VS", "QS"))
        ws.ask("VS", "leads_to", "ZZ")
        ws.ask("VS", "leads_to", "QS")
        self.assertEqual(ws.lacunae(), ("VS|leads_to|ZZ",))


class ProvenanceTests(unittest.TestCase):
    def test_a_conclusion_walks_back_to_its_premises(self):
        ws = graph(("VS", "QS"), ("QS", "IU"))
        derived = ws.derive(
            "VS", "leads_to", "IU", ("VS|leads_to|QS", "QS|leads_to|IU")
        )
        self.assertEqual(
            ws.roots(derived.pid), ("VS|leads_to|QS", "QS|leads_to|IU")
        )
        tree = ws.justification(derived.pid)
        self.assertEqual(len(tree["support"]), 2)
        self.assertEqual(tree["status"], "derived")

    def test_provenance_survives_two_levels_of_derivation(self):
        ws = graph(("A", "B"), ("B", "C"), ("C", "D"))
        ws.derive("A", "leads_to", "C", ("A|leads_to|B", "B|leads_to|C"))
        deep = ws.derive("A", "leads_to", "D", ("A|leads_to|C", "C|leads_to|D"))
        self.assertEqual(
            ws.roots(deep.pid),
            ("A|leads_to|B", "B|leads_to|C", "C|leads_to|D"),
        )

    def test_justifying_an_absent_proposition_is_refused(self):
        with self.assertRaises(WorkspaceError) as ctx:
            Workspace().justification("nope")
        self.assertEqual(ctx.exception.code, "E-WS-001")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
